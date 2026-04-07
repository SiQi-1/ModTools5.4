# Changelog

## 2026-03-25 - 修复：编辑器输出 "Unknown property box-shadow"

### 问题描述
- 启动程序或打开 QSS 样式时，终端/编辑器会不断输出多次警告："Unknown property box-shadow"。

### 原因分析
- 样式文件 `resources/styles/base.qss` 中使用了 CSS 的 `box-shadow` 属性，但 Qt 样式表（QSS）不支持该属性。VS Code 的 CSS 语言服务或相关校验器在解析 `.qss` 文件时将其当作标准 CSS，并将 `box-shadow` 视为未知属性，从而产生警告。

### 解决方法
- 在代码层面：为运行时提供了等效的程序化阴影（使用 `QGraphicsDropShadowEffect`），无需依赖 `box-shadow`。
- 在样式层面：已将 `resources/styles/base.qss` 中的所有 `box-shadow` 属性注释掉，避免编辑器/语言服务报错；UI 的视觉效果仍由程序化实现保留。
- 在工作区层面（可选）：已添加 `.vscode/settings.json`，将 `*.qss` 关联为纯文本并忽略未知属性警告，避免编辑器再次报告类似问题。

### 备注
- 此次修改仅移除 QSS 中不受支持的属性并保留程序化实现，保证视觉效果不变且消除误报，便于在 VS Code 中开发与调试。


## 2026-03-20 - 5.4.0-beta.4-hotfix.2（描述类文本框右键插入图标）

### 文本：FontIcons 图标插入（[ICON_XXX]）
- 新增“图标浮层选择器”：在支持的描述类文本框中右键弹出，按 `11 x 25` 网格布局（与 `FontIcons.dds` 一致），空位留空。
- 交互：点击图标插入到当前光标处；点击空位/浮层外区域自动关闭；悬浮显示图标 `Name`（toolTip）。
- 数据一致性：编辑区显示为图标图片；导出/预览仍为 token 字符串（例如 `[ICON_Housing]`）。
- 多名称同一格：若多个 `Name` 共享同一 `Index`，按钮点击会弹出小菜单供选择。
- 浮层优化：图标间距更紧凑；内容超出自动出现滚动条；整行无图标的行会自动隐藏。
- 浮层体验：禁用横向滚动条；弹窗宽度按当前图集“刚好容纳所有列”计算；右键弹窗位置会根据屏幕边缘自动向上/向左避让，避免显示不全。
- 新增 `FontIconsXP1.dds` 支持：对存在大量空洞的 atlas 采用 `packed` 布局（仅按 XML 已定义的 Index 顺序填充，每行 11 个），避免出现大片空位。

### 数据：内置 FontIcons registry
- 新增 `data/font_icons_registry.json`（仅 baseline 4/6/8）：由 `FontIcons.xml` 预处理生成，记录 `Name -> Index/Atlas/Sheet`，并为后续“多图集向下堆叠显示”留出结构。
- 为“自定义图标分区”预留接口（未实现）。

## 2026-03-16 - 5.4.0-beta.4-hotfix.1（加载组文件管理 + 删除计划 + 工程总览过滤）

### 基础信息页：加载组文件管理
- `FrontEndActionData / InGameActionData` 新增文件级操作：
  - `选择文件`：从“未加载文件”中加入当前加载组。
  - `从此加载组删除`：仅移出当前加载组，不删除文件本体。
  - `删除选中文件`：加入删除计划（真删除流程）。
- `UpdateDatabase` 创建文件时新增 SQL/XML 二选一（默认 SQL）。
- 支持类型范围：`UpdateDatabase / UpdateIcons / UpdateText / AddGameplayScripts / AddUserInterfaces / ImportFiles`。

### 创建文件状态识别
- `created -> imported` 判定由“非空”改为“与默认模板比对”：
  - Gameplay Lua / UI Lua / UI XML：仅当内容偏离默认模板时才转为 `imported`。
  - 避免 UI 默认模板文件被误判为导入文件。

### 生成流程：删除计划
- 新增 `file_info.delete_requests` 持久化字段，记录待删除文件。
- 工程总览中：若目标工程目录存在该待删文件，则在树中标红显示。
- “生成所有文件”冲突弹窗新增“待删除文件”区：
  - 默认勾选执行删除；取消勾选则忽略删除。
  - 文案明确提示“删除后不可复原”。

### 工程总览文件显示规则
- 总览文件过滤为白名单：`xml/xlp/artdef/civ6proj/sql/lua`。
- 保留两个清单特例：
  - `IMG/图片生成清单.txt`
  - `Textures/纹理生成清单.txt`

### 工程总览目录结构
- 固定显示 `Import` 文件夹（即使当前无 `Import/*` 文件）。

## 2026-03-16 - 5.4.0-beta.4（领袖xlp分离生成 + 刷新配置读取自定义XLP Class）

### 领袖xlp与Leaders.artdef（美术页）
- 美术页新增“领袖xlp与Leaders.artdef生成”编辑区：每个领袖一行，可勾选是否输出该领袖独立 xlp。
- 领袖 xlp 输出规则：
  - 文件名固定为 `{leaderType.lower()}.xlp`。
  - XLP `m_ClassName` 使用 `Leader`。
  - XLP `m_PackageName` 使用 `leaderType` 全小写（与文件名一致，不带 `.xlp`）。
- `Leaders.artdef` 改为按条件输出：仅当至少勾选了一个领袖 xlp 时才生成该公共文件。

### Art.xml 联动
- 工作区 Art.xml 配置会自动把“已勾选领袖 xlp”并入 `Library -> Leader` 包列表（包名为 leaderType 全小写，去后缀）。
- 结合现有可用性过滤，Art.xml 仅写入可用包名，不再写入不存在的 XLP。

### 基础信息页“刷新配置”增强
- 点击“刷新配置”后，除更新工程总览外，还会扫描工程目录中的“只读自定义 XLP 文件”。
- 自动解析每个自定义 XLP 的 `m_ClassName` 与 `m_PackageName`（缺省回退文件名 stem），并合并进 `art_xml_source_config.libraries`。
- 该过程为“源配置增量合并”，不会覆盖 `.CIV` 内已保存的工作区配置。

## 2026-03-16 - 5.4.0-beta.3-hotfix.1（Art.xml 保底模板 + 单文件输出修正）

### Art.xml 输出规则修正
- `Library/relativePackagePaths` 输出改为包名（去掉 `.xlp` 后缀）。
- 仅在文件“实际存在/可用”时才写入 Art.xml 对应条目：
  - ArtConsumer 的 `relativeArtDefPaths` 仅保留可用 `.artdef`（或空白模板原生条目）。
  - Library 的 `relativePackagePaths` 仅保留可用 XLP 包名（或空白模板原生条目）。
- 解决了把未来规划文件（当前尚未生成/不存在）提前写入 Art.xml 的问题。

### 空白 Art.xml 保底
- 新增内置空白模板：`ModTools_5_4/data/default_blank_art.xml`（参考 `Test.Art.xml`）。
- 当读取 `.civ6proj` 所在目录未找到 Art.xml 时，自动回退到该空白模板作为保底配置。

### 单工程单 Art.xml
- Art.xml 文件名改为优先绑定 `.civ6proj` 文件名（`{civ6proj_stem}.Art.xml`），避免改名后生成新文件并残留旧文件。
- `.civ6proj` 预览中的 `<None Include="...Art.xml" />` 同步改为使用上述单一文件名。

### 工程总览精简
- 移除工程总览中的 `ArtXML/` 额外配置预览目录输出。
- 工程总览仅保留一个根目录 Art.xml 文件输出。

## 2026-03-15 - 5.4.0-beta.3（Art.xml 自动合并预览 + 原工程配置读取）

### Art.xml 规则与数据源
- 新增 `ModTools_5_4/data/art_xml_rules.json`：作为“工作区侧 Art.xml 规则”配置源，集中定义 ArtConsumer 与 Library 的默认映射。
- Art.xml 配置改为双来源存储并自动合并：
  - `art_xml_workspace_config`：来自工作区规则（随工作区刷新）。
  - `art_xml_source_config`：来自原工程目录 Art.xml 读取结果。
- 合并策略：按 ArtConsumer / Library 名称做去重合并（保序，不重复写入）。

### 美术工作区（预览窗口）
- “输出与预览”新增按钮：`读取Art.xml配置`。
  - 按基础信息中的 `.civ6proj` 路径，在同目录优先读取“同名 `.Art.xml`”，找不到则回退读取目录内首个 `*.Art.xml`。
  - 读取结果并入“原始文件配置”，重复项自动去重。
- 预览窗口新增 `Art.xml` 分组，并拆分为三份预览：
  - `{工程名}.Art.xml`（最终合并后的完整 XML）
  - `ArtConsumer（合并预览）.txt`
  - `Library（合并预览）.txt`

### 读取优先级与覆盖规则
- 打开 `.CIV` 时，不覆盖工程中已保存的 Art.xml 配置状态；`.CIV` 内保存的数据优先。
- 当检测到新的 `.civ6proj` 路径且尚未加载对应源 Art.xml 时，会自动尝试读取一次并合并到“原始文件配置”。

### 工程总览与生成
- 工程总览（与 XLP / ArtDef / Icons 同链路）新增 Art.xml 输出项：
  - 根目录 `{工程名}.Art.xml`（用于 `.civ6proj` 的 `<None Include="{工程名}.Art.xml" />`）。
  - 额外调试预览放在 `ArtXML/` 目录（ArtConsumer / Library 文本预览）。

## 2026-03-15 - 5.4.0-beta.2-hotfix.2（主表必填机制 + Trait绑定体验 + 圆形裁切导出一致性）

### 主表必填字段机制（集中配置 + UI 星标 + 生成拦截）
- 新增“必填字段集中规则表”，用于统一标记必填、默认值等规则，便于后续增减。
- 必填字段 UI 标签末尾追加红色 `*`（主表编辑器统一生效）。
- 生成动作前新增必填校验：
  - 区域主表 `MilitaryDomain`：为空时自动写回默认值 `NO_DOMAIN`。
  - 单位主表 `FormationClass`：无合适默认值；为空时弹窗提示并阻止生成。
- SQL 输出策略调整：必填字段对应列在导出时会强制输出，避免被“默认值省略”规则跳过而导致数据库缺列。

### Trait 绑定体验优化
- Trait 绑定选择弹窗：不再显示已选项，避免重复绑定。
- 领袖绑定文明后：领袖侧可选 Trait 会排除该文明已绑定的 Trait，避免重复配置。
- 绑定选择弹窗支持双击条目快速确认。

### 总督 ICON：导出真正圆形裁切 + 可选黑边
- 圆形裁切状态写入图片 state，并在导出渲染路径真实生效（不再仅是预览圆形）。
- 圆形几何统一：以 256×256 为基准，居中且距边 10px（按尺寸等比缩放）。
- 新增勾选项“添加黑边”：默认 3px（按尺寸等比缩放），黑边与圆形裁切相互独立且位于导入图片下层。

### 美术工作区：历史时刻“（已丢失对象）”残留行修复
- 不再为 `moments_map` 中找不到对象的 key 补“孤儿行”（避免出现“（已丢失对象）”与旧名字残留）。
- 刷新时会自动清理无效的 `moment:*` key，避免重命名后旧 key 长期堆积。

### 设计记录：Art.xml 文件应如何生成/补齐（未实现，先记录规则）
- 目标：自动生成与 ModBuddy 输出一致的 `{工程名}.Art.xml`（GameArtSpecification），用于把本工程的 `*.artdef`、`*.xlp`（UITexture 包）与游戏侧 consumer 关联起来。
- 基础策略：以“空白模板 Art.xml”为底（类似 `Test.Art.xml`），复制一份到工程输出目录后再做最小增改（避免手写遗漏 consumer / library）。
- 必填字段：
  - `<id>/<name>`：建议使用 `LOC_{工程名}_NAME`（或项目名文本），与工程基础信息保持一致。
  - `<id>/<id>`：每个工程一个 GUID。
- `artConsumers` 补齐要点（对比正确文件的最小差异）：
  - 只在少数 consumer 里填写 `relativeArtDefPaths`，其余保持空即可：
    - `Audio`：通常引用 `Civilizations.artdef` / `Districts.artdef` / `Units.artdef`（与是否做音频事件相关）。
    - `Civilizations`：`Civilizations.artdef`
    - `Cultures`：`Civilizations.artdef` + `Cultures.artdef`
    - `Clutter`：`Clutter.artdef`
    - `Landmarks`：`Civilizations.artdef` + `Cultures.artdef`
    - `LeaderFallback`：`FallbackLeaders.artdef`
    - `Units`：`Units.artdef`
    - `StrategicView_Translate`：常见为 `Buildings.artdef` + `Districts.artdef`
    - `WorldView_Translate`：常见为 `Buildings.artdef` + `Civilizations.artdef` + `Cultures.artdef` + `Districts.artdef`
  - 少数 consumer 的 `libraryDependencies` 在正确文件中有固定依赖（模板若为空需要补齐）：
    - `Camera`：`CameraAnimation`（且 `loadsLibraries=true`）
    - `Water`：除 `Water` 外，正确文件额外依赖 `SkyBoxTexture`（避免水体/天空盒链路缺库）
  - 其余 consumer 的 `libraryDependencies` 基本可沿用空白模板的固定列表（StrategicView、UI、Leader、VFX、Terrain 等）。
- `gameLibraries` 补齐要点：
  - `UITexture` 的 `relativePackagePaths`：需要包含 `{工程名}_dds`（对应 UITexture XLP 的包名/输出目录），否则 UITexture consumer 找不到本工程纹理包。
  - `LeaderFallback` 的 `relativePackagePaths`：正确文件包含 `LeaderFallbacks`（保持与 ModBuddy/基础库的约定一致）。
- `requiredGameArtIDs`：
  - 需要根据工程目标 DLC 选择（示例中存在 `Expansion1` 与 `Expansion2` 两种 GUID）。
  - 规则建议：若工程使用 GS（XP2）相关资源/库，则使用 `Expansion2`；否则按需要选择 `Expansion1`。
- 路径注意：`relativeArtDefPaths` 中写的通常是文件名（如 `Civilizations.artdef`），前提是这些 artdef 在 Art.xml 旁的相对路径可被解析；若工程目录结构不同（例如放在 `ArtDefs/` 子目录），则需要同步调整为带目录的相对路径。

## 2026-03-08 - 5.4.0-beta.2-hotfix.1（纹理链路修复：TEX/XLP/生成行为）

### 重大修复（.tex 可用性）
- 重写 `Textures/*.tex` 生成模板，统一为可用的 `AssetObjects..TextureInstance` 结构。
- 两类 `.tex`（`UISliceTexture` / `Leader_Fallback`）改为固定模板，仅按条目替换关键字段：
  - `m_SourceFilePath`
  - `m_ExportedTime`
  - `m_Name`
  - `m_DataFiles/Element/m_RelativePath`
- 自动生成链路下，`m_SourceFilePath` 统一改为工程内 IMG 路径：
  - `//civ6/main/{工程名}\IMG\{文件名}.png`

### m_ExportedTime 规则
- `m_ExportedTime` 改为固定公式：`473821489 + YYYYMMDD + HHMMSS`。
- 同一轮纹理生成（同一组 tex）复用同一个 `m_ExportedTime`，保证组内一致。

### UITexture XLP（`{工程名}_dds.xlp`）补齐规则
- 条目来源改为“纹理输出计划”全集，而不再仅限 ICON 系列。
- 新增纳入：
  - 总督单尺寸纹理（如 `GOVERNOR_*`）
  - 领袖直出纹理（前景/背景/外交背景/选择界面等）
  - Moments 导入图模式纹理（有原始路径时）
- 排除规则：
  - 所有 `FALLBACK_*` 不写入 `{工程名}_dds.xlp`
  - 未导入原始图片（无源路径）的项不写入 `{工程名}_dds.xlp`
- 领袖新增勾选项 `是否新增外交背景幕布(BARBAROSSA_4)`：勾选后为对应领袖额外写入一条 XLP Entry：
  - `m_EntryID = {LEADER_后缀}_4`（例如 `LEADER_SIQI_MORTIS` → `SIQI_MORTIS_4`）
  - `m_ObjectName = BARBAROSSA_4`
  - 未勾选时不写入该条目。

### 领袖基础信息新增控件
- 在“领袖基础信息”中，`领袖能力描述` 下方、图片区上方新增同一行两个控件：
  - `选择界面顺序`（整数数字框，默认 `0`）
  - `是否新增外交背景幕布(BARBAROSSA_4)`（勾选框）
- 兼容旧工程：旧 `.CIV` 缺失这两个字段时自动按默认值处理（`0` / `未勾选`），不会导致导入失败。

### Configs.sql（Players.SortIndex）规则调整
- `Players.SortIndex` 改为读取领袖条目的 `选择界面顺序`：
  - 当值为 `0` 时输出 `NULL`
  - 非 `0` 时输出对应整数

### 生成行为调整
- 点击纹理清单生成时，不再落盘 `Textures/纹理生成清单.txt`。
- 批量“生成所有文件”时，同样跳过 `Textures/纹理生成清单.txt` 落盘。
- IMG 侧行为保持不变。

### 兼容与稳定性
- 修复旧工程打开时美术数据被覆盖清空的问题（加载期间避免编辑器回写污染工程状态）。
- 加强美术工作区旧结构兼容（缺失键补齐、Moments 容错、孤儿行回显）。
- 日志增强：保留终端静默，同时镜像写入工作区 `logs` 便于排障。

## 2026-03-07 - 5.4.0-beta.2（Moments：历史时刻插画）

### 新增
- 美术页新增“历史时刻（Moments）插画”专用区域：每条支持“导入图片 / 使用数据库Texture（二选一）”。
- 新增导出 `Data/{工程名}_Moments.sql`：自动生成 `MomentIllustrations` 写入。

### 规则
- 导入图片模式：
  - 未选择图片路径时：不生成 SQL 行、不写入 UITexture XLP、不生成 PNG/DDS/TEX（但清单预览仍会显示“未设置来源”）。
  - 已选择图片路径时：生成 `IMG/Moment_{GameDataType}.png`（456×332）与 `Textures/Moment_{GameDataType}.dds/.tex`，并写入 UITexture XLP。
- 数据库Texture模式：SQL 直接引用所选 Texture（`.dds` 名称）；不会重复导入资产（不进入 IMG/Textures 清单，也不写入 UITexture XLP）。

## 2026-03-07 - 5.4.0-beta.1（Beta：Textures 纹理输出首版）

### 新增
- 工程总览新增 `Textures/纹理生成清单.txt`（预览清单；点击生成后才落盘）。
- Beta 首批支持：为 `LeaderFallback.xlp` 对应的 `FALLBACK_NEUTRAL_*` 生成纹理文件：
  - `Textures/FALLBACK_NEUTRAL_*.dds`
  - `Textures/FALLBACK_NEUTRAL_*.tex`

### 补齐
- `{工程名}_dds.xlp`（UITexture）现在会按“实际可生成的图标 PNG 清单”自动填写 `m_Entries`。
- `Textures/` 现在会额外生成：
  - 所有 `IconTextureAtlases` 对应的图标多尺寸：`Textures/ICON_*_<size>.dds/.tex`
  - 总督最终图（NORMAL/SELECTED）：`Textures/GOVERNOR_*_NORMAL.dds/.tex`、`Textures/GOVERNOR_*_SELECTED.dds/.tex`

### 交互
- 点击生成 `IMG/图片生成清单.txt` 或 `Textures/纹理生成清单.txt`：会同时输出 PNG（IMG）+ 纹理（Textures）。
- 点击“生成所有文件”：会同时输出 PNG（IMG）+ 纹理（Textures）。

### 工程文件
- `.civ6proj` 生成时不再包含 `Textures/`（Folder/Content 均排除），避免把生成物写入工程定义。

### 说明
- `.dds` 为 DX10 Header + `R8G8B8A8_UNORM`（无压缩），并按 2 倍缩小生成 Mips（Beta 默认最小到 3x3）。
- `.tex` 为 ModBuddy 纹理描述 XML，`m_ClassName` 使用 `Leader_Fallback`。

## 2026-03-04 - 5.4.0-alpha.8-hotfix.58（Icons预览：单位肖像OtherName修复）

### 修复
- 修复 `Icons.xml` 预览中单位肖像别名可能指向非肖像图标的问题：
  - 例如 `ICON_UNIT_XXX_PORTRAIT` 现在会正确别名到 `ICON_UNIT_BASE_PORTRAIT`（不再是 `ICON_UNIT_BASE`）。
- 仅影响单位肖像（`unit:*:portrait`）别名链路。

## 2026-03-03 - 5.4.0-alpha.8-hotfix.54（UnitAbility CLASS不再重复写Tags）

### 修复
- 修改器页新增 UnitAbility 时，`TypeTags(Type, Tag)` 中选择的 `CLASS_*` 不再额外写入 `Tags(Tag, Vocabulary='ABILITY_CLASS')`。
- 现在仅保留 `TypeTags` 关联，避免与数据库已存在的 `ABILITY_CLASS` 标签重复定义。

## 2026-03-03 - 5.4.0-alpha.8-hotfix.55（Units 主表 Domain 必出）

### 修复
- 单位主表 `Units` 的 `Domain` 在 SQL 预览中改为“始终输出”。

### 说明
- 即便 `Domain` 等于 UI 默认值（如 `DOMAIN_LAND`）也会写入。
- 原因：`Domain` 不应依赖“默认值省略”规则（它没有可靠的数据库默认值，属于必填字段）。

## 2026-03-03 - 5.4.0-alpha.8-hotfix.56（修改器 AbilityType导出修复 + 文本预览补齐）

### 修改器参数导出修复
- 修复修改器工作区 `AbilityType` 参数偶发导出为“显示文本 | 英文Type”的问题。
  - 现在 `unit_ability_type` 模板只会输出英文 `UnitAbilityType`（下拉项显示仍保留“中文 | 英文”）。

### Text 预览补齐
- `Text` 工作区预览新增两类分组：
  - `LOC_ABILITY_*`（单位 Ability 的 Name/Description）。
  - `LOC_MODIFIER_*_PREVIEW`（修改器预览文本，供 `ModifierStrings(Text=LOC_..._PREVIEW)` 解析）。
- 根因：此前 Text 预览按“对象 type 是否出现在 Tag 中”分组过滤，导致上述 Tag 不包含单位 type 时被漏掉。

## 2026-03-03 - 5.4.0-alpha.8-hotfix.57（Text预览去重：单位基础文本不再包含Ability）

### Text 预览去重
- `LOC_ABILITY_*` 文本不再出现在“单位基础文本”分组中。
  - 统一仅在“单位Ability文本”分组展示，避免重复。

## 2026-03-03 - 5.4.0-alpha.8-hotfix.53（领袖文本预览补齐 + UpdateIcons路径修复）

### 文本预览修复
- 修复领袖编辑区“首都名字 / 领袖名言”未进入 `Text` 工作区预览的问题。
- 这两条文本按 LOC 行强制参与预览，即使内容为空也保留（文本可为 `''`）。

### civ6proj 动作路径修复
- `UpdateIcons` 的文件路径统一为 `Icons/...`（不再使用根目录历史写法）。
- 新建默认动作与 `.civ6proj` 生成阶段均做了修正，避免历史配置继续输出错误路径。

## 2026-03-03 - 5.4.0-alpha.8-hotfix.52（图片最小缩放与居中导出修复）

### 修复
- 修复图片导出偏左上问题：当历史状态 `scale` 过小时，导出前会自动提升到“至少铺满画布”的最小缩放，并自动居中。

### 编辑器一致性
- 图片编辑器不再允许缩放到小于“铺满画布”的最小值，避免再次生成会偏移的状态。

### 影响
- 领袖头像、文明图标及其它共用图片槽位统一生效。

## 2026-03-03 - 5.4.0-alpha.8-hotfix.51（领袖/文明头像导出偏移修复）

### 修复
- 修复旧工程中“预览看起来居中，但导出偏左上”的图片导出问题（领袖头像最明显）。

### 原因与处理
- 旧状态缺少预览画布尺寸信息，导出时坐标换算基准不完整，导致位移偏差。
- 现在进入子条目编辑器时会自动回写当前状态到工程数据，补齐画布参数并统一导出坐标换算。

### 影响范围
- 不仅领袖头像，文明图标等同类图片槽位在旧状态下也可能出现相同偏移；本次一并修复迁移链路。

## 2026-03-03 - 5.4.0-alpha.8-hotfix.50（图片导出缩放坐标修复）

### 修复
- 修复图片导出时的缩放/位移坐标系不一致问题。
- 导出 PNG 时改为按“预览画布 -> 目标尺寸”做换算，输出结果与编辑器预览一致。

### 兼容
- 新保存的图片状态会记录预览画布尺寸信息（用于精确导出）。
- 对旧状态（无画布尺寸）保留回退换算逻辑，避免历史工程无法导出。

## 2026-03-03 - 5.4.0-alpha.8-hotfix.49（civ6proj不再定义IMG）

### 调整
- `.civ6proj` 生成时，`IMG/` 下文件不再写入 `Content Include`。
- `.civ6proj` 生成时，`IMG` 文件夹不再写入 `Folder Include`。

### 兼容
- 在“基于已存在 `.civ6proj` 的 DOM 生成路径”下，会清理已有的 `IMG` 相关 `Content/Folder` 条目。
- 其余行为保持不变：`ArtDefs`、`XLPs` 仍不在工程文件中定义。

## 2026-03-03 - 5.4.0-alpha.8-hotfix.48（AbilityType动态输入下拉模板）

### 新增
- 参数名为 `AbilityType` 时，修改器参数值控件改为专用模板：可输入 + 可下拉选择。
- 下拉选项实时来自“修改器页新增的 UnitAbility”。

### 交互规则
- 下拉允许为空（不强制选择）。
- Ability 列表实时更新时，保留当前输入内容，不会被刷新覆盖。
- 参数名切换触发值控件重建时，也会尽量保留原有输入值。

## 2026-03-03 - 5.4.0-alpha.8-hotfix.47（UnitAbility CLASS下拉显示修复）

### 修复
- 修复 UnitAbility 编辑窗口中 `TypeTags` 的 `ABILITY_CLASS` 下拉文本显示不完整问题。
- 下拉框改为不省略文本，并扩大显示/弹出宽度，长标签可完整查看。

## 2026-03-03 - 5.4.0-alpha.8-hotfix.46（Ability编辑改为简称生成Type）

### Ability 编辑规则调整
- Ability 编辑窗口改为“简称驱动”：
  - 输入简称；
  - `UnitAbilityType` 自动生成并只读。

### 生成规则
- `UnitAbilityType` 生成格式：`ABILITY_{前缀}_{A中缀}_{简称}`。
- `前缀/中缀` 读取自基础信息中的共享工作区参数。
- 当中缀为 `0` 时，跳过 `A中缀` 段，直接按 `ABILITY_{前缀}_{简称}` 生成。

## 2026-03-03 - 5.4.0-alpha.8-hotfix.45（Ability按钮显隐 + 战斗预览文本链路）

### UnitAbility 按钮显隐
- 修改器页“新增Ability”按钮改为默认隐藏，仅当“表名”选择 `UnitAbilityModifiers` 时显示。

### 战斗预览文本（ModifierStrings）
- 在 Modifier 编辑区中，当 `EffectType = EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER` 时，参数表下方显示多行文本框：
  - 对应 `ModifierStrings (ModifierId, Context, Text)`；
  - `Context` 固定输出 `Preview`；
  - `Text` 输出 `LOC_{ModifierId}_PREVIEW`。
- SQL/XML 预览中新增 `ModifierStrings` 表输出（位于 `ModifierArguments` 之后）。

### 文本输出顺序（单位链路）
- 单位文本输出顺序调整为：
  1) 单位基础文本；
  2) 单位能力基础文本（Ability Name/Description）；
  3) 战斗基础文本（Modifier 预览文本 `LOC_{ModifierId}_PREVIEW`）。

## 2026-03-03 - 5.4.0-alpha.8-hotfix.44（修改器页 UnitAbilityModifiers 专项编辑）

### 修改器页新增
- 在“所有者绑定”中，当表名为 `UnitAbilityModifiers` 时，新增 `新增Ability` 按钮。
- 点击后弹出 Ability 编辑窗口，支持编辑：
  - 主表：`UnitAbilityType`、`Name(zh)`、`Description(zh)`、`Inactive`、`ShowFloatTextWhenEarned`、`Permanent`
  - 副表：`TypeTags(Type, Tag)`（Type 固定为 `UnitAbilityType`，Tag 使用 `ABILITY_CLASS` 下拉模板复用）
- 在“所有者对象管理”头部（折叠按钮右侧）新增 `编辑Ability` 按钮：
  - 选中由修改器页新增的 `UnitAbilityModifiers` 所有者后，可回到同一窗口继续编辑。

### 数据与预览联动
- 修改器 payload 新增 `unit_abilities` 存储，支持随工程保存/导入。
- `UnitAbilities.sql` 预览（单位工作区输出链路）已接入这些 Ability：
  - 输出 `Types/Tags/TypeTags/UnitAbilities`；
  - `Name/Description` 作为中文文本写入 `LocalizedText`。

## 2026-03-03 - 5.4.0-alpha.8-hotfix.43（ArtDef 保底输出规则）

### 调整
- ArtDef 输出改为“至少一个文件”策略：
  - 先按分类对象是否存在执行正常过滤；
  - 若过滤后没有任何 ArtDef，则自动输出 `Cultures.artdef` 作为保底文件。

### 细则
- `Cultures.artdef` 不再固定输出：
  - 有其它 ArtDef 要输出时，仍仅在“文明有对象”时输出；
  - 只有在“没有任何 ArtDef 可输出”时，才作为保底强制输出。

## 2026-03-03 - 5.4.0-alpha.8-hotfix.42（空对象分类不再输出对应 ArtDef）

### 修复
- 当以下分类没有对象时，不再生成对应 `ArtDefs/*.artdef` 文件：
  - 文明 → `Civilizations.artdef`、`Cultures.artdef`
  - 领袖 → `FallbackLeaders.artdef`
  - 区域 → `Districts.artdef`
  - 建筑 → `Buildings.artdef`
  - 单位 → `Units.artdef`
  - 改良设施 → `Improvements.artdef`

### 生效范围
- 工程总览预览文件列表不再显示这些空分类 ArtDef。
- `.civ6proj` 生成内容不再包含对应缺失 ArtDef 文件引用。
- 最终输出阶段不再写出这些文件。

## 2026-03-03 - 5.4.0-alpha.8-hotfix.41（基础信息补回描述输入）

### 调整
- 基础信息区域在 `Mod名字` 下新增 `描述` 输入项，使用多行输入框。
- 基础信息现为三个核心字段：`名字`、`描述`、`致谢`。

### 数据同步
- 导入 `.civ6proj` / 工程 payload 时，描述优先读取 `Description`，兼容回退 `Teaser`。
- 导出 payload 时，`Teaser` 与 `Description` 统一写入“描述”输入内容。
- `.civ6proj` 预览与生成时，`LocalizedTextData` 的描述文本改为使用该“描述”输入（不再强制等于名字）。

## 2026-03-02 - 5.4.0-alpha.8-hotfix.40（对象工作区新增删除按钮）

### 新增
- 在对象子条目工作区（文明、领袖、区域、建筑、单位、改良设施、总督、伟人、政策卡、项目、信仰）顶部新增“删除当前对象”按钮。

### 删除流程
- 点击按钮后弹出二次确认；确认后删除当前对象。
- 删除后自动刷新树与工作区：
  - 若该分类仍有对象，自动选中相邻对象；
  - 若已删空，自动回到该分类分组页。

### 同步刷新
- 删除后同步刷新修改器所有者来源与美术工作区数据，保证预览与编辑状态一致。

## 2026-03-02 - 5.4.0-alpha.8-hotfix.39（领袖选择界面图片尺寸调整）

### 调整
- 领袖“选择界面前景图”目标尺寸调整为 `512x1024`。
- 领袖“选择界面背景图”目标尺寸调整为 `384x1024`。

### 同步范围
- 编辑器图片槽位裁切尺寸已同步。
- 工作区导出图片计划（`IMG/*`）目标尺寸已同步，保证预览与输出一致。

## 2026-03-02 - 5.4.0-alpha.8-hotfix.38（.civ6proj 基础信息字段语义修正）

### 字段语义对齐
- `SpecialThanks` 作为“致谢”字段：
  - 基础信息编辑区改为仅编辑“致谢”（写入 `SpecialThanks`）；
  - 不再把“致谢”误映射到 `Teaser`。

### Teaser/Description 输出规则
- 基础信息编辑区不再展示 `Teaser/Description` 编辑输入。
- `.civ6proj` 预览/导出时，`Teaser` 与 `Description` 统一同步输出（同一文本）。

## 2026-03-02 - 5.4.0-alpha.8-hotfix.37（UI文案成品化）

### 首页与版本信息
- 首页标题由“基础架构”文案调整为正式产品标题 `ModTools 5.4`。
- 首页副标题调整为“文明6 Mod 一体化编辑工作台”。
- 关于弹窗版本信息去除“基础架构阶段”字样，统一为正式版本展示。

### 占位提示文案优化
- 搜索页与部分导入提示去除“后续接入/暂未实现”措辞，改为用户可执行的引导文案。
- 功能边界不变，仅优化文案表达与产品完成度观感。

## 2026-03-02 - 5.4.0-alpha.8-hotfix.36（总览巡检：导入异常兜底与日志补全）

### 稳定性补强
- 设置页文本导入流程增加统一异常兜底：
  - 导入异常不再直接抛出 Traceback 终止 UI；
  - 统一弹窗提示并更新状态栏；
  - 写入日志（包含 importer/source），便于复盘。
- 当未找到可导入的 `.xml/.sql` 文件时，设置页显示明确提示，不再走空导入路径。

### 可观测性改进
- `workspace_page` 在 `.civ6proj` XML DOM 生成路径失败时，补充异常日志；
- 仍保留原有文本回退生成逻辑，避免因单一路径失败导致功能中断。

## 2026-03-02 - 5.4.0-alpha.8-hotfix.35（DLC导入与文件夹导入结果对齐）

### 问题
- 设置页中 `导入DLC` 与 `导入文件夹` 在同一目录下结果不一致：
  - `导入DLC` 额外启用了 `LOC_` 标签过滤；
  - `导入文件夹` 未启用该过滤。

### 修复
- 统一两者解析规则：`导入DLC` 不再额外启用 `LOC_` 过滤。
- 现在两种导入方式在相同输入范围下，文本入库结果保持一致。

## 2026-03-02 - 5.4.0-alpha.8-hotfix.34（超大导入修复：SQLite变量上限）

### 修复
- 修复设置页“导入文件夹/导入DLC”在超多文本记录场景下可能触发的：
  - `sqlite3.OperationalError: too many SQL variables`
- 原因是冲突检测阶段使用单条 `IN (...)` 查询全部 Tag，超过 SQLite 绑定参数上限。

### 调整
- `_fetch_existing_tags` 改为分批查询并合并结果（batch 查询），避免单次绑定参数过多。

## 2026-03-02 - 5.4.0-alpha.8-hotfix.33（设置页DLC文本导入修补）

### DLC 导入精准化
- DLC 导入流程新增 `LOC_` 标签过滤：仅导入 `Tag` 以 `LOC_` 开头的中文文本，减少无关文本进入本地库。
- 冲突检测与正式导入统一使用同一过滤规则，避免“冲突弹窗与实际导入集合不一致”。

### 导入性能与稳定性
- 设置页导入流程由“先解析一次用于冲突、再解析一次用于导入”改为“单次解析并复用结果写库”。
- 对大体量 DLC 文本（如 20 万+ 行 XML）减少重复解析开销，降低导入阶段卡顿感。

## 2026-03-02 - 5.4.0-alpha.8-hotfix.32（日志改为仅文件输出，终端静默）

### 日志输出策略调整
- `ModTools_5_4` 日志配置改为仅写入日志文件，不再默认输出到终端（移除 `StreamHandler`）。
- 保留日志级别逻辑（debug 时 `DEBUG`，默认 `INFO`），仅改变输出目标。

### 目的
- 避免终端持续刷屏导致的交互卡顿，降低运行时 I/O 干扰。

## 2026-03-02 - 5.4.0-alpha.8-hotfix.31（Icons.xml：总督与政策卡规则完善）

### 总督图标规则完善
- 总督图标继续使用三组资源：
  - `ICON_{GovernorType}` → `SIZE_GOVERNOR_MAIN`
  - `ICON_{GovernorType}_FILL` / `ICON_{GovernorType}_SLOT` → `SIZE_GOVERNOR_FILL_SLOT`
- `ICON_{GovernorType}_PROMOTION` 改为 `IconAliases` 别名，指向 `ICON_{GovernorType}_FILL`（不再单独走 Atlas 行）。
- 补充总督复用别名（按完整 `GovernorType` 动态生成，不是固定 Ibrahim）：
  - `{GovernorType}_SLOT -> ICON_{GovernorType}_SLOT`
  - `{GovernorType}_FILL -> ICON_{GovernorType}_FILL`

### 政策卡图标规则明确
- 政策卡固定使用 `ICON_ATLAS_POLICIES` 画册，仅通过 `Index` 区分图标。
- `Index` 映射按槽位类型：
  - 经济 `0`、军事 `1`、外交 `2`
  - 伟人/通配及其它未匹配类型统一保底 `3`

### 细节
- `Icons.xml` 生成中的别名行增加去重，避免重复输出相同 `Name/OtherName` 组合。
- 修复总督图标未生成问题：美术工作区读取总督对象时增加 `GovernorType` 兼容（不再仅依赖 `type` 字段）。
- 修复总督 Atlas 命名：从 `ATLAS_ICON_{GovernorType}` 统一为 `ATLAS_{GovernorType}`（含 Fill/Slot 对应画册命名）。

## 2026-03-02 - 5.4.0-alpha.8-hotfix.30（空工作区文件忽略：工程总览与一键配置）

### 空分类文件输出规则统一
- 对以下分类新增“有对象才输出数据文件”规则：
  - 区域、建筑、单位、改良设施、伟人、总督、项目、信仰、政策卡、议程。
- 判定依据改为“工作区对应分类是否存在对象”，不再依赖预览文本内容（避免被注释占位误判为非空）。

### 工程总览（Project Root）
- 当上述分类为空时，不再在工程总览文件列表中生成对应 `Data/*` 文件。
- `单位` 与 `伟人` 的配套文件（`UnitAbilities` / `GreatWorks`）同样遵循该规则。
- `议程` 当前未接入内容，空分类时不再出现占位文件。

### 基础信息一键配置
- 一键配置生成 `UpdateDatabase` 文件列表时，同步忽略上述空分类对应文件。
- 仍保留固定输出文件（如 `Modifiers.sql` / `Moments.sql`）逻辑不变。

## 2026-03-02 - 5.4.0-alpha.8-hotfix.29（伟人个体激活类所有者 AttachmentTargetType 专项支持）

### 修改器所有者绑定专项扩展
- 对 `GreatPersonIndividualActionModifiers` 增加专项处理：
  - 绑定结构从“仅 ModifierId”扩展为“按绑定行存储参数”；
  - 新增 `AttachmentTargetType` 输入下拉框（可手输、可选择）；
  - 下拉候选来自游戏库 `GreatPersonIndividualActionModifiers` 表中去重后的 `AttachmentTargetType`。
- 该控件仅在选中 `GreatPersonIndividualActionModifiers` 所有者时显示；其他所有者不显示该控件。

### 绑定行为与兼容
- `AttachmentTargetType` 属于“所有者-Modifier 绑定行”数据，不属于 Modifier 本体：
  - 同一个 `ModifierId` 绑定到不同伟人个体时，可分别使用不同 `AttachmentTargetType`。
- 兼容历史数据：旧版仅 `bound_modifier_ids` 的结构导入后会自动归一化为新绑定结构。

### 伟人个体 Action/Birth 规则补正
- `GreatPersonIndividualActionModifiers` 仅纳入激活类伟人个体。
- `GreatPersonIndividualBirthModifiers` 同时纳入激活类与巨作类伟人个体。
- 文案语义补充：此处 `Birth` 在工具中按“被动”理解与展示。

### 预览输出同步
- SQL 预览对 `GreatPersonIndividualActionModifiers` 输出三列：
  - `(GreatPersonIndividualType, ModifierId, AttachmentTargetType)`
- XML 预览对应输出 `AttachmentTargetType` 节点。
- 其他所有者表保持原有两列输出，不受影响。

## 2026-03-02 - 5.4.0-alpha.8-hotfix.28（打开工程后全工作区首次刷新）

### 打开工程后统一刷新
- 修复“仅在修改单位后才刷新”的问题：现在在打开 `.CIV` 工程后会自动执行一次全工作区刷新。
- 刷新流程包含：
  - 同步各编辑器到 `workspace.sections`（统一数据源）；
  - 刷新美术工作区；
  - 刷新修改器所有者同步；
  - 刷新文本预览；
  - 刷新工程总览；
  - 预热各分类工作区一次，确保首次进入时数据已是最新。
- 新增日志：打开工程后全量刷新完成时记录 `project` 名称，便于排查刷新链路。

## 2026-03-01 - 5.4.0-alpha.8-hotfix.27（Ability/伟人对象名同步与刷新链路修复）

### 单位 Ability 编辑显示与数据源一致性
- 修复 `UnitAbilityBindingsEditor` 在加载条目时“默认值覆盖已有值”的问题：
  - 不再无条件重写 `UnitAbilityType` / `Tag`；
  - 仅在空值或“自动生成值”场景下回填默认值。
- 解决“打开工程后单位编辑区 Ability 名/Type 显示已变化，但预览与修改器对象名未变化”的来源分叉问题。

### 修改器所有者自动同步补齐（含漏记补录）
- `UnitAbilityModifiers` 候选改为优先读取 `subtables.UnitAbilityBindings`，并兼容回退 `unit_ability_bindings`。
- 新增伟人相关自动候选：
  - `GreatPersonIndividualActionModifiers`
  - `GreatPersonIndividualBirthModifiers`
  - `GreatWorkModifiers`
- 候选生成增加调试日志，便于追踪对象名同步是否生效。

### 预览刷新链路修复
- 子条目变更后新增“当前可见工作区刷新”钩子：
  - 若当前为工程总览，立即刷新总览预览；
  - 若当前为对应分类组，立即刷新该分类预览。
- 增加子条目变更日志（section/index/名称变化），便于定位刷新滞后问题。

## 2026-03-01 - 5.4.0-alpha.8-hotfix.26（文件动作创建与 .civ6proj 生成修复）

### 文件信息区：创建文件与动作约束
- `AddGameplayScripts` / `AddUserInterfaces` 在动作编辑区新增“创建文件”按钮：
  - `AddGameplayScripts` 追加 `Scripts/{文件名}_{简称}.lua`
  - `AddUserInterfaces` 追加 `UI/{文件名}_{简称}.xml`
- `FrontEndActionData` 明确禁用并过滤：
  - `AddGameplayScripts`
  - `AddUserInterfaces`

### 工程总览即时刷新与模板输出
- 修复“创建文件后工程总览不立即刷新”的问题：工程总览清单生成前强制同步基础信息数据。
- `AddGameplayScripts` 关联 `.lua` 文件默认模板补齐：
  - `function Initialize()`
  - `Events.LoadGameViewStateDone.Add(Initialize)`
- `AddUserInterfaces` 关联 `.xml` 文件默认模板补齐，并自动补同名 `.lua` 文件。

### .civ6proj 生成规则修复
- `AddUserInterfaces` 动作固定写入 `<Properties><Context>InGame</Context></Properties>`（有有效 `LoadOrder` 时同时输出）。
- `.civ6proj` 的 `ItemGroup` 追加逻辑中，移除 `XLPs/` 与 `ArtDefs/` 目录及其文件（不写入 `Content` / `Folder`）。

### 文件命名规则修正
- `Icons.xml` 继续使用带前缀命名并位于 `Icons` 文件夹：`Icons/{文件名}_Icons.xml`。
- `XLPs/UI_Icons_dds.xlp` 改为 `XLPs/{文件名}_dds.xlp`（`{文件名}` 仅英文/数字/下划线）。

## 2026-03-01 - 5.4.0-alpha.8-hotfix.25（文档状态同步更新）

### README 状态修正
- `ModTools_5_4/README.md` 从“基础架构阶段”更新为“开发中”状态说明。
- 补充当前实际能力：
  - `.CIV` 工程流（新建/打开/保存）
  - 工作区树与已接入分类编辑器
  - SQL/XML 预览与工程生成输出
- 补充当前缺口说明：
  - 议程（Agendas）尚未完整接入
  - 全局搜索逻辑未接入
  - 部分分类导入与自动化测试仍待完善

### ROADMAP 现状化重写
- `ModTools_5_4/docs/ROADMAP.md` 由早期前瞻规划改为“当前真实进度 + 缺口 + 迭代顺序”。
- 新增分区：
  - `Done`（已完成能力）
  - `TODO`（P1/P2 缺口）
  - 建议迭代 A~D
- 明确维护约定：每次功能变更后需同步更新 `CHANGELOG.md` 与 `ROADMAP.md`，避免文档与代码状态再次偏离。

## 2026-02-26 - 5.4.0-alpha.8-hotfix.24（巨作类伟人编辑区与巨作SQL预览接入）

### 巨作类伟人编辑区
- 在伟人个体编辑器中正式接入“巨作类伟人”专用面板，不再使用占位说明。
- 新增“添加巨作”按钮与巨作列表，选中后显示巨作编辑区。
- 巨作编辑区已接入字段：
  - `GreatWorkType`（简称自动生成：`GREATWORK_{简称}`）
  - `GreatWorkObjectType`
  - `Name`（中文）
  - `Audio`（下拉，来源 `GreatWorks.Audio`）
  - `Image`（下拉，来源 `GreatWorks.Image`）
  - `Quote`（中文输入）
  - `Tourism`（中文显示“旅游业绩”）
  - `EraType`
- `GreatWork_YieldChanges` 以多行副表形式接入（可新增/删除行，编辑 `YieldType` / `YieldChange`）。

### 巨作类个体通用规则
- 巨作类伟人的 `ActionCharges` 在界面中强制锁定为 `0`（仍参与导出）。

### 伟人 SQL/Text 预览扩展
- `伟人` SQL 预览新增输出：
  - `GreatWorks`
  - `GreatWork_YieldChanges`
- `Quote` 规则调整：
  - 编辑器输入中文；
  - SQL 写入 `LOC_{GreatWorkType}_QUOTE`；
  - `Text.sql` 自动输出对应 `LocalizedText`。
- 巨作名称 `Name` 也按 LOC 规则输出并写入 `Text.sql`。

### Types 输出补齐
- 伟人个体现在会补齐 `Types`：
  - `('GREAT_PERSON_INDIVIDUAL_xxx', 'KIND_GREAT_PERSON_INDIVIDUAL')`
- 巨作条目也会补齐 `Types`：
  - `('GREATWORK_xxx', 'KIND_GREATWORK')`

## 2026-02-26 - 5.4.0-alpha.8-hotfix.23（伟人个体新模板与LOC输出规则）

### 伟人个体模板扩展
- 新增 `ABILITY_CLASS` 标签模板：`ability_class_tag`
  - 作为可输入下拉框，候选来自 `Tags` 表中 `Vocabulary='ABILITY_CLASS'`；
  - 支持手输新值与候选补全。
- 新增巨作类型模板：`great_work_object_type`
  - 候选来自 `GreatWorkObjectTypes`；
  - 下拉显示 `Name` 的中文解释并保存英文 `GreatWorkObjectType`。

### 伟人个体字段与默认值规则
- `ActionRequiresNearbyUnitWithTagA/B` 改为使用 `ability_class_tag` 模板。
- `ActionRequiresCityGreatWorkObjectType` 改为使用 `great_work_object_type` 模板。
- `ActionNameTextOverride` 增加默认值：`LOC_GREATPERSON_ACTION_NAME_RETIRE`（新增个体与回填缺省均生效）。
- Birth 两项文本字段文案改为“输入 LOC tag”语义提示。

### 简化单位编辑区字段顺序
- 按需求互换显示顺序：`单位名称` 与 `TraitType完整名字` 的位置互换。

### 伟人 SQL 预览规则补充
- `GreatPersonIndividuals.ActionEffectTextOverride` 改为：
  - 编辑器输入中文效果文本；
  - SQL 中写入 `LOC_{GreatPersonIndividualType}_ACTICE`；
  - 同步在 `LocalizedText` 输出该 LOC 的中文文本。

## 2026-02-26 - 5.4.0-alpha.8-hotfix.22（伟人简化单位区布局对齐单位主编辑器）

### 简化单位编辑区布局调整
- 伟人页面中的“Units（简化单位）”编辑区改为与单位主编辑区一致的左右布局：
  - 左侧为参数编辑列；
  - 右侧为图片列（图标名 + 图片槽位）。
- 图片列改为顶部对齐并固定为内容高度，不再与左侧区域平均分布高度。

## 2026-02-26 - 5.4.0-alpha.8-hotfix.21（伟人简化单位图片控件改为同款槽位UI）

### 图片控件实现回归统一
- 撤回自定义图片导入控件方案，改为复用项目既有 `_ImageSlotWidget`（与文明/领袖/区域/建筑等一致）。
- 伟人简化单位图片区现在沿用统一交互：
  - 选择/清除/重置/缩放；
  - 256x256 输出目标；
  - 与现有 `images` 状态结构保持一致（`set_state/export_state`）。

### 构造链调整
- `GreatPeopleCompositeEditor` 新增 `image_widget_factory` 注入参数；
- 由 `SectionItemWorkspacePanel` 统一注入 `_ImageSlotWidget` 工厂，保持与其它编辑器一致。

## 2026-02-25 - 5.4.0-alpha.8-hotfix.20（简化单位图标与单位预览合并）

### 伟人-简化单位编辑区补充图标位
- 伟人页面的简化单位编辑区新增单位图标编辑位：
  - 固定尺寸要求 `256x256`；
  - 选择图片时自动校验尺寸，不匹配则提示。
- 新增图标名称只读显示位（默认 `ICON_{UnitType}`）。

### 单位 SQL 预览合并伟人简化单位
- `单位` 分类 SQL 预览现在会合并输出伟人页面中“非导入锁定（import_locked=False）”的简化单位数据。
- 合并规则：
  - 若单位类型在“单位”分类已存在，则不重复追加；
  - 导入锁定的伟人类型不参与单位预览输出。

### 单位图标预览备注
- 在 `Units.sql` 预览末尾增加简化单位图标备注注释（图标名与源路径），用于打包时核对素材。

## 2026-02-25 - 5.4.0-alpha.8-hotfix.19（导入伟人个体可编辑与新增按钮可见性修复）

### 导入伟人类型锁定范围调整
- 导入伟人类型（`import_locked=True`）时，锁定范围仅限：
  - 伟人类型编辑区（`GreatPersonClasses`）
  - 简化单位编辑区（`Units`）
- 伟人个体编辑区保持可操作：
  - 允许新增伟人个体；
  - 允许编辑既有伟人个体。

### 新增伟人个体按钮位置修正
- `新增伟人个体` 按钮移入“伟人个体”分组固定行，避免在编辑区滑动时被内容区视觉覆盖。

## 2026-02-25 - 5.4.0-alpha.8-hotfix.18（伟人预览输出规则与个体文本布局修正）

### GreatPersonIndividuals 预览输出规则
- `GreatPersonIndividuals` 预览改为“每个伟人个体独享一个 INSERT 语句”。
- 激活类个体参数改为仅输出“非默认值”字段：
  - 布尔字段按默认值差异输出；
  - 数值字段仅在非默认值时输出；
  - 文本字段仅在非空时输出。

### 导入伟人类型预览过滤
- 对 `import_locked=True` 的导入伟人类型，预览中不再输出：
  - `Types / Traits / GreatPersonClasses / Units` 对应伟人类型数据；
- 仍保留该类型下新增/编辑的伟人个体输出与个体文本输出。

### 伟人个体激活文本参数布局
- 激活类伟人文本参数改为“单行标签 + 单行输入控件”的布局（每个参数一行）。


## 2026-02-25 - 5.4.0-alpha.8-hotfix.17（伟人参数中文标签与模板控件修复）

### 参数展示规则调整（伟人类型 + 伟人个体）
- 伟人类型与伟人个体参数区统一改为：
  - 界面仅显示中文参数说明；
  - 控件与标签鼠标悬浮时显示对应英文参数名（字段名）。

### 伟人个体激活参数控件规范
- 文本参数切换为 `ui_widget_kit.py` 模板控件（`build_template_widget(...)`），不再使用裸 `QLineEdit`。
- 激活参数布局改为：
  - 文本参数：单列布局；
  - 布尔参数与数值参数：双列布局。

### 伟人类型 DistrictType 控件修正
- 伟人类型 `DistrictType` 改为 `district_search` 模板控件，支持搜索选择并保持可手输能力。

### 模板兼容性补丁
- `ui_widget_kit.py` 的 `TextInputTemplate` 新增 `set_current_value(...)`，用于编辑器回填文本值。

## 2026-02-25 - 5.4.0-alpha.8-hotfix.16（伟人编辑器交互与命名修复）

### 布局与默认值修正
- 伟人类型编辑区与简化单位编辑区改为双列参数布局，提升同屏编辑效率。
- 伟人类型与单位名称默认保持空值，不再因回退名显示为 `子条目 N`。
- 激活类伟人个体改为“通用参数 + 激活参数”结构：
  - 通用参数单独分组；
  - 激活参数按“布尔条件 / 文本与数值”分类；
  - 激活参数区域全部采用双列布局。

### 参数解释与控件语义匹配
- 伟人类型、单位简化参数与伟人个体激活参数均补充中文解释标签（字段含义说明）。
- `DistrictType` 升级为“可搜索选择 + 可手填”的区域选择控件。
- `AreaHighlightRadius` 调整为伟人个体通用参数。

### 新增通用 UI 模板（表内去重可编辑选择）
- 在伟人编辑器中新增 `DistinctValueEditableTemplate`：
  - 数据源为指定表字段的去重值；
  - 默认空值；
  - 支持手动输入新值；
  - 支持搜索弹窗快速选择现有值。
- `ActionIcon`、`IconString`、`PseudoYieldType` 已切换为该模板控件。

### 命名规则与导入显示修复
- 伟人个体新增简称字段，完整类型改为自动生成：
  - `GreatPersonIndividualType = GREAT_PERSON_INDIVIDUAL_{简称}`。
- 修复“导入伟人类型后左侧仍显示子条目N”的问题：
  - 导入条目默认 `name` 回填为导入的 `GreatPersonClasses.Name`；
  - 左侧命名回退逻辑新增 `class_data.Name / GreatPersonClassType` 解析。

## 2026-02-25 - 5.4.0-alpha.8-hotfix.15（伟人独立编辑器首版接入）

### 结构调整：伟人独立文件落地
- 新增独立 UI 文件 [ModTools_5_4/ui/pages/great_people_editor.py](ModTools_5_4/ui/pages/great_people_editor.py)，用于承载伟人复杂编辑逻辑，避免 `group_workspace.py` 继续膨胀。
- `伟人` 编辑页不使用通用模板，改为专用编辑器。

### 伟人类型（GreatPersonClasses）编辑区
- 新建伟人现在是“新建伟人类型”。
- 接入 `GreatPersonClasses` 主表字段：
  - `GreatPersonClassType`
  - `Name`
  - `UnitType`
  - `DistrictType`
  - `MaxPlayerInstances`
  - `PseudoYieldType`
  - `IconString`
  - `ActionIcon`
  - `AvailableInTimeline`
  - `GenerateDuplicateIndividuals`
- 命名规则接入：
  - `GreatPersonClassType = GREAT_PERSON_CLASS_{前缀}_{中缀}_{简称}`
  - `UnitType = UNIT_GREAT_{前缀}_{中缀}_{简称}`

### 单位简化编辑区（非模板）
- 在伟人类型页内接入简化 `Units` 编辑区，仅覆盖指定列：
  - `UnitType, BaseSightRange, BaseMoves, FormationClass, Domain, CanRetreatWhenCaptured, CanCapture, Cost, ZoneOfControl, FoundReligion, CanTrain, TraitType, Name, Description`
- UI 初始值接入：
  - `BaseSightRange=4`
  - `BaseMoves=5`
  - `FormationClass=FORMATION_CLASS_CIVILIAN`
  - `Domain=DOMAIN_LAND`
  - `Cost=1`
- TraitType 规则接入：
  - 勾选时输出 `TRAIT_{UnitType}`；并在 SQL 中补 `Types/Traits` 定义。

### 伟人个体（GreatPersonIndividuals）编辑区首版
- 顶部模式二选一：`激活类伟人` / `巨作类伟人`，默认激活类。
- 已接入共有字段：
  - `GreatPersonIndividualType`
  - `Name`
  - `GreatPersonClassType`（固定为所属伟人类型）
  - `EraType`
  - `ActionCharges`
  - `Gender`
- 激活类模式下接入激活专属字段编辑（布尔/文本/数值）。
- 巨作类模式当前按需求仅保留共有字段，激活专属面板隐藏。

### 分组页接入与新增/导入
- `SectionItemWorkspacePanel` 已接入 `伟人` 真实编辑器，不再显示占位页。
- `伟人` 分组导入按钮开启。
- 新增伟人类型：创建可编辑条目（`import_locked=False`）。
- 导入伟人类型：从 `GreatPersonClasses` + 对应 `Units` 回填，导入条目标记只读（`import_locked=True`）。

### 预览接入（首版）
- `工作区 -> 伟人` 已接入 `SQL/XML` 预览。
- SQL 首版覆盖：
  - `Types`
  - `Traits`（当勾选单位 TraitType）
  - `GreatPersonClasses`
  - `Units`（简化列）
  - `GreatPersonIndividuals`（按列集合分组输出）
- Text 首版覆盖：
  - 伟人类型名 `LOC_{GreatPersonClassType}_NAME`
  - 单位 `LOC_{UnitType}_NAME / DESCRIPTION`
  - 伟人个体名 `LOC_{GreatPersonIndividualType}_NAME`

## 2026-02-24 - 5.4.0-alpha.8-hotfix.14（总督编辑器细节修复补记）

### 总督编辑区交互与默认值修复
- 新建总督时，`Name` 不再自动回填 `新总督X`，默认保持空。
- 总督主图区布局调整：
  - 主表区与双主图区改为上下结构；
  - 双主图区内部保持左右两图（`NORMAL` / `SELECTED`）。
- `TransitionStrength` 的 UI 默认值改为 `100`（仅 UI 默认，不改变表默认定义）。
- 增加 `TransitionStrength` 说明行：
  - `100:5回合 125:4回合 150:3回合 250:2回合 500:1.99回合 501:0回合`

### 总督晋升树规则与稳定性修复
- 修复启用晋升时的绘制异常：
  - `QPainterPath.moveTo/lineTo` 参数类型不匹配导致崩溃的问题已修复。
- 晋升前置关系改为新规则：
  - 第一级（左/中/右）前置均为基础晋升（若启用）；
  - 下一级左前置：上一级左+中（若启用）；
  - 下一级中前置：上一级左+中+右（若启用）；
  - 下一级右前置：上一级右+中（若启用）。
- 上述前置关系已同步到可视化折线连接与 `GovernorPromotionPrereqs` SQL 预览生成。

### 总督描述输入升级
- 总督主表 `Description` 改为多行输入（支持 `[NEWLINE]` token 导出）。
- 总督晋升节点 `Description` 也改为多行输入（支持 `[NEWLINE]` token 导入/导出）。

### 事件绑定兼容性修复
- 修复总督编辑器中信号回调参数不匹配导致的 `TypeError`：
  - `lambda _v` 统一调整为兼容多签名的 `lambda *_args`。

## 2026-02-24 - 5.4.0-alpha.8-hotfix.13（总督独立编辑器与预览接入）

### 总督子条目编辑器接入（独立实现）
- `总督` 子条目从占位页升级为独立编辑器（不复用通用主表模板）。
- 主表字段按 `Governors` 表接入：
  - `GovernorType`（自动生成）
  - `Name / Description / Title / ShortTitle`（中文单行）
  - `IdentityPressure / TransitionStrength / AssignCityState`
  - `TraitType` 输入框 + `新TraitType` 勾选 + `自动填充` 按钮
- `TraitType` 自动填充规则：点击后填 `TRAIT_{完整Type}` 并自动勾选 `新TraitType`。

### 固定命名图片与 ICON 编辑位
- 主图固定命名规则：
  - `Image`、`PortraitImage` → `{完整Type}_NORMAL`
  - `PortraitImageSelected` → `{完整Type}_SELECTED`
- 主图尺寸：
  - `{完整Type}_NORMAL`：`206x208`（无圆形裁切）
  - `{完整Type}_SELECTED`：`326x339`（无圆形裁切）
- 三个 ICON 编辑位：
  - `ICON_{完整Type}`、`ICON_{完整Type}_FILL`、`ICON_{完整Type}_SLOT`
  - 尺寸均为 `256x256`，支持圆形裁切。

### 副表勾选与晋升树
- 以勾选方式接入轻量副表：
  - `Governors_XP2.AssignToMajor`
  - `GovernorsCannotAssign.CannotAssign`
- 新增可视化晋升树编辑器：
  - 固定基础晋升 + 三级左中右节点
  - 非基础节点需勾选启用后可编辑
  - 连接线采用方正折线显示前置关系。

### SQL/Text 预览接入
- `工作区 -> 总督` 已接入真实 `Governors.sql` 预览，覆盖：
  - `Types`（Governor 与 Promotion；可选新 Trait 的 `KIND_TRAIT`）
  - `Traits`（仅勾选 `新TraitType` 时输出）
  - `Governors`
  - `Governors_XP2`（勾选时输出）
  - `GovernorsCannotAssign`（勾选时输出）
  - `GovernorPromotionSets`
  - `GovernorPromotions`
  - `GovernorPromotionPrereqs`
- 文本预览新增总督相关 `LocalizedText`：
  - `LOC_{完整Type}_NAME / DESCRIPTION / TITLE / SHORT_TITLE`
  - 各晋升 `LOC_{PromotionType}_NAME / DESCRIPTION`。

## 2026-02-23 - 5.4.0-alpha.8-hotfix.12（改良设施编辑器/预览/导入完整接入）

### 改良设施子条目编辑器接入
- `改良设施` 子条目从占位页升级为完整复合编辑器，包含：
  - 主表：`Improvements`
  - 单行副表：`Improvements_MODE`、`Improvements_XP2`、`Improvement_Tourism`、`Improvement_YieldsOutsideTerritories`
  - 多行副表：
    - `Improvement_BonusYieldChanges`
    - `Improvement_YieldChanges`
    - `Improvement_InvalidAdjacentFeatures`
    - `Improvement_ValidAdjacentResources`
    - `Improvement_ValidAdjacentTerrains`
    - `Improvement_ValidBuildUnits`
    - `Improvement_ValidFeatures`
    - `Improvement_ValidResources`
    - `Improvement_ValidTerrains`
  - 相邻加成：`Improvement_Adjacencies`（复用相邻加成编辑器）

### 关键规则实现
- `Icon` 固定规则：主表导出统一使用 `ICON_{完整Type}`。
- `Improvement_YieldsOutsideTerritories` 特化为单勾选开关（仅按 `ImprovementType` 生成行）。
- `Improvement_BonusYieldChanges.Id` 固定规则：`{完整Type}_{序号}`。
- `Improvement_YieldChanges` 编辑器默认注入 6 种基础产出，初值均为 `0`。
- `Improvement_ValidBuildUnits` 默认自带一行 `UNIT_BUILDER`。
- 改良设施相邻加成 custom 行导出到 `Adjacency_YieldChanges` 时采用占位描述 `Placeholder`（不生成额外文本 LOC）。

### SQL/Text 预览接入
- `工作区 -> 改良设施` 已接入真实 `Improvements.sql` 预览。
- `Text` 工作区已合并改良设施 `LocalizedText`（`Name/Description`）。

### 改良设施导入接入
- 新增 `改良设施 -> 导入` 流程，支持从数据库回填主表与上述副表到编辑区。
- 导入对可选副表缺失保持容错，不再因单表缺失导致整次导入失败。

## 2026-02-23 - 5.4.0-alpha.8-hotfix.11（单位导入功能完善）

### 单位导入可用性修复
- 修复 `单位 -> 导入` 在部分数据库环境下直接失败的问题：
  - 当设置项 `game_db_path` 不可用时，自动回退到默认缓存库 `DebugGameplay.sqlite`。
  - 导入读取改为“可选副表容错”：缺少可选表/列时不再中断整次导入，改为该子表返回空数据。
- 导入结果现在可稳定生成完整单位 payload（主表 + 副表），并保持此前约定：`Ability` 部分不导入。

## 2026-02-23 - 5.4.0-alpha.8-hotfix.10（单位导入与文本XML预览修复）

### 单位导入规则调整
- 完善 `单位 -> 导入`：Ability 部分不再导入。
- 导入后 `UnitAbilityBindings` 保持空列表，避免把数据库现有 Ability 反向回填到编辑区。

### 文本 XML 预览修复
- `LocalizedText` 的空文本属性改为强制保留：
  - 即便文本为空，也输出 `Text=""`。
- 解决预览中出现 `<Row Language="..." Tag="..."/>` 缺少 `Text` 属性的问题。

## 2026-02-23 - 5.4.0-alpha.8-hotfix.9（XML冗余属性清理 + 战略资源空值修复）

### XML 预览清理
- 调整 SQL -> XML 预览转换：
  - 空值属性不再输出（例如 `Description=""`）。
  - `UnitAbilities` 中默认开关值不再输出：`Inactive="0"`、`Permanent="0"`。

### 单位主表 UI 修复
- 修复 `StrategicResource`（战略资源）下拉空值被覆盖的问题：
  - 现在可稳定保持“空值/未选择”状态；
  - 刷新后不再自动跳到第一个资源选项。

## 2026-02-23 - 5.4.0-alpha.8-hotfix.8（单位XML预览分页补齐）

### 单位 XML 预览分页补齐
- `工作区 -> 单位 -> XML预览` 现已与 SQL 预览保持一致，支持分页展示：
  - `Units.xml`
  - `UnitAbility.sql`（内容为 Ability SQL 对应的 XML 预览）
- 解决此前 XML 模式下单位仅显示单页、无法单独查看 Ability 预览的问题。

## 2026-02-23 - 5.4.0-alpha.8-hotfix.7（单位Ability分页与跟随规则修复）

### 单位 SQL 预览分页调整
- `工作区 -> 单位 -> SQL预览` 新增 `UnitAbility.sql` 分页。
- Ability 相关输出从 `Units.sql` 拆分到 `UnitAbility.sql`：
  - `Types`（`KIND_ABILITY`）
  - `Tags`
  - `TypeTags`
  - `UnitAbilities`

### 单位 Ability 跟随规则修复
- `UnitAbilityType` 强制跟随主单位完整 Type：
  - 规则：`ABILITY_{完整UnitType}`
- Ability 绑定 `Tag` 强制跟随主单位完整 Type：
  - 规则：`CLASS_{完整UnitType}`

### SQL 空值规范
- 修复单位导出中的空值文本问题：
  - 不再输出 `None` 字面量；
  - 空值统一输出为 `NULL`。

## 2026-02-23 - 5.4.0-alpha.8-hotfix.6（单位主表UI修正 + Units_XP2导出规则完善）

### 单位主表 UI 修正
- 新增并接入单位主表下拉字段：
  - `FormationClass` 改为固定选项下拉（`FORMATION_CLASS_AIR/CIVILIAN/LAND_COMBAT/NAVAL/SUPPORT`）。
  - `PromotionClass` 改为 `UnitPromotionClasses` 数据源下拉。
- 修复 `PromotionClass` 下拉灰置问题：
  - 兼容数据库列名差异（`PromotionClassType` / `UnitPromotionClassType`），避免因列名不一致导致数据源为空。
- `PseudoYieldType` 改为英文输入框（不再使用产出模板下拉）。
- 单位主表上半区布局改为“按视觉框数分配”：
  - 仅单位主表生效；
  - 上半部分容量 `16` 框；
  - 多行输入框按 `3` 框计算，普通输入按 `1` 框；
  - 其余字段进入下半区并保持双列排布。

### 单位 SQL 导出规则：`Units_XP2`
- 调整为“仅输出非默认值列”：
  - 单位 `Units_XP2` 单行副表中，字段值与默认值一致时不再输出该字段。
- 新增“同参数结构合并”规则：
  - 多个单位若 `Units_XP2` 的非默认字段集合一致，合并到同一条 `INSERT ... VALUES (...), (...);`。
  - 字段集合不同则拆分为多条 `INSERT`。

## 2026-02-20 - 5.4.0-alpha.8-hotfix.5（建筑细节修复 + 单位编辑页接入）

### 紧急修复（2026-02-20，单位页启动卡死）
- 修复单位页首次加载时可能出现的列宽分配死循环：
  - 触发场景：多列表格列数较多、可视宽度较窄时，旧算法在“最小列宽约束”下无法收敛，导致主线程卡死（表现为启动后进入工作区卡住）。
- 修复方式：
  - 新增统一列宽拟合函数，改为“自适应最小宽度 + 可收敛的差值回收”策略。
  - 对区域/建筑/单位三类多行副表的比例列宽分配逻辑统一替换，避免同类问题复发。

### 建筑：巨作主题文本 LOC 规则修复
- 修复 `Building_GreatWorks.ThemingBonusDescription` 预览输出：
  - 当编辑文本非空时，SQL 统一输出 `LOC_{完整Type}_{槽位简称}_THEMING`。
  - 同步向 `LocalizedText` 自动追加对应中文文本行。
- 兼容历史数据：
  - 若旧数据把中文直接写在 `ThemingBonusDescription`（非 `LOC_`），导出时自动识别为文本并转换为 LOC + Text 行。

### 建筑：副表布局与显示规则完善
- 建筑副表布局调整为：
  - `Buildings_XP2` 独占单行。
  - 其余副表恢复双列配对布局（表与表之间左右两列）。
  - `Building_GreatWorks` 保持独占展示。
- 修复多行副表列宽：
  - 改为严格贴合可视区的比例分配，避免最右列被截断。
- 勾选框/数值悬浮提示：
  - 主表与副表中仅 `QCheckBox` / `QSpinBox` / `QDoubleSpinBox` 显示英文参数名 tooltip。
  - 修复“标签 + 勾选框重复英文参数名”问题，勾选框本体不再重复显示参数文本。
  - 参数标签显示规则统一为“优先中文解释；无中文时回退英文参数名”。

### 单位：编辑页与预览链路首轮接入
- 新增单位主表 schema（`Units`）并接入到工作区子条目编辑器：
  - 单位主表支持双图片：
    - `ICON_{完整Type}`
    - `ICON_{完整Type}_PORTRAIT`（放在图标下方）
- 新增单位副表编辑器：
  - 单行：`Units_MODE`、`Units_Presentation`、`Units_XP2`、`UnitReplaces`、`UnitUpgrades`、`UnitCaptures`
  - 多行：`UnitRetreats_XP1`、`Unit_BuildingPrereqs`、`UnitAiInfos`
  - 迁移增强：`TypeTags`、`UnitAbilityBindings`（单位能力/ModifierType 绑定迁移版）
- 特殊规则接入：
  - `Units_XP2` 独占单行。
  - `CivUniqueUnitType` / `Unit` / `CapturedUnitType` 视为当前主 `UnitType` 自动继承。
  - `UpgradeUnit` 新增“填充建议”按钮与建议值显示：
    - 建议值来源为 `UnitReplaces.ReplacesUnitType` 在 `UnitUpgrades` 中对应的 `UpgradeUnit`。
- 新增 `UnitAiTypes` 搜索模板：
  - `AiType` 选择器改为数据库弹窗搜索（来源 `UnitAiTypes`），并提供中文解释展示。

### 单位：工作区 SQL/Text 预览与导入接线
- `工作区 -> 单位` 已接入真实 SQL 预览（不再占位）。
- SQL 预览覆盖：
  - `Types`、`Traits`、`Units`
  - `Units_MODE`、`Units_Presentation`、`Units_XP2`
  - `UnitReplaces`、`UnitUpgrades`、`UnitCaptures`
  - `UnitRetreats_XP1`、`Unit_BuildingPrereqs`、`UnitAiInfos`
  - `TypeTags`、`UnitAbilities`、`UnitAbilityModifiers`、`Modifiers`（迁移版）
- Text 工作区合并单位 `LocalizedText` 输出。
- 新增单位导入（数据库 -> 新单位条目）：
  - 支持主表与上述副表回填到单位复合编辑器。

### 单位：主表必出字段与独立迁移区修复（2026-02-20）
- 主表 `Units` 导出规则修正：
  - `Description` 现在始终输出（即便描述为空，也写 `LOC_{UnitType}_DESCRIPTION`）。
  - `BaseMoves` 与 `BaseSightRange` 现在作为必出字段，默认值也会输出。
- `UnitAiTypes` 中文解释重做：
  - 由“统一占位说明”改为“固定映射 + 自动词元翻译”组合策略。
  - 搜索弹窗可直接看到按 `AiType` 语义翻译的中文。
- `TypeTags` 改为独立编辑区域（不再使用通用模板表格）：
  - 固定 `CLASS_*` 勾选区。
  - 自定义 Tag 从数据库 `TypeTags(Type LIKE 'UNIT_%')` 选择并维护。
  - SQL 严格按 `TypeTags(Type, Tag)` 输出。
- 单位 Ability/Modifier 绑定改为独立编辑区域（不再使用通用模板表格）：
  - 支持 Ability 基本信息（`UnitAbilityType/Tag/Name/Description`）。
  - 支持 Modifier 基本链路（`UnitAbilityModifiers`、`Modifiers`）及运行控制字段。
  - 新增 `ModifierArguments` 与 `ModifierStrings(Preview)` 输出与导入回填。

## 2026-02-20 - 5.4.0-alpha.8-hotfix.4（区域SQL输出规则完善）

### 区域数据预览导出
- `工作区 -> 区域分组` 已接入真实 `Districts.sql` 导出（不再占位）。
- 导出覆盖：
  - `Types`
  - `Traits`（仅当 `Districts.TraitType` 非空）
  - `DistrictReplaces`
  - `Districts`
  - `Districts_XP2`
  - `District_CitizenYieldChanges`
  - `District_TradeRouteYields`
  - `District_GreatPersonPoints`
  - `District_RequiredFeatures`
  - `District_ValidTerrains`
  - `District_Adjacencies`
  - `Adjacency_YieldChanges`

### 导出规则对齐
- 主表 `Districts`：
  - `Name` 与 `Description` 列始终输出（即便文本为空）。
  - 其他字段仅在“非默认值”时输出。
- 单行副表（`Districts_XP2` / `DistrictReplaces`）：仅在非默认或有效值时输出。
- 多行副表：按表一次性输出单条 `INSERT ... VALUES (...), (...);`，不按默认值过滤。

### 相邻加成导出
- `District_Adjacencies` 统一按区域条目输出绑定 ID。
- `Adjacency_YieldChanges`（自定义）改为“同参数结构合并、不同参数结构拆分”：
  - 字段集合一致的记录合并到同一条 `INSERT`。
  - 字段集合不同的记录分开生成 `INSERT`。

### 文本导出
- 区域相关 `LocalizedText` 已接入 `Text` 工作区合并预览。
- 区域 `Name/Description` 对应文本行始终生成（`Text` 可为空字符串但不缺行）。

### 输出规则补充（2026-02-20）
- `Cost` 规则：
  - 主表 `Cost` 在编辑端最小值提升为 `1`，并在导出时始终写入（视为必填）。
- Trait 文本引用规则：
  - 当区域启用 `TraitType` 时，`LOC_{TRAIT}_NAME / LOC_{TRAIT}_DESCRIPTION` 文本改为索引引用：
    - `"{LOC_{DISTRICT}_NAME}"`
    - `"{LOC_{DISTRICT}_DESCRIPTION}"`
- XML 预览格式调整：
  - `Row` 节点由子节点模式改为属性模式（`DistrictType="..."`），不再输出 `<DistrictType>...</DistrictType>`。
- SQL 表块排版：
  - 统一保证表与表之间至少一行空行分隔，避免 `);` 与下一段表注释紧贴。

### 区域导入功能（数据库 -> 新区域条目）
- `区域 -> 导入` 已接入可用流程：
  - 选择窗口复用“区域搜索选择框”同款对话框样式。
  - 选择后从数据库读取区域主表与副表数据，自动创建新区域条目并写入编辑区。
- 导入范围：
  - 主表：`Districts`
  - 副表：`Districts_XP2`、`District_GreatPersonPoints`、`District_CitizenYieldChanges`、`District_RequiredFeatures`、`District_TradeRouteYields`、`District_ValidTerrains`、`DistrictReplaces`、`District_Adjacencies`
  - 明确不导入：`Adjacency_YieldChanges`（按 existing 模式仅导入 `YieldChangeId` 绑定）
- 文本处理规则：
  - `Name/Description` 导入时自动解析为中文文本。
  - 未解析到中文时显示 `未知`。
  - 数据库字段为 `NULL` 时保持空值（不强制填充）。

### 导入与编辑细节修复
- 区域导入简称规则修复：
  - 不再取最后一段下划线后缀。
  - 统一按 `DISTRICT_` 后完整片段作为简称（保留中间下划线）。
- 通用主表描述字段输入升级：
  - `Description` 改为多行文本控件。
  - 回车输入转换为 `[NEWLINE]` token。
  - 导入/导出自动做 token 文本互转。

### 本轮修复（UI置顶与前置条件导入）
- 主表右侧图片编辑区改为“顶对齐”：
  - 图标名输入框与图片编辑器固定贴顶显示，不再在右列中被纵向均分拉开。
- 前置科技/前置市政导入增强：
  - 修复主表模板字段在旧格式（`dict`）值下的回填失败问题。
  - 区域数据库导入对 `PrereqTech/PrereqCivic` 增加兼容键兜底读取，确保可正确回显。

### 前置科技/市政稳定性补强（追加）
- 主表模板字段读写改为“字段专用取值”：
  - `PrereqTech` 与 `PrereqCivic` 不再依赖通用“首个非空字段”策略。
  - 同时兼容旧键名与大小写差异（如 `TechnologyType/CivicType`、`Value/Type` 等）。
- 区域数据库导入的键名匹配改为不区分大小写：
  - 解决不同数据源/历史导入格式导致的键名大小写偏差问题。

### 根因修复（前置科技/前置市政仍不生效）
- 修复 `technology_search` 与 `civic_search` 模板类缺失 `set_current_value` 的问题：
  - 导入回填时此前无法写入控件，导致界面显示为空并在后续保存时丢失。
- 同步修复模板输入状态逻辑：
  - 手动输入/弹窗选择均会标准化为大写 Type，并稳定写入 `export_data`。

### 建筑工作区扩展（副表 UI / SQL 预览 / 导入）
- 建筑编辑器由“仅主表”升级为复合编辑器：
  - 新增单行副表：`Buildings_XP2`、`BuildingReplaces`。
  - 新增多行副表：
    - `BuildingPrereqs`
    - `Building_CitizenYieldChanges`
    - `Building_GreatPersonPoints`
    - `Building_RequiredFeatures`
    - `Building_TourismBombs_XP2`
    - `Building_ResourceCosts`（含“谨慎填写”提示）
    - `Building_ValidFeatures`
    - `Building_ValidTerrains`
    - `Building_YieldChanges`
    - `Building_YieldChangesBonusWithPower`
    - `Building_YieldDistrictCopies`
    - `Building_YieldsPerEra`
    - `BuildingConditions`
    - `Building_BuildChargeProductions`
- `Building_GreatWorks` 采用独立特殊编辑器（不走通用模板）：
  - 槽位类型、主题化规则、倍率、非唯一作者加成、主题文本独立编辑。
  - 参考 4.5 规则支持“槽位类型去重”与描述自动生成提示。
- 建筑 SQL 预览接入：
  - `工作区 -> 建筑` 支持主表+副表完整生成。
  - `Building_GreatWorks` 按默认值裁剪非必要列并逐条 INSERT 输出。
  - Text 工作区已合并建筑 `LocalizedText`。
- 建筑导入接入：
  - `建筑 -> 导入` 复用建筑分组搜索弹窗。
  - 从数据库回填主表与上述副表到 5.4 建筑复合编辑区。

### 建筑编辑区大修（布局与说明体系）
- 统一中文说明映射：
  - 新增文件头集中映射表，建筑各副表与参数中文解释统一从映射读取。
  - 支持“同名参数在不同表含义不同”的独立说明。
- 布局调整：
  - `Buildings_XP2` 改为独占一行展示（不再与其他表并排）。
  - 建筑副表区由双列混排改为单列顺排，减少横向挤压与遮挡。
- `BuildingConditions` 结构修正：
  - 改为单行表编辑器（`BuildingType + UnlocksFromEffect`），不再按多行表处理。
- 多行表头规范：
  - 表格表头统一为纯英文参数名。
  - 中文解释下沉到对应表说明文本中，不再写在表头。
- 宽度与滚动优化：
  - 建筑多行表按可视宽度进行比例列宽分配，关闭内部横向滚动条。

## 2026-02-19 - 5.4.0-alpha.8-hotfix.3（区域副表UI与滚动行为修复）

### 区域副表（Districts）UI优化
- `District_GreatPersonPoints` 多行副表改为与 Modifiers 参数区一致的“按钮 + 表格行”样式：
  - 列：`GreatPersonClassType / PointsPerTurn / 操作`
  - 支持逐行添加与删除
  - `DistrictType` 继续自动继承主表完整 Type
- `Districts_XP2` 单行副表改为纯两列字段布局，不再拆分“布尔区/数值区”。

### 字体显示与行高修复
- 移除副表行控件的固定高度限制，修复字体上下被裁切的问题。
- 删除按钮改为更紧凑样式（小字号、紧凑按钮），与参数表视觉密度保持一致。

### 滚动行为统一
- 移除主表编辑器 `MainTableEditor` 内部滚动容器，避免“表内再滚动”。
- 现在仅保留外层工作区主滚动区域承接滚动。
- 多行副表表格改为按行数自动撑高并关闭自身滚动条，确保区域内全显示。

### 补充修复（主滚轮恢复）
- `SectionItemWorkspacePanel` 已恢复并统一外层主滚轮区：
  - 文明 / 领袖 / 区域 / 建筑 编辑页均改为“编辑器内容 + 单一外层滚动容器”。
  - 修复此前无主滚轮导致内容被压缩显示的问题。

### 区域副表扩展与中文说明补充
- 区域副表标题已去除“副表 / 多行 / 单行”等冗余文案，仅保留表名。
- 各区域副表新增中文说明文本，明确用途与填写语义。
- 新增并接入以下区域表：
  - `District_CitizenYieldChanges`
  - `District_RequiredFeatures`
  - `District_TradeRouteYields`
  - `District_ValidTerrains`
  - `DistrictReplaces`
- `DistrictReplaces` 规则补充：
  - `CivUniqueDistrictType` 视为当前主表 `DistrictType` 自动继承。
  - `ReplacesDistrictType` 使用“无 Trait 区域”搜索选择框。
  - 中文语义：`取代区域`。

### 多行表对齐规范
- 修复多行表单元格控件默认垂直居中导致的显示问题，改为统一“顶部对齐”。
- 多行表行高改为按内容自适应计算后整体撑开，避免文字/控件观感不一致。
- 后续新增多行表均按“单元格内容顶部对齐”规则实现。

### 双列表行置顶修复
- 修复“表与表两列布局”下左列增高时右列区域被同步拉伸，导致控件在 Y 轴分散显示的问题。
- 双列表行改为列级顶部对齐容器：左/右列内容均固定贴顶显示，剩余空间留在底部，不再做均匀分布。

### 多行表列宽策略优化
- 回退“多行表内部单元格置顶包装”，恢复单元格默认控件布局（不再强制单元格内容顶部对齐）。
- 多行表列宽改为“按表头完整显示所需最小宽度建立比例”，在区域变宽时按比例拉伸分配。
- 当区域宽度不足以完整容纳表头最小宽度时，保留最小宽度并由外层主滚动承接。

### 4.5 区域相邻加成窗口迁移（首轮完整接线）
- 将 4.5 的“区域相邻加成”编辑能力接入到 5.4 区域复合编辑器中：
  - 新增 `AdjacencyEditorWidget` 在 `区域` 页面可直接使用（添加已有 / 新增自定义 / 编辑自定义 / 移除选中）。
  - 自定义相邻加成窗口沿用现有 5.4 组件能力，保留 `ID/描述/产出/前置条件/相邻来源` 结构。
- 区域数据载入/导出接线完成：
  - 读取键：`subtables.District_Adjacencies`（兼容 `adjacencies`）
  - 导出键：`adjacencies` 与 `subtables.District_Adjacencies`
- 自动 ID 上下文补齐 4.5 中缀规则：
  - `AdjacencyAutoContext` 新增 `district_infix`。
  - 区域相邻加成自动 ID 生成现在支持前缀 + `Dxxxx` 中缀 + 区域简称拼接。

## 2026-02-15 - 5.4.0-alpha.8-hotfix.2（文明/领袖图片编辑器与尺寸约束）

### 文明与领袖右上角 ICON 区
- 文明编辑页与领袖编辑页顶部新增嵌入式 ICON 区域：
  - 文本：`ICON_{完整Type}`（只读）
  - 下方：可调整图片框
- 布局位置对齐要求：与“简称/完整Type”同一行右侧显示。

### 新图片编辑控件（通用）
- 原静态图片框升级为“可平移 + 可缩放”编辑器：
  - 鼠标拖动平移
  - 鼠标滚轮缩放
  - 按钮：选择 / 缩小 / 放大 / 重置 / 清除
  - 支持拖拽文件到图片框
- 默认导入规则：
  - 按覆盖目标框进行缩放
  - 初始定位左上角对齐

### 尺寸约束
- 文明 ICON：`256 x 256`
- 领袖 ICON：`256 x 256`
- 领袖加载背景：`1960 x 960`
- 领袖加载前景：`960 x 960`
- 领袖外交背景：`1960 x 1600`
- 领袖外交前景：`960 x 960`

### 数据兼容
- 图片数据改为保存可编辑状态（路径 + 缩放 + 偏移 + 目标尺寸）。
- 向后兼容旧结构：旧版仅路径字符串数据可继续读取。

### 本次微调补充
- 文明/领袖基础信息顶部两列新增“高度平衡”策略：
  - 运行时按左列 `sizeHint` 估算可用高度。
  - 自动下调右列 ICON 图片预览高度（限制在合理区间），使左右视觉高度更协调。
  - 窗口尺寸变化时会实时重新计算并更新。

- 文明 ICON 与领袖 ICON 图片编辑新增 `圆形裁切` 按钮：
  - 调整为单一布尔状态：`圆形预览`。
  - 仅改变编辑框预览形态（圆形蒙版），不执行图片落盘与替换。
  - 预览状态下仍可继续平移/缩放调整。
- 领袖下方“加载/外交”四张图片不启用圆形裁切按钮（保持原编辑逻辑）。
- 最小缩放下限放宽，允许继续缩小并显示透明空背景填充区域。

### 通用主表 UI 模块（区域首批接入）
- 新增通用 Schema 驱动主表编辑器：
  - 文件：`ui/pages/entity_table_form.py`
  - 支持基础信息区、数值区（三列）、布尔区（三列）、联动参数组。
- 首批接入 `区域 -> Districts` 主表编辑：
  - `DistrictType` 作为完整 Type 自动生成。
  - `Name/Description` 中文输入。
  - 模板映射字段优先使用 `ui_widget_kit` 对应模板（科技/市政/掠夺类型/领域/成本递增/顾问类型）。
  - 未映射 `TEXT` 字段默认英文输入框。
- 右上角图片区已按主表模式接入（含圆形预览能力）。

### 可配置入口
- 区域主表定义与中文标签：`ui/pages/entity_table_form.py` 中 `build_districts_main_schema()`。
- 字段模板映射表：`ui/pages/entity_table_form.py` 中 `DISTRICT_TEMPLATE_MAPPING`。

### 本次修复补充
- `TraitType` 改为布尔联动控件：
  - 勾选后自动显示并导出 `TRAIT_{完整Type}`。
  - 未勾选则导出空值。
- 修复科技/市政搜索控件占位提示文案错误：
  - 科技改为“可直接输入或点击选择科技Type”。
  - 市政改为“可直接输入或点击选择市政Type”。

- 区域主表编辑器中 `Name` 输入框不再默认回填“新区域N”，保持初始为空。
- 通用主表编辑器新增反向 SQL 接口：
  - `export_main_table_row()`：导出当前主表字段字典。
  - `build_main_table_insert_sql()`：导出当前单行 `INSERT INTO ... VALUES ...` SQL。

- 数字显示与输出优化：
  - 实数输入框显示改为有效数字（去除无意义尾零），如 `-1` 不再显示为 `-1.000000`。
  - SQL 导出中的实数字段同样按有效数字输出。

- 复用验证：新增 `Buildings` 主表 schema 并接入 `建筑` 编辑区：
  - 字段定义与中文标签、模板映射、分区布局均由通用模块生成。
  - `ObsoleteEra` 已映射为时代选择框。
  - 其他可映射字段已按现有 `ui_widget_kit` 模板进行识别与接入。

- 通用主表基础信息区布局优化：
  - 改为固定阈值分段（不再按高度动态估算）。
  - 当前默认阈值：
    - 首段（与图片同排）字段数：8
    - 后续双列每列字段数：8
  - 首段改为“多列 UI + 图片”布局。
  - 剩余基础字段固定按“左列/右列”双列表单分配（即便不足阈值也会拆成两列），避免退化为单列。

## 2026-02-15 - 5.4.0-alpha.8-hotfix.1（领袖预览与文明选择窗口修复）

### 本次修复
- `领袖 -> 外交文本区域` 改为高度自适应：
  - 不再使用固定高度容器限制显示。
  - 表格按行内容自动撑高，内部纵向滚动关闭，交由外层工作区滚动承接。

### 绑定文明选择窗口
- 新建/本地文明优先显示：
  - 排序优先级调整为 `本地文明 > 数据库文明`。
  - 名称以 `新文明` 开头的条目在本地文明中优先展示。
- 本地文明条目增加颜色标记，便于快速识别当前工程内创建的文明。

### 领袖 SQL/XML 预览
- `工作区 -> 领袖分组预览` 已从占位改为真实生成，支持 `SQL预览 / XML预览`：
  - `Types`
  - `Traits`
  - `Leaders`
  - `CivilizationLeaders`
  - `LeaderQuotes`
  - `LeaderTraits`
  - `LoadingInfo`
- 图片名称注释区已接入（加载前景/加载背景/外交肖像/外交背景）。
- 注释格式按要求统一为 `-- XXX 表`，不再附加“共 N 条”。

### 文本预览
- `工作区 -> 文本` 预览现在合并文明与领袖的 `LocalizedText` 生成结果，SQL/XML 两种格式保持一致。

## 2026-02-15 - 5.4.0-alpha.8（领袖页面首版接入）

### 本次实现
- `领袖` 子条目编辑器已接入并可实际编辑，页面分为三大区域：
  - 领袖基础信息
  - 领袖绑定区域
  - 领袖外交文本区域

### 领袖基础信息
- 新增字段：
  - 领袖简称（仅英文/数字/下划线）
  - 完整Type（实时联动）
  - 领袖名字（中文）
  - 性别（男/女，默认男）
  - 首都名字（中文）
  - 绑定文明（可手输 + 选择按钮）
  - 加载文本（中文）
  - 领袖名言（中文）
  - 领袖能力名字（中文）
  - 领袖能力描述（中文）
- 换行输入统一使用 `[NEWLINE]`（回车直接写入 token）。

### 通用 Type 规则
- 抽取通用 Type 构建函数，文明与领袖统一走同一套逻辑：
  - `头部_{前缀}_{字母中缀4位}_{简称}`
  - 当前已用于：`CIVILIZATION(C)`、`LEADER(L)`

### 绑定文明选择
- 选择文明弹窗支持：
  - 本地工作区文明
  - 数据库主要文明（major civ）
- 排序规则：未知文明靠后，支持 Type/名字搜索过滤。

### 图片名字与图片槽位
- 新增加载/外交图片名字区域（两行两列）：
  - ForegroundImage / BackgroundImage
  - DiploForegroundImage / DiploBackgroundImage
- 对应每个名字下方都支持图片槽位：
  - 可拖入图片文件
  - 可点击选择图片
  - 支持清除
- 图片路径可随领袖条目保存/读回到 `.CIV` 工程数据（JSON）。

### 绑定对象与外交文本
- 领袖绑定区域复用文明同款“绑定对象区域”组件（添加/删除所选 + 分类/名称/Type表格）。
- 外交文本区域内置外交场景参数，不依赖外部文件导入；Tag 随领袖 Type 自动生成。

### 工作区接线
- `workspace_page.py` 已接入领袖编辑器数据通道：
  - 新增领袖默认 payload
  - 新增文明列表提供器（供领袖绑定文明弹窗）
  - 保持树节点名称回写逻辑兼容

## 2026-02-15 - 5.4.0-alpha.7-hotfix.10（文明绑定Trait改为5.0绑定对象区域）

### 本次调整
- `文明编辑页` 的 `Trait绑定区域` 已改为 `ModTools5.0` 风格的 `绑定对象` 区域：
  - 按钮：`添加` / `删除所选`
  - 列表：`分类 / 名称 / Type`
  - 添加时弹窗按分类分页多选（区域、建筑、单位、改良设施、伟人、项目、议程）
- 绑定对象来源改为当前工作区已创建的对应分类条目。

### 数据与兼容
- 绑定数据存储改为对象结构（含分类、名称、Type、索引），不再仅是字符串列表。
- 兼容旧数据：旧版字符串绑定会自动读取并显示为可兼容条目。
- 文明 SQL 预览已兼容新结构，`CivilizationTraits` 会按绑定对象 `Type` 自动转为 `TRAIT_{Type}`。

## 2026-02-15 - 5.4.0-alpha.7-hotfix.9（城市/市民自定义折叠布局顶对齐修复）

### 本次修复
- `文明 -> 城市名字/市民名字 -> 自定义模式` 在折叠状态下，顶部控制行不再垂直居中。
- 通过将自定义页布局设置为顶对齐，并增加底部伸缩位，确保控件始终贴顶显示。

### 影响范围
- 城市名字自定义页
- 市民名字自定义页

## 2026-02-14 - 5.4.0-alpha.7-hotfix.8（左侧树名称同步修复）

### 问题表现
- 编辑文明名字时，左侧树节点名称未随输入同步更新（尤其是第一个条目）。

### 原因
- 树节点刷新逻辑在比对 `section_item` 索引时，使用了 `int(value or -1)`。
- 当索引为 `0`（第一个条目）时会被误判为 `-1`，导致名称更新条件不成立。

### 修复内容
- 索引解析改为显式 `try/except` 转换，不再使用 `or -1` 这种会吞掉 `0` 的写法。
- 现在第一个与后续条目都能正确实时同步左侧树名称。

## 2026-02-14 - 5.4.0-alpha.7-hotfix.7（文明名默认空与[NEWLINE]输入修复）

### 本次修复
- 新增文明时，`文明名字` 输入框默认改为空，不再自动填入 `新文明N`。
- 左侧树节点名称与文明名字联动修正：
  - 文明名字为空时，仍显示占位名 `新文明N`。
  - 文明名字有值时，左侧树节点实时同步为该名字。
- `文明能力描述` 输入框的回车行为调整：
  - 按回车将直接插入文本 `[NEWLINE]`。
  - 不再在编辑框中插入真实换行。

### 兼容说明
- 旧数据中若存在真实换行，加载到该输入框时会统一转换为 `[NEWLINE]` 显示。

## 2026-02-14 - 5.4.0-alpha.7-hotfix.6（文明名字联动仅首字符问题修复）

### 问题表现
- 在文明子条目编辑器中，`文明描述` 与 `文明形容` 理应随 `文明名字` 连续联动更新。
- 实际表现为只在输入第一个字符时联动，后续字符不再跟随。

### 原因
- 自动填充描述/形容时触发了 `textChanged`，被误判为“用户手动编辑”。
- 手动标记被提前置位后，后续联动逻辑被锁定。

### 修复内容
- 在 `CivilizationItemEditor` 增加“自动填充保护标记”，区分程序写入与用户手动输入。
- 自动联动写入期间不再触发手动锁定。
- 描述后缀变化时同样应用该保护逻辑，确保行为一致。

## 2026-02-14 - 5.4.0-alpha.7-hotfix.5（文本预览迁移到文本工作区）

### 本次调整
- 按工作区职责划分，`Text.sql / Text.xml` 预览已从“文明分组预览页”迁移到 `工作区 -> 文本` 节点。
- “文明分组页”现在仅保留数据文件预览（如 `Civilizations.sql/xml`）。
- `工作区 -> 文本` 新增独立 SQL/XML 按钮与预览区域，点击即刷新。

### 说明
- 该调整避免了“同一类文本预览分散在业务分组页”的混用问题，文本预览入口统一到文本工作区。

## 2026-02-14 - 5.4.0-alpha.7-hotfix.4（文明预览SQL/XML与文本预览双区接入）

### 本次修复
- `工作区 -> 文明分组` 预览从占位改为真实生成：
  - 数据文件预览支持 `SQL预览 / XML预览`。
  - 文本文件预览支持 `SQL预览 / XML预览`。
- 文明数据 SQL 预览按当前工作区文明条目动态生成，包含：
  - `Types`
  - `Traits`
  - `Civilizations`
  - `CivilizationTraits`
  - `CityNames`
  - `CivilizationCitizenNames`
  - `StartBiasFeatures / StartBiasTerrains / StartBiasResources / StartBiasRivers`
- 文本 SQL 预览按当前文明条目动态生成 `LocalizedText`（`zh_Hans_CN`）内容。
- XML 预览改为“由当前 SQL 预览直接转换并格式化输出（GameInfo/Row 结构）”，与 SQL 内容保持一致。

### 交互说明
- 预览区域拆分为“数据文件预览”和“文本文件预览”两块。
- 每块都具备独立的 `SQL/XML` 按钮和独立预览区。
- 点击按钮立即刷新对应预览内容。

## 2026-02-14 - 5.4.0-alpha.7-hotfix.3（DLC导入默认路径自动探测）

### 本次修复
- `设置 -> 导入DLC` 现在会自动尝试定位默认目录：
  - `\SteamLibrary\steamapps\common\Sid Meier's Civilization VI\DLC`
- 仅当该路径在某个磁盘上实际存在时，才作为导入对话框起始目录。
- 若未找到该目录，则保持原有行为（不强制默认路径）。

### 说明
- DLC 安装位置并不固定，本次实现按“可探测即使用，探测不到不影响手动选择”的策略处理。

## 2026-02-14 - 5.4.0-alpha.7-hotfix.2（文本XML导入Replace节点修复）

### 问题原因
- XML 解析逻辑此前仅在 `Tag` 缺失时才读取子节点字段。
- 对于常见结构 `<Replace Tag="..." Language="zh_Hans_CN"><Text>...</Text></Replace>`：
  - `Tag/Language` 在属性上已存在
  - 子节点 `<Text>` 未被读取
  - 结果导致该条目文本未正确导入（会表现为缺失或空值）

### 修复内容
- `ModTools_5_4/db/text_database.py`：
  - XML 解析改为始终尝试读取子节点 `Tag/Language/Text` 的补充值（不再受 `Tag` 是否缺失限制）。
  - 对解析出的空文本记录直接跳过，避免导入时误覆盖已有文本。

### 使用建议
- 修复后请对受影响文本文件重新执行一次导入。
- 若历史导入已把部分 Tag 覆盖为空，重新导入可恢复正确中文值。

## 2026-02-14 - 5.4.0-alpha.7-hotfix.1（启动缩进报错修复）

### 本次修复
- 修复 `ModTools_5_4/ui/pages/group_workspace.py` 中 `_fetch_random_city_pool_zh()` 的缩进错误。
- 该问题会导致启动时报错：`IndentationError: unexpected indent`。
- 现在可正常完成模块导入并继续启动流程。

### 备注
- 按要求：本次小修改也已记录更新日志。

## 2026-02-14 - 5.4.0-alpha.7（文明编辑区规则修复与城市/市民重构）

### 规则修复
- `完整Type` 拼接规则修正：
  - 前缀为空时，不输出前缀段。
  - 中缀为 `0` 时，不输出 `Cxxxx` 段。
  - 自动处理下划线连接，避免多余 `_`。
- 示例：前缀空 + 中缀 `0` + 简称 `ABC` -> `CIVILIZATION_ABC`。

### 按钮样式优化
- 分组页与子文明页的 `新增/删除/导入/随机/展开折叠` 等操作按钮统一改为小尺寸样式：
  - 更小的高度与内边距
  - 匹配更紧凑的字体尺寸
  - 降低视觉压迫感，提升密集编辑区可读性

### 城市/市民区域重构（对齐参考逻辑）
- 城市与市民三种模式（现有文明 / 自定义 / 随机）重构为表格化交互：
  - 现有文明：从游戏数据库读取文明并联动加载城市/市民。
  - 自定义：数量控制 + 展开/折叠 + 表格逐行编辑。
  - 随机：按数量从随机池抽样并填充表格。
- 市民表格包含三列：`市民名字`、`女性`、`现代`（布尔勾选）。
- 城市与市民自定义表格支持：
  - 回车跳到下一行
  - 多行粘贴按换行逐行写入
  - 连续换行保留为空行（一个换行对应下一行）
- 序列化与反序列化已迁移为表格结构，并兼容旧版 `*_text` 字段恢复。

### 本次补丁（alpha.7 后续修订）
- UI 宽度自适应增强：
  - 城市/市民双列表格列宽随窗口宽度伸缩，避免内容在窗口变宽后仍挤压显示。
  - 城市市民区域位置调整到“出生点信息区域”下方，整体阅读顺序更清晰。
- 城市/市民名字表格高度自适应：
  - 按行数自动增高，行数越多显示越高。
  - 关闭表格内部纵向滚动，交由外层整体滚动承接。
- 文本接口新增：
  - `ModTools_5_4/db/interface.py` 增加 `get_chinese_text_for_tag_or_unknown()`。
  - 当解析结果仍为 `LOC_XXX` 或缺失文本时返回“未知”。
  - 原 `get_chinese_text_for_tag()` 保留不变，兼容旧逻辑。
- 选项优先级新增规则：
  - 中文显示为“未知”的选项自动降级到最低优先级（排在列表末尾）。

## 2026-02-14 - 5.4.0-alpha.6（文明分组编辑区首版接入）

### 本次实现
- 新增 `ModTools_5_4/ui/pages/group_workspace.py`，接入“分组编辑区 + 子条目编辑区”框架。
- 点击 `文明/领袖/区域/建筑/单位/改良设施/...` 分组后，进入统一编辑页：
  - 按钮：`新增{分类}`
  - 预览：`SQL预览` / `XML预览`（二选一）
  - 预览文本分页：`{SectionName}.sql` 或 `{SectionName}.xml`
  - 进入分组时自动刷新预览（当前为占位内容，生成逻辑后续接入）
- 非 `文明/领袖` 分类显示 `导入{分类}` 按钮（逻辑暂留空，先保留入口）。

### 文明子条目编辑区（已实现）
- 新增文明后自动创建子条目，默认命名：`新文明1/2/...`。
- 子文明编辑区包含三大区域：
  - 基础信息区域
  - 城市市民信息区域（现有文明/自定义/随机模式三种结构）
  - 出生点信息区域
- 基础信息能力：
  - `简称`（仅英文/数字/下划线）
  - `完整Type` 自动联动：`CIVILIZATION_{前缀}_C{中缀4位}_{简称}`
  - 文明名字/描述/形容 + LOC 补充说明自动更新
  - 描述后缀下拉（帝国/王国/共和国/城邦）
  - 文明等级、种族、随机城市名深度
  - 文明能力名字、文明能力描述（多行，导出自动替换换行为 `[NEWLINE]`）
- Trait绑定区域：新增/删除按钮与列表高度自适应已接入；跨分类选择逻辑按计划后续补充。
- 出生点信息区域：
  - 开局绑定地形（`terrain`）
  - 开局绑定地貌（`feature_passable`）
  - 开局绑定资源（`resource_search`）
  - 每行含选择控件 + 绑定等级（1~5）+ 删除按钮
  - 新增“开局绑定河流”与绑定等级

### 工作区联动
- `ModTools_5_4/ui/pages/workspace_page.py` 已接入分组/子条目面板，并实现子条目改动实时回写。
- 修正子条目编辑时的树刷新策略，避免输入过程中因重建树导致焦点中断。

### UI控件库补充
- `ModTools_5_4/ui/ui_widget_kit.py` 新增 `NewlineTokenTextEdit`，用于多行文本与 `[NEWLINE]` 标记互转。

## 2026-02-14 - 5.4.0-alpha.5（基础信息页整体滚动修复）

### 本次修复
- `ModTools_5_4/ui/pages/basic_info_workspace.py` 的“基础信息”页面改为外层整体滚动容器（`QScrollArea`）。
- 保留并兼容现有 `FrontEndActionData / InGameActionData` 的内容自适应高度逻辑。
- 当窗口高度不足时，页面可整体纵向滚动，不再出现底部内容被截断或必须依赖局部滚动才能访问的问题。
- 基础信息区域新增只读参数“文件名”（位于 `ID` 下方），值取 `.civ6proj` 文件主名（例如 `Siqi_Leaders_0030`）。
- “前缀 / 中缀 / 文件名”已统一为工作区共享参数，后续文明、领袖等编辑工作区可直接读取使用。

### 设计说明（整体滚动区域的必要性）
- `InGameActionData` 在真实项目中通常动作数量更多、文件列表更长，页面总高度天然高于常见窗口可视区。
- 若只依赖局部控件滚动，会造成“多层滚动”与信息分割，编辑路径不连续，操作成本明显升高。
- 采用“外层统一滚动 + 局部内容自适应高度”的结构，能保证信息连续可读、交互一致，也更符合工作区编辑器的长期可扩展需求。
- 通用布局原则补充：当一个大区域包含多个小区域时，大区域应保持自适应高度，不设置固定高度上限；由外层统一滚动承接超出视口的内容。

## 2026-02-12 - 5.4.0-alpha.4（按原版逻辑复制控件与DEBUG UI测试区）

### 本次目标
- 取消改编型 `ui_widget_kit.py`，回到你要求的 `common_widgets` 使用逻辑。
- 将 DEBUG 页的 UI控件测试区重写为 `ModifiersTool` 同类布局与交互。

### ui_widget_kit.py 重置
- `ModTools_5_4/ui/ui_widget_kit.py` 现为直接映射 `common_widgets` 风格接口：
  - `BaseTemplateWidget`
  - `UITemplateSpec`
  - `TEMPLATE_SPECS`
  - `build_template_widget(key)`
- 按你给定清单完整替换模板集合：
  - 数据下拉选择：`feature_passable`、`feature_all`、`terrain`、`era`、`resource_strategic`、`plunder_type`、`cost_progression`、`domain`、`yield`、`great_person_class`、`advisor_type`、`resource_class`
  - 搜索弹窗选择：`resource_search`、`district_search`、`district_search_no_trait`、`building_search`、`building_search_all`、`building_search_no_trait`、`unit_search`、`unit_search_no_trait`、`improvement_search`、`technology_search`、`civic_search`
- 控件实现直接复用 `ModifiersTool.ui.common_widgets` 对应类，保持“搜索按钮 -> 弹窗 -> 选择”的原始体验。

### DEBUG 页面 UI控件测试区重写
- `ModTools_5_4/ui/pages/debug_page.py` 的 UI测试区改为参照 `ModifiersTool` 的结构：
  - 模版选择添加区
  - 实例列表区（可删除）
  - 拖拽预览画布
  - 模版数据表
- 新增/恢复核心类：
  - `UITemplateBadge`
  - `CanvasWidget`
  - `MoveHandleButton`
  - `DraggableResizableCard`
  - `UITestManager`

### 兼容说明
- 文本数据库测试区与游戏数据库测试区功能保持不变。
- 这次调整重点是“回到你熟悉的控件与调试交互”，避免继续偏离原方案。

### 独立化与拖拽区高度修正
- 按你的新要求，`ModTools_5_4/ui/ui_widget_kit.py` 已改为本地完整实现（直接复制入 5.4），不再通过 `from ModifiersTool...` 调用。
- 为了支持该文件中的本地化查询，新增 `ModTools_5_4/db/interface.py`，提供 `get_chinese_text_for_tag()`（仅 `zh_Hans_CN`）。
- DEBUG 页面 UI测试拖拽区高度上调：
  - `CanvasWidget.BASE_MIN_HEIGHT` 从 `320` 提升到 `560`
  - 拖拽区滚动容器最小高度设为 `560`
- 现在默认可同时展示至少 3 个卡片高度，减少频繁滚动。

## 2026-02-12 - 5.4.0-alpha.3（设置页与文本数据库导入框架）

### 本次目标
- 完成设置页面基础能力，对齐你提出的数据库配置与导入流程。
- 打通“多文本数据库配置 + 记忆上次链接 + 导入中文文本 + 冲突处理 + Tag 查询接口”。
- 新增 DEBUG 页面分区，先落地文本数据库测试能力。

### 设置页重构（参考 5.0 数据库配置思路）
- `ModTools_5_4/ui/pages/settings_page.py` 由占位页重构为真实配置页，包含：
  - 游戏数据库（外部链接）路径配置。
  - 文本数据库（本地）多库配置与切换。
  - 基础文本数据库路径配置（默认可指向 `DebugLocalization.sqlite`）。
  - 四个导入按钮：`导入DLC`、`导入文本文件`、`导入.modinfo`、`导入文件夹`。
- 当未选择当前文本数据库时：
  - 四个导入按钮自动禁用。
  - 显示悬浮说明“请选择当前文本数据库后才可导入”。

### 配置持久化（记住上一次链接文本库）
- 新增 `ModTools_5_4/app/settings_store.py`：
  - 配置文件位置：`ModTools_5_4/data/settings.json`。
  - 持久化内容：
    - `game_db_path`
    - `base_text_source_db_path`
    - `text_databases`（多文本库列表）
    - `active_text_db_path`（上次选中的文本库）
- 应用重新启动后会恢复上次选中的文本数据库。

### 文本数据库核心能力
- 新增 `ModTools_5_4/db/text_database.py`：
  - `create_local_text_database_from_source()`
    - 以基础文本库为源，新建本地 `.sqlite` 文本库。
    - 仅复制中文语言（`zh*`）文本，减少空间占用。
  - 导入能力：
    - `import_dlc_texts()`
    - `import_text_files()`
    - `import_modinfo_texts()`
    - `import_folder_texts()`
  - `.modinfo` 支持：
    - 读取 `<UpdateText><File>...</File></UpdateText>` 相对路径。
    - 基于 `.modinfo` 所在目录解析并导入实际文件。
  - SQL 读取策略：
    - 忽略 `UPDATE` 语句。
    - 兼容 `INSERT INTO` / `INSERT OR REPLACE INTO` / `REPLACE INTO` 风格。
    - 不修改源文件。
  - XML 读取策略：
    - 使用 XML 结构读取，尽量不依赖具体排版风格。
    - 仅收集中文语言节点。
    - `<Text>` 中换行符会被清理，不写入数据库。

### 文本冲突处理
- 新增 `ModTools_5_4/ui/dialogs/conflict_file_dialog.py`：
  - 冲突时弹窗列出相关文件，支持全选/全不选/部分选择。
  - 选择文件才覆盖冲突 Tag；未选择文件的冲突 Tag 被忽略。
  - 未冲突内容仍会继续导入。
- 冲突判定覆盖两类：
  - 与当前文本数据库已有 Tag 冲突。
  - 本次导入文件之间互相 Tag 冲突。

### Debug 页面
- 新增 `ModTools_5_4/ui/pages/debug_page.py` 并接入主窗口导航。
- 分区结构：
  - 文本数据库测试区（已可用）
  - 游戏数据库测试区（已支持 SELECT 查询）
  - UI控件测试区（已支持控件实例化与参数记录）
- 已实现“通过 Tag 获取文本”：
  - 如果文本中包含 `{LOC_XXX}`，会递归替换为对应文本。
  - 若数据库中不存在目标 Tag，则返回 Tag 本身。
- 游戏数据库测试区新增：
  - SQL 输入框（仅允许 `SELECT` 开头语句）。
  - “填充示例”按钮，默认示例：`SELECT Type, Name FROM Units LIMIT 10;`
  - “执行 SELECT”按钮，查询结果以表格展示并给出返回行数。
  - 查询失败会显示错误信息，数据库路径来自设置页中的游戏数据库配置。

### 新增：重写版 UI 控件辅助模块（替代旧结构思路）
- 新建 `ModTools_5_4/ui/ui_widget_kit.py`，采用 `Spec + 工厂 + 参数导出` 架构：
  - `WidgetSpec`：控件定义（key/title/参数模式/字段集合）
  - `FieldSpec`：字段定义（参数键、编辑器类型、选项来源）
  - `ParameterWidget`：按规格动态生成控件并导出参数
  - `list_widget_specs()` / `create_parameter_widget()`：快速使用入口
- 文件顶部新增完整使用说明，便于后续页面快速接入。

### 单参数 / 多参数控件
- 单参数示例（参数模式：`single`）：
  - 区域选择框（`district_type`）
  - 建筑选择框（`building_type`）
  - 单位选择框（`unit_type`）
  - 地形选择框（`terrain_type`）
  - 改良设施选择框（`improvement_type`）
- 多参数示例（参数模式：`multi`）：
  - 成本增长组合控件：
    - `cost_progression_model`（成本增长模型）
    - `cost_progression_scale`（成本增长系数）

### 数据来源策略（按你的要求）
- 大部分控件选项改为动态读取游戏数据库：
  - `Districts / Buildings / Units / Terrains / Improvements`
- 中文仅作展示标签，导出值始终为英文标识（Type/枚举值）。
- 少量特定控件使用静态枚举（如成本增长模型）。

### DEBUG 的 UI 控件测试区升级
- 可在下拉框选择预设控件规格并“新增控件”实例。
- 支持新增多个实例、移除单个实例。
- 支持“刷新参数记录”，并实时展示所有实例的导出 JSON（英文参数键值）。
- 控件参数变化会自动刷新记录，便于快速验证字段输出。

### DEBUG UI控件区重置（参考 ModTools 5.0 结构）
- 根据你的反馈，已将 5.4 的 UI控件测试区重置为更接近 5.0 的管理方式：
  - 左侧“实例列表（编号+类型+删除）”
  - 中部“控件实例展示区”
  - 下方“参数表格（编号/控件/参数JSON）”
- 新增 `WidgetTestManager` 统一管理实例生命周期、编号复用、参数表刷新。
- 新增 `WidgetInstanceBadge` 作为实例清单行组件，支持快速删除。
- 保留新控件系统 `ui_widget_kit.py` 的能力，但 DEBUG 展示改为 5.0 风格的“管理器 + 表格”交互，而非纯日志文本区域。

### ui_widget_kit 回退为 common_widgets 风格（按要求重置）
  - `UITemplateSpec` / `TEMPLATE_SPECS`（模板注册）
  - `build_template_widget(key)`（工厂创建）
- 按你的要求，文本语言过滤从“所有 zh 前缀”改为“仅 `zh_Hans_CN`”：
  - `ModTools_5_4/db/text_database.py`
    - 导入判定 `_is_chinese_language()` 仅接受 `zh_Hans_CN`（大小写不敏感）
    - 新建文本库时仅复制 `zh_Hans_CN` 行
    - 导入写入时统一标准化为 `zh_Hans_CN`
    - `query_text_by_tag()` 优先查询 `zh_Hans_CN`
  - `ModTools_5_4/ui/ui_widget_kit.py`
    - 文本映射读取仅查询 `Language = zh_Hans_CN`
- 这样可避免繁体中文被读入或展示。
  - `dataChanged` + `export_data()`（统一导出行为）
- DEBUG 页面同步改为使用上述接口（不再依赖上一版 `create_parameter_widget/list_widget_specs/ParameterWidget`）。
- 保留“多数控件从游戏数据库动态读取”的原则，并保留一个多参数控件 `cost_bundle`。

### 主窗口调整
- `ModTools_5_4/ui/main_window.py` 增加 DEBUG 页面入口（窗口菜单）。

### 当前边界说明
- 本次重点是设置与导入基础架构，未实现分类业务编辑器。
- 游戏数据库测试区/UI控件测试区仅完成分区占位，后续继续扩展。

## 2026-02-12 - 5.4.0-alpha.2（工作区与工程文件基础架构重构）

### 重构目标
- 把“工作区”升级为 5.4 的核心：左侧工程树 + 右侧工作区内容。
- 引入 `.CIV` 工程文件格式（文件后缀为 `.CIV`，内容本质为 JSON）。
- 明确工程结构节点与 UI 行为，先打通框架，具体字段后续迭代。

### 新增：工程文件域模型
- 新建 `ModTools_5_4/project/civ_project.py`，定义了：
  - 工程后缀：`.CIV`
  - 基础 schema 版本：`0.1.0`
  - 固定节点顺序：
    - 基础信息，文明，领袖，区域，建筑，单位，改良设施，总督，伟人，政策卡，项目，信仰，议程，美术，文本，修改器
  - 直接工作区节点：`基础信息`、`美术`、`文本`、`修改器`
  - 子条目组节点：其余分类（文明/领袖/区域/.../议程）
- 新增 `CivProject` 数据类与 `create_empty_project/load_civ_project/save_civ_project`。
- `.CIV` 文件读写约束：
  - 后缀必须为 `.CIV`
  - 内容读取为 JSON 对象
  - 自动标准化缺失节点（直接节点 -> `{}`，子条目组 -> `[]`）

### 重构：工作区 UI（核心）
- `ModTools_5_4/ui/pages/workspace_page.py` 从占位页重构为双栏工作区：
  - 左侧：`QTreeWidget` 工程树
  - 右侧：工作区标题 + 说明 + 当前路径
- 树结构逻辑：
  - 根节点显示当前工程名（未保存时显示 `工程名.CIV`）
  - 分类节点按固定顺序加载
  - 直接工作区分类可直接切换右侧工作区
  - 子条目组可展开子条目（数量不定，可为 0）
  - 选择子条目后切换到右侧工作区占位内容
- 新增工作区能力方法：
  - `create_new_project()`
  - `load_project()`
  - `save_project()`

### 重构：主窗口菜单动作接线
- `ModTools_5_4/ui/main_window.py` 文件菜单从占位动作改为可用动作：
  - 新建工程：输入工程名 -> 创建空工程
  - 打开工程：选择 `.CIV` -> 加载工程并刷新左树
  - 保存工程：首次弹保存对话框，后续直接覆盖保存
- 保存/打开失败时显示错误对话框。

### 样式更新
- `ModTools_5_4/resources/styles/base.qss` 新增工作区样式：
  - 左侧工程树边框与选中态
  - 右侧路径信息标签样式

### 当前阶段明确边界
- 已完成：工程文件容器、树结构导航、工作区切换框架。
- 未完成：各分类具体编辑字段、增删子条目交互、导出与校验逻辑。

### 后续接口预留说明
- 子条目命名当前使用 `name`/`id` 字段兜底，后续可按分类扩展显示策略。
- 工程 schema 允许后续逐步扩充，不破坏当前 UI 框架。

## 2026-02-12 - 5.4.0-alpha.1（基础架构阶段）

### 本次目标
- 启动全新的 ModTools 5.4 工程骨架。
- 明确“先 UI 架构、后功能接入”的路线。
- 丢弃旧数据实现，仅保留可扩展的界面结构参考（学习 ModTools 5.0 的布局思路）。

### 目录结构新增
- 新建 `ModTools_5_4/` 包目录，作为 5.4 独立代码基线。
- 新建分层目录：
  - `ModTools_5_4/app/`（应用启动、配置、日志）
  - `ModTools_5_4/ui/`（主窗口、主题、页面）
  - `ModTools_5_4/ui/pages/`（分页面容器）
  - `ModTools_5_4/resources/styles/`（QSS 样式资源）
  - `ModTools_5_4/docs/`（后续开发协作文档）
  - `ModTools_5_4/logs/`（运行日志输出目录）

### 核心文件新增
- `ModTools_5_4/app/config.py`
  - 新增 `AppConfig` 配置对象。
  - 定义窗口最小尺寸、标题、日志目录、调试开关。
  - 支持环境变量 `MODTOOLS54_DEBUG`。
- `ModTools_5_4/app/logging_setup.py`
  - 建立控制台 + 文件双通道日志。
  - 默认写入 `ModTools_5_4/logs/modtools_5_4.log`。
- `ModTools_5_4/app/application.py`
  - 提供 `build_application()` 与 `launch()` 统一启动入口。
- `ModTools_5_4/ui/main_window.py`
  - 搭建 `QMainWindow + QStackedWidget` 页面壳。
  - 实现基础菜单：文件 / 窗口 / 关于。
  - 实现页面切换与状态栏反馈。
- `ModTools_5_4/ui/theme.py`
  - 集中加载基础 QSS，便于后续统一主题扩展。
- `ModTools_5_4/ui/pages/*.py`
  - 新增 `HomePage/WorkspacePage/SearchPage/SettingsPage`。
  - 目前均为功能容器，不接业务数据。
- `ModTools_5_4/resources/styles/base.qss`
  - 建立 5.4 第一版主题基线（简洁卡片按钮 + 菜单栏 + 状态栏）。

### 入口与兼容性处理
- 更新根入口脚本 `ModTools5.4.py`：
  - 由空文件改为 5.4 GUI 启动器。
  - 统一调用 `ModTools_5_4.app.application.launch()`。

### UI 设计基线（参考 5.0）
- 采用和 5.0 相同的核心组织方式：
  - 顶层主窗口 `MainWindow`
  - 菜单驱动导航
  - 多页面栈（`QStackedWidget`）
- 保留“主页快速入口”交互习惯，简化首屏流程。
- 暂不引入任何旧版数据表、缓存、导入器或数据库依赖。

### 明确不做（本阶段）
- 不迁移旧数据逻辑。
- 不导入旧缓存格式。
- 不实现编辑器字段、导出 SQL/XML、批量导入等业务能力。

### 下一阶段建议（已记录到 docs）
- 阶段 2：页面布局定型（左栏导航 + 中央编辑器 + 右栏预览）。
- 阶段 3：定义领域模型与事件流（不绑定旧数据结构）。
- 阶段 4：逐模块接入功能（Types / Modifiers / Artdef）。
- 阶段 5：导出、校验、打包与回归测试。
