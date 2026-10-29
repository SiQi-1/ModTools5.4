# modifier-diplomacy -- 外交/影响力/使者/不满/议程类 EffectType — 影响力/不满

> 分册：由 [modifier-diplomacy.md](modifier-diplomacy.md) 按主题拆出；覆盖 不满值 / 战争狂 (Grievance / Warmonger)、EFFECT_ADJUST_PLAYER_GRIEVANCE_DECAY、EFFECT_ADJUST_PLAYER_GRIEVANCE_GENERATION、EFFECT_DISABLE_PLAYER_GRIEVANCE_DECAY、EFFECT_DIPLOMACY_WARMONGER、EFFECT_ADJUST_PLAYER_WARMONGER_MULTIPLIER、EFFECT_ADJUST_PLAYER_MAX_WARMONGER_PERCENT、影响力 / 使者 (Influence / Envoy)、EFFECT_ADJUST_DISABLE_INFLUENCE、EFFECT_ADJUST_DUPLICATE_FIRST_INFLUENCE_TOKEN、EFFECT_ADJUST_DUPLICATE_INFLUENCE_TOKEN_WHEN_RIVAL_GOVERNMENT、EFFECT_ADJUST_DUPLICATE_INFLUENCE_TOKEN_WHEN_SAME_RELIGION、EFFECT_ADJUST_DUPLICATE_INFLUENCE_TOKEN_WHEN_TRADE_ROUTE_TO、EFFECT_ADJUST_INFLUENCE_POINTS_PER_TURN、EFFECT_ADJUST_PLAYER_ADJUST_ENVOYS_NON_SPECIALTY `[无官方使用示例，但 Mod 中可用]`、EFFECT_ADJUST_PLAYER_OPEN_BORDERS_FROM_INFLUENCE、EFFECT_ADJUST_PLAYER_YIELD_CHANGE_PER_USED_INFLUENCE_TOKEN、EFFECT_ADJUST_PLAYER_SEND_INFLUENCE_TOKEN_FAVOR_BY_BONUS_TYPE、EFFECT_GRANT_CITY_OWNER_INFLUENCE_TOKEN_WONDER、EFFECT_GRANT_FREE_ENVOYS_HERE `[无官方使用示例，但 Mod 中可用]`、EFFECT_GRANT_INFLUENCE_TOKEN、EFFECT_GRANT_INFLUENCE_TOKEN_LEVY_MILITARY、EFFECT_ENABLE_RELIGION_AWARDS_ENVOY、EFFECT_ENABLE_RELIGION_AWARDS_ENVOY_RELIGIOUS_PRESSURE、EFFECT_ADJUST_PLAYER_SPECIFIC_DISTRICT_GRANT_ENVOYS。触发：改使者影响力、不满值战争狂时。

## 不满值 / 战争狂 (Grievance / Warmonger)

### EFFECT_ADJUST_PLAYER_GRIEVANCE_DECAY

加速/减缓不满值衰减速率。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_GRIEVANCE_DECAY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 衰减速率修正百分比。示例值: `100` (+100% 即双倍衰减速度) |

---

### EFFECT_ADJUST_PLAYER_GRIEVANCE_GENERATION

调整不满值生成倍率。数据库中活跃使用（如宣战时减少不满值生成）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_GRIEVANCE_MULTIPLIER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 百分比修正。示例值: `-50` (减少 50% 不满值生成), `100` (双倍) |

> 与 `EFFECT_ADJUST_PLAYER_GRIEVANCE_DECAY` 不同，此为生成倍率调整而非衰减速率。

---

### EFFECT_DISABLE_PLAYER_GRIEVANCE_DECAY

完全禁用不满值衰减（如网络战争效果）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DISABLE_GRIEVANCE_DECAY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Disable` | **必写** | `1` — 禁用衰减 |

> 与 `EFFECT_ADJUST_PLAYER_GRIEVANCE_DECAY` 不同，此为完全禁用而非速率调整。

---

### EFFECT_DIPLOMACY_WARMONGER

新战争狂 — 根据对方造成的整体不满值产生外交惩罚。

| ModifierType | CollectionType |
|-------------|----------------|
| （未在数据库中活跃使用） | |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `LowerLimit` | **必写** | 整数 — 最低修正值下限 (ESTIMATED) |
| `PercentOfGrievances` | **必写** | 整数 — 不满值百分比转化为外交惩罚 (ESTIMATED) |
| `ReductionTurns` | **必写** | 整数 — 衰减间隔回合 (ESTIMATED) |
| `ReductionValue` | **必写** | 整数 — 每次衰减值 (ESTIMATED) |

> 来源: `reference/csv-export/Effects.csv` EFFECT_DIPLOMACY_WARMONGER 行。仅存在于 New Frontier / War Machine / Black Death 等后期 DLC 中，**不在 Vanilla / Rise and Fall / Gathering Storm 中可用**。CSV 中此 EffectType 的参数字段为空，以上参数为从同系列效果推断。

---

### EFFECT_ADJUST_PLAYER_WARMONGER_MULTIPLIER

调整战争狂不满值倍率。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_WARMONGER_MULTIPLIER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 百分比倍率。示例值: `0` (完全取消战争狂惩罚) |

> 数据库活跃实例: `NONAGENDA_IGNORE_WARMONGERING`（Amount=0，完全无视战争狂惩罚）。

---

### EFFECT_ADJUST_PLAYER_MAX_WARMONGER_PERCENT

调整最大战争狂惩罚百分比上限。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_MAX_WARMONGER_PERCENT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `MaxPercent` | **必写** | 整数 — 最大百分比上限。示例值: `100` |

> 数据库活跃实例: `TRAIT_FALLBABYLON_WARMONGER_MAX`（MaxPercent=100，将战争狂惩罚上限设为 100%）。见于 New Frontier。

---

## 影响力 / 使者 (Influence / Envoy)

### EFFECT_ADJUST_DISABLE_INFLUENCE

禁用影响力产出（如成为叛军状态）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DISABLE_INFLUENCE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Disable` | **必写** | `0` = 启用, `1` = 禁用 |

---

### EFFECT_ADJUST_DUPLICATE_FIRST_INFLUENCE_TOKEN

向城邦首次派遣使者时获得双倍使者。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_DUPLICATE_FIRST_INFLUENCE_TOKEN` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | `1` — 额外获得的使者数。原版固定为 1 |

---

### EFFECT_ADJUST_DUPLICATE_INFLUENCE_TOKEN_WHEN_RIVAL_GOVERNMENT

对政体不同的城邦派遣使者时双倍。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_DUPLICATE_INFLUENCE_TOKEN_WHEN_RIVAL_GOVERNMENT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | `1` — 额外使者数 |

---

### EFFECT_ADJUST_DUPLICATE_INFLUENCE_TOKEN_WHEN_SAME_RELIGION

向同宗教城邦派遣使者时双倍。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_DUPLICATE_INFLUENCE_TOKEN_WHEN_SAME_RELIGION` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | `1` — 额外使者数 |

---

### EFFECT_ADJUST_DUPLICATE_INFLUENCE_TOKEN_WHEN_TRADE_ROUTE_TO

对已建立贸易路线的城邦派遣使者时获得额外使者。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_DUPLICATE_INFLUENCE_TOKEN_WHEN_TRADE_ROUTE_TO` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 额外使者数。示例值: `1` |

---

### EFFECT_ADJUST_INFLUENCE_POINTS_PER_TURN

调整每回合获得的影响力点数。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_INFLUENCE_POINTS_PER_TURN` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 每回合影响力增量。示例值: `3` |

---

### EFFECT_ADJUST_PLAYER_ADJUST_ENVOYS_NON_SPECIALTY `[无官方使用示例，但 Mod 中可用]`

非特色区域建成时获得额外使者。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DISTRICT_ADJUST_PLAYER_ENVOYS_NON_SPECIALTY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 获得使者数。示例值: `1` |

---

### EFFECT_ADJUST_PLAYER_OPEN_BORDERS_FROM_INFLUENCE

根据影响力自动开放边界（炮舰外交）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_ADJUST_OPEN_BORDERS_FROM_INFLUENCE` | `COLLECTION_ALL_PLAYERS` |

> 无额外参数。触发后根据影响力值自动对所有玩家开放边界。

---

### EFFECT_ADJUST_PLAYER_YIELD_CHANGE_PER_USED_INFLUENCE_TOKEN

根据已派遣的使者数量提供产出加成。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_YIELD_CHANGE_PER_USED_INFLUENCE_TOKEN` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 每个使者提供的产出量。示例值: `1` |
| `YieldType` | **必写** | `YIELD_GOLD` / `YIELD_SCIENCE` / `YIELD_CULTURE` / `YIELD_FAITH` |

> 原版示例：商业城邦宗主国加成，每派遣 1 名使者 +1 金币。

---

### EFFECT_ADJUST_PLAYER_SEND_INFLUENCE_TOKEN_FAVOR_BY_BONUS_TYPE

根据城邦类型调整派遣使者时获得的外交支持。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_SEND_INFLUENCE_TOKEN_FAVOR_BY_BONUS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — Favor 值 (ESTIMATED，来自 `reference/csv-export/Effects.csv`) |
| `BonusType` | **必写** | 城邦类型标识。可选项参考 `reference/csv-export/Enumerations.csv` 中 `GovernmentBonusTypes` 表 (ESTIMATED) |

> 来源: `reference/csv-export/Effects.csv` EFFECT_ADJUST_PLAYER_SEND_INFLUENCE_TOKEN_FAVOR_BY_BONUS_TYPE 行（Gathering Storm / New Frontier）。数据库中无活跃 Modifier 实例，参数为推定值。

---

### EFFECT_GRANT_CITY_OWNER_INFLUENCE_TOKEN_WONDER

建造奇观时获得使者（等同于 `MODIFIER_PLAYER_GRANT_INFLUENCE_TOKEN_FROM_CITY_WONDER`）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_GRANT_INFLUENCE_TOKEN_FROM_CITY_WONDER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 使者数量。示例值: `2` |

---

### EFFECT_GRANT_FREE_ENVOYS_HERE `[无官方使用示例，但 Mod 中可用]`

直接在该城邦赋予免费使者。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_CITY_GRANT_FREE_ENVOYS_HERE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 使者数量。示例值: `3` |

> `COLLECTION_OWNER` 指 Modifier 附着对象的"所有者"——当附着于城邦时，即该城邦获得使者。

---

### EFFECT_GRANT_INFLUENCE_TOKEN

直接给予玩家使者。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_GRANT_INFLUENCE_TOKEN` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_GRANT_INFLUENCE_TOKEN_FROM_CITY_WONDER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 使者数量。示例值: `2` |

---

### EFFECT_GRANT_INFLUENCE_TOKEN_LEVY_MILITARY

征用城邦军队时获得使者。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_ENVOYS_FROM_LEVIED_CITY_STATES` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 使者数量。示例值: `2` |

---

### EFFECT_ENABLE_RELIGION_AWARDS_ENVOY

启用宗教奖励使者机制。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_RELIGION_ENABLE_AWARDS_ENVOY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Enable` | **必写** | `0` = 禁用, `1` = 启用 |

---

### EFFECT_ENABLE_RELIGION_AWARDS_ENVOY_RELIGIOUS_PRESSURE

根据宗教压力奖励使者。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_RELIGION_ENABLE_AWARDS_ENVOY_RELIGIOUS_PRESSURE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 宗教压力阈值。示例值: `200` |

---

### EFFECT_ADJUST_PLAYER_SPECIFIC_DISTRICT_GRANT_ENVOYS

建成特定区域时获得使者。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DISTRICT_ADJUST_SPECIFIC_DISTRICT_GRANT_ENVOYS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数 — 使者数量。示例值: `1` |
| `DistrictType` | **必写** | `Districts.DistrictType` — 指定区域类型。示例值: `DISTRICT_GOVERNMENT` |

---

