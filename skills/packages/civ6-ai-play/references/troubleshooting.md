# 排障：Tuner、启动、Mod、加载与窗口

原则：先取证（进程、端口、日志、截图）再改配置；一次只改一个变量；每次记录命令、时间和日志文件 `LastWriteTime`。旧日志是常见误判来源——判断前先确认文件是否随本次启动更新。

## 快速分诊

| 现象 | 先查 | 下一步 |
|---|---|---|
| 连接 4318 被拒绝 | 游戏是否已启动、`EnableTuner 1`、端口是否监听 | 见 Tuner 连不上 |
| 4318 在进入对局后消失 | 是否仍在加载/停在领袖介绍界面 | 等 `OnLoadGameViewStateDone`、Esc 跳过介绍，再带重试重连（监听会恢复） |
| 桥 `/health` 显示未连接 | 游戏未启动、仍在前端早期、桥等待超时、已有客户端占用 4318 | 见常驻桥与单连接 |
| 连上但命令无回复/超时 | 是否已有其他 Tuner 客户端、状态索引是否正确 | 断开其他客户端，经桥重取状态表 |
| 游戏进程在但无窗口 | 是否卡在启动、`Startup.log`/`Engine.log` 是否增长 | 窗口枚举后等待，仍无转启动失败 |
| 选完人后没有对局状态 | 是否仍在加载、`Database.log` 是否停在半截 | 等 `GameCore` 状态，不要在加载中抢发命令 |
| Mod 界面/效果缺失 | `Modding.log` 启用列表、`Database.log` 加载错误 | 见 Mod 报错或未生效 |
| 窗口全屏/黑屏/花屏 | `[Video]` 设置、GPU 驱动、是否独占全屏 | 见 GPU 与窗口问题 |

## Tuner 连不上

按顺序排除：

1. **游戏确实已启动**：进程名 `CivilizationVI` / `CivilizationVI_DX12`；主菜单出现后再连接（前端 `FrontEnd` 状态早于对局）。
2. **`EnableTuner 1`**：读 `AppOptions.txt` 的 `[Debug]` 段；修改前备份、关闭游戏后改。若文件被游戏重写（顶部有 Version 警告），改完要再次确认。
3. **端口监听**：`netstat -ano | findstr :4318`，确认 `127.0.0.1:4318` 处于 `LISTENING` 且 PID 对应游戏进程。无监听 = 游戏未开 Tuner 或仍在启动早期。
4. **单连接与重连时机**：FireTuner 只接受一个客户端；**加载/领袖介绍期间 4318 暂不可用，但加载完成 + Esc 跳过介绍后会恢复监听，可重连**（实测对局内反复 connect/close 3 轮成功）。加载中不要抢连；重连时以 2–3 秒间隔重试，可用 `civ6_ops.connect_tuner_retry`。
5. **桥状态**：`civ6_bridge.py health` 或 `Invoke-RestMethod http://127.0.0.1:8770/health` 看 `connected`；未连接时桥仍每 2 秒探测 4318/4319/4320，直到 `--wait` 超时。`/eval` 返回 503 表示桥连不上 Tuner，先解决连接再发命令。
6. **状态名**：`states` 列出全部状态；主菜单没有 `GameCore_Tuner`，此时只能操作前端状态。按名称解析失败时用索引或 `--state` 子串。
7. **超时与重连**：`connect` 成功但无回复时，先用短 Lua（如 `print("@@ok")`）验证链路；若确认还在加载/介绍界面，等加载完成 + Esc 后再重试，而不是反复直连。直连一段时间仍失败时，改用 `civ6_tuner_gui.py`（官方 FireTuner2 自带重连）判断是协议问题还是时机问题。
8. **代理/虚拟网卡**：回环直连一般不经过代理；挂全局代理或异常虚拟网卡时临时关闭后重试。

取证：保存 `civ6_bridge.py health`、桥未运行时的 `civ6_tuner.py states`、`netstat` 输出和 `Engine.log` 尾部。

## 常驻桥（civ6_bridge）与单连接

- 启动：`civ6ctl.py serve`（前台阻塞，HTTP `127.0.0.1:8770`）；健康检查 `civ6_bridge.py health`；停止 `civ6_bridge.py stop`，或在退出游戏时用 `close --stop-bridge`。
- 桥持有唯一 Tuner 连接，其他脚本/agent 只访问 8770 的 HTTP；**桥运行期间不要再直连 4318**，第二个客户端会失败或与桥抢回复。
- 桥先于游戏启动是正常的：它循环探测端口，日志出现 `[bridge] connected tuner port=4318` 才算连上。
- 桥等待超时（`civ6ctl.py serve --wait` 默认 900 秒，`civ6_bridge.py serve` 默认 600 秒）后进程仍在但 `connected=false`：检查游戏是否启动、Tuner 是否开启、是否有别的客户端占用。
- 桥自己退出或异常终止后，先等几秒让游戏重新监听 4318，再按「加载完成 + Esc」的前提重连；对局稳定后断开再连是可行的，不必重启游戏。


## 游戏启动失败或卡住

- 确认 exe 路径与工作目录；DX11 与 DX12 分开记录，不用一个版本的成功推断另一个。
- 确认 Steam 客户端已运行（游戏需要 Steam）；不要用结束 Steam 的方式「重开」。
- 首次进入或大 Mod 场景加载慢是正常的：给 60–120 秒，期间观察 `Startup.log` 是否增长。
- 启动即退：读 `Startup.log`、`Engine.log`、`Renderer.log` 尾部；检查用户目录 `dumps\` 是否有崩溃转储。
- **卡住时先截图判读**：`civ6ctl.py shot --out workspace\scratch\ai-play\stuck.png` 看是加载画面、黑屏还是错误弹窗；截图黑屏时改用 `civ6_win.py shot --method screen`，或先 `civ6_win.py focus` 再截，然后决定继续等待还是结束。
- 卡住无响应：先截图取证并等待，再确认是否上一次进程残留占用文件；不要连续强杀重试。
- 重复失败时回退到未改动的 `AppOptions.txt` 备份，排除窗口化设置导致。

## Mod 报错或未生效

1. **启用集合**：`Modding.log` 中 "Enabled Mods (in no particular order):" 块逐个核对；也可用 Mods 脚本只读列出所选组启用项。用户原有启用集很大时，先确认测试的是哪一组。
2. **加载错误**：`Database.log` 查 `ERROR`/`Error`/`Failed to load`/`Unable to load`，定位到具体 Mod 的文件与行。
3. **运行时错误**：`Lua.log` 查 `Runtime Error`/`stack traceback`；`UIWarnings.csv`/`UserInterface.log` 查界面层警告。
4. **写库时机**：必须在游戏进程退出后写 `Mods.sqlite`；写前备份、写后读回校验。游戏运行中写入可能被锁或损坏数据。
5. **依赖缺失**：确认测试 Mod 的资料片/前置 Mod 在启用集内；`Modding.log` 会记录扫描与依赖问题。
6. **效果层**：日志干净只说明加载没报错；玩法效果按 [验收分层](../SKILL.md#验收分层) 用状态查询与截图分别确认。

## 加载卡住

- 判断是否真卡住：`Modding.log`/`Database.log` 的 `LastWriteTime` 与大小是否还在变化；先等 2–3 分钟。
- 卡在选人后：多为数据库加载或 Mod 冲突；记录最后一次新增的 Mod，二分启用集复现（每次改启用集都备份 `Mods.sqlite`）。
- 卡在加载条：检查 `Lua.log` 最后一行与 `Database.log` 最后一条；加载期间不要发 Tuner 命令。
- 地图/大 Mod 场景首局更慢；给足时间并记录计时。

## GPU 与窗口问题

- 自动测试一律窗口化：用 `[Video] FullScreen 0` + 合理 `RenderWidth`/`RenderHeight`（可截图、可聚焦、后台操作稳定），不尝试独占全屏。
- 黑屏/花屏：先确认是否仍在加载，再检查 `Renderer.log`；如需对比 DX11 与 DX12，记录用的 exe 和结论，不混测。
- 窗口截图黑屏但游戏画面正常，多半是 `PrintWindow` 限制或窗口被遮挡，换屏幕抓取/置前处理，不据此判断渲染失败。
- 分辨率异常：还原备份的三个值后重启；不要把桌面缩放比例当作游戏渲染设置。
- 最小化后无法恢复：用窗口脚本恢复并置前；仍失败则记录窗口 rect/样式后转安全结束进程。
- 修改任何 `[Video]` 值前先备份，一次只动一个变量。
- **温度**：上限按用户/机器约定（显卡厂商阈值或用户指定值）。测试前后各查一次（NVIDIA 用 `nvidia-smi --query-gpu=temperature.gpu,utilization.gpu,power.draw --format=csv,noheader`，其他显卡用厂商工具）；接近上限就缩短测试先降温，超过上限立即退出。
- 如果窗口化后仍持续高负载：把 `--width/--height` 降到 1024×600，确认低画质项（MSAA 0、阴影 0、AO 0、TerrainQuality 1）确实写入 `GraphicsOptions.txt`。

## 截图与日志定位

- 截图前先置前窗口并记录 rect；截图与日志、操作说明一起归档到 `workspace/scratch/<任务名>/`。
- 日志优先级：`Lua.log`（Lua 运行时）、`Database.log`（数据库/Mod 加载）、`Modding.log`（启用与扫描）；启动问题看 `Startup.log`/`Engine.log`/`Renderer.log`。
- 用 `Get-Item <日志> | Select LastWriteTime,Length` 确认日志来自本次运行，再判断内容。
- 扫描错误时记录命中的文件、行号和原始行，不要只写「有报错」。
- **截图判读**：整窗截图确认游戏在前台、画面不是加载/黑屏/弹窗；客户区截图用 `--client` 与 rect 对照。`PrintWindow` 对部分 DX11/DX12 窗口必然黑屏，这不是游戏崩溃；改用 `--method screen` 或置前后重截。
- **DPI**：`civ6_win.py rect --json` 记录 `dpi`/`dpi_scale`；高 DPI 虚拟化下窗口矩形可能偏移 1–2 px，截图与 rect 不一致时按物理像素和实际画面复核。

## 安全结束进程

1. 确认目标：`Get-Process CivilizationVI*`，核对 PID 与路径；**不要结束 Steam 及 Steam 辅助进程**。
2. 先保存截图/日志副本，再优先 `civ6ctl.py close`（经桥请求 Lua 退出，默认等 30 秒后才对残留进程 `taskkill /F`）或游戏菜单正常退出。
3. 桥还活着时用 `civ6ctl.py close --stop-bridge`，或单独 `civ6_bridge.py stop`。
4. 退出后还原：`civ6ctl.py restore-config`；`Mods.sqlite` 用 `civ6ctl.py mods restore` 或时间戳备份；确认 `Mods.sqlite` 已解锁。
5. 手动兜底：先 `CloseMainWindow()` 等 10–15 秒，仍不退再 `Stop-Process -Id <PID>`；结束方式写进报告。
6. 不确定进程用途时停止操作并询问用户，不批量结束以 Civilization 开头的所有进程。

## DLL Loader 与自定义 UI Mod

- **DLL Mod 没生效**：先看 Logs\Civ6DllLoader_Loader.log 是否存在；不存在说明 loader 根本没进进程。再查进程里的 VERSION.dll：若来自 `C:\WINDOWS\SYSTEM32` 而不是 exe 目录，说明被 Windows 兼容性库抢占；典型来源是 sysMerge.sdb 中的文明6 DXGICompat 条目，用 `scripts/civ6_sdb_fix.py status` 确认是否命中。
- **标准安装修复**：先 python skills\civ6-ai-play\scripts\civ6_sdb_fix.py status 看是否已 patched；未修复则 apply --yes（需管理员，修改 sysMerge.sdb，自动备份/可 restore；Windows 更新后重新 apply），再启动游戏用 verify 确认 exe 目录 VERSION.dll 被加载、AcGenral 消失、loader 日志出现。
- **不能改系统时备用**：确认游戏关闭后把 Civ6DllLoader.runtime.dll 复制到游戏 exe 目录，启动并等窗口出现，用 scripts/civ6_inject.py --dll 注入；loader 日志出现 Loaded plugin / OnLoad / active 才算插件加载成功。注入过早会命中 Steam 重启前的临时进程；等窗口出现、进程稳定后再注入。
- **自定义 UI 找不到**：用 tuner states 找 Mod 新增的 Lua 状态（状态名随 loader 版本与 Mod 组合变化，以实际状态表新增项为准）；在该状态读 Controls 键和全局 API，不要只靠截图。SDB 修复后 loader 由 version.dll 早期加载，UI 注入钩子能正常安装；注入 workaround 若晚于界面加载，本次运行不会出现面板。
- **清理**：注入 workaround 后删除注入进 exe 目录的 runtime 与 exe\Civ6DllLoader 目录；无论哪种方式都要还原 Mods.sqlite 与 AppOptions/GraphicsOptions，关闭游戏。

## 常见误判

- 命令返回 `true` 或空 ack 只代表命令已送达，不代表游戏状态变了——必须复查状态。
- 日志没有 `ERROR` 不代表 Mod 生效；反过来旧日志里的 `ERROR` 也不属于本次运行。
- 窗口截图正常不代表操作生效；截图与状态查询要成对出现。
- 桥占着 Tuner 时直连 4318 失败是预期现象，不是 Tuner 坏了；用桥的 `/health` 判断连接。
- 加载中/领袖介绍界面连不上 4318 不代表 Tuner 坏了：先等加载完成并用 Esc 跳过介绍，再重试；不要因此立刻重启游戏。
- 命令返回 `true` 不代表单位/城市动作立即完成：`FOUND_CITY` 的城市数变化可能下一 tick 才可见，需 `probe` 复查。
- 截图黑屏可能是 `PrintWindow` 限制，不一定是游戏黑屏；换 `--method screen` 或置前后再看。
