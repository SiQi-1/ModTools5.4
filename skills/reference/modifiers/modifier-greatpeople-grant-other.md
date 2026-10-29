# modifier-greatpeople — 伟人/巨作类 EffectType — 授予/其他

> 分册：由 [modifier-greatpeople.md](modifier-greatpeople.md) 按主题拆出；覆盖 EFFECT_ADD_EXPENDED_GREAT_PERSON_TILES、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_GREAT_PERSON_EARNED、EFFECT_ADJUST_PLAYER_GREATPERSON_FAVOR_MODIFIER、EFFECT_ADJUST_PLAYER_YIELD_MODIFIER_PER_EARNED_GREAT_PERSON、EFFECT_ADJUST_UNIT_GREAT_PERSON_CHARGES、EFFECT_GRANT_BOOST_WITH_GREAT_PERSON、EFFECT_GRANT_PLAYER_RELIGIOUS_PRESSURE_GREAT_PERSON_ACTIVATED、EFFECT_GRANT_PLAYER_SPECIFIC_TECH_BOOST_GREAT_PERSON。触发：改伟人相关授予、科技加速、时代得分时。

## 授予/其他

### EFFECT_ADD_EXPENDED_GREAT_PERSON_TILES

消耗任意伟人时，城市扩张指定数量的地块。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_CITIES_ADD_EXPENDED_GREAT_PERSON_TILES` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 扩张地块数（整数，例：`1`） |

> **溯源**：俄罗斯文明能力「**拉夫拉修道院**」——拥有拉夫拉修道院的城市每消耗一位伟人，城市边界扩张 1 格（`Amount=1`，SubjectRequirementSetId=`REQUIREMENTS_CITY_HAS_LAVRA`）。

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_GREAT_PERSON_EARNED

每次获得伟人时额外获得时代得分。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_PLAYER_ERA_SCORE_PER_GREAT_PERSON_EARNED` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 每获得一位伟人额外获得的时代得分（整数，例：`1`） |

> **溯源**：纪念时刻「**航空纪念**」——非黄金时代期间，每招募一位伟人 +1 时代得分（`Amount=1`，`SubjectRequirementSetId` 限定非黄金时代和允许纪念任务中）。用于鼓励追赶的文明通过招募伟人提升时代得分。

---

### EFFECT_ADJUST_PLAYER_GREATPERSON_FAVOR_MODIFIER

招募伟人时获得额外外交支持（百分比）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_GREATPERSON_FAVOR_MODIFIER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 百分比值（整数，例：`50` = +50% 外交支持产出） |

> **溯源**：瑞典文明能力「**诺贝尔奖**」——招募伟人时额外获得 +50% 外交支持（`Amount=50`）。注意这是调整外交支持产出量的百分比，而非每次招募固定获得 N 点。

---

### EFFECT_ADJUST_PLAYER_YIELD_MODIFIER_PER_EARNED_GREAT_PERSON

每招募一位伟人，获得特定产出百分比加成（累积型）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_YIELD_MODIFIER_PER_EARNED_GREAT_PERSON` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 每位伟人提供的百分比加成（整数，例：`2` = 每招募一位伟人 +2% 产出） |
| `YieldType` | **必写** | 产出类型。`YIELD_SCIENCE / CULTURE / GOLD / FAITH / PRODUCTION / FOOD`（YieldType.txt） |

> **溯源**：城邦「**安塔那那利佛**」宗主国加成——每招募一位伟人 +2% 文化产量（`Amount=2`，`YieldType=YIELD_CULTURE`）。效果为累积型：招募 N 位伟人后 = +N × Amount %。不区分伟人类型。

---

### EFFECT_ADJUST_UNIT_GREAT_PERSON_CHARGES

调整伟人单位的使用次数（充能数）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_UNITS_ADJUST_GREAT_PERSON_CHARGES` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 增加的充能数（整数，例：`1`） |

> **溯源**：奇观「**摩索拉斯王陵墓**」——大工程师 +1 使用次数（`Amount=1`，`SubjectRequirementSetId=UNIT_IS_ENGINEER` 限定仅大工程师生效）。注意此 EffectType 作用于玩家所有单位的充能，通常配合 `SubjectRequirementSetId` 限定特定伟人类型。

---

### EFFECT_GRANT_BOOST_WITH_GREAT_PERSON

招募指定类型伟人时，为所有玩家（或仅自己）提供随机科技尤里卡。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_GRANT_BOOST_WITH_GREAT_PERSON` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `GreatPersonClass` | **必写** | 伟人类型（[GreatPersonClassType.txt](../../SOURCES.md#类型与枚举)）。**注意：参数名为 `GreatPersonClass`（非 `GreatPersonClassType`）** |
| `TechBoost` | **必写** | `0` = 市政尤里卡，`1` = 科技尤里卡 |
| `OtherPlayers` | **可选** | `1` = 为所有其他玩家也提供尤里卡 |

> **溯源**：奇观「**大图书馆**」——其他玩家招募大科学家时，你获得一个随机科技尤里卡（`GreatPersonClass=GREAT_PERSON_CLASS_SCIENTIST`，`OtherPlayers=1`，`TechBoost=1`）。注意：`OtherPlayers=1` 时，效果在其他玩家招募伟人时触发，但尤里卡发放给**你自己**。

---

### EFFECT_GRANT_PLAYER_RELIGIOUS_PRESSURE_GREAT_PERSON_ACTIVATED

激活伟人时，向周围城市施加宗教压力。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_GRANT_RELIGIOUS_PRESSURE_GREAT_PERSON_ACTIVATED` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 宗教压力值（整数，例：`400`） |

> **溯源**：城邦「**梵蒂冈城**」宗主国加成——激活伟人时，向 10 格内所有城市施加 400 宗教压力（`Amount=400`）。用于宗教胜利辅助，每次激活任意伟人均触发。

---

### EFFECT_GRANT_PLAYER_SPECIFIC_TECH_BOOST_GREAT_PERSON

激活伟人时，为该玩家提供指定科技的尤里卡（Eureka），可在已有尤里卡时直接完成科技。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_GRANT_SPECIFIC_TECH_BOOST` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `TechType` | **必写** | 目标科技。`TECH_WRITING / MATHEMATICS / ENGINEERING / ROCKETRY / ...`（完整列表查数据库 Technologies 表） |
| `GrantTechIfBoosted` | **可选** | `1` = 科技已有尤里卡时直接授予该科技（跳过尤里卡，直接完成） |

> **溯源**：
> - 大科学家「**爱达·勒芙蕾丝**」——激活后获得「计算机」科技的尤里卡（`TechType=TECH_COMPUTERS`）
> - 大科学家「**毕昇**」——激活后获得「印刷术」科技的尤里卡（`TechType=TECH_PRINTING`）
> - 大科学家「**欧几里得**」——激活后获得「数学」科技的尤里卡（`TechType=TECH_MATHEMATICS`）
> - 大科学家「**罗伯特·哥达德**」——激活后获得「火箭学」科技的尤里卡（`TechType=TECH_ROCKETRY`）
> - 大科学家「**德米特里·门捷列夫**」——激活后获得「化学」科技的尤里卡（`TechType=TECH_CHEMISTRY`）
> - 大科学家「**张衡**」——激活后获得「数学」「天文导航」「工程」的尤里卡（三行参数，且 `GrantTechIfBoosted=1`：若科技已有尤里卡则直接完成科技）
> - 纪念时刻「**航空纪念**」——黄金时代时获得指定科技的尤里卡（`OwnerRequirementSetId=PLAYER_HAS_GOLDEN_AGE_*`）
> - 腓尼基文明能力「**地中海殖民地**」——获得「文字」科技的尤里卡（`TechType=TECH_WRITING`）
>
> 可多行指定多个 `TechType`（每个 `TechType` 一行参数）。若科技已完成，则跳过。与 `EFFECT_GRANT_BOOST_WITH_GREAT_PERSON` 的区别：后者发放随机尤里卡槽位，此 Effect 指定具体科技。

---

