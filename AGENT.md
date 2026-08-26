# AGENT.md — ModTools AI 协作规范与知识库

> **强制阅读**：任何 AI/agent 在本仓库（ModTools 5.4）内工作、特别是**编写 .CIV 工程文件**或回答文明6 mod 制作问题时，必须先完整阅读本文件。规则优先于任何"合理想象"。
>
> **薄指针**：本文件只含工具专属规则。文明6 **游戏深度知识**（Modifier/Requirement/文本/图标/DB 验证，137+ 技能文件）在 `D:\文明6mod用文件夹\AI制作Mod\skills\`（入口 `AGENTS.md`，.CIV 工作流见 `skills/05-modtools-civ/INDEX.md`）。写 .CIV 时缺知识先查那边，别在本仓库重新积累（单一知识源，防漂移）。
> **单会话交付**：.CIV + 特殊 SQL/Lua 补丁一体化流水线见 `AI制作Mod/skills/05-modtools-civ/pipeline.md`；无头导出用 `AI制作Mod/export_modtools.py`（本仓库 `.venv` 的 python 运行）。

---

## 0. 本项目是什么、不是什么

- ModTools 是**可视化编辑工具**：AI 的工作是**编写 `.CIV` 工程文件（JSON，schema 0.1.0）**，由工具生成 SQL/XML/图标/ArtDef/XLP 等所有输出。**AI 不直接写 SQL/XML 文件**（SQL 仅出现在向用户解释或检查生成的产物时）。
- 输出模型：`workspace` 是 section 索引字典，顺序固定（`CIV_SECTION_ORDER`，17 节）。基础信息/美术/文本/修改器 4 节存 dict，其余各节存条目列表。
- Type 命名由工具按 `{表前缀}_{前缀}_{中缀}{4位编号}_{简称}` 自动生成（前缀/中缀来自"基础信息"配置），AI 写入 `type` 字段时遵循同一格式即可。

## ⚠️ 禁止 Lua —— 必须向用户强调

**本项目不生成、不编写、不支持 Lua**（GamePlay/UI 脚本均不支持）。这是工具能力边界，不是知识缺口：

- 不得在 .CIV 内容、生成输出、或给用户的方案中包含任何 Lua 脚本/UI.xml 能力；
- 用户需求涉及 Lua（如 UI 面板、事件脚本、自定义操作逻辑）时，**必须明确告知用户："本工具无法编写 Lua 能力"**，并引导其用 SQL/Modifier 系统可实现的替代方案；
- 不要引用任何 Lua API、事件、模板——那是其他工作流的知识，与本工具无关。

## 1. 硬规则一：ModifierType / EffectType / RequirementType 优先引用已有类型

- Modifier 的 `ModifierType` **必须优先**从游戏数据库 `DynamicModifiers` 表选择**已存在**的类型；EffectType / RequirementType / CollectionType 同理（库中真实存在才允许引用）。
- **确需自定义新 ModifierType 时**（该表确实不存在符合语义的类型才允许）：
  - 命名遵循 `MODIFIER_{前缀}_{语义}`，不允许裸名；
  - 必须同时补 `DynamicModifiers` 行（ModifierType/CollectionType/EffectType），且 CollectionType 与 EffectType 必须是已存在类型。
- 查询方式：`SELECT ModifierType, CollectionType, EffectType FROM DynamicModifiers`（工具内也有 ModifierType 搜索）。不确定就查，禁止凭记忆编造。

## 2. 硬规则二：JSON 值禁止写 `""`（空字符串）

| 写法 | 含义 | 生成 SQL | 后果 |
|------|------|----------|------|
| 字段省略 | 使用默认值 | 列不出现/NULL | ✅ 正确 |
| `null` | 显式 NULL | `NULL` | ✅ 正确 |
| `""` | 空字符串 | `''` | ❌ **严重报错**：类型/外键失败 |
| `"NONE"` | 字符串 NONE | `'NONE'` | ❌ 不是通用空值（仅极少数游戏对象真的叫 NONE） |

- 参数（ModifierArguments/RequirementArguments 的 `value`）、子表行字段一律不得写 `""`；
- 空值 → 省略字段/整行，或写 `null`；别写 `"null"` 字符串；
- 字符串 `"true"`/`"false"` 参数会被工具按布尔转 `1`/`0`（有意设计）；
- 布尔字段用 0/1 或 true/false 均可（工具归一化），但别用 `""`。
- 生成器已兜底（空参数行跳过、`None` 输出 NULL），但 AI 不应依赖兜底。

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

- 权威数据源：游戏实时库（工具在设置页配置路径，默认 `...\Cache\DebugGameplay.sqlite`）。查表结构、字段名、ModifierType 是否真实存在，**以此为准**。
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
- 图标引用后必须带文字：`[ICON_xxx] 标签`。

## 8. 写完 .CIV 的自检清单

- [ ] 所有 ModifierType/EffectType/RequirementType/CollectionType 都查过游戏库（新类型极少且已写 DynamicModifiers 行）
- [ ] JSON 中无任何 `""` 值（自查搜索 `": \"\""`）
- [ ] 所有 Type/外键引用在游戏库中存在
- [ ] 必填字段齐全（UI 中带 `*` 的字段）
- [ ] 命名遵循前缀约定；无任何 Lua 相关内容
- [ ] 图片字段不虚构路径，无图写 `{}`
