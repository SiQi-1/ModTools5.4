# lua-gp-combat — 战斗类 GP 函数 — 晋升/辅助

> 分册：由 [lua-gp-combat.md](lua-gp-combat.md) 按主题拆出；覆盖 单位晋升、晋升叠加战斗力Ability（ABILITY_1~ABILITY_12逐个激活）、晋升叠加移动力Ability、战斗力继承（升级保留属性）、辅助工具、IsCombatUnits / IsZOCUnits、Siqi_FindMostDamageUnit — 找相邻6格最多伤害的己方单位、Siqi_FindUnitEnemy / Siqi_FindCityEnemy — 查找相邻格敌方单位/市中心、SiqiFindFriendUnitAround — 判断相邻是否存在己方单位、改良设施触发、磐蟹石屋恢复移动力+满血、兔兔玩偶对经过单位造成伤害、救助站满血、绿洲满血。触发：单位晋升、辅助工具、改良触发时。

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

