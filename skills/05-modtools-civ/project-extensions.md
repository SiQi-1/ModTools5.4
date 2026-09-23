# 项目级扩展：Core.sql、Lua 与统一交付

一个完整功能可同时需要 .CIV 数据、扩展 SQL、Gameplay Lua、UI 和资源。开始前一起规划，使用稳定的标识和依赖连接各部分；不要到生成后再临时补文件。行为边界见 [RULES](../RULES.md)，执行次序见 [WORKFLOW](../WORKFLOW.md)。

## Core.sql 的默认职责

工具支持的实体、Modifier、Requirement、文本、图标和纹理继续通过 .CIV 管理。默认 `Data/{file_name}_Core.sql` 集中维护工具暂未表达的 Gameplay SQL、自定义配置表、INSERT SELECT 和必要补丁。Lua 从约定的数据表读取配置，具体 API 按 [Lua 规范](../04-lua/code-style.md) 查证。

默认一个 Gameplay Core.sql。数据库作用域不同、需要在生成数据之前建表、或有明确的独立依赖时，再增加文件。文本和图标 SQL 不能随意并入 Gameplay；同一条数据只保留一个维护入口，不在 .CIV 和 Core 重复 INSERT。

## 初始化与源码位置

```powershell
python -m modgen.cli extension init 工程.CIV --gameplay --ui
python -m modgen.cli extension write 工程.CIV --core --content-file modgen_work/Core.sql
python -m modgen.cli extension write 工程.CIV --path Scripts/My_Gameplay.lua --role gameplay --feature events --depends-on core --content-file modgen_work/Gameplay.lua
python -m modgen.cli extension list 工程.CIV --json
```

`init` 必须有已保存的 .CIV，不需要先绑定 .civ6proj。默认创建 Core；`--gameplay` / `--ui` 可选创建脚本入口和成对 UI 文件，重复执行保留已有源码。输出基名来自基础信息 file_name，省略时取 .CIV 文件名。

```text
工程.CIV
工程.extensions/
  Data/My_Core.sql
  Scripts/My_Gameplay.lua
  UI/My_Panel.xml
  UI/My_Panel.lua
```

源码目录是 .CIV 旁的 `{CIV文件名}.extensions`，同目录多个工程互不共享默认目录；路径记录为相对路径。备份与迁移时一起带上 .CIV 和扩展目录；这些是正式 Mod 源码，不可随临时缓存删除。遵守 [R4 仓库边界](../RULES.md#r4-数据与写入边界)：在 ModTools 仓库中 `.CIV` 与 `*.extensions/` 均为本地工作资料，不提交；只有独立 Mod 仓库才将两者共同纳入 Git。GUI 跨目录另存会复制已声明源码，遇到内容不同的目标文件会拒绝覆盖。图片及既有纹理源仍使用美术字段，扩展管理不自动搬运所有外部资源。

## 清单字段与功能归属

.CIV 顶层可选 `extensions`，不增加 workspace 分节。旧工程没有该字段时保持原有自定义文件流程。

```json
{
  "version": 1,
  "source_root": "工程.extensions",
  "files": [
    {
      "id": "core",
      "path": "Data/My_Core.sql",
      "role": "database",
      "scope": "in_game",
      "phase": "after_generated",
      "feature": "events",
      "depends_on": []
    }
  ]
}
```

| 字段 | 含义 |
|---|---|
| id | 稳定英文标识，供 depends_on 引用；初始化使用 core/gameplay/ui_xml/ui_lua |
| path | 输出相对路径；实际源码位于 source_root/path，禁止穿越、盘符和越界链接 |
| role | database / text / icons / colors / gameplay / ui / import |
| scope | front / in_game / both；脚本和 UI 当前仅支持 in_game |
| phase | 仅 database 使用 before_generated / after_generated，默认后者 |
| feature | 文件所属功能，用于定位问题；共享 Core 可命名为 core |
| depends_on | 依赖的扩展 id 数组，检查存在性和循环；空数组表示无依赖 |

`extension write` 未指定的元数据保留旧值；新文件按路径推断 role。使用 `--id`、`--feature`、`--scope`、`--phase`、重复 `--depends-on` 设置元数据，`--clear-dependencies` 清空依赖。UI 使用 UI/ 下同名 XML/Lua，XML 根必须是 Context，动作只引用 XML，二者都进入 Content。依赖 UI 时引用 XML 入口 id。

## 加载顺序与边界

每个扩展动作有独立 `MTX_` ID。输出时从旧动作中排除受管文件，按清单重新登记，避免重复执行或被合并进生成组。

- 同一数据库 scope 内，before_generated 排在已有 UpdateDatabase 动作之前，after_generated 排在其后；同阶段按依赖拓扑排序。
- 不同数据库 scope 的 SQL 不建立顺序依赖；before_generated 不得依赖 after_generated。
- 当前序列化使用正 LoadOrder；如果前置阶段没有正数空间，检查明确报错，需调整已有动作顺序。
- 跨角色依赖表示功能所需的文件齐备，**不表示 SQL 和 Lua 共享一个数值加载时序**。GP/UI 运行环境仍按 Lua 规范隔离。
- 该排序只相对于本项目的动作；对其他 Mod 的实际依赖与游戏运行时机仍需单独核实。

## 检查与生成

```powershell
python -m modgen.cli extension check 工程.CIV --json
python -m modgen.cli project-check 工程.CIV --json
python -m modgen.cli civ6proj 工程.CIV --out modgen_work/ModBuddy --update-civ
python -m modgen.cli build 工程.CIV --overwrite all --json
```

- `extension check`：纯标准库，检查清单、源码、XML、UI 配对、依赖和动作计划。
- `project-check`：还检查 .CIV 数据、完整预览、生成文件重名、动作引用和 SQL 冲突，需要 PyQt。
- `build`：复用现有生成器、自动配置生成文件动作、检查后写入绑定的 ModBuddy 工程，并保存动作配置。默认 `--overwrite none` 保留现有输出；源码更新需要显式 all。GUI/AI generate_all 同样纳入扩展源码与生成前检查。
- preview 和检查不写输出。源文件缺失时报错，不能用输出目录旧副本替代。移除使用 `extension remove --path`；输出副本在下次覆盖生成时按删除计划清理，`--keep-file` 仅保留源码。

SQL 检查覆盖已知主键的 VALUES 多行及 XML Row、复合主键、引号/注释/字符串分号，区分数据库作用域。未知主键、动态表达式、INSERT SELECT、CTE/触发器会提示检查范围；不执行 SQL，不做 Lua 语法编译和运行时验证。构建、Cooker、部署与游戏验收见 [交付指南](pipeline.md)。

## 旧工程迁移与 AI 接口

先保留工程版本，再 `extension init`。同名 Core/可选骨架文件已存在于绑定输出目录时，初始化采纳其内容；其他旧文件逐个按路径 `extension import` 纳管，整个功能可在同一轮批量执行：

```powershell
python -m modgen.cli extension import 工程.CIV --path Scripts/Existing.lua --role gameplay --feature events --depends-on core
python -m modgen.cli project-check 工程.CIV --json
```

import 读取旧输出目录，复制为源码，不删除原文件、不覆盖现有受管源码；未迁移的旧文件仍兼容。已启用扩展的 `custom-file write` 和 AI `project_file_write` 自动写入源码目录；`--no-action` 不适用受管文件，Lua 工具库声明为 import。

AI 新动作 `extension` 支持 init/write/list/check/remove，参数见 [API](../../ModTools_5_4/docs/AI_CONTROL_API.md)。修改会自动保存 .CIV；`project_check` 检查当前编辑状态。`get_state` 包含清单，`get_manifest` 包含扩展路径和错误。正式文件由工具管理，内容临时文件仍放 modgen_work。
