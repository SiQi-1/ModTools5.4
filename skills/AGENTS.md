# 技能库入口与维护约定

> 受众：AI 与知识库维护者 ｜ 何时读：制作任务开始、改知识库结构时 ｜ 适用版本：ModTools 5.4

制作任务先读 [规则正文](RULES.md) 和 [统一工作流](WORKFLOW.md)，按 [知识地图](SKILLS_OUTLINE.md) 定位资料。即使熟悉该主题，也必须读取对应依据；同会话已读且未变化可复用。

## 分层

- 根：规则（RULES）、流程（WORKFLOW）、地图（SKILLS_OUTLINE）、来源（SOURCES）、外置名单（EXTERNAL_SKILLS）、机器可读映射（catalog.json、retrieval_cases.json）。
- `guides/`：当前工具操作步骤，含任务必读清单。
- `reference/`：按性质分 `entities/`（条目键与命名）、`sql/`（生成 SQL 列含义，仅核对）、`config/`、`project/`、`lua/`、`modifiers/`（EffectType 分册）、`art/`；字段与参数按章节读取。
- `packages/`：5 个可整包分享的技能包（SKILL.md + references/scripts/assets）。
- `_archive/`：下划线前缀不索引；旧草稿/待删资料。

## 检索

```powershell
python -m modgen.cli skill "城市奇观相邻加成"
python -m modgen.cli skill "UI 按钮" --plan --json
python -m modgen.cli skill --file RULES.md
python -m modgen.cli skill --check
```

检索只收录 Markdown；`_` 前缀目录不索引。结果给出文件、章节、行号、类别与片段；`--plan` 返回 must/optional、字节数与 max_kb 告警。用 `--file` 加 `--section` 读取章节。`search` 查游戏现成实现，`query` 查表，`loc` 查文本。

## 维护

任务映射由 [catalog.json](catalog.json) 维护；新增/移动资料登记到相应 INDEX，叶子资料可从目录链接到达。通用规则不复制到每篇案例，允许在回答中简短注明依据。

外置技能包不在本目录内置：只在 [外置技能名单](EXTERNAL_SKILLS.md) 登记名单、署名与本机安装/检索方法；包体不入 Git、不随源码分享，不代替作者发布。

修改后运行 `python -m modgen.cli skill --check`、`python -m unittest tests.test_skills_search tests.test_knowledge_quality -v` 与 `python tools/doc_lint.py`。质量检查包括断链/锚点、入口覆盖、catalog 覆盖、过时工作流引用、重复文档、检索场景与必读预算。
