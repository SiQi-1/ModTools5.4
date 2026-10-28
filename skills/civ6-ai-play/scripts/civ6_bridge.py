#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""civ6_bridge.py - 常驻 Tuner 桥：保持单个 FireTuner 连接，对外提供 HTTP。

为什么需要桥：文明6 的 FireTuner TCP 服务端在同一时刻只接受一个客户端；
而且实测在进入对局后若客户端断开，监听端口可能不再恢复（4318 消失、4319 为
其他服务）。因此需要在“主菜单 -> 加载 -> 对局”整个过程中保持同一条连接。
本模块启动一个后台进程持有连接，其他脚本/agent 通过 localhost HTTP 发送
Lua 命令，即可在任意时刻读取状态或操作游戏。

用法：
  python civ6_bridge.py serve [--port 4318] [--http-port 8770] [--wait 600]
  python civ6_bridge.py health
  python civ6_bridge.py states
  python civ6_bridge.py eval --state GameCore_Tuner --lua "print('hi')"
  python civ6_bridge.py run --state FrontEnd --file setup.lua
  python civ6_bridge.py stop

HTTP API（JSON）：
  GET  /health                      -> {ok, connected, app, states_count, port}
  GET  /states                      -> {states: {index: name}}
  POST /eval    {state, code, wait} -> {ok, lines, error, raw, states}
  POST /refresh                     -> {states}
  POST /shutdown                    -> 关闭桥进程
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from civ6_tuner import TunerClient, TunerError

DEFAULT_TUNER_PORT = 4318
DEFAULT_HTTP_PORT = 8770
PORT_SCAN = [4318, 4319, 4320]


class TunerHolder:
    """持有 Tuner 连接，序列化所有命令。"""

    def __init__(self, tuner_port: int = DEFAULT_TUNER_PORT):
        self.tuner_port = tuner_port
        self.client: TunerClient | None = None
        self.lock = threading.RLock()
        self.app = ""
        self.last_error = ""

    def connect_loop(self, stop_event: threading.Event, wait_seconds: float = 600.0) -> None:
        deadline = time.time() + wait_seconds
        while not stop_event.is_set() and time.time() < deadline:
            with self.lock:
                if self.client is not None:
                    return
                for port in [self.tuner_port] + [p for p in PORT_SCAN if p != self.tuner_port]:
                    c = TunerClient(port=port)
                    try:
                        app = c.connect(timeout=3.0, handshake_timeout=5.0)
                        self.client = c
                        self.app = app
                        self.last_error = ""
                        print(f"[bridge] connected tuner port={port} app={app!r}", flush=True)
                        return
                    except (OSError, TunerError) as exc:
                        self.last_error = str(exc)
                        c.close()
            time.sleep(2.0)
        print(f"[bridge] tuner connect timeout: {self.last_error}", flush=True)

    def _ensure(self) -> TunerClient:
        if self.client is None:
            raise TunerError("桥尚未连接 Tuner：" + (self.last_error or "unknown"))
        return self.client

    def states(self) -> dict:
        with self.lock:
            c = self._ensure()
            c.refresh_states()
            return {str(k): v for k, v in sorted(c.states.items())}

    def eval(self, state, code: str, wait: float = 4.0) -> dict:
        with self.lock:
            c = self._ensure()
            res = c.eval_collect(state, code, wait=wait)
            res["states"] = {str(k): v for k, v in sorted(c.states.items())}
            return res

    def close(self) -> None:
        with self.lock:
            if self.client is not None:
                self.client.close()
                self.client = None


class Handler(BaseHTTPRequestHandler):
    holder: TunerHolder = None  # type: ignore
    stop_cb = None  # type: ignore

    def log_message(self, fmt, *args):  # 安静
        pass

    def _send(self, code: int, obj) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        return json.loads(self.rfile.read(n).decode("utf-8"))

    def do_GET(self):
        try:
            if self.path.startswith("/health"):
                h = self.holder
                connected = h.client is not None
                self._send(200, {"ok": True, "connected": connected, "app": h.app,
                                 "states_count": len(h.client.states) if connected else 0,
                                 "port": h.tuner_port, "last_error": h.last_error})
            elif self.path.startswith("/states"):
                self._send(200, {"ok": True, "states": self.holder.states()})
            else:
                self._send(404, {"ok": False, "error": "not found"})
        except TunerError as exc:
            self._send(503, {"ok": False, "error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            self._send(500, {"ok": False, "error": repr(exc)})

    def do_POST(self):
        try:
            body = self._body()
            if self.path.startswith("/eval"):
                res = self.holder.eval(body.get("state", "FrontEnd"), body.get("code", ""),
                                       float(body.get("wait", 4.0)))
                self._send(200, res)
            elif self.path.startswith("/refresh"):
                self._send(200, {"ok": True, "states": self.holder.states()})
            elif self.path.startswith("/shutdown"):
                self._send(200, {"ok": True, "bye": True})
                if self.stop_cb:
                    threading.Thread(target=self.stop_cb, daemon=True).start()
            else:
                self._send(404, {"ok": False, "error": "not found"})
        except TunerError as exc:
            self._send(503, {"ok": False, "error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            self._send(500, {"ok": False, "error": repr(exc)})


def serve(tuner_port: int, http_port: int, wait_seconds: float) -> int:
    holder = TunerHolder(tuner_port)
    stop_event = threading.Event()
    t = threading.Thread(target=holder.connect_loop, args=(stop_event, wait_seconds), daemon=True)
    t.start()

    Handler.holder = holder  # type: ignore

    def stop():
        stop_event.set()
        holder.close()
        threading.Thread(target=server.shutdown, daemon=True).start()

    Handler.stop_cb = staticmethod(stop)  # type: ignore
    server = ThreadingHTTPServer(("127.0.0.1", http_port), Handler)
    print(f"[bridge] http://127.0.0.1:{http_port}  tuner_port={tuner_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        stop()
    finally:
        stop_event.set()
        holder.close()
    return 0


# ---------------------------------------------------------------------------
# 与 TunerClient 兼容的 HTTP 客户端（供 civ6ctl / civ6_game 复用）
# ---------------------------------------------------------------------------
class BridgeTunerClient:
    """通过 civ6_bridge HTTP 访问游戏的客户端，接口模仿 TunerClient。"""

    def __init__(self, base_url: str = f"http://127.0.0.1:{DEFAULT_HTTP_PORT}"):
        self.base_url = base_url.rstrip("/")
        self.states: dict[int, str] = {}
        self.app_identity = ""

    # ---- http ----
    def _get(self, path: str) -> dict:
        with urllib.request.urlopen(self.base_url + path, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))

    def _post(self, path: str, obj: dict) -> dict:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(self.base_url + path, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode("utf-8"))

    # ---- TunerClient 兼容接口 ----
    def connect(self, timeout: float | None = None, handshake_timeout: float = 20.0) -> str:
        h = self._get("/health")
        if not h.get("connected"):
            raise TunerError("桥未连接 Tuner: " + str(h.get("last_error")))
        self.app_identity = h.get("app", "")
        self.refresh_states()
        return self.app_identity

    def close(self) -> None:
        pass

    def refresh_states(self, attempts: int = 2, wait: float = 1.0) -> dict[int, str]:
        data = self._get("/states")
        self.states = {int(k): v for k, v in (data.get("states") or {}).items()}
        return self.states

    def resolve_state(self, name_or_index) -> int:
        if isinstance(name_or_index, int):
            return name_or_index
        text = str(name_or_index).strip()
        if text.isdigit():
            return int(text)
        if not self.states:
            self.refresh_states()
        low = text.lower()
        for idx, nm in self.states.items():
            if nm.lower() == low:
                return idx
        for idx, nm in self.states.items():
            if low in nm.lower():
                return idx
        raise TunerError(f"找不到 Lua 状态: {text}")

    def find_state(self, name_part: str):
        low = name_part.lower()
        for idx, nm in self.states.items():
            if nm.lower() == low:
                return idx
        for idx, nm in self.states.items():
            if low in nm.lower():
                return idx
        return None

    def eval_lua(self, state, lua_code: str, wait: float = 3.0) -> list[dict]:
        idx = self.resolve_state(state)
        res = self._post("/eval", {"state": idx, "code": lua_code, "wait": wait})
        if res.get("states"):
            self.states = {int(k): v for k, v in res["states"].items()}
        msgs = []
        for line in res.get("lines") or []:
            msgs.append({"kind": "output", "context": "", "text": line})
        if res.get("error"):
            msgs.append({"kind": "error", "context": "", "text": res["error"]})
        for raw in res.get("raw") or []:
            msgs.append({"kind": "raw", "context": "", "text": raw})
        return msgs

    def eval_collect(self, state, lua_code: str, wait: float = 3.0) -> dict:
        idx = self.resolve_state(state)
        res = self._post("/eval", {"state": idx, "code": lua_code, "wait": wait})
        if res.get("states"):
            self.states = {int(k): v for k, v in res["states"].items()}
        return res

    def shutdown(self) -> None:
        try:
            self._post("/shutdown", {})
        except OSError:
            pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="文明6 FireTuner 常驻桥")
    ap.add_argument("--http-port", type=int, default=DEFAULT_HTTP_PORT)
    ap.add_argument("--port", type=int, default=DEFAULT_TUNER_PORT)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("serve")
    p.add_argument("--wait", type=float, default=600.0)
    sub.add_parser("health")
    sub.add_parser("states")
    sub.add_parser("stop")
    p = sub.add_parser("eval")
    p.add_argument("--state", required=True)
    p.add_argument("--lua", required=True)
    p.add_argument("--wait", type=float, default=4.0)
    p = sub.add_parser("run")
    p.add_argument("--state", required=True)
    p.add_argument("--file", required=True)
    p.add_argument("--wait", type=float, default=4.0)
    args = ap.parse_args(argv)

    if args.cmd == "serve":
        return serve(args.port, args.http_port, args.wait)
    client = BridgeTunerClient(f"http://127.0.0.1:{args.http_port}")
    try:
        if args.cmd == "health":
            print(json.dumps(client._get("/health"), ensure_ascii=False, indent=2))
        elif args.cmd == "states":
            for idx, name in sorted(client.refresh_states().items()):
                print(f"{idx:>3}  {name}")
        elif args.cmd == "stop":
            client.shutdown()
            print("stop requested")
        elif args.cmd == "eval":
            print(json.dumps(client.eval_collect(args.state, args.lua, args.wait), ensure_ascii=False, indent=2))
        elif args.cmd == "run":
            with open(args.file, encoding="utf-8") as f:
                code = f.read()
            print(json.dumps(client.eval_collect(args.state, code, args.wait), ensure_ascii=False, indent=2))
        return 0
    except (OSError, TunerError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
