# MCP 通道：civ6-mcp 工具速查与 Mod 测试用法

> 适用：客户端已注册外置 MCP 服务器 civ6-mcp（本仓库只登记、不内置，安装与许可见 [外置技能名单](../../../EXTERNAL_SKILLS.md#civ6-mcp)）。工具名以客户端实际展示为准：DSH 中形如 `mcp__civ6__<工具名>`，其他客户端可能带不同前缀。本文件是对其操作面的原创整理与 Mod 测试映射，不复制上游代码或 playbook；工具清单随上游版本变化（本版按 v1.1.11 核对），换版本按实际工具列表复核。

## 1. 定位与分工

MCP 负责**游戏内读状态、做操作、结束回合**；本技能脚本负责 **Mod 启停/备份还原、启动/关闭、日志与截图取证**。MCP 不处理 Mods.sqlite、不读 Lua/Database/Modding 日志、进不去自定义 UI 状态，也不涉及 DLL loader，因此**不能替代 Mod 生命周期与日志验收**。

| 任务 | 首选 |
|---|---|
| 查回合/单位/城市/地图/外交/科技/政策/伟人/议会/胜利 | MCP 读工具（§2） |
| 单位移动/攻击/建城、城市生产/购买、外交贸易、宗教、政策、总督、伟人、议会投票 | MCP 操作工具（§2） |
| Mod 启用/停用、备份与还原 | 本技能 `civ6_mods.py` / `civ6ctl mods` |
| 启动/关闭、窗口化、截图、日志扫描与还原 | 本技能脚本（MCP 的 launch/OCR 是另一套启动器，二选一） |
| Mod 专属断言（`GameEffects`、`GetProperty`、自定义 GP 状态） | MCP `run_lua`（§3）或本技能 `tuner_eval.py` |
| 自定义 UI 状态/Controls、DLL Loader | 本技能 tuner/bridge + 日志（MCP 无此能力） |

**单连接（最重要）**：MCP 服务器、本技能直连、`civ6_bridge.py` 常驻桥、FireTuner GUI 四者同一时刻只能有一个占用 4318。推荐交接顺序：脚本备份并启停 Mod → 脚本窗口化启动/开局 → 若 MCP 接管，先关脚本侧 bridge/直连与 FireTuner GUI → MCP 操作 → 退出 MCP（或游戏）→ 脚本收集日志/截图并还原。不要在 MCP 连接期间再跑 `probe`/`tuner_eval`/`shot` 之外的 Tuner 命令。

## 2. 工具速查（76 个）

> 参数为常用关键字，完整签名以客户端工具描述为准；`get_*` 只读。客户端前缀（如 `mcp__civ6__`）省略。

### 2.1 全局、回合与生命周期

| 用途 | 工具（关键参数） |
|---|---|
| 全局概览（回合/产出/研究/城市/单位数） | `get_game_overview` |
| 结束回合并写日记（5 个必填反思字段） | `end_turn(tactical, strategic, tooling, planning, hypothesis)` |
| 读回合日记 | `get_diary(last_n=5 / turn / from_turn / to_turn)` |
| 弹窗与阻塞 | `dismiss_popup`、`get_notifications`、`get_pending_diplomacy`、`get_pending_trades`、`skip_remaining_units` |
| 存档与恢复 | `list_saves`、`load_save(save_index)`、`load_game_save(save_name)`、`load_save_from_menu(save_name?)`、`restart_and_load(save_name?)`、`launch_game`、`kill_game` |
| 任意 Lua（Mod 断言逃生口） | `run_lua(code, context="gamecore"\|"ingame")` |

### 2.2 单位

| 用途 | 工具（关键参数） |
|---|---|
| 单位列表 | `get_units` |
| 单位动作 | `unit_action(unit_id, action, target_x?, target_y?, improvement?)`；action 含 move/attack/found_city/fortify/skip/improve/repair/remove_improvement/remove_feature/build_route/automate/heal/alert/sleep/delete/trade_route/activate/sacrifice_charges/teleport/spread_religion，`improvement` 仅 improve 用 |
| 晋升/升级 | `get_unit_promotions(unit_id)`、`promote_unit(unit_id, promotion_type)`、`upgrade_unit(unit_id)` |
| 寻路与建城建议 | `get_pathing_estimate(unit_id, target_x, target_y)`、`get_settle_advisor(unit_id)`、`get_global_settle_advisor` |
| 建造者任务 | `get_builder_tasks` |

### 2.3 城市

| 用途 | 工具（关键参数） |
|---|---|
| 城市列表/生产 | `get_cities`、`get_city_production(city_id)` |
| 设置生产 | `set_city_production(city_id, item_type=UNIT/BUILDING/DISTRICT/PROJECT, item_name, target_x?, target_y?)` |
| 购买 | `purchase_item(city_id, item_type=UNIT/BUILDING, item_name, yield_type=YIELD_GOLD/YIELD_FAITH)` |
| 人口与地块 | `set_city_focus(city_id, focus=food/production/gold/science/culture/faith/default)`、`get_purchasable_tiles(city_id)`、`purchase_tile(city_id, x, y)` |
| 区域/奇观选址 | `get_district_advisor(city_id, district_type)`、`get_wonder_advisor(city_id, wonder_name)` |
| 城市动作（攻击/保留/解放等） | `city_action(city_id, action=attack/keep/reject/raze/liberate_founder/liberate_previous, target_x?, target_y?)` |

### 2.4 地图与资源

| 用途 | 工具（关键参数） |
|---|---|
| 区域地形 | `get_map_area(center_x, center_y, radius=2)` |
| 战略地图/未开发资源 | `get_strategic_map`、`get_empire_resources` |

### 2.5 科技、市政与政府

| 用途 | 工具（关键参数） |
|---|---|
| 科技/市政树与当前研究 | `get_tech_civics` |
| 设定研究 | `set_research(tech_or_civic, category="tech"\|"civic")` |
| 政策与政府 | `get_policies`、`set_policies(assignments="0=POLICY_X,1=NONE")`、`change_government(government_type)` |
| 时代与献祭 | `get_dedications`、`choose_dedication(dedication_index)` |

### 2.6 外交与贸易

| 用途 | 工具（关键参数） |
|---|---|
| 外交关系/待处理会话 | `get_diplomacy`、`get_pending_diplomacy` |
| 外交动作 | `send_diplomatic_action(other_player_id, action)`、`respond_to_diplomacy(other_player_id, response=POSITIVE/NEGATIVE)`、`form_alliance(other_player_id, alliance_type=MILITARY/RESEARCH/CULTURAL/ECONOMIC/RELIGIOUS)` |
| 交易 | `get_trade_options(other_player_id)`、`propose_trade(other_player_id, ...)`、`respond_to_trade(other_player_id, accept)`、`get_pending_trades` |
| 和平 | `propose_peace(other_player_id)` |
| 贸易路线 | `get_trade_routes`、`get_trade_destinations(unit_id)` |

### 2.7 总督、宗教、城邦、伟人、议会、间谍、胜利

| 用途 | 工具（关键参数） |
|---|---|
| 总督 | `get_governors`、`appoint_governor(governor_type)`、`assign_governor(governor_type, city_id)`、`promote_governor(governor_type, promotion_type)` |
| 万神殿/宗教 | `get_pantheon_beliefs`、`choose_pantheon(belief_type)`、`get_religion_beliefs`、`found_religion(religion_type, follower_belief, founder_belief)`、`get_religion_spread` |
| 城邦 | `get_city_states`、`send_envoy(player_id)` |
| 伟人 | `get_great_people`、`get_gp_advisor(unit_index)`、`recruit_great_person(individual_id)`、`patronize_great_person(individual_id, yield_type)`、`reject_great_person(individual_id)` |
| 世界议会 | `get_world_congress`、`queue_wc_votes(votes=[{hash, option, target, votes}] 的 JSON)` |
| 胜利进度 | `get_victory_progress` |
| 间谍 | `get_spies`、`spy_action(unit_id, action=travel/COUNTERSPY/GAIN_SOURCES/SIPHON_FUNDS/STEAL_TECH_BOOST/SABOTAGE_PRODUCTION/GREAT_WORK_HEIST/RECRUIT_PARTISANS/NEUTRALIZE_GOVERNOR/FABRICATE_SCANDAL, target_x, target_y)` |

## 3. `run_lua`：Mod 专属断言

`run_lua` 只有两个上下文：`gamecore`（默认，只读状态查询，不能 `UI.*`/`UnitManager.*`）与 `ingame`（可发命令、访问 UI）。用 `print()` 输出并以可解析标记包裹；它只是把 Lua 送进游戏，**断言模板、证据分层仍按 [真实 Mod 运行时验证](mod-runtime-testing.md#3-断言模板) 与 [Mod 测试方法](mod-testing.md) 执行**。

```lua
-- gamecore：读 Mod 属性/计数（键名以 Mod 源码为准）
local p = Players[0]
local ok, v = pcall(function() return p:GetProperty('<Mod 键>') end)
print('@@mod_value=' .. (ok and tostring(v) or 'ERR'))
```

- modifier/对象列表断言沿用 `mod-runtime-testing.md` 的查询，不要另起一套口径。
- 自定义 UI 状态（Mod 的 LSQ 新状态、`Controls`）**不能**用 `run_lua` 进入；改用本技能 tuner/bridge 或 FireTuner GUI。
- 上游可用环境变量 `CIV_MCP_DISABLE_LUA` 移除该工具；被禁用时改用 `tuner_eval.py`（同一单连接规则）。

## 4. 对 Mod 测试流程的映射

| 标准流程步骤 | MCP 可用时 |
|---|---|
| 1–2 环境检查、Mod 启停/备份 | 本技能脚本（MCP 无 Mods.sqlite 能力） |
| 3 窗口化启动 | 二选一：本技能 `launch --windowed`（可备份/还原选项）或 MCP `launch_game` |
| 4 开局 | 优先本技能 `start`（确定性）；从固定存档复现时用 MCP `load_game_save`/`restart_and_load` |
| 6 读状态 | `get_game_overview`/`get_units`/`get_cities`/`get_diplomacy`/`get_tech_civics` 等；每条操作后用对应 `get_*` 复查 |
| 7 操作对局 | `unit_action`/`set_city_production`/`purchase_item`/外交/宗教/政策/总督/伟人工具；测试夹具类造物仍用 tuner Lua |
| 8 截图取证 | 本技能 `civ6_win.py`/`civ6ctl shot`（MCP 无通用窗口截图工具） |
| 9 Mod 与日志验收 | 本技能 `civ6-logs`/`civ6ctl logs`；MCP `get_diary`/JSONL 仅作补充 |
| 10 关闭与还原 | 本技能 `close`/`restore-config`/`mods restore` |

示例（一次简短行为测试）：脚本 `mods backup`→`mods enable`→`launch --windowed`→`start`；停脚本侧连接后交给 MCP：`get_game_overview`→`get_units`→`unit_action(found_city)`→`run_lua` 断言→`end_turn`→`get_diary`；回到脚本：`shot`→`logs errors`→`close`→`restore-config`/`mods restore`。

## 5. MCP 内置的回合/存档/观测能力（上游行为，换版本重测）

- **end_turn 状态机**：回合前后快照 diff；把弹窗、生产/研究、总督、晋升、政策、宗教、使者、献祭、城邦占领等软 blocker 自动分类，未知/无法自动处理的 blocker 报 hard（不会盲点）。Mod 自定义面板挡住回合时通常是 hard，按截图+人工处理，不要反复强推。
- **每回合自动存档**：Windows 下生成 `0_MCP_NNNN` 存档（保留最近若干个），`load_game_save`/`restart_and_load` 可回滚，适合固定场景复现与长跑恢复。
- **观测**：`~/.civ6-mcp/` 下有 diary/log/spatial JSONL，`get_diary` 可回读；它们是**补充证据**，正式验收仍以本技能的 `Lua.log`/`Database.log`/`Modding.log` 与截图为准。
- `end_turn` 的 5 个反思字段是必填项，写测试日记时如实填写，别用占位符冒充证据。

## 6. 局限与改用脚本的情形

- 无 Mods.sqlite/Modding.log 能力；无自定义 UI 状态；DLL Loader 无关；无窗口 rect/DPI/截图工具。
- 工具返回是面向 agent 的叙述文本，做机器断言优先用 `run_lua` 或本技能的原始 Lua/日志/JSON 输出。
- LLM 驱动非确定性、按 token 计费；可复现回归优先用脚本固定序列。
- 上游快速迭代（benchmark/编排为主），工具可能增删；锁定版本并记录 commit（见外置名单）。
- 不要从 WSL 运行；握手失败常需重启游戏；SDK 的 `FireTuner.exe` 必须先关闭。

## 7. 常见问题

| 现象 | 处理 |
|---|---|
| MCP 工具报连接失败/超时 | 游戏已启动并加载对局、`EnableTuner 1`、4318 有监听；关闭 `FireTuner.exe`、本技能 bridge/直连后重试 |
| 连上后工具无响应/状态错乱 | 确认只有一个 Tuner 客户端；断开其他客户端，必要时重启游戏 |
| 工具列表里没有 civ6 工具 | 客户端未注册 MCP：见 [外置技能名单](../../../EXTERNAL_SKILLS.md#civ6-mcp)；DSH 可用 `tools/install_skills.py --target dsh --link` 接入技能包 |
| 回合不推进 | 先 `get_notifications`/`dismiss_popup`/`skip_remaining_units` 处理软 blocker；Mod 面板/未知 blocker 报 hard 时截图转人工 |
| `run_lua` 不存在 | 上游设置了 `CIV_MCP_DISABLE_LUA`；改用 `tuner_eval.py` |
