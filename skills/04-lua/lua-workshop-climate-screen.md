# lua-workshop-climate-screen — 模态画面 + 数据可视化 + 事件历史

从 Better Climate Screen (Infxo) 提炼的独立 Modal Screen 模式：多 Tab 全屏面板、数据统计展示、饼图/进度条可视化、事件历史列表、热重载支持。

---

## 快速索引

| 模式 | 核心 API / 技术 | 适用场景 |
|------|----------------|---------|
| Modal Screen 全屏面板 | `QueuePopup + Vignette + Tab` | 独立全屏信息界面 |
| 多标签页切换 | `CreateTabs + AddTab + RealizeTabs` | 内容分页展示 |
| PieChart 可视化 | `BuildPieChart(Meter + InstanceManager)` | 占比展示 |
| PhaseBar 进度条 | MakeInstance + SetColor/SetTexture | 阶段进度 |
| 事件历史列表 | 反向遍历回合 + Instance 填充 | 时间线展示 |
| 当前事件显示 | GameRandomEvents API | 当前回合天气 |
| 函数替换(monkey-patch) | 覆盖 GameClimate 方法 | 修复原版 Bug |
| 热重载支持 | RELOAD_CACHE_ID + GameDebug | 开发时免重启 |
| TurnEnd 数据缓存 | Events.TurnEnd + 本地变量 | 显示"上回合变化量" |
| DLC 内容条件显示 | GameCapabilities / Modding.IsModActive | 扩展包适配 |

---

## 一、整体架构

### 1.1 生命周期

```
Initialize()                        → 注册 UI 事件 + Game 事件 + PhaseBar 初始化
  ↓
OnInit(isReload)                    → LateInitialize() 建 Tab + 热重载恢复
  ↓
Open(selectedTabName)               → UpdateData → 选择 Tab → RefreshYields
  ↓
TabSelectOverview / CO2Levels / EventHistory → RealizeTabs + 填充数据
  ↓
OnPlayerTurnActivated               → 持久打开时自动刷新
  ↓
Close()                             → DequeuePopup
```

### 1.2 模态全屏框架模板

```lua
include("InstanceManager");
include("TabSupport");
include("ModalScreen_PlayerYieldsHelper");  -- 顶部 Yield 显示 + 暗角调整

-- ===========================================================================
function Open(selectedTabName)
    local playerID = Game.GetLocalPlayer();
    if playerID == -1 then return; end    -- 观战模式跳过

    -- 更新数据
    UpdateData();

    -- 选择 Tab
    if selectedTabName == "Overview" or selectedTabName == nil then
        m_tabs.SelectTab(Controls.ButtonOverview);
    end

    UI.PlaySound("UI_Screen_Open");

    -- 调整暗角高度（让出顶部 Yield 面板）
    if not RefreshYields() then
        Controls.Vignette:SetSizeY(m_TopPanelHeight);
    end

    -- 动画
    Controls.ScreenAnimIn:SetToBeginning();
    Controls.ScreenAnimIn:Play();

    -- QueuePopup 参数
    local kParameters = {};
    kParameters.RenderAtCurrentParent = true;
    kParameters.InputAtCurrentParent = true;
    kParameters.AlwaysVisibleInQueue = true;
    UIManager:QueuePopup(ContextPtr, PopupPriority.Low, kParameters);
end

function Close()
    if not ContextPtr:IsHidden() then
        UI.PlaySound("UI_Screen_Close");
    end
    UIManager:DequeuePopup(ContextPtr);
end
```

---

## 二、多 Tab 切换

### 2.1 Tab 创建

```lua
function LateInitialize()
    m_tabs = CreateTabs(Controls.TabContainer, 42, 34, 0xFF331D05);
    m_tabs.AddTab(Controls.ButtonOverview,    TabSelectOverview);
    m_tabs.AddTab(Controls.ButtonCO2Levels,   TabSelectCO2Levels);
    m_tabs.AddTab(Controls.ButtonEventHistory, TabSelectEventHistory);
    m_tabs.CenterAlignTabs(-10);
end
```

### 2.2 手动 Tab 实现（未使用 TabSupport 的 SelectTab / AddAnimDeco）

Better Climate Screen 使用手动 `RealizeTabs` 模式：

```lua
function RealizeTabs(selectedTabName)
    m_currentTabName = selectedTabName;

    -- 三个 Tab: 每个都有 Button + Selected 指示器
    Controls.SelectedOverview:SetHide(selectedTabName ~= "Overview");
    Controls.ButtonOverview:SetSelected(selectedTabName == "Overview");
    Controls.OverviewPane:SetHide(selectedTabName ~= "Overview");

    Controls.SelectedCO2Levels:SetHide(selectedTabName ~= "CO2Levels");
    Controls.ButtonCO2Levels:SetSelected(selectedTabName == "CO2Levels");
    Controls.CO2LevelsPane:SetHide(selectedTabName ~= "CO2Levels");

    Controls.SelectedEventHistory:SetHide(selectedTabName ~= "EventHistory");
    Controls.ButtonEventHistory:SetSelected(selectedTabName == "EventHistory");
    Controls.EventHistoryPane:SetHide(selectedTabName ~= "EventHistory");
end
```

XML 结构（每个 Tab 一个 Button + 一个 Selected 控件）：
```xml
<GridButton ID="ButtonOverview" Size="170,34" Style="TabButton"
            FontSize="14" TextOffset="0,2" String="LOC_CLIMATE_TAB_OVERVIEW">
    <GridButton ID="SelectedOverview" Size="parent,parent"
                Style="TabButtonSelected" Hidden="1" />
</GridButton>
```

---

## 三、PieChart 可视化

### 3.1 BuildPieChart 实现

使用 `Meter` 控件模拟饼图（不是真正的饼图，而是多个半透明 Meter 叠加）。

```lua
function BuildPieChart(uiHolder, sliceIM, kSliceAmounts, kColors)
    -- 参数验证
    if uiHolder == nil or sliceIM == nil or kSliceAmounts == nil then
        return {};
    end

    -- 计算总占比，超过 1.0 时等比缩放
    local total = 0;
    local multiplier = 1;
    for i, v in ipairs(kSliceAmounts) do total = total + v; end
    if total > 1.0 then multiplier = 1.0 / total; end

    -- 默认颜色表
    if kColors == nil or table.count(kColors) == 0 then
        kColors = {
            UI.GetColorValueFromHexLiteral(0xff000099),  -- 蓝
            UI.GetColorValueFromHexLiteral(0xff008888),  -- 青
            UI.GetColorValueFromHexLiteral(0xff009900),  -- 绿
            UI.GetColorValueFromHexLiteral(0xff888800),  -- 黄
            UI.GetColorValueFromHexLiteral(0xff990000),  -- 红
            UI.GetColorValueFromHexLiteral(0xff880088),  -- 紫
        };
    end
    local maxColors = #kColors;

    -- 循环生成 slice（每个 slice 是一个 Meter 实例）
    local kUISlices = {};
    local remaining = total;
    for i, v in ipairs(kSliceAmounts) do
        local uiInstance = sliceIM:GetInstance(uiHolder);
        table.insert(kUISlices, uiInstance);
        uiInstance["Slice"]:SetColor(kColors[((i - 1) % maxColors) + 1]);
        uiInstance["Slice"]:SetPercent(remaining);
        remaining = remaining - v;
    end
    return kUISlices;
end
```

XML Instance（Meter 控件）：
```xml
<Instance Name="PieChartSliceInstance">
    <Meter ID="Slice" Anchor="C,C" Size="360,360"
           Texture="Climate_CO2Meter_Fill" Speed="0" />
</Instance>
```

### 3.2 释放切片

```lua
-- 每次重建饼图前释放旧切片
for _, uiSliceInstance in ipairs(m_kGlobalPieSlices) do
    m_kSliceIM:ReleaseInstance(uiSliceInstance);
end
m_kGlobalPieSlices = BuildPieChart(...);
```

---

## 四、PhaseBar 进度条

### 4.1 初始化所有段

```lua
local MAX_PHASES = 7;
local m_kBarSegments = {};

function InitPhaseSegment(segmentNum)
    local uiSegment = Controls["Phase" .. tostring(segmentNum)];
    uiSegment.Name:SetText(Locale.ToRomanNumeral(segmentNum));
    m_kBarSegments[segmentNum] = uiSegment;
    uiSegment.Progress:SetTexture("Climate_PhaseMeter_" .. segmentNum);
    uiSegment.Progress:SetColor(UI.GetColorValue("COLOR_CLEAR"));  -- 默认透明
    uiSegment.Pip:SetTexture("Climate_PhaseMeterPip_Off");
end

-- Initialize 中批量初始化
for phase = 1, MAX_PHASES do
    InitPhaseSegment(phase);
end
```

### 4.2 更新当前阶段

```lua
function UpdatePhaseBar(phase, realismAmount, globalTemp)
    -- 填充当前及之前所有段为白色
    if phase > 0 then
        for i = 1, phase do
            local uiSegment = m_kBarSegments[i];
            uiSegment.Progress:SetColor(UI.GetColorValue("COLOR_WHITE"));
            uiSegment.Pip:SetTexture("Climate_PhaseMeterPip_On");
        end
    end
    -- 更新所有段的 tooltip
    for i = 1, MAX_PHASES do
        UpdatePhaseTooltips(i);
    end
end
```

### 4.3 复杂 Tooltip 构建

```lua
function UpdatePhaseTooltips(segmentNum)
    local kEventDef = GameInfo.RandomEvents[m_firstSeaLevelEvent + segmentNum - 1];
    if kEventDef == nil then return; end

    -- 从 CoastalLowlands 获取淹没/沉没阈值信息
    local szAtOrAboveString = "";
    for row in GameInfo.CoastalLowlands() do
        if row.FloodedEvent == kEventDef.RandomEventType then
            szAtOrAboveString = Locale.Lookup("LOC_CLIMATE_TILES_AT_OR_BELOW_FLOOD_TOOLTIP", row.Name);
            break;
        elseif row.SubmergedEvent == kEventDef.RandomEventType then
            szAtOrAboveString = Locale.Lookup("LOC_CLIMATE_TILES_AT_OR_BELOW_SUBMERGE_TOOLTIP", row.Name);
            break;
        end
    end

    -- 组装 tooltip
    local tooltip =
        Locale.ToUpper(kEventDef.Name)
        .. "[NEWLINE]" .. Locale.Lookup("LOC_CLIMATE_CO2_LEVELS")
            .. " " .. tostring(m_CO2For1Phase * 0.5 * (segmentNum + 1))
        .. "[NEWLINE]"
        .. "[NEWLINE]" .. Locale.Lookup("LOC_CLIMATE_CLIMATE_CHANGE_POINTS_TOOLTIP",
            GameClimate.GetClimateChangeLevel(), kEventDef.ClimateChangePoints)
        .. "[NEWLINE]" .. Locale.Lookup("LOC_CLIMATE_FROM_WORLD_REALISM_NUM_TOOLTIP",
            GameClimate.GetClimateChangeFromRealism())
        .. "[NEWLINE]" .. Locale.Lookup("LOC_CLIMATE_FROM_GLOBAL_TEMPERATURE_NUM_TOOLTIP",
            GameClimate.GetClimateChangeFromTemperature())
        .. "[NEWLINE]"
        .. "[NEWLINE]" .. Locale.ToUpper("LOC_CLIMATE_EFFECTS_ADDED_THIS_PHASE_TOOLTIP")
        .. "[NEWLINE]" .. Locale.Lookup("LOC_CLIMATE_SEA_LEVEL_RISES_NUM_TOOLTIP", kEventDef.Description)
        .. szAtOrAboveString
        .. "[NEWLINE]"
        .. "[NEWLINE]" .. Locale.Lookup("LOC_CLIMATE_POLAR_ICE_MELT_TOOLTIP", kEventDef.IceLoss);

    m_kBarSegments[segmentNum].Progress:SetToolTipString(tooltip);
end
```

---

## 五、事件历史列表

### 5.1 反向遍历回合

```lua
function TabSelectEventHistory()
    RealizeTabs("EventHistory");

    m_kEventRowInstance:ResetInstances();
    m_kClimateChangeInstance:ResetInstances();

    local iCurrentTurn = Game.GetCurrentGameTurn();
    for i = iCurrentTurn, 0, -1 do        -- 从当前回合倒序遍历到第 0 回合
        local kEvent = GameRandomEvents.GetEventsForTurn(i);
        if kEvent ~= nil then
            local kEventDef = GameInfo.RandomEvents[kEvent.RandomEvent];
            if kEventDef ~= nil then
                if kEventDef.ClimateChangePoints > 0 then
                    CreateClimateChangeInstance(kEvent, kEventDef, i);
                elseif kEventDef.EffectOperatorType ~= "NUCLEAR_ACCIDENT" then
                    -- 仅显示可见区域的事件
                    local pEventPlot = Map.GetPlotByIndex(kEvent.CurrentLocation);
                    if kEventDef.Global then
                        CreateEventInstance(kEvent, kEventDef, i);
                    elseif pEventPlot ~= nil then
                        local pVis = PlayersVisibility[Game.GetLocalPlayer()];
                        if pVis:IsRevealed(pEventPlot:GetX(), pEventPlot:GetY()) then
                            CreateEventInstance(kEvent, kEventDef, i);
                        end
                    end
                end
            end
        end
    end
end
```

### 5.2 事件行填充

```lua
function CreateEventInstance(kEvent, kEventDef, iTurn)
    local kInstance = m_kEventRowInstance:GetInstance();

    -- Icon
    if kEventDef.IconSmall and kEventDef.IconSmall ~= "" then
        kInstance.Icon:SetTexture(kEventDef.IconSmall);
    end

    -- Name
    kInstance.EventTypeName:SetText(Locale.ToUpper(kEventDef.Name));
    kInstance.EventName:SetText(Locale.ToUpper(kEvent.Name));

    -- Tooltip
    if kEventDef.EffectString then
        kInstance.NameContainer:SetToolTipString(Locale.Lookup(kEventDef.EffectString));
    end

    -- Location（大陆名 或 领土名）
    local pPlot = Map.GetPlotByIndex(kEvent.StartLocation);
    if pPlot ~= nil then
        local eContinentType = pPlot:GetContinentType();
        if eContinentType and eContinentType ~= -1 then
            kInstance.LocationString:SetText(
                Locale.Lookup(GameInfo.Continents[eContinentType].Description));
        else
            kInstance.LocationString:SetText(Locale.Lookup("LOC_CLIMATE_SCREEN_WATER"));
        end
    end

    -- Effects（条件显示）
    if kEvent.FertilityAdded > 0 then
        kInstance.FertilizedTilesIcon:SetHide(false);
        kInstance.LosingFertilizedTilesIcon:SetHide(true);
        kInstance.FertilizedTiles:SetText(kEvent.FertilityAdded);
    elseif kEvent.FertilityAdded < 0 then
        kInstance.FertilizedTilesIcon:SetHide(true);
        kInstance.LosingFertilizedTilesIcon:SetHide(false);
        kInstance.FertilizedTiles:SetText(math.abs(kEvent.FertilityAdded));
    else
        kInstance.FertilizedTilesIcon:SetHide(true);
        kInstance.LosingFertilizedTilesIcon:SetHide(true);
    end
    -- ... TilesDamaged / UnitsLost / PopLost 同理 ...

    -- Date
    local strDate = Calendar.MakeYearStr(iTurn);
    kInstance.DateString:SetText("[Icon_Turn]"
        .. Locale.Lookup("LOC_CLIMATE_ENTRY_DATE", iTurn, strDate));
end
```

---

## 六、当前事件显示

### 6.1 获取 & 显示当前天气事件

```lua
function RefreshCurrentEvent()
    local kCurrentEvent = GameRandomEvents.GetCurrentTurnEvent();
    if kCurrentEvent == nil then
        Controls.CurrentEventStack:SetHide(true);
        return;
    end

    local kEventDef = GameInfo.RandomEvents[kCurrentEvent.RandomEvent];

    -- 跳过气候变化事件和核事故（在其他地方显示）
    if kEventDef.EffectOperatorType == "SEA_LEVEL" then
        Controls.SeaLevelAlertIndicator:SetHide(false);
        return;
    elseif kEventDef.EffectOperatorType == "NUCLEAR_ACCIDENT" then
        return;
    end

    -- 判断事件位置是否对本地玩家可见
    local pCurrentPlot = Map.GetPlotByIndex(kCurrentEvent.CurrentLocation);
    local bIsEventVisible = false;
    if pCurrentPlot ~= nil then
        local pVis = PlayersVisibility[Game.GetLocalPlayer()];
        if pVis:IsRevealed(pCurrentPlot:GetX(), pCurrentPlot:GetY()) then
            bIsEventVisible = true;
        end
    end

    -- 天气类型名称
    Controls.WeatherStatusText:SetText(Locale.ToUpper(kEventDef.Name));

    -- 位置描述（大陆 + 方向）
    local location = "";
    if pCurrentPlot ~= nil then
        local eContinent = pCurrentPlot:GetContinentType();
        if eContinent and eContinent ~= -1 then
            location = Locale.ToUpper(GameInfo.Continents[eContinent].Description);
        end
    end
    local direction = Locale.Lookup(GetDirectionText(kCurrentEvent.CurrentDirection));
    Controls.WeatherLocation:SetText(
        Locale.Lookup("LOC_CLIMATE_SCREEN_LOCATION_DIRECTION", location, direction));

    -- 受影响的可见城市
    m_kAffectedCitiesIM:ResetInstances();
    local kAffectedCities = GameRandomEvents.GetCurrentAffectedCities();
    for _, affectedCity in ipairs(kAffectedCities) do
        local pOwner = Players[affectedCity.CityOwner];
        local pDiplo = Players[Game.GetLocalPlayer()]:GetDiplomacy();
        if pOwner ~= nil and pDiplo:HasMet(affectedCity.CityOwner) then
            local pCity = pOwner:GetCities():FindID(affectedCity.CityID);
            if pCity then
                local iconString = "ICON_" .. PlayerConfigurations[affectedCity.CityOwner]
                    :GetCivilizationTypeName();
                local tx, ty, sheet = IconManager:FindIconAtlas(iconString, 30);
                local sc, pc = UI.GetPlayerColors(affectedCity.CityOwner);

                local cityInstance = m_kAffectedCitiesIM:GetInstance();
                cityInstance.Icon:SetTexture(tx, ty, sheet);
                cityInstance.Icon:SetColor(pc);
                cityInstance.IconBacking:SetColor(sc);
                cityInstance.Name:SetText(Locale.Lookup(pCity:GetName()));
            end
        end
    end
end
```

---

## 七、函数替换 (Monkey-Patching)

### 7.1 修复原版 Bug

Better Climate Screen 替换了 `GameClimate.GetPlayerCO2Footprint` 和 `GetTotalCO2Footprint` 来修复负数处理。

```lua
-- 保存原版引用
GameClimate.GetPlayerCO2FootprintFromEngine = GameClimate.GetPlayerCO2Footprint;

-- 替换：负数转为 0
GameClimate.GetPlayerCO2Footprint = function(ePlayer)
    return math.max(0, GameClimate.GetPlayerCO2FootprintFromEngine(ePlayer));
end

-- 替换：通过遍历玩家求和计算（而非直接调用原版）
GameClimate.GetTotalCO2FootprintFromEngine = GameClimate.GetTotalCO2Footprint;
GameClimate.GetTotalCO2Footprint = function()
    local totalCO2 = 0;
    for _, playerID in ipairs(PlayerManager.GetWasEverAliveMajorIDs()) do
        totalCO2 = totalCO2 + GameClimate.GetPlayerCO2Footprint(playerID);
    end
    if GameClimate.GetCO2FootprintModifier() > 0 then
        totalCO2 = math.floor(totalCO2 * (100.0 + GameClimate.GetCO2FootprintModifier()) / 100.0);
    end
    return totalCO2;
end
```

### 7.2 注意事项

- **仅在 UI 端生效**（GP 端不加载此文件），不会影响游戏逻辑
- **在文件顶部 early-loaded**（在 `include()` 之后的任何函数调用前）
- **适用于数据获取层的 patch**，不适用于游戏逻辑修改

---

## 八、热重载支持

### 8.1 模式

```lua
local RELOAD_CACHE_ID = "ClimateScreen";

-- 关闭时保存状态
function OnShutdown()
    LuaEvents.GameDebug_AddValue(RELOAD_CACHE_ID, "isHidden", ContextPtr:IsHidden());
    LuaEvents.GameDebug_AddValue(RELOAD_CACHE_ID, "m_currentTabName", m_currentTabName);
end

-- 启动时恢复
function OnInit(isReload)
    LateInitialize();
    if isReload then
        LuaEvents.GameDebug_GetValues(RELOAD_CACHE_ID);
    end
end

-- 接收恢复数据
function OnGameDebugReturn(context, contextTable)
    if context ~= RELOAD_CACHE_ID then return; end
    m_currentTabName = contextTable["m_currentTabName"];
    if contextTable["isHidden"] ~= nil and not contextTable["isHidden"] then
        Open(m_currentTabName);
    end
end

-- 注册
function Initialize()
    ContextPtr:SetInitHandler(OnInit);
    ContextPtr:SetShutdown(OnShutdown);
    LuaEvents.GameDebug_Return.Add(OnGameDebugReturn);
end
```

### 8.2 热重载触发方式

1. 在 ModBuddy 中修改 Lua 文件后保存
2. 控制台输入 `lua_reload` 或使用 Civ6 Debug 面板中的 Reload UI
3. `SetInitHandler` 的 `isReload=true` 被触发
4. 发送 `GameDebug_GetValues` 请求 → `GameDebug_Return` 回调恢复状态

---

## 九、数据统计展示（TurnEnd 缓存）

显示"上回合变化量"的核心技巧。

```lua
local m_prevTurnNum = 0;
local m_prevTurnCO2 = 0;
local m_prevTurnRecapture = 0;

-- 回合结束时缓存当前值
function OnTurnEnd()
    m_prevTurnNum = Game.GetCurrentGameTurn();
    m_prevTurnCO2 = GameClimate.GetTotalCO2Footprint();
    m_prevTurnRecapture = math.min(m_prevTurnRecapture,
        GameClimate.GetPlayerCO2FootprintFromEngine(m_playerID)
        - GetPlayerCO2FootprintFromResources(m_playerID));
end

-- 显示时计算差值
function TabSelectCO2Levels()
    local CO2Total = GameClimate.GetTotalCO2Footprint();
    if m_prevTurnNum > 0 then
        -- 显示 "1234  (+56)" 格式
        Controls.GlobalContributionsTotalNum:SetText(
            string.format("%s  +%d", sGlobalTotal, CO2Total - m_prevTurnCO2));
    else
        Controls.GlobalContributionsTotalNum:SetText(sGlobalTotal);
    end
end

-- 注册
Events.TurnEnd.Add(OnTurnEnd);
```

---

## 十、CO2 数据采集模式

### 10.1 按资源遍历

```lua
-- 获取某玩家的资源 CO2 总和
function GetPlayerCO2FootprintFromResources(ePlayer)
    local total = 0;
    for kResourceInfo in GameInfo.Resources() do
        total = total + GameClimate.GetPlayerResourceCO2Footprint(
            ePlayer, kResourceInfo.Index, false);
    end
    return total;
end

-- 显示每个资源的贡献
function RealizePlayerCO2()
    m_kYourCO2IM:ResetInstances();
    local total = GetPlayerCO2FootprintFromResources(m_playerID);

    for kResourceInfo in GameInfo.Resources() do
        local kConsumption = GameInfo.Resource_Consumption[kResourceInfo.ResourceType];
        if kConsumption ~= nil and kConsumption.CO2perkWh > 0 then
            local amount = GameClimate.GetPlayerResourceCO2Footprint(
                m_playerID, kResourceInfo.Index, false);
            if amount > 0 then
                local uiResource = m_kYourCO2IM:GetInstance();
                uiResource.Icon:SetIcon("ICON_" .. kResourceInfo.ResourceType);
                uiResource.Name:SetText(Locale.Lookup(kResourceInfo.Name));
                uiResource.Percent:SetText(FormatPercent(amount, total));
                uiResource.Amount:SetText(amount);
                uiResource.LastTurn:SetText(FormatLastTurn(amountLastTurn));
            end
        end
    end
end
```

### 10.2 按文明遍历

```lua
function TabCO2ByCivilization()
    m_kCivCO2IM:ResetInstances();

    -- 先计算所有玩家的总排放量
    local total = 0;
    for _, pPlayer in ipairs(PlayerManager.GetAliveMajors()) do
        total = total + GameClimate.GetPlayerCO2Footprint(pPlayer:GetID(), false);
    end

    -- 计算阈值（均值 50% ~ 150% 用于颜色标记）
    local avg = total / iNumPlayersWithCO2;
    local minGood, maxGood = avg * 0.5, avg * 1.5;

    -- 颜色辅助函数
    local function FormatColor(text, amount)
        if amount == 0 then return "[COLOR:128,128,128,128]" .. text .. "[ENDCOLOR]"; end
        if iNumPlayersWithCO2 < 2 then return text; end
        if amount < minGood then return "[COLOR_GREEN]" .. text .. "[ENDCOLOR]"; end
        if amount > maxGood then return "[COLOR_RED]" .. text .. "[ENDCOLOR]"; end
        return text;
    end

    -- 未遇见的玩家合并为一个条目
    local bShowUnmet = false;
    local iUnmetCO2 = 0;
    for _, pPlayer in ipairs(PlayerManager.GetAliveMajors()) do
        local playerID = pPlayer:GetID();
        if pDiplo:HasMet(playerID) or playerID == m_playerID then
            -- 单独一行
            AddCivCO2Row(true, playerID, civName, amount);
        else
            iUnmetCO2 = iUnmetCO2 + amount;
            bShowUnmet = true;
        end
    end
    if bShowUnmet then
        AddCivCO2Row(false, 0, Locale.Lookup("LOC_WORLD_RANKING_UNMET_PLAYER"), iUnmetCO2);
    end

    -- 排序后显示（排放量降序，同量则按上回合降序）
    table.sort(tRows, function(a, b)
        if a.Amount == b.Amount then return a.LastTurn > b.LastTurn; end
        return a.Amount > b.Amount;
    end);
end
```

---

## 十一、关键 API 速查

### 气候/CO2

| API | 说明 |
|-----|------|
| `GameClimate.GetTotalCO2Footprint()` | 全球 CO2 总排放 |
| `GameClimate.GetPlayerCO2Footprint(pid, lastTurn)` | 某玩家 CO2 排放 |
| `GameClimate.GetPlayerResourceCO2Footprint(pid, resIndex, lastTurn)` | 某玩家某资源 CO2 |
| `GameClimate.GetPlayerRawResourceConsumption(pid, resIndex, lastTurn)` | 某玩家某资源消耗量 |
| `GameClimate.GetCO2FootprintModifier()` | CO2 修正百分比 |
| `GameClimate.GetTemperatureChange()` | 温度变化 (Celsius) |
| `GameClimate.GetClimateChangeLevel()` | 气候变化等级 |
| `GameClimate.GetStormPercentChance()` | 风暴概率 |
| `GameClimate.GetEruptionPercentChance()` | 火山喷发概率 |
| `GameClimate.GetNextSeaLevelRiseTurns()` | 距下次海平面上升回合数 |
| `GameClimate.GetTilesFlooded()` / `GetTilesSubmerged()` | 已淹/已沉地块数 |
| `GameClimate.GetClimateChangeForLastSeaLevelEvent()` | 上次海平面事件的 CC 点数 |

### 随机事件

| API | 说明 |
|-----|------|
| `GameRandomEvents.GetCurrentTurnEvent()` | 当前回合天气事件 |
| `GameRandomEvents.GetCurrentAffectedCities()` | 当前事件影响的城市 |
| `GameRandomEvents.GetEventsForTurn(turn)` | 某回合的事件（历史查询） |

### 地图配置

| API | 说明 |
|-----|------|
| `MapConfiguration.GetValue("world_age")` | 世界年龄设置 |
| `MapFeatureManager.GetNumActiveVolcanoes()` | 活动火山数 |
| `MapFeatureManager.GetNumEruptions()` | 已喷发次数 |
| `RiverManager.GetNumRivers()` / `GetNumFloodableRivers()` | 河流统计 |

---

## 十二、注意事项

1. **`GameClimate` 方法在 UI 端和 GP 端都可调用**（只读数据获取）
2. **`GetPlayerResourceCO2Footprint` 的第二个参数是 `resourceIndex`（数字），不是 `resourceType`（字符串）**
3. **`QueuePopup` 的 `AlwaysVisibleInQueue = true`** 确保切换 Tab 时界面不闪烁
4. **`RefreshYields()` 来自 `ModalScreen_PlayerYieldsHelper`**，用于显示顶部 Yield 栏
5. **`GameCapabilities.HasCapability("CAPABILITY_WORLD_CLIMATE_VIEW")`** 检查玩家是否能打开气候界面
6. **`Events.PlayerTurnActivated`** 用于持久打开时自动刷新（但检查 `isFirstTime`）
7. **`Calendar.MakeYearStr(turn)`** 将回合数转为年月字符串

---

## XML 配合

### XML 文件

| 文件 | 路径 | 角色 |
|------|------|------|
| GS 版布局 | `GCM/climatescreen.xml` | 主布局（Gathering Storm） |
| XP2 兼容 | `XP2/climatescreen.xml` | XP2 入口可引用 |

### 核心控件 ID 对照表

| 控件 ID | 控件类型 | 用途 |
|---------|---------|------|
| `PopupContainer` | Container | 根容器，`Size="1024,768"` |
| `OverviewBG` | Image | 概览背景纹理 `Climate_BG` |
| `ModalScreenTitle` | Label | 模态标题 |
| `ModalScreenClose` | Button | 关闭按钮 |
| `TabContainer` | Container | 标签按钮容器 |
| `ButtonOverview` / `ButtonCO2Levels` / `ButtonEventHistory` | GridButton | 三个 Tab 按钮（含子 `SelectedXxx` 指示器） |
| `OverviewPane` | Container | 概览页 |
| `CO2LevelsPane` | Container | CO2 详情页 |
| `EventHistoryPane` | Container | 事件历史页 |
| `Vignette` | Container | 暗角遮罩 |
| `YieldsContainer` | Grid | 顶部产量栏容器（`Style="YieldContainerStyle"`） |

### 概览页（OverviewPane）关键控件

| 控件 ID | 用途 |
|---------|------|
| `ClimateChangePhaseText` | 当前气候变化阶段名称 |
| `ContributeTotal` / `ContributeTop` / `ContributeMe` | CO2 排放统计（全球/最高/自己） |
| `TemperatureValue` / `ClimateTemperature` | 温度数据 |
| `WorldAgeText` / `RealismText` | 世界设置 |
| `StormChanceNum` / `StormChanceFromClimateChange` | 风暴概率 |
| `RiverFloodChanceNum` / `RiverFloodChanceFromClimateChange` | 洪水概率 |
| `DroughtActivityChanceNum` / `DroughtChanceFromClimateChange` | 干旱概率 |
| `VolcanicActivityChanceNum` / `VolatileNum` / `ActiveNum` / `EruptedNum` | 火山活动 |
| `ForestFireActivityChanceNum` / `ForestFireChanceFromClimateChange` | 森林大火 |
| `CurrentEventStack` | 当前天气事件栈 |
| `WeatherStatusText` / `WeatherLocation` | 当前天气名/位置 |
| `CitiesStack` | 受影响城市列表 |
| `BuffStack` | 影响效果统计（肥沃/受损/单位损失/人口损失） |
| `SeaLevelArea` → `SeaLevel` / `TilesFlooded` / `TilesSubmerged` / `NextSeaLevelRise` | 海平面信息 |
| `SeaLevelAlertIndicator` | 海平面变化警报 |
| `PolarIceLostNum` / `NextPolarIceLost` | 极冰融化信息 |
| `PolarIceAlertIndicator` | 极冰警报 |

### CO2 详情页（CO2LevelsPane）关键控件

| 控件 ID | 用途 |
|---------|------|
| `GlobalContributionsTotalNum` | 全球总排放 |
| `GlobalCivScroll` / `GlobalCivStack` | 按文明排放滚动列表 |
| `GlobalResStack` | 按资源排放列表 |
| `YourCO2Stack` | 自身 CO2 详情列表 |
| `YourContributionsNum` | 自身贡献合计 |
| `RecaptureAmount` / `RecaptureLastTurn` | 碳回收统计 |

### 事件历史页（EventHistoryPane）关键控件

| 控件 ID | 用途 |
|---------|------|
| `EventScroll` / `EventStack` | 事件历史滚动列表 |

### Instance 对照表

| Instance Name | 用途 |
|--------------|------|
| `PhaseSectionInstance` | PhaseBar 阶段段（`Progress` meter + `Pip` + `Name`） |
| `PieChartSliceInstance` | 饼图切片（`Meter` 控件，360x360） |
| `CivCO2Instance` | 按文明 CO2 行（`CivIcon` + `Name` + `Percent` + `Amount` + `LastTurn`） |
| `ResourceCO2Instance` | 按资源 CO2 行（`Icon` + `Name` + `Percent` + `Amount` + `LastTurn` + `ResAmount` + `ResLastTurn`） |
| `EventRowHeaderInstance` | 事件历史表头 |
| `EventRowInstance` | 事件历史行（`Icon` + `EventTypeName` + `EventName` + `LocationString` + 效果列 + `DateString`） |
| `ClimateChangeInstance` | 气候变化事件行（特殊样式） |
| `EventEraRowInstance` | 事件历史中时代分隔行 |
| `CityInstance` | 受影响城市条目 |
| `AffectedInstance` | 影响统计条目 |

### 可复用模板：PhaseBar 多阶段进度条

```xml
<Grid Anchor="C,T" Size="1022,20" Texture="Climate_PhaseMeterBG" SliceCorner="11,8" SliceSize="2,2">
  <Stack Anchor="C,C" StackGrowth="Right" StackPadding="-1">
    <MakeInstance ID="Phase1" Name="PhaseSectionInstance" />
    <Image Anchor="L,C" Size="3,18" Texture="Climate_PhaseMeterDiv"/>
    <MakeInstance ID="Phase2" Name="PhaseSectionInstance" />
    <!-- ... 重复至 Phase7 ... -->
  </Stack>
</Grid>

<Instance Name="PhaseSectionInstance">
  <Image ID="Progress" Anchor="C,C" Size="144,12" Texture="Climate_PhaseMeter_1">
    <Image ID="Pip" Anchor="C,C" Size="32,32" Texture="Climate_PhaseMeterPip_Off">
      <Label ID="Name" Anchor="C,C" Style="FontNormal14" String="$"/>
    </Image>
  </Image>
</Instance>
```
