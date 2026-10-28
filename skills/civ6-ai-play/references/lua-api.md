# 文明6 Lua API 速查（官方文件静态核对 + 真机运行实测）

> **适用范围**：用 Lua（FireTuner / 自定义 UI / 自动化脚本）读取对局状态、新建对局、操作单位与城市、结束回合。
> **依据**：§0–§9 只依据游戏安装目录内的官方文件（本地安装版本；行号随版本可能偏移，引用时以实际文件复核；未引用任何第三方仓库、论坛或 Mod 代码）；**§10 是 2026-10-26 的真机运行实测记录**，两类证据分开标注、不混用。
> **证据等级**（每条结论都标注其一）：
> - 【静态核对】= 调用形式/枚举成员在官方文件中直接可见，`文件:行` 已逐条核对。
> - 【待运行时验证】= 官方文件里能看到该调用，但参数完整语义、返回值结构、副作用或时序需在运行中的游戏里验证（推荐 FireTuner 控制台）。
> - 【推断】= 由多处官方用法交叉推出、但无单点直接定义（例如引擎侧对象未在 Lua 中定义）。
> - 【运行实测 2026-10-26】= 真机 Tuner 通道实测得到（帧协议、状态编号、返回值、失败现象）；换游戏版本/Mod 组合需重测。

`GAME_ROOT` 指游戏安装根目录（由 [environment.md](environment.md) 的「路径探测」解析；不同机器路径不同，不要写死）：

本文所有 `Base/...`、`Debug/...` 引用都相对于 `GAME_ROOT`。

---

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

## 2. 对局中：读状态

### 2.1 全局入口对象

| 对象 | 说明 | 来源 |
| --- | --- | --- |
| `Game` | 全局单例（局信息/管理器入口） | 全仓库无 Lua 定义 → 引擎导出【推断】 |
| `Players[playerId]` | 玩家对象 | `Debug/Players.ltp:34` |
| `PlayerConfigurations[playerId]` | 玩家配置（跨前后端） | `Debug/Players.ltp:35` |
| `PlayerManager` | 玩家集合工具 | `Debug/Map.ltp:54`、`Debug/Player.ltp:731` |
| `GameInfo` | 数据库表（按表名访问） | `Base/Assets/UI/Panels/UnitPanel.lua:548` |
| `Map` | 地图 | `Debug/Map.ltp:28` |
| `PlayersVisibility[id]` | 玩家视野 | `Debug/Map.ltp:27` |
| `Locale` | 本地化 | `Debug/City.ltp:415` |
| `DB` | 哈希等 | `Base/Assets/UI/Panels/UnitPanel.lua:2501`（`DB.MakeHash`） |
| `GameDefines` | 常量（`MAX_PLAYERS` 等） | `Automation_StandardTests.lua:43`、`Debug/Players.ltp:95` |
| `NotificationManager` / `Matchmaking` / `UserConfiguration` | 通知/联机匹配/用户设置 | `ActionPanel.lua:556`、`Automation_StandardTests.lua:833`、`:76` |

### 2.2 Game.* 观测到的成员【静态核对】

| 调用 | 说明 | 来源 |
| --- | --- | --- |
| `Game.GetLocalPlayer()` | 本机玩家 id（可能是 `PlayerTypes.NONE`） | `ActionPanel.lua:498`；`Automation_StandardTests.lua:346` |
| `Game.GetLocalObserver()` | 本机观察者 id | `Debug/Demo.ltp:229` |
| `Game.GetCurrentGameTurn()` | 当前回合 | `Debug/Diplomacy.ltp:364` |
| `Game.GetRandomSeed()` | 随机种子 | `Debug/Player.ltp:586` |
| `Game.GetEras()` → `:ChangePlayerEraScore(player, delta)` | 时代分（先 `~= nil` 判定，DLC 依赖） | `Debug/Player.ltp:306-307`、`:316-317`、`:326-327`、`:336-337` |
| `Game.GetGreatPeople():GetTimeline()` | 伟人时间线 | `Debug/Great People.ltp:32` |
| `Game.GetHeroesManager()` | 英雄管理器（需 DLC） | `Debug/Heroes.ltp:75` |
| `Game.GetFalloutManager()` | 核污染管理器 | `Debug/Random Events.ltp:221` |
| `Game.GetPlayers({Alive=true, Major=true})` | 带过滤的玩家列表 | `Debug/Heroes.ltp:123` |
| `Game.GetWinningTeam()` / `Game.GetVictoryProgressForTeam(victory, team)` / `Game.GetVictoryRequirements(team, victory)` | 胜利 | `Debug/Victories.ltp:16`、`:53`、`:52` |
| `Game.GetDefeatRequirements(player, defeat)` | 失败条件 | `Debug/Defeats.ltp:34` |
| `Game.WriteHistoryLog()` | 写历史日志（调试） | `Debug/Autoplay.ltp:14` |

### 2.3 Player 对象（`Players[id]`）观测成员

| 分类 | 调用 | 来源 |
| --- | --- | --- |
| 身份 | `GetID()`、`GetTeam()`、`IsAlive()`、`IsEverAlive()`、`WasEverAlive()`、`IsHuman()`、`IsMajor()`、`IsTurnActive()` | `Debug/Players.ltp:38-69`；`Automation_StandardTests.lua:857-868` |
| 成员集合 | `GetCities()`、`GetUnits()` | `Automation_StandardTestSupport.lua:21`、`:68` |
| 资源 | `GetTreasury():GetGoldBalance()` / `:SetGoldBalance(n)` / `:ChangeGoldBalance(n)` | `Debug/Player.ltp:556`、`:560`、`:100` |
| 文化 | `GetCulture():GetCultureYield()`、`GetProgressingCivic()`、`GetTurnsLeftOnCurrentCivic()`、`ChangeCurrentCulturalProgress(n)`、`SetCulturalProgress(civic, amount)`、`GetCultureCost(civic)` | `Debug/Player.ltp:572`、`:615`、`:635`、`:108`、`:901` |
| 科技 | `GetTechs():CanResearch(id)`、`HasTech(id)`、`GetTurnsToResearch(id)`、`GetResearchCost(id)`、`GetResearchProgress()`、`SetResearchProgress(id, n)`、`ChangeCurrentResearchProgress(n)`、`SetTech(id, bool)`、`GetResearchingTech()` | `Debug/Player.ltp:124-138`、`:159`、`:83` |
| 宗教 | `GetReligion():ChangeFaithBalance(n)`、`GetFaithBalance()` | `Debug/Player.ltp:147`；`Debug/WorldBuilder.ltp:170` |
| 外交 | `GetDiplomacy():SetAtWarWith(team, true)`、`GetFavor()`、`ChangeFavor(n)`、`SetHasDeclaredFriendship(player, true)` | `Debug/Player.ltp:172-173`、`:694`、`:365`；`Debug/Diplomacy.ltp:138-139` |
| AI | `GetInfluenceMap():Find(plotIndex)` | `Debug/AI.ltp:23-26` |

玩家列表两种拿法：

```lua
-- A：活着的玩家数组（Automation_StandardTests.lua:855-856）
for _, pPlayer in ipairs(PlayerManager.GetAlive()) do ... end

-- B：按 id 遍历（Debug/Players.ltp:32-37）
for _, player_id in ipairs(GameConfiguration.GetParticipatingPlayerIDs()) do
    local pPlayer = Players[player_id];
    local pPlayerConfig = PlayerConfigurations[player_id];
    if (pPlayerConfig and pPlayer and pPlayer:WasEverAlive()) then ... end
end
```

`PlayerManager` 观测成员：`GetAlive()`（`Automation_StandardTests.lua:855`）、`IsAlive(id)`（`Debug/WorldBuilder.ltp:751`）、`IsValid(id)`（`Automation_StandardTestSupport.lua:62`）、`GetPlayer(id)`（`Debug/WorldBuilder.ltp:752`）、`SetLocalObserverTo(id | PlayerTypes.OBSERVER)`（`Debug/Map.ltp:54`、`:64`）【静态核对】。

**观察者模式接管相机**（官方测试 `Automation_StandardTestSupport.lua:55-78`）【静态核对】：

```lua
-- observeAs 为 PlayerTypes.OBSERVER / NONE 或某个 player id
PlayerManager.SetLocalObserverTo(PlayerTypes.OBSERVER);   -- Debug/Map.ltp:64
-- 然后把镜头放到该玩家的首都，找不到就看它一个单位
local pCapital = Players[p]:GetCities():GetCapitalCity();  -- :20-22
if pCapital then UI.LookAtPlot(pCapital:GetX(), pCapital:GetY()); end   -- :24
for i, pUnit in pPlayer:GetUnits():Members() do                         -- :68-69
    if (not pUnit:IsDead()) then UI.LookAtPlot(pUnit:GetX(), pUnit:GetY()); break; end
end
```

### 2.4 城市 / 单位对象集合遍历

```lua
-- 城市：按 (playerId, cityId) 取（Debug/*.ltp 与官方 UI 通用）
local pCity  = CityManager.GetCity(playerID, cityID);       -- Base/Assets/UI/ProductionHelper.lua:178
local pCity2 = CityManager.GetCityAt(x, y);                 -- Base/Assets/UI/GenVFX.lua:32

-- 某玩家的城市集合
local pPlayerCities = Players[p]:GetCities();
local pCapital = pPlayerCities:GetCapitalCity();            -- Automation_StandardTestSupport.lua:21-22
local pRanged  = pPlayer:GetCities():GetFirstRangedAttackCity(); -- ActionPanel.lua:563

-- 单位：按 (playerId, unitId) 取 / 遍历某玩家单位
local pUnit = UnitManager.GetUnit(playerID, componentID);   -- Automation_ObserverCamera.lua:571
for i, pUnit in pPlayer:GetUnits():Members() do ... end     -- Automation_StandardTestSupport.lua:69
```

### 2.5 Map / 视野 / GameInfo / Locale

| 调用 | 说明 | 来源 |
| --- | --- | --- |
| `Map.GetPlotCount()` | 地格总数 | `Debug/Map.ltp:28` |
| `Map.GetPlot(x, y)` | 按坐标取格 | `Debug/Map.ltp:91` |
| `Map.GetPlotByIndex(index)` | 按索引取格 | `Debug/AI.ltp:44` |
| `Map.GetPlotLocation(index)` → `x, y` | 索引转坐标 | `Debug/Rivers.ltp:132` |
| `Map.GetMapSize()` | 尺寸名 | `Debug/AutoProfiler.ltp:35` |
| `Map.IsPlot(plotId)` | 合法性校验 | `Base/Assets/UI/WorldInput.lua:799` |
| `GameInfo.Maps[mapSize].GridWidth/.GridHeight` | 地图尺寸数值 | `Debug/AutoProfiler.ltp:36-37` |
| `PlayersVisibility[id]:IsVisible(x, y)` | 该玩家是否可见 | `Base/Assets/UI/Civ6Common.lua:115` |
| `PlayersVisibility[id]:ChangeVisibilityCount(plotIndex, delta)` | 改视野计数（+1 揭示 / 0 探索 / -1 撤销） | `Debug/Map.ltp:27-29`、`:42`、`:76` |
| `Locale.Lookup(keyOrName)` | 文本本地化 | `Debug/City.ltp:415`；`Base/Assets/UI/Panels/UnitPanel.lua:574` |
| `GameInfo.<Table>()` 迭代 / `GameInfo.<Table>[key]` 索引 | 数据库表 | `UnitPanel.lua:548`（`GameInfo.UnitOperations()`）；`Debug/WorldBuilder.ltp:490`（`GameInfo.Improvements()`）；`Civ6Common.lua:139`（`GameInfo.Units[name].Domain`） |

官方"揭示全图"（`Debug/Map.ltp:26-31`、`:39-44`、`:73-78`）【静态核对】：

```lua
if (Game.GetLocalPlayer() ~= -1) then
    local pVis = PlayersVisibility[Game.GetLocalPlayer()];
    for i = 0, Map.GetPlotCount() - 1, 1 do
        pVis:ChangeVisibilityCount(i, 1);   -- 1 揭示 / 0 探索 / -1 撤销
    end
end
```

> 注意 `ChangeVisibilityCount` 的语义是从官方面板三个按钮反推的（Reveal All=1、Explore All=0、Unreveal All=-1），**单格叠加是否可逆需运行时验证**【待运行时验证】。

### 2.6 NotificationManager（回合阻塞/通知）

| 调用 | 说明 | 来源 |
| --- | --- | --- |
| `NotificationManager.GetFirstEndTurnBlocking(player)` | 当前阻塞类型 | `Base/Assets/UI/ActionPanel.lua:556` |
| `NotificationManager.FindEndTurnBlocking(blockingId, player)` | 取阻塞通知 | `ActionPanel.lua:584` |
| `NotificationManager.Find(player, notificationId)` | 取通知 | `ActionPanel.lua:1015` |
| `NotificationManager.GetList(player)` | 通知列表 | `Debug/Notifications.ltp:73` |
| `NotificationManager.RestoreVisualState(player)` | 恢复视觉状态 | `ActionPanel.lua:1085` |

阻塞类型枚举 `EndTurnBlockingTypes.*`（18 项，`ActionPanel.lua:99-123` 全部可见）：`NO_ENDTURN_BLOCKING`、`ENDTURN_BLOCKING_UNITS`、`..._STACKED_UNITS`、`..._UNIT_NEEDS_ORDERS`、`..._RESEARCH`、`..._CIVIC`、`..._FILL_CIVIC_SLOT`、`..._CONSIDER_GOVERNMENT_CHANGE`、`..._CONSIDER_RAZE_CITY`、`..._PRODUCTION`、`..._PANTHEON`、`..._RELIGION`、`..._BELIEF`、`..._GIVE_INFLUENCE_TOKEN`、`..._CLAIM_GREAT_PERSON`、`..._SPY_CHOOSE_ESCAPE_ROUTE`、`..._SPY_CHOOSE_DRAGNET_PRIORITY`、`..._ARTIFACT`【静态核对】。

---

## 3. 单位操作

### 3.1 两个核心调用

```lua
-- 能开始吗？（第 5 参要结果表）
local bCanStart, tResults = UnitManager.CanStartOperation(pUnit, eOperation, targetPlot, tParameters, bWantResults);
-- 开始
UnitManager.RequestOperation(pUnit, eOperation, tParameters);
```

官方调用形式（**参数个数会变**，注意逐条比对）【静态核对】：

| 形式 | 来源 |
| --- | --- |
| `CanStartOperation(unit, op, nil, tParameters)` | `Base/Assets/UI/Civ6Common.lua:141` |
| `CanStartOperation(unit, op, nil, tParameters, true)` | `Base/Assets/UI/Panels/UnitPanel.lua:558` |
| `CanStartOperation(unit, op, nil, false, false)` — 注释 "No exclusion test, no results" | `UnitPanel.lua:609` |
| `CanStartOperation(unit, op, nil, false, OperationResultsTypes.ALL)` | `UnitPanel.lua:630` |
| `CanStartOperation(unit, op, targetPlot, false, true)` | `Base/Assets/UI/Choosers/EspionageChooser.lua:199` |
| `CanStartOperation(unit, op, nil, tParameters, OperationResultsTypes.NO_TARGETS)` | `UnitPanel.lua:677` |
| `RequestOperation(unit, op)` | `UnitPanel.lua:2535`、`:2636` |
| `RequestOperation(unit, op, tParameters)` | `UnitPanel.lua:2557`；`Civ6Common.lua:142` |

【静态核对】第 1 参 = 单位对象，第 2 参 = `UnitOperationTypes.*`，第 5 参可接受 `true/false` 或 `OperationResultsTypes.*`。
【待运行时验证】第 3 参 `targetPlot`（地格对象，非坐标）与第 4 参"参数表 or false"的准确契约；`OperationResultsTypes` 仅观测到 `ALL`（`UnitPanel.lua:630`）与 `NO_TARGETS`（`UnitPanel.lua:677`）两个值。

### 3.2 UnitOperationTypes 观测成员（32 项，非穷举）

| 成员 | 用途 | 来源 |
| --- | --- | --- |
| `MOVE_TO` | 移动 | `Civ6Common.lua:163`；`UnitPanel.lua:608` |
| `SWAP_UNITS` | 换位 | `Civ6Common.lua:160-161` |
| `FOUND_CITY` | 建城 | `UnitPanel.lua:629-630`、`:2636` |
| `BUILD_IMPROVEMENT` | 造改良 | `UnitPanel.lua:337`、`:2557` |
| `RANGE_ATTACK` | 远程攻击 | `Civ6Common.lua:148-149` |
| `AIR_ATTACK` / `DEPLOY` | 空袭/部署（空军） | `Civ6Common.lua:141-144` |
| `COASTAL_RAID` | 沿海劫掠 | `Civ6Common.lua:153-154` |
| `WMD_STRIKE` | 核打击 | `UnitPanel.lua:635-643` |
| `FORTIFY` / `ALERT` | 驻守/警戒 | `Base/Assets/UI/WorldTracker.lua:948` |
| `MAKE_TRADE_ROUTE` | 商队路线 | `Base/Assets/UI/Choosers/TradeRouteChooser.lua:817`、`:835` |
| `REBASE` | 飞机转场 | `Base/Assets/UI/WorldInput.lua:2486-2487` |
| `SPY_COUNTERSPY` / `SPY_TRAVEL_NEW_CITY` / `SPY_LISTENING_POST` / `SPY_SIPHON_FUNDS` / `SPY_GAIN_SOURCES` / `SPY_STEAL_TECH_BOOST` / `SPY_GREAT_WORK_HEIST` | 间谍 | `Choosers/EspionageChooser.lua:374`、`:616`；`Base/Assets/UI/EspionageSupport.lua:198-219` |
| 参数键 | `PARAM_X`、`PARAM_Y`、`PARAM_X0/PARAM_Y0/PARAM_X1/PARAM_Y1`、`PARAM_MODIFIERS`、`PARAM_IMPROVEMENT_TYPE`、`PARAM_OPERATION_TYPE`、`PARAM_WMD_TYPE`、`PARAM_FLAGS` | `Civ6Common.lua:105-106`、`:140`；`TradeRouteChooser.lua:813-816`；`UnitPanel.lua:568`、`:642`；`Choosers/TradeOriginChooser.lua:68`；`Base/Assets/UI/Popups/RazeCity.lua:17` |

移动修正符 `UnitOperationMoveModifiers.*`：`NONE`、`ATTACK`、`MOVE_IGNORE_UNEXPLORED_DESTINATION`（`Civ6Common.lua:140`、`:147`、`:152`）【静态核对】。

### 3.3 移动单位（最常用，官方完整分支）

官方 `MoveUnitToPlot` → `RequestMoveOperation`（`Base/Assets/UI/Civ6Common.lua:102-169`）【静态核对】：

```lua
local tParameters = {};
tParameters[UnitOperationTypes.PARAM_X] = plotX;      -- :105
tParameters[UnitOperationTypes.PARAM_Y] = plotY;      -- :106

-- 空军：AIR_ATTACK / DEPLOY
tParameters[UnitOperationTypes.PARAM_MODIFIERS] = UnitOperationMoveModifiers.ATTACK;
if UnitManager.CanStartOperation(kUnit, UnitOperationTypes.AIR_ATTACK, nil, tParameters) then
    UnitManager.RequestOperation(kUnit, UnitOperationTypes.AIR_ATTACK, tParameters);
elseif UnitManager.CanStartOperation(kUnit, UnitOperationTypes.DEPLOY, nil, tParameters) then
    UnitManager.RequestOperation(kUnit, UnitOperationTypes.DEPLOY, tParameters);
end

-- 陆军/海军
tParameters[UnitOperationTypes.PARAM_MODIFIERS] = UnitOperationMoveModifiers.NONE;
if UnitManager.CanStartOperation(kUnit, UnitOperationTypes.RANGE_ATTACK, nil, tParameters)
   and (kUnit:GetRangedCombat() > kUnit:GetCombat() or kUnit:GetBombardCombat() > kUnit:GetCombat()) then
    UnitManager.RequestOperation(kUnit, UnitOperationTypes.RANGE_ATTACK, tParameters);
else
    tParameters[UnitOperationTypes.PARAM_MODIFIERS] =
        UnitOperationMoveModifiers.ATTACK + UnitOperationMoveModifiers.MOVE_IGNORE_UNEXPLORED_DESTINATION;
    if UnitManager.CanStartOperation(kUnit, UnitOperationTypes.COASTAL_RAID, nil, tParameters) then
        UnitManager.RequestOperation(kUnit, UnitOperationTypes.COASTAL_RAID, tParameters);
    elseif plotX ~= kUnit:GetX() or plotY ~= kUnit:GetY() then
        if UnitManager.CanStartOperation(kUnit, UnitOperationTypes.SWAP_UNITS, nil, tParameters) then
            UnitManager.RequestOperation(kUnit, UnitOperationTypes.SWAP_UNITS, tParameters);
        else
            UnitManager.RequestOperation(kUnit, UnitOperationTypes.MOVE_TO, tParameters);   -- :163 兜底
        end
    end
end
```

> 关键点：**移动其实就是 `MOVE_TO` + `PARAM_X`/`PARAM_Y`**；上层逻辑只是用更具体的操作去覆盖"顺便攻击/换位/飞机"的特例。做 AI 驱动时，直接用 `MOVE_TO` + 坐标最省事，但会失去"到达即攻击"的行为。
> 另一个官方入口：`UI.SetInterfaceMode(InterfaceModeTypes.MOVE_TO)` 让玩家自己点目标（`UnitPanel.lua:2612-2616`）——这是 UI 交互路径，自动化里不推荐。

**宣战保护**：官方在移动前会查 `CombatManager.IsAttackChangeWarState(componentId, x, y)`（`Civ6Common.lua:116`），若会引发宣战则弹确认框而不直接移动。AI 驱动若要"绕过确认直接打"，需自行跳过该检查（行为差异【待运行时验证】）。

### 3.4 建城 / 造改良 / 远程攻击

```lua
-- 建城（UnitPanel.lua:2621-2642）：先判定，结果里可能提示会移除地貌
local bCanStart, kResults = UnitManager.CanStartOperation(pUnit, UnitOperationTypes.FOUND_CITY,
                                                          nil, false, OperationResultsTypes.ALL);
if bCanStart then
    UnitManager.RequestOperation(pUnit, UnitOperationTypes.FOUND_CITY);   -- :2636 / :2641
end

-- 造改良（UnitPanel.lua:2548-2557）：坐标必须给
local tParameters = {};
tParameters[UnitOperationTypes.PARAM_X] = pUnit:GetX();
tParameters[UnitOperationTypes.PARAM_Y] = pUnit:GetY();
tParameters[UnitOperationTypes.PARAM_IMPROVEMENT_TYPE] = improvementHash;   -- GameInfo.Improvements[...].Hash
UnitManager.RequestOperation(pUnit, UnitOperationTypes.BUILD_IMPROVEMENT, tParameters);

-- 远程攻击（WorldInput.lua:839-849）：目标用坐标
local plot = Map.GetPlotByIndex(plotID);
local tParameters = {};
tParameters[UnitOperationTypes.PARAM_X] = plot:GetX();
tParameters[UnitOperationTypes.PARAM_Y] = plot:GetY();
UnitManager.RequestOperation(pUnit, UnitOperationTypes.RANGE_ATTACK, tParameters);
```

`CanStartOperation` 返回的 `tResults` 是**表**，常用键 `UnitOperationResults.*`【静态核对】：
`IMPROVEMENTS`（可选改良列表）、`BEST_IMPROVEMENT`、`FEATURE_TYPE`（会移除的地貌）、`ACTION_NAME`、`ADDITIONAL_DESCRIPTION`、`FAILURE_REASONS`、`PLOTS`、`MODIFIERS`、`MODIFIER_IS_TARGET`
—— 来源：`Base/Assets/UI/Panels/UnitPanel.lua:504-528`、`:561-596`、`:686-703`、`:3815-3818`。

### 3.5 单位指令（Command，与 Operation 不同）

```lua
UnitManager.RequestCommand(pUnit, actionHash [, tParameters]);   -- UnitPanel.lua:2513
```

`UnitCommandTypes` 观测成员【静态核对】：`DELETE`、`CANCEL`、`NAME_UNIT`、`PROMOTE`、`UPGRADE`、`FORM_CORPS`、`FORM_ARMY`、`ENTER_FORMATION`、`AIRLIFT`、`TRANSFORM_UNIT`、`RESTORE_UNIT_MOVES`、`KILL_WEAKER_UNIT`、`NAVAL_GOLD_RAID`、`CONDEMN_HERETIC`、`MOVE_JUMP`、`WAKE`、`TYPE`，参数键 `PARAM_NAME`、`PARAM_PROMOTION_TYPE`、`PARAM_UNIT_ID`、`PARAM_UNIT_PLAYER`、`PARAM_X`、`PARAM_Y`
—— 来源：`UnitPanel.lua:412-448`、`:2602-2604`；`WorldInput.lua:2880-2882`、`:3030-3036`、`:3149-3154`、`:3272-3273`、`:3332-3333`；`WorldTracker.lua:955`。

`CanStartCommand` 观测形式：`CanStartCommand(unit, cmd, true)` / `CanStartCommand(unit, cmd, nil, true)` / `CanStartCommand(unit, cmd, false, tParameters, true)` —— `UnitPanel.lua:419`、`:437`、`:448`、`:454`、`:461-471`【静态核对】；参数语义【待运行时验证】。

### 3.6 UnitManager 其它观测成员

| 调用 | 说明 | 来源 |
| --- | --- | --- |
| `GetUnit(playerId, unitId)` | 取单位对象 | `Automation_ObserverCamera.lua:571` |
| `GetTypeName(unit)` | 类型名（`UNIT_xxx`） | `Base/Assets/Scenarios/Tutorial/TutorialScenarioBase.lua:1243` |
| `GetOperationTypeName(unit)` | 当前操作名 | `Debug/Unit.ltp:323` |
| `GetActivityType(unit)` | 活动类型 | `UnitPanel.lua:2147` |
| `GetQueuedDestination(unit)` | 已排队目标格 | `Base/Assets/UI/WorldInput.lua:821` |
| `GetTravelTime(unit, city)` / `GetEstablishInCityTime(unit, city)` | 间谍行程 | `Choosers/EspionageChooser.lua:404-405` |
| `GetTimeToComplete(op, unit)` | 操作所需回合 | `Base/Assets/UI/EspionageSupport.lua:30` |
| `GetResultProbability(op, unit, plot)` | 结果概率表 | `EspionageSupport.lua:35` |
| `Kill(unit, bDestroy)` | 删除单位 | `Debug/Unit.ltp:51`、`:65` |
| `RestoreMovementToFormation(unit)` / `RestoreUnitAttacks(unit)` | 恢复移动/攻击 | `Debug/Unit.ltp:24-25` |
| `GetUnitMaintenance(hash)` / `GetUnitCorpsMaintenance` / `GetUnitArmyMaintenance` / `GetUnitTypeBaseLifespan` | 费用/寿命 | `Base/Assets/UI/Screens/ReportScreen.lua:319-334`；`Civilopedia/CivilopediaPage_Unit.lua:354` |

单位对象（`pUnit`）观测成员：`GetID`、`GetOwner`、`GetX`、`GetY`、`GetUnitType`、`GetType`、`GetComponentID`、`IsDead`、`GetMovesRemaining`、`GetDamage`/`SetDamage`/`ChangeDamage`、`GetExperience():ChangeExperience(n)`、`GetCombat`/`GetRangedCombat`/`GetBombardCombat`、`GetReligion():GetReligionType()`
—— 来源：`UnitPanel.lua:545`、`:2553-2554`、`Civ6Common.lua:110-111`、`:148`、`Debug/Unit.ltp:37`、`:49-53`、`:485-493`【静态核对】。

---

## 4. 城市生产

### 4.1 核心调用

```lua
CityManager.RequestOperation(city, CityOperationTypes.BUILD, tParameters);
-- 能不能造（第 4 参 true = 要结果表）
local bCanStart, tResults = CityManager.CanStartOperation(city, CityOperationTypes.BUILD, tParameters, true);
```

【静态核对】4 参 `CanStartOperation` 见 `Base/Assets/UI/StrategicView_MapPlacement.lua:220`；3 参 `RequestOperation` 见 `Base/Assets/UI/Panels/ProductionPanel.lua:301`、`:315`、`:370`、`:403`、`:418`。
【待运行时验证】`CanStartOperation` 第 4 参是否严格为布尔（官方只出现过 `true`）。

### 4.2 参数键（按生产对象选一个）

| 要生产 | 参数键 | 值来源 | 来源 |
| --- | --- | --- | --- |
| 单位 | `CityOperationTypes.PARAM_UNIT_TYPE` | `GameInfo.Units[type].Hash` / 列表项 `unitEntry.Hash` | `ProductionPanel.lua:299` |
| 建筑/奇观 | `PARAM_BUILDING_TYPE` | `buildingEntry.Hash` | `ProductionPanel.lua:368`、`:361` |
| 区域 | `PARAM_DISTRICT_TYPE` | `districtEntry.Hash` | `ProductionPanel.lua:401`、`:394` |
| 项目 | `PARAM_PROJECT_TYPE` | `projectEntry.Hash` | `ProductionPanel.lua:416` |
| 军团/军队 | `MILITARY_FORMATION_TYPE` | `MilitaryFormationTypes.CORPS_MILITARY_FORMATION` / `ARMY_MILITARY_FORMATION` | `ProductionPanel.lua:314`、`:328` |
| 放置坐标（区域/奇观必须） | `PARAM_X` / `PARAM_Y` | `plot:GetX()` / `plot:GetY()` | `StrategicView_MapPlacement.lua:47-48`、`:205-207` |
| 队列插入模式 | `PARAM_INSERT_MODE` | `VALUE_APPEND` / `VALUE_REPLACE_AT` / `VALUE_REMOVE_AT` / `VALUE_SWAP` / `VALUE_MOVE_TO` / `VALUE_EXCLUSIVE` | `ProductionPanel.lua:2885-2899`；`ProductionHelper.lua:199-224` |
| 队列位置 | `PARAM_QUEUE_LOCATION` / `PARAM_QUEUE_SOURCE_LOCATION` / `PARAM_QUEUE_DESTINATION_LOCATION` | 整数索引（0 起） | `ProductionHelper.lua:200`、`:210-211`；`ProductionPanel.lua:2890` |

### 4.3 最简"造单位"和"造区域"

```lua
-- 造单位（ProductionPanel.lua:293-303 的等价最小写法）
local tParameters = {};
tParameters[CityOperationTypes.PARAM_UNIT_TYPE] = GameInfo.Units["UNIT_WARRIOR"].Hash;
tParameters[CityOperationTypes.PARAM_INSERT_MODE] = CityOperationTypes.VALUE_REPLACE_AT;
tParameters[CityOperationTypes.PARAM_QUEUE_DESTINATION_LOCATION] = 0;   -- 0 = 当前生产
CityManager.RequestOperation(pCity, CityOperationTypes.BUILD, tParameters);

-- 造需要选位置的区域（StrategicView_MapPlacement.lua:204-220 的等价写法）
local kPlot = Map.GetPlot(x, y);
local tParameters = {};
tParameters[CityOperationTypes.PARAM_X] = kPlot:GetX();
tParameters[CityOperationTypes.PARAM_Y] = kPlot:GetY();
tParameters[CityOperationTypes.PARAM_DISTRICT_TYPE] = GameInfo.Districts["DISTRICT_CAMPUS"].Hash;
tParameters[CityOperationTypes.PARAM_INSERT_MODE] = CityOperationTypes.VALUE_APPEND;
local bCanStart, tResults = CityManager.CanStartOperation(pCity, CityOperationTypes.BUILD, tParameters, true);
if bCanStart then
    CityManager.RequestOperation(pCity, CityOperationTypes.BUILD, tParameters);
end

-- 从队列删除 / 交换（ProductionHelper.lua:196-226）
tParameters[CityOperationTypes.PARAM_INSERT_MODE] = CityOperationTypes.VALUE_REMOVE_AT;
tParameters[CityOperationTypes.PARAM_QUEUE_LOCATION] = queueIndex;
CityManager.RequestOperation(pCity, CityOperationTypes.BUILD, tParameters);
```

> `CanStartOperation` 的 `tResults` 里常用 `CityOperationResults.SUCCESS_CONDITIONS`（字符串数组，需 `Locale.Lookup`）— `StrategicView_MapPlacement.lua:61-67`、`:226-232`【静态核对】。

### 4.4 购买（Command 而非 Operation）

```lua
local tParameters = {};
tParameters[CityCommandTypes.PARAM_UNIT_TYPE] = unitEntry.Hash;
tParameters[CityCommandTypes.PARAM_MILITARY_FORMATION_TYPE] = MilitaryFormationTypes.STANDARD_MILITARY_FORMATION;
tParameters[CityCommandTypes.PARAM_YIELD_TYPE] = GameInfo.Yields["YIELD_GOLD"].Index;   -- 或 YIELD_FAITH
CityManager.RequestCommand(pCity, CityCommandTypes.PURCHASE, tParameters);
```

来源：`ProductionPanel.lua:423-434`、`:449`、`:464`、`:478`；`StrategicView_MapPlacement.lua:218`、`:238`、`:242`【静态核对】。

`CityCommandTypes` 观测成员：`PURCHASE`、`RANGE_ATTACK`、`WMD_STRIKE`、`SET_FOCUS`、`MANAGE`、`NAME_CITY`、`DESTROY`、`SWAP_TILE_OWNER`；参数键 `PARAM_UNIT_TYPE`、`PARAM_BUILDING_TYPE`、`PARAM_DISTRICT_TYPE`、`PARAM_YIELD_TYPE`、`PARAM_PLOT_PURCHASE`、`PARAM_X`/`PARAM_Y`/`PARAM_X0`/`PARAM_Y0`/`PARAM_X1`/`PARAM_Y1`、`PARAM_RANGED_ATTACK`、`PARAM_WMD_TYPE`、`PARAM_MANAGE_CITIZEN`、`PARAM_SWAP_TILE_OWNER`、`PARAM_NAME`、`PARAM_DATA0`、`PARAM_FLAGS`
—— 来源：`ProductionPanel.lua:425-478`、`:1639-1640`；`Panels/CityPanel.lua:448-477`、`:616-629`；`StrategicView_MapPlacement.lua:198`；`WorldInput.lua:2232-2271`、`:2575`；`WorldView/PlotInfo.lua:60-78`；`CityPanelOverview.lua:763-765`【静态核对】。

### 4.5 City 对象 / CityManager 其它

| 调用 | 说明 | 来源 |
| --- | --- | --- |
| `pCity:GetBuildQueue()` → `:AddProgress(n)`、`:GetAt(i)`、`:HasBeenPlaced(hash)` | 生产队列 | `Debug/City.ltp:106-107`；`ProductionHelper.lua:179`、`:185`；`ProductionPanel.lua:345` |
| `pCity:ChangePopulation(delta)` | 人口 | `Debug/City.ltp:28`、`:40` |
| `pCity:SetProperty(key, valueOrNil)` | 城市属性 | `Debug/City.ltp:288`、`:301` |
| `pCity:GetDistricts():GetDistrictAtLocation(x, y)` → `:ChangeDamage(type, delta)` / `:SetPillaged(b)` / `:IsPillaged()` | 区域 | `Debug/City.ltp:118-122`、`:334-336` |
| `pCity:GetBuildings():HasBuilding(hash)` | 建筑 | `ProductionPanel.lua:352` |
| `pCity:GetName()` / `GetX()` / `GetY()` / `GetID()` / `GetOwner()` | 基本属性 | `Debug/City.ltp:415`、`:120` |
| `CityManager.GetCity(player, id)` / `GetCityAt(x, y)` | 取城市 | `ProductionHelper.lua:178`；`GenVFX.lua:32` |
| `CityManager.SetAsCapital(city)` / `SetAsOriginalCapital(city)` / `TransferCityToFreeCities(city)` | 改归属 | `Debug/City.ltp:314`、`:325`、`:277` |
| `Cities.DestroyCity(city)` | 摧毁城市 | `Debug/City.ltp:95` |
| `CityManager.CanStartCommand(city, cmd, wantResults, params, ...)` | 判定（5 参形式） | `ProductionPanel.lua:1639-1640`【待运行时验证】参数顺序 |

---

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

## 7. 状态与 UI 上下文差异（踩坑清单）

1. **前端 vs 对局**：`GameConfiguration`/`MapConfiguration`/`PlayerConfigurations` 在前端就被大量使用（`Automation_StandardTests.lua:267-310` 全程在前端完成配置后才 `Network.HostGame`）；`Players[]`/`Map`/`CityManager`/`UnitManager` 只有在 `Network.HostGame` 之后（且进入 InGame）才有内容。在错误上下文调用得到的可能是 `nil` 而不是报错 —— 官方到处写 `if (pPlayer ~= nil)` 就是这个原因（`Automation_StandardTests.lua:857`、`Debug/Unit.ltp:23`）。
2. **观察者 / 无本地玩家**：`Game.GetLocalPlayer() == PlayerTypes.NONE` 表示当前是纯观察视角（`Automation_StandardTests.lua:346`）。此状态下很多"玩家操作"没有意义，官方测试的做法是先 `StartupObserverCamera(observeAs)` 再看/再结束。
3. **UI 事件与 GameCore 事件都在 UI 上下文派发**：所有 `Events.*` 的订阅都在 UI Lua 里（`ActionPanel.lua:1326-1346` 一屏可见 21 个）。所以"AI 控制游戏"的代码天然属于 UI 脚本层，而不是 Gameplay 层。
4. **上下文会被重建**：见 §0.1 官方注释。跨局保存的状态必须放引擎侧参数容器（`Automation.SetLocalParameter` 等）。
5. **事件订阅是易失的**：读档/换局后需重新 `Add`（`Automation_StandardTests.lua:542` 注释明确）。
6. **必须走 Request**：`UnitManager.RequestOperation` / `CityManager.RequestOperation` / `UI.RequestAction`。直接改对象字段（如 `pUnit:SetDamage`）在官方调试面板里确实存在，但那是**调试面板**用法（`Debug/Unit.ltp:50`、`Debug/City.ltp:28`），不保证触发正常游戏事件；做正式自动化/测试时不要当常规手段【推断 + 待运行时验证】。
7. **FireTuner 面板受状态限制**：面板的 `<CompatibleStates>` 决定它在 MainMenu / InGame / GameCore_Tuner 哪一态可用（§0.3）。`GameCore_Tuner` 类面板（Player/City/Autoplay/Modifiers…）对游戏核心对象访问最全，适合做验证；`InGame` 类面板偏 UI。另外 `Debug/Asset Preview.ltp`、`AutoProfiler.ltp`、`DebugOptions.ltp`、`LandmarkVisualizer.ltp` 声明的是 `TunerAssetPreviewPanel`（资产预览态），与普通对局无关。

---

## 8. 证据索引（被引用文件一览）

| 文件（相对 GAME_ROOT） | 行数 | 本文用途 |
| --- | --- | --- |
| `Base/Assets/UI/Automation/Automation_StandardTests.lua` | 873 | 新局配置全流程；`Tests` 表 |
| `Base/Assets/UI/Automation/Automation_StandardTestSupport.lua` | 318 | 测试驱动器、观察者相机、玩家遍历 |
| `Base/Assets/UI/Automation/Automation_DailySmokeTest.lua` | 368 | 极简 15 回合冒烟测试（可作最小模板） |
| `Base/Assets/UI/Automation/Automation_ObserverCamera.lua` | 718 | 观察者相机活动 |
| `Base/Assets/UI/Civ6Common.lua` | 791 | 移动单位完整分支 `MoveUnitToPlot`/`RequestMoveOperation` |
| `Base/Assets/UI/Panels/UnitPanel.lua` | 4295 | 单位操作/指令全部分支与结果表键 |
| `Base/Assets/UI/Panels/ProductionPanel.lua` | 2994 | 生产/购买/队列参数 |
| `Base/Assets/UI/ProductionHelper.lua` | 262 | 队列增删改 |
| `Base/Assets/UI/ActionPanel.lua` | 1367 | 结束回合、回合事件、阻塞类型 |
| `Base/Assets/UI/WorldInput.lua` | 4255 | 点击操作入口、指令参数 |
| `Base/Assets/UI/StrategicView_MapPlacement.lua` | 415 | 区域/奇观放置坐标参数 |
| `Base/Assets/UI/FrontEnd/AdvancedSetup.lua` | 1748 | 开局按钮流程、加减玩家 |
| `Base/Assets/UI/FrontEnd/PlayerSetupLogic.lua` | 1476 | 领袖/随机池设置顺序 |
| `Base/Assets/UI/FrontEnd/MainMenu.lua` | 1811 | `SetToDefaults` 用法、基准测试脚本入口 |
| `Base/Assets/UI/FrontEnd/Multiplayer/LobbyTypes.lua` | 66 | ServerType / GameModeTypes 映射 |
| `Debug/Player.ltp` | 977 | 玩家资源/科技/文化/时代分真实调用 |
| `Debug/City.ltp` | 1145 | 城市属性/人口/队列/区域真实调用 |
| `Debug/Unit.ltp` | 519 | 单位伤害/经验/移动恢复真实调用 |
| `Debug/Map.ltp` | 586 | 视野/揭示全图/观察者真实调用 |
| `Debug/Autoplay.ltp` | 218 | AutoplayManager 全 API |
| `Debug/Diplomacy.ltp` | 418 | 外交/战争/友谊真实调用 |
| `Debug/Players.ltp` | 86 | 玩家列表最全字段读法 |

---

## 9. 待运行时验证清单（优先级从高到低）

> **2026-10-26 更新**：第 5 条（`SetSlotStatus` 后是否必须 `UpdatePlayerCounts()`）已实测**不需要**——直接 `SetSlotStatus` + 设领袖/文明 + `BroadcastPlayerInfo` + `HostGame` 就能进局，详见 §10.3。其余各条仍未验证。

1. `UnitManager.CanStartOperation` 五个位置的参数契约（第 3 参地格对象 vs 坐标；第 4 参 `false` vs 参数表；第 5 参布尔 vs `OperationResultsTypes`）。
2. `CityManager.CanStartOperation(city, BUILD, params, true)` 第 4 参语义；`CityManager.CanStartCommand` 五参形式的顺序（`ProductionPanel.lua:1639-1640` 那种）。
3. `MOVE_TO` 只给 `PARAM_X`/`PARAM_Y` 时，是否会像 UI 路径一样自动处理"到达即攻击/换位"（官方 UI 路径要额外判断 `RANGE_ATTACK`/`SWAP_UNITS`）。
4. `PlayersVisibility[p]:ChangeVisibilityCount(index, delta)` 的可逆性与对 AI 视野的实际影响。
5. `SetSlotStatus` 改动后是否需要 `UpdatePlayerCounts()` 才能生效。
6. `Automation.Pause(true)` 的实际行为（暂停什么、如何恢复）。
7. `AutoplayManager.SetTurns(0)` 与 `-1` 的差异（官方两处说法不一致：`Automation_StandardTests.lua:325` 注释说 "A turn count of 0 means no turn limit"；而面板把 `-1` 当 "No limit"（`Debug/Autoplay.ltp:146-147`、`:157`）—— 需实测）。
8. `UI.RequestAction(ActionTypes.ACTION_ENDTURN)` 在 `REASON = "UserForced"` 下的差异（是否会跳过阻塞）。
9. `Network.LoadGame` 返回 `false` 之外，失败是否还有异步回调路径。
10. `Events.*` 中哪些在 `GameCore_Tuner` 态（FireTuner 面板）也能收到、哪些只在 InGame UI 栈里。

---

## 10. 运行实测记录（2026-10-26）

> 本节全部是**真机运行实测**：文明6 本体 + 外部脚本经 FireTuner 通道驱动。
> 与 §0–§9 的"官方文件静态核对"分属两类证据，引用时请保留【运行实测 2026-10-26】标注；换游戏版本 / Mod 组合 / 运行环境都需重测。

### 10.1 Tuner 通道：端口与帧协议【运行实测 2026-10-26】

- 端口：`127.0.0.1:4318`，**在主菜单即可连接使用**，不必先进对局。
- 帧格式（客户端 → 游戏）：

```text
+------------------+---------+----------------------+-----+
| u32 payloadLen   | i32 tag | utf8 payload         | NUL |
| (长度含结尾 NUL)  |         |                      |     |
+------------------+---------+----------------------+-----+
```

- 请求 tag：
  - `tag = 4` → `APP:<...>` / `LSQ:<...>`（应用信息 / 状态表查询）
  - `tag = 3` → `CMD:<state>:<lua 源码>`（在指定 state 中执行 Lua）
- 响应 tag 固定 `-1`；payload 以「一个字符 + NUL」开头区分类型：
  - `O\0` → 普通输出（print / 返回值文本）
  - `L\0` → 状态表（配合 `LSQ:`）
  - 失败 → 以 `ERR:` 开头的文本

最小交互原型（伪代码，**不是官方 API**）：

```text
send  tag=4  "LSQ:"                                   -> "L\0<状态表，31 项>"
send  tag=3  "30:GameConfiguration.SetToDefaults()"   -> "O\0..."
```

> 官方安装目录内**没有**这份协议的任何文档（对照 §2.1 的静态结论：脚本加载/通道在文件中不可见）。

### 10.2 状态表与"前端注入状态 30"【运行实测 2026-10-26】

主菜单下 `LSQ:` 返回 **31 项**状态表。与开局相关的条目（**本次实测表内编号**）：

| 编号 | 名字 | 说明 |
| --- | --- | --- |
| **30** | `FrontEnd` | **前端注入状态**：整套前端配置接口在这里可执行 |
| 24 | `MainMenu` | 主菜单本体；在这里发 `GameConfiguration` 类 Lua 会失败 |
| 20 | `FrontEndPopup` | 前端弹窗态 |
| 29 | `Test` | 测试态 |

- **要在主菜单开局，必须把 Lua 发到 state 30（`FrontEnd`）**：`GameConfiguration` / `MapConfiguration` / `PlayerConfigurations` / `Network.HostGame` 在该 state 下均可调用。
- **不要硬编码编号**：编号是"当前状态表内的下标"，进局后会变 —— 本次实测进局后 `GameCore_Tuner` 的编号是 `3`。正确做法：`LSQ:` 取表 → **按名字查编号** → 再发 `CMD:<编号>:<lua>`。
- 与 §0.3 的对照：`.ltp` 面板的 `<CompatibleStates>` 写的是**名字**（`MainMenu`/`InGame`/`GameCore_Tuner`）；实测证实这些名字确实对应 Tuner 状态表条目，并且"主菜单里没有 `GameCore_Tuner`"。

### 10.3 实测可用的新局 Lua（在 state 30 跑通，真的进了对局）【运行实测 2026-10-26】

可直接发到 state 30 的完整版本（每步均实测有效；参数值可按需替换）：

```lua
-- 1. 复位与规则集 / 地图 / 速度 / 难度
GameConfiguration.SetToDefaults();
GameConfiguration.SetRuleSet("RULESET_EXPANSION_2");
MapConfiguration.SetMapSize("MAPSIZE_TINY");
GameConfiguration.SetGameSpeedType("GAMESPEED_ONLINE");
GameConfiguration.SetHandicapType("HANDICAP_PRINCE");

-- 2. 取本地玩家槽（关键：可能返回 -1）
local pid = Network.GetLocalPlayerID();
if pid == -1 then pid = 0; end                 -- 主菜单下可能没有本地玩家，退化为 0 号槽

-- 3. 占槽 + 选领袖 / 文明（三件套缺一不可）
local pc = PlayerConfigurations[pid];
pc:SetSlotStatus(SlotStatus.SS_TAKEN);         -- 数值 3
pc:SetLeaderTypeName("LEADER_QIN");
pc:SetCivilizationTypeName("CIVILIZATION_CHINA");
Network.BroadcastPlayerInfo(pid);              -- 改完必须广播

-- 4. 其余槽位无需处理：实测默认已是 SS_COMPUTER（数值 1）
-- 5. 开局
Network.HostGame(ServerType.SERVER_TYPE_NONE); -- 实测返回 1
```

与静态来源（§1.1 / `Automation_StandardTests.lua:267-310`）的差异 —— **这些只有运行时才暴露**：

| 实测点 | 说明 |
| --- | --- |
| `Network.GetLocalPlayerID()` 存在、且可能返回 `-1` | 静态文件里没出现过该调用；主菜单下需退化为 `0` 号槽 |
| `SetLeaderTypeName` + `SetCivilizationTypeName` 必须成对显式调用 | 静态文件只有"改领袖需按特定顺序多次调用"的注释（`PlayerSetupLogic.lua:54-56`）；实测确认这套三件套 |
| `Network.BroadcastPlayerInfo(pid)` 必须调用 | 静态来源 `PlayerSetupLogic.lua:89`；实测确认是进局必需 |
| 其他槽默认就是 `SS_COMPUTER` | 与 §1.4 里"遍历真人槽改 AI"等价，但实测**不必要** |
| `Network.HostGame(...)` 返回 `1` | 静态文件只对 `Network.LoadGame` 判断返回 `false` |

### 10.4 枚举数值【运行实测 2026-10-26】

| 枚举 | 数值 |
| --- | --- |
| `SlotStatus.SS_OPEN` | 0 |
| `SlotStatus.SS_COMPUTER` | 1 |
| `SlotStatus.SS_CLOSED` | 2 |
| `SlotStatus.SS_TAKEN` | 3 |
| `SlotStatus.SS_OBSERVER` | 4 |
| `PlayerTypes.NONE` | -1 |

> 成员名的存在性由官方文件确认（§1.4、§2；`AdvancedSetup.lua:1383-1385`、`Automation_StandardTests.lua:128/135`、`Automation_StandardTestSupport.lua:40-45`【静态核对】）；**数值顺序是本次实测结果**。

### 10.5 进局后的状态与服务【运行实测 2026-10-26】

- 进入对局后状态表出现 `GameCore_Tuner`（本次编号 `3`），并同时出现 `LoadScreen` / `JoiningRoom` / `StagingRoom` 等服务条目。
- **地图生成完成的实测信号：`LoadScreen: OnLoadGameViewStateDone`** —— 看到它再去操作单位/城市/结束回合最稳。
- 与静态分层对照：官方脚本把流程分成 `PostGameInitialization`（对局初始化完、地形未生成）→ `GameStarted`（能看到地图）（`Automation_StandardTests.lua:313-316`、`:340-341`【静态核对】）；实测把"地形生成完毕"这一步落在 `LoadScreen: OnLoadGameViewStateDone` 上。

### 10.6 坑（必读）：进局后断开 Tuner，4318 可能不再监听【运行实测 2026-10-26】

- 实测现象（分段）：① 地图还在加载、或领袖介绍界面尚未跳过时断开，4318 会无监听或 connect 超时，此时确实连不上；② **等 `LoadScreen: OnLoadGameViewStateDone` 出现并用 Esc 跳过领袖介绍后，游戏会重新监听 4318，可以新建连接**；③ 对局稳定后反复 connect/close 实测 3 轮均成功。
- 结论：**不是"进局后永久失联"**。关键是等加载完成、跳过介绍，再带重试地连接；加载进行中不要抢连。
- 做法：
  1. 加载完成后先发一次 Esc（跳过领袖介绍），再以 2–3 秒间隔重试 `connect`；本仓库 `scripts/civ6_ops.py` 的 `connect_tuner_retry` / `start_game_flow` 已封装。
  2. 进局操作优先发到 `InGame` 状态（单位/城市 API 完整）；`GameCore_Tuner` 可读部分数据，但 `Unit:GetUnitType` 等在该上下文不可用（用 `UnitManager.GetTypeName`）。
  3. 对局中"每次操作开新连接"实测可用（3 轮），短命令可直连；需要长时间多步保持时再用常驻桥。
  4. `ERR:...` 与连接失败是两类问题：前者是 Lua 报错或 state 名字/编号不对，后者是通道/时机问题。
- 【运行实测】`civ6ctl launch --windowed` → `start`（自动等加载 + Esc + 重连）→ `probe` → `act found` → `act move` → `act endturn` → `shot` → `close` 流程已跑通；具体城市/坐标/回合数以本次对局为准，换机器、版本或 Mod 组合需重跑。


