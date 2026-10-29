# modifier-city — 城市（成长/住房/宜居度/忠诚度/人口）类 EffectType — 城防/战斗

> 分册：由 [modifier-city.md](modifier-city.md) 按主题拆出；覆盖 EFFECT_ADJUST_CITY_AIR_DEFENSE_BONUS、EFFECT_ADJUST_CITY_ATTACKS_PER_TURN、EFFECT_ADJUST_CITY_COMBAT_BONUS、EFFECT_ADJUST_CITY_FRIENDLY_COMBAT_BONUS、EFFECT_ADJUST_CITY_HIT_POINTS、EFFECT_ADJUST_CITY_INNER_DEFENSE、EFFECT_ADJUST_CITY_OUTER_DEFENSE、EFFECT_ADJUST_CITY_PREVENT_BYPASS_OUTER_DEFENSES、EFFECT_ADJUST_CITY_PREVENT_MELEE_ATTACK_OUTER_DEFENSES、EFFECT_ADJUST_CITY_RANGED_STRIKE、EFFECT_ADJUST_CITY_SIEGE_PROTECTION、EFFECT_ADJUST_CITY_SPY_BONUS。触发：改城防、战斗、间谍、进攻防御时。

## 城防/战斗

### EFFECT_ADJUST_CITY_AIR_DEFENSE_BONUS

调整城市对空防御力（防空值）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_CITY_ADJUST_AIR_DEFENSE_BONUS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 防空值（整数）。原版示例值：`25` |

---

### EFFECT_ADJUST_CITY_ATTACKS_PER_TURN

调整城市每回合攻击次数。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_CITY_ADJUST_ATTACKS_PER_TURN` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 攻击次数（整数）。原版示例值：`1` |

---

### EFFECT_ADJUST_CITY_COMBAT_BONUS

调整城市战斗力（远程攻击伤害加成）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_CITY_ADJUST_CITY_COMBAT_BONUS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 战斗力加成值（整数）。原版示例值：`5` |

---

### EFFECT_ADJUST_CITY_FRIENDLY_COMBAT_BONUS

调整城市对友方单位的战斗支援加成（友军在城市领土内的战斗力）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_CITY_ADJUST_CITY_FRIENDLY_COMBAT_BONUS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 战斗力加成值（整数）。原版示例值：`5` |

> 完整规则（三种 Context、占位符 `{1_Amount}` / `{Property}`、工具生成链路）见 [modifier-techniques.md 技巧 3](techniques.md)。

---

### EFFECT_ADJUST_CITY_HIT_POINTS

调整城市生命值上限。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_CITIES_ADJUST_CITY_HIT_POINTS` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 生命值增量（整数） |

> ⚠️ 无官方使用实例，有效性存疑。

---

### EFFECT_ADJUST_CITY_INNER_DEFENSE

调整城市内城防御值（内城防御 = 城市本体防御力，非城墙）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_CITIES_ADJUST_INNER_DEFENSE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 防御值（整数）。原版示例值：`5`、`3` |

> 内城防御 = 城市本体，外城防御 = 城墙防御力。两者独立计算，互不影响。
>

---

### EFFECT_ADJUST_CITY_OUTER_DEFENSE

调整城市外层防御值（外城防御 = 城墙耐久度/城防值）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_CITIES_ADJUST_OUTER_DEFENSE` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 城墙耐久度值（整数）。原版示例值：`5`、`6`、`10` |

> 内城防御 = 城市本体，外城防御 = 城墙防御力。两者独立计算，互不影响。
>

---

### EFFECT_ADJUST_CITY_PREVENT_BYPASS_OUTER_DEFENSES

禁止无视城墙直接攻击城市（需先破城才能攻击市中心）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_SINGLE_CITY_ADJUST_PREVENT_BYPASS_OUTER_DEFENSE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| 无参数 | — | 效果由 ModifierType 自身实现 |

---

### EFFECT_ADJUST_CITY_PREVENT_MELEE_ATTACK_OUTER_DEFENSES

禁止近战单位攻击城墙（只有远程/攻城单位可攻击城墙）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_SINGLE_CITY_ADJUST_PREVENT_MELEE_ATTACK_OUTER_DEFENSES` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| 无参数 | — | 效果由 ModifierType 自身实现 |

---

### EFFECT_ADJUST_CITY_RANGED_STRIKE

调整城市远程攻击力。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_CITIES_ADJUST_RANGED_STRIKE` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 远程攻击力值（整数）。原版示例值：`5`、`10` |

---

### EFFECT_ADJUST_CITY_SIEGE_PROTECTION

调整城市是否免疫围城（围城状态下不减回血）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_CITY_ADJUST_SIEGE_PROTECTION` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Protected` | **必写** | `1` = 免疫围城。原版示例值：`1` |

---

### EFFECT_ADJUST_CITY_SPY_BONUS

调整城市内间谍行动等级加成。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_CITY_ADJUST_SPY_BONUS` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_CITIES_ADJUST_SPY_BONUS` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 间谍等级加成（整数，对己方为防御加成，对敌方为进攻加成）。原版示例值：`1`、`3` |

---

