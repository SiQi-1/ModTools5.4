# Civ 6 Mod 代码规范

## 一、文件夹结构

```
<ModName>/
├── <ModName>.civ6proj           ← ModBuddy 工程（自动生成，不手改）
├── <ModName>.civ6sln            ← 解决方案（自动生成，不手改）
├── <ModName>.dep                ← 依赖声明（自动生成，不手改）
│
├── Data/                        ← 所有数据库 SQL
│   ├── <ModName>_Civilizations.sql
│   ├── <ModName>_Leaders.sql
│   ├── <ModName>_Buildings.sql
│   ├── <ModName>_Districts.sql
│   ├── <ModName>_Units.sql
│   ├── <ModName>_UnitAbilities.sql
│   ├── <ModName>_UnitPromotions.sql
│   ├── <ModName>_Improvements.sql
│   ├── <ModName>_Governors.sql
│   ├── <ModName>_Policies.sql
│   ├── <ModName>_Projects.sql
│   ├── <ModName>_Modifiers.sql
│   ├── <ModName>_Colors.sql
│   ├── <ModName>_Configs.sql    ← Players / PlayerItems 注册
│   └── <ModName>_Moments.sql
│
├── Text/
│   ├── <ModName>_Text_CN.sql
│   └── <ModName>_UIText_CN.sql  ← 有 UI 时
│
├── Scripts/
│   └── <ModName>_Scripts.lua    ← GP 端
│
├── UI/
│   ├── <ModName>_UI.lua
│   └── <ModName>_UI.xml
│
├── Import/                      ← 复杂 Lua 时用
│   ├── <ModName>_Core.lua
│   └── <ModName>_Support.lua
│
├── Icons/
│   └── <ModName>_Icons.xml
│
├── ArtDefs/
│   ├── Buildings.artdef
│   ├── Civilizations.artdef
│   ├── Leaders.artdef
│   ├── Units.artdef
│   ├── Districts.artdef
│   └── Improvements.artdef
│
├── XLPs/
│   ├── <ModName>_dds.xlp
│   ├── LeaderFallback.xlp
│   └── tilebases.xlp
│
├── IMG/                         ← 原始图片（用户提供）
├── Textures/                    ← 编译纹理（用户提供）
└── Platforms/Windows/Audio/     ← 音频（有则）
```

### 文件存在条件

| 文件 | 条件 |
|------|------|
| `_Civilizations.sql` | 有文明 |
| `_Leaders.sql` | 有领袖 |
| `_Buildings.sql` | 有建筑 |
| `_Districts.sql` | 有区域 |
| `_Units.sql` | 有单位 |
| `_UnitAbilities.sql` | 有单位能力（几乎必写） |
| `_UnitPromotions.sql` | 有单位晋升 |
| `_Improvements.sql` | 有改良 |
| `_Governors.sql` | 有总督 |
| `_Policies.sql` | 有政策卡 |
| `_Projects.sql` | 有项目 |
| `_Modifiers.sql` | 总是需要（几乎所有 Mod 都有 Modifier） |
| `_Colors.sql` | 有自定义文明/领袖颜色 |
| `_Configs.sql` | 新文明/领袖需要注册 Players+PlayerItems |
| `_Moments.sql` | 有时刻插图 |
| `Scripts/` | 有 GP 端 Lua 逻辑 |
| `UI/` | 有 UI 改动 |
| `Import/` | Lua 跨文件复用 |
| `Icons/` | 有自定义图标 |
| `ArtDefs/` | 有新模型/自定义美术 |
| `XLPs/` | 有自定义纹理 |

---

## 二、变量命名规范

### 2.1 前缀体系（Type 标识符头部）

所有 INSERT INTO Types (Type, Kind) 的 Type 字段遵循：

```
<TYPE_KIND>_SIQI_<IDENTIFIER>
```

| 前缀 | Kind | 用途 |
|------|------|------|
| `CIVILIZATION_` | `KIND_CIVILIZATION` | 文明 |
| `LEADER_` | `KIND_LEADER` | 领袖 |
| `TRAIT_CIVILIZATION_` | `KIND_TRAIT` | 文明特质 |
| `TRAIT_LEADER_` | `KIND_TRAIT` | 领袖特质 |
| `TRAIT_BUILDING_` | `KIND_TRAIT` | 建筑特质（特色建筑时） |
| `TRAIT_DISTRICT_` | `KIND_TRAIT` | 区域特质（特色区域时） |
| `TRAIT_UNIT_` | `KIND_TRAIT` | 单位特质（特色单位时） |
| `TRAIT_IMPROVEMENT_` | `KIND_TRAIT` | 改良特质（特色改良时） |
| `TRAIT_GOVERNOR_` | `KIND_TRAIT` | 总督特质 |
| `BUILDING_` | `KIND_BUILDING` | 建筑 |
| `DISTRICT_` | `KIND_DISTRICT` | 区域 |
| `UNIT_` | `KIND_UNIT` | 单位 |
| `IMPROVEMENT_` | `KIND_IMPROVEMENT` | 改良设施 |
| `GOVERNOR_` | `KIND_GOVERNOR` | 总督 |
| `POLICY_` | `KIND_POLICY` | 政策卡 |
| `PROJECT_` | `KIND_PROJECT` | 项目 |
| `ABILITY_` | `KIND_ABILITY` | 单位能力 |
| `MODIFIER_` | `KIND_MODIFIER` | 效果器 |

### 2.2 实体命名：从文件夹名推导

文件夹名和变量前缀必须对应。推导规则：

```
文件夹:  Siqi_Leaders_0035
         ~~~~ ~~~~~~~~ ~~~~
         前缀   类型    编号

简称推导:
  文明 = C0035     (C = Civilization)
  领袖 = L0035     (L = Leader)
  建筑 = B0035     (B = Building)
  区域 = D0035     (D = District)
  单位 = U0035     (U = Unit)
   改良 = I0035     (I = Improvement)
  总督 = GOV0035   (GOV = Governor)
  政策 = P0035     (P = Policy)
  项目 = PRJ0035   (PRJ = Project)

实际 Type 示例:
  CIVILIZATION_SIQI_C0035_1     ← 文明，第 1 个
  LEADER_SIQI_L0035_1           ← 领袖，第 1 个
  BUILDING_SIQI_B0035_1         ← 建筑，第 1 个
  BUILDING_SIQI_B0035_2         ← 建筑，第 2 个
  UNIT_SIQI_U0035_1             ← 单位，第 1 个
  DISTRICT_SIQI_D0035_1         ← 区域，第 1 个
  IMPROVEMENT_SIQI_I0035_1      ← 改良，第 1 个
  TRAIT_CIVILIZATION_SIQI_C0035 ← 文明特质（不编号）
  TRAIT_LEADER_SIQI_L0035_1     ← 领袖特质（跟随领袖编号）
  TRAIT_BUILDING_SIQI_B0035_1   ← 建筑特质（跟随建筑编号）
  TRAIT_DISTRICT_SIQI_D0035_1   ← 区域特质（跟随区域编号）
  TRAIT_UNIT_SIQI_U0035_1       ← 单位特质（跟随单位编号）
  TRAIT_IMPROVEMENT_SIQI_I0035_1 ← 改良特质（跟随改良编号）
```

**数字式命名规则：**
- 实体字母 + 项目号 + 下划线 + 实例号
- 同项目内实例号从 1 递增
- 特质不单独编号，跟随其所属实体

**语义式命名规则（Arknights 等个人作品）：**
- 数字编号替换为有意义的英文名
- 示例：`LEADER_SIQI_OBLIVIONIS`、`BUILDING_SIQI_ANOTHER_HER`
- 只在用户明确指定语义名时使用

### 2.3 ModifierId 命名

```
MODIFIER_SIQI_<项目号>_<效果描述>
```

示例：
```
MODIFIER_SIQI_0040_PLOT_YIELD_SCIENCE
MODIFIER_SIQI_0041_DISTRICT_PRODUCTION_MODIFIER
MODIFIER_SIQI_0042_GRANT_TECH_MINING
MODIFIER_SIQI_0045_ADJUST_STRENGTH_10
```

命名要素：
- `MODIFIER_SIQI_` 固定前缀
- 项目号（如 `0040`、`0042`）
- 效果描述自由命名（用下划线分隔，建议包含作用目标+动作+效果）

### 2.4 RequirementId 命名

```
REQ_SIQI_<项目号>_<条件描述>
```

示例：
```
REQ_SIQI_0040_PLOT_ADJACENT_TO_OWNER_3
REQ_SIQI_0042_PLAYER_IS_LEADER
REQ_SIQI_0042_PLOT_HAS_ANY_RESOURCE
```

### 2.5 RequirementSetId 命名

```
REQSET_SIQI_<项目号>_<条件描述>
```

示例：
```
REQSET_SIQI_0040_PLOT_ADJACENT_TO_OWNER_3
REQSET_SIQI_0042_LEADER_L0042
REQSET_SIQI_0042_PLOT_HAS_ANY_RESOURCE
```

注意：RequirementSetId 常与内部一组 Requirements 共享相同的描述部分，区别是 Set 为 `REQSET_` 前缀，单个 Requirement 为 `REQ_` 前缀。

---

## 三、LOC_ 文本键规范

### 3.1 键结构

```
LOC_<CONTEXT>_SIQI_<ENTITY_ID>_<PROPERTY>
```

### 3.2 CONTEXT 对照表

| CONTEXT | 用于 |
|---------|------|
| `CIVILIZATION_` | 文明全名、形容词 |
| `LEADER_` | 领袖名称 |
| `TRAIT_CIVILIZATION_` | 文明特质名/描述 |
| `TRAIT_LEADER_` | 领袖特质名/描述 |
| `TRAIT_BUILDING_` | 建筑特质名/描述 |
| `TRAIT_DISTRICT_` | 区域特质名/描述 |
| `TRAIT_UNIT_` | 单位特质名/描述 |
| `TRAIT_IMPROVEMENT_` | 改良特质名/描述 |
| `TRAIT_GOVERNOR_` | 总督特质名/描述 |
| `BUILDING_` | 建筑名/描述 |
| `DISTRICT_` | 区域名/描述 |
| `UNIT_` | 单位名/描述 |
| `IMPROVEMENT_` | 改良名/描述 |
| `GOVERNOR_` | 总督名/描述 |
| `POLICY_` | 政策卡名/描述 |
| `PROJECT_` | 项目名/描述 |
| `ABILITY_` | 能力描述 |
| `CITY_NAME_` | 首都名 |
| `CITIZEN_NAME_` | 市民名 |
| `LOADING_INFO_` | 加载画面文本 |
| `PEDIA_LEADERS_PAGE_` | 百科引言 |

### 3.3 PROPERTY 常用值

| PROPERTY | 用于 |
|----------|------|
| `NAME` | 名称 |
| `DESCRIPTION` | 描述 |
| `ART_THEMING` | 建筑主题文本 |
| `CAPITAL` | 首都名（搭配 `LOC_CITY_NAME_` 前缀） |

### 3.4 用法规则

- 如果实体的 LOC_ 文本和特质一样，用 `{LOC_xxx}` 引用链，不重复写文本：
  ```sql
  ('zh_Hans_CN', 'LOC_TRAIT_DISTRICT_SIQI_BALLROOM_NAME', '{LOC_DISTRICT_SIQI_BALLROOM_NAME}')
  ```
- 如果文本不同，直接写内容，不引用
- 文本中嵌入图标：`[ICON_Science]`、`[ICON_Gold]` 等
- 语言：主体只写 `zh_Hans_CN`，需要多语言时追加 `en_US`

---

## 四、SQL 文件内组织规范

### 4.1 每个 SQL 文件的 INSERT 顺序

```
1. Types               ← 总是第一个
2. Traits              ← 如果有
3. 主实体表             ← 对应文件主题
4. 实体关联表           ← Replaces / Prereqs / Traits 等
5. 实体扩展表           ← YieldChanges / GreatWorks 等
6. TypeTags             ← CLASS_ 标签
7. Abilities            ← 单位能力（UnitAbilities.sql 中）
8. UnitPromotions       ← 单位晋升（UnitPromotions.sql 中）
9. Modifiers            ← 效果定义
9. ModifierArguments    ← 效果参数
10. ModifierStrings     ← 效果预览文本
11. RequirementSets     ← 条件集
12. RequirementSetRequirements  ← 条件集成员
13. Requirements        ← 条件
14. RequirementArguments ← 条件参数
```

### 4.2 书写格式

**INSERT 格式规则：**

1. **列少（≤ 5 列）：** 表名和 VALUES 同行，值一行一条：
```sql
INSERT INTO Types (Type, Kind) VALUES
('LEADER_SIQI_L0035_1', 'KIND_LEADER');
INSERT INTO Types (Type, Kind) VALUES
('TRAIT_LEADER_SIQI_L0035_1', 'KIND_TRAIT');
```

2. **列中等（6-9 列）：** 表名和 VALUES 换行，值一行一条：
```sql
INSERT INTO Policies (PolicyType, Name, Description, PrereqCivic, GovernmentSlotType) VALUES
('POLICY_SIQI_POLICY_0001', 'LOC_...', 'LOC_...', 'CIVIC_DEFENSIVE_TACTICS', 'SLOT_MILITARY');
```

3. **列多（≥ 10 列）：** 一参数一换行，逗号紧跟值尾部：
```sql
-- ⚠️ ModifierType 必须是真实存在的类型（0035 自定义类型，Types + DynamicModifiers 已注册）
INSERT INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId) VALUES
('MODIFIER_SIQI0035_CITY_DISTRICT_ADJUST_BASE_YIELD_CHANGE',
 'MODIFIER_SIQI0035_CITY_DISTRICT_ADJUST_BASE_YIELD_CHANGE',
 'SIQI0035_IS_CAMPUS');
```

**通用规则：**
- 每段前用 `-- 中文注释` 标题说明这是哪个表/什么功能
- 每段之间空一行
- 不要空列，即使不用也要填占位值（0 或 ''）
- 布尔值用 0/1，不用 true/false
- 逗号 `,` 紧跟值尾部，换行后缩进对齐第一个值

### 4.3 Configs.sql 模板

文明/领袖必须注册到 Players：
```sql
INSERT INTO Players (Domain, CivilizationType, LeaderType, CivilizationName, LeaderName, ...)
VALUES
('Players:Expansion2_Players', 'CIVILIZATION_SIQI_XXX', 'LEADER_SIQI_XXX', 'LOC_...', 'LOC_...', ...);

INSERT INTO PlayerItems (Domain, CivilizationType, LeaderType, ...)
VALUES
('Players:Expansion2_Players', 'CIVILIZATION_SIQI_XXX', 'LEADER_SIQI_XXX', ...);
```

---

## 五、Lua 规范

### 5.1 函数命名

- 事件处理函数：驼峰 + 项目前缀
  ```lua
  function SiqiOnUnitKilledInCombat(killedPlayerID, killedUnitID, playerID, unitID)
  function SiqiPurchasePlotFromGold()
  ```
- 辅助/工具函数：下划线分隔
  ```lua
  function Siqi_GetCanBuyPlot(playerID, plotX, plotY)
  function Siqi_IsSameTable(t1, t2)
  ```

### 5.2 事件注册

统一模式：
```lua
function Initialize()
    Events.UnitKilledInCombat.Add(SiqiOnUnitKilledInCombat)
    Events.UnitGreatPersonActivated.Add(SiqiOnUnitGreatPersonActivated)
end
Events.LoadGameViewStateDone.Add(Initialize)
```

### 5.3 UI ↔ GP 通信

**UI → GP**（请求修改游戏状态）：
```lua
UI.RequestPlayerOperation(playerID, PlayerOperations.EXECUTE_SCRIPT, {
    OnStart = 'SiqiFunctionName',     -- GP 端函数名
    param1  = value1,
    param2  = value2,
})
```

**GP → UI**（通知 UI 更新）：
```lua
-- GP 端
GameEvents.SiqiEventName.Call(ePlayer, params)

-- UI 端
GameEvents.SiqiEventName.Add(SiqiEventHandler)
```

### 5.4 复杂度判断

| 条件 | 处理方式 |
|------|---------|
| 单文件、单个事件、< 100 行 | 直接写，不拆 Import |
| 多面板、多事件、> 200 行 | 引入 `SiqiGP.*` / `SiqiUI.*` 模块化 |
| UI + GP 双向通信 | 拆 GP 脚本 + UI 脚本，必要时加 Import |

---

## 六、modinfo 动作顺序

### FrontEndActions（菜单阶段）
```
1. UpdateDatabase (Configs.sql)      ← 注册 Players
2. UpdateText (Text_CN.sql)          ← 加载文本
3. UpdateIcons (LoadOrder=1000)      ← 加载图标
4. UpdateColors (Colors.sql)
5. UpdateArt (Art Dependency)
```

### InGameActions（进入游戏后）
```
1. UpdateColors (Colors.sql)
2. UpdateText (Text_CN.sql)
3. UpdateIcons (LoadOrder=1000)
4. UpdateArt (Art Dependency)
5. UpdateDatabase (LoadOrder=9999)   ← 主体 SQL
   顺序: Civilizations → Leaders → Districts → Buildings
         → Units → UnitAbilities → UnitPromotions
         → Improvements → Governors
         → Policies → Projects → Modifiers → Moments
6. AddUserInterfaces                 ← UI xml+lua
7. AddGameplayScripts                ← GP 脚本
8. ImportFiles                       ← 共享库（有则）
```

### 2.5 设计审查约束（补充）

- 没有用户明确要求时，不得为了承载效果虚构 `BUILDING_SIQI_*` 或其他实体；应优先将效果挂到官方实体的 `DistrictModifiers`、`BuildingModifiers` 或对应的 Modifier 绑定表。
- `REQUIREMENT_CITY_HAS_DISTRICT` 的 `MustBeFunctioning` 使用引擎默认值时不写入 `ModifierArguments`；只有用户明确要求覆盖默认行为时才填写。
- 官方领袖外交背景剪影使用 `<LEADER_SHORT>_4` 条目引用官方对象，不生成仿制剪影图片。
- 历史时刻图片按 ModTools 5.4 的 `456×332` 画布生成，并加入项目 UITexture XLP；`MomentIllustrations.Texture` 必须与 `Moment_<GameDataType>` 一致。

