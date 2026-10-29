# modifier-district-building -- 区域/建筑产出/生产力/购买类 EffectType — 区域/相邻（1）

> 分册：由 [modifier-district-building.md](modifier-district-building.md) 按主题拆出；覆盖 EFFECT_ADJUST_ADJACENT_CITY_RIVER_DISTRICT_PRODUCTION、EFFECT_ADJUST_ALL_DISTRICT_PRODUCTION_MODIFIER、EFFECT_ADJUST_CITY_HOUSING_PER_DISTRICT、EFFECT_ADJUST_CITY_PRODUCTION_DISTRICT、EFFECT_ADJUST_CITY_STATE_TRADE_ROUTE_DISTRICT_YIELD、EFFECT_ADJUST_CITY_YIELD_PER_DISTRICT、EFFECT_ADJUST_DISTRICT_ADJACENT_NATURAL_WONDER_PRODUCTION、EFFECT_ADJUST_DISTRICT_AMENITY、EFFECT_ADJUST_DISTRICT_ATTACK_RANGE、EFFECT_ADJUST_DISTRICT_BASE_YIELD_CHANGE、EFFECT_ADJUST_DISTRICT_EXTRA_ENTERTAINMENT、EFFECT_ADJUST_DISTRICT_EXTRA_REGIONAL_ENTERTAINMENT、EFFECT_ADJUST_DISTRICT_EXTRA_REGIONAL_RANGE、EFFECT_ADJUST_DISTRICT_EXTRA_REGIONAL_YIELD、EFFECT_ADJUST_DISTRICT_GREAT_PERSON_POINTS、EFFECT_ADJUST_DISTRICT_HOUSING、EFFECT_ADJUST_DISTRICT_PREREQ、EFFECT_ADJUST_DISTRICT_PRODUCTION、EFFECT_ADJUST_DISTRICT_TOURISM_ADJACENCY_YIELD_MOFIFIER、EFFECT_ADJUST_DISTRICT_TOURISM_CHANGE。触发：改区域产出、相邻、旅游、住房、大人物点数时。

## 区域/相邻（1）

### EFFECT_ADJUST_ADJACENT_CITY_RIVER_DISTRICT_PRODUCTION

为毗邻河流的城市调整区域生产力（固定值加成）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_ADJACENT_RIVER_DISTRICT_PRODUCTION` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例为 `50`（+50% 生产力） |

> **溯源**：TRAIT_CIVILIZATION_PEARL_DANUBE（匈牙利--多瑙河之珠）：同上 EFFECT_ADJUST_ADJACENT_CITY_RIVER_BUILDING_PRODUCTION，共同实现匈牙利UA。

---

### EFFECT_ADJUST_ALL_DISTRICT_PRODUCTION_MODIFIER

调整城市所有区域的生产力百分比加成。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_CITY_ADJUST_DISTRICT_PRODUCTION_MODIFIER` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_CITIES_ADJUST_DISTRICT_PRODUCTION_MODIFIER` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数（百分比）。官方实例：SINGLE_CITY `15`/`25`/`100`；PLAYER_CITIES `15`/`25`/`30`/`50` |

> **溯源**：
> - BUILDING_KILWA_KISIWANI（基尔瓦基斯瓦尼）：使所在城市所有区域+15%生产力（SINGLE_CITY）；帝国范围内按宗主数量+15%~+30%（PLAYER_CITIES）。
> - TRAIT_LEADER_FOUNDER_CARTHAGE（狄多--迦太基建国者）：拥有U型港的城市建造区域时+50%生产力。
> - POLICY_VETERANCY（经验）：为军营和港口区的建筑+30%生产力（此处用于搭配）。

> **注意事项**：与 EFFECT_ADJUST_DISTRICT_PRODUCTION（固定值）的区别：此为百分比修饰，后者为固定值加成。两者的 MODIFIER 变体名称以 `_MODIFIER` 结尾。

---

### EFFECT_ADJUST_CITY_HOUSING_PER_DISTRICT

根据城市中的区域数量调整住房。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_HOUSING_PER_DISTRICT` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| _(无参数记录)_ | — | 当前数据库中该 ModifierType 无已配置的 ModifierId 实例 |

> **注意事项**：DynamicModifiers 中存在但无实际使用实例。可能是基于每个区域自动计算住房的占位效果。

---

### EFFECT_ADJUST_CITY_PRODUCTION_DISTRICT

根据文明特性调整区域生产力（固定值加成）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CAPITAL_CITY_ADJUST_DISTRICT_PRODUCTION` | `COLLECTION_PLAYER_CAPITAL_CITY` |
| `MODIFIER_PLAYER_DISTRICTS_ADJUST_DISTRICT_PRODUCTION` | `COLLECTION_PLAYER_DISTRICTS` |
| `MODIFIER_PLAYER_CITIES_ADJUST_DISTRICT_PRODUCTION_CHANGE` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_PLAYER_CITIES_ADJUST_DISTRICT_PRODUCTION_CHANGE_ETHIOPIA` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例：`1`~`3` |

> **注意事项**：与 EFFECT_ADJUST_CITY_PRODUCTION_BUILDING 配对使用，区别在于 BUILDING（建筑生产力）vs DISTRICT（区域生产力）。_ETHIOPIA 后缀版本为埃塞俄比亚专属。同样无上游溯源主体。

---

### EFFECT_ADJUST_CITY_STATE_TRADE_ROUTE_DISTRICT_YIELD

调整通往城邦的贸易路线中区域带来的额外产出。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_CITY_STATE_TRADE_ROUTE_DISTRICT_YIELD` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例：`1`、`2`、`3` |
| `YieldType` | **必写** | YIELD_CULTURE / YIELD_GOLD |

> **溯源**：TRAIT_LEADER_ELIZABETH（伊丽莎白一世--德瑞克的遗产）："通往城邦的贸易路线中，每个特色区域提供+3金币、+1文化值。"（注意：该效果可能与其他修饰叠加，实际数值为 Amount 参数）。

> **注意事项**：CollectionType 为 `COLLECTION_OWNER`（作用于单个城市），但通过叠加实现玩家整体效果。

---

### EFFECT_ADJUST_CITY_YIELD_PER_DISTRICT

城市中每个区域提供额外产出。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_PER_DISTRICT` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_CITY_ADJUST_CITY_YIELD_PER_DISTRICT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数/小数。官方实例：`1`、`2` |
| `YieldType` | **必写** | YIELD_CULTURE / YIELD_FAITH |

> **溯源**：
> - GOVERNMENT_DIGITAL_DEMOCRACY（数字化民主）：城市中每个区域提供+2文化值（PLAYER_CITIES 版，国会政体效果）。
> - GOVERNOR_PROMOTION_CARDINAL_BISHOP（大主教）：此城市每有一个区域+2信仰值（SINGLE_CITY 版）。

---

### EFFECT_ADJUST_DISTRICT_ADJACENT_NATURAL_WONDER_PRODUCTION

为毗邻自然奇观的城市调整区域生产力。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_ALL_CITIES_ADJUST_DISTRICT_ADJACENT_NATURAL_WONDER_PRODUCTION` | `COLLECTION_ALL_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数（百分比）。官方实例为 `50` |
| `FeatureType` | **必写** | FEATURE_IKKIL（伊基尔天坑，官方 GS 天然奇观）。自然奇观在游戏中以 Feature 形式存在（`FEATURE_` 前缀），官方实例中此参数必填 |

> **溯源**：GS 资料片伊基尔天坑（Ik-kil Cenote）的建造效果——所有城市毗邻伊基尔天坑时，区域建造生产力 +50%（`Amount=50`，`FeatureType=FEATURE_IKKIL`）。注意：天然奇观在游戏中均以 `FEATURE_NATURAL_WONDER` 类型或其专属 `FEATURE_*` 子类型存在，非 mod 内容。

---

### EFFECT_ADJUST_DISTRICT_AMENITY

调整区域提供的宜居度（全局宜居度）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_CITY_DISTRICTS_ADJUST_DISTRICT_AMENITY` | `COLLECTION_CITY_DISTRICTS` |
| `MODIFIER_PLAYER_DISTRICT_ADJUST_DISTRICT_AMENITY` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_DISTRICTS_ADJUST_DISTRICT_AMENITY` | `COLLECTION_PLAYER_DISTRICTS` |
| `MODIFIER_ADJUST_AMENITIES_IN_DISTRICT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例：`1`~`3`；mod 内容 `-1`~`-64` 等 |

> **溯源**：
> - DISTRICT_AQUEDUCT（水渠）/ DISTRICT_BATH（浴场）→ PLAYER_DISTRICT 版：水渠区域提供+1宜居度。
> - GOVERNOR_PROMOTION_WATER_WORKS（自来水工程）→ CITY_DISTRICTS 版：城市每个水渠和浴场+1宜居度。
> - TRAIT_LEADER_LINCOLN（林肯--解放黑奴宣言）→ PLAYER_DISTRICTS 版：工业区+2宜居度。
> - GREAT_PERSON_INDIVIDUAL_IBN_KHALDUN（伊本-赫勒敦）→ ADJUST_AMENITIES_IN_DISTRICT 版：指定区域+1宜居度。

> **注意事项**：与 EFFECT_ADJUST_DISTRICT_EXTRA_ENTERTAINMENT（本地娱乐）和 EFFECT_ADJUST_DISTRICT_EXTRA_REGIONAL_ENTERTAINMENT（区域辐射娱乐）的区别：AMENITY 为全局宜居度，后者分别为本地和区域辐射宜居度。

---

### EFFECT_ADJUST_DISTRICT_ATTACK_RANGE

调整区域对城市攻击范围的影响。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_DISTRICT_ADJUST_CITY_ATTACK_RANGE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| _(无参数记录)_ | — | 当前数据库中该 ModifierType 无已配置的 ModifierId 实例 |

> **注意事项**：DynamicModifiers 中存在但无实际使用实例。可能用于军事区域（如军营）扩展城市攻击范围。

---

### EFFECT_ADJUST_DISTRICT_BASE_YIELD_CHANGE

调整区域的基础产出值（影响区域地基产出，区别于后期加成）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISTRICT_ADJUST_BASE_YIELD_CHANGE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例：`1`~`4` |
| `YieldType` | **必写** | YIELD_CULTURE / YIELD_FAITH / YIELD_FOOD / YIELD_GOLD / YIELD_PRODUCTION / YIELD_SCIENCE |

> **溯源**：
> - DISTRICT_ROYAL_NAVY_DOCKYARD（皇家海军船坞）→ 英国特色港口，基础产出+4金币。
> - DISTRICT_MBANZA（姆班赞）→ 刚果特色区域，基础产出+2食物、+4金币。

> **与 EFFECT_ADJUST_DISTRICT_YIELD_CHANGE 的关键区别**：BASE_YIELD_CHANGE 的产出属于**相邻加成**，可被政策卡翻倍（如自然哲学、海军基建等）。DISTRICT_YIELD_CHANGE 的产出不会被翻倍。

---

### EFFECT_ADJUST_DISTRICT_EXTRA_ENTERTAINMENT

调整区域提供的额外本地宜居度（仅对区域所在城市生效）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISTRICTS_ADJUST_EXTRA_ENTERTAINMENT` | `COLLECTION_PLAYER_DISTRICTS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例：`1`~`16`；也有 `-2`（惩罚） |

> **溯源**：
> - TRAIT_CIVILIZATION_KHMER_BARAYS（高棉--大人工湖）：拥有水渠的城市改良设施提供宜居度+1。
> - TRAIT_CIVILIZATION_INDONESIA_NUSANTARA（印度尼西亚--伟大千岛之国）：邻接海岸/湖泊单元格的娱乐设施+1宜居度。
> - Mod 内容（蜜莓、苏苏洛、桃金娘、小刻画图写话等）：用于自定义文明的特殊宜居度调整。

> **注意事项**：与 EFFECT_ADJUST_DISTRICT_AMENITY 的区别：EXTRA_ENTERTAINMENT 是区域对所在城市的本地宜居度加值（影响城市本地娱乐值），而 AMENITY 是全局宜居度（影响整个帝国的宜居度计算）。与 EXTRA_REGIONAL_ENTERTAINMENT 的区别：后者影响一定范围内的其他城市。

---

### EFFECT_ADJUST_DISTRICT_EXTRA_REGIONAL_ENTERTAINMENT

调整区域提供的额外区域辐射宜居度（影响一定范围内的其他城市）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISTRICT_ADJUST_EXTRA_REGIONAL_ENTERTAINMENT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例为 `1` |

> **溯源**：GREAT_PERSON_INDIVIDUAL_JOSEPH_PAXTON（约瑟夫-帕克斯顿，大工程师）：使用后指定区域+1区域辐射宜居度（使该区域的娱乐设施向周边城市辐射额外宜居度）。

---

### EFFECT_ADJUST_DISTRICT_EXTRA_REGIONAL_RANGE

调整区域宜居度/娱乐设施的影响范围（格数）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISTRICT_ADJUST_EXTRA_REGIONAL_RANGE` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_DISTRICTS_ADJUST_EXTRA_REGIONAL_RANGE` | `COLLECTION_PLAYER_DISTRICTS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例为 `3`（即影响范围+3格） |

> **溯源**：
> - GREAT_PERSON_INDIVIDUAL_JOSEPH_PAXTON（约瑟夫-帕克斯顿）：使区域娱乐辐射范围+3。
> - GREAT_PERSON_INDIVIDUAL_NIKOLA_TESLA（尼古拉-特斯拉）：使区域影响范围+3（也用于工业区范围扩展）。

---

### EFFECT_ADJUST_DISTRICT_EXTRA_REGIONAL_YIELD

调整区域额外提供给周边城市的产出。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISTRICT_ADJUST_EXTRA_REGIONAL_YIELD` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例为 `2` |
| `YieldType` | **必写** | YIELD_PRODUCTION（官方实例） |

> **溯源**：GREAT_PERSON_INDIVIDUAL_NIKOLA_TESLA（尼古拉-特斯拉）：使指定区域向周边城市辐射+2生产力。此效果作用于特定区域，为周边一定范围内的城市提供区域产出加成。

---

### EFFECT_ADJUST_DISTRICT_GREAT_PERSON_POINTS

调整区域提供的伟人点数。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISTRICT_ADJUST_GREAT_PERSON_POINTS` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_DISTRICTS_ADJUST_GREAT_PERSON_POINTS` | `COLLECTION_PLAYER_DISTRICTS` |
| `MODIFIER_SINGLE_CITY_DISTRICTS_ADJUST_GREAT_PERSON_POINTS` | `COLLECTION_CITY_DISTRICTS` |
| `MODIFIER_ALLIANCE_DISTRICTS_ADJUST_GREAT_POINTS` | `COLLECTION_ALLIANCE_DISTRICTS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例：`1` / `2` |
| `GreatPersonClassType` | 选写 | GREAT_PERSON_CLASS_ 枚举。PLAYER_DISTRICTS 和 SINGLE_CITY_DISTRICTS 版本有此参数 |

> **溯源**：
> - BUILDING_ORACLE（神谕）→ SINGLE_CITY 版：此城市中各区域+2对应类型的伟人点数。
> - TRAIT_CIVILIZATION_BYZANTIUM（拜占庭--天授规矩）→ PLAYER_DISTRICTS 版：圣地区域+1大预言家点数。
> - ALLIANCE_DISTRICTS 版：用于同盟加成（联盟区域提供额外伟人点数）。

---

### EFFECT_ADJUST_DISTRICT_HOUSING

调整区域提供的住房值。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISTRICTS_ADJUST_HOUSING` | `COLLECTION_PLAYER_DISTRICTS` |
| `MODIFIER_CITY_DISTRICTS_ADJUST_DISTRICT_HOUSING` | `COLLECTION_CITY_DISTRICTS` |
| `MODIFIER_ADJUST_HOUSING_IN_DISTRICT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例：`2` / `3` |

> **溯源**：
> - TRAIT_LEADER_MONASTERIES_KING（阇耶跋摩七世--国王的修道院）：圣地位于河流之上时+2住房（PLAYER_DISTRICTS）。
> - GOVERNOR_PROMOTION_WATER_WORKS（自来水工程）→ CITY_DISTRICTS 版：城市每个水渠+2住房。
> - GREAT_PERSON_INDIVIDUAL_IBN_KHALDUN（伊本-赫勒敦）→ ADJUST_HOUSING_IN_DISTRICT 版：指定区域+2住房。

---

### EFFECT_ADJUST_DISTRICT_PREREQ

变更区域的科技或市政前置条件（使区域可通过不同科技/市政解锁）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_DISTRICT_UNLOCK` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `DistrictType` | **必写** | DISTRICT_ 枚举（如 DISTRICT_CANAL） |
| `TechType` | 选写 | TECH_ 枚举（如 TECH_MASONRY） |

> **溯源**：FIRST_EMPEROR_TRAIT（秦始皇--秦始皇/天命者）：该领袖特质使用此效果使运河可通过砌砖科技提前解锁（原本运河需更晚的科技）。"可以比其他文明更早地用砌砖解锁运河区域。"

> **注意事项**：TechType 可为空（仅解锁不需科技），或指定具体的科技/市政枚举。此效果改变的是区域解锁的科技/市政前置条件，不改变区域本身的其他属性。

---

### EFFECT_ADJUST_DISTRICT_PRODUCTION

调整特定区域的生产力（固定值/百分比加成）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_DISTRICT_PRODUCTION` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数（百分比/固定值，取决于上下文）。官方实例：`30`~`500` |
| `DistrictType` | **必写** | DISTRICT_ 枚举。官方实例涵盖：DISTRICT_CAMPUS / DISTRICT_COMMERCIAL_HUB / DISTRICT_DAM / DISTRICT_DIPLOMATIC_QUARTER / DISTRICT_ENCAMPMENT / DISTRICT_GOVERNMENT / DISTRICT_HARBOR / DISTRICT_HOLY_SITE 等 |

> **溯源**：
> - 城邦特质（科技/宗教/贸易/文化/军事/工业城邦）：各类城邦的宗主加成，使特定区域建造速度提升（通常 Amount=30 到 50）。
> - POLICY_VETERANCY（经验）：为军营和港口区建造+30%生产力。
> - TRAIT_LEADER_DIVINE_WIND（北条时宗--神风）：在非丘陵陆地单元格上的军营、圣地和剧院广场建造速度+50%（即和平时期1.5倍速）。
> - TRAIT_CIVILIZATION_GROTE_RIVIEREN（荷兰--大河地带）：沿河流时学院、剧院广场和工业区建造获得加成。

> **注意事项**：与 EFFECT_ADJUST_ALL_DISTRICT_PRODUCTION_MODIFIER 的区别：此效果可指定 DistrictType 针对特定区域类型加成。城邦宗主加成和领袖特质是此效果最大的实际应用场景。

---

### EFFECT_ADJUST_DISTRICT_TOURISM_ADJACENCY_YIELD_MOFIFIER

将区域的相邻加成产出按比例转化为旅游业绩（"MOFIFIER" 为 Firaxis 原始拼写错误，实为 MODIFIER）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_CITY_DISTRICTS_ADJUST_TOURISM_ADJACENCY_YIELD_MOFIFIER` | `COLLECTION_CITY_DISTRICTS` |
| `MODIFIER_PLAYER_DISTRICT_ADJUST_TOURISM_ADJACENCY_YIELD_MOFIFIER` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_DISTRICTS_ADJUST_TOURISM_ADJACENCY_YIELD_MOFIFIER` | `COLLECTION_PLAYER_DISTRICTS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数（转化百分比）。官方实例：`50` / `100`（即 50% 或 100% 的相邻加成产出转化为旅游业绩） |
| `YieldType` | **必写** | YIELD_CULTURE / YIELD_FAITH / YIELD_GOLD / YIELD_PRODUCTION / YIELD_SCIENCE |

> **溯源**：
> - TRAIT_LEADER_LUDWIG（路德维希二世--童话国王）：所有区域的 [ICON_CULTURE] 文化值相邻加成提供旅游业绩（PLAYER_DISTRICTS 版，Amount=100，完整转化）。
> - GREAT_PERSON_INDIVIDUAL_KENZO_TANGE（丹下健三）：每个城市区域的文化值/信仰值/金币/生产力/科技值相邻加成均转化为旅游业绩（CITY_DISTRICTS 版，Amount=50~100）。
> - DISTRICT_THANH（越南特色区域--城池）：该区域的文化值相邻加成转化为旅游业绩（PLAYER_DISTRICT 单区域版）。

> **注意事项**：命名中的 "MOFIFIER" 是 Firaxis 的原始拼写错误（应为 MODIFIER），在 Mod 中引用时必须使用原拼写。此效果是文化胜利策略的核心效果之一，实现"相邻加成产出 = 旅游业绩"的转化。

---

### EFFECT_ADJUST_DISTRICT_TOURISM_CHANGE

调整区域提供的旅游业绩（直接增加旅游业绩值）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISTRICT_ADJUST_TOURISM_CHANGE` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_DISTRICTS_ADJUST_TOURISM_CHANGE` | `COLLECTION_PLAYER_DISTRICTS` |
| `MODIFIER_CITY_DISTRICTS_ADJUST_TOURISM_CHANGE` | `COLLECTION_CITY_DISTRICTS` |
| `MODIFIER_EMERGENCY_DISTRICTS_ADJUST_TOURISM_CHANGE` | `COLLECTION_EMERGENCY_DISTRICTS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例：`1`~`20` |

> **溯源**：
> - BUILDING_FERRIS_WHEEL（摩天轮）/ BUILDING_SHOPPING_MALL（购物商场）/ BUILDING_STADIUM（体育场）/ BUILDING_THERMAL_BATH（温泉浴场）→ PLAYER_DISTRICT 版：特定建筑提供旅游业绩值。
> - BUILDING_AQUATICS_CENTER（水上运动中心）→ CITY_DISTRICTS 版：城市区域的旅游业绩。
> - CIVIC_CONSERVATION（保护地球）：所有区域+2旅游业绩（随全球化时代政策变化）。
> - TRAIT_CIVILIZATION_BUILDING_PRASAT（高棉--高棉庙堂）：高棉特色建筑提供旅游业绩。
> - TRAIT_LEADER_TOKUGAWA（德川家康--幕藩）：每有一个区域+1旅游业绩。
> - GREAT_PERSON_INDIVIDUAL_MASARU_IBUKA（井深大）/ JAMSETJI_TATA（贾姆希德吉-塔塔）→ 伟人效果。

> **注意事项**：与 EFFECT_ADJUST_DISTRICT_TOURISM_ADJACENCY_YIELD_MOFIFIER 的区别：此效果直接提供旅游业绩数值，而后者是将相邻加成产出按百分比转化。此效果更常用于建筑自带旅游业绩（如摩天轮、购物商场），以及文明/领袖特质的旅游业绩加成。

---

