# lua-gp-resource — 非战斗类 GP 函数 — 经济/触发/数据

> 分册：由 [lua-gp-resource.md](lua-gp-resource.md) 按主题拆出；覆盖 消费返利系统、金币消费返利 20%（0026：总督 R2 晋升城市购买时自动返还 20% 金币）、科技市政操作、直接完成指定市政（0026 / 通用）、直接完成指定科技（通用）、尤里卡触发时抽奖（0024：30% 概率触发随机鼓舞/尤里卡）、征服、城市征服奖励（0034：金币按区域数量+减少人口保底）、奇观/伟人触发、奇观完成随机奖励（0028：尤里卡/鼓舞二选一 + 随机 100 伟人点）、累计/阈值系统、灵值累积系统（0024：每回合累加资源，满 200 触发进度+重置）、多源进度追踪系统（0024：伟人/宗教/黄金时代/项目多来源累计，26 点胜利）、项目完成奖励、工程项目完成 → 一次性 AttachModifierByID 多重奖励（0027）、首都切换（0018：项目完成后将当前城市设为首都）、城市生产状态追踪、生产队列变更时写地块 Property（0019：标记城市是否正在执行目标项目）、城市数据、城市主流宗教获取（0027/0028 Support：GP 端通用）、玩家科文进度系数（0027/0028 Support：1~10 的动态系数）、自定义资源/货币系统、Game Property 自定义余额系统（0015 香韵：玩家独立余额）、工人创建/移除地貌资源（0015：消耗自定义资源创建 Feature/Resource）。触发：消费返利、征服、奇观触发、阈值系统、自定义货币时。

## 消费返利系统

### 金币消费返利 20%（0026：总督 R2 晋升城市购买时自动返还 20% 金币）

监听 TreasuryChanged（记录差值）和 CityMadePurchase（标记购买完成），若玩家有总督 R2 属性则返还金币差值的 20%。

```lua
function OnTreasuryChanged_Refund(playerID, yield, balance)
    local pPlayer = Players[playerID]
    local lastGold = pPlayer:GetProperty("Siqi0026GoldBalance") or 0
    local diff = balance - lastGold
    -- 只记录负差（消费）
    if diff < 0 then
        pPlayer:SetProperty("Siqi0026GoldDifference", diff)
    end
    pPlayer:SetProperty("Siqi0026GoldBalance", balance)
    -- 如果购买标记已就绪，立即结算
    if pPlayer:GetProperty("Siqi0026CityMadePurchase") then
        ApplyGoldRefund(playerID)
    end
end

function OnCityMadePurchase_Refund(playerID, cityID, iX, iY, purchaseType, objectType)
    local pPlayer = Players[playerID]
    local pCity = CityManager.GetCity(playerID, cityID)
    if not pCity then return end
    -- 检查总督 R2 属性：城市有该属性则触发返利
    if not HasProperty(pPlayer, 'PROPERTY_SIQI0026_GOVERNOR_PROMOTIONS') then return end
    if not HasProperty(pCity, 'PROPERTY_SIQI0026_GOVERNOR_PROMOTIONS_COUNT') then return end
    pPlayer:SetProperty("Siqi0026CityMadePurchase", true)
    ApplyGoldRefund(playerID)
end

function ApplyGoldRefund(playerID)
    local pPlayer = Players[playerID]
    local diff = pPlayer:GetProperty("Siqi0026GoldDifference") or 0
    local madePurchase = pPlayer:GetProperty("Siqi0026CityMadePurchase") or false
    if not madePurchase or diff == 0 then return end
    -- 返还 20%
    Siqi_ChangeGold(playerID, math.floor(math.abs(diff) * 0.2))
    pPlayer:SetProperty("Siqi0026GoldDifference", 0)
    pPlayer:SetProperty("Siqi0026CityMadePurchase", false)
end
```

---

## 科技市政操作

### 直接完成指定市政（0026 / 通用）

```lua
function CompleteCivic(playerID, civicType)
    local pPlayer = Players[playerID]
    local playerCivics = pPlayer:GetCulture()
    local civicInfo = GameInfo.Civics[civicType]
    if not civicInfo then return end
    if not playerCivics:HasCivic(civicInfo.Index) then
        playerCivics:SetCulturalProgress(civicInfo.Index, playerCivics:GetCultureCost(civicInfo.Index))
    end
end
```

### 直接完成指定科技（通用）

```lua
function CompleteTech(playerID, techType)
    local pPlayer = Players[playerID]
    local playerTechs = pPlayer:GetTechs()
    local techInfo = GameInfo.Technologies[techType]
    if not techInfo then return end
    if not playerTechs:HasTech(techInfo.Index) then
        playerTechs:SetResearchProgress(techInfo.Index, playerTechs:GetResearchCost(techInfo.Index))
    end
end
```

### 尤里卡触发时抽奖（0024：30% 概率触发随机鼓舞/尤里卡）

监听 TechBoostTriggered，查询城市有 District Property(D3) 加成的次数，每触发一次科技尤里卡即进行一次 30% 概率抽奖。

```lua
function OnTechBoostTriggered_Lottery(playerId, boostedTech)
    local pPlayer = Players[playerId]
    local YLKNUM = pPlayer:GetProperty("PROPERTY_DISTRICT_D3_BONUS") or 0
    if YLKNUM <= 0 then return end
    local already = pPlayer:GetProperty("Siqi0024_YLK") or 0
    if already >= YLKNUM then return end

    local Rand = Game.GetRandNum(100) + 1
    if Rand <= 30 then
        pPlayer:SetProperty("Siqi0024_YLK", already + 1)
        if Game.GetRandNum(2) == 1 then
            pPlayer:AttachModifierByID("MODIFIER_GRANT_RANDOM_TECH_BOOST")
        else
            pPlayer:AttachModifierByID("MODIFIER_GRANT_RANDOM_CIVIC_BOOST")
        end
    end
end
```

---

## 征服

### 城市征服奖励（0034：金币按区域数量+减少人口保底）

监听 CityConquered，占领城市后按区域数量给金币（200 * 区域数 * 速度倍率），减少 2 人口但最低保留 1。

```lua
function OnCityConquered_Reward(newPlayerID, oldPlayerID, newCityID, iCityX, iCityY)
    local pCity = Cities.GetCityInPlot(iCityX, iCityY)
    if not pCity then return end
    local numDistricts = pCity:GetDistricts():GetNumDistricts()
    local goldReward = math.floor(200 * numDistricts * GAME_SPEED_MULTIPLIER)
    ChangeGold(newPlayerID, goldReward)
    AddYieldStringToWorld(goldReward, "YIELD_GOLD", iCityX, iCityY)

    -- 减少人口：>2 减 2，==2 减 1，最低保留 1
    local nowPop = pCity:GetPopulation()
    if nowPop > 2 then
        pCity:ChangePopulation(-2)
    elseif nowPop == 2 then
        pCity:ChangePopulation(-1)
    end
end
```

---

## 奇观/伟人触发

### 奇观完成随机奖励（0028：尤里卡/鼓舞二选一 + 随机 100 伟人点）

监听 WonderCompleted，随机科技或市政鼓舞，再从 9 种伟人类别中随机一个给 100 点数。

```lua
local TABLE_INDEX_GREAT_PEOPLE = {
    GameInfo.GreatPersonClasses["GREAT_PERSON_CLASS_GENERAL"].Index,
    GameInfo.GreatPersonClasses["GREAT_PERSON_CLASS_ADMIRAL"].Index,
    GameInfo.GreatPersonClasses["GREAT_PERSON_CLASS_PROPHET"].Index,
    GameInfo.GreatPersonClasses["GREAT_PERSON_CLASS_SCIENTIST"].Index,
    GameInfo.GreatPersonClasses["GREAT_PERSON_CLASS_MERCHANT"].Index,
    GameInfo.GreatPersonClasses["GREAT_PERSON_CLASS_ENGINEER"].Index,
    GameInfo.GreatPersonClasses["GREAT_PERSON_CLASS_WRITER"].Index,
    GameInfo.GreatPersonClasses["GREAT_PERSON_CLASS_ARTIST"].Index,
    GameInfo.GreatPersonClasses["GREAT_PERSON_CLASS_MUSICIAN"].Index,
}

function OnWonderCompleted_Reward(iX, iY, buildingIndex, playerIndex, cityID)
    local pPlayer = Players[playerIndex]
    -- 随机鼓舞或尤里卡
    if Game.GetRandNum(2) == 1 then
        pPlayer:AttachModifierByID('MODIFIER_TECHNOLOGY_BOOST')
    else
        pPlayer:AttachModifierByID('MODIFIER_CIVIC_BOOST')
    end
    -- 随机伟人类别 +100 点
    local idx = Game.GetRandNum(#TABLE_INDEX_GREAT_PEOPLE) + 1
    pPlayer:GetGreatPeoplePoints():ChangePointsTotal(TABLE_INDEX_GREAT_PEOPLE[idx], 100)
end
```

---

## 累计/阈值系统

### 灵值累积系统（0024：每回合累加资源，满 200 触发进度+重置）

每回合 Player Property + 区域属性加成，达到阈值（200）触发刷新回调并重置。与星辉系统类似但阈值不同。

```lua
function OnTurnActivated_LZ(playerID)
    local pPlayer = Players[playerID]
    local LZnum = pPlayer:GetProperty("Siqi0024_LingZhi") or 0
    local LZperturn = pPlayer:GetProperty("PROPERTY_DISTRICT_D5_BONUS") or 0
    if LZperturn <= 0 then return end

    LZnum = LZnum + LZperturn
    if LZnum >= 200 then
        -- 触发进度奖励（如胜利进度 Tracking）
        OnThresholdReached(playerID)
        pPlayer:SetProperty("Siqi0024_LingZhi", LZnum - 200)
        return
    end
    pPlayer:SetProperty("Siqi0024_LingZhi", LZnum)
end
```

### 多源进度追踪系统（0024：伟人/宗教/黄金时代/项目多来源累计，26 点胜利）

多种事件（伟人诞生 +1、创建宗教 +1、黄金时代 +1、完成项目 +1）统一写入 Player Property 累加计数器，到达 26 时授予胜利建筑并重置。同时维护 Tooltip 日志表记录触发来源和回合。

```lua
function TrackingProgress_Add(playerID, reasonText)
    local pPlayer = Players[playerID]
    local SL = "Siqi0024_ShengLing"
    local oldSL = pPlayer:GetProperty(SL) or 0
    oldSL = oldSL + 1

    if oldSL >= 26 then
        -- 达到 26：授予胜利建筑
        local pCapital = pPlayer:GetCities():GetCapitalCity()
        if pCapital then
            GrantBuilding(playerID, pCapital:GetID(), 'BUILDING_SIQI0024')
        end
        return
    end
    pPlayer:SetProperty(SL, oldSL)

    -- 工具提示日志
    local SLTooltips = pPlayer:GetProperty("Siqi0024_ShengLing_Tooltip") or {}
    table.insert(SLTooltips, reasonText .. " (回合" .. Game.GetCurrentGameTurn() .. ")")
    pPlayer:SetProperty("Siqi0024_ShengLing_Tooltip", SLTooltips)
    BroadcastRefresh()
end

-- 事件绑定示例：
-- Events.UnitGreatPersonCreated.Add(...)     → TrackingProgress_Add(playerID, '伟人诞生')
-- Events.ReligionFounded.Add(...)            → TrackingProgress_Add(playerID, '创建宗教')
-- Events.GameEraChanged.Add(...)             → 检查黄金时代 → TrackingProgress_Add(playerID, '黄金时代')
-- Events.CityProjectCompleted.Add(...)       → TrackingProgress_Add(playerID, '项目完成')
```

---

## 项目完成奖励

### 工程项目完成 → 一次性 AttachModifierByID 多重奖励（0027）

项目完成后 Attach 多项 Modifier（单位能力、城市产出加成），并给外交支持。支持倍数 = 玩家科文进度（GetPlayerProgress）。

```lua
function OnProjectCompleted_GrantModifiers(playerID, cityID, projectID)
    local pPlayer = Players[playerID]
    pPlayer:SetProperty("Property_Completed_Project", 1)
    -- 注意: AttachModifierByID 参数是 0027 自定义的 ModifierId（非标准类型），新 Mod 需自行定义同名 Modifier
    pPlayer:AttachModifierByID('MODIFIER_GRANT_ABILITY')
    pPlayer:AttachModifierByID('MODIFIER_ADJUST_CITY_YIELD_SCIENCE_MODIFIER')
    pPlayer:AttachModifierByID('MODIFIER_ADJUST_CITY_YIELD_CULTURE_MODIFIER')
    -- 外交支持 = 20 * 科文进度系数 (1~10)
    pPlayer:GetDiplomacy():ChangeFavor(math.floor(20 * GetPlayerProgress(playerID)))
end
```

### 首都切换（0018：项目完成后将当前城市设为首都）

```lua
function OnProjectCompleted_SetCapital(playerID, cityID, projectID)
    local pCity = CityManager.GetCity(playerID, cityID)
    CityManager.SetAsCapital(pCity)
end
```

---

## 城市生产状态追踪

### 生产队列变更时写地块 Property（0019：标记城市是否正在执行目标项目）

监听 CityProductionChanged，若 orderType==3（项目）且是目标项目则 set Plot Property=1，否则清零。UI 或 Modifier 可据此判断城市是否在执行特定项目。

```lua
local PROPERTY_PROJECT = DB.MakeHash("SIQI_0019_PROJECT_PROPERTY")

function OnCityProductionChanged_TrackProject(playerID, cityID, orderType, objectID)
    local pCity = CityManager.GetCity(playerID, cityID)
    local pPlot = Map.GetPlot(pCity:GetX(), pCity:GetY())
    local targetProject = GameInfo.Projects['PROJECT_SIQI_P0019'].Index

    if orderType ~= 3 then  -- 非项目
        if pPlot:GetProperty(PROPERTY_PROJECT) == 1 then
            pPlot:SetProperty(PROPERTY_PROJECT, 0)
        end
    elseif orderType == 3 and objectID == targetProject then
        if pPlot:GetProperty(PROPERTY_PROJECT) ~= 1 then
            pPlot:SetProperty(PROPERTY_PROJECT, 1)
        end
    else
        pPlot:SetProperty(PROPERTY_PROJECT, 0)
    end
end
```

---

## 城市数据

### 城市主流宗教获取（0027/0028 Support：GP 端通用）

```lua
function GetCityReligion(playerID, cityID)
    local pCity = CityManager.GetCity(playerID, cityID)
    if not pCity then return -1 end
    return pCity:GetReligion():GetMajorityReligion()
end
```

### 玩家科文进度系数（0027/0028 Support：1~10 的动态系数）

取已研究科技/市政中较高的完成百分比，映射为 1 + 9 * floor(progress% * 100) / 100，即进度 0%→1，100%→10。

```lua
function GetPlayerProgress(playerID)
    local pPlayer = Players[playerID]
    local techTotal, techCurrent = 0, 0
    for row in GameInfo.Technologies() do
        techTotal = techTotal + 1
        if pPlayer:GetTechs():HasTech(row.Index) then techCurrent = techCurrent + 1 end
    end
    local civicTotal, civicCurrent = 0, 0
    for row in GameInfo.Civics() do
        civicTotal = civicTotal + 1
        if pPlayer:GetCulture():HasCivic(row.Index) then civicCurrent = civicCurrent + 1 end
    end
    local techProgress = techCurrent / techTotal
    local civicProgress = civicCurrent / civicTotal
    return 1 + 9 * math.floor(math.max(techProgress, civicProgress) * 100) / 100
end
```

---

## 自定义资源/货币系统

### Game Property 自定义余额系统（0015 香韵：玩家独立余额）

使用 Game:GetProperty/SetProperty 存储 `{ [playerID] = amount }` 的 table，而非 Player Property。适合 UI 端直接读取的全局资源。

```lua
-- 读取余额
function GetCustomBalance(playerID, gamePropertyKey)
    local balance = Game:GetProperty(gamePropertyKey) or {}
    return balance[playerID] or 0
end

-- 修改余额
function ChangeCustomBalance(playerID, amount, gamePropertyKey)
    local balance = Game:GetProperty(gamePropertyKey) or {}
    if balance[playerID] == nil then balance[playerID] = 0 end
    balance[playerID] = balance[playerID] + amount
    Game:SetProperty(gamePropertyKey, balance)
end

-- 初始化（LoadGameViewStateDone 中执行）
function InitCustomBalance(gamePropertyKey, traitType, initialAmount)
    if Game:GetProperty(gamePropertyKey) ~= nil then return end
    local balance = {}
    for _, pPlayer in ipairs(PlayerManager.GetAliveMajors()) do
        if HasTrait(pPlayer:GetID(), traitType) then
            balance[pPlayer:GetID()] = initialAmount
        end
    end
    Game:SetProperty(gamePropertyKey, balance)
end
```

### 工人创建/移除地貌资源（0015：消耗自定义资源创建 Feature/Resource）

工人消耗自定义货币，在目标地块创建 Feature 或 Resource，同时消耗工人行动力。移除时恢复部分货币。

```lua
function WorkerCreateFeatureOrResource(playerID, params)
    local pUnit = UnitManager.GetUnit(playerID, params.UnitID)
    local plot = Map.GetPlot(params.X, params.Y)
    if params.Type == 'FEATURE' then
        TerrainBuilder.SetFeatureType(plot, params.Index)
    elseif params.Type == 'RESOURCE' then
        ResourceBuilder.SetResourceType(plot, params.Index, 1)
    end
    UnitManager.FinishMoves(pUnit)
    ReduceUnitCharges(playerID, params.UnitID)
    -- 消耗自定义货币
    ChangeCustomBalance(playerID, -1, 'Siqi0015_XiangYun_Balance')
end

function WorkerRemoveFeatureOrResource(playerID, params)
    local plot = Map.GetPlot(params.iX, params.iY)
    -- 给有能力的城市加生产力
    local pPlayerCities = Players[playerID]:GetCities()
    local cost = params.cost or 0
    for _, pCity in pPlayerCities:Members() do
        if (pCity:GetProperty("Siqi0015_XiangYun_PerTurn") or 0) > 0 then
            pCity:GetBuildQueue():AddProgress(cost)
        end
    end
    if params.Feature then TerrainBuilder.SetFeatureType(plot, -1) end
    if params.Resource then ResourceBuilder.SetResourceType(plot, -1) end
    -- 返还自定义货币
    local num = (params.Feature and params.Resource) and 2 or 1
    ChangeCustomBalance(playerID, num * UNIT_AMOUNT, 'Siqi0015_XiangYun_Balance')
    -- 减少工人行动力或替换为侦察兵
    local pUnit = UnitManager.GetUnit(playerID, params.unitID)
    if pUnit then
        if pUnit:GetActionCharges() <= 1 then
            -- 替换为侦察兵
            local iX, iY = pUnit:GetX(), pUnit:GetY()
            UnitManager.Kill(pUnit)
            UnitManager.InitUnit(playerID, 'UNIT_SCOUT', iX, iY)
        else
            pUnit:ChangeActionCharges(-1)
        end
    end
end

-- 减少单位劳动力（遍历 16 个 Ability 槽找到空位）
function ReduceUnitCharges(playerID, unitID)
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    if not pUnit then return end
    local pUnitAbility = pUnit:GetAbility()
    for i = 1, 16 do
        if pUnitAbility:GetAbilityCount("ABILITY_SIQI_0015_REDUCED_CHARGE_" .. i) == 0 then
            pUnitAbility:ChangeAbilityCount("ABILITY_SIQI_0015_REDUCED_CHARGE_" .. i, 1)
            break
        end
    end
end
```

---
> **公共判断函数**（IsCivilization / IsLeader / HasProperty / HasTrait）及 **FormatValue / AddYieldStringToWorld / YIELD 快捷映射** 见 `code-style.md` 和 `Support.lua` 标准库，此处不重复。
