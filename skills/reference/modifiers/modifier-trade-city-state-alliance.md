# modifier-trade -- 商路类 EffectType — 城邦/同盟商路

> 分册：由 [modifier-trade.md](modifier-trade.md) 按主题拆出；覆盖 C. 城邦商路加成、EFFECT_ADJUST_CITY_STATE_TRADE_ROUTE_FLAT_YIELD、EFFECT_ADJUST_CITY_STATE_TRADE_ROUTE_DISTRICT_YIELD、EFFECT_ADJUST_PLAYER_TRADE_ROUTE_BY_CITY_STATE_BONUS_TYPE_MODIFIER、D. 同盟/宗主商路产出、EFFECT_ADJUST_PLAYER_TRADE_ROUTE_DESTINATION_YIELD_FOR_ALLY_ROUTE、EFFECT_ADJUST_PLAYER_TRADE_ROUTE_DESTINATION_YIELD_FOR_SUZERAIN_ROUTE、EFFECT_ADJUST_PLAYER_TRADE_ROUTE_ORIGIN_YIELD_FOR_ALLY_ROUTE、EFFECT_ADJUST_PLAYER_TRADE_ROUTE_ORIGIN_YIELD_FOR_SUZERAIN_ROUTE。触发：改城邦、同盟/宗主商路时。

## C. 城邦商路加成

---

### EFFECT_ADJUST_CITY_STATE_TRADE_ROUTE_FLAT_YIELD

调整通往城邦的商路所额外提供的固定产出。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTES_CITY_STATE_YIELD` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，固定产出数值 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：伊本·法德兰（大商人）— 通往城邦商路 +2 信仰。统治（政策）— 通往城邦商路 +2 金币。

---

### EFFECT_ADJUST_CITY_STATE_TRADE_ROUTE_DISTRICT_YIELD

通往城邦的商路，目的地城市每有一种区域类型，产出增加（库马西机制）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_CITY_STATE_TRADE_ROUTE_DISTRICT_YIELD` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，每区域提供的产出 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：库马西（城邦）— 通往城邦的商路，每个区域 +2 文化、+1 金币。伊丽莎白一世（德瑞克的遗产）— 通往城邦商路 +3 金币。

---

### EFFECT_ADJUST_PLAYER_TRADE_ROUTE_BY_CITY_STATE_BONUS_TYPE_MODIFIER

百分比修改城邦类型提供的商路加成。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_MAJOR_PLAYER_TRADE_ROUTE_BY_CITY_STATE_BONUS_TYPE_MODIFIER` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数（百分比），如 `100` = 加倍 |

> **溯源**：世界议会主权决议 — 城邦类型商路加成 +100%（`COLLECTION_MAJOR_PLAYERS`，作用于所有主要文明）。

---

## D. 同盟/宗主商路产出

---

### EFFECT_ADJUST_PLAYER_TRADE_ROUTE_DESTINATION_YIELD_FOR_ALLY_ROUTE

通往盟友的商路，为**目的地城市**增加产出。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_DESTINATION_YIELD_FOR_ALLY_ROUTE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，产出增量 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：民主主义政体 — 盟友商路目的地 +4 粮食、+4 生产力。贸易银行（政策）— +2 粮食、+2 生产力。民主兵工厂（政策）— +2 粮食、+2 生产力。

---

### EFFECT_ADJUST_PLAYER_TRADE_ROUTE_DESTINATION_YIELD_FOR_SUZERAIN_ROUTE

通往宗主的商路，为**目的地城市**增加产出。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_DESTINATION_YIELD_FOR_SUZERAIN_ROUTE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，产出增量 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：民主主义政体 — 宗主商路目的地 +4 粮食、+4 生产力。贸易银行（政策）— +2 粮食、+2 生产力。

---

### EFFECT_ADJUST_PLAYER_TRADE_ROUTE_ORIGIN_YIELD_FOR_ALLY_ROUTE

来自盟友的商路，为**起源城市**增加产出。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_ORIGIN_YIELD_FOR_ALLY_ROUTE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，产出增量 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：民主主义政体 — 来自盟友的商路起源 +4 粮食、+4 生产力。民主兵工厂（政策）— +2 粮食、+2 生产力。贸易银行（政策）— 起源 +2 粮食、+2 生产力。

---

### EFFECT_ADJUST_PLAYER_TRADE_ROUTE_ORIGIN_YIELD_FOR_SUZERAIN_ROUTE

来自宗主的商路，为**起源城市**增加产出。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_ORIGIN_YIELD_FOR_SUZERAIN_ROUTE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，产出增量 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：民主主义政体 — 来自宗主的商路起源 +4 粮食、+4 生产力。贸易银行（政策）— 起源 +2 粮食、+2 生产力。

---

