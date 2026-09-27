# modgen

原生相邻提供 `adjacency list/show/check` 与官方离线快照；`text-icons format/check` 按角色处理描述图标。两项审计接入 project-check/build，PSD 社区模板随技能分发，详见 [契约](AGENTS.md)。

文明6 Mod 工程(.CIV) 生成与校验工具。规则与 ModTools 5.4 编辑器一致。数据和扩展源码命令为纯标准库；完整预览、检查与生成需要 PyQt。

> AI Agent 请阅读 [AGENTS.md](AGENTS.md)（必读）。

## 用途

头像、历史时刻和实体图标提供 `image inspect-psd/extract-psd/render/check`：从用户 PSD 提取底板/透明蒙版，用 JSON 配方套框、裁切、处理白标/灰度，输出多背景与小尺寸预览。区域白色核心插入 PSD 的 Alpha 组，读取渐变、描边和发光，同时保存可编辑 PSD；旧的底板叠白图配方被拒绝。核心不依赖 Qt 或 AI SDK；区域渲染需要 psd-tools[composite]>=1.20，PNG 与 Photoshop 的近似差异写入报告。构图与识别仍需多模态模型/人工验收。见 [图像模板技能](../skills/civ6-art-images/SKILL.md)。

自定义 UI/Lua LOC 使用 `.CIV` 的 `文本.custom_entries`，由统一 Text SQL/XML 输出；字段及冲突规则见 [美术与文本指南](../skills/05-modtools-civ/ui-assets.md#自定义-ui--lua-loc-文本)。

原生面板的 Lua 替换使用 `extension write --role ui_replace --lua-context CityPanel`；单个 UI/ Lua 自动生成 ReplaceUIScript 属性，无需 XML 配对，参见 [项目扩展](../skills/05-modtools-civ/project-extensions.md)。

独立纹理使用 `texture add/list/remove`；HTML 原型提供 `texture render/import-manifest/verify`，见 [可分享 UI 技能](../skills/civ6-html-ui/SKILL.md) 和 [命令契约](AGENTS.md#html-ui-纹理工具)。

地标模型提供 `landmark catalog/compose/import/verify/cook`：静态官方几何组合、托管资源包、CIV/ModBuddy 导出和隔离的官方编译；`local_pantry/local_files` 可纳管已转换好的自建静态 GEO/FGX/材质/纹理，支持二进制原样导出。区域 building_sets 按玩法可达阶段限制输出，base_variants 可按完整建筑组合切换基底，未列出组合回退 base_asset；同名 SDK 几何/材质/纹理仅在源与关联载荷完全相同后消歧。美术源目录不写入 civ6proj 发布项，verify 会检查误注册；见 [地标技能](../skills/civ6-landmarks/SKILL.md)。

让 AI（或脚本）生成"编辑器能直接打开、正确导出"的 .CIV 工程与条目：
- `new-project`：创建工程级 .CIV 骨架（基础信息/美术/修改器/文本 结构就位，无需拷贝旧工程）
- `generate`：意图参数 → 合规条目（Type/LOC/默认值/子表骨架自动生成）
- `validate`：条目/工程规则校验（ERROR 硬错误 / WARNING 建议）
- `merge`：条目合并进工程（内容分类与修改器；同 id 去重，自动备份 .bak）
- `civ6proj`：从 .CIV 基础信息生成 ModBuddy 兼容 .civ6proj + 空白 Art.xml（`--update-civ` 回写路径）
- `extension`：Core/Gameplay/UI 配套初始化、源码清单、依赖、旧文件纳管（init/write/import/list/check/remove）；纯标准库
- `project-check` / `build`：统一检查与 ModBuddy 工程源码生成，需 PyQt；不调用 ModBuddy 编译或部署
- `custom-file`：自定义 SQL/XML/Lua 文件通道——有扩展清单时写源码目录，旧工程写绑定的输出目录（write/list/remove；与 AI 控制接口 `project_file_write` 同语义）
- assets check / audio check / art compare / workshop check：纯标准库只读检查资源引用、音频依赖、Cooker XML 差异及工坊包；[契约与边界](AGENTS.md#资源与发布产物检查)
- `skill`：本地技能库（仓库根 `skills/`，随源码分发）章节检索——中文 bigram + 英文词边界 + BM25；`--plan` 必读清单、`--file --section` 章节、`--check` 质量检查、`--json` 结构化输出
- `search`：能力实现搜索（**BM25 检索**：中文 bigram + 领域词典 + 字段权重 + 相关性排序；支持"通往你城市的贸易路线加产出"这类自然语言；与 GUI 小工具同一实现）
- `query`：游戏库只读查询（仅 SELECT/WITH/PRAGMA/EXPLAIN，自动限行）
- `loc`：LOC 标签 → 简体中文（含嵌套 `{LOC_...}` 引用链展开，单一实现见 `ModTools_5_4/db/loc_text.py`）
- `preview`：无头预览 .CIV 将导出的全部文件（SQL/XML/Icons/ArtDef/XLP…，验证闭环；需 PyQt 环境）

领袖支持 fallback_images 外交表情映射，GUI 与校验/导出共享 project/leader_fallbacks.py；见 [领袖美术](../skills/05-modtools-civ/leader-art.md)。社区工作流与署名见 [来源说明](../THIRD_PARTY_NOTICES.md)。

美术检查支持 assets check <工程> --cooker-config <目标SDK/Civ6.cfg>，核对 XLP/AST/GEO/TEX 的类注册与允许关系；BLP/FGX 复原及证据边界见 [美术解包指南](../skills/05-modtools-civ/art-unpack.md)。

修改器校验包含 Property 产出二进制家族档位提示，按具体效果区分最高档，详细边界见 [AI 契约](AGENTS.md#二进制产出档位检查)；线性范围计数优先 [逐来源挂载](../skills/07-techniques/modifiers/patterns/pattern-spatial-attach-count.md)。

## 安装/运行

以源码目录运行，不依赖 EXE 或预制 ZIP。分享时保留 `modgen/`、`ModTools_5_4/`、`skills/` 和必要资源；使用 [源码分享工具](../docs/SOURCE_SHARING.md)导出完整目录。基础数据/知识命令为标准库；完整生成和 GUI 的依赖由 `tools/setup_env.py` 初始化。


```bash
# 无需安装，仓库根目录下直接运行
python -m modgen.cli new-project 工程.CIV --name 中文工程名 --prefix SIQI --infix 35
python -m modgen.cli generate 区域 --name "测试区域" --abbr TEST --prefix SIQI --infix 35
python -m modgen.cli generate-modifier --effect EFFECT_DISTRICT_ADJACENCY --collection COLLECTION_OWNER --desc ADJ_STRENGTH
python -m modgen.cli generate-requirement --type REQUIREMENT_PLOT_ADJACENT_FEATURE_TYPE_MATCHES --desc ADJ_FOREST
python -m modgen.cli generate-reqset --desc MILITARY --logic ALL
python -m modgen.cli generate-ability --abbr DEMO_ABILITY --name "测试能力"
python -m modgen.cli generate-ability --abbr INTERNAL_MARKER  # 内部能力允许 Name/Description 为 NULL
python -m modgen.cli validate 工程.CIV
python -m modgen.cli merge 工程.CIV 区域 --entry entry.json
python -m modgen.cli merge 工程.CIV 修改器 --entry modifier.json
python -m modgen.cli civ6proj 工程.CIV --update-civ   # 生成 .civ6proj + 空白 Art.xml 并回写路径
python -m modgen.cli custom-file write 工程.CIV --path Scripts/My.lua --content-file modgen_work/My.lua
python -m modgen.cli custom-file list 工程.CIV
python -m modgen.cli skill 相邻加成          # 本地技能库全文检索（--file 查看全文）
python -m modgen.cli query "SELECT ModifierType FROM DynamicModifiers LIMIT 5"
python -m modgen.cli loc LOC_DISTRICT_AQUEDUCT_NAME
python -m modgen.cli preview 工程.CIV --dry-run
```

## 结构

```
modgen/
├── landmark.py               # AST 资源包 CLI、隔离 Cooker；共享核心 project/landmarks.py
├── AGENTS.md                 # AI Agent 必读说明
├── cli.py                    # generate / validate / merge / search / new-project / civ6proj / custom-file / query / loc / preview 命令
├── rules.py                  # 命名/结构规则（与 GUI 一致）
├── generator.py              # generate 核心
├── modifier_generator.py     # 修改器四类生成（Modifier/Requirement/ReqSet/Ability）
├── validator.py              # 校验（errors + warnings）
├── modifier_validator.py     # 修改器校验（类型/参数名/引用）
├── merger.py                 # 合并进 .CIV（自动备份）
├── modifier_merger.py        # 修改器条目合并进工程"修改器"节
├── project_scaffold.py       # new-project 工程骨架（运行时纯标准库）
├── asset_cli.py              # 资源/音频/Cooker/工坊只读检查；核心 project/asset_checks.py
├── extension_cli.py          # 扩展源码管理、project-check/build；核心复用 project/extensions.py
├── sql_inspect.py            # SQL 词法、VALUES 多行/复合主键及 XML Row 保守检查
├── custom_file.py            # custom-file 自定义 SQL/XML/Lua 文件通道（写工程目录 + 注册文件动作）
├── texture.py                # PNG 声明增删、清单全批校验后一次登记
├── html_ui.py                # HTML 渲染/像素验证适配器，复用 skills/civ6-html-ui/scripts
├── skill_cli.py              # 知识命令展示（路由/章节/质量检查）
├── skills.py                 # skill 本地技能库全文检索（仓库根 skills/，文件清单/mtime/size 缓存索引）
├── dbquery.py                # query（游戏库只读查询）/ loc（LOC 文本查询）
├── mt_bridge.py              # 复用 ModTools 侧 db.loc_text / db.search_index / project.civ6proj_generator / project.custom_files（单一实现，防漂移）
├── preview.py                # preview（无头 GUI 生成引擎，需 PyQt）
├── schema_store.py           # 加载 entry_schemas.json / modifier_schemas.json
├── schemas/entry_schemas.json# 条目结构 schema（提取产物，提交 git）
├── schemas/modifier_schemas.json # EffectType/RequirementType 参数集（源自游戏库）
├── schemas/project_scaffold.json # 工程骨架默认结构（extract_scaffold 提取，提交 git）
├── tools/extract_schemas.py  # 从 ModTools 源码+fixture 重新提取 schema
├── tools/extract_scaffold.py # 从 GUI 编辑器默认导出重新提取工程骨架
└── tests/test_modgen.py      # 回归测试（fixture 全过 + 真实错误抓取）
└── tests/test_cli_tools.py   # 新命令测试（new-project/query/loc/merge 修改器/preview）
```

> `search` 的检索实现（BM25 + 领域词典）与 LOC 嵌套解析在 `ModTools_5_4/db/`（`search_index.py` /
> `loc_text.py`），modgen 经 `mt_bridge.py` 复用——**不在 modgen 内另维护一份**（历史教训：两份实现
> 漂移导致嵌套引用解析缺失、中文检索失效）。

## 测试

```bash
python -m unittest discover -s modgen/tests -v
```

## 临时文件

遵守 [本地工程与临时文件约定](AGENTS.md#本地-mod-工程与临时文件约定必须遵守)：新 Mod 的工程、扩展源码和专用脚本/测试/报告/产物默认集中到 `modgen_work/<工程名>/`，不进入 ModTools 的 Git；已有工程保持路径，`.CIV` 和 `*.extensions/` 由忽略规则覆盖，正式源码需保留和备份。通用工具测试与参考数据仍纳入版本管理。AI 会话的临时条目文件一律放仓库根 `modgen_work/`；`generate` 输出为 stdout 可直接消费。merge 备份 `.CIV.bak` 自动生成、下次覆盖。`preview` 默认把预览文件写到 `modgen_work/preview_<工程名>/`。

## schema / 骨架更新

编辑器字段变化后（需 PyQt 环境，offscreen）：

```bash
python modgen/tools/extract_schemas.py     # 条目/修改器 schema
python modgen/tools/extract_scaffold.py    # new-project 工程骨架（基础信息/美术/修改器默认结构）
```
