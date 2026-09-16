# UI↔GP 通信模式 (UI-GamePlay Communication Patterns)

> 来源：Resource Introduction (3275724171) + ChaoGong System (3475587881) + Modular Adjacency Bonus (3429735059) + Collectibles Mode (3565119013)
> 跨模组总结的通用通信模式

## 概述

文明6 Mod 中 UI 脚本和 GamePlay 脚本运行在不同的 Lua 环境中，无法直接互相调用。需要通过特定机制进行通信。本文总结四种主流通信模式。

## 核心通信路径

```
UI (UserInterface State)              GP (GamePlay State)
      │                                      │
      ├─ UI.RequestPlayerOperation ─────────>│ EXECUTE_SCRIPT
      │  (带参数的执行请求)                   │ GameEvents 回调
      │                                      │
      ├─ LuaEvents.*.Add ────────────────────│ (仅UI间通信)
      │                                      │
      ├─ ExposedMembers.GameEvents ──────────│ GameEvents 暴露给UI可读
      │  (UI读取GP注册的GameEvents)           │
      │                                      │
GP ──│─ Game.AddWorldViewText ──────────────>│ 显示在地图上
      │                                      │
GP ──│─ GameEvents.*.Call ──────────────────>│ 传递数据(UI作为监听方)
      │                                      │
GP ──│─ ReportingEvents.SendLuaEvent ────────>│ 传递数据到UI
      └──────────────────────────────────────┘
```

## 模式一：UI.RequestPlayerOperation + EXECUTE_SCRIPT

**适用场景**：UI 需要触发 GP 端执行某个操作（如修改地块、设置属性）

**资源引进 Mod 完整示例：**

### UI 端（发送）

```lua
-- ResourceIntroductionUI.lua

-- 发起世界文字显示
function AddWorldViewText(sMsg, iX, iY, iPlayer)
    local tParameters = {}
    tParameters.iX, tParameters.iY = iX, iY
    tParameters.sMsg = sMsg
    tParameters.OnStart = 'RIGP_AddWorldViewText'  -- 对应GP端的 GameEvents 名称
    UI.RequestPlayerOperation(iPlayer, PlayerOperations.EXECUTE_SCRIPT, tParameters)
end

-- 发起设置单位属性
function SetUnitProperty(iPlayer, iUnit, sProperty, value)
    local tParameters = {}
    tParameters.iUnit = iUnit
    tParameters.sProperty = sProperty
    tParameters.value = value
    tParameters.OnStart = 'RIGP_SetUnitProperty'
    UI.RequestPlayerOperation(iPlayer, PlayerOperations.EXECUTE_SCRIPT, tParameters)
end
```

### GP 端（接收）

```lua
-- ResourceIntroductionGP.lua

-- 注册 GameEvents 回调
function RIGP_AddWorldViewText(iPlayer, tParam)
    Game.AddWorldViewText(0, tParam.sMsg, tParam.iX, tParam.iY)
end
GameEvents.RIGP_AddWorldViewText.Add(RIGP_AddWorldViewText)

function RIGP_SetUnitProperty(iPlayer, tParam)
    local pUnit = UnitManager.GetUnit(iPlayer, tParam.iUnit)
    pUnit:SetProperty(tParam.sProperty, tParam.value)
end
GameEvents.RIGP_SetUnitProperty.Add(RIGP_SetUnitProperty)
```

### 关键点

- `tParameters.OnStart` = GP 端注册的 `GameEvents.XXX` 名称
- `tParameters` 中的所有字段会作为第二个参数传给 GP 回调
- 操作仅对 `iPlayer` 生效（因为用了 `UI.RequestPlayerOperation`）
- GP 端回调第一个参数永远是 `playerID`

## 模式二：GameEvents.Call（GP 主动通知 UI）

**适用场景**：GP 端发生事件后通知 UI 更新显示

```lua
-- GP 端
GameEvents.Ophidy_Collectible_Added.Call(iPlayer, iCollectible)
GameEvents.Ophidy_Collectible_Token_Changed.Call(iPlayer, eAmount)

-- UI 端
GameEvents.Ophidy_Collectible_Added.Add(function(iPlayer, iCollectible)
    -- 更新UI显示
end)
```

## 模式三：ReportingEvents.SendLuaEvent（GP 发送结构化数据到 UI）

**适用场景**：需要传递复杂数据结构时使用

```lua
-- GP 端
ReportingEvents.SendLuaEvent('Ophidy_Collectible_Activated', {
    iPlayer = iPlayer,
    iCollectible = iCollectible
})

-- UI 端
-- 在 UI 环境中通过事件系统接收（具体取决于UI框架）
```

## 模式四：自定义 GameEvents 双向桥接

**适用场景**：多文件间解耦通信，特别是弹窗 UI 触发 GP 操作

**朝贡 Mod 使用方式：**

### GP 端注册自定义事件

```lua
-- Chaogong_GP.lua

-- 将 ExposedMembers.GameEvents 暴露给UI
ExposedMembers.GameEvents = GameEvents

-- 注册自定义事件回调
GameEvents.CHAOGONG_FirstButton.Add(function(object_civID, object_Cost)
    -- 处理朝贡逻辑
    localPlayer:GetTreasury():ChangeGoldBalance(-object_Cost)
    localPlayer:GetDiplomacy():SetHasAllied(object_civID, ...)
end)

GameEvents.CHAOGONG_SecondButton.Add(function(object_civID, object_income)
    -- 处理送礼逻辑
end)

GameEvents.CHAOGONG_ThirdButton.Add(function(object_civID, Hiring_Unit)
    -- 处理雇佣逻辑
end)
```

### UI 端触发

```lua
-- CHAOGONG_Popup_Panel.lua

-- 获取 GP 暴露的 GameEvents
GameEvents = ExposedMembers.GameEvents

Controls.FirstButton:RegisterCallback(Mouse.eLClick, function()
    GameEvents.CHAOGONG_FirstButton.Call(object_civID, object_Cost)
    HidePopupPanel()
end)

Controls.SecondButton:RegisterCallback(Mouse.eLClick, function()
    GameEvents.CHAOGONG_SecondButton.Call(object_civID, object_income)
    HidePopupPanel()
end)
```

**注意**：`ExposedMembers.GameEvents = GameEvents` 必须在 GP 脚本中早于 UI 脚本加载之前执行。

## 模式五：Game.AddWorldViewText（GP 在地图上显示文字）

**适用场景**：GP 需要向玩家展示状态信息（进度、结果等）

```lua
-- 显示工作进度
Game.AddWorldViewText(
    0,  -- 0 = 所有玩家可见
    Locale.Lookup('LOC_MOD_RI_BUTTONC_ING') .. ':' .. resourceName .. ' (' .. n .. '/' .. N .. ')',
    iX, iY
)

-- 显示成功信息
Game.AddWorldViewText(0, Locale.Lookup("LOC_RI_WORK_SUCCESS"), iX, iY)
```

## 通用注册模式

### GP 端事件注册模板

```lua
-- 1. 通过 UI.RequestPlayerOperation 接收
function GP_Handler(iPlayer, tParam)
    -- 处理逻辑
end
GameEvents.GP_Handler.Add(GP_Handler)

-- 2. 通过自定义 GameEvents 接收
GameEvents.CustomEvent.Add(function(...)
    -- 处理逻辑
end)

-- 3. 系统事件监听
Events.UnitKilledInCombat.Add(handler)
Events.PlayerTurnStarted.Add(handler)
Events.UnitMoveComplete.Add(handler)
Events.DistrictBuildProgressChanged.Add(handler)
Events.CapitalCityChanged.Add(handler)
Events.AllianceEnded.Add(handler)
Events.GameEraChanged.Add(handler)
Events.LoadGameViewStateDone.Add(Initialize)
```

### UI 端事件注册模板

```lua
function Initialize()
    -- 系统事件
    Events.UnitSelectionChanged.Add(OnUnitSelectionChanged)
    Events.UnitMoveComplete.Add(OnUnitMoveComplete)
    Events.LoadGameViewStateDone.Add(Initialize)

    -- GP → UI 事件
    GameEvents.Ophidy_Collectible_Added.Add(OnCollectibleAdded)

    -- UI 间事件
    LuaEvents.CHAOGONG_Popup_ShowScreen.Add(ON_CHAOGONG_Popup_ShowScreen)
end
```

## 参数传递注意事项

1. **table 类型**：`tParameters` 中的值必须是基本类型（number, string, boolean），复杂 table 可能无法正确序列化
2. **nil 值**：table 中的 nil 值会被序列化过程忽略
3. **大数据**：避免在参数中传递大量数据，应考虑用 Property 中转
4. **Property 中转**：大量或复杂数据通过 Player/Plot/City/Game 的 Property 存储，两端读取同一 Property
5. **事件时序**：GP 脚本和 UI 脚本加载顺序不定，`GameEvents.*.Add` 必须在对应 `GameEvents.*.Call` 之前执行

## 典型完整流程示例

### 资源引进流程

```
1. UI: 玩家选中"实业家"单位
       ↓ Events.UnitSelectionChanged
2. UI: 显示操作按钮 (K消除/I导入/C种植)
       ↓ 玩家点击C
3. UI: 扫描周围6格资源 → 弹出资源选择网格
       ↓ 玩家选择资源
4. UI: SetUnitProperty(iPlayer, iUnit, 'PORPERTY_RI_I_WORK', {iOperation=1, ...})
       ↓ UI.RequestPlayerOperation → GameEvents.RIGP_SetUnitProperty
5. GP: pUnit:SetProperty('PORPERTY_RI_I_WORK', tWorkStatus)
       ↓
6. GP: 每回合 OnPlayerTurnStarted → 检查工作进度
       ↓ Game.AddWorldViewText 显示进度
7. GP: 达到目标回合 → RIGP_AddResourceInPlot
       ↓ ResourceBuilder.SetResourceType + ImprovementBuilder.SetImprovementType
8. GP: Game.AddWorldViewText(0, "成功", iX, iY)
```

## 注册顺序依赖

在 `.modinfo` 文件中控制加载顺序：

```xml
<InGameActions>
    <!-- GP 脚本先加载（注册 GameEvents 回调） -->
    <UpdateDatabase id="GP_DB">
        <File>GP_Script.lua</File>
    </UpdateDatabase>
    <UpdateDatabase id="UI_DB">
        <File>UI_Script.lua</File>
    </UpdateDatabase>
</InGameActions>
```

或将 Lua 文件放在不同 Action 组中确保加载顺序。
