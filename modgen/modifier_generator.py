"""修改器相关条目生成：Modifier / Requirement / RequirementSet / UnitAbility。

命名约定（与知识库 skills/06-naming.md 一致）：
- ModifierId: MODIFIER_{前缀}_{项目号}_{描述}（如 MODIFIER_SIQI_0040_PLOT_YIELD_SCIENCE）
- RequirementId: REQUIREMENT_{前缀}_{项目号}_{描述}
- RequirementSetId: REQSET_{前缀}_{项目号}_{描述}
- UnitAbilityType: ABILITY_{前缀}_{中缀代码}{中缀:04d}_{简称}
"""
from __future__ import annotations

from typing import Any

from . import rules
from .schema_store import collection_type_exists, effect_type_params, requirement_type_params


def _require_valid_effect(effect_type: str) -> None:
    params = effect_type_params(effect_type)
    if params is None:
        raise ValueError(f"未知 EffectType：{effect_type}（可用 python -m modgen.cli search <效果词> 查现成实现）")


def _require_valid_requirement_type(requirement_type: str) -> None:
    params = requirement_type_params(requirement_type)
    if params is None:
        raise ValueError(f"未知 RequirementType：{requirement_type}（可用 python -m modgen.cli search <效果词> 查现成实现）")


def _param_skeleton(param_names: list[str] | None) -> list[dict[str, Any]]:
    """按参数名生成空值骨架（value 为 None，AI 填写）。"""
    return [{"name": name, "value": None} for name in (param_names or [])]


def build_modifier_id(prefix: str, infix: int, desc: str) -> str:
    """按规范生成 ModifierId：MODIFIER_{前缀}_{项目号}_{描述}。"""
    parts = ["MODIFIER"]
    prefix_text = str(prefix or "").strip().upper()
    if prefix_text:
        parts.append(prefix_text)
    if infix > 0:
        parts.append(f"{infix:04d}")
    desc_text = rules.sanitize_short_token(desc)
    if desc_text:
        parts.append(desc_text)
    return "_".join(parts)


def build_requirement_id(prefix: str, infix: int, desc: str) -> str:
    parts = ["REQUIREMENT"]
    prefix_text = str(prefix or "").strip().upper()
    if prefix_text:
        parts.append(prefix_text)
    if infix > 0:
        parts.append(f"{infix:04d}")
    desc_text = rules.sanitize_short_token(desc)
    if desc_text:
        parts.append(desc_text)
    return "_".join(parts)


def build_requirement_set_id(prefix: str, infix: int, desc: str) -> str:
    parts = ["REQSET"]
    prefix_text = str(prefix or "").strip().upper()
    if prefix_text:
        parts.append(prefix_text)
    if infix > 0:
        parts.append(f"{infix:04d}")
    desc_text = rules.sanitize_short_token(desc)
    if desc_text:
        parts.append(desc_text)
    return "_".join(parts)


def build_ability_type(prefix: str, infix: int, abbr: str) -> str:
    """UnitAbilityType：ABILITY_{前缀}_{中缀}_{简称}（与 GUI 单位 Ability 生成一致）。"""
    return rules.build_entity_type(prefix, infix, head="ABILITY", midfix_code="A", short_name=abbr)


def generate_modifier(
    *,
    prefix: str,
    infix: int,
    effect_type: str,
    collection_type: str = "",
    desc: str = "",
    modifier_id: str = "",
    parameters: list[dict[str, Any]] | None = None,
    comment: str = "",
    owner_reqset: str = "",
    subject_reqset: str = "",
    **flags: Any,
) -> dict[str, Any]:
    """生成 Modifier 条目。

    Args:
        prefix/infix: 工程前缀/中缀
        effect_type: EffectType（必填，参数骨架自动生成）
        collection_type: CollectionType（如 COLLECTION_OWNER）
        desc: 效果描述（自动生成 ModifierId 用）
        modifier_id: 完整 ModifierId（不传则按 desc 自动生成）
        parameters: 参数列表 [{"name","value"}]；不传则按 EffectType 生成空骨架
        comment: 中文注释（可选）
        owner_reqset/subject_reqset: 引用 RequirementSetId
        flags: run_once/new_only/permanent/owner_stack_limit/subject_stack_limit
    """
    _require_valid_effect(effect_type)
    if collection_type and not collection_type_exists(collection_type):
        raise ValueError(f"未知 CollectionType：{collection_type}")

    if not modifier_id:
        if not desc:
            raise ValueError("需提供 --id（完整 ModifierId）或 --desc（自动生成 ModifierId）")
        modifier_id = build_modifier_id(prefix, infix, desc)

    if parameters is None:
        parameters = _param_skeleton(effect_type_params(effect_type))

    record: dict[str, Any] = {
        "modifier_id": modifier_id,
        "modifier_type": modifier_id,  # 自定义 ModifierType = ModifierId（GUI 约定）
        "comment": comment,
        "owner_reqset": owner_reqset,
        "subject_reqset": subject_reqset,
        "run_once": bool(flags.get("run_once", False)),
        "new_only": bool(flags.get("new_only", False)),
        "permanent": bool(flags.get("permanent", False)),
        "owner_stack_limit": int(flags.get("owner_stack_limit") or 0),
        "subject_stack_limit": int(flags.get("subject_stack_limit") or 0),
        "effect_type": effect_type,
        "collection_type": collection_type,
        "preview_text": "",
        "parameters": parameters,
    }
    return record


def generate_requirement(
    *,
    prefix: str,
    infix: int,
    requirement_type: str,
    desc: str = "",
    requirement_id: str = "",
    parameters: list[dict[str, Any]] | None = None,
    comment: str = "",
    **flags: Any,
) -> dict[str, Any]:
    """生成 Requirement 条目。"""
    _require_valid_requirement_type(requirement_type)
    if not requirement_id:
        if not desc:
            raise ValueError("需提供 --id 或 --desc（自动生成 RequirementId）")
        requirement_id = build_requirement_id(prefix, infix, desc)
    if parameters is None:
        parameters = _param_skeleton(requirement_type_params(requirement_type))
    return {
        "requirement_id": requirement_id,
        "comment": comment,
        "requirement_type": requirement_type,
        "likeliness": int(flags.get("likeliness") or 0),
        "impact": int(flags.get("impact") or 0),
        "progress_weight": int(flags.get("progress_weight") or 1),
        "inverse": bool(flags.get("inverse", False)),
        "reverse": bool(flags.get("reverse", False)),
        "persistent": bool(flags.get("persistent", False)),
        "triggered": bool(flags.get("triggered", False)),
        "parameters": parameters,
    }


def generate_requirement_set(
    *,
    prefix: str,
    infix: int,
    desc: str,
    requirement_set_id: str = "",
    logic: str = "ALL",
    requirements: list[str] | None = None,
    comment: str = "",
) -> dict[str, Any]:
    """生成 RequirementSet 条目。"""
    if not requirement_set_id:
        requirement_set_id = build_requirement_set_id(prefix, infix, desc)
    logic_text = str(logic or "ALL").strip().upper()
    if logic_text not in {"ALL", "ANY"}:
        raise ValueError(f"logic 必须是 ALL 或 ANY（实际 {logic_text}）")
    return {
        "requirement_set_id": requirement_set_id,
        "comment": comment,
        "logic": logic_text,
        "bound_requirements": list(requirements or []),
    }


def generate_ability(
    *,
    prefix: str,
    infix: int,
    abbr: str,
    name_zh: str,
    description_zh: str = "",
    unit_ability_type: str = "",
    **flags: Any,
) -> dict[str, Any]:
    """生成 UnitAbility 条目。"""
    if not unit_ability_type:
        unit_ability_type = build_ability_type(prefix, infix, abbr)
    return {
        "unit_ability_type": unit_ability_type,
        "name_zh": name_zh,
        "description_zh": description_zh,
        "inactive": bool(flags.get("inactive", False)),
        "show_float_text_when_earned": bool(flags.get("show_float_text_when_earned", False)),
        "permanent": bool(flags.get("permanent", True)),
        "type_tags": list(flags.get("type_tags") or []),
    }
