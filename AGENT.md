# AGENT.md — ModTools AI 协作规范与知识库

> **任务分流**：本文件是**实际应用向**（写 .CIV / 答文明6 Mod 制作问题）的规范与知识库。
> **工具优化向**（改 ModTools/modgen 代码、测试、打包）请读根目录 `CLAUDE.md`，本文件大部分内容与任务无关；
> 通用任务分流见根目录 `AGENTS.md`；modgen 工具用法见 `modgen/AGENTS.md`（硬规则与本文件同源，任一处为准）。

> **强制阅读**：任何 AI/agent 在本仓库（ModTools 5.4）内工作、特别是**编写 .CIV 工程文件**或回答文明6 mod 制作问题时，必须先完整阅读本文件。规则优先于任何"合理想象"。
>
> **薄指针**：本文件只含工具专属规则。文明6 **游戏深度知识**（Modifier/Requirement/文本/图标/DB 验证、Lua API 等 260+ 技能文件）在**仓库根 `skills/`**（随发布包分发；入口 `skills/AGENTS.md`，检索用 `python -m modgen.cli skill <关键词>`）。写 .CIV 时缺知识先查那边，别在本仓库重新积累（单一知识源，防漂移）。
> **单会话交付**：.CIV + 特殊 SQL/Lua 补丁一体化流水线见 `skills/05-modtools-civ/pipeline.md`（本地）；无头导出用 `modgen preview`（工具内置，需 PyQt）或 GUI/AI 接口 `generate_all`。

---

## 0. 本项目是什么、不是什么

- ModTools 是**可视化编辑工具**：AI 的工作是**编写 `.CIV` 工程文件（JSON，schema 0.1.0）**，由工具生成 SQL/XML/图标/ArtDef/XLP 等所有输出。**主内容（13 分类/修改器/文本）AI 不直接写 SQL/XML**；确需自定义 SQL/XML/Lua 时，**只能走"自定义文件通道"**（见下节）——工具仍是唯一写入者。
- 输出模型：`workspace` 是 section 索引字典，顺序固定（`CIV_SECTION_ORDER`，18 节）。基础信息/美术/文本/修改器 4 节存 dict，其余各节存条目列表（含「UI图标」）。
- **「UI图标」段**（2026-09-19）：声明**与游戏实体无关**的自定义 UI 图标（新闻分类、单位动作、追踪器等），
  条目形如 `{"icon_name":"ICON_X","name_zh":"备注","sizes":[32,50],"images":{"icon":{"path":"D:/x.png"}}}`。
  只影响 `Icons.xml` 与 IMG/Textures，**不产出 SQL / Players / 文本**；图集名自动为 `ATLAS_X`；
  `alias` 非空则改用该图标、不自带图集；`icon_name` 不得落进实体内置图标命名空间（`ICON_<实体类型>_*`）。
- Type 命名由工具按 `{表前缀}_{前缀}_{中缀}{4位编号}_{简称}` 自动生成（前缀/中缀来自"基础信息"配置），AI 写入 `type` 字段时遵循同一格式即可。

## ⚠️ Lua 与自定义 SQL/XML —— 仅走"自定义文件通道"

- **主内容禁止 Lua**：.CIV 条目与生成器输出**不包含、不生成 Lua**——遇到需要 Lua 的需求（UI 面板、事件脚本、自定义逻辑），引导用户走自定义文件通道，而不是塞进 .CIV。
- **自定义文件通道（2026-08-17 起允许）**：确需 Lua / 自定义 SQL/XML 补丁时，AI 必须**经工具写入**（绝不手工散落文件）：
  - 无头：`python -m modgen.cli custom-file write 工程.CIV --path Scripts/My.lua --content-file modgen_work/My.lua`（内容临时文件放 `modgen_work/`）；
  - GUI 接管：AI 控制接口 `project_file_write`（`--ai-port` HTTP / `--ai-exec`，同语义）；
  - 自动按路径注册文件动作并进 .CIV：`Scripts/*.lua`→AddGameplayScripts、`UI/*.xml+lua`→AddUserInterfaces、`Import/*.lua`→ImportFiles、`Data/*.sql|xml`→UpdateDatabase、`Icons/`→UpdateIcons、`Text/`→UpdateText（`--action` 可显式指定）。
- 文件写入 `.civ6proj` 工程目录，**一键生成原样透传**（不重新生成、不改写）；路径穿越被拒绝；`custom-file remove` / `project_file_delete` 可删除。
- 内容质量由 AI 负责（工具不校验 Lua 语法/游戏 API）；SQL 里引用的 ModifierType 等仍须遵守硬规则一；Lua 仅用于 Modifier/Requirement 体系无法覆盖的少数场景，能不用就不用。

## 1. 硬规则一：ModifierType / EffectType / RequirementType 优先引用已有类型

- Modifier 的 `ModifierType` **必须优先**从游戏数据库 `DynamicModifiers` 表选择**已存在**的类型；EffectType / RequirementType / CollectionType 同理（库中真实存在才允许引用）。
- **确需自定义新 ModifierType 时**（该表确实不存在符合语义的类型才允许）：
  - 命名遵循 `MODIFIER_{前缀}_{语义}`，不允许裸名；
  - 必须同时补 `DynamicModifiers` 行（ModifierType/CollectionType/EffectType），且 CollectionType 与 EffectType 必须是已存在类型。
- 查询方式：`SELECT ModifierType, CollectionType, EffectType FROM DynamicModifiers`（工具内也有 ModifierType 搜索）。不确定就查，禁止凭记忆编造。
  ⚠ **但"库里查得到"≠"这是原版类型"**：`DebugGameplay.sqlite` 是运行缓存，**玩家装过的每个 Mod 注册的类型都在里面**（实测本机 1024 条里 57 条非原版）。
  - 判断是否原版，看随包分发的**原版快照** `ModTools_5_4/data/vanilla_modifier_types.json`（989 条，由 `python -m modgen.tools.extract_vanilla_modifier_types` 从游戏自带 XML 提取）；
  - 生成器按快照决定是否补 `Types` + `DynamicModifiers` 行：**不在快照里 = 本工程新建，必须补**；
  - 条目可用 `modifier_type_source` 覆盖自动判定（`null` 自动 / `"new"` 强制新建 / `"vanilla"` 强制视为游戏已有）；
  - 引用了别人 Mod 的类型而不补行 → 在**没装那个 Mod 的机器上加载失败**；`modgen validate` 会对此报 ERROR。

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
  **该效果类型必须写 `preview_text`**（原版 226 个实例里 221 个都写了）：不写不会报错，但**战斗预览面板看不到这层加成的来源**（沉默失效）。
  - 工具链路：`modifier_workspace` 生成 `INSERT INTO ModifierStrings(ModifierId,'Preview','LOC_{ModifierId}_PREVIEW')`，`workspace_page._modifier_strength_preview_text_rows()` 生成对应 LocalizedText 行；**两行都依赖 `preview_text` 非空**。
  - 写法：数值型 `+{1_Amount} [ICON_Strength] 战斗力（来源）`；`Key`（属性）型 `+{Property} [ICON_Strength] 战斗力（来源）`。
  - `modgen validate` 对"该效果类型 + preview_text 为空"给 WARNING。
- 图标引用后必须带文字：`[ICON_xxx] 标签`。

## 8. 写完 .CIV 的自检清单

- [ ] 所有 ModifierType/EffectType/RequirementType/CollectionType 都查过游戏库（新类型极少且已写 DynamicModifiers 行）
- [ ] 自定义 ModifierType（不在 `data/vanilla_modifier_types.json` 快照中的）已确认会被注册：`modgen validate` 无「强制已有却不在快照」ERROR
- [ ] JSON 中无任何 `""` 值（自查搜索 `": \"\""`）
- [ ] 所有 Type/外键引用在游戏库中存在
- [ ] 必填字段齐全（UI 中带 `*` 的字段）
- [ ] 命名遵循前缀约定；主内容无任何 Lua；自定义 SQL/XML/Lua 一律经 `custom-file` / `project_file_write` 写入并已注册文件动作
- [ ] 图片字段不虚构路径，无图写 `{}`
