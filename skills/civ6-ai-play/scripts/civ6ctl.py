#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""civ6ctl.py - 文明6 AI 控制/自动化测试统一 CLI。

把 civ6_tuner（协议）、civ6_game（启动/新局/操作）、civ6_win（窗口/截图）、
civ6_mods（Mod 启停）、civ6_logs（日志取证）串成可复用命令。

常见流程：
  python civ6ctl.py env                          # 检查安装、Tuner 端口、运行状态
  python civ6ctl.py launch --windowed            # 备份配置、窗口化、启动并等待 Tuner
  python civ6ctl.py start --leader LEADER_QIN --civ CIVILIZATION_CHINA
  python civ6ctl.py probe                        # 读取回合/玩家/单位/城市
  python civ6ctl.py act move --x 10 --y 10
  python civ6ctl.py act found
  python civ6ctl.py act endturn
  python civ6ctl.py shot --out shot.png
  python civ6ctl.py close                        # 退出游戏
  python civ6ctl.py restore-config               # 还原启动前备份的选项文件

所有会改写用户文件的动作（AppOptions/GraphicsOptions/Mods.sqlite）先备份；
任何命令都不在游戏运行时改写 Mods.sqlite 或选项文件。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import civ6_game as G
import civ6_ops as O
import civ6_tuner as T


def _print(obj) -> None:
    if isinstance(obj, str):
        print(obj)
    else:
        print(json.dumps(obj, ensure_ascii=False, indent=2))


def _optional(module: str):
    try:
        return __import__(module)
    except ImportError:
        return None


def _connect(timeout: float = 30.0):
    client = G.make_client()
    if hasattr(client, "base_url"):
        G.wait_for_bridge_connected(client.base_url, timeout=timeout)
        client.connect()
        return client
    return G.wait_for_tuner(timeout=timeout)


# ---------------------------------------------------------------------------
# 命令实现
# ---------------------------------------------------------------------------
def cmd_env(args) -> int:
    game_dir = G.find_game_dir()
    tuner_ok = False
    app = ""
    if game_dir:
        try:
            c = T.TunerClient()
            app = c.connect(timeout=3.0)
            tuner_ok = bool(c.states)
            c.close()
        except (OSError, T.TunerError):
            pass
    _print({
        "game_dir": str(game_dir) if game_dir else None,
        "user_dir": str(G.user_dir()),
        "logs_dir": str(G.logs_dir()),
        "mods_db": str(G.mods_db_path()),
        "state_dir": str(G.STATE_DIR),
        "running": G.running_game_processes(),
        "tuner_reachable": tuner_ok,
        "tuner_app": app,
    })
    return 0


def cmd_launch(args) -> int:
    if args.windowed:
        _print({"windowed": G.ensure_windowed(args.width, args.height,
                                              low_graphics=not args.keep_graphics)})
    if G.game_running():
        print("游戏已在运行，跳过启动")
    else:
        G.launch(exe=args.exe, wait=False)
    win = G.wait_for_game_window(timeout=args.timeout)
    _print({"window": win})
    # 等待主菜单 Tuner 就绪（游戏加载 mod 时需要几十秒）
    try:
        client = O.connect_tuner_retry(timeout=args.timeout)
        try:
            _print({"tuner": {"connected": True, "states": len(client.states),
                              "frontend": client.find_state("FrontEnd")}})
        finally:
            client.close()
    except TimeoutError as exc:
        _print({"tuner": {"connected": False, "error": str(exc)}})
    return 0


def cmd_states(args) -> int:
    client = _connect()
    try:
        for idx, name in sorted(client.states.items()):
            print(f"{idx:>3}  {name}")
    finally:
        client.close()
    return 0


def cmd_start(args) -> int:
    if args.bridge:
        return _cmd_start_via_bridge(args)
    session = O.start_game_flow(
        leader=args.leader, civilization=args.civ, ruleset=args.ruleset,
        map_size=args.map_size, game_speed=args.speed, handicap=args.handicap,
        game_name=args.game_name, load_timeout=args.load_timeout,
        log_cb=lambda m: print("[start]", m))
    try:
        _print({"states": {"GameCore_Tuner": session.game_state, "InGame": session.ui_state},
                "probe": session.probe()["data"]})
        return 0
    finally:
        session.close()


def _cmd_start_via_bridge(args) -> int:
    session = G.open_session(timeout=60, require_frontend=True)
    try:
        if session.frontend_state is None:
            print("未找到 FrontEnd Lua 状态（游戏未在主菜单？）")
            return 3
        res = session.client.eval_collect(
            session.frontend_state,
            G.lua_setup_new_game(leader=args.leader, civilization=args.civ,
                                 ruleset=args.ruleset, map_size=args.map_size,
                                 game_speed=args.speed, handicap=args.handicap,
                                 game_name=args.game_name),
            wait=8.0)
        _print({"frontend_state": session.frontend_state, "result": res})
        idx = G.wait_for_state(session.client, "GameCore", timeout=args.load_timeout)
        session.game_state = idx
        print(f"对局 Lua 状态: {idx} {session.client.states[idx]}")
        return 0
    finally:
        session.client.close()


def cmd_probe(args) -> int:
    session = O.open_ingame_session(timeout=args.timeout)
    try:
        _print(session.probe())
    finally:
        session.close()
    return 0


def cmd_act(args) -> int:
    session = O.open_ingame_session(timeout=30)
    try:
        if args.action == "move":
            _print(session.act("move", x=args.x, y=args.y, unit_type=args.unit_type))
        elif args.action == "found":
            _print(session.act("found", unit_type=args.unit_type))
        else:
            _print(session.act(args.action))
    finally:
        session.close()
    return 0


def cmd_shot(args) -> int:
    win = _optional("civ6_win")
    if win is None:
        print("缺少 civ6_win.py（窗口/截图模块）")
        return 3
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    shot = win.capture_window(proc_names=args.proc, out_path=str(out),
                              bring_to_front=not args.no_front)
    _print({"saved": str(out), "info": shot})
    return 0


def cmd_mods(args) -> int:
    mods = _optional("civ6_mods")
    if mods is None:
        print("缺少 civ6_mods.py（Mods.sqlite 模块）")
        return 3
    if args.mods_cmd == "list":
        _print(mods.list_mods())
    elif args.mods_cmd == "groups":
        _print(mods.list_groups())
    elif args.mods_cmd == "enabled":
        _print(mods.enabled_mods())
    elif args.mods_cmd == "enable":
        _print(mods.set_enabled(args.name, True, allow_running=args.force))
    elif args.mods_cmd == "disable":
        _print(mods.set_enabled(args.name, False, allow_running=args.force))
    elif args.mods_cmd == "backup":
        _print({"backup": mods.backup()})
    elif args.mods_cmd == "restore":
        _print({"restored": mods.restore(args.backup)})
    return 0


def cmd_logs(args) -> int:
    logs = _optional("civ6_logs")
    if logs is None:
        print("缺少 civ6_logs.py（日志模块）")
        return 3
    if args.logs_cmd == "errors":
        _print(logs.scan_errors(files=args.file or None,
                                since_turn=args.since, max_lines=args.max_lines))
    elif args.logs_cmd == "tail":
        _print(logs.tail(args.file or "Lua.log", lines=args.max_lines))
    elif args.logs_cmd == "enabled-mods":
        _print(logs.enabled_mods_from_log())
    elif args.logs_cmd == "paths":
        _print(logs.paths())
    return 0


def cmd_close(args) -> int:
    quit_ok = False
    if G.game_running():
        try:
            session = O.open_ingame_session(timeout=20)
            session.quit()
            session.close()
            quit_ok = True
        except Exception as exc:  # noqa: BLE001
            print("对局内退出失败，尝试前端/强杀:", exc)
    deadline = time.time() + args.wait
    while time.time() < deadline:
        if not G.game_running():
            break
        time.sleep(1.0)
    if G.game_running():
        for proc in G.running_game_processes():
            import subprocess
            subprocess.run(["taskkill", "/PID", str(proc["pid"]), "/F"], capture_output=True)
        time.sleep(1)
    if args.stop_bridge:
        _optional_stop_bridge()
    print("游戏已退出" if not G.game_running() else "游戏仍在运行，请检查")
    return 0 if not G.game_running() else 1


def _optional_stop_bridge() -> None:
    try:
        import civ6_bridge
        civ6_bridge.BridgeTunerClient().shutdown()
    except Exception:  # noqa: BLE001
        pass


def cmd_serve(args) -> int:
    import civ6_bridge
    return civ6_bridge.serve(args.port, args.http_port, args.wait)


def cmd_restore_config(args) -> int:
    _print({"restored": G.restore_options()})
    return 0


# ---------------------------------------------------------------------------
# argparse
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="文明6 AI 控制与自动化测试 CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("env", help="检查环境、路径、Tuner 可达性")

    p = sub.add_parser("launch", help="窗口化并启动游戏，等待 Tuner")
    p.add_argument("--exe", default="dx12", choices=["dx12", "dx11"])
    p.add_argument("--windowed", action="store_true", help="先备份并改写为窗口化配置")
    p.add_argument("--keep-graphics", action="store_true", help="不改低显卡画质")
    p.add_argument("--width", type=int, default=G.WINDOW_WIDTH)
    p.add_argument("--height", type=int, default=G.WINDOW_HEIGHT)
    p.add_argument("--timeout", type=float, default=360.0)

    sub.add_parser("states", help="列出当前 Lua 状态")

    p = sub.add_parser("start", help="在前端选择文明/领袖并开始新对局")
    p.add_argument("--leader", default="LEADER_QIN")
    p.add_argument("--civ", default="")
    p.add_argument("--ruleset", default="RULESET_EXPANSION_2")
    p.add_argument("--map-size", default="MAPSIZE_TINY")
    p.add_argument("--speed", default="GAMESPEED_ONLINE")
    p.add_argument("--handicap", default="HANDICAP_PRINCE")
    p.add_argument("--game-name", default="AI_CONTROL_TEST")
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--load-timeout", type=float, default=300.0)
    p.add_argument("--bridge", action="store_true", help="经 civ6_bridge 执行（默认直连）")

    p = sub.add_parser("probe", help="读取对局状态（回合/城市/单位）")
    p.add_argument("--timeout", type=float, default=60.0)

    p = sub.add_parser("act", help="对局内动作")
    p.add_argument("action", choices=["probe", "move", "found", "endturn", "quit"])
    p.add_argument("--x", type=int)
    p.add_argument("--y", type=int)
    p.add_argument("--unit-type", default="UNIT_SETTLER")

    p = sub.add_parser("shot", help="窗口截图")
    p.add_argument("--out", default="civ6_shot.png")
    p.add_argument("--proc", default=None, help="进程名，默认自动查找 CivilizationVI*")
    p.add_argument("--no-front", action="store_true")

    p = sub.add_parser(
        "mods",
        help="Mod 启停/查看（Mods.sqlite；enable/disable 先自动备份再立即写入）",
        epilog="说明：enable/disable 会先自动备份 Mods.sqlite 再立即写入（等价于 civ6_mods.py --yes），"
               "不需要 --yes；游戏运行中始终拒绝写入。--force 仅为兼容参数，实际不生效。")
    p.add_argument("mods_cmd", choices=["list", "groups", "enabled", "enable", "disable", "backup", "restore"])
    p.add_argument("--name", default="")
    p.add_argument("--force", action="store_true",
                   help="兼容参数，实际不生效（游戏运行中始终拒绝写入）")
    p.add_argument("--backup", default=None, help="restore 时指定备份文件")

    p = sub.add_parser("logs", help="日志取证")
    p.add_argument("logs_cmd", choices=["errors", "tail", "enabled-mods", "paths"])
    p.add_argument("--file", default=None)
    p.add_argument("--since", type=float, default=0.0)
    p.add_argument("--max-lines", type=int, default=200)

    p = sub.add_parser("close", help="退出游戏（必要时强杀）")
    p.add_argument("--wait", type=float, default=30.0)
    p.add_argument("--stop-bridge", action="store_true", help="退出后同时关闭 civ6_bridge")

    p = sub.add_parser("serve", help="启动常驻 Tuner 桥（后台运行）")
    p.add_argument("--port", type=int, default=4318, help="Tuner 端口")
    p.add_argument("--http-port", type=int, default=8770)
    p.add_argument("--wait", type=float, default=900.0, help="等待 Tuner 连接的最长秒数")

    sub.add_parser("restore-config", help="还原启动前备份的 AppOptions/GraphicsOptions")

    args = ap.parse_args(argv)
    handlers = {
        "env": cmd_env, "launch": cmd_launch, "states": cmd_states,
        "start": cmd_start, "probe": cmd_probe, "act": cmd_act,
        "shot": cmd_shot, "mods": cmd_mods, "logs": cmd_logs,
        "close": cmd_close, "serve": cmd_serve,
        "restore-config": cmd_restore_config,
    }
    try:
        return handlers[args.cmd](args)
    except (T.TunerError, TimeoutError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
