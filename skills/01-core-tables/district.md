# District — 区域定义

## 涉及文件

| 文件 | 内容 |
|------|------|
| `Data/<ModName>_Districts.sql` | 区域主表 + 子表（替代/产出/伟人/放置条件） |
| `Text/<ModName>_Text_CN.sql` | 区域名、描述、特质名/描述 |

## 涉及的表（按 INSERT 顺序）

```
Types → Traits → DistrictReplaces → Districts → [Districts_XP2]
→ [District_CitizenYieldChanges] → [District_TradeRouteYields]
→ [District_GreatPersonPoints] → [District_CitizenGreatPersonPoints]
→ [District_ValidTerrains] → [District_RequiredFeatures]
→ [ExcludedDistricts] → [MutuallyExclusiveDistricts]
→ [District_BuildChargeProductions] → [Building_YieldDistrictCopies]
```

不归 district.md 的表：
- **DistrictModifiers** → `07-techniques/modifiers.md`（Modifier 统一管理）
- **District_Adjacencies** → `district-adjacency.md`（相邻加成单独 skill，SQL 写入 Districts.sql）

---

## 一、Types

```sql
INSERT INTO Types (Type, Kind) VALUES
('DISTRICT_SIQI_{SHORT}', 'KIND_DISTRICT'),
('TRAIT_DISTRICT_SIQI_{SHORT}', 'KIND_TRAIT');
```

---

## 二、Traits

区域特质在 Traits 表中注册：

```sql
INSERT INTO Traits (TraitType, Name, Description) VALUES
('TRAIT_DISTRICT_SIQI_{SHORT}',
 'LOC_TRAIT_DISTRICT_SIQI_{SHORT}_NAME',
 'LOC_TRAIT_DISTRICT_SIQI_{SHORT}_DESCRIPTION');
```

---

## 三、DistrictReplaces

```sql
INSERT INTO DistrictReplaces (CivUniqueDistrictType, ReplacesDistrictType) VALUES
('DISTRICT_SIQI_{SHORT}', 'DISTRICT_CAMPUS');
```

- 非特色区域不写此表
- ReplacesDistrictType 枚举值见 [reference/enums/DistrictType.txt](../../reference/enums/DistrictType.txt)（41 条，含中文名，不含 Mod 区域）

---

## 四、Districts（主表，40 列）

### 完整 INSERT 模板（必写列）

```sql
INSERT INTO Districts (
    DistrictType,
    Name,
    Description,
    PrereqCivic,
    Cost,
    RequiresPlacement,
    NoAdjacentCity,
    Aqueduct,
    InternalOnly,
    CaptureRemovesBuildings,
    CaptureRemovesCityDefenses,
    PlunderType,
    PlunderAmount,
    MilitaryDomain,
    CostProgressionParam1,
    Appeal,
    Maintenance,
    CitizenSlots,
    CityStrengthModifier,
    AdvisorType,
    TraitType
) VALUES
(
    'DISTRICT_SIQI_{SHORT}',
    'LOC_DISTRICT_SIQI_{SHORT}_NAME',
    'LOC_DISTRICT_SIQI_{SHORT}_DESCRIPTION',
    'CIVIC_CODE_OF_LAWS',
    27,
    1,
    0,
    0,
    0,
    0,
    0,
    'PLUNDER_SCIENCE',
    25,
    'NO_DOMAIN',
    40,
    0,
    1,
    0,
    2,
    'ADVISOR_TECHNOLOGY',
    'TRAIT_DISTRICT_SIQI_{SHORT}'
);
```

### 逐列参考

**身份 + 文本：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 0 | DistrictType | `DISTRICT_SIQI_{SHORT}` | **必写** |
| 1 | Name | `LOC_DISTRICT_SIQI_{SHORT}_NAME` | **必写** |
| 5 | Description | `LOC_DISTRICT_SIQI_{SHORT}_DESCRIPTION` | **必写** |

**前置 + 花费：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 2 | PrereqTech | `TECH_xxx`，查 enum | 可选（二选一或全空=继承取代区域） |
| 3 | PrereqCivic | `CIVIC_xxx`，查 enum | 可选 |
| 6 | Cost | 标准 `54`，低价 `27` | **必写** |

**放置与城市关系：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 4 | Coast | 1=必须海岸，默认0不写 | 按需 |
| 7 | RequiresPlacement | 1（需选地块放置） | **必写** |
| 8 | RequiresPopulation | 1=消耗区域位（每3人口1个位），默认1不写 | 按需 |
| 9 | NoAdjacentCity | 1=不需邻接市中心，0=需要 | **必写** |
| 10 | CityCenter | **永远不写**（有严重bug） | 不写 |
| 35 | AdjacentToLand | 1=必须邻接陆地，默认0不写 | 按需 |

**特殊类型标志：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 11 | Aqueduct | 1=水渠类效果，按需 | 按需 |
| 12 | InternalOnly | 写 0（意义不明，一般没必要写） | 默认不写 |
| 28 | OnePerCity | 1=每城限一(默认)，0=可多个 | 按需 |
| 29 | AllowsHolyCity | 1=可创建宗教（圣地效果），按需 | 按需 |

**战斗与防御：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 13 | ZOC | 1=有控制区(敌人进入后本回合无法离开)，默认0 | 按需 |
| 14 | FreeEmbark | 1=不消耗额外移动力下海，默认0 | 按需 |
| 15 | HitPoints | 一般填 100（有血条的区域如军营） | 按需 |
| 16 | CaptureRemovesBuildings | 一般 0，军营类有血条才填 1 | **必写** |
| 17 | CaptureRemovesCityDefenses | 一般 0，用户无说明时默认 0 | **必写** |
| 34 | CityStrengthModifier | 区域提供城防加成，默认0 | 按需 |
| 36 | CanAttack | 1=区域可远程攻击，默认0 | 按需 |

**掠夺：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 18 | PlunderType | `PLUNDER_SCIENCE` / `PLUNDER_GOLD` / `PLUNDER_FAITH` / `PLUNDER_CULTURE` / `NO_PLUNDER` | **必写** |
| 19 | PlunderAmount | 标准 25 | **必写** |
| 38 | CaptureRemovesDistrict | 默认0不写 | 按需 |

**贸易 + 军事域 + 花费模型：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 20 | TradeEmbark | 1=商路可穿越水域（市中心+港口系为1，水域区域默认1） | 按需 |
| 21 | MilitaryDomain | `NO_DOMAIN` / `DOMAIN_LAND` / `DOMAIN_SEA` / `DOMAIN_AIR` | **必写** |
| 22 | CostProgressionModel | `COST_PROGRESSION_NUM_UNDER_AVG_PLUS_TECH`(标准) / `COST_PROGRESSION_GAME_PROGRESS`(Param=1000) / `NO_COST_PROGRESSION` | 默认不写（继承） |
| 23 | CostProgressionParam1 | 标准 40（配合 NUM_UNDER_AVG_PLUS_TECH），25为低价 | **必写** |
| 33 | TravelTime | 默认 -1。取代某区域时复制其值：机场=1 / 港口系=2 / 商业系=3 / 市中心=4 | 按需 |

**特质 + 顾问 + 上限：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 24 | TraitType | `TRAIT_DISTRICT_SIQI_{SHORT}`（特色区域必写，非特色不写） | 按需 |
| 37 | AdvisorType | `ADVISOR_TECHNOLOGY` / `ADVISOR_CONQUEST` / `ADVISOR_CULTURE` / `ADVISOR_RELIGIOUS` / `ADVISOR_GENERIC` | 可选 |
| 39 | MaxPerPlayer | -1=不限(默认)，1=全局限造一个 | 默认不写 |

**杂项：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 25 | Appeal | 相邻地块魅力值修正，默认0 | 按需 |
| 26 | Housing | 区域提供住房，默认0 | 按需 |
| 27 | Entertainment | 区域提供宜居度，默认0 | 按需 |
| 30 | Maintenance | 维护费，标准 1 | 按需 |
| 31 | AirSlots | 空军槽位，机场用，默认0 | 按需 |
| 32 | CitizenSlots | 专家位（人口可在此工作），按需 | 按需 |

---

## 五、Districts_XP2

| 列名 | 值参考 | 写不写 |
|------|--------|--------|
| DistrictType | `DISTRICT_SIQI_{SHORT}` | **必写** |
| OnePerRiver | 1=每条河限一个(河堤坝效果) | 按需 |
| PreventsFloods | 1=防洪(堤坝) | 按需 |
| PreventsDrought | 1=防旱 | 按需 |
| Canal | 1=运河连接水域 | 按需 |
| AttackRange | 一般填 2（用户说明此区域可攻击时） | 按需 |

不需要的列不写，不需要整张表就不写。

---

## 六、产出类子表（按需，特色区域默认复制被取代区域）

### 产出复制策略

特色区域若用户无特别说明，**查被取代区域的值直接复制**：

```sql
-- 以取代学院为例，查 CAMPUS 的商路产出
SELECT YieldType, YieldChangeAsOrigin, YieldChangeAsDomesticDestination, YieldChangeAsInternationalDestination
FROM District_TradeRouteYields
WHERE DistrictType = 'DISTRICT_CAMPUS';
```

常见被取代区域产出速查：

| 被取代区域 | TradeRoute 产出 | CitizenYield |
|-----------|----------------|--------------|
| CAMPUS | FOOD(国内=1) + SCIENCE(国际=1) | — |
| COMMERCIAL_HUB | PRODUCTION(国内=1) + GOLD(国际=3) | — |
| HARBOR | PRODUCTION(国内=1) + GOLD(国际=3) | — |
| HOLY_SITE | FOOD(国内=1) + FAITH(国际=1) | — |
| THEATER | FOOD(国内=1) + CULTURE(国际=1) | — |
| INDUSTRIAL_ZONE | PRODUCTION(国内=1, 国际=1) | — |
| ENCAMPMENT | PRODUCTION(国内=1, 国际=1) | — |
| ENTERTAINMENT_COMPLEX | FOOD(国内=1, 国际=1) | — |

### District_CitizenYieldChanges

```sql
INSERT INTO District_CitizenYieldChanges (DistrictType, YieldType, YieldChange) VALUES
('DISTRICT_SIQI_{SHORT}', 'YIELD_SCIENCE', 2);
```

- YieldType：`YIELD_SCIENCE` / `YIELD_CULTURE` / `YIELD_GOLD` / `YIELD_FAITH` / `YIELD_PRODUCTION` / `YIELD_FOOD`
- YieldChange：每公民产出量

### District_TradeRouteYields

```sql
INSERT INTO District_TradeRouteYields (
    DistrictType, YieldType,
    YieldChangeAsOrigin,
    YieldChangeAsDomesticDestination,
    YieldChangeAsInternationalDestination
) VALUES
('DISTRICT_SIQI_{SHORT}', 'YIELD_SCIENCE', 0, 0, 1),
('DISTRICT_SIQI_{SHORT}', 'YIELD_FOOD', 0, 1, 0);
```

- 三列分别控制起点/国内/国际产出，写整数不用小数（`1` 不写 `1.0`）

### District_BuildChargeProductions

军事工程师使用建造次数加速（水渠/堤坝/运河类用）：

```sql
INSERT INTO District_BuildChargeProductions (DistrictType, UnitType, PercentProductionPerCharge) VALUES
('DISTRICT_SIQI_{SHORT}', 'UNIT_MILITARY_ENGINEER', 20);
```

### Building_YieldDistrictCopies

将建筑的某种产出按相邻加成值复制到区域：

```sql
INSERT INTO Building_YieldDistrictCopies (BuildingType, OldYieldType, NewYieldType) VALUES
('BUILDING_SIQI_{SHORT}', 'YIELD_SCIENCE', 'YIELD_SCIENCE');
```

---

## 七、伟人点数

### District_GreatPersonPoints

```sql
INSERT INTO District_GreatPersonPoints (DistrictType, GreatPersonClassType, PointsPerTurn) VALUES
('DISTRICT_SIQI_{SHORT}', 'GREAT_PERSON_CLASS_SCIENTIST', 1);
```

### District_CitizenGreatPersonPoints

```sql
INSERT INTO District_CitizenGreatPersonPoints (DistrictType, GreatPersonClassType, PointsPerTurn) VALUES
('DISTRICT_SIQI_{SHORT}', 'GREAT_PERSON_CLASS_SCIENTIST', 1);
```

GreatPersonClassType 见 [reference/enums/GreatPersonClassType.txt](../../reference/enums/GreatPersonClassType.txt)（10 条，含中文名，不含 Mod）

---

## 八、放置条件

### District_ValidTerrains

```sql
INSERT INTO District_ValidTerrains (DistrictType, TerrainType) VALUES
('DISTRICT_SIQI_{SHORT}', 'TERRAIN_GRASS');
```

TerrainType 查 [reference/enums/TerrainType.txt](../../reference/enums/TerrainType.txt)。

### District_RequiredFeatures

```sql
INSERT INTO District_RequiredFeatures (DistrictType, FeatureType) VALUES
('DISTRICT_SIQI_{SHORT}', 'FEATURE_FOREST');
```

FeatureType 查 [reference/enums/FeatureType.txt](../../reference/enums/FeatureType.txt)。

---

## 九、互斥表

### ExcludedDistricts

某特质生效时排除某区域：

```sql
INSERT INTO ExcludedDistricts (DistrictType, TraitType) VALUES
('DISTRICT_SIQI_{SHORT}', 'TRAIT_CIVILIZATION_SIQI_C{SHORT}');
```

### MutuallyExclusiveDistricts

两区域不共存于同一城市，双向各写一行：

```sql
INSERT INTO MutuallyExclusiveDistricts (District, MutuallyExclusiveDistrict) VALUES
('DISTRICT_SIQI_{SHORT}', 'DISTRICT_CAMPUS'),
('DISTRICT_CAMPUS', 'DISTRICT_SIQI_{SHORT}');
```

---

## 十、文本（Text/ 文件）

### 需要创建的 LOC_ 键

| LOC_ 键 | 说明 |
|---------|------|
| `LOC_DISTRICT_SIQI_{SHORT}_NAME` | 区域名称 |
| `LOC_DISTRICT_SIQI_{SHORT}_DESCRIPTION` | 区域描述 |
| `LOC_TRAIT_DISTRICT_SIQI_{SHORT}_NAME` | 特质名称 |
| `LOC_TRAIT_DISTRICT_SIQI_{SHORT}_DESCRIPTION` | 特质描述 |

### Text INSERT 模板

```sql
INSERT INTO LocalizedText (Language, Tag, Text) VALUES
('zh_Hans_CN', 'LOC_DISTRICT_SIQI_{SHORT}_NAME',              '{区域名称}'),
('zh_Hans_CN', 'LOC_DISTRICT_SIQI_{SHORT}_DESCRIPTION',       '{区域描述}'),
('zh_Hans_CN', 'LOC_TRAIT_DISTRICT_SIQI_{SHORT}_NAME',        '{特质名称}'),
('zh_Hans_CN', 'LOC_TRAIT_DISTRICT_SIQI_{SHORT}_DESCRIPTION', '{特质描述}');
```

> 如果特质名称/描述与区域相同，可用 `{LOC_DISTRICT_SIQI_{SHORT}_NAME}` 引用链。

---

## 十一、关联文件

| 文件 | 技能 | 说明 |
|------|------|------|
| `Data/<ModName>_Civilizations.sql` | `civilization.md` | CivilizationTraits 绑 TRAIT_DISTRICT |
| `Data/<ModName>_Configs.sql` | `configs.md` | PlayerItems 注册特色区域展示 |
| `Icons/<ModName>_Icons.xml` | `icons.md` | 区域图标（尺寸 22/32/38/50/80/128/256） |
| `<ModName>.civ6proj` | `civ6proj.md` | 注册 UpdateDatabase |
| `Data/<ModName>_Modifiers.sql` | `modifiers.md` | DistrictModifiers 绑定 |
| `district-adjacency.md` | 相邻加成 | District_Adjacencies 写入 Districts.sql |
