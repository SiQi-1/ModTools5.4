> 受众：改 ModTools / modgen 的开发者 ｜ 何时读：改代码、加分类、迁移生成器前 ｜ 适用版本：ModTools 5.4 ｜ 更新：2026-10-29

# 架构与模块地图

本文件只面向**工具开发**（改 GUI / modgen / 生成引擎 / 测试）。制作 Mod、写 `.CIV`、回答游戏实现问题 → 从 [AGENTS.md](../../AGENTS.md) 进入。已定型的决策单独成 ADR（见 [decisions/](decisions/)），编码与文档纪律见 [conventions.md](conventions.md)，当前进度见 [roadmap.md](roadmap.md)。

## 项目概览

- ModTools 5.4 = 基于 PyQt6 的文明6 Mod 可视化编辑器（中文 UI）；编辑状态存 `.CIV`（JSON），生成 SQL/XML/Icons/ArtDef/XLP/Art.xml/Textures 到绑定的 `.civ6proj` 目录。
- 规模（2026-10-29 实测，`git ls-files 'ModTools_5_4/*.py'`）：**59,007 行 / 61 个非 `__init__` 模块**（含 `__init__` 共 71 文件 / 59,076 行）。四个大文件：`ui/pages/workspace_page.py` **10,282 行**、`ui/pages/modifier_workspace.py` 7,759、`ui/ui_widget_kit.py` 6,103、`ui/pages/entity_table_form.py` 5,945。
- Windows-only，Python 3.13（`.venv/` 不进 Git）。
- 应用内置的「AI Agent」功能已于 2026-06-30 移除（不要恢复 `agent/` 或聊天面板引用）。这与现役 **AI 控制接口**（`ai/control_server.py`：外部 AI 经 localhost HTTP 驱动 GUI 的一键按钮）不是同一功能，勿混删。

## 常用命令

```bash
python ModTools5.4.py                              # 启动 GUI
python -m unittest discover -s tests -v            # 主套件（不需要游戏库；GUI 测试跑 offscreen）
python tools/make_screenshots.py                   # 重新生成界面截图
python -S tools/share_source.py --check            # 源码分发检查
python ModTools5.4.py 工程.CIV --ai-port 8765 [--ai-token X]   # AI 控制服务
python ModTools5.4.py 工程.CIV --headless --ai-exec '<json动作>' # 一次性执行后退出
```

- 发行 source-only：skills + modgen + 共享核心 + 可选 GUI。`tools/share_source.py` 只复制已跟踪文件并写提交/散列来源，从不构建可执行文件或压缩包。
- 依赖只有 PyQt6 + Pillow（`requirements.txt`）；测试用标准库 `unittest`，无额外依赖。
- CI：`.github/workflows/source-check.yml` 检查 Git 产物卫生与知识门禁、导出源码目录并在其中冒烟，不发布二进制。
- git 跟踪 `local_text_New.sqlite`（运行数据）；可执行文件、压缩包、`shares/`、缓存与本机设置被忽略并受 CI 校验。

## 分层：Qt-free 核心 vs GUI 引擎

生成链路刻意分成两层，便于 CLI / AI / 测试复用而不拉起 Qt：

| 层 | 位置 | 职责 |
|---|---|---|
| Qt-free 核心 | `ModTools_5_4/project/`、`db/`、`artdef_parser.py`、`skills_search.py`、`application/services.py` | `.CIV` 模型与 schema、SQL 构建器、`.civ6proj` 生成器、扩展清单、UI 图标校验、资源检查、能力搜索 |
| GUI 引擎 | `ModTools_5_4/ui/pages/workspace_page.py` 等 | 分类编辑、预览与生成编排（大部分分类的 SQL/XML 构建仍在这里） |
| modgen 镜像 | `modgen/`（纯标准库） | `generate/validate/merge/preview/search/skill` 等命令；与 GUI 共用 `.civ6proj` 生成器与 vanilla 快照 |

- **输出模型**：生成由 workspace 状态驱动，输出树按 `CIV_SECTION_ORDER`（18 节）逐节贡献文件类型；空分类不产文件；`file_info.delete_requests` 在生成时执行。政策卡/信仰 SQL 已迁到 `project/sql_builders/`，其余分类仍在 `workspace_page.py`（如 `_build_civilization_sql_pair`）。
- 文件写入绑定的 `.civ6proj` 目录；`modgen preview` 无头复用 GUI 引擎（需 PyQt）。
- **自定义文件通道**：`project/custom_files.py` 是 GUI 一键配置与 modgen `custom-file` 的单一实现；主内容不写 Lua/不手写 SQL，扩展走该通道或项目级扩展。
- **AI 控制接口**：`ai/control_server.py` 的动作在 GUI 主线程执行（HTTP 线程经 QTimer 队列桥接），共 **22 个动作**；协议与动作表见 [reference/ai-control-api.md](../reference/ai-control-api.md)。
- **导入能力**：导入按钮只对 区域/建筑/单位/单位晋升/改良设施/伟人 显示；政策卡逻辑已实现但按钮未开放；AI 动作 `import_from_db` 是第二入口（覆盖区域/建筑/单位/改良设施/伟人/政策卡）。

## 模块地图（2026-10-29 核对）

```
ModTools5.4.py                  # 入口：raise SystemExit(launch())
ModTools_5_4/
├── ai/control_server.py        # AI 控制接口：动作注册表 + localhost HTTP 服务 + --ai-exec
├── app/                        # application.py（入口解析）、config、logging、settings、user_paths
├── application/services.py     # Qt-free ProjectService / GenerationService 接缝
├── project/                    # .CIV 模型、schema、sql_builders/、civ6proj_generator、
│                               # extensions、ui_icons、custom_files、asset_checks、landmarks ...
├── db/                         # 文本库、游戏库路径、LOC 解析（loc_text）、搜索索引
├── artdef_parser.py            # ArtDef XML 解析（From/{Base,DLC}/ 扫描 + lru_cache）
├── skills_search.py            # 本地技能库检索（GUI/AI 与 modgen skill 单一实现）
├── ui/
│   ├── main_window.py          # 3 页（主页/工作区/设置）；小工具是独立窗口
│   ├── theme/images/font_icons/image_ops/psd_summarizer/responsive
│   ├── ui_widget_kit.py        # 模板控件系统
│   ├── dialogs/                # 文本导入冲突解析等
│   └── pages/                  # workspace_page（树/预览/生成）、group_workspace、
│                               # basic_info、modifier、art、great_people、
│                               # entity_table_form、tools/search/settings/home
├── data/                       # 运行资源：颜色预设、effect/requirement 模板、
│                               # vanilla_modifier_types.json、font_icons_registry、字体图标 DDS
├── From/{Base,DLC}/            # 官方 ModBuddy artdef 参考文件
├── resources/                  # QSS、图标、内嵌 UI 图片
└── logs/                       # modtools_5_4.log（只写文件）
```

仓库根文档面：`AGENTS.md`（唯一 AI 路由）、`CLAUDE.md`（兼容 shim）、`README.md`（人读门面）、`docs/`（本目录）、`modgen/AGENTS.md`（命令契约）、`skills/`（分层技能库）。

## 测试

- 标准库 `unittest`（无 pytest）：`python -m unittest discover -s tests -v`；不需要游戏库或显示器（GUI 测试自行设 `QT_QPA_PLATFORM=offscreen`）。
- **数量口径**：只写「`python -m unittest discover -s tests` 当日实测」的数字并注明日期；历史记录里的 187 / 480 / 475 等数字是各自日期快照，不代表现状。2026-10-29 用 `.venv` 实测：`unittest` discover 计数 **561 项**（本机完整运行受环境差异影响：缺 PyQt6 的解释器会产生 27 个 import 错误、Windows 临时路径短名会导致 4 项断言失败；以 CI 或修复后的本机重跑为准）。
- `tests/sample_project.py` 是共享示例工程 fixture（每分类一条最小条目），`tools/make_screenshots.py` 也用它；改 preview builder 的字段时同步更新 fixture。

## 关键设计决策（摘要，正文见 ADR）

1. 自定义 ModifierType 是否补注册，只认随源码分发的**原版快照**，不认本机运行库 → [ADR-0001](decisions/ADR-0001-modifier-type-snapshot.md)
2. 文本预览**不用** `DebugLocalization.sqlite` → [ADR-0002](decisions/ADR-0002-no-debug-localization.md)
3. SQL 导出按实际有值字段生成列（稀疏列）→ [ADR-0003](decisions/ADR-0003-sparse-column-export.md)
4. 两个公开面：GitHub 仓库 vs 源码分享目录 → [ADR-0004](decisions/ADR-0004-github-vs-source-share.md)
5. 文本数据库是必配运行数据 → [ADR-0005](decisions/ADR-0005-text-db-required.md)
6. 「UI图标」是不进导航树的非实体分节 → [ADR-0006](decisions/ADR-0006-ui-icons-section.md)
7. 项目级扩展清单只有一个写入者 → [ADR-0007](decisions/ADR-0007-extension-manifest-writer.md)

其余约定（文件命名、日志、美术源目录、审批门、文档纪律）见 [conventions.md](conventions.md)。

## Changelog

`ModTools_5_4/CHANGELOG.md` 是权威历史（每次功能变更按日期记录，最新在顶部），只读顶部 5 条；当前 Done/TODO 与维护约定见 [roadmap.md](roadmap.md)。两者随功能变更同步更新。
