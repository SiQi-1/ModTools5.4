# 城邦宗主国 Modifier 注入模式 (Suzerain Modifier Pattern)

> 来源：CityStatesDiversity (2652224074) + BetterCityStates (2495851756)
> 核心文件：`Core/Database.sql`, `base/citystates.lua`, `UI/BST/citystates.lua`

## 1. 系统概述

为城邦新增宗主国（Suzerain）加成时，传统做法是把 Modifier 挂到 `TraitModifiers` 表上（如 `MINOR_CIV_SCIENTIFIC_TRAIT`），但这样**所有该类型城邦都会共享同一个加成**。

要做"每个城邦独有"的宗主国加成，核心技术是**临时表自动注入模式**：

```
自定义 Trait → TraitAttachedModifiers (临时表) → 自动生成 ATTACH Modifier
→ 自动挂 TraitModifiers → 运行时检测 PLAYER_IS_SUZERAIN
```

---

## 2. 核心 SQL 模式

### 2.1 三步自动注入法

```sql
-- 第一步：创建临时表，声明 Trait 与 Modifier 的绑定关系
CREATE TEMPORARY TABLE IF NOT EXISTS TraitAttachedModifiers (
    TraitType  TEXT NOT NULL,
    ModifierId TEXT NOT NULL,
    PRIMARY KEY (TraitType, ModifierId)
);

INSERT OR REPLACE INTO TraitAttachedModifiers (TraitType, ModifierId)
VALUES
    ('MINOR_CIV_CSD_KIEV_TRAIT',    'MINOR_CIV_CSD_KIEV_GROWTH_RATE_AT_PEACE'),
    ('MINOR_CIV_CSD_KIEV_TRAIT',    'MINOR_CIV_CSD_KIEV_PRODUCTION_AT_WAR');

-- 第二步：定义实际的 Modifier（如产出加成、生产加速等）
INSERT OR REPLACE INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId)
VALUES
    ('MINOR_CIV_CSD_KIEV_GROWTH_RATE_AT_PEACE',
     'MODIFIER_PLAYER_CITIES_ADJUST_CITY_GROWTH',
     'PLAYER_IS_AT_PEACE_WITH_ALL_MAJORS');

INSERT OR REPLACE INTO ModifierArguments (ModifierId, Name, Value)
VALUES ('MINOR_CIV_CSD_KIEV_GROWTH_RATE_AT_PEACE', 'Amount', 7);

-- 第三步（最后统一执行）：自动生成 ATTACH Modifier 并挂到 TraitModifiers
INSERT OR IGNORE INTO TraitModifiers (TraitType, ModifierId)
SELECT TraitType, ModifierId || '_ATTACH'
FROM TraitAttachedModifiers;

INSERT OR IGNORE INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId)
SELECT ModifierId || '_ATTACH',
       'MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER',
       'PLAYER_IS_SUZERAIN'
FROM TraitAttachedModifiers;

INSERT OR IGNORE INTO ModifierArguments (ModifierId, Name, Value)
SELECT ModifierId || '_ATTACH', 'ModifierId', ModifierId
FROM TraitAttachedModifiers;

DROP TABLE TraitAttachedModifiers;
```

### 2.2 原理说明

| 步骤 | 说明 |
|------|------|
| `TraitAttachedModifiers` | 临时表，记录"哪个 Trait 拥有哪些 Modifier" |
| `_ATTACH` Modifier | 每个原始 Modifier 自动生成一个 ATTACH 版本，ModifierType = `MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER` |
| `PLAYER_IS_SUZERAIN` | SubjectRequirementSetId，确保只有**成为该城邦宗主国**的玩家才获得加成 |
| `TraitModifiers` 绑定 | ATTACH Modifier 挂到对应 Trait 上，游戏加载时生效 |
| 最后 DROP | 清理临时表，不影响其他 SQL 文件 |

### 2.3 完整示例：新增自定义城邦 "基辅"

```sql
-- 定义 Modifier
INSERT INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId)
VALUES
    ('MY_KIEV_GROWTH',  'MODIFIER_PLAYER_CITIES_ADJUST_CITY_GROWTH', 'PLAYER_IS_AT_PEACE_WITH_ALL_MAJORS');

INSERT INTO ModifierArguments (ModifierId, Name, Value)
VALUES
    ('MY_KIEV_GROWTH', 'Amount', 10);

-- 挂到临时表
INSERT INTO TraitAttachedModifiers (TraitType, ModifierId)
VALUES ('MINOR_CIV_MY_KIEV_TRAIT', 'MY_KIEV_GROWTH');
```

---

## 3. 常用 Modifier 类型参考

### 3.1 产出调整类

| ModifierType | 用途 | 参数 |
|---|---|---|
| `MODIFIER_PLAYER_ADJUST_PLOT_YIELD` | 调整地块产出 | YieldType, Amount |
| `MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_MODIFIER` | 城市产出百分比加成 | YieldType, Amount |
| `MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_CHANGE` | 城市产出固定值加成 | YieldType, Amount |
| `MODIFIER_CITY_PLOT_YIELDS_ADJUST_PLOT_YIELD` | 调整单个城市地块产出 | YieldType, Amount |
| `MODIFIER_PLAYER_DISTRICTS_ADJUST_YIELD_CHANGE` | 区域产出调整 | YieldType, Amount |
| `MODIFIER_SINGLE_CITY_ADJUST_TRADE_ROUTE_YIELD_TO_OTHERS` | 商路对他人产出 | YieldType, Amount, Domestic |
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_FOR_INTERNATIONAL` | 国际商路产出 | YieldType, Amount |
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_FOR_DOMESTIC` | 国内商路产出 | YieldType, Amount |

### 3.2 生产/建造加速类

| ModifierType | 用途 | 参数 |
|---|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_DISTRICT_PRODUCTION` | 区域建造加速 | DistrictType, Amount |
| `MODIFIER_PLAYER_CITIES_ADJUST_BUILDING_PRODUCTION` | 建筑建造加速 | DistrictType, Amount |
| `MODIFIER_PLAYER_CITIES_ADJUST_ALL_DISTRICTS_PRODUCTION` | 所有区域加速 | Amount |
| `MODIFIER_PLAYER_CITIES_ADJUST_SPACE_RACE_PROJECTS_PRODUCTION` | 太空项目加速 | Amount |

### 3.3 伟人/人口/宜居度类

| ModifierType | 用途 | 参数 |
|---|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_GREAT_PERSON_POINT` | 伟人点数 | GreatPersonClassType, Amount |
| `MODIFIER_PLAYER_CITIES_ADJUST_CITY_GROWTH` | 城市成长速度 | Amount |
| `MODIFIER_PLAYER_CITIES_ADJUST_TRAIT_AMENITY` | 宜居度 | Amount |
| `MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_PER_POPULATION` | 按人口产出 | YieldType, Amount |

### 3.4 单位能力类

| ModifierType | 用途 | 参数 |
|---|---|---|
| `MODIFIER_PLAYER_UNITS_GRANT_ABILITY` | 授予单位能力（需配套 Type/Ability 定义） | AbilityType |
| `MODIFIER_UNIT_ADJUST_COMBAT_STRENGTH` | 单位战斗力 | Amount |
| `MODIFIER_PLAYER_UNIT_ADJUST_UNIT_EXPERIENCE_MODIFIER` | 单位经验倍率 | Amount |
| `MODIFIER_PLAYER_TRAINED_UNITS_ADJUST_BUILDER_CHARGES` | 建造者次数 | Amount |

### 3.5 其他

| ModifierType | 用途 | 参数 |
|---|---|---|
| `MODIFIER_PLAYER_CITIES_ADJUST_PLOT_PURCHASE_COST` | 地块购买费用 | Amount |
| `MODIFIER_PLAYER_CITIES_ADJUST_PLOT_PURCHASE_COST_TERRAIN` | 特定地形地块购买费用 | TerrainType, Amount |
| `MODIFIER_PLAYER_CITIES_DISTRICT_ADJACENCY` | 区域相邻加成 | DistrictType, YieldType, Amount, Description |
| `MODIFIER_PLAYER_CITIES_IMPROVEMENT_ADJACENCY` | 改良相邻加成 | DistrictType, ImprovementType, YieldType, Amount, Description |

---

## 4. 多层 Modifier 链（Attach 模式）

当需要"满足条件 A 时给城市挂 Modifier B，B 再影响地块"时，使用**嵌套 Attach**：

```sql
-- 外层：检查城市是否有港口，有则挂内层 Modifier
INSERT INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId)
VALUES ('RIGA_SCIENCE_TIER1',
        'MODIFIER_PLAYER_CITIES_ATTACH_MODIFIER',
        'CITY_HAS_DISTRICT_HARBOR_TIER_1_BUILDING_REQUIREMENTS');

-- 内层：实际效果（国际商路产出科研）
INSERT INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId)
VALUES ('RIGA_SCIENCE_TIER1_MODIFIER',
        'MODIFIER_SINGLE_CITY_ADJUST_TRADE_ROUTE_YIELD_FOR_INTERNATIONAL',
        NULL);

-- ModifierArguments：外层传 ModifierId 指向内层
INSERT INTO ModifierArguments (ModifierId, Name, Value)
VALUES ('RIGA_SCIENCE_TIER1', 'ModifierId', 'RIGA_SCIENCE_TIER1_MODIFIER');
```

**链式结构**：`Suzerain ATTACH → CITY_ATTACH → 内层 Modifier`

---

## 5. 授予单位特殊能力（Ability 模式）

用于通过城邦宗主国身份给特定单位类型加能力：

```sql
-- 1) 定义 Ability 类型
INSERT INTO Types (Type, Kind) VALUES ('ABILITY_MY_BONUS', 'KIND_ABILITY');

-- 2) 给 Ability 打标签（限定单位类型）
INSERT INTO TypeTags (Type, Tag)
VALUES
    ('ABILITY_MY_BONUS', 'CLASS_NAVAL_MELEE'),
    ('ABILITY_MY_BONUS', 'CLASS_NAVAL_RAIDER');

-- 3) 注册 Ability（默认不激活）
INSERT INTO UnitAbilities (UnitAbilityType, Inactive)
VALUES ('ABILITY_MY_BONUS', 1);

-- 4) Ability 的 Modifier
INSERT INTO UnitAbilityModifiers (UnitAbilityType, ModifierId)
VALUES ('ABILITY_MY_BONUS', 'MY_BONUS_COMBAT_MODIFIER');

-- 5) 宗主国 ATTACH 授予 Ability
INSERT INTO Modifiers (ModifierId, ModifierType)
VALUES ('MY_SUZERAIN_ABILITY', 'MODIFIER_PLAYER_UNITS_GRANT_ABILITY');

INSERT INTO ModifierArguments (ModifierId, Name, Value)
VALUES ('MY_SUZERAIN_ABILITY', 'AbilityType', 'ABILITY_MY_BONUS');
```

---

## 6. 城邦 UI 面板模式（BetterCityStates）

BetterCityStates 是城邦面板 UI 的增强版，核心概念：

### 6.1 面板模式切换

```lua
local MODE = {
    Overview      = "Overview",      -- 列表总览
    SendEnvoys    = "SendEnvoys",    -- 派遣使者
    EnvoySent     = "EnvoySent",     -- 单个城邦详情
    InfluencedBy  = "InfluencedBy",  -- 谁影响了此城邦
    Quests        = "Quests",        -- 城邦任务
    Relationships = "Relationships"  -- 外交关系
}
```

### 6.2 关键 API

```lua
-- 获取城邦列表
local pPlayer = Players[localPlayerID];
local pInfluence = pPlayer:GetInfluence();

-- 使者相关
pInfluence:GetPointsEarned()       -- 影响力点数
pInfluence:GetPointsPerTurn()      -- 每回合影响力
pInfluence:GetPointsThreshold()    -- 阈值
pInfluence:GetTokensToGive()       -- 可用使者数
pInfluence:GetTokensPerThreshold() -- 每阈值使者数

-- 派遣使者操作
UI.RequestPlayerOperation(playerID, PlayerOperations.GIVE_INFLUENCE_TOKEN, {
    [PlayerOperations.PARAM_PLAYER_ONE] = cityStatePlayerID
});

-- 获取宗主国加成文本
local leader = PlayerConfigurations[playerID]:GetLeaderTypeName();
for leaderTraitPairInfo in GameInfo.LeaderTraits() do
    if leader == leaderTraitPairInfo.LeaderType then
        local traitInfo = GameInfo.Traits[leaderTraitPairInfo.TraitType];
        -- traitInfo.Description 即宗主国加成描述
    end
end
```

### 6.3 城邦类型判断

```lua
local leaderInfo = GameInfo.Leaders[leader];
if leaderInfo.InheritFrom == "LEADER_MINOR_CIV_SCIENTIFIC" then
    -- 科技城邦
end
```

---

## 7. 动态 SQL 生成模式

CityStatesDiversity 大量使用 `INSERT ... SELECT` 从现有数据动态生成新数据：

```sql
-- 示例：为所有畜牧业/狩猎营地的资源自动生成 Modifier
CREATE TEMPORARY TABLE CatalhoyukResources (ResourceType TEXT NOT NULL PRIMARY KEY);

INSERT INTO CatalhoyukResources (ResourceType)
SELECT ResourceType FROM Improvement_ValidResources
WHERE ImprovementType = 'IMPROVEMENT_PASTURE' OR ImprovementType = 'IMPROVEMENT_CAMP';

-- 然后遍历临时表生成 Modifier
INSERT INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId)
SELECT 'MY_BONUS_' || ResourceType,
       'MODIFIER_PLAYER_CITIES_ATTACH_MODIFIER',
       'MY_CITY_HAS_' || ResourceType || '_REQUIREMENTS'
FROM CatalhoyukResources;

DROP TABLE CatalhoyukResources;
```

---

## XML 配合

### CityStatesDiversity (2652224074)

纯 SQL 数据库驱动，无独立 XML UI。城邦面板文本通过外挂的 `LocalizedText` 条目呈现。SpecialtyDistrict 等额外区域定义在 `Core/Database.sql` 中。

### BetterCityStates (2495851756)

城邦 UI 面板增强，通过 `citystates.xml` 文件定义面板模式切换的控件布局。主要容器结构：
- 面板模式在 `MODE` 表中定义 (`Overview`, `SendEnvoys`, `EnvoySent`, `InfluencedBy`, `Quests`, `Relationships`)
- 控件通过 `ContextPtr:LookUpControl("/InGame/..."` 挂接到游戏内置城邦面板
- Lua 文件 `UI/BST/citystates.lua` 负责面板逻辑，`base/citystates.lua` 负责数据获取

### 文本定义

两种城邦 Mod 的文本均在 SQL 文件中通过 `LocalizedText INSERT` 定义（非 XML），包括城邦名称、宗主国加成描述等。

---

## 8. 条件检测 DLC 存在

```sql
-- 仅在 DLC 存在时插入数据（如外交区）
INSERT INTO TraitAttachedModifiers (TraitType, ModifierId)
SELECT 'MINOR_CIV_CSD_VIENNA_TRAIT', 'MY_VIENNA_DIPLO_BONUS'
WHERE EXISTS (
    SELECT DistrictType FROM Districts
    WHERE DistrictType = 'DISTRICT_DIPLOMATIC_QUARTER'
);
```

---

## 9. 关键提醒

- **ATTACH Modifier 名称约定**：`原始ModifierId || '_ATTACH'`
- **PLAYER_IS_SUZERAIN** 是游戏内置的 RequirementSet，检查玩家是否是该城邦宗主国
- **临时表**（`TEMPORARY TABLE`）仅在当前数据库连接有效，不影响其他 Mod
- **自定义城邦**需要完整的 Civilization + Leader + Trait + 起始加成定义
- Ability 的 `Inactive = 1` 表示该能力默认不显示/不生效，由 Modifier 激活
