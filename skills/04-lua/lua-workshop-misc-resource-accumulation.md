# 资源积累与触发系统 (Resource Accumulation & Trigger)

## 来源
- Celebrations (Nwflower, id=3492136529) — 幸福值积累 -> 庆典触发

## 概述
实现"自定义资源每回合积累 -> 到达阈值触发事件 -> 玩家选择 -> 消耗资源"的完整系统。以庆典幸福值为范例，可移植到任意"点数积累"机制。

## XML 配合

### CelebrationsTracker.xml — 顶部面板幸福值追踪器

`UI/CelebrationsTracker.xml` 在游戏顶部面板（`/InGame/TopPanel/InfoStack`）中挂入幸福值追踪器：

```xml
<Context Name="CelebrationsTracker">
    <Container ID="CelebrationsTrackerGrid">
        <Image Texture="TopBar_YieldBacking.dds" Size="auto,24"/>
        <GridButton ID="CelebrationsTrackerHappiness" Size="auto,24"
                    Style="YieldBacking" Color="24,156,216,255">
            <Stack ID="YieldButtonStack" StackGrowth="Right">
                <Label ID="HappinessIconString"
                       String="[ICON_CelebrationHappinessLarge]"/>
                <Label ID="HappinessBalance" Style="FontNormal18" String="?"/>
                <Label ID="HappinessPerTurn" Style="FontNormal14" String="0"/>
            </Stack>
        </GridButton>
    </Container>
</Context>
```

显示：当前幸福值 / 触发阈值、每回合增长量。Lua 端通过 `ContextPtr:LookUpControl("/InGame/TopPanel/InfoStack")` 挂入父控件，`AddChildAtIndex(..., 1)` 放在最前。

### Celebration_Panel.xml — 庆典选择弹窗

`UI/Celebration_Panel.xml` 定义了庆典触发时的选择弹窗（借鉴黄金时代面板风格）：
- 容器 702x748，使用 `Ages_ParchmentNormal` 纹理
- 标题（`Title`）+ 副标题（`AgeAchieved`）
- 滚动选择列表（`CommemorationsStack`），每个选项包含图标（`CommemorationIcon`）、类别名（`MomentCategory`）、效果描述（`MomentBonuses`）
- 确认按钮（`Confirm`，初始 Disabled，选择后启用）

弹窗在幸福值达到阈值时触发，显示 4 个加权随机选项供玩家选择。

### Celebration_Config.xml — 配置面板

`Database/Celebration_Config.xml` 注册 GameConfig 参数（如庆典难度、持续回合数等），供 `MapConfiguration.GetValue()` 读取。

### Celebrations_Icon.xml — 图标资源

---

## 核心公式

### 点数产出
```lua
-- 幸福值 = 正宜居度 * 1.0 + 满额忠诚时溢出忠诚 * 0.05
function GetCityPointsPoint(playerID, cityID)
    local pCity = CityManager.GetCity(playerID, cityID)
    -- 正宜居度部分
    local totalAmen = pCity:GetGrowth():GetAmenities()
    local needAmen = math.floor((pCity:GetPopulation() + 1) / 2)
    local freeAmen = GameInfo.GlobalParameters['CITY_AMENITIES_FOR_FREE'].Value or 0
    local excessAmen = math.max(0, totalAmen - needAmen + freeAmen)

    -- 忠诚度溢出部分
    local loyalty = pCity:GetCulturalIdentity():GetLoyalty()
    local maxLoyalty = pCity:GetCulturalIdentity():GetMaxLoyalty()
    local loyaltyPerTurn = pCity:GetCulturalIdentity():GetLoyaltyPerTurn()
    local excessLoyalty = (loyalty == maxLoyalty) and loyaltyPerTurn or 0

    return excessAmen * AMEN_RATIO + excessLoyalty * LOYALTY_RATIO
end

-- 每回合汇总所有城市
function GetPerTurnPoints(playerID)
    local total = 0
    for _, city in Players[playerID]:GetCities():Members() do
        total = total + GetCityPointsPoint(playerID, city:GetID())
    end
    return total
end
```

### 触发阈值（指数增长）
```lua
function GetPointsTrigger(playerID)
    local times = GetTimes(playerID)  -- 已触发次数
    local trigger = (10 * FREQ + times * 35 * FREQ_MULTI)
                  * math.exp(0.06 * FREQ * times * FREQ_MULTI)
    return ModifyBySpeed(trigger)  -- 按游戏速度缩放
end
```

阈值设计要点：
- 初始阈值低（容易触发第一次）
- 后续指数增长（避免过于频繁）
- 乘以游戏速度 `CostMultiplier / 100` 保证一致性

## 步骤 1：自定义属性存储 (SQL)

不需要 SQL 表，直接用 `Player:SetProperty` / `GetProperty`：

```lua
local KEY_POINTS = 'YourSystemPoints'
local KEY_TIMES = 'YourSystemTimes'
local KEY_LAST_TRIGGER_TURN = 'YourSystemLastTurn'

-- 设置点数（Gameplay端）
function SetPoints(playerID, value)
    Players[playerID]:SetProperty(KEY_POINTS, value)
end

-- 读取点数（UI端也用）
function GetPoints(playerID)
    return Players[playerID]:GetProperty(KEY_POINTS) or 0
end
```

## 步骤 2：每回合积累点数 (Gameplay)

```lua
function OnPlayerTurnActivated(playerID, isFirst)
    if not isFirst then return end  -- 只在第一回合开始时积累

    local pPlayer = Players[playerID]
    local perTurn = GetPerTurnPoints(playerID)

    -- 累加点数
    local current = pPlayer:GetProperty(KEY_POINTS) or 0
    pPlayer:SetProperty(KEY_POINTS, current + perTurn)

    -- 检查是否触发
    local trigger = GetPointsTrigger(playerID)
    if (current + perTurn) >= trigger and pPlayer:IsHuman() then
        -- 发送通知给 UI 端
        SendTriggerNotification(playerID)
    end
end
Events.PlayerTurnActivated.Add(OnPlayerTurnActivated)
```

## 步骤 3：触发事件消耗点数 (Gameplay)

```lua
-- UI 端调用 PlayerOperations 后执行
function OnTriggerSelected(playerID, params)
    local pPlayer = Players[playerID]
    local trigger = GetPointsTrigger(playerID)
    local current = GetPoints(playerID)

    -- 消耗点数（触发阈值）
    pPlayer:SetProperty(KEY_POINTS, math.max(0, current - trigger))

    -- 增加触发次数
    local times = (pPlayer:GetProperty(KEY_TIMES) or 0) + 1
    pPlayer:SetProperty(KEY_TIMES, times)

    -- 记录触发回合
    pPlayer:SetProperty(KEY_LAST_TRIGGER_TURN, Game.GetCurrentGameTurn())

    -- 广播给其他脚本（跨 Mod 兼容）
    LuaEvents.YourSystem_Triggered(playerID, params.ChoiceType)
end

GameEvents.YourTriggerHandler.Add(OnTriggerSelected)
```

## 步骤 4：UI 端每回合显示 (Tracker)

在 TopPanel 中插入显示面板：

```lua
function TrackerInit()
    local parent = ContextPtr:LookUpControl("/InGame/TopPanel/InfoStack")
    if parent then
        Controls.YourTrackerGrid:ChangeParent(parent)
        parent:AddChildAtIndex(Controls.YourTrackerGrid, 1)
        parent:CalculateSize()
    end
end

function TrackerRefresh()
    local point = GetPoints(localPlayerID)
    local pointMax = GetPointsTrigger(localPlayerID)
    Controls.YourBalance:SetText(tostring(point) .. '/' .. tostring(pointMax))
    Controls.YourPerTurn:SetText(GetPerTurnPoints(localPlayerID))
end

Events.LoadGameViewStateDone.Add(TrackerInit)
Events.PlayerTurnActivated.Add(function(playerID) TrackerRefresh() end)
```

## 步骤 5：加权随机选择

庆典系统使用加权随机从候选列表中选出 4 个选项：

```lua
function WeightedRandomSelection(selection_tmp, num)
    if #selection_tmp == 0 then return {} end
    if #selection_tmp < num then return selection_tmp end

    local totalWeight = 0
    local available = {}
    for _, item in ipairs(selection_tmp) do
        local weight = item.Weight or 1
        if weight > 0 then
            available[item] = true
            totalWeight = totalWeight + weight
        end
    end

    local selection = {}
    for i = 1, num do
        local randomPoint = Game.GetRandNum(totalWeight)
        local cumulative = 0
        local chosen = nil
        for item, isAvail in pairs(available) do
            if isAvail then
                cumulative = cumulative + (item.Weight or 1)
                if cumulative > randomPoint then
                    chosen = item; break
                end
            end
        end
        if chosen then
            table.insert(selection, chosen)
            available[chosen] = false
            totalWeight = totalWeight - (chosen.Weight or 1)
        end
    end
    return selection
end
```

## 步骤 6：时代感知筛选

```lua
function GetAvailableOptions(playerID)
    local currentEra = Game.GetEras():GetCurrentEra()
    local result = {}
    for row in GameInfo.YourOptions() do
        -- 最早出现时代检查
        local preEraOK = GameInfo.Eras[row.PreEra].Index <= currentEra
        -- 过时时代检查
        local obsoleteEraOK = not row.ObsoleteEra
                           or GameInfo.Eras[row.ObsoleteEra].Index > currentEra
        -- 解锁条件检查
        local unlockOK = true
        if row.UnlocksFromEffect == 1 then
            unlockOK = Players[playerID]:GetProperty('Property_' .. row.OptionType) ~= nil
        end

        if preEraOK and obsoleteEraOK and unlockOK then
            table.insert(result, row)
        end
    end
    return result
end
```

## 要点总结

1. **持久化**：全部用 `Player:SetProperty` / `GetProperty`，自动同步到存档
2. **阈值指数增长**：防止后期过于频繁触发
3. **游戏速度修正**：`num * gameSpeed.CostMultiplier / 100`
4. **跨 Mod 广播**：用 `LuaEvents` 而非 GameEvents，让其他 Mod 可监听
5. **时代限制**：用 `PreEra` / `ObsoleteEra` 控制选项纪元
6. **解锁条件**：用 `PlayerProperty` 作为效果解锁标记
