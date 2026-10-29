# 文明6 Lua API 速查（官方文件静态核对 + 真机运行实测） — 踩坑/证据/实测

> 分册：由 [lua-api.md](lua-api.md) 按主题拆出；覆盖 7. 状态与 UI 上下文差异（踩坑清单）、8. 证据索引（被引用文件一览）、9. 待运行时验证清单（优先级从高到低）、10. 运行实测记录（2026-10-26）、10.1 Tuner 通道：端口与帧协议【运行实测 2026-10-26】、10.2 状态表与"前端注入状态 30"【运行实测 2026-10-26】、10.3 实测可用的新局 Lua（在 state 30 跑通，真的进了对局）【运行实测 2026-10-26】、10.4 枚举数值【运行实测 2026-10-26】、10.5 进局后的状态与服务【运行实测 2026-10-26】、10.6 坑（必读）：进局后断开 Tuner，4318 可能不再监听【运行实测 2026-10-26】。触发：查上下文差异、证据索引、待验证项与实测记录时。

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


