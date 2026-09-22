# Civilization — 文明定义

## 涉及文件

| 文件 | 内容 |
|------|------|
| `Data/<ModName>_Civilizations.sql` | 文明主表 + 城市名/市民名 + 起始偏好 |
| `Text/<ModName>_Text_CN.sql` | 文明名、形容词、城市名、市民名文本 |

## 涉及的表（按 INSERT 顺序）

```
Types → Civilizations → CivilizationTraits → CivilizationLeaders
→ CityNames → CivilizationCitizenNames
→ StartBiasRivers → StartBiasTerrains → StartBiasResources → StartBiasFeatures
```

---

## 一、Types

### 表结构

| 列名 | 类型 | 写不写 |
|------|------|--------|
| Type | TEXT, NOT NULL | **必写** |
| Kind | TEXT, NOT NULL | **必写** |
| Hash | INTEGER, NOT NULL, default=0 | **不写**（自动生成） |

### INSERT 模板

```sql
-- 文明
INSERT INTO Types (Type, Kind) VALUES
('CIVILIZATION_SIQI_{SHORT}', 'KIND_CIVILIZATION'),
('TRAIT_CIVILIZATION_SIQI_{SHORT}', 'KIND_TRAIT');
```

`{SHORT}` = 文明简称，从 Mod 文件夹名推导。例如 `Siqi_Leaders_0029` → `C0029`（C + 项目号）。

---

## 二、Civilizations

### 表结构

| 列名 | 类型 | 写不写 |
|------|------|--------|
| CivilizationType | TEXT, NOT NULL | **必写** |
| Name | TEXT, NOT NULL | **必写**（LOC_ 键） |
| Description | TEXT, NOT NULL | **必写**（LOC_ 键。⚠ **国家全称**，如"中华帝国""罗马帝国"，不是玩法描述） |
| Adjective | TEXT, NOT NULL | **必写**（LOC_ 键） |
| RandomCityNameDepth | INTEGER, NOT NULL, default=1 | **必写** |
| StartingCivilizationLevelType | TEXT, NOT NULL | **必写** |
| Ethnicity | TEXT, 可空 | **写**（默认 `ETHNICITY_ASIAN`） |

### 列值参考

| 列名 | 值参考 |
|------|--------|
| CivilizationType | `CIVILIZATION_SIQI_{SHORT}` |
| Name | `LOC_CIVILIZATION_SIQI_{SHORT}_NAME` |
| Description | `LOC_CIVILIZATION_SIQI_{SHORT}_DESCRIPTION` |
| Adjective | `LOC_CIVILIZATION_SIQI_{SHORT}_ADJECTIVE` |
| RandomCityNameDepth | 在前 N 个未使用城市名中随机取下一个。填 `1` = 严格按表序；值越大越随机。见第五节 CityNames |
| StartingCivilizationLevelType | `CIVILIZATION_LEVEL_FULL_CIV`（完整文明） |
| Ethnicity | 默认 `ETHNICITY_ASIAN`。其他：`ETHNICITY_EURO` / `ETHNICITY_MEDIT` / `ETHNICITY_SOUTHAM` / `ETHNICITY_AFRICAN` |

`StartingCivilizationLevelType` 可选值：
- `CIVILIZATION_LEVEL_FULL_CIV` — 完整文明
- `CIVILIZATION_LEVEL_CITY_STATE` — 城邦
- `CIVILIZATION_LEVEL_TRIBE` — 部落
- `CIVILIZATION_LEVEL_FREE_CITIES` — 自由城市

### INSERT 模板（7 列）

```sql
INSERT INTO Civilizations (CivilizationType, Name, Description, Adjective, StartingCivilizationLevelType, Ethnicity, RandomCityNameDepth) VALUES
('CIVILIZATION_SIQI_{SHORT}',
 'LOC_CIVILIZATION_SIQI_{SHORT}_NAME',
 'LOC_CIVILIZATION_SIQI_{SHORT}_DESCRIPTION',
 'LOC_CIVILIZATION_SIQI_{SHORT}_ADJECTIVE',
 'CIVILIZATION_LEVEL_FULL_CIV',
 'ETHNICITY_ASIAN',
 10);
```

---

## 三、CivilizationTraits

### 表结构

| 列名 | 类型 | 写不写 |
|------|------|--------|
| CivilizationType | TEXT, NOT NULL | **必写** |
| TraitType | TEXT, NOT NULL | **必写** |

### INSERT 模板

```sql
INSERT INTO CivilizationTraits (CivilizationType, TraitType) VALUES
('CIVILIZATION_SIQI_{SHORT}', 'TRAIT_CIVILIZATION_SIQI_{SHORT}');
```

每一行一个特质。有特色建筑/单位/区域/改良时追加对应特质行：

```sql
INSERT INTO CivilizationTraits (CivilizationType, TraitType) VALUES
('CIVILIZATION_SIQI_{SHORT}', 'TRAIT_BUILDING_SIQI_B{SHORT}_1'),
('CIVILIZATION_SIQI_{SHORT}', 'TRAIT_UNIT_SIQI_U{SHORT}_1'),
('CIVILIZATION_SIQI_{SHORT}', 'TRAIT_DISTRICT_SIQI_D{SHORT}_1'),
('CIVILIZATION_SIQI_{SHORT}', 'TRAIT_IMPROVEMENT_SIQI_I{SHORT}_1');
```

> TraitType 必须在 Types 中先注册为 `KIND_TRAIT`。

---

## 四、CivilizationLeaders

### 表结构

| 列名 | 类型 | 写不写 |
|------|------|--------|
| CivilizationType | TEXT, NOT NULL | **必写** |
| LeaderType | TEXT, NOT NULL | **必写** |
| CapitalName | TEXT, NOT NULL | **必写** |

### 规则
- 一个文明可以有多个领袖，写多行
- 一个领袖**不可以**绑多个文明（非法操作）
- CapitalName 填首都名的 LOC_ 键

### INSERT 模板

```sql
INSERT INTO CivilizationLeaders (CivilizationType, LeaderType, CapitalName) VALUES
('CIVILIZATION_SIQI_{SHORT}', 'LEADER_SIQI_L{SHORT}_1', 'LOC_CITY_NAME_SIQI_L{SHORT}_1_CAPITAL');
```

多领袖：
```sql
INSERT INTO CivilizationLeaders (CivilizationType, LeaderType, CapitalName) VALUES
('CIVILIZATION_SIQI_{SHORT}', 'LEADER_SIQI_L{SHORT}_1', 'LOC_CITY_NAME_SIQI_L{SHORT}_1_CAPITAL'),
('CIVILIZATION_SIQI_{SHORT}', 'LEADER_SIQI_L{SHORT}_2', 'LOC_CITY_NAME_SIQI_L{SHORT}_2_CAPITAL');
```

---

## 五、CityNames

### 表结构

| 列名 | 类型 | 写不写 |
|------|------|--------|
| ID | INTEGER, 可空 | **不写**（自动递增） |
| CivilizationType | TEXT, 可空 | **写**（文明专属城市名时填） |
| LeaderType | TEXT, 可空 | 用户有告知时写，否则不写 |
| ContinentType | TEXT, 可空 | 用户有告知时写，否则不写 |
| CityName | TEXT, NOT NULL | **必写**（LOC_ 键） |
| SortIndex | INTEGER, NOT NULL, default=0 | **不写**（使用默认值） |

### INSERT 模板

```sql
INSERT INTO CityNames (CivilizationType, CityName) VALUES
('CIVILIZATION_SIQI_{SHORT}', 'LOC_SIQI_{SHORT}_CITY_NAME_1'),
('CIVILIZATION_SIQI_{SHORT}', 'LOC_SIQI_{SHORT}_CITY_NAME_2'),
('CIVILIZATION_SIQI_{SHORT}', 'LOC_SIQI_{SHORT}_CITY_NAME_3');
-- ... 建议 10-30 个
```

### 城市名来源

| 方式 | 说明 |
|------|------|
| 用户直接提供 | 用户说出城市名列表，直接填入 |
| AI 联网搜索 | 搜索主题相关真实地名（如"三国城市名""罗德岛地名"）填入 |
| SELECT 复制官方 | `INSERT INTO CityNames (CivilizationType, CityName) SELECT 'CIVILIZATION_SIQI_{SHORT}', CityName FROM CityNames WHERE CivilizationType = 'CIVILIZATION_AMERICA'` |

### 与 RandomCityNameDepth 的关系

`Civilizations.RandomCityNameDepth` 控制随机抽取范围：
- 填 `1` = 严格按 CityNames 表序依次使用城市名
- 填 `10` = 在前 10 个未使用城市名中随机取
- 城市名 30 个，填 `30` = 从全部未用名中完全随机

---

## 六、CivilizationCitizenNames

### 表结构

| 列名 | 类型 | 写不写 |
|------|------|--------|
| CivilizationType | TEXT, NOT NULL | **必写** |
| CitizenName | TEXT, NOT NULL | **必写**（LOC_ 键） |
| Female | BOOLEAN, NOT NULL, default=0 | **必写** |
| Modern | BOOLEAN, NOT NULL, default=0 | **必写** |

- `Female`：0 = 男，1 = 女
- `Modern`：0 = 古代，1 = 现代

### INSERT 模板

```sql
-- 市民名（按 Female 和 Modern 混排，不分四类）
INSERT INTO CivilizationCitizenNames (CivilizationType, CitizenName, Female, Modern) VALUES
-- 古代男性
('CIVILIZATION_SIQI_{SHORT}', 'LOC_SIQI_{SHORT}_CITIZEN_NAME_1', 0, 0),
('CIVILIZATION_SIQI_{SHORT}', 'LOC_SIQI_{SHORT}_CITIZEN_NAME_2', 0, 0),
-- ...（中间按需分配）
-- 古代女性
('CIVILIZATION_SIQI_{SHORT}', 'LOC_SIQI_{SHORT}_CITIZEN_NAME_11', 1, 0),
('CIVILIZATION_SIQI_{SHORT}', 'LOC_SIQI_{SHORT}_CITIZEN_NAME_12', 1, 0),
-- ...（中间按需分配）
-- 现代男性
('CIVILIZATION_SIQI_{SHORT}', 'LOC_SIQI_{SHORT}_CITIZEN_NAME_21', 0, 1),
-- ...（中间按需分配）
-- 现代女性
('CIVILIZATION_SIQI_{SHORT}', 'LOC_SIQI_{SHORT}_CITIZEN_NAME_31', 1, 1);
-- ...（中间按需分配）
```

各组合最少 1 个，建议各占约 1/4。LOC 键用连续数字后缀 `_N`，不分 MALE/FEMALE/ANCIENT/MODERN 字样。

### 市民名来源

同城市名：用户提供 / AI 联网搜索 / SELECT 复制官方。

---

## 七、StartBias 系列

### 表结构

| 表名 | 特征列 | 规则 |
|------|--------|------|
| StartBiasRivers | *(无)* | 只填 CivilizationType + Tier |
| StartBiasTerrains | TerrainType (TEXT, NOT NULL) | — |
| StartBiasResources | ResourceType (TEXT, NOT NULL) | — |
| StartBiasFeatures | FeatureType (TEXT, NOT NULL) | — |

所有表共享：`CivilizationType` (TEXT, NOT NULL)、`Tier` (INTEGER, NOT NULL, default=-1)

- Tier：`1`(最强偏好) ~ `5`(最弱偏好)，值越小越优先
- 不需要的起始偏好表不写
- StartBiasAdjacencies：空表，跳过

### 枚举值来源

| 列 | 查哪个文件 |
|------|------------|
| TerrainType | [TerrainType 查询依据](../SOURCES.md#类型与枚举) — 17 条，含中文名 |
| ResourceType | [ResourceType 查询依据](../SOURCES.md#类型与枚举) — 54 条，按战略/奢侈品/加成/文物分组，含中文名 |
| FeatureType | [FeatureType 查询依据](../SOURCES.md#类型与枚举) — 50 条，按类型分组，含中文名 |

### INSERT 模板

```sql
-- 起始偏好：地形（例：优先草原山脉）
INSERT INTO StartBiasTerrains (CivilizationType, TerrainType, Tier) VALUES
('CIVILIZATION_SIQI_{SHORT}', 'TERRAIN_GRASS_MOUNTAIN', 1),
('CIVILIZATION_SIQI_{SHORT}', 'TERRAIN_PLAINS_MOUNTAIN', 3);
-- 起始偏好：资源（例：优先铁矿）
INSERT INTO StartBiasResources (CivilizationType, ResourceType, Tier) VALUES
('CIVILIZATION_SIQI_{SHORT}', 'RESOURCE_IRON', 2);
-- 起始偏好：河流
INSERT INTO StartBiasRivers (CivilizationType, Tier) VALUES
('CIVILIZATION_SIQI_{SHORT}', 3);
```

---

## 八、文本（Text/ 文件）

### 需要创建的 LOC_ 键

| LOC_ 键 | 说明 | 示例值 |
|---------|------|--------|
| `LOC_CIVILIZATION_SIQI_{SHORT}_NAME` | 文明名 | `测试文明` |
| `LOC_CIVILIZATION_SIQI_{SHORT}_DESCRIPTION` | 文明百科描述 | `测试文明的百科描述` |
| `LOC_CIVILIZATION_SIQI_{SHORT}_ADJECTIVE` | 文明形容词 | `测试` |
| `LOC_TRAIT_CIVILIZATION_SIQI_{SHORT}_NAME` | 特质名称 | `测试特质` |
| `LOC_TRAIT_CIVILIZATION_SIQI_{SHORT}_DESCRIPTION` | 特质描述 | `这是特质的描述` |
| `LOC_CITY_NAME_SIQI_L{SHORT}_1_CAPITAL` | 首都名 | `测试首都` |
| `LOC_SIQI_{SHORT}_CITY_NAME_{N}` | 第 N 个城市名 | `测试城1` |
| `LOC_SIQI_{SHORT}_CITIZEN_NAME_{N}` | 第 N 个市民名 | `阿明`（男古）、`小花`（女现） |

### Text INSERT 模板

```sql
INSERT INTO LocalizedText (Language, Tag, Text) VALUES
-- 文明基本信息
('zh_Hans_CN', 'LOC_CIVILIZATION_SIQI_{SHORT}_NAME',        '{文明名称}'),
('zh_Hans_CN', 'LOC_CIVILIZATION_SIQI_{SHORT}_DESCRIPTION', '{文明百科描述}'),
('zh_Hans_CN', 'LOC_CIVILIZATION_SIQI_{SHORT}_ADJECTIVE',   '{文明形容词}'),
('zh_Hans_CN', 'LOC_TRAIT_CIVILIZATION_SIQI_{SHORT}_NAME',        '{特质名称}'),
('zh_Hans_CN', 'LOC_TRAIT_CIVILIZATION_SIQI_{SHORT}_DESCRIPTION', '{特质描述}'),
-- 首都名
('zh_Hans_CN', 'LOC_CITY_NAME_SIQI_L{SHORT}_1_CAPITAL', '{首都名称}'),
-- 城市名
('zh_Hans_CN', 'LOC_SIQI_{SHORT}_CITY_NAME_1',  '{城市名1}'),
('zh_Hans_CN', 'LOC_SIQI_{SHORT}_CITY_NAME_2',  '{城市名2}'),
-- 市民名（按 Female/Modern 混排，连续编号）
('zh_Hans_CN', 'LOC_SIQI_{SHORT}_CITIZEN_NAME_1',  '{市民名1}'),
('zh_Hans_CN', 'LOC_SIQI_{SHORT}_CITIZEN_NAME_2',  '{市民名2}'),
-- ...
```

多语言时追加 `en_US` 行即可。

---

## 九、关联文件

写完 Civilization.sql + Text 后，还必须写以下配套文件：

| 文件 | 技能 | 说明 |
|------|------|------|
| `Data/<ModName>_Leaders.sql` | `leader.md` | 领袖必须有 |
| `Data/<ModName>_Configs.sql` | `configs.md` | Players + PlayerItems 注册 |
| `Data/<ModName>_Colors.sql` | `colors.md` | 玩家颜色 |
| `Icons/<ModName>_Icons.xml` | `icons.md` | 文明图标（尺寸 22/30/32/36/44/45/48/50/64/80/128/200/256） |
| `<ModName>.civ6proj` | `civ6proj.md` | 注册 UpdateDatabase 动作 |
