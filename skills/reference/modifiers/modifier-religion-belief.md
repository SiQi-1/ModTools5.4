# modifier-religion -- 宗教类 EffectType — 信条/信仰收益

> 分册：由 [modifier-religion.md](modifier-religion.md) 按主题拆出；覆盖 EFFECT_ADD_BELIEF、EFFECT_ADD_PLAYER_BELIEF_YIELD、EFFECT_ADD_RELIGIOUS_BELIEF_YIELD、EFFECT_ADD_RELIGIOUS_BUILDING、EFFECT_ADD_RELIGIOUS_BUILDING_MULTIPLIER、EFFECT_ADJUST_GAINS_ALL_FOLLOWER_BELIEFS、EFFECT_ADJUST_GAINS_FOUNDER_BELIEF_MAJORITY_RELIGION、EFFECT_ADJUST_PLAYER_ALWAYS_FULL_RELIGIOUS_TOURISM、EFFECT_ADJUST_PLAYER_RELIGIOUS_TOURISM_REDUCTION、EFFECT_ADJUST_RELIGION_AMENITIES_FOR_MINIMUM_FOLLOWERS、EFFECT_ADJUST_RELIGION_ANYONE_CONDEMNS_FAVOR、EFFECT_ADJUST_RELIGION_BUILDING_DISCOUNT、EFFECT_ADJUST_RELIGION_CONDEMN_PROHIBITED、EFFECT_ADOPT_ALLY_FOUNDED_RELIGIONS、EFFECT_ALLIANCE_YIELD_INCOME_FROM_ALLY_RELIGION、EFFECT_ENABLE_RELIGION_AWARDS_ENVOY。触发：改信条、追随者/创立者收益、宗教建筑、外交谴责时。

## 信条/信仰收益

### EFFECT_ADD_BELIEF

为玩家新增一条信条（直接添加到宗教信条列表中）。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_ADD_BELIEF` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `BeliefType` | **必写** | `BELIEF_CHURCH_PROPERTY` 等，引用 [Beliefs.BeliefType] |

> **溯源**：DynamicModifiers 定义于 `Modifiers.xml`，游戏中无活跃 DB 实例。效果是直接给玩家挂载一条信条，与宗教信条选择面板解耦，常用于文明/领袖特质绕过正常信条获取流程。

---

### EFFECT_ADD_PLAYER_BELIEF_YIELD

根据信念产出模式，为拥有该宗教的玩家添加产出（与 `EFFECT_ADD_RELIGIOUS_BELIEF_YIELD` 共享同一套 `BeliefYieldType` 体系，但参数更简洁）。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_RELIGION_ADD_PLAYER_BELIEF_YIELD` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，产出量 |
| `BeliefYieldType` | **必写** | `BELIEF_YIELD_PER_CITY` / `BELIEF_YIELD_PER_FOLLOWER` / `BELIEF_YIELD_PER_FOREIGN_FOLLOWER` / `BELIEF_YIELD_PER_DISTRICT` / `BELIEF_YIELD_PER_FOREIGN_CITY` / `BELIEF_YIELD_PER_CITY_WITH_WONDER` |
| `PerXItems` | **必写** | 整数，每 X 个单位触发一次（如每 1 个外国城市、每 4 个信徒） |
| `YieldType` | **必写** | `YIELD_FAITH` / `YIELD_GOLD` / `YIELD_CULTURE` / `YIELD_SCIENCE` 等，引用 [Yields.YieldType] |

> **溯源**：阿拉伯 — 最后的预言家（`TRAIT_CIVILIZATION_LAST_PROPHET`）— 每个信奉阿拉伯宗教的外国城市 +1 科技值（`BeliefYieldType=BELIEF_YIELD_PER_FOREIGN_CITY`, `Amount=1`, `YieldType=YIELD_SCIENCE`）。与 `EFFECT_ADD_RELIGIOUS_BELIEF_YIELD` 类似但参数模型不同，此版本无 `DistrictType` 参数。

---

### EFFECT_ADD_RELIGIOUS_BELIEF_YIELD

为拥有该宗教的玩家添加一种信条产出，覆盖全部六种 `BELIEF_YIELD_*` 模式。是信条产出体系中最核心的 EffectType。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_RELIGION_ADD_RELIGIOUS_BELIEF_YIELD` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，产出量 |
| `BeliefYieldType` | **必写** | `BELIEF_YIELD_PER_CITY` / `BELIEF_YIELD_PER_FOLLOWER` / `BELIEF_YIELD_PER_FOREIGN_FOLLOWER` / `BELIEF_YIELD_PER_DISTRICT` / `BELIEF_YIELD_PER_FOREIGN_CITY` / `BELIEF_YIELD_PER_CITY_WITH_WONDER` |
| `DistrictType` | `PER_DISTRICT` 时**必写** | `DISTRICT_HOLY_SITE` / `DISTRICT_THEATER` / `DISTRICT_CAMPUS` / `DISTRICT_COMMERCIAL_HUB`，引用 [Districts.DistrictType] |
| `PerXItems` | **必写** | 整数，每 X 个单位触发一次（如每 1 个城市、每 4 个信徒） |
| `YieldType` | **必写** | `YIELD_FAITH` / `YIELD_GOLD` / `YIELD_CULTURE` / `YIELD_SCIENCE` 等，引用 [Yields.YieldType] |

> **溯源**（DB 中 17 个活跃实例，均为信条）：
> - **教会财产**（`BELIEF_CHURCH_PROPERTY`，创立者信条）— 每座信奉此宗教的城市 +2 金币（`PER_CITY`）
> - **什一税**（`BELIEF_TITHE`，创立者信条）— 每 4 个信徒 +1 金币（`PER_FOLLOWER`，原版）；每座城市 +3 金币（`PER_CITY`，DLC 调整版）
> - **普世教会**（`BELIEF_WORLD_CHURCH`，创立者信条）— 其他文明每 5 个信徒 +1 文化值（`PER_FOREIGN_FOLLOWER`）；每 4 个信徒 +1 文化值（`PER_FOLLOWER`）
> - **跨文化对话**（`BELIEF_CROSS_CULTURAL_DIALOGUE`，创立者信条）— 其他文明每 5 个信徒 +1 科技值（`PER_FOREIGN_FOLLOWER`）；每 4 个信徒 +1 科技值（`PER_FOLLOWER`）
> - **朝圣**（`BELIEF_PILGRIMAGE`，创立者信条）— 每个外国信奉城市 +2 信仰值（`PER_FOREIGN_CITY`）；每座城市 +2 信仰值（`PER_CITY`）
> - **民间宗教团**（`BELIEF_LAY_MINISTRY`，信徒信条）— 圣地 +1 信仰值（`PER_DISTRICT`, `DISTRICT_HOLY_SITE`）；剧院广场 +1 文化值（`PER_DISTRICT`, `DISTRICT_THEATER`）
> - **管理工作**（`BELIEF_STEWARDSHIP`，信徒信条）— 学院 +1 科技值（`PER_DISTRICT`, `DISTRICT_CAMPUS`）；商业中心 +1 金币（`PER_DISTRICT`, `DISTRICT_COMMERCIAL_HUB`）
> - **神圣之地**（`BELIEF_SACRED_PLACES`，信徒信条）— 拥有奇观的城市 +2 信仰值/文化值/科技值/金币（`PER_CITY_WITH_WONDER`，四种产出各一个 Modifier）

---

### EFFECT_ADD_RELIGIOUS_BUILDING

允许拥有该宗教的玩家在圣地中建造指定的宗教建筑。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_RELIGION_ADD_RELIGIOUS_BUILDING` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `BuildingType` | **必写** | `BUILDING_CATHEDRAL` / `BUILDING_GURDWARA` / `BUILDING_MEETING_HOUSE` / `BUILDING_MOSQUE` / `BUILDING_PAGODA` / `BUILDING_SYNAGOGUE` / `BUILDING_WAT` / `BUILDING_STUPA` / `BUILDING_DAR_E_MEHR`，引用 [Buildings.BuildingType] |

> **溯源**（DB 中 9 个实例，均为崇拜信条 `BELIEF_CLASS_WORSHIP`）：
> - **大教堂**（`BELIEF_CATHEDRAL`）— +3 信仰值，1 个宗教艺术槽位
> - **谒师所**（`BELIEF_GURDWARA`）— +3 信仰值，+2 食物
> - **礼拜堂**（`BELIEF_MEETING_HOUSE`）— +3 信仰值，+2 生产力
> - **清真寺**（`BELIEF_MOSQUE`）— +3 信仰值，传教士/使徒传播次数 +1
> - **宝塔**（`BELIEF_PAGODA`）— +3 信仰值，+1 住房
> - **犹太教堂**（`BELIEF_SYNAGOGUE`）— +5 信仰值
> - **佛寺**（`BELIEF_WAT`）— +3 信仰值，+2 科技值
> - **窣堵波**（`BELIEF_STUPA`）— +3 信仰值，+1 宜居度
> - **拜火神庙**（`BELIEF_DAR_E_MEHR`）— +3 信仰值，每个时代额外 +1 信仰值

---

### EFFECT_ADD_RELIGIOUS_BUILDING_MULTIPLIER

对宗教建筑的产出施加百分比倍率加成（用于特质而非信条）。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_ADD_RELIGIOUS_BUILDING_MULTIPLIER` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Founder` | **可选** | `1` = 仅对创立者信条相关建筑生效，`0` 或不写 = 对所有相关建筑生效 |
| `Multiplier` | **必写** | 整数（百分比），产出倍率加成。`10` = +10% |
| `YieldType` | **必写** | `YIELD_CULTURE` / `YIELD_FAITH` / `YIELD_SCIENCE`，引用 [Yields.YieldType] |

> **溯源**：萨拉丁 — 正义的信仰（`TRAIT_LEADER_RIGHTEOUSNESS_OF_FAITH`）— 宗教建筑的文化值/信仰值/科技值 +10%（三个 Modifier，各对一种产出）。

---

### EFFECT_ADJUST_GAINS_ALL_FOLLOWER_BELIEFS

玩家获得其主流宗教所拥有的全部信徒信条加成（即使该玩家并非创立者）。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_GAINS_ALL_FOLLOWER_BELIEFS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Enable` | **必写** | `1` 启用 |

> **溯源**：**达摩**（`TRAIT_CIVILIZATION_DHARMA`，印度文明特质）— 从城市的每个宗教获得信徒信条加成（`Enable=1`）。

---

### EFFECT_ADJUST_GAINS_FOUNDER_BELIEF_MAJORITY_RELIGION

玩家获得其多数宗教的创立者信条加成（即使该玩家并非该宗教的创立者）。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_GAINS_FOUNDER_BELIEF_MAJORITY_RELIGION` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Enable` | **必写** | `1` 启用 |

> **溯源**：**宗教皈依者**（`TRAIT_LEADER_RELIGIOUS_CONVERT`，刚果姆本巴·恩津加特质）— 无法创建宗教，但获得己方多数宗教的创立者信条加成（`Enable=1`）。

---

### EFFECT_ADJUST_PLAYER_ALWAYS_FULL_RELIGIOUS_TOURISM

玩家始终获得全部宗教旅游业绩，不受不同宗教的 -50% 惩罚影响。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_ADJUST_ALWAYS_FULL_RELIGIOUS_TOURISM` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Enable` | **必写** | `1` 启用完全宗教旅游业绩 |

> **溯源**：**基督像**（`BUILDING_CRISTO_REDENTOR`，奇观建筑）— 圣遗物的旅游业绩值不会被启蒙运动等削减，宗教旅游业绩翻倍且不受不同宗教惩罚（`Enable=1`）。

---

### EFFECT_ADJUST_PLAYER_RELIGIOUS_TOURISM_REDUCTION

调整玩家因宗教差异遭受的旅游业绩削减百分比。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_ADJUST_RELIGIOUS_TOURISM_REDUCTION` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Modifier` | **必写** | 整数（百分比），旅游削减的调整值。**注意**：参数名为 `Modifier` 而非 `Amount` |

> **溯源**：**启蒙运动**（`CIVIC_THE_ENLIGHTENMENT`，市政）— 与不同宗教的文明间宗教旅游业绩削减 50%（`Modifier=50`）。

---

### EFFECT_ADJUST_RELIGION_AMENITIES_FOR_MINIMUM_FOLLOWERS

城市中达到最低信徒数量时，为该城市提供宜居度。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_CITIES_ADJUST_RELIGION_AMENITIES_FOR_MINIMUM_FOLLOWERS` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amenities` | **必写** | 整数，提供的宜居度数量 |
| `Followers` | **必写** | 整数，所需的最低信徒数阈值 |

> **溯源**：**达摩**（`TRAIT_CIVILIZATION_DHARMA`，印度文明特质）— 城市每有 1 个至少 1 名信徒的宗教，便 +1 宜居度（`Amenities=1`, `Followers=1`）。

---

### EFFECT_ADJUST_RELIGION_ANYONE_CONDEMNS_FAVOR

允许任何文明（不论宗教）对该宗教使用审判官谴责，并获取外交支持。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_RELIGION_ADJUST_ANYONE_CONDEMNS_FAVOR` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，谴责获得的外交支持数量 |

> **溯源**：**世界宗教**（`WC_RES_WORLD_RELIGION`，世界议会决议）— 任何文明都可谴责此宗教的宗教单位，每次谴责获得 25 外交支持（`Amount=25`）。此效果通过 `ResolutionEffects` 表链接到世界议会系统。

---

### EFFECT_ADJUST_RELIGION_BUILDING_DISCOUNT

该宗教的宗教建筑获得建造折扣（信仰值或生产力折扣）。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_ADJUST_RELIGION_BUILDING_DISCOUNT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Discount` | **必写** | 整数（百分比），折扣力度。`90` = 一折（仅需 10% 费用） |

> **溯源**：**正义的信仰**（`TRAIT_LEADER_RIGHTEOUSNESS_OF_FAITH`，萨拉丁特质）— 宗教建筑仅需 10% 的常规费用（`Discount=90`），即可用信仰值以极低折扣购买。

---

### EFFECT_ADJUST_RELIGION_CONDEMN_PROHIBITED

禁止该宗教被审判官谴责。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_RELIGION_ADJUST_CONDEMN_PROHIBITED` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Prohibited` | **必写** | `1` 禁止谴责。**注意**：参数名为 `Prohibited` 而非 `Enable` |

> **溯源**：DynamicModifiers 在 GS / NF / BD / WAR 中注册，但游戏中无活跃 DB 实例。此效果与 `EFFECT_ADJUST_RELIGION_ANYONE_CONDEMNS_FAVOR` 对应（一个禁止谴责，一个鼓励谴责）。使用前需充分测试。

---

### EFFECT_ADOPT_ALLY_FOUNDED_RELIGIONS

允许玩家采用盟友创立的宗教（即使自己未创立）。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_ADOPT_ALLY_FOUNDED_RELIGIONS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Adopt` | **必写** | `1` 允许采用 |

> **溯源**：**耶路撒冷**（`MINOR_CIV_JERUSALEM`，宗教城邦）— 作为其宗主国，可自动采用盟友创立的宗教（`Adopt=1`）。

---

### EFFECT_ALLIANCE_YIELD_INCOME_FROM_ALLY_RELIGION

从追随你宗教的盟友城市中获得产出。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_ALLIANCE_PLAYERS_YIELD_FROM_FOLLOWERS_OF_ALLY_RELIGIONS` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 整数，产出数量 |
| `YieldType` | **必写** | `YIELD_FAITH` 等，引用 [Yields.YieldType] |

> **溯源**：**宗教联盟 3 级效果**（联盟系统）— 从追随你宗教的盟友城市中每位信徒获得 +1 信仰值（`Amount=1`, `YieldType=YIELD_FAITH`）。

---

### EFFECT_ENABLE_RELIGION_AWARDS_ENVOY

城邦首次皈依此宗教时，玩家获得城邦使者。

| ModifierType | CollectionType |
|--------------|----------------|
| `MODIFIER_PLAYER_RELIGION_ENABLE_AWARDS_ENVOY` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Enable` | **必写** | `1` 启用使者奖励 |

> **溯源**：**宗教统一**（`BELIEF_RELIGIOUS_UNITY`，创立者信条）— 城邦首次皈依此宗教时额外获得 1 名使者（`Enable=1`）。

---

