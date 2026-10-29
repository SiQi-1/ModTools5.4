# modifier-misc — 其余杂项类 EffectType — 战争/战斗

> 分册：由 [modifier-misc.md](modifier-misc.md) 按主题拆出；覆盖 战争与好战、EFFECT_ADJUST_PLAYER_ALLIED_WAR_DISCOUNT、EFFECT_ADJUST_PLAYER_ENFORCE_BORDERS、EFFECT_ADJUST_PLAYER_JOINTWAR_EXPERIENCE、EFFECT_ADJUST_PLAYER_JOINTWAR_PLUNDER、EFFECT_ADJUST_PLAYER_LEVY_DISCOUNT_PERCENT、EFFECT_ADJUST_PLAYER_MAX_WARMONGER_PERCENT、EFFECT_ADJUST_PLAYER_NO_OCCUPATION_PENALTIES、EFFECT_ADJUST_PLAYER_WARMONGER_MULTIPLIER、EFFECT_ADJUST_WAR_WEARINESS、战斗与单位、EFFECT_ADJUST_ATTACKER_STRENGTH_MODIFIER、EFFECT_ADJUST_CORPS_ARMY_MODIFIED_STRENGTH、EFFECT_ADJUST_CORPS_ARMY_PREREQ、EFFECT_ADJUST_DEFENDER_STRENGTH_MODIFIER、EFFECT_ADJUST_DISABLE_HEALING、EFFECT_ADJUST_HEAL_CHARGES、EFFECT_ADJUST_PLAYER_HEALING_FROM_DISPERSAL、EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER、EFFECT_GRANT_COMBAT_ADJACENCY、EFFECT_GRANT_HEAL_AFTER_ACTION、EFFECT_GRANT_PROMOTION、EFFECT_GRANT_RANDOM_BASE_PROMOTION。触发：改战争好战、战斗单位类杂项效果时。

## 战争与好战

### EFFECT_ADJUST_PLAYER_ALLIED_WAR_DISCOUNT

调整发起同盟战争的折扣。`Discount=150` 表示成本降低150。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_ALLIED_WAR_DISCOUNT` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Discount` | `150` |

> **溯源**：TraitModifiers — 加拿大文明「和平秩序」（TRAIT_CIVILIZATION_CANADA_PEACE_ORDER）

---

### EFFECT_ADJUST_PLAYER_ENFORCE_BORDERS

强制拒绝所有开放边境请求。`Enable=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_ENFORCE_BORDERS` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Enable` | `1` |

> **溯源**：PolicyModifiers — 政策「帝国卫队」（POLICY_IMPERIAL_GUARD）

---

### EFFECT_ADJUST_PLAYER_JOINTWAR_EXPERIENCE

联合作战中我方单位战斗获得额外经验。`Range=5` 表示5格范围内有效。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_JOINTWAR_EXPERIENCE` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Range` | `5` |

> **溯源**：TraitModifiers — 加拿大文明「和平秩序」

---

### EFFECT_ADJUST_PLAYER_JOINTWAR_PLUNDER

联合作战中掠夺收益倍数调整。`Multiplier=100` 表示+100%。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_JOINTWAR_PLUNDER` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Multiplier` | `100` |

> **溯源**：TraitModifiers — 加拿大文明「和平秩序」

---

### EFFECT_ADJUST_PLAYER_LEVY_DISCOUNT_PERCENT

调整征募城邦单位的金币折扣百分比。`Percent=50`（半价）/`75`（二五折）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_LEVY_DISCOUNT_PERCENT` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Percent` | `50` / `75` |

> **溯源**：PolicyModifiers（外交政策）; BuildingModifiers（马丘比丘等）

---

### EFFECT_ADJUST_PLAYER_MAX_WARMONGER_PERCENT

调整最大好战程度的上限百分比。`MaxPercent=100`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_MAX_WARMONGER_PERCENT` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `MaxPercent` | `100` |

> **溯源**：PolicyModifiers — 政策「限制令」

---

### EFFECT_ADJUST_PLAYER_NO_OCCUPATION_PENALTIES

取消占领城市的生产力/科研/文化惩罚。`NoPenalties=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_NO_OCCUPATION_PENALTIES` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `NoPenalties` | `1` |

> **溯源**：无特定上游（通用效果）

---

### EFFECT_ADJUST_PLAYER_WARMONGER_MULTIPLIER

调整好战惩罚的倍率。`Amount=0` 表示完全免疫好战惩罚。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_WARMONGER_MULTIPLIER` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `0` |

> **溯源**：无特定上游（通用效果）

---

### EFFECT_ADJUST_WAR_WEARINESS

调整厌战情绪的累积量。`Domestic=1` 影响国内厌战，`Enemy=1` 影响敌方厌战，`Overall=1` 影响总厌战。正值增加厌战（不利），负值减少厌战（有利）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_WAR_WEARINESS` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `-100` / `-25` / `100` / `20` |
| `Domestic` | `1` |
| `Enemy` | `1` |
| `Overall` | `1` / `true` |

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_EMERGENCY_PLAYERS_ADJUST_WAR_WEARINESS` | `COLLECTION_EMERGENCY_PLAYERS` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `50` |
| `Overall` | `1` |

> **溯源**：TraitModifiers（亚历山大、居鲁士、托米丽司、成吉思汗等）; PolicyModifiers; EmergencyRewards

---


## 战斗与单位

### EFFECT_ADJUST_ATTACKER_STRENGTH_MODIFIER

在紧急事件中调整所有参与方攻击时的战斗力。仅用于 `COLLECTION_EMERGENCY_COMBATS`。`Amount=2` 增强攻击方。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_EMERGENCY_COMBATS_ADJUST_ATTACKER_STRENGTH` | `COLLECTION_EMERGENCY_COMBATS` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `-2` / `-3` / `2` |

> **溯源**：EmergencyBuffs — 紧急事件加成系统

---

### EFFECT_ADJUST_CORPS_ARMY_MODIFIED_STRENGTH

调整军团/军队的额外战斗力加成。`Corps=1`=军团（2单位合并），`Corps=0`=军队（3单位合并）。`DOMAIN_LAND` 限定陆军。`Amount=5`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CORPS_ARMY_MODIFIED_STRENGTH` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `5` |
| `Corps` | `0` / `1` |
| `Domain` | `DOMAIN_LAND` |

> **溯源**：PolicyModifiers — 政策「军事传统」（POLICY_MILITARY_TRADITION）

---

### EFFECT_ADJUST_CORPS_ARMY_PREREQ

调整军团/军队所需的前置科技/市政（提前解锁合并功能）。`Corps=1`=军团/`0`=军队。`Domain` 区分陆军/海军。`CivicType` 指定解锁市政。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_CORPS_ARMY_PREREQ` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `CivicType` | `CIVIC_MERCANTILISM` / `CIVIC_MERCENARIES` / `CIVIC_NATIONALISM` |
| `Corps` | `0` / `1` |
| `Domain` | `DOMAIN_LAND` / `DOMAIN_SEA` |

> **溯源**：TraitModifiers（祖鲁「部落荣耀」）; CivicModifiers（军事传统/民族主义等）

---

### EFFECT_ADJUST_DEFENDER_STRENGTH_MODIFIER

在紧急事件中调整所有参与方防守时的战斗力。仅用于 `COLLECTION_EMERGENCY_COMBATS`。`Amount=-2/-3`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_EMERGENCY_COMBATS_ADJUST_DEFENDER_STRENGTH` | `COLLECTION_EMERGENCY_COMBATS` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `-2` / `-3` |

> **溯源**：EmergencyBuffs — 紧急事件加成系统

---

### EFFECT_ADJUST_DISABLE_HEALING

禁用单位的生命恢复。`Disable=1` 禁止恢复，`Foreign=1` 禁止在外国领土恢复。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_DISABLE_HEALING` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Disable` | `1` |
| `Foreign` | `0` / `1` |

> **溯源**：UnitAbilityModifiers — 单位能力「暮光之幕」（ABILITY_TWILIGHT_VEIL）

---

### EFFECT_ADJUST_HEAL_CHARGES

调整单位的治疗次数/充能数（如宗教单位的传播次数）。`Amount` 为充能数调整量。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_HEAL_CHARGES` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | 整数，充能数调整量 |

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_CITY_HEAL_SPREADS` | `COLLECTION_CITY_TRAINED_UNITS` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | 整数，充能数调整量 |

> **溯源**：DynamicModifiers 定义（Base `Modifiers.xml`），游戏中无活跃 DB 实例

---

### EFFECT_ADJUST_PLAYER_HEALING_FROM_DISPERSAL

清除蛮族营地时玩家所有单位获得治疗。`Amount=100` 表示完全恢复。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_HEALING_FROM_DISPERSAL` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `100` |

> **溯源**：无特定上游（通用蛮族清除效果）

---

### EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER

调整玩家单位在战斗中的战斗力加成。`Amount` 为加成值（正值增强，负值削弱）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_COMBAT_STRENGTH` | `COLLECTION_PLAYER_COMBAT` |

| 参数 | 值/引用 |
|---|---|
| `Amount` | `-5` / `-3` / `3` / `5` / `7` / `10` 等，整数 |

> **溯源**：TraitModifiers（红胡子、成吉思汗等）; UnitAbilityModifiers; PolicyModifiers

---

### EFFECT_GRANT_COMBAT_ADJACENCY

授予战斗相邻加成（支援/夹击系统）。`Enable=1`。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_GRANT_COMBAT_ADJACENCY` | `COLLECTION_OWNER` |

| 参数 | 值/引用 |
|---|---|
| `Enable` | `1` |

> **溯源**：CivicModifiers — 市政「军事传统」（CIVIC_MILITARY_TRADITION）

---

### EFFECT_GRANT_HEAL_AFTER_ACTION

单位行动后自动恢复生命值（移动/攻击后回复固定血量）。无参数。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_GRANT_HEAL_AFTER_ACTION` | `COLLECTION_OWNER` |

| 参数 |
|---|
| （无参数） |

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_GRANT_HEAL_AFTER_ACTION` | `COLLECTION_PLAYER_UNITS` |

| 参数 |
|---|
| （无参数） |

> **溯源**：UnitPromotionModifiers（多种战斗晋升）; UnitAbilityModifiers; PolicyModifiers

---

### EFFECT_GRANT_PROMOTION

直接授予指定类型晋升。`PromotionType` 可选 GDR 升级晋升或殉道者晋升等。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_GRANT_PROMOTION` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 值/引用 |
|---|---|
| `PromotionType` | `PROMOTION_GDR_AA_DEFENSE` / `PROMOTION_GDR_ARMOR_UPGRADE` / `PROMOTION_GDR_BONUS_MOVEMENT` / `PROMOTION_GDR_SIEGE_LASER` / `PROMOTION_MARTYR` |

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_UNITS_GRANT_PROMOTION` | `COLLECTION_ALL_UNITS` |

| 参数 |
|---|
| （无参数） |

> **溯源**：BuildingModifiers — 圣米歇尔山奇观（BUILDING_MONT_ST_MICHEL），新建传教单位赠送殉道者晋升

---

### EFFECT_GRANT_RANDOM_BASE_PROMOTION

授予一项随机基础晋升。对全体主要玩家或指定玩家生效。无参数。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_GRANT_RANDOM_BASE_PROMOTION` | `COLLECTION_OWNER` |

| 参数 |
|---|
| （无参数） |

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_MAJOR_PLAYERS_GRANT_BASE_PROMOTION` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 |
|---|
| （无参数） |

> **溯源**：Base + GranColombia DLC — 多个文明/领袖特性（如大哥伦比亚）使用

---


