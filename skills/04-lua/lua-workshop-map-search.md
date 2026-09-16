# Map Search Extension — 地图搜索

参考 Mod: Map Search Extension (1709115371)

## 核心架构

基于 Civ6 的 Search API 实现增量式地图搜索。核心流程：产出建议数据 -> 图块数据采集 -> 搜索词生成 -> 增量搜索 -> 结果高亮与导航。

## 模式 1: Search API 双上下文

```lua
SEARCHCONTEXT_MAPSEARCH   = "MapSearch_Primary";   -- 实际地图搜索用
SEARCHCONTEXT_SUGGESTIONS = "MapSearch_Suggestions"; -- 搜索建议/自动补全用

-- 创建
Search.CreateContext(SEARCHCONTEXT_MAPSEARCH, "", "", "...");
Search.CreateContext(SEARCHCONTEXT_SUGGESTIONS, "", "", "...");

-- 填充数据
Search.AddData(ctx, plotString, "", "", searchTermsTable);

-- 优化索引
Search.Optimize(ctx);

-- 搜索
local results = Search.Search(ctx, term, maxResultsPerFrame);

-- 清理
Search.ClearData(ctx);

-- 销毁
Search.DestroyContext(ctx);
```

注意：`Search.AddData` 的第三个参数（key）用于建议搜索时的匹配。MapSearch 上下文用 `tostring(plotIndex)` 做 key，Suggestions 上下文用 `szTerm` 做 key。

## 模式 2: 增量搜索 (帧分片)

每帧只扫描 `PLOTS_CHECKED_PER_FRAME` (35) 个地块，避免卡顿：

```lua
ContextPtr:SetUpdate(IncrementalSearch);

function IncrementalSearch()
    Search.ClearData(ctx);
    for iPlot = m_nLastPlotSearched + 1, nPlots - 1 do
        if IsRevealed(iPlot) and IsTileMatchesCriteria(iPlot) then
            local info = GetPlotInfo(iPlot);
            Search.AddData(ctx, tostring(iPlot), "", "", info);
            checkedThisFrame++;
            if checkedThisFrame >= PLOTS_CHECKED_PER_FRAME then
                CheckForMatches();
                Controls.ProgressBar:SetPercent(iPlot / nPlots);
                m_nLastPlotSearched = iPlot;
                return;  -- 下帧继续
            end
        end
    end
    -- 扫描完成
    CheckForMatches();
    HighlightResults();
    StopSearch();  -- ContextPtr:ClearUpdate()
end
```

## 模式 3: 图块信息收集 (FetchData)

从 plot 对象提取所有可搜索属性：

```lua
function FetchData(plot)
    return {
        X, Y, Index,
        Appeal, Continent,
        DistrictID, DistrictComplete, DistrictPillaged, DistrictType,
        FeatureType, FeatureAdded,
        Impassable, ImprovementType, ImprovementPillaged,
        IsCity, IsLake, IsRiver, IsMountain, IsHill, IsRoute, IsWater,
        NationalPark, Owner, OwnerCity,
        ResourceCount, ResourceType,
        RoutePillaged, RouteType,
        TerrainType, TerrainTypeName,
        WonderComplete, WonderType,
        BuildingNames, BuildingsPillaged, BuildingTypes, Constructions,
        Yields, DistrictYields,
    };
end
```

XP2 扩展添加：IsVolcano, VolcanoName, Active, Erupting, Storm, Drought, CoastalLowland, Flooded, Submerged, TerritoryName, RiverNames。

## 模式 4: 搜索词生成 (GetPlotSearchTerms)

将图块数据转换为本地化的搜索词数组：

```lua
function GetPlotSearchTerms(data)
    local terms = {};
    local Add = function(kLocKey)
        table.insert(terms, Locale.Lookup(kLocKey));
    end

    -- 拥有者: data.Owner -> 文明名/城邦名/"无主"
    -- 地形: 湖/海岸/丘陵/山脉/河流/不可通行
    -- 地貌: 自然奇观/普通地貌名
    -- 资源: 资源类名/资源名 (仅可见资源)
    -- 道路: 道路名/被掠夺状态
    -- 魅力: 对应等级名称
    -- 大陆: 大陆名
    -- 奇观: 奇观名/建造中状态
    -- 改良: 改良名/被掠夺状态
    -- 产出: 各产出类型名
    -- 辐射: 辐射标记
    -- 国家公园: 公园名
    -- 城区: 城区名/专家标记/被掠夺/建造中/城区产出
    -- 建筑/巨作: 建筑名/巨作类型名/巨作名
    -- 单位: 单位名/类型名/拥有者/编队(军团/军队/舰队/大舰队)/战斗类型

    return terms;
end
```

XP2 扩展: 火山(喷发/活跃/火山名)、河流(河流名)、灾害(暴风雪/干旱/风暴名)、沿海低地(高度/淹没/洪水)、领土名。

## 模式 5: 多词条 AND 逻辑 + 黑名单

白名单 (Whitelist) 中的词条必须全部在同一个图块上匹配，黑名单 (Blacklist) 中的词条必须全部不存在：

```lua
function CheckForMatches()
    -- 对每个白名单词搜索
    for _, key in pairs(m_Search.Whitelist) do
        local results = Search.Search(ctx, key, PLOTS_CHECKED_PER_FRAME);
        for _, result in pairs(results) do
            kResultCounters[plotIndex] = (kResultCounters[plotIndex] or 0) + 1;
        end
    end
    -- 对每个黑名单词搜索
    for _, key in pairs(m_Search.Blacklist) do
        local results = Search.Search(ctx, key, PLOTS_CHECKED_PER_FRAME);
        for _, result in pairs(results) do
            kResultCounters[plotIndex] = -1;  -- 标记为排除
        end
    end
    -- 计数 >= 白名单词数 的图块为匹配
    for iPlot, nCount in pairs(kResultCounters) do
        if nCount >= nRequiredCount then
            table.insert(m_ResultPlots, iPlot);
        end
    end
end
```

## 模式 6: 搜索结果高亮与导航

```lua
-- 高亮
local pOverlay = UILens.GetOverlay("MapSearch");
pOverlay:ClearAll();
pOverlay:SetPlotChannel(m_ResultPlots, 0);
pOverlay:SetBorderColors(0, borderColor1, borderColor2);
pOverlay:SetHighlightColor(0, fillColor);

-- 区域分组（相邻地块合并为一个导航组）
m_ResultGroups = {};
local pGroups = UI.PartitionRegions(m_ResultPlots);
for _, pGroup in pairs(pGroups) do
    local x, y = UI.GetRegionCenter(pGroup);
    table.insert(m_ResultGroups, { Plots=pGroup, CenterX=x, CenterY=y });
end

-- 上一个/下一个结果
function OnNextResult()
    m_FocusedResult = m_FocusedResult + 1;
    if m_FocusedResult > #m_ResultGroups then m_FocusedResult = 1; end
    UI.LookAtPosition(m_ResultGroups[m_FocusedResult].CenterX,
                      m_ResultGroups[m_FocusedResult].CenterY);
end
```

## 模式 7: 搜索建议 (自动补全)

两个 EditBox 各自维护独立的建议面板和历史记录：

```lua
function UpdateSuggestions(pEditBox, pSuggestionPanel, pInstanceManager, pHistoryList)
    pInstanceManager:ResetInstances();
    local str = pEditBox:GetText();

    if str == nil or string.len(str) == 0 then
        -- 无输入时显示历史记录
        for _, szSuggestion in pairs(pHistoryList) do
            local pInstance = pInstanceManager:GetInstance();
            pInstance.SuggestionButton:SetText(szSuggestion);
        end
        m_TabCompleteString = pHistoryList[1];
    else
        -- 有输入时从 Suggestions 上下文搜索
        local results = Search.Search(SEARCHCONTEXT_SUGGESTIONS, str, 14);
        for _, result in pairs(results) do
            local pInstance = pInstanceManager:GetInstance();
            pInstance.SuggestionButton:SetText(result[1]);
        end
        m_TabCompleteString = results and results[1] and results[1][1];
    end

    -- 通过 Timer 延迟隐藏建议（让点击事件能触发）
    -- 失去焦点时: Controls.SearchSuggestionsTimer:Play();
end
```

Tab 键自动补全：`OnInputHandler` 中检测 `Keys.VK_TAB`，将 `m_TabCompleteString` 写入 EditBox。

## 模式 8: 搜索历史管理

最大 8 条历史（原版 5 条），去重 + LIFO：

```lua
function UpdateHistory(pHistoryTable, szNewString)
    -- 去重
    for i, szString in ipairs(pHistoryTable) do
        if szNewString == szString then table.remove(pHistoryTable, i); end
    end
    -- 插入最前
    table.insert(pHistoryTable, 1, szNewString);
    -- 裁剪
    while table.count(pHistoryTable) > MAXIMUM_SEARCH_HISTORY do
        table.remove(pHistoryTable);
    end
end
```

搜索栏和过滤栏各自独立维护历史。

## 模式 9: 快捷选择面板系统

提供分类快捷面板，点击即可追加搜索词到搜索/过滤框：

```
资源面板 (MSEResGrid1-5):
  - 战略资源 / 奢侈品 / 加成资源 / 遗物 / 次要文明奢侈品
  - 按首字母排序，每个资源以图标按钮呈现

文明面板 (MseStackCivilizations):
  - 列举所有已相遇的文明/城邦
  - 含文明图标 + 领袖图标 + 类型专属颜色

单位面板 (MseStackUni):
  - 按类型分组（贸易/支援/伟人/平民/反空/空军/近战远程/海军）
  - 颜色编码区分单位类型

改良面板 (MseStackImprovements):
  - 分组：可移除改良 / 普通改良 / 文明专属改良

奇观面板 (MseStackWonders):
  - 从 GameInfo.Buildings() 筛选 IsWonder=true
```

面板通过按钮切换，互斥显示（`MseHideAllSelectorPanels()` 后再显示目标面板）。

## 模式 10: 词条目标路由

可选择将快捷面板的词条填入搜索框（Whitelist）或过滤框（Blacklist）：

```lua
termDestinationEditBox = Controls.MapSearchBox; -- 或 Controls.MapSearchFilterBox

-- 切换按钮
Controls.MSEBtnSelSearchBar:RegisterCallback(click, MseSetDestinationFilter); -- 注意：按钮故意反过来
Controls.MSEBtnSelFilterBar:RegisterCallback(click, MseSetDestinationSearch);

-- EditBox 获焦时自动切换目的地
Controls.MapSearchBox:RegisterHasFocusCallback(MseSetDestinationSearch);
Controls.MapSearchFilterBox:RegisterHasFocusCallback(MseSetDestinationFilter);
```

词条追加模式（勾选 "追加" CheckBox 时用空格连接，否则替换）：
```lua
function AppendSuggestionText(szSuggestion)
    if not Controls.MseCBAppend:IsChecked() or termDestinationEditBox:GetText() == nil then
        termDestinationEditBox:SetText(szSuggestion);
    else
        termDestinationEditBox:SetText(termDestinationEditBox:GetText() .. " " .. szSuggestion);
    end
end
```

## 模式 11: 地块过滤 (Tile Criteria)

搜索前预过滤地块所有者：

```lua
function IsTileMatchesCriteria(iPlot)
    local eObserverID = Game.GetLocalObserver();
    return CheckOwnedByMeCriteria(iPlot)
        or CheckOwnedByOthersCriteria(iPlot)
        or CheckOwnedByNoneCriteria(iPlot)
        or CheckNearPlayerCityCriteria(iPlot, eObserverID);
end
```

三个 CheckBox 控制：
- 我拥有的 (`MseCBOwnerMe`)
- 他人拥有的 (`MseCBOwnerOthers`)
- 无主地块 (`MseCBOwnerNone`)
- 我可购买的地块 (`MseCBPurchasedByMe`) — 搜索城市 3 格范围内无主地块

## 模式 12: 搜索结果颜色自定义

用 PullDown 选择三种颜色（填充色、边框色1、边框色2）：

```lua
-- 颜色定义
fillColor = UI.GetColorValueFromHexLiteral(0x2800FF00);      -- 默认半透明绿
borderColor1 = UI.GetColorValueFromHexLiteral(0x66FFFFFF);   -- 默认半透明白
borderColor2 = UI.GetColorValueFromHexLiteral(0x66FFFFFF);   -- 默认半透明白

-- 应用
local pOverlay = UILens.GetOverlay("MapSearch");
pOverlay:SetBorderColors(0, borderColor1, borderColor2);
pOverlay:SetHighlightColor(0, fillColor);
```

## 模式 13: DLC 兼容覆写

运行时检测 DLC 并扩展功能：

```lua
function IsXP2()
    if GameInfo.Units_XP2 ~= nil then return true; end
    return false;
end

if IsXP2() then
    -- 缓存原函数
    BASE_FetchData = FetchData;
    -- 覆写: 先调原始获取，再追加 XP2 数据
    function FetchData(plot)
        local data = BASE_FetchData(plot);
        data.IsVolcano = MapFeatureManager.IsVolcano(plot);
        data.Storm = GameClimate.GetActiveStormTypeAtPlot(plot);
        -- ...
        return data;
    end
end
```

对其他 Mod 的兼容性：
```lua
-- 检测特定 Mod
local isARSActive = Modding.IsModActive("42F8CFFC-07EF-8F69-4302-67F277A6042D");
if isARSActive then
    FormationClassNameMap["FORMATION_CLASS_LAND_RANGED"] = ...;  -- 补充新 formation class
end
```

## 模式 14: 运行时刷新搜索结果

每回合开始时自动重新搜索（如果之前有搜索条件）：

```lua
Events.PlayerTurnActivated.Add(OnPlayerTurnActivated);
function OnPlayerTurnActivated(ePlayer, isFirstTimeThisTurn)
    if Game.GetLocalPlayer() == ePlayer then
        RefreshMapSearchResults();  -- 重新执行增量搜索
    end
end
```

## 关键 API

| API | 用途 |
|-----|------|
| `Search.CreateContext(name, primaryKey, sortKey, data)` | 创建搜索上下文 |
| `Search.AddData(ctx, primaryKey, sortKey, data)` | 向上下文添加数据 |
| `Search.Search(ctx, term, maxResults)` | 执行搜索 |
| `Search.Optimize(ctx)` | 优化索引（搜索前必须调用） |
| `Search.ClearData(ctx)` | 清理上下文数据 |
| `Search.DestroyContext(ctx)` | 销毁上下文 |
| `UILens.GetOverlay("MapSearch")` | 获取地图搜索覆盖层 |
| `pOverlay:SetPlotChannel(plots, channel)` | 高亮指定图块 |
| `pOverlay:SetHighlightColor(channel, color)` | 设置高亮颜色 |
| `pOverlay:SetBorderColors(channel, c1, c2)` | 设置边框颜色 |
| `UI.PartitionRegions(plots)` | 将图块按相邻关系分组 |
| `UI.GetRegionCenter(pGroup)` | 获取区域中心坐标 |
| `UI.LookAtPosition(x, y)` | 移动镜头到指定位置 |
| `ContextPtr:SetUpdate(callback)` | 注册每帧更新回调 |
| `ContextPtr:ClearUpdate()` | 清除每帧更新 |
| `Map.GetPlotCount()` | 获取地图总图块数 |
| `Map.GetPlotByIndex(index)` | 按索引获取 plot |
| `MapFeatureManager.IsVolcano(plot)` | 火山检测 (XP2) |
| `GameClimate.GetActiveStormTypeAtPlot(plot)` | 活跃风暴 (XP2) |
| `TerrainManager.GetCoastalLowlandType(plot)` | 沿海低地海拔 (XP2) |
| `RiverManager.GetRiverTypes(plot)` | 获取经过该地块的所有河流 |
| `Territories.GetTerritoryAt(plotIndex)` | 获取地块所属领土 |
| `Game.GetBarbarianManager():GetTribeIndexAtLocation(x, y)` | 蛮族部落位置 |
| `Modding.IsModActive(modGuid)` | 检测 Mod 是否激活 |

## 重要细节

- `Search.AddData` 的 data 参数是一个 table of strings，不是单个字符串
- `Search.Search` 每次搜索最多处理 35 个地块，超出的下帧继续
- 搜索建议面板隐藏用 Timer 延迟，确保鼠标点击建议条目不会被焦点丢失事件抢先隐藏
- `EditBox` 的 `RegisterCommitCallback` 在按回车或焦点离开时触发
- `RegisterStringChangedCallback` 在每次文本变化时触发（用于实时更新建议）
- 两位玩家同步搜索时可能会相互干扰 overlay 状态
- 在 `InterfaceModeTypes.CINEMATIC` 模式下需要隐藏搜索 overlay
- `GameCoreEventPlaybackComplete` 事件在多人游戏中可用于检测回放结束
- 蛮族部落名称前缀为 `LOC_` 直接拼接到 TribeNameType
- BuildInstanceForControl 创建的重叠面板需用 Offset 控制布局，避免遮挡

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `MapSearchPanel.xml` | 地图搜索主面板 + 快速选择面板 + 搜索选项面板 + 所有 Instance 模板 |

### 搜索主面板控件 ID 对照

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `MapSearchPanel` | Grid | `Controls.MapSearchPanel` | 搜索面板根容器（320xauto，Tracker_OptionsBacking） |
| `MapSearchBox` | EditBox | `Controls.MapSearchBox` | 搜索词编辑框（白名单） |
| `MapSearchFilterBox` | EditBox | `Controls.MapSearchFilterBox` | 过滤词编辑框（黑名单） |
| `MseRemoveLastWordSearch` | GridButton | `Controls.MseRemoveLastWordSearch` | 删除搜索框最后一个词 |
| `MseRemoveLastWordFilter` | GridButton | `Controls.MseRemoveLastWordFilter` | 删除过滤框最后一个词 |
| `SearchButton` | GridButton | `Controls.SearchButton` | 开始搜索按钮 |
| `ClearButton` | GridButton | `Controls.ClearButton` | 清除搜索结果 |
| `MseSearchOptionsBtn` | GridButton | `Controls.MseSearchOptionsBtn` | 搜索选项按钮（颜色设置） |
| `MseCBAppend` | CheckBox | `Controls.MseCBAppend` | 追加模式（空格连接而非替换） |
| `PrevResultButton` / `NextResultButton` | Button | `Controls.PrevResultButton` / `Controls.NextResultButton` | 上一个/下一个搜索结果导航 |
| `ResultsLabel` | Label | `Controls.ResultsLabel` | 搜索结果数量标签 |
| `ProgressBar` | Bar | `Controls.ProgressBar` | 增量搜索进度条 |
| `SearchSuggestions` | Grid | `Controls.SearchSuggestions` | 搜索建议下拉面板 |
| `SearchSuggestionStack` | Stack | `Controls.SearchSuggestionStack` | 搜索建议条目挂载点 |
| `FilterSuggestions` | Grid | `Controls.FilterSuggestions` | 过滤建议下拉面板 |
| `FilterSuggestionStack` | Stack | `Controls.FilterSuggestionStack` | 过滤建议条目挂载点 |
| `SearchSuggestionsTimer` | AlphaAnim | `Controls.SearchSuggestionsTimer` | 建议面板延迟隐藏动画 |

### 地块过滤 Criteria CheckBox

| XML 控件（ID） | Lua 引用 | 用途 |
|---------------|---------|------|
| `MseCBOwnerMe` | `Controls.MseCBOwnerMe` | 搜索我拥有的地块 |
| `MseCBOwnerOthers` | `Controls.MseCBOwnerOthers` | 搜索他人拥有的地块 |
| `MseCBOwnerNone` | `Controls.MseCBOwnerNone` | 搜索无主地块 |
| `MseCBPurchasedByMe` | `Controls.MseCBPurchasedByMe` | 搜索我可购买的地块（城市 3 格内） |

### 快速选择面板按钮

| XML 控件（ID） | Lua 引用 | 用途 |
|---------------|---------|------|
| `MSEBtnSelSearchBar` | GridButton | 词条目标路由到搜索框 |
| `MSEBtnSelFilterBar` | GridButton | 词条目标路由到过滤框 |
| `MSEBtnSelRes` | Button | 打开资源快捷面板 |
| `MSEBtnSelCivil` | Button | 打开文明快捷面板 |
| `MSEBtnSelUnits` | Button | 打开单位快捷面板 |
| `MSEBtnSelImpr` | Button | 打开改良快捷面板 |
| `MSEBtnSelWond` | Button | 打开奇观快捷面板 |

### 快捷面板容器 ID 对照

| 面板 Grid ID | 内部 Stack ID | 用途 |
|-------------|-------------|------|
| `ExtendedMapSearchPanelSuggestionsRes` | `MSEResGrid1`~`MSEResGrid5` | 资源面板（战略/奢侈/加成/遗物/次要奢侈） |
| `ExtendedMapSearchPanelSuggestionsCivil` | `MseStackCivilizations` | 文明/城邦面板 |
| `ExtendedMapSearchPanelSuggestionsUnits` | `MseStackUni` | 单位面板 |
| `ExtendedMapSearchPanelSuggestionsImpr` | `MseStackImprovements` | 改良面板 |
| `ExtendedMapSearchPanelSuggestionsWon` | `MseStackWonders` | 奇观面板 |
| `MSESearchOptions` | `MSEColorPD1`/`PD2`/`PD3` | 搜索选项面板（颜色） |

### Instance 模板

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `SuggestionEntry` | 搜索建议条目 | `SuggestionButton`(GridButton, 26px 高) |
| `ResEntry` | 资源快捷条目 | `ResButton`(GridButton, 28x28), `MseResLbl`(Label) |
| `MseCivilizationEntry` | 文明快捷条目 | `CivButton`(GridButton), `CivIcon`(Image, 44x44), `LeaderIcon`(Image, 45x45) |
| `MseUnitTypeListEntry` | 单位快捷条目 | `UnitTypeButton`(GridButton), `UnitTypeIcon`(Image, 22x22) |
| `MseWonderListEntry` | 奇观快捷条目 | `MSEWonderButton`(GridButton), `MSEWonderIcon`(Image, 38x38) |

### 布局架构

```
MapSearchPanel (Grid, 320xauto)              ← 搜索主面板
ExtendedMapSearchPanelSelection (Grid, 80)    ← 快速选择面板（垂直按钮列）
MSESearchOptions (Grid, 380)                  ← 搜索选项面板（颜色 PullDown）
ExtendedMapSearchPanelSuggestionsRes/Civil/Units/Impr/Won (Grid, 337~380)
                                              ← 5 个互斥的快捷面板
```

所有面板都 `Hidden="1"` 默认隐藏，通过选择器按钮互斥显示（`MseHideAllSelectorPanels()` 后再显示目标面板）。
