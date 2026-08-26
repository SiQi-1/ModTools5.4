# ModTools 5.4 路线图（2026-08 更新）

> 本文档用于同步"代码真实状态"和"下一步优先级"。
> 详细历史请看 `CHANGELOG.md`。功能改动时需同步更新两份文档。

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
- **能力实现搜索**（知识查询核心）：三通道（对象文本/能力层反查/中文效果词映射），14 类对象；详情 = 能力树（绑定来源分组、ATTACH/GRANT_ABILITY 嵌套展开、非默认标志、Strings）+ 数据表（主表/副表动态发现、相邻加成自动描述对照）；GUI（小工具窗口）与命令行（`modgen search`）双入口。
- 文本标记渲染：`[ICON_XXX]`（6 产出大小写不敏感）、`[NEWLINE]`、`[COLOR:XXX]`（官方 Civ6_ColorAtlas 116 预设 + 直接 RGB）。

### 6) 数据库导入能力（游戏库）
- 区域、建筑、单位、单位晋升、改良设施、伟人导入已开放；政策卡逻辑已实现（按钮未开放）。

### 7) AI 生成 .CIV（modgen）
- 纯标准库 CLI：generate（13 分类 + 修改器四类，Type 自动生成、EffectType 存在性校验、参数骨架）、validate（ERROR/WARNING）、merge、**search**（知识查询，`--object` 输出 Modifier 完整实现）。
- 方法论内置：错误提示引导 search、"先搜索再断言"写入 AGENTS.md/README/教程。
- 新设备无需外部知识库：知识查询 = `modgen search` / 能力实现搜索。

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
