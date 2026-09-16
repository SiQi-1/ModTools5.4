# lua-gp-combat — 战斗类 GP 函数

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

## 击杀效果

### 击败蛮族80%概率转建造者

```lua
function OnXiaoCombat(pCombatResult)
    local attacker = pCombatResult[CombatResultParameters.ATTACKER]
    local attInfo = attacker[CombatResultParameters.ID]
    if not Siqi32.IsLeader(attInfo.player, 'LEADER_SIQI_L0032_5') then return end

    local defender = pCombatResult[CombatResultParameters.DEFENDER]
    local defInfo = defender[CombatResultParameters.ID]
    local pDefender = Players[defInfo.player]
    if not pDefender or not pDefender:IsBarbarian() then return end

    local defUnit = UnitManager.GetUnit(defInfo.player, defInfo.id)
    if not defUnit then return end
    if not defUnit:IsDead() and not defUnit:IsDelayedDeath() then return end

    if Game.GetRandNum(100) + 1 > 80 then return end  -- 80%概率

    local defLoc = defender[CombatResultParameters.LOCATION]
    local newUnit = UnitManager.InitUnit(attInfo.player, 'UNIT_BUILDER', defLoc.x, defLoc.y)
end
```

### 击杀敌对单位→+5大将军点数

```lua
function OnUnitKilled(killedPlayerID, killedUnitID, playerID, unitID)
    local pPlayer = Players[playerID]
    if not pPlayer then return end
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    if not pUnit then return end
    local pUnitAbility = pUnit:GetAbility()
    if not pUnitAbility then return end
    -- 需要拥有特定光环Ability才触发
    if pUnitAbility:GetAbilityCount('ABILITY_SIQI_G0032_4_AURA') <= 0 then return end
    pPlayer:GetGreatPeoplePoints():ChangePointsTotal('GREAT_PERSON_CLASS_GENERAL', 5)
end
```

### 击杀→所有城市+生产力(等于目标战斗力)+杀者满血（Surtr）

```lua
function SiqiOnUnitKilledInCombat(killedPlayerID, killedUnitID, playerID, unitID)
    if not Siqi_IsPlayerLeader(playerID, LEADER_SURTR) then return end
    local pkilledUnit = UnitManager.GetUnit(killedPlayerID, killedUnitID)
    if pkilledUnit ~= nil then
        local combat = pkilledUnit:GetCombat()
        local pPlayer = Players[playerID]
        local pPlayerCities = pPlayer:GetCities()
        for i, pCity in pPlayerCities:Members() do
            pCity:GetBuildQueue():AddProgress(combat)
        end
    end
    -- 击杀者满血
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    if pUnit ~= nil then
        pUnit:SetDamage(0)
    end
end
```

### 击杀→获取被杀单位战略资源消耗量

```lua
function SiqiOnUnitKilledInCombat(killedPlayerID, killedUnitID, playerID, unitID)
    if not Siqi_IsPlayerLeader(playerID, TYPE_ZHUGELIANG) then return end
    local pkilledUnit = UnitManager.GetUnit(killedPlayerID, killedUnitID)
    if pkilledUnit == nil then return end
    local eKillUnit = GameInfo.Units[pkilledUnit:GetType()]
    local r = eKillUnit.StrategicResource
    if not r then return end  -- 无战略资源消耗
    local ResourceIndex = GameInfo.Resources[r].Index
    if ResourceIndex == nil then return end
    -- 查 Units_XP2 的 ResourceCost（维保费）
    local quary = "SELECT ResourceCost FROM Units_XP2 WHERE UnitType = '" .. eKillUnit.UnitType .. "'"
    local result = DB.Query(quary)
    if result == nil or #result == 0 then return end
    local resourceCost = result[1].ResourceCost or 0
    if resourceCost <= 0 then return end
    pPlayer:GetResources():ChangeResourceAmount(ResourceIndex, resourceCost)
end
```

### 特殊单位死亡→自动在首都重建（1血+清空移动力）

```lua
-- 特殊单位被击杀，在首都重建
function SiqiOnUnitKilledInCombat(killedPlayerID, killedUnitID, playerID, unitID)
    local pPlayer = Players[killedPlayerID]
    local num = SiqiFindPlayernum(pPlayer)
    if num == 0 then return end
    local pUnit = UnitManager.GetUnit(killedPlayerID, killedUnitID)
    if pUnit == nil or GameInfo.Units[pUnit:GetType()].UnitType ~= UNITLIST[num] then return end
    SiqiCreateUnit(killedPlayerID, num)
end

function SiqiCreateUnit(playerID, num)
    local pPlayer = Players[playerID]
    local pCapital = pPlayer:GetCities():GetCapitalCity()
    if pCapital == nil then return end
    UnitManager.InitUnit(playerID, UNITLIST[num], pCapital:GetX(), pCapital:GetY())
    pPlayer:SetProperty('SIQI_CUTE_5_0_Second_' .. LEADERSLIST[num], true)
end

-- 重建的单位在 UnitAddedToMap 中设为1血+清空移动力
function SiqiOnUnitAddedToMap(playerID, unitID)
    local pPlayer = Players[playerID]
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    if pUnit == nil then return end
    if GameInfo.Units[pUnit:GetType()].UnitType == UNITLIST[num] then
        if pPlayer:GetProperty('SIQI_CUTE_5_0_Second_' .. LEADERSLIST[num]) then
            pUnit:SetDamage(99)
            UnitManager.ChangeMovesRemaining(pUnit, -pUnit:GetMovesRemaining())
        end
    end
end
```

### 克洛丝濒死传送回首都+15经验+战斗力+3

```lua
function SiqiOnUnitDamageChanged(PlayerID, UnitID, newDamage, prevDamage)
    if not Siqi_IsPlayerLeader(PlayerID, LEADER_KROOS) then return end
    if newDamage < 100 then return end  -- 血量降到0（濒死）时触发

    local pUnit = UnitManager.GetUnit(PlayerID, UnitID)
    if pUnit == nil then return end
    if pUnit:GetType() ~= GameInfo.Units["UNIT_RESERVE_OPERATOR_TEAM_A1"].Index then return end

    local pPlayer = Players[PlayerID]
    local pCity = pPlayer:GetCities():GetCapitalCity()
    if pCity ~= nil then
        -- 传送回首都（不死亡）
        UnitManager.PlaceUnit(pUnit, pCity:GetX(), pCity:GetY())
        UnitManager.FinishMoves(pUnit)
        pUnit:GetExperience():ChangeExperience(15)
        local amount = pUnit:GetProperty('SIQI_KROOS_PLAYER_FROM_DEATH_UNIT_PROPERTY') or 0
        amount = amount + 3
        if amount <= 42 then  -- 战斗力上限42
            pUnit:SetProperty('SIQI_KROOS_PLAYER_FROM_DEATH_UNIT_PROPERTY', amount)
        end
    else
        -- 无己方城市：正常死亡
        pUnit:SetProperty('MaxHitPoints', 100)
        UnitManager.Kill(pUnit, false)
    end
end
```

---

## 经验值

### 战斗+10XP / 磐蟹联动+3XP — 在SiqiOnCombat中给予经验值

```lua
-- Ceobe R2：战斗中本单位+10经验
if attunitType.UnitType == UNIT_CEOBE and pPlayer:GetProperty('PROMOTION_CEOBE_R2') then
    attUnit:GetExperience():ChangeExperience(10)
end

-- 豆苗M2：磐蟹攻击/防御时，豆苗本体+3经验
if pPlayer:GetProperty('PROMOTION_BEANSTALK_M2') and attunitType.UnitType == 'UNIT_SIQI_STONE_CRAB' then
    local beanstalkUnit = UnitManager.GetUnit(attInfo.player, SiqiFindUnitid(attInfo.player, UNIT_BEANSTALK))
    if beanstalkUnit then beanstalkUnit:GetExperience():ChangeExperience(3) end
end
```

### 境外军事单位回合开始+3XP（Oblivionis）

```lua
function OnTurnActivated(playerID)
    if not self:IsLeader(playerID) then return end
    local pPlayer = Players[playerID]
    for i, unit in pPlayer:GetUnits():Members() do
        if unit:GetCombat() > 0 then
            local pPlot = Map.GetPlot(unit:GetX(), unit:GetY())
            if pPlot:GetOwner() ~= playerID then  -- 不在己方领土
                unit:GetExperience():ChangeExperience(3)
            end
        end
    end
end
```

### 经验值Property加成 — 每区域+1战斗经验

```lua
-- SQL侧：区域 → Property 累加到 Player
-- Lu侧：战斗时读取 Property 增量

function SiqiOnCombat(pCombatResult)
    local attacker = pCombatResult[CombatResultParameters.ATTACKER]
    local attInfo = attacker[CombatResultParameters.ID]
    local attUnit = UnitManager.GetUnit(attInfo.player, attInfo.id)

    if not Siqi_HasTraitProperty(attInfo.player, Property_player) then return end
    if not attUnit then return end

    local exp = Players[attInfo.player]:GetProperty(Property_unit) or 0
    if exp <= 0 then return end

    attUnit:GetExperience():ChangeExperience(exp)
end
```

### 翻倍经验 — 特定Ability下战斗经验×2

```lua
-- 模式：监听 Combat → 检测Ability → ChangeExperience
function OnCombatExpDouble(pCombatResult)
    local attacker = pCombatResult[CombatResultParameters.ATTACKER]
    local attUnit = UnitManager.GetUnit(attacker[CombatResultParameters.ID].player, attacker[CombatResultParameters.ID].id)
    if not attUnit then return end
    if attUnit:GetAbility() and attUnit:GetAbility():GetAbilityCount('ABILITY_DOUBLE_XP_UNIT') > 0 then
        attUnit:GetExperience():ChangeExperience(10)
    end
end
```

---

## 单位晋升

### 晋升叠加战斗力Ability（ABILITY_1~ABILITY_12逐个激活）

```lua
function SiqiOnUnitKilledInCombat(killedPlayerID, killedUnitID, playerID, unitID)
    if not Siqi_IsPlayerLeader(playerID, LEADER_TYPE) then return end
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    if pUnit == nil then return end
    local pUnitAbility = pUnit:GetAbility()
    if pUnitAbility == nil then return end
    -- 逐个检查ABILITY_1~ABILITY_12，找到第一个未激活的并激活
    for i = 1, 12 do
        if pUnitAbility:GetAbilityCount("ABILITY_LEADER_CIV_PROPERTY_" .. i) == 0 then
            pUnitAbility:ChangeAbilityCount("ABILITY_LEADER_CIV_PROPERTY_" .. i, 1)
            break
        end
    end
end
```

### 晋升叠加移动力Ability

```lua
-- 模式：Ability逐个递增激活，例如 ABILITY_PROMOTION_MOVE_1~10
-- 每层通过SQL Modifier增加1移动力
function OnUnitPromoted(playerID, params)
    local pUnit = UnitManager.GetUnit(playerID, params.unitid)
    local pUnitAbility = pUnit:GetAbility()
    local nextTier = pUnit:GetProperty('PROMOTION_MOVE_TIER') or 1
    if nextTier <= 10 then
        pUnitAbility:ChangeAbilityCount("ABILITY_PROMOTION_MOVE_" .. nextTier, 1)
        pUnit:SetProperty('PROMOTION_MOVE_TIER', nextTier + 1)
    end
end
```

### 战斗力继承（升级保留属性）

```lua
-- 单位升级前（UnitRemovedFromMap），记录属性到 Player
function SiqiOnUnitRemovedFromMap(playerID, unitID)
    if not Siqi_IsPlayerLeader(playerID, LEADER_TYPE) then return end
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    if pUnit == nil then return end
    local combat = pUnit:GetProperty('SIQI_ROPE_PLAYER_GRANT_COMBAT_PROPERTY') or 0
    local pPlayer = Players[playerID]
    pPlayer:SetProperty('SIQI_ROPE_PLAYER_COMBAT_PROPERTY', combat)
    -- 如果已有待继承的单位ID，立即触发继承
    if (pPlayer:GetProperty('SIQI_ROPE_PLAYER_UNIT_ID') or 0) ~= 0 then
        Siqi_JiChengProperty(playerID)
    end
end

-- 单位升级后（UnitUpgraded），记录新单位ID
function SiqiOnUnitUpgraded(playerID, unitID)
    if not Siqi_IsPlayerLeader(playerID, LEADER_TYPE) then return end
    local pPlayer = Players[playerID]
    pPlayer:SetProperty('SIQI_ROPE_PLAYER_UNIT_ID', unitID)
    if (pPlayer:GetProperty('SIQI_ROPE_PLAYER_COMBAT_PROPERTY') or 0) ~= 0 then
        Siqi_JiChengProperty(playerID)
    end
end

-- 继承：将Player记录的属性转移到新单位
function Siqi_JiChengProperty(playerID)
    local pPlayer = Players[playerID]
    local unitID = pPlayer:GetProperty('SIQI_ROPE_PLAYER_UNIT_ID')
    local combat = pPlayer:GetProperty('SIQI_ROPE_PLAYER_COMBAT_PROPERTY') or 0
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    if pUnit == nil then return end
    pUnit:SetProperty('SIQI_ROPE_PLAYER_GRANT_COMBAT_PROPERTY', combat)
    -- 清空Player侧记录
    pPlayer:SetProperty('SIQI_ROPE_PLAYER_UNIT_ID', 0)
    pPlayer:SetProperty('SIQI_ROPE_PLAYER_COMBAT_PROPERTY', 0)
end
```

---

## 辅助工具

### IsCombatUnits / IsZOCUnits

```lua
function IsCombatUnits(pUnit)
    if pUnit then
        if GameInfo.Units[pUnit:GetType()].Combat > 0
           or GameInfo.Units[pUnit:GetType()].RangedCombat > 0
           or GameInfo.Units[pUnit:GetType()].Bombard > 0 then
            return true
        end
        return false
    end
    return false
end

function IsZOCUnits(pUnit)
    if pUnit then
        if GameInfo.Units[pUnit:GetType()].ZoneOfControl then
            return true
        end
        return false
    end
    return false
end
```

### Siqi_FindMostDamageUnit — 找相邻6格最多伤害的己方单位

```lua
function Siqi_FindMostDamageUnit(pUnit)
    local pPlayer = Players[pUnit:GetOwner()]
    local MostDamageUnit = pUnit
    local MaxDamage = pUnit:GetDamage()
    for i = 0, 5 do
        local pAdjacentPlot = Map.GetAdjacentPlot(pUnit:GetX(), pUnit:GetY(), i)
        if pAdjacentPlot ~= nil then
            for loop, unit in ipairs(Units.GetUnitsInPlot(pAdjacentPlot)) do
                if unit ~= nil and pPlayer:GetID() == unit:GetOwner()
                   and unit:GetDamage() > MaxDamage then
                    MaxDamage = unit:GetDamage()
                    MostDamageUnit = unit
                end
            end
        end
    end
    -- 补充本格单位
    local pPlot = Map.GetPlot(pUnit:GetX(), pUnit:GetY())
    if pPlot ~= nil then
        for loop, unit in ipairs(Units.GetUnitsInPlot(pPlot)) do
            if unit ~= nil and pPlayer:GetID() == unit:GetOwner()
               and unit:GetDamage() > MaxDamage then
                MaxDamage = unit:GetDamage()
                MostDamageUnit = unit
            end
        end
    end
    return MostDamageUnit
end
```

### Siqi_FindUnitEnemy / Siqi_FindCityEnemy — 查找相邻格敌方单位/市中心

```lua
function Siqi_FindUnitEnemy(playerID, iX, iY)
    local pPlayer = Players[playerID]
    if pPlayer == nil then return {} end
    local unittable = {}
    for iDir = 0, 5 do
        for loop, unit in ipairs(Units.GetUnitsInPlot(Map.GetAdjacentPlot(iX, iY, iDir))) do
            if pPlayer:GetDiplomacy():IsAtWarWith(unit:GetOwner()) then table.insert(unittable, unit) end
        end
    end
    return unittable
end

function Siqi_FindCityEnemy(playerID, iX, iY)
    local pPlayer = Players[playerID]
    if pPlayer == nil then return nil end
    for iDir = 0, 5 do
        local pPlot = Map.GetAdjacentPlot(iX, iY, iDir)
        if pPlot then
            local pCity = CityManager.GetCityAt(pPlot:GetX(), pPlot:GetY())
            if pCity and pPlayer:GetDiplomacy():IsAtWarWith(pCity:GetOwner()) then return pCity end
        end
    end
    return nil
end
```

### SiqiFindFriendUnitAround — 判断相邻是否存在己方单位

```lua
function SiqiFindFriendUnitAround(playerID, unitID)
    local pPlayer = Players[playerID]
    if pPlayer == nil then return false end
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    if pUnit == nil then return false end
    local unitX = pUnit:GetX()
    local unitY = pUnit:GetY()
    for iDirection = 0, 5 do
        local pPlot = Map.GetAdjacentPlot(unitX, unitY, iDirection)
        for loop, unit in ipairs(Units.GetUnitsInPlot(pPlot)) do
            if unit ~= nil and unit:GetOwner() == playerID then
                return true
            end
        end
    end
    return false
end
```

---

## 改良设施触发

### 磐蟹石屋恢复移动力+满血

```lua
function SiqiOnUnitMoveComplete(playerID, unitID, iX, iY)
    local pPlot = Map.GetPlot(iX, iY)
    if pPlot:GetImprovementType() ~= IMPROVEMENT_STONE_CRAB_HOUSE then return end
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    local eUnit = GameInfo.Units[pUnit:GetType()]
    if eUnit.UnitType == 'UNIT_SIQI_STONE_CRAB' then  -- 仅磐蟹单位触发
        UnitManager.ChangeMovesRemaining(pUnit, pUnit:GetMaxMoves() - pUnit:GetMovesRemaining())
        pUnit:SetDamage(0)
    end
end
```

### 兔兔玩偶对经过单位造成伤害

```lua
function SiqiOnUnitMoveComplete(playerID, unitID, iX, iY)
    local pPlot = Map.GetPlot(iX, iY)
    if not pPlot or pPlot:GetImprovementType() ~= IMPROVEMENT_BUNNY_PLUSHIE then return end
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    local pPlayer = Players[playerID]
    local damage = 25
    if pUnit:GetOwner() ~= playerID then  -- 非己方单位伤害加倍
        damage = 50
    end
    if pUnit:GetDamage() + damage >= 100 then
        UnitManager.Kill(pUnit, false)
    else
        pUnit:ChangeDamage(damage)
    end
end
```

### 救助站满血

```lua
function SiqiOnUnitMoveComplete(playerID, unitID, iX, iY)
    local pPlot = Map.GetPlot(iX, iY)
    if pPlot:GetImprovementType() ~= INDEX_AID_STATION then return end
    if not Siqi_IsPlayerLeader(playerID, TYPE_SUSSURRO) then return end  -- 仅特定领袖
    if pPlot:IsImprovementPillaged() then return end
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    pUnit:SetDamage(0)
end
```

### 绿洲满血

```lua
function SiqiOnUnitMoveComplete(playerID, unitID, iX, iY)
    if not Siqi_IsPlayerLeader(playerID, TYPE_LEADER) then return end
    local pPlot = Map.GetPlot(iX, iY)
    local INDEX_FEATURE_OASIS = GameInfo.Features["FEATURE_OASIS"].Index
    if pPlot:GetFeatureType() == INDEX_FEATURE_OASIS then
        local pUnit = UnitManager.GetUnit(playerID, unitID)
        pUnit:SetDamage(0)
    end
end
```

---

## 自我衰减与倒计时

### Surtr递增自伤 + 死亡倒计时 — 单位每回合扣血递增，血量为0后5回合内死亡

```lua
-- 单位添加时设置血量上限101，初始每回合扣血2
function SiqiOnUnitAddedToMap(playerID, unitID)
    if not Siqi_IsPlayerLeader(playerID, LEADER_SURTR) then return end
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    if pUnit:GetCombat() > 0 then
        pUnit:SetProperty("MaxHitPoints", 101)
        if pUnit:GetProperty('Siqi_Surtr_Unit_DamagePerTurn') == nil then
            pUnit:SetProperty('Siqi_Surtr_Unit_DamagePerTurn', 2)
        end
    end
end

-- 回合开始时处理扣血+死亡倒计时+冰淇淋店恢复
function SiqiOnPlayerTurnStarted(playerID)
    if not Siqi_IsPlayerLeader(playerID, LEADER_SURTR) then return end
    local pPlayer = Players[playerID]
    for i, unit in pPlayer:GetUnits():Members() do
        if unit:GetCombat() > 0 then
            -- 保险：确保血量上限为101
            if unit:GetProperty('MaxHitPoints') ~= 101 then
                unit:SetProperty("MaxHitPoints", 101)
            end
            -- 死亡倒计时: 每回合-1, 归零时击杀并返还生产力
            if unit:GetProperty('Siqi_Surtr_Unit_daethtime') ~= nil then
                local deathtime = unit:GetProperty('Siqi_Surtr_Unit_daethtime') - 1
                unit:SetProperty('Siqi_Surtr_Unit_daethtime', deathtime)
                if deathtime <= 0 then
                    local cost = GameInfo.Units[unit:GetType()].Cost or 0
                    Siqi_GivePlayerAllCityProduction(playerID, cost * GAME_SPEED_MULTIPLIER)
                    unit:SetProperty('MaxHitPoints', 100)
                    UnitManager.Kill(unit, false)
                end
            end
            -- 冰淇淋店恢复：-30伤害，重置扣血速率
            local pPlot = Map.GetPlot(unit:GetX(), unit:GetY())
            if pPlot and pPlot:GetImprovementType() == GameInfo.Improvements["IMPROVEMENT_ICE_CREAM_SHOP"].Index then
                unit:ChangeDamage(-30)
                unit:SetProperty('Siqi_Surtr_Unit_DamagePerTurn', 2)
            else
                -- 递增扣血（最多递增到20/回合）
                local damage = unit:GetProperty('Siqi_Surtr_Unit_DamagePerTurn') or 2
                local unitdamage = unit:GetDamage()
                if damage + unitdamage >= 100 then
                    unit:ChangeDamage(100 - unitdamage)
                else
                    unit:ChangeDamage(damage)
                end
                if damage < 20 then
                    unit:SetProperty('Siqi_Surtr_Unit_DamagePerTurn', damage + 2)
                end
            end
        end
    end
end

-- 伤害达到100时挂5回合死亡倒计时
function SiqiOnUnitDamageChanged(PlayerID, UnitID, newDamage, prevDamage)
    if not Siqi_IsPlayerLeader(PlayerID, LEADER_SURTR) then return end
    if newDamage < 100 then return end
    local pUnit = UnitManager.GetUnit(PlayerID, UnitID)
    if pUnit and pUnit:GetProperty('Siqi_Surtr_Unit_daethtime') == nil then
        pUnit:SetProperty('Siqi_Surtr_Unit_daethtime', 5)
    end
end
```

---

## 被击反制（Debuff攻击者）

### 被攻击时给攻击者挂减战斗力Ability — 叠加多层减战斗力

```lua
-- 在 Combat 事件中，防御方是泡泡时触发
if defunitType.UnitType == UNIT_BUBBLE and defUnitDamage < 100 then
    -- L2: 防御时对攻击者反伤
    if pPlayer:GetProperty('PROMOTION_BUBBLE_L2') and attunitDamage < 100 then
        SiqiBubbledefenddamage(defInfo.player, attUnit, attunitDamage)
    end
    -- M1: 被攻击后敌方-8战斗力
    if pPlayer:GetProperty('PROMOTION_BUBBLE_M1') and attunitDamage < 100 then
        if attUnitAbility:GetAbilityCount('ABILITY_UNIT_BUBBLE_LESS_COMBAT_8') == 0 then
            attUnitAbility:ChangeAbilityCount('ABILITY_UNIT_BUBBLE_LESS_COMBAT_8', 1)
        end
    end
    -- M2: 被攻击后敌方-4战斗力
    if pPlayer:GetProperty('PROMOTION_BUBBLE_M2') and attunitDamage < 100 then
        if attUnitAbility:GetAbilityCount('ABILITY_UNIT_BUBBLE_LESS_COMBAT_4') == 0 then
            attUnitAbility:ChangeAbilityCount('ABILITY_UNIT_BUBBLE_LESS_COMBAT_4', 1)
        end
    end
end
```

### 回合开始时对相邻敌方单位自动反伤+挂减战斗力

```lua
-- 每回合自动扫描周围敌方单位，造成反伤+减战斗力debuff
function SiqiOnPlayerTurnActivated(playerID, bIsFirstTime)
    if not bIsFirstTime then return end
    if not Siqi_IsPlayerLeader(playerID, LEADER_BUBBLE) then return end
    if not pPlayer:GetProperty('PROMOTION_BUBBLE_L3') then return end
    local unitID = SiqiFindUnitid(playerID, UNIT_BUBBLE)
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    local enemies = SiqiGetEnemyUnitAround(playerID, pUnit:GetX(), pUnit:GetY())
    for _, unit in ipairs(enemies) do
        SiqiBubbledefenddamage(playerID, unit, unit:GetDamage())
        local pUnitAbility = unit:GetAbility()
        if pPlayer:GetProperty('PROMOTION_BUBBLE_M1')
           and pUnitAbility:GetAbilityCount('ABILITY_UNIT_BUBBLE_LESS_COMBAT_8') == 0 then
            unit:GetAbility():ChangeAbilityCount("ABILITY_UNIT_BUBBLE_LESS_COMBAT_8", 1)
        end
        if pPlayer:GetProperty('PROMOTION_BUBBLE_M2')
           and pUnitAbility:GetAbilityCount('ABILITY_UNIT_BUBBLE_LESS_COMBAT_4') == 0 then
            unit:GetAbility():ChangeAbilityCount("ABILITY_UNIT_BUBBLE_LESS_COMBAT_4", 1)
        end
    end
end
```

### 受击反伤 50（联机稳定版，攻击者侧提交；0054 实测）

反伤需要"攻击者身份"，而攻击由玩家在回合内发起 → 由**攻击者侧 UI** 唯一提交（见 lua-multiplayer-stable §六决策表新增行）；防守方被动受伤类才 GP 直连。

```lua
-- UI 端（Events.Combat 在 UI 环境可用）：
function OnUiCombatReflect(pCombatResult)
    local defender = pCombatResult[CombatResultParameters.DEFENDER];
    local attacker = pCombatResult[CombatResultParameters.ATTACKER];
    if defender == nil or attacker == nil then return end
    local defInfo = defender[CombatResultParameters.ID];
    local attInfo = attacker[CombatResultParameters.ID];
    if defInfo == nil or attInfo == nil then return end
    if defInfo.type ~= 1 or not IsCiv(defInfo.player) then return end   -- 防守方须为目标文明单位
    if (defender[CombatResultParameters.DAMAGE_TO] or 0) <= 0 then return end
    if attInfo.type ~= 1 then return end                                 -- 攻击者须为单位
    local localPlayerID = Game.GetLocalPlayer();
    if attInfo.player ~= localPlayerID and (localPlayerID ~= 0 or IsHuman(attInfo.player)) then return end
    UI.RequestPlayerOperation(localPlayerID, PlayerOperations.EXECUTE_SCRIPT, {
        OnStart          = 'SIQI_XXXX_REFLECT_SUBMIT',
        AttackerPlayerID = attInfo.player,
        AttackerUnitID   = attInfo.id,
        DefenderPlayerID = defInfo.player,
        DefenderUnitID   = defInfo.id,
    });
end

-- GP 端：无脑执行（nil 防护 + 每回合冷却戳，超血上限击杀）
function OnReflectSubmit(playerID, params)
    if params == nil then return end
    local pDefender = UnitManager.GetUnit(params.DefenderPlayerID, params.DefenderUnitID);
    if pDefender == nil or pDefender:IsDead() then return end
    local pAttacker = UnitManager.GetUnit(params.AttackerPlayerID, params.AttackerUnitID);
    if pAttacker == nil or pAttacker:IsDead() then return end
    local turn = Game.GetCurrentGameTurn();
    if pDefender:GetProperty('SIQI_XXXX_REFLECT_TURN') == turn then return end
    pDefender:SetProperty('SIQI_XXXX_REFLECT_TURN', turn);
    AttachUnitDamage(pAttacker, 50);  -- 见"伤害"节：超血量上限自动击杀
end
```

---

## 条件额外伤害

### 攻击相邻特定单位类型的敌人时额外造成50%伤害（豆苗L3 + 磐蟹）

```lua
-- 在 Combat 事件中
if num == BEANSTALK and pPlayer:GetProperty('PROMOTION_BEANSTALK_L3') and defUnitDamage < 100 then
    if SiqiFindCrabUnitAround(defInfo.player, defInfo.id) then
        local damage = math.floor(defdamage * 0.5)
        if defUnitDamage + damage >= 100 then
            UnitManager.Kill(defUnit, false)
        else
            defUnit:ChangeDamage(damage)
        end
    end
end
```

### 攻击区域时额外造成防御力75%的伤害（剥壳）

```lua
-- 在 Combat 事件中，defInfo.type == 3（攻击区域）
if attUnit and GameInfo.Units[attUnit:GetType()].UnitType == UNIT_CEOBE then
    if defInfo.type == 3 then
        local pDistrict = CityManager.GetDistrict(defInfo.player, defInfo.id)
        if pDistrict and pPlayer:GetProperty('PROMOTION_CEOBE_M1') then
            local Citydef = pDistrict:GetDefenseStrength()
            local damage = math.floor(Citydef * 0.75)
            pDistrict:ChangeDamage(DefenseTypes.DISTRICT_GARRISON, damage)
        end
    end
end
```

### 战后百分比回血 — 受到伤害后治疗伤害量的一定比例

```lua
function OnUnitDamageChanged(playerID, unitID, newDamage, oldDamage)
    local pUnit = Players[playerID]:GetUnits():FindID(unitID)
    if pUnit and pUnit:GetProperty('PEN_XIANZHOU_ENABLE_HEAL_AFTER_COMBAT')
       and pUnit:GetProperty('PEN_XIANZHOU_ENABLE_HEAL_AFTER_COMBAT') > 0 then
        if newDamage > oldDamage then
            local HealCount = math.floor((newDamage - oldDamage) * HealBonus / 100)
            pUnit:ChangeDamage(-HealCount)
        end
    end
end
```

---

## 移动力削减

### 二进制移动力削减 — 根据敌方最大移动力分位削减

```lua
-- Ceobe L1 "很冰的斧": 攻击后根据目标最大移动力逐位削减
-- Ability_0为总开关, Ability_1~4分别对应二进制位的8/4/2/1
function SiqiCeobeL1Ability(n)
    if n >= 15 then return {1, 1, 1, 1}
    elseif n <= 0 then return {0, 0, 0, 0}
    end
    return {
        math.floor(n / 8),
        math.floor((n % 8) / 4),
        math.floor((n % 4) / 2),
        n % 2
    }
end

-- Combat 中触发
if attunitType.UnitType == UNIT_CEOBE and defUnitDamage < 100 then
    if pPlayer:GetProperty('PROMOTION_CEOBE_L1')
       and defUnitAbility:GetAbilityCount('ABILITY_UNIT_CEOBE_LESS_MOVE_0') == 0 then
        local defmove = defUnit:GetMaxMoves()
        local abcd = SiqiCeobeL1Ability(defmove - 1)
        defUnitAbility:ChangeAbilityCount("ABILITY_UNIT_CEOBE_LESS_MOVE_0", 1)  -- 总开关
        for i = 1, 4 do
            defUnitAbility:ChangeAbilityCount("ABILITY_UNIT_CEOBE_LESS_MOVE_" .. i, abcd[i])
        end
    end
end
-- SQL侧: ABILITY_1~4 分别通过 Modifier 减 8/4/2/1 移动力
```

---

## 条件自身能力（邻接触发）

### 独行长路 — 相邻无友方时获得战斗力+移动力，每回合补满移动力

```lua
function SiqiOnPlayerTurnActivated(playerID, bIsFirstTime)
    if not bIsFirstTime then return end
    if not Siqi_IsPlayerLeader(playerID, LEADER_CEOBE) then return end
    if not pPlayer:GetProperty('PROMOTION_CEOBE_M2') then return end
    local unitID = SiqiFindUnitid(playerID, UNIT_CEOBE)
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    local pUnitAbility = pUnit:GetAbility()
    local Abilitynum = pUnitAbility:GetAbilityCount('ABILITY_UNIT_CEOBE_COMBAT_AND_MOVE')
    if SiqiFindFriendUnitAround(playerID, unitID) then
        -- 有友方：移除加成
        if Abilitynum > 0 then
            pUnitAbility:ChangeAbilityCount('ABILITY_UNIT_CEOBE_COMBAT_AND_MOVE', -Abilitynum)
        end
    else
        -- 无友方：激活加成
        if Abilitynum == 0 then
            pUnitAbility:ChangeAbilityCount('ABILITY_UNIT_CEOBE_COMBAT_AND_MOVE', 1)
        end
    end
    -- 每回合补满移动力
    if pUnit:GetMovesRemaining() ~= pUnit:GetMaxMoves() then
        UnitManager.ChangeMovesRemaining(pUnit, pUnit:GetMaxMoves() - pUnit:GetMovesRemaining())
    end
end
```

---

## 经验共享光环

### 战斗经验共享给2环内所有己方单位

```lua
-- 获取战斗双方各自获得的经验，复制给2环内所有己方单位
function SiqiOnCombat(pCombatResult)
    local attacker = pCombatResult[CombatResultParameters.ATTACKER]
    local defender = pCombatResult[CombatResultParameters.DEFENDER]
    local attInfo = attacker[CombatResultParameters.ID]
    local defInfo = defender[CombatResultParameters.ID]
    if not Siqi_IsPlayerLeader(attInfo.player, LEADER_TYPE)
       and not Siqi_IsPlayerLeader(defInfo.player, LEADER_TYPE) then return end
    local exp1 = attacker[CombatResultParameters.EXPERIENCE_CHANGE] or 0
    local exp2 = defender[CombatResultParameters.EXPERIENCE_CHANGE] or 0
    if exp1 == 0 and exp2 == 0 then return end
    if Siqi_IsPlayerLeader(attInfo.player, LEADER_TYPE) then
        Siqi_ChangeExp(attInfo.player, attInfo.id, exp1)
    end
    if Siqi_IsPlayerLeader(defInfo.player, LEADER_TYPE) then
        Siqi_ChangeExp(defInfo.player, defInfo.id, exp2)
    end
end

function Siqi_ChangeExp(playerID, unitID, exp)
    if exp <= 0 then return end
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    if pUnit == nil then return end
    local iX, iY = pUnit:GetX(), pUnit:GetY()
    local kplot = Map.GetNeighborPlots(iX, iY, 2)  -- 2环范围
    for _, plot in ipairs(kplot) do
        if plot:GetX() ~= iX and plot:GetY() ~= iY then  -- 不含自身格
            for loop, unit in ipairs(Units.GetUnitsInPlot(plot)) do
                if unit and unit:GetOwner() == playerID then
                    unit:GetExperience():ChangeExperience(exp)
                end
            end
        end
    end
end
```

---

## 定时炸弹单位

### 特殊单位每回合有概率自动死亡

```lua
function SiqiOnPlayerTurnActivated(playerID, bIsFirstTime)
    if not bIsFirstTime then return end
    if not Siqi_IsPlayerLeader(playerID, LEADER_TYPE) then return end
    local pPlayer = Players[playerID]
    for i, unit in pPlayer:GetUnits():Members() do
        if GameInfo.Units[unit:GetType()].UnitType == 'UNIT_SIQI_U0006_5_2' then
            if SiqiRandnumber(2857) then  -- 2.857%概率 (2857/100000)
                UnitManager.Kill(unit, true)
            end
        end
    end
end

-- 通用概率函数（100000分率）
function SiqiRandnumber(probability)
    return Game.GetRandNum(100000) < probability
end
```

---

## 区域防御伤害

### 敌方单位经过伏击区区域时受到30伤害

```lua
-- UnitMoveComplete 中判断是否相邻敌对伏击区
function SiqiOnUnitMoveComplete(playerID, unitID, iX, iY)
    local owner, IsNearAmbushZone = Siqi_IsUnitAdjacentDistrict(playerID, unitID, INDEX_AMBUSH_ZONE)
    if IsNearAmbushZone and Siqi_IsPlayerCivilizationEnemy(playerID, owner) then
        local pUnit = UnitManager.GetUnit(playerID, unitID)
        Siqi_AttachUnitDamage(pUnit, 30)
    end
end

-- 判断单位或相邻格是否有目标区域
function Siqi_IsUnitAdjacentDistrict(playerID, unitID, districtID)
    local unit = UnitManager.GetUnit(playerID, unitID)
    if unit == nil then return -1, false end
    local pPlot = Map.GetPlot(unit:GetX(), unit:GetY())
    -- 检查自身格
    if pPlot:GetDistrictType() == districtID then
        return pPlot:GetOwner(), true
    end
    -- 检查相邻6格
    for iDir = 0, 5 do
        local pAdj = Map.GetAdjacentPlot(pPlot:GetX(), pPlot:GetY(), iDir)
        if pAdj and pAdj:GetDistrictType() == districtID then
            return pAdj:GetOwner(), true
        end
    end
    return -1, false
end
```

---

## 击杀→宗教压力扩散

### 击杀单位后在大范围内扩散己方宗教压力

```lua
-- 在 OnCombatOccurred 中，攻击者单位存活且防御者死亡时触发
if pAttackingUnit and pDefendingUnit
   and (pDefendingUnit:IsDead() or pDefendingUnit:IsDelayedDeath()) then
    if pAttackerLeader == "LEADER_SIQI_L0009" then
        local x, y = pAttackingUnit:GetX(), pAttackingUnit:GetY()
        local power = pDefendingUnit:GetCombat()
        local religionType = pAttackerReligion:GetReligionTypeCreated()
        if x and y and religionType and religionType ~= -1 then
            ApplyByzantiumTrait(x, y, power, religionType, attackerPlayerID)
        end
    end
end

-- 扫描范围内所有城市并施加宗教压力
function ApplyByzantiumTrait(x, y, power, religionType, playerID)
    local pPlot = Map.GetPlot(x, y)
    for i = 1, 90 do  -- 90格覆盖（约5格半径）
        local plotScanned = GetAdjacentTiles(pPlot, i)
        if plotScanned and plotScanned:IsCity() then
            local pCity = Cities.GetCityInPlot(plotScanned)
            local impact = 175  -- 固定压力值（或 = power * multiplier）
            pCity:GetReligion():AddReligiousPressure(playerID, religionType, impact, -1)
        end
    end
end
```

---

## 晋升满级克隆

### 特定单位晋升到满级时在首都生成一个新同款单位

```lua
function OnSiqiOnUnitPromoted(playerID, params)
    local unitID = params.unitid
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    if pUnit and pUnit:GetType() == GameInfo.Units["UNIT_RESERVE_OPERATOR_TEAM_A1"].Index then
        local newpromotion = params.newpromotion
        pUnit:SetProperty('Siqi_Cute_' .. newpromotion, true)  -- 记录晋升
        if params.amount == 5 then  -- 晋升满（5次）
            local pPlayer = Players[playerID]
            local pCity = pPlayer:GetCities():GetCapitalCity()
            local newUnit = UnitManager.InitUnit(playerID, 'UNIT_RESERVE_OPERATOR_TEAM_A1', pCity:GetX(), pCity:GetY())
            newUnit:SetProperty("MaxHitPoints", 101)
        end
    end
end
```

---

## 技能冷却/持续回合系统

### 单位主动技能 — 持续N回合，冷却M回合，到期自动移除

```lua
-- 激活技能
local SKILL_ABILITY = "ABILITY_UNIT_SKILL_S1"
local SKILL_DURATION = 3
local SKILL_COOLDOWN = 6

function ActivateSkill(playerID, params)
    local pUnit = UnitManager.GetUnit(playerID, params.unitID)
    if pUnit == nil then return end
    local currentTurn = params.currentTurn or Game.GetCurrentGameTurn()
    -- 检查冷却
    local lastTurn = pUnit:GetProperty('SKILL_LAST_USED_TURN')
    if lastTurn and (currentTurn - lastTurn) < SKILL_COOLDOWN then return end
    -- 激活
    pUnit:GetAbility():ChangeAbilityCount(SKILL_ABILITY, 1)
    pUnit:SetProperty('SKILL_LAST_USED_TURN', currentTurn)
    pUnit:SetProperty('SKILL_EXPIRE_TURN', currentTurn + SKILL_DURATION)
    UnitManager.FinishMoves(pUnit)
end

-- 回合开始检查到期自动移除
function OnTurnBeginRemoveExpired(playerID, bFirstTime)
    if not bFirstTime then return end
    local currentTurn = Game.GetCurrentGameTurn()
    for _, pUnit in pPlayer:GetUnits():Members() do
        local expireTurn = pUnit:GetProperty('SKILL_EXPIRE_TURN')
        if expireTurn and currentTurn >= expireTurn then
            local ability = pUnit:GetAbility()
            if ability:GetAbilityCount(SKILL_ABILITY) > 0 then
                ability:ChangeAbilityCount(SKILL_ABILITY, -1)
            end
            pUnit:SetProperty('SKILL_EXPIRE_TURN', nil)
        end
    end
end
```

---

## 击杀堆叠属性

### 每次击杀+1 Property（永久成长，不依赖晋升）

```lua
function SiqiOnUnitKilledInCombat(killedPlayerID, killedUnitID, playerID, unitID)
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    if pUnit == nil then return end
    if GameInfo.Units[pUnit:GetType()].UnitType ~= 'UNIT_SIQI_U0006_7' then return end
    local property = pUnit:GetProperty("SIQI_L0006_ABILITY_0192") or 0
    pUnit:SetProperty("SIQI_L0006_ABILITY_0192", property + 1)
end
-- SQL侧通过 Modifier 将 Property 值转化为战斗力加成
```

---

## 伤害阈值触发

### 根据受伤程度设置分档Property（每10血一档）

```lua
function SiqiOnUnitDamageChanged(PlayerID, UnitID, newDamage, prevDamage)
    if not Siqi_IsPlayerLeader(PlayerID, LEADER_TYPE) then return end
    local pUnit = UnitManager.GetUnit(PlayerID, UnitID)
    if pUnit == nil then return end
    -- 每10点伤害为一档，避免同一档内重复设置
    local newTier = math.floor(newDamage / 10)
    local oldTier = pUnit:GetProperty("UNIT_DAMAGE_TIER") or 0
    if oldTier == newTier then return end
    pUnit:SetProperty("UNIT_DAMAGE_TIER", newTier)
end
-- SQL侧: 不同Tier触发不同的Modifier（如低血量+战斗力）
```
