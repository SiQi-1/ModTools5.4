# 社区技能与工具整合记录

日期：2026-09-25。状态：**功能、知识路由与署名已落地**。

来源、作者、许可及原始包 SHA-256 见 [第三方参考资料与致谢](../THIRD_PARTY_NOTICES.md)。本轮在现有工作区增量整合，保留已有 HTML UI、UnitAbility 及其他工作；没有复制第三方程序、模板原件、模型、贴图或 Steam DLL。

## 已实现内容

| 交付 | 正式入口 | 内容 |
|---|---|---|
| 领袖美术知识 | [leader-art.md](../skills/05-modtools-civ/leader-art.md) | 普通回退图、外交表情、三维平面模型的区别；引用链、材质和灯光排错 |
| 音频工作流 | [audio-pipeline.md](../skills/05-modtools-civ/audio-pipeline.md) | 声道、响度、Wwise、Banks.ini、流式 WEM、UpdateAudio 与弃用路径 |
| 模型与动画交换 | [blender-civnexus.md](../skills/05-modtools-civ/blender-civnexus.md) | CN6 / NA2 与 CivNexus6 职责、模型先于动画、权重与版本依据 |
| 美术产物验证 | [art-cook-validation.md](../skills/05-modtools-civ/art-cook-validation.md) | 源工程、Cooker 产物与实机分阶段验收，区分格式变化和语义变化 |
| 工坊交付 | [workshop-release.md](../skills/05-modtools-civ/workshop-release.md) | 上传器 workspace、元数据、本地化、条目 ID、依赖和退出码 |
| Lua 规则统一 | [code-style.md](../skills/04-lua/code-style.md#事件环境与运行时核验) | 按本项目原要求及本次用户确认修正冲突 |

上述五篇指南与 Lua 环境规则接入 INDEX、catalog 和 retrieval_cases，可用 modgen skill 检索；技能库共 235 篇、31 个检索用例。

## 领袖外交表情差分

领袖条目新增可选 fallback_images，GUI 提供折叠状态表、选择、清除和原图预览。声明以外交状态为键、图片槽对象为值；显式 DEFAULT 优先，否则使用旧 images.diplo_foreground。未设置状态不生成空条目。含差分时必须有默认图。

Qt-free 的 [leader_fallbacks.py](../ModTools_5_4/project/leader_fallbacks.py) 集中维护状态、资源名和校验；编辑器、modgen 校验、PNG/DDS/TEX 计划、XLP 和 ArtDef 共用它。schema 和 .CIV 往返同步支持新字段。

默认资源继续使用 FALLBACK_NEUTRAL_<领袖标识>；其他状态使用 FALLBACK_STATE_<状态>__LEADER_<领袖标识>，确保 DEFAULT / NEUTRAL 不重名，HAPPY 与 HAPPY_IDLE 等前缀重叠的状态也不会跨领袖冲突。

只填 path 的新差分图按比例完整放入 960×960 透明画布，保留 alpha；已有 scale/offset/canvas 配置继续沿用图片槽排版。旧默认图输出和变换保持兼容。文件名沿用 LeaderFallback.xlp、FallbackLeaders.artdef。

23 状态来自飞花白模板，保留 DECLAR_WAR_FROM_HUMAN 拼写。该状态名称不是本项目已核实的官方枚举；目标 SDK、Cooker 和实际外交状态触发需独立验收。

## 四类只读检查

~~~powershell
python -m modgen.cli assets check MyMod/MyMod.civ6proj --json
python -m modgen.cli audio check MyMod/MyMod.modinfo --json
python -m modgen.cli art compare MyMod/ArtDefs Cooked/ArtDefs --json
python -m modgen.cli workshop check workshop --modinfo MyMod.modinfo --json
~~~

核心是纯标准库 [asset_checks.py](../ModTools_5_4/project/asset_checks.py)，CLI 为 [asset_cli.py](../modgen/asset_cli.py)。完整契约见 [modgen/AGENTS.md](../modgen/AGENTS.md#资源与发布产物检查)。

- assets：工程声明与动作内嵌 XML、模板残留、已知美术槽位、LeaderFallback → XLP → TEX/DDS 引用。支持命名空间、自闭合动作；显式处理虚拟 Art Dependency File。官方 pantry 或外部资产列为未验证。
- audio：UpdateAudio → ASCII 无 BOM 的 INI → BNK，结合可用 SoundBanksInfo 核对流式 WEM。扫描音频目录中未登记媒体。缺元数据时明确不能确认全部依赖。
- art：比较明确的 XML 目录，默认 .artdef；保留属性、有效文本、嵌套和集合顺序，忽略格式与注释，报告字段位置。缺失、_MissingArt、结构变化返回非零；不自动修补输出。
- workshop：workspace 元数据类型、唯一或显式选定 modinfo、GUID、文件清单、动作、可选 PNG 头和工坊 ID。dependencies 按上传器采用 UInt64 整数数组；更新允许省略可选元数据。错误 JSON 类型和无法读取的文件返回诊断。

报告包含 errors、warnings、unverified；无静态错误退出 0，错误退出 1，警告或未验证不会冒充已完成的 SDK / 游戏 / Steam 验证。所有命令只读，显式文件引用限制在输入目录内，不通过它们导入二进制、构建或上传。

## 冲突处理

本项目规则优先于外部技能的写法：

| 外部内容或冲突 | 本轮处理 |
|---|---|
| GP 不可用 LuaEvents 等矛盾表述 | 按用户确认：LuaEvents 不直接跨环境，但 GP-GP 可用；Events 在 UI / GP 可用；GameEvents 在 GP 可用。UI 使用时须明确取得 GP 桥接引用 |
| 事件未触发被一概归因于 Events / GameEvents | 要求核对具体事件、注册时机、参数、上下文；不以事件系统名称下结论 |
| 外部技能全面禁用 ExposedMembers | 保留项目既有桥接方式及同步操作通道，不导入外部全面禁用政策 |
| FireTuner 上下文结果被泛化 | 必须注明环境与对象层级，不将工具上下文代替 Mod 实际环境 |
| 音频早期 ADPCM bank 构造方案 | 保留弃用说明，不复制或接入该脚本 |
| 音频动作直接列 BNK/XML 的旧说明 | 采用后续 INI 注册流程并检查引用链 |
| 上游个人路径、专用名称、响度或灯光数值 | 作为有条件参考，不成为本项目通用硬约束 |
| ArtDef 标签外中文说明 | 界面/文档保留中文解释，生成 XML 不携带混合说明文字；检查器诊断残留 |

## 署名与发行

- 根 THIRD_PARTY_NOTICES.md 明确千寻瀑（许可证署名千与千寻瀑）、煎包 / Jianbao233、飞花白、Deliverator / Sukritact，以及原资料注明的间接来源。
- 五篇指南和新核心模块注明参考范围及独立实现方式。S1 / S2 / S6 未发现独立许可证，不原样分发其脚本和模板。
- 保留 S4、S5 的原 MIT 许可证全文；不将第三方素材或游戏二进制自动归入本项目许可证。
- 2026-09-26 起由 tools/share_source.py 随源码复制来源声明、licenses 目录和本记录，替代旧打包脚本。源码分享目录不依赖用户参考资料目录。

## 验证记录

- 资源检查回归 15 项，其中 14 通过、1 因 Windows 符号链接权限跳过；覆盖缺失流式媒体、INI/动作、XML 命名空间与 CDATA、路径边界、差异定位、异常元数据和只读行为。以禁用 site-packages 的 Python -S 子进程确认不依赖 Qt/Pillow。
- 领袖差分回归 5 项通过：默认与显式差分、未知/缺失图片、GUI 和 .CIV 往返、多领袖命名、实际 PNG/DDS/TEX/XLP/ArtDef 导出以及坏图片阻断。透明像素验证通过。
- 旧默认领袖 XLP / ArtDef 已与修改前实现逐字节比较一致；新增控件已用中文字体和 Qt 事件循环作离屏可视检查。
- 最终主套件 480 项：475 通过、5 跳过、0 失败；modgen 全套 99 项通过。跳过原因：3 项 Windows 符号链接权限、1 项真实浏览器测试未启用、1 项未安装 psd-tools。schema 在临时目录再提取，确认保留 fallback_images。
- 知识质量检查：235 篇、31 场景、0 问题。发布脚本通过 PowerShell 语法解析；新增复制段在临时发行目录执行，来源页、本记录和两个许可证逐文件 SHA-256 一致。没有执行整个 PyInstaller 发布构建。

本轮没有运行 Wwise、Blender 插件、SDK Cooker、Steam 上传或游戏实机验收。上述外部步骤及状态触发、声音表现、照明/透明边缘仍在各指南中明确列为独立验证项。

## 追加 S7：千川白浪 Civ6ArtUnpack（2026-09-25）

原包 Civ6ArtUnpack_Handover.zip 标记生成于 2026-09-17，SHA-256 为 8a559b7cf44f7645be2058a466a0e08eeaa9b9c1e1c9de290f7c08d6cafe8a6b。作者署名由用户确认为千川白浪。阅读移交说明、状态与缺口文档、blpkit 入口/蒙皮提取签名及相关经验笔记；不执行原包二进制和批量脚本。

已新增 [美术解包与复原指南](../skills/05-modtools-civ/art-unpack.md)，接入 INDEX、来源页、Blender/Cooker 指南、任务路由与 3 条检索用例。重点是 pantry 遮蔽、名字与记录身份、分阶段验收、预乘域与 mip、回打包真实载荷覆盖率；包内缺失脚本、参数签名、领袖完成度等冲突已明确记录。

工具在原 assets check 上增量增强：可选 --cooker-config 从用户指定 SDK 配置读取 XLP/AST/GEO/TEX 注册与允许关系；按 ObjectName 查资源，EntryID 留作 BLP 引用名；检查 AST 内的 BLPEntryValue，支持 Windows XLP 相对路径。纯标准库、只读；外部 pantry 和未覆盖的实体类型、FGX/BLP 内部内容及实际编译来源仍列为未验证。

本机官方 Civ6.cfg 的 SHA-256：e10dd128c50caea9b17fffe6a7b47c951e7fda7cc409708fc5819cb041b33feb。其实际注册表确认了正确 TileBase→LandmarkModel 组合，以及 LeaderFallback 拒绝 UserInterface、接受 Leader_Fallback 的关系；测试前后配置散列一致。没有把完整配置、SDK 素材、原包源码、Oodle/Granny EXE 或历史仓库纳入分发。

本轮验证：新增 SDK/AST 检查 8 项通过，既有资源检查 15 项（1 项符号链接权限跳过），知识回归 31 项（1 项符号链接权限跳过），modgen 99 项通过；知识质量检查 243 篇 / 36 场景，0 问题。
## 2026-10-26 来源治理调整

- PSD 模板：用户再次确认区域/领袖/历史时刻 PSD 可作为来源分享，继续随 `skills/civ6-art-images/assets/templates/` 分发。
- 04-lua：从他人 Steam 工坊 Mod 提炼的 92 篇 Lua/UI 资料移出 Git 与源码分享，维护者本机保留在 `local_notes/04-lua-workshop/`（含本地索引，可用 `modgen skill --skills-dir` 检索）；自有 Mod 子系统与 17 篇官方游戏 UI 文件分析继续随仓库。
- 外部 skill/知识仓库：只记录参考链接，不内置、不提供拉取工具、不炼化；S4 线上仓库现行许可为 PolyForm Noncommercial 1.0.0，本项目仅按旧 zip 的 MIT 版本采用已炼化部分并署名。
- 压缩包类原件不内置：S2/S3/S6/S7 等原始包与 S5 上传器二进制不随包分发；需要时由用户向作者或分享者获取。
- 新设备工具链：CivNexus6 注册表、AssetEditor `FbxImporter.dll` 名称修正、Blender 4.5 插件安装/启用写入 [AGENT_SETUP](../AGENT_SETUP.md) 第 7 节，并在 [Blender/CivNexus6 指南](../skills/05-modtools-civ/blender-civnexus.md) 补充环境前置。
- 验证：`python -m modgen.cli skill --check` 通过；`python tools/share_source.py --check` 通过；modgen 测试通过。主测试套件在本机有 4 项失败/1 项错误（PSD 断言文案、Windows 临时路径短名等环境因素），与本次文档与文件移出无关。
验证使用最小资源声明与真实 SDK 配置，没有复现全量解包、领袖动画、Cooker 或游戏显示。此前全量主套件数字属于上一轮记录，本轮按改动范围运行相关套件。

## 追加 S8：千寻瀑 civ6-model-import（外置技能，2026-10-29）

用户提供 `D:\Backup\Downloads\civ6-model-import.zip`（完整分发版，包内版本 2026-10-27；12,594,811 字节；SHA-256 `2d9f3727303fa71c651658e356bc3128dad655317d9a9c66d9387e99c7c7026f`），要求作为“外置技能”接入：不参与 Git、不提交，但保留名单，其他人可向作者千寻瀑索取后自行安装，本项目不代替作者发布。作者署名按用户确认记为千寻瀑。

处理方式：

- 名单登记：[外置技能名单](../skills/EXTERNAL_SKILLS.md) 记录技能名、作者、包指纹、内容范围、适用/不适用、本机安装路径与取得方式；不复制包内文档、脚本或二进制进仓库，也不把其流程炼化为本项目规则。
- 本机安装：解压到 Git 忽略的 `local_skills/civ6-model-import/`；默认 `skills/` 索引与源码分享不包含该包，检索用 `python -m modgen.cli skill ... --skills-dir local_skills/civ6-model-import`。
- 隔离：根 `.gitignore` 新增 `local_skills/`；`tools/share_source.py` 的 `LOCAL_DIRS` 加入 `local_skills`，误跟踪时 `--check` 会失败；任务目录新增 `external_model_import` 路由，检索命中名单页。
- 分布边界：包内 `tools/CivNexus6/` 的 Firaxis/Granny/FBX 程序集与未签名 exe 属作者的 CivNexus6 构建产物，许可以上游为准；包内未发现独立 LICENSE 文件。本项目只做本机安装与名单登记，不分发原件，不执行包内 exe/dll/脚本。
- 包内文档的本机绝对路径、工程常量与实测结论不回流到 `skills/`。

验证记录：zip 306 条目（10 目录 + 296 文件）无绝对路径、盘符或 `..` 越界；按包内 `MANIFEST.sha256` 逐文件复核 295 条全部一致（缺失 0、不一致 0，唯一清单外文件为清单自身）；本机安装 296 文件、34.86 MiB；`git check-ignore` 命中 `.gitignore` 的 `local_skills/`，`git status --untracked-files=all` 不含该目录；本地检索 8 条命中（top 为 `SKILL.md`），`--file SKILL.md` 读取非空（5,921 字符）。知识检查 `python -m modgen.cli skill --check` 通过（167 篇、62 个检索用例、0 个问题）；`python -m unittest tests.test_knowledge_quality tests.test_skills_search tests.test_external_skills tests.test_source_distribution` 48 项通过；`python tools/share_source.py --check` 通过。未运行包内 exe/dll/脚本，未做游戏内实机验收。

## 追加 S9：lmwilki civ6-mcp（可拉取的外部 MCP 服务器，2026-10-29）

- 来源与处理：https://github.com/lmwilki/civ6-mcp（作者 Liam Wilkinson / lmwilki，MIT，v1.1.11，审阅提交 `dd2019056371b92ea4854e879ddf05a8cad95e8a`）。用户确认按外置 skill 处理：可以拉取、可以记录网址、不内置；本项目只记录 URL/版本/许可与本地安装方式，不复制其代码、`AGENTS.md` playbook 或文档。
- 名单与路由：[外置技能名单](../skills/EXTERNAL_SKILLS.md) 的 civ6-mcp 节；`external_civ6_mcp` 任务路由与 2 条检索用例；知识地图入口同步更新。名单页区分“仅名单（向作者索取）”与“公开仓库（可自行 clone）”两类。
- 本机安装（仓库外，不进 Git）：clone 到独立目录；pip 安装 uv 0.13.6；`uv sync` 成功（CPython 3.12.16，75 包）；`--extra launcher-windows` 成功（+6 winrt 包）；`import civ_mcp` 通过；用户级 skill 包装建立于 `~/.agents/skills/civ6-mcp/`（仅说明文件，无仓库代码）；Codex `~/.codex/config.toml` 备份后追加 `[mcp_servers.civ6]`（`codex mcp list` 显示 enabled）；游戏 `AppOptions.txt` 的 `EnableTuner` 已是 1。
- 边界与注意：MCP 服务器走 stdio，由客户端拉起；游戏同一时间只允许一个 tuner 连接（先关 SDK 的 `FireTuner.exe`），连接失败后重启游戏，不要从 WSL 运行。本项目不内置、不随源码分享其代码或文档，也不提供副本。
- 未验证：本机未启动游戏，`scripts/test_connection.py` 返回 Connection refused（预期）；握手、对局读取与操作需启动游戏并加载对局后另行验收。MCP stdio `initialize` 冒烟已通过（serverInfo `Civilization VI`）。
- 验证：`python -m modgen.cli skill --check`（167 篇、64 个检索用例、0 个问题）；`python -m unittest tests.test_knowledge_quality tests.test_skills_search tests.test_external_skills tests.test_source_distribution`（49 项通过）；`python tools/share_source.py --check` 通过。
