"""modgen CLI：generate / validate / merge。

用法：
    python -m modgen.cli generate <分类> --name 中文名 --abbr 简称 [--prefix 前缀] [--infix 编号] [--desc 描述]
    python -m modgen.cli validate <工程.CIV> [--prefix 前缀] [--infix 编号]
    python -m modgen.cli merge <工程.CIV> <分类> --entry entry.json [--no-validate]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import rules
from .generator import (
    generate_agenda,
    generate_entry,
    generate_great_person,
    generate_promotion_tree,
    required_fields_to_fill,
)
from .merger import load_civ, merge_entry, save_civ
from .validator import check_entry, validate_project


def _parse_json_list(raw: str | None) -> list[dict[str, Any]]:
    if not raw:
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("--json 参数需要 JSON 数组")
    return [item for item in data if isinstance(item, dict)]


def _cmd_generate(args: argparse.Namespace) -> int:
    if args.section == "伟人":
        entry = generate_great_person(
            prefix=args.prefix,
            infix=args.infix,
            name=args.name,
            class_abbr=args.abbr,
            unit_abbr=args.unit_abbr,
            individuals=_parse_json_list(args.individuals),
        )
    elif args.section == "单位晋升":
        entry = generate_promotion_tree(
            prefix=args.prefix,
            infix=args.infix,
            name=args.name,
            tree_abbr=args.abbr,
            nodes=_parse_json_list(args.nodes),
        )
    elif args.section == "议程":
        entry = generate_agenda(
            prefix=args.prefix,
            infix=args.infix,
            name=args.name,
            agenda_abbr=args.abbr,
            description=args.desc,
            leader_abbr=args.leader_abbr,
        )
    else:
        entry = generate_entry(
            args.section,
            prefix=args.prefix,
            infix=args.infix,
            name=args.name,
            abbr=args.abbr,
            description=args.desc,
        )
    print(json.dumps(entry, ensure_ascii=False, indent=2))
    required = required_fields_to_fill(args.section)
    if required:
        print(f"# 待填必填字段（无默认值，需手动填写）：{', '.join(required)}", file=sys.stderr)
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    if args.entry:
        data = json.loads(Path(args.entry).read_text(encoding="utf-8"))
        errors, warnings = check_entry(args.section, data, prefix=args.prefix, infix=args.infix)
    else:
        payload = load_civ(Path(args.civ))
        errors = validate_project(payload, prefix=args.prefix, infix=args.infix)
        warnings = []
    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK: 校验通过")
    return 0


def _cmd_merge(args: argparse.Namespace) -> int:
    payload = load_civ(Path(args.civ))
    entry = json.loads(Path(args.entry).read_text(encoding="utf-8"))
    merge_entry(
        payload,
        args.section,
        entry,
        prefix=args.prefix,
        infix=args.infix,
        validate=not args.no_validate,
    )
    save_civ(Path(args.civ), payload)
    print(f"已合并到 {args.civ}（自动备份 .bak）")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="modgen", description="文明6 Mod 工程(.CIV)生成与校验工具")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="生成合规条目 JSON")
    gen.add_argument("section", choices=rules.CONTENT_SECTIONS, help="分类")
    gen.add_argument("--name", required=True, help="中文名")
    gen.add_argument("--abbr", default="", help="英文简称（生成 Type 用；伟人=类别简称，晋升树=树简称，议程=议程简称）")
    gen.add_argument("--prefix", default="", help="工程前缀（如 SIQI）")
    gen.add_argument("--infix", type=int, default=0, help="工程中缀编号（如 35）")
    gen.add_argument("--desc", default="", help="中文描述")
    gen.add_argument("--unit-abbr", default="", help="伟人：对应单位简称")
    gen.add_argument("--individuals", default="", help="伟人：个体 JSON 数组，如 [{\"mode\":\"activation\",\"abbr\":\"NEWTON\",\"name_cn\":\"牛顿\"}]")
    gen.add_argument("--nodes", default="", help="单位晋升：节点 JSON 数组，如 [{\"abbr\":\"A\",\"name_cn\":\"晋升一\"}]")
    gen.add_argument("--leader-abbr", default="", help="议程：绑定领袖简称")
    gen.set_defaults(func=_cmd_generate)

    val = sub.add_parser("validate", help="校验条目或整个工程")
    val.add_argument("civ", nargs="?", help="工程 .CIV 路径（校验工程时）")
    val.add_argument("--section", choices=rules.CONTENT_SECTIONS, help="分类（校验单条目时）")
    val.add_argument("--entry", help="条目 JSON 文件（校验单条目时）")
    val.add_argument("--prefix", default="", help="工程前缀")
    val.add_argument("--infix", type=int, default=0, help="工程中缀编号")
    val.set_defaults(func=_cmd_validate)

    merge = sub.add_parser("merge", help="合并条目进工程")
    merge.add_argument("civ", help="工程 .CIV 路径")
    merge.add_argument("section", choices=rules.CONTENT_SECTIONS, help="分类")
    merge.add_argument("--entry", required=True, help="条目 JSON 文件")
    merge.add_argument("--prefix", default="", help="工程前缀")
    merge.add_argument("--infix", type=int, default=0, help="工程中缀编号")
    merge.add_argument("--no-validate", action="store_true", help="跳过校验")
    merge.set_defaults(func=_cmd_merge)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
