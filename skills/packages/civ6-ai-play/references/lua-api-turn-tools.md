# 文明6 Lua API 速查（官方文件静态核对 + 真机运行实测） — 回合/工具

> 分册：由 [lua-api.md](lua-api.md) 按主题拆出；覆盖 5. 回合控制、5.1 结束回合、5.2 回合事件（AI 驱动的主循环钩子）、5.3 AutoplayManager（让引擎自己跑 N 回合）、6. 其它常用工具调用。触发：结束回合、其它常用工具调用时。

## 5. 回合控制

### 5.1 结束回合

```lua
UI.RequestAction(ActionTypes.ACTION_ENDTURN);                             -- 普通结束回合
UI.RequestAction(ActionTypes.ACTION_ENDTURN, { REASON = "UserForced" });  -- 强制（Shift+Enter 同款）
UI.RequestAction(ActionTypes.ACTION_UNREADYTURN);                         -- 取消"已准备"
```

【静态核对】来源：`Base/Assets/UI/ActionPanel.lua:512`、`:571`、`:592`（普通）；`:1099`（带 `REASON = "UserForced"`，来自 `:1097-1099` 的 Shift+Enter 分支）；`:537`（`ACTION_UNREADYTURN`）。
`ActionTypes` 在本机 Lua 中只观测到 4 个成员：`ACTION_ENDTURN`、`ACTION_UNREADYTURN`、`ACTION_RETIRE`（`Base/Assets/UI/Menus/InGameTopOptionsMenu.lua:51`）、`SET_WAR_STATE`（`Base/Assets/UI/Popups/DeclareWarPopup.lua:111`）【静态核对】。

**结束回合前必须先自检**（照抄官方顺序，`ActionPanel.lua:497-515`、`:526-600`）【静态核对】：

```lua
-- 1) 有没有阻塞（单位要指令、要选研究/生产、要选信条……）
local blocker = NotificationManager.GetFirstEndTurnBlocking(Game.GetLocalPlayer());   -- :556
if blocker ~= EndTurnBlockingTypes.NO_ENDTURN_BLOCKING then
    -- 有阻塞：官方会 UI.SelectNextReadyUnit() 或弹对应通知
    return;
end
-- 2) 核心是否空闲
if UI.IsProcessingMessages() then return; end                     -- :541
-- 3) 引擎是否认为能结束
if not UI.CanEndTurn() then return; end                           -- :588-593
-- 4) 本回合是否已发过 turn complete
if UI.HasSentTurnComplete() then return; end                      -- :506
-- 5) 接口模式复位（避免卡在放置/攻击模式）
if UI.GetInterfaceMode() ~= InterfaceModeTypes.SELECTION then
    UI.SetInterfaceMode(InterfaceModeTypes.SELECTION);            -- :547-549
end
UI.RequestAction(ActionTypes.ACTION_ENDTURN);                     -- :571
```

`UI.*` 相关判定成员【静态核对】：`CanEndTurn()`、`HasSentTurnComplete()`、`SkipNextAutoEndTurn()`、`IsProcessingMessages()`、`IsGameCoreBusy()`、`GetInterfaceMode()`、`SetInterfaceMode(mode [, params])`、`GetInterfaceModeParameter(key)`、`IsTurnTimerElapsed(player)`
—— 来源：`ActionPanel.lua:502-512`、`:541`、`:547-549`、`:1099`；`WorldInput.lua:818`；`StrategicView_MapPlacement.lua:27-30`、`:44`。
`InterfaceModeTypes` 观测 41 个成员，常用：`SELECTION`、`MOVE_TO`、`ATTACK`、`RANGE_ATTACK`、`DISTRICT_PLACEMENT`、`BUILDING_PLACEMENT`、`CITY_MANAGEMENT`、`CITY_RANGE_ATTACK`、`WMD_STRIKE`、`SPY_CHOOSE_MISSION`、`NONE` — 来源 `ActionPanel.lua:547`、`:566`、`:636`、`:672-673`；`UnitPanel.lua:2498`、`:2613-2615`、`:2568`【静态核对】。

### 5.2 回合事件（AI 驱动的主循环钩子）

| 事件 | 触发点说明 | 来源 |
| --- | --- | --- |
| `Events.LocalPlayerTurnBegin.Add(fn)` | 本机玩家回合开始 | `ActionPanel.lua:1334`、`:932` |
| `Events.LocalPlayerTurnEnd.Add(fn)` | 本机玩家回合结束 | `ActionPanel.lua:1335`、`:963` |
| `Events.LocalPlayerTurnUnready.Add(fn)` | 取消"已准备" | `ActionPanel.lua:1336`、`:979` |
| `Events.TurnBegin.Add(fn)` | 回合开始（任意玩家） | `ActionPanel.lua:1332`、`:1075` |
| `Events.TurnEnd.Add(fn)` | 回合结束（`Automation_StandardTests.lua:721` 用它倒计剩余回合） | `ActionPanel.lua:1332-1337`；`Automation_StandardTests.lua:721`、`:735` |
| `Events.RemotePlayerTurnEnd.Add(fn)` | 远端玩家回合结束 | `ActionPanel.lua:1337`、`:984` |
| `Events.EndTurnBlockingChanged.Add(fn)` / `EndTurnDirty` | 阻塞状态变化 | `ActionPanel.lua:1328-1329` |
| `Events.UnitMoveComplete` / `UnitOperationStarted` / `UnitOperationsCleared` / `UnitOperationSegmentComplete` | 单位动作进度 | `UnitPanel.lua:4255`、`:4258`；`ActionPanel.lua:1342-1343` |
| `Events.CityProductionCompleted` / `CityProductionChanged` / `CityProductionQueueChanged` | 城市生产 | `CityPanel.lua:1304`；`ActionPanel.lua:1327`；`ProductionManager.lua:442` |
| `Events.SaveComplete` | 存档完成（异步） | `Automation_StandardTests.lua:37` |
| `Events.ExitToMainMenu` | 请求回主菜单 | `Automation_StandardTests.lua:272` |
| `Events.UserConfirmedClose` | 确认关闭应用 | `Automation_StandardTestSupport.lua:259` |

完整事件名清单（官方 UI 共订阅 314 个 `Events.*`）的复现方法见 `official-automation.md` §6。

> 唯一的"AI 主循环"官方范本其实就是：**把回合阻塞都清掉 → `ACTION_ENDTURN` → 等 `LocalPlayerTurnBegin`**。事件的 Add/Remove 必须成对，且**换局/读档后要重新 Add**（官方原话：`Automation_StandardTests.lua:542` "The subscription in Run() is lost on game load. Resubscribe so it works while ingame."）【静态核对】。

### 5.3 AutoplayManager（让引擎自己跑 N 回合）

这是"不写 AI 也能把对局推进 N 回合"的官方通道 【静态核对】，用法来自 `Automation_StandardTests.lua:326-335`、`:367`：

```lua
local turnCount = Automation.GetSetParameter("CurrentTest", "Turns");   -- 0 = 不限回合
local observeAs = GetCurrentTestObserver();
AutoplayManager.SetTurns(turnCount);           -- 跑多少回合
AutoplayManager.SetReturnAsPlayer(0);          -- 结束后把控制权还给谁（player id）
AutoplayManager.SetObserveAsPlayer(observeAs); -- 过程中以谁的身份观察
AutoplayManager.SetActive(true);               -- 开始
...
AutoplayManager.SetActive(false);              -- 停止（Stop 里务必执行）
```

观测到的其余成员（来自 `Debug/Autoplay.ltp`）【静态核对】：

| 调用 | 说明 | 来源 |
| --- | --- | --- |
| `AutoplayManager.GetTurns()` / `SetTurns(n)` | 回合数；`-1` 表示不限（面板把 "No limit" 映射为 `-1`） | `Debug/Autoplay.ltp:26`、`:30`、`:145-161` |
| `AutoplayManager.IsActive()` / `SetActive(b)` | 开关 | `Debug/Autoplay.ltp:45`、`:49` |
| `AutoplayManager.GetReturnAsPlayer()` / `SetReturnAsPlayer(id)` | 结束后交还控制的玩家 | `Debug/Autoplay.ltp:100`、`:111` |
| `AutoplayManager.GetObserveAsPlayer()` / `SetObserveAsPlayer(id)` | 观察对象（`PlayerTypes.NONE` / `OBSERVER` / 具体 id） | `Debug/Autoplay.ltp:179-211` |
| `AutoplayManager.GetDisableAssertsForAutoplay()` / `SetDisableAssertsForAutoplay(b)` | 关断言（长跑防崩溃） | `Debug/Autoplay.ltp:60`、`:63` |
| 事件 | `LuaEvents.AutoPlayStart` / `LuaEvents.AutoPlayEnd`，注释明确 "Raised by engine AutoPlay_Manager!" | `Base/Assets/UI/ActionPanel.lua:1349-1350` |
| 日志 | autoplay 独立日志（`Automation_StandardTests.lua:25` 注释提到 `autoplay.log`） | `Automation_StandardTests.lua:25` |

> 官方面板的所有 autoplay 控件都套了 `if (not Automation.IsActive()) then` 保护（`Debug/Autoplay.ltp:29`、`:48`、`:110`、`:155`、`:209`）——**自动化测试运行期间不允许手动改 autoplay 参数**。做外部驱动时同样应避免在 autoplay 激活时下指令。

---

## 6. 其它常用工具调用

| 调用 | 说明 | 来源 |
| --- | --- | --- |
| `Automation.Log(msg)` / `Automation.LogDivider()` | 写自动化日志 | `Automation_StandardTests.lua:18`；`Automation_StandardTestSupport.lua:200` |
| `Automation.GenerateSaveName()` / `Automation.GetLastGeneratedSaveName()` | 自动存档名 | `Automation_StandardTests.lua:28`、`:408` |
| `Automation.SetActive(b)` / `Automation.IsActive()` | 自动化开关 | `Automation_StandardTestSupport.lua:138`；`Debug/Autoplay.ltp:29` |
| `Automation.Pause(b)` | 暂停 | `Automation_StandardTestSupport.lua:125` |
| `Automation.SendTestComplete()` | 宣告当前测试完成（**不要**直接发 `LuaEvents.AutomationTestComplete`） | `Automation_StandardTests.lua:17-19` |
| `Automation.*Parameter` 系列 | 见 `official-automation.md` §3 | — |
| `UserConfiguration.SetLockedValue("QuickMovement", b)` / `LockValue(...)` | 锁定用户设置（快速移动/战斗） | `Automation_StandardTests.lua:76`、`:115-116` |
| `UserConfiguration.IsAutoEndTurn()` / `IsAutoUnitCycle()` | 读用户设置 | `ActionPanel.lua:502`、`:956` |
| `DB.MakeHash(str)` | 字符串转哈希 | `UnitPanel.lua:2501`；`Automation_StandardTests.lua:240` |
| `Matchmaking.InitLobby(lobbyType)` / `RefreshGameList()` / `GetGameListEntry(idLobby)` | 联机列表 | `Automation_StandardTests.lua:833-834`、`:758` |
| `Benchmark.RunGraphicsBenchmark(save)` / `RunExp2GraphicsBenchmark(save, dir, "A.lua; B.lua")` / `RunAIBenchmark` | 基准测试（第三参是**分号分隔的自动化脚本名**，见 `official-automation.md` §2） | `Base/Assets/UI/FrontEnd/MainMenu.lua:290`、`:294`、`:298`、`:302` |

---

