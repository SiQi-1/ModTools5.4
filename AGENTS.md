# AGENTS.md — 本仓库任务路由（先读本文件）

> 本仓库是《文明6》Mod 编辑器 **ModTools 5.4** 的源码仓库，同时承载两种目的：
> - **A 实际应用**：用 ModTools / modgen 制作文明6 Mod、编写/修改 `.CIV` 工程文件、回答文明6 Mod 制作问题；
> - **B 工具优化**：开发/改进 ModTools 本身（GUI、modgen、测试、打包、文档）。
>
> **先判断你的任务属于哪个目的，再按下方清单读对应文档**——不要把所有根目录文档都通读一遍，
> 也不需要读与你目的无关的文件。

## 目的 A：实际应用（做 Mod / 写 .CIV / 答 Mod 问题）

任务特征：出现"生成/修改 .CIV、做文明/领袖/单位/区域、某个效果怎么实现、这个 Mod 怎么做、帮我把 XX 做进游戏"等。

必读（按序）：

1. **[skills/RULES.md](skills/RULES.md)** —— 唯一制作规则正文；无论是否熟悉都要读。
2. **[skills/WORKFLOW.md](skills/WORKFLOW.md)** —— 统一流程；按 `modgen skill "任务描述" --plan` 读取任务必读资料。
3. **[modgen/AGENTS.md](modgen/AGENTS.md)** —— 当前命令与字段契约。

`AGENT.md` 保留兼容入口；同会话已读且未变化的资料可复用。实现前简短注明所用文件/章节与待验证项。

其余按需：`README.md`「AI 生成 .CIV」章节（开局提示词，给人/AI 的摘要）、`CIV6_MOD_TUTORIAL.md`（全流程教程，人读为主）。

## 目的 B：工具优化（改 ModTools 本身）

任务特征：出现"改工具/加功能/修 bug、modgen 命令行为、生成器、预览、测试、打包、重构、文档优化"等。

必读（按序）：

1. **`CLAUDE.md`**（仓库根）——代码架构、关键设计决策、开发约定（文档同步、日志、测试）。
2. **`ModTools_5_4/docs/ROADMAP.md`** —— 当前 Done/TODO 状态（改功能前先看，避免重复/冲突）。
3. **`ModTools_5_4/CHANGELOG.md`** —— 功能历史；**每次功能改动必须在此记录**（最新条目在顶部）。
4. 改 `modgen/` 相关代码时，额外读 `modgen/README.md`（模块结构）与 `modgen/AGENTS.md`（**AI 使用契约**——工具行为必须服从它，改行为 = 改契约，需同步两边）。

## 目的 C：环境初始化（新设备）

- **`AGENT_SETUP.md`**（仓库根）——一键初始化任务书（setup_env / 手动配置 / 验证 / 排障）。

## 红线（无论哪个目的；涉及 .CIV 内容时一律适用）

- ModifierType / EffectType / RequirementType / CollectionType **优先引用游戏库已有类型**；确需新建必须同时写 `DynamicModifiers` 行；
- JSON 值**禁止写 `""`**（空值 → 省略字段或写 `null`）；
- 主内容（.CIV 条目）**不写 Lua、不手写 SQL/XML**（一切输出由工具从 .CIV 生成）；确需 Lua/自定义 SQL/XML 时走**自定义文件通道**（`modgen custom-file` / AI 动作 `project_file_write`，工具是唯一写入者）。
