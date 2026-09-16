# Government — 政体定义

## 涉及文件

| 文件 | 内容 |
|------|------|
| `Data/<ModName>_Governments.sql` | 政体主表 + 子表 |
| `Text/<ModName>_Text_CN.sql` | 政体名、加成描述 |

## 涉及的表（按 INSERT 顺序）

```
Types → Governments → Government_SlotCounts → GovernmentModifiers
→ [Governments_XP2] → [StartingGovernments]
```

不归 government.md 的表：
- **Policy_GovernmentExclusives_XP2** → `policy.md`（已在政策卡技能覆盖）

---

## 一、Types

```sql
INSERT INTO Types (Type, Kind) VALUES
('GOVERNMENT_SIQI_{SHORT}', 'KIND_GOVERNMENT');
```

---

## 二、Governments（主表，13 列）

### 完整 INSERT 模板（必写列）

```sql
INSERT INTO Governments (
    GovernmentType,
    Name,
    PrereqCivic,
    InherentBonusDesc,
    AccumulatedBonusShortDesc,
    AccumulatedBonusDesc,
    OtherGovernmentIntolerance,
    InfluencePointsPerTurn,
    InfluencePointsThreshold,
    InfluenceTokensPerThreshold,
    BonusType,
    PolicyToUnlock,
    Tier
) VALUES
(
    'GOVERNMENT_SIQI_{SHORT}',
    'LOC_GOVERNMENT_SIQI_{SHORT}_NAME',
    'CIVIC_POLITICAL_PHILOSOPHY',
    'LOC_GOVERNMENT_SIQI_{SHORT}_INHERENT_BONUS',
    'LOC_GOVERNMENT_SIQI_{SHORT}_ACCUMULATED_BONUS_SHORT',
    'LOC_GOVERNMENT_SIQI_{SHORT}_ACCUMULATED_BONUS',
    0,
    5,
    1,
    2,
    'GOVERNMENTBONUS_OVERALL_PRODUCTION',
    NULL,
    'Tier2'
);
```

### 逐列参考

**身份 + 显示：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 0 | GovernmentType | `GOVERNMENT_SIQI_{SHORT}` | **必写** |
| 1 | Name | `LOC_GOVERNMENT_SIQI_{SHORT}_NAME` | **必写** |

**解锁条件：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 2 | PrereqCivic | `CIVIC_POLITICAL_PHILOSOPHY` 等 | **必写**（仅酋邦可为 NULL） |

> 酋邦（CHIEFDOM）的 PrereqCivic 为 NULL，它是开局默认政体。自定义政体若希望开局可用，设 NULL 并配合 `StartingGovernments` 表注册。

**加成描述（纯文本，不驱动效果）：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 3 | InherentBonusDesc | `LOC_GOVERNMENT_SIQI_{SHORT}_INHERENT_BONUS` | **必写** |
| 4 | AccumulatedBonusShortDesc | `LOC_GOVERNMENT_SIQI_{SHORT}_ACCUMULATED_BONUS_SHORT` | **必写** |
| 5 | AccumulatedBonusDesc | `LOC_GOVERNMENT_SIQI_{SHORT}_ACCUMULATED_BONUS` | **必写** |

> 这两列只是**显示文本**，实际效果通过 `GovernmentModifiers` 挂载 Modifier 实现。
>
> 原版政体有两套加成实现方式，对应不同的文本写法：
>
> **1. FLAT_BONUS（固定加成，GS 原版默认）**
>
> 使用 `MODIFIER_PLAYER_GOVERNMENT_FLAT_BONUS`，只有两个参数：
>
> | 参数名 | 说明 |
> |--------|------|
> | `BonusType` | GovernmentBonusNames 枚举，推荐与 Governments.BonusType 一致 |
> | `Amount` | 加成百分比（固定值，不随时间增长） |
>
> 用这套的政体，AccumulatedBonusDesc 写固定效果。GS 原版示例：
>
> | 政体 | BonusType | Amount | AccumulatedBonusDesc |
> |---|---|---|---|
> | 独裁 | WONDER_CONSTRUCTION | 10 | `建造奇观时+10%生产力。` |
> | 寡头 | COMBAT_EXPERIENCE | 20 | `+20%单位经验值。` |
> | 古典共和 | GREAT_PEOPLE | 15 | `+15%伟人点数。` |
> | 君主制 | ENVOYS | 50 | `+50%影响力点数。` |
> | 神权 | FAITH_PURCHASES | 15 | `使用信仰值购买时享受15%折扣。` |
> | 商人共和 | DISTRICT_PRODUCTION | 15 | `建造区域时+15%生产力。` |
> | 法西斯 | UNIT_PRODUCTION | 50 | `训练单位时+50%生产力。` |
> | 民主 | GOLD_PURCHASES | 15 | `使用金币购买时享受-25%折扣。` |
>
> T4 政体（企业自由主义/数字民主/合成专家统治）和共产主义不用 FLAT_BONUS，各自用普通 Modifier 实现，文本直接写效果。
>
> **2. ACCUMULATING_BONUS（随时间增长，GS 原版不用但系统仍可用）**
>
> 使用 `MODIFIER_PLAYER_GOVERNMENT_ACCUMULATING_BONUS`，三个参数：
>
> | 参数名 | 说明 |
> |--------|------|
> | `BonusType` | 同上 |
> | `Increment` | 每次增长加多少百分点 |
> | `Interval` | 多少回合增长一次（`ScaleByGameSpeed` 缩放） |
>
> 用这套时，AccumulatedBonusDesc 用括号格式：`{效果描述}（{基础%}，在标准速度下每{Interval}回合加{Increment}%）。`
>
> > GS 原版政体统一用 FLAT_BONUS（固定值），不随时间增长。AccumulatedBonusDesc 的文本来自政体面板的积累加成描述（非 FLAT_BONUS 加成），不要混淆。

**外交不容忍：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 6 | OtherGovernmentIntolerance | 整数，默认 `0` | 按需 |

> 控制对不同政体文明的外交惩罚。原版：酋邦/T1/T2=0（中立），T3/T4=-20（更不容忍，产生外交减益）。负值越大越不容忍。

**使者/影响力：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 7 | InfluencePointsPerTurn | 整数 | **必写** |
| 8 | InfluencePointsThreshold | 整数 | **必写** |
| 9 | InfluenceTokensPerThreshold | 整数 | **必写** |

> 三列共同控制城邦使者获取速率。Threshold 是攒满一个使者的所需点数，层级越高门槛越高。原版参考：

| 层级 | PointsPerTurn | Threshold | TokensPerThreshold |
|------|:---:|:---:|:---:|
| 酋邦 | 1 | 100 | 1 |
| Tier1 | 3 | 100 | 1 |
| Tier2 | 5 | 150 | 2 |
| Tier3 | 7 | 200 | 3 |
| Tier4 | 9 | 250 | 4 |

**加成类型：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 10 | BonusType | `GovernmentBonusNames` 枚举值 | **必写**（占位可用 `GOVERNMENTBONUS_OVERALL_PRODUCTION` 或 `NO_GOVERNMENTBONUS`，实际选匹配效果的。酋邦用 `NO_GOVERNMENTBONUS`） |

> 模板中 `GOVERNMENTBONUS_OVERALL_PRODUCTION` 和 `NO_GOVERNMENTBONUS` 都是占位符。如果政体有 `MODIFIER_PLAYER_GOVERNMENT_FLAT_BONUS`，BonusType 建议与 Modifier 的 `BonusType` 参数一致；如果没有 FLAT_BONUS，`NO_GOVERNMENTBONUS` 更直白。
>
> **可选值（DB 中 11 种）：**

| 值 | 说明 |
|----|------|
| `NO_GOVERNMENTBONUS` | 无加成类型 |
| `GOVERNMENTBONUS_WONDER_CONSTRUCTION` | 奇观生产力 |
| `GOVERNMENTBONUS_COMBAT_EXPERIENCE` | 战斗经验 |
| `GOVERNMENTBONUS_GREAT_PEOPLE` | 伟人点数 |
| `GOVERNMENTBONUS_ENVOYS` | 使者点数 |
| `GOVERNMENTBONUS_FAITH_PURCHASES` | 信仰购买折扣 |
| `GOVERNMENTBONUS_GOLD_PURCHASES` | 金币购买折扣 |
| `GOVERNMENTBONUS_DISTRICT_PRODUCTION` | 区域生产力 |
| `GOVERNMENTBONUS_UNIT_PRODUCTION` | 单位生产力 |
| `GOVERNMENTBONUS_OVERALL_PRODUCTION` | 全局生产力 |
| `GOVERNMENTBONUS_DISTRICT_PROJECTS` | 区域项目生产力 |

> `BonusType` 是标签，不自动产生效果。习惯上通过 `MODIFIER_PLAYER_GOVERNMENT_FLAT_BONUS` 类型 Modifier 激活（参数 BonusType + Amount），但不是强制。不同政体即使 BonusType 相同也可设不同加成数值。

**专属政策卡：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 11 | PolicyToUnlock | `POLICY_GOV_xxx` | 按需 |

> 选择此政体后自动解锁的专属政策卡。该政策卡需在 `Policies` 表独立定义，设为 `ExplicitUnlock=1`。酋邦及部分政体为 NULL。

**层级：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 12 | Tier | `Tier1` / `Tier2` / `Tier3` / `Tier4` | **必写**（酋邦为 NULL） |

> `GovernmentTiers` 表可扩展。新 Tier 只需 `INSERT INTO GovernmentTiers`，即可在政体中引用。

| Tier | Sorting | 对应时代 | 原版政体 |
|------|:---:|---------|----------|
| `Tier1` | 1 | 古典（政治哲学） | 独裁、寡头、古典共和 |
| `Tier2` | 2 | 中世纪-文艺复兴 | 君主制、神权政体、商人共和 |
| `Tier3` | 3 | 现代-原子能 | 法西斯、共产主义、民主 |
| `Tier4` | 4 | 信息时代 | 数字民主、合成专家统治、企业自由主义 |

> **UI 陷阱**：官方 `GovernmentScreen.lua` 的 `RealizeGovernmentsPage()` **不读 `GovernmentTiers` 表**，而是按**总政策槽数**分组同列。槽数相同的政体会被 UI 归入同一列显示。扩 Tier 时需确保同 Tier 政体的槽总数一致，且不与相邻 Tier 相同，否则出现跨级混排。

---

## 三、Government_SlotCounts（政策槽位数量）

```sql
INSERT INTO Government_SlotCounts (GovernmentType, GovernmentSlotType, NumSlots) VALUES
('GOVERNMENT_SIQI_{SHORT}', 'SLOT_MILITARY',   1),
('GOVERNMENT_SIQI_{SHORT}', 'SLOT_ECONOMIC',   2),
('GOVERNMENT_SIQI_{SHORT}', 'SLOT_DIPLOMATIC', 1),
('GOVERNMENT_SIQI_{SHORT}', 'SLOT_WILDCARD',   1);
```

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 0 | GovernmentType | 政体 Type | **必写** |
| 1 | GovernmentSlotType | 见下表 5 种 | **必写** |
| 2 | NumSlots | 该类型槽位数 | **必写** |

> 每种槽位每政体只写一行，不需要的槽位类型不写。槽位类型（GovernmentSlots 表）：

| GovernmentSlotType | 中文 | 说明 |
|---|---|---|
| `SLOT_MILITARY` | 军事槽 | 只能放军事政策卡 |
| `SLOT_ECONOMIC` | 经济槽 | 只能放经济政策卡 |
| `SLOT_DIPLOMATIC` | 外交槽 | 只能放外交政策卡 |
| `SLOT_GREAT_PERSON` | 伟人槽 | 只能放伟人政策卡 |
| `SLOT_WILDCARD` | 万能槽 | 可放任何政策卡 |

各层级总槽数参考（不含伟人槽）：

| 层级 | 总槽数 |
|------|:---:|
| 酋邦 | 2 |
| Tier1 | 4 |
| Tier2 | 6 |
| Tier3 | 8 |
| Tier4 | 10 |

---

## 四、GovernmentModifiers（政体 Modifier 挂载）

```sql
INSERT INTO GovernmentModifiers (GovernmentType, ModifierId) VALUES
('GOVERNMENT_SIQI_{SHORT}', 'MODIFIER_SIQI_{SHORT}_xxx');
```

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 0 | GovernmentType | 政体 Type | **必写** |
| 1 | ModifierId | Modifier ID，定义在 `Modifiers` 表 | **必写** |

> 纯关联表。Modifier 的 ModifierType 和 SubjectRequirementSet 由需求决定，无固定模式。
>
> 原版参考——独裁政体挂了五种 Modifier：
>
> | ModifierId | ModifierType | SubjectRequirementSet |
> |---|---|---|
> | `AUTOCRACY_CAPITAL` | `MODIFIER_PLAYER_CITIES_ADJUST_CITY_ALL_YIELDS_CHANGE` | `BUILDING_IS_PALACE`（仅首都） |
> | `AUTOCRACY_TIER1` | 同上 | `BUILDING_IS_TIER1`（政府区T1建筑） |
> | `AUTOCRACY_TIER2` | 同上 | `BUILDING_IS_TIER2`（政府区T2建筑） |
> | `AUTOCRACY_TIER3` | 同上 | `BUILDING_IS_TIER3`（政府区T3建筑） |
> | `AUTOCRACY_WONDERS` | `MODIFIER_PLAYER_GOVERNMENT_FLAT_BONUS` | 无 |
>
> 而寡头政体只挂两个：`MODIFIER_PLAYER_UNITS_GRANT_ABILITY`（近战+4力）+ `MODIFIER_PLAYER_GOVERNMENT_FLAT_BONUS`（经验加成率）。没有 Tier 系列。
>
> `MODIFIER_PLAYER_GOVERNMENT_FLAT_BONUS` 是原版政体普遍使用的类型，参数：

| 参数名 | 类型 | 说明 |
|--------|------|------|
| `BonusType` | String | 推荐与 Governments.BonusType 一致（非强制） |
| `Amount` | Integer | 加成百分比数值 |

---

## 五、Governments_XP2（风云变幻扩展）

```sql
INSERT INTO Governments_XP2 (GovernmentType, Favor) VALUES
('GOVERNMENT_SIQI_{SHORT}', 2);
```

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 0 | GovernmentType | 政体 Type | **必写** |
| 1 | Favor | 整数 | **必写** |

> 仅 GS 需要。原版参考：酋邦=0, Tier1=1, Tier2=2, Tier3=3, Tier4=4。

---

## 六、StartingGovernments（开局自动解锁）

```sql
INSERT INTO StartingGovernments (Government, Era, Change) VALUES
('GOVERNMENT_CHIEFDOM', 'ERA_ANCIENT', 0);
```

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 0 | Government | 政体 Type | **必写** |
| 1 | Era | `ERA_ANCIENT` 等 | **必写** |
| 2 | Change | 0=不可切换, 1=此后可切换政体 | **必写** |

> 自定义政体通常不需动此表，除非替换酋邦作为开局默认政体。原版在 `ERA_MEDIEVAL` 起设置 Change=1，解锁政体切换机制。

---

## 七、Text — 本地化文本

```sql
INSERT INTO LocalizedText (Language, Tag, Text) VALUES
('zh_Hans_CN', 'LOC_GOVERNMENT_SIQI_{SHORT}_NAME',                     '{中文政体名}'),
('zh_Hans_CN', 'LOC_GOVERNMENT_SIQI_{SHORT}_INHERENT_BONUS',           '{固有加成描述}'),
('zh_Hans_CN', 'LOC_GOVERNMENT_SIQI_{SHORT}_ACCUMULATED_BONUS_SHORT',  '{积累加成短描述}'),
('zh_Hans_CN', 'LOC_GOVERNMENT_SIQI_{SHORT}_ACCUMULATED_BONUS',        '{积累加成完整描述}');
```

| Tag 后缀 | 显示位置 | 写不写 |
|-----------|---------|--------|
| `_NAME` | 政体面板标题、文明百科 | **必写** |
| `_INHERENT_BONUS` | 政体面板固有加成区域 | **必写** |
| `_ACCUMULATED_BONUS_SHORT` | 政体面板积累加成预览 | **必写** |
| `_ACCUMULATED_BONUS` | 文明百科积累加成展开 | **必写** |

---

## 八、Enum 文件

| 文件 | 内容 |
|------|------|
| `reference/enums/GovernmentSlotType.txt` | 5 种政策槽位 |
| `reference/enums/GovernmentBonusType.txt` | 9 种积累加成类型（DB 有 11 种，缺 `NO_GOVERNMENTBONUS` 和 `GOVERNMENTBONUS_DISTRICT_PRODUCTION`） |

---

## 九、关联文件

| 文件 | 技能 | 说明 |
|------|------|------|
| `Data/<ModName>_Modifiers.sql` | `modifiers.md` | Modifiers 表定义三类加成 Modifier |
| `Data/<ModName>_Policies.sql` | `policy.md` | 专属政策卡定义 + Policy_GovernmentExclusives_XP2 |
| `Data/<ModName>_Configs.sql` | `configs.md` | 无需额外注册（政体不进入 PlayerItems） |
| `Text/<ModName>_Text_CN.sql` | `text.md` | 名称/描述本地化 |
