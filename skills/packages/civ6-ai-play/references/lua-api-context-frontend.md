# 文明6 Lua API 速查（官方文件静态核对 + 真机运行实测） — 运行上下文/开局

> 分册：由 [lua-api.md](lua-api.md) 按主题拆出；覆盖 0. 先读：运行上下文与三条硬边界、0.1 Lua 跑在 UI 上下文，不是游戏核心、0.2 判断自己在哪个上下文、0.3 FireTuner 面板的"状态"概念、1. 前端：新建一局（配置 + 开局）、1.1 完整最小流程（照抄官方顺序）、1.2 GameConfiguration（前端配置对象，共观测 50 个方法）、1.3 MapConfiguration（共观测 15 个方法）、1.4 PlayerConfigurations：槽位与领袖、1.5 开局与存读档：Network.*。触发：启动对局、配置玩家与前端调用时。

## 0. 先读：运行上下文与三条硬边界

### 0.1 Lua 跑在 UI 上下文，不是游戏核心

官方自动化脚本头部的注释把限制写得最清楚 【静态核对】：

- `Base/Assets/UI/Automation/Automation_StandardTestSupport.lua:9-11`
  > "if your automation test starts or load a new game, you should NOT rely on local script variables as the whole Lua context may get rebuilt if DLC/Mods are activated/deactivated. Use the Automation parameter containers which are store on the C++ side."
  → **不要在 Lua 局部变量里存跨对局/跨读档状态**；上下文可能被重建，状态要放引擎侧参数容器（见 `official-automation.md` §3）。

三条由此推出的边界：

1. **改游戏状态必须"请求操作"**，不能直接赋值。单位和城市都走 `RequestOperation` / `RequestCommand`（§3、§4），由核心校验后执行。
2. **前端（MainMenu/读盘/玩家配置）和对局中（InGame）是两个不同上下文**，很多对象只在其一存在：`GameConfiguration` / `MapConfiguration` / `PlayerConfigurations` 主要在前端与开局前后用；`Players[]` / `Map` / `UnitManager` / `CityManager` 只有进入对局后才有数据。
3. **观察者（observer）状态下 `Game.GetLocalPlayer()` 可能是 `PlayerTypes.NONE`**，官方测试用这个判断"这一局有没有真人" 【静态核对】`Automation_StandardTests.lua:346`、`:545`；观察者模式的相机接管见 `Automation_StandardTestSupport.lua:55-78`。

### 0.2 判断自己在哪个上下文

| 判断 | 调用 | 来源 |
| --- | --- | --- |
| 是否在前端（主菜单/设置） | `UI.IsInFrontEnd()` | `Base/Assets/UI/Automation/Automation_StandardTests.lua:270` 【静态核对】 |
| 是否在对局中 | `UI.IsInGame()` | `Base/Assets/UI/ActionPanel.lua:967` 附近同族 API 枚举见 §8 |
| 核心是否忙（正在处理消息） | `UI.IsGameCoreBusy()` / `UI.IsProcessingMessages()` | `Base/Assets/UI/WorldInput.lua:818`、`Base/Assets/UI/ActionPanel.lua:541` 【静态核对】 |
| 本机玩家 | `Game.GetLocalPlayer()` | `Base/Assets/UI/ActionPanel.lua:498` 【静态核对】 |
| 本地观察者 | `Game.GetLocalObserver()` | `Debug/Demo.ltp:229` 【静态核对】 |

前端 → 对局的标准切换写法（官方测试用）【静态核对】：

```lua
-- Automation_StandardTests.lua:270-274：不在前端就先退回主菜单，下一轮再来
if (not UI.IsInFrontEnd()) then
    Events.ExitToMainMenu();
    return;
end
```

退出对局回主菜单：`Events.ExitToMainMenu()`（`Automation_StandardTests.lua:272`、`:384`）；直接关闭应用：`Events.UserConfirmedClose()`（`Automation_StandardTestSupport.lua:259`、`Automation_DailySmokeTest.lua:231`）【静态核对】。

### 0.3 FireTuner 面板的"状态"概念

`Debug/*.ltp` 面板用 `<CompatibleStates>` 声明自己只在哪类状态可用，这是官方对"上下文差异"的权威说明 【静态核对】：

| 状态字符串 | 含义 | 例子 |
| --- | --- | --- |
| `MainMenu` | 主菜单 | `Debug/Network.ltp:7-10`（Network 面板 MainMenu/InGame 两态可用） |
| `InGame` | 对局中（UI 可见） | `Debug/AI.ltp:7-9`、`Debug/Players.ltp:7-9`、`Debug/Unit.ltp:12` |
| `GameCore_Tuner` | 需要游戏核心对象（Player/City/Modifiers 等） | `Debug/Player.ltp:7-9`、`Debug/Autoplay.ltp:7-9`、`Debug/Modifiers.ltp:7-9` |
| `TunerXxxPanel` | 该面板自己加载的 LoadState | `Debug/City.ltp:17-22`（`TunerCityPanel`）、`Debug/Map.ltp:17-22`（`TunerMapPanel`） |

面板全清单与每面板能力见 `official-automation.md` §5。

---

## 1. 前端：新建一局（配置 + 开局）

参考流程是官方自动化 `Tests["PlayGame"].Run` 【静态核对】：`Base/Assets/UI/Automation/Automation_StandardTests.lua:267-310`。

### 1.1 完整最小流程（照抄官方顺序）

```lua
-- 来源：Automation_StandardTests.lua:267-310（PlayGame.Run），按同样顺序重排并加注
if (not UI.IsInFrontEnd()) then Events.ExitToMainMenu(); return; end

GameConfiguration.SetToDefaults();                        -- :277 复位全部配置
GameConfiguration.SetValue("RULESET", nil);               -- MainMenu.lua:154 官方"技巧"：清掉 RULESET 让参数逻辑自选默认值

MapConfiguration.SetScript("Continents.lua");             -- :169 地图脚本
MapConfiguration.SetMapSize("MAPSIZE_STANDARD");          -- :176 地图尺寸
-- 尺寸/脚本会改变玩家数，官方紧接着重算（见 UpdatePlayerCounts，:41-54）
local def = GameInfo.Maps[MapConfiguration.GetMapSize()]; -- :44-45
if (def) then
    MapConfiguration.SetMaxMajorPlayers(def.DefaultPlayers);              -- :51
    GameConfiguration.SetParticipatingPlayerCount(def.DefaultPlayers
        + GameConfiguration.GetHiddenPlayerCount());                      -- :52
end

GameConfiguration.SetHandicapType("DIFFICULTY_PRINCE");   -- :189
GameConfiguration.SetGameSpeedType("GAMESPEED_STANDARD"); -- :195
GameConfiguration.SetStartEra("ERA_ANCIENT");             -- :213
-- 可选：分数胜利回合上限（不是"测试跑几回合"）
GameConfiguration.SetMaxTurns(300);                       -- :219
GameConfiguration.SetTurnLimitType(TurnLimitTypes.CUSTOM);-- :220
-- 固定随机种子（复现同一局）
MapConfiguration.SetValue("RANDOM_SEED", 12345);          -- :201
GameConfiguration.SetValue("GAME_SYNC_RANDOM_SEED", 12345);-- :207

-- 把"人类槽位"改成 AI（单机自动跑局的关键一步）
for _, id in ipairs(GameConfiguration.GetHumanPlayerIDs()) do   -- :126-128
    PlayerConfigurations[id]:SetSlotStatus(SlotStatus.SS_COMPUTER);
end

Network.HostGame(ServerType.SERVER_TYPE_NONE);            -- :309 真正开局
```

【静态核对】以上每个调用的行号均来自 `Automation_StandardTests.lua` / `MainMenu.lua`；【待运行时验证】具体参数值（如 `MAPSIZE_STANDARD`、`DIFFICULTY_PRINCE`）是否为合法枚举名，取决于当前规则集/Mod 的 `GameInfo` 内容，建议先 `GameInfo.Maps[...]` / `GameInfo.Difficulties[...]` 查表再传。

> **已实测可用**：2026-10-26 真机跑通了一版等效新局 Lua（含 `SetLeaderTypeName` / `SetCivilizationTypeName` / `Network.BroadcastPlayerInfo` 的确切顺序，以及"必须在哪个 Tuner state 里执行"），见 **§10.3**。

### 1.2 GameConfiguration（前端配置对象，共观测 50 个方法）

**不存在 Lua 定义**，是引擎导出对象（全仓库无 `GameConfiguration = {` 定义）【推断】。下表 = 官方 Lua 中实际调用过的成员（非穷举）【静态核对】：

| 方法 | 用途 | 来源 |
| --- | --- | --- |
| `SetToDefaults([gameMode])` | 全部复位；参数可给 `GameModeTypes.*` | `Automation_StandardTests.lua:277`；`MainMenu.lua:401`（CROSSPLAY）、`:447`（INTERNET） |
| `SetValue(key, value)` | 通用配置键；`nil` 表示清空 | `Automation_StandardTests.lua:207`（`GAME_SYNC_RANDOM_SEED`）、`:631`（`GAME_NAME`）；`MainMenu.lua:154`（`RULESET`） |
| `GetValue(key)` | 读配置键 | `Base/Assets/UI/EndGame/EndGameMenu.lua:271` |
| `SetRuleSet(name)` | 规则集（标准/资料片） | `Automation_StandardTests.lua:163` |
| `SetHandicapType(name)` | 难度（别名 `Difficulty` 由脚本自己兼容，`:184-187`） | `Automation_StandardTests.lua:189` |
| `SetGameSpeedType(name)` | 游戏速度 | `Automation_StandardTests.lua:195` |
| `SetStartEra(name)` | 起始时代 | `Automation_StandardTests.lua:213` |
| `SetMaxTurns(n)` / `SetTurnLimitType(t)` | 回合上限与类型（分数胜利用） | `Automation_StandardTests.lua:219-220` |
| `SetParticipatingPlayerCount(n)` | 参与者总数 | `Automation_StandardTests.lua:52` |
| `GetHiddenPlayerCount()` | 隐藏玩家数 | `Automation_StandardTests.lua:52` |
| `GetHumanPlayerIDs()` / `GetHumanPlayerCount()` | 人类槽位 | `Automation_StandardTests.lua:126`、`:131` |
| `GetAIPlayerIDs()` | AI 槽位 | `Automation_StandardTests.lua:144` |
| `GetAvailablePlayerIDs()` | 空闲槽位 | `Automation_StandardTests.lua:133` |
| `GetParticipatingPlayerIDs()` | 本局全部参与者 | `Debug/Players.ltp:32`；`Base/Assets/UI/FrontEnd/AdvancedSetup.lua:1511` |
| `GetInUsePlayerIDs()` / `GetMultiplayerPlayerIDs()` | 在用/联机玩家 | `Base/Assets/UI/Popups/ChatPanel.lua:645`；`Base/Assets/UI/FrontEnd/Multiplayer/StagingRoom.lua:633` |
| `RegenerateSeeds()` | 重掷随机种子 | `Base/Assets/UI/FrontEnd/AdvancedSetup.lua:1432` |
| `AddEnabledMods(...)` / `ClearEnabledMods()` / `UpdateEnabledMods(...)` | 启用 Mod 列表 | `MainMenu.lua:449`、`:448`；`Base/Assets/UI/FrontEnd/Mods.lua:904` |
| `SetWorldBuilderEditor(b)` / `IsWorldBuilderEditor()` | 世界编辑器模式 | `AdvancedSetup.lua:1420-1422`；`MainMenu.lua:981` |
| `IsAnyMultiplayer()` / `IsHotseat()` / `IsNetworkMultiplayer()` / `IsPlayByCloud()` / `IsLANMultiplayer()` / `IsInternetMultiplayer()` / `IsMatchMaking()` | 模式判定 | `ActionPanel.lua:771`、`:967`；`EndGameMenu.lua:274`；`GameSetupLogic.lua:113-119` |
| `IsPaused()` / `GetPausePlayer()` / `GetGameState()` | 状态查询 | `Panels/PausePanel.lua:28-32`；`FrontEnd/LoadGameMenu.lua:130` |
| `GetCalendarType()` / `GetStartTurn()` / `GetGameSpeedType()` / `GetStartEra()` / `GetRuleSet()` / `GetTeamName(t)` / `GetTeamPlayerCount(t)` | 只读查询 | `GreatWorksSupport.lua:20`；`ARXManager.lua:394`、`:102`；`InGameTopOptionsMenu.lua:442`；`Automation_NarrationManager.lua:153`；`FrontEnd/LeaderPicker.lua:139` |
| `RemovePlayer(id)` | 移除玩家槽 | `AdvancedSetup.lua:1156` |
| `SetToDefaultGameName()` / `SetToPreGame()` | 名称/预对局态 | `FrontEnd/Multiplayer/HostGame.lua:520`；`FrontEnd/LoadGameMenu.lua:513` |

> `GameConfiguration.SetValue` 还有一个官方"批量透传"写法：参数集合里以 `Game.` / `Map.` 开头的键会被分别转发到 `GameConfiguration.SetValue` / `MapConfiguration.SetValue`，值以 `#` 开头则先 `DB.MakeHash` — `Automation_StandardTests.lua:223-261` 【静态核对】。这是从外部（自动化参数/配置）注入任意配置键的通用通道，做 AI 驱动时很好用。

### 1.3 MapConfiguration（共观测 15 个方法）

| 方法 | 用途 | 来源 |
| --- | --- | --- |
| `SetScript(name)` / `GetScript()` | 地图脚本（如 `Continents.lua`） | `Automation_StandardTests.lua:169`；`AdvancedSetup.lua:1319` |
| `SetMapSize(name)` / `GetMapSize()` | 尺寸 | `Automation_StandardTests.lua:176`、`:44` |
| `SetMaxMajorPlayers(n)` / `GetMaxMajorPlayers()` / `GetMinMajorPlayers()` | 主要文明数 | `Automation_StandardTests.lua:51`；`AdvancedSetup.lua:1173`；`GameSetupLogic.lua:769` |
| `SetMaxMinorPlayers(n)` / `SetMinMinorPlayers(n)` / `GetMinMinorPlayers()` | 城邦数 | `GameSetupLogic.lua:813-814`、`:775` |
| `SetValue(key, v)` / `GetValue(key)` | 通用键（`RANDOM_SEED`） | `Automation_StandardTests.lua:201`；`FrontEnd/PlayerSetupLogic.lua:344` |
| `SetImportFilename(name)` | 导入地图文件 | `FrontEnd/LoadGameMenu.lua:148` |

### 1.4 PlayerConfigurations：槽位与领袖

`PlayerConfigurations[id]` 以 **player_id 为索引**返回配置对象（`Automation_StandardTests.lua:128` 等）【静态核对】。

**关键坑（官方原话）** `Base/Assets/UI/FrontEnd/PlayerSetupLogic.lua:54-56` 【静态核对】：
> "This is a hack. Right now changing a player's leader requires many explicit calls in a specific order."

官方设置领袖的**显式顺序**（`PlayerSetupLogic.lua:57-81`）：

```lua
-- 指定领袖
local playerConfig = PlayerConfigurations[o.PlayerId];
playerConfig:SetLeaderName(rawNameOrName);         -- :77 显示名（可为 nil）
playerConfig:SetLeaderTypeName("LEADER_TRAJAN");   -- :80 领袖类型名

-- 随机领袖（三种随机池）
playerConfig:SetLeaderName(nil);
playerConfig:SetLeaderTypeName(nil);
playerConfig:SetLeaderRandomPoolID(LeaderRandomPoolTypes.LEADER_RANDOM_POOL_DEFAULT); -- :65（_POOL_1 :69 / _POOL_2 :73）

Network.BroadcastPlayerInfo(o.PlayerId);           -- :89 改完广播给联机对端
```

观测到的 `PlayerConfiguration` 方法（前端 + 自动化，非穷举）【静态核对】：

| 分类 | 方法 | 来源 |
| --- | --- | --- |
| 槽位 | `SetSlotStatus(SlotStatus.*)`、`GetSlotStatus()` | `AdvancedSetup.lua:1384`、`:1383`；`Automation_StandardTests.lua:128`（`SS_COMPUTER`）、`:135`（`SS_TAKEN`） |
| 槽位 | `SetMajorCiv()`、`SetTeam(t)`、`SetReady(b)`、`GetReady()` | `AdvancedSetup.lua:1385`；`Multiplayer/StagingRoom.lua:931`、`:1012`；`PlayerSetupLogic.lua:898` |
| 领袖 | `SetLeaderTypeName` / `GetLeaderTypeName` / `GetLeaderTypeID` / `GetLeaderName` / `SetLeaderName` / `SetLeaderRandomPoolID` / `GetLeaderRandomPoolID` | 见上；`AdvancedSetup.lua:1283-1285`；`FrontEnd/LoadScreen.lua:208`、`:349` |
| 文明 | `SetCivilizationTypeName` / `GetCivilizationTypeName` / `GetCivilizationTypeID` / `GetCivilizationShortDescription` / `GetCivilizationDescription` | `FrontEnd/LoadGameMenu.lua:523`；`LoadScreen.lua:330`；`Automation_StandardTests.lua:860-865` |
| 判定 | `IsHuman()`、`IsAlive()`、`IsParticipant()`、`IsLocked()`、`GetCivilizationLevelTypeID()` | `Multiplayer/StagingRoom.lua:1940`；`ActionPanel.lua:935`；`PlayerSetupLogic.lua:257`、`:928`；`Automation_StandardTests.lua:146` |
| 其它 | `GetNickName([id])`、`GetPlayerName()`、`GetHandicapTypeID()`、`GetValue(id)`、`GetModReady()` | `Debug/Players.ltp:51-52`；`Debug/Victories.ltp:173`；`AdvancedSetup.lua:1286`；`Multiplayer/StagingRoom.lua:1133` |

`SlotStatus` 已观测成员：`SS_CLOSED`（`AdvancedSetup.lua:1383`）、`SS_COMPUTER`（`Automation_StandardTests.lua:128`）、`SS_TAKEN`（`:135`）、`SS_OPEN`（`StagingRoom.lua:120`）、`SS_OBSERVER`（`StagingRoom.lua:1126`）【静态核对】。

"把人类玩家变成 AI"的官方两段式（`Automation_StandardTests.lua:121-156`）：

```lua
-- 需求 N 个真人；先从空闲槽拿，再从 AI 槽里"抢"完整文明
local neededHumanPlayers = humanPlayerCount - GameConfiguration.GetHumanPlayerCount();
if neededHumanPlayers > 0 then
    for _, id in ipairs(GameConfiguration.GetAvailablePlayerIDs()) do
        PlayerConfigurations[id]:SetSlotStatus(SlotStatus.SS_TAKEN);
        neededHumanPlayers = neededHumanPlayers - 1;
        if neededHumanPlayers == 0 then break; end
    end
end
-- 反向：把所有真人槽变 AI（单机自动局最常用）
for _, id in ipairs(GameConfiguration.GetHumanPlayerIDs()) do
    PlayerConfigurations[id]:SetSlotStatus(SlotStatus.SS_COMPUTER);
end
```

【待运行时验证】`SetSlotStatus` 之后是否需要重算玩家数（官方在 `MapScript/MapSize` 变更后调用 `UpdatePlayerCounts()`，见 `Automation_StandardTests.lua:170-181` 的注释 "Make sure this is after the MapScript and MapSize"）；不重算可能得到人数不符的配置。

### 1.5 开局与存读档：Network.*

| 调用 | 签名（观测到的形式） | 来源 |
| --- | --- | --- |
| 单机新局 | `Network.HostGame(ServerType.SERVER_TYPE_NONE)` | `Automation_StandardTests.lua:309`；`MainMenu.lua:171`；`FrontEnd/AdvancedSetup.lua:1448` |
| 联机主持 | `Network.HostGame(GetTestServerType())` | `Automation_StandardTests.lua:651` |
| 读档 | `Network.LoadGame(loadParams, serverType)` → 返回 `boolean` 成功与否 | `Automation_StandardTests.lua:298`、`:417`；返回值判断 `:299`、`:418` |
| 存档 | `Network.SaveGame(saveGame)`（异步，等 `Events.SaveComplete`） | `Automation_StandardTests.lua:34-37` |
| 联机加入 | `Network.JoinGame(serverID)` | `Automation_StandardTests.lua:774` |
| 离开 | `Network.LeaveGame()` | `FrontEnd/MainMenu.lua:143` |
| 广播玩家信息 | `Network.BroadcastPlayerInfo(playerId)` | `FrontEnd/PlayerSetupLogic.lua:89` |
| 重同步（调试） | `Network.ForceResync()` / `Network.RequestSnapshot()` / `Network.TestSync()` | `Debug/Network.ltp:15`、`:23`、`:31` |

**存档/读档参数表**（`Automation_StandardTests.lua:27-34` 存档；`:283-302` 读档；`:601-621` 读配置）【静态核对】：

```lua
local saveGame = {};
saveGame.Name        = Automation.GenerateSaveName();      -- 或自己给名字
saveGame.Location    = SaveLocations.LOCAL_STORAGE;
saveGame.Type        = SaveTypes.SINGLE_PLAYER;            -- 联机用 SaveTypes.NETWORK_MULTIPLAYER（:604）
saveGame.IsAutosave  = false;
saveGame.IsQuicksave = false;
saveGame.Directory   = SaveDirectories.DEFAULT;            -- 读档/读配置时可换成参数给的目录
saveGame.FileType    = SaveFileTypes.GAME_CONFIGURATION;   -- 只读"游戏配置"而非存档（:287）
Network.SaveGame(saveGame);
Events.SaveComplete.Add(OnSaveComplete);                   -- 保存不是立即完成，必须等事件（:36-37）
```

`ServerType` 观测成员：`SERVER_TYPE_NONE`（本地）、`SERVER_TYPE_LAN`、`SERVER_TYPE_INTERNET`、`SERVER_TYPE_STEAM`、`SERVER_TYPE_HOTSEAT`、`SERVER_TYPE_FIRAXIS_CLOUD`、`SERVER_TYPE_CROSSPLAY` — 定义与映射见 `Base/Assets/UI/FrontEnd/Multiplayer/LobbyTypes.lua:14-30` 与 `Automation_StandardTests.lua:101`、`:498` 【静态核对】。
`SaveTypes`：`SINGLE_PLAYER`、`NETWORK_MULTIPLAYER`、`TILED_MAP`、`WORLDBUILDER_MAP`。`SaveFileTypes`：`GAME_STATE`、`GAME_CONFIGURATION`。`SaveDirectories`：`DEFAULT`、`BENCHMARK`。`SaveLocations`：`LOCAL_STORAGE`【静态核对】。

> **联机前置**：跨平台模式要先 `Network.AttemptConnectionToCrossPlayLobbyService()` 并等 `Events.CrossPlayLoginStateUpdated` 才能 `HostGame`/`JoinGame`（`Automation_StandardTests.lua:498-507`、`:674-682`）【静态核对】。

---

