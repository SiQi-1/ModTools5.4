# .CIV 必炸清单与工具契约（civ-pitfalls）

> 本页记录 .CIV 落地时的常见问题。行为边界见 [规则正文](../RULES.md)，当前操作见 [统一工作流](../WORKFLOW.md)。

## 工具契约（ModTools 边界，违反 = 工具无法生成或生成错误）

| # | 规则 | 说明 |
|---|------|------|
| 1 | **禁 Lua** | 主内容不包含 Lua；自定义 Lua/UI XML 经 custom-file 写入并注册，见 [交付指南](pipeline.md) |
| 2 | **JSON 禁 `""`** | 空值 = 省略字段或写 `null`；写 `""` 会生成 `''` 导致类型/外键失败。AI 写文件时必须清零；执行 modgen validate，并检查 AI 填写字段 |
| 3 | **section 顺序固定** | 18 section 按 `CIV_SECTION_ORDER` 排列；多余/缺失由加载器归一化（写时仍按顺序） |
| 4 | **Type 由工具自动生成** | 前缀+infix+4位编号+缩写；手写 `type` 字段须符合同一格式，禁止自创前缀 |
| 4b | **实体外的 UI 图标走「UI图标」段** | 新闻分类/单位动作/追踪器等**不属于任何游戏实体**的图标写进 `UI图标` 段（`icon_name` + `images.icon.path` + `sizes`）；`icon_name` 不得落进实体内置命名空间（`ICON_<实体类型>_*`，含 `_PORTRAIT`），源 PNG 必须存在，否则 `modgen validate` / GUI 生成前检查报 ERROR |

## 游戏层必炸（.CIV 落地形态）

| # | 陷阱 | .CIV 中的纠正 |
|---|------|--------------|
| 5 | `InheritFrom` 继承特质非图片 | 领袖/建筑等 `InheritFrom` 一律 `LEADER_DEFAULT` 等游戏既有类型，且须在 DB 验证 |
| 6 | CityNames/CitizenNames 不自动继承 | `city_info`/`citizen_info` 必须显式给（工具据此生成 `INSERT...SELECT`） |
| 7 | 建筑 TraitType 复用文明特质 | 建筑须独立 `TRAIT_BUILDING_xxx`（模板中 `trait_bindings`/`new_trait_type` 字段处理） |
| 8 | 图标后裸写 `[ICON_xxx]` | 必带文字：`+{1_Amount}[ICON_Science] 科技值`；ICON 拼写查快照 `font_icons_registry.json` |
| 9 | 事件类 Requirement 漏 `Triggered` | `requirements[].triggered` 必须 `true`（如 `REQUIREMENT_PLAYER_TURN_STARTED`） |
| 10 | Modifier 链断在关联表 | `owners[].table_name` + `bound_modifier_ids` 必须形成完整挂载链；写完对照 [规则正文](../RULES.md) |
| 11 | EffectType/RequirementType 凭记忆 | 必须查游戏 DB（`DynamicModifiers`/`Requirements`）或快照 `data/effect_type_parameters.json` |
| 12 | 参数值 `"true"/"false"` 歧义 | 布尔参数工具会转 `1/0`（有意设计）；数值参数别写引号内 |
| 13 | 战斗力类 Modifier 漏 `preview_text` | EffectType = `EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER` 的条目**必须填 `preview_text`**（`.CIV` 的 `modifiers[].preview_text`）。不填不报错，但**战斗预览面板看不到加成来源**；`modgen validate` 会给 WARNING。占位符用 `{1_Amount}`（数值）/ `{Property}`（Key 属性），**别写 `{Amount}`**（详见 `07-techniques/modifier-techniques.md` 技巧 3） |
| 14 | 世界奇观效果挂 `DISTRICT_WONDER` | 奇观**落位**即生成虚拟 `DISTRICT_WONDER` 区域 → **未建成就生效**。必须改挂 `BuildingModifiers`：`INSERT INTO BuildingModifiers (BuildingType, ModifierId) SELECT BuildingType, '<ModifierId>' FROM Buildings WHERE IsWonder = 1;`（走自定义文件通道，独立动作 id + `LoadOrder 199999`）。详见 `07-techniques/modifier-techniques.md` 技巧 4 |
| 15 | 建筑挂载的城市级效果把需求写错侧（或把 subject 当"这个建筑"） | 建筑挂载 + **城市级**效果时 **subject 就是城市**：城市/地块级需求写 `subject_reqset`（地块按**城市地块=市中心格**求值），**玩家/领袖级需求（本文明、某领袖）写 `owner_reqset`**（0050 `REQSET_SIQI_0050_IS_LEADER` ×20 条建筑挂载先例；原版 `KILWA_*` 也有写 subject 侧的，本工程统一 owner 侧）。`PLOT_ADJACENT_TO_OWNER` 的 **owner = 挂载对象**（改良设施/伟人/奇观本体），不是玩家 → "该奇观与这座城市相邻 1 环" 用 `{MinDistance=1, MaxDistance=1}`；`PLOT_ADJACENT_DISTRICT_TYPE_MATCHES{DISTRICT_CITY_CENTER}` 是**自指恒假**。产出类型优先 cities 版 `MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_MODIFIER`。详见 `07-techniques/modifier-techniques.md` 技巧 4 |
| 16 | 给建筑发遗物/放巨作，但建筑没在 `Building_GreatWorks` 登记槽位 | `EFFECT_GRANT_RELIC` 找"能装遗物的建筑"只认 `Building_GreatWorks` 的**登记行**，**Modifier 给的槽不算**（`EFFECT_ADJUST_EXTRA_GREAT_WORK_SLOTS` 只加容量）。给原版建筑补登记行要写自定义 SQL：`INSERT OR IGNORE … SELECT … WHERE NOT EXISTS(…)`（主键 `(BuildingType,GreatWorkSlotType)`，`NumSlots` 默认 1 所以要显式写 0），**只 INSERT 不 UPDATE**，独立动作 id + 尽量晚的 `LoadOrder`。槽类型别写错：遗物必须 `GREATWORKSLOT_RELIC`（写成 `PALACE` UI 照样显示但遗物进不去）。详见技巧 5 |
| 17 | 只改了 ModBuddy 工程目录，忘了游戏 Mods 目录 | 工具只写 ModBuddy 端；游戏读的是 `文档\My Games\…\Mods\<工程名>\`。改完必须同步：生成文件按**哈希比对**只复制 DIFF 的；新增自定义 SQL 还要在 `.modinfo` 的 `InGameActions` 加同 id/同 `LoadOrder` 动作块 + `<Files>` 加一行。`add_file_action` 之后**必须 `save_project`**，否则动作只存在内存里，下次 `generate_all` 就没了 |

## 命名速记（见 [命名参考](../06-naming.md) 与 [制作参考](authoring-reference.md)）

- 前缀体系：`CIVILIZATION_`/`LEADER_`/`TRAIT_CIVILIZATION_`/`TRAIT_LEADER_`/`BUILDING_`/`DISTRICT_`/`UNIT_`/`IMPROVEMENT_`/`GOVERNOR_`/`POLICY_`/`PROJECT_`/`ABILITY_`/`MODIFIER_`
- ModifierId：`MODIFIER_{前缀}_{编号或语义}_{效果描述}`（如 `MODIFIER_SIQI_0040_PLOT_YIELD_SCIENCE`）
- Requirement/Set：`REQ_` / `REQSET_` + 前缀 + 描述；Set 与成员共享描述段
- LOC：`LOC_{CONTEXT}_{TYPE}_NAME/DESCRIPTION`（`TRAIT_CIVILIZATION_`/`CITY_NAME_`/`LOADING_INFO_`/`PEDIA_LEADERS_PAGE_` 等）
- 语言：主体只写 `zh_Hans_CN`；相同文本用引用链 `('zh_Hans_CN','LOC_xxx_NAME','{LOC_yyy_NAME}')`，不同则直写
- `abbr`/缩写只允许英文字母/数字/下划线

## 自检清单（写完后逐项勾）

- [ ] `python -m modgen.cli validate 工程.CIV` 无 ERROR，AI 填写 JSON 无空字符串
- [ ] 主内容无 Lua；自定义 Lua / UI XML 已通过工具注册
- [ ] 已有 Type 已核实来源；本工程新增 Type 的生成注册齐全（不能要求未加载的新 Type 已在游戏缓存中）
- [ ] 事件类 Requirement `triggered=true`；Modifier 挂载链完整
- [ ] 战斗力类 Modifier（EffectType = `EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER`）都填了 `preview_text`（否则战斗预览不显示来源）
- [ ] 建筑挂载的城市级效果：城市/地块级需求在 **subject 侧**、玩家/领袖级在 **owner 侧**，且没有"城市相邻市中心"这类自指需求（陷阱 15）
- [ ] 依赖"引擎自己找空槽位"的效果（发遗物/放巨作）已确认目标建筑在 `Building_GreatWorks` 有登记行（陷阱 16）
- [ ] 生成后同步到游戏 Mods 目录（哈希比对复制 + 新自定义 SQL 补 `.modinfo` 动作），并确认 `add_file_action` 后已 `save_project`（陷阱 17）
- [ ] 图标字段路径不虚构，无图时留 `{}`（模板字段 `images` 为空对象）
- [ ] 实体之外的 UI 图标已写进 `UI图标` 段（不是硬塞进某个实体的 `icon_image_name`），且 `icon_name` 不占用 `ICON_<实体类型>_*` 命名空间、源 PNG 真实存在（陷阱 4b）
- [ ] 文本 LOC 键与 `skills/02-config-files/text.md` 引用链一致
