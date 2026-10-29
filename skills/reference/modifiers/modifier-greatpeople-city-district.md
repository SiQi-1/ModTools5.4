# modifier-greatpeople — 伟人/巨作类 EffectType — 城市/区域伟人

> 分册：由 [modifier-greatpeople.md](modifier-greatpeople.md) 按主题拆出；覆盖 EFFECT_ADJUST_CITY_AMENITIES_FROM_GREAT_PEOPLE、EFFECT_ADJUST_CITY_HAPPINESS_GREAT_PERSON、EFFECT_ADJUST_CITY_HOUSING_FROM_GREAT_PEOPLE。触发：改城市/区域的伟人、住房、宜居效果时。

## 城市/区域伟人

### EFFECT_ADJUST_CITY_AMENITIES_FROM_GREAT_PEOPLE

按城市中已消耗的伟人数量提供宜居度加成。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_SINGLE_CITY_ADJUST_CITY_AMENITIES_FROM_GREAT_PEOPLE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 每消耗一位伟人提供的宜居度（整数，例：`1`、`3`） |

> **溯源**：大工程师「**约翰·罗布尔**」激活效果——该城市每消耗一位伟人 +1 宜居度（`Amount=1`）。大工程师「**简·德鲁**」激活效果——该城市每消耗一位伟人 +3 宜居度（`Amount=3`）。两位伟人均作用于当前所在城市，不区分伟人类型。

---

### EFFECT_ADJUST_CITY_HAPPINESS_GREAT_PERSON

按城市中已消耗的特定伟人类型数量，在达到指定幸福度等级后提供额外幸福度。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_CITIES_ADJUST_HAPPINESS_GREAT_PERSON` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 幸福度值（整数，例：`1`、`2`） |
| `GreatPersonClassType` | **必写** | 伟人类型。`GREAT_PERSON_CLASS_SCIENTIST / ENGINEER / ...`（[GreatPersonClassType.txt](../../SOURCES.md#类型与枚举)） |
| `HappinessType` | **必写** | 幸福度等级。`HAPPINESS_ECSTATIC / HAPPY / CONTENT / DISPLEASED / UNHAPPY`（HappinessType.txt） |

> **溯源**：苏格兰文明能力「**苏格兰启蒙运动**」——拥有学院的快乐城市每招募一位大科学家 +1 幸福度（`HappinessType=HAPPY`，`Amount=1`）；欣喜若狂时 +2（`HappinessType=ECSTATIC`，`Amount=2`）。拥有工业区的快乐城市每招募一位大工程师同理。用法：仅在该城市已达到指定 `HappinessType` 等级时，按该城市消耗的指定类型伟人数 × Amount 提供额外幸福度。

---

### EFFECT_ADJUST_CITY_HOUSING_FROM_GREAT_PEOPLE

按城市中已消耗的所有伟人数量提供住房（累积型）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_SINGLE_CITY_ADJUST_CITY_HOUSING_FROM_GREAT_PEOPLE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 每消耗一位伟人提供的住房（整数，例：`1`、`2`、`4`） |

> **溯源**：大工程师「**约翰·罗布尔**」激活效果——该城市每消耗一位伟人 +2 住房（`Amount=2`）。大工程师「**简·德鲁**」激活效果——该城市每消耗一位伟人 +4 住房（`Amount=4`）。另有未关联上游的 `GREATPERSON_CITY_HOUSING_SMALL` 提供 +1 住房。不区分伟人类型，累加所有已消耗伟人数量。

---

