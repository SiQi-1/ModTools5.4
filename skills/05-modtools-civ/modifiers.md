# 修改器与类型来源操作指南

涉及 ModifierType、原版类型、自定义类型、modifier_type_source、vanilla_modifier_types、条件或能力时必读。先读 [实现前清单](../07-techniques/modifiers/patterns/pre-code-checklist.md) 与 [通用技巧](../07-techniques/modifier-techniques.md)。

## 修改器规则（generate-modifier 等）

- **ModifierId 命名**：`MODIFIER_{前缀}_{项目号:04d}_{描述}`（如 `MODIFIER_SIQI_0035_ADJ_STRENGTH`）；
  Requirement 用 `REQUIREMENT_`、ReqSet 用 `REQSET_`、Ability 用 `ABILITY_{前缀}_{中缀}{编号:04d}_{简称}`。
- **EffectType / RequirementType / CollectionType 必须真实存在**——generator 会校验并拒绝未知类型，
  validate 也会对未知类型报错（参数集合来自 `schemas/modifier_schemas.json`，源自游戏库权威数据）。
- **参数名必须属于该 Effect/Requirement 的参数集合**（多写/拼错报 error，标准参数缺失给 warning）。
- **引用**：`owner_reqset` / `subject_reqset` / `bound_requirements` 必须指向工程内存在的 ReqSet/Requirement。
- 生成的 Modifier 参数骨架 value 为 null，AI 需填入实际值（数值/Type/文本）。
- 注意：`generate-modifier` 产物是"自定义 ModifierType"（modifier_type = modifier_id），
  若要用游戏内置 ModifierType，需另行指定。
- **ModifierStrings 预览文本**：`effect_type = EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER` 的 modifier **必须填 `preview_text`**
  （原版 226 个实例里 221 个都写了；不写不报错，但战斗预览面板不显示该加成来源）。
  工具会生成两行：`ModifierStrings(ModifierId,'Preview','LOC_{ModifierId}_PREVIEW')` + 对应 `LocalizedText`
  （前者在 `modifier_workspace`，后者在 `workspace_page._modifier_strength_preview_text_rows()`），**都要求 `preview_text` 非空**。
  写法：数值型 `+{1_Amount} [ICON_Strength] 战斗力（来源）`；`Key`（属性）型 `+{Property} [ICON_Strength] 战斗力（来源）`。
- **自定义 ModifierType 必须注册**：`.CIV` 里 `modifier_type` 不属于**原版快照**
  （`ModTools_5_4/data/vanilla_modifier_types.json`，989 条，由
  `python -m modgen.tools.extract_vanilla_modifier_types` 从游戏自带 XML 提取）时，
  导出会补 `INSERT INTO Types(KIND_MODIFIER)` + `INSERT INTO DynamicModifiers` 行。
  - 判定**不看本机运行缓存库** `DebugGameplay.sqlite`（它含玩家装过的所有 Mod 的类型，
    "库里有"≠"原版有"）；沿用它会把别人的自定义类型误当原版、不补行，
    结果 Mod 在没装那个旧 Mod 的机器上加载失败。
  - 条目可用 `modifier_type_source` 覆盖：`null`=自动（按快照）/ `"new"`=强制新建 /
    `"vanilla"`=强制视为游戏已有（仅当快照中确实存在该类型）。
  - `validate` 会对「强制新建却属原版」「强制已有却不在快照」报 **ERROR**；
    自动判定为自定义时给 WARNING（提示将补注册行）。

## UnitAbilities 的可选显示文本

原版 `Base/Assets/Gameplay/Data/Schema/01_GameplaySchema.sql` 中 `UnitAbilities.Name`、`Description` 都允许 NULL。原版 `ABILITY_RECEIVE_RANGE_BONUS`、`ABILITY_OLIGARCHY_MELEE_BUFF` 也省略这两项。内部状态、扣劳动力等实现用能力可将 `name_zh` / `description_zh` 省略或设为 null，并关闭获得时漂字；无需为每个辅助能力编写玩家文本。真正需要玩家理解的单位能力按需提供说明，两个字段互不强制依赖。

`modgen generate-ability --abbr INTERNAL_MARKER` 可直接生成无显示文本的能力；校验不再将空名称视为问题，导出 SQL 使用 NULL、不产生空 LOC。该规则只针对 UnitAbilities，不能推广到其他实体的必填名称。
