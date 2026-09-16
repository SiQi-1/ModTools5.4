# Improvement — 改良设施定义

## 涉及文件

| 文件 | 内容 |
|------|------|
| `Data/<ModName>_Improvements.sql` | 改良主表 + 子表（产出/放置条件/旅游） |
| `Icons/<ModName>_Icons.xml` | `icons.md` — 改良图标（尺寸 38/50/80/256） |
| `Text/<ModName>_Text_CN.sql` | 改良名、描述、特质名/描述 |

## 涉及的表（按 INSERT 顺序）

```
Types → Improvements → [Improvements_XP2]
→ Improvement_YieldChanges → Improvement_BonusYieldChanges → Improvement_YieldsOutsideTerritories
→ Improvement_Adjacencies
→ Improvement_ValidTerrains → Improvement_ValidFeatures → Improvement_ValidResources
→ Improvement_ValidAdjacentTerrains → Improvement_ValidAdjacentResources
→ Improvement_InvalidAdjacentFeatures
→ Improvement_ValidBuildUnits → Improvement_Tourism
```

不归 improvement.md 的表：
- **ImprovementModifiers** → `07-techniques/modifiers.md`（Modifier 统一管理）
- **Improvements_MODE** — 无用，不写

---

## 一、Types

```sql
INSERT INTO Types (Type, Kind) VALUES
('IMPROVEMENT_SIQI_{SHORT}', 'KIND_IMPROVEMENT'),
('TRAIT_IMPROVEMENT_SIQI_{SHORT}', 'KIND_TRAIT');
```

> 改良使用独立特质前缀 `TRAIT_IMPROVEMENT_`（不是 `TRAIT_CIVILIZATION_`），通过 CivilizationTraits 绑到文明上。

---

## 二、Improvements（主表，48 列）

### 完整 INSERT 模板（必写列）

```sql
INSERT INTO Improvements (
    ImprovementType,
    Name,
    Description,
    Icon,
    TraitType,
    PrereqTech,
    PrereqCivic,
    Buildable,
    Domain,
    TilesRequired,
    SameAdjacentValid,
    RequiresRiver,
    EnforceTerrain,
    BuildInLine,
    CanBuildOutsideTerritory,
    BuildOnFrontier,
    Coast,
    AdjacentSeaResource,
    RequiresAdjacentBonusOrLuxury,
    RequiresAdjacentLuxury,
    AdjacentToLand,
    ValidAdjacentTerrainAmount,
    RemoveOnEntry,
    PlunderType,
    PlunderAmount,
    ImprovementOnRemove,
    Removable,
    Capturable,
    BarbarianCamp,
    DispersalGold,
    Goody,
    TilesPerGoody,
    GoodyRange,
    GoodyNotify,
    AirSlots,
    DefenseModifier,
    GrantFortification,
    WeaponSlots,
    Housing,
    MinimumAppeal,
    YieldFromAppeal,
    YieldFromAppealPercent,
    Appeal,
    OnePerCity,
    MovementChange,
    Workable,
    NoAdjacentSpecialtyDistrict,
    OnlyOpenBorders,
    ReligiousUnitHealRate
) VALUES
(
    'IMPROVEMENT_SIQI_{SHORT}',
    'LOC_IMPROVEMENT_SIQI_{SHORT}_NAME',
    'LOC_IMPROVEMENT_SIQI_{SHORT}_DESCRIPTION',
    'ICON_IMPROVEMENT_SIQI_{SHORT}',
    'TRAIT_IMPROVEMENT_SIQI_{SHORT}',
    'TECH_IRRIGATION',
    NULL,
    1,
    'DOMAIN_LAND',
    1,
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
    0,
    'PLUNDER_GOLD',
    0,
    NULL,
    1,
    1,
    0,
    0,
    0,
    NULL,
    NULL,
    1,
    0,
    0,
    0,
    0,
    0,
    NULL,
    NULL,
    100,
    0,
    0,
    0,
    1,
    0,
    0,
    0
);
```

### 逐列参考

**身份 + 文本：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 1 | ImprovementType | `IMPROVEMENT_SIQI_{SHORT}` | **必写** |
| 2 | Name | `LOC_IMPROVEMENT_SIQI_{SHORT}_NAME` | **必写** |
| 7 | Description | `LOC_IMPROVEMENT_SIQI_{SHORT}_DESCRIPTION` | **必写** |
| 14 | Icon | `ICON_IMPROVEMENT_SIQI_{SHORT}` | **必写** |
| 15 | TraitType | `TRAIT_IMPROVEMENT_SIQI_{SHORT}` | 按需 |

**前置条件：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 3 | PrereqTech | `TECH_xxx`，查 enum | 可选（二选一或全空） |
| 4 | PrereqCivic | `CIVIC_xxx`，查 enum | 可选 |
| 5 | Buildable | 1=可被建造者建造，0=不可建造 | **必写**（通常=1） |
| 36 | Domain | `DOMAIN_LAND` / `DOMAIN_SEA` | **必写** |

**建造位置限制：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 17 | TilesRequired | 一般=1，国家公园=4（但硬编码） | 默认=1 |
| 18 | SameAdjacentValid | 1=可相邻同类改良，0=不可相邻 | 默认=1 |
| 19 | RequiresRiver | 0/1/2（需临河，2=需河流边） | 按需 |
| 20 | EnforceTerrain | 1=不可在非ValidTerrains地块上替换其他改良 | 按需 |
| 21 | BuildInLine | 1=排成线（120°角，如长城） | 按需 |
| 22 | CanBuildOutsideTerritory | 1=可境外建造 | 按需 |
| 23 | BuildOnFrontier | 1=边境建造（罗马堡垒） | 按需 |
| 28 | Coast | 1=必须沿海 | 按需 |
| 36 | AdjacentSeaResource | 1=需相邻海洋资源 | 按需 |
| 37 | RequiresAdjacentBonusOrLuxury | 1=需相邻加成资源或奢侈资源 | 按需 |
| 44 | RequiresAdjacentLuxury | 1=需相邻奢侈资源 | 按需 |
| 45 | AdjacentToLand | 1=需相邻陆地 | 按需 |
| 35 | ValidAdjacentTerrainAmount | N=至少N个有效地形相邻 | 按需 |
| 43 | NoAdjacentSpecialtyDistrict | 1=不可相邻专业化区域 | 按需 |

**掠夺 / 移除：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 8 | RemoveOnEntry | 1=单位进入时移除（部落村庄） | 按需 |
| 9 | PlunderType | `PLUNDER_xxx`，查 `PlunderType.txt` 枚举 | 按需 |
| 10 | PlunderAmount | 掠夺数量 | 默认=0 |
| 41 | ImprovementOnRemove | 另一个 `IMPROVEMENT_xxx`，移除后生成 | 按需 |
| 46 | Removable | 1=可手动移除，0=不可 | 默认=1 |
| 48 | Capturable | 领土易手时保留（1=保留，0=摧毁），官方全=1 | 默认不写 |

**蛮族 / 部落村庄：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 2 | BarbarianCamp | 1=蛮族营地 | 按需 |
| 8 | DispersalGold | 摧毁时金币 | 默认=0 |
| 11 | Goody | 1=部落村庄 | 按需 |
| 12 | TilesPerGoody | 每N格生成一个部落村庄 | 按需 |
| 13 | GoodyRange | 生成范围 | 按需 |
| 42 | GoodyNotify | 1=发现时通知 | 默认=1 |

**军事 / 防御：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 24 | AirSlots | 飞机停放数 | 按需 |
| 25 | DefenseModifier | 防御修正绝对值，参考：堡垒=4 | 默认=0 |
| 26 | GrantFortification | 授予驻防回合数，2=标准（堡垒） | 默认=0 |
| 30 | WeaponSlots | 武器槽位 | 按需 |

**产出 / 魅力 / 住房：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 16 | Housing | 提供住房。农场=0.5 | 默认=0 |
| 27 | MinimumAppeal | 最低魅力要求，如 `BEACH_RESORT`=4 | 按需 |
| 29 | YieldFromAppeal | 魅力→产出类型（如 `YIELD_CULTURE`/`YIELD_GOLD`） | 按需 |
| 34 | YieldFromAppealPercent | 魅力转换百分比，默认=100 | 按需 |
| 32 | Appeal | 给相邻地块的魅力加成 | 默认=0 |
| 40 | Workable | 1=可被市民工作 | 默认=1 |

**其他：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 31 | ReligiousUnitHealRate | 宗教单位驻守治疗速率 | 按需 |
| 33 | OnePerCity | 每城限一个 | 按需 |
| 39 | MovementChange | 地块移动力修正，圩田=2（阻挡移动） | 默认=0 |
| 47 | OnlyOpenBorders | 1=仅开放边界文明可建造 | 按需 |

> 关于产量相邻加成：必须先在 `Improvement_YieldChanges` 注册对应产出（哪怕设 `YieldChange=0`），相邻加成才能生效。见下文。

---

## 三、子表

### A. Improvement_YieldChanges — 基础产出

```sql
INSERT INTO Improvement_YieldChanges (ImprovementType, YieldType, YieldChange) VALUES
('IMPROVEMENT_SIQI_{SHORT}', 'YIELD_SCIENCE', 2),
('IMPROVEMENT_SIQI_{SHORT}', 'YIELD_GOLD',    0);  -- 必须注册，相邻加成才能用
```

> **重要**：如果改良需要相邻加成产某产出，哪怕基础产出为0也必须在此表写一行。

### B. Improvement_BonusYieldChanges — 解锁后追加产出

```sql
INSERT INTO Improvement_BonusYieldChanges (Id, ImprovementType, YieldType, BonusYieldChange, PrereqTech, PrereqCivic) VALUES
(1, 'IMPROVEMENT_SIQI_{SHORT}', 'YIELD_SCIENCE', 2, 'TECH_EDUCATION', NULL);
```

> Id 自增，不冲突即可。PrereqTech / PrereqCivic 填写解锁的条件。

### C. Improvement_YieldsOutsideTerritories — 境外产出不减

```sql
INSERT INTO Improvement_YieldsOutsideTerritories (ImprovementType) VALUES
('IMPROVEMENT_SIQI_{SHORT}');
```

> 极少使用，当前数据库为空。效果：境外改良产出不衰减。

### D. Improvement_Adjacencies — 相邻加成

```sql
INSERT INTO Improvement_Adjacencies (ImprovementType, YieldChangeId) VALUES
('IMPROVEMENT_SIQI_{SHORT}', 'Siqi_Adjacency_Science');
```

> 与区域共用 `Adjacent_YieldChanges` 表，详见 [district-adjacency.md](../district-adjacency.md)。

### E. Improvement_ValidTerrains — 可建造地形

```sql
INSERT INTO Improvement_ValidTerrains (ImprovementType, TerrainType, PrereqTech, PrereqCivic) VALUES
('IMPROVEMENT_SIQI_{SHORT}', 'TERRAIN_GRASS', NULL, NULL),
('IMPROVEMENT_SIQI_{SHORT}', 'TERRAIN_PLAINS', NULL, NULL);
```

> 可选 PrereqTech / PrereqCivic 解锁新地形。

### F. Improvement_ValidFeatures — 可建造地貌

```sql
INSERT INTO Improvement_ValidFeatures (ImprovementType, FeatureType, PrereqTech, PrereqCivic) VALUES
('IMPROVEMENT_SIQI_{SHORT}', 'FEATURE_FOREST', NULL, NULL);
```

> 可选 PrereqTech / PrereqCivic 解锁新地貌。

### G. Improvement_ValidResources — 可建在资源上

```sql
INSERT INTO Improvement_ValidResources (ImprovementType, ResourceType, MustRemoveFeature) VALUES
('IMPROVEMENT_SIQI_{SHORT}', 'RESOURCE_IRON', 1);
```

> 通常是战略/奢侈资源。MustRemoveFeature=1=须先移除地貌。

### H. Improvement_ValidAdjacentTerrains — 需要相邻地形

```sql
INSERT INTO Improvement_ValidAdjacentTerrains (ImprovementType, TerrainType) VALUES
('IMPROVEMENT_SIQI_{SHORT}', 'TERRAIN_DESERT');
```

### I. Improvement_ValidAdjacentResources — 需要相邻资源

```sql
INSERT INTO Improvement_ValidAdjacentResources (ImprovementType, ResourceType) VALUES
('IMPROVEMENT_SIQI_{SHORT}', 'RESOURCE_FISH');
```

### J. Improvement_InvalidAdjacentFeatures — 不可相邻地貌

```sql
INSERT INTO Improvement_InvalidAdjacentFeatures (ImprovementType, FeatureType) VALUES
('IMPROVEMENT_SIQI_{SHORT}', 'FEATURE_MARSH');
```

> 与 ValidFeatures 互斥逻辑：Valid 写可建的，Invalid 写不可相邻的。

### K. Improvement_ValidBuildUnits — 可建造单位

```sql
INSERT INTO Improvement_ValidBuildUnits (ImprovementType, UnitType) VALUES
('IMPROVEMENT_SIQI_{SHORT}', 'UNIT_BUILDER');
```

> 默认填 `UNIT_BUILDER`。`ConsumesCharge`（默认1=消耗次数）和 `ValidRepairOnly`（默认0=可新建/1=仅可修复）通常不写。

### L. Improvement_Tourism — 旅游业绩

```sql
INSERT INTO Improvement_Tourism (ImprovementType, TourismSource, PrereqTech, PrereqCivic, ScalingFactor) VALUES
('IMPROVEMENT_SIQI_{SHORT}', 'TOURISMSOURCE_CULTURE', 'TECH_FLIGHT', NULL, 100);
```

> **TourismSource 可选值：**
> - `TOURISMSOURCE_CULTURE` — 文化=旅游业绩
> - `TOURISMSOURCE_FAITH` — 信仰=旅游业绩
> - `TOURISMSOURCE_APPEAL` — 魅力=旅游业绩
> - `TOURISMSOURCE_FOOD` — 食物=旅游业绩
>
> ScalingFactor=百分比，默认100。

### M. Improvements_XP2 — XP2 扩展属性

```sql
INSERT INTO Improvements_XP2 (ImprovementType, AllowImpassableMovement, BuildOnAdjacentPlot, PreventsDrought, DisasterResistant) VALUES
('IMPROVEMENT_SIQI_{SHORT}', 0, 0, 0, 0);
```

| 列 | 说明 | 参考 |
|---|------|------|
| AllowImpassableMovement | 允许在不可通行地块移动（山脉） | 山路/穿山隧道 |
| BuildOnAdjacentPlot | 工人站在相邻地块建造（而非自身所占格） | 滑雪场/山路 |
| PreventsDrought | 防止干旱 | 印度阶梯井 |
| DisasterResistant | 抗自然灾害 | 长城/滑雪场/山洞教堂 |

---

## 四、Text — 本地化文本

```sql
INSERT INTO LocalizedText (Language, Tag, Text) VALUES
('zh_Hans_CN', 'LOC_IMPROVEMENT_SIQI_{SHORT}_NAME',        '{中文名}'),
('zh_Hans_CN', 'LOC_IMPROVEMENT_SIQI_{SHORT}_DESCRIPTION', '{中文描述}');
```

---

## 五、Enum 文件

| 文件 | 内容 |
|------|------|
| `reference/enums/ImprovementType.txt` | 官方改良 ~63 个，分基础改良/军事工程/特色改良/特殊机制 |
| `reference/enums/PlunderType.txt` | PlunderType 可选值 |
| `reference/enums/TerrainType.txt` | ValidTerrains / ValidAdjacentTerrains 用 |
| `reference/enums/FeatureType.txt` | ValidFeatures / InvalidAdjacentFeatures 用 |
| `reference/enums/ResourceType.txt` | ValidResources / ValidAdjacentResources 用 |
