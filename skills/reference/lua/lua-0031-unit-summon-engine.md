# 单位召唤引擎（来源：0031）

## 做什么
特殊单位（U0031_1）可从 UI 触发，在自身周围3格内放置一个指定类型的单位。包含多层验证：冷却检查、单位类型许可、距离范围检查、地块可放置性检查。召唤出的单位自动获得一个指定能力（ABILITY_UNIT_SIQI_C0031_1）。

## 触发方式
UI 通过 `GameEvents.Siqi0031_MiuMiu_SpawnUnit` 发送参数 `{UnitID, UnitType, X, Y, PlotID}`，Lua 端验证并执行。

## 涉及文件和函数

| 文件 | 函数 | 作用 |
|------|------|------|
| `Siqi_Leaders_0031_MiuMiu_Scripts.lua` | `OnMiuMiuSpawnUnit(playerID, params)` | 召唤入口，多层验证 |
| `Siqi_Leaders_0031_MiuMiu_Scripts.lua` | `IsCooldownReady(pUnit)` | 检查通用冷却 |
| `Siqi_Leaders_0031_MiuMiu_Scripts.lua` | `IsAllowedUnitType(playerID, unitType)` | 检查可召唤的单位类型 |
| `Siqi_Leaders_0031_MiuMiu_Scripts.lua` | `IsPlotInRange(pUnit, x, y)` | 检查目标坐标是否在3格内 |
| `Siqi_Leaders_0031_Supports.lua` | `Siqi_CanHaveUnit(plotIndex)` | 检查地块是否可放置单位 |
| `Siqi_Leaders_0031_Supports.lua` | `Siqi_InitUnit(iX, iY, unitType, playerID)` | 放置单位的回退逻辑（3环内找空位） |

## 核心代码

```lua
-- 允许召唤的单位类型（按晋升类）
local allowClass = {
    ["PROMOTION_CLASS_MELEE"] = true,
    ["PROMOTION_CLASS_RANGED"] = true,
    ["PROMOTION_CLASS_HEAVY_CAVALRY"] = true,
    ["PROMOTION_CLASS_LIGHT_CAVALRY"] = true
}

-- 召唤主函数
function OnMiuMiuSpawnUnit(playerID, params)
    -- 1. 参数校验
    if not unitID or not unitType or x == nil or y == nil then return end

    -- 2. 施法单位校验：必须是 ALLOW_UNIT_TYPE
    local pUnit = UnitManager.GetUnit(playerID, unitID)
    if unitInfo.UnitType ~= ALLOW_UNIT_TYPE then return end

    -- 3. 冷却检查
    if not IsCooldownReady(pUnit) then return end

    -- 4. 目标单位类型检查：只允许四大战斗晋升类
    if not IsAllowedUnitType(playerID, unitType) then return end

    -- 5. 距离检查：必须在施法单位3格内
    if not IsPlotInRange(pUnit, x, y) then return end

    -- 6. 地块可用性检查
    if not Siqi_CanHaveUnit(targetPlot:GetIndex()) then return end

    -- 7. 创建单位
    local newUnit = UnitManager.InitUnit(playerID, unitType, x, y)
    if newUnit then
        -- 设置冷却
        pUnit:SetProperty(PROPERTY_LAST_USED, Game.GetCurrentGameTurn())
        -- 赋予新单位指定能力
        newUnit:GetAbility():ChangeAbilityCount("ABILITY_UNIT_SIQI_C0031_1", 1)
    end
    UnitManager.FinishMoves(pUnit)
end

-- 地块可放置检查
function Siqi_CanHaveUnit(plotIndex)
    local pPlot = Map.GetPlotByIndex(plotIndex)
    if pPlot:IsImpassable() then return false end
    if pPlot:IsMountain() then return false end
    if pPlot:IsUnit() then return false end
    if pPlot:IsCity() then return false end
    if pPlot:IsWater() then return false end
    local iDistrict = pPlot:GetDistrictType()
    if iDistrict ~= -1 and GameInfo.Districts[iDistrict].HitPoints > 0 then return false end
    return true
end
```

## 关键设计要点

1. **多层验证链**：参数完整性 → 施法单位类型 → 冷却 → 目标单位类型 → 距离 → 地块可放置性，任一层失败即返回
2. **单位类型白名单**：可召唤单位限制为四大战斗晋升类（近战/远程/重骑/轻骑），防止召唤经济/宗教/支援单位
3. **距离限制**：`Map.GetPlotDistance` ≤ 3，防止远距离召唤
4. **冷却共享**：共用 `PROPERTY_LAST_USED` 和 `COOLDOWN_TURNS = 6`，同一施法单位的所有召唤共享冷却
5. **地块验证完整**：检查不可通行、山脉、已有单位、城市、水域、有血条的区域，比官方更严格
6. **新单位自动赋能**：被召唤单位立即获得指定能力（ABILITY_UNIT_SIQI_C0031_1），实现"召唤物自带Buff"

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `UI/Siqi_Leaders_0031_MiuMiu.xml` | 召唤选择面板 — 技能1（MiuMiu）带下拉选择 |
| `UI/Siqi_Leaders_0031_Skill2.xml` | 技能2（Skill2）按钮 — 纯点击无面板 |
| `UI/Siqi_Leaders_0031_UI.xml` | 奇观加速按钮 — 建造者站在奇观上使用 |

### 控件 ID 与 Lua Controls.xxx 对照

#### Siqi_Leaders_0031_MiuMiu.xml（召唤选择面板）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `MiuMiuButtonGrid` | Grid | `Controls.MiuMiuButtonGrid` | 外层容器（SetHide 控制显隐） |
| `MiuMiuButton` | Button | `Controls.MiuMiuButton` | 召唤入口按钮（44x53，注册 eLClick） |
| `MiuMiuButtonIcon` | Image | — | 按钮图标（ICON_SIQI0031_SKILL_1.png） |
| `MiuMiuSelectContainer` | Container | `Controls.MiuMiuSelectContainer` | 单位选择下拉面板（280x360） |
| `MiuMiuSelectTitle` | Label | — | 选择面板标题 |
| `MiuMiuSelectHint` | Label | — | 底部提示文字 |
| `MiuMiuSelectScrollPanel` | ScrollPanel | `Controls.MiuMiuSelectScrollPanel` | 可召唤单位列表滚动面板 |
| `MiuMiuSelectStack` | Stack | `Controls.MiuMiuSelectStack` | 单位槽位挂载点（InstanceManager 父容器） |
| `MiuMiuSelectEmpty` | Label | `Controls.MiuMiuSelectEmpty` | "无可召唤单位"提示 |

**Instance 模板：**

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `MiuMiuUnitSlot` | 可召唤单位选项 | `MiuMiuUnitSelect`(GridButton), `MiuMiuUnitIcon`(Image, 50x50), `MiuMiuUnitName`(Label), `MiuMiuUnitClass`(Label) |

**交互流程：**
```lua
-- 1. 点击入口按钮 → 打开下拉面板
Controls.MiuMiuButton:RegisterCallback(Mouse.eLClick, OnMiuMiuButtonClicked)
-- 2. OnMiuMiuButtonClicked 中：
Controls.MiuMiuSelectContainer:SetHide(false)
Controls.MiuMiuSelectEmpty:SetHide(#unitList > 0)
Controls.MiuMiuSelectScrollPanel:SetHide(#unitList == 0)
-- 3. 动态填充可召唤单位列表
local m_UnitSelectIM = InstanceManager:new("MiuMiuUnitSlot", "MiuMiuUnitSelect", Controls.MiuMiuSelectStack)
for _, unitInfo in ipairs(unitList) do
    local instance = m_UnitSelectIM:GetInstance()
    instance.MiuMiuUnitName:SetText(Locale.Lookup(unitInfo.Name))
    instance.MiuMiuUnitClass:SetText(Locale.Lookup(unitInfo.PromotionClass))
end
-- 4. 点击具体单位 → 进入 WB_SELECT_PLOT 地块选择模式
-- 5. 选择地块 → 发送 GameEvents.Siqi0031_MiuMiu_SpawnUnit
-- 6. 关闭面板
Controls.MiuMiuSelectContainer:SetHide(true)
```

#### Siqi_Leaders_0031_Skill2.xml（技能2按钮）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `Siqi0031Skill2S1ButtonGrid` | Grid | `Controls.Siqi0031Skill2S1ButtonGrid` | 外层容器 |
| `Siqi0031Skill2S1Button` | Button | `Controls.Siqi0031Skill2S1Button` | 技能2按钮（注册 eLClick） |
| `Siqi0031Skill2S1ButtonIcon` | Image | — | 按钮图标（ICON_SIQI0031_SKILL_2.png） |

纯点击按钮，无下拉面板，点击后直接发送 GameEvent。

#### Siqi_Leaders_0031_UI.xml（奇观加速按钮）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `Siqi0031WonderSpeedButtonGrid` | Grid | `Controls.Siqi0031WonderSpeedButtonGrid` | 外层容器（建造者选中奇观时显示） |
| `Siqi0031WonderSpeedButton` | Button | `Controls.Siqi0031WonderSpeedButton` | 奇观加速按钮（注册 eLClick） |
| `Siqi0031WonderSpeedButtonIcon` | Image | — | 按钮图标（ICON_UNITCOMMAND_WONDER_PRODUCTION） |

### 通用挂载模式（UnitPanel 扩展）

这三个 XML 文件使用相同的挂载模式：

```lua
function Initialize()
    local pContext = ContextPtr:LookUpControl("/InGame/UnitPanel/StandardActionsStack")
    if pContext then
        Controls.XXXButtonGrid:ChangeParent(pContext)
        Controls.XXXButton:RegisterCallback(Mouse.eLClick, OnXXXButtonClicked)
    end
    Events.UnitSelectionChanged.Add(OnUnitSelectionChanged)
    Events.UnitMoveComplete.Add(OnUnitMoveComplete)
end
Events.LoadGameViewStateDone.Add(Initialize)
```

### WB_SELECT_PLOT 地块选择模式（MiuMiu 独有）

```lua
-- 进入地块选择模式
UI.SetInterfaceMode(InterfaceModeTypes.SELECTION)
UI.SetInterfaceMode(InterfaceModeTypes.WB_SELECT_PLOT)
m_IsInWBInterfaceMode = true
Controls.MiuMiuButton:SetSelected(true)

-- 高亮可用地块
UILens.SetLayerHexesArea(HEX_COLORING_MOVEMENT, Game.GetLocalPlayer(), validPlots)
UILens.ToggleLayerOn(HEX_COLORING_MOVEMENT)

-- 监听地块点击
LuaEvents.WorldInput_WBSelectPlot.Add(OnSelectPlot)

-- 退出时清理
function QuitWBInterfaceMode(ifChangeInterfaceMode)
    if ifChangeInterfaceMode then
        UI.SetInterfaceMode(InterfaceModeTypes.SELECTION)
    end
    UILens.ClearLayerHexes(HEX_COLORING_MOVEMENT)
    UILens.ToggleLayerOff(HEX_COLORING_MOVEMENT)
    m_IsInWBInterfaceMode = false
    Controls.MiuMiuButton:SetSelected(false)
end
```

### 添加新控件模板

```xml
<!-- 新技能按钮模板（有下拉面板） -->
<Grid ID="NewSkillButtonGrid" Anchor="R,B" Size="auto,41" AutoSizePadding="6,0" 
      Texture="SelectionPanel_ActionGroupSlot" SliceCorner="5,19" SliceSize="1,1" 
      SliceTextureSize="12,41" ConsumeMouse="1" Alpha="1" Hidden="1">
    <Button ID="NewSkillButton" Anchor="C,B" Size="44,53" Texture="UnitPanel_ActionButton">
        <Image ID="NewSkillButtonIcon" Anchor="C,C" Offset="0,-2" Size="38,38" 
               Texture="ICON_SKILL.png"/>
    </Button>
    <Container ID="NewSkillSelectContainer" Anchor="C,B" Size="280,360" Offset="0,60">
        <Grid Size="parent,parent" Texture="Controls_ContainerBlue" 
              SliceStart="0,0" SliceCorner="3,3" SliceSize="9,9" SliceTextureSize="16,16"/>
        <Label ID="NewSkillSelectTitle" Anchor="C,T" Offset="0,10" 
               Style="FontFlair24" String="LOC_SKILL_SELECT_TITLE"/>
        <ScrollPanel ID="NewSkillSelectScrollPanel">
            <Stack ID="NewSkillSelectStack" Anchor="C,T" StackGrowth="Down"/>
        </ScrollPanel>
    </Container>
</Grid>
```

```lua
-- Lua 端
local m_InstanceIM = InstanceManager:new("NewSkillSlot", "SelectButton", Controls.NewSkillSelectStack)
```
