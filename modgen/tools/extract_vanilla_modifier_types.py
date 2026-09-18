"""从游戏自带 XML 提取「原版 ModifierType 快照」。

为什么要这个快照（背景）：
    ModifierType 是否为「游戏已有类型」过去是靠查询本机运行缓存
    ``DebugGameplay.sqlite`` 的 ``DynamicModifiers`` 表判断的。该缓存会把
    **玩家装过的所有 Mod 注册的类型**一起带进来（实测本机 1024 条里有 51 条
    是作者自己 Mod 留下的），于是「库里已有」被误判成「原版已有」，
    生成时就不补 ``Types`` / ``DynamicModifiers`` 行 —— 换一台没装那个 Mod 的
    机器加载直接失败。本脚本改为从**游戏自己的数据文件**提取权威原版清单，
    与「本机装过什么 Mod」彻底解耦，导出结果可复现。

数据源：
    ``<游戏目录>/{Base,DLC,CTP,Debug,LaunchPad}/**/*.xml`` 中的
    ``<DynamicModifiers><Row>`` 块（官方 Base + 全部 DLC/资料片）。

用法：
    python -m modgen.tools.extract_vanilla_modifier_types
    python -m modgen.tools.extract_vanilla_modifier_types --game-dir "E:/SteamLibrary/steamapps/common/Sid Meier's Civilization VI"
    python -m modgen.tools.extract_vanilla_modifier_types --out ModTools_5_4/data/vanilla_modifier_types.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUT = REPO_ROOT / "ModTools_5_4" / "data" / "vanilla_modifier_types.json"

SCAN_SUBDIRS = ("Base", "DLC", "CTP", "Debug", "LaunchPad")
GAME_DIR_NAME = "Sid Meier's Civilization VI"
MARKER = Path("Base") / "Assets" / "Gameplay" / "Data" / "Modifiers.xml"


def _steam_roots_from_registry() -> list[Path]:
    roots: list[Path] = []
    try:
        import winreg  # type: ignore[import-not-found]
    except ImportError:
        return roots
    for hive, key in (
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
    ):
        try:
            with winreg.OpenKey(hive, key) as handle:
                for value_name in ("SteamPath", "InstallPath"):
                    try:
                        value, _ = winreg.QueryValueEx(handle, value_name)
                    except OSError:
                        continue
                    text = str(value or "").strip()
                    if text:
                        roots.append(Path(text))
        except OSError:
            continue
    return roots


def _library_paths(steam_root: Path) -> list[Path]:
    """解析 steamapps/libraryfolders.vdf 里的库目录。"""
    found: list[Path] = [steam_root]
    for vdf in (steam_root / "steamapps" / "libraryfolders.vdf",
                steam_root / "config" / "libraryfolders.vdf"):
        if not vdf.is_file():
            continue
        try:
            text = vdf.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for match in re.finditer(r'"path"\s+"([^"]+)"', text):
            raw = match.group(1).replace("\\\\", "\\")
            if raw:
                found.append(Path(raw))
    return found


def _candidate_game_dirs() -> list[Path]:
    candidates: list[Path] = []

    env_dir = str(os.environ.get("CIV6_GAME_DIR") or "").strip()
    if env_dir:
        candidates.append(Path(env_dir))

    for steam_root in _steam_roots_from_registry():
        for library in _library_paths(steam_root):
            candidates.append(library / "steamapps" / "common" / GAME_DIR_NAME)

    for drive in ("C", "D", "E", "F", "G"):
        candidates.append(Path("%s:/Program Files (x86)/Steam/steamapps/common" % drive) / GAME_DIR_NAME)
        candidates.append(Path("%s:/Steam/steamapps/common" % drive) / GAME_DIR_NAME)
        candidates.append(Path("%s:/SteamLibrary/steamapps/common" % drive) / GAME_DIR_NAME)
        candidates.append(Path("%s:/Games/Steam/steamapps/common" % drive) / GAME_DIR_NAME)

    unique: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def find_game_dir(explicit: str = "") -> Path | None:
    if explicit:
        path = Path(explicit)
        return path if (path / MARKER).is_file() else None
    for candidate in _candidate_game_dirs():
        if (candidate / MARKER).is_file():
            return candidate
    return None


def extract(game_dir: Path) -> dict[str, list[str]]:
    rows: dict[str, list[str]] = {}
    for sub in SCAN_SUBDIRS:
        base = game_dir / sub
        if not base.is_dir():
            continue
        for xml in sorted(base.rglob("*.xml")):
            try:
                root = ElementTree.parse(xml).getroot()
            except (ElementTree.ParseError, OSError):
                continue
            for block in root.iter("DynamicModifiers"):
                for row in block.findall("Row"):
                    modifier_type = (row.findtext("ModifierType") or "").strip()
                    if not modifier_type:
                        continue
                    collection = (row.findtext("CollectionType") or "").strip()
                    effect = (row.findtext("EffectType") or "").strip()
                    rows.setdefault(modifier_type, [collection, effect])
    return dict(sorted(rows.items()))


def build_payload(game_dir: Path, types: dict[str, list[str]]) -> dict[str, object]:
    return {
        "format": "MODTOOLS54_VANILLA_MODIFIER_TYPES",
        "version": 1,
        "source": "Civ6 官方 XML（Base/DLC/CTP/Debug/LaunchPad 的 <DynamicModifiers><Row>）",
        "game_dir": str(game_dir),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(types),
        "modifier_types": types,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="提取原版 ModifierType 快照（从游戏自带 XML）")
    parser.add_argument("--game-dir", default="", help="文明6 安装目录（缺省自动探测）")
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="输出 JSON 路径")
    parser.add_argument("--json", action="store_true", help="结果以 JSON 打印到 stdout")
    args = parser.parse_args(argv)

    game_dir = find_game_dir(args.game_dir)
    if game_dir is None:
        print(
            "未找到文明6安装目录。请用 --game-dir 指定，或设置环境变量 CIV6_GAME_DIR。\n"
            "（判定标记：<游戏目录>/Base/Assets/Gameplay/Data/Modifiers.xml）",
            file=sys.stderr,
        )
        return 2

    types = extract(game_dir)
    if not types:
        print("未从 %s 提取到任何 DynamicModifiers 行。" % game_dir, file=sys.stderr)
        return 3

    payload = build_payload(game_dir, types)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    if args.json:
        print(json.dumps({"ok": True, "out": str(out_path), "count": len(types),
                          "game_dir": str(game_dir)}, ensure_ascii=False))
    else:
        print("已写入：%s" % out_path)
        print("原版 ModifierType 条数：%d" % len(types))
        print("游戏目录：%s" % game_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
