# modifier-religion -- 宗教类 EffectType — 宗教战斗

> 分册：由 [modifier-religion.md](modifier-religion.md) 按主题拆出；覆盖 EFFECT_ADJUST_CITY_RELIGION_IGNORE_COMBAT、EFFECT_ADJUST_CITY_RELIGIOUS_COMBAT_BONUS、EFFECT_ADJUST_CITY_RELIGIOUS_HEAL、EFFECT_ADJUST_RELIGIOUS_COMBAT_LOSS、EFFECT_ADJUST_UNITS_RELIGIOUS_STRENGTH_BY_RELIGION_TYPE、EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_WHOLE_GAME_SAME_RELIGION、EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_WHOLE_GAME_SAME_RELIGION_PROMOTION_CLASS、EFFECT_ADJUST_UNIT_HEALING_RELIGION_MODIFIERS。触发：改宗教战斗、治疗、破墙、宗教强度时。

## 宗教战斗

### EFFECT_ADJUST_CITY_RELIGION_IGNORE_COMBAT

该城市的宗教单位免疫敌方宗教单位的神学战斗（无法被攻击）。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_SINGLE_CITY_RELIGION_IGNORE_COMBAT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Enable` | **必写** | `1` 启用免疫 / `0` 禁用 |

> **溯源**：**红衣主教：神之堡垒**（`GOVERNOR_PROMOTION_CARDINAL_CITADEL_OF_GOD`）— 此总督所在城市免疫外教的战斗和压力（与 `IGNORE_PRESSURE` 成对使用，共同实现"宗教禁区"城市）。

---

### EFFECT_ADJUST_CITY_RELIGIOUS_COMBAT_BONUS

调整城市中宗教单位的神学战斗加成。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_SINGLE_CITY_RELIGIOUS_COMBAT_BONUS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，宗教战斗力加成值 |

> **溯源**：**红衣主教：大审判官**（`GOVERNOR_PROMOTION_CARDINAL_GRAND_INQUISITOR`）— 此城境内的宗教单位神学战斗 +10 宗教战斗力（`Amount=10`）。

---

### EFFECT_ADJUST_CITY_RELIGIOUS_HEAL

调整城市中宗教单位每回合恢复量。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_SINGLE_CITY_RELIGIOUS_HEAL` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，每回合额外恢复量 |

> **溯源**：**红衣主教：按手礼**（`GOVERNOR_PROMOTION_CARDINAL_LAYING_ON_OF_HANDS`）— 此总督所在城市境内宗教单位 1 回合后完全恢复（`Amount=100`）。

---

### EFFECT_ADJUST_RELIGIOUS_COMBAT_LOSS

调整宗教单位在神学战斗中失败时的宗教压力损失。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_RELIGION_ADJUST_COMBAT_LOSS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `ReductionPercent` | **必写** | 整数（百分比），损失减少比例。`100` = 完全免疫战斗失败惩罚 |

> **溯源**：**与世隔绝**（`BELIEF_MONASTIC_ISOLATION`，信徒信条）— 宗教压力不会因神学战斗失败而减少（`ReductionPercent=100`）。

---

### EFFECT_ADJUST_UNITS_RELIGIOUS_STRENGTH_BY_RELIGION_TYPE

全局调整所有文明的宗教单位战斗力（常用于世界议会决议）。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_MAJOR_PLAYERS_ADJUST_UNITS_RELIGIOUS_STRENGTH_BY_RELIGION_TYPE` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，所有文明宗教单位战斗力加成值 |

> **溯源**：世界议会决议 — 所有主要文明的宗教单位 +10 宗教战斗力（`Amount=10`）。注意此 ModifierType 作用于 `COLLECTION_MAJOR_PLAYERS`，会同时影响所有文明。

---

### EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_WHOLE_GAME_SAME_RELIGION

允许玩家的近战/骑兵单位攻击城墙（条件：与目标城市同宗教）。无参数版本。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_ADJUST_ENABLE_WALL_ATTACK_WHOLE_GAME_SAME_RELIGION` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| （无） | — | 无参数，直接使用 `ABILITY_ENABLE_WALL_ATTACK_WHOLE_GAME_SAME_RELIGION` 能力 |

> **溯源**：DB 中有一个实例（`TRAIT_ABILITY_ENABLE_WALL_ATTACK_SAME_RELIGION`）存在于 `Modifiers` 表，但未在任何参考表中找到。可能与同宗教攻城特质有关。使用前需确认上游挂载路径。

---

### EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_WHOLE_GAME_SAME_RELIGION_PROMOTION_CLASS

允许指定的晋升兵种类型攻击城墙（条件：目标城市同宗教）。可指定具体的兵种类别。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_ADJUST_ENABLE_WALL_ATTACK_WHOLE_GAME_SAME_RELIGION_PROMOTION_CLASS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `PromotionClass` | **必写** | `PROMOTION_CLASS_LIGHT_CAVALRY` / `PROMOTION_CLASS_HEAVY_CAVALRY` 等，引用 [UnitPromotionClasses.PromotionClassType] |

> **溯源**：**巴兹尔二世**（`TRAIT_LEADER_BASIL`，拜占庭特质）— 轻骑兵和重骑兵均可攻击与拜占庭同宗教的城市的城墙（两个 Modifier 各指定一个 `PromotionClass`）。

---

### EFFECT_ADJUST_UNIT_HEALING_RELIGION_MODIFIERS

在圣地区域或相邻单元格中调整单位每回合恢复量（宗教单位限定）。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_ALL_UNITS_ADJUST_HEAL_RELIGION_PER_TURN` | `COLLECTION_ALL_UNITS` |
| `MODIFIER_PLAYER_UNITS_ADJUST_HEAL_RELIGION_PER_TURN` | `COLLECTION_PLAYER_UNITS` |
| `MODIFIER_PLAYER_UNIT_ADJUST_HEAL_RELIGION_PER_TURN` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，每回合额外恢复量 |
| `Type` | **必写** | `ALL` = 所有单位均适用 |

> **溯源**：
> - 有实例：**神圣水域**（`BELIEF_HOLY_WATERS`，信徒信条）— 圣地区域或相邻单元格的宗教单位生命值回复 +10（`Amount=10`, `Type=ALL`，使用 `COLLECTION_ALL_UNITS`）
> - `COLLECTION_PLAYER_UNITS` / `COLLECTION_OWNER` 版本在 DB 中无实例，保留供自定义使用

---

