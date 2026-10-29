# lua-gp-combat — 战斗类 GP 函数 — 伤害

> 分册：由 [lua-gp-combat.md](lua-gp-combat.md) 按主题拆出；覆盖 伤害、Siqi_AttachUnitDamage — 对单位造成指定伤害，超出血量则击杀、XianZhouOnCombat — 近战AOE波及相邻敌方单位+区域，战斗力差公式、SiqiOnCombat — 60%扩散伤害到相邻敌方单位+等量驻军伤害到相邻城市、SiqiBubbledamage — 累计受击伤害换经验（每50点+15XP）、SiqiBubbledefenddamage — 防御力×50%反伤、苏苏洛治疗转科文 — 单位恢复血量时获得恢复量20%的科技+文化、诸葛亮八卦阵免伤 — 己方领土首次受伤免伤（回滚伤害），每回合重置、帕斯卡拉分摊伤害 — 伤害分摊到后续5回合、偷取战斗力 — 攻方战力低于防方时"偷取"差额为永久加成。触发：计算/施加战斗伤害时。

## 伤害

### Siqi_AttachUnitDamage — 对单位造成指定伤害，超出血量则击杀

```lua
function Siqi_AttachUnitDamage(pUnit, damage)
    if pUnit == nil then return; end
    local MaxDamage = pUnit:GetProperty('MaxHitPoints') or 100
    local unitdamage = pUnit:GetDamage()
    if unitdamage + damage >= MaxDamage then
        UnitManager.Kill(pUnit, true)
    else
        pUnit:ChangeDamage(damage)
    end
end
```

### XianZhouOnCombat — 近战AOE波及相邻敌方单位+区域，战斗力差公式

```lua
function XianZhouAdjUnit(attInfo, defInfo, iX, iY, iRange, iCombat)
    local e = 2.71828
    local plots = Map.GetNeighborPlots(iX, iY, iRange)
    local attUnit = UnitManager.GetUnit(attInfo.player, attInfo.id)
    local defUnit = UnitManager.GetUnit(defInfo.player, defInfo.id)
    if not attUnit then return end
    for i, adjPlot in ipairs(plots) do
        if adjPlot then
            -- AOE波及相邻敌方单位
            local pUnitList = Units.GetUnitsInPlot(adjPlot)
            if pUnitList ~= nil then
                for _, NeighborUnit in ipairs(pUnitList) do
                    if NeighborUnit and IsCombatUnits(NeighborUnit)
                       and Players[NeighborUnit:GetOwner()]:GetDiplomacy():IsAtWarWith(attInfo.player) then
                        if not adjPlot:IsWater() and NeighborUnit ~= defUnit and IsZOCUnits(attUnit) then
                            local remaining = NeighborUnit:GetMaxDamage() - NeighborUnit:GetDamage()
                            local nDamage = math.ceil((12 + Game.GetRandNum(6)) * e^((iCombat - NeighborUnit:GetCombat()) * 0.04))
                            if remaining <= nDamage then UnitManager.Kill(NeighborUnit, false)
                            else NeighborUnit:ChangeDamage(nDamage) end
                        end
                    end
                end
            end
            -- AOE波及敌方区域（城墙优先，再驻军）
            local pDistrict = CityManager.GetDistrictAt(adjPlot:GetX(), adjPlot:GetY())
            if pDistrict and Players[adjPlot:GetOwner()]:GetDiplomacy():IsAtWarWith(attInfo.player) then
                local distDef = pDistrict:GetDefenseStrength()
                if distDef and distDef > 0 then
                    local nDamage = math.min(50, math.ceil((12 + Game.GetRandNum(6)) * e^((iCombat - distDef) * 0.04)))
                    if pDistrict:GetDamage(DefenseTypes.DISTRICT_OUTER) < pDistrict:GetMaxDamage(DefenseTypes.DISTRICT_OUTER) then
                        pDistrict:ChangeDamage(DefenseTypes.DISTRICT_OUTER, nDamage)
                    else
                        pDistrict:ChangeDamage(DefenseTypes.DISTRICT_GARRISON, nDamage)
                    end
                end
            end
        end
    end
end

function XianZhouOnCombat(pCombatResult)
    if not pCombatResult[CombatResultParameters.ATTACKER_ADVANCES] then return end
    local attacker = pCombatResult[CombatResultParameters.ATTACKER]
    local defender = pCombatResult[CombatResultParameters.DEFENDER]
    local attInfo = attacker[CombatResultParameters.ID]
    local defInfo = defender[CombatResultParameters.ID]
    local attUnit = UnitManager.GetUnit(attInfo.player, attInfo.id)
    if attUnit and attUnit:GetProperty('PEN_XIANZHOU_ENABLE_AOE_COMBAT')
       and attUnit:GetProperty('PEN_XIANZHOU_ENABLE_AOE_COMBAT') > 0 then
        local location = attUnit:GetLocation()
        XianZhouAdjUnit(attInfo, defInfo, location.x, location.y, 1, attUnit:GetCombat())
    end
end
```

### SiqiOnCombat — 60%扩散伤害到相邻敌方单位+等量驻军伤害到相邻城市

```lua
function SiqiOnCombat(pCombatResult)
    local attacker = pCombatResult[CombatResultParameters.ATTACKER]
    local defender = pCombatResult[CombatResultParameters.DEFENDER]
    local attInfo = attacker[CombatResultParameters.ID]
    local defInfo = defender[CombatResultParameters.ID]
    local attUnit = UnitManager.GetUnit(attInfo.player, attInfo.id)
    local defUnit = UnitManager.GetUnit(defInfo.player, defInfo.id)

    -- 单位A1攻击时对敌人相邻单位造成60%扩散伤害
    if attUnit and attUnit:GetType() == INDEX_TARGET_UNIT then
        local attdamage = defender[CombatResultParameters.DAMAGE_TO] or 0
        local d = math.floor(attdamage * 0.6)
        local location = {x = attUnit:GetX(), y = attUnit:GetY()}
        if defInfo.type == 1 then
            location = {x = defUnit:GetX(), y = defUnit:GetY()}
        elseif defInfo.type == 3 then
            local pDistrict = CityManager.GetDistrict(defInfo.player, defInfo.id)
            location = {x = pDistrict:GetX(), y = pDistrict:GetY()}
        end
        local Unitlist = Siqi_FindUnitEnemy(attInfo.player, location.x, location.y)
        for i = 1, #Unitlist do
            Siqi_AttachUnitDamage(Unitlist[i], d)
        end
        -- 相邻敌方城市驻军伤害
        local pCity = Siqi_FindCityEnemy(attInfo.player, location.x, location.y)
        if pCity ~= nil then
            local pCityDistrict = pCity:GetDistricts():GetDistrict(GameInfo.Districts['DISTRICT_CITY_CENTER'].Index)
            pCityDistrict:ChangeDamage(DefenseTypes.DISTRICT_GARRISON, d)
        end
    end
end
```

### SiqiBubbledamage — 累计受击伤害换经验（每50点+15XP）

```lua
function SiqiBubbledamage(playerID, unitID, damage)
    local pPlayer = Players[playerID]
    local pPlayerConfig = PlayerConfigurations[playerID]
    if pPlayerConfig:GetLeaderTypeName() ~= LEADERSLIST[3] then return end
    if pPlayer:GetProperty('Siqi_Cute_PromotionMax' .. pPlayerConfig:GetLeaderTypeName()) then return end
    local alldamage = pPlayer:GetProperty('Siqi_Cute_Bubble_Damage') or 0
    alldamage = alldamage + damage
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    if pUnit == nil then return end
    if alldamage >= 50 then
        local amount = math.floor(alldamage / 50)
        for i = 1, amount do
            pUnit:GetExperience():ChangeExperience(15)
            alldamage = alldamage - 50
        end
    end
    pPlayer:SetProperty('Siqi_Cute_Bubble_Damage', alldamage)
end
```

### SiqiBubbledefenddamage — 防御力×50%反伤

```lua
function SiqiBubbledefendnum(playerID)
    local pPlayer = Players[playerID]
    local num = 10
    if pPlayer:GetProperty('Siqi_Cute_PROMOTION_SPECIAL_BUBBLE_L1') then num = num + 16 end
    if pPlayer:GetProperty('Siqi_Cute_PROMOTION_SPECIAL_BUBBLE_L3') then num = num + 12 end
    return num
end

function SiqiBubbledefenddamage(playerID, pUnit, damage)
    local defendnum = math.floor(SiqiBubbledefendnum(playerID) * 0.5)
    if damage + defendnum >= 100 then
        UnitManager.Kill(pUnit, false)
    elseif damage + defendnum < 100 then
        pUnit:ChangeDamage(defendnum)
    end
    SiqiBubbledamage(playerID, pUnit:GetID(), defendnum)
end
```

### 苏苏洛治疗转科文 — 单位恢复血量时获得恢复量20%的科技+文化

```lua
function SiqiOnUnitDamageChanged(PlayerID, UnitID, newDamage, prevDamage)
    if not Siqi_IsPlayerLeader(PlayerID, TYPE_SUSSURRO) then return end
    if newDamage >= prevDamage then return end  -- 只处理回血
    local pPlayer = Players[PlayerID]
    local healAmount = prevDamage - newDamage
    local yield = healAmount * 0.2
    pPlayer:GetTechs():ChangeCurrentResearchProgress(yield)
    pPlayer:GetCulture():ChangeCurrentCulturalProgress(yield)

    -- 同时记录到三环内己方城市的累计治疗量（供Bin Property加成用）
    local pUnit = UnitManager.GetUnit(PlayerID, UnitID)
    if pUnit == nil then return end
    local Citylist = Siqi_GetNearCityIn3(pUnit:GetX(), pUnit:GetY())
    for i, pCity in ipairs(Citylist) do
        if pCity:GetOwner() == PlayerID then
            local val = (pCity:GetProperty("SIQI_SUSSURRO_HEALING_AMOUNT") or 0) + healAmount
            pCity:SetProperty("SIQI_SUSSURRO_HEALING_AMOUNT", val)
            if math.floor(val / 100) > 0 then
                local t = Siqi_10to2(math.floor(val / 100), 11)
                local plot = Map.GetPlot(pCity:GetX(), pCity:GetY())
                for j = 1, 11 do plot:SetProperty("SIQI_SUSSURRO_CITY_YIELD_PROPERTY_" .. NumberTable[j], t[j]) end
            end
        end
    end
end
```

### 诸葛亮八卦阵免伤 — 己方领土首次受伤免伤（回滚伤害），每回合重置

```lua
function SiqiOnUnitDamageChanged(PlayerID, UnitID, newDamage, prevDamage)
    if not Siqi_IsPlayerLeader(PlayerID, TYPE_ZHUGELIANG) then return end
    if newDamage <= prevDamage or newDamage >= 100 then return end  -- 回血或死亡不触发
    local pUnit = UnitManager.GetUnit(PlayerID, UnitID)
    if pUnit == nil then return end
    local pPlot = Map.GetPlot(pUnit:GetX(), pUnit:GetY())
    if not pPlot or pPlot:GetOwner() ~= PlayerID then return end  -- 必须在己方领土
    local ability = 'ABILITY_SIQI_ZHUGE_LIANNU_BAGUA'
    local pUnitAbility = pUnit:GetAbility()
    if pUnitAbility:GetAbilityCount(ability) <= 0 then return end  -- 必须有八卦阵Ability
    if pUnit:GetProperty('Siqi_Zhugeliang_Bagua') then return end  -- 本回合已触发
    pUnit:SetDamage(prevDamage)                                     -- 回滚到受伤前
    pUnit:SetProperty('Siqi_Zhugeliang_Bagua', true)                -- 标记已使用
end

-- 每回合重置标记
function SiqiOnPlayerTurnActivated(playerID, bIsFirstTime)
    if not Siqi_IsPlayerLeader(playerID, TYPE_ZHUGELIANG) then return end
    if not bIsFirstTime then return end
    local pPlayer = Players[playerID]
    for i, unit in pPlayer:GetUnits():Members() do
        unit:SetProperty('Siqi_Zhugeliang_Bagua', false)
    end
end
```

### 帕斯卡拉分摊伤害 — 伤害分摊到后续5回合

```lua
-- 受到伤害时：回滚本次伤害，将差值分摊到5回合
function SiqiOnUnitDamageChanged(PlayerID, UnitID, newDamage, prevDamage)
    if not Siqi_IsPlayerLeader(PlayerID, TYPE_PASCALA) then return end
    if newDamage <= prevDamage or newDamage >= 100 then return end
    local pUnit = UnitManager.GetUnit(PlayerID, UnitID)
    if pUnit == nil then return end
    pUnit:SetDamage(prevDamage)  -- 回滚伤害
    local damagePerTurn = pUnit:GetProperty("Siqi_PASCALA_UNIT_DAMAGE_Turn") or {0, 0, 0, 0, 0}
    local totalDamage = newDamage - prevDamage
    for i = 1, 4 do
        damagePerTurn[i] = damagePerTurn[i] + math.floor(totalDamage / (6 - i))
        totalDamage = totalDamage - math.floor(totalDamage / (6 - i))
    end
    damagePerTurn[5] = totalDamage
    pUnit:SetProperty("Siqi_PASCALA_UNIT_DAMAGE_Turn", damagePerTurn)
end

-- 回合结束时结算分摊伤害（需先Remove UnitDamageChanged事件避免递归）
function Siqi_PascalaUnitDamage(playerID)
    local pPlayer = Players[playerID]
    for i, unit in pPlayer:GetUnits():Members() do
        if unit:GetProperty("Siqi_PASCALA_UNIT_DAMAGE_Turn") then
            local damagePerTurn = unit:GetProperty("Siqi_PASCALA_UNIT_DAMAGE_Turn")
            local value = damagePerTurn[1] or 0
            if value > 0 then
                Siqi_AttachUnitDamage(unit, value)
            end
            for j = 1, 4 do
                damagePerTurn[j] = damagePerTurn[j + 1]
            end
            damagePerTurn[5] = 0
            unit:SetProperty("Siqi_PASCALA_UNIT_DAMAGE_Turn", damagePerTurn)
        end
    end
end

-- 回合结束入口：移除监听→结算→标记
function SiqiOnTurnEnd()
    local playerID = Siqi_Findplayerid(TYPE_PASCALA)
    if playerID == nil then return end
    Events.UnitDamageChanged.Remove(SiqiOnUnitDamageChanged)
    Game:SetProperty("Siqi_PASCALA_UNIT_DAMAGE", true)
    Siqi_PascalaUnitDamage(playerID)
end

-- 回合开始：恢复监听
function SiqiOnTurnBegin()
    if not Game:GetProperty("Siqi_PASCALA_UNIT_DAMAGE") then return end
    Events.UnitDamageChanged.Add(SiqiOnUnitDamageChanged)
    Game:SetProperty("Siqi_PASCALA_UNIT_DAMAGE", false)
end
```

### 偷取战斗力 — 攻方战力低于防方时"偷取"差额为永久加成

```lua
function SiqiOnCombat(pCombatResult)
    local attacker = pCombatResult[CombatResultParameters.ATTACKER]
    local defender = pCombatResult[CombatResultParameters.DEFENDER]
    local attInfo = attacker[CombatResultParameters.ID]
    local defInfo = defender[CombatResultParameters.ID]
    if attInfo.type == 3 or defInfo.type == 3 then return end  -- 排除区域
    local attUnit = UnitManager.GetUnit(attInfo.player, attInfo.id)
    local defUnit = UnitManager.GetUnit(defInfo.player, defInfo.id)
    if attUnit == nil or defUnit == nil then return end

    if not Siqi_IsPlayerLeader(attInfo.player, LEADER_TYPE) then return end

    -- 攻方已有的偷取战斗力
    local attstealcombat = attUnit:GetProperty('SIQI_ROPE_PLAYER_GRANT_COMBAT_PROPERTY') or 0
    -- 基础战斗力 + 加成
    local attcombat = attacker[CombatResultParameters.COMBAT_STRENGTH] or 0
    local attcombatmodifier = attacker[CombatResultParameters.STRENGTH_MODIFIER] or 0
    local defcombat = defender[CombatResultParameters.COMBAT_STRENGTH] or 0
    local defcombatmodifier = defender[CombatResultParameters.STRENGTH_MODIFIER] or 0

    if defcombat + defcombatmodifier > attcombat + attcombatmodifier then
        local combatdifference = defcombat + defcombatmodifier - attcombat - attcombatmodifier
        attUnit:SetProperty('SIQI_ROPE_PLAYER_GRANT_COMBAT_PROPERTY', attstealcombat + combatdifference)
        -- 给防御方挂减战斗力标记（防方存活时）
        if defUnit ~= nil then
            local defUnitAbility = defUnit:GetAbility()
            if defUnitAbility:GetAbilityCount('ABILITY_UNIT_SIQI_ROPE_LESS_COMBAT_PROPERTY') == 0 then
                defUnitAbility:ChangeAbilityCount('ABILITY_UNIT_SIQI_ROPE_LESS_COMBAT_PROPERTY', 1)
            end
            defUnit:SetProperty('SIQI_ROPE_PLAYER_LESS_COMBAT_PROPERTY', -combatdifference)
        end
    end
end
```

---

