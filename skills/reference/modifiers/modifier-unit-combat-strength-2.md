# modifier-unit-combat -- 单位战斗/属性/移动/经验/间谍/旅游/宗教等 EffectType — 战斗力/属性（2）

> 分册：由 [modifier-unit-combat.md](modifier-unit-combat.md) 按主题拆出；覆盖 EFFECT_ADJUST_UNIT_FIGHT_WHILE_EMBARKED、EFFECT_ADJUST_UNIT_FLANKING_BONUS_MODIFIER、EFFECT_ADJUST_UNIT_FORCE_RETREAT、EFFECT_ADJUST_UNIT_FRIENDLY_TERRITORY_COMBAT、EFFECT_ADJUST_UNIT_HOLY_CITIES_COMBAT_MODIFIER、EFFECT_ADJUST_UNIT_IGNORE_CLIFF_WALLS、EFFECT_ADJUST_UNIT_IGNORE_RANGED_VS_DISTRICT_PENALTY、EFFECT_ADJUST_UNIT_IGNORE_RESOURCE_MAINTENANCE、EFFECT_ADJUST_UNIT_IGNORE_STRATEGIC_RESOURCE_LEVIED、EFFECT_ADJUST_UNIT_IGNORE_ZOC、EFFECT_ADJUST_UNIT_MILITARY_FORMATION、EFFECT_ADJUST_UNIT_MILITARY_POLICIES_COMBAT_MODIFIER、EFFECT_ADJUST_UNIT_NEIGHBOR_COMBAT_MODIFIER、EFFECT_ADJUST_UNIT_NO_REDUCTION_DAMAGE、EFFECT_ADJUST_UNIT_NUM_ATTACKS、EFFECT_ADJUST_UNIT_PER_LUXURY_ATTACK_MODIFIER、EFFECT_ADJUST_UNIT_PER_UNUSED_MOVEMENT_COMBAT_BONUS、EFFECT_ADJUST_UNIT_POST_COMBAT_YIELD、EFFECT_ADJUST_UNIT_PROPERTY、EFFECT_ADJUST_UNIT_RAIDING、EFFECT_ADJUST_UNIT_RELIC_UPON_DEATH、EFFECT_ADJUST_UNIT_STRENGTH_FROM_CITY_CULTURAL_IDENTITY、EFFECT_ADJUST_UNIT_STRENGTH_REDUCTION_FOR_DAMAGE_MODIFIER、EFFECT_ADJUST_UNIT_SUPPORT_BONUS_MODIFIER、EFFECT_ADJUST_UNIT_WATER_DAMAGE_PROTECTION、EFFECT_ADJUST_UNIT_WMD_PROTECTION、EFFECT_ADJUST_UNITS_RELIGIOUS_STRENGTH_BY_RELIGION_TYPE、EFFECT_GRANT_STRENGTH_PER_ADJACENT_UNIT_TYPE。触发：改单位战斗力、属性、克制、攻城数值时。

### EFFECT_ADJUST_UNIT_FIGHT_WHILE_EMBARKED

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_UNIT_ADJUST_FIGHT_WHILE_EMBARKED` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `CanFight` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：允许单位在登船状态下发动战斗
> **溯源**：单位能力 — ABILITY_UNIT_FIGHT_WHILE_EMBARKED（`ABILITY_UNIT_FIGHT_WHILE_EMBARKED`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_FLANKING_BONUS_MODIFIER

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_FLANKING_BONUS_MODIFIER` | `COLLECTION_PLAYER_UNITS` |
| `MODIFIER_PLAYER_UNIT_ADJUST_FLANKING_BONUS_MODIFIER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Percent` | 是 | `100`、`50` |

**效果**：调整单位的侧翼夹击加成倍率
> **溯源**：单位能力 — ABILITY_HORATIO_NELSON_FLANKING_BONUS（`ABILITY_HORATIO_NELSON_FLANKING_BONUS`） — 赋予单位特殊能力
> **溯源**：单位能力 — ABILITY_GEORGY_ZHUKOV_FLANKING_BONUS（`ABILITY_GEORGY_ZHUKOV_FLANKING_BONUS`） — 赋予单位特殊能力
> **溯源**：单位晋升 — 两翼包围（`PROMOTION_DOUBLE_ENVELOPMENT`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 无影拳（`PROMOTION_MONK_SHADOW_STRIKE`） — 赋予单位晋升效果
> **溯源**：单位能力 — ABILITY_ZULU_IMPI（`ABILITY_ZULU_IMPI`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_FORCE_RETREAT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_UNIT_ADJUST_FORCE_RETREAT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `ForceRetreat` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：赋予单位强制击退敌方单位的能力
> **溯源**：单位能力 — ABILITY_PUSHBACK（`ABILITY_PUSHBACK`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_FRIENDLY_TERRITORY_COMBAT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_FRIENDLY_TERRITORY_COMBAT` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_UNITS_ADJUST_FRIENDLY_TERRITORY_COMBAT` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `15`、`35` |

**效果**：调整单位在友方领土中的战斗力
> **溯源**：单位能力 — 友好领土优势（`ABILITY_FRIENDLY_TERRITORY_RELIGIOUS`） — 赋予单位特殊能力（在友方领土中时获得 [ICON_Strength] 战斗力加成。）
> **溯源**：单位能力 — 宗教审讯（`ABILITY_INQUISITION_FRIENDLY_TERRITORY_BONUS`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_HOLY_CITIES_COMBAT_MODIFIER

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_COMBAT_FOR_NUMBER_HOLY_CITIES` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `3` |

**效果**：根据圣城数量调整单位战斗力
> **溯源**：单位能力 — 圣城之战（`ABILITY_BYZANTIUM_COMBAT_UNITS`） — 赋予单位特殊能力
> **溯源**：单位能力 — 圣城宗教战斗力（`ABILITY_BYZANTIUM_RELIGIOUS_UNITS`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_IGNORE_CLIFF_WALLS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_IGNORE_CLIFF_WALLS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Ignore` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：允许单位忽略悬崖移动限制
> **溯源**：单位晋升 — 突击队（`PROMOTION_COMMANDO`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_IGNORE_RANGED_VS_DISTRICT_PENALTY

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_IGNORE_RANGED_VS_DISTRICT_PENALTY` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_UNITS_IGNORE_RANGED_VS_DISTRICT_PENALTY` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Ignore` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：忽略远程单位对区域攻击的减伤惩罚
> **溯源**：单位晋升 — 粒子束攻城巨炮（`PROMOTION_GDR_SIEGE_LASER`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_IGNORE_RESOURCE_MAINTENANCE

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_IGNORE_RESOURCE_MAINTENANCE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Ignore` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：免除单位的战略资源维护需求
> **溯源**：单位能力 — ABILITY_LINCOLN_MELEE_UNITS（`ABILITY_LINCOLN_MELEE_UNITS`） — 赋予单位特殊能力
> **溯源**：伟人能力 — 安东尼奥·何塞·苏克雷（`GREAT_PERSON_INDIVIDUAL_COMMANDANTE_JOSE_DE_SUCRE`）
> **溯源**：单位能力 — 跑马场（`ABILITY_FREE_RESOURCE_MAITENANCE_HIPPODROME`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_IGNORE_STRATEGIC_RESOURCE_LEVIED

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_LEVIED_UNIT_IGNORE_STRATEGIC_RESOURCE` | `COLLECTION_OWNER` |

| *(无参数)* | | |
|---|---|---|

**效果**：免除征召单位的战略资源维护需求

---

### EFFECT_ADJUST_UNIT_IGNORE_ZOC

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_IGNORE_ZOC` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Ignore` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：赋予单位忽略敌方控制区（ZOC）的能力
> **溯源**：单位能力 — 忽略控制区（`ABILITY_IGNORE_ZOC`） — 赋予单位特殊能力（未受控制区影响）

---

### EFFECT_ADJUST_UNIT_MILITARY_FORMATION

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_MILITARY_FORMATION` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `MilitaryFormationType` | 是 | `ARMY_MILITARY_FORMATION`、`CORPS_MILITARY_FORMATION` |

**效果**：将单位升级为军团/军队等编队形态
> **溯源**：伟人能力 — 盖尤斯·杜伊路斯（`GREAT_PERSON_INDIVIDUAL_GAIUS_DUILIUS`）（由一个军事海军单位形成一支舰队。）
> **溯源**：伟人能力 — 圣·克鲁斯（`GREAT_PERSON_INDIVIDUAL_SANTA_CRUZ`）（由一个军事海军单位形成一支无敌舰队。）
> **溯源**：伟人能力 — 艾尔·熙德（`GREAT_PERSON_INDIVIDUAL_EL_CID`）（把一个军事陆地单位变成军团。）
> **溯源**：伟人能力 — 拿破仑·波拿巴（`GREAT_PERSON_INDIVIDUAL_NAPOLEON_BONAPARTE`）（把一个军事陆地单位变成军队。）

---

### EFFECT_ADJUST_UNIT_MILITARY_POLICIES_COMBAT_MODIFIER

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_PER_MILITARY_POLICIES_COMBAT_MODIFIER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1` |

**效果**：根据已启用军事政策槽位数量提供战斗力加成
> **溯源**：单位能力 — ABILITY_GORGO_POLICY_SLOT_COMBAT_BONUS（`ABILITY_GORGO_POLICY_SLOT_COMBAT_BONUS`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_NEIGHBOR_COMBAT_MODIFIER

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_COMBAT_FOR_NUMBER_NEIGHBORS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `2` |

**效果**：根据相邻己方单位数量调整战斗力
> **溯源**：单位能力 — 安比奥里克斯（`ABILITY_AMBIORIX_NEIGHBOR_COMBAT_BONUS`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_NO_REDUCTION_DAMAGE

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_NO_REDUCTION_DAMAGE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `NoReduction` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：移除单位受伤后的战斗力惩罚
> **溯源**：单位能力 — 武士（`ABILITY_SAMURAI`） — 赋予单位特殊能力
> **溯源**：单位晋升 — 锁子甲（`PROMOTION_NIHANG_NO_WOUNDED_PENALTY`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_NUM_ATTACKS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_UNIT_ADJUST_NUM_ATTACKS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1`、`3` |

**效果**：调整单位每回合的攻击次数
> **溯源**：单位晋升 — 精英卫队（`PROMOTION_ELITE_GUARD`） — 赋予单位晋升效果
> **溯源**：单位能力 — ABILITY_EXPERT_MARKSMAN（`ABILITY_EXPERT_MARKSMAN`） — 赋予单位特殊能力（如果单位没有移动，每回合+1额外攻击。）
> **溯源**：单位晋升 — 神枪手（`PROMOTION_EXPERT_MARKSMAN`） — 赋予单位晋升效果（如果单位没有移动，每回合+1额外攻击。）
> **溯源**：单位晋升 — 突破（`PROMOTION_BREAKTHROUGH`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 狼群战术（`PROMOTION_WOLFPACK`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_PER_LUXURY_ATTACK_MODIFIER

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_PER_LUXURY_ATTACK_MODIFIER` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_UNITS_ADJUST_PER_LUXURY_ATTACK_MODIFIER` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1` |

**效果**：根据拥有奢侈品数量提供战斗力加成
> **溯源**：单位能力 — ABILITY_MONTEZUMA_COMBAT_BONUS_PER_LUXURY（`ABILITY_MONTEZUMA_COMBAT_BONUS_PER_LUXURY`） — 赋予单位特殊能力（奢侈品提供+{1_Amount} [ICON_Strength] 战斗力。（蒙特祖玛））

---

### EFFECT_ADJUST_UNIT_PER_UNUSED_MOVEMENT_COMBAT_BONUS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_UNIT_ADJUST_COMBAT_FOR_UNUSED_MOVEMENT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `3` |

**效果**：根据未使用移动力提供战斗力加成
> **溯源**：单位能力 — 向前冲（`ABILITY_CAROLEAN`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_POST_COMBAT_YIELD

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_UNIT_ADJUST_POST_COMBAT_YIELD` | `COLLECTION_UNIT_COMBAT` |
| `MODIFIER_PLAYER_UNITS_ADJUST_POST_COMBAT_YIELD` | `COLLECTION_PLAYER_COMBAT` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `OnlyWhenDefeatedEarlierEraUnit` | 是 | `1`（`1`=是 / `0`=否） |
| `PercentDefeatedStrength` | 是 | `100`、`150`、`50` |
| `YieldType` | 是 | `YIELD_CULTURE`、`YIELD_FAITH`、`YIELD_GOLD`、`YIELD_SCIENCE` |

**效果**：战斗胜利后获得指定产出
> **溯源**：单位能力 — 泰迪的莽骑兵（`ABILITY_ROUGH_RIDER`） — 赋予单位特殊能力
> **溯源**：单位晋升 — 登船（`PROMOTION_BOARDING`） — 赋予单位晋升效果
> **溯源**：单位能力 — 赠金者（`ABILITY_MANDEKALU`） — 赋予单位特殊能力
> **溯源**：单位能力 — ABILITY_LEVIED_HARALD（`ABILITY_LEVIED_HARALD`） — 赋予单位特殊能力
> **溯源**：单位晋升 — 三叉戟（`PROMOTION_NIHANG_FAITH_FOR_VICTORIES`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_PROPERTY

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_UNIT_ADJUST_PROPERTY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `-5`、`1`、`2`、`20`、`3`、`4` ... (共 10 种值) |
| `Key` | 是 | 自定义属性标识（由MOD定义） |

**效果**：调整单位自定义属性值（Key参数决定具体属性）
> **溯源**：单位能力 — ABILITY_SHAMARE_UU_GRANT（`ABILITY_SHAMARE_UU_GRANT`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_RAIDING

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_UNIT_ADJUST_RAIDING` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Bonus` | 是 | `50` |
| `CanRaid` | 是 | `1` |

**效果**：赋予单位海岸劫掠能力及劫掠产出加成
> **溯源**：单位能力 — 海岸扫荡（`ABILITY_COASTAL_RAID`） — 赋予单位特殊能力
> **溯源**：单位能力 — 雷霆海岸扫荡（`ABILITY_MELEE_COASTAL_RAID`） — 赋予单位特殊能力
> **溯源**：单位晋升 — 掠夺（`PROMOTION_LOOT`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_RELIC_UPON_DEATH

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_RELIC_UPON_DEATH` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `RelicSource` | 是 | `RELIC_SOURCE_RELIGIOUS_UNIT` |

**效果**：宗教单位死亡时产生遗物
> **溯源**：单位能力 — ABILITY_MARTYR（`ABILITY_MARTYR`） — 赋予单位特殊能力
> **溯源**：单位晋升 — 殉道者（`PROMOTION_MARTYR`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_STRENGTH_FROM_CITY_CULTURAL_IDENTITY

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_UNIT_STRENGTH_FROM_CITY_CULTURAL_IDENTITY` | `COLLECTION_PLAYER_COMBAT` |

| *(无参数)* | | |
|---|---|---|

**效果**：根据城市文化身份调整单位战斗力
> **溯源**：该 EffectType 仅在 DynamicModifiers 中注册，官方数据库中无实际 Modifier 使用记录

---

### EFFECT_ADJUST_UNIT_STRENGTH_REDUCTION_FOR_DAMAGE_MODIFIER

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_STRENGTH_REDUCTION_FOR_DAMAGE_MODIFIER` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `50` |

**效果**：调整受伤单位的战斗力削减幅度
> **溯源**：政策 — 国家认同（`POLICY_NATIONAL_IDENTITY`） — 通过政策卡提供加成

---

### EFFECT_ADJUST_UNIT_SUPPORT_BONUS_MODIFIER

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_SUPPORT_BONUS_MODIFIER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Percent` | 是 | `100`、`50` |

**效果**：调整单位的支援加成倍率
> **溯源**：单位晋升 — 方阵（`PROMOTION_SQUARE`） — 赋予单位晋升效果
> **溯源**：单位能力 — ABILITY_HYPASPIST（`ABILITY_HYPASPIST`） — 赋予单位特殊能力
> **溯源**：单位晋升 — 米格鲁（`PROMOTION_RESERVE_OPERATOR_TEAM_A1_R2`） — 赋予单位晋升效果
> **溯源**：单位能力 — ABILITY_SALADIN_FLANKING_UNITS（`ABILITY_SALADIN_FLANKING_UNITS`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_WATER_DAMAGE_PROTECTION

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_WATER_DAMAGE_RESISTANCE` | `COLLECTION_OWNER` |

| *(无参数)* | | |
|---|---|---|

**效果**：保护单位免受水灾伤害
> **溯源**：该 EffectType 仅在 DynamicModifiers 中注册，官方数据库中无实际 Modifier 使用记录

---

### EFFECT_ADJUST_UNIT_WMD_PROTECTION

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_WMD_RESISTANCE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Blast` | 是 | `50` |
| `Fallout` | 是 | `100` |

**效果**：保护单位免受核武器伤害及辐射影响
> **溯源**：单位能力 — ABILITY_UNIT_WMD_RESISTANCE（`ABILITY_UNIT_WMD_RESISTANCE`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNITS_RELIGIOUS_STRENGTH_BY_RELIGION_TYPE

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_MAJOR_PLAYERS_ADJUST_UNITS_RELIGIOUS_STRENGTH_BY_RELIGION_TYPE` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `10` |

**效果**：根据宗教类型调整宗教单位的宗教战斗力
> **溯源**：世界议会决议 — "世界宗教"（`WC_RES_WORLD_RELIGION`） — 世界议会议案效果

---

### EFFECT_GRANT_STRENGTH_PER_ADJACENT_UNIT_TYPE

| ModifierType | CollectionType |
|---|---|
| `GRANT_STRENGTH_PER_ADJACENT_UNIT_TYPE` | `COLLECTION_UNIT_COMBAT` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `2` |
| `UnitType` | 是 | `UNIT_COLOMBIAN_LLANERO` |

**效果**：根据相邻指定单位类型数量提供战斗力加成
> **溯源**：单位能力 — ABILITY_LLANERO_ADJACENCY_STRENGTH（`ABILITY_LLANERO_ADJACENCY_STRENGTH`） — 赋予单位特殊能力（相邻的牛仔骑兵提供+{CalculatedAmount} [ICON_Strength] 战斗力。）

---

