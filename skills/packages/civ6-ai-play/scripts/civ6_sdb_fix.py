#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""civ6_sdb_fix.py - 修复 Windows 11 兼容性数据库导致文明6无法加载 exe 目录 version.dll 的问题。

背景（2026-10 实测）：
  Windows 的兼容性数据库给 CivilizationVI_DX12.exe 施加了 DXGICompat 修复。该修复在进程
  启动早期加载 AcGenral 兼容层，AcGenral 会从 system32 抢先加载 VERSION.dll，导致游戏 exe
  目录里的 version.dll（Civ6DllLoader 代理）永远不会被加载。
  本脚本把 %SystemRoot%\apppatch\MergeSdbFilesSource\sysMerge.sdb 里所有文明6相关的匹配名
  替换为同长度占位名，使该兼容性修复不再命中；改完标准安装的 version.dll 即可正常加载。

警告：
  - 这会修改 Windows 系统文件（sysMerge.sdb）。脚本会先备份原文件到
    %LOCALAPPDATA%\civ6_ai_play\sdb_backup，并保存/恢复原始 ACL。
  - 需要管理员权限。Windows 更新可能覆盖 sysMerge.sdb，更新后请重新 apply。
  - 只改 sysMerge.sdb；DirectXApps.sdb / sysmain.sdb 中也有同类条目，但实测不需要改。
  - 只影响文明6的兼容性匹配，不改游戏文件、不改注册表。

用法：
  python civ6_sdb_fix.py status
  python civ6_sdb_fix.py apply --yes
  python civ6_sdb_fix.py restore --yes
  python civ6_sdb_fix.py verify                    # 默认自动探测 DX12 主程序
  python civ6_sdb_fix.py verify --game-exe "<游戏根>\Base\Binaries\Win64Steam\CivilizationVI_DX12.exe"
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from civ6_game import EXE_DX11, EXE_DX12, find_game_dir  # noqa: E402  同目录模块：游戏目录探测


def _default_sdb_path() -> Path:
    """sysMerge.sdb 路径：优先 %SystemRoot%（系统盘不一定是 C:），保留 C:\\Windows 回退。"""
    primary = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "apppatch" / "MergeSdbFilesSource" / "sysMerge.sdb"
    fallback = Path(r"C:\Windows\apppatch\MergeSdbFilesSource\sysMerge.sdb")
    if not primary.exists() and fallback.exists():
        return fallback
    return primary


SDB = _default_sdb_path()
STATE_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "civ6_ai_play" / "sdb_backup"
BACKUP = STATE_DIR / "sysMerge.sdb.orig"
BACKUP_SDDL = STATE_DIR / "sysMerge.sdb.orig.sddl.txt"

LOADER_LOG = Path(os.environ.get("LOCALAPPDATA", "")) / "Firaxis Games" / "Sid Meier's Civilization VI" / "Logs" / "Civ6DllLoader_Loader.log"


def resolve_game_exe(game_exe: str | None = None) -> Path:
    """定位 verify 用的游戏主程序（DX12）。

    优先级：--game-exe → CIV6_GAME_EXE → CIV6_GAME_DIR（经 civ6_game.find_game_dir）。
    找不到时抛 RuntimeError 并附覆盖提示。
    """
    for value, label in ((game_exe, "--game-exe 指定"),
                         (os.environ.get("CIV6_GAME_EXE", "").strip().strip('"'), "CIV6_GAME_EXE 指定")):
        if value:
            p = Path(os.path.expanduser(os.path.expandvars(str(value))))
            if p.is_file():
                return p
            raise RuntimeError("%s的文件不存在: %s" % (label, p))
    try:
        game_dir = find_game_dir()
    except Exception:  # noqa: BLE001 - 探测异常按未命中处理，不阻断错误提示
        game_dir = None
    if game_dir:
        p = game_dir / EXE_DX12
        if p.exists():
            return p
        if (game_dir / EXE_DX11).exists():
            raise RuntimeError("未找到 DX12 主程序: %s；该安装只有 DX11 版本，"
                               "verify 需要 CivilizationVI_DX12.exe（可用 --game-exe 指定）" % p)
    raise RuntimeError(
        "找不到游戏主程序 CivilizationVI_DX12.exe。\n"
        "请用 --game-exe 指定 exe 路径，或设置 CIV6_GAME_DIR（游戏根目录）/"
        "CIV6_GAME_EXE（exe 路径）环境变量。"
        + ("" if game_dir is None else "\n当前探测到的游戏目录: %s" % game_dir)
    )


# 原文与同长度占位名（只替换匹配名，不动其它数据）
PAIRS = [
    ("civ6_win64_dx12_release.exe", "civ6_win64_dx99_release.exe"),
    ("civilizationvi_dx12.exe", "civilizationvi_dx99.exe"),
    ("Civilizationvi_dx12.exe", "Civilizationvi_dx99.exe"),
    ("CivilizationVI.exe", "CivilizationVX.exe"),
]

k32 = ctypes.windll.kernel32
k32.MoveFileExW.argtypes = [wt.LPCWSTR, wt.LPCWSTR, wt.DWORD]
k32.MoveFileExW.restype = wt.BOOL


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_ps(cmd: str, timeout: int = 60) -> str:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", cmd],
        capture_output=True, text=True, errors="replace", timeout=timeout,
    ).stdout


def current_sddl(path: Path) -> str:
    return run_ps("(Get-Acl -LiteralPath '%s').Sddl" % str(path)).strip()


def set_sddl(path: Path, sddl: str) -> None:
    if not sddl:
        return
    ps = (
        "$acl=New-Object System.Security.AccessControl.FileSecurity;"
        "$acl.SetSecurityDescriptorSddlForm('%s');"
        "Set-Acl -LiteralPath '%s' -AclObject $acl"
        % (sddl.replace("'", "''"), str(path))
    )
    run_ps(ps)


def counts(data: bytes) -> dict:
    return {old: data.count(old.encode("utf-16-le")) for old, _ in PAIRS}


def patched_counts(data: bytes) -> dict:
    return {new: data.count(new.encode("utf-16-le")) for _, new in PAIRS}


def write_via_movefile(path: Path, data: bytes) -> str:
    tmp = Path(tempfile.gettempdir()) / (path.name + ".civ6fix.tmp")
    tmp.write_bytes(data)
    if k32.MoveFileExW(str(tmp), str(path), 0x1 | 0x8):
        return "MoveFileEx"
    err = ctypes.get_last_error()
    try:
        with open(path, "r+b") as f:
            f.write(data)
            f.truncate()
        tmp.unlink(missing_ok=True)
        return "in-place"
    except OSError as exc:
        raise RuntimeError("写入失败: MoveFileEx err=%d, in-place %r" % (err, exc))


def ensure_backup() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not BACKUP.exists():
        raise RuntimeError("缺少原始备份: %s（无法安全 apply/restore，请先确认系统状态）" % BACKUP)
    if not BACKUP_SDDL.exists():
        raise RuntimeError("缺少原始 ACL 备份: %s" % BACKUP_SDDL)


def status() -> dict:
    info = {
        "admin": is_admin(),
        "sdb": str(SDB),
        "exists": SDB.exists(),
        "backup": str(BACKUP),
        "backup_exists": BACKUP.exists(),
    }
    if SDB.exists():
        data = SDB.read_bytes()
        info["sha256"] = sha256(SDB)
        info["original_names"] = counts(data)
        info["placeholder_names"] = patched_counts(data)
        info["patched"] = all(v == 0 for v in info["original_names"].values()) and any(v > 0 for v in info["placeholder_names"].values())
        info["acl_sddl"] = current_sddl(SDB)
    if BACKUP.exists():
        info["backup_sha256"] = sha256(BACKUP)
    return info


def apply(force: bool = False) -> dict:
    if not is_admin():
        raise RuntimeError("需要管理员权限（右键以管理员身份运行 PowerShell）")
    if not SDB.exists():
        raise RuntimeError("找不到 sysMerge.sdb")
    data = SDB.read_bytes()
    if all(v == 0 for v in counts(data).values()):
        return {"result": "already-applied", "status": status()}
    ensure_backup()
    old_sddl = current_sddl(SDB)
    if not BACKUP_SDDL.exists():
        BACKUP_SDDL.write_text(old_sddl, encoding="utf-8")
    before = counts(data)
    new_data = data
    for old, new in PAIRS:
        ob = old.encode("utf-16-le")
        nb = new.encode("utf-16-le")
        if len(ob) != len(nb):
            raise RuntimeError("占位名长度不一致: %s" % old)
        new_data = new_data.replace(ob, nb)
    method = write_via_movefile(SDB, new_data)
    set_sddl(SDB, old_sddl)
    res = {
        "result": "patched",
        "method": method,
        "replacements": before,
        "status": status(),
    }
    (STATE_DIR / "apply_log.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    return res


def restore() -> dict:
    if not is_admin():
        raise RuntimeError("需要管理员权限")
    ensure_backup()
    old_sddl = BACKUP_SDDL.read_text(encoding="utf-8").strip()
    method = write_via_movefile(SDB, BACKUP.read_bytes())
    set_sddl(SDB, old_sddl)
    return {
        "result": "restored",
        "method": method,
        "restored_sha_matches": sha256(SDB) == sha256(BACKUP),
        "status": status(),
    }


def verify(game_exe: str | None = None) -> dict:
    exe = resolve_game_exe(game_exe)
    log = LOADER_LOG
    try:
        if log.exists():
            log.unlink()
    except OSError:
        pass
    env = dict(os.environ)
    env.update({"SteamAppId": "289070", "SteamGameId": "289070", "SteamClientLaunch": "1"})
    subprocess.Popen([str(exe)], cwd=str(exe.parent), env=env,
                     creationflags=getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
                     close_fds=True)
    time.sleep(12)
    pid = None
    out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, errors="replace").stdout
    for line in out.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) > 1 and parts[0].lower() == "civilizationvi_dx12.exe":
            pid = int(parts[1])
            break
    res = {"pid": pid}
    if pid:
        mods = run_ps("Get-Process -Id %d | Select-Object -ExpandProperty Modules | ForEach-Object { $_.FileName }" % pid)
        files = [m.strip() for m in mods.splitlines() if m.strip()]
        vers = [m for m in files if os.path.basename(m).lower() == "version.dll"]
        res["version_modules"] = vers
        res["app_local_loader_loaded"] = any("win64steam" in m.lower() for m in vers)
        res["acgenral"] = any("acgenral" in os.path.basename(m).lower() for m in files)
    res["loader_log_exists"] = log.exists()
    if log.exists():
        text = log.read_text(encoding="utf-8", errors="replace").splitlines()
        res["loader_log_tail"] = text[-5:]
    if pid:
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
    return res


def main() -> int:
    ap = argparse.ArgumentParser(description="修复 Windows 兼容性数据库对文明6 version.dll 的抢占")
    sub = ap.add_subparsers(dest="action", required=True)
    sub.add_parser("status", help="查看当前 SDB 状态与备份")
    p_apply = sub.add_parser("apply", help="打补丁（修改 sysMerge.sdb，需管理员）")
    p_apply.add_argument("--yes", action="store_true", help="确认修改系统文件")
    p_restore = sub.add_parser("restore", help="还原原始 sysMerge.sdb，需管理员")
    p_restore.add_argument("--yes", action="store_true", help="确认还原系统文件")
    p_verify = sub.add_parser("verify", help="启动游戏，检查 exe 目录 VERSION.dll 与 loader 日志")
    p_verify.add_argument("--game-exe", default=None,
                          help="文明6 主程序路径（默认自动探测 DX12 exe；也可设 "
                               "CIV6_GAME_EXE / CIV6_GAME_DIR）")
    args = ap.parse_args()
    if args.action == "status":
        print(json.dumps(status(), ensure_ascii=False, indent=1))
        return 0
    if args.action == "apply":
        if not args.yes:
            print("拒绝执行：修改 Windows 系统文件需要显式传入 --yes")
            return 2
        print(json.dumps(apply(), ensure_ascii=False, indent=1))
        return 0
    if args.action == "restore":
        if not args.yes:
            print("拒绝执行：还原 Windows 系统文件需要显式传入 --yes")
            return 2
        print(json.dumps(restore(), ensure_ascii=False, indent=1))
        return 0
    if args.action == "verify":
        print(json.dumps(verify(getattr(args, "game_exe", None)), ensure_ascii=False, indent=1))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
