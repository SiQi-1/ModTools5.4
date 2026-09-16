# Ocean Feature & Resource Generation — 海洋地貌与资源生成

参考 Mod: Sukritact's Oceans (2542898147)

## 概述

该 Mod 展示了一套完整的海洋自定义生态系统生成方案，包括：高斯卷积热力图、海藻森林生成、按大陆分配海洋资源（含奢侈品抽牌算法）、以及 Jump Flood 大陆重划分。所有系统均可独立使用。

---

## 系统 1: 高斯卷积热力图 (Map Convolution)

文件: `Lua/Suk_MapConvolution.lua`

### 核心概念

将离散的地图数据（如温度值）通过高斯核卷积平滑为连续热力图，用于指导后续资源/地貌的权重分布。

### 预定义高斯核

```lua
-- 3x3 高斯核 (Sigma=0.85)
g_Suk_GaussianKernel_3x3 = {
    0.077847, 0.123317, 0.077847,
    0.123317, 0.195346, 0.123317,
    0.077847, 0.123317, 0.077847,
}

-- 5x5 高斯核 (Sigma=1.35)
g_Suk_GaussianKernel_5x5 = {
    0.003765, 0.015019, 0.023792, 0.015019, 0.003765,
    0.015019, 0.059912, 0.094907, 0.059912, 0.015019,
    0.023792, 0.094907, 0.150342, 0.094907, 0.023792,
    0.015019, 0.059912, 0.094907, 0.059912, 0.015019,
    0.003765, 0.015019, 0.023792, 0.015019, 0.003765,
}

-- 7x7 高斯核 (Sigma=1.9)
g_Suk_GaussianKernel_7x7 = {
    0.000036, 0.000363, 0.001446, 0.002291, 0.001446, 0.000363, 0.000036,
    0.000363, 0.003676, 0.014662, 0.023226, 0.014662, 0.003676, 0.000363,
    0.001446, 0.014662, 0.058488, 0.092651, 0.058488, 0.014662, 0.001446,
    0.002291, 0.023226, 0.092651, 0.146768, 0.092651, 0.023226, 0.002291,
    0.001446, 0.014662, 0.058488, 0.092651, 0.058488, 0.014662, 0.001446,
    0.000363, 0.003676, 0.014662, 0.023226, 0.014662, 0.003676, 0.000363,
    0.000036, 0.000363, 0.001446, 0.002291, 0.001446, 0.000363, 0.000036,
}
```

### MapConvolution 对象

```lua
Suk_MapConvolution = {
    m_MapWidth  = Map.GetGridSize(),
    m_MapHeight = select(2, Map.GetGridSize()),
    m_WrapX     = Map:IsWrapX(),
    m_WrapY     = Map:IsWrapY(),

    -- 构造函数: padding=地图外取值(用于非Wrap地图), limiter=可选的惰性跳过函数
    new = function(self, padding, limiter)
        local o = {}
        setmetatable(o, self)
        self.__index = self
        o.m_Padding = padding
        o.m_Limiter = limiter
        o.m_MapGrid = {}  -- 一维数组，按 plotIndex 索引
        return o
    end,

    -- 高斯卷积（kernel 为一维数组，边长自动推断）
    DoConvolution = function(self, kernel)
        local half_length = math.floor(math.sqrt(#kernel)/2)
        local new_grid = Suk_MapConvolution:new(self.m_Padding, self.m_Limiter)

        for plotX = 0, self.m_MapWidth-1 do
            for plotY = 0, self.m_MapHeight-1 do
                local plotIndex = plotY * self.m_MapWidth + plotX
                if (not self.m_Limiter) or (self.m_Limiter(plotIndex)) then
                    local new_value = 0
                    for kernelX = -half_length, half_length do
                        for kernelY = -half_length, half_length do
                            local val, _, _ = self:Get(plotX + kernelX, plotY + kernelY)
                            local kernelIdx = (kernelY + half_length) * (2*half_length+1) + (kernelX + half_length) + 1
                            new_value = new_value + val * kernel[kernelIdx]
                        end
                    end
                    new_grid.m_MapGrid[plotIndex] = new_value
                else
                    new_grid.m_MapGrid[plotIndex] = self.m_MapGrid[plotIndex]
                end
            end
        end
        return new_grid
    end,

    -- 归一化到 [0, 1]
    DoNormalise = function(self)
        local iMin, iMax = 0, 0
        for _, v in pairs(self.m_MapGrid) do
            iMin = math.min(iMin, v)
            iMax = math.max(iMax, v)
        end
        local iRange = iMax - iMin
        for i, v in pairs(self.m_MapGrid) do
            self.m_MapGrid[i] = (v - iMin) / iRange
        end
    end,
}
```

### 使用模式

```lua
-- 1. 创建热力图并填入初始值
local tTempMap = Suk_MapConvolution:new()
for iY = 0, iH - 1 do
    for iX = 0, iW - 1 do
        local iPlot = iY * iW + iX
        local pPlot = Map.GetPlotByIndex(iPlot)
        -- 从地形/地貌查表赋值
        if tTerrainMap[pPlot:GetTerrainType()] then
            tTempMap.m_MapGrid[iPlot] = tTerrainMap[pPlot:GetTerrainType()]
        elseif tFeatureMap[pPlot:GetFeatureType()] then
            tTempMap.m_MapGrid[iPlot] = tFeatureMap[pPlot:GetFeatureType()]
        else
            tTempMap.m_MapGrid[iPlot] = 0
        end
    end
end

-- 2. 多次卷积模糊（各级核递进）
tTempMap = tTempMap:DoConvolution(g_Suk_GaussianKernel_5x5)
tTempMap = tTempMap:DoConvolution(g_Suk_GaussianKernel_5x5)
tTempMap = tTempMap:DoConvolution(g_Suk_GaussianKernel_7x7)
tTempMap:DoNormalise()

-- 3. 使用归一化后的值 (0~1) 作为权重
local iWeight = 1 - tTempMap.m_MapGrid[iPlot]  -- 热的地方权重高
```

### 边界处理

- **WrapX/WrapY**: 坐标超出范围时环绕到地图另一侧
- **无 Wrap + padding**: 超出范围的坐标返回 padding 值（通常 0 或 -1 表示"无数据"）
- **无 Wrap + 无 padding**: 坐标超出范围时钳制到边缘

---

## 系统 2: 海藻森林生成 (Kelp Forest)

文件: `Lua/Suk_KelpGenerator.lua`

### 流程

1. **去重保护**: 用 `Game:GetProperty("Suk_Kelp_Spawned")` 防止重复生成
2. **温度计算**: 用地形和地貌映射值，经三次高斯卷积生成温度热力图
3. **筛选可生地格**: 水域 + 空地格 + 非暗礁相邻 + 在 `Resource_ValidFeatures` 中
4. **加权随机放置**: 根据相邻海藻数量调整分数（聚类：1~2 块相邻加分，4+ 块相邻减分）

### 可生条件

```lua
function CanHaveKelp(pPlot, iX, iY)
    return pPlot:IsWater()
        and pPlot:GetFeatureType() == g_FEATURE_NONE
        and TerrainBuilder.CanHaveFeature(pPlot, g_FEATURE_SUK_KELP)
        and (not IsAdjacentToReef(iX, iY))
        and tValidResources[pPlot:GetResourceType()]  -- 资源对海藻有效
end
```

`tValidResources` 预加载: 遍历 `Resource_ValidFeatures` 表，收集 FeatureType 为海藻的资源类型。

### 聚类评分

```lua
function AddKelpAtPlot(pPlot, iX, iY, iPlot)
    local iScore = 200
    local iAdjacent = TerrainBuilder.GetAdjacentFeatureCount(pPlot, g_FEATURE_SUK_KELP)

    if iAdjacent == 0 then     iScore = iScore
    elseif iAdjacent == 1 then iScore = iScore + 175  -- 鼓励成对
    elseif iAdjacent == 2 then iScore = iScore + 100  -- 小群
    elseif iAdjacent == 3 then iScore = iScore        -- 中性
    elseif iAdjacent == 4 then iScore = iScore - 100  -- 过密
    else                       iScore = iScore - 150
    end

    -- 温度越高(热力图值越大)，权重越低
    local iMod = (1 - tTemperatureMap.m_MapGrid[iPlot])
    if TerrainBuilder.GetRandomNumber(300, "...") <= iScore * iMod then
        TerrainBuilder.SetFeatureType(pPlot, g_FEATURE_SUK_KELP)
        return true
    end
    return false
end
```

### 洗牌后顺序放置

使用 `GetShuffledCopyOfTable` 打乱候选地块，逐个尝试放置，达到百分比目标后 `break`。

---

## 系统 3: Jump Flood 大陆划分

文件: `Lua/Suk_ContinentJumpFlood.lua`

### 原理

用 GPU 风格的 Jump Flooding 算法在六角格地图上快速生成 Voronoi 图，每个大陆像素扩散为 Voronoi 区域。相比遍历全图做距离比较，复杂度从 O(n^2) 降到 O(n log n)。

### 核心步骤

```lua
-- 1. Pack: 将游戏大陆数据打包为 2D 种子数组
function PackMap()
    local tMapArray = {}
    for iX = 0, m_MAP_WIDTH - 1 do
        tMapArray[iX] = {}
        for iY = 0, m_MAP_HEIGHT - 1 do
            local iContinent = Map.GetPlotByIndex(iY * m_MAP_WIDTH + iX):GetContinentType()
            tMapArray[iX][iY] = {
                (iContinent > -1) and iX or -1,  -- seedX
                (iContinent > -1) and iY or -1,  -- seedY
                iContinent                       -- continentID
            }
        end
    end
    return tMapArray
end

-- 2. Jump Flooding 迭代
-- iStep 从 0 递增，步长 = 2^(ceil(log2(max(W,H))) - step - 1)
-- 每个像素检查 offset = ±stepSize 处的 4 个邻居种子，取最近

-- 3. Unpack: 将扩散结果转为 {ContinentID -> [plotIndex, ...]} 映射
local tContinentPlots = Suk_GetPlotContinents()
-- 返回: { Continents = {[1]={plot1, plot2,...}}, Plots = {[plotIndex]=continentID} }
```

### 六角格距离

```lua
local m_SQRT_3 = math.sqrt(3)
-- 像素坐标转换（六角格 → 笛卡尔）
local iPixelX = m_SQRT_3 * (iX + ((iY % 2 == 0) and 0 or 0.5))
local iPixelY = 1.5 * iY
-- 距离 = dx^2 + dy^2 (无需 sqrt)
```

### 注意事项

- 大陆种子来自 `pPlot:GetContinentType()`，只有陆地格有有效值
- 经过完整 log2(max(W,H)) 步迭代后，每个水格会被分配到最近的陆地块的大陆 ID
- 结果暴露到 `ExposedMembers.Suk_Oceans_ContinentsData` 供下游使用

---

## 系统 4: 按大陆分配海洋资源

文件: `Lua/Suk_ResourceGenerator.lua`

### 整体流程

```
1. 查询所有 SeaFrequency > 0 的资源（含 CLASS_SUK_LAKE_ONLY 标签判断）
2. 对大陆所有水格做初始扫描，移除已有奢侈品
3. 对现有资源做卷积热力图（奢侈品图和加成品图分离）
4. 对每个大陆，计算每个资源在该大陆的有效格数和得分
5. 每大陆抽 2 种奢侈品（加权随机抽卡）
6. 按得分升序逐个放置，用热力图权重 + 邻近惩罚决定具体格位
```

### 加权随机抽卡

```lua
function DrawRandomCard(tCards, tWeights, sReason)
    local iWeightSum = 0
    for _, iWeight in ipairs(tWeights) do iWeightSum = iWeightSum + iWeight end

    local iRandomDraw = TerrainBuilder.GetRandomNumber(100, sReason) / 100 * iWeightSum
    local iRunningWeight = 0

    for iIndex, iWeight in ipairs(tWeights) do
        iRunningWeight = iRunningWeight + iWeight
        if iRandomDraw < iRunningWeight then
            return tCards[iIndex], iIndex
        end
    end
end

-- 不放回抽取多张
function DrawRandomCards(tCards, tWeights, iNum, sReason)
    local tDrawn = {}
    -- 深拷贝
    while #tDrawn < iNum do
        local pCard, iIndex = DrawRandomCard(tCards, tWeights, sReason)
        table.insert(tDrawn, pCard)
        table.remove(tCards, iIndex)
        table.remove(tWeights, iIndex)
    end
    return unpack(tDrawn)
end
```

### 资源得分计算

```lua
-- 每个资源在每片大陆的得分
tContinentLuxuries[iResource][iContinent].Score =
    math.floor((iTargetPercentage/100) * iResourcePlots * (iLuxuryPercentage/100) * iFrequency + 0.5) * 100
```

### 单格放置评分

```lua
local iWeight  = tPlotsData.LuxuryWeight[iPlot] / iMaxWeight  -- 热力图权重归一化
local iNearby  = tPlotsData.NearbyLuxuries[iPlot]              -- 周围奢侈品密度（通过环形迭代累积）
local iScore   = (iWeight^0.666) * (6 - iNearby) * 0.1666 * 100

if TerrainBuilder.GetRandomNumber(100, "...") <= iScore then
    ResourceBuilder.SetResourceType(pPlot, iResource, 1)
    -- 更新周围地格的邻近奢侈品计数 (1环+3, 2环+2, 3环+1)
end
```

### 湖泊 vs 海洋差异

- 湖泊专属资源通过 `CLASS_SUK_LAKE_ONLY` 标签识别（`TypeTags` 表）
- `CanHaveResource` 对湖泊资源额外检查 `pPlot:IsLake()`
- 计算放置数量时湖泊会乘以 `iLakesMultiplier = 1 + (iNumWaterPlots - iNumLakes)/iNumWaterPlots`，使湖泊地格获得更密集的资源

### 去重保护

```lua
if Game:GetProperty("Suk_Oceans_Resources_Spawned") then
    -- 从持久化属性恢复大陆数据
    local tData = Game:GetProperty("Suk_Oceans_ContinentsData")
    if tData then ExposedMembers.Suk_Oceans_ContinentsData = tData end
    return
else
    Game:SetProperty("Suk_Oceans_Resources_Spawned", true)
end
```

---

## XML 配合

### Suk_TemperatureLens.xml — 温度透镜按钮

`Lua/Suk_TemperatureLens.xml` 在小地图（MinimapPanel）的透镜切换栈中挂入温度透镜单选按钮：

```xml
<Context>
    <RadioButton ID="SukTemperatureLensButton" RadioGroup="ActiveLens"
        String="Temperature Lens" ToolTip="Temperature Lens"
        Style="WhiteSemiBold14"
        ButtonTexture="Controls_RadioButtonLarge.dds" ButtonSize="35,35"/>
</Context>
```

Lua 端通过 `ContextPtr:LookUpControl("/InGame/MinimapPanel/LensToggleStack")` 找到父控件后 `ChangeParent` 挂入。点击时触发分桶着色逻辑（10 级温度分桶，红蓝色渐变）。

### 海洋资源和地貌 XML

`Suk_Oceans_Features.sql` / `Suk_Oceans_Resources.sql` 中的地貌/资源定义完全通过 SQL 实现，无独立 XML。`CLASS_SUK_LAKE_ONLY` 标签通过 SQL `TypeTags` 表注册。海洋资源产出定义在 `Resource_YieldChanges` 中（SQL INSERT）。

---

## 系统 5: 温度透镜 UI

文件: `Lua/Suk_TemperatureLens.lua` + `Lua/Suk_TemperatureLens.xml`

### 关键模式

```lua
-- 从 ExposedMembers 获取地图数据
local m_TemperatureOverlay = UILens.GetOverlay("Suk_TemperatureBorderOverlay")

-- 分桶着色
for iPlot, iVal in pairs(ExposedMembers.SukTemperature.m_MapGrid) do
    local iBucket = math.floor(iVal * 10) + 1  -- 10 级分桶
    table.insert(tTemp[iBucket], iPlot)
end

for iBucket, tPlots in pairs(tTemp) do
    local iVal = (iBucket-1)/10
    local iAlpha = 1 - (4*iVal) + (4*iVal^2)  -- 非线性透明度
    local iRed = 1 - iVal
    local iBlue = iVal
    local iColor = UI.GetColorValue(iBlue, 0, iRed, iAlpha)
    m_TemperatureOverlay:SetHighlightColor(iBucket, iColor)
    m_TemperatureOverlay:SetPlotChannel(tPlots, iBucket)
end
```

### 按钮挂接到 Minimap 透镜栈

```lua
function OnInit(bIsReload)
    Events.LoadScreenClose.Add(OnInit)
    -- 在 minimap 面板的透镜切换栈中找到父控件
    local pLensToggleStack = ContextPtr:LookUpControl("/InGame/MinimapPanel/LensToggleStack")
    Controls.SukTemperatureLensButton:ChangeParent(pLensToggleStack)
    pLensToggleStack:CalculateSize()
    pLensToggleStack:ReprocessAnchoring()
end
```

---

## 跨系统通信: Game Property 去重

每个 Lua 地图生成脚本使用 `Game:SetProperty` / `Game:GetProperty` 确保只运行一次，防止 Mod 重载或地图刷新时重复添加：

```lua
-- 海藻生成器
if Game:GetProperty("Suk_Kelp_Spawned") then return end
Game:SetProperty("Suk_Kelp_Spawned", true)

-- 资源生成器
if Game:GetProperty("Suk_Oceans_Resources_Spawned") then return end
Game:SetProperty("Suk_Oceans_Resources_Spawned", true)
```

跨 Lua 文件的数据传递通过 `ExposedMembers` 全局表或 `Game:SetProperty`（后者支持持久化到存档）。

---

## 配置引导的生成参数

```lua
-- 从 MapConfiguration 读取玩家设置
local iKelpPercent = 25 + (MapConfiguration.GetValue("rainfall") or 0)    -- 降雨量影响海藻
local iResourceSetting = MapConfiguration.GetValue("resources") or 0       -- 资源丰富度

-- 映射到生成参数调整
local tResourceSettings = {
    [1] = -3,   -- 稀疏
    [3] = 3,    -- 丰富
    [4] = TerrainBuilder.GetRandomNumber(9, "...") - 4,  -- 随机
}
```

---

## 相关参考

- `Suk_Oceans_Features.sql` — Kelp Feature 数据库定义（含 Requirement、Resource_ValidFeatures）
- `Suk_Oceans_Resources.sql` — 海洋资源数据库定义（含 CLASS_SUK_LAKE_ONLY 标签、Resource_YieldChanges）
- `PlotIterators.lua` — 环形地块迭代器 `PlotRingIterator(plot, radius)`
