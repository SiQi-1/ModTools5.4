# 04-lua 技能索引

## 基础规范

事件环境见 [LuaEvents / Events / GameEvents 环境表](code-style.md#事件环境与运行时核验)：LuaEvents 同环境可用（含 GP-GP），Events 两端可用，GameEvents 原生位于 GP。
- **[code-style.md](code-style.md)** — Lua 代码规范（GP/UI 环境分离、原生属性零返回值、命名、通信、Support 函数索引）
- **[lua-multiplayer-stable.md](lua-multiplayer-stable.md)** — 联机稳定通信写法（唯一提交者模式；⚠️仅用户要求联机稳定才用；变体A=AI无效果，变体B=主机0代AI提交）
- **[lua-crash-bisect.md](lua-crash-bisect.md)** — 无日志开局崩溃二分排查（文件停载→挂载注释→Initialize→行级 `--` 注释；末行分号/噪音清单/虚空接口/Cache 佐证；0054 实录）

## GP 函数库（直接复制使用）
- **[lua-gp-resource.md](lua-gp-resource.md)** — 非战斗：产出/伟人/建筑/修改器/科技/地块/计数/分期扣款
- **[lua-gp-combat.md](lua-gp-combat.md)** — 战斗：伤害/击杀/经验/晋升/技能冷却/反伤/衰减/AOE
- **[lua-binary.md](lua-binary.md)** — 产出二进制选型（动态 Property / 永久增量 AttachModifierByID、位范围、防重与存档迁移）

## XML 参考（ForgeUI 控件系统）
- **[lua-xml-controls.md](lua-xml-controls.md)** — 24 种控件的完整属性表+示例：容器/按钮/文本/输入/进度条/动画/结构

## HTML 设计落地

- **[civ6-html-ui](../civ6-html-ui/SKILL.md)** — HTML/CSS → PNG → 原生 XML/Lua：精确导出、四态/九宫格、独立页面与弹窗、CIV 注册及验收；含可分享工具包。

## UI 模版库
- **[lua-ui-button.md](lua-ui-button.md)** — 按钮模版：城市面板/单位面板/选地格/CheckBox/条件显示

## 自有 Mod 系统（完整子系统）
- **[lua-core-shop.md](lua-core-shop.md)** — 双货币商店系统（商品/栏位/CRUD/动态参数）
- **[lua-13-livestream.md](lua-13-livestream.md)** — 热度直播打赏系统（对数阈值/66奖励/弹幕模拟）
- **[lua-0013-aoe-combat-engine.md](lua-0013-aoe-combat-engine.md)** — AOE战斗引擎（近战溅射 + 占卜经济）
- **[lua-0013-divination-economy.md](lua-0013-divination-economy.md)** — 占卜点数经济系统（与AOE配套）
- **[lua-0022-xingliu-economy.md](lua-0022-xingliu-economy.md)** — 心流双资源经济（积累/消耗/商店）
- **[lua-0029-quest-system.md](lua-0029-quest-system.md)** — 任务+奖励系统（6级35种任务类型）
- **[lua-0029-lingzhi-economy.md](lua-0029-lingzhi-economy.md)** — 灵质经济系统（8种产出属性复合，与任务系统配套）
- **[lua-0029-leader-abilities.md](lua-0029-leader-abilities.md)** — 七大领袖能力
- **[lua-0029-gp-ui-communication.md](lua-0029-gp-ui-communication.md)** — GP-UI 通信全景（7条管道）
- **[lua-0029-spirit-unit.md](lua-0029-spirit-unit.md)** — 生灵单位系统
- **[lua-0031-skill-cooldown-duration.md](lua-0031-skill-cooldown-duration.md)** — 技能冷却与持续时间管理
- **[lua-0031-unit-summon-engine.md](lua-0031-unit-summon-engine.md)** — 单位召唤引擎（6层验证链）
- **[lua-0031-wonder-charge-system.md](lua-0031-wonder-charge-system.md)** — 奇观加速充能（30层递增）
- **[lua-0031-splash-damage-combat.md](lua-0031-splash-damage-combat.md)** — 溅射伤害战斗（60%邻格扩散）
- **[lua-0032-prop-dual-economy.md](lua-0032-prop-dual-economy.md)** — 属性双资源经济（星辉/星数）
- **[lua-0033-citypanel-resource-spending.md](lua-0033-citypanel-resource-spending.md)** — 城市面板资源消费
- **[lua-0034-lens-plot-purchase.md](lua-0034-lens-plot-purchase.md)** — UILens 透镜地块购买
- **[lua-0035-ui-file-replacement.md](lua-0035-ui-file-replacement.md)** — UI 文件替换（ui_replace / ReplaceUIScript、CityPanel ViewMain 产出来源拆分）
- **[lua-0036-productivity-stockpile.md](lua-0036-productivity-stockpile.md)** — 生产力蓄力与自动投资
- **[lua-0037-plot-pillage-system.md](lua-0037-plot-pillage-system.md)** — 单元格掠夺与产出修改
- **[lua-19-fever-system.md](lua-19-fever-system.md)** — Fever 进度累计与模式切换

## 官方 UI 面板 — 完整分析（XML+Lua 双文件对照）

> 内容为对官方游戏 UI 文件（Firaxis/2K）的分析，仓库不随包分发游戏文件，仅作参考。

### 核心架构
- **[lua-workshop-ingame-structure.md](lua-workshop-ingame-structure.md)** — InGame 控件树全景（11层渲染+LuaContext加载+BulkHide机制+Mod注入点）
- **[lua-workshop-popupdialog.md](lua-workshop-popupdialog.md)** — PopupDialog 标准弹窗框架（8种内容模板+生命周期+命令系统）
- **[lua-workshop-instance-manager.md](lua-workshop-instance-manager.md)** — InstanceManager 动态克隆系统（3种类+Instance模板写法+Lua包装类模式）
- **[lua-workshop-support-libs.md](lua-workshop-support-libs.md)** — Support 共享库（4个核心文件：SupportFunctions+Civ6Common+ToolTipHelper+PopupManager）

### HUD 面板
- **[lua-workshop-actionpanel.md](lua-workshop-actionpanel.md)** — 结束回合按钮+动画系统（AlphaAnim+SlideAnim+FlipAnim+Meter全覆盖）
- **[lua-workshop-citypanel.md](lua-workshop-citypanel.md)** — 城市详情面板（产出/人口/建筑/生产/简介+MOD按钮ActionStack注入点）
- **[lua-workshop-unitpanel.md](lua-workshop-unitpanel.md)** — 单位操作面板+UnitFlagManager 3D旗帜（MOD钩子5个+旗帜对象系统）
- **[lua-workshop-production-panel.md](lua-workshop-production-panel.md)** — 生产选择器+LaunchBar+TopPanel（三合一HUD条）
- **[lua-workshop-worldtracker-minimap.md](lua-workshop-worldtracker-minimap.md)** — 科技追踪器+小地图镜头+通知面板+状态消息

### 外交系统
- **[lua-workshop-diplomacy-dealview.md](lua-workshop-diplomacy-dealview.md)** — 交易界面（9个Instance模板黄金标准+展开折叠+数值编辑）
- **[lua-workshop-diplomacy-actionview.md](lua-workshop-diplomacy-actionview.md)** — 外交三件套（领袖面板+丝带+3D场景+28个IM）

### 全屏面板
- **[lua-workshop-techtree.md](lua-workshop-techtree.md)** — 科技/市政树（4层同步滚动+FlipAnim+Meter+搜索+弹窗选择器）
- **[lua-workshop-government-greatworks.md](lua-workshop-government-greatworks.md)** — 政体政策卡+巨作管理（拖拽系统+嵌套IM+展开折叠组）
- **[lua-workshop-report-religion-trade.md](lua-workshop-report-religion-trade.md)** — 报告/宗教/贸易面板（TabSupport标签+可折叠组+路线选择器）

### 弹窗+菜单+样式
- **[lua-workshop-popups-system.md](lua-workshop-popups-system.md)** — 7种系统弹窗全览（电影化+居中面板+队列+触发源）
- **[lua-workshop-menus-overlays.md](lua-workshop-menus-overlays.md)** — 暂停菜单+存档+城邦+世界排名+结束画面
- **[lua-workshop-styles-reference.md](lua-workshop-styles-reference.md)** — Styles+ColorAtlas样式颜色字体速查（100+皮肤+60+颜色+7字体族）

## 本地保留的工坊提炼资料（不随仓库分享）

2026-10-26 起，原「工坊 — 」各节的 92 篇他人 Steam 工坊 Mod 提炼资料已移出仓库，只保留在维护者本机 `local_notes/04-lua-workshop/`，不进入 Git、不随源码分享、不主张再分发。用户自有 Mod 系统资料继续随仓库分享；官方游戏 UI 文件分析保留在上一节。
