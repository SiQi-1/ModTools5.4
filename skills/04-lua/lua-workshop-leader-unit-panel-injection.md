# 单位面板按钮注入模式（来源：EagleUnion、Amphoreus、GUMOON、Iberia）

## 做什么
在文明 6 原生单位面板（选中单位时左下角的操作栏）的 `StandardActionsStack` 中注入自定义操作按钮，实现领袖专属单位能力（如：创建资源、传送、范围净化、回血等）。

## 涉及 Mod

| Mod ID | 名称 | 注入按钮 |
|--------|------|----------|
| 3091608915 | EagleUnion | StLouis(3按钮)、Eldridge(2按钮)、Enterprise(1按钮)、Flasher(顶部面板) |
| 3597437530 | Amphoreus 翁法罗斯 | Janus传送按钮、死亡之龙行动按钮 |
| 3574534861 | GUMOON | EarthEngineer资源创建按钮 |
| 3391173367 | Iberia XP | PenalBattalion净化按钮 |
| 3451186356 | Amphoreus 崩铁 | DeathDragon行动按钮 |
| 3017462977 | Majo no Tabitabi | 自定义单位面板事件监听（SelectedUnit） |

## 核心架构：三层分离

```
[UI Lua] -- 按钮显示/隐藏、条件检查、tooltip生成
   ↓ PlayerOperations.EXECUTE_SCRIPT
[GameEvents] -- Gameplay Script Lua 接收执行请求
   ↓ UnitManager.ReportActivation
[UnitActivate 事件] -- UI Lua 响应动画/特效
```

**关键文件分三类：**
- `UI/Additions/XxxUnitPanel.lua` + `.xml` — UI 端按钮逻辑（AddUserInterfaces）
- `Scripts/XxxScript.lua` — Gameplay 端执行逻辑（AddGameplayScripts）
- 可选 `ModSupport/` — 第三方 Mod 扩展适配

## 步骤 1：XML 按钮 Grid 模板

需要在自定义按钮的 Context 中创建一个 Grid 容器，内含 Stack 存放按钮。

### 单按钮模板（Amphoreus 传送 / GUMOON EarthEngineer）

```xml
<Context>
    <Grid ID="UnitJanusGrid" Anchor="R,B" Size="auto,41"
          AutoSizePadding="6,0"
          Texture="SelectionPanel_ActionGroupSlot"
          SliceCorner="5,19" SliceSize="1,1" SliceTextureSize="12,41"
          ConsumeMouse="1" Hidden="1">
        <Button ID="UnitJanusButton" Anchor="C,B" Size="44,53"
                Texture="UnitPanel_ActionButton">
            <Image ID="UnitJanusIcon" Anchor="C,C" Offset="0,-2"
                   Size="38,38" Icon="ICON_UNITOPERATION_TELEPORT_TO_CITY"/>
        </Button>
    </Grid>
</Context>
```

关键属性：
- `Texture="SelectionPanel_ActionGroupSlot"` — 使用原生按钮组背景
- `Texture="UnitPanel_ActionButton"` — 使用原生按钮背景
- `Hidden="1"` — 默认隐藏，由 Lua 逻辑决定显示
- `AutoSizePadding="6,0"` — 自动边距

### 多按钮模板（EagleUnion StLouis 3按钮）

```xml
<Context>
    <Grid ID="StLouisGrid" Anchor="R,B" Size="Auto,41"
          AutoSizePadding="2,0"
          Texture="SelectionPanel_ActionGroupSlot"
          SliceCorner="5,19" SliceSize="1,1" SliceTextureSize="12,41"
          ConsumeMouse="1" Hidden="1">
        <Stack ID="StLouisActionStack" Anchor="C,B"
               StackGrowth="Right" StackPadding="2">
            <Button ID="Remove" Anchor="C,B" Size="44,53"
                    Texture="UnitPanel_ActionButton">
                <Image ID="RemoveIcon" Anchor="C,C" Offset="0,-2"
                       Size="38,38" Icon="ICON_STLOUIS_REMOVE"/>
            </Button>
            <Button ID="Improv" Anchor="C,B" Size="44,53"
                    Texture="UnitPanel_ActionButton">
                <Image ID="ImprovIcon" Anchor="C,C" Offset="0,-2"
                       Size="38,38" Icon="ICON_STLOUIS_IMPROV"/>
            </Button>
        </Stack>
    </Grid>
</Context>
```

## 步骤 2：Lua — Init 阶段注入按钮

所有按钮注入遵循同一模式：在 `LoadGameViewStateDone` 时通过 `LookUpControl` + `ChangeParent` 挂载到原生面板。

### 标准 Init 函数

```lua
-- 在 LoadGameViewStateDone 时调用
function OnLoadGameViewStateDone()
    -- 1. 获取原生 StandardActionsStack 容器
    local context = ContextPtr:LookUpControl("/InGame/UnitPanel/StandardActionsStack")
    if context then
        -- 2. 将自己 Context 的按钮Grid挂载过去
        Controls.MyActionGrid:ChangeParent(context)

        -- 3. 注册按钮回调
        Controls.MyButton:RegisterCallback(Mouse.eLClick, OnMyButtonClicked)
        Controls.MyButton:RegisterCallback(Mouse.eMouseEnter, OnMouseEnter) -- 可选

        -- 4. 初始刷新状态
        Refresh()
    end
end

Events.LoadGameViewStateDone.Add(OnLoadGameViewStateDone)
```

### 多按钮版本（带 Detail/Refresh 子对象结构）

```lua
MyUnitPanel = {
    Refresh = function(self)
        local pUnit = UI.GetHeadSelectedUnit()
        if pUnit and IsMyUnit(pUnit) then
            Controls.MyGrid:SetHide(false)
            self.ButtonA:Refresh(pUnit)
            self.ButtonB:Refresh(pUnit)
        else
            Controls.MyGrid:SetHide(true)
        end
        -- 强制刷新原生UnitPanel
        ContextPtr:LookUpControl("/InGame/UnitPanel"):RequestRefresh()
    end,
    Init = function(self)
        local stack = ContextPtr:LookUpControl("/InGame/UnitPanel/StandardActionsStack")
        if stack then
            Controls.MyGrid:ChangeParent(stack)
            self.ButtonA:Register()
            self.ButtonB:Register()
            self:Refresh()
        end
    end,
    ButtonA = {
        GetDetail = function(pUnit)
            local detail = { Disable = true, Reason = '' }
            if pUnit:GetMovesRemaining() == 0 then
                detail.Reason = Locale.Lookup('LOC_ACTION_REASON_NO_MOVEMENT')
                return detail
            end
            -- ... 更多条件检查
            detail.Disable = false
            return detail
        end,
        Refresh = function(self, pUnit)
            local detail = self.GetDetail(pUnit)
            local disable = detail.Disable
            Controls.ButtonA:SetDisabled(disable)
            Controls.ButtonA:SetAlpha((disable and 0.7) or 1)

            local tooltip = Locale.Lookup('LOC_BUTTON_TITLE')
                .. '[NEWLINE][NEWLINE]' .. Locale.Lookup('LOC_BUTTON_DESC')
            if disable then
                tooltip = tooltip .. '[NEWLINE][NEWLINE]' .. detail.Reason
            end
            Controls.ButtonA:SetToolTipString(tooltip)
        end,
        Callback = function(self)
            local pUnit = UI.GetHeadSelectedUnit()
            if not pUnit then return end
            local detail = self.GetDetail(pUnit)
            if detail.Disable then return end

            UI.RequestPlayerOperation(Game.GetLocalPlayer(),
                PlayerOperations.EXECUTE_SCRIPT, {
                    UnitID = pUnit:GetID(),
                    X = pUnit:GetX(),
                    Y = pUnit:GetY(),
                    OnStart = 'MyGameEventName',
                }
            )
            Network.BroadcastPlayerInfo()  -- 多人同步
        end,
        Register = function(self)
            Controls.ButtonA:RegisterCallback(Mouse.eLClick, function() self:Callback() end)
            Controls.ButtonA:RegisterCallback(Mouse.eMouseEnter, MyMouseEnterFunc)
        end
    }
}
```

## 步骤 3：事件绑定 — 全面刷新

刷新时机覆盖所有单位状态变化事件：

```lua
function Initialize()
    Events.LoadGameViewStateDone.Add(OnLoadGameViewStateDone)
    Events.UnitSelectionChanged.Add(OnUnitSelectChanged)

    -- 全面刷新事件列表（16个事件）
    Events.UnitAddedToMap.Add(Refresh)
    Events.UnitOperationSegmentComplete.Add(Refresh)
    Events.UnitCommandStarted.Add(Refresh)
    Events.UnitDamageChanged.Add(Refresh)
    Events.UnitMoveComplete.Add(Refresh)
    Events.UnitChargesChanged.Add(Refresh)
    Events.UnitPromoted.Add(Refresh)
    Events.UnitOperationsCleared.Add(Refresh)
    Events.UnitOperationAdded.Add(Refresh)
    Events.UnitOperationDeactivated.Add(Refresh)
    Events.UnitMovementPointsChanged.Add(Refresh)
    Events.UnitMovementPointsCleared.Add(Refresh)
    Events.UnitMovementPointsRestored.Add(Refresh)
    Events.UnitAbilityLost.Add(Refresh)
    Events.UnitRemovedFromMap.Add(Refresh)

    -- 回合切换（PhaseBegin）
    Events.PhaseBegin.Add(Refresh)

    -- 按钮如果需要响应城市变化
    Events.CityAddedToMap.Add(Refresh)   -- Eldridge 传送目标需要
    Events.CityRemovedFromMap.Add(Refresh)
end
```

## 步骤 4：Gameplay 脚本 — 执行与反馈

Gameplay 脚本通过 GameEvents 接收 UI 请求，执行实际效果后触发 UnitActivate 通知 UI 播放动画。

```lua
-- Scripts/MyLeaderScript.lua（AddGameplayScripts）
include('EagleCore')  -- 通用辅助库

-- 自定义行为原因常量
local Reason_1 = DB.MakeHash("MY_ACTION_REASON")

function MyGameEventHandler(playerID, param)
    local pUnit = UnitManager.GetUnit(playerID, param.UnitID)
    if not pUnit then return end

    -- 执行实际效果
    -- ... 改变游戏状态 ...

    -- 1. 结束单位回合
    local curMoves = pUnit:GetMovesRemaining()
    UnitManager.ChangeMovesRemaining(pUnit, -curMoves)

    -- 2. 报告单位激活（触发 UnitActivate 事件，通知 UI 播放动画）
    UnitManager.ReportActivation(pUnit, "MY_ACTION_REASON")
end

function Initialize()
    -- 注册 GameEvent 处理器
    GameEvents.MyGameEventName.Add(MyGameEventHandler)
end
Initialize()
```

### UI 端响应 UnitActivate 播放动画

```lua
-- UI 文件中
local Reason_1 = DB.MakeHash("MY_ACTION_REASON")

function OnUnitActive(owner, unitID, x, y, eReason)
    local pUnit = UnitManager.GetUnit(owner, unitID)
    if eReason == Reason_1 then
        -- 播放单位动画
        SimUnitSystem.SetAnimationState(pUnit, "ACTION_1", "IDLE")
        -- 播放世界空间特效
        WorldView.PlayEffectAtXY("MY_EFFECT_NAME", x, y)
    end
    Refresh()  -- 刷新按钮状态
end

Events.UnitActivate.Add(OnUnitActive)
```

## 步骤 5：CheckLeaderMatched 条件门控

大多数工坊 Mod 使用 CheckLeaderMatched 来确保按钮只对特定领袖生效：

```lua
-- EagleCore 中的通用辅助
function EagleCore.CheckLeaderMatched(playerID, leaderType)
    local leader = PlayerConfigurations[playerID]:GetLeaderTypeName()
    return leader == leaderType
end

-- 或基于 Property 的检测
function HasTrait_Property(sTrait, iPlayer)
    local pPlayer = Players[iPlayer]
    local ePro = pPlayer:GetProperty('PROPERTY_' .. sTrait) or 0
    return ePro > 0
end

-- 在 Refresh 中使用
function Refresh()
    local pUnit = UI.GetHeadSelectedUnit()
    if pUnit and HasTrait_Property('TRAIT_LEADER_NW_TRIBIOS_JANUS', Game.GetLocalPlayer()) then
        Controls.MyGrid:SetHide(false)
    else
        Controls.MyGrid:SetHide(true)
    end
end
```

## 步骤 6：按钮条件检查模式（GetDetail）

每个按钮的 GetDetail 函数返回统一格式：

```lua
GetDetail = function(pUnit)
    local detail = { Disable = true, Reason = '' }

    -- 检查1：单位有剩余移动力
    if pUnit:GetMovesRemaining() == 0 then
        detail.Reason = Locale.Lookup('LOC_ACTION_REASON_NO_MOVEMENT')
        return detail
    end

    -- 检查2：冷却时间（通过 Unit Property 实现）
    local turns = pUnit:GetProperty('MyCooldownKey') or 0
    if turns >= Game.GetCurrentGameTurn() then
        detail.Reason = Locale.Lookup('LOC_ACTION_REASON_HAS_USED')
        return detail
    end

    -- 检查3：特定条件（如血量、地块等）
    if not CheckSpecificCondition(pUnit) then
        detail.Reason = Locale.Lookup('LOC_ACTION_REASON_SPECIFIC')
        return detail
    end

    detail.Disable = false
    return detail
end
```

## 步骤 7：通知面板注入（Flasher 模式）

除了 `StandardActionsStack`，还可注入到世界追踪面板顶部：

```lua
function FlasherAttachPanel()
    local parent = ContextPtr:LookUpControl("/InGame/WorldTracker/PanelStack")
    if parent ~= nil then
        Controls.FlasherPanelGrid:ChangeParent(parent)
        parent:AddChildAtIndex(Controls.FlasherPanelGrid, 1)

        Controls.FlasherGainButton:RegisterCallback(Mouse.eLClick,
            function()
                RefreshPanel()
                UI.PlaySound('UI_Screen_Open')
            end
        )

        parent:CalculateSize()
        parent:ReprocessAnchoring()
        RefreshPanel()
    end
end
Events.LoadGameViewStateDone.Add(FlasherAttachPanel)
```

## 步骤 8：模块化扩展（ModSupport / Carlotta 模式）

当其他 Mod 需要扩展你 Mod 的 UnitPanel 时，通过保存原函数引用 + 覆盖实现：

```lua
-- ModSupport/Carlotta/UI/Replace/StLouisUnitPanel_Carlotta.lua
-- 保存原始函数
local StLouisCarlottaReinit = StLouisReinit

-- 覆盖为新函数
function StLouisReinit()
    StLouisCarlottaReinit()  -- 调用原始逻辑
    -- 添加新逻辑
    local emerald = EagleResource:new('RESOURCE_EMERALD_BU')
    Luxuries.Resources['RESOURCE_EMERALD_BU'] = emerald
end

-- 兜底 hot-reload 兼容
include('StLouisUnitPanel_Carlotta_', true)
```

## 完整事件流总结

```
用户选中单位
  → UnitSelectionChanged
    → Refresh() → 检查领袖+单位类型 → SetHide(false/true)
    → 各按钮 GetDetail() → Refresh() → SetDisabled/SetAlpha/SetToolTipString

用户点击按钮
  → Callback()
    → UI.RequestPlayerOperation(playerID, PlayerOperations.EXECUTE_SCRIPT, {
        UnitID, X, Y, OnStart = 'GameEventName', ...额外参数
      })
    → Network.BroadcastPlayerInfo()

Gameplay 脚本接收
  → GameEvents.GameEventName(playerID, params)
    → 执行游戏逻辑
    → UnitManager.ChangeMovesRemaining(unit, -curMoves)  -- 结束回合
    → UnitManager.ReportActivation(unit, "REASON_HASH")  -- 触发动画

UI 响应动画
  → Events.UnitActivate(owner, unitID, x, y, eReason)
    → SimUnitSystem.SetAnimationState(unit, "SPAWN", "IDLE")
    → WorldView.PlayEffectAtXY("EFFECT_NAME", x, y)
    → Refresh()  -- 再次刷新按钮状态
```

## 设计要点

1. **GetDetail → Refresh → Callback → Register** 四件套是每个按钮的标准结构
2. **始终通过 `UI.RequestPlayerOperation(...EXECUTE_SCRIPT...)` 通信**，不要让 UI Lua 直接修改游戏状态（防止多人不同步）
3. **OnStart 字符串必须与 GameEvents 注册名称一致**
4. **全面事件监听**：至少绑定 UnitSelectionChanged + UnitMoveComplete；完整版绑定全部 16+ 事件
5. **Network.BroadcastPlayerInfo()** — 多人游戏中同步 UI 状态
6. **CheckLeaderMatched / HasTrait_Property** — 确保按钮只在正确的领袖/文明下显示
7. **ContextPtr:LookUpControl("/InGame/UnitPanel"):RequestRefresh()** — 每次更新后刷新原生面板
8. **include('FileName_', true)** — 兼容 hot-reload（Reload 时跳过重复加载）
9. **Tooltip 禁在 eMouseEnter 中设** — `SetToolTipString` 必须在 `GetDetail/Refresh` 流程中主动设好，不要用 `Mouse.eMouseEnter` 回调动态改 Tooltip。`eMouseEnter` 仅限 `UI.PlaySound("Main_Menu_Mouse_Over")` 等副作用。原因：游戏引擎 Tooltip 系统在 hover 时读取按钮上已有的 tooltip 值，动态修改会导致冲突而不显示。
10. **禁用原因红色文本** — `[COLOR_RED]reason[ENDCOLOR]`，封装为 `Red(str)` 辅助函数。参见 `SiqiUI.Red` 模式。

---

## XML 配合

### 用到的 XML 文件

| 来源 Mod | XML 文件路径 | 按钮数 |
|----------|------------|--------|
| EagleUnion (3091608915) | `UI/Additions/StLouisUnitPanel.xml` | 3按钮 (Remove/Improv/Create) |
| EagleUnion (3091608915) | `UI/Additions/EldridgeUnitPanel.xml` | 2按钮 (Teleport/...) |
| Amphoreus (3597437530) | `UI/Additions/UnitJanus.xml` | 1按钮 (传送) |
| GUMOON (3574534861) | `UI/Additions/EarthEngineerUnitPanel.xml` | 1按钮 (资源创建) |
| Iberia XP (3391173367) | `Event_ProfoundSilence/UI/Additions/PenalBattalion/PenalBattalionCleansing.xml` | 1按钮 (净化) |
| Majo no Tabitabi (3017462977) | `UI/Additions/WitchUnitPanel.xml` | Aura 透镜监听（无按钮） |

### 控件 ID 对照（以 StLouis 双按钮为例）

| XML 控件 ID | 类型 | Lua 角色 |
|------------|------|---------|
| `StLouisGrid` | `Grid` | 按钮根容器，`ChangeParent` 挂载到 `StandardActionsStack` |
| `StLouisActionStack` | `Stack` | 按钮水平排列容器，`StackGrowth="Right"` |
| `Remove` | `Button` | 移除资源按钮 |
| `RemoveIcon` | `Image` | 移除按钮图标 |
| `Improv` | `Button` | 改良资源按钮 |
| `ImprovIcon` | `Image` | 改良按钮图标 |

### Instance 模板

本模式在同一个 Context 中完整定义所有按钮（非 InstanceManager），按需使用嵌套 InstanceManager 做资源/选项网格：

```xml
<Context>
    <Grid ID="MyActionGrid" Anchor="R,B" Size="auto,41"
          Texture="SelectionPanel_ActionGroupSlot"
          SliceCorner="5,19" SliceSize="1,1" SliceTextureSize="12,41"
          ConsumeMouse="1" Hidden="1">
        <Stack ID="MyActionStack" Anchor="C,B"
               StackGrowth="Right" StackPadding="2">
            <Button ID="MyButtonA" Anchor="C,B" Size="44,53"
                    Texture="UnitPanel_ActionButton">
                <Image ID="MyIconA" Anchor="C,C" Offset="0,-2"
                       Size="38,38" Icon="ICON_XXX"/>
            </Button>
        </Stack>
    </Grid>
</Context>
```

### 可复用 XML

- **单按钮模板**：最小配置 — 一个 Grid + 一个 Button + 一个 Image，适合注入单个操作
- **多按钮模板**：Grid + Stack(StackGrowth="Right") + N×Button，通过 `StackPadding` 控制间距
- 所有 UnitPanel 按钮都使用 `Texture="SelectionPanel_ActionGroupSlot"`（容器） + `Texture="UnitPanel_ActionButton"`（按钮）以匹配原生样式
- 作为 Context Additions 注册到 modinfo，`LoadGameViewStateDone` 时动态挂载
