# 在真实 Mod 上做运行时验证（实机验证整理）

本页记录“审查/修复完成之后，如何把 Mod 放进真实对局逐项验证”的通用方法，来源是一次完整的『审查 → 修复 → 构建 → 实机验证』项目（项目细节只留仓库外 `local_notes/`，不随包）。它补充 [Mod 测试方法](mod-testing.md) 的通用取证方法，重点在**断言驱动**与**可复现的测试夹具**；下文带【实测】标记的行为结论来自特定游戏版本/Mod 组合，换版本需重测。

## 1. 四层证据，不要混写

| 层 | 证据 | 说明 |
|---|---|---|
| 数据层 | `GameInfo.*` 读到真实加载后的行（不是生成 SQL） | 证明“数据已进引擎”，不证明玩法正确 |
| 逻辑层 | Mod 自己的 GP 状态里执行 Lua，断言玩家属性/建筑/单位/计数器 | 证明“代码路径按预期执行” |
| 表现层 | 打开对应 UI 状态截图 | 证明“玩家看得到”，不证明规则正确 |
| 流程层 | `Lua.log` / `Database.log` / `Modding.log` 与构建产物哈希 | 证明“加载、构建、部署一致” |

结论必须写清哪一层通过；只有数据层+逻辑层+表现层都通过，才能把一条能力写成“实机验证通过”。

## 2. 找到 Mod 自己的 Lua 状态与入口

- 常驻桥：`civ6_bridge.py serve`（HTTP 8770），再 `bridge states` 列出全部状态。
- Mod 的 GP 状态通常直接以文件名出现（如 `..._Scripts`），在里面可以调用该文件定义的全局函数/表（如 `MyMod`、`Ability` 等，按 Mod 源码命名）。
- UI 状态名可能被截断（多个同名），用**状态内的 `ContextPtr:GetID()`** 识别，再打开面板：

```lua
-- 在候选状态中执行
print(tostring(ContextPtr:GetID()))
ContextPtr:SetHide(false)
if Controls.MainContainer then Controls.MainContainer:SetHide(false) end
```

- 逐个面板识别后把 state 索引记成表，后续截图不再猜。

## 3. 断言模板

统一用安全的取值包装（未设置属性返回 0 个 Lua 值，`tostring` 会报 `bad argument #1`）：

```lua
local function s(v) if v == nil then return 'nil' end return tostring(v) end
print('value', s(Players[0]:GetProperty('<Mod 属性键>')))
```

常用可断言对象：

- 玩家属性：`GetProperty/SetProperty`（键名以 Mod 源码为准）。
- 城市/玩家建筑：`city:GetBuildings():HasBuilding(index)`、`city:GetDistricts():HasDistrict(index)`。
- 单位/能力：`unit:GetType()`、`unit:GetAbility()`。
- 资源：`player:GetResources():GetResourceAmount(index)` / `HasResource`。
- 全局参数：`GameInfo.GlobalParameters['Key'].Value`。
- 数据库落地：`GameInfo.Modifiers/ModifierArguments/Requirements/TypeTags/Improvement_Tourism/Improvement_ValidTerrains` 等。

“修复项落地”优先用数据库断言；“玩法效果”再用属性/建筑/单位断言。

## 4. 可复现的测试夹具

常规动作可用 MCP 工具完成（`unit_action`/`set_city_production`/政策/总督/宗教/外交等，见 [MCP 工具速查](mcp-tools.md)）；需要 WorldBuilder 造物、属性/参数注入或自定义 UI 状态时仍用下面的 tuner Lua。

### 4.1 建城、授予科技/市政

```lua
WorldBuilder.CityManager():Create(0, x, y)                 -- 城市最小间距 4，3 环内会静默失败
player:GetTechs():SetTech(GameInfo.Technologies['TECH_X'].Index, true)
player:GetCulture():SetCivic(GameInfo.Civics['CIVIC_X'].Index, true)
```

### 4.2 正常建造区域（推荐）

`WorldBuilder.CityManager():CreateDistrict` 对自定义区域可能静默失败且不触发区域修饰器；**用生产队列**：

```lua
city:GetBuildQueue():CreateIncompleteDistrict(districtIndex, plotIndex, 100)
city:GetBuildQueue():FinishProgress()
```

### 4.3 总督

```lua
-- 在 UI 状态执行
UI.RequestPlayerOperation(0, PlayerOperations.APPOINT_GOVERNOR, {[PlayerOperations.PARAM_GOVERNOR_TYPE]=idx})
UI.RequestPlayerOperation(0, PlayerOperations.ASSIGN_GOVERNOR, {[PlayerOperations.PARAM_GOVERNOR_TYPE]=idx, [PlayerOperations.PARAM_CITY_DEST]=cityID})
UI.RequestPlayerOperation(0, PlayerOperations.PROMOTE_GOVERNOR, {[PlayerOperations.PARAM_GOVERNOR_TYPE]=idx, [PlayerOperations.PARAM_GOVERNOR_PROMOTION_TYPE]=promoIndex})
```

总督“就职”需要若干回合，`HasEstablishedShowGovernor`/`IsEstablished` 可作为门槛断言。

### 4.4 信仰购买

```lua
-- UI 状态
local params = {}
params[CityCommandTypes.PARAM_UNIT_TYPE] = GameInfo.Units['UNIT_X'].Hash
params[CityCommandTypes.PARAM_MILITARY_FORMATION_TYPE] = MilitaryFormationTypes.STANDARD_MILITARY_FORMATION
params[CityCommandTypes.PARAM_YIELD_TYPE] = GameInfo.Yields['YIELD_FAITH'].Index
CityManager.RequestCommand(city, CityCommandTypes.PURCHASE, params)
```

必须配**对照**（没有对应修改器的城市同参数购买应失败），否则无法区分“效果生效”与“通用购买本来就允许”。

### 4.5 单位与改良（截图用）

- `WorldBuilder.MapManager():SetImprovementType(plot, improvementIndex, playerID)` 可直接放改良并渲染。
- `UnitManager.InitUnit` 在部分环境返回成功但单位坐标 `-9999`（未落地）【实测，部分环境】；单位截图优先走正常生产路径。
- `UI.LookAtPlot(x, y)` 聚焦相机（UI 状态）。

## 5. UI 交互与截图

- **DPI**：高 DPI 缩放下（用 `civ6_win.py rect --json` 读 `dpi_scale`），PowerShell 未声明 DPI 感知时 `SetCursorPos` 会偏移。点击脚本先 `SetProcessDPIAware()`；坐标 = 窗口截图坐标 + `GetWindowRect` 左上角。
- **原生弹窗**：Eureka/Boost 等会盖住 Mod 面板；用 `SendKeys {ENTER}` / `{ESC}` 关闭后再截图。
- **面板内容为空**：直接 `SetHide(false)` 只能证明外观；要验证数据绑定需先制造数据（开城、给任务、触发 Mod 系统状态等）。【实测：部分注入 UI 需走真实点击/`DoLeftClick()` 才会执行 `Refresh()`】
- 每个关键状态至少两张图（前/后），文件名带时间戳与场景标签。

## 6. 连接与回合

- Tuner 单连接：桥/MCP/直连三者只开一个；用 MCP 前先 `civ6_bridge.py stop`，回合交接后再恢复。
- 回合：可用 MCP `end_turn`（带 blocker 处理与快照，需写 5 个反思字段）或 `civ6ctl act endturn`；Tuner 本身没有 EndTurn API。
- 回合推进后注意“同回合不重算”的产出：百分比产出建议跨回合对比。

## 7. 构建/部署常见坑

| 现象 | 根因 | 处理 |
|---|---|---|
| `Modding.log: Invalid file reference in action` | 构建临时目录用 8.3 短路径（`ADMINI~1`），modinfo `<Files>` 写成 temp 相对路径 | 构建脚本用长路径 `C:\Users\<user>\AppData\Local\Temp\...`；检查 modinfo 无 `Temp/`、无 `../` |
| 启动卡住 `CheckShaderDepotManifest` | Steam 仍跟踪上一轮游戏/BugReporter 进程 | 结束残留进程；必要时重启 Steam 再启动 |
| 部署后哈希不一致 | 复制/生成中断或旧文件残留 | 部署脚本全量 SHA-256 对比；旧目录移出 Mods 避免同 GUID 双份 |
| `.CIV` 被工具重新保存后字段变化 | 编辑器保存会丢弃 null/空字段并规范化子表 | 语义计数不变即可；保留 `.CIV.bak` 回溯 |

## 8. 收尾

- 归档日志与截图到本次任务工作目录（如 `workspace/scratch/<任务>/logs/<时间戳>-<标签>/`、`workspace/scratch/<任务>/screenshots/<时间戳>-<标签>/`），不写进工具仓库。
- 收尾按 [SKILL](../SKILL.md) 的「关闭与还原」流程执行：退出游戏、释放桥/直连、还原 AppOptions/GraphicsOptions；测试期间临时禁用/启用的 Mod 要恢复，还原后读回核对。
- 把结果写进本次任务的结果文件（滚动表），报告只引用汇总，不逐条复制日志。

## 9. 看海：让游戏内 AI 自动跑对局（动态测试）

**前置**：工坊上的「上帝视角 / God's perspective」类观察 Mod（workshop `2309132864`，GUID `F749E5C5-C38E-E837-76CF-FC47EAEE5F52`；工坊信息可能变化）。本技能/仓库**不内置**、不随包提供该 Mod；用户未安装时提示先订阅，否则缺少这一种测试方法。

方法：

1. 启用被测 Mod + 外部观察 Mod（`civ6_mods.py enable <GUID> --exact`，Mods.sqlite 自动备份）。
2. 启动窗口化、正常开局（本地玩家选要测的 Mod 领袖）。
3. 在 `InGame` 状态执行：
   ```lua
   AutoplayManager.SetObserveAsPlayer(PlayerTypes.OBSERVER)
   AutoplayManager.SetReturnAsPlayer(0)
   AutoplayManager.SetTurns(-1)          -- 持续；正数=只跑 N 回合
   AutoplayManager.SetActive(true)
   ```
   键盘 `A` 也可开关，`H` 隐藏界面。**`SetTurns(n)` 会限制总回合数**，误设会导致自动对局提前停止。
4. 加速：外部观察 Mod 提供 Z（科技）/X（市政）/C（金币信仰使者）/B（伟人总督点）/N（完成生产）/P（人口）/M（单位移动经验）等作弊键；这些属于该 Mod，不是被测 Mod 内容。**按键依赖该外部 Mod 的版本，以该 Mod 说明为准**【实测，换版本重测】。
5. 观察：`Lua.log` 中 Mod 的回合摘要、`Runtime Error`、`[Core] applied` 等日志；停止后通过桥读取各玩家状态（城市数、Mod 系统状态、建筑、总督点）。
6. 停止：`A` 或 `AutoplayManager.SetActive(false)`；恢复被启用的外部 Mod，再关闭游戏。

**能测/不能测**：AI 会积累资源、造区域/建筑、招募总督、结算数据驱动产出；**AI 不会使用 Mod 新增 UI**（需要玩家主动触发的面板/按钮/领奖），这些必须用下面的脚本驱动（见 §10）。多人远端玩家不在看海覆盖范围内。

## 10. 数据驱动的 UI 动态测试（初始面板之外）

直接 `ContextPtr:SetHide(false)` 只能截外观，**不会执行面板的 `Refresh()`**，数据仍是空的。正确做法：

1. 打开 UI 状态，找到 LaunchBar 按钮控件并调用它的真实点击：
   ```lua
   local stack = ContextPtr:LookUpControl('/InGame/LaunchBar/ButtonStack')
   for _,ch in ipairs(stack:GetChildren()) do
       local ok,id = pcall(function() return ch:GetID() end)
       if ok and id == '<ButtonID>' then ch:DoLeftClick() end
   end
   ```
   `DoLeftClick()` 是可靠的“脚本点击”；合成鼠标点击（SendInput/`mouse_event`）对部分注入 UI 不生效【实测，特定 loader/Windows 版本下观察】，所以能用控件状态/后端 API 断言时优先不用鼠标注入。
2. 构造真实数据：
   - 战略层：GP 状态 `player:GetDiplomacy():SetHasMet(minorID)` 遇见城邦；`WorldBuilder.CityManager():Create(playerID,x,y)` 建城；`UI.RequestPlayerOperation(...)` 任命/晋升总督。
   - Mod 内部：调用 Mod 自己的 GP 公共函数/属性（`<Mod>.<系统>:<方法>`、物品属性 `<Mod 属性键>`；键名/方法名以 Mod 源码为准）。
3. 截图前后状态：面板初始空态 → 注入数据后 → 动作后（如购买/领取）。
4. 断言：购买记录属性、日志 `applied/ready/accepted`、计数与资源变化；两者一致才算通过。

**踩坑记录（实测经验，换版本重测）**：
- 直接 `SetHide(false)` 面板空白 → 必须 `DoLeftClick()`（它会走 `Open()`→`Refresh()`）。
- `SetHasMet` 在 GP 状态调用才稳定；UI 侧读同一状态。
- 领奖前必须有城市（`G.CanOffer` 在无城市时直接拒绝 `#offers==0`）。
- 用 `GetProperty` 读未设置属性返回 0 个值，先判 nil 再 tostring。

## 11. GP 与 UI 上下文的类型差异（动态测试高发）

同一 API 在不同上下文可能返回不同类型【实测，换版本重测】。实例：

```lua
-- GP 状态里 GameConfiguration.GetGameSpeedType() 返回 hash（数字），不是 "GAMESPEED_ONLINE"
local speed = GameConfiguration.GetGameSpeedType()
local row = GameInfo.GameSpeeds[speed]   -- hash 索引可用；不要用字符串比较
```

用字符串比较 hash 会永远匹配不到 → 静默回退到默认值（如伤害/价格回退 1.0），表现为「UI 显示与实际扣费不一致」。**凡是“UI 显示与实扣/实际数值不一致”，优先怀疑 GP/UI 的类型与上下文差异**。

其他常见差异：`GetCivilizationType()` 在 GP 可能不可用（用 `PlayerConfigurations` 或属性）；`city:GetDistricts()` 的集合方法在 GP/UI 不同（`HasDistrict/GetDistrictByType` 在 GameCore，`Members()` 在 UI 脚本常见）。遇到 nil 方法先小脚本探测，不要假设。

## 12. 最小可复现示例（看海）

```powershell
# 启用外部看海 Mod（已安装时；GUID 见 §9 前置，工坊信息可能变化）
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6_mods.py enable F749E5C5-C38E-E837-76CF-FC47EAEE5F52 --exact --yes
# 启动 + 开局（civ6ctl / 自建测试脚本）
# 桥
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6_bridge.py serve
# 启动自动对局
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\tuner_eval.py --state InGame "AutoplayManager.SetObserveAsPlayer(PlayerTypes.OBSERVER); AutoplayManager.SetReturnAsPlayer(0); AutoplayManager.SetTurns(-1); AutoplayManager.SetActive(true)"
# 等回合推进后，读日志与状态
# 停止后记得禁用外部 Mod、关闭游戏

# 读 Mod 全局 / 动态打开面板（不要用 SetHide，走 DoLeftClick）
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\tuner_eval.py --state <Mod_GP_state> "print(type(<Mod 全局表>))"
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\tuner_eval.py --state <panel_idx> "local s=ContextPtr:LookUpControl('/InGame/LaunchBar/ButtonStack'); for _,ch in ipairs(s:GetChildren()) do local ok,id=pcall(function() return ch:GetID() end); if ok and id=='<ButtonID>' then ch:DoLeftClick() end end"
```
