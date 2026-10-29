# modifier-unit-combat -- 单位战斗/属性/移动/经验/间谍/旅游/宗教等 EffectType — 间谍/宗教/掠夺

> 分册：由 [modifier-unit-combat.md](modifier-unit-combat.md) 按主题拆出；覆盖 间谍、EFFECT_ADJUST_UNIT_BOOST_ALL_SPIES、EFFECT_ADJUST_UNIT_SPY_COUNTERSPY_ADJACENT_LEVEL_BOOST、EFFECT_ADJUST_UNIT_SPY_COUNTERSPY_ENTIRE_CITY、EFFECT_ADJUST_UNIT_SPY_ESTABLISH_TIME、EFFECT_ADJUST_UNIT_SPY_OFFENSIVE_OPERATION_TIME、EFFECT_ADJUST_UNIT_SPY_OPERATION_CHANCE、EFFECT_ADJUST_UNIT_SPY_OPERATION_TIME、宗教传播、EFFECT_ADD_RELIGIOUS_UNIT、EFFECT_ADJUST_UNIT_FOREIGN_SPREAD_MODIFIER、EFFECT_ADJUST_UNIT_LAND_VICTORY_SPREAD、EFFECT_ADJUST_UNIT_NO_FOREIGN_SPREAD、EFFECT_ADJUST_UNIT_SPREAD_CHARGES、掠夺/劫掠、EFFECT_ADJUST_UNIT_FAITH_ON_DISTRICT_PLUNDER、EFFECT_ADJUST_UNIT_FAITH_ON_IMPROVEMENT_PLUNDER、EFFECT_ADJUST_UNIT_PILLAGE_DISTRICT_MODIFIER、EFFECT_ADJUST_UNIT_PILLAGE_IMPROVEMENT_MODIFIER、EFFECT_ADJUST_UNIT_PLUNDER_YIELDS。触发：改间谍、宗教传播、掠夺劫掠时。

## 间谍

### EFFECT_ADJUST_UNIT_BOOST_ALL_SPIES

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_BOOST_ALL_SPIES` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1` |
| `Defense` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：提升所有间谍的有效等级
> **溯源**：单位晋升 — 军需官（`PROMOTION_SPY_QUARTERMASTER`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 测谎仪（`PROMOTION_SPY_POLYGRAPH`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_SPY_COUNTERSPY_ADJACENT_LEVEL_BOOST

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_UNIT_ADJUST_SPY_COUNTERSPY_ADJACENT_LEVEL_BOOST` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1` |

**效果**：反间谍时提升相邻单元格友方间谍的等级
> **溯源**：单位晋升 — 监视（`PROMOTION_SPY_SURVEILLANCE`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_SPY_COUNTERSPY_ENTIRE_CITY

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_UNIT_ADJUST_SPY_COUNTERSPY_ENTIRE_CITY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `EntireCity` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：反间谍时保护整个城市的所有区域
> **溯源**：单位晋升 — 监视（`PROMOTION_SPY_SURVEILLANCE`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_SPY_ESTABLISH_TIME

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_SPY_ESTABLISH_TIME` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_UNITS_ADJUST_SPY_ESTABLISH_TIME` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `ReductionPercent` | 是 | `100` |

**效果**：减少间谍在目标城市建立据点的回合数
> **溯源**：单位晋升 — 掩饰（`PROMOTION_SPY_DISGUISE`） — 赋予单位晋升效果
> **溯源**：纪念活动 — COMMEMORATION_ESPIONAGE（`COMMEMORATION_ESPIONAGE`）

---

### EFFECT_ADJUST_UNIT_SPY_OFFENSIVE_OPERATION_TIME

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_SPY_OFFENSIVE_OPERATION_TIME` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `ReductionPercent` | 是 | `25` |

**效果**：减少间谍进攻性行动所需回合数
> **溯源**：纪念活动 — COMMEMORATION_ESPIONAGE（`COMMEMORATION_ESPIONAGE`）
> **溯源**：政策 — 权术主义（`POLICY_MACHIAVELLIANISM`） — 通过政策卡提供加成

---

### EFFECT_ADJUST_UNIT_SPY_OPERATION_CHANCE

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_SPY_OPERATION_CHANCE` | `COLLECTION_OWNER` |
| `MODIFIER_EMERGENCY_UNITS_ADJUST_SPYING_EFFICIENCY` | `COLLECTION_EMERGENCY_UNITS` |
| `MODIFIER_ALL_UNITS_ADJUST_SPYING_EFFICIENCY` | `COLLECTION_ALL_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `-10`、`2` |
| `Offensive` | 是 | `0`、`1`（`1`=是 / `0`=否） |
| `OperationType` | 是 | `UNITOPERATION_SPY_BREACH_DAM`、`UNITOPERATION_SPY_DISRUPT_ROCKETRY`、`UNITOPERATION_SPY_FABRICATE_SCANDAL`、`UNITOPERATION_SPY_FOMENT_UNREST`、`UNITOPERATION_SPY_GREAT_WORK_HEIST`、`UNITOPERATION_SPY_NEUTRALIZE_GOVERNOR` ... (共 10 种值) |

**效果**：调整间谍行动的成功率
> **溯源**：单位晋升 — 技术专家（`PROMOTION_SPY_TECHNOLOGIST`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 飞贼（`PROMOTION_SPY_CAT_BURGLAR`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 爆破兵（`PROMOTION_SPY_DEMOLITIONS`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 骗子（`PROMOTION_SPY_CON_ARTIST`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 游击队领袖（`PROMOTION_SPY_GUERILLA_LEADER`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_SPY_OPERATION_TIME

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_SPY_OPERATION_TIME` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_UNITS_ADJUST_SPY_OPERATION_TIME` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `OperationType` | 是 | `UNITOPERATION_SPY_DISRUPT_ROCKETRY`、`UNITOPERATION_SPY_GAIN_SOURCES`、`UNITOPERATION_SPY_GREAT_WORK_HEIST`、`UNITOPERATION_SPY_RECRUIT_PARTISANS`、`UNITOPERATION_SPY_SABOTAGE_PRODUCTION`、`UNITOPERATION_SPY_SIPHON_FUNDS` |
| `ReductionPercent` | 是 | `25` |

**效果**：减少特定间谍行动类型所需回合数
> **溯源**：单位晋升 — 语言学家（`PROMOTION_SPY_LINGUIST`） — 赋予单位晋升效果

---

## 宗教传播

### EFFECT_ADD_RELIGIOUS_UNIT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_RELIGION_ADD_RELIGIOUS_UNIT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `UnitType` | 是 | `UNIT_WARRIOR_MONK` |

**效果**：解锁可购买的宗教单位类型
> **溯源**：信条 — 武僧（`BELIEF_WARRIOR_MONKS`）

---

### EFFECT_ADJUST_UNIT_FOREIGN_SPREAD_MODIFIER

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_FOREIGN_SPREAD_MODIFIER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `200` |

**效果**：调整宗教单位在外国领土的传播强度
> **溯源**：单位晋升 — 翻译员（`PROMOTION_TRANSLATOR`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_LAND_VICTORY_SPREAD

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_LAND_VICTORY_SPREAD` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `LandVictorySpread` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：陆地单位击杀敌方时自动传播己方宗教
> **溯源**：单位晋升 — 弟子（`PROMOTION_MONK_DISCIPLES`） — 赋予单位晋升效果
> **溯源**：单位能力 — 圣城之战（`ABILITY_BYZANTIUM_COMBAT_UNITS`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_NO_FOREIGN_SPREAD

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_NO_FOREIGN_SPREAD` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `NoSpread` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：禁止宗教单位在外国领土传教
> **溯源**：单位能力 — 国内传播（`ABILITY_NO_FOREIGN_SPREAD`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_SPREAD_CHARGES

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_SPREAD_CHARGES` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_UNITS_ADJUST_SPREAD_CHARGES` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1`、`2` |

**效果**：调整宗教单位的传教次数
> **溯源**：单位晋升 — 演说者（`PROMOTION_ORATOR`） — 赋予单位晋升效果
> **溯源**：建筑 — 圣索菲亚大教堂（`BUILDING_HAGIA_SOPHIA`）
> **溯源**：文明/领袖特性 — 艾思科里亚（`TRAIT_LEADER_EL_ESCORIAL`） — 文明或领袖特性效果

---

## 掠夺/劫掠

### EFFECT_ADJUST_UNIT_FAITH_ON_DISTRICT_PLUNDER

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_FAITH_ON_DISTRICT_PILLAGE` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `30` |

**效果**：掠夺区域时额外获得信仰
> **溯源**：建筑 — 骑士团长礼拜堂（`BUILDING_GOV_FAITH`）

---

### EFFECT_ADJUST_UNIT_FAITH_ON_IMPROVEMENT_PLUNDER

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_FAITH_ON_IMPROVEMENT_PILLAGE` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `15` |

**效果**：掠夺改良设施时额外获得信仰
> **溯源**：建筑 — 骑士团长礼拜堂（`BUILDING_GOV_FAITH`）

---

### EFFECT_ADJUST_UNIT_PILLAGE_DISTRICT_MODIFIER

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_DISTRICT_PILLAGE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `50` |

**效果**：调整掠夺区域获得的产出倍率
> **溯源**：政策 — 扫荡（`POLICY_RAID`） — 通过政策卡提供加成
> **溯源**：政策 — 全面战争（`POLICY_TOTAL_WAR`） — 通过政策卡提供加成

---

### EFFECT_ADJUST_UNIT_PILLAGE_IMPROVEMENT_MODIFIER

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_IMPROVEMENT_PILLAGE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `50` |

**效果**：调整掠夺改良设施获得的产出倍率
> **溯源**：政策 — 扫荡（`POLICY_RAID`） — 通过政策卡提供加成
> **溯源**：政策 — 全面战争（`POLICY_TOTAL_WAR`） — 通过政策卡提供加成

---

### EFFECT_ADJUST_UNIT_PLUNDER_YIELDS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_PLUNDER_YIELDS` | `COLLECTION_PLAYER_UNITS` |
| `MODIFIER_PLAYER_UNIT_ADJUST_PLUNDER_YIELDS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `100`、`40`、`50`、`60` |

**效果**：调整单位掠夺时获得的总产出倍率
> **溯源**：政策 — 全面战争（`POLICY_TOTAL_WAR`） — 通过政策卡提供加成
> **溯源**：政策 — 私掠许可证（`POLICY_LETTERS_OF_MARQUE`） — 通过政策卡提供加成
> **溯源**：单位能力 — ABILITY_RAJENDRA_CHOLA_PLUNDER_BONUS（`ABILITY_RAJENDRA_CHOLA_PLUNDER_BONUS`） — 赋予单位特殊能力
> **溯源**：单位能力 — ABILITY_FRANCIS_DRAKE_PLUNDER_BONUS（`ABILITY_FRANCIS_DRAKE_PLUNDER_BONUS`） — 赋予单位特殊能力
> **溯源**：单位能力 — ABILITY_CHING_SHIH_PLUNDER_BONUS（`ABILITY_CHING_SHIH_PLUNDER_BONUS`） — 赋予单位特殊能力

---

