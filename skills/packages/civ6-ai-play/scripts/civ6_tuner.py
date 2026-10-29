#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""civ6_tuner.py - 文明6 FireTuner（Firaxis Nexus）线协议最小客户端。

协议（依据官方 FireTuner2 行为实测/静态核对，见 references/lua-api.md）：
    帧 = <u32 LE length | i32 LE tag> + payload(utf-8) + b"\x00"
    length 含结尾 NUL。
    tag 4 = 握手：payload "APP:" -> 游戏身份；"LSQ:" -> Lua 状态表
            （NUL 分隔的 <索引> <名称> 交替串）
    tag 3 = 命令：payload "CMD:<状态索引>:<lua 代码>"
            回复可能多帧：
              tag -1 且 payload 以 "O\x00" 开头 = Lua print 输出，
                 格式 "O\x00<上下文>: <值>"（上下文如 GameCore）
              tag -1 且 payload 以 "L\x00" 开头 = 状态表变更通知
              payload 以 "ERR:" 开头 = Lua 运行时错误全文
              "true" / "" = 成功 ack（实现里统一当 raw 消息返回）
    tag 1 = help（官方 GUI 内部用，本项目未用）

要点：
- 游戏必须已启动且 AppOptions.txt [Debug] EnableTuner 为 1；
- 端口 127.0.0.1:4318，游戏内 TCP 服务端，同一时刻只允许一个客户端连接；
- 主菜单和对局中 Lua 状态不同：对局中才有 GameCore_Tuner 等状态；
- 断开 = 直接关闭 socket（协议没有 close 消息）。
- 建议每条 Lua 用 print("@@...") 输出结构化结果，便于外部解析；
  tuner 的 print 链路对 nil 比较敏感，打印前先 tostring/判空。

用法（CLI）：
    python civ6_tuner.py states
    python civ6_tuner.py eval --state GameCore_Tuner --lua "print('hi')"
    python civ6_tuner.py run --state FrontEnd --file setup.lua
"""
from __future__ import annotations

import argparse
import json
import socket
import struct
import sys
import time

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 4318
TAG_HANDSHAKE = 4
TAG_COMMAND = 3
TAG_HELP = 1


class TunerError(RuntimeError):
    pass


class TunerClient:
    """FireTuner 线协议客户端（同步、单连接）。"""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                 timeout: float = 10.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.app_identity = ""
        self.states: dict[int, str] = {}

    # ---------- 连接 / 握手 ----------
    def connect(self, timeout: float | None = None, handshake_timeout: float = 20.0) -> str:
        """连接并握手。刚启动时服务端可能已监听但暂不处理帧，故重试 APP:。"""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout or self.timeout)
        s.connect((self.host, self.port))
        s.settimeout(None)
        self.sock = s
        self._drain(0.2)
        deadline = time.time() + handshake_timeout
        while time.time() < deadline:
            self.send_frame(TAG_HANDSHAKE, "APP:")
            msgs = self._drain(2.0)
            if msgs:
                self.app_identity = msgs[0][1]
                break
        else:
            self.app_identity = "<no-response>"
        self.refresh_states()
        return self.app_identity

    def close(self) -> None:
        if self.sock is not None:
            try:
                self.sock.close()
            except OSError:
                pass
            self.sock = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *exc):
        self.close()

    # ---------- 帧收发 ----------
    def send_frame(self, tag: int, payload: str) -> None:
        if self.sock is None:
            raise TunerError("未连接 Tuner")
        data = payload.encode("utf-8") + b"\x00"
        self.sock.sendall(struct.pack("<Ii", len(data), tag) + data)

    def recv_frame(self, timeout: float = 2.0):
        """读一帧；超时返回 None。"""
        if self.sock is None:
            raise TunerError("未连接 Tuner")
        self.sock.settimeout(max(0.05, timeout))
        header = b""
        try:
            while len(header) < 8:
                chunk = self.sock.recv(8 - len(header))
                if not chunk:
                    return None
                header += chunk
            length, tag = struct.unpack("<Ii", header)
            if length <= 0 or length > 64 * 1024 * 1024:
                raise TunerError(f"异常帧长度: {length}")
            data = b""
            while len(data) < length:
                chunk = self.sock.recv(length - len(data))
                if not chunk:
                    return None
                data += chunk
        except socket.timeout:
            return None
        finally:
            self.sock.settimeout(None)
        payload = data.rstrip(b"\x00").decode("utf-8", errors="replace")
        return tag, payload

    def _drain(self, timeout: float = 0.6, max_msgs: int = 400):
        out = []
        deadline = time.time() + timeout
        while len(out) < max_msgs:
            remain = deadline - time.time()
            if remain <= 0:
                break
            msg = self.recv_frame(timeout=min(remain, 1.0))
            if msg is None:
                break
            out.append(msg)
        return out

    # ---------- 状态表 ----------
    @staticmethod
    def parse_states(payload: str) -> dict[int, str]:
        parts = [p.strip() for p in payload.replace("\x00", "\n").split("\n") if p.strip()]
        states: dict[int, str] = {}
        i = 0
        while i + 1 < len(parts):
            try:
                states[int(parts[i])] = parts[i + 1]
                i += 2
            except ValueError:
                i += 1
        return states

    def refresh_states(self, attempts: int = 3, wait: float = 2.0) -> dict[int, str]:
        for _ in range(max(1, attempts)):
            self.send_frame(TAG_HANDSHAKE, "LSQ:")
            msgs = self._drain(wait)
            raw = ""
            for _tag, payload in msgs:
                if "\x00" in payload:
                    raw = payload
                    break
                if payload.strip().isdigit() and not raw:
                    raw = payload
            if raw:
                parsed = self.parse_states(raw)
                if parsed:
                    self.states = parsed
                    break
        return self.states

    def resolve_state(self, name_or_index) -> int:
        """按索引或名称（精确优先，再子串，忽略大小写）解析 Lua 状态。"""
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
        raise TunerError(f"找不到 Lua 状态: {text}. 现有状态: "
                         + ", ".join(f"{i}={n}" for i, n in sorted(self.states.items())))

    def find_state(self, name_part: str):
        """按名称返回状态索引（精确优先，再子串）；找不到返回 None。"""
        low = name_part.lower()
        for idx, nm in self.states.items():
            if nm.lower() == low:
                return idx
        for idx, nm in self.states.items():
            if low in nm.lower():
                return idx
        return None

    # ---------- 命令 ----------
    def send_command(self, state_index: int, lua_code: str) -> None:
        self.send_frame(TAG_COMMAND, f"CMD:{state_index}:{lua_code}")

    @staticmethod
    def classify(tag: int, payload: str) -> dict:
        """把一帧回复解析成 {kind, context, text}。"""
        if payload.startswith("ERR:"):
            return {"kind": "error", "context": "", "text": payload[4:].strip()}
        if payload.startswith("O\x00"):
            rest = payload[2:]
            ctx, sep, val = rest.partition(": ")
            if not sep:
                ctx, sep, val = rest.partition(":")
            return {"kind": "output", "context": ctx.strip(), "text": val.strip()}
        if payload.startswith("L\x00"):
            return {"kind": "states", "context": "", "text": payload[2:]}
        return {"kind": "raw", "context": "", "text": payload}

    def eval_lua(self, state, lua_code: str, wait: float = 3.0) -> list[dict]:
        """在指定状态执行 Lua，返回解析后的消息列表。"""
        idx = self.resolve_state(state)
        self.send_command(idx, lua_code)
        msgs = []
        for tag, payload in self._drain(wait):
            msg = self.classify(tag, payload)
            if msg["kind"] == "states":
                parsed = self.parse_states(msg["text"])
                if parsed:
                    self.states.update(parsed)
                continue
            msgs.append(msg)
        return msgs

    def eval_collect(self, state, lua_code: str, wait: float = 3.0) -> dict:
        """执行 Lua 并收集以 @@ 开头的输出行。

        返回 {"ok": bool, "lines": [...], "error": str|None, "raw": [...]}。
        Lua 端建议 print("@@key=value")。
        """
        msgs = self.eval_lua(state, lua_code, wait=wait)
        lines, errors, raw = [], [], []
        for m in msgs:
            if m["kind"] == "error":
                errors.append(m["text"])
            elif m["kind"] == "output":
                for line in m["text"].splitlines():
                    line = line.strip()
                    if line.startswith("@@"):
                        lines.append(line[2:])
                    elif line:
                        raw.append(line)
            elif m["kind"] == "raw" and m["text"] not in ("true", ""):
                raw.append(m["text"])
        return {"ok": not errors, "lines": lines, "error": "\n".join(errors) or None,
                "raw": raw}


def _state_index(value: str) -> int | str:
    return int(value) if value.isdigit() else value


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="文明6 FireTuner 最小客户端")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--timeout", type=float, default=10.0)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("states", help="连接并列出 Lua 状态表")

    p_eval = sub.add_parser("eval", help="在指定状态执行 Lua 代码")
    p_eval.add_argument("--state", required=True, help="状态名或索引")
    p_eval.add_argument("--lua", required=True)
    p_eval.add_argument("--wait", type=float, default=3.0)

    p_run = sub.add_parser("run", help="执行 Lua 文件")
    p_run.add_argument("--state", required=True)
    p_run.add_argument("--file", required=True)
    p_run.add_argument("--wait", type=float, default=3.0)

    p_wait = sub.add_parser("wait", help="轮询等待某个状态出现")
    p_wait.add_argument("--state", required=True, help="状态名子串")
    p_wait.add_argument("--timeout", type=float, default=180.0)

    args = ap.parse_args(argv)
    client = TunerClient(args.host, args.port, args.timeout)
    try:
        app = client.connect()
    except (ConnectionRefusedError, OSError) as exc:
        print(f"连接失败: {exc} (游戏是否已启动，EnableTuner=1？)")
        return 2
    try:
        if args.cmd == "states":
            print("APP:", app)
            for idx, name in sorted(client.states.items()):
                print(f"{idx:>3}  {name}")
            return 0
        if args.cmd == "wait":
            deadline = time.time() + args.timeout
            while time.time() < deadline:
                client.refresh_states()
                idx = client.find_state(args.state)
                if idx is not None:
                    print(f"FOUND {idx} {client.states[idx]}")
                    return 0
                time.sleep(1.0)
            print("TIMEOUT", args.state)
            return 1
        if args.cmd == "run":
            with open(args.file, "r", encoding="utf-8") as f:
                code = f.read()
        else:
            code = args.lua
        msgs = client.eval_lua(_state_index(args.state), code, wait=args.wait)
        for m in msgs:
            if m["kind"] == "output":
                print(f"[{m['context']}] {m['text']}")
            elif m["kind"] == "error":
                print("LUA-ERROR:", m["text"])
            else:
                print(m["text"])
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    sys.exit(main())
