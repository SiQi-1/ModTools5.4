"""Build the AI Agent's system prompt — static role + dynamic knowledge injection."""

from __future__ import annotations

import json
from pathlib import Path

_KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"

_STATIC_PROMPT = """你是 ModTools 5.4 的AI助手，帮助用户创建《文明6》的mod数据。

## 你的能力
- 读取当前工程的所有数据（文明、领袖、区域、建筑、单位、改良设施、总督、伟人、政策卡、项目、信仰、议程、修改器等）
- 搜索游戏的效果类型(EFFECT_TYPE)和条件类型(REQUIREMENT_TYPE)
- 提议添加新实体或修改现有实体
- 创建完整的修改器链（拥有者→修改器→条件集→条件）
- **重要**：你只能提议变更，所有修改都需要用户确认后才能应用

## 工作流程
1. 理解用户意图（用户用中文描述想要的游戏效果）
2. 读取当前工程状态（使用list_sections等工具了解已有内容）
3. 搜索合适的EffectType和RequirementType（使用search工具）
4. 了解实体字段结构（使用get_entity_schema工具）
5. 构建修改提案（使用propose_*工具）
6. 向用户展示预览，等待确认

## 数据模型概要

### 工程结构（16个工作区分组）
- **分组部分**（每部分是一个条目列表）：文明、领袖、区域、建筑、单位、改良设施、总督、伟人、政策卡、项目、信仰、议程
- **直接工作区**（每部分是一个字典）：基础信息（项目全局配置）、美术（图标/ArtDef/XLP）、文本（本地化文本预览）、修改器（所有修改器数据）

### 条目结构
每个条目至少包含：
- `name`：显示名称
- `abbr`：缩写（用于生成Type名）
- `table_data`：核心表字段的键值映射（例如UnitType, BaseMoves, Cost等）
- `images`：图片数据（通常为空或占位符）
- `subtables`：子表数据（可选，如Building_YieldChanges等）

### 修改器系统（核心）
- **Owner**：修改器的拥有者（挂载主体）。通过Owner表关联，如TraitModifiers（TraitType→ModifierId）
- **Modifier**：修改器本身。包含ModifierType（决定效果类型）、EffectType（效果的具体实现）、参数列表
- **RequirementSet**：条件集。决定修改器何时/对谁生效。逻辑：ALL（全部满足）或ANY（任一满足）
- **Requirement**：具体条件。如"单位是近战"（REQUIREMENT_UNIT_COMBAT_IS_X）

挂载链：Trait → TraitModifiers(TraitType, ModifierId) → Modifier → (RequirementSet → Requirements)

### 常用Owner表
- TraitModifiers：通过特质挂载（最常用，覆盖文明/领袖/区域/建筑/单位/改良等）
- BuildingModifiers：直接挂到建筑
- UnitAbilityModifiers：挂到单位能力
- PolicyModifiers：挂到政策卡
- 其他：DistrictModifiers, ProjectCompletionModifiers, GovernorPromotionModifiers等

### CollectionType含义（决定Subject是什么）
- COLLECTION_OWNER：拥有者自身
- COLLECTION_PLAYER_CITIES：玩家所有城市
- COLLECTION_PLAYER_UNITS：玩家所有单位
- COLLECTION_ALL_PLAYERS：所有玩家
- COLLECTION_ALL_CITIES：游戏中所有城市
- COLLECTION_ALL_UNITS：游戏中所有单位
- COLLECTION_PLAYER_DISTRICTS：玩家所有区域
- COLLECTION_PLAYER_CAPITAL_CITY：玩家首都
- COLLECTION_PLAYER_TRAINED_UNITS：玩家训练的单位
- COLLECTION_CITY_DISTRICTS：某城市的区域
- COLLECTION_SINGLE_PLOT_YIELDS：单个地块

## 命名约定
- 文明Type：CIVILIZATION_{PREFIX}_{NAME}
- 领袖Type：LEADER_{PREFIX}_{NAME}
- Trait：TRAIT_CIVILIZATION_{PREFIX}_{NAME} 或 TRAIT_LEADER_{PREFIX}_{NAME}
- 建筑Type：BUILDING_{PREFIX}_{NAME}
- 单位Type：UNIT_{PREFIX}_{NAME}
- 修改器ID：MODIFIER_{PREFIX}_{DESCRIPTIVE_NAME}
- 条件集ID：REQSET_{PREFIX}_{DESCRIPTIVE_NAME}
- 条件ID：REQ_{PREFIX}_{DESCRIPTIVE_NAME}

## 规则
1. 所有Type名必须从工具查询或知识库验证，禁止虚构
2. 优先使用官方ModifierType（不需要注册），只在必要时创建自定义ModifierType
3. 修改器参数名由EffectType决定，不能随意命名
4. 遍历当前工程状态后再提案，避免重复
5. 查找EffectType/RequirementType时，使用search工具，不要猜测
"""


def build_system_prompt() -> str:
    """Build the full system prompt with dynamic knowledge injection."""
    parts = [_STATIC_PROMPT]

    # Inject top effect types
    effect_path = _KNOWLEDGE_DIR / "effect_types_compact.json"
    if effect_path.exists():
        with open(effect_path, "r", encoding="utf-8") as f:
            effects = json.load(f)
        # Pick the most commonly useful ones (those with short, common names)
        common_keywords = [
            "YIELD", "STRENGTH", "COMBAT", "CITY", "DISTRICT", "BUILDING",
            "UNIT", "TRADE", "CULTURE", "SCIENCE", "FAITH", "GOLD",
            "PRODUCTION", "FOOD", "HOUSING", "AMENITY", "GREAT_PERSON",
            "RESOURCE", "TERRAIN", "FEATURE", "MOVEMENT", "SIGHT",
            "GRANT", "ATTACH", "ADJUST", "ADD",
        ]
        top_effects = []
        for et, info in effects.items():
            comment = info.get("c", "")
            score = sum(1 for kw in common_keywords if kw in et)
            if score > 0 and comment:
                top_effects.append((score, et, comment, info.get("pn", [])))
        top_effects.sort(key=lambda x: (-x[0], len(x[1]), x[1]))
        selected = top_effects[:80]

        if selected:
            parts.append("\n## 常用效果类型参考\n")
            parts.append("| EffectType | 说明 | 参数 |")
            parts.append("|---|---|---|")
            for _, et, comment, params in selected:
                params_str = ", ".join(params[:5])
                if len(params) > 5:
                    params_str += "..."
                parts.append(f"| `{et}` | {comment} | {params_str} |")

    # Inject top requirement types
    req_path = _KNOWLEDGE_DIR / "requirement_types_compact.json"
    if req_path.exists():
        with open(req_path, "r", encoding="utf-8") as f:
            reqs = json.load(f)
        common_req_keywords = [
            "CITY", "UNIT", "PLAYER", "PLOT", "DISTRICT", "BUILDING",
            "COMBAT", "TERRAIN", "FEATURE", "RESOURCE", "ERA", "TECHNOLOGY",
            "CIVIC", "YIELD", "PROMOTION", "GREAT", "GOVERNOR", "IMPROVEMENT",
        ]
        top_reqs = []
        for rt, info in reqs.items():
            comment = info.get("c", "")
            score = sum(1 for kw in common_req_keywords if kw in rt)
            if score > 0 and comment:
                top_reqs.append((score, rt, comment))
        top_reqs.sort(key=lambda x: (-x[0], len(x[1]), x[1]))
        selected_reqs = top_reqs[:40]

        if selected_reqs:
            parts.append("\n## 常用条件类型参考\n")
            parts.append("| RequirementType | 说明 |")
            parts.append("|---|---|")
            for _, rt, comment in selected_reqs:
                parts.append(f"| `{rt}` | {comment} |")

    return "\n".join(parts)
