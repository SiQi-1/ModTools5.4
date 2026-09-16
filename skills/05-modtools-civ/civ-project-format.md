# .CIV 工程文件格式（稳定摘要）

> 本文只写**稳定结构**；精确键名/字段以 `reference/modtools-civ/MANIFEST.md` 钉住的快照和样例工程（`D:\文明6mod用文件夹\ModTools5.4\*.CIV`）为准。**禁止把快照内容抄进本文件**。

## 总览

- `.CIV` = JSON 文本（UTF-8，`ensure_ascii=False`，`indent=2`），扩展名大写 `.CIV`
- 顶层两个节点：`meta`（format=`CIV_PROJECT`、schema_version=`0.1.0`、project_name）和 `workspace`（17 个 section）
- **section 顺序固定**（`CIV_SECTION_ORDER`，定义在快照 `project/civ_project.py`），缺 section 会被加载器按形态补空，多余 section 被丢弃 —— 写文件时按顺序排列

## 17 个 section 的形态

| 形态 | section |
|------|---------|
| **dict**（直接工作区） | 基础信息、美术、文本、修改器 |
| **list**（条目列表） | 文明、领袖、区域、建筑、单位、单位晋升、改良设施、总督、伟人、政策卡、项目、信仰、议程 |

- dict section 内部：`基础信息`/`美术`/`修改器` 为 `{format, schema_version, data}` 三键包装；`文本` 为 `{preview_settings}`（文本以 LOC 键嵌入各实体条目内）
- list section：每个元素是一个实体条目（键见 `entity-templates/`），可空列表

## 修改器 section 内部（最复杂，dict 的 data）

`data` 含 7 个键（均不可省略时按需给空列表）：

| 键 | 内容 |
|----|------|
| `prefix1` / `prefix2` | 与基础信息一致的 prefix/infix 拆开（Type 命名源） |
| `owners` | 修改器挂载点（`table_name`/`type_column`/`type_name`/`display_name`/`source_key`/`bound_modifier_ids`/`owner_bindings`） |
| `unit_abilities` | 单位能力条目（`unit_ability_type`/`name_zh`/`description_zh`/`inactive`/`show_float_text_when_earned`/`permanent`/`type_tags`） |
| `modifiers` | 修改器条目（`modifier_id`/`modifier_type`/`comment`/`owner_reqset`/`subject_reqset`/`run_once`/`new_only`/`permanent`/`owner_stack_limit`/`subject_stack_limit`/`effect_type`/`collection_type`/`preview_text`/`parameters`） |
| `requirement_sets` | 条件集（`requirement_set_id`/`comment`/`logic`/`bound_requirements`） |
| `requirements` | 条件（`requirement_id`/`comment`/`requirement_type`/`likeliness`/`impact`/`progress_weight`/`inverse`/`reverse`/`persistent`/`triggered`/`parameters`） |

> **参数形态**（modifiers/requirements 的 `parameters`）：`[{"name": "Amount", "value": 1.0}, {"name": "YieldType", "value": {"yield_type": "YIELD_FOOD", "display": "食物", "name": "食物", "value": "YIELD_FOOD"}}]` —— value 可为**标量**（数字/字符串）或**选择器对象**（从游戏库选的枚举，含 display 中文名）。对照 `data/effect_type_parameters.json` 确认参数名/类型。

> 与手写 SQL 的对应关系：modifiers ↔ `Modifiers`+`ModifierArguments`；requirement_sets/requirements ↔ `RequirementSets`+`Requirements`+`RequirementArguments`+`RequirementSetRequirements`；owner 表 ↔ 挂载链（`TraitModifiers`/`BuildingModifiers` 等，对应 AGENTS.md §5 陷阱 12）。**Modifier 知识全部复用 `skills/07-techniques/`，只是落盘载体从 SQL 换成 JSON。**

## 生成链路（为什么 .CIV 写对了就够）

```
.CIV (JSON) → ModTools5.4 工具 → SQL/XML/图标/ArtDef/XLP → ModBuddy 工程 → .modinfo 打包
```

- 工具按 section 生成独立文件：`<基础信息.file_name>_<section>.sql` / `Text.sql` / `Icons.xml` 等
- 用户可用工具"生成预览"检查产物；AI 侧出口检查用 `check_civ.py`
