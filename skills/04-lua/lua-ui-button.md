# lua-ui-button — UI 按钮模版

从 Siqi Mod 全部工程中提炼的城市面板 / 单位面板按钮实现模式。

---

## 快速索引

| 模式 | 父容器路径 | 适用场景 |
|------|-----------|---------|
| 城市面板按钮（简单） | `/InGame/CityPanel/ActionStack` | 点击即执行 |
| 城市面板 CheckBox | `/InGame/CityPanel/ActionStack` | 切换 Lens 层 |
| 城市面板按钮 + 选地格 | `/InGame/CityPanel/ActionStack` | 点按钮→选地格→执行 |
| 单位面板按钮（简单） | `/InGame/UnitPanel/StandardActionsStack` | 点击即执行 |
| 单位面板按钮 + 选地格 | `/InGame/UnitPanel/StandardActionsStack` | 点按钮→高亮→选格→执行 |

---

## 一、城市面板按钮

### 1.1 完整模版（简单动作按钮）

```lua
-- ===========================================================================
-- CityPanel 按钮 — 简单动作型（点击即执行）
-- 父容器: /InGame/CityPanel/ActionStack
-- ===========================================================================

-- Init: 查找父控件 → ChangeParent → RegisterCallback
function Init()
    local pContext = ContextPtr:LookUpControl("/InGame/CityPanel/ActionStack")
    if pContext ~= nil then
        Controls.MyCityButtonGrid:ChangeParent(pContext)
        Controls.MyCityButton:RegisterCallback(Mouse.eLClick, OnMyCityButtonClicked)
        Controls.MyCityButton:RegisterCallback(Mouse.eMouseEnter, function()
            UI.PlaySound("Main_Menu_Mouse_Over")
        end)
    end
end

-- 隐藏按钮
function Close()
    Controls.MyCityButtonGrid:SetHide(true)
end

-- Refresh: 判断城市是否选中、条件是否满足、按钮是否可用
function Refresh()
    local pCity = UI.GetHeadSelectedCity()
    if not pCity then Close(); return end

    -- [可选] 领袖/文明判���
    if not MyCondition_PlayerHasTrait(pCity:GetOwner()) then Close(); return end

    local playerID = Game.GetLocalPlayer()
    local CanUse, tooltip = MyCondition_CanUseAbility(Players[playerID], pCity)

    Controls.MyCityButtonGrid:SetHide(false)
    Controls.MyCityButton:SetDisabled(not CanUse)
    Controls.MyCityButton:SetToolTipString(tooltip)
end

-- OnClick: 打包参数 → UI.RequestPlayerOperation
function OnMyCityButtonClicked()
    local pCity = UI.GetHeadSelectedCity()
    if not pCity then return end

    local params = {
        OnStart = "MyMod_CityButtonAction",   -- GP 端 GameEvents 名称
        CityID  = pCity:GetID(),
        -- [自定义参数] ...
    }
    UI.RequestPlayerOperation(Game.GetLocalPlayer(), PlayerOperations.EXECUTE_SCRIPT, params)
    Refresh()
end

-- 城市选择变化时刷新
function OnCitySelectionChanged(ownerPlayerID, cityID, i, j, k, isSelected)
    if ownerPlayerID ~= Game.GetLocalPlayer() then return end
    if isSelected then Refresh() end
end

function Initialize()
    Init()
    Events.CitySelectionChanged.Add(OnCitySelectionChanged)
    Events.PlayerTurnActivated.Add(Refresh)
    Events.CityProductionChanged.Add(Refresh)
    -- [可选] Events.DistrictBuildProgressChanged.Add(Refresh)
    -- [可选] Events.CityWorkerChanged.Add(Refresh)
    -- [可选] Events.GamePropertyChanged.Add(Refresh)
end
Events.LoadGameViewStateDone.Add(Initialize)
```

### 1.2 变体：CheckBox 开关按钮（切换 Lens 层）

用于信仰买地、相邻加成高亮等切换镜头状态的场景。注意用 `RegisterCheckHandler` 而非 `RegisterCallback`。

```lua
local m_MyLensLayer = UILens.CreateLensLayerHash("MyMod_LensLayer")

function Refresh()
    local pCity = UI.GetHeadSelectedCity()
    if not pCity then return end
    if pCity:GetOwner() ~= Game.GetLocalPlayer() then return end
    if not MyCondition_PlayerHasTrait(pCity:GetOwner()) then
        Controls.MyCityCheckGrid:SetHide(true); return
    end
    Controls.MyCityCheckGrid:SetHide(false)
    Controls.MyCityCheck:SetSelected(false)
    Controls.MyCityCheck:SetDisabled(false)
    Controls.MyCityCheck:SetToolTipString(Locale.Lookup("LOC_MY_TOOLTIP"))
end

function OnMyCityCheckChecked()
    if Controls.MyCityCheck:IsChecked() then
        RecenterCameraOnCity()
        UILens.ToggleLayerOn(m_MyLensLayer)
    else
        UILens.ToggleLayerOff(m_MyLensLayer)
    end
end

function RecenterCameraOnCity()
    local kCity = UI.GetHeadSelectedCity()
    if kCity then UI.LookAtPlot(kCity:GetX(), kCity:GetY()) end
end

function Init()
    local pContext = ContextPtr:LookUpControl("/InGame/CityPanel/ActionStack")
    if pContext ~= nil then
        Controls.MyCityCheckGrid:ChangeParent(pContext)
        -- CheckBox 用 RegisterCheckHandler，普通按钮用 RegisterCallback
        Controls.MyCityCheck:RegisterCheckHandler(OnMyCityCheckChecked)
        Controls.MyCityCheck:RegisterCallback(Mouse.eMouseEnter, function()
            UI.PlaySound("Main_Menu_Mouse_Over")
        end)
    end
end

function Initialize()
    Init()
    Events.CitySelectionChanged.Add(function(ownerPlayerID, cityID, i, j, k, isSelected)
        if ownerPlayerID ~= Game.GetLocalPlayer() then return end
        if isSelected then Refresh() end
    end)
    Events.PlayerTurnActivated.Add(Refresh)
end
Events.LoadGameViewStateDone.Add(Initialize)
```

### 1.3 变体：城市面板按钮 + 选地格模式

点按钮 → 高亮可选地格 → 点格子执行 → 退出模式。

```lua
local m_IsInWBInterfaceMode = false
local m_Plots = nil               -- { [plotIndex] = 1 }
local g_HexColoring = UILens.CreateLensLayerHash("MyMod_HexColoring")

function Init()
    local pContext = ContextPtr:LookUpControl("/InGame/CityPanel/ActionStack")
    if pContext ~= nil then
        Controls.MyCityButtonGrid:ChangeParent(pContext)
        Controls.MyCityButton:RegisterCallback(Mouse.eLClick, OnButtonClicked)
        Controls.MyCityButton:RegisterCallback(Mouse.eMouseEnter, function()
            UI.PlaySound("Main_Menu_Mouse_Over")
        end)
    end
end

function Refresh()
    local pCity = UI.GetHeadSelectedCity()
    if not pCity then QuitSelectMode(true); return end
    local Disabled, Tooltip = IsButtonDisabled()
    Controls.MyCityButtonGrid:SetHide(false)
    Controls.MyCityButton:SetDisabled(Disabled)
    Controls.MyCityButton:SetToolTipString(Tooltip)
end

function IsButtonDisabled()
    local pCity = UI.GetHeadSelectedCity()
    if not pCity then return true, "" end
    local plots = GetValidPlots(pCity)
    m_Plots = MakeHash(plots)
    if #plots == 0 then
        return true, SiqiUI.Red(Locale.Lookup("LOC_MY_NO_VALID_PLOTS"))
    else
        return false, Locale.Lookup("LOC_MY_BUTTON_READY")
    end
end

-- 进入选地格模式
function OnButtonClicked()
    if m_IsInWBInterfaceMode then QuitSelectMode(true); return end
    UI.SetInterfaceMode(InterfaceModeTypes.SELECTION)
    UI.SetInterfaceMode(InterfaceModeTypes.WB_SELECT_PLOT)
    m_IsInWBInterfaceMode = true
    Controls.MyCityButton:SetSelected(true)
    local plots = GetValidPlots(UI.GetHeadSelectedCity())
    if #plots > 0 then
        UILens.ToggleLayerOn(g_HexColoring)
        UILens.SetLayerHexesArea(g_HexColoring, Game.GetLocalPlayer(), plots)
    end
end

-- 选地格回调
function OnPlotClicked(plotID)
    local pCity = UI.GetHeadSelectedCity()
    if not pCity or not m_Plots[plotID] then return end
    local pPlot = Map.GetPlotByIndex(plotID)
    local params = {
        OnStart = "MyMod_PlotAction",
        X = pPlot:GetX(), Y = pPlot:GetY(), CityID = pCity:GetID(),
    }
    UI.RequestPlayerOperation(Game.GetLocalPlayer(), PlayerOperations.EXECUTE_SCRIPT, params)
    QuitSelectMode(true); m_Plots = {}; Refresh()
end

-- 退出选地格模式
function QuitSelectMode(ifChangeInterfaceMode)
    if m_IsInWBInterfaceMode and ifChangeInterfaceMode then
        UI.SetInterfaceMode(InterfaceModeTypes.SELECTION)
    end
    UILens.ClearLayerHexes(g_HexColoring)
    UILens.ToggleLayerOff(g_HexColoring)
    m_IsInWBInterfaceMode = false
    Controls.MyCityButton:SetSelected(false)
end

function GetValidPlots(pCity)
    local plots = {}
    local kplots = Map.GetCityPlots():GetPurchasedPlots(pCity)
    for _, plotID in ipairs(kplots) do
        local kPlot = Map.GetPlotByIndex(plotID)
        if kPlot:GetYield(YieldTypes.CULTURE) > 0 then    -- [自定义筛选]
            table.insert(plots, plotID)
        end
    end
    return plots
end

function MakeHash(plots)
    local hash = {}
    for _, id in ipairs(plots) do hash[id] = 1 end
    return hash
end

function Initialize()
    Init()
    Events.CitySelectionChanged.Add(function(playerID, cityID, i, j, k, isSelected)
        if playerID ~= Game.GetLocalPlayer() then return end
        if isSelected then Refresh() else if m_IsInWBInterfaceMode then QuitSelectMode(false) end end
    end)
    Events.PlayerTurnActivated.Add(function(playerID, bIsFirstTime)
        if not bIsFirstTime then return end
        if playerID ~= Game.GetLocalPlayer() then return end
        local pCity = UI.GetHeadSelectedCity(); if pCity then Refresh() end
    end)
    LuaEvents.WorldInput_WBSelectPlot.Add(function(plotId, plotEdge, boolDown, rButton)
        if not boolDown then
            if rButton then QuitSelectMode(true) else OnPlotClicked(plotId) end
        end
    end)
end
Events.LoadGameViewStateDone.Add(Initialize)
```

---

## 二、单位面板按钮

### 2.1 完整模版（简单动作按钮）

```lua
-- ===========================================================================
-- UnitPanel 按钮 — 简单动作型（点击即执行）
-- 父容器: /InGame/UnitPanel/StandardActionsStack
-- ===========================================================================

local AllowUnits = {}
AllowUnits['UNIT_BUILDER'] = true    -- 示例

function Init()
    local pContext = ContextPtr:LookUpControl("/InGame/UnitPanel/StandardActionsStack")
    if pContext ~= nil then
        Controls.MyUnitButtonGrid:ChangeParent(pContext)
        Controls.MyUnitButton:RegisterCallback(Mouse.eLClick, OnButtonClicked)
    end
end

-- 标准 Refresh 三连：Hide → Disabled → Tooltip
function Refresh()
    local pUnit = UI.GetHeadSelectedUnit()
    if pUnit == nil then return end
    if IsButtonHide(pUnit) then
        Controls.MyUnitButtonGrid:SetHide(true)
    else
        Controls.MyUnitButtonGrid:SetHide(false)
        local disabled, str = IsButtonDisabled(pUnit)
        Controls.MyUnitButton:SetDisabled(disabled)
        Controls.MyUnitButton:SetToolTipString(str)
    end
end

-- IsButtonHide: 返回 true = 不显示按钮
function IsButtonHide(pUnit)
    if not pUnit then return true end

    -- 1. 必须是允许的单位类型
    local UnitInfo = GameInfo.Units[pUnit:GetType()]
    if not UnitInfo then return true end
    if not AllowUnits[UnitInfo.UnitType] then return true end

    -- 2. 必须有剩余移动力
    if pUnit:GetMovementMovesRemaining() <= 0 then return true end

    -- 3. [可选] 必须在自己的领土上
    -- local pPlot = Map.GetPlot(pUnit:GetX(), pUnit:GetY())
    -- if pPlot:GetOwner() ~= pUnit:GetOwner() then return true end

    -- 4. [可选] 必须是自己回合
    -- if not Players[Game.GetLocalPlayer()]:IsTurnActive() then return true end

    -- 5. [可选] 必须有建造次数
    -- if pUnit:GetBuildCharges() <= 0 then return true end

    -- 6. [可选] 判断格子状态（资源/区域等）
    -- local pPlot = Map.GetPlot(pUnit:GetX(), pUnit:GetY())
    -- if pPlot:GetResourceType() == -1 then return true end

    return false
end

-- IsButtonDisabled: 返回 (disabled, tooltip)
function IsButtonDisabled(pUnit)
    local str = Locale.Lookup("LOC_MY_UNIT_BUTTON_READY")
    local disabled = false

    -- [自定义禁用逻辑]
    -- 冷却时间检查
    -- local lastTurn = pUnit:GetProperty("PROPERTY_MY_COOLDOWN") or 0
    -- local remain = COOLDOWN - (Game.GetCurrentGameTurn() - lastTurn)
    -- if remain > 0 then disabled = true; str = Locale.Lookup("...", remain) end

    -- 资源不足
    -- if balance < COST then disabled = true; str = Locale.Lookup("...", COST) end

    return disabled, str
end

-- OnClick: 打包参数 → UI.RequestPlayerOperation
function OnButtonClicked()
    local pUnit = UI.GetHeadSelectedUnit()
    if not pUnit then return end
    local playerID = Game.GetLocalPlayer()
    local params = {
        OnStart = "MyMod_UnitButtonAction",
        UnitID  = pUnit:GetID(),
        iX      = pUnit:GetX(), iY = pUnit:GetY(),
        -- [自定义参数] ...
    }
    UI.RequestPlayerOperation(playerID, PlayerOperations.EXECUTE_SCRIPT, params)
    Controls.MyUnitButtonGrid:SetHide(true)     -- 点击后立即隐藏
end

-- Events
function OnUnitSelectionChanged(playerID, unitID, plotX, plotY, plotZ, bSelected, bEditable)
    if playerID ~= Game.GetLocalPlayer() then return end
    if bSelected then Refresh() end
end
function OnUnitMoveComplete(playerID, unitID, iX, iY)
    if playerID ~= Game.GetLocalPlayer() then return end
    Refresh()
end

function Initialize()
    Init()
    Events.UnitSelectionChanged.Add(OnUnitSelectionChanged)
    Events.UnitMoveComplete.Add(OnUnitMoveComplete)
    -- [可选] Events.UnitMovementPointsCleared.Add(Refresh)
    -- [可选] Events.UnitMovementPointsChanged.Add(Refresh)
    -- [可选] Events.UnitPromoted.Add(Refresh)
end
Events.LoadGameViewStateDone.Add(Initialize)
```

### 2.2 变体：根据领袖/文明控制按钮可见性

在 `IsButtonHide()` 或 `Refresh()` 开头增加领袖判断即可。

```lua
-- 方式 A：PlayerConfigurations 直判
function IsTargetLeader(playerID, leaderTypeName)
    return PlayerConfigurations[playerID]:GetLeaderTypeName() == leaderTypeName
end

-- 方式 B：Trait Property 判断（推荐，兼容文明特質）
function PlayerHasTrait(playerID, traitType)
    return SiqiUI["TRAIT"](playerID, traitType)
end

-- 方式 C：遍历 CivilizationTraits / LeaderTraits 表
function IPlayerHasTrait(playerID, sTrait)
    if not playerID or not sTrait then return false end
    local cfg = PlayerConfigurations[playerID]
    if not cfg then return false end
    local sCiv, sLea = cfg:GetCivilizationTypeName(), cfg:GetLeaderTypeName()
    for row in GameInfo.CivilizationTraits() do
        if row.CivilizationType == sCiv and row.TraitType == sTrait then return true end
    end
    for row in GameInfo.LeaderTraits() do
        if row.LeaderType == sLea and row.TraitType == sTrait then return true end
    end
    return false
end

-- 在 IsButtonHide 中使用
function IsButtonHide(pUnit)
    if not pUnit then return true end
    -- 只有目标领袖才显示按钮
    if not IsTargetLeader(pUnit:GetOwner(), "LEADER_SIQI_MY_LEADER") then return true end
    -- ... 其余条件
end
```

### 2.3 变体：单位面板按钮 + 选地格模式

与城市面板 1.3 模式一致，区别在于父容器和格子筛选方式。关键改动如下：

```lua
local m_IsInWBInterfaceMode = false
local m_Plots = nil                    -- { [plotIndex] = 1 }
local g_HexColoring = UILens.CreateLensLayerHash("MyMod_HexColoring_Unit")

function Init()
    local pContext = ContextPtr:LookUpControl("/InGame/UnitPanel/StandardActionsStack")
    if pContext then
        Controls.MyUnitButtonGrid:ChangeParent(pContext)
        Controls.MyUnitButton:RegisterCallback(Mouse.eLClick, OnButtonClicked)
    end
end

-- Refresh / IsButtonHide / IsButtonDisabled 同 2.1，略

-- 进入选地格模式
function OnButtonClicked()
    local pUnit = UI.GetHeadSelectedUnit()
    if not pUnit then return end
    if m_IsInWBInterfaceMode then QuitWBInterfaceMode(true); return end

    UI.SetInterfaceMode(InterfaceModeTypes.SELECTION)
    UI.SetInterfaceMode(InterfaceModeTypes.WB_SELECT_PLOT)
    m_IsInWBInterfaceMode = true
    Controls.MyUnitButton:SetSelected(true)

    local validPlots, hash = GetValidPlots(pUnit)
    m_Plots = hash
    if #validPlots > 0 then
        UILens.SetLayerHexesArea(g_HexColoring, Game.GetLocalPlayer(), validPlots)
        UILens.ToggleLayerOn(g_HexColoring)
    end
end

-- 地块选择监听（WorldInput_WBSelectPlot）
function OnSelectPlot(plotId, plotEdge, boolDown, rButton)
    if boolDown then return end
    if rButton then
        QuitWBInterfaceMode(true)           -- 右键取消
    else
        local pUnit = UI.GetHeadSelectedUnit()
        if pUnit and m_Plots and m_Plots[plotId] == 1 then
            QuitWBInterfaceMode(true)
            local params = {
                OnStart = "MyMod_UnitPlotAction",
                UnitID  = pUnit:GetID(),
                X = Map.GetPlotByIndex(plotId):GetX(),
                Y = Map.GetPlotByIndex(plotId):GetY(),
                PlotID  = plotId,
            }
            UI.RequestPlayerOperation(Game.GetLocalPlayer(), PlayerOperations.EXECUTE_SCRIPT, params)
            m_Plots = nil
            Controls.MyUnitButtonGrid:SetHide(true)
        end
    end
end

function QuitWBInterfaceMode(ifChangeInterfaceMode)
    if ifChangeInterfaceMode then UI.SetInterfaceMode(InterfaceModeTypes.SELECTION) end
    UILens.ClearLayerHexes(g_HexColoring)
    UILens.ToggleLayerOff(g_HexColoring)
    m_IsInWBInterfaceMode = false
    Controls.MyUnitButton:SetSelected(false)
end

-- 筛选可选格子（单位周围 N 格内可到达的地块）
function GetValidPlots(pUnit)
    local plots, hash = {}, {}
    local pVis = PlayersVisibility[pUnit:GetOwner()]
    if not pVis then return plots, hash end
    local tplot = Map.GetNeighborPlots(pUnit:GetX(), pUnit:GetY(), 3)
    for _, plot in ipairs(tplot) do
        if pVis:IsRevealed(plot:GetIndex())
            and not plot:IsImpassable() and not plot:IsMountain()
            and not plot:IsUnit() and not plot:IsCity() and not plot:IsWater() then
            local index = plot:GetIndex()
            table.insert(plots, index); hash[index] = 1
        end
    end
    return plots, hash
end

function Initialize()
    Init()
    Events.UnitSelectionChanged.Add(function(playerID, unitID, x, y, z, bSelected)
        if playerID ~= Game.GetLocalPlayer() then return end
        if bSelected then Refresh() else QuitWBInterfaceMode(false) end
    end)
    Events.UnitMoveComplete.Add(function(playerID)
        if playerID ~= Game.GetLocalPlayer() then return end; Refresh()
    end)
    Events.UnitMovementPointsCleared.Add(function()
        Controls.MyUnitButtonGrid:SetHide(true)
    end)
    Events.InterfaceModeChanged.Add(function(intPara, curMode)
        if m_IsInWBInterfaceMode and curMode ~= InterfaceModeTypes.WB_SELECT_PLOT then
            QuitWBInterfaceMode(false)
        end
    end)
    LuaEvents.WorldInput_WBSelectPlot.Add(OnSelectPlot)
end
Events.LoadGameViewStateDone.Add(Initialize)
```

---

## 三、关键要点速查

### 3.1 父容器路径

| 场景 | LookUpControl 路径 |
|------|-------------------|
| 城市面板操作按钮 | `/InGame/CityPanel/ActionStack` |
| 城市主面板内部 | `/InGame/CityPanel/MainPanel` |
| 单位面板操作按钮 | `/InGame/UnitPanel/StandardActionsStack` |
| 启动栏（右上角） | `/InGame/LaunchBar/ButtonStack` |

### 3.2 控件命名约定

XML 中每个按钮需要两个控件：`{Name}Grid`（容器，挂到父容器）+ `{Name}`（按钮本身）。

```xml
<Grid ID="MyCityButtonGrid" Anchor="C,C" Hidden="1">
    <Button ID="MyCityButton" ... />
</Grid>
```

### 3.3 事件速查

| 事件 | 适用场景 |
|------|---------|
| `Events.CitySelectionChanged` | CityPanel 按钮必须 |
| `Events.PlayerTurnActivated` | 回合开始时刷新状态 |
| `Events.CityProductionChanged` | 生产变化时刷新 |
| `Events.UnitSelectionChanged` | UnitPanel 按钮必须 |
| `Events.UnitMoveComplete` | 单位移动后刷新 |
| `Events.UnitMovementPointsCleared` | 移动力耗尽时隐藏 |
| `Events.UnitMovementPointsChanged` | 移动力变化时刷新 |
| `Events.UnitPromoted` | 单位晋升后刷新 |
| `Events.InterfaceModeChanged` | 选地格模式需监听 |
| `LuaEvents.WorldInput_WBSelectPlot` | 选地格模式必须 |

### 3.4 Refresh 三种形态

```lua
-- A: 三联直接型
function Refresh()
    Controls.ButtonGrid:SetHide(Hide())
    Controls.Button:SetDisabled(Disabled())
    Controls.Button:SetToolTipString(ToolTip())
end

-- B: 分离判断型（推荐）
function Refresh()
    if IsButtonHide() then Controls.ButtonGrid:SetHide(true)
    else
        Controls.ButtonGrid:SetHide(false)
        local d, s = IsButtonDisabled()
        Controls.Button:SetDisabled(d); Controls.Button:SetToolTipString(s)
    end
end

-- C: 条件排除型
function Refresh()
    if not pCity then Close(); return end
    if not HasTrait() then Close(); return end
    Controls.ButtonGrid:SetHide(false)
    Controls.Button:SetDisabled(false)
    Controls.Button:SetToolTipString(tooltip)
end
```

### 3.5 GP 通信规范

```lua
-- UI 端发送
local params = {
    OnStart = "MyUniqueActionName",     -- GP 端 GameEvents 名称（必填）
    -- 其他参数...
}
UI.RequestPlayerOperation(playerID, PlayerOperations.EXECUTE_SCRIPT, params)

-- GP 端接收（Scripts.lua）
function OnMyUniqueActionName(playerID, params)
    -- 执行游戏逻辑...
end
GameEvents.MyUniqueActionName.Add(OnMyUniqueActionName)
```

### 3.6 常见错误

| 错误 | 修正 |
|------|------|
| 按钮不出现（`IsButtonHide` 永远返回 true） | 逐行检查 early return 条件 |
| 按钮在错误玩家的城市出现 | `CitySelectionChanged` 加 `if ownerPlayerID ~= Game.GetLocalPlayer() then return end` |
| 选地格后无法退出 | 监听 `InterfaceModeChanged` + `WorldInput_WBSelectPlot` 右键处理 |
| 冷却时间切换单位后丢失 | 用 `pUnit:SetProperty()` 在 GP 端持久化，而非 UI 端记忆 |
| `RequestPlayerOperation` 无反应 | 检查 UI 和 Scripts 两端 `OnStart` 名称完全一致 |
| Tooltip 不显示 / 闪烁 | **不要在 `eMouseEnter` 里设 Tooltip**。Tooltip 必须在 `Refresh()` 中主动调用 `SetToolTipString` 一次设好。`eMouseEnter` 仅限播音效等副作用，永远不用于更新 Tooltip 文本。原因：游戏引擎的 Tooltip 系统在 hover 时自行读取已设置的值，`eMouseEnter` 里动态改会冲突导致不显示。 |
| Tooltip 禁用原因文字 | 用 `[COLOR_RED]reason[ENDCOLOR]` 包裹，封装为 `Red(str)` 辅助函数。参见 `SiqiUI.Red` 模式。 |
