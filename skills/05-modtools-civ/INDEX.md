# .CIV 制作指南

先读 [规则正文](../RULES.md) 和 [统一工作流](../WORKFLOW.md)。本库与 ModTools 同仓库发布，直接使用当前 schema、CLI 和实现，无外部快照同步步骤。

## 按任务读取

| 文档 | 用途 |
|---|---|
| [工程格式](civ-project-format.md) | workspace / 18 分节 / 字段形态 |
| [实体模板目录](entity-templates/INDEX.md) | 按涉及的实体选模板 |
| [修改器指南](modifiers.md) | 原版/自定义类型、参数、预览文本 |
| [UI 美术与文本](ui-assets.md) | UI图标、独立纹理、按钮背景、自定义 LOC |
| [常见陷阱](civ-pitfalls.md) | 数据、挂载、语义与生成后的自检 |
| [制作参考](authoring-reference.md) | 命名、相邻加成、TypeProperties |
| [自定义文件与交付](pipeline.md) | SQL/XML/Lua 通道、动作、加载顺序、部署 |

## 当前依据

[命令契约](../../modgen/AGENTS.md)、[实体 schema](../../modgen/schemas/entry_schemas.json)、[修改器 schema](../../modgen/schemas/modifier_schemas.json)。游戏枚举/API 的核实路径见 [资料依据](../SOURCES.md)。
