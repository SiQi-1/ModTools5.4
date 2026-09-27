# ModTools 5.4 路线图（2026-08 更新）

### 2026-09-28 文明文化美术检查（知识已回流）
- 新增文明的城市/建筑文化及单位文化配置进入通用规则、工作流与文明模板；新增 Cultures.artdef 字段和引用链指南，并接入检索。
- 要求核对实际文明成员与 Art.xml 加载关系，不能把空文件、ethnicity 或音乐来源当作文化配置完成；未新增工具自动覆盖审计。

### 2026-09-28 选人皮肤背景策略（知识已回流）
- 场景型皮肤背景＋空白前景进入领袖美术指南，按两槽尺寸分别排版并检查透明度；更新美术入口与索引。
- 用户提供的控件留白经验与导出器字段分开记录，PNG 构图和游戏可视范围分别验收。

### 2026-09-28 二进制与范围挂载（已实现）
- 二进制按效果/正负号限制档位，校验提示可识别家族的过大上限；常规城市/区域最高位 1024，不默认铺 16/31 位。
- 逐对象挂载作为线性计数的优先方案，覆盖区域、城市、单位、建筑、改良；身份边界、动态 flags 和生命周期验证进入技能。

### 2026-09-28 UI 脚本替换与固定相邻预览（已实现，原生显示待验收）
- ui_replace 扩展生成 ReplaceUIScript 的 LuaContext / LuaReplace 属性，CLI、AI、GUI 导出和引用检查接通，无需额外 XML。
- Self 固定产出语义、放置预览与 CityPanel 产出来源拆分方法已回流；模拟检查不替代实机显示。

### 2026-09-28 原生相邻与文本制作检查（已实现）
- 官方相邻快照、adjacency 查询/继承审计、text-icons 候选/工程检查进入 modgen；统一检查同时提示漏继承和缺失图标。
- 相邻技能纠正原生改良桥接表，路由优先命中原生规则；用户设计稿无需自行填写字体图标。
- 社区 PSD 经用户确认可 Git 管理与分享，已内置 27 份及使用说明/来源清单；先前本地保留的限制对此套模板解除，单 Mod 立绘/成品仍留在工作目录。

### 2026-09-28 区域 Alpha 组修正（已实现）
- 白色核心置入 PSD Alpha 组，读取原始渐变、内部渐变描边和外发光；底板内发光也进入 PNG 处理。另存可编辑 PSD，原模板不改。
- 旧的平涂配方被拒绝；不支持的样式不静默省略。PNG 的发光核、渐变插值/抖动与原生 Photoshop 差异写入报告，原生像素对照及游戏显示仍需另验收。

### 2026-09-28 头像、图标与历史时刻模板工具（已实现，视觉与游戏验收独立）
- 新增 Qt-free project/art_images.py 与 modgen image：PSD 层级检查/选择提取、JSON 配方合成、白标/灰度与透明度检查、多尺寸预览和散列记录。
- 研究用户历史时刻、头像与区域 PSD；方法进入 civ6-art-images 技能。模板/原作素材留在用户本地，不作为通用开源资产分发。
- 明确工具不自动定位脸部或理解核心轮廓；没有视觉能力的 AI 只能复用已验收坐标或输出待复核候选。PSD 特效、游戏显示需另验收。

### 2026-09-26 skills + tools 源码分享（已完成）
- 分享入口统一为当前源码目录，保留可选 GUI；停止维护 EXE/预制 ZIP 和 PyInstaller 发布流程。
- 新增 Git 产物检查、源码目录导出、版本/散列清单和 CI 冒烟；本地历史产物与个人设置不进入新分享内容。

### 2026-09-26 工程元数据多语言（已完成）
- 名称和说明的 LocalizedTextData 保留 en_US 等额外语言；中文编辑仍正常更新，重复生成不新增重复语言节点。

### 2026-09-26 产出二进制选型（知识已回流）
- 动态目标值用 Property，少量永久增量可直接 Attach；迁移、防重、位容量与原生验证边界已纳入 Lua 指南及检索回归。

### 2026-09-26 UI 输入与列表验收（知识已回流）
- 滚轮/滑动条分别验收、交叉排序样例和统一状态栏空间已同步到仓库与已安装 UI skill。
- 明确 HTML 与模拟检查不能替代原生输入验收。

### 2026-09-25 UI 文本角色与尺寸警告（知识已回流）
- 标题/奖励名与描述分别处理字体图标；仓库及已安装 HTML UI skill 同步相同规则，保留各自其他内容。
- 原生 parent 尺寸归属、筛选缺项告警和 Lua 环境验证边界进入 UI 参考，不以模拟通过代替实机验收。


### 2026-09-25 地标玩法阶段筛选（已完成）
- building_sets 显式限定可达阶段，与 base_variants 交叉校验；旧配方保持兼容。
- 技能先核对前置/互斥/实际授予，再设计共用槽位，取消假设异常授予的全组合推荐。

### 2026-09-25 奇观完成态地标适配经验（文档完成）
- 已记录一个可静态显示的官方奇观案例及 GEO 类、FGX 散列、状态与编译检查；仅作为有限手工资源包装流程。
- 通用奇观/动画转换、游戏贴地和原生渲染仍不在该案例的验证范围。

### 2026-09-25 区域基底差分与 SDK 副本解析（已完成）
- base_variants 按完整建筑组合切换基底，默认回退及输入检查已接入 compose；建筑玩法不变。
- 同名 GEO/MTL/TEX 比较源和直接载荷后消歧，同名 AST 仍显式选源；原创回归覆盖差异载荷与缺文件。
- 模型 A/B/C 差分、占地和地面高度核对进入地标技能；游戏实际贴地仍需实测。

### 2026-09-25 美术解包参考与 SDK 类检查（已完成）
- 千川白浪 Civ6ArtUnpack 移交包的复原方法和证据边界已进入知识检索，保留来源与冲突记录。
- assets check 支持可选官方配置，区分 XLP/AST/GEO/TEX 类及其允许关系，AST 引用校验接通。
- 原 blpkit、领袖批量解包、Oodle/Granny 工具和全量重建未内置；外部依赖及游戏验收明确保留。

### 2026-09-25 自建静态地标资源纳管（已完成）
- 已转换的 AST/GEO/FGX/MTL/TEX/DDS 可通过 local_pantry/local_files 进入受管资源包、CIV 导出和隔离 Cooker，支持散列与依赖检查、二进制原样输出。
- 外部模型转换和实际游戏显示分别验证；不包含单位动画管线。自建模型可按用户需求使用一套状态外观。


### 2026-09-25 HTML UI 独立分享包（已完成）
- 入口与元数据移除 .CIV 前置要求，新增 SDK 独立接入；现有 ModTools 工作流保留为可选。
- 独立 ZIP 携带说明、示例、脚本、许可证与散列清单；Node/浏览器/Python 按操作提供，不与 ModTools 版本绑定。

### 2026-09-25 静态地标 AST 组合（工具完成，游戏显示待验收）
- 已修正美术源码误注册：源目录留在磁盘供 Cooker 读取，civ6proj 不注册这些 Content/Folder/None；既有工程导出时清理旧注册，verify 检测回归。
- CLI 支持资源检索、配方组合、CIV 导入、引用链校验和隔离 Cooker；GUI 往返/预览/生成保留资源包，SDK 不随包复制。
- 区域建筑集合、补充建筑美术、实体 Xref 与来源资料片依赖接入完整导出；支持单时代、多建设状态。
- 地标技能、示例、检索和回归已接入。当前不提供 GUI 配方编辑器、任意 AE AST 反向导入或单位动画组合；AE/游戏内地形与差分触发单独验收。


### 2026-09-25 社区技能与资源工具整合（已完成）
- 五篇知识指南及六条主题路由、来源声明与许可证随源码发布；Lua 事件环境规则按本项目及用户确认统一。
- 领袖外交差分字段、GUI、共享校验和 PNG/DDS/TEX/XLP/ArtDef 导出已接通，旧默认产物兼容。
- assets/audio/art/workshop 四类只读 CLI 已落地，明确报告外部依赖和运行时未验证项；契约、schema、提取器及回归同步。
- 验证：主套件 480 项无失败（5 跳过），modgen 99 通过；知识检查 235 篇 / 31 场景零问题，发行署名已核验。
- 外部 Wwise/Blender/SDK Cooker/Steam 程序继续使用原工具；本轮未自动化模型导入或发布，实机触发、发声和显示独立验收。完整记录见 [社区整合](../../docs/COMMUNITY_SKILL_INTEGRATION.md)。

### 2026-09-25 HTML UI 限宽与布局经验（已完成）
- 将用户确认无偏移的布局策略及适用边界回流技能，补充受限宽度、留白和完整视口预览方法；仓库与安装副本同步。

### 2026-09-24 UnitAbility 可选显示文本（已完成）
- 内部能力允许 Name/Description 为 NULL，CLI 生成和校验与已有导出器一致；普通实体名称要求保持。

### 2026-09-24 可分享 HTML UI 工具链（已完成）
- 仓库内 civ6-html-ui 技能包接入检索/任务路由和发布目录，可跨 agent 阅读，也可整包独立复制。
- 新增纹理渲染、清单批量导入、资源链像素校验 CLI，共用随包实现；不依赖个人安装，不自动安装浏览器或部署 Mod。
- Node/Chromium 路径可配置；Windows 已运行真实浏览器与分离目录验证，其他系统和游戏内显示仍按各自环境验收。


### 2026-09-24 HTML 转原生 UI 技能修正（已完成）
- 固定按钮与字体示例按实机反馈修正；新增独立只读尺寸/字体检查及回归。
- 九宫格参数和引擎字体排版仍需原生验收；不修改工具生成器。


- 2026-09-23：议程仅通过 HistoricalAgendas 绑定领袖；修复通用 Trait 误挂载，旧绑定兼容转出并同步规范和回归。

> 本文档用于同步"代码真实状态"和"下一步优先级"。
> 详细历史请看 `CHANGELOG.md`。功能改动时需同步更新两份文档。

### 2026-09-24 本地 Mod 工程隔离（已完成）
- `.CIV` 与 `*.extensions/` 成对忽略；专用脚本、测试、素材、报告和构建包按工作流留在本地工作目录。
- 已跟踪的单 Mod 占位素材仅移出索引，保留本地；通用代码、schema 和回归测试保持可纳入 Git。
- 工作流明确工具仓库与独立 Mod 仓库的边界，交付时检查忽略命中和已跟踪状态。

### 2026-09-23 单位导出稳定性（已完成）
- 空搜索引用保存 null；自定义单位标签使用官方静态快照判定，导出结果不受已加载本 Mod 的运行缓存影响。

### 2026-09-23 工程元数据回写（已完成）
- 导入 .civ6proj 的依赖、项目 GUID、Mod 版本与兼容版本随 .CIV 保存，缺少旧工程文件也可恢复；额外本地化简介标签保留。

### 2026-09-23 项目级扩展（已完成）
- `.CIV.extensions` + 工程旁源码目录，Core/GP/UI 配套初始化、旧文件纳管、依赖与独立动作、另存/重建兼容。
- CLI extension/project-check/build 与 AI extension/project_check 共用核心；GUI 预览和生成接入受管源码，阻断缺失与冲突。
- SQL 检查支持已知复合主键、多行、XML Row 和作用域，无法静态确认的语句明确提示。规则、工作流和任务检索同步。
- 验证：主套件 431 项无失败（2 项符号链接权限跳过），modgen 96 通过；知识检查 225 篇 / 20 场景零问题，扩展/AI/SQL 专项回归通过。
- 范围：SQL/XML/Lua 源码；既有美术源路径仍由美术功能管理。完整预览/生成仍依赖 Qt；ModBuddy/Cooker/游戏验收仍为独立步骤。Lua 语法编译与动态引用检查未实现。

### 2026-09-23 AI 知识框架（已完成）
- 规则正文、统一工作流、任务必读映射、当前功能指南与完整分类入口已接入。
- CLI / AI 共享章节检索与结构化阅读清单；旧全文读取调用兼容。
- skill --check 检查知识结构与真实查询排名，并接入发布前检查；历史脚本/重复草稿隔离，不参与检索。
- 验证：知识检查 224 篇 / 15 个检索场景零问题；主测试 399 通过、2 跳过；modgen 96 通过。
- 此阶段改善知识发现和工具契约；SQL/XML 生成器脱离 GUI 仍按下方阶段 3 继续。

### 2026-09-23 文本统一与纹理覆盖
- 已完成：`文本.custom_entries` 的 .CIV 声明、统一 SQL/XML 预览/导出、保存兼容与冲突拦截；当前无专用文本表格编辑器。
- 已完成：虚拟 DDS/TEX 纹理计划进入覆盖选择，重复生成 all 更新纹理、none 保留。新增源尺寸变化回归。
- 20.0 现有 38 张 HTML 纹理通过官方 SDK 编译；报童改为 4 个原生单位按钮，自绘图标。玩法自定义 SQL 只保留 Core；300 个 LOC 纳入标准文本输出。

### 2026-09-23 独立 UI 纹理
- 已完成：美术页批量 PNG 导入、原尺寸 alpha 输出、DDS/TEX/XLP 登记；`modgen texture add/list/remove`；GUI / CLI 共用校验。旧工程兼容。
- 20.0 首版的 31 张 HTML 纹理已接入自定义 UI（现已更新为上节的 38 张），并通过官方 SDK 素材编译。完整 Mod 的最终构建和游戏内显示仍需后续验收。


### 2026-09-22 数据正确性修复
- 已完成：工程生成同步移除显式 delete_requests 中的 Content 引用，保留其他手工内容和项目元数据。
- 已完成：议程生成不再注册不存在的 KIND_AGENDA；保留议程主表和特质，增加带外键约束的 SQL 回归检查。

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
- `.CIV` 工程结构（schema 0.1.0）、序列化与加载流程已落地，按 `CIV_SECTION_ORDER` 18 节归一化（基础信息/美术/文本/修改器 4 节存 dict，「UI图标」等其余分节存列表；旧工程缺节点自动补空）。
- 主窗口 3 页（主页/工作区/设置）；新建/打开/保存/删除工程；多会话 tab；文件关联双击打开 `.CIV`。

### 2) 分类编辑能力（13 个内容分类全部接入）
- 文明、领袖、区域、建筑、单位、单位晋升、改良设施、总督、伟人、政策卡、项目、信仰、议程。
- 议程完整接入（主表 + HistoricalAgendas / ExclusiveAgendas / AgendaModifiers / AI 偏好）；单位晋升为画布式晋升树编辑器（2221/2212 模板 + 随机模式）。

### 3) 修改器工作区
- Modifier / RequirementSet / Requirement / UnitAbility 全链路编辑；EffectType/RequirementType 搜索与参数模板、中文注释模板；批量生成对话框；战斗预览文本（ModifierStrings）。

### 4) 美术与输出链路
- Icons.xml / ArtDef / XLP / Art.xml / Textures（PNG→DDS→TEX→XLP）/ Moments / 领袖独立 XLP；格式说明见 `docs/TEX_FORMAT.md`。
- **「UI图标」段**（2026-09-19）：`.CIV` 可声明与游戏实体无关的自定义 UI 图标（新闻分类/单位动作/追踪器等），
  只影响 `Icons.xml` 与 IMG/Textures；美术页专属编辑区（列表增删、源图选择与状态提示，工作区树不单列节点），
  校验接入 GUI 生成前检查与 `modgen validate`，命名空间（`ICON_<实体类型>_*`）冲突报 ERROR。
  实现单一来源 `project/ui_icons.py`（Qt-free，GUI/modgen 共用）；11 类实体图标产出未改动。
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
- **skill**（2026-08-17）：本地技能库章节检索——仓库根 `skills/`（从外部工作区内迁并分层整理，
  随发布包分发，入口 `skills/AGENTS.md`），中文/英文分词 + 章节 BM25 + `--file` 全文/`--section` 章节；与 search 分工：
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
