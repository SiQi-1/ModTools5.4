# 相邻加成 — Adjacency_YieldChanges

## 适用范围

区域相邻加成和改良相邻加成**共用此表**。唯一区别是 Description 写法不同。

## 涉及的表

| 表 | 说明 |
|------|------|
| District_Adjacencies | 区域→规则的桥接表 |
| Adjacency_YieldChanges | 核心定义表（20 列） |

> 改良的桥接表为用户自定义（`Siqi_Core_Improvement_Adjacency` 等），不在此 skill 范围。

---

## 一、District_Adjacencies

纯桥接表，一个区域可绑定多条加成规则。

| 列名 | 说明 |
|------|------|
| DistrictType | 区域 Type（区域枚举见 [DistrictType 查询依据](SOURCES.md#类型与枚举)） |
| YieldChangeId | 规则 ID，引用 Adjacency_YieldChanges.ID |

### INSERT 模板

```sql
INSERT INTO District_Adjacencies (DistrictType, YieldChangeId) VALUES
('DISTRICT_SIQI_{SHORT}', 'Siqi_{SHORT}_Science_Mountain'),
('DISTRICT_SIQI_{SHORT}', 'Siqi_{SHORT}_Science_District');
```

多条规则写多行，每条规则一个条件。

---

## 二、Adjacency_YieldChanges

### 表结构（20 列）

| # | 列名 | 类型 | 约束 | 写不写 | 说明 |
|---|------|------|------|--------|------|
| 0 | ID | TEXT | NOT NULL | **必写** | 规则唯一标识 |
| 1 | Description | TEXT | NOT NULL | **必写** | 显示文本，区域/改良写法不同（见下方） |
| 2 | YieldType | TEXT | NOT NULL | **必写** | 产出类型 |
| 3 | YieldChange | INTEGER | NOT NULL, default=0 | **必写** | 每满足 TilesRequired 个条件时的加成量 |
| 4 | TilesRequired | INTEGER | NOT NULL, default=1 | **必写** | 每 N 个相邻格触发 1 次加成。标准 1（每格 1 次），填 2 = 每 2 格 +1 |
| 5 | OtherDistrictAdjacent | BOOLEAN | NOT NULL, default=0 | 条件 | 邻接任意区域（有产出加成的区域也算） |
| 6 | AdjacentSeaResource | BOOLEAN | NOT NULL, default=0 | 条件 | 邻接海洋资源 |
| 7 | AdjacentTerrain | TEXT | 可空 | 条件 | 邻接特定地形。见 [TerrainType 查询依据](SOURCES.md#类型与枚举) |
| 8 | AdjacentFeature | TEXT | 可空 | 条件 | 邻接特定地貌。见 [FeatureType 查询依据](SOURCES.md#类型与枚举) |
| 9 | AdjacentRiver | BOOLEAN | NOT NULL, default=0 | 条件 | 临河 |
| 10 | AdjacentWonder | BOOLEAN | NOT NULL, default=0 | 条件 | 邻接奇观（人造） |
| 11 | AdjacentNaturalWonder | BOOLEAN | NOT NULL, default=0 | 条件 | 邻接自然奇观 |
| 12 | AdjacentImprovement | TEXT | 可空 | 条件 | 邻接特定改良设施 |
| 13 | AdjacentDistrict | TEXT | 可空 | 条件 | 邻接特定区域。见 [DistrictType 查询依据](SOURCES.md#类型与枚举) |
| 14 | PrereqCivic | TEXT | 可空 | 条件 | 解锁此加成的市政 |
| 15 | PrereqTech | TEXT | 可空 | 条件 | 解锁此加成的科技 |
| 16 | ObsoleteCivic | TEXT | 可空 | 可选 | 某市政后失效（一般不用） |
| 17 | ObsoleteTech | TEXT | 可空 | 可选 | 某科技后失效（一般不用） |
| 18 | AdjacentResource | BOOLEAN | NOT NULL, default=0 | 条件 | 邻接任意资源 |
| 19 | AdjacentResourceClass | TEXT | NOT NULL, default="NO_RESOURCECLASS" | 条件 | 按资源分类筛选。`NO_RESOURCECLASS`(默认)/`RESOURCECLASS_BONUS`/`RESOURCECLASS_LUXURY`/`RESOURCECLASS_STRATEGIC` |
| — | Self | BOOLEAN | NOT NULL, default=0 | 条件 | 邻接同类型区域/改良（如学院邻接学院） |

### 核心规则

- **一个规则只设一个条件**（列 5-19 选一，其余不写或用默认值）
- 条件列之间是互斥的，不要一条规则同时设多个条件
- 多个条件 → 写多条规则
- 有 PrereqCivic/PrereqTech 时 Description 追加说明，Obsolete 一般不用

### 常用条件组合速查

| 场景 | 设哪些列 |
|------|---------|
| 山脉 +1 | AdjacentTerrain = 五种 MOUNTAIN（各写一条） |
| 相邻区域 +1 | OtherDistrictAdjacent = 1 |
| 相邻特定区域 +2 | AdjacentDistrict = DISTRICT_XXX |
| 森林 +1（每2格） | AdjacentFeature = FEATURE_FOREST, TilesRequired = 2 |
| 河流 +2 | AdjacentRiver = 1, YieldChange = 2 |
| 自然奇观 +2 | AdjacentNaturalWonder = 1 |
| 海洋资源 +1 | AdjacentSeaResource = 1 |
| 同类相邻 | Self = 1 |
| 战略资源 +1 | AdjacentResourceClass = RESOURCECLASS_STRATEGIC |

---

## 三、Description 格式

### 区域用法（LOC_ 键）

```sql
-- Description 填 LOC_ 键，文本统一在 Text/ 文件中定义
'LOC_DISTRICT_SIQI_{SHORT}_MOUNTAIN_SCIENCE'
```

Text 文件中的文本格式：
```
{解锁条件} +{1_Amount}[ICON_Science]科技值 来自相邻的 {条件名称}。
```

示例：
```
+{1_Amount}[ICON_Science]科技值 来自相邻的 山脉。（解锁前置科技/市政）

+{1_Amount}[ICON_Faith]信仰值 来自相邻的 自然奇观。
```

### 改良用法（占位符直写）

```sql
-- Description 直接填 'Placeholder' 或带 {1_Amount} 的格式串
'Placeholder'
-- 或
'+{1_Amount}[ICON_Food]{LOC_YIELD_FOOD_NAME}'
```

- `{1_Amount}`：运行时替换为产量数值
- `[ICON_xxx]`：嵌游戏图标
- `{LOC_YIELD_XXX_NAME}`：引用产出名 LOC 键

> 代码规范：数值占位符用 `{1_Amount}`，不用 `{1_num}`。

---

## 四、INSERT 模板

### 区域相邻加成（标准流程）

```sql
-- 1. 定义加成规则
INSERT INTO Adjacency_YieldChanges (ID, Description, YieldType, YieldChange, TilesRequired, AdjacentTerrain) VALUES
('Siqi_{SHORT}_Science_Mountain1', 'LOC_DISTRICT_SIQI_{SHORT}_MOUNTAIN_SCIENCE1', 'YIELD_SCIENCE', 1, 1, 'TERRAIN_GRASS_MOUNTAIN'),
('Siqi_{SHORT}_Science_Mountain2', 'LOC_DISTRICT_SIQI_{SHORT}_MOUNTAIN_SCIENCE2', 'YIELD_SCIENCE', 1, 1, 'TERRAIN_PLAINS_MOUNTAIN');

-- 2. 绑定到区域
INSERT INTO District_Adjacencies (DistrictType, YieldChangeId) VALUES
('DISTRICT_SIQI_{SHORT}', 'Siqi_{SHORT}_Science_Mountain1'),
('DISTRICT_SIQI_{SHORT}', 'Siqi_{SHORT}_Science_Mountain2');
```

### 山脉加成的标准写法（5 条山脉 × N 个产出）

```sql
-- 每种山脉地形各写一条
INSERT INTO Adjacency_YieldChanges (ID, Description, YieldType, YieldChange, TilesRequired, AdjacentTerrain) VALUES
('Siqi_{SHORT}_Science_M1', 'LOC_DISTRICT_SIQI_{SHORT}_MOUNTAIN_SCIENCE', 'YIELD_SCIENCE', 1, 1, 'TERRAIN_GRASS_MOUNTAIN'),
('Siqi_{SHORT}_Science_M2', 'LOC_DISTRICT_SIQI_{SHORT}_MOUNTAIN_SCIENCE', 'YIELD_SCIENCE', 1, 1, 'TERRAIN_PLAINS_MOUNTAIN'),
('Siqi_{SHORT}_Science_M3', 'LOC_DISTRICT_SIQI_{SHORT}_MOUNTAIN_SCIENCE', 'YIELD_SCIENCE', 1, 1, 'TERRAIN_DESERT_MOUNTAIN'),
('Siqi_{SHORT}_Science_M4', 'LOC_DISTRICT_SIQI_{SHORT}_MOUNTAIN_SCIENCE', 'YIELD_SCIENCE', 1, 1, 'TERRAIN_TUNDRA_MOUNTAIN'),
('Siqi_{SHORT}_Science_M5', 'LOC_DISTRICT_SIQI_{SHORT}_MOUNTAIN_SCIENCE', 'YIELD_SCIENCE', 1, 1, 'TERRAIN_SNOW_MOUNTAIN');

INSERT INTO District_Adjacencies (DistrictType, YieldChangeId) VALUES
('DISTRICT_SIQI_{SHORT}', 'Siqi_{SHORT}_Science_M1'),
('DISTRICT_SIQI_{SHORT}', 'Siqi_{SHORT}_Science_M2'),
('DISTRICT_SIQI_{SHORT}', 'Siqi_{SHORT}_Science_M3'),
('DISTRICT_SIQI_{SHORT}', 'Siqi_{SHORT}_Science_M4'),
('DISTRICT_SIQI_{SHORT}', 'Siqi_{SHORT}_Science_M5');
```

### 改良相邻加成（Placeholder 写法）

```sql
INSERT INTO Adjacency_YieldChanges (ID, Description, YieldType, YieldChange, TilesRequired, AdjacentDistrict) VALUES
('Siqi_{SHORT}_Imp_Gold_District', 'Placeholder', 'YIELD_GOLD', 2, 1, 'DISTRICT_COMMERCIAL_HUB');
```

### 反向相邻加成 — 为相邻区域提供加成

定义规则时 `AdjacentDistrict` 指向自己的区域，再通过 `District_Adjacencies` 绑定到**标准区域**。

**力度等级：**

| 等级 | TilesRequired | YieldChange | 示例 |
|------|---------------|-------------|------|
| 少量 | 2 | 1 | 每 2 个邻格 +1 |
| 标准 | 1 | 1 | 每 1 个邻格 +1 |
| 大量 | 1 | 2 | 每 1 个邻格 +2 |

> 注意没有小数，全部整数。

**INSERT 模板：**

```sql
-- 1. 定义规则：AdjacentDistrict 指向自己的区域
INSERT INTO Adjacency_YieldChanges (ID, Description, YieldType, YieldChange, TilesRequired, AdjacentDistrict) VALUES
('Siqi_{SHORT}_Science',    'LOC_DISTRICT_SIQI_{SHORT}_ADJACENCY_SCIENCE',    'YIELD_SCIENCE',    1, 1, 'DISTRICT_SIQI_{SHORT}'),
('Siqi_{SHORT}_Production', 'LOC_DISTRICT_SIQI_{SHORT}_ADJACENCY_PRODUCTION', 'YIELD_PRODUCTION', 1, 1, 'DISTRICT_SIQI_{SHORT}'),
('Siqi_{SHORT}_Gold',       'LOC_DISTRICT_SIQI_{SHORT}_ADJACENCY_GOLD',       'YIELD_GOLD',       2, 1, 'DISTRICT_SIQI_{SHORT}'),
('Siqi_{SHORT}_Food',       'LOC_DISTRICT_SIQI_{SHORT}_ADJACENCY_FOOD',       'YIELD_FOOD',       1, 1, 'DISTRICT_SIQI_{SHORT}'),
('Siqi_{SHORT}_Culture',    'LOC_DISTRICT_SIQI_{SHORT}_ADJACENCY_CULTURE',    'YIELD_CULTURE',    1, 1, 'DISTRICT_SIQI_{SHORT}'),
('Siqi_{SHORT}_Faith',      'LOC_DISTRICT_SIQI_{SHORT}_ADJACENCY_FAITH',      'YIELD_FAITH',      1, 1, 'DISTRICT_SIQI_{SHORT}');

-- 2. 绑定到标准区域（每种产出匹配对应该产出的标准区域）
INSERT INTO District_Adjacencies (DistrictType, YieldChangeId) VALUES
('DISTRICT_CAMPUS',          'Siqi_{SHORT}_Science'),
('DISTRICT_COMMERCIAL_HUB',  'Siqi_{SHORT}_Gold'),
('DISTRICT_HARBOR',          'Siqi_{SHORT}_Gold'),
('DISTRICT_THEATER',         'Siqi_{SHORT}_Culture'),
('DISTRICT_INDUSTRIAL_ZONE', 'Siqi_{SHORT}_Production'),
('DISTRICT_HOLY_SITE',       'Siqi_{SHORT}_Faith');
```

> Food 无对应的标准专业区域，定义后留给自定义区域使用，或跳过。
> 标准区域的 YieldChangeId 映射：学院→Science、商业/港口→Gold、剧院→Culture、工业→Production、圣地→Faith。

**Text 格式（6 条）：**

```sql
('zh_Hans_CN', 'LOC_DISTRICT_SIQI_{SHORT}_ADJACENCY_SCIENCE',    '+{1_Amount}[ICON_Science]科技值 来自相邻的 {区域名}。'),
('zh_Hans_CN', 'LOC_DISTRICT_SIQI_{SHORT}_ADJACENCY_PRODUCTION', '+{1_Amount}[ICON_Production]生产力 来自相邻的 {区域名}。'),
('zh_Hans_CN', 'LOC_DISTRICT_SIQI_{SHORT}_ADJACENCY_GOLD',       '+{1_Amount}[ICON_Gold]金币 来自相邻的 {区域名}。'),
('zh_Hans_CN', 'LOC_DISTRICT_SIQI_{SHORT}_ADJACENCY_FOOD',       '+{1_Amount}[ICON_Food]食物 来自相邻的 {区域名}。'),
('zh_Hans_CN', 'LOC_DISTRICT_SIQI_{SHORT}_ADJACENCY_CULTURE',    '+{1_Amount}[ICON_Culture]文化值 来自相邻的 {区域名}。'),
('zh_Hans_CN', 'LOC_DISTRICT_SIQI_{SHORT}_ADJACENCY_FAITH',      '+{1_Amount}[ICON_Faith]信仰值 来自相邻的 {区域名}。');
```

---

## 五、文本（区域用法时）

区域相邻加成的 LOC_ 文本格式：

```
+{1_Amount}[ICON_{产出图标}]产出描述 来自相邻的 {条件对象}。（解锁条件）
```

完整示例：
```
('zh_Hans_CN', 'LOC_DISTRICT_SIQI_D0029_1_MOUNTAIN_SCIENCE', '+{1_Amount}[ICON_Science]科技值 来自相邻的 山脉。'),
('zh_Hans_CN', 'LOC_DISTRICT_SIQI_D0029_1_DISTRICT_SCIENCE', '+{1_Amount}[ICON_Science]科技值 来自相邻的 区域。'),
('zh_Hans_CN', 'LOC_DISTRICT_SIQI_D0029_1_JUNGLE_SCIENCE', '+{1_Amount}[ICON_Science]科技值 来自相邻的 {LOC_FEATURE_JUNGLE_NAME}（每2格触发1次）。'),
('zh_Hans_CN', 'LOC_DISTRICT_SIQI_D0029_1_RIVER_GOLD', '+{1_Amount}[ICON_Gold]金币 来自相邻的 河流。（解锁科技：{LOC_TECH_CURRENCY_NAME}）'),
```

图标对应：`YIELD_SCIENCE`→`[ICON_Science]`，`YIELD_GOLD`→`[ICON_Gold]`，`YIELD_FAITH`→`[ICON_Faith]`，`YIELD_CULTURE`→`[ICON_Culture]`，`YIELD_PRODUCTION`→`[ICON_Production]`，`YIELD_FOOD`→`[ICON_Food]`

---

## 六、对 district.md 的关联

District_Adjacencies 的 SQL 写入 `Data/<ModName>_Districts.sql`（与 region 主体同文件），但定义逻辑查询本 skill。
