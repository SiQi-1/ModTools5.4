# lua-workshop-era-tracker — 独立报表界面 + 筛选排序 + 持久化存储

从 Real Era Tracker (Infxo) 提炼的独立 UI 报表模式：基于 InstanceManager 的列表界面、多 Tab 切换、复选框筛选、自定义排序、数据持久化、搜索功能。

---

## 快速索引

| 模式 | 核心 API / 技术 | 适用场景 |
|------|----------------|---------|
| 独立报表界面 | `UIManager:QueuePopup/DequeuePopup` | 全新独立窗口 |
| Tab 标签系统 | `CreateTabs / AddTab / SelectTab` | 多页切换 |
| 行 InstanceManager | `BuildInstanceForControl + GetInstance` | 列表项动态创建 |
| 自定义迭代器排序 | `spairs(t, order_function)` | 非标准排序 |
| 复选框筛选 | `CheckBox:IsSelected()` | 多条件过滤 |
| 搜索 | `EditBox + nocase() + string.find` | 文本搜索 |
| 数据持久化 | `serialize/deserialize` → `SetValue/GetValue` | 跨存档保存 |
| GameInfo 遍历 | `GameInfo.Moments()` + DB.Query | 枚举所有可能项 |
| ReportsList 集成 | `LuaEvents.ReportsList_OpenXxx.Add` | 从原版报表列表入口 |
| Historic Moment 处理 | `Game.GetHistoryManager()` | 读取历史时刻 |

---

## 一、整体架构

### 1.1 生命周期

```
Initialize()           → 注册 UI 回调、事件监听
  ↓
OnInit(isReload)       → LateInitialize() 建 Tab、注册事件
  ↓
Open(tabToOpen)        → 更新数据、选择 Tab、显示统计
  ↓
ViewMomentsPage(group) → 筛选→排序→ShowMoment 填充每行
  ↓
Close()                → DequeuePopup
```

### 1.2 独立报表框架模板

```lua
-- ===========================================================================
-- MyReport.lua — 独立报表界面模板
-- ===========================================================================
include("InstanceManager");
include("TabSupport");

-- 单入口显示
function Open()
    UIManager:QueuePopup(ContextPtr, PopupPriority.Medium);
    Controls.ScreenAnimIn:SetToBeginning();
    Controls.ScreenAnimIn:Play();
    UI.PlaySound("UI_Screen_Open");
    -- 刷新数据 & 显示页面
    RefreshData();
    ShowPage();
end

-- 单出口关闭
function Close()
    if not ContextPtr:IsHidden() then
        UI.PlaySound("UI_Screen_Close");
    end
    UIManager:DequeuePopup(ContextPtr);
end

-- ESC 关闭
function OnInputHandler(pInputStruct)
    local uiMsg = pInputStruct:GetMessageType();
    if uiMsg == KeyEvents.KeyUp and pInputStruct:GetKey() == Keys.VK_ESCAPE then
        if not ContextPtr:IsHidden() then Close(); return true; end
    end
    return false;
end

-- 窗口尺寸自适应
function Resize()
    local x, y = UIManager:GetScreenSizeVal();
    Controls.Main:SetSizeY(y - 30);
    Controls.Main:SetOffsetY(15);
end

function Initialize()
    ContextPtr:SetInitHandler(OnInit);
    ContextPtr:SetInputHandler(OnInputHandler, true);
    Controls.CloseButton:RegisterCallback(Mouse.eLClick, OnClose);
    Controls.CloseButton:RegisterCallback(Mouse.eMouseEnter, function()
        UI.PlaySound("Main_Menu_Mouse_Over");
    end);
end
Initialize();
```

---

## 二、Tab 标签系统

### 2.1 创建 Tab

使用 `TabSupport.lua` 提供的 `CreateTabs` / `AddTab`。

```lua
local m_tabs = nil;

function LateInitialize()
    -- CreateTabs(容器, 宽度, 高度, 颜色hex)
    m_tabs = CreateTabs(Controls.TabContainer, 42, 34, 0xFF331D05);

    AddTabSection("LOC_MY_TAB_1", function() ShowPage(1); end);
    AddTabSection("LOC_MY_TAB_2", function() ShowPage(2); end);
    AddTabSection("LOC_MY_TAB_3", function() ShowPage(3); end);

    m_tabs.SameSizedTabs(20);     -- 等宽 + 内边距
    m_tabs.CenterAlignTabs(-10);  -- 居中 + 偏移
end

-- AddTabSection 辅助函数（使用 InstanceManager 创建每个 Tab 按钮）
local m_tabIM = InstanceManager:new("TabInstance", "Button", Controls.TabContainer);

function AddTabSection(name, populateCallback)
    local kTab = m_tabIM:GetInstance();
    kTab.Button[DATA_FIELD_SELECTION] = kTab.Selection;
    local callback = function()
        if m_tabs.prevSelectedControl then
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

-- 动画装饰（滑动箭头）
function OnInit(isReload)
    LateInitialize();
    if isReload then
        if not ContextPtr:IsHidden() then Open(); end
    end
    m_tabs.AddAnimDeco(Controls.TabAnim, Controls.TabArrow);
end
```

---

## 三、InstanceManager 列表行模式

### 3.1 XML 定义

```xml
<!-- 简单容器（每页一个） -->
<Instance Name="SimpleInstance">
    <Stack ID="Top" StackGrowth="Down" />
</Instance>

<!-- 表头行（每页第一行） -->
<Instance Name="HeaderInstance">
    <Container ID="Top" Size="990,22">
        <Stack StackGrowth="Right">
            <Container Size="70,parent">
                <Label Style="ReportHeaderSmallText" String="LOC_COLUMN_1" />
            </Container>
            <Container Size="55,parent">
                <Label Style="ReportHeaderSmallText" String="LOC_COLUMN_2" />
            </Container>
            <!-- ...更多列 -->
        </Stack>
    </Container>
</Instance>

<!-- 数据行（每条数据一个） -->
<Instance Name="EntryInstance">
    <Container ID="Top" Size="990,28">
        <Stack StackGrowth="Right">
            <Container Size="70,parent">
                <GridButton ID="Favored" Style="CheckBoxControl" />
                <Label ID="Group" Style="ReportValueText" />
            </Container>
            <Container Size="55,parent">
                <Label ID="Score" Style="ReportValueText" />
            </Container>
            <Container Size="310,parent">
                <Label ID="Description" Style="ReportValueLeftName" />
            </Container>
            <Container Size="50,parent">
                <Label ID="Status" Style="ReportValueText" />
            </Container>
            <!-- ...更多列 -->
        </Stack>
    </Container>
</Instance>
```

### 3.2 Lua 填充

```lua
local m_simpleIM = InstanceManager:new("SimpleInstance", "Top", Controls.Stack);

function ShowPage()
    -- 1. 重置所有实例
    m_simpleIM:ResetInstances();
    Controls.Scroll:SetScrollValue(0);

    -- 2. 获取容器实例
    local instance = m_simpleIM:GetInstance();
    instance.Top:DestroyAllChildren();

    -- 3. 构建表头
    local headerInstance = {};
    ContextPtr:BuildInstanceForControl("HeaderInstance", headerInstance, instance.Top);

    -- 4. 遍历数据，为每条数据创建行
    local filteredData = FilterData();
    for _, item in ipairs(filteredData) do
        local rowInstance = {};
        ContextPtr:BuildInstanceForControl("EntryInstance", rowInstance, instance.Top);
        FillRow(item, rowInstance);
    end

    -- 5. 重新计算堆叠和滚动尺寸
    Controls.Stack:CalculateSize();
    Controls.Scroll:CalculateSize();
    Controls.Scroll:SetSizeY(
        Controls.Main:GetSizeY() - (Controls.BottomFilters:GetSizeY() + 85)
    );
end
```

---

## 四、复选框筛选 + 排序

### 4.1 筛选逻辑

```lua
function ViewMomentsPage(eGroup)
    -- 读取所有复选框状态
    local bEraScore1 = Controls.EraScore1Checkbox:IsSelected();
    local bEraScore2 = Controls.EraScore2Checkbox:IsSelected();
    local bHideNotActive = Controls.HideNotActiveCheckbox:IsSelected();
    local bShowOnlyEarned = Controls.ShowOnlyEarnedCheckbox:IsSelected();
    local bHideNotAvailable = Controls.HideNotAvailableCheckbox:IsSelected();

    local tShow = {};
    local iCurrentEra = Game.GetEras():GetCurrentEra();

    for key, moment in pairs(m_kMoments) do
        local bShow = true;

        -- 硬排除
        if moment.EraScore == nil or moment.EraScore == 0 then bShow = false; end

        -- 文明/领袖限定（仅显示当前玩家的 unique 时刻）
        if moment.ValidFor ~= nil and moment.ValidFor ~= "" then
            if not (moment.ValidFor == sCivilization or moment.ValidFor == sLeader) then
                bShow = false;
            end
        end

        -- 分组过滤
        if eGroup == 4 then                -- 收藏页
            if not moment.Favored then bShow = false; end
        else
            if moment.Category ~= eGroup then bShow = false; end
        end

        -- 复选框过滤（favored 项始终显示，跳过所有复选框）
        if not moment.Favored then
            if moment.EraScore == 1 and not bEraScore1 then bShow = false; end
            if moment.EraScore == 2 and not bEraScore2 then bShow = false; end
            if bHideNotActive  and moment.Status ~= 0 then bShow = false; end
            if bShowOnlyEarned and moment.Status ~= 1 then bShow = false; end

            -- 时代可用性过滤
            if bHideNotAvailable then
                local iMinEra = moment.MinEra and GameInfo.Eras[moment.MinEra].Index or 0;
                local iMaxEra = moment.MaxEra and GameInfo.Eras[moment.MaxEra].Index or m_iMaxEraIndex;
                if iCurrentEra < iMinEra or iCurrentEra > iMaxEra then bShow = false; end
            end
        end

        -- 搜索过滤
        if _SearchQuery and string.find(moment.Description, _SearchQuery) == nil then
            bShow = false;
        end

        if bShow then table.insert(tShow, moment); end
    end

    -- 排序后显示
    for _, moment in spairs(tShow, MomentsSortFunction) do
        -- 创建行...
    end
end
```

### 4.2 互斥复选框

```lua
-- 两个复选框不能同时选中
function OnToggleHideNotActiveCheckbox()
    local isChecked = Controls.HideNotActiveCheckbox:IsSelected();
    Controls.HideNotActiveCheckbox:SetSelected(not isChecked);
    if not isChecked then Controls.ShowOnlyEarnedCheckbox:SetSelected(isChecked); end
    ViewMomentsPage();
end

function OnToggleShowOnlyEarnedCheckbox()
    local isChecked = Controls.ShowOnlyEarnedCheckbox:IsSelected();
    Controls.ShowOnlyEarnedCheckbox:SetSelected(not isChecked);
    if not isChecked then Controls.HideNotActiveCheckbox:SetSelected(isChecked); end
    ViewMomentsPage();
end
```

### 4.3 自定义迭代器排序

```lua
-- spairs: 对 table 排序后迭代（Civ6 中 table 遍历是无序的）
function spairs(t, order_function)
    local keys = {};
    for key, _ in pairs(t) do table.insert(keys, key); end
    if order_function then
        table.sort(keys, function(a, b) return order_function(t, a, b) end);
    else
        table.sort(keys);
    end
    local i = 0;
    return function()
        i = i + 1;
        if keys[i] then return keys[i], t[keys[i]]; end
    end
end

-- 排序函数：favored 置顶 → 按 EraScore 降序 → 按 Description 升序 → 按 Object 升序
function MomentsSortFunction(t, a, b)
    if t[a].Favored ~= t[b].Favored then
        return t[a].Favored;  -- true > false, favored 排前面
    end
    if t[a].EraScore == t[b].EraScore then
        if t[a].Description == t[b].Description then
            return t[a].Object < t[b].Object;
        end
        return t[a].Description < t[b].Description;
    end
    return t[a].EraScore > t[b].EraScore;  -- 高分在前
end
```

---

## 五、搜索功能

### 5.1 不区分大小写搜索

```lua
-- 将每个字母替换为大小写匹配模式（"abc" → "[aA][bB][cC]"）
function nocase(s)
    return string.gsub(s, "%a",
        function(c)
            return string.format("[%s%s]", string.lower(c), string.upper(c));
        end);
end

-- 过滤时使用 string.find
if _SearchQuery and string.find(moment.Description, _SearchQuery) == nil then
    bShow = false;
end
```

### 5.2 EditBox 回调链

```lua
-- 获得焦点：清空搜索（恢复到无过滤状态）
function OnSearchBarGainFocus()
    Controls.SearchEditBox:ClearString();
    if _SearchQuery then
        _SearchQuery = nil;
        ViewMomentsPage();
    end
end

-- 失去焦点：恢复提示文字，取消搜索
function OnSearchBarLostFocus()
    if Controls.SearchEditBox:GetText() == nil then
        Controls.SearchEditBox:SetText(LOC_TREE_SEARCH_W_DOTS);
        if _SearchQuery then
            _SearchQuery = nil;
            ViewMomentsPage();
        end
    end
end

-- 输入变化：仅当实际搜索词变化时才刷新页面
function OnSearchCharCallback()
    local str = Controls.SearchEditBox:GetText();
    if str ~= nil and #str > 0 and str ~= LOC_TREE_SEARCH_W_DOTS then
        local newSearch = nocase(str);
        if newSearch ~= _SearchQuery then
            _SearchQuery = newSearch;
            ViewMomentsPage();
        end
    end
end

-- 注册
Controls.SearchEditBox:RegisterStringChangedCallback(OnSearchCharCallback);
Controls.SearchEditBox:RegisterHasFocusCallback(OnSearchBarGainFocus);
Controls.SearchEditBox:RegisterLostFocusCallback(OnSearchBarLostFocus);
```

---

## 六、数据持久化

### 6.1 serialize/deserialize（Metalua 实现）

```lua
-- 序列化 Lua table 为可存储字符串
function serialize(x)
    -- 处理多重引用、嵌套点...
    -- 返回如 "return { ... }" 的字符串
end

function deserialize(x)
    return loadstring(x)();
end
```

### 6.2 保存 & 加载

```lua
-- 保存到玩家槽位（跟存档走）
function SaveDataToPlayerSlot(ePlayerID, sSlotName, data)
    local sData = serialize(data);
    PlayerConfigurations[ePlayerID]:SetValue(sSlotName, sData);
end

-- 从玩家槽位加载
function LoadDataFromPlayerSlot(ePlayerID, sSlotName)
    local sData = PlayerConfigurations[ePlayerID]:GetValue(sSlotName);
    if sData == nil then return nil; end
    return loadstring(sData)();  -- 执行序列化字符串获得 table
end

-- 保存到 GameConfiguration（跨存档全局）
function SaveDataToGameSlot(sSlotName, data)
    local sData = serialize(data);
    GameConfiguration.SetValue(sSlotName, sData);
end
```

### 6.3 加载时机

```lua
-- Events.LoadComplete 只在加载存档时触发（开始游戏时不触发）
function OnLoadComplete()
    local data = LoadDataFromPlayerSlot(Game.GetLocalPlayer(), "MyFavoredItems");
    if data then
        for _, key in ipairs(data) do
            if m_kItems[key] then m_kItems[key].Favored = true; end
        end
    end
end

-- 注册
Events.LoadComplete.Add(OnLoadComplete);

-- 保存时机：每次显示页面时
function ViewPage()
    -- ... 构建显示 ...
    local tSaveData = {};
    for key, item in pairs(m_kItems) do
        if item.Favored then table.insert(tSaveData, key); end
    end
    SaveDataToPlayerSlot(localPlayerID, "MyFavoredItems", tSaveData);
end
```

### 6.4 注意事项

- **`PlayerConfigurations:SetValue/GetValue`** 随存档保存
- **`GameConfiguration.SetValue/GetValue`** 是跨存档全局的（慎用）
- **`serialize`** 生成的字符串可通过 `loadstring(sData)()` 还原
- 不要在热座模式下依赖持久化数据（`OnLocalPlayerTurnEnd` 中关闭界面）

---

## 七、GameInfo 遍历生成数据

### 7.1 遍历 GameInfo 表

```lua
function InitializeData()
    for moment in GameInfo.Moments() do
        if moment.Special == "ERA" then
            -- 为每个时代生成独立条目（排除 Ancient）
            for era in GameInfo.Eras() do
                if era.EraType ~= "ERA_ANCIENT" then
                    RegisterOneMoment(era.EraType .. "_" .. moment.MomentType, moment, ...);
                end
            end
        elseif moment.Special == "STRATEGIC" then
            -- 为每种战略资源生成条目
            for _, row in ipairs(DB.Query(
                "SELECT DISTINCT StrategicResource FROM Units WHERE StrategicResource IS NOT NULL"
            )) do
                RegisterOneMoment(row.StrategicResource .. "_" .. moment.MomentType, moment, ...);
            end
        elseif moment.Special == "UNIQUE" then
            -- 遍历所有文明的 Unique（Building/District/Improvement/Unit）
            RegisterMomentsForUniques("Buildings", "BuildingType");
        else
            -- 标准时刻，直接注册
            RegisterOneMoment(moment.MomentType, moment, ...);
        end
    end
end
```

### 7.2 Trait → Leader/Civ 反向查找

```lua
local function GetValidFor(sTrait)
    -- 查 CivilizationTraits
    for row in GameInfo.CivilizationTraits() do
        if row.TraitType == sTrait then
            local civ = GameInfo.Civilizations[row.CivilizationType];
            if civ and civ.StartingCivilizationLevelType == "CIVILIZATION_LEVEL_FULL_CIV" then
                return civ.CivilizationType;
            end
        end
    end
    -- 查 LeaderTraits
    for row in GameInfo.LeaderTraits() do
        if row.TraitType == sTrait then
            local leader = GameInfo.Leaders[row.LeaderType];
            if leader and leader.InheritFrom == "LEADER_DEFAULT" then
                return leader.LeaderType;
            end
        end
    end
    return "";
end
```

---

## 八、ReportsList 集成

在游戏自带的"报表"按钮列表中添加自定义入口。

```lua
-- MyReportList.lua（独立文件）
include("ReportsList");  -- 或 ReportsList_BRS / ReportsListLoader

function OnRaiseMyReport()
    Close();                    -- 关闭当前报表界面
    LuaEvents.MyReport_Open();  -- 触发自定义事件
end

function LateInitialize()
    -- 在这里调用 ReportsList 框架的 LateInitialize
    BRS_LateInitialize();
    -- 添加自定义报表按钮
    AddReport("LOC_MY_BUTTON_LABEL", OnRaiseMyReport, Controls.GlobalReportsStack);
end

-- 主界面文件中接收
function Initialize()
    LuaEvents.MyReport_Open.Add(function() Open(); end);
end
```

AddReport 参数：
- `buttonLabel` — LOC 文本
- `callback` — 点击回调
- `stackControl` — 按钮挂载的 Stack 容器（GlobalReportsStack / TeamReportsStack）

---

## 九、关键事件速查

| 事件 | 说明 |
|------|------|
| `Events.LoadComplete` | 仅加载存档时触发 |
| `Events.LocalPlayerTurnEnd` | 本地玩家回合结束（热座模式用） |
| `LuaEvents.ReportsList_OpenXxx` | 自定义事件，从 ReportsList 打开 |
| `LuaEvents.ReportScreen_Closed` | 自定义事件，报表关闭通知 |

---

## 十、完整文件结构

```
MyReport.lua              — 主界面逻辑（Initialize / Open / Close / ShowPage）
MyReport.xml              — UI 结构（Instance 定义、Tab 容器、ScrollPanel）
MyReportList.lua          — ReportsList 集成入口（AddReport）
Serialize.lua             — 序列化库（如需要持久化）
Text/MyReport_Text.xml    — 本地化文本
```

---

## 十一、注意事项

1. **`BuildInstanceForControl` 的 Instance Name 必须与 XML 中 `<Instance Name="...">` 完全匹配**
2. **每次 ShowPage 必须 `ResetInstances()`** 否则会重复创建行
3. **`CalculateSize()` 调用顺序**：先 Stack 后 Scroll
4. **`Events.LoadComplete` 与 `Events.LoadGameViewStateDone` 不同**：前者只在加载存档时触发，后者所有游戏启动都触发
5. **GameInfo 遍历时用 `for row in GameInfo.TableName() do`** 而非 `ipairs`
6. **DLC 检测**：`Modding.IsModActive("DLC_UUID")` 判断扩展包是否存在

---

## XML 配合

### XML 文件

| 文件 | 路径 |
|------|------|
| 报表布局 | `RealEraTracker.xml` |

### 核心控件 ID 对照表

| 控件 ID | 控件类型 | 用途 |
|---------|---------|------|
| `Main` | Box | 主窗口，`Size="1015,711"` |
| `CloseButton` | Button | 关闭按钮 |
| `EraNameLabel` | Label | 当前时代名称 |
| `TurnsLabel` | Label | 当前回合信息 |
| `TotalsLabel` | Label | 时代总分 |
| `ThresholdsLabel` | Label | 时代阈值信息 |
| `TajMahalImage` | Image | 泰姬陵图标（条件显示） |
| `TabContainer` | Container | 标签按钮容器 |
| `TabAnim` / `TabArrow` | SlideAnim / Image | Tab 切换动画箭头 |
| `Scroll` | ScrollPanel | 主内容滚动区 |
| `Stack` | Stack | 主内容堆叠 |
| `BottomFilters` | Container | 底部筛选栏 |
| `EraScore1Checkbox` / `EraScore2Checkbox` / `EraScore3Checkbox` / `EraScore4Checkbox` | GridButton | 时代分数筛选项（1/2/3/4+） |
| `SearchEditBox` | EditBox | 搜索输入框 |
| `HideNotActiveCheckbox` | GridButton | "隐藏未激活"筛选 |
| `ShowOnlyEarnedCheckbox` | GridButton | "仅显示已完成"筛选 |
| `HideNotAvailableCheckbox` | GridButton | "隐藏不可用"筛选 |

### Instance 对照表

| Instance Name | 用途 | 关键子控件 |
|--------------|------|----------|
| `TabInstance` | 标签按钮 | `Button` + `Selection`（AlphaAnim） |
| `SimpleInstance` | 不可折叠简单行容器 | `Top` Stack |
| `CityStatus2HeaderInstance` | 表头行（10列） | `GroupButton`, `EraScoreButton`, `DescriptionButton`, `ObjectButton`, `StatusButton`, `TurnButton`, `CountButton`, `ErasButton`, `PlayerButton`, `ExtraButton` |
| `MomentEntryInstance` | 时刻数据行 | `Favored`（CheckBox）, `Group`, `EraScore`, `Description`, `Object`, `Status`, `Turn`, `Count`, `Eras`, `Player`, `Extra` |

### 可复用模板：多重复选框筛选栏

```xml
<Container ID="BottomFilters" Anchor="C,B" Offset="0,0" Size="parent-6,80">
  <Grid Anchor="C,T" Offset="0,0" Size="parent,8" Style="Divider3Grid"/>
  <Image Anchor="C,B" Offset="0,2" Size="parent,parent" Texture="Controls_Gradient" Color="255,255,255,32">
    <GridButton ID="EraScore1Checkbox" Style="CheckBoxControl" Anchor="L,T" Offset="40,10" Size="140,26" String="..."/>
    <GridButton ID="EraScore2Checkbox" Style="CheckBoxControl" Anchor="L,T" Offset="200,10" Size="140,26" String="..."/>
    <Grid ID="Civilopedia_SearchPanel" Anchor="L,T" Offset="680,10" Size="240,27">
      <EditBox ID="SearchEditBox" Anchor="L,C" Offset="24,0" Size="parent-20,14" Style="FontNormal14" CallOnChar="1" MaxLength="20" String="LOC_TREE_SEARCH_W_DOTS"/>
    </Grid>
    <GridButton ID="HideNotActiveCheckbox" Style="CheckBoxControl" Anchor="L,B" Offset="40,10" Size="220,26" String="..."/>
    <GridButton ID="ShowOnlyEarnedCheckbox" Style="CheckBoxControl" Anchor="L,B" Offset="280,10" Size="220,26" String="..."/>
    <GridButton ID="HideNotAvailableCheckbox" Style="CheckBoxControl" Anchor="L,B" Offset="520,10" Size="400,26" String="..."/>
  </Image>
</Container>
```
