# modifier-trade -- 商路类 EffectType — 城市级商路

> 分册：由 [modifier-trade.md](modifier-trade.md) 按主题拆出；覆盖 概述、A. 商路产出调整（城市级）、EFFECT_ADJUST_CITY_TRADE_ROUTE_YIELD_FOR_DOMESTIC、EFFECT_ADJUST_CITY_TRADE_ROUTE_YIELD_FOR_INTERNATIONAL、EFFECT_ADJUST_CITY_TRADE_ROUTE_YIELD_PER_DESTINATION_LUXURY_RESOURCE_FOR_INTERNATIONAL、EFFECT_ADJUST_CITY_TRADE_ROUTE_YIELD_PER_DESTINATION_STRATEGIC_RESOURCE_FOR_DOMESTIC、EFFECT_ADJUST_CITY_TRADE_ROUTE_YIELD_PER_DESTINATION_STRATEGIC_RESOURCE_FOR_INTERNATIONAL、EFFECT_ADJUST_CITY_TRADE_ROUTE_YIELD_PER_LOCAL_BONUS_RESOURCE_FOR_DOMESTIC、EFFECT_ADJUST_CITY_TRADE_ROUTE_YIELD_PER_LOCAL_BONUS_RESOURCE_FOR_INTERNATIONAL、EFFECT_ADJUST_CITY_TRADE_ROUTE_YIELD_PER_LOCAL_LUXURY_RESOURCE_FOR_INTERNATIONAL、EFFECT_ADJUST_CITY_TRADE_ROUTE_YIELD_PER_LOCAL_STRATEGIC_RESOURCE_FOR_INTERNATIONAL、EFFECT_ADJUST_CITY_YIELD_FROM_FOREIGN_TRADE_ROUTES_PASSING_THROUGH、EFFECT_ADJUST_CITY_YIELD_PER_MAJOR_TRADE_PARTNER、EFFECT_ADJUST_TRADE_ROUTE_YIELD_PER_SPECIALTY_DISTRICT_FOR_DOMESTIC、EFFECT_ADJUST_TRADE_ROUTE_YIELD_PER_SPECIALTY_DISTRICT_FOR_INTERNATIONAL。触发：改城市级商路产出、概述时。

## 概述

商路类 EffectType 共 **57** 个，涵盖商路产出、容量、外交、宗教压力、旅游业绩等所有商路相关机制。

| 子类 | 数量 | 说明 |
|------|------|------|
| 商路产出调整（城市级） | ~11 | PER_DESTINATION / PER_LOCAL 系列，城市级按资源/设施计算 |
| 商路产出调整（玩家级） | ~19 | TRADE_ROUTE_YIELD 系列，玩家全局或按条件 |
| 商路容量 | 6 | 增加商路数量上限（含特殊触发条件变体） |
| 外交与商路 | 3 | 一厢情愿贸易 / 贸易关系好感 / 同盟点数 |
| 城邦商路加成 | 3 | 城邦类型商路加成 / 城邦区域产出 / 使者复制 |
| 同盟/宗主商路 | 4 | 同盟间 + 宗主间商路产出（起源/目的地双向） |
| 特殊机制 | 11 | 宗教压力 / 旅游业绩 / 掠夺免疫 / 禁运 / 忠诚度等 |

---

## A. 商路产出调整（城市级）

以**城市为作用域**的产出调整，建筑/区域附着时使用。

---

### EFFECT_ADJUST_CITY_TRADE_ROUTE_YIELD_FOR_DOMESTIC

调整单城国内商路固定产出。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_CITY_ADJUST_TRADE_ROUTE_YIELD_FOR_DOMESTIC` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_CITIES_ADJUST_TRADE_ROUTE_YIELD_FOR_DOMESTIC_WARLORDS` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，产出增量 |
| `YieldType` | **必写** | `Yields.YieldType`，如 `YIELD_GOLD` / `YIELD_PRODUCTION` |

> **溯源**：纳迪尔沙（波斯之剑）— 国内商路 +3 金币、+2 信仰（`COLLECTION_PLAYER_CITIES`）。基础版 `COLLECTION_OWNER` 用于建筑附着（如自定义区域建筑）。

---

### EFFECT_ADJUST_CITY_TRADE_ROUTE_YIELD_FOR_INTERNATIONAL

调整单城国际商路固定产出。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_CITY_ADJUST_TRADE_ROUTE_YIELD_FOR_INTERNATIONAL` | `COLLECTION_OWNER` |
| `MODIFIER_ALL_CITIES_ADJUST_TRADE_ROUTE_YIELD_FOR_INTERNATIONAL` | `COLLECTION_ALL_CITIES` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，产出增量 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：宗教社区（信条）— 神社/寺庙等建筑各 +2 金币（`COLLECTION_OWNER`，建筑附着）。帕依提提（自然奇观）— 国际商路 +4 金币（`COLLECTION_ALL_CITIES`，全局城市）。

---

### EFFECT_ADJUST_CITY_TRADE_ROUTE_YIELD_PER_DESTINATION_LUXURY_RESOURCE_FOR_INTERNATIONAL

国际商路**目的地**每有一种奢侈资源，产出增加。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_TRADE_ROUTE_YIELD_PER_DESTINATION_LUXURY_FOR_INTERNATIONAL` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_CITY_ADJUST_TRADE_ROUTE_YIELD_PER_DESTINATION_LUXURY_FOR_INTERNATIONAL` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，每种奢侈资源增加的产出 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：市场经济（政策）— 国际商路目的地每种奢侈资源 +1 金币。阿姆斯特丹/安条克（城邦）— 每种奢侈资源 +1 金币。贝伦塔（奇观）— 每种奢侈资源 +2 金币（`COLLECTION_OWNER`）。

---

### EFFECT_ADJUST_CITY_TRADE_ROUTE_YIELD_PER_DESTINATION_STRATEGIC_RESOURCE_FOR_DOMESTIC

国内商路**目的地**每有一种战略资源，产出增加。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_TRADE_ROUTE_YIELD_PER_DESTINATION_STRATEGIC_FOR_DOMESTIC` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，每种战略资源增加的产出 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：大商人（马可波罗/梅莉塔·本茨）— 国内商路目的地每种战略资源 +2 金币。

---

### EFFECT_ADJUST_CITY_TRADE_ROUTE_YIELD_PER_DESTINATION_STRATEGIC_RESOURCE_FOR_INTERNATIONAL

国际商路**目的地**每有一种战略资源，产出增加。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_TRADE_ROUTE_YIELD_PER_DESTINATION_STRATEGIC_FOR_INTERNATIONAL` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，每种战略资源增加的产出 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：大商人（马可波罗/梅莉塔·本茨）— 国际商路目的地每种战略资源 +2 金币。市场经济（政策）— 每种战略资源 +1 金币。

---

### EFFECT_ADJUST_CITY_TRADE_ROUTE_YIELD_PER_LOCAL_BONUS_RESOURCE_FOR_DOMESTIC

国内商路**起源城市**每有一种加成资源，产出增加。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITY_TRADE_ROUTE_YIELD_PER_LOCAL_BONUS_RESOURCE_FOR_DOMESTIC` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，每种加成资源增加的产出 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：大津巴布韦（奇观）— 国内商路起源每种加成资源 +2 金币（`COLLECTION_OWNER`，单城）。

---

### EFFECT_ADJUST_CITY_TRADE_ROUTE_YIELD_PER_LOCAL_BONUS_RESOURCE_FOR_INTERNATIONAL

国际商路**起源城市**每有一种加成资源，产出增加。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITY_TRADE_ROUTE_YIELD_PER_LOCAL_BONUS_RESOURCE_FOR_INTERNATIONAL` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_CITIES_TRADE_ROUTE_YIELD_PER_LOCAL_BONUS_RESOURCE_FOR_INTERNATIONAL` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 支持小数（如 `0.5`），每种加成资源增加的产出 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：大津巴布韦（奇观）— 国际商路起源每种加成资源 +2 金币（`COLLECTION_OWNER`）。埃塞俄比亚（阿克苏姆的遗产）— 每种加成资源 +0.5 信仰（`COLLECTION_PLAYER_CITIES`）。

---

### EFFECT_ADJUST_CITY_TRADE_ROUTE_YIELD_PER_LOCAL_LUXURY_RESOURCE_FOR_INTERNATIONAL

国际商路**起源城市**每有一种奢侈资源，产出增加。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_TRADE_ROUTE_YIELD_PER_LOCAL_LUXURY_RESOURCE_FOR_INTERNATIONAL` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_SIQI0032_CITY_TRADE_ROUTE_YIELD_PER_LOCAL_LUXURY_RESOURCE_FOR_INTERNATIONAL` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 支持小数（如 `0.5`），每种奢侈资源增加的产出 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：埃塞俄比亚（阿克苏姆的遗产）— 每种奢侈资源 +0.5 信仰（`COLLECTION_PLAYER_CITIES`）。注意 `SIQI0032` 变体为社区自定义但已在 DB 中注册为独立 ModifierType。

---

### EFFECT_ADJUST_CITY_TRADE_ROUTE_YIELD_PER_LOCAL_STRATEGIC_RESOURCE_FOR_INTERNATIONAL

国际商路**起源城市**每有一种战略资源，产出增加。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_TRADE_ROUTE_YIELD_PER_LOCAL_STRATEGIC_RESOURCE_FOR_INTERNATIONAL` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_SIQI0032_CITY_TRADE_ROUTE_YIELD_PER_LOCAL_STRATEGIC_RESOURCE_FOR_INTERNATIONAL` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 支持小数（如 `0.5`），每种战略资源增加的产出 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：埃塞俄比亚（阿克苏姆的遗产）— 每种战略资源 +0.5 信仰（`COLLECTION_PLAYER_CITIES`）。

---

### EFFECT_ADJUST_CITY_YIELD_FROM_FOREIGN_TRADE_ROUTES_PASSING_THROUGH

外国商路经过本城时，为本城提供产出。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_YIELD_FROM_FOREIGN_TRADE_ROUTES_PASSING_THROUGH` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_CITY_ADJUST_YIELD_FROM_FOREIGN_TRADE_ROUTES_PASSING_THROUGH` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，每条路过的外国商路提供的产出 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：在线社区（政策）— 经过的外国商路 +3 金币（`COLLECTION_OWNER`，单城作用域）。注意在线社区的官方 LOC 为"在线社区"，实际使用 `FOREIGN_EXCHANGE` ModifierId。

---

### EFFECT_ADJUST_CITY_YIELD_PER_MAJOR_TRADE_PARTNER

每有一个主要文明贸易伙伴，城市产出增加（仅 GS 扩展）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_PER_MAJOR_TRADE_PARTNER` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，每个主要贸易伙伴提供的产出 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：新加坡（城邦）— 每个主要贸易伙伴 +2 生产力（`COLLECTION_PLAYER_CITIES`）。

---

### EFFECT_ADJUST_TRADE_ROUTE_YIELD_PER_SPECIALTY_DISTRICT_FOR_DOMESTIC

国内商路目的地城市每有一处专业化区域，产出增加。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_PER_SPECIALTY_DISTRICT_FOR_DOMESTIC` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 支持小数（如 `0.5`），每专业区域增加的产出 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：德川家康（幕藩）— 国内商路目的地每个专业化区域 +1 文化/+1 金币/+1 科技。大商人（马可波罗）— 国内商路每个专业区域 +0.5 金币。

---

### EFFECT_ADJUST_TRADE_ROUTE_YIELD_PER_SPECIALTY_DISTRICT_FOR_INTERNATIONAL

国际商路目的地城市每有一处专业化区域，产出增加。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_PER_SPECIALTY_DISTRICT_FOR_INTERNATIONAL` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数或小数，每专业区域增加的产出 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：经济黄金时代纪念（GS 模式）— 国际商路每个专业化区域 +3 金币。

---

