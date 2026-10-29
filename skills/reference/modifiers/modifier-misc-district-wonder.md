# modifier-misc — 其余杂项类 EffectType — 区域/建筑/奇观

> 分册：由 [modifier-misc.md](modifier-misc.md) 按主题拆出；覆盖 区域与建筑、EFFECT_ADD_CULTURE_BOMB_TRIGGER、EFFECT_ADD_PLAYER_PROJECT_AVAILABILITY、EFFECT_ADJUST_ALL_BUILDINGS_PURCHASE_COST、EFFECT_ADJUST_ALL_DISTRICTS_CULTURE_BOMB、EFFECT_ADJUST_ALL_DISTRICTS_PRODUCTION、EFFECT_ADJUST_ALL_DISTRICTS_PURCHASE_COST、EFFECT_ADJUST_ALL_PROJECTS_PRODUCTION、EFFECT_ADJUST_AUTO_THEMED_BUILDINGS_WITH_X_SLOTS、EFFECT_ADJUST_PROJECT_PRODUCTION、EFFECT_ADJUST_SPACE_RACE_PROJECTS_PRODUCTION、奇观、EFFECT_ADJUST_RIVER_WONDER_PRODUCTION、EFFECT_ADJUST_WONDER_ADJACENT_NATURAL_WONDER_PRODUCTION、EFFECT_ADJUST_WONDER_ERA_PRODUCTION、EFFECT_ADJUST_WONDER_PRODUCTION、自然奇观、EFFECT_ADJUST_NATURAL_WONDER_AMENITY、EFFECT_ADJUST_NATURAL_WONDER_RELIC。触发：改区域建筑、奇观、自然奇观时。

## 区域与建筑

### EFFECT_ADD_CULTURE_BOMB_TRIGGER

添加文化炸弹触发条件：建造指定区域或改良设施时自动吞并周围地块。`DistrictType`/`ImprovementType` 二选一。`CaptureOwnedTerritory=0` 不吞并已有归属地块。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADD_CULTURE_BOMB_TRIGGER` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `CaptureOwnedTerritory` | `0` |
| `DistrictType` | `DISTRICT_AMBUSH_ZONE` / `DISTRICT_ENCAMPMENT` / `DISTRICT_HARBOR` / `DISTRICT_HOLY_SITE` / `DISTRICT_INDUSTRIAL_ZONE` / `DISTRICT_UNVEILING_OF_DEVOTION` / `DISTRICT_VICTORIA_HIGHER_ED` |
| `ImprovementType` | `IMPROVEMENT_FARM` / `IMPROVEMENT_FISHING_BOATS` / `IMPROVEMENT_FORT` / `IMPROVEMENT_MINE` / `IMPROVEMENT_PASTURE` / `IMPROVEMENT_QUARRY` |

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_ALL_PLAYERS_ADD_CULTURE_BOMB_TRIGGER` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 值/引用 |
|---|---|
| `CaptureOwnedTerritory` | `0` |
| `DistrictType` | `DISTRICT_PRESERVE` |

> **溯源**：TraitModifiers（毛利、澳大利亚、印加等文明）; BuildingModifiers

---

### EFFECT_ADD_PLAYER_PROJECT_AVAILABILITY

使玩家可以使用特定项目（如文明专属项目、紧急事件项目、退役电厂等）。`ProjectType` 指定。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_EMERGENCY_PLAYERS_MAKE_PROJECT_AVAILABLE` | `COLLECTION_EMERGENCY_PLAYERS` |

| 参数 | 值/引用 |
|---|---|
| `ProjectType` | `PROJECT_DECOMMISSION_COAL_POWER_PLANT` / `PROJECT_DECOMMISSION_NUCLEAR_POWER_PLANT` / `PROJECT_DECOMMISSION_OIL_POWER_PLANT` / `PROJECT_SEND_AID` / `PROJECT_TRAIN_ASTRONAUTS` / `PROJECT_TRAIN_ATHLETES` |

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ALLOW_PROJECT_CHINA` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `ProjectType` | `PROJECT_LIJIA_FAITH` / `PROJECT_LIJIA_FOOD` / `PROJECT_LIJIA_GOLD` |

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ALLOW_PROJECT_CATHERINE` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `ProjectType` | `PROJECT_COURT_FESTIVAL` |

> **溯源**：TraitModifiers（凯瑟琳华丽派对等）; EmergencyRewards

---

### EFFECT_ADJUST_ALL_BUILDINGS_PURCHASE_COST

调整所有建筑的购买费用百分比。`Amount=20` 表示降价20%。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_ALL_BUILDINGS_PURCHASE_COST` | `COLLECTION_PLAYER_CITIES` |

| 参数 |
|---|
| （无参数） |

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_CITY_ADJUST_ALL_BUILDINGS_PURCHASE_COST` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `20` |

> **溯源**：BuildingModifiers — 建筑「大市场」（BUILDING_SUKIENNICE）

---

### EFFECT_ADJUST_ALL_DISTRICTS_CULTURE_BOMB

使所有区域建造都能触发文化炸弹（全局效果）。无参数。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_ALL_DISTRICTS_CULTURE_BOMB` | `COLLECTION_OWNER` |

| 参数 |
|---|
| （无参数） |

> **溯源**：无特定上游（通用效果）

---

### EFFECT_ADJUST_ALL_DISTRICTS_PRODUCTION

调整所有区域的生产力消耗百分比。`Amount=20/25/30/50`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_ALL_DISTRICTS_PRODUCTION` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `20` / `25` / `30` / `50` |

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_CITY_INCREASE_DISTRICT_PRODUCTION_RATE` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `20` |

> **溯源**：TraitModifiers（多个文明领袖特性）; CivicModifiers（市政「城市化」等）

---

### EFFECT_ADJUST_ALL_DISTRICTS_PURCHASE_COST

调整所有区域的购买费用百分比。`Amount=20`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_CITY_ADJUST_ALL_DISTRICTS_PURCHASE_COST` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `20` |

> **溯源**：BuildingModifiers — 建筑「大市场」

---

### EFFECT_ADJUST_ALL_PROJECTS_PRODUCTION

调整所有项目的生产力消耗百分比。`Amount=5/20/30`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_ALL_PROJECTS_PRODUCTION` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `20` / `30` / `5` |

> **溯源**：TraitModifiers（罗斯福进步党）; GovernmentModifiers（政体加成）

---

### EFFECT_ADJUST_AUTO_THEMED_BUILDINGS_WITH_X_SLOTS

自动主题化指定槽位数量的建筑。`Amount`=槽位数阈值，`IsWonder` 区分奇观/普通建筑。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_AUTO_THEME_BUILDINGS_WITH_X_SLOTS` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `2` / `3` |
| `IsWonder` | `0` / `1` |

> **溯源**：BuildingModifiers — 奇观「冬宫博物馆」（BUILDING_HERMITAGE）

---

### EFFECT_ADJUST_PROJECT_PRODUCTION

调整特定项目的生产力消耗。`ProjectType` 指定项目。`Amount=100` 翻倍速度，`Amount=-50` 减慢一半。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_PROJECT_PRODUCTION` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `100` / `50` |
| `ProjectType` | `PROJECT_BUILD_NUCLEAR_DEVICE` / `PROJECT_BUILD_THERMONUCLEAR_DEVICE` / `PROJECT_MANHATTAN_PROJECT` / `PROJECT_OPERATION_IVY` |

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_CITY_ADJUST_PROJECT_PRODUCTION` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `30` |
| `ProjectType` | `PROJECT_BUILD_NUCLEAR_DEVICE` / `PROJECT_BUILD_THERMONUCLEAR_DEVICE` / `PROJECT_MANHATTAN_PROJECT` / `PROJECT_OPERATION_IVY` |

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_ALL_CITIES_ADJUST_PROJECT_PRODUCTION` | `COLLECTION_ALL_CITIES` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `-50` / `100` |

> **溯源**：PolicyModifiers（曼哈顿计划、常春藤行动等）; EmergencyRewards

---

### EFFECT_ADJUST_SPACE_RACE_PROJECTS_PRODUCTION

调整所有太空竞赛项目的生产力消耗。`Amount=15/20/30/100`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_SPACE_RACE_PROJECTS_PRODUCTION` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `100` / `15` / `20` |

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_CITY_ADJUST_SPACE_RACE_PROJECTS_PRODUCTION` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `30` |

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_EMERGENCY_CITIES_ADJUST_SPACE_RACE_PROJECTS_PRODUCTION` | `COLLECTION_EMERGENCY_CITIES` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `20` / `40` |

> **溯源**：PolicyModifiers — 政策「一体化空间站」; EmergencyRewards

---


## 奇观

### EFFECT_ADJUST_RIVER_WONDER_PRODUCTION

临河城市建造奇观时获得生产力加成。`Amount=15` 表示+15%。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_RIVER_WONDER_PRODUCTION` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `15` |

> **溯源**：BuildingModifiers — 奇观「大浴场」

---

### EFFECT_ADJUST_WONDER_ADJACENT_NATURAL_WONDER_PRODUCTION

邻近特定自然奇观时建造奇观获得生产力加成。`FeatureType=FEATURE_IKKIL`（伊基尔天坑）。`Amount=50`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_ALL_CITIES_ADJUST_WONDER_ADJACENT_NATURAL_WONDER_PRODUCTION` | `COLLECTION_ALL_CITIES` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `50` |
| `FeatureType` | `FEATURE_IKKIL` |

> **溯源**：All Cities 范围 — 由自然奇观自身（FEATURE_IKKIL）提供

---

### EFFECT_ADJUST_WONDER_ERA_PRODUCTION

建造其他时代（非当前时代）的奇观时获得生产力加成。`StartEra`/`EndEra` 划定时代范围。`IsWonder=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_WONDER_ERA_PRODUCTION` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `10` / `15` / `20` |
| `EndEra` | `ERA_CLASSICAL` / `ERA_FUTURE` / `ERA_INDUSTRIAL` / `ERA_INFORMATION` / `ERA_RENAISSANCE` |
| `IsWonder` | `1` |
| `StartEra` | `ERA_ANCIENT` / `ERA_INDUSTRIAL` / `ERA_MEDIEVAL` |

> **溯源**：TraitModifiers（法国、埃及、中国等文明）; BuildingModifiers（多个奇观）

---

### EFFECT_ADJUST_WONDER_PRODUCTION

调整奇观生产力消耗（通用加成，无时代限制）。`Amount=10/15/30/100`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_WONDER_PRODUCTION` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `10` / `15` / `30` |

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_CITY_ADJUST_WONDER_PRODUCTION` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `100` |

> **溯源**：TraitModifiers（多个文明领袖特性）; PolicyModifiers（哥特式建筑等）

---


## 自然奇观

### EFFECT_ADJUST_NATURAL_WONDER_AMENITY

调整自然奇观为所在城市提供的宜居度。`Amount=1` 所有城市。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_ALL_CITIES_ADJUST_NATURAL_WONDER_AMENITY` | `COLLECTION_ALL_CITIES` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` |

> **溯源**：无特定上游（通用效果）

---

### EFFECT_ADJUST_NATURAL_WONDER_RELIC

发现自然奇观时获得一个圣遗物。`Amount=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_NATURAL_WONDER_RELIC` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` |

> **溯源**：无特定上游（通用效果）

---


