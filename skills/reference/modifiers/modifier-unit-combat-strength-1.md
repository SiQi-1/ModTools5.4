# modifier-unit-combat -- 单位战斗/属性/移动/经验/间谍/旅游/宗教等 EffectType — 战斗力/属性（1）

> 分册：由 [modifier-unit-combat.md](modifier-unit-combat.md) 按主题拆出；覆盖 战斗力/属性、EFFECT_ADJUST_ADJACENT_LEVIED_UNIT_COMBAT_BONUS、EFFECT_ADJUST_NUMBER_ALLIES_UNIT_COMBAT_BONUS、EFFECT_ADJUST_UNIT_AGAINST_DISTRICT_COMBAT_BONUS、EFFECT_ADJUST_UNIT_ANTI_AIR_STRENGTH、EFFECT_ADJUST_UNIT_ATTACK_RANGE、EFFECT_ADJUST_UNIT_ADVANCED_COASTAL_RAID、EFFECT_ADJUST_UNIT_ADVANCED_PILLAGING、EFFECT_ADJUST_UNIT_BARBARIAN_COMBAT、EFFECT_ADJUST_UNIT_BYPASS_COMBAT_UNIT、EFFECT_ADJUST_UNIT_BYPASS_WALLS、EFFECT_ADJUST_UNIT_BYPASS_WALLS_PROMOTION_CLASS、EFFECT_ADJUST_UNIT_CANNOT_ATTACK、EFFECT_ADJUST_UNIT_COMBAT_CAPTURE、EFFECT_ADJUST_UNIT_COMBAT_STRENGTH、EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER、EFFECT_ADJUST_UNIT_COMBAT_UNIT_CAPTURE、EFFECT_ADJUST_UNIT_CONVERTS_BARBARIANS、EFFECT_ADJUST_UNIT_DAMAGE、EFFECT_ADJUST_UNIT_DIPLO_VISIBILITY_COMBAT_MODIFIER、EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK、EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_PROMOTION_CLASS、EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_WHOLE_GAME_PROMOTION_CLASS、EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_WHOLE_GAME_SAME_RELIGION、EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_WHOLE_GAME_SAME_RELIGION_PROMOTION_CLASS、EFFECT_ADJUST_UNIT_ERA_STRENGTH_MODIFIER、EFFECT_ADJUST_UNIT_EVICT_PERCENT、EFFECT_ADJUST_UNIT_EXERT_ZOC。触发：改单位战斗力、属性、克制、攻城数值时。

## 战斗力/属性

### EFFECT_ADJUST_ADJACENT_LEVIED_UNIT_COMBAT_BONUS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_UNIT_ADJUST_COMBAT_FOR_ADJACENT_LEVIED_UNITS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `3` |

**效果**：调整相邻征召单位的近战战斗力（绝对值加成）
> **溯源**：单位能力 — 匈牙利黑军（`ABILITY_BLACK_ARMY`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_NUMBER_ALLIES_UNIT_COMBAT_BONUS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_UNIT_ADJUST_COMBAT_FOR_NUMBER_ALLIES` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `3` |

**效果**：根据相邻友军数量调整单位近战战斗力
> **溯源**：单位能力 — 克鲁兹起义军（`ABILITY_HUSZAR`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_AGAINST_DISTRICT_COMBAT_BONUS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_GOVERNOR_ADJUST_DISTRICT_COMBAT_BONUS` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `10` |

**效果**：调整单位对区域攻击时的战斗力加成
> **溯源**：总督晋升 — 塞拉斯克尔（`GOVERNOR_PROMOTION_SERASKER`） — 赋予总督晋升能力

---

### EFFECT_ADJUST_UNIT_ANTI_AIR_STRENGTH

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_SINGLE_UNIT_ADJUST_ANTI_AIR_STRENGTH_MODIFIER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `40` |

**效果**：调整单位的防空战斗力
> **溯源**：单位晋升 — 无人机防空（`PROMOTION_GDR_AA_DEFENSE`） — 赋予单位晋升效果（无人机防空）

---

### EFFECT_ADJUST_UNIT_ATTACK_RANGE

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_UNIT_ADJUST_ATTACK_RANGE` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_UNITS_ADJUST_ATTACK_RANGE` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1`、`2` |

**效果**：调整单位的攻击范围（射程）
> **溯源**：单位能力 — ABILITY_RECEIVE_RANGE_BONUS（`ABILITY_RECEIVE_RANGE_BONUS`） — 赋予单位特殊能力
> **溯源**：单位晋升 — 前方观察员（`PROMOTION_FORWARD_OBSERVERS`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 副油箱（`PROMOTION_DROP_TANKS`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 远程（`PROMOTION_LONG_RANGE`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 测距一致（`PROMOTION_COINCIDENCE_RANGEFINDING`） — 赋予单位晋升效果

---

### EFFECT_ADJUST_UNIT_ADVANCED_COASTAL_RAID

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_ADVANCED_COASTAL_RAID` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `UseAdvancedCoastalRaid` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：赋予单位高级海岸劫掠能力
> **溯源**：单位能力 — 海盗（`ABILITY_CORSAIR`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_ADVANCED_PILLAGING

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_ADVANCED_PILLAGING` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `UseAdvancedPillaging` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：赋予单位高级掠夺能力
> **溯源**：单位晋升 — 掠夺（`PROMOTION_DEPREDATION`） — 赋予单位晋升效果
> **溯源**：单位晋升 — 超级堡垒（`PROMOTION_SUPERFORTRESS`） — 赋予单位晋升效果
> **溯源**：单位能力 — ABILITY_MAPUCHE_MALON_RAIDER（`ABILITY_MAPUCHE_MALON_RAIDER`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_BARBARIAN_COMBAT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_BARBARIAN_COMBAT` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `15`、`5` |

**效果**：调整单位对蛮族的战斗力
> **溯源**：政策 — 纪律（`POLICY_DISCIPLINE`） — 通过政策卡提供加成
> **溯源**：文明/领袖特性 — 我来，我见，我征服（`TRAIT_LEADER_CAESAR`） — 文明或领袖特性效果


---

### EFFECT_ADJUST_UNIT_BYPASS_COMBAT_UNIT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_BYPASS_COMBAT_UNIT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Bypass` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：允许单位绕过敌方战斗单位移动
> **溯源**：单位能力 — 针对性攻击（`ABILITY_BYPASS_COMBAT_UNIT`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_BYPASS_WALLS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_BYPASS_WALLS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Enable` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：允许近战单位绕过城墙直接攻击市中心
> **溯源**：单位能力 — 绕开城墙（`ABILITY_BYPASS_WALLS`） — 赋予单位特殊能力（允许近战单位绕开城墙。）

---

### EFFECT_ADJUST_UNIT_BYPASS_WALLS_PROMOTION_CLASS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_BYPASS_WALLS_PROMOTION_CLASS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `PromotionClass` | 是 | `PROMOTION_CLASS_ANTI_CAVALRY`、`PROMOTION_CLASS_MELEE` |

**效果**：允许指定晋升类别的单位绕开城墙
> **溯源**：单位能力 — ABILITY_BYPASS_WALLS_PROMOTION_CLASS（`ABILITY_BYPASS_WALLS_PROMOTION_CLASS`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_CANNOT_ATTACK

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_CANNOT_ATTACK` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Disable` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：禁止单位发动攻击
> **溯源**：单位能力 — 和平卫士（`ABILITY_RELIGIOUS_CANNOT_ATTACK`） — 赋予单位特殊能力（阻止单位攻击。）

---

### EFFECT_ADJUST_UNIT_COMBAT_CAPTURE

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_UNIT_ADJUST_COMBAT_CAPTURE` | `COLLECTION_OWNER` |

| *(无参数)* | | |
|---|---|---|

**效果**：调整单位在战斗中俘获敌方单位的能力
> **溯源**：该 EffectType 仅在 DynamicModifiers 中注册，官方数据库中无实际 Modifier 使用记录

---

### EFFECT_ADJUST_UNIT_COMBAT_STRENGTH

调整单位的**基础战斗力**（直接加在 Combat/RangedCombat 属性上，UI 中显示为基础值变化）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_UNIT_ADJUST_BASE_COMBAT_STRENGTH` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数，绝对值加成 |
| `Type` | 可选 | `MELEE`=近战（Combat）/ `RANGED`=远程（RangedCombat）/ `ANTIAIR`=防空（AntiAirCombat）/ `BOMBARD`=轰炸（Bombard）。不填默认 MELEE |

```sql
INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
('MODIFIER_SIQI_UNIT_BASE_STRENGTH', 'Amount', '5'),
('MODIFIER_SIQI_UNIT_BASE_STRENGTH', 'Type', 'RANGED');
```

**效果**：直接修改单位面板上的基础战斗力，叠加在 Combat 或 RangedCombat 字段上。
> **溯源**：官方无 Modifiers 实例，工坊广泛使用。
> **不需要 ModifierStrings**（基础值变化直接在单位面板可见，无需额外 UI）

---

### EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER

调整单位在战斗中的**实际战斗力**（战斗上下文中生效，不影响基础面板值）。

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_UNIT_ADJUST_COMBAT_STRENGTH` | `COLLECTION_UNIT_COMBAT` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | **必写** | 整数，绝对值加成 |

**两种写法：**

| 写法 | 参数 | ModifierStrings | 说明 |
|------|------|----------------|------|
| **固定值** | `Amount='4'` | `+{1_Amount} [ICON_Strength] 战斗力` | `{1_Amount}` 解析为该 Modifier 的 Amount 值 |
| **变化值** | `Key='PROP_KEY'` | `+{Property} [ICON_Strength] 战斗力（来源）` | 战斗力取该 Property 当前值 |

Property 赋值方式（**二选一，不能混用**）：
- `EFFECT_ADJUST_UNIT_PROPERTY`（`Key='PROP_KEY'`，Amount=数值）
- Lua `UnitManager.SetProperty(unitId, 'PROP_KEY', value)`

```sql
-- 固定值写法（官方标准）
INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
('MODIFIER_SIQI_COMBAT_FIXED', 'Amount', '5');
-- 模式 A：LOC 引用 + {1_Amount}（数值动态读取）
INSERT INTO ModifierStrings (ModifierId, Context, Text) VALUES
('MODIFIER_SIQI_COMBAT_FIXED', 'Preview', 'LOC_COMBAT_FIXED_PREVIEW');
-- LOC_COMBAT_FIXED_PREVIEW = "进攻时+{1_Amount} [ICON_Strength] 战斗力"
-- UI 显示：进攻时+5 战斗力
-- 负值写法（设计意图为减益时）："防御时{1_Amount} [ICON_Strength] 战斗力"（不带 +）

-- 模式 B：晋升内联模板（数量多时统一格式，不建 LOC）
INSERT INTO ModifierStrings (ModifierId, Context, Text) VALUES
('MODIFIER_SIQI_COMBAT_FIXED', 'Preview', '+{1_Amount} {LOC_PROMOTION_SIQI_NAME} {LOC_PROMOTION_DESCRIPTOR_PREVIEW_TEXT}');
-- UI 显示：+5 思琪战吼 战斗力

-- 变化值写法（用 {Property} 显示属性值）
INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
('MODIFIER_SIQI_COMBAT_VAR', 'Key', 'PROP_COMBAT_BONUS');
INSERT INTO ModifierStrings (ModifierId, Context, Text) VALUES
('MODIFIER_SIQI_COMBAT_VAR', 'Preview', 'LOC_COMBAT_VAR_PREVIEW');
-- LOC_COMBAT_VAR_PREVIEW = "{Property} [ICON_Strength] 战斗力"
-- Property 值可为正或负，不加 + 前缀，负值时自动显示为 -5
```

> **溯源**：DEFENDER_OF_FAITH_COMBAT_BONUS_MODIFIER（守护者信仰，Amount=5）/ OLIGARCHY_MELEE_BUFF（寡头政体，Amount=4）/ ANTI_SPEAR（反骑兵晋升，Amount=10）等 20 个官方固定值实例。变化值（Key=Property 名）见工坊。
---

### EFFECT_ADJUST_UNIT_COMBAT_UNIT_CAPTURE

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_UNIT_ADJUST_COMBAT_UNIT_CAPTURE` | `COLLECTION_UNIT_COMBAT` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `CanCapture` | 是 | `1`（`1`=是 / `0`=否） |
| `UnitType` | 是 | `UNIT_BUILDER` |

**效果**：允许俘虏特定类型的敌方单位
> **溯源**：单位能力 — 被俘船（`ABILITY_PRIZE_SHIPS`） — 赋予单位特殊能力
> **溯源**：单位能力 — 俘获工人（`ABILITY_CAPTIVE_WORKERS`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_CONVERTS_BARBARIANS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_CONVERTS_BARBARIANS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Converts` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：赋予单位转化蛮族为己方单位的能力
> **溯源**：单位晋升 — 异教徒信仰转变（`PROMOTION_HEATHEN_CONVERSION`） — 赋予单位晋升效果
> **溯源**：单位能力 — ABILITY_QIN_MELEE_UNITS（`ABILITY_QIN_MELEE_UNITS`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_DAMAGE

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_DAMAGE` | `COLLECTION_PLAYER_UNITS` |
| `MODIFIER_PLAYER_UNIT_ADJUST_DAMAGE` | `COLLECTION_OWNER` |
| `MODIFIER_WORLD_UNITS_ADJUST_DAMAGE` | `COLLECTION_ALL_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `-100`、`30` |

**效果**：对单位造成直接伤害（正数=伤害，负数=治疗）
> **溯源**：伟人能力 — 安东尼奥·何塞·苏克雷（`GREAT_PERSON_INDIVIDUAL_COMMANDANTE_JOSE_DE_SUCRE`）
> **溯源**：伟人能力 — 弗朗西斯科·德保拉·桑坦德尔（`GREAT_PERSON_INDIVIDUAL_COMMANDANTE_PAULA_SANTANDER`）
> **溯源**：伟人能力 — 何塞·安东尼奥·派斯（`GREAT_PERSON_INDIVIDUAL_COMMANDANTE_ANTONIO_PAEZ`）
> **溯源**：伟人能力 — 拉斐尔·乌达内塔（`GREAT_PERSON_INDIVIDUAL_COMMANDANTE_URDANETA`）
> **溯源**：伟人能力 — 圣地亚哥·马里诺（`GREAT_PERSON_INDIVIDUAL_COMMANDANTE_MARINO`）

---

### EFFECT_ADJUST_UNIT_DIPLO_VISIBILITY_COMBAT_MODIFIER

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_DIPLO_VISIBILITY_COMBAT_MODIFIER` | `COLLECTION_PLAYER_UNITS` |
| `MODIFIER_ALL_UNITS_ADJUST_DIPLO_VISIBILITY_COMBAT_MODIFIER` | `COLLECTION_ALL_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `1`、`2`、`3` |
| `DeltaWithOpponent` | 是 | `1` |

**效果**：根据外交能见度差距提供战斗力加成
> **溯源**：文明/领袖特性 — 驿站（`TRAIT_CIVILIZATION_MONGOLIAN_ORTOO`） — 文明或领袖特性效果
> **溯源**：文明/领袖特性 — TRAIT_LEADER_MAJOR_CIV（`TRAIT_LEADER_MAJOR_CIV`） — 文明或领袖特性效果

---

### EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_ENABLE_WALL_ATTACK` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Enable` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：允许近战单位攻击城墙
> **溯源**：单位能力 — 启用城墙攻击（`ABILITY_ENABLE_WALL_ATTACK`） — 赋予单位特殊能力（允许近战单位攻击城墙。）

---

### EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_PROMOTION_CLASS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_ENABLE_WALL_ATTACK_PROMOTION_CLASS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `PromotionClass` | 是 | `PROMOTION_CLASS_ANTI_CAVALRY`、`PROMOTION_CLASS_MELEE` |

**效果**：允许指定晋升类别的单位攻击城墙
> **溯源**：单位能力 — ABILITY_ENABLE_WALL_ATTACK_PROMOTION_CLASS（`ABILITY_ENABLE_WALL_ATTACK_PROMOTION_CLASS`） — 赋予单位特殊能力

---

### EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_WHOLE_GAME_PROMOTION_CLASS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNITS_ADJUST_ENABLE_WALL_ATTACK_WHOLE_GAME_PROMOTION_CLASS` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `PromotionClass` | 是 | `PROMOTION_CLASS_ANTI_CAVALRY`、`PROMOTION_CLASS_MELEE`、`PROMOTION_CLASS_RANGED` |

**效果**：全局允许指定晋升类别的单位攻击城墙
> **溯源**：文明/领袖特性 — 里人格（`TRAIT_CIVILIZATION_NIGHTMARE`） — 文明或领袖特性效果

---

### EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_WHOLE_GAME_SAME_RELIGION

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_ENABLE_WALL_ATTACK_WHOLE_GAME_SAME_RELIGION` | `COLLECTION_OWNER` |

| *(无参数)* | | |
|---|---|---|

**效果**：全局允许相同宗教文明的单位攻击城墙

---

### EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_WHOLE_GAME_SAME_RELIGION_PROMOTION_CLASS

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_ADJUST_ENABLE_WALL_ATTACK_WHOLE_GAME_SAME_RELIGION_PROMOTION_CLASS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `PromotionClass` | 是 | `PROMOTION_CLASS_HEAVY_CAVALRY`、`PROMOTION_CLASS_LIGHT_CAVALRY` |

**效果**：全局允许同宗教文明指定晋升类别的单位攻击城墙
> **溯源**：文明/领袖特性 — 生于紫室（`TRAIT_LEADER_BASIL`） — 文明或领袖特性效果

---

### EFFECT_ADJUST_UNIT_ERA_STRENGTH_MODIFIER

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_ERA_STRENGTH_MODIFIER` | `COLLECTION_OWNER` |

| *(无参数)* | | |
|---|---|---|

**效果**：根据时代差异调整单位战斗力
> **溯源**：该 EffectType 仅在 DynamicModifiers 中注册，官方数据库中无实际 Modifier 使用记录

---

### EFFECT_ADJUST_UNIT_EVICT_PERCENT

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_EVICT_PERCENT` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_UNITS_ADJUST_EVICT_PERCENT` | `COLLECTION_PLAYER_UNITS` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Amount` | 是 | `25`、`50` |

**效果**：调整宗教单位驱逐敌方宗教的压力百分比
> **溯源**：单位晋升 — 劝导者（`PROMOTION_PROSELYTIZER`） — 赋予单位晋升效果
> **溯源**：文明/领袖特性 — 艾思科里亚（`TRAIT_LEADER_EL_ESCORIAL`） — 文明或领袖特性效果

---

### EFFECT_ADJUST_UNIT_EXERT_ZOC

| ModifierType | CollectionType |
|---|---|
| `MODIFIER_PLAYER_UNIT_ADJUST_EXERT_ZOC` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|---|---|---|
| `Exert` | 是 | `1`（`1`=是 / `0`=否） |

**效果**：赋予/移除单位的控制区（ZOC）能力
> **溯源**：单位晋升 — 压制（`PROMOTION_SUPPRESSION`） — 赋予单位晋升效果

---

