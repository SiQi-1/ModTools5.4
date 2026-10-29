# lua-gp-combat — 战斗类 GP 函数 — 击杀/经验

> 分册：由 [lua-gp-combat.md](lua-gp-combat.md) 按主题拆出；覆盖 击杀效果、击败蛮族80%概率转建造者、击杀敌对单位→+5大将军点数、击杀→所有城市+生产力(等于目标战斗力)+杀者满血（Surtr）、击杀→获取被杀单位战略资源消耗量、特殊单位死亡→自动在首都重建（1血+清空移动力）、克洛丝濒死传送回首都+15经验+战斗力+3、经验值、战斗+10XP / 磐蟹联动+3XP — 在SiqiOnCombat中给予经验值、境外军事单位回合开始+3XP（Oblivionis）、经验值Property加成 — 每区域+1战斗经验、翻倍经验 — 特定Ability下战斗经验×2。触发：击杀效果、经验值处理时。

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

