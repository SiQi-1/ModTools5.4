# 实体命名参考（Type / Modifier / Requirement）

> 受众：写 .CIV 条目、核对生成 Type 与手写 Modifier/Requirement 的制作者 ｜ 何时读：新建实体、命名 Modifier/条件、核对导出 SQL 时 ｜ 适用版本：ModTools 5.4

Type 由生成器按工程"基础信息"的前缀/中缀自动生成，不要手写主表 SQL（见 [规则正文](../../RULES.md) R4）。本文件用于**核对**生成结果，并约定生成器不代劳的 Modifier / Requirement / RequirementSet 命名。

## 一、实体 Type 前缀

| 前缀 | Type Kind | 用途 |
|------|-----------|------|
| `CIVILIZATION_` | `KIND_CIVILIZATION` | 文明 |
| `LEADER_` | `KIND_LEADER` | 领袖 |
| `TRAIT_CIVILIZATION_` | `KIND_TRAIT` | 文明特质 |
| `TRAIT_LEADER_` | `KIND_TRAIT` | 领袖特质 |
| `TRAIT_BUILDING_` | `KIND_TRAIT` | 特色建筑特质 |
| `TRAIT_DISTRICT_` | `KIND_TRAIT` | 特色区域特质 |
| `TRAIT_UNIT_` | `KIND_TRAIT` | 特色单位特质 |
| `TRAIT_IMPROVEMENT_` | `KIND_TRAIT` | 特色改良特质 |
| `TRAIT_GOVERNOR_` | `KIND_TRAIT` | 总督特质 |
| `BUILDING_` | `KIND_BUILDING` | 建筑 |
| `DISTRICT_` | `KIND_DISTRICT` | 区域 |
| `UNIT_` | `KIND_UNIT` | 单位 |
| `IMPROVEMENT_` | `KIND_IMPROVEMENT` | 改良设施 |
| `GOVERNOR_` | `KIND_GOVERNOR` | 总督 |
| `POLICY_` | `KIND_POLICY` | 政策卡 |
| `PROJECT_` | `KIND_PROJECT` | 项目 |
| `ABILITY_` | `KIND_ABILITY` | 单位能力 |
| `MODIFIER_` | `KIND_MODIFIER` | 效果器 |

## 二、实体简称（abbr）与 Type 形态

Type 形态由生成器维护为 `{HEAD}_{前缀}_{中缀}{编号:04d}_{简称}`（例如 `CIVILIZATION_SIQI_C0035_1`）。**简称**（abbr）是条目里需要填写/核对的唯一命名输入：

| 实体 | 简称格式 | 示例 |
|------|----------|------|
| 文明 | `C{编号}` | `C0035` |
| 领袖 | `L{编号}` | `L0035` |
| 建筑 | `B{编号}` | `B0035` |
| 区域 | `D{编号}` | `D0035` |
| 单位 | `U{编号}` | `U0035` |
| 改良 | `I{编号}` | `I0035` |
| 总督 | `GOV{编号}` | `GOV0035` |
| 政策 | `P{编号}` | `P0035` |
| 项目 | `PRJ{编号}` | `PRJ0035` |

数字式命名规则：

- 实体字母 + 项目号 + 下划线 + 实例号；同项目内实例号从 1 递增。
- 特质不单独编号，跟随所属实体（如 `TRAIT_LEADER_SIQI_L0035_1`）。
- 语义式命名（如 `LEADER_SIQI_OBLIVIONIS`）只在用户明确指定语义名时使用，不要自行替换数字编号。

## 三、Modifier / Requirement / RequirementSet 命名

| 对象 | 格式 | 示例 |
|------|------|------|
| Modifier | `MODIFIER_{前缀}_{项目号}_{效果描述}` | `MODIFIER_SIQI_0040_PLOT_YIELD_SCIENCE` |
| Requirement | `REQ_{前缀}_{项目号}_{条件描述}` | `REQ_SIQI_0040_PLOT_ADJACENT_TO_OWNER_3` |
| RequirementSet | `REQSET_{前缀}_{项目号}_{条件描述}` | `REQSET_SIQI_0040_PLOT_ADJACENT_TO_OWNER_3` |

- 效果/条件描述用下划线分隔，包含"作用目标 + 动作 + 效果"。
- RequirementSet 与其内部 Requirement 可共享描述部分，区别只在前缀 `REQSET_` / `REQ_`。
- 生成器会为 `generate-modifier` / `generate-requirement` 产出候选 ID；自定义 ID 必须能追溯到同一语义。

## 四、实体承载审查约束

- 没有用户明确要求时，不得为了承载效果虚构 `BUILDING_*` 或其他实体；应优先把效果挂到官方实体的 `DistrictModifiers`、`BuildingModifiers` 或对应 Modifier 绑定表。
- `REQUIREMENT_CITY_HAS_DISTRICT` 的 `MustBeFunctioning` 使用引擎默认值时不写入 `ModifierArguments`；只有用户明确要求覆盖默认行为时才填写。
- 官方领袖外交背景剪影使用 `<LEADER_SHORT>_4` 条目引用官方对象，不生成仿制剪影图片。
- 历史时刻图片按 ModTools 5.4 的 `456×332` 画布生成，并加入项目 UITexture XLP；`MomentIllustrations.Texture` 必须与 `Moment_<GameDataType>` 一致。

## 五、TypeProperties 与 Modifier Property

- TypeProperties 作用于 **TYPE 级**默认值；Modifier Property 作用于 **INSTANCE 级**运行时。DLL 用 FNV-1a(seed=0xA1AB32F7, prime=0x01000193) 哈希小写 Name。
- Name 与 Type 前缀**强绑定**（`UNIT_*` 的 `LIFESPAN` 不能给 `IMPROVEMENT_*`）；Name 是 DLL 硬编码，**不能自创**。
- 常用族：`UNIT_*`（LIFESPAN、CAN_EVER_TRAIN_BARBARIAN、IGNORE_PLAYER_STAT_MAX_STRENGTH 等）、`IMPROVEMENT_*`（PLOT_DAMAGE_TO_WALKING_INTO/ADJACENT）、`UNITCOMMAND_*`（COST_PROGRESSION_TYPE、RANGE、STRENGTH、XP_EARNED）、`TRIBE_*`、`DIFFICULTY_*`。工具表单内选择，不要手写。

## 相关

- LOC 文本键命名 → [文本规范](../config/text.md)。
- Lua 函数/事件命名 → [Lua 规范](../lua/code-style.md)。
- 生成 SQL 的表顺序核对 → [SQL 参考索引](../sql/INDEX.md)。