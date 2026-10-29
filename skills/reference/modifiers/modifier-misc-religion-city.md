# modifier-misc — 其余杂项类 EffectType — 宗教/城市

> 分册：由 [modifier-misc.md](modifier-misc.md) 按主题拆出；覆盖 宗教与信仰、EFFECT_ADD_BELIEF、EFFECT_ADJUST_CAN_FAITH_PURCHASE_DISTRICTS、EFFECT_ADJUST_DISABLE_PATRONAGE、EFFECT_ADJUST_GAINS_ALL_FOLLOWER_BELIEFS、EFFECT_ADJUST_PLAYER_FAITH_FROM_DISPERSAL、EFFECT_ADJUST_PLAYER_FAITH_PEACEFUL_FOUNDERS、EFFECT_GRANT_PLAYER_FAITH_FROM_HARVEST、城市与人口、EFFECT_ADJUST_CITIES_FRESHWATER_HOUSING_BONUS、EFFECT_ADJUST_CITIES_HAS_URBAN_DEFENSES、EFFECT_ADJUST_EXTRA_STARTING_POPULATION_OFF_HOME_CONTINENT、EFFECT_ADJUST_NO_FRESH_WATER_HOUSING、EFFECT_ADJUST_PLAYER_FEAUTE_REQUIRED_FOR_SPECIALTY_DISTRICTS、EFFECT_ADJUST_POPULATION_AFTER_CONQUEST、EFFECT_ADJUST_WATER_HOUSING。触发：改宗教信仰、城市人口时。

## 宗教与信仰

### EFFECT_ADD_BELIEF

为玩家创建的宗教额外添加信条（超过常规数量限制，与宗教信条选择面板解耦）。`BeliefType` 指定要添加的信条类型，`Amount` 为添加数量。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADD_BELIEF` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `BeliefType` | `BELIEF_CHURCH_PROPERTY` 等，引用 [Beliefs.BeliefType] |
| `Amount` | 整数，添加的信条数量 |

> **溯源**：DynamicModifiers 定义（Base `Modifiers.xml`），游戏中无活跃 DB 实例。效果是直接给玩家挂载一条信条，与宗教信条选择面板解耦，常用于文明/领袖特质绕过正常信条获取流程。

---

### EFFECT_ADJUST_CAN_FAITH_PURCHASE_DISTRICTS

允许所在城市使用信仰购买区域。`CanPurchase=1`。由总督能力提供。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_GOVERNOR_ADJUST_CAN_FAITH_PURCHASE_DISTRICTS` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `CanPurchase` | `1` |

> **溯源**：GovernorPromotionModifiers — 总督「莫克夏」晋升

---

### EFFECT_ADJUST_DISABLE_PATRONAGE

禁用伟人赞助（不能用金币/信仰直接购买伟人）。无参数。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISABLE_PATRONAGE` | `COLLECTION_OWNER` |

| 参数 |
|---|
| （无参数） |

> **溯源**：Expansion1/2 DLC — 仅 XML 声明，无数据库实例

---

### EFFECT_ADJUST_GAINS_ALL_FOLLOWER_BELIEFS

获得所有信教文明的信徒信条效果（你的宗教在外国城市中享有的信徒信条也为你生效）。`Enable=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GAINS_ALL_FOLLOWER_BELIEFS` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Enable` | `1` |

> **溯源**：TraitModifiers — 印度文明「达摩」（TRAIT_CIVILIZATION_INDIA_DHARMA）

---

### EFFECT_ADJUST_PLAYER_FAITH_FROM_DISPERSAL

清除蛮族营地时获得信仰。`Amount=50`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_FAITH_FROM_DISPERSAL` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `50` |

> **溯源**：无特定上游（通用效果）

---

### EFFECT_ADJUST_PLAYER_FAITH_PEACEFUL_FOUNDERS

和平创立者信仰加成（每座信仰你的宗教的外国城市提供额外信仰产出）。`Amount=5`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_FAITH_PEACEFUL_FOUNDERS` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `5` |

> **溯源**：BeliefModifiers — 信条「圣巴斯弟盎受难」（BELIEF_PEACEFUL_FOUNDERS）

---

### EFFECT_GRANT_PLAYER_FAITH_FROM_HARVEST

收获资源/移除地貌时获得信仰。`Amount=100`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GRANT_FAITH_FROM_HARVEST` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `100` |

> **溯源**：Effects.csv 标记 USER ADDED — [无官方使用示例，但 Mod 中可用]

---


## 城市与人口

### EFFECT_ADJUST_CITIES_FRESHWATER_HOUSING_BONUS

为有淡水水源的城市提供额外住房加成。`HasBonus=1` 所有淡水城市都获得。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GRANT_CITIES_FRESHWATER_HOUSING_BONUS` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `HasBonus` | `1` |

> **溯源**：无特定上游（通用效果）

---

### EFFECT_ADJUST_CITIES_HAS_URBAN_DEFENSES

使城市自动获得城墙防御（无需建造城墙建筑）。`DefenseValue=400`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GRANT_CITIES_URBAN_DEFENSES` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `DefenseValue` | `400` |

> **溯源**：无特定上游（通用效果）

---

### EFFECT_ADJUST_EXTRA_STARTING_POPULATION_OFF_HOME_CONTINENT

非首都大陆新建城市的初始额外人口。`Amount=3` 表示初始为4人口。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_EXTRA_STARTING_POPULATION_OFF_HOME_CONTINENT` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `3` |

> **溯源**：TraitModifiers — 毛利文明「人船合一」

---

### EFFECT_ADJUST_NO_FRESH_WATER_HOUSING

调整无水城市的基础住房。`NoHousing=1` 表示无水城市无基础住房。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_NO_FRESH_WATER_HOUSING` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 值/引用 |
|---|---|
| `NoHousing` | `1` |

> **溯源**：TraitModifiers — 澳大利亚文明「南方大陆」

---

### EFFECT_ADJUST_PLAYER_FEAUTE_REQUIRED_FOR_SPECIALTY_DISTRICTS

调整建造专属区域所需的地貌条件。`FeatureType` 指定地形（森林/雨林/沼泽）。注意 `FEAUTE`=法语拼写遗留。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_FEAUTE_REQUIRED_FOR_SPECIALTY_DISTRICTS` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `FeatureType` | `FEATURE_FOREST` / `FEATURE_JUNGLE` / `FEATURE_MARSH` |

> **溯源**：TraitModifiers — 巴西文明「亚马逊」（TRAIT_CIVILIZATION_BRAZIL_AMAZON）

---

### EFFECT_ADJUST_POPULATION_AFTER_CONQUEST

调整征服后城市剩余人口比例。`Percent=100` 表示人口不变。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_POPULATION_AFTER_CONQUEST` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Percent` | `100` |

> **溯源**：BuildingModifiers — 奇观「兵马俑」（BUILDING_TERRACOTTA_ARMY）

---

### EFFECT_ADJUST_WATER_HOUSING

调整沿海/临水城市的基础住房。`Amount=3` 表示额外+3住房。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_WATER_HOUSING` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `3` |

> **溯源**：TraitModifiers — 澳大利亚文明「南方大陆」

---


