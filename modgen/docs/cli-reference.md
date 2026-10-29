# modgen CLI 命令清单

> 受众：调用 modgen 的 AI 与脚本 ｜ 何时读：需要具体命令、参数、输出格式或字段说明时 ｜ 适用版本：ModTools 5.4

> 本文件是 [modgen/AGENTS.md](../AGENTS.md) 的命令附录：生成/校验契约与硬规则以 AGENTS.md 为准，本文件只列命令、参数与字段说明。

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
python -m modgen.cli extension write 工程.CIV --core --content-file workspace/scratch/Core.sql
python -m modgen.cli extension write 工程.CIV --path Scripts/My.lua --role gameplay --feature events --depends-on core --content-file workspace/scratch/My.lua
python -m modgen.cli extension write 工程.CIV --path UI/CityPanel_Custom.lua --role ui_replace --lua-context CityPanel --content-file workspace/scratch/CityPanel_Custom.lua
python -m modgen.cli extension list 工程.CIV --json
python -m modgen.cli extension check 工程.CIV --json
python -m modgen.cli extension import 工程.CIV --path Scripts/Old.lua --role gameplay
python -m modgen.cli extension remove 工程.CIV --path Scripts/Old.lua
python -m modgen.cli project-check 工程.CIV --json
python -m modgen.cli build 工程.CIV --overwrite all --json

# 自定义文件通道：有扩展清单时写源码目录，旧工程写绑定的输出目录（--action 可显式指定，旧工程可用 --no-action 跳过）
python -m modgen.cli custom-file write 工程.CIV --path Scripts/My.lua --content-file workspace/scratch/My.lua
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

## 二进制产出档位检查

修改器校验会提示可识别的 Property 产出二进制家族档位过高：城市/区域正数最高档通常不超过 1024、负数 64，地块正数 64、负数 8。这是制作经验提示，不是引擎极限；不阻断有依据的特殊设计，也不改写工程。识别依赖多个幂次后缀 Property 与实际 Modifier 条件链，动态 SQL 等未覆盖内容需人工核对。完整选型、Core 样本与超限处理见 [二进制指南](../../skills/reference/lua/lua-binary.md)。

## UnitAbility 显示文本

`generate-ability` 的 `--name` / `--desc` 均可省略，分别输出 `name_zh: null` / `description_zh: null`。原版 UnitAbilities 两列允许 NULL；内部标记、劳动力扣减等辅助能力无需显示名和说明。仅有玩家需要了解的独立效果才填写，内部能力同时关闭 `show_float_text_when_earned`。导出器保留 SQL NULL，且不生成对应空 LOC；名称或说明也可以只填其中一项。

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

search 查游戏库实现；query 只读 SELECT/WITH/PRAGMA/EXPLAIN，默认 50 行、最大 500；loc 查询已配置文本库。来源和不可用的历史资料说明见 [SOURCES](../../skills/SOURCES.md)。

原生相邻规则与 text-icons 检查见 [相邻与文本检查](channels/adjacency-text.md)。

## 专项字段与规则（涉及时必读）

- [项目级扩展](../../skills/guides/project-extensions.md)：清单完整字段、Core、GP/UI 配套、迁移、依赖和静态检查边界。
- [UI 美术与文本](../../skills/reference/art/ui-assets.md)：UI图标、ui_textures、custom_entries 的完整字段与命令；包含 texture add/list/remove、覆盖策略、尺寸与动作要求。
- [修改器与类型来源](../../skills/guides/modifiers.md)：生成器参数、原版快照、modifier_type_source、preview_text 与引用验证。

## 重新生成 schema

编辑器字段变化后，需重新提取 schema（需要 PyQt 环境）：

```bash
python modgen/tools/extract_schemas.py
```
