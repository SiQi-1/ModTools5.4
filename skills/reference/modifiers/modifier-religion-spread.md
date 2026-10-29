# modifier-religion -- 宗教类 EffectType — 传播/压力

> 分册：由 [modifier-religion.md](modifier-religion.md) 按主题拆出；覆盖 EFFECT_ADD_RELIGIOUS_UNIT、EFFECT_ADJUST_CITY_RELIGION_IGNORE_PRESSURE、EFFECT_ADJUST_CITY_RELIGION_PRESSURE、EFFECT_ADJUST_INQUISITION_START_CHARGES、EFFECT_ADJUST_PLAYER_TRADE_ROUTE_RELIGIOUS_PRESSURE、EFFECT_ADJUST_RELIGIOUS_SPREAD_DISTANCE、EFFECT_ADJUST_RELIGIOUS_SPREAD_STRENGTH、EFFECT_ALLIANCE_PRESSURE_FROM_NO_ALLY_RELIGION、EFFECT_ENABLE_RELIGION_AUTO_SPREAD、EFFECT_ENABLE_RELIGION_AWARDS_ENVOY_RELIGIOUS_PRESSURE、EFFECT_GRANT_PLAYER_RELIGIOUS_PRESSURE_GREAT_PERSON_ACTIVATED、EFFECT_GRANT_RELIGIOUS_PRESSURE_BURST。触发：改传教、宗教压力、传播距离/强度、宗教单位时。

## 传播/压力

### EFFECT_ADD_RELIGIOUS_UNIT

允许拥有该宗教的玩家训练指定的宗教单位。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_RELIGION_ADD_RELIGIOUS_UNIT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `UnitType` | **必写** | `UNIT_WARRIOR_MONK` 等，引用 [Units.UnitType] |

> **溯源**：武僧（`BELIEF_WARRIOR_MONKS`，信徒信条）— 可花费信仰值训练武僧，中世纪陆地战斗单位，拥有独特晋升树，只能在有寺庙的城市购买。

---

### EFFECT_ADJUST_CITY_RELIGION_IGNORE_PRESSURE

该城市免疫外来宗教压力（其他宗教无法被动传播至此城）。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_SINGLE_CITY_RELIGION_IGNORE_PRESSURE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Enable` | **必写** | `1` 启用免疫 / `0` 禁用 |

> **溯源**：**红衣主教：神之堡垒**（`GOVERNOR_PROMOTION_CARDINAL_CITADEL_OF_GOD`）— 与 `IGNORE_COMBAT` 成对挂载，该总督所在城市成为宗教安全区。

---

### EFFECT_ADJUST_CITY_RELIGION_PRESSURE

调整城市输出的宗教压力值（基准为 100）。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_SINGLE_CITY_RELIGION_PRESSURE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，城市压力输出值变化量（`100` = 基础值，`+100` = 翻倍） |

> **溯源**：**红衣主教：主教**（`GOVERNOR_PROMOTION_CARDINAL_BISHOP`）— 此城向其他城市释放的宗教压力翻倍（`Amount=100`）。

---

### EFFECT_ADJUST_INQUISITION_START_CHARGES

调整审判官初始充能次数（默认为 1 次）。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_ADJUST_INQUISITION_START_CHARGES` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，额外充能次数（`1` = 共 2 次充能） |

> **溯源**：**宗教审讯**（`POLICY_INQUISITION`，外交政策卡）— 审判官初始充能 +1（`Amount=1`），同时启动宗教审讯（可审判清除异教）。

---

### EFFECT_ADJUST_PLAYER_TRADE_ROUTE_RELIGIOUS_PRESSURE

玩家的商路施加宗教压力。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_RELIGIOUS_PRESSURE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，宗教压力值 |
| `Destination` | **必写** | `1` = 对商路目的地施加压力，`0` = 不施加 |
| `Origin` | **必写** | `1` = 对商路起始地施加压力，`0` = 不施加 |

> **溯源**：**达摩**（`TRAIT_CIVILIZATION_DHARMA`，印度文明特质）— 商路对出发地和目的地均施加 100 宗教压力（`Amount=100`, `Destination=1`, `Origin=1`）。

---

### EFFECT_ADJUST_RELIGIOUS_SPREAD_DISTANCE

调整宗教压力传播距离。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_RELIGION_ADJUST_RELIGIOUS_SPREAD_DISTANCE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `DistanceChange` | **必写** | 整数，传播距离改变量（正数增加格数） |

> **溯源**：**巡回传教士**（`BELIEF_ITINERANT_PREACHERS`，增强信条）— 宗教传播距离增加 30%（`DistanceChange=3`）。

---

### EFFECT_ADJUST_RELIGIOUS_SPREAD_STRENGTH

调整宗教传播力度（含市政/科技加成）。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_RELIGION_ADJUST_RELIGIOUS_SPREAD_STRENGTH` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `EnhancingTechType` | **必写** | `TECH_PRINTING` 等，引用 [Technologies.TechnologyType]。该科技将触发额外传播加成 |
| `SpreadMultiplier` | **必写** | 整数（百分比），基础传播倍率加成 |
| `TechEnabledSpreadMultiplier` | **必写** | 整数（百分比），拥有 `EnhancingTechType` 科技后的额外倍率加成 |

> **溯源**：**经文**（`BELIEF_SCRIPTURE`，增强信条）— 邻近城市宗教传播压力 +25%。研发印刷术后提升至 +50%（`SpreadMultiplier=25`, `TechEnabledSpreadMultiplier=25`, `EnhancingTechType=TECH_PRINTING`）。

---

### EFFECT_ALLIANCE_PRESSURE_FROM_NO_ALLY_RELIGION

在盟友领土内施加宗教压力（不论盟友是否信奉你的宗教）。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_ALLIANCE_PLAYERS_RELIGIOUS_PRESSURE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，施加的宗教压力值 |

> **溯源**：**宗教联盟 3 级效果**（联盟系统）— 对盟友领土施加 20 宗教压力（`Amount=20`），不论盟友是否信仰你的宗教。

---

### EFFECT_ENABLE_RELIGION_AUTO_SPREAD

启用宗教的自动传播（建立新城时该城自动获得此宗教）。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_RELIGION_ENABLE_AUTO_SPREAD` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Enable` | **必写** | `1` 启用自动传播 |

> **溯源**：**宗教殖民**（`BELIEF_RELIGIOUS_COLONIZATION`，增强信条）— 以此宗教为主流宗教的玩家建立新城后，城市初始便拥有此宗教（`Enable=1`）。

---

### EFFECT_ENABLE_RELIGION_AWARDS_ENVOY_RELIGIOUS_PRESSURE

城邦首次皈依此宗教时，对该城邦施加宗教压力爆发（附带使者奖励逻辑的上层效果）。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_RELIGION_ENABLE_AWARDS_ENVOY_RELIGIOUS_PRESSURE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，施加的宗教压力值 |

> **溯源**：**教皇权威**（`BELIEF_PAPAL_PRIMACY`，创立者信条）— 城邦首次皈依时对该城邦施加 200 宗教压力（`Amount=200`），同时从该城邦获得的加成增加 50%。

---

### EFFECT_GRANT_PLAYER_RELIGIOUS_PRESSURE_GREAT_PERSON_ACTIVATED

伟人激活时对周围城市施加宗教压力爆发。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_GRANT_RELIGIOUS_PRESSURE_GREAT_PERSON_ACTIVATED` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，宗教压力值。`400` 约为一次标准传教 |

> **溯源**：**梵蒂冈城**（`MINOR_CIV_VATICAN_CITY`，宗教城邦）— 伟人激活时对周围城市施加 400 宗教压力（`Amount=400`）。仅在 **New Frontier (Expansion2_DLC)** 中可用。

---

### EFFECT_GRANT_RELIGIOUS_PRESSURE_BURST

对一组城市施加一次宗教压力爆发（常用于紧急事件奖励）。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_EMERGENCY_CITIES_EXERT_RELIGIOUS_PRESSURE` | `COLLECTION_EMERGENCY_CITIES` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，宗教压力值 |
| `Range` | **必写** | 整数，影响范围（格数） |

> **溯源**：**宗教紧急事件奖励**（紧急事件系统）— 目标城市向 9 格范围内的城市施加 250 宗教压力（`Amount=250`, `Range=9`）。此效果依赖 `COLLECTION_EMERGENCY_CITIES`，仅在紧急事件上下文中生效。

---

