# lua-gp-resource — 非战斗类 GP 函数

基于 Siqi_Leaders_0032（最新标准）和 19.47 Mod 提炼。GP 环境专用，所有函数均需在 Scripts/Import 中运行。

---

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

## 伟人

### ChangeGreatPeoplePoints — 修改指定类别伟人点数

```lua
function ChangeGreatPeoplePoints(playerID, amount, class)
    local player = Players[playerID]
    local i = GameInfo.GreatPersonClasses[class].Index
    player:GetGreatPeoplePoints():ChangePointsTotal(i, amount)
end
```

### Siqi_AddGreatPeople — 赠送指定伟人个体到首都

通过 GrantPerson API 直接赠送伟人个体，使用 Hash 值定位。

```lua
function AddGreatPeople(iPlayer, greatPersonIndividualName)
    local individual = GameInfo.GreatPersonIndividuals[greatPersonIndividualName].Hash
    local class = GameInfo.GreatPersonClasses["GREAT_PERSON_CLASS_PEACH_GENERAL"].Hash
    local era = GameInfo.Eras["ERA_ANCIENT"].Hash
    local cost = 0
    Game.GetGreatPeople():GrantPerson(individual, class, era, cost, iPlayer, false)
end
```

### 击杀单位 → +5 大将军点数（魈基础）

单位拥有的 Ability（ABILITY_SIQI_G0032_4_AURA）提供光环，击杀时触发。

```lua
function OnXiaoUnitKilled(killedPlayerID, killedUnitID, playerID, unitID)
    local pPlayer = Players[playerID]
    if not pPlayer then return end

    local pUnit = UnitManager.GetUnit(playerID, unitID)
    if not pUnit then return end
    local pUnitAbility = pUnit:GetAbility()
    if not pUnitAbility then return end
    if pUnitAbility:GetAbilityCount('ABILITY_SIQI_G0032_4_AURA') <= 0 then return end

    pPlayer:GetGreatPeoplePoints():ChangePointsTotal('GREAT_PERSON_CLASS_GENERAL', 5)
    local ggInfo = GameInfo.GreatPersonClasses['GREAT_PERSON_CLASS_GENERAL']
    if ggInfo then
        Game.AddWorldViewText(0, '+5' .. ggInfo.IconString .. Locale.Lookup(ggInfo.Name),
            pUnit:GetX(), pUnit:GetY())
    end
end

```

---

## 建筑

### GrantBuilding — 授予建筑（指定城市或首都）

```lua
function GrantBuilding(playerID, cityID, building)
    local pCity = CityManager.GetCity(playerID, cityID)
    if pCity and not pCity:GetBuildings():HasBuilding(GameInfo.Buildings[building].Index) then
        pCity:GetBuildQueue():CreateBuilding(GameInfo.Buildings[building].Index)
    end
end
```

### RemoveBuilding — 移除建筑

```lua
function RemoveBuilding(playerID, cityID, building)
    local pCity = CityManager.GetCity(playerID, cityID)
    if pCity and pCity:GetBuildings():HasBuilding(GameInfo.Buildings[building].Index) then
        pCity:GetBuildings():RemoveBuilding(GameInfo.Buildings[building].Index)
    end
end
```

### 七天神像形态切换（钟离）

UI 发起请求 → GP 端判定首都已有哪些形态 → 创建目标形态建筑（首都最多同时拥有一个形态建筑）。

```lua
function OnStatueFormSwitch(playerID, params)
    local targetBuilding = params.TargetBuilding
    if not targetBuilding then return end

    local pPlayer = Players[playerID]
    if not pPlayer then return end
    local pCapital = pPlayer:GetCities():GetCapitalCity()
    if not pCapital then return end

    local buildingHash = GameInfo.Buildings[targetBuilding].Hash
    local BuildingIndex = GameInfo.Buildings[targetBuilding].Index
    if not buildingHash then return end
    if pCapital:GetBuildings():HasBuilding(buildingHash) then return end

    pCapital:GetBuildQueue():CreateBuilding(BuildingIndex)
end

```

---

## 修改器

### AttachModifierByID 动态附加（Doloris 能力购买）

通过 GameEvent 接收 UI 请求，遍历 Modifier 列表逐个 AttachModifierByID，扣信仰。

```lua
function AbilityPurchase_Doloris(playerID, params)
    local pPlayer = Players[playerID]
    -- 授予能力
    local Modifiers = GetAbilitiesModifiers(params.CivilizationType, params.InheritFrom) or {}
    for _, ModifierID in ipairs(Modifiers) do
        pPlayer:AttachModifierByID(ModifierID)
    end
    -- 记录购买次数和能力属性
    local count = pPlayer:GetProperty("Siqi_Doloris_Mujica_Bought_Abilities_Count") or 0
    count = count + 1
    pPlayer:SetProperty("Siqi_Doloris_Mujica_Bought_Abilities_Count", count)
    pPlayer:SetProperty('Doloris_Key_' .. params.TraitType, 1)
    -- 扣除信仰
    ChangeFaith(playerID, -(params.Cost or 0))
end
```

### AttachModifierByID 计时脱手（魈 R1：4 层槽位，15 回合过期剥离）

单位死亡 → 填充 4 个槽位中最早过期的 → Attach +5% 生产力 Modifier。每回合检查过期槽位 → Attach 反向 Modifier 剥离。槽位通过 Player Property（序列化表）管理，断电/读档不丢失。

```lua
function OnXiaoR1UnitKilled(killedPlayerID, killedUnitID, playerID, unitID)
    local pPlayer = Players[killedPlayerID]
    if not pPlayer then return end
    if not HasProperty(pPlayer, 'SIQI32_G0032_4_R1_ACTIVE') then return end

    local slots = pPlayer:GetProperty('SIQI32_G0032_4_R1_SLOTS') or {}
    local current = Game.GetCurrentGameTurn()
    local expiryTurn = current + 15

    -- 找空槽或最早过期槽
    local filled = false
    for i = 1, 4 do
        if not slots[i] or slots[i] <= current then
            slots[i] = expiryTurn
            filled = true
            break
        end
    end

    if not filled then
        -- 4 槽全满：弹出最早过期者
        local minIdx, minVal = 1, slots[1]
        for i = 2, 4 do
            if slots[i] < minVal then minIdx, minVal = i, slots[i] end
        end
        pPlayer:AttachModifierByID('MODIFIER_SIQI_G0032_4_R1_PROD_MINUS')
        slots[minIdx] = expiryTurn
    end

    pPlayer:AttachModifierByID('MODIFIER_SIQI_G0032_4_R1_PROD_PLUS')
    pPlayer:SetProperty('SIQI32_G0032_4_R1_SLOTS', slots)
end

function OnXiaoR1TurnBegin(playerID)
    local pPlayer = Players[playerID]
    if not pPlayer then return end
    local slots = pPlayer:GetProperty('SIQI32_G0032_4_R1_SLOTS')
    if not slots then return end
    local current = Game.GetCurrentGameTurn()
    local changed = false
    for i = 1, 4 do
        if slots[i] and slots[i] <= current then
            pPlayer:AttachModifierByID('MODIFIER_SIQI_G0032_4_R1_PROD_MINUS')
            slots[i] = nil
            changed = true
        end
    end
    if changed then
        pPlayer:SetProperty('SIQI32_G0032_4_R1_SLOTS', slots)
    end
end

```

### AttachModifierByID 计数触发（凝光 L2：每 7 条商路 → +1 商人 +1 容量）

监听 TradeRouteAddedToMap，累加计数。每满 7 条：AttachModifierByID 到城市（赠送商人）和玩家（+1 商路容量），计数减 7 继续。

```lua
function OnNingTradeRouteAdded(playerID, iX, iY)
    local pPlayer = Players[playerID]
    if not pPlayer then return end
    if not HasProperty(pPlayer, 'SIQI32_G0032_4_L2_ACTIVE') then return end

    local count = (pPlayer:GetProperty('SIQI32_G0032_4_L2_TRADE_COUNT') or 0) + 1
    if count >= 7 then
        count = count - 7
        local pCity = CityManager.GetCityAt(iX, iY)
        if pCity then
            pCity:AttachModifierByID('MODIFIER_SIQI_G0032_4_L2_TRADER')
        end
        pPlayer:AttachModifierByID('MODIFIER_SIQI_G0032_4_L2_CAPACITY')
    end
    pPlayer:SetProperty('SIQI32_G0032_4_L2_TRADE_COUNT', count)
end

```

### 分期扣款系统（摩拉克斯馈赠）

项目完成→记录债务表（"总额,每回合扣,结束回合"|分隔），每回合查表扣款+清理过期。

```lua
-- 配置：项目 Index → { 倍率, 持续回合 }
local MORAX_GIFT_CONFIG = {}
do
    local proj = GameInfo.Projects['PROJECT_SIQI_P0032_1']
    if proj then MORAX_GIFT_CONFIG[proj.Index] = { ratio = 1.5, duration = 30 } end
    proj = GameInfo.Projects['PROJECT_SIQI_P0032_2']
    if proj then MORAX_GIFT_CONFIG[proj.Index] = { ratio = 2.5, duration = 20 } end
    proj = GameInfo.Projects['PROJECT_SIQI_P0032_3']
    if proj then MORAX_GIFT_CONFIG[proj.Index] = { ratio = 3.5, duration = 10 } end
end

function OnMoraxGiftCompleted(playerID, cityID, projectID, buildingIndex, iX, iY, bCancelled)
    if bCancelled then return end
    local config = MORAX_GIFT_CONFIG[projectID]
    if not config then return end

    local pPlayer = Players[playerID]
    if not pPlayer then return end
    local goldBalance = pPlayer:GetTreasury():GetGoldBalance()
    if goldBalance <= 0 then return end

    local lumpSum = math.floor(goldBalance * config.ratio)
    local perTurn = math.floor(lumpSum / config.duration)
    if perTurn <= 0 then perTurn = 1 end
    local endTurn = Game.GetCurrentGameTurn() + config.duration

    ChangeGold(playerID, lumpSum)

    -- 写入债务追踪表：格式 "总额,每回合扣,结束回合"
    local raw = pPlayer:GetProperty('SIQI32_MG_DEBT_TRACKER') or ''
    local entries = {}
    if raw ~= '' then
        for entry in string.gmatch(raw, '[^|]+') do
            table.insert(entries, entry)
        end
    end
    table.insert(entries, string.format('%d,%d,%d', lumpSum, perTurn, endTurn))
    pPlayer:SetProperty('SIQI32_MG_DEBT_TRACKER', table.concat(entries, '|'))
end

function ProcessMoraxGiftDebt(playerID)
    local pPlayer = Players[playerID]
    if not pPlayer then return end
    local raw = pPlayer:GetProperty('SIQI32_MG_DEBT_TRACKER') or ''
    if raw == '' then return end

    local currentTurn = Game.GetCurrentGameTurn()
    local remaining = {}

    for entry in string.gmatch(raw, '[^|]+') do
        local totalStr, perTurnStr, endTurnStr = string.match(entry, '(%d+),(%-?%d+),(%d+)')
        local totalRemaining = tonumber(totalStr)
        local perTurn = tonumber(perTurnStr)
        local endTurn = tonumber(endTurnStr)

        if endTurn and endTurn >= currentTurn and totalRemaining and totalRemaining > 0 and perTurn and perTurn > 0 then
            local deduct = math.min(perTurn, totalRemaining)
            ChangeGold(playerID, -deduct)
            totalRemaining = totalRemaining - deduct
            if totalRemaining > 0 then
                table.insert(remaining, string.format('%d,%d,%d', totalRemaining, perTurn, endTurn))
            end
        end
    end

    if #remaining > 0 then
        pPlayer:SetProperty('SIQI32_MG_DEBT_TRACKER', table.concat(remaining, '|'))
    else
        pPlayer:SetProperty('SIQI32_MG_DEBT_TRACKER', '')
    end
end

```

---

## 科技市政

### 获取已完成尤里卡但未研究的科技列表

```lua
function GetHasBoostTechs(playerID)
    local pPlayer = Players[playerID]
    local playerTechs = pPlayer:GetTechs()
    local Techs = {}
    for tech in GameInfo.Technologies() do
        if playerTechs:HasBoostBeenTriggered(tech.Index) and (not playerTechs:HasTech(tech.Index)) then
            table.insert(Techs, tech.Index)
        end
    end
    return Techs
end
```

### 判断某时代科技是否全部已触发尤里卡

传入 playerID 和某个科技的 Index，返回该科技所属 Era 是否全部未完成科技都已触发尤里卡。

```lua
function HasTechBoostForEra(playerID, iTech)
    local pPlayer = Players[playerID]
    local playerTechs = pPlayer:GetTechs()
    local TechInfo = GameInfo.Technologies[iTech]
    if TechInfo == nil then return false end
    local EraType = TechInfo.EraType
    local AllHasBoost = true
    for tech in GameInfo.Technologies() do
        if tech.EraType == EraType
            and (not playerTechs:HasBoostBeenTriggered(tech.Index))
            and (not playerTechs:HasTech(tech.Index)) then
            AllHasBoost = false
            break
        end
    end
    return AllHasBoost
end
```

### 赠送某时代全部未完成科技

```lua
function RewardTechBoostForEra(playerID, iTech)
    local pPlayer = Players[playerID]
    local playerTechs = pPlayer:GetTechs()
    local TechInfo = GameInfo.Technologies[iTech]
    local EraType = TechInfo.EraType
    for tech in GameInfo.Technologies() do
        if tech.EraType == EraType and (not playerTechs:HasTech(tech.Index)) then
            playerTechs:SetResearchProgress(tech.Index, playerTechs:GetResearchCost(tech.Index))
        end
    end
end
```

### 判断某时代市政是否全部已触发鼓舞

```lua
function HasCivicBoostForEra(playerID, iCivic)
    local pPlayer = Players[playerID]
    local playerCivics = pPlayer:GetCulture()
    local CivicInfo = GameInfo.Civics[iCivic]
    if CivicInfo == nil then return false end
    local EraType = CivicInfo.EraType
    local AllHasBoost = true
    for civic in GameInfo.Civics() do
        if civic.EraType == EraType
            and (not playerCivics:HasBoostBeenTriggered(civic.Index))
            and (not playerCivics:HasCivic(civic.Index)) then
            AllHasBoost = false
            break
        end
    end
    return AllHasBoost
end
```

### 赠送某时代全部未完成市政

```lua
function RewardCivicBoostForEra(playerID, iCivic)
    local pPlayer = Players[playerID]
    local playerCivics = pPlayer:GetCulture()
    local CivicInfo = GameInfo.Civics[iCivic]
    local EraType = CivicInfo.EraType
    for civic in GameInfo.Civics() do
        if civic.EraType == EraType and (not playerCivics:HasCivic(civic.Index)) then
            playerCivics:SetCulturalProgress(civic.Index, playerCivics:GetCultureCost(civic.Index))
        end
    end
end
```

### 解锁政体（完成前置市政，稳定写法）

`UnlockGovernment`/`IsGovernmentUnlocked` 官方源码零使用、0054 实测**开局崩溃** → 弃用（memory feedback-0054-government-unlock）。政体可用判定 = 其 `PrereqCivic` 已完成 → 稳定实现 = 遍历政体收集前置市政并"立即完成市政"：

```lua
-- 每回合幂等兜底（读档自愈）
-- 跳过 PrereqCivic=NULL（初始政体酋邦无前置）
-- T1 三政体共用 CIVIC_POLITICAL_PHILOSOPHY → table 去重只完成一次
function UnlockGovernmentsByCivic(playerID)
    local pCulture = Players[playerID]:GetCulture();
    if pCulture == nil then return end
    local civicToComplete = {};
    for row in GameInfo.Governments() do
        local prereq = row.PrereqCivic;
        if prereq ~= nil then
            local civicInfo = GameInfo.Civics[prereq];
            if civicInfo ~= nil and not pCulture:HasCivic(civicInfo.Index) then
                civicToComplete[civicInfo.Index] = civicInfo.Index;
            end
        end
    end
    for _, civicIndex in pairs(civicToComplete) do
        pCulture:SetCulturalProgress(civicIndex, pCulture:GetCultureCost(civicIndex));
    end
end
```

- `SetCulturalProgress(idx, GetCultureCost(idx))` = "立即赠送市政"（0013/0026/0029/0030/18.0 出货 Mod 实证）
- 政策卡直接全量 `UnlockPolicy(Index)`（`for row in GameInfo.Policies()` + `IsPolicyUnlocked` 幂等）；`ExplicitUnlock=1` 自创卡与基础卡均可用此法解锁
- 完成市政会连带解锁该市政的奖励政策（"任意政体+任意政策"文案即此口径）

### HasTech — 检查玩家是否拥有某科技

```lua
function HasTech(playerID, techType)
    if not techType or techType == "" then return true end
    local pPlayer = Players[playerID]
    if not pPlayer then return false end
    local techInfo = GameInfo.Technologies[techType]
    if not techInfo then return false end
    local pTeam = Teams[pPlayer:GetTeam()]
    if not pTeam then return false end
    return pTeam:HasTech(techInfo.Index)
end
```

### HasCivic — 检查玩家是否拥有某市政

```lua
function HasCivic(playerID, civicType)
    if not civicType or civicType == "" then return true end
    local pPlayer = Players[playerID]
    if not pPlayer then return false end
    local civicInfo = GameInfo.Civics[civicType]
    if not civicInfo then return false end
    local pCulture = pPlayer:GetCulture()
    if not pCulture then return false end
    return pCulture:HasCivic(civicInfo.Index)
end
```

---

## 城市状态 / Property

### 城市宜居度计算（GP 精确版）

基于 GlobalParameters 精确计算溢出宜居度：总宜居度 + 免费宜居度 - 人口消耗。

```lua
function GetCitySurplusAmenities(pCity)
    local CityGrowth = pCity:GetGrowth()
    local TotalAmenities = CityGrowth:GetAmenities()
    local Population = pCity:GetPopulation()
    local CITY_POP_PER_AMENITY = GameInfo.GlobalParameters['CITY_POP_PER_AMENITY'].Value
    local AmenitiesNeeded_FromPopulation = math.ceil(Population / CITY_POP_PER_AMENITY)
    local CITY_AMENITIES_FOR_FREE = GameInfo.GlobalParameters['CITY_AMENITIES_FOR_FREE'].Value
    local Count = TotalAmenities + CITY_AMENITIES_FOR_FREE - AmenitiesNeeded_FromPopulation
    return Count
end
```

### 宜居度转二进制属性（桃金娘 / 苏苏洛共用）

城市溢出宜居度→地块二进制 Property。桃金娘：每 2 宜居度 +10% 产出。苏苏洛：补全到 6 再修正。

```lua
-- 二进制表常量
local NumberTable = {1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048}

-- 数字转定长二进制表
function NumToBinary(num, length)
    local result = {}
    for i = 1, length do
        result[i] = 0
        if num >= NumberTable[i] then
            result[i] = 1
            num = num - NumberTable[i]
        end
    end
    return result
end

function SetAmenitiesPropertyInCity(playerID, cityID)
    local pCity = CityManager.GetCity(playerID, cityID)
    if pCity == nil then return end
    local Amenities = GetCitySurplusAmenities(pCity)
    local pPlot = Map.GetPlot(pCity:GetX(), pCity:GetY())

    -- 桃金娘：每 2 宜居度 +10% 产出，上限 8 位
    if IsLeader(playerID, 'LEADER_MYRTLE') then
        if Amenities < 0 then Amenities = 0 end
        local yieldbonus = math.floor(Amenities / 2)
        local yieldbonus2 = NumToBinary(yieldbonus, 8)
        for i = 1, 8 do
            pPlot:SetProperty("SIQI_MYRTLE_CITY_PROPERTY_" .. NumberTable[i], yieldbonus2[i])
        end
    end

    -- 苏苏洛：补全宜居度到 6，然后修正（多退少补），上限 5 位
    if IsLeader(playerID, 'LEADER_SUSSURRO') then
        local Happyiness = 0
        for i = 1, 5 do
            local num = NumberTable[i]
            Happyiness = Happyiness + (pPlot:GetProperty("SIQI_SUSSURRO_HAPPYINESS_" .. num) or 0) * num
        end
        if Amenities < 6 then
            Happyiness = Happyiness + (6 - Amenities)
        elseif Amenities > 6 and Happyiness > 0 then
            Happyiness = Happyiness - (Amenities - 6)
        end
        if Happyiness < 0 then Happyiness = 0 end
        local HappyinessTable = NumToBinary(Happyiness, 5)
        for i = 1, 5 do
            pPlot:SetProperty("SIQI_SUSSURRO_HAPPYINESS_" .. NumberTable[i], HappyinessTable[i])
        end
    end
end
```

### 星辉系统：消耗星辉 → 触发鼓舞/尤里卡

每消耗 1 星辉累加计数器，满 5 触发一次随机鼓舞/尤里卡（AttachModifierByID），计数器清零。星辉(XingHui)→鼓舞，星术(XingShu)→尤里卡，两者对称。

```lua
function ChangeAmount_XingHui(playerID, amount)
    local pPlayer = Players[playerID]
    local key = "Siqi_XingHui"
    local cur = pPlayer:GetProperty(key) or 0
    pPlayer:SetProperty(key, cur + amount)
    if amount < 0 then
        local now = (pPlayer:GetProperty(key .. "_now") or 0) + math.abs(amount)
        if now >= 5 then
            pPlayer:AttachModifierByID("MODIFIER_SIQI_ASTESIA_GRANT_RANDOM_CIVIC_BOOST_GOODY_HUT")
            pPlayer:SetProperty('PROPERTY_SIQI_ASTESIA_GRANT_RANDOM_CIVIC_BOOST_GOODY_HUT_USED', true)
            now = 0
        end
        pPlayer:SetProperty(key .. "_now", now)
    end
    BroadcastRefresh()
end

-- ChangeAmount_XingShu 同理：key="Siqi_XingShu"，满5触发尤里卡 Modifier
```

### 摩拉产出系统核心：UI 计算 → GP 写 Property

UI 端读取各城市 From/Req/To 规则表 → 计算每回合摩拉 → 通过 EXECUTE_SCRIPT 异步发给 GP → GP 端写 Player Property(MORA) + 广播刷新。

```lua
-- GP 端接收 UI 计算结果
function GP_OnApplyTurnMora(playerID, params)
    if not params then return end
    local amount = params.Amount or 0
    if amount <= 0 then return end
    local pPlayer = Players[playerID]
    if not pPlayer then return end
    local current = pPlayer:GetProperty('MORA') or 0
    pPlayer:SetProperty('MORA', current + amount)
    pPlayer:SetProperty('MORA_PER_TURN', amount)
    BroadcastRefresh()
end

-- 统一余额变更入口（所有摩拉增加/消耗必须走此函数）
function Mora_ChangeBalance(playerID, amount, reason)
    local pPlayer = Players[playerID]
    if not pPlayer then return end
    if amount == 0 then return end
    local current = pPlayer:GetProperty("MORA") or 0
    local newBalance = current + amount
    pPlayer:SetProperty("MORA", newBalance)
    BroadcastRefresh()
end

```

### BroadcastRefresh — 广播刷新（GP → UI 通知）

toggle Game Property 触发跨上下文 Events.GamePropertyChanged。GP 修改数据后调用，UI 监听后自行读 Property 刷新。

```lua
function BroadcastRefresh()
    if Game:GetProperty("SIQI32_CORE_REFRESH") then
        Game:SetProperty("SIQI32_CORE_REFRESH", false)
    end
    if not Game:GetProperty("SIQI32_CORE_REFRESH") then
        Game:SetProperty("SIQI32_CORE_REFRESH", true)
    end
end
```
UI 端监听 `Events.GamePropertyChanged`，自行读 Property 刷新面板。见 `code-style.md` 第七章。

---

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
