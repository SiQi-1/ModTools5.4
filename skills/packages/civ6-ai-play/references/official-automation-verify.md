# 文明6 官方自动化测试与 Debug 面板（结构 + 可借鉴点 + 运行实测补充） — 待验证/实测

> 分册：由 [official-automation.md](official-automation.md) 按主题拆出；覆盖 12. 待运行时验证清单、13. 运行实测补充（2026-10-26）：不走官方 Automation 的外部驱动路径、13.1 结论、13.2 与官方 Automation 的机制对照、13.3 外部驱动必须自己补的三件事、13.4 待验证（外部路径特有）。触发：核对待运行时验证清单与实测补充时。

## 12. 待运行时验证清单

1. **普通自动化的启动方式**：`RunTests` 启动参数由谁传（命令行开关/开发工具）、脚本名列表是否与 `Benchmark.RunExp2GraphicsBenchmark` 同一机制。
   —— **2026-10-26 部分回答**：绕开该机制的 FireTuner 注入路径已实测跑通（§13）；`RunTests` 本身的传参方式仍未确认。
2. `AutoplayManager.SetTurns(0)` vs `-1` 的真实语义（§7.2 官方注释自相矛盾）。
3. `LuaEvents.AutomationMainMenuStarted` 的触发时机（是否每次回主菜单都触发；会不会与 `AutomationStarted` 冲突）。
4. `Automation.SendTestComplete()` 到 `LuaEvents.AutomationTestComplete` 之间 "safe time" 的延迟窗口（注释 `StandardTests.lua:17`）。
5. `PostGameInitialization` 与 `GameStarted` 的先后，及一次对局中是否可能多次触发（读档/重同步时）。
6. `Events.MultiplayerGameLastPlayer` 在单人局的触发条件（`StandardTests.lua:577`）。
7. `Debug/*.ltp` 中声明 `GameCore_Tuner` 的面板，在对局正常进行时是否也能打开（还是必须暂停/特定 Tuner 态）。
8. `Automation_NarrationManager.lua` 的参数命名规则（`NarrationEvent_<事件名>`）能否直接复用到"事件录制"。
9. `Benchmark.*` 的具体实现（只有调用点，无 Lua 实现）→ 引擎侧行为未知。
10. `Automation_Profile.lua` 写 C:\Temp 的路径是否可改（当前硬编码，`Profile.lua:3`）。

---

## 13. 运行实测补充（2026-10-26）：不走官方 Automation 的外部驱动路径

> 本节是**真机运行实测**，与 §1–§11 的官方文件静态结论分属两类证据，引用时请保留【运行实测 2026-10-26】标注。

### 13.1 结论

官方 Automation 依赖引擎启动参数（§2.1 未确认）。实测确认了**另一条可用路径**：

> **FireTuner 通道（`127.0.0.1:4318`）→ 注入前端状态（state 30 / `FrontEnd`）→ 执行建局 Lua → 进局后切到 `GameCore_Tuner` 继续操作。**

协议、状态表、可复制的新局 Lua、枚举数值、进局信号与断连坑，全部记在 [lua-api.md](lua-api.md) 的 **§10**（同一份实测只维护一处，避免两处漂移）。

### 13.2 与官方 Automation 的机制对照

| 官方机制（静态来源） | 外部驱动替代（运行实测） | 现状 |
| --- | --- | --- |
| `Automation.GetSetParameter("CurrentTest", ...)` 传参（Support:36 等） | 外部脚本直接生成 Lua 字面量 | 可用，但参数化程度更低 |
| `Tests["PlayGame"].Run` 建局（StandardTests:267-310） | state 30 执行建局 Lua（lua-api §10.3） | **已实测进局成功** |
| `PostGameInitialization` / `GameStarted` 分层（Support:241 / :228） | 观测 `LoadScreen: OnLoadGameViewStateDone`（lua-api §10.5） | 可用，粒度更粗 |
| `AutoplayManager` 快进（StandardTests:326-335） | 同一套 API，进局后从 `GameCore_Tuner` 调 | 待实测确认该调用时机等价 |
| `Automation.SendTestComplete()` + 外层统计 | 外部脚本自己判定 + 扫日志 | 需自建 |
| `RunTests` 启动开关（未知） | 不需要 | 已绕开 |

### 13.3 外部驱动必须自己补的三件事

官方框架里由 `Automation` 系统兜底的东西，外部路径没有，必须自己实现：

1. **状态管理**：每次执行前先 `LSQ:` 取状态表、**按名字**定位 state（不要硬编码编号 —— 进局后编号会变，实测 `GameCore_Tuner` 进局后是 3、主菜单前端注入态是 30）。
2. **清理**：结束前 `AutoplayManager.SetActive(false)`、恢复用户配置、回主菜单 —— 官方靠 `Stop()` 保证（StandardTests:360-371）。
3. **连接存活**：加载中/领袖介绍未跳过时 4318 可能暂不可用；等 `OnLoadGameViewStateDone` 并 Esc 跳过介绍后重试连接即可（lua-api §10.6 已按最终实测更正）。长会话建议常驻桥，短命令可每次重连。

### 13.4 待验证（外部路径特有）

1. 已部分回答：加载完成 + 跳过介绍后可重连（lua-api §10.6）；「介绍界面是否为唯一阻塞条件」仍待多版本验证。
2. 进局后从 `GameCore_Tuner` 调 `AutoplayManager` 是否与官方在 `PostGameInitialization` 里的调用等价（时序/生效条件）。
3. `PlayerSetupLogic.lua:89` 的 `BroadcastPlayerInfo` 在纯单机场景是否严格必需，还是本次实测的偶然结果。
4. `FrontEnd` 这个名字在所有版本/语言下是否稳定存在（编号 30 已确认会随上下文变化，名字稳定性待多版本验证）。

