# 多列排序栏 + Shift/Ctrl 优先排序（来源：工坊 873246701）

## 做什么
实现一个交互式排序栏：多个产出列的按钮支持点击切换升序/降序，Shift+点击追加排序优先级（多级排序），Ctrl+点击设置组内排序，按钮上显示数字表示优先级顺序。

## 如何挂载到官方UI

排序栏是面板 XML 内部的自定义控件，通过 Stack 水平排列各产出列按钮来构建。

## 关键 Lua 代码

### 排序常量定义

```lua
SORT_BY_ID = {
    FOOD = 1,  PRODUCTION = 2,  GOLD = 3,
    SCIENCE = 4,  CULTURE = 5,  FAITH = 6,
    TURNS_TO_COMPLETE = 7
}
SORT_ASCENDING = 1;
SORT_DESCENDING = 2;
```

### 排序设置结构

每个排序设置是一个表数组，按优先级排列：
```lua
-- 例如：先按产能降序，再按回合数升序
m_SortBySettings = {
    { SortByID = SORT_BY_ID.PRODUCTION,       SortOrder = SORT_DESCENDING },
    { SortByID = SORT_BY_ID.TURNS_TO_COMPLETE, SortOrder = SORT_ASCENDING  },
}
```

### 分数计算函数

```lua
ScoreFunctionByID = {}
ScoreFunctionByID[SORT_BY_ID.FOOD]    = function(a) return GetYieldForOriginCity(a, FOOD_INDEX) end
ScoreFunctionByID[SORT_BY_ID.GOLD]    = function(a) return GetYieldForOriginCity(a, GOLD_INDEX) end
ScoreFunctionByID[SORT_BY_ID.TURNS_TO_COMPLETE] = function(a) return GetTurnsToComplete(a) end
-- ...

function ScoreRoute(routeInfo, sortSettings)
    local score = {}
    for _, sortSetting in ipairs(sortSettings) do
        local val = ScoreFunctionByID[sortSetting.SortByID](routeInfo)
        -- 降序时取反以实现反向比较
        if sortSetting.SortOrder == SORT_DESCENDING then
            if type(val) == "string" then
                val = invert_string(val)
            else
                val = val * -1
            end
        end
        score[#score + 1] = val
    end
    score[#score + 1] = GetNetYieldForOriginCity(routeInfo)  -- 最终决胜：总产出
    return score
end

function ScoreComp(scoreInfo1, scoreInfo2)
    local score1 = scoreInfo1.score
    local score2 = scoreInfo2.score
    for i = 1, #score1 - 1 do  -- 最后一个是 net yield
        if score1[i] < score2[i] then return true end
        if score1[i] > score2[i] then return false end
    end
    return score1[#score1] > score2[#score1]  -- 降序比较净产出
end
```

### 排序条复制新（隐藏所有箭头，再显示活跃的）

```lua
function ResetSortBar()
    Controls.FoodDescArrow:SetHide(true);
    Controls.FoodAscArrow:SetHide(true);
    Controls.ProductionDescArrow:SetHide(true);
    Controls.ProductionAscArrow:SetHide(true);
    -- ... 全部隐藏
end

function RefreshSortButtons(sortSettings)
    ResetSortBar();

    -- 重置所有按钮颜色为禁用
    Controls.FoodSortButton:SetColorByName("ButtonDisabledCS");
    -- ...

    -- 遍历当前排序设置，显示箭头
    for _, sortEntry in ipairs(sortSettings) do
        if sortEntry.SortByID == SORT_BY_ID.FOOD then
            SetSortArrow(Controls.FoodAscArrow, Controls.FoodDescArrow, sortEntry.SortOrder)
            Controls.FoodSortButton:SetColorByName("ButtonCS");  -- 亮色表示激活
        elseif sortEntry.SortByID == SORT_BY_ID.PRODUCTION then
            -- ...
        end
    end
end
```

### 箭头切换

```lua
function SetSortArrow(ascArrow, descArrow, sortOrder)
    if sortOrder == SORT_ASCENDING then
        descArrow:SetHide(true);
        ascArrow:SetHide(false);
    else
        descArrow:SetHide(false);
        ascArrow:SetHide(true);
    end
end
```

### 排序按钮点击处理（Shift 多级、Ctrl 组内）

```lua
function OnGeneralSortBy(descArrowControl, sortByID)
    -- Shift 未按下 → 重置排序
    if not m_shiftDown then
        if not m_ctrlDown then
            m_GroupSortBySettings[m_currentTab] = {};  -- 重置总排序
        end
        m_InGroupSortBySettings[m_currentTab] = {};     -- 重置组内排序
    end

    -- 始终移除旧的"回合数升序"（会在后面重新追加）
    RemoveSortEntry(SORT_BY_ID.TURNS_TO_COMPLETE, m_InGroupSortBySettings[m_currentTab]);

    -- 根据当前箭头状态切换
    if descArrowControl:IsHidden() then
        if not m_ctrlDown then
            InsertSortEntry(sortByID, SORT_DESCENDING, m_GroupSortBySettings[m_currentTab]);
        end
        InsertSortEntry(sortByID, SORT_DESCENDING, m_InGroupSortBySettings[m_currentTab]);
    else
        if not m_ctrlDown then
            InsertSortEntry(sortByID, SORT_ASCENDING, m_GroupSortBySettings[m_currentTab]);
        end
        InsertSortEntry(sortByID, SORT_ASCENDING, m_InGroupSortBySettings[m_currentTab]);
    end

    -- 始终追加回合数升序作为组内最终决胜
    InsertSortEntry(SORT_BY_ID.TURNS_TO_COMPLETE, SORT_ASCENDING, m_InGroupSortBySettings[m_currentTab]);

    RefreshSortBar();
    if not m_shiftDown then
        Refresh();  -- 立即刷新排序
    else
        m_sortCallRefresh = true;  -- 等 Shift 松开后再刷新
    end
end
```

### 右键删除排序

```lua
function OnGeneralNotSortBy(sortByID)
    if not m_ctrlDown then
        RemoveSortEntry(sortByID, m_GroupSortBySettings[m_currentTab]);
    end
    RemoveSortEntry(sortByID, m_InGroupSortBySettings[m_currentTab]);

    RefreshSortBar();
    if not m_shiftDown then Refresh(); else m_sortCallRefresh = true; end
end
```

### Shift/Ctrl 状态追踪

```lua
function KeyDownHandler(key)
    if key == Keys.VK_SHIFT then
        m_shiftDown = true;
        ShowSortOrderLabels();  -- 显示优先级数字
    end
    if key == Keys.VK_CONTROL then
        m_ctrlDown = true;
        RefreshSortBar();  -- 切换到组内排序视图
    end
    return false;  -- 让事件继续传播
end

function KeyUpHandler(key)
    if key == Keys.VK_SHIFT then
        m_shiftDown = false;
        if m_sortCallRefresh then
            Refresh();  -- 延迟刷新
            m_sortCallRefresh = false;
        end
        HideSortOrderLabels();
    end
    if key == Keys.VK_CONTROL then
        m_ctrlDown = false;
        RefreshSortBar();  -- 切换回总排序视图
    end
    -- ...
end
```

### 优先级数字显示/隐藏

```lua
function ShowSortOrderLabels()
    -- 在对应按钮上显示优先级序号
    for index, sortEntry in ipairs(sortSettings) do
        if sortEntry.SortByID == SORT_BY_ID.FOOD then
            Controls.FoodSortOrder:SetHide(false);
            Controls.FoodSortOrder:SetText(index);
        elseif sortEntry.SortByID == SORT_BY_ID.PRODUCTION then
            Controls.ProductionSortOrder:SetHide(false);
            Controls.ProductionSortOrder:SetText(index);
        -- ...
        end
    end
end
```

## XML 控件定义

### 排序栏结构

```xml
<Stack Size="50,50" Anchor="L,B" StackGrowth="Right" Offset="82,-9" StackPadding="2">
  <GridButton ID="FoodSortButton" ToolTip="LOC_TRADE_SORT_BY_FOOD_TOOLTIP"
              Size="48,parent-17" Style="PanelButtonLightweight">
    <Label ID="FoodSortOrder" Hidden="1" Anchor="C,C" Offset="1,0" String="9" Style="FontNormal12"/>
    <Label ID="FoodSortLabel" Anchor="C,C" Offset="15,1" Style="FontNormal12" String="[Icon_Food]"/>
    <Image ID="FoodDescArrow" Texture="Controls_ButtonExtendSmall2" TextureOffset="0,0"
           Size="20,16" Anchor="C,C" Offset="-12,0"/>
    <Image ID="FoodAscArrow" Texture="Controls_ButtonExtendSmall2" TextureOffset="0,60"
           Size="20,16" Anchor="C,C" Offset="-12,-4"/>
  </GridButton>

  <!-- Production, Gold, Science, Culture, Faith, TurnsToComplete 同理 -->
</Stack>
```

每个排序按钮包含：
- **SortOrder Label** — 优先级数字（平时隐藏，Shift 按下时显示）
- **SortLabel** — 产出图标（[Icon_Food] 等）
- **DescArrow** — 降序箭头
- **AscArrow** — 升序箭头

## 数据刷新机制

- 点击排序按钮 → `m_SortSettingsChanged = true` → 刷新时重新调用 `SortTradeRoutes()`
- Shift 按住时不立即刷新，松开后才刷新（优化性能，避免每次 Shift+Click 都重建整个列表）
- Ctrl 切换的是"总排序"vs"组内排序"两个设置表，刷新时根据 Ctrl 状态显示不同的箭头组合

## 应用场景

- 贸易路线排序
- 伟人列表排序
- 任何需要多列、多优先级排序的数据列表

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `UI/TradeOverview.xml` | 贸易总览面板 — 含排序栏 Stack 及所有排序按钮定义 |

### 排序栏控件 ID 对照

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `FoodSortButton` | GridButton | `Controls.FoodSortButton` | 按食物排序按钮（48x33，PanelButtonLightweight） |
| `FoodSortOrder` | Label | `Controls.FoodSortOrder` | 食物列优先级数字（Hidden，Shift 时显示） |
| `FoodSortLabel` | Label | — | 食物产出图标（[Icon_Food]） |
| `FoodDescArrow` | Image | `Controls.FoodDescArrow` | 食物降序箭头（Controls_ButtonExtendSmall2，20x16） |
| `FoodAscArrow` | Image | `Controls.FoodAscArrow` | 食物升序箭头（TextureOffset="0,60"，20x16） |
| `ProductionSortButton` | GridButton | `Controls.ProductionSortButton` | 按产能排序 |
| `ProductionSortOrder` | Label | — | 产能优先级数字 |
| `ProductionSortLabel` | Label | — | 产能图标（[Icon_Production]） |
| `ProductionDescArrow` | Image | `Controls.ProductionDescArrow` | 产能降序箭头 |
| `ProductionAscArrow` | Image | `Controls.ProductionAscArrow` | 产能升序箭头 |
| `GoldSortButton` | GridButton | `Controls.GoldSortButton` | 按金币排序（同上结构） |
| `GoldSortOrder` / `GoldSortLabel` / `GoldDescArrow` / `GoldAscArrow` | — | — | 同上 |
| `ScienceSortButton` | GridButton | `Controls.ScienceSortButton` | 按科技排序 |
| `ScienceSortOrder` / `ScienceSortLabel` / `ScienceDescArrow` / `ScienceAscArrow` | — | — | 同上 |
| `CultureSortButton` | GridButton | `Controls.CultureSortButton` | 按文化排序 |
| `CultureSortOrder` / `CultureSortLabel` / `CultureDescArrow` / `CultureAscArrow` | — | — | 同上 |

### 排序栏 XML 布局

```xml
<Stack Size="50,50" Anchor="L,B" StackGrowth="Right" Offset="82,-9" StackPadding="2">
  <GridButton ID="FoodSortButton" Size="48,parent-17"
              Style="PanelButtonLightweight">
    <Label ID="FoodSortOrder" Hidden="1" Anchor="C,C"
           String="9" Style="FontNormal12"/>
    <Label ID="FoodSortLabel" Anchor="C,C" Offset="15,1"
           Style="FontNormal12" String="[Icon_Food]"/>
    <Image ID="FoodDescArrow" Texture="Controls_ButtonExtendSmall2"
           Size="20,16" Anchor="C,C" Offset="-12,0"/>
    <Image ID="FoodAscArrow" Texture="Controls_ButtonExtendSmall2"
           TextureOffset="0,60" Size="20,16" Anchor="C,C" Offset="-12,-4"/>
  </GridButton>
  <!-- Production / Gold / Science / Culture / Faith / TurnsToComplete 同理 -->
</Stack>
```

### 按钮状态与 Lua 交互

| 状态 | FoodsSortButton 颜色 | DescArrow | AscArrow | SortOrder |
|------|--------------------|-----------|----------|-----------|
| 未参与排序 | `ButtonDisabledCS` | Hidden | Hidden | Hidden |
| 降序优先级 1 | `ButtonCS`（亮） | Visible | Hidden | "1" |
| 升序优先级 1 | `ButtonCS`（亮） | Hidden | Visible | "1" |
| 降序优先级 2 | `ButtonCS`（亮） | Visible | Hidden | "2" |

### 容器上下文

排序栏在 `TradeOverview.xml` 中位于 `HeaderFrame` 下方，`GroupByPulldown` 和 `FilterPulldown` 右侧。完整的外层结构：

```xml
<Context>
  <Container ID="TabHeader" ...>
    <GridButton ID="MyRoutesButton" Style="TabButton" />
    <GridButton ID="RoutesToCitiesButton" Style="TabButton" />
    <GridButton ID="AvailableRoutesButton" Style="TabButton" />
  </Container>
  <Grid ID="HeaderFrame" ...>
    <!-- 标题和筛选 PullDown -->
  </Grid>
  <!-- 排序栏 Stack 在此 -->
  <Stack StackGrowth="Right" Anchor="L,B">
    <PullDown ID="OverviewGroupByPulldown" .../>
    <PullDown ID="OverviewDestinationFilterPulldown" .../>
    <!-- 排序栏紧随其后 -->
  </Stack>
</Context>
```
