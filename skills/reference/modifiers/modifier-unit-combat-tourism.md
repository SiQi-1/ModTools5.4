# modifier-unit-combat -- 单位战斗/属性/移动/经验/间谍/旅游/宗教等 EffectType — 旅游/摇滚

> 分册：由 [modifier-unit-combat.md](modifier-unit-combat.md) 按主题拆出；覆盖 旅游/摇滚乐队、EFFECT_ADJUST_PLAYER_ROCK_BAND_UNIT_ALBUM_SALES、EFFECT_ADJUST_UNIT_POST_TOURISM_BOMB_LOYALTY、EFFECT_ADJUST_UNIT_ROCK_BAND_LEVEL_DISTRICT、EFFECT_ADJUST_UNIT_ROCK_BAND_LEVEL_IMPROVEMENT、EFFECT_ADJUST_UNIT_ROCK_BAND_LEVEL_NATIONAL_PARK、EFFECT_ADJUST_UNIT_ROCK_BAND_LEVEL_NATURAL_WONDER、EFFECT_ADJUST_UNIT_ROCK_BAND_TOURISM_BOMB_VALUE_PEACE、EFFECT_ADJUST_UNIT_TOURISM_BOMB_CONVERT_CITY、EFFECT_ADJUST_UNIT_TOURISM_BOMB_DISTRICT、EFFECT_ADJUST_UNIT_TOURISM_BOMB_IMPROVEMENT、EFFECT_ADJUST_UNIT_TOURISM_BOMB_NATIONAL_PARK、EFFECT_ADJUST_UNIT_TOURISM_BOMB_NATURAL_WONDER、EFFECT_ADJUST_UNIT_TOURISM_BOMB_RANGE、EFFECT_ADJUST_UNIT_YIELD_PER_TOURISM_BOMB。触发：改旅游业绩、摇滚乐队时。

## 旅游/摇滚乐队

### EFFECT_ADJUST_PLAYER_ROCK_BAND_UNIT_ALBUM_SALES

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_EMERGENCY_PLAYERS_ADJUST_ROCK_BAND_UNIT_ALBUM_SALES` | `COLLECTION_EMERGENCY_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `25`、`50`、`75` |

**效果**：调整摇滚乐队演出后的专辑销售旅游业绩
> **溯源**：紧急情况 — 诺贝尔文学奖（`EMERGENCY_NOBEL_PRIZE_LITERATURE`） — 紧急情况奖励效果

---

### EFFECT_ADJUST_UNIT_POST_TOURISM_BOMB_LOYALTY

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_UNIT_ADJUST_POST_TOURISM_BOMB_LOYALTY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `-40` |

**效果**：摇滚乐队演出后降低目标城市的忠诚度
> **溯源**：单位晋升 — 独立摇滚（`PROMOTION_INDIE`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_ROCK_BAND_LEVEL_DISTRICT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_ROCK_BAND_LEVEL_DISTRICT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1`、`2` |
| `DistrictType` | 是 | `DISTRICT_ACROPOLIS`、`DISTRICT_CAMPUS`、`DISTRICT_COTHON`、`DISTRICT_ENTERTAINMENT_COMPLEX`、`DISTRICT_HARBOR`、`DISTRICT_HIPPODROME` ... (共 15 种值) |

**效果**：摇滚乐队在指定区域演出时获得额外等级
> **溯源**：单位晋升 — 太空摇滚（`PROMOTION_SPACE_ROCK`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 专辑封面（`PROMOTION_ALBUM_COVER_ART`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 舞台摇滚（`PROMOTION_ARENA_ROCK`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 华丽摇滚（`PROMOTION_GLAM_ROCK`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 雷鬼音乐（`PROMOTION_REGGAE_ROCK`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_ROCK_BAND_LEVEL_IMPROVEMENT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_ROCK_BAND_LEVEL_IMPROVEMENT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1` |
| `ImprovementType` | 是 | `IMPROVEMENT_BEACH_RESORT` |

**效果**：摇滚乐队在指定改良设施上演出时获得额外等级
> **溯源**：单位晋升 — 冲浪摇滚（`PROMOTION_SURF_ROCK`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_ROCK_BAND_LEVEL_NATIONAL_PARK

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_ROCK_BAND_LEVEL_NATIONAL_PARK` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1` |

**效果**：摇滚乐队在国家公园演出时获得额外等级
> **溯源**：单位晋升 — 音乐节（`PROMOTION_MUSIC_FESTIVAL`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_ROCK_BAND_LEVEL_NATURAL_WONDER

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_ROCK_BAND_LEVEL_NATURAL_WONDER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1` |

**效果**：摇滚乐队在自然奇观演出时获得额外等级
> **溯源**：单位晋升 — 音乐节（`PROMOTION_MUSIC_FESTIVAL`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_ROCK_BAND_TOURISM_BOMB_VALUE_PEACE

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_ROCK_BAND_TOURISM_BOMB_VALUE_PEACE` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `200`、`50` |

**效果**：调整和平时期摇滚乐队的旅游业绩爆发值
> **溯源**：政策 — 权力归花儿（`POLICY_FLOWER_POWER`） — 通过政策卡提供加成

---

### EFFECT_ADJUST_UNIT_TOURISM_BOMB_CONVERT_CITY

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_TOURISM_BOMB_CONVERT_CITY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Convert` | 是 | `1` |

**效果**：摇滚乐队演出后转化目标城市的信仰宗教
> **溯源**：单位晋升 — 宗教摇滚（`PROMOTION_RELIGIOUS_ROCK`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_TOURISM_BOMB_DISTRICT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_TOURISM_BOMB_DISTRICT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `500` |
| `DistrictType` | 是 | `DISTRICT_CAMPUS`、`DISTRICT_COTHON`、`DISTRICT_HARBOR`、`DISTRICT_OBSERVATORY`、`DISTRICT_ROYAL_NAVY_DOCKYARD`、`DISTRICT_SEOWON` |

**效果**：摇滚乐队在指定区域演出时额外获得旅游业绩
> **溯源**：单位晋升 — 太空摇滚（`PROMOTION_SPACE_ROCK`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 冲浪摇滚（`PROMOTION_SURF_ROCK`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_TOURISM_BOMB_IMPROVEMENT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_TOURISM_BOMB_IMPROVEMENT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `500` |
| `ImprovementType` | 是 | `IMPROVEMENT_BEACH_RESORT` |

**效果**：摇滚乐队在指定改良设施上演出时额外获得旅游业绩
> **溯源**：单位晋升 — 冲浪摇滚（`PROMOTION_SURF_ROCK`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_TOURISM_BOMB_NATIONAL_PARK

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_TOURISM_BOMB_NATIONAL_PARK` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1000` |

**效果**：摇滚乐队在国家公园演出时额外获得旅游业绩
> **溯源**：单位晋升 — 音乐节（`PROMOTION_MUSIC_FESTIVAL`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_TOURISM_BOMB_NATURAL_WONDER

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_TOURISM_BOMB_NATURAL_WONDER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1000` |

**效果**：摇滚乐队在自然奇观演出时额外获得旅游业绩
> **溯源**：单位晋升 — 音乐节（`PROMOTION_MUSIC_FESTIVAL`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_TOURISM_BOMB_RANGE

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_TOURISM_BOMB_RANGE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Modifier` | 是 | `-50` |
| `Range` | 是 | `10` |

**效果**：调整摇滚乐队旅游业绩爆发的有效范围
> **溯源**：单位晋升 — 音量爆表（`PROMOTION_GOES_TO`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_YIELD_PER_TOURISM_BOMB

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_TOURISM_BOMB_ADDITIONAL_YIELD` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `-75` |
| `YieldType` | 是 | `YIELD_GOLD` |

**效果**：摇滚乐队旅游爆发时额外获得指定产出
> **溯源**：单位晋升 — 流行巨星（`PROMOTION_POP`） — 赋予单位晋升效果

---

