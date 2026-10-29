# Civ6 ForgeUI XML 控件参考 — 容器/布局

> 分册：由 [lua-xml-controls.md](lua-xml-controls.md) 按主题拆出；覆盖 一、容器/布局控件。触发：写容器、Grid、Stack、ScrollPanel 时。


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

## 一、容器/布局控件

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

