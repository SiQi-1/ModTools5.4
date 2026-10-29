# modifier-misc — 其余杂项类 EffectType — 经济/贸易

> 分册：由 [modifier-misc.md](modifier-misc.md) 按主题拆出；覆盖 经济与黄金、EFFECT_ADJUST_BONUS_RATE、EFFECT_ADJUST_FLAT_BONUS、EFFECT_ADJUST_GOLD_DISPERSAL、EFFECT_ADJUST_MULTIPLY_TREASURY、EFFECT_ADJUST_PLAYER_BID_COST_MODIFIER、EFFECT_ADJUST_PLAYER_GOLD_INTEREST_PERCENT、贸易与路线、EFFECT_ADJUST_FORBID_LAND_ROUTE、EFFECT_ADJUST_PLAYER_IMMEDIATE_TRADING_POST、EFFECT_ADJUST_PLAYER_IMPROVED_ROUTE_LEVEL、EFFECT_GRANT_ROUTE_IN_RADIUS。触发：改经济黄金、贸易路线时。

## 经济与黄金

### EFFECT_ADJUST_BONUS_RATE

调整政体加成资源的基础倍率。`BonusRate` 为倍率值，`BonusType` 指定加成种类，`CityStatesOnly`（UNTESTED）限定仅对城邦生效。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GOVERNMENT_ADJUST_BONUS_RATE` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `BonusRate` | 整数，倍率值 |
| `BonusType` | 引用 [GovernmentBonusNames.GovernmentBonusType] |
| `CityStatesOnly` | `0` / `1`，UNTESTED Boolean |

> **溯源**：DynamicModifiers 定义（Base `Modifiers.xml`），游戏中无活跃 DB 实例，由政体系统使用

---

### EFFECT_ADJUST_FLAT_BONUS

调整政体固定加成的数值。`BonusType` 指定加成种类（战斗经验/区域生产力/使者/信仰折扣/金币折扣/伟人点/商路/单位生产力/奇观建造），`Amount` 指定数值。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GOVERNMENT_FLAT_BONUS` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `10` / `100` / `15` / `20` / `30` / `50` |
| `BonusType` | `GOVERNMENTBONUS_COMBAT_EXPERIENCE` / `GOVERNMENTBONUS_DISTRICT_PRODUCTION` / `GOVERNMENTBONUS_ENVOYS` / `GOVERNMENTBONUS_FAITH_PURCHASES` / `GOVERNMENTBONUS_GOLD_PURCHASES` / `GOVERNMENTBONUS_GREAT_PEOPLE` / `GOVERNMENTBONUS_UNIT_PRODUCTION` / `GOVERNMENTBONUS_WONDER_CONSTRUCTION` |

> **溯源**：PolicyModifiers（精英统治、古典共和、君主制、神权政治、共产主义等多种政策）

---

### EFFECT_ADJUST_GOLD_DISPERSAL

调整清除蛮族营地获得的金钱。`Improvement=IMPROVEMENT_BARBARIAN_CAMP` 限定蛮族营地。`Amount=0/200/300/400`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_GOLD_DISPERSAL` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `0` / `200` / `300` / `400` |
| `Improvement` | `IMPROVEMENT_BARBARIAN_CAMP` |

> **溯源**：PolicyModifiers — 政策「军事纪律」（POLICY_DISCIPLINE）

---

### EFFECT_ADJUST_MULTIPLY_TREASURY

调整国库金币总量的乘数因子。`Amount=100` 翻倍，`Amount=50` 增加50%。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_MULTIPLY_TREASURY` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `100` / `30` / `50` |

> **溯源**：CivicModifiers — 市政「重商主义」（CIVIC_MERCANTILISM）

---

### EFFECT_ADJUST_PLAYER_BID_COST_MODIFIER

调整玩家在世博会/国际项目等竞标中的费用（外交支持花费折扣）。`Amount` 为费用调整量。ESTIMATED 级别参数。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_BID_MODIFIER` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | 整数，ESTIMATED |

> **溯源**：Expansion2 DLC — `Expansion2_Modifiers.xml` 声明，世博会竞标系统

---

### EFFECT_ADJUST_PLAYER_GOLD_INTEREST_PERCENT

调整国库资金的利率（每回合金币增长百分比）。无参数，由经济系统硬编码。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_GOLD_INTEREST_PERCENT` | `COLLECTION_OWNER` |

| 参数 |
|---|
| （无参数） |

> **溯源**：Base XML — 无数据库实例，经济系统自动应用

---


## 贸易与路线

### EFFECT_ADJUST_FORBID_LAND_ROUTE

禁止陆上贸易路线。`Domestic=0` 禁止对内陆上路线。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_FORBID_LAND_ROUTE` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Domestic` | `0` |

> **溯源**：TraitModifiers — 印度尼西亚文明「黄金群岛」

---

### EFFECT_ADJUST_PLAYER_IMMEDIATE_TRADING_POST

在贸易路线目标城市当回合立即建立商站。`ImmediateTradingPost=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_IMMEDIATE_TRADING_POST` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `ImmediateTradingPost` | `1` |

> **溯源**：TraitModifiers — 蒙古文明「驿站」

---

### EFFECT_ADJUST_PLAYER_IMPROVED_ROUTE_LEVEL

提升境内道路的基础等级。`ImprovedRouteLevel=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_IMPROVED_ROUTE_LEVEL` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `ImprovedRouteLevel` | `1` |

> **溯源**：TraitModifiers — 波斯文明「总督辖区」（TRAIT_CIVILIZATION_PERSIA_SATRAPIES）

---

### EFFECT_GRANT_ROUTE_IN_RADIUS

在指定半径内自动铺设道路。`RouteType=ROUTE_MODERN_ROAD`，`Radius=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_GRANT_ROUTE_IN_RADIUS` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Radius` | `1` |
| `RouteType` | `ROUTE_MODERN_ROAD` |

> **溯源**：BuildingModifiers — 建筑「航海学校」

---


