# modifier-misc — 其余杂项类 EffectType — 科技/文化/胜利

> 分册：由 [modifier-misc.md](modifier-misc.md) 按主题拆出；覆盖 科技与文化、EFFECT_ADJUST_CIVIC_BOOST、EFFECT_ADJUST_FREE_CIVIC_BOOST_FIRST_TRADING_POST_EACH_CIV、EFFECT_ADJUST_FREE_CIVIC_BOOST_WONDER_ERA、EFFECT_ADJUST_FREE_TECH_BOOST_FIRST_TRADING_POST_EACH_CIV、EFFECT_ADJUST_FREE_TECH_BOOST_WONDER_ERA、EFFECT_ADJUST_TECHNOLOGY_BOOST、EFFECT_GRANT_ALL_TECHNOLOGY_BOOST_BY_ERA、EFFECT_GRANT_PLAYER_RANDOM_CIVIC、EFFECT_GRANT_PLAYER_RANDOM_TECHNOLOGY、EFFECT_GRANT_PLAYER_SPECIFIC_TECHNOLOGY、EFFECT_GRANT_RANDOM_CIVIC_BOOST_BY_ERA、EFFECT_GRANT_RANDOM_CIVIC_BOOST_ON_NEW_ERA、EFFECT_GRANT_RANDOM_TECHNOLOGY_BOOST_BY_ERA、EFFECT_GRANT_RANDOM_TECHNOLOGY_BOOST_ON_NEW_ERA、科学与胜利、EFFECT_ADJUST_PLAYER_SCIENCE_VICTORY_POINTS、EFFECT_ADJUST_PLAYER_SCIENCE_VICTORY_POINTS_PER_TURN。触发：改科技、文化、科研胜利时。

## 科技与文化

### EFFECT_ADJUST_CIVIC_BOOST

调整市政鼓舞的触发进度百分比。`Amount=-40` 表示只需完成60%即可触发；`Amount=20` 表示触发后额外获得20%进度（超100%）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_CIVIC_BOOST` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `-40` / `10` / `20` / `25` |

> **溯源**：TraitModifiers（秦始皇、罗马等）; PolicyModifiers（政策「启蒙运动」）

---

### EFFECT_ADJUST_FREE_CIVIC_BOOST_FIRST_TRADING_POST_EACH_CIV

首次在每个文明的城市建立商站时，免费触发一次市政鼓舞。`Amount=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_FREE_CIVIC_BOOST_FIRST_TRADING_POST_EACH_CIV` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` |

> **溯源**：TraitModifiers — 蒙古文明「驿站」（TRAIT_CIVILIZATION_MONGOLIAN_ORDU）

---

### EFFECT_ADJUST_FREE_CIVIC_BOOST_WONDER_ERA

建造非当前时代奇观时，免费触发一次市政鼓舞。`Amount=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_FREE_CIVIC_BOOST_WONDER_ERA` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` |

> **溯源**：TraitModifiers — 秦始皇（LEADER_QIN_MANDATE_OF_HEAVEN）

---

### EFFECT_ADJUST_FREE_TECH_BOOST_FIRST_TRADING_POST_EACH_CIV

首次在每个文明的城市建立商站时，免费触发一次科技尤里卡。`Amount=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_FREE_TECH_BOOST_FIRST_TRADING_POST_EACH_CIV` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` |

> **溯源**：TraitModifiers — 蒙古文明「驿站」

---

### EFFECT_ADJUST_FREE_TECH_BOOST_WONDER_ERA

建造非当前时代奇观时，免费触发一次科技尤里卡。`Amount=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_FREE_TECH_BOOST_WONDER_ERA` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` |

> **溯源**：TraitModifiers — 秦始皇

---

### EFFECT_ADJUST_TECHNOLOGY_BOOST

调整科技尤里卡的触发进度百分比。`Amount=-40` 表示只需60%即可触发；`Amount=100` 表示直接完成该科技。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TECHNOLOGY_BOOST` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `-40` / `10` / `100` / `20` / `25` |

> **溯源**：TraitModifiers（巴比伦「Enuma Anu Enlil」、秦始皇、朝鲜等）; PolicyModifiers（政策「自由探索」）

---

### EFFECT_GRANT_ALL_TECHNOLOGY_BOOST_BY_ERA

免费获得指定时代范围内所有科技的尤里卡（不随机，全给）。`StartEraType`/`EndEraType` 划定范围。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GRANT_ALL_TECHNOLOGY_BOOST_BY_ERA` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `EndEraType` | `ERA_CLASSICAL` / `ERA_INFORMATION` |
| `StartEraType` | `ERA_ANCIENT` / `ERA_INFORMATION` |

> **溯源**：ProjectCompletionModifiers — 项目「登月计划」（PROJECT_LAUNCH_MOON_LANDING）

---

### EFFECT_GRANT_PLAYER_RANDOM_CIVIC

免费获得一项随机市政（直接完成）。`Amount=1/2`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GRANT_RANDOM_CIVIC` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` / `2` |

> **溯源**：BuildingModifiers — 莫斯科大剧院奇观（BUILDING_BOLSHOI_THEATRE）

---

### EFFECT_GRANT_PLAYER_RANDOM_TECHNOLOGY

免费获得一项随机科技（直接完成）。`Amount=1/2`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GRANT_RANDOM_TECHNOLOGY` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` / `2` |

> **溯源**：BuildingModifiers — 牛津大学奇观（BUILDING_OXFORD_UNIVERSITY）

---

### EFFECT_GRANT_PLAYER_SPECIFIC_TECHNOLOGY

免费获得一项指定的特定科技（直接完成）。`TechType` 指定科技。`MODIFIER_PLAYER_GRANT_SPECIFIC_TECHNOLOGY_GAUL` 为高卢专属。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GRANT_SPECIFIC_TECHNOLOGY` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `TechType` | `TECH_ANIMAL_HUSBANDRY` / `TECH_ASTROLOGY` / `TECH_CURRENCY` / `TECH_FLIGHT` / `TECH_MASONRY` / `TECH_MINING` / `TECH_POTTERY` / `TECH_SAILING` / `TECH_SHIPBUILDING` / `TECH_WRITING` |

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GRANT_SPECIFIC_TECHNOLOGY_GAUL` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `TechType` | `TECH_APPRENTICESHIP` |

> **溯源**：TraitModifiers（巴比伦/毛利/高卢文明）

---

### EFFECT_GRANT_RANDOM_CIVIC_BOOST_BY_ERA

随机获得指定时代范围内的 N 次市政鼓舞。`Amount=99` 表示尽可能多地给。紧急事件版本奖励参与玩家。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GRANT_RANDOM_CIVIC_BOOST_BY_ERA` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` / `99` |
| `EndEraType` | `ERA_ATOMIC` / `ERA_CLASSICAL` / `ERA_FUTURE` / `ERA_RENAISSANCE` |
| `StartEraType` | `ERA_ANCIENT` / `ERA_ATOMIC` / `ERA_MEDIEVAL` / `ERA_RENAISSANCE` |

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_EMERGENCY_PLAYERS_GRANT_RANDOM_CIVIC_BOOST_BY_ERA` | `COLLECTION_EMERGENCY_PLAYERS` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` / `2` |
| `EndEraType` | `ERA_INFORMATION` |
| `StartEraType` | `ERA_INDUSTRIAL` |

> **溯源**：TraitModifiers; EmergencyRewards（世界博览会等）

---

### EFFECT_GRANT_RANDOM_CIVIC_BOOST_ON_NEW_ERA

进入新时代时获得随机市政鼓舞。`Amount=0, ApplyImmediately=1` 表示进入新时代后立即触发。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GRANT_RANDOM_CIVIC_BOOST_ON_NEW_ERA` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `0` |
| `ApplyImmediately` | `1` |

> **溯源**：无特定上游（通用效果）

---

### EFFECT_GRANT_RANDOM_TECHNOLOGY_BOOST_BY_ERA

随机获得指定时代范围内的 N 次科技尤里卡。紧急事件版本奖励参与玩家。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GRANT_RANDOM_TECHNOLOGY_BOOST_BY_ERA` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` / `2` / `3` / `99` |
| `EndEraType` | `ERA_ATOMIC` / `ERA_CLASSICAL` / `ERA_FUTURE` / `ERA_INDUSTRIAL` / `ERA_INFORMATION` / `ERA_MEDIEVAL` / `ERA_MODERN` / `ERA_RENAISSANCE` |
| `StartEraType` | `ERA_ANCIENT` / `ERA_ATOMIC` / `ERA_CLASSICAL` / `ERA_INDUSTRIAL` / `ERA_MEDIEVAL` / `ERA_MODERN` / `ERA_RENAISSANCE` |

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_EMERGENCY_PLAYERS_GRANT_RANDOM_TECHNOLOGY_BOOST_BY_ERA` | `COLLECTION_EMERGENCY_PLAYERS` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` |
| `EndEraType` | `ERA_FUTURE` / `ERA_INFORMATION` |
| `StartEraType` | `ERA_INDUSTRIAL` |

> **溯源**：TraitModifiers; EmergencyRewards（国际宇航空间站等）

---

### EFFECT_GRANT_RANDOM_TECHNOLOGY_BOOST_ON_NEW_ERA

进入新时代时获得随机科技尤里卡。`Amount=0/1, ApplyImmediately=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GRANT_RANDOM_TECHNOLOGY_BOOST_ON_NEW_ERA` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `0` / `1` |
| `ApplyImmediately` | `1` |

> **溯源**：无特定上游（通用效果）

---


## 科学与胜利

### EFFECT_ADJUST_PLAYER_SCIENCE_VICTORY_POINTS

调整科技胜利进度点数（用于推进系外行星探索等太空项目）。`Amount` 为一次性增加的点数。ESTIMATED 级别参数。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_SCIENCE_VICTORY_POINTS` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | 整数，ESTIMATED |

> **溯源**：Expansion2 DLC — `Expansion2_Modifiers.xml` 声明，科技胜利系统

---

### EFFECT_ADJUST_PLAYER_SCIENCE_VICTORY_POINTS_PER_TURN

调整每回合自动获得的科技胜利点数。`Amount=1/3`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_SCIENCE_VICTORY_POINTS_PER_TURN` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` / `3` |

> **溯源**：ProjectCompletionModifiers — 太空竞赛项目（发射卫星/登月/火星殖民后的持续效果）

---


