# modifier-diplomacy -- 外交/影响力/使者/不满/议程类 EffectType — 外交行动/产出

> 分册：由 [modifier-diplomacy.md](modifier-diplomacy.md) 按主题拆出；覆盖 外交行动、EFFECT_ADD_DIPLOMATIC_ACTION_OVERRIDE、EFFECT_ADJUST_DIPLOMATIC_ACTION_PREFERENCE、EFFECT_ADJUST_BANNED_DIPLOMATIC_ACTIONS、EFFECT_ADJUST_BANNED_DIPLOMATIC_ACTIONS_SPECIFIC_CIVILIZATION、外交产出修正、EFFECT_ADD_DIPLOMATIC_COMBAT_MODIFIER、EFFECT_ADD_DIPLOMATIC_MOVEMENT_MODIFIER、EFFECT_ADD_DIPLOMATIC_YIELD_MODIFIER、外交能见度、EFFECT_ADD_DIPLO_VISIBILITY、EFFECT_ADJUST_UNIT_DIPLO_VISIBILITY_COMBAT_MODIFIER、外交分数、EFFECT_ADJUST_DIPLOMATIC_SCORE `[无官方使用示例，但 Mod 中可用]`。触发：改外交行动、外交产出、能见度、分数时。

## 外交行动

### EFFECT_ADD_DIPLOMATIC_ACTION_OVERRIDE

允许玩家执行原本不可用的外交行动（如通过市政解锁特殊宣战理由）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADD_DIPLOMATIC_ACTION_OVERRIDE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `CivicType` | 来源指定 | `CIVIC_*` — 触发该覆盖的市政 |
| `DiplomaticAction` | **必写** | `DIPLOACTION_*` — 允许执行的外交行动 |

> 原版示例：通过 `CIVIC_DEFENSIVE_TACTICS` 解锁 `DIPLOACTION_DECLARE_LIBERATION_WAR`。
>
> 可选值来自 `DiplomaticActions` 表（`DiplomaticActionType` 列），含宣战理由、联盟、使馆、边界开放、交易等 45 种行动，不限于宣战类。

---

### EFFECT_ADJUST_DIPLOMATIC_ACTION_PREFERENCE

调整AI对外交行动的偏好（倾向/回避某类行动）。支持逗号分隔多个外交行动。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_ADJUST_DIPLOMATIC_ACTION_PREFERENCE` | `COLLECTION_ALL_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Action` | **必写** | `DIPLOACTION_*` — 可多个以逗号分隔 |
| `Favored` | **必写** | `0` = 回避, `1` = 倾向 |

> 数据库中有活跃使用（如 `TRAIT_BEFRIEND_MINOR_CIV_HOME_CONTINENT`），确认支持逗号分隔多个外交行动。

---

### EFFECT_ADJUST_BANNED_DIPLOMATIC_ACTIONS

禁止某一类外交行动。数据库中有活跃使用（如禁止突袭战争）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_BANNED_DIPLOMATIC_ACTION` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Banned` | **必写** | `true` = 禁止, `false` = 允许 |
| `DiplomaticActionType` | **必写** | `DiplomaticActions.DiplomaticActionType` — 如 `DIPLOACTION_DECLARE_SURPRISE_WAR` |

> 引用 `DiplomaticActions` 表的 `DiplomaticActionType` 列。注意与 #1 `EFFECT_ADD_DIPLOMATIC_ACTION_OVERRIDE` 的参数名不同（`DiplomaticActionType` vs `DiplomaticAction`），但引用同一张表。

---

### EFFECT_ADJUST_BANNED_DIPLOMATIC_ACTIONS_SPECIFIC_CIVILIZATION

禁止对特定文明执行某类外交行动。数据库中有活跃使用（如 Siqi Myrtle 文明之间的突袭战争限制）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_BANNED_DIPLOMATIC_ACTION_SPECIFIC_CIVILIZATION` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `CivilizationType` | **必写** | `Civilizations.CivilizationType` — 目标文明 |
| `DiplomaticActionType` | **必写** | `DiplomaticActions.DiplomaticActionType` — 被禁的外交行动类型 |

---

## 外交产出修正

### EFFECT_ADD_DIPLOMATIC_COMBAT_MODIFIER

因外交事件（如发动领土扩张战争）获得外交战斗加成。

> 此 EffectType 存在于 Effects.csv 中，但在游戏 C++ 逻辑中定义，数据库中无参数结构可查。以下参数为从实际使用实例（`TRAIT_TERRITORIAL_WAR_COMBAT`）搜集推定。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADD_DIPLOMATIC_COMBAT_MODIFIER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 战斗加成值 |
| `DiplomaticYieldSource` | **必写** | `TERRITORIAL_EXPANSION_WAR_INITIATED` / `SURPRISE_WAR_INITIATED` / `CITY_CAPTURED` 等 |
| `ReligiousOnly` | 可选 | `0` = 所有单位, `1` = 仅宗教单位 |
| `TurnsActive` | **必写** | 整数 — 持续回合数 |

---

### EFFECT_ADD_DIPLOMATIC_MOVEMENT_MODIFIER

因外交事件获得外交移动力加成。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADD_DIPLOMATIC_MOVEMENT_MODIFIER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 移动力加成值 |
| `DiplomaticYieldSource` | **必写** | 同 `EFFECT_ADD_DIPLOMATIC_COMBAT_MODIFIER` |
| `TurnsActive` | **必写** | 整数 — 持续回合数 |

---

### EFFECT_ADD_DIPLOMATIC_YIELD_MODIFIER

因外交事件获得产出加成（如占领城市后 +20% 生产力）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADD_DIPLOMATIC_YIELD_MODIFIER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 产出加成百分比 |
| `DiplomaticYieldSource` | **必写** | 同 `EFFECT_ADD_DIPLOMATIC_COMBAT_MODIFIER` |
| `StackWithOtherDiploYieldModifiers` | 可选 | `0` = 不可叠加, `1` = 可叠加 |
| `TurnsActive` | **必写** | 整数 — 持续回合数 |
| `YieldType` | **必写** | `YIELD_PRODUCTION` / `YIELD_GOLD` / `YIELD_SCIENCE` 等 |

---

## 外交能见度

### EFFECT_ADD_DIPLO_VISIBILITY

增加外交能见度等级。每个能见度等级在战斗时提供 +3 战斗力（随等级差浮动）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADD_DIPLO_VISIBILITY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 能见度等级增量。示例值: `1`（商路驿站特质）, `2`（印刷术科技） |
| `Source` | **必写** | 标识来源。官方值: `SOURCE_ALLY` / `SOURCE_DELEGATE` / `SOURCE_GREAT_PERSON_JOURNALISM` / `SOURCE_SPY` / `SOURCE_TECH` / `SOURCE_TRADER` / `SOURCE_TRADING_POST_TRAIT` / `SOURCE_TRAIT`。可自定义，但需在新表（`DiploVisibilitySources`）定义其文本 |
| `SourceType` | **必写** | `DIPLO_SOURCE_ALL_NAMES` / `DIPLO_SOURCE_FEMALE_ONLY` — 固定二选一 |

> `Source` 参数如使用自定义值，须参考 Core Mod 写法，在 `DiploVisibilitySources` 表中新增条目并提供 `LOC_` 文本。

---

### EFFECT_ADJUST_UNIT_DIPLO_VISIBILITY_COMBAT_MODIFIER

根据与对手的外交能见度等级差，额外调整单位战斗力。游戏默认机制：每级能见度差提供 +3 战斗力，此效果设置 `Amount=3` 即在此基础上翻倍（每级差共 +6）。`Amount=6` 则为三倍。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_UNITS_ADJUST_DIPLO_VISIBILITY_COMBAT_MODIFIER` | `COLLECTION_PLAYER_UNITS` |
| `MODIFIER_ALL_UNITS_ADJUST_DIPLO_VISIBILITY_COMBAT_MODIFIER` | `COLLECTION_ALL_UNITS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 每级能见度差的额外战斗力。注意：游戏默认 +3，`Amount=3` 相当于x2（总 +6/级），`Amount=6` 相当于x3。示例值: `3` |

> `DeltaWithOpponent` 在 Effects.csv 中无记录，一般不写。蒙古特色能力即使用此效果（骑兵按能见度差获得战斗力）。

---

## 外交分数

### EFFECT_ADJUST_DIPLOMATIC_SCORE `[无官方使用示例，但 Mod 中可用]`

调整外交分数。

| ModifierType | CollectionType |
|-------------|----------------|
| （未在数据库中活跃使用） | |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 外交分数修正值 (ESTIMATED) |

> 来源: `reference/csv-export/Effects.csv` EFFECT_ADJUST_DIPLOMATIC_SCORE 行。非官方效果，当前无活跃数据库实例。

---

