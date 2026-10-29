> 受众：贡献者 ｜ 何时读：追溯该决策的背景与后果、或准备推翻它时 ｜ 适用版本：ModTools 5.4 ｜ 更新：2026-10-29
# ADR-0002：文本预览不使用 DebugLocalization.sqlite
**状态**：已采纳

## 背景
游戏会生成 `DebugLocalization.sqlite`，但它不会随语言/游戏更新刷新，直接用会出现缺条目和过期文本，让中文预览与最终生成结果不一致。

## 决定
文本解析只使用自建文本库（源码自带 `local_text_New.sqlite`，可导入 DLC 文本）；`db/interface.py` docstring 明确记录「工具刻意不用 DebugLocalization」。未配置文本库时中文显示「未知」，不静默回退到其它库。

## 后果
- 首次使用必须配置文本库（见 [ADR-0005](ADR-0005-text-db-required.md)）。
- 预览与生成结果可复现；文本库更新由工具导入流程负责，不依赖游戏运行时。
