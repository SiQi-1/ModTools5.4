# INDEX — 05-modtools-civ（ModTools5.4 .CIV 工程）

> **这是什么**：用 ModTools5.4 生成 Civ6 Mod 的 AI 工作流知识。
> 分工：**本仓库 = 知识层**（游戏深度知识在此），**ModTools5.4 = 数据/能力层**（.CIV schema 上游 + 生成 SQL/XML 的工具）。
> 产物 `.CIV` 一律输出到 `D:\文明6mod用文件夹\ModTools5.4\`，由工具生成 SQL/XML 到 ModBuddy 工程。

## 何时用本 skill

- 用户要求"用 ModTools 做 Mod / 生成 .CIV 工程"（替代手写 SQL/XML 的 80% 工作）
- 用户给出 Mod 需求（文明/领袖/区域/建筑/单位/修改器效果/文本…）且**不涉及 Lua 动态逻辑**
- 工具边界：**ModTools 不生成 Lua**。需求涉 Lua/UI.xml → 告知用户该部分需本仓库工作流 C/D 手写

## 工作流（写 .CIV 并单会话交付）

> **完整流水线见 `pipeline.md`**（能力边界矩阵 + 6 步：需求拆分 → 写 .CIV → 无头导出 → 手写补丁 → 统一验证 → 交付）。此处为速览：

1. **确认版本** — 读 `reference/modtools-civ/MANIFEST.md`（钉住 commit）。schema 有更新时先跑 `python sync_modtools.py` 并读差异报告
2. **需求拆分** — `pipeline.md` 能力边界矩阵：可 .CIV 部分 vs 补丁清单（特殊 SQL / Lua）
3. **基础信息** — 读 `entity-templates/basic-info.md` 要点：prefix/infix/文件命名，后续所有 Type 命名的基础
4. **逐实体建条目** — 选 `entity-templates/<实体>.md`，逐字段对照；内容知识桥接本仓库现有技能：
   - 实体表字段 → `skills/01-core-tables/<实体>.md`（SQL 模板同源知识）
   - 修改器效果 → `skills/07-techniques/modifiers.md` 概念映射 + `modifiers/patterns/` 现成链路
   - 命名 → `skills/06-naming.md` + 本目录 `civ-pitfalls.md` §命名
   - 文本 → `skills/02-config-files/text.md`（LOC 引用链/图标嵌入）+ `reference/local_text_New.sqlite`（查已有中文）
   - 配色 → `skills/02-config-files/colors.md` + 快照 `data/standard_colors.json`
5. **写文件** — 输出到 `D:\文明6mod用文件夹\ModTools5.4\<工程名>.CIV`（UTF-8，`json.dumps(ensure_ascii=False, indent=2)`，沿用现有命名惯例：编号或英文名）
6. **无头导出 + 补丁** — `export_modtools.py` 会话内导出到 ModBuddy；补丁（特殊 SQL/Lua）按 `pipeline.md` 第 4 步；再次导出注册
7. **出口检查**（全部通过才交付）：
   - [ ] `python check_civ.py <文件.CIV>` — schema 可加载（硬）；`""` 空串为警告项，**AI 写的文件必须清零**（工具自身保存的占位空串不算）
   - [ ] `python -m modgen.cli validate <工程.CIV>` 无 ERROR（在 ModTools5.4 目录跑）
   - [ ] 所有 Type/ModifierType/EffectType/RequirementType 查过游戏 DB（AGENTS.md §2 数据源优先级）
   - [ ] 命名遵循前缀约定（`06-naming.md`）；无自创前缀
   - [ ] 无 Lua 内容写入 .CIV（工具边界）；Lua 需求已列入补丁清单并交付
   - [ ] 每个实体有图标字段（`icon_image_name` 等）与文本
   - [ ] 事件类 Requirement 有 `Triggered=1`（见 `civ-pitfalls.md`）
   - [ ] `modcheck.py` 对 ModBuddy 全部 SQL（工具产物 + 补丁）❌ 清零
8. **交付后** — 用户在 GUI 打开 .CIV 复核 → 打包 → 知识回流（新坑记 `memory/`，再并入本目录模板）

## 文件地图

| 文件 | 内容 |
|------|------|
| `pipeline.md` | **单会话流水线**（能力边界矩阵 + 6 步 + 补丁模式 + 验证命令） |
| `civ-project-format.md` | .CIV 整体结构（meta/workspace、18 section、dict vs list、UI图标段） |
| `civ-pitfalls.md` | 工具契约规则 + 合并后的必炸清单（禁 Lua/禁 `""`/Triggered…） |
| `entity-templates/INDEX.md` | 实体模板地图（各实体入口键 + 桥接技能） |
| `entity-templates/basic-info.md` | 基础信息 section（prefix/infix/命名根基） |
| `entity-templates/*.md` | 各实体模板（文明/领袖/区域/建筑/单位/晋升/改良/总督/伟人/政策/项目/信仰/议程） |

## 数据源（快照，钉 commit）

- `reference/modtools-civ/project/civ_project.py` — 18 section 顺序/形态（**禁止手改**，`sync_modtools.py` 独占）
- `reference/modtools-civ/data/effect_type_parameters.json` — EffectType 参数（写修改器必查）
- `reference/modtools-civ/data/font_icons_registry.json` — `[ICON_x]` 拼写权威源
- `reference/modtools-civ/data/standard_colors.json` / `text_color_presets.json` — 配色/文本色
- 样例工程：`D:\文明6mod用文件夹\ModTools5.4\*.CIV`（32.CIV 覆盖 12/17 个 section，字段级活样例）
