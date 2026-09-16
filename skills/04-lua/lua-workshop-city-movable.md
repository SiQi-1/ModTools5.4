# 可移动城市系统 (Movable Cities)

> 来源：MovableCities (2950891319)
> 核心文件：`Scripts/MC_Gameplay.lua`, `UI/MC_MoveCityButton.lua`, `Data/MC_Projects.xml`, `Data/MC_WonderRecover.sql`

## 1. 系统概述

让玩家通过**完成城市项目**后，将城市**移动到相邻地块**。移动过程本质是"摧毁旧城 → 在新位置重建 → 恢复建筑/区域/人口/宗教"。

### 核心流程

```
1. 城市完成 PROJECT_MOVE_CITY → 设置 CityProperty "move_city" = 1
2. 玩家点击城市面板"移动"按钮 → 进入选地块模式
3. 玩家点击目标地块 → 触发 EXECUTE_SCRIPT
4. Gameplay 端：记录旧城所有数据 → DestroyCity → Create 新城
5. CityAddedToMap 事件：恢复人口/名称/建筑/区域/宗教
6. CityMadePurchase 事件：购回旧地块
7. DistrictAddedToMap 事件：恢复区域的建筑
```

---

## XML 配合

### MC_MoveCityButton.xml — 城市面板移动按钮

`UI/MC_MoveCityButton.xml` 在游戏城市面板（`/InGame/CityPanel/ActionStack`）中挂入"移动城市"按钮：

```xml
<Context>
    <Grid ID="MoveCityGrid" Anchor="R,B" Size="41,41" Texture="UnitPanel_ActionGroupSlot"
          Offset="30,0" Hidden="1">
        <Button ID="MoveCityButton" Size="44,53" Texture="UnitPanel_ActionButton">
            <Image ID="MoveCityButtonIcon" Size="38,38" Icon="ICON_UNITOPERATION_FOUND_CITY"/>
        </Button>
    </Grid>
</Context>
```

按钮默认隐藏（`Hidden="1"`），Lua 端在 `OnCitySelectionChanged()` 中根据 `CityProperty("move_city")` 是否已完成项目来决定显示/隐藏。

### MC_Projects.xml — 移动城市项目定义

定义了 `PROJECT_MOVE_CITY_NOT_CAPITAL` 项目（`Data/MC_Projects.xml`）：
- 成本 30，需求市中心区域
- 挂载到 `TRAIT_LEADER_MAJOR_CIV`，仅人类玩家可用 (`REQSET_PLAYER_IS_HUMAN_MC`)
- DynamicModifier 类型：`MODIFIER_PLAYER_ALLOW_PROJECT_MC`（⚠️ **工坊自定义类型**，非标准。定义见 2.1：Types + DynamicModifiers，EffectType=`EFFECT_ADD_PLAYER_PROJECT_AVAILABILITY`，CollectionType=`COLLECTION_OWNER`。标准库中只有法国/中国特供的 `MODIFIER_PLAYER_ALLOW_PROJECT_CATHERINE` / `_CHINA`，通用版必须自定义）
- 完成赠送大工程师点数 + 转化 15% 产出为科技

### MC_Icons.xml — 图标定义
MC_Buildings.xml — 配套建筑 (PROJECT_MOVE_CITY_CAPITAL)
MC_Civilopedia.xml — 百科页面定义

---

## 2. 数据层（SQL / XML）

### 2.1 移动城市项目

```xml
<Types>
    <Row Type="PROJECT_MOVE_CITY_NOT_CAPITAL" Kind="KIND_PROJECT"/>
    <Row Type="MODIFIER_PLAYER_ALLOW_PROJECT_MC" Kind="KIND_MODIFIER"/>
</Types>

<DynamicModifiers>
    <Row>
        <ModifierType>MODIFIER_PLAYER_ALLOW_PROJECT_MC</ModifierType>
        <CollectionType>COLLECTION_OWNER</CollectionType>
        <EffectType>EFFECT_ADD_PLAYER_PROJECT_AVAILABILITY</EffectType>
    </Row>
</DynamicModifiers>

<Projects>
    <Row ProjectType="PROJECT_MOVE_CITY_NOT_CAPITAL"
         PrereqDistrict="DISTRICT_CITY_CENTER"
         Cost="30"
         UnlocksFromEffect="true"/>
</Projects>

<!-- 挂载到所有主要文明 -->
<TraitModifiers>
    <Row TraitType="TRAIT_LEADER_MAJOR_CIV" ModifierId="MAJOR_CIV_ALLOW_PROJECT_MOVE_CITY_NOT_CAPITAL_MC"/>
</TraitModifiers>

<Modifiers>
    <Row>
        <ModifierId>MAJOR_CIV_ALLOW_PROJECT_MOVE_CITY_NOT_CAPITAL_MC</ModifierId>
        <ModifierType>MODIFIER_PLAYER_ALLOW_PROJECT_MC</ModifierType>
        <OwnerRequirementSetId>REQSET_PLAYER_IS_HUMAN_MC</OwnerRequirementSetId>
    </Row>
</Modifiers>
```

### 2.2 奇观恢复

将奇观的 `MaxWorldInstances` 改回 `-1` 以支持重建：

```sql
UPDATE Buildings SET MaxWorldInstances = '-1'
WHERE RequiresPlacement = '1' AND IsWonder = '1' AND AllowsHolyCity = '0';

UPDATE Buildings SET MaxPlayerInstances = '1'
WHERE RequiresPlacement = '1' AND IsWonder = '1' AND AllowsHolyCity = '0';
```

---

## 3. Gameplay 层核心模式

### 3.1 CityProperty 状态管理

```lua
-- 城市是否已完成移动准备
local MC_CITY_KEY = "move_city"
-- 城市的恢复数据包（存于 CityProperty）
local MC_CITY_RECOVER_KEY = "move_city_recover"
-- 标记新位置
local MC_CITY_TAKE_PLACE_KEY = "move_city_take_place"
-- 跨上下文传递数据（存于 PlayerProperty）
local MC_PLAYER_CITY_RECOVER_KEY = "player_move_city_recover"

-- 项目完成后设置状态
function OnCityProjectCompletedMC(playerID, cityID, projectID, ...)
    if projectID ~= m_movecity_project then return end
    pCity:SetProperty(MC_CITY_KEY, 1);  -- 标记可移动
end
```

### 3.2 跨上下文通信：EXECUTE_SCRIPT

UI 层通过 `EXECUTE_SCRIPT` 向 Gameplay 层发指令：

```lua
-- UI 侧（MC_MoveCityButton.lua）
local kParameters = {};
kParameters.OnStart = 'MoveCityActionFirst';  -- Gameplay 中注册的 GameEvent 名
kParameters.CityID = cityID;
kParameters.TargetPlotID = plotId;
kParameters.CityReligionslist = cityReligionslist;
kParameters.CityReligionsPressurelist = cityReligionsPressurelist;
kParameters.HolyCityPlayerID = pHolyCityPlayerID;
UI.RequestPlayerOperation(iPlayer, PlayerOperations.EXECUTE_SCRIPT, kParameters);
```

```lua
-- Gameplay 侧（MC_Gameplay.lua）
function OnMoveCityActionFirst(playerID, params)
    local targetPlot = Map.GetPlotByIndex(params.TargetPlotID)
    local oldCity = pPlayer:GetCities():FindID(params.CityID)
    -- ... 记录数据、销毁旧城、创建新城
end

-- 注册 GameEvent
function InitializeMoveCityGameplay()
    GameEvents.MoveCityActionFirst.Add(OnMoveCityActionFirst)
end
Events.LoadGameViewStateDone.Add(InitializeMoveCityGameplay)
```

### 3.3 销毁-重建城市模式

```lua
function OnMoveCityActionFirst(playerID, params)
    local oldCity = pPlayer:GetCities():FindID(params.CityID);

    -- === 记录阶段 ===
    -- 1. 记录原始首都（如果移动的是其他玩家的原始首都）
    if oldCity:GetOriginalOwner() ~= playerID then
        -- 切换原始首都标记
        CityManager.SetAsOriginalCapital(otherCapitalCity);
    end

    -- 2. 记录城市 Properties
    local my_pCityProperties = oldCity:GetProperties();

    -- 3. 记录地块/区域/建筑/改良信息
    -- 遍历老城地块，记录到 playerRecoverNewCityProperty

    -- 4. 记录宗教信息
    local cityReligionslist = {};
    local cityReligionsPressurelist = {};

    -- 5. 记录圣城状态
    local pHolyCityPlayerID = -1;

    -- === 清理阶段 ===
    -- 6. 杀死目标地块上的非己方单位
    for _, unit in ipairs(Units.GetUnitsInPlot(targetPlot)) do
        if unit:GetOwner() ~= playerID then
            UnitManager.Kill(unit);
        end
    end

    -- 7. 给无限金币（用于自动购回地块）
    pPlayer:GetTreasury():ChangeGoldBalance(999999);

    -- === 存储恢复数据到 PlayerProperty ===
    pPlayer:SetProperty(MC_PLAYER_CITY_RECOVER_KEY, playerRecoverNewCityProperty);

    -- === 销毁 + 重建 ===
    CityManager.DestroyCity(oldCity);
    pPlayer:GetCities():Create(newCityX, newCityY);
end
```

### 3.4 CityAddedToMap 恢复模式

```lua
function OnCityAddedToMapMC(playerID, cityID, iX, iY)
    if LoadScreenFinished == -1 then return end  -- 读档时跳过

    local pPlayer = Players[playerID];
    if pPlayer == nil or not pPlayer:IsHuman() then return end

    -- 设置初始 Property
    pCity:SetProperty(MC_CITY_KEY, 0);
    pCity:SetProperty(MC_CITY_TAKE_PLACE_KEY, 666);

    -- 读取恢复数据
    local playerRecoverNewCityProperty = pPlayer:GetProperty(MC_PLAYER_CITY_RECOVER_KEY);
    if playerRecoverNewCityProperty == nil then return end

    -- 恢复名称和人口
    pCity:SetName(playerRecoverNewCityProperty.name);
    pCity:ChangePopulation(playerRecoverNewCityProperty.population - pCity:GetPopulation());

    -- 恢复 Properties
    for k, v in pairs(my_pCityProperties) do
        if k ~= MC_CITY_RECOVER_KEY and k ~= MC_CITY_KEY then
            pCity:SetProperty(k, v);
        end
    end

    -- 恢复市中心建筑
    for bik, biv in ipairs(cityBuildingIndexlist) do
        local buildingInfo = GameInfo.Buildings[biv];
        if buildingInfo.PrereqDistrict == nil
           or GameInfo.Districts[buildingInfo.PrereqDistrict].Index == m_citycenter_district then
            if not buildingInfo.RequiresAdjacentRiver
               or targetPlot:IsRiver() or targetPlot:IsRiverAdjacent() then
                pCity:GetBuildQueue():CreateBuilding(biv);
            end
        end
    end

    -- 恢复区域（非引水渠，且地块已属玩家）
    for key, value in ipairs(cityDistrictPlotIndexlist) do
        local kPlot = Map.GetPlotByIndex(value);
        if kPlot:GetDistrictType() == -1 and kPlot:GetOwner() == playerID then
            WorldBuilder.CityManager():CreateDistrict(pCity, oldDistrictType, 100, kPlot);
            -- 同时创建该区域的建筑
            for cbik, cbiv in ipairs(cityBuildingIndexlist) do
                if buildingInfo.PrereqDistrict == oldDistrictTypeString then
                    pCity:GetBuildQueue():CreateBuilding(cbiv);
                end
            end
        end
    end

    -- 恢复宗教压力
    for key, rvalue in ipairs(cityReligionslist) do
        newCityReligion:AddReligiousPressure(playerID, religion.Index, pressure);
    end

    -- 恢复圣城
    if pHolyCityPlayerID ~= -1 then
        hcPlayerReligion:SetHolyCity(cityID);
    end

    -- 存储剩余待恢复数据到 CityProperty
    pCity:SetProperty(MC_CITY_RECOVER_KEY, newCityRecoverProperty);
    pPlayer:SetProperty(MC_PLAYER_CITY_RECOVER_KEY, nil);  -- 清空
end
```

### 3.5 地块购回模式（CityMadePurchase）

```lua
function OnCityMadePurchaseMC(playerID, cityID, plotX, plotY, purchaseType, objectType)
    if purchaseType ~= EventSubTypes.PLOT then return end

    local cityRecover = pCity:GetProperty(MC_CITY_RECOVER_KEY);
    if cityRecover == nil then return end

    -- 检查购回的地块是否在待恢复列表中
    for key, value in ipairs(cityRecover.cityPlots) do
        if value == kPlotIndex then
            -- 恢复改良设施
            if oldImprovementType ~= -1 then
                ImprovementBuilder.SetImprovementType(kPlot, oldImprovementType, kPlot:GetOwner());
            end
            -- 恢复区域
            if oldDistrictType ~= -1 then
                WorldBuilder.CityManager():CreateDistrict(pCity, oldDistrictType, 100, kPlot);
            end
            -- 从待恢复列表中移除
            table.remove(cityRecover.cityPlots, key);
        end
    end

    -- 最后一块地购回时，恢复初始金币
    if #cityRecover.cityPlots <= 1 then
        pPlayer:GetTreasury():SetGoldBalance(cityRecover.playerGold);
    end

    pCity:SetProperty(MC_CITY_RECOVER_KEY, cityRecover);
end
```

### 3.6 DistrictAddedToMap 中的建筑恢复

```lua
function OnDistrictAddedToMapMC(playerID, districtID, cityID, iX, iY, districtType, percentComplete)
    -- 跳过市中心和奇观区
    if districtType == "DISTRICT_CITY_CENTER" then return end

    local cityRecover = pCity:GetProperty(MC_CITY_RECOVER_KEY);

    -- 奇观区：自动完成建造
    if districtType == "DISTRICT_WONDER" then
        local pCurrentlyBuildingInfo = GameInfo.Buildings[pCurrentBuild];
        for key, value in pairs(cityRecover.wonders) do
            if value == pCurrentlyBuildingInfo.Index then
                pCityBuildQueue:FinishProgress();
                table.remove(cityRecover.wonders, key);
            end
        end
        return
    end

    -- OnePerCity 区域
    for k, v in pairs(cityRecover.districts) do
        if v == districtType then
            pCity:GetBuildQueue():FinishProgress();
            -- 恢复该区域内的建筑
            for k1, v1 in pairs(cityRecover.buildings) do
                if buildingInfo.PrereqDistrict == districtTypeString then
                    pCity:GetBuildQueue():CreateBuilding(v1);
                end
            end
            table.remove(cityRecover.districts, k);
        end
    end

    -- 非 OnePerCity 区域（如多个农场区）
    for k, v in pairs(cityRecover.districtNOPCs) do
        if v == districtType and cityRecover.districtNOPCNumbers[k] > 0 then
            cityRecover.districtNOPCNumbers[k] = cityRecover.districtNOPCNumbers[k] - 1;
            -- 同样恢复建筑
        end
    end
end
```

---

## 4. UI 层核心模式

### 4.1 地块选择模式

```lua
-- 进入选地块模式
function OnButtonClicked()
    UI.SetInterfaceMode(InterfaceModeTypes.SELECTION);
    UI.SetInterfaceMode(InterfaceModeTypes.WB_SELECT_PLOT);

    -- 高亮可选地块
    local selectablePlots, invalidPlots = GetPlotsMC(pPlot, 1);
    UILens.SetLayerHexesArea(HEX_COLORING_MOVEMENT, iPlayer, selectablePlots);
    UILens.ToggleLayerOn(HEX_COLORING_MOVEMENT);
end

-- 地块选中回调
LuaEvents.WorldInput_WBSelectPlot.Add(OnSelectPlotMC);

-- 检查地块有效性
function JudgeValidCityPlot(pPlotIndex, oldPlotIndex)
    if pPlot:IsWater() then return false end
    if GameInfo.Terrains[pPlotTerrainType].Impassable then return false end
    if not GameInfo.Features[pFeatureType].Settlement then return false end
    -- 检查 3 格内无其他城市
    -- 检查地块属于玩家
    -- 检查无其他玩家的单位
    return true
end
```

### 4.2 UI 按钮注入（挂到城市面板）

```lua
function InitializeMoveCityUI()
    -- 找到城市面板的 ActionStack，挂入自定义按钮
    local pContext = ContextPtr:LookUpControl("/InGame/CityPanel/ActionStack");
    Controls.MoveCityGrid:ChangeParent(pContext);
    Controls.MoveCityButton:RegisterCallback(Mouse.eLClick, OnButtonClicked);
end
Events.LoadGameViewStateDone.Add(InitializeMoveCityUI);
```

### 4.3 按钮可用性检查

```lua
function IsButtonDisabled(playerID, cityID)
    -- 不能移动原始首都
    if pCity:IsOriginalCapital() and pCityOriginalOwnerID == playerID then
        return true, 'LOC_MOVECITY_DISABLED_ORIGINAL_CAPITAL_TOOLTIP'
    end
    -- 如果没有任何原始首都，不能移动当前首都
    if not hasOriginalCapital and pCapital:GetID() == cityID then
        return true, 'LOC_MOVECITY_DISABLED_CAPITAL_AND_NO_ORIGINAL_CAPITAL_TOOLTIP'
    end
    -- 其他玩家的原始首都，如果原主已灭则不能移动
    if isOtherMajorOriginalCapital and not pCityOriginalOwner:IsAlive() then
        return true, 'LOC_MOVECITY_DISABLED_OTHER_ORIGINAL_CAPITAL_NOT_ALIVE_TOOLTIP'
    end
    -- 检查是否已完成移动项目
    if property == 0 then
        return true, 'LOC_MOVECITY_DISABLED_NOT_FINISHED_PROJECT_TOOLTIP'
    end
    return false, ''
end
```

---

## 5. 恢复数据结构

玩家移动城市时的完整数据包（存于 PlayerProperty / CityProperty）：

```lua
playerRecoverNewCityProperty = {
    targetPlotIndex        = 0,     -- 新位置 plot index
    oldPlotIndex           = 0,     -- 旧位置 plot index
    name                   = "",    -- 城市名
    population             = 0,     -- 人口
    playerGold             = 0,     -- 移动前金币（用于恢复）
    cityReligions          = {},    -- 宗教列表
    cityReligionsPressure  = {},    -- 宗教压力列表
    pHolyCityPlayerID      = -1,    -- 圣城所属玩家
    cityPlots              = {},    -- 待购回地块 ID 列表（围城 4 环内）
    cityPlotImprovements   = {},    -- 对应地块的改良类型
    districts              = {},    -- OnePerCity 区域列表
    districtPlotIDs        = {},    -- 区域对应地块 ID
    districtNOPCs          = {},    -- 非 OnePerCity 区域列表
    districtNOPCNumbers    = {},    -- 非 OnePerCity 区域数量
    buildings              = {},    -- 所有建筑 Index 列表
    wonders                = {},    -- 奇观 Index 列表
}
```

---

## 6. 关键 API 速查

### 城市操作
```lua
CityManager.DestroyCity(pCity)                 -- 摧毁城市
pPlayer:GetCities():Create(x, y)               -- 创建城市
WorldBuilder.CityManager():CreateDistrict(pCity, districtType, 100, kPlot)  -- 创建区域
CityManager.SetAsOriginalCapital(pCity)        -- 设为原始首都

-- 建筑
pCity:GetBuildQueue():CreateBuilding(buildingIndex)      -- 添加建筑到队列
pCity:GetBuildQueue():FinishProgress()                   -- 立即完成当前建造
pCityBldgs:HasBuilding(buildingIndex)                    -- 检查是否有建筑
pCityBldgs:RemoveBuilding(buildingIndex)                 -- 移除建筑

-- 地块
WorldBuilder.CityManager():SetPlotOwner(plot, playerOrNil)  -- 设置地块归属
ImprovementBuilder.SetImprovementType(plot, type, owner)    -- 放置改良
ResourceBuilder.SetResourceType(plot, resourceType, amount) -- 放置资源
```

### 单位操作
```lua
UnitManager.GetUnit(playerID, unitID)    -- 获取单位对象
UnitManager.Kill(unit)                   -- 杀死单位
UnitManager.FinishMoves(unit)            -- 结束单位移动
```

### 宗教操作
```lua
pCityReligion:AddReligiousPressure(playerID, religionIndex, pressure)  -- 添加宗教压力
pPlayerReligion:SetHolyCity(cityID)                                     -- 设置圣城
```

### 地块信息
```lua
pPlot:GetOwner()          -- 地块所属玩家
pPlot:GetDistrictType()   -- 地块区域类型，-1 表示无
pPlot:GetImprovementType()-- 地块改良类型
pPlot:GetResourceType()   -- 地块资源类型
pPlot:IsCity()            -- 是否有城市
pPlot:IsWater()           -- 是否水域
Map.GetPlotDistance(x1, y1, x2, y2)  -- 两地块距离
Map.GetNeighborPlots(x, y, range)     -- 获取范围内相邻地块
```

### UI 透镜
```lua
local lens = UILens.CreateLensLayerHash("Hex_Coloring_Movement");
UILens.SetLayerHexesArea(lens, playerID, plotIndexList);
UILens.ToggleLayerOn(lens);
UILens.ToggleLayerOff(lens);
UILens.ClearLayerHexes(lens);
```

---

## 7. 关键提醒

- **EXECUTE_SCRIPT 参数**：首个字段必须是 `OnStart = 'GameEventName'`，对应 Gameplay 层注册的 `GameEvents.XXX.Add(callback)`
- **读档保护**：所有事件回调开头检查 `if LoadScreenFinished == -1 then return end`，防止读档时重复恢复
- **PlayerProperty 用于传递跨上下文数据**：UI 执行 EXECUTE_SCRIPT 后数据通过 PlayerProperty 传递给 Gameplay 的事件
- **恢复顺序很重要**：先恢复地块归属，再恢复区域，最后恢复建筑
- **奇观 rebuild**需要把 MaxWorldInstances 改回 -1，否则无法重建
- **恢复建筑时检查河流条件**：需要河流的建筑如果目标地块没有河流则跳过
- **金币技巧**：移动前给无限金币，购回完成后恢复原始金币数
- **原始首都保护**：不能移动原始首都；移动别人的原始首都时需先转移原始首都标记
