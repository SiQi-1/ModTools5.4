# 文明6 Lua API 速查（官方文件静态核对 + 真机运行实测） — 读状态

> 分册：由 [lua-api.md](lua-api.md) 按主题拆出；覆盖 2. 对局中：读状态、2.1 全局入口对象、2.2 Game.* 观测到的成员【静态核对】、2.3 Player 对象（`Players[id]`）观测成员、2.4 城市 / 单位对象集合遍历、2.5 Map / 视野 / GameInfo / Locale、2.6 NotificationManager（回合阻塞/通知）。触发：读取玩家/单位/城市/外交状态时。

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

