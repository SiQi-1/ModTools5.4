"""One-time script to build compact knowledge files for the AI Agent.

Reads: data/*.json, entity_table_form.py, group_workspace.py, workspace_page.py
Writes: agent/knowledge/*.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
KNOWLEDGE_OUT = Path(__file__).resolve().parent


def build_collection_types():
    src = DATA_DIR / "effect_type_parameters.json"
    if not src.exists():
        return
    with open(src, "r", encoding="utf-8") as f:
        data = json.load(f)
    collection_types = data.get("collection_types", [])
    out_path = KNOWLEDGE_OUT / "collection_types.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"collection_types": collection_types}, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(collection_types)} collection types to {out_path}")


def build_effect_types_compact():
    ct_path = DATA_DIR / "effect_comment_templates.json"
    ep_path = DATA_DIR / "effect_type_parameters.json"
    if not ct_path.exists():
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
        compact[effect_type] = {
            "c": info.get("comment", ""),
            "p": info.get("params", {}),
            "pn": param_names.get(effect_type, []),
        }
    out_path = KNOWLEDGE_OUT / "effect_types_compact.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(compact, f, ensure_ascii=False)
    print(f"Wrote {len(compact)} effect types to {out_path}")


def build_requirement_types_compact():
    ct_path = DATA_DIR / "requirement_comment_templates.json"
    if not ct_path.exists():
        return
    with open(ct_path, "r", encoding="utf-8") as f:
        comments = json.load(f)
    compact = {}
    for req_type, info in comments.items():
        compact[req_type] = {"c": info.get("comment", ""), "p": info.get("params", {})}
    out_path = KNOWLEDGE_OUT / "requirement_types_compact.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(compact, f, ensure_ascii=False)
    print(f"Wrote {len(compact)} requirement types to {out_path}")


def _load_enum_file(rel_path: str) -> dict[str, dict]:
    path = PROJECT_ROOT.parent.parent / "AI制作Mod" / rel_path
    if not path.exists():
        return {}
    result = {}
    current_category = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            current_category = line.lstrip("# ").strip()
            continue
        label = ""
        if "|" in line:
            key, label = line.split("|", 1)
            key = key.strip()
            label = label.strip()
        else:
            key = line.strip()
        if key:
            result[key] = {"label": label or key, "category": current_category}
    return result


def build_diplo_scenes():
    sys.path.insert(0, str(PROJECT_ROOT.parent))
    try:
        from ModTools_5_4.ui.pages.group_workspace import LEADER_DIPLO_SCENES
        scenes = [{"label": label, "template": tmpl} for label, tmpl in LEADER_DIPLO_SCENES]
        path = KNOWLEDGE_OUT / "diplo_scenes.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"scenes": scenes}, f, ensure_ascii=False, indent=2)
        print(f"Wrote {len(scenes)} diplomacy scenes to {path}")
    except ImportError as e:
        print(f"WARNING: Could not import LEADER_DIPLO_SCENES: {e}")


def build_reference_enums():
    terrain_enums = _load_enum_file("reference/enums/TerrainType.txt")
    feature_enums = _load_enum_file("reference/enums/FeatureType.txt")
    resource_enums = _load_enum_file("reference/enums/ResourceType.txt")

    def _format(enum_dict: dict) -> list[dict]:
        return [
            {"value": k, "label": v["label"], "category": v["category"]}
            for k, v in enum_dict.items()
        ]
    out = {
        "terrains": _format(terrain_enums),
        "features": _format(feature_enums),
        "resources": _format(resource_enums),
    }
    path = KNOWLEDGE_OUT / "reference_enums.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(terrain_enums)} terrains, {len(feature_enums)} features, "
          f"{len(resource_enums)} resources to {path}")


# ─── Auto-generated entity schemas ─────────────────────────────────


def _parse_flat_export_fields(class_name: str) -> list[dict]:
    """Parse export_entry() return dict keys from group_workspace.py or great_people_editor.py."""
    import ast
    for rel_path in ["ui/pages/group_workspace.py", "ui/pages/great_people_editor.py"]:
        path = PROJECT_ROOT / rel_path
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name == "export_entry":
                        for child in ast.walk(item):
                            if isinstance(child, ast.Return) and isinstance(child.value, ast.Dict):
                                keys = []
                                for k in child.value.keys:
                                    if isinstance(k, ast.Constant):
                                        keys.append({"key": str(k.value), "label": str(k.value),
                                                     "field_type": "text", "default": ""})
                                return keys
    return []


def _extract_table_fields(schema_name: str) -> list[dict]:
    """Extract table_data fields from entity_table_form.py schema builders."""
    sys.path.insert(0, str(PROJECT_ROOT.parent))
    builders = {
        "Districts": "build_districts_main_schema",
        "Buildings": "build_buildings_main_schema",
        "Units": "build_units_main_schema",
        "Improvements": "build_improvements_main_schema",
        "Policies": "build_policies_main_schema",
        "Projects": "build_projects_main_schema",
        "Beliefs": "build_beliefs_main_schema",
        "Agendas": "build_agendas_main_schema",
    }
    func_name = builders.get(schema_name)
    if not func_name:
        return []
    import importlib
    mod = importlib.import_module("ModTools_5_4.ui.pages.entity_table_form")
    builder = getattr(mod, func_name, None)
    if not builder:
        return []
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
    return fields


# ─── Manual overlay (descriptions, enums, notes) ─────────────────

_MANUAL_OVERLAY: dict[str, dict] = {
    # ── Agent level notes on which complex fields to skip ──
    "_skip_fields": {
        "subtables": "子表编辑器（多行动态表格，agent无法填写，需手动编辑）",
        "promotions": "总督晋升树（可视化节点编辑器，agent无法填写，需手动编辑）",
        "individuals": "伟人个体列表（每个个体有独立编辑器，agent无法填写，需手动编辑）",
        "trait_bindings": "特质绑定（搜索选择+多条目，建议跳过）",
        "bindings": "特质绑定列表（搜索选择+多条目，建议跳过）",
    },

    "_field_descriptions": {
        "adjacency": "相邻加成。格式: [{\"id\":\"ADJACENCY_DISTRICT\",\"yield_change\":2,"
                      "\"yield_type\":\"YIELD_SCIENCE\"}, ...]\n"
                      "existing模式(用游戏已有id): 只需id+yield_change+yield_type\n"
                      "custom模式(自定义): id+yield_type+yield_change+description+source_type",
    },

    "Civilizations": {
        "note": "文明编辑器字段（扁平格式，字段在data顶层，不要放table_data里！）",
        "field_meta": {
            "civilization_description": {"desc": "自动生成=名称+后缀，一般无需手动填"},
            "level": {"enum": ["CIVILIZATION_LEVEL_FULL_CIV", "CIVILIZATION_LEVEL_CITY_STATE",
                               "CIVILIZATION_LEVEL_TRIBE", "CIVILIZATION_LEVEL_FREE_CITIES"],
                      "default": "CIVILIZATION_LEVEL_FULL_CIV"},
            "ethnicity": {"enum": ["ETHNICITY_ASIAN", "ETHNICITY_EURO", "ETHNICITY_MEDIT",
                                   "ETHNICITY_SOUTHAM", "ETHNICITY_AFRICAN"],
                          "default": "ETHNICITY_ASIAN"},
            "description_suffix": {"default": "帝国"},
            "city_name_depth": {"default": 10, "desc": "1=严格按序，10=前十中随机"},
            "city_info": {"desc": "三种模式(mode_index): 0=复制/1=自定义/2=随机。通常用1"},
            "citizen_info": {"desc": "同city_info。自定义时entries格式: {name,female,modern}"},
            "start_bias": {"desc": "出生地偏好。用get_enum_values查可选值。terrains/features/resources是数组(每项{selector_data:{type:VALUE},tier:1})"},
        },
    },
    "Leaders": {
        "note": "领袖编辑器字段（扁平格式）",
        "field_meta": {
            "sex": {"enum": ["Male", "Female"], "default": "Male"},
            "diplomacy": {"desc": "外交场景文本(49个场景)。先调get_diplo_scenes获取精确label，再填text"},
        },
    },
    "Governors": {
        "note": "总督编辑器字段（扁平格式）",
    },
    "GreatPeople": {
        "note": "伟人编辑器字段。含class_data和unit_data嵌套对象及individuals数组",
    },
}


def build_entity_schemas():
    sys.path.insert(0, str(PROJECT_ROOT.parent))
    schemas = {}

    # ── Auto-extract from TableFieldSpec builders in entity_table_form.py ──
    table_sections = {
        "Districts": "区域", "Buildings": "建筑", "Units": "单位",
        "Improvements": "改良设施", "Policies": "政策卡", "Projects": "项目",
        "Beliefs": "信仰", "Agendas": "议程",
    }
    for schema_name, section_name in table_sections.items():
        fields = _extract_table_fields(schema_name)
        schemas[schema_name] = {
            "table_name": schema_name,
            "format": "table_data",
            "section": section_name,
            "fields": fields,
        }

    # ── Auto-extract from export_entry() methods in group_workspace.py ──
    flat_sections = {
        "Civilizations": ("CivilizationItemEditor", "文明"),
        "Leaders": ("LeaderItemEditor", "领袖"),
        "Governors": ("GovernorItemEditor", "总督"),
        "GreatPeople": ("GreatPeopleCompositeEditor", "伟人"),
    }
    for schema_name, (class_name, section_name) in flat_sections.items():
        fields = _parse_flat_export_fields(class_name)
        for f in fields:
            f["required"] = False
        schemas[schema_name] = {
            "table_name": schema_name,
            "format": "flat",
            "section": section_name,
            "fields": fields,
        }

    # ── Apply manual overlay (descriptions, enums, notes) ──
    for schema_key, overlay in _MANUAL_OVERLAY.items():
        if schema_key not in schemas:
            continue
        if "note" in overlay:
            schemas[schema_key]["note"] = overlay["note"]
        field_meta = overlay.get("field_meta", {})
        for f in schemas[schema_key]["fields"]:
            meta = field_meta.get(f["key"], {})
            for mk, mv in meta.items():
                f[mk] = mv

    # Mark known required fields for flat entities
    _FLAT_REQUIRED = {"name", "civilization_name", "civilization_adjective",
                      "leader_name", "GovernorType", "GreatPersonClassType",
                      "ability_name", "ability_description"}
    for schema_key, schema in schemas.items():
        if schema.get("format") == "flat":
            for f in schema["fields"]:
                if f["key"] in _FLAT_REQUIRED:
                    f["required"] = True

    # Inject skip warnings and field descriptions
    skip_fields = _MANUAL_OVERLAY.get("_skip_fields", {})
    descriptions = _MANUAL_OVERLAY.get("_field_descriptions", {})
    for schema_key, schema in schemas.items():
        for f in schema["fields"]:
            if f["key"] in skip_fields:
                f["agent_skip"] = True
                f["desc"] = skip_fields[f["key"]]
            if f["key"] in descriptions and not f.get("desc"):
                f["desc"] = descriptions[f["key"]]

    # Add skip reference as metadata key
    schemas["_meta"] = {"skip_fields": skip_fields}

    out_path = KNOWLEDGE_OUT / "entity_schemas.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(schemas, f, ensure_ascii=False, indent=2)
    entity_schemas = {k: v for k, v in schemas.items() if isinstance(v, dict) and "fields" in v}
    total_fields = sum(len(s["fields"]) for s in entity_schemas.values())
    print(f"Wrote {len(schemas)} entity schemas ({total_fields} fields total) to {out_path}")


def _field_type_from_schema(fields: list[dict], key: str) -> str:
    for f in fields:
        if f["key"] == key:
            return f.get("field_type", "text")
    return "text"


def main():
    print("Building agent knowledge files...")
    build_collection_types()
    build_effect_types_compact()
    build_requirement_types_compact()
    build_reference_enums()
    build_diplo_scenes()
    build_entity_schemas()
    print("Done.")


if __name__ == "__main__":
    main()
