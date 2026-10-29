# modifier-trade -- 商路类 EffectType — 容量/外交/特殊

> 分册：由 [modifier-trade.md](modifier-trade.md) 按主题拆出；覆盖 E. 商路容量、EFFECT_ADJUST_TRADE_ROUTE_CAPACITY、EFFECT_ADJUST_PLAYER_TRADE_ROUTE_CAPACITY_ON_MEETING、EFFECT_GRANT_FOUND_FOREIGN_CITY_TRADE_ROUTE_CAPACITY、EFFECT_GRANT_GOLDEN_AGE_TRADE_ROUTE_CAPACITY、EFFECT_ADJUST_TRADE_ROUTE_WATER_RANGE、F. 外交与商路、EFFECT_DIPLOMACY_ONE_SIDED_TRADES、EFFECT_DIPLOMACY_TRADE_RELATIONS、EFFECT_ADJUST_ALLIANCE_POINTS_FOR_TRADE_MODIFIER、G. 特殊机制、EFFECT_ADJUST_PLAYER_TRADE_ROUTE_RELIGIOUS_PRESSURE、EFFECT_ADJUST_PLAYER_TRADE_ROUTE_TOURISM_MODIFIER、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_TRADE_ROUTE_COMPLETED、EFFECT_ADJUST_PLAYER_IDENTITY_PER_TURN_FOR_DOMESTIC_TRADE_ROUTE_ORIGIN、EFFECT_ADJUST_UNIT_TRADE_ROUTE_PLUNDER_IMMUNITY、EFFECT_ADJUST_DUPLICATE_INFLUENCE_TOKEN_WHEN_TRADE_ROUTE_TO、EFFECT_ADJUST_PLAYER_TRADE_GAIN_TILES_EN_ROUTE、EFFECT_TRADE_ROUTE_DISABLE。触发：改商路容量、外交与商路、特殊机制时。

## E. 商路容量

---

### EFFECT_ADJUST_TRADE_ROUTE_CAPACITY

调整商路容量上限（最通用的商路容量效果）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_CAPACITY` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_DISTRICTS_ADJUST_TRADE_ROUTE_CAPACITY` | `COLLECTION_PLAYER_DISTRICTS` |
| `MODIFIER_PLAYER_CITIES_ADJUST_TRADE_ROUTE_CAPACITY` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_ALLIANCE_PLAYER_TRADE_ROUTE_CAPACITY` | `COLLECTION_ALLIANCE_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，增加的商路容量 |

> **溯源**：
> - `COLLECTION_OWNER`（最常用）：巨像/大津巴布韦 +1；市场/灯塔 +1；对外贸易市政 +1；大商人（马可波罗/张骞/梅莉塔）激活后 +1；伊丽莎白一世 +2
> - `COLLECTION_PLAYER_DISTRICTS`：每个商业中心 +1（见 `TRAIT_POTTERY_TRADE_ROUTE` 示例）
> - `COLLECTION_PLAYER_CITIES`：迦太基建国者 — 政府区建筑每城 +1
> - `COLLECTION_ALLIANCE_PLAYERS`：同盟成员 +1

---

### EFFECT_ADJUST_PLAYER_TRADE_ROUTE_CAPACITY_ON_MEETING

首次遭遇其他文明时获得商路容量。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_CAPACITY_ON_MEETING` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，商路容量增加数 |
| `Intercontinental` | 选写 | `Boolean`，`1` = 仅跨大陆有效 |

> **溯源**：若昂三世（关闸）— 首次遭遇文明 +1 商路容量（`Amount=1`）。

---

### EFFECT_GRANT_FOUND_FOREIGN_CITY_TRADE_ROUTE_CAPACITY

首次在外大陆建立城市时获得商路容量。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_CAPACITY_FOUND_FOREIGN_CITY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，增加的商路容量 |

> **溯源**：维多利亚（英国强权下的和平）— 在外大陆建城 +1 商路。

---

### EFFECT_GRANT_GOLDEN_AGE_TRADE_ROUTE_CAPACITY

黄金时代获得商路容量。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_CAPACITY_GOLDEN_AGE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，增加的商路容量 |

> **溯源**：曼萨穆萨（萨赫勒商人）— 黄金时代 +1 商路容量。

---

### EFFECT_ADJUST_TRADE_ROUTE_WATER_RANGE

调整水上商路范围。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_WATER_RANGE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，水上商路额外格数 |

> **溯源**：葡萄牙（印度之家）— 水上商路范围 +15 格。

---

## F. 外交与商路

---

### EFFECT_DIPLOMACY_ONE_SIDED_TRADES

对"只发不收"交易（一厢情愿贸易）的文明产生外交好感惩罚。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DIPLOMACY_ONE_SIDED_TRADES` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `IncrementValue` | **必写** | 整数，好感变化增量（通常为 `0`） |
| `MaxValue` | **必写** | 整数，最大好感惩罚值 |
| `ReductionTurns` | **必写** | 整数，惩罚衰减所需回合数 |
| `ReductionValue` | **必写** | 整数，每回合衰减量 |
| `TradeValuePerModifierPoint` | **必写** | 整数，每点惩罚对应的贸易价值阈值 |

> **溯源**：标准外交（`TRAIT_LEADER_MAJOR_CIV`）— 所有主要文明默认行为：`MaxValue=20, ReductionTurns=2, ReductionValue=1, TradeValuePerModifierPoint=10`。此参数体系完全不同于其他商路效果。

---

### EFFECT_DIPLOMACY_TRADE_RELATIONS

根据贸易关系调整外交好感。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DIPLOMACY_TRADE_RELATIONS` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `StatementKey` | **必写** | `LOC_` 文本键，外交陈述语句 |
| `SimpleModifierDescription` | **必写** | `LOC_` 文本键，简单描述 |
| `TradeBonus` | **必写** | 整数，基础贸易好感加成 |
| `BonusPerRoute` | 选写 | `Boolean`，`1` = 每条商路额外加好感 |
| `NoTradePenalty` | 选写 | 整数，无商路时的好感惩罚值（如 `12`） |
| `OnlyInboundTrade` | 选写 | `Boolean`，`1` = 仅计入来向商路 |

> **溯源**：标准外交（所有文明默认）— `TradeBonus=3`（基础 +3 好感）。威尔米娜（亿万富翁议程）— `BonusPerRoute=1, NoTradePenalty=12, OnlyInboundTrade=1`，每条来向商路额外好感。伊丽莎白一世（贸易协定议程）— 同上参数。

---

### EFFECT_ADJUST_ALLIANCE_POINTS_FOR_TRADE_MODIFIER

调整每商路提供的同盟点数倍率。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_ALLIANCE_POINTS_FOR_TRADE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，每商路同盟点数倍率（`1` = 标准倍率） |

> **溯源**：克莉奥帕特拉（地中海新娘）— 每商路同盟点数 ×1（标准倍率）。

---

## G. 特殊机制

---

### EFFECT_ADJUST_PLAYER_TRADE_ROUTE_RELIGIOUS_PRESSURE

调整商路带来的宗教压力。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_RELIGIOUS_PRESSURE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，宗教压力百分比增量（如 `100` = 加倍） |
| `Destination` | 选写 | `Boolean`，`1` = 影响目的地宗教压力 |
| `Origin` | 选写 | `Boolean`，`1` = 影响起源城市宗教压力 |

> **溯源**：西班牙（艾斯科里亚尔）— 商路起源+目的地宗教压力各 +100%（`Origin=1, Destination=1`）。

---

### EFFECT_ADJUST_PLAYER_TRADE_ROUTE_TOURISM_MODIFIER

百分比调整商路带来的旅游业绩。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_TOURISM_MODIFIER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数（百分比），如 `25` = +25%，`-25` = -25% |

> **溯源**：大商人（莎拉·布里德洛夫/梅莉塔·本茨）— 商路旅游业绩 +25%。在线社区（政策）— +50%。德川家康（幕藩）— 国际商路旅游业绩 -25%。

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_TRADE_ROUTE_COMPLETED

每完成一条商路，获得时代分数。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PLAYER_ERA_SCORE_PER_TRADE_ROUTE_COMPLETED` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，每条完成的商路给予的时代分数 |

> **溯源**：经济黄金时代纪念（GS 模式）— 每完成商路 +1 时代分数。

---

### EFFECT_ADJUST_PLAYER_IDENTITY_PER_TURN_FOR_DOMESTIC_TRADE_ROUTE_ORIGIN

每有一条国内商路从己方城市出发，每回合获得忠诚度。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PLAYER_IDENTITY_PER_TURN_FOR_DOMESTIC_TRADE_ROUTE_ORIGIN` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，每条国内出发商路提供的忠诚度/回合 |

> **溯源**：威廉明娜（橙色电台）— 每条国内出发商路 +2 忠诚度/回合。

---

### EFFECT_ADJUST_UNIT_TRADE_ROUTE_PLUNDER_IMMUNITY

使指定域的单位获得商路掠夺免疫。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_TRADE_ROUTE_PLUNDER_IMMUNITY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `DomainType` | **必写** | `DOMAIN_LAND` 或 `DOMAIN_SEA` |

> **溯源**：经济黄金时代 — 陆地单位免疫掠夺（`DOMAIN_LAND`）+ 海上单位免疫掠夺（`DOMAIN_SEA`）。曼德卡鲁骑兵（马里 UU）— 附近陆地商路免疫掠夺。拜占庭桨帆船 — 附近海上商路免疫掠夺。

---

### EFFECT_ADJUST_DUPLICATE_INFLUENCE_TOKEN_WHEN_TRADE_ROUTE_TO

向有商路连接的城邦派遣使者时，额外获得等同于已派遣数量的使者。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_DUPLICATE_INFLUENCE_TOKEN_WHEN_TRADE_ROUTE_TO` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，复制的使者数量（= 已派遣数量 × Amount，通常为 `1`） |

> **溯源**：西奥多·罗斯福（罗斯福推论）— 向有商路的城邦派遣使者时，复制已派遣使者数量（`Amount=1`）。

---

### EFFECT_ADJUST_PLAYER_TRADE_GAIN_TILES_EN_ROUTE

商路经过地块时获得视野。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_TRADE_GAIN_TILES_EN_ROUTE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `GainTileRadius` | **必写** | 整数，商路沿途获得视野的半径格数 |

> **溯源**：克里（林地克里人）— 商路路径打开 3 格视野（`GainTileRadius=3`）。注意参数名非 `Amount`。

---

### EFFECT_TRADE_ROUTE_DISABLE

禁用指定类型的商路。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_TRADE_ROUTES_DISABLE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Domestic` | **必写** | `Boolean`，`1` = 禁用国内商路 |
| `InternationalMajors` | **必写** | `Boolean`，`1` = 禁止通往主要文明的国际商路 |
| `InternationalMinors` | **必写** | `Boolean`，`1` = 禁止通往城邦的国际商路 |

> **溯源**：世界议会贸易条约决议（效果 2）— 禁用国际主要文明商路（`Domestic=0, InternationalMajors=1, InternationalMinors=0`）。

---

