# ModTools 5.4 路线图（2026-08 更新）

> 本文档用于同步"代码真实状态"和"下一步优先级"。
> 详细历史请看 `CHANGELOG.md`。功能改动时需同步更新两份文档。

## 一、当前已完成（Done）

### 1) 工程与工作区框架
- `.CIV` 工程结构（schema 0.1.0）、序列化与加载流程已落地，按 `CIV_SECTION_ORDER` 17 节归一化。
- 主窗口已接入新建/打开/保存工程；工作区树支持分类节点与子条目组切换。

### 2) 分类编辑能力（13 个内容分类全部接入）
- 文明、领袖、区域、建筑、单位、单位晋升、改良设施、总督、伟人、政策卡、项目、信仰、议程。
- 议程已完整接入：复合编辑器（主表 + HistoricalAgendas / ExclusiveAgendas / AgendaModifiers / AI 偏好）→ SQL/XML 预览 → 生成输出，不再有占位。
- 单位晋升为独立画布式晋升树编辑器（卡片拖拽 + 端口连线 + 2221/2212 模板 + 随机模式）。
- 修复：晋升节点类型按 .CIV 包装式「基础信息」payload 解析前缀/中缀（`_shared_params_from_basic_section`），晋升类型正确生成 `PROMOTION_SIQI_P0053_*` 全名（2026-08-14）。

### 3) 修改器工作区
- Modifier / RequirementSet / Requirement / UnitAbility 全链路编辑。
- EffectType / RequirementType 搜索与参数模板、中文注释模板（effect/requirement_comment_templates.json）。
- 批量生成对话框（BatchGenerateDialog）、RequirementSet 配对参数、快捷键、战斗预览文本（ModifierStrings）。

### 4) 美术与输出链路
- Icons.xml / ArtDef / XLP / Art.xml / Textures（PNG→DDS→TEX→XLP）/ Moments / 领袖独立 XLP。
- 领袖颜色配置与城邦旗帜实时预览；图片圆形裁切 + 黑边。
- 工程根一键生成：Data/Text/Icons/美术文件 + 覆盖冲突弹窗 + 删除计划。

### 5) 文本与搜索
- 文本工作区统一承载 Text.sql / Text.xml 预览；描述框右键 `[ICON_XXX]` 插入。
- 小工具页（搜索子页）：文本搜索 ✓、ModifierType 搜索 ✓；图片工具（圆裁/黑白/区域图标/PSD模板总结）✓。

### 6) 数据库导入能力（游戏库）
- 区域、建筑、单位、单位晋升、改良设施、伟人、政策卡（逻辑已实现）。

### 7) 发布与工程规范化（2026-08）
- `build_release.ps1`：PyInstaller onefile（`--noconsole`）→ release/ + ModTools5.4.zip。
- GitHub Actions `release.yml`：`v*` tag 自动构建并发布 GitHub Release（测试仅本地运行，无 CI 测试流水线）。
- 测试 39 个用例（工程模型 / artdef 解析 / 文本库导入查询 / 设置读写 / 各分类 SQL 预览 / 无头 GUI 冒烟），`python -m unittest discover -s tests -v`。
- `tests/sample_project.py` 共享示例工程（测试与截图脚本共用）。
- MIT LICENSE、requirements.txt（PyQt6 + Pillow）、.gitattributes、README 截图自动生成脚本（tools/make_screenshots.py，13 张）。

### 8) 2026-08-16 全量代码审查 + 阶段 1 数据安全修复
- 7 路并行审查（工作区全部页面/核心层/生成链路）+ 手工验证，产出 bug 清单与拆分蓝图（见 CHANGELOG 2026-08-16 条目）。
- 阶段 1 已修（数据丢失/损坏类，127 项测试全过）：
  - 空值输出 NULL 而非 `''`（7 处 `_sql_literal` 统一，修复 fixture 自带 `PrereqTech: ""` 病态样本）；
  - SQL 文本内分号不再截断（Text.sql 静默丢失）；
  - 修改器条件编辑即时落库；可输入选择框占位文案不再进 .CIV；
  - 议程 AiLists LeaderType 过期残留；.civ6proj Teaser 保留原始值；
  - 旧式平铺基础信息 prefix/infix 迁移 + 加载中禁止回写。
- 明确设计意图不改：改良设施相邻加成 Description 用 "Placeholder"（游戏无改良相邻加成文本）。

### 9) 2026-08-16 新增：删除工程（关闭页面）
- 文件菜单「删除工程」：关闭当前会话 tab，不删除磁盘文件；`WorkspacePage.remove_active_session()` 处理确认/切换/归零；132 项测试全过。

### 10) 2026-08-16 小工具独立为窗口
- 主窗口 3 页（主页/工作区/设置）；小工具 = 独立 `ToolsWindow`（窗口菜单/主页按钮打开，关闭=隐藏保留状态，与主窗口并排使用）。
- 图片工具与 PSD 模板总结已移除（2026-08-16，待重新设计）；底层 image_ops/psd_summarizer 保留。

### 11) 2026-08-16 新增：信仰官方固定图标（非万神殿）
- 依据 `Icons_Beliefs.xml` + `Beliefs.xml` 实测：所有信仰图标位于官方图集 `ICON_ATLAS_BELIEFS_PATHEON`，非万神殿按类别共用一个 Index（WORSHIP=22 / FOLLOWER=23 / FOUNDER=24 / ENHANCER=25）。
- 信仰编辑器新增「使用官方固定图标」复选框（万神殿自动禁用并取消勾选；已导入自定义图片时以自定义图片为准；老工程默认不勾选）。
- Icons.xml 对启用官方图标的信仰直接输出官方图集引用行（政策卡同款），不再生成自定义图集与 IMG/DDS；美术页别名表同步隐藏该类条目；新建信仰默认启用。
- 新增 `tests/test_belief_official_icon.py`（8 例）；全量 169 项测试通过。

### 12) 2026-08-16 修复：统一 Text.sql 文本重复输出
- 根因：`ordered_rows` 去重结果未用于实际输出（只算 total_rows）；分组按 `entity_type in tag` 子串匹配，type 前缀重叠或同 type 条目时同一行进入多个组。
- 修复：Text 组装阶段跨组按行去重（行只归首个匹配组、total_rows 与输出行数一致）；`_build_belief_sql_pair` 按信仰 type 去重条目（消除 Beliefs 表同主键隐患）。
- 新增 3 例回归测试；全量 175 项测试通过。

### 13) 2026-08-16 修复：全分区 SQL 生成器按 type 去重重复条目
- 12 个分区生成器统一在条目循环按 type 去重（同 type 只取第一条），消除主表同主键两行与文本重复；伟人两层去重（class + individual/greatwork）。
- 新增 `tests/test_duplicate_type_entries.py`（12 例）；全量 187 项测试通过。

## 二、当前缺口（TODO）

### P2：响应式布局继续推广
- 现状：主表编辑器（顶部表单/数字区/布尔区）、复合编辑器 `_pair_row`、单行子表编辑器已接入 ResponsiveGrid/ResponsiveSplit（`ui/responsive.py`）；其余页面（修改器、基本信息、美术、伟人等）仍为固定双列/网格布局。
- 目标：全工作区统一窄窗降列/堆叠；`_pair_row` 断点阈值按实际面板宽度统一。

### P1：全局搜索接入真实逻辑（✅ 2026-08-16 完成：能力实现搜索）
- ✅ 小工具页「搜索」子页的"全局搜索"占位已替换为**能力实现搜索**（参考旧版 ModTools4.5 理念重构）：
  - 三通道：对象文本（中文名/描述）、能力层反查（Modifier/参数/条件 LIKE → 绑定对象）、中文效果词映射（"宣战"→WAR）；
  - 详情 = 数据表（主表+副表动态发现，相邻加成专门渲染：自动描述+原文对照）+ 能力树（绑定来源分组、ATTACH/GRANT_ABILITY 嵌套展开、条件集/条件/参数）；
  - 浏览历史导航（后退/前进）、树内过滤、右键复制；14 类对象全覆盖。
- 后续可扩展：结果定位到工作区对应条目；能力树节点跳转到修改器编辑器。

### P2：图片工具扩展
- 现状：小工具页已有 圆形裁切/黑白图标/区域图标(人工确认+底图复制)/PSD模板总结；区域图标六边形检查为人工确认。
- 目标：区域图标自动几何检测；模板总结的 recipe 接入合成器（自动拼合+多尺寸导出）；打包 exe 时决定是否内置 psd-tools。

### P1：导入按钮开放与补齐
- 现状：分组面板"导入"按钮仅对 区域/建筑/单位/单位晋升/改良设施/伟人 显示；政策卡导入逻辑已实现但按钮未开放（`group_workspace.py` 显隐名单需加入政策卡）。
- 未实现导入：文明、领袖、总督、项目、信仰、议程。

### P2：测试与回归扩展
- 现状：已有 39 个用例，覆盖工程模型、artdef、文本导入、设置、全部 13 分类 SQL/XML 预览与无头 GUI 冒烟。
- 目标：生成链路测试（`_generate_all_output_files` 写出文件树）、图片导出（PNG/DDS/TEX）、GUI 交互测试（QTest）可按需补充。

### P2：阶段 2 数据安全与性能（2026-08 审查发现，已部分完成）
- ✅ sqlite 连接统一：art_workspace/workspace_page 5 处 `with connect` 泄漏 → `contextlib.closing`；group_workspace 4 处异常路径不 close → try/finally。
- ✅ LOC 查询缓存：db/interface 按文件 mtime 自动失效（settings + tag 结果），不再每次重读磁盘。
- ✅ artdef 缓存：文件级 mtime 解析缓存 + `invalidate_cache()` 接入美术页刷新。
- ✅ 输入安全：delete_requests 路径穿越校验、必填校验不再改写工程数据、伟人 Type 净化（CJK 移除）、AiFavoredItems/colors/leader_type 脏数据兜底。
- ✅ 复制政策卡/信仰重算 type；晋升树跨树 abbr 全局去重；美术渲染不写状态；批量生成 ModifierId 去重 + 只写已填参数。
- ⏳ 未做：三份「tag→中文」解析收敛为单一入口 + 批查询 API（`_resolve_loc_text`/`_active_text_db_path`/`_load_civ*` 重复样板）；`import_dlc_texts` 等死代码清理（归入阶段 3）。

### P3：阶段 3 去臃肿（2026-08 审查拆分蓝图，改动大、单独排期）
- workspace_page（10,498 行）：SQL 预览构建器群拆 `sql_builders/` 子包；公共 `_sql_literal`/`_normalized`/`_render_plan_table` 提为工具函数。
- modifier_workspace（8,4xx 行）：拆 modifier_data/modifier_widgets/batch_generate_dialog/modifier_preview/modifier_id_templates；`HomePage` 改名 `ModifierEditorPage`。
- ui_widget_kit（7,121 行）：9 个搜索对话框抽 `_SearchDialogBase`；20+ 同构可输入选择器改数据驱动注册表；TEMPLATE_SPECS 去重复键。
- entity_table_form（6,742 行）：三大复合编辑器抽「子表配置表 + 驱动助手」；group_workspace：SectionItemWorkspacePanel if-链数据表驱动、`_CityNamesTable`/`_CitizenTable` 抽基类、needs_import 名单收敛。
- 死代码清理：`_BuildingSearchDialog`、`_query_agenda_reqset_options`、modifier snapshot×3、reqset 菜单机制、`export_main_table_row`/`build_main_table_insert_sql`、17 处死 import 等。

### P2：打包配置收敛
- 现状：`build_release.ps1` 与本地 `ModTools5.4.spec` 各维护一份数据清单，易漂移。
- 目标：改为单一来源（spec 由脚本生成或删除 spec 路径）。

## 三、建议迭代顺序

### 迭代 A（建议先做）
- 全局搜索：关键词检索 + 结果定位，复用各分类已有名称/预览逻辑。

### 迭代 B
- 开放政策卡导入按钮；补齐 文明/领袖/总督/项目/信仰/议程 的数据库导入。

### 迭代 C
- 最小测试集与回归脚本（启动冒烟、工程读写、核心预览生成）。

### 迭代 D
- 打包配置收敛、版本号统一维护、大文件拆分（workspace_page 9.4k 行）。

## 四、维护约定

- 每次功能合并后，同步更新：
  - `CHANGELOG.md`（事实记录，最上方为最新）
  - 本文档（当前状态与下一步）
- 文档描述以"已在代码中存在的能力"为准，避免前瞻规划替代现状说明。
- 文件命名红线：Data/Text/Icons 可使用"文件名前缀_..."，但 XLP 与 ArtDef 文件名禁止加前缀。
- AI Agent 功能已移除（2026-06-30），如需恢复使用 `git checkout agent-dev`。
