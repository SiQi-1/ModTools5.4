# 奇观加速充能系统（来源：0031）

## 做什么
特殊建造者单位拥有"奇观加速"充能：每次使用消耗一层充能（ABILITY_SIQI0031_WONDER_BUILD_CHARGE_X），为目标城市正在建造的奇观注入生产力（施工进度）。充能层级从1递增到30，用完30层后单位自动死亡。

注入的产值公式：`buildingInfo.Cost * GameSpeedMultiplier * speedPercent / 10000`，即奇观基础造价乘以游戏速度倍率再乘以百分比（默认10%）。

## 触发方式
UI 通过 `GameEvents.Siqi0031_WonderSpeedUp` 发送参数 `{unitID, cityID, wonderIndex, speedPercent}`。

## 涉及文件和函数

| 文件 | 函数 | 作用 |
|------|------|------|
| `Siqi_Leaders_0031_MiuMiu_Scripts.lua` | `OnWonderSpeedUp(playerID, params)` | 入口，调用核心逻辑 |
| `Siqi_Leaders_0031_MiuMiu_Scripts.lua` | `AddWonderProgress(pCity, wonderIndex, speedPercent)` | 计算并注入奇观进度 |
| `Siqi_Leaders_0031_MiuMiu_Scripts.lua` | `ConsumeOneBuilderCharge(pUnit)` | 消耗充能层级，递增或死亡 |

## 核心代码

```lua
local WONDER_SPEED_PROPERTY_ABILITY_STEP = "SIQI0031_WONDER_SPEED_ABILITY_STEP"
local WONDER_SPEED_ABILITY_PREFIX = "ABILITY_SIQI0031_WONDER_BUILD_CHARGE_"
local WONDER_SPEED_MAX_ABILITY = 30

-- 计算并注入奇观进度
function AddWonderProgress(pCity, wonderIndex, speedPercent)
    local buildingInfo = GameInfo.Buildings[wonderIndex]
    if buildingInfo == nil or buildingInfo.Cost == nil then return false end

    -- 游戏速度倍率（固定写法，nil 安全）
    local GAME_SPEED = GameConfiguration.GetGameSpeedType()
    local GAME_SPEED_MULTIPLIER = GameInfo.GameSpeeds[GAME_SPEED] and GameInfo.GameSpeeds[GAME_SPEED].CostMultiplier / 100 or 1
    local percent = speedPercent or 10  -- 默认10%
    if percent <= 0 then return false end

    -- 公式：奇观造价 * 速度倍率 * 百分比 / 10000
    local amount = buildingInfo.Cost * GAME_SPEED_MULTIPLIER * percent / 10000
    pCity:GetBuildQueue():AddProgress(amount)
    return true
end

-- 消耗充能层级
function ConsumeOneBuilderCharge(pUnit)
    local step = pUnit:GetProperty(WONDER_SPEED_PROPERTY_ABILITY_STEP)
    if step == nil then step = 1
    else
        -- 移除当前层级的能力
        unitAbility:ChangeAbilityCount(WONDER_SPEED_ABILITY_PREFIX .. tostring(step), -1)
        step = step + 1
    end

    if step > WONDER_SPEED_MAX_ABILITY then
        UnitManager.Kill(pUnit)  -- 30层用尽，单位死亡
        return
    end

    -- 设置新层级并赋予对应能力
    pUnit:SetProperty(WONDER_SPEED_PROPERTY_ABILITY_STEP, step)
    unitAbility:ChangeAbilityCount(WONDER_SPEED_ABILITY_PREFIX .. tostring(step), 1)
    UnitManager.FinishMoves(pUnit)
end

-- 入口函数
function OnWonderSpeedUp(playerID, params)
    local pUnit = UnitManager.GetUnit(playerID, params.unitID)
    local pCity = CityManager.GetCity(playerID, params.cityID)

    local ok = AddWonderProgress(pCity, params.wonderIndex, params.speedPercent)
    if not ok then return end

    ConsumeOneBuilderCharge(pUnit)
end
```

## 关键设计要点

1. **层级递增机制**：充能不是简单的数字加减，而是通过30个独立的 Ability（`ABILITY_SIQI0031_WONDER_BUILD_CHARGE_1` ~~ `_30`）实现，每层是一个独立的 SQL Modifier，可以给每层配置不同的视觉效果或数值加成
2. **Property 追踪**：用 `WONDER_SPEED_PROPERTY_ABILITY_STEP` 属性记录当前层级，用于判断下次激活哪个 Ability
3. **游戏速度适配**：`CostMultiplier` 确保在不同游戏速度（标准/快速/马拉松）下，注入的绝对锤数比例一致
4. **单位有限生命**：`WONDER_SPEED_MAX_ABILITY = 30`，用尽后单位死亡（`UnitManager.Kill`），形成消耗品设计
5. **Action 经济**：每次使用消耗一次移动（`UnitManager.FinishMoves`），属于标准行动消耗
6. **安全守卫**：`AddWonderProgress` 返回 false 时（奇观不存在/百分比无效），不消耗充能
