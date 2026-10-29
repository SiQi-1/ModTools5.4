# modifier-trade -- 商路类 EffectType — 玩家级商路

> 分册：由 [modifier-trade.md](modifier-trade.md) 按主题拆出；覆盖 B. 商路产出调整（玩家级）、EFFECT_ADJUST_TRADE_ROUTE_YIELD、EFFECT_ADJUST_TRADE_ROUTE_YIELD_FOR_DOMESTIC、EFFECT_ADJUST_TRADE_ROUTE_YIELD_FOR_INTERNATIONAL、EFFECT_ADJUST_PLAYER_INTERNATIONAL_TRADE_ROUTE_YIELD_MODIFIER、EFFECT_ADJUST_PLAYER_TRADE_ROUTE_YIELD_MODIFIER、EFFECT_ADJUST_PLAYER_TRADE_ROUTE_YIELD_PER_IMPROVEMENT_IN_TARGET_CITY、EFFECT_ADJUST_PLAYER_INTERNATIONAL_TRADE_ROUTE_YIELD_PER_IMPROVEMENT_IN_ORIGIN_CITY、EFFECT_ADJUST_PLAYER_TRADE_ROUTE_YIELD_PER_PATH_TILE、EFFECT_ADJUST_PLAYER_TRADE_ROUTE_YIELD_PER_POST_IN_FOREIGN_CITY、EFFECT_ADJUST_PLAYER_TRADE_ROUTE_YIELD_PER_POST_IN_OWN_CITY、EFFECT_ADJUST_PLAYER_TRADE_ROUTE_YIELD_PER_TERRAIN_FOR_DOMESTIC、EFFECT_ADJUST_PLAYER_TRADE_ROUTE_YIELD_PER_TERRAIN_FOR_INTERNATIONAL、EFFECT_ADJUST_PLAYER_TRADE_ROUTE_YIELD_PER_FOLLOWER、EFFECT_ADJUST_PLAYER_PROGRESS_DIFF_TRADE_BONUS、EFFECT_ADJUST_TRADE_ROUTE_YIELD_CHANGE、EFFECT_ADJUST_TRADE_ROUTE_YIELD_FROM_OTHERS、EFFECT_ADJUST_TRADE_ROUTE_YIELD_TO_OTHERS。触发：改玩家级商路产出时。

## B. 商路产出调整（玩家级）

以**玩家为作用域**的全局产出调整，政策/领袖特质/伟人用。

---

### EFFECT_ADJUST_TRADE_ROUTE_YIELD

调整所有商路的固定产出（最基础通用的商路产出效果）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，产出增量 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：商队旅馆（政策）— 所有商路 +2 金币。三角贸易（政策）— 所有商路 +4 金币、+1 信仰。电子商务（政策）— 所有商路 +5 金币、+2 生产力。

---

### EFFECT_ADJUST_TRADE_ROUTE_YIELD_FOR_DOMESTIC

调整所有国内商路的产出（玩家全局）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_FOR_DOMESTIC` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，产出增量 |
| `YieldType` | **必写** | `Yields.YieldType` |
| `Intercontinental` | 选写 | `Boolean`，`1` = 仅跨大陆国内商路有效 |

> **溯源**：孤立主义（政策）— 国内商路 +2 粮食、+2 生产力（`Intercontinental=0`）。集体化（政策）— 国内商路 +4 粮食、+2 生产力。波斯行省总督（文明特质）— 国内商路 +1 文化、+2 金币。葡萄牙（印度之家）— 跨大陆国内商路 +6 金币/+6 信仰/+6 生产力（`Intercontinental=1`）。

---

### EFFECT_ADJUST_TRADE_ROUTE_YIELD_FOR_INTERNATIONAL

调整所有国际商路的产出（玩家全局）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_FOR_INTERNATIONAL` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，产出增量 |
| `YieldType` | **必写** | `Yields.YieldType` |
| `Intercontinental` | 选写 | `Boolean`，`1` = 仅跨大陆国际商路有效 |

> **溯源**：贸易联盟（政策）— 国际商路 +1 文化、+1 科技。市场经济（政策）— 国际商路 +2 文化、+2 科技。电子商务（政策）— 国际商路 +2 金币、+2 生产力。葡萄牙（印度之家）— 国际商路 +3 金币/+3 信仰/+3 生产力；跨大陆时 +6（`Intercontinental=1`）。

---

### EFFECT_ADJUST_PLAYER_INTERNATIONAL_TRADE_ROUTE_YIELD_MODIFIER

**百分比**调整国际商路产出（支持多产出逗号分隔）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_INTERNATIONAL_TRADE_ROUTE_YIELD_MODIFIER` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_ADJUST_INTERNATIONAL_TRADE_ROUTE_YIELD_MODIFIER_WARLORDS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 逗号分隔的百分比列表（如 `"50, 50, 50, 50, 50, 50"`），负值 = 减少 |
| `YieldType` | **必写** | 逗号分隔的 `Yields.YieldType` 列表，与 `Amount` 一一对应 |

> **溯源**：葡萄牙（印度之家）— 国际商路全产出 +50%（6 种产出各 +50%）。德川家康（幕藩）— 国际商路全产出 -25%（`_WARLORDS` 变体，6 种各 -25%）。

---

### EFFECT_ADJUST_PLAYER_TRADE_ROUTE_YIELD_MODIFIER

百分比调整商路产出（可分别指定起源/目的地侧）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_MODIFIER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数（百分比），正值为增加，负值为减少 |
| `YieldType` | **必写** | `Yields.YieldType` |
| `Origin` | 选写 | `Boolean`，`1` = 影响起源城市侧 |
| `Destination` | 选写 | `Boolean`，`1` = 影响目的地城市侧 |

> **溯源**：私掠许可证（政策）— 目的地侧 6 种产出各 -50% + 起源侧 6 种产出各 -50%（逐产出分别建 Modifier，共 12 个）。采办中心（自定义建筑）— 类似私掠许可证的正值版（各 +50%）。

---

### EFFECT_ADJUST_PLAYER_TRADE_ROUTE_YIELD_PER_IMPROVEMENT_IN_TARGET_CITY

商路目标城市每有指定改良设施，产出增加。可分别指定起源/目的地侧。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_PER_IMPROVEMENT_IN_TARGET` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_PER_IMPROVEMENT_AT_LOCATION` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，每改良设施增加的产出 |
| `YieldType` | **必写** | `Yields.YieldType` |
| `ImprovementType` | **必写** | `Improvements.ImprovementType` |
| `Origin` | 选写 | `Boolean`，`1` = 影响起源侧 |
| `Destination` | 选写 | `Boolean`，`1` = 影响目的地方侧 |

> **溯源**：威尔米娜（"同盟与贸易"领袖）— 营地 +1 粮食（Origin）、+1 金币（Destination）；牧场 +1 粮食（Origin）、+1 金币（Destination）。葡萄牙商站文明— 商站 +4 金币（Origin）、+1 生产力（Origin），使用 `AT_LOCATION` 变体。

> **区别：** `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_PER_IMPROVEMENT_IN_TARGET` 同时支持 `Origin` + `Destination` 参数。`MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_PER_IMPROVEMENT_AT_LOCATION` 仅支持 `Origin`。

---

### EFFECT_ADJUST_PLAYER_INTERNATIONAL_TRADE_ROUTE_YIELD_PER_IMPROVEMENT_IN_ORIGIN_CITY

国际商路起源城市每有指定改良设施，产出增加。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_PER_IMPROVEMENT_AT_LOCATION_BABYLON` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，每改良设施增加的产出 |
| `YieldType` | **必写** | `Yields.YieldType` |
| `ImprovementType` | **必写** | `Improvements.ImprovementType` |

> **溯源**：撒马尔罕（城邦）— 国际商路起源每有贸易圆顶 +1 金币。

---

### EFFECT_ADJUST_PLAYER_TRADE_ROUTE_YIELD_PER_PATH_TILE

商路每经过一格，产出增加。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_PER_PATH_TILE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 支持小数（如 `0.2`）或整数，每格产出增加 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：罕萨（城邦）— 商路每格 +0.2 金币。

---

### EFFECT_ADJUST_PLAYER_TRADE_ROUTE_YIELD_PER_POST_IN_FOREIGN_CITY

每条商路的外国城市中每有一个己方贸易站，产出增加。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_PER_POST_IN_FOREIGN_CITY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，每个外国城市贸易站提供的产出 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：雅加达（城邦）— 每个外国城市贸易站 +1 金币。

---

### EFFECT_ADJUST_PLAYER_TRADE_ROUTE_YIELD_PER_POST_IN_OWN_CITY

每条商路的己方城市中每有一个己方贸易站，产出增加。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_PER_POST_IN_OWN_CITY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，每个己方城市贸易站提供的产出 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：克莉奥帕特拉（地中海新娘）— 每个己方城市贸易站 +1 金币。

---

### EFFECT_ADJUST_PLAYER_TRADE_ROUTE_YIELD_PER_TERRAIN_FOR_DOMESTIC

国内商路起源/目的地城市有指定地形时，产出增加。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_PER_TERRAIN_DOMESTIC` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，每种指定地形/格提供的产出 |
| `YieldType` | **必写** | `Yields.YieldType` |
| `TerrainType` | **必写** | `Terrains.TerrainType`，如 `TERRAIN_DESERT_MOUNTAIN` |
| `Origin` | 选写 | `Boolean`，`1` = 影响起源城市 |

> **溯源**：帕查库蒂（印加路网）— 国内商路起源有沙漠山脉/草原山脉/平原山脉/雪地山脉/冻土山脉时，每种 +1 粮食（Origin=1，每种地形分别建一个 Modifier）。

---

### EFFECT_ADJUST_PLAYER_TRADE_ROUTE_YIELD_PER_TERRAIN_FOR_INTERNATIONAL

国际商路起源/目的地城市有指定地形时，产出增加。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_PER_TERRAIN_INTERNATIONAL` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，每种指定地形/格提供的产出 |
| `YieldType` | **必写** | `Yields.YieldType` |
| `TerrainType` | **必写** | `Terrains.TerrainType` |
| `Origin` | 选写 | `Boolean`，`1` = 影响起源城市 |

> **溯源**：曼萨穆萨（萨赫勒商人）— 国际商路起源有沙漠时 +1 金币（Origin=1）。

---

### EFFECT_ADJUST_PLAYER_TRADE_ROUTE_YIELD_PER_FOLLOWER

商路目的地城市的信仰追随者每有一人，产出增加。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_PER_FOLLOWER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，每个追随者提供的产出 |
| `YieldType` | **必写** | `Yields.YieldType` |

> **溯源**：欣盖提（城邦）— 目的地每位追随者 +1 信仰。

---

### EFFECT_ADJUST_PLAYER_PROGRESS_DIFF_TRADE_BONUS

根据科技/市政领先程度提供商路加成。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PROGRESS_DIFF_TRADE_BONUS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `TechCivicsPerYield` | **必写** | 整数，每领先 N 个科技/市政提供 1 点商路产出 |

> **溯源**：巴比伦（大使馆）— 每领先 3 个科技/市政，商路提供额外产出（参数名非 `Amount`，使用 `TechCivicsPerYield`）。

---

### EFFECT_ADJUST_TRADE_ROUTE_YIELD_CHANGE

调整特定商路集合的产出（同盟和紧急事件专用）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_EMERGENCY_TRADE_ROUTES_ADJUST_YIELDS` | `COLLECTION_EMERGENCY_TRADE_ROUTES` |
| `MODIFIER_ALLIANCE_TRADE_ROUTE_ADJUST_YIELD` | `COLLECTION_ALLIANCE_TRADEROUTES` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，产出增量 |
| `YieldType` | **必写** | `Yields.YieldType` |
| `AffectOrigin` | 选写 | `Boolean`，`1` = 影响起源侧 |
| `AffectDestination` | 选写 | `Boolean`，`1` = 影响目的地方侧 |

> **溯源**：经济同盟（1 级）— 同盟间商路目的地 +2 金币、起源 +4 金币。文化同盟（1 级）— 目的地方 +1 文化、起源 +1 文化。宗教同盟（1 级）— 目的地方 +2 信仰、起源 +2 信仰。科技同盟（1 级）— 目的地方 +1 科技、起源 +1 科技。背叛紧急事件 — 会员间商路起源 +2 生产力、目的地方 +2 生产力（同时设置 `AffectOrigin=1, AffectDestination=1`）。

> **注意：** 此 Effect 作用于商路集合（`COLLECTION_ALLIANCE_TRADEROUTES` / `COLLECTION_EMERGENCY_TRADE_ROUTES`），非玩家或城市级，需配合同盟/紧急事件的 SubjectRequirementSet。

---

### EFFECT_ADJUST_TRADE_ROUTE_YIELD_FROM_OTHERS

调整**其他文明通往己方**的商路为己方提供的产出（外部商路→己方获得）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_TRADE_ROUTE_YIELD_FROM_OTHERS` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_SINGLE_CITY_ADJUST_TRADE_ROUTE_YIELD_FROM_OTHERS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，产出增量 |
| `YieldType` | **必写** | `Yields.YieldType` |
| `Domestic` | 选写 | `Boolean`，`0` = 仅国际商路（默认），`1` = 含国内 |

> **溯源**：克莉奥帕特拉（地中海新娘）— 入向商路 +2 金币（`COLLECTION_PLAYER_CITIES`）。威廉明娜（橙色电台）— 入向商路 +2 文化。郑和（大商人）— 单城入向商路 +2 金币（`COLLECTION_OWNER`）。桑科雷大学（奇观）— 入向商路 +2 科技（Domestic=0）。世界议会贸易条约决议 — 入向商路 +4 金币。

---

### EFFECT_ADJUST_TRADE_ROUTE_YIELD_TO_OTHERS

调整**己方通往其他文明**的商路为对方提供的产出（己方商路→对方获得）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_TRADE_ROUTE_YIELD_TO_OTHERS` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_SINGLE_CITY_ADJUST_TRADE_ROUTE_YIELD_TO_OTHERS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，产出增量 |
| `YieldType` | **必写** | `Yields.YieldType` |
| `Domestic` | 选写 | `Boolean`，`true`/`false`，`true` = 含国内商路 |

> **溯源**：克莉奥帕特拉（地中海新娘）— 出向商路对方 +2 粮食（`COLLECTION_PLAYER_CITIES`）。各城邦类型（贸易/文化/工业/军事/宗教/科技）— 对应产出给对方 +1~+2（`COLLECTION_PLAYER_CITIES`）。桑科雷大学（奇观）— 出向商路对方 +1 金币/+1 科技；国内出向商路对方 +1 信仰/+1 科技（Domestic=1）。郑和（大商人）— 单城出向商路对方 +2 金币（`COLLECTION_OWNER`）。剩余物流（政策）— 出向国内商路对方 +2 粮食（Domestic=true）。

---

