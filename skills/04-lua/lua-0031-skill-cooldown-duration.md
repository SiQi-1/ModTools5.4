# 技能冷却与持续时间管理（来源：0031）

## 做什么
为特殊单位技能提供通用的冷却时间（cooldown）和效果持续时间（duration）管理。使用 Unit Properties 存储 `LastUsedTurn` 和 `ExpireTurn`，通过 `PlayerTurnActivated` 事件每回合检查并清理过期能力。

## 适用场景
- 主动技能有冷却限制，使用后 N 回合内不可再次使用
- Buff/Debuff 能力有持续时间，到期后自动移除

## 涉及文件和函数

| 文件 | 函数 | 作用 |
|------|------|------|
| `Siqi_Leaders_0031_MiuMiu_Scripts.lua` | `IsSkillS1CooldownReady(pUnit, currentTurn, cooldownTurns)` | 检查冷却是否就绪 |
| `Siqi_Leaders_0031_MiuMiu_Scripts.lua` | `ActivateSkillS1(playerID, params)` | 激活技能（设置属性和能力计数） |
| `Siqi_Leaders_0031_MiuMiu_Scripts.lua` | `OnTurnBeginRemoveExpiredS1(playerID, bfristTime)` | 每回合开始移除过期能力 |
| Event | `GameEvents.Siqi0031_U0031_1_S1_Activate` | UI 触发技能激活 |
| Event | `Events.PlayerTurnActivated` | 每回合检查过期 |

## 核心代码

```lua
-- 属性定义
local SKILL_S1_ABILITY = "ABILITY_UNIT_SIQI_U0031_1_S1"
local SKILL_S1_PROPERTY_LAST_USED_TURN = "SIQI0031_U0031_1_S1_LAST_USED_TURN"
local SKILL_S1_PROPERTY_EXPIRE_TURN = "SIQI0031_U0031_1_S1_EXPIRE_TURN"
local SKILL_S1_DEFAULT_DURATION = 3    -- 持续3回合
local SKILL_S1_DEFAULT_COOLDOWN = 6    -- 冷却6回合

-- 冷却检查
local function IsSkillS1CooldownReady(pUnit, currentTurn, cooldownTurns)
    local lastTurn = pUnit:GetProperty(SKILL_S1_PROPERTY_LAST_USED_TURN)
    if lastTurn == nil then return true end  -- 从未使用，就绪
    local cd = cooldownTurns or SKILL_S1_DEFAULT_COOLDOWN
    return (currentTurn - lastTurn) >= cd
end

-- 激活技能（由 UI/GameEvents 调用）
local function ActivateSkillS1(playerID, params)
    local pUnit = UnitManager.GetUnit(playerID, params.unitID)
    -- 类型检查
    if unitInfo.UnitType ~= ALLOW_UNIT_TYPE then return end
    -- 冷却检查
    if not IsSkillS1CooldownReady(pUnit, currentTurn, cooldownTurns) then return end

    -- 添加能力(Ability)（提供数值效果）
    unitAbility:ChangeAbilityCount(SKILL_S1_ABILITY, 1)

    -- 记录使用回合和过期回合
    pUnit:SetProperty(SKILL_S1_PROPERTY_LAST_USED_TURN, currentTurn)
    pUnit:SetProperty(SKILL_S1_PROPERTY_EXPIRE_TURN, currentTurn + durationTurns)

    UnitManager.FinishMoves(pUnit)
end

-- 每回合清理过期能力
local function OnTurnBeginRemoveExpiredS1(playerID, bfristTime)
    if not bfristTime then return end  -- 只处理一次（首回合）
    for _, pUnit in pPlayer:GetUnits():Members() do
        if unitInfo.UnitType == ALLOW_UNIT_TYPE then
            local expireTurn = pUnit:GetProperty(SKILL_S1_PROPERTY_EXPIRE_TURN)
            if expireTurn ~= nil and currentTurn >= expireTurn then
                -- 移除能力
                if unitAbility:GetAbilityCount(SKILL_S1_ABILITY) > 0 then
                    unitAbility:ChangeAbilityCount(SKILL_S1_ABILITY, -1)
                end
                pUnit:SetProperty(SKILL_S1_PROPERTY_EXPIRE_TURN, nil)
            end
        end
    end
end
```

## 关键设计要点

1. **双 Property 追踪**：`LAST_USED_TURN` 追踪冷却（决定何时可再用），`EXPIRE_TURN` 追踪到期（决定何时移除效果）
2. **Ability + Property 配合**：Ability（SQL 定义的 Modifier 载体）提供实际数值效果，Property 管理时间状态
3. **bfristTime 守卫**：`PlayerTurnActivated` 对每个玩家触发，`bfristTime` 确保逻辑只执行一次而非每玩家重复
4. **参数化**：duration 和 cooldown 通过 `params` 传入，同一框架可支持多个技能复用
5. **FinishMoves**：激活技能后立即结束单位行动，防止同一回合内做额外操作
