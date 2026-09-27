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

## 工坊 — 面板/弹窗/界面框架
- **[lua-workshop-standalone-modal.md](lua-workshop-standalone-modal.md)** — 独立 Modal 屏幕 + LaunchBar 按钮注入
- **[lua-workshop-in-context-popup.md](lua-workshop-in-context-popup.md)** — 上下文内弹出编辑层
- **[lua-workshop-partial-screen-hooks.md](lua-workshop-partial-screen-hooks.md)** — PartialScreenHooks 替换官方面板
- **[lua-workshop-changeparent-overlay.md](lua-workshop-changeparent-overlay.md)** — ChangeParent 浮动叠加面板
- **[lua-workshop-ui-extend-existing.md](lua-workshop-ui-extend-existing.md)** — 扩展已有 UI（Lua 函数覆盖+XML 注入）
- **[lua-workshop-import-files.md](lua-workshop-import-files.md)** — ImportFiles 整文件替换模式
- **[lua-workshop-exposed-members.md](lua-workshop-exposed-members.md)** — ExposedMembers 跨 Mod 通信
- **[lua-workshop-state-machine.md](lua-workshop-state-machine.md)** — 单屏多状态导航
- **[lua-workshop-event-refresh.md](lua-workshop-event-refresh.md)** — 事件驱动 UI 自动刷新
- **[lua-workshop-session-persistence.md](lua-workshop-session-persistence.md)** — 跨会话状态持久化（GameConfig/序列化/存档）
- **[lua-workshop-modular-support-file.md](lua-workshop-modular-support-file.md)** — 模块化共享 Support 文件
- **[lua-workshop-wildcard-include-extensibility.md](lua-workshop-wildcard-include-extensibility.md)** — 通配符 include 扩展机制

## 工坊 — 列表/表格/排序/过滤
- **[lua-workshop-sort-bar.md](lua-workshop-sort-bar.md)** — 多列排序栏 + Shift/Ctrl 优先排序
- **[lua-workshop-collapsible-sections.md](lua-workshop-collapsible-sections.md)** — 可折叠分类区域 + 最小化视图
- **[lua-workshop-composite-filter.md](lua-workshop-composite-filter.md)** — 复合过滤下拉菜单
- **[lua-workshop-confirm-workflow.md](lua-workshop-confirm-workflow.md)** — 多步确认提交工作流
- **[lua-workshop-dynamic-tabs.md](lua-workshop-dynamic-tabs.md)** — 动态 Tab 系统（自适应尺寸）
- **[lua-workshop-dynamic-im.md](lua-workshop-dynamic-im.md)** — 动态 InstanceManager（按需创建缓存）
- **[lua-workshop-instance-manager-variants.md](lua-workshop-instance-manager-variants.md)** — InstanceManager 多变体（图标/文字/迷你等）
- **[lua-workshop-instance-extension.md](lua-workshop-instance-extension.md)** — XML Instance 扩展（向已有模板追加控件）
- **[lua-workshop-misc-tooltip-override.md](lua-workshop-misc-tooltip-override.md)** — ToolTip 覆写模式
## 工坊 — 专项面板
- **[lua-workshop-great-people-ui.md](lua-workshop-great-people-ui.md)** — 伟人界面（三标签页+过滤器+规划器）
- **[lua-workshop-tourism-overview.md](lua-workshop-tourism-overview.md)** — 旅游概览面板
- **[lua-workshop-espionage.md](lua-workshop-espionage.md)** — 间谍界面增强（双模式选择+动画）
- **[lua-workshop-report-unit-list.md](lua-workshop-report-unit-list.md)** — 单位报表（可折叠分组+多字段排序）
- **[lua-workshop-climate-screen.md](lua-workshop-climate-screen.md)** — 气候界面（饼图+事件历史+CO2追踪）
- **[lua-workshop-world-rankings.md](lua-workshop-world-rankings.md)** — 世界排名（数据增强+胜利适配）
- **[lua-workshop-era-tracker.md](lua-workshop-era-tracker.md)** — 时代追踪器（Tab+复选筛选+搜索）
- **[lua-workshop-greatest-cities.md](lua-workshop-greatest-cities.md)** — 伟大城市排名全屏界面
- **[lua-workshop-top-panel-extension.md](lua-workshop-top-panel-extension.md)** — 顶部面板扩展（产量/资源/Tooltip）
- **[lua-workshop-loading-screen.md](lua-workshop-loading-screen.md)** — 加载界面替换模式

## 工坊 — 通知/弹窗/对话
- **[lua-workshop-notification-log.md](lua-workshop-notification-log.md)** — 通知日志面板（WorldTracker 扩展）
- **[lua-workshop-simplified-gossip.md](lua-workshop-simplified-gossip.md)** — 外交流言简化
- **[lua-workshop-disable-popup.md](lua-workshop-disable-popup.md)** — 弹窗禁用/条件跳过
- **[lua-workshop-misc-ui-popup-choice.md](lua-workshop-misc-ui-popup-choice.md)** — UI 弹窗选择系统（Notification→Popup→PlayerOperations）

## 工坊 — 地图/透镜
- **[lua-workshop-morelens-plugin-arch.md](lua-workshop-morelens-plugin-arch.md)** — 透镜插件架构（自动发现+寄生Appeal层）
- **[lua-workshop-morelens-entry.md](lua-workshop-morelens-entry.md)** — 透镜入口数据结构契约
- **[lua-workshop-morelens-rule-color.md](lua-workshop-morelens-rule-color.md)** — 基于规则优先级的着色系统
- **[lua-workshop-morelens-subpanel.md](lua-workshop-morelens-subpanel.md)** — 透镜附加配置面板
- **[lua-workshop-auto-apply-lens.md](lua-workshop-auto-apply-lens.md)** — 单位选择时自动应用透镜
- **[lua-workshop-mouse-lens.md](lua-workshop-mouse-lens.md)** — 鼠标/键盘交互透镜（Ctrl+光标着色）
- **[lua-workshop-world-overlay.md](lua-workshop-world-overlay.md)** — WorldAnchor 世界空间 UI 叠加层
- **[lua-workshop-map-tacks.md](lua-workshop-map-tacks.md)** — 地图钉+相邻加成计算（Modifier/Rqmt遍历）
- **[lua-workshop-map-search.md](lua-workshop-map-search.md)** — 地图搜索扩展（帧分片+自动补全+高亮）
- **[lua-workshop-quick-deals.md](lua-workshop-quick-deals.md)** — 快速交易系统（AI自动交易+异步队列）

## 工坊 — 领袖 UI
- **[lua-workshop-leader-launchbar-button.md](lua-workshop-leader-launchbar-button.md)** — LaunchBar 按钮 + 动态尺寸 + 领袖条件注入
- **[lua-workshop-leader-custom-dialog.md](lua-workshop-leader-custom-dialog.md)** — 自定义游戏内弹出对话框
- **[lua-workshop-leader-worldtracker-inject.md](lua-workshop-leader-worldtracker-inject.md)** — WorldTracker PanelStack 注入
- **[lua-workshop-leader-unit-panel-injection.md](lua-workshop-leader-unit-panel-injection.md)** — 单位面板注入（StandardActionsStack 四件套）
- **[lua-workshop-leader-unit-teleport-lens.md](lua-workshop-leader-unit-teleport-lens.md)** — 单位传送 + UILens 地块高亮
- **[lua-workshop-leader-unit-resource-actions.md](lua-workshop-leader-unit-resource-actions.md)** — 动态 InstanceManager 资源操作面板
- **[lua-workshop-leader-fullscreen-popup.md](lua-workshop-leader-fullscreen-popup.md)** — LaunchBar 入口全屏弹窗
- **[lua-workshop-leader-tracker-cooldown-badge.md](lua-workshop-leader-tracker-cooldown-badge.md)** — TopPanel 冷却状态徽章
- **[lua-workshop-leader-tracker-production-distribution.md](lua-workshop-leader-tracker-production-distribution.md)** — CityPanel 生产力分配追踪器
- **[lua-workshop-leader-tracker-expandable-spender.md](lua-workshop-leader-tracker-expandable-spender.md)** — 可展开/收起多按钮资源消费面板
- **[lua-workshop-leader-popup-dialog-variants.md](lua-workshop-leader-popup-dialog-variants.md)** — PopupDialog 变体（多按钮/YesNo）
- **[lua-workshop-leader-popup-citypanel-expandable.md](lua-workshop-leader-popup-citypanel-expandable.md)** — CityPanel 可展开子按钮组
- **[lua-workshop-leader-popup-interfacemode-plot.md](lua-workshop-leader-popup-interfacemode-plot.md)** — InterfaceMode 地块选择 + UILens
- **[lua-workshop-leader-popup-pulldown-selector.md](lua-workshop-leader-popup-pulldown-selector.md)** — PullDown 选择器（图标嵌入+Modal）
- **[lua-workshop-leader-popup-movie-player.md](lua-workshop-leader-popup-movie-player.md)** — BIK 视频播放器
- **[lua-workshop-leader-event-choice-framework.md](lua-workshop-leader-event-choice-framework.md)** — 事件/选择表驱动框架

## 工坊 — 游戏机制
- **[lua-workshop-economy-transnational.md](lua-workshop-economy-transnational.md)** — 跨国公司系统
- **[lua-workshop-economy-investor-tycoon.md](lua-workshop-economy-investor-tycoon.md)** — 投资者/大亨经济单位系统（MonopolyPlus）
- **[lua-workshop-economy-station-trade.md](lua-workshop-economy-station-trade.md)** — 车站与国内贸易系统（MonopolyPlus）
- **[lua-workshop-economy-warehouse.md](lua-workshop-economy-warehouse.md)** — 仓库/集装箱（Lua+Property+SQL联动）
- **[lua-workshop-economy-loan-finance.md](lua-workshop-economy-loan-finance.md)** — 贷款金融系统
- **[lua-workshop-economy-dynamic-modifiers.md](lua-workshop-economy-dynamic-modifiers.md)** — 动态Modifier批量生成（INSERT-SELECT拼接）
- **[lua-workshop-economy-monopoly-categories.md](lua-workshop-economy-monopoly-categories.md)** — 垄断资源类别重设计
- **[lua-workshop-economy-products.md](lua-workshop-economy-products.md)** — 产品巨作系统
- **[lua-workshop-combat-auto-attack.md](lua-workshop-combat-auto-attack.md)** — BFS环形扫描自动攻击
- **[lua-workshop-combat-morale.md](lua-workshop-combat-morale.md)** — 士气系统（Property+战斗力映射+围城）
- **[lua-workshop-combat-golden-age.md](lua-workshop-combat-golden-age.md)** — 黄金时代叉积生成时代BUFF/DEBUFF
- **[lua-workshop-city-suzerain.md](lua-workshop-city-suzerain.md)** — 城邦宗主国Modifier注入
- **[lua-workshop-city-movable.md](lua-workshop-city-movable.md)** — 可移动城市（销毁-重建-恢复）
- **[lua-workshop-city-plant-breed.md](lua-workshop-city-plant-breed.md)** — 种植/育种资源系统
- **[lua-workshop-map-ocean-features.md](lua-workshop-map-ocean-features.md)** — 海洋扩展（高斯卷积+海藻+大陆划分）
- **[lua-workshop-map-river-generation.md](lua-workshop-map-river-generation.md)** — 真实河流地形雕刻
- **[lua-workshop-map-starting-plots.md](lua-workshop-map-starting-plots.md)** — 起始平衡（出生偏好+产出评估+回退）
- **[lua-workshop-resource-introduction.md](lua-workshop-resource-introduction.md)** — 资源引进（自定义平民单位引入/删除资源）
- **[lua-workshop-vassal-system.md](lua-workshop-vassal-system.md)** — 朝贡/附庸体系
- **[lua-workshop-modular-adjacency.md](lua-workshop-modular-adjacency.md)** — 模块化相邻加成框架（SQL表定义+Lua自动处理）
- **[lua-workshop-collectibles.md](lua-workshop-collectibles.md)** — 收藏品系统（稀有度级联+双阶段Modifier）
- **[lua-workshop-binary-yield.md](lua-workshop-binary-yield.md)** — 二进制折叠产出入体系
- **[lua-workshop-misc-resource-accumulation.md](lua-workshop-misc-resource-accumulation.md)** — 幸福值积累/阈值触发
- **[lua-workshop-misc-virtual-buildings.md](lua-workshop-misc-virtual-buildings.md)** — 虚拟建筑效果系统
- **[lua-workshop-misc-overflow-calculator.md](lua-workshop-misc-overflow-calculator.md)** — 科技/文化溢出计算器
- **[lua-workshop-misc-gameproperty-state.md](lua-workshop-misc-gameproperty-state.md)** — GameProperty 跨端状态持久化
- **[lua-workshop-misc-custom-sql-tables.md](lua-workshop-misc-custom-sql-tables.md)** — 自定义SQL表驱动逻辑
- **[lua-workshop-misc-map-limits.md](lua-workshop-misc-map-limits.md)** — 地图规模扩展
- **[lua-workshop-ui-gp-comm.md](lua-workshop-ui-gp-comm.md)** — UI-GP通信模式总结（跨Mod）
- **[lua-workshop-combat-report-text.md](lua-workshop-combat-report-text.md)** — 纯XML文本替换战斗报告
- **[lua-workshop-combat-preview-enhance.md](lua-workshop-combat-preview-enhance.md)** — 战斗预览增强（伤害范围+三血条+修饰符轮播）
