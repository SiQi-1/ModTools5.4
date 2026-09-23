# 制作规则（任务开始时必读）

本文件是制作 Mod、编写 .CIV、回答游戏实现问题的统一行为规范。命令参数以 [modgen 契约](../modgen/AGENTS.md) 为准；具体游戏知识按 [资料依据](SOURCES.md) 验证。维护工具代码另读 [开发约定](../CLAUDE.md)。

## R1 查证先于实现

- 无论是否熟悉，都先读本文件和 [统一工作流](WORKFLOW.md)，再按 [任务目录](catalog.json) 读取命中的必读资料；不要通读整个知识库。
- 用 `python -m modgen.cli skill "任务描述" --plan` 获取必读清单；搜索结果只是定位，必须打开对应章节。
- 实现或给出确定结论前，简短列出“采用的文件/章节 → 本任务结论 → 待验证项”。同会话已经读过且未变化的资料可复用，注明出处即可。
- 没搜到答案时，拆词、换中文/英文 Type、查所属 INDEX，再查真实数据或官方调用点。零结果不能证明能力不存在；禁止凭记忆补出类型、API、字段或断言做不到。
- 实测、官方代码、工具校验和推断须区分。历史案例是线索，不能视为全部环境可用的保证。

## R2 数据来源与冲突

- 工具命令/字段：当前 CLI `--help`、契约、schema 与实现；游戏参数：官方定义、随包快照、目标环境只读查询。具体入口见 [SOURCES](SOURCES.md)。
- 判断 ModifierType 是否原版，以随包 `vanilla_modifier_types.json` 为准；运行缓存可能混入其他 Mod。
- 文档相互冲突时核对当前实现和来源，在交付中说明采用依据；维护任务同步修正文档。不要任选一份照抄，也不要伪造缺失的旧脚本或数据文件。

## R3 类型与参数

- ModifierType 优先复用符合语义的原版类型。EffectType、RequirementType、CollectionType 必须有真实定义，不能按名字猜。
- 确需自定义 ModifierType 时使用项目命名，填写合法 CollectionType/EffectType，由工具生成 Types 与 DynamicModifiers 注册。外部 Mod 用过不等于原版存在。
- 确认 owner/subject、挂载对象、参数和条件链；字段存在不代表语义成立。读 [修改器操作指南](05-modtools-civ/modifiers.md) 与 [通用技巧](07-techniques/modifier-techniques.md)。
- `EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER` 必须填写 `preview_text`；不可把该规则推广到所有 EffectType。

## R4 数据与写入边界

- 主内容通过 `new-project`、`generate`、`generate-*` 建骨架，Type 由工具生成，再按 schema 填入意图；不靠复制旧工程搭新骨架。
- AI 编写的 JSON 值禁止空字符串：省略字段或写 `null`，不要写字符串 `"null"`、通用占位 `"NONE"`。参数名和枚举需查证，图片路径必须真实。
- 主内容不手写 SQL/XML，不把 Lua 塞进条目。确需特殊 SQL、UI XML 或 Lua，内容临时文件放 `modgen_work/`，先启用 [项目级扩展](05-modtools-civ/project-extensions.md)，通过 `extension write` / `custom-file write` / AI `extension` 写入源码并按清单注册；工具是工程文件的唯一写入者。
- 默认将未被 .CIV 支持的 Gameplay SQL 集中到 Core.sql；不同数据库作用域或前后阶段有明确需求时再分文件。一次规划完整功能的数据、GP、UI、文本与资源，登记功能归属和依赖。源码和 ModBuddy 输出分离，缺失源码不得用输出副本替代。
- 修改生成内容应回到 .CIV；自定义 SQL 不得与生成数据同主键双写，不得为消除告警随意改成 REPLACE。
- **仓库边界**：ModTools 仓库只版本管理通用工具代码、文档、参考数据和可复用测试。单个 Mod 的 `.CIV`、`*.extensions/`、专用脚本/测试、交接报告、日志、预览、美术与构建包保存在本地，不提交到工具仓库；新项目及其工作资料默认集中到 `modgen_work/<工程名>/`，或用户指定的仓库外目录。已有工程保持路径并补齐忽略规则；正式源码必须保留和备份，不能当作缓存删除。只有独立的 Mod 源码仓库才将 `.CIV` 与扩展源码一起纳入版本管理。

## R5 按任务读取

| 涉及内容 | 额外必读 |
|---|---|
| 工程/实体 | [工程入口](05-modtools-civ/INDEX.md)、对应实体模板 |
| Modifier/条件/能力 | [修改器指南](05-modtools-civ/modifiers.md)、[实现前清单](07-techniques/modifiers/patterns/pre-code-checklist.md) |
| Lua/事件 | [Lua 规范](04-lua/code-style.md)、[Lua 索引](04-lua/INDEX.md) 中对应模式 |
| UI/按钮/控件 | [控件参考](04-lua/lua-xml-controls.md)、[美术与文本指南](05-modtools-civ/ui-assets.md) |
| 图标/背景/纹理/LOC | [美术与文本指南](05-modtools-civ/ui-assets.md)，区分实体图标、UI图标、独立纹理与自定义文本 |
| 自定义 SQL/XML/Lua | [项目级扩展](05-modtools-civ/project-extensions.md)、[自定义文件与交付](05-modtools-civ/pipeline.md) |

## R6 验证与交付

- 保存/合并前 `validate`；ERROR 必须修复，WARNING 逐项说明处理依据。
- 扩展工程执行 `project-check` 统一检查数据、源码、依赖、预览、动作及 SQL 冲突；用 `preview` 核对具体内容。旧自定义 SQL 流程继续使用 `check-conflicts`。完整检查/预览需 PyQt，`extension check` 等纯数据命令不需要。
- 检查引用、挂载链、文本、动作注册及输出目录。构建、部署、游戏内测试分别记录；校验通过不能宣称实机效果已验证。
- 无法执行某项验证时说明原因和剩余步骤，继续完成可执行的检查。交付包括变更、依据、验证结果及尚未确认的边界。

## R7 知识维护

- 通用行为规则只在此维护；操作步骤进入指南，参数进入参考，可复用经验进入案例；单个 Mod 的交接、日志和验收记录遵守 R4 的本地工作目录约定。入口使用链接，避免复制多份规则正文。
- 新增/移动文档须登记到相应 INDEX；任务必读映射维护 [catalog.json](catalog.json)。历史来源应标注，不能成为发布包运行依赖。
- 修改后运行 `python -m modgen.cli skill --check` 和知识回归测试。通过检查表示结构/检索用例合格，不代表全部游戏知识经过实机验证。
