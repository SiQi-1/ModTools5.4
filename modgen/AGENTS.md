# modgen —— 文明6 Mod 工程(.CIV) 生成与校验工具

> **本文件是 AI Agent 的必读说明**。使用本目录的工具生成/校验 .CIV 工程前，请先完整阅读。
>
> **同源声明**：本文件的硬规则（ModifierType 优先引用游戏库已有类型 / JSON 禁止 `""` /
> 主内容不写 Lua，自定义 SQL/XML/Lua 仅走自定义文件通道）
> 与根目录 `AGENT.md` **同源一致，任一处为准**；作者规范与游戏知识细节见 `AGENT.md`。
> 任务分流见根目录 `AGENTS.md`；改 modgen 工具本身（工具优化向）见根目录 `CLAUDE.md`。

## 本工具是什么

生成"合规的文明6 Mod 工程条目"（.CIV 工作区结构），而不是直接生成 SQL/XML。
规则来自 ModTools 5.4 编辑器（GUI）——工具生成的条目保证编辑器能打开、能正确导出。

- **不依赖** PyQt6 / GUI，纯标准库，任何环境可直接运行
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

# 自定义文件通道：自定义 SQL/XML/Lua 写入工程目录并自动注册文件动作（--action 可显式指定，--no-action 跳过）
python -m modgen.cli custom-file write 工程.CIV --path Scripts/My.lua --content-file modgen_work/My.lua
python -m modgen.cli custom-file write 工程.CIV --path Data/Extra.sql --content "INSERT INTO ..."
python -m modgen.cli custom-file list 工程.CIV
python -m modgen.cli custom-file remove 工程.CIV --path Scripts/My.lua [--keep-file]
python -m modgen.cli check-conflicts 工程.CIV [--json]                          # 自定义 SQL × 生成 SQL 冲突检测

# 修改器四类生成（EffectType/RequirementType 存在性与参数骨架自动处理）
python -m modgen.cli generate-modifier --effect EFFECT_XXX --collection COLLECTION_XXX --desc 效果描述 [--params '{"Amount":2,"YieldType":"YIELD_PRODUCTION"}']
python -m modgen.cli generate-requirement --type REQUIREMENT_XXX --desc 条件描述 [--params '{"...":...}']
python -m modgen.cli generate-reqset --desc 集合描述 --logic ALL [--requirements '["REQUIREMENT_A"]']
python -m modgen.cli generate-ability --abbr 简称 --name 中文名 [--desc 中文描述]

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

## 推荐工作流（AI 必须遵守）

1. **新工程**：`new-project` 生成工程骨架（含基础信息/美术/修改器/文本 结构）——
   不要手工拷贝旧工程、不要手写 workspace 骨架；
2. `generate` 生成条目骨架（Type/LOC/默认值/子表结构已就位）
3. 把用户意图填入骨架：必填字段、数值、子表内容（如子表为空需确认是否应填）
4. `validate` 校验（`--entry` 单条目 或 整个工程）
   - ERROR = 硬错误，必须修
   - WARNING = 建议（type 与规则生成值不一致多为语义式命名，需确认）
5. 修正后 `merge` 进工程（内容分类与**修改器**均可 merge；merge 默认校验，不合格会拒绝）
6. **生成→校验闭环**：`preview 工程.CIV --dry-run` 查看将导出的全部文件清单，
   `preview --section 分类` 检查具体 SQL/XML 内容——早发现字段/引用/文本问题，不要等 GUI。
7. 切勿跳过 validate 直接 merge——merge 默认校验，不合格会拒绝。
8. **自定义文件（确需 Lua / 自定义 SQL/XML 时）**：`custom-file write` 写入工程目录并自动
   注册文件动作（先 `civ6proj --update-civ` 绑定目录）；**绝不手工放文件**——工具是唯一写入者；
   内容临时文件放 `modgen_work/`。自定义文件经一键生成**原样透传**，不被生成器改写。
9. **协调检测（自定义 SQL 后必跑）**：`python -m modgen.cli check-conflicts 工程.CIV [--json]`——
   同表同主键双写=ERROR（改 .CIV 条目）；UPDATE/DELETE 生成表=WARNING（反模式，用 INSERT OR REPLACE）；
   `INSERT...SELECT` 继承/自定义表合法不告警。加载顺序由工具保证（自定义 UpdateDatabase=10000 > 生成数据 9999）。

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

## 临时文件约定（必须遵守）

- **所有临时条目文件（entry 等）一律写入 `modgen_work/` 目录**（仓库根下，已 gitignore，绝不提交 git）。
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
- **自定义文件**：确需 Lua/自定义 SQL/XML 时用 `custom-file` 命令（AI 控制接口 `project_file_write`
  同语义）——按路径自动分类注册文件动作（Scripts/*.lua→AddGameplayScripts、UI/*.xml+lua→AddUserInterfaces、
  Import/*.lua→ImportFiles、Data/*.sql|xml→UpdateDatabase、Icons/→UpdateIcons、Text/→UpdateText）；
  路径穿越被拒绝；内容原样透传进 .civ6proj 与 ActionData，不被生成器改写。
- **自定义 SQL 协调**：加载顺序 = UpdateDatabase 10000（生成数据 9999 之后）；同表同主键禁止与生成
  SQL 双写（`check-conflicts` 报 ERROR）；UPDATE/DELETE 生成表 = 反模式（WARNING）；SELECT 仅用于
  `INSERT...SELECT` 继承与自定义表填充。
- **需要"更晚"的加载顺序时**：`custom-file write` 自动注册的动作 **id 就是类型名**（`UpdateDatabase`）、
  load order 10000；注册按 **(type, id)** 合并，所以同 id 只会被并进原组、**拿不到自己的顺序**。
  要独立顺序必须给**独立 id** + 显式 `load_order`（AI 接口 `add_file_action` 支持），例如遍历原版表
  （`INSERT INTO BuildingModifiers … SELECT … FROM Buildings WHERE IsWonder = 1`）用 `LoadOrder 199999`，
  确保资料片/其他 Mod 的数据已就位；同时确认该文件**没有**留在原组（否则执行两次 → 主键冲突）。

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

## UI图标规则（非实体美术资源声明）

给**不属于任何游戏实体**的 UI 元素声明专属图标（替代借 `ICON_YIELD_*` 凑）。写进 `workspace["UI图标"]` 列表：

```jsonc
{
  "icon_name": "ICON_SIQI_WUJIU_NEWS_CITY",   // 必填，须以 ICON_ 开头
  "name_zh": "城建图标",                       // 选填，仅 GUI 显示
  "sizes": [32, 50],                           // 选填，缺省 22/32/38/50/64/80/128/256
  "images": {"icon": {"path": "D:/art/news_city.png"}},  // 必填：工程外的源 PNG
  "alias": ""                                  // 选填，非空则出 IconAliases 行、不出自带图集
}
```

- **图集名自动推导**：`ATLAS_` + `icon_name` 去掉 `ICON_`（`ICON_X_32` 的文件名 → `ATLAS_X` 的 `IconSize=32` 行）；
- **命名空间硬约束**：`icon_name` 不得落进实体内置图标空间（`ICON_<实体类型>_*`，如 `ICON_DISTRICT_NEWS`
  会与 `DISTRICT_NEWS` 撞车）→ `validate` 报 ERROR；
- 源 PNG **必须存在**（工程外路径 / 工程目录相对路径 / 文件名按 `IMG|Images|Art` 搜索）→ 不存在报 ERROR；
  未设源图 = WARNING（该条被跳过）；源图最小边 < `max(sizes)` = WARNING（放大会模糊）；
- **不产出 SQL / Players / PlayerItems / 文本**——它只是美术资源，不是游戏实体；
- 校验：`python -m modgen.cli validate 工程.CIV`（与 GUI 生成前检查同源实现）；
- 单独看产物：`python -m modgen.cli preview 工程.CIV --section UI图标`（直接打印 Icons.xml）；
- 生成完整产物（Icons.xml + `IMG/ICON_X_<size>.png` + `Textures/…dds|.tex`）需 `.civ6proj` 已绑定，
  用 GUI / AI 接口 `generate_all`。

## 修改器规则（generate-modifier 等）

- **ModifierId 命名**：`MODIFIER_{前缀}_{项目号:04d}_{描述}`（如 `MODIFIER_SIQI_0035_ADJ_STRENGTH`）；
  Requirement 用 `REQUIREMENT_`、ReqSet 用 `REQSET_`、Ability 用 `ABILITY_{前缀}_{中缀}{编号:04d}_{简称}`。
- **EffectType / RequirementType / CollectionType 必须真实存在**——generator 会校验并拒绝未知类型，
  validate 也会对未知类型报错（参数集合来自 `schemas/modifier_schemas.json`，源自游戏库权威数据）。
- **参数名必须属于该 Effect/Requirement 的参数集合**（多写/拼错报 error，标准参数缺失给 warning）。
- **引用**：`owner_reqset` / `subject_reqset` / `bound_requirements` 必须指向工程内存在的 ReqSet/Requirement。
- 生成的 Modifier 参数骨架 value 为 null，AI 需填入实际值（数值/Type/文本）。
- 注意：`generate-modifier` 产物是"自定义 ModifierType"（modifier_type = modifier_id），
  若要用游戏内置 ModifierType，需另行指定。
- **ModifierStrings 预览文本**：`effect_type = EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER` 的 modifier **必须填 `preview_text`**
  （原版 226 个实例里 221 个都写了；不写不报错，但战斗预览面板不显示该加成来源）。
  工具会生成两行：`ModifierStrings(ModifierId,'Preview','LOC_{ModifierId}_PREVIEW')` + 对应 `LocalizedText`
  （前者在 `modifier_workspace`，后者在 `workspace_page._modifier_strength_preview_text_rows()`），**都要求 `preview_text` 非空**。
  写法：数值型 `+{1_Amount} [ICON_Strength] 战斗力（来源）`；`Key`（属性）型 `+{Property} [ICON_Strength] 战斗力（来源）`。
- **自定义 ModifierType 必须注册**：`.CIV` 里 `modifier_type` 不属于**原版快照**
  （`ModTools_5_4/data/vanilla_modifier_types.json`，989 条，由
  `python -m modgen.tools.extract_vanilla_modifier_types` 从游戏自带 XML 提取）时，
  导出会补 `INSERT INTO Types(KIND_MODIFIER)` + `INSERT INTO DynamicModifiers` 行。
  - 判定**不看本机运行缓存库** `DebugGameplay.sqlite`（它含玩家装过的所有 Mod 的类型，
    "库里有"≠"原版有"）；沿用它会把别人的自定义类型误当原版、不补行，
    结果 Mod 在没装那个旧 Mod 的机器上加载失败。
  - 条目可用 `modifier_type_source` 覆盖：`null`=自动（按快照）/ `"new"`=强制新建 /
    `"vanilla"`=强制视为游戏已有（用于快照漏收的极端情况）。
  - `validate` 会对「强制新建却属原版」「强制已有却不在快照」报 **ERROR**；
    自动判定为自定义时给 WARNING（提示将补注册行）。

## 知识查询：优先使用工具内置能力（新设备无需外部知识库）

生成 .CIV 所需的知识（"某个效果/能力是怎么实现的"）**由工具本身提供**，不要依赖外部资料：

0. **`modgen skill`（本地技能库全文检索，2026-08-17 起随发布包分发）**：
   ```bash
   python -m modgen.cli skill <关键词>              # 仓库根 skills/ 全文检索（文件名+内容词频评分，命中文件+片段）
   python -m modgen.cli skill <关键词> --file <相对路径>   # 输出命中文件全文（现查现读）
   ```
   - 模板/写法/工作流知识（核心表 SQL 写法、Lua API、.CIV 工作流、效果技巧）在**仓库根 `skills/`**；
   - 与 `search` 的分工：**"怎么做/怎么写" → skill**；**"某个效果在游戏里现成实现" → search**。
1. **`modgen search`（命令行首选，AI 直接可用）**：
   ```bash
   python -m modgen.cli search <关键词>          # 自然语言/中文效果词（"通往你城市的贸易路线加产出"）或英文 Type/参数（WAR/YIELD_PRODUCTION）
   python -m modgen.cli search --object <关键词>  # 列出命中对象的全部 Modifier 实现（EffectType/参数/条件集/条件，照抄用）
   ```
   - **排序为 BM25 相关性**（中文 bigram + 领域词典 + 字段权重，与 GUI 能力实现搜索同一实现）：
     可以直接用整句中文描述意图，结果按相关性从高到低排列（不再是"整句子串匹配"）；
   - 路径自动解析：`--game-db/--text-db` 参数 > 当前目录 `settings.json` > 游戏默认 Cache；中文检索需要文本库（settings.json 的 `active_text_db_path`）；
   - 例：`search --object 农场` → 高棉「大人工湖」→ `TRAIT_FARM_AQUEDUCT_ADJECENCY_FOOD [EFFECT_ADJUST_PLOT_YIELD]` + `REQUIREMENT_PLOT_IMPROVEMENT_TYPE_MATCHES(IMPROVEMENT_FARM)` ——"相邻农场+食物"的现成实现，直接照抄。
2. **能力实现搜索（ModTools 小工具 → 能力实现搜索）**（GUI 场景）：
   - 中文搜效果/描述，或英文搜 Type/参数；打开对象后右侧展示**完整实现**（含 ATTACH/GRANT_ABILITY 嵌套展开）；
   - **用途**：与 `modgen search --object` 相同，只是 GUI 版。
3. **游戏库（DebugGameplay.sqlite）**：`modgen validate` 会校验 EffectType/RequirementType/参数名归属；不确定的表结构/字段名直接查库。
   ```bash
   python -m modgen.cli query "SELECT ModifierType, CollectionType, EffectType FROM DynamicModifiers WHERE ModifierType LIKE '%PLOT_YIELD%' LIMIT 10"
   python -m modgen.cli query "PRAGMA table_info(Units)"        # 查表结构（只读）
   python -m modgen.cli query "SELECT ..." --json                # JSON 输出
   ```
   `query` 只允许 SELECT/WITH/PRAGMA/EXPLAIN（只读打开），行数上限 50（`--limit` 调，最大 500）。
4. **文本库（LOC 查询）**：不确定某个 LOC 文本内容时：
   ```bash
   python -m modgen.cli loc LOC_TRAIT_CIVILIZATION_XXX_NAME     # 含 {LOC_...} 引用链展开
   ```
5. **modgen schemas**：`modgen/schemas/modifier_schemas.json`（789 效果类型参数集）与 `entry_schemas.json` 是工具内置的权威数据。

> **方法论（硬性要求）**：判断"某个效果有没有现成实现"的唯一正确方法是 **search 查原版**，**不要凭记忆断言做不到**——绝大多数效果游戏里都有对应 Modifier（相邻加成、地块产出等）。确需 Lua 的只有自定义界面/事件逻辑等极少数场景，此时经自定义文件通道写入，Lua 知识查 `modgen skill`（skills/04-lua/）。
> 注意：知识一律用上述工具内能力查询（技能库已内迁仓库根 `skills/`，随发布包分发，`modgen skill` 检索；外部目录仅为开发机历史备份，不作为依赖）。
> 硬规则不变：ModifierType 优先引用游戏库已有类型（确需新建时补 DynamicModifiers 行）；JSON 禁止 `""`；
> 主内容不写 Lua（自定义 SQL/XML/Lua 仅走 `custom-file` 自定义文件通道）。

## 重新生成 schema

编辑器字段变化后，需重新提取 schema（需要 PyQt 环境）：

```bash
python modgen/tools/extract_schemas.py
```
