# 种植/育种资源系统 (Plant & Breed)

> 来源：PlantAndBreed (2929355120)
> 核心文件：`Scripts/PlantAndBreed_Gameplay.lua`, `UI/Addition/PlantAndBreed_UI.lua`, `Data/PlantAndBreed_Core.sql`, `Data/PlantAndBreed_Resources.sql`, `Data/PlantAndBreed_Improvements.sql`, `Data/PlantAndBreed_Projects.sql`

## 1. 系统概述

让建造者（Builder）在己方领土内的空地格上**种植奖励/奢侈资源**。核心机制：

1. 改良对应资源 → 获得"种子"（种子是一种 Artifact 类资源）
2. 建造者移动到空地 → 消耗种子 → 在地块上放置资源
3. 城市可运行"育种项目"消耗种子 → 项目完成后给地块加产出
4. 消耗种子数随种植次数递增（边际成本递增）

### 完整循环

```
改良原资源 → 获得 Resource_Seed (Artifact)
         → 建造者种植 (消耗种子)
         → 城市运行育种项目 (消耗种子)
         → 太空育种项目 (终极项目)
```

---

## XML 配合

### PlantAndBreed_UI.xml — 建造者面板种植按钮

`UI/Addition/PlantAndBreed_UI.xml` 在建造者单位面板（`/InGame/UnitPanel/StandardActionsStack`）中挂入种植按钮和资源选择面板：

```xml
<Context>
    <!-- K/C/I 按钮容器 -->
    <Grid ID="PlantAndBreedGrid" Anchor="R,B" Size="46,41" Hidden="1">
        <Button ID="PlantAndBreedButton" Size="44,53" Texture="UnitPanel_ActionButton">
            <Image Icon="ICON_PLANT_AND_BREED_630E123F.dds" Size="38,38"/>
        </Button>
        <!-- 资源选择弹窗 -->
        <Container ID="PlantAndBreedContainer" Size="256,384">
            <Stack ID="PlantAndBreedStack" StackGrowth="Down"/>
        </Container>
    </Grid>
    <!-- 每个资源的显示模板（图标+名称+种植成本+限制） -->
    <Instance Name="PlantAndBreedSlot">
        <GridButton ID="PlantAndBreedSelect" Size="240,64" Texture="Religion_BeliefButton">
            <Image ID="PlantAndBreedIcons" Size="50,50"/>
            <Label ID="PlantAndBreedText1/2/3" Style="FontFlair14"/>
        </GridButton>
    </Instance>
</Context>
```

按钮默认隐藏，Lua 端仅在选中建造者且剩余移动力 > 0 时显示。弹窗包含资源网格（可用/不可用筛选、种子需求显示）。

### PlantAndBreed_Districts.xml / PlantAndBreed_Icons.xml

育种建筑、图标等辅助数据定义。

---

## 2. 数据层模式

### 2.1 自定义配置表（SQLite 新表）

```sql
-- 核心：定义哪些资源可种植/育种
CREATE TABLE IF NOT EXISTS 'PlantAndBreedResources' (
    'ResourceType' TEXT NOT NULL,
    'IsLuxury'     BOOLEAN NOT NULL DEFAULT 0,
    'IsPlant'      BOOLEAN NOT NULL DEFAULT 0,  -- 可种植
    'IsBreed'      BOOLEAN NOT NULL DEFAULT 0,  -- 可育种
    PRIMARY KEY ('ResourceType')
);

INSERT OR REPLACE INTO PlantAndBreedResources (ResourceType, IsLuxury, IsPlant, IsBreed)
VALUES
    ('RESOURCE_WHEAT',  0, 1, 0),  -- 奖励资源-可种植
    ('RESOURCE_CATTLE', 0, 0, 1),  -- 奖励资源-可育种
    ('RESOURCE_WINE',   1, 1, 0),  -- 奢侈资源-可种植
    ('RESOURCE_IVORY',  1, 0, 1);  -- 奢侈资源-可育种
```

### 2.2 种子资源自动生成

种子是 Artifact 类资源，从原资源自动派生：

```sql
-- GlobalParameters（全局可调参数）
INSERT INTO GlobalParameters (Name, Value) VALUES
    ('PLANTANDBREED_630E123F_BASE_COST_BONUS',      20),
    ('PLANTANDBREED_630E123F_BASE_COST_STRATEGIC',  40),
    ('PLANTANDBREED_630E123F_BASE_COST_LUXURY',     40),
    ('PLANTANDBREED_630E123F_INCREASE_FACTOR',      0.5),
    ('PLANTANDBREED_630E123F_MAX_COST_FACTOR',      10);

-- 为每个 PlantAndBreed 资源创建一个种子类型
INSERT INTO Types (Type, Kind)
SELECT ResourceType || '_630E123F', 'KIND_RESOURCE'
FROM Resources WHERE ResourceType IN (SELECT ResourceType FROM PlantAndBreedResources);

-- 种子是 Artifact 类，不显示在地图上
INSERT INTO Resources (ResourceType, Name, ResourceClassType)
SELECT ResourceType || '_630E123F',
       'LOC_' || ResourceType || '_630E123F_NAME',
       'RESOURCECLASS_ARTIFACT'
FROM Resources WHERE ResourceType IN (SELECT ResourceType FROM PlantAndBreedResources);

-- 种子累积、不在地图上产出、上限 999
INSERT INTO Resource_Consumption (ResourceType, Accumulate, BaseExtractionRate, ImprovedExtractionRate, StockpileCap)
SELECT ResourceType || '_630E123F', 1, 0, 0, 999
FROM Resources WHERE ResourceType IN (SELECT ResourceType FROM PlantAndBreedResources);
```

### 2.3 改良设施自动产出种子

利用 `MODIFIER_SINGLE_CITY_ADJUST_FREE_RESOURCE_EXTRACTION` 让改良原资源时获取种子：

```sql
-- 自动为每个 (改良设施, 资源) 生成 Modifier
INSERT INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId)
SELECT ImprovementType || '_' || ResourceType || '_630E123F',
       'MODIFIER_SINGLE_CITY_ADJUST_FREE_RESOURCE_EXTRACTION',
       ImprovementType || '_' || ResourceType || '_630E123F_REQSET'
FROM Improvement_ValidResources
WHERE ResourceType IN (SELECT ResourceType FROM PlantAndBreedResources);

-- Amount = 1, ResourceType = 种子
INSERT INTO ModifierArguments (ModifierId, Name, Value)
SELECT ImprovementType || '_' || ResourceType || '_630E123F', 'Amount', '1'
FROM Improvement_ValidResources
WHERE ResourceType IN (SELECT ResourceType FROM PlantAndBreedResources);

INSERT INTO ModifierArguments (ModifierId, Name, Value)
SELECT ImprovementType || '_' || ResourceType || '_630E123F', 'ResourceType', ResourceType || '_630E123F'
FROM Improvement_ValidResources
WHERE ResourceType IN (SELECT ResourceType FROM PlantAndBreedResources);

-- 挂到 ImprovementModifiers
INSERT INTO ImprovementModifiers (ImprovementType, ModifierId)
SELECT ImprovementType, ImprovementType || '_' || ResourceType || '_630E123F'
FROM Improvement_ValidResources
WHERE ResourceType IN (SELECT ResourceType FROM PlantAndBreedResources);
```

---

## 3. 种植操作（建造者动作）

### 3.1 Gameplay 层：在地块放置资源

```lua
function PlantAndBreedResource(playerID, params)
    -- params: { X, Y, UnitID, eResource, eResourceSeed, iResourceSeed }
    local pPlot = Map.GetPlot(params.X, params.Y);
    local pCity = Cities.GetPlotPurchaseCity(pPlot);

    -- 核心操作：在地块上设置资源类型
    ResourceBuilder.SetResourceType(pPlot, params.eResource, 1);

    -- 消耗种子
    pPlayer:GetResources():ChangeResourceAmount(params.eResourceSeed, -1 * params.iResourceSeed);

    -- 结束单位动作
    UnitManager.FinishMoves(pUnit);

    -- 临时移除地块归属（后面会购回）
    WorldBuilder.CityManager():SetPlotOwner(pPlot, false);

    -- 发放金币（用于后续地块购回）
    pPlayer:GetTreasury():ChangeGoldBalance(1000);
end
```

### 3.2 UI 层：种植操作三步走

```lua
function ExecutePlantAndBreed(ResourceInst, tResource)
    -- 记录当前金币
    local iTreasury = Players[iPlayer]:GetTreasury():GetGoldBalance();

    -- 计算消耗种子数量
    local ResourceSeedRequired = CalculateSeedRequired(tResource);

    -- 第1步：EXECUTE_SCRIPT → Gameplay 放置资源
    UI.RequestPlayerOperation(iPlayer, PlayerOperations.EXECUTE_SCRIPT, {
        OnStart = 'PlantAndBreedResource',
        X = iX, Y = iY, UnitID = unitID,
        eResource = ResourceIndex,
        eResourceSeed = ResourceSeedIndex,
        iResourceSeed = ResourceSeedRequired
    });

    -- 第2步：通过 UI 购回地块归属（正常购买流程）
    local tParameters = {};
    tParameters[CityCommandTypes.PARAM_PLOT_PURCHASE] = UI.GetInterfaceModeParameter(...);
    tParameters[CityCommandTypes.PARAM_X] = iX;
    tParameters[CityCommandTypes.PARAM_Y] = iY;
    if CityManager.CanStartCommand(pCity, CityCommandTypes.PURCHASE, tParameters) then
        CityManager.RequestCommand(pCity, CityCommandTypes.PURCHASE, tParameters);
    else
        -- 如果无法正常购买，通过 Lua 恢复地块归属
        UI.RequestPlayerOperation(iPlayer, PlayerOperations.EXECUTE_SCRIPT, {
            OnStart = 'RecoverPlantPlotOwner',
            X = iX, Y = iY, CityID = pCity:GetID()
        });
    end

    -- 第3步：恢复玩家金币到种植前的数额
    UI.RequestPlayerOperation(iPlayer, PlayerOperations.EXECUTE_SCRIPT, {
        OnStart = 'RecoverPlayerTreasury',
        Treasury = iTreasury
    });

    -- 第4步：记录种植次数
    SetPreviousCopiesUI(tResource);
end
```

### 3.3 地块归属恢复

```lua
-- 如果无法通过购买系统获取地块，直接用 Lua 恢复
function RecoverPlantPlotOwner(playerID, params)
    local pPlot = Map.GetPlot(params.X, params.Y);
    local pCity = pPlayer:GetCities():FindID(params.CityID);
    WorldBuilder.CityManager():SetPlotOwner(pPlot, pCity);
end

-- 恢复金币
function RecoverPlayerTreasury(playerID, params)
    pPlayer:GetTreasury():SetGoldBalance(params.Treasury);
end
```

---

## 4. 成本递增系统

```lua
-- GlobalParameters 配置
BASE_COST_BONUS    = 20    -- 奖励资源基础消耗
BASE_COST_STRATEGIC= 40    -- 战略资源基础消耗
BASE_COST_LUXURY   = 40    -- 奢侈资源基础消耗
INCREASE_FACTOR    = 0.5   -- 每次种植后消耗增幅
MAX_COST_FACTOR    = 10    -- 最大消耗倍率

function CalculateSeedRequired(tResource)
    local iPreviousCopies = CalculatePreviousCopies(tResource);  -- 之前种过多少次
    local iCostFactor = 1 + iPreviousCopies * INCREASE_FACTOR;
    if iCostFactor >= MAX_COST_FACTOR then iCostFactor = MAX_COST_FACTOR; end

    if tResource.ResourceClassType == "RESOURCECLASS_BONUS" then
        return math.floor(BASE_COST_BONUS * GAME_SPEED_MULTIPLIER * iCostFactor);
    elseif tResource.ResourceClassType == "RESOURCECLASS_LUXURY" then
        return math.floor(BASE_COST_LUXURY * GAME_SPEED_MULTIPLIER * iCostFactor);
    end
end
```

记录种植次数通过 CityProperty：

```lua
function SetPreviousCopies(tResource)
    local iPreviousCopies = pPlayer:GetProperty(tResource.ResourceType .. '_630E123F') or 0;
    iPreviousCopies = iPreviousCopies + 1;
    pPlayer:SetProperty(tResource.ResourceType .. '_630E123F', iPreviousCopies);
end
```

---

## 5. 育种项目系统

### 5.1 项目层级

```
Level 1: PROJECT_<Resource>_630E123F_1  → 育种项目 (消耗种子 → 产出更多种子 100个)
Level 2: PROJECT_<Resource>_630E123F_2  → 杂交育种 (消耗种子 → 给对应资源地块加产出)
Level 3: PROJECT_SPACE_BREEDING_630E123F → 太空育种 (全局加成)
```

### 5.2 项目1：育种（产出种子）

```sql
INSERT INTO Projects (ProjectType, Cost, PrereqResource)
SELECT 'PROJECT_' || ResourceType || '_630E123F_1', 100, ResourceType || '_630E123F'
FROM PlantAndBreedResources;

-- 需要建筑：BUILDING_PLANTANDBREED_2_630E123F
INSERT INTO Projects_XP2 (ProjectType, RequiredBuilding)
SELECT 'PROJECT_' || ResourceType || '_630E123F_1', 'BUILDING_PLANTANDBREED_2_630E123F'
FROM PlantAndBreedResources;
```

Lua 侧：项目完成后给玩家种子

```lua
function OnPlantAndBreedProject1(playerID, cityID, projectIndex, ...)
    -- 检查是否是育种项目
    for row in GameInfo.PlantAndBreedProject1() do
        if sProjectType == row.ProjectType then
            sResourceSeed = row.ResourceSeedType;
            break;
        end
    end
    if sResourceSeed == '' then return end

    -- 发放种子
    pPlayer:GetResources():ChangeResourceAmount(eResourceSeed, iResourceGive);
end
Events.CityProjectCompleted.Add(OnPlantAndBreedProject1);
```

### 5.3 项目2：杂交育种（加产出）

```sql
-- 奖励资源：+1 食物 +1 生产力
INSERT INTO ProjectCompletionModifiers (ProjectType, ModifierId)
SELECT 'PROJECT_' || ResourceType || '_630E123F_2', ResourceType || '_630E123F_FOOD'
FROM PlantAndBreedResources WHERE NOT IsLuxury;

INSERT INTO ProjectCompletionModifiers (ProjectType, ModifierId)
SELECT 'PROJECT_' || ResourceType || '_630E123F_2', ResourceType || '_630E123F_PRODUCTION'
FROM PlantAndBreedResources WHERE NOT IsLuxury;

-- 奢侈资源：+2 信仰 +2 金币
INSERT INTO ProjectCompletionModifiers (ProjectType, ModifierId)
SELECT 'PROJECT_' || ResourceType || '_630E123F_2', ResourceType || '_630E123F_FAITH'
FROM PlantAndBreedResources WHERE IsLuxury;

-- Modifier 定义：MODIFIER_PLAYER_ADJUST_PLOT_YIELD
INSERT INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId)
SELECT ResourceType || '_630E123F_FOOD', 'MODIFIER_PLAYER_ADJUST_PLOT_YIELD',
       'PLOT_HAS_' || ResourceType || '_630E123F_REQSET'
FROM PlantAndBreedResources WHERE NOT IsLuxury;
```

### 5.4 太空育种项目

```sql
INSERT INTO Projects (ProjectType, PrereqDistrict, PrereqTech, Cost, SpaceRace)
VALUES ('PROJECT_SPACE_BREEDING_630E123F', 'DISTRICT_SPACEPORT', 'TECH_ROCKETRY', 1200, 1);

-- 完成效果：所有植物地块 +2 科技 +2 文化，+50% 太空项目产能，+2 宜居度
INSERT INTO ProjectCompletionModifiers VALUES
    ('PROJECT_SPACE_BREEDING_630E123F', 'PROJECT_SPACE_BREEDING_630E123F_SCIENCE'),
    ('PROJECT_SPACE_BREEDING_630E123F', 'PROJECT_SPACE_BREEDING_630E123F_CULTURE'),
    ('PROJECT_SPACE_BREEDING_630E123F', 'PROJECT_SPACE_BREEDING_630E123F_SPACE_RACE'),
    ('PROJECT_SPACE_BREEDING_630E123F', 'PROJECT_SPACE_BREEDING_630E123F_AMENITY');
```

---

## 6. UI 集成模式

### 6.1 按钮注入到建造者面板

```lua
function Initialize()
    -- 查找建造者操作面板，挂入"种植"按钮
    local pContext = ContextPtr:LookUpControl("/InGame/UnitPanel/StandardActionsStack");
    Controls.PlantAndBreedGrid:ChangeParent(pContext);
    Controls.PlantAndBreedButton:RegisterCallback(Mouse.eLClick, OnPlantAndBreedButtonClicked);
    Controls.PlantAndBreedGrid:SetHide(true);  -- 默认隐藏
end
Events.LoadGameViewStateDone.Add(Initialize);
```

### 6.2 按钮可见性控制

```lua
-- 仅在选中建造者且还有移动力时显示按钮
function SetPlantAndBreedGridState()
    local pUnit = UI.GetHeadSelectedUnit();
    if not IsPlantAndBreedUnit(pUnit) then
        Controls.PlantAndBreedGrid:SetHide(true);
    else
        Controls.PlantAndBreedGrid:SetHide(false);
    end
end

function IsPlantAndBreedUnit(pUnit)
    local tUnit = GameInfo.Units[pUnit:GetType()];
    if tUnit.UnitType == "UNIT_BUILDER" then
        if pUnit:GetMovementMovesRemaining() == 0 then return false; end
        return true;
    end
    return false;
end

-- 监听单位选择变化
Events.UnitSelectionChanged.Add(OnUnitSelectionChanged);
Events.UnitMoveComplete.Add(OnUnitMoveComplete);
Events.TurnBegin.Add(OnTurnBegin);
```

### 6.3 Lua 自定义表（供 Gameplay 查询）

```sql
-- 创建自定义表供 Lua 查询"哪个项目产出哪种种子"
CREATE TABLE IF NOT EXISTS 'PlantAndBreedProject1' (
    'ProjectType'      TEXT NOT NULL,
    'ResourceSeedType' TEXT NOT NULL,
    PRIMARY KEY ('ProjectType')
);

INSERT INTO PlantAndBreedProject1 (ProjectType, ResourceSeedType)
SELECT 'PROJECT_' || ResourceType || '_630E123F_1', ResourceType || '_630E123F'
FROM PlantAndBreedResources;
```

Lua 侧查询：

```lua
for row in GameInfo.PlantAndBreedProject1() do
    if sProjectType == row.ProjectType then
        sResourceSeed = row.ResourceSeedType;
    end
end
```

---

## 7. 跨上下文通信：GameEvents 模式

```lua
-- Gameplay 层：暴露 GameEvents 给 UI 层
ExposedMembers.GameEvents = GameEvents;

-- 注册 GameEvent
function Initialize()
    GameEvents.PlantAndBreedResource.Add(PlantAndBreedResource);
    GameEvents.RecoverPlantPlotOwner.Add(RecoverPlantPlotOwner);
    GameEvents.RecoverPlayerTreasury.Add(RecoverPlayerTreasury);
    GameEvents.SetPreviousCopies.Add(SetPreviousCopies);
end
Events.LoadGameViewStateDone.Add(Initialize);

-- UI 层：获取 GameEvents
GameEvents = ExposedMembers.GameEvents;

-- UI 层调用 Gameplay 函数
function SetPreviousCopiesUI(tResource)
    GameEvents.SetPreviousCopies.Call(tResource);
end
```

---

## 8. 种植条件校验（完整校验链）

```lua
function IsResourceBuildable(tResource)
    if not IsPlantAndBreedResource(tResource) then return false; end  -- 是否在配置表中
    if not IsResourceTerrainValid(tResource) then return false; end     -- 地形匹配
    if not IsResourceFeatureValid(tResource) then return false; end     -- 地貌匹配
    if not IsPlotOwned() then return false; end                         -- 地块属于玩家
    if not IsPlotNoDistrict() then return false; end                    -- 无区域
    if not IsPlotNoResource() then return false; end                    -- 无现有资源
    if not IsResourceImprovementValid(tResource) then return false; end -- 改良不冲突
    if not IsResourceSeedEnough(tResource) then return false; end       -- 种子足够
    return true;
end

-- 地形检查
function IsResourceTerrainValid(tResource)
    for row in GameInfo.Resource_ValidTerrains() do
        if sResourceType == row.ResourceType and sTerrainType == row.TerrainType then
            return true;
        end
    end
end

-- 地貌检查
function IsResourceFeatureValid(tResource)
    if eFeature == -1 then
        return IsResourceTerrainValid(tResource);  -- 无地貌，只查地形
    end
    for row in GameInfo.Resource_ValidFeatures() do
        if sResourceType == row.ResourceType and sFeatureType == row.FeatureType then
            return true;
        end
    end
    return false;
end

-- 改良不冲突：无改良或改良支持此资源
function IsResourceImprovementValid(tResource)
    if eImprovement == -1 then return true; end
    for row in GameInfo.Improvement_ValidResources() do
        if sResourceType == row.ResourceType and sImprovementType == row.ImprovementType then
            return true;
        end
    end
    return false;
end
```

---

## 9. 关键 API 速查

### 资源配置
```lua
ResourceBuilder.SetResourceType(pPlot, resourceIndex, amount)  -- 放置资源
pPlayer:GetResources():GetResourceAmount(resourceType)          -- 获取资源数量（支持字符串）
pPlayer:GetResources():ChangeResourceAmount(resourceIndex, delta)-- 修改资源数量
```

### 地块操作
```lua
pPlot:GetResourceType()     -- 当前资源类型，-1 表示无
pPlot:GetTerrainType()      -- 地形类型
pPlot:GetFeatureType()      -- 地貌类型，-1 表示无
pPlot:GetDistrictType()     -- 区域类型，-1 表示无
pPlot:GetImprovementType()  -- 改良类型，-1 表示无
pPlot:GetOwner()            -- 地块所属玩家
Map.GetPlot(x, y)           -- 根据坐标获取 Plot
Map.GetPlotByIndex(index)   -- 根据 Index 获取 Plot
```

### 城市操作
```lua
Cities.GetPlotPurchaseCity(pPlot)           -- 获取可购买此地块的城市
CityManager.CanStartCommand(pCity, CityCommandTypes.PURCHASE, params)  -- 检查可否购买地块
CityManager.RequestCommand(pCity, CityCommandTypes.PURCHASE, params)   -- 发起地块购买
```

### 单位操作
```lua
UI.GetHeadSelectedUnit()                    -- 当前选中单位
pUnit:GetMovementMovesRemaining()           -- 剩余移动力
UnitManager.FinishMoves(pUnit)              -- 结束单位所有移动
SimUnitSystem.SetAnimationState(pUnit, "ACTION_1", "IDLE")  -- 设置单位动画
```

### 金币操作
```lua
pPlayer:GetTreasury():GetGoldBalance()      -- 获取当前金币
pPlayer:GetTreasury():ChangeGoldBalance(amount)  -- 增减金币
pPlayer:GetTreasury():SetGoldBalance(amount)     -- 设置金币为精确值
```

### 自定义表查询（Lua）
```lua
for row in GameInfo.PlantAndBreedResources() do  -- 查询自定义表
for row in GameInfo.PlantAndBreedProject1() do   -- 查询自定义项目表
for row in GameInfo.Resource_ValidTerrains() do  -- 查询游戏默认表
```

---

## 10. 关键提醒

- **Artifact 资源类**：`RESOURCECLASS_ARTIFACT` 类型资源不会显示在地图上，只能通过 modifier 产出，适合做"代币"用途
- **种子命名约定**：`<原资源>_630E123F`，后缀用于避免冲突（实际开发时可替换为自己的唯一后缀）
- **种植成本递增**：通过 PlayerProperty 记录每种资源种植次数，防止无限复制奢侈资源
- **地块购买流程**：种植操作先移除地块归属再购回，是为保证购买价格正确
- **不支持无人地块种植**：必须在己方领土内，通过 `Cities.GetPlotPurchaseCity` 获取购买城市
- **读档安全**：事件回调中不需要特别的读档保护（因为用的是 EXECUTE_SCRIPT + GameEvent 而非 CityAddedToMap 等自动事件）
- **兼容多 Mod**：PlantAndBreedResources 表结构支持手动添加其他 Mod 的资源
- **GameInfo 自定义表**：在 SQL 中 CREATE TABLE 后，Lua 端可通过 `GameInfo.表名()` 迭代器访问
