# 文明6 Mod 全自动测试工作流（auto-mod-test-workflow）

> 本流程由一次真实项目的自动化落地整理：一条命令完成「启动 → 开局 → 自动夹具/断言 → UI 截图 → 归档 → 关闭」，并生成图文测试报告。换游戏版本、Mod 组合或机器都需重测。
> 本文件是 [mod-test-workflow.md](mod-test-workflow.md)（策略/判定/覆盖）与 [mod-runtime-testing.md](mod-runtime-testing.md)（运行时断言/夹具）的**自动化执行层**；三者配合使用。
> **脚本未随包**：本文的编排脚本与 harness 属作者本地历史工作流，本技能 `scripts/` 只有 `civ6*.py`、`click_dpi.ps1`、`tuner_eval.py`。可按 §2 架构自建等价 harness；示例中的 `workspace/scratch/<任务名>/...` 均为占位路径（`workspace/mods/` 已 gitignore，只在本机存档，不随包）。

## 1. 适用与前置

- 适用：已构建/部署到用户 Mods 目录、可在本机开局的文明6 Mod（Lua/UI/Data 混合）。
- 前置：Windows、窗口化配置、`EnableTuner 1`、仓库 `.venv`、可用的 Python 标准库；Mod 已启用。
- 启动前预检：同一 ModId 是否有多份 modinfo、Mods 目录是否残留旧副本；有冲突先清理（否则可能加载到旧构建）。
- 不适用：联机、修改游戏安装目录、无 Tuner 的 Store 版（需另寻通道）。

## 2. 架构

自动化层按「一条命令编排 + 分步骤脚本 + harness 断言 + 报告汇总」分层。下图为**架构示意**，脚本需按本节自建（作者本地实现未随包）：

```text
workspace/scratch/<任务名>/test/scripts/
├─ run_session.ps1                 编排：一条命令跑完整个会话
│   ├─ launch-windowed             窗口化 + 启动
│   ├─ wait-main-menu              等 Tuner/主菜单就绪
│   ├─ start-game                  注入 bEnableTuner/bDebugMenu + HostGame + Esc + 重连
│   ├─ run_<feature>_suite.py      自动场景（自建 harness）
│   │    ├─ ensure_bridge()        复用/拉起 civ6_bridge.py serve（8770）
│   │    ├─ fixture helpers        建城/生成单位/宣战/攻击/回合/面板
│   │    ├─ checks[]               断言 + evidence + 截图
│   │    └─ result.json / summary.md
│   ├─ archive-logs                归档 Lua/Database/Modding 日志
│   └─ close-restore               退出游戏、释放桥、还原选项
└─ report_builder.py               汇总 sessions + 截图 + findings → 图文报告（可选）
```

## 3. 一条命令（示例）

下例中的路径与脚本名均为占位符，需按 §2 自建：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File `
  workspace\mods\<任务名>\test\scripts\run_session.ps1 `
  -Leader <LEADER_TYPE> -Civ <CIVILIZATION_TYPE> `
  -Suite run_<feature>_suite.py -Label <标签>
```

单独重跑某个场景（游戏已启动时）：

```powershell
.venv\Scripts\python.exe workspace\mods\<任务名>\test\scripts\run_<feature>_suite.py
```

报告生成（自建脚本）：

```powershell
.venv\Scripts\python.exe workspace\mods\<任务名>\test\scripts\report_builder.py
```

## 4. Harness API（自建实现的能力契约）

方法名与参数是契约示意，按自建 harness 的实际命名实现：

| 能力 | 方法 | 说明 |
|---|---|---|
| 连接 | `ensure_bridge()` / `stop_bridge()` | 自动探测 8770，不存在则拉起桥 |
| 状态 | `game(code)` / `gp_eval(code)` / `ui_eval(code)` | GameCore_Tuner / Mod GP / InGame |
| 面板 | `panel_state("<Mod 状态名>")` | 用 `ContextPtr:GetID()` 自动定位状态索引 |
| 建城 | `found_city()` | 选中 settler → `FOUND_CITY` |
| 生成单位 | `spawn_unit(type, player, x, y)` | 优先生产队列；用 `WorldBuilder.UnitManager():Create` 走捷径后必须回读坐标确认（Unique/Air 单位可能失败） |
| 攻击 | `move_attack(unitID, x, y)` | 近战 `MOVE_TO` + `PARAM_MODIFIERS=ATTACK`（4 参 `CanStartOperation`）；远程用 `RANGE_ATTACK` |
| 宣战 | `declare_war(a,b)` | `PARAM_PLAYER_ONE/TWO` |
| 选择 | `select_city()` / `select_unit()` | UI 选择，用于面板截图 |
| 回合 | `end_turn()` | 停桥→`civ6ctl act endturn`→重启桥并**等待回合号前进**；检查返回码，失败不静默 |
| 断言 | `check(case, name, ok, expected, actual)` | 自动写入 result.json |
| 记录 | `record(kind, name, value)` | 非断言的证据/待确认事项 |
| 截图 | `screenshot(name)` | 统一命名/归档 |
| 汇总 | `summary(meta)` | 输出 `result.json` + `summary.md` |

## 5. 夹具 Cookbook（踩坑后的正确写法）

### 5.1 生成单位

```lua
WorldBuilder.UnitManager():Create(GameInfo.Units['UNIT_X'].Index, 0, x, y)
```

- ❌ `UnitManager.InitUnit` 会生成 `-9999` 无效单位【实测，部分环境】；`WorldBuilder.UnitManager():Create` 对 Unique/Air 单位在部分版本也可能失败（不落地）。**夹具造单位优先走生产/购买队列**；用捷径生成后必须回读坐标/owner 确认真的落地，不能只看 API 返回。
- ❌ 不要给蛮族（玩家 63）建城：实测（部分版本）会在回合处理时无 Lua 错误地崩溃退出（非法夹具）。

### 5.2 攻击

```lua
local t = {[UnitOperationTypes.PARAM_X]=x, [UnitOperationTypes.PARAM_Y]=y}
t[UnitOperationTypes.PARAM_MODIFIERS] = UnitOperationMoveModifiers.ATTACK
UnitManager.CanStartOperation(u, UnitOperationTypes.MOVE_TO, nil, t)  -- 必须 4 参
UnitManager.RequestOperation(u, UnitOperationTypes.MOVE_TO, t)
```

- 近战用 `MOVE_TO` + `PARAM_MODIFIERS=ATTACK`；**远程单位必须用 `UnitOperationTypes.RANGE_ATTACK`**——用近战的 `MOVE_TO + ATTACK` 驱动远程会 `CAN=false`【实测，换版本重测】。
- 3 参 `CanStartOperation` 会报 `Instance does not exist`。
- 攻击前若单位移动力为 0：`UnitManager.ChangeMovesRemaining(u, 2)` + `UnitManager.RestoreUnitAttacks(u)`；主动技能次数不足时同样先补次数（`ChangeActionCharges`）。
- 目标单位可先 `UnitManager.FinishMoves(enemy)` 静止，避免 AI 回合移动干扰 AOE 归因。

### 5.3 结束回合并等待

```python
h.end_turn()  # 内部：current_turn → stop bridge → civ6ctl endturn → serve → 等 turn+1
```

- 只 sleep 不等回合号会读到「AI 回合处理中」的中间态，trait modifier/回合事件可能尚未挂载。
- `end_turn` 必须检查 `civ6ctl` 的返回码，失败不可静默；必要时对 UI `ACTION_ENDTURN` 重试一次，回合号未前进即抛错。
- 等待超时（90s 为经验值，按机器/Mod 规模调整）说明有弹窗/加载卡住：先 `dismiss_popups()` 再重试，仍失败则截图并人工检查。
- 打开的自定义面板/弹窗会阻塞 `End Turn`（`IsTurnActive=false`、回合不前进），导致「回合开始」类效果误判；**看到回合不推进，先查 UI 面板，而不是判 Mod bug**。harness 的 `end_turn()` 已统一先 `dismiss_popups()`。

### 5.4 属性与状态读取

- Civ6 Lua 的 `tostring(nil)` 会报错；统一写 `local function sv(v) if v==nil then return 'nil' end return tostring(v) end`。
- 城市伤害读 `city:GetDistricts():GetDistrictByType(DISTRICT_CITY_CENTER,false):GetDamage(DefenseTypes.DISTRICT_OUTER)`；直接 `city:GetDamage` 在 GameCore 不可用。
- **城市产出优先从 UI 端读**：GP 端 `city:GetYield` 在部分上下文恒为 0；在 UI 状态 `CityPanel` 调用 `UpdateYieldData` 读 Food/Production/Gold/Culture/Science，或读 UI 端 `GetCityData(city)` 快照。tooltip 会显示「来自修正值」，用启用前后数值/文本对比。
- 未工作地块的 `GetYield`/`GetAppeal` 不重算：先让地块被工作或推进回合后再读。
- 任意官方面板函数都可用「拿到该 UI 状态后调用其全局函数」的方式读取（如 `CityPanel` 的 `UpdateYieldData`），避免 GP 端 API 缺失。

### 5.5 初始化时序

- Mod trait modifier 可能在开局/面板打开后才挂载：对「对象列表」断言先重试 10–20 次，仍为空则记 `DEFERRED`（附独立查询证据），不要直接判 FAIL。
- `run_once` modifier 若在目标对象（如首都）创建前结算，可能不补发；这是**真实问题候选**，不是测试瑕疵。

### 5.6 AI 看海 / 长时回归

内置 `AutoplayManager` 可直接在 Tuner 里做稳定性回归，无需外部工坊 Mod：

```lua
AutoplayManager.SetDisableAssertsForAutoplay(true)
AutoplayManager.SetTurns(60)
AutoplayManager.SetReturnAsPlayer(0)
AutoplayManager.SetActive(true)
-- 轮询 Game.GetCurrentGameTurn()；结束后 SetActive(false)
```

- 每 3–5 秒轮询回合号，直到 `turn >= start + N` 或 `IsActive()==false`；超时则强制关闭并记 partial。
- 断言：回合数推进、游戏进程存活、`Lua.log` 无新增 `Runtime Error`；记录 pPlot guard 触发次数。
- 建议至少 50–60 回合；短跑会漏掉后期才暴露的 `Map.GetPlot` nil 类崩溃。
- 在线速度下生产溢出会让百分比产出夹具不可区分（某项目示例 +55%）；测百分比产出前先确认游戏速度与溢出状态。

### 5.7 政策激活与政策效果测试

```lua
-- InGame(UI) 状态；GameCore_Tuner 里 RequestChangeGovernment/RequestPolicyChanges 为 nil
local c = Players[0]:GetCulture()
c:RequestChangeGovernment(GameInfo.Governments['GOVERNMENT_CHIEFDOM'].Hash)
-- 解锁方式按 Mod 设计（自定义解锁或正常市政）
c:RequestPolicyChanges({0,1}, {[0] = GameInfo.Policies['POLICY_<政策名>'].Hash})
-- addList 必须以槽位 index 为键；数组形式不会生效
```

然后 **结束一回合**，`IsPolicyActive(policy.Index)` 才为 true；`GetNumPolicySlotsOpen()` 用于确认空槽。

- 测单卡效果前先填满全部槽（不能只 `IsPolicyActive`）；选择可观测的载体（单位属性、金币、单位数、城市产出）；逐卡贡献可用「满槽值 ÷ 卡数」验证。
- 注意领袖/civ 前置：某些 Mod 能力要求特定领袖 + 文明组合，否则会被引擎拒绝；用 CIV/源码核对前置，不要假设任意组合都成立。

## 6. 判定模型

| 状态 | 含义 | 要求 |
|---|---|---|
| PASS | 期望=实际，含对象/属性/日志/UI 至少两类证据 | 写入 result.json |
| FAIL | 期望≠实际且可复现 | 保留日志/截图，进 FINDINGS |
| DEFERRED | 因夹具/时序/前置未满足，尚无结论 | 必须写原因与已做尝试 |
| UNVERIFIED | 本轮未执行 | 报告明确标出，不冒充通过 |

原则：**对象列表优先**（`GameEffects.GetModifiers()` 的 owner/active/definition 是主证据），Effect 行为只在自定义/语义不明时采样；官方 Effect 语义正确可信任。

### 6.1 证据纪律（通用）

- 禁止恒真断言：`True`、`len(x) >= 0`、`expected=actual=0`、空 `actual` 不得计 PASS；应改为可复算谓词 + 机器证据（日志/对象读回/路径）。
- 每个 session 写 `build id/hash、leader/civ、回合、测试时间`；`result.json` 必须能回答「哪条构建/哪一局」。
- 报告只引用同一轮 result 对应的截图/日志；禁止跨轮混用。
- 回合推进类断言必须确认回合号真的前进；失败不可静默。
- 修改/回退补丁后的验证失败要标 `FIX-ATTEMPT-FAIL`，不能混入当前产物 FAIL 统计。
- 旧 Mod 副本、第三方 Mod、Steam 残留运行状态必须写入环境记录并作为发布判据。

### 6.2 反复测不出的能力：及时搁置、转人工审核（硬规则）

- 同一能力/机制连续 **2–3 轮**尝试仍无法取得可判定结果时，**停止死磕**；
- 在 FINDINGS 标记 `DEFERRED（待人工审核）`，写清已排除项、可复现步骤、当前证据与建议；
- 继续测其它能力，不因单点阻塞整体进度；
- 例：某能力连续多轮尝试 trait modifier/Lua/城市事件等均无定论时，转人工复核并写清已排除项，而不是持续改实现；不要把项目版本号/编号写进通用规则。

## 7. UI 取证

1. `panel_state()` 定位状态；面板必须先 `Open()/Refresh()`。
2. 优先真实入口：LaunchBar 按钮 `DoLeftClick()`、城市面板 ActionStack、单位面板 StandardActionsStack。
3. 仅 `SetHide(false)` 会出现空白面板；必要时同时刷新。
4. 截图命名：`<label>/<panel>-<state>.png`；报告只选有内容/有状态的图，避免空面板。
5. 每个 UI 场景至少截图一张「有数据状态」，并在 result.json 记录路径。
6. 游戏自带弹窗（历史时刻/尤里卡/鼓舞/外交）：harness 用 `dismiss_popups()` 连发 ESC/ENTER 关闭，再截图/开 Mod 面板。
7. 模拟 WB_SELECT_PLOT 等 LuaEvent：在**注册 handler 的 Mod 状态**内用点号调用 `LuaEvents.<Event>.Call(args...)`；冒号调用会把 self 当首参，InGame 状态里该事件 Count=0，均会静默不触发。

## 8. 报告与经验回写

- 会话流水（`RUN_<日期>.md`）、问题清单（`FINDINGS.md`：ID/严重度/状态/证据/与审查报告关系）、截图与 result 资产放本次任务目录（如 `workspace/scratch/<任务名>/report/`）。
- 报告生成脚本属作者本地历史工作流（未随包）：按 §6 判定模型与本节约定汇总各 session 的 `result.json` + FINDINGS + assets → 图文报告（数据层表格 + UI 截图 + 冲突说明 + 未验证清单）。
- 每次修复/回归后重跑对应 suite，并更新 FINDINGS 与报告；不要只改一次报告不回归。

### 8.1 修复验证与回退

- 修 bug 后必须重新构建/部署并**用同一夹具回归**；修复验证失败时回退补丁，避免把死代码留在构建里。
- 事件回调（`PlayerTurnActivated`/`CityAddedToMap`）在 Tuner 观察下可能早于/晚于对象就绪；不要只凭「注册了事件」就认为会执行，必须加日志或写入可查询属性来证明执行。
- 启动脚本报「游戏进程已退出」但日志停在旧时间：先检查 Steam 是否卡住，按 [排障](troubleshooting.md) 重启 Steam 再重试，不要误判为 Mod 崩溃。

## 9. 反模式

- ❌ 只截菜单截图就宣称 UI 通过（空面板/被开场画面遮挡）。
- ❌ 用 `InitUnit` 或给蛮族建城造夹具。
- ❌ 用 `sleep` 代替「等待回合号/对象出现」。
- ❌ 把 `DEFERRED` 当 PASS，或把夹具崩溃当 Mod bug。
- ❌ 只按 modifier 逐行测，而不按能力组测对象/触发/负向/边界。
- ❌ 在报告里混用旧构建截图与新构建结论（必须标构建/日期）。

## 10. 参考实现

- 作者本地历史工作流（**未随包**）：一条命令编排脚本、按能力组拆分的 `run_<feature>_suite.py`、harness、报告生成脚本；本技能 `scripts/` 不含这些文件。
- 按 §2 架构自建等价实现即可；报告模板见 §6/§8。归档在本机 `local_notes/`、`workspace/mods/` 的项目记录不随包。
