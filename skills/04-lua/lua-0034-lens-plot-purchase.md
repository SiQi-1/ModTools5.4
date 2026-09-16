# UILens 透镜地块购买系统（来源：15.0 Almond 杏仁文明）

## 做什么
通过 UILens 图层系统，在城市地块上叠加可交互的购买按钮（金币标价），允许玩家消耗金币购买特定类型区域的相邻加成。核心是 UILens 层开关 + InstanceManager 世界空间定位 + 递增定价的完整系统。同时维护与原生城市管理的兼容性。

## 涉及文件

| 文件 | 角色 |
|------|------|
| `15.0/UI/Arknights_Cute_Leaders_15.0_PlotInfo.lua` | 购买按钮叠加层（346 行）：UILens 层管理、InstanceManager 定位、按钮生成、金币检测 |
| `15.0/UI/Arknights_Cute_Leaders_15.0_CityPanel.lua` | CityPanel 勾选框：触发透镜开关、检查是否有可购买区域 |
| `15.0/Scripts/Arknights_Cute_Leaders_15.0_Scripts.lua` | GP 端：购买逻辑（扣除金币、增加相邻加成）、区域移除清理 |
| Core Mod GamePlay.lua | `SiqiChangeDistrictYieldChange` — 修改区域产出的底层函数 |

## GP 端

### 购买逻辑

```lua
function SiqiCuteLeader15OnPurchaseAdjacency(playerID, params)
    -- 1. 修改区域产出变化固定值 +1
    LuaEvents.SiqiChangeDistrictYieldChange(params.iX, params.iY, params.YieldType, 1)
    -- 2. 递增定价：cost = 当前 cost + BASE_COST (25 * 游戏速度)
    local Property = pPlot:GetProperty("Siqi_AlmondPurchaseCost") or {index = DistrictType, cost = BASE_COST}
    local goldCost = Property.cost
    pPlot:SetProperty("Siqi_AlmondPurchaseCost", {index = DistrictType, cost = goldCost + BASE_COST})
    -- 3. 扣除金币
    pPlayer:GetTreasury():ChangeGoldBalance(-goldCost)
end
```

### 区域移除时清理（防止 exploit）

```lua
function OnDistrictRemovedFromMap(playerID, districtID, cityID, districtX, districtY, districtType)
    -- 计算已购买次数 = (currentCost - BASE_COST) / BASE_COST
    -- 扣除对应次数的相邻加成
    LuaEvents.SiqiChangeDistrictYieldChange(districtX, districtY, YieldType, -count)
    -- 清空购买记录
    pPlot:SetProperty("Siqi_AlmondPurchaseCost", false)
end
```

## UI 端

### 一、CityPanel 勾选框（CityPanel.lua）

**注入位置：** `/InGame/CityPanel/ActionStack`

**逻辑：**
```lua
function Refresh()
    if pCity and SIqi_PlayerHasTrait(pCity:GetOwner(), TRAIT_ALMOND) then
        if Siqi_HasDistrict() then
            -- 有符合类型的区域 → 启用勾选框
            Controls.SiqiAlmondCheck:SetDisabled(false)
        else
            Controls.SiqiAlmondCheck:SetDisabled(true)
        end
    else
        Controls.SiqiAlmondGrid:SetHide(true)
    end
end
```

**勾选回调：**
```lua
function OnSiqiAlmondButtonChecked()
    if Controls.SiqiAlmondCheck:IsChecked() then
        -- 关闭城市管理和地块购买透镜（避免冲突）
        UILens.ToggleLayerOff(m_CitizenManagement)
        UILens.ToggleLayerOff(m_PurchasePlot)
        RecenterCameraOnCity()
        UILens.ToggleLayerOn(m_PurchaseAdjacencyBonusDistricts)  -- 开启购买透镜
    else
        UILens.ToggleLayerOff(m_PurchaseAdjacencyBonusDistricts)
    end
end
```

### 二、地块叠加层（PlotInfo.lua — 核心）

**透镜层定义：**
```lua
local m_PurchaseAdjacencyBonusDistricts = UILens.CreateLensLayerHash("PurchaseAdjacencyBonusDistricts")
local m_MapHexMask = UILens.CreateLensLayerHash("Map_HexMask")
```

**InstanceManager 定义：**
```lua
local m_PlotIM = InstanceManager:new("SiqiInfoInstance", "Anchor", Controls.SiqiPlotInfoContainer)
```

#### 核心函数：ShowPurchaseAdjacency()

遍历城市已购买地块中所有符合条件的区域（类型在 `m_Distrcits` 表中且已完成建造）：
1. 为每个区域获取或创建 InstanceManager instance
2. 设置世界空间位置：`pInstance.Anchor:SetWorldPositionVal(worldX, worldY, 20)`
3. 按钮显示金币价格（从 plot property 读取 `Siqi_AlmondPurchaseCost`）
4. 金币不足时禁用按钮 + 红色文字
5. 金币足够时播放旋转金币动画

**按钮交互：**
```lua
pInstance.SiqiPurchaseButton:RegisterCallback(Mouse.eLClick, function()
    OnPurchaseAdjacency(plotIndex)
    -- → UI.RequestPlayerOperation(playerID, PlayerOperations.EXECUTE_SCRIPT, params)
end)
```

#### 透镜管理

**开关处理：**
```lua
function OnLensLayerOn(layerNum)
    if layerNum == m_PurchaseAdjacencyBonusDistricts then
        ShowPurchaseAdjacency()
        RealizeShadowMask()   -- 高亮可购买区域，其余变暗
        RealizeTilt()          -- 固定视角倾斜
    end
end

function OnLensLayerOff(layerNum)
    if layerNum == m_PurchaseAdjacencyBonusDistricts then
        HidePurchaseAdjacency()
        RealizeShadowMask()
        RealizeTilt()
    end
end
```

**阴影遮罩（RealizeShadowMask）：**
```lua
-- 收集所有需要"不遮罩"的地块 ID（购买区 + 城市管理 + 区域放置 + 交换地块）
local kNotToMask = AggregateLensHexes({ KEY_PLOT_PURCHASE, KEY_CITIZEN_MANAGEMENT, KEY_DISTRICT_PLACEMENT, KEY_SWAP_TILE_OWNER })
UILens.SetLayerHexesArea(m_MapHexMask, Game.GetLocalPlayer(), kNotToMask)
```

**固定视角（RealizeTilt）：**
```lua
function RealizeTilt()
    if UILens.IsLayerOn(m_PurchaseAdjacencyBonusDistricts) then
        UI.SetFixedTiltMode(true)   -- 固定俯视视角，方便点击世界空间按钮
    else
        UI.SetFixedTiltMode(false)
    end
end
```

#### 刷新机制

```lua
function SiqiRefresh()
    if UILens.IsLayerOn(m_PurchaseAdjacencyBonusDistricts) and Siqi_IsLeader15() then
        HidePurchaseAdjacency()     -- 先清除
        ShowPurchaseAdjacency()    -- 再重建（更新价格和状态）
        RealizeShadowMask()
        RealizeTilt()
    end
end

-- 监听国库变化和城市选择变化
Events.TreasuryChanged.Add(SiqiRefresh)
Events.CitySelectionChanged.Add(SiqiRefresh)
```

## 支持的产出类型映射

```lua
m_Distrcits = {
    {DistrcitIndex = DISTRICT_CAMPUS,            YieldType = YIELD_SCIENCE},
    {DistrcitIndex = DISTRICT_COMMERCIAL_HUB,    YieldType = YIELD_GOLD},
    {DistrcitIndex = DISTRICT_HARBOR,            YieldType = YIELD_GOLD},
    {DistrcitIndex = DISTRICT_HOLY_SITE,         YieldType = YIELD_FAITH},
    {DistrcitIndex = DISTRICT_THEATER,           YieldType = YIELD_CULTURE},
    {DistrcitIndex = DISTRICT_INDUSTRIAL_ZONE,   YieldType = YIELD_PRODUCTION},
    -- 可选：模组自定义区域
    {DistrcitIndex = DISTRICT_SIQIYI_ENGINEERING_DEPARTMENT, YieldType = YIELD_PRODUCTION},
    {DistrcitIndex = DISTRICT_JD_HOSPITAL,       YieldType = YIELD_FOOD},  -- 条件存在
    {DistrcitIndex = DISTRICT_C_AGRICULTURE,     YieldType = YIELD_FOOD},  -- 条件存在
}
```

## XML 配合

### UILens 注册

```xml
<!-- 在 PlotInfo 上下文中注册自定义透镜层 -->
<LensLayer Name="PurchaseAdjacencyBonusDistricts" ... />
```

### 需要 GameCapabilities 属性

```xml
<GameCapabilities>
    <Property Name="Siqi_AlmondPurchaseCost" ... />  <!-- 每个地块独立存储 {index, cost} -->
</GameCapabilities>
```

## 设计要点

1. **透镜层隔离**：开启购买透镜时自动关闭城市管理和地块购买透镜，避免 UI 冲突
2. **递增定价**：每次购买后 cost += BASE_COST，存储在 plot property 中，地块间独立
3. **金币动画**：旋转金币动画 + mouse enter/exit 控制播放/停止
4. **区域移除清理**：监听 `Events.DistrictRemovedFromMap` 恢复已增加的产出，防止 exploit
5. **世界空间定位**：`UI.GridToWorld(plotIndex)` + `SetWorldPositionVal(x, y, 20)` 将 UI 固定在 3D 世界上方
6. **Instance 复用**：`m_uiWorldMap[plotIndex]` 缓存已分配的 instance，避免重复创建
7. **阴影遮罩**：非可购买区域变暗，提升可交互区域的视觉辨识度
8. **条件区域支持**：通过 `if GameInfo.Districts[...] then` 安全添加第三方模组区域
