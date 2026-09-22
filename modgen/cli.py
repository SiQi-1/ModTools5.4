"""modgen CLI：generate / validate / merge / search / new-project / civ6proj / custom-file / query / loc / preview。

用法：
    python -m modgen.cli generate <分类> --name 中文名 --abbr 简称 [--prefix 前缀] [--infix 编号] [--desc 描述]
    python -m modgen.cli validate <工程.CIV> [--prefix 前缀] [--infix 编号]
    python -m modgen.cli merge <工程.CIV> <分类|修改器> --entry entry.json [--kind 类型] [--no-validate]
    python -m modgen.cli search <关键词> [--object] [--detail] [--game-db 路径] [--text-db 路径]
    python -m modgen.cli skill <关键词> [--file 相对路径] [--limit N]   # 本地技能库全文检索
    python -m modgen.cli new-project <输出.CIV> [--name 中文名] [--prefix 前缀] [--infix 编号] [--file-name 文件名]
    python -m modgen.cli civ6proj <工程.CIV> [--out 目录] [--update-civ]
    python -m modgen.cli custom-file write <工程.CIV> --path <相对路径> [--content 文本 | --content-file 文件] [--action 类型] [--no-action]
    python -m modgen.cli custom-file list <工程.CIV>
    python -m modgen.cli custom-file remove <工程.CIV> --path <相对路径> [--keep-file]
    python -m modgen.cli check-conflicts <工程.CIV> [--json]   # 自定义 SQL × 生成 SQL 冲突检测
    python -m modgen.cli query "SELECT ..." [--json] [--limit N] [--game-db 路径]
    python -m modgen.cli loc <LOC_TAG> [LOC_TAG ...] [--text-db 路径]
    python -m modgen.cli preview <工程.CIV> [--section 分类] [--format sql|xml] [--out 目录]
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

from . import rules
from . import mt_bridge
from .custom_file import (
    CustomFileError,
    list_custom_files,
    remove_custom_file,
    write_custom_file,
)
from .dbquery import (
    QueryError,
    format_loc_results,
    format_query_result,
    open_game_db_readonly,
    resolve_game_db_path,
    resolve_loc_tag,
    resolve_text_db_path,
    run_query,
)
from .generator import (
    generate_agenda,
    generate_entry,
    generate_great_person,
    generate_promotion_tree,
    required_fields_to_fill,
)
from .merger import load_civ, merge_entry, save_civ
from .modifier_generator import (
    generate_ability,
    generate_modifier,
    generate_requirement,
    generate_requirement_set,
)
from .modifier_merger import merge_modifier_file
from .preview import (
    PreviewError,
    build_preview_files,
    preview_section,
    safe_out_dir_name,
    write_preview_files,
)
from .project_scaffold import create_new_project_file
from .search import object_modifier_summary, resolve_db_paths, search_keyword
from .skills import read_skill_file, search_skills
from .validator import check_entry, validate_project

SEARCH_HINT = (
    "提示：不确定效果怎么做时，先用 `python -m modgen.cli search <效果词>` 查游戏里现成的实现，"
    "再照抄（不要凭记忆断言某效果不存在）。"
)


def _cmd_skill(args: argparse.Namespace) -> int:
    """skill：本地技能库（仓库根 skills/）全文检索。"""
    from pathlib import Path as _Path

    root = _Path(args.skills_dir) if args.skills_dir else None
    if root is not None and not root.exists():
        print(f"ERROR: 技能库目录不存在：{root}", file=sys.stderr)
        return 1
    if args.file:
        content = read_skill_file(args.file, root=root)
        if content is None:
            print(f"ERROR: 技能文件不存在或路径非法：{args.file}", file=sys.stderr)
            return 1
        print(content.rstrip("\n"))
        return 0
    results = search_skills(args.keyword, root=root, limit=args.limit)
    if not results:
        print(f"未在技能库中找到与「{args.keyword}」相关的内容。")
        print("提示：试英文关键词/表名（如 Modifier、TraitModifiers），或 `modgen search` 查游戏库实现。")
        return 1
    print(f"命中 {len(results)} 个技能文件（--file <相对路径> 查看全文）：")
    for item in results:
        marker = "★" if item["name_hit"] else " "
        print(f"  {marker} {item['rel']}  (得分 {item['score']:.0f})")
        for snippet in item["snippets"]:
            print(f"      | {snippet}")
    return 0


def _parse_json_list(raw: str | None) -> list[dict[str, Any]]:
    if not raw:
        return []
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("--json 参数需要 JSON 数组")
    return [item for item in data if isinstance(item, dict)]


def _cmd_custom_file(args: argparse.Namespace) -> int:
    """custom-file：自定义 SQL/XML/Lua 文件通道（写工程目录 + 注册文件动作）。"""
    civ_path = Path(args.civ)
    payload = load_civ(civ_path)
    try:
        if args.sub == "write":
            if args.content_file:
                content = Path(args.content_file).read_text(encoding="utf-8")
            elif args.content is not None:
                content = args.content
            else:
                print("ERROR: 需要 --content 或 --content-file", file=sys.stderr)
                return 1
            result = write_custom_file(
                payload,
                args.path,
                content,
                action_type=args.action or "",
                register_action=not args.no_action,
            )
            save_civ(civ_path, payload)
            print(f"已写入自定义文件：{result['absolute']}")
            if result["actions"]:
                specs = "、".join(f"{scope}/{atype}" for scope, atype in result["actions"])
                print(f"已注册文件动作：{specs}")
            print("提示：GUI「一键生成」/ --ai-exec generate_all 会原样透传该文件进 .civ6proj 与 ActionData。")
            return 0
        if args.sub == "list":
            summary = list_custom_files(payload)
            print(f"工程目录：{summary['root']}")
            print(f"磁盘文件 {len(summary['files'])} 个：")
            for item in summary["files"]:
                print(f"  {item['path']}  ({item['size']} B)")
            for scope, label in (("front_end_actions", "FrontEnd 动作"), ("in_game_actions", "InGame 动作")):
                entries = summary[scope]
                print(f"{label} {len(entries)} 条：")
                for entry in entries:
                    print(f"  {entry['type']} id={entry['id']} load={entry['load_order']} files={entry['files']}")
            return 0
        if args.sub == "remove":
            result = remove_custom_file(payload, args.path, keep_file=args.keep_file)
            save_civ(civ_path, payload)
            print(
                f"已从动作移除 {result['removed_actions']} 处引用；"
                f"磁盘文件{'保留' if args.keep_file else ('已删除' if result['deleted_file'] else '不存在')}：{result['path']}"
            )
            return 0
        print("ERROR: 未知子命令", file=sys.stderr)
        return 1
    except CustomFileError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def _cmd_check_conflicts(args: argparse.Namespace) -> int:
    """check-conflicts：自定义 SQL × 生成 SQL 冲突检测（主键重复 / UPDATE 反模式）。"""
    from .custom_conflicts import check_conflicts

    civ_path = Path(args.civ)
    if not civ_path.exists():
        print(f"ERROR: 工程文件不存在：{civ_path}", file=sys.stderr)
        return 1
    result = check_conflicts(civ_path)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
        return 1 if result["errors"] else 0
    print(
        f"生成 SQL 文件 {len(result['generated_files'])} 个；自定义 SQL 文件 {len(result['custom_files'])} 个。"
    )
    for warning in result["warnings"]:
        print(f"WARNING: [{warning.get('file')}] {warning.get('message')}")
    for error in result["errors"]:
        print(f"ERROR: [{error.get('file')}] {error.get('message')}")
    if not result["errors"] and not result["warnings"]:
        print("OK: 未发现生成/自定义 SQL 冲突。")
    return 1 if result["errors"] else 0


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
    if args.section == "修改器":
        merge_modifier_file(args.civ, args.entry, kind=args.kind, validate=not args.no_validate)
        print(f"已合并修改器条目到 {args.civ}（自动备份 .bak）")
        return 0
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


def _cmd_new_project(args: argparse.Namespace) -> int:
    project_name = args.name or Path(args.output).stem
    file_name = args.file_name or Path(args.output).stem
    create_new_project_file(
        Path(args.output),
        project_name,
        prefix=args.prefix,
        infix=args.infix,
        file_name=file_name,
        mod_name=args.name or project_name,
        description=args.desc,
        authors=args.authors,
    )
    print(f"已创建工程骨架：{args.output}")
    print("下一步：generate 生成条目 → validate 校验 → merge 合并 → preview 验证导出。")
    return 0


def _cmd_civ6proj(args: argparse.Namespace) -> int:
    """civ6proj：从 .CIV 基础信息直接生成 ModBuddy 兼容工程文件（无需 ModBuddy 新建）。"""
    generator = mt_bridge.civ6proj_generator
    civ_path = Path(args.civ)
    payload = load_civ(civ_path)
    workspace = payload.get("workspace")
    project_info: dict[str, Any] = {}
    basic_section = (workspace or {}).get("基础信息") if isinstance(workspace, dict) else None
    if isinstance(basic_section, dict):
        data = basic_section.get("data") if isinstance(basic_section.get("data"), dict) else basic_section
        project_info = data.get("project_info") if isinstance(data.get("project_info"), dict) else {}

    def _p(key: str) -> str:
        return str(project_info.get(key) or "").strip()

    def _flag(key: str) -> bool:
        # 与 ModBuddy 向导一致：.CIV 未显式开启时按向导默认值 true 处理
        # （scaffold 的 false 表示"未配置"，若照抄会生成无法加载的 mod）
        value = project_info.get(key)
        return value if isinstance(value, bool) else True

    file_name = generator.sanitize_file_name(args.file_name or _p("file_name") or civ_path.stem)
    mod_name = args.mod_name or _p("mod_name") or file_name
    description = args.desc or _p("description") or _p("teaser") or mod_name
    out_dir = Path(args.out) if args.out else generator.default_modbuddy_project_dir(file_name)

    created = generator.create_mod_project(
        directory=out_dir,
        file_name=file_name,
        mod_name=mod_name,
        guid=_p("guid") or None,
        teaser=_p("teaser") or description,
        description=description,
        authors=args.authors or _p("authors"),
        special_thanks=_p("thanks"),
        affects_saved_games=_flag("affects_saved_games"),
        supports_single_player=_flag("supports_single_player"),
        supports_multiplayer=_flag("supports_multiplayer"),
        supports_hotseat=_flag("supports_hotseat"),
        write_art_xml=not args.no_art_xml,
    )
    proj_path = created["civ6proj"]
    print(f"已生成：{proj_path}")
    if created.get("art_xml"):
        print(f"已生成：{created['art_xml']}")

    if args.update_civ:
        if not isinstance(basic_section, dict):
            print("WARNING: 工程缺少「基础信息」节，无法回写 civ6proj_path", file=sys.stderr)
            return 0
        data = basic_section.get("data") if isinstance(basic_section.get("data"), dict) else basic_section
        info = data.get("project_info")
        if not isinstance(info, dict):
            info = {}
            data["project_info"] = info
        info["civ6proj_path"] = str(proj_path.resolve())
        if not str(info.get("file_name") or "").strip():
            info["file_name"] = file_name
        # ModID 稳定性：.CIV 里没有 guid 时把本次生成的 GUID 回写，
        # 否则下次运行会再生成新 GUID，游戏会把它当成另一个 Mod
        if not str(info.get("guid") or "").strip():
            info["guid"] = str(created["guid"])
            print(f"已生成并回写 ModID（guid={info['guid']}）")
        save_civ(civ_path, payload)
        print(f"已回写 civ6proj_path 到 {civ_path}（自动备份 .bak）")
    print("提示：modgen preview 可检查导出内容；GUI「一键生成」会把文件写入该目录。")
    return 0


def _cmd_query(args: argparse.Namespace) -> int:
    game_db = resolve_game_db_path(args.game_db)
    conn = open_game_db_readonly(game_db)
    try:
        result = run_query(conn, args.sql, limit=args.limit)
    except QueryError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    if args.json:
        payload = {
            "columns": result["columns"],
            "rows": [list(row) for row in result["rows"]],
            "truncated": result["truncated"],
            "game_db": str(game_db),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=1))
    else:
        print(format_query_result(result))
    return 0


def _cmd_loc(args: argparse.Namespace) -> int:
    text_db = resolve_text_db_path(args.text_db)
    conn = sqlite3.connect(f"file:{text_db.as_posix()}?mode=ro", uri=True)
    try:
        results = [(tag, resolve_loc_tag(conn, tag)) for tag in args.tags]
    finally:
        conn.close()
    print(format_loc_results(results))
    return 0


def _cmd_preview(args: argparse.Namespace) -> int:
    civ_path = Path(args.civ)
    if not civ_path.exists():
        print(f"ERROR: 工程文件不存在：{civ_path}", file=sys.stderr)
        return 1
    try:
        if args.section:
            text = preview_section(civ_path, args.section, args.format)
            print(text)
            return 0
        files = build_preview_files(civ_path)
    except PreviewError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    out_dir = Path(args.out) if args.out else Path("modgen_work") / f"preview_{safe_out_dir_name(civ_path.stem)}"
    if args.dry_run:
        print(f"预览清单（{len(files)} 个文件，未落盘）：")
        for rel in sorted(files):
            size = len(files[rel].encode("utf-8"))
            print(f"  {rel}  ({size} B)")
        return 0
    count, total = write_preview_files(files, out_dir)
    print(f"已写入 {count} 个预览文件到 {out_dir}（共 {total} 字节）")
    print("提示：预览文件仅用于检查导出内容，与 .civ6proj 目录无关。")
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    """search：搜效果/对象 → 找到游戏里现成的实现（AI 知识获取的内置途径）。"""
    keyword = args.keyword
    game_db, text_db = resolve_db_paths(args.game_db, args.text_db)
    if game_db is None:
        print("ERROR: 未找到游戏数据库。可指定 --game-db 路径，或确认本机已运行过文明6。", file=sys.stderr)
        return 1
    conn = sqlite3.connect(str(game_db))
    loc_conn = None
    if text_db is not None:
        try:
            loc_conn = sqlite3.connect(str(text_db))
        except sqlite3.Error:
            loc_conn = None
    try:
        if args.object:
            # 对象视角：列出该对象绑定的全部 Modifier 实现
            results = search_keyword(conn, loc_conn, keyword, limit=5)
            if not results:
                print(f"未找到与「{keyword}」相关的对象。")
                return 1
            for item in results:
                print(f"[{item['label']}] {item['name']} ({item['type']}) — 命中: {item['hit']}")
                mods = object_modifier_summary(conn, loc_conn, item["category"], item["type"])
                if not mods:
                    print("    （该对象无直接绑定 Modifier，能力可能来自建筑/特质/相邻加成）")
                for mod in mods:
                    line = f"    {mod['modifier_id']} [{mod['effect_type'] or mod['modifier_type']}]"
                    if mod["args"]:
                        line += f"  参数: {', '.join(mod['args'][:6])}"
                    print(line)
                    for rs in mod["reqsets"]:
                        print(f"        {rs}")
            return 0

        results = search_keyword(conn, loc_conn, keyword)
        if not results:
            print(f"未找到与「{keyword}」相关的内容。")
            print("提示：中文可试效果词（宣战→WAR、产能→PRODUCTION…）；也可直接搜英文 Type/参数。")
            return 1
        print(f"命中 {len(results)} 个对象（--object 查看具体实现）：")
        for item in results:
            print(f"  [{item['label']}] {item['name']} ({item['type']}) — {item['hit']} | {item['summary'][:60]}")
        return 0
    finally:
        conn.close()
        if loc_conn is not None:
            loc_conn.close()


def _parse_params(raw: str | None) -> list[dict[str, Any]]:
    """--params JSON 对象 → [{"name","value"}] 列表。"""
    if not raw:
        return []
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("--params 需要 JSON 对象")
    return [{"name": name, "value": value} for name, value in data.items()]


def _cmd_generate_modifier(args: argparse.Namespace) -> int:
    entry = generate_modifier(
        prefix=args.prefix,
        infix=args.infix,
        effect_type=args.effect,
        collection_type=args.collection,
        desc=args.desc,
        modifier_id=args.id,
        parameters=_parse_params(args.params) or None,
        comment=args.comment,
        owner_reqset=args.owner_reqset,
        subject_reqset=args.subject_reqset,
        run_once=args.run_once,
        new_only=args.new_only,
        permanent=args.permanent,
    )
    print(json.dumps(entry, ensure_ascii=False, indent=2))
    return 0


def _cmd_generate_requirement(args: argparse.Namespace) -> int:
    entry = generate_requirement(
        prefix=args.prefix,
        infix=args.infix,
        requirement_type=args.req_type,
        desc=args.desc,
        requirement_id=args.id,
        parameters=_parse_params(args.params) or None,
        comment=args.comment,
    )
    print(json.dumps(entry, ensure_ascii=False, indent=2))
    return 0


def _cmd_generate_reqset(args: argparse.Namespace) -> int:
    requirements = json.loads(args.requirements) if args.requirements else []
    entry = generate_requirement_set(
        prefix=args.prefix,
        infix=args.infix,
        desc=args.desc,
        requirement_set_id=args.id,
        logic=args.logic,
        requirements=requirements,
        comment=args.comment,
    )
    print(json.dumps(entry, ensure_ascii=False, indent=2))
    return 0


def _cmd_generate_ability(args: argparse.Namespace) -> int:
    entry = generate_ability(
        prefix=args.prefix,
        infix=args.infix,
        abbr=args.abbr,
        name_zh=args.name,
        description_zh=args.desc,
        unit_ability_type=args.id,
    )
    print(json.dumps(entry, ensure_ascii=False, indent=2))
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

    val = sub.add_parser("validate", help="校验条目或整个工程（含「UI图标」段：图标名/重名/源图）")
    val.add_argument("civ", nargs="?", help="工程 .CIV 路径（校验工程时）")
    val.add_argument("--section", choices=rules.CONTENT_SECTIONS, help="分类（校验单条目时）")
    val.add_argument("--entry", help="条目 JSON 文件（校验单条目时）")
    val.add_argument("--prefix", default="", help="工程前缀")
    val.add_argument("--infix", type=int, default=0, help="工程中缀编号")
    val.set_defaults(func=_cmd_validate)

    merge = sub.add_parser("merge", help="合并条目进工程（内容分类或修改器）")
    merge.add_argument("civ", help="工程 .CIV 路径")
    merge.add_argument(
        "section",
        choices=list(rules.CONTENT_SECTIONS) + ["修改器"],
        help="分类（修改器 = 合并 modifier/requirement/reqset/ability/owner 条目）",
    )
    merge.add_argument("--entry", required=True, help="条目 JSON 文件")
    merge.add_argument("--kind", default="", help="修改器条目类型（modifier/requirement/requirement_set/unit_ability/owner；缺省自动检测）")
    merge.add_argument("--prefix", default="", help="工程前缀")
    merge.add_argument("--infix", type=int, default=0, help="工程中缀编号")
    merge.add_argument("--no-validate", action="store_true", help="跳过校验")
    merge.set_defaults(func=_cmd_merge)

    search = sub.add_parser("search", help="搜索效果/对象，查看游戏里现成的 Modifier 实现（知识查询）")
    search.add_argument("keyword", help="关键词：中文效果词（宣战/产能/农场…）或英文 Type/参数（WAR/YIELD_PRODUCTION…）")
    search.add_argument("--object", action="store_true", help="列出命中对象的全部 Modifier 实现（照抄用）")
    search.add_argument("--game-db", default="", help="游戏库路径（默认读 settings.json 或游戏 Cache）")
    search.add_argument("--text-db", default="", help="文本库路径（中文检索用；默认读 settings.json）")
    search.set_defaults(func=_cmd_search)

    sk = sub.add_parser("skill", help="本地技能库全文检索（仓库根 skills/；文件名+内容词频评分）")
    sk.add_argument("keyword", help="关键词：中文效果词/表名/写法（如 Modifier、相邻加成、TraitModifiers）")
    sk.add_argument("--file", default="", help="输出命中文件的全文（相对路径，如 05-modtools-civ/pipeline.md）")
    sk.add_argument("--limit", type=int, default=10, help="结果数上限（默认 10）")
    sk.add_argument("--skills-dir", default="", help="技能库目录（默认仓库根 skills/）")
    sk.set_defaults(func=_cmd_skill)

    cc = sub.add_parser("check-conflicts", help="自定义 SQL × 生成 SQL 冲突检测（主键重复=ERROR；UPDATE 生成表=WARNING）")
    cc.add_argument("civ", help="工程 .CIV 路径（需已绑定 .civ6proj；需 PyQt 环境）")
    cc.add_argument("--json", action="store_true", help="JSON 输出（供 AI 消费）")
    cc.set_defaults(func=_cmd_check_conflicts)

    newp = sub.add_parser("new-project", help="创建工程级 .CIV 骨架（基础信息/美术/修改器/文本 结构就位）")
    newp.add_argument("output", help="输出 .CIV 路径（已存在则拒绝覆盖）")
    newp.add_argument("--name", default="", help="工程中文名（缺省用文件名）")
    newp.add_argument("--prefix", default="", help="工程前缀（如 SIQI）")
    newp.add_argument("--infix", type=int, default=0, help="工程中缀编号（如 35）")
    newp.add_argument("--file-name", default="", help="输出文件名基名（如 Siqi_Leaders_0035；缺省取输出文件名）")
    newp.add_argument("--desc", default="", help="mod_name 描述（teaser/description）")
    newp.add_argument("--authors", default="", help="作者")
    newp.set_defaults(func=_cmd_new_project)

    cp = sub.add_parser("civ6proj", help="从 .CIV 基础信息生成 ModBuddy 兼容 .civ6proj 工程（含空白 Art.xml，无需 ModBuddy 新建）")
    cp.add_argument("civ", help="工程 .CIV 路径")
    cp.add_argument("--out", default="", help="输出目录（默认 文档/Firaxis ModBuddy/Civilization VI/<文件名>/）")
    cp.add_argument("--file-name", default="", help="文件基名（缺省取工程 file_name）")
    cp.add_argument("--mod-name", default="", help="Mod 显示名（缺省取工程 mod_name）")
    cp.add_argument("--desc", default="", help="Mod 描述（缺省取工程 description）")
    cp.add_argument("--authors", default="", help="作者（缺省取工程 authors）")
    cp.add_argument("--no-art-xml", action="store_true", help="不生成空白 Art.xml")
    cp.add_argument("--update-civ", action="store_true", help="把生成路径回写进 .CIV 基础信息（自动备份 .bak）")
    cp.set_defaults(func=_cmd_civ6proj)

    cf = sub.add_parser("custom-file", help="自定义 SQL/XML/Lua 文件通道：写入 .civ6proj 工程目录并注册文件动作")
    cf_sub = cf.add_subparsers(dest="sub", required=True)

    cfw = cf_sub.add_parser("write", help="写入自定义文件（自动按路径分类注册文件动作）")
    cfw.add_argument("civ", help="工程 .CIV 路径")
    cfw.add_argument("--path", required=True, help="工程内相对路径，如 Scripts/My.lua、Data/Extra.sql")
    cfw.add_argument("--content", default=None, help="文件内容（文本）")
    cfw.add_argument("--content-file", default="", help="从文件读取内容")
    cfw.add_argument("--action", default="", help="显式动作类型（UpdateDatabase/AddGameplayScripts/AddUserInterfaces/ImportFiles/UpdateIcons/UpdateText…；缺省按路径自动分类）")
    cfw.add_argument("--no-action", action="store_true", help="只写文件不注册动作")
    cfw.set_defaults(func=_cmd_custom_file)

    cfl = cf_sub.add_parser("list", help="列出工程目录文件与已注册文件动作")
    cfl.add_argument("civ", help="工程 .CIV 路径")
    cfl.set_defaults(func=_cmd_custom_file)

    cfr = cf_sub.add_parser("remove", help="从文件动作移除（可选删除磁盘文件）")
    cfr.add_argument("civ", help="工程 .CIV 路径")
    cfr.add_argument("--path", required=True, help="工程内相对路径")
    cfr.add_argument("--keep-file", action="store_true", help="保留磁盘文件，仅移除动作引用")
    cfr.set_defaults(func=_cmd_custom_file)

    q = sub.add_parser("query", help="游戏库只读查询（仅 SELECT/WITH/PRAGMA/EXPLAIN，自动限行）")
    q.add_argument("sql", help="SQL 语句（单条）")
    q.add_argument("--json", action="store_true", help="JSON 输出（columns/rows）")
    q.add_argument("--limit", type=int, default=50, help="行数上限（默认 50，最大 500）")
    q.add_argument("--game-db", default="", help="游戏库路径（默认读 settings.json 或游戏 Cache）")
    q.set_defaults(func=_cmd_query)

    loc = sub.add_parser("loc", help="LOC 标签 → 简体中文文本（含 {LOC_...} 引用展开）")
    loc.add_argument("tags", nargs="+", help="LOC tag，如 LOC_TRAIT_CIVILIZATION_XXX_NAME")
    loc.add_argument("--text-db", default="", help="文本库路径（默认读 settings.json）")
    loc.set_defaults(func=_cmd_loc)

    prev = sub.add_parser("preview", help="无头预览 .CIV 将导出的 SQL/XML/图标/ArtDef 等文件（验证闭环）")
    prev.add_argument("civ", help="工程 .CIV 路径")
    prev.add_argument("--section", default="", help="只预览单个分类（内容分类 / UI图标 / 修改器）")
    prev.add_argument("--format", default="sql", choices=["sql", "xml"], help="单分类预览格式")
    prev.add_argument("--out", default="", help="预览输出目录（默认 modgen_work/preview_<工程名>/）")
    prev.add_argument("--dry-run", action="store_true", help="只打印文件清单，不落盘")
    prev.set_defaults(func=_cmd_preview)

    # 修改器四类（共享 prefix/infix）
    def _add_shared(parser_: argparse.ArgumentParser) -> None:
        parser_.add_argument("--prefix", default="", help="工程前缀（如 SIQI）")
        parser_.add_argument("--infix", type=int, default=0, help="工程中缀编号（如 35）")

    mod = sub.add_parser("generate-modifier", help="生成 Modifier（参数骨架自动按 EffectType 生成）")
    _add_shared(mod)
    mod.add_argument("--effect", required=True, help="EffectType（必填）")
    mod.add_argument("--collection", default="", help="CollectionType（如 COLLECTION_OWNER）")
    mod.add_argument("--desc", default="", help="效果描述（自动生成 ModifierId）")
    mod.add_argument("--id", default="", help="完整 ModifierId（不传则按 desc 生成）")
    mod.add_argument("--params", default="", help="参数 JSON 对象，如 {\"Amount\":2,\"YieldType\":\"YIELD_PRODUCTION\"}")
    mod.add_argument("--comment", default="", help="中文注释")
    mod.add_argument("--owner-reqset", default="", help="OwnerRequirementSetId")
    mod.add_argument("--subject-reqset", default="", help="SubjectRequirementSetId")
    mod.add_argument("--run-once", action="store_true")
    mod.add_argument("--new-only", action="store_true")
    mod.add_argument("--permanent", action="store_true")
    mod.set_defaults(func=_cmd_generate_modifier)

    req = sub.add_parser("generate-requirement", help="生成 Requirement")
    _add_shared(req)
    req.add_argument("--type", dest="req_type", required=True, help="RequirementType（必填）")
    req.add_argument("--desc", default="", help="条件描述（自动生成 RequirementId）")
    req.add_argument("--id", default="", help="完整 RequirementId")
    req.add_argument("--params", default="", help="参数 JSON 对象")
    req.add_argument("--comment", default="", help="中文注释")
    req.set_defaults(func=_cmd_generate_requirement)

    rs = sub.add_parser("generate-reqset", help="生成 RequirementSet")
    _add_shared(rs)
    rs.add_argument("--desc", required=True, help="集合描述（生成 RequirementSetId）")
    rs.add_argument("--id", default="", help="完整 RequirementSetId")
    rs.add_argument("--logic", default="ALL", choices=["ALL", "ANY"])
    rs.add_argument("--requirements", default="", help="RequirementId 列表 JSON，如 [\"REQUIREMENT_A\",\"REQUIREMENT_B\"]")
    rs.add_argument("--comment", default="", help="中文注释")
    rs.set_defaults(func=_cmd_generate_reqset)

    ab = sub.add_parser("generate-ability", help="生成 UnitAbility")
    _add_shared(ab)
    ab.add_argument("--abbr", required=True, help="能力简称（生成 ABILITY_ Type）")
    ab.add_argument("--name", required=True, help="中文名")
    ab.add_argument("--desc", default="", help="中文描述")
    ab.add_argument("--id", default="", help="完整 UnitAbilityType（不传则按 abbr 生成）")
    ab.set_defaults(func=_cmd_generate_ability)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        # 未知效果/条件类型等知识性错误：内置"先搜索再断言"的方法论引导
        message = str(exc)
        if any(marker in message for marker in ("EffectType", "RequirementType", "CollectionType")):
            print(SEARCH_HINT, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
