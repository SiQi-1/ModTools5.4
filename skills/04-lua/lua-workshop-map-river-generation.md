# River Terrain Carving & Gameplay — 真实河流地形雕刻

参考 Mod: Real Rivers Map (3019522388)

## 概述

将河流实现为可通行的水域地形（TERRAIN_REAL_RIVER），而非原版的直线边界。包含：地图类型感知的方向偏置河流生成、小型湖泊点缀、激流（Cataract）地貌分配、浮桥改良设施和限时自毁机制、以及水路贸易路线自动铺设。

---

## XML 配合

本系统为纯地图生成脚本，无 UI 面板。所有参数通过 `MapConfiguration.GetValue()` 从游戏地图设置面板读取（`RealRiver_MaxLength`, `RealRiver_Num` 等需要在 `Config.xml` 中注册为 `Parameters`）。浮桥改良设施的提示文本和河流路线名称在 `RR_Improvements.sql` 等数据文件中定义。

---

## 系统 1: 真实河流生成器 (River Terrain Carving)

文件: `Maps/Utility/RealRiverGenerator.lua`

### 核心概念

将河流定义为自定义地形类型 `TERRAIN_REAL_RIVER`（而非原版的河流边界），使其成为可航行、可建改良的水域地格。在陆地上"雕刻"河流路径，每格设为 OCEAN 地块类型。

### 地形常量

```lua
g_TERRAIN_TYPE_REAL_RIVER        = GetGameInfoIndex("Terrains", "TERRAIN_REAL_RIVER")
g_FEATURE_REAL_RIVER_NORMAL      = GetGameInfoIndex("Features", "FEATURE_REAL_RIVER_NORMAL")
g_FEATURE_REAL_RIVER_CATARACT    = GetGameInfoIndex("Features", "FEATURE_REAL_RIVER_CATARACT")
g_TERRAIN_TYPE_REAL_LAKE         = GetGameInfoIndex("Terrains", "TERRAIN_REAL_LAKE")
g_FEATURE_REAL_LAKE_NORMAL       = GetGameInfoIndex("Features", "FEATURE_REAL_LAKE_NORMAL")
```

### 参数配置

```lua
function Initialize()
    g_RealRiver_MaxLength  = MapConfiguration.GetValue("RealRiver_MaxLength") or 12
    g_RealRiver_MinLength  = MapConfiguration.GetValue("RealRiver_MinLength") or 6
    g_RealRiver_Num        = MapConfiguration.GetValue("RealRiver_Num") or 8
    g_RealRiver_MinInterval= MapConfiguration.GetValue("RealRiver_MinInterval") or 6
    -- 激流百分比: CATARACT_PERCENTAGE_1..4 → 1/2/3/4 格中 1 格
end
```

### 生成流程

```
1. Initialize() — 从 MapConfiguration 读取参数
2. 根据地图类型初始化方向偏好 (InitializeRiverKinds_xxx)
3. 对于大陆地图，清除地图顶部/底部边缘的陆地块 → 海岸
4. For each river to generate:
   a. 寻找有效入海口 (IsCoastalLand + 3个相邻陆地同侧 + 远离已有河口)
   b. 距离加权随机选取入海口 (越远越优先避免聚集)
   c. 从入海口向内陆延伸 (6~12 格)，每步用方向偏好选择下一格
5. AddFeatures_RealRivers() — 随机分配 Normal/Cataract 地貌
```

### 入海口条件

```lua
function HasAtLeast3LandsAdjacentAtOneSide(plot)
    -- 收集非河流、非海岸、非海洋的相邻方向
    local valid_direction_list = {}
    for i = 0, 5 do
        local nextPlot = Map.GetAdjacentPlot(iX, iY, i)
        if nextPlot and nextPlot:GetTerrainType() ~= g_TERRAIN_TYPE_REAL_RIVER
            and nextPlot:GetTerrainType() ~= g_TERRAIN_TYPE_COAST
            and nextPlot:GetTerrainType() ~= g_TERRAIN_TYPE_OCEAN then
            table.insert(valid_direction_list, i)
        end
    end
    -- 必须至少有 3 个连续方向指向陆地
    if #valid_direction_list < 3 then return false end
    -- 检查方向连续性
    local temp = valid_direction_list[1]
    for _, value in ipairs(valid_direction_list) do
        local diff = math.abs(temp - value)
        if diff ~= 1 and diff ~= 5 then return false end  -- 非连续
        temp = value
    end
    return true
end
```

- 内陆海、七海等地图跳过此检查（地图结构不同）

### 方向偏好系统

每个地图类型基于入海口纬度定义 4~6 种河流方向类型：

```lua
-- DirectionTypes: 0=NE, 1=E, 2=SE, 3=SW, 4=W, 5=NW

-- 大陆地图 (4 种类型):
-- riverKind 1: 向西 (方向 3,4,5 | 权重 3,6,3)
-- riverKind 2: 向东 (方向 0,1,2 | 权重 3,6,3)
-- riverKind 3: 向北 (方向 1,0,5,4 | 权重 2,4,4,2) — 南半球
-- riverKind 4: 向南 (方向 1,2,3,4 | 权重 2,4,4,2) — 北半球

-- 七海地图 (6 种类型): 增加 NW→SE (3) 和 SE→NW (4) 等
```

### 单步方向选择

```lua
function HasOneAdjacentRealRiver_andValidDirection(oldplot, newplot, lastDirection, judgeDirection)
    -- 条件1: 新格必须恰好有 1 个相邻水域 + 1 个相邻真实河流
    if not HasOneAdjacentWater_andIsRealRiver(newplot) then return false end
    -- 条件2: 新格不与已有河流太近
    if IsNearOtherRealRivers(newplot, real_river_plot_index_list, minInterval) then return false end
    -- 条件3: 新格不在地图边缘
    if IsNearMapEdge(newplot) then return false end
    -- 方向判断
    local newDirection = GetDirection(oldplot, newplot)
    if lastDirection == newDirection then
        return true, newDirection, 12  -- 直行高权重
    elseif is_adjacent_direction(lastDirection, newDirection) then
        return true, newDirection, 6   -- 转弯中权重
    else
        return false                   -- 禁止急转弯
    end
end
```

### 加权随机抽选下一格

对每个有效相邻格计算复合权重，然后按权重随机选：

```lua
function GetNextRealRiverPlot(plot, isFirstPlot, lastDirection, riverKind, bannedDirections)
    local valid_plot_list = {}       -- 按重复次数实现加权
    local valid_plot_direction_list = {}

    for _, pNeighborPlot in ipairs(Map.GetAdjacentPlots(iX, iY)) do
        -- 权重 = 基础权重(来自方向) + 方向偏好加成 + 远离水源加成
        local weight = base_weight or 1
        -- + 方向偏好表加成
        weight = weight + riverKind_Weight_list[key]
        -- + 如果下一个地块比当前更少水域，加 4 (偏好内陆)
        if nextPlotWaterNum < thisPlotWaterNum then weight = weight + 4 end
        -- 按权重插入
        for i = 0, weight - 1 do
            table.insert(valid_plot_list, pNeighborPlot:GetIndex())
            table.insert(valid_plot_direction_list, direction)
        end
    end

    local rand = TerrainBuilder.GetRandomNumber(#valid_plot_list, "...") + 1
    return valid_plot_list[rand], valid_plot_direction_list[rand], my_riverKind
end
```

### 激流地貌分配

```lua
function AddFeatures_RealRivers()
    for i = 0, Map.GetPlotCount() - 1 do
        local plot = Map.GetPlotByIndex(i)
        if plot:GetTerrainType() == g_TERRAIN_TYPE_REAL_RIVER then
            if not plot:IsNaturalWonder() then
                local rand = TerrainBuilder.GetRandomNumber(totalSampleNum, "...") + 1
                if rand > cataractPercentage then
                    TerrainBuilder.SetFeatureType(plot, g_FEATURE_REAL_RIVER_NORMAL)
                else
                    TerrainBuilder.SetFeatureType(plot, g_FEATURE_REAL_RIVER_CATARACT)
                end
            end
        end
    end
end
```

---

## 系统 2: 真实湖泊生成

文件: `Maps/Utility/RealRiverGenerator.lua` (AddLakes_RealRivers_Step1)

### 原理

在地图陆地内部放置小型湖泊（半径 3 格内无河流/海岸的内陆格），设为其专属海岸地形：

```lua
function AddLakes_RealRivers_Step1(numSmallLakes)
    for i = 0, numSmallLakes - 1 do
        local possible_lake_plot_list = {}
        for idx = 0, Map.GetPlotCount() - 1 do
            local plot = Map.GetPlotByIndex(idx)
            if plot and not plot:IsWater()
                and not plot:IsCoastalLand()
                and not HasRealRiversOrCoastWithXTiles(plot, 3)  -- 3格内无河/海
                and not plot:IsRiver() and not plot:IsRiverAdjacent()
                and plot:GetFeatureType() ~= g_FEATURE_VOLCANO
                and not plot:IsNaturalWonder() then
                table.insert(possible_lake_plot_list, idx)
            end
        end
        -- 随机选取一个设为海岸
        if #possible_lake_plot_list > 0 then
            local rand = TerrainBuilder.GetRandomNumber(#possible_lake_plot_list, "...") + 1
            local kplot = Map.GetPlotByIndex(possible_lake_plot_list[rand])
            TerrainBuilder.SetTerrainType(kplot, g_TERRAIN_TYPE_COAST)
            plotTypes[kplot:GetIndex()] = g_PLOT_TYPE_OCEAN
        end
    end
    AreaBuilder.Recalculate()  -- 重新计算水域区域
end
```

---

## 系统 3: 浮桥改良设施 (Pontoon Bridge)

文件: `Scripts/RR_Function_Gameplay.lua`

### 数据结构

- 改良设施类型: `IMPROVEMENT_PONTOON`
- 使用 Plot Property 存储建造时间和所有者
- 全局参数: `RRM_PONTOON_EXIST_TURNS` (默认 30 回合)

### 建造时记录

```lua
function OnImprovementAddedToMap_SetPlotProperty(locationX, locationY, improvementType, eImprovementOwner, ...)
    if improvementType ~= my_PontoonImprov then return end
    local pPlot = Map.GetPlot(locationX, locationY)
    local tParameters = {
        PlayerID = eImprovementOwner,
        AddTurn = Game:GetCurrentGameTurn()
    }
    pPlot:SetProperty(PLOT_PONTOON_ADD_KEY, tParameters)
end
```

### 每回合检查并移除过期浮桥

```lua
function On_Request_Remove_Pontoon(iTurn)
    local currentTurn = Game.GetCurrentGameTurn()
    for i = 0, Map.GetPlotCount() - 1 do
        local kPlot = Map.GetPlotByIndex(i)
        if kPlot and kPlot:GetImprovementType() == my_PontoonImprov then
            local prop = kPlot:GetProperty(PLOT_PONTOON_ADD_KEY)
            local exist_time = math.ceil(my_adjustedCostMultiplier * my_pontoon_exist_time)
            if prop and prop.AddTurn + exist_time < currentTurn then
                -- 过期: 移除改良设施
                ImprovementBuilder.SetImprovementType(kPlot, -1)
                -- 发送通知给所有者
                NotificationManager.SendNotification(prop.PlayerID, notificationHash,
                    'LOC_NOTIFICATION_...', 'LOC_NOTIFICATION_..._SUMMARY',
                    kPlot:GetX(), kPlot:GetY())
            end
        end
    end
end
```

### 游戏速度适应

```lua
-- 从 GameSpeeds 读取 CostMultiplier 调整浮桥持续回合数
local my_Speed = GameConfiguration.GetGameSpeedType()
local my_multiplier = GameInfo.GameSpeeds[my_Speed].CostMultiplier
local my_adjustedCostMultiplier = my_multiplier / 100
local existTime = math.ceil(my_adjustedCostMultiplier * baseExistTurns)
```

### 掠劫时移除浮桥

```lua
function OnPillage(iUnitPlayerID, iUnitID, eImprovement, ...)
    if eImprovement == my_PontoonImprov then
        ImprovementBuilder.SetImprovementType(Map.GetPlotByIndex(plotIndex), -1)
    end
end
```

---

## 系统 4: 水上贸易路线 (River Road)

文件: `Scripts/RR_Function_Gameplay.lua`

### 商人移动时自动铺设河流路线

```lua
function On_SetRiverRoad(playerID, unitID, iX, iY)
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    -- 限商人
    if GameInfo.Units[pUnit:GetType()].UnitType ~= "UNIT_TRADER" then return end

    local pPlot = Map.GetPlot(iX, iY)
    if not pPlot:IsWater() then return end

    local routeTable = pPlot:GetRouteType()
    if routeTable ~= my_riverRoadItem.Index then
        RouteBuilder.SetRouteType(pPlot, my_riverRoadItem.Index)
    end
end

-- 注册事件
Events.UnitMoved.Add(On_SetRiverRoad)
```

### 水上陷阱移除路线

```lua
-- 建造水上陷阱 (IMPROVEMENT_WATER_TRAP_DEFENSE) 时移除地块路线
function OnImprovementAddedToMap_RemoveRoute(locationX, locationY, improvementType, ...)
    if improvementType ~= my_WaterTrapDefenseImprov then return end
    RouteBuilder.SetRouteType(Map.GetPlot(locationX, locationY), -1)
end
```

---

## 系统 5: 数据库整合 — 兼容现有改良设施

文件: `Data/RR_Improvements.sql`

让原版和 Mod 的水上改良设施能在真实河流上建造：

```sql
-- 通用: 让海上风车/渔场/海上家园兼容河流地形
INSERT INTO Improvement_ValidTerrains (ImprovementType, TerrainType)
VALUES
    ('IMPROVEMENT_OFFSHORE_WIND_FARM', 'TERRAIN_REAL_RIVER'),
    ('IMPROVEMENT_FISHERY', 'TERRAIN_REAL_RIVER'),
    ('IMPROVEMENT_SEASTEAD', 'TERRAIN_REAL_RIVER');

-- 兼容 DLC 特色改良
INSERT OR IGNORE INTO Improvement_ValidTerrains
    (ImprovementType, TerrainType)
SELECT ImprovementType, 'TERRAIN_REAL_RIVER'
FROM Improvements WHERE ImprovementType IN ('IMPROVEMENT_POLDER', 'IMPROVEMENT_KAMPUNG', 'IMPROVEMENT_FEITORIA');
```

---

## 模式总结: 地图感知的方向偏好系统

| 地图类型 | 方向种类数 | 纬度划分 | 河流走向 |
|---------|-----------|---------|---------|
| Continents | 4 | y < H/3 → 向北, y > 2H/3 → 向南, 中纬度按东西 | 纵向流入海域 |
| InlandSea | 4 | 按内陆海边界划分 | 流向内陆海 |
| Seven Seas | 6 | 全按上次方向决定 | 多方向绕行群岛 |
| Lake Baikal | 2 | 按对角象限划分 | 汇入贝尔加湖 |

每种类型的共同参数结构:

```lua
riverKind_Favor_Total_list = {
    {3, 4, 5},   -- riverKind 1 的偏好方向列表
    {0, 1, 2},   -- riverKind 2
    ...
}
riverKind_Weight_Total_list = {
    {3, 6, 3},   -- 对应权重 (每 36 份中的分配)
    {3, 6, 3},
    ...
}
```

---

## 相关参考

- `Data/RR_Features.sql` — 真实河流地貌 (FEATURE_REAL_RIVER_NORMAL/CATARACT) 数据库定义
- `Data/RR_Terrains.sql` — TERRAIN_REAL_RIVER / TERRAIN_REAL_LAKE 地形定义
- `Data/RR_Routes_Mode.sql` — ROUTE_RIVER_ROAD 路线定义
- `Maps/Real_Rivers_Continents.lua` — 大陆地图完整调用示例
- `Maps/Utility/MapEnums.lua` — 地图常量枚举
