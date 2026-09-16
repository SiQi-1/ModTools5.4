# 动态 Tab 创建与自适应尺寸模式（来源：Better Religion Screen）

## 做什么
在运行时根据游戏数据创建可变数量的 Tab，当 Tab 过多导致总宽度超出容器时自动切换为紧凑模式（小图标 + 无文本 + 工具提示）。这是 TabSupport 库的高级用法，用于处理数量不可预知的 Tab 场景。

## 涉及文件

| 文件 | 来源 Mod | 角色 |
|------|---------|------|
| `ReligionScreen.lua` | Better Religion Screen (2145663327) | 动态 Tab 创建逻辑 |
| `ReligionScreen.xml` | Better Religion Screen | ReligionTab Instance 定义 |

## 技术原理

### 问题背景

宗教界面需要为每个已创建的宗教显示一个 Tab。游戏可能只有 1 个宗教（游戏早期），也可能有 8+ 个（大型地图后期），Tab 数量完全不可预知。

### XML Instance 定义

```xml
<Instance Name="ReligionTab">
    <GridButton ID="Button" Size="50,34" Style="TabButton" FontSize="14" TextOffset="0,2">
        <Image ID="Icon" Size="22,22" Texture="Religions22" Offset="8,8" />
        <GridButton ID="Selection" Offset="-2,0" Size="parent,parent"
                    Style="TabButtonSelected" ConsumeMouseButton="0"
                    ConsumeMouseOver="1" Hidden="1"/>
        <Image ID="SelectionIcon" Size="22,22" Texture="Religions22" Offset="8,8" />
    </GridButton>
</Instance>
```

### 动态 Tab 创建

```lua
function UpdateTabs()
    -- 1. 清理旧数据
    m_MyReligionTab = nil
    m_AllReligionsTab = nil
    m_ReligionTabsIM:ResetInstances()

    -- 2. 重置 TabSupport
    if m_ReligionTabs ~= nil then
        m_ReligionTabs.SelectTab(nil)
        if m_ReligionTabs.prevSelectedControl ~= nil then
            m_ReligionTabs.prevSelectedControl[DATA_FIELD_SELECTION]:SetHide(true)
        end
    end

    -- 3. 创建 TabSupport 对象
    m_ReligionTabs = CreateTabs(Controls.TabContainer, 42, 34,
        UI.GetColorValueFromHexLiteral(0xFF331D05))

    -- 4. 创建"我的宗教"Tab（始终存在）
    m_MyReligionTab = AddTab(playerReligionName, religionData, ViewMyReligion)

    -- 5. 为每个已创建的宗教添加一个 Tab
    for _, religionInfo in ipairs(m_pGameReligion:GetReligions()) do
        local religionData = GameInfo.Religions[religionInfo.Religion]
        if religionData.Pantheon == false and
           m_pGameReligion:HasBeenFounded(religionInfo.Religion) then
            if religionInfo.Religion ~= m_PlayerReligionType then
                AddTab(
                    Game.GetReligion():GetName(religionInfo.Religion),
                    religionData,
                    function() ViewReligion(religionInfo.Religion) end
                )
            end
        end
    end

    -- 6. 创建"查看所有宗教"Tab（如果已有多个宗教）
    if numFoundedReligions > 0 then
        m_AllReligionsTab = AddTab(
            Locale.Lookup("LOC_UI_RELIGION_ALL_RELIGIONS",
                numFoundedReligions .. "/" .. maxReligions),
            nil,
            ViewAllReligions
        )
    end

    -- 7. 自适应尺寸调整（见下文）
    AdjustTabSizes()
end
```

### AddTab 辅助函数

```lua
function AddTab(label, religionData, onClickCallback)
    local tabInst = m_ReligionTabsIM:GetInstance()

    -- 在 Button 控件上存储附加数据，供回调使用
    tabInst.Button[DATA_FIELD_SELECTION] = tabInst.Selection
    tabInst.Button[DATA_FIELD_ICONS] = {
        Icon = tabInst.Icon,
        SelectionIcon = tabInst.SelectionIcon
    }

    -- 设置文本并计算宽度
    tabInst.Button:SetText(label)
    local textControl = tabInst.Button:GetTextControl()
    textControl:SetHide(false)
    local textSize = textControl:GetSizeX()
    tabInst.Button:SetSizeX(textSize + PADDING_TAB_BUTTON_TEXT)
    tabInst.Selection:SetSizeX(textSize + PADDING_TAB_BUTTON_TEXT + 4)

    -- 设置宗教图标和颜色
    if religionData ~= nil then
        tabInst.Button[DATA_FIELD_INDEX] = religionData.Index
        local religionColor = UI.GetColorValue(religionData.Color)
        local txX, txY, txSheet = IconManager:FindIconAtlas(
            "ICON_" .. religionData.ReligionType, SIZE_RELIGION_ICON_SMALL)
        tabInst.Icon:SetColor(religionColor)
        tabInst.Icon:SetTexture(txX, txY, txSheet)
        tabInst.SelectionIcon:SetColor(religionColor)
        tabInst.SelectionIcon:SetTexture(txX, txY, txSheet)
        tabInst.Icon:SetHide(false)
        tabInst.SelectionIcon:SetHide(true)
    else
        tabInst.Icon:SetHide(true)
        tabInst.SelectionIcon:SetHide(true)
    end

    -- 回调中管理选中状态
    local callback = function()
        if m_ReligionTabs.prevSelectedControl ~= nil then
            m_ReligionTabs.prevSelectedControl[DATA_FIELD_SELECTION]:SetHide(true)
            m_ReligionTabs.prevSelectedControl[DATA_FIELD_ICONS].SelectionIcon:SetHide(true)
        end
        tabInst.Selection:SetHide(false)
        tabInst.SelectionIcon:SetHide(false)
        onClickCallback()
    end

    m_ReligionTabs.AddTab(tabInst.Button, callback)
    return tabInst.Button
end
```

### 自适应尺寸调整

关键：计算所有 Tab 的总宽度，如果超出容器则切换为紧凑模式：

```lua
function AdjustTabSizes()  -- 实际代码在 UpdateTabs() 尾部
    -- 1. 计算所有 Tab 总宽度
    local totalSize = 0
    for _, tabButton in ipairs(m_ReligionTabs.tabControls) do
        totalSize = totalSize + tabButton:GetSizeX() + PADDING_ICON + PADDING_TABS
    end

    -- 2. 判断是否需要紧凑模式
    local numTabs = table.count(m_ReligionTabs.tabControls)
    local smallSize = SIZE_RELIGION_ICON_SMALL + (PADDING_ICON * 2)
    local bSmallTabs = totalSize > Controls.TabContainer:GetSizeX()

    -- 3. 对每个 Tab 应用模式
    for i, tabButton in ipairs(m_ReligionTabs.tabControls) do
        -- 第一个和最后一个 Tab 不缩小（它们通常是"我的宗教"和"查看全部"）
        if i ~= 1 and i ~= numTabs then
            local tabIcons = tabButton[DATA_FIELD_ICONS]
            if bSmallTabs then
                -- 紧凑模式：隐藏文本，只留图标
                tabButton:SetText("")
                tabButton:SetSizeX(smallSize)
                tabButton[DATA_FIELD_SELECTION]:SetSizeX(smallSize + 4)
                tabIcons.Icon:SetOffsetX(PADDING_RELIGION_ICON_SMALL)
                tabIcons.SelectionIcon:SetOffsetX(PADDING_RELIGION_ICON_SELECTION_SMALL)
                -- 工具提示作为唯一标识
                tabButton:SetToolTipString(
                    Game.GetReligion():GetName(tabButton[DATA_FIELD_INDEX]))
            else
                -- 正常模式：图标 + 文本
                tabIcons.Icon:SetOffsetX(PADDING_RELIGION_ICON)
                tabIcons.SelectionIcon:SetOffsetX(PADDING_RELIGION_ICON_SELECTION)
            end
        end
    end

    -- 4. 均匀分布
    m_ReligionTabs.EvenlySpreadTabs()
end
```

## 模式模板

```lua
-- ===========================================================================
-- 动态 Tab 系统模板
-- ===========================================================================

include("TabSupport")
include("InstanceManager")

local PADDING_TAB_BUTTON_TEXT = 55
local PADDING_ICON = 10
local PADDING_TABS = 10
local SIZE_ICON_SMALL = 22
local DATA_FIELD_SELECTION = "Selection"
local DATA_FIELD_ICONS = "Icons"
local DATA_FIELD_INDEX = "Index"

local m_Tabs = nil
local m_TabIM = InstanceManager:new("MyTab", "Button", Controls.TabContainer)

function UpdateTabs()
    -- 清理
    m_TabIM:ResetInstances()
    if m_Tabs ~= nil then
        m_Tabs.SelectTab(nil)
    end
    m_Tabs = CreateTabs(Controls.TabContainer, 42, 34,
        UI.GetColorValueFromHexLiteral(0xFF331D05))

    -- 动态创建 Tab
    for _, item in ipairs(GetDynamicItems()) do
        AddTab(item.Name, item.Data, function() OnTabClicked(item) end)
    end

    -- 自适应尺寸
    AdjustTabSizes()
end

function AddTab(label, itemData, onClickCallback)
    local inst = m_TabIM:GetInstance()

    -- 存储附加数据
    inst.Button[DATA_FIELD_SELECTION] = inst.Selection
    inst.Button[DATA_FIELD_ICONS] = {
        Icon = inst.Icon,
        SelectionIcon = inst.SelectionIcon
    }

    -- 设置文本和尺寸
    inst.Button:SetText(label)
    local textSize = inst.Button:GetTextControl():GetSizeX()
    inst.Button:SetSizeX(textSize + PADDING_TAB_BUTTON_TEXT)
    inst.Selection:SetSizeX(textSize + PADDING_TAB_BUTTON_TEXT + 4)

    -- 设置图标
    if itemData ~= nil then
        inst.Button[DATA_FIELD_INDEX] = itemData.Index
        local txX, txY, txSheet = IconManager:FindIconAtlas(
            "ICON_" .. itemData.IconType, SIZE_ICON_SMALL)
        inst.Icon:SetTexture(txX, txY, txSheet)
        inst.Icon:SetHide(false)
        inst.SelectionIcon:SetTexture(txX, txY, txSheet)
        inst.SelectionIcon:SetHide(true)
    else
        inst.Icon:SetHide(true)
        inst.SelectionIcon:SetHide(true)
    end

    -- 选中状态管理
    local callback = function()
        if m_Tabs.prevSelectedControl ~= nil then
            m_Tabs.prevSelectedControl[DATA_FIELD_SELECTION]:SetHide(true)
            m_Tabs.prevSelectedControl[DATA_FIELD_ICONS].SelectionIcon:SetHide(true)
        end
        inst.Selection:SetHide(false)
        inst.SelectionIcon:SetHide(false)
        onClickCallback()
    end

    m_Tabs.AddTab(inst.Button, callback)
    return inst.Button
end

function AdjustTabSizes()
    local totalSize = 0
    for _, tab in ipairs(m_Tabs.tabControls) do
        totalSize = totalSize + tab:GetSizeX() + PADDING_ICON + PADDING_TABS
    end

    local numTabs = table.count(m_Tabs.tabControls)
    local bSmallTabs = totalSize > Controls.TabContainer:GetSizeX()

    for i, tab in ipairs(m_Tabs.tabControls) do
        if i ~= 1 and i ~= numTabs and bSmallTabs then
            -- 紧凑模式
            tab:SetText("")
            tab:SetSizeX(SIZE_ICON_SMALL + PADDING_ICON * 2)
            tab[DATA_FIELD_SELECTION]:SetSizeX(SIZE_ICON_SMALL + PADDING_ICON * 2 + 4)
            tab:SetToolTipString(GetTooltipForTab(i))
        end
    end

    m_Tabs.EvenlySpreadTabs()
end
```

## 设计要点

1. **CreateTabs 每次重建**：`UpdateTabs()` 中总是先清理再重建 `CreateTabs`，确保 Tab 数量和顺序正确
2. **在 Button 上存储附加数据**：用 `tabButton[DATA_FIELD]` 存储 Selection、Icons、Index 等，在回调中可以访问
3. **两端 Tab 保持完整尺寸**：首尾 Tab（"我的宗教"和"查看全部"）即使在紧凑模式下也不缩小，保留其标识性
4. **紧凑模式保留工具提示**：文字隐藏后，工具提示成为唯一标识方式
5. **EvenlySpreadTabs**：TabSupport 会根据控件实际尺寸重新计算间距，需在尺寸调整后调用
6. **Tab 回调中管理选中状态**：总是先隐藏前一个 Tab 的选中标记，再显示当前 Tab 的选中标记

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `UI/ReligionScreen.xml` | Better Religion Screen 完整布局 — 含 Tab 容器、Tab 实例、所有内容面板 |

### Tab 相关控件 ID 对照

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `TabContainer` | Container | `Controls.TabContainer` | Tab 按钮容器（Size="Parent-80,34"，Offset="40,13"） |
| `ModalControls` | Container | `Controls.ModalControls` | 模态弹窗外壳（ModalScreen 样式） |

**Instance 模板：**

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `ReligionTab` | 宗教 Tab 按钮 | `Button`(GridButton, 50x34, "TabButton"), `Icon`(Image, 22x22, "Religions22"), `Selection`(GridButton, "TabButtonSelected", Hidden="1"), `SelectionIcon`(Image, 22x22, "Religions22") |

### ReligionTab Instance 完整 XML

```xml
<Instance Name="ReligionTab">
  <GridButton ID="Button" Size="50,34" Style="TabButton"
              FontSize="14" TextOffset="0,2">
    <Image ID="Icon" Size="22,22" Texture="Religions22" Offset="8,8" />
    <GridButton ID="Selection" Offset="-2,0" Size="parent,parent"
                Style="TabButtonSelected" ConsumeMouseButton="0"
                ConsumeMouseOver="1" Hidden="1"/>
    <Image ID="SelectionIcon" Size="22,22" Texture="Religions22" Offset="8,8" />
  </GridButton>
</Instance>
```

### Tab 外层容器 XML 结构

```xml
<Container ID="ModalControls" Style="ModalScreen">
  <Container Anchor="C,T" Offset="0,30" Size="500,61">
    <Image Anchor="C,C" Size="639,27" Texture="Controls_TabLedge2_Fill" StretchMode="Tile"/>
    <Grid Anchor="C,T" Size="980,61" Texture="Controls_TabLedge2"
          SliceCorner="194,18" SliceSize="52,26" SliceTextureSize="438,61">
      <Container ID="TabContainer" Size="Parent-80,34" Offset="40,13" />
    </Grid>
  </Container>
  <!-- 内容面板容器：WorkingTowards / SelectBeliefs / ChooseReligion / AddBeliefs -->
</Container>
```

### 紧凑模式示意

正常 Tab：图标 + 文本（如 "佛教"）
紧凑 Tab：仅图标（22x22），文本通过 `SetToolTipString` 提供

XML 中 TabButton 默认 `Size="50,34"`，紧凑模式下 Lua 调整为 `Size="34,34"` 并隐藏文本。
