# 产品巨作系统（来源：工坊 2616754773 CorporationsDiversity + 2479197624）

## 做什么
重新设计公司产品（Product Great Works），按资源类别分配不同的产出和旅游业绩。
扩展产品展示位（建筑中的 GreatWorkSlot）和主题加成（Theming）。
增加 4 种新项目用于创建特定公司产品（玩具、化妆品、牛仔裤、香水）。

## SQL 配合

### 产品产出按类别分配

`Database/products.sql`

```sql
-- 宜居度类产品：+4锤 +8金
INSERT INTO GreatWork_YieldChanges
SELECT 'GREATWORK_PRODUCT_'||substr(ResourceType,10)||'_'||Count, 'YIELD_PRODUCTION', 4
FROM HDMonopolyResourceEffects a, HDCounter b WHERE Category = 'AMENITY' AND Count < 6;

-- 增长类产品：+8粮
-- 信仰类产品：+5信仰 +6金
-- 伟人点类产品：+4科技 +4文化
-- 贸易类产品：+16金
-- 食品类产品：+4粮 +8金
-- 奇观类产品：+8锤
-- 旅游类产品：+6文化（旅游业绩24）
-- 渔业类产品：+4粮 +4锤
```

### 旅游业绩差异化
```sql
-- 默认产品旅游业绩为 18
UPDATE GreatWorks SET Tourism = 18
WHERE GreatWorkType LIKE 'GREATWORK_PRODUCT_%';

-- 旅游类和娱乐类产品旅游业绩为 24
UPDATE GreatWorks SET Tourism = 24
WHERE GreatWorkType IN (
    SELECT 'GREATWORK_PRODUCT_'||substr(ResourceType,10)||'_'||Count
    FROM HDMonopolyResourceEffects a, HDCounter b
    WHERE Category IN ('TOURISM', 'ENTERTAINMENT') AND Count < 6
);
```

### 新项目：创建特定公司产品

`GreatPerson/Products.sql` — 定义 4 个新项目：

| 项目 | 所需资源 | 成本 |
|------|----------|------|
| `PROJECT_CREATE_PRODUCT_TOYS` | RESOURCE_TOYS | 160 |
| `PROJECT_CREATE_PRODUCT_COSMETICS` | RESOURCE_COSMETICS | 280 |
| `PROJECT_CREATE_PRODUCT_JEANS` | RESOURCE_JEANS | 280 |
| `PROJECT_CREATE_PRODUCT_PERFUME` | RESOURCE_PERFUME | 340 |

```sql
-- 项目定义
INSERT INTO Projects (ProjectType, Name, ShortName, Description, Cost, AdvisorType)
VALUES ('PROJECT_CREATE_PRODUCT_TOYS', ..., 160, 'ADVISOR_GENERIC');

-- 完成效果：随机获得一个对应资源的产品
INSERT INTO Modifiers (ModifierId, ModifierType)
VALUES ('PROJECT_COMPLETE_CREATE_TOYS_PRODUCT', 'MODIFIER_PLAYER_GRANT_RANDOM_RESOURCE_PRODUCT');

INSERT INTO ModifierArguments (ModifierId, Name, Value)
VALUES ('PROJECT_COMPLETE_CREATE_TOYS_PRODUCT', 'ResourceType', 'RESOURCE_TOYS');

-- 项目-资源关联（MODE表）
INSERT INTO Projects_MODE (ProjectType, ResourceType)
VALUES ('PROJECT_CREATE_PRODUCT_TOYS', 'RESOURCE_TOYS');
```

### 公司产品巨作定义

为每种公司资源生成 5 个产品变体（通过 HDCounter 1-5）：

#### 玩具公司（TOYS）
| 产品 | 产出 |
|------|------|
| TOYS_1 | +10锤 |
| TOYS_2 | +20金 |
| TOYS_3 | +10信仰 |
| TOYS_4 | +10文化 |
| TOYS_5 | +10科技 |

旅游业绩统一 24。

#### 化妆品公司（COSMETICS）
| 产品 | 产出 |
|------|------|
| COSMETICS_1-5 | +8文化 +8金 |

旅游业绩 30。附加效果：`HD_PRODUCT_CITY_AMENITY`（城市宜居度加成）。

#### 牛仔裤公司（JEANS）
| 产品 | 产出 |
|------|------|
| JEANS_1-5 | +8锤 +4信仰 |

旅游业绩 30。附加效果：`HD_PRODUCT_CITY_AMENITY`。

#### 香水公司（PERFUME）
| 产品 | 产出 |
|------|------|
| PERFUME_1-5 | +4文化 +20金 |

旅游业绩 36（最高）。附加效果：`HD_PRODUCT_CITY_AMENITY`。

```sql
-- 生成模式（以玩具为例）
INSERT INTO Types (Type, Kind)
SELECT 'GREATWORK_PRODUCT_TOYS_'||Count, 'KIND_GREATWORK'
FROM HDCounter WHERE Count < 6;

INSERT INTO GreatWorks (GreatWorkType, GreatWorkObjectType, Tourism, Name)
SELECT 'GREATWORK_PRODUCT_TOYS_'||Count, 'GREATWORKOBJECT_PRODUCT', 24,
       'LOC_GREATWORK_PRODUCT_TOYS_'||Count||'_NAME'
FROM HDCounter WHERE Count < 6;

INSERT INTO GreatWorks_ImprovementType (GreatWorkType, ResourceType)
SELECT 'GREATWORK_PRODUCT_TOYS_'||Count, 'RESOURCE_TOYS'
FROM HDCounter WHERE Count < 6;
```

### 产品槽位和主题加成

`Database/database.sql`

#### 建筑槽位扩展
```sql
-- 基础槽位
INSERT INTO Building_GreatWorks VALUES ('BUILDING_EXHIBITION', 'GREATWORKSLOT_PRODUCT', 1);

-- 调整已有建筑槽位
UPDATE Building_GreatWorks SET NumSlots = 2 WHERE GreatWorkSlotType = 'GREATWORKSLOT_PRODUCT'
  AND BuildingType IN ('BUILDING_SEAPORT','BUILDING_STOCK_EXCHANGE','BUILDING_FOOD_MARKET','BUILDING_SHOPPING_MALL');

-- 新增建筑槽位
INSERT INTO Building_GreatWorks (BuildingType, GreatWorkSlotType, NumSlots) VALUES
('BUILDING_CANAL',             'GREATWORKSLOT_PRODUCT', 1),
('BUILDING_CASA_DE_CONTRATACION','GREATWORKSLOT_PRODUCT', 3),
('BUILDING_RUHR_VALLEY',      'GREATWORKSLOT_PRODUCT', 3),
('BUILDING_BIG_BEN',          'GREATWORKSLOT_PRODUCT', 3),
('BUILDING_AIRPORT',          'GREATWORKSLOT_PRODUCT', 2),
('BUILDING_PANAMA_CANAL',     'GREATWORKSLOT_PRODUCT', 3),
('BUILDING_PORCELAIN_TOWER',  'GREATWORKSLOT_PRODUCT', 3),
('BUILDING_BURJ_KHALIFA',     'GREATWORKSLOT_PRODUCT', 4),
('WON_CL_EMPIRE_STATES',      'GREATWORKSLOT_PRODUCT', 4);
```

#### 主题加成
```sql
-- 3槽及以上：每个不同伟人=+100%产出/+100%旅游
UPDATE Building_GreatWorks SET
    ThemingUniquePerson = 1,
    ThemingYieldMultiplier = 100,
    ThemingTourismMultiplier = 100,
    ThemingBonusDescription = 'LOC_BUILDING_THEMINGBONUS_PRODUCT_UNIQUE'
WHERE GreatWorkSlotType = 'GREATWORKSLOT_PRODUCT' AND NumSlots >= 3;

-- 帝国大厦和哈利法塔：所有产品同类型=+200%产出/+200%旅游
UPDATE Building_GreatWorks SET
    ThemingUniquePerson = 0,
    ThemingSameObjectType = 1
WHERE BuildingType IN ('WON_CL_EMPIRE_STATES', 'BUILDING_BURJ_KHALIFA');
```

#### 银行巨作槽位更新
```sql
UPDATE ModifierArguments SET Value = 'GREATWORKSLOT_PRODUCT'
WHERE ModifierId = 'GREATPERSON_BANK_GREAT_WORK_SLOTS' AND Name = 'GreatWorkSlotType';
```
让银行伟人提供产品槽位（而非普通巨作槽）。

### 产品旅游加成
```sql
-- 仓库/码头给产品类巨作提供旅游
INSERT INTO Modifiers VALUES ('HD_WAREHOUSE_PRODUCT_TOURISM',
    'MODIFIER_SINGLE_CITY_ADJUST_TOURISM', null);
-- Args: GreatWorkObjectType='GREATWORKOBJECT_PRODUCT', ScalingFactor=150

-- 电子商务政策强化
INSERT INTO Modifiers VALUES ('ECOMMERCE_PRODUCT_TOURISM',
    'MODIFIER_PLAYER_CITIES_ADJUST_TOURISM', null);
-- Args: GreatWorkObjectType='GREATWORKOBJECT_PRODUCT', ScalingFactor=300
-- 供电后：ECOMMERCE_PRODUCT_TOURISM_POWERED (SubjectRequirementSet='CITY_IS_POWERED')

-- 巴拿马运河
INSERT INTO Modifiers VALUES ('PANAMA_PRODUCT_TOURISM',
    'MODIFIER_PLAYER_CITIES_ADJUST_TOURISM', 'HD_CITY_HAS_CANAL');
-- Args: ScalingFactor=150

-- 金融中心奇迹
INSERT INTO Modifiers VALUES ('HD_NAT_FINANCE_PRODUCT_TOURISM',
    'MODIFIER_PLAYER_CITIES_ADJUST_TOURISM', 'HD_CITY_HAS_BUILDING_EXHIBITION_NO_BUILDING_CANAL');
```

### 清理原版数据
```sql
-- 删除原版产品modifier和产出
DELETE FROM GreatWorkModifiers WHERE GreatWorkType LIKE 'GREATWORK_PRODUCT_%';
DELETE FROM GreatWork_YieldChanges WHERE GreatWorkType LIKE 'GREATWORK_PRODUCT_%';
DELETE FROM Projects_XP2 WHERE ProjectType LIKE 'PROJECT_CREATE_CORPORATION_PRODUCT_%';
-- 统一项目成本
UPDATE Projects SET Cost = 160 WHERE ProjectType LIKE 'PROJECT_CREATE_CORPORATION_PRODUCT_%';
```

### 展示厅建筑 + 改良地块金加成
```sql
INSERT INTO BuildingModifiers VALUES ('BUILDING_EXHIBITION', 'HD_EXHIBITION_IMPROVEMENT_GOLD');
INSERT INTO Modifiers VALUES ('HD_EXHIBITION_IMPROVEMENT_GOLD',
    'MODIFIER_CITY_PLOT_YIELDS_ADJUST_PLOT_YIELD', 'PLOT_IS_IMPROVED');
-- Args: YieldType='YIELD_GOLD', Amount=3
```
城市中有展示厅时，所有已改良地块+3金币。

## Lua 端
此系统纯 SQL 实现，无独立 Lua。

## XML 配合
无独立 XML。文本定义在 `Text/HD_Monopoly_Text.sql` 和 `GreatPerson/GreatPerson_Text.sql` 中。
