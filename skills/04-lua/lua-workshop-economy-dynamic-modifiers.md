# 动态 Modifier 生成技术（来源：工坊 2479197624 + 2616754773）

## 做什么
通过 SQL 的 `INSERT ... SELECT` 从已有数据**自动批量生成** Modifier / Requirement / RequirementSet，避免手工为每种资源写重复代码。

核心思路：用一张临时表或已有数据表作为"模板数据源"，通过字符串拼接动态生成所有配套数据库条目。

## Corporation Boost 自动生成（MonopolyPlus 2479197624）

`Core/MonopolyPlus_ImprovementsCorporationBoost.sql`

### 临时映射表
```sql
CREATE TABLE Leu_CorporationResourceReqs (
    ResourceType        TEXT PRIMARY KEY,
    BoostModifier       TEXT,  -- 例如 'LEU_INVESTOR_CORPORATION_BOOST_SUGAR'
    AdjRequirementSet   TEXT,  -- 例如 'LEU_BOOSTER_ADJ_TO_SUGAR'
    CorpRequirementSet  TEXT,  -- 例如 'LEU_IS_SUGAR_CORPORATION'
    PropertyRequirement TEXT,  -- 例如 'REQUIRES_LEU_ADJ_SUGAR_PROPERTY'
    ResourceRequirement TEXT,  -- 例如 'REQUIRES_LEU_CORP_TILE_HAS_SUGAR'
    ResourceProperty    TEXT   -- 例如 'Leu_Warehouse_Has_SUGAR'
);

-- 从 ResourceCorporations 表自动填充
INSERT OR REPLACE INTO Leu_CorporationResourceReqs
SELECT ResourceType,
    'LEU_INVESTOR_CORPORATION_BOOST_'||ResourceType,
    'LEU_BOOSTER_ADJ_TO'||ResourceType,
    'LEU_IS_'||ResourceType||'_CORPORATION',
    'REQUIRES_LEU_ADJ_'||ResourceType||'_PROPERTY',
    'REQUIRES_LEU_CORP_TILE_HAS_'||ResourceType,
    'Leu_Warehouse_Has_'||ResourceType
FROM ResourceCorporations;
```

### 批量生成 6 类数据库条目
```sql
-- 1. ImprovementModifiers（仓库和码头各一份）
INSERT INTO ImprovementModifiers (ImprovementType, ModifierId)
SELECT 'IMPROVEMENT_LEU_WAREHOUSE', BoostModifier FROM Leu_CorporationResourceReqs;
INSERT INTO ImprovementModifiers (ImprovementType, ModifierId)
SELECT 'IMPROVEMENT_LEU_CONTAINER_PORT', BoostModifier FROM Leu_CorporationResourceReqs;

-- 2. Modifiers（地块产出加成和商路加成）
INSERT INTO Modifiers (ModifierId, ModifierType, OwnerRequirementSetId, SubjectRequirementSetId)
SELECT BoostModifier, 'MODIFIER_GAME_ADJUST_PLOT_YIELD', AdjRequirementSet, CorpRequirementSet
FROM Leu_CorporationResourceReqs;

-- 3. ModifierArguments（产出类型和数值）
INSERT INTO ModifierArguments (ModifierId, Name, Value)
SELECT BoostModifier, 'YieldType', 'YIELD_GOLD' FROM Leu_CorporationResourceReqs;
INSERT INTO ModifierArguments (ModifierId, Name, Value)
SELECT BoostModifier, 'Amount', 5 FROM Leu_CorporationResourceReqs;

-- 4. RequirementSets
INSERT INTO RequirementSets (RequirementSetId, RequirementSetType)
SELECT AdjRequirementSet, 'REQUIREMENTSET_TEST_ALL' FROM Leu_CorporationResourceReqs;
INSERT INTO RequirementSets (RequirementSetId, RequirementSetType)
SELECT CorpRequirementSet, 'REQUIREMENTSET_TEST_ALL' FROM Leu_CorporationResourceReqs;

-- 5. Requirements（3 种类型）
-- Property 匹配
INSERT INTO Requirements (RequirementId, RequirementType)
SELECT PropertyRequirement, 'REQUIREMENT_PLOT_PROPERTY_MATCHES' FROM Leu_CorporationResourceReqs;
-- 地块改良类型匹配
INSERT INTO Requirements VALUES ('LEU_WAREHOUSE_CORPORATION_PLOT', 'REQUIREMENT_PLOT_IMPROVEMENT_TYPE_MATCHES');
-- 资源类型匹配
INSERT INTO Requirements (RequirementId, RequirementType)
SELECT ResourceRequirement, 'REQUIREMENT_PLOT_RESOURCE_TYPE_MATCHES' FROM Leu_CorporationResourceReqs;

-- 6. RequirementArguments
INSERT INTO RequirementArguments (RequirementId, Name, Value)
SELECT PropertyRequirement, 'PropertyName', ResourceProperty FROM Leu_CorporationResourceReqs;
INSERT INTO RequirementArguments (RequirementId, Name, Value)
SELECT PropertyRequirement, 'PropertyMinimum', 1 FROM Leu_CorporationResourceReqs;
INSERT INTO RequirementArguments (RequirementId, Name, Value)
SELECT ResourceRequirement, 'ResourceType', ResourceType FROM Leu_CorporationResourceReqs;
```

### 商路 Attach Modifier 模式
```sql
-- 自定义 DynamicModifier：将一个 Modifier 挂到满足条件的 Plots 上
INSERT INTO Types VALUES ('MODIFIER_LEU_MONOPOLY_PLOT_ATTACH_MODIFIER', 'KIND_MODIFIER');
INSERT INTO DynamicModifiers VALUES
('MODIFIER_LEU_MONOPOLY_PLOT_ATTACH_MODIFIER',
 'COLLECTION_ALL_PLOT_YIELDS', 'EFFECT_ATTACH_MODIFIER');

-- 批量生成 Attach Modifier
INSERT INTO Modifiers (ModifierId, ModifierType, OwnerRequirementSetId, SubjectRequirementSetId)
SELECT BoostModifier||'_TRADE_ROUTE', 'MODIFIER_LEU_MONOPOLY_PLOT_ATTACH_MODIFIER',
       AdjRequirementSet, CorpRequirementSet
FROM Leu_CorporationResourceReqs;

-- 参数：挂哪个 Modifier
INSERT INTO ModifierArguments (ModifierId, Name, Value)
SELECT BoostModifier||'_TRADE_ROUTE', 'ModifierId', 'CIVIC_GRANT_ONE_TRADE_ROUTE'
FROM Leu_CorporationResourceReqs;
```

## 行业/公司类别系统（CorporationsDiversity 2616754773）

`Database/database.sql`

### 定义资源类别表
```sql
-- 资源类别（手工艺/信仰/伟人点/贸易/食品/宜居度/奇观/旅游/渔业/娱乐/药材）
CREATE TABLE HDMonopolyResourceClasses (Category TEXT NOT NULL PRIMARY KEY);

-- 每个资源的效果映射
CREATE TABLE HDMonopolyResourceEffects (
    ResourceType      TEXT NOT NULL PRIMARY KEY,
    Category          TEXT NOT NULL,
    IndustryEffect    TEXT NOT NULL,  -- 行业效果ID
    CorporationEffect TEXT NOT NULL,  -- 公司效果ID
    ProductEffect     TEXT            -- 产品效果ID
);
```

### 行业 Modifier 表
```sql
CREATE TABLE HD_IndustryModifiers (
    Category   TEXT NOT NULL,
    ModifierId TEXT NOT NULL,
    PRIMARY KEY (Category, ModifierId)
);

-- 每个类别对应多个 Modifier
-- 例：GROWTH 类有 2 个 Modifier（粮食和人口粮食）
INSERT INTO HD_IndustryModifiers VALUES
('GROWTH', 'INDUSTRY_HD_GROWTH_BONUS_FOOD'),
('GROWTH', 'INDUSTRY_HD_GROWTH_BONUS_POP_FOOD');
```

### 批量生成 Attach 链
```sql
-- 1. 给行业改良贴上 Attach Modifier
INSERT INTO ImprovementModifiers (ImprovementType, ModifierId)
SELECT 'IMPROVEMENT_INDUSTRY', ModifierId || '_ATTACH' FROM HD_IndustryModifiers;

-- 2. Attach Modifier 的定义
INSERT INTO Modifiers (ModifierId, ModifierType, OwnerRequirementSetId)
SELECT ModifierId || '_ATTACH', 'MODIFIER_SINGLE_CITY_ATTACH_MODIFIER',
       'HD_' || Category || '_BONUS_REQUIREMENTS'
FROM HD_IndustryModifiers;

-- 3. Attach 的参数：指向真正的效果 Modifier
INSERT INTO ModifierArguments (ModifierId, Name, Value)
SELECT ModifierId || '_ATTACH', 'ModifierId', ModifierId FROM HD_IndustryModifiers;
```

效果链：
```
IMPROVEMENT_INDUSTRY
  → ATTACH_MODIFIER (OwnerRequirementSet: 城市拥有该类资源)
    → 真正的效果 Modifier (如 +粮食、+信仰)
```

### 旅游类公司批量生成
```sql
-- 为所有巨作类型生成公司旅游加成
INSERT INTO HD_CorporationModifiers (Category, ModifierId)
SELECT 'TOURISM', 'CORPORATION_HD_TOURISM_BONUS_' || GreatWorkObjectType
FROM GreatWorkObjectTypes;

-- 为所有工业区建筑生成公司加成
INSERT INTO HD_CorporationModifiers (Category, ModifierId)
SELECT 'TOURISM', 'CORPORATION_HD_TOURISM_BONUS_1_' || BuildingType
FROM Buildings WHERE PrereqDistrict = 'DISTRICT_INDUSTRIAL_ZONE'
  AND TraitType IS NULL AND Cost != 0;
```

### 首饰公司：为每种有旅游产出的改良设施生成旅游加成
```sql
INSERT INTO Modifiers (ModifierId, ModifierType, OwnerRequirementSetId)
SELECT 'CORPORATION_HD_COSMETICS_' || ImprovementType || '_TOURISM_BOOST',
       'MODIFIER_PLAYER_CITIES_ADJUST_TOURISM',
       'HD_RESOURCE_COSMETICS_IN_PLOT'
FROM Improvement_Tourism WHERE TourismSource IN ('TOURISMSOURCE_CULTURE','TOURISMSOURCE_PRODUCTION');

INSERT INTO ModifierArguments (ModifierId, Name, Value)
SELECT 'CORPORATION_HD_COSMETICS_' || ImprovementType || '_TOURISM_BOOST',
       'ImprovementType', ImprovementType
FROM Improvement_Tourism ...;
```

### 总督联动批量生成
`Core/MonopolyPlus_Units.sql`
```sql
-- 为所有 Tycoon/Investor 可建造的改良设施生成 Reyna 加成
INSERT INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId)
SELECT 'LEU_AUDIT_GOLD_'||ImprovementType, 'MODIFIER_PLAYER_ADJUST_PLOT_YIELD',
       'LEU_'||ImprovementType||'_WITHIN_6_TILES'
FROM Improvement_ValidBuildUnits WHERE UnitType = 'UNIT_LEU_TYCOON'
UNION ALL
SELECT ... FROM Improvement_ValidBuildUnits WHERE UnitType = 'UNIT_LEU_INVESTOR';
```

### 夏宫联动批量生成
`Database/database.sql`
```sql
-- 为每种行业资源类别生成夏宫附加 Modifier
INSERT INTO HD_ChateauResourceModifiers (ResourceType, IndustryModifierId)
SELECT ResourceType, ModifierId
FROM HDMonopolyResourceEffects m
INNER JOIN HD_IndustryModifiers i ON m.Category = i.Category
WHERE ResourceType IN (
    SELECT ResourceType FROM Improvement_ValidResources
    WHERE ImprovementType IN ('IMPROVEMENT_PLANTATION', 'IMPROVEMENT_FARM', 'IMPROVEMENT_LUMBER_MILL')
);
-- 然后生成两层 Attach 链：Chateau → Plantation → IndustryModifier
```

## XML 配合

本系统为纯 SQL 动态生成技术，无独立 UI 面板。所有效果通过 Modifier / Requirement / RequirementSet 数据库条目间接生效，无需 Lua 或 XML 端 UI 交互。

---

## 关键技术模式总结

### 动态 Attach 模式
```sql
-- 双层 Modifier：Attach Modifier + 效果 Modifier
-- Improvement → Attach (检查条件) → Effect (实际效果)
INSERT INTO Modifiers (..., ModifierType, OwnerRequirementSetId)
SELECT ..., 'MODIFIER_SINGLE_CITY_ATTACH_MODIFIER', ...
INSERT INTO ModifierArguments (..., Name, Value)
SELECT ..., 'ModifierId', <效果ModifierId>
```

### 命名约定
- 效果 Modifier: `PREFIX_CATEGORY_RESOURCE` 如 `INDUSTRY_HD_GROWTH_BONUS_FOOD`
- Attach Modifier: 效果ID + `_ATTACH`
- RequirementSet: `PREFIX_CATEGORY_RESOURCE_REQUIREMENTS`
- 条件 Requirement: `REQUIRES_PREFIX_CATEGORY_RESOURCE`

### 生产用临时表
- 创建临时映射表存储 ID 拼接
- 用 `INSERT ... SELECT ... || 拼接` 批量生成
- 处理完毕后可删除临时表
