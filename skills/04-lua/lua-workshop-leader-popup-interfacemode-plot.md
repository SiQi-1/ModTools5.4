# 自定义 InterfaceMode + 地块选择高亮（来源：工坊 3665503799 Black Shores / 3462397703 Herrscher Finality / 3550604297 Tara）

## 做什么
创建一个自定义界面模式（InterfaceMode），让玩家选中单位后点击按钮进入"选择目标地块"模式，高亮有效地块区域，玩家点击有效地块后执行操作（瞬移/技能释放/附身）。

## 核心流程

```
选中单位 → 点击操作按钮
  → SetInterfaceMode(WB_SELECT_PLOT)
    → 计算有效地块 → UILens.SetLayerHexesArea 高亮
      → 玩家点击地块 → 校验是否有效 → EXECUTE_SCRIPT 执行操作
        → Quit: 右键/ESC/模式切换 → 清除高亮 → 回到 SELECTION
```

---

## 一、自定义 InterfaceMode 注册（需要时）

### 来源：Tara (3550604297) DeadFlame 附身模式

```lua
-- 注册自定义 InterfaceModeType
InterfaceModeTypes.TARA_DEADFLAME_POSSESS = DB.MakeHash("INTERFACEMODE_TARA_DEADFLAME_POSSESS")
```

**注意**：大多数场景不需要注册新类型，直接复用游戏的 `InterfaceModeTypes.WB_SELECT_PLOT` 即可。

---

## 二、UILens 高亮图层

```lua
-- 创建一个专属的高亮图层哈希
local HEX_COLORING_MOVEMENT = UILens.CreateLensLayerHash("Hex_Coloring_Movement")

-- 进入模式时高亮
function EnterSelectPlotMode()
    local pUnit = UI.GetHeadSelectedUnit()
    local validPlots, hash = GetValidPlots(Game.GetLocalPlayer(), pUnit)

    if #validPlots > 0 then
        UILens.SetLayerHexesArea(HEX_COLORING_MOVEMENT, Game.GetLocalPlayer(), validPlots)
        UILens.ToggleLayerOn(HEX_COLORING_MOVEMENT)
    end

    m_Plots = hash  -- 保存供点击事件校验
end

-- 退出模式时清除
function ExitSelectPlotMode()
    UILens.ClearLayerHexes(HEX_COLORING_MOVEMENT)
    UILens.ToggleLayerOff(HEX_COLORING_MOVEMENT)
end
```

---

## 三、进入/退出界面模式的完整逻辑

### 来源：Herrscher Finality (3462397703) 量子跃迁

```lua
local m_IsInWBInterfaceMode = false
local m_Plots = nil

function OnActionButtonClicked()
    local pUnit = UI.GetHeadSelectedUnit()
    if not pUnit then return end

    if m_IsInWBInterfaceMode then
        QuitInterfaceMode(true)     -- 已处于选择模式，再点=取消
    else
        -- 先切到 SELECTION 清除其他模式，再切到 WB_SELECT_PLOT
        UI.SetInterfaceMode(InterfaceModeTypes.SELECTION)
        UI.SetInterfaceMode(InterfaceModeTypes.WB_SELECT_PLOT)
        m_IsInWBInterfaceMode = true
        Controls.MyButton:SetSelected(true)

        local validPlots, hash = GetValidPlots(Game.GetLocalPlayer(), pUnit)
        m_Plots = hash
        if #validPlots > 0 then
            UILens.SetLayerHexesArea(HEX_COLORING_MOVEMENT, Game.GetLocalPlayer(), validPlots)
            UILens.ToggleLayerOn(HEX_COLORING_MOVEMENT)
        end
    end
end

function QuitInterfaceMode(ifChangeInterfaceMode)
    if ifChangeInterfaceMode then
        UI.SetInterfaceMode(InterfaceModeTypes.SELECTION)
    end
    UILens.ClearLayerHexes(HEX_COLORING_MOVEMENT)
    UILens.ToggleLayerOff(HEX_COLORING_MOVEMENT)
    m_IsInWBInterfaceMode = false
    Controls.MyButton:SetSelected(false)
    m_Plots = nil
end
```

---

## 四、监听地块点击事件

```lua
-- 注册 WorldInput 的地块选择事件
LuaEvents.WorldInput_WBSelectPlot.Add(OnSelectPlot)

function OnSelectPlot(plotId, plotEdge, boolDown, rButton)
    if not m_IsInWBInterfaceMode then return end

    if not boolDown then    -- 鼠标松开时才处理
        if rButton then     -- 右键 = 取消
            QuitInterfaceMode(true)
        else                -- 左键 = 尝试执行
            if m_Plots and m_Plots[plotId] == 1 then  -- 校验是否有效
                local pUnit = UI.GetHeadSelectedUnit()
                local plot = Map.GetPlotByIndex(plotId)

                QuitInterfaceMode(true)

                UI.RequestPlayerOperation(Game.GetLocalPlayer(),
                    PlayerOperations.EXECUTE_SCRIPT, {
                        OnStart = "MyActionName",
                        UnitID = pUnit:GetID(),
                        X = plot:GetX(),
                        Y = plot:GetY(),
                    }
                )
            end
        end
    end
end
```

---

## 五、监听 InterfaceMode 变化（防止冲突）

```lua
Events.InterfaceModeChanged.Add(function(oldMode, newMode)
    -- 当从 WB_SELECT_PLOT 切出去却未经过自己的 Quit 函数时
    if m_IsInWBInterfaceMode and oldMode == InterfaceModeTypes.WB_SELECT_PLOT then
        QuitInterfaceMode(false)  -- 不改变模式，只清理高亮
    end
end)
```

---

## 六、有效地块计算（BFS 范围搜索）

```lua
function Map.GetNeighborPlots(x, y, radius)
    local plots = {}
    local centerPlot = Map.GetPlot(x, y)
    if not centerPlot then return plots end

    local queue = { {plot=centerPlot, distance=0} }
    local visited = {}
    visited[centerPlot:GetIndex()] = true

    while #queue > 0 do
        local current = table.remove(queue, 1)
        local currentPlot, currentDist = current.plot, current.distance

        if currentDist > 0 then
            table.insert(plots, currentPlot)
        end

        if currentDist < radius then
            for direction = 0, 5 do  -- 六边形 6 方向
                local neighborPlot = Map.GetAdjacentPlot(
                    currentPlot:GetX(), currentPlot:GetY(), direction)
                if neighborPlot and not visited[neighborPlot:GetIndex()] then
                    visited[neighborPlot:GetIndex()] = true
                    table.insert(queue, {plot=neighborPlot, distance=currentDist + 1})
                end
            end
        end
    end
    return plots
end

function GetValidPlots(playerID, pUnit)
    local validPlots, hash = {}, {}
    local nearby = Map.GetNeighborPlots(pUnit:GetX(), pUnit:GetY(), 6)

    for _, plot in ipairs(nearby) do
        if IsPlotValid(plot, playerID, pUnit) then
            local index = plot:GetIndex()
            table.insert(validPlots, index)
            hash[index] = 1
        end
    end
    return validPlots, hash
end

function IsPlotValid(pPlot, playerID, pUnit)
    -- 1. 可见性检查
    local pVisibility = PlayersVisibility[playerID]
    if not pVisibility or not pVisibility:IsRevealed(pPlot:GetIndex()) then
        return false
    end

    -- 2. 通行性检查
    if pPlot:IsImpassable() then return false end

    -- 3. 可到达性检查（可选，开销较大）
    local pathInfo = UnitManager.GetMoveToPathEx(pUnit, pPlot:GetIndex())
    if table.count(pathInfo.plots) <= 1 then return false end

    -- 4. 敌方单位检查
    local unitList = Units.GetUnitsInPlotLayerID(pPlot:GetX(), pPlot:GetY(), MapLayers.ANY)
    for _, unit in ipairs(unitList) do
        if playerID ~= unit:GetOwner() and pVisibility:IsUnitVisible(unit) then
            return false
        end
    end

    -- 5. 水域/陆地限制（按单位类型）
    local unitInfo = GameInfo.Units[pUnit:GetType()]
    if unitInfo.Domain == "DOMAIN_LAND" and pPlot:IsWater() and not pPlot:IsCoastalLand() then
        return false
    end

    return true
end
```

---

## 七、Unit 选中/移动事件联动

```lua
-- 选择其他单位时重置
Events.UnitSelectionChanged.Add(function(playerID, unitID, x, y, z, bSelected, bEditable)
    if playerID ~= Game.GetLocalPlayer() then return end
    if bSelected then
        RefreshButton()   -- 刷新按钮可见性/可用性
    end
end)

-- 单位移动完成时隐藏按钮
Events.UnitMoveComplete.Add(function(playerID, unitID)
    if playerID == Game.GetLocalPlayer() then
        Controls.MyButtonGrid:SetHide(true)
    end
end)

-- 移动力耗尽时隐藏
Events.UnitMovementPointsCleared.Add(function()
    Controls.MyButtonGrid:SetHide(true)
end)
```

---

## 八、完整初始化模板

```lua
function Initialize()
    -- 1. 注入按钮到 UnitPanel
    local pContext = ContextPtr:LookUpControl("/InGame/UnitPanel/StandardActionsStack")
    if pContext then
        Controls.MyButtonGrid:ChangeParent(pContext)
        Controls.MyButton:RegisterCallback(Mouse.eLClick, OnActionButtonClicked)
    end

    -- 2. 监听事件
    Events.UnitSelectionChanged.Add(OnUnitSelectionChanged)
    Events.UnitMoveComplete.Add(OnUnitMoveComplete)
    Events.UnitMovementPointsCleared.Add(OnUnitMovementPointsCleared)
    Events.InterfaceModeChanged.Add(OnInterfaceModeChanged)

    -- 3. 注册地块选择（关键！）
    LuaEvents.WorldInput_WBSelectPlot.Add(OnSelectPlot)
end
Events.LoadGameViewStateDone.Add(Initialize)
```

---

## XML 配合

### 用到的 XML 文件

| 来源 Mod | XML 文件路径 | 作用 |
|----------|------------|------|
| Black Shores (3665503799) | `UI/Leader_CML/CML_Switcher_BS.xml` 等 | UnitPanel 按钮 Grid（触发 InterfaceMode） |
| Herrscher Finality (3462397703) | `UI/Additions/XXX.xml`（推断） | 量子跃迁按钮 |
| Tara (3550604297) | `UI/Additions/XXX.xml`（推断） | DeadFlame 附身按钮 |

### 控件 ID 对照

此模式的 XML 与 `lua-workshop-leader-unit-panel-injection.md` 中的单按钮模板完全一致：

| XML 控件 ID | 类型 | Lua 角色 |
|------------|------|---------|
| `MyButtonGrid` | `Grid` | 根容器，挂载到 `StandardActionsStack` |
| `MyButton` | `Button` | 操作按钮，注册 `Mouse.eLClick` 进入/退出 WB_SELECT_PLOT 模式 |

### Instance 模板

```xml
<Context>
    <Grid ID="MyButtonGrid" Anchor="R,B" Size="auto,41"
          Texture="SelectionPanel_ActionGroupSlot"
          SliceCorner="5,19" SliceSize="1,1" SliceTextureSize="12,41"
          ConsumeMouse="1" Hidden="1">
        <Button ID="MyButton" Anchor="C,B" Size="44,53"
                Texture="UnitPanel_ActionButton">
            <Image ID="MyButtonIcon" Anchor="C,C" Offset="0,-2"
                   Size="38,38" Icon="ICON_MY_ACTION"/>
        </Button>
    </Grid>
</Context>
```

### 可复用 XML

- **UnitPanel 单按钮 Grid**：与 `lua-workshop-leader-unit-panel-injection.md` 共用模板
- **XLens 层**在 Lua 中通过 `UILens.CreateLensLayerHash()` 创建，无需 XML
- **自定义 InterfaceModeType** 在 Lua 中通过 `DB.MakeHash()` 注册，无需 XML
- 作为 Context Additions 注册到 modinfo
