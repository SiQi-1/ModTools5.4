---
name: civ6-ai-play
description: 用 FireTuner（127.0.0.1:4318）与窗口化启动让 AI 或脚本控制文明6实际对局：探测游戏与用户目录、启停 Mod 启用集、选择文明与领袖开局、移动单位、建城、结束回合、截图取证，并读取 Lua/Database/Modding 日志验收。适用于 Mod 自动测试、问题复现和无人值守检查；不替代 Mod 制作规则，也不修改游戏安装目录或绕过 Steam 校验。
---

# AI 控制文明6（窗口化 + FireTuner）

目标是把一次真实对局变成可重复、可取证、可还原的流程：**启动 → 配置 Mod → 开局 → 操作 → 截图 → 读日志 → 关闭**。命令返回、日志无错、状态读数、画面表现是不同层的结论，必须分开记录（见 [验收分层](#验收分层)）。

本技能随 ModTools 5.4 仓库使用，技能目录可整包复制（复制前删除 `scripts\__pycache__\` 等本地缓存）。运行时只依赖 Windows、Python 标准库和本机已安装的文明6；脚本不需要 PyQt，也不需要启动 ModTools GUI。

**关键架构（实机验证整理；换游戏版本或 Mod 组合需重测）。** FireTuner 是单连接 TCP：主菜单可直连；地图加载中或领袖介绍未跳过时连接不可用；**等 `LoadScreen: OnLoadGameViewStateDone` 出现并用 Esc 跳过领袖介绍后，4318 会恢复监听，可以重连**（对局稳定后可反复断开/重连）。`civ6ctl start` 已把「前端选文明/领袖 → `Network.HostGame` → 等加载 → Esc 跳过介绍 → 带重试重连」封装成一个命令。常驻桥 `civ6_bridge.py`（HTTP `127.0.0.1:8770`）只在需要长时间多步操作时使用；`civ6_tuner_gui.py`（自动化官方 FireTuner2 的 Lua Console）是备用通道。

## 适用场景

- **自动测试 Mod**：启用/停用指定 Mod、开新局、移动到触发点、截图并扫描日志，形成一次可复现的验收记录。
- **复现问题**：固定文明、领袖、地图、速度和种子，重复同一操作序列并保存日志。
- **让 AI 实际玩**：读取对局状态，操作单位移动、建城、生产和结束回合，观察 AI 与系统反应。
- **环境排查**：窗口/分辨率异常、Tuner 连不上、Mod 未生效、加载卡住。

不适用：制作或修改 `.CIV` 内容（先读 [规则正文](../RULES.md)、[统一工作流](../WORKFLOW.md) 与 [modgen 契约](../../modgen/AGENTS.md)）；修改游戏安装目录、Steam 文件或联网对战；长时间无人值守挂机。civ6_sdb_fix.py 是唯一会修改 Windows 系统文件的脚本（兼容性库 sysMerge.sdb），只应在用户明确同意时执行，且必须保留备份/可 restore。

> 不要和 ModTools 的 AI 控制接口混淆：`ModTools5.4.py --ai-port` 是对 ModTools GUI 发 HTTP 动作；本技能驱动的是**游戏本体**（FireTuner + 窗口），两者通道和失败原因不同。

## 安全与边界（先读再动手）

1. **必须窗口化**，不使用独占全屏。窗口可枚举 rect、可截图、可聚焦；独占全屏会破坏截图与后台操作，所以自动测试一律窗口化。分辨率与画质按目标机器能力选：脚本默认 1280×720 + 低画质档，运行吃力时继续降低窗口尺寸或画质，不要把某台机器的取值当成通用常量。测试前后查显卡温度与负载（NVIDIA 用 `nvidia-smi`，其他显卡用厂商工具），上限先与用户/机器约定；**接近上限就缩短单次测试或先退出降温，超过上限立即停止**，不要长时间挂机。改 `AppOptions.txt` 的 `[Video]` 段前先备份，结束时还原。
2. **先备份再改动**：`AppOptions.txt`、`GraphicsOptions.txt`（仅在必要时）和 `Mods.sqlite`。备份名带时间戳，恢复后读回核对；不要拿备份整文件覆盖用户期间手工改过的其他设置而不说明。
3. **不破坏用户启用集**：Mod 启停只改 `Selected=1` 组内 `ModGroupItems.Disabled`，不改组本身；游戏进程运行时拒绝写 `Mods.sqlite`；测试结束恢复测试前状态，或明确告知用户保留了哪些改动。
4. **同一时刻只允许一个 Tuner 客户端**：直连与常驻桥二选一，不要同时开（脚本直连、FireTuner 面板都算）。默认直连流程在「加载完成 + Esc 跳过介绍」后带重试重连；只有需要跨多步长时间保持连接时才 `civ6ctl.py serve` 起桥（HTTP `127.0.0.1:8770`）。关闭时用 `close`（需要时加 `--stop-bridge`）。
5. **测试后关闭游戏**：不留下后台游戏进程占用 `Mods.sqlite`、日志和显卡资源。关闭前先保存日志与截图；结束进程的方式见 [安全结束进程](references/troubleshooting.md#安全结束进程)，不结束 Steam。
6. **不猜状态名和 API**：Tuner Lua 状态分前端与对局，主菜单里没有 `GameCore_Tuner`；调用签名以 [Lua API 速查](references/lua-api.md) 或本机官方文件核对为准，未验证的点标「待验证」。
7. **产物留在工作目录**：截图、日志副本、Lua 脚本放 `modgen_work/<任务名>/` 或仓库外目录，不把单次测试产物写进工具仓库。

## 准备

- **游戏根与程序**：游戏安装根由 [环境与路径](references/environment.md) 的「路径探测」从 Steam 注册表/库配置解析，不要写死盘符或用户名；主程序为 `Base\Binaries\Win64Steam\CivilizationVI.exe`（DX11）与 `CivilizationVI_DX12.exe`（DX12），记录本次使用哪个。
- **用户目录**：`%LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VI\`，含 `AppOptions.txt`、`GraphicsOptions.txt`、`Mods.sqlite`、`Logs\`。
- **Tuner**：`AppOptions.txt` 的 `[Debug]` 段 `EnableTuner 1`；游戏在 `127.0.0.1:4318` 提供单连接 Tuner。主菜单可直连；开局后等加载完成 + Esc 跳过领袖介绍再重连（`civ6_ops.py` 已封装重试）。常驻桥 `civ6ctl.py serve`（HTTP 8770）仅在需要长时间保持连接时启用。主菜单与对局中的 Lua 状态表不同，进局后优先用 `InGame` 状态。
- **日志**：`Logs\Lua.log`、`Database.log`、`Modding.log`（另有 `Startup.log`、`Engine.log`、`Renderer.log`、`UserInterface.log`、`UIWarnings.csv`）。
- **Python**：优先仓库 `.venv\Scripts\python.exe`（3.13）；脚本只用标准库，截图在缺 Pillow 时降级 BMP。
- **备份与状态**：`civ6_game.py windowed` 把 `AppOptions.txt`/`GraphicsOptions.txt` 备份到 `%LOCALAPPDATA%\civ6_ai_play\`（`CIV6_AI_PLAY_STATE` 可覆盖）；`Mods.sqlite` 由 Mods 脚本另行备份。删除或清空这些目录前先确认已还原。

窗口化设置、分辨率建议、Steam 探测、截图方式与还原步骤全部在 [环境与路径](references/environment.md)。

**验证要求**：本技能只提供流程与判定方法，不附带任何一台机器的验收结论。实际使用时按 [验收分层](#验收分层) 六层逐项记录证据；换游戏版本、Mod 组合或机器都必须重跑，不能沿用他人机器或旧版本的通过记录。

## 标准流程

1. **环境检查**：`civ6ctl.py env` 看安装路径/用户目录/Tuner/运行状态；确认游戏未在运行，备份 `AppOptions.txt` 与 `Mods.sqlite`，确认 `EnableTuner 1`。
2. **配置 Mod**：`mods enabled` 看启用集，`mods backup` 备份后按需 `enable`/`disable`；游戏未退出时禁止写 `Mods.sqlite`。
3. **窗口化启动**：`launch --windowed` 备份选项、改窗口化（默认 1280×720 低画质）并启动；命令会等游戏窗口出现并等到主菜单 Tuner 就绪。
4. **选择文明/领袖/地图开局**：`start --leader LEADER_QIN --civ CIVILIZATION_CHINA ...` 自动完成前端注入、`Network.HostGame`、等待 `LoadScreen: OnLoadGameViewStateDone`、Esc 跳过领袖介绍、带重试重连，并返回 `GameCore_Tuner`/`InGame` 状态与首轮 `probe`；精确 Lua 签名见 [Lua API 速查](references/lua-api.md)。
5. **需要长时间多步操作时再起桥**：`civ6ctl.py serve`（HTTP `127.0.0.1:8770`）持有连接，后续命令会自动经桥；只做一次短流程不用起桥。
6. **读取状态与日志**：`probe` 读回合/玩家/单位/城市，同时 tail `Database.log`/`Lua.log`；加载卡住转 [加载卡住](references/troubleshooting.md#加载卡住)。
7. **操作对局**：`act move --x .. --y ..`、`act found`、`act endturn`；每次操作后 `probe` 复查状态变化。
8. **截图取证**：`shot --out ...` 在操作前后各截一次，保存窗口 rect、时间戳与操作说明；判读方式见 [截图与日志定位](references/troubleshooting.md#截图与日志定位)。
9. **Mod 与日志验收**：`logs enabled-mods`、`logs errors`、`logs tail --file Lua.log` 核对启用集与报错，再对照游戏内可观测效果。
10. **关闭与还原**：`close --stop-bridge` 退出游戏并结束桥；`restore-config` 还原选项；必要时 `mods restore` 还原启用集，记录最终状态。

每步的期望结果、失败信号和取证位置见下方命令速查与 references；不要跳过第 1、10 步。

## 测试 Mod（Lua / DLL / 自定义 UI）

启用 Mod、开一局，按 [验收分层](#验收分层) 分层取证（命令 → 连接 → 开局 → 操作 → Mod → 环境）；完整方法见 [Mod 测试方法](references/mod-testing.md)；需要对每条能力做属性/建筑/单位断言与面板截图时，用 [真实 Mod 运行时验证](references/mod-runtime-testing.md) 的模板与夹具（含 `tuner_eval.py` 与 DPI 点击脚本）。

- 玩法 Lua Mod：看 Lua.log 中 Mod 自己的打印与 Database.log 报错，用 tuner 对比修改前后状态。
- DLL Loader 插件 Mod：先确认 loader 日志与插件 OnLoad；若 loader 日志不生成且进程加载的 VERSION.dll 来自 `C:\WINDOWS\SYSTEM32`，可能是 Windows 兼容性库抢先加载了系统 VERSION.dll，用 `scripts/civ6_sdb_fix.py status/apply/verify` 诊断修复（apply 会改 sysMerge.sdb，需管理员，自动备份/可 restore；Windows 更新后重新 apply）。无法改系统时用 `scripts/civ6_inject.py` 注入（测试后删除注入文件与目录）。
- 自定义 UI Mod：用 tuner LSQ 找新增 Lua 状态，读 Controls 与全局 API，截图加坐标点击做真实交互，最后用控件状态或日志断言。

## 按阶段读取

- **测试 Mod（Lua / DLL 插件 / 自定义 UI）** → [Mod 测试方法](references/mod-testing.md)
- **建立可靠、可重复、防漏判的大型 Mod 测试工作流（能力组、判定标准、覆盖矩阵、Modifier/Requirement 知识库）** → [Mod 测试工作流](references/mod-test-workflow.md)
- **对已完成审查/修复的 Mod 做逐能力运行时断言、UI 截图与构建坑排查** → [真实 Mod 运行时验证](references/mod-runtime-testing.md)（含断言模板、测试夹具、DPI/弹窗/构建大小坑；含**看海 AI 自动对局**与**数据驱动 UI 动态测试**——看海需要外部工坊 Mod「上帝视角」，本项目不内置，未安装时提示用户订阅）
- **全自动执行：启动→夹具/断言→UI 截图→归档→关闭→图文报告** → [全自动测试工作流](references/auto-mod-test-workflow.md)（架构与 Harness API 契约；作者本地实现脚本未随包，可按文中架构自建，含夹具 Cookbook 与反模式）

- **环境、路径、窗口化、截图、还原** → [环境与路径](references/environment.md)
- **Tuner 连不上、启动失败、Mod 报错、加载卡住、GPU/窗口异常、日志定位、安全结束进程** → [排障](references/troubleshooting.md)
- **官方 Lua 调用点、函数签名、前端/对局状态差异、单位与城市操作** → [Lua API 速查](references/lua-api.md)（官方文件静态核对，标注证据等级）
- **官方自动化框架（Tests 表、PlayGame/HostGame/Autoplay 流程）与 Debug 面板清单** → [官方自动化与 Debug 面板](references/official-automation.md)（官方文件静态核对）

只读当前阶段需要的部分，不要一次加载全部参考。

## 验收分层

1. **命令层**：脚本退出码、`--help`、状态查询 JSON 正常。
2. **连接层**：常驻桥 `/health` 返回 `connected: true`（或直连 Tuner 握手成功），状态表可解析目标状态。
3. **开局层**：`Game`/`Players` 能读到目标文明、领袖、回合数和地图信息。
4. **操作层**：请求返回后复查状态变化（单位坐标、城市数量、生产项、回合数）。
5. **Mod 层**：`Modding.log` 启用集合符合预期、`Database.log` 无加载错误、`Lua.log` 无栈回溯，且游戏内能观察到目标效果。
6. **环境层**：关闭后游戏进程退出、常驻桥已结束、`Mods.sqlite` 与选项文件已还原，用户既有启用集未被破坏。

只完成前几层就写清「已完成/未完成」，不能把静态检查或模拟结果写成实机验收。

## 命令速查

统一入口 `skills\civ6-ai-play\scripts\civ6ctl.py` 覆盖整条流程；需要单独调试时再调用下面的模块脚本。子命令与参数以 `--help` 为准。

```powershell
# 环境自检：安装路径、用户目录、日志、Mods.sqlite、Tuner 可达性、运行状态
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6ctl.py env

# 常驻桥：前台阻塞运行，放另一个终端/后台任务；HTTP 127.0.0.1:8770
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6ctl.py serve

# 备份配置 → 窗口化 → 启动并等待游戏窗口（Tuner 可能再等几十秒）
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6ctl.py launch --windowed --exe dx12

# 新开对局：前端注入领袖/文明并 HostGame，等待加载进对局
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6ctl.py start --leader LEADER_QIN --civ CIVILIZATION_CHINA --ruleset RULESET_EXPANSION_2 --map-size MAPSIZE_TINY --speed GAMESPEED_ONLINE

# 读取对局状态 / 操作（move|found|endturn|quit|probe）
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6ctl.py probe
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6ctl.py act found
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6ctl.py act move --x 10 --y 10
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6ctl.py act endturn

# 截图取证（默认查找 CivilizationVI* 窗口）
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6ctl.py shot --out modgen_work\ai-play\shot.png

# 对常驻桥执行任意 Lua（识别 Mod 全局/UI 状态、断言属性）：--state <状态名或索引>
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\tuner_eval.py --state GameCore_Tuner "print('hi')"
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\tuner_eval.py --states

# DPI 感知鼠标点击（高 DPI 下必须；用 civ6_win.py rect --json 的 dpi_scale 判断；坐标为“窗口截图坐标 + 窗口左上角”）
powershell -File skills\civ6-ai-play\scripts\click_dpi.ps1 -X <x> -Y <y>

# Mods.sqlite 与日志：写 Mods.sqlite 前游戏必须已退出；不建议 --force
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6ctl.py mods enabled
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6ctl.py logs errors
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6ctl.py logs enabled-mods

# 退出游戏（并结束桥）与还原启动前的选项文件
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6ctl.py close --stop-bridge
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6ctl.py restore-config
```

`serve` 是前台阻塞进程，不要和后续命令挤在同一个前台窗口；结束桥用 `civ6_bridge.py stop`，或 `close --stop-bridge`。

**GPU 温度/负载自检**（每轮测试前后各一次；上限按用户/机器约定，接近上限就缩短测试，超过立即退出）：

```powershell
# NVIDIA 显卡；其他显卡用厂商工具或系统监视器
nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,power.draw --format=csv,noheader
```

窗口化低画质仍接近上限时，继续减小 `--width/--height` 或降低画质档位（尺寸不超过桌面分辨率）。

分模块脚本（单独调试或排障时使用）：

```powershell
# Tuner 直连：仅在桥未运行时短连接使用（桥运行中直连会抢连接）
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6_tuner.py states
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6_tuner.py eval --state GameCore_Tuner --lua "print('@@ok')"

# 常驻桥：健康检查 / 状态 / 停止
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6_bridge.py health
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6_bridge.py stop

# 启动/窗口/对局/操作（civ6ctl 的底层实现）
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6_game.py --help
# civ6_ops.py 无 CLI，供 import：start_game_flow / Session.probe/act / connect_tuner_retry

# 备用通道：自动化 FireTuner2 GUI 的 Lua Console（状态选择 + 执行 + 读输出）
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6_tuner_gui.py status

# 窗口/截图、Mods.sqlite、日志模块
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6_win.py --help
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6_mods.py --help
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6_logs.py --help

# Windows 兼容性库修复（标准 version.dll 被 system32 VERSION.dll 抢占时；改 sysMerge.sdb，需管理员，自动备份/可 restore）
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6_sdb_fix.py status
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6_sdb_fix.py apply --yes
.venv\Scripts\python.exe skills\civ6-ai-play\scripts\civ6_sdb_fix.py verify
```

检索本技能资料：`python -m modgen.cli skill "AI 控制文明6 FireTuner 窗口化" --plan`。

## 与 ModTools 的关系

本技能不生成也不修改 `.CIV`。Mod 内容仍按 [统一工作流](../WORKFLOW.md) 与 [modgen 契约](../../modgen/AGENTS.md) 制作、生成和构建；技能只负责把已部署的 Mod 放进游戏实际跑一遍。游戏内测试通过后再回写验收记录，不把测试脚本当成 Mod 源码或生成器输出。
