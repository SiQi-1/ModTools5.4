"""CLI adapters for shared read-only resource checks."""
import json

from ModTools_5_4.project.asset_checks import (
    check_assets, check_audio, compare_art, check_workshop,
)


def run(args):
    if args.resource_command == "assets":
        result = check_assets(args.target, cooker_config=args.cooker_config)
    elif args.resource_command == "audio":
        result = check_audio(args.target)
    elif args.resource_command == "art":
        result = compare_art(args.source, args.target, suffixes=args.suffix)
    else:
        result = check_workshop(args.target, modinfo=args.modinfo)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['kind']}: {'无静态错误' if result['ok'] else '发现错误'}")
        for level, title in (("errors", "ERROR"), ("warnings", "WARNING"), ("unverified", "未验证")):
            for item in result[level]:
                print(f"{title}: {item.get('file', '')} {item['message']}")
        for item in result.get("comparisons", []):
            print(f"{item['status']}: {item['file']}")
    return 0 if result["ok"] else 1


def register(subparsers):
    for name, operation, help_text in (
        ("assets", "check", "只读检查工程与美术资源引用"),
        ("audio", "check", "只读检查 UpdateAudio/INI/BNK/流式 WEM"),
        ("art", "compare", "比较美术 XML 源文件与 Cooker 产物"),
        ("workshop", "check", "只读检查工坊 workspace，不连接 Steam"),
    ):
        parser = subparsers.add_parser(name, help=help_text)
        child = parser.add_subparsers(required=True).add_parser(operation)
        if name == "art":
            child.add_argument("source", help="源美术目录")
            child.add_argument("--suffix", action="append", help="要比较的 XML 后缀，可重复；默认 .artdef")
        child.add_argument("target", help="工程文件、产物目录或工坊 workspace")
        child.add_argument("--json", action="store_true", help="结构化报告，含未验证项")
        if name == "assets":
            child.add_argument("--cooker-config", help="可选：目标 SDK 的 Civ6.cfg，只读核对 XLP/AST/GEO/TEX 类关系")
        if name == "workshop":
            child.add_argument("--modinfo", help="相对于 content 的 .modinfo 路径")
        child.set_defaults(func=run, resource_command=name)
