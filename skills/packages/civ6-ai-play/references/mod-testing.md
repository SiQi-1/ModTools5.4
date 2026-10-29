# Mod 测试：玩法 Lua / DLL 插件 / 自定义 UI

本文记录「用本技能实测一个 Mod 是否真的加载、API 是否可用、玩法与 UI 是否生效」的方法。原则：**命令返回、日志无错、状态读数、画面表现是四层不同证据，必须逐层记录**；单靠其中一层不下结论。

## 三类 Mod 与入口

| 类型 | 加载入口 | 首要证据 | 效果验证 |
|---|---|---|---|
| 数据/玩法 Lua Mod | .modinfo 的 InGameActions / FrontEndActions | Modding.log 启用集与 Database.log | Lua.log 打印、tuner 调 Lua API、状态与截图对比 |
| DLL Loader 插件 Mod（GameCore/Global DLL） | Civ6DllLoader 的 version.dll 代理 → 插件 OnLoad | loader 日志（Logs\Civ6DllLoader_Loader.log）出现 Loaded plugin / OnLoad / active | tuner 调插件新增的 Lua 方法并读回数值 |
| 自定义 UI Mod | 前端：loader 的 FrontEndUI_*.xml/lua；对局内：AddUserInterfaces/ReplaceUIScript | tuner LSQ 多出的 Lua 状态、控件表、截图 | Controls 状态断言 + 截图/坐标点击 + 日志 |

## 通用取证顺序

1. **先备份**：Mods.sqlite（备份文件带时间戳）、AppOptions.txt/GraphicsOptions.txt；DLL Mod 还要记录 exe 目录原本有哪些文件。
2. **启用 Mod**：游戏关闭时改 Mods.sqlite 启用集（本技能 mods enable/disable 会备份并校验）；DLL Mod 需要 loader 在场。
3. **启动并开局**：窗口化 1280x720 低画质，开始一局并跳过领袖介绍；记录 GPU 温度。
4. **查加载层**：Modding.log 中启用集与 Mod 文件名；Database.log 的 ERROR；DLL 看 loader 日志；Lua Mod 看 Lua.log 中 Mod 自己的 loaded 打印。
5. **查 API/状态层**：tuner 在 InGame 或 GameCore_Tuner 上下文执行 Mod 提供的函数；数值型效果要记录修改前后。
6. **查表现层**：窗口截图（操作前后各一张）；UI Mod 要打开/点击/关闭并截图。
7. **收尾**：关闭游戏、还原 Mods.sqlite 与选项、清理临时注入文件，再写结论。

**操作驱动**：客户端已注册 civ6-mcp 时，常规单位/城市/外交/宗教/政策等操作优先用其工具（[MCP 工具速查](mcp-tools.md)），不必现场手写 Lua；断言仍按本文与 [真实 Mod 运行时验证](mod-runtime-testing.md) 记录。自定义 UI 状态、DLL loader、WorldBuilder 造物等 MCP 不做，继续用 tuner/脚本。

## 案例 A：玩法 Lua Mod（数据 + 游戏事件脚本）

以「建城时给城市 3 环地块加产出」的测试脚本为例（Mod 自带一段测试 Lua）：

1. 启用 Mod 后开局，读 Lua.log 应出现 Mod 的 loaded 行（示例格式：`<Mod 名>: [<标记>] loaded`）。
2. 用 act found 或 MCP `unit_action(action="found_city")` 建城（本技能的 `act found` 会把 RequestOperation(FOUND_CITY) 发到 InGame 状态）。
3. 等待 2 到 3 秒后查 Lua.log，应出现 CityBuilt 与逐地块的 before -> after 行；触发范围内地块的增量与测试脚本设定一致（示例 +5，随机产出类型）。
4. 用 tuner 在 InGame 状态读同一批地块的 GetYield 值，与建城前基线对比，确认 +5 落在预期地块（距离 1..3）。
5. 截图记录城市与地块产出画面。

注意：城市数量变化可能下一 tick 才可见；FoundCity 返回 true 不代表城市已创建，必须 probe 复查 cities 与 capital。

## 案例 B：DLL Loader 插件 Mod（GameCore 插件）

### 已知兼容性问题：Windows 兼容性库把系统 VERSION.dll 抢在 exe 前加载

Civ6DllLoader 的标准安装是把 runtime 复制成游戏 exe 目录下的 version.dll（exe 静态导入）。**诊断**：若进程里 VERSION.dll 来自 `C:\WINDOWS\SYSTEM32` 而不是 exe 目录，说明 app-local 代理未被加载，loader 日志与 `exe\Civ6DllLoader` 目录也不会生成。**典型根因**：Windows 兼容性数据库（`C:\Windows\apppatch\MergeSdbFilesSource\sysMerge.sdb`）里有文明6的匹配条目（civ6_win64_dx12_release.exe、CivilizationVI.exe、Civilizationvi_dx12.exe），命中后系统施加 DXGICompat 兼容性修复，在 exe 导入解析前加载 AcGenral；AcGenral 依赖的 VERSION.dll 从 system32 抢先装入进程，app-local 代理因此轮不到。对照：同一 exe 改名启动可绕过匹配，但 loader 用文件名精确识别 DX11/DX12（ImageAddress 匹配 CivilizationVI.exe / CivilizationVI_DX12.exe），改名后插件不加载，不是可用方案；同目录普通程序能正常加载该代理，说明不是文件缺失。

修复：用 `scripts/civ6_sdb_fix.py` 把 sysMerge.sdb 里上述匹配名替换为同长度占位名，使兼容性修复不再命中。它会先备份原文件到 `%LOCALAPPDATA%\civ6_ai_play\sdb_backup`（含原始 SHA256 与 ACL SDDL），apply/restore 都会恢复原 ACL；只改 sysMerge.sdb，不改 DirectXApps.sdb/sysmain.sdb，也不改游戏文件。

```powershell
python skills\civ6-ai-play\scripts\civ6_sdb_fix.py status
python skills\civ6-ai-play\scripts\civ6_sdb_fix.py apply --yes
python skills\civ6-ai-play\scripts\civ6_sdb_fix.py verify
python skills\civ6-ai-play\scripts\civ6_sdb_fix.py restore --yes
```

注意：apply/restore 修改 Windows 系统文件，需要管理员权限并显式 --yes；Windows 更新可能覆盖 sysMerge.sdb，更新后重新 apply；不能用时仍可用下面的注入 workaround。修复后用 `verify` 确认 exe 目录 VERSION.dll 被加载、AcGenral 消失，并做一次开局冒烟：loader 日志出现 Loaded plugin / OnLoad / active 即视为恢复。

### 注入 workaround（SDB 修复前使用；修改系统受限时备用）

1. 关闭游戏；把 Civ6DllLoader.runtime.dll 复制到游戏 exe 目录（loader 的 DllMain 要求模块目录等于宿主 exe 目录，且宿主是 CivilizationVI*.exe 才启动）。
2. 启动游戏（窗口化），等窗口出现且进程稳定（过早会命中 Steam 重启前的临时进程）。
3. 注入：python skills\civ6-ai-play\scripts\civ6_inject.py --dll "<exe目录>\Civ6DllLoader.runtime.dll"（脚本用 CreateRemoteThread + LoadLibraryW，不需要编译器）。
4. 检查 Logs\Civ6DllLoader_Loader.log：应出现 Loader 初始化、LoadDLL + UnloadDLL installed、UiInject 释放资源；exe\Civ6DllLoader\config.ini 与 UI 资源生成。
5. 正常开局：loader 日志应出现 ruleset=RULESET_EXPANSION_2、Loaded plugin xxx.dll、OnLoad、active 等行。若插件符号不匹配，会打印 disabled/回滚原因。
6. 用 tuner 测插件新增 Lua 方法，记录前后数值。
7. **收尾必须清理**：删除复制进 exe 目录的 runtime 与 exe\Civ6DllLoader 目录（恢复到测试前状态），并还原 Mods.sqlite / 选项。

### 案例结果模板：ChangeYield 测试应看到什么

- loader 日志：出现 GameCore plugin candidate；`Loaded plugin <测试插件>.dll`；`OnLoad`；symbol db match（示例 matchRatio=1.000）；InstallHook GetYield 两个重载；`active: ChangeYield installed`。
- Lua API：InGame 与 GameCore_Tuner 两个上下文里 `pPlot.ChangeYield` 都是 function；某地块 Food 2 调用 `ChangeYield(0,5)` 后立即读回 7，返回 true。
- 建城脚本：触发范围内地块各出现 before -> after 行，增量与测试脚本设定一致（示例 +5 随机产出类型）。
- getyield 读数：UI（InGame）、GameCore_Tuner、玩法脚本自身三处读到的新值应一致；若某个上下文出现旧值，先确认调用的是哪个 API（GetYield 有无 player 参数、是否读取缓存、是否在 tick 边界）并用 UI 上下文交叉核对。

## 其他 DLL Mod 加载机制（对照）

除 app-local version.dll 代理外，还有两类常见机制：

- **C6SE（Civ6 Script Extender）**：Mod 自带 `GameCore_XP2_Loader_*.dll` 一类加载器，插件放在 `Binaries/Win64/c6se/*.dll`；`Config.sql` 用 `UPDATE GameCores` 把 Expansion2 的 PackageId/DllPrefix 指向本 Mod，引擎直接从 Mod 包加载该 loader，再由它加载 c6se 插件并转发/挂接官方 GameCore，不需要 app-local version.dll。
- **直接替换 GameCore DLL**：`Config.sql` 把 Expansion2 槽位指向本 Mod 自带的 GameCore DLL。

判断是否生效：查进程里加载的 DLL 路径；用 tuner 读 `GameInfo`/属性并做前后对比（例如数据 Mod 改的 `GlobalParameters` 值）。注意：多个 GameCore 槽位 Mod 会互相覆盖 GameCores 改写，同一时间只能有一个槽位生效；一个 C6SE loader 可同时加载多个启用 Mod 的 c6se 插件，但仍需逐个验证。引用第三方 loader/插件需遵守其许可，不要复制进技能或仓库；本文只描述测试操作与观测方法。

## 案例 C：自定义 UI Mod（独立界面）

加载器自带一个独立主菜单 UI（文明6插件加载器面板），是很好的测试样本。实测方法：

1. SDB 修复后 loader 由 version.dll 在启动早期自动加载，主菜单 LoadUI 钩子能正常安装；若不能改系统，才用注入 workaround（尽量在窗口出现前注入）。
2. tuner 连上后取 LSQ 状态表：多出的状态名就是 Mod UI 上下文（名称随 loader 版本与 Mod 组合变化，以实际状态表新增项为准，与原生 FrontEnd/MainMenu 并列）。
3. 在该状态执行 Lua 读控件：Controls 表包含 LoaderOpenButton、LoaderPanelRoot、LoaderEnableGlobal、LoaderEnableGameCore 等；同时 DllLoader 表可读 GetGlobalState/GetGameCoreState（均 true）。
4. 面板开关：直接 Controls.LoaderPanelRoot:SetHide(false) 可显示面板；SetHide(true) 关闭。真实点击入口按钮可用截图定位坐标 + SendInput 点击，再用控件状态/截图确认。
5. 截图：主菜单有右上角齿轮入口；打开面板后为「文明6插件加载器」窗口，勾选框与说明文字齐全（截图归档到本次任务工作目录）。
6. 对任意 Mod 自定义 UI 的通用做法：
   - 先截图对比「启用前/后」找新增按钮或面板；
   - tuner LSQ 找新增 Lua 状态（Mod UI 脚本通常有自己的 context 名）；
   - 在该状态读 Controls 键、全局函数、LuaEvents，尽量用状态断言代替 OCR；
   - 需要真实点击时用窗口截图定位 + civ6_win 坐标点击（窗口化下稳定），点击后截图与状态双确认；
   - 只注入主菜单的 UI（loader FrontEndUI）与对局内 UI（AddUserInterfaces）分开记录，二者状态生命周期不同。

## 判定表与常见坑

| 层 | 通过证据 | 常见失败 |
|---|---|---|
| 启用/加载 | Modding.log 启用集包含 Mod；Database.log 无 Mod 相关 ERROR | 写库时游戏在运行；启用集没保存 |
| DLL 注入 | loader 日志有 Loader 初始化与插件 OnLoad | Windows 兼容性库抢占 version.dll（用 civ6_sdb_fix.py 修复）；注入时机过早或过晚；exe 目录残留 |
| Lua API | tuner 能列出新函数，参数合法时返回 true | 上下文选错（GP 与 UI 状态不同）；函数在每局重建需重新挂 |
| 玩法效果 | Lua.log 打印 before -> after；probe 状态变化 | 异步 tick、账本不写存档、城市产出下一回合才重算 |
| 自定义 UI | 截图可见新增控件；Controls/DllLoader 状态正确 | UI 注入钩子晚于界面加载；只看截图不做状态断言 |

- 注入/UI 测试后必须清理：删除复制进游戏目录的文件、还原 Mods.sqlite 与选项、关闭游戏并确认进程退出。
- 每次测试记录 GPU 温度/负载，按用户约定的上限判断；接近上限就缩短或退出，命令见 `SKILL.md`『GPU 温度/负载自检』。
- 实测补充（特定 loader/Windows 版本下观察）：游戏窗口的**合成鼠标点击**（SendInput / mouse_event）没有触发这个注入 UI 按钮（键盘 Esc 正常）；按钮的真实点击测试需要另找输入通道（例如向窗口投递 WM_LBUTTONDOWN 或改用真实硬件输入），更稳的做法是用 tuner 读取控件状态与后端 API，并直接驱动与按钮相同的代码路径（显示面板 + 调 DllLoader.Get/SetXxx），再用截图确认。


