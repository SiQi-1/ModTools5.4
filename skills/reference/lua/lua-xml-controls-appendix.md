# Civ6 ForgeUI XML 控件参考 — 附录

> 分册：由 [lua-xml-controls.md](lua-xml-controls.md) 按主题拆出；覆盖 附录 A：预定义 Style 速查总表、附录 B：控件嵌套规则。触发：查 Style 总表与控件嵌套规则时。

## 附录 A：预定义 Style 速查总表

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
| `FontFlair14/16/18/20/22/24/26/28/30/40` | 艺术字；不是连续序列，FontFlair32 不存在，核对目标语言 Fonts/Civ6_FontStyles 文件 |

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

## 附录 B：控件嵌套规则

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
