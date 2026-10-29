# 知识地图

> 受众：AI 与维护者 ｜ 何时读：`skill --plan` 未命中，或需要了解知识库全貌时 ｜ 适用版本：ModTools 5.4

## 常驻入口

[规则正文](RULES.md) → [统一工作流](WORKFLOW.md) → [任务必读映射](catalog.json)。资料冲突或旧来源不可用时读 [SOURCES](SOURCES.md)。维护方法见 [AGENTS](AGENTS.md)。

## 分层

| 目录 | 内容 | 何时读 |
|---|---|---|
| `skills/` 根 | 规则、流程、导航、来源、外置名单 | 每次任务开始 |
| `guides/` | 当前工具的操作指南：.CIV 工程格式、修改器、扩展、文件与交付、常见陷阱 | 动手操作前 |
| `reference/entities/` | 实体条目键模板 + Type/Modifier/Requirement 命名 | 新建/修改实体 |
| `reference/sql/` | 生成 SQL 的列含义（**只用于核对**，禁止手写） | 核对导出结果时 |
| `reference/config/` | 文本/LOC、配色、图标、Configs 注册、原生相邻 | 配置与文本 |
| `reference/project/` | .civ6proj 模板、动作顺序、输出目录 | 工程文件与交付 |
| `reference/lua/` | Lua 规范、控件、事件/API 模式、历史案例 | 写 Lua/UI 脚本 |
| `reference/modifiers/` | Modifier 方法 + EffectType 分册 + 模式与案例 | 选效果、查参数 |
| `reference/art/` | 领袖/文明美术、音频、Blender、解包、Cooker、工坊 | 美术与发布 |
| `packages/` | 5 个可分享技能包（HTML UI、地标、明日方舟、AI 对局、图像模板） | 对应专题 |
| `_archive/` | 下划线前缀不索引；旧草稿/待删资料 | 维护 |

## 指南与实体

- [.CIV 指南入口](guides/INDEX.md)：工程、修改器、扩展、文件、交付与常见陷阱。
- [实体模板索引](reference/entities/INDEX.md)：按实体选条目键；[命名参考](reference/entities/naming.md)。

## 可分享的技能包

- [HTML → 文明6原生 UI](packages/civ6-html-ui/SKILL.md)：HTML/CSS 设计、四态纹理、XML/Lua 接入；包含独立脚本、示例和跨 agent 使用说明。
- [地标与 AST 组合](packages/civ6-landmarks/SKILL.md)：改良、区域、建筑差分与 TileBase 注册；配套 `landmark catalog/compose/import/verify/cook`。
- [明日方舟系列](packages/civ6-arknights-series/SKILL.md)：该题材的系列命名、地名和发布准备；附封面 PSD 与排版脚本。
- [AI 控制文明6](packages/civ6-ai-play/SKILL.md)：窗口化启动、FireTuner Lua、Mod 启停、开局、单位移动/建城、截图与日志取证。
- [头像/图标/历史时刻模板](packages/civ6-art-images/SKILL.md)：PSD 图层提取、PNG 配方、像素检查与模板素材。

## 外置技能（仅名单，不随仓库分发）

- [外置技能名单](EXTERNAL_SKILLS.md)：登记 civ6-model-import、civ6-mcp 等外部技能包的作者署名、包指纹与本机安装/检索方法；包体不随仓库分发。

## 参考入口

- [表参考目录](reference/sql/INDEX.md)：生成 SQL 的列含义（仅核对）。
- [配置参考目录](reference/config/INDEX.md)：配色、文本、图标、Configs、相邻加成。
- [工程参考目录](reference/project/INDEX.md)：.civ6proj 与动作顺序。
- [Lua 目录](reference/lua/INDEX.md)：规范、控件、事件/API 模式及历史案例。
- [Modifier 目录](reference/modifiers/INDEX.md)：通用语义、EffectType 分册、实现模式和案例。
- [美术与发布目录](reference/art/INDEX.md)：领袖/文明美术、音频、Blender、解包、Cooker、工坊。

## 渐进读取

`skill "任务" --plan` 返回必读文件（must 级）与可选参考；搜索返回命中章节和行号；`--file 路径 --section 章节名` 读取该章节及其子节。`--plan` 会给出字节数与 max_kb 告警；不要为小任务一次加载全部参数参考。

维护脚本与重复草稿在 `_archive/`（不索引）。新增文件要能从上述目录通过链接到达，检查命令为 `python -m modgen.cli skill --check`。
