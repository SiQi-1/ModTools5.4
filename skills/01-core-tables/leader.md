# Leader — 领袖定义

## 涉及文件

| 文件 | 内容 |
|------|------|
| `Data/<ModName>_Leaders.sql` | 领袖主表 + 特质绑定 + 加载画面 |
| `Text/<ModName>_Text_CN.sql` | 领袖名、特质名/描述、加载文本、百科引言 |

## 涉及的表（按 INSERT 顺序）

```
Types → Leaders → LeaderTraits → LoadingInfo → [LeaderQuotes] → [Leaders_XP2]
```

---

## 一、Types

与 civilization.md 相同模式的 Type 注册。领袖需要注册两个：

```sql
INSERT INTO Types (Type, Kind) VALUES
('LEADER_SIQI_{SHORT}', 'KIND_LEADER'),
('TRAIT_LEADER_SIQI_{SHORT}', 'KIND_TRAIT');
```

---

## 二、Leaders

### 表结构

| 列名 | 类型 | 写不写 |
|------|------|--------|
| LeaderType | TEXT, NOT NULL | **必写** |
| Name | TEXT, NOT NULL | **必写**（LOC_ 键） |
| OperationList | TEXT, 可空 | **不写**（通常不用） |
| IsBarbarianLeader | BOOLEAN, NOT NULL, default=0 | **不写**（默认 0） |
| InheritFrom | TEXT, 可空 | **必写** |
| SceneLayers | INTEGER, NOT NULL, default=0 | **必写** |
| Sex | TEXT, NOT NULL, default="Male" | **必写** |
| SameSexPercentage | INTEGER, NOT NULL, default=0 | **不写**（默认 0） |

### 列值参考

| 列名 | 值参考 |
|------|--------|
| LeaderType | `LEADER_SIQI_L{SHORT}_{N}` |
| Name | `LOC_LEADER_SIQI_L{SHORT}_{N}_NAME` |
| InheritFrom | `LEADER_DEFAULT`（新建领袖默认值）。`InheritFrom` 继承的是**特质（Traits）**，不是美术资源。仅同一领袖绑定不同文明时才需要指定别的值。切勿以为它继承图片/模型/动画 |
| SceneLayers | `4`（标准外交场景层数） |
| Sex | `Male` / `Female`，用户告知，无说明默认 `Male` |

### INSERT 模板

```sql
INSERT INTO Leaders (LeaderType, Name, Sex, InheritFrom, SceneLayers) VALUES
('LEADER_SIQI_L{SHORT}_{N}',
 'LOC_LEADER_SIQI_L{SHORT}_{N}_NAME',
 'Male',
 'LEADER_DEFAULT',
 4);
```

---

## 三、Leaders_XP2

### 表结构

| 列名 | 类型 | 写不写 |
|------|------|--------|
| LeaderType | TEXT, NOT NULL | **必写** |
| OceanStart | BOOLEAN, NOT NULL, default=0 | **必写**(如果需要) |
| MinorCivBonusType | TEXT, 可空 | **不写**（城邦用） |

### 说明

控制领袖是否出生在海上（如毛利）。**绝大部分领袖不写这张表。**

```sql
-- 仅当领袖需要海上出生时：
INSERT INTO Leaders_XP2 (LeaderType, OceanStart) VALUES
('LEADER_SIQI_L{SHORT}_{N}', 1);
```

不需要海上出生就不写。

---

## 四、LeaderTraits

### 表结构

| 列名 | 类型 | 写不写 |
|------|------|--------|
| LeaderType | TEXT, NOT NULL | **必写** |
| TraitType | TEXT, NOT NULL | **必写** |

### INSERT 模板

```sql
INSERT INTO LeaderTraits (LeaderType, TraitType) VALUES
('LEADER_SIQI_L{SHORT}_{N}', 'TRAIT_LEADER_SIQI_L{SHORT}_{N}');
```

> TraitType 必须在 Types 中先注册为 `KIND_TRAIT`。

---

## 五、LoadingInfo

### 表结构

| 列名 | 类型 | 写不写 |
|------|------|--------|
| LeaderType | TEXT, NOT NULL | **必写** |
| ForegroundImage | TEXT, 可空 | **必写** |
| BackgroundImage | TEXT, 可空 | **必写** |
| EraText | TEXT, 可空 | **可选** |
| LeaderText | TEXT, 可空 | **可选**（LOC_ 键） |
| PlayDawnOfManAudio | BOOLEAN, NOT NULL, default=1 | **必写** |
| DawnOfManLeaderId | TEXT, 可空 | **不写**（除非语音重定向） |
| DawnOfManEraId | TEXT, 可空 | **不写**（除非语音重定向） |

### 美术资产命名规则

每个领袖实例需要以下美术资产（**用户提供图片，AI 只保证命名正确**）：

| 用途 | 命名格式 | 对应列 |
|------|---------|--------|
| 加载前景 | `LEADER_SIQI_L{SHORT}_{N}_NEUTRAL` | ForegroundImage |
| 加载背景 | `LEADER_SIQI_L{SHORT}_{N}_BACKGROUND` | BackgroundImage |
| 外交肖像 | `FALLBACK_NEUTRAL_SIQI_L{SHORT}_{N}` | XLPs/LeaderFallback.xlp |
| 外交背景1 | `SIQI_L{SHORT}_{N}_1` | 外交场景 |
| 外交背景2 | `SIQI_L{SHORT}_{N}_2` | 外交场景 |
| 外交背景3 | `SIQI_L{SHORT}_{N}_3` | 外交场景 |

示例（0032 取三个领袖，方便复制替换）：

```
-- 领袖钟离加载前景：LEADER_SIQI_L0032_1_NEUTRAL
-- 领袖钟离加载背景：LEADER_SIQI_L0032_1_BACKGROUND
-- 领袖钟离外交肖像：FALLBACK_NEUTRAL_SIQI_L0032_1
-- 领袖钟离外交背景：SIQI_L0032_1_1,SIQI_L0032_1_2,SIQI_L0032_1_3

-- 领袖兹白加载前景：LEADER_SIQI_L0032_2_NEUTRAL
-- 领袖兹白加载背景：LEADER_SIQI_L0032_2_BACKGROUND
-- 领袖兹白外交肖像：FALLBACK_NEUTRAL_SIQI_L0032_2
-- 领袖兹白外交背景：SIQI_L0032_2_1,SIQI_L0032_2_2,SIQI_L0032_2_3

-- 领袖闲云加载前景：LEADER_SIQI_L0032_3_NEUTRAL
-- 领袖闲云加载背景：LEADER_SIQI_L0032_3_BACKGROUND
-- 领袖闲云外交肖像：FALLBACK_NEUTRAL_SIQI_L0032_3
-- 领袖闲云外交背景：SIQI_L0032_3_1,SIQI_L0032_3_2,SIQI_L0032_3_3
```

### INSERT 模板

```sql
INSERT INTO LoadingInfo (LeaderType, ForegroundImage, BackgroundImage, PlayDawnOfManAudio, LeaderText) VALUES
('LEADER_SIQI_L{SHORT}_{N}',
 'LEADER_SIQI_L{SHORT}_{N}_NEUTRAL',
 'LEADER_SIQI_L{SHORT}_{N}_BACKGROUND',
 1,
 'LOC_LOADING_INFO_LEADER_SIQI_L{SHORT}_{N}');
```

如果懒得写 `LeaderText`，可以省略该列：
```sql
INSERT INTO LoadingInfo (LeaderType, ForegroundImage, BackgroundImage, PlayDawnOfManAudio) VALUES
('LEADER_SIQI_L{SHORT}_{N}',
 'LEADER_SIQI_L{SHORT}_{N}_NEUTRAL',
 'LEADER_SIQI_L{SHORT}_{N}_BACKGROUND',
 1);
```

---

## 六、LeaderQuotes（可选）

### 表结构

| 列名 | 类型 | 写不写 |
|------|------|--------|
| LeaderType | TEXT, NOT NULL | **必写** |
| Quote | TEXT, NOT NULL | **必写**（LOC_ 键） |
| QuoteAudio | TEXT, 可空 | **不写**（音频导入黑箱，一般用不到） |

### INSERT 模板

```sql
INSERT INTO LeaderQuotes (LeaderType, Quote) VALUES
('LEADER_SIQI_L{SHORT}_{N}', 'LOC_PEDIA_LEADERS_PAGE_LEADER_SIQI_L{SHORT}_{N}_QUOTE');
```

---

## 七、文本（Text/ 文件）

### 需要创建的 LOC_ 键

| LOC_ 键 | 说明 | 是否必须 |
|---------|------|---------|
| `LOC_LEADER_SIQI_L{SHORT}_{N}_NAME` | 领袖名称 | **是** |
| `LOC_TRAIT_LEADER_SIQI_L{SHORT}_{N}_NAME` | 领袖特质名称 | **是** |
| `LOC_TRAIT_LEADER_SIQI_L{SHORT}_{N}_DESCRIPTION` | 领袖特质描述 | **是** |
| `LOC_LOADING_INFO_LEADER_SIQI_L{SHORT}_{N}` | 加载画面文本 | 可选（写了 LoadingInfo.LeaderText 就要） |
| `LOC_PEDIA_LEADERS_PAGE_LEADER_SIQI_L{SHORT}_{N}_QUOTE` | 百科引言 | 可选（写了 LeaderQuotes 就要） |

### Text INSERT 模板

```sql
INSERT INTO LocalizedText (Language, Tag, Text) VALUES
-- 领袖基本信息
('zh_Hans_CN', 'LOC_LEADER_SIQI_L{SHORT}_{N}_NAME',                  '{领袖名称}'),
('zh_Hans_CN', 'LOC_TRAIT_LEADER_SIQI_L{SHORT}_{N}_NAME',            '{特质名称}'),
('zh_Hans_CN', 'LOC_TRAIT_LEADER_SIQI_L{SHORT}_{N}_DESCRIPTION',     '{特质描述}'),
-- 加载文本（可选）
('zh_Hans_CN', 'LOC_LOADING_INFO_LEADER_SIQI_L{SHORT}_{N}',          '{加载画面文本}'),
-- 百科引言（可选）
('zh_Hans_CN', 'LOC_PEDIA_LEADERS_PAGE_LEADER_SIQI_L{SHORT}_{N}_QUOTE', '{百科引言}');
```

---

## 八、关联文件

写完 Leaders.sql + Text 后，还必须写以下配套文件：

| 文件 | 技能 | 说明 |
|------|------|------|
| `Data/<ModName>_Civilizations.sql` | `civilization.md` | CivilizationLeaders 绑领袖 |
| `Data/<ModName>_Configs.sql` | `configs.md` | Players + PlayerItems 注册 |
| `Data/<ModName>_Colors.sql` | `colors.md` | 玩家颜色 |
| `Icons/<ModName>_Icons.xml` | `icons.md` | 领袖图标（尺寸 32/45/48/50/55/64/80/256） |
| `<ModName>.Art.xml` | `art.md` | 领袖美术依赖 |
| `XLPs/LeaderFallback.xlp` | `art.md` | 外交肖像注册 |
| `XLPs/<ModName>_dds.xlp` | `art.md` | 纹理包 |
| `<ModName>.civ6proj` | `civ6proj.md` | 注册 UpdateDatabase 动作 |
