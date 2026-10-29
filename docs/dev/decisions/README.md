> 受众：贡献者 ｜ 何时读：想知道某条设计为什么这样做、或准备推翻它时 ｜ 适用版本：ModTools 5.4 ｜ 更新：2026-10-29

# 架构决策记录（ADR）

已定型的设计决策单独成文，架构文档只留一句摘要 + 链接。**改决策要新增 ADR**，不要往架构文档里堆；旧 ADR 不重写，用新 ADR 取代并注明。

| ADR | 决策 | 状态 |
|---|---|---|
| [ADR-0001](ADR-0001-modifier-type-snapshot.md) | 自定义 ModifierType 注册由原版快照驱动 | 已采纳 |
| [ADR-0002](ADR-0002-no-debug-localization.md) | 文本预览不使用 `DebugLocalization.sqlite` | 已采纳 |
| [ADR-0003](ADR-0003-sparse-column-export.md) | SQL 按实际有值字段生成列（稀疏列） | 已采纳 |
| [ADR-0004](ADR-0004-github-vs-source-share.md) | 两个公开面：GitHub 仓库 vs 源码分享目录 | 已采纳 |
| [ADR-0005](ADR-0005-text-db-required.md) | 文本数据库是必配运行数据 | 已采纳 |
| [ADR-0006](ADR-0006-ui-icons-section.md) | 「UI图标」是非实体分节、不进导航树 | 已采纳 |
| [ADR-0007](ADR-0007-extension-manifest-writer.md) | 项目级扩展清单只有一个写入者 | 已采纳 |

命名：`ADR-NNNN-kebab-title.md`，正文 ≤15 行，固定三段「背景 / 决定 / 后果」。
