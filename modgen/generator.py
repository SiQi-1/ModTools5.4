"""generate：从"意图参数"生成合规条目 JSON。

设计原则（准确性优先）：
- Type 永远由规则生成（AI 不手写），简称是唯一输入；
- 条目结构以 fixture 提取的 entry_template 为骨架（GUI 已验证可用）；
- 中文文本存 name/Name/Description 等字段，LOC tag 由导出约定生成，不存条目里；
- 图片一律空（images={}），路径留给用户。
"""
from __future__ import annotations

import copy
from typing import Any

from . import rules
from .schema_store import section_schema


class GenerateError(ValueError):
    pass


def _build_type(
    section: str,
    *,
    prefix: str,
    infix: int,
    short_name: object | None,
) -> str:
    type_rule = rules.SECTION_TYPE_RULES.get(section)
    if type_rule is None:
        raise GenerateError(f"未知分类：{section}")
    return rules.build_entity_type(
        prefix,
        infix,
        head=type_rule["head"],
        midfix_code=type_rule["midfix"],
        short_name=short_name,
    )


def _apply_table_data_defaults(section: str, table_data: dict[str, Any]) -> dict[str, Any]:
    """按主表 schema 补齐字段默认值（仅补有默认值的字段）。"""
    schema = section_schema(section)
    if not schema:
        return table_data
    main_table = schema.get("main_table")
    if not isinstance(main_table, dict):
        return table_data
    for field in main_table.get("fields", []):
        key = field.get("key")
        if not key or key in table_data:
            continue
        if field.get("default") not in (None, ""):
            table_data[key] = field.get("default")
    return table_data


def _build_base_entry(section: str, *, prefix: str, infix: int, name: str, abbr: str, description: str = "") -> dict[str, Any]:
    """生成分类条目的基础骨架（模板结构 + type 生成 + 中文名）。"""
    schema = section_schema(section)
    if schema is None:
        raise GenerateError(f"未知分类：{section}")
    template = schema.get("entry_template")
    if not isinstance(template, dict):
        raise GenerateError(f"分类 {section} 缺少条目模板")

    entity_type = _build_type(section, prefix=prefix, infix=infix, short_name=abbr)
    entry = copy.deepcopy(template)

    # 基础字段：总督用 code（与 GUI 一致），其余用 abbr；name 通用
    entry["name"] = name
    if section == "总督":
        entry["code"] = abbr
    else:
        entry["abbr"] = abbr
    entry["type"] = entity_type

    db_type_key = rules.SECTION_DB_TYPE_KEY.get(section)
    if db_type_key and db_type_key in entry:
        entry[db_type_key] = entity_type

    table_name = rules.SECTION_TABLE_NAME.get(section)
    if table_name and "table_name" in entry:
        entry["table_name"] = table_name

    # 主表 Name/Description（若模板有对应键）
    if "Name" in entry:
        entry["Name"] = name
    if "Description" in entry:
        entry["Description"] = ""

    # 图标名约定
    icon_key = "icon_image_name"
    if icon_key in entry:
        entry[icon_key] = f"ICON_{entity_type}"

    # 图片一律空
    entry["images"] = {}

    # 分类专属显示名键（GUI 编辑器读取的键）
    if section == "文明":
        entry["civilization_name"] = name
        entry["civilization_description"] = description
        entry["civilization_adjective"] = ""
        if "description_suffix" in entry:
            entry["description_suffix"] = "文明"
    elif section == "领袖":
        entry["leader_name"] = name
        entry["leader_text"] = ""
    elif section == "项目":
        # 项目有图片槽（256×256），预填目标尺寸骨架供 AI 填图
        entry["images"] = {
            "icon": {
                "path": "",
                "scale": 1.0,
                "offset_x": 0.0,
                "offset_y": 0.0,
                "target_width": 256,
                "target_height": 256,
            }
        }
    # 信仰 has_images=False（GUI 无图片槽），保持 images={}，
    # 图标经美术页别名/数据库处理，无需导入图片。

    return entry


def generate_entry(
    section: str,
    *,
    prefix: str,
    infix: int,
    name: str,
    abbr: str,
    description: str = "",
    **extra: Any,
) -> dict[str, Any]:
    """生成一个合规条目。

    Args:
        section: 分类名（文明/领袖/区域/…）
        prefix: 工程前缀（如 SIQI）
        infix: 工程中缀编号（如 35）
        name: 中文名（显示名）
        abbr: 英文简称（用于生成 Type，如 C0035_1 或 DEMO）
        description: 中文描述（可选）
        extra: 其余意图参数，直接写入条目（覆盖模板同名字段）
    """
    entry = _build_base_entry(
        section,
        prefix=prefix,
        infix=infix,
        name=name,
        abbr=abbr,
        description=description,
    )

    # 分类专属：table_data 补齐默认值
    if "table_data" in entry and isinstance(entry["table_data"], dict):
        table_data = copy.deepcopy(entry["table_data"])
        table_data["Name"] = name
        if description:
            table_data["Description"] = description
        entry["table_data"] = _apply_table_data_defaults(section, table_data)

    if "Description" in entry and description:
        entry["Description"] = description

    # extra 覆盖
    for key, value in extra.items():
        entry[key] = value

    return entry


def required_fields_to_fill(section: str) -> list[str]:
    """返回该分类"必填且无默认值"的主表字段清单（AI 需手动填写）。"""
    schema = section_schema(section)
    if not schema:
        return []
    main_table = schema.get("main_table")
    if not isinstance(main_table, dict):
        return []
    fields = []
    for field in main_table.get("fields", []):
        if field.get("required") and field.get("default") in (None, ""):
            key = field.get("key")
            if key:
                fields.append(key)
    return fields


def generate_great_person(
    *,
    prefix: str,
    infix: int,
    name: str,
    class_abbr: str,
    unit_abbr: str = "",
    individuals: list[dict[str, Any]] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """生成伟人类型条目（含伟人个体骨架）。

    Args:
        prefix/infix: 工程前缀/中缀
        name: 伟人类型中文名
        class_abbr: 伟人类型简称（生成 GreatPersonClassType）
        unit_abbr: 对应单位简称（生成 UnitType，如 SCIENTIST）
        individuals: 个体列表，每项含 mode(activation/greatwork)/abbr/name_cn，
            可选 desc_cn/era/charges 等；仅传 abbr+name 即可，其余自动生成默认
        extra: 覆盖 class_data 的其他字段（IconString/ActionIcon 等）
    """
    class_type = rules.build_entity_type(
        prefix, infix, head="GREAT_PERSON_CLASS", midfix_code="G", short_name=class_abbr
    )
    unit_type = rules.build_entity_type(prefix, infix, head="UNIT", midfix_code="U", short_name=unit_abbr) if unit_abbr else ""

    entry: dict[str, Any] = {
        "type": class_type,
        "name": name,
        "class_data": {
            "GreatPersonClassType": class_type,
            "UnitType": unit_type,
            "Name": name,
            "DistrictType": "",
            "IconString": "ICON_UNIT_GREAT_GENERAL",
            "ActionIcon": "ICON_UNITACTION_RETIRE",
            "AvailableInTimeline": True,
            "GenerateDuplicateIndividuals": False,
        },
        "unit_data": {},
        "import_locked": False,
        "individuals": [],
    }

    for index, spec in enumerate(individuals or [], start=1):
        mode = str(spec.get("mode") or "activation").strip().lower()
        individual_abbr = str(spec.get("abbr") or "").strip() or f"{class_abbr}_I{index}"
        name_cn = str(spec.get("name_cn") or "").strip() or f"{name}个体{index}"
        individual_type = rules.build_individual_type(prefix, infix, individual_abbr)

        individual: dict[str, Any] = {
            "mode": mode,
            "abbr": individual_abbr,
            "GreatPersonIndividualType": individual_type,
            "Name": name_cn,
            "EraType": str(spec.get("era") or "ERA_ANCIENT").strip(),
        }
        if mode == "activation":
            individual["ActionCharges"] = 1
            individual["Gender"] = "M"
            individual["ActionNameTextOverride"] = "LOC_GREATPERSON_ACTION_NAME_RETIRE"
            desc = str(spec.get("desc_cn") or "").strip()
            if desc:
                individual["ActionEffectTextOverride"] = desc
        elif mode == "greatwork":
            individual["ActionCharges"] = 0
            works = spec.get("great_works")
            if isinstance(works, list) and works:
                individual["great_works"] = []
                for work_spec in works:
                    work_abbr = str(work_spec.get("abbr") or "").strip() or f"{individual_abbr}_W"
                    individual["great_works"].append({
                        "GreatWorkType": rules.build_great_work_type(prefix, infix, work_abbr),
                        "GreatWorkObjectType": str(work_spec.get("object_type") or "GREATWORKOBJECT_LITERATURE"),
                        "Name": str(work_spec.get("name_cn") or "").strip() or f"巨作{index}",
                        "Quote": str(work_spec.get("quote_cn") or "").strip(),
                        "Tourism": int(work_spec.get("tourism") or 1),
                        "EraType": str(work_spec.get("era") or "").strip(),
                        "Audio": "",
                        "Image": "",
                        "yield_changes": [],
                    })
            else:
                individual["great_works"] = []
        entry["individuals"].append(individual)

    for key, value in extra.items():
        entry["class_data"][key] = value
    return entry


def generate_promotion_tree(
    *,
    prefix: str,
    infix: int,
    name: str,
    tree_abbr: str,
    nodes: list[dict[str, Any]] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """生成单位晋升树条目。

    Args:
        name: 晋升树中文名
        tree_abbr: 晋升树简称（生成 PromotionClassType）
        nodes: 节点列表，每项含 abbr/name_cn，可选 desc_cn/level/column/prereq_indices；
            缺省 level=1/column=1/prereq 空
    """
    tree_type = rules.build_entity_type(
        prefix, infix, head="PROMOTION_CLASS", midfix_code="P", short_name=tree_abbr
    )
    entry: dict[str, Any] = {
        "name": name,
        "type": tree_type,
        "mode": "tree",
        "nodes": [],
    }
    for index, spec in enumerate(nodes or [], start=1):
        node_abbr = str(spec.get("abbr") or "").strip() or f"N{index}"
        node: dict[str, Any] = {
            "abbr": node_abbr,
            "name_cn": str(spec.get("name_cn") or "").strip() or f"{name}晋升{index}",
            "desc_cn": str(spec.get("desc_cn") or "").strip(),
            "level": int(spec.get("level") or 1),
            "column": int(spec.get("column") or 1),
            "prereq_indices": list(spec.get("prereq_indices") or []),
        }
        entry["nodes"].append(node)
    entry.update(extra)
    return entry


def generate_agenda(
    *,
    prefix: str,
    infix: int,
    name: str,
    agenda_abbr: str,
    description: str = "",
    leader_abbr: str = "",
    **extra: Any,
) -> dict[str, Any]:
    """生成议程条目。

    Args:
        name: 议程中文名
        agenda_abbr: 议程简称（生成 AgendaType）
        description: 议程中文描述
        leader_abbr: 绑定领袖简称（生成 HistoricalAgendas.LeaderType）
    """
    agenda_type = rules.build_entity_type(
        prefix, infix, head="AGENDA", midfix_code="A", short_name=agenda_abbr
    )
    leader_type = rules.build_entity_type(prefix, infix, head="LEADER", midfix_code="L", short_name=leader_abbr) if leader_abbr else ""
    entry: dict[str, Any] = {
        "name": name,
        "type": agenda_type,
        "table_data": {
            "Name": name,
            "Description": description,
        },
        "historical_agendas": {},
        "subtables": {
            "ExclusiveAgendas": [],
            "AiLists": [],
            "AgendaModifiers": [],
        },
    }
    if leader_type:
        entry["historical_agendas"] = {
            "LeaderType": leader_type,
            "ExitKudoStatementKey": "",
            "ExitKudoText": "",
            "ExitWarningStatementKey": "",
            "ExitWarnText": "",
        }
    entry.update(extra)
    return entry
