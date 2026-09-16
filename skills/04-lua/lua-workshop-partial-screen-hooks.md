# PartialScreenHooks 替换官方面板（来源：工坊 873246701）

## 做什么
利用游戏内置的 `PartialScreenHooks` LuaEvents 系统，挂钩官方面板的 Open/Close/CloseAll 事件，使自定义面板能像官方 partial screen 一样被游戏管理（确保同一时间只有一个 partial screen 打开）。

## 如何挂载到官方UI

### 入口：LuaEvents 钩子注册

在 `Initialize()` 中注册三个核心事件：

```lua
LuaEvents.PartialScreenHooks_OpenTradeOverview.Add( OnOpen );
LuaEvents.PartialScreenHooks_CloseTradeOverview.Add( OnClose );
LuaEvents.PartialScreenHooks_CloseAllExcept.Add( OnCloseAllExcept );
```

命名规范：
- `PartialScreenHooks_Open<PanelName>` — 其他 UI 调用此事件来打开你的面板
- `PartialScreenHooks_Close<PanelName>` — 其他 UI 调用此事件来关闭你的面板
- `PartialScreenHooks_CloseAllExcept` — 全局关闭事件，收到后必须关闭（除非传入的 context ID 是自己的）

### CloseAllExcept 实现

```lua
function OnCloseAllExcept( contextToStayOpen:string )
    if contextToStayOpen == ContextPtr:GetID() then return; end
    Close();
end
```

### ContextPtr:SetHide 控制显示

用 `ContextPtr:SetHide(false)` 而非 `ContextPtr:SetHide(true)` 来显示：
```lua
function OnOpen()
    m_AnimSupport.Show();  -- 或者 ContextPtr:SetHide(false)
    Refresh();
end

function OnClose()
    if not ContextPtr:IsHidden() then
        m_AnimSupport.Hide();  -- 或者 ContextPtr:SetHide(true)
    end
end
```

## 关键 Lua 代码

### 基础框架

```lua
include("AnimSidePanelSupport");

local m_AnimSupport:table;

function Open()
    m_AnimSupport.Show();
    Refresh();
end

function Close()
    m_AnimSupport.Hide();
end

function Refresh()
    -- 重建所有 UI 内容
end

function Initialize()
    -- 侧面板动画
    m_AnimSupport = CreateScreenAnimation(Controls.SlideAnim);
    Events.SystemUpdateUI.Add(m_AnimSupport.OnUpdateUI);

    -- PartialScreenHooks 注册
    LuaEvents.PartialScreenHooks_OpenMyPanel.Add( OnOpen );
    LuaEvents.PartialScreenHooks_CloseMyPanel.Add( OnClose );
    LuaEvents.PartialScreenHooks_CloseAllExcept.Add( OnCloseAllExcept );

    -- 输入处理
    ContextPtr:SetInputHandler( OnInputHandler, true );

    -- 游戏事件
    Events.InterfaceModeChanged.Add( OnInterfaceModeChanged );
    Events.LocalPlayerTurnEnd.Add( OnLocalPlayerTurnEnd );
end
Initialize();
```

### 动画支持 (AnimSidePanelSupport)

```lua
-- 在 XML 中定义 SlideAnim 控件
-- <SlideAnim Style="RundownAnimBG" Speed="5">
--   所有 UI 内容放在 SlideAnim 内
-- </SlideAnim>

-- Lua 中创建动画控制器
m_AnimSupport = CreateScreenAnimation(Controls.SlideAnim);
Events.SystemUpdateUI.Add(m_AnimSupport.OnUpdateUI);
```

### 键盘输入处理

```lua
function KeyUpHandler( key:number )
    if key == Keys.VK_ESCAPE then
        Close();
        return true;  -- 吃掉事件
    end
    if key == Keys.VK_RETURN then
        return true;  -- 防止 Enter 穿透到下层 UI
    end
    return false;  -- 不处理，让事件继续传播
end

function OnInputHandler( pInputStruct:table )
    local uiMsg = pInputStruct:GetMessageType();
    if uiMsg == KeyEvents.KeyUp then
        return KeyUpHandler( pInputStruct:GetKey() );
    end
    return false;
end
```

## XML 控件定义

### 侧面板容器结构

```xml
<Context>
  <SlideAnim Style="RundownAnimBG" Speed="5">
    <!-- Title Bar -->
    <Grid Anchor="C,T" Size="parent-6,140" Offset="0,50"
          Texture="Controls_TitleBarDark" SliceCorner="21,17" SliceTextureSize="42,34">
      <Button ID="CloseButton" Anchor="R,T" Offset="5,40" Style="CloseButtonSmall" />
      <!-- Tab 按钮、Header、过滤下拉等 -->
    </Grid>

    <!-- Body: ScrollPanel + Stack -->
    <Container Anchor="C,B" Size="parent, parent-195" Offset="0,5">
      <ScrollPanel ID="BodyScrollPanel" Size="495,parent" Vertical="1">
        <ScrollBar Anchor="R,C" AnchorSide="O,I" Style="ScrollVerticalBar"/>
        <Stack ID="BodyStack" StackGrowth="Down" StackPadding="4"/>
      </ScrollPanel>
    </Container>
  </SlideAnim>

  <!-- Instance 模板 -->
  <Instance Name="RouteInstance">
    <Container ID="Top" Size="485,78" Offset="10,0">
      <GridButton ID="GridButton" Size="parent,parent">
        <!-- 每条路由的 UI 元素 -->
      </GridButton>
    </Container>
  </Instance>

  <Instance Name="HeaderInstance">
    <Container ID="Top" Size="485,42" Offset="10,0">
      <!-- 分组标题 UI -->
    </Container>
  </Instance>
</Context>
```

### ScrollPanel + Stack 组合

```xml
<ScrollPanel ID="BodyScrollPanel" Size="495,parent" Vertical="1">
  <ScrollBar Anchor="R,C" AnchorSide="O,I" Offset="0,0" Style="ScrollVerticalBar"/>
  <Stack ID="BodyStack" StackGrowth="Down" StackPadding="4"/>
</ScrollPanel>
```

Stack 放在 ScrollPanel 内（而非 ScrollPanel 子级），StackGrowth="Down" 表示垂直排列。

### 刷新后重新计算尺寸

```lua
function PostRefresh()
    Controls.BodyScrollPanel:CalculateSize();
    Controls.BodyScrollPanel:ReprocessAnchoring();
    Controls.BodyScrollPanel:CalculateInternalSize();
end
```

## 数据刷新机制

### 触发刷新的时机

| 事件 | 触发条件 |
|------|---------|
| 面板打开 | `Open()` 中调用 `Refresh()` |
| 游戏事件 | `Events.UnitOperationStarted`、`Events.GovernmentPolicyChanged` 等 |
| 用户操作 | 排序按钮点击、过滤下拉选择、分组下拉选择 |
| 回合变化 | `Events.LocalPlayerTurnEnd`（清理缓存） |

### 刷新流程

```
Refresh()
  ├── PreRefresh()              -- Reset 所有 InstanceManager
  │   ├── m_RouteInstanceIM:ResetInstances()
  │   ├── m_HeaderInstanceIM:ResetInstances()
  │   └── m_DividerInstanceIM:ResetInstances()
  ├── 重建数据表（如果需要）     -- RebuildAvailableTradeRoutesTable()
  ├── 过滤数据                   -- FilterTradeRoutes()
  ├── 分组数据                   -- GroupRoutes()
  ├── 排序数据                   -- SortTradeRoutes()
  ├── 生成 UI Instance           -- AddRouteInstanceFromRouteInfo() × N
  └── PostRefresh()              -- CalculateSize / ReprocessAnchoring
```

### 延迟重建（按需缓存）

只在回合变化时才重建路由数据表：
```lua
if (not m_HasBuiltTradeRouteTable) or Game.GetCurrentGameTurn() > m_LastTurnBuiltTradeRouteTable then
    RebuildAvailableTradeRoutesTable();
end
```

## 应用场景

- 替换游戏原有的 Trade Overview 面板
- 创建新的侧面板（如自定义报表、统计面板）
- 任何需要"同一时间只显示一个"的覆盖式面板

## XML 配合

### 涉及的关键 XML 文件

| 文件 | 路径（相对于 Mod 根目录） | 用途 |
|------|--------------------------|------|
| `TradeOverview.xml` | `UI/TradeOverview.xml` | 侧面板 Context（SlideAnim + Tab + ScrollPanel + Instances） |

### 核心控件 ID 对照表

| 控件 ID | 类型 | 用途 |
|---------|------|------|
| **动画/框架** | | |
| `SlideAnim` | SlideAnim | 侧面板入场/离场动画容器（Style="RundownAnimBG", Speed="5"） |
| `CloseButton` | Button | 关闭按钮（Style="CloseButtonSmall"） |
| **Tab 导航** | | |
| `TabHeader` | Container | Tab 按钮容器 |
| `MyRoutesButton` / `RoutesToCitiesButton` / `AvailableRoutesButton` | GridButton | Tab 切换按钮 |
| `MyRoutesSelected` 等 | GridButton | Tab 选中状态覆盖 |
| **Header** | | |
| `HeaderFrame` | Grid | 表头框架 |
| `HeaderLabel` | Label | 路由数量标题 |
| `SettingsButton` | Button | 设置按钮 |
| **过滤/排序/分组** | | |
| `OverviewGroupByPulldown` | PullDown | 分组下拉 |
| `OverviewFilterPulldown` | PullDown | 过滤下拉 |
| `FoodSortButton` ~ `TurnsToCompleteSortButton` | GridButton | 排序按钮 × 7 |
| `GroupExpandAllCheckBox` / `GroupCollapseAllCheckBox` | CheckBox | 展开/折叠全部 |
| **Body** | | |
| `BodyScrollPanel` | ScrollPanel | 主内容滚动区 |
| `BodyStack` | Stack | 动态路由条目列表（StackGrowth="Down"） |
| **Instances** | | |
| `HeaderInstance` | Instance | 分组标题（含展开/折叠、路由统计） |
| `RouteInstance` | Instance | 单条路由行（含产出、文明图标、回合数） |
| `SectionDividerInstance` | Instance | 分组分隔线 |
| `SimpleButtonInstance` | Instance | 简单按钮行 |

### 可复用 XML 模板

```xml
<Context>
    <SlideAnim Style="RundownAnimBG" Speed="5">
        <!-- 标题栏 -->
        <Grid Anchor="C,T" Size="parent-6,140" Offset="0,50" Texture="Controls_TitleBarDark" SliceCorner="21,17" SliceTextureSize="42,34">
            <!-- Tab 容器 -->
            <Container ID="TabHeader" Anchor="C,T" Offset="0,-10" Size="540,61">
                <Stack StackGrowth="Right" Anchor="C,C">
                    <GridButton ID="Tab1Button" Size="150,34" Style="TabButton" String="LOC_TAB_1">
                        <GridButton ID="Tab1Selected" Size="parent,parent" Style="TabButtonSelected" ConsumeMouseButton="0" ConsumeMouseOver="1"/>
                    </GridButton>
                    <GridButton ID="Tab2Button" Size="150,34" Style="TabButton" String="LOC_TAB_2">
                        <GridButton ID="Tab2Selected" Size="parent,parent" Style="TabButtonSelected" ConsumeMouseButton="0" ConsumeMouseOver="1"/>
                    </GridButton>
                </Stack>
            </Container>

            <!-- 排序/过滤控制 -->
            <Stack StackGrowth="Right" Anchor="L,B" Offset="0,-7">
                <CheckBox ID="ExpandAllCheckBox" Anchor="L,T" String="LOC_EXPAND_ALL" Style="CityPanelCBFaith" IsChecked="0"/>
                <!-- 排序按钮 -->
                <GridButton ID="FoodSortButton" ToolTip="LOC_SORT_BY_FOOD" Size="48,22" Style="PanelButtonLightweight">
                    <Label ID="FoodSortLabel" Anchor="C,C" String="[Icon_Food]"/>
                </GridButton>
                <!-- ... 更多排序按钮 ... -->
            </Stack>

            <Button ID="CloseButton" Anchor="R,T" Offset="5,40" Style="CloseButtonSmall"/>
        </Grid>

        <!-- Body -->
        <Container Anchor="C,B" Size="parent, parent-195" Offset="0,5">
            <ScrollPanel ID="BodyScrollPanel" Size="495,parent" Vertical="1">
                <ScrollBar Anchor="R,C" AnchorSide="O,I" Style="ScrollVerticalBar"/>
                <Stack ID="BodyStack" StackGrowth="Down" StackPadding="4"/>
            </ScrollPanel>
        </Container>
    </SlideAnim>

    <!-- Instances -->
    <Instance Name="ItemInstance">
        <Container ID="Top" Size="485,78" Offset="10,0">
            <GridButton ID="GridButton" Size="parent,parent">
                <Label ID="ItemLabel" Anchor="L,T" Offset="33,10" Style="FontFlair16" TruncateWidth="370"/>
                <!-- 数据标签... -->
            </GridButton>
        </Container>
    </Instance>

    <Instance Name="HeaderInstance">
        <Container ID="Top" Size="485,42" Offset="10,0">
            <GridButton ID="HeaderGrid" Anchor="C,B" Size="parent,parent">
                <Label ID="HeaderLabel" Anchor="L,C" Offset="36,1" Style="FontFlair16"/>
                <CheckBox ID="RoutesExpand" Anchor="R,C" ButtonSize="41,26" CheckTexture="Controls_ExpandButton"/>
            </GridButton>
        </Container>
    </Instance>
</Context>
```
