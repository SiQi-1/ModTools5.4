# modifier-misc — 其余杂项类 EffectType — 注意事项

> 分册：由 [modifier-misc.md](modifier-misc.md) 按主题拆出；覆盖 注意事项、命名特例、无数据库实例的 EffectType、相似效果对比、游戏模式（MODE）发现、特殊参数索引、GovernmentBonus 类型完整列表、EraType 标准值、RandomEventType 已知值、WMD 类型、PlunderType、RouteType。触发：实现前核对杂项通用注意点时。

## 注意事项

### 命名特例

- **`EFFECT_ADJUST_PREVENT_STRUCTURAL_DAMAGE`** — ModifierType 拼写为 `MODIFIER_GOVERNOR_ADJUST_PREVENET_STRUCTURAL_DAMAGE`（`PREVENT` 误拼为 `PREVENET`），为游戏内部保留错误，引用时需原样使用。
- **`EFFECT_ADJUST_PLAYER_FEAUTE_REQUIRED_FOR_SPECIALTY_DISTRICTS`** — `FEAUTE` 实为 `FEATURE` 的法语拼写遗留，参数名正确为 `FeatureType`，但 EffectType/ModifierType 名称保持游戏原始拼写。
- **布尔型参数命名多样**：`Disable` / `Disabled` / `Enable` / `NoPenalties` / `NoRemove` / `NoHousing` / `HasBonus` / `CanPurchase` / `Prevent` / `ImmediateTradingPost`，用途相似但命名不同，使用时需查看具体实例中的参数名。
- **`EFFECT_ADJUST_TRAIT_AMENITY`** — 名含 `TRAIT` 但实际可通用于任何来源的宜居度调整，不限于领袖特性。

### 无数据库实例的 EffectType

以下 EffectType 在 DynamicModifiers 中注册但 Modifiers 表中无实例（效果由游戏硬编码或 Lua 调用）：

| EffectType | 声明位置 | 说明 |
|---|---|---|
| `EFFECT_ACTIVATE_VOLCANOES` | GranColombia_Maya DLC | 天启模式激活火山 |
| `EFFECT_ADJUST_GAME_REALISM_SETTING` | GranColombia_Maya DLC | 天启模式灾难等级设定 |
| `EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_CURRENT_CIVIC` | Expansion1/2 DLC | 黑暗时代追赶 |
| `EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_CURRENT_TECH` | Expansion1/2 DLC | 黑暗时代追赶 |
| `EFFECT_ADJUST_PLAYER_CULTURAL_IDENTITY_PRESSURE_RADIUS_FROM_CAPITAL` | Expansion1/2 DLC | 身份压力半径 |
| `EFFECT_ADJUST_HEAL_CHARGES` | Base + DLC | 治疗/传播充能 |
| `EFFECT_GRANT_RANDOM_BASE_PROMOTION` | Base + GranColombia DLC | 随机基础晋升 |
| `EFFECT_ADD_BELIEF` | Base | 添加信条（Lua 调用） |
| `EFFECT_ADJUST_DISABLE_PATRONAGE` | Expansion1/2 DLC | 禁用伟人赞助 |
| `EFFECT_ADJUST_BONUS_RATE` | Base | 政体加成倍率 |
| `EFFECT_ADJUST_PLAYER_BID_COST_MODIFIER` | Expansion2 DLC | 世博会竞标费用 |
| `EFFECT_ADJUST_PLAYER_GOLD_INTEREST_PERCENT` | Base | 国库利率 |
| `EFFECT_ADJUST_PLAYER_SCIENCE_VICTORY_POINTS` | Expansion2 DLC | 科技胜利点数 |
| `EFFECT_ADJUST_ACCUMULATING_BONUS` | Base | 政体积蓄加成 |

### 相似效果对比

| 效果组 | 说明 |
|---|---|
| `ADJUST_TECHNOLOGY_BOOST` vs `ADJUST_CIVIC_BOOST` | 镜像效果，参数完全相同（`Amount`），前者尤里卡，后者鼓舞 |
| `*_WONDER_ERA` 系列 | 建造其他时代奇观给鼓舞/尤里卡/生产力加成三组不同效果 |
| `GRANT_RANDOM_*_BOOST_BY_ERA` vs `GRANT_RANDOM_*_BOOST_ON_NEW_ERA` | 前者可指定时代范围，后者进入新时代时触发 |
| `GRANT_PLAYER_RANDOM_TECHNOLOGY` vs `GRANT_PLAYER_SPECIFIC_TECHNOLOGY` | 前者随机，后者指定 `TechType` |
| `GRANT_ALL_TECHNOLOGY_BOOST_BY_ERA` vs `GRANT_RANDOM_TECHNOLOGY_BOOST_BY_ERA` | 前者全给，后者随机 N 个 |
| `ERA_SCORE_PER_*` 系列 | 全用 `Amount` 参数，仅触发条件不同 |
| `ADJUST_ATTACKER/DEFENDER_STRENGTH_MODIFIER` | 镜像效果，仅用于紧急事件 |
| `ADJUST_CORPS_ARMY_MODIFIED_STRENGTH` vs `ADJUST_CORPS_ARMY_PREREQ` | 前者战斗力加成，后者前置解锁，共用 `Corps`/`Domain` |
| `ADJUST_WAR_WEARINESS` | `Domestic`/`Enemy`/`Overall` 三个布尔参数分别控制 |

### 游戏模式（MODE）发现

- **天启模式（Apocalypse）** — `GranColombia_Maya` DLC：新增 `EFFECT_ACTIVATE_VOLCANOES`、`EFFECT_ADJUST_GAME_REALISM_SETTING`
- **秘密结社（Secret Societies）** — `Ethiopia` DLC：定义于 `Ethiopia_SecretSocieties_MODE.xml`，包含吸血鬼、炼金术士、夜莺、密涅瓦猫头鹰四个结社
- **英雄传说（Heroes）** — `Babylon` DLC：定义于 `Babylon_Heroes_MODE.xml`
- **戏剧时代（Dramatic Ages）** — `Byzantium_Gaul` DLC：定义于 `Byzantium_Gaul_DramaticAges_MODE.xml`
- **僵尸防御（Zombie Defense）** — `Portugal` DLC：定义于 `Portugal_GameEffects_MODE.xml`

### 特殊参数索引

| 参数 | Enum/来源 | 使用于 |
|---|---|---|
| `BonusType` | GovernmentBonus 枚举 | `EFFECT_ADJUST_FLAT_BONUS` |
| `EmergencyType` | EmergencyAlliances 枚举 | `EFFECT_PLAYER_SEND_GOLD_TO_EMERGENCIES_OF_TYPE` |
| `MechanicName` | 硬编码字符串 | `EFFECT_TRIGGER_GAME_MECHANIC` |
| `RandomEventType` | RandomEvents 枚举 | 随机事件相关效果 |
| `ResourceUsageType` | ResourceUsageType 枚举 | `EFFECT_ADJUST_CO2_GENERATION_REDUCTION` |
| `RouteType` | Routes.RouteType | `EFFECT_GRANT_ROUTE_IN_RADIUS` |
| `Source` / `SourceType` | 外交能见度来源枚举 | `EFFECT_ADD_DIPLO_VISIBILITY` |
| `PlunderType` | `PLUNDER_CULTURE` / `PLUNDER_SCIENCE` | `EFFECT_ADJUST_ADDITIONAL_PILLAGING` |
| `Corps` | `1`=军团 / `0`=军队 | 军团/军队相关效果 |
| `Domain` | `DOMAIN_LAND` / `DOMAIN_SEA` | 军团/军队相关效果 |
| `Offense` | `0`=防御 / `1`=进攻 | `EFFECT_ADJUST_PLAYER_SPY_BONUS` |
| `Description` | LOC 字符串 | `EFFECT_RIVER_ADJACENCY` |

### GovernmentBonus 类型完整列表

| BonusType | 含义 |
|---|---|
| `GOVERNMENTBONUS_COMBAT_EXPERIENCE` | 战斗经验 |
| `GOVERNMENTBONUS_DISTRICT_PRODUCTION` | 区域生产力 |
| `GOVERNMENTBONUS_ENVOYS` | 使者 |
| `GOVERNMENTBONUS_FAITH_PURCHASES` | 信仰购买折扣 |
| `GOVERNMENTBONUS_GOLD_PURCHASES` | 金币购买折扣 |
| `GOVERNMENTBONUS_GREAT_PEOPLE` | 伟人点数 |
| `GOVERNMENTBONUS_TRADE_ROUTES` | 商路容量 |
| `GOVERNMENTBONUS_UNIT_PRODUCTION` | 单位生产力 |
| `GOVERNMENTBONUS_WONDER_CONSTRUCTION` | 奇观建造 |

### EraType 标准值

`ERA_ANCIENT` / `ERA_CLASSICAL` / `ERA_MEDIEVAL` / `ERA_RENAISSANCE` / `ERA_INDUSTRIAL` / `ERA_MODERN` / `ERA_ATOMIC` / `ERA_INFORMATION` / `ERA_FUTURE`

### RandomEventType 已知值

`RANDOM_EVENT_FLOOD_1000_YEAR` / `RANDOM_EVENT_FLOOD_MAJOR` / `RANDOM_EVENT_FLOOD_MODERATE` / `RANDOM_EVENT_BLIZZARD_CRIPPLING` / `RANDOM_EVENT_BLIZZARD_SIGNIFICANT` / `RANDOM_EVENT_HURRICANE_CAT_4` / `RANDOM_EVENT_HURRICANE_CAT_5`

### WMD 类型

`WMD_NUCLEAR_DEVICE`（核装置） / `WMD_THERMONUCLEAR_DEVICE`（热核武器）

### PlunderType

`PLUNDER_CULTURE`（掠夺文化） / `PLUNDER_SCIENCE`（掠夺科技）

### RouteType

`ROUTE_ANCIENT_ROAD`（古道） / `ROUTE_MEDIEVAL_ROAD`（中世纪道路） / `ROUTE_INDUSTRIAL_ROAD`（工业道路） / `ROUTE_MODERN_ROAD`（现代道路）
