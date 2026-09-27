# 修改器实现前清单

适用于 .CIV 修改器和自定义 SQL 补丁。先读 [规则正文](../../../RULES.md)、[修改器指南](../../../05-modtools-civ/modifiers.md)。不要求开发机必须安装某个历史 Mod。

## 1 查证来源

- [ ] 已读最接近的 [模式](INDEX.md) 或 [案例](../cases/INDEX.md)，说明本任务沿用什么、改变什么。
- [ ] ModifierType 对照随包原版快照；其他 Mod 中使用过只能作为线索，不能当作原版依据。
- [ ] 新类型确有必要，CollectionType/EffectType 已核实，并确认工具将生成 Types/DynamicModifiers 注册。
- [ ] RequirementType 与参数已按 [资料依据](../../../SOURCES.md) 核实；搜索无结果时没有直接编造类型。

## 2 建立链路

- [ ] 原生表、布尔条件和逐来源 ATTACH 已先检查；线性计数没有无故改成 Lua 扫描 + req property。
- [ ] 二进制每种效果分别登记最高位、总上限与超限处理，不套 16/31 位万能列表；定义、条件、Lua 和所有者绑定范围一致。
- [ ] 列出外层/内层 Modifier、条件集、Ability 及挂载表；ATTACH 的 ModifierId 和 GrantAbility 的 AbilityType 指向真实条目。
- [ ] 分别说明 owner / subject 指向哪个游戏对象，玩家、城市、地块条件使用正确上下文。
- [ ] 事件类 Requirement 按真实语义填写 Triggered；不把 Inverse 与 Triggered 当作可互换的列。
- [ ] 主内容用工具骨架；特殊 SQL 显式写列名并对照表结构，通过自定义文件通道注册。

## 3 文本与验证

- [ ] 每个 `EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER` 必写 `preview_text`；工具输出 ModifierStrings 和对应 LOC。
- [ ] 占位符 `{1_Amount}`（固定数值）/ `{Property}`（Key 属性）正确，不能照抄旧模板的 `{Amount}`。
- [ ] 其他效果不机械添加 ModifierStrings；支持范围见 [通用技巧](../../modifier-techniques.md)。
- [ ] validate、相关预览与自定义 SQL 的 check-conflicts 已执行；结构校验与游戏内效果分别说明。
