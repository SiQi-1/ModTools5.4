# Civ6 ForgeUI XML 控件参考 — 文本/图标

> 分册：由 [lua-xml-controls.md](lua-xml-controls.md) 按主题拆出；覆盖 三、文本/图标显示。触发：写 Label、Image 时。

## 三、文本/图标显示

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

