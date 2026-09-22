# modgen

文明6 Mod 工程(.CIV) 生成与校验工具。规则与 ModTools 5.4 编辑器一致，纯标准库实现，不依赖 PyQt。

> AI Agent 请阅读 [AGENTS.md](AGENTS.md)（必读）。

## 用途

自定义 UI/Lua LOC 使用 `.CIV` 的 `文本.custom_entries`，由统一 Text SQL/XML 输出；字段及冲突规则见 [AI 契约](AGENTS.md#自定义-ui--lua-loc-文本)。

独立纹理使用 `texture add/list/remove`；完整字段与生成约定见 [AI 契约](AGENTS.md#独立-ui-纹理背景--按钮--精灵表)。

让 AI（或脚本）生成"编辑器能直接打开、正确导出"的 .CIV 工程与条目：
- `new-project`：创建工程级 .CIV 骨架（基础信息/美术/修改器/文本 结构就位，无需拷贝旧工程）
- `generate`：意图参数 → 合规条目（Type/LOC/默认值/子表骨架自动生成）
- `validate`：条目/工程规则校验（ERROR 硬错误 / WARNING 建议）
- `merge`：条目合并进工程（内容分类与修改器；同 id 去重，自动备份 .bak）
- `civ6proj`：从 .CIV 基础信息生成 ModBuddy 兼容 .civ6proj + 空白 Art.xml（`--update-civ` 回写路径）
- `custom-file`：自定义 SQL/XML/Lua 文件通道——写入工程目录并自动注册文件动作（write/list/remove；与 AI 控制接口 `project_file_write` 同语义）
- `skill`：本地技能库（仓库根 `skills/`，随发布包分发）全文检索——文件名+内容词频评分、命中片段、`--file` 全文
- `search`：能力实现搜索（**BM25 检索**：中文 bigram + 领域词典 + 字段权重 + 相关性排序；支持"通往你城市的贸易路线加产出"这类自然语言；与 GUI 小工具同一实现）
- `query`：游戏库只读查询（仅 SELECT/WITH/PRAGMA/EXPLAIN，自动限行）
- `loc`：LOC 标签 → 简体中文（含嵌套 `{LOC_...}` 引用链展开，单一实现见 `ModTools_5_4/db/loc_text.py`）
- `preview`：无头预览 .CIV 将导出的全部文件（SQL/XML/Icons/ArtDef/XLP…，验证闭环；需 PyQt 环境）

## 安装/运行

```bash
# 无需安装，仓库根目录下直接运行
python -m modgen.cli new-project 工程.CIV --name 中文工程名 --prefix SIQI --infix 35
python -m modgen.cli generate 区域 --name "测试区域" --abbr TEST --prefix SIQI --infix 35
python -m modgen.cli generate-modifier --effect EFFECT_DISTRICT_ADJACENCY --collection COLLECTION_OWNER --desc ADJ_STRENGTH
python -m modgen.cli generate-requirement --type REQUIREMENT_PLOT_ADJACENT_FEATURE_TYPE_MATCHES --desc ADJ_FOREST
python -m modgen.cli generate-reqset --desc MILITARY --logic ALL
python -m modgen.cli generate-ability --abbr DEMO_ABILITY --name "测试能力"
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
├── custom_file.py            # custom-file 自定义 SQL/XML/Lua 文件通道（写工程目录 + 注册文件动作）
├── texture.py                # texture 原尺寸 PNG 声明增删（校验复用 project/ui_textures.py）
├── skills.py                 # skill 本地技能库全文检索（仓库根 skills/，mtime 缓存索引）
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

AI 会话的临时条目文件一律放仓库根 `modgen_work/`（已 gitignore，绝不提交 git）；`generate` 输出为 stdout 可直接消费。merge 备份 `.CIV.bak` 自动生成、下次覆盖。`preview` 默认把预览文件写到 `modgen_work/preview_<工程名>/`。

## schema / 骨架更新

编辑器字段变化后（需 PyQt 环境，offscreen）：

```bash
python modgen/tools/extract_schemas.py     # 条目/修改器 schema
python modgen/tools/extract_scaffold.py    # new-project 工程骨架（基础信息/美术/修改器默认结构）
```
