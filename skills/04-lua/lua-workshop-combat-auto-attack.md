# lua-workshop-combat-auto-attack -- 自动远程攻击系统

从工坊 Mod **Auto Range Attack** (Ruivo, 3493733508) 提炼。核心模式：玩家回合开始时，自动遍历所有远程单位/城市/区域，对射程内的有效目标执行自动攻击，攻击后通过 GP 事件恢复部分移动力。

---

## 快速索引

| 模式 | 核心 API / 技术 | 适用场景 |
|------|----------------|---------|
| BFS 环形扫描 | `Map.GetAdjacentPlots` + visited set | 获取射程内所有地块 |
| 单位自动操作 | `UnitManager.CanStartOperation / RequestOperation` | 自动执行单位行动 |
| 城市/区域自动攻击 | `CityManager.GetCommandTargets / RequestCommand` | 自动防御射击 |
| 空军自动空袭 | `GameInfo.Units[].Domain == "DOMAIN_AIR"` | 区分空军与地面远程 |
| GP 事件回调 | `UI.RequestPlayerOperation(EXECUTE_SCRIPT)` | UI→GP 线程通信 |
| 回合次数节制 | `Game.GetCurrentGameTurn()` 防重复 | 每回合每个单位只触发一次 |

---

## 架构概览

该 Mod 由两个 Lua 文件组成：

```
Ruivo_Auto_Range_Attack.lua    → 游戏脚本 (GameplayScript)，注册 Events.PlayerTurnActivated
Ruivo_Auto_Range_Attack_GP.lua → UI 脚本 (InGameUIAddin)，注册 GameEvents + Events.CombatVisBegin
```

**关键架构决策**：自动攻击需要"攻击→恢复移动力→攻击"循环，但单位攻击操作是异步的。Mod 通过 `UI.RequestPlayerOperation(EXECUTE_SCRIPT)` 唤回 GP 线程执行 `RestoreUnitAttacks + RestoreMovementToFormation + ChangeMovesRemaining(-1)`，实现"攻击后只扣 1 点移动力"的语义。

---

## XML 配合

本系统无独立 UI 面板，纯通过 `Events.PlayerTurnActivated` / `Events.CombatVisBegin` 游戏事件自动触发。战斗报告文本通过原版 `LOC_COMBAT_*` 键呈现，无需额外 XML 控件。

---

## 一、BFS 环形地块扫描

用于获取以单位为中心、指定环数（射程）内的所有可达地块。

```lua
function ruivoGetRingsPlots(iX, iY, maxRing)
    maxRing = tonumber(maxRing)
    local resultPlots = {}
    local visited = {}    -- key = plot:GetIndex()
    local queue = {}

    local centerPlot = Map.GetPlot(iX, iY)
    if not centerPlot then return resultPlots end

    -- 初始化中心格
    local centerIndex = centerPlot:GetIndex()
    visited[centerIndex] = true
    table.insert(resultPlots, centerPlot)
    table.insert(queue, centerPlot)

    while #queue > 0 do
        local currentPlot = table.remove(queue, 1)
        local dist = Map.GetPlotDistance(iX, iY, currentPlot:GetX(), currentPlot:GetY())

        if dist < maxRing then
            local adjPlots = Map.GetAdjacentPlots(currentPlot:GetX(), currentPlot:GetY())
            for _, adj in ipairs(adjPlots) do
                if adj then
                    local adjIndex = adj:GetIndex()
                    if not visited[adjIndex] then
                        visited[adjIndex] = true
                        table.insert(resultPlots, adj)
                        table.insert(queue, adj)
                    end
                end
            end
        end
    end
    return resultPlots
end
```

**要点**：
- 使用 `plot:GetIndex()` 作为 visited key，比坐标对更高效
- `Map.GetAdjacentPlots` 一次获取 6 个相邻地块（六边形网格）
- `queue` 用 `table.remove(queue, 1)` 实现 BFS（O(n) 出队，适合小范围扫描）
- 返回包含中心格的完整地块列表（含 `centerPlot`）

---

## 二、单位自动远程攻击

### 2.1 地面远程攻击

```lua
function Ruivo_OnPlayerTurnActivated(playerID)
    local pPlayer = Players[playerID]
    if not pPlayer or not pPlayer:IsHuman() then return end  -- 仅人类玩家

    for _, unit in pPlayer:GetUnits():Members() do
        if unit:GetRange() > 0 then
            local attacked = false
            local range = unit:GetRange()

            for _, plot in ipairs(ruivoGetRingsPlots(unit:GetX(), unit:GetY(), range)) do
                local tParameters = {
                    [UnitOperationTypes.PARAM_X] = plot:GetX(),
                    [UnitOperationTypes.PARAM_Y] = plot:GetY()
                }

                -- 自动射击
                if UnitManager.CanStartOperation(unit, UnitOperationTypes.RANGE_ATTACK, nil, tParameters) then
                    UnitManager.RequestOperation(unit, UnitOperationTypes.RANGE_ATTACK, tParameters)
                    attacked = true
                end

                -- 自动空袭（如果是空军）
                TryAutoAirAttack(unit, plot)
            end

            -- 攻击过则通过 GP 事件恢复移动力
            if attacked then
                local kPara = {
                    playerID = playerID,
                    attackerID = unit:GetID(),
                    OnStart = 'restore_1_move'
                }
                UI.RequestPlayerOperation(playerID, PlayerOperations.EXECUTE_SCRIPT, kPara)
            end
        end
    end
end
Events.PlayerTurnActivated.Add(Ruivo_OnPlayerTurnActivated)
```

**关键 API**：
| API | 说明 |
|-----|------|
| `unit:GetRange()` | 单位远程攻击射程，>0 表示是远程单位 |
| `UnitManager.CanStartOperation(unit, op, nil, params)` | 检查单位能否执行指定操作 |
| `UnitManager.RequestOperation(unit, op, params)` | 发出操作请求，游戏引擎在下个 tick 处理 |
| `UI.RequestPlayerOperation(pid, EXECUTE_SCRIPT, {OnStart='name'})` | 从游戏脚本线程唤起 UI 脚本的 GameEvents 回调 |

### 2.2 空军自动空袭

```lua
function TryAutoAirAttack(unit, plot)
    -- 必须是空军单位
    if GameInfo.Units[unit:GetType()].Domain ~= "DOMAIN_AIR" then return end

    local CanAirAttack = false
    local airAttackerPlayerID = unit:GetOwner()
    local tParameters = {
        [UnitOperationTypes.PARAM_X] = plot:GetX(),
        [UnitOperationTypes.PARAM_Y] = plot:GetY()
    }

    -- 检查目标地块上的单位
    local targetUnits = Units.GetUnitsInPlot(plot)
    for _, targetUnit in ipairs(targetUnits) do
        local targetPlayerID = targetUnit:GetOwner()
        local targetPlayer = Players[targetPlayerID]
        local civType = PlayerConfigurations[targetPlayerID]:GetCivilizationTypeName()

        if civType == "CIVILIZATION_FREE_CITIES"
        or civType == "CIVILIZATION_BARBARIAN"
        or targetPlayer:GetDiplomacy():IsAtWarWith(airAttackerPlayerID) then
            CanAirAttack = true
            break
        end
    end

    -- 检查目标是否有敌方区域
    if not CanAirAttack and plot:GetDistrictType() ~= -1 then
        local districtOwnerID = plot:GetOwner()
        if districtOwnerID ~= -1 then
            local districtOwner = Players[districtOwnerID]
            if districtOwner:GetDiplomacy():IsAtWarWith(airAttackerPlayerID) then
                CanAirAttack = true
            end
        end
    end

    -- 执行空袭
    if CanAirAttack then
        if UnitManager.CanStartOperation(unit, UnitOperationTypes.AIR_ATTACK, nil, tParameters) then
            UnitManager.RequestOperation(unit, UnitOperationTypes.AIR_ATTACK, tParameters)
        end
    end
end
```

**空军与地面远程的区别**：
- 地面远程：直接用 `CanStartOperation(RANGE_ATTACK)` 判断，游戏引擎自动校验目标合法性
- 空军空袭：必须先手动验证目标是否为敌方（因为空袭可打击无单位的地块上的区域）

**敌意判定三层逻辑**：
1. `CivilizationTypeName == "CIVILIZATION_FREE_CITIES"` — 自由城邦始终可攻击
2. `CivilizationTypeName == "CIVILIZATION_BARBARIAN"` — 蛮族始终可攻击
3. `IsAtWarWith(attackerPlayerID)` — 与攻击方处于战争状态

---

## 三、城市与区域自动攻击

### 3.1 遍历逻辑

```lua
function Ruivo_Auto_Dis_City_Attack(playerID)
    local pPlayer = Players[playerID]
    if not pPlayer or not pPlayer:IsHuman() then return end

    -- 遍历城市本体
    for _, pCity in pPlayer:GetCities():Members() do
        TryAutoCityAttack(pCity)

        -- 遍历所有区域
        local districts = pCity:GetDistricts()
        for _, pDistrict in districts:Members() do
            -- 只处理有防御能力的区域（HitPoints > 0）
            if GameInfo.Districts[pDistrict:GetType()].HitPoints > 0 then
                TryAutoDistrictAttack(pDistrict)
            end
        end
    end
end
Events.PlayerTurnActivated.Add(Ruivo_Auto_Dis_City_Attack)
```

**关键判定**：`GameInfo.Districts[].HitPoints > 0` 区分哪些区域有防御能力。无 HitPoints 的区域（如社区、水渠）不需要自动攻击。

### 3.2 攻击指令执行

```lua
function TryAutoCityAttack(pCity)
    local tResults = CityManager.GetCommandTargets(pCity, CityCommandTypes.RANGE_ATTACK, {})
    ProcessAutoAttack(pCity, tResults)
end

function TryAutoDistrictAttack(pDistrict)
    local tResults = CityManager.GetCommandTargets(pDistrict, CityCommandTypes.RANGE_ATTACK, {})
    ProcessAutoAttack(pDistrict, tResults)
end

function ProcessAutoAttack(source, tResults)
    local allPlots = tResults[CityCommandResults.PLOTS]
    local modifiers = tResults[CityCommandResults.MODIFIERS]

    if allPlots ~= nil then
        for i, modifier in ipairs(modifiers) do
            if modifier == CityCommandResults.MODIFIER_IS_TARGET then
                local targetPlotID = allPlots[i]
                local plot = Map.GetPlotByIndex(targetPlotID)

                local tParameters = {
                    [UnitOperationTypes.PARAM_X] = plot:GetX(),
                    [UnitOperationTypes.PARAM_Y] = plot:GetY()
                }

                if CityManager.CanStartCommand(source, CityCommandTypes.RANGE_ATTACK, tParameters) then
                    CityManager.RequestCommand(source, CityCommandTypes.RANGE_ATTACK, tParameters)
                end
            end
        end
    end
end
```

**城市/区域攻击与单位攻击的关键区别**：

| | 单位攻击 | 城市/区域攻击 |
|---|---|---|
| 获取目标 | 手动 BFS 扫描射程 | `CityManager.GetCommandTargets` |
| 目标结构 | plots 列表 | `{PLOTS=..., MODIFIERS=...}` 配对列表 |
| 目标筛选 | `CanStartOperation` 自动筛选 | `MODIFIER_IS_TARGET` 标记筛选 |
| 执行命令 | `UnitManager.RequestOperation` | `CityManager.RequestCommand` |
| 操作类型 | `UnitOperationTypes.RANGE_ATTACK` | `CityCommandTypes.RANGE_ATTACK` |

---

## 四、GP 线程攻击后移动力恢复

这是该 Mod 最精巧的设计：自动攻击后只扣减 1 点移动力（而非让单位回合结束）。

### 4.1 游戏脚本端触发

```lua
-- 在 Ruivo_OnPlayerTurnActivated 中，每次攻击后：
if attacked then
    local kPara = {
        playerID = playerID,
        attackerID = unit:GetID(),
        OnStart = 'restore_1_move'   -- 指定 GP 端事件名
    }
    UI.RequestPlayerOperation(playerID, PlayerOperations.EXECUTE_SCRIPT, kPara)
end
```

### 4.2 GP/UI 端响应

```lua
-- Ruivo_Auto_Range_Attack_GP.lua

-- 每回合每个单位最多触发一次
falseTable = {}

function restore_1_move(playerID, kPara)
    local playerID = kPara.playerID
    local attackerID = kPara.attackerID
    local attackerUnit = UnitManager.GetUnit(playerID, attackerID)

    if falseTable[playerID] == nil then
        falseTable[playerID] = {}
    end

    local currentTurn = Game.GetCurrentGameTurn()
    if falseTable[playerID][attackerID] ~= currentTurn then
        falseTable[playerID][attackerID] = currentTurn
        UnitManager.RestoreUnitAttacks(attackerUnit)            -- 恢复攻击次数
        UnitManager.RestoreMovementToFormation(attackerUnit)    -- 恢复移动力
        UnitManager.ChangeMovesRemaining(attackerUnit, -1)     -- 扣 1 点
    end
end
GameEvents.restore_1_move.Add(restore_1_move)
```

**三步操作的作用**：
1. `RestoreUnitAttacks` — 恢复攻击次数（允许再次攻击）
2. `RestoreMovementToFormation` — 将移动力重置为编队最大值（同时恢复 ZOC 免疫状态）
3. `ChangeMovesRemaining(-1)` — 净扣 1 点移动力

**`falseTable` 防重复**：以 `[playerID][attackerID] = currentTurn` 记录，防止同一回合对同一单位多次触发恢复。

### 4.3 战斗前移动力恢复（手动攻击兼容）

```lua
function OnCombatVisBegin(combatMembers)
    local attacker = combatMembers[0]
    if not attacker then return end

    local player = Players[attacker.playerID]
    if not player or not player:IsHuman() then return end

    local attackerUnit = UnitManager.GetUnit(attacker.playerID, attacker.componentID)
    if not attackerUnit then return end

    UnitManager.RestoreMovementToFormation(attackerUnit)
    UnitManager.ChangeMovesRemaining(attackerUnit, -1)
end
Events.CombatVisBegin.Add(OnCombatVisBegin)
```

**用途**：当玩家手动用远程单位攻击时（而非自动攻击），同样扣 1 移动力。`CombatVisBegin` 在战斗动画开始时触发，时机早于 `CombatVisEnd`，能避免战斗动画完成后的额外移动力恢复。

---

## 五、完整使用模板

### 最小可运行框架

```lua
-- ===========================================================================
-- AutoAttack_Gameplay.lua — 游戏脚本侧
-- ===========================================================================

-- 1. BFS 扫描函数（复制 ruivoGetRingsPlots）
function GetPlotsInRange(iX, iY, maxRing)
    -- ...（同上）
end

-- 2. 主逻辑
function OnPlayerTurnActivated(playerID)
    local pPlayer = Players[playerID]
    if not pPlayer or not pPlayer:IsHuman() then return end

    for _, unit in pPlayer:GetUnits():Members() do
        if unit:GetRange() > 0 then
            local range = unit:GetRange()
            for _, plot in ipairs(GetPlotsInRange(unit:GetX(), unit:GetY(), range)) do
                local tParams = {
                    [UnitOperationTypes.PARAM_X] = plot:GetX(),
                    [UnitOperationTypes.PARAM_Y] = plot:GetY()
                }
                if UnitManager.CanStartOperation(unit, UnitOperationTypes.RANGE_ATTACK, nil, tParams) then
                    UnitManager.RequestOperation(unit, UnitOperationTypes.RANGE_ATTACK, tParams)
                    break  -- 只攻击一次
                end
            end
        end
    end
end
Events.PlayerTurnActivated.Add(OnPlayerTurnActivated)

-- ===========================================================================
-- AutoAttack_GP.lua — UI/GP 脚本侧
-- ===========================================================================
function OnRestoreAfterAutoAttack(playerID, kPara)
    local unit = UnitManager.GetUnit(kPara.playerID, kPara.attackerID)
    if unit then
        UnitManager.RestoreUnitAttacks(unit)
        UnitManager.RestoreMovementToFormation(unit)
        UnitManager.ChangeMovesRemaining(unit, -1)
    end
end
GameEvents.restore_1_move.Add(OnRestoreAfterAutoAttack)
```

### 常见变体

| 需求 | 修改方式 |
|------|---------|
| 只攻击不恢复移动力 | 删除 `UI.RequestPlayerOperation` 和 GP 文件 |
| 对所有玩家（含 AI）自动攻击 | 删除 `not pPlayer:IsHuman()` 条件 |
| 只攻击特定领域单位 | 增加 `GameInfo.Units[unit:GetType()].Domain == "DOMAIN_LAND"` |
| 每回合限制攻击次数 | 在 BFS 循环中计数，达到上限 `break` |
| 排除特定操作类型 | 增加 `CanStartOperation` 的第三个参数 `bTestVisible` 或 `bTestFacing` |

---

## 六、注意事项

1. **线程限制**：`UnitManager.RequestOperation` 只能在 GameplayScript 调用；`UI.RequestPlayerOperation(EXECUTE_SCRIPT)` 是唯一从游戏线程回呼 UI 线程的方式。

2. **异步执行**：`RequestOperation` 不是立即执行的，游戏引擎在下一 tick 处理。因此不能在同一帧内反复请求同一单位的多次攻击。

3. **城市/区域攻击无次数限制**：城市的远程攻击每回合只能进行一次，但 `ProcessAutoAttack` 中的循环会遍历所有可用目标。实际只会命中第一个满足条件的目标（因为攻击后该城市/区域的攻击机会被消耗）。

4. **性能警告**：BFS 在大地图（如射程 6 的火箭炮）上扫描可能涉及大量地块。对于后期大量远程单位，建议增加射程上限检查或跳过特定单位类型。

5. **兼容性**：该 Mod 不修改任何游戏数据库，纯 Lua 实现。与其他战斗类 Mod 兼容（只要不冲突修改移动力恢复逻辑）。
