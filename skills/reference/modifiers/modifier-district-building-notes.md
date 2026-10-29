# modifier-district-building -- 区域/建筑产出/生产力/购买类 EffectType — 注意事项/速查

> 分册：由 [modifier-district-building.md](modifier-district-building.md) 按主题拆出；覆盖 相似效果对比、特殊参数提醒、枚举引用清单、命名审查、无官方实例的 EffectType。触发：实现前核对注意事项、溯源与枚举时。

## 注意事项/速查

## 相似效果对比

| 效果组 | EffectTypes | 关键差异 |
|---|---|---|
| 建筑生产力（固定值） | `EFFECT_ADJUST_BUILDING_PRODUCTION` / `EFFECT_ADJUST_CITY_PRODUCTION_BUILDING` | 前者按 BuildingType+DistrictType 指定目标，后者按文明特性（首都/区域/城市/文明专属）自动计算 |
| 建筑生产力（百分比） | `EFFECT_ADJUST_ALL_BUILDING_PRODUCTION_MODIFIER` | 百分比修饰，可限 IsWonder |
| 区域生产力（固定值） | `EFFECT_ADJUST_DISTRICT_PRODUCTION` / `EFFECT_ADJUST_CITY_PRODUCTION_DISTRICT` | 前者可指定 DistrictType，后者按文明特性计算 |
| 区域生产力（百分比） | `EFFECT_ADJUST_ALL_DISTRICT_PRODUCTION_MODIFIER` | 百分比修饰，作用于所有区域 |
| 区域产出（固定值） | `EFFECT_ADJUST_DISTRICT_YIELD_CHANGE` / `EFFECT_ADJUST_DISTRICT_BASE_YIELD_CHANGE` | BASE 修改区域基础产出，CHANGE 附加产出变化 |
| 区域产出（百分比） | `EFFECT_ADJUST_DISTRICT_YIELD_MODIFIER` | 百分比翻倍，政策卡核心机制 |
| 建筑产出（固定值） | `EFFECT_ADJUST_BUILDING_YIELD_CHANGE` | 按 BuildingType 指定建筑的固定产出增量 |
| 建筑产出（百分比） | `EFFECT_ADJUST_BUILDING_YIELD_MODIFIER` / `EFFECT_ADJUST_BUILDING_YIELD_MODIFIERS_FOR_DISTRICT` | 前者按建筑类型，后者按区域类型，粒度不同 |
| 宜居度 | `EFFECT_ADJUST_DISTRICT_AMENITY` / `EXTRA_ENTERTAINMENT` / `EXTRA_REGIONAL_ENTERTAINMENT` | AMENITY=全局宜居度，ENTERTAINMENT=本地娱乐值，REGIONAL=区域辐射 |
| 旅游业绩 | `EFFECT_ADJUST_DISTRICT_TOURISM_CHANGE` / `TOURISM_ADJACENCY_YIELD_MOFIFIER` | 前者直接加旅游业绩值，后者将相邻加成按比例转化 |
| 时代得分 | `EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_*_CONSTRUCTED`（5 个变体） | 参数完全相同（仅 Amount），差异仅在命名限制生效范围 |
| 免费建筑 | `EFFECT_GRANT_BUILDING_IN_CITY` / `EFFECT_GRANT_BUILDING_IN_CITY_IGNORE` | IGNORE 版本无视前置条件（如牛顿无需图书馆即可赠送大学） |
| 贸易路线（国内vs国际） | `FOR_DOMESTIC` / `FOR_INTERNATIONAL` | 专用于不同类型的贸易路线产出加成 |

---

## 特殊参数提醒

| EffectType | 特殊参数名 | 说明 |
|---|---|---|
| `EFFECT_ADJUST_DISTRICT_YIELD_BASED_ON_ADJACENCY_BONUS` | `YieldTypeToGrant` + `YieldTypeToMirror` | 需同时填写两个参数，仅复制已有相邻加成不为 0 的产出 |
| `EFFECT_ADJUST_DISTRICT_YIELD_BASED_ON_APPEAL` | `YieldChange` | 参数名非 `Amount`，配合 `RequiredAppeal` 门槛值使用 |
| `EFFECT_ADJUST_DISTRICT_PREREQ` | `TechType` 为空 | 仅解锁不需科技，或指定具体科技 |
| `EFFECT_ADJUST_PLAYER_DISTRICT_CREATE_YIELD` | `MustReplaceImprovement` / `YieldBasedOnAppeal` | 极特殊参数组合，用于区域上创建改良设施 |
| `EFFECT_ADJUST_PLAYER_BUILDING_FAVOR` | `Favor` | 参数名非 `Amount` |
| `EFFECT_ADJUST_RELIGION_BUILDING_DISCOUNT` | `Discount` | 参数名非 `Amount` |
| `EFFECT_GRANT_CITY_YIELD_PERCENT_BUILDING_CREATED_COST` | `BuildingProductionPercent` | 参数名非 `Amount`，百分比值 |
| `EFFECT_PLAYER_DIPLOMACY_AGENDA_DISTRICT_SPREAD` | `SimpleModifierDescription` / `StatementKey` | 外交 UI 专用参数 |
| `EFFECT_ADJUST_DISTRICT_TOURISM_ADJACENCY_YIELD_MOFIFIER` | MOFIFIER 拼写 | Firaxis 原始拼写错误，引用时必须使用原拼写 |
| `EFFECT_ADJUST_BUILDING_SPREAD_CHARGES` | Amount 含义 | Amount 表示"传教次数增量"而非产量 |

---

## 枚举引用清单

| 参数 | 枚举前缀 | 参考来源 |
|---|---|---|
| `BuildingType` | `BUILDING_` | DebugGameplay.sqlite Buildings 表 |
| `DistrictType` | `DISTRICT_` | DebugGameplay.sqlite Districts 表 |
| `YieldType` | `YIELD_` | YIELDS: YIELD_CULTURE / YIELD_FAITH / YIELD_FOOD / YIELD_GOLD / YIELD_PRODUCTION / YIELD_SCIENCE |
| `FeatureType` | `FEATURE_` | DebugGameplay.sqlite Features 表 |
| `GreatPersonClassType` | `GREAT_PERSON_CLASS_` | 如 GREAT_PERSON_CLASS_SCIENTIST / ENGINEER / MERCHANT / PROPHET / WRITER / ARTIST / MUSICIAN / GENERAL / ADMIRAL |
| `ImprovementType` | `IMPROVEMENT_` | DebugGameplay.sqlite Improvements 表 |
| `TechType` | `TECH_` | DebugGameplay.sqlite Technologies 表 |

---

## 命名审查

- **EFFECT_ADJUST_CITY_PRODUCTION_BUILDING vs EFFECT_ADJUST_CITY_PRODUCTION_DISTRICT**：前者调整建筑生产力，后者调整区域生产力，BUILDING/DISTRICT 区分明确。
- **EFFECT_ADJUST_DISTRICT_TOURISM_ADJACENCY_YIELD_MOFIFIER**：拼写错误 "MOFIFIER"（应为 MODIFIER），系 Firaxis 原始命名。Mod 中引用时需使用原拼写。
- **EFFECT_ADJUST_BUILDING_SPREAD_CHARGES**：效果实际作用于宗教单位传教次数，名称中 BUILDING 指"建筑解锁的相关宗教能力"，非直接调整建筑。
- **EFFECT_ADJUST_PLAYER_FREE_BUILDING_WHEN_SPECIALTY_DISTRICT_CONSTRUCTED 与 _EXCEPT 版本**：后者多排除参数（DistrictType=GOVERNMENT），共同组成汉谟拉比UA。
- **EFFECT_GRANT_CHEAPEST_BUILDING_IN_CITY**："CHEAPEST" 特指"所需生产力最低的建筑"（非金币价格），用于贝伦塔、图拉真圆柱等。
- **EFFECT_ADJUST_ALL_BUILDING_PRODUCTION_MODIFIER**：参数 IsWonder=1 时仅作用于奇观，IsWonder=0 时仅作用于普通建筑。两个版本（SINGLE_CITY / PLAYER_CITIES）的参数略有不同。

---

## 无官方实例的 EffectType

以下 EffectType 在 DynamicModifiers 中注册，但在 Modifiers 表中无任何已配置的 ModifierId 实例：

| EffectType | 可能用途 |
|---|---|
| `EFFECT_ADJUST_ACTIVE_BUILDING_PRODUCTION` | 根据当前建造的建筑类型动态调整生产力 |
| `EFFECT_ADJUST_CITY_HOUSING_PER_DISTRICT` | 根据城市区域数量提供住房 |
| `EFFECT_ADJUST_DISTRICT_ATTACK_RANGE` | 扩展城市攻击范围（军事区域效果） |
| `EFFECT_ADJUST_PLAYER_VALID_BUILDING` | 解锁建筑的建造权限 |
| `EFFECT_GRANT_BUILDING_IN_CITY`（非 IGNORE 版） | 需前置条件的免费赠送建筑 |

这些 EffectType 可能为预留接口、DLC/情景专属内容，或在 GameEffects 表（非 Modifiers 表）中有其他引用方式。

---
