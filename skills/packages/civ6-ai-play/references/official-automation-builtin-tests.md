# 文明6 官方自动化测试与 Debug 面板（结构 + 可借鉴点 + 运行实测补充） — 内置测试/autoplay

> 分册：由 [official-automation.md](official-automation.md) 按主题拆出；覆盖 5. 内置测试项逐个看、5.1 PlayGame（最重要的模板）、5.2 LoadGame、5.3 HostGame（联机 + autoplay）、5.4 JoinGame（客户端）、5.5 公共参数注入：ApplyCommonNewGameParametersToConfiguration、6. PlayGame 支持的 `CurrentTest` 参数全表、7. autoplay 用法（"不写 AI 也能推进对局"）、7.1 启动 / 停止、7.2 回合数语义有矛盾，需实测、7.3 事件、7.4 防崩溃开关、7.5 极简模板：DailySmokeTest（冒烟测试）。触发：查内置测试项、CurrentTest 参数、autoplay 用法时。

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

