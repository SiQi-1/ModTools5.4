# 技能库入口与维护约定

制作任务先读 [规则正文](RULES.md) 和 [统一工作流](WORKFLOW.md)，按 [知识地图](SKILLS_OUTLINE.md) 定位资料。即使熟悉该主题，也必须读取对应依据；同会话已读且未变化可复用。

## 分层

- 规则：行为边界和资料依据。
- 指南：当前工具的操作步骤，包含任务必读清单。
- 参考：字段、参数、控件与 API 模式，按章节读取。
- 案例：历史 Mod 的实现线索，需要核实目标环境。

## 检索

```powershell
python -m modgen.cli skill "城市奇观相邻加成"
python -m modgen.cli skill "UI 按钮" --plan --json
python -m modgen.cli skill --file RULES.md
python -m modgen.cli skill --check
```

检索只收录 Markdown；维护归档不索引。结果给出文件、章节、行号、类别和片段；用 `--file` 加 `--section` 读取章节。`search` 查游戏现成实现，`query` 查表，`loc` 查文本。

## 维护

任务映射由 [catalog.json](catalog.json) 维护；新增/移动资料登记到相应 INDEX，叶子资料可从目录链接到达。通用规则不复制到每篇案例，允许在回答中简短注明依据。

修改后运行 `python -m modgen.cli skill --check` 与 `python -m unittest tests.test_skills_search tests.test_knowledge_quality -v`。质量检查包括断链/锚点、入口覆盖、过时工作流引用、重复文档及检索场景。
