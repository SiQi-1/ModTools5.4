# 投资者/大亨经济单位系统（来源：工坊 2479197624 MonopolyPlus）

## 做什么
用两种新的经济民用单位（投资者 Investor / 大亨 Tycoon）**替代建造者**来建造垄断相关的改良设施（行业、公司、仓库、车站等）。
通过自定义 Ability + DynamicModifier 禁止这些单位进行建造者的常规操作（砍树、收资源、移除地貌等）。

## SQL 配合

### 单位定义
`Core/MonopolyPlus_Units.sql`

| 属性 | Investor (投资者) | Tycoon (大亨) |
|------|------------------|---------------|
| `UnitType` | `UNIT_LEU_INVESTOR` | `UNIT_LEU_TYCOON` |
| `PrereqTech` | `TECH_ECONOMICS` | `TECH_PRINTING` |
| `Cost` | 400 | 250 |
| `CostProgressionParam1` | 50 | 35 |
| `BuildCharges` | 1 | 1 |
| `MustPurchase` | 1 (只能金币购买) | 1 |
| `PurchaseYield` | `YIELD_GOLD` | `YIELD_GOLD` |
| `FormationClass` | `FORMATION_CLASS_CIVILIAN` | `FORMATION_CLASS_CIVILIAN` |
| `Domain` | `DOMAIN_LAND` | `DOMAIN_LAND` |
| `PseudoYieldType` | `PSEUDOYIELD_RESOURCE_LUXURY` | `PSEUDOYIELD_RESOURCE_LUXURY` |
| `CanCapture` | 1 | 1 |
| `Maintenance` | 0 | 0 |

### 前置建筑
```sql
-- 投资者需要银行
INSERT INTO Unit_BuildingPrereqs VALUES ('UNIT_LEU_INVESTOR', 'BUILDING_BANK');
-- + 所有银行替代建筑（UB）

-- 兼容 JNR 模组额外前置
INSERT INTO Unit_BuildingPrereqs
SELECT 'UNIT_LEU_INVESTOR', BuildingType FROM Buildings
WHERE BuildingType IN ('BUILDING_JNR_GUILDHALL', 'BUILDING_JNR_MERCHANT_QUARTER');

INSERT INTO Unit_BuildingPrereqs
SELECT 'UNIT_LEU_TYCOON', BuildingType FROM Buildings
WHERE BuildingType = 'BUILDING_JNR_MANUFACTURY';
```

### 建造权限（Improvement_ValidBuildUnits）
```sql
-- 投资者可建造
('IMPROVEMENT_LEU_WAREHOUSE',       'UNIT_LEU_INVESTOR')
('IMPROVEMENT_LEU_CONTAINER_PORT',  'UNIT_LEU_INVESTOR')
('IMPROVEMENT_LEU_TRANSNATIONAL',   'UNIT_LEU_INVESTOR')
('IMPROVEMENT_LEU_TRANSNATIONAL_SEA','UNIT_LEU_INVESTOR')
-- 大亨可建造
('IMPROVEMENT_CORPORATION',   'UNIT_LEU_TYCOON')
('IMPROVEMENT_INDUSTRY',      'UNIT_LEU_TYCOON')
('IMPROVEMENT_LEU_STATION',   'UNIT_LEU_TYCOON')
('IMPROVEMENT_BEACH_RESORT',  'UNIT_LEU_TYCOON')
('IMPROVEMENT_SKI_RESORT',    'UNIT_LEU_TYCOON')
```

**关键清理**：移除建造者对行业/公司的建造权限，并移除建造者对海滩/滑雪胜地的建造权限。
```sql
DELETE FROM Improvement_ValidBuildUnits
WHERE ImprovementType = 'IMPROVEMENT_INDUSTRY';
DELETE FROM Improvement_ValidBuildUnits
WHERE ImprovementType = 'IMPROVEMENT_CORPORATION';
DELETE FROM Improvement_ValidBuildUnits
WHERE UnitType = 'UNIT_BUILDER' AND ImprovementType IN ('IMPROVEMENT_BEACH_RESORT','IMPROVEMENT_SKI_RESORT');
```

### 类型标签
```sql
INSERT INTO Tags VALUES ('CLASS_MONOPOLY_UNIT', 'ABILITY_CLASS');
INSERT INTO TypeTags VALUES ('UNIT_LEU_INVESTOR', 'CLASS_MONOPOLY_UNIT');
INSERT INTO TypeTags VALUES ('UNIT_LEU_TYCOON',   'CLASS_MONOPOLY_UNIT');
```

### 单位属性
```sql
-- 可传送至城市
INSERT INTO TypeProperties VALUES ('UNIT_LEU_INVESTOR', 'CAN_TELEPORT_TO_CITY', 1, 'PROPERTYTYPE_IDENTITY');
INSERT INTO TypeProperties VALUES ('UNIT_LEU_TYCOON',   'CAN_TELEPORT_TO_CITY', 1, 'PROPERTYTYPE_IDENTITY');
-- 生命周期 40 回合
INSERT INTO TypeProperties VALUES ('UNIT_LEU_INVESTOR', 'LIFESPAN', 40, 'PROPERTYTYPE_IDENTITY');
INSERT INTO TypeProperties VALUES ('UNIT_LEU_TYCOON',   'LIFESPAN', 40, 'PROPERTYTYPE_IDENTITY');
```

### AI 支持
```sql
INSERT INTO UnitAiInfos VALUES ('UNIT_LEU_INVESTOR', 'UNITAI_BUILD');
INSERT INTO UnitAiInfos VALUES ('UNIT_LEU_TYCOON',   'UNITAI_BUILD');
```

### 禁止建造者操作（DynamicModifier 系统）
自定义 Modifier 用于按操作类型禁用单位能力：

```sql
-- 定义新 ModifierType
INSERT INTO Types VALUES ('MODIFIER_LEU_CHANGE_UNIT_OPERATION_AVAILABILITY', 'KIND_MODIFIER');
INSERT INTO DynamicModifiers VALUES
('MODIFIER_LEU_CHANGE_UNIT_OPERATION_AVAILABILITY',
 'COLLECTION_OWNER',
 'EFFECT_CHANGE_UNIT_OPERATION_AVAILABILITY');
-- 参数：Available (Bool), OperationType
```

#### 禁用的操作
```sql
-- 对所有 CLASS_MONOPOLY_UNIT 单位
ABILITY_LEU_NO_BUILDER_OPERATIONS:
  禁用 UNITOPERATION_PLANT_FOREST
  禁用 UNITOPERATION_CLEAR_CONTAMINATION
  禁用 UNITOPERATION_HARVEST_RESOURCE
  禁用 UNITOPERATION_REMOVE_FEATURE
  禁用 UNITOPERATION_REMOVE_IMPROVEMENT

-- 仅对 CLASS_INVESTOR 单位（额外）
ABILITY_LEU_NO_INVESTOR_LOCAL_IMPROVEMENTS:
  禁用 UNITOPERATION_BUILD_IMPROVEMENT
  -- 但有条件：仅在 'INVESTOR_IS_OWNED_UNIMPROVED' RequirementSet 满足时生效
  -- 该条件 = 在自己领土内 + 格位无改良 + 格位有资源
```

#### 关键代码模式
```sql
-- 动态生成能力标签关联
INSERT INTO TypeTags
SELECT 'ABILITY_LEU_NO_BUILDER_OPERATIONS', 'CLASS_MONOPOLY_UNIT';

-- Ability → Modifier 的桥接
INSERT INTO UnitAbilityModifiers VALUES
('ABILITY_LEU_NO_BUILDER_OPERATIONS', 'LEU_DISABLE_PLANT_FOREST');

-- Modifier 参数化禁用
INSERT INTO ModifierArguments VALUES
('LEU_DISABLE_PLANT_FOREST', 'OperationType', 'UNITOPERATION_PLANT_FOREST'),
('LEU_DISABLE_PLANT_FOREST', 'Available', 0);
```

### 伟人联动
`Core/MonopolyPlus_GreatPeople.sql`

两个新伟人（Andrew Carnegie / John Keynes）提供充能加成：
```sql
-- Andrew Carnegie (工业时代大商人): Tycoon +1 充能, 送1个免费 Tycoon
-- John Keynes (原子能时代大商人): Investor +1 充能, 送1个免费 Investor

-- 使用 MODIFIER_PLAYER_UNITS_ADJUST_BUILDER_CHARGES
-- NewOnly=1 只影响新生产的单位
-- SubjectRequirementSet=LEU_UNIT_IS_TYCOON/LEU_UNIT_IS_INVESTOR
```

### 总督联动（Reyna）
修改 Reyna 的 Tax Collector 技能：
- 投资者/大亨购买费用 **-10%**（`MODIFIER_SINGLE_CITY_ADJUST_UNIT_PURCHASE_COST`）
- Tycoon/Investor 建造的改良设施在 Reyna 6 格范围内 +4 金币

### 铁路建造
```sql
INSERT INTO Route_ValidBuildUnits VALUES ('ROUTE_RAILROAD', 'UNIT_LEU_TYCOON');
```
大亨可建造铁路（与军事工程师相同能力）。

### 修改科技
```sql
-- 移除 CURRENCY 科技原版描述（因为被修改）
UPDATE Technologies SET Description = null WHERE TechnologyType = 'TECH_CURRENCY';
-- 伟大商人建造次数归零
UPDATE Units SET BuildCharges = 0 WHERE UnitType = 'UNIT_GREAT_MERCHANT';
```

## Lua 端
此系统纯 SQL 实现，无独立 Lua。

## XML 配合
`Core/MonopolyPlus_Icons.sql` — 图标注册
`Text/MonopolyPlust_UnitTexts.sql` — 文本定义
