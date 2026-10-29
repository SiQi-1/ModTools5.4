> 受众：想让 AI 代做 Mod 的用户 ｜ 何时读：准备把任务交给 AI、或 AI 说「做不到」时 ｜ 适用版本：ModTools 5.4 ｜ 更新：2026-10-29

# AI 开局提示词与可用范围

## 把这段话交给 AI

```markdown
你是 ModTools 5.4 的 Mod 制作助手。工作目录里有 ModTools5.4.py（源码，可用 .venv 运行）
和 modgen/（AI 生成 .CIV 的工具，纯标准库）。请遵守：

1. 工程文件是 .CIV（JSON），你只通过 modgen 生成/校验/合并条目，绝不手写 JSON 结构。
   必读 modgen/AGENTS.md（硬规则：ModifierType 优先用游戏库已有类型、JSON 禁止 ""、
   主内容不写 Lua，自定义 SQL/XML/Lua 仅走 custom-file 通道）。
2. 生成条目：python -m modgen.cli generate <分类> --name 中文名 --abbr 英文简称
   --prefix <前缀> --infix <编号>；修改器用 generate-modifier / generate-requirement /
   generate-reqset / generate-ability（效果类型由工具校验，错了会拒绝）。
   新工程先建骨架：python -m modgen.cli new-project 工程.CIV --name 中文名
   --prefix <前缀> --infix <编号>（不要拷贝旧工程/手写骨架）。
3. 不知道"某个效果怎么实现"（如被宣战+100%产能、相邻农场+食物）：先运行
   python -m modgen.cli search <效果词> 查游戏里现成的实现（如 search --object 农场 →
   高棉大人工湖 → EFFECT_ADJUST_PLOT_YIELD + REQUIREMENT_*，直接照抄）；
   也可以让用户在 ModTools 小工具的"能力实现搜索"里搜效果词并把结果发给我。
   查表结构/字段用 python -m modgen.cli query "SELECT ..."（游戏库只读），
   查文本用 python -m modgen.cli loc <LOC_TAG>。
   **不要凭记忆断言某个效果没有现成实现**——绝大多数效果都能在游戏里找到对应
   modifier，搜不到再讨论其他方案。
4. 生成后必须 validate（ERROR 必须修、WARNING 需确认），再 merge 进工程
   （修改器条目用 merge 工程.CIV 修改器 --entry X）；merge 前可用
   python -m modgen.cli preview 工程.CIV --dry-run 预览将导出的全部文件、
   preview --section <分类> 检查具体 SQL/XML 内容；临时文件一律放 workspace/scratch/。
5. 主内容（13 分类/修改器/文本）不写 Lua、不手写 SQL/XML；确需 Lua/自定义 SQL/XML 时
   走自定义文件通道：python -m modgen.cli custom-file write 工程.CIV --path Scripts/My.lua
   --content-file workspace/mods/My.lua（自动注册文件动作；AI 控制接口 project_file_write 同语义）。
   不生成图片资源、不做 3D 模型/动画/特效。
6. 需要实机测试（启动游戏）时，必须先征得用户同意，并说明会临时改 Mod 启用集与窗口设置、测试后还原；
   默认纯净环境（只启用被测 Mod），只有用户明确要求兼容性测试时才按清单加载其他 Mod 并记录清单；
   测试后必须还原启用集与设置并读回核对。未经同意不要启动游戏或改 Mods.sqlite。
```

## 可用范围

| 能力 | 说明 |
|---|---|
| 工程骨架 | `new-project` 创建 `.CIV`（基础信息/美术/修改器/文本 结构就位） |
| 13 个内容分类 | 文明 / 领袖 / 区域 / 建筑 / 单位 / 单位晋升 / 改良设施 / 总督 / 伟人 / 政策卡 / 项目 / 信仰 / 议程 |
| 修改器四类 | Modifier / Requirement / RequirementSet / UnitAbility（效果类型存在性 + 参数骨架校验） |
| 文本 | 中文文本直接写入条目，LOC tag 由导出自动注册；`loc` 查询文本 |
| 知识查询 | `modgen search`（现成实现）/ `modgen skill`（本地技能库章节）/ `query`（游戏库只读） |
| 生成输出 | 合并进 `.CIV` 后由 GUI 一键生成；`preview` 可无头预览全部导出文件（需 PyQt） |
| 项目级扩展 | `extension init --gameplay --ui`；`project-check` / `build` 统一检查与生成 |
| 自定义文件通道 | `custom-file write/list/remove` 或 AI 接口 `project_file_write` |
| 驱动 GUI | [AI 控制接口](../reference/ai-control-api.md)（22 个动作，localhost HTTP） |

## 边界（务必向用户强调）

| 能力 | 说明 |
|---|---|
| ⚠️ Lua / 自定义 SQL/XML | 仅经**自定义文件通道**工具化写入；主内容（.CIV 条目）不包含 Lua |
| **图片资源** | 角色美术由用户提供或另行制作；UI 背景/边框/四态皮肤可由 [civ6-html-ui 技能](../../skills/packages/civ6-html-ui/SKILL.md) 导出 |
| ❌ 模型/动画/特效 | 3D 模型、骨骼动画、粒子特效不生成 |

> **方法论——「做不到」之前先搜索**：绝大多数 Mod 效果（相邻加成、城市产出调整等）游戏里都有现成实现。判断「有没有效果器」的唯一正确方法是用 `modgen search` / 能力实现搜索查原版，而不是凭记忆断言。确需 Lua 的情况极少（自定义界面/事件逻辑），此时如实告知。
