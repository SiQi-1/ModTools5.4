# PullDown 动态下拉选择器 + Modal（来源：工坊 3518104864 Carlotta / 3268741499 Noctuary）

## 做什么
在面板中创建动态下拉选择器（PullDown），支持运行时填充条目（BuildEntry）、条目选择回调（RegisterSelectionCallback）、带图标的条目（LeaderIcon），以及独立 Modal 弹窗式选择器。

---

## 模式一：面板内嵌 PullDown 选择器

### 来源：Carlotta (3518104864) 投资筛选器

### XML 定义

```xml
<Instance Name="InvestmentFilterInstance">
    <Container ID="Top" Offset="4,0" Size="auto,auto">
        <Stack StackGrowth="Right">
            <Container Offset="1,5" Size="140,auto">
                <PullDown ID="PlayerFilter" Offset="0,0" Size="140,62"
                          AutoFlip="1" AutoSizePopup="1"
                          ScrollThreshold="450" SpaceForScroll="0">
                    <!-- 下拉按钮外观 -->
                    <ButtonData>
                        <GridButton Size="81,62" Style="TabFont"
                                    TextAnchor="C,C" TextOffset="15,0" WrapWidth="150">
                            <Container Size="auto,auto" Anchor="L,C" Offset="10,-1">
                                <MakeInstance Anchor="L,C" ID="LeaderIcon"
                                              Name="LeaderIcon45"/>
                            </Container>
                            <GridData Texture="Reports_DropDownControlLarge"
                                      StateOffsetIncrement="0,45"
                                      SliceCorner="10,15" SliceTextureSize="45,45"/>
                        </GridButton>
                    </ButtonData>

                    <!-- 下拉面板外观 -->
                    <GridData Offset="0,56" Texture="Controls_DropdownPanel"
                              InnerPadding="3,6"
                              SliceCorner="10,10" SliceTextureSize="22,22"/>
                    <ScrollPanelData Anchor="C,C" Vertical="1"
                                     Size="parent,parent" AutoScrollBar="1">
                        <ScrollBar Style="Slider_Blue" Anchor="R,C" AnchorSide="I,I"/>
                    </ScrollPanelData>
                    <StackData StackGrowth="Bottom" Anchor="L,T"/>

                    <!-- 条目模板 -->
                    <InstanceData Name="InstanceOne">
                        <GridButton ID="Button" Size="124,62"
                                    Texture="Reports_ButtonControl"
                                    SliceCorner="12,6" WrapWidth="150"
                                    TextOffset="15,0" TextAnchor="C,C"
                                    SliceTextureSize="45,24"
                                    StateOffsetIncrement="0,24"
                                    Style="TabFont" Anchor="L,T">
                            <Container Size="auto,auto" Anchor="L,C" Offset="10,-1">
                                <MakeInstance Anchor="L,C" ID="LeaderIcon"
                                              Name="LeaderIcon45"/>
                            </Container>
                        </GridButton>
                    </InstanceData>
                </PullDown>
            </Container>
        </Stack>
    </Container>
</Instance>
```

### Lua 填充条目 + 选择回调

```lua
-- 填充条目
local filterList = GetMyFilterList(playerID)  -- 返回 { { Icon, Index, Name, Cost } }

for i, row in ipairs(filterList) do
    local uiEntry = {}
    m_uiFilterInstance.PlayerFilter:BuildEntry("InstanceOne", uiEntry)

    -- 设置图标（隐藏无关部分）
    uiEntry.LeaderIcon.Portrait:SetIcon(row.Icon, row.Index, true)
    uiEntry.LeaderIcon.TeamRibbon:SetHide(true)
    uiEntry.LeaderIcon.Relationship:SetHide(true)
    uiEntry.LeaderIcon.Portrait:SetAlpha(1)

    -- 设置文本
    uiEntry.Button:SetText(Locale.Lookup(row.Name))
    uiEntry.Button:SetVoid1(row.Index)
    uiEntry.Button:SetSizeX(124)
end

-- 注册选择回调（当玩家从下拉菜单选择时触发）
m_uiFilterInstance.PlayerFilter:RegisterSelectionCallback(function(selectedIndex)
    for _, row in ipairs(filterList) do
        if row.Index == selectedIndex then
            -- 更新主按钮显示
            m_uiFilterInstance.LeaderIcon.Portrait:SetIcon(row.Icon, row.Index, true)
            m_uiFilterInstance.PlayerFilter:GetButton():SetText(Locale.Lookup(row.Name))

            -- 更新操作按钮
            pInvestmentInstance.IconButton:RegisterCallback(Mouse.eLClick, function()
                ExecuteAction(row)
            end)

            -- 更新费用显示
            local cost = row.Cost or CalculateCost(row)
            pInvestmentInstance.InvestmentCost:SetText(cost)
            return true  -- 返回true表示已处理
        end
    end
end)

m_uiFilterInstance.PlayerFilter:CalculateInternals()
```

### 默认选中第一项 + 刷新操作按钮

```lua
if i == 1 then  -- 第一项作为默认
    -- 更新主显示
    m_uiFilterInstance.LeaderIcon.Portrait:SetIcon(row.Icon, row.Index, true)
    m_uiFilterInstance.PlayerFilter:GetButton():SetText(Locale.Lookup(row.Name))

    -- 注册第一项的操作回调
    pInvestmentInstance.IconButton:RegisterCallback(Mouse.eLClick, function()
        ExecuteAction(row)
    end)

    local cost = row.Cost or CalculateCost(row)
    pInvestmentInstance.InvestmentCost:SetText(cost)
end
```

---

## 模式二：独立 Modal PullDown 选择器

### 来源：Noctuary (3268741499) 单位类型选择弹出

```lua
-- 由 LuaEvent 触发打开
LuaEvents.WorldInput_Noctuary_PullDownRefresh.Add(function(units)
    -- 先清空旧条目
    Controls.PopupPullDown:ClearEntries()

    -- 动态构建条目
    for i, unit in ipairs(units) do
        local unitEntry = {}
        Controls.PopupPullDown:BuildEntry("UnitTypeListEntry", unitEntry)

        unitEntry.UnitTypeIcon:SetIcon("Icon_" .. unit.Type)
        unitEntry.Button:SetText(Locale.Lookup("LOC_" .. unit.Type .. "_NAME"))
        unitEntry.Button:RegisterCallback(Mouse.eLClick, function()
            SelectedUnit = i
            Controls.PopupPullDown:GetButton():SetText(
                Locale.Lookup("LOC_" .. unit.Type .. "_NAME"))
            Controls.UnitTypeIcon:SetIcon("Icon_" .. unit.Type)
        end)
    end

    -- 默认选中第一项
    SelectedUnitRefresh(units[1].Type, 1)

    -- 显示 Modal
    Controls.PopupRoot:SetShow(true)
    UIManager:PushModal(ContextPtr)    -- 阻塞输入

    -- 确认/取消
    Controls.ButtonOk:RegisterCallback(Mouse.eLClick, function()
        UIManager:PopModal(ContextPtr)
        Controls.PopupRoot:SetHide(true)
        LuaEvents.SomeAction(SelectedUnit)
    end)
    Controls.ButtonNo:RegisterCallback(Mouse.eLClick, function()
        UIManager:PopModal(ContextPtr)
        Controls.PopupRoot:SetHide(true)
    end)
end)
```

---

## PullDown XML 关键属性说明

| 属性 | 说明 |
|------|------|
| `AutoFlip="1"` | 空间不足时自动翻转弹出方向 |
| `AutoSizePopup="1"` | 下拉面板自动调整宽度 |
| `ScrollThreshold="450"` | 超出此高度时出现滚动条 |
| `SpaceForScroll="0"` | 不为滚动条预留空间 |
| `InnerPadding="3,6"` | 下拉面板内边距 (水平, 垂直) |
| `StateOffsetIncrement` | Button 按下/选中状态的纹理偏移 |

## LeaderIcon 嵌入条目

当条目标签需要在条目中嵌入 LeaderIcon 时：
```xml
<InstanceData Name="InstanceOne">
    <GridButton ID="Button" ...>
        <Container Size="auto,auto" Anchor="L,C" Offset="10,-1">
            <MakeInstance Anchor="L,C" ID="LeaderIcon" Name="LeaderIcon45"/>
        </Container>
    </GridButton>
</InstanceData>
```

Lua 端通过 `uiEntry.LeaderIcon.Portrait` / `.TeamRibbon` / `.Relationship` 控制器标和边饰的显隐。

## 关键 API

```lua
pullDown:ClearEntries()                       -- 清空所有条目
pullDown:BuildEntry("InstanceOne", table)     -- 从模板创建条目
pullDown:RegisterSelectionCallback(function)  -- 选择回调
pullDown:CalculateInternals()                 -- 重新计算内部布局
pullDown:GetButton():SetText("...")           -- 设置当前显示文本
UIManager:PushModal(ContextPtr)               -- 阻塞全局输入
UIManager:PopModal(ContextPtr)                -- 释放全局输入
```

---

## XML 配合

### 用到的 XML 文件

| 来源 Mod | XML 文件路径 | 作用 |
|----------|------------|------|
| Carlotta (3518104864) | `UI/Additions/Carlotta_Panel.xml` | 面板内嵌 PullDown 选择器 + Instance 模板 |
| Carlotta (3518104864) | `UI/Additions/Carlotta_EntryButton.xml` | LaunchBar 入口按钮 Instance |
| Noctuary (3268741499) | `UI/Additions/XXX.xml`（推断） | Modal 式 PullDown 选择器 |

### 控件 ID 对照（Carlotta 投资筛选器）

| XML 控件 ID | 类型 | Lua 角色 |
|------------|------|---------|
| `InvestmentFilterInstance` (Instance) | `Container` | 筛选器整体容器模板 |
| `PlayerFilter` | `PullDown` | PullDown 控件，`BuildEntry()` 填充条目 |
| `LeaderIcon` (MakeInstance) | — | 条目中嵌入的领袖图标（`Name="LeaderIcon45"`） |

### 入口按钮 Instance

```xml
<Instance Name="Carlotta_InvestmentItem">
    <Button ID="Carlotta_Investment_ItemButton" Anchor="L,C" Size="49,49"
            Texture="LaunchBar_Hook_GreatPeopleButton" Style="ButtonNormalText"
            StateOffsetIncrement="0,49" ToolTip="LOC_CARLOTTA_BU_ENTRY_BUTTON_TOOLTIP">
        <Image ID="Carlotta_Investment_ItemIcon" Texture="Placeholder"
               Size="35,35" Anchor="C,C" Offset="0,1"/>
        <Label ID="AlertIndicator" String="[ICON_New]" Anchor="R,T"
               AnchorSide="O,O" Offset="-18,-18" Hidden="1"/>
    </Button>
</Instance>
```

### PullDown Instance 模板（含条目 InstanceData）

```xml
<Instance Name="InvestmentFilterInstance">
    <Container ID="Top" Offset="4,0" Size="auto,auto">
        <PullDown ID="PlayerFilter" Offset="0,0" Size="140,62"
                  AutoFlip="1" AutoSizePopup="1"
                  ScrollThreshold="450" SpaceForScroll="0">
            <ButtonData> ... </ButtonData>
            <GridData Texture="Controls_DropdownPanel" ... />
            <ScrollPanelData ... />
            <StackData StackGrowth="Bottom" Anchor="L,T"/>
            <InstanceData Name="InstanceOne">
                <GridButton ID="Button" Size="124,62" ...>
                    <MakeInstance ID="LeaderIcon" Name="LeaderIcon45"/>
                </GridButton>
            </InstanceData>
        </PullDown>
    </Container>
</Instance>
```

### 可复用 XML

- **PullDown + InstanceData 模式**：`BuildEntry("InstanceOne", table)` 从 `InstanceData` 模板动态创建条目
- **MakeInstance 嵌入条目**：`Name="LeaderIcon45"` 引用游戏内置的领袖图标 Instance，可在 Lua 中通过 `.LeaderIcon.Portrait` 控制
- **LaunchBar 入口 Instance**：与 `lua-workshop-leader-launchbar-button.md` 共用模式
- 作为独立 Context 注册到 modinfo，或用 Instance 嵌入到其他面板中
