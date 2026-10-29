# modifier-unit-combat -- 单位战斗/属性/移动/经验/间谍/旅游/宗教等 EffectType — 经验/回血

> 分册：由 [modifier-unit-combat.md](modifier-unit-combat.md) 按主题拆出；覆盖 经验/等级、EFFECT_ADJUST_CITY_UNIT_MAX_LEVEL、EFFECT_ADJUST_UNIT_ATTACK_EXPERIENCE_MODIFIER、EFFECT_ADJUST_UNIT_EXPERIENCE_LEVEL、EFFECT_ADJUST_UNIT_EXPERIENCE_MODIFIER、EFFECT_ADJUST_UNIT_GRANT_EXPERIENCE、EFFECT_ADJUST_UNIT_NO_BARB_XP_LIMIT、EFFECT_ADJUST_UNIT_UPGRADE_GOODY_HUT、回血/治疗、EFFECT_ADJUST_RANDOM_EVENT_NO_UNIT_DAMAGE、EFFECT_ADJUST_UNIT_HEAL、EFFECT_ADJUST_UNIT_HEALING_MODIFIERS、EFFECT_ADJUST_UNIT_HEALING_RELIGION_MODIFIERS、EFFECT_ADJUST_UNIT_POST_COMBAT_HEAL。触发：改单位经验、等级、回血治疗时。

## 经验/等级

### EFFECT_ADJUST_CITY_UNIT_MAX_LEVEL

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_UNIT_MAX_LEVEL` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_SINGLE_CITY_ADJUST_CITY_UNIT_MAX_LEVEL` | `COLLECTION_OWNER` |

| *(无参数)* | | |
|---|---|---|

**效果**：提升城市训练单位的最大等级上限
> **溯源**：该 EffectType 仅在 DynamicModifiers 中注册，官方数据库中无实际 Modifier 使用记录

---

### EFFECT_ADJUST_UNIT_ATTACK_EXPERIENCE_MODIFIER

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_UNIT_ATTACK_EXPERIENCE_MODIFIER` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `100` |

**效果**：调整单位攻击获得的经验倍率
> **溯源**：城邦 — 喀布尔（`MINOR_CIV_KABUL`） — 城邦宗主国加成

---

### EFFECT_ADJUST_UNIT_EXPERIENCE_LEVEL

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_EXPERIENCE_LEVEL` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `2` |

**效果**：直接提升单位的经验等级
> **溯源**：单位能力 — ABILITY_UNIT_AUTO_VETERANCY（`ABILITY_UNIT_AUTO_VETERANCY`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_EXPERIENCE_MODIFIER

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_UNIT_EXPERIENCE_MODIFIER` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_UNITS_ADJUST_UNIT_EXPERIENCE_MODIFIER` | `COLLECTION_PLAYER_UNITS` |
| `MODIFIER_CITY_TRAINED_UNITS_ADJUST_XP_BONUS` | `COLLECTION_CITY_TRAINED_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `-100`、`0`、`10`、`100`、`200`、`25` ... (共 9 种值) |

**效果**：调整单位获取经验的倍率
> **溯源**：单位能力 — 军官（`ABILITY_MUSTANG`） — 赋予单位特殊能力
> **溯源**：单位能力 — ABILITY_BARRACKS_TRAINED_UNIT_XP（`ABILITY_BARRACKS_TRAINED_UNIT_XP`） — 赋予单位特殊能力
> **溯源**：单位能力 — ABILITY_STABLE_TRAINED_UNIT_XP（`ABILITY_STABLE_TRAINED_UNIT_XP`） — 赋予单位特殊能力
> **溯源**：单位能力 — ABILITY_ARMORY_TRAINED_UNIT_XP（`ABILITY_ARMORY_TRAINED_UNIT_XP`） — 赋予单位特殊能力
> **溯源**：单位能力 — ABILITY_MILITARY_ACADEMY_TRAINED_UNIT_XP（`ABILITY_MILITARY_ACADEMY_TRAINED_UNIT_XP`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_GRANT_EXPERIENCE

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_ALLIANCE_TRAINED_UNITS_FREE_UPGRADE` | `COLLECTION_ALLIANCE_TRAINED_UNITS` |
| `MODIFIER_CITY_TRAINED_UNITS_ADJUST_GRANT_EXPERIENCE` | `COLLECTION_CITY_TRAINED_UNITS` |
| `MODIFIER_UNITS_ADJUST_GRANT_EXPERIENCE` | `COLLECTION_ALL_UNITS` |
| `MODIFIER_PLAYER_UNIT_ADJUST_GRANT_EXPERIENCE` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_UNITS_ADJUST_GRANT_EXPERIENCE` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `-1`、`20` |

**效果**：赠予单位指定数量的经验值
> **溯源**：总督晋升 — 射击孔（`GOVERNOR_PROMOTION_EMBRASURE`） — 赋予总督晋升能力
> **溯源**：伟人能力 — 阿尔特米西亚（`GREAT_PERSON_INDIVIDUAL_ARTEMISIA`）（为军事海军单位赠予1次强化等级。）
> **溯源**：伟人能力 — 拉斯喀瑞尼亚·鲍勃里斯（`GREAT_PERSON_INDIVIDUAL_LASKARINA_BOUBOULINA`）
> **溯源**：伟人能力 — 谢尔盖·戈尔什科夫（`GREAT_PERSON_INDIVIDUAL_SERGEY_GORSHKOV`）
> **溯源**：伟人能力 — 克兰西·费尔南多（`GREAT_PERSON_INDIVIDUAL_CLANCY_FERNANDO`）

---

### EFFECT_ADJUST_UNIT_NO_BARB_XP_LIMIT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_UNIT_NO_BARB_XP_LIMIT` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `NoLimit` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：移除单位从蛮族获得的经验上限
> **溯源**：文明/领袖特性 — 我来，我见，我征服（`TRAIT_LEADER_CAESAR`） — 文明或领袖特性效果

---

### EFFECT_ADJUST_UNIT_UPGRADE_GOODY_HUT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_UPGRADE_GOODY_HUT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1` |

**效果**：允许单位从部落村庄中升级
> **溯源**：部落村庄 — 军事升级（`GOODYHUT_GRANT_UPGRADE`） — 部落村庄奖励效果

---

## 回血/治疗

### EFFECT_ADJUST_RANDOM_EVENT_NO_UNIT_DAMAGE

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_RANDOM_EVENT_NO_UNIT_DAMAGE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `NoDamage` | 是 | `1`（`1`=是 / `0`=否） |
| `RandomEventType` | 是 | `RANDOM_EVENT_BLIZZARD_CRIPPLING`、`RANDOM_EVENT_BLIZZARD_SIGNIFICANT`、`RANDOM_EVENT_DROUGHT_EXTREME`、`RANDOM_EVENT_DROUGHT_MAJOR`、`RANDOM_EVENT_DUST_STORM_GRADIENT`、`RANDOM_EVENT_DUST_STORM_HABOOB` ... (共 27 种值) |

**效果**：保护单位免受指定随机环境事件的伤害
> **溯源**：文明/领袖特性 — 俄罗斯母亲（`TRAIT_CIVILIZATION_MOTHER_RUSSIA`） — 文明或领袖特性效果
> **溯源**：文明/领袖特性 — 神风（`TRAIT_LEADER_DIVINE_WIND`） — 文明或领袖特性效果
> **溯源**：文明/领袖特性 — 平安祈愿（`TRAIT_LEADER_GU_NINGNING`） — 文明或领袖特性效果

---

### EFFECT_ADJUST_UNIT_HEAL

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_HEAL` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `100` |

**效果**：直接治疗单位指定血量
> **溯源**：部落村庄 — 军事治疗（`GOODYHUT_HEAL`） — 部落村庄奖励效果

---

### EFFECT_ADJUST_UNIT_HEALING_MODIFIERS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_EMERGENCY_UNITS_ADJUST_HEALING` | `COLLECTION_EMERGENCY_UNITS` |
| `MODIFIER_ALL_UNITS_ADJUST_HEAL_PER_TURN` | `COLLECTION_ALL_UNITS` |
| `MODIFIER_PLAYER_UNIT_ADJUST_HEAL_PER_TURN` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_UNITS_ADJUST_HEAL_PER_TURN` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `10`、`100`、`20`、`30`、`5`、`50` |
| `Type` | 是 | `ALL`、`ENEMY`、`FRIENDLY`、`NEUTRAL` |

**效果**：调整单位每回合的生命值回复量
> **溯源**：单位能力 — 中立地区恢复（`ABILITY_HEAL_NEUTRAL_TERRITORY`） — 赋予单位特殊能力
> **溯源**：单位晋升 — 辅助船（`PROMOTION_AUXILIARY_SHIPS`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 船舰补给（`PROMOTION_SUPPLY_FLEET`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 超级航空母舰（`PROMOTION_SUPER_CARRIER`） — 赋予单位晋升效果
> **溯源**：单位能力 — 桃大将军的鼓舞（`ABILITY_UNIT_PEACH_MYRTLE_COMBAT_AND_MOVE`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_HEALING_RELIGION_MODIFIERS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_HEAL_RELIGION_PER_TURN` | `COLLECTION_OWNER` |
| `MODIFIER_ALL_UNITS_ADJUST_HEAL_RELIGION_PER_TURN` | `COLLECTION_ALL_UNITS` |
| `MODIFIER_PLAYER_UNITS_ADJUST_HEAL_RELIGION_PER_TURN` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `10` |
| `Type` | 是 | `ALL` |

**效果**：调整宗教单位在特定宗教领土中的回复量
> **溯源**：万神/信条 — "圣水"（`BELIEF_HOLY_WATERS`） — 宗教单位在己方圣水领土中回血量增加

---

### EFFECT_ADJUST_UNIT_POST_COMBAT_HEAL

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_HEAL_FROM_COMBAT` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_UNITS_ADJUST_HEAL_FROM_COMBAT` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `20`、`30` |

**效果**：单位战斗后回复指定血量
> **溯源**：单位能力 — ABILITY_TOMYRIS_HEAL_AFTER_DEFEATING_UNIT（`ABILITY_TOMYRIS_HEAL_AFTER_DEFEATING_UNIT`） — 赋予单位特殊能力
> **溯源**：建筑 — 作战部（`BUILDING_GOV_MILITARY`）

---

