# 单位传送/重新部署 + 透镜高亮（来源：EagleUnion Eldridge、Amphoreus Janus、Majo Witch）

## 做什么
选中单位后点击自定义传送按钮，进入地块选择模式；合法目的地高亮显示；点击目标地块执行传送；退出选择模式。

## 涉及 Mod

| Mod | 单位 | 能力 |
|-----|------|------|
| EagleUnion Eldridge | 彩虹计划 (Rainbow) | 传送到任意城市中心 |
| Amphoreus 翁法罗斯 | 缇宝 Janus | 从市中心传送到其他市中心 |
| Majo no Tabitabi | 魔女 Witch | 选中时显示光环范围（无交互） |

## 核心模式

```
[选中单位] → [点击传送按钮]
  → UI.SetInterfaceMode(WB_SELECT_PLOT)         -- 进入地块选择模式
  → UILens.SetLayerHexesArea(layer, player, plots) -- 高亮合法目标
  → UILens.ToggleLayerOn(layer)

[用户在地图上点击]
  → LuaEvents.WorldInput_WBSelectPlot(plotID, edge, lbtn, rbtn)
  → 如果右键 → 退出模式
  → 如果左键且合法 → EXECUTE_SCRIPT 传送 → 退出模式

[UI模式变化]
  → Events.InterfaceModeChanged(intPara, currentInterfaceMode)
  → 如果离开 WB_SELECT_PLOT → 取消
```

## 步骤 1：XLens 层定义

```lua
local g_HexColoring = UILens.CreateLensLayerHash("Hex_Coloring_Movement")

-- 注意：第二个参数传一个已有的游戏透镜层名，复用其颜色方案
-- 常用：Hex_Coloring_Movement, Hex_Coloring_Great_People 等
```

## 步骤 2：完整传送按钮实现

```lua
local m_IsActive = false
local m_ValidPlots = {}     -- 合法目标的 PlotIndex 集合
local m_ValidPlotsHash = {} -- Hash 表用于 O(1) 查找

TeleportButton = {
    GetTargetPlots = function(pUnit)
        local plots, hash = {}, {}
        local pPlayer = Players[pUnit:GetOwner()]

        -- 遍历城市，收集合法传送目标
        for _, city in pPlayer:GetCities():Members() do
            local plot = Map.GetPlot(city:GetX(), city:GetY())
            if CanUnitEnterPlot(pUnit, plot) then
                table.insert(plots, plot:GetIndex())
                hash[plot:GetIndex()] = 1
            end
        end
        return plots, hash
    end,

    -- 退出传送模式
    Quit = function(fullQuit)
        if fullQuit then
            UI.SetInterfaceMode(InterfaceModeTypes.SELECTION)
        end
        UILens.ClearLayerHexes(g_HexColoring)
        UILens.ToggleLayerOff(g_HexColoring)
        m_IsActive = false
        Controls.TeleportButton:SetSelected(false)
    end,

    -- 进入/退出传送模式
    SetState = function(self, active, pUnit)
        if active then
            -- 先切换到 SELECTION 再切换到 WB_SELECT_PLOT（防止模式残留）
            UI.SetInterfaceMode(InterfaceModeTypes.SELECTION)
            UI.SetInterfaceMode(InterfaceModeTypes.WB_SELECT_PLOT)

            local plots, hash = self.GetTargetPlots(pUnit)
            m_ValidPlotsHash = hash

            if #plots > 0 then
                UILens.SetLayerHexesArea(g_HexColoring,
                    Game.GetLocalPlayer(), plots)
                UILens.ToggleLayerOn(g_HexColoring)
            end
        else
            self.Quit(true)
        end
        Controls.TeleportButton:SetSelected(active)
    end,

    -- 条件检查
    GetDetail = function(self, pUnit)
        local detail = { Disable = true, Reason = 'NONE' }
        local unitDef = GameInfo.Units[pUnit:GetType()]

        if pUnit:GetMovesRemaining() == 0 then
            detail.Reason = Locale.Lookup('LOC_ACTION_REASON_NO_MOVEMENT')
        elseif unitDef.IgnoreMoves == true then
            detail.Reason = Locale.Lookup('LOC_ACTION_REASON_NO_MOVEMENT')
        else
            local plots = self.GetTargetPlots(pUnit)
            if #plots > 0 then
                detail.Disable = false
            else
                detail.Reason = Locale.Lookup('LOC_ACTION_REASON_NO_TARGET')
            end
        end
        return detail
    end,

    -- 点击回调
    Callback = function(self)
        local pUnit = UI.GetHeadSelectedUnit()
        if pUnit then
            m_IsActive = not m_IsActive
            self:SetState(m_IsActive, pUnit)
        end
    end,
}
```

## 步骤 3：地块选择回调处理

```lua
-- 注册 WB_SELECT_PLOT 事件监听
function OnSelectPlot(plotID, edge, lbutton, rbutton)
    if not m_IsActive then return end

    if rbutton then
        -- 右键 → 退出
        TeleportButton.Quit(true)
    else
        local pUnit = UI.GetHeadSelectedUnit()
        if pUnit and m_ValidPlotsHash[plotID] == 1 then
            -- 目标合法 → 执行传送
            TeleportButton.Quit(true)
            UI.RequestPlayerOperation(Game.GetLocalPlayer(),
                PlayerOperations.EXECUTE_SCRIPT, {
                    OnStart = 'MyTeleportEvent',
                    unitID = pUnit:GetID(),
                    x = Map.GetPlotByIndex(plotID):GetX(),
                    y = Map.GetPlotByIndex(plotID):GetY(),
                }
            )
            UI.PlaySound("Unit_Relocate")
            Network.BroadcastPlayerInfo()
        end
    end
end

LuaEvents.WorldInput_WBSelectPlot.Add(OnSelectPlot)
```

## 步骤 4：模式变化守卫

防止用户通过其他方式（如按 ESC）意外退出 WB_SELECT_PLOT 后仍然处于"激活"状态：

```lua
function OnUIModeChange(intPara, currentInterfaceMode)
    if m_IsActive and currentInterfaceMode ~= InterfaceModeTypes.WB_SELECT_PLOT then
        TeleportButton.Quit(false)  -- 不清除 SELECTION（已被外部修改）
    end
end

Events.InterfaceModeChanged.Add(OnUIModeChange)
```

## 步骤 5：额外安全事件

Hero/Great Person 的传送还需要监听额外事件：

```lua
-- 单位传送后重新计算光环（Majo Witch 模式）
function OnUnitTeleported(playerID, unitID, x, y)
    if playerID == Game.GetLocalPlayer() then
        local pUnit = UI.GetHeadSelectedUnit()
        if pUnit then
            RecalculateAuraLens(pUnit)  -- 重新计算透镜区域
        end
    end
end
Events.UnitTeleported.Add(OnUnitTeleported)

-- 本地玩家变化（热座模式）
function OnLocalPlayerChanged(eLocalPlayer, ePrevLocalPlayer)
    if UILens.IsLayerOn(g_HexColoring) then
        UILens.ClearLayerHexes(g_HexColoring)
        UILens.ToggleLayerOff(g_HexColoring)
    end
    m_IsActive = false
end
Events.LocalPlayerChanged.Add(OnLocalPlayerChanged)
```

## 步骤 6：Aura 透镜模式（非交互式：Majo Witch）

选中特定单位时自动显示光环范围，无需用户点击按钮：

```lua
local m_AuraLens = UILens.CreateLensLayerHash("Hex_Coloring_Great_People")
local m_AuraPromotion = GameInfo.UnitPromotions["PROMOTION_WITCH_2_2"]

function RealizeGreatPersonLens(pUnit)
    if pUnit ~= nil and pUnit == UI.GetHeadSelectedUnit()
        and (not UI.IsGameCoreBusy()) then
        local playerID = pUnit:GetOwner()
        if playerID == Game.GetLocalPlayer() then
            local unitInfo = GameInfo.Units[pUnit:GetType()]
            if unitInfo and unitInfo.PromotionClass == 'PROMOTION_CLASS_WITCH' then

                local res = {}
                if pUnit:GetExperience():HasPromotion(m_AuraPromotion.Index) then
                    pPlots = Map.GetNeighborPlots(pUnit:GetX(), pUnit:GetY(), 2)  -- 2格
                else
                    pPlots = Map.GetNeighborPlots(pUnit:GetX(), pUnit:GetY(), 1)  -- 1格
                end

                for _, pPlot in ipairs(pPlots) do
                    table.insert(res, pPlot:GetIndex())
                end

                if #res > 0 then
                    UILens.SetLayerHexesArea(m_AuraLens, playerID, res)
                    UILens.ToggleLayerOn(m_AuraLens)
                end
            end
        end
    end
end

-- 多个事件触发重新计算
Events.UnitSelectionChanged.Add(OnUnitSelectionChanged)
Events.UnitSimPositionChanged.Add(OnUnitSimPositionChanged)
Events.UnitMovementPointsChanged.Add(OnUnitMovementPointsChanged)
Events.UnitRemovedFromMap.Add(OnUnitRemovedFromMap)
```

## Amphoreus Janus 特有：城市过滤条件

```lua
function GetTeleportTarget(pUnit)
    local result = {}
    local sUnitFormationClass = GameInfo.Units[pUnit:GetType()].FormationClass
    for _, pCity in m_pCurrentPlayer:GetCities():Members() do
        local pPlot = Map.GetPlot(pCity:GetX(), pCity:GetY())
        local flag = false

        -- 海洋单位只能传送到沿海城市
        if GameInfo.Units[pUnit:GetType()].Domain == 'DOMAIN_SEA' then
            flag = true
            for _, neighborPlot in ipairs(Map.GetAdjacentPlots(pCity:GetX(), pCity:GetY())) do
                if neighborPlot:IsWater() then flag = false; break end
            end
        end

        -- 目的地不能有相同 FormationClass 的单位
        for _, pUnitInPlot in ipairs(Units.GetUnitsInPlot(pPlot)) do
            if GameInfo.Units[pUnitInPlot:GetType()].FormationClass == sUnitFormationClass then
                flag = true; break
            end
        end

        if not flag then
            table.insert(result, pPlot:GetIndex())
        end
    end
    return result
end
```

## Eldridge 特有：使用 EagleCore 辅助

```lua
-- 检查地块是否允许特定单位类型
function EagleCore.CanHaveUnit(plot, unitdef)
    -- 实现地块可达性检查
    -- ...
end

-- 在 GetTargetPlots 中调用
if EagleCore.CanHaveUnit(plot, unitdef) then
    if domain == 'DOMAIN_SEA' then
        if plot:IsAdjacentToShallowWater() then
            table.insert(plots, plot:GetIndex())
        end
    else
        table.insert(plots, plot:GetIndex())
    end
end
```

## 初始化事件绑定

```lua
function Initialize()
    -- 按钮挂载
    Events.LoadGameViewStateDone.Add(function()
        local stack = ContextPtr:LookUpControl("/InGame/UnitPanel/StandardActionsStack")
        if stack then
            Controls.TeleportGrid:ChangeParent(stack)
            TeleportButton:Register()
            TeleportButton:Refresh()
        end
    end)

    -- 交互事件
    LuaEvents.WorldInput_WBSelectPlot.Add(OnSelectPlot)
    Events.InterfaceModeChanged.Add(OnUIModeChange)
    Events.UnitTeleported.Add(OnUnitTeleported)
    Events.UnitSelectionChanged.Add(OnUnitSelectChanged)
    Events.UnitMoveComplete.Add(OnUnitMoveComplete)
    Events.LocalPlayerChanged.Add(OnLocalPlayerChanged)
    Events.PhaseBegin.Add(OnPhaseBegin)

    -- 全量刷新事件（参考 unit-panel-injection 的16个事件）
    Events.UnitAddedToMap.Add(Refresh)
    Events.UnitRemovedFromMap.Add(Refresh)
    -- ... 等等
    add_all_remaining_events(Refresh)
end
```

## 状态机总览

```
状态: IDLE (m_IsActive = false)
  ├─ [点击按钮] → 检查条件 → 进入 PLOT_SELECT
  └─ [选中新单位] → Refresh() → 仍在 IDLE

状态: PLOT_SELECT (m_IsActive = true)
  ├─ [左键合法地块] → EXECUTE_SCRIPT → 退出到 IDLE
  ├─ [右键] → Quit(true) → 回到 SELECTION mode → IDLE
  ├─ [ESC/接口模式变化] → Quit(false) → IDLE
  ├─ [取消选中单位] → Quit(true) → IDLE
  └─ [单位移动/删除] → Quit(true) → IDLE
```

## 设计要点

1. **先 SetInterfaceMode(SELECTION) 再 SetInterfaceMode(WB_SELECT_PLOT)** — EagleUnion 的做法，防止残留
2. **同时维护 plots 数组和 hash 表** — 数组给 SetLayerHexesArea，hash 给 O(1) 合法性检查
3. **InterfaceModeChanged 守卫** — 其他面板/ESC 可能改变 UI 模式
4. **右键退出** — 给用户退出机制
5. **IsGameCoreBusy() 检查** — 防止在过场动画/AI 回合时应用透镜
6. **LocalPlayerChanged** — 热座模式切换时必须清除透镜状态
7. **UnitTeleported** — 传送完成后刷新透镜（如传送后光环范围变化）
8. **UILens 不可跨层共享** — 每个能力用独立的 CreateLensLayerHash
9. **Tooltip 在 Refresh 中设，禁用 eMouseEnter** — `SetToolTipString` 在 `Refresh()` 里主动调用，禁用/可用的文本一次设好。不要用 `Mouse.eMouseEnter` 回调去动态设 tooltip，原因：① 和游戏引擎的 tooltip 系统冲突，可能不显示；② 每次鼠标移入都查一遍状态，不必要的开销。除非功能明确要求 hover 动态计算文本，否则一律在 Refresh 中设。
10. **禁用原因的红色文本** — 用 `[COLOR_RED]reason[ENDCOLOR]` 包裹。建议封装为 `Red(str)` 辅助函数（参见 SiqiUI.Red 模式）。

---

## XML 配合

### 用到的 XML 文件

| 来源 Mod | XML 文件路径 | 作用 |
|----------|------------|------|
| EagleUnion Eldridge (3091608915) | `UI/Additions/EldridgeUnitPanel.xml` | 传送按钮 Grid（含 TeleportButton） |
| Amphoreus Janus (3597437530) | `UI/Additions/UnitJanus.xml` | 传送按钮 Grid（单按钮） |
| Majo no Tabitabi (3017462977) | `UI/Additions/WitchUnitPanel.xml` | 无按钮 — 仅透镜光环监听 |

### 控件 ID 对照

| XML 控件 ID | 类型 | Lua 角色 |
|------------|------|---------|
| `TeleportGrid` / `UnitJanusGrid` | `Grid` | 按钮根容器，挂载到 `StandardActionsStack` |
| `TeleportButton` / `UnitJanusButton` | `Button` | 传送按钮，注册 `Mouse.eLClick` 进入/退出选择模式 |
| `TeleportIcon` / `UnitJanusIcon` | `Image` | 按钮图标 |

### Instance 模板

XML 结构与 `lua-workshop-leader-unit-panel-injection.md` 中的单按钮模板完全一致：

```xml
<Context>
    <Grid ID="MyTeleportGrid" Anchor="R,B" Size="auto,41"
          Texture="SelectionPanel_ActionGroupSlot"
          SliceCorner="5,19" SliceSize="1,1" SliceTextureSize="12,41"
          ConsumeMouse="1" Hidden="1">
        <Button ID="MyTeleportButton" Anchor="C,B" Size="44,53"
                Texture="UnitPanel_ActionButton">
            <Image ID="MyTeleportIcon" Anchor="C,C" Offset="0,-2"
                   Size="38,38" Icon="ICON_UNITOPERATION_TELEPORT_TO_CITY"/>
        </Button>
    </Grid>
</Context>
```

### 可复用 XML

- **传送按钮 Grid**：与 unit-panel-injection 单按钮模板共用，不需要额外的 XML 结构
- **XLens 层定义**在 Lua 中通过 `UILens.CreateLensLayerHash()` 完成，无需 XML
- 作为 Context Additions 注册到 modinfo，与其他 UnitPanel 按钮共存在同一批 AddUserInterfaces 中
