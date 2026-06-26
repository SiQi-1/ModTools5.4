"""Tool definitions for the AI Agent — JSON Schema specifications.

Each tool is a ToolDef with an OpenAI-compatible function definition.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SECTION_NAMES = [
    "文明", "领袖", "区域", "建筑", "单位", "改良设施",
    "总督", "伟人", "政策卡", "项目", "信仰", "议程",
]

DIRECT_SECTION_NAMES = ["基础信息", "美术", "文本", "修改器"]

OWNER_TABLE_NAMES = [
    "TraitModifiers", "BuildingModifiers", "DistrictModifiers",
    "UnitAbilityModifiers", "UnitPromotionModifiers", "PolicyModifiers",
    "ProjectCompletionModifiers", "GovernorPromotionModifiers",
    "BeliefModifiers", "GovernmentModifiers", "CivicModifiers",
    "TechnologyModifiers", "ImprovementModifiers",
    "GreatPersonIndividualActionModifiers", "GreatPersonIndividualBirthModifiers",
    "GreatWorkModifiers", "GameModifiers",
]


@dataclass(slots=True)
class ToolDef:
    name: str
    description: str
    parameters: dict
    requires_preview: bool = False

    def to_openai_dict(self, strict: bool = False) -> dict:
        """Convert to OpenAI-compatible function dict. Set strict=True for DeepSeek."""
        func: dict = {
            "name": self.name,
            "description": self.description,
            "parameters": dict(self.parameters),
        }
        if strict:
            func["strict"] = True
        # Ensure all nested object schemas have additionalProperties: false
        _enforce_object_constraints(func["parameters"])
        return {"type": "function", "function": func}

    def to_openai_dict_legacy(self) -> dict:
        """Format with additionalProperties constraint but without strict mode."""
        params = dict(self.parameters)
        _enforce_object_constraints(params)
        return {"type": "function", "function": {
            "name": self.name,
            "description": self.description,
            "parameters": params,
        }}


def _enforce_object_constraints(schema: dict) -> None:
    """Recursively add additionalProperties: false to all object schemas."""
    if not isinstance(schema, dict):
        return
    if schema.get("type") == "object":
        schema.setdefault("additionalProperties", False)
    if "properties" in schema:
        for prop in schema.get("properties", {}).values():
            _enforce_object_constraints(prop)
    if "items" in schema:
        _enforce_object_constraints(schema["items"])
    if "anyOf" in schema:
        for sub in schema.get("anyOf", []):
            _enforce_object_constraints(sub)


TOOL_DEFS: list[ToolDef] = []


def _tool(name, desc, props, required=None, preview=False):
    TOOL_DEFS.append(ToolDef(
        name=name,
        description=desc,
        parameters={
            "type": "object",
            "properties": props,
            "required": required or [],
        },
        requires_preview=preview,
    ))


# ── Read tools ──

_tool(
    "list_sections",
    "列出所有16个工作区分组及其条目数量。用于了解当前工程包含哪些内容。",
    {
        "include_direct": {
            "type": "boolean",
            "description": "是否包含直接工作区分组（基础信息、美术、文本、修改器），默认true",
        },
    },
)

_tool(
    "get_section_entries",
    "获取指定分组的条目列表。返回每个条目的索引、名称和类型缩写。",
    {
        "section_name": {
            "type": "string",
            "description": "分组名称",
            "enum": SECTION_NAMES,
        },
    },
    required=["section_name"],
)

_tool(
    "get_entry_detail",
    "获取指定条目的完整数据，包括所有字段值和子表数据。",
    {
        "section_name": {
            "type": "string",
            "enum": SECTION_NAMES,
        },
        "entry_index": {
            "type": "integer",
            "description": "条目在分组中的索引（从0开始）",
        },
    },
    required=["section_name", "entry_index"],
)

_tool(
    "get_direct_section",
    "获取直接工作区分组的数据（基础信息、美术、文本、修改器）。",
    {
        "section_name": {
            "type": "string",
            "enum": DIRECT_SECTION_NAMES,
        },
    },
    required=["section_name"],
)

_tool(
    "get_modifier_summary",
    "获取修改器工作区的总览：拥有者数量、修改器数量、条件集数量、条件数量。",
    {},
)

_tool(
    "get_modifier_detail",
    "获取修改器链的详细信息。可以按修改器ID或拥有者键查找。",
    {
        "modifier_id": {
            "type": "string",
            "description": "修改器ID，如MODIFIER_SIQI_UNIT_COMBAT",
        },
        "owner_key": {
            "type": "string",
            "description": "拥有者标识，格式为'表名:类型名'，如'TraitModifiers:TRAIT_LEADER_QIN'",
        },
    },
)

_tool(
    "search_effect_types",
    "按中文描述搜索效果类型(EFFECT_TYPE)。用于确定实现某个游戏效果需要哪个EffectType。",
    {
        "query": {
            "type": "string",
            "description": "中文搜索关键词，如'战斗力'、'科技产出'、'文化炸弹'",
        },
        "limit": {
            "type": "integer",
            "description": "最多返回条数，默认15",
        },
    },
    required=["query"],
)

_tool(
    "search_requirement_types",
    "按中文描述搜索条件类型(REQUIREMENT_TYPE)。用于确定设置条件需要哪个RequirementType。",
    {
        "query": {
            "type": "string",
            "description": "中文搜索关键词，如'地形'、'近战'、'首都'",
        },
        "limit": {
            "type": "integer",
            "description": "最多返回条数，默认15",
        },
    },
    required=["query"],
)

_tool(
    "get_entity_schema",
    "获取某类实体的数据表结构：有哪些字段、字段类型、是否必填。用于了解创建该实体需要填写哪些数据。",
    {
        "section_name": {
            "type": "string",
            "description": "分组名称或表名，如'区域'/'Districts'、'建筑'/'Buildings'",
        },
    },
    required=["section_name"],
)

_tool(
    "get_effect_parameters",
    "获取某个效果类型的参数列表和中文注释模板。用于了解该EffectType需要填写哪些参数。",
    {
        "effect_type": {
            "type": "string",
            "description": "效果类型，如EFFECT_ADJUST_CITY_YIELD_CHANGE",
        },
    },
    required=["effect_type"],
)

_tool(
    "get_enum_values",
    "获取某个枚举类型的可选值列表。用于了解字段可以填写哪些值。"
    "可用于填充起始偏好(start_bias)的地形/地貌/资源，或其他下拉选项。",
    {
        "enum_type": {
            "type": "string",
            "description": "枚举类型名称",
            "enum": ["terrains", "features", "resources"],
        },
    },
    required=["enum_type"],
)


# ── Propose tools (require preview) ──

_tool(
    "propose_add_entity",
    "提议向工作区分组添加新实体（文明、领袖、区域、建筑等）。返回变更预览供用户确认。"
    "data字段应包含该实体类型所需的所有字段值。请先用get_entity_schema了解字段结构。",
    {
        "section_name": {
            "type": "string",
            "enum": SECTION_NAMES,
        },
        "data": {
            "type": "object",
            "description": "新实体的数据。至少包含name、abbr、table_data字段。table_data是核心表数据的字段->值映射。",
        },
        "description": {
            "type": "string",
            "description": "一句话描述这个变更，如'添加建筑：图书馆，+2科技'",
        },
    },
    required=["section_name", "data", "description"],
    preview=True,
)

_tool(
    "propose_edit_entity",
    "提议编辑现有实体。只需传入要修改的字段，未传入的字段保持不变。",
    {
        "section_name": {
            "type": "string",
            "enum": SECTION_NAMES,
        },
        "entry_index": {
            "type": "integer",
        },
        "data": {
            "type": "object",
            "description": "要更新的字段及其新值（增量更新，只传要改的字段）",
        },
        "description": {
            "type": "string",
            "description": "一句话描述变更内容",
        },
    },
    required=["section_name", "entry_index", "data", "description"],
    preview=True,
)

_tool(
    "propose_add_modifier",
    "提议添加完整的修改器链（拥有者→修改器→条件集→条件）。"
    "这是最核心的工具。请先用search_effect_types找到合适的EffectType，"
    "用get_effect_parameters了解参数，再用search_requirement_types设置条件。\n\n"
    "修改器层级关系：Owner是修改器的挂载主体（如Trait）；Modifier定义效果；"
    "RequirementSet定义生效条件（ALL=全部满足，ANY=任一满足）；"
    "Requirement是具体条件。\n\n"
    "常用CollectionType：\n"
    "- COLLECTION_OWNER：影响拥有者自身\n"
    "- COLLECTION_PLAYER_CITIES：影响玩家所有城市\n"
    "- COLLECTION_PLAYER_UNITS：影响玩家所有单位\n"
    "- COLLECTION_ALL_PLAYERS：影响所有玩家",
    {
        "owner": {
            "type": "object",
            "description": "修改器的拥有者（挂载主体）",
            "properties": {
                "table_name": {
                    "type": "string",
                    "enum": OWNER_TABLE_NAMES,
                    "description": "拥有者表名",
                },
                "type_name": {
                    "type": "string",
                    "description": "拥有者类型名，如TRAIT_CIVILIZATION_ZHONGGUO",
                },
                "display_name": {
                    "type": "string",
                    "description": "拥有者中文显示名",
                },
            },
            "required": ["table_name", "type_name"],
        },
        "modifier": {
            "type": "object",
            "description": "修改器主体",
            "properties": {
                "modifier_type": {
                    "type": "string",
                    "description": "修改器类型，如MODIFIER_PLAYER_UNITS_GRANT_ABILITY",
                },
                "effect_type": {
                    "type": "string",
                    "description": "效果类型，如EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER",
                },
                "collection_type": {
                    "type": "string",
                    "description": "集合类型",
                },
                "comment": {
                    "type": "string",
                    "description": "修改器的中文注释/说明",
                },
                "run_once": {
                    "type": "boolean",
                    "description": "是否只运行一次，默认false",
                },
                "permanent": {
                    "type": "boolean",
                    "description": "是否永久生效，默认false",
                },
                "parameters": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "value": {},
                        },
                        "required": ["name", "value"],
                    },
                    "description": "效果参数列表",
                },
            },
            "required": ["modifier_type", "effect_type", "collection_type"],
        },
        "reqsets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "requirement_set_id": {"type": "string", "description": "条件集ID"},
                    "comment": {"type": "string"},
                    "logic": {"type": "string", "enum": ["ALL", "ANY"]},
                    "bound_requirements": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "该条件集包含的条件ID列表",
                    },
                },
                "required": ["requirement_set_id", "logic", "bound_requirements"],
            },
            "description": "条件集列表（可空数组）",
        },
        "requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "requirement_id": {"type": "string"},
                    "comment": {"type": "string"},
                    "requirement_type": {"type": "string"},
                    "inverse": {"type": "boolean"},
                    "parameters": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "value": {},
                            },
                            "required": ["name", "value"],
                        },
                    },
                },
                "required": ["requirement_id", "requirement_type"],
            },
            "description": "条件列表（可空数组）",
        },
        "description": {
            "type": "string",
            "description": "一句话描述整个修改器链的功能",
        },
    },
    required=["owner", "modifier", "description"],
    preview=True,
)

_tool(
    "propose_delete_entity",
    "提议删除某个实体条目。",
    {
        "section_name": {
            "type": "string",
            "enum": SECTION_NAMES,
        },
        "entry_index": {
            "type": "integer",
        },
        "description": {
            "type": "string",
        },
    },
    required=["section_name", "entry_index", "description"],
    preview=True,
)
