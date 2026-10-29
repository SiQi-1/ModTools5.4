# modifier-misc — 其余杂项类 EffectType — 环境/事件

> 分册：由 [modifier-misc.md](modifier-misc.md) 按主题拆出；覆盖 环境与生态、EFFECT_ACTIVATE_VOLCANOES、EFFECT_ADJUST_CO2_GENERATION_REDUCTION、EFFECT_ADJUST_GLOBAL_WMD_STOCKPILE、EFFECT_ADJUST_PLAYER_WMD_COUNT、EFFECT_ADJUST_PLAYER_WMD_MAINTENANCE_MODIFIER、EFFECT_ADJUST_PREVENT_STRUCTURAL_DAMAGE、EFFECT_MAP_REMOVE_CLIFFS_IN_DIRECTION、EFFECT_ADD_PLAYER_SEQUESTERED_CARBON、紧急事件、EFFECT_PLAYER_SEND_GOLD_TO_EMERGENCIES_OF_TYPE、随机事件与蛮族/村庄、EFFECT_ADJUST_GAME_REALISM_SETTING、EFFECT_ADJUST_PLAYER_RANDOM_CIVIC_BOOST_GOODY_HUT、EFFECT_ADJUST_PLAYER_RANDOM_EVENT_AVOID、EFFECT_ADJUST_PLAYER_RANDOM_TECHNOLOGY_BOOST_GOODY_HUT、EFFECT_ADJUST_RANDOM_EVENT_MODIFIED_DAMAGE_OPPOSING_PLAYER。触发：改环境生态、紧急事件、蛮族村庄时。

## 环境与生态

### EFFECT_ACTIVATE_VOLCANOES

激活游戏中所有火山为活跃状态（天启模式内容，由 MODIFIER_GAME_SET_ACTIVE_VOLCANOES 在游戏模式选择时触发）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_GAME_SET_ACTIVE_VOLCANOES` | `COLLECTION_OWNER` |

| 参数 |
|---|
| （无参数） |

> **溯源**：天启模式（MEGADISASTERS_MODE）— `GranColombia_Maya_RandomEvents_MODE.xml`，无数据库 ModifierId 实例

---

### EFFECT_ADJUST_CO2_GENERATION_REDUCTION

减少特定资源消耗方式产生的CO2排放量百分比。`Amount=50` 表示减少50%排放。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_CO2_GENERATION_REDUCTION` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `50` |
| `ResourceUsageType` | `RESOURCE_USAGE_UNIT` |

> **溯源**：通用效果（`UNIT_CO2_REDUCTION` ModifierId）；另见于政策「二次攻击能力」

---

### EFFECT_ADJUST_GLOBAL_WMD_STOCKPILE

调整全球大规模杀伤武器储备量。`PLAYERS_EQUALIZE_WMD_COUNTS` 平衡所有玩家；`PLAYER_TARGET_WMD_BAN`（`TargetOnly=1, Amount=0`）禁止特定目标持有WMD。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYERS_ADJUST_WMD_STOCKPILE` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `0` |
| `TargetOnly` | `1` |

> **溯源**：紧急事件系统（难民援助/军事援助请求）

---

### EFFECT_ADJUST_PLAYER_WMD_COUNT

为玩家创建指定类型的WMD。`Type=WMD_NUCLEAR_DEVICE` 创建核装置，`Type=WMD_THERMONUCLEAR_DEVICE` 创建热核装置。项目完成时触发。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CREATE_WMD` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` |
| `Type` | `WMD_NUCLEAR_DEVICE` / `WMD_THERMONUCLEAR_DEVICE` |

> **溯源**：ProjectCompletionModifiers — 项目「建造核装置」/「建造热核装置」

---

### EFFECT_ADJUST_PLAYER_WMD_MAINTENANCE_MODIFIER

调整WMD维护费用的百分比。`Amount=50` 表示维护费降低50%。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_WMD_MAINTENANCE_MODIFIER` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `50` |

> **溯源**：PolicyModifiers — 政策「二次攻击能力」（POLICY_SECOND_STRIKE_CAPABILITY）

---

### EFFECT_ADJUST_PREVENT_STRUCTURAL_DAMAGE

防止建筑和区域因自然灾害（洪水、火山等）受到结构性损坏。`Prevent=1` 启用。注意 ModifierType 中 `PREVENET` 为游戏保留的拼写错误。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_GOVERNOR_ADJUST_PREVENET_STRUCTURAL_DAMAGE` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Prevent` | `1` |

> **溯源**：GovernorPromotionModifiers — 总督「加固者」（防损专员晋升）

---

### EFFECT_MAP_REMOVE_CLIFFS_IN_DIRECTION

在指定半径内移除悬崖地形，使海军单位可穿越。`Radius=1` 表示1格半径。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_MAP_REMOVE_CLIFFS_IN_DIRECTION` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Radius` | `1` |

> **溯源**：BuildingModifiers — 建筑「航海学校」（BUILDING_NAVIGATION_SCHOOL，葡萄牙特色）

---

### EFFECT_ADD_PLAYER_SEQUESTERED_CARBON

为玩家添加封存碳的量（抵消CO2排放）。`Amount=50000` 表示一次性封存50000碳。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADD_SEQUESTERED_CARBON` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `50000` |

> **溯源**：ProjectCompletionModifiers — 项目「碳捕集」（PROJECT_CARBON_RECAPTURE）

---


## 紧急事件

### EFFECT_PLAYER_SEND_GOLD_TO_EMERGENCIES_OF_TYPE

向指定类型的紧急事件自动发送金钱援助。`EmergencyType` 可选 `EMERGENCY_SEND_AID`（援助金）或 `EMERGENCY_SEND_MILITARY_AID`（军事援助）。`Amount=200`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_SEND_GOLD_TO_EMERGENCIES_OF_TYPE` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `200` |
| `EmergencyType` | `EMERGENCY_SEND_AID` / `EMERGENCY_SEND_MILITARY_AID` |

> **溯源**：PolicyModifiers — 政策「提供援助」（POLICY_SEND_AID）

---


## 随机事件与蛮族/村庄

### EFFECT_ADJUST_GAME_REALISM_SETTING

设置游戏的真实感/灾难等级（`REALISM_SETTING_MEGADISASTERS` 大灾变或 `REALISM_SETTING_APOCALYPSE` 天启模式）。由游戏模式选择时触发。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_GAME_SET_REALISM_SETTING` | `COLLECTION_OWNER` |

| 参数 |
|---|
| （无参数） |

> **溯源**：天启模式（MEGADISASTERS_MODE）— `GranColombia_Maya_RandomEvents_MODE.xml`，无数据库实例

---

### EFFECT_ADJUST_PLAYER_RANDOM_CIVIC_BOOST_GOODY_HUT

从村庄/被征服城市获得随机市政鼓舞。`Source=CAPTURED_CITY` 表示来源为征服城市。`Amount=1/2`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GRANT_RANDOM_CIVIC_BOOST_GOODY_HUT` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` / `2` |
| `Source` | `CAPTURED_CITY` |

> **溯源**：无固定上游（通过 Lua 脚本或特定文明特性触发）

---

### EFFECT_ADJUST_PLAYER_RANDOM_EVENT_AVOID

避免特定类型的随机事件/自然灾害发生在自己的领土上。`RandomEventType` 指定要避开的灾害类型。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_AVOID_RANDOM_EVENT` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `RandomEventType` | `RANDOM_EVENT_FLOOD_1000_YEAR` / `RANDOM_EVENT_FLOOD_MAJOR` / `RANDOM_EVENT_FLOOD_MODERATE` |

> **溯源**：BuildingModifiers — 建筑「大浴场」（BUILDING_GREAT_BATH），避免洪水事件

---

### EFFECT_ADJUST_PLAYER_RANDOM_TECHNOLOGY_BOOST_GOODY_HUT

从村庄/被征服城市获得随机科技尤里卡。`Source=CAPTURED_CITY`。`Amount=1/2`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GRANT_RANDOM_TECHNOLOGY_BOOST_GOODY_HUT` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` / `2` |
| `Source` | `CAPTURED_CITY` |

> **溯源**：无固定上游（通用效果）

---

### EFFECT_ADJUST_RANDOM_EVENT_MODIFIED_DAMAGE_OPPOSING_PLAYER

调整特定随机事件对敌方玩家造成的伤害。`Amount=100` 表示+100%伤害。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_RANDOM_EVENT_MODIFIED_DAMAGE_OPPOSING_PLAYER` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `100` |
| `RandomEventType` | `RANDOM_EVENT_BLIZZARD_CRIPPLING` / `RANDOM_EVENT_BLIZZARD_SIGNIFICANT` / `RANDOM_EVENT_HURRICANE_CAT_4` / `RANDOM_EVENT_HURRICANE_CAT_5` |

> **溯源**：TraitModifiers — 努比亚（TA_SETI）/ 俄罗斯（MOTHER_RUSSIA）领袖特性

---


