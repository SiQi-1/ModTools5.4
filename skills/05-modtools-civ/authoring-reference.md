# 制作参考：命名、相邻加成与常见陷阱

行为规则见 [RULES](../RULES.md)，本页保留原 AGENT 的游戏参考知识。

## 3. 命名规范（参考知识）

> 工具的 Type 由"基础信息"前缀+中缀+简称自动生成；以下规范用于理解命名体系与手写 `abbr`/`简称` 时参考。

- 前缀体系：`CIVILIZATION_`、`LEADER_`、`TRAIT_CIVILIZATION_`、`TRAIT_LEADER_`、`TRAIT_BUILDING_`、`TRAIT_DISTRICT_`、`TRAIT_UNIT_`、`TRAIT_IMPROVEMENT_`、`BUILDING_`、`DISTRICT_`、`UNIT_`、`IMPROVEMENT_`、`GOVERNOR_`、`POLICY_`、`PROJECT_`、`ABILITY_`、`MODIFIER_`（对应 KIND_* 见游戏 Types 表）。
- ModifierId：`MODIFIER_{前缀}_{编号或语义}_{效果描述}`（如 `MODIFIER_SIQI_0040_PLOT_YIELD_SCIENCE`）。
- RequirementId / RequirementSetId：`REQ_` / `REQSET_` + 前缀 + 描述；Set 与成员共享描述段。
- LOC 键：`LOC_{CONTEXT}_{TYPE}_NAME/DESCRIPTION`，CONTEXT 与实体前缀对应（`TRAIT_CIVILIZATION_`、`CITY_NAME_`、`LOADING_INFO_`、`PEDIA_LEADERS_PAGE_` 等）。
- 文本相同用引用链：`('zh_Hans_CN','LOC_TRAIT_xxx_NAME','{LOC_xxx_NAME}')`；不同则直写。
- 图标嵌入：`[ICON_Science]`、`[ICON_Gold]` 等，必须带文字说明（如 `+{1_Amount}[ICON_Science]科技值`）。
- 语言：主体只写 `zh_Hans_CN`。
- `abbr`/简称只允许英文字母/数字/下划线。

## 4. 相邻加成知识（Adjacency_YieldChanges）

> 工具的区域/改良编辑器内置相邻加成面板（含描述自动生成），此知识用于理解生成产物与手写时的依据。

- 桥接表 `District_Adjacencies`（DistrictType → YieldChangeId）；核心表 `Adjacency_YieldChanges`（20 列）。
- 必写列：`ID`、`Description`、`YieldType`、`YieldChange`、`TilesRequired`（每 N 个相邻格 +1 次）。
- **一条规则只设一个条件**（AdjacentTerrain/AdjacentFeature/AdjacentDistrict/AdjacentRiver/AdjacentWonder/AdjacentNaturalWonder/AdjacentResource/AdjacentResourceClass/AdjacentSeaResource/OtherDistrictAdjacent/Self 等选一）；多条件写多条规则。
- 山脉加成标准写法：5 种 MOUNTAIN 地形各一条（GRASS/PLAINS/DESERT/TUNDRA/SNOW）。
- Description 格式：`{解锁条件} +{1_Amount}[ICON_X]产出 来自相邻的 {条件}。`；数值占位符统一 `{1_Amount}`；改良可写 `Placeholder`。
- 产出图标映射：YIELD_SCIENCE→[ICON_Science]、YIELD_PRODUCTION→[ICON_Production]、YIELD_GOLD→[ICON_Gold]、YIELD_FOOD→[ICON_Food]、YIELD_CULTURE→[ICON_Culture]、YIELD_FAITH→[ICON_Faith]。
- 反向加成：规则 `AdjacentDistrict` 指向自己的区域，再绑定到标准区域（学院→Science、商业/港口→Gold、剧院→Culture、工业→Production、圣地→Faith）。
- 力度等级：少量=每2格+1（TilesRequired=2），标准=每1格+1，大量=每1格+2；无小数。

## 5. 数据库查询参考（DebugGameplay.sqlite）

- 权威数据源：游戏实时库（工具在设置页配置路径，默认 `...\Cache\DebugGameplay.sqlite`）。查表结构、字段名、ModifierType 是否真实存在，以当前环境记录为准；是否原版另查 [原版快照](../../ModTools_5_4/data/vanilla_modifier_types.json)。
- 常见坑：
  - 表名 `Domains` 不存在 → `SELECT DISTINCT Domain FROM Units`；
  - Units 列名是 `PromotionClass`（UnitPromotionClasses 才是 `PromotionClassType`）；
  - `COLLECTION_` 枚举 → `SELECT DISTINCT CollectionType FROM DynamicModifiers`；
  - `REQUIREMENT_`/`EFFECT_` 枚举 → `SELECT DISTINCT ... FROM Requirements / DynamicModifiers`；效果参数可反向从 ModifierArguments 收集；
  - `ICON_` 枚举不在 DB 中，查官方 Icons 文件。
- 核心表速查：DynamicModifiers(ModifierType,CollectionType,EffectType)；Modifiers(ModifierId,ModifierType,RunOnce,Permanent,Owner/SubjectRequirementSetId,SubjectStackLimit)；ModifierArguments(ModifierId,Name,Value)；ModifierStrings(ModifierId,Context,Text)；RequirementSets/Requirements/RequirementArguments/RequirementSetRequirements；Types(Type,Kind)；挂载表 TraitModifiers/PolicyModifiers/BuildingModifiers/DistrictModifiers/UnitAbilityModifiers/UnitPromotionModifiers/GovernorPromotionModifiers/GreatPersonIndividualActionModifiers/GreatPersonIndividualBirthModifiers/ProjectCompletionModifiers/GovernmentModifiers/CivicModifiers/TechnologyModifiers/GameModifiers/GreatWorkModifiers。

## 6. TypeProperties 参考（XML）

- TypeProperties 作用于 **TYPE 级**默认值；Modifier Property 作用于 **INSTANCE 级**运行时。DLL 用 FNV-1a(seed=0xA1AB32F7, prime=0x01000193) 哈希小写 Name。
- 重要规则：Name 与 Type 前缀**强绑定**（UNIT_* 的 LIFESPAN 不能给 IMPROVEMENT_*）；Name 是 DLL 硬编码，**不能自创**。
- 常用：UNIT_*（LIFESPAN、CAN_EVER_TRAIN_BARBARIAN/CITY_STATE/FREE_CITY、IGNORE_PLAYER_STAT_MAX_STRENGTH、CAN_MOVE_AFTER_PURCHASE、CAN_TELEPORT_TO_CITY 等）；IMPROVEMENT_*（PLOT_DAMAGE_TO_WALKING_INTO/ADJACENT）；UNITCOMMAND_*（COST_PROGRESSION_TYPE、RANGE、STRENGTH、XP_EARNED 等）；TRIBE_*（贿赂/雇佣/煽动/劫掠/赎金参数）；DIFFICULTY_*（AI/玩家黑暗时代丢城数等）。

## 7. 常见陷阱速查

- `InheritFrom` 继承的是**特质（Traits）**不是图片/模型；新建领袖用 `LEADER_DEFAULT`。
- CityNames/CitizenNames 需 `INSERT...SELECT` 显式继承。
- 建筑 TraitType 需独立 `TRAIT_BUILDING_xxx`（不共用文明特质）。
- 事件类 Requirement（如 REQUIREMENT_PLAYER_TURN_STARTED）必须写 `Triggered=1`。
- ModifierStrings 预览文本仅 `EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER` 一种效果器支持（Context 固定 Preview）。
  **该效果类型必须写 `preview_text`**（原版 226 个实例里 221 个都写了）：不写不会报错，但**战斗预览面板看不到这层加成的来源**（沉默失效）。
  - 工具链路：`modifier_workspace` 生成 `INSERT INTO ModifierStrings(ModifierId,'Preview','LOC_{ModifierId}_PREVIEW')`，`workspace_page._modifier_strength_preview_text_rows()` 生成对应 LocalizedText 行；**两行都依赖 `preview_text` 非空**。
  - 写法：数值型 `+{1_Amount} [ICON_Strength] 战斗力（来源）`；`Key`（属性）型 `+{Property} [ICON_Strength] 战斗力（来源）`。
  - `modgen validate` 对"该效果类型 + preview_text 为空"给 WARNING。
- 图标引用后必须带文字：`[ICON_xxx] 标签`。
