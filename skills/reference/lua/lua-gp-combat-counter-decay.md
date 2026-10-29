# lua-gp-combat — 战斗类 GP 函数 — 反制/衰减

> 分册：由 [lua-gp-combat.md](lua-gp-combat.md) 按主题拆出；覆盖 自我衰减与倒计时、Surtr递增自伤 + 死亡倒计时 — 单位每回合扣血递增，血量为0后5回合内死亡、被击反制（Debuff攻击者）、被攻击时给攻击者挂减战斗力Ability — 叠加多层减战斗力、回合开始时对相邻敌方单位自动反伤+挂减战斗力、受击反伤 50（联机稳定版，攻击者侧提交；0054 实测）、条件额外伤害、攻击相邻特定单位类型的敌人时额外造成50%伤害（豆苗L3 + 磐蟹）、攻击区域时额外造成防御力75%的伤害（剥壳）、战后百分比回血 — 受到伤害后治疗伤害量的一定比例、移动力削减、二进制移动力削减 — 根据敌方最大移动力分位削减。触发：自我衰减、被击反制、条件伤害、移动削减时。

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

