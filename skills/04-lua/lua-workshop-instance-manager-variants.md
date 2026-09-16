# InstanceManager 多变体模式（来源：工坊 2066679333）

## 做什么
定义多种 InstanceManager，每种对应不同的 UI 条目呈现风格（仅图标 / 图标+文字 / 图标+详情 / 小型化等），运行时根据数据特征选择合适的 InstanceManager 来生成 UI 条目。

## 如何挂载到官方UI

InstanceManager 只需要指定控件容器，不需要挂载到官方 UI——它们在 XML Instance 模板中预先定义了控件的子元素结构：

```lua
-- 在初始化时创建多个 InstanceManager，指向不同的隐藏容器
g_IconOnlyIM         = InstanceManager:new("IconOnly",       "SelectButton", Controls.IconOnlyContainer)
g_IconAndTextIM      = InstanceManager:new("IconAndText",    "SelectButton", Controls.IconAndTextContainer)
g_SmallIconAndTextIM = InstanceManager:new("SmallIconAndText","SelectButton", Controls.IconOnlyContainer)
ms_CityDetailsIM     = InstanceManager:new("CityIconAndDetails", "CityDetailsContainer", Controls.IconAndTextContainer)
ms_MinimizedSectionIM = InstanceManager:new("MinimizedSection", "MinimizedSectionContainer")
```

注意：多个 IM 可以指向同一个隐藏容器（如 `g_IconOnlyIM` 和 `g_SmallIconAndTextIM` 都指向 `Controls.IconOnlyContainer`），但它们的 Instance Name 不同。

## 关键 Lua 代码

### 变体 1：IconOnly — 纯图标 + 数量

```lua
-- 获取实例
local uiIcon = g_IconOnlyIM:GetInstance(iconList.ListStack);

-- 设置图标
SetIconToSize(uiIcon.Icon, "ICON_YIELD_GOLD_5");

-- 设置数量
uiIcon.AmountText:SetText(tostring(goldBalance));
uiIcon.AmountText:SetHide(false);

-- 隐藏不需要的控件
uiIcon.ValueText:SetHide(true);
uiIcon.RemoveButton:SetHide(true);

-- 注册回调
uiIcon.SelectButton:RegisterCallback(Mouse.eLClick, function() ... end);
```

### 变体 2：IconAndText — 图标 + 描述文字 + 可选值

```lua
local uiIcon = g_IconAndTextIM:GetInstance(iconList.ListStack);

SetIconToSize(uiIcon.Icon, "ICON_" .. info.DiplomaticActionType, 38);
uiIcon.IconText:LocalizeAndSetText("LOC_DIPLOMACY_DEAL_GOLD_PER_TURN");
uiIcon.AmountText:SetHide(true);
uiIcon.ValueText:LocalizeAndSetText(valueName);

uiIcon.SelectButton:RegisterCallback(Mouse.eLClick, function() ... end);
uiIcon.RemoveButton:RegisterCallback(Mouse.eLClick, function() ... end);
```

### 变体 3：SmallIconAndText — 紧凑步骤按钮

用于快速增减（如金币 +/- 1、10、500 等）：
```lua
local uiIcon = g_SmallIconAndTextIM:GetInstance(iconListInner.ListStack);
uiIcon.IconText:SetText("500")  -- 按钮显示的文字
uiIcon.SelectButton:RegisterCallback(Mouse.eLClick, function()
    OnClickAvailableOneTimeGold(player, 500);
end);
uiIcon.SelectButton:RegisterCallback(Mouse.eRClick, function()
    OnClickAvailableOneTimeGold(player, -500);
end);
```

### 变体 4：CityIconAndDetails — 可展开的子详情

城市条目可以展开显示其附属的资源/巨作：
```lua
local uiIcon = ms_CityDetailsIM:GetInstance(iconList.CityDealsStack);

-- 展开/折叠按钮
uiIcon.CollapseButton:RegisterCallback(Mouse.eLClick, function()
    OnCityDetailsCollapse(uiIcon.CityDetails, typeName, uiIcon.CollapseButton);
end);

-- 子条目通过 g_IconOnlyIM 填入 CityDetailsStack
local childIcon = g_IconOnlyIM:GetInstance(uiIcon.CityDetailsStack);
SetIconToSize(childIcon.Icon, "ICON_" .. resourceDesc.ResourceType);
```

### 变体 5：MinimizedSection — 折叠后的最小化视图

```lua
local uiMinimizedSection = ms_MinimizedSectionIM:GetInstance(iconList.List);
local uiMinimizedIcon = g_IconOnlyIM:GetInstance(uiMinimizedSection.MinimizedSectionStack);

SetIconToSize(uiMinimizedIcon.Icon, "ICON_" .. info.DiplomaticActionType, 38);
uiMinimizedIcon.SelectButton:RegisterCallback(Mouse.eLClick, function() ... end);
```

### 释放实例（切换父容器时）

在重新填充前，先释放之前占用该容器的所有实例：
```lua
-- 释放特定父容器下的所有实例
g_IconOnlyIM:ReleaseInstanceByParent(iconList.CaptivesDealsStack);
g_IconAndTextIM:ReleaseInstanceByParent(iconList.AgreementDealsStack);
```

### 全部重置（打开面板时）

```lua
g_IconOnlyIM:ResetInstances();
g_IconAndTextIM:ResetInstances();
g_SmallIconAndTextIM:ResetInstances();
ms_MinimizedSectionIM:ResetInstances();
```

## XML 控件定义

### IconOnly Instance

```xml
<Instance Name="IconOnly">
  <GridButton ID="SelectButton" Style="ButtonDraggableGrid" Size="56,56" Anchor="L,T">
    <Image ID="Icon" StretchMode="None" Size="64,64" Anchor="C,C"/>
    <Label ID="AmountText" Style="FontNormalBold16" Anchor="R,B" Offset="-5,-9" FontStyle="Stroke" />
    <Button ID="RemoveButton" Anchor="L,B" Offset="-10,-10" Size="16,16" Hidden="1"/>
  </GridButton>
</Instance>
```

### IconAndText Instance

```xml
<Instance Name="IconAndText">
  <GridButton ID="SelectButton" Style="ButtonDraggableGrid" Size="210,56" Anchor="L,T">
    <Stack Size="parent,0" StackGrowth="Right">
      <Container Size="44,parent">
        <Image ID="Icon" StretchMode="None" Size="44,44" Anchor="C,C"/>
        <Label ID="AmountText" Anchor="R,B" Style="FontNormalBold12" Offset="24,-9"/>
      </Container>
      <Container Size="parent-44,parent">
        <Stack StackGrowth="Bottom" Anchor="L,C">
          <Label ID="IconText" Size="parent,0" Style="FontNormalBold12"/>
          <ScrollTextField ID="ValueText" Size="125,0" Style="FontNormalBold12"/>
        </Stack>
      </Container>
    </Stack>
    <Button ID="RemoveButton" Anchor="R,B" Offset="-4,-4" Size="22,22" Hidden="1"/>
  </GridButton>
</Instance>
```

### 关键点

- 所有 InstanceManager 的隐藏容器放在 XML 顶层，**hidden="0" 或不设 hidden**（实际上它们不直接可见）：
```xml
<Container ID="IconOnlyContainer" Hidden="1"/>
<Container ID="IconAndTextContainer" Hidden="1"/>
```
- 实例生成到目标 Stack 中时才会可见
- 同一个控件模板可被多个 IM 分别管理（只要 Instance Name 不同）

## 数据刷新机制

### 填充前先释放

每个 Populate 函数开头：
```lua
function PopulateDealResources(player, iconList)
    g_IconOnlyIM:ReleaseInstanceByParent(iconList.OneTimeDealsStack);
    g_IconAndTextIM:ReleaseInstanceByParent(iconList.For30TurnsDealsStack);
    -- ... 然后遍历数据，GetInstance() 填充
end
```

### 空类别隐藏

```lua
-- 如果该类别没有条目，隐藏标题和容器
iconList.OneTimeDealsHeader:SetHide(table.count(iconList.OneTimeDealsStack:GetChildren()) == 0);
iconList.For30TurnsDealsHeader:SetHide(table.count(iconList.For30TurnsDealsStack:GetChildren()) == 0);
```

### 填充后计算尺寸

```lua
iconList.OfferStack:CalculateSize();
```

## 应用场景

- 交易面板（商品库存展示）
- 伟人选择器
- 任何需要多种展示风格的列表 UI

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `DiplomacyDealView.xml` | 外交交易面板 — 含所有 Instance 变体定义 + 隐藏容器 |

### 隐藏容器（IM 初始父节点）

| XML 控件（ID） | 类型 | 用途 |
|---------------|------|------|
| `IconOnlyContainer` | Container | IconOnly / SmallIconAndText IM 的初始父容器（Hidden="1"） |
| `IconAndTextContainer` | Container | IconAndText / CityIconAndDetails IM 的初始父容器（Hidden="1"） |
| `LeftRightListContainer` | Container | LeftRightList IM 的初始父容器 |
| `SmallLeftRightListContainer` | Container | SmallLeftRightList IM 的初始父容器 |
| `TopDownListContainer` | Container | TopDownList IM 的初始父容器 |
| `HistoryListContainer` | Container | HistoryList IM 的初始父容器 |

### Instance 变体完整控件 ID 对照

#### IconOnly

| 控件 ID | 类型 | 尺寸 | 用途 |
|--------|------|------|------|
| `SelectButton` | GridButton | 56x56 | 点击区域（ButtonDraggableGrid 样式） |
| `Icon` | Image | 64x64 | 图标（StretchMode="None"） |
| `AmountText` | Label | — | 数量文字（R,B 锚定，FontNormalBold16） |
| `UnacceptableIcon` | Image | 18x18 | 不可交易警告（Alert18 纹理） |
| `RemoveButton` | Button | 16x16 | 移除按钮（Controls_RemoveDealSmall） |
| `StopAskingButton` | Button | 16x16 | 标记不可接受按钮 |

#### IconAndText

| 控件 ID | 类型 | 尺寸 | 用途 |
|--------|------|------|------|
| `SelectButton` | GridButton | 210x56 | 点击区域 |
| `Icon` | Image | 44x44 | 图标 |
| `AmountText` | Label | — | 数量（R,B，FontNormalBold12） |
| `IconText` | Label | — | 描述文字（FontNormalBold12） |
| `ValueText` | ScrollTextField | 125px 宽 | 值文本（可滚动） |
| `UnacceptableIcon` | Image | 18x18 | 警告图标 |
| `RemoveButton` | Button | 22x22 | 移除按钮（Controls_RemoveDeal） |
| `StopAskingButton` | Button | 16x16 | 标记按钮 |

#### SmallIconAndText

| 控件 ID | 类型 | 尺寸 | 用途 |
|--------|------|------|------|
| `SelectButton` | GridButton | 25x25 | 紧凑点击区域 |
| `Icon` | Image | 16x16 | 小图标 |
| `AmountText` | Label | — | 数量 |
| `IconText` | Label | — | 文字 |
| `ValueText` | ScrollTextField | — | 值 |

#### CityIconAndDetails

| 控件 ID | 类型 | 尺寸 | 用途 |
|--------|------|------|------|
| `CityDetailsContainer` | Container | Auto, MinSize=210x60 | 城市详情外层 |
| `CityDetails` | Grid | 210xauto | 城市详情展开区域（Hidden="1"） |
| `CityDetailsStack` | Stack | — | 子条目挂载点（Growth="Right", WrapWidth="210"） |
| `SelectButton` | GridButton | 210x56 | 城市行主点击区域 |
| `CollapseButton` | Button | 16x16 | 展开/折叠按钮（Controls_CityExpand 纹理） |

#### MinimizedSection

| 控件 ID | 类型 | 尺寸 | 用途 |
|--------|------|------|------|
| `MinimizedSectionContainer` | Grid | Auto, MinSize=210x60 | 最小化视图容器（Hidden="1"） |
| `MinimizedSectionStack` | Stack | — | 最小化图标行（Growth="Right", WrapWidth="230"） |

### 多个 IM 共享父容器

```lua
-- 两个 IM 都指向 IconOnlyContainer
g_IconOnlyIM          = InstanceManager:new("IconOnly",    "SelectButton", Controls.IconOnlyContainer)
g_SmallIconAndTextIM  = InstanceManager:new("SmallIconAndText", "SelectButton", Controls.IconOnlyContainer)

-- 两个 IM 都指向 IconAndTextContainer
g_IconAndTextIM       = InstanceManager:new("IconAndText", "SelectButton", Controls.IconAndTextContainer)
ms_CityDetailsIM      = InstanceManager:new("CityIconAndDetails", "CityDetailsContainer", Controls.IconAndTextContainer)
```

父容器仅用于创建过程，实际的控件被 `GetInstance(targetStack)` 移动到目标 Stack 中才可见。
