# 垄断资源类别系统（来源：工坊 2616754773 CorporationsDiversity）

## 做什么
将垄断模式中所有奢侈资源按类别（增长/信仰/伟人点/贸易/食品/宜居度/奇观/旅游/渔业/娱乐/药材）分组，每种资源统一获得该类的行业/公司/产品效果，替代原版逐资源的单调效果。

## SQL 配合

### 核心数据表

`Database/early_setup.sql`

#### HDMonopolyResourceClasses — 资源类别表
```sql
CREATE TABLE HDMonopolyResourceClasses (
    Category TEXT NOT NULL PRIMARY KEY
);
-- 插入基础类别
INSERT INTO HDMonopolyResourceClasses (Category) VALUES
('GROWTH'), ('FAITH'), ('GPP'), ('TRADER'), ('FOOD'),
('AMENITY'), ('WONDER'), ('TOURISM'), ('FISHERY');
-- Resourceful2 模组新增
INSERT INTO HDMonopolyResourceClasses (Category)
SELECT 'ENTERTAINMENT' WHERE EXISTS (SELECT ResourceType FROM Resources WHERE ResourceType = 'RESOURCE_GRANITE');
INSERT INTO HDMonopolyResourceClasses (Category)
SELECT 'MEDICINE' WHERE EXISTS (SELECT ResourceType FROM Resources WHERE ResourceType = 'RESOURCE_GRANITE');
```

#### HDMonopolyResourceEffects — 资源效果映射表
```sql
CREATE TABLE HDMonopolyResourceEffects (
    ResourceType      TEXT NOT NULL PRIMARY KEY,
    Category          TEXT NOT NULL,
    IndustryEffect    TEXT NOT NULL,    -- 行业时使用的效果ID
    CorporationEffect TEXT NOT NULL,    -- 公司时使用的效果ID
    ProductEffect     TEXT,            -- 产品效果ID（可为NULL）
    FOREIGN KEY(ResourceType) REFERENCES Resources(ResourceType),
    FOREIGN KEY(Category) REFERENCES HDMonopolyResourceClasses(Category)
);
```

### 资源分类示例

`Database/database.sql` 中的分类逻辑：

| 类别 | 效果特征 | 代表资源 |
|------|----------|----------|
| GROWTH | 城市成长 | 香料、盐、糖、蜂蜜 |
| FAITH | 信仰 | 香、烟草、染料 |
| GPP | 伟人点 | 葡萄酒、可可、咖啡、茶 |
| TRADER | 贸易 | 丝绸、白银、黄金、钻石 |
| FOOD | 食物 | 柑橘、松露 |
| AMENITY | 宜居度(默认) | 棉花、皮毛、橄榄 |
| WONDER | 奇观 | 大理石、石膏、水银 |
| TOURISM | 旅游 | 象牙、翡翠、琥珀 |
| FISHERY | 渔业 | 龟、珍珠 |
| ENTERTAINMENT | 娱乐观赏 | 狼、虎、樱花(需要 Resourceful2) |
| MEDICINE | 药材 | 芦荟、藏红花(需要 Resourceful2) |

### 行业效果表

`Database/database.sql` 中创建 `HD_IndustryModifiers` 表：

```sql
CREATE TABLE HD_IndustryModifiers (
    Category   TEXT NOT NULL,
    ModifierId TEXT NOT NULL,
    PRIMARY KEY (Category, ModifierId)
);
```

每种 Category 对应多个 Modifier：

| Category | Modifier | 效果 |
|----------|----------|------|
| GROWTH | `...GROWTH_BONUS_FOOD` | 区域+1粮（MODIFIER_CITY_DISTRICTS_ADJUST_YIELD_CHANGE） |
| GROWTH | `...GROWTH_BONUS_POP_FOOD` | 每人口+0.5粮 |
| FAITH | `...FAITH_BONUS_FAITH` | 每人口+1信仰 |
| FAITH | `...FAITH_BONUS_GOLD` | 每人口+3金币 |
| GPP | `...GPP_BONUS_POP_SCIENCE` | 每人口+0.5科技 |
| GPP | `...GPP_BONUS_POP_CULTURE` | 每人口+0.5文化 |
| GPP | `...GPP_BONUS_POP_SCIENCE_N` | 有社区时每人口额外+0.5科技 |
| TRADER | `...TRADER_BONUS_CAPACITY` | +1商路容量 |
| TRADER | `...TRADER_BONUS_COMMERCIAL` | 商业中心+100%金币 |
| TRADER | `...TRADER_BONUS_HARBOR` | 港口+100%金币 |
| FOOD | `...FOOD_BONUS_FOOD` | 城市+10%粮食 |
| FOOD | `...FOOD_BONUS_GOLD` | 城市+10%金币 |
| AMENITY | `...AMENITY_BONUS_PRODUCTION` | 区域+1锤 |
| AMENITY | `...AMENITY_BONUS_POP_PRODUCTION` | 每人口+0.5锤 |
| WONDER | `...WONDER_BONUS` | +20%奇观生产力 |
| WONDER | `...WONDER_BONUS_DISTRICT` | 工业区+100%锤 |
| TOURISM | `...TOURISM_BONUS_CULTURE` | 区域+1文化 |
| TOURISM | `...TOURISM_BONUS_GOLD` | 区域+3金币 |
| FISHERY | `...FISHERY_BONUS` | 渔船+3金币 |
| FISHERY | `...FISHERY_BONUS_FOOD` | 渔船+1粮食 |
| FISHERY | `...FISHERY_BONUS_PROD` | 渔船+1锤 |
| MEDICINE | `...MEDICINE_BONUS_SCIENCE` | 每人口+科学 |
| MEDICINE | `...MEDICINE_BONUS_FAITH` | 每人口+信仰 |

另外每个 Category 还有一个 SET_PROPERTY Modifier：
```sql
-- 在拥有行业的城市上设置 Plot Property
INSERT INTO Modifiers (ModifierId, ModifierType)
SELECT 'INDUSTRY_HD_' || Category || '_SET_PROPERTY',
       'MODIFIER_SINGLE_CITY_ADJUST_PROPERTY'
FROM HDMonopolyResourceClasses;
-- Args: Key='HD_CITY_HAS_<Category>_INDUSTRY', Amount=1
```
用于鲁尔山谷等地块检测"城市有某类行业"。

### 公司效果表

`HD_CorporationModifiers` 表（与 Industry 类似结构）：

| Category | Modifier | 效果 |
|----------|----------|------|
| GROWTH | `...GROWTH_BONUS` | +20%城市成长 |
| GROWTH | `...GROWTH_BONUS_TRADE_FOOD` | 国内商路+4粮 |
| FAITH | `...FAITH_BONUS_HOLY_SITE` | 圣地+100%信仰 |
| FAITH | `...FAITH_BONUS_TRADE_ROUTE` | 商路+4信仰 |
| GPP | `...GPP_BONUS` | 政府区+50%伟人点 |
| TRADER | `...TRADER_BONUS` | 商路+6金币 |
| TRADER | `...TRADER_BONUS_GOLD` | 城市+10%金币 |
| TRADER | `...TRADER_BONUS_GPP` | +50%大商人点 |
| FOOD | `...FOOD_BONUS_DISTRICT_FOOD` | 沿河/沿海区域+1粮 |
| FOOD | `...FOOD_BONUS_DISTRICT_GOLD` | 沿河/沿海区域+3金 |
| AMENITY | `...AMENITY_BONUS_EXTRA_AMENITY1` | 娱乐区+1宜居 |
| AMENITY | `...AMENITY_BONUS_EXTRA_AMENITY2` | 水上乐园+1宜居 |
| AMENITY | `...AMENITY_BONUS_TRADE_PRODUCTION` | 国内商路+4锤 |
| WONDER | `...WONDER_BONUS` | +10%建筑生产力 |
| WONDER | `...WONDER_BONUS_DISTRICT` | +10%区域生产力 |
| WONDER | `...WONDER_BONUS_GPP` | +50%大工程师点 |
| FISHERY | `...FISHERY_BONUS` | 渔船+1粮+1锤 |
| FISHERY | `...FISHERY_BONUS_AMENITY3` | 有港口3级建筑时+2宜居 |
| TOURISM | 多条目 | 每种巨作类型旅游加成 |
| TOURISM | 多条目 | 每种工业区建筑+2文化/+6金币 |
| ENTERTAINMENT | 多条目 | 每种改良设施+旅游,每个国家公园+旅游,每个区域+伟人点 |
| MEDICINE | 多条目 | 每种学院建筑产出加成 |

### 垄断百分比调整
```sql
UPDATE GlobalParameters SET Value = 201
WHERE Name IN ('MONOPOLY_REQUIRED_RESOURCE_CONTROL_PERCENTAGE',
               'MONOPOLY_REQUIRED_RESOURCE_CONTROL_PERCENTAGE_MED',
               'MONOPOLY_REQUIRED_RESOURCE_CONTROL_PERCENTAGE_MAX');
```
将垄断所需资源百分比改为 201%（实际上无法触发，意味着移除了原版垄断机制，完全由自定义系统承担）。

### 行业/公司改良产出提升
```sql
-- 行业改良基础产出提升
UPDATE Improvement_YieldChanges SET YieldChange = 5  WHERE ImprovementType = 'IMPROVEMENT_INDUSTRY' AND YieldType = 'YIELD_FOOD';
UPDATE Improvement_YieldChanges SET YieldChange = 6  WHERE ImprovementType = 'IMPROVEMENT_INDUSTRY' AND YieldType = 'YIELD_PRODUCTION';
UPDATE Improvement_YieldChanges SET YieldChange = 6  WHERE ImprovementType = 'IMPROVEMENT_INDUSTRY' AND YieldType = 'YIELD_GOLD';
-- 公司改良基础产出
UPDATE Improvement_YieldChanges SET YieldChange = 6  WHERE ImprovementType = 'IMPROVEMENT_CORPORATION' AND YieldType = 'YIELD_FOOD';
UPDATE Improvement_YieldChanges SET YieldChange = 8  WHERE ImprovementType = 'IMPROVEMENT_CORPORATION' AND YieldType = 'YIELD_PRODUCTION';
UPDATE Improvement_YieldChanges SET YieldChange = 8  WHERE ImprovementType = 'IMPROVEMENT_CORPORATION' AND YieldType = 'YIELD_GOLD';
```

### 清理原版效果
```sql
-- 删除原版行业/公司效果
DELETE FROM ImprovementModifiers WHERE ImprovementType = 'IMPROVEMENT_INDUSTRY' AND ModifierID LIKE 'INDUSTRY_%';
DELETE FROM ImprovementModifiers WHERE ImprovementType = 'IMPROVEMENT_CORPORATION' AND ModifierID LIKE 'CORPORATION_%';
-- 删除原版资源行业/公司记录
DELETE FROM ResourceIndustries;
DELETE FROM ResourceCorporations;
-- 用自定义效果重新填充
INSERT INTO ResourceIndustries (ResourceType, ResourceEffect, ResourceEffectTExt)
SELECT ResourceType, IndustryEffect, 'LOC_'||IndustryEffect||'_DESCRIPTION'
FROM HDMonopolyResourceEffects;
INSERT INTO ResourceCorporations (ResourceType, ResourceEffect, ResourceEffectTExt)
SELECT ResourceType, CorporationEffect, 'LOC_'||CorporationEffect||'_DESCRIPTION'
FROM HDMonopolyResourceEffects;
```

## Lua 端
此系统纯 SQL 实现，无独立 Lua。

## XML 配合
无独立 XML。
