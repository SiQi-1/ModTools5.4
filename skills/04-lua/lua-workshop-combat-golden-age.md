# lua-workshop-combat-golden-age -- 文明黄金时代系统

从工坊 Mod **GoldenAge-BNW** (2582452031) 提炼。核心模式：为每个文明定义"黄金时代"（全产出+15%）和"黑暗时代"（全产出-15%），通过嵌套 Requirement 链路判定玩家当前处于哪个时代、拥有该时代哪种科技/市政、未进入下一时代，从而精确锁定生效窗口。附带多个 Lua 子系统：单位退役加人口、资源培育、世界大战自动宣战。

---

## 快速索引

| 模式 | 核心 API / 技术 | 适用场景 |
|------|----------------|---------|
| 时代窗口锁定 | 嵌套 `REQUIREMENT_REQUIREMENTSET_IS_MET` | 精确时代判定 |
| 全产出倍率 | `MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_MODIFIER` | 百分比产出修正 |
| SQL 叉积生成 | `INSERT SELECT FROM Eras, Yields` | 为所有时代×产出组合创建 Modifier |
| 反向排除判定 | `REQUIREMENTSET_TEST_ANY` + 无下一时代科技 | 限定"未进入下一时代" |
| 自定义配置表 | `CREATE TABLE GA_Resource_Cultivation` | 资源→培育设施映射 |
| 地块归属刷新 | `WorldBuilder.CityManager():SetPlotOwner` | Lua 中刷新地块所属 |
| 单位退役换人口 | `CityManager.GetCityAt + ChangePopulation + Kill` | 单位转化为城市人口 |
| UI→GP 暴露函数 | `ExposedMembers.DEMO.SacrificeUnitInCity` | 跨上下文函数调用 |
| 全局自动宣战 | `PlayerManager.GetAliveMajors` + `DeclareWarOn` | 世界大战自动化 |
| 游戏参数注册 | `Parameters + DomainValues + ParameterCriteria` | 多层级配置选项 |

---

## 一、时代窗口锁定系统（纯 SQL 核心）

### 1.1 设计目标

每个文明获得两个自定义 Trait：
- **黄金时代 BUFF**：在文明的历史黄金时期，所有城市产出 +15%
- **黑暗时代 DEBUFF**：在文明的历史衰落时期，所有城市产出 -15%

需要精确判定"玩家当前处于哪个时代"，且 BUFF/DEBUFF 只在对应时代**且尚未进入下一时代**时生效。

### 1.2 判定链路设计

```
┌─────────────────────────────────────────────────────┐
│ GOLDEN_PLAYER_HAS_ERA_CLASSICAL_ANY_TECH_CIVIC_REQS │  ← 时代 Buff 入口
│   ├── GOLDEN_REQUIRES_PLAYER_HAS_ERA_CLASSICAL_ANY_TECH   │
│   │     └── GOLDEN_PLAYER_HAS_ERA_CLASSICAL_TECH_REQS      │
│   │           └── 典例: 对每个古典科技创建 Requirement     │
│   │               (REQUIREMENT_PLAYER_HAS_TECH)             │
│   ├── GOLDEN_REQUIRES_PLAYER_HAS_ERA_CLASSICAL_ANY_CIVIC  │
│   │     └── (同上，对每个古典市政)                         │
│   └── GOLDEN_REQUIRES_PLAYER_HAS_NO_ERA_MEDIEVAL_...      │  ← 反向排除
│         └── GOLDEN_PLAYER_HAS_NO_ERA_MEDIEVAL_ANY_TECH_... │
│               ├── GOLDEN_PLAYER_REALLY_HAS_NO_ERA_MEDIEVAL_ANY_TECH │
│               │     └── GOLDEN_PLAYER_HAS_NO_ERA_MEDIEVAL_TECH_REQS │
│               │           └── 对每个中世纪科技: TEST_ANY (全部没有) │
│               └── (同上，对每个中世纪市政)                         │
└─────────────────────────────────────────────────────┘
```

**三层嵌套结构**：
1. **顶层**：`REQUIREMENTSET_TEST_ALL` — 必须同时满足"有当前时代科技"+"有当前时代市政"+"未进入下一时代"
2. **中层**：`REQUIREMENT_REQUIREMENTSET_IS_MET` — 动态引用子 RequirementSet
3. **底层**：`REQUIREMENT_PLAYER_HAS_TECH` / `REQUIREMENT_PLAYER_HAS_CIVIC` — 对具体科技/市政的判定

### 1.3 SQL 生成代码

```sql
-- ==========================================
-- 1. 创建 BUFF / DEBUFF Modifier（叉积：Eras × Yields）
-- ==========================================
INSERT OR REPLACE INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId)
SELECT
    'GOLDEN_'|| a.EraType ||'_BUFF_' || b.YieldType,
    'MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_MODIFIER',
    'GOLDEN_PLAYER_HAS_'|| a.EraType ||'_ANY_TECH_CIVIC_REQUIREMENTS'
FROM Eras AS a, Yields AS b;
-- 结果：GOLDEN_ERA_ANCIENT_BUFF_YIELD_FOOD, ... _YIELD_PRODUCTION, ... (N_Eras × N_Yields 条)

INSERT OR REPLACE INTO ModifierArguments (ModifierId, Name, Value)
SELECT
    'GOLDEN_'|| a.EraType ||'_BUFF_' || b.YieldType, 'YieldType', b.YieldType
FROM Eras AS a, Yields AS b;

INSERT OR REPLACE INTO ModifierArguments (ModifierId, Name, Value)
SELECT
    'GOLDEN_'|| a.EraType ||'_BUFF_' || b.YieldType, 'Amount', 15
FROM Eras AS a, Yields AS b;
-- DEBUFF 同理，Amount = -15

-- ==========================================
-- 2. 时代 RequirementSet：当前时代任意科技 AND 市政
-- ==========================================
INSERT OR REPLACE INTO RequirementSets (RequirementSetId, RequirementSetType)
SELECT
    'GOLDEN_PLAYER_HAS_'|| EraType ||'_ANY_TECH_CIVIC_REQUIREMENTS',
    'REQUIREMENTSET_TEST_ALL'
FROM Eras;

INSERT OR REPLACE INTO RequirementSetRequirements (RequirementSetId, RequirementId)
SELECT
    'GOLDEN_PLAYER_HAS_'|| EraType ||'_ANY_TECH_CIVIC_REQUIREMENTS',
    'GOLDEN_REQUIRES_PLAYER_HAS_'|| EraType ||'_ANY_TECH'
FROM Eras;
-- 同上追加 _ANY_CIVIC

-- ==========================================
-- 3. 反向排除：没有下一时代的科技 AND 市政（限定窗口上限）
-- ==========================================
INSERT OR REPLACE INTO RequirementSetRequirements (RequirementSetId, RequirementId)
VALUES
('GOLDEN_PLAYER_HAS_ERA_ANCIENT_ANY_TECH_CIVIC_REQUIREMENTS',
 'GOLDEN_REQUIRES_PLAYER_HAS_NO_ERA_CLASSICAL_ANY_TECH_AND_CIVIC'),
-- ... 每个时代一条

-- 反向排除用 TEST_ANY（只要没有任意一个下一时代科技/市政即满足）
INSERT OR REPLACE INTO RequirementSets (RequirementSetId, RequirementSetType)
VALUES
('GOLDEN_PLAYER_HAS_NO_ERA_CLASSICAL_ANY_TECH_AND_CIVIC',
 'REQUIREMENTSET_TEST_ANY');

-- 内部两项：REALLY_HAS_NO_ERA_CLASSICAL_ANY_TECH + ANY_CIVIC
INSERT OR REPLACE INTO RequirementSetRequirements VALUES
('GOLDEN_PLAYER_HAS_NO_ERA_CLASSICAL_ANY_TECH_AND_CIVIC',
 'GOLDEN_PLAYER_REALLY_HAS_NO_ERA_CLASSICAL_ANY_TECH'),
('GOLDEN_PLAYER_HAS_NO_ERA_CLASSICAL_ANY_TECH_AND_CIVIC',
 'GOLDEN_PLAYER_REALLY_HAS_NO_ERA_CLASSICAL_ANY_CIVIC');
```

**关键设计**：
- `REQUIREMENTSET_TEST_ANY` + 对所有下一时代科技的"没有"判定 = 只要缺少下一时代任一科技就满足（即尚未完全进入下一时代）
- 这种"反向排除"避免了需要在每个时代明确定义结束条件

### 1.4 文明→Trait→Modifier 绑定

```sql
-- 每个文明有唯一的 GOLDEN_TRAIT
INSERT INTO Types (Type, Kind) VALUES
('GOLDEN_TRAIT_CIVILIZATION_ROME', 'KIND_TRAIT');

INSERT INTO Traits (TraitType, Name, Description) VALUES
('GOLDEN_TRAIT_CIVILIZATION_ROME', 'LOC_GOLDEN_TRAIT_NAME',
 'LOC_GOLDEN_TRAIT_CIVILIZATION_ROME_DESCRIPTION');

INSERT INTO CivilizationTraits (CivilizationType, TraitType) VALUES
('CIVILIZATION_ROME', 'GOLDEN_TRAIT_CIVILIZATION_ROME');

-- 绑定 Trait → 时代 Modifier（以罗马为例：古典黄金/中古黑暗）
INSERT INTO TraitModifiers (TraitType, ModifierId)
SELECT 'GOLDEN_TRAIT_CIVILIZATION_ROME',
       'GOLDEN_ERA_CLASSICAL_BUFF_' || YieldType FROM Yields;

INSERT INTO TraitModifiers (TraitType, ModifierId)
SELECT 'GOLDEN_TRAIT_CIVILIZATION_ROME',
       'GOLDEN_ERA_MEDIEVAL_DEBUFF_' || YieldType FROM Yields;
```

**文明黄金时代对照**（部分示例）：

| 文明 | 黄金时代 | 黑暗时代 |
|------|---------|---------|
| 罗马 | 古典 | 中古 |
| 中国 | 中古 | 文艺复兴 |
| 美国 | 现代 | 工业 |
| 英国 | 文艺复兴 | 中古 |
| 俄罗斯 | 现代 | 原子 |
| 埃及/希腊/印度 | 远古 | 古典 |
| 日本 | 现代 | 工业 |

---

## XML 配合

### 游戏配置 XML

`Configuration/Config.xml` — 定义游戏设置面板中的配置参数：

- `EXTRA_TRAITS_OPTION` (GoldenAge 黄金时代勾选框)
- `GA_TOTALWAR` (世界大战模式开关)
- `GA_CIVIC_TECH_COST` (科技/市政成本百分比下拉框，100/150/200 三档)
- `GA_MILESTONE` (里程碑模式，与科技随机化互斥)
- 参数互斥通过 `ParameterCriteria` + `ConfigurationUpdates` 实现

### UI 面板 XML

`UI/GoldenAge_MilitaryService_UI.xml` — 单位退役按钮，挂接到 UnitPanel 的 `ActionStack`：
```xml
<Stack ID="TestButtonGrid" Anchor="R,B" Size="auto,41" Texture="SelectionPanel_ActionGroupSlot">
    <Button ID="TestButton" Size="44,53" Texture="UnitPanel_ActionButton">
        <Image Icon="ICON_CIVIC_NATIONALISM" Size="38,38"/>
    </Button>
</Stack>
```

`UI/GoldenAge_Cultivation_UI.xml` — 培育单位面板（建造者在资源地块上的培育操作按钮）

`UI/GoldenAge_Totalwar_UI.xml` — 世界大战状态面板

### 资源培育 UI 模式

`UI/GoldenAge_Cultivation_UI.xml` 为培育单位（农民/牧民/渔民/矿工）挂接操作按钮到 UnitPanel，Lua 侧通过 `ExposedMembers.DEMO.SacrificeUnitInCity` 暴露函数供 UI 调用。

---

## 二、子系统：资源培育（Cultivation）

### 2.1 设计概要

新增 4 种培育单位（农民/牧民/渔民/矿工），每种对应一类改良设施的建造。培育单位在资源地块上建造"培育改良"后，Lua 将地块资源类型改变（复制资源到新地块）。

### 2.2 数据表结构

```sql
CREATE TABLE GA_Resource_Cultivation(
    ResourceType         varchar(100),   -- 资源类型
    ResourceClassType    varchar(100),   -- BONUS / LUXURY
    UnitType             varchar(100),   -- 建造单位
    ImprovementType      varchar(100),   -- 培育改良类型 (如 IMPROVEMENT_CULTIVATE_WHEAT)
    PrereqTech           varchar(100),
    PrereqCivic          varchar(100),
    ResourceCultivation  varchar(100) DEFAULT 0,
    Icon                 varchar(100),
    ValidImprovementType varchar(100),   -- 合法的目标改良（替换原改良）
    TraitType            varchar(100),   -- BONUS_RESOURCE_CULTIVATION / LUXURY_RESOURCE_CULTIVATION
    Housing              varchar(100) DEFAULT 0,
    TilesRequired        varchar(100) DEFAULT 0,
    Domain               varchar(100) DEFAULT 'DOMAIN_LAND',
    PRIMARY KEY (UnitType, ImprovementType)
);
```

### 2.3 资源放置后的 Lua 处理

```lua
function OnResourcePlantedOrBreeded(locationX, locationY, eImprovementType,
                                     eImprovementOwnerID, resource, isPillaged, isWorked)
    local pPlayer = Players[eImprovementOwnerID]
    local plot = Map.GetPlot(locationX, locationY)
    local pResourceImprovement = GameInfo.Improvements[eImprovementType]

    if pResourceImprovement then
        -- 1. 解析改良名称获取目标资源类型
        --    例如 IMPROVEMENT_CULTIVATE_WHEAT_RESOURCE → RESOURCE_WHEAT
        PlantOrBreed(pResourceImprovement, plot, eImprovementOwnerID)

        -- 2. 将培育改良替换为目标正常改良
        for row in GameInfo.GA_Resource_Cultivation() do
            if pResourceImprovementType == row.ImprovementType then
                ImprovementBuilder.SetImprovementType(plot,
                    GameInfo.Improvements[row.ValidImprovementType].Index,
                    plot:GetOwner())
            end
        end
    end

    -- 3. 刷新玩家的资源属性（控制奢侈品城市专属数量）
    if pPlayer and eImprovementOwnerID then
        RefreshResourceAmountProperty(eImprovementOwnerID)
    end
end
Events.ImprovementAddedToMap.Add(OnResourcePlantedOrBreeded)
```

### 2.4 地块归属刷新技术

```lua
-- 替换地块资源后，需要刷新地块归属以触发 UI 更新
function PlantOrBreed(pResourceImprovement, pPlot, iPlayerID)
    -- 解析改良名称: IMPROVEMENT_CULTIVATE_WHEAT_RESOURCE → RESOURCE_WHEAT
    local transplant_types = {'RESOURCE'}
    local found = false
    for segment in string.gmatch(pResourceImprovement.ImprovementType, "[^_]+") do
        if segment == 'CULTIVATE' then
            found = true
        elseif found then
            table.insert(transplant_types, segment)
        end
    end

    if found then
        local transplant_resource_type = table.concat(transplant_types, '_')
        -- 设置地块资源类型
        ResourceBuilder.SetResourceType(pPlot,
            GameInfo.Resources[transplant_resource_type].Index, 1)
        -- 移除培育改良
        ImprovementBuilder.SetImprovementType(pPlot, -1, -1)

        -- 关键：刷新地块归属以触发重新绘制
        local pPlayer = Players[iPlayerID]
        if pPlayer:IsMajor() then
            local pCity = Cities.GetPlotPurchaseCity(pPlot:GetIndex())
            -- 短暂剥夺归属再恢复
            WorldBuilder.CityManager():SetPlotOwner(pPlot, false)
            if pCity then
                ExposedMembers.ResourceCultivation.GA_CultivationBuyPlot(
                    pCity:GetID(), pPlot:GetIndex(), iPlayerID)
            end
        end
    end
end
```

**`SetPlotOwner(plot, false)` 再恢复**：这是 Civ6 Lua 中触发地块刷新/重绘的常见技巧。短暂剥夺归属（不改变所有权数据）再通过 `BuyPlot` 恢复，强制游戏重新计算地块状态。

### 2.5 奢侈品城市专属控制

通过 Plot Property 控制哪些城市可以建造特定奢侈品的培育改良：

```lua
-- 每个奢侈资源每玩家最多 3 个、每城市最多 2 个
-- 设置地块属性: GA_PLAYER_WHEAT_MAX_AMOUNT = 0/1
iCityPlot:SetProperty("GA_PLAYER_"..ResourceStringOnly.."_MAX_AMOUNT", 1)
```

SQL 侧用 `REQUIREMENT_PLOT_PROPERTY_MATCHES` 检查这些属性：
```sql
INSERT INTO RequirementArguments (RequirementId, Name, Value) VALUES
('REQUIRES_GA_WHEAT_PROPERTY', 'PropertyName', 'GA_PLAYER_WHEAT_MAX_AMOUNT'),
('REQUIRES_GA_WHEAT_PROPERTY', 'PropertyMinimum', 1);
```

---

## 三、子系统：兵役制度（MilitaryService）

### 3.1 单位退役换人口

```lua
-- GoldenAge_MilitaryService.lua

-- 前提条件：城市住房 > 现有人口（有住房余量）
local function CityPopOverflow(pCity)
    if pCity == nil then return false end
    local iHousing = pCity:GetGrowth():GetHousing()
    local iPopulation = pCity:GetPopulation()
    return (iHousing > iPopulation)
end

function SacrificeUnitInCity(iPlayerID, iUnitID)
    local pUnit = UnitManager.GetUnit(iPlayerID, iUnitID)
    if pUnit ~= nil then
        local x, y = pUnit:GetX(), pUnit:GetY()
        local pCity = CityManager.GetCityAt(x, y)
        if pCity ~= nil and CityPopOverflow(pCity) then
            pCity:ChangePopulation(1)       -- 城市人口 +1
            UnitManager.Kill(pUnit)         -- 删除单位
            Game.AddWorldViewText(0, 'LOC_MODE_UNIT_RETIREMENT_SUCCESS', x, y)
        elseif pCity == nil then
            Game.AddWorldViewText(0, 'LOC_MODE_UNIT_RETIREMENT_CITY_WARNING', x, y)
        else
            Game.AddWorldViewText(0, 'LOC_MODE_UNIT_RETIREMENT_HOUSING_WARNING', x, y)
        end
    end
end

-- 暴露给 UI 调用
ExposedMembers.DEMO = ExposedMembers.DEMO or {}
ExposedMembers.DEMO.SacrificeUnitInCity = SacrificeUnitInCity
```

**`ExposedMembers` 暴露模式**：将 GameplayScript 中的函数暴露给 UI 脚本调用。UI 脚本通过 `ExposedMembers.DEMO.SacrificeUnitInCity(playerID, unitID)` 触发退役。

### 3.2 SQL 相关改动

```sql
-- 所有战斗单位消耗 1 人口建造
UPDATE Units SET PopulationCost = 1, PrereqPopulation = 2
WHERE UnitType IN (SELECT UnitType FROM Units WHERE Combat > 0 AND PrereqPopulation IS Null);

-- 起始人口 +1（补偿）
UPDATE StartEras SET StartingPopulationCapital = 2 WHERE EraType = 'ERA_ANCIENT';

-- 老马右一冲突修复：开拓者消耗人口改为返还人口
INSERT INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId) VALUES
('MODIFIER_GA_SETTLER_POPULATION_REFUND',
 'MODIFIER_PLAYER_CITIES_CHANGE_POPULATION_CREATE_UNIT',
 'GA_CITY_FOUNDED');
```

---

## 四、子系统：世界大战（WorldWar）

### 4.1 时代自动宣战

```lua
-- GoldenAge_WorldWar.lua

include("PopupManager")
include("TeamSupport")

function OnCheckGameEraChanged()
    local localPlayer = Game.GetLocalPlayer()
    local currentEra = Game.GetEras():GetCurrentEra()

    if currentEra == 5 and iLastShownEraIndex ~= currentEra
       and localPlayer ~= PlayerTypes.NONE then
        -- 时代 5 = 工业时代：所有存活主要文明互相宣战
        local pAllPlayerIDs = PlayerManager.GetAliveMajors()
        for _, pPlayer1 in ipairs(pAllPlayerIDs) do
            for _, pPlayer2 in ipairs(pAllPlayerIDs) do
                if pPlayer1:GetDiplomacy():CanDeclareWarOn(
                    pPlayer2:GetID(), WarTypes.SURPRISE_WAR, true) then
                    -- 避免人类玩家主动宣战自己
                    if Players[localPlayer] ~= pPlayer1 then
                        pPlayer1:GetDiplomacy():DeclareWarOn(
                            pPlayer2:GetID(), WarTypes.SURPRISE_WAR, true)
                    else
                        pPlayer2:GetDiplomacy():DeclareWarOn(
                            pPlayer1:GetID(), WarTypes.SURPRISE_WAR, true)
                    end
                end
            end
        end
    end
end

function Initialize()
    Events.LocalPlayerTurnBegin.Add(OnCheckGameEraChanged)
end
Initialize()
```

**防止人类玩家主动宣战**：`if Players[localPlayer] ~= pPlayer1 then ... else` 确保人类玩家作为被动方（被宣战），避免"你向所有文明宣战"的提示框。

### 4.2 获取存活主要文明

```lua
local pAllPlayerIDs = PlayerManager.GetAliveMajors()
```

返回所有存活的主要文明玩家对象列表（不含城邦和自由城邦）。

---

## 五、游戏参数配置系统

### 5.1 多层级参数注册

```sql
-- GameMode 参数（创建游戏时的勾选框）
INSERT INTO Parameters (ParameterId, Name, Description, Domain,
    DefaultValue, ConfigurationGroup, ConfigurationId, GroupId, SortIndex)
VALUES
('GOLDEN_EXTRA_TRAITS', 'LOC_...', 'LOC_...', 'bool', 1,
 'Game', 'EXTRA_TRAITS_OPTION', 'GameModes', 204),
('GA_TOTALWAR', 'LOC_...', 'LOC_...', 'bool', 0,
 'Game', 'GA_TOTALWAR', 'GameModes', 211);

-- AdvancedOptions 参数（高级设置下拉框）
INSERT INTO Parameters (ParameterId, ConfigurationGroup, ConfigurationId,
    DefaultValue, Description, Domain, GroupId, Name, SortIndex)
VALUES
('GA_COST_CIVIC_TECH', 'Game', 'GA_COST_CIVIC_TECH', 100,
 'LOC_...', 'GA_CivicTechCost', 'AdvancedOptions',
 'LOC_GA_COST_CIVIC_TECH_NAME', 51);

-- DomainValues（下拉框选项）
INSERT INTO DomainValues (Domain, Value, Name, SortIndex) VALUES
('GA_CivicTechCost', 100, 'LOC_..._100_NAME', 1),
('GA_CivicTechCost', 150, 'LOC_..._150_NAME', 2);
```

### 5.2 参数互斥规则

```sql
-- ParameterCriteria：里程碑模式与科技随机化互斥
INSERT INTO ParameterCriteria (ParameterId, ConfigurationGroup,
    ConfigurationId, Operator, ConfigurationValue) VALUES
('GA_MILESTONE', 'Game', 'GAMEMODE_TREE_RANDOMIZER', 'NotEquals', 1);

-- ConfigurationUpdates：一方开启时关闭另一方
INSERT INTO ConfigurationUpdates (SourceGroup, SourceId, SourceValue,
    TargetGroup, TargetId, TargetValue, Static) VALUES
('Game', 'GA_MILESTONE', 1, 'Game', 'GAMEMODE_TREE_RANDOMIZER', 0, 0);
```

---

## 六、完整使用模板

### 为文明添加黄金时代的最小实现

```sql
-- 1. 定义 Trait
INSERT INTO Types (Type, Kind) VALUES
('GOLDEN_TRAIT_MY_CIV', 'KIND_TRAIT');

INSERT INTO Traits (TraitType, Name, Description) VALUES
('GOLDEN_TRAIT_MY_CIV', 'LOC_GOLDEN_TRAIT_NAME', 'LOC_...');

INSERT INTO CivilizationTraits (CivilizationType, TraitType) VALUES
('CIVILIZATION_MY_CIV', 'GOLDEN_TRAIT_MY_CIV');

-- 2. 创建 Buff Modifier（黄金时代：中古 +15% 全产出）
INSERT INTO TraitModifiers (TraitType, ModifierId)
SELECT 'GOLDEN_TRAIT_MY_CIV', 'GOLDEN_ERA_MEDIEVAL_BUFF_' || YieldType
FROM Yields;

-- 3. 创建 Debuff Modifier（黑暗时代：文艺复兴 -15%）
INSERT INTO TraitModifiers (TraitType, ModifierId)
SELECT 'GOLDEN_TRAIT_MY_CIV', 'GOLDEN_ERA_RENAISSANCE_DEBUFF_' || YieldType
FROM Yields;
```

### 定制时代窗口

```sql
-- 修改 Amount 值改变倍率强度
UPDATE ModifierArguments SET Value = 25
WHERE ModifierId LIKE 'GOLDEN_ERA_MEDIEVAL_BUFF_%' AND Name = 'Amount';

-- 自定义判定条件（例如：需要该时代所有科技而非任意一个）
UPDATE RequirementSets SET RequirementSetType = 'REQUIREMENTSET_TEST_ALL'
WHERE RequirementSetId LIKE 'GOLDEN_PLAYER_HAS_ERA_%';
```

---

## 七、注意事项

1. **叉积爆炸**：`Eras × Yields` 会产生大量 Modifier（8 个时代 × 6 种产出 × 2 种 Buff/Debuff = 96 个），再加每个文明的复刻，总量可观。对于自定义文明，只需创建对应 Trait。

2. **反向排除的边界**：`REQUIREMENTSET_TEST_ANY` + 对所有下一时代科技的"没有"判定，意味着玩家只要**尚未完整拥有下一时代任一科技**就满足。这在"只开了少量下一时代科技"的情况下仍然使 BUFF 生效。

3. **未来时代特殊处理**：最后一个时代（未来）使用 `TECH_FUTURE_TECH` 和 `CIVIC_FUTURE_CIVIC` 判定（而非遍历所有科技），因为未来时代无其他科技。

4. **地块归属刷新**：`SetPlotOwner(plot, false)` 再恢复是一个 hack，可能在某些 Mod 负载下有副作用（如触发不必要的 `CityTileOwnershipChanged` 事件）。注意做好事件过滤。

5. **世界大战**：`PlayerManager.GetAliveMajors()` 可能抛出空列表。在调用 `DeclareWarOn` 前需确保目标玩家有效。

6. **Lua 子系统可选**：资源培育、兵役制度、世界大战是 GoldenAge Mod 的可选附加系统，通过 Parameters 中的 bool 开关控制是否启用。核心时代 BUFF/DEBUFF 系统完全独立运行。
