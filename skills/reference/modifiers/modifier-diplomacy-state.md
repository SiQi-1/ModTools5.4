# modifier-diplomacy -- 外交/影响力/使者/不满/议程类 EffectType — 外交状态

> 分册：由 [modifier-diplomacy.md](modifier-diplomacy.md) 按主题拆出；覆盖 外交状态、EFFECT_DIPLOMACY_ARCHAEOLOGY、EFFECT_DIPLOMACY_BROKEN_PLEDGE、EFFECT_DIPLOMACY_BROKEN_PROMISE、EFFECT_DIPLOMACY_CULTURAL_ID、EFFECT_DIPLOMACY_ESPIONAGE、EFFECT_DIPLOMACY_FORCE_INCURSION、EFFECT_DIPLOMACY_GOVERNMENTS、EFFECT_DIPLOMACY_KEPT_PLEDGE、EFFECT_DIPLOMACY_KEPT_PROMISE、EFFECT_DIPLOMACY_NEW_WARMONGER、EFFECT_DIPLOMACY_NO_PLEDGE、EFFECT_DIPLOMACY_NO_PROMISE、EFFECT_DIPLOMACY_RANDOM、EFFECT_DIPLOMACY_SETTLED_CITIES、EFFECT_DIPLOMACY_SIMPLE_EFFECT、EFFECT_DIPLOMACY_THIRD_PARTY_EFFECTS、EFFECT_DIPLOMACY_THIRD_PARTY_WARMONGER。触发：改宣战、和谈、同盟、外交状态时。

## 外交状态

以下 EffectType 控制双边外交关系的动态变化（承诺/违约/间谍/定居/政府差异等）。

核心参数模式（大部分共用）：

| 通用参数 | 说明 |
|----------|------|
| `IncrementValue` | 每回合自动变化量（正值=关系变好） |
| `IncrementTurns` | 每隔多少回合触发递增 |
| `InitialValue` | 初始外交修正值 |
| `ReductionTurns` | 衰减修正所需的回合数 |
| `ReductionValue` | 每次衰减的变化量 |
| `SimpleModifierDescription` | 外交修正的说明文本 LOC |
| `StatementKey` | 弹出对话框的文本键 |
| `MessageThrottle` | 弹出信息间隔（回合） |
| `HiddenAgenda` | 是否隐藏议程（`0` = 显示 / `1` = 隐藏） |
| `DiplomacyKey` | 外交警告键（如 `WARNING_DONT_SETTLE_NEAR_ME`） |

---

### EFFECT_DIPLOMACY_ARCHAEOLOGY

考古争议 — 对在己方领土内挖掘遗迹的文明产生不满。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_ARCHAEOLOGY` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `DiplomacyKey` | **必写** | `WARNING_STOP_DIGGING_UP_ARTIFACTS` |
| `IncrementValue` | **必写** | 整数 — 示例值: `0` |
| `InitialValue` | **必写** | 整数 — 示例值: `0` |
| `MessageThrottle` | **必写** | 整数 — 示例值: `20` |
| `ModifierPerTransgression` | **必写** | 整数 — 每次挖掘惩罚。示例值: `-5` |
| `SimpleModifierDescription` | **必写** | `LOC_*` |

---

### EFFECT_DIPLOMACY_BROKEN_PLEDGE

违背誓言 — 对方违反了对你的承诺（如在边境集结后仍宣战）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_BROKEN_PLEDGE` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `IncrementValue` | **必写** | 整数 — 示例值: `0` |
| `ModifierPerTransgression` | **必写** | 整数 — 每次违约惩罚。示例值: `-6` |
| `ReductionTurns` | **必写** | 整数 — 示例值: `15` |
| `ReductionValue` | **必写** | 整数 — 示例值: `1` |
| `SimpleModifierDescription` | **必写** | `LOC_*` |

---

### EFFECT_DIPLOMACY_BROKEN_PROMISE

违背承诺 — 对方违反了对你的口头承诺（非正式誓言）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_BROKEN_PROMISE` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `IncrementValue` | **必写** | 整数 — 示例值: `0` |
| `ModifierPerTransgression` | **必写** | 整数 — 每次违约惩罚。示例值: `-6` |
| `ReductionTurns` | **必写** | 整数 — 示例值: `15` |
| `ReductionValue` | **必写** | 整数 — 示例值: `1` |
| `SimpleModifierDescription` | **必写** | `LOC_*` |

> 与 `BROKEN_PLEDGE` 的区别：Pledge 为正式誓言（如"不在边境集结军队"），Promise 为口头承诺（如"不要在我附近定居"）。

---

### EFFECT_DIPLOMACY_CULTURAL_ID

文化认同外交修正 — 根据对方夺取城市获取/失去文化认同。用于劳塔罗/马普切"图卡佩尔之魂"议程。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_SPIRIT_OF_TUCAPEL` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `CityGainLowerBound` | **必写** | 整数 — 获得城市的下限。示例值: `0` |
| `CityGainUpperBound` | **必写** | 整数 — 获得城市的上限。示例值: `3` |
| `ScorePerCity` | **必写** | 整数 — 每城市的评分。示例值: `3` |
| `SimpleModifierDescription` | **必写** | `LOC_*` — 示例值: `LOC_DIPLO_MODIFIER_SPIRIT_OF_TUCAPEL_GAINING_CITIES` |
| `StatementKey` | **必写** | `LOC_*` — 示例值: `LOC_DIPLO_KUDO_LEADER_LAUTARO_REASON_ANY` |

> 在 Rise and Fall / Gathering Storm 及部分场景中可用。

---

### EFFECT_DIPLOMACY_ESPIONAGE

间谍活动 — 对在己方进行间谍活动的文明产生不满。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_ESPIONAGE` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `DiplomacyKey` | **必写** | `WARNING_STOP_SPYING_ON_ME` |
| `IncrementValue` | **必写** | 整数 — 示例值: `0` |
| `InitialValue` | **必写** | 整数 — 示例值: `0` |
| `MessageThrottle` | **必写** | 整数 — 示例值: `20` |
| `ModifierPerTransgression` | **必写** | 整数 — 每次被发现惩罚。示例值: `-5` |
| `ReductionTurns` | **必写** | 整数 — 示例值: `15` |
| `ReductionValue` | **必写** | 整数 — 示例值: `1` |
| `SimpleModifierDescription` | **必写** | `LOC_*` |

---

### EFFECT_DIPLOMACY_FORCE_INCURSION

因军事入侵产生的外交修正。主要资料片+场景可用。

| ModifierType | CollectionType |
|-------------|----------------|
| （未在数据库中活跃使用） | |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `IncrementValue` | **必写** | 整数 — 递增修正值 |
| `InitialValue` | **必写** | 整数 — 初始修正值 |
| `ReductionValue` | **必写** | 整数 — 衰减修正值 |

> 在 Vanilla + Rise and Fall + Gathering Storm 及多数场景中可用。参数信息来自 `reference/csv-export/Effects.csv`。

---

### EFFECT_DIPLOMACY_GOVERNMENTS

政府差异 — 根据双方政体差异产生的外交修正。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_GOVERNMENTS` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `IncrementTurns` | **必写** | 整数 — 示例值: `1` |
| `IncrementValue` | **必写** | 整数 — 每回合增量（负值表示恶化）。示例值: `-1` |
| `SimpleModifierDescription` | **必写** | `LOC_*` |

---

### EFFECT_DIPLOMACY_KEPT_PLEDGE

遵守誓言 — 对方遵守了对你的正式承诺，关系变好。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_KEPT_PLEDGE` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `IncrementValue` | **必写** | 整数 — 示例值: `0` |
| `InitialValue` | **必写** | 整数 — 示例值: `0` |
| `ModifierPerKeptPledge` | **必写** | 整数 — 每次遵守奖励。示例值: `4` |
| `ReductionTurns` | **必写** | 整数 — 示例值: `15` |
| `ReductionValue` | **必写** | 整数 — 示例值: `1` |
| `SimpleModifierDescription` | **必写** | `LOC_*` |

---

### EFFECT_DIPLOMACY_KEPT_PROMISE

遵守承诺 — 对方遵守了口头承诺，关系变好。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_KEPT_PROMISE` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `IncrementValue` | **必写** | 整数 — 示例值: `0` |
| `InitialValue` | **必写** | 整数 — 示例值: `0` |
| `ModifierPerKeptPromise` | **必写** | 整数 — 每次遵守奖励。示例值: `4` |
| `ReductionTurns` | **必写** | 整数 — 示例值: `15` |
| `ReductionValue` | **必写** | 整数 — 示例值: `1` |
| `SimpleModifierDescription` | **必写** | `LOC_*` |

---

### EFFECT_DIPLOMACY_NEW_WARMONGER

新战争狂 — 根据对方造成的不满值产生外交惩罚。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_NEW_WARMONGER` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `LowerLimit` | **必写** | 整数 — 最低修正值（下限）。示例值: `-60` |
| `PercentOfGrievances` | **必写** | 整数 — 不满值百分比转化为外交惩罚。示例值: `20` |
| `ReductionTurns` | **必写** | 整数 — 衰减间隔回合。示例值: `2` |
| `ReductionValue` | **必写** | 整数 — 每次衰减值。示例值: `-1` |

> 数据库活跃实例: `STANDARD_DIPLOMATIC_WARMONGER`（LowerLimit=-60, PercentOfGrievances=20, ReductionTurns=2, ReductionValue=-1）。此为游戏的核心战争狂系统。

---

### EFFECT_DIPLOMACY_NO_PLEDGE

无誓言 — 对方拒绝做出正式承诺。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_NO_PLEDGE` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `IncrementValue` | **必写** | 整数 — 示例值: `0` |
| `ModifierPerTransgression` | **必写** | 整数 — 每次拒绝惩罚。示例值: `-3` |
| `ReductionTurns` | **必写** | 整数 — 示例值: `10` |
| `ReductionValue` | **必写** | 整数 — 示例值: `1` |
| `SimpleModifierDescription` | **必写** | `LOC_*` |

---

### EFFECT_DIPLOMACY_NO_PROMISE

无承诺 — 对方拒绝做出口头承诺。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_NO_PROMISE` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `IncrementValue` | **必写** | 整数 — 示例值: `0` |
| `ModifierPerTransgression` | **必写** | 整数 — 每次拒绝惩罚。示例值: `-3` |
| `ReductionTurns` | **必写** | 整数 — 示例值: `10` |
| `ReductionValue` | **必写** | 整数 — 示例值: `1` |
| `SimpleModifierDescription` | **必写** | `LOC_*` |

---

### EFFECT_DIPLOMACY_RANDOM

随机外交修正 — 开局时给予一个随机的初始外交态度。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_RANDOM` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `DifficultyOffset` | 可选 | 整数 — 难度偏移量 |
| `ReductionTurns` | **必写** | 整数 — 示例值: `10` |
| `ReductionValue` | **必写** | 整数 — 示例值: `1` |

---

### EFFECT_DIPLOMACY_SETTLED_CITIES

定居争议 — 对在己方附近建城的文明产生不满。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_SETTLED_CITIES` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `DiplomacyKey` | **必写** | `WARNING_DONT_SETTLE_NEAR_ME` |
| `IncrementValue` | **必写** | 整数 — 示例值: `0` |
| `InitialValue` | **必写** | 整数 — 示例值: `0` |
| `MessageThrottle` | **必写** | 整数 — 示例值: `20` |
| `ReductionTurns` | **必写** | 整数 — 示例值: `10` |
| `ReductionValue` | **必写** | 整数 — 示例值: `-1` |
| `SimpleModifierDescription` | **必写** | `LOC_*` |

---

### EFFECT_DIPLOMACY_SIMPLE_EFFECT

通用简单外交效果 — 可自定义几乎所有参数的外交状态变化模板。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_SIMPLE_MODIFIER` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `IncrementTurns` | **必写** | 整数 — 递增间隔 |
| `IncrementValue` | **必写** | 整数 — 每次递增的变化量 |
| `InitialValue` | **必写** | 整数 — 初始值 |
| `MaxValue` | 可选 | 整数 — 上限值 |
| `ReductionTurns` | 可选 | 整数 — 衰减间隔 |
| `ReductionValue` | 可选 | 整数 — 每次衰减值 |
| `SimpleModifierDescription` | 可选 | `LOC_*` |
| `StatementKey` | 可选 | `LOC_*` |
| `HiddenAgenda` | 可选 | `0` = 显示, `1` = 隐藏 |
| `DiplomacyKey` | 可选 | 外交警告键 |
| `MessageThrottle` | 可选 | 整数 — 信息间隔 |
| `Accumulates` | 可选 | `0` = 不累积, `1` = 累积 |
| `OnlyOwnersCity` | 可选 | `0` = 全局, `1` = 仅己方城市 |

> 外交议程的核心修改器。数据库中多达 176 个活跃实例，涵盖标准外交态度（宣称友好、谴责、边境警告、解放城市等）和领袖议程（高低科学/文化/信仰/军力等）。具体用法将在议程文件详述。此处仅列参数。
>
> 在 Vanilla + Rise and Fall + Gathering Storm 及多数场景中可用。

---

### EFFECT_DIPLOMACY_THIRD_PARTY_EFFECTS

第三方外交效果 — 因对方与你的敌人/盟友的关系产生修正。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_THIRD_PARTY_EFFECTS` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `AmountPerIncident` | **必写** | 整数 — 每事件修正。示例值: `-8` |
| `EffectType` | **必写** | `AlliedWithEnemy` / `FriendsWithEnemy` 等 |
| `IncrementValue` | **必写** | 整数 — 示例值: `0` |
| `InitialValue` | **必写** | 整数 — 示例值: `0` |
| `MaxEffectMagnitude` | **必写** | 整数 — 最大累积修正幅度。示例值: `8` |
| `SimpleModifierDescription` | **必写** | `LOC_*` |

---

### EFFECT_DIPLOMACY_THIRD_PARTY_WARMONGER

第三方战争狂 — 因对方对第三方发动战争产生的外交惩罚。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_THIRD_PARTY_WARMONGER` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `LowerLimit` | **必写** | 整数 — 最小修正值。示例值: `-40` |
| `PercentOfGrievancesDelta` | **必写** | 整数 — 不满值百分比转为修正。示例值: `10` |

> 数据库活跃实例: `STANDARD_DIPLOMATIC_THIRD_PARTY_WARMONGER`（LowerLimit=-40, PercentOfGrievancesDelta=10）。此为游戏核心的第三方战争狂系统。

---

