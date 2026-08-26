"""ModTools 5.4 一键初始化（新设备环境配置，供用户或 AI agent 执行）。

流程：
1. 检测 Python 版本（要求 >= 3.10）
2. 创建 .venv（如不存在）并安装 requirements.txt（PyQt6 + Pillow）
3. 探测数据库：游戏库（默认游戏 Cache 路径，找不到提示手动指定）、
   文本库（zip 自带 local_text_New.sqlite）→ 生成便携 settings.json（zip 根目录）
4. 验证：源码导入冒烟 + modgen 冒烟
5. 输出就绪报告与后续步骤（注册 .CIV 文件关联等）

用法：
    python tools/setup_env.py              # 全流程
    python tools/setup_env.py --check      # 仅检测环境并报告
    python tools/setup_env.py --game-db <路径>   # 手动指定游戏库
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

MIN_PYTHON = (3, 10)
ZIP_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = ZIP_ROOT / ".venv"
REQUIREMENTS = ZIP_ROOT / "requirements.txt"
SETTINGS_FILE = ZIP_ROOT / "settings.json"
TEXT_DB = ZIP_ROOT / "local_text_New.sqlite"

DEFAULT_GAME_DB = (
    Path.home()
    / "AppData/Local/Firaxis Games/Sid Meier's Civilization VI/Cache/DebugGameplay.sqlite"
)


def _venv_python() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def step_check_python() -> bool:
    version = sys.version_info[:2]
    ok = version >= MIN_PYTHON
    print(f"[1/5] Python 检测: {sys.version.split()[0]} {'✅' if ok else '❌（需 >= 3.10）'}")
    return ok


def step_create_venv() -> bool:
    if VENV_DIR.exists():
        print(f"[2/5] venv 已存在: {VENV_DIR}")
        return True
    print("[2/5] 创建 venv ...")
    result = subprocess.run(
        [sys.executable, "-m", "venv", str(VENV_DIR)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"      ❌ venv 创建失败: {result.stderr.strip()}")
        return False
    print("      ✅ venv 已创建")
    return True


def step_install_deps() -> bool:
    if not REQUIREMENTS.exists():
        print(f"[3/5] ❌ 未找到 {REQUIREMENTS}，跳过依赖安装")
        return False
    print("[3/5] 安装依赖（PyQt6 + Pillow）...")
    result = subprocess.run(
        [_venv_python(), "-m", "pip", "install", "-r", str(REQUIREMENTS)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"      ❌ 依赖安装失败: {result.stderr.strip()[-800:]}")
        return False
    print("      ✅ 依赖已安装")
    return True


def _probe_game_db() -> Path | None:
    """游戏库 Cache 永远在 %LOCALAPPDATA%，与游戏安装盘无关。"""
    if DEFAULT_GAME_DB.exists():
        return DEFAULT_GAME_DB
    return None


def step_configure_dbs(game_db_arg: str | None) -> bool:
    game_db: Path | None = None
    if game_db_arg:
        game_db = Path(game_db_arg)
        if not game_db.exists():
            print(f"[4/5] ❌ 指定的游戏库不存在: {game_db}")
            return False
    else:
        game_db = _probe_game_db()
        if game_db is None:
            print(
                "[4/5] ⚠️ 未在默认位置找到游戏库 DebugGameplay.sqlite\n"
                "      （游戏需至少运行过一次，或运行：python tools/setup_env.py --game-db <路径>）"
            )
            # 不阻断：游戏库缺失只影响导入/能力搜索，不影响编辑与生成
        else:
            print(f"[4/5] ✅ 游戏库: {game_db}")

    text_db = TEXT_DB if TEXT_DB.exists() else None
    if text_db is None:
        print("[4/5] ⚠️ 未找到 local_text_New.sqlite（zip 内应自带）")
    else:
        print(f"[4/5] ✅ 文本库: {text_db.name}")

    payload: dict[str, object] = {}
    if SETTINGS_FILE.exists():
        try:
            payload = json.loads(SETTINGS_FILE.read_text(encoding="utf-8-sig"))
        except Exception:
            payload = {}
    if game_db is not None:
        payload["game_db_path"] = str(game_db)
    if text_db is not None:
        payload["active_text_db_path"] = str(text_db)
        payload.setdefault("text_databases", [])
        if not any(
            isinstance(item, dict) and item.get("path") == str(text_db)
            for item in payload.get("text_databases", [])
        ):
            payload["text_databases"].append({"name": "内置中文文本库", "path": str(text_db)})
    SETTINGS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[4/5] ✅ 已生成便携配置: {SETTINGS_FILE}")
    return True


def step_verify() -> bool:
    python = _venv_python()
    ok = True
    print("[5/5] 验证 ...")
    result = subprocess.run(
        [str(python), "-c", "import PyQt6, PIL; print('PyQt6 + Pillow OK')"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"      ❌ 依赖导入失败: {result.stderr.strip()[-500:]}")
        ok = False
    else:
        print(f"      ✅ {result.stdout.strip()}")

    result = subprocess.run(
        [str(python), "-m", "modgen.cli", "generate", "区域", "--name", "测试", "--abbr", "T", "--prefix", "X", "--infix", "1"],
        capture_output=True,
        text=True,
        cwd=str(ZIP_ROOT),
    )
    if result.returncode != 0 or "type" not in result.stdout:
        print("      ❌ modgen 冒烟失败")
        ok = False
    else:
        print("      ✅ modgen 可用")
    return ok


def report() -> None:
    python = _venv_python()
    print()
    print("=" * 60)
    print("初始化就绪。使用方式：")
    print(f"  启动编辑器 : {python} ModTools5.4.py   （或双击 ModTools5.4.exe）")
    print(f"  AI 生成 CIV: python -m modgen.cli generate <分类> ...（见 modgen/AGENTS.md）")
    print(f"  能力查询   : python -m modgen.cli search <效果词>")
    print("  注册 .CIV 双击打开: python tools/register_file_association.py")
    print("=" * 60)


def main() -> int:
    parser = argparse.ArgumentParser(description="ModTools 5.4 一键初始化")
    parser.add_argument("--check", action="store_true", help="仅检测环境并报告，不执行安装")
    parser.add_argument("--game-db", default="", help="手动指定游戏库 DebugGameplay.sqlite 路径")
    args = parser.parse_args()

    if args.check:
        step_check_python()
        print(f"venv: {'存在' if VENV_DIR.exists() else '不存在'}")
        print(f"游戏库: {DEFAULT_GAME_DB if DEFAULT_GAME_DB.exists() else '未找到（默认位置）'}")
        print(f"文本库: {'存在' if TEXT_DB.exists() else '缺失'}")
        print(f"配置: {SETTINGS_FILE if SETTINGS_FILE.exists() else '未生成'}")
        return 0

    steps = [
        ("Python 检测", step_check_python),
        ("创建 venv", step_create_venv),
        ("安装依赖", step_install_deps),
        ("配置数据库", lambda: step_configure_dbs(args.game_db or None)),
        ("验证", step_verify),
    ]
    failed = False
    for name, func in steps:
        try:
            if not func():
                failed = True
                print(f"步骤「{name}」失败，后续步骤可能不可用。")
        except Exception as exc:  # noqa: BLE001
            failed = True
            print(f"步骤「{name}」异常: {exc}")
    if failed:
        print("\n存在未完成步骤，请根据上方提示处理（常见：Python 未装/游戏库未生成）。")
        return 1
    report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
