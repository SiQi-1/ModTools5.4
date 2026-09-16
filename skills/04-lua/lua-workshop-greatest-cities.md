# lua-workshop-greatest-cities — 城市排名全屏界面模式

从工坊 Mod GreatestCities (2494925002) 提炼。展示世界城市排名、奇观列表、历史数据追溯的完整全屏 UI 模式。

---

## 快速索引

| 技术点 | 说明 |
|--------|------|
| **全屏弹窗** | `UIManager:QueuePopup()` + `ContextPtr:SetInputHandler()` |
| **Tab 系统** | Include `TabSupport` + `CreateTabs()` + `AddTabSection()` |
| **排序系统** | `spairs()` 迭代器 + 排序函数表 + 点击列头切换 ASC/DESC |
| **数据持久化** | `serialize()` / `loadstring()` + `GameConfiguration.SetValue()` / `PlayerConfigurations` |
| **叙事性通知** | `NotificationManager.SendNotification()` + `NotificationActivated` 事件 |
| **ReportsList 集成** | 通过 `LuaEvents.ReportsList_OpenXxx.Add()` 挂入游戏报告列表 |

---

## 一、全屏弹窗生命周期

### 1.1 Open / Close

```lua
-- ===========================================================================
-- 入口函数：打开界面
-- ===========================================================================
function Open(tabToOpen, eraToShow)
    UIManager:QueuePopup(ContextPtr, PopupPriority.Medium);
    Controls.ScreenAnimIn:SetToBeginning();
    Controls.ScreenAnimIn:Play();
    UI.PlaySound("UI_Screen_Open");

    -- [数据准备]
    setupData(eraToShow or m_currentEra)

    -- [GUI 状态初始化]
    -- ...
end

-- ===========================================================================
-- 出口函数：关闭界面
-- ===========================================================================
function Close()
    if not ContextPtr:IsHidden() then
        UI.PlaySound("UI_Screen_Close");
    end
    UIManager:DequeuePopup(ContextPtr);
end
```

### 1.2 InputHandler（ESC 关闭）

```lua
function OnInputHandler(pInputStruct)
    local uiMsg = pInputStruct:GetMessageType();
    if uiMsg == KeyEvents.KeyUp then
        local uiKey = pInputStruct:GetKey();
        if uiKey == Keys.VK_ESCAPE then
            if ContextPtr:IsHidden() == false then
                Close();
                return true;
            end
        end
    end
    return false;
end
```

### 1.3 Initialize 注册

```lua
function Initialize()
    -- UI Callbacks
    ContextPtr:SetInitHandler(OnInit);
    ContextPtr:SetInputHandler(OnInputHandler, true);
    Controls.CloseButton:RegisterCallback(Mouse.eLClick, OnCloseButton);
    Controls.CloseButton:RegisterCallback(Mouse.eMouseEnter, function()
        UI.PlaySound("Main_Menu_Mouse_Over");
    end);

    -- Tab 系统
    m_tabs = CreateTabs(Controls.TabContainer, 42, 34, 0xFF331D05);
    AddTabSection("LOC_AKGC_CITIES_TAB_WORLD",  function() ViewPage(1); end);
    AddTabSection("LOC_AKGC_CITIES_TAB_EMPIRE", function() ViewPage(2); end);
    AddTabSection("LOC_AKGC_CITIES_TAB_WONDERS", function() ViewPage(3); end);
    m_tabs.SameSizedTabs(20);
    m_tabs.CenterAlignTabs(-10);

    -- 挂入报告列表
    LuaEvents.ReportsList_OpenGreatestCities.Add(function() Open(); end);

    -- 游戏事件
    Events.LocalPlayerTurnEnd.Add(OnLocalPlayerTurnEnd);
    Events.LoadComplete.Add(OnLoadComplete);
    Events.LoadScreenClose.Add(OnLoadScreenClose);
end
```

---

## 二、Tab 系统

### 2.1 Tab 创建

需要 `include("TabSupport")`。TabSupport 提供了 `CreateTabs()`, `AddTabSection()` 等函数。

```lua
local m_tabIM = InstanceManager:new("TabInstance", "Button", Controls.TabContainer);
local m_tabs  = nil;

-- Tab XML Instance
-- <Instance Name="TabInstance">
--     <GridButton ID="Button" Size="50,34" Style="TabButton" FontSize="14" TextOffset="0,2">
--         <AlphaAnim ID="Selection" Offset="-2,0" Size="parent+3,parent" Speed="4"
--                    AlphaBegin="0" AlphaEnd="1" Cycle="Once" Function="Root" Hidden="1">
--             <GridButton Size="parent,parent" Style="TabButtonSelected"
--                         ConsumeMouseButton="0" ConsumeMouseOver="1" />
--         </AlphaAnim>
--     </GridButton>
-- </Instance>
```

### 2.2 AddTabSection 包装

```lua
local DATA_FIELD_SELECTION = "Selection"

function AddTabSection(name, populateCallback)
    local kTab = m_tabIM:GetInstance();
    kTab.Button[DATA_FIELD_SELECTION] = kTab.Selection;

    local callback = function()
        if m_tabs.prevSelectedControl ~= nil then
            m_tabs.prevSelectedControl[DATA_FIELD_SELECTION]:SetHide(true);
        end
        kTab.Selection:SetHide(false);
        populateCallback();
    end

    kTab.Button:GetTextControl():SetText(Locale.Lookup(name));
    kTab.Button:SetSizeToText(40, 20);
    kTab.Button:RegisterCallback(Mouse.eMouseEnter, function()
        UI.PlaySound("Main_Menu_Mouse_Over");
    end);

    m_tabs.AddTab(kTab.Button, callback);
end
```

### 2.3 Tab 切换逻辑

```lua
function ViewPage(idx)
    if idx == 3 then
        m_kCurrentTab = idx
        ViewWondersPage()
    elseif idx == 2 or idx == 1 then
        m_kCurrentTab = idx
        ViewCitiesPage(idx)
    end
end

function ViewCitiesPage(eGroup)
    if eGroup == nil then eGroup = m_kCurrentTab; end
    m_kCurrentTab = eGroup;

    ResetTabForNewPageContent();   -- 清空滚动面板 + 重置简单行实例
    Controls.CitiesHeaderRow:SetHide(false)
    Controls.WondersHeaderRow:SetHide(true)

    -- 使用 spairs 排序后逐行填入
    for _, city in spairs(tShow, CitiesSortFunctions[m_CitiesListLastSortMode]) do
        local inst = m_CityInfoIM:GetInstance(instance.Top);
        ShowCity(city.rank, city, inst, m_showHistoricEra);
    end

    Controls.Stack:CalculateSize();
    Controls.Scroll:CalculateSize();
end
```

---

## 三、排序系统

### 3.1 spairs 迭代器（排序的 pairs）

```lua
-- ===========================================================================
-- spairs: 返回按键排序的迭代器
-- 来源：https://stackoverflow.com/questions/15706270/sort-a-table-in-lua
-- ===========================================================================
function spairs(t, order_function)
    local keys = {};
    for key, _ in pairs(t) do table.insert(keys, key); end

    if order_function then
        table.sort(keys, function(a,b) return order_function(t, a, b) end)
    else
        table.sort(keys)
    end

    local i = 0;
    return function()
        i = i + 1;
        if keys[i] then return keys[i], t[keys[i]] end
    end
end
```

### 3.2 排序函数表 + 点击切换

```lua
-- 排序函数表（ASC/DESC 成对定义）
CitiesSortFunctions = {
    CitiesSortByRankASC = function(t, a, b)
        return t[a].rank < t[b].rank;
    end
    ,CitiesSortByRankDESC = function(t, a, b)
        return t[a].rank > t[b].rank;
    end
    ,CitiesSortByNameASC = function(t, a, b)
        return LL(t[a].Name) < LL(t[b].Name)
    end
    ,CitiesSortByNameDESC = function(t, a, b)
        return LL(t[a].Name) > LL(t[b].Name)
    end
    ,CitiesSortByPopulationASC = function(t, a, b)
        return t[a].Population > t[b].Population
    end
    ,CitiesSortByPopulationDESC = function(t, a, b)
        return t[a].Population < t[b].Population
    end
    -- ... 更多排序维度
}

-- 点击列头切换 ASC/DESC
function OnCitiesListHeaderClick(control)
    local sorttype = control:GetID()     -- e.g. "CitiesSortByRank"
    if m_CitiesListLastSortMode == sorttype .. "ASC" then
        CitiesListSetSortMode(sorttype .. "DESC")
    else
        CitiesListSetSortMode(sorttype .. "ASC")
    end
    ViewCitiesPage()
end

-- 设置排序模式 + 更新列头箭头指示器
function CitiesListSetSortMode(sortmode)
    m_CitiesListLastSortMode = sortmode
    if string.sub(sortmode, -3) == "ASC" then
        local ctrl = Controls[string.sub(sortmode, 1, string.len(sortmode) - 3)]
        ctrl:SetText(ctrl:GetText() .. "[ICON_PressureUp]")
    else
        local ctrl = Controls[string.sub(sortmode, 1, string.len(sortmode) - 4)]
        ctrl:SetText(ctrl:GetText() .. "[ICON_PressureDown]")
    end
end
```

### 3.3 XML 列头按钮

```xml
<!-- 列头行（在内容上方固定） -->
<Container ID="CitiesHeaderRow" Offset="0,86" Size="parent,26">
    <Image Offset="4,0" Size="parent-8,parent"
           Texture="Controls_GradientSmall" FlipY="1"
           Color="39,89,137,125" />
    <Stack Offset="4,0" StackGrowth="Right" Padding="10">
        <GridButton ID="CitiesSortByRank"       String="LOC_AKGC_COL_RANK"
                    Size="60,parent" Offset="12,0" Style="ReportValueText" />
        <GridButton ID="CitiesSortByOwner"      String="LOC_AKGC_COL_OWNER"
                    Size="60,parent" Offset="0,0"  Style="ReportValueText" />
        <GridButton ID="CitiesSortByName"       String="LOC_AKGC_COL_CITY"
                    Size="240,parent" Offset="0,0" Style="ReportValueText" />
        <GridButton ID="CitiesSortByPopulation" String="LOC_AKGC_COL_POPULATION"
                    Size="110,parent" Offset="0,0" Style="ReportValueText" />
        <GridButton ID="CitiesSortByNumWonders" String="LOC_AKGC_COL_WONDERS"
                    Size="313,parent" Offset="0,0" Style="ReportValueText" />
    </Stack>
</Container>

<!-- 在 Initialize() 中注册点击 -->
Controls.CitiesSortByRank:RegisterCallback(Mouse.eLClick,
    function() OnCitiesListHeaderClick(Controls.CitiesSortByRank); end);
Controls.CitiesSortByName:RegisterCallback(Mouse.eLClick,
    function() OnCitiesListHeaderClick(Controls.CitiesSortByName); end);
-- ... 其余列头
```

---

## 四、数据持久化（Serialize + GameConfiguration）

### 4.1 序列化/反序列化

```lua
include("Serialize");    -- 第三方 serialize 库

-- 序列化；保存到 GameConfiguration（跨玩家、跨存档持久）
function SaveDataToGameSlot(sSlotName, data)
    local sData = serialize(data);
    GameConfiguration.SetValue(sSlotName, sData);
end

-- 反序列化：从 GameConfiguration 加载
function LoadDataFromGameSlot(sSlotName)
    local sData = GameConfiguration.GetValue(sSlotName);
    if sData == nil then return nil; end
    local tTable = loadstring(sData)();   -- deserialize
    return tTable;
end

-- 序列化；保存到 PlayerConfigurations（每玩家独立）
function SaveDataToPlayerSlot(ePlayerID, sSlotName, data)
    local sData = serialize(data);
    PlayerConfigurations[ePlayerID]:SetValue(sSlotName, sData);
end

function LoadDataFromPlayerSlot(ePlayerID, sSlotName)
    local sData = PlayerConfigurations[ePlayerID]:GetValue(sSlotName);
    if sData == nil then return nil; end
    local tTable = loadstring(sData)();
    return tTable;
end
```

### 4.2 可持久化数据类型

| 数据类型 | 用途示例 |
|----------|---------|
| `m_historicData` | 每时代城市排名快照（表套表） |
| `m_wonderHistories` | 每个奇观的建造/摧毁记录 |
| `m_cityHistories` | 每个城市的历史事件列表 |
| `m_cityGIDIndex` | 城市 GID 到 (pID,cID) 的映射 |
| `m_pState` | UI 状态标记（如是否已显示选项提醒） |
| `opt` | 玩家选项设置 |

### 4.3 加载时机

```lua
-- 仅在加载存档时触发（新游戏不触发）
function OnLoadComplete()
    LoadData()    -- 恢复所有持久化数据
end

-- 新游戏 + 加载存档都触发，在此绑定事件处理器
function OnLoadScreenClose()
    HookEventHandlers()
end
```

---

## 五、叙事性通知系统

### 5.1 定义通知类型（XML）

```xml
<GameInfo>
    <Types>
        <Row Type="NOTIFICATION_AKGC_ENDOFERARANK" Kind="KIND_NOTIFICATION"/>
        <Row Type="NOTIFICATION_AKGC_DEFAULTOPTIONS" Kind="KIND_NOTIFICATION"/>
    </Types>
    <Notifications>
        <Row NotificationType="NOTIFICATION_AKGC_ENDOFERARANK"
             SeverityType="MID"
             ExpiresEndOfTurn="false"
             AutoNotify="False"
             GroupType="USER"/>
        <Row NotificationType="NOTIFICATION_AKGC_DEFAULTOPTIONS"
             SeverityType="MID"
             ExpiresEndOfTurn="false"
             AutoNotify="False"
             GroupType="USER"/>
    </Notifications>
</GameInfo>
```

### 5.2 发送通知

```lua
local ENDOFERANOTIFICATION_HASH = GameInfo.Types["NOTIFICATION_AKGC_ENDOFERARANK"].Hash

function RaiseEndOfEraRankingNotification(eraNumber)
    local eraName = GameInfo.Eras[eraNumber].Name
    local notificationData = {}
    notificationData.Message = LL("LOC_AKGC_ENDOFERARANK_NOTIFICATION_HEADER", eraName)
    notificationData.Summary = ""  -- 动态构建
    notificationData.Icon = "ICON_NOTIFICATION_AKGC_ENDOFERARANK"
    notificationData.AlwaysUnique = true

    -- 遍历所有人类玩家，向每人发送定制通知
    local players = Game:GetPlayers();
    for i, pPlayer in ipairs(players) do
        if pPlayer:IsHuman() then
            local playerID = pPlayer:GetID()
            -- ... 构建 playerID 专属的 notificationData.Summary ...
            NotificationManager.SendNotification(
                playerID, ENDOFERANOTIFICATION_HASH, notificationData);
        end
    end
end
```

### 5.3 处理通知点击

```lua
function OnProcessNotification(playerId, notificationId, activatedByUser)
    if playerId == Game.GetLocalPlayer() then
        local notification = NotificationManager.Find(playerId, notificationId);
        if notification ~= nil then
            if notification:GetType() == ENDOFERANOTIFICATION_HASH
               and ContextPtr:IsHidden() then
                NotificationManager.Dismiss(playerId, notificationId);
                Open(1, getCurrentEra() - 1);    -- 打开界面并跳转
            elseif notification:GetType() == DEFAULTOPTIONSNOTIFICATION_HASH
                   and ContextPtr:IsHidden() then
                NotificationManager.Dismiss(playerId, notificationId);
                Open();
                OnButtonShowOptions();           -- 打开选项面板
            end
        end
    end
end

-- 在 Initialize() 中绑定
Events.NotificationActivated.Add(OnProcessNotification);
```

---

## 六、建筑/城市事件追踪

### 6.1 事件绑定（HookEventHandlers）

```lua
function HookEventHandlers()
    Events.WonderCompleted.Add(OnWonderCompleted)
    Events.CityAddedToMap.Add(OnCityAddedToMap)
    Events.CityLiberated.Add(OnCityLiberated)
    Events.CityTransfered.Add(OnCityTransfered)
    Events.CityRemovedFromMap.Add(OnCityRemovedFromMap)
    Events.CityNameChanged.Add(OnCityNameChanged)
    Events.BuildingRemovedFromMap.Add(OnBuildingRemovedFromMap)

    -- Era 变化（兼容不同版本）
    if Game.GetEras ~= nil then
        Events.GameEraChanged.Add(OnGameEraChanged)
    else
        Events.PlayerEraChanged.Add(OnPlayerEraChanged)
    end

    Events.PlayerTurnActivated.Add(OnPlayerTurnActivated);
    Events.NotificationActivated.Add(OnProcessNotification);
end
```

### 6.2 事件记录模式

```lua
cityEventType = {
    Added       = 1,
    Transferred = 2,
    Liberated   = 3,
    Renamed     = 4,
    Removed     = 5,
}

function OnCityAddedToMap(playerID, cityID, ix, iy)
    local cityGID, cityName = getCityGIDandName(playerID, cityID)

    -- 更新索引
    if m_cityGIDIndex == nil then m_cityGIDIndex = {} end
    m_cityGIDIndex[cityGID] = playerID .. "_" .. cityID

    -- 添加历史记录
    if m_cityHistories == nil then m_cityHistories = {} end
    if m_cityHistories[cityGID] == nil then m_cityHistories[cityGID] = {} end

    m_cityHistories[cityGID][#m_cityHistories[cityGID]+1] = {
        turn     = Game.GetCurrentGameTurn(),
        event    = cityEventType.Added,
        playerid = playerID,
        cityid   = cityID,
        name     = cityName,
    }

    SaveDataToGameSlot("AKGCCityHistories", m_cityHistories)
    SaveDataToGameSlot("AKGCCityGIDIndex", m_cityGIDIndex)
end
```

### 6.3 GID 索引模式（坐标定位城市）

```lua
function getCityGIDandName(playerID, cityID)
    local pPlayer = Players[playerID]
    local pCity = pPlayer:GetCities():FindID(cityID)

    if pCity ~= nil then
        return pCity:GetX() .. "_" .. pCity:GetY(), pCity:GetName()
    else
        return "unknown", "unknown"
    end
end

function getCityfromGID(cityGID)
    if m_cityGIDIndex and m_cityGIDIndex[cityGID] then
        res = Split(m_cityGIDIndex[cityGID], "_")
    else
        return nil
    end
    local pPlayer = Players[tonumber(res[1])]
    return pPlayer:GetCities():FindID(tonumber(res[2]))
end
```

---

## 七、Reailkla List 集成

### 7.1 ReportsList Loader（第三方库，由 Infixo 开发）

```lua
include("ReportsList");    -- 提供 AddReport()

function LateInitialize()
    m_ReportButtonIM:ResetInstances();
    local tReports = {};
    for report in GameInfo.RLLReports() do
        local bAdd = true;
        if report.RequiresXP1 and not bIsRiseAndFall then bAdd = false; end
        if report.RequiresXP2 and not bIsGatheringStorm then bAdd = false; end
        if bAdd then table.insert(tReports, report); end
    end

    table.sort(tReports, function(a,b) return a.SortOrder < b.SortOrder; end);
    for _, report in ipairs(tReports) do
        AddReport(report.ButtonLabel,
                  function() Close(); LuaEvents[report.LuaEvent](); end,
                  Controls[report.StackID]);
    end
end
```

### 7.2 自身挂入报告列表

```lua
-- 在 Initialize() 中
LuaEvents.ReportsList_OpenGreatestCities.Add(
    function() Open(); end
);
```

---

## 八、奇观列表渲染模式

### 8.1 奇观发现（遍历所有城市的区域/建造队列）

```lua
function PopulateWondersPage()
    local wonderList = {}

    for i, player in ipairs(PlayerManager:GetAlive()) do
        local pCities = player:GetCities()
        for j, pCity in pCities:Members() do
            if pCity ~= nil then
                local pCityDistricts = pCity:GetDistricts()
                local pCityBuildings = pCity:GetBuildings()
                local pCityBQ = pCity:GetBuildQueue()

                for k, district in pCityDistricts:Members() do
                    if GameInfo.Districts[district:GetType()].DistrictType
                       == "DISTRICT_WONDER" then
                        local plot = Map.GetPlot(district:GetX(), district:GetY())

                        -- 已完成奇观
                        local buildingTypes = pCityBuildings:GetBuildingsAtLocation(
                            plot:GetIndex())
                        for _, buildingType in ipairs(buildingTypes) do
                            if GameInfo.Buildings[buildingType].IsWonder
                               and GameInfo.Buildings[buildingType].MaxWorldInstances == 1 then
                                local wonderData = {}
                                wonderData.WonderID = buildingType
                                wonderData.CityName = pCity:GetName()
                                wonderData.Owner = player:GetID()
                                wonderData.x = district:GetX()
                                wonderData.y = district:GetY()
                                wonderData.Progress = 100
                                table.insert(wonderList, wonderData)
                            end
                        end

                        -- 建造中奇观
                        local contructionTypes = pCityBQ:GetConstructionsAtLocation(
                            plot:GetIndex())
                        for _, contructionType in ipairs(contructionTypes) do
                            if GameInfo.Buildings[contructionType].IsWonder
                               and GameInfo.Buildings[contructionType].MaxWorldInstances == 1 then
                                local cost = pCityBQ:GetBuildingCost(contructionType) or 0
                                local progress = pCityBQ:GetBuildingProgress(contructionType) or 0
                                local wonderData = {}
                                wonderData.WonderID = contructionType
                                wonderData.isUnderConstruction = true
                                wonderData.Progress = (cost > 0) and (progress / cost) or 0
                                table.insert(wonderList, wonderData)
                            end
                        end
                    end
                end
            end
        end
    end

    -- 追加已摧毁的奇观（从历史记录中查找不存在于地图上的）
    if m_wonderHistories then
        for wid, hist in pairs(m_wonderHistories) do
            if not wonderIndex[wid] then
                table.insert(wonderList, {
                    WonderID = wid,
                    isDestroyed = true,
                    -- ... 从历史记录推断城市名和摧毁者
                })
            end
        end
    end
end
```

### 8.2 图片进度条（奇观建造进度覆盖）

```lua
-- 利用 TextureOffset 裁剪图标实现进度条效果
if opt.ShowWonderProgress and wdata.isUnderConstruction then
    local progressFudged = math.min(0.95 * wdata.Progress, 0.99)
    progressFudged = math.max(progressFudged, 0.15)
    local texOX, texOY, texSheet = IconManager:FindIconAtlas(
        wdata.DisplayIcon, inst.WonderProgressIcon:GetSizeX());
    -- 核心：垂直偏移剪掉底部未完成部分
    inst.WonderProgressIcon:SetTexture(
        texOX,
        texOY + (inst.WonderProgressIcon:GetSizeX() * (1 - progressFudged)),
        texSheet);
    inst.WonderProgressIcon:Resize(
        inst.WonderProgressIcon:GetSizeX(),
        inst.WonderProgressIcon:GetSizeY() * progressFudged)
    inst.WonderProgressIcon:SetHide(false)
end
```

需要 XML 中定义 MaskTexture：
```xml
<Image Hidden="1" ID="WonderProgressIcon"
       MaskTexture="akgc_WonderProgressMask.dds"
       Texture="CivDefaults256" Size="128,128"
       Anchor="L,B" Offset="0,0" Color="255,255,255,255"/>
```

---

## 九、城市评分与历史时代导航

### 9.1 评分公式

```lua
function CalculateCityScore(cityData)
    local score = 0
    if cityData.IsHolyCity then score = score + 12 end
    score = score + (cityData.NumWonders or 0) * 25
    score = score + (cityData.Population or 0) * 4
    score = score + (cityData.DistrictsNum or 0) * 2
    score = score + (cityData.NumBuildings or 0) * 1
    score = score + (cityData.NumPlots or 0) * 1
    score = score + (cityData.AmenitiesNetAmount or 0) * 2
    -- 负面影响
    score = score + (cityData.NumPlotsPillaged or 0) * -2
    score = score + (cityData.NumBuildingsPillaged or 0) * -4
    score = score + (cityData.NumDistrictsPillaged or 0) * -8
    score = score + math.floor((1 - (cityData.CityWallHPPercent or 1)) * -10)
    -- "第一"加分
    if cityData.IsHighestGoldPT       then score = score + 10 end
    if cityData.IsHighestFaithPT      then score = score + 10 end
    if cityData.IsHighestCulturePT    then score = score + 10 end
    if cityData.IsHighestSciencePT    then score = score + 10 end
    if cityData.IsHighestProductionPT then score = score + 10 end
    return score
end
```

### 9.2 Era 下拉框（历史快照导航）

```lua
function PopulateComboBox(control, values, selected_value, selection_handler)
    control:ClearEntries();
    for i, v in ipairs(values) do
        local instance = {};
        control:BuildEntry("InstanceOne", instance);
        instance.Button:SetVoid1(i);
        instance.Button:LocalizeAndSetText(v[1]);

        if v[2] == selected_value then
            local button = control:GetButton();
            button:LocalizeAndSetText(v[1]);
        end
    end
    control:CalculateInternals();

    if selection_handler then
        control:RegisterSelectionCallback(
            function(voidValue1, voidValue2, control)
                local option = values[voidValue1];
                local button = control:GetButton();
                button:LocalizeAndSetText(option[1]);
                selection_handler(option[2]);
            end
        );
    end
end
```

---

## 十、选项系统（CheckBox + Slider + 持久化）

### 10.1 默认选项

```lua
opts_defaults = {
    NumWorldCitiesToShow = 10,
    NumOwnCitiesToShow   = 500,
    IncludeMinors        = true,
    ShowWondersForDiscoveredCities = true,
    ShowBestOfBonusesForDiscoveredCities = true,
    DebugMode = false,
    -- ...
}
opt = {}
for k, v in pairs(opts_defaults) do opt[k] = v end
```

### 10.2 选项面板显示 / 保存

```lua
function populateOptionsScreen(options)
    for k, v in pairs(options) do
        if Controls[k.."CBX"] then       -- CheckBox 控件
            Controls[k.."CBX"]:SetDisabled(false)
            PopulateCheckBox(Controls[k.."CBX"], v,
                             function() return true end, nil)
        elseif Controls[k.."Slider"] then -- Slider 控件
            Controls[k.."Slider"]:SetDisabled(false)
            Controls[k.."Val"]:SetDisabled(false)
            Controls[k.."Slider"]:SetValue(math.min(v/500, 1))
            Controls[k.."Val"]:SetText(math.min(v, 500))
        end
    end
end

function updateOptionsFromScreen()
    for k, v in pairs(opt) do
        if Controls[k.."CBX"] then
            opt[k] = Controls[k.."CBX"]:IsSelected()
        elseif Controls[k.."Slider"] then
            local value = Controls[k.."Slider"]:GetValue()
            opt[k] = math.max(math.ceil(value*100)*5, 1)
        end
    end
end

function saveOptions()
    SaveDataToPlayerSlot(Game.GetLocalPlayer(), "AKGCPlayerOptions", opt)
end
```

### 10.3 XML Slider + Label 组合

```xml
<Container Anchor="C,C" Size="650,32" Padding="0">
    <Slider Style="SliderControl" Anchor="R,C" Size="400,13"
            Offset="0,0" SpaceForScroll="0"
            ID="NumWorldCitiesToShowSlider" Disabled="1"/>
    <Label String="10" Style="ShellOptionText" WrapWidth="50"
           Anchor="R,C" ID="NumWorldCitiesToShowVal"
           Offset="430,0" Disabled="1"/>
    <Label String="LOC_AKGC_OPT_NumWorldCitiesToShow"
           Style="DiplomacyCivHeader" WrapWidth="350"
           Anchor="L,C" Offset="0,0" />
</Container>
```

---

## 十一、Options 面板切换模式

在原 UI 上叠加一个全屏遮罩面板：

```lua
function OnButtonShowOptions()
    populateOptionsScreen(opt)
    Controls.WindowTitle:SetText(Locale.ToUpper(LL("LOC_AKGC_BUTTON_OPTIONS_TT")))
    Controls.Options:SetHide(false)     -- 显示选项面板
    ResetTabForNewPageContent()         -- 清空下方内容
end

function OnButtonSettingsCancel()
    Controls.Options:SetHide(true)      -- 隐藏选项面板
    Controls.WindowTitle:SetText(m_windowTitle)
    ViewPage(m_kCurrentTab or 1)        -- 恢复原页面
end

function OnButtonSettingsSave()
    updateOptionsFromScreen()
    saveOptions()
    Controls.WindowTitle:SetText(m_windowTitle)
    Controls.Options:SetHide(true)
    ViewPage(m_kCurrentTab or 1)
end
```

---

## 十二、关键要点速查

### 12.1 文件结构

```
GreatestCities/
├── GreatestCities.lua           -- 主 UI 逻辑（~2800 行）
├── GreatestCities.xml           -- UI 结构 + Instance 模板
├── AKGC_DefaultOptions.lua      -- 默认选项表
├── Serialize.lua                -- 序列化/反序列化库
├── RLL/
│   └── ReportsListLoader.lua    -- 挂入游戏报告列表
├── AKGC_Notifications.xml       -- 通知类型定义
└── Text/
    └── AKGC_Text.xml            -- 本地化文本
```

### 12.2 核心 Includes

| Include | 来源 | 用途 |
|---------|------|------|
| `InstanceManager` | 系统 | 列表行复用 |
| `SupportFunctions` | 系统 | `TruncateString` |
| `TabSupport` | 系统 | 标签页框架 |
| `CitySupport` | 系统 | `GetCityData()` |
| `Civ6Common` | 系统 | `GetYieldString()` |
| `Serialize` | 自备 | 数据序列化 |
| `ReportsList` | 第三方 | 挂入报告列表 |

### 12.3 数据流

```
游戏事件 → HookEventHandlers()
  ├─ OnCityAddedToMap / OnWonderCompleted / ...
  ├─ 记录到 m_cityHistories / m_wonderHistories
  └─ SaveDataToGameSlot() 持久化

打开 UI → Open()
  ├─ buildCityList() 构建当前城市数据
  ├─ ViewPage() 排序+渲染
  └─ ShowCity() 每行详细填充

时代变化 → OnGameEraChanged()
  ├─ buildCityList() 拍快照
  ├─ m_historicData[era] = {cityList, cityAwards}
  ├─ RaiseEndOfEraRankingNotification()
  └─ grantEndofEraAwards()（可选奖励）
```

---

## XML 配合

### XML 文件

| 文件 | 路径 | 角色 |
|------|------|------|
| 主界面布局 | `GreatestCities.xml` | 全部 UI 控件 + Instance 模板 |
| 通知定义 | `AKGC_Notifications.xml` | 自定义通知类型注册 |

### 核心控件 ID 对照表

| 控件 ID | 控件类型 | 用途 |
|---------|---------|------|
| `Main` | Box | 主窗口背景，`Size="1015,843"` |
| `CloseButton` | Button | 关闭按钮 |
| `WindowTitle` | Label | 窗口标题 |
| `ButtonShowOptions` | GridButton | 选项设置齿轮按钮 |
| `TabContainer` | Container | Tab 按钮挂载点 |
| `EraPullDown` | PullDown | 时代选择下拉（历史快照导航） |
| `CitiesHeaderRow` | Container | 城市排列表头行 |
| `WondersHeaderRow` | Container | 奇观列表表头行 |
| `Scroll` | ScrollPanel | 主内容滚动区 |
| `Stack` | Stack | 主内容堆叠（城市/奇观行挂载点） |
| `Options` | Container | 选项面板覆盖层（`Hidden="1"`） |

### 排序表头按钮对照

| 按钮 ID | 排序维度 |
|---------|---------|
| `CitiesSortByRank` | 综合排名 |
| `CitiesSortByOwner` | 文明所有者 |
| `CitiesSortByName` | 城市名 |
| `CitiesSortByPopulation` | 人口 |
| `CitiesSortBySpecial` | 特殊属性 |
| `CitiesSortByNumWonders` | 奇观数 |
| `WondersSortByTurnBuilt` | 建造回合 |
| `WondersSortByOwner` | 所有者 |
| `WondersSortByName` | 奇观名 |
| `WondersSortByLocation` | 所在城市 |

### 选项面板 Slider/CheckBox 对照

| 控件 ID | 类型 | 用途 |
|---------|------|------|
| `NumWorldCitiesToShowSlider` / `NumWorldCitiesToShowVal` | Slider / Label | 世界排名显示上限 |
| `NumOwnCitiesToShowSlider` / `NumOwnCitiesToShowVal` | Slider / Label | 自身城市显示上限 |
| `IncludeMinorsCBX` | GridButton(CheckBox) | 包含城邦 |
| `ShowWondersForDiscoveredCitiesCBX` | GridButton(CheckBox) | 显示已探索城市的奇观 |
| `ShowWonderProgressCBX` | GridButton(CheckBox) | 显示奇观建造进度 |
| `ButtonSettingsSave` / `ButtonSettingsCancel` / `ButtonSettingsReset` | GridButton | 选项保存/取消/重置 |

### Instance 对照表

| Instance Name | 用途 | 关键子控件 |
|--------------|------|----------|
| `TabInstance` | 标签按钮 | `Button` + `Selection`(AlphaAnim) |
| `SimpleInstance` | 简单行容器 | `Top` Stack |
| `CityEntryInstance` | 城市排名行 | `Rank`(名次), `OwnerButton`(文明图标), `NameButton`->`Name`+`Description`, `Population`, `SpecialStack`(Capital/HolyCity图标), `WonderStack` |
| `WonderInstance` | 奇观图标（嵌入城市行） | `WonderIcon`(45x45) |
| `WonderEntryInstance` | 奇观排名行 | `DateBuilt`, `OwnerButton`, `WonderIconButton`->`WonderIcon`(128x128)+`WonderProgressIcon`(Mask)+`WonderUnderConstructionIcon`, `WonderNameButton`->`WonderName`+`City`+`OwnedBy`+`BuiltBy`, `DestroyedDate` |

### 可复用模板：奇观进度覆盖图标

```xml
<Image Hidden="1" ID="WonderProgressIcon"
       MaskTexture="akgc_WonderProgressMask.dds"
       Texture="CivDefaults256" Size="128,128"
       Anchor="L,B" Offset="0,0" Color="255,255,255,255"/>
```

Lua 端通过 `SetTexture()` 偏移 + `Resize()` 实现从底部裁剪的进度条效果。```
