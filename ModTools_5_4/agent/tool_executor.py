"""Tool execution dispatch — reads workspace state, searches knowledge, builds proposals.

Does NOT modify data directly. Proposals are returned for user approval, then
applied by WorkspacePage.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

_KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"


class ToolExecutor:
    def __init__(self, sections_provider: Callable[[], dict[str, object]]):
        self._sections_provider = sections_provider
        self._effect_types: dict = {}
        self._requirement_types: dict = {}
        self._collection_types: list[str] = []
        self._entity_schemas: dict = {}
        self._reference_enums: dict = {}
        self._diplo_scenes: list[dict] = []
        self._load_knowledge()

    def _load_knowledge(self) -> None:
        for fname, target in [
            ("effect_types_compact.json", "_effect_types"),
            ("requirement_types_compact.json", "_requirement_types"),
            ("entity_schemas.json", "_entity_schemas"),
        ]:
            path = _KNOWLEDGE_DIR / fname
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    setattr(self, target, json.load(f))
        ct_path = _KNOWLEDGE_DIR / "collection_types.json"
        if ct_path.exists():
            with open(ct_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._collection_types = data.get("collection_types", [])
        enum_path = _KNOWLEDGE_DIR / "reference_enums.json"
        if enum_path.exists():
            with open(enum_path, "r", encoding="utf-8") as f:
                self._reference_enums = json.load(f)
        diplo_path = _KNOWLEDGE_DIR / "diplo_scenes.json"
        if diplo_path.exists():
            with open(diplo_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._diplo_scenes = data.get("scenes", [])

    def execute(self, tool_name: str, params: dict) -> dict:
        method = getattr(self, f"_exec_{tool_name}", None)
        if method is None:
            return {"error": f"未知工具: {tool_name}"}
        try:
            result = method(params)
            return result
        except Exception as e:
            logger.exception("Tool %s failed", tool_name)
            return {"error": f"工具执行失败: {e}"}

    # ── Read tools ──

    def _exec_list_sections(self, params: dict) -> dict:
        sections = self._sections_provider()
        include_direct = params.get("include_direct", True)
        result = {"group_sections": [], "direct_sections": []}
        for key in [
            "文明", "领袖", "区域", "建筑", "单位", "改良设施",
            "总督", "伟人", "政策卡", "项目", "信仰", "议程",
        ]:
            entries = sections.get(key)
            count = len(entries) if isinstance(entries, list) else 0
            result["group_sections"].append({"name": key, "entry_count": count})
        if include_direct:
            for key in ["基础信息", "美术", "文本", "修改器"]:
                data = sections.get(key)
                has_data = data is not None and (not isinstance(data, dict) or bool(data))
                result["direct_sections"].append({"name": key, "has_data": has_data})
        return result

    def _exec_get_section_entries(self, params: dict) -> dict:
        section_name = params["section_name"]
        sections = self._sections_provider()
        entries = sections.get(section_name)
        if not isinstance(entries, list):
            return {"section_name": section_name, "entries": [], "count": 0}
        summary = []
        for i, entry in enumerate(entries):
            summary.append({
                "index": i,
                "name": entry.get("name", ""),
                "abbr": entry.get("abbr", ""),
                "table_name": entry.get("table_name", ""),
            })
        return {"section_name": section_name, "entries": summary, "count": len(summary)}

    def _exec_get_entry_detail(self, params: dict) -> dict:
        section_name = params["section_name"]
        entry_index = params["entry_index"]
        sections = self._sections_provider()
        entries = sections.get(section_name)
        if not isinstance(entries, list) or entry_index >= len(entries):
            return {"error": f"条目不存在: {section_name}[{entry_index}]"}
        entry = dict(entries[entry_index])
        # Simplify image data to avoid overwhelming the LLM
        if "images" in entry and isinstance(entry["images"], dict):
            entry["images"] = {k: "[image data]" for k in entry["images"]}
        return {"section_name": section_name, "index": entry_index, "data": entry}

    def _exec_get_direct_section(self, params: dict) -> dict:
        section_name = params["section_name"]
        sections = self._sections_provider()
        data = sections.get(section_name)
        if data is None:
            return {"section_name": section_name, "data": None}
        raw = dict(data) if isinstance(data, dict) else {"value": str(data)}
        # Summarize large modifier data
        if section_name == "修改器" and "data" in raw:
            md = raw["data"]
            if isinstance(md, dict):
                raw["data"] = {
                    "owners_count": len(md.get("owners", [])),
                    "modifiers_count": len(md.get("modifiers", [])),
                    "requirement_sets_count": len(md.get("requirement_sets", [])),
                    "requirements_count": len(md.get("requirements", [])),
                    "unit_abilities_count": len(md.get("unit_abilities", [])),
                }
        return {"section_name": section_name, "data": raw}

    def _exec_get_modifier_summary(self, params: dict) -> dict:
        sections = self._sections_provider()
        mod_section = sections.get("修改器")
        if not isinstance(mod_section, dict):
            return {"error": "修改器工作区未初始化"}
        data = mod_section.get("data")
        if not isinstance(data, dict):
            return {"error": "修改器数据为空"}
        return {
            "owners": len(data.get("owners", [])),
            "unit_abilities": len(data.get("unit_abilities", [])),
            "modifiers": len(data.get("modifiers", [])),
            "requirement_sets": len(data.get("requirement_sets", [])),
            "requirements": len(data.get("requirements", [])),
        }

    def _exec_get_modifier_detail(self, params: dict) -> dict:
        sections = self._sections_provider()
        mod_section = sections.get("修改器")
        if not isinstance(mod_section, dict):
            return {"error": "修改器工作区未初始化"}
        data = mod_section.get("data")
        if not isinstance(data, dict):
            return {"error": "修改器数据为空"}

        modifier_id = params.get("modifier_id")
        owner_key = params.get("owner_key")

        owners = data.get("owners", [])
        modifiers = data.get("modifiers", [])
        reqsets = data.get("requirement_sets", [])
        reqs = data.get("requirements", [])

        if modifier_id:
            mod = next((m for m in modifiers if m.get("modifier_id") == modifier_id), None)
            if not mod:
                return {"error": f"未找到修改器: {modifier_id}"}
            return self._build_modifier_chain(mod, owners, reqsets, reqs)

        if owner_key:
            table_name, type_name = owner_key.split(":", 1)
            owner = next(
                (o for o in owners
                 if o.get("table_name") == table_name and o.get("type_name") == type_name),
                None,
            )
            if not owner:
                return {"error": f"未找到拥有者: {owner_key}"}
            result = {"owner": owner, "modifiers": []}
            bindings = owner.get("owner_bindings") or []
            bound_ids = [b.get("modifier_id") for b in bindings if b.get("modifier_id")]
            # Also check legacy bound_modifier_ids
            legacy = owner.get("bound_modifier_ids") or []
            for mid in legacy:
                if mid not in bound_ids:
                    bound_ids.append(mid)
            for mid in bound_ids:
                mod = next((m for m in modifiers if m.get("modifier_id") == mid), None)
                if mod:
                    result["modifiers"].append(
                        self._build_modifier_chain(mod, owners, reqsets, reqs)
                    )
            return result

        return {"error": "请指定modifier_id或owner_key"}

    def _build_modifier_chain(self, mod: dict, owners, reqsets, reqs) -> dict:
        result = {"modifier": mod}
        # Resolve reqsets
        result["owner_reqset"] = self._resolve_reqset(mod.get("owner_reqset"), reqsets, reqs)
        result["subject_reqset"] = self._resolve_reqset(mod.get("subject_reqset"), reqsets, reqs)
        return result

    def _resolve_reqset(self, rs_id, reqsets, reqs):
        if not rs_id:
            return None
        rs = next((r for r in reqsets if r.get("requirement_set_id") == rs_id), None)
        if not rs:
            return {"requirement_set_id": rs_id, "error": "未找到"}
        result = dict(rs)
        resolved = []
        for rid in rs.get("bound_requirements", []):
            r = next((r for r in reqs if r.get("requirement_id") == rid), None)
            resolved.append(r if r else {"requirement_id": rid, "error": "未找到"})
        result["requirements"] = resolved
        return result

    def _exec_search_effect_types(self, params: dict) -> dict:
        query = params["query"].lower()
        limit = params.get("limit", 15)
        results = []
        for et, info in self._effect_types.items():
            comment = info.get("c", "")
            if not comment:
                continue
            if query in comment.lower() or query in et.lower():
                results.append({
                    "effect_type": et,
                    "comment": comment,
                    "params": info.get("pn", []),
                })
                if len(results) >= limit * 2:
                    break
        # Sort: shorter effect_type names first (more common), then by relevance
        results.sort(key=lambda x: (len(x["effect_type"]), x["effect_type"]))
        return {"query": query, "results": results[:limit]}

    def _exec_search_requirement_types(self, params: dict) -> dict:
        query = params["query"].lower()
        limit = params.get("limit", 15)
        results = []
        for rt, info in self._requirement_types.items():
            comment = info.get("c", "")
            if not comment:
                continue
            if query in comment.lower() or query in rt.lower():
                results.append({
                    "requirement_type": rt,
                    "comment": comment,
                    "params": list(info.get("p", {}).keys()),
                })
                if len(results) >= limit * 2:
                    break
        results.sort(key=lambda x: (len(x["requirement_type"]), x["requirement_type"]))
        return {"query": query, "results": results[:limit]}

    def _exec_get_entity_schema(self, params: dict) -> dict:
        section_name = params["section_name"]
        # Map Chinese names to schema keys
        name_map = {
            "文明": "Civilizations", "领袖": "Leaders",
            "区域": "Districts", "建筑": "Buildings",
            "单位": "Units", "改良设施": "Improvements",
            "总督": "Governors", "伟人": "GreatPeople",
            "政策卡": "Policies", "项目": "Projects",
            "信仰": "Beliefs", "议程": "Agendas",
        }
        key = name_map.get(section_name, section_name)
        schema = self._entity_schemas.get(key)
        if not schema:
            available = list(self._entity_schemas.keys())
            return {"error": f"未找到实体Schema: {section_name}", "available": available}
        return {"table_name": schema.get("table_name"), "fields": schema.get("fields", [])}

    def _exec_get_effect_parameters(self, params: dict) -> dict:
        effect_type = params["effect_type"]
        info = self._effect_types.get(effect_type)
        if not info:
            return {"error": f"未找到效果类型: {effect_type}"}
        return {
            "effect_type": effect_type,
            "comment": info.get("c", ""),
            "params": info.get("pn", []),
            "param_types": info.get("p", {}),
        }

    def _exec_get_enum_values(self, params: dict) -> dict:
        enum_type = params.get("enum_type", "")
        exclude_categories = params.get("exclude_categories", [])
        values = self._reference_enums.get(enum_type)
        if not values:
            return {"error": f"未知枚举类型: {enum_type}，可选: {list(self._reference_enums.keys())}"}

        # Filter by category exclusion
        if exclude_categories:
            values = [v for v in values if v.get("category", "") not in exclude_categories]

        total = len(values)
        # Show categories summary
        cats = {}
        for v in values:
            cats[v.get("category", "")] = cats.get(v.get("category", ""), 0) + 1
        cat_summary = ", ".join(f"{k}({v})" for k, v in sorted(cats.items()))

        return {
            "enum_type": enum_type,
            "total": total,
            "categories": cat_summary,
            "values": values[:30],
            "note": f"共{total}项，仅展示前30项。可传exclude_categories排除不需要的分类" if total > 30 else "",
        }

    def _exec_search_web(self, params: dict) -> dict:
        query = params.get("query", "")
        limit = params.get("limit", 5)
        results = _web_search(query, limit)
        return {"query": query, "results": results}

    # ── Propose tools ──

    def _exec_propose_add_entity(self, params: dict) -> dict:
        section_name = params.get("section_name", "文明")
        data = params.get("data") or {}
        if not isinstance(data, dict):
            return {"error": "data参数必须是对象"}
        description = params.get("description") or str(data.get("name", "新条目"))
        if "name" not in data:
            data["name"] = description
        if "abbr" not in data:
            data["abbr"] = data.get("name", "NEW")

        # Flat entity types (文明/领袖/总督/伟人): fields go at TOP LEVEL, never in table_data
        FLAT_SECTIONS = {"文明", "领袖", "总督", "伟人"}
        if section_name in FLAT_SECTIONS:
            td = data.get("table_data")
            if isinstance(td, dict) and td:
                for k, v in td.items():
                    if k not in data:
                        data[k] = v
                del data["table_data"]

        # Auto-fix diplomacy tags for leaders
        if section_name == "领袖":
            diplo = data.get("diplomacy")
            if isinstance(diplo, list):
                abbr = str(data.get("abbr", "")).strip()
                for entry in diplo:
                    if isinstance(entry, dict):
                        tag = str(entry.get("tag", "")).strip()
                        # If tag is missing/wrong but label is provided, auto-generate
                        if not tag and entry.get("label"):
                            template = self._diplo_label_to_template(str(entry["label"]))
                            if template and abbr:
                                entry["tag"] = f"LOC_DIPLO_{template.replace('XXX', abbr)}"

        # Auto-correct common field name mistakes inside start_bias
        sb = data.get("start_bias")
        if isinstance(sb, dict) and sb:
            # Fix key names
            for wrong, right in [
                ("terrain_types", "terrains"), ("terrain_type", "terrains"),
                ("feature_types", "features"), ("feature_type", "features"),
                ("resource_types", "resources"), ("resource_type", "resources"),
            ]:
                if wrong in sb and right not in sb:
                    sb[right] = sb.pop(wrong)
            if "rivers" in sb and "river_enabled" not in sb:
                sb["river_enabled"] = bool(sb.pop("rivers"))
                sb.setdefault("river_tier", 3)
            if "river" in sb and "river_enabled" not in sb:
                sb["river_enabled"] = bool(sb.pop("river"))
                sb.setdefault("river_tier", 3)
            sb.pop("coast", None)

            # Convert simple string arrays to BiasRowsEditor format
            for key in ("terrains", "features", "resources"):
                arr = sb.get(key)
                if isinstance(arr, list) and arr and isinstance(arr[0], str):
                    if key == "resources":
                        sb[key] = [
                            {"selector_data": {"resource_type": v, "display": v}, "tier": 1}
                            for v in arr
                        ]
                    else:
                        sb[key] = [
                            {"selector_data": {"type": v}, "tier": 1}
                            for v in arr
                        ]

        # Validate field names against known schema
        schema_key = self._section_to_schema_key(section_name)
        schema = self._entity_schemas.get(schema_key, {})
        valid_fields = {"name", "abbr", "table_name", "table_data", "images", "subtables",
                        "policies_xp1", "policy_government_exclusive", "projects_mode",
                        "projects_xp1", "projects_xp2", "project_building_costs",
                        "project_great_person_points", "project_resource_costs",
                        "project_yield_conversions", "project_prereqs",
                        "class_data", "unit_data", "individuals"}
        for f in schema.get("fields", []):
            valid_fields.add(f["key"])

        unknown = [k for k in data if k not in valid_fields]
        if unknown:
            known_sample = ", ".join(sorted(valid_fields - {"name", "abbr", "images"})[:15])
            return {
                "error": f"字段名不匹配！你使用了不存在或错误的字段：{unknown}。\n"
                         f"该实体({section_name})的有效字段包括：{known_sample}...\n"
                         f"请调用 get_entity_schema('{section_name}') 确认字段名后重新提案。\n"
                         f"注意：{section_name}是扁平格式，字段直接放在data顶层，不要放进table_data！"
            }

        sections = self._sections_provider()
        current = sections.get(section_name)
        current_count = len(current) if isinstance(current, list) else 0

        return {
            "action": "add_entity",
            "section_name": section_name,
            "description": description,
            "data": data,
            "insert_at_index": current_count,
            "preview": {"before": f"（新建，当前{section_name}有{current_count}个条目）", "after": data},
        }

    @staticmethod
    def _section_to_schema_key(section: str) -> str:
        return {
            "文明": "Civilizations", "领袖": "Leaders",
            "区域": "Districts", "建筑": "Buildings",
            "单位": "Units", "改良设施": "Improvements",
            "总督": "Governors", "伟人": "GreatPeople",
            "政策卡": "Policies", "项目": "Projects",
            "信仰": "Beliefs", "议程": "Agendas",
        }.get(section, section)

    def _exec_propose_edit_entity(self, params: dict) -> dict:
        section_name = params.get("section_name", "")
        entry_index = params.get("entry_index", 0)
        data = params.get("data") or {}
        description = params.get("description") or f"编辑{section_name}[{entry_index}]"

        sections = self._sections_provider()
        entries = sections.get(section_name)
        if not isinstance(entries, list) or entry_index >= len(entries):
            return {"error": f"条目不存在: {section_name}[{entry_index}]"}
        current = dict(entries[entry_index])
        merged = dict(current)
        merged.update(data)

        return {
            "action": "edit_entity",
            "section_name": section_name,
            "entry_index": entry_index,
            "description": description,
            "data": data,
            "preview": {"before": current, "after": merged},
        }

    def _exec_propose_add_modifier(self, params: dict) -> dict:
        owner = params.get("owner") or {}
        modifier = params.get("modifier") or {}
        reqsets = params.get("reqsets", [])
        requirements = params.get("requirements", [])
        description = params.get("description") or str(modifier.get("modifier_id", "新修改器"))

        # Validate
        warnings = []
        effect_type = modifier.get("effect_type", "")
        if effect_type and effect_type not in self._effect_types:
            warnings.append(f"EffectType '{effect_type}' 在知识库中未找到，请确认是否正确")
        for req in requirements:
            rt = req.get("requirement_type", "")
            if rt and rt not in self._requirement_types:
                warnings.append(f"RequirementType '{rt}' 在知识库中未找到，请确认是否正确")

        # Ensure ASCII-only IDs (no Chinese characters)
        def _asciify_id(id_str: str) -> str:
            if not id_str:
                return id_str
            if any('一' <= c <= '鿿' or '　' <= c <= '〿' for c in id_str):
                # Contains Chinese — replace with safe version
                safe = _safe_id(description)
                warnings.append(f"ID '{id_str}' 包含中文字符，已自动替换为 '{safe}'。ID必须纯英文(A-Z,0-9,_)")
                return safe
            return id_str

        if "modifier_id" in modifier:
            modifier["modifier_id"] = _asciify_id(str(modifier["modifier_id"]))
        else:
            modifier["modifier_id"] = f"MODIFIER_{_safe_id(description)}"

        for rs in reqsets:
            if "requirement_set_id" in rs:
                rs["requirement_set_id"] = _asciify_id(str(rs["requirement_set_id"]))
            else:
                rs["requirement_set_id"] = f"REQSET_{_safe_id(description)}"

        for req in requirements:
            if "requirement_id" in req:
                req["requirement_id"] = _asciify_id(str(req["requirement_id"]))
            else:
                req["requirement_id"] = f"REQ_{_safe_id(description)}"

        return {
            "action": "add_modifier",
            "description": description,
            "owner": owner,
            "modifier": modifier,
            "reqsets": reqsets,
            "requirements": requirements,
            "warnings": warnings,
            "preview": {
                "owner": owner,
                "modifier": modifier,
                "requirement_sets": reqsets,
                "requirements": requirements,
            },
        }

    def _exec_propose_delete_entity(self, params: dict) -> dict:
        section_name = params.get("section_name", "")
        entry_index = params.get("entry_index", 0)
        description = params.get("description") or f"删除{section_name}[{entry_index}]"

        sections = self._sections_provider()
        entries = sections.get(section_name)
        if not isinstance(entries, list) or entry_index >= len(entries):
            return {"error": f"条目不存在: {section_name}[{entry_index}]"}
        current = entries[entry_index]

        return {
            "action": "delete_entity",
            "section_name": section_name,
            "entry_index": entry_index,
            "description": description,
            "preview": {"deleted_entry": current.get("name", str(entry_index))},
        }

    def _diplo_label_to_template(self, label: str) -> str:
        """Map a Chinese diplomacy scene label to its template string."""
        for scene in self._diplo_scenes:
            if scene["label"] == label:
                return scene["template"]
        for scene in self._diplo_scenes:
            if scene["label"] in label or label in scene["label"]:
                return scene["template"]
        return ""


def _safe_id(text: str) -> str:
    """Convert a Chinese description to an ASCII-safe ID fragment."""
    import hashlib
    ascii_parts = re.findall(r"[A-Za-z0-9]+", text)
    if ascii_parts:
        return "_".join(ascii_parts[:4]).upper()[:40]
    h = hashlib.md5(text.encode("utf-8")).hexdigest()[:8].upper()
    return f"MOD_{h}"


def _web_search(query: str, limit: int = 5) -> list[dict]:
    """Simple web search using DuckDuckGo Lite (no API key needed)."""
    try:
        q = urllib.parse.quote(query)
        url = f"https://lite.duckduckgo.com/lite/?q={q}"
        req = urllib.request.Request(url, headers={"User-Agent": "ModTools5.4/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")
        # Extract result snippets from DDG Lite HTML
        results = []
        # Match result links and snippets
        pattern = re.compile(
            r'<a[^>]*class="result-link"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
            r'<td class="result-snippet"[^>]*>(.*?)</td>',
            re.DOTALL,
        )
        matches = pattern.findall(html)
        for href, title, snippet in matches[:limit]:
            title_clean = re.sub(r'<[^>]+>', '', title).strip()
            snippet_clean = re.sub(r'<[^>]+>', '', snippet).strip()
            results.append({
                "title": title_clean,
                "snippet": snippet_clean,
                "url": href,
            })
        if not results:
            # Fallback: try to extract any text
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text)
            if len(text) > 500:
                results.append({"title": "搜索结果摘要", "snippet": text[:500], "url": url})
        return results
    except Exception as e:
        logger.warning("Web search failed for '%s': %s", query, e)
        return [{"title": "搜索失败", "snippet": str(e), "url": ""}]
