# 模块化相邻加成框架 (Modular Adjacency Bonus Framework)

> 来源：Modular Adjacency Bonus (3429735059)
> 完整独立框架，支持数据驱动定义任意相邻加成逻辑

## 概述

一套数据驱动的相邻加成系统。通过 SQL 表定义"什么区域、多少环内、统计什么相邻对象、给什么产出"，Lua 端自动处理所有逻辑。核心亮点：

- **表驱动**：加成逻辑完全由 SQL 表定义，不需要为每个加成写 Lua 代码
- **多来源**：同一加成可挂在区域/特质/建筑/政策/科技/市政/政体/信仰/总督上
- **多环支持**：任意环数（含0环=自身）
- **通用统计函数**：~100 个 FROM_* 统计函数覆盖各种相邻对象
- **二进制折叠**：配合二进制属性系统动态传递数值
- **双环境**：同时支持 GamePlay 和 UserInterface 环境

## XML 配合

本系统为纯数据驱动框架，无独立 UI 面板。所有加成逻辑由 SQL 表（`Ruivo_New_Adjacency`、`Ruivo_AdjacencyType` 等）定义，Lua 端自动生成 Modifier / Requirement / Property，通过 `REQUIREMENT_PLOT_PROPERTY_MATCHES` 触发效果。相邻加成值通过 Tooltip 系统自动显示（由 `Ruivo_New_Adjacency_Text` 表控制），无需额外 XML 控件。

---

## 核心表结构

### 1. 主定义表 Ruivo_New_Adjacency

```sql
CREATE TABLE Ruivo_New_Adjacency (
    ID TEXT PRIMARY KEY NOT NULL,              -- 加成唯一ID
    DistrictType TEXT NOT NULL,                -- 目标区域类型
    ProvideType TEXT NOT NULL DEFAULT 'SelfBonus', -- 提供类型
    YieldType TEXT NOT NULL,                   -- 产出类型
    CustomArgumentValue TEXT NOT NULL DEFAULT 'NONE', -- 自定义参数值
    YieldChange FLOAT NOT NULL DEFAULT 0,      -- 每个相邻对象的加成量
    AdjacencyType TEXT NOT NULL,               -- 相邻统计类型
    CustomAdjacentObject TEXT NOT NULL DEFAULT 'NONE', -- 自定义相邻对象
    Rings INTEGER NOT NULL DEFAULT 1,          -- 环数
    DistrictModifiers BOOLEAN DEFAULT 0,       -- 是否绑在区域上
    NewMethod BOOLEAN DEFAULT 0,               -- 新方法(绑在TraitModifiers)
    ApplyForUniqueDistricts BOOLEAN DEFAULT 0, -- 是否应用于特色区域
    TraitType TEXT DEFAULT NULL,               -- 需要特定特质
    ModifierOwner TEXT NOT NULL DEFAULT 'DistrictModifiers', -- 发起者类型
    WhoIsTheOwner TEXT DEFAULT NULL,           -- 发起者具体对象
    CollectionType TEXT NOT NULL DEFAULT 'COLLECTION_PLAYER_DISTRICTS', -- 作用范围
    Only TEXT CHECK (Only IN ('Human&AI','OnlyHuman','OnlyAI')) DEFAULT 'Human&AI',
    FreeCompose BOOLEAN DEFAULT 0              -- 自由组装模式
);
```

### 2. 相邻类型注册表 Ruivo_AdjacencyType

定义每种 FROM_* 函数的元数据：

```sql
CREATE TABLE Ruivo_AdjacencyType (
    AdjacencyType TEXT PRIMARY KEY NOT NULL,   -- 函数名
    AttributeType TEXT NOT NULL,               -- 属性来源层级: Plot/City/Player/Game/District/Religion
    HasCustomAdjacentObject BOOLEAN,           -- 是否有自定义相邻对象
    Environment TEXT CHECK (IN ("GamePlay","UserInterface")), -- 运行环境
    CanDisplay BOOLEAN,                        -- 能否在UI中显示
    Tooltip TEXT
);
```

示例条目：
```sql
('FROM_RINGS_CAO_DISTRICT',     'Plot', 1, 'GamePlay', 1, '环数内的指定区域'),
('FROM_CITY_POPULATION',        'City', 0, 'GamePlay', 1, '城市人口总数'),
('FROM_PLAYER_TECHS_NUM',       'Player',0, 'GamePlay', 1, '玩家科技种类'),
('FROM_GAME_PROPERTY',          'Game',  1, 'GamePlay', 1, '游戏property'),
('FROM_UI_SELF_APPEAL',         'Plot',  0, 'UserInterface', 1, '本单元格的魅力'),
```

### 3. 提供类型注册表 Ruivo_New_Adjacency_ProvideType

用于扩展自定义 ProvideType：

```sql
CREATE TABLE Ruivo_New_Adjacency_ProvideType (
    ProvideType TEXT PRIMARY KEY NOT NULL,
    ModifierType TEXT NOT NULL,               -- 对应的 ModifierType
    ArgumentName TEXT NOT NULL DEFAULT 'NONE' -- 附加参数名
);

-- 示例：城市魅力
INSERT INTO Ruivo_New_Adjacency_ProvideType (ProvideType, ModifierType) VALUES
('SelfCityAppeal', 'MODIFIER_SINGLE_CITY_ADJUST_CITY_APPEAL');
```

### 4. 支持表

```sql
-- 二进制折叠数值表
CREATE TABLE Ruivo_BinaryList (Num INTEGER PRIMARY KEY);
INSERT INTO Ruivo_BinaryList (Num) VALUES (1),(2),(4),(8),(16),(32),(64),(128),(256),(512);

-- 自定义相邻对象名称表（用于某些无法通过游戏数据库获取名称的对象）
CREATE TABLE Ruivo_CAO (CustomAdjacentObject TEXT PRIMARY KEY, Name TEXT NOT NULL);

-- 自定义产出图标表
CREATE TABLE Ruivo_Yield_IconString (
    YieldType TEXT PRIMARY KEY, Name TEXT, IconString TEXT, TextColor TEXT
);

-- 自定义Tooltip表
CREATE TABLE Ruivo_New_Adjacency_Text (
    ID TEXT PRIMARY KEY, Tooltip TEXT NOT NULL, AddPercentChar BOOLEAN DEFAULT 0
);
```

## 架构流程

```
┌────────────────────────────────────────────────────┐
│ SQL: Ruivo_New_Adjacency (核心定义表)              │
│   ↓ 编译时自动生成 Modifier + REQ (INSERT_SQL)    │
│   ↓                                                │
│ SQL: Modifiers + Requirements + DistrictModifiers  │
│   ↓                                                │
│ Lua: 初始化 → 缓存所有配置到 RuivoAdjacencyInfo    │
│   ↓                                                │
│ 事件触发 (回合开始/区域建成)                       │
│   ↓                                                │
│ Lua: Ruivo_Refresh → 遍历所有玩家/城市/区域        │
│   ↓                                                │
│ Lua: StatsModule_For_GP → 调用 FROM_* 统计函数    │
│   ↓                                                │
│ Lua: Ruivo_Zip_SetProperty → 二进制折叠写入地块    │
│   ↓                                                │
│ REQ: REQUIREMENT_PLOT_PROPERTY_MATCHES 触发 Modifier│
└────────────────────────────────────────────────────┘
```

## Lua 核心实现

### 1. 缓存初始化

```lua
-- 从 SQL 表读取相邻类型元数据
function InitializeAdjacencyCache()
    for row in GameInfo.Ruivo_AdjacencyType() do
        RuivoAdjacencyInfo[row.AdjacencyType] = {
            AttributeType = row.AttributeType,
            Environment = row.Environment,
            CanDisplay = row.CanDisplay
        }
    end
end

-- 区域加成缓存（按目标区域分组）
Ruivo_Adjacency_Cache = { byDistrict = {} }
-- 在初始化时按 DistrictType 建立索引
for row in GameInfo.Ruivo_New_Adjacency() do
    if not Ruivo_Adjacency_Cache.byDistrict[row.DistrictType] then
        Ruivo_Adjacency_Cache.byDistrict[row.DistrictType] = {}
    end
    table.insert(Ruivo_Adjacency_Cache.byDistrict[row.DistrictType], row)
end
```

### 2. 统计函数调度

```lua
-- 函数注册表（在初始化时填充）
RuivoAdjacencyDispatch = {}
-- 通过将 FROM_* 函数名注册到表中实现动态调度：
RuivoAdjacencyDispatch['FROM_RINGS_CAO_DISTRICT'] = FROM_RINGS_CAO_DISTRICT
RuivoAdjacencyDispatch['FROM_CITY_POPULATION'] = FROM_CITY_POPULATION
-- ... 所有 FROM_* 函数

-- 通用调度核心
function CallAdjacencyFunction(AdjacencyType, CustomAdjacentObject, iX, iY, playerID, City, Rings)
    local func = RuivoAdjacencyDispatch[AdjacencyType]
    if not func then return -1 end

    local info = RuivoAdjacencyInfo[AdjacencyType]
    if not info then return -1 end

    local attr = info.AttributeType
    if attr == 'Game' then
        return func(CustomAdjacentObject)
    elseif attr == 'Plot' then
        return func(iX, iY, Rings, CustomAdjacentObject)
    elseif attr == 'District' then
        return func(iX, iY, Rings, CustomAdjacentObject)
    elseif attr == 'City' then
        return func(City, CustomAdjacentObject)
    elseif attr == 'Player' then
        return func(playerID, CustomAdjacentObject)
    elseif attr == 'Religion' then
        return func(playerID, iX, iY)
    end
    return -1
end

-- GP 环境调用
function StatsModule_For_GP(AdjacencyType, CustomAdjacentObject, iX, iY, playerID, City, Rings)
    local info = RuivoAdjacencyInfo[AdjacencyType]
    if info and info.Environment == 'GamePlay' then
        return CallAdjacencyFunction(AdjacencyType, CustomAdjacentObject, iX, iY, playerID, City, Rings)
    end
    return -1
end
```

### 3. 发起者判断系统

```lua
function IsModifierOwnerValid(ModifierOwner, WhoIsTheOwner, CollectionType, playerID, pCity)
    local pPlayer = Players[playerID]

    if ModifierOwner == 'DistrictModifiers' then return true end
    if ModifierOwner == 'TraitModifiers' then
        return Ruivo_PlayerHasTrait(WhoIsTheOwner, pPlayer)
    end
    if ModifierOwner == 'BuildingModifiers' then
        if CollectionType == 'COLLECTION_CITY_DISTRICTS' then
            return Ruivo_CityHasBuilding(WhoIsTheOwner, pCity)
        elseif CollectionType == 'COLLECTION_PLAYER_DISTRICTS' then
            return Ruivo_PlayerHasBuilding(WhoIsTheOwner, pPlayer)
        end
    end
    if ModifierOwner == 'PolicyModifiers' then
        return Ruivo_PlayerHasPolicy(WhoIsTheOwner, pPlayer)
    end
    -- ... TechnologyModifiers, CivicModifiers, GovernmentModifiers,
    --     BeliefModifiers, GovernorPromotionModifiers
    return false
end
```

各判断函数对 `WhoIsTheOwner` 的处理：
- **特质**: `HasLeaderTrait` / `HasCivilizationTrait`
- **建筑**: `pCity:GetBuildings():HasBuilding(index)` / 遍历所有城市
- **政策**: `pPlayer:GetCulture():IsPolicyActive(index)`
- **科技**: `pPlayer:GetTechs():HasTech(index)`
- **市政**: `pPlayer:GetCulture():HasCivic(index)`
- **政体**: `pPlayer:GetCulture():GetCurrentGovernment()` (UI下用pcall，GP下默认true)
- **信仰(万神殿)**: `pCityReligion:GetActivePantheon()`
- **信仰(信条)**: 遍历城市主流宗教的信条列表
- **总督升级**: `pGovernor:HasPromotion(hash)` (UI下用pcall，GP下默认true)

### 4. 模块显示判断

```lua
function CanDisplayModule(row, CivilizationType, LeaderType, playerID, pCity)
    local pPlayer = Players[playerID]

    -- Only 参数：仅人类/仅AI
    if row.Only == 'OnlyHuman' and not pPlayer:IsHuman() then return false end
    if row.Only == 'OnlyAI' and pPlayer:IsHuman() then return false end

    -- TraitType 限制
    local validTrait = true
    if row.TraitType then
        validTrait = HasCivilizationTrait(CivilizationType, row.TraitType)
                  or HasLeaderTrait(LeaderType, row.TraitType)
    end

    -- 区域Modifier 或 特质通过后，再检查发起者
    if (row.DistrictModifiers or validTrait) then
        return IsModifierOwnerValid(row.ModifierOwner, row.WhoIsTheOwner,
                                     row.CollectionType, playerID, pCity)
    end

    return false
end
```

### 5. 刷新流程

```lua
-- 遍历所有 存活+主要文明 的玩家
function Ruivo_All_Players()
    local kPlayers = PlayerManager.GetAliveMajors()
    for _, pPlayer in ipairs(kPlayers) do
        Ruivo_Single_Player(pPlayer:GetID())
    end
end

-- 遍历一个玩家的所有城市
function Ruivo_Single_Player(playerID)
    local pPlayer = Players[playerID]
    for _, pCity in pPlayer:GetCities():Members() do
        Ruivo_Single_City(pCity)
    end
end

-- 遍历一个城市的所有区域
function Ruivo_Single_City(pCity)
    local CityDistricts = pCity:GetDistricts()
    local DistrictsNum = CityDistricts:GetNumDistricts()
    for DistrictIndex = 0, DistrictsNum - 1 do
        local district = CityDistricts:GetDistrictByIndex(DistrictIndex)
        Ruivo_Single_District(district)
    end
end

-- 单个区域处理
function Ruivo_Single_District(district)
    if district and district:IsComplete() then
        local iDistrictType = district:GetType()
        local targetDistrictType = GameInfo.Districts[iDistrictType].DistrictType

        -- 获取该区域类型对应的所有加成定义
        local cachedEntries = Ruivo_Adjacency_Cache.byDistrict[targetDistrictType] or {}
        for _, row in ipairs(cachedEntries) do
            if CanDisplayModule(row, ...) then
                local iBonus = StatsModule_For_GP(
                    row.AdjacencyType, row.CustomAdjacentObject,
                    iX, iY, playerID, pCity, row.Rings)
                if iBonus >= 0 then
                    Ruivo_Zip_SetProperty(row.ID, iBonus, row.YieldChange, iX, iY)
                end
            end
        end
    end
end
```

### 6. 事件注册

```lua
function Initialize()
    -- 区域建成时刷新（开关法防止触发两次）
    Events.DistrictBuildProgressChanged.Add(Ruivo_Refresh_OnDistrictCompleted)
    -- 玩家回合开始时刷新
    Events.PlayerTurnActivated.Add(Ruivo_Refresh_OnPlayerTurnActivated)
    -- 风暴记录
    Events.RandomEventOccurred.Add(OnRandomEventOccurred)
end
Events.LoadGameViewStateDone.Add(Initialize)
```

### 7. 广度优先搜索——多环支持

```lua
function RuivoGetRingPlotIndexes(iX, iY, maxRing)
    local resultPlotIndex = {}
    local visited = {}
    local queue = {}

    local centerPlot = Map.GetPlot(iX, iY)
    local centerIndex = centerPlot:GetIndex()
    visited[centerIndex] = true
    table.insert(queue, centerIndex)

    while #queue > 0 do
        local currentIndex = table.remove(queue, 1)
        local plot = Map.GetPlotByIndex(currentIndex)
        local dist = Map.GetPlotDistance(iX, iY, plot:GetX(), plot:GetY())

        if dist < maxRing then
            local adjPlots = Map.GetAdjacentPlots(plot:GetX(), plot:GetY())
            for _, adj in ipairs(adjPlots) do
                local adjIndex = adj:GetIndex()
                if not visited[adjIndex] then
                    visited[adjIndex] = true
                    table.insert(resultPlotIndex, adjIndex)
                    table.insert(queue, adjIndex)
                end
            end
        end
    end
    return resultPlotIndex
end
```

## FROM_* 统计函数分类

### 单元格层 (Plot) — GP 环境

| 函数类别 | 示例函数 | 统计内容 |
|---|---|---|
| 本格属性 | `FROM_SELF_ROUTE` | 本格道路等级 |
| | `FROM_SELF_WORKER` | 本格在岗公民 |
| | `FROM_CLIFF` | 有无悬崖 |
| | `FROM_LATITUDE` / `FROM_POLE` | 纬度百分比 |
| | `FROM_SELF_WATER_LEVEL` | 淡水等级 |
| | `FROM_LAND_WATER_PAIR` | 相邻水陆对数 |
| | `FROM_RIVER_CROSSING` | 相邻河流面数 |
| 相邻格 | `FROM_ADJACENT_ROUTE` | 相邻道路等级总和 |
| | `FROM_ADJACENT_DISTRICT` | 相邻区域数量 |
| | `FROM_ADJACENT_RESOURCE` | 相邻资源数量 |
| | `FROM_ADJACENT_WONDERS` | 相邻奇观数量 |
| 多环 | `FROM_RINGS_ROUTE` | N环内道路等级 |
| | `FROM_RINGS_DISTRICT` | N环内区域数 |
| | `FROM_RINGS_RESOURCE` | N环内资源数 |
| 多环+自定义 | `FROM_RINGS_CAO_DISTRICT` | N环内指定区域 |
| | `FROM_RINGS_CAO_IMPROVEMENT` | N环内指定改良 |
| | `FROM_RINGS_CAO_TERRAIN` | N环内指定地形 |
| | `FROM_RINGS_CAO_FEATURE` | N环内指定地貌 |
| | `FROM_RINGS_CAO_RESOURCE` | N环内指定资源 |
| | `FROM_RINGS_CAO_RESOURCE_CLASS` | N环内某类资源 |
| | `FROM_RINGS_TYPETAG_RESOURCE` | N环内某tag资源 |
| | `FROM_RINGS_CAO_UNIT` | N环内指定单位 |

### 区域层 (District) — GP 环境

| 函数 | 统计内容 |
|---|---|
| `FROM_SELF_YIELD_FOOD` 等 | 区域自身6大产出 |
| `FROM_SELF_DISTRICT_MAX_HP` | 区域血量上限 |
| `FROM_SELF_DISTRICT_DAMAGE` | 区域受损值 |

### 城市层 (City) — GP 环境

| 函数 | 统计内容 |
|---|---|
| `FROM_CITY_POPULATION` | 城市人口 |
| `FROM_CITY_TOTAL_HOUSING` | 总住房 |
| `FROM_CITY_SURPLUS_FOOD` | 余粮 |
| `FROM_CITY_SURPLUS_AMENITIES` | 溢出宜居度 |
| `FROM_CITY_DISTRICTS_NUM` | 区域总数 |

### 玩家层 (Player) — GP 环境

| 函数 | 统计内容 |
|---|---|
| `FROM_PLAYER_TECHS_NUM` | 科技数量 |
| `FROM_PLAYER_CIVICS_NUM` | 市政数量 |
| `FROM_OUTGOING_ROUTES` | 贸易路线数 |
| `FROM_SLOT_MILITARY` 等 | 政策槽数量 |
| `FROM_PLAYER_TOTAL_UNITS` | 单位总数 |

### 全局层 (Game)

| 函数 | 统计内容 |
|---|---|
| `FROM_UNCONDITIONAL_BONUS` | 总是返回1 |
| `FROM_STORM_HAPPEND` | 本局风暴次数 |
| `FROM_STANDARDIZE_TURNS` | 标准化回合数 |
| `FROM_HIGHEST_HUMAN_YIELD` | 最高人类某产出 |

### Property 体系

| 函数 | 说明 |
|---|---|
| `FROM_PLOT_PROPERTY` | 单元格Property |
| `FROM_RINGS_PLOT_PROPERTY` | N环内单元格Property |
| `FROM_CITY_PROPERTY` | 城市Property |
| `FROM_PLAYER_PROPERTY` | 玩家Property |
| `FROM_GAME_PROPERTY` | 游戏Property |
| 对应 `_HASHED` 版本 | 哈希化的Property键名（来自Modifier） |

## ProvideType 列表

| ProvideType | 效果 | 使用的 ModifierType |
|---|---|---|
| SelfBonus | 区域自身基础产出 | MODIFIER_PLAYER_DISTRICT_ADJUST_BASE_YIELD_CHANGE |
| SelfMultiplier | 区域产出系数(%) | RUIVO_MODIFIER_PLAYER_DISTRICT_ADJUST_YIELD_MODIFIER |
| ProvideToADJ | 给相邻区域加产出 | RUIVO_MODIFIER_PLAYER_DISTRICTS_ADJUST_BASE_YIELD_CHANGE |
| SelfTourism | 旅游业绩 | RUIVO_MODIFIER_PLAYER_DISTRICT_ADJUST_TOURISM_CHANGE |
| SelfAmenity | 宜居度 | MODIFIER_PLAYER_DISTRICT_ADJUST_DISTRICT_AMENITY |
| SelfHousing | 住房 | RUIVO_MODIFIER_PLAYER_DISTRICT_ADJUST_DISTRICT_HOUSING |
| SelfLoyalty | 忠诚度 | RUIVO_MODIFIER_OWNER_CITY_ADJUST_IDENTITY_PER_TURN |
| SelfPower | 电力 | MODIFIER_SINGLE_CITY_ADJUST_FREE_POWER |
| SelfInfluence | 影响力 | MODIFIER_PLAYER_ADJUST_INFLUENCE_POINTS_PER_TURN |
| SelfFavor | 外交支持 | MODIFIER_PLAYER_ADJUST_EXTRA_FAVOR_PER_TURN |
| SelfTradeRoute | 贸易路线 | MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_CAPACITY |
| GreatPersonPoints | 伟人点 | MODIFIER_PLAYER_ADJUST_GREAT_PERSON_POINTS |
| SelfExtractResource | 战略资源产出 | MODIFIER_SINGLE_CITY_ADJUST_FREE_RESOURCE_EXTRACTION |
| SelfExtraDistrictSlot | 额外区域位 | MODIFIER_SINGLE_CITY_EXTRA_DISTRICT |
| SelfDistrictProperty | 区域属性 | RUIVO_MODIFIER_PLAYER_DISTRICT_ADJUST_PROPERTY |
| SelfCityProperty | 城市属性 | RUIVO_MODIFIER_PLAYER_CITY_ADJUST_PROPERTY |
| SelfPlayerProperty | 玩家属性 | RUIVO_MODIFIER_PLAYER_ADJUST_PROPERTY |
| SelfGameProperty | 游戏属性 | RUIVO_MODIFIER_PLAYER_GAME_ADJUST_PROPERTY |
| (自定义) | 通过 Ruivo_New_Adjacency_ProvideType 扩展 | 任意 ModifierType |

## 自定义 DynamicModifier

框架注册了一系列自制 ModifierType（支持常规产出、属性修改、修饰符挂载等）：

```sql
-- 给本城所有区域贴 modifier
('RUIVO_MODIFIER_OWNER_CITY_DISTRICTS_ATTACH_MODIFIER', 'EFFECT_ATTACH_MODIFIER', 'COLLECTION_CITY_DISTRICTS')
-- 给玩家所有区域贴 modifier
('RUIVO_MODIFIER_PLAYER_ALL_DISTRICTS_ATTACH_MODIFIER', 'EFFECT_ATTACH_MODIFIER', 'COLLECTION_PLAYER_DISTRICTS')
-- 区域属性修改
('RUIVO_MODIFIER_PLAYER_DISTRICT_ADJUST_PROPERTY', 'EFFECT_ADJUST_DISTRICT_PROPERTY', 'COLLECTION_OWNER')
-- 城市属性修改
('RUIVO_MODIFIER_PLAYER_CITY_ADJUST_PROPERTY', 'EFFECT_ADJUST_CITY_PROPERTY', 'COLLECTION_OWNER_CITY')
-- 玩家属性修改
('RUIVO_MODIFIER_PLAYER_ADJUST_PROPERTY', 'EFFECT_ADJUST_PLAYER_PROPERTY', 'COLLECTION_OWNER')
```

## 使用示例

在 SQL 中定义一条加成：

```sql
-- "剧院广场相邻1环内每个奇观+2文化"
INSERT INTO Ruivo_New_Adjacency
(ID, DistrictType, ProvideType, YieldType, YieldChange, AdjacencyType, Rings)
VALUES
('THEATER_WONDER_CULTURE', 'DISTRICT_THEATER', 'SelfBonus',
 'YIELD_CULTURE', 2, 'FROM_RINGS_WONDERS', 1);
```

无需额外 Lua 代码，框架会自动：
1. 生成 Modifier：`THEATER_WONDER_CULTURE_1` ~ `THEATER_WONDER_CULTURE_10`
2. 生成 REQ：检测 `THEATER_WONDER_CULTURE_1` 等 Property
3. 每回合统计每个剧院广场1环内的奇观数
4. 二进制折叠写入地块 Property
5. 触发对应档位的文化加成

## 注意事项

1. **特色区域支持**：`ApplyForUniqueDistricts=1` 会自动为替代的特色区域生成相同规则
2. **NewMethod**：`NewMethod=1` 将加成挂在 `TRAIT_LEADER_MAJOR_CIV` 上而非 `DistrictModifiers`（避开AI判断问题）
3. **区域建成事件触发2次**：使用开关法 (`DistrictCompletedSwitch`)
4. **pcall 处理**：政体和总督判断在 GP 下可能出错，使用 pcall 包裹，出错时默认返回 true
5. **性能**：每回合遍历所有玩家所有城市所有区域，建议只在需要时刷新
6. **环境分离**：GP 函数和 UI 函数分开注册，确保在不同环境下正确执行
