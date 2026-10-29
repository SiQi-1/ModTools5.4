# lua-gp-resource — 非战斗类 GP 函数 — 地块/建造/计数

> 分册：由 [lua-gp-resource.md](lua-gp-resource.md) 按主题拆出；覆盖 地块购买、金币购买地块（Wuxian / 通用）、信仰购买地块（0026 / FAITH_BUY_PLOTS 通用）、建造/生产加强、区域瞬间完成（0015：首个专业化区域免费秒建）、建造单位翻倍（0028：特定区域所在城市造战斗单位→额外送一个）、`Events.CityProductionCompleted` — `iConstructionType` 值、`Events.CityMadePurchase` — `purchaseType` 值（`EventSubTypes` 枚举）、区域完成时赠送最低级建筑（0028）、计数/里程碑系统、改良计数里程碑奖励（0026：农场/种植园分别计数，按 3/6/9/12/36 档发奖）、城市资源种类追踪（0026：奖励资源每类仅第一份计入区域产出加成）。触发：地块购买、建造生产、计数里程碑时。

## 地块购买

### 金币购买地块（Wuxian / 通用）

UI 计算价格 → 通过 GameEvent 传入 → GP 端 AnnexPlotByXY + 扣金币。

```lua
function PurchasePlotFromGold(playerID, params)
    local iX, iY = params.iX, params.iY
    local cost = params.Cost or 0
    local cityID = params.CityID or -1
    local pCity = CityManager.GetCity(playerID, cityID)
    if not pCity then return end
    pCity:AnnexPlotByXY(iX, iY)
    Players[playerID]:GetTreasury():ChangeGoldBalance(-cost)
end
```

### 信仰购买地块（0026 / FAITH_BUY_PLOTS 通用）

与金币版对称，扣信仰。0026 另有总督 R2 消费返利 20% 配合（见下方“金币消费返利”）。

```lua
function PurchasePlotFromFaith(playerID, params)
    local iX, iY = params.iX, params.iY
    local cost = params.Cost or 0
    local cityID = params.CityID or -1
    local pCity = CityManager.GetCity(playerID, cityID)
    if not pCity then return end
    pCity:AnnexPlotByXY(iX, iY)
    Players[playerID]:GetReligion():ChangeFaithBalance(-cost)
end
```

---

## 建造/生产加强

### 区域瞬间完成（0015：首个专业化区域免费秒建）

监听 CityProductionChanged，检测到要建的是需要人口的区域（RequiresPopulation），且城市从未用过此能力（Hash Property），则 FinishProgress() 秒出。

```lua
local HASH_SPE_PROPERTY = DB.MakeHash('Siqi0015_HasSpecialtyDistrict')

function OnCityProductionChanged_DistrictInstant(playerID, cityID, orderType, objectID, bCancelled)
    -- orderType ~= 2 即非区域类型，跳过
    if orderType ~= 2 then return end
    local pCity = CityManager.GetCity(playerID, cityID)
    if pCity:GetProperty(HASH_SPE_PROPERTY) then return end  -- 已用过
    local product = GameInfo.Districts[objectID]
    if not product then return end
    if not product.RequiresPopulation then return end       -- 仅限需要人口的区域
    pCity:SetProperty(HASH_SPE_PROPERTY, true)
    pCity:GetBuildQueue():FinishProgress()
end
```

### 建造单位翻倍（0028：特定区域所在城市造战斗单位→额外送一个）

### `Events.CityProductionCompleted` — `iConstructionType` 值

| iConstructionType | 大类 | itemID 查表 |
|-------------------|------|-----------|
| 0 | 单位 | `GameInfo.Units[itemID]` |
| 1 | 建筑/奇观 | `GameInfo.Buildings[itemID]` |
| 2 | 区域 | `GameInfo.Districts[itemID]` |
| 3 | 项目 | `GameInfo.Projects[itemID]` |

### `Events.CityMadePurchase` — `purchaseType` 值（`EventSubTypes` 枚举）

| purchaseType | 大类 | objectType 查表 |
|-------------|------|---------------|
| `EventSubTypes.UNIT` | 购买单位 | `GameInfo.Units[objectType]` |
| `EventSubTypes.BUILDING` | 购买建筑 | `GameInfo.Buildings[objectType]` |
| `EventSubTypes.DISTRICT` | 购买区域 | `GameInfo.Districts[objectType]` |
| `EventSubTypes.PLOT` | 购买地块 | — |

> 参数顺序：`Events.CityMadePurchase(playerID, cityID, iX, iY, purchaseType, objectType)`
> 购买不受 `CityProductionCompleted` 覆盖，如需同时检测生产和购买，两个事件都要注册。

监听 CityProductionCompleted，检测到生产的是战斗单位且城市有目标区域，InitUnit 再送一个同款单位。陆地在城市坐标生成，海军查港口坐标。

```lua
function OnCityProductionCompleted_UnitDup(playerID, cityID, iConstructionType, itemID)
    if iConstructionType ~= 0 then return end          -- 0 = 单位
    local pCity = CityManager.GetCity(playerID, cityID)
    local pCityDistricts = pCity:GetDistricts()
    if not pCityDistricts:HasDistrict(m_district, true) then return end

    local unitinfo = GameInfo.Units[itemID]
    if not unitinfo or unitinfo.Combat <= 0 then return end

    if unitinfo.Domain == "DOMAIN_LAND" then
        UnitManager.InitUnit(playerID, unitinfo.UnitType, pCity:GetX(), pCity:GetY())
    elseif unitinfo.Domain == "DOMAIN_SEA" then
        local iX, iY = pCity:GetX(), pCity:GetY()
        local harborInfo = GameInfo.Districts['DISTRICT_HARBOR']
        if pCityDistricts:HasDistrict(harborInfo.Index, true) then
            iX, iY = pCityDistricts:GetDistrictLocation(harborInfo.Index)
        end
        UnitManager.InitUnit(playerID, unitinfo.UnitType, iX, iY)
    end
end
```

### 区域完成时赠送最低级建筑（0028）

监听 CityProductionCompleted，检测到建了非特殊区域（排除市中心/政府区/奇观/自身），通过 DB.Query 按前置链排序取第一个建筑，GrantBuilding。

```lua
local NotDistricts = {
    ["DISTRICT_GOVERNMENT"] = true,
    ["DISTRICT_CITY_CENTER"] = true,
    ["DISTRICT_WONDER"] = true,
    -- 排除自身区域避免循环
}

function OnDistrictCompleted_GrantBuilding(playerID, cityID, iConstructionType, itemID)
    if iConstructionType ~= 2 then return end
    local DistrictInfo = GameInfo.Districts[itemID]
    if not DistrictInfo then return end
    if NotDistricts[DistrictInfo.DistrictType] then return end

    -- SQL 取该区域最低级建筑：按前置链深度排序取第一个
    local query = "SELECT b.BuildingType FROM Buildings b " ..
                  "LEFT JOIN BuildingPrereqs bp ON b.BuildingType = bp.Building OR b.BuildingType = bp.PrereqBuilding " ..
                  "WHERE b.PrereqDistrict = '" .. DistrictInfo.DistrictType .. "' AND TraitType IS NULL " ..
                  "GROUP BY b.BuildingType " ..
                  "ORDER BY CASE WHEN COUNT(bp.Building) = 0 THEN 0 " ..
                       "WHEN COUNT(CASE WHEN bp.Building = b.BuildingType THEN 1 END) = 0 " ..
                        "AND COUNT(CASE WHEN bp.PrereqBuilding = b.BuildingType THEN 1 END) > 0 THEN 1 ELSE 2 END"
    local result = DB.Query(query)
    if result and result[1] then
        GrantBuilding(playerID, cityID, result[1].BuildingType)
    end
end
```

---

## 计数/里程碑系统

### 改良计数里程碑奖励（0026：农场/种植园分别计数，按 3/6/9/12/36 档发奖）

监听 ImprovementAddedToMap，分别维护农场和种植园计数器，每达到 3 的倍数给金币/信仰，6 给尤里卡/鼓舞，9 给建造者/总督点，12 给能力选择，36 直接解锁目标市政。

```lua
function OnFarmMilestone(playerID, iX, iY, counterKey, rewardConfig)
    local pPlayer = Players[playerID]
    local Count = (pPlayer:GetProperty(counterKey) or 0) + 1

    -- rewardConfig = { gold=150, boost='TECH', unit='BUILDER', civic='CIVIC_FEUDALISM', property='...' }
    local era = pPlayer:GetEra() + 1
    local GAME_SPEED_MULTIPLIER = GameInfo.GameSpeeds[GameConfiguration.GetGameSpeedType()].CostMultiplier / 100

    if Count % 3 == 0 then
        Siqi_ChangeGold(playerID, math.floor(rewardConfig.gold * era * GAME_SPEED_MULTIPLIER))
    end
    if Count % 6 == 0 then
        pPlayer:AttachModifierByID(rewardConfig.boostModifier)
    end
    if Count % 9 == 0 then
        local pCity = GetNearestCity(iX, iY, playerID)
        if pCity then pCity:AttachModifierByID(rewardConfig.unitModifier) end
    end
    if Count % 12 == 0 then
        pPlayer:AttachModifierByID(rewardConfig.propertyModifier)
    end
    if Count == 36 then
        CompleteCivic(playerID, rewardConfig.targetCivic)
    end
    pPlayer:SetProperty(counterKey, Count)
end

-- 最近城市查找
function GetNearestCity(PlotX, PlotY, PlayerID)
    local dist = 9999
    local city = nil
    for _, pCity in Players[PlayerID]:GetCities():Members() do
        local iDistance = Map.GetPlotDistance(PlotX, PlotY, pCity:GetX(), pCity:GetY())
        if iDistance < dist then dist = iDistance; city = pCity end
    end
    return city or Players[PlayerID]:GetCities():GetCapitalCity()
end
```

### 城市资源种类追踪（0026：奖励资源每类仅第一份计入区域产出加成）

监听 ImprovementAddedToMap / RemovedFromMap，检查资源类型是否是奖励资源（RESOURCECLASS_BONUS），按城市归属追踪每类资源的份数。第一份出现时 ChangeplotNum +1，最后一份消失时 -1。

```lua
function OnBonusResourceTrack(iX, iY, eImprovement, playerID, isAdd)
    local pPlot = Map.GetPlot(iX, iY)
    local resourceID = pPlot:GetResourceType()
    if resourceID == -1 then return end
    local resourceInfo = GameInfo.Resources[resourceID]
    if not resourceInfo or resourceInfo.ResourceClassType ~= "RESOURCECLASS_BONUS" then return end

    local pCity = Cities.GetPlotPurchaseCity(pPlot)
    if not pCity then return end
    local pCityPlot = Map.GetPlot(pCity:GetX(), pCity:GetY())
    local key = "Siqi0026_" .. resourceInfo.ResourceType
    local HasRes = pCity:GetProperty(key) or 0

    if isAdd then
        HasRes = HasRes + 1
        pCity:SetProperty(key, HasRes)
        if HasRes == 1 then  -- 第一份该资源
            ChangeplotNum(pCityPlot:GetIndex(), 'PROPERTY_DISTRICT_', 1, 5)
        end
    else
        HasRes = HasRes - 1
        if HasRes <= 0 then
            pCity:SetProperty(key, 0)
            ChangeplotNum(pCityPlot:GetIndex(), 'PROPERTY_DISTRICT_', -1, 5)
        else
            pCity:SetProperty(key, HasRes)
        end
    end
end
```

---

