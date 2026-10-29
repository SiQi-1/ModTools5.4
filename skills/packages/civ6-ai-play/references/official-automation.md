# 文明6 官方自动化测试与 Debug 面板（结构 + 可借鉴点 + 运行实测补充）

> 本文件已按主题拆成分册（每册 ≤32KB），保留为索引：按触发条件选读对应分册，不要整篇读取。

> 总览：> **依据**：§1–§11 只依据游戏安装目录内的官方文件（本地安装版本；行号与数量随版本变化，引用时以实际文件复核），未引用任何第三方仓库、论坛或 Mod 代码；**§13 是 2026-10-26 的真机运行实测补充**。 > **证据等级**：【静态核对】= 官方文件中直接可见、行号已逐条核对；【待运行时验证】= 依赖引擎内部行为或命令行参数，文件中看不到，需实测；【推断】= 由多处官方用法交叉推出；【运行实测 2026-10-26】= 真机 Tuner 通道实测（换版本/Mod 组合需重测）。 > 路径前缀 `GAME_ROOT` = 游戏安装根目录（由 [environment.

## 分册清单

| 分册 | 覆盖内容 | 触发条件 |
|---|---|---|
| [official-automation-overview-lifecycle.md](official-automation-overview-lifecycle.md) | 1. 框架总览：一个 `Tests` 表 + 一个引擎驱动器、1.1 数据契约（测试套 = 全局 `Tests` 表）、2. 脚本是怎么被加载 / 启动的、2.1 加载：引擎按"文件名列表"加载，没有 XML 注册表、2.2 启动：等"主菜单就绪"事件、3. Automation 参数容器 API（跨上下文唯一的可靠状态）、4. 完整生命周期（逐事件） | 了解官方自动化框架、加载方式、参数容器与生命周期时 |
| [official-automation-builtin-tests.md](official-automation-builtin-tests.md) | 5. 内置测试项逐个看、5.1 PlayGame（最重要的模板）、5.2 LoadGame、5.3 HostGame（联机 + autoplay）、5.4 JoinGame（客户端）、5.5 公共参数注入：ApplyCommonNewGameParametersToConfiguration、6. PlayGame 支持的 `CurrentTest` 参数全表、7. autoplay 用法（"不写 AI 也能推进对局"）、7.1 启动 / 停止、7.2 回合数语义有矛盾，需实测、7.3 事件、7.4 防崩溃开关、7.5 极简模板：DailySmokeTest（冒烟测试） | 查内置测试项、CurrentTest 参数、autoplay 用法时 |
| [official-automation-debug-panels.md](official-automation-debug-panels.md) | 8. 其余 Automation_*.lua 脚本职责、9. 能借鉴到"AI 控制游戏 / Mod 测试"的点、9.1 直接可复用的设计、9.2 不要照抄的地方、9.3 "Mod 自动测试"最小可行流程（由官方拼装）、10. Debug/*.ltp 面板全清单（数量随安装版本变化）、10.1 面板元数据、10.2 按能力分类（做验证/取证时按需挑面板）、10.3 两个特别有用的面板、11. .ltp 文件结构（自己写面板时照这个来） | 查其余 Automation 脚本、可借鉴点、Debug 面板与 ltp 结构时 |
| [official-automation-verify.md](official-automation-verify.md) | 12. 待运行时验证清单、13. 运行实测补充（2026-10-26）：不走官方 Automation 的外部驱动路径、13.1 结论、13.2 与官方 Automation 的机制对照、13.3 外部驱动必须自己补的三件事、13.4 待验证（外部路径特有） | 核对待运行时验证清单与实测补充时 |

## 使用建议

先按任务关键词在上表定位分册，只读命中分册；参数表在分册内，不要一次加载全部。原文件的目录/分组索引已由本表替代。
