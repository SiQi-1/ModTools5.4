# .CIV 必炸清单与工具契约（civ-pitfalls）

> 合并来源：ModTools5.4 AGENT.md（工具契约）+ 本仓库 AGENTS.md §5（游戏层必炸清单）。
> 本文件是**交集提炼**：游戏层完整清单仍以 AGENTS.md §5 为准，此处只写 .CIV 落地时的高频坑。

## 工具契约（ModTools 边界，违反 = 工具无法生成或生成错误）

| # | 规则 | 说明 |
|---|------|------|
| 1 | **禁 Lua** | 工具不生成/不写 Lua、UI.xml。需求涉动态逻辑 → 明确告知用户该部分需手写（本仓库工作流 C/D） |
| 2 | **JSON 禁 `""`** | 空值 = 省略字段或写 `null`；写 `""` 会生成 `''` 导致类型/外键失败。AI 写文件时必须清零（`check_civ.py` 会警告；工具自身保存的占位空串如 random_entries 空槽不算错误） |
| 3 | **section 顺序固定** | 17 section 按 `CIV_SECTION_ORDER` 排列；多余/缺失由加载器归一化（写时仍按顺序） |
| 4 | **Type 由工具自动生成** | 前缀+infix+4位编号+缩写；手写 `type` 字段须符合同一格式，禁止自创前缀 |

## 游戏层必炸（.CIV 落地形态）

| # | 陷阱 | .CIV 中的纠正 |
|---|------|--------------|
| 5 | `InheritFrom` 继承特质非图片 | 领袖/建筑等 `InheritFrom` 一律 `LEADER_DEFAULT` 等游戏既有类型，且须在 DB 验证 |
| 6 | CityNames/CitizenNames 不自动继承 | `city_info`/`citizen_info` 必须显式给（工具据此生成 `INSERT...SELECT`） |
| 7 | 建筑 TraitType 复用文明特质 | 建筑须独立 `TRAIT_BUILDING_xxx`（模板中 `trait_bindings`/`new_trait_type` 字段处理） |
| 8 | 图标后裸写 `[ICON_xxx]` | 必带文字：`+{1_Amount}[ICON_Science] 科技值`；ICON 拼写查快照 `font_icons_registry.json` |
| 9 | 事件类 Requirement 漏 `Triggered` | `requirements[].triggered` 必须 `true`（如 `REQUIREMENT_PLAYER_TURN_STARTED`） |
| 10 | Modifier 链断在关联表 | `owners[].table_name` + `bound_modifier_ids` 必须形成完整挂载链；写完对照 AGENTS.md §5 陷阱 12 |
| 11 | EffectType/RequirementType 凭记忆 | 必须查游戏 DB（`DynamicModifiers`/`Requirements`）或快照 `data/effect_type_parameters.json` |
| 12 | 参数值 `"true"/"false"` 歧义 | 布尔参数工具会转 `1/0`（有意设计）；数值参数别写引号内 |

## 命名速记（详情 `skills/06-naming.md` + 工具 AGENT.md §3）

- 前缀体系：`CIVILIZATION_`/`LEADER_`/`TRAIT_CIVILIZATION_`/`TRAIT_LEADER_`/`BUILDING_`/`DISTRICT_`/`UNIT_`/`IMPROVEMENT_`/`GOVERNOR_`/`POLICY_`/`PROJECT_`/`ABILITY_`/`MODIFIER_`
- ModifierId：`MODIFIER_{前缀}_{编号或语义}_{效果描述}`（如 `MODIFIER_SIQI_0040_PLOT_YIELD_SCIENCE`）
- Requirement/Set：`REQ_` / `REQSET_` + 前缀 + 描述；Set 与成员共享描述段
- LOC：`LOC_{CONTEXT}_{TYPE}_NAME/DESCRIPTION`（`TRAIT_CIVILIZATION_`/`CITY_NAME_`/`LOADING_INFO_`/`PEDIA_LEADERS_PAGE_` 等）
- 语言：主体只写 `zh_Hans_CN`；相同文本用引用链 `('zh_Hans_CN','LOC_xxx_NAME','{LOC_yyy_NAME}')`，不同则直写
- `abbr`/缩写只允许英文字母/数字/下划线

## 自检清单（写完后逐项勾）

- [ ] `python check_civ.py <文件.CIV>` 通过（结构 + 无 `""`）
- [ ] 全文 grep 无 `.lua` 引用（除说明文字）
- [ ] 每个新 Type 在游戏 DB 可查（`DebugGameplay.sqlite`，AGENTS.md §2 优先级）
- [ ] 事件类 Requirement `triggered=true`；Modifier 挂载链完整
- [ ] 图标字段路径不虚构，无图时留 `{}`（模板字段 `images` 为空对象）
- [ ] 文本 LOC 键与 `skills/02-config-files/text.md` 引用链一致
