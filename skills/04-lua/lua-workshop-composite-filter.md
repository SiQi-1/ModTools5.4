# 复合过滤与下拉菜单模式（来源：Better Religion Screen）

## 做什么
在一个数据面板上提供多个独立的过滤维度，每个维度通过下拉菜单（PullDown）选择，过滤变化时立即刷新数据列表。与单一排序/过滤不同，多个过滤条件独立作用，形成笛卡尔积过滤效果。

## 涉及文件

| 文件 | 来源 Mod | 角色 |
|------|---------|------|
| `ReligionScreen.lua` | Better Religion Screen (2145663327) | 城市过滤 + 文明过滤的实现 |
| `ReligionScreen.xml` | Better Religion Screen | PullDown 容器定义 |

## 技术原理

### XML 中的下拉菜单

```xml
<!-- 城市排序类型下拉 -->
<PullDown ID="FilterType" Size="240" Offset="32,-5" Style="SmallPullDown" />
<!-- 文明过滤下拉 -->
<PullDown ID="FilterCiv" Size="95" Offset="270,-5" Style="SmallPullDown" />
```

### 过滤维度定义

```lua
-- 维度 1：城市排序类型（4 种）
local CITIES_FILTER = {
    FOLLOWING_RELIGION   = 1,  -- 信仰此宗教的城市
    RELIGION_PRESENT     = 2,  -- 有该宗教存在的城市
    NOT_FOLLOWING_RELIGION = 3,  -- 不信仰此宗教的城市
    ALL_CITIES           = 4,  -- 所有城市
}

-- 维度 2：文明过滤
--    -1 = 全部
--    -2 = 城邦
--    >=0 = 特定文明 playerID

-- 当前过滤状态
local m_CitiesFilter = CITIES_FILTER.NOT_FOLLOWING_RELIGION
local m_CivFilter = -1  -- 默认全部
```

### 下拉菜单填充

```lua
function PopulateSortType()
    -- 定义的显示顺序
    local sortOrder = {
        CITIES_FILTER.ALL_CITIES,
        CITIES_FILTER.RELIGION_PRESENT,
        CITIES_FILTER.FOLLOWING_RELIGION,
        CITIES_FILTER.NOT_FOLLOWING_RELIGION
    }

    for _, sortType in ipairs(sortOrder) do
        local control = {}
        Controls.FilterType:BuildEntry("SmallItemInstance", control)
        control.Button:SetSizeX(Controls.FilterType:GetSizeX())
        control.DescriptionText:SetOffsetX(10)

        -- 设置显示文本
        if sortType == CITIES_FILTER.ALL_CITIES then
            control.DescriptionText:LocalizeAndSetText("LOC_BRW_CITY_SORT_ALL")
        elseif sortType == CITIES_FILTER.RELIGION_PRESENT then
            control.DescriptionText:LocalizeAndSetText("LOC_UI_RELIGION_CITY_SORT_TYPE_PRESENT")
        elseif sortType == CITIES_FILTER.FOLLOWING_RELIGION then
            control.DescriptionText:LocalizeAndSetText("LOC_UI_RELIGION_CITY_SORT_TYPE_FOLLOWING")
        elseif sortType == CITIES_FILTER.NOT_FOLLOWING_RELIGION then
            control.DescriptionText:LocalizeAndSetText("LOC_BRW_CITY_SORT_NOT_FOLLOWING")
        end

        -- 点击回调
        control.Button:RegisterCallback(Mouse.eLClick,
            function() OnSortTypeChanged(sortType) end)
        control.Button:RegisterCallback(Mouse.eMouseEnter,
            function() UI.PlaySound("Main_Menu_Mouse_Over") end)
    end
    Controls.FilterType:CalculateInternals()
end

function PopulateSortCiv()
    local function AddSingleEntry(civID, civName)
        local control = {}
        Controls.FilterCiv:BuildEntry("SmallItemInstance", control)
        control.Button:SetSizeX(Controls.FilterCiv:GetSizeX())
        control.DescriptionText:SetOffsetX(10)
        control.DescriptionText:SetText(civName)
        control.Button:RegisterCallback(Mouse.eLClick,
            function() OnSortCivChanged(civID) end)
        control.Button:RegisterCallback(Mouse.eMouseEnter,
            function() UI.PlaySound("Main_Menu_Mouse_Over") end)
    end

    local localPlayerID = GetDisplayPlayerID()
    local localDiplomacy = Players[localPlayerID]:GetDiplomacy()

    -- "全部"选项
    AddSingleEntry(-1, LL("LOC_GOVT_FILTER_NONE"))

    -- 每个已知的主要文明
    for _, playerID in ipairs(PlayerManager.GetAliveMajorIDs()) do
        if playerID == localPlayerID or localDiplomacy:HasMet(playerID) then
            AddSingleEntry(playerID,
                LL(PlayerConfigurations[playerID]:GetCivilizationShortDescription()))
        end
    end

    -- 城邦选项
    AddSingleEntry(-2, LL("LOC_CITY_STATES_TITLE"))

    Controls.FilterCiv:CalculateInternals()
end
```

### 选中状态管理：RealizeSortTypePulldown

```lua
function RealizeSortTypePulldown()
    local pullDownButton = Controls.FilterType:GetButton()
    if m_CitiesFilter == CITIES_FILTER.ALL_CITIES then
        pullDownButton:SetText("  " .. LL("LOC_BRW_CITY_SORT_ALL"))
    elseif m_CitiesFilter == CITIES_FILTER.RELIGION_PRESENT then
        pullDownButton:SetText("  " .. LL("LOC_UI_RELIGION_CITY_SORT_TYPE_PRESENT"))
    elseif m_CitiesFilter == CITIES_FILTER.FOLLOWING_RELIGION then
        pullDownButton:SetText("  " .. LL("LOC_UI_RELIGION_CITY_SORT_TYPE_FOLLOWING"))
    elseif m_CitiesFilter == CITIES_FILTER.NOT_FOLLOWING_RELIGION then
        pullDownButton:SetText("  " .. LL("LOC_BRW_CITY_SORT_NOT_FOLLOWING"))
    end
end

function RealizeSortCivPulldown()
    local pullDownButton = Controls.FilterCiv:GetButton()
    if m_CivFilter == -1 then
        pullDownButton:SetText("  " .. LL("LOC_GOVT_FILTER_NONE"))
    elseif m_CivFilter == -2 then
        pullDownButton:SetText("  " .. LL("LOC_CITY_STATES_TITLE"))
    else
        local player = Players[m_CivFilter]
        if player ~= nil and player:IsAlive() and player:IsMajor() then
            pullDownButton:SetText("  " .. LL(
                PlayerConfigurations[m_CivFilter]:GetCivilizationShortDescription()))
        end
    end
end
```

### 过滤变化回调

```lua
function OnSortTypeChanged(filterType)
    if filterType ~= m_CitiesFilter then
        m_CitiesFilter = filterType
        -- 刷新数据：重新读取 cities 并 rebind UI
        ViewReligion(m_SelectedReligion.ID)
    end
end

function OnSortCivChanged(filterCiv)
    if filterCiv ~= m_CivFilter then
        m_CivFilter = filterCiv
        ViewReligion(m_SelectedReligion.ID)
    end
end
```

### 过滤逻辑在数据收集循环中

```lua
for _, player in ipairs(majorPlayers) do
    local playerID = player:GetID()
    local playerCities = player:GetCities()

    -- === 文明过滤 ===
    local bIncludeCiv = false
    if m_CivFilter == -1 then
        bIncludeCiv = true                    -- 全部
    elseif m_CivFilter == -2 and not PlayerManager.IsMajor(playerID) then
        bIncludeCiv = true                    -- 仅城邦
    elseif m_CivFilter == playerID then
        bIncludeCiv = true                    -- 特定文明
    end

    for _, city in playerCities:Members() do
        -- === 城市类型过滤 ===
        local bIncludeCity = false
        local cityReligion = city:GetReligion()

        if cityReligion:GetMajorityReligion() == religionType then
            if m_CitiesFilter == CITIES_FILTER.FOLLOWING_RELIGION then
                bIncludeCity = true
            end
        else
            if m_CitiesFilter == CITIES_FILTER.NOT_FOLLOWING_RELIGION then
                bIncludeCity = true
            end
        end

        -- 检查该宗教是否存在于本城市
        for _, cityReligionData in ipairs(cityReligion:GetReligionsInCity()) do
            if m_CitiesFilter == CITIES_FILTER.RELIGION_PRESENT
               and cityReligionData.Religion == religionType then
                bIncludeCity = true
            end
            if m_CitiesFilter == CITIES_FILTER.ALL_CITIES then
                bIncludeCity = true            -- 覆盖前面的排除
            end
        end

        -- 两个过滤条件都满足才加入列表
        if bIncludeCity and bIncludeCiv then
            table.insert(cities, { City = city, ... })
        end
    end
end
```

### 关键：ALL_CITIES 覆盖逻辑

```lua
-- 注意：ALL_CITIES 必须在循环内部设置，且放在最后
-- 这样它会覆盖前面的 FOLLOWING_RELIGION / NOT_FOLLOWING_RELIGION 判断
if m_CitiesFilter == CITIES_FILTER.ALL_CITIES then
    bIncludeCity = true  -- 覆盖
end
```

## 模式模板

```lua
-- ===========================================================================
-- 复合过滤模式模板
-- ===========================================================================

-- 过滤维度定义
local SORT_BY = { NAME = 1, VALUE = 2, TYPE = 3 }
local FILTER_BY_SOURCE = { ALL = -1, SOURCE_A = 1, SOURCE_B = 2 }

local m_SortBy = SORT_BY.NAME
local m_FilterSource = FILTER_BY_SOURCE.ALL

-- 下拉填充（Init 时调用一次）
function PopulatePulldowns()
    -- 排序下拉
    for _, sortType in ipairs({SORT_BY.NAME, SORT_BY.VALUE, SORT_BY.TYPE}) do
        local control = {}
        Controls.SortPulldown:BuildEntry("SmallItemInstance", control)
        control.DescriptionText:SetText(GetSortName(sortType))
        control.Button:RegisterCallback(Mouse.eLClick,
            function() OnSortChanged(sortType) end)
    end
    Controls.SortPulldown:CalculateInternals()

    -- 来源过滤下拉
    for _, filterVal in ipairs(GetAvailableSourceValues()) do
        local control = {}
        Controls.FilterPulldown:BuildEntry("SmallItemInstance", control)
        control.DescriptionText:SetText(GetFilterName(filterVal))
        control.Button:RegisterCallback(Mouse.eLClick,
            function() OnFilterChanged(filterVal) end)
    end
    Controls.FilterPulldown:CalculateInternals()
end

-- 下拉选中文本更新
function RealizePulldownLabels()
    Controls.SortPulldown:GetButton():SetText(
        "  " .. GetSortName(m_SortBy))
    Controls.FilterPulldown:GetButton():SetText(
        "  " .. GetFilterName(m_FilterSource))
end

-- 过滤变化回调
function OnSortChanged(newSort)
    if newSort ~= m_SortBy then
        m_SortBy = newSort
        RefreshDataView()
    end
end

function OnFilterChanged(newFilter)
    if newFilter ~= m_FilterSource then
        m_FilterSource = newFilter
        RefreshDataView()
    end
end

-- 数据收集（在渲染函数中）
function CollectFilteredData()
    local result = {}
    for _, item in ipairs(allItems) do
        -- 逐层过滤
        local bInclude = true

        -- 来源过滤
        if m_FilterSource ~= FILTER_BY_SOURCE.ALL
           and item.Source ~= m_FilterSource then
            bInclude = false
        end

        if bInclude then
            table.insert(result, item)
        end
    end

    -- 排序
    table.sort(result, function(a, b)
        if m_SortBy == SORT_BY.NAME then
            return a.Name < b.Name
        elseif m_SortBy == SORT_BY.VALUE then
            return a.Value > b.Value
        else
            return a.Type < b.Type
        end
    end)

    return result
end

function RefreshDataView()
    RealizePulldownLabels()
    local data = CollectFilteredData()
    RenderDataList(data)
end
```

## 设计要点

1. **PullDown.BuildEntry**：用此方法动态添加下拉选项，而非在 XML 中写死
2. **CalculateInternals**：填充选项后必须调用，否则下拉不显示新条目
3. **PullDown.GetButton**：获取下拉的触发按钮以设置当前选中文本
4. **过滤回调中重新渲染**：`OnXxxChanged` → 更新成员变量 → 调用渲染函数重新生成列表
5. **ALL_XXX 覆盖逻辑**：ALL 选项必须放在过滤链最后，覆盖前面的排除判断
6. **独立维度互不干扰**：两个过滤条件分别判断，用 `bIncludeA and bIncludeB` 组合
7. **下拉填充只做一次**：在 `OnInit` 中填充，后续只需更新选中文本和重新渲染

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `UI/ReligionScreen.xml` | Better Religion Screen 完整布局 — 含 FilterType/FilterCiv PullDown + 所有面板容器 |

### 过滤 PullDown 控件 ID 对照

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `FilterType` | PullDown | `Controls.FilterType` | 城市排序类型下拉（240px，SmallPullDown 样式） |
| `FilterCiv` | PullDown | `Controls.FilterCiv` | 文明过滤下拉（95px，SmallPullDown 样式） |

### PullDown 操作关键 Lua API

| 操作 | API |
|------|-----|
| 添加条目 | `Controls.FilterType:BuildEntry("SmallItemInstance", control)` |
| 计算布局 | `Controls.FilterType:CalculateInternals()` |
| 获取下拉按钮 | `Controls.FilterType:GetButton()` |
| 设置选中文本 | `pullDownButton:SetText("  " .. LL("LOC_KEY"))` |

### BuildEntry 创建的控件

每个条目通过 `BuildEntry` 动态创建，对应的控件 ID：

| 动态控件 ID | 类型 | 用途 |
|-----------|------|------|
| `Button` | Button | 条目的点击按钮 |
| `DescriptionText` | Label | 条目的显示文本 |

### PullDown XML 结构

```xml
<PullDown ID="FilterType" Size="240" Offset="32,-5" Style="SmallPullDown" />
<PullDown ID="FilterCiv" Size="95" Offset="270,-5" Style="SmallPullDown" />
```

两个 PullDown 在 ReligionScreen.xml 中位于 `TabContainer` 下方、主内容面板上方。它们不包含预定义的 `<ButtonData>`/`<GridData>` 等子结构——所有条目均在 Lua 中通过 `BuildEntry` 动态填充。

### 面板容器上下文

过滤 PullDown 所在的上下文面板：

| Container ID | 用途 |
|-------------|------|
| `WorkingTowards` | 尚未创建宗教时的显示 |
| `SelectBeliefs` | 选择信条面板（含 ChooseBelief 网格 + Reselect/Confirm 按钮） |
| `AddBeliefs` | 为已有宗教添加信条面板（结构同 SelectBeliefs 但尺寸不同） |
| `ChooseReligion` | 选择宗教面板（含宗教图标选择列表） |

过滤 PullDown 在切换到"查看宗教"视图时显示，位于这些面板的工具栏区域。
