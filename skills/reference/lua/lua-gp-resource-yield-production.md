# lua-gp-resource — 非战斗类 GP 函数 — 产出/生产

> 分册：由 [lua-gp-resource.md](lua-gp-resource.md) 按主题拆出；覆盖 产出、ChangeScience / ChangeCulture / ChangeGold / ChangeFaith — 一次性产出修改、ChangeProduction — 一次性生产力修改（指定城市或全部城市）、FinishProduction — 立即完成当前生产任务、OnGoldProduction — 金币购买生产力（凝光核心：1:2 比率 + 总督返还 20%）、游戏速度倍率（固定写法）、AddWonderProgress — 按百分比推进奇观建造、生产力/奇观、闲云：奇观建成 → 其他在建奇观推进 20%、闲云：派遣总督 → 奇观 +80% 进度（2 回合冷却）、大工程司：加速区域重建（拆除→立即重建）、桃金娘：无生产任务时奖励产出。触发：改产出、生产力、奇观时。

## 产出

### ChangeScience / ChangeCulture / ChangeGold / ChangeFaith — 一次性产出修改

```lua
function ChangeScience(playerID, amount)  -- 科技进度
    Players[playerID]:GetTechs():ChangeCurrentResearchProgress(amount)
end
function ChangeCulture(playerID, amount)  -- 文化进度
    Players[playerID]:GetCulture():ChangeCurrentCulturalProgress(amount)
end
function ChangeGold(playerID, amount)     -- 金币余额
    Players[playerID]:GetTreasury():ChangeGoldBalance(amount)
end
function ChangeFaith(playerID, amount)    -- 信仰余额
    Players[playerID]:GetReligion():ChangeFaithBalance(amount)
end
```

### ChangeProduction — 一次性生产力修改（指定城市或全部城市）

```lua
function ChangeProduction(playerID, amount, cityID)
    local pPlayer = Players[playerID]
    if not cityID then
        -- 未指定城市：全部城市 +amount 生产力
        local pCities = pPlayer:GetCities()
        for _, pCity in pCities:Members() do
            pCity:GetBuildQueue():AddProgress(amount)
        end
        return
    end
    local pCity = CityManager.GetCity(playerID, cityID)
    if pCity then
        pCity:GetBuildQueue():AddProgress(amount)
    end
end
```

### FinishProduction — 立即完成当前生产任务

```lua
function FinishProduction_AllCities(playerID)
    local pPlayer = Players[playerID]
    local pPlayerCities = pPlayer:GetCities()
    for i, pCity in pPlayerCities:Members() do
        pCity:GetBuildQueue():FinishProgress()
    end
end
```

### OnGoldProduction — 金币购买生产力（凝光核心：1:2 比率 + 总督返还 20%）

GP 接收 UI 请求，按比率扣金币注入生产力。凝光能力：总督 3 级晋升城市返还 20%。

```lua
function OnGoldProduction(playerID, params)
    if params == nil then return end
    if params.CityID == nil then return end

    local goldCost = params.GoldCost or 0
    local ratio = params.GoldPerProduction or 2   -- 默认 1:2，凝光 R2 为 1:3
    if goldCost <= 0 then return end

    local pPlayer = Players[playerID]
    if not pPlayer then return end
    local pCity = CityManager.GetCity(playerID, params.CityID)
    if not pCity then return end

    -- GP-safe: 用 CurrentlyBuilding() 判断是否在生产
    local typeName = pCity:GetBuildQueue():CurrentlyBuilding()
    if not typeName or typeName == '' or typeName == -1 then return end

    ChangeGold(playerID, -goldCost)
    local prodAmount = math.floor(goldCost / ratio)
    pCity:GetBuildQueue():AddProgress(prodAmount)

    -- 凝光基础：总督城市消耗金币返还 20%
    if HasProperty(pPlayer, 'SIQI32_L0032_4_GOV_ACTIVE')
        and ExposedMembers.Siqi32 and ExposedMembers.Siqi32.IsNingGovEstablished3Titles
        and ExposedMembers.Siqi32.IsNingGovEstablished3Titles(playerID, params.CityID) then
        local refund = math.floor(goldCost * 0.2)
        if refund > 0 then
            ChangeGold(playerID, refund)
            AddYieldStringToWorld(refund, 'YIELD_GOLD', pCity:GetX(), pCity:GetY())
        end
    end
end

-- 注册示例（Scripts 中）：
-- GameEvents.Siqi32_GoldProduction.Add(OnGoldProduction)
```

### 游戏速度倍率（固定写法）

**统一写法（必用，勿再手写 `GameSpeeds[GameSpeed]`——`GameSpeed` 是未定义全局）**：

```lua
-- 模块级常量（GP/UI 环境通用）
local GAME_SPEED = GameConfiguration.GetGameSpeedType()
local GAME_SPEED_MULTIPLIER = GameInfo.GameSpeeds[GAME_SPEED] and GameInfo.GameSpeeds[GAME_SPEED].CostMultiplier / 100 or 1
```

- 含义：标准=1.0、快速=0.67、史诗=1.5、马拉松=3.0
- nil 安全：`GameSpeeds[GAME_SPEED]` 不存在时回退 1
- 用法示例：`local ironCost = math.max(1, math.floor(COST * GAME_SPEED_MULTIPLIER))`
- 若需百分比（如 100/150/300）而非倍率：`GAME_SPEED_MULTIPLIER * 100`

### AddWonderProgress — 按百分比推进奇观建造

传入 city、wonderIndex、百分比（如 30 = 30%），自动处理游戏速度。

```lua
function AddWonderProgress(pCity, wonderIndex, speedPercent)
    local buildingInfo = GameInfo.Buildings[wonderIndex]
    if buildingInfo == nil or buildingInfo.Cost == nil then
        return false
    end

    local iSpeed = GameConfiguration.GetGameSpeedType()
    local multiplier = GameInfo.GameSpeeds[iSpeed] and GameInfo.GameSpeeds[iSpeed].CostMultiplier or 100
    local percent = speedPercent or 30
    if percent <= 0 then return false end

    local amount = buildingInfo.Cost * multiplier * percent / 10000
    pCity:GetBuildQueue():AddProgress(amount)
    return true
end
```

---

## 生产力/奇观

### 闲云：奇观建成 → 其他在建奇观推进 20%

```lua
function OnXianyunWonderPush(playerID, cityID, iConstructionType, itemID, bCancelled)
    if bCancelled then return end
    if iConstructionType ~= 1 then return end

    local info = GameInfo.Buildings[itemID]
    if not info or not info.IsWonder then return end

    local pPlayer = Players[playerID]
    if not pPlayer then return end
    if not HasProperty(pPlayer, 'SIQI32_LEADER_XIANYUN') then return end

    for _, pCity in pPlayer:GetCities():Members() do
        local typeName = pCity:GetBuildQueue():CurrentlyBuilding()
        if typeName and typeName ~= '' then
            local buildingInfo = GameInfo.Buildings[typeName]
            if buildingInfo and buildingInfo.IsWonder then
                local pushAmount = math.floor(buildingInfo.Cost * GAME_SPEED_MULTIPLIER * 0.2)
                if pushAmount > 0 then
                    pCity:GetBuildQueue():AddProgress(pushAmount)
                end
            end
        end
    end
end

```

### 闲云：派遣总督 → 奇观 +80% 进度（2 回合冷却）

```lua
function OnXianyunGovernorAssigned(cityOwner, cityID, governorOwner, governorType)
    if governorType ~= GameInfo.Governors["GOVERNOR_SIQI_G0032_2"].Index then return end

    local pPlayer = Players[cityOwner]
    if not pPlayer then return end

    -- 2 回合冷却检查
    local lastTurn = pPlayer:GetProperty('SIQI32_XIANYUN_GOV_COOLDOWN') or 0
    local currentTurn = Game.GetCurrentGameTurn()
    if currentTurn - lastTurn < 2 then return end

    local pCity = CityManager.GetCity(cityOwner, cityID)
    if not pCity then return end

    local typeName = pCity:GetBuildQueue():CurrentlyBuilding()
    if not typeName or typeName == '' then return end

    local buildingInfo = GameInfo.Buildings[typeName]
    if not buildingInfo or not buildingInfo.IsWonder then return end

    local amount = math.floor(buildingInfo.Cost * GAME_SPEED_MULTIPLIER * 0.8)
    if amount > 0 then
        pCity:GetBuildQueue():AddProgress(amount)
        pPlayer:SetProperty('SIQI32_XIANYUN_GOV_COOLDOWN', currentTurn)
    end
end

```

### 大工程司：加速区域重建（拆除→立即重建）

移除区域并立即重新创建，消耗单位行动次数。

```lua
function SpeedDistrict(iPlayer, Param)
    local pPlot = Map.GetPlot(Param.iX, Param.iY)
    local pUnit = UnitManager.GetUnit(iPlayer, Param.iUnit)
    local eDistrict = GameInfo.Districts[Map.GetPlot(Param.iX, Param.iY):GetDistrictType()].Index
    local pDistrict = CityManager.GetDistrictAt(Param.iX, Param.iY)
    local pCity = Cities.GetPlotPurchaseCity(pPlot)

    WorldBuilder.CityManager():RemoveDistrict(pDistrict)
    pCity:GetBuildQueue():CreateDistrict(eDistrict, pPlot:GetIndex())
    pUnit:ChangeActionCharges(-1)
    UnitManager.FinishMoves(pUnit)
end

```

### 桃金娘：无生产任务时奖励产出

城市无建造任务时 UI 计算产出表 → GP 发放。

```lua
function MyrtleOnPlayerTurnDeactivated(playerID, params)
    local pPlayer = Players[playerID]
    local YieldTable = params.yieldtable
    pPlayer:GetTreasury():ChangeGoldBalance(2 * YieldTable[2])          -- 金币产出
    pPlayer:GetTechs():ChangeCurrentResearchProgress(2 * YieldTable[3]) -- 科技产出
    pPlayer:GetCulture():ChangeCurrentCulturalProgress(2 * YieldTable[4]) -- 文化产出
    -- 给予 +2 大将军点数
    local General = GameInfo.GreatPersonClasses['GREAT_PERSON_CLASS_GENERAL'].Index
    pPlayer:GetGreatPeoplePoints():ChangePointsTotal(General, 2)
end

```

---

