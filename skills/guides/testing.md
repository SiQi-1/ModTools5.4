# 实机测试（可选阶段；启动游戏必须先经用户同意）

> 受众：需要游戏内验证的 AI 与制作人 ｜ 何时读：准备启动游戏做测试、复现或兼容性检查时 ｜ 适用版本：ModTools 5.4

本页是 [统一工作流](../WORKFLOW.md) 第 6 步的细则。只有需要游戏内效果、问题复现或第三方兼容性结论时才进入；`validate` / `preview` / 日志静态检查能确认的内容不启动游戏。执行手册见 [civ6-ai-play 技能](../packages/civ6-ai-play/SKILL.md)，行为规则见 [R6](../RULES.md#r6-验证与交付)。

## 1 同意门禁（硬性）

启动游戏、修改 `Mods.sqlite` 启用集或游戏显示设置前，必须先取得用户明确同意，并说明三件事：

1. 将启动游戏并可能占用窗口/显卡；
2. 会临时调整 Mod 启用集与窗口设置；
3. 会截图与读取游戏日志，测试结束后会还原。

未经同意不得启动游戏或改配置；只能做离线校验（validate / project-check / preview / 日志静态检查）。

## 2 环境基线

- 测试前确认游戏未运行；备份 `Mods.sqlite`、`AppOptions.txt`（必要时 `GraphicsOptions.txt`），备份名带时间戳。
- 记录当前启用集（Mod 名称与 ID）与备份路径；换机器或换游戏版本必须重新记录。
- 检查 Tuner 可用性预期（`EnableTuner 1`），但不提前改设置。

## 3 Mod 环境（默认纯净）

- **默认纯净环境**：停用其他 Mod，只启用被测 Mod，避免第三方 Mod 干扰归因。
- **兼容性测试**：只有用户明确要求时才按用户给出的清单一起加载，记录完整清单（名称/ID/版本）；结论必须注明「含第三方 Mod」，不能当作纯净环境结论。
- 同一时刻只允许一个 Tuner 客户端（MCP / 脚本直连 / 常驻桥 / FireTuner GUI 四选一）。
- 修改启用集只改所选组内的 `Disabled` 位，不新建或替换用户的 Mod 组；游戏运行时禁止写 `Mods.sqlite`。

## 4 执行与验收

按 [civ6-ai-play 标准流程](../packages/civ6-ai-play/SKILL.md#标准流程) 窗口化启动、选文明/领袖开局、执行操作、截图、读日志，并按 [验收分层](../packages/civ6-ai-play/SKILL.md#验收分层) 分开记录：

命令 → 连接 → 开局 → 操作 → Mod 生效 → 环境与视觉。

「能启动」「日志无错」不能替代「效果正确」；截图与日志放 `workspace/scratch/<任务名>/`，不写进工具仓库。

## 5 还原与一致性（硬性）

- 关闭游戏并等待进程退出；还原 Mod 启用集与显示设置。
- 读回核对 `Mods.sqlite` / `AppOptions.txt` 与测试前基线一致；清空或停用过的 Mod 必须恢复原启用集。
- 报告测试前/后启用集、本次加载的 Mod 清单、截图与日志位置、结论及未覆盖项。
- 技能仍在完善：缺失步骤按「技能未覆盖」记录，不得跳过备份/还原或修改游戏安装目录。

## 6 与其它文档的关系

- [统一工作流](../WORKFLOW.md)：第 6 步的入口与门禁摘要。
- [规则正文 R6](../RULES.md#r6-验证与交付)：实机测试的硬规则。
- [civ6-ai-play](../packages/civ6-ai-play/SKILL.md)：命令、脚本与排障。
- [Mod 测试方法](../packages/civ6-ai-play/references/mod-testing.md)、[Mod 测试工作流](../packages/civ6-ai-play/references/mod-test-workflow.md)：分层取证与判定标准。
