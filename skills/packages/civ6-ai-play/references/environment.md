# 环境、路径与窗口化

本文件记录「AI 控制文明6」所需的路径、窗口、Tuner 与还原方法。路径与配置因机器而异：先按「路径探测」确认，再按本文件操作；不要把示例值或某台机器的取值当成通用常量。

## 环境与路径（按机器核对）

| 项目 | 位置/取值 | 说明 |
|---|---|---|
| 游戏根 | `<Steam 库>\steamapps\common\Sid Meier's Civilization VI` | 由「路径探测」解析；只读，不修改 |
| DX11 主程序 | `Base\Binaries\Win64Steam\CivilizationVI.exe` | 备选；脚本默认 DX12，可用 `--exe dx11` |
| DX12 主程序 | `Base\Binaries\Win64Steam\CivilizationVI_DX12.exe` | 脚本默认；显卡/驱动不支持时用 `--exe dx11` |
| 用户目录 | `%LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VI\` | 配置、Mod 数据库、日志 |
| 选项文件 | `AppOptions.txt`、`GraphicsOptions.txt`、`UserOptions.txt`、`SoundOpts.txt`、`EOSOptions.txt` | 修改前备份 |
| Mod 数据库 | `Mods.sqlite` | 启用集与扫描文件；写前必须关闭游戏 |
| 日志目录 | `Logs\` | `Lua.log`/`Database.log`/`Modding.log`/`Startup.log`/`Engine.log`/`Renderer.log`/`UserInterface.log`/`UIWarnings.csv` 等 |
| Tuner 设置 | `AppOptions.txt` 的 `[Debug]` 段 `EnableTuner 1` | 未开启时先备份再补该行 |
| Tuner 端口 | `127.0.0.1:4318` | 游戏内 TCP 服务，单连接；主菜单可用，加载/领袖介绍期间暂不可用，加载完成 + Esc 后恢复 |
| 常驻桥（可选） | `127.0.0.1:8770`（HTTP） | `civ6_bridge.py` 持有唯一 Tuner 连接；仅长时间多步操作时用 |
| 窗口段 | `[Video]` 的 `RenderWidth`/`RenderHeight`/`FullScreen` | 自动测试改为 `FullScreen 0` + 窗口尺寸；改前备份、结束还原 |
| 官方自动化脚本 | `Base\Assets\UI\Automation\*.lua` | 静态分析来源，见 official-automation 参考；数量随游戏版本变化 |
| 官方 Tuner 面板 | `Debug\*.ltp` | FireTuner 面板，可核对真实 Lua 用法；数量随游戏版本变化 |
| 脚本状态与备份 | `%LOCALAPPDATA%\civ6_ai_play\`（`backups\`、`state.json`） | `civ6_game.py` 的选项备份/还原状态；`CIV6_AI_PLAY_STATE` 可覆盖 |
| Python | 仓库 `.venv\Scripts\python.exe`（3.11+） | 技能脚本只用标准库 |

`AppOptions.txt` 的 `[Video]` 段形如（值为占位示例，按本机探测填写）：

```ini
[Video]
RenderWidth <窗口宽>
RenderHeight <窗口高>
;0 : windowed, 1 : fullscreen, 2 : windowed with no title bar
FullScreen 0
UIUpscale 0.000000
```

`FullScreen`：`0` 窗口化、`1` 独占全屏、`2` 无边框窗口。自动测试改成 `0` 并设置渲染尺寸，结束后按备份还原。独占全屏（1）不用于自动测试。

### Mods.sqlite 结构（只读核对，以实际库为准）

- `ModGroups(ModGroupRowId, Name, CanDelete, Selected, SortIndex)`：Mod 组；当前选中组由 `Selected=1` 决定，组名不可假定。
- `ModGroupItems(ModGroupRowId, ModRowId, Disabled)`：组内条目；启用语义 = 所选组（`Selected=1`）内 `Disabled=0`。
- `Mods(ModRowId, ScannedFileRowId, ModId, Version)`、`ModFiles(FileRowId, ModRowId, Path)`、`ScannedFiles(ScannedFileRowId, Path, LastWriteTime)`：Mod 识别与文件路径。
- 组内条目数与启用数随用户 Mod 库变化；脚本应动态读取，不假设数量。

启停 Mod 的正确做法：只改所选组内的 `Disabled` 位；先备份 `Mods.sqlite`；游戏进程运行时拒绝写入；测试结束按备份或按记录恢复。不要新建/替换用户的 Mod 组。

## 路径探测（换机器）

1. **游戏根**：优先从 Steam 库配置读取。注册表 `HKCU\Software\Valve\Steam` 的 `SteamPath`/`SteamExe`；库列表在 `<Steam>\steamapps\libraryfolders.vdf` 的 `path` 字段。目标子路径固定为 `steamapps\common\Sid Meier's Civilization VI`。自动探测覆盖 Steam 版；Epic/GOG/Game Pass 或自定义安装位置用 `CIV6_GAME_DIR` 环境变量覆盖（脚本的 `find_game_dir()` 优先读取）。
2. **校验程序**：`Base\Binaries\Win64Steam\CivilizationVI.exe` 与 `CivilizationVI_DX12.exe` 同时存在才算完整安装；补丁/资料片只影响内容，不改变这两个路径。
3. **用户目录**：`%LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VI`；`LOCALAPPDATA` 缺失时用脚本的 `--db`/`--dir` 参数显式指定。中文用户名或非 C 盘 Steam 库都不改变该相对路径。
4. **确认 EnableTuner**：只读检查 `AppOptions.txt` 的 `[Debug]` 段是否已有 `EnableTuner 1`；没有则先备份再补该行，不要整文件重写。
5. **Python**：仓库内用 `.venv\Scripts\python.exe`；系统 `python` 也可，但需 3.11+。脚本不依赖 PyQt；截图在缺 Pillow 时降级 BMP。

## 窗口化

- **为什么窗口化**：窗口可枚举 rect、可截图、可聚焦；独占全屏下截图与后台操作不可靠，自动测试一律窗口化。
- **尺寸标准**：窗口尺寸不写死。启动前按主屏物理分辨率推导：取与主屏宽高比一致（允许 <1% 误差）、约占工作区 85–90% 的整数尺寸（宽度可 8 像素对齐），使比例与屏幕一致且面积尽量大；主屏分辨率或缩放变化时重新计算。设备的具体分辨率/缩放/窗口尺寸属本机数据，只写本机状态目录（示例：`%LOCALAPPDATA%\civ6_ai_play\device_profile.json`），**不写入技能文档或仓库**。
- **修改方式**：两种等价做法，优先用脚本。脚本：`civ6_game.py windowed --width <宽> --height <高>`（尺寸由启动器按上条标准自动计算；显卡吃力时按同一比例缩小），游戏运行时会拒绝改写；它把 `[Video]` 的 `FullScreen` 改为 `0`、`RenderWidth`/`RenderHeight` 改为指定值，同时确保 `[Debug] EnableTuner 1`，并按低配档位关闭 MSAA、阴影、泛光等选项。手工：关闭游戏后只改 `[Video]` 的三个值，`UIUpscale` 保持不变；尺寸不超过桌面分辨率。
- **备份与还原**：脚本在改写前把 `AppOptions.txt`、`GraphicsOptions.txt` 整文件复制到状态目录 `backups\`（时间戳命名），并写入 `state.json`；**重复调用 windowed/launch 时会复用最初一次的备份**，`civ6_game.py restore` 按记录整文件复制回原路径。手工操作的替代办法：备份后记录原 `RenderWidth`/`RenderHeight`/`FullScreen` 三个值，还原时只写回这三个值，避免覆盖用户期间的其他设置。两种方式都要在还原后读回确认。
- **启动**：脚本 `launch --exe dx12|dx11` 以游戏根为工作目录直接运行 exe，也可由 Steam 启动；手工运行时工作目录设为 `Base\Binaries\Win64Steam` 或游戏根均可（记录实际方式）。同一时刻只运行一个游戏实例；不要结束 Steam。
- **核对**：启动后用窗口脚本列出 `CivilizationVI*` 窗口并记录 rect；若窗口仍全屏或黑屏，先等 30 秒再判断，仍异常转 [排障](troubleshooting.md)。
- **结束还原**：关闭游戏并等待进程退出后再还原；`state.json` 缺失时备份不会被自动找回，应改用带时间戳的备份文件人工恢复。

## GPU 温度与负载

- 自动测试优先窗口化 + 低画质档（示例：MSAA 0、阴影/AO/泛光关闭、TerrainQuality 1、VFX/Clutter 0、Leaders 1）；具体档位按显卡实际负载与温度调整，不把某台机器的清单当通用常量。
- **阈值**：与用户/机器约定温度上限（显卡厂商默认阈值或用户指定值）。每轮测试前后各查一次温度、占用与功耗：NVIDIA 用 `nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,power.draw --format=csv,noheader`，其他显卡用厂商工具或系统监视器。
- **处置**：接近上限就缩短单次测试或先退出降温；超过上限立即停止。
- **进一步降温**：继续减小 `--width/--height` 或降低画质档位；一次只开一局并尽快结束；不要在测试期间后台跑渲染/训练任务。
- 测完必须退出游戏并确认进程结束，避免后台持续占用显卡。

## Tuner 连接

- `[Debug] EnableTuner 1` 让游戏在 `127.0.0.1:4318` 监听；只绑定本机回环，一般不需要防火墙放行。
- **单连接**：同一时刻只接受一个客户端；MCP 客户端、外部脚本与 FireTuner 面板不要同时连。MCP 接管前先停 bridge/直连，交接顺序见 [MCP 工具速查](mcp-tools.md#1-定位与分工)。
- **连接生命周期（真机实测，换版本重测）**：主菜单可直连；地图加载中/领袖介绍未跳过时 4318 无监听或 connect 超时；**`LoadScreen: OnLoadGameViewStateDone` 出现并用 Esc 跳过领袖介绍后，4318 恢复监听，可重连**；对局稳定后可反复断开/重连。加载期间不要抢连。
- **直连 vs 常驻桥**：短命令默认直连（`civ6_ops.connect_tuner_retry` 内置重试）；需要跨多步长时间持有时再 `civ6ctl.py serve`（HTTP `127.0.0.1:8770`，`/eval` 转发 Lua、`/shutdown` 关闭）。`civ6_bridge.py health|states|eval|run|stop` 可直接操作桥；`civ6ctl.py close --stop-bridge` 退出游戏后一并关闭桥。
- **备用 GUI 通道**：`civ6_tuner_gui.py` 用 Win32 自动化官方 `FireTuner2.exe` 的 Lua Console（选中状态、写入代码、回车、读输出）；FireTuner2 自带重连，适合直连反复失败时排障。
- 状态表分两套：前端（主菜单/选人，如 `FrontEnd`）与对局（如 `GameCore_Tuner`、`InGame`）；状态编号随加载变化，一律按名字查，不要硬编码编号。
- 连接失败、状态不存在、执行超时的排查见 [排障](troubleshooting.md#tuner-连不上)。

## Python 与脚本

- DLL Loader 标准安装：把 runtime 复制成 exe 目录的 version.dll。若 Windows 兼容性库（sysMerge.sdb 的文明6 DXGICompat 条目）抢先加载 system32 VERSION.dll，app-local 代理会失效；用 `scripts/civ6_sdb_fix.py status/apply/restore/verify` 诊断修复（apply 会改 sysMerge.sdb，自动备份原文件与 ACL；Windows 更新后重跑 apply），详见 [Mod 测试方法](mod-testing.md)。无法改系统时用 `scripts/civ6_inject.py` 注入（测试后删除注入文件与生成目录）。

- 统一入口：`skills\civ6-ai-play\scripts\civ6ctl.py`，子命令 `env`/`serve`/`launch`/`states`/`start`/`probe`/`act`/`shot`/`mods`/`logs`/`close`/`restore-config`（以 `--help` 为准）。
- 模块：Tuner 协议客户端 `civ6_tuner.py`、对局操作与开局编排 `civ6_ops.py`（`start_game_flow`、`Session.probe/act`、`connect_tuner_retry`）、游戏启动/窗口化/配置 `civ6_game.py`、窗口/截图 `civ6_win.py`、Mods 数据库 `civ6_mods.py`、日志扫描 `civ6_logs.py`、常驻桥 `civ6_bridge.py`、备用 GUI 通道 `civ6_tuner_gui.py`。
- 脚本不修改游戏安装目录（唯一例外：civ6_sdb_fix.py 在用户明确同意下修改 Windows 兼容性库 sysMerge.sdb，自动备份原文件与 ACL、可 restore）；写用户目录（`Mods.sqlite`、`AppOptions.txt`、`GraphicsOptions.txt`）前必须备份，并在游戏未运行时操作。`civ6_game.py windowed` 同时备份两个选项文件并写 `state.json`，`restore` 依据该状态还原。
- 运行结果优先输出 JSON/结构化文本，便于把每一步写入测试报告；`civ6_game.py env` 会打印游戏根、用户目录、日志、`Mods.sqlite`、运行中进程和状态目录。

## 截图

- 优先截窗口客户区，记录窗口 rect、时间戳与当前操作说明；保存 PNG。
- **DPI 与截图方式**：`civ6_win.py` 会尽量开启 Per-Monitor DPI 感知，`rect` 输出含 `dpi`/`dpi_scale`；高 DPI 下若宿主进程已固定 DPI 感知级别，矩形可能与物理像素有偏差。截图默认 `auto`：先 `PrintWindow(PW_RENDERFULLCONTENT)`，失败或纯色再屏幕抓取、GDI；`PrintWindow` 能截被遮挡窗口，但部分 DX11/DX12 硬件加速窗口必然黑屏（Windows API 限制），此时用 `--method screen`，或先 `focus` 置前后重截。
- 无 Pillow 时降级 BMP；截图尺寸应与 `[Video]` 设置一致，便于比对。
- 最小化、被遮挡、独占全屏时截图不可靠；截图前先恢复并置前窗口。
- 截图只作取证，不替代状态查询：能截到画面不等于 Mod 效果正确。

## 关闭与还原

1. 保存截图与需要的日志副本（或记录文件 mtime/size）后再关闭。
2. 优先 `civ6ctl.py close`（经桥发 Lua 退出请求，超时才强杀）或游戏菜单退出；无法正常退出时按 [安全结束进程](troubleshooting.md#安全结束进程) 操作。
3. 等进程完全退出（`Mods.sqlite` 解锁）后还原：优先 `civ6ctl.py restore-config`（等价 `civ6_game.py restore`）；`Mods.sqlite` 用带时间戳的备份或 `mods restore` 恢复。
4. 读回确认还原值；报告保留了哪些用户文件、改动了哪些。用过常驻桥时确认 `civ6ctl.py close --stop-bridge` 或 `civ6_bridge.py stop` 已结束桥进程。
