# modifier-unit-combat -- 单位战斗/属性/移动/经验/间谍/旅游/宗教等 EffectType — 视野/其他

> 分册：由 [modifier-unit-combat.md](modifier-unit-combat.md) 按主题拆出；覆盖 视野/可见性、EFFECT_ADJUST_UNIT_HIDDEN_VISIBILITY、EFFECT_ADJUST_UNIT_SEE_HIDDEN、EFFECT_ADJUST_UNIT_SEE_THROUGH_FEATURES、EFFECT_ADJUST_UNIT_SEE_THROUGH_TERRAIN、EFFECT_ADJUST_UNIT_SIGHT、其他、EFFECT_ADJUST_NUM_UNITS_SUPPORTED、EFFECT_ADJUST_PLAYER_DISTRICT_AND_BUILDINGS_CREATE_UNIT_WITH_ABILITY_BY_CLASS、EFFECT_ADJUST_PLAYER_DISTRICT_CREATE_UNIT、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_NON_BARBARIAN_UNIT_KILLED_BY_GDR、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_NON_BARBARIAN_UNIT_SEA_KILLED、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_UNIT_PROMOTION_EARNED、EFFECT_ADJUST_UNIT_BUILD_CHARGES、EFFECT_ADJUST_UNIT_DISASTER_CHARGES、EFFECT_ADJUST_UNIT_EXTRACT_SEA_ARTIFACTS、EFFECT_ADJUST_UNIT_GREAT_PERSON_CHARGES、EFFECT_ADJUST_UNIT_INITIATION_YIELD、EFFECT_ADJUST_UNIT_INITIATION_YIELD_POPULATION、EFFECT_ADJUST_UNIT_NATURAL_WONDER_DEFERRED_CHARGES、EFFECT_ADJUST_UNIT_OWNER、EFFECT_ADJUST_UNIT_VALID_TERRAIN、EFFECT_CHANGE_UNIT_OPERATION_AVAILABILITY、EFFECT_DISTRICT_ADD_NAVAL_UNIT、EFFECT_GRANT_FREE_RESOURCE_FROM_UNIT_PLOT、EFFECT_SETTLED_FOREIGN_CONTINENT_UNIT_CLASS。触发：改视野、可见性及其他单位类效果时。

## 视野/可见性

### EFFECT_ADJUST_UNIT_HIDDEN_VISIBILITY

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_HIDDEN_VISIBILITY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Hidden` | 是 | `1`、`true`（`1`=是 / `0`=否） |

**效果**：赋予单位隐身能力（对敌方不可见）
> **溯源**：单位能力 — 隐形（`ABILITY_STEALTH`） — 赋予单位特殊能力
> **溯源**：单位晋升 — 伪装（`PROMOTION_CAMOUFLAGE`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 迷魂幕（`PROMOTION_MONK_TWILIGHT_VEIL`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_SEE_HIDDEN

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_SEE_HIDDEN` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `SeeHidden` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：赋予单位探测隐身单位的能力
> **溯源**：单位能力 — 反隐形（`ABILITY_SEE_HIDDEN`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_SEE_THROUGH_FEATURES

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_SEE_THROUGH_FEATURES` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `CanSee` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：允许单位看穿地貌
> **溯源**：单位能力 — 开阔视野（`ABILITY_UNOBSTRUCTED_VIEW`） — 赋予单位特殊能力（一览无余的视野）
> **溯源**：单位能力 — 森林斗士（`ABILITY_NAGAO`） — 赋予单位特殊能力
> **溯源**：单位晋升 — 哨兵（`PROMOTION_SENTRY`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 很干的面包（`PROMOTION_SPECIAL_CEOBE_R1`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_SEE_THROUGH_TERRAIN

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_SEE_THROUGH_TERRAIN` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `CanSee` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：允许单位看穿地形
> **溯源**：单位能力 — 开阔视野（`ABILITY_UNOBSTRUCTED_VIEW`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_SIGHT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_SIGHT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `-1`、`1`、`10`、`2`、`3` |

**效果**：调整单位的视野范围
> **溯源**：单位晋升 — 望远镜（`PROMOTION_SPYGLASS`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 航线海图（`PROMOTION_RUTTER`） — 赋予单位晋升效果（航线海图）
> **溯源**：单位晋升 — 侦察飞机（`PROMOTION_SCOUT_PLANES`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 观察（`PROMOTION_OBSERVATION`） — 赋予单位晋升效果
> **溯源**：单位能力 — 雷夫·埃里克森（`ABILITY_ERIKSON_NAVAL_SIGHT`） — 赋予单位特殊能力

---

## 其他

### EFFECT_ADJUST_NUM_UNITS_SUPPORTED

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_NUM_UNITS_SUPPORTED` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1` |
| `BuildingType` | 是 | `BUILDING_MUSEUM_ARTIFACT` |

**效果**：调整可支持的单位数量（如考古学家）
> **溯源**：文明/领袖特性 — 大英博物馆（`TRAIT_CIVILIZATION_DOUBLE_ARCHAEOLOGY_SLOTS`） — 文明或领袖特性效果

---

### EFFECT_ADJUST_PLAYER_DISTRICT_AND_BUILDINGS_CREATE_UNIT_WITH_ABILITY_BY_CLASS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISTRICT_ADJUST_PLAYER_DISTRICT_AND_BUILDINGS_CREATE_UNIT_WITH_ABILITY_BY_CLASS_GREAT_NEGOTIATORS` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_DISTRICT_ADJUST_PLAYER_DISTRICT_AND_BUILDINGS_CREATE_UNIT_WITH_ABILITY_BY_CLASS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `DistrictType` | 是 | `DISTRICT_HIPPODROME`、`DISTRICT_INDUSTRIAL_ZONE` |
| `UnitAbilityType` | 是 | `ABILITY_FREE_RESOURCE_MAITENANCE_HIPPODROME`、`ABILITY_LINCOLN_MELEE_UNITS` |
| `UnitPromotionClass` | 是 | `PROMOTION_CLASS_HEAVY_CAVALRY`、`PROMOTION_CLASS_MELEE` |

**效果**：建造区域及建筑时生成携带指定能力的单位
> **溯源**：文明/领袖特性 — 解放黑奴宣言（`TRAIT_LEADER_LINCOLN`） — 文明或领袖特性效果
> **溯源**：文明/领袖特性 — TRAIT_CIVILIZATION_DISTRICT_HIPPODROME（`TRAIT_CIVILIZATION_DISTRICT_HIPPODROME`） — 文明或领袖特性效果

---

### EFFECT_ADJUST_PLAYER_DISTRICT_CREATE_UNIT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISTRICT_CREATE_UNIT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `DistrictType` | 是 | `DISTRICT_MBANZA`、`DISTRICT_THEATER` |
| `UnitType` | 是 | `UNIT_APOSTLE` |

**效果**：完成区域建造时生成指定单位
> **溯源**：文明/领袖特性 — 宗教转换（`TRAIT_LEADER_RELIGIOUS_CONVERT`） — 文明或领袖特性效果

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_NON_BARBARIAN_UNIT_KILLED_BY_GDR

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PLAYER_ERA_SCORE_PER_NON_BARBARIAN_UNIT_KILLED_BY_GDR` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1` |

**效果**：GDR击杀非蛮族单位时获得时代分数
> **溯源**：纪念活动 — COMMEMORATION_AUTOMATON（`COMMEMORATION_AUTOMATON`）

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_NON_BARBARIAN_UNIT_SEA_KILLED

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PLAYER_ERA_SCORE_PER_NON_BARBARIAN_NAVAL_UNIT_KILLED` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1` |

**效果**：海军单位击杀非蛮族单位时获得时代分数
> **溯源**：纪念活动 — COMMEMORATION_EXPLORATION（`COMMEMORATION_EXPLORATION`）

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_UNIT_PROMOTION_EARNED

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_ALL_PLAYERS_ADJUST_ERA_SCORE_PER_UNIT_PROMOTION_EARNED` | `COLLECTION_MAJOR_PLAYERS` |

| *(无参数)* | | |
|---|---|---|

**效果**：单位晋升时获得时代分数
> **溯源**：该 EffectType 仅在 DynamicModifiers 中注册，官方数据库中无实际 Modifier 使用记录

---

### EFFECT_ADJUST_UNIT_BUILD_CHARGES

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_UNIT_ADJUST_BUILDER_CHARGES` | `COLLECTION_OWNER` |
| `MODIFIER_CEOBE_PLAYER_UNIT_ADJUST_BUILDER_CHARGES` | `COLLECTION_OWNER` |
| `MODIFIER_SINGLE_CITY_BUILDER_CHARGES` | `COLLECTION_CITY_TRAINED_UNITS` |
| `MODIFIER_PLAYER_TRAINED_UNITS_ADJUST_BUILDER_CHARGES` | `COLLECTION_PLAYER_TRAINED_UNITS` |
| `MODIFIER_PLAYER_UNITS_ADJUST_BUILDER_CHARGES` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `-1`、`1`、`2`、`3` |

**效果**：调整建造者/工兵的使用次数
> **溯源**：政策 — 公共工程（`POLICY_PUBLIC_WORKS`） — 通过政策卡提供加成
> **溯源**：政策 — 农奴制（`POLICY_SERFDOM`） — 通过政策卡提供加成
> **溯源**：奇观 — 金字塔（`BUILDING_PYRAMIDS`） — 奇观效果
> **溯源**：文明/领袖特性 — 始皇帝（`FIRST_EMPEROR_TRAIT`） — 文明或领袖特性效果
---

### EFFECT_ADJUST_UNIT_DISASTER_CHARGES

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_UNIT_ADJUST_DISASTER_CHARGES` | `COLLECTION_OWNER` |

| *(无参数)* | | |
|---|---|---|

**效果**：调整单位应对灾害的使用次数
> **溯源**：该 EffectType 仅在 DynamicModifiers 中注册，官方数据库中无实际 Modifier 使用记录

---

### EFFECT_ADJUST_UNIT_EXTRACT_SEA_ARTIFACTS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_EXTRACT_SEA_ARTIFACTS` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Extract` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：赋予单位提取海洋文物的能力
> **溯源**：市政 — 文化遗产（`CIVIC_CULTURAL_HERITAGE`）

---

### EFFECT_ADJUST_UNIT_GREAT_PERSON_CHARGES

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_GREAT_PERSON_CHARGES` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1` |

**效果**：调整伟人的使用次数
> **溯源**：建筑 — 摩索拉斯王陵墓（`BUILDING_HALICARNASSUS_MAUSOLEUM`）

---

### EFFECT_ADJUST_UNIT_INITIATION_YIELD

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_INITIATION_GOLD` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `100` |
| `YieldType` | 是 | `YIELD_GOLD` |

**效果**：宗教单位首次传教时获得指定产出
> **溯源**：单位晋升 — 赎罪卷小贩（`PROMOTION_INDULGENCE_VENDOR`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_INITIATION_YIELD_POPULATION

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_INITIATION_YIELD_POPULATION` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `20` |
| `YieldType` | 是 | `YIELD_SCIENCE` |

**效果**：宗教单位按目标城市人口传教时获得指定产出
> **溯源**：城邦 — 菲斯（`MINOR_CIV_FEZ`） — 城邦宗主国加成

---

### EFFECT_ADJUST_UNIT_NATURAL_WONDER_DEFERRED_CHARGES

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_NATURAL_WONDER_DEFERRED_CHARGES` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `3` |

**效果**：宗教单位在自然奇观旁传教不消耗次数
> **溯源**：单位晋升 — 朝圣者（`PROMOTION_PILGRIM`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_OWNER

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_OWNER` | `COLLECTION_ALL_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `NewOwner` | 是 | `Player` |

**效果**：转移单位的所有权给当前玩家
> **溯源**：伟人能力 — 布狄卡（`GREAT_PERSON_INDIVIDUAL_BOUDICA`）（把相邻蛮族转到您的控制之下。）

---

### EFFECT_ADJUST_UNIT_VALID_TERRAIN

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_VALID_TERRAIN` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_UNITS_ADJUST_VALID_TERRAIN` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `TerrainType` | 是 | `TERRAIN_OCEAN` |
| `Valid` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：设置单位可通行的地形类型
> **溯源**：文明/领袖特性 — 龙骨船（`TRAIT_CIVILIZATION_EARLY_OCEAN_NAVIGATION`） — 文明或领袖特性效果
> **溯源**：伟人能力 — 雷夫·埃里克森（`GREAT_PERSON_INDIVIDUAL_LEIF_ERIKSON`）
> **溯源**：科技 — 制图学（`TECH_CARTOGRAPHY`）
> **溯源**：文明/领袖特性 — 玛那（`TRAIT_CIVILIZATION_MAORI_MANA`） — 文明或领袖特性效果

---

### EFFECT_CHANGE_UNIT_OPERATION_AVAILABILITY

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_ALL_UNITS_DISABLE_OPERATION` | `COLLECTION_ALL_UNITS` |

| *(无参数)* | | |
|---|---|---|

**效果**：禁用/启用单位的特定行动操作
> **溯源**：世界议会决议 — "间谍协定"（`WC_RES_ESPIONAGE_PACT`） — 世界议会议案效果

---

### EFFECT_DISTRICT_ADD_NAVAL_UNIT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_DISTRICT_ADD_NAVAL_UNIT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `DistrictType` | 是 | `DISTRICT_ROYAL_NAVY_DOCKYARD` |

**效果**：完成区域建造时获得一艘海军单位
> **溯源**：文明/领袖特性 — 英国强权下的和平（`TRAIT_LEADER_PAX_BRITANNICA`） — 文明或领袖特性效果

---

### EFFECT_GRANT_FREE_RESOURCE_FROM_UNIT_PLOT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GRANT_FREE_RESOURCE_FROM_UNIT_PLOT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1` |

**效果**：赠予单位所在单元格的奢侈品资源
> **溯源**：伟人能力 — 柯莱欧司（`GREAT_PERSON_INDIVIDUAL_COLAEUS`）（赠予{Amount}份该单元格上的奢侈品资源给您的 [ICON_Capital] 首都城市。）
> **溯源**：伟人能力 — 斐迪南·麦哲伦（`GREAT_PERSON_INDIVIDUAL_FERDINAND_MAGELLAN`）

---

### EFFECT_SETTLED_FOREIGN_CONTINENT_UNIT_CLASS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_SETTLE_FOREIGN_CONTINENT_UNIT_CLASS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `UnitPromotionClassType` | 是 | `PROMOTION_CLASS_MELEE` |

**效果**：在其他大陆建立城市时赠送指定兵种类别的单位
> **溯源**：文明/领袖特性 — 英国强权下的和平（`TRAIT_LEADER_PAX_BRITANNICA`） — 文明或领袖特性效果

---

