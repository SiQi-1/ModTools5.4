# .CIV 制作指南（guides）

> 受众：用 ModTools/modgen 做 .CIV 工程与交付的制作者 ｜ 何时读：动手操作前 ｜ 适用版本：ModTools 5.4

先读 [规则正文](../RULES.md) 和 [统一工作流](../WORKFLOW.md)。本库与 ModTools 同仓库发布，直接使用当前 schema、CLI 和实现，无外部快照同步步骤。

## 按任务读取

| 文档 | 用途 |
|---|---|
| [工程格式](civ-project-format.md) | workspace / 18 分节 / 字段形态 |
| [实体模板目录](../reference/entities/INDEX.md) | 按涉及的实体选模板；命名见 [命名参考](../reference/entities/naming.md) |
| [修改器指南](modifiers.md) | 原版/自定义类型、参数、预览文本 |
| [项目级扩展](project-extensions.md) | Core.sql、Lua/UI、源码清单、依赖、project-check/build |
| [自定义文件与交付](pipeline.md) | SQL/XML/Lua 通道、动作、加载顺序、部署 |
| [常见陷阱](civ-pitfalls.md) | 数据、挂载、语义与生成后的自检 |
| [实机测试](testing.md) | 用户同意门禁、默认纯净环境、兼容性测试、测试后还原与验收分层 |

## 美术、文本与发布（reference/）

| 文档 | 用途 |
|---|---|
| [美术与发布目录](../reference/art/INDEX.md) | 领袖/文明美术、音频、Blender、解包、Cooker、工坊 |
| [文明文化美术](../reference/art/civilization-art.md) | Culture / UnitCulture 配置、Cultures.artdef 文明成员与 Art.xml 引用 |
| [UI 美术与文本](../reference/art/ui-assets.md) | UI图标、独立纹理、按钮背景、自定义 LOC |
| [文本规范](../reference/config/text.md) | 本地化文本、LOC 键命名、图标嵌入 |
| [相邻加成](../reference/config/district-adjacency.md) | 区域/改良原生相邻与继承 |
| [工程文件与动作顺序](../reference/project/civ6proj.md) | .civ6proj 模板、FrontEnd/InGame 动作顺序、输出目录 |

## 可分享技能包

- [HTML → 原生 UI](../packages/civ6-html-ui/SKILL.md)：设计/渲染/批量导入/像素校验与 XML/Lua。
- [地标与 AST 组合](../packages/civ6-landmarks/SKILL.md)：官方几何复用、Landmarks、建筑差分、资源包导入和 Cooker。
- [头像/图标/历史时刻模板](../packages/civ6-art-images/SKILL.md)：PSD 图层提取、PNG 配方处理、多模态边界与像素检查。

## 当前依据

[命令契约](../../modgen/AGENTS.md)、[实体 schema](../../modgen/schemas/entry_schemas.json)、[修改器 schema](../../modgen/schemas/modifier_schemas.json)。游戏枚举/API 的核实路径见 [资料依据](../SOURCES.md)。
