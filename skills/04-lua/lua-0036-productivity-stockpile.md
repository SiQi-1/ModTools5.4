# 生产力蓄力与自动投资系统（来源：14.0 RafiaSilva + GreyThroat）

## 做什么
记录城市已完成生产任务的花费，在新生产任务开始时自动注入累积的生产力。展示同一模式在两个领袖身上的不同变体——RafiaSilva（龙舌兰）通过总督属性驱动，GreyThroat（灰喉）每次自动注入 50%。同时还包含 FeatherPen（羽毛笔）的单元格属性堆叠和宣战自动生成叛军。

## 涉及文件

| 文件 | 角色 |
|------|------|
| `14.0/Scripts/Arknights_Cute_Leaders_14.0_Scripts.lua` | GP 端：全部生产力逻辑 + 宣战叛军 + 单位属性堆叠 |
| `14.0/UI/Arknights_Cute_Leaders_14.0_UI.lua` | UI 端：城市生产事件触发 + 单位按钮系统 |

## 系统一：RafiaSilva 生产力蓄力（龙舌兰）

### GP 端

**触发条件：** 城市有总督龙舌兰（检查 `SIQI_RAFIA_SILVA_TEQUILA_PROPERTY_BASE` > 0）

**生产完成时（累计花费）：**
```lua
function SiqiRafiaSilvaOnCityProductionCompleted(playerID, params)
    -- 1. 去重检查：同一 itemID 不重复记录
    local Table = pCity:GetProperty("SIQI_RAFIA_SILVA_IS_FIRST") or {}
    if itemID ~= -1 and Siqi_IsInTable(itemID, Table) then return end
    table.insert(Table, itemID)
    
    -- 2. 累计花费
    pCity:SetProperty("SIQI_RAFIA_SILVA_PRODUCTION_COST", oldCost + params.productionCost)
end
```

**生产变化时（注入累计生产力）：**
```lua
function SiqiRafiaSilvaOnCityProductionChanged(playerID, params)
    local oldCost = pCity:GetProperty("SIQI_RAFIA_SILVA_PRODUCTION_COST") or 0
    if oldCost <= 0 then return end
    
    local ShouldCost = cost - progress  -- 还需多少生产力
    
    if ShouldCost > oldCost then
        pCity:GetBuildQueue():AddProgress(oldCost)  -- 全注入
        oldCost = 0
    else
        pCity:GetBuildQueue():AddProgress(ShouldCost) -- 刚好完成
        oldCost = oldCost - ShouldCost
    end
    
    pCity:SetProperty("SIQI_RAFIA_SILVA_PRODUCTION_COST", oldCost)
    
    -- 如果有晋升右 1（Tequila R1），生产力同时转换为科技和文化
    local Property2 = pCity:GetProperty(HASH_GOV_PROPERTY_R1) or 0
    if Property2 > 0 then
        pPlayer:GetTechs():ChangeCurrentResearchProgress(c)
        pPlayer:GetCulture():ChangeCurrentCulturalProgress(c)
    end
end
```

**UI 端触发：** 监听到 `CityProductionCompleted`（非单位生产）+ `CityProductionChanged`（单位生产），通过 EXECUTE_SCRIPT 传递参数：

```lua
-- UI 端
UI.RequestPlayerOperation(playerID, PlayerOperations.EXECUTE_SCRIPT, {
    OnStart = 'SiqiRafiaSilvaOnCityProductionChanged',
    productionCost = cost,
    cityID = cityID,
    progress = Progress
})
```

### 浮动文字显示

```lua
function Siqi_AddProductionGameText(amount, iX, iY)
    Game.AddWorldViewText(0, '+'..amount..GameInfo.Yields[1].IconString..Locale.Lookup(GameInfo.Yields[1].Name), iX, iY)
end
```

## 系统二：GreyThroat 生产加速（灰喉）

### GP 端

**生产完成时（记录花费）：**
```lua
function SiqiGreyThroatOnCityProductionCompleted(playerID, params)
    -- 记录最后完成任务的 cost
    pCity:SetProperty("SIQI_GREYTHROAT_LAST_COST", params.productionCost)
    pCity:SetProperty("SIQI_GREYTHROAT_HAD_GIVE", false)  -- 重置标记
end
```

**生产变化时（注入 50%）：**
```lua
function SiqiGreyThroatOnCityProductionChanged(playerID, params)
    local HadGive = pCity:GetProperty('SIQI_GREYTHROAT_HAD_GIVE') or false
    if HadGive then return end  -- 每任务只触发一次
    
    local LastCost = pCity:GetProperty('SIQI_GREYTHROAT_LAST_COST') or 0
    local cost = params.productionCost
    if LastCost > cost then return end  -- 只有新任务花费高于上次才触发
    
    local half = math.floor(cost * 0.5)
    pCity:GetBuildQueue():AddProgress(half)
    pCity:SetProperty("SIQI_GREYTHROAT_HAD_GIVE", true)
end
```

**UI 端触发：**
```lua
-- 每次生产完成 → 记录 cost
UI.RequestPlayerOperation(playerID, PlayerOperations.EXECUTE_SCRIPT, {
    OnStart = 'SiqiGreyThroatOnCityProductionCompleted',
    productionCost = cost, cityID = cityID, itemID = DistrictID
})
-- 每次生产变化 → 如果 cost > lastCost，注入 50%
UI.RequestPlayerOperation(playerID, PlayerOperations.EXECUTE_SCRIPT, {
    OnStart = 'SiqiGreyThroatOnCityProductionChanged',
    productionCost = cost, cityID = cityID, progress = Progress
})
```

## 系统三：FeatherPen 属性堆叠（羽毛笔）

### GP 端

**两种堆叠来源：**

1. **城市完成生产** → 城市所在地块 `SIQI_FEATHER_PEN_YIELD_PRODUCTION_PROPERTY` +1（最多 12）
2. **击杀单位** → 击杀单位的 Ability 层数 +1（ABILITY_RAFIA_SILVA_CIV_PROPERTY_1~12，最多 12 层）

```lua
function SiqiOnCityProductionCompleted(playerID, cityID, ...)
    local oldproperty = pPlot:GetProperty("SIQI_FEATHER_PEN_YIELD_PRODUCTION_PROPERTY") or 0
    if oldproperty >= 12 then return end
    pPlot:SetProperty("SIQI_FEATHER_PEN_YIELD_PRODUCTION_PROPERTY", oldproperty + 1)
end

function SiqiOnUnitKilledInCombat(killedPlayerID, killedUnitID, playerID, unitID)
    -- 找第一个未获得的 Ability 层级
    for i = 1,12 do
        if pUnitAbility:GetAbilityCount("ABILITY_RAFIA_SILVA_CIV_PROPERTY_"..i) == 0 then
            pUnitAbility:ChangeAbilityCount("ABILITY_RAFIA_SILVA_CIV_PROPERTY_"..i, 1)
            break
        end
    end
end
```

## 辅助工具函数

### DB.Query 随机单位

```lua
function Siqi_GetRandomEraUnit(era)
    local query = 
    "WITH AAA AS ( SELECT TechnologyType AS Tech FROM Technologies WHERE EraType = '"..era.."' )"..
    "SELECT Units.UnitType AS UnitType FROM Units "..
    "JOIN AAA WHERE Units.PrereqTech = AAA.Tech AND Units.Domain = 'DOMAIN_LAND' AND Units.Combat != 0 "
    local result = DB.Query(query)
    -- 随机选一个
    local randomIndex = Game.GetRandNum(#UnitList) + 1
    return UnitList[randomIndex]
end
```

### 自由城市单位生成

```lua
function Siqi_InitFreeCityUnit(iX, iY, unitType)
    local FreeCityPlayerID = 62
    -- 先尝试目标格，不行则搜索 3 环内邻格
    local kplot = Map.GetNeighborPlots(iX, iY, 3)
    for i, plot in ipairs(kplot) do
        if Siqi_CanHaveUnit(plot) then
            UnitManager.InitUnit(FreeCityPlayerID, unitType, plot:GetX(), plot:GetY())
            return plot:GetX(), plot:GetY()
        end
    end
    return false
end
```

### 宣战自动生成叛军

```lua
function SiqiOnDiplomacyDeclareWar(firstPlayerID, secondPlayerID)
    -- 羽毛笔宣战或被宣战时
    -- 敌方的每个城市周围生成 5 个该时代随机陆地军事单位（自由城市）
    for i, pCity in pPlayerCities:Members() do
        for j = 1, 5 do
            Siqi_InitFreeCityUnit(pCity:GetX(), pCity:GetY(), Siqi_GetRandomEraUnit(eraType))
        end
    end
end
```

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `UI/Arknights_Cute_Leaders_14.0_UI.xml` | 4 个单位面板按钮（A/B/C/D Grid × 4 领袖） |
| `Arknights_Cute_Leaders_14.0_Governors.sql` | 总督龙舌兰定义 + Modifier 属性附加 |
| `Arknights_Cute_Leaders_14.0_UnitAbilities.sql` | 单位能力定义（ABILITY_RAFIA_SILVA_CIV_PROPERTY_1~12） |
| `Arknights_Cute_Leaders_14.0_Modifiers.sql` | 总督属性 Modifier + 城市产出 Modifier 链 |
| `Arknights_Cute_Leaders_14.0_Units.sql` | 自定义单位定义 |
| `Arknights_Cute_Leaders_14.0_Configs.sql` | GameCapabilities 属性注册 |

### 控件 ID 与 Lua Controls.xxx 对照

#### Arknights_Cute_Leaders_14.0_UI.xml（单位面板按钮）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `SiqiCuteLeader14AGrid` | Grid | `Controls.SiqiCuteLeader14AGrid` | 按钮 A 容器（RafiaSilva 龙舌兰） |
| `SiqiCuteLeader14AButton` | Button | `Controls.SiqiCuteLeader14AButton` | 按钮 A（44x53，ICON_CUTELEADER_BUTTON_A） |
| `SiqiCuteLeader14BGrid` | Grid | `Controls.SiqiCuteLeader14BGrid` | 按钮 B 容器（GreyThroat 灰喉） |
| `SiqiCuteLeader14BButton` | Button | `Controls.SiqiCuteLeader14BButton` | 按钮 B（44x53，ICON_CUTELEADER_BUTTON_B） |
| `SiqiCuteLeader14CGrid` | Grid | `Controls.SiqiCuteLeader14CGrid` | 按钮 C 容器（FeatherPen 羽毛笔） |
| `SiqiCuteLeader14CButton` | Button | `Controls.SiqiCuteLeader14CButton` | 按钮 C（44x53，ICON_CUTELEADER_BUTTON_C） |
| `SiqiCuteLeader14DGrid` | Grid | `Controls.SiqiCuteLeader14DGrid` | 按钮 D 容器（备用） |
| `SiqiCuteLeader14DButton` | Button | `Controls.SiqiCuteLeader14DButton` | 按钮 D（44x53，ICON_CUTELEADER_BUTTON_D） |

**按钮模板（4 个完全对称）：**
```xml
<Grid ID="SiqiCuteLeader14XGrid" Anchor="R,B" Size="auto,41" AutoSizePadding="6,0"
      Texture="SelectionPanel_ActionGroupSlot" SliceCorner="5,19" SliceSize="1,1"
      SliceTextureSize="12,41" ConsumeMouse="1" Hidden="1">
    <Button ID="SiqiCuteLeader14XButton" Anchor="C,B" Size="44,53" Texture="UnitPanel_ActionButton">
        <Image ID="SiqiCuteLeader14XButtonIcon" Anchor="C,C" Offset="0,-2" Size="38,38"
               Icon="ICON_CUTELEADER_BUTTON_X"/>
    </Button>
</Grid>
```

**挂载模式（UnitPanel 扩展）：**
```lua
function Initialize()
    local pContext = ContextPtr:LookUpControl("/InGame/UnitPanel/StandardActionsStack")
    if pContext then
        Controls.SiqiCuteLeader14AGrid:ChangeParent(pContext)
        Controls.SiqiCuteLeader14AButton:RegisterCallback(Mouse.eLClick, OnSiqiCuteLeader14AButtonClicked)
        -- B/C/D 同理
    end
    Events.UnitSelectionChanged.Add(OnUnitSelectionChanged)
    Events.UnitMoveComplete.Add(OnUnitMoveComplete)
end
Events.LoadGameViewStateDone.Add(Initialize)
```

### SQL 必需定义

#### 单位能力（UnitAbilities.sql）

```sql
-- FeatherPen 属性堆叠 12 层
INSERT INTO UnitAbilities (UnitAbilityType, Name, ...) VALUES
    ('ABILITY_RAFIA_SILVA_CIV_PROPERTY_1', ...),
    ('ABILITY_RAFIA_SILVA_CIV_PROPERTY_2', ...),
    -- ... 共 12 层
    ('ABILITY_RAFIA_SILVA_CIV_PROPERTY_12', ...);
```

#### 总督属性 Modifier

| ModifierType | 作用 | 关联属性 |
|-------------|------|---------|
| `MODIFIER_SIQI_RAFIA_SILVA_TEQUILA_PROPERTY_BASE_ATTACH` | 给所在城市设置基础属性（龙舌兰在城时） | `SIQI_RAFIA_SILVA_TEQUILA_PROPERTY_BASE` |
| `MODIFIER_SIQI_RAFIA_SILVA_TEQUILA_PROPERTY_R1_ATTACH` | 给所在城市设置晋升 R1 属性 | HASH_GOV_PROPERTY_R1 |

#### GameCapabilities 属性（Configs.sql 注册）

```sql
-- Player/City 属性（需在 GameCapabilities 注册才能 SetProperty/GetProperty）
SIQI_RAFIA_SILVA_PRODUCTION_COST       -- 龙舌兰累计生产力
SIQI_RAFIA_SILVA_IS_FIRST             -- 龙舌兰去重表
SIQI_GREYTHROAT_LAST_COST             -- 灰喉上次任务花费
SIQI_GREYTHROAT_HAD_GIVE              -- 灰喉每任务触发标记
SIQI_GREYTHROAT_IS_FIRST              -- 灰喉去重表
SIQI_FEATHER_PEN_YIELD_PRODUCTION_PROPERTY  -- 羽毛笔单元格堆叠（上限12）
```

### 添加新领袖按钮模板

```xml
<!-- 新单位面板按钮 -->
<Grid ID="SiqiCuteLeader14NewGrid" Anchor="R,B" Size="auto,41" AutoSizePadding="6,0"
      Texture="SelectionPanel_ActionGroupSlot" SliceCorner="5,19" SliceSize="1,1"
      SliceTextureSize="12,41" ConsumeMouse="1" Hidden="1">
    <Button ID="SiqiCuteLeader14NewButton" Anchor="C,B" Size="44,53" Texture="UnitPanel_ActionButton">
        <Image ID="SiqiCuteLeader14NewButtonIcon" Anchor="C,C" Offset="0,-2" Size="38,38"
               Icon="ICON_NEW_LEADER"/>
    </Button>
</Grid>
```

```lua
-- Lua 端注册
Controls.SiqiCuteLeader14NewGrid:ChangeParent(pContext)
Controls.SiqiCuteLeader14NewButton:RegisterCallback(Mouse.eLClick, OnNewLeaderButtonClicked)
```

## 设计要点

1. **两次 EXECUTE_SCRIPT 分离**：UI 端检测触发条件，GP 端执行修改，分工明确
2. **去重机制**：通过 `SIQI_RAFIA_SILVA_IS_FIRST` 表记录已完成条目，防止同一产物的重复计数
3. **双领袖共享触发**：同一事件注册两次（A 和 B 版本），各自检查领袖身份
4. **AddProgress vs FinishProgress**：AddProgress 是部分注入（可能需要多次调用），FinishProgress 是一次完成
5. **游戏速度适配**：`GAME_SPEED_MULTIPLIER = CostMultiplier / 100`
6. **属性堆叠上限**：用条件守卫 `if oldproperty >= 12 then return end` 设置硬上限
7. **随机单位 SQL 查询**：`DB.Query` 适合简单查询，跨表 JOIN 筛选特定时代单位
8. **自由城市 ID = 62**：硬编码常量，蛮族 = 63
