# modifier-religion -- 宗教类 EffectType — 城市宗教

> 分册：由 [modifier-religion.md](modifier-religion.md) 按主题拆出；覆盖 EFFECT_ADJUST_CITY_AMENITIES_FROM_RELIGION、EFFECT_ADJUST_CITY_RELIGION_EXTRA_PROMOTIONS、EFFECT_ADJUST_CITY_RELIGION_ON_CAPTURE、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_CITY_RELIGION_CONVERSION、EFFECT_CITY_REMOVE_OTHER_RELIGIONS。触发：改城市宗教效果（宜居、晋升、被俘、压力）时。

## 城市宗教

### EFFECT_ADJUST_CITY_AMENITIES_FROM_RELIGION

调整城市因拥有宗教而获得的宜居度加成（基础为每个宗教 +1 宜居度）。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_SINGLE_CITY_ADJUST_CITY_AMENITIES_FROM_RELIGION` | `COLLECTION_OWNER` |
| `MODIFIER_CITY_DISTRICTS_ADJUST_CITY_AMENITIES_FROM_RELIGION` | `COLLECTION_CITY_DISTRICTS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | `SINGLE_CITY` 版本**必写** | 整数，宜居度加成量。`CITY_DISTRICTS` 版本无此参数，按区域自动计算 |

> **溯源**（DB 中 2 个实例）：
> - **禅修**（`BELIEF_ZEN_MEDITATION`，信徒信条）— 拥有 2 个特色区域的城市 +1 宜居度（`SINGLE_CITY`, `Amount=1`）
> - **Podenco 社区**（`DISTRICT_NEIGHBORHOOD` 上的 `MODIFIER_PODENCO_NEIGHBORHOOD_AMENITIES`）— 社区 +3 宜居度（`SINGLE_CITY`, `Amount=3`，Siqi Mod 扩展内容）

---

### EFFECT_ADJUST_CITY_RELIGION_EXTRA_PROMOTIONS

城市中训练或购买的宗教单位获得额外免费晋升次数。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_SINGLE_CITY_RELIGION_EXTRA_PROMOTIONS` | `COLLECTION_OWNER` |
| `MODIFIER_SINGLE_CITY_RELIGION_EXTRA_PROMOTIONS_SCENARIO` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | 主版本**必写** | 整数，额外晋升次数。`SCENARIO` 版本无参数 |

> **溯源**：
> - 主版本 — **红衣主教：守护圣人**（`GOVERNOR_PROMOTION_CARDINAL_PATRON_SAINT`）— 此城训练的使徒/武僧初始获得 1 次额外晋升（`Amount=1`）
> - `_SCENARIO` 变体 — DB 无实例，专为剧本模式保留，不设参数

---

### EFFECT_ADJUST_CITY_RELIGION_ON_CAPTURE

单位攻占城市时，强制城市转换为占领方的主流宗教。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_UNIT_ADJUST_CITY_ON_CAPTURE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Enable` | **必写** | `1` 启用 |

> **溯源**：**征服者**（`ABILITY_CONQUISTADOR`，西班牙特色单位能力）— 攻占城市时，该城市自动转换为西班牙主流宗教。

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_CITY_RELIGION_CONVERSION

调整玩家通过宗教转换城市获得的时代得分。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_ADJUST_PLAYER_ERA_SCORE_PER_CITY_RELIGION_CONVERSION` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，每次转换的额外时代得分 |

> **溯源**：**宗教任务**（`COMMEMORATION_RELIGIOUS_QUEST`，纪念时刻/黄金时代着力点）— 每次转换城市宗教额外获得 +2 时代得分（`Amount=2`）。此 Modifier 位于 `Modifiers` 表中但未出现在任何标准参考表（BeliefModifiers 等）中，通过纪念时刻系统间接引用。

---

### EFFECT_CITY_REMOVE_OTHER_RELIGIONS

移除城市中除当前宗教外的所有其他宗教。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_CITY_REMOVE_OTHER_RELIGIONS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| （无） | — | 无参数，执行时直接清除城市中所有非主流宗教 |

> **溯源**：此 EffectType 在 Effects.csv 中标记为 `USER ADDED` + `UNTESTED`，游戏中无活跃 DB 实例。使用前需充分测试。

---

