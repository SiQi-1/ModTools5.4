#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""civ6_inject.py - 向正在运行的文明6注入 DLL（DLL Loader 类 Mod 的测试通道）。

背景（某台 Windows 11 机器实测；换机后以 --status 输出复核）：
- Civ6DllLoader 系 mod 的标准安装形态是把 Civ6DllLoader.runtime.dll 复制成
  游戏 exe 目录下的 version.dll（exe 静态导入它）。
- 实测发现游戏进程实际加载的是 %SystemRoot%\SYSTEM32\VERSION.dll，exe 目录里的
  version.dll 未被采用（把 version.dll 换成无效 DLL 后游戏仍能启动，证明
  app-local 未被加载）；因此 loader 日志与 exe\Civ6DllLoader 目录都不产生，
  DLL 插件 Mod 不会生效。
- 本脚本提供测试用 workaround：把 loader runtime 复制到游戏 exe 目录，然后
  CreateRemoteThread(LoadLibraryW) 注入。Loader 的 DllMain 要求模块目录等于
  宿主 exe 目录，且宿主是 CivilizationVI*.exe，注入后才肯启动。
- 注入仅用于本地验收；测试后要删除复制进 exe 目录的 runtime 和 loader 生成的
  Civ6DllLoader 子目录，恢复原始状态。

用法：
    python civ6_inject.py --dll "...\Civ6DllLoader.runtime.dll" --copy-to-game
    python civ6_inject.py --dll "...\SomePlugin.dll"      # 直接注入（不复制）
    python civ6_inject.py --status                       # 查看游戏进程/module
    python civ6_inject.py --remove Civ6DllLoader.runtime.dll

游戏 exe 目录默认经 civ6_game 自动探测 Steam 库；可用 --exe-dir 直接指定
Base\Binaries\Win64Steam，或设 CIV6_GAME_DIR 指向游戏安装根目录。

安全与限制：
- 只对 64 位 CivilizationVI / CivilizationVI_DX12 使用；
- 注入要等游戏窗口出现、进程稳定后再做，过早会命中 Steam 重启前的临时进程；
- 只用于单机测试，不要用于联机或分发。
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from civ6_game import find_game_dir  # noqa: E402  同目录模块：Steam 库自动探测

# 游戏 exe 相对于安装根目录的子目录
EXE_SUBDIR = os.path.join("Base", "Binaries", "Win64Steam")
PROCESS_NAMES = ("CivilizationVI_DX12.exe", "CivilizationVI.exe")


def find_game_exe_dir(exe_dir: str | None = None) -> str | None:
    """定位游戏 exe 目录（Base\\Binaries\\Win64Steam）。

    优先级：--exe-dir → CIV6_GAME_DIR（经 civ6_game.find_game_dir 探测/校验）。
    返回 None 时由调用方给出覆盖提示。
    """
    if exe_dir:
        p = os.path.expanduser(os.path.expandvars(exe_dir))
        return p if os.path.isdir(p) else None
    try:
        game_dir = find_game_dir()
    except Exception:  # noqa: BLE001 - 探测异常不应让 --status 等只读命令崩溃
        game_dir = None
    if game_dir:
        cand = os.path.join(str(game_dir), EXE_SUBDIR)
        if os.path.isdir(cand):
            return cand
    return None


def _exe_dir_error() -> str:
    """找不到 exe 目录时的提示（含覆盖方式）。"""
    env_dir = os.environ.get("CIV6_GAME_DIR", "").strip()
    tried = ["CIV6_GAME_DIR %s" % ("= " + env_dir if env_dir else "未设置")]
    return (
        "找不到游戏 exe 目录（Base\\Binaries\\Win64Steam）。\n"
        "已尝试：\n  - " + "\n  - ".join(tried) + "\n"
        "请用 --exe-dir 指定 exe 目录（如 ...\\Sid Meier's Civilization VI\\Base\\Binaries\\Win64Steam），"
        "或设置 CIV6_GAME_DIR 环境变量指向游戏根目录（如 ...\\Steam\\steamapps\\common\\Sid Meier's Civilization VI）。"
    )


def find_game_pid() -> int | None:
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True,
                             text=True, errors="replace", timeout=20).stdout
    except OSError:
        return None
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) > 1 and parts[0].lower() in [n.lower() for n in PROCESS_NAMES]:
            return int(parts[1])
    return None


def game_modules() -> list[str]:
    pid = find_game_pid()
    if not pid:
        return []
    ps = ("Get-Process -Id %d | Select-Object -ExpandProperty Modules | "
          "Select-Object -ExpandProperty FileName" % pid)
    try:
        out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, errors="replace", timeout=30).stdout
        return [ln.strip() for ln in out.splitlines() if ln.strip()]
    except OSError:
        return []


def inject(pid: int, dll_path: str) -> dict:
    dll_path = os.path.abspath(dll_path)
    if not os.path.exists(dll_path):
        raise FileNotFoundError(dll_path)
    k32 = ctypes.windll.kernel32
    k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
    k32.OpenProcess.restype = wt.HANDLE
    k32.VirtualAllocEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, wt.DWORD]
    k32.VirtualAllocEx.restype = ctypes.c_void_p
    k32.WriteProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                       ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
    k32.GetModuleHandleW.argtypes = [wt.LPCWSTR]
    k32.GetModuleHandleW.restype = wt.HMODULE
    k32.GetProcAddress.argtypes = [wt.HMODULE, wt.LPCSTR]
    k32.GetProcAddress.restype = ctypes.c_void_p
    k32.CreateRemoteThread.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t,
                                       ctypes.c_void_p, ctypes.c_void_p, wt.DWORD, ctypes.c_void_p]
    k32.CreateRemoteThread.restype = wt.HANDLE
    k32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
    k32.GetExitCodeThread.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]

    PROCESS_ALL_ACCESS = 0x1F0FFF
    h = k32.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
    if not h:
        raise RuntimeError("OpenProcess failed: %s" % ctypes.GetLastError())
    try:
        path_bytes = (dll_path + "\0").encode("utf-16-le")
        MEM_COMMIT_RESERVE = 0x3000
        PAGE_READWRITE = 0x04
        addr = k32.VirtualAllocEx(h, None, len(path_bytes), MEM_COMMIT_RESERVE, PAGE_READWRITE)
        if not addr:
            raise RuntimeError("VirtualAllocEx failed: %s" % ctypes.GetLastError())
        written = ctypes.c_size_t(0)
        if not k32.WriteProcessMemory(h, ctypes.c_void_p(addr), path_bytes,
                                      len(path_bytes), ctypes.byref(written)):
            raise RuntimeError("WriteProcessMemory failed: %s" % ctypes.GetLastError())
        load_lib = k32.GetProcAddress(k32.GetModuleHandleW("kernel32.dll"), b"LoadLibraryW")
        th = k32.CreateRemoteThread(h, None, 0, ctypes.c_void_p(load_lib),
                                    ctypes.c_void_p(addr), 0, None)
        if not th:
            raise RuntimeError("CreateRemoteThread failed: %s" % ctypes.GetLastError())
        k32.WaitForSingleObject(th, 15000)
        code = wt.DWORD(0)
        k32.GetExitCodeThread(th, ctypes.byref(code))
        return {"pid": pid, "dll": dll_path, "hmodule": int(code.value), "ok": code.value != 0}
    finally:
        k32.CloseHandle(h)


def copy_runtime_to_game(dll_path: str, exe_dir: str | None = None) -> str:
    exe_dir = exe_dir or find_game_exe_dir()
    if not exe_dir:
        raise RuntimeError(_exe_dir_error())
    dst = os.path.join(exe_dir, os.path.basename(dll_path))
    shutil.copy2(dll_path, dst)
    return dst


def remove_injected_runtime(name: str, exe_dir: str | None = None) -> str | None:
    exe_dir = exe_dir or find_game_exe_dir()
    if not exe_dir:
        return None
    p = os.path.join(exe_dir, name)
    if os.path.exists(p):
        os.remove(p)
        return p
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="向文明6注入 DLL（DLL Loader mod 测试用）")
    ap.add_argument("--dll", help="要注入的 DLL 路径")
    ap.add_argument("--copy-to-game", action="store_true",
                    help="先复制到游戏 exe 目录再注入（loader 需要模块目录==exe 目录）")
    ap.add_argument("--pid", type=int, help="指定进程 pid，默认自动查找游戏")
    ap.add_argument("--status", action="store_true", help="打印游戏进程与已加载模块")
    ap.add_argument("--remove", help="从游戏 exe 目录删除某个文件（清理注入的 runtime）")
    ap.add_argument("--exe-dir", default=None,
                    help="游戏 exe 目录（Base\\Binaries\\Win64Steam）；默认自动探测，"
                         "也可设 CIV6_GAME_DIR 指向游戏根目录")
    args = ap.parse_args(argv)

    if args.status:
        pid = find_game_pid()
        print("game_pid:", pid)
        mods = game_modules()
        print("modules:", len(mods))
        for m in mods:
            if "civilization" in m.lower() or "civ6dllloader" in m.lower() or m.lower().endswith("version.dll"):
                print("  ", m)
        return 0
    if args.remove:
        exe_dir = find_game_exe_dir(args.exe_dir)
        if not exe_dir:
            print(_exe_dir_error(), file=sys.stderr)
            return 4
        print("removed:", remove_injected_runtime(args.remove, exe_dir))
        return 0
    if not args.dll:
        print("需要 --dll", file=sys.stderr)
        return 2
    pid = args.pid or find_game_pid()
    if not pid:
        print("找不到 CivilizationVI 进程（先启动游戏并等窗口出现）", file=sys.stderr)
        return 3
    dll = args.dll
    if args.copy_to_game:
        exe_dir = find_game_exe_dir(args.exe_dir)
        if not exe_dir:
            print(_exe_dir_error(), file=sys.stderr)
            return 4
        dll = copy_runtime_to_game(dll, exe_dir)
        print("copied to:", dll)
    print("inject:", inject(pid, dll))
    return 0


if __name__ == "__main__":
    sys.exit(main())
