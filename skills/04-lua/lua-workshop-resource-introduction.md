# 资源引进系统 (Resource Introduction via Custom Unit)

> 来源：Resource Introduction (3275724171)
> 完整独立系统，可复用

## 概述

通过一个自定义平民单位"实业家"，在地块上工作若干回合后引入或删除资源。核心机制：UI 端选择资源 → GP 端计时工作 → 到期执行 `ResourceBuilder.SetResourceType`。系统包含 GameConfig 难度选择、地块条件校验、AI 禁用等功能。

## 架构

```
┌─────────────────────────────────┐
│  UI (ResourceIntroductionUI.lua)│
│  - 单位选中时显示操作按钮       │
│  - K(消除) I(存储种子) C(种植)  │
│  - 资源网格选择弹窗              │
│  - 通过 RequestPlayerOperation   │
│    发送指令到 GP                 │
└──────────┬──────────────────────┘
           │ GameEvents
┌──────────▼──────────────────────┐
│  GP (ResourceIntroductionGP.lua)│
│  - 接收 UI 指令执行实际修改      │
│  - 每回合检查工作进度            │
│  - 到期调用 ResourceBuilder      │
│  - WorldViewText 进度反馈        │
└─────────────────────────────────┘
```

## XML 配合

### ResourceIntroductionUI.xml — 实业家单位面板

`ResourceIntroductionUI.xml` 在选中实业家单位时挂入三个操作按钮（K消除 / I导入种子 / C种植）：

```xml
<Context>
    <Grid ID="UNIT_MOD_RI_INDUSTRIALIST_Grid" Anchor="R,B" Size="auto,41"
          Texture="SelectionPanel_ActionGroupSlot">
        <Stack StackGrowth="Right">
            <Button ID="UNIT_MOD_RI_INDUSTRIALIST_ButtonKill" Size="44,53"
                    Texture="UnitPanel_ActionButton" ToolTip="LOC_MOD_RI_BUTTONK">
                <Image Icon="ICON_MOD_RI_BUTTONK" Size="38,38"/>
            </Button>
            <Button ID="UNIT_MOD_RI_INDUSTRIALIST_ButtonImport" Size="44,53"
                    Texture="UnitPanel_ActionButton" ToolTip="LOC_MOD_RI_BUTTONI"/>
            <Button ID="UNIT_MOD_RI_INDUSTRIALIST_ButtonConstruction" Size="44,53"
                    Texture="UnitPanel_ActionButton" ToolTip="LOC_MOD_RI_BUTTONC"/>
        </Stack>
    </Grid>
    <!-- 资源选择网格（C种植时弹出，显示周围可用资源和已存储种子） -->
    <Grid ID="UNIT_MOD_RI_INDUSTRIALIST_Box" Size="parent,auto"
          Texture="Civilopedia_StatsFrame" Anchor="C,B">
        <Stack ID="UNIT_MOD_RI_INDUSTRIALIST_Stack" StackGrowth="Right"
               WrapGrowth="Down" Padding="1"/>
    </Grid>
    <!-- 资源图标实例模板 -->
    <Instance Name="UNIT_MOD_RI_INDUSTRIALIST_Instance">
        <GridButton ID="UNIT_MOD_RI_INDUSTRIALIST_InstanceGridButton" Size="53,53">
            <Image ID="UNIT_MOD_RI_INDUSTRIALIST_InstanceResource" Size="50,50"
                   Texture="Resources50"/>
        </GridButton>
    </Instance>
</Context>
```

### ResourceIntroductionText.xml — 中英双语文本

单位名称、操作按钮提示、配置面板文本等。

### ResourceIntroductionICON.xml + RI_cfg_Text.xml

图标定义和 GameConfig 难度选项的文本描述。

---

## SQL 核心定义

### 1. 自定义单位

```sql
INSERT INTO Types (Type, Kind) VALUES
('UNIT_MOD_RI_INDUSTRIALIST', 'KIND_UNIT');

INSERT INTO Units (UnitType, ...) VALUES
('UNIT_MOD_RI_INDUSTRIALIST', ...);

-- 关键属性
-- Domain: DOMAIN_LAND
-- FormationClass: FORMATION_CLASS_CIVILIAN
-- Cost: 80, CostProgressionModel: COST_PROGRESSION_PREVIOUS_COPIES
-- CostProgressionParam1: 45（每多造一个+45锤）
-- PurchaseYield: YIELD_GOLD, MustPurchase: 0
-- PrereqCivic: CIVIC_EARLY_EMPIRE
```

### 2. 禁止 AI 建造

```sql
-- 给主要文明和城邦的默认特性都加上禁用 modifier
INSERT INTO TraitModifiers (TraitType, ModifierId) VALUES
('TRAIT_LEADER_MAJOR_CIV', 'MODIFIER_TRAIT_LEADER_MAJOR_CIV_AI_NO_BUILD_...'),
('MINOR_CIV_DEFAULT_TRAIT', 'MODIFIER_MINOR_CIV_DEFAULT_TRAIT_AI_NO_BUILD_...');

INSERT INTO Modifiers (ModifierId, ModifierType, OwnerRequirementSetId) VALUES
(..., 'MODIFIER_PLAYER_UNIT_BUILD_DISABLED', 'PLAYER_IS_AI');

INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
(..., 'UnitType', 'UNIT_MOD_RI_INDUSTRIALIST');
```

### 3. 合法资源白名单表

```sql
CREATE TABLE IF NOT EXISTS ResourceIntroduction_ValidResource (
    ResourceType TEXT PRIMARY KEY,
    FOREIGN KEY (ResourceType) REFERENCES Resources (ResourceType)
);
-- 插入所有加成/奢侈资源（约30种）
```

### 4. GameConfig 表（难度选择）

```sql
CREATE TABLE IF NOT EXISTS ResourceIntroduction_Param (
    Name TEXT NOT NULL, Value INTEGER NOT NULL, PRIMARY KEY (Name)
);
-- 根据不同 Criteria (c0-c7) 载入不同的 iWorkTurns 值：
-- c0=4, c1=6, c2=8, c3=10, c4=14, c5=18, c6=24, c7=30
```

### 5. GameConfig 参数定义

```sql
INSERT INTO Parameters (Key1, Key2, ParameterId, ConfigurationGroup, ConfigurationId,
    DefaultValue, Description, Domain, GroupId, Name, SortIndex) VALUES
('Ruleset', 'RULESET_EXPANSION_2', 'PARAM_RI_WORKTURNNS', 'Game', 'Cfg_RI',
    2, '...DESCRIPTION', 'DOMAIN_RI_WORKTURNS', 'GameOptions', '...NAME', 27015000);
-- 配合 DomainValues 提供 0-7 共 8 档选项
```

## Lua 核心实现

### GP 端：工作进度与资源操作

```lua
-- 工作属性名
local g_PORPERTY_RI_I_WORK = 'PORPERTY_RI_I_WORK'

-- 计算实际工作回合数（基础值 × 游戏速度系数 × 0.01）
local g_iWorkTurns = math.ceil(
    GameInfo.ResourceIntroduction_Param['iWorkTurns'].Value *
    GameInfo.GameSpeeds[GameConfiguration.GetGameSpeedType()].CostMultiplier * 0.01
)

-- 每回合检查
function OnPlayerTurnStarted(playerID)
    for _, pUnit in Players[playerID]:GetUnits():Members() do
        if pUnit:GetType() == GameInfo.Units['UNIT_MOD_RI_INDUSTRIALIST'].Index then
            local tWorkStatus = pUnit:GetProperty(g_PORPERTY_RI_I_WORK)
            if tWorkStatus then
                -- 单位移动/换主人则取消工作
                if (pUnit:GetOwner() ~= tWorkStatus.iPlayer
                    or pUnit:GetX() ~= tWorkStatus.iX
                    or pUnit:GetY() ~= tWorkStatus.iY) then
                    pUnit:SetProperty(g_PORPERTY_RI_I_WORK, nil)
                    break
                end

                -- 操作类型 1 = 种植
                if tWorkStatus.iOperation == 1 then
                    if Game.GetCurrentGameTurn() - tWorkStatus.iStartTurn >= g_iWorkTurns then
                        RIGP_AddResourceInPlot(pUnit:GetOwner(), {...})
                        pUnit:SetProperty(g_PORPERTY_RI_I_WORK, nil)
                    else
                        -- 显示进度文字
                        Game.AddWorldViewText(0, "种植中:资源名 (n/N)", iX, iY)
                    end
                -- 操作类型 2 = 消除
                elseif tWorkStatus.iOperation == 2 then
                    if Game.GetCurrentGameTurn() - tWorkStatus.iStartTurn >=
                       math.ceil(g_iWorkTurns * 0.5) then  -- 消除只需50%时间
                        RIGP_DelResourceInPlot(pUnit:GetOwner(), {...})
                        pUnit:SetProperty(g_PORPERTY_RI_I_WORK, nil)
                    end
                end
            end
        end
    end
end

-- 单位移动 → 取消工作
function OnUnitMoveComplete(playerID, unitID, _iX, _iY)
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    if pUnit:GetType() == GameInfo.Units['UNIT_MOD_RI_INDUSTRIALIST'].Index then
        pUnit:SetProperty(g_PORPERTY_RI_I_WORK, nil)
    end
end
```

### GP 端：实际添加/删除资源

```lua
function RIGP_AddResourceInPlot(iPlayer, tParam)
    local pPlot = Map.GetPlot(tParam.iPlotX, tParam.iPlotY)
    local sResource = GameInfo.Resources[tParam.iResource].ResourceType

    -- 查找该资源对应的改良设施
    local tImprovement = nil
    for row in GameInfo.Improvement_ValidResources() do
        if row.ResourceType == sResource then
            tImprovement = row
            break
        end
    end

    -- 设置资源类型
    ResourceBuilder.SetResourceType(pPlot, tParam.iResource, 1)

    -- 如果有对应改良，自动建造
    if tImprovement then
        ImprovementBuilder.SetImprovementType(pPlot,
            GameInfo.Improvements[tImprovement.ImprovementType].Index, iPlayer)
    end
end

function RIGP_DelResourceInPlot(iPlayer, tParam)
    local pPlot = Map.GetPlot(tParam.iPlotX, tParam.iPlotY)
    ResourceBuilder.SetResourceType(pPlot, -1)  -- -1 表示移除
    if pPlot:GetImprovementType() >= 0 then
        ImprovementBuilder.SetImprovementType(pPlot, -1)
    end
end
```

### UI 端：地块条件校验

```lua
-- 检查资源在本地块是否合法（地形 + 地貌）
-- 通过 GameInfo.Resource_ValidFeatures / Resource_ValidTerrains 遍历
-- 用绿/红/灰色显示能否种植

local function NewResourceInstance(sResource, iUnitPlotFeature, iUnitPlotTerrain, pUnit)
    -- 遍历资源所需的 Feature 和 Terrain
    -- 匹配的显示绿色，不匹配的显示红色
    -- 至少匹配一个条件 flag=true
    -- flag=true 的项可点击种植
end
```

### UI 端：操作按钮逻辑

```
三种按钮：
- K (消除/移除资源)：当前地块有合法资源 → 可消除
- I (引入/存储种子)：当前地块有合法资源 → 存储为种子
- C (种植/工作)：扫描周围6格内己方领地的合法资源 + 已存储的种子
                  → 弹出资源网格供选择
                  → 选择后启动工作
```

### UI 端：按钮显示条件

```lua
-- K 按钮可见条件：地块有合法资源 AND 玩家有对应科技 AND
--    (地块无人 / 地块是自己的 / 与地块主人处于战争) AND
--    (没有正在进行的工作 OR 正在进行消除但还没到50%进度)

-- I 按钮可见条件：地块有合法资源 AND 玩家有对应科技 AND (没有正进行的工作 OR ...)

-- C 按钮可见条件：地块无区域 AND 地块无资源 AND (没有正进行的工作 OR 正在进行种植但还没完成)
```

## UI↔GP 通信方式

```lua
-- UI 端通过 RequestPlayerOperation + EXECUTE_SCRIPT 触发 GP 端代码
function SetUnitProperty(iPlayer, iUnit, sProperty, value)
    local tParameters = {}
    tParameters.iUnit = iUnit
    tParameters.sProperty = sProperty
    tParameters.value = value
    tParameters.OnStart = 'RIGP_SetUnitProperty'  -- 在GP端注册的GameEvents名称
    UI.RequestPlayerOperation(iPlayer, PlayerOperations.EXECUTE_SCRIPT, tParameters)
end

-- GP 端注册
function RIGP_SetUnitProperty(iPlayer, tParam)
    local pUnit = UnitManager.GetUnit(iPlayer, tParam.iUnit)
    pUnit:SetProperty(tParam.sProperty, tParam.value)
end
GameEvents.RIGP_SetUnitProperty.Add(RIGP_SetUnitProperty)

-- GP 端回调 WorldViewText 到 UI
-- 同理通过 GameEvents.RIGP_AddWorldViewText
```

## 单位属性作为状态机

单位用 `SetProperty` / `GetProperty` 存储工作状态：

```lua
tWorkStatus = {
    iOperation = 1,      -- 1=种植, 2=消除
    iResource = <idx>,   -- 资源Index
    iStartTurn = <turn>, -- 开始回合
    iPlayer = <player>,  -- 单位所有者
    iX, iY = <coords>    -- 工作位置
}
```

另一个属性 `PROPERTY_RI_I_RESOURCE_STORED` 存储"种子"（已存储的资源Index，用于在无邻近资源时也能种植）。

## 关键技术点

1. **工作取消机制**：单位移动 → `Events.UnitMoveComplete` → 清除工作属性
2. **单位易主检测**：每回合检查 `pUnit:GetOwner() ~= tWorkStatus.iPlayer`
3. **速度适配**：`iWorkTurns × GameSpeed.CostMultiplier × 0.01`
4. **导入存储**：可将已存在的合法资源存为"种子"，然后去其他地块种植
5. **自动改良**：种植资源后，如果该资源有对应的改良设施，自动建造
6. **WorldViewText 进度反馈**：每回合在地块上显示"xx中:资源名 (n/N)"

## 依赖

- 无外部依赖，纯原版 API
- 需要 `ResourceBuilder`（游戏自带）
- 需要 `ImprovementBuilder`（游戏自带）
