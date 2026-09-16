# 游戏事件驱动的 UI 自动刷新模式（来源：Better Religion Screen + Extended Policy Cards）

## 做什么
监听游戏核心事件（GameEvents / Events），在相关游戏状态变化时自动刷新 UI，免去玩家手动操作。同时使用状态守卫防止在 UI 自身发起操作后的"刷新风暴"。

## 涉及文件

| 文件 | 来源 Mod | 角色 |
|------|---------|------|
| `ReligionScreen.lua` | Better Religion Screen (2145663327) | 事件驱动刷新 + 状态守卫 |
| `GovernmentScreen.lua` | Extended Policy Cards (2266952591) | 多事件监听 + 热座处理 |

## 技术原理

### Better Religion Screen 的事件监听

```lua
-- 初始化时注册
function Initialize()
    -- GameCore Events
    Events.BeliefAdded.Add(OnBeliefAdded)
    Events.PantheonFounded.Add(OnPantheonFounded)
    Events.ReligionFounded.Add(OnReligionFounded)
    Events.LocalPlayerTurnEnd.Add(OnLocalPlayerTurnEnd)

    -- LuaEvents (UI 侧)
    LuaEvents.LaunchBar_OpenReligionPanel.Add(OnShowScreen)
    LuaEvents.LaunchBar_CloseReligionPanel.Add(OnClose)
    LuaEvents.NotificationPanel_OpenReligionPanel.Add(OnShowScreen)
    LuaEvents.PantheonChooser_OpenReligionPanel.Add(OnShowScreen)

    -- GameDebug (热加载支持)
    LuaEvents.GameDebug_Return.Add(OnGameDebugReturn)
end

-- 关闭时注销
function OnShutdown()
    Events.BeliefAdded.Remove(OnBeliefAdded)
    Events.PantheonFounded.Remove(OnPantheonFounded)
    Events.ReligionFounded.Remove(OnReligionFounded)
    Events.LocalPlayerTurnEnd.Remove(OnLocalPlayerTurnEnd)
    LuaEvents.GameDebug_Return.Remove(OnGameDebugReturn)
    LuaEvents.LaunchBar_OpenReligionPanel.Remove(OnShowScreen)
    -- ...
end
```

### 带状态守卫的刷新函数

关键守卫：`m_isConfirmedBeliefs` 和 `m_TurnBlockingType`

```lua
function OnBeliefAdded(ePlayer)
    if ePlayer == Game.GetLocalPlayer() then
        -- 注意：选择信条后 m_TurnBlockingType 不会立即清除
        -- 因此在确认信条期间的 UI 更新可能造成"刷新风暴"
        if not m_isConfirmedBeliefs
           or m_TurnBlockingType ~= EndTurnBlockingTypes.ENDTURN_BLOCKING_BELIEF then
            UpdateData()
        end
    end
end

function OnPantheonFounded(ePlayer)
    if ePlayer == Game.GetLocalPlayer() then
        if not m_isConfirmedBeliefs
           or m_TurnBlockingType ~= EndTurnBlockingTypes.ENDTURN_BLOCKING_BELIEF then
            UpdateData()
        end
    end
end

function OnReligionFounded(ePlayer)
    if ePlayer == Game.GetLocalPlayer() then
        if not m_isConfirmedBeliefs
           or m_TurnBlockingType ~= EndTurnBlockingTypes.ENDTURN_BLOCKING_BELIEF then
            UpdateData()
        end
    end
end
```

守卫逻辑说明：
- `m_isConfirmedBeliefs == true` 且 `m_TurnBlockingType == ENDTURN_BLOCKING_BELIEF` → 说明是 UI 自己发起确认操作后的回调，此时不刷新（避免"刷新风暴"）
- 否则 → 说明是外部操作（如其他玩家选择万神殿），需要刷新

### Extended Policy Cards 的事件监听

```lua
function Initialize()
    -- GameCore Events
    Events.CivicsUnlocked.Add(OnCivicsUnlocked)
    Events.GovernmentChanged.Add(OnGovernmentChanged)
    Events.GovernmentPolicyChanged.Add(OnGovernmentPolicyChanged)
    Events.GovernmentPolicyObsoleted.Add(OnGovernmentPolicyChanged)
    Events.PhaseBegin.Add(OnPhaseBegin)
    Events.LocalPlayerTurnBegin.Add(OnLocalPlayerTurnBegin)
    Events.LocalPlayerTurnEnd.Add(OnLocalPlayerTurnEnd)
    Events.SystemUpdateUI.Add(OnUpdateUI)

    -- LuaEvents (UI 打开入口)
    LuaEvents.LaunchBar_CloseGovernmentPanel.Add(OnCloseFromLaunchBar)
    LuaEvents.NotificationPanel_GovernmentOpenGovernments.Add(OnOpenGovernmentScreenGovernments)
    LuaEvents.NotificationPanel_GovernmentOpenPolicies.Add(OnOpenGovernmentScreenPolicies)
    LuaEvents.LaunchBar_GovernmentOpenMyGovernment.Add(OnOpenGovernmentScreenMyGovernment)
    LuaEvents.TechCivicCompletedPopup_GovernmentOpenGovernments.Add(OnOpenGovernmentScreenGovernments)
    LuaEvents.TechCivicCompletedPopup_GovernmentOpenPolicies.Add(OnOpenGovernmentScreenPolicies)
    LuaEvents.Advisor_GovernmentOpenPolicies.Add(OnOpenGovernmentScreenPolicies)
end
```

### 数据改动时立即刷新可见 UI

```lua
function OnGovernmentChanged(playerID)
    if playerID == m_ePlayer and m_ePlayer ~= -1 then
        RefreshAllData()             -- 总是刷新数据
        if ContextPtr:IsVisible() then -- 如果屏幕可见，立即重绘
            RealizeMyGovernmentPage()
            RealizeGovernmentsPage()
            RealizePoliciesPage()
        end
        -- 如果当前政体变为 nil（无政府状态），关闭屏幕
        if g_kCurrentGovernment == nil and ContextPtr:IsVisible() then
            Close()
        end
    end
end
```

### 屏幕大小变化处理

```lua
function OnUpdateUI(type, tag, iData1, iData2, strData1)
    if type == SystemUpdateUI.ScreenResize then
        Resize()
        SwitchTab(m_tabs.selectedControl, m_tabs.selectedControl, true)
    end
end
```

### 热座支持：多玩家数据保存/恢复

```lua
function OnLocalPlayerTurnBegin()
    m_isLocalPlayerTurn = true
    local ePlayer = Game.GetLocalPlayer()
    if ePlayer ~= m_ePlayer and m_ePlayer ~= -1 then
        SaveLivePlayerData(m_ePlayer)  -- 保存前一个玩家的 UI 状态
    end
    m_ePlayer = ePlayer
    if m_ePlayer ~= -1 then
        RefreshAllData()
    end
end

function OnLocalPlayerTurnEnd()
    m_isLocalPlayerTurn = false
    if GameConfiguration.IsHotseat() then
        Close()  -- 热座模式下关闭
    end
end

function SaveLivePlayerData(ePlayer)
    local playerData = {}
    playerData[DATA_FIELD_CURRENT_FILTER] = m_kPolicyFilterCurrent
    m_kAllPlayerData[ePlayer] = playerData
end
```

### PhaseBegin 作为后备刷新

```lua
function OnPhaseBegin()
    local ePlayer = Game.GetLocalPlayer()
    if ePlayer ~= m_ePlayer and m_ePlayer ~= -1 then
        SaveLivePlayerData(m_ePlayer)
    end
    m_ePlayer = ePlayer
    if m_ePlayer ~= -1 then
        RefreshAllData()
    end
end
```

### 热加载状态恢复 (GameDebug)

```lua
-- 关闭时缓存状态
function OnShutdown()
    local eOpenTabAtInit = nil
    if ContextPtr:IsVisible() then
        if m_tabs.selectedControl == Controls.ButtonMyGovernment then
            eOpenTabAtInit = SCREEN_ENUMS.MY_GOVERNMENT
        elseif m_tabs.selectedControl == Controls.ButtonGovernments then
            eOpenTabAtInit = SCREEN_ENUMS.GOVERNMENTS
        else
            eOpenTabAtInit = SCREEN_ENUMS.POLICIES
        end
    end
    LuaEvents.GameDebug_AddValue("GovernmentScreen", "eOpenTabAtInit", eOpenTabAtInit)
end

-- 热加载后恢复
function OnGameDebugReturn(context, contextTable)
    if context == "GovernmentScreen" and contextTable then
        local eOpenTabAtInit = contextTable["eOpenTabAtInit"]
        if eOpenTabAtInit ~= nil and OnOpenGovernmentScreen ~= nil then
            OnOpenGovernmentScreen(eOpenTabAtInit)
        end
    end
end
```

## 模式模板

```lua
-- ===========================================================================
-- 游戏事件驱动的 UI 刷新模板
-- ===========================================================================

local m_IsSelfTriggered = false   -- 防止自触发刷新风暴

-- === 注册事件（Initialize） ===
function Initialize()
    -- 注册 GameCore Events
    Events.GameEventName.Add(OnGameEvent)

    -- 注册 UI 打开入口（可能有多个来源）
    LuaEvents.LaunchBar_OpenMyPanel.Add(OnShowScreen)
    LuaEvents.Notification_OpenMyPanel.Add(OnShowScreen)

    -- 热加载支持
    LuaEvents.GameDebug_Return.Add(OnGameDebugReturn)

    ContextPtr:SetInitHandler(OnInit)
    ContextPtr:SetShutdown(OnShutdown)
end

-- === 注销事件（OnShutdown） ===
function OnShutdown()
    Events.GameEventName.Remove(OnGameEvent)
    LuaEvents.LaunchBar_OpenMyPanel.Remove(OnShowScreen)
    LuaEvents.Notification_OpenMyPanel.Remove(OnShowScreen)
    LuaEvents.GameDebug_Return.Remove(OnGameDebugReturn)

    -- 缓存状态用于热加载
    LuaEvents.GameDebug_AddValue("MyScreen", "isVisible", not ContextPtr:IsHidden())
end

-- === 事件回调：带守卫的刷新 ===
function OnGameEvent(playerID)
    -- 守卫 1：只处理本地玩家
    if playerID ~= Game.GetLocalPlayer() then return end

    -- 守卫 2：防止自己的操作触发刷新风暴
    if m_IsSelfTriggered then return end

    -- 刷新数据
    UpdateAllData()

    -- 如果屏幕可见，立即重绘
    if not ContextPtr:IsHidden() then
        RealizeCurrentView()
    end
end

-- === 热座/多玩家支持 ===
function OnLocalPlayerTurnBegin()
    local ePlayer = Game.GetLocalPlayer()
    if ePlayer ~= m_CurrentPlayer then
        SavePlayerUIState(m_CurrentPlayer)
    end
    m_CurrentPlayer = ePlayer
    UpdateAllData()
end

function OnLocalPlayerTurnEnd()
    if GameConfiguration.IsHotseat() then
        Close()
    end
end

-- === 屏幕大小变化 ===
function OnUpdateUI(type)
    if type == SystemUpdateUI.ScreenResize then
        Resize()
    end
end

-- === UI 打开入口（支持多种触发源） ===
function OnShowScreen()
    Open()
end

function Open()
    if Game.GetLocalPlayer() == -1 then return end

    UpdateAllData()

    if not UIManager:IsInPopupQueue(ContextPtr) then
        local kParameters = {}
        kParameters.RenderAtCurrentParent = true
        kParameters.InputAtCurrentParent = true
        kParameters.AlwaysVisibleInQueue = true
        UIManager:QueuePopup(ContextPtr, PopupPriority.Low, kParameters)
        UI.PlaySound("UI_Screen_Open")
    end

    -- 顶部栏 Vignette 偏移
    if not RefreshYields() then
        Controls.Vignette:SetSizeY(m_TopPanelConsideredHeight)
    end

    Controls.ScreenAnimIn:SetToBeginning()
    Controls.ScreenAnimIn:Play()
end
```

## 设计要点

1. **守卫 1：玩家检查** — `if playerID ~= Game.GetLocalPlayer() then return end`，热座模式下必须过滤
2. **守卫 2：自触发防护** — 用 `m_isConfirmedBeliefs` 等标志位防止 UI 发起操作后的事件回调触发重复刷新
3. **守卫 3：可见性检查** — `if ContextPtr:IsHidden() then return end`，不可见时只更新数据不重绘
4. **事件注册/注销对称** — 每个 `Events.XXX.Add` 在 `OnShutdown` 中都有对应的 `Remove`
5. **多入口统一** — 多个 `LuaEvents.XXX_OpenPanel` 都指向同一个 `OnShowScreen`，保持入口单一
6. **热加载缓存** — 用 `LuaEvents.GameDebug_AddValue` 缓存当前状态，`GameDebug_Return` 恢复
7. **ScreenResize 即刷新** — 窗口大小变化必须重新计算所有布局
8. **PopupQueue 检查** — `UIManager:IsInPopupQueue` 防止重复入队

## XML 配合

### 涉及的关键 XML 文件

| 文件 | 来源 Mod | 用途 |
|------|---------|------|
| `ReligionScreen.xml` | Better Religion Screen (2145663327) | 事件驱动刷新 + 状态守卫的 XML 载体 |
| `GovernmentScreen.xml` | Extended Policy Cards (2266952591) | 多事件监听 + 热座处理的 XML 载体 |

### 核心控件 ID 对照表（事件刷新相关）

| 控件 ID | 类型 | 来源文件 | 用途 |
|---------|------|---------|------|
| **打开/关闭动画** | | | |
| `Vignette` | Container | 通用 | 全屏遮罩（SetSizeY 用于适配顶部栏） |
| `ScreenAnimIn` / `SlideAnim` | AlphaAnim / SlideAnim | 通用 | 面板打开入场动画（SetToBeginning + Play） |
| `CloseButton` | Button | 通用 | 关闭按钮（触发 Close()） |
| **ReligionScreen 刷新目标** | | | |
| `ViewReligion` + 子控件 | Container + Labels | ReligionScreen.xml | 查看宗教状态数据刷新 |
| `AvailableBeliefs` | Stack | ReligionScreen.xml | 可选信条列表（事件触发后重建） |
| `SelectedBeliefs` | Stack | ReligionScreen.xml | 已选信条列表 |
| `Cities` | Stack | ReligionScreen.xml | 城市数据列表 |
| `CivStack` | Stack | ReligionScreen.xml | 文明数据列表 |
| `FilterType` / `FilterCiv` | PullDown | ReligionScreen.xml | 过滤下拉（选择变化触发刷新） |
| **GovernmentScreen 刷新目标** | | | |
| `MyGovernment` + 子控件 | Stack + Labels + Images | GovernmentScreen.xml | 我的政体面板刷新 |
| `HeritageBonusStack` | Stack | GovernmentScreen.xml | 传承加成列表 |
| `PolicyCatalog` | Stack | GovernmentScreen.xml | 政策目录刷新 |
| `StackMilitary` / `StackEconomic` / `StackDiplomatic` / `StackWildcard` | Container | GovernmentScreen.xml | 四行政策槽位刷新 |
| `GovernmentTree` + `GovernmentDividers` | AlphaAnim + Container | GovernmentScreen.xml | 政体树视图刷新 |
| `PolicyListScroller` / `PoliciesListStack` | ScrollPanel / Stack | GovernmentScreen.xml | 政策清单侧栏刷新 |
| **产量条** | | | |
| `YieldStack` / `SciencePerTurn` / `CulturePerTurn` 等 | Stack + Labels | 通用 | 顶部产量条（RefreshYields） |

### 可复用 XML 模板（支持事件驱动刷新的面板骨架）

```xml
<Context>
    <Container ID="Vignette" Style="FullScreenVignetteConsumer" />

    <!-- 开场/离场动画容器 -->
    <AlphaAnim ID="ScreenAnimIn" AlphaStart="0" AlphaEnd="1" Cycle="Once" Speed="3" Function="Root" Stopped="1">
        <SlideAnim ID="SlideAnim" Start="0,-30" End="0,0" Cycle="Once" Speed="3" Function="Root" Stopped="1">
            <!-- 产量条 -->
            <Stack ID="YieldStack" Offset="10,0" StackGrowth="Right" Padding="2" Anchor="R,T">
                <GridButton ID="ScienceBacking" Size="auto,24" Style="YieldBacking">
                    <Stack Anchor="L,C" StackGrowth="Right">
                        <Label String="[ICON_ScienceLarge]"/>
                        <Label ID="SciencePerTurn" Style="FontNormal18" String="0"/>
                    </Stack>
                </GridButton>
                <!-- ... 更多产量条 ... -->
            </Stack>
        </SlideAnim>
    </AlphaAnim>

    <!-- 标题栏 -->
    <Grid Anchor="C,T" Size="parent-6,140" Offset="0,50" Texture="Controls_TitleBarDark">
        <Button ID="CloseButton" Anchor="R,T" Offset="5,40" Style="CloseButtonSmall"/>
        <!-- Tab 按钮 -->
        <Container ID="TabContainer" Anchor="C,T" Offset="0,-10" Size="540,61">
            <GridButton ID="Tab1Button" Size="150,34" Style="TabButton" String="LOC_TAB_1">
                <GridButton ID="Tab1Selected" Size="parent,parent" Style="TabButtonSelected" ConsumeMouseButton="0" ConsumeMouseOver="1"/>
            </GridButton>
        </Container>
    </Grid>

    <!-- 数据列表区（事件触发后重建） -->
    <Container Anchor="C,B" Size="parent,parent-195" Offset="0,5">
        <ScrollPanel ID="BodyScrollPanel" Size="495,parent" Vertical="1">
            <ScrollBar Anchor="R,C" AnchorSide="O,I" Style="ScrollVerticalBar"/>
            <Stack ID="BodyStack" StackGrowth="Down" StackPadding="4"/>
        </ScrollPanel>
    </Container>

    <!-- Instance -->
    <Instance Name="DataRowInstance">
        <Container ID="Top" Size="485,78" Offset="10,0">
            <GridButton ID="GridButton" Size="parent,parent">
                <Label ID="RowLabel" Anchor="L,T" Offset="33,10" Style="FontFlair16" TruncateWidth="370"/>
                <!-- 数据字段... -->
            </GridButton>
        </Container>
    </Instance>
</Context>
```

### 事件刷新与 XML 的关系

- 每个 `Events.XXX.Add(handler)` 对应 XML 中的某个数据展示区
- `m_isConfirmedBeliefs` 守卫防止 UI 发起确认后的回调触发"刷新风暴"，涉及 XML 中的 `ConfirmBeliefs` 等按钮
- `RefreshYields()` 依赖 XML 中定义的 `YieldStack` 及其子 Label ID
- 热座支持 `SaveLivePlayerData()` 保存的是 UI 状态（如 `m_kPolicyFilterCurrent`），对应 XML 中的 `FilterPolicyPulldown`
- `OnUpdateUI(ScreenResize)` 触发 `Resize()`，需重新计算 XML 中所有容器尺寸
