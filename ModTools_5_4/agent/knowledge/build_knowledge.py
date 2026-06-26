"""One-time script to build compact knowledge files for the AI Agent.

Reads: data/effect_comment_templates.json, data/requirement_comment_templates.json,
       data/effect_type_parameters.json, data/art_xml_rules.json
Writes: agent/knowledge/effect_types_compact.json,
        agent/knowledge/requirement_types_compact.json,
        agent/knowledge/collection_types.json,
        agent/knowledge/entity_schemas.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
KNOWLEDGE_OUT = Path(__file__).resolve().parent


def build_collection_types():
    """Extract collection types from effect_type_parameters.json."""
    src = DATA_DIR / "effect_type_parameters.json"
    if not src.exists():
        print(f"SKIP: {src} not found")
        return
    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)
    collection_types = data.get("collection_types", [])
    out_path = KNOWLEDGE_OUT / "collection_types.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"collection_types": collection_types}, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(collection_types)} collection types to {out_path}")


def build_effect_types_compact():
    """Merge effect_comment_templates.json + effect_type_parameters.json into one compact file."""
    # Load comment templates (Chinese descriptions + param types)
    ct_path = DATA_DIR / "effect_comment_templates.json"
    ep_path = DATA_DIR / "effect_type_parameters.json"
    if not ct_path.exists():
        print(f"SKIP: {ct_path} not found")
        return
    with open(ct_path, "r", encoding="utf-8") as f:
        comments = json.load(f)
    param_names = {}
    if ep_path.exists():
        with open(ep_path, "r", encoding="utf-8") as f:
            ep_data = json.load(f)
        for entry in ep_data.get("effect_types", []):
            param_names[entry["effect_type"]] = entry.get("parameter_names", [])

    compact = {}
    for effect_type, info in comments.items():
        entry = {
            "c": info.get("comment", ""),          # Chinese comment template
            "p": info.get("params", {}),            # param name -> type
            "pn": param_names.get(effect_type, []),  # param names in order
        }
        compact[effect_type] = entry

    out_path = KNOWLEDGE_OUT / "effect_types_compact.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(compact, f, ensure_ascii=False)
    print(f"Wrote {len(compact)} effect types to {out_path}")


def build_requirement_types_compact():
    """Compact requirement comment templates."""
    ct_path = DATA_DIR / "requirement_comment_templates.json"
    if not ct_path.exists():
        print(f"SKIP: {ct_path} not found")
        return
    with open(ct_path, "r", encoding="utf-8") as f:
        comments = json.load(f)

    compact = {}
    for req_type, info in comments.items():
        entry = {
            "c": info.get("comment", ""),
            "p": info.get("params", {}),
        }
        compact[req_type] = entry

    out_path = KNOWLEDGE_OUT / "requirement_types_compact.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(compact, f, ensure_ascii=False)
    print(f"Wrote {len(compact)} requirement types to {out_path}")


def _load_enum_file(rel_path: str) -> dict[str, str]:
    """Parse an enum txt file from AI制作Mod: ENUM_NAME | Chinese_Label or ENUM_NAME."""
    path = PROJECT_ROOT.parent.parent / "AI制作Mod" / rel_path
    if not path.exists():
        return {}
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "|" in line:
            key, label = line.split("|", 1)
            key = key.strip()
            label = label.strip()
            if key:
                result[key] = label
        else:
            if line and not line.startswith("#"):
                result[line.strip()] = ""
    return result


def build_reference_enums():
    """Extract key enum values from AI制作Mod reference/enums/."""
    terrain_enums = _load_enum_file("reference/enums/TerrainType.txt")
    feature_enums = _load_enum_file("reference/enums/FeatureType.txt")
    resource_enums = _load_enum_file("reference/enums/ResourceType.txt")

    out = {
        "terrains": [
            {"value": k, "label": v or k} for k, v in terrain_enums.items()
        ],
        "features": [
            {"value": k, "label": v or k} for k, v in feature_enums.items()
        ],
        "resources": [
            {"value": k, "label": v or k} for k, v in resource_enums.items()
        ],
    }
    path = KNOWLEDGE_OUT / "reference_enums.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(terrain_enums)} terrains, {len(feature_enums)} features, "
          f"{len(resource_enums)} resources to {path}")


def build_entity_schemas():
    """Extract entity table schemas from entity_table_form.py schema builders.

    We import the schema builders and extract field metadata.
    """
    sys.path.insert(0, str(PROJECT_ROOT.parent))
    try:
        from ModTools_5_4.ui.pages.entity_table_form import (
            build_districts_main_schema,
            build_buildings_main_schema,
            build_units_main_schema,
            build_improvements_main_schema,
            build_policies_main_schema,
            build_projects_main_schema,
            build_beliefs_main_schema,
            build_agendas_main_schema,
        )
    except ImportError as e:
        print(f"WARNING: Could not import schema builders: {e}")
        print("Skipping entity_schemas.json generation.")
        return

    schema_builders = {
        "Districts": build_districts_main_schema,
        "Buildings": build_buildings_main_schema,
        "Units": build_units_main_schema,
        "Improvements": build_improvements_main_schema,
        "Policies": build_policies_main_schema,
        "Projects": build_projects_main_schema,
        "Beliefs": build_beliefs_main_schema,
        "Agendas": build_agendas_main_schema,
    }

    schemas = {}
    for name, builder in schema_builders.items():
        try:
            schema = builder()
            fields = []
            for f in schema.fields:
                fields.append({
                    "key": f.key,
                    "label": f.label,
                    "field_type": f.field_type,
                    "section": f.section,
                    "default": f.default,
                    "required": getattr(f, "required", False),
                    "template_key": f.template_key,
                })
            schemas[name] = {
                "table_name": schema.table_name,
                "fields": fields,
                "linked_groups": [
                    {"first_key": lg.first_key, "second_key": lg.second_key}
                    for lg in (schema.linked_groups or [])
                ],
            }
        except Exception as e:
            print(f"  Error building schema for {name}: {e}")

    # Add manual schemas for sections without TableFieldSpec builders
    # Workspace entry field schemas (matches the format used by set_entry/export_entry in editors)
    manual_schemas = {
        "Civilizations": {
            "table_name": "Civilizations",
            "note": "文明编辑器字段（扁平格式，字段在data顶层，不要放table_data里！）",
            "fields": [
                {"key": "civilization_name", "label": "文明名称", "field_type": "text", "required": True,
                 "desc": "中文名，如'中华'"},
                {"key": "civilization_description", "label": "文明全称", "field_type": "text", "required": False,
                 "desc": "自动生成为 文明名称+后缀，如'中华帝国'。一般无需手动填"},
                {"key": "civilization_adjective", "label": "形容词", "field_type": "text", "required": True,
                 "desc": "如'中华的'"},
                {"key": "description_suffix", "label": "全称后缀", "field_type": "text", "required": False,
                 "default": "帝国", "desc": "如填'帝国'，则全称='中华帝国'"},
                {"key": "level", "label": "文明级别", "field_type": "text", "required": True,
                 "enum": ["CIVILIZATION_LEVEL_FULL_CIV", "CIVILIZATION_LEVEL_CITY_STATE",
                          "CIVILIZATION_LEVEL_TRIBE", "CIVILIZATION_LEVEL_FREE_CITIES"],
                 "default": "CIVILIZATION_LEVEL_FULL_CIV"},
                {"key": "ethnicity", "label": "人种", "field_type": "text", "required": False,
                 "enum": ["ETHNICITY_ASIAN", "ETHNICITY_EURO", "ETHNICITY_MEDIT",
                          "ETHNICITY_SOUTHAM", "ETHNICITY_AFRICAN"],
                 "default": "ETHNICITY_ASIAN"},
                {"key": "city_name_depth", "label": "城市名随机深度", "field_type": "int", "required": False,
                 "default": 10, "desc": "1=严格按序，10=前十中随机"},
                {"key": "trait_name", "label": "特质名称", "field_type": "text", "required": False,
                 "desc": "如'中华特质'"},
                {"key": "trait_description", "label": "特质描述", "field_type": "text", "required": False},
                {"key": "trait_bindings", "label": "特质绑定", "field_type": "array", "required": False,
                 "default": [], "desc": "绑定到其他实体的特质条目列表，[]表示空"},
                {"key": "icon_image_name", "label": "图标名", "field_type": "text", "required": False,
                 "desc": "如ICON_CIVILIZATION_SIQI_X"},
                {"key": "images", "label": "图片", "field_type": "object", "required": False,
                 "default": {}, "desc": "图标图片数据，{}表示空"},
                {"key": "city_info", "label": "城市名设置", "field_type": "object", "required": False,
                 "default": {}, "desc": "城市名配置，{}表示空/默认"},
                {"key": "citizen_info", "label": "市民名设置", "field_type": "object", "required": False,
                 "default": {}, "desc": "市民名配置，{}表示空/默认"},
                {"key": "start_bias", "label": "起始偏好", "field_type": "object", "required": False,
                 "default": {},
                 "desc": "出生地偏好。格式: {\"terrains\":[],\"features\":[],\"resources\":[],\"river_enabled\":false,\"river_tier\":1}。\n"
                         "terrain示例: TERRAIN_GRASS, TERRAIN_PLAINS, TERRAIN_DESERT, TERRAIN_TUNDRA, TERRAIN_GRASS_HILLS等\n"
                         "feature示例: FEATURE_FOREST, FEATURE_JUNGLE, FEATURE_MARSH, FEATURE_OASIS, FEATURE_FLOODPLAINS等\n"
                         "resource示例: RESOURCE_IRON, RESOURCE_HORSES, RESOURCE_COAL, RESOURCE_OIL, RESOURCE_URANIUM等\n"
                         "tier: 1(最强偏好)~5(最弱偏好)"},
            ],
        },
        "Leaders": {
            "table_name": "Leaders",
            "note": "领袖编辑器字段（ModTools5.4内部格式）",
            "fields": [
                {"key": "leader_name", "label": "领袖名称", "field_type": "text", "required": True,
                 "desc": "中文名，如'秦始皇'"},
                {"key": "sex", "label": "性别", "field_type": "text", "required": True,
                 "enum": ["Male", "Female"], "default": "Male"},
                {"key": "capital_name", "label": "首都名", "field_type": "text", "required": False,
                 "desc": "首都中文名"},
                {"key": "civilization_type", "label": "关联文明类型", "field_type": "text", "required": False,
                 "desc": "如CIVILIZATION_SIQI_X"},
                {"key": "civilization_name", "label": "关联文明名", "field_type": "text", "required": False,
                 "desc": "关联文明的中文显示名"},
                {"key": "leader_text", "label": "领袖格言", "field_type": "text", "required": False,
                 "desc": "加载画面引语"},
                {"key": "leader_quote", "label": "百科引言", "field_type": "text", "required": False,
                 "desc": "文明百科中显示的引言"},
                {"key": "ability_name", "label": "领袖能力名称", "field_type": "text", "required": True},
                {"key": "ability_description", "label": "领袖能力描述", "field_type": "text", "required": True},
                {"key": "select_sort_index", "label": "选择界面排序", "field_type": "int", "required": False,
                 "default": 0, "desc": "影响选择界面的排序顺序"},
                {"key": "add_diplo_background_curtain", "label": "外交背景幕布", "field_type": "bool", "required": False,
                 "default": False},
                {"key": "icon_image_name", "label": "图标名", "field_type": "text", "required": False},
                {"key": "bindings", "label": "特质绑定", "field_type": "array", "required": False,
                 "desc": "绑定其他实体的特质列表"},
                {"key": "diplomacy", "label": "外交文本", "field_type": "array", "required": False,
                 "desc": "外交场景文本列表"},
                {"key": "images", "label": "图片数据", "field_type": "object", "required": False,
                 "desc": "6张图片（加载前景/背景、外交肖像/背景等）"},
            ],
        },
        "Governors": {
            "table_name": "Governors",
            "note": "总督编辑器字段（ModTools5.4内部格式）",
            "fields": [
                {"key": "GovernorType", "label": "总督类型", "field_type": "text", "required": True,
                 "desc": "如GOVERNOR_SIQI_X"},
                {"key": "name", "label": "总督名称", "field_type": "text", "required": True},
                {"key": "description", "label": "描述", "field_type": "text", "required": False},
                {"key": "IdentityPressure", "label": "身份压力", "field_type": "int", "required": False,
                 "default": 0, "desc": "身份压力的数值"},
                {"key": "TransitionStrength", "label": "过渡强度", "field_type": "int", "required": False,
                 "default": 0},
                {"key": "new_trait_type", "label": "使用独立Trait", "field_type": "bool", "required": False,
                 "default": False, "desc": "是否为此总督创建独立的TraitType"},
                {"key": "TraitType", "label": "特质类型", "field_type": "text", "required": False,
                 "desc": "关联的TraitType，如TRAIT_GOVERNOR_SIQI_X"},
                {"key": "trait_type", "label": "特质类型(备用键)", "field_type": "text", "required": False},
                {"key": "icon_image_name", "label": "图标名", "field_type": "text", "required": False},
                {"key": "icon_fill_image_name", "label": "填充图标名", "field_type": "text", "required": False},
                {"key": "icon_slot_image_name", "label": "槽位图标名", "field_type": "text", "required": False},
                {"key": "images", "label": "图片数据", "field_type": "object", "required": False,
                 "desc": "5张图片（图标填充/槽位/画像等）"},
            ],
        },
        "GreatPeople": {
            "table_name": "GreatPersonClasses",
            "note": "伟人编辑器字段，含class_data和unit_data两个子对象",
            "fields": [
                {"key": "GreatPersonClassType", "label": "伟人类型", "field_type": "text", "required": True,
                 "desc": "如GREAT_PERSON_CLASS_SIQI_X"},
                {"key": "name", "label": "名称", "field_type": "text", "required": True},
                {"key": "class_data", "label": "伟人类别数据", "field_type": "object", "required": False,
                 "desc": "包含：GreatPersonClassType, Name, PseudoYieldType, IconString, ActionIcon, MaxPlayerInstances等"},
                {"key": "unit_data", "label": "关联单位数据", "field_type": "object", "required": False,
                 "desc": "包含：UnitType, Name, BaseMoves, Cost, FormationClass, Domain, TraitType, icon/portrait图片等"},
                {"key": "individuals", "label": "伟人个体列表", "field_type": "array", "required": False,
                 "desc": "每个个体可以是激活类(activation)或巨作类(greatwork)模式"},
            ],
        },
    }
    schemas.update(manual_schemas)

    out_path = KNOWLEDGE_OUT / "entity_schemas.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(schemas, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(schemas)} entity schemas to {out_path}")


def main():
    print("Building agent knowledge files...")
    build_collection_types()
    build_effect_types_compact()
    build_requirement_types_compact()
    build_reference_enums()
    build_entity_schemas()
    print("Done.")


if __name__ == "__main__":
    main()
