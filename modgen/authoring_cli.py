"""Offline adjacency references, inheritance review and description typography."""
import json
from pathlib import Path


def run_adjacency(args):
    from ModTools_5_4.project.adjacency_reference import reference, load_reference, audit_project
    if args.operation == 'show':
        result = reference(args.entity, args.ruleset)
    elif args.operation == 'list':
        data = load_reference()
        result = {'ruleset': args.ruleset, 'districts': data['profiles'][args.ruleset]['base_districts'],
                  'optional_base_districts': data['optional_base_districts'], 'scope': data['scope']}
    else:
        from .merger import load_civ
        result = audit_project(load_civ(Path(args.civ)), args.ruleset)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get('ok', True) else 1


def run_text(args):
    from ModTools_5_4.project.text_icons import check_text, audit_project
    if args.operation == 'check':
        from .merger import load_civ
        result = audit_project(load_civ(Path(args.civ)))
    else:
        text = args.text if args.text is not None else Path(args.file).read_text(encoding='utf-8-sig')
        result = check_text(text, args.role)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get('ok', True) else 1


def register(sub):
    parser = sub.add_parser('adjacency', help='原版相邻快照与特色区域继承差异检查（离线）')
    modes = parser.add_subparsers(dest='operation', required=True)
    for name in ('list', 'show', 'check'):
        command = modes.add_parser(name)
        command.add_argument('--ruleset', choices=('base', 'expansion1', 'expansion2'), default=None if name == 'check' else 'expansion2')
        if name == 'show': command.add_argument('entity')
        if name == 'check': command.add_argument('civ')
        command.set_defaults(func=run_adjacency)
    parser = sub.add_parser('text-icons', help='按文本角色补充描述图标或检查工程；不自动写回')
    modes = parser.add_subparsers(dest='operation', required=True)
    command = modes.add_parser('format')
    source = command.add_mutually_exclusive_group(required=True)
    source.add_argument('--text'); source.add_argument('--file')
    command.add_argument('--role', choices=('description', 'name', 'title'), default='description')
    command.set_defaults(func=run_text)
    command = modes.add_parser('check'); command.add_argument('civ'); command.set_defaults(func=run_text)
