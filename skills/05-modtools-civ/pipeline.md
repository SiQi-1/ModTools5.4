# 自定义文件与交付

统一执行顺序见 [WORKFLOW](../WORKFLOW.md)，写入边界见 [RULES](../RULES.md)。本页补充特殊 SQL、Lua、UI XML 与实际导出的步骤。

## 创建与注册

先用 `python -m modgen.cli civ6proj 工程.CIV --update-civ` 绑定输出目录。将内容临时文件写在 `modgen_work/`，经工具写入正式工程：

```powershell
python -m modgen.cli custom-file write 工程.CIV --path Scripts/My.lua --content-file modgen_work/My.lua
python -m modgen.cli custom-file list 工程.CIV
python -m modgen.cli check-conflicts 工程.CIV --json
```

Scripts → AddGameplayScripts；UI XML/Lua → AddUserInterfaces；Import → ImportFiles；Data SQL/XML → UpdateDatabase。AI 接口 project_file_write 同语义。UI XML 与同名 Lua 配对及环境隔离见 [Lua 规范](../04-lua/code-style.md)。

## SQL 协调与加载顺序

- 新实体/标准效果先由 .CIV 生成。自定义 SQL 用于工具未表达的 SELECT 继承、批量挂载、自定义表等，不能与生成 SQL 同表同主键双写。
- `check-conflicts` 的 ERROR 必须处理；UPDATE/DELETE 的 WARNING 需判断执行顺序和意图，不能机械换成 INSERT OR REPLACE（会覆盖整行）。
- 自动 UpdateDatabase 动作默认顺序 10000，生成数据默认 9999；实际合并按 (type,id)，检查最终 .civ6proj，不能只根据默认值判断。
- 需要独立顺序时用 AI `add_file_action` 指定独立 id 和 load_order，移除原动作中的重复文件，随后 `save_project`。例如批量奇观挂载见 [通用技巧](../07-techniques/modifier-techniques.md)。

## 输出与验证

validate → preview 文件清单/具体内容 → check-conflicts → GUI/AI generate_all。preview 写预览目录；generate_all 才写绑定工程。自定义文件原样透传，不改生成文件来修正源数据。检查动作引用的文件存在且只执行一次。

针对复杂 SQL，可在具备目标 schema 的临时 SQLite 库执行并开启外键；区分 Gameplay / FrontEnd / 本地化库，并处理游戏专属函数。模拟加载只能验证部分结构，owner/subject 语义和游戏效果仍需实机。

## 构建与部署

工程源目录与游戏 Mods 目录是两份状态。通过 ModBuddy Build / 美术 Cooker 生成所需 .modinfo 与编译资源，再同步部署；核对动作、加载顺序、文件列表和实际文件。只同步源 SQL 不代表纹理或 UI 已完成构建。

交付时分别报告源文件生成、构建、部署、游戏内验证状态。相关协议见 [AI 控制接口](../../ModTools_5_4/docs/AI_CONTROL_API.md)。
