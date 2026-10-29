# modifier-misc — 其余杂项类 EffectType — 旅游/忠诚

> 分册：由 [modifier-misc.md](modifier-misc.md) 按主题拆出；覆盖 旅游与文化胜利、EFFECT_ADJUST_PLAYER_OVERALL_TOURISM_REDUCTION、EFFECT_ADJUST_PLAYER_TOURISM、EFFECT_ADJUST_PLAYER_TOURISM_FROM_NATIONAL_PARKS、EFFECT_ADJUST_TRAIT_AMENITY、EFFECT_GRANT_TOURISM_PER_EXCESS_LUXURIES、忠诚度与身份压力、EFFECT_ADJUST_IGNORE_IDENTITY_PRESSURE、EFFECT_ADJUST_PLAYER_ALWAYS_LOYAL_COASTAL_HOME_CONTINENT、EFFECT_ADJUST_PLAYER_CULTURAL_IDENTITY_PRESSURE_RADIUS_FROM_CAPITAL、EFFECT_ADJUST_PLAYER_LOYALTY_MARTIAL_LAW_MODIFIER、EFFECT_ADJUST_PLAYER_POST_COMBAT_LOYALTY、EFFECT_ADJUST_PLAYER_POST_PILLAGE_LOYALTY。触发：改旅游文化胜利、忠诚度压力时。

## 旅游与文化胜利

### EFFECT_ADJUST_PLAYER_OVERALL_TOURISM_REDUCTION

调整整体旅游业绩效的衰减比例（不同政体/意识形态会减少对他文明的旅游输出）。`Modifier=20` 表示降低20%衰减。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_OVERALL_TOURISM_REDUCTION` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Modifier` | `20` |

> **溯源**：PolicyModifiers — 政策「线上社群」（POLICY_ONLINE_COMMUNITIES）

---

### EFFECT_ADJUST_PLAYER_TOURISM

调整玩家的总旅游业绩效值（百分比）。影响对他文明的文化压力。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TOURISM` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `-10` / `100` / `25` |

> **溯源**：TraitModifiers（罗斯福、法国等）; GovernmentModifiers（政体加成）

---

### EFFECT_ADJUST_PLAYER_TOURISM_FROM_NATIONAL_PARKS

调整国家公园提供的旅游业绩效百分比。`Amount=100` 表示翻倍。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TOURISM_FROM_NATIONAL_PARKS` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `100` |

> **溯源**：CommemorationModifiers — 纪念「愿您安息」

---

### EFFECT_ADJUST_TRAIT_AMENITY

调整城市宜居度（来自领袖/文明特性）。虽然名含 `TRAIT`，但可通用于任何来源。`Amount=1/2/3`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_TRAIT_AMENITY` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `1` / `2` / `3` |

> **溯源**：TraitModifiers（蒙特祖玛、佩德罗二世、亚历山大等领袖特性）

---

### EFFECT_GRANT_TOURISM_PER_EXCESS_LUXURIES

每种多余的奢侈资源提供额外旅游业绩效。`Amount=50` 表示每种多余奢侈资源+50%旅游业绩效。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GRANT_TOURISM_PER_EXCESS_LUXURIES` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `50` |

> **溯源**：BuildingModifiers — 马拉卡纳体育场奇观（BUILDING_MARACANA）

---


## 忠诚度与身份压力

### EFFECT_ADJUST_IGNORE_IDENTITY_PRESSURE

使所在城市忽略来自其他文明的身份压力（忠诚度不受外部文化影响）。`Ignore=1` 启用。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_GOVERNOR_ADJUST_IGNORE_CULTURAL_IDENTITY` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Ignore` | `1` |

> **溯源**：GovernorPromotionModifiers — 总督「维克多」的晋升能力

---

### EFFECT_ADJUST_PLAYER_ALWAYS_LOYAL_COASTAL_HOME_CONTINENT

使首都大陆上的沿海城市永久保持满忠诚度。无参数。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_ALWAYS_LOYAL_COASTAL_HOME_CONTINENT` | `COLLECTION_OWNER` |

| 参数 |
|---|
| （无参数） |

> **溯源**：TraitModifiers — 腓尼基文明「地中海殖民地」（TRAIT_CIVILIZATION_PHOENICIA_MEDITERRANEAN_COLONIES）

---

### EFFECT_ADJUST_PLAYER_CULTURAL_IDENTITY_PRESSURE_RADIUS_FROM_CAPITAL

调整首都向外传播身份压力的半径。无参数。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_PLAYER_CULTURAL_IDENTITY_PRESSURE_RADIUS_FROM_CAPITAL` | `COLLECTION_OWNER` |

| 参数 |
|---|
| （无参数） |

> **溯源**：Expansion1/2 DLC — 仅 XML 声明，无数据库实例

---

### EFFECT_ADJUST_PLAYER_LOYALTY_MARTIAL_LAW_MODIFIER

调整戒严令驻军的忠诚度加成值。`Amount=5` 表示驻军额外+5忠诚度。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_LOYALTY_ADJUST_MARTIAL_LAW_MODIFIER` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `-3` / `5` / `7` |

> **溯源**：PolicyModifiers — 政策「限制令」（POLICY_LIMITANEI，巴比伦特性）

---

### EFFECT_ADJUST_PLAYER_POST_COMBAT_LOYALTY

战斗胜利后降低敌方城市的忠诚度。`Amount=-20`；`AdditionalGoldenAge=-20` 黄金时代额外再降。`AffectLocal=0` 仅影响战斗城市。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_POST_COMBAT_LOYALTY` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `AdditionalGoldenAge` | `-20` |
| `AffectLocal` | `0` |
| `Amount` | `-20` |

> **溯源**：TraitModifiers — 奥斯曼文明「迅捷之鹰」（TRAIT_CIVILIZATION_OTTOMAN_SULEIMAN）

---

### EFFECT_ADJUST_PLAYER_POST_PILLAGE_LOYALTY

掠夺敌方地块后降低敌方城市的忠诚度。`Amount=-5`。`AffectLocal=0`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_POST_PILLAGE_LOYALTY` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `AffectLocal` | `0` |
| `Amount` | `-5` |

> **溯源**：无固定上游（通用效果）

---


