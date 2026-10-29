# modifier-greatpeople — 伟人/巨作类 EffectType — 伟人点数

> 分册：由 [modifier-greatpeople.md](modifier-greatpeople.md) 按主题拆出；覆盖 EFFECT_ADJUST_CITY_GREAT_PERSON_POINTS_MODIFIER、EFFECT_ADJUST_DISTRICT_GREAT_PERSON_POINTS、EFFECT_ADJUST_GREAT_PEOPLE_POINTS_PER_KILL、EFFECT_ADJUST_GREAT_PEOPLE_POINTS_PER_KILL_BY_DEFEATED_STRENGTH、EFFECT_ADJUST_GREAT_PERSON_GUARANTEE、EFFECT_ADJUST_GREAT_PERSON_PATRONAGE_DISCOUNT_PERCENT、EFFECT_ADJUST_GREAT_PERSON_POINTS、EFFECT_ADJUST_GREAT_PERSON_POINTS_PERCENT、EFFECT_ADJUST_GREAT_PERSON_POINTS_REFUND_PERCENT、EFFECT_ADJUST_NO_GREAT_PERSON_POINTS、EFFECT_ADJUST_PLAYER_FREE_GREAT_PERSON_POINTS、EFFECT_GRANT_GREAT_PERSON_CLASS_IN_CITY。触发：改伟人点数、保底、赞助折扣、伟人授予时。

## 伟人点数

### EFFECT_ADJUST_CITY_GREAT_PERSON_POINTS_MODIFIER

调整城市伟人点数获取速率（百分比加成，不影响基础值）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_CITY_INCREASE_GREAT_PERSON_POINT_BONUS` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_CITIES_ADJUST_GREAT_PERSON_POINT_BONUS` | `COLLECTION_PLAYER_CITIES` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 百分比值（例：`100` = +100%，`-50` = -50%） |

> **溯源**：
> - 平伽拉总督晋升「**拨款**」——所在城市伟人点数 +100%（`Amount=100`）
> - 政策卡「**集体主义**」——所有城市伟人点数 -50%（`Amount=-50`）
> 
> 注意：`CITY_INCREASE_GREAT_PERSON_POINT_BONUS` 作用于单城，`PLAYER_CITIES_ADJUST_GREAT_PERSON_POINT_BONUS` 作用于所有城市。此 Effect 调整的是"城市伟人点数总额"的百分比加成，不区分伟人类型。

---

### EFFECT_ADJUST_DISTRICT_GREAT_PERSON_POINTS

指定区域提供每回合伟人点数（绝对值）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_ALLIANCE_DISTRICTS_ADJUST_GREAT_POINTS` | `COLLECTION_ALLIANCE_DISTRICTS` |
| `MODIFIER_PLAYER_DISTRICTS_ADJUST_GREAT_PERSON_POINTS` | `COLLECTION_PLAYER_DISTRICTS` |
| `MODIFIER_PLAYER_DISTRICT_ADJUST_GREAT_PERSON_POINTS` | `COLLECTION_OWNER` |
| `MODIFIER_SINGLE_CITY_DISTRICTS_ADJUST_GREAT_PERSON_POINTS` | `COLLECTION_CITY_DISTRICTS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 每回合伟人点数（整数，例：`1`、`2`） |
| `GreatPersonClassType` | **可选** | 伟人类型。不写则对所有伟人类型生效（[GreatPersonClassType.txt](../../SOURCES.md#类型与枚举)） |

> **溯源**：
> - 同盟效果——与盟友贸易路线相连的城市区域 +1 伟人点数（`COLLECTION_ALLIANCE_DISTRICTS`）
> - 拜占庭文明能力「**天授规矩**」——圣地 +1 大预言家点数（`GreatPersonClassType=GREAT_PERSON_CLASS_PROPHET`）
> - 万神殿信条「**神圣之光**」——对应区域 +1 对应伟人点数（如学院 +1 大科学家、剧院广场 +1 大作家）
> - 奇观「**神谕**」——该城市各区域 +2 对应伟人点数（`COLLECTION_CITY_DISTRICTS`）
> - 政策卡「**人事管理**」（Mod 自定）——各区域 +1 对应伟人点数

---

### EFFECT_ADJUST_GREAT_PEOPLE_POINTS_PER_KILL

单位击杀敌人后获得伟人点数（固定值）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_UNIT_ADJUST_GREAT_PEOPLE_POINTS_PER_KILL` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 每次击杀获得的伟人点数（整数，例：`5`、`10`） |
| `GreatPersonClassType` | **可选** | 伟人类型。不写则对所有伟人类型生效（[GreatPersonClassType.txt](../../SOURCES.md#类型与枚举)） |

> **溯源**：法国单位「**帝国卫队**」——击杀敌人 +10 陆军统帅伟人点数（`Amount=10`，`GreatPersonClassType=GREAT_PERSON_CLASS_GENERAL`）。马其顿单位「**伙友骑兵**」——击杀敌人 +5 陆军统帅伟人点数（`Amount=5`）。CollectionType 为 `COLLECTION_OWNER`（玩家），但效果实际作用于玩家的单位，通常配合 `SubjectRequirementSetId` 限定单位类型。

---

### EFFECT_ADJUST_GREAT_PEOPLE_POINTS_PER_KILL_BY_DEFEATED_STRENGTH

击杀敌人后，根据被击杀单位的战斗力按比例获得伟人点数。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_UNITS_GREAT_PEOPLE_POINTS_PER_KILL_BY_DEFEATED_STRENGTH` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **可选** | 百分比倍率（整数，例：`25` = 25%，`100` = 100%） |
| `GreatPersonClassType` | **可选** | 伟人类型。不写则对所有伟人类型生效（[GreatPersonClassType.txt](../../SOURCES.md#类型与枚举)） |

> **溯源**：
> - 维京单位「**沃林**」——击杀敌人后按战斗力 25% 获得陆军统帅/海军统帅伟人点数（`Amount=25`）
> - 单位能力「**特遣队**」——击杀敌人后按战斗力 100% 获得大科学家/陆军统帅/大工程师伟人点数（`Amount=100`）
> 
> 例：击杀战斗力 40 的敌人，`Amount=25` → 获得 40 × 0.25 = 10 伟人点数。

---

### EFFECT_ADJUST_GREAT_PERSON_GUARANTEE

保证指定时代的指定类型伟人必然出现（不受伟人点数竞争影响，直接"锁定"）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_GREAT_PERSON_GUARANTEE` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `EraType` | **可选** | 时代。`ERA_ANCIENT / CLASSICAL / MEDIEVAL / RENAISSANCE / INDUSTRIAL / MODERN / ATOMIC / INFORMATION / FUTURE`（[EraType.txt](../../SOURCES.md#类型与枚举)）。不写则仅一次性生效 |
| `GreatPersonClassType` | **必写** | 伟人类型（[GreatPersonClassType.txt](../../SOURCES.md#类型与枚举)） |

> **溯源**：
> - 阿拉伯文明能力「**最后的预言家**」——确保在最后一个大预言家被招募时必然获得一位大预言家（只传 `GreatPersonClassType=GREAT_PERSON_CLASS_PROPHET`，不传 `EraType`）
> - 大哥伦比亚领袖能力「**荣耀之战**」——古典到未来每个时代均保证出现一位总指挥（`EraType` 从 `ERA_CLASSICAL` 到 `ERA_FUTURE` 逐条配置）
> 
> 每个时代每种伟人类型只能 guarantee 一次。`EraType` 不传时效果为一次性（仅在当前可招募伟人池中锁定）。

---

### EFFECT_ADJUST_GREAT_PERSON_PATRONAGE_DISCOUNT_PERCENT

降低用信仰/金币购买伟人的赞助费用（百分比折扣）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_GREAT_PERSON_PATRONAGE_DISCOUNT_PERCENT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 折扣百分比（整数，例：`20` = 20% 折扣，`25` = 25% 折扣） |
| `YieldType` | **可选** | 限定折扣适用的货币类型。`YIELD_FAITH / YIELD_GOLD`。不写则两种货币均打折 |

> **溯源**：
> - 奇观「**神谕**」——信仰购买伟人费用 -25%（`Amount=25`，`YieldType=YIELD_FAITH`）
> - 领袖能力「**索格伦**」（松迪亚塔·凯塔）——金币购买伟人费用 -20%（`Amount=20`，`YieldType=YIELD_GOLD`）

---

### EFFECT_ADJUST_GREAT_PERSON_POINTS

每回合获得指定类型的伟人点数（绝对值）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_GREAT_PERSON_POINTS` | `COLLECTION_OWNER` |
| `MODIFIER_PLAYER_CITIES_ADJUST_GREAT_PERSON_POINT` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_PLAYER_CITIES_ADJUST_GREAT_PERSON_POINT_BASE` | `COLLECTION_PLAYER_CITIES` |
| `MODIFIER_SINGLE_CITY_ADJUST_GREAT_PERSON_POINT` | `COLLECTION_OWNER` |
| `MODIFIER_ALL_PLAYERS_ADJUST_GREAT_PERSON_POINTS` | `COLLECTION_ALL_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 每回合伟人点数（整数，例：`1`、`2`、`4`） |
| `GreatPersonClassType` | **可选** | 伟人类型。不写则对所有伟人类型生效（[GreatPersonClassType.txt](../../SOURCES.md#类型与枚举)） |

> **溯源（广泛使用）**：
> - 政策卡（玩家级 `COLLECTION_OWNER`）：「**文学传统**」→ +2 大作家点数；「**鼓舞**」→ +2 大科学家点数；「**启示**」→ +2 大预言家点数；「**将军**」→ +2 陆军统帅点数；「**航海**」→ +2 海军统帅点数；「**旅行商人**」→ +2 大商人点数；「**不干涉主义**」→ +4 大商人点数；「**军事组织**」→ +4 陆军统帅点数；「**诺贝尔奖**」→ +4 大科学家点数；「**交响曲**」→ +4 大音乐家点数；「**发明**」→ +4 大工程师点数；「**壁画**」→ +2 大艺术家点数
> - 纪念时刻：「**宗教纪念**」（黄金时代）→ +4 大预言家点数（`OwnerRequirementSetId=PLAYER_HAS_GOLDEN_AGE`）
> - 世界奇观「**张掖丹霞**」→ 所有玩家 +2 陆军统帅/大商人伟人点数（`COLLECTION_ALL_PLAYERS`，受邻近区域条件限制）
> - 城邦斯德哥尔摩/博洛尼亚——对应建筑 +1 对应伟人点数（`COLLECTION_PLAYER_CITIES`，每城生效）
> - 政策卡进阶用法（附加建筑条件）：如「**壁画**」+ 艺术博物馆 → +2 大艺术家点数；「**交响曲**」+ 广播中心 → +4 大音乐家点数；「**不干涉主义**」+ 银行 → +2 大商人点数；「**诺贝尔奖**」+ 研究实验室 → +4 大科学家点数
> - 俄罗斯文明能力「**拉夫拉修道院**」（`POINT_BASE`）——神社 +1 大作家、寺庙 +1 大艺术家、三级宗教建筑 +1 大音乐家（基础值加成，`SubjectRequirementSetId` 限定建筑）
> - 万神殿信条「**神圣之光**」——对应建筑 +1 大科学家/大作家点数（`COLLECTION_OWNER`，`SINGLE_CITY` 作用域）
>
> **四者区别**：
> - `COLLECTION_OWNER`（玩家级）：全局加，总额外点数
> - `COLLECTION_PLAYER_CITIES`（每城）：每座城市都加
> - `POINT_BASE`：加的是城市基础伟人点数（受百分比加成影响）
> - `POINT`：直接叠加，不受百分比加成影响

---

### EFFECT_ADJUST_GREAT_PERSON_POINTS_PERCENT

调整伟人点数获取速率（百分比，玩家级）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_GREAT_PERSON_POINTS_PERCENT` | `COLLECTION_OWNER` |
| `MODIFIER_MAJOR_PLAYERS_ADJUST_GREAT_PERSON_POINTS_PERCENT` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 百分比值（整数，例：`50` = +50%，`100` = +100%） |
| `GreatPersonClassType` | **可选** | 伟人类型。不写则对所有类型生效（[GreatPersonClassType.txt](../../SOURCES.md#类型与枚举)） |

> **溯源**：
> - 世界议会决议「**赞助**」——所有主要文明伟人点数 +100%/+50%/-50%（`COLLECTION_MAJOR_PLAYERS`）
> - 刚果文明能力「**精神实体**」——大艺术家/大音乐家/大商人点数 +50%（`GreatPersonClassType` 分别指定）
>
> 与 `EFFECT_ADJUST_GREAT_PERSON_POINTS` 的区别：前者是绝对值（+N 点/回合），这个是百分比（+N% 速率）。

---

### EFFECT_ADJUST_GREAT_PERSON_POINTS_REFUND_PERCENT

招募伟人后返还部分伟人点数（百分比）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_GREAT_PERSON_POINTS_REFUND_PERCENT` | `COLLECTION_OWNER` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 返还百分比（整数，例：`20` = 返还 20% 已消耗伟人点数） |

> **溯源**：巴西领袖能力「**宽宏大量**」（佩德罗二世）——招募伟人后返还 20% 伟人点数（`Amount=20`）。

---

### EFFECT_ADJUST_NO_GREAT_PERSON_POINTS

禁止获得伟人点数（开关型效果）。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_MAJOR_PLAYERS_ADJUST_NO_GREAT_PERSON_POINTS` | `COLLECTION_MAJOR_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| — | 无参数 | 效果为开关：有该 Modifier 则伟人点数产出归零 |

> **溯源**：世界议会决议「**赞助**」——表决结果可使所有主要文明伟人点数清零（无参数，纯开关逻辑）。与同一决议的 `EFFECT_ADJUST_GREAT_PERSON_POINTS_PERCENT` 为三种表决结果中的一种。

---

### EFFECT_ADJUST_PLAYER_FREE_GREAT_PERSON_POINTS

每回合获得免费伟人点数（绝对值），可自由分配到任意伟人类型。不受城市建筑产出的伟人点数加成影响。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_PLAYER_ADJUST_FREE_GREAT_PERSON_POINTS` | `COLLECTION_OWNER` |
| `MODIFIER_EMERGENCY_PLAYERS_ADJUST_GREAT_PERSON_POINTS` | `COLLECTION_EMERGENCY_PLAYERS` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 每回合伟人点数（整数，例：`100`） |

> **溯源**：
> - 大科学家「**阿尔弗雷德·诺贝尔**」激活效果——每回合 +100 伟人点数，可自由分配到任意伟人类型（`Amount=100`）
> - 紧急事件「**世界博览会**」——第一名获得每回合 +100 伟人点数（`COLLECTION_EMERGENCY_PLAYERS`，`SubjectRequirementSetId` 限定第一名玩家）

---

### EFFECT_GRANT_GREAT_PERSON_CLASS_IN_CITY

在城市中生成一个指定类型的伟人。

| ModifierType | CollectionType |
|-------------|----------------|
| `MODIFIER_SINGLE_CITY_GRANT_GREAT_PERSON_CLASS_IN_CITY` | `COLLECTION_OWNER` |
| `MODIFIER_EMERGENCY_CAPITAL_CITIES_GRANT_GREAT_PERSON_CLASS_IN_CITY` | `COLLECTION_EMERGENCY_CAPITAL_CITIES` |

| 参数 | 写不写 | 值/引用 |
|------|--------|---------|
| `Amount` | **必写** | 生成伟人数量（整数，例：`1`） |
| `GreatPersonClassType` | **必写** | 伟人类型（[GreatPersonClassType.txt](../../SOURCES.md#类型与枚举)） |

> **溯源**：
> - 奇观「**巨石阵**」——免费获得一位大预言家（`Amount=1`，`GreatPersonClassType=GREAT_PERSON_CLASS_PROPHET`，受 `STONEHENGE_PROPHET_REQUIREMENTS` 限制：仅当玩家可招募大预言家时生效）
> - 紧急事件「**诺贝尔和平奖**」——前三名分别在首都获得大音乐家/大科学家/大工程师/大艺术家（`COLLECTION_EMERGENCY_CAPITAL_CITIES`，搭配名次条件）
> 
> 生成的伟人从当前可用的伟人池中随机抽取。若该类型无可招募的伟人，则生成失败。

---

