# ModTools 5.4 路线图（2026-08 更新）

> 本文档用于同步"代码真实状态"和"下一步优先级"。
> 详细历史请看 `CHANGELOG.md`。功能改动时需同步更新两份文档。


### 2026-09 阶段 0/1（已完成）
- 完成架构基线记录：`docs/ARCHITECTURE_BASELINE.md`。
- `.CIV` schema 归一化已从 `civ_project.py` 提取到 `project/schema.py`，旧入口保持兼容。
- 输出 manifest 和路径安全规则已提取到 `project/output_manifest.py`，AI `get_manifest` 已使用共享值对象。
- AI 动作 contract 元数据已加入 `ai/contracts.py`，`help` 可返回参数说明。
- 日志 handler 重复配置时主动关闭，减少 Windows 文件句柄泄漏。

### 2026-09 阶段 2（已完成）
- 建立 `application` 服务层：`ProjectService` 负责 `.CIV` 持久化，`GenerationService` 负责 manifest/生成动作委托。
- WorkspacePage 的项目 I/O 已接入 ProjectService；GUI/AI 生成入口已改为公开适配方法。
- 当前仍由旧生成器执行实际内容构建，后续阶段再逐步迁移 SQL/XML 和资源生成逻辑。
### 2026-09 阶段 3（进行中）
- 已完成第一小步：SQL 字面量格式化提取到 `project/sql_utils.py`，WorkspacePage 的七处分类生成器统一委托。
- 已修复自定义输出文件的 CRLF 重复换行问题。
- 第二步已完成：政策卡完整 SQL 生成迁入 `project/sql_builders/policies.py`，直接接收条目列表；默认值由 `project/entity_defaults.py` 同时供编辑器和生成器使用。
- 政策卡迁移以 `47ed84d` 的九组输出为兼容基线，包含 SQLite 执行、无第三方依赖、GUI 接入验证；公共转义、去重、INSERT 块逻辑已收敛。
- 第三步已完成：信仰完整 SQL 生成迁入 `project/sql_builders/beliefs.py`，编辑器与生成器共享 `BELIEF_FIELD_DEFAULTS`，七组旧输出逐字兼容。
- 完整 CLI 预览、XML 和其他分类仍依赖 GUI 引擎；下一步继续选择依赖较少的分类，每个切片测试通过后单独提交。
- 已完成：**自定义 ModifierType 注册判定改为原版快照驱动**（修复「本机装过旧 Mod 就不补 `Types`/`DynamicModifiers` 行 → 换机加载失败」）：
  - 新增 `ModTools_5_4/data/vanilla_modifier_types.json`（989 条）+ 提取脚本 `modgen/tools/extract_vanilla_modifier_types.py`（从游戏自带 XML 提取，自动定位游戏目录）。
  - `.CIV` 新增字段 `modifiers[].modifier_type_source`（`null` 自动 / `"new"` 强制新建 / `"vanilla"` 强制已有），GUI 三态下拉 + 实时判定提示。
  - `modgen/modifier_validator.py` 新增两条 ERROR（强制新建却属原版 / 强制已有却不在快照）+ 一条 WARNING（自动判定为自定义）。
  - 判据收敛为单一来源 `_custom_modifier_type_map()`，SQL 与 XML 两条生成路径共用。

## 一、当前已完成（Done）

### 1) 工程与工作区框架
- `.CIV` 工程结构（schema 0.1.0）、序列化与加载流程已落地，按 `CIV_SECTION_ORDER` 17 节归一化（基础信息/美术/文本/修改器 4 节存 dict，其余存列表）。
- 主窗口 3 页（主页/工作区/设置）；新建/打开/保存/删除工程；多会话 tab；文件关联双击打开 `.CIV`。

### 2) 分类编辑能力（13 个内容分类全部接入）
- 文明、领袖、区域、建筑、单位、单位晋升、改良设施、总督、伟人、政策卡、项目、信仰、议程。
- 议程完整接入（主表 + HistoricalAgendas / ExclusiveAgendas / AgendaModifiers / AI 偏好）；单位晋升为画布式晋升树编辑器（2221/2212 模板 + 随机模式）。

### 3) 修改器工作区
- Modifier / RequirementSet / Requirement / UnitAbility 全链路编辑；EffectType/RequirementType 搜索与参数模板、中文注释模板；批量生成对话框；战斗预览文本（ModifierStrings）。

### 4) 美术与输出链路
- Icons.xml / ArtDef / XLP / Art.xml / Textures（PNG→DDS→TEX→XLP）/ Moments / 领袖独立 XLP；格式说明见 `docs/TEX_FORMAT.md`。
- 领袖颜色配置与城邦旗帜实时预览；工程根一键生成 + 覆盖冲突弹窗 + 删除计划（含路径穿越防护）。

### 5) 文本与知识查询
- 文本工作区统一承载 Text.sql / Text.xml 预览；描述框右键 `[ICON_XXX]` 插入。
- **LOC 文本解析单一实现**（`db/loc_text.py`）：嵌套 `{LOC_...}` 引用迭代展开 + 防环 + 深度上限；原四份分散实现（text_database / interface / ability_search / modgen）已全部收敛（含 modgen/dbquery，共五处）。
- **能力实现搜索**（知识查询核心）：**BM25 检索**（`db/search_index.py`：中文 bigram + 150+ 条领域词典 → 英文 Type 片段 + 字段权重 + 覆盖度 + 精确匹配晋级），语料 = 对象名称/描述 + ModifierStrings 中文 + Modifier/Requirement 的 Id·Type·参数；16 类对象（2026-08-17 新增**科技/市政**，效果经 TechnologyModifiers/CivicModifiers 反查）；详情 = 能力树（绑定来源分组、ATTACH/GRANT_ABILITY 嵌套展开、非默认标志、Strings）+ 数据表（主表/副表动态发现、相邻加成自动描述对照）；GUI（小工具窗口）与命令行（`modgen search`）**同一实现与排序**。
- 文本标记渲染：`[ICON_XXX]`（6 产出大小写不敏感）、`[NEWLINE]`、`[COLOR:XXX]`（官方 Civ6_ColorAtlas 116 预设 + 直接 RGB）。

### 6) 数据库导入能力（游戏库）
- 区域、建筑、单位、单位晋升、改良设施、伟人导入已开放；政策卡逻辑已实现（按钮未开放）。

### 7) AI 生成 .CIV（modgen）
- 纯标准库 CLI：generate（13 分类 + 修改器四类，Type 自动生成、EffectType 存在性校验、参数骨架）、validate（ERROR/WARNING）、merge（内容分类 + **修改器**，自动备份）、**search**（知识查询，`--object` 输出 Modifier 完整实现）。
- **new-project**：工程级 .CIV 骨架（基础信息/美术/修改器/文本 结构来自 GUI 默认导出提取的 project_scaffold.json），替代拷贝旧工程。
- **civ6proj**：从 .CIV 基础信息直接生成 ModBuddy 兼容 .civ6proj + 空白 Art.xml（`--update-civ` 回写路径），无需 ModBuddy 新建工程。
- **preview**：无头运行 GUI 生成引擎预览将导出的全部文件（SQL/XML/Icons/ArtDef/XLP/Text…，需 PyQt；`--section` 单分类输出）。
- **query**（游戏库只读查询，仅 SELECT/WITH/PRAGMA/EXPLAIN）、**loc**（LOC → 简体中文）。
- **skill**（2026-08-17）：本地技能库全文检索——仓库根 `skills/`（260+ 技能文件内迁自外部工作区，
  随发布包分发，入口 `skills/AGENTS.md`），文件名+内容词频评分 + `--file` 全文；与 search 分工：
  "怎么做/怎么写"→skill，"现成实现"→search。
- 方法论内置：错误提示引导 search、"先搜索再断言"写入 AGENTS.md/README/教程。
- 新设备无需外部知识库：知识查询 = `modgen search` / `skill` / `query` / `loc` / 能力实现搜索。

### 7b) AI 控制接口（外部 AI 驱动 GUI，2026-08）
- GUI 内置 localhost HTTP 控制服务（`ai/control_server.py`，`--ai-port [--ai-token]`，QTimer 桥接主线程）
  与 CLI 一次性执行（`--ai-exec [--headless]`）：18 动作（open_project/get_state/get_manifest/
  generate_all/civ6proj_create/quick_config/import_from_db/search/screenshot + **自定义文件通道**
  project_file_write/read/list/delete/add_file_action），协议见 `docs/AI_CONTROL_API.md`。
- 生成/一键配置/必填校验非交互化（GUI 交互行为不变）；内置 .civ6proj 生成器（`project/civ6proj_generator.py`
  + 基础信息页「新建 .civ6proj」按钮），生成物 ModBuddy 可打开/构建；.modinfo 下期再做（Build 时产物）。
- **自定义文件通道**（2026-08-17）：`project/custom_files.py`（GUI 一键配置与 modgen `custom-file`
  命令单一实现）——AI 可写自定义 SQL/XML/Lua（路径净化 + 动作自动分类注册 + 一键生成原样透传），
  硬规则修订为"主内容不写 Lua/不手写 SQL；自定义文件经工具通道写入"；get_state 返回文件动作与自定义文件清单。
- **生成 × 自定义 SQL 协调**（2026-08-17）：加载顺序显式化（自定义 UpdateDatabase=10000 > 生成数据 9999）；
  `modgen check-conflicts [--json]` + AI 动作 `check_conflicts`（主键双写=ERROR / UPDATE 生成表=WARNING /
  INSERT...SELECT 豁免）；preview 引擎新增 `build_preview_manifest`（readonly 判别）；skill 协调文档
  pipeline.md 改写为新通道。

### 8) 发布与工程规范化（2026-08）
- `build_release.ps1`：**源码 + exe 双轨**发行（zip 含 exe + 完整源码 + modgen + tools + 文档 + 数据文件）；PyInstaller onefile。
- `tools/setup_env.py` 一键初始化（venv/依赖/数据库配置/验证）；`tools/register_file_association.py` .CIV 文件关联。
- GitHub Actions `release.yml`：`v*` tag 自动构建发布（测试仅本地运行）。
- 测试 187+ 项（工程模型 / artdef / 文本导入 / 设置 / 各分类 SQL 预览 / 修改器模板 / 能力搜索 / 无头 GUI 冒烟）；`tests/sample_project.py` 共享 fixture。

### 9) 2026-08 数据安全与性能（全量审查后修复）
- 阶段 1（数据丢失/损坏）：空值输出 NULL（7 处 `_sql_literal` 统一）、SQL 分号截断、修改器条件落库、占位文案、AiLists 过期 LeaderType、Teaser 保留、旧式平铺基础信息迁移。
- 阶段 2（资源/输入/边界）：sqlite 连接统一（closing/finally）、LOC 查询缓存（mtime 失效）、artdef 文件级缓存；delete_requests 路径穿越校验、必填校验不写回、伟人 Type 净化、脏数据兜底；复制重算 type、晋升树跨树去重、批量 ModifierId 去重；`''` 全链路清零（真实工程验证）。
- 明确设计意图不改：改良设施相邻加成 Description 用 "Placeholder"。

## 二、当前缺口（TODO）

### P1：.modinfo 生成（ModBuddy 完全脱钩的最后一步）
- 复刻 `Civ6.targets` 里 GenerateModInfo 任务的输出（civ6proj 属性 + 文件清单 → .modinfo），
  文本/SQL 类 Mod 即可不经 ModBuddy 直接部署进游戏 Mods 目录；含美术资源的 Mod 仍依赖 Cooker。
- 入口：`civ6proj_generator.generate_modinfo()` + GUI 按钮 + modgen `civ6proj --modinfo` + AI 动作。

### P1：导入按钮补齐
- 政策卡导入逻辑已实现但按钮未开放（`group_workspace.py` 显隐名单）；文明、领袖、总督、项目、信仰、议程未实现导入。

### P2：响应式布局继续推广
- 已接入：主表编辑器、复合编辑器 `_pair_row`、单行子表编辑器（`ui/responsive.py`）；其余页面（修改器、基本信息、美术、伟人等）仍为固定布局。
- 目标：全工作区统一窄窗降列/堆叠。

### P2：三份「tag→中文」解析收敛
- `_resolve_loc_text`（group_workspace）/ `_active_text_db_path` / 各 `_load_civ*` 重复样板 → 统一入口 + 批查询 API。

### P3：阶段 3 去臃肿（2026-08 审查拆分蓝图，改动大、单独排期）
- workspace_page（10,498 行）：SQL 预览构建器群拆 `sql_builders/` 子包；`_sql_literal`/`_normalized`/`_render_plan_table` 提为工具函数。
- modifier_workspace（8,4xx 行）：拆 modifier_data/modifier_widgets/batch_generate_dialog/modifier_preview/modifier_id_templates；`HomePage` 改名 `ModifierEditorPage`。
- ui_widget_kit（7,121 行）：9 个搜索对话框抽基类；20+ 同构可输入选择器改数据驱动；TEMPLATE_SPECS 去重复键。
- entity_table_form（6,742 行）：三大复合编辑器抽「子表配置表 + 驱动助手」；group_workspace：if-链数据表驱动、`_CityNamesTable`/`_CitizenTable` 抽基类、needs_import 名单收敛。
- 死代码清理：`_BuildingSearchDialog`、`_query_agenda_reqset_options`、modifier snapshot×3、reqset 菜单机制、`export_main_table_row`/`build_main_table_insert_sql`、17 处死 import 等。

### P2：打包配置收敛
- `build_release.ps1` 与本地 `ModTools5.4.spec` 各维护一份数据清单 → 单一来源。

## 三、维护约定

- 每次功能合并后，同步更新：`CHANGELOG.md`（事实记录，最上方为最新）+ 本文档（当前状态与下一步）。
- 文档描述以"已在代码中存在的能力"为准，避免前瞻规划替代现状说明。
- 文件命名红线：Data/Text/Icons 可使用"文件名前缀_..."，但 XLP 与 ArtDef 文件名禁止加前缀。
- AI Agent 功能已移除（2026-06-30），如需恢复使用 `git checkout agent-dev`。
