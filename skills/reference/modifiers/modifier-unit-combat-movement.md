# modifier-unit-combat -- 单位战斗/属性/移动/经验/间谍/旅游/宗教等 EffectType — 移动力

> 分册：由 [modifier-unit-combat.md](modifier-unit-combat.md) 按主题拆出；覆盖 移动力、EFFECT_ADJUST_PLAYER_EMBARKED_UNIT_MOVEMENT、EFFECT_ADJUST_PLAYER_EMBARK_UNIT_PASS、EFFECT_ADJUST_UNIT_ATTACK_AND_MOVE、EFFECT_ADJUST_UNIT_CLEAR_TERRAIN_START_MOVEMENT、EFFECT_ADJUST_UNIT_ENTER_FOREIGN_LANDS、EFFECT_ADJUST_UNIT_ENEMY_TERRITORY_START_MOVEMENT、EFFECT_ADJUST_UNIT_ESCAPE_BOOST、EFFECT_ADJUST_UNIT_ESCORT_MOBILITY、EFFECT_ADJUST_UNIT_FRIENDLY_TERRITORY_START_MOVEMENT、EFFECT_ADJUST_UNIT_IGNORE_RIVERS、EFFECT_ADJUST_UNIT_IGNORE_SHORES、EFFECT_ADJUST_UNIT_IGNORE_TERRAIN_COST、EFFECT_ADJUST_UNIT_JUMP_ABILITY、EFFECT_ADJUST_UNIT_MOVEMENT、EFFECT_ADJUST_UNIT_MOVE_AND_ATTACK、EFFECT_ADJUST_UNIT_PARADROP_ABILITY、EFFECT_ADJUST_UNIT_PROMOTE_NO_FINISH_MOVES、EFFECT_ADJUST_UNIT_SEA_MOVEMENT、EFFECT_ADJUST_UNIT_TRADE_ROUTE_PLUNDER_IMMUNITY、EFFECT_RESTORE_UNIT_MOVEMENT。触发：改移动力、忽略地形/控制区时。

## 移动力

### EFFECT_ADJUST_PLAYER_EMBARKED_UNIT_MOVEMENT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_EMBARKED_MOVEMENT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1`、`2` |

**效果**：调整所有登船单位的移动力
> **溯源**：建筑 — 大灯塔（`BUILDING_GREAT_LIGHTHOUSE`）
> **溯源**：科技 — 横帆装置（`TECH_SQUARE_RIGGING`）
> **溯源**：科技 — 蒸汽动力（`TECH_STEAM_POWER`）
> **溯源**：科技 — 内燃机（`TECH_COMBUSTION`）
> **溯源**：纪念活动 — COMMEMORATION_EXPLORATION（`COMMEMORATION_EXPLORATION`）

---

### EFFECT_ADJUST_PLAYER_EMBARK_UNIT_PASS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_EMBARK_UNIT_PASS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `UnitType` | 是 | `UNIT_TRADER` |

**效果**：允许指定单位类型登船通行
> **溯源**：文明/领袖特性 — 印度之家（`TRAIT_CIVILIZATION_PORTUGAL`） — 文明或领袖特性效果

---

### EFFECT_ADJUST_UNIT_ATTACK_AND_MOVE

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_ATTACK_AND_MOVE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `CanMove` | 是 | `1`、`True`（`1`=是 / `0`=否） |

**效果**：允许单位攻击后再移动
> **溯源**：单位能力 — 静静的顿河（`ABILITY_COSSACK`） — 赋予单位特殊能力
> **溯源**：单位晋升 — 游击队（`PROMOTION_GUERRILLA`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 精英卫队（`PROMOTION_ELITE_GUARD`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 突破（`PROMOTION_BREAKTHROUGH`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 风舞拳（`PROMOTION_MONK_SWEEPING_WIND`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_CLEAR_TERRAIN_START_MOVEMENT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_CLEAR_TERRAIN_START_MOVEMENT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1`、`2` |

**效果**：若回合开始时位于开阔地形，增加移动力
> **溯源**：单位能力 — 重型战车（`ABILITY_HEAVY_CHARIOT`） — 赋予单位特殊能力（初始处于开阔地貌时+1 [ICON_Movement] 移动力。）
> **溯源**：单位能力 — 轻战车（`ABILITY_LIGHT_CHARIOT`） — 赋予单位特殊能力（初始处于开阔地貌时+2 [ICON_Movement] 移动力。）

---

### EFFECT_ADJUST_UNIT_ENTER_FOREIGN_LANDS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_ENTER_FOREIGN_LANDS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Enter` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：允许单位进入外国领土（无视封闭边界）
> **溯源**：单位能力 — 进入外国领土。（`ABILITY_ARCHAEOLOGIST_ENTER_FOREIGN_LANDS`） — 赋予单位特殊能力
> **溯源**：单位能力 — 忽略边界（`ABILITY_RELIGIOUS_ENTER_FOREIGN_LANDS`） — 赋予单位特殊能力
> **溯源**：单位能力 — 进入外国领土（`ABILITY_ROCK_BAND_ENTER_FOREIGN_LANDS`） — 赋予单位特殊能力
> **溯源**：伟人 — 周达观（`GREAT_PERSON_INDIVIDUAL_ZHOU_DAGUAN`）（此伟人将无视封闭的边界。）
> **溯源**：伟人 — 马休·佩里（`GREAT_PERSON_INDIVIDUAL_MATTHEW_PERRY`）（此伟人将无视封闭的边界。）

---

### EFFECT_ADJUST_UNIT_ENEMY_TERRITORY_START_MOVEMENT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_ENEMY_TERRITORY_START_MOVEMENT` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1` |

**效果**：若回合开始时位于敌方领土，增加移动力
> **溯源**：政策 — 综合攻击后勤保障（`POLICY_FUTURE_VICTORY_DOMINATION`） — 通过政策卡提供加成

---

### EFFECT_ADJUST_UNIT_ESCAPE_BOOST

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ESCAPE_BOOST` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `4` |

**效果**：增加间谍逃脱时的移动力
> **溯源**：单位晋升 — 王牌驾驶员（`PROMOTION_SPY_ACE_DRIVER`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_ESCORT_MOBILITY

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_UNIT_ADJUST_ESCORT_MOBILITY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `EscortMobility` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：赋予单位护卫其他单位的机动能力
> **溯源**：单位能力 — ABILITY_JONG（`ABILITY_JONG`） — 赋予单位特殊能力
> **溯源**：单位能力 — ABILITY_MONGOLIAN_KESHIG（`ABILITY_MONGOLIAN_KESHIG`） — 赋予单位特殊能力
> **溯源**：单位晋升 — 护卫队机动性（`PROMOTION_ESCORT_MOBILITY`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_FRIENDLY_TERRITORY_START_MOVEMENT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_FRIENDLY_TERRITORY_START_MOVEMENT` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1` |

**效果**：若回合开始时位于友方领土，增加移动力
> **溯源**：政策 — 后勤（`POLICY_LOGISTICS`） — 通过政策卡提供加成

---

### EFFECT_ADJUST_UNIT_IGNORE_RIVERS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_IGNORE_RIVERS` | `COLLECTION_PLAYER_UNITS` |
| `MODIFIER_PLAYER_UNIT_ADJUST_IGNORE_RIVERS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Ignore` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：单位移动时忽略河流消耗
> **溯源**：单位能力 — 忽略穿越河流的消耗（`ABILITY_IGNORE_CROSSING_RIVERS_COST`） — 赋予单位特殊能力（穿越河流忽略移动力消耗。）
> **溯源**：单位能力 — 空中漫步（`ABILITY_RELIGIOUS_IGNORE_TERRAIN_COST`） — 赋予单位特殊能力（穿越河流忽略移动力消耗。）
> **溯源**：单位晋升 — 水陆两栖（`PROMOTION_AMPHIBIOUS`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_IGNORE_SHORES

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_IGNORE_SHORES` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_UNITS_ADJUST_IGNORE_SHORES` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Ignore` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：单位登船/下船时忽略移动力消耗
> **溯源**：单位能力 — 全球性军队（`ABILITY_REDCOAT`） — 赋予单位特殊能力
> **溯源**：单位能力 — ABILITY_KNARR_IGNORE_EMBARK_DISEMBARK_COST（`ABILITY_KNARR_IGNORE_EMBARK_DISEMBARK_COST`） — 赋予单位特殊能力
> **溯源**：单位晋升 — 水陆两栖（`PROMOTION_AMPHIBIOUS`） — 赋予单位晋升效果
> **溯源**：单位能力 — 地中海殖民地（`ABILITY_MEDITERRANEAN_COLONIES`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_IGNORE_TERRAIN_COST

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_IGNORE_TERRAIN_COST` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Ignore` | 是 | `1`、`true`（`1`=是 / `0`=否） |
| `Type` | 是 | `ALL`、`FEATURE_JUNGLE`、`FEATURE_MARSH`、`FOREST`、`HILLS` |

**效果**：单位移动时忽略地形/地貌的移动力消耗
> **溯源**：单位能力 — 忽略地形消耗（`ABILITY_IGNORE_TERRAIN_COST`） — 赋予单位特殊能力（所有地形消耗1个 [ICON_Movement] 移动力。）
> **溯源**：单位能力 — 空中漫步（`ABILITY_RELIGIOUS_IGNORE_TERRAIN_COST`） — 赋予单位特殊能力（所有地形消耗1个 [ICON_Movement] 移动力。）
> **溯源**：单位能力 — 高原训练（`ABILITY_ALTITUDE_TRAINING`） — 赋予单位特殊能力
> **溯源**：单位能力 — 森林斗士（`ABILITY_NAGAO`） — 赋予单位特殊能力
> **溯源**：单位晋升 — 游骑兵（`PROMOTION_RANGER`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_JUMP_ABILITY

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_UNIT_ADJUST_JUMP_DISTANCE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Range` | 是 | `4`、`5`、`6` |

**效果**：赋予/调整单位的跳跃（空降/传送）距离
> **溯源**：单位晋升 — 增强机动（`PROMOTION_GDR_BONUS_MOVEMENT`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_MOVEMENT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_MOVEMENT` | `COLLECTION_PLAYER_UNITS` |
| `MODIFIER_PLAYER_UNIT_ADJUST_MOVEMENT` | `COLLECTION_OWNER` |
| `MODIFIER_EMERGENCY_UNITS_ADJUST_MOVEMENT` | `COLLECTION_EMERGENCY_UNITS` |
| `MODIFIER_ALLIANCE_UNIT_MOVEMENT` | `COLLECTION_ALLIANCE_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `-1`、`-2`、`-4`、`-8`、`1`、`2` |

**效果**：调整单位的移动力（绝对值）
> **溯源**：纪念活动 — COMMEMORATION_INFRASTRUCTURE（`COMMEMORATION_INFRASTRUCTURE`）
> **溯源**：纪念活动 — COMMEMORATION_RELIGIOUS（`COMMEMORATION_RELIGIOUS`）
> **溯源**：政策 — 私掠许可证（`POLICY_LETTERS_OF_MARQUE`） — 通过政策卡提供加成
> **溯源**：单位能力 — ABILITY_GRANT_MOVEMENT_BONUS（`ABILITY_GRANT_MOVEMENT_BONUS`） — 赋予单位特殊能力
> **溯源**：单位晋升 — "和谐"（`PROMOTION_SPECIAL_POPUKAR_R2`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_MOVE_AND_ATTACK

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_MOVE_AND_ATTACK` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `CanAttack` | 是 | `0`、`1`（`1`=是 / `0`=否） |

**效果**：控制单位是否能在移动后攻击
> **溯源**：单位能力 — 无法移动射击（`ABILITY_NO_MOVE_AND_SHOOT`） — 赋予单位特殊能力（无法在移动后进行攻击。）
> **溯源**：单位晋升 — 专家组（`PROMOTION_EXPERT_CREW`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_PARADROP_ABILITY

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_PARADROP_ABILITY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `CanDrop` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：赋予/移除单位的伞降能力
> **溯源**：单位能力 — ABILITY_PARADROP（`ABILITY_PARADROP`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_PROMOTE_NO_FINISH_MOVES

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_PROMOTE_NO_FINISH_MOVES` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `NoFinishMoves` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：单位晋升后不结束回合（仍可移动/攻击）
> **溯源**：文明/领袖特性 — 爱国军（`TRAIT_CIVILIZATION_EJERCITO_PATRIOTA`） — 文明或领袖特性效果


---

### EFFECT_ADJUST_UNIT_SEA_MOVEMENT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_CITY_TRAINED_UNITS_ADJUST_MOVEMENT` | `COLLECTION_CITY_TRAINED_UNITS` |
| `MODIFIER_PLAYER_UNITS_ADJUST_SEA_MOVEMENT` | `COLLECTION_PLAYER_UNITS` |
| `MODIFIER_PLAYER_UNIT_ADJUST_SEA_MOVEMENT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1`、`2` |

**效果**：调整单位的海洋移动力
> **溯源**：科技 — 数学（`TECH_MATHEMATICS`）
> **溯源**：纪念活动 — COMMEMORATION_EXPLORATION（`COMMEMORATION_EXPLORATION`）
> **溯源**：单位能力 — 长船移动力（`ABILITY_LONGSHIP_MOVEMENT`） — 赋予单位特殊能力
> **溯源**：单位能力 — ABILITY_ROYAL_NAVY_DOCKYARD_MOVEMENT_BONUS（`ABILITY_ROYAL_NAVY_DOCKYARD_MOVEMENT_BONUS`） — 赋予单位特殊能力
> **溯源**：单位能力 — ABILITY_GREAT_LIGHTHOUSE_MOVEMENT（`ABILITY_GREAT_LIGHTHOUSE_MOVEMENT`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_TRADE_ROUTE_PLUNDER_IMMUNITY

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_TRADE_ROUTE_PLUNDER_IMMUNITY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `DomainType` | 是 | `DOMAIN_LAND`、`DOMAIN_SEA` |

**效果**：赋予贸易路线单位免于被掠夺的免疫能力
> **溯源**：单位能力 — 海上掠夺豁免（`ABILITY_TRADE_ROUTE_PLUNDER_IMMUNITY_SEA`） — 赋予单位特殊能力
> **溯源**：单位能力 — 经济黄金时代（`ABILITY_ECONOMIC_GOLDEN_AGE_PLUNDER_IMMUNITY`） — 赋予单位特殊能力
> **溯源**：单位能力 — 双层桨座战船商人保护（`ABILITY_TRADER_PROTECTED_BY_BIREME`） — 赋予单位特殊能力
> **溯源**：单位能力 — 曼德卡鲁骑兵商人保护（`ABILITY_TRADER_PROTECTED_BY_MANDEKALU`） — 赋予单位特殊能力

---

### EFFECT_RESTORE_UNIT_MOVEMENT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_RESET_MOVES` | `COLLECTION_PLAYER_UNITS` |

| *(无参数)* | | |
|---|---|---|

**效果**：恢复单位的全部移动力
> **溯源**：伟人能力 — 拉斐尔·乌达内塔（`GREAT_PERSON_INDIVIDUAL_COMMANDANTE_URDANETA`）（2单元格内的所有陆地战斗单位重新获得全额 [ICON_Movement] 移动力和攻击力。）

---

