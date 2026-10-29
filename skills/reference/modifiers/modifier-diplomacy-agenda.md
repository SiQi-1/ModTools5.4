# modifier-diplomacy -- 外交/影响力/使者/不满/议程类 EffectType — 议程

> 分册：由 [modifier-diplomacy.md](modifier-diplomacy.md) 按主题拆出；覆盖 议程 (Agenda)、EFFECT_DIPLOMACY_AGENDA_ANGEVIN_EMPIRE、EFFECT_DIPLOMACY_AGENDA_ARCHIPELAGIC_STATE、EFFECT_DIPLOMACY_AGENDA_AYYUBID_DYNASTY、EFFECT_DIPLOMACY_AGENDA_BLACK_QUEEN、EFFECT_DIPLOMACY_AGENDA_BULL_MOOSE、EFFECT_DIPLOMACY_AGENDA_BUSHIDO、EFFECT_DIPLOMACY_AGENDA_CANADIAN_EXPEDITIONARY、EFFECT_DIPLOMACY_AGENDA_END_TO_SUFFERING、EFFECT_DIPLOMACY_AGENDA_ENVIRONMENT、EFFECT_DIPLOMACY_AGENDA_ETHIOPIAN_HIGHLANDS、EFFECT_DIPLOMACY_AGENDA_EXPLOITATIVE、EFFECT_DIPLOMACY_AGENDA_FLAT_EARTHER、EFFECT_DIPLOMACY_AGENDA_HORN_CHEST_LOINS、EFFECT_DIPLOMACY_AGENDA_HORSE_LORD、EFFECT_DIPLOMACY_AGENDA_KAITIAKITANGA、EFFECT_DIPLOMACY_AGENDA_KUBLAI_PAX、EFFECT_DIPLOMACY_AGENDA_LAST_VIKING_KING、EFFECT_DIPLOMACY_AGENDA_LAWGIVER、EFFECT_DIPLOMACY_AGENDA_LORD_OF_MINES、EFFECT_DIPLOMACY_AGENDA_MAGNIFICENCES、EFFECT_DIPLOMACY_AGENDA_OPPORTUNIST、EFFECT_DIPLOMACY_AGENDA_OPTIMUS_PRINCEPS、EFFECT_DIPLOMACY_AGENDA_PARANOID、EFFECT_DIPLOMACY_AGENDA_PATRON_OF_ARTS、EFFECT_DIPLOMACY_AGENDA_PERPETUALLY_ON_GUARD、EFFECT_DIPLOMACY_AGENDA_QUEEN_OF_NILE、EFFECT_DIPLOMACY_AGENDA_RAVEN_BANNER、EFFECT_DIPLOMACY_AGENDA_SHORT_LIFE_GLORY、EFFECT_DIPLOMACY_AGENDA_SIMON_BOLIVAR、EFFECT_DIPLOMACY_AGENDA_TRIEU_DEFENDER `[无官方使用示例，但 Mod 中可用]`、EFFECT_DIPLOMACY_AGENDA_TURTLER、EFFECT_DIPLOMACY_AGENDA_WITH_SHIELD_OR_ON_IT、EFFECT_DIPLOMACY_AGENDA_ZEALOT、EFFECT_PLAYER_DIPLOMACY_AGENDA_COMPARE_ARMY_SIZE。触发：改议程、AI 议程行为时。

## 议程 (Agenda)

> **统一说明**: 以下 `EFFECT_DIPLOMACY_AGENDA_*` 为各领袖的定制议程效果，其核心逻辑由 C++ DLL 固化了具体规则，Mod 中**文本无法自定义**（无法更改议程描述和对白），因此在实际 Mod 中不易用于新领袖。创建自定义议程应优先考虑 `EFFECT_DIPLOMACY_SIMPLE_EFFECT`。

议程类 EffectType 统一使用 `COLLECTION_MAJOR_PLAYERS`（对主要文明生效）或 `COLLECTION_ALL_PLAYERS`。

---

### EFFECT_DIPLOMACY_AGENDA_ANGEVIN_EMPIRE

安茹帝国议程 — 根据对方人口高低增减外交态度。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_ANGEVIN_EMPIRE` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `BottomRankingDiploMod` | **必写** | 整数 — 对低人口的惩罚。示例值: `-8` |
| `HighPopulationThreshold` | **必写** | 整数 — 高人口阈值。示例值: `110` |
| `LowPopulationThreshold` | **必写** | 整数 — 低人口阈值。示例值: `70` |
| `StatementKey` | **必写** | `LOC_*` — 议程提示文本 |
| `TopRankingDiploMod` | **必写** | 整数 — 对高人口的奖励。示例值: `8` |

---

### EFFECT_DIPLOMACY_AGENDA_ARCHIPELAGIC_STATE

群岛国家议程 — 根据对方拥有大型岛屿（大陆）面积增减态度。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_ARCHIPELAGIC_STATE` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `AcceptableIslandPercentage` | 可选 | 整数 — 可接受的岛屿百分比。示例值: `20` |
| `MaxNegativeModifier` | **必写** | 整数 — 最大负面修正。示例值: `-8` |
| `MaxPositiveModifier` | **必写** | 整数 — 最大正面修正。示例值: `8` |
| `MaxTilesLargeIsland` | **必写** | 整数 — 大型岛屿最大格数。示例值: `37` |
| `MaxTilesMediumIsland` | **必写** | 整数 — 中型岛屿最大格数。示例值: `19` |
| `MaxTilesSmallIsland` | **必写** | 整数 — 小型岛屿最大格数。示例值: `7` |
| `ReductionTurns` | 可选 | 整数 — 衰减回正所需回合 |
| `StatementKey` | **必写** | `LOC_*` |

---

### EFFECT_DIPLOMACY_AGENDA_AYYUBID_DYNASTY

阿尤布王朝议程。数据库中活跃使用。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_AYYUBID_DYNASTY` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `StatementKey` | **必写** | `LOC_*` |

---

### EFFECT_DIPLOMACY_AGENDA_BLACK_QUEEN

黑皇后议程（法国凯瑟琳）— 对缺乏间谍的文明不满。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_BLACK_QUEEN` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `StatementKey` | **必写** | `AGENDA_BLACK_QUEEN_WARNING` |

---

### EFFECT_DIPLOMACY_AGENDA_BULL_MOOSE

公牛驼鹿议程（美国泰迪·罗斯福）— 根据对方是否在同一大陆发动战争。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_BULL_MOOSE` | `COLLECTION_ALL_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `StatementKey` | **必写** | `LOC_PLACEHOLDER` |

---

### EFFECT_DIPLOMACY_AGENDA_BUSHIDO

武士道议程（日本北条时宗）— 对有强大军事和文化的文明尊敬、对两者都弱者蔑视。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_BUSHIDO` | `COLLECTION_ALL_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `StatementKey` | **必写** | `AGENDA_BUSHIDO_WARNING` |

---

### EFFECT_DIPLOMACY_AGENDA_CANADIAN_EXPEDITIONARY

加拿大远征议程 — 对参与紧急事件和竞赛积极的文明友好。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_CANADIAN_EXPEDITIONARY` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `BottomPercentage` | **必写** | 整数 — 对表现低于此百分位的惩罚阈值。示例值: `30` |
| `BottomRankingDiploMod` | **必写** | 整数 — 低排名修正值。示例值: `-8` |
| `StatementKey` | **必写** | `LOC_*` |
| `TopPercentage` | **必写** | 整数 — 对表现高于此百分位的奖励阈值。示例值: `65` |
| `TopRankingDiploMod` | **必写** | 整数 — 高排名修正值。示例值: `8` |

---

### EFFECT_DIPLOMACY_AGENDA_END_TO_SUFFERING

止苦议程 — 根据对方建设圣地/大城市的宗教/城区建设。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_END_TO_SUFFERING` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `DisappointingHolySitePercentage` | **必写** | 整数 — 圣地偏少阈值。示例值: `25` |
| `DisappointingLargeCityPercentage` | **必写** | 整数 — 大城市偏少阈值。示例值: `35` |
| `MaxNegativeModifier` | **必写** | 整数 — 最大负面修正。示例值: `-8` |
| `MaxPositiveModifier` | **必写** | 整数 — 最大正面修正。示例值: `8` |
| `StatementKey` | **必写** | `LOC_*` |
| `TargetHolySitePercentage` | **必写** | 整数 — 目标圣地比例。示例值: `50` |
| `TargetLargeCityPercentage` | **必写** | 整数 — 目标大城市比例。示例值: `65` |

---

### EFFECT_DIPLOMACY_AGENDA_ENVIRONMENT

环保议程 — 根据对方保护/破坏自然环境的程度（种树/建国家公园 vs 砍伐地貌）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_ENVIRONMENT` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `ForestPlacedValue` | **必写** | 整数 — 每植树的分数 |
| `HiddenAgenda` | 可选 | `0` = 显示, `1` = 隐藏 |
| `HighThreshold` | **必写** | 整数 — 高分阈值 |
| `IncrementValue` | **必写** | 整数 — 每次递增修正值 |
| `InitialValue` | **必写** | 整数 — 初始值 |
| `LowThreshold` | **必写** | 整数 — 低分阈值 |
| `MaxDiploModifierMagnitude` | **必写** | 整数 — 最大修正幅度 |
| `NationalParkConstructionValue` | **必写** | 整数 — 每建国家公园的分数 |
| `PlotFeatureRemovedValue` | **必写** | 整数 — 每移除地貌的惩罚分数 |
| `ScoreAllowancePerEra` | 可选 | 整数 — 每时代的容忍度 |
| `SimpleModifierDescription` | **必写** | `LOC_*` |
| `StatementKey` | **必写** | `LOC_*` |

---

### EFFECT_DIPLOMACY_AGENDA_ETHIOPIAN_HIGHLANDS

埃塞俄比亚高原议程 — 根据对方在山脉/丘陵区域的建城情况。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_ETHIOPIAN_HIGHLANDS` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `StatementKey` | **必写** | `LOC_PLACEHOLDER` |

---

### EFFECT_DIPLOMACY_AGENDA_EXPLOITATIVE

剥削议程（罗斯福·进步党）— 对地貌改良过多不满。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_EXPLOITATIVE` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `HiddenAgenda` | 可选 | `0` = 显示, `1` = 隐藏。示例值: `1` |
| `HighScoreThreshold` | **必写** | 整数 — 高分阈值。示例值: `15` |
| `IncrementValue` | **必写** | 整数 — 增量值。示例值: `0` |
| `InitialValue` | **必写** | 整数 — 初始值。示例值: `0` |
| `LowScoreThreshold` | **必写** | 整数 — 低分阈值。示例值: `-15` |
| `MaxDiploModifierMagnitude` | **必写** | 整数 — 最大修正幅度。示例值: `10` |
| `NationalParkConstructionValue` | **必写** | 整数 — 建国家公园的分数。示例值: `10` |
| `PlotFeatureRemovalValue` | **必写** | 整数 — 移除地貌的惩罚。示例值: `1` |
| `SimpleModifierDescription` | **必写** | `LOC_*` |
| `StatementKey` | **必写** | `LOC_*` |
| `TileImprovementHighThreshold` | **必写** | 整数 — 改良过多阈值。示例值: `75` |
| `TileImprovementLowThreshold` | **必写** | 整数 — 改良较少阈值。示例值: `35` |
| `TileImprovementPreferenceValue` | **必写** | 整数 — 改良偏好评分。示例值: `9` |

---

### EFFECT_DIPLOMACY_AGENDA_FLAT_EARTHER

地平说议程 — 对进行航天项目/建设航天中心的文明不满。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_FLAT_EARTHER` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `DiploModForCircumnavigation` | **必写** | 整数 — 环游世界惩罚。示例值: `-2` |
| `DiploModPerSpaceProject` | **必写** | 整数 — 每个航天项目惩罚。示例值: `-1` |
| `DiploModPerSpaceport` | **必写** | 整数 — 每个航天中心惩罚。示例值: `-1` |
| `HiddenAgenda` | 可选 | `0` = 显示, `1` = 隐藏。示例值: `1` |
| `SimpleModifierDescription` | **必写** | `LOC_*` |
| `StatementKey` | **必写** | `LOC_*` |
| `TopRankingDiploMod` | **必写** | 整数 — 最高正面修正。示例值: `8` |

---

### EFFECT_DIPLOMACY_AGENDA_HORN_CHEST_LOINS

角胸甲议程（斯基泰托米丽司）— 根据对方是否有军团/军队编制。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_HORN_CHEST_LOINS` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `BottomPercentage` | **必写** | 整数 — 示例值: `30` |
| `BottomRankingDiploMod` | **必写** | 整数 — 示例值: `-7` |
| `CantBuildDiploMod` | **必写** | 整数 — 无法编制时的修正。示例值: `-3` |
| `CorpsPrereqCivic` | **必写** | `CIVIC_*` — 编制军团所需市政。示例值: `CIVIC_NATIONALISM` |
| `StatementKey` | **必写** | `LOC_*` |
| `TopPercentage` | **必写** | 整数 — 示例值: `70` |
| `TopRankingDiploMod` | **必写** | 整数 — 示例值: `6` |

---

### EFFECT_DIPLOMACY_AGENDA_HORSE_LORD

马背之王议程（蒙古成吉思汗）— 看重对方骑兵数量。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_HORSE_LORD` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `BottomPercentage` | **必写** | 整数 — 示例值: `30` |
| `BottomRankingDiploMod` | **必写** | 整数 — 低骑兵比例的正面修正。示例值: `7` |
| `PromotionClass1` | **必写** | `PROMOTION_CLASS_HEAVY_CAVALRY` |
| `PromotionClass2` | **必写** | `PROMOTION_CLASS_LIGHT_CAVALRY` |
| `StatementKey` | **必写** | `LOC_*` |
| `TopPercentage` | **必写** | 整数 — 示例值: `70` |
| `TopRankingDiploMod` | **必写** | 整数 — 高骑兵比例的负面修正。示例值: `-6` |

---

### EFFECT_DIPLOMACY_AGENDA_KAITIAKITANGA

守护理事会议程（毛利）— 对未受战争破坏的环境文明友好。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_KAITIAKITANGA` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `BottomPercentage` | **必写** | 整数 — 示例值: `40` |
| `BottomRankingDiploMod` | **必写** | 整数 — 示例值: `-6` |
| `HiddenAgenda` | 可选 | `0` = 显示, `1` = 隐藏。示例值: `1` |
| `StatementKey` | **必写** | `LOC_*` |
| `TopPercentage` | **必写** | 整数 — 示例值: `60` |
| `TopRankingDiploMod` | **必写** | 整数 — 示例值: `6` |

---

### EFFECT_DIPLOMACY_AGENDA_KUBLAI_PAX

忽必烈和平议程 — 根据对方是否使用通配符政策。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_KUBLAI_PAX` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `StatementKey` | **必写** | `AGENDA_KUBLAI_PAX_KUDO_AND_WARNING` |

---

### EFFECT_DIPLOMACY_AGENDA_LAST_VIKING_KING

最后维京王议程（挪威哈拉尔）— 看重海军实力。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_LAST_VIKING_KING` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `BetterMilitaryBonus` | **必写** | 整数 — 军力稍弱的奖励。示例值: `4` |
| `HiddenAgenda` | 可选 | `0` = 显示, `1` = 隐藏。示例值: `1` |
| `SimpleModifierDescription` | **必写** | `LOC_*` |
| `StatementKey` | **必写** | `LOC_*` |
| `TopMilitaryBonus` | **必写** | 整数 — 军力最强的奖励。示例值: `6` |

---

### EFFECT_DIPLOMACY_AGENDA_LAWGIVER

立法者议程（巴比伦汉谟拉比）— 根据对方是否建造了各区类型。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_LAWGIVER` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `BonusIfNotOriginalOwner` | **必写** | 整数 — 如对方不是原始所有者时的加成。示例值: `50` |
| `BottomPercentage` | **必写** | 整数 — 示例值: `30` |
| `BottomRankingDiploMod` | **必写** | 整数 — 示例值: `-8` |
| `StatementKey` | **必写** | `LOC_*` |
| `TopPercentage` | **必写** | 整数 — 示例值: `65` |
| `TopRankingDiploMod` | **必写** | 整数 — 示例值: `8` |

---

### EFFECT_DIPLOMACY_AGENDA_LORD_OF_MINES

矿主议程 — 根据对方采矿/采石场数量。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_LORD_OF_MINES` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `BottomPercentage` | **必写** | 整数 — 示例值: `30` |
| `BottomRankingDiploMod` | **必写** | 整数 — 示例值: `-8` |
| `StatementKey` | **必写** | `LOC_*` |
| `TopPercentage` | **必写** | 整数 — 示例值: `65` |
| `TopRankingDiploMod` | **必写** | 整数 — 示例值: `8` |

---

### EFFECT_DIPLOMACY_AGENDA_MAGNIFICENCES

辉煌议程（法国路易十四）— 根据对方奇观/巨作数量。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_MAGNIFICENCES` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `StatementKey` | **必写** | `LOC_PLACEHOLDER` |

---

### EFFECT_DIPLOMACY_AGENDA_OPPORTUNIST

机会主义者议程（马其顿亚历山大）— 对和平状态不满，喜欢交战文明。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_OPPORTUNIST` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `EachSurpriseWarBonus` | **必写** | 整数 — 每场突袭战争的奖励。示例值: `1` |
| `NeverSurpriseWarPenalty` | **必写** | 整数 — 从未发动突袭的惩罚。示例值: `-6` |
| `RecentSurpriseWarBonus` | **必写** | 整数 — 近期突袭的奖励。示例值: `15` |
| `StatementKey` | **必写** | `AGENDA_BACKSTABBER` |
| `SurpriseWarDegradeTurns` | **必写** | 整数 — 突袭加分衰减回合。示例值: `3` |

---

### EFFECT_DIPLOMACY_AGENDA_OPTIMUS_PRINCEPS

贤君议程（罗马图拉真）— 看重领土面积。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_OPTIMUS_PRINCEPS` | `COLLECTION_ALL_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `BetterTerritoryBonus` | **必写** | 整数 — 示例值: `4` |
| `HiddenAgenda` | 可选 | `0` = 显示, `1` = 隐藏。示例值: `1` |
| `SimpleModifierDescription` | **必写** | `LOC_*` |
| `StatementKey` | **必写** | `LOC_*` |
| `TopTerritoryBonus` | **必写** | 整数 — 示例值: `6` |

---

### EFFECT_DIPLOMACY_AGENDA_PARANOID

偏执议程 — 仅 `StatementKey` 参数。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_PARANOID` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `StatementKey` | **必写** | `AGENDA_PARANOID_WARNING` |

---

### EFFECT_DIPLOMACY_AGENDA_PATRON_OF_ARTS

艺术赞助人议程 — 对缺乏巨作/艺术品的文明不满。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_PATRON_OF_ARTS` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `BottomPercentage` | **必写** | 整数 — 示例值: `30` |
| `BottomRankingDiploMod` | **必写** | 整数 — 示例值: `8` |
| `StatementKey` | **必写** | `LOC_*` |
| `TopPercentage` | **必写** | 整数 — 示例值: `65` |
| `TopRankingDiploMod` | **必写** | 整数 — 示例值: `-8` |

---

### EFFECT_DIPLOMACY_AGENDA_PERPETUALLY_ON_GUARD

永不卸防议程（澳大利亚约翰·科廷）— 对占领敌方城市不满。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_PERPETUALLY_ON_GUARD` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `PenaltyPerOccupiedCity` | **必写** | 整数 — 每占领城市的惩罚。示例值: `-2` |
| `SimpleModifierDescription` | **必写** | `LOC_*` |
| `StatementKey` | **必写** | `LOC_*` |

---

### EFFECT_DIPLOMACY_AGENDA_QUEEN_OF_NILE

尼罗河女王议程（埃及克利奥帕特拉）— 仅 `StatementKey` 参数。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_QUEEN_OF_NILE` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `StatementKey` | **必写** | `AGENDA_QUEEN_OF_NILE_WARNING` |

---

### EFFECT_DIPLOMACY_AGENDA_RAVEN_BANNER

渡鸦旗帜议程（挪威/维京）— 根据海军实力。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_RAVEN_BANNER` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `BottomPercentage` | **必写** | 整数 — 示例值: `30` |
| `BottomRankingDiploMod` | **必写** | 整数 — 示例值: `-8` |
| `StatementKey` | **必写** | `LOC_*` |
| `TopPercentage` | **必写** | 整数 — 示例值: `65` |
| `TopRankingDiploMod` | **必写** | 整数 — 示例值: `8` |

---

### EFFECT_DIPLOMACY_AGENDA_SHORT_LIFE_GLORY

生短荣长议程（苏美尔吉尔伽美什）— 根据对方是否在战争中。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_SHORT_LIFE_GLORY` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `EachWarDeclaredBonus` | **必写** | 整数 — 每场宣战奖励。示例值: `1` |
| `MajorWarBonus` | **必写** | 整数 — 主要战争奖励。示例值: `5` |
| `MaxWarDeclaredBonus` | **必写** | 整数 — 最大宣战奖励。示例值: `5` |
| `NotAtWarPenalty` | **必写** | 整数 — 不在战争中的惩罚。示例值: `-6` |
| `SinceWarPenaltyTurns` | **必写** | 整数 — 多少回合内无战争开始惩罚。示例值: `40` |
| `StatementKey` | **必写** | `AGENDA_SHORT_LIFE_GLORY` |

---

### EFFECT_DIPLOMACY_AGENDA_SIMON_BOLIVAR

玻利瓦尔议程 — 根据对方有晋升的单位数量。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_SIMON_BOLIVAR` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `MinPromotedUnits` | **必写** | 整数 — 最小晋升单位数。示例值: `5` |
| `NumSteps` | **必写** | 整数 — 评分阶梯数。示例值: `4` |
| `PercentageDifferencePerStep` | **必写** | 整数 — 每阶梯百分比差。示例值: `10` |
| `ScorePerStep` | **必写** | 整数 — 每阶梯评分。示例值: `3` |
| `SimpleModifierDescription` | **必写** | `LOC_*` |
| `StatementKey` | **必写** | `LOC_*` |

---

### EFFECT_DIPLOMACY_AGENDA_TRIEU_DEFENDER `[无官方使用示例，但 Mod 中可用]`

赵氏守护议程（越南征氏姐妹）— 根据对方是否喜欢在植被区域建造。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_TRIEU_DEFENDER` | `COLLECTION_MAJOR_PLAYERS` |

> 数据库示例中无显式参数（参数可能全由 DLL 逻辑处理）。

---

### EFFECT_DIPLOMACY_AGENDA_TURTLER

龟缩议程（中国秦始皇）— 看重奇观建造。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_TURTLER` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `BottomRankingDiploMod` | **必写** | 整数 — 示例值: `-6` |
| `HiddenAgenda` | 可选 | `0` = 显示, `1` = 隐藏。示例值: `1` |
| `SimpleModifierDescription` | 可选 | `LOC_*` |
| `TopRankingDiploMod` | **必写** | 整数 — 示例值: `4` |

---

### EFFECT_DIPLOMACY_AGENDA_WITH_SHIELD_OR_ON_IT

或持盾归议程（希腊戈尔戈）— 对从未在战争中放弃/赔款的文明友好。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_WITH_SHIELD_OR_ON_IT` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `AvoidedWarPenalty` | **必写** | 整数 — 避战惩罚。示例值: `-4` |
| `AvoidedWarPenaltyTurnsToRampUp` | **必写** | 整数 — 避战惩罚爬升回合。示例值: `15` |
| `HighThreshold` | **必写** | 整数 — 示例值: `4` |
| `IncrementValue` | **必写** | 整数 — 示例值: `0` |
| `InitialValue` | **必写** | 整数 — 示例值: `0` |
| `LowThreshold` | **必写** | 整数 — 示例值: `-1` |
| `MaxDiploModifierMagnitude` | **必写** | 整数 — 示例值: `12` |
| `PaidForPeacePenalty` | **必写** | 整数 — 赔款求和惩罚。示例值: `-8` |
| `PaidForPeacePenaltyTurnsToFadeOut` | **必写** | 整数 — 赔款惩罚消退回合。示例值: `30` |
| `ReductionTurns` | **必写** | 整数 — 衰减回合。示例值: `2` |
| `ReductionValue` | **必写** | 整数 — 每次衰减值。示例值: `0` |
| `SimpleModifierDescription` | **必写** | `LOC_*` |
| `StatementKey` | **必写** | `LOC_*` |

---

### EFFECT_DIPLOMACY_AGENDA_ZEALOT

狂热者议程（西班牙菲利普二世）— 根据对方是否同宗教。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_ZEALOT` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `BottomRankingDiploMod` | **必写** | 整数 — 示例值: `-6` |
| `StatementKey` | **必写** | `LOC_*` |
| `TopRankingDiploMod` | **必写** | 整数 — 示例值: `6` |

---

### EFFECT_PLAYER_DIPLOMACY_AGENDA_COMPARE_ARMY_SIZE

比较军力大小的议程（安比奥里克斯/高卢议程）。数据库中活跃使用。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_DIPLOMACY_AGENDA_AMBIORIX_ARMY` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `AdjustPerStep` | **必写** | 整数 — 每阶梯修正值。示例值: `4` |
| `DeltaUnits` | **必写** | 整数 — 单位数差额。示例值: `5` |
| `MaxSteps` | **必写** | 整数 — 最大阶梯数。示例值: `4` |
| `MinUnitsNeeded` | **必写** | 整数 — 所需最小单位数。示例值: `5` |
| `StatementKey` | **必写** | `AGENDA_AMBIORIX` |

---

