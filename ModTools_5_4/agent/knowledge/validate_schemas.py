"""Validate auto-generated entity schemas against source code.

Run: python ModTools_5_4/agent/knowledge/validate_schemas.py

Compares generated entity_schemas.json against actual editor export_entry()
methods and TableFieldSpec builders. Reports missing/extra fields.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
KNOWLEDGE_OUT = Path(__file__).resolve().parent


def _parse_export_keys(file_path: Path, class_name: str) -> set[str]:
    """Parse return dict keys from class.export_entry() using AST."""
    if not file_path.exists():
        return set()
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "export_entry":
                    for child in ast.walk(item):
                        if isinstance(child, ast.Return) and isinstance(child.value, ast.Dict):
                            return {
                                str(k.value) for k in child.value.keys
                                if isinstance(k, ast.Constant)
                            }
    return set()


def _parse_table_fields(class_name: str) -> set[str]:
    """Parse TableFieldSpec keys from entity_table_form.py."""
    sys.path.insert(0, str(PROJECT_ROOT.parent))
    import importlib
    mod = importlib.import_module("ModTools_5_4.ui.pages.entity_table_form")
    mapping = {
        "Districts": "build_districts_main_schema",
        "Buildings": "build_buildings_main_schema",
        "Units": "build_units_main_schema",
        "Improvements": "build_improvements_main_schema",
        "Policies": "build_policies_main_schema",
        "Projects": "build_projects_main_schema",
        "Beliefs": "build_beliefs_main_schema",
        "Agendas": "build_agendas_main_schema",
    }
    func_name = mapping.get(class_name)
    if not func_name:
        return set()
    builder = getattr(mod, func_name, None)
    if not builder:
        return set()
    schema = builder()
    return {f.key for f in schema.fields}


def main():
    schema_path = KNOWLEDGE_OUT / "entity_schemas.json"
    if not schema_path.exists():
        print("Run build_knowledge.py first to generate entity_schemas.json")
        return 1

    with open(schema_path, encoding="utf-8") as f:
        generated = json.load(f)

    group_path = PROJECT_ROOT / "ui" / "pages" / "group_workspace.py"
    gp_path = PROJECT_ROOT / "ui" / "pages" / "great_people_editor.py"

    checks = [
        # (schema_key, source_type, class_or_table, file_path)
        ("Civilizations", "flat", "CivilizationItemEditor", group_path),
        ("Leaders", "flat", "LeaderItemEditor", group_path),
        ("Governors", "flat", "GovernorItemEditor", group_path),
        ("GreatPeople", "flat", "GreatPeopleCompositeEditor", gp_path),
        ("Districts", "table", "Districts", None),
        ("Buildings", "table", "Buildings", None),
        ("Units", "table", "Units", None),
        ("Improvements", "table", "Improvements", None),
        ("Policies", "table", "Policies", None),
        ("Projects", "table", "Projects", None),
        ("Beliefs", "table", "Beliefs", None),
        ("Agendas", "table", "Agendas", None),
    ]

    ok = 0
    fail = 0

    for schema_key, source_type, class_or_table, file_path in checks:
        if schema_key not in generated:
            print(f"  MISSING: {schema_key} not in generated schemas")
            fail += 1
            continue

        gen_fields = {f["key"] for f in generated[schema_key]["fields"]}

        if source_type == "flat":
            src_fields = _parse_export_keys(file_path, class_or_table)
        else:
            src_fields = _parse_table_fields(class_or_table)

        # Known extra fields in generated that are valid (added by build logic)
        known_extra = {"name", "abbr", "table_name", "table_data", "images", "subtables"}

        gen_only = gen_fields - src_fields - known_extra
        src_only = src_fields - gen_fields

        if gen_only or src_only:
            print(f"  DIFF {schema_key} ({len(gen_fields)} gen / {len(src_fields)} src):")
            if gen_only:
                print(f"    Extra in generated: {sorted(gen_only)}")
            if src_only:
                print(f"    Missing from generated: {sorted(src_only)}")
            fail += 1
        else:
            print(f"  OK  {schema_key}: {len(gen_fields)} fields match")
            ok += 1

    total = ok + fail
    print(f"\n{'='*40}")
    print(f"Result: {ok}/{total} OK, {fail}/{total} FAIL")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
