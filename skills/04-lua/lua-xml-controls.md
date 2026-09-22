# Civ6 ForgeUI XML 控件参考

> **提取来源**：`Civ6_Styles.xml`(2452行)、`InGame.xml`、`DiplomacyDealView.xml`、`ActionPanel.xml`、`ProductionPanel.xml` 等官方 UI 文件。
> **涵盖**：全部 24 种 ForgeUI 控件的属性、示例和嵌套规则。

---

## 通用属性

以下属性适用于几乎所有控件：

| 属性 | 取值 | 说明 |
|------|------|------|
| `ID` | 字符串 | Lua 通过 `Controls.xxx` 查找。不需要 Lua 操作的控件可不写 |
| `Size` | `"W,H"` | 宽,高。`parent`=撑满父容器，`parent-N`=父容器减 N 像素，`auto`=内容自适应，数字=绝对像素 |
| `Anchor` | `"X,Y"` | 9 点锚定。X：`L`/`C`/`R`，Y：`T`/`C`/`B` |
| `Offset` | `"X,Y"` | 从锚点位置的偏移。**正方向 = 指向父容器中心**（Anchor=L,T 时 X+向右、Y+向下；Anchor=R,B 时 X+向左、Y+向上；Anchor=C,C 时 X+向右、Y+向上） |
| `Hidden` | `0`/`1` | `1` = 初始隐藏 |
| `Style` | 样式名 | 引用 `Civ6_Styles.xml` 中预定义的复合样式。**强烈推荐使用**——不手写纹理/字体参数 |
| `ConsumeMouse` | `0`/`1` | `1` = 吞噬鼠标事件，阻止穿透到下层控件 |
| `AnchorSide` | `"I,O"` / `"O,I"` | 锚定相对于父容器内侧/外侧边界。"O,I" 常用于挂在容器外部（滚动条等） |

## 精灵表坐标约定

按本地官方 `Controls_Close.dds` 与 `Civ6_Styles.xml`（`StateOffsetIncrement="0,34"`）核对：PNG/DDS 像素行从上往下，前四帧依次是 Normal、Hover、Down、Disabled。`StateOffsetIncrement` 的正 Y 对应向下选取下一帧；不要把整张图倒置。部分官方纹理还含额外状态帧。

```
PNG 顶部 y=0     Normal
         y=34    Hover
         y=68    Down
         y=102   Disabled
```

2026-09-23 修正：旧版“从底部向上读取”说明错误。检查转换结果时也应确认 DDS→PNG 脚本没有垂直翻转。

---

# 一、容器/布局控件

## 1. Container

最基础的容器 = HTML `<div>`。没有纹理、没有交互。用于分组和布局。

**纹理相关**：无

**专有属性**：无（纯通用属性）

**子元素**：任意控件

```xml
<!-- 全屏渲染分层容器（InGame.xml） -->
<Container ID="Screens" Size="parent,parent">
    <LuaContext ID="TechTree"  FileName="TechTree"  Hidden="1" />
</Container>

<!-- 半透明模态遮罩 -->
<Container ID="ModalBG" Size="parent,parent" Color="0,0,0,160" ConsumeMouse="1" Hidden="1" />
```

## 2. Grid

带九宫格纹理的容器 = Container + 纹理背景。没有交互（点击用 GridButton）。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Texture` | 纹理名 | 九宫格纹理源文件（无后缀） |
| `SliceCorner` | `"X,Y"` | 四角固定尺寸（像素），不被拉伸 |
| `SliceTextureSize` | `"W,H"` | 纹理图集中单帧的原尺寸 |
| `SliceSize` | `"X,Y"` | **语义待确认**。常见值 `"1,1"`，暂从模板复制，不自定义 |
| `SliceStart` | `"X,Y"` | 纹理中切片起始坐标（取非首帧时使用） |
| `InnerPadding` | `"X,Y"` | 内容区域距九宫格边框的内边距 |
| `InnerOffset` | `"X,Y"` | 内容起始偏移微调 |
| `Color` | `R,G,B,A` | 纹理染色叠加 |
| `MinSize` | `"W,H"` | 最小尺寸下限 |

**九宫格原理**：`SliceCorner="25,13"` 意味着从纹理四边向内 25×13 像素切割。四个角保持原始像素不变形，四个边单向拉伸，中心双向拉伸。与 CSS `border-image-slice`、Unity 9-slice、Android `.9.png` 一致。

```xml
<!-- 提示框背景 -->
<Grid Texture="Controls_Tooltip"
      SliceCorner="16,10" SliceTextureSize="33,32" />

<!-- 通过 Style 引用（推荐） -->
<Grid Size="300,200" Style="BlackContainer" />
```

## 3. Stack

自动布局容器 = CSS Flexbox。子元素按主轴方向自动依次排列，**不需要手动为子元素写 Anchor/Offset**。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `StackGrowth` | `"Bottom"` / `"Right"` | 主轴方向。`Bottom`=垂直向下，`Right`=水平向右 |
| `StackPadding` | 像素 | 子元素之间的间距 |
| `WrapWidth` | 像素 | 子元素总宽超过此值后换行（流式布局，较少使用） |
| `WrapGrowth` | `"Bottom"` | 换行后新行的排列方向 |
| `Padding` | 像素或`"X,Y"` | 容器内边距 |

```xml
<!-- 垂直列表（最常用） -->
<Stack ID="MyList" StackGrowth="Bottom" Size="auto,auto" Anchor="C,T">
    <GridButton ... />
    <GridButton ... />
</Stack>

<!-- 多行多列 = 嵌套 Stack（推荐方式，比 WrapWidth 更可靠） -->
<Stack StackGrowth="Bottom">         <!-- 外层：行 -->
    <Stack StackGrowth="Right">      <!-- 内层：列 -->
        <Image ... /><Label ... />
    </Stack>
    <Stack StackGrowth="Right">      <!-- 第二行 -->
        <Image ... /><Label ... />
    </Stack>
</Stack>
```

## 4. ScrollPanel

可滚动区域视口。内容超出可视区域时裁剪并提供滚动。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Vertical` | `0`/`1` | `1`=垂直滚动，`0`=水平滚动 |
| `AutoScrollBar` | `0`/`1` | `1`=内容溢出时自动显示滚动条，否则隐藏 |
| `ScrollThreshold` | 像素 | 内容超过此高度才触发滚动 |
| `SpaceForScroll` | 像素 | 为滚动条预留的额外空间 |

**`Size` 确定可视视口大小**——内容再长也不影响 ScrollPanel 自身的布局尺寸。

### 子元素

ScrollBar（见 §24）、UpButton/DownButton、内容容器（通常是 Stack）。

```xml
<!-- 用复合样式（推荐） -->
<ScrollPanel Style="ScrollPanelWithRightBar" Size="300,400" Anchor="C,C">
    <Stack StackGrowth="Bottom" Anchor="C,T">
        <!-- 列表项 -->
    </Stack>
</ScrollPanel>

<!-- 裸写（不推荐，除非需要自定义外观） -->
<ScrollPanel ID="MyScroll" Vertical="1" Size="parent-16,parent" AutoScrollBar="1" />
```

### 预定义 ScrollPanel 样式

| Style 名 | 说明 |
|----------|------|
| `ScrollPanelWithRightBar` | 右侧滚动条（通用） |
| `ScrollPanelWithLeftBar` | 左侧滚动条（少数特殊面板） |
| `WorldRankingsScrollPanel` | 世界排名面板专用 |
| `ScrollPanelHighContrast` | 高对比度样式 |

## 24. ScrollBar

滚动条 = 轨道 + 滑块 + 箭头。本质是 Slider 的滚动专用变体，通常作为 ScrollPanel 的子控件。

**三个独立部件：**

| 部件 | 样式 | 说明 |
|------|------|------|
| 轨道 | `ScrollVerticalBacking` / `ScrollHorizontalBacking` | 九宫格底板，通常挂在 ScrollPanel 右外侧 |
| 滑块 | `ScrollThumb` / `ScrollThumbAlt` | 可拖拽把手 |
| 箭头 | `ScrollUpButton` / `ScrollDownButton` | 端点箭头，2 态（Normal + Pressed） |

```xml
<!-- 完整滚动条组合 -->
<ScrollPanelWithRightBar Vertical="1" Size="18,18" AutoScrollBar="1">
    <ScrollBar  Anchor="R,C" AnchorSide="O,I" Style="ScrollVerticalBar" />
    <UpButton   Anchor="R,T" AnchorSide="O,I" Style="ScrollUpButton" />
    <DownButton Anchor="R,B" AnchorSide="O,I" Style="ScrollDownButton" />
</ScrollPanelWithRightBar>
```

**直接用 `Style="ScrollPanelWithRightBar"`，不需要手写 ScrollBar。**

---

# 二、按钮控件

## 5. GridButton

带九宫格纹理的可点击按钮。**矩形框架**，通过九宫格可缩放到任意尺寸。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Texture` | 纹理名 | 按钮九宫格纹理 |
| `SliceCorner` | `"X,Y"` | 四角参数 |
| `SliceTextureSize` | `"W,H"` | 纹理原尺寸 |
| `String` | LOC_xxx 或文本 | 按钮文字 |
| `TextAnchor` | `"X,Y"` | 文字在按钮内的锚定位置（与控件 Anchor 独立） |
| `TextOffset` | `"X,Y"` | 文字从 TextAnchor 的偏移 |
| `WrapWidth` | 像素 | 文字超宽自动换行 |
| `FontStyle` | `"shadow"`/`"glow"`/`"stroke"` | 文字效果 |
| `Color0`/`Color1`/`ColorSet` | 同 Label | 文字颜色（见 §14） |
| `SmallCaps` | 像素 | 小大写字母高度 |
| `SmallCapsType` | `"EveryWord"`/`"FirstWord"` | 小大写规则 |
| `NoStateChange` | `0`/`1` | `1`=禁用状态切换 |

### 动画/交互属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `StateOffsetIncrement` | `"0,N"` | 状态帧纵向步进（PNG/DDS 像素行向下）。4 态：Normal→Hover→Down→Disabled |
| `States` | 整数 | 状态帧数（默认 4） |
| `DisabledMouseMoveCallbacks` | `0`/`1` | `1`=禁用鼠标移动回调 |

```xml
<!-- 推荐：直接用预定义 Style -->
<GridButton ID="ConfirmBtn" Size="200,41" Anchor="C,B"
            String="LOC_OK" Style="ButtonConfirm" />

<!-- 带图标的按钮（子元素模式） -->
<GridButton Size="325,45" Style="TabFont" TextAnchor="L,C" TextOffset="100">
    <GridData Texture="Controls_DropDownControlLarge" StateOffsetIncrement="0,45"
              SliceCorner="10,15" SliceTextureSize="45,45" />
    <Container Size="62,62" Anchor="L,C">
        <Image ID="LeaderIcon" Texture="Leaders45" Size="45,45" Anchor="C,C"/>
    </Container>
</GridButton>
```

### 预定义 GridButton 样式速查

| Style 名 | 纹理尺寸 | 用途 |
|----------|----------|------|
| `ButtonConfirm` | 80×41 | 确认按钮（蓝色） |
| `ButtonRed` | 80×41 | 取消/危险按钮（红色） |
| `ButtonControl` | 24×24 缩放 | 通用控件按钮 |
| `MainButton` | 80×41 | 主菜单按钮 |
| `TabButton` | 自适应 | 标签页按钮 |
| `TabButtonSelected` | 自适应 | 标签页选中态 |
| `ProductionButton` | 102×48 | 生产面板按钮 |
| `ButtonExpand` | 57×41 | 展开/折叠按钮 |
| `ButtonLightWeight` | 32×32 缩放 | 轻量按钮 |
| `ButtonBig` | 180×63 | 大型按钮 |
| `RoundedButton` | 24×24 缩放 | 圆角通用按钮 |
| `ShellButtonOrnate` | 133×36 | 华丽装饰按钮 |

## 6. Button

固定尺寸的非矩形按钮。**圆形/箭头/X 号**，没有九宫格，不缩放——点击区域 = 纹理原生尺寸。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Texture` | 纹理名 | 按钮纹理（单帧或精灵表） |
| `NoStateChange` | `0`/`1` | `1`=禁用状态切换 |
| `String` | 文本 | 文字（极少使用，Button 通常是纯图标） |

### 动画/交互属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `StateOffsetIncrement` | `"0,N"` | 状态帧纵向步进（PNG/DDS 像素行向下），默认 4 态 |
| `States` | 整数 | 状态帧数 |

```xml
<Button ID="CloseBtn" Anchor="R,T" Offset="5,5" Style="CloseButtonLarge" />
<Button ID="BackBtn" Anchor="L,T" Style="BackButtonSmall" />
```

### 预定义 Button 样式

| Style 名 | 尺寸 | 形状 |
|----------|------|------|
| `CloseButtonLarge` | 44×44 | 圆形 X |
| `CloseButtonSmall` | 34×34 | 圆形 X |
| `CloseButtonAlt` | 32×32 | 圆形 X |
| `ClosePanelButtonSmall` | 26×26 | 圆形 X |
| `BackButtonSmall` | 27×27 | 箭头 |
| `ArrowButtonLeft` | 19×23 | 左箭头 |
| `ArrowButtonRight` | 19×23 | 右箭头 |
| `CircleButton` | 58×58 | 圆形按钮 |
| `Btn_Topbar_Quit` | 50×50 | 退出按钮 |

### 三种按钮区分

| | Button | BoxButton | GridButton |
|------|--------|-----------|------------|
| 外观 | 纹理（固定尺寸） | 纯色 | 九宫格纹理 |
| 形状 | 圆形/箭头/X 号 | 矩形 | 矩形框架 |
| 缩放 | 否 | 是 | 是（九宫格） |
| 子元素 | 是 | 是 | 是 |

## 7. BoxButton

纯色可点击矩形。没有纹理、没有九宫格——纯 Color + 点击行为。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Color` | `R,G,B,A` | 纯色填充。`"0,0,0,0"`=透明热区 |
| `ConsumeAllMouse` | `0`/`1` | 比 `ConsumeMouse` 更强——连右键一起吞 |

### 动画/交互属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `NoStateChange` | `0`/`1` | `1`=不响应状态切换（无视觉反馈） |

```xml
<!-- 透明热区（最常见） -->
<BoxButton ID="EndTurnButton" Anchor="R,B" Offset="11,28"
           Size="108,108" Color="0,0,0,0" NoStateChange="1" />

<!-- 全屏模态遮罩 -->
<BoxButton ID="ScreenConsumer" Color="0,0,0,0" Size="parent,parent" ConsumeMouse="1" />

<!-- 纯色覆盖层 -->
<BoxButton ID="MovieFill" Size="parent,parent" Color="0,0,0,255"
           Hidden="1" ConsumeAllMouse="1" />
```

Styles 文件中**没有**预定义 BoxButton 样式——全部现场手写。

---

# 三、文本/图标显示

## 14. Label

文本标签。Civ6 UI 中使用频率最高的控件。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `String` | LOC_xxx 或文本 | 支持 `[ICON_xxx]` 内嵌图标、`[NEWLINE]` 换行 |
| `Style` | 字体样式名 | 来自 Styles 的字族+字号组合 |
| `FontStyle` | `"shadow"`/`"glow"`/`"stroke"` | 文字效果 |
| `Color` | `R,G,B,A` 或命名色 | 纯色文字（不指定效果色时用） |
| `Color0` | `R,G,B,A` 或命名色 | 前景文字色（配合 FontStyle 使用，与 Color 互斥） |
| `Color1` | `R,G,B,A` 或命名色 | 效果色：shadow=阴影色，glow=辉光色，stroke=描边色 |
| `Color2` | `R,G,B,A` 或命名色 | 辉光第二层色（极少用） |
| `ColorSet` | ColorSet 名 | 预设前景/效果色对（如 `"BodyTextCool"`） |
| `Align` | `"Left"`/`"Center"`/`"Right"` | 水平对齐 |
| `WrapWidth` | 像素 | 超宽自动换行。不写则不换行 |
| `TruncateWidth` | 像素 | 超宽截断+`...`。和 WrapWidth 互斥 |
| `TruncatedTooltip` | `0`/`1` | `1`=被截断时悬停显示完整 Tooltip |
| `SmallCaps` | 像素高度 | 转为小大写字母 |
| `SmallCapsType` | `"EveryWord"`/`"FirstWord"` | 每个词 / 仅首词 |
| `LeadingOffset` | `"X,Y"` | 行间距偏移 |
| `KerningAdjustment` | 像素 | 字间距调整 |

### Color/ColorSet 协作规则

```
ColorSet="BodyTextCool"          ← 同时定义 Color0 和 Color1，一行搞定
         vs
Color0="208,212,217,255"  Color1="0,0,0,200"  FontStyle="stroke"  ← 手动指定
         vs
Color="Red"                                                      ← 纯色无效果
```

### FontStyle 三种效果

| FontStyle | 效果 | Color1 的作用 |
|-----------|------|---------------|
| `"shadow"` | 右下角投影 | 阴影颜色 |
| `"glow"` | 向外辉光 | 辉光颜色 |
| `"stroke"` | 文字边缘描边 | 描边颜色 |

```xml
<!-- 标题（Style 一把梭） -->
<Label String="LOC_MY_TITLE" Anchor="C,T" Style="ShellHeader" />

<!-- 正文 + 自动换行 -->
<Label ID="Dialog" String="LOC_DIPLO_DEAL_INTRO"
       Anchor="C,C" Style="BodyText18" WrapWidth="420" />

<!-- 截断 + 悬停看全文 -->
<Label String="LOC_LONG_TEXT" Anchor="C,C"
       Style="HeaderSmallCaps" Color0="89,85,85"
       TruncateWidth="145" TruncatedTooltip="1" />

<!-- 纯图标 -->
<Label Anchor="L,B" String="[ICON_ScienceLarge]" />
```

### 预定义文本 Style 速查

| Style 名 | 底层字体 | 效果 | 适用 |
|----------|----------|------|------|
| `FontNormal10/12/14/16/18/20/22` | 系统无衬线 | 无 | 裸字，需手动加 FontStyle |
| `FontNormalMedium14/16` | 中粗 | 无 | 同上 |
| `FontNormalBold12/14/16` | 粗体 | 无 | 同上 |
| `FontFlair14~40` | 衬线艺术字 | 无 | 同上 |
| `BodyText20/18/16/12` | FontNormal | stroke | 正文 |
| `BodyTextDark18/16/14` | FontNormal | glow | 深蓝正文 |
| `ButtonText20/18/16/14` | FontNormal | glow | 按钮文字 |
| `HeaderSmallCaps` | FontFlair16 | glow | 小大写标题 |
| `ShellHeader` | FontFlair24 | glow | 弹窗主标题 |
| `WindowHeader` | FontFlair22 | glow | 子窗口标题 |

## 8. Image

纹理/图标渲染。纯视觉，无文字、无交互。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Texture` | 纹理名 | 纹理资源。可选带 `.dds` 后缀 |
| `StretchMode` | `"None"`/`"Tile"`/`"TileY"` | 缩放模式 |
| `TextureOffset` | `"X,Y"` | 精灵表子帧偏移（PNG/DDS 像素行向下） |
| `Color` | `R,G,B,A` | 纹理染色叠加。`"0,0,0,50"`=半透明黑遮罩 |
| `Rotate` | 度数 | 旋转。支持 `90`、`270` |
| `FlipY` | `0`/`1` | 垂直翻转 |
| `ToolTip` | LOC_xxx | 悬停提示文字 |
| `ConsumeAllMouse` | `0`/`1` | 吞所有鼠标事件 |

### 动画/交互属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `ShowOnMouseOver` | `0`/`1` | `1`=仅鼠标悬停父控件时显示（常用于箭头） |
| `StateOffsetIncrement` | `"0,N"` | 状态帧步进 |

### StretchMode

| 值 | 行为 |
|----|------|
| 不写（默认） | 拉伸到 Size |
| `"None"` | 原生尺寸，不缩放 |
| `"Tile"` | 平铺重复 |
| `"TileY"` | 仅纵向平铺 |

```xml
<!-- 多层领袖头像（标准模式） -->
<Image ID="CivIconBG" Texture="CircleBacking44" Size="44,44" />
<Image Size="44,44" Texture="Circle44_Darker"  Color="0,0,0,50" Anchor="C,C" />
<Image Size="44,44" Texture="Circle44_Lighter" Color="255,255,255,100" Anchor="C,C" />
<Image ID="CivIcon" Texture="CivSymbols44" Size="44,44" Anchor="C,C" />

<!-- 平铺背景 + 渐变装饰 -->
<Image Size="parent,parent" Texture="Controls_BannerWide"
       StretchMode="Tile" ConsumeMouse="1">
    <Image Texture="Controls_GradientSmall" Size="22,parent"
           AnchorSide="O,I" Anchor="L,T" Color="0,0,0,255" Rotate="90" />
</Image>
```

---

# 四、输入控件

## 10. CheckBox

勾选框 = 状态图标 + 文字标签。有两种纹理模式。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `ButtonTexture` | 纹理名 | 未勾选态的背景纹理 |
| `ButtonSize` | `"W,H"` | 按钮（框）尺寸 |
| `CheckTexture` | 纹理名 | 勾选态纹理（通常与 ButtonTexture 同一文件的不同帧） |
| `CheckSize` | `"W,H"` | 勾选图标尺寸 |
| `CheckTextureOffset` | `"0,N"` | 勾选态帧偏移（正 Y = 向上） |
| `CheckOffset` | `"X,Y"` | 勾选图标在按钮内微调 |
| `UnCheckTexture` | 纹理名 | 手动指定未勾选纹理（扩展用） |
| `UnCheckSize` / `UnCheckTextureOffset` | — | 同上 |
| `UseSelectedTextures` | `0`/`1` | 启用 "Selected" 变体纹理（展开/折叠按钮） |
| `String` | 文本 | 标签文字 |
| `Style` | 字体样式 | 标签文字样式 |
| `TextOffset` | `"X,Y"` | 文字相对于按钮的偏移 |

**模式 B（九宫格）专用：**

| 属性 | 格式 | 说明 |
|------|------|------|
| `Texture` | 纹理名 | 九宫格纹理（替代 ButtonTexture） |
| `StateOffsetIncrement` | `"0,N"` | 状态帧步进 |
| `States` | 整数 | 状态帧数（`8` = 4 态 × 2 勾选态） |
| `SliceCorner` / `SliceTextureSize` | — | 九宫格参数 |

```xml
<!-- 设置页复选框（最简） -->
<CheckBox ID="MyToggle" Anchor="L,T"
          String="LOC_OPTION_ENABLE_FEATURE" Style="MainCheckBox" />

<!-- 大号开关按钮 -->
<CheckButton ButtonTexture="Controls_CheckButton2" ButtonSize="41,26"
             CheckTexture="Controls_CheckButton2" CheckSize="41,26"
             CheckTextureOffset="0,104" />
```

**Lua 交互：**

```lua
Controls.MyToggle:RegisterCheckHandler(function(isChecked) ... end)
Controls.MyToggle:SetCheck(true)
```

### 预定义 CheckBox 样式

| Style 名 | 框尺寸 | 用途 |
|----------|--------|------|
| `MainCheckBox` | 17×17 | 通用设置复选框 |
| `MainMenuCheck` | 17×17 | 主菜单复选框（带文字） |
| `CheckButton` | 41×26 | 大号开关按钮 |
| `CheckBoxExpand` | 41×26/22×22 | 展开/折叠箭头 |
| `CheckBoxControl` | 自适应（九宫格） | 可缩放复选框（8 态） |
| `CheckBoxModsControl` | 22×22 | Mod 管理界面 |
| `CheckBoxPopupControl` | 22×22 | 弹窗内复选框 |

## 11. PullDown

下拉选择器。固定由 **5 个子模块**构成。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `AutoSizePopup` | `0`/`1` | `1`=弹出列表自适应高度 |
| `ScrollThreshold` | 像素 | 列表超过此高度才出现滚动条 |
| `SpaceForScroll` | 像素 | 为滚动条预留的额外空间 |
| `AutoFlip` | `0`/`1` | `1`=靠近屏幕边缘时自动翻转方向 |

### 5 子模块结构（固定顺序）

```xml
<PullDown Size="194,24" AutoSizePopup="1" ScrollThreshold="450" SpaceForScroll="0">
    <!-- ① 按钮本体：始终可见的部分 -->
    <ButtonData>
        <GridButton Size="194,28" Style="TabFont" ...>
            <GridData Texture="Controls_DropDownControl" ... />
        </GridButton>
    </ButtonData>

    <!-- ② 弹出面板背景纹理 -->
    <GridData Offset="0,24" Texture="Controls_DropdownPanel"
              InnerPadding="3,6" SliceCorner="10,10" SliceTextureSize="22,22" />

    <!-- ③ 滚动面板 -->
    <ScrollPanelData Anchor="C,C" Vertical="1" Size="parent,parent" AutoScrollBar="1">
        <ScrollBar Style="Slider_Blue" Anchor="R,C" AnchorSide="O,I" />
    </ScrollPanelData>

    <!-- ④ 列表排列方向 -->
    <StackData StackGrowth="Bottom" Anchor="C,T" />

    <!-- ⑤ 列表行模板 -->
    <InstanceData Name="InstanceOne">
        <GridButton ID="Button" Style="ButtonControl"
                    Anchor="L,T" Size="190,24" ... />
    </InstanceData>
</PullDown>
```

### 预定义 PullDown 样式——直接用

| Style 名 | 尺寸 | 用途 |
|----------|------|------|
| `SmallPullDown` | 194×26 | 字体/UI 缩放选择器 |
| `PullDownBlue` | 194×24 | 通用下拉 |
| `GenericPullDown` | 自适应 | 通用自适应 |
| `PlayerSelectPullDown` | 325×50 | 选领袖（带头像） |
| `PlayerSelectPullDownMP` | 245×50 | 多人选领袖 |
| `ColorSchemePullDown` | 85×50 | 配色方案 |
| `ChatPullDown` | 自适应 | 聊天面板 |
| `PullDownMultiplayerTeam` | 194×24 | 多人队伍 |
| `PullDownPlayerSlot` | 218×46 | 玩家槽位 |

不需要手动拆解 5 部件——用预定义 Style 即可。

## 12. Slider

滑块 = 轨道（Track）+ 手柄（Thumb）。Setting 界面调节数值用。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Vertical` | `0`/`1` | `0`=水平，`1`=垂直 |
| `Texture` | 纹理名 | 轨道纹理（九宫格） |
| `Color` | `R,G,B,A` | 轨道染色 |
| `SliceCorner`/`SliceTextureSize` | — | 轨道九宫格 |

### 动画/交互属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `StateOffsetIncrement` | `"0,N"` | 通常 `"0,0"`（轨道无状态） |

### 子控件 `<Thumb>`

| 属性 | 说明 |
|------|------|
| `Texture` | 手柄纹理 |
| `Size` | 手柄尺寸 |
| `Vertical` | 与父 Slider 一致 |
| `SliceCorner`/`SliceTextureSize` | 手柄九宫格 |
| `StateOffsetIncrement` | 手柄状态步进 |

```xml
<!-- 水平设置滑块 -->
<Slider ID="VolumeSlider" Anchor="L,C" Style="SliderControl" />

<!-- 裸写 -->
<Slider ID="VertSlider" Size="18,100" Vertical="1"
        Texture="slider_vert" SliceCorner="0,6" SliceTextureSize="18,18">
    <Thumb Texture="slider_vertthumb" Size="18,18" Vertical="1"
           SliceCorner="0,3" SliceTextureSize="18,18" StateOffsetIncrement="0,18" />
</Slider>
```

### 预定义 Slider 样式

| Style 名 | 方向 | 轨道尺寸 | 用途 |
|----------|------|----------|------|
| `SliderControl` | 水平 | 220×13 | 设置页通用 |
| `Slider_Vert` | 垂直 | 18×18 | 滚动条/调节 |
| `Slider_Horiz` | 水平 | 12×8 | 水平滚动 |
| `Slider_Blue` | 垂直 | 10×14 | 蓝色主题 |
| `Slider_BlueLightweight` | 垂直 | 11×14 | 轻薄蓝色 |
| `Slider_Light` | 垂直 | 11×14 | 亮色 |
| `Slider_Religion` | 垂直 | 11×14 | 宗教面板 |

## 13. EditBox

文本输入框。支持字符限制、密码遮蔽、数字专用、实时回调。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `MaxLength` | 整数 | 最大字符数 |
| `EditMode` | `0`/`1` | `1`=激活编辑模式（大多数情况必写） |
| `String` | 文本 | 初始/默认文字 |
| `Style` | 字体样式 | 输入文字样式 |
| `FontStyle` | `"shadow"`/`"glow"`/`"stroke"` | 文字效果 |
| `Color0`/`Color1`/`ColorSet` | 同 Label | 文字色+效果色 |
| `NumberInput` | `0`/`1` | `1`=仅允许数字 |
| `Obscure` | `0`/`1` | `1`=密码模式（`***`） |
| `CallOnChar` | `0`/`1` | `1`=每次按键触发 `RegisterStringChangedCallback`（实时搜索/过滤）。不写则仅在 Enter/失焦时触发 |
| `KeepFocus` | `0`/`1` | `1`=保持键盘焦点（聊天框专用） |
| `FocusStop` | `0`/`1` | Tab 键：`0`=跳过，`1`=停留 |
| `CursorColor` | `R,G,B,A` | 光标颜色 |
| `HighlightColor` | `R,G,B,A` | 选中高亮背景色 |

```xml
<!-- 数字输入 -->
<EditBox ID="AmountBox" NumberInput="1" EditMode="1" MaxLength="11"
         Size="parent-5,parent" Style="FontNormalBold16" FontStyle="Stroke"
         ConsumeMouse="1" HighlightColor="25,120,154,200" />

<!-- 密码输入 -->
<EditBox ID="Password" EditMode="1" Obscure="1"
         Size="426,24" Style="FontNormal22" MaxLength="64" FocusStop="1" />

<!-- 实时搜索（百科） -->
<EditBox ID="SearchEditBox" Style="Civilopedia_SearchEditBox" CallOnChar="1" />
```

---

# 五、进度条控件

## 9. Meter

圆形/弧形进度填充条。填充形状完全由纹理决定（环形、弧形、圆点）。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Texture` | 纹理名 | 填充纹理（决定填充形状） |
| `Percent` | `"0"`~`"1"` | 初始填充比例 |
| `Color` | `R,G,B,A` | 填充色染色 |

### 动画/交互属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Speed` | 浮点 | 动画速度。`"0"`=瞬间跳变，`"1.0"`=正常过渡 |
| `Follow` | `0`/`1` | `1`=平滑追赶动画（从当前值过渡到新值） |

```xml
<!-- 科技进度环（平滑动画） -->
<Meter ID="ProgressMeter" Size="56,56" Anchor="C,C"
       Texture="ResearchPanel_Meter" Percent="0"
       Speed="1.0" Follow="1" />

<!-- 回合计时器（瞬间跳变） -->
<Meter ID="TurnTimerMeter" Size="95,95" Anchor="C,C"
       Texture="ActionPanel_TurnTimerFill" Speed="0" />
```

Lua：`Controls.ProgressMeter:SetPercent(0.75)`

## 19. TextureBar

方向性填充条。纹理沿指定方向拉伸表示进度——矩形定向填充。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Texture` | 纹理名 | 填充纹理 |
| `TextureOffset` | `"X,Y"` | 纹理帧偏移（PNG/DDS 像素行向下） |
| `Direction` | `"Right"`/`"Up"` | 填充方向：左→右 / 下→上 |
| `Percent` | `"0"`~`"1"` | 填充比例 |

### 动画/交互属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Speed` | 整数 | 动画速度。`"0"`=瞬间跳变 |

```xml
<!-- 水平进度条 -->
<TextureBar ID="Progress" Direction="Right" Size="295,22"
            Texture="Espionage_ProgressBar" TextureOffset="0,22"
            Speed="0" Percent="1.0" />

<!-- 垂直填充 -->
<TextureBar ID="TouristsFill" Direction="Up" Size="52,52"
            Texture="Tourism_Meter" TextureOffset="0,52" Speed="0" />
```

### Meter vs TextureBar

| | Meter | TextureBar |
|------|-------|------------|
| 填充形状 | 圆形/弧形（纹理决定） | 矩形定向拉伸 |
| 典型场景 | 科技进度环、血条 | 水平进度条、旅游业绩 |

---

# 六、动画控件

## 15. AlphaAnim

透明度动画——淡入/淡出。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `AlphaBegin`（或 `AlphaStart`） | `"0"`~`"1"` | 起始透明度 |
| `AlphaEnd` | `"0"`~`"1"` | 目标透明度 |
| `Function` | `"Root"` | 缓动函数。`"Root"`=减速缓出 |

### 动画/交互属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Speed` | 整数 | 越大越快。`"2"`=快速，`"10"`=极快 |
| `Cycle` | `"Once"`/`"Bounce"` | 播放一次 / 来回循环 |
| `Pause` | 浮点 | 播放前延迟秒数（如 `".6"`） |
| `ShowOnMouseOut` | `0`/`1` | `1`=鼠标离开时自动反向播放（按钮高亮专用） |
| `Stopped` | `0`/`1` | `1`=初始暂停，等 Lua `:Play()` |

## 16. SlideAnim

位移动画——平移滑入/滑出。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Begin`（或 `Start`） | `"X,Y"` | 起始偏移量 |
| `End`（或 `EndOffset`） | `"X,Y"` | 目标偏移量 |
| `Function` | `"Root"`/`"OutQuint"`/`"OutQuad"` | 缓动函数 |

### 动画/交互属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Speed` / `Cycle` / `Pause` / `Stopped` | 同 AlphaAnim | |

```xml
<SlideAnim ID="TurnBlockerSlide" Begin="0,30" End="0,0"
           Speed="1" Cycle="Once" Function="OutQuint" Stopped="1" />
<!-- 从下方 30px 滑入到位 -->
```

## 17. FlipAnim

精灵表帧序列动画——逐帧播放。

### 静态显示属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Texture` | 纹理名 | 精灵表纹理 |
| `FrameCount` | 整数 | 总帧数 |
| `Columns` | 整数 | 每行列数。行数 = FrameCount / Columns |
| `Size` | `"W,H"` | 每帧显示尺寸 |

### 动画/交互属性

| 属性 | 格式 | 说明 |
|------|------|------|
| `Speed` | 整数 | 帧速。`"10"`=中速，`"30"`=高速 |
| `Cycle` | `"OneBounce"` | 播完倒播回来 |
| `EndPause` | 整数 | 播完暂停秒数再循环 |
| `Color` | `R,G,B,A` | 染色叠加 |
| `Stopped` | `0`/`1` | `1`=初始暂停 |

```xml
<FlipAnim ID="GearAnim" Texture="CivicPanel_MeterFrameAnim"
          FrameCount="3" Columns="3" Speed="10" Size="40,40" Stopped="1" />

<FlipAnim Texture="AdvisorRecAnim22" Size="26,26" Anchor="C,C"
          FrameCount="12" Columns="4" Speed="14"
          EndPause="3" Color="255,255,255,200" />
```

### 动画 Lua 控制

```lua
Controls.MyAnim:SetToBeginning()  -- 重置到头
Controls.MyAnim:Play()            -- 正向播放
Controls.MyAnim:Reverse()         -- 设为反向
Controls.MyAnim:IsHidden()        -- 查询是否隐藏
Controls.MyAnim:IsReversing()     -- 查询是否正在反向播放
```

---

# 七、基础视觉控件

## 18. Box

纯色矩形。无纹理、无交互。最简单的基础控件。

| 属性 | 格式 | 说明 |
|------|------|------|
| `Color` | `R,G,B,A` | **核心属性**——纯色填充。`"0,0,0,60"`=半透明暗色 |

```xml
<!-- 暗色背景 -->
<Box Size="parent,parent-10" Color="0,0,0,60" />

<!-- 1px 竖线分隔 -->
<Box Size="1,parent" Anchor="R,C" Color="0,0,0,150" />

<!-- 透明点击拦截区 -->
<Box Size="parent,parent" Color="0,0,0,0" ConsumeMouse="1" />
```

## 20. Line

矢量线段。起点、终点、宽度、颜色。

| 属性 | 格式 | 说明 |
|------|------|------|
| `Start` | `"X,Y"` | 起点（相对父容器） |
| `End` | `"X,Y"` | 终点 |
| `Width` | 整数 | 线宽（通常 `"2"`） |
| `Color` | `R,G,B,A` | 线色 |

```xml
<Line Start="10,1" End="730,1" Color="30,66,96,255" Width="2" />
<Line Start="750,8" End="750,45" Width="2" Color="0,0,0,122" />
```

---

# 八、结构/系统控件

## 21. WorldAnchor

3D 世界空间 → 2D 屏幕坐标锚点。仅在世界控件层使用（CityBanner、UnitFlag 等）。XML 中只写占位，位置由 Lua `SetWorldPosition(x,y,z)` 动态设置。极少直接手写。

## 22. LuaContext

将 Lua 文件绑定到 UI 控件树。**每个 UI 面板的加载入口。**

| 属性 | 格式 | 说明 |
|------|------|------|
| `FileName` | 文件名 | Luas 文件名（无 `.lua` 后缀）。引擎自动加载同名 `.xml` |

```xml
<LuaContext ID="TechTree" FileName="TechTree" Hidden="1" />
```

核心机制：
1. 引擎加载 `TechTree.lua` → 自动加载 `TechTree.xml`
2. `TechTree.lua` 中 `ContextPtr` 指向此上下文根
3. `Hidden="1"` → Lua 通过 `ContextPtr:SetHide(false)` 显示

## 23. Instance

**模板/蓝图——不直接渲染。** 定义一段控件结构供 Lua 通过 `InstanceManager` 在运行时动态克隆。这是批量生成同类控件的核心机制。

| 属性 | 格式 | 说明 |
|------|------|------|
| `Name` | 字符串 | 模板名。Lua 中 `CreateInstance("Name")` |

```xml
<Instance Name="IconOnly">
    <GridButton ID="SelectButton" Style="ButtonDraggableGrid" Size="56,56" Anchor="L,T">
        <Image ID="Icon" StretchMode="None" Size="64,64" Anchor="C,C"/>
        <Label ID="AmountText" Style="FontNormalBold16" Anchor="R,B" Offset="-5,-9"/>
    </GridButton>
</Instance>
```

### Instance 的使用模式（重点）

**① 模板定义（XML 中）**：

Instance 在 XML 中定义一次，包含所有需要的子控件及 ID。这些 ID 在克隆后成为独立副本，可以各自赋值。

**② InstanceManager 创建（Lua 中）**：

```lua
-- 创建 InstanceManager（通常在 OnInit 中）
g_MyIM = InstanceManager:new("MyInstanceName", "SelectButton", Controls.MyParentContainer)

-- 克隆一个实例并赋值
local inst = g_MyIM:CreateInstance()
inst.Icon:SetTexture(iconSheet, offsetX, offsetY)
inst.AmountText:SetText("+5")
inst.SelectButton:RegisterCallback(Mouse.eLClick, OnClick)
```

**③ 带数据的列表构建**：

```lua
g_MyIM:ResetInstances()  -- 清空所有克隆
for _, data in ipairs(dataList) do
    local inst = g_MyIM:CreateInstance()
    inst.Icon:SetTexture(data.icon)
    inst.AmountText:SetText(tostring(data.amount))
end
```

**④ Instance 内控件被创建后才存在**：

```lua
-- 错误：Controls.SelectButton 不存在（这是模板 ID，不是实际控件）
-- 正确：inst = g_MyIM:CreateInstance(); inst.SelectButton:SetHide(false)
```

**⑤ 与 PullDown 的关系**：

PullDown 的 `<InstanceData Name="InstanceOne">` 本质就是 Instance——Lua 通过 PullDown 的 `AddItem()` 等方法自动管理克隆和回收。

### Instance 注意事项

- **Instance 内的 ID 只在克隆后通过 `inst.xxx` 访问**——不是全局 `Controls.xxx`
- **不要手动创建 Instance 内的按钮回调时引用全局变量**——使用闭包捕获 `data` 或 `inst`
- **ResetInstances() 后重新 CreateInstance() 之前，旧引用失效**
- **Instance 定义通常在 XML 文件顶层**（与面板内容同级），便于查找

---

# 附录 A：预定义 Style 速查总表

## 按钮类

| Style | 类型 | 说明 |
|-------|------|------|
| `ButtonConfirm` | GridButton | 蓝色确认按钮 |
| `ButtonRed` | GridButton | 红色取消按钮 |
| `ButtonControl` | GridButton | 通用控件按钮 |
| `MainButton` | GridButton | 主菜单大按钮 |
| `ButtonMainSmall` | GridButton | 主菜单小按钮 |
| `TabButton` | GridButton | 标签页按钮 |
| `TabButtonSelected` | GridButton | 标签页选中态 |
| `ProductionButton` | GridButton | 生产面板按钮 |
| `ButtonExpand` | GridButton | 展开/折叠按钮 |
| `ButtonLightWeight` | GridButton | 轻量按钮 |
| `RoundedButton` | GridButton | 圆角通用按钮 |
| `ShellButton` | GridButton | Shell 风格按钮 |
| `ShellButtonOrnate` | GridButton | 华丽装饰按钮 |
| `CloseButtonLarge` | Button | 圆形 X（44px） |
| `CloseButtonSmall` | Button | 圆形 X（34px） |
| `BackButtonSmall` | Button | 后退箭头（27px） |
| `ArrowButtonLeft` | Button | 左箭头（19×23） |
| `ArrowButtonRight` | Button | 右箭头（19×23） |
| `CircleButton` | Button | 圆形按钮（58px） |

## 文本类

| Style | 说明 |
|-------|------|
| `BodyText20/18/16/12` | 正文（FontNormal + stroke + 冷灰） |
| `BodyTextDark18/16/14` | 深蓝正文（FontNormal + glow） |
| `ButtonText20~14` | 按钮文字（FontNormal + glow） |
| `HeaderSmallCaps` | 小大写标题（FontFlair16 + glow） |
| `ShellHeader` | 弹窗主标题（FontFlair24 + glow） |
| `WindowHeader` | 子窗口标题（FontFlair22 + glow） |
| `FontNormal10/12/14/16/18/20/22` | 裸字（无效果） |
| `FontFlair14~40` | 艺术字（无效果） |

## 输入/进度类

| Style | 类型 | 说明 |
|-------|------|------|
| `MainCheckBox` | CheckBox | 通用复选框 |
| `CheckBoxControl` | CheckBox | 可缩放复选框（8 态） |
| `SliderControl` | Slider | 水平滑块（220×13） |
| `PullDownBlue` | PullDown | 通用下拉 |
| `SmallPullDown` | PullDown | 小型下拉 |

## 容器类

| Style | 说明 |
|-------|------|
| `ScrollPanelWithRightBar` | 右侧滚动条面板 |
| `ScrollPanelWithLeftBar` | 左侧滚动条面板 |
| `BlackContainer` | 黑色面板背景 |
| `BlackContainerRect` | 黑色矩形面板 |

---

# 附录 B：控件嵌套规则

| 父控件 | 可包含子控件 |
|--------|-------------|
| Container | 所有控件 |
| Grid | 所有控件 |
| Stack | 所有控件 |
| ScrollPanel | Stack、ScrollBar、UpButton、DownButton、以及内容控件 |
| GridButton | Container、Image、Label、GridData、AlphaAnim |
| Button | Image、Label 等（官方 ActionPanel.xml 的 EndTurnButtonLabel 含 Label） |
| BoxButton | Image、Label 等 |
| Slider | Thumb |
| ScrollBar | Thumb |
| PullDown | ButtonData、GridData、ScrollPanelData、StackData、InstanceData |
| CheckBox | 无（纯纹理+文字属性） |
| AlphaAnim/SlideAnim | 所有控件 |
| Instance | 所有控件（模板定义） |
