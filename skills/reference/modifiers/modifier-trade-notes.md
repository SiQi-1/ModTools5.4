# modifier-trade -- 商路类 EffectType — 注意事项

> 分册：由 [modifier-trade.md](modifier-trade.md) 按主题拆出；覆盖 H. 无活跃实例的效果（需验证）、PER_xxx 系列效果矩阵、注意事项、作用域选择、关键区别、特殊参数、商路容量特殊变体、SIQI 前缀的 ModifierType。触发：核对无活跃实例效果、PER_ 矩阵与注意事项时。

## H. 无活跃实例的效果（需验证）

以下 EffectType 在 DynamicModifiers 中注册，但数据库中**无活跃 Modifier 实例**，且无 `GameEffectArguments` 定义。参数仅能通过命名和关联模式推断。

| EffectType | 注册 ModifierType | CollectionType | 风险 |
|---|---|---|---|
| `EFFECT_ADJUST_PLAYER_ANYONE_TRADE_TO_FAVOR` | `MODIFIER_PLAYER_ADJUST_ANYONE_TRADE_TO_FAVOR` | `COLLECTION_OWNER` | 中 — 推断参数 `Amount`（外交支持），名称含 "ANYONE" 暗示与所有文明交易相关 |
| `EFFECT_ADJUST_PLAYER_SEND_TRADE_ROUTE_FAVOR_BY_BONUS_TYPE` | `MODIFIER_PLAYER_ADJUST_SEND_TRADE_ROUTE_FAVOR_BY_BONUS` | `COLLECTION_OWNER` | 中 — 推断参数 `Amount` + `BonusType`，`BonusType` 枚举待确认 |
| `EFFECT_ADJUST_PLAYER_TOKEN_ON_TRADE_ROUTE_STARTED` | `MODIFIER_PLAYER_ADJUST_TOKEN_ON_TRADE_ROUTE_STARTED` | `COLLECTION_OWNER` | 高 — 无参数记录，推断为商路开始时获得使者 |
| `EFFECT_TRADE_ROUTE_CANCEL` | `MODIFIER_EMERGENCY_TRADE_ROUTES_CANCEL` | `COLLECTION_EMERGENCY_TRADE_ROUTES` | 高 — 两个 ModifierType 均无活跃实例，无参数记录 |
| `EFFECT_TRADE_ROUTE_CANCEL` | `MODIFIER_PLAYER_TRADE_ROUTES_CANCEL` | `COLLECTION_OWNER` | 高 — 同上 |

---

## PER_xxx 系列效果矩阵

"起源地每有一种 X 资源" vs "目的地每有一种 Y 资源"，国内 vs 国际商路，三种资源类型（加成/奢侈/战略）的交叉矩阵。

| 维度 | 国内 (Domestic) | 国际 (International) |
|------|:--:|:--:|
| 目的地奢侈资源数 | **缺失** | `PER_DESTINATION_LUXURY_RESOURCE_FOR_INTERNATIONAL` |
| 目的地战略资源数 | `PER_DESTINATION_STRATEGIC_RESOURCE_FOR_DOMESTIC` | `PER_DESTINATION_STRATEGIC_RESOURCE_FOR_INTERNATIONAL` |
| 目的地加成资源数 | **缺失**（游戏本身有此判定逻辑吗？） | **缺失** |
| 起源地加成资源数 | `PER_LOCAL_BONUS_RESOURCE_FOR_DOMESTIC` | `PER_LOCAL_BONUS_RESOURCE_FOR_INTERNATIONAL` |
| 起源地奢侈资源数 | **缺失** | `PER_LOCAL_LUXURY_RESOURCE_FOR_INTERNATIONAL` |
| 起源地战略资源数 | **缺失** | `PER_LOCAL_STRATEGIC_RESOURCE_FOR_INTERNATIONAL` |

**8 种可能组合中 5 种缺失。** 缺失的格子可通过 `EFFECT_ADJUST_TRADE_ROUTE_YIELD_FOR_DOMESTIC` 或 `EFFECT_ADJUST_TRADE_ROUTE_YIELD_FOR_INTERNATIONAL` 配合条件需求间接实现。

近年新增的 `PER_SPECIALTY_DISTRICT_FOR_DOMESTIC` 和 `PER_SPECIALTY_DISTRICT_FOR_INTERNATIONAL` 属于专业化区域维度，非资源维度，完整矩阵（国内/国际）均有覆盖。

---

## 注意事项

### 作用域选择

| CollectionType | 适用场景 | 示例 |
|---|---|---|
| `COLLECTION_OWNER` | 单城（建筑/区域附着）或单玩家全局 | 灯塔 +1 商路、民主政体同盟商路产出 |
| `COLLECTION_PLAYER_CITIES` | 全文明城市 | 纳迪尔沙国内商路产出、埃塞俄比亚资源加成 |
| `COLLECTION_ALL_CITIES` | 全局所有城市（自然奇观/世界奇观） | 帕依提提 +4 金币 |
| `COLLECTION_PLAYER_DISTRICTS` | 按区域类型累加 | 每商业中心 +1 商路 |
| `COLLECTION_MAJOR_PLAYERS` | 所有主要文明（外交/世界议会） | 贸易关系好感、一厢情愿惩罚 |
| `COLLECTION_ALLIANCE_PLAYERS` | 同盟成员 | 同盟 +1 商路 |
| `COLLECTION_ALLIANCE_TRADEROUTES` | 同盟间的商路集合 | 同盟 1 级商路产出 |
| `COLLECTION_EMERGENCY_TRADE_ROUTES` | 紧急事件相关商路集合 | 背叛紧急事件商路 buff |

### 关键区别

1. **`EFFECT_ADJUST_CITY_TRADE_ROUTE_YIELD_FOR_DOMESTIC` vs `EFFECT_ADJUST_TRADE_ROUTE_YIELD_FOR_DOMESTIC`**
   - 前者（CITY 前缀）：城市级，建筑/区域附着用。两种 ModifierType 变体（`SINGLE_CITY` / `PLAYER_CITIES_WARLORDS`）
   - 后者（无 CITY 前缀）：玩家全局。一种 ModifierType，支持 `Intercontinental` 参数

2. **`FROM_OTHERS` vs `TO_OTHERS`**
   - `FROM_OTHERS` = 其他文明通往己方的商路为**己方**提供产出（入向）
   - `TO_OTHERS` = 己方通往其他文明的商路为**对方**提供产出（出向）
   - 两者均有 `SINGLE_CITY`（`COLLECTION_OWNER`）和 `PLAYER_CITIES`（`COLLECTION_PLAYER_CITIES`）变体

3. **`PER_IMPROVEMENT_IN_TARGET` vs `PER_IMPROVEMENT_AT_LOCATION`**
   - `IN_TARGET`：同时支持 `Origin` + `Destination` 参数，可分别指定影响哪一侧
   - `AT_LOCATION`：仅支持 `Origin` 参数

4. **`EFFECT_ADJUST_TRADE_ROUTE_YIELD_CHANGE` = 商路集合级**
   - 作用于 `COLLECTION_ALLIANCE_TRADEROUTES` / `COLLECTION_EMERGENCY_TRADE_ROUTES`
   - 参数为 `AffectOrigin` / `AffectDestination`（非 `Origin` / `Destination`）

### 特殊参数

- `EFFECT_ADJUST_PLAYER_INTERNATIONAL_TRADE_ROUTE_YIELD_MODIFIER` 的 `Amount` / `YieldType` 使用**逗号分隔多值列表**（6 种产出各 50% 配 6 个 YieldType）
- `EFFECT_ADJUST_PLAYER_PROGRESS_DIFF_TRADE_BONUS` 使用 `TechCivicsPerYield` 参数（非 `Amount`）
- `EFFECT_ADJUST_PLAYER_TRADE_GAIN_TILES_EN_ROUTE` 使用 `GainTileRadius` 参数（非 `Amount`）
- `EFFECT_DIPLOMACY_ONE_SIDED_TRADES` / `EFFECT_DIPLOMACY_TRADE_RELATIONS` 参数体系完全独立，使用 `StatementKey` / `TradeBonus` 等自定义参数名
- `EFFECT_ADJUST_UNIT_TRADE_ROUTE_PLUNDER_IMMUNITY` 使用 `DomainType` 参数（`DOMAIN_LAND` / `DOMAIN_SEA`）

### 商路容量特殊变体

`EFFECT_GRANT_FOUND_FOREIGN_CITY_TRADE_ROUTE_CAPACITY` 和 `EFFECT_GRANT_GOLDEN_AGE_TRADE_ROUTE_CAPACITY` 均有独立的 EffectType（非 `EFFECT_ADJUST_TRADE_ROUTE_CAPACITY` 的子集），各有专用触发条件。

### SIQI 前缀的 ModifierType

DB 中存在多个 `MODIFIER_SIQIxxx` 变体（如 `MODIFIER_SIQI0032_CITY_TRADE_ROUTE_YIELD_PER_LOCAL_LUXURY_RESOURCE_FOR_INTERNATIONAL`），这些为社区自定义 Mod 注册的独立 ModifierType，与官方变体（`MODIFIER_PLAYER_CITIES_TRADE_ROUTE_YIELD_PER_LOCAL_xxx`）功能等价但 CollectionType 不同（`COLLECTION_OWNER` vs `COLLECTION_PLAYER_CITIES`）。使用官方命名时无需关注这些变体。
