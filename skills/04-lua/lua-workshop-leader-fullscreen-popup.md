# 领袖自定义全屏弹窗面板（来源：Majo WitchBook、Laterano Belief、YvangelistaXI GP、Amphoreus SayWonder）

## 做什么
创建独立的全屏/大半屏弹窗面板，用于显示领袖专属交互界面（教条选择、伟人招募、奇观预言、故事书阅览等）。点击 LaunchBar 中的自定义按钮或通过 LuaEvents 触发打开。

## 涉及 Mod

| Mod | 面板名 | 功能 |
|-----|--------|------|
| Majo no Tabitabi | WitchBook | 魔女故事书翻页阅览器 |
| Laterano | Extra Belief Panel | 额外教条选择面板 |
| Laterano | YvangelistaXI Panel | 伟人招募面板（含分类过滤、费用计算） |
| Amphoreus 翁法罗斯 | SayWonder | 奇观预言选择面板（图标网格） |
| Iberia XP | OphEventChoice | 自定义事件/选择弹窗 |
| EagleUnion | Flasher Extra Panel | 世界追踪器顶部击杀计数器面板 |

## 架构：弹窗生命周期

```
[LaunchBar 按钮点击 / LuaEvents 触发]
  → LuaEvents.Xxx_TogglePopup.Add(OnTogglePanel)
  → OnTogglePanel()
    → if 隐藏: Open()
    → if 显示: Close()

[Open]
  → ContextPtr:SetHide(false)
  → UIManager:QueuePopup(ContextPtr, priority, options)  [可选]
  → CloseOtherPanels()
  → Realize() / Refresh()
  → PlayOpenAnim / PlaySound

[Close]
  → PlayCloseAnim / PlaySound
  → UIManager:DequeuePopup(ContextPtr)  [可选]
  → ContextPtr:SetHide(true)
```

## 步骤 1：LaunchBar 入口按钮

在顶部右侧 LaunchBar 添加自定义按钮：

```xml
<Context FontStyle="Stroke">
    <Instance Name="WitchBookItem">
        <Button ID="WitchBookButton" Anchor="L,C" Size="49,49"
                Texture="LaunchBar_Hook_GovernmentButton"
                Style="ButtonNormalText"
                StateOffsetIncrement="0,49"
                ToolTip="LOC_TOPPANEL_WITCHBOOK_NAME">
            <Image ID="WitchBookIcon" Size="35,35" Anchor="C,C" Offset="0,0"
                   Texture="LaunchBar_Hook_WitchBook"/>
        </Button>
    </Instance>

    <!-- 装饰性分隔点 -->
    <Instance Name="WitchBookPinInstance">
        <Image ID="ReminderPin" Anchor="L,C" Offset="0,-2" Size="7,7"
               Texture="LaunchBar_TrackPip" Color="255,255,255,200"/>
    </Instance>
</Context>
```

```lua
-- 入口按钮挂载到 LaunchBar
function AttachLaunchButton()
    local buttonStack = ContextPtr:LookUpControl("/InGame/LaunchBar/ButtonStack")

    ContextPtr:BuildInstanceForControl("WitchBookItem",
        m_LaunchButtonInstance, buttonStack)
    m_LaunchButtonInstance.WitchBookButton:RegisterCallback(
        Mouse.eLClick, ShowWitchBook)

    ContextPtr:BuildInstanceForControl("WitchBookPinInstance", {}, buttonStack)

    -- 调整 LaunchBar 背景大小
    buttonStack:CalculateSize()
    local backing = ContextPtr:LookUpControl("/InGame/LaunchBar/LaunchBacking")
    backing:SetSizeX(buttonStack:GetSizeX() + 116)
    local backingTile = ContextPtr:LookUpControl("/InGame/LaunchBar/LaunchBackingTile")
    backingTile:SetSizeX(buttonStack:GetSizeX() - 20)

    LuaEvents.LaunchBar_Resize(buttonStack:GetSizeX())
end

function ShowWitchBook()
    LuaEvents.ShowWitchBook()  -- 通知弹窗面板打开
end

Events.LoadGameViewStateDone.Add(AttachLaunchButton)
```

## 步骤 2：弹窗面板 XML 模板

### 全屏 Image 承载（WitchBook 模式）

```xml
<Context>
    <!-- 全屏背景图 -->
    <Image ID="WitchBookUI" Size="1280,720" Anchor="C,C"
           Texture="AranyakaBook720">

        <!-- 关闭按钮（右上） -->
        <Button ID="CloseBtn" Size="73,63" Offset="33,85"
                Anchor="R,T" Texture="WitchBook_CloseBtn"
                States="2" StateOffsetIncrement="0,63"
                ToolTip="LOC_WITCHBOOK_CLOSEBTN_TOOLTIP"/>

        <!-- 主内容区域 -->
        <Container ID="MainContainer" Size="parent-300,parent-150"
                   Anchor="C,C" Offset="5,-5">
            <!-- 左页堆叠 -->
            <Stack ID="PageStackLeft" Size="parent-530,parent"
                   Anchor="L,T"/>
            <!-- 右页堆叠 -->
            <Stack ID="PageStackRight" Size="parent-530,parent"
                   Anchor="R,T"/>

            <!-- 页码 + 翻页按钮 -->
            <Container Anchor="C,B" Offset="0,-15" Size="300,50">
                <Label ID="PageNum" String="1/1" Anchor="C,C"
                       Font="GSIFont.ttc" FontSize="32"
                       FontStyle="stroke" Color0="132,96,61,255"/>
                <Button ID="PageUpButton" Size="50,50" Anchor="L,T"
                        Texture="WitchBookArrowLeft" States="5"
                        StateOffsetIncrement="0,50"/>
                <Button ID="PageDownButton" Size="50,50" Anchor="R,T"
                        Texture="WitchBookArrowRight" States="5"
                        StateOffsetIncrement="0,50"/>
            </Container>
        </Container>
    </Image>

    <!-- 页面 Instance -->
    <Instance Name="BookPage">
        <Container ID="PageContainer" Size="parent,parent" Anchor="L,T">
            <Label ID="PageTitleText" Anchor="C,T" Font="GSIFont.ttc"
                   FontSize="32" FontStyle="stroke"
                   Color0="132,96,61,255"/>
            <Label ID="PageMainText" Size="450,parent-40" Anchor="L,T"
                   Offset="0,40" Font="GSIFont.ttc" FontSize="20"
                   FontStyle="stroke" Color0="171,146,122,255"
                   Align="left"/>
        </Container>
    </Instance>
</Context>
```

### 标准弹窗框架（Laterano / SayWonder 模式）

```xml
<Context>
    <Container Style="FullScreenVignetteConsumer"/>
    <BoxButton ID="ScreenConsumer" ConsumeMouseButton="1"
               ConsumeMouseWheel="1"/>

    <Grid ID="DropShadow" Size="595,auto" Anchor="C,C"
          Style="DropShadow2">
        <Grid ID="Window" Anchor="C,C" Style="EventPopupFrame">
            <!-- 标题栏 -->
            <Grid Style="EventPopupTitleBar" Anchor="C,T">
                <Label ID="EventTitle" Style="EventPopupTitle"
                       String="LOC_PANEL_TITLE"/>
                <Button ID="Header_CloseButton"
                        Style="EventPopupTitleCloseButton"/>
            </Grid>

            <!-- 滚动内容区 -->
            <ScrollPanel Anchor="C,T" Vertical="1"
                         Size="parent,parent-80" Offset="0,10">
                <Stack StackGrowth="Down" StackPadding="4"
                       Anchor="C,T">
                    <!-- 动态填充内容 -->
                </Stack>
            </ScrollPanel>

            <!-- 确认按钮 -->
            <Container Anchor="C,B" Offset="0,13">
                <GridButton ID="ConfirmButton" Style="MainButton"
                            Size="220,40" String="LOC_OK"/>
            </Container>
        </Grid>
    </Grid>
</Context>
```

## 步骤 3：Lua — 弹窗核心逻辑

### Open/Close 模式

```lua
function OnTogglePanel()
    if ContextPtr:IsHidden() then
        Open()
    else
        Close()
    end
end

function Open()
    if Game.GetLocalPlayer() == -1 then return end
    ContextPtr:SetHide(false)

    -- 可选：使用 QueuePopup（更高优先级，会遮盖其他面板）
    if not UIManager:IsInPopupQueue(ContextPtr) then
        local kParams = {
            RenderAtCurrentParent = true,
            InputAtCurrentParent = true,
            AlwaysVisibleInQueue = true,
        }
        UIManager:QueuePopup(ContextPtr, PopupPriority.Low, kParams)
        -- 如果需要在 Screens 层级显示
        ContextPtr:ChangeParent(ContextPtr:LookUpControl("/InGame/Screens"))
    end

    -- 播放打开音效和动画
    Controls.PantheonChooserSlideAnim:SetToBeginning()
    Controls.PantheonChooserSlideAnim:Play()
    UI.PlaySound("Tech_Tray_Slide_Open")

    CloseOtherPanels()  -- 关闭其他已打开面板
    Refresh()
end

function Close()
    if not Controls.PantheonChooserSlideAnim:IsReversing() then
        Controls.PantheonChooserSlideAnim:SetToEnd()
        Controls.PantheonChooserSlideAnim:Reverse()
        UI.PlaySound("Tech_Tray_Slide_Closed")
    end

    UIManager:DequeuePopup(ContextPtr)
    -- 动画完成后再隐藏（在 OnAnimEnd 中处理）
end

function OnAnimEnd()
    if Controls.PantheonChooserSlideAnim:IsReversing() then
        ContextPtr:SetHide(true)
    end
end
```

### ESC 关闭处理

```lua
function OnInputHandler(pInputStruct)
    local uiMsg = pInputStruct:GetMessageType()
    if uiMsg == KeyEvents.KeyUp and pInputStruct:GetKey() == Keys.VK_ESCAPE then
        if not ContextPtr:IsHidden() then
            Close()
        end
        return true
    end
    return false
end

ContextPtr:SetInputHandler(OnInputHandler, true)
```

### 关闭其他面板（面板互斥）

```lua
function CloseOtherPanels()
    LuaEvents.LaunchBar_CloseTechTree()
    LuaEvents.LaunchBar_CloseCivicsTree()
    LuaEvents.LaunchBar_CloseGovernmentPanel()
    LuaEvents.LaunchBar_CloseReligionPanel()
    LuaEvents.LaunchBar_CloseGreatPeoplePopup()
    LuaEvents.LaunchBar_CloseGreatWorksOverview()
    -- Expansion 面板
    LuaEvents.GovernorPanel_Close()
    LuaEvents.HistoricMoments_Close()
    LuaEvents.ClimateScreen_Opened()
end

-- 同时监听外部面板打开事件来关闭本面板
LuaEvents.DiplomacyActionView_HideIngameUI.Add(Close)
LuaEvents.EndGameMenu_Shown.Add(Close)
LuaEvents.FullscreenMap_Shown.Add(Close)
LuaEvents.TechTree_OpenTechTree.Add(Close)
LuaEvents.CivicsTree_OpenCivicsTree.Add(Close)
LuaEvents.Government_OpenGovernment.Add(Close)
LuaEvents.Religion_OpenReligion.Add(Close)
```

## 步骤 4：WitchBook 翻页器物

使用自定义数据库表存储故事页面数据：

```lua
local m_currentPage = 1
local m_PageLeft  = InstanceManager:new("BookPage", "PageContainer", Controls.PageStackLeft)
local m_PageRight = InstanceManager:new("BookPage", "PageContainer", Controls.PageStackRight)

function Refresh()
    -- 从 ExposedMembers 获取玩家解锁的故事列表
    local bookData = ExposedMembers.ElainaWitchBook

    -- 计算总页数
    totalPages = 0
    for _, storyID in pairs(bookData) do
        totalPages = totalPages + GameInfo.Majo_no_Tabitabi_Stories[storyID].PageNum
    end

    -- 定位当前显示的两页
    UpdateCurrentPageInfo()

    -- 渲染左右页
    m_PageLeft:ResetInstances()
    m_PageRight:ResetInstances()
    if pageLeftInfo then
        local inst = m_PageLeft:GetInstance()
        inst.PageTitleText:SetText(Locale.Lookup(pageLeftInfo.StoryTitle))
        inst.PageMainText:SetText(Locale.Lookup(pageLeftInfo.StoryBody))
    end
    if pageRightInfo then
        local inst = m_PageRight:GetInstance()
        inst.PageTitleText:SetText(Locale.Lookup(pageRightInfo.StoryTitle))
        inst.PageMainText:SetText(Locale.Lookup(pageRightInfo.StoryBody))
    end

    Controls.PageNum:SetText(m_currentPage .. ' / ' .. math.ceil(totalPages/2))
end

function PageUp()
    if m_currentPage > 1 then
        m_currentPage = m_currentPage - 1
        UI.PlaySound("Civilopedia_Page_Turn")
        Refresh()
    end
end

function PageDown()
    if m_currentPage * 2 < totalPages then
        m_currentPage = m_currentPage + 1
        UI.PlaySound("Civilopedia_Page_Turn")
        Refresh()
    end
end

-- 键盘翻页支持
function OnInputHandler(pInputStruct)
    local uiMsg = pInputStruct:GetMessageType()
    if uiMsg == KeyEvents.KeyUp then
        local key = pInputStruct:GetKey()
        if key == 84 or key == 79 then      -- PageUp
            PageUp(); return true
        elseif key == 86 or key == 82 then  -- PageDown
            PageDown(); return true
        end
    end
    return false
end
```

## 步骤 5：YvangelistaXI 伟人招募面板（完整模式）

### 数据刷新与缓存

```lua
-- 缓存结构：侦测其他玩家招募的伟人
function InsertRecruitableGreatPeople(iPlayer, iUnit, iClass, iIndividual)
    if iPlayer == Game.GetLocalPlayer() then return end
    if not HasTrait_Property(TRAIT_YVANGELISTA, iPlayer) then return end

    -- 构建伟人数据
    local kPersonInfo = {
        GreatPersonClassType = kClassInfo.GreatPersonClassType,
        GreatPersonIndividualType = kIndividualInfo.GreatPersonIndividualType,
        EraType = kIndividualInfo.EraType,
        Cost = ((GameInfo.Eras[kIndividualInfo.EraType].Index + 1) * 500 * SPEED_FACTOR),
        FormerOwner = iPlayer,
        -- ...
    }
    table.insert(m_kCacheGreatPersonAvailable, kPersonInfo)

    LuaEvents.Yvangelista_CallLaunchButtonAlert()  -- 通知入口按钮发光
end

Events.UnitGreatPersonCreated.Add(InsertRecruitableGreatPeople)
```

### InstanceManager 渲染 + 信仰支付

```lua
function PopulateInstance(kUnitInfo, index)
    local instance = m_greatPersonPanelIM:GetInstance()

    -- 伟人头像（区分 Timeline 伟人和非 Timeline 伟人）
    local portrait
    if GameInfo.GreatPersonClasses[kUnitInfo.GreatPersonClassType].AvailableInTimeline then
        portrait = "ICON_GENERIC_" .. kUnitInfo.GreatPersonClassType
        portrait = portrait:gsub("_CLASS", "_INDIVIDUAL")
    else
        portrait = "ICON_" .. GameInfo.GreatPersonClasses[kUnitInfo.GreatPersonClassType].UnitType
    end
    instance.Portrait:SetIcon(portrait)

    instance.ClassName:SetText(Locale.Lookup(kUnitInfo.GreatPersonClassName))
    instance.IndividualName:SetText(Locale.Lookup(kUnitInfo.GreatPersonIndividualName))
    instance.EraName:SetText(Locale.Lookup(GameInfo.Eras[kUnitInfo.EraType].Name))

    -- 能力效果文本（Active + Passive）
    RenderAbilityEffects(instance, kUnitInfo)

    -- 显示来源文明图标和颜色
    local FormerCivType = PlayerConfigurations[iPlayer]:GetCivilizationTypeName()
    local primaryColor, secondaryColor = UI.GetPlayerColors(iPlayer)
    instance.CivIndicator:SetColor(primaryColor)
    instance.CivIcon:SetColor(secondaryColor)
    instance.CivIcon:SetIcon('ICON_' .. FormerCivType)

    -- 费用计算和方法检查
    local FaithCost = math.ceil(kUnitInfo.Cost * multiplier)
    local Disabled = false
    if not HasMatchedDistrict(domain) then
        Disabled = true
    elseif FaithBalance < FaithCost then
        Disabled = true
    end

    instance.FaithButton:SetDisabled(Disabled)
    instance.FaithButton:SetText('[ICON_FAITH]' .. FaithCost)
    instance.FaithButton:RegisterCallback(Mouse.eLClick, function()
        Yvangelista_RecruitGreatPerson(hIndividual, hClass, hEra, FaithCost, index, iFormerOwner)
        UI.PlaySound("Purchase_With_Faith")
    end)
end
```

### 分类过滤（PullDown 下拉）

```lua
function InitPresets()
    Controls.PresetPulldown:ClearEntries()

    -- "全部" 选项
    local entry = {}
    Controls.PresetPulldown:BuildEntry("InstanceOne", entry)
    entry.Button:SetText(Locale.Lookup("LOC_PICK_PRESET_ALL"))
    entry.Button:RegisterCallback(Mouse.eLClick, function()
        Controls.PresetPulldown:GetButton():SetText("All")
        m_sCurrentGreatPeopleClass = 'CLASS_ALL'
        Refresh()
    end)

    -- 各伟人分类
    for row in GameInfo.GreatPersonClasses() do
        if IsValidClass(row.GreatPersonClassType) then
            local entry = {}
            Controls.PresetPulldown:BuildEntry("InstanceOne", entry)
            entry.Button:SetText(Locale.Lookup(row.Name))
            entry.Button:RegisterCallback(Mouse.eLClick, function()
                Controls.PresetPulldown:GetButton():SetText(Locale.Lookup(row.Name))
                m_sCurrentGreatPeopleClass = row.GreatPersonClassType
                Refresh()
            end)
        end
    end
    Controls.PresetPulldown:CalculateInternals()
end
```

## 步骤 6：SayWonder 图标网格选择器

类似文明选择界面的图标网格（8-16列），动态计算最佳列数：

```lua
function PopulateIconOptions()
    g_iconPulldownOptions = GetWonderIconOptions(playerID)  -- 返回 {name, tooltip} 数组

    -- 动态计算最佳列数（目标：行数不超过12，留白最少）
    local MIN_COLS, MAX_COLS, MAX_ROWS = 8, 16, 12
    local columns = MAX_COLS
    local nMinBlanks = MAX_COLS * MAX_ROWS
    for i = MIN_COLS, MAX_COLS do
        local nRows = math.ceil(#g_iconPulldownOptions / i)
        local remainder = #g_iconPulldownOptions % i
        local nBlanks = 0
        if remainder > 0 then nBlanks = i - remainder end
        if nBlanks < nMinBlanks and nRows <= MAX_ROWS then
            nMinBlanks = nBlanks
            columns = i
        end
    end

    -- 分批渲染（每 N 行一段）
    local sectionTable = {}
    ContextPtr:BuildInstanceForControl("IconOptionRowInstance",
        sectionTable, Controls.IconOptionStack)
    sectionTable.IconOptionRowStack:SetWrapWidth(100 * columns)

    for i, pair in ipairs(g_iconPulldownOptions) do
        local controlTable = {}
        ContextPtr:BuildInstanceForControl("IconOptionInstance",
            controlTable, sectionTable.IconOptionRowStack)

        controlTable.Icon:SetIcon(pair.name, 80)

        -- 检查奇观状态
        if wondersHasBuilt[pair.tooltip] then
            controlTable.IconState:SetText('[COLOR:ResGoldLabelCS]已建成[ENDCOLOR]')
            controlTable.IconOptionButton:SetEnabled(false)
        elseif pPlayer:GetProperty('NW_AM_SAY_WONDER_' .. pair.tooltip) then
            controlTable.IconState:SetText('[COLOR:ResScienceLabelCS]已预言[ENDCOLOR]')
            controlTable.IconOptionButton:SetEnabled(false)
        else
            controlTable.IconOptionButton:RegisterCallback(Mouse.eLClick, OnIconOption)
            controlTable.IconOptionButton:SetVoids(i, 1)
            controlTable.StateContainer:SetHide(true)
        end

        -- Tooltip
        if pair.tooltip then
            local tooltip = ToolTipHelper.GetToolTip(pair.tooltip, Game.GetLocalPlayer())
                or Locale.Lookup(pair.tooltip)
            controlTable.IconOptionButton:SetToolTipString(tooltip)
        end
    end

    -- 动态调整窗口大小
    Controls.Window:SetSizeX(100 * columns + 30)
    Controls.OptionsStack:SetWrapWidth(100 * columns + 8)
    CalculateAllSizes()
end
```

## 步骤 7：Gameplay 端数据保存（回合开始保存）

```lua
-- 面板关闭时不丢失临时数据
function LocalPlayerTurnBegin()
    if ContextPtr:IsHidden() then
        SaveTempGreatPersonInfo()
    end
end

function SaveTempGreatPersonInfo()
    if m_kCacheGreatPersonAvailable and Players[Game.GetLocalPlayer()]:IsTurnActive() then
        UI.RequestPlayerOperation(Game.GetLocalPlayer(),
            PlayerOperations.EXECUTE_SCRIPT, {
                OnStart = 'Laterano_SetProperty',
                Key = 'kPlayerRecruitableGP',
                Value = m_kCacheGreatPersonAvailable
            }
        )
        m_kCacheGreatPersonAvailable = nil
    end
end

Events.LocalPlayerTurnBegin.Add(LocalPlayerTurnBegin)
```

## 初始化函数模板

```lua
function Initialize()
    ContextPtr:SetHide(true)
    ContextPtr:SetInitHandler(OnInit)           -- reload 处理
    ContextPtr:SetInputHandler(OnInputHandler, true)  -- ESC关闭

    -- 按钮回调
    Controls.ConfirmButton:RegisterCallback(Mouse.eLClick, OnConfirm)
    Controls.Header_CloseButton:RegisterCallback(Mouse.eLClick, Close)
    Controls.SlideAnim:RegisterEndCallback(OnAnimEnd)

    -- 打开入口
    LuaEvents.MyPanel_TogglePopup.Add(OnTogglePanel)
    LuaEvents.MyPanel_Opened.Add(CloseOtherPanels)

    -- 外部面板互斥
    LuaEvents.TechTree_OpenTechTree.Add(Close)
    LuaEvents.CivicsTree_OpenCivicsTree.Add(Close)
    -- ... 全量互斥列表
end
Initialize()
```

## 设计要点

1. **LuaEvents 触发开闭**：入口按钮调用 `LuaEvents.Xxx()`，面板监听 `LuaEvents.Xxx.Add(OnTogglePanel)`，解耦入口和面板
2. **面板互斥**：打开本面板时关闭其他面板（CloseOtherPanels）；同时监听外部面板事件来关闭自己
3. **QueuePopup vs SetHide**：需要遮盖层时用 QueuePopup + Screens parent；简单浮动用 SetHide
4. **动画延迟隐藏**：在 SlideAnim EndCallback 中才 SetHide(true)，让关闭动画播放完成
5. **数据显示模式**：打开时调用 Refresh() 重新读取 Property/GameInfo 数据
6. **Reload 恢复**：`ContextPtr:SetInitHandler(OnInit)` 处理游戏重载时恢复面板
7. **ESC 关闭**：`ContextPtr:SetInputHandler(OnInputHandler, true)` 捕获 ESC 键
8. **ToolTipHelper.GetToolTip**：获取游戏对象的自动 tooltip 文本
9. **SetVoids 传递索引**：用于 InstanceManager 生成的按钮在回调中识别是哪一个实例
10. **WrapWidth 自动换行**：配合动态列数控制图标网格布局

---

## XML 配合

### 用到的 XML 文件

| 来源 Mod | XML 文件路径 | 面板类型 |
|----------|------------|---------|
| Majo no Tabitabi (3017462977) | `UI/Additions/WitchBook.xml`（推断） | 全屏 Image 承载翻页书 |
| Laterano | `UI/Additions/ExtraBeliefPanel.xml`（推断） | 标准弹窗框架 |
| Amphoreus 翁法罗斯 (3597437530) | `UI/Additions/SayWonderPanel.xml`（推断） | 图标网格选择器 |
| EagleUnion (2966077687) | `UI/Additions/EagleUnionExtraPanel.xml` | 侧滑动面板 |
| Iberia XP (3391173367) | `UI/Additions/OphEventChoice_Iberia.xml`（推断） | 事件选择弹窗 |

### 控件 ID 对照（WitchBook 全屏模式）

| XML 控件 ID | 类型 | Lua 角色 |
|------------|------|---------|
| `WitchBookUI` | `Image` | 全屏背景图（1280×720） |
| `CloseBtn` | `Button` | 关闭按钮（右上角） |
| `MainContainer` | `Container` | 主内容区域 |
| `PageStackLeft` / `PageStackRight` | `Stack` | 左右页容器（InstanceManager 填充） |
| `PageNum` | `Label` | 页码显示（"1/5"） |
| `PageUpButton` / `PageDownButton` | `Button` | 翻页按钮 |
| `BookPage` (Instance) | `Container` | 书页模板（含 PageTitleText + PageMainText） |

### 控件 ID 对照（标准弹窗框架模式）

| XML 控件 ID | 类型 | Lua 角色 |
|------------|------|---------|
| `DropShadow` | `Grid` | 阴影容器 |
| `Window` | `Grid` | 弹窗主窗口 |
| `EventTitle` | `Label` | 标题栏文本 |
| `Header_CloseButton` | `Button` | 标题栏关闭按钮 |
| `ConfirmButton` | `GridButton` | 底部确认按钮 |

### Instance 模板（LaunchBar 入口按钮）

```xml
<Instance Name="MyPopupEntryItem">
    <Button ID="MyPopupEntryButton" Anchor="L,C" Size="49,49"
            Texture="LaunchBar_Hook_GreatPeopleButton"
            Style="ButtonNormalText" StateOffsetIncrement="0,49"
            ToolTip="LOC_MY_POPUP_TOOLTIP">
        <Image ID="MyPopupEntryIcon" Size="35,35" Anchor="C,C"
               Texture="ICON_MY_CIVILIZATION_32"/>
    </Button>
</Instance>
```

### 可复用 XML

- **全屏 Image 承载模式**：适合故事书、图鉴等以图像为主的界面
- **标准弹窗框架模式**：`DropShadow` + `Window` + `EventPopupTitleBar` + `ScrollPanel` 可复用于任何选择/确认弹窗
- **LaunchBar 入口 Instance**：所有全屏面板都需要一个 LaunchBar 按钮 Instance 作为入口
- 弹窗 Context 和入口按钮 Context 通常在同一个 XML 文件中定义
- 作为独立 Context 注册到 modinfo（AddUserInterfaces）
