# 跨会话状态持久化（来源：工坊 873246701）

## 做什么
在 Civ 6 UI 中实现三种层级的状态持久化：
1. **热重载持久化** — UI 重载（Lua 热加载）时恢复面板状态
2. **存档持久化** — 游戏存档/读档时恢复跨回合数据
3. **设置广播** — 多个 UI 文件间的设置同步

## 如何挂载到官方UI

不需要挂载——这些是纯 Lua 数据层技术。

## 关键 Lua 代码

### 层级 1：热重载持久化 (GameDebug)

游戏调试系统提供基础的 Lua 表保存/恢复机制，用于 UI 热重载（不存档）：

```lua
local RELOAD_CACHE_ID:string = "MyPanelName";  -- 唯一标识符

-- 关闭时保存状态
function OnShutdown()
    LuaEvents.GameDebug_AddValue(RELOAD_CACHE_ID, "isHidden", ContextPtr:IsHidden());
    LuaEvents.GameDebug_AddValue(RELOAD_CACHE_ID, "currentTab", m_currentTab);
    LuaEvents.GameDebug_AddValue(RELOAD_CACHE_ID, "filterSelected", m_filterSelected);
    LuaEvents.GameDebug_AddValue(RELOAD_CACHE_ID, "groupBySelected", m_groupBySelected);
end

-- 重载时请求恢复
function OnInit(isReload:boolean)
    if isReload then
        LuaEvents.GameDebug_GetValues(RELOAD_CACHE_ID);
    end
end

-- 接收恢复数据
function OnGameDebugReturn(context:string, contextTable:table)
    if context == RELOAD_CACHE_ID then
        if contextTable["isHidden"] ~= nil and not contextTable["isHidden"] then
            Open();  -- 面板之前是打开的，重新打开
        end
        if contextTable["currentTab"] ~= nil then
            m_currentTab = contextTable["currentTab"];
            Refresh();
        end
        if contextTable["filterSelected"] ~= nil then
            m_filterSelected = contextTable["filterSelected"];
        end
        -- ...
    end
end

-- 注册
ContextPtr:SetInitHandler(OnInit);
ContextPtr:SetShutdown(OnShutdown);
LuaEvents.GameDebug_Return.Add(OnGameDebugReturn);
```

**限制**：GameDebug 只在 UI 热重载（游戏运行中重载 Lua）时工作，存档/读档时无效。

### 层级 2：存档持久化 (PlayerConfigurations + DataDumper)

对于需要在存档/读档之间保持的数据（如当前运行中的贸易路线），使用 `PlayerConfigurations:SetValue/GetValue` + `DataDumper` 序列化：

```lua
-- 保存复杂 Lua 表到存档
function SaveRunningRoutesInfo()
    local dataDump = DataDumper(m_LocalPlayerRunningRoutes, "localPlayerRunningRoutes");
    PlayerConfigurations[Game.GetLocalPlayer()]:SetValue("BTS_LocalPlayerRunningRotues", dataDump);
end

-- 从存档恢复
function LoadRunningRoutesInfo()
    local localPlayerID = Game.GetLocalPlayer();
    local dataDump = PlayerConfigurations[localPlayerID]:GetValue("BTS_LocalPlayerRunningRotues");
    if dataDump ~= nil then
        loadstring(dataDump)();                    -- 执行序列化代码，重建表
        m_LocalPlayerRunningRoutes = localPlayerRunningRoutes;  -- 变量名由 DataDumper 传入
        CheckConsistencyWithMyRunningRoutes(m_LocalPlayerRunningRoutes);  -- 修正不一致
    end
end
```

**DataDumper 序列化格式**：将 Lua 表转换为可执行的 Lua 代码字符串，`loadstring` 后执行即可重建原始表。

**何时保存**：
```lua
-- 路线变更时
Events.UnitOperationStarted.Add(function(ownerID, unitID, operationID)
    if operationID == UnitOperationTypes.MAKE_TRADE_ROUTE then
        -- 添加新路线 → SaveRunningRoutesInfo()
    end
end);

-- 路线完成时
Events.UnitOperationsCleared.Add(function(ownerID, unitID, operationID)
    -- 移除已完成路线 → SaveRunningRoutesInfo()
end);
```

### 存档数据一致性检查

读档后可能因为版本更新/mod 卸载导致数据不一致，需要验证：

```lua
function CheckConsistencyWithMyRunningRoutes(routesTable)
    -- 1. 从游戏实时数据构建当前运行中的路线列表
    local routesCurrentlyRunning = {};
    for _, city in localPlayerCities:Members() do
        for _, route in ipairs(city:GetTrade():GetOutgoingRoutes()) do
            table.insert(routesCurrentlyRunning, route);
        end
    end

    -- 2. 添加实时有但存档没有的路线
    for _, route in ipairs(routesCurrentlyRunning) do
        if not FindInTable(routesTable, route) then
            AddRouteWithTurnsRemaining(route, routesTable);
        end
    end

    -- 3. 移除存档有但实时没有的路线
    for i = #routesTable, 1, -1 do
        if not FindInTable(routesCurrentlyRunning, routesTable[i]) then
            table.remove(routesTable, i);
        end
    end
end
```

### 层级 3：设置广播 (LuaEvents + GameConfiguration)

多个 UI 文件之间同步设置变化：

```lua
-- === 设置面板（修改方）===
local function OnCheckboxClicked()
    local selected = not control:IsSelected();
    control:SetSelected(selected);
    GameConfiguration.SetValue("BTS_ShowSortPriorities", selected);
    LuaEvents.BTS_SettingsUpdate();  -- 广播给所有监听文件
end

-- === 其他 UI 文件（响应方）===
local function OnSettingsChange()
    showSortPriorities = GameConfiguration.GetValue("BTS_ShowSortPriorities")
    CacheEmpty()  -- 清除缓存（因为设置变更可能影响计算）
    if m_isOpen then
        Refresh()  -- 重新渲染
    end
end
LuaEvents.BTS_SettingsUpdate.Add(OnSettingsChange)
```

### 设置默认值（从数据库读取）

```lua
local function PopulateCheckBox(control, setting_name)
    local current_value = GameConfiguration.GetValue(setting_name);
    if current_value == nil then
        -- 从自建的 SQL 表获取默认值
        if GameInfo.MyMod_Settings[setting_name] then
            current_value = (GameInfo.MyMod_Settings[setting_name].Value ~= 0)
        else
            current_value = false;
        end
        GameConfiguration.SetValue(setting_name, current_value);
    end
    control:SetSelected(current_value);
end
```

## 三种持久化方式对比

| 方式 | 热重载有效 | 存档有效 | 复杂度 | 适用场景 |
|------|----------|---------|-------|---------|
| GameDebug | 是 | 否 | 低 | UI 状态（面板是否打开、当前 Tab） |
| PlayerConfig + DataDumper | 否 | 是 | 高 | 游戏数据（运行中的路线、单位状态） |
| LuaEvents + GameConfig | 自动 | 是（内置） | 低 | 设置项（布尔/数字开关） |

## DataDumper 注意点

DataDumper 来自 Olivetti-Engineering 的开源实现，约 200 行纯 Lua 代码。使用时将整个 `DataDumper` 函数复制到文件中即可。核心 API：

```lua
-- 序列化
DataDumper(value, varname, fastmode, indent)

-- 使用示例
local dump = DataDumper(m_TradersAutomatedSettings, "traderAutomatedSettings");
-- dump 现在是一个 Lua 代码字符串，执行后会在全局创建 traderAutomatedSettings 变量

-- 恢复
loadstring(dump)();
m_TradersAutomatedSettings = traderAutomatedSettings;
```

## 应用场景

- 贸易路线追踪（路线剩余回合数跨存档保持）
- 单位自动化设置
- Mod 选项面板的状态保持
- 任何需要"热重载不丢失当前状态"的 UI

## XML 配合

### 涉及的关键 XML 文件

| 文件 | 路径（相对于 Mod 根目录） | 用途 |
|------|--------------------------|------|
| `BTS_SettingsPanel.xml` | `Settings/BTS_SettingsPanel.xml` | 持有持久化复选框控件 |
| `TradeOverview.xml` | `UI/TradeOverview.xml` | 持有持久化排序/过滤/分组下拉控件 |

### 核心控件 ID 对照表（按持久化层级）

| 控件 ID | 类型 | 持久化方式 | 持久化内容 |
|---------|------|----------|----------|
| **层级 1：热重载（GameDebug）** | | | |
| `BodyScrollPanel` | ScrollPanel（TradeOverview.xml） | `GameDebug_AddValue` | 当前滚动位置、面板可见性 |
| Tab 按钮状态 | GridButton | `GameDebug_AddValue` | `m_currentTab` — 当前选中的 Tab |
| `OverviewFilterPulldown` | PullDown | `GameDebug_AddValue` | `m_filterSelected` — 当前过滤条件 |
| `OverviewGroupByPulldown` | PullDown | `GameDebug_AddValue` | `m_groupBySelected` — 当前分组条件 |
| **层级 2：存档（PlayerConfig + DataDumper）** | | | |
| 路线数据（无直接 XML 控件） | - | `PlayerConfigurations:SetValue` | 运行中的贸易路线表 |
| **层级 3：设置广播（LuaEvents + GameConfiguration）** | | | |
| `ApproximateTraderPathCheckbox` | GridButton/CheckBox（BTS_SettingsPanel.xml） | `GameConfiguration.SetValue` | `BTS_ApproximateTraderPath` |
| `ShowSortPrioritiesCheckbox` | GridButton/CheckBox | `GameConfiguration.SetValue` | `BTS_ShowSortPriorities` |
| `ShowAllRoutePathsCheckbox` | GridButton/CheckBox | `GameConfiguration.SetValue` | `BTS_ShowAllRoutePaths` |
| `ShowTraderPathOnSelectionCheckbox` | GridButton/CheckBox | `GameConfiguration.SetValue` | `BTS_ShowTraderPathOnSelection` |
| `GroupExpandAllCheckBox` | CheckBox（TradeOverview.xml） | `GameConfiguration.SetValue` | 展开/折叠全部设置 |
| 排序按钮（`FoodSortButton` 等） | GridButton | `GameConfiguration.SetValue` | `BTS_SortOrder` 等排序设置 |

### 可复用 XML 模板（带持久化复选框的面板）

```xml
<Context>
    <Container ID="SettingsPanel" Size="380,512" Anchor="C,C" ConsumeMouse="1">
        <Grid Size="parent,parent" Texture="Controls_ContainerBlue" SliceStart="0,0" SliceCorner="3,3" SliceSize="9,9" SliceTextureSize="16,16">
            <!-- 标题栏 -->
            <Container ID="Header" Size="parent,54" Anchor="C,T" Style="ShellHeaderContainer">
                <Grid Style="ShellHeaderButtonGrid">
                    <Label Style="FontFlair24" FontStyle="glow" ColorSet="ShellHeader" Anchor="C,C" String="LOC_SETTINGS_TITLE"/>
                </Grid>
            </Container>

            <!-- 持久化选项区 -->
            <Container ID="OptionsContainer" Size="parent,parent-54" Offset="0,20" Anchor="C,T">
                <Stack Anchor="C,T" StackGrowth="Down" Padding="5" Offset="0,50">
                    <!-- 每个 CheckBox 绑定一个 GameConfiguration key -->
                    <GridButton ID="Option1Checkbox" Anchor="L,C" Size="300,24" Style="CheckBoxControl" String="LOC_OPTION_1" ToolTip="LOC_OPTION_1_TOOLTIP"/>
                    <GridButton ID="Option2Checkbox" Anchor="L,C" Size="300,24" Style="CheckBoxControl" String="LOC_OPTION_2" ToolTip="LOC_OPTION_2_TOOLTIP"/>
                    <!-- 排序选项 -->
                    <GridButton ID="SortCheckbox1" Anchor="L,C" Size="300,24" Style="CheckBoxControl" String="LOC_SORT_1" ToolTip="LOC_SORT_1_TOOLTIP"/>
                </Stack>
            </Container>

            <!-- 确认按钮 -->
            <Container ID="Footer" Size="parent,60" Anchor="C,B" Offset="0,-5" Style="ShellHeaderContainer">
                <GridButton ID="ConfirmButton" Style="ButtonConfirm" Anchor="C,C" String="LOC_OK" Size="300,41"/>
            </Container>
        </Grid>
    </Container>
</Context>
```

### Lua 持久化配合代码（复选框绑定示例）

```lua
-- 初始化：从 GameConfiguration 恢复
function PopulateCheckBox(control, setting_name)
    local current_value = GameConfiguration.GetValue(setting_name)
    if current_value == nil then
        -- 从数据库获取默认值
        current_value = false  -- 或 GameInfo.YourTable[setting_name].Value ~= 0
        GameConfiguration.SetValue(setting_name, current_value)
    end
    control:SetSelected(current_value)
    control:RegisterCallback(Mouse.eLClick, function()
        local selected = not control:IsSelected()
        control:SetSelected(selected)
        GameConfiguration.SetValue(setting_name, selected)
        LuaEvents.SettingsUpdated()  -- 广播给其他 UI 文件
    end)
end

-- 热重载：保存面板可见性
function OnShutdown()
    LuaEvents.GameDebug_AddValue("MyPanel", "isHidden", ContextPtr:IsHidden())
    LuaEvents.GameDebug_AddValue("MyPanel", "currentTab", m_currentTab)
end

-- 热重载：恢复
function OnGameDebugReturn(context, contextTable)
    if context == "MyPanel" then
        if contextTable["isHidden"] ~= nil and not contextTable["isHidden"] then
            Open()
        end
        if contextTable["currentTab"] ~= nil then
            m_currentTab = contextTable["currentTab"]
            Refresh()
        end
    end
end
```
