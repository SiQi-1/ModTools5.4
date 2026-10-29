# modifier-misc — 其余杂项类 EffectType — 时代/时代得分

> 分册：由 [modifier-misc.md](modifier-misc.md) 按主题拆出；覆盖 时代与时代得分、EFFECT_ADJUST_PLAYER_ALWAYS_ALLOW_COMMEMORATION_QUEST_COUNT、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_ARMY_KILLED、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_ARTIFACT_EXTRACTED、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_CIVIC_BOOST、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_CONTINENT_DISCOVERED、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_CORPS_KILLED、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_CURRENT_CIVIC、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_CURRENT_TECH、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_NATURAL_WONDER_DISCOVERED、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_PRIDE_MOMENT、EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_TECH_BOOST。触发：改时代与时代得分时。

## 时代与时代得分

### EFFECT_ADJUST_PLAYER_ALWAYS_ALLOW_COMMEMORATION_QUEST_COUNT

固定可完成的纪念任务数量。`Amount=1` 表示额外增加1个纪念任务。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PLAYER_ALWAYS_ALLOW_COMMEMORATION_QUEST_COUNT` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` |

> **溯源**：TraitModifiers — 塔玛丽（格鲁吉亚文明「团结多种力量」）

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_ARMY_KILLED

每击杀一个敌方军队（Army，3单位合并）时获得时代得分。`Amount=2`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PLAYER_ERA_SCORE_PER_ARMY_KILLED` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `2` |

> **溯源**：PolicyModifiers — 政策「全民动员」（POLICY_TOTAL_MOBILIZATION）

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_ARTIFACT_EXTRACTED

考古学家每提取一个文物时获得时代得分。`Amount=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PLAYER_ERA_SCORE_PER_ARTIFACT_EXTRACTED` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` |

> **溯源**：CommemorationModifiers — 纪念「愿您安息」（COMMEMORATION_IN_MEMORIAM）

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_CIVIC_BOOST

每次触发市政鼓舞时获得时代得分。`Amount=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PLAYER_ERA_SCORE_PER_CIVIC_BOOST` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` |

> **溯源**：CommemorationModifiers — 纪念「启蒙运动」（COMMEMORATION_ENLIGHTENMENT）

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_CONTINENT_DISCOVERED

每发现一个新大陆时获得时代得分。`Amount=3`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PLAYER_ERA_SCORE_PER_CONTINENT_DISCOVERED` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `3` |

> **溯源**：TraitModifiers — 毛利文明「人船合一」（TRAIT_CIVILIZATION_MAORI_MANA）

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_CORPS_KILLED

每击杀一个敌方军团（Corps，2单位合并）时获得时代得分。`Amount=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PLAYER_ERA_SCORE_PER_CORPS_KILLED` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` |

> **溯源**：PolicyModifiers — 政策「全民动员」（POLICY_TOTAL_MOBILIZATION）

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_CURRENT_CIVIC

完成与当前时代相同或更早的市政时额外获得时代得分（仅黑暗时代可触发，用于追赶）。无参数，由时代系统全局生效。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_ALL_PLAYERS_ADJUST_ERA_SCORE_PER_CURRENT_CIVIC` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 |
|---|
| （无参数） |

> **溯源**：Expansion1/2 DLC — `Expansion1_Modifiers.xml` / `Expansion2_Modifiers.xml` 声明，无数据库实例

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_CURRENT_TECH

完成与当前时代相同或更早的科技时额外获得时代得分（仅黑暗时代可触发，用于追赶）。无参数，由时代系统全局生效。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_ALL_PLAYERS_ADJUST_ERA_SCORE_PER_CURRENT_TECH` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 |
|---|
| （无参数） |

> **溯源**：Expansion1/2 DLC — `Expansion1_Modifiers.xml` / `Expansion2_Modifiers.xml` 声明，无数据库实例

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_NATURAL_WONDER_DISCOVERED

每发现一个自然奇观时获得时代得分。`Amount=3`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PLAYER_ERA_SCORE_PER_NATURAL_WONDER_DISCOVERED` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `3` |

> **溯源**：TraitModifiers — 毛利文明「人船合一」

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_PRIDE_MOMENT

每个光荣时刻获得额外时代得分。`MinScore=2` 表示基础分>=2 的光荣时刻才适用。`Amount=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PLAYER_ERA_SCORE_PER_PRIDE_MOMENT` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` |
| `MinScore` | `2` |

> **溯源**：BuildingModifiers — 泰姬陵奇观（BUILDING_TAJ_MAHAL）

---

### EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_TECH_BOOST

每次触发科技尤里卡时获得时代得分。`Amount=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PLAYER_ERA_SCORE_PER_TECH_BOOST` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` |

> **溯源**：CommemorationModifiers — 纪念「自由探索」（COMMEMORATION_FREE_INQUIRY）

---


