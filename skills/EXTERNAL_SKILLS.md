# 外置技能名单（不随仓库分发）

本页登记**未纳入 Git、不随源码分享**的外置技能。仓库只保留名单、作者署名、来源信息与本机安装/检索方法；不内置原件、不提供下载或副本，也不代替作者发布。名单分为两类：

- **仅名单**：原件不公开，需要时向作者获取压缩包，安装到本机 `workspace/local_skills/`（已由 Git 忽略）；
- **公开仓库**：可按本节网址自行拉取（clone）到本机仓库外目录，本项目只记录网址、版本与许可，不复制其代码或文档。

## civ6-model-import：UE 模型导入文明6领袖 3D

| 项目 | 内容 |
|---|---|
| 技能名 | civ6-model-import |
| 作者 / 署名 | 千寻瀑（用户提供署名） |
| 原始包 | `civ6-model-import.zip`，完整分发版，包内版本 2026-10-27 |
| 大小 / SHA-256 | 12,594,811 字节 / `2d9f3727303fa71c651658e356bc3128dad655317d9a9c66d9387e99c7c7026f` |
| 内容 | `SKILL.md`、7 篇 `references/` 文档、`scripts/` 转换与采样脚本、C# 读数工具源码、`patches/UAnimSequence.cs`，以及 `tools/CivNexus6/` 转换工具链（含未签名 exe 与 Firaxis/Granny/FBX 程序集） |
| 适用 | 把 UE 工程（鸣潮等）的 psk 模型与 ueanim 动画导入文明6，作为领袖 3D 模型；含十步流程、四条采信判据、朝向/口型/眨眼处理与跨会话交接模板 |
| 不适用 | 引用原版模型素材、Blender 通用 fgx/ast 导出、纯 UI/音频任务；这些仍走本项目既有指南 |
| 本机安装 | `workspace/local_skills/civ6-model-import/`（Git 忽略；换机器重新向作者取得后解压） |
| 取得方式 | 向作者 **千寻瀑** 索取压缩包；本仓库不提供下载、不内置原件、不代替作者发布 |

### 本机安装与检索

1. 从作者处取得 `civ6-model-import.zip`，解压到仓库的 `workspace/local_skills/`，得到 `workspace/local_skills/civ6-model-import/SKILL.md`。
2. 外置技能不并入默认 `skills/` 索引，按目录检索与读取：

   ```powershell
   python -m modgen.cli skill "领袖3D模型 psk ueanim 导入" --skills-dir workspace/local_skills/civ6-model-import
   python -m modgen.cli skill --file SKILL.md --skills-dir workspace/local_skills/civ6-model-import
   ```

3. 按包内 `SKILL.md` 的开工自检与参数槽位执行；工具链部署位置以包内 `references/upstream.md` 为准，部署到工程树外。

### 边界与署名

- 压缩包原件与解压内容不进入 Git，也不进入源码分享目录；`tools/share_source.py --check` 会拒绝被误跟踪的 `local_skills/` 文件。
- 包内未发现独立 LICENSE 文件；`tools/CivNexus6/` 的 Firaxis/Granny/FBX 程序集与未签名 exe 来自作者的 CivNexus6 构建产物，许可以上游为准；本项目不复制、不重新分发。
- 包内文档的本机绝对路径、工程常量与实测结论只在该包语境有效，不自动成为本项目通用规则；需要时按本项目 [规则正文](RULES.md) 与 [统一工作流](WORKFLOW.md) 复核。
- 本机未安装该包时检索不到属正常情况，不代表能力不存在；先按上方向作者取得。

## civ6-mcp

MCP 服务器：通过 FireTuner（TCP 4318，单连接）把文明6对局状态与操作暴露给 LLM agent，共 76 个工具（单位、城市、地图、科技、外交、贸易、政府、宗教、伟人、世界议会、胜利进度、存读档），附带对局 playbook。

| 项目 | 内容 |
|---|---|
| 技能名 | civ6-mcp |
| 作者 / 许可 | Liam Wilkinson（GitHub [lmwilki](https://github.com/lmwilki)）；MIT |
| 仓库网址 | https://github.com/lmwilki/civ6-mcp |
| 版本 / 审阅提交 | v1.1.11；`dd2019056371b92ea4854e879ddf05a8cad95e8a`（2026-05-03） |
| 需求 | Python 3.12+、uv、Civ6（Steam，含 Gathering Storm）、Civ6 SDK、游戏内启用 Tuner（会禁用成就）、MCP 客户端（Claude Code / Codex / Gemini CLI 或任意 MCP 客户端） |
| 拉取与运行 | `git clone https://github.com/lmwilki/civ6-mcp` → `uv sync` → stdio 服务器 `uv run civ-mcp`；仓库自带 `.mcp.json`（Claude Code 自动识别） |
| 本机安装 | 拉取到本项目仓库之外的独立目录（路径按本机自定），不进入本项目 Git，不随源码分享；本机实际路径、依赖与客户端配置记录在 Git 忽略的本地安装记录中 |
| 注意 | 游戏只允许一个 tuner 连接：先关闭 SDK 的 `FireTuner.exe`，同一时间只开一个 MCP 客户端；连接失败后重启游戏；不要从 WSL 运行 |

对局操作规范读仓库内 `AGENTS.md`（回合循环、外交、常见坑）；本仓库不复制、不炼化其 playbook。需要窗口/OCR 自动化时按上游 README 安装 `civ6-mcp[launcher-windows]`，并要求游戏窗口化。

本项目只记录网址、版本与许可，不复制其代码或文档；本机 clone 目录与 MCP 客户端配置都在仓库之外。

### 在 DSH（DeepSeek Harness）中使用

DSH 的本地 skill 提供方按 rank 扫描：项目根 `.dsh/skills`、`.agents/skills`、自定义目录、`~/.dsh/skills`、`~/.agents/skills`；只识别根目录下 `<name>/SKILL.md`（目录 bundle）或 `<name>.md`，不递归。

- 上面两个外置技能已安装在本机 `~/.agents/skills/`，DSH 会话会自动识别，无需额外配置。
- 本仓库 `skills/packages/` 的 5 个可分享技能包可用安装器接入 DSH（Windows 目录联接，零拷贝、不占额外空间）：

  ```powershell
  python tools/install_skills.py --target dsh --link
  ```

  该命令在 `~/.dsh/skills/` 下创建指向仓库 `skills/packages/<name>/` 的 Junction，DSH 会在下一次目录刷新时出现这些技能；移除时删除对应 Junction 即可。
- 其它 agent：`--target claude` / `--target codex` / `--target agents`，或 `--dir <目录>`；不加 `--link` 时复制文件。

### 更新与移除（Junction 方式）

- **更新已有技能**：Junction 指向仓库目录，直接改 `skills/packages/<name>/` 即可，无需重装或重启 DSH。`SKILL.md` 的 frontmatter（name/description）变更会触发 DSH 目录刷新；正文在每次调用 `skill` 时重新读取（2026-10-29 用临时技能实测：新增、改 description、改正文、删除均即时生效）。`references/`、`scripts/`、`assets/` 编辑不会触发目录刷新，但资源路径经 Junction 解析到仓库，按需读取时总是最新。
- **新增技能包**：重跑 `python tools/install_skills.py --target dsh --link`；已存在的会跳过，加 `--force` 重建链接。
- **改名/移动仓库目录**：Junction 会悬空，需删除旧链接后重跑安装器（安装器会校验 `name` 与目录名一致）。
- **移除**：删除对应 Junction 即可（`cmd /c rmdir "%USERPROFILE%\.dsh\skills\<name>"`，不会删除仓库目录），DSH 下一步目录即移除该技能。



来源与指纹另见 [第三方来源声明](../THIRD_PARTY_NOTICES.md)，整合记录见 [社区整合记录](../docs/meta/community-integration.md)。
