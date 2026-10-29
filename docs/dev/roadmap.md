> 受众：维护者与贡献者 ｜ 何时读：决定下一步做什么、或核对当前真实状态时 ｜ 适用版本：ModTools 5.4 ｜ 更新：2026-10-29

# 当前进度与下一步（路线图）

> **历史流水位置**：2026-09 ~ 2026-10 的逐日条目已原样迁到 [changelog-archive/roadmap-flow-2026-10.md](changelog-archive/roadmap-flow-2026-10.md)。权威变更日志是 [ModTools_5_4/CHANGELOG.md](../../ModTools_5_4/CHANGELOG.md)（只读顶部 5 条）。本页只保留当前 Done / TODO / 维护约定。

## 一、当前已完成（Done）

### 0) 2026-10-29 文档与仓库结构重构（P0-P5）
- 入口：根 `AGENTS.md` 四个门路由 + `CLAUDE.md` shim；常驻指令 55 KB → 2.8 KB；`modgen/AGENTS.md` 29.6 KB → 8 KB + `docs/` 8 篇。
- 文档：根文档归位 `docs/{user,dev,reference,meta}`，新增 7 条 ADR；README 23.2 KB → 3.3 KB；15 项过期事实修正。
- 知识库：`skills/` 分层为 `guides/reference/packages/_archive`，巨文件拆分，catalog 33 route 带 level/预算；「新增一个单位」必读 71 KB → 26.6 KB。
- 边界：11 GB 本机物集中到忽略的 `workspace/`；根本机文件清零；27 个含本机路径的 legacy 脚本移出 Git；`.gitignore` 重写。
- 文本库：`local_text_New.sqlite` 重新生成（84,467 → 32,268 行，仅官方 zh_Hans，Mod 词条 0）。
- 守卫：`tools/doc_lint.py` + `tests/test_repo_layout.py` + CI 两步 + `tools/install_skills.py`。

### 1) 工程与工作区框架
- `.CIV` 工程结构（schema 0.1.0）、序列化与加载流程；按 `CIV_SECTION_ORDER` **18 节**归一化（基础信息/美术/文本/修改器 4 节存 dict，「UI图标」等其余分节存列表；旧工程缺节点自动补空）。
- 主窗口 **3 页**（主页 / 工作区 / 设置）；**小工具是独立窗口**（窗口菜单或主页按钮打开，可与主窗口并排）；新建/打开/保存/删除工程、多会话 tab、双击 `.CIV` 打开。

### 2) 分类编辑能力（13 个内容分类全部接入）
- 文明、领袖、区域、建筑、单位、单位晋升、改良设施、总督、伟人、政策卡、项目、信仰、议程。
- 议程完整接入（主表 + HistoricalAgendas / ExclusiveAgendas / AgendaModifiers / AI 偏好）；单位晋升为画布式晋升树编辑器（2221/2212 模板 + 随机模式）。

### 3) 修改器工作区
- Modifier / RequirementSet / Requirement / UnitAbility 全链路编辑；EffectType/RequirementType 搜索与参数模板、中文注释模板；批量生成对话框；战斗预览文本（ModifierStrings）。

### 4) 美术与输出链路
- Icons.xml / ArtDef / XLP / Art.xml / Textures（PNG→DDS→TEX→XLP）/ Moments / 领袖独立 XLP；格式说明见 [reference/tex-format.md](../reference/tex-format.md)。
- **「UI图标」段**：`.CIV` 可声明与游戏实体无关的自定义 UI 图标（新闻分类/单位动作/追踪器等），只影响 `Icons.xml` 与 IMG/Textures；美术页专属编辑区，工作区树不单列节点（决策见 [ADR-0006](decisions/ADR-0006-ui-icons-section.md)）。
- 领袖颜色配置与城邦旗帜实时预览；工程根一键生成 + 覆盖冲突弹窗 + 删除计划（含路径穿越防护）。

### 5) 文本与知识查询
- 文本工作区统一承载 Text.sql / Text.xml 预览；描述框右键 `[ICON_XXX]` 插入。
- **LOC 文本解析单一实现**（`db/loc_text.py`）：嵌套 `{LOC_...}` 引用迭代展开 + 防环 + 深度上限；原分散实现已收敛。
- **能力实现搜索**：BM25 检索（中文 bigram + 领域词典），16 类对象（含科技/市政）；GUI 小工具与 `modgen search` 同一实现与排序。
- 文本标记渲染：`[ICON_XXX]`、`[NEWLINE]`、`[COLOR:XXX]`（官方 Civ6_ColorAtlas 116 预设 + 直接 RGB）。

### 6) 数据库导入能力（游戏库）
- 区域、建筑、单位、单位晋升、改良设施、伟人导入已开放；政策卡逻辑已实现（按钮未开放）。

### 7) AI 生成 .CIV（modgen，纯标准库）
- `generate`（13 分类 + 修改器四类）、`validate`（ERROR/WARNING）、`merge`（内容分类 + 修改器，自动备份）、`search`（`--object` 输出 Modifier 完整实现）。
- `new-project`（工程骨架，替代拷贝旧工程）、`civ6proj`（生成 ModBuddy 兼容工程 + 空白 Art.xml，`--update-civ` 回写）、`preview`（无头预览全部导出文件，需 PyQt）、`query` / `loc`、`skill`（本地技能库章节检索）。
- 方法论内置：错误提示引导 `search`、「先搜索再断言」写入 AGENTS.md / README / 教程。

### 7b) AI 控制接口（外部 AI 驱动 GUI）——**22 个动作**
- GUI 内置 localhost HTTP 控制服务（`ai/control_server.py`，`--ai-port [--ai-token]`，QTimer 桥接主线程）与 CLI 一次性执行（`--ai-exec [--headless]`）。
- 22 个动作：`ping` / `help` / `open_project` / `save_project` / `get_state` / `get_manifest` / `generate_all` / `generate_file` / `civ6proj_create` / `quick_config` / `import_from_db` / `extension` / `project_check` / `project_file_write` / `project_file_read` / `project_file_list` / `project_file_delete` / `add_file_action` / `search` / `skill` / `check_conflicts` / `screenshot`；协议见 [reference/ai-control-api.md](../reference/ai-control-api.md)。
- 注意：这是给**外部 AI 的驱动接口**，与 2026-06-30 移除的应用内置 agent 无关（两者名字相近，勿混删）。
- 生成/一键配置/必填校验非交互化（GUI 交互行为不变）；`.civ6proj` 生成统一走 `project/civ6proj_generator.py`（GUI 按钮 / modgen `civ6proj` / AI `civ6proj_create` 三处共用）；`.modinfo` 仍未生成（见 TODO P1）。
- **自定义文件通道**：`project/custom_files.py` 是 GUI 一键配置与 modgen `custom-file` 单一实现；生成 × 自定义 SQL 协调（加载顺序显式化 + `check_conflicts`）已落地。

### 8) 发布与工程规范化（2026-09 起 source-only）
- **只分发源码**：`tools/share_source.py --check` / `--out` 从已跟踪工作树导出并生成 `SOURCE_MANIFEST.json`；不再构建 exe/zip，仓库内**不存在** `build_release.ps1` 或 `release.yml`。
- 当前 CI 只有 `.github/workflows/source-check.yml`（产物卫生、知识门禁、源码导出冒烟），不构建/上传二进制。
- `tools/setup_env.py` 一键初始化（venv/依赖/数据库配置/验证）；`tools/register_file_association.py` 注册 `.CIV` 文件关联。

### 9) 2026-08 数据安全与性能（全量审查后修复）
- 阶段 1（数据丢失/损坏）：空值输出 NULL（`_sql_literal` 统一）、SQL 分号截断、修改器条件落库、占位文案、AiLists 过期 LeaderType、Teaser 保留、旧式平铺基础信息迁移。
- 阶段 2（资源/输入/边界）：sqlite 连接统一、LOC 查询缓存（mtime 失效）、artdef 文件级缓存、delete_requests 路径穿越校验、必填校验不写回、伟人 Type 净化、复制重算 type、晋升树跨树去重、批量 ModifierId 去重；`''` 全链路清零。

## 二、当前缺口（TODO）

### P1：.modinfo 生成（ModBuddy 完全脱钩的最后一步）
- 复刻 `Civ6.targets` 里 GenerateModInfo 任务的输出（civ6proj 属性 + 文件清单 → `.modinfo`），文本/SQL 类 Mod 即可不经 ModBuddy 直接部署进游戏 Mods 目录；含美术资源的 Mod 仍依赖 Cooker。
- 入口：`civ6proj_generator.generate_modinfo()` + GUI 按钮 + modgen `civ6proj --modinfo` + AI 动作。

### P1：导入按钮补齐
- 政策卡导入逻辑已实现但按钮未开放（`group_workspace.py` 显隐名单）；文明、领袖、总督、项目、信仰、议程未实现导入。

### P2：响应式布局继续推广
- 已接入：主表编辑器、复合编辑器 `_pair_row`、单行子表编辑器（`ui/responsive.py`）；其余页面（修改器、基本信息、美术、伟人等）仍为固定布局。目标：全工作区统一窄窗降列/堆叠。

### P2：三份「tag→中文」解析收敛
- `_resolve_loc_text`（group_workspace）/ `_active_text_db_path` / 各 `_load_civ*` 重复样板 → 统一入口 + 批查询 API。

### P3：阶段 3 去臃肿（2026-08 拆分蓝图，改动大、单独排期）
- `workspace_page.py`（**10,282 行**）：SQL 预览构建器群拆 `sql_builders/` 子包；`_sql_literal` / `_normalized` / `_render_plan_table` 提为工具函数。
- `modifier_workspace.py`（**7,759 行**）：拆 modifier_data/modifier_widgets/batch_generate_dialog/modifier_preview/modifier_id_templates；`HomePage` 改名 `ModifierEditorPage`。
- `ui_widget_kit.py`（**6,103 行**）：9 个搜索对话框抽基类；20+ 同构可输入选择器改数据驱动；TEMPLATE_SPECS 去重复键。
- `entity_table_form.py`（**5,945 行**）：三大复合编辑器抽「子表配置表 + 驱动助手」；`group_workspace`：if-链数据表驱动、`_CityNamesTable` / `_CitizenTable` 抽基类、needs_import 名单收敛。
- 死代码清理：`_BuildingSearchDialog`、`_query_agenda_reqset_options`、modifier snapshot×3、reqset 菜单机制、`export_main_table_row` / `build_main_table_insert_sql`、17 处死 import 等。

## 三、维护约定

- 每次功能合并后同步更新：`CHANGELOG.md`（事实记录，最上方为最新）+ 本文档（当前状态与下一步）；逐日流水不再往本页堆。
- 文档描述以「已在代码中存在的能力」为准，避免前瞻规划替代现状。
- **测试数量口径**：只写 `python -m unittest discover -s tests` 当日实测值并注明日期。2026-10-29 用 `.venv` 实测：`unittest` discover 计数 **561 项**；本机完整运行存在环境差异（缺 PyQt6 的解释器会产生 27 个 import 错误、Windows 临时路径短名会导致 4 项断言失败），以 CI 或修复后的本机重跑为准。历史数字（187+ / 480 / 475 等）是各自日期快照，不代表现状。
- 文件命名红线：Data/Text/Icons 可使用「文件名前缀_...」，XLP 与 ArtDef 文件名禁止加前缀。
- 应用内置 AI Agent 功能已移除（2026-06-30），如需恢复使用 `git checkout agent-dev`；**AI 控制接口**仍现役，两者不是同一功能。
