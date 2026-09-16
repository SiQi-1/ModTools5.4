# AOE战斗引擎（来源：0013）

## 做什么
近战单位推进（attacker advances）后，对攻击目标周围1格内所有敌方战斗单位和区域造成溅射伤害。伤害公式为指数型，与双方战斗力差值相关：`(12 + rand(6)) * e^((attCombat - defCombat) * 0.04)`。对区域伤害上限为50。

## 触发条件
- 单位必须拥有属性 `PEN_XIANZHOU_ENABLE_AOE_COMBAT` > 0
- 必须是近战推进战斗（`ATTACKER_ADVANCES` = true，即近战击杀/击退）
- 单位必须有 ZoneOfControl（判定为 ZOC 单位才触发）

## 涉及文件和函数

| 文件 | 函数 | 作用 |
|------|------|------|
| `Siqi_Leaders_0013_Scripts.lua` | `XianZhouOnCombat(pCombatResult)` | Combat 事件入口，检查条件后调用 AOE |
| `Siqi_Leaders_0013_Scripts.lua` | `XianZhouAdjUnit(attInfo, defInfo, iX, iY, iRange, iCombat)` | AOE 核心：遍历邻格，对单位和区域分别计算伤害 |
| `Siqi_Leaders_0013_Scripts.lua` | `IsCombatUnits(pUnit)` | 判断单位是否有战斗力（Combat/RangedCombat/Bombard > 0） |
| `Siqi_Leaders_0013_Scripts.lua` | `IsZOCUnits(pUnit)` | 判断单位是否有 ZoneOfControl |

## 核心代码

```lua
-- 战斗入口
function XianZhouOnCombat (pCombatResult)
    local attackeradvance = pCombatResult[CombatResultParameters.ATTACKER_ADVANCES]
    if attackeradvance then
        local attacker = pCombatResult[CombatResultParameters.ATTACKER]
        local attInfo = attacker[CombatResultParameters.ID]
        local attUnit = UnitManager.GetUnit(attInfo.player, attInfo.id)
        local defender = pCombatResult[CombatResultParameters.DEFENDER]
        local defInfo = defender[CombatResultParameters.ID]
        local defUnit = UnitManager.GetUnit(defInfo.player, defInfo.id)

        if attUnit and attUnit:GetProperty('PEN_XIANZHOU_ENABLE_AOE_COMBAT') and attUnit:GetProperty('PEN_XIANZHOU_ENABLE_AOE_COMBAT') > 0 then
            local iCombat = attUnit:GetCombat()
            local location = attUnit:GetLocation()
            XianZhouAdjUnit(attInfo, defInfo, location.x, location.y, 1, iCombat)
        end
    end
end

-- AOE 核心逻辑
function XianZhouAdjUnit(attInfo, defInfo, iX, iY, iRange, iCombat)
    local plots = Map.GetNeighborPlots(iX, iY, iRange)
    local attUnit = UnitManager.GetUnit(attInfo.player, attInfo.id)
    local defUnit = UnitManager.GetUnit(defInfo.player, defInfo.id)
    if attUnit then
        for i, adjPlot in ipairs(plots) do
            if adjPlot then
                -- 对单位：检查是否为敌方战斗单位
                local pUnitList = Units.GetUnitsInPlot(adjPlot)
                -- ... 遍历单位，用指数公式计算伤害
                local nDamage = math.ceil(
                    (12 + Game.GetRandNum(6)) * e^((iCombat - nCombat) * 0.04)
                )

                -- 对区域：检查是否有敌方区域，伤害上限50
                local nDamage = math.min(50, math.ceil(
                    (12 + Game.GetRandNum(6)) * e^((iCombat - districtDefense) * 0.04)
                ))
                -- 先打外墙(DISTRICT_OUTER)，外墙破后打守军(DISTRICT_GARRISON)
            end
        end
    end
end
```

## 关键设计要点

1. **双重目标**：同时处理邻格单位和邻格区域，两套伤害计算逻辑
2. **战斗公式**：`e^((攻防差)*0.04)` 指数型，攻防差越大战力差距越大（非简单的加减法）
3. **偏转保护**：攻击主目标（`defUnit`）本身不会被 AOE 二次伤害（`NeighborUnit ~= defUnit`）
4. **区域伤害链**：先削减外墙血量(`DISTRICT_OUTER`)，外墙为0后才打击守军血量(`DISTRICT_GARRISON`)
5. **水域豁免**：水域地块(`adjPlot:IsWater()`)不触发 AOE
6. **区域防御为0跳过**：`districtDefense > 0`，对无防御区域（如未完成的营地）不造成伤害

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `UI/Siqi_Leaders_0013_UI.xml` | 占卜（Divination）系统 — 单位操作面板扩展 |
| `UI/Siqi_Leaders_U0013.xml` | 相位穿梭（KTA/Quantum Leap） — 单位瞬移 |
| `UI/CityBannerManager.xml` | 城市横幅扩展 — WMD 攻击按钮（核弹/热核/终焉） |
| `UI/TopPanel.xml` | 顶部面板扩展 — 产出堆 + WMD 计数 + 资源显示 |

### 控件 ID 与 Lua Controls.xxx 对照

#### Siqi_Leaders_0013_UI.xml（占卜系统）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `XianZhouDivinationGrid` | Grid | `Controls.XianZhouDivinationGrid` | 占卜按钮外层容器 |
| `XianZhouDivinationButton` | Button | `Controls.XianZhouDivinationButton` | 占卜入口按钮（44x53） |
| `XianZhouDivinationIcon` | Image | — | 按钮图标（ICON_BUILDING_SIQI_B0013） |
| `XianZhouDivinationContainer` | Container | `Controls.XianZhouDivinationContainer` | 占卜选项下拉面板（44x160） |
| `XianZhouButtonStack` | Stack | — | 三个占卜按钮的 Stack（StackGrowth=Down） |
| `XianZhouDivinationScienceButton` | Button | `Controls.XianZhouDivinationScienceButton` | 科技完成按钮（含 ToolTip） |
| `XianZhouDivinationCultureButton` | Button | `Controls.XianZhouDivinationCultureButton` | 文化完成按钮 |
| `XianZhouDivinationProductionButton` | Button | `Controls.XianZhouDivinationProductionButton` | 生产力完成按钮 |
| `XianZhouDivinationScienceIcon` | Image | — | 科技图标 |
| `XianZhouDivinationCultureIcon` | Image | — | 文化图标 |
| `XianZhouDivinationProductionIcon` | Image | — | 生产力图标 |

**交互流程：**
```lua
-- 占卜按钮切换下拉面板
function OnXianZhouShowAvailableClicked()
    if Controls.XianZhouDivinationContainer:IsHidden() then
        Controls.XianZhouDivinationButton:SetSelected(true)
        Controls.XianZhouDivinationContainer:SetHide(false)
        -- 动态更新各按钮的 ToolTip（含科技/文化/生产队列信息）
        Controls.XianZhouDivinationScienceButton:SetToolTipString(...)
        Controls.XianZhouDivinationCultureButton:SetToolTipString(...)
        Controls.XianZhouDivinationProductionButton:SetToolTipString(...)
    else
        Controls.XianZhouDivinationButton:SetSelected(false)
        Controls.XianZhouDivinationContainer:SetHide(true)
    end
end
```

#### Siqi_Leaders_U0013.xml（相位穿梭）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `KTAButtonGrid` | Grid | `Controls.KTAButtonGrid` | 相位穿梭按钮容器 |
| `KTAButton` | Button | `Controls.KTAButton` | 相位穿梭入口按钮（44x53） |
| `KTAButtonIcon` | Image | — | 按钮图标（ICON_UNIT_SIQI_U0013） |

**挂载 + WB_SELECT_PLOT 模式：**
```lua
-- 初始化挂载到 StandardActionsStack
local pContext = ContextPtr:LookUpControl("/InGame/UnitPanel/StandardActionsStack")
Controls.KTAButtonGrid:ChangeParent(pContext)
Controls.KTAButton:RegisterCallback(Mouse.eLClick, OnQuantumLeapButtonClickedk)

-- 点击进入地块选择模式（6 格范围，支持路径检查）
function OnQuantumLeapButtonClickedk()
    UI.SetInterfaceMode(InterfaceModeTypes.SELECTION)
    UI.SetInterfaceMode(InterfaceModeTypes.WB_SELECT_PLOT)
    Controls.KTAButton:SetSelected(true)
    -- 高亮可用地块
    local plots, hash = GetQuantumLeapPlotsk(playerID, pUnit)
    UILens.SetLayerHexesArea(HEX_COLORING_MOVEMENT, Game.GetLocalPlayer(), plots)
    UILens.ToggleLayerOn(HEX_COLORING_MOVEMENT)
end

-- 选择地块后发送 EXECUTE_SCRIPT
UI.RequestPlayerOperation(playerID, PlayerOperations.EXECUTE_SCRIPT, {
    OnStart = 'U0013LeapAction1',
    UnitID = pUnit:GetID(),
    X = ..., Y = ...
})
Controls.KTAButtonGrid:SetHide(true)
```

#### CityBannerManager.xml（WMD 城市横幅）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `CityBanners` | Container | — | 城市横幅容器 |
| `CityDistrictIcons` | Container | — | 区域图标容器 |

**WMD Banner Instance（WMDBanner）：**

| 子控件（ID） | 类型 | 用途 |
|-------------|------|------|
| `Anchor` | ZoomAnchor | 缩放锚点 |
| `WMDBannerContainer` | Container | WMD 横幅容器（138x40） |
| `Banner_Base` | Grid | 横幅背景 |
| `NukeCountLabel` | Label | 核弹数量 |
| `NukeBombButton` | Button | 核弹发射按钮 |
| `ThermoNukeCountLabel` | Label | 热核弹数量 |
| `ThermoNukeBombButton` | Button | 热核弹发射按钮 |
| `ZhongYanAttackCountLabel` | Label | 终焉攻击数量 |
| `ZhongYanAttackButton` | Button | 终焉攻击发射按钮 |

#### TopPanel.xml（顶部产出面板扩展）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `Backing` | Grid | — | 顶部横条背景 |
| `InfoStack` | Stack | `Controls.InfoStack` | 主信息堆（含 YieldStack + StaticInfoStack） |
| `YieldStack` | Stack | `Controls.YieldStack` | 产出按钮堆（InstanceManager 父容器） |
| `StaticInfoStack` | Stack | `Controls.StaticInfoStack` | 静态信息堆（贸易/使者/核弹） |
| `TradeRoutes` | Grid | `Controls.TradeRoutes` | 贸易路线容器 |
| `TradeRoutesActive` | Label | `Controls.TradeRoutesActive` | 活跃贸易路线数 |
| `TradeRoutesCapacity` | Label | `Controls.TradeRoutesCapacity` | 贸易路线容量 |
| `Envoys` | Grid | `Controls.Envoys` | 使者容器 |
| `EnvoysNumber` | Label | `Controls.EnvoysNumber` | 使者数量 |
| `EnvoysMeter` | Meter | `Controls.EnvoysMeter` | 使者进度条 |
| `NuclearDevices` | Grid | `Controls.NuclearDevices` | 核弹容器 |
| `NuclearDeviceCount` | Label | `Controls.NuclearDeviceCount` | 核弹数量 |
| `ThermoNuclearDevices` | Grid | `Controls.ThermoNuclearDevices` | 热核弹容器 |
| `ThermoNuclearDeviceCount` | Label | `Controls.ThermoNuclearDeviceCount` | 热核弹数量 |
| `ZhongYanAttack` | Grid | `Controls.ZhongYanAttack` | 终焉攻击容器 |
| `ZhongYanAttackCount` | Label | `Controls.ZhongYanAttackCount` | 终焉攻击数量 |
| `Resources` | Grid | — | 资源容器 |
| `ResourceStack` | Stack | `Controls.ResourceStack` | 资源列表堆（InstanceManager 父容器） |
| `MenuButton` | Button | — | 菜单按钮 |
| `CivpediaButton` | Button | — | 百科按钮 |
| `Turns` | Label | — | 回合数 |
| `CurrentDate` | Label | — | 当前日期文字 |

**Instance 模板：**

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `YieldButton_SingleLabel` | 单行产出按钮（产出+每回合） | `YieldBacking`(GridButton), `YieldIconString`(Label), `YieldPerTurn`(Label) |
| `YieldButton_DoubleLabel` | 双行产出按钮（产出+余额+每回合） | `YieldBacking`(GridButton), `YieldIconString`(Label), `YieldBalance`(Label), `YieldPerTurn`(Label) |
| `ResourceInstance` | 资源显示项 | `Top`(Container), `ResourceText`(Label), `ResourceVelocity`(Image) |
| `TopBarButtonInstance` | 顶部栏按钮模板 | `Top`(Container, 50x36) |
| `WMDBanner` | WMD 城市横幅 | `Anchor`(ZoomAnchor), `WMDBannerContainer`(Container), 三种弹头按钮 |
| `TribeBanner` | 蛮族部落横幅 | `TribeBannerContainer`(Container), `ConversionBar`(TextureBar) |

```lua
-- InstanceManager 初始化
m_YieldButtonSingleManager = InstanceManager:new("YieldButton_SingleLabel", "Top", Controls.YieldStack)
m_YieldButtonDoubleManager = InstanceManager:new("YieldButton_DoubleLabel", "Top", Controls.YieldStack)
m_kResourceIM = InstanceManager:new("ResourceInstance", "Top", Controls.ResourceStack)

-- 刷新时重新计算大小
Controls.YieldStack:CalculateSize()
Controls.StaticInfoStack:CalculateSize()
Controls.InfoStack:CalculateSize()
```

### 添加新控件模板

```xml
<!-- 新增单位技能按钮（占卜风格，带下拉面板） -->
<Grid ID="NewSkillGrid" Anchor="R,B" Size="auto,41" AutoSizePadding="6,0" 
      Texture="SelectionPanel_ActionGroupSlot" SliceCorner="5,19" 
      SliceSize="1,1" SliceTextureSize="12,41" ConsumeMouse="1" Alpha="0.75">
    <Button ID="NewSkillButton" Anchor="C,B" Size="44,53" Texture="UnitPanel_ActionButton">
        <Image ID="NewSkillIcon" Anchor="C,C" Offset="0,-2" Size="45,45" Icon="ICON_BUILDING_YOURS"/>
    </Button>
    <Container ID="NewSkillContainer" Anchor="C,B" Size="44,160" Offset="0,50">
        <Stack ID="NewSkillStack" Offset="0,0" Padding="-2" StackGrowth="Down">
            <Button ID="NewSkillOption1" Anchor="C,T" Size="44,53" Texture="UnitPanel_ActionButton" 
                    ToolTip="LOC_NEW_SKILL_OPTION1_TOOLTIP">
                <Image ID="NewSkillOption1Icon" Anchor="C,C" Offset="0,-2" Size="40,40" 
                       Icon="ICON_NOTIFICATION_CHOOSE_TECH"/>
            </Button>
        </Stack>
    </Container>
</Grid>
```

```lua
-- 挂载模式
local pContext = ContextPtr:LookUpControl("/InGame/UnitPanel/StandardActionsStack")
Controls.NewSkillGrid:ChangeParent(pContext)
Controls.NewSkillButton:RegisterCallback(Mouse.eLClick, OnNewSkillButtonClicked)
Controls.NewSkillOption1:RegisterCallback(Mouse.eLClick, OnNewSkillOption1Clicked)
```
