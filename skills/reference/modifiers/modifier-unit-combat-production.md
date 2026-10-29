# modifier-unit-combat -- 单位战斗/属性/移动/经验/间谍/旅游/宗教等 EffectType — 生产/购买

> 分册：由 [modifier-unit-combat.md](modifier-unit-combat.md) 按主题拆出；覆盖 生产/购买、EFFECT_ADJUST_ALL_UNITS_PURCHASE_COST、EFFECT_ADJUST_ALL_UNIT_PRODUCTION_MODIFIER、EFFECT_ADJUST_CITY_ALL_MILITARY_UNITS_PRODUCTION、EFFECT_ADJUST_CITY_POPULATION_UNIT_CREATED、EFFECT_ADJUST_CITY_PRODUCTION_UNIT、EFFECT_ADJUST_PLAYER_BAN_UNIT_PRODUCTION_YIELD、EFFECT_ADJUST_PLAYER_BLOCK_UNIT_ENTRY、EFFECT_ADJUST_PLAYER_BUFF_UNIT_PRODUCTION_YIELD、EFFECT_ADJUST_PLAYER_LEVIED_UNIT_UPGRADE_DISCOUNT_PERCENT、EFFECT_ADJUST_PLAYER_UNIT_BUILD_DISABLED、EFFECT_ADJUST_PLAYER_UNIT_DISTRICT_PERCENT、EFFECT_ADJUST_PLAYER_UNIT_PROJECT_PERCENT、EFFECT_ADJUST_PLAYER_UNIT_UPGRADE_DISCOUNT_PERCENT、EFFECT_ADJUST_PLAYER_UNIT_UPGRADE_RESOURCE_COST_DISCOUNT、EFFECT_ADJUST_PLAYER_UNIT_WONDER_PERCENT、EFFECT_ADJUST_PLAYER_VALID_UNIT_BUILD、EFFECT_ADJUST_UNIT_DOMAIN_PRODUCTION、EFFECT_ADJUST_UNIT_MAINTENANCE_DISCOUNT、EFFECT_ADJUST_UNIT_PRODUCTION、EFFECT_ADJUST_UNIT_PURCHASE_COST、EFFECT_ADJUST_UNIT_TAG_ERA_PRODUCTION、EFFECT_ENABLE_UNIT_FAITH_PURCHASE、EFFECT_GRANT_CITY_YIELD_PERCENT_UNIT_CREATED_COST、EFFECT_GRANT_PLAYER_YIELD_PERCENT_UNIT_COST。触发：改单位生产、购买、升级费用时。

## 生产/购买

### EFFECT_ADJUST_ALL_UNITS_PURCHASE_COST

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_CITY_ADJUST_ALL_UNITS_PURCHASE_COST` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_CITIES_ADJUST_UNITS_PURCHASE_COST` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `-100`、`20`、`30` |
| `IncludeCivilian` | 是 | `0`、`1`（`1`=是 / `0`=否） |
| `UnitDomain` | 是 | `DOMAIN_ALL`、`DOMAIN_LAND` |

**效果**：调整所有单位的购买费用
> **溯源**：区域 — 曼丁哥市场（`DISTRICT_SUGUBA`）
> **溯源**：政策 — 权力归花儿（`POLICY_FLOWER_POWER`） — 通过政策卡提供加成

---

### EFFECT_ADJUST_ALL_UNIT_PRODUCTION_MODIFIER

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_UNIT_PRODUCTION_MODIFIER` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_SINGLE_CITY_ADJUST_UNIT_PRODUCTION_MODIFIER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `-100`、`-30`、`15` |

**效果**：调整所有单位的生产力产出倍率
> **溯源**：建筑 — 基尔瓦基斯瓦尼（`BUILDING_KILWA_KISIWANI`）
> **溯源**：政策 — 权力归花儿（`POLICY_FLOWER_POWER`） — 通过政策卡提供加成
> **溯源**：文明/领袖特性 — 杰利之歌（`TRAIT_CIVILIZATION_MALI_GOLD_DESERT`） — 文明或领袖特性效果

---

### EFFECT_ADJUST_CITY_ALL_MILITARY_UNITS_PRODUCTION

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_MILITARY_UNITS_PRODUCTION` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_SINGLE_CITY_ADJUST_MILITARY_UNITS_PRODUCTION` | `COLLECTION_OWNER` |
| `MODIFIER_GOVERNOR_ADJUST_CITY_MILITARY_UNIT_PRODUCTION` | `COLLECTION_OWNER` |
| `MODIFIER_ALLIANCE_CITIES_MILITARY_UNIT_PRODUCTION` | `COLLECTION_ALLIANCE_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `15`、`20`、`200`、`25`、`5`、`50` |
| `EndEra` | 是 | `ERA_CLASSICAL` |
| `PromotionClass` | 是 | `PROMOTION_CLASS_NAVAL_RAIDER`、`PROMOTION_CLASS_NAVAL_RANGED` |
| `StartEra` | 是 | `ERA_ANCIENT` |

**效果**：调整城市军事单位的生产力产出倍率
> **溯源**：伟人能力 — 德怀特·艾森豪威尔（`GREAT_PERSON_INDIVIDUAL_DWIGHT_EISENHOWER`）（为军事单位+5% [ICON_Production] 生产力。）
> **溯源**：文明/领袖特性 — MINOR_CIV_DEFAULT_TRAIT（`MINOR_CIV_DEFAULT_TRAIT`）
> **溯源**：纪念活动 — COMMEMORATION_MILITARY（`COMMEMORATION_MILITARY`）
> **溯源**：伟人能力 — 切斯特·尼米兹（`GREAT_PERSON_INDIVIDUAL_CHESTER_NIMITZ`）
> **溯源**：伟人能力 — 特米斯托克力（`GREAT_PERSON_INDIVIDUAL_THEMISTOCLES`）

---

### EFFECT_ADJUST_CITY_POPULATION_UNIT_CREATED

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_CHANGE_POPULATION_CREATE_UNIT` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `-1` |
| `UnitType` | 是 | `UNIT_SULEIMAN_JANISSARY` |

**效果**：训练指定单位时消耗城市人口
> **溯源**：文明/领袖特性 — TRAIT_LEADER_UNIT_SULEIMAN_JANISSARY（`TRAIT_LEADER_UNIT_SULEIMAN_JANISSARY`） — 文明或领袖特性效果

---

### EFFECT_ADJUST_CITY_PRODUCTION_UNIT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CAPITAL_CITY_ADJUST_UNIT_PRODUCTION` | `COLLECTION_PLAYER_CAPITAL_CITY` |
| `MODIFIER_PLAYER_CITIES_ADJUST_UNIT_PRODUCTION_CHANGE` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_PLAYER_DISTRICTS_ADJUST_UNIT_PRODUCTION` | `COLLECTION_PLAYER_DISTRICTS` |
| `MODIFIER_PLAYER_CITIES_ADJUST_UNIT_PRODUCTION_CHANGE_ETHIOPIA` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1`、`2`、`3` |

**效果**：调整城市特定条件下的单位生产力基础产出
> **溯源**：城邦 — 军事城邦（`MINOR_CIV_MILITARISTIC`） — 城邦宗主国加成（首都/兵营/军营/军事学院等军事建筑提供）

---

### EFFECT_ADJUST_PLAYER_BAN_UNIT_PRODUCTION_YIELD

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYERS_ADJUST_UNIT_BAN_PRODUCTION_YIELD` | `COLLECTION_MAJOR_PLAYERS` |

| *(无参数)* | | |
|---|---|---|

**效果**：禁止使用特定产出类型生产单位

---

### EFFECT_ADJUST_PLAYER_BLOCK_UNIT_ENTRY

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_BLOCK_UNIT_ENTRY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `UnitType` | 是 | `UNIT_ROCK_BAND` |

**效果**：阻止指定单位类型进入己方领土
> **溯源**：政策 — 音乐审查制度（`POLICY_MUSIC_CENSORSHIP`） — 通过政策卡提供加成

---

### EFFECT_ADJUST_PLAYER_BUFF_UNIT_PRODUCTION_YIELD

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYERS_ADJUST_UNIT_BUFF_PRODUCTION_YIELD` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `-100`、`50` |

**效果**：调整使用特定产出类型生产单位时的效率
> **溯源**：世界议会决议 — "雇佣兵公司"（`WC_RES_MERCENARY_COMPANIES`） — 世界议会议案效果

---

### EFFECT_ADJUST_PLAYER_LEVIED_UNIT_UPGRADE_DISCOUNT_PERCENT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_LEVIED_UNIT_UPGRADE_DISCOUNT_PERCENT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `75` |

**效果**：降低征召单位的升级费用百分比
> **溯源**：文明/领袖特性 — 渡鸦之王（`TRAIT_LEADER_RAVEN_KING`） — 文明或领袖特性效果

---

### EFFECT_ADJUST_PLAYER_UNIT_BUILD_DISABLED

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_BUILD_DISABLED` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `UnitType` | 是 | `UNIT_SETTLER` |

**效果**：禁止建造指定单位类型
> **溯源**：政策 — 孤立主义（`POLICY_ISOLATIONISM`） — 通过政策卡提供加成

---

### EFFECT_ADJUST_PLAYER_UNIT_DISTRICT_PERCENT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_UNIT_DISTRICT_PERCENT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `20` |

**效果**：根据已建区域数量加速单位建造
> **溯源**：文明/领袖特性 — 五个太阳的传说（`TRAIT_CIVILIZATION_LEGEND_FIVE_SUNS`） — 文明或领袖特性效果

---

### EFFECT_ADJUST_PLAYER_UNIT_PROJECT_PERCENT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_UNIT_PROJECT_PERCENT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `2` |

**效果**：根据已建项目数量加速单位建造
> **溯源**：建筑 — 皇家学会（`BUILDING_GOV_SCIENCE`）

---

### EFFECT_ADJUST_PLAYER_UNIT_UPGRADE_DISCOUNT_PERCENT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_UNIT_UPGRADE_DISCOUNT_PERCENT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `100`、`50` |

**效果**：降低单位升级费用百分比
> **溯源**：文明/领袖特性 — MINOR_CIV_DEFAULT_TRAIT（`MINOR_CIV_DEFAULT_TRAIT`）
> **溯源**：政策 — 职业军队（`POLICY_PROFESSIONAL_ARMY`） — 通过政策卡提供加成
> **溯源**：政策 — 军队现代化（`POLICY_FORCE_MODERNIZATION`） — 通过政策卡提供加成

---

### EFFECT_ADJUST_PLAYER_UNIT_UPGRADE_RESOURCE_COST_DISCOUNT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_UNIT_UPGRADE_RESOURCE_COST_MODIFIER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `50` |

**效果**：降低单位升级的战略资源费用
> **溯源**：政策 — 贴身随从（`POLICY_RETINUES`） — 通过政策卡提供加成
> **溯源**：政策 — 军队现代化（`POLICY_FORCE_MODERNIZATION`） — 通过政策卡提供加成

---

### EFFECT_ADJUST_PLAYER_UNIT_WONDER_PERCENT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_UNIT_WONDER_PERCENT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `15` |

**效果**：根据奇观建造进度加速单位建造
> **溯源**：文明/领袖特性 — FIRST_EMPEROR_TRAIT（`FIRST_EMPEROR_TRAIT`）

---

### EFFECT_ADJUST_PLAYER_VALID_UNIT_BUILD

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_VALID_UNIT_BUILD` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `UnitType` | 是 | `UNIT_LAHORE_NIHANG` |

**效果**：允许建造指定的特殊单位类型
> **溯源**：城邦 — 拉合尔（`MINOR_CIV_LAHORE`） — 城邦宗主国可建造尼杭战士

---

### EFFECT_ADJUST_UNIT_DOMAIN_PRODUCTION

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_CITY_ADJUST_UNIT_DOMAIN_PRODUCTION` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `25`、`50` |
| `Domain` | 是 | `DOMAIN_SEA` |

**效果**：调整指定领域单位的生产力产出
> **溯源**：区域 — U型港（`DISTRICT_COTHON`）
> **溯源**：建筑 — 航海学校（`BUILDING_NAVIGATION_SCHOOL`）

---

### EFFECT_ADJUST_UNIT_MAINTENANCE_DISCOUNT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_UNIT_MAINTENANCE_DISCOUNT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `-2`、`1`、`2`、`5` |

**效果**：降低单位的维护费用
> **溯源**：政策 — 征兵（`POLICY_CONSCRIPTION`） — 通过政策卡提供加成
> **溯源**：政策 — 全民动员（`POLICY_LEVEE_EN_MASSE`） — 通过政策卡提供加成
> **溯源**：政策 — 精兵政策（`POLICY_ELITE_FORCES`） — 通过政策卡提供加成
> **溯源**：文明/领袖特性 — 勤俭节约（`TRAIT_LEADER_SNOWSANT`） — 文明或领袖特性效果
> **溯源**：文明/领袖特性 — 北欧卫队（`TRAIT_LEADER_HARALD_ALT`） — 文明或领袖特性效果

---

### EFFECT_ADJUST_UNIT_PRODUCTION

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_CITY_ADJUST_UNIT_PRODUCTION` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_UNITS_ADJUST_UNIT_PRODUCTION` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_CITIES_ADJUST_UNIT_PRODUCTION` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `100`、`200`、`30`、`50` |
| `UnitType` | 是 | `UNIT_BUILDER`、`UNIT_GIANT_DEATH_ROBOT`、`UNIT_MILITARY_ENGINEER`、`UNIT_NIGHTMARE_SHADOW`、`UNIT_SETTLER`、`UNIT_SPY` |

**效果**：调整特定单位类型的生产力消耗倍率
> **溯源**：文明/领袖特性 — TRAIT_CIVILIZATION_INEXPENSIVE_BUILDERS（`TRAIT_CIVILIZATION_INEXPENSIVE_BUILDERS`） — 文明或领袖特性效果
> **溯源**：文明/领袖特性 — MINOR_CIV_DEFAULT_TRAIT（`MINOR_CIV_DEFAULT_TRAIT`）
> **溯源**：政策 — 殖民（`POLICY_COLONIZATION`） — 通过政策卡提供加成
> **溯源**：政策 — 征收（`POLICY_EXPROPRIATION`） — 通过政策卡提供加成
> **溯源**：政策 — 服役（`POLICY_ILKUM`） — 通过政策卡提供加成

---

### EFFECT_ADJUST_UNIT_PURCHASE_COST

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_UNIT_PURCHASE_COST` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_EMERGENCY_CITIES_ADJUST_UNIT_PURCHASE_COST` | `COLLECTION_EMERGENCY_CITIES` |
| `MODIFIER_SINGLE_CITY_ADJUST_UNIT_PURCHASE_COST` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `100`、`20`、`30`、`50` |
| `UnitType` | 是 | `UNIT_AIRCRAFT_CARRIER`、`UNIT_AMERICAN_P51`、`UNIT_AMERICAN_ROUGH_RIDER`、`UNIT_APOSTLE`、`UNIT_ARABIAN_MAMLUK`、`UNIT_ARCHER` ... (共 146 种值) |

**效果**：调整特定单位类型的购买费用
> **溯源**：纪念活动 — COMMEMORATION_INFRASTRUCTURE（`COMMEMORATION_INFRASTRUCTURE`）
> **溯源**：政策 — 权力归花儿（`POLICY_FLOWER_POWER`） — 通过政策卡提供加成
> **溯源**：建筑 — 米纳克希神庙（`BUILDING_MEENAKSHI_TEMPLE`）
> **溯源**：文明/领袖特性 — 连击，甜品与猫猫！（`TRAIT_LEADER_MOUSSE`） — 文明或领袖特性效果


---

### EFFECT_ADJUST_UNIT_TAG_ERA_PRODUCTION

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_UNIT_TAG_ERA_PRODUCTION` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `100`、`30`、`50` |
| `EraType` | 是 | `ERA_ANCIENT`、`ERA_ATOMIC`、`ERA_CLASSICAL`、`ERA_FUTURE`、`ERA_INDUSTRIAL`、`ERA_INFORMATION` ... (共 10 种值) |
| `UnitPromotionClass` | 是 | `PROMOTION_CLASS_AIR_BOMBER`、`PROMOTION_CLASS_AIR_FIGHTER`、`PROMOTION_CLASS_ANTI_CAVALRY`、`PROMOTION_CLASS_HEAVY_CAVALRY`、`PROMOTION_CLASS_LIGHT_CAVALRY`、`PROMOTION_CLASS_MELEE` ... (共 13 种值) |

**效果**：调整指定时代/晋升类别单位的生产力消耗倍率
> **溯源**：文明/领袖特性 — TRAIT_LEADER_MELEE_COASTAL_RAIDS（`TRAIT_LEADER_MELEE_COASTAL_RAIDS`） — 文明或领袖特性效果
> **溯源**：政策 — 斯巴达教育（`POLICY_AGOGE`） — 通过政策卡提供加成
> **溯源**：政策 — 封建契约（`POLICY_FEUDAL_CONTRACT`） — 通过政策卡提供加成
> **溯源**：政策 — 大军团（`POLICY_GRANDE_ARMEE`） — 通过政策卡提供加成
> **溯源**：政策 — 先军政策（`POLICY_MILITARY_FIRST`） — 通过政策卡提供加成

---

### EFFECT_ENABLE_UNIT_FAITH_PURCHASE

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ENABLE_UNIT_FAITH_PURCHASE` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_CITY_ENABLE_UNIT_FAITH_PURCHASE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Tag` | 是 | `CLASS_AIR_FIGHTER`、`CLASS_ANTI_CAVALRY`、`CLASS_ARCHAEOLOGIST`、`CLASS_GIANT_DEATH_ROBOT`、`CLASS_HEAVY_CAVALRY`、`CLASS_HEAVY_CHARIOT` ... (共 20 种值) |

**效果**：允许使用信仰购买指定类别的单位
> **溯源**：文明/领袖特性 — 三界的崇高女神（`TRAIT_LEADER_EXALTED_GODDESS`） — 文明或领袖特性效果
> **溯源**：建筑 — 骑士团长礼拜堂（`BUILDING_GOV_FAITH`）

---

### EFFECT_GRANT_CITY_YIELD_PERCENT_UNIT_CREATED_COST

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_CITY_GRANT_YIELD_PER_UNIT_COST` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_CITIES_GRANT_YIELD_PER_UNIT_COST` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `UnitProductionPercent` | 是 | `20`、`25` |
| `YieldType` | 是 | `YIELD_CULTURE`、`YIELD_SCIENCE` |

**效果**：训练单位时按生产力消耗百分比获得额外产出
> **溯源**：建筑 — 皇家学堂（`BUILDING_BASILIKOI_PAIDES`）
> **溯源**：文明/领袖特性 — 厄勃隆尼斯之王（`TRAIT_LEADER_AMBIORIX`） — 文明或领袖特性效果

---

### EFFECT_GRANT_PLAYER_YIELD_PERCENT_UNIT_COST

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GRANT_YIELD_PERCENT_UNIT_COST` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `UnitCostPercent` | 是 | `50` |
| `YieldType` | 是 | `YIELD_GOLD` |

**效果**：训练单位时按消耗百分比返还指定产出
> **溯源**：伟人能力 — 格雷格尔·麦克格雷格尔（`GREAT_PERSON_INDIVIDUAL_COMMANDANTE_MACGREGOR`）

---

