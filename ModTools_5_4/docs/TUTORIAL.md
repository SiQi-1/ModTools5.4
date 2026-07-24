# 文明6 Mod 制作完整教程

本教程带你从零开始，用 ModTools 5.4 制作一个完整的文明6 Mod。每章结束时你都能在游戏中验证成果。

> **阅读方式**：按顺序从头读到尾，边读边操作。每一步都描述了具体点击位置和填写内容，不需要截图。

---

## 目录

1. [准备工作](#1-准备工作)
2. [你的第一个 Mod：创建工程](#2-你的第一个-mod创建工程)
3. [第一个文明](#3-第一个文明)
4. [第一个领袖](#4-第一个领袖)
5. [第一个单位](#5-第一个单位)
6. [建筑](#6-建筑)
7. [区域](#7-区域)
8. [改良设施](#8-改良设施)
9. [修改器系统](#9-修改器系统)
10. [图标和美术](#10-图标和美术)
11. [文本和本地化](#11-文本和本地化)
12. [生成与部署](#12-生成与部署)
13. [进阶：从数据库导入再修改](#13-进阶从数据库导入再修改)
14. [其他内容类型](#14-其他内容类型)
    - 14.1 伟人 · 14.2 政策卡 · 14.3 项目 · 14.4 单位晋升 · 14.5 总督 · 14.6 议程 · 14.7 信仰
15. [常见问题排解](#15-常见问题排解)

---

## 1. 准备工作

### 1.1 你需要什么

- **文明6 游戏**（至少运行过一次，以生成缓存数据）
- **ModBuddy**（Steam 库 → 工具 → Civilization VI Development Tools，用于最后打包和部署）
- **ModTools 5.4**（本工具，无需安装 Python）

### 1.2 首次启动 ModTools

打开 ModTools 后，先别急着建工程。点击顶部菜单 **设置**，配置两个数据库：

**文本数据库**
- 发布包自带 `local_text_New.sqlite`，直接选择它即可
- 如果需要 DLC 文本（如迭起兴衰、风云变幻的新内容），点击「导入 DLC」选择游戏 DLC 目录追加导入
- 不配文本库 → 所有中文预览显示"未知"

**游戏数据库**
- 选择 `DebugGameplay.sqlite`
- 路径：`C:\Users\<用户名>\AppData\Local\Firaxis Games\Sid Meier's Civilization VI\Cache\DebugGameplay.sqlite`
- 用于从原版游戏导入对象、搜索修改器等功能
- 不配游戏库 → 导入功能和修改器搜索不可用

两项都配好后，关闭设置页。

---

## 2. 你的第一个 Mod：创建工程

### 2.1 概念说明

ModTools 用两种文件：

| 文件 | 谁用的 | 干什么 |
|------|--------|--------|
| `.CIV` | ModTools | 保存你的所有编辑状态（JSON 格式） |
| `.civ6proj` | ModBuddy | 定义 Mod 的文件结构和元信息 |

ModTools 读取 `.civ6proj` 来确定输出文件写到哪个目录，然后把生成好的 SQL/XML/图标文件放到对应位置。

### 2.2 创建工程

1. 菜单 **文件 → 新建工程**
2. 输入工程名（英文，建议格式：`Siqi_MyFirstMod`）
3. 选择保存位置，保存为 `.CIV` 文件

### 2.3 创建 ModBuddy 工程

在 ModBuddy 中：
1. **File → New → Project** → 选择 **Civilization VI Mod**
2. 命名为与上面相同的英文名
3. 记下工程保存位置（默认在 `Documents\Firaxis ModBuddy\Civilization VI\`）

### 2.4 绑定工程

回到 ModTools，在左侧树中点击 **基础信息**：
1. 点击「选择 .civ6proj」→ 找到上一步 ModBuddy 创建的 `.civ6proj` 文件
2. 设置 **文件名前缀**：你的 Mod 名称，如 `Siqi_MyFirstMod`
3. 设置 **文件名中缀**：起始编号，一般填 `0`
4. 点击「一键配置」自动生成常用文件条目

**前缀和中缀决定了你所有 Type 的命名**。比如前缀填 `Siqi_MyFirstMod`，中缀填 `0`，你的第一个文明 Type 会是 `CIVILIZATION_SIQI_MYFIRSTMOD_0`。中缀值在每新建一个对象时自动递增。

---

## 3. 第一个文明

### 3.1 你要做什么

创建一个自定义文明，定义它的特色能力（Trait），让游戏能识别它。

### 3.2 新建文明

在左侧树中右键 **文明** → **新增条目**。

右侧会出现文明编辑器，包含以下区域：

**基本区域**（上半部分）
- **Name**：文明中文名，如"明日方舟"
- **Description**：文明描述文本，会显示在选择文明界面
- **TraitType**：文明特质，这是文明的核心。点击右侧「生成」按钮自动创建

**数值和布尔区域**（下半部分）
- 大部分保持默认即可
- 常用修改项：`StartingCivilizationLevelType`（起始时代）、`CapitalName`（首都名）

### 3.3 关键字段解释

| 字段 | 说明 |
|------|------|
| `TraitType` | 文明特质，所有特色效果都通过它挂载（见第9章修改器） |
| `Ethnicity` | 民族外观，决定城市/单位的美术风格 |
| `RandomCityName` | 是否使用随机城市名（一般勾选） |

其他字段绝大多数不需要动。

### 3.4 注意

- 标 `*` 的字段为必填，留空会导致生成失败
- `TraitType` 的 Type 命名格式自动遵循 `TRAIT_CIVILIZATION_<前缀>_<中缀>` 规则
- 如果你还没准备好修改器，`TraitType` 可以先只有名字（生成后在数据库中有条目即可），效果可以之后再加

填完后按 `Ctrl+S` 或点击 **工程根节点** → 先不生成，继续下一步。

---

## 4. 第一个领袖

### 4.1 你要做什么

创建一个领袖，绑定到刚才的文明上。

### 4.2 新建领袖

在左侧树中右键 **领袖** → **新增条目**。

### 4.3 关键字段

**基本区域**
- **Name**：领袖中文名
- **Description**：领袖描述
- **TraitType**：领袖特质，点击「生成」自动创建（格式：`TRAIT_LEADER_<前缀>_<中缀>`）
- **CivilizationType**：选择你刚才创建的文明 Type
- **LeaderType**：自动生成，无需修改
- **InheritFrom**：领袖"继承"——你的领袖行为和动画将基于原版某个领袖。下拉框可搜索（如 `LEADER_T_ROOSEVELT`），大部分情况选 `LEADER_DEFAULT` 即可

**领袖图片**（编辑器下方区域）
- 共 6 个图片槽位：前景、背景、外交界面、选择界面等
- 如果暂时没有美术素材，可以先空着，后期在「美术」页统一管理

**领袖颜色**（颜色配置区域）
- 4 套球衣配色（Primary/Secondary/Alt1/Alt2）
- 点击取色弹窗，内置 28 个官方标准色可选，也可以输入自定义色值
- 右侧横幅预览实时显示效果

### 4.4 绑定文明

`CivilizationType` 字段点击下拉，搜索你创建的文明 Type（如 `CIVILIZATION_SIQI_MYFIRSTMOD_0`）。选完后，在游戏中这个领袖就能带领你的文明了。

---

## 5. 第一个单位

### 5.1 你要做什么

创建一个自定义单位——比如一个替代勇士（Warrior）的独特单位。

### 5.2 新建单位

在左侧树中右键 **单位** → **新增条目**。

### 5.3 单位编辑器结构

单位的编辑器是一个**复合编辑器**，从上到下依次是：

| 区块 | 类型 | 说明 |
|------|------|------|
| **主表** | 表单 | 单位核心属性（战斗、移动、造价等） |
| **Units_XP2** | 表单 | 资料片参数（资源消耗、经验获取等） |
| **Units_MODE / Units_Presentation** | 单行 | 垄断公司模式、旗标偏移 |
| **UnitReplaces / UnitUpgrades** | 单行 | 替代哪个单位 / 升级成哪个单位 |
| **UnitCaptures** | 单行 | 捕获后转换成的单位 |
| **UnitRetreats_XP1 / Unit_BuildingPrereqs** | 多行表 | 撤退规则、建筑前置条件 |
| **TypeTags** | 复选框+搜索 | 单位类别标签 |
| **UnitAiInfos** | 多行表 | AI 行为类型 |
| **TypeProperties** | 多行表 | 单位特殊属性（英雄寿命等） |
| **UnitAbilityBindings** | 开关 | 单位能力绑定 |

### 5.4 主表核心字段

**基础字段**
- `Name` / `Description`：单位名称和描述。先在 Descirption 写个简短说明（记得用英文或留空——Name 已经能显示）
- `Domain`：`DOMAIN_LAND`（陆地）或 `DOMAIN_SEA`（海军）
- `FormationClass`：单位编队类型，**必填**。下拉可选：`FORMATION_CLASS_MELEE`（近战）、`FORMATION_CLASS_RANGED`（远程）、`FORMATION_CLASS_LANDCIVILIAN`（平民）等
- `PromotionClass`：晋升树类型，决定单位能晋升到哪种兵种
- `PrereqTech` / `PrereqCivic`：解锁科技/市政
- `StrategicResource`：所需战略资源
- `TraitType`：单位特质，点击「生成」自动创建

**数值字段**
- `BaseSightRange`：视野（默认 2）
- `BaseMoves`：移动力（默认 2）
- `Combat`：近战攻击力
- `RangedCombat`：远程攻击力
- `Range`：远程射程
- `Cost`：造价
- `BuildCharges`：建造次数（工人用，默认 0）
- `Maintenance`：每回合维护费

**布尔字段**
- `CanTrain`：是否可训练（勾上才能在城里造）
- `FoundCity`：是否可建城
- `MakeTradeRoute`：是否可建立商路
- `ZoneOfControl`：是否有控制区
- `CanCapture`：是否可俘获城市

### 5.5 替代单位（UnitReplaces）

在「UnitReplaces」区域中：
- `ReplacesUnitType`：选择 `UNIT_WARRIOR`（或你想替代的其他单位）
- 下拉框可搜索游戏数据库中所有已有单位

设置了替代后，你的单位会在科技树中替代原单位的位置。

### 5.6 单位类别标签（TypeTags）

决定单位在游戏中被归类为什么类型。分两部分：

**固定类别标签**（复选框）：如 `CLASS_RECON`（侦察）、`CLASS_MELEE`（近战）、`CLASS_NAVAL_MELEE`（海军近战）等，直接勾选即可。

**数据库的其他 Tag**（搜索添加）：点击「添加」按钮，搜索游戏数据库中已有的 Tag（如 `CLASS_ANTI_CAVALRY`）。

### 5.7 TypeProperties（特殊属性）

这个表用于设置单位的特殊属性，如英雄的寿命、是否可以传送到城市等。

- 点击「＋ 添加行」
- Name 列下拉框显示已知属性名（带中文说明），也可以手输自定义属性名
- Value 列会随 Name 自动变化：布尔属性显示复选框，数字属性显示数字框，自定义 Name 显示文本输入框

常用属性举例：
- `LIFESPAN`（寿命）：英雄单位的存活回合数
- `CAN_EVER_TRAIN_BARBARIAN`：蛮族模式是否可训练
- `CAN_TELEPORT_TO_CITY`：是否可传送到城市

---

## 6. 建筑

### 6.1 你要做什么

创建一个建筑——比如一个替代纪念碑（Monument）的独特建筑。

### 6.2 新建建筑

在左侧树中右键 **建筑** → **新增条目**。

### 6.3 关键字段

建筑的主表字段比单位少得多：

| 字段 | 说明 |
|------|------|
| `Name` / `Description` | 建筑名和描述 |
| `PrereqDistrict` | 必须建在哪个区域中，如 `DISTRICT_CITY_CENTER` |
| `PrereqTech` / `PrereqCivic` | 解锁条件 |
| `Cost` | 造价 |
| `Maintenance` | 维护费 |
| `TraitType` | 建筑特质（用于挂修改器） |

### 6.4 建筑子表

建筑有多行子表，用于定义建筑的额外效果：

| 子表 | 说明 |
|------|------|
| **Building_YieldChanges** | 基础产出加成（如 +2 文化） |
| **Building_GreatPersonPoints** | 每回合伟人点数 |
| **Building_GreatWorks** | 巨作槽位（类型和数量） |
| **Building_ValidTerrains / Building_ValidFeatures** | 放置地形/地貌限制 |
| **Building_RequiredFeatures** | 要求的地貌条件 |
| **Building_ResourceCosts** | 建造时的资源消耗 |
| **BuildingPrereqs** | 前置建筑要求 |

以 `Building_YieldChanges` 为例：
- 点击「＋ 添加行」
- `YieldType`：下拉选择产出类型（如 `YIELD_CULTURE`）
- `YieldChange`：数值（如 `2` 代表 +2 文化）

多行表支持添加多行，每行一个效果。不需要的效果表直接忽略即可。

---

## 7. 区域

### 7.1 你要做什么

创建一个特色区域（Unique District）。

### 7.2 新建区域

在左侧树中右键 **区域** → **新增条目**。

### 7.3 关键字段

| 字段 | 说明 |
|------|------|
| `Name` / `Description` | 区域名和描述 |
| `DistrictType` | 自动生成，格式 `DISTRICT_<前缀>_<中缀>` |
| `PrereqTech` / `PrereqCivic` | 解锁条件 |
| `Cost` | 造价 |
| `CostProgressionModel` | 造价增长模式（一般默认） |
| `MaxPerPlayer` | 每个玩家最多几个（一般 `1`） |
| `RequiresPlacement` | 是否需要放置在地块上 |
| `RequiresPopulation` | 是否需要人口支持 |
| `TraitType` | 区域特质 |

### 7.4 区域子表

| 子表 | 说明 |
|------|------|
| **District_CitizenYieldChanges** | 公民产出 |
| **District_GreatPersonPoints** | 伟人点数 |
| **District_ValidTerrains** | 可放置地形 |
| **District_RequiredFeatures** | 要求地貌 |
| **ExcludedDistricts** | 排斥的区域 |

### 7.5 相邻加成

区域可以定义相邻地块带来的产出加成。在「相邻加成」编辑器中：
1. 选择加成类型（自动 / 自定义）
2. 选择产出类型和加成数值
3. 配置触发条件（相邻什么地块、什么地貌等）

相邻加成会生成到 `Adjacency_YieldChanges` 表中，ModTools 会自动处理。

---

## 8. 改良设施

### 8.1 你要做什么

创建一个改良设施——工人可以在地块上建造的东西。

### 8.2 新建改良设施

在左侧树中右键 **改良设施** → **新增条目**。

### 8.3 关键字段

| 字段 | 说明 |
|------|------|
| `Name` / `Description` | 改良设施名和描述 |
| `PrereqTech` / `PrereqCivic` | 解锁条件 |
| `TraitType` | 绑在文明上的特质（格式 `TRAIT_CIVILIZATION_xxx`） |
| `BuildOnFrontier` | 国境线外也可建造 |

### 8.4 改良设施子表

| 子表 | 说明 |
|------|------|
| **Improvement_YieldChanges** | 基础产出加成 |
| **Improvement_BonusYieldChanges** | 科技/市政解锁后的额外产出加成 |
| **Improvement_ValidTerrains / ValidFeatures / ValidResources** | 建造条件：允许在什么地形/地貌/资源上造 |
| **Improvement_ValidAdjacentTerrains / ValidAdjacentResources** | 相邻条件：邻近什么地形/资源才能造 |
| **Improvement_Tourism** | 旅游业绩产出 |
| **TypeProperties** | 特殊属性（如走入伤害、视野控制等） |

以 `Improvement_ValidTerrains` 为例：添加行后，`TerrainType` 下拉搜索（如 `TERRAIN_GRASS` 草地、`TERRAIN_PLAINS` 平原），`PrereqTech` 和 `PrereqCivic` 可留空（表示无额外条件）。

---

## 9. 修改器系统

### 9.1 什么是修改器

修改器（Modifier）是文明6 Mod 的核心机制。简单理解：

- **Modifier** = 一个效果（如"+5 战斗力"）
- **RequirementSet** = 一组条件（如"当攻击城市时"）
- **Requirement** = 单个条件
- Modifier + RequirementSet = "当条件满足时，产生效果"

### 9.2 挂载方式

Modifier 不直接写进对象表，而是通过"挂载"绑定：

**间接挂载（常用）**
```
对象（文明/领袖/区域/建筑/单位/改良）
  → TraitType
    → TraitModifiers (TraitType → ModifierId)
      → Modifiers
```

**直接挂载（特定对象）**
- `BuildingModifiers`：建筑直接挂 Modifier
- `DistrictModifiers`：区域直接挂 Modifier
- `UnitAbilityModifiers`：单位能力挂 Modifier
- `PolicyModifiers`：政策卡挂 Modifier

### 9.3 在 ModTools 中操作

点击左侧树中的 **修改器** 页。

**创建 Modifier**
1. 在「Modifiers」表格中新增一行
2. `ModifierType`：选择效果类型，如 `MODIFIER_PLAYER_UNITS_ADJUST_COMBAT_STRENGTH`
3. `RunOnce`：是否只运行一次
4. `Permanent`：是否永久生效
5. 参数表：根据 EffectType 填入参数（如 `Amount=5` 代表 +5 战斗力）

**创建 RequirementSet**
1. 在「RequirementSets」表格中新增一行
2. 在「Requirements」表格中添加条件行，每个 Requirement 选择 `RequirementType` 和填入参数

**挂载到对象**
1. 在挂载工具区选择目标对象和 Modifier
2. ModTools 自动生成 `TraitModifiers` 或对应的实体 Modifier 关联 SQL

### 9.4 常用 EffectType

游戏中**真实存在**的 EffectType 有超过 2000 个。ModTools 的 EffectType 搜索功能直接查询游戏数据库，保证不会虚构。常用类别：

| 类别 | 示例 | 效果 |
|------|------|------|
| 调整产出 | `EFFECT_ADJUST_CITY_YIELD` | 城市产出变化 |
| 调整战斗力 | `EFFECT_ADJUST_PLAYER_UNIT_COMBAT` | 单位战斗力变化 |
| 免费单位 | `EFFECT_PLAYER_GRANT_UNIT` | 赠送单位 |
| 地块产出 | `EFFECT_ADJUST_PLOT_YIELD` | 地块产出修正 |
| 伟人点数 | `EFFECT_ADJUST_GREAT_PERSON_POINTS` | 伟人点数变化 |

> 不要凭记忆写 EffectType。每次都用 ModTools 的搜索功能查找确认。

---

## 10. 图标和美术

### 10.1 图标尺寸参考

不同对象类型需要的图标尺寸不同：

| 对象类型 | 图标尺寸（像素） |
|----------|-----------------|
| 文明 | 22, 30, 32, 36, 45, 48, 50, 55, 64, 80, 128, 256 |
| 领袖 | 32, 45, 50, 55, 64, 80, 128, 256 |
| 区域 | 22, 32, 38, 50, 80, 128, 256 |
| 建筑 | 38, 50, 80, 128, 256 |
| 单位 | 22, 32, 36, 45, 50, 64, 80, 128, 256 |
| 改良设施 | 38, 50, 80, 128, 256 |

### 10.2 在 ModTools 中操作

点击左侧树中的 **美术** 页。这里管理：

- **Icons.xml**：图标定义（IconTextureAtlas + IconDefinitions）
- **ArtDef**：美术定义文件
- **XLP**：领袖 XLP 配置
- **Art.xml**：美术资源配置
- **Textures**：纹理文件（PNG → DDS → TEX 链路）
- **Moments**：历史时刻插画

对于大多数 Mod 对象（文明、领袖、建筑、单位、改良），图标在主编辑器中就有图片槽位，直接选择 PNG 文件即可。ModTools 会自动处理尺寸和格式。

### 10.3 纹理链路

如果你需要导入完整的领袖美术素材，需要了解游戏使用的纹理格式：
1. PNG（原始图片）
2. DDS（DirectX 纹理格式，使用 NVIDIA Texture Tools 等工具转换）
3. TEX（游戏内部格式，由 ModBuddy 构建时自动从 DDS 生成）
4. XLP（纹理打包配置，告诉游戏各图片在纹理文件中的位置）

ModTools 的美术页可以配置这些链路，自动生成对应的 XLP 配置。

---

## 11. 文本和本地化

### 11.1 文本是怎么工作的

文明6 的文本系统使用 **LOC_ 标签**。数据库不直接存文字，而是存标签：

```
Units.Name = 'LOC_UNIT_SIQI_MYFIRSTMOD_0_NAME'
```

然后 `LocalizedText` 表中存储标签对应的真实文字：

```sql
INSERT INTO LocalizedText (Language, Tag, Text) VALUES
('zh_Hans_CN', 'LOC_UNIT_SIQI_MYFIRSTMOD_0_NAME', '近卫干员'),
('zh_Hans_CN', 'LOC_UNIT_SIQI_MYFIRSTMOD_0_DESCRIPTION', '罗德岛近战单位。');
```

### 11.2 ModTools 中的文本处理

在主编辑器填写 `Name` 和 `Description` 时，直接输入中文。ModTools 生成时会自动创建 LOC 标签并填入。

文本预览功能依赖文本数据库，如果显示"未知"请在设置页配置文本库。

### 11.3 书写规范

**名称（Name）**
- 简洁，2-6 个汉字为佳
- 如"舞会演出厅"、"近卫干员"

**描述（Description）**
- 一段话描述功能效果
- 用 `[NEWLINE]` 换行分隔不同效果层级
- 用 `[ICON_xxx]` 嵌入游戏内图标

示例：
```
提供 2 点 [ICON_Culture] 文化值。[NEWLINE]每回合获得 1 点 [ICON_GreatPerson] 大作家伟人点数。[NEWLINE]城市战斗力 +5。
```

### 11.4 通用文本字段

- `Name`：显示名称
- `Description`：百科描述
- `ShortDescription`/`Strategy`/`Civilopedia`：部分对象支持，用于 Tips 和文明百科
- `BarbarianName`/`EndGameName`/`EndGameDescription`：部分对象支持

---

## 12. 生成与部署

### 12.1 生成文件

当你编辑完所有内容后：
1. 点击左侧树中的 **工程根节点**
2. 点击「生成所有文件」
3. ModTools 会将所有 SQL/XML/图标/ArtDef 文件写入 `.civ6proj` 所在目录

也可以在**预览**区域查看即将生成的 SQL（`Units.sql` 等），确认无误后再写入。

### 12.2 已有文件处理

如果目标目录已有同名文件，ModTools 会弹出对话框让你选择：
- 覆盖（替换旧文件）
- 跳过（保留旧文件）

建议首次生成全部覆盖，之后仅覆盖修改过的文件。

### 12.3 在 ModBuddy 中构建

1. 打开 ModBuddy，打开你的 `.civ6proj` 工程
2. 检查文件是否都在 `Solution Explorer` 中出现
3. 点击 **Build → Build Solution**
4. 成功后在游戏主菜单 **额外内容** 中启用你的 Mod

### 12.4 验证

启动文明6，进入主菜单 → **额外内容** → 勾选你的 Mod → 开始游戏。

从远古时代开始，迅速进入科技/市政树查看你的对象是否出现。如果一切正常，你的文明/领袖/单位/建筑应该出现在游戏中。

---

## 13. 进阶：从数据库导入再修改

### 13.1 为什么要导入

如果你不想从零创建，而是想基于原版某个单位/建筑进行修改（比如做一个+5战斗力的勇士替代品），最方便的方式是**从游戏数据库导入**，然后在导入的基础上修改。

### 13.2 操作步骤

1. 在对应分类下（如「单位」），点击顶部的「**导入**」按钮
2. 搜索对话框弹出，输入原版对象名（如 `UNIT_WARRIOR`）
3. 选中后点击确认
4. ModTools 会从游戏数据库读取该对象的所有数据，填充到编辑器
5. Type 会自动加上你的前缀，避免和原版冲突
6. 修改你想要的字段（比如改 Combat、加一个子表行），其余保持原样

### 13.3 注意

- 导入后 Type 会变更为你的前缀，所以需要设置 `UnitReplaces` 指向原版单位
- 部分子表（如 TypeProperties）数据库不提供，导入后为空，需手动添加
- 导入的图片/图标不会自动带过来，需要自己准备

---

## 14. 其他内容类型

前文已覆盖最常用的 6 种对象。ModTools 还支持以下类型，操作模式类似：

### 14.1 伟人（GreatPeople）

伟人是游戏中的"特殊人才"——大科学家、大工程师、大商人等。每个伟人有一个特殊技能（激活后消耗）或可创作巨作。

#### 伟人编辑器结构

伟人编辑器是一个复合编辑器，包含三个子区域：

**① 伟人类别（GreatPersonClasses）**
- 选择伟人所属类别：`GREAT_PERSON_CLASS_SCIENTIST`（大科学家）、`GREAT_PERSON_CLASS_ENGINEER`（大工程师）等
- 一个伟人类别下可以有多个伟人个体

**② 简化单位（Unit）**
- 伟人在游戏中是以"单位"的形式存在的——可移动、可激活
- 需要配置基本的单位参数：移动力、视野、是否可以传送等
- 大部分伟人移动力为 2-4，视野为 2
- 如果要做"移动力为 0"的伟人（如原地站桩型），把 `BaseMoves` 设为 0

**③ 伟人个体（GreatPersonIndividuals）**

伟人个体分两种类型：

**激活类**：有一个主动技能，使用后伟人消失
- 填写 `ActionEffectType`（效果类型）和 `ActionEffectValue`（效果数值）
- 比如：`EFFECT_GRANT_RANDOM_TECH_BOOST` + 数值 1 = 随机触发一个科技的尤里卡
- 效果通过修改器系统实现，需在修改器页创建对应的 Modifier

**巨作类**：可以创作巨作（GreatWork）
- 设置巨作类型（宗教/文学/音乐等）
- 对应的巨作槽位在建筑表中定义

#### 实际案例：自定义伟人"稀音"

假设你要做一个特殊的伟人——不是放在标准伟人池中，而是一个独特的"英雄型"伟人：

1. 在「伟人」下新增条目
2. 伟人类别：新建或选择一个已有类别
3. 简化单位：设置 `BaseMoves=0`（不能移动），`BaseSightRange=2`
4. 伟人个体：选择「激活类」，配置特殊技能
5. 技能效果——比如"位于自然奇观旁边时记录该奇观"——需要配合 Lua 脚本来实现复杂的触发逻辑（见 [番外篇：UI 和 Lua](#番外篇ui-和-lua)）
6. 光环类效果——比如"3 环内军事单位 +5 战斗力"——通过修改器系统挂到伟人的 Trait 上

关键点：伟人的复杂交互（如"主动记录奇观""每种奇观仅一次"）通常需要 Lua 辅助。ModTools 负责生成伟人的数据库定义，Lua 负责实现特殊逻辑。

### 14.2 政策卡（Policy）

政策卡是政体系统的一部分，挂在政体的槽位上提供加成。

**主表关键字段**：
| 字段 | 说明 |
|------|------|
| `Name` / `Description` | 政策卡名和描述 |
| `GovernmentSlotType` | 槽位类型：`SLOT_MILITARY`（军事）、`SLOT_ECONOMIC`（经济）、`SLOT_DIPLOMATIC`（外交）、`SLOT_WILDCARD`（万能） |
| `PrereqCivic` | 解锁市政 |

政策卡的效果通过修改器实现（`PolicyModifiers` 表）。ModTools 的修改器页支持直接挂载到政策卡。

### 14.3 项目（Project）

城市项目是城市可以执行的临时任务（如"建造核弹""狂欢节"）。

**主表关键字段**：
| 字段 | 说明 |
|------|------|
| `Name` / `Description` | 项目名和描述 |
| `Cost` | 基础造价 |
| `CostProgressionModel` | 造价增长模型 |
| `PrereqTech` / `PrereqCivic` | 解锁条件 |
| `MaxPlayerInstances` | 每个玩家最多执行次数（填 1 为只能一次） |

**项目子表**：
- `Project_BuildingCosts`：需要消费的建筑
- `Project_GreatPersonPoints`：完成后获得的伟人点数
- `Project_ResourceCosts`：执行需要的资源
- `Project_YieldConversions`：生产转换率（把城市生产力转化为其他产出）
- `ProjectPrereqs`：前置项目

项目完成后的奖励效果通过 `ProjectCompletionModifiers` 挂载修改器。

### 14.4 单位晋升（UnitPromotions）

晋升树编辑器支持两种模式：
- **树形**：卡片拖拽定位（Level 1→4），上下端口连线建立前置关系。支持 2221 / 2212 一键模板
- **随机**：按 Level 分组列表排列

晋升节点自动注册到修改器的 `UnitPromotionModifiers`。

### 14.5 总督（Governor）

总督晋升树的卡片可视化编辑器 + 圆形裁切头像。需要配置总督类型 + 各层级晋升效果，效果通过 `GovernorPromotionModifiers` 挂载修改器。

### 14.6 议程（Agenda）

领袖的 AI 行为倾向。包含议程主表、独家议程、议程修饰符、AI 列表。配合领袖的 `AgendaType` 字段使用。

### 14.7 信仰（Religion）

信仰主表 + 信仰修改器绑定。一般较少自制，多数 Mod 通过修改建筑/文明的信仰相关字段来实现宗教效果。

所有类型的操作模式都一致：**新增/导入 → 填表 → 生成**，学完前几章后应该能触类旁通。

---

## 15. 常见问题排解

### 中文显示"未知"

设置页没配文本数据库，或没导入 DLC 文本。重新配置即可。

### 生成时提示"请先导入 .civ6proj"

基础信息页没选择 ModBuddy 工程文件。

### 生成时提示必填字段缺失

检查编辑器中标 `*` 的字段是否有值。常见遗漏：单位的 `FormationClass`。

### 游戏中看不到我的 Mod

1. 检查 ModBuddy 中 Build 是否成功
2. 检查主菜单「额外内容」中 Mod 是否启用
3. 检查类型名是否有前缀，避免和原版重名
4. 查看 `Documents\My Games\Sid Meier's Civilization VI\Logs\Database.log`，搜索 `ERROR` 关键字找 SQL 错误

### 修改器不生效

1. 确认 EffectType / RequirementType 在游戏数据库中真实存在（用 ModTools 搜索验证）
2. 检查 TraitModifiers 是否正确关联
3. 检查 RequirementSetId 的拼写
4. OwnerRequirementSetId 和 SubjectRequirementSetId 搞反了：Owner 决定"触不触发"，Subject 决定"作用在谁身上"

### 图标不显示

1. 确认 Icons.xml 中的 Atlas 定义和纹理文件匹配
2. 确认 `<IconDefinitions>` 中的 `Index` 从 0 开始递增
3. 确认纹理文件（DDS/TEX）已放入正确的文件夹
4. 启动游戏时加了 `--no-tex` 参数需要去掉

### 游戏启动崩溃

大概率是 SQL 语法错误或 XML 格式错误。检查日志：`Documents\My Games\Sid Meier's Civilization VI\Logs\Modding.log` 和 `Database.log`。

### 我的文明6装D盘，影响使用吗

不影响。游戏 Cache 永远在 C 盘 `%LOCALAPPDATA%`，跟安装位置无关。ModTools 配置文件里手动选一次数据库路径即可。

### 图片缩到比画布小，导出还是撑满的

在 ModTools 图片槽位中重新选择一次图片即可（编辑器已修复导出端缩放问题，旧状态需要刷新）。

---

## 附录：命名规则速查

| 对象 | Type 前缀 | 特质前缀 | 示例 |
|------|-----------|----------|------|
| 文明 | `CIVILIZATION_` | `TRAIT_CIVILIZATION_` | `CIVILIZATION_SIQI_MYMOD_0` |
| 领袖 | `LEADER_` | `TRAIT_LEADER_` | `LEADER_SIQI_MYMOD_0` |
| 区域 | `DISTRICT_` | `TRAIT_DISTRICT_` | `DISTRICT_SIQI_MYMOD_0` |
| 建筑 | `BUILDING_` | `TRAIT_BUILDING_` | `BUILDING_SIQI_MYMOD_0` |
| 单位 | `UNIT_` | `TRAIT_UNIT_` | `UNIT_SIQI_MYMOD_0` |
| 改良设施 | `IMPROVEMENT_` | `TRAIT_CIVILIZATION_` | `IMPROVEMENT_SIQI_MYMOD_0` |
| 政策卡 | `POLICY_` | — | `POLICY_SIQI_MYMOD_0` |
| 项目 | `PROJECT_` | — | `PROJECT_SIQI_MYMOD_0` |

> 改良设施的特质绑在**文明**上（`TRAIT_CIVILIZATION_`），与建筑/区域的独立特质不同。这是由游戏机制决定的——改良设施通过文明特质解锁，而不是改良设施本身拥有特质。

---

祝你制作愉快。有问题或建议欢迎反馈。
