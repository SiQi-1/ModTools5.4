# 车站与国内贸易系统（来源：工坊 2479197624 MonopolyPlus）

## 做什么
新增车站改良设施，提供**国内贸易路线**的加成产出（向其他城市发送/从其他城市接收）。
通过 `MODIFIER_SINGLE_CITY_ADJUST_TRADE_ROUTE_YIELD_TO_OTHERS` 和 `MODIFIER_SINGLE_CITY_ADJUST_TRADE_ROUTE_YIELD_FOR_DOMESTIC` 实现国内贸易双向收益。

车站也自动铺设铁路、增加城市电力需求，体现工业化特征。

## SQL 配合

### 改良设施定义
`Core/MonopolyPlus_Improvements.sql` / `Core/MonopolyPlus_Tycoons.sql`

| 字段 | 值 |
|------|-----|
| `ImprovementType` | `IMPROVEMENT_LEU_STATION` |
| `PrereqTech` | `TECH_STEAM_POWER` |
| `Domain` | `DOMAIN_LAND` |
| `OnePerCity` | 1 |
| `Workable` | 1 |
| `Appeal` | 1 |
| `YieldFromAppeal` | `YIELD_PRODUCTION` |
| `YieldFromAppealPercent` | 75 |
| `PlunderType` | `PLUNDER_GOLD` (50) |
| `Capturable` | 1 |
| `Removable` | 1 |

### 基础产出
```sql
-- 基础产出为 0（实际效果靠 modifier）
INSERT INTO Improvement_YieldChanges VALUES
('IMPROVEMENT_LEU_STATION', 'YIELD_CULTURE',    0),
('IMPROVEMENT_LEU_STATION', 'YIELD_PRODUCTION', 0);
```

### 旅游业绩
```sql
INSERT INTO Improvement_Tourism VALUES
('IMPROVEMENT_LEU_STATION', 'TOURISMSOURCE_PRODUCTION', 'TECH_STEEL', 100);
```

### 相邻加成
车站提供和获取多种相邻加成：

```sql
-- 车站自身提供的加成（给其他东西）
INSERT INTO Adjacency_YieldChanges VALUES
('Station_Production',              'YIELD_PRODUCTION', 2, AdjacentImprovement='IMPROVEMENT_LEU_STATION'),
('Station_Production_From_Districts','YIELD_PRODUCTION', 1, OtherDistrictAdjacent=1),
('Station_Culture_From_Wonder',     'YIELD_CULTURE',    2, AdjacentWonder=1, PrereqTech='TECH_STEEL'),
('Station_Production_From_Wonder',  'YIELD_PRODUCTION', 1, AdjacentWonder=1);

-- 工业区获得车站加成
INSERT INTO District_Adjacencies VALUES ('DISTRICT_INDUSTRIAL_ZONE', 'Station_Production');
-- 所有工业区UB也获得
INSERT INTO District_Adjacencies
SELECT CivUniqueDistrictType, 'Station_Production'
FROM DistrictReplaces WHERE ReplacesDistrictType = 'DISTRICT_INDUSTRIAL_ZONE';

-- 车站自身获得加成
INSERT INTO Improvement_Adjacencies VALUES
('IMPROVEMENT_LEU_STATION', 'Station_Production_From_Districts'),
('IMPROVEMENT_LEU_STATION', 'Station_Culture_From_Wonder'),
('IMPROVEMENT_LEU_STATION', 'Station_Production_From_Wonder');
```

在 CorporationsDiversity 版本中还有更多相邻加成：
```sql
-- 车站相邻行业 +2锤
('Station_Production_From_Industry',    'YIELD_PRODUCTION', 2, AdjacentImprovement='IMPROVEMENT_INDUSTRY')
-- 车站相邻公司 +2锤
('Station_Production_From_Corporation', 'YIELD_PRODUCTION', 2, AdjacentImprovement='IMPROVEMENT_CORPORATION')
```

### 国内贸易加成（核心机制）

每个车站配 16 个 Modifier（4种产出 x 2方向 x 2供电状态）：

#### 未供电时
| Modifier | ModifierType | 效果 |
|----------|-------------|------|
| `..._TO_OTHERS` | `MODIFIER_SINGLE_CITY_ADJUST_TRADE_ROUTE_YIELD_TO_OTHERS` | 国内商路**发给**其他城市 +产出 |
| `..._FROM_OTHERS` | `MODIFIER_SINGLE_CITY_ADJUST_TRADE_ROUTE_YIELD_FOR_DOMESTIC` | 从其他城市**接收**国内商路 +产出 |

参数（以生产力为例）：
```sql
-- TO_OTHERS: Domestic=1, YieldType='YIELD_PRODUCTION', Amount=4
-- FROM_OTHERS: YieldType='YIELD_PRODUCTION', Amount=4
```

#### 四种产出方向
| 产出 | TO_OTHERS (发) | FROM_OTHERS (收) |
|------|---------------|-----------------|
| 生产力 | 4 | 4 |
| 文化 | 2 | 2 |
| 食物 | 2 | 2 |
| 金币 | 4 | 4 |

#### 供电后（SubjectRequirementSet = `CITY_IS_POWERED`）
数量减半但额外叠加：
| 产出 | TO_OTHERS | FROM_OTHERS |
|------|-----------|-------------|
| 生产力 | 2 | 2 |
| 文化 | 1 | 1 |
| 食物 | 1 | 1 |
| 金币 | 2 | 2 |

### 电力消耗
```sql
INSERT INTO Modifiers VALUES
('LEU_STATION_REQUIRED_POWER', 'MODIFIER_SINGLE_CITY_ADJUST_REQUIRED_POWER', null, null);
-- Args: Amount=2
```
车站使城市**额外需要 2 电力**。

### 铁路铺设
```sql
INSERT INTO Modifiers VALUES
('LEU_STATION_GRANT_ROUTE_IN_RADIUS', 'MODIFIER_GRANT_ROUTE_IN_RADIUS', null, null);
-- Args: RouteType='ROUTE_RAILROAD', Radius=1
```
车站自动在周围 1 格范围内铺设铁路。

### 建造者
```sql
INSERT INTO Improvement_ValidBuildUnits VALUES
('IMPROVEMENT_LEU_STATION', 'UNIT_LEU_TYCOON');
```
只能由大亨建造。

### 地形限制
可建在草原、平原、沙漠、冻土、雪地以及以下地貌：
- 泛滥平原、丛林、森林、火山土

## Lua 端
此系统纯 SQL 实现，无独立 Lua。

## XML 配合
无独立 XML。
