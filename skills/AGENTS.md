# skills/ — ModTools5.4 本地技能库（随发布包分发）

> **本目录是文明6 Mod 制作的**唯一本地知识源**（2026-08-17 起内迁自外部工作区，随仓库/发布包分发）。
> 用 ModTools5.4 / modgen 制作 Mod 时缺知识，**先查这里**——不要凭记忆，也不要去翻外部目录。

## 快速入口

| 分类 | 内容 | 何时用 |
|---|---|---|
| `01-core-tables/` | 游戏核心表（Types/Modifiers/文本/图标等）SQL 写法模板 | 写 SQL/自定义补丁时 |
| `02-config-files/` | 配置文件（.modinfo/.civ6proj/Art.xml 等）格式 | 手写/检查配置文件时 |
| `03-project-file/` | 工程文件规范 | 工程结构问题 |
| `04-lua/` | Lua 技能（GP/UI 脚本、API、事件） | **自定义文件通道写 Lua 时**（`modgen custom-file` / `project_file_write`） |
| `05-modtools-civ/` | ModTools5.4 .CIV 工作流（INDEX/pipeline/格式/陷阱） | 做 .CIV 工程时（配合 `modgen/AGENTS.md`） |
| `07-techniques/` | 技巧与实战经验（效果实现、DB 验证等） | "某个效果怎么做"时 |

## 查询方式（AI 与人都用）

```bash
python -m modgen.cli skill <关键词>            # 全文检索：文件名+内容词频评分，命中文件+片段
python -m modgen.cli skill <关键词> --file <相对路径>   # 输出命中文件全文
python -m modgen.cli skill <关键词> --limit 20
```

- 查询优先：效果/能力实现 → `modgen search`（游戏库）；**模板/写法/工作流 → `modgen skill`（本目录）**；
  表结构/字段 → `modgen query`；LOC 文本 → `modgen loc`。
- **单一知识源**：知识只存本目录（与 `AGENT.md`/`modgen/AGENTS.md` 同源分工）。禁止把知识复制进对话或临时文件，需要时用 `skill --file` 现查现读。
- 文件内容里若出现历史遗留的外部绝对路径（如 `D:\文明6mod用文件夹\...`、`reference/...`），以本仓库相对路径与工具内置能力为准。

## 维护约定

- **跨 EffectType 的通用规则**写进 `07-techniques/modifier-techniques.md`（技巧 1/2/3…）；**每个 EffectType 的参数**才写进 `07-techniques/modifiers/modifier-<分类>.md`。
  通用规则必须在三处留入口，否则等于没写：`07-techniques/modifiers.md`（SQL 步骤表）、`07-techniques/modifiers/patterns/pre-code-checklist.md`（写码自检）、`05-modtools-civ/civ-pitfalls.md`（.CIV 落地自检）。
- **`_` 前缀 = 非知识文件**：生成脚本、查询脚本、中间产物（如 `_generate_final.py`、`_modifier-city.md.effects.txt`、`_trace_result*.txt`）一律用 `_` 开头 —— 检索引擎会跳过这些路径（`ModTools_5_4/skills_search.py::_is_dev_artifact`），避免它们把真正该读的文档挤出结果前列。新增此类文件请沿用 `_` 前缀。
- **生成式文档**（如 `07-techniques/modifiers/modifier-unit-combat.md`）由同目录 `_*.py` 脚本产出：改内容要**改脚本模板并重新生成**，只改产物会被下次生成覆盖；模版占位符统一 `{1_Amount}`。

