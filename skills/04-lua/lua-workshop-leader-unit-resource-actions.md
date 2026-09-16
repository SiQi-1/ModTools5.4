# 单位资源操作面板（来源：EagleUnion StLouis、GUMOON EarthEngineer、Iberia PenalBattalion）

## 做什么
在单位面板中嵌入自定义的操作面板，允许单位在所在位置执行资源创建/移除/改良/净化等地图操作。使用 InstanceManager 动态生成资源/选项网格。

## 涉及 Mod

| Mod | 单位 | 能力 |
|-----|------|------|
| EagleUnion StLouis | Explorer | 创建随机奢侈资源(3列网格)、移除资源并收获、改良资源并吞并地块 |
| GUMOON | EarthEngineer | 在无主地块随机创建资源 |
| Iberia XP | PenalBattalion | 净化被 ProfoundSilence 影响的单元格 |

## 模式分类

### 类型A：动态资源网格面板（StLouis Create）

扩展 UnitPanel 右侧，以浮动面板+InstanceManager 显示可用资源网格。

### 类型B：条件性单按钮（EarthEngineer / PenalBattalion）

注入按钮到 StandardActionsStack，满足条件时激活。

### 类型C：混合模式（StLouis Remove + Improv）

一个按钮网格 + 一个浮动资源面板。

## 类型A：动态资源网格面板

### XML 定义

```xml
<Context>
    <!-- 按钮Grid（挂载到StandardActionsStack） -->
    <Grid ID="StLouisGrid" Anchor="R,B" Size="Auto,41"
          Texture="SelectionPanel_ActionGroupSlot"
          SliceCorner="5,19" SliceSize="1,1" SliceTextureSize="12,41"
          ConsumeMouse="1" Hidden="1">
        <Stack ID="StLouisActionStack" Anchor="C,B"
               StackGrowth="Right" StackPadding="2">
            <Button ID="Remove" Size="44,53" Texture="UnitPanel_ActionButton">
                <Image ID="RemoveIcon" Size="38,38" Icon="ICON_STLOUIS_REMOVE"/>
            </Button>
            <Button ID="Improv" Size="44,53" Texture="UnitPanel_ActionButton">
                <Image ID="ImprovIcon" Size="38,38" Icon="ICON_STLOUIS_IMPROV"/>
            </Button>
        </Stack>
    </Grid>

    <!-- 资源面板（挂载到UnitPanelSlide，显示在右侧） -->
    <Grid ID="ResourcePanel" Anchor="R,B" Offset="501,0"
          Size="51,160" Texture="UnitPanel_SpecialActionsFrame"
          SliceCorner="14,14">
        <Stack ID="ResourcesStack" Anchor="R,T" Offset="11,0"
               StackGrowth="Left" Padding="6" />
    </Grid>

    <!-- 资源列实例（3行/列） -->
    <Instance Name="ResourceColumnInstance">
        <Container ID="Top" Size="38,140">
            <Image ID="Row1" Anchor="L,T" Offset="0,15"
                   Texture="UnitPanel_SpecialActionSlot" />
            <Image ID="Row2" Anchor="L,T" Offset="0,60"
                   Texture="UnitPanel_SpecialActionSlot" />
            <Image ID="Row3" Anchor="L,T" Offset="0,105"
                   Texture="UnitPanel_SpecialActionSlot" />
        </Container>
    </Instance>

    <!-- 单个资源按钮 -->
    <Instance Name="ResourceInstance">
        <Button ID="ResourceButton" Anchor="L,T" Offset="-4,-4"
                Size="44,53" Texture="Controls_IconButton.dds">
            <Image ID="ResourceIcon" Anchor="C,C" Offset="0,-1"
                   Size="38,38" Icon="ICON_STLOUIS_CREATE"/>
        </Button>
    </Instance>
</Context>
```

### Lua 初始化：双重 ChangeParent

资源面板挂载到 UnitPanelSlide（可滑动区域），使其随 UnitPanel 一起滑动：

```lua
function Init()
    -- 1. 资源面板挂载到 UnitPanelSlide
    local PanelSlide = ContextPtr:LookUpControl("/InGame/UnitPanel/UnitPanelSlide")
    if PanelSlide then
        Controls.ResourcePanel:ChangeParent(PanelSlide)
    end

    -- 2. 按钮Grid挂载到 StandardActionsStack
    local ActionStack = ContextPtr:LookUpControl("/InGame/UnitPanel/StandardActionsStack")
    if ActionStack then
        Controls.StLouisGrid:ChangeParent(ActionStack)
        RemoveButton:Register()
        ImprovButton:Register()
    end

    Refresh()
end
Events.LoadGameViewStateDone.Add(Init)
```

### 资源数据准备：EagleResources 辅助类

```lua
-- EagleCore 中的资源辅助
Luxuries = EagleResources:new({ ["RESOURCECLASS_LUXURY"] = true })
-- 返回可在该地块放置的资源列表
local resources = Luxuries:GetPlaceableResources(plot)
-- 每个 resource 包含: .Type, .Name, .Icon, .Index, :GetChangeYieldsTooltip()
```

### 动态资源网格生成

每 3 个资源一组（3行/列），动态计算面板大小：

```lua
local m_ResourceIM = InstanceManager:new("ResourceColumnInstance", "Top", Controls.ResourcesStack)

Refresh = function(self, unit)
    m_ResourceIM:DestroyInstances()
    m_ResourceIM:ResetInstances()

    if unit:GetActionCharges() > 0 then
        local detail = self.GetDetail(unit)  -- 返回 {Disable, Resource = {...}}
        local count = #detail.Resource

        if count == 0 then
            Controls.ResourcePanel:SetHide(true)
            return
        end

        -- 每列3行，遍历填充
        for i = 1, count, 3 do
            local columnInstance = m_ResourceIM:GetInstance()
            for iRow = 1, 3 do
                if (i + iRow - 1) <= count then
                    local resource = detail.Resource[i + iRow - 1]
                    local slotName = "Row" .. tostring(iRow)

                    -- 在列中的特定行构建按钮实例
                    local instance = {}
                    ContextPtr:BuildInstanceForControl("ResourceInstance",
                        instance, columnInstance[slotName])

                    -- 设置图标
                    instance.ResourceIcon:SetIcon('ICON_' .. resource.Type)

                    -- 设置回调
                    instance.ResourceButton:RegisterCallback(Mouse.eLClick,
                        function()
                            local pUnit = UI.GetHeadSelectedUnit()
                            if pUnit == nil then return end
                            local x, y = pUnit:GetX(), pUnit:GetY()
                            UI.RequestPlayerOperation(Game.GetLocalPlayer(),
                                PlayerOperations.EXECUTE_SCRIPT, {
                                    UnitID = pUnit:GetID(),
                                    X = x, Y = y,
                                    Index = resource.Index,
                                    OnStart = 'MyResourceCreated',
                                }
                            )
                            Network.BroadcastPlayerInfo()
                        end
                    )

                    -- 设置 tooltip：资源名 + 产量变化
                    local tooltip = Locale.Lookup('LOC_CREATE_RESOURCE',
                        resource.Icon, resource.Name)
                    tooltip = tooltip .. '[NEWLINE][NEWLINE]'
                        .. resource:GetChangeYieldsTooltip()
                    instance.ResourceButton:SetToolTipString(tooltip)
                end
            end
        end

        -- 动态设置面板大小
        Controls.ResourcesStack:CalculateSize()
        local stackWidth  = Controls.ResourcesStack:GetSizeX()
        local stackHeight = Controls.ResourcesStack:GetSizeY()
        Controls.ResourcePanel:SetSizeX(stackWidth + 24)
        Controls.ResourcePanel:SetSizeY(stackHeight + 20)

        -- 设置面板偏移（放在 UnitPanel 右侧）
        local container = ContextPtr:LookUpControl('/InGame/UnitPanel/UnitPanelBaseContainer')
        Controls.ResourcePanel:SetOffsetX(container:GetSizeX() + 162)
    else
        Controls.ResourcePanel:SetHide(true)
    end
end
```

### 地块条件检查

```lua
GetDetail = function(unit)
    local detail = { Disable = true, Resource = {} }

    -- 检查1：移动力
    if unit:GetMovesRemaining() == 0 then return detail end

    -- 检查2：地块无主（中立地块才能放置）
    local plot = Map.GetPlot(unit:GetX(), unit:GetY())
    if plot:GetOwner() ~= -1 then return detail end

    -- 检查3：地块无已有资源
    local index = plot:GetResourceType()
    local resourceHash = plot:GetResourceTypeHash()
    local resourceData = Players[unit:GetOwner()]:GetResources()
    if index ~= -1 and resourceData:IsResourceVisible(resourceHash) then
        return detail
    end

    -- 检查4：有可放置的奢侈资源
    detail.Resource = Luxuries:GetPlaceableResources(plot)
    if #detail.Resource == 0 then return detail end

    detail.Disable = false
    return detail
end
```

## 类型B：条件性单按钮（EarthEngineer）

### 地块条件：无主 + 无区域 + 无资源 + 无改良

```lua
function IsButtonHide()
    local pUnit = UI.GetHeadSelectedUnit()
    if pUnit == nil then return true end
    if pUnit:GetMovementMovesRemaining() == 0 then return true end

    local iX, iY = pUnit:GetX(), pUnit:GetY()

    if Map.GetPlot(iX, iY):IsOwned() then return true end

    local eDistrict = Map.GetPlot(iX, iY):GetDistrictID() or -1
    local eResource = Map.GetPlot(iX, iY):GetResourceType() or -1
    local eImprovement = Map.GetPlot(iX, iY):GetImprovementType() or -1

    if eDistrict < 0 and eResource < 0 and eImprovement < 0 then
        return false  -- 按钮可用
    end
    return true
end
```

### 随机资源选择（通过自定义数据库表）

```lua
function OnButtonClicked()
    local pUnit = UI.GetHeadSelectedUnit()
    local iX, iY = pUnit:GetX(), pUnit:GetY()
    local pPlot = Map.GetPlot(iX, iY)
    local iFeature = pPlot:GetFeatureType() or -1
    local iTerrain = pPlot:GetTerrainType()

    -- 根据地形/地貌从自定义表查询可用资源
    local Resources = {}
    if iFeature > -1 then
        local sFeature = GameInfo.Features[iFeature].FeatureType
        for row in GameInfo.NW_TABLE_BASE_RANDOM_RESOURCES() do
            if row.FeatureType == sFeature then
                Resources[row.ResourceType] = 1
            end
        end
    else
        local sTerrain = GameInfo.Terrains[iTerrain].TerrainType
        for row in GameInfo.NW_TABLE_BASE_RANDOM_RESOURCES() do
            if row.TerrainType == sTerrain then
                Resources[row.ResourceType] = 1
            end
        end
    end

    -- 转换为数组并随机选择
    local iResources = {}
    for key, _ in pairs(Resources) do
        table.insert(iResources, key)
    end

    if #iResources == 0 then
        UI.AddWorldViewText(0, Locale.Lookup('LOC_NO_RESOURCE_AVAILABLE'), iX, iY, 0)
    else
        local ResourceType = iResources[math.random(#iResources)]
        UI.RequestPlayerOperation(Game.GetLocalPlayer(),
            PlayerOperations.EXECUTE_SCRIPT, {
                OnStart = 'EarthEngineer_CreateResource',
                iX = iX, iY = iY,
                iUnit = pUnit:GetID(),
                ResourceType = ResourceType
            }
        )
        SimUnitSystem.SetAnimationState(pUnit, "ACTION_1", "IDLE")
    end
end
```

## 类型B2：净化按钮（PenalBattalion）

### 全局状态驱动：通过 Game.GetProperty 获取全局受影响地块

```lua
function RealizePlotNeedCleansing()
    m_kPlots = {}
    local pUnit = UI.GetHeadSelectedUnit()
    if pUnit ~= nil and not UI.IsGameCoreBusy() then
        local pUnitPlot = Map.GetPlot(pUnit:GetX(), pUnit:GetY())
        local CanCleansing = false

        -- 从全局 GameProperty 获取受影响地块集合
        local AffectedPlots = Game.GetProperty('ProfoundSilenceAffectingPlot') or {}
        for iPlot, _ in pairs(AffectedPlots) do
            local pPlot = Map.GetPlotByIndex(iPlot)
            local key = pPlot:GetProperty('IsProfoundSilenceAffected') or 0
            if key > 0 then
                table.insert(m_kPlots, iPlot)
                if pPlot:GetIndex() == pUnitPlot:GetIndex() then
                    CanCleansing = true
                end
            end
        end
        return CanCleansing
    end
    return false
end
```

### 带特效的净化执行

```lua
function OnButtonClicked()
    local pUnit = UI.GetHeadSelectedUnit()
    local iX, iY = pUnit:GetX(), pUnit:GetY()

    UI.RequestPlayerOperation(Game.GetLocalPlayer(),
        PlayerOperations.EXECUTE_SCRIPT, {
            OnStart = 'PenalBattalionCleansing',
            iX = iX, iY = iY,
            iUnit = pUnit:GetID()
        }
    )

    -- UI 端特效
    SimUnitSystem.SetAnimationState(pUnit, "ACTION_1", "IDLE")
    WorldView.PlayEffectAtXY("IBERIA_PENALBATTALION_CLEANSE", iX, iY)
    AssetPreview.DestroyAt(Map.GetPlot(iX, iY))

    Controls.ButtonGrid:SetHide(true)
end
```

## Gameplay 端执行（StLouis 三合一示例）

```lua
-- Scripts/EagleUnionStLouis.lua（AddGameplayScripts）

-- 结束单位回合
function StLouisEndTurn(unit)
    local curMoves = unit:GetMovesRemaining()
    UnitManager.ChangeMovesRemaining(unit, -curMoves)
end

-- 创建资源
function StLouisCreated(playerID, param)
    local plot = Map.GetPlot(param.X, param.Y)
    ResourceBuilder.SetResourceType(plot, param.Index, 1)  -- 放置资源

    local unit = UnitManager.GetUnit(playerID, param.UnitID)
    unit:ChangeActionCharges(-1)  -- 消耗行动次数
    StLouisEndTurn(unit)
    UnitManager.ReportActivation(unit, "STLOUIS_CREATED")  -- 触发动画
end

-- 移除资源
function StLouisRemoved(playerID, param)
    local plot = Map.GetPlot(param.X, param.Y)
    ResourceBuilder.SetResourceType(plot, -1)      -- 移除资源
    ImprovementBuilder.SetImprovementType(plot, -1) -- 移除改良（如有）

    local resource = resources:GetResource(param.Resource)
    resource:GrantHarvestYields(playerID, param.X, param.Y)  -- 给予收获产出

    local unit = UnitManager.GetUnit(playerID, param.UnitID)
    StLouisEndTurn(unit)
    UnitManager.ReportActivation(unit, "STLOUIS_REMOVED")
end

-- 改良地块（吞并中立地块）
function StLouisImprove(playerID, param)
    local unit = UnitManager.GetUnit(playerID, param.UnitID)
    -- 通过 Ability 系统吞并地块
    local unitAbility = unit:GetAbility()
    unitAbility:ChangeAbilityCount(ability, 1)
    unitAbility:ChangeAbilityCount(ability, -unitAbility:GetAbilityCount(ability))

    local plot = Map.GetPlot(param.X, param.Y)
    ImprovementBuilder.SetImprovementType(plot, param.Index, playerID)
    StLouisEndTurn(unit)
    UnitManager.ReportActivation(unit, "STLOUIS_IMPROVE")
end

GameEvents.StLouisCreated.Add(StLouisCreated)
GameEvents.StLouisRemoved.Add(StLouisRemoved)
GameEvents.StLouisImprove.Add(StLouisImprove)
```

## 事件监听要点

资源操作面板需要额外监听资源相关事件：

```lua
-- 资源相关全局事件
Events.ResourceAddedToMap.Add(Refresh)
Events.PlayerResourceChanged.Add(Refresh)
Events.ResourceRemovedFromMap.Add(Refresh)

-- 单位行动次数变化
Events.UnitChargesChanged.Add(Refresh)

-- 回合切换
Events.PhaseBegin.Add(Refresh)

-- 游戏加载后重新初始化资源数据
Events.LoadGameViewStateDone.Add(ReinitResources)
```

## 设计要点

1. **BuildInstanceForControl** 用于在已有 Instance 的子槽位中构建子 Instance（嵌套 InstanceManager）
2. **CalculateSize + SetSizeX/Y + SetOffsetX** 动态调整浮动面板大小和位置
3. **UnitPanelBaseContainer** 的 SizeX 用于计算偏移，使资源面板始终在 UnitPanel 右侧
4. **ActionCharges** (unit:GetActionCharges()) 用于限制资源创建次数
5. **ResourceBuilder.SetResourceType** 是 Gameplay 端放置/移除资源的 API
6. **ImprovementBuilder.SetImprovementType** 是 Gameplay 端放置/移除改良的 API
7. **GrantHarvestYields** 给予资源收获产出（科技解锁后）
8. **ChangeActionCharges(-1)** 消耗单位行动次数
9. **ChangeAbilityCount(ability, 1); ChangeAbilityCount(ability, -count)** 触发性地吞并地块
10. **三列布局**：每列 3 个按钮，`StackGrowth="Left"` 保证从右向左排列（与 UnitPanel 对齐）

---

## XML 配合

### 用到的 XML 文件

| 来源 Mod | XML 文件路径 | 类型 |
|----------|------------|------|
| EagleUnion StLouis (3091608915) | `UI/Additions/StLouisUnitPanel.xml` | 类型A + 类型C：资源网格 + 按钮组 |
| GUMOON (3574534861) | `UI/Additions/EarthEngineerUnitPanel.xml` | 类型B：单按钮 |
| Iberia XP (3391173367) | `Event_ProfoundSilence/UI/Additions/PenalBattalion/PenalBattalionCleansing.xml` | 类型B2：净化按钮 |

### 控件 ID 对照（类型A：动态资源网格面板）

| XML 控件 ID | 类型 | Lua 角色 |
|------------|------|---------|
| `StLouisGrid` | `Grid` | 按钮根容器，挂载到 `StandardActionsStack` |
| `StLouisActionStack` | `Stack` | 操作按钮水平 Stack（Remove/Improv） |
| `ResourcePanel` | `Grid` | 资源浮动面板根容器，挂载到 `UnitPanelSlide` |
| `ResourcesStack` | `Stack` | 资源列存放容器，`StackGrowth="Left"` |
| `ResourceColumnInstance` (Instance) | `Container` | 资源列模板（3行/列：Row1/Row2/Row3） |
| `ResourceInstance` (Instance) | `Button` | 单个资源按钮模板（含 `ResourceButton` + `ResourceIcon`） |

### Instance 模板（嵌套）

```xml
<!-- 资源列实例（每列3行） -->
<Instance Name="ResourceColumnInstance">
    <Container ID="Top" Size="38,140">
        <Image ID="Row1" Anchor="L,T" Offset="0,15"
               Texture="UnitPanel_SpecialActionSlot" />
        <Image ID="Row2" Anchor="L,T" Offset="0,60"
               Texture="UnitPanel_SpecialActionSlot" />
        <Image ID="Row3" Anchor="L,T" Offset="0,105"
               Texture="UnitPanel_SpecialActionSlot" />
    </Container>
</Instance>

<!-- 单个资源按钮 -->
<Instance Name="ResourceInstance">
    <Button ID="ResourceButton" Anchor="L,T" Offset="-4,-4"
            Size="44,53" Texture="Controls_IconButton.dds">
        <Image ID="ResourceIcon" Anchor="C,C" Offset="0,-1"
               Size="38,38" Icon="ICON_STLOUIS_CREATE"/>
    </Button>
</Instance>
```

### 可复用 XML

- **浮动资源面板**：`ResourcePanel` + `ResourcesStack` 模板可复用于任何需要动态生成网格图标的场景
- **嵌套 InstanceManager**：`ResourceColumnInstance`（外层容器） + `ResourceInstance`（内层按钮）的嵌套结构适用于所有需要行列网格的选择器
- **UnitPanel 双注入点**：StandardActionsStack（按钮）+ UnitPanelSlide（浮动面板），两个 ChangeParent 分别挂载
- 控件作为 Context Additions 注册到 modinfo
