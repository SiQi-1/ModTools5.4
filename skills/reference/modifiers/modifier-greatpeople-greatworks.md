# modifier-greatpeople — 伟人/巨作类 EffectType — 巨作/旅游

> 分册：由 [modifier-greatpeople.md](modifier-greatpeople.md) 按主题拆出；覆盖 EFFECT_ADJUST_ALL_GREAT_WORKS_TOURISM_MODIFIER、EFFECT_ADJUST_ALL_GREAT_WORKS_YIELDS_MODIFIER、EFFECT_ADJUST_CITY_GREATWORK_YIELD、EFFECT_ADJUST_CITY_HOUSING_FROM_GREAT_WORKS、EFFECT_ADJUST_EXTRA_GREAT_WORK_SLOTS、EFFECT_ADJUST_GREAT_WORK_OBJECT_NO_TOURISM、EFFECT_ADJUST_GREAT_WORK_OBJECT_TOURISM_MODIFIER、EFFECT_ADJUST_IDENTITY_PER_TURN_FROM_NEARBY_GREAT_WORKS、EFFECT_ADJUST_LOYALTY_FROM_GREAT_WORKS_CITIZENS、EFFECT_GRANT_YIELD_PER_GREAT_WORK_IN_CITY。触发：改巨作、巨作旅游、巨作产出时。

## 巨作/旅游

### EFFECT_ADJUST_ALL_GREAT_WORKS_TOURISM_MODIFIER

所有巨作完成主题化后获得的旅游业绩加成（百分比）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_THEMED_TOURISM` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 百分比值（例：`100` = +100%）。仅对已完成主题化的巨作生效 |

> **溯源**：克里斯蒂娜领袖能力「**北方的弥涅耳瓦**」——拥有 3 个以上巨作槽位的建筑填满后自动主题化，且主题化巨作的旅游业绩 +100%（`Amount=100`）。

---

### EFFECT_ADJUST_ALL_GREAT_WORKS_YIELDS_MODIFIER

所有巨作完成主题化后获得的全部产出加成（百分比）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_THEMED_ALL_YIELDS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 百分比值（例：`100` = +100%）。仅对已完成主题化的巨作生效 |

> **溯源**：克里斯蒂娜领袖能力「**北方的弥涅耳瓦**」——填满巨作槽位自动主题化后，主题化巨作的所有基础产出 +100%（`Amount=100`）。与上一个 Effect 共同构成该能力的完整效果。

---

### EFFECT_ADJUST_CITY_GREATWORK_YIELD

城市中特定类型的巨作提供产出（每件巨作累加）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_CITIES_ADJUST_GREATWORK_YIELD` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_SINGLE_CITY_ADJUST_GREATWORK_YIELD` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `GreatWorkObjectType` | **必写** | 巨作对象类型。`GREATWORKOBJECT_WRITING / PORTRAIT / LANDSCAPE / SCULPTURE / RELIGIOUS / ARTIFACT / MUSIC / RELIC`（[GreatWorkObjectType.txt](../../SOURCES.md#类型与枚举)） |
| `YieldType` | **必写** | 产出类型。`YIELD_SCIENCE / CULTURE / GOLD / FAITH / PRODUCTION / FOOD`（YieldType.txt） |
| `YieldChange` | **必写** | 每件巨作的基础产出值（整数，与 `ScalingFactor` 配合使用） |
| `ScalingFactor` | **可选** | 产量倍率（整数，除以 100）。例：`ScalingFactor=300` + `YieldChange=2` → 每件巨作 +6 产出。不写时等同于 100（×1） |

> **溯源**：
> - 刚果文明能力「**精神实体**」——雕塑/文物/遗物分别提供 +2 食物、+2 生产力、+4 金币、+1 信仰（`YieldChange` 直接指定，无 `ScalingFactor`）
> - 城邦康提——遗物产出 +50% 信仰（`ScalingFactor=150`，无 `YieldChange`，DLL 内置基础值 × 1.5）
> - 领袖能力「**索格伦**」（松迪亚塔·凯塔）——巨作文字 +4 金币、+2 生产力
> - 领袖能力「**立陶宛联邦**」——遗物 +2 信仰、+2 文化、+4 金币
> - 政策卡「**手工艺品**」（Mod 自定）——多种巨作类型产出的 `ScalingFactor=300`（×3 倍）
> - 创立者信条「**圣物箱**」——遗物产出 ×3 信仰（`ScalingFactor=300`）

---

### EFFECT_ADJUST_CITY_HOUSING_FROM_GREAT_WORKS

按城市中存放的「产品」类巨作数量提供住房。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_SINGLE_CITY_ADJUST_CITY_HOUSING_FROM_GREAT_WORKS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| — | 无参数 | 效果内置，DLL 硬编码。不传参 |

> **溯源**：此 EffectType 虽名含 `GREAT_WORKS`，实际用于《垄断与公司》游戏模式的产品系统。产品（可可、盐、糖、蜂蜜等）通过 `GreatWorkModifiers` 表挂载到城市，每件产品提供固定住房量（DLL 内置逻辑，不在 ModifierArguments 中传参）。
> 
> 官方用法：`PRODUCT_CITY_GROWTH_HOUSING_COCOA` / `SALT` / `SUGAR` / `HONEY`，均挂载到对应的 `GREATWORK_PRODUCT_*` 巨作类型上，`SubjectStackLimit=1`。

---

### EFFECT_ADJUST_EXTRA_GREAT_WORK_SLOTS

为指定建筑增加巨作槽位。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_CITIES_ADJUST_EXTRA_GREAT_WORK_SLOTS` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_SINGLE_CITY_ADJUST_EXTRA_GREAT_WORK_SLOTS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 增加的槽位数（整数，例：`1`、`2`、`3`、`4`） |
| `BuildingType` | **必写** | 目标建筑。`BUILDING_PALACE / AMPHITHEATER / MARKET / MUSEUM_ARTIFACT / BANK / ...`（[BuildingType.txt](../../SOURCES.md#类型与枚举)） |
| `GreatWorkSlotType` | **必写** | 槽位类型。`GREATWORKSLOT_PALACE / WRITING / ARTIFACT / ART / MUSIC / CATHEDRAL / RELIC`（[GreatWorkSlotType.txt](../../SOURCES.md#类型与枚举)） |

> **溯源**：
> - 英国文明能力「**大英博物馆**」——考古博物馆 +3 文物槽位（`BuildingType=BUILDING_MUSEUM_ARTIFACT`，`GreatWorkSlotType=GREATWORKSLOT_ARTIFACT`，`Amount=3`）
> - 刚果文明能力「**精神实体**」——宫殿 +4 通用槽位（`BuildingType=BUILDING_PALACE`，`GreatWorkSlotType=GREATWORKSLOT_PALACE`，`Amount=4`）
> - 大商人「**乔凡尼·德·美第奇**」激活效果——银行 +2 通用槽位（`BuildingType=BUILDING_BANK`，`GreatWorkSlotType=GREATWORKSLOT_PALACE`，`Amount=2`）
> - 领袖能力「**索格伦**」（松迪亚塔·凯塔）——市场 +2 著作槽位（`BuildingType=BUILDING_MARKET`，`GreatWorkSlotType=GREATWORKSLOT_WRITING`，`Amount=2`）
> 
> `BuildingType` + `GreatWorkSlotType` 组合决定新增槽位挂到哪个建筑的哪种槽位类型。自定义 `GreatWorkSlotType` 需注意 UI 兼容性。

---

### EFFECT_ADJUST_GREAT_WORK_OBJECT_NO_TOURISM

禁止巨作产生旅游业绩（开关型效果）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_GREAT_WORK_OBJECT_NO_TOURISM` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `NoTourism` | **必写** | `1` = 禁止产生旅游业绩 |

> **溯源**：世界议会决议「**文化遗产组织**」——所有巨作的旅游业绩归零（`NoTourism=1`）。这是决议 A 面的效果。与 `EFFECT_ADJUST_GREAT_WORK_OBJECT_TOURISM_MODIFIER`（B 面效果）为同一决议的两种表决结果。

---

### EFFECT_ADJUST_GREAT_WORK_OBJECT_TOURISM_MODIFIER

调整巨作旅游业绩加成（百分比）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_GREAT_WORK_OBJECT_TOURISM` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 百分比值（例：`100` = +100%） |

> **溯源**：世界议会决议「**文化遗产组织**」——所有巨作旅游业绩 +100%（`Amount=100`）。这是决议 B 面的效果（A 面为完全禁止旅游业绩）。不区分巨作类型，对所有巨作全局生效。

---

### EFFECT_ADJUST_IDENTITY_PER_TURN_FROM_NEARBY_GREAT_WORKS

每回合按附近外国城市的巨作数量提供忠诚度压力。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_IDENTITY_PER_TURN_FROM_NEARBY_GREAT_WORKS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 每件巨作提供的忠诚度压力值（整数，例：`1`） |
| `ForeignCities` | **可选** | `1` = 仅计算外国城市巨作 |
| `DomesticCities` | **可选** | `1` = 仅计算本国城市巨作 |

> **溯源**：埃莉诺领袖能力「**爱之法庭**」——附近外国城市的每件巨作 -1 忠诚度/回合（`Amount=1`，`ForeignCities=1`）。`ForeignCities` 和 `DomesticCities` 互斥（二选一）。

---

### EFFECT_ADJUST_LOYALTY_FROM_GREAT_WORKS_CITIZENS

按城市中巨作数量调整忠诚度压力（从公民产出）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_CITIES_ADJUST_ADJUST_LOYALTY_FROM_GREAT_WORKS_CITIZENS` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | 按需 | 忠诚度修正值（整数）。效果由 DLL 内置逻辑决定 |

> **溯源**：此 EffectType 在官方 XML 中仅定义了 `DynamicModifiers` 条目，**无任何官方 Modifier 使用**。效果逻辑由 DLL 硬编码，参数需通过 DLL 源码或实验确定。ModifierType 名含双 `ADJUST_ADJUST`（官方命名冗余）。实际使用时建议先检查官方后续 DLC/游戏模式是否有使用该 EffectType 的实例。

---

### EFFECT_GRANT_YIELD_PER_GREAT_WORK_IN_CITY

城市中每件指定类型的巨作提供一次性产出。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_SINGLE_CITY_GRANT_YIELD_PER_GREAT_WORK` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 每件巨作提供的一次性产出值（整数，例：`350`） |
| `GreatWorkObjectType` | **必写** | 巨作对象类型。`GREATWORKOBJECT_ARTIFACT / WRITING / ...`（[GreatWorkObjectType.txt](../../SOURCES.md#类型与枚举)） |
| `YieldType` | **必写** | 产出类型。`YIELD_SCIENCE / CULTURE / GOLD / FAITH / PRODUCTION / FOOD`（YieldType.txt） |

> **溯源**：大科学家「**玛丽·利基**」激活效果——所在城市每件文物提供 350 科技（`Amount=350`，`GreatWorkObjectType=GREATWORKOBJECT_ARTIFACT`，`YieldType=YIELD_SCIENCE`）。注意：此为**一次性产出**（Grant），非每回合持续产出。触发时机为伟人激活的瞬间，数量按城市当时拥有的指定巨作数量计算。

---

