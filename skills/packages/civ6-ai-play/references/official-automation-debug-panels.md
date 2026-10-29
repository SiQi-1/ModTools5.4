# 文明6 官方自动化测试与 Debug 面板（结构 + 可借鉴点 + 运行实测补充） — 脚本/Debug 面板

> 分册：由 [official-automation.md](official-automation.md) 按主题拆出；覆盖 8. 其余 Automation_*.lua 脚本职责、9. 能借鉴到"AI 控制游戏 / Mod 测试"的点、9.1 直接可复用的设计、9.2 不要照抄的地方、9.3 "Mod 自动测试"最小可行流程（由官方拼装）、10. Debug/*.ltp 面板全清单（数量随安装版本变化）、10.1 面板元数据、10.2 按能力分类（做验证/取证时按需挑面板）、10.3 两个特别有用的面板、11. .ltp 文件结构（自己写面板时照这个来）。触发：查其余 Automation 脚本、可借鉴点、Debug 面板与 ltp 结构时。

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

