# 溅射伤害战斗系统（来源：0031）

## 做什么
特定单位（UNIT_SIQI_U0031_2）在攻击后，对攻击目标周围相邻6格内的所有敌方单位造成60%溅射伤害，对相邻敌方城市造成城区守军伤害。判定方式基于攻击者与目标的相对位置（单位/区域/城市）。

## 触发条件
- 攻击者单位类型为 `UNIT_SIQI_U0031_2`（通过 `GameInfo.Units["UNIT_SIQI_U0031_2"].Index` 判断）
- 事件：`Events.Combat`（任意战斗完成）

## 涉及文件和函数

| 文件 | 函数 | 作用 |
|------|------|------|
| `Siqi_Leaders_0031_MiuMiu_Scripts.lua` | `SiqiOnCombat(pCombatResult)` | 战斗事件入口，判断单位类型并触发溅射 |
| `Siqi_Leaders_0031_MiuMiu_Scripts.lua` | `Siqi_FindUnitEnemy(playerID, iX, iY)` | 寻找目标单元格相邻6格内所有敌方单位 |
| `Siqi_Leaders_0031_MiuMiu_Scripts.lua` | `Siqi_FindCityEnemy(playerID, iX, iY)` | 寻找目标单元格相邻6格内敌方市中心 |
| `Siqi_Leaders_0031_MiuMiu_Scripts.lua` | `Siqi_AttachUnitDamage(pUnit, damage)` | 对单位造成伤害（可致死） |

## 核心代码

```lua
function SiqiOnCombat(pCombatResult)
    local attacker = pCombatResult[CombatResultParameters.ATTACKER]
    local attInfo = attacker[CombatResultParameters.ID]
    local attUnit = UnitManager.GetUnit(attInfo.player, attInfo.id)
    local defender = pCombatResult[CombatResultParameters.DEFENDER]
    local defInfo = defender[CombatResultParameters.ID]
    local defUnit = UnitManager.GetUnit(defInfo.player, defInfo.id)

    local INDEX_2 = GameInfo.Units["UNIT_SIQI_U0031_2"].Index

    -- 检查攻击者是否为目标单位类型
    if attUnit and attUnit:GetType() == INDEX_2 then
        -- 获取攻击者造成的实际伤害
        local attdamage = defender[CombatResultParameters.DAMAGE_TO] or 0

        -- 溅射伤害 = 原始伤害的60%
        local d = math.floor(attdamage * 0.6)

        -- 确定溅射中心坐标：
        -- 防御目标是单位 → 用防御单位的坐标
        -- 防御目标是区域 → 用区域的坐标
        local location = {x = attUnit:GetX(), y = attUnit:GetY()}
        if defInfo.type == 1 then  -- 单位
            location = {x = defUnit:GetX(), y = defUnit:GetY()}
        elseif defInfo.type == 3 then  -- 区域
            local pDistrict = CityManager.GetDistrict(defInfo.player, defInfo.id)
            location = {x = pDistrict:GetX(), y = pDistrict:GetY()}
        end

        -- 对相邻敌方单位造成溅射伤害
        local Unitlist = Siqi_FindUnitEnemy(attInfo.player, location.x, location.y)
        for i = 1, #Unitlist do
            Siqi_AttachUnitDamage(Unitlist[i], d)
        end

        -- 对相邻敌方城市造成溅射伤害
        local pCity = Siqi_FindCityEnemy(attInfo.player, location.x, location.y)
        if pCity ~= nil then
            local pCityDistrict = pCity:GetDistricts():GetDistrict(
                GameInfo.Districts['DISTRICT_CITY_CENTER'].Index)
            pCityDistrict:ChangeDamage(DefenseTypes.DISTRICT_GARRISON, d)
        end
    end
end

-- 寻找相邻6格敌方单位
function Siqi_FindUnitEnemy(playerID, iX, iY)
    local unittable = {}
    for iDirection = 0, 5 do
        local pPlot = Map.GetAdjacentPlot(iX, iY, iDirection)
        for loop, unit in ipairs(Units.GetUnitsInPlot(pPlot)) do
            if pPlayer:GetDiplomacy():IsAtWarWith(unit:GetOwner()) then
                table.insert(unittable, unit)
            end
        end
    end
    return unittable
end

-- 造成伤害（溢血致死）
function Siqi_AttachUnitDamage(pUnit, damage)
    local MaxDamage = pUnit:GetProperty('MaxHitPoints') or 100
    local unitdamage = pUnit:GetDamage()
    if unitdamage + damage >= MaxDamage then
        UnitManager.Kill(pUnit, true)
    else
        pUnit:ChangeDamage(damage)
    end
end
```

## 关键设计要点

1. **以目标为中心**：溅射中心不是攻击者位置，而是防御目标的位置（`defInfo.type` 区分单位/区域/城市），更符合"命中点爆炸"逻辑
2. **比例溅射**：伤害基于实际造成的伤害（`DAMAGE_TO`）的60%，而非战斗力差值，高伤害攻击产生更高的溅射
3. **双目标体系**：同时处理单位和城市两种目标，用两套独立的查找函数
4. **兼容 MaxHitPoints**：`Siqi_AttachUnitDamage` 使用 `GetProperty('MaxHitPoints')` 而非硬编码100，兼容其他 Mod 修改血量上限
5. **adjacent 遍历**：用 `for iDirection = 0, 5` + `Map.GetAdjacentPlot` 遍历6个邻格，而非 `GetNeighborPlots`（后者可能包含更多格）
6. **市中心直接伤害**：对城市溅射直接打守军血量(`DISTRICT_GARRISON`)，跳过外墙
