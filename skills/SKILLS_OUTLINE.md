# Skill 体系现状架构图

> 本文件是 `skills/` 目录的**现状地图**（非规划）。新增/移动 skill 文件后必须同步本图与对应 INDEX。

## 目录结构

```
skills/
├── 06-naming.md              # 代码规范（命名/文件命名）
├── district-adjacency.md     # 相邻加成（区域/改良共用）
│
├── 01-core-tables/           # 实体定义（SQL 模板）—— 入口: INDEX.md
│   ├── civilization.md / leader.md / district.md / building.md / unit.md
│   ├── improvement.md / governor.md / policy.md / project.md
│   ├── greatperson.md / agenda.md / government.md / belief.md
│
├── 02-config-files/          # 配套注册文件（XML/SQL）
│   ├── configs.md（Players/PlayerItems）/ colors.md / icons.md
│   ├── text.md / diplo-text.md
│
├── 03-project-file/          # 工程文件
│   └── civ6proj.md（.civ6proj / .modinfo）
│
├── 04-lua/                   # Lua 全部知识 —— 入口: INDEX.md（唯一权威索引）
│   ├── code-style.md         # 环境隔离/命名/通信规范
│   ├── lua-gp-*.md           # GP 函数库（combat / resource）
│   ├── lua-binary.md         # 二进制 Property 系统
│   ├── lua-xml-controls.md   # ForgeUI 控件属性表
│   ├── lua-ui-button.md      # 按钮模版
│   ├── lua-00xx-*.md         # 自有 Mod 系统（18 个，按 Mod 编号）
│   ├── lua-19-fever-system.md
│   ├── lua-workshop-*.md     # 工坊 Mod 模式（109 个，按面板/机制分类）
│   └── INDEX.md              # ★ 137 个文件的唯一索引，新增必登记
│
├── 05-modtools-civ/          # ModTools5.4 .CIV 工程 —— 入口: INDEX.md
│   ├── pipeline.md           # 单会话流水线（能力边界 + 无头导出 + 补丁模式）
│   ├── civ-project-format.md # .CIV 结构（17 section / dict vs list）
│   ├── civ-pitfalls.md       # 工具契约 + 合并必炸清单
│   └── entity-templates/     # 13 个实体模板（桥接 01/02/07 技能 → .CIV 条目）
│       └── INDEX.md          # 实体模板地图（新增必登记）
│
└── 07-techniques/            # 技巧 Cookbook
    ├── modifiers.md          # Modifier 总纲（概念映射：想做什么→EffectType）
    ├── modifier-techniques.md# 跨 EffectType 通用技巧
    └── modifiers/            # 17 个分类文件 + patterns/ + cases/
        ├── modifier-*.md     # EffectType 分类参考（按 ### 每类型一节）
        ├── patterns/INDEX.md # 7 种实现模式（含列序/链路/参考Mod）
        ├── patterns/pattern-*.md
        ├── cases/INDEX.md    # 40+ Mod 真实案例（Grant Ability/Yield/ATTACH…）
        └── cases/case-*.md
```

## 命名规则

| 前缀 | 含义 | 登记位置 |
|------|------|----------|
| `lua-workshop-*` | 工坊 Mod 模式（带来源工坊 ID） | 04-lua/INDEX.md |
| `lua-00xx-*` | 自有 Mod 系统（Mod 编号） | 04-lua/INDEX.md |
| `lua-gp-*` | GP 环境函数库 | 04-lua/INDEX.md |
| `modifier-*` | EffectType 分类（07-techniques/modifiers/） | modifiers/ 内自然分组 |
| `pattern-*` | 实现模式（07-techniques/modifiers/patterns/） | patterns/INDEX.md |
| `case-*` | 真实案例（07-techniques/modifiers/cases/） | cases/INDEX.md |

## 铁律（与 AGENTS.md §4/§8 一致）

1. **新增文件必须登记**到对应 INDEX（04-lua/INDEX.md、01-core-tables/INDEX.md、patterns/INDEX.md、cases/INDEX.md）——不登记 = 不存在
2. **单一知识源**：同一知识只存一处；skill 内引用 reference/ 用 `../../reference/`（01-core-tables 层级）或对应相对路径
3. **来源标注**：工坊模式在标题注明来源 Mod ID；自有系统注明 Mod 编号
4. **过时规划即删除**：本文件只描述现状，不做规划

## 与工具层的关系

| 工具 | 职责 | 与 skills/ 的关系 |
|------|------|------------------|
| `lua_api.py` + `reference/lua-api/` | 接口/事件/枚举/条件的机械查询 | skills/ 是**已验证模式**层，优先于工具 |
| `modcheck.py` | Modifier SQL 类型存在性验证 + `--audit` 全库回归 | 写 SQL 后必跑；audit 防止 skill 再次漂移 |
| `dll-reference/extract_types_from_dll.py` + `reference/dll_types.txt` | **DLL 硬编码类型全集**（RequirementType 327 个，权威源） | Requirement 验证的三重并集之一（DLL ∪ CSV ∪ DB） |
| `reference/csv-export/` | 原始数据 | skill 的素材源，不直接面向 AI 查询 |
| `reference/modtools-civ/` | ModTools5.4 schema 快照（钉 commit） | 05-modtools-civ 的字段权威源，`sync_modtools.py` 独占更新 |
| `sync_modtools.py` | 同步快照 + 差异报告 + MANIFEST 更新 | ModTools5.4 更新后必跑；防 skill 漂移 |
| `check_civ.py` | .CIV 出口检查（结构 + 禁 `""`） | 写完 .CIV 后必跑（工作流 I） |
| `export_modtools.py` | **无头导出** .CIV → SQL/XML → ModBuddy（offscreen + 交互补丁） | 单会话流水线第 3 步；用 ModTools5.4 的 .venv python 跑 |
| `memory/` | 踩坑反馈 | 新坑先记 memory，后并入 skill 模板 |
