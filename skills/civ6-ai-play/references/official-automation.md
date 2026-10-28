# 文明6 官方自动化测试与 Debug 面板（结构 + 可借鉴点 + 运行实测补充）

> **依据**：§1–§11 只依据游戏安装目录内的官方文件（本地安装版本；行号与数量随版本变化，引用时以实际文件复核），未引用任何第三方仓库、论坛或 Mod 代码；**§13 是 2026-10-26 的真机运行实测补充**。
> **证据等级**：【静态核对】= 官方文件中直接可见、行号已逐条核对；【待运行时验证】= 依赖引擎内部行为或命令行参数，文件中看不到，需实测；【推断】= 由多处官方用法交叉推出；【运行实测 2026-10-26】= 真机 Tuner 通道实测（换版本/Mod 组合需重测）。
> 路径前缀 `GAME_ROOT` = 游戏安装根目录（由 [environment.md](environment.md) 的「路径探测」解析；不同机器路径不同）；文中 `Base/...`、`Debug/...` 均相对于它。

---

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

## 5. 内置测试项逐个看

`Tests` 里共有 **8 项**（4 个在 `Automation_StandardTests.lua`，另 4 个小项在 Support）【静态核对】：

| 测试名 | 文件:行 | 作用 |
| --- | --- | --- |
| `PlayGame` | StandardTests.lua:264-371 | 前端新建单机局 → autoplay N 回合 → 存档 → 完成 |
| `LoadGame` | StandardTests.lua:376-481 | 读上一项的存档 → autoplay → 完成 |
| `HostGame` | StandardTests.lua:486-574 | 主持联机局（可 autoplay）→ 最后一名玩家时完成 |
| `JoinGame` | StandardTests.lua:662-744 | 加入联机局 → 倒计回合 → 完成 |
| `QuitApp` | StandardTestSupport.lua:82-92 | 置 `QuitApp` 标志 → 完成 → 外层关进程 |
| `QuitGame` | StandardTestSupport.lua:97-110 | 回主菜单 → 完成 |
| `PauseGame` | StandardTestSupport.lua:115-127 | `Automation.Pause(true)` |
| `End` | StandardTestSupport.lua:133-140 | `Automation.SetActive(false)`（就地停自动化，不退出） |

### 5.1 PlayGame（最重要的模板）

四段式：

```lua
-- (1) Run：必须在主菜单，否则先退出对局（StandardTests.lua:267-274）
Tests["PlayGame"].Run = function()
	if (not UI.IsInFrontEnd()) then Events.ExitToMainMenu(); return; end
	GameConfiguration.SetToDefaults();                       -- :277
	-- 可选：读一份已存的游戏配置（SaveFileTypes.GAME_CONFIGURATION）
	local configurationFile = Automation.GetSetParameter("CurrentTest", "LoadConfiguration");
	...
	ApplyCommonNewGameParametersToConfiguration();           -- :305 统一套参数
	ReadUserConfigOptions();                                 -- :307 快速移动/战斗
	Network.HostGame(ServerType.SERVER_TYPE_NONE);           -- :309
end

-- (2) PostGameInitialization：对局初始化完、地形还没生成
Tests["PlayGame"].PostGameInitialization = function(bWasLoaded)
	LogCurrentPlayers();                                     -- :318
	LuaEvents.AutoPlayEnd.Add( SharedGame_OnAutoPlayEnd );   -- :321 结束时要存档
	local turnCount = Automation.GetSetParameter("CurrentTest", "Turns");
	if turnCount ~= nil then                                 -- 没给 Turns = 不 autoplay
		local observeAs = GetCurrentTestObserver();
		AutoplayManager.SetTurns(turnCount);                 -- :330
		AutoplayManager.SetReturnAsPlayer(0);                -- :331
		AutoplayManager.SetObserveAsPlayer(observeAs);       -- :332
		AutoplayManager.SetActive(true);                     -- :334
	end
end

-- (3) GameStarted：能看到地图了
Tests["PlayGame"].GameStarted = function()
	if (Game.GetLocalPlayer() == PlayerTypes.NONE) then      -- :346 纯观察视角
		StartupObserverCamera(GetCurrentTestObserver());     -- :349
	else
		Automation.SendTestComplete();                       -- :353 有真人 = 测试目标达成
	end
end

-- (4) Stop：清理（一定会执行）
Tests["PlayGame"].Stop = function()
	LuaEvents.AutoPlayEnd.RemoveAll();                       -- :363
	Events.SaveComplete.Remove( SharedGame_OnSaveComplete ); -- :365
	AutoplayManager.SetActive(false);                        -- :367
	RestoreUserConfigOptions();                              -- :369
end
```
autoplay 结束后自动存档（`StandardTests.lua:24-38`）：

```lua
function SharedGame_OnAutoPlayEnd()
	Automation.Log("The autoplay manager has deactivated. (See autoplay.log) Saving game prior to completing current test. ");
	local saveGame = {};
	saveGame.Name = Automation.GenerateSaveName();
	saveGame.Location = SaveLocations.LOCAL_STORAGE;
	saveGame.Type = SaveTypes.SINGLE_PLAYER;
	saveGame.IsAutosave = false;
	saveGame.IsQuicksave = false;
	Network.SaveGame(saveGame);
	Events.SaveComplete.Add( SharedGame_OnSaveComplete );   -- 存档异步，等事件（:36-37）
end
function SharedGame_OnSaveComplete()                         -- :16-20
	Automation.SendTestComplete();
end
```
> 注意注释 `StandardTests.lua:25` 明确写了 **autoplay 的日志在 autoplay.log**（独立文件），这是排查"游戏为什么自己跑/不跑"的第一落点。

### 5.2 LoadGame

- `Run`（`:379-423`）：读 `SaveName` 参数，否则用 `Automation.GetLastGeneratedSaveName()`（`:404-409`）；`Network.LoadGame` 返回 false 就 `SendTestComplete`（`:417-421`）。
- `PostGameInitialization`（`:438-457`）：与 PlayGame 相同，但 autoplay 结束**不存档**，直接 `SendTestComplete()`（`LoadGame_OnAutoPlayEnd`，`:427-432`）。
- `Stop`（`:477-481`）：只恢复用户配置。

### 5.3 HostGame（联机 + autoplay）

```lua
-- Run（:489-507）：先判断跨平台
if (GetTestServerType() == ServerType.SERVER_TYPE_CROSSPLAY) then
	Events.CrossPlayLoginStateUpdated.Add(HostGame_OnCrossPlayLoginStateUpdated);
	Network.AttemptConnectionToCrossPlayLobbyService();     -- :501 先登录
	return;                                                  -- 登录回调里再继续
end
HostAutoplayGame();                                          -- :506

-- HostAutoplayGame（:593-655）
GameConfiguration.SetToDefaults();                            -- :595
-- 可选：读配置（Type = SaveTypes.NETWORK_MULTIPLAYER，:604）
ApplyCommonNewGameParametersToConfiguration();                -- :624
local gameName = Automation.GetSetParameter("CurrentTest", "GameName") or "autoplay";
GameConfiguration.SetValue("GAME_NAME", gameName);            -- :631 联机房间名（JoinGame 靠它找房）
ReadUserConfigOptions();                                      -- :633
local saveFileName = Automation.GetSetParameter("CurrentTest", "SaveFile");
if saveFileName ~= nil then Network.LoadGame(saveFileTable, GetTestServerType());  -- :648
else                        Network.HostGame(GetTestServerType());                 -- :651
end
Events.MultiplayerGameLastPlayer.Add( HostGame_OnMultiplayerGameLastPlayer );       -- :654
```
- 完成条件：成为最后一个玩家（`:577-584`，可用 `QuitOnLastPlayer` 关闭）或成为本地真人玩家（`:538-555`）。
- `GameStarted` 里必须**重新订阅** `Events.MultiplayerGameLastPlayer` —— 注释原话："The subscription in Run() is lost on game load. Resubscribe so it works while ingame."（`:542-543`）【静态核对】。

### 5.4 JoinGame（客户端）

流程最有参考价值的一点：**用"剩余回合数"做断线重连容忍** 【静态核对】：

```lua
-- JoinAutoplayGame（:821-837）
ReadUserConfigOptions();
local turnCount = Automation.GetSetParameter("CurrentTest", "Turns", DEFAULT_AUTOMATION_TURNS);
Automation.SetSetParameter("CurrentTest", "RemainingTurns", turnCount);   -- :826 缓存到引擎侧
Events.MultiplayerGameListUpdated.Add( JoinGame_OnGameListUpdated );      -- :828
Events.MultiplayerGameListComplete.Add( JoinGame_OnGameListComplete );    -- :829
Events.MultiplayerHostMigrated.Add( JoinGame_MultiplayerHostMigrated );   -- :830
Matchmaking.InitLobby(GetTestLobbyType());                                -- :833
Matchmaking.RefreshGameList();                                            -- :834

-- 在 GameListUpdated 里按房间名匹配后加入（:748-777）
local serverTable = Matchmaking.GetGameListEntry(idLobby);                 -- :758
local serverEntry = serverTable[1];                                       -- :760
if (serverEntry.serverName == gameName) then
	Network.JoinGame(serverEntry.serverID);                               -- :774
end

-- 每回合扣减（:793-801），因为"重连后要能知道还剩几回合"
function JoinGame_OnTurnEnd(iTurn)
	local remainingTurns = Automation.GetSetParameter("CurrentTest", "RemainingTurns", DEFAULT_AUTOMATION_TURNS);
	if (remainingTurns ~= nil and remainingTurns >= 0) then
		Automation.SetSetParameter("CurrentTest", "RemainingTurns", remainingTurns - 1);  -- :799
	end
end
```
`DEFAULT_AUTOMATION_TURNS = -1`（`StandardTests.lua:7`）表示"不限回合"，所以扣减前要先判 `>= 0`【静态核对】。

### 5.5 公共参数注入：ApplyCommonNewGameParametersToConfiguration

`StandardTests.lua:159-262` 是"外部参数 → 游戏配置"的完整映射器，**这段是整份官方脚本里最值得抄的一节**：

```lua
function ApplyCommonNewGameParametersToConfiguration()
	-- 逐项：RuleSet / MapScript / MapSize / 人机槽位 / 难度 / 速度 / 种子 / 起始时代 / 回合上限
	local ruleSet     = Automation.GetSetParameter("CurrentTest", "RuleSet");
	if ruleSet ~= nil then GameConfiguration.SetRuleSet(ruleSet); end            -- :161-164
	local mapScript   = Automation.GetSetParameter("CurrentTest", "MapScript");
	if mapScript ~= nil then MapConfiguration.SetScript(mapScript); UpdatePlayerCounts(); end  -- :167-171
	...
	ApplyHumanPlayersToConfiguration();                                          -- :181 必须在尺寸/脚本之后
	...
	-- 末尾：任意自定义键批量透传（Game.* / Map.*，'#' 前缀走 DB.MakeHash）
	for k,v in pairs(Automation.GetParameterSet("CurrentTest")) do               -- :229
		if (k:sub(1, #"Game") == "Game") then
			GameConfiguration.SetValue(k:sub(#"Game"+2), value);                 -- :243
		elseif (k:sub(1, #"Map") == "Map") then
			MapConfiguration.SetValue(k:sub(#"Map"+2), value);                   -- :257
		end
	end
end
```
> 这套"前缀路由 + # 哈希"的约定，等于给自动化开了一个**任意配置键的注入口**，而不必改 Lua。做外部 AI 驱动时可直接复用（例如传 Game.GAME_NAME=我的测试局、Map.RANDOM_SEED=12345）。

---

## 6. PlayGame 支持的 `CurrentTest` 参数全表

若某项缺省，行为见"缺省"列；行号均为 `Automation_StandardTests.lua`（除注明）【静态核对】。

| 参数 | 类型/取值 | 作用 | 行 |
| --- | --- | --- | --- |
| `RuleSet` | 字符串 | 规则集 | :161 |
| `MapScript` | 字符串 | 地图脚本 | :167 |
| `MapSize` | 字符串 | 地图尺寸 | :174 |
| `HumanPlayers` | 整数，0 = 全 AI | 真人槽位数；0 时把所有真人槽变 `SS_COMPUTER` | :122-156 |
| `Handicap` / `Difficulty` | 字符串 | 难度（`Difficulty` 是别名） | :184-189 |
| `GameSpeed` | 字符串 | 速度 | :193 |
| `MapSeed` | 整数 | `RANDOM_SEED` | :199 |
| `GameSeed` | 整数 | `GAME_SYNC_RANDOM_SEED` | :205 |
| `StartEra` | 字符串 | 起始时代 | :211 |
| `MaxTurns` | 整数 >= 1 | 分数胜利回合上限（**不是**测试回合数）+ `TurnLimitTypes.CUSTOM` | :217-221 |
| `LoadConfiguration` | 文件名 | 先读一份 `GAME_CONFIGURATION` 再套其余参数 | :280-303 |
| `ConfigurationDirectory` | 目录 | 上项的目录 | :294 |
| `Turns` | 整数；0 = 不限 | autoplay 回合数；**缺省 = 不 autoplay** | :326-335 |
| `ObserveAs` | OBSERVER / NONE / player id | 观察身份 | Support:36-49 |
| `QuickMovement` | bool/0/1 | 锁 `UserConfiguration("QuickMovement")` | :74-77 |
| `QuickCombat` | 同上 | 锁 QuickCombat | :79-82 |
| `MPLobbyType` | `MPLobbyTypes.*` 字符串 | 联机大厅类型（Host/Join/跨平台判定） | :89-110 |
| `GameName` | 字符串，缺省 autoplay | 联机房间名 | :626-631 |
| `SaveFile` | 文件名 | HostGame 改为读存档 | :635-648 |
| `SaveDirectory` | 目录 | 存档目录 | :642 |
| `SaveName` | 文件名 | LoadGame 指定存档（缺省用上次生成名） | :404-413 |
| `QuitOnLastPlayer` | 0/1，缺省 1 | 成为最后玩家是否算完成 | :578-583 |
| `QuitOnHostMigrate` | 0/1，缺省 1 | 主机迁移是否算完成 | :805-810 |
| `RemainingTurns` | 内部 | JoinGame 倒计用 | :696、:795-800 |
| `HasLaunched` | 内部 | LoadGame 防重入 | :388-394 |

---

## 7. autoplay 用法（"不写 AI 也能推进对局"）

### 7.1 启动 / 停止

```lua
AutoplayManager.SetTurns(turnCount);            -- 回合数（0 或 -1 的语义见 §7.2）
AutoplayManager.SetReturnAsPlayer(0);           -- 结束后把控制权交还哪个玩家
AutoplayManager.SetObserveAsPlayer(observeAs);  -- NONE / OBSERVER / player id
AutoplayManager.SetActive(true);                -- 开
...
AutoplayManager.SetActive(false);               -- 关（Stop 里必做，否则跑出测试范围）
```
完整 API 表见 `lua-api.md` §5.3；来源 `Automation_StandardTests.lua:326-335`、`:367` 与 `Debug/Autoplay.ltp:26-211`【静态核对】。

### 7.2 回合数语义有矛盾，需实测

- `Automation_StandardTests.lua:325` 注释："A turn count of 0 means no turn limit."
- `Debug/Autoplay.ltp:146-147`、`:157`：面板把 **-1** 映射为 "No limit"
- `Automation_StandardTests.lua:7`：`DEFAULT_AUTOMATION_TURNS = -1`

→ **【待运行时验证】** 0 与 -1 到底哪个是"不限"。安全写法：传入正数。

### 7.3 事件

| 事件 | 说明 | 来源 |
| --- | --- | --- |
| `LuaEvents.AutoPlayStart` | autoplay 开始；`ActionPanel` 用它把结束回合按钮换成"自动进行中"文案 | `Base/Assets/UI/ActionPanel.lua:1349`、`:1114-1117` |
| `LuaEvents.AutoPlayEnd` | autoplay 结束（本测试在这里存档） | `ActionPanel.lua:1350`；`Automation_StandardTests.lua:321`、`:517` |

两个事件注释都写着 "Raised by engine AutoPlay_Manager!"（`ActionPanel.lua:1349-1350`）→ **autoplay 是引擎功能，Lua 只是控制开关**【静态核对】。

### 7.4 防崩溃开关

`AutoplayManager.SetDisableAssertsForAutoplay(true)`（`Debug/Autoplay.ltp:63`）—— 长跑/无人值守时关掉断言。面板里所有 autoplay 控件都套 `if (not Automation.IsActive())` 保护（`:29`、`:48`、`:110`、`:155`、`:209`），说明**自动化期间禁止人工改 autoplay**。

### 7.5 极简模板：DailySmokeTest（冒烟测试）

`Automation_DailySmokeTest.lua` 是"最短可用自动化测试"：文件开头固定 `Turns = 5`（`:7`），PlayGame 里取 `Turns` 参数（缺省 **15**，`:190`），autoplay 15 回合后存档 → Stop 里直接关进程（`:219-233`）：

```lua
Tests["PlayGame"].Stop = function()
	LuaEvents.AutoPlayEnd.RemoveAll();
	Events.SaveComplete.Remove( PlayGame_OnSaveComplete );
	AutoplayManager.SetActive(false);
	RestoreUserConfigOptions();
	Automation.Log("\nSuccesfully played 15 turns\n");    -- :230
	Events.UserConfirmedClose();                          -- :231 冒烟测试跑完就关游戏
end
```
> 这就是"Mod 冒烟测试"的最小闭环：**开新局 → 跑 N 回合 → 存盘/退出**。判断 Mod 是否有加载期/运行时错误，靠的是日志而不是断言。

---

## 8. 其余 Automation_*.lua 脚本职责

| 脚本 | 行数 | 职责 / 关键点 |
| --- | --- | --- |
| `Automation_StandardTests.lua` | 873 | 主测试套（§5） |
| `Automation_StandardTestSupport.lua` | 318 | 驱动器 + 观察者相机 + 4 个小测试（§5 表） |
| `Automation_DailySmokeTest.lua` | 368 | 冒烟测试（§7.5） |
| `Automation_ObserverCamera.lua` | 718 | 自动观察者运镜：定义 7 种 `VisitActivity`（None/Unit/City/Plot/Combat/Wonder/District，`:42-48`）、按概率看首都（`:29-32`）、在 2D/战略/3D 视图间切换（`:16-27`）；监听 `CombatVisBegin/End`、`WonderCompleted`、`DistrictBuildProgressChanged` 等事件决定看什么 |
| `Automation_BenchmarkCamera.lua` / `_Capitals.lua` | ~5.3K | 基准测试专用相机：监听 `CityVisibilityChanged`（`:72`）、`PlayerTurnActivated`（`:92`）、`CombatVisBegin`（`:104`），配合 `BenchmarkStart/End`（`:136`、`:144`） |
| `Automation_Profile.lua` | 261 | 资产/性能剖析：把结果写到 C:\Temp\（`:3-4`），用 `AutoProfiler.SetFilePath/AddColumn`（`:6`、`:42`）、`AssetPreview.SpoofCityAt/SpoofDistrictBaseAt/ClearLandmarkSystem`（`:51`、`:77`、`:8`）批量伪造城市/区域做渲染统计 |
| `Automation_NarrationManager.lua` + `Automation_NarrationPopup.lua/.xml` | ~8K/15K | 旁白/播音测试：按事件（`WonderCompleted` `:216`、`DiplomacyDeclareWar` `:217`、`DiplomacyRelationshipChanged` `:219`、`PlayerEraChanged` `:221`、`CityOccupationChanged` `:223`、`SpyMissionUpdated` `:224`、`UnitActivate` `:225`）触发字幕；参数形如 `NarrationEvent_<事件名>`（`:20-21`） |

---

## 9. 能借鉴到"AI 控制游戏 / Mod 测试"的点

### 9.1 直接可复用的设计

| 官方做法 | 借鉴到 AI 驱动 | 依据 |
| --- | --- | --- |
| 状态放引擎侧参数容器，不放 Lua 局部变量 | 外部（AI）→ 游戏的状态同样应放 `Automation.SetSetParameter` 或自建 UI 脚本的持久容器；否则读档即丢 | `Automation_StandardTestSupport.lua:9-11` |
| 用 `Tests` 表 + Run/Stop/GameStarted/PostGameInitialization 四段划分流程 | 把"AI 任务"也拆成四段：准备/开局后/真正开始/清理，清理放 Stop 保证一定执行 | `Support:3-11`、`195-250` |
| 完成信号由执行方声明（`SendTestComplete`），失败 = 提前声明完成 | AI 任务也用"显式完成/失败"回报，别让监管方猜 | `StandardTests.lua:17-19`、`:418-421` |
| 防重入参数（`HasLaunched`） | AI 重试同一动作时用同样手法防死循环 | `StandardTests.lua:388-394` |
| 倒计剩余回合并缓存（`RemainingTurns`） | 长任务/重连场景同样要"进度落盘" | `StandardTests.lua:793-801`、`:821-827` |
| 事件订阅"换局后重订阅" | UI 脚本里所有 AI 事件监听都要在 `GameStarted`/读档后重挂 | `StandardTests.lua:542-543` |
| autoplay 当"快进" | Mod 测试可直接 `SetTurns(N)` + `SetActive(true)` 快进 N 回合，无需写任何 AI | §7 |
| 参数前缀路由（Game. / Map. + # 哈希） | 外部配置一键注入任意游戏配置键，免改 Lua | `StandardTests.lua:223-261` |
| 观察者相机 | AI 想"看"某个玩家时用 `PlayerManager.SetLocalObserverTo` + `UI.LookAtPlot` | `Support:55-78`；`Debug/Map.ltp:54-64` |

### 9.2 不要照抄的地方

1. **不要指望官方自动化帮你断言 Mod 正确性**：整套框架只有"完成/未完成"，没有断言、没有测试报告；失败靠日志（automation 日志 + autoplay.log，`StandardTests.lua:25`）。
2. **不要用 Lua 局部变量存游戏句柄**（如 `local pCity = CityManager.GetCity(...)`）跨调用持有 —— 上下文重建后失效（同上注释）。
3. **不要绕过 Request 直接改状态**：调试面板可以（`Debug/City.ltp:28` `ChangePopulation`、`Debug/Unit.ltp:50` `SetDamage`），但正式流程要走 `RequestOperation`/`RequestCommand`/`UI.RequestAction`，否则游戏事件不触发、UI 不同步（**推断 + 待运行时验证**）。
4. **不要在 `Automation.IsActive()` 或 autoplay 激活时下人工/外部指令**（面板自己都加了这层保护，`Debug/Autoplay.ltp:29` 等）。
5. **联机测试强依赖房间名**（`GAME_NAME`，`StandardTests.lua:626-631`），做外部驱动时要么沿用 autoplay 这个名字，要么自己保证两边一致。

### 9.3 "Mod 自动测试"最小可行流程（由官方拼装）

```
1. 备份配置（Mods.sqlite 等），启用待测 Mod
2. 启动游戏到主菜单
3. 触发 Automation（或自己的 UI 脚本）→ PlayGame 流程建局
4. SetTurns(N) + SetActive(true) 快进 N 回合
5. OnAutoPlayEnd → 存档（或直接退出）
6. 退出后扫描日志：automation 日志、autoplay.log、Database.log、Lua.log
7. 还原配置
```
---

## 10. Debug/*.ltp 面板全清单（数量随安装版本变化）

### 10.1 面板元数据

全部 `GAME_ROOT\Debug\*.ltp`（本次静态核对时 33 个，另有 `Civ6TunerPlugin.dll`、`DefaultPanels.xml`；数量随游戏版本/资料片/语言变化，以实际目录列举为准）。列含义：面板名（`<Name>` 在第 3 行）｜`<App>`（第 4 行，空 = 未指定）｜`<CompatibleStates>`（第 7 行，个别 12/17/18/19）｜`<ActionData>` 动作数｜总行数【静态核对】。

| 文件 | 面板名 | App | 兼容状态 | 动作数 | 行数 |
| --- | --- | --- | --- | --- | --- |
| `AI.ltp` | AI | Civ6 | InGame | 2 | 120 |
| `Asset Preview.ltp` | Asset Preview | Civ6 | TunerAssetPreviewPanel | 16 | 452 |
| `Audio.ltp` | Audio | (空) | InGame | 2 | 53 |
| `AutoProfiler.ltp` | AutoProfiler | Civ6 | TunerAssetPreviewPanel | 5 | 459 |
| `Autoplay.ltp` | Autoplay | Civ6 | GameCore_Tuner | 1 | 218 |
| `City.ltp` | City | Civ6 | TunerCityPanel | 24 | 1145 |
| `DebugOptions.ltp` | Debug Options | Civ6 | TunerAssetPreviewPanel | 31 | 293 |
| `Defeats.ltp` | Defeats | Civ6 | InGame | 0 | 127 |
| `Demo.ltp` | Demo | Civ6 | TunerDemoPanel | 2 | 538 |
| `Diplomacy.ltp` | Diplomacy | Civ6 | GameCore_Tuner, TunerDiplomacyPanel | 8 | 418 |
| `Forge.ltp` | Forge | Civ6 | FrontEnd, InGame, WorldBuilder | 3 | 535 |
| `Great People.ltp` | Great People | Civ5 | GameCore_Tuner | 0 | 55 |
| `Heroes.ltp` | Heroes | Civ6 | TunerHeroesPanel | 6 | 215 |
| `LandmarkVisualizer.ltp` | Landmark Visualizer | Civ6 | TunerAssetPreviewPanel | 4 | 531 |
| `Leader.ltp` | Leader | Civ6 | InGame | 0 | 65 |
| `Map.ltp` | Map | Civ5 | TunerMapPanel | 7 | 586 |
| `Modifiers.ltp` | Modifiers | Civ6 | GameCore_Tuner | 0 | 374 |
| `Network.ltp` | Network | (空) | MainMenu, InGame | 3 | 47 |
| `No Tool Tip.ltp` | No Tool Tip | Civ6 | PlotToolTip | 19 | 175 |
| `Notifications.ltp` | Notifications | Civ6 | GameCore_Tuner | 0 | 120 |
| `Player.ltp` | Player | Civ5 | GameCore_Tuner | 42 | 977 |
| `Players.ltp` | Players | Civ6 | InGame | 0 | 86 |
| `Random Events.ltp` | Random Events | Civ6 | TunerGameRandomEvents | 1 | 288 |
| `Requirements.ltp` | Requirements | Civ6 | GameCore_Tuner | 0 | 512 |
| `Rivers.ltp` | Rivers | Civ6 | GameCore_Tuner | 0 | 182 |
| `Routes.ltp` | Routes | Civ6 | InGame | 0 | 62 |
| `Storms.ltp` | Storms | Civ6 | GameCore_Tuner | 0 | 63 |
| `Territories.ltp` | Territories | Civ6 | InGame | 1 | 99 |
| `UI Units.ltp` | UI Units | Civ6 | InGame | 45 | 1004 |
| `Unit.ltp` | Unit | Civ6 | TunerUnitPanel | 12 | 519 |
| `Victories.ltp` | Victories | Civ6 | InGame | 0 | 189 |
| `WorldBuilder.ltp` | WorldBuilder | Civ5 | TunerWorldBuilderPanel | 7 | 910 |
| `WorldBuilderCity.ltp` | WorldBuilderCity | Civ6 | TunerWorldBuilderCityPanel | 0 | 394 |

另：`Debug/DefaultPanels.xml` 声明默认加载的面板（静态核对时为 7 个：Audio / City / Map / Player / Players / Unit / Great People；以实际文件为准）（`DefaultPanels.xml:3-9`）【静态核对】。

### 10.2 按能力分类（做验证/取证时按需挑面板）

**A. 改游戏核心状态（最适合验证 Mod 效果）**

| 面板 | 能做什么 | 代表动作 |
| --- | --- | --- |
| `Player.ltp`（42 动作，977 行） | 给资源/科技/文化/信仰/时代分/外交官/伟人点/战略资源/胜利点/核武；改金币/科研进度/得分；改随机种子 | `GetTreasury():ChangeGoldBalance(1000)`（:100）、`GetCulture():ChangeCurrentCulturalProgress(1000)`（:108）、`GetReligion():ChangeFaithBalance(5)`（:147）、`GetTechs():SetResearchProgress(...)`（:138）、`Game.GetEras():ChangePlayerEraScore(...,5)`（:307）、`GetDiplomacy():SetAtWarWith(...)`（:172-173） |
| `City.ltp`（24 动作，1145 行） | 加/减人口、加生产力、改驻军/外墙伤害、改忠诚、变自由城市、设首都、切掠夺、改地块归属/建筑/区域、任意城市属性 | `ChangePopulation(1)`（:28）、`GetBuildQueue():AddProgress(20)`（:107）、`GetDistricts():GetDistrictAtLocation(...):ChangeDamage(...)`（:120-122）、`SetProperty(key,val)`（:288）、`CityManager.SetAsCapital`（:314）、`Cities.DestroyCity`（:95） |
| `Unit.ltp`（12 动作） | 恢复移动/攻击、加经验、加/减伤害、击杀、编军团/军队 | `UnitManager.RestoreMovementToFormation`（:24）、`GetExperience():ChangeExperience(10)`（:37）、`UnitManager.Kill(pUnit,false)`（:51） |
| `Map.ltp`（7 动作） | 揭示/探索/撤销全图、切换本机观察对象、清空资源/地貌、放置各种要素 | `PlayersVisibility[...]:ChangeVisibilityCount(i,1)`（:27-29）、`PlayerManager.SetLocalObserverTo`（:54、:64）、`ResourceBuilder.SetResourceType(plot,-1)`（:93） |
| `Diplomacy.ltp`（8 动作） | 加/减外交评分、给金币、发 Kudos/Warning、结军事同盟、设宣布友谊 | `GetDiplomacy():SetHasDeclaredFriendship`（:138-139） |
| `Modifiers.ltp` / `Requirements.ltp` / `Defeats.ltp` / `Victories.ltp` | 只读诊断：列出所有 Modifier/Requirement 实例、是否满足、引用计数 —— **查 Mod 的 Modifier 为什么没生效就用这两个** | `GetObjectType/GetObjectName`（`Requirements.ltp:51-52`）、`Game.GetVictoryProgressForTeam`（`Victories.ltp:53`） |
| `Notifications.ltp` | 列出通知与"是否会阻塞回合" | `NotificationManager.GetList/Find`（:73、:77） |
| `Random Events.ltp` / `Storms.ltp` / `Rivers.ltp` / `Routes.ltp` / `Territories.ltp` | 天灾/风暴/河流/路线/领土诊断 | `Game.GetFalloutManager()`（`Random Events.ltp:221`） |
| `Great People.ltp` / `Heroes.ltp` | 伟人时间线 / 英雄 | `Game.GetGreatPeople():GetTimeline()`（`Great People.ltp:32`）、`Game.GetHeroesManager()`（`Heroes.ltp:75`） |

**B. 运行控制**

| 面板 | 能做什么 | 代表 |
| --- | --- | --- |
| `Autoplay.ltp` | autoplay 开关/回合数/返回玩家/观察玩家/关断言 | §7；:26-63、:100-211 |
| `Network.ltp` | 强制重同步/请求快照/触发同步测试 | :15、:23、:31 |
| `Audio.ltp` | 重载声音库、下一首、环境音量 | 见动作列表 |
| `DebugOptions.ltp`（31 动作） | 渲染调试：法线/金属度/AO/高光/线框/VFX/水/UI 开关、自由相机、4K 截图 | 见动作列表 |

**C. 表现/资产（与玩法无关）**

| 面板 | 用途 |
| --- | --- |
| `Asset Preview.ltp`（16 动作） | 资产预览：放置/移动/旋转/缩放、动画与状态切换 |
| `AutoProfiler.ltp` | 自动性能剖析（配合 `Automation_Profile.lua`） |
| `LandmarkVisualizer.ltp` | 批量放地标：区域/基础资产/建筑资产/文明/魅力等级组合 |
| `UI Units.ltp`（45 动作，1004 行） | UI 层单位模型：播各种动画（Idle/Death/Attack A-P-S/Defend/Run/Dodge/Hero 等）、重建编队、旋转、Spawn |
| `Demo.ltp` / `Leader.ltp` / `Forge.ltp` / `No Tool Tip.ltp` | 演示运镜、领袖动画、UI 控件检查（Forge 列所有 popup/控件属性）、无提示框模式（截图取证用） |
| `WorldBuilder.ltp` / `WorldBuilderCity.ltp` | 世界编辑器：初始化玩家（人/AI）、放置地形/资源/地貌/河流/悬崖/单位/城市 |

### 10.3 两个特别有用的面板

- **`DebugOptions.ltp` 里有 "Matt's 4K Screenshot Button"**（与 `No Tool Tip.ltp` 同名动作）→ 官方自带的截图取证入口【静态核对】。
- **`Forge.ltp`** 能列出所有 Popup/Modal 及其属性、是否可见/可用、是否吃鼠标 → **排查"弹窗挡住 AI 操作"** 的首选面板（其选择列表列头含 Popup ID / Priority / Flags、Modal ID）。

---

## 11. .ltp 文件结构（自己写面板时照这个来）

顶层 `<PanelData>`（XML），字段顺序固定【静态核对，以 `Debug/Autoplay.ltp` 为例】：

| 元素 | 行 | 说明 |
| --- | --- | --- |
| `<Name>` | 3 | 面板名（FireTuner 里显示） |
| `<App>` | 4 | Civ6 / Civ5 / 空（历史遗留，Map/Player/Great People/WorldBuilder 仍写 Civ5） |
| `<EnterAction>` / `<ExitAction>` | 5-6 | 面板打开/关闭时执行的 Lua（可用于进入/退出调试模式，见 `Debug/Map.ltp:5-16`） |
| `<CompatibleStates>` | 7 | 可用的游戏状态列表（见 `lua-api.md` §0.3） |
| `<LoadStates>` | 10-12 | 面板自己的 UI LoadState（需要特定 Tuner 面板时用） |
| `<Actions>` | 11-20 | 每个 `<ActionData>` = 一个按钮：`<Name>` + `<Action>`(Lua) + `<Location><X><Y></X></Y></Location>` |
| `<StringControls>` / `<IntegerControls>` / `<FloatControls>` / `<BooleanControls>` | — | 各含 `<Name>` + `<GetFunction>` + `<SetFunction>` + `<Location>`（整数另有 `<DefaultValue>`） |
| `<TableViews>` / `<DataViews>` / `<StatTrackers>` | — | 表格/数据/统计视图 |
| `<SelectionLists>` | — | `<SelectionListData>`：`<Name>` 用 `字段名:宽度;字段名:宽度` 定义列，`<PopulateList>` 返回字符串数组（分号分隔字段），`<OnSelection>` 处理选中，`<Sorted>` 是否排序 |
| `<MultiselectLists>` | — | 多选列表 |

最小可用面板 = Name + App + CompatibleStates + 一个 ActionData。写面板调试 Mod 时，**在 `<Action>` 里直接写 Lua**（可多行、可用全局变量在面板内共享，如 `g_TunerSelectedPlayer`）。

---

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

