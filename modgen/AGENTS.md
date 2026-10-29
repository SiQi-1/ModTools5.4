# modgen —— 文明6 Mod 工程(.CIV) 生成与校验工具

> **本文件是 AI Agent 的必读说明**。使用本目录的工具生成/校验 .CIV 工程前，请先完整阅读。
> 读法：
> ① 先读「必须遵守的工作流」「硬规则」「本地 Mod 工程约定」，这是行为边界；
> ② 具体命令、参数、输出格式查 [命令清单](docs/cli-reference.md)；
> ③ 专项任务按「专项通道索引」只读对应一篇 docs/channels/*.md，不要通读整个 docs/。
>
> 制作规则见 [RULES](../skills/RULES.md)，执行顺序见 [统一工作流](../skills/WORKFLOW.md)。本文件只维护命令与字段契约；工具开发见 [开发约定](../docs/dev/architecture.md)。

## 本工具是什么

生成"合规的文明6 Mod 工程条目"（.CIV 工作区结构），而不是直接生成 SQL/XML。
规则来自 ModTools 5.4 编辑器（GUI）——工具生成的条目保证编辑器能打开、能正确导出。

- **不依赖** PyQt6 / GUI 的数据与 extension 命令为纯标准库；preview / check-conflicts / project-check / build 使用 GUI 生成引擎，需 PyQt
- **Type 永远由工具生成**，AI 不要手写 Type（详见"硬规则"）
- 中文文本存条目（name/Description 等），LOC tag 由导出约定自动注册，条目里不写 LOC

## 分发契约

以 skill + tools 源码目录为准，不依赖内置 EXE/ZIP。`modgen/` 与 `ModTools_5_4/`、`skills/` 及 schemas 必须一起分发；维护者用 `python tools/share_source.py --out shares/<新目录>` 导出当前已跟踪源码。安装和可选依赖见 [初始化](../docs/user/install.md)，Git/来源清单约定见 [分享说明](../docs/meta/source-sharing.md)。

## 必须遵守的工作流

先读 [规则正文](../skills/RULES.md) 与 [统一工作流](../skills/WORKFLOW.md)，执行 `skill "任务描述" --plan` 并读取相关章节。先核实依据，再 new-project / generate / validate / merge；已有工程只修改目标内容。扩展任务执行 project-check / build；旧自定义 SQL 用 check-conflicts，预览、工程导出、部署和实机分别验收。

## 硬规则（生成/校验的依据）

- **Type 命名**：`{HEAD}_{前缀}_{中缀}{编号:04d}_{简称}`（如 `CIVILIZATION_SIQI_C0035_1`）。
  生成器按简称自动生成，AI 手写 type 会被 validate 警告/报错。
- **必填字段**：条目必须有 `name`（中文名）+ 分类标识（多数分类 `abbr`，总督用 `code`）。
  主表必填字段见 `schemas/entry_schemas.json` 中 `required` 字段；无默认值的必填字段（如单位 `FormationClass`）必须由 AI 填写。
- **主表 SQL 稀疏输出**：导出器只写主键/Type、Name、Description 和确有值的字段；可选空字符串、`None`/`NULL` 哨兵从列清单中省略。多行记录按实际列集合分组生成 INSERT，禁止为了复用一套列清单填充无意义的连续 `NULL`。必填字段缺失由 validate/project-check 报错，不能用 NULL 占位绕过校验。
- **DynamicModifiers 注册完整性**：需要新建的 ModifierType 必须同时提供 `effect_type` 与 `collection_type`；缺失时 validate/project-check 报错，导出器不生成 NULL 占位行。
- **LOC**：文本字段存中文，不写 `LOC_` 前缀 tag；导出时自动注册。
- **图片**：项目图标有图片槽（目标 **256×256**，`images.icon` 已预填尺寸骨架，AI 只需填 `path`）；信仰 `has_images=False`（GUI 无图片槽，图标经美术页别名/数据库处理，无需导入图片）；其余分类一律空 `images: {}`，路径由用户提供。
- **图标名**：约定 `ICON_{Type}`，由生成器自动填（如 `ICON_PROJECT_SIQI_P0035_TEST`）。
- **引用**：`bindings` / `trait_bindings` 中的 section/name 必须指向存在的对象。
- **议程绑定**：只用议程 `historical_agendas.LeaderType` 指定领袖；不要放入 `bindings` / `trait_bindings`。议程 Trait 通过 `AgendaTraits` 挂载，不进入 `LeaderTraits` / `CivilizationTraits`。校验会提示旧写法；导出兼容将旧领袖议程绑定转为 `HistoricalAgendas`，显式历史议程归属优先。

- **项目级扩展 / custom-file / 加载顺序 / 兼容**：完整规则见 [扩展通道](docs/channels/extensions.md)；未启用 extensions 的旧 .CIV 不变。

## 分类说明

| 分类 | Type 前缀 | 标识键 | 备注 |
|---|---|---|---|
| 文明 | CIVILIZATION | abbr | trait_bindings 绑定特色对象 |
| 领袖 | LEADER | abbr | bindings 绑定所属文明等 |
| 区域 | DISTRICT | abbr | 主表 table_data + 子表 |
| 建筑 | BUILDING | abbr | 主表 table_data + 子表 |
| 单位 | UNIT | abbr | FormationClass 必填无默认 |
| 单位晋升 | PROMOTION_CLASS | type | 晋升树，nodes 列表 |
| 改良设施 | IMPROVEMENT | abbr | PlunderType 必填（默认 NO_PLUNDER） |
| 总督 | GOVERNOR | code | 顶层无 type，用 GovernorType |
| 伟人 | GREAT_PERSON_CLASS | (class_data) | 个体在 individuals |
| 政策卡 | POLICY | abbr | |
| 项目 | PROJECT | abbr | |
| 信仰 | BELIEF | abbr | |
| 议程 | AGENDA | (type) | 顶层无 abbr |
| **UI图标** | （无 Type） | icon_name | **非实体分节**：与游戏实体无关的自定义 UI 图标（新闻分类/单位动作/追踪器…），只出 `Icons.xml` 与 IMG/Textures，见 [命令清单](docs/cli-reference.md) |

## 本地 Mod 工程与临时文件约定（必须遵守）

遵守 [R4 仓库边界](../skills/RULES.md#r4-数据与写入边界)，具体目录与 Git 验收步骤见 [统一工作流](../skills/WORKFLOW.md)。

- 新 Mod 工程及专用工作文件默认集中在 `workspace/mods/<工程名>/`，已有工程位置保持不变；`.CIV` 和同级 `*.extensions/` 由仓库忽略，源码仍需保留和备份。
- **所有临时条目、Mod 专用生成/修复脚本、专用测试、报告、预览和构建包一律写入 `workspace/` 对应目录**（整个 `workspace/` 已 gitignore，绝不提交）：工程 `mods/`、临时文件 `scratch/`、预览 `preview/`、报告 `reports/`。通用工具回归测试仍放 `tests/` 或 `modgen/tests/`。
- 不要在任何其他位置留下生成中间文件（工程目录、仓库根、modgen/ 内）。
- `generate` 输出是 stdout——能直接消费就不要落盘；必须落盘时用 `workspace/scratch/`。
- merge 会在工程旁生成 `.CIV.bak`（自动备份，已 gitignore，下次覆盖）。

## 专项通道索引（按触发条件只读一篇）

| 若涉及… | 读 |
|---|---|
| 具体命令、参数、输出格式、字段说明、知识查询全量命令 | [docs/cli-reference.md](docs/cli-reference.md) |
| 项目级扩展、extension/custom-file、加载顺序、兼容、project-check/build 细节 | [docs/channels/extensions.md](docs/channels/extensions.md) |
| 地标 AST、Landmarks 资源包、landmark catalog/compose/import/verify/cook | [docs/channels/landmark.md](docs/channels/landmark.md) |
| HTML→UI 纹理、texture render/import-manifest/verify | [docs/channels/texture-html-ui.md](docs/channels/texture-html-ui.md) |
| 头像/图标/历史时刻 PSD 模板、image inspect-psd/extract-psd/render/check | [docs/channels/image-templates.md](docs/channels/image-templates.md) |
| 领袖外交表情差分、fallback_images | [docs/channels/leader-fallback.md](docs/channels/leader-fallback.md) |
| 资源/音频/美术/工坊产物检查、assets/audio/art/workshop check、--cooker-config | [docs/channels/assets-audio-art.md](docs/channels/assets-audio-art.md) |
| 原生相邻规则、text-icons 描述图标、adjacency 命令 | [docs/channels/adjacency-text.md](docs/channels/adjacency-text.md) |

## 知识查询（skill --plan）

先执行 `python -m modgen.cli skill "任务描述" --plan`，只读返回的 must 项与建议章节；再按需 `skill --file <相对路径> --section "<章节>"`。全量参数、语义与 search/query/loc 见 [命令清单](docs/cli-reference.md#知识与证据查询)。
