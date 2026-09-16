# 可折叠分类区域 + 最小化视图（来源：工坊 2066679333）

## 做什么
将列表分类（协议/城市/巨作/俘虏等）设计为可折叠区域：展开时显示完整条目，折叠时切换为紧凑的图标行（最小化视图），通过按钮切换两种显示状态。

## 如何挂载到官方UI

不涉及官方 UI 挂载——这是一种纯自定义的 XML+Instance 结构，用于自定义 Context 内部。

## 关键 Lua 代码

### 切换折叠/展开

```lua
function OnDealsHeaderCollapseButton(control, minimizedControl, button)
    if control["isCollapsed"] == nil then
        control["isCollapsed"] = false;
    end
    control["isCollapsed"] = not control["isCollapsed"];

    -- 展开列表 与 最小化列表 互斥显示
    control:SetHide(control["isCollapsed"]);
    minimizedControl:SetHide(not control["isCollapsed"]);

    control:CalculateSize();

    -- 更新按钮图标
    if control["isCollapsed"] then
        button:SetTexture("Controls_CategoryExpand");
        button:LocalizeAndSetToolTip("LOC_DIPLO_DEAL_EXPAND_CATEGORY");
    else
        button:SetTexture("Controls_CategoryCollapse");
        button:LocalizeAndSetToolTip("LOC_DIPLO_DEAL_COLLAPSE_CATEGORY");
    end
end
```

### 注册折叠按钮回调

每种类型的类别分别注册（因为展开/最小化容器的 ID 不同）：
```lua
g_uiMyOffers.CityDealsExpandButton:RegisterCallback(Mouse.eLClick, function()
    OnDealsHeaderCollapseButton(
        g_uiMyOffers.CityDealsStack,
        g_uiMyOffers.MinimizedCityDealsStack,
        g_uiMyOffers.CityDealsExpandButton
    );
end);

g_uiMyOffers.AgreementDealsExpandButton:RegisterCallback(Mouse.eLClick, function()
    OnDealsHeaderCollapseButton(
        g_uiMyOffers.AgreementDealsStack,
        g_uiMyOffers.MinimizedAgreementDealsStack,
        g_uiMyOffers.AgreementDealsExpandButton
    );
end);
```

### 条件显示折叠按钮

只有当条目数 > 1 时才显示折叠按钮；条目数为 0 则隐藏整个区块：
```lua
local itemCount = table.count(iconList.AgreementDealsStack:GetChildren());

-- 如果折叠后展开列表为空，自动切换回折叠状态
if itemCount <= 1 and iconList.AgreementDealsStack:IsHidden() then
    OnDealsHeaderCollapseButton(
        iconList.AgreementDealsStack,
        iconList.MinimizedAgreementDealsStack,
        iconList.AgreementDealsExpandButton
    );
end

-- 控制按钮和区块可见性
iconList.AgreementDealsExpandButton:SetHide(not (itemCount > 1));
iconList.AgreementDealsGrid:SetHide(itemCount == 0);
iconList.AgreementDealsHeader:SetHide(itemCount == 0);
```

### 填充时同步创建展开版和最小化版

```lua
function PopulateAvailableAgreements(player, iconList)
    local uiMinimizedSection = ms_MinimizedSectionIM:GetInstance(iconList.List);

    for i, entry in ipairs(possibleAgreements) do
        -- 完整版条目
        local uiIcon = g_IconAndTextIM:GetInstance(iconList.ListStack);

        -- 最小化版条目（相同的回调）
        local uiMinimizedIcon = g_IconOnlyIM:GetInstance(uiMinimizedSection.MinimizedSectionStack);

        -- 设置相同的点击回调
        local agreementType = entry.SubType;
        uiIcon.SelectButton:RegisterCallback(Mouse.eLClick, function()
            OnClickAvailableAgreement(player, agreementType, agreementDuration);
        end);
        uiMinimizedIcon.SelectButton:RegisterCallback(Mouse.eLClick, function()
            OnClickAvailableAgreement(player, agreementType, agreementDuration);
        end);
    end

    -- 初始化最小化容器的显示状态
    uiMinimizedSection.MinimizedSectionContainer:SetHide(iconList.ListStack:IsVisible());

    -- 注册标题上的折叠按钮
    iconList.HeaderExpandButton:RegisterCallback(Mouse.eLClick, function()
        OnDealsHeaderCollapseButton(iconList.ListStack,
            uiMinimizedSection.MinimizedSectionContainer,
            iconList.HeaderExpandButton);
    end);
    iconList.HeaderExpandButton:SetHide(table.count(iconList.ListStack:GetChildren()) == 1);
end
```

## XML 控件定义

### 类别区域结构

每种可折叠类别包含四个控件：
1. **ColumnHeader** — 标题标签
2. **ExpandButton** — 折叠/展开按钮
3. **完整 Stack** — 展开时显示的条目列表
4. **最小化 Stack** — 折叠时显示的图标行

```xml
<!-- 协议类别 -->
<Grid Style="ColumnHeader" ID="AgreementDealsHeader" Size="150,22" Offset="0,10"
      Anchor="C,T" Color="50,50,50">
  <Label String="LOC_DIPLOMACY_DEAL_AGREEMENTS" Anchor="C,C"
         Style="HeaderSmallCaps" Color0="89,85,85"/>
  <Button ID="AgreementDealsExpandButton" Anchor="R,T" Offset="-16,5"
          Size="16,16" Texture="Controls_CategoryCollapse" Hidden="1"
          ToolTip="LOC_DIPLO_DEAL_COLLAPSE_CATEGORY"/>
</Grid>

<Grid ID="AgreementDealsGrid" Style="ButtonDraggableGrid" Anchor="C,T"
      Size="Auto,Auto" MinSize="232,60">
  <Stack ID="AgreementDealsStack" Anchor="C,T" Size="Auto,Auto"/>
  <Stack ID="MinimizedAgreementDealsStack" Anchor="C,T" Size="Auto,Auto"
         StackGrowth="Right" WrapGrowth="Bottom" WrapWidth="227" Hidden="1"/>
</Grid>
```

### 最小化容器 Instance

```xml
<Instance Name="MinimizedSection">
  <Grid ID="MinimizedSectionContainer" Style="ButtonDraggableGrid"
        Size="auto,auto" MinSize="210,60" Anchor="C,T" Hidden="1">
    <Stack ID="MinimizedSectionStack" Size="auto,auto" Anchor="C,C"
           StackGrowth="Right" WrapWidth="230"/>
  </Grid>
</Instance>
```

关键：`StackGrowth="Right" WrapWidth="230"` — 图标水平排列，超出宽度自动换行。

## 数据刷新机制

每次刷新时重建所有条目（展开版 + 最小化版），根据 `itemCount` 决定按钮可见性：

1. `g_IconAndTextIM:ReleaseInstanceByParent(完整 Stack)` — 清除旧条目
2. `g_IconOnlyIM:ReleaseInstanceByParent(最小化 Stack)` — 清除旧最小化图标
3. 遍历数据 → `GetInstance()` 填充两种版本
4. 根据条目数设置按钮/区块可见性
5. `CalculateSize()`

## 应用场景

- 外交交易面板的分类区域
- 伟人列表（按类型分组）
- 任何条目较多需要按类别折叠的列表 UI

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `DiplomacyDealView.xml` | 外交交易面板 — 含所有折叠类别区域 + Instance 模板定义 |

### 可折叠类别区域控件 ID 对照

每个类别有 4 个控件组：

| 类别 | 标题 Header | 展开按钮 | 完整 Stack | 最小化 Stack |
|------|-----------|---------|-----------|------------|
| 一次性交易 | `OneTimeDealsHeader` | —（无折叠） | `OneTimeDealsStack` | — |
| 30 回合交易 | `For30TurnsDealsHeader` | —（无折叠） | `For30TurnsDealsStack` | — |
| 协议 | `AgreementDealsHeader` | `AgreementDealsExpandButton` | `AgreementDealsStack` | `MinimizedAgreementDealsStack` |
| 城市 | `CityDealsHeader` | `CityDealsExpandButton` | `CityDealsStack` | `MinimizedCityDealsStack` |
| 巨作 | `GreatWorkDealsHeader` | `GreatWorkDealsExpandButton` | `GreatWorkDealsStack` | `MinimizedGreatWorkDealsStack` |
| 俘虏 | `CaptivesDealsHeader` | `CaptivesDealsExpandButton` | `CaptivesDealsStack` | `MinimizedCaptivesDealsStack` |

Lua 引用格式：`iconList.AgreementDealsHeader`、`iconList.AgreementDealsExpandButton` 等（通过 `g_uiMyOffers` 的成员访问）。

### 折叠按钮

| XML 控件 | 展开时 Texture | 折叠时 Texture | ToolTip |
|---------|--------------|--------------|---------|
| `AgreementDealsExpandButton` | `Controls_CategoryCollapse` | `Controls_CategoryExpand` | LOC_DIPLO_DEAL_COLLAPSE/EXPAND_CATEGORY |
| `CityDealsExpandButton` | 同上 | 同上 | 同上 |

### Instance 模板汇总

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `IconOnly` | 纯图标（56x56） | `SelectButton`, `Icon`(64x64), `AmountText`, `RemoveButton`, `UnacceptableIcon`, `StopAskingButton` |
| `IconAndText` | 图标+文字（210x56） | `SelectButton`, `Icon`(44x44), `IconText`, `ValueText`(ScrollTextField), `AmountText`, `RemoveButton` |
| `SmallIconAndText` | 紧凑步骤按钮（25x25） | `SelectButton`, `Icon`(16x16), `IconText`, `ValueText` |
| `CityIconAndDetails` | 城市条目（可展开子详情） | `CityDetailsContainer`, `CityDetails`(Grid), `CityDetailsStack`(Stack), `SelectButton`, `CollapseButton`(16x16) |
| `MinimizedSection` | 折叠后的最小化容器 | `MinimizedSectionContainer`(Grid, 210x60), `MinimizedSectionStack`(Stack, Growth="Right", WrapWidth="230") |
| `LeftRightList` | 横向图标列表 | `List`(Stack), `Title`(Grid, ColumnHeader), `ListStack`(Stack, Growth="Right") |
| `SmallLeftRightList` | 小型横向列表（60x60） | `List`(Stack, 60x60), `ListStack`(Stack, WrapWidth="60") |
| `TopDownList` | 纵向列表（协议等） | `List`(Stack), `Title`(Grid, ColumnHeader), `HeaderExpandButton`(Button), `ListStack`(Stack, Growth="Bottom") |
| `MyOffers` | 我方供应总容器 | `OfferStack`(Stack, Growth="Bottom"), 含 OneTime/For30Turns/Agreement/City 等全部类别区域 |

### 可折叠类别 XML 模板

```xml
<!-- 协议类别示例 -->
<Grid Style="ColumnHeader" ID="AgreementDealsHeader"
      Size="150,22" Offset="0,10" Anchor="C,T" Color="50,50,50">
  <Label String="LOC_DIPLOMACY_DEAL_AGREEMENTS" Anchor="C,C"
         Style="HeaderSmallCaps" Color0="89,85,85"/>
  <Button ID="AgreementDealsExpandButton" Anchor="R,T" Offset="-16,5"
          Size="16,16" Texture="Controls_CategoryCollapse" Hidden="1"
          ToolTip="LOC_DIPLO_DEAL_COLLAPSE_CATEGORY"/>
</Grid>
<Grid ID="AgreementDealsGrid" Style="ButtonDraggableGrid"
      Anchor="C,T" Size="Auto,Auto" MinSize="232,60">
  <Stack ID="AgreementDealsStack" Anchor="C,T" Size="Auto,Auto"/>
  <Stack ID="MinimizedAgreementDealsStack" Anchor="C,T" Size="Auto,Auto"
         StackGrowth="Right" WrapGrowth="Bottom" WrapWidth="227" Hidden="1"/>
</Grid>
```

### 隐藏容器

```xml
<Container ID="IconOnlyContainer" Hidden="1"/>
<Container ID="IconAndTextContainer" Hidden="1"/>
<Container ID="LeftRightListContainer" Hidden="1"/>
<Container ID="SmallLeftRightListContainer" Hidden="1"/>
<Container ID="TopDownListContainer" Hidden="1"/>
<Container ID="HistoryListContainer" Hidden="1"/>
```

这些隐藏容器是所有 InstanceManager 的初始父节点。实例通过 `GetInstance(targetStack)` 创建到目标 Stack 中才可见。
