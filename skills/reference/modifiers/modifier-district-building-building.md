# modifier-district-building -- 区域/建筑产出/生产力/购买类 EffectType — 建筑

> 分册：由 [modifier-district-building.md](modifier-district-building.md) 按主题拆出；覆盖 EFFECT_ADD_RELIGIOUS_BUILDING、EFFECT_ADD_RELIGIOUS_BUILDING_MULTIPLIER、EFFECT_ADJUST_ACTIVE_BUILDING_PRODUCTION、EFFECT_ADJUST_ADJACENT_CITY_RIVER_BUILDING_PRODUCTION、EFFECT_ADJUST_ALL_BUILDING_PRODUCTION_MODIFIER、EFFECT_ADJUST_BUILDING_FEATURE_YIELD_CHANGE、EFFECT_ADJUST_BUILDING_HOUSING、EFFECT_ADJUST_BUILDING_PRODUCTION、EFFECT_ADJUST_BUILDING_PURCHASE_COST、EFFECT_ADJUST_BUILDING_SPREAD_CHARGES、EFFECT_ADJUST_BUILDING_YIELD_CHANGE、EFFECT_ADJUST_BUILDING_YIELD_MODIFIER、EFFECT_ADJUST_BUILDING_YIELD_MODIFIERS_FOR_DISTRICT、EFFECT_ADJUST_CITY_PRODUCTION_BUILDING、EFFECT_ADJUST_CITY_YIELD_FROM_POWERED_BUILDING、EFFECT_ADJUST_DISTRICT_BUILDING_PRODUCTION、EFFECT_ADJUST_PLAYER_AUTO_THEMED_BUILDING、EFFECT_ADJUST_PLAYER_BUILDING_FAVOR、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_AERODROME_BUILDING_CONSTRUCTED、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_CULTURE_BUILDING_CONSTRUCTED、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_INDUSTRIAL_BUILDING_CONSTRUCTED、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_SCIENCE_BUILDING_CONSTRUCTED、EFFECT_ADJUST_PLAYER_FREE_BUILDING_WHEN_SPECIALTY_DISTRICT_CONSTRUCTED、EFFECT_ADJUST_PLAYER_FREE_BUILDING_WHEN_SPECIALTY_DISTRICT_CONSTRUCTED_EXCEPT、EFFECT_ADJUST_PLAYER_VALID_BUILDING、EFFECT_ADJUST_RELIGION_BUILDING_DISCOUNT、EFFECT_ENABLE_BUILDING_FAITH_PURCHASE、EFFECT_ENABLE_SPECIFIC_BUILDING_FAITH_PURCHASE、EFFECT_GRANT_BUILDING_IN_CITY、EFFECT_GRANT_BUILDING_IN_CITY_IGNORE、EFFECT_GRANT_CHEAPEST_BUILDING_IN_CITY、EFFECT_GRANT_CITY_YIELD_PERCENT_BUILDING_CREATED_COST。触发：改建筑产出、生产、购买、授予、信仰购买时。

## 建筑

### EFFECT_ADD_RELIGIOUS_BUILDING

为宗教解锁额外的宗教建筑（大教堂、谒师所、礼拜堂、清真寺、宝塔、犹太教堂、佛寺、窣堵波、拜火神庙）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_RELIGION_ADD_RELIGIOUS_BUILDING` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `BuildingType` | **必写** | BUILDING_CATHEDRAL / BUILDING_GURDWARA / BUILDING_MEETING_HOUSE / BUILDING_MOSQUE / BUILDING_PAGODA / BUILDING_SYNAGOGUE / BUILDING_WAT / BUILDING_STUPA / BUILDING_DAR_E_MEHR 等 |

> **溯源**：所有 9 个官方实例均来自 BeliefModifiers→Beliefs（信徒信条：大教堂、谒师所、礼拜堂、清真寺、宝塔、犹太教堂、佛寺、窣堵波、拜火神庙）。此 EffectType 的唯一用途是在宗教信条（Belief）中为追随者解锁第三级宗教建筑选项。

---

### EFFECT_ADD_RELIGIOUS_BUILDING_MULTIPLIER

为宗教建筑的产出提供倍率加成（可指定产出类型和是否仅创立者有效）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADD_RELIGIOUS_BUILDING_MULTIPLIER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Founder` | 选写 | `0`=所有追随者 / `1`=仅创立者。官方实例仅用 `1` |
| `Multiplier` | **必写** | 整数。倍率值，官方实例为 `10`（即 +10%） |
| `YieldType` | **必写** | YIELD_CULTURE / YIELD_FAITH / YIELD_SCIENCE 等 |

> **溯源**：TRAIT_LEADER_RIGHTEOUSNESS_OF_FAITH（萨拉丁--正义的信仰）："阿拉伯可使用平时信仰值的 1/10 购买宗教的祭祀建筑。此种祭祀建筑为拥有它的城市带来科技值、信仰值、文化值+10%。" 此效果用于领袖特质中，使宗教建筑产出获得额外百分比加成。

---

### EFFECT_ADJUST_ACTIVE_BUILDING_PRODUCTION

根据城市当前正在建造的建筑类型调整生产力。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_CITY_ADJUST_ACTIVE_BUILDING_PRODUCTION` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| _(无参数记录)_ | — | 当前数据库中该 ModifierType 无已配置的 ModifierId 实例 |

> **注意事项**：DynamicModifiers 中存在但无实际 Modifiers 实例，属于预留但未使用的 EffectType。

---

### EFFECT_ADJUST_ADJACENT_CITY_RIVER_BUILDING_PRODUCTION

为毗邻河流的城市调整建筑生产力（固定值加成）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_ADJACENT_RIVER_BUILDING_PRODUCTION` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例为 `50`（+50% 生产力） |

> **溯源**：TRAIT_CIVILIZATION_PEARL_DANUBE（匈牙利--多瑙河之珠）："与河流相邻的城市建造区域和建筑时+50%生产力。" 此效果与 EFFECT_ADJUST_ADJACENT_CITY_RIVER_DISTRICT_PRODUCTION 配对使用，共同实现匈牙利UA中沿河城市的生产力加成。两者参数结构完全相同（均为 Amount=50）。

---

### EFFECT_ADJUST_ALL_BUILDING_PRODUCTION_MODIFIER

调整城市所有建筑的生产力百分比加成（可限定是否仅作用于奇观）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_CITY_ADJUST_BUILDING_PRODUCTION_MODIFIER` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_CITIES_ADJUST_BUILDING_PRODUCTION_MODIFIER` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数（百分比）。官方实例：`-30` / `15` / `25` |
| `IsWonder` | 选写 | `0`=不限 / `1`=仅奇观。仅 PLAYER_CITIES 版本有此参数 |

> **溯源**：
> - BUILDING_KILWA_KISIWANI（基尔瓦基斯瓦尼）：对 SINGLE_CITY 版本，使所在城市所有建筑+15%生产力（含奇观）。对 PLAYER_CITIES 版本，根据城邦宗主数量提供帝国范围内+15%至+25%建筑生产力。
> - TRAIT_CIVILIZATION_MALI_GOLD_DESERT（马里--杰利之歌）：使用 Amount=-30，使马里建造建筑时-30%生产力（惩罚）。

> **注意事项**：SINGLE_CITY 版本无 `IsWonder` 参数（全局作用于所有建筑）；PLAYER_CITIES 版本通过 `IsWonder=0` 限定非奇观建筑。

---

### EFFECT_ADJUST_BUILDING_FEATURE_YIELD_CHANGE

根据建筑所在地貌类型调整建筑的产出（固定值）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_BUILDING_FEATURE_YIELD_CHANGE` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例为 `1` |
| `FeatureType` | 选写 | FEATURE_FOREST / FEATURE_JUNGLE / FEATURE_MARSH |
| `YieldType` | **必写** | YIELD_CULTURE / YIELD_PRODUCTION / YIELD_SCIENCE |

> **溯源**：TRAIT_CIVILIZATION_VIETNAM（越南--九龙江三角洲）："越南陆地特色区域只能建造在雨林、树林、沼泽单元格上。建造在这些地貌上的建筑将获得额外收益：" -- 树林+1文化值、雨林+1科技值、沼泽+1生产力。此效果根据建筑所在地貌为建筑产出附加额外收益，用法独特，需要结合地貌条件使用。

---

### EFFECT_ADJUST_BUILDING_HOUSING

调整建筑提供的住房值（固定值）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_CITY_ADJUST_BUILDING_HOUSING` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_CITIES_ADJUST_BUILDING_HOUSING` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_CITY_OWNER_ADJUST_BUILDING_HOUSING` | `COLLECTION_OWNER_CITY` |
| `MODIFIER_PLAYER_CAPITAL_CITY_ADJUST_BUILDING_HOUSING` | `COLLECTION_PLAYER_CAPITAL_CITY` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例：`1`~`10` |

> **溯源**：
> - BUILDING_LIGHTHOUSE（灯塔）→ `CITY_OWNER` 版：拥有灯塔的城市建筑+2住房。
> - TRAIT_LEADER_KUPES_VOYAGE（库佩--库佩的航行）→ `PLAYER_CAPITAL_CITY` 版：首都建造建筑后+3住房。
> - BUILDING_ANGKOR_WAT（吴哥窟）→ `PLAYER_CITIES` 版：所有城市建筑+1住房。

> **注意事项**：四个 ModifierType 的作用范围不同：SINGLE_CITY 作用于单城，CITY_OWNER 作用于建筑所在城市的拥有者，PLAYER_CITIES 作用于所有城市，PLAYER_CAPITAL_CITY 仅作用于首都。

---

### EFFECT_ADJUST_BUILDING_PRODUCTION

调整特定建筑或指定区域内建筑的建造生产力（固定值）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_ALL_CITIES_ADJUST_BUILDING_PRODUCTION` | `COLLECTION_ALL_CITIES` |
| `MODIFIER_SINGLE_CITY_ADJUST_BUILDING_PRODUCTION` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_CITIES_ADJUST_BUILDING_PRODUCTION` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数（百分比）。官方实例：`20`~`200` |
| `BuildingType` | 选写 | BUILDING_ 枚举。SINGLE_CITY 和 PLAYER_CITIES 版本有此参数；ALL_CITIES 版本无 |
| `DistrictType` | 选写 | DISTRICT_ 枚举。仅 PLAYER_CITIES 版本有此参数 |

> **溯源**：
> - POLICY_LIMES（边界）：为防御建筑+100%生产力（ALL_CITIES，无 BuildingType/DistrictType 参数，可能通过条件限制）。
> - POLICY_VETERANCY（经验）：为军营和港口区的建筑+30%生产力。
> - TRAIT_CIVILIZATION_GOLDEN_AGE_QUESTS（格鲁吉亚--团结就是力量）：黄金时代建造城墙类建筑+50%生产力。
> - TRAIT_CIVILIZATION_GROTE_RIVIEREN（荷兰--大河地带）：沿河时建造学院、剧院广场、工业区建筑获得加成。
> - TRAIT_CIVILIZATION_INDUSTRIAL_REVOLUTION（英国--世界工厂）：建造工业区建筑+20%生产力。
> - TRAIT_LEADER_SHANA_MUI_MANN（夏娜-穆伊曼--结构加固）：建造城墙建筑+100%生产力。

> **注意事项**：与 EFFECT_ADJUST_ALL_BUILDING_PRODUCTION_MODIFIER（百分比修饰）的区别：此效果用于指定特定建筑类型（BuildingType）或特定区域（DistrictType）内的建筑加成。参数 BuildingType 和 DistrictType 均支持单个值，不支持逗号分隔多个值，但可通过多个 ModifierId 分别指定。

---

### EFFECT_ADJUST_BUILDING_PURCHASE_COST

调整特定建筑的购买费用。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_BUILDING_PURCHASE_COST` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数（百分比）。官方实例为 `50`（即 50% 费用） |
| `BuildingType` | **必写** | BUILDING_ 枚举。官方实例：BUILDING_WALLS / BUILDING_CASTLE / BUILDING_STAR_FORT |

> **溯源**：城邦瓦莱塔宗主加成（`MINOR_CIV_VALLETTA`）——所有城市可用信仰购买市中心建筑和城墙建筑，费用 -50%（`Amount=-50`，`BuildingType=BUILDING_WALLS / BUILDING_CASTLE / BUILDING_STAR_FORT`）。此效果瓦莱塔专属，使城墙建筑信仰购买半价。

---

### EFFECT_ADJUST_BUILDING_SPREAD_CHARGES

调整宗教单位的传教次数。虽然 EffectType 名称含 "BUILDING"，但实际作用于宗教单位的传教/传播能力。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_CITY_RELIGIOUS_SPREADS` | `COLLECTION_CITY_TRAINED_UNITS` |
| `MODIFIER_PLAYER_UNITS_RELIGIOUS_SPREADS` | `COLLECTION_PLAYER_UNITS` |
| `MODIFIER_SINGLE_UNIT_RELIGIOUS_SPREADS` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_TRAINED_UNITS_ADJUST_RELIGIOUS_CHARGES` | `COLLECTION_PLAYER_TRAINED_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。表示传教次数增量。官方实例：`1` / `2` |

> **溯源**：
> - BUILDING_MOSQUE（清真寺）→ SINGLE_CITY_RELIGIOUS_SPREADS：在此城市训练的宗教单位+1传教次数。
> - TRAIT_CIVILIZATION_DHARMA（印度--达摩）：所有宗教单位+2传教次数（PLAYER_UNITS）。
> - ABILITY_QIN_MELEE_UNITS（三十六计）→ SINGLE_UNIT：指定单位+1传教次数。

> **注意事项**：四个 ModifierType 的作用维度不同。SINGLE_CITY 对城市内训练的单位生效，PLAYER_UNITS 对所有已有单位生效，SINGLE_UNIT 对指定单位生效，PLAYER_TRAINED_UNITS 对未来训练的单位生效。名称中的 "BUILDING" 指代的是建筑解锁的宗教单位能力。

---

### EFFECT_ADJUST_BUILDING_YIELD_CHANGE

调整特定建筑的产出值（固定值增量）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_BUILDING_YIELD_CHANGE` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_CITIES_ADJUST_BUILDING_YIELD_CHANGE` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例：`1`~`6` |
| `BuildingType` | **必写** | BUILDING_ 枚举 |
| `YieldType` | **必写** | YIELD_CULTURE / YIELD_FAITH / YIELD_FOOD / YIELD_GOLD / YIELD_PRODUCTION / YIELD_SCIENCE |
| `CityStatesOnly` | 选写 | `0`=否 / `1`=是。仅 PLAYER_CITIES 版本有此参数 |

> **溯源**：
> - BUILDING_ELECTRONICS_FACTORY / BUILDING_TSIKHE → MODIFIER_BUILDING_YIELD_CHANGE：建筑自身产出的固定加成。
> - GOVERNOR_PROMOTION_RESOURCE_MANAGER_INDUSTRIALIST（实业家）、GOVERNOR_PROMOTION_MERCHANT_RENEWABLE_ENERGY（再生资源补贴）→ 总督能力固定产出提升。
> - GREAT_PERSON 系列（列奥纳多·达·芬奇、詹姆斯·瓦特、希帕蒂娅、艾萨克·牛顿、阿尔伯特·爱因斯坦）→ 伟人使用效果为指定建筑+产出。
> - POLICY_THIRD_ALTERNATIVE（第三选择）→ 每座研究实验室、军事学院和发电厂+4金币。
> - POLICY_MILITARY_RESEARCH（军事研究）→ 军事学院和马厩+1科技值。
> - TRAIT_CIVILIZATION_DISTRICT_IKANDA（祖鲁）→ 军营区特有建筑产出。
> - TRAIT_LEADER_SUSSURRO（深度治疗）→ 建筑产出随生命值恢复增长。

> **注意事项**：MODIFIER_BUILDING_YIELD_CHANGE 作用于单个建筑自身（COLLECTION_OWNER），而 MODIFIER_PLAYER_CITIES_ADJUST_BUILDING_YIELD_CHANGE 作用于玩家所有城市。后者多了 `CityStatesOnly` 参数，用于限制仅城邦有效。

---

### EFFECT_ADJUST_BUILDING_YIELD_MODIFIER

调整特定建筑的产出百分比加成。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_BUILDING_YIELD_MODIFIER` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数（百分比）。官方实例为 `100`（即 +100%，双倍） |
| `BuildingType` | **必写** | BUILDING_ 枚举。实例：BUILDING_MONUMENT / BUILDING_SHRINE / BUILDING_TEMPLE |
| `YieldType` | **必写** | YIELD_ 枚举 |

> **溯源**：TRAIT_CIVILIZATION_DOUBLE_CULTURE_BUILDINGS（双倍文化建筑）：文化类建筑（纪念碑、神社、寺庙）的文化值产出+100%。此效果直接翻倍特定建筑的产出，而非像 EFFECT_ADJUST_BUILDING_YIELD_MODIFIERS_FOR_DISTRICT 那样作用于区域级别。

---

### EFFECT_ADJUST_BUILDING_YIELD_MODIFIERS_FOR_DISTRICT

调整指定区域内所有建筑的产出百分比加成。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_BUILDING_YIELD_MODIFIERS_FOR_DISTRICT` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数（百分比）。官方实例为 `50`（即 +50%） |
| `DistrictType` | **必写** | DISTRICT_CAMPUS / DISTRICT_COMMERCIAL_HUB / DISTRICT_HOLY_SITE / DISTRICT_THEATER |
| `YieldType` | **必写** | YIELD_ 枚举 |

> **溯源**：
> - POLICY_FREE_MARKET（自由市场）：商业中心区建筑金币产出+100%。
> - POLICY_GRAND_OPERA（大歌剧）：剧院广场区建筑文化值产出+100%。
> - POLICY_RATIONALISM（理性主义）：学院区建筑科技值产出+100%。
> - POLICY_SIMULTANEUM（共享教堂）：圣地区建筑信仰值产出+100%。

> **注意事项**：此效果与 EFFECT_ADJUST_BUILDING_YIELD_MODIFIER 的区别在于作用粒度：前者针对单一建筑类型，后者针对整个区域内的所有建筑。对于政策卡翻倍区域建筑产出的场景，应使用此效果。

---

### EFFECT_ADJUST_CITY_PRODUCTION_BUILDING

根据文明特性调整建筑生产力（固定值加成，具体逻辑取决于具体 ModifierType 实现）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CAPITAL_CITY_ADJUST_BUILDING_PRODUCTION` | `COLLECTION_PLAYER_CAPITAL_CITY` |
| `MODIFIER_PLAYER_DISTRICTS_ADJUST_BUILDING_PRODUCTION` | `COLLECTION_PLAYER_DISTRICTS` |
| `MODIFIER_PLAYER_CITIES_ADJUST_BUILDING_PRODUCTION_CHANGE` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_PLAYER_CITIES_ADJUST_BUILDING_PRODUCTION_CHANGE_ETHIOPIA` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例：`1`~`3` |

> **注意事项**：名称中的 "CHANGE" 而非 "MODIFIER" 表示此效果为固定值（非百分比）加成。_ETHIOPIA 后缀版本为埃塞俄比亚专属实现。所有变体均无上游溯源主体（直接内置于文明 DLL 中）。该效果与 EFFECT_ADJUST_CITY_PRODUCTION_DISTRICT 配对使用，多个 ModifierType 分别作用于首都/区域/城市/文明专属维度。

---

### EFFECT_ADJUST_CITY_YIELD_FROM_POWERED_BUILDING

调整已通电建筑（Power Plant 等提供电力的建筑）提供的额外产出。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_YIELD_FROM_POWERED_BUILDINGS` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例为 `4` |
| `YieldType` | **必写** | YIELD_CULTURE / YIELD_FOOD / YIELD_GOLD / YIELD_PRODUCTION / YIELD_SCIENCE |

> **溯源**：TRAIT_CIVILIZATION_INDUSTRIAL_REVOLUTION（英国--世界工厂）："拥有通电建筑时，建筑提供额外+4全部产出。" 此效果用于在建筑通电后额外提升产出，适用于发电厂、工厂等通电建筑。

---

### EFFECT_ADJUST_DISTRICT_BUILDING_PRODUCTION

调整区域内所有建筑的生产力（全局加成）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_ALL_CITIES_ADJUST_DISTRICT_BUILDING_PRODUCTION` | `COLLECTION_ALL_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数（百分比）。官方实例为 `100` |

> **注意事项**：无上游溯源主体。此效果为全局加成（COLLECTION_ALL_CITIES），对所有城市的区域建筑生效，区别于 EFFECT_ADJUST_BUILDING_PRODUCTION（可指定特定建筑或区域）。

---

### EFFECT_ADJUST_PLAYER_AUTO_THEMED_BUILDING

使特定建筑（如考古博物馆）自动完成主题化（无需手动搭配巨作）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_AUTO_THEMED_BUILDING` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `BuildingType` | **必写** | BUILDING_ 枚举。官方实例：BUILDING_MUSEUM_ARTIFACT（考古博物馆） |

> **溯源**：TRAIT_CIVILIZATION_DOUBLE_ARCHAEOLOGY_SLOTS（英国--大英博物馆）："每个考古博物馆可保存6个文物而非3个。建造后可供当前所有考古学家调用。当6个文物填满后，考古博物馆自动主题化。" 此效果使英国UA中的考古博物馆填满6个文物后自动完成主题化，获得主题化加成。

---

### EFFECT_ADJUST_PLAYER_BUILDING_FAVOR

调整建筑提供的外交支持。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_BUILDING_FAVOR` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `BuildingType` | **必写** | BUILDING_BROADCAST_CENTER（官方实例为广播中心） |
| `Favor` | **必写** | 整数。官方实例为 `3` |

> **溯源**：POLICY_DISINFORMATION_CAMPAIGN（抹黑行动）："每拥有1个广播中心，每回合获得外交支持+3。" 此效果的参数名为 Favor 而非 Amount。

> **注意事项**：参数名为 `Favor` 而非 `Amount`，填写时需注意参数名的差异。

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_AERODROME_BUILDING_CONSTRUCTED

每建造一个航空港区域建筑时获得时代得分。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PLAYER_ERA_SCORE_PER_AERODROME_BUILDING_CONSTRUCTED` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例为 `1` |

> **溯源**：纪念时刻系统（`COMMEMORATION_AERONAUTICAL` 等）——黄金时代/普通时代期间，每建造一个航空港建筑 +1 时代得分（`Amount=1`）。与同系列其他 4 个 EffectType 均为纪念时刻系统的时代得分奖励效果，参数结构完全相同（仅 Amount），差异仅在命名上限制生效的建筑类型范围。

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_CULTURE_BUILDING_CONSTRUCTED

每建造一个文化区建筑时获得时代得分。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PLAYER_ERA_SCORE_PER_CULTURE_BUILDING_CONSTRUCTED` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例为 `1` |

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_INDUSTRIAL_BUILDING_CONSTRUCTED

每建造一个工业区建筑时获得时代得分。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PLAYER_ERA_SCORE_PER_INDUSTRIAL_BUILDING_CONSTRUCTED` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例为 `1` |

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_SCIENCE_BUILDING_CONSTRUCTED

每建造一个学院区建筑时获得时代得分。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PLAYER_ERA_SCORE_PER_SCIENCE_BUILDING_CONSTRUCTED` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例为 `1` |

---

### EFFECT_ADJUST_PLAYER_FREE_BUILDING_WHEN_SPECIALTY_DISTRICT_CONSTRUCTED

首次建造每种专业区域时，在该区域中免费赠送最低生产力的建筑（汉谟拉比UA核心效果）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISTRICT_ADJUST_FREE_BUILDING_WHEN_SPECIALTY_DISTRICT_CONSTRUCTED` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| _(无参数记录)_ | — | 该效果通过内置逻辑自动选择该区域中生产力最低的建筑赠送 |

> **溯源**：TRAIT_LEADER_HAMMURABI（汉谟拉比--尼鲁-伊路-辛鲁）："首次建成每一种特色区域时，获得当前可建造的、所需生产力最低的建筑。" 此效果是汉谟拉比UA的核心，配合 _EXCEPT 版本排除政府区。

---

### EFFECT_ADJUST_PLAYER_FREE_BUILDING_WHEN_SPECIALTY_DISTRICT_CONSTRUCTED_EXCEPT

首次建造每种专业区域时免费赠送最低生产力建筑，但排除指定区域类型（汉谟拉比UA配套效果）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISTRICT_ADJUST_FREE_BUILDING_WHEN_SPECIALTY_DISTRICT_CONSTRUCTED_EXCEPT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `DistrictType` | **必写** | DISTRICT_ 枚举。官方实例：DISTRICT_GOVERNMENT（政府区） |

> **溯源**：TRAIT_LEADER_HAMMURABI（汉谟拉比--尼鲁-伊路-辛鲁）：排除政府区，因为政府区本身无第一级建筑。此效果配合不含 _EXCEPT 的版本使用，确保政府区不会触发空赠送。

---

### EFFECT_ADJUST_PLAYER_VALID_BUILDING

使特定建筑对玩家可用（解锁建筑的建造权限）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_VALID_BUILDING` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| _(无参数记录)_ | — | 当前数据库中该 ModifierType 无已配置的 ModifierId 实例 |

> **注意事项**：DynamicModifiers 中存在但无实际使用实例。此效果可能用于"使某文明可以使用原本无法建造的建筑"场景（如让非宗教文明使用宗教建筑）。

---

### EFFECT_ADJUST_RELIGION_BUILDING_DISCOUNT

调整宗教建筑的信仰购买折扣。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_RELIGION_BUILDING_DISCOUNT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Discount` | **必写** | 整数（百分比折扣）。官方实例为 `90`（即 90% 折扣 = 仅花费 10% 信仰值） |

> **溯源**：TRAIT_LEADER_RIGHTEOUSNESS_OF_FAITH（萨拉丁--正义的信仰）："阿拉伯可使用平时信仰值的 1/10 购买宗教的祭祀建筑。" 此效果实现萨拉丁UA中宗教建筑购买享有 90% 折扣（即 1/10 价格）。

> **注意事项**：参数名为 `Discount` 而非 `Amount`，填写时需注意。与 EFFECT_ADD_RELIGIOUS_BUILDING_MULTIPLIER 同为萨拉丁UA的一部分（前者提供产出加成，此效果提供购买折扣）。

---

### EFFECT_ENABLE_BUILDING_FAITH_PURCHASE

允许用信仰购买指定区域内的建筑。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_CITY_ENABLE_BUILDING_FAITH_PURCHASE` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_CITIES_ENABLE_BUILDING_FAITH_PURCHASE` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `DistrictType` | **必写** | DISTRICT_ 枚举 |

> **溯源**：
> - CITY_ENABLE 版：学院区和剧院广场区（无上游主体，可能为特定建筑/奇迹效果）。
> - PLAYER_CITIES 版：TRAIT_CIVILIZATION_MALI_GOLD_DESERT（马里--杰利之歌）：允许使用信仰值购买商业中心建筑。TRAIT_CIVILIZATION_ROSE_SALT（瑰盐--好生活）：允许使用信仰值购买市中心、商业中心、军营等区域建筑（mod内容）。

> **注意事项**：此效果仅开启信仰购买权限，不改变价格。若需改变信仰购买价格，需配合其他效果（如 EFFECT_ADJUST_BUILDING_PURCHASE_COST）。

---

### EFFECT_ENABLE_SPECIFIC_BUILDING_FAITH_PURCHASE

允许用信仰购买指定的单个建筑（而非整个区域类型下的所有建筑）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ENABLE_SPECIFIC_BUILDING_FAITH_PURCHASE` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `BuildingType` | **必写** | BUILDING_ 枚举。官方实例：BUILDING_MUSEUM_ARTIFACT（考古博物馆） |

> **溯源**：TRAIT_CIVILIZATION_ETHIOPIA（埃塞俄比亚--阿克苏姆的遗产）：允许用信仰值购买考古博物馆。

> **注意事项**：与 EFFECT_ENABLE_BUILDING_FAITH_PURCHASE 的区别：前者按区域类型（DistrictType）解锁区域内所有建筑的信仰购买，后者按具体建筑类型（BuildingType）解锁单个建筑。粒度不同。

---

### EFFECT_GRANT_BUILDING_IN_CITY

在城市中免费赠送建筑（需满足前置条件，如必须先有一级建筑才能送二级）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_CITY_GRANT_BUILDING_IN_CITY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| _(无参数记录)_ | — | 当前数据库中该 ModifierType 无已配置的 ModifierId 实例 |

> **注意事项**：DynamicModifiers 中存在但无实际使用实例。与 IGNORE 版本的区别：此版本需要满足建筑前置条件（如必须先有图书馆才能送大学），而 IGNORE 版本可跳过前置条件。

---

### EFFECT_GRANT_BUILDING_IN_CITY_IGNORE

在城市中免费赠送建筑（无视前置条件，可直接赠送高级建筑）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_CITY_GRANT_BUILDING_IN_CITY_IGNORE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `BuildingType` | **必写** | BUILDING_ 枚举。官方实例涵盖：BUILDING_BANK / BUILDING_CASTLE / BUILDING_FACTORY / BUILDING_LIBRARY / BUILDING_LIGHTHOUSE / BUILDING_MARKET / BUILDING_SHIPYARD / BUILDING_UNIVERSITY 等 |

> **溯源**：多位大工程师（圣乔治-詹姆斯、詹姆斯-瓦特、乔凡尼-德-美第奇、希帕蒂娅、艾萨克-牛顿、霍雷肖-纳尔逊）的伟人使用效果均使用此 EffectType，在城市中直接赠送一座无视前置条件的建筑。

> **注意事项**：与不含 IGNORE 的版本相比，此效果可以跳过建筑前置条件直接赠送。这是大工程师"赠送免费建筑"效果的标准实现方式。典型用法：牛顿赠送大学（无需图书馆前置），瓦特赠送工厂（无需工坊前置）。

---

### EFFECT_GRANT_CHEAPEST_BUILDING_IN_CITY

在城市中赠送当前可建造的最低生产力建筑。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_GRANT_CHEAPEST_BUILDING_IN_CITY` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数。官方实例为 `1`（赠送1个建筑） |

> **溯源**：
> - BUILDING_TORRE_DE_BELEM（贝伦塔）："建造后，非首都且位于另一大陆的城市将直接获得当前可建造的最低生产力建筑。" 此效果实现贝伦塔的跨大陆赠送机制。
> - TRAJANS_COLUMN_TRAIT（图拉真--图拉真圆柱）：所有新建城市获得一座免费建筑（通常是纪念碑）。

> **注意事项**：命名中的"CHEAPEST"指"生产力需求最低的建筑"而非"价格最便宜"。此效果自动计算当前科技/市政条件下该城市可建造的所需生产力最低的建筑并赠送。

---

### EFFECT_GRANT_CITY_YIELD_PERCENT_BUILDING_CREATED_COST

建造建筑时按建造费用的一定比例返还指定产出（"建筑返利"效果）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_CITY_GRANT_YIELD_PER_BUILDING_COST` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_CITIES_GRANT_YIELD_PER_BUILDING_COST` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_SINGLE_CITY_GRANT_YIELD_PER_BUILDING_COST_GRANCOLOMBIA_MAYA` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_CITIES_GRANT_YIELD_PER_BUILDING_COST_SAHARA` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `BuildingProductionPercent` | **必写** | 整数（百分比）。官方实例：`-15` / `-50` / `10` / `25` / `30` / `50` |
| `IncludeWonder` | 选写 | `0`=否 / `1`=是。是否包含奇观 |
| `YieldType` | **必写** | YIELD_CULTURE / YIELD_FAITH / YIELD_GOLD / YIELD_SCIENCE |

> **溯源**：
> - TRAIT_LEADER_RAMSES（拉美西斯二世--阿布辛贝）：建造建筑时获得等同于建造费用 15% 的文化值（BuildingProductionPercent=15，YieldType=CULTURE）。建造奇观时获得等同于建造费用 30% 的文化值（BuildingProductionPercent=30，IncludeWonder=1）。
> - GOVERNOR_PROMOTION_CARDINAL_CITADEL_OF_GOD（神之堡垒）：建造建筑时返还 25% 费用的信仰值。

> **注意事项**：参数名是 `BuildingProductionPercent` 而非 `Amount`，这是此效果的特殊之处。该参数取值为百分比值，正数表示返还，负数（如 -15、-50）表示额外花费惩罚。_SAHARA 和 _GRANCOLOMBIA_MAYA 后缀版本为特定文明/情景的专属实现。

---

