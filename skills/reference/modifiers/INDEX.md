# Modifiers 参考索引（reference/modifiers）

> 受众：需要选 EffectType / Requirement、核对参数或找实现模式的制作者 ｜ 何时读：写 Modifier、排查效果不生效、选择原生类型时 ｜ 适用版本：ModTools 5.4

ModifierType 优先复用符合语义的原版；自定义类型必须同时注册 EffectType 与 CollectionType（见 [规则正文](../../RULES.md) R3/R4）。本目录分三层：方法与索引、EffectType 分册、实现模式与案例。

## 方法与索引

- [techniques.md](techniques.md) — Modifier 通用技巧：ModifierStrings 必写、参数占位、常见误区。
- [effect-index.md](effect-index.md) — EffectType 概念映射、强制查类型流程、完整 INSERT 链路。
- [patterns/pre-code-checklist.md](patterns/pre-code-checklist.md) — 实现前清单（写 Modifier 前先过一遍）。

## EffectType 分册

> 每个 `modifier-*.md` 已按主题拆成分册并保留为索引：先看索引的分册清单与触发条件，再按需读取对应分册；不要整目录通读。

- [modifier-unit-combat.md](modifier-unit-combat.md) — 单位战斗/属性/移动/经验/间谍/旅游/宗教/视野。
- [modifier-misc.md](modifier-misc.md) — 其余杂项：环境、时代、科技文化、忠诚、战争、奇观等。
- [modifier-diplomacy.md](modifier-diplomacy.md) — 外交、影响力、使者、不满、议程、外交状态。
- [modifier-district-building.md](modifier-district-building.md) — 区域/建筑产出、生产、购买、授予。
- [modifier-trade.md](modifier-trade.md) — 商路产出、容量、城邦/同盟商路。
- [modifier-religion.md](modifier-religion.md) — 信仰/信条、宗教传播与压力、宗教战斗。
- [modifier-greatpeople.md](modifier-greatpeople.md) — 伟人点数、巨作、伟人授予。
- [modifier-city.md](modifier-city.md) — 城市成长、住房、宜居、忠诚、城防。
- [modifier-yield.md](modifier-yield.md) — 产出修改。
- [modifier-resource.md](modifier-resource.md) — 资源/奢侈/战略/电力。
- [modifier-improvement-plot.md](modifier-improvement-plot.md) — 改良/地块/地形。
- [modifier-policy-government.md](modifier-policy-government.md) — 政策卡/政体/槽位。
- [modifier-governor.md](modifier-governor.md) — 总督。
- [modifier-alliance.md](modifier-alliance.md) — 同盟。
- [modifier-unit-spawn.md](modifier-unit-spawn.md) — 单位生成/复制/授予能力。
- [modifier-attach.md](modifier-attach.md) — ATTACH_MODIFIER 链式机制。

## 实现模式与案例

- [patterns/INDEX.md](patterns/INDEX.md) — 可复用实现模式（范围挂载、逐级遍历、区域效果等）。
- [cases/INDEX.md](cases/INDEX.md) — 历史 Mod 实现案例（线索，需在当前环境核实）。
