# modifier-unit-combat -- 单位战斗/属性/移动/经验/间谍/旅游/宗教等 EffectType — 注意事项

> 分册：由 [modifier-unit-combat.md](modifier-unit-combat.md) 按主题拆出；覆盖 注意事项、统计、SPECIAL: EFFECT_ADJUST_UNIT_PROPERTY、SPECIAL: GRANT_STRENGTH_PER_ADJACENT_UNIT_TYPE、战斗力类效果的 ModifierStrings、常见枚举值速查。触发：实现前核对通用注意点时。

## 注意事项

### 统计
- 总计 165 个通过 DynamicModifiers 注册的 EffectType
- 0 个 EffectType 在 DB 中无记录（可能为 MOD 专属或已废弃）

### SPECIAL: EFFECT_ADJUST_UNIT_PROPERTY

`EFFECT_ADJUST_UNIT_PROPERTY` 是通用单位属性修改 EffectType，其行为完全由 `Key` 参数决定。

该 EffectType 在官方数据库中无实际使用记录，Key 值由 MOD 自定义定义。

### SPECIAL: GRANT_STRENGTH_PER_ADJACENT_UNIT_TYPE

`GRANT_STRENGTH_PER_ADJACENT_UNIT_TYPE` 是少数**不带 `MODIFIER_` 前缀**的 ModifierType（直接以 `GRANT_` 开头），
用于根据相邻指定单位类型提供战斗力加成。参数：`Amount`（每单位加成量）、`UnitType`（指定单位类型）。

### 战斗力类效果的 ModifierStrings

`EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER` 必须填写预览文本，详见 [通用技巧](techniques.md)。不要按“战斗力/属性类”的名字把这条规则推广到其他 EffectType；基础战斗力效果与战斗上下文加成应区分。

### 常见枚举值速查

| 参数 | 枚举类型 | 常用值 |
|---|---|---|
| `UnitType` | Units | `UNIT_BUILDER`, `UNIT_SETTLER`, `UNIT_APOSTLE` |
| `PromotionClass` | UnitPromotionClasses | `PROMOTION_CLASS_MELEE`, `PROMOTION_CLASS_ANTI_CAVALRY`, `PROMOTION_CLASS_HEAVY_CAVALRY` |
| `UnitDomain` | `SELECT DISTINCT Domain FROM Units` | `DOMAIN_LAND`, `DOMAIN_SEA`, `DOMAIN_ALL` |
| `MilitaryFormationType` | MilitaryFormations | `CORPS_MILITARY_FORMATION`, `ARMY_MILITARY_FORMATION` |
| `YieldType` | Yields | `YIELD_GOLD`, `YIELD_FAITH`, `YIELD_CULTURE`, `YIELD_SCIENCE` |
| `OperationType` | UnitOperations | `UNITOPERATION_SPY_GREAT_WORK_HEIST`, `UNITOPERATION_SPY_RECRUIT_PARTISANS` |
| `Type` (回血) | — | `ALL`, `FRIENDLY`, `NEUTRAL`, `ENEMY` |
