# modifier-city — 城市（成长/住房/宜居度/忠诚度/人口）类 EffectType — 忠诚/身份

> 分册：由 [modifier-city.md](modifier-city.md) 按主题拆出；覆盖 EFFECT_ADJUST_CITY_IDENTITY_PER_TURN、EFFECT_ADJUST_CITY_IDENTITY_PRESSURE、EFFECT_ADJUST_CULTURE_BOMB_CONVERTS_CITY、EFFECT_BECOME_CITY_SUZERAIN、EFFECT_GRANT_CITY_LOYALTY、EFFECT_GRANT_CITY_ROAD_TO_CAPITAL、EFFECT_TREAT_CAPITAL_AS_HOLY_CITY、EFFECT_TREAT_HOLY_SITE_AS_HOLY_CITY。触发：改忠诚度、身份压力、文化炸弹、宗主/圣城时。

## 忠诚/身份

### EFFECT_ADJUST_CITY_IDENTITY_PER_TURN

调整每回合产生的忠诚度（直接加减值）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_CITIES_ADJUST_IDENTITY_PER_TURN` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_SINGLE_CITY_ADJUST_IDENTITY_PER_TURN` | `COLLECTION_OWNER` |
| `MODIFIER_EMERGENCY_TARGET_CITY_GRANT_LOYALTY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 每回合忠诚度值（整数，可为负）。原版示例值：`-5`、`2`、`3` |

> `MODIFIER_EMERGENCY_TARGET_CITY_GRANT_LOYALTY` 用于紧急事件中给目标城邦/城市加忠诚度。

---

### EFFECT_ADJUST_CITY_IDENTITY_PRESSURE

调整城市对外施加的忠诚度压力。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_CITIES_ADJUST_IDENTITY_PRESSURE_FROM_EMERGENCIES` | `COLLECTION_EMERGENCY_CITIES` |
| `MODIFIER_SINGLE_CITY_ADJUST_IDENTITY_PRESSURE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 忠诚度压力值（可为负）。原版示例值：`-1`（紧急事件用） |

> `MODIFIER_SINGLE_CITY_ADJUST_IDENTITY_PRESSURE` 游戏中无现成 Modifiers 条目，需自行使用。

---

### EFFECT_ADJUST_CULTURE_BOMB_CONVERTS_CITY

文化炸弹夺取格子时是否同时占领城市。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_CULTURE_BOMB_CONVERTS_CITY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `ConvertsCity` | **必写** | `1` = 文化炸弹可夺取城市。原版示例值：`1` |

---

### EFFECT_BECOME_CITY_SUZERAIN

提供足够数量的使者成为此城邦的宗主国，并移除所有其他玩家的使者。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_UNIT_BECOME_CITY_SUZERAIN` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `RemoveOthers` | **必写** | `1` / `true` = 移除所有其他玩家的使者。原版示例值：`True` |

---

### EFFECT_GRANT_CITY_LOYALTY

一次性给予城市忠诚度。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_SINGLE_CITY_GRANT_LOYALTY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 忠诚度值（整数）。原版示例值：`20` |

> 与 `EFFECT_ADJUST_CITY_IDENTITY_PER_TURN` 的区别：`_GRANT_CITY_LOYALTY` 是一次性给予，`_IDENTITY_PER_TURN` 是每回合持续生效。

---

### EFFECT_GRANT_CITY_ROAD_TO_CAPITAL

自动在城市与首都之间修建道路。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_CITIES_GRANT_ROAD_TO_CAPITAL` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| 无参数 | — | 效果由 ModifierType 自身实现 |

---

### EFFECT_TREAT_CAPITAL_AS_HOLY_CITY

将首都视为圣城。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_TREAT_CAPITAL_AS_HOLY_CITY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Value` | **必写** | `1` = 视为圣城。原版示例值：`1` |

> 只是视为圣城（有宗教压力等），并非真正的圣城。

---

### EFFECT_TREAT_HOLY_SITE_AS_HOLY_CITY

将圣地区域视为圣城。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_TREAT_HOLY_SITES_AS_HOLY_CITIES` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Value` | **必写** | `1` = 视为圣城。原版示例值：`1` |

---

