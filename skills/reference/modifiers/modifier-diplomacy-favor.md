# modifier-diplomacy -- 外交/影响力/使者/不满/议程类 EffectType — 外交支持

> 分册：由 [modifier-diplomacy.md](modifier-diplomacy.md) 按主题拆出；覆盖 外交支持 (Favor)、EFFECT_ADD_PLAYER_FAVOR、EFFECT_ADJUST_PLAYER_EXTRA_FAVOR_PER_TURN、EFFECT_ADJUST_PLAYER_DIPLOMATIC_VICTORY_POINTS、EFFECT_ADJUST_PLAYER_EMERGENCY_FAVOR_MODIFIER、EFFECT_ADJUST_PLAYER_FAVOR_REFUND_FOR_SUCCESSFUL_RESOLUTION、EFFECT_ADJUST_PLAYER_GOVERNMENT_SLOT_TYPE_GRANT_FAVOR、EFFECT_ADJUST_PLAYER_GOVERNOR_FAVOR、EFFECT_ADJUST_PLAYER_GREATPERSON_FAVOR_MODIFIER、EFFECT_ADJUST_PLAYER_POLICY_FAVOR、EFFECT_ADJUST_PLAYER_SUZERAIN_FAVOR_MULTIPLIER、EFFECT_ADJUST_PLAYER_SUZERAIN_FAVOR_BY_BONUS_TYPE、EFFECT_ADJUST_PLAYER_TOURISM_FAVOR、EFFECT_ADJUST_PLAYER_BUILDING_FAVOR、EFFECT_ADJUST_PLAYER_ANYONE_TRADE_TO_FAVOR、EFFECT_ADJUST_PLAYER_ANYONE_PLUNDER_FAVOR、EFFECT_ADJUST_PLAYER_ANYONE_PLUNDER_TO_FAVOR、EFFECT_ADJUST_RELIGION_ANYONE_CONDEMNS_FAVOR、EFFECT_PLAYER_ADJUST_FAVOR_FROM_DELEGATIONS `[无官方使用示例，但 Mod 中可用]`、EFFECT_PLAYER_ADJUST_FAVOR_FROM_EMBASSIES `[无官方使用示例，但 Mod 中可用]`、EFFECT_ADJUST_PLAYER_SEND_TRADE_ROUTE_FAVOR_BY_BONUS_TYPE。触发：改外交支持(Favor)相关效果时。

## 外交支持 (Favor)

### EFFECT_ADD_PLAYER_FAVOR

直接给予玩家外交支持点数。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADD_FAVOR` | `COLLECTION_OWNER` |
| `MODIFIER_EMERGENCY_PLAYERS_ADD_FAVOR` | `COLLECTION_EMERGENCY_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — Favor 数量。示例值: `50` (市政), `100` (紧急事件参与者) |

---

### EFFECT_ADJUST_PLAYER_EXTRA_FAVOR_PER_TURN

每回合额外获得外交支持点数。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_EXTRA_FAVOR_PER_TURN` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_CITIES_ADJUST_EXTRA_FAVOR_PER_TURN` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 每回合 Favor 增量。示例值: `1`~`3` |

---

### EFFECT_ADJUST_PLAYER_DIPLOMATIC_VICTORY_POINTS

调整外交胜利点数。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_DIPLOMATIC_VICTORY_POINTS` | `COLLECTION_OWNER` |
| `MODIFIER_EMERGENCY_PLAYERS_ADJUST_DIPLOMATIC_VICTORY_POINTS` | `COLLECTION_EMERGENCY_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 外交胜利点数值。示例值: `1`~`4` |
| `Tooltip` | 可选 | `LOC_*` — 来源说明文本 |
| `VictoryResolution` | 可选 | `1` = 通过决议获得, `0` = 非决议来源 |

> 文本示例（在 ModifierStrings 表中用 `Preview` 上下文）:
> ```
> INSERT INTO ModifierStrings (ModifierId, Context, Text)
> VALUES ('MY_DIPLO_VICTORY_POINTS', 'Preview', 'LOC_DIPLO_VICTORY_POINTS_PREVIEW_TEXT');
> ```
> 常用于奇观（自由女神像、摩诃菩提寺、布达拉宫）和计分竞赛。

---

### EFFECT_ADJUST_PLAYER_EMERGENCY_FAVOR_MODIFIER

调整从紧急事件中获得的外交支持倍率。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_EMERGENCY_FAVOR_MODIFIER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 百分比修正值。示例值: `100` (即 x2) |
| `Member` | 可选 | `0` = 通用, `1` = 仅针对紧急事件成员身份 |

> 数据库活跃实例: `TRAIT_EMERGENCY_FAVOR_MODIFIER`（Amount=100, Member=1）。见于 Gathering Storm / New Frontier。

---

### EFFECT_ADJUST_PLAYER_FAVOR_REFUND_FOR_SUCCESSFUL_RESOLUTION

对成功的世界议会决议退还部分外交支持。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_FAVOR_REFUND_FOR_SUCCESSFUL_RESOLUTION` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Percent` | **必写** | 整数 — 退还百分比。示例值: `50` (退还 50%) |
| `ResolutionType` | **必写** | `WC_RES_*` — 指定的决议类型 |
| `WhichEffect` | 可选 | 整数 — 决议中的第几项效果 |

---

### EFFECT_ADJUST_PLAYER_GOVERNMENT_SLOT_TYPE_GRANT_FAVOR

根据政体槽位类型提供外交支持。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_GOVERNMENT_SLOT_TYPE_GRANT_FAVOR` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 每个对应槽位提供的 Favor 数 |
| `GovernmentSlotType` | **必写** | `SLOT_WILDCARD` / `SLOT_MILITARY` / `SLOT_ECONOMIC` / `SLOT_DIPLOMATIC` |

> 数据库活跃实例: `TRAIT_WILD_CARD_FAVOR`（美国政府首脑特质，每个 `SLOT_WILDCARD` 通配符槽位 +1 Favor）。见于 Gathering Storm / New Frontier。

---

### EFFECT_ADJUST_PLAYER_GOVERNOR_FAVOR

任命/晋升指定总督时获得外交支持。设 `Neutralize=1` 则改为抵消该总督类型的负面效果。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_MAJOR_PLAYERS_ADJUST_GOVERNOR_FAVOR` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `FavorAmount` | **必写** | 整数 — 每次晋升获得的 Favor 量。示例值: `3` |
| `GovernorType` | **必写** | `Governors.GovernorType` — 指定总督类型。示例值: `GOVERNOR_THE_EDUCATOR` |
| `Neutralize` | 可选 | `0` = 不抵消, `1` = 抵消指定总督类型的负面效果 |

> 来源: `reference/csv-export/Effects.csv` EFFECT_ADJUST_PLAYER_GOVERNOR_FAVOR 行（Gathering Storm / New Frontier / Black Death / War Machine）。当前数据库中无活跃 Modifier 实例。

---

### EFFECT_ADJUST_PLAYER_GREATPERSON_FAVOR_MODIFIER

调整招募伟人时获得的外交支持倍率。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_GREATPERSON_FAVOR_MODIFIER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 百分比修正。示例值: `50` (+50%) |

> 数据库活跃实例: `TRAIT_GREATPERSON_FAVOR_MODIFIER`（Amount=50）。见于 Gathering Storm / New Frontier。

---

### EFFECT_ADJUST_PLAYER_POLICY_FAVOR

调整政策卡提供的外交支持。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_POLICY_FAVOR` | `COLLECTION_OWNER` |
| `MODIFIER_MAJOR_PLAYERS_ADJUST_POLICY_FAVOR` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — Favor 修正量 (ESTIMATED) |
| `PolicyType` | **必写** | `Policies.PolicyType` — 指定政策卡 (ESTIMATED) |

> 来源: `reference/csv-export/Effects.csv` EFFECT_ADJUST_PLAYER_POLICY_FAVOR 行（Gathering Storm）。数据库中无活跃 Modifier 实例。

---

### EFFECT_ADJUST_PLAYER_SUZERAIN_FAVOR_MULTIPLIER

调整城邦宗主国外交支持倍率。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_SUZERAIN_FAVOR_MULTIPLIER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 百分比倍率。示例值: `100` (即 x2，如匈牙利议会大厦) |

> 数据库活跃实例: `ORSZAGHAZ_DOUBLE_FAVOR_SUZERAIN`（Amount=100）。见于 Gathering Storm。

---

### EFFECT_ADJUST_PLAYER_SUZERAIN_FAVOR_BY_BONUS_TYPE

根据城邦类型调整宗主国外交支持。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_MAJOR_PLAYERS_ADJUST_SUZERAIN_FAVOR_BY_BONUS` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `BonusType` | **必写** | 城邦类型标识。可选项参考 `reference/csv-export/Enumerations.csv` 中 `GovernmentBonusTypes` 表（如 `GOVERNMENTBONUS_ENVOYS` / `GOVERNMENTBONUS_FAITH_PURCHASES` 等）(ESTIMATED) |
| `Amount` | **必写** | 整数 — Favor 修正值 (ESTIMATED) |

> 来源: `reference/csv-export/Effects.csv` EFFECT_ADJUST_PLAYER_SUZERAIN_FAVOR_BY_BONUS_TYPE 行（Gathering Storm / New Frontier）。数据库中无活跃 Modifier 实例，参数为推定值。

---

### EFFECT_ADJUST_PLAYER_TOURISM_FAVOR

根据旅游业绩提供外交支持。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_TOURISM_INTO_FAVOR` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Favor` | **必写** | 整数 — 每单位 Tourism 对应的 Favor 值。示例值: `1` |
| `Tourism` | **必写** | 整数 — Tourism 阈值。示例值: `100` |

> 数据库活跃实例: `TRAIT_TOURISM_INTO_FAVOR`（Tourism=100, Favor=1）。见于 Gathering Storm / New Frontier。

---

### EFFECT_ADJUST_PLAYER_BUILDING_FAVOR

根据建造的指定建筑提供外交支持。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_BUILDING_FAVOR` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `BuildingType` | **必写** | `Buildings.BuildingType` — 指定建筑。示例值: `BUILDING_BROADCAST_CENTER` |
| `Favor` | **必写** | 整数 — Favor 值。示例值: `3` |

> 数据库存在 1 个活跃 Modifier 实例。见于场景包（Black Death / War Machine 等）。

---

### EFFECT_ADJUST_PLAYER_ANYONE_TRADE_TO_FAVOR

建立贸易路线时获得外交支持。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_ANYONE_TRADE_TO_FAVOR` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — Favor 值 (ESTIMATED，来自 `reference/csv-export/Effects.csv`) |

> 来源: `reference/csv-export/Effects.csv` EFFECT_ADJUST_PLAYER_ANYONE_TRADE_TO_FAVOR 行（Gathering Storm / New Frontier）。数据库中无活跃 Modifier 实例。

---

### EFFECT_ADJUST_PLAYER_ANYONE_PLUNDER_FAVOR

掠夺时获得外交支持（资料片/场景可用）。

| ModifierType | CollectionType |
|-------------|----------------|
| （未在数据库中活跃使用） | |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — Favor 值 (ESTIMATED) |

> 来源: `reference/csv-export/Effects.csv` EFFECT_ADJUST_PLAYER_ANYONE_PLUNDER_FAVOR 行（Gathering Storm / New Frontier / 部分场景）。数据库中无活跃 Modifier 实例。

---

### EFFECT_ADJUST_PLAYER_ANYONE_PLUNDER_TO_FAVOR

掠夺时获得外交支持（原版可用版本）。`[未在数据库中活跃使用]`

| ModifierType | CollectionType |
|-------------|----------------|
| （未在数据库中活跃使用） | |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — Favor 值 (ESTIMATED) |

> 来源: `reference/csv-export/Effects.csv` EFFECT_ADJUST_PLAYER_ANYONE_PLUNDER_TO_FAVOR 行。仅原版 (Vanilla) 可用，数据库中无活跃 Modifier 实例。与 `EFFECT_ADJUST_PLAYER_ANYONE_PLUNDER_FAVOR` 是不同 EffectType。

---

### EFFECT_ADJUST_RELIGION_ANYONE_CONDEMNS_FAVOR

因异端谴责获得外交支持。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_RELIGION_ADJUST_ANYONE_CONDEMNS_FAVOR` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 每次谴责获得的 Favor 量。示例值: `25` |

> 数据库活跃实例: `ANYONE_CONDEMNS_FOR_FAVOR`（Amount=25）。见于 Gathering Storm。

---

### EFFECT_PLAYER_ADJUST_FAVOR_FROM_DELEGATIONS `[无官方使用示例，但 Mod 中可用]`

调整来自代表团的每回合外交支持。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_FAVOR_FROM_DELEGATIONS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 每个代表团额外获得的 Favor/回合 |

---

### EFFECT_PLAYER_ADJUST_FAVOR_FROM_EMBASSIES `[无官方使用示例，但 Mod 中可用]`

调整来自大使馆的每回合外交支持。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_FAVOR_FROM_EMBASSIES` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 每个大使馆额外获得的 Favor/回合 |

---

### EFFECT_ADJUST_PLAYER_SEND_TRADE_ROUTE_FAVOR_BY_BONUS_TYPE

根据城邦类型调整发送贸易路线时获得的外交支持。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_SEND_TRADE_ROUTE_FAVOR_BY_BONUS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — Favor 值 (ESTIMATED，来自 `reference/csv-export/Effects.csv`) |
| `BonusType` | **必写** | 城邦类型标识。可选项参考 `reference/csv-export/Enumerations.csv` 中 `GovernmentBonusTypes` 表 (ESTIMATED) |

> 来源: `reference/csv-export/Effects.csv` EFFECT_ADJUST_PLAYER_SEND_TRADE_ROUTE_FAVOR_BY_BONUS_TYPE 行（Gathering Storm / New Frontier）。数据库中无活跃 Modifier 实例，参数为推定值。

---

