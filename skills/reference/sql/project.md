# Project — 项目定义

## 涉及文件

| 文件 | 内容 |
|------|------|
| `Data/<ModName>_Projects.sql` | 项目主表 + 子表 |
| `Data/<ModName>_Modifiers.sql` | UnlocksFromEffect 项目的自定义 ModifierType（一次定义，多次复用） |
| `Icons/<ModName>_Icons.xml` | `icons.md` — 项目图标（尺寸 30/32/38/50/70/80/256） |

## 涉及的表（按 INSERT 顺序）

```
Types → Projects → [Projects_XP2] → [Projects_XP1]
→ ProjectPrereqs → Project_ResourceCosts → Project_BuildingCosts
→ Project_YieldConversions → Project_GreatPersonPoints → ProjectCompletionModifiers
→ [Projects_MODE]
```

---

## 一、Types

```sql
INSERT INTO Types (Type, Kind) VALUES
('PROJECT_SIQI_{SHORT}', 'KIND_PROJECT');
```

---

## 二、Projects（主表，21 列）

### 完整 INSERT 模板

```sql
INSERT INTO Projects (
    ProjectType,
    Name,
    ShortName,
    Description,
    PopupText,
    Cost,
    CostProgressionModel,
    CostProgressionParam1,
    PrereqTech,
    PrereqCivic,
    PrereqDistrict,
    AdvisorType,
    MaxPlayerInstances,
    AmenitiesWhileActive,
    PrereqResource,
    SpaceRace,
    OuterDefenseRepair,
    WMD,
    UnlocksFromEffect
) VALUES
(
    'PROJECT_SIQI_{SHORT}',
    'LOC_PROJECT_SIQI_{SHORT}_NAME',
    'LOC_PROJECT_SIQI_{SHORT}_SHORT_NAME',
    'LOC_PROJECT_SIQI_{SHORT}_DESCRIPTION',
    NULL,
    100,
    'NO_PROGRESSION_MODEL',
    0,
    'TECH_xxx',
    NULL,
    'DISTRICT_CAMPUS',
    'ADVISOR_GENERIC',
    NULL,
    NULL,
    NULL,
    0,
    0,
    0,
    0
);
```

> `RequiredBuilding` 写在 `Projects_XP2`（主表该列无效）。
> `VisualBuildingType` 仅航天项目用（火箭模型），省略。

### 逐列参考

**身份 + 文本：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 1 | ProjectType | `PROJECT_SIQI_{SHORT}` | **必写** |
| 2 | Name | `LOC_PROJECT_SIQI_{SHORT}_NAME` | **必写** |
| 3 | ShortName | `LOC_PROJECT_SIQI_{SHORT}_SHORT_NAME` | **必写** |
| 4 | Description | `LOC_PROJECT_SIQI_{SHORT}_DESCRIPTION` | 按需 |
| 5 | PopupText | 完成弹窗文本 LOC（通常 NULL） | 按需 |

**花费：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 6 | Cost | 基础花费 | **必写** |
| 7 | CostProgressionModel | 见下表 | 按需 |
| 8 | CostProgressionParam1 | 见下表 | 按需 |

> **CostProgressionModel 参考：**
> | 模型 | 说明 | Param1 参考 |
> |------|------|------------|
> | `NO_PROGRESSION_MODEL` | 默认，不增长 | — |
> | `COST_PROGRESSION_GAME_PROGRESS` | 随游戏进程增长 | 1500（嘉年华/区域增强）、800（ANOTHER HER） |
> | `NO_COST_PROGRESSION` | 不增长（极少用） | — |

**前置条件：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 9 | PrereqTech | `TECH_xxx` | 可选 |
| 10 | PrereqCivic | `CIVIC_xxx` | 可选 |
| 11 | PrereqDistrict | `DISTRICT_xxx` | 按需 |
| 12 | AdvisorType | `ADVISOR_GENERIC` | 按需 |
| 18 | PrereqResource | 战略资源，如 `RESOURCE_URANIUM` | 按需 |

**数量：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 16 | MaxPlayerInstances | 1=每玩家一次（航天项目），NULL=不限 | 按需 |
| 17 | AmenitiesWhileActive | 项目进行中提供宜居度（整体很少用） | 按需 |

**特殊标志：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 14 | SpaceRace | 1=航天竞赛项目 | 按需 |
| 15 | OuterDefenseRepair | 1=修复外层防御 | 按需 |
| 20 | WMD | 1=核武器项目 | 按需 |
| 21 | UnlocksFromEffect | 1=通过 Modifier 解锁（需配合 UnlocksFromEffect 技巧） | 按需 |

---

## 三、Projects_XP2（扩展属性）

```sql
INSERT INTO Projects_XP2 (
    ProjectType,
    RequiredPowerWhileActive,
    ReligiousPressureModifier,
    UnlocksFromEffect,
    RequiredBuilding,
    CreateBuilding,
    FullyPoweredWhileActive,
    MaxSimultaneousInstances
) VALUES
(
    'PROJECT_SIQI_{SHORT}',
    0, 0, 0,
    'BUILDING_SIQI_{SHORT}',
    NULL, NULL, NULL
);
```

| 列 | 说明 | 参考用例 |
|---|------|---------|
| `RequiredPowerWhileActive` | 项目运行需要电力（实际极少用） | 全为 0 |
| `ReligiousPressureModifier` | 项目运行时宗教压力 | 圣地增强=100 |
| `UnlocksFromEffect` | 1=通过 Modifier 解锁 | 援助/运动员/退役发电站 |
| `RequiredBuilding` | 有特定建筑才可启动（主表同名列无效，写这里） | 重启反应堆需核电站 |
| `CreateBuilding` | 完成时生成新建筑（升级/转换用） | 发电站转换；SIQI L1↔L3 |
| `FullyPoweredWhileActive` | 运行时完全通电 | 工业区增强=1 |
| `MaxSimultaneousInstances` | 每城最大同时实例 | 首都迁移=1 |

> **外键占位禁令**：`RequiredBuilding`/`CreateBuilding` 无需求时填 `NULL`，**禁止写 `'0'`**（外键引用 Buildings，`'0'` 不存在 → 加载报错，0014 实测）。`Projects_MODE` 无资源/改良前置时**整段不写**（官方项目 0 行）。

---

## 四、Projects_XP1

```sql
INSERT INTO Projects_XP1 (ProjectType, IdentityPerCitizenChange, UnlocksFromEffect) VALUES
('PROJECT_SIQI_{SHORT}', NULL, 0);
```

| 列 | 说明 |
|---|------|
| `IdentityPerCitizenChange` | 每公民忠诚度变化（Bread & Circuses=1.0） |
| `UnlocksFromEffect` | 同 XP2 |

---

## 五、ProjectPrereqs

```sql
INSERT INTO ProjectPrereqs (ProjectType, PrereqProjectType, MinimumPlayerInstances) VALUES
('PROJECT_LAUNCH_MOON_LANDING', 'PROJECT_LAUNCH_EARTH_SATELLITE', 1);
```

> 先完成前置项目 N 次后，才能启动本项。

---

## 六、Project_ResourceCosts

```sql
INSERT INTO Project_ResourceCosts (ProjectType, ResourceType, StartProductionCost) VALUES
('PROJECT_BUILD_NUCLEAR_DEVICE', 'RESOURCE_URANIUM', 10);
```

> 启动项目时消耗的战略资源量。

---

## 七、Project_BuildingCosts

```sql
INSERT INTO Project_BuildingCosts (ProjectType, ConsumedBuildingType) VALUES
-- 切换发电站：转换到燃煤 → 消耗旧发电站
('PROJECT_CONVERT_REACTOR_TO_COAL', 'BUILDING_FOSSIL_FUEL_POWER_PLANT'),
('PROJECT_CONVERT_REACTOR_TO_COAL', 'BUILDING_POWER_PLANT');
```

> 启动项目时消耗的建筑。官方例子：发电站类型转换（消耗旧类型 → `CreateBuilding` 生成新类型）。

---

## 八、Project_YieldConversions

```sql
INSERT INTO Project_YieldConversions (ProjectType, YieldType, PercentOfProductionRate) VALUES
('PROJECT_ENHANCE_DISTRICT_CAMPUS', 'YIELD_SCIENCE', 15);
```

| `PercentOfProductionRate` | 说明 | 参考 |
|---|---|---|
| 15% | 标准区域项目 | 大部分增强项目 |
| 30% | 商业中心 | 商业中心增强 |
| 50%-200% | 自定义 | LIJIA / SIQI 项目 |

---

## 九、Project_GreatPersonPoints

```sql
INSERT INTO Project_GreatPersonPoints (ProjectType, GreatPersonClassType, Points, PointProgressionModel, PointProgressionParam1) VALUES
('PROJECT_ENHANCE_DISTRICT_CAMPUS', 'GREAT_PERSON_CLASS_SCIENTIST', 10, 'COST_PROGRESSION_GAME_PROGRESS', 800);
```

| `Points` | 说明 | 参考 |
|---|------|------|
| 5 | 嘉年华（多类伟人） | 娱乐中心 |
| 10 | 标准区域增强 | 学院/圣地/军营等 |
| 15-30 | 自定义 | SIQI TECNO=30 |

---

## 十、ProjectCompletionModifiers

```sql
INSERT INTO ProjectCompletionModifiers (ProjectType, ModifierId) VALUES
('PROJECT_LAUNCH_EARTH_SATELLITE', 'PROJECT_COMPLETION_EXPLORE_ENTIRE_MAP');
```

> 项目完成时触发的 Modifier。

---

## 十一、Projects_MODE

```sql
INSERT INTO Projects_MODE (ProjectType, ResourceType) VALUES
('PROJECT_SIQI_{SHORT}', 'RESOURCE_xxx');
```

> `PrereqImprovement` 无效，不写。

---

## 十二、UnlocksFromEffect 技巧

项目设 `UnlocksFromEffect=1`，通过自定义 ModifierType 解锁。

### 步骤 1：定义 ModifierType（整个 Mod 一次）

```sql
INSERT INTO Types (Type, Kind) VALUES
('MODIFIER_SIQI_UNLOCK_PROJECT', 'KIND_MODIFIER');

INSERT INTO DynamicModifiers (ModifierType, EffectType, CollectionType) VALUES
('MODIFIER_SIQI_UNLOCK_PROJECT', 'EFFECT_ADD_PLAYER_PROJECT_AVAILABILITY', 'COLLECTION_OWNER');
```

### 步骤 2：每个项目创建 Modifier

```sql
INSERT INTO Modifiers (ModifierId, ModifierType) VALUES
('MODIFIER_SIQI_GRANT_PROJECT_{SHORT}', 'MODIFIER_SIQI_UNLOCK_PROJECT');

INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
('MODIFIER_SIQI_GRANT_PROJECT_{SHORT}', 'ProjectType', 'PROJECT_SIQI_{SHORT}');

INSERT INTO TraitModifiers (TraitType, ModifierId) VALUES
('TRAIT_CIVILIZATION_SIQI_{SHORT}', 'MODIFIER_SIQI_GRANT_PROJECT_{SHORT}');
```

> ModifierType 整个 Mod 定义一次，多个项目复用。

---

## 十三、Text — 本地化文本

```sql
INSERT INTO LocalizedText (Language, Tag, Text) VALUES
('zh_Hans_CN', 'LOC_PROJECT_SIQI_{SHORT}_NAME',        '{中文名}'),
('zh_Hans_CN', 'LOC_PROJECT_SIQI_{SHORT}_SHORT_NAME',  '{短名}'),
('zh_Hans_CN', 'LOC_PROJECT_SIQI_{SHORT}_DESCRIPTION', '{中文描述}');
```
