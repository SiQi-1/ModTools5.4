# modifier-misc — 其余杂项类 EffectType — 间谍/能见度

> 分册：由 [modifier-misc.md](modifier-misc.md) 按主题拆出；覆盖 间谍与外交能见度、EFFECT_ADD_DIPLO_VISIBILITY、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_SPY_SUCCESSFUL_MISSION、EFFECT_ADJUST_PLAYER_SPY_BONUS、EFFECT_ADJUST_PLAYER_STEAL_TECH_BOOSTS、EFFECT_GRANT_SPY。触发：改间谍与外交能见度时。

## 间谍与外交能见度

### EFFECT_ADD_DIPLO_VISIBILITY

增加对指定来源目标的外交能见度等级。`Source` 标记来源类型（特性/科技/商站等），`SourceType` 指定来源范围（全体或仅女性领袖）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADD_DIPLO_VISIBILITY` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` / `2` |
| `Source` | `SOURCE_GREAT_PERSON_JOURNALISM` / `SOURCE_TECH` / `SOURCE_TRADING_POST_TRAIT` / `SOURCE_TRAIT` |
| `SourceType` | `DIPLO_SOURCE_ALL_NAMES` / `DIPLO_SOURCE_FEMALE_ONLY` |

> **溯源**：TraitModifiers（成吉思汗、黑王后等）; PolicyModifiers; TechnologyModifiers（印刷术）

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_SPY_SUCCESSFUL_MISSION

每次间谍成功执行任务时获得时代得分。`Amount=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PLAYER_ERA_SCORE_PER_SPY_SUCCESSFUL_MISSION` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` |

> **溯源**：PolicyModifiers — 政策「权术政治」（POLICY_MACHIAVELLIANISM）

---

### EFFECT_ADJUST_PLAYER_SPY_BONUS

调整间谍任务的成功率/效率加成。`Offense=1`=进攻任务，`Offense=0`=防御/反间谍。`Amount=1/2/3` 为等级加成。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_SPY_BONUS` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` / `2` / `3` |
| `Offense` | `0` / `1` / `false` |

> **溯源**：TraitModifiers（黑王后、法国等）; PolicyModifiers; GovernorPromotionModifiers（语言学家等）

---

### EFFECT_ADJUST_PLAYER_STEAL_TECH_BOOSTS

允许间谍窃取科技时额外获得尤里卡。`Amount=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_STEAL_TECH_BOOSTS` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` |

> **溯源**：PolicyModifiers — 政策「核间谍」（POLICY_NUCLEAR_ESPIONAGE）

---

### EFFECT_GRANT_SPY

免费获得一个间谍单位（间谍容量+1）。`Amount=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GRANT_SPY` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` |

> **溯源**：TraitModifiers（黑王后凯瑟琳等）; CivicModifiers（民族主义、意识形态等市政）

---


