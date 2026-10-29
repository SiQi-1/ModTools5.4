# Civ6 ForgeUI XML 控件参考 — 输入控件

> 分册：由 [lua-xml-controls.md](lua-xml-controls.md) 按主题拆出；覆盖 四、输入控件。触发：写 CheckBox、PullDown、Slider、EditBox 时。

## 四、输入控件

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

