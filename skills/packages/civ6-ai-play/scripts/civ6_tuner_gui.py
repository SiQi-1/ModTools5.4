#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""civ6_tuner_gui.py - 通过官方 FireTuner2 GUI 控制文明6（备用通道）。

背景：FireTuner 是单连接 TCP；某版本/某台机器实测，进入对局后断开的客户端无法重连
（换版本/换机后建议重测），而 FireTuner2.exe 具备自动重连能力，进入对局并跳过领袖介绍后
它会重新连上（4318 监听只在游戏完全就绪后出现）。因此把 FireTuner2 当作“协议代理”：
本模块用 Win32 消息/键鼠自动化它的 Lua Console —— 选择 Lua 状态、写入代码、
回车执行、读取输出区文本，从而在不重写协议客户端的情况下操作游戏。

用法（CLI）：
  python civ6_tuner_gui.py launch                 # 启动 FireTuner2（若未运行）
  python civ6_tuner_gui.py status                 # 连接状态/当前状态/输出尾部
  python civ6_tuner_gui.py states                 # 下拉框中的 Lua 状态列表
  python civ6_tuner_gui.py exec --state GameCore_Tuner --code "print('hi')"
  python civ6_tuner_gui.py exec --state GameCore_Tuner --file probe.lua
  python civ6_tuner_gui.py select --state InGame

FireTuner2.exe 默认由 civ6_game 自动探测游戏目录旁的
Sid Meier's Civilization VI SDK\FireTuner\FireTuner2.exe；也可用 --exe 指定，
或设置 CIV6_FIRETUNER_EXE（CIV6_GAME_DIR 可指定游戏根目录以推导相邻 SDK）。

输出约定：Lua 代码建议 print("@@key=value")；exec 返回新增输出文本。
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from civ6_game import find_game_dir  # noqa: E402  同目录模块：Steam 库自动探测

try:  # DPI 感知：坐标必须与物理像素一致
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:  # noqa: BLE001
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:  # noqa: BLE001
        pass

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
user32.SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
user32.SendMessageW.restype = ctypes.c_ssize_t

WM_GETTEXT, WM_SETTEXT, WM_GETTEXTLENGTH = 0x000D, 0x000C, 0x000E
CB_GETCOUNT, CB_GETCURSEL, CB_GETLBTEXT = 0x0146, 0x0147, 0x0148
HWND_TOPMOST = wt.HWND(-1)
SWP_SHOWWINDOW = 0x0040
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
VK_RETURN, VK_HOME, VK_DOWN = 0x0D, 0x24, 0x28


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wt.WORD), ("wScan", wt.WORD), ("dwFlags", wt.DWORD),
                ("time", wt.DWORD), ("dwExtraInfo", ctypes.c_void_p)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wt.DWORD), ("ki", KEYBDINPUT), ("mi", ctypes.c_byte * 24)]


def _send(h, msg, w=0, l=0):
    return user32.SendMessageW(h, msg, w, l)


def _key(vk, flags=0):
    return INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(vk, 0, flags, 0, None))


def press(vk, hold=0.05):
    user32.SendInput(1, ctypes.byref(_key(vk)), ctypes.sizeof(INPUT))
    time.sleep(hold)
    user32.SendInput(1, ctypes.byref(_key(vk, KEYEVENTF_KEYUP)), ctypes.sizeof(INPUT))
    time.sleep(0.05)


def click(x, y):
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.1)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.06)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.15)


def win_text(h):
    n = user32.GetWindowTextLengthW(h)
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.GetWindowTextW(h, buf, n + 1)
    return buf.value


def win_class(h):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(h, buf, 256)
    return buf.value


def get_text(h, maxlen=400000):
    n = _send(h, WM_GETTEXTLENGTH)
    if n <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(min(n, maxlen) + 1)
    _send(h, WM_GETTEXT, min(n, maxlen) + 1, ctypes.addressof(buf))
    return buf.value


def set_text(h, text):
    buf = ctypes.create_unicode_buffer(text)
    _send(h, WM_SETTEXT, 0, ctypes.addressof(buf))


def children(hwnd):
    out = []

    def cb(h, l):
        out.append(h)
        return True

    user32.EnumChildWindows(hwnd, ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)(cb), 0)
    return out


def force_foreground(hwnd):
    fg = user32.GetForegroundWindow()
    tfg = user32.GetWindowThreadProcessId(fg, None)
    tcur = kernel32.GetCurrentThreadId()
    if tfg != tcur:
        user32.AttachThreadInput(tcur, tfg, True)
    user32.ShowWindow(hwnd, 9)
    ok = user32.SetForegroundWindow(hwnd)
    if tfg != tcur:
        user32.AttachThreadInput(tcur, tfg, False)
    return bool(ok)


def _pid_of(name: str):
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True,
                             text=True, errors="replace", timeout=20).stdout
    except OSError:
        return None
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) > 1 and parts[0].lower().startswith(name.lower()):
            return int(parts[1])
    return None


# FireTuner2 相对于游戏安装目录父级（steamapps\common）的路径：
#   <steamapps\common>\Sid Meier's Civilization VI SDK\FireTuner\FireTuner2.exe
SDK_SUBDIR = os.path.join("Sid Meier's Civilization VI SDK", "FireTuner", "FireTuner2.exe")


def _firetuner_from_game_dir() -> str | None:
    """用自动探测到的游戏目录推导相邻的 SDK FireTuner 路径。"""
    try:
        game_dir = find_game_dir()
    except Exception:  # noqa: BLE001 - 探测异常按未命中处理，不阻断状态命令
        game_dir = None
    if not game_dir:
        return None
    return str(game_dir.parent / SDK_SUBDIR)


def find_firetuner_exe(exe: str | None = None) -> str | None:
    """定位 FireTuner2.exe。

    优先级：--exe → CIV6_FIRETUNER_EXE → 游戏目录旁 SDK 推导。
    显式覆盖的文件不存在时直接报错（避免静默用错路径）。
    """
    if exe:
        p = os.path.expanduser(os.path.expandvars(exe))
        if os.path.exists(p):
            return p
        raise RuntimeError("--exe 指定的 FireTuner2.exe 不存在: %s" % p)
    env_exe = os.environ.get("CIV6_FIRETUNER_EXE", "").strip().strip('"')
    if env_exe:
        p = os.path.expandvars(env_exe)
        if os.path.exists(p):
            return p
        raise RuntimeError("CIV6_FIRETUNER_EXE 指向的 FireTuner2.exe 不存在: %s" % p)
    cand = _firetuner_from_game_dir()
    return cand if cand and os.path.exists(cand) else None


def _firetuner_error() -> str:
    """找不到 FireTuner2 时区分"SDK 未安装"与"路径未覆盖"的提示。"""
    cand = _firetuner_from_game_dir()
    lines = [
        "找不到 FireTuner2.exe。",
        "已尝试：",
        "  - 游戏目录旁 SDK 推导: %s" % (cand or "未探测到游戏目录（无法推导）"),
    ]
    lines += [
        "常见原因：",
        "  1) SDK 可能未安装：需在 Steam 安装免费工具 “Sid Meier's Civilization VI Development Tools”"
        "（安装后 Steam 库目录下会有 Sid Meier's Civilization VI SDK\\FireTuner\\FireTuner2.exe）；",
        "  2) 路径未覆盖：SDK 装在其它 Steam 库或自定义位置时，用 --exe 指定 FireTuner2.exe，"
        "或设置 CIV6_FIRETUNER_EXE 环境变量（也可用 CIV6_GAME_DIR 指定游戏根目录以推导相邻 SDK）。",
    ]
    return "\n".join(lines)


def launch_firetuner(exe: str | None = None) -> int:
    if _pid_of("FireTuner2"):
        return _pid_of("FireTuner2")
    exe_path = find_firetuner_exe(exe)
    if not exe_path:
        raise RuntimeError(_firetuner_error())
    subprocess.Popen([exe_path], cwd=os.path.dirname(exe_path))
    time.sleep(5)
    return _pid_of("FireTuner2")


class FireTunerGUI:
    def __init__(self, pid: int | None = None):
        self.pid = pid or _pid_of("FireTuner2")
        self.hwnd = None
        self._find_main()

    def _find_main(self):
        if not self.pid:
            return
        found = []

        def cb(h, l):
            p = wt.DWORD()
            user32.GetWindowThreadProcessId(h, ctypes.byref(p))
            if p.value == self.pid and user32.IsWindowVisible(h) and win_text(h).startswith("Firaxis Live Tuner"):
                found.append(h)
                return False
            return True

        user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, wt.HWND, wt.LPARAM)(cb), 0)
        self.hwnd = found[0] if found else None

    # ---------- 控件 ----------
    def controls(self) -> dict:
        if not self.hwnd:
            return {}
        info = {"edit": None, "output": None, "combo": None}
        for h in children(self.hwnd):
            cls = win_class(h)
            if "RichEdit" in cls:
                info["output"] = h
            elif "COMBOBOX" in cls:
                info["combo"] = h
            elif "EDIT" in cls:
                info["edit"] = h
        return info

    def title(self) -> str:
        return win_text(self.hwnd) if self.hwnd else ""

    def connected(self) -> bool:
        return "civilization" in self.title().lower()

    def state(self) -> dict:
        c = self.controls()
        return {
            "pid": self.pid,
            "hwnd": self.hwnd,
            "title": self.title(),
            "connected": self.connected(),
            "combo": get_text(c["combo"]) if c.get("combo") else "",
            "output_tail": get_text(c["output"])[-1500:] if c.get("output") else "",
        }

    def combo_items(self) -> list[str]:
        c = self.controls()
        if not c.get("combo"):
            return []
        n = _send(c["combo"], CB_GETCOUNT)
        items = []
        for i in range(max(0, n)):
            buf = ctypes.create_unicode_buffer(512)
            _send(c["combo"], CB_GETLBTEXT, i, ctypes.addressof(buf))
            items.append(buf.value)
        return items

    def wait_connected(self, timeout: float = 120.0, poll: float = 2.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            self._find_main()
            if self.connected() and self.combo_items():
                return True
            time.sleep(poll)
        return False

    def make_front(self, width: int = 1180, height: int = 760) -> bool:
        if not self.hwnd:
            return False
        user32.SetWindowPos(self.hwnd, HWND_TOPMOST, 0, 0, width, height, SWP_SHOWWINDOW)
        time.sleep(0.3)
        ok = force_foreground(self.hwnd)
        time.sleep(0.2)
        rect = wt.RECT()
        user32.GetWindowRect(self.hwnd, ctypes.byref(rect))
        # 若前台化失败，点击标题栏（位于 0,0 后一定可见）
        if not ok:
            click((rect.left + rect.right) // 2, rect.top + 12)
            time.sleep(0.3)
        return user32.GetForegroundWindow() == self.hwnd

    # ---------- 操作 ----------
    def select_state(self, name: str) -> dict:
        items = self.combo_items()
        if name not in items:
            lower = [i for i, it in enumerate(items) if name.lower() in it.lower()]
            if not lower:
                return {"ok": False, "error": "state-not-found", "items": items}
            idx = lower[0]
        else:
            idx = items.index(name)
        c = self.controls()
        # 用 CB_SETCURSEL 直接选中：实测 Console 在执行时读取该组合框当前项，
        # 因此不需要模拟键盘展开下拉列表（更稳、更快）。
        _send(c["combo"], 0x014E, idx, 0)  # CB_SETCURSEL
        time.sleep(0.3)
        current = get_text(c["combo"])
        return {"ok": current == items[idx], "selected": current, "index": idx}

    def run_lua(self, code: str, timeout: float = 8.0) -> dict:
        c = self.controls()
        if not c.get("edit") or not c.get("output"):
            return {"ok": False, "error": "controls-missing"}
        before = get_text(c["output"])
        set_text(c["edit"], code)
        time.sleep(0.25)
        # 直接向输入框投递回车：不依赖全局焦点，实测最稳定
        user32.PostMessageW(c["edit"], 0x0100, VK_RETURN, 0x001C0001)  # WM_KEYDOWN
        time.sleep(0.06)
        user32.PostMessageW(c["edit"], 0x0101, VK_RETURN, 0xC01C0001)  # WM_KEYUP
        deadline = time.time() + timeout
        appended = ""
        while time.time() < deadline:
            time.sleep(0.25)
            after = get_text(c["output"])
            if len(after) > len(before):
                appended = after[len(before):]
                if "@@" in appended or "error" in appended.lower():
                    break
        return {"ok": True, "appended": appended,
                "output_tail": get_text(c["output"])[-800:],
                "state": get_text(c["combo"])}


def exec_lua(state: str, code: str, timeout: float = 8.0, exe: str | None = None) -> dict:
    gui = FireTunerGUI()
    if not gui.hwnd:
        launch_firetuner(exe)
        gui = FireTunerGUI()
    if not gui.wait_connected(timeout=30):
        return {"ok": False, "error": "firetuner-not-connected", "state": gui.state()}
    if not gui.make_front():
        pass
    sel = gui.select_state(state)
    res = gui.run_lua(code, timeout=timeout)
    res["select"] = sel
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="通过 FireTuner2 GUI 控制文明6")
    sub = ap.add_subparsers(dest="cmd", required=True)
    exe_common = argparse.ArgumentParser(add_help=False)
    exe_common.add_argument("--exe", default=None,
                            help="FireTuner2.exe 路径（默认自动探测游戏目录旁 SDK；"
                                 "也可设 CIV6_FIRETUNER_EXE / CIV6_GAME_DIR）")
    sub.add_parser("launch", parents=[exe_common])
    sub.add_parser("status")
    sub.add_parser("states")
    p = sub.add_parser("select")
    p.add_argument("--state", required=True)
    p = sub.add_parser("exec", parents=[exe_common])
    p.add_argument("--state", required=True)
    p.add_argument("--code")
    p.add_argument("--file")
    p.add_argument("--timeout", type=float, default=8.0)
    args = ap.parse_args(argv)

    if args.cmd == "launch":
        print("pid:", launch_firetuner(getattr(args, "exe", None)))
        return 0
    gui = FireTunerGUI()
    if args.cmd == "status":
        print(json.dumps(gui.state(), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "states":
        print(json.dumps(gui.combo_items(), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "select":
        print(json.dumps(gui.select_state(args.state), ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "exec":
        code = args.code
        if args.file:
            with open(args.file, encoding="utf-8") as f:
                code = f.read()
        if not code:
            print("需要 --code 或 --file", file=sys.stderr)
            return 2
        print(json.dumps(exec_lua(args.state, code, timeout=args.timeout,
                                  exe=getattr(args, "exe", None)),
                         ensure_ascii=False, indent=2))
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
