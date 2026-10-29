> 受众：贡献者 ｜ 何时读：追溯该决策的背景与后果、或准备推翻它时 ｜ 适用版本：ModTools 5.4 ｜ 更新：2026-10-29
# ADR-0001：自定义 ModifierType 注册由原版快照驱动
**状态**：已采纳（2026-09）｜ **取代**：本机运行库启发式

## 背景
判断某个 `ModifierType` 是否需要自建 `Types` + `DynamicModifiers` 行时，早期实现读本机 `DebugGameplay.sqlite`。该库也包含本机已装 Mod 注册的类型，导致「本机判定为原版、换机后 Mod 加载失败」的静默错误。

## 决定
以随源码分发的原版快照 `ModTools_5_4/data/vanilla_modifier_types.json`（989 条，由 `python -m modgen.tools.extract_vanilla_modifier_types` 从游戏 XML 提取）为唯一判据。判定顺序：条目覆盖字段 `modifiers[].modifier_type_source`（null 自动 / `"new"` 强制注册 / `"vanilla"` 强制跳过）→ 快照 → 快照缺失时的旧启发式。GUI（`project/vanilla_modifier_types.py`）与 modgen（`modgen/vanilla_types.py`）共用同一 JSON，SQL 与 XML 两条生成路径共用 `_custom_modifier_type_map()`。

## 后果
- 换机/少装 Mod 不再漏注册；`modgen/modifier_validator.py` 对「强制新建却属原版」「强制已有却不在快照」报 ERROR。
- 游戏版本更新后需重跑提取脚本更新快照，否则新类型会被误判为自定义。
