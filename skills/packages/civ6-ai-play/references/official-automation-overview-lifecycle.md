# 文明6 官方自动化测试与 Debug 面板（结构 + 可借鉴点 + 运行实测补充） — 框架/生命周期

> 分册：由 [official-automation.md](official-automation.md) 按主题拆出；覆盖 1. 框架总览：一个 `Tests` 表 + 一个引擎驱动器、1.1 数据契约（测试套 = 全局 `Tests` 表）、2. 脚本是怎么被加载 / 启动的、2.1 加载：引擎按"文件名列表"加载，没有 XML 注册表、2.2 启动：等"主菜单就绪"事件、3. Automation 参数容器 API（跨上下文唯一的可靠状态）、4. 完整生命周期（逐事件）。触发：了解官方自动化框架、加载方式、参数容器与生命周期时。

## 1. 框架总览：一个 `Tests` 表 + 一个引擎驱动器

官方自动化不是独立程序，而是**挂在 UI 层的一组 Lua 脚本**。分工只有两块：

| 组成 | 文件 | 行数 | 职责 |
| --- | --- | --- | --- |
| 引擎侧 Automation 系统 | （C++，无 Lua 源码） | — | 提供 `Automation` 全局对象、派发 `LuaEvents.Automation*` 事件、按字符串加载脚本、控制进程退出 |
| 测试驱动器（通用框架） | `Base/Assets/UI/Automation/Automation_StandardTestSupport.lua` | 318 | 监听引擎事件 → 按 `Tests` 表回调具体测试；管理测次索引与参数容器 |
| 具体测试套 | `Automation_StandardTests.lua`（873 行）、`Automation_DailySmokeTest.lua`（368 行） | — | 定义 `Tests["PlayGame"]` 等条目，自己写 Run/Stop |
| 专项脚本 | `Automation_ObserverCamera.lua`（718）、`Automation_BenchmarkCamera.lua`（5.3K）、`Automation_BenchmarkCamera_Capitals.lua`、`Automation_Profile.lua`（261）、`Automation_NarrationManager.lua` + `Automation_NarrationPopup.lua/.xml` | — | 观察者运镜、基准相机、资产分析、旁白录音 |

### 1.1 数据契约（测试套 = 全局 `Tests` 表）

框架约定（原注释见 `Automation_StandardTestSupport.lua:3-11`）【静态核对】：

- 顶层键 = 测试名，值 = 一张表；
- 每张测试表**支持**以下四个回调（都是可选，但 `Run` 实际必填）：

| 回调 | 何时触发 | 来源 |
| --- | --- | --- |
| `Run` | 轮到本测试时（在**前端/主菜单**或任何当前状态调用） | `Automation_StandardTestSupport.lua:195-209` |
| `PostGameInitialization(bWasLoaded)` | 对局初始化完成但地形/UI 尚未就绪（注释 "or loaded"） | 同上 `:241-250`；注释 `Automation_StandardTests.lua:313-316` |
| `GameStarted()` | 对局真正开始、能看到地图 | `Automation_StandardTestSupport.lua:228-237`；注释 `Automation_StandardTests.lua:340-341` |
| `Stop()` | 本测试结束（**无论成功失败都会调用**，用来清理） | `Automation_StandardTestSupport.lua:215-224` |

`Tests` 是**全局变量**且由测试套自己声明：`Automation_StandardTests.lua:9` `Tests = {};`；`Automation_DailySmokeTest.lua:6` 同样 `Tests = {};`【静态核对】。

---

## 2. 脚本是怎么被加载 / 启动的

### 2.1 加载：引擎按"文件名列表"加载，没有 XML 注册表

全仓库检索 `Automation_StandardTest`（Lua/XML 配置）**没有任何注册条目**；唯一一处把脚本名当参数传给引擎的地方是主菜单的基准测试入口 【静态核对】：

```lua
-- Base/Assets/UI/FrontEnd/MainMenu.lua:293-295
function OnExp2GraphicsBenchmark()
	Benchmark.RunExp2GraphicsBenchmark("XP2Benchmark.Civ6Save", SaveDirectories.BENCHMARK,
	    "Automation_StandardTests.lua; Automation_BenchmarkCamera_Capitals.lua");
end
```
→ 第三参是**分号分隔的自动化脚本文件名列表**，由引擎加载并在前台/对局各阶段调用。同族的还有 `Benchmark.RunGraphicsBenchmark`（`:290`）、`Benchmark.RunAIBenchmark`（`:298`）、`Benchmark.RunExp2AIBenchmark`（`:302`）【静态核对】。
【待运行时验证】普通（非基准）自动化运行的启动方式：官方测试用 `Automation.GetStartupParameter` 读参数，说明引擎接受启动参数（形如 `RunTests=...`），但**具体命令行开关不在安装目录的任何 Lua/XML 里**（可能在 exe 参数或开发版工具链中）。可先看 `Automation_StandardTestSupport.lua:143-190` 的参数读取逻辑反推。

> **2026-10-26 运行实测补充**：已确认存在一条**不依赖那个未知启动开关**的外部驱动路径 —— 通过 FireTuner 通道把 Lua 注入前端状态（state 30 / `FrontEnd`）即可完成"建局 → 进局"的等效流程。协议与可复制的 Lua 见 [lua-api.md](lua-api.md) §10，机制对照见本文件 **§13**。官方 `RunTests` 开关本身仍未确认。

脚本之间用 `include` 组合 【静态核对】：
- `Automation_StandardTests.lua:4` `include("LobbyTypes");` → 引入 `Base/Assets/UI/FrontEnd/Multiplayer/LobbyTypes.lua`（提供 `MPLobbyTypes` 与三个映射函数，见 `LobbyTypes.lua:4-66`）
- `Automation_StandardTests.lua:843` / `Automation_DailySmokeTest.lua:338` `include ("Automation_StandardTestSupport")` → 引入驱动器

### 2.2 启动：等"主菜单就绪"事件

驱动器只在自己被 include 后注册监听（`Automation_StandardTestSupport.lua:301-317`）【静态核对】：

```lua
function OnAutomationMainMenuStarted()
	local bStarted = Automation.GetLocalParameter("AutomationStarted", false);
	if (not bStarted) then
		Automation.SetLocalParameter("AutomationStarted", true);
		LuaEvents.AutomationStart();             -- 第一次：开始跑第一项
	else
		LuaEvents.AutomationRunTest("Restart");  -- 之后每次回主菜单：重启当前项
	end
end
LuaEvents.AutomationMainMenuStarted.Add( OnAutomationMainMenuStarted );
```
要点：**"回到主菜单"是测试之间的天然分隔点**，驱动器用 `AutomationStarted` 本地参数防止重复启动（`:305-309`）【静态核对】。

---

## 3. Automation 参数容器 API（跨上下文唯一的可靠状态）

全套 API（本机官方脚本中观测到的，非穷举）【静态核对】：

| 调用 | 作用域 | 说明 | 来源 |
| --- | --- | --- | --- |
| `Automation.GetStartupParameter(name)` | 启动级 | 读取启动参数；`RunTests` 就是一个数组 | `Automation_StandardTestSupport.lua:145`、`:172` |
| `Automation.GetSetParameter(setName, key [, default])` | 参数集（引擎侧） | 读某参数集的键；**跨 Lua 上下文重建仍保留** | `:36`、`Automation_StandardTests.lua:74` 等大量 |
| `Automation.SetSetParameter(setName, key, value)` | 参数集 | 写；用于"记住已启动过/剩余回合" | `Automation_StandardTests.lua:394`、`:799`、`:826` |
| `Automation.GetParameterSet(setName)` | 参数集 | 取整张表（可遍历任意自定义键） | `Automation_StandardTests.lua:223` |
| `Automation.SetParameterSet(setName, table)` | 参数集 | 整体写入（当前测试的参数表） | `Automation_StandardTestSupport.lua:183` |
| `Automation.ClearParameterSet(setName)` | 参数集 | 清空 | `:181` |
| `Automation.GetLocalParameter(key [, default])` | 本机局部 | 存"本进程内的测试进度"，如 `TestIndex` | `:148`、`:175`、`:278` |
| `Automation.SetLocalParameter(key, value)` | 本机局部 | 如 `QuitApp` / `TestIndex` / `AutomationStarted` | `:88`、`:280`、`:308` |
| `Automation.Log(msg)` / `Automation.LogDivider()` | 日志 | 写自动化日志 | `Automation_StandardTests.lua:18`；`Automation_StandardTestSupport.lua:200` |
| `Automation.SendTestComplete()` | 流程 | **唯一的"本测试完成"信号**（注释明确：不要直接发 `LuaEvents.AutomationTestComplete`） | `Automation_StandardTests.lua:17-19` |
| `Automation.GenerateSaveName()` / `GetLastGeneratedSaveName()` | 存档 | 生成/取回自动存档名 | `Automation_StandardTests.lua:28`、`:408` |
| `Automation.SetActive(bool)` / `IsActive()` | 开关 | 关闭自动化（`Tests["End"]` 就只做这件事） | `Automation_StandardTestSupport.lua:138`；`Debug/Autoplay.ltp:29` |
| `Automation.Pause(bool)` | 暂停 | `Tests["PauseGame"]` 用 | `Automation_StandardTestSupport.lua:125` |

三套容器的作用域差异（据官方用法归纳）【推断】：
- **Startup**：启动时给一次，只读（`RunTests` 等）；
- **Set**（`CurrentTest`）：跨上下文、跨对局、跨读档都保留 → **放"当前测试的全部参数 + 进度记忆"**；
- **Local**：本机进程内、不跨对局 → 放 `TestIndex`、`QuitApp`、`AutomationStarted`。

> 这一条正是 `Automation_StandardTestSupport.lua:9-11` 注释的原因：Lua 局部变量会随上下文重建丢失，而 Set/Local 容器在 C++ 侧。

---

## 4. 完整生命周期（逐事件）

把驱动器与测试套的调用串起来【静态核对，来源见每行】：

```
引擎加载脚本
   └─ include("Automation_StandardTestSupport")            -- StandardTests:843
        └─ 注册 5 个 LuaEvents 监听                         -- Support:211/224/237/250/268/287/297/317

LuaEvents.AutomationMainMenuStarted                        -- 主菜单就绪
   └─ OnAutomationMainMenuStarted                          -- Support:301
        ├─ 首次: LuaEvents.AutomationStart()               --   :309
        └─ 之后: LuaEvents.AutomationRunTest("Restart")    --   :312

LuaEvents.AutomationStart → OnAutomationStart → LuaEvents.AutomationRunTest   -- Support:291-297
LuaEvents.AutomationRunTest → OnAutomationRunTest(option)                     -- Support:195
   ├─ StoreCurrentTestParameters()      -- 把本次测试的参数表写进 CurrentTest -- :201
   ├─ handler.Run()                     -- 进入具体测试                        -- :204
   └─ 若没有 handler: LuaEvents.AutomationComplete()                          -- :206

（测试自己 Network.HostGame / LoadGame / JoinGame …）

LuaEvents.AutomationPostGameInitialization(bWasLoad) → handler.PostGameInitialization()  -- Support:241
LuaEvents.AutomationGameStarted                      → handler.GameStarted()             -- Support:228

（测试自己决定何时完成 → Automation.SendTestComplete()）

LuaEvents.AutomationTestComplete → OnAutomationTestComplete                  -- Support:272
   ├─ LuaEvents.AutomationStopTest()   → handler.Stop()                      -- :275 / :215
   ├─ TestIndex = TestIndex + 1                                             -- :278-280
   └─ LuaEvents.AutomationRunTest()    → 跑下一项                            -- :283

（RunTests 列表跑完）
OnAutomationRunTest 发现没有 handler → LuaEvents.AutomationComplete          -- :206
LuaEvents.AutomationComplete → OnAutomationComplete                          -- Support:254
   ├─ Automation.SetActive(false)                                            -- :255
   ├─ 若 LocalParameter("QuitApp") == true → Events.UserConfirmedClose()     -- :257-259
   └─ 否则若不在前端 → Events.ExitToMainMenu()                               -- :261-263
```
**关键设计（非常值得借鉴）**：

1. **测次索引存在引擎侧**（`TestIndex`，`Support:278-280`），因为 Lua 上下文会被重建。
2. **Stop 一定先于下一项的 Run**（`Support:274-283`），保证清理。
3. **"完成"由测试自己声明**（`SendTestComplete`），框架不猜。
4. **失败也走 `SendTestComplete`**：官方在 `LoadGame` 里 `Network.LoadGame` 返回 false 时直接 `SendTestComplete()`（`Automation_StandardTests.lua:418-421`），即"失败 = 提前完成"，由外层统计。
5. **重入保护**：`LoadGame` 用 `HasLaunched` 参数防死循环（`:388-394`）。

---

