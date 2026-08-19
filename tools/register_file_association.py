"""注册/解除 .CIV 文件关联（双击用 ModTools 打开）。

用法：
    python tools/register_file_association.py            # 注册
    python tools/register_file_association.py --unregister  # 解除
    python tools/register_file_association.py --status     # 查看状态

说明：
- 写入 HKCU\\Software\\Classes（当前用户级，无需管理员权限）；
- 关联命令 = "<可执行文件>" "%1"（带引号，支持空格路径）；
- 源码运行（python）时注册到 python.exe + 本脚本入口；打包 exe 时注册到 exe 自身。
"""
from __future__ import annotations

import sys
import winreg
from pathlib import Path

EXTENSION = ".CIV"
PROG_ID = "ModTools5.4.CIV"


def target_command() -> str:
    """返回文件关联命令（可执行文件 + 入口脚本）。"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        exe = Path(sys.executable)
        return f'"{exe}" "%1"'
    root = Path(__file__).resolve().parent.parent
    entry = root / "ModTools5.4.py"
    python = Path(sys.executable)
    return f'"{python}" "{entry}" "%1"'


def register() -> str:
    command = target_command()
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{EXTENSION}") as key:
        winreg.SetValue(key, "", winreg.REG_SZ, PROG_ID)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{PROG_ID}\shell\open\command") as key:
        winreg.SetValue(key, "", winreg.REG_SZ, command)
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{PROG_ID}\DefaultIcon") as key:
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            winreg.SetValue(key, "", winreg.REG_SZ, f'"{sys.executable}",0')
    return command


def unregister() -> None:
    for sub in (rf"Software\Classes\{PROG_ID}", rf"Software\Classes\{EXTENSION}"):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
        except FileNotFoundError:
            pass


def status() -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{PROG_ID}\shell\open\command") as key:
            value, _ = winreg.QueryValueEx(key, "")
            return f"已注册 → {value}"
    except FileNotFoundError:
        return "未注册"


if __name__ == "__main__":
    if "--unregister" in sys.argv:
        unregister()
        print("已解除 .CIV 文件关联。")
    elif "--status" in sys.argv:
        print(status())
    else:
        command = register()
        print(f"已注册 .CIV 文件关联：\n{command}")
        print("现在可以双击 .CIV 文件直接打开（若资源管理器未刷新，重启 explorer 或注销重登）。")
