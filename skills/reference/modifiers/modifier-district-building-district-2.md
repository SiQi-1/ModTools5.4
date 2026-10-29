# modifier-district-building -- 区域/建筑产出/生产力/购买类 EffectType — 区域/相邻（2）

> 分册：由 [modifier-district-building.md](modifier-district-building.md) 按主题拆出；覆盖 EFFECT_ADJUST_DISTRICT_WITHIN_ONE_HEX_ESPIONAGE_DEFENSE_BONUS、EFFECT_ADJUST_DISTRICT_YIELD_BASED_ON_ADJACENCY_BONUS、EFFECT_ADJUST_DISTRICT_YIELD_BASED_ON_APPEAL、EFFECT_ADJUST_DISTRICT_YIELD_CHANGE、EFFECT_ADJUST_DISTRICT_YIELD_MODIFIER、EFFECT_ADJUST_PLAYER_DISTRICT_AIR_SLOTS、EFFECT_ADJUST_PLAYER_DISTRICT_CREATE_YIELD、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_DISTRICT_CONSTRUCTED、EFFECT_ADJUST_PLAYER_SPECIALTY_DISTRICT_CANNOT_BE_BUILT_ADJACENT_TO_CITY、EFFECT_ADJUST_PLAYER_SPECIFIC_DISTRICT_GRANT_ENVOYS、EFFECT_ADJUST_RIVER_DISTRICT_PRODUCTION、EFFECT_ADJUST_TRADE_ROUTE_YIELD_PER_SPECIALTY_DISTRICT_FOR_DOMESTIC、EFFECT_ADJUST_TRADE_ROUTE_YIELD_PER_SPECIALTY_DISTRICT_FOR_INTERNATIONAL、EFFECT_DISTRICT_ADJACENCY、EFFECT_PLAYER_DIPLOMACY_AGENDA_DISTRICT_SPREAD。触发：改区域产出、相邻、旅游、住房、大人物点数时。

## 区域/相邻（2）

### EFFECT_ADJUST_DISTRICT_WITHIN_ONE_HEX_ESPIONAGE_DEFENSE_BONUS

为一格内有该区域的所有城市提供间谍防御加成。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_DISTRICT_ADJUST_WITHIN_ONE_HEX_ESPIONAGE_DEFENSE_BONUS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例为 `2` |

> **溯源**：DISTRICT_DIPLOMATIC_QUARTER（外交区）：外交区区域在其一格内为所有城市提供+2间谍防御等级。此效果使得外交区成为反间谍关键区域。

---

### EFFECT_ADJUST_DISTRICT_YIELD_BASED_ON_ADJACENCY_BONUS

将区域的某种相邻加成按比例复制/转化为另一种产出（核心效果：相邻加成镜像）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_ALL_DISTRICTS_ADJUST_YIELD_BASED_ON_ADJACENCY_BONUS` | `COLLECTION_ALL_DISTRICTS` |
| `MODIFIER_PLAYER_DISTRICT_ADJUST_YIELD_BASED_ON_ADJACENCY_BONUS` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_DISTRICTS_ADJUST_YIELD_BASED_ON_ADJACENCY_BONUS` | `COLLECTION_PLAYER_DISTRICTS` |
| `MODIFIER_PLAYER_DISTRICTS_ADJUST_YIELD_BASED_ON_ADJACENCY_BONUS_BUILDER` | `COLLECTION_PLAYER_DISTRICTS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `DistrictType` | 选写 | DISTRICT_ 枚举（ALL_DISTRICTS 和 BUILDER 版本无此参数） |
| `YieldTypeToGrant` | **必写** | YIELD_ 枚举。要授予的目标产出类型 |
| `YieldTypeToMirror` | **必写** | YIELD_ 枚举。要复制的源相邻加成产出类型 |

> **溯源**：
> - BELIEF_WORK_ETHIC（职业道德，信徒信条）：将区域的信仰相邻加成镜像为生产力加成（ALL_DISTRICTS 版）。"追随该宗教的城市每个信仰值相邻加成使生产力+1%。"
> - TRAIT_LEADER_MONASTERIES_KING（阇耶跋摩七世--国王的修道院）：圣地的文化相邻加成转化为食物加成。
> - TRAIT_LEADER_THEODORA（狄奥多拉--悔改）：圣地的文化值相邻加成同时提供文化值（BUILDER 版，文化→文化自身镜像）。
> - GREAT_PERSON_INDIVIDUAL_HILDEGARD_OF_BINGEN（宾根的希尔德加德）：指定区域的信仰相邻加成转化为科技值。

> **注意事项**：此效果的核心机制是"读取区域已有的相邻加成值（YieldTypeToMirror），然后等量或以一定比例转化为另一种产出（YieldTypeToGrant）"。需同时填写两个 Yield 参数。仅对有相邻加成的区域类型有效。ALL_DISTRICTS 版本（如职业道德）对所有区域生效，其余版本可指定 DistrictType 限定区域类型。

---

### EFFECT_ADJUST_DISTRICT_YIELD_BASED_ON_APPEAL

根据区域所在单元格的魅力值提供额外产出（魅力门槛机制）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISTRICTS_ADJUST_YIELD_BASED_ON_APPEAL` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Description` | 选写 | LOC_ 字符串，用于 UI 显示加成来源描述 |
| `DistrictType` | **必写** | DISTRICT_ 枚举：DISTRICT_CAMPUS / DISTRICT_COMMERCIAL_HUB / DISTRICT_HOLY_SITE / DISTRICT_THEATER |
| `RequiredAppeal` | **必写** | 整数。魅力门槛值：`0`=无要求，`2`=迷人，`4`=惊艳，`6`=叹为观止 |
| `YieldChange` | **必写** | 整数。产出变化量（注意：参数名为 YieldChange 而非 Amount） |
| `YieldType` | **必写** | YIELD_CULTURE / YIELD_FAITH / YIELD_GOLD / YIELD_SCIENCE |

> **溯源**：
> - TRAIT_CIVILIZATION_LAND_DOWN_UNDER（澳大利亚--南方大陆）：根据魅力值为学院/商业中心/圣地/剧院提供额外产出。魅力迷人（2）时+1，惊艳（4）时+3。
> - TRAIT_CIVILIZATION_NIGHTMARE（夜魔--里人格）、TRAIT_DISTRICT_WANDERERS_CLUB（罗德岛闲逛部--闲逛部）等 mod 内容。

> **注意事项**：此效果的参数名为 `YieldChange` 而非通常的 `Amount`，这是此效果的特殊之处。Description 参数用于在 UI 中动态显示"因xxx魅力获得+xxx产出"的描述文本。RequiredAppeal 为门槛值而非精确匹配值（如 RequiredAppeal=2 表示魅力>=2时生效）。

---

### EFFECT_ADJUST_DISTRICT_YIELD_CHANGE

调整区域的产出值（固定值增量）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISTRICT_ADJUST_YIELD_CHANGE` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_DISTRICTS_ADJUST_YIELD_CHANGE` | `COLLECTION_PLAYER_DISTRICTS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例：`1`~`12` |
| `YieldType` | **必写** | YIELD_CULTURE / YIELD_FAITH / YIELD_FOOD / YIELD_GOLD / YIELD_PRODUCTION / YIELD_SCIENCE |

> **溯源**：
> - TRAIT_LEADER_EXALTED_GODDESS（特丽布瓦娜--三界的崇高女神）：邻接海岸/湖泊单元格的区域+2信仰值。
> - POLICY_PUBLIC_TRANSPORT（公共交通）：社区区域取替农场时每个单元格获+50金币。

> **与 EFFECT_ADJUST_DISTRICT_BASE_YIELD_CHANGE 的区别**：CHANGE 产出不会被政策卡翻倍，BASE 产出属于相邻加成可以被翻倍。
> **与 EFFECT_ADJUST_DISTRICT_YIELD_MODIFIER 的区别**：CHANGE 为固定值，MODIFIER 为百分比。

---

### EFFECT_ADJUST_DISTRICT_YIELD_MODIFIER

调整区域的产出百分比加成。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISTRICTS_ADJUST_YIELD_MODIFIER` | `COLLECTION_PLAYER_DISTRICTS` |
| `MODIFIER_CITY_DISTRICTS_ADJUST_YIELD_MODIFIER` | `COLLECTION_CITY_DISTRICTS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数（百分比）。官方实例：`50` / `100` |
| `YieldType` | **必写** | YIELD_CULTURE / YIELD_FAITH / YIELD_GOLD / YIELD_PRODUCTION / YIELD_SCIENCE |

> **溯源**：
> - POLICY_NATURAL_PHILOSOPHY（自然哲学）：学院区相邻加成+100%（产出百分比双倍）。
> - POLICY_SCRIPTURE（经文）：圣地区相邻加成+100%。
> - POLICY_NAVAL_INFRASTRUCTURE（海军基础设施）：港口区相邻加成+100%。
> - POLICY_TOWN_CHARTERS（城镇特许状）：商业中心区相邻加成+100%。
> - POLICY_CRAFTSMEN（工匠）：工业区相邻加成+100%。
> - POLICY_AESTHETICS（美学）：剧院广场区相邻加成+100%。
> - POLICY_FIVE_YEAR_PLAN（五年计划）：学院区和工业区相邻加成+100%。
> - POLICY_ECONOMIC_UNION（经济同盟）：商业中心和港口区相邻加成+100%。
> - POLICY_SPORTS_MEDIA（体育传媒）：剧院广场区+100%，体育场+1宜居度。
> - POLICY_COLLECTIVISM（集体主义）：工业区相邻加成+100%。
> - GOVERNOR_PROMOTION_MERCHANT_HARBORMASTER（大投资商）：商业中心和港口相邻加成翻倍（CITY_DISTRICTS 版）。

> **注意事项**：此效果是游戏中大量经济/军事政策卡的核心机制，用于双倍区域的相邻加成产出。POLICY 版本的典型用法是 Amount=100（+100%，即双倍），配合特定区域类型和产出类型。CITY_DISTRICTS 版本作用于单个城市的区域。

---

### EFFECT_ADJUST_PLAYER_DISTRICT_AIR_SLOTS

调整区域提供的空军槽位数量（增加机场/机库的飞机驻扎容量）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISTRICT_GRANT_AIR_SLOTS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例为 `1`（+1个空军槽位） |

> **溯源**：
> - BUILDING_HANGAR（机库）：航空港区域+1空军槽位。
> - BUILDING_AIRPORT（机场）：航空港区域+2空军槽位。
> - GREAT_PERSON_INDIVIDUAL_MARINA_RASKOVA（玛丽娜-拉斯科娃，大科学家）：+1空军槽位。

---

### EFFECT_ADJUST_PLAYER_DISTRICT_CREATE_YIELD

在城市区域单元格上创建改良设施并产生相应产出。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISTRICT_CREATE_YIELD` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例为 `100`（百分比/固定值，取决于具体实现） |
| `DistrictType` | **必写** | DISTRICT_ 枚举。官方实例：DISTRICT_NEIGHBORHOOD（社区） |
| `ImprovementType` | 选写 | IMPROVEMENT_ 枚举。官方实例：IMPROVEMENT_FARM（农场） |
| `MustReplaceImprovement` | 选写 | `0`=否 / `1`=是。是否必须替换已有改良设施。官方实例为 `1` |
| `YieldBasedOnAppeal` | 选写 | `0`=否 / `1`=是。产出是否基于魅力值。官方实例为 `1` |
| `YieldType` | **必写** | YIELD_ 枚举 |

> **溯源**：POLICY_PUBLIC_TRANSPORT（公共交通）："社区取替农场时单元格+50金币。" 此效果在社区区域单元格上创建农场改良设施，并根据魅力值提供金币产出。

> **注意事项**：这是一个极特殊的 EffectType，参数组合非常罕见。它不仅在区域单元格上应用改良设施的产出逻辑，还提供了 MustReplaceImprovement（是否替换已有设施）和 YieldBasedOnAppeal（是否基于魅力值计算产出）等独特参数。一般用于"将区域单元格转化为可产出资源的改良设施"这类场景。

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_DISTRICT_CONSTRUCTED

每建造一个区域时获得时代得分。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PLAYER_ERA_SCORE_PER_DISTRICT_CONSTRUCTED` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例为 `1` |

---

### EFFECT_ADJUST_PLAYER_SPECIALTY_DISTRICT_CANNOT_BE_BUILT_ADJACENT_TO_CITY

禁止专业区域毗邻市中心建造（高卢UA核心限制）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_SPECIALTY_DISTRICT_CANNOT_BE_BUILT_ADJACENT_TO_CITY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| _(无参数记录)_ | — | 无参数，通过内置逻辑实现限制 |

> **溯源**：TRAIT_CIVILIZATION_GAUL（高卢--哈尔施塔特文化）："专业区域无法毗邻市中心，也无法从其他区域的相邻中获得加成。" 此效果实现高卢UA中"专业区域不能毗邻市中心"的建筑限制。

---

### EFFECT_ADJUST_PLAYER_SPECIFIC_DISTRICT_GRANT_ENVOYS

建造特定区域时获得使者（汉谟拉比UA配套效果）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISTRICT_ADJUST_SPECIFIC_DISTRICT_GRANT_ENVOYS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例为 `1` |
| `DistrictType` | **必写** | DISTRICT_ 枚举。官方实例：DISTRICT_GOVERNMENT（政府区） |

> **溯源**：TRAIT_LEADER_HAMMURABI（汉谟拉比--尼鲁-伊路-辛鲁）："首次建成非特色区域（政府区）时，获得1名使者。" 此效果与上述 FREE_BUILDING 效果共同组成汉谟拉比UA的完整实现。

---

### EFFECT_ADJUST_RIVER_DISTRICT_PRODUCTION

为沿河城市调整区域生产力（固定百分比加成）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_RIVER_DISTRICT_PRODUCTION` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数（游戏中表现为百分比加成，官方实例为 `15` = +15% 生产力）。**注意**：效果名无 `_MODIFIER` 后缀（通常 `_MODIFIER` 后缀对应百分比，无后缀对应绝对值），此为 Firaxis 命名不一致。需 DLL 验证实际为绝对值还是百分比 |

> **溯源**：TRAIT_CIVILIZATION_ITERU（埃及--古尼罗河）："区域和奇观可建在泛滥平原上，如建在河边+15%生产力。" 此效果实现埃及UA中沿河区域建造的生产力加成。效果名虽无 `_MODIFIER` 后缀，但官方描述和游戏表现为百分比加成。

---

### EFFECT_ADJUST_TRADE_ROUTE_YIELD_PER_SPECIALTY_DISTRICT_FOR_DOMESTIC

国内贸易路线中，目的城市每个专业区域为贸易路线提供额外产出。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_PER_SPECIALTY_DISTRICT_FOR_DOMESTIC` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数/小数。官方实例：`0.5` / `1` / `2` / `3` |
| `YieldType` | **必写** | YIELD_CULTURE / YIELD_GOLD / YIELD_SCIENCE |

> **溯源**：
> - TRAIT_LEADER_TOKUGAWA（德川家康--幕藩）：国内贸易路线中目的城市每有一个专业区域提供+1文化值、+2金币、+1科技值。
> - GREAT_PERSON_INDIVIDUAL_RAJA_TODAR_MAL（拉贾-托达-马尔）：国内贸易路线中每个专业区域提供额外产出。

> **注意事项**：此效果专用于国内贸易路线（DOMESTIC），Parameter Amount 支持小数值（如 0.5）。

---

### EFFECT_ADJUST_TRADE_ROUTE_YIELD_PER_SPECIALTY_DISTRICT_FOR_INTERNATIONAL

国际贸易路线中，目的城市每个专业区域为贸易路线提供额外产出。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_PER_SPECIALTY_DISTRICT_FOR_INTERNATIONAL` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例为 `3` |
| `YieldType` | **必写** | YIELD_GOLD |

> **注意事项**：专用于国际贸易路线（INTERNATIONAL），与 DOMESTIC 版本配对使用。无官方溯源实例，参数由 Effects.csv 记录。

---

### EFFECT_DISTRICT_ADJACENCY

设置区域之间的相邻加成（区域A对区域B的产出加成，基于相邻关系）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_DISTRICT_ADJACENCY` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例：`1` / `2` |
| `Description` | 选写 | LOC_ 字符串，用于 UI 显示加成来源描述 |
| `DistrictType` | **必写** | DISTRICT_ 枚举（如 DISTRICT_CAMPUS / DISTRICT_COMMERCIAL_HUB / DISTRICT_HARBOR / DISTRICT_HOLY_SITE / DISTRICT_INDUSTRIAL_ZONE / DISTRICT_THEATER / DISTRICT_WONDER） |
| `TilesRequired` | 选写 | 整数。通常为 `1`（相邻所需地块数） |
| `YieldType` | **必写** | YIELD_CULTURE / YIELD_FAITH / YIELD_GOLD / YIELD_PRODUCTION / YIELD_SCIENCE |

> **溯源**：
> - TRAIT_CIVILIZATION_ADJACENT_DISTRICTS（日本--明治维新）："所有区域与另一个区域相邻时获得与平常一样的相邻加成（而不只是+1）。" 日本UA使区域间相邻提供与标准相邻相同的加成。
> - TRAIT_LEADER_LITHUANIAN_UNION（雅德维加--立陶宛联邦）：圣地区域可从邻接的其他区域获得加成（+2信仰值、+2文化值、+4金币）。
> - TRAIT_LEADER_LUDWIG（路德维希二世--童话国王）：区域间的相邻加成（与旅游业绩转化搭配）。

> **注意事项**：此效果是核心的"区域相邻加成"机制。Description 参数用于在游戏中显示"因与其他区域相邻而获得+1xxx"的文本。与 `District_Adjacencies` 表（静态配置）不同，此效果通过 Modifier 系统动态追加相邻加成关系。

---

### EFFECT_PLAYER_DIPLOMACY_AGENDA_DISTRICT_SPREAD

外交议程：基于区域多样性的评价系统（汉谟拉比议程）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_HAMMURABI_DISTRICTS` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `SimpleModifierDescription` | 选写 | LOC_ 字符串。用于 UI 显示简化描述 |
| `StatementKey` | 选写 | LOC_ 字符串。议程语句键名 |

> **溯源**：TRAIT_AGENDA_HAMMURABI_DISTRICTS（汉谟拉比议程）：汉谟拉比的AI议程偏好——喜欢建造多种不同区域的文明，讨厌只建造少数几种区域的文明。

> **注意事项**：这是唯一使用 `COLLECTION_MAJOR_PLAYERS` 的 EffectType 在此文档中，参数为外交 UI 专用（SimpleModifierDescription 和 StatementKey）。此效果用于定义AI领袖的外交行为偏好，而非影响游戏数值。

---

