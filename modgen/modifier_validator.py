"""修改器数据校验：Modifier / Requirement / RequirementSet / UnitAbility。

关键校验（AI 最容易错的地方）：
- EffectType / RequirementType / CollectionType 存在性
- 参数名必须 ∈ 该类型的参数名集合（多余/拼错参数名报错，缺失参数提示）
- requirement_set 引用存在（owner_reqset/subject_reqset/bound_requirements）
- ModifierId / RequirementId 命名规范（MODIFIER_ / REQUIREMENT_ / REQSET_ 前缀）
- **自定义 ModifierType 注册**：不在原版快照中的类型必须补 Types + DynamicModifiers 行
  （否则该 Mod 在没装过同名 Mod 的机器上加载即缺类型；判定见 modgen/vanilla_types.py）
"""
from __future__ import annotations

from typing import Any

from .schema_store import (
    collection_type_exists,
    effect_type_params,
    requirement_type_params,
)
from .vanilla_types import load_vanilla_modifier_types, needs_registration, snapshot_available


def _params_to_dict(parameters: Any) -> dict[str, Any]:
    if not isinstance(parameters, list):
        return {}
    result: dict[str, Any] = {}
    for item in parameters:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        if name:
            result[name] = item.get("value")
    return result


def check_modifier(
    modifier: dict[str, Any],
    *,
    requirement_set_ids: set[str] | None = None,
    check_id_prefix: bool = True,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    modifier_id = str(modifier.get("modifier_id") or "").strip()
    if not modifier_id:
        errors.append("modifier_id 为空")
    elif check_id_prefix and not modifier_id.startswith("MODIFIER_"):
        warnings.append(f"modifier_id 不以 MODIFIER_ 开头：{modifier_id}")

    effect_type = str(modifier.get("effect_type") or "").strip()
    if not effect_type:
        errors.append("effect_type 为空")
    else:
        known_params = effect_type_params(effect_type)
        if known_params is None:
            errors.append(f"未知 EffectType：{effect_type}")
        else:
            params = _params_to_dict(modifier.get("parameters"))
            for name in params:
                if name not in known_params:
                    errors.append(f"参数 {name} 不属于 {effect_type} 的参数集合")
            known_set = set(known_params)
            for name in known_params:
                if name not in params:
                    warnings.append(f"参数 {name} 未提供（{effect_type} 标准参数）")

    collection_type = str(modifier.get("collection_type") or "").strip()
    if collection_type and not collection_type_exists(collection_type):
        errors.append(f"未知 CollectionType：{collection_type}")

    # ---- ModifierStrings 预览文本（战斗预览面板显示加成来源）----
    # 仅 EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER 支持 Preview；原版 226 个实例里 221 个都写了。
    # 不写不会报错，但战斗预览面板看不到这层加成的来源 —— 属于典型的"沉默失效"。
    if effect_type.upper() == "EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER" and not str(
        modifier.get("preview_text") or ""
    ).strip():
        warnings.append(
            "缺少 ModifierStrings 预览文本（preview_text）：战斗预览面板不会显示该加成来源；"
            "数值型填 +{1_Amount} [ICON_Strength] 战斗力（来源），Key/属性型填 +{Property} …（来源）"
        )

    # ---- 自定义 ModifierType 注册（Types + DynamicModifiers）----
    modifier_type = str(modifier.get("modifier_type") or "").strip()
    source = str(modifier.get("modifier_type_source") or "").strip().lower()
    if modifier_type and snapshot_available():
        snapshot = load_vanilla_modifier_types()
        in_snapshot = modifier_type in snapshot
        if source == "new" and in_snapshot:
            errors.append(
                f"modifier_type_source=new 但该类型已属原版（{modifier_type}）；"
                "重复注册会与游戏 DynamicModifiers 主键冲突，请改为自动或 vanilla"
            )
        elif source == "vanilla" and not in_snapshot:
            errors.append(
                f"modifier_type_source=vanilla 但该类型不在原版快照中（{modifier_type}）；"
                "不注册会让本 Mod 在未装同名 Mod 的机器上加载失败"
            )
        elif not source and not in_snapshot:
            warnings.append(
                f"自定义 ModifierType（{modifier_type}）将在生成时补 Types + DynamicModifiers 行"
            )

    if requirement_set_ids is not None:
        for key in ("owner_reqset", "subject_reqset"):
            value = str(modifier.get(key) or "").strip()
            if value and value not in requirement_set_ids:
                errors.append(f"{key} 引用了不存在的 RequirementSet：{value}")

    return errors, warnings


def check_requirement(
    requirement: dict[str, Any],
    *,
    check_id_prefix: bool = True,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    requirement_id = str(requirement.get("requirement_id") or "").strip()
    if not requirement_id:
        errors.append("requirement_id 为空")
    elif check_id_prefix and not requirement_id.startswith("REQUIREMENT_"):
        warnings.append(f"requirement_id 不以 REQUIREMENT_ 开头：{requirement_id}")

    requirement_type = str(requirement.get("requirement_type") or "").strip()
    if not requirement_type:
        errors.append("requirement_type 为空")
    else:
        known_params = requirement_type_params(requirement_type)
        if known_params is None:
            errors.append(f"未知 RequirementType：{requirement_type}")
        else:
            params = _params_to_dict(requirement.get("parameters"))
            for name in params:
                if name not in known_params:
                    errors.append(f"参数 {name} 不属于 {requirement_type} 的参数集合")
            for name in known_params:
                if name not in params:
                    warnings.append(f"参数 {name} 未提供（{requirement_type} 标准参数）")

    return errors, warnings


def check_requirement_set(
    reqset: dict[str, Any],
    *,
    requirement_ids: set[str] | None = None,
    check_id_prefix: bool = True,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    reqset_id = str(reqset.get("requirement_set_id") or "").strip()
    if not reqset_id:
        errors.append("requirement_set_id 为空")
    elif check_id_prefix and not reqset_id.startswith("REQSET_"):
        warnings.append(f"requirement_set_id 不以 REQSET_ 开头：{reqset_id}")

    logic = str(reqset.get("logic") or "").strip().upper()
    if logic not in {"ALL", "ANY"}:
        errors.append(f"logic 必须是 ALL 或 ANY（实际 {logic or '空'}）")

    if requirement_ids is not None:
        bound = reqset.get("bound_requirements")
        if not isinstance(bound, list):
            warnings.append("bound_requirements 不是列表")
        else:
            for req_id in bound:
                if str(req_id or "").strip() not in requirement_ids:
                    errors.append(f"bound_requirements 引用不存在的 Requirement：{req_id}")

    return errors, warnings


def check_ability(ability: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    ability_type = str(ability.get("unit_ability_type") or "").strip()
    if not ability_type:
        errors.append("unit_ability_type 为空")
    elif not ability_type.startswith("ABILITY_"):
        warnings.append(f"unit_ability_type 不以 ABILITY_ 开头：{ability_type}")
    if not str(ability.get("name_zh") or "").strip():
        # 从游戏库导入的能力可无中文名（GUI 合法），仅提示
        warnings.append("name_zh（中文名）为空")
    return errors, warnings


def check_modifier_data(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    """校验整个修改器工作区 data（含跨对象引用检查）。"""
    errors: list[str] = []
    warnings: list[str] = []

    modifiers = data.get("modifiers")
    reqsets = data.get("requirement_sets")
    requirements = data.get("requirements")
    abilities = data.get("unit_abilities")

    reqset_ids = {str(r.get("requirement_set_id") or "").strip() for r in reqsets} if isinstance(reqsets, list) else set()
    requirement_ids = {str(r.get("requirement_id") or "").strip() for r in requirements} if isinstance(requirements, list) else set()

    for index, modifier in enumerate(modifiers or []):
        if not isinstance(modifier, dict):
            errors.append(f"modifiers[{index}] 不是对象")
            continue
        sub_errors, sub_warnings = check_modifier(modifier, requirement_set_ids=reqset_ids)
        errors += [f"modifiers[{index}]: {e}" for e in sub_errors]
        warnings += [f"modifiers[{index}]: {w}" for w in sub_warnings]

    for index, reqset in enumerate(reqsets or []):
        if not isinstance(reqset, dict):
            errors.append(f"requirement_sets[{index}] 不是对象")
            continue
        sub_errors, sub_warnings = check_requirement_set(reqset, requirement_ids=requirement_ids)
        errors += [f"requirement_sets[{index}]: {e}" for e in sub_errors]
        warnings += [f"requirement_sets[{index}]: {w}" for w in sub_warnings]

    for index, requirement in enumerate(requirements or []):
        if not isinstance(requirement, dict):
            errors.append(f"requirements[{index}] 不是对象")
            continue
        sub_errors, sub_warnings = check_requirement(requirement)
        errors += [f"requirements[{index}]: {e}" for e in sub_errors]
        warnings += [f"requirements[{index}]: {w}" for w in sub_warnings]

    for index, ability in enumerate(abilities or []):
        if not isinstance(ability, dict):
            errors.append(f"unit_abilities[{index}] 不是对象")
            continue
        sub_errors, sub_warnings = check_ability(ability)
        errors += [f"unit_abilities[{index}]: {e}" for e in sub_errors]
        warnings += [f"unit_abilities[{index}]: {w}" for w in sub_warnings]

    return errors, warnings
