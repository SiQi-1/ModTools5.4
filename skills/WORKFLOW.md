# 统一工作流

适用：做 Mod、修改 .CIV、回答效果实现问题。仅回答问题时执行步骤 1～3，附上依据；有交付任务时执行到步骤 6。行为要求见 [规则正文](RULES.md)。

## 1 识别任务并读取依据

```powershell
python -m modgen.cli skill "UI 按钮背景和独立纹理" --plan
python -m modgen.cli skill "按钮背景" --json
python -m modgen.cli skill --file 05-modtools-civ/ui-assets.md --section "独立 UI 纹理（背景 / 按钮 / 精灵表）"
```

读取全局规则、命中任务的必读资料和相关章节。复杂任务可以命中多个主题；不要只选一个。未命中时查 [知识地图](SKILLS_OUTLINE.md) 的目录入口。查询英文名称用完整词/Type，不靠词中子串。

## 2 建立实现依据

列出需求如何落到实体、修改器、文本、美术或自定义文件。每个关键判断说明技能文件/章节；需要确认的 Type、参数、API 用 [资料依据](SOURCES.md) 查询。输出简短依据摘要，例如“按钮状态帧：控件参考 → 正 Y 向下；源图尺寸：已检查；游戏内显示：待验证”。

## 3 一次规划并实现完整功能

涉及替代区域，先运行 `modgen adjacency show 原区域 --ruleset base|expansion1|expansion2`，保留完整原规则清单并标明每项复用/改写/移除；涉及改良相邻，先检查 `improvement_adjacencies`。原生表不能表达的距离、动态条件才进入 Modifier/Lua 设计。

新增文明时同时完成[文明文化美术配置](05-modtools-civ/civilization-art.md)：在美术页为每个文明填写城市/建筑文化及单位文化。`ethnicity`、音乐和立绘不替代该配置；已有工程先核对已填写内容。

需要计数时先画出来源对象→目标对象的挂载链，核对每一层 owner、subject、距离与受益玩家；线性计数用逐来源效果叠加，类型/存在性使用原生条件。进入 Property 前写明缺少的原生表达能力；确需二进制时登记最高位、总上限、取整和超限方式，再同步 Lua/条件/Modifier/挂载四处。

| 内容 | 路径 |
|---|---|
| 工程/实体 | `new-project` → `generate` → 填字段 → `validate` → `merge` |
| 修改器/条件/能力 | `generate-modifier` / `generate-requirement` / `generate-reqset` / `generate-ability`，见 [指南](05-modtools-civ/modifiers.md) |
| 自定义 UI 图标、纹理、LOC | [美术与文本指南](05-modtools-civ/ui-assets.md)；纹理用 `texture add/list/remove` |
| 自定义 SQL/XML/Lua | `extension init` → `extension write`；源码、功能归属和依赖见 [项目级扩展](05-modtools-civ/project-extensions.md) |

例如一个建筑触发事件面板：建筑/Modifier 用 .CIV，配置数据用 Core.sql，事件用 Gameplay Lua，面板用 UI XML/Lua，LOC/纹理用文本与美术。先确定共享标识、运行环境与依赖，再一起实施和验收。按 [R4 仓库边界](RULES.md#r4-数据与写入边界) 保存工程与源码；在独立 Mod 仓库管理版本时，二者一起提交。ModTools 仓库不收录单个 Mod 的工程、源码与产物。

命令完整参数见 [modgen 契约](../modgen/AGENTS.md)。新工程及专用工作资料默认放 `modgen_work/<工程名>/`，例如 `modgen_work/示例/示例.CIV`、同级 `示例.extensions/`、`scripts/`、`verify/`、`reports/`、`preview/` 和 `ModBuddy/`；也可使用用户指定的仓库外目录。已有工程保留原路径，通过忽略规则隔离，避免迁移破坏资源引用。

## 4 校验与预览

设计稿导入后，先用 `modgen text-icons format --role description --text "描述"` 生成候选，再按语义复核、写入工程描述字段；名称不加产出图标。已有标记不得重复，用户原稿可以保持纯文字。`text-icons check` 可单独复查整个工程。

```powershell
python -m modgen.cli validate 工程.CIV
python -m modgen.cli preview 工程.CIV --dry-run
python -m modgen.cli preview 工程.CIV --section 修改器
python -m modgen.cli project-check 工程.CIV --json
```

最后一项统一检查完整工程；旧自定义 SQL 可继续使用 check-conflicts。preview 写预览目录，不等于导出到 ModBuddy。修 ERROR，解释 WARNING，检查引用、挂载和语义；数据库可执行不保证游戏内条件生效。

## 5 生成与部署

`project-check` / `build` 还会报告替代区域的原生相邻缺项、等价 custom 重复定义，以及描述缺失/未知字体图标。原规则不同的设计必须逐项解释，不自动补回或删除。快照规则集按声明的资料片依赖推断，未声明时为本体；可用 `adjacency check 工程.CIV --ruleset expansion2` 明确复核。最后核对实际生成的 District_Adjacencies / Improvement_Adjacencies，不能只检查 Adjacency_YieldChanges 有无定义。

先绑定独立的 ModBuddy 输出目录，再统一生成：

```powershell
python -m modgen.cli civ6proj 工程.CIV --out modgen_work/ModBuddy --update-civ
python -m modgen.cli build 工程.CIV --overwrite all --json
```

也可用 GUI 或 [AI 控制接口](../ModTools_5_4/docs/AI_CONTROL_API.md) `generate_all`。扩展以源码目录为准同步，工具从清单生成独立动作；缺失源码、冲突与无效依赖会阻断生成。build 默认 none 保留已有输出，使用 all 才将新源码覆盖到旧输出。ModBuddy 构建与美术 Cooker、部署到游戏 Mods 目录是后续步骤，不能把预览、源文件生成、构建与实机验证混为一谈。

按[文化美术出口检查](05-modtools-civ/civilization-art.md#生成后检查实际成员关系)核对 `ArtDefs/Cultures.artdef` 中的文明成员、`Civilizations.artdef` 目标及 Art.xml 的 consumer 引用；空文件或仅存在文件不算完成。

## 6 交付与知识回流

交付前执行 `git status --short --untracked-files=all`，确认没有新增单个 Mod 的专用文件；用 `git check-ignore -v -- <路径>` 核对规则，再用 `git ls-files -- <路径>` 检查是否早已被跟踪。忽略规则不会影响已跟踪文件：若需移出工具仓库，先核对用途和本地备份，再对明确路径执行 `git rm --cached -- <文件>`，保留本地副本；不要批量取消跟踪通用工具文件，也不要强制添加被忽略的 Mod 产物。

报告 .CIV/工程位置、采用的规则、校验结果、构建/实机状态。新发现写入对应指南或案例，标注验证环境；修正文档矛盾并更新 INDEX，不向不存在的外部 memory 目录写资料。
