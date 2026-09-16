# 可展开的多按钮资源消费面板（来源：崩坏仙舟 3172771643）

## 做什么
在城市面板（CityPanel）的 ActionStack 中嵌入一个可展开/收起的资源追踪与消费按钮组。主按钮始终显示，点击后向上展开 2-4 个子按钮，每个子按钮对应一种消费目标（产能/食物/科技/文化），悬停显示详细转换率，左键消费、右键查看产出汇总。适合需要将"一种通用资源转换为多种产出"的领袖机制。

## 涉及文件

| 文件 | 角色 |
|------|------|
| `UI/LuoFu_XianZhou_UI.lua` | 主 UI 逻辑（900+ 行） |
| `UI/LuoFu_XianZhou_UI.xml` | 按钮组布局定义 |
| `Scripts/LuoFu_XianZhou_Gameplay.lua` | GP 端：Property 读写、DivinationPointToXxx 函数 |

## 核心模式

### 1. XML 布局：主按钮 + 可收起子按钮栈

```xml
<Grid ID="XianZhouDivinationGrid" Anchor="R,B" Size="auto,41" ...>
    <!-- 主按钮：始终可见 -->
    <Button ID="XianZhouDivinationButton" Anchor="C,B" Size="44,53" Texture="UnitPanel_ActionButton">
        <Image ID="XianZhouDivinationIcon" Anchor="C,C" Size="45,45" Icon="ICON_ACTION_XIANZHOU_FUXUAN"/>
    </Button>

    <!-- 子按钮容器：默认隐藏，展开时显示 -->
    <Container ID="XianZhouDivinationContainer" Offset="0,0">
        <Stack ID="XianZhouButtonStack" Anchor="L,B" Size="44,260" Padding="-2" StackGrowth="Up">
            <Button ID="XianZhouDivinationProductionButton" Size="44,53">
                <Image Icon="ICON_NOTIFICATION_CHOOSE_CITY_PRODUCTION"/>
            </Button>
            <Button ID="XianZhouDivinationFoodButton" Size="44,53">
                <Image Icon="FOODLARGE"/>
            </Button>
            <Button ID="XianZhouDivinationCultureButton" Size="44,53">
                <Image Icon="ICON_NOTIFICATION_CHOOSE_CIVIC"/>
            </Button>
            <Button ID="XianZhouDivinationScienceButton" Size="44,53">
                <Image Icon="ICON_NOTIFICATION_CHOOSE_TECH"/>
            </Button>
        </Stack>
    </Container>
</Grid>
```

### 2. 挂载到 CityPanel ActionStack

```lua
function XianZhouButtonInitialize()
    local pContext = ContextPtr:LookUpControl("/InGame/CityPanel/ActionStack")
    if pContext ~= nil then
        Controls.XianZhouDivinationGrid:ChangeParent(pContext)

        -- 主按钮：左键展开/收起，右键查看汇总
        Controls.XianZhouDivinationButton:RegisterCallback(
            Mouse.eLClick, OnXianZhouShowAvailableClicked)
        Controls.XianZhouDivinationButton:RegisterCallback(
            Mouse.eRClick, OnXianZhouShowSummaryClicked)

        -- 子按钮：左键确认消费
        Controls.XianZhouDivinationFoodButton:RegisterCallback(
            Mouse.eLClick, DivinationFoodComplete)
        Controls.XianZhouDivinationScienceButton:RegisterCallback(
            Mouse.eLClick, DivinationScienceComplete)
        Controls.XianZhouDivinationCultureButton:RegisterCallback(
            Mouse.eLClick, DivinationCultureComplete)
        Controls.XianZhouDivinationProductionButton:RegisterCallback(
            Mouse.eLClick, DivinationProductionComplete)

        -- 悬停音效
        for _, btn in ipairs({"Food","Science","Culture","Production"}) do
            Controls["XianZhouDivination"..btn.."Button"]:RegisterCallback(
                Mouse.eMouseEnter, function() UI.PlaySound("Main_Menu_Mouse_Over") end)
        end
    end
    -- 注册联动事件
    Events.CitySelectionChanged.Add(OnXianZhouSelectionChanged)
    Events.PlayerTurnActivated.Add(OnTurnBegin)
    Events.CityAddedToMap.Add(RefreshAmenityProperty)
    Events.CityPropertyChanged.Add(OnDivinationLater)
    Events.CityProjectCompleted.Add(XianZhouProjectCompleted)
    Events.ImprovementChanged.Add(OnXianZhouImprovementChanged)
    Events.CityProductionQueueChanged.Add(OnDivinationQueueChanged)
end

Events.LoadGameViewStateDone.Add(XianZhouButtonInitialize)
```

### 3. 展开/收起切换（左键主按钮）

```lua
function OnXianZhouShowAvailableClicked()
    if Controls.XianZhouDivinationContainer:IsHidden() then
        -- 展开：选中主按钮，显示容器，按条件显示各子按钮
        Controls.XianZhouDivinationButton:SetSelected(true)
        Controls.XianZhouDivinationContainer:SetHide(false)

        -- 初始全部隐藏
        Controls.XianZhouDivinationProductionButton:SetHide(true)
        Controls.XianZhouDivinationScienceButton:SetHide(true)
        Controls.XianZhouDivinationCultureButton:SetHide(true)
        Controls.XianZhouDivinationFoodButton:SetHide(true)

        local localPlayer = Players[Game.GetLocalPlayer()]
        if localPlayer:GetProperty('XIANZHOU_ENABLE_MATRIX_OF_PRESCIENCE') > 0 then
            local DivinationPoint = localPlayer:GetProperty('XIANZHOU_DIVINATION_POINT') or 0

            -- 按条件逐个显示子按钮 + 设置详细 Tooltip
            if localPlayer:GetProperty('XIANZHOU_ENABLE_MATRIX_OF_PRESCIENCE_FOR_YIELD_PRODUCTION') > 0 then
                Controls.XianZhouDivinationProductionButton:SetHide(false)
                local ProductionInfo = DivinationCityBuildQueue(iPlayer, pCity:GetID())
                Controls.XianZhouDivinationProductionButton:SetToolTipString(
                    Locale.Lookup('LOC_XIANZHOU_DIVINATION_CITYBUILDQUEUE_INFO',
                        ProductionInfo.Name, ...) ..
                    '[NEWLINE]' .. Locale.Lookup('LOC_XIANZHOU_DIVINATION_POINT_BUTTON_PRODUCTION_TOOLTIP',
                        math.floor(DivinationPoint * (100 - DIVINATION_TO_PRODUCTION) / 10) / 10))
            end
            -- 科技、文化、食物同理 ...
        end
    else
        -- 收起
        Controls.XianZhouDivinationButton:SetSelected(false)
        Controls.XianZhouDivinationContainer:SetHide(true)
    end
end
```

### 4. 汇总模式（右键主按钮）

右键点击时显示各城市产出汇总 Tooltip：

```lua
function OnXianZhouShowSummaryClicked()
    -- 先收起子按钮面板（避免 UI 冲突）
    Controls.XianZhouDivinationButton:SetSelected(true)
    Controls.XianZhouDivinationContainer:SetHide(true)

    local localPlayer = Players[Game.GetLocalPlayer()]
    if localPlayer:GetProperty('XIANZHOU_ENABLE_MATRIX_OF_PRESCIENCE') > 0 then
        local totalDivination = 0
        local DivinationTooltip = ""

        for _, city in localPlayer:GetCities():Members() do
            if city:GetProperty('CITY_ENABLE_MATRIX_OF_PRESCIENCE') > 0 then
                local totalCityDivination = 0
                for YieldType, YieldID in pairs(DivinationYieldType) do
                    local CityDivinationPoint = UpdateCityYieldToDivinationPoint(
                        ePlayer, city:GetID(), city:GetYieldToolTip(YieldID), YieldType)
                    totalCityDivination = totalCityDivination + CityDivinationPoint
                end
                totalDivination = totalDivination + totalCityDivination
                DivinationTooltip = DivinationTooltip ..
                    "[NEWLINE][ICON_Bullet]" .. FormatValuePerTurn(totalCityDivination) ..
                    "[ICON_XIANZHOU_MATRIX_OF_PRESCIENCE]" ..
                    Locale.Lookup("LOC_XIANZHOU_DIVINATION_POINT_FROM_CITY",
                        Locale.Lookup(city:GetName()))
            end
        end
        -- 更新主按钮 Tooltip 为汇总内容
        Controls.XianZhouDivinationButton:SetToolTipString(
            Locale.Lookup("LOC_XIANZHOU_DIVINATION_POINT_SUMMARY") ..
            FormatValuePerTurn(totalDivination) .. DivinationTooltip)
    end
end
```

### 5. 城市选择联动刷新

```lua
function Refresh()
    local pCity = UI.GetHeadSelectedCity()
    if pCity then
        -- 检查城市是否启用该机制
        if pCity:GetProperty('CITY_ENABLE_MATRIX_OF_PRESCIENCE') == nil
            or pCity:GetProperty('CITY_ENABLE_MATRIX_OF_PRESCIENCE') == 0 then
            Controls.XianZhouDivinationGrid:SetHide(true)
        else
            Controls.XianZhouDivinationGrid:SetHide(false)
            -- 收起子按钮状态
            Controls.XianZhouDivinationButton:SetSelected(false)
            Controls.XianZhouDivinationContainer:SetHide(true)

            local pPlayer = Players[pCity:GetOwner()]
            if pPlayer:GetProperty('XIANZHOU_ENABLE_MATRIX_OF_PRESCIENCE') > 0 then
                local DivinationPoint = pPlayer:GetProperty('XIANZHOU_DIVINATION_POINT') or 0
                Controls.XianZhouDivinationButton:SetDisabled(false)
                Controls.XianZhouDivinationButton:SetToolTipString(...)
            else
                Controls.XianZhouDivinationButton:SetDisabled(true)
            end
        end
    end
end

function OnXianZhouSelectionChanged(ownerPlayerID, cityID, i, j, k, isSelected, isEditable)
    if ownerPlayerID ~= Game.GetLocalPlayer() then return end
    if isSelected then Refresh() end
end
```

### 6. 消费到不同类型队列

四种消费目标分别对应不同的游戏系统：

```lua
-- 1. 生产队列（建筑/区域/单位/项目）
function DivinationProductionComplete()
    local currentProductionInfo = DivinationCityBuildQueue(iPlayer, CityID)
    local tParameters = {}
    tParameters.CityID = CityID
    tParameters.Type = currentProductionInfo.Type        -- "Building"/"District"/"Unit"/"Project"
    tParameters.Index = currentProductionInfo.Index
    tParameters.Hash = currentProductionInfo.Hash
    tParameters.Cost = currentProductionInfo.Cost
    tParameters.Progress = currentProductionInfo.Progress
    tParameters.OnStart = 'DivinationPointToProduction'
    UI.RequestPlayerOperation(iPlayer, PlayerOperations.EXECUTE_SCRIPT, tParameters)
    Refresh()
end

-- 2. 科技队列
function DivinationScienceComplete()
    local cost = pPlayerTechs:GetResearchCost(pRTech)
    local progress = pPlayerTechs:GetResearchProgress(pRTech)
    local tParameters = { OnStart = 'DivinationPointToScience', Cost = cost, Progress = progress, ... }
    UI.RequestPlayerOperation(iPlayer, PlayerOperations.EXECUTE_SCRIPT, tParameters)
    Refresh()
end

-- 3. 市政队列
function DivinationCultureComplete()
    -- 同理，OnStart = 'DivinationPointToCulture'
end

-- 4. 食物/成长队列
function DivinationFoodComplete()
    -- 需要使用 GrowthThreshold + CityFood + GrowthModifier
    -- OnStart = 'DivinationPointToFood'
end
```

### 7. 每回合自动积累资源

```lua
function OnTurnBegin(ePlayer, isFirstTimeThisTurn)
    if ePlayer ~= Game.GetLocalPlayer() then return end
    if not isFirstTimeThisTurn then return end

    local player = Players[ePlayer]
    if player:GetProperty('XIANZHOU_ENABLE_MATRIX_OF_PRESCIENCE') then
        local totalDivination = 0
        for _, pCity in player:GetCities():Members() do
            if pCity:GetProperty('CITY_ENABLE_MATRIX_OF_PRESCIENCE') > 0 then
                for YieldType, YieldID in pairs(DivinationYieldType) do
                    -- 解析城市产出 Tooltip，提取精确的产出数值
                    local CityDivinationPoint = UpdateCityYieldToDivinationPoint(
                        ePlayer, pCity:GetID(), pCity:GetYieldToolTip(YieldID), YieldType)
                    totalDivination = totalDivination + CityDivinationPoint
                end
            end
        end
        -- 设置 Player Property
        local tParameters = {}
        tParameters.Propertykey = 'XIANZHOU_DIVINATION_POINT'
        tParameters.PointNum = math.floor(totalDivination * 10 + 0.5) / 10
        tParameters.OnStart = 'XianZhouSetDivinationPoint'
        UI.RequestPlayerOperation(player:GetID(), PlayerOperations.EXECUTE_SCRIPT, tParameters)
    end
end
```

## 巧技：解析产出 Tooltip 获取精确数值

该 Mod 的一个独特技术是通过正则解析城市产出的 Tooltip 文本来计算实际产出（而非使用 `city:GetYield()` 的简单值）：

```lua
function UpdateCityYieldToDivinationPoint(playerID, cityID, tooltip, yieldType)
    local CityBaseYield = 0
    local CityDivinationPoint = 0
    -- 正则匹配产出面板中的各种加成格式
    local modifierPattern = "(%+*%-*%d*%.?%d+)"        -- 固定数值
    local modifierPattern2 = "(%+*%-*%d*)%%"            -- 纯百分比
    local modifierPattern3 = "(%+*%-*%d*)%%%s*%p?(%+*%-*%d*%.?%d+)%p?"  -- 百分比+数值
    local modifierPattern4 = "(%+*%-*%d*)%%（(%+*%-*%d*%.?%d+)）"        -- 全角括号格式

    local newTooltip = string.gsub(tooltip, "%[NEWLINE%]", ";")
    for line in string.gmatch(newTooltip, "([^;]+)") do
        -- 跳过 ICON_Bullet 开头的子项（避免重复计算）
        if string.match(line, "%[ICON_Bullet]") == nil then
            -- 识别纯固定数值加成
            local fromModifierAmountStr = line:match(modifierPattern)
            -- 识别百分比（+百分值）×（数值） 格式
            local _, _, d0 = line:find(modifierPattern2)
            local _, _, d1, d2 = line:find(modifierPattern3)
            -- ... 按类型累加
        end
    end
    return CityDivinationPoint
end
```

虽然不精确，但这一步为 UI 端提供了在没有 C++ API 访问全部产出细节时的近似计算方法。

## 与已有模式的对比

| 已有模式 | 本模式差异 |
|----------|-----------|
| `lua-0033-citypanel-resource-spending.md` | 本模式的子按钮**按条件动态显隐**；**左键消费右键汇总**的双模式；资源**每回合自动从产出累积** |
| `lua-workshop-leader-tracker-production-distribution.md` | 本模式是**单一城市消费**而非多城市分配；消费目标涵盖科技/市政/食物等多种队列 |
| `lua-workshop-economy-dynamic-modifiers.md` | 本模式重点在 UI 交互模式（展开/收起/汇总），而非 Modifier 动态计算 |

## XML 尺寸指南

- 主按钮：44×53（与游戏内置 ActionButton 一致）
- 子按钮栈宽度：44（与主按钮等宽）
- 子按钮栈高度：260（容纳 4 个子按钮，每个约 53 + 少量 padding）
- `StackGrowth="Up"` 使子按钮向上展开

## 来源

工坊 Mod 3172771643（崩坏星穹铁道 仙舟罗浮），`UI/LuoFu_XianZhou_UI.lua`——符玄的"矩阵卜算"系统，将城市产出按比例转换为卜算点，可注入生产/科技/市政/食物队列。

---

## XML 配合

### 用到的 XML 文件

| 来源 Mod | XML 文件路径 | 作用 |
|----------|------------|------|
| 仙舟罗浮 (3172771643) | `UI/LuoFu_XianZhou_UI.xml` | 可展开的多按钮资源消费面板 |

### 控件 ID 对照

| XML 控件 ID | 类型 | Lua 角色 |
|------------|------|---------|
| `XianZhouDivinationGrid` | `Grid` | 根容器，`ChangeParent` 挂载到 CityPanel ActionStack |
| `XianZhouDivinationButton` | `Button` | 主按钮：左键展开/收起，右键查看汇总 |
| `XianZhouDivinationIcon` | `Image` | 主按钮图标 |
| `XianZhouDivinationContainer` | `Container` | 子按钮容器，`SetHide(true/false)` 控制展开/收起 |
| `XianZhouButtonStack` | `Stack` | 子按钮垂直排列栈，`StackGrowth="Up"` 向上展开 |
| `XianZhouDivinationProductionButton` | `Button` | 产能消费子按钮 |
| `XianZhouDivinationFoodButton` | `Button` | 食物消费子按钮 |
| `XianZhouDivinationCultureButton` | `Button` | 市政消费子按钮 |
| `XianZhouDivinationScienceButton` | `Button` | 科技消费子按钮 |

### 完整 XML

```xml
<Context>
    <Grid ID="XianZhouDivinationGrid" Anchor="R,B" Size="auto,41"
          Texture="SelectionPanel_ActionGroupSlot"
          SliceCorner="5,19" SliceSize="1,1" SliceTextureSize="12,41"
          ConsumeMouse="1" Alpha="0.75">
        <Button ID="XianZhouDivinationButton" Anchor="C,B" Size="44,53"
                Texture="UnitPanel_ActionButton">
            <Image ID="XianZhouDivinationIcon" Anchor="C,C" Offset="0,-2"
                   Size="45,45" Icon="ICON_ACTION_XIANZHOU_FUXUAN"/>
        </Button>
        <Container ID="XianZhouDivinationContainer" Offset="0,0">
            <Stack ID="XianZhouButtonStack" Anchor="L,B" Size="44,260"
                   Padding="-2" StackGrowth="Up">
                <!-- 4个子按钮 -->
            </Stack>
        </Container>
    </Grid>
</Context>
```

### 可复用 XML

- **可展开主按钮 + 子按钮组**：主按钮始终可见，子按钮 `Container` 默认隐藏，点击展开/收起
- **上下键分离**：左键消费、右键查看汇总，实现一个按钮两种交互
- **StackGrowth 方向**：`Up` 使子按钮向上展开（适合底部按钮）；`Down` 适合顶部按钮
- 作为 Context Additions 注册到 modinfo
