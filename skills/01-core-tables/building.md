# Building — 建筑定义

## 涉及文件

| 文件 | 内容 |
|------|------|
| `Data/<ModName>_Buildings.sql` | 建筑主表 + 子表（产出/伟人/著作/放置条件） |
| `Text/<ModName>_Text_CN.sql` | 建筑名、描述、特质名/描述 |

## 涉及的表（按 INSERT 顺序）

```
Types → Buildings → [Buildings_XP2]
→ BuildingReplaces → BuildingPrereqs
→ Building_YieldChanges → Building_CitizenYieldChanges
→ Building_YieldChangesBonusWithPower → Building_YieldsPerEra
→ Building_GreatPersonPoints → Building_GreatWorks
→ Building_ValidTerrains → Building_RequiredFeatures → Building_ValidFeatures
→ Building_ResourceCosts → Building_BuildChargeProductions
→ Building_TourismBombs_XP2 → MutuallyExclusiveBuildings
```

不归 building.md 的表：
- **BuildingModifiers** → `07-techniques/modifiers.md`（Modifier 统一管理）
- **Building_YieldDistrictCopies** → `district.md`（已在区域技能覆盖）

---

## 一、Types

```sql
INSERT INTO Types (Type, Kind) VALUES
('BUILDING_SIQI_{SHORT}', 'KIND_BUILDING'),
('TRAIT_BUILDING_SIQI_{SHORT}', 'KIND_TRAIT');
```

> 建筑特质独立于区域特质，用 `TRAIT_BUILDING_` 前缀。

---

## 二、Buildings（主表，46 列）

### 完整 INSERT 模板（必写列）

```sql
INSERT INTO Buildings (
    BuildingType,
    Name,
    Description,
    PrereqDistrict,
    Cost,
    PrereqTech,
    PrereqCivic,
    PurchaseYield,
    MustPurchase,
    Maintenance,
    IsWonder,
    TraitType,
    CitizenSlots,
    Housing,
    Entertainment,
    OuterDefenseHitPoints,
    OuterDefenseStrength,
    GrantFortification,
    DefenseModifier,
    RegionalRange,
    ObsoleteEra,
    AdvisorType,
    MaxPlayerInstances,
    MaxWorldInstances,
    Capital,
    EnabledByReligion,
    AllowsHolyCity,
    InternalOnly,
    UnlocksGovernmentPolicy,
    GovernmentTierRequirement,
    RequiresPlacement,
    RequiresRiver,
    AdjacentResource,
    Coast,
    MustBeLake,
    MustNotBeLake,
    AdjacentToMountain,
    RequiresAdjacentRiver,
    MustBeAdjacentLand,
    AdjacentCapital,
    AdjacentImprovement,
    CityAdjacentTerrain,
    Quote,
    QuoteAudio
) VALUES
(
    'BUILDING_SIQI_{SHORT}',
    'LOC_BUILDING_SIQI_{SHORT}_NAME',
    'LOC_BUILDING_SIQI_{SHORT}_DESCRIPTION',
    'DISTRICT_CAMPUS',
    90,
    'TECH_WRITING',
    NULL,
    NULL,
    0,
    1,
    0,
    'TRAIT_BUILDING_SIQI_{SHORT}',
    NULL,
    0,
    0,
    NULL,
    0,
    0,
    0,
    0,
    'NO_ERA',
    'ADVISOR_TECHNOLOGY',
    -1,
    -1,
    0,
    0,
    0,
    0,
    0,
    NULL,
    0,
    0,
    NULL,
    NULL,
    0,
    0,
    0,
    0,
    0,
    0,
    NULL,
    NULL,
    NULL,
    NULL
);
```

### 逐列参考

**身份 + 文本：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 0 | BuildingType | `BUILDING_SIQI_{SHORT}` | **必写** |
| 1 | Name | `LOC_BUILDING_SIQI_{SHORT}_NAME` | **必写** |

**前置条件：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 2 | PrereqTech | `TECH_xxx`，查 enum | 可选（二选一或全空） |
| 3 | PrereqCivic | `CIVIC_xxx`，查 enum | 可选 |
| 8 | PrereqDistrict | `DISTRICT_xxx`，写基础区域（非特色区域），奇观可不写 | **必写**（一般建筑） |
| 9 | AdjacentDistrict | `DISTRICT_xxx`，城市需有此区域并邻接。奇观用居多，普通建筑按需 | 按需 |
| 32 | RequiresReligion | 1=需要已创立宗教 | 按需 |

> PrereqDistrict 不自动继承。取代建筑时也要手动写，且永远写基础区域 Type（如 `DISTRICT_CAMPUS`，不写 `DISTRICT_SIQI_XXX`）。

**花费：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 4 | Cost | 取代建筑→复制被取代建筑的 Cost；无取代且用户未指定→反问 | **必写** |
| 20 | PurchaseYield | `YIELD_GOLD`(金币买) / `YIELD_FAITH`(信仰买) | 按需 |
| 21 | MustPurchase | 1=只能用 PurchaseYield 买，不能锤 | 按需 |
| 22 | Maintenance | 一般 1，无维护=0 | 按需 |

> PurchaseYield 不填 + MustPurchase=1 = 虚拟建筑（不可生产不可购买，特定用）。

**数量限制：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 5 | MaxPlayerInstances | -1=不限，1=每玩家限一个 | 默认不写 |
| 6 | MaxWorldInstances | -1=不限，1=全球唯一（奇观用） | 默认不写 |

**类型标志：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 7 | Capital | 1=首都自动获得此建筑（如宫殿） | 按需 |
| 18 | EnabledByReligion | 1=信仰购买需要已创立宗教（圣地建筑） | 按需 |
| 19 | AllowsHolyCity | 1=可创建宗教（如巨石阵） | 按需 |
| 23 | IsWonder | 1=奇观（不可掠夺等行为变化） | 按需 |
| 35 | InternalOnly | 写 0（语义不明，一般没必要写） | 默认不写 |
| 44 | UnlocksGovernmentPolicy | 1=解锁政策槽（市政广场建筑） | 按需 |
| 45 | GovernmentTierRequirement | `Tier1` / `Tier2` / `Tier3`（政体层级，市政广场用） | 按需 |

**描述：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 10 | Description | `LOC_BUILDING_SIQI_{SHORT}_DESCRIPTION` | **必写** |
| 37 | Quote | 引言 LOC_ 键（奇观专属） | 按需 |
| 38 | QuoteAudio | 引言音频（奇观专属，一般不用） | 按需 |

**放置条件：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 11 | RequiresPlacement | 1=需选地块放置（改良/水渠类/奇观） | 按需 |
| 12 | RequiresRiver | 1=需临河（奇观用） | 按需 |
| 16 | AdjacentResource | 资源 Type，需邻接特定资源 | 按需 |
| 17 | Coast | 1=需沿海。NULL 和 0 效果相同 | 按需 |
| 27 | MustBeLake | 1=必须在湖上 | 按需 |
| 28 | MustNotBeLake | 1=必须不在湖上 | 按需 |
| 30 | AdjacentToMountain | 1=需邻接山脉 | 按需 |
| 36 | RequiresAdjacentRiver | 1=需临河（普通建筑用） | 按需 |
| 39 | MustBeAdjacentLand | 1=需邻接陆地 | 按需 |
| 41 | AdjacentCapital | 1=需邻接首都 | 按需 |
| 42 | AdjacentImprovement | 改良 Type，需邻接特定改良 | 按需 |
| 43 | CityAdjacentTerrain | 城市需邻接某地形 | 按需 |

**防御：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 13 | OuterDefenseHitPoints | 城墙线=100，特色城墙（Tsikhe）=200 | 按需 |
| 25 | OuterDefenseStrength | 配 OuterDefenseHitPoints，城墙=3 | 按需 |
| 33 | GrantFortification | 驻防防御加成，参考：阿尔罕布拉宫=2，圣米歇尔山=2 | 按需 |
| 34 | DefenseModifier | 防御修正值（绝对值）。参考：阿尔罕布拉宫=4，圣米歇尔山=6 | 按需 |

**产出 / 人口：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 14 | Housing | 粮仓=2，灯塔=1，下水道=4，按需 | 按需 |
| 15 | Entertainment | 竞技场=2，动物园=2，按需 | 按需 |
| 26 | CitizenSlots | 专家槽位。图书馆=1，大学=1，NULL=0 | 按需 |

**特质 + 区域效应 + 过期 + 顾问：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 24 | TraitType | `TRAIT_BUILDING_SIQI_{SHORT}`（特色建筑用） | 按需 |
| 29 | RegionalRange | 产出辐射半径。建筑上显示的所有产出（基础产出/通电加成/Modifier等）均辐射到该范围内其他城市。工厂/发电厂=6，竞技场/动物园=6，非辐射=0 | 按需 |
| 31 | ObsoleteEra | `NO_ERA`(默认永不过期) / `ERA_MEDIEVAL` 等 | 按需 |
| 40 | AdvisorType | `ADVISOR_TECHNOLOGY` / `ADVISOR_CULTURE` / `ADVISOR_CONQUEST` / `ADVISOR_RELIGIOUS` / `ADVISOR_GENERIC` | 可选 |

---

## 三、Buildings_XP2

| 列名 | 值参考 | 写不写 |
|------|--------|--------|
| BuildingType | `BUILDING_SIQI_{SHORT}` | **必写** |
| RequiredPower | 1=购物中心/机场, 2=工厂/体育场, 3=研究所/广播中心 | 按需 |
| ResourceTypeConvertedToPower | `RESOURCE_COAL` / `RESOURCE_OIL` / `RESOURCE_URANIUM`（烧战略资源发电） | 按需 |
| PreventsFloods | 1=防洪 | 按需 |
| PreventsDrought | 1=防旱 | 按需 |
| BlocksCoastalFlooding | 1=防沿海泛滥。参考：防洪坝=1，其余=0 | 按需 |
| CostMultiplierPerTile | 每格成本倍数。参考：防洪坝=1，其余=0 | 按需 |
| CostMultiplierPerSeaLevel | 每海平面成本倍数。参考：防洪坝=1，其余=0 | 按需 |
| Bridge | 1=桥梁。参考：金门大桥=1 | 按需 |
| CanalWonder | 1=运河奇观。参考：巴拿马运河=1 | 按需 |
| EntertainmentBonusWithPower | 通电后宜居度加成。参考：体育场=2，购物中心=1 | 按需 |
| NuclearReactor | 1=可发生核泄漏。参考：核电站=1 | 按需 |
| Pillage | 默认 1=可掠夺，0=不可。参考：防洪坝=0 | 按需 |

不需要的列不写，不需要整张表就不写。

---

## 四、BuildingReplaces

特色建筑取代基础建筑：

```sql
INSERT INTO BuildingReplaces (CivUniqueBuildingType, ReplacesBuildingType) VALUES
('BUILDING_SIQI_{SHORT}', 'BUILDING_LIBRARY');
```

ReplacesBuildingType 枚举值后续建立 BuildingType.txt。

---

## 五、BuildingPrereqs

建筑升级链前置：

```sql
INSERT INTO BuildingPrereqs (Building, PrereqBuilding) VALUES
('BUILDING_SIQI_{SHORT}', 'BUILDING_LIBRARY');
```

> 特色建筑如果在升级链中，前置写基础建筑（如特色大学 → `BUILDING_LIBRARY`）。

---

## 六、产出类子表（按需，特色建筑默认复制被取代建筑）

### 产出复制策略

特色建筑若用户无特别说明，**查被取代建筑的产出直接复制**：

```sql
-- 以取代图书馆为例，查 LIBRARY 的各种产出
SELECT YieldType, YieldChange FROM Building_YieldChanges WHERE BuildingType = 'BUILDING_LIBRARY';
SELECT YieldType, YieldChange FROM Building_CitizenYieldChanges WHERE BuildingType = 'BUILDING_LIBRARY';
```

### Building_YieldChanges

```sql
INSERT INTO Building_YieldChanges (BuildingType, YieldType, YieldChange) VALUES
('BUILDING_SIQI_{SHORT}', 'YIELD_SCIENCE', 2);
```

建筑自身基础产出。

### Building_CitizenYieldChanges

```sql
INSERT INTO Building_CitizenYieldChanges (BuildingType, YieldType, YieldChange) VALUES
('BUILDING_SIQI_{SHORT}', 'YIELD_SCIENCE', 2);
```

专家位产出（每个公民）。

### Building_YieldChangesBonusWithPower

```sql
INSERT INTO Building_YieldChangesBonusWithPower (BuildingType, YieldType, YieldChange) VALUES
('BUILDING_SIQI_{SHORT}', 'YIELD_SCIENCE', 2);
```

通电后额外产出，需配合 Buildings_XP2.RequiredPower。

### Building_YieldsPerEra

```sql
INSERT INTO Building_YieldsPerEra (BuildingType, YieldType, YieldChange) VALUES
('BUILDING_SIQI_{SHORT}', 'YIELD_CULTURE', 1);
```

每已过时代 +N 产出。

---

## 七、伟人点数 + 著作槽位

### Building_GreatPersonPoints

```sql
INSERT INTO Building_GreatPersonPoints (BuildingType, GreatPersonClassType, PointsPerTurn) VALUES
('BUILDING_SIQI_{SHORT}', 'GREAT_PERSON_CLASS_SCIENTIST', 1);
```

GreatPersonClassType 见 [GreatPersonClassType 查询依据](../SOURCES.md#类型与枚举)（10 条）。

### Building_GreatWorks

```sql
INSERT INTO Building_GreatWorks (
    BuildingType, GreatWorkSlotType, NumSlots,
    ThemingUniquePerson, ThemingSameObjectType, ThemingUniqueCivs, ThemingSameEras,
    ThemingYieldMultiplier, ThemingTourismMultiplier,
    NonUniquePersonYield, NonUniquePersonTourism,
    ThemingBonusDescription
) VALUES
(
    'BUILDING_SIQI_{SHORT}',
    'GREATWORKSLOT_ART', 3,
    1, 1, 0, 0,
    100, 100,
    1, 1,
    'LOC_BUILDING_THEMINGBONUS_SIQI_{SHORT}'
);
```

**GreatWorkSlotType**（7 种）：

```
GREATWORKSLOT_ART      — 艺术作品
GREATWORKSLOT_ARTIFACT — 文物
GREATWORKSLOT_MUSIC    — 音乐
GREATWORKSLOT_WRITING  — 著作
GREATWORKSLOT_RELIC    — 遗物
GREATWORKSLOT_CATHEDRAL — 大教堂（宗教艺术）
GREATWORKSLOT_PALACE   — 宫殿（任意类型）
```

**主题化列：**

| 列 | 说明 |
|------|------|
| ThemingUniquePerson | 要求不同作者（如不同艺术家/作家） |
| ThemingSameObjectType | 要求相同作品类型（如都是雕塑） |
| ThemingUniqueCivs | 要求不同文明（文物用，艺术/音乐/著作一般不写） |
| ThemingSameEras | 要求相同年代（文物用） |
| ThemingYieldMultiplier | 主题化产出加成，百分比。100=+100% |
| ThemingTourismMultiplier | 主题化旅游加成，百分比。100=+100% |
| NonUniquePersonYield | 非主题化基础产出 |
| NonUniquePersonTourism | 非主题化基础旅游 |
| ThemingBonusDescription | 主题化描述 LOC_ 键 |

**ThemingBonusDescription 文本模板：**

```
当展示来自 {条件1}{条件2}的 {[ICON_GreatWork_xxx] 巨作类型名}时，主题加成翻倍。
```

官方参考：
```
LOC_BUILDING_THEMINGBONUS_ART：
当展示来自不同艺术家相同类型的作品时，主题加成翻倍。

LOC_BUILDING_THEMINGBONUS_ARCHAEOLOGY：
当展示来自不同文明相同时代的 [ICON_GreatWork_Artifact] 文物时，主题加成翻倍。
```

---

## 八、放置条件

### Building_ValidTerrains

```sql
INSERT INTO Building_ValidTerrains (BuildingType, TerrainType) VALUES
('BUILDING_SIQI_{SHORT}', 'TERRAIN_GRASS');
```

可放置地形。TerrainType 查 [TerrainType 查询依据](../SOURCES.md#类型与枚举)。

### Building_RequiredFeatures

```sql
INSERT INTO Building_RequiredFeatures (BuildingType, FeatureType) VALUES
('BUILDING_SIQI_{SHORT}', 'FEATURE_FOREST');
```

**必须有**该地貌才能放置。

### Building_ValidFeatures

```sql
INSERT INTO Building_ValidFeatures (BuildingType, FeatureType) VALUES
('BUILDING_SIQI_{SHORT}', 'FEATURE_FLOODPLAINS');
```

**允许**在该地貌上放置（本来会阻止的）。奇观用居多。

FeatureType 查 [FeatureType 查询依据](../SOURCES.md#类型与枚举)。

---

## 九、资源消耗 + 建造加速

### Building_ResourceCosts

```sql
INSERT INTO Building_ResourceCosts (BuildingType, ResourceType, StartProductionCost, PerTurnMaintenanceCost) VALUES
('BUILDING_SIQI_{SHORT}', 'RESOURCE_COAL', 1, 1);
```

- ResourceType **只能用战略资源**（RESOURCE_COAL / RESOURCE_OIL / RESOURCE_URANIUM 等）
- StartProductionCost：初始消耗量
- PerTurnMaintenanceCost：每回合消耗量

### Building_BuildChargeProductions

```sql
INSERT INTO Building_BuildChargeProductions (BuildingType, UnitType, PercentProductionPerCharge) VALUES
('BUILDING_SIQI_{SHORT}', 'UNIT_MILITARY_ENGINEER', 20);
```

军事工程师使用建造次数加速（堤坝/运河类用）。

---

## 十、旅游爆发 + 互斥

### Building_TourismBombs_XP2

```sql
INSERT INTO Building_TourismBombs_XP2 (BuildingType, TourismBombValue) VALUES
('BUILDING_SIQI_{SHORT}', 250);
```

| TourismBombValue | 对应 Cost 范围 | 参考建筑 |
|------|------|------|
| 250 | 135–150（低价） | 圆形竞技场/角斗场/大浴场 |
| 500 | 250–290（中价） | 大学/港口造船厂/航海学校 |
| 750 | 440–510（高价） | 体育场/广播中心/电影制片厂/水上运动中心 |

### MutuallyExclusiveBuildings

两建筑不共存，双向各写一行：

```sql
INSERT INTO MutuallyExclusiveBuildings (Building, MutuallyExclusiveBuilding) VALUES
('BUILDING_SIQI_{SHORT}', 'BUILDING_LIBRARY'),
('BUILDING_LIBRARY', 'BUILDING_SIQI_{SHORT}');
```

---

## 十一、文本（Text/ 文件）

### 需要创建的 LOC_ 键

| LOC_ 键 | 说明 | 是否必须 |
|---------|------|---------|
| `LOC_BUILDING_SIQI_{SHORT}_NAME` | 建筑名称 | **是** |
| `LOC_BUILDING_SIQI_{SHORT}_DESCRIPTION` | 建筑描述 | **是** |
| `LOC_TRAIT_BUILDING_SIQI_{SHORT}_NAME` | 特质名称 | 特色建筑时 |
| `LOC_TRAIT_BUILDING_SIQI_{SHORT}_DESCRIPTION` | 特质描述 | 特色建筑时 |
| `LOC_BUILDING_THEMINGBONUS_SIQI_{SHORT}` | 主题化描述 | 有著作槽位时 |
| `LOC_PEDIA_BUILDINGS_PAGE_BUILDING_SIQI_{SHORT}_QUOTE` | 百科引言 | 奇观时 |

### Text INSERT 模板

```sql
INSERT INTO LocalizedText (Language, Tag, Text) VALUES
('zh_Hans_CN', 'LOC_BUILDING_SIQI_{SHORT}_NAME',              '{建筑名称}'),
('zh_Hans_CN', 'LOC_BUILDING_SIQI_{SHORT}_DESCRIPTION',       '{建筑描述}'),
-- 特色建筑（可选）
('zh_Hans_CN', 'LOC_TRAIT_BUILDING_SIQI_{SHORT}_NAME',        '{特质名称}'),
('zh_Hans_CN', 'LOC_TRAIT_BUILDING_SIQI_{SHORT}_DESCRIPTION', '{特质描述}'),
-- 主题化（可选）
('zh_Hans_CN', 'LOC_BUILDING_THEMINGBONUS_SIQI_{SHORT}',      '当展示来自{条件}的{类型}时，主题加成翻倍。');
```

> 如果特质名称/描述与区域相同，可用 `LOC_TRAIT_BUILDING_SIQI_{SHORT}_NAME` 引用。

---

## 十二、关联文件

| 文件 | 技能 | 说明 |
|------|------|------|
| `Data/<ModName>_Districts.sql` | `district.md` | CivilizationTraits 绑 TRAIT_DISTRICT，区域注册特质 |
| `Data/<ModName>_Civilizations.sql` | `civilization.md` | CivilizationTraits 绑建筑特质 |
| `Data/<ModName>_Configs.sql` | `configs.md` | PlayerItems 注册特色建筑展示 |
| `Icons/<ModName>_Icons.xml` | `icons.md` | 建筑图标（尺寸 32/38/50/80/128/256） |
| `<ModName>.civ6proj` | `civ6proj.md` | 注册 UpdateDatabase |
| `Data/<ModName>_Modifiers.sql` | `modifiers.md` | BuildingModifiers 绑定 |
