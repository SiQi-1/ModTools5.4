# modifier-diplomacy -- 外交/影响力/使者/不满/议程类 EffectType — 注意事项

> 分册：由 [modifier-diplomacy.md](modifier-diplomacy.md) 按主题拆出；覆盖 相似效果对比、特殊参数注意。触发：实现前核对外交类相似效果与特殊参数时。

## 相似效果对比

| 效果组 | 差异 |
|--------|------|
| `BROKEN_PLEDGE` vs `BROKEN_PROMISE` | Pledge 为正式誓言（更重惩罚 -6），Promise 为口头承诺（-6） |
| `KEPT_PLEDGE` vs `KEPT_PROMISE` | Pledge 奖励 +4，Promise 奖励 +4 |
| `NO_PLEDGE` vs `NO_PROMISE` | Pledge 拒绝 -3，Promise 拒绝 -3，衰减回合都是 10 |
| `DUPLICATE_FIRST_INFLUENCE_TOKEN` vs `DUPLICATE_INFLUENCE_TOKEN_WHEN_RIVAL_GOVERNMENT` vs `DUPLICATE_INFLUENCE_TOKEN_WHEN_SAME_RELIGION` vs `DUPLICATE_INFLUENCE_TOKEN_WHEN_TRADE_ROUTE_TO` | 触发条件不同：首次 vs 异政体 vs 同宗教 vs 贸易路线 |
| `ADJUST_PLAYER_GRIEVANCE_DECAY` vs `DISABLE_PLAYER_GRIEVANCE_DECAY` vs `GRIEVANCE_GENERATION` | 衰减速率 vs 完全禁用 vs 生成倍率 |
| `NEW_WARMONGER` vs `THIRD_PARTY_WARMONGER` vs `DIPLOMACY_WARMONGER` | 对己方宣战 vs 对第三方宣战 vs 通用战争狂惩罚 |
| `FAVOR_FROM_DELEGATIONS` vs `FAVOR_FROM_EMBASSIES` | 代表团 vs 大使馆 |
| `EXTRA_FAVOR_PER_TURN`（城市级） vs `EXTRA_FAVOR_PER_TURN`（玩家级） | CollectionType 不同: `COLLECTION_PLAYER_CITIES` vs `COLLECTION_OWNER` |
| `ANYONE_PLUNDER_FAVOR` vs `ANYONE_PLUNDER_TO_FAVOR` | 前者用于资料片/场景, 后者用于原版 — 两个不同 EffectType |

## 特殊参数注意

- `DiplomaticYieldSource` 枚举值来自游戏 DLL，常见值: `TERRITORIAL_EXPANSION_WAR_INITIATED`, `SURPRISE_WAR_INITIATED`, `CITY_CAPTURED`, `EMERGENCY_JOINED` 等
- `DiplomaticAction` / `DiplomaticActionType` 值来自 `DiplomaticActions` 表
- `GovernmentSlotType` 枚举: `SLOT_MILITARY`, `SLOT_ECONOMIC`, `SLOT_DIPLOMATIC`, `SLOT_WILDCARD`
- `StatementKey` 通常使用 `AGENDA_*` 系列的 LOC 文本键（不含 `LOC_` 前缀），少数为 `LOC_*` 格式
- `EffectType` 参数（在 `EFFECT_DIPLOMACY_THIRD_PARTY_EFFECTS` 中）是字符串枚举，不是 EffectType 引用
- 议程系列中 `HiddenAgenda = 1` 表示该议程不在外交面板显示，为隐藏议程
- CollectionType 区分: `COLLECTION_MAJOR_PLAYERS`（仅主要文明） vs `COLLECTION_ALL_PLAYERS`（含城邦和自由城市）
- `Source` 参数（`EFFECT_ADD_DIPLO_VISIBILITY` 中）标识能见度来源: `SOURCE_GREAT_PERSON_JOURNALISM`, `SOURCE_TRADING_POST_TRAIT`, `SOURCE_TECH`, `SOURCE_TRAIT` 等
- `SourceType` 参数过滤适用范围: `DIPLO_SOURCE_ALL_NAMES`（全部）, `DIPLO_SOURCE_FEMALE_ONLY`（仅女性领袖）
- 标记 `[无官方使用示例，但 Mod 中可用]` 的 EffectType 来自 Modding Companion 的 USER ADDED 条目，ModifierType 存在但无官方数据库实例，使用时需自行测试（这不意味着效果无效，只是没有官方参考实现）
- 标记 `[未在数据库中活跃使用]` 的 EffectType 在当前游戏数据库中无 Modifier 实例，但 EffectType 已注册可在 Mod 中使用
