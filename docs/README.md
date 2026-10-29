> 受众：所有读者（人 / AI） ｜ 何时读：需要找文档、或新增/改动文档前 ｜ 适用版本：ModTools 5.4 ｜ 更新：2026-10-29

# 文档索引

仓库根目录只保留入口文件（`AGENTS.md` 唯一 AI 路由、`CLAUDE.md` 兼容 shim、`README.md` 门面）；其余文档全部在 `docs/`。AI 任务路由从 [AGENTS.md](../AGENTS.md) 开始，本页负责人找文档。

## 元信息规范

每篇文档**首行**必须是：

> 受众：… ｜ 何时读：… ｜ 适用版本：ModTools 5.4 ｜ 更新：YYYY-MM-DD

历史/归档类文档再加 `状态：历史记录`。改内容时同步更新日期。预算：普通文档 ≤32 KB，`SKILL.md` ≤500 行，`--plan` 必读总量 ≤30 KB，超限就拆。**一个事实只写一处**，其他位置只放链接；改命令/行为 = 改契约，需同步 `modgen/AGENTS.md`、`skills/catalog.json` 与测试。

## 目录

| 目录 | 放什么 | 入口 |
|---|---|---|
| `docs/user/` | 使用向：安装、快速上手、GUI、完整教程、AI 提示词、FAQ | [quickstart.md](user/quickstart.md) |
| `docs/dev/` | 开发向：架构、路线图、约定、ADR、历史流水 | [architecture.md](dev/architecture.md) |
| `docs/reference/` | 参考契约：AI 控制接口动作表、纹理格式 | [ai-control-api.md](reference/ai-control-api.md) |
| `docs/meta/` | 分享、来源与社区整合记录 | [source-sharing.md](meta/source-sharing.md) |

### docs/user/

| 文档 | 内容 |
|---|---|
| [install.md](user/install.md) | 新设备一键初始化、手动配置、验证、排障、外部建模工具链 |
| [quickstart.md](user/quickstart.md) | 设置数据库 → 新建工程 → 生成文件的 5 步；工程概念 |
| [gui-guide.md](user/gui-guide.md) | 主窗口 3 页、小工具独立窗口、13 分类与各工作区说明 |
| [tutorial.md](user/tutorial.md) | 从零全流程：GUI 路径、纯 AI 路径、部署进游戏 |
| [ai-prompt.md](user/ai-prompt.md) | 可直接交给 AI 的开局提示词、可用范围与边界 |
| [faq.md](user/faq.md) | 常见问题与系统要求（不含已停止发布的 EXE/打包版） |

### docs/dev/

| 文档 | 内容 |
|---|---|
| [architecture.md](dev/architecture.md) | 模块地图、生成引擎、测试、约定 |
| [roadmap.md](dev/roadmap.md) | 当前 Done / TODO / 维护约定（不含逐日流水） |
| [conventions.md](dev/conventions.md) | 文件命名、日志、美术源目录、文档与变更纪律 |
| [decisions/](dev/decisions/) | ADR-0001 ~ ADR-0007：已定型的设计决策 |
| [changelog-archive/](dev/changelog-archive/) | 路线图历史流水（2026-09 ~ 2026-10） |

### docs/reference/ 与 docs/meta/

| 文档 | 内容 |
|---|---|
| [ai-control-api.md](reference/ai-control-api.md) | localhost HTTP / `--ai-exec` 动作表（22 动作）与协议 |
| [tex-format.md](reference/tex-format.md) | `.tex` / `.dds` 纹理格式与覆盖行为 |
| [source-sharing.md](meta/source-sharing.md) | 源码分享范围、导出方式与校验命令 |
| [community-integration.md](meta/community-integration.md) | 社区技能与工具整合记录（**状态：历史记录**） |

## 历史

- 路线图逐日流水（2026-09 ~ 2026-10）：[dev/changelog-archive/roadmap-flow-2026-10.md](dev/changelog-archive/roadmap-flow-2026-10.md)
- 完整变更日志（权威）：[ModTools_5_4/CHANGELOG.md](../ModTools_5_4/CHANGELOG.md)，只读顶部 5 条，不要通读 260 KB。

## 维护约定

- 不新增根目录文档；新文档进 `docs/` 或 `skills/` 对应目录。  
- 数字与路径必须可复核；引用代码规模/动作数/测试数时写明口径与日期。  
- 移动被跟踪文件用 `git mv` 保历史；只读命令用 `git status` / `git ls-files` / `grep`。
