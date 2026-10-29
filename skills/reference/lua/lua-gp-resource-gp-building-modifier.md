# lua-gp-resource — 非战斗类 GP 函数 — 伟人/建筑/修改器

> 分册：由 [lua-gp-resource.md](lua-gp-resource.md) 按主题拆出；覆盖 伟人、ChangeGreatPeoplePoints — 修改指定类别伟人点数、Siqi_AddGreatPeople — 赠送指定伟人个体到首都、击杀单位 → +5 大将军点数（魈基础）、建筑、GrantBuilding — 授予建筑（指定城市或首都）、RemoveBuilding — 移除建筑、七天神像形态切换（钟离）、修改器、AttachModifierByID 动态附加（Doloris 能力购买）、AttachModifierByID 计时脱手（魈 R1：4 层槽位，15 回合过期剥离）、AttachModifierByID 计数触发（凝光 L2：每 7 条商路 → +1 商人 +1 容量）、分期扣款系统（摩拉克斯馈赠）。触发：改伟人、建筑、修改器时。

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

