# Espionage UI 增强模式（来源：Better Espionage Screen）

从工坊 Mod `872296228`（Better Espionage Screen）提炼的间谍界面重做模式，涵盖滑入面板动画、双模式选择器、区域过滤、间谍全景概览、任务历史等完整技巧。

---

## 源文件

| 文件 | 角色 |
|------|------|
| `UI/Choosers/EspionageChooser.lua` | 间谍目的地/任务选择器（Slide Panel） |
| `UI/Choosers/EspionageChooser.xml` | 选择器布局：DestinationInstance、MissionInstance、DistrictInstance |
| `UI/PartialScreens/EspionageOverview.lua` | 间谍全景面板：特工/城市活动/任务历史三页签 |
| `UI/PartialScreens/EspionageOverview.xml` | 全景布局：OperativeInstance、CityInstance、MissionHistoryInstance |
| `UI/EspionageSupport.lua` | 共用函数：GetFormattedOperationDetailText、RefreshMissionStats、GetSpyRankNameByLevel |
| `Text/BES_Text.xml` | 新增文本 |

---

## 模式一：Slide Panel 动画系统

### 1.1 AnimSidePanelSupport

游戏内置的动画装饰器，封装滑入/滑出逻辑：

```lua
include("AnimSidePanelSupport");

-- 在 Initialize 中创建
m_AnimSupport = CreateScreenAnimation(Controls.SlideAnim);

-- 注册系统更新 + 输入处理
Events.SystemUpdateUI.Add(m_AnimSupport.OnUpdateUI);
ContextPtr:SetInputHandler(m_AnimSupport.OnInputHandler, true);

-- 使用
function Open()
    -- ... 准备数据 ...
    if not m_AnimSupport:IsVisible() then
        m_AnimSupport:Show();
    end
end

function Close()
    if m_AnimSupport:IsVisible() then
        m_AnimSupport:Hide();
    end
end
```

### 1.2 SlideAnim XML 模板

```xml
<SlideAnim Style="ChooserAnim">
    <!-- 全部内容放在 SlideAnim 内部 -->
    <Grid Anchor="C,T" Size="parent+7,102" ...>
        <!-- 城市横幅等 -->
    </Grid>
    <!-- ...其他控件... -->
</SlideAnim>
```

**与普通弹出面板的区别：** Slide Panel 使用 `AnimSidePanelSupport` 而非 `QueuePopup`，适合需要从屏幕边缘滑入的面板。

---

## 模式二：双模式选择器（Destination vs Mission）

### 2.1 模式枚举 + 切换

```lua
local EspionageChooserModes = {
    DESTINATION_CHOOSER = 0;   -- 选目标城市
    MISSION_CHOOSER     = 1;   -- 选任务
};

-- Open 中根据 InterfaceMode 决定模式
function Open()
    if UI.GetInterfaceMode() == InterfaceModeTypes.SPY_TRAVEL_TO_CITY then
        m_currentChooserMode = EspionageChooserModes.DESTINATION_CHOOSER;
    else
        m_currentChooserMode = EspionageChooserModes.MISSION_CHOOSER;
    end
    -- ...
end
```

### 2.2 RefreshTop / RefreshBottom 分离

两个模式下有完全不同的控件显隐逻辑，通过分离 Top/Bottom 刷新简化：

```lua
function Refresh()
    RefreshTop();
    RefreshBottom();
end

function RefreshTop()
    if m_currentChooserMode == EspionageChooserModes.DESTINATION_CHOOSER then
        Controls.Title:SetText(Locale.ToUpper("LOC_ESPIONAGECHOOSER_PANEL_HEADER"));
        Controls.ActiveBoostContainer:SetHide(true);
        Controls.NoActiveBoostLabel:SetHide(true);
        if m_city then
            AddDistrictIcons(Controls, m_city);
            Controls.DistrictInfo:SetHide(false);
            Controls.SelectACityMessage:SetHide(true);
            Controls.MissionGrid:SetOffsetX(DESTINATION_CHOOSER_MISSIONSCROLLPANEL_OFFSET_X);
            UpdateCityBanner(m_city);
        else
            Controls.BannerBase:SetHide(true);
            Controls.DistrictInfo:SetHide(true);
            Controls.SelectACityMessage:SetHide(false);
        end
    else  -- MISSION_CHOOSER
        Controls.Title:SetText(Locale.ToUpper("LOC_ESPIONAGECHOOSER_CHOOSE_MISSION"));
        Controls.SelectACityMessage:SetHide(true);
        Controls.DistrictInfo:SetHide(true);
        Controls.MissionGrid:SetOffsetX(0);
        Controls.BannerBase:SetHide(false);
        UpdateCityBanner(m_city);
        -- 显示信息收集加成
        local boostedTurnsRemaining = playerDiplomacy:GetSourceTurnsRemaining(m_city);
        if boostedTurnsRemaining > 0 then
            Controls.ActiveBoostContainer:SetHide(false);
            Controls.NoActiveBoostLabel:SetHide(true);
        end
    end
end
```

---

## 模式三：区域图标过滤系统

### 3.1 复选框式过滤面板

```lua
local m_DistrictFilterChoiceIM = InstanceManager:new(
    "DistrictsFilterInstance", "DistrictsFilterButton", Controls.DistrictsFilterStack);
local m_DistrictFilterSelection = {}

function BuildDistrictFilterPanel()
    m_DistrictFilterChoiceIM:ResetInstances()
    for row in GameInfo.Districts() do
        if row.DistrictType ~= "DISTRICT_CITY_CENTER"
            and row.DistrictType ~= "DISTRICT_WONDER" then
            -- 排除替代区域（用 DistrictReplaces 表判断）
            local validRow = true
            for replcRow in GameInfo.DistrictReplaces() do
                if replcRow.CivUniqueDistrictType == row.DistrictType then
                    validRow = false; break
                end
            end
            if validRow then
                local kInstance = m_DistrictFilterChoiceIM:GetInstance()
                kInstance.DistrictIcon:SetIcon("ICON_" .. row.DistrictType);
                kInstance.DistrictLabel:SetText(Locale.Lookup(row.Name));
                kInstance.DistrictsFilterButton:RegisterCallback(Mouse.eLClick, function()
                    if not m_DistrictFilterSelection[row.DistrictType] then
                        kInstance.DistrictsFilterButton:SetTextureOffsetVal(0, 24)  -- 选中态
                        m_DistrictFilterSelection[row.DistrictType] = true
                    else
                        kInstance.DistrictsFilterButton:SetTextureOffsetVal(0, 0)   -- 未选态
                        m_DistrictFilterSelection[row.DistrictType] = false
                    end
                    Refresh();
                end)
            end
        end
    end
    Controls.DistrictsFilterStack:CalculateSize()
    Controls.DistrictsFilterGrid:DoAutoSize()
end
```

### 3.2 过滤应用

```lua
function CheckDistrictFilters(pCity)
    if table.count(m_DistrictFilterSelection) > 0 then
        for district, isChecked in pairs(m_DistrictFilterSelection) do
            if isChecked and not hasDistrict(pCity, district) then
                return false   -- 只要有一个选中但城市没有该区域 → 不显示
            end
        end
    end
    return true
end
```

### 3.3 hasDistrict 辅助函数（处理独特区域替代）

```lua
function hasDistrict(city, districtType)
    for i, district in city:GetDistricts():Members() do
        if district:IsComplete() and not district:IsPillaged() then
            local districtInfo = GameInfo.Districts[district:GetType()];
            local currentDistrictType = districtInfo.DistrictType

            -- 独特区域→映射回基础类型（Hansa → Industrial Zone）
            local replaces = GameInfo.DistrictReplaces[districtInfo.Hash];
            if replaces then
                currentDistrictType = GameInfo.Districts[replaces.ReplacesDistrictType].DistrictType
            end

            if currentDistrictType == districtType then return true end
        end
    end
    return false
end
```

---

## 模式四：可滚动区域图标列表

当一个城市有大量区域时，显示左右箭头按钮来滚动：

```lua
local NUM_DISTRICTS_WITHOUT_SCROLL = 7;

-- 渲染时判断是否需要滚动
if pCityDistricts:GetNumDistricts() > NUM_DISTRICTS_WITHOUT_SCROLL then
    cityInstance.CurrentScrollPos = 1;
    cityInstance.DistrictsScrollLeftButton:SetHide(false);
    cityInstance.DistrictsScrollLeftButton:SetDisabled(true);   -- 初始在左端
    cityInstance.DistrictsScrollRightButton:SetHide(false);
    -- 隐藏超出可见范围的图标
    for each district_icon beyond position 5 (留 2 给箭头) ...
end

-- 滚动逻辑
function OnDistrictsRightButton(kCityInstance)
    kCityInstance.CurrentScrollPos = kCityInstance.CurrentScrollPos + 1;
    local kChildren = kCityInstance.CityDistrictStack:GetChildren();
    kCityInstance.DistrictsScrollLeftButton:SetDisabled(false);
    if (kCityInstance.CurrentScrollPos + NUM_DISTRICTS_WITHOUT_SCROLL - 2) >= #kChildren then
        kCityInstance.DistrictsScrollRightButton:SetDisabled(true);
    end
    -- Show/hide by position range
end
```

---

## 模式五：PullDown 过滤器（文明/类别）

```lua
local m_filterList = {};
local m_filterCount = 0;
local m_filterSelected = 1;

function RefreshFilters()
    Controls.DestinationFilterPulldown:ClearEntries();
    m_filterList = {};
    m_filterCount = 0;

    -- 添加 "全部"
    AddFilter(Locale.Lookup("LOC_ESPIONAGECHOOSER_FILTER_ALL"), function(a) return true; end);

    -- 遍历玩家添加单项过滤器
    for i, pPlayer in ipairs(players) do
        if ShouldAddToFilter(pPlayer) then
            local playerConfig = PlayerConfigurations[pPlayer:GetID()];
            local name = Locale.Lookup(GameInfo.Civilizations[playerConfig:GetCivilizationTypeID()].Name);
            AddFilter(name, function(a) return a:GetID() == pPlayer:GetID() end);
        end
    end

    -- "城邦" + "国际"
    AddFilter(Locale.Lookup("LOC_HUD_REPORTS_CITY_STATE"), function(a) return a:IsMinor() end);
    AddFilter(Locale.Lookup("LOC_ESPIONAGECHOOSER_FILTER_INTERNATIONAL"),
        function(a) return a:GetID() ~= Game.GetLocalPlayer() end);

    -- 构建条目
    for index, filter in ipairs(m_filterList) do
        AddFilterEntry(index);
    end

    Controls.FilterButton:SetText(m_filterList[m_filterSelected].FilterText);
    Controls.DestinationFilterPulldown:CalculateInternals();
    UpdateFilterArrow();
end

function AddFilter(filterName, filterFunction)
    -- 去重检查
    for index, filter in ipairs(m_filterList) do
        if filter.FilterText == filterName then return; end
    end
    m_filterCount = m_filterCount + 1;
    m_filterList[m_filterCount] = {FilterText=filterName, FilterFunction=filterFunction};
end

function AddFilterEntry(filterIndex)
    local filterEntry = {};
    Controls.DestinationFilterPulldown:BuildEntry("FilterEntry", filterEntry);
    filterEntry.Button:SetText(m_filterList[filterIndex].FilterText);
    filterEntry.Button:SetVoids(i, filterIndex);
end
```

**PullDown XML 结构：**

```xml
<PullDown ID="DestinationFilterPulldown" ConsumeMouse="0" Offset="5,158"
    Anchor="L,T" Size="245,32" AutoSizePopUp="1" AutoFlip="1" ScrollThreshold="400">
    <ButtonData>
        <GridButton ID="FilterButton" ... />
    </ButtonData>
    <GridData InnerPadding="15,15" ... />
    <ScrollPanelData ... />
    <StackData StackGrowth="Bottom" ... />
    <InstanceData Name="FilterEntry">
        <GridButton Anchor="L,T" ID="Button" Size="0,26" ... />
    </InstanceData>
</PullDown>
```

---

## 模式六：PartialScreen 架构

### 6.1 PartialScreenHooks

Better Espionage Screen 使用 PartialScreen 而非 Popup：

```lua
function Initialize()
    -- Lua 事件系统：与 LaunchBar 或外部系统通信
    LuaEvents.PartialScreenHooks_OpenEspionage.Add(OnOpen);
    LuaEvents.PartialScreenHooks_CloseEspionage.Add(OnClose);
    LuaEvents.PartialScreenHooks_CloseAllExcept.Add(OnCloseAllExcept);
    -- ...
end

function OnCloseAllExcept(contextToStayOpen)
    if contextToStayOpen ~= ContextPtr:GetID() then
        Close();
    end
end
```

### 6.2 InterfaceMode 驱动显隐

```lua
Events.InterfaceModeChanged.Add(OnInterfaceModeChanged);

function OnInterfaceModeChanged(oldMode, newMode)
    -- 当切换到无关模式时关闭面板
    if oldMode == InterfaceModeTypes.SPY_CHOOSE_MISSION
        and newMode ~= InterfaceModeTypes.SPY_TRAVEL_TO_CITY then
        if m_AnimSupport:IsVisible() then Close(); end
    end
    -- 当切换到间谍模式时打开
    if newMode == InterfaceModeTypes.SPY_TRAVEL_TO_CITY then Open(); end
    if newMode == InterfaceModeTypes.SPY_CHOOSE_MISSION then Open(); end
end
```

---

## 模式七：任务列表（可用/禁用混合显示）

### 7.1 可用任务

```lua
function AddAvailableOffensiveOperation(operation, result, pTargetPlot)
    local missionInstance = AddOffensiveOperation(operation, result, pTargetPlot);
    missionInstance.MissionDetails:SetText(
        GetFormattedOperationDetailText(operation, m_spy, m_city));
    missionInstance.MissionDetails:SetColorByName("White");

    -- 只在 Mission Chooser 模式可点击
    if m_currentChooserMode == EspionageChooserModes.MISSION_CHOOSER then
        missionInstance.MissionButton:RegisterCallback(Mouse.eLClick,
            function() OnMissionSelected(operation, missionInstance, pTargetPlot); end);
    end
    -- Destination Chooser 模式不可点击（仅预览）
    if m_currentChooserMode == EspionageChooserModes.DESTINATION_CHOOSER then
        missionInstance.MissionButton:SetDisabled(true);
        missionInstance.MissionButton:SetVisState(0);
    end
end
```

### 7.2 禁用任务（显示原因）

```lua
function AddDisabledOffensiveOperation(operation, result, targetCityPlot)
    local missionInstance = AddOffensiveOperation(operation, result, targetCityPlot);

    -- 从 CanStartOperation 的失败原因中提取文本
    if result and result[UnitOperationResults.FAILURE_REASONS] then
        local failureReasons = result[UnitOperationResults.FAILURE_REASONS];
        local missionDetails = "";
        for i, reason in ipairs(failureReasons) do
            missionDetails = (missionDetails == "") and reason
                or missionDetails .. "[NEWLINE]" .. reason;
        end
        missionInstance.MissionDetails:SetText(missionDetails);
        missionInstance.MissionDetails:SetColorByName("Red");
    end
    missionInstance.MissionButton:SetDisabled(true);
end
```

### 7.3 任务统计信息渲染

```lua
function RefreshMissionStats(parentControl, operation, result, spy, city, targetPlot)
    -- 回合数
    local turnsToComplete = UnitManager.GetTimeToComplete(eOperation, spy);
    parentControl.TurnsToCompleteLabel:SetText(turnsToComplete);

    -- 成功率（含颜色分级）
    if operation.Hash ~= UnitOperationTypes.SPY_COUNTERSPY then
        local resultProbability = UnitManager.GetResultProbability(eOperation, spy, targetPlot);
        local probability = (resultProbability["ESPIONAGE_SUCCESS_UNDETECTED"] or 0)
            + (resultProbability["ESPIONAGE_SUCCESS_MUST_ESCAPE"] or 0);
        probability = math.floor((probability * 100) + 0.5);
        parentControl.ProbabilityLabel:SetText(probability .. "%");

        if probability > 85 then      parentControl.ProbabilityLabel:SetColorByName("OperationChance_Green");
        elseif probability > 65 then  parentControl.ProbabilityLabel:SetColorByName("OperationChance_YellowGreen");
        elseif probability > 45 then  parentControl.ProbabilityLabel:SetColorByName("OperationChance_Yellow");
        elseif probability > 25 then  parentControl.ProbabilityLabel:SetColorByName("OperationChance_Orange");
        else                           parentControl.ProbabilityLabel:SetColorByName("OperationChance_Red");
        end
    end

    -- 目标区域名称 + 图标
    -- 根据 result[UnitOperationResults.PLOTS] 匹配城市区域...
end
```

---

## 模式八：自制 PullDown 箭头状态

```lua
function UpdateFilterArrow()
    if Controls.DestinationFilterPulldown:IsOpen() then
        Controls.PulldownOpenedArrow:SetHide(true);
        Controls.PulldownClosedArrow:SetHide(false);
    else
        Controls.PulldownOpenedArrow:SetHide(false);
        Controls.PulldownClosedArrow:SetHide(true);
    end
end

-- FilterButton 点击时调用
Controls.FilterButton:RegisterCallback(Mouse.eLClick, UpdateFilterArrow);
```

---

## 模式九：间谍状态分类渲染

OperativeInstance 用一个 Grid 包含四种状态布局，通过 `SetTextureOffsetVal` + `SetHide(true/false)` 切换：

```lua
function AddOperative(spy)
    local operationType = spy:GetSpyOperation();
    if operationType == -1 then
        -- 等待分配
        instance.Top:SetTextureOffsetVal(0, 73);    -- 切换到等待背景
        instance.AwaitingAssignmentStack:SetHide(false);
        instance.ActiveMissionContainer:SetHide(true);
        instance.TravellingContainer:SetHide(true);
        instance.CapturedContainer:SetHide(true);
    else
        -- 执行任务中
        instance.Top:SetTextureOffsetVal(0, 0);     -- 默认背景
        -- 显示任务名称、进度条、剩余回合、图标等
        instance.AwaitingAssignmentStack:SetHide(true);
        instance.ActiveMissionContainer:SetHide(false);
    end
end

function AddOffMapOperative(spy)
    -- 移动中
    instance.Top:SetTextureOffsetVal(0, 146);
    instance.TravellingContainer:SetHide(false);
end

function AddCapturedOperative(spy, playerCapturedBy)
    -- 被捕获
    instance.Top:SetTextureOffsetVal(0, 146);
    instance.CapturedContainer:SetHide(false);
    -- 显示请求交易按钮（需要不为战争状态且无待定交易）
end
```

---

## 模式十：被捕获间谍交易

```lua
function OnAskForOperativeTradeClicked(capturingPlayerID, capturedSpyID)
    if not DealManager.HasPendingDeal(Game.GetLocalPlayer(), capturingPlayerID) then
        DealManager.ClearWorkingDeal(DealDirection.OUTGOING, Game.GetLocalPlayer(), capturingPlayerID);
        local pDeal = DealManager.GetWorkingDeal(DealDirection.OUTGOING, Game.GetLocalPlayer(), capturingPlayerID);
        if pDeal ~= nil then
            local pDealItem = pDeal:AddItemOfType(DealItemTypes.CAPTIVE, capturingPlayerID);
            if pDealItem ~= nil then
                pDealItem:SetValueType(capturedSpyID);
                pDealItem:SetLocked(true);
            end
        end
        DiplomacyManager.RequestSession(Game.GetLocalPlayer(), capturingPlayerID, "MAKE_DEAL");
    end
end
```

**注意：** 如果处于战争状态或无待定交易，按钮应禁用并显示原因。

---

## 共用函数（EspionageSupport.lua）

### GetSpyRankNameByLevel

```lua
function GetSpyRankNameByLevel(level)
    if level == 4 then return "LOC_ESPIONAGE_LEVEL_4_NAME";
    elseif level == 3 then return "LOC_ESPIONAGE_LEVEL_3_NAME";
    elseif level == 2 then return "LOC_ESPIONAGE_LEVEL_2_NAME";
    else return "LOC_ESPIONAGE_LEVEL_1_NAME"; end
end
```

### GetFormattedOperationDetailText

不同任务类型的详细信息格式不同（如偷钱显示城市名），通过 OperationType 分支处理：

```lua
function GetFormattedOperationDetailText(operation, spy, city)
    local sOperationDetails = UnitManager.GetOperationDetailText(
        operation.Index, spy, Map.GetPlot(city:GetX(), city:GetY()));
    if operation.OperationType == "UNITOPERATION_SPY_SIPHON_FUNDS" then
        return Locale.Lookup("LOC_SPYMISSIONDETAILS_UNITOPERATION_SPY_SIPHON_FUNDS",
            Locale.ToUpper(city:GetName()), sOperationDetails);
    elseif sOperationDetails ~= "" then
        return sOperationDetails;
    else
        return Locale.Lookup("LOC_SPYMISSIONDETAILS_" .. operation.OperationType);
    end
end
```

---

## 事件监听速查

| 事件 | 用途 |
|------|------|
| `Events.InterfaceModeChanged` | 间谍模式切换时打开/关闭面板 |
| `Events.UnitSelectionChanged` | 选择间谍时自动切换模式 |
| `Events.UnitActivityChanged` | 间谍状态变化时刷新 |
| `Events.LocalPlayerTurnEnd` | 热座模式关闭 |
| `Events.SystemUpdateUI` | 驱动 SlideAnim 动画帧 |
| `Events.SpyAdded` / `Events.SpyRemoved` | 刷新特工列表 |
| `Events.UnitOperationStarted` | 任务开始后刷新 |
| `Events.DiplomacyDealEnacted` | 交易完成后刷新（可能涉及被俘间谍） |
| `LuaEvents.EspionagePopup_MissionBriefingClosed` | 任务详情关闭时清理选择边框 |
| `LuaEvents.PartialScreenHooks_OpenEspionage` | LaunchBar 打开请求 |
| `LuaEvents.PartialScreenHooks_CloseAllExcept` | 集中关闭除指定面板外所有面板 |

---

## 关键 include

```lua
include("InstanceManager");
include("AnimSidePanelSupport");
include("SupportFunctions");
include("EspionageSupport");      -- 自定义共用函数
include("TabSupport");
include("Colors");
```

---

## XML 配合

### XML 文件

| 文件 | 路径 | 角色 |
|------|------|------|
| 选择器布局 | `Base/Assets/UI/Choosers/EspionageChooser.xml` | Slide Panel 目的地/任务选择 |
| 全景布局 | `Base/Assets/UI/PartialScreens/EspionageOverview.xml` | PartialScreen 三页签全景 |

### EspionageChooser.xml 核心控件

| 控件 ID | 控件类型 | 用途 |
|---------|---------|------|
| `SlideAnim` (Style="ChooserAnim") | SlideAnim | 滑入动画根控件 |
| `BannerBase` | Grid | 城市横幅（含 `BannerDarker`/`BannerLighter`） |
| `CityName` | Label | 当前城市名 |
| `DistrictInfo` | Grid | 区域图标行 |
| `DistrictIconStack` | Stack | 区域图标堆叠（`StackGrowth="Right"`） |
| `DistrictsScrollLeftButton` / `DistrictsScrollRightButton` | Button | 区域图标左右滚动箭头 |
| `SelectACityMessage` | Label | 提示"选择一个城市" |
| `ActiveBoostContainer` | Container | 信息收集加成容器 |
| `NoActiveBoostLabel` | Label | 无加成提示 |
| `DestinationFilterPulldown` | PullDown | 目标城市过滤器（文明/全部/城邦） |
| `FilterButton` | GridButton | 过滤器按钮 |
| `DistrictsFilterShownButton` | Button | 区域过滤开关按钮 |
| `DistrictsFilterGrid` | Grid | 区域复选框过滤面板（`Hidden="1"`） |
| `DistrictsFilterStack` | Stack | 过滤项堆叠 |
| `DestinationPanel` | ScrollPanel | 目标城市列表 |
| `DestinationStack` | Stack | 城市行堆叠 |
| `MissionGrid` | Grid | 任务面板 |
| `MissionScrollPanel` | ScrollPanel | 任务列表滚动区 |
| `MissionStack` | Stack | 任务行堆叠 |
| `ConfirmButton` / `CancelButton` | GridButton | 确认/取消按钮 |
| `CloseButton` | Button | 关闭按钮 |
| `PulldownOpenedArrow` / `PulldownClosedArrow` | Image | PullDown 自定义箭头 |

### EspionageOverview.xml 核心控件

| 控件 ID | 控件类型 | 用途 |
|---------|---------|------|
| `SlideAnim` (Style="RundownAnimBG") | SlideAnim | 全景背景动画 |
| `TabContainer` | Container | 标签按钮容器 |
| `OperativesTabButton` / `CityActivityTabButton` / `MissionHistoryTabButton` | GridButton | 三个 Tab 按钮 |
| `OperativeTabContainer` | Container | Tab1 特工列表 |
| `OperativeScrollPanel` | ScrollPanel | 特工滚动区 |
| `OperativeStack` | Stack | 特工行堆叠 |
| `NoOperativesLabel` | Label | 无特工占位 |
| `CityActivityTabContainer` | Container | Tab2 城市活动 |
| `CityActivityScrollPanel` | ScrollPanel | 城市活动滚动区 |
| `CityActivityStack` | Stack | 城市行堆叠 |
| `NoCitiesLabel` | Label | 无城市占位 |
| `MissionHistoryTabContainer` | Container | Tab3 任务历史 |
| `MissionHistoryScrollPanel` | ScrollPanel | 历史滚动区 |
| `MissionHistoryStack` | Stack | 历史行堆叠 |
| `CapturedEnemyOperativeStack` | Stack | 被俘特工堆叠 |
| `CloseButton` | Button | 关闭按钮 |

### Instance 对照表

| Instance | 所属文件 | 用途 |
|----------|---------|------|
| `DestinationInstance` | EspionageChooser | 目标城市行（Banner + DistrictIcons + TravelTime） |
| `MissionInstance` | EspionageChooser | 任务行（Icon + Name + Details + Stats） |
| `CityDistrictInstance` | EspionageChooser | 区域图标（32px） |
| `DistrictsFilterInstance` | EspionageChooser | 区域过滤复选框项 |
| `FilterEntry` | EspionageChooser / EspionageOverview | PullDown 下拉条目 |
| `OperativeInstance` | EspionageOverview | 特工行（4种状态布局：Awaiting/Active/Travelling/Captured） |
| `EnemyOperativeInstance` | EspionageOverview | 敌方特工行（捕获请求交易） |
| `MissionHistoryInstance` | EspionageOverview | 任务历史行（Outcome + Details + District） |
| `CityInstance` | EspionageOverview | 城市活动行（Banner + DistrictIcons + ScrollArrows） |
| `CityDistrictInstance` | EspionageOverview | 城市区域图标（含间谍图标覆盖） |

### 可复用模板：Slide Panel 带过滤器 + 自定义箭头

```xml
<SlideAnim Style="ChooserAnim">
  <!-- 顶部城市横幅 -->
  <Grid Anchor="C,T" Size="parent+7,102" Offset="0,28"
        Texture="DestinationChooser_CurrentSlot"
        SliceCorner="23,23" SliceSize="250,70" SliceTextureSize="308,173">
    <!-- Banner 三联层：Base/Darker/Lighter -->
    <Grid ID="BannerBase" Anchor="C,T" Size="parent-26,33" Texture="CityPanel_BannerBase" ...>
      <Grid ID="BannerDarker" ... />
      <Grid ID="BannerLighter" ... />
      <Label ID="CityName" ... />
    </Grid>
  </Grid>
  <!-- 下拉过滤器 -->
  <PullDown ID="DestinationFilterPulldown" ...>
    <ButtonData><GridButton ID="FilterButton" ... /></ButtonData>
    <GridData ... />
    <ScrollPanelData ... />
    <StackData StackGrowth="Bottom" />
    <InstanceData Name="FilterEntry"><GridButton ID="Button" ... /></InstanceData>
    <!-- 自定义箭头 -->
    <Image ID="PulldownOpenedArrow" ... />
    <Image ID="PulldownClosedArrow" ... />
  </PullDown>
  <!-- 任务/目标内容区 -->
  <ScrollPanel ID="DestinationPanel" ...><Stack ID="DestinationStack" ... /></ScrollPanel>
</SlideAnim>
```
