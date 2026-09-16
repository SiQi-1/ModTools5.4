# Unit — 单位定义（三部分）

## 涉及文件

| 文件 | 内容 |
|------|------|
| `Data/<ModName>_Units.sql` | 单位主表 + 子表（取代/升级/XP2/AI/捕获等） |
| `Data/<ModName>_UnitAbilities.sql` | Tags + TypeTags + UnitAbilities + UnitAbilityModifiers |
| `Data/<ModName>_UnitPromotions.sql` | UnitPromotionClasses + UnitPromotions + Prereqs + Modifiers |
| `Text/<ModName>_Text_CN.sql` | 单位名、描述、能力名/描述、晋升名/描述 |

---

# 第一部分：单位本体 → `Data/<ModName>_Units.sql`

## 一.1、涉及的表（按 INSERT 顺序）

```
Types → Units → [Units_XP2]
→ UnitReplaces → UnitUpgrades
→ [UnitAiInfos] → [UnitCaptures] → [Units_MODE]
→ [Units_Presentation] → [UnitNames] → [Unit_RockbandResults_XP2] → [Unit_RebellionTags]
```

不归 unit.md 的表：
- **UnitModifiers** → `07-techniques/modifiers.md`（Modifier 统一管理）
- **UnitCommands / UnitOperations** → 硬编码，不动

---

## 一.2、Types

```sql
INSERT INTO Types (Type, Kind) VALUES
('UNIT_SIQI_{SHORT}', 'KIND_UNIT'),
('TRAIT_UNIT_SIQI_{SHORT}', 'KIND_TRAIT');
```

---

## 一.3、Units（主表，67 列）

### 完整 INSERT 模板（常用列）

```sql
INSERT INTO Units (
    UnitType,
    Name,
    Description,
    Domain,
    FormationClass,
    Cost,
    PopulationCost,
    BaseSightRange,
    BaseMoves,
    Combat,
    RangedCombat,
    Bombard,
    Range,
    AntiAirCombat,
    PrereqTech,
    PrereqCivic,
    PrereqDistrict,
    PrereqPopulation,
    StrategicResource,
    PurchaseYield,
    MustPurchase,
    Maintenance,
    CanTrain,
    TraitType,
    PromotionClass,
    InitialLevel,
    NumRandomChoices,
    CanEarnExperience,
    FoundCity,
    FoundReligion,
    EvangelizeBelief,
    LaunchInquisition,
    RequiresInquisition,
    BuildCharges,
    ReligiousStrength,
    ReligionEvictPercent,
    SpreadCharges,
    ReligiousHealCharges,
    ExtractsArtifacts,
    CanCapture,
    CanRetreatWhenCaptured,
    Stackable,
    ZoneOfControl,
    Spy,
    WMDCapable,
    IgnoreMoves,
    TeamVisibility,
    AirSlots,
    CanTargetAir,
    PseudoYieldType,
    ParkCharges,
    DisasterCharges,
    UseMaxMeleeTrainedStrength,
    ImmediatelyName,
    AllowBarbarians,
    CostProgressionModel,
    CostProgressionParam1,
    ObsoleteTech,
    ObsoleteCivic,
    MandatoryObsoleteTech,
    MandatoryObsoleteCivic,
    AdvisorType,
    EnabledByReligion,
    TrackReligion,
    Flavor,
    Quote
) VALUES
(
    'UNIT_SIQI_{SHORT}',
    'LOC_UNIT_SIQI_{SHORT}_NAME',
    'LOC_UNIT_SIQI_{SHORT}_DESCRIPTION',
    'DOMAIN_LAND',
    'FORMATION_CLASS_LAND_COMBAT',
    100,
    NULL,
    2,
    2,
    20,
    0,
    0,
    0,
    0,
    'TECH_MINING',
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    0,
    0,
    1,
    'TRAIT_CIVILIZATION_SIQI_C{SHORT}',
    'PROMOTION_CLASS_MELEE',
    1,
    0,
    1,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    0,
    0,
    1,
    0,
    0,
    0,
    0,
    NULL,
    NULL,
    0,
    0,
    NULL,
    0,
    0,
    0,
    0,
    0,
    'NO_COST_PROGRESSION',
    0,
    NULL,
    NULL,
    NULL,
    NULL,
    NULL,
    0,
    0,
    NULL,
    NULL
);
```

### 逐列参考

**身份 + 文本：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 0 | UnitType | `UNIT_SIQI_{SHORT}` | **必写** |
| 1 | Name | `LOC_UNIT_SIQI_{SHORT}_NAME` | **必写** |
| 24 | Description | `LOC_UNIT_SIQI_{SHORT}_DESCRIPTION` | **必写** |
| 25 | Flavor | 全区 NULL，语义不明，默认不写 | 不写 |

**战斗属性：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 2 | BaseSightRange | 步兵=2，侦察兵=3-5，船=2-3 | **必写** |
| 3 | BaseMoves | 步兵=2，骑兵=4，船=3-4 | **必写** |
| 4 | Combat | 近战/陆军战力，平民=0 | **必写** |
| 5 | RangedCombat | 远程攻击力，非远程=0。Bombard 二选一 | **必写** |
| 6 | Range | 攻击范围，远程=1-3，攻城=2-3 | **必写** |
| 7 | Bombard | 轰炸战斗力，非轰炸=0。RangedCombat 二选一 | **必写** |
| 50 | AntiAirCombat | 防空战力，非防空=0 | **必写** |
| 64 | UseMaxMeleeTrainedStrength | 1=战斗力等同于已训练单位的最大近战战力。配合 CanTrain=1 + MustPurchase=1 + 不写PurchaseYield + Cost=9999。Combat 填远古无近战时的保底值。文本标志："基础战斗力等同于训练过的最强近战战斗力" | 按需 |

**域 + 编队：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 8 | Domain | `DOMAIN_LAND` / `DOMAIN_SEA` / `DOMAIN_AIR` | **必写** |
| 9 | FormationClass | `FORMATION_CLASS_LAND_COMBAT` / `FORMATION_CLASS_NAVAL` / `FORMATION_CLASS_AIR` / `FORMATION_CLASS_CIVILIAN` / `FORMATION_CLASS_SUPPORT` | **必写** |

**成本：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 10 | Cost | 取代单位→复制被取代单位；无取代且用户未指定→反问 | **必写** |
| 11 | PopulationCost | 消耗人口，一般是开拓者用 | 按需 |

**平民能力：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 12 | FoundCity | 1=建城（开拓者） | 按需 |
| 13 | FoundReligion | 1=创建宗教（大先知） | 按需 |
| 14 | MakeTradeRoute | 有 bug，一般不写 | 不写 |
| 15 | EvangelizeBelief | 1=传播宗教（传教士） | 按需 |
| 16 | LaunchInquisition | 1=开启审判（使徒） | 按需 |
| 17 | RequiresInquisition | 1=需要审判庭已启动 | 按需 |
| 18 | BuildCharges | 建造次数（建造者/军事工程师） | 按需 |
| 19 | ReligiousStrength | 宗教传播力。参考：传教士=100，使徒=110，审判官=75，上师=90 | 按需 |
| 20 | ReligionEvictPercent | 移除非本教压力%。参考：传教士=10，使徒=25，审判官=75，上师=0 | 按需 |
| 21 | SpreadCharges | 传教次数。参考：传教士/使徒/审判官=3 | 按需 |
| 22 | ReligiousHealCharges | 治疗次数。参考：上师=3 | 按需 |
| 23 | ExtractsArtifacts | 1=提取文物（考古学家） | 按需 |

**战斗行为：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 26 | CanCapture | 1=可俘虏平民单位。军事单位默认 1，平民/宗教单位=0 | 按需 |
| 27 | CanRetreatWhenCaptured | 1=被俘后可撤退 | 按需 |
| 45 | Stackable | 1=可堆叠（平民/宗教单位=1） | 按需 |
| 49 | ZoneOfControl | 1=有控制区 | 按需 |
| 51 | Spy | 1=间谍 | 按需 |
| 52 | WMDCapable | 1=可发射核弹。参考：轰炸机/核潜艇/喷气式轰炸机=1 | 按需 |
| 54 | IgnoreMoves | 1=无法移动（实际含义）。示例：商人、间谍、空军 | 按需 |
| 55 | TeamVisibility | 1=全队共享视野。示例：间谍=1 | 按需 |

**特质 + 蛮族：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 28 | TraitType | `TRAIT_CIVILIZATION_SIQI_C{SHORT}`（特色单位用文明特质） | 按需 |
| 29 | AllowBarbarians | 1=蛮族可刷新 | 按需 |

**费用递进：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 30 | CostProgressionModel | 默认 `NO_COST_PROGRESSION`（军事单位）。`COST_PROGRESSION_PREVIOUS_COPIES`（平民/宗教单位），`COST_PROGRESSION_GAME_PROGRESS`（商人） | 按需 |
| 31 | CostProgressionParam1 | 参考：建造者=4，传教士=6，上师=12，使徒=15，开拓者=30，自然学家=50，间谍=75，商人=400 | 按需 |

**晋升相关：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 32 | PromotionClass | 晋升树类型，见 [reference/enums/UnitPromotionClassType.txt](../../reference/enums/UnitPromotionClassType.txt)（待建） | **必写**（战斗单位） |
| 33 | InitialLevel | 初始等级，默认 1 | 按需 |
| 34 | NumRandomChoices | 随机晋升选项数，默认 0 | 按需 |
| 66 | CanEarnExperience | 可获取经验，默认 1 | 按需 |

**前置条件：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 35 | PrereqTech | `TECH_xxx` | 可选 |
| 36 | PrereqCivic | `CIVIC_xxx` | 可选 |
| 37 | PrereqDistrict | `DISTRICT_xxx` | 按需 |
| 38 | PrereqPopulation | 需要城市人口数，配合 PopulationCost | 按需 |
| 39 | LeaderType | 限定领袖 | 按需 |

**训练/购买：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 40 | CanTrain | 1=可锤子生产，默认 1 | 按需 |
| 41 | StrategicResource | 战略资源 Type，见 [reference/enums/ResourceType.txt](../../reference/enums/ResourceType.txt) 战略类 | 按需 |
| 42 | PurchaseYield | `YIELD_GOLD` / `YIELD_FAITH` | 按需 |
| 43 | MustPurchase | 1=只能买不能锤。不填 PurchaseYield=虚拟单位（不可产不可买） | 按需 |
| 44 | Maintenance | 维护费，一般 1 或 0 | 按需 |

**空军相关：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 46 | AirSlots | 搭载飞机数（机场/航母用） | 按需 |
| 47 | CanTargetAir | 1=可攻击空中单位 | 按需 |

**杂项：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 48 | PseudoYieldType | AI 行为引导。见 [reference/enums/PseudoYieldType.txt](../../reference/enums/PseudoYieldType.txt)（待建） | 按需 |
| 53 | ParkCharges | 国家公园次数。参考：自然学家=1，加拿大骑警=2 | 按需 |
| 63 | DisasterCharges | 发起灾难次数（天启模式预言者） | 按需 |
| 65 | ImmediatelyName | 1=立即命名 | 按需 |

**过期：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 56 | ObsoleteTech | 过期科技，通常不写 | 不写 |
| 57 | ObsoleteCivic | 过期市政，通常不写 | 不写 |
| 58 | MandatoryObsoleteTech | 强制过期科技，通常不写 | 不写 |
| 59 | MandatoryObsoleteCivic | 强制过期市政，通常不写 | 不写 |

**最后三列：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 60 | AdvisorType | 见 [reference/enums/AdvisorType.txt](../../reference/enums/AdvisorType.txt) | 可选 |
| 61 | EnabledByReligion | 1=需要创立宗教才能购买/训练 | 按需 |
| 62 | TrackReligion | 1=所属宗教单位。参考：传教士/使徒/审判官/上师/武僧 | 按需 |

---

## 一.3.1、特殊设计模式（非 Lua）

以下是纯 SQL 列组合即可实现的常见设计模式。当文本描述匹配到关键词时，**优先查此表**，避免误判为"需要 Lua"。

### 战斗力继承单位
**文本关键词**："基础战斗力等同于训练过的最强近战战斗力"、"战斗力等同于"、"战斗力跟随时代"
**列组合**：
- `UseMaxMeleeTrainedStrength=1` — 核心，动态取已训练最强近战战力
- `CanTrain=1` — 必须为 1，否则 Modifier 也无法赠送此单位
- `MustPurchase=1` — 禁止锤子生产
- `PurchaseYield` 不写 — 禁止购买（无购买货币类型）
- `Cost=9999` — 天价兜底
- `Combat=20` — 填远古无近战单位时的保底值
**说明**：Combat 值在游戏运行时会被覆盖，SQL 中填的值仅在没有已训练近战单位时生效。`CanTrain=1` ≠ 可训练，因为 `MustPurchase=1` 会阻止锤子生产；`CanTrain=1` 的真正作用是允许 Modifier（如 GRANT_FREE_UNIT）赠送此单位。无需 Lua。

### 免费赠送单位（建城送）
**文本关键词**："建造城市后获得一个"、"新建城市赠送"
**列组合**：
- `MODIFIER_PLAYER_BUILT_CITIES_GRANT_FREE_UNIT` Modifier
- 参数：`UnitType` + `Amount=1` + `AllowUniqueOverride=1`
**说明**：纯 Modifier 实现，无需 Lua。挂在 TRAIT 或 ABILITY 上均可。

### 不可生产/购买的虚拟单位
**文本关键词**："无法训练，无法购买"、"不可生产"
**列组合**：
- `CanTrain=1` — 必须为 1，否则 Modifier 也无法赠送
- `MustPurchase=1` — 禁止锤子生产
- `PurchaseYield` 不写 — 禁止购买
- `Cost=9999` — 天价兜底
**说明**：这种单位只能通过 Modifier（如 GRANT_FREE_UNIT）或 Lua 获得。如果设为 `CanTrain=0`，则连 Modifier 都无法赠送，只能靠 Lua `UnitManager.CreateUnit()`。

---

## 一.4、UnitReplaces

```sql
INSERT INTO UnitReplaces (CivUniqueUnitType, ReplacesUnitType) VALUES
('UNIT_SIQI_{SHORT}', 'UNIT_WARRIOR');
```

ReplacesUnitType 枚举值后续建立 UnitType.txt。

---

## 一.5、UnitUpgrades

```sql
INSERT INTO UnitUpgrades (Unit, UpgradeUnit) VALUES
('UNIT_SIQI_{SHORT}', 'UNIT_SWORDSMAN');
```

UpgradeUnit 可复制被取代单位的升级目标。若用户未指定且无参考，反问。

---

## 一.6、Units_XP2

| 列名 | 值参考 | 写不写 |
|------|--------|--------|
| UnitType | `UNIT_SIQI_{SHORT}` | **必写** |
| ResourceMaintenanceAmount | 每回合资源消耗量。参考：末日机甲=3，晚期单位=1 | 按需 |
| ResourceCost | 训练时资源消耗量。参考：标准单位=20，特色单位=5-10，晚期=1 | 按需 |
| ResourceMaintenanceType | 消耗资源类型（战略资源），同 StrategicResource | 按需 |
| TourismBomb | 旅游爆发值。实际值在 Unit_RockbandResults_XP2 | 按需 |
| TourismBombPossible | 1=可触发旅游爆发。仅摇滚乐队=1 | 按需 |
| CanFormMilitaryFormation | 1=可组成军团/军队，默认 1 | 按需 |
| MajorCivOnly | 1=仅主要文明可用 | 按需 |
| CanCauseDisasters | 1=可引发灾害（天启模式） | 按需 |
| CanSacrificeUnits | 1=可献祭单位 | 按需 |

CanEarnExperience 与主表 #66 重复，不写。

不需要的列不写，不需要整张表就不写。

---

## 一.7、UnitAiInfos

```sql
INSERT INTO UnitAiInfos (UnitType, AiType) VALUES
('UNIT_SIQI_{SHORT}', 'UNITTYPE_MELEE'),
('UNIT_SIQI_{SHORT}', 'UNITAI_COMBAT');
```

一个单位可写多行，同时有多个 AiType。AiType 枚举见 [reference/enums/UnitAiType.txt](../../reference/enums/UnitAiType.txt)（22 条）。

> **引用校验（0054 实测）**：`AiType` 必须存在于 `UnitAiTypes` 表，否则游戏加载直接报
> `[Gameplay] ERROR: Invalid Reference on UnitAiInfos.AiType`。常见坑：**`UNITTYPE_RECON` 不存在**。
> 替换侦察兵的特色单位镜像 `UNIT_SCOUT` 同款两行即可：`UNITAI_EXPLORE` + `UNITTYPE_LAND_COMBAT`（战斗单位另加 `UNITAI_COMBAT`/`UNITTYPE_MELEE` 等合法值）。

---

## 一.8、UnitCaptures

```sql
INSERT INTO UnitCaptures (CapturedUnitType, BecomesUnitType) VALUES
('UNIT_SIQI_{SHORT}', 'UNIT_SETTLER');
```

被俘后变为什么单位。官方数据：开拓者→开拓者，建造者→建造者。俘虏后类型不变也写此表。

---

## 一.9、Units_MODE

```sql
INSERT INTO Units_MODE (UnitType, ActionCharges) VALUES
('UNIT_SIQI_{SHORT}', 1);
```

特殊行动次数，配合 Lua 使用（Lua 可直接改变此值，而 BuildCharges 不能）。一般用不到。

---

## 一.10、Units_Presentation

```sql
INSERT INTO Units_Presentation (UnitType, UIFlagOffset) VALUES
('UNIT_SIQI_{SHORT}', 0);
```

纯 UI 旗帜偏移调整。一般用不到。

---

## 一.11、UnitNames

```sql
INSERT INTO UnitNames (ID, NameType, TextKey) VALUES
(1, 'SUFFIX_ALL', 'LOC_UNIT_SIQI_{SHORT}_NAME_SUFFIXES');
```

为军事单位提供随机名称池。NameType 可选值：`PREFIX_ALL` / `SUFFIX_ALL` / `SUFFIX_RECON` / `SUFFIX_RANGED` / `SUFFIX_CAVALRY` / `SUFFIX_NAVAL` / `SUFFIX_AIR` 等。一般用不到。

---

## 一.12、Unit_RockbandResults_XP2

摇滚乐队表演结果表，格式固定。需要时参考官方数据填入。

---

## 一.13、Unit_RebellionTags

控制叛乱时生成什么类型的单位。一般用不到。

---

## 一.14、文本（Units 部分）

```sql
INSERT INTO LocalizedText (Language, Tag, Text) VALUES
('zh_Hans_CN', 'LOC_UNIT_SIQI_{SHORT}_NAME',        '{单位名称}'),
('zh_Hans_CN', 'LOC_UNIT_SIQI_{SHORT}_DESCRIPTION', '{单位描述}');
```

---

# 第二部分：单位能力 → `Data/<ModName>_UnitAbilities.sql`

## 二.1、涉及的表（按 INSERT 顺序）

```
Tags → TypeTags → UnitAbilities → UnitAbilityModifiers
```

> **[首要原则] 涉及单位效果，一律通过 Ability 实现**。给单位批量加效果时，使用 `EFFECT_GRANT_ABILITY` → `UnitAbility` → `UnitAbilityModifiers` 路径，**不要**直接 `EFFECT_ATTACH_MODIFIER` 把效果挂到单位上。理由：① 官方 155 个实例均采用此模式（`MODIFIER_PLAYER_UNITS_GRANT_ABILITY`）；② Ability 能显示在单位面板 UI 上，玩家可感知；③ Tag 过滤比 RequirementSet 更简洁可靠；④ Ability 生命周期由引擎管理，存档/升级/死亡更安全。

**核心机制**：单位通过 TypeTags 绑定 CLASS_xxx 标签，能力也绑定同标签。**Tag 是能力的匹配过滤器**——不论 Inactive=0 还是 Inactive=1，能力只对绑定了相同 Tag 的单位生效。

- `Inactive=0`：同 Tag 单位**自动获得**能力（无需任何 Modifier）
- `Inactive=1`：需 `EFFECT_GRANT_ABILITY` Modifier 手动授予，但**仍然受 Tag 过滤**——只有同 Tag 的单位才能被授予此能力

> **关键推论**：当用 `EFFECT_GRANT_ABILITY` 给特定兵种（如所有远程/攻城单位）授予能力时，**不需要写 SubjectRequirementSet 按 PROMOTION_CLASS 筛选**。只需给 Ability 绑定对应 CLASS Tag（如 `CLASS_RANGED`、`CLASS_SIEGE`），Tag 本身就会过滤掉不匹配的单位。这比 RequirementSet 更简洁可靠。

**泛标签**（`CLASS_ALL_UNITS` / `CLASS_ALL_COMBAT_UNITS` / `CLASS_ALL_ERAS` / `CLASS_RELIGIOUS_ALL`）：不绑单位，仅能力用。Req 中无法匹配泛标签。

## 二.2、Tags

```sql
INSERT INTO Tags (Tag, Vocabulary) VALUES
('CLASS_SIQI_{SHORT}', 'ABILITY_CLASS');
```

Vocabulary 固定为 `ABILITY_CLASS`。

---

## 二.3、TypeTags

```sql
-- 给单位打标签
INSERT INTO TypeTags (Type, Tag) VALUES
('UNIT_SIQI_{SHORT}', 'CLASS_MELEE'),
('UNIT_SIQI_{SHORT}', 'CLASS_SIQI_{SHORT}');

-- 给能力打标签
INSERT INTO TypeTags (Type, Tag) VALUES
('ABILITY_SIQI_{SHORT}', 'CLASS_MELEE'),
('ABILITY_SIQI_{SHORT}', 'CLASS_SIQI_{SHORT}');
```

- 单位一般绑定现成通用 CLASS 标签（如 `CLASS_MELEE`）。通用 CLASS 见 [reference/enums/AbilityClassTag.txt](../../reference/enums/AbilityClassTag.txt)
- 自定义能力可以新建 CLASS 标签，单位和能力同时绑定
- Type 可以是 `UNIT_xxx` / `ABILITY_xxx` / `TRAIT_xxx` / `CIVILIZATION_xxx` 等

---

## 二.4、UnitAbilities

```sql
INSERT INTO UnitAbilities (UnitAbilityType, Name, Description, Inactive, ShowFloatTextWhenEarned, Permanent) VALUES
('ABILITY_SIQI_{SHORT}',
 NULL,
 'LOC_ABILITY_SIQI_{SHORT}_DESCRIPTION',
 0,
 0,
 1);
```

| 列名 | 值参考 | 写不写 |
|------|--------|--------|
| UnitAbilityType | `ABILITY_SIQI_{SHORT}` | **必写** |
| Name | ShowFloatTextWhenEarned=1 时的浮动文本 LOC_ 键。一般只写 Description 不写 Name | 按需 |
| Description | 单位面板上显示的能力描述 LOC_ 键 | **必写** |
| Inactive | 0=同 TAG 自动获得；1=需 GRANT_ABILITY Modifier 手动赋予 | 按需 |
| ShowFloatTextWhenEarned | 1=获得时弹浮动文本 | 按需 |
| Permanent | 1=永久能力；0=非永久——**GRANT 的 SubjectReq 不再满足时能力自动摘除**（动态生效） | 按需 |

> Inactive=1 时，GRANT_ABILITY Modifier 通常不用写条件，因为能力本身绑定的 CLASS 已筛选了可获得的单位。

### Permanent=0 动态摘除（关键）

当能力需要"**条件满足时才生效**"（离开条件区域立即失效）时：

- GRANT_ABILITY 带 SubjectReq 判条件 + 能力 **Permanent=0** → 条件不再满足时引擎**自动摘除**能力（无需 Lua）
- 若 Permanent=1 → 条件不满足能力仍保留（效果常驻，只有 GRANT modifier 整体移除才消失）

| 场景 | 写法 |
|------|------|
| 单位进入雨林解除禁疗（非雨林才禁疗） | GRANT(SubjectReq=非雨林) + Ability Permanent=0 |
| 孤狼状态离开即失效（相邻敌1友0才+15力） | GRANT(SubjectReq=孤狼条件) + Ability Permanent=0 |
| 时代切换移除伟人能力（原版 AOE 先例） | GRANT(SubjectReq=时代条件) + Ability Permanent=0 |

> 原版先例：`ABILITY_GREAT_ADMIRAL_STRENGTH` 等 AOE 时代能力（Permanent=0 + 时代条件 GRANT，时代过自动摘除）。

---

## 二.5、UnitAbilityModifiers

```sql
INSERT INTO UnitAbilityModifiers (UnitAbilityType, ModifierId) VALUES
('ABILITY_SIQI_{SHORT}', 'MODIFIER_SIQI_{SHORT}_COMBAT_BONUS');
```

桥接表。一个能力可绑多个 Modifier。

---

## 二.6、文本（能力部分）

```sql
INSERT INTO LocalizedText (Language, Tag, Text) VALUES
('zh_Hans_CN', 'LOC_ABILITY_SIQI_{SHORT}_DESCRIPTION', '{能力描述}');
```


# 第三部分：单位晋升 → `Data/<ModName>_UnitPromotions.sql`

## 三.1、涉及的表（按 INSERT 顺序）

```
UnitPromotionClasses → UnitPromotions → UnitPromotionPrereqs → UnitPromotionModifiers
```

> 晋升通常用现成的，只有做新晋升树才需要写这些表。

## 三.2、UnitPromotionClasses

```sql
INSERT INTO UnitPromotionClasses (PromotionClassType, Name) VALUES
('PROMOTION_CLASS_SIQI_{SHORT}', 'LOC_PROMOTION_CLASS_SIQI_{SHORT}_NAME');
```

官方 PromotionClass 值（20 个）：
```
PROMOTION_CLASS_RECON / MELEE / RANGED / SIEGE / ANTI_CAVALRY
/ LIGHT_CAVALRY / HEAVY_CAVALRY / AIR_FIGHTER / AIR_BOMBER
/ NAVAL_MELEE / NAVAL_RANGED / NAVAL_CARRIER / NAVAL_RAIDER
/ APOSTLE / INQUISITOR / SUPPORT / SPY / MONK / ROCK_BAND / GIANT_DEATH_ROBOT
```

---

## 三.3、UnitPromotions

```sql
INSERT INTO UnitPromotions (UnitPromotionType, Name, Description, Level, Specialization, PromotionClass, Column) VALUES
('PROMOTION_SIQI_{SHORT}_L1',
 'LOC_PROMOTION_SIQI_{SHORT}_L1_NAME',
 'LOC_PROMOTION_SIQI_{SHORT}_L1_DESCRIPTION',
 1,
 NULL,
 'PROMOTION_CLASS_MELEE',
 0);
```

| 列名 | 值参考 | 写不写 |
|------|--------|--------|
| UnitPromotionType | `PROMOTION_SIQI_{SHORT}_L{N}` | **必写** |
| Name | LOC_ 键 | **必写** |
| Description | LOC_ 键 | **必写** |
| Level | 1-4，等级（行），越高所需经验越多 | **必写** |
| Specialization | 全区 NULL，不写 | 不写 |
| PromotionClass | 所属晋升树 | **必写** |
| Column | 列位置。1=L, 2=M, 3=R | **必写** |

### 晋升树位置（Level + Column）

典型 4 级 7 晋升树布局：

```
Level 4:           [M4]
Level 3:       L3        R3
Level 2:     L2    M2    R2
Level 1:   L1    M1    R1
```

每级常规 2-2-2-1 分布（L 和 R 各有 2 个，M 每个 Level 最多 1 个）。命名惯例：
- Level=1, Column=1 → `_L1`
- Level=1, Column=2 → `_M1`
- Level=1, Column=3 → `_R1`

---

## 三.4、UnitPromotionPrereqs

```sql
INSERT INTO UnitPromotionPrereqs (UnitPromotion, PrereqUnitPromotion) VALUES
('PROMOTION_SIQI_{SHORT}_L2', 'PROMOTION_SIQI_{SHORT}_L1'),
('PROMOTION_SIQI_{SHORT}_L2', 'PROMOTION_SIQI_{SHORT}_R1');
```

一个晋升可写多个前置（多路径到达）。

---

## 三.5、UnitPromotionModifiers

```sql
INSERT INTO UnitPromotionModifiers (UnitPromotionType, ModifierId) VALUES
('PROMOTION_SIQI_{SHORT}_L1', 'MODIFIER_SIQI_{SHORT}_PROMOTION_L1');
```

桥接表，和 UnitAbilityModifiers 相同模式。

---

## 三.6、文本（晋升部分）

```sql
INSERT INTO LocalizedText (Language, Tag, Text) VALUES
-- 晋升树名
('zh_Hans_CN', 'LOC_PROMOTION_CLASS_SIQI_{SHORT}_NAME', '{晋升树名称}'),
-- 晋升
('zh_Hans_CN', 'LOC_PROMOTION_SIQI_{SHORT}_L1_NAME',        '{L1 晋升名}'),
('zh_Hans_CN', 'LOC_PROMOTION_SIQI_{SHORT}_L1_DESCRIPTION', '{L1 晋升描述}');
```

---

# 四、关联文件

| 文件 | 技能 | 说明 |
|------|------|------|
| `Data/<ModName>_Civilizations.sql` | `civilization.md` | CivilizationTraits 绑单位特质 |
| `Data/<ModName>_Configs.sql` | `configs.md` | PlayerItems 注册特色单位展示 |
| `Icons/<ModName>_Icons.xml` | `icons.md` | 单位图标 |
| `<ModName>.civ6proj` | `civ6proj.md` | 注册 UpdateDatabase |
| `Data/<ModName>_Modifiers.sql` | `modifiers.md` | UnitModifiers 绑定 |
