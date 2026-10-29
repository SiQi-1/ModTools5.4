# Civ6 ForgeUI XML 控件参考 — 按钮

> 分册：由 [lua-xml-controls.md](lua-xml-controls.md) 按主题拆出；覆盖 二、按钮控件。触发：写 GridButton、Button、BoxButton 时。

## 二、按钮控件

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

