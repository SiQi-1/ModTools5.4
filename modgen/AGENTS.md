# modgen —— 文明6 Mod 工程(.CIV) 生成与校验工具

> **本文件是 AI Agent 的必读说明**。使用本目录的工具生成/校验 .CIV 工程前，请先完整阅读。
>
> 制作规则见 [RULES](../skills/RULES.md)，执行顺序见 [统一工作流](../skills/WORKFLOW.md)。本文件只维护命令与字段契约；工具开发见 [CLAUDE](../CLAUDE.md)。

## 本工具是什么

生成"合规的文明6 Mod 工程条目"（.CIV 工作区结构），而不是直接生成 SQL/XML。
规则来自 ModTools 5.4 编辑器（GUI）——工具生成的条目保证编辑器能打开、能正确导出。

- **不依赖** PyQt6 / GUI 的数据与 extension 命令为纯标准库；preview / check-conflicts / project-check / build 使用 GUI 生成引擎，需 PyQt
- **Type 永远由工具生成**，AI 不要手写 Type（详见"硬规则"）
- 中文文本存条目（name/Description 等），LOC tag 由导出约定自动注册，条目里不写 LOC

## 用法

```bash
# 创建工程级骨架（基础信息/美术/修改器/文本 结构就位，替代手工拷贝旧工程）
python -m modgen.cli new-project <输出.CIV> --name 中文工程名 --prefix 前缀 --infix 编号 [--file-name 文件名基名]

# 生成一个合规条目（JSON 输出到 stdout）
python -m modgen.cli generate <分类> --name 中文名 --abbr 英文简称 [--prefix 前缀] [--infix 编号] [--desc 描述]

# 校验条目文件或整个工程
python -m modgen.cli validate 工程.CIV [--prefix 前缀] [--infix 编号]
python -m modgen.cli validate --section 分类 --entry entry.json [--prefix 前缀] [--infix 编号]

# 合并条目进工程（同 type 去重，自动备份 .bak）
python -m modgen.cli merge 工程.CIV <分类> --entry entry.json [--prefix 前缀] [--infix 编号]
# 合并修改器条目进工程（modifier/requirement/reqset/ability/owner 自动识别，合并后整体校验）
python -m modgen.cli merge 工程.CIV 修改器 --entry modifier.json [--kind modifier|requirement|requirement_set|unit_ability|owner]

# 生成 ModBuddy 兼容 .civ6proj 工程（+ 空白 Art.xml，无需 ModBuddy 新建工程）
python -m modgen.cli civ6proj 工程.CIV [--out 目录] [--update-civ]

# 项目级扩展：.CIV 保存清单；源码在 工程.extensions/，无须先绑定输出
python -m modgen.cli extension init 工程.CIV --gameplay --ui
python -m modgen.cli extension write 工程.CIV --core --content-file modgen_work/Core.sql
python -m modgen.cli extension write 工程.CIV --path Scripts/My.lua --role gameplay --feature events --depends-on core --content-file modgen_work/My.lua
python -m modgen.cli extension list 工程.CIV --json
python -m modgen.cli extension check 工程.CIV --json
python -m modgen.cli extension import 工程.CIV --path Scripts/Old.lua --role gameplay
python -m modgen.cli extension remove 工程.CIV --path Scripts/Old.lua
python -m modgen.cli project-check 工程.CIV --json
python -m modgen.cli build 工程.CIV --overwrite all --json

# 自定义文件通道：有扩展清单时写源码目录，旧工程写绑定的输出目录（--action 可显式指定，旧工程可用 --no-action 跳过）
python -m modgen.cli custom-file write 工程.CIV --path Scripts/My.lua --content-file modgen_work/My.lua
python -m modgen.cli custom-file write 工程.CIV --path Data/Extra.sql --content "INSERT INTO ..."
python -m modgen.cli custom-file list 工程.CIV
python -m modgen.cli custom-file remove 工程.CIV --path Scripts/My.lua [--keep-file]
python -m modgen.cli check-conflicts 工程.CIV [--json]                          # 自定义 SQL × 生成 SQL 冲突检测

# 修改器四类生成（EffectType/RequirementType 存在性与参数骨架自动处理）
python -m modgen.cli generate-modifier --effect EFFECT_XXX --collection COLLECTION_XXX --desc 效果描述 [--params '{"Amount":2,"YieldType":"YIELD_PRODUCTION"}']
python -m modgen.cli generate-requirement --type REQUIREMENT_XXX --desc 条件描述 [--params '{"...":...}']
python -m modgen.cli generate-reqset --desc 集合描述 --logic ALL [--requirements '["REQUIREMENT_A"]']
python -m modgen.cli generate-ability --abbr 简称 [--name 中文名] [--desc 中文描述]

# 知识/验证工具
python -m modgen.cli skill <关键词> [--file 相对路径]                                     # 本地技能库（仓库根 skills/）全文检索
python -m modgen.cli query "SELECT ModifierType, CollectionType FROM DynamicModifiers LIMIT 10"  # 游戏库只读查询
python -m modgen.cli loc LOC_TRAIT_XXX_NAME                                                 # LOC → 简体中文
python -m modgen.cli preview 工程.CIV [--dry-run | --out 目录]                               # 无头预览将导出的全部文件
python -m modgen.cli preview 工程.CIV --section 分类 [--format sql|xml]                      # 单分类输出文本
python -m modgen.cli preview 工程.CIV --section UI图标                                        # 自定义 UI 图标 → Icons.xml

# 原版 ModifierType 快照（自定义类型注册判定用；随包分发，缺失时回退旧启发式）
python -m modgen.tools.extract_vanilla_modifier_types [--game-dir 目录] [--out 路径] [--json]
```

`--prefix`/`--infix` 来自工程"基础信息"（前缀如 SIQI、中缀编号如 35）。

## 必须遵守的工作流

先读 [规则正文](../skills/RULES.md) 与 [统一工作流](../skills/WORKFLOW.md)，执行 `skill "任务描述" --plan` 并读取相关章节。先核实依据，再 new-project / generate / validate / merge；已有工程只修改目标内容。扩展任务执行 project-check / build；旧自定义 SQL 用 check-conflicts，预览、工程导出、部署和实机分别验收。

## 导出与部署（GUI 一键按钮 → AI 控制接口）

- 导出文件需 .civ6proj 定位输出目录：**`modgen civ6proj 工程.CIV --update-civ`** 直接生成
  ModBuddy 兼容工程文件（+ 空白 Art.xml，默认 `文档/Firaxis ModBuddy/Civilization VI/<文件名>/`），
  并把路径回写进 .CIV 基础信息——**不需要 ModBuddy 新建工程**（生成物 ModBuddy 仍可打开/构建）。
- GUI 的一键按钮（一键生成/一键配置/导入等）可通过 **AI 控制接口**驱动：
  启动 `python ModTools5.4.py 工程.CIV --ai-port 8765` 后用 HTTP 调用动作
  （get_state/get_manifest/generate_all/quick_config/import_from_db/project_file_write/…），
  协议与动作表见 `ModTools_5_4/docs/AI_CONTROL_API.md`；
  一次性执行：`--ai-exec '{"action":"generate_all","params":{"overwrite":"all"}}'`。
- 自定义 SQL/XML/Lua：`custom-file write` 或 AI 接口 `project_file_write`（自动注册文件动作）。
- 部署进游戏仍需 .modinfo：本期工具不生成（ModBuddy Build 时产物），文本类 Mod 可手写模板。

## 本地 Mod 工程与临时文件约定（必须遵守）

遵守 [R4 仓库边界](../skills/RULES.md#r4-数据与写入边界)，具体目录与 Git 验收步骤见 [统一工作流](../skills/WORKFLOW.md)。

- 新 Mod 工程及专用工作文件默认集中在 `modgen_work/<工程名>/`，已有工程位置保持不变；`.CIV` 和同级 `*.extensions/` 由仓库忽略，源码仍需保留和备份。
- **所有临时条目、Mod 专用生成/修复脚本、专用测试、报告、预览和构建包一律写入 `modgen_work/` 目录**（仓库根下，已 gitignore，绝不提交到工具仓库）。通用工具回归测试仍放 `tests/` 或 `modgen/tests/`。
- 不要在任何其他位置留下生成中间文件（工程目录、仓库根、modgen/ 内）。
- `generate` 输出是 stdout——能直接消费就不要落盘；必须落盘时用 `modgen_work/`。
- merge 会在工程旁生成 `.CIV.bak`（自动备份，已 gitignore，下次覆盖）。

## 硬规则（生成/校验的依据）

- **Type 命名**：`{HEAD}_{前缀}_{中缀}{编号:04d}_{简称}`（如 `CIVILIZATION_SIQI_C0035_1`）。
  生成器按简称自动生成，AI 手写 type 会被 validate 警告/报错。
- **必填字段**：条目必须有 `name`（中文名）+ 分类标识（多数分类 `abbr`，总督用 `code`）。
  主表必填字段见 `schemas/entry_schemas.json` 中 `required` 字段；无默认值的必填字段（如单位 `FormationClass`）必须由 AI 填写。
- **LOC**：文本字段存中文，不写 `LOC_` 前缀 tag；导出时自动注册。
- **图片**：项目图标有图片槽（目标 **256×256**，`images.icon` 已预填尺寸骨架，AI 只需填 `path`）；信仰 `has_images=False`（GUI 无图片槽，图标经美术页别名/数据库处理，无需导入图片）；其余分类一律空 `images: {}`，路径由用户提供。
- **图标名**：约定 `ICON_{Type}`，由生成器自动填（如 `ICON_PROJECT_SIQI_P0035_TEST`）。
- **引用**：`bindings` / `trait_bindings` 中的 section/name 必须指向存在的对象。
- **议程绑定**：只用议程 `historical_agendas.LeaderType` 指定领袖；不要放入 `bindings` / `trait_bindings`。议程 Trait 通过 `AgendaTraits` 挂载，不进入 `LeaderTraits` / `CivilizationTraits`。校验会提示旧写法；导出兼容将旧领袖议程绑定转为 `HistoricalAgendas`，显式历史议程归属优先。
- **自定义文件**：新任务先启用 extension 清单，SQL/XML/Lua 正文通过 extension write 或 custom-file write / AI project_file_write 存到源码目录，生成时按清单注册并复制到输出。Scripts 用 gameplay；UI XML/Lua 配对，动作只引用 XML；Import 用 import；数据库、文本、图标分别声明 database/text/icons。旧工程未启用时保留按路径分类与输出目录透传。路径越界被拒绝。
- **自定义 SQL 协调**：默认把未被 .CIV 支持的 Gameplay SQL 放入 Core.sql；相同主键不得双写，UPDATE/DELETE 需明确依赖，不得机械替换成 REPLACE。
- **加载顺序**：扩展清单独立编译 MTX_ 动作，按作用域、前后阶段和依赖决定顺序。旧 custom-file 自动动作仍按 (type,id) 合并并保留旧顺序，不能只凭默认 10000 推断加载时机。完整契约见 [项目级扩展](../skills/05-modtools-civ/project-extensions.md)。
- **统一检查与生成**：project-check 组合数据、源码/依赖、预览、动作和 SQL 冲突；build 自动配置后检查、生成并保存动作，默认 overwrite=none，all 才覆盖已有输出。build 不调用 ModBuddy Build/Cooker，不部署。
- **兼容**：未启用 extensions 的旧 .CIV 不变。启用后 custom-file write 自动写源码；无动作文件不适用，Lua 库声明 import。CLI 修改备份 .CIV.bak；AI extension 修改自动保存。GUI/CLI/AI 共用 project/extensions.py。

## UnitAbility 显示文本

`generate-ability` 的 `--name` / `--desc` 均可省略，分别输出 `name_zh: null` / `description_zh: null`。原版 UnitAbilities 两列允许 NULL；内部标记、劳动力扣减等辅助能力无需显示名和说明。仅有玩家需要了解的独立效果才填写，内部能力同时关闭 `show_float_text_when_earned`。导出器保留 SQL NULL，且不生成对应空 LOC；名称或说明也可以只填其中一项。

## 分类说明

| 分类 | Type 前缀 | 标识键 | 备注 |
|---|---|---|---|
| 文明 | CIVILIZATION | abbr | trait_bindings 绑定特色对象 |
| 领袖 | LEADER | abbr | bindings 绑定所属文明等 |
| 区域 | DISTRICT | abbr | 主表 table_data + 子表 |
| 建筑 | BUILDING | abbr | 主表 table_data + 子表 |
| 单位 | UNIT | abbr | FormationClass 必填无默认 |
| 单位晋升 | PROMOTION_CLASS | type | 晋升树，nodes 列表 |
| 改良设施 | IMPROVEMENT | abbr | PlunderType 必填（默认 NO_PLUNDER） |
| 总督 | GOVERNOR | code | 顶层无 type，用 GovernorType |
| 伟人 | GREAT_PERSON_CLASS | (class_data) | 个体在 individuals |
| 政策卡 | POLICY | abbr | |
| 项目 | PROJECT | abbr | |
| 信仰 | BELIEF | abbr | |
| 议程 | AGENDA | (type) | 顶层无 abbr |
| **UI图标** | （无 Type） | icon_name | **非实体分节**：与游戏实体无关的自定义 UI 图标（新闻分类/单位动作/追踪器…），只出 `Icons.xml` 与 IMG/Textures，见下节 |

## 专项字段与规则（涉及时必读）

- [项目级扩展](../skills/05-modtools-civ/project-extensions.md)：清单完整字段、Core、GP/UI 配套、迁移、依赖和静态检查边界。
- [UI 美术与文本](../skills/05-modtools-civ/ui-assets.md)：UI图标、ui_textures、custom_entries 的完整字段与命令；包含 texture add/list/remove、覆盖策略、尺寸与动作要求。
- [修改器与类型来源](../skills/05-modtools-civ/modifiers.md)：生成器参数、原版快照、modifier_type_source、preview_text 与引用验证。

## HTML UI 纹理工具

配套可分享技能：[civ6-html-ui](../skills/civ6-html-ui/SKILL.md)，完整用法/依赖见 [通用入口](../skills/civ6-html-ui/references/portable-use.md)。正式来源随仓库发布，不依赖个人 agent 安装。

```bash
python -m modgen.cli texture render --html design/index.html --out design/textures
python -m modgen.cli texture import-manifest 工程.CIV --manifest design/textures/texture_manifest.json --dry-run
python -m modgen.cli texture import-manifest 工程.CIV --manifest design/textures/texture_manifest.json --replace
python -m modgen.cli texture verify --manifest design/textures/texture_manifest.json --project ModBuddy/MyMod
```

- `render`：本地 HTML 实现 textureSpecs/renderTexture；需 Node.js 22+ 与 Chromium/Chrome/Edge。`--node`/`--browser` 优先于 CIV6_UI_NODE/CIV6_UI_BROWSER，再查 PATH/常见浏览器路径；无 Codex 专用路径。`--replace` 才覆盖既有输出；不修改 CIV。
- `import-manifest`：标准库命令，清单格式 `{ "UI_MYMOD_PANEL": [640,400] }`，PNG 默认与清单同目录，可用 `--png-dir`。全批名称/重复/PNG 头/尺寸和合并结果校验后只保存一次，保留无关纹理与工作区；同名需 `--replace`，`--dry-run` 不写 CIV 或备份。源路径保存为绝对路径，不生成 DDS。
- `verify`：需 Pillow，只读检查源 PNG；加 `--project` 校验 DDS/TEX/UITexture XLP/Art.xml 及 alpha/可见像素。`--png-dir` 可覆盖源目录，`--tolerance` 为 0..255 最大单通道差，默认 0。不能代替 project-check 或实机验证。
- 三命令成功输出 JSON，失败非零退出；均不编译 XML、不自动翻译 HTML、不运行 ModBuddy/Cooker、不生成 modinfo 或部署。
- 现有 `texture add/list/remove` 契约不变；主数据、UI 扩展和完整生成仍分别走现有通道。

## 领袖外交表情差分

领袖条目可声明可选映射 fallback_images：键为外交状态，值为图片对象（path 必填，既有图片槽变换可选）。null / 空映射保留旧工程行为。DEFAULT 优先于 images.diplo_foreground，其余只导出明确提供的状态；有差分时必须有默认图。

只填 path 的新状态图按比例完整放入 960×960 透明画布；显式变换沿用图片槽规则。默认资源仍为 FALLBACK_NEUTRAL_<short_type>，其他状态为 FALLBACK_STATE_<STATE>__LEADER_<short_type>，避免 NEUTRAL 与默认资源冲突。状态、路径、资源名由 project/leader_fallbacks.py 统一；GUI、schema、CLI 校验与导出共享该模型。

validate 检查声明、状态、Type 和文件存在性，不加载 Qt/Pillow；GUI 生成前另检查图片可读性。完整生成会输出 PNG、DDS/TEX、LeaderFallback.xlp 和 FallbackLeaders.artdef。23 状态来自署名社区模板，其中 DECLAR_WAR_FROM_HUMAN 保留模板拼写，目标 SDK 和游戏触发仍需验收。字段例子与操作见 [领袖美术指南](../skills/05-modtools-civ/leader-art.md)。

## 资源与发布产物检查

~~~powershell
python -m modgen.cli assets check MyMod/MyMod.civ6proj --json
python -m modgen.cli audio check MyMod/MyMod.modinfo --json
python -m modgen.cli art compare MyMod/ArtDefs Cooked/ArtDefs --json
python -m modgen.cli workshop check workshop --modinfo MyMod.modinfo --json
~~~

- 四个入口只读、纯标准库，核心共用 project/asset_checks.py。与针对 .CIV 的 project-check 分开，不自动构建或上传。
- assets check：输入 .civ6proj / .modinfo；解析命名空间、内嵌动作 XML 和显式文件引用，检查资源 XML、模板残留、已知 Leader_Matte 槽及 LeaderFallback → XLP → TEX/DDS 链。IMG/Textures 不要求作为源工程 Content；外部 pantry 引用列入未验证项。
- assets check 可选 --cooker-config <Civ6.cfg>：只读加载目标 SDK 的注册表，分别核对 XLP/AST/GEO/TEX 类；校验 ASSET/TEXTURE XLP 的 ObjectName 对应资源是否属于 m_AllowedClasses，以及 AST 模型对应 GEO 是否属于 m_AllowedGeoClasses。ArtDef 与 AST 的 BLPEntryValue 都校验 EntryID。未知配置结构报错；缺配置、未支持实体类型或外部 pantry 对象明确未验证。未检查 FGX/BLP 内部数据及 pantry 优先级，不能将类关系通过等同于解包复原成功。
- audio check：同类工程输入；核对 UpdateAudio → INI → BNK、文件清单与可用 SoundBanksInfo 中的流式 WEM；INI 要求 ASCII 无 BOM，非 CRLF 提示。无 bank 元数据不能证明所有流式媒体完整。
- art compare：两个目录，默认比较 .artdef；可重复 --suffix 选择支持的资源 XML 后缀。忽略缩进/换行/注释和属性顺序，保留属性值、文本与子节点顺序；缺失、_MissingArt 和结构变化报错，并输出差异位置（最多 100 项）。
- workshop check：输入含 workshop.json、content 的 workspace；content 内需唯一 .modinfo，或 --modinfo 明确指定相对路径。检查 GUID、元数据类型、声明文件、动作引用、可选封面 PNG 头和既有条目 ID。dependencies 为 UInt64 整数列表；现有条目允许省略可选元数据。
- --json 报告包含 kind、target、ok、errors、warnings、unverified、checked；art 另有 comparisons。无静态错误退出 0，错误退出 1；警告/未验证不改变退出码。0 不代表 SDK 编译、游戏显示、Wwise 版本、Steam 所有权已经验证。
- 文件引用禁止绝对路径、越界和逃出输入根目录的链接；不修补源文件。Blender、Wwise、Cooker 和工坊上传器仍按各指南独立使用。

来源、版本及许可见 [第三方说明](../THIRD_PARTY_NOTICES.md)。

## 知识与证据查询

```powershell
python -m modgen.cli skill "任务描述" --plan --json
python -m modgen.cli skill "城市奇观相邻加成" --json
python -m modgen.cli skill --file RULES.md
python -m modgen.cli skill --file 05-modtools-civ/ui-assets.md --section "通道选择"
python -m modgen.cli skill --check --json
python -m modgen.cli search "城市产出"
python -m modgen.cli search --object 农场
python -m modgen.cli query "PRAGMA table_info(Units)" --json
python -m modgen.cli loc LOC_UNIT_WARRIOR_NAME
```

skill 只检索发布知识 Markdown，中文 bigram、英文词边界、章节 BM25 与规则/指南权重排序。旧 keyword / --file / --limit / --skills-dir 参数兼容；--plan 返回必读清单，--section 需配 --file，--check 返回质量问题并以非零状态退出，--json 输出结构化结果。未检索到不是能力不存在的证明。

search 查游戏库实现；query 只读 SELECT/WITH/PRAGMA/EXPLAIN，默认 50 行、最大 500；loc 查询已配置文本库。来源和不可用的历史资料说明见 [SOURCES](../skills/SOURCES.md)。

## 重新生成 schema

编辑器字段变化后，需重新提取 schema（需要 PyQt 环境）：

```bash
python modgen/tools/extract_schemas.py
```

## 地标 AST 与 Landmarks 资源包

本通道生成静态 TileBase，美术 XML/AST/XLP 由工具写出；不在 CIV 主内容手写 XML。共享核心是 `ModTools_5_4/project/landmarks.py`，CLI 是 `modgen/landmark.py`。完整制作技能：[civ6-landmarks](../skills/civ6-landmarks/SKILL.md)。

```powershell
python -m modgen.cli landmark catalog --sdk-assets "<SDK Assets>" --query Sphinx
python -m modgen.cli landmark compose --recipe recipe.json --sdk-assets "<SDK Assets>" --out MyMod.landmarks
python -m modgen.cli landmark import MyMod.CIV --bundle MyMod.landmarks/manifest.json [--dry-run] [--replace]
python -m modgen.cli landmark verify --bundle MyMod.landmarks/manifest.json [--sdk-assets "<SDK Assets>"] [--project "<工程目录>"]
python -m modgen.cli landmark cook --bundle MyMod.landmarks/manifest.json --sdk-assets "<SDK Assets>" --sdk "<SDK>" --out modgen_work/art-check [--project "<工程目录>"]
```

- 配方 schema 与字段见[工具契约](../skills/civ6-landmarks/references/workflow.md)；根 format=`MODTOOLS54_LANDMARK_RECIPE`。主内容 Type 必须先存在于 CIV，资产名与附件字段严格校验。
- `compose` 静态复用 SDK TileBase 的实例/材质组/可见状态，清除源附件和动画行为，再创建本地附件；不支持任意动画 AST 或单位骨骼转换。
- 配方可声明 local_pantry/local_files，纳管已经转换好的 AST/GEO/FGX/MTL/TEX/DDS；只复制清单文件，验证本地数据文件与材质贴图引用，二进制原样导出。该命令不执行 Blender/CN6 转换或处理动画。
- 区域 binding 可选 building_sets（建筑 Type 数组的数组），按已核对的前置/互斥与实际授予逻辑列可达阶段；必须含 []，无重复/未知项，每个声明建筑至少使用一次。生成器只输出这些集合；base_variants 不得引用被排除集合。顺序无关且输出稳定；省略/null 为旧配方保留全子集，新设计应显式填写。互斥建筑可共用资产与槽位，不假设异常授予来扩大模型组合。
- 区域 binding 可选 base_variants（buildings/asset 列表）：按完整建筑集合匹配，顺序无关、空数组代表空区域；未声明集合回退 base_asset。拒绝重复/未知建筑、重复集合和缺失资产。SDK 同名 GEO/MTL/TEX 仅在源及直接数据文件逐字节相同后合并，优先 Shared；同名 AST 仍需明确路径。
- 资源包含 AST、Landmarks、TileBase XLP、可选补充 Buildings、本地模型与材质贴图、recipe 与 manifest 散列。CIV 只存 `workspace.美术.data.landmark_bundle.manifest` 绝对路径；当前一个 CIV 一个包。
- `import` 校验完整批次后保存一次并备份 CIV，自动设置 need/source map、Landmarks/TileBase 标记与来源 SDK Art ID；不同包切换需 `--replace`。移动源目录后重新导入，当前不自动重定位。
- GUI 导入/导出保留声明；预览有 AST 组。工程总览允许 AST；生成 Assets 等标准美术源目录，但不登记为 civ6proj Content/Folder/None；更新既有工程时清除这些目录的旧注册，磁盘源文件保留，仍由目录扫描与 Cooker pantry 读取；补充建筑与已有 Buildings 合并。
- 包文件散列变化会阻断导出，调整应回到配方重新 compose；依赖或绑定变化后再次 import。`validate` 同时检查资源包来源存在且散列一致。
- `verify --project` 检查源文件、引用链和错误的美术源目录注册；不要求 AST Content。`verify` 不调用 SDK 二进制；`cook` 需要 Windows 官方 Cooker，使用新英文临时目录解决中文路径问题，只编译地标资源链。两者均不是游戏内视觉验收。
- Mod 源 `*.landmarks/` 与 CIV/扩展目录一起保留在本地或独立 Mod 仓库；通用示例和测试不包含官方几何/纹理文件。
