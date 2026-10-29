# lua-gp-combat — 战斗类 GP 函数 — 光环/特殊系统

> 分册：由 [lua-gp-combat.md](lua-gp-combat.md) 按主题拆出；覆盖 条件自身能力（邻接触发）、独行长路 — 相邻无友方时获得战斗力+移动力，每回合补满移动力、经验共享光环、战斗经验共享给2环内所有己方单位、定时炸弹单位、特殊单位每回合有概率自动死亡、区域防御伤害、敌方单位经过伏击区区域时受到30伤害、击杀→宗教压力扩散、击杀单位后在大范围内扩散己方宗教压力、晋升满级克隆、特定单位晋升到满级时在首都生成一个新同款单位、技能冷却/持续回合系统、单位主动技能 — 持续N回合，冷却M回合，到期自动移除、击杀堆叠属性、每次击杀+1 Property（永久成长，不依赖晋升）、伤害阈值触发、根据受伤程度设置分档Property（每10血一档）。触发：邻接触发、经验光环、炸弹、区域防御、冷却等特殊系统时。

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
