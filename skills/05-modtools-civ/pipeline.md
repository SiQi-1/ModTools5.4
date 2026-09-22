# 单会话流水线：CIV + 补丁一体化（pipeline）

> **为什么需要**：.CIV 只能表达"表数据 + 标准 Modifier"。特殊 SQL（SELECT/UPDATE/自定义表）与 Lua 动态逻辑无法用 .CIV 表达。
> 因此完整 Mod 交付 = **写 .CIV → 无头导出 → 手写补丁**，本文件定义这条链路在**一个会话内**完成。
> 配套脚本：`export_modtools.py`（无头导出，已用 52.CIV 实测：23 文件全量生成，与 GUI 导出逐字节一致）。

## 能力边界矩阵（需求拆分依据）

| 需求类型 | 能否 .CIV | 去向 |
|---------|----------|------|
| 文明/领袖/区域/建筑/单位/晋升/改良/总督/伟人/政策/项目/信仰/议程 实体 | ✅ | `.CIV` 17 section（entity-templates/） |
| 标准 Modifier/Requirement/ReqSet/Ability（EffectType 库内） | ✅ | `.CIV` 修改器 section（modgen generate-* 校验类型存在性） |
| 文本/图标/配色/ArtDef/XLPs/工程文件 | ✅ | `.CIV` 基础信息/文本/美术 section |
| **特殊 SQL**：`INSERT...SELECT` 继承、`UPDATE`、自定义表、条件迁移 | ❌ | **补丁 SQL**（本工作流第 4 步） |
| **Lua GP/UI**：事件、动态数值、UI 面板、Import 脚本 | ❌ | **Lua 补丁**（工作流 C/D） |
| 复杂触发（首次抵达、多步交互） | ❌ | Lua 补丁（工作流 C 事件模式） |

> 工具硬边界：**ModTools 不生成 Lua**（工具 AGENT.md 契约）。需求涉 Lua → 交付方案必须含补丁步骤，提前告知用户。

## 流水线（6 步，全部在会话内）

```
┌─ 1. 需求拆分（能力边界矩阵）→ 产出"补丁清单"
├─ 2. 写 .CIV → D:\文明6mod用文件夹\ModTools5.4\<工程名>.CIV
│     modgen generate（条目骨架）→ 按 entity-templates 填内容 → merge/validate
│     出口：check_civ.py 通过；modgen validate 无 ERROR
├─ 3. 无头导出（会话内）：
│     D:\文明6mod用文件夹\ModTools5.4\.venv\Scripts\python.exe export_modtools.py --civ <工程.CIV>
│     → 全部 SQL/XML/ArtDefs/XLPs/.civ6proj 写入 ModBuddy 工程（civ6proj_path）
├─ 4. 手写补丁（针对补丁清单）：
│     a. 特殊 SQL → ModBuddy 工程 Data/<ModName>_Patch.sql（独立文件，工具不覆盖）
│     b. Lua GP/UI → Scripts/ UI/（工作流 C/D 规范），UI 文件成对（陷阱 10）
│     c. 图片资源 → 放工程 IMG/（工具图片计划生成，或 GUI 生成）
│     出口：再次运行导出（工具识别 custom 文件并注册进 .civ6proj Actions）；
│           若注册缺失，按 03-project-file/civ6proj.md 手工补 AddUserInterfaces/UpdateDatabase/ImportFiles
├─ 5. 统一出口检查：
│     python check_civ.py <工程.CIV>            （.CIV 结构）
│     python -m modgen.cli validate <工程.CIV>   （条目合规，在 ModTools5.4 目录跑）
│     python modcheck.py <ModBuddy 工程全部 SQL>（工具产物 + 补丁的 Type 存在性，❌ 清零）
│     工作流 C/D 的 Lua 出口检查（事件/环境隔离/控件对应）
└─ 6. 交付 + 回流：新坑记 memory/ → 并入本目录模板
```

## 补丁模式（第 4 步细节）

### a. 特殊 SQL 补丁（自定义文件通道）

- 位置：`Data/<任意名>.sql`（**独立文件**，不要改工具生成的 `Data/<ModName>_*.sql`——下次生成会覆盖）
- 写入：`python -m modgen.cli custom-file write 工程.CIV --path Data/<名>.sql --content-file modgen_work/<名>.sql`
  （自动注册 UpdateDatabase，**load_order=10000** —— 永远在生成数据 9999 之后执行；AI 接口 `project_file_write` 同语义）
- **何时用 SELECT**（合法模式，check-conflicts 不告警）：
  - `INSERT...SELECT` 显式继承：CityNames/CitizenNames（模板 `01-core-tables/civilization.md` §SELECT 复制官方）；
  - 自定义表建表 + `INSERT...SELECT` 数据迁移/填充（数据驱动模式见 `04-lua/lua-workshop-misc-custom-sql-tables.md`）；
  - 跨表条件迁移（如 BeliefModifiers 遍历信条，`07-techniques/modifiers/cases/case-attach-chain.md`）；
  - **批量挂载到原版对象**：如世界奇观效果
    `INSERT INTO BuildingModifiers (BuildingType, ModifierId) SELECT BuildingType, '<ModifierId>' FROM Buildings WHERE IsWonder = 1;`
    （**不要手抄奇观清单**，清单随资料片/DLC/其他 Mod 变化；奇观为什么必须挂建筑而不是 `DISTRICT_WONDER` 区域，
    见 `07-techniques/modifier-techniques.md` 技巧 4）。
- **需要更晚的加载顺序时**（如上面的遍历要求资料片/其他 Mod 数据就位）：给**独立动作 id + `LoadOrder 199999`**。
  注意 `custom-file write` 自动注册的动作 id 就是类型名 `UpdateDatabase`（load_order 10000），而注册按
  **(type, id)** 合并 —— 同 id 会被并进原组、拿不到自己的顺序；且要确认该文件没留在原组，否则执行两次（主键冲突）。
  可用 AI 接口 `add_file_action`（带 `load_order`）注册。
- **协调规则（红线，检测工具 `modgen check-conflicts`）**：
  1. **同表同主键禁止双写**：生成 SQL 已插入的行，自定义 SQL 不得再 INSERT（= ERROR，游戏加载主键冲突）。
     要改生成内容 → **回 .CIV 改对应条目**（工具是唯一写入者）；
  2. **UPDATE/DELETE 生成 SQL 写过的表 = 反模式**（= WARNING）：下次生成覆盖回退。
     确需覆盖个别值用 `INSERT OR REPLACE` 改写行；
  3. 检测：`python -m modgen.cli check-conflicts 工程.CIV [--json]`（ERROR 必须清零，WARNING 需确认；
     AI 接口同款动作 `check_conflicts`）。
- 分工口诀：**.CIV 管"新增实体/标准效果"；自定义 SQL 只做"SELECT 继承/自定义表/增量补行"**。

### b. Lua 补丁
- GP：`Scripts/*.lua`（Import 事件脚本 → `Import/`）；UI：`UI/*.xml + *.lua` 成对；写入同走 `custom-file` 通道
- 规则全部走 `04-lua/`：环境隔离（陷阱/规范）、事件注册表选择、`LoadGameViewStateDone` 包裹
- UI 面板引用工具生成的实体数据：`GameInfo` 查询 + `LOC_` 键全部由工具导出（文本在 `Text/<ModName>_Text_CN.sql`），Lua 里直接引用

### c. 二次导出与 custom 文件机制（已验证）
- 工具 `_project_root_manifest` 会扫描 ModBuddy 工程中**非生成清单**的文件（`_collect_external_project_files`），识别为 custom 只读文件：
  - 生成时**不会覆盖**它们（`_readonly_custom_paths`）
  - 会合并进生成的 `.civ6proj` Actions 注册（`custom_project_files_provider`）
- 因此流程固定为：**导出 → 放补丁 → 再导出**（第二次导出把补丁注册进 civ6proj）

### d. 双端同步：ModBuddy 工程目录 × 游戏 Mods 目录（0055 实测）
工具只写 **ModBuddy 工程目录**（`.CIV` 里 `civ6proj_path` 指向的那个），游戏实际读的是
`文档\My Games\Sid Meier's Civilization VI\Mods\<工程名>\`。**两端都要改**，否则实机测的还是旧内容。

| 改动类型 | ModBuddy 端（工具写） | Mods 端（同步动作） |
|---|---|---|
| 生成文件（Data/Text/Icons…） | `--ai-exec generate_all` 全量重写 | **逐文件比对哈希**，只复制 DIFF 的（全量覆盖也行，但别漏文件） |
| 新增自定义 SQL | `custom-file write --no-action` → `add_file_action`（独立 id + `load_order`）→ **`save_project`** → `generate_all` | 复制 SQL 到 `Data/`，并在 `.modinfo` 的 `InGameActions` 加**同 id、同 LoadOrder** 的动作块，`<Files>` 加一行 |
| 美术（ArtDefs/XLPs/IMG/BLP） | ArtDefs/XLPs/IMG | 需要 ModBuddy Build（BLP/Cooker），工具不管 |

- `.civ6proj` 的 `UpdateArt` 文件是占位符 `(Mod Art Dependency File)`，`.modinfo` 里是构建后的真实 `.dep`（如 `LOC_SIQI_LEADERS_0055_NAME.dep`）—— 这条差异是**正常**的，不算不同步。
- 校验思路（脚本化）：解析 `.civ6proj` 的 `InGameActions`/`FrontEndActions` CDATA 与 `.modinfo` 对应块，
  比对 (类型, id, LoadOrder, 文件列表)；再检查"动作引用的文件都在 `<Files>` 里、且磁盘存在"。
- ⚠ `add_file_action` 只改内存：**不 `save_project` 就退出，动作会丢**（下次 `generate_all` 后消失，症状是 `.civ6proj` 里没有该动作块）。

## 验证命令速查（全部为 ModTools5.4 仓库内置，不依赖外部脚本）

| 命令 | 验证什么 |
|------|---------|
| `python -m modgen.cli validate <工程.CIV>` | 条目合规（ERROR 必清） |
| `python -m modgen.cli preview <工程.CIV> --dry-run` | 将导出文件清单/内容（无头生成引擎） |
| `python -m modgen.cli check-conflicts <工程.CIV> [--json]` | 自定义 SQL × 生成 SQL 冲突（主键双写=ERROR / UPDATE 生成表=WARNING） |
| `python -m modgen.cli skill <关键词>` / `search <效果词>` | 模板/写法知识 / 游戏库现成实现 |

> 历史外部脚本（`check_civ.py`/`modcheck.py`/`export_modtools.py`）属外部工作区，本仓库不依赖；
> 其等价内置能力 = 上表 + `modgen query`（SQL 类型/引用对照查表）。

## 落盘门禁方法论（导出产物 + 自定义补丁后人工/脚本复核；经验保留）

1. **Type 存在性**：引用列值对照 DB 查表（`modgen query "SELECT Type FROM Types WHERE Type='X'"` 逐项核对）
2. **模拟加载**：临时库 executescript 逐句执行（需 `create_function("Make_Hash", 1, fnv1a)` 模拟游戏 UDF）；注意块注释内分号切分；已知噪音：PlayerColors 无 Alt 列、Players/PlayerItems 无表（FrontEnd 库）、无扩展 schema 下 Units_XP2 等无表
3. **重复/占位扫描**：同表主键跨文件重复（含自定义文件）→ 内置 `check-conflicts`；`'0'` 占位行（正确形态：不取代=不写行、战斗单位不写 UnitCaptures、无资源单位 XP2=(0,0)）
4. **引用列对照**：模拟加载看不到游戏侧引用校验（非法值进游戏才报 Invalid Reference），对插入的引用列值逐项核对查表

## 会话外仍需人工的（诚实边界）

- 图片资源（PSD 处理/最终贴图）——工具图片计划需要源图，GUI 生成或用户提供
- 部署：`.modinfo`（下期工具内置；当前 ModBuddy Build 或手写模板）+ 含美术 Mod 的 Cooker 烘焙
- `.civ6proj` 的 `<CompatibleVersions>`/作者信息等发布前复核
