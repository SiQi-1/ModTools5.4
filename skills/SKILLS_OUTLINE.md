# 知识地图

## 常驻入口

[规则正文](RULES.md) → [统一工作流](WORKFLOW.md) → [任务必读映射](catalog.json)。资料冲突或旧来源不可用时读 [SOURCES](SOURCES.md)。维护方法见 [AGENTS](AGENTS.md)。

## 操作指南

[.CIV 指南](05-modtools-civ/INDEX.md) 包含实体、修改器、UI图标、独立纹理、LOC、自定义文件和交付。操作指南优先于历史案例；完整命令契约在 [modgen](../modgen/AGENTS.md)。

## 参考与案例

- [核心表目录](01-core-tables/INDEX.md)：实体 SQL 结构，主内容仍经工具生成。
- [配置文件目录](02-config-files/INDEX.md)：配色、文本、图标等参考。
- [工程注册目录](03-project-file/INDEX.md)：工程文件与动作参考。
- [Lua 目录](04-lua/INDEX.md)：规范、控件、事件/API 模式及历史案例。
- [技巧目录](07-techniques/INDEX.md)：Modifier 通用语义、参数、实现模式和案例。
- [命名参考](06-naming.md)、[相邻加成](district-adjacency.md)：专题参考。

## 渐进读取

`skill "任务" --plan` 返回必读文件；搜索返回命中的章节和行号；`--file 路径 --section 章节名` 读取该章节及其子节，省略 --section 仍可读全文。不要为小任务一次加载全部参数参考。

维护脚本与重复草稿已移出知识库，归档不参与检索。新增文件要能从上述目录通过链接到达，检查命令为 `python -m modgen.cli skill --check`。
