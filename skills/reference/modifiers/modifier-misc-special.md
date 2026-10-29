# modifier-misc — 其余杂项类 EffectType — 公民/特殊加成

> 分册：由 [modifier-misc.md](modifier-misc.md) 按主题拆出；覆盖 公民与总督、EFFECT_ADJUST_ACCUMULATING_BONUS、特殊文明加成、EFFECT_ADJUST_ADDITIONAL_PILLAGING、EFFECT_ADJUST_DISABLE_SETTLING、EFFECT_ADJUST_PLAYER_BAN_CHOP、EFFECT_ADJUST_PLAYER_CAPITAL、EFFECT_ADJUST_PLAYER_PROPERTY、EFFECT_ADJUST_PLAYER_SUZERAIN_BONUS_DISABLED、EFFECT_ADJUST_PLAYER_TOKEN_ON_FIRST_MEETING、EFFECT_EXPLORE_ENTIRE_MAP、EFFECT_MOUNTAIN_PORTAL、EFFECT_RIVER_ADJACENCY、奖励授予、EFFECT_GRANT_AIR_SLOTS、EFFECT_GRANT_RELIC、特殊/系统、EFFECT_DO_NOTHING、EFFECT_TRIGGER_GAME_MECHANIC。触发：改公民总督、特殊文明加成、奖励授予时。

## 公民与总督

### EFFECT_ADJUST_ACCUMULATING_BONUS

调整政体累积加成的效果（如每回合积累的使者/外交支持增量）。`BonusType` 指定加成种类，`Increment` 为每次累积量，`Interval` 为累积间隔（回合数）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GOVERNMENT_ACCUMULATING_BONUS` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `BonusType` | `GOVERNMENTBONUS_ENVOYS` / `GOVERNMENTBONUS_FAITH_PURCHASES` / `GOVERNMENTBONUS_GOLD_PURCHASES` / `GOVERNMENTBONUS_GREAT_PEOPLE` / `GOVERNMENTBONUS_TRADE_ROUTES` 等，引用 [GovernmentBonusNames.GovernmentBonusType] |
| `Increment` | 整数，每次累积量 |
| `Interval` | 整数，累积间隔回合数 |

> **溯源**：DynamicModifiers 定义（Base `Modifiers.xml`），游戏中无活跃 DB 实例，由政体系统使用

---


## 特殊文明加成

### EFFECT_ADJUST_ADDITIONAL_PILLAGING

调整掠夺特定改良设施时的额外收益。`PlunderType` 指定收益类型（文化/科技），`ImprovementType` 指定改良设施。`Amount=15`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_ADDITIONAL_PILLAGING` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `15` |
| `ImprovementType` | `IMPROVEMENT_CAMP` / `IMPROVEMENT_MINE` / `IMPROVEMENT_PASTURE` / `IMPROVEMENT_PLANTATION` / `IMPROVEMENT_QUARRY` |
| `PlunderType` | `PLUNDER_CULTURE` / `PLUNDER_SCIENCE` |

> **溯源**：TraitModifiers — 挪威文明「维京突袭」

---

### EFFECT_ADJUST_DISABLE_SETTLING

禁用开拓者建造新城市。`Disabled=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISABLE_SETTLING` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Disabled` | `1` |

> **溯源**：DistrictModifiers — 区域「政府特区」（DISTRICT_GOVERNMENT_QUARTER）

---

### EFFECT_ADJUST_PLAYER_BAN_CHOP

禁止砍伐森林/雨林或收获资源。`NoRemove=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYERS_ADJUST_CHOP_BAN` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 值/引用 |
|---|---|
| `NoRemove` | `1` |

> **溯源**：PolicyModifiers — 政策「森林管理公约」

---

### EFFECT_ADJUST_PLAYER_CAPITAL

允许通过完成指定项目变更首都位置。`ProjectType=PROJECT_COTHON_CAPITAL_MOVE`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_CAPITAL` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `ProjectType` | `PROJECT_COTHON_CAPITAL_MOVE` |

> **溯源**：DistrictModifiers — 腓尼基特色区域「科通」（DISTRICT_COTHON）

---

### EFFECT_ADJUST_PLAYER_PROPERTY

调整自定义玩家属性值（键值对属性系统）。通过 Lua 读写可实现复杂自定义效果追踪。`PropertyName` 为自定义属性名。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PROPERTY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Key` | **必写** | 自定义字符串，Property 名（Lua 用 `GetProperty(key)` 读取） |
| `Amount` | **必写** | 通常为 `1`（Marker 标记） |

```sql
INSERT INTO Modifiers (ModifierId, ModifierType) VALUES
('MODIFIER_SIQI_{SHORT}_PROPERTY', 'MODIFIER_PLAYER_ADJUST_PROPERTY');

INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
('MODIFIER_SIQI_{SHORT}_PROPERTY', 'Key', 'SIQI_{SHORT}_MARKER'),
('MODIFIER_SIQI_{SHORT}_PROPERTY', 'Amount', '1');
```

> **用途**：政体/领袖/文明等挂载后设置 Player Property 标记，Lua 侧通过 `pPlayer:GetProperty('SIQI_{SHORT}_MARKER')` 读取判断。政体切换时 Modifier 自动卸载，Property 归 nil，无需额外清理。
>
> **溯源**：DB 中 58 个活跃实例（Siqi_Leaders_0032 广泛使用）。

---

### EFFECT_ADJUST_PLAYER_SUZERAIN_BONUS_DISABLED

禁用城邦宗主国加成。无参数，完全移除所有宗主国加成。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_SUZERAIN_BONUS_DISABLED` | `COLLECTION_OWNER` |

| 参数 |
|---|
| （无参数） |

> **溯源**：无特定上游（通用效果）

---

### EFFECT_ADJUST_PLAYER_TOKEN_ON_FIRST_MEETING

首次遇见城邦时自动获得额外使者（无需完成城邦任务）。无参数。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TOKEN_ON_FIRST_MEETING` | `COLLECTION_OWNER` |

| 参数 |
|---|
| （无参数） |

> **溯源**：Portugal DLC — 葡萄牙文明「印度之家」（若昂三世）使用

---

### EFFECT_EXPLORE_ENTIRE_MAP

揭示整个地图（立即消除全部战争迷雾）。无参数。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_EXPLORE_ENTIRE_MAP` | `COLLECTION_OWNER` |

| 参数 |
|---|
| （无参数） |

> **溯源**：ProjectCompletionModifiers — 项目「发射卫星」（PROJECT_LAUNCH_EARTH_SATELLITE）

---

### EFFECT_MOUNTAIN_PORTAL

山脉传送门——允许单位穿越山脉格子（山脉视为可通行地形）。无参数。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_MOUNTAIN_PORTAL` | `COLLECTION_OWNER` |

| 参数 |
|---|
| （无参数） |

> **溯源**：TraitModifiers — 印加文明「印加路网」/ 巴基斯坦「山岳通道」

---

### EFFECT_RIVER_ADJACENCY

为临河区域提供指定产出相邻加成。`DistrictType`=受影响的区域，`YieldType`=加成产出类型，`Description`=自定义本地化描述。`Amount=2`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_RIVER_ADJACENCY` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `2` |
| `Description` | `LOC_DISTRICT_RIVER_CULTURE` / `LOC_DISTRICT_RIVER_FAITH` / `LOC_DISTRICT_RIVER_PRODUCTION` / `LOC_DISTRICT_RIVER_SCIENCE` |
| `DistrictType` | `DISTRICT_CAMPUS` / `DISTRICT_HOLY_SITE` / `DISTRICT_INDUSTRIAL_ZONE` / `DISTRICT_THEATER` |
| `YieldType` | `YIELD_CULTURE` / `YIELD_FAITH` / `YIELD_PRODUCTION` / `YIELD_SCIENCE` |

> **溯源**：BuildingModifiers（纳斯卡线条）; DistrictModifiers（仪式场地等自定义区域）

---


## 奖励授予

### EFFECT_GRANT_AIR_SLOTS

授予单位额外航空槽位。`Amount=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_GRANT_AIR_SLOTS` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` |

> **溯源**：UnitPromotionModifiers（航母/机场晋升）; BuildingModifiers（机库/机场等建筑）

---

### EFFECT_GRANT_RELIC

授予一个圣遗物。`RelicSource=RELIC_SOURCE_TRIBAL_VILLAGE`（标记来源）。另有紧急事件版本。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GRANT_RELIC` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` |
| `RelicSource` | `RELIC_SOURCE_TRIBAL_VILLAGE` |

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_EMERGENCY_PLAYERS_GRANT_RELIC` | `COLLECTION_EMERGENCY_PLAYERS` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` |

> **溯源**：TraitModifiers — 波兰文明「立陶宛联邦」; EmergencyRewards

---


## 特殊/系统

### EFFECT_DO_NOTHING

什么都不做——空占位效果。用于需要填 ModifierType 但不产生效果的情况。无参数。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_ALLIANCE_DO_NOTHING` | `COLLECTION_OWNER` |

| 参数 |
|---|
| （无参数） |

> **溯源**：Alliances 表 — 联盟占位效果（MODIFIER_ALLIANCE_DO_NOTHING）

---

### EFFECT_TRIGGER_GAME_MECHANIC

触发游戏全局机制。`MechanicName=GenerateLandAntiquities` 生成陆地文物；`=GenerateSeaAntiquities` 生成海洋文物。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_GAME_TRIGGER_MECHANIC` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `MechanicName` | `GenerateLandAntiquities` / `GenerateSeaAntiquities` |

> **溯源**：CivicModifiers — 市政「文化遗产」/「自然历史」，完成市政后触发文物生成

---



