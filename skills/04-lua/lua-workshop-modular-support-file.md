# 模块化共享 Support 文件（来源：工坊 873246701）

## 做什么
将共享的数据获取、计算、缓存逻辑提取到一个独立的 `.lua` 文件（如 `TradeSupport.lua`），供多个 UI Context 文件通过 `include()` 引入，避免代码重复。该文件本身不包含 UI 控件引用，只定义纯数据函数。

## 如何挂载到官方UI

Support 文件本身不挂载到 UI——它被其他 UI 文件 `include()` 后，所有函数和变量注入到 include 方的全局作用域中。

## 关键 Lua 代码

### Support 文件结构

```lua
-- TradeSupport.lua — 无 UI 控件的纯数据层

-- ==========================================
-- 常量定义（全局，供所有 include 方使用）
-- ==========================================
SORT_BY_ID = {
    FOOD = 1, PRODUCTION = 2, GOLD = 3,
    SCIENCE = 4, CULTURE = 5, FAITH = 6,
    TURNS_TO_COMPLETE = 7,
}

-- ==========================================
-- 缓存系统
-- ==========================================
local m_Cache = {}

function CacheRoutesInfo(tRoutes)
    -- 填充缓存
end

function CacheEmpty()
    m_Cache = {}
end

-- ==========================================
-- 产出计算函数
-- ==========================================
function GetYieldsForOriginCity(routeInfo, buildTooltip, checkCache)
    -- 从 TradeManager 获取原始产出，计算/缓存后返回
end

function GetYieldForOriginCity(routeInfo, yieldIndex, buildTooltip, checkCache)
    -- 单个产出值查询
end

-- ==========================================
-- 排序功能
-- ==========================================
function SortTradeRoutes(tradeRoutes, sortSettings)
    -- 根据多级排序设置返回有序列表
end

function InsertSortEntry(sortByID, sortOrder, sortSettings)
    -- 插入排序条目到设置表
end

-- ==========================================
-- 辅助函数
-- ==========================================
function CanPossiblyTradeWithPlayer(player1, player2)
    -- 判断两个玩家是否可以交易
end

function FormatYieldText(yieldIndex, yieldAmount)
    -- 格式化产出文本：+15[ICON_Food]
end

-- ==========================================
-- 跟踪子系统初始化
-- ==========================================
function TradeSupportTracker_Initialize()
    -- 注册游戏事件，跟踪路线变化
    Events.UnitOperationStarted.Add(handler)
    Events.UnitOperationsCleared.Add(handler)
    Events.PlayerTurnActivated.Add(handler)
end

function TradeSupportAutomater_Initialize()
    -- 注册自动化逻辑
    Events.PlayerTurnActivated.Add(autoRenewHandler)
end
```

### include 方调用

```lua
-- TradeOverview.lua（UI Context 文件）
include("TradeSupport");       -- 引入所有全局函数和变量

-- 直接使用 Support 文件中定义的函数
m_FinalTradeRoutes = SortTradeRoutes(m_FinalTradeRoutes, sortSettings);

-- 使用的常量
local yieldText = FormatYieldText(yieldIndex, yieldValue);

-- 初始化子系统
TradeSupportTracker_Initialize();
```

### 多文件共享

同一个 Support 文件可以被多个 UI Context 同时 include：

```lua
-- TradeRouteChooser.lua
include("TradeSupport");
-- 同样可以调用 GetYieldsForOriginCity()、SortTradeRoutes()、FormatYieldText() 等

-- TradeOriginChooser.lua
include("TradeSupport");
-- 同样可以调用 CanPossiblyTradeWithPlayer() 等
```

**注意**：include 会导致 Support 文件中的代码在每个引用方各自执行一次。因此 local 变量（如 `m_Cache`）在每个 Context 中是独立的实例。如果需要跨 Context 共享数据，应使用 LuaEvents 或 PlayerConfigurations。

### 带可选缓存的 Getter 函数模式

```lua
function GetYieldForOriginCity(routeInfo, yieldIndex, buildTooltip, checkCache)
    -- 参数默认值
    if buildTooltip == nil then buildTooltip = false end
    if checkCache == nil then checkCache = useCache end

    if checkCache then
        local key = GetRouteKey(routeInfo)
        return Cached_GetYieldForOriginCity(key, yieldIndex)
    else
        -- 实时计算（不便用缓存时）
        local tradeManager = Game.GetTradeManager();
        local kRouteYield = tradeManager:CalculateOriginYieldFromPotentialRoute(...);
        local kPathYield = tradeManager:CalculateOriginYieldFromPath(...);
        -- ... 计算并返回
        return total, tooltip
    end
end
```

## 缓存设计

### 缓存结构

```lua
m_Cache = {
    TurnBuilt = 10,                              -- 缓存构建的回合数
    ["0_5_3_12"] = {                             -- 每个路线一个键
        Yields = {[FOOD]=3, [PROD]=2, ...},
        OriginYieldValues = {...},
        DestinationYieldValues = {...},
        NetOriginYield = 15,
        HasTradingPost = true,
        HasActiveRoute = true,
        -- ...
    },
    Players = {
        [3] = {
            HasActiveRoute = true,
            VisibilityIndex = 2,
            Icon = {x, y, sheet, tooltip},
            Colors = {back, front, darker, brighter},
        }
    }
}
```

### 缓存 Touch 机制（惰性填充）

```lua
function CacheTouchRoute(routeCacheKey)
    if m_Cache[routeCacheKey] == nil then
        print("CACHE MISS for routeKey: " .. routeCacheKey)
        CacheRoute(CacheKeyToRouteInfo(routeCacheKey));
    end
end

function Cached_GetYieldForOriginCity(routeCacheKey, yieldIndex)
    CacheTouchRoute(routeCacheKey)   -- 缺失时自动填充
    return m_Cache[routeCacheKey].OriginYieldValues[yieldIndex]
end
```

### 缓存失效

```lua
function CacheEmpty()
    if m_Cache.TurnBuilt ~= nil then
        m_Cache = {}
    end
end

-- 何时清空缓存：
-- 1. 设置变更时
-- 2. 回合变化时（Events.LocalPlayerTurnEnd）
-- 3. 政策变化时
```

## 数据刷新机制

Support 文件本身不驱动刷新——它只是数据提供层。刷新由 UI 文件决定：UI 刷新时调用 Support 文件的 Getter 函数，Getter 函数内部检查缓存是否有效。

## 应用场景

- 多个 UI 面板需要访问相同的游戏数据
- 复杂的产出计算逻辑（贸易路线、城市产出等）
- 排序/过滤/分组引擎
- 跟踪系统（路线状态、单位自动化）

## XML 配合

### 涉及的关键 XML 文件

| 文件 | 路径（相对于 Mod 根目录） | 用途 |
|------|--------------------------|------|
| `TradeOverview.xml` | `UI/TradeOverview.xml` | 主面板 XML，调用 Support 文件的排序/过滤/产出函数 |
| `TradeRouteChooser.xml` | `UI/Choosers/TradeRouteChooser.xml` | 路由选择面板，调用 Support 文件的产出计算函数 |
| `TradeOriginChooser.xml` | `UI/Choosers/TradeOriginChooser.xml` | 起点选择面板，调用 Support 文件的 CanPossiblyTrade 等函数 |

### 核心控件 ID 对照表（按调用 Support 函数分组）

| 控件 ID | 类型 | 所在文件 | 调用的 Support 函数 |
|---------|------|---------|-------------------|
| **产出计算调用者** | | | |
| `OriginYieldFoodLabel` ~ `OriginYieldFaithLabel` | Label | TradeOverview.xml (RouteInstance) | `GetYieldForOriginCity()` — 起点城市 6 种产出 |
| `DestinationYieldFoodLabel` ~ `DestinationYieldFaithLabel` | Label | TradeOverview.xml (RouteInstance) | `GetYieldForDestinationCity()` — 终点城市 6 种产出 |
| `OriginResourceList` | Stack | TradeRouteChooser.xml | `GetYieldsForOriginCity()` — 路线选择面板起始资源列表 |
| `DestinationResourceList` | Stack | TradeRouteChooser.xml | `GetYieldsForOriginCity()` — 路线选择面板目标资源列表 |
| **排序/过滤调用者** | | | |
| `FoodSortButton` / `ProductionSortButton` / `GoldSortButton` / `ScienceSortButton` / `CultureSortButton` / `FaithSortButton` / `TurnsToCompleteSortButton` | GridButton | TradeOverview.xml | `InsertSortEntry()` + `SortTradeRoutes()` |
| `OverviewFilterPulldown` | PullDown | TradeOverview.xml | `FilterRoutes()` — 目标文明过滤 |
| `OverviewGroupByPulldown` | PullDown | TradeOverview.xml | `GroupRoutes()` — 分组方式 |
| `DestinationFilterPulldown` | PullDown | TradeRouteChooser.xml | `FilterRoutes()` — 路线选择面板过滤 |
| **缓存相关** | | | |
| `RouteLabel` | Label | TradeOverview.xml (RouteInstance) | `CacheTouchRoute()` — 路线键 |
| `TurnsToComplete` | Label | TradeOverview.xml (RouteInstance) | `GetTurnsRemaining()` |
| `TradingPostIcon` | Label | TradeOverview.xml | `HasTradingPost()` |
| `TourismBonusPercentage` | Label | TradeOverview.xml | `GetTourismBonus()` |
| **路线数据** | | | |
| `OriginCivIcon` / `DestinationCivIcon` | Image | TradeOverview.xml (RouteInstance) | `GetCivIcon()` — 文明图标 |
| `RouteCountLabel` | Label | TradeOverview.xml (HeaderInstance) | `GetActiveRoutesCount()` |
| `RepeatRouteCheckbox` | CheckBox | TradeRouteChooser.xml | 重复路线设置 |
| `FromTopSortEntryCheckbox` | CheckBox | TradeRouteChooser.xml | 从顶部排序条目 |
| **起点/终点选择** | | | |
| `BeginRouteButton` | GridButton | TradeRouteChooser.xml | `CanPossiblyTradeWithPlayer()` |
| `ChangeOriginCityButton` | GridButton | TradeOriginChooser.xml | `CanPossiblyTradeWithPlayer()` |
| `CityScrollPanel` / `CityStack` | ScrollPanel / Stack | TradeOriginChooser.xml | `GetValidOriginCities()` |

### 可复用 XML 模板（使用 Support 产出的行 Instance）

```xml
<Instance Name="YieldsRowInstance">
    <Container ID="Top" Size="485,78" Offset="10,0">
        <GridButton ID="GridButton" Size="parent,parent">
            <Label ID="RowLabel" Anchor="L,T" Offset="33,10" Style="FontFlair16" TruncateWidth="300"/>

            <!-- 产出列：由 Support 文件填充 -->
            <Stack ID="YieldsStack" StackGrowth="Down" Anchor="C,T" Offset="0,31" StackPadding="4">
                <Stack ID="OriginYields" Anchor="C,T" StackGrowth="Right" StackPadding="2">
                    <Container Size="48,20">
                        <Label ID="OriginYieldFoodLabel" Color="Food" Anchor="C,C" Style="FontNormal14" String="+15[Icon_Food]"/>
                    </Container>
                    <Container Size="48,20">
                        <Label ID="OriginYieldProductionLabel" Color="Production" Anchor="C,C" Style="FontNormal14" String="+15[Icon_Production]"/>
                    </Container>
                    <Container Size="48,20">
                        <Label ID="OriginYieldGoldLabel" Color="Gold" Anchor="C,C" Style="FontNormal14" String="+15[Icon_Gold]"/>
                    </Container>
                    <!-- ... Science, Culture, Faith ... -->
                </Stack>

                <Stack ID="DestinationYields" Anchor="C,T" StackGrowth="Right" StackPadding="2">
                    <!-- 与 OriginYields 结构相同，ID 前缀为 DestinationYield -->
                </Stack>
            </Stack>

            <!-- 辅助数据 -->
            <Label ID="TurnsToComplete" Anchor="R,T" Style="FontNormal16" String="00"/>
            <Image ID="OriginCivIconBacking" Anchor="L,B" Size="30,30" Offset="8,12">
                <Image ID="OriginCivIcon" Anchor="C,C" Size="30,30" Icon="ICON_CIVILIZATION_UNKNOWN"/>
            </Image>
        </GridButton>
    </Container>
</Instance>
```

### Support 文件与 XML 的调用链

```
XML 控件点击/显示
  → Lua 事件回调（如 OnClickSortButton）
    → include("TradeSupport") 引入的函数
      → GetYieldsForOriginCity() / SortTradeRoutes() / FormatYieldText()
        → 返回计算值
          → 更新 XML 控件（如 Controls.OriginYieldFoodLabel:SetText()）
```
