# 单位选择自动应用透镜模式（来源：MoreLenses 871712879）

## 做什么
监听单位选择事件，当特定类型的单位被选中时自动激活对应透镜；单位取消选择、移除、被捕获、或耗尽行动力时自动关闭透镜。同时支持通过 `GameConfiguration` 开关控制此行为。

## 涉及文件

| 文件 | 角色 |
|------|------|
| `Lenses/Builder/ModLens_Builder.lua` | Builder 自动透镜（有 GameConfiguration 开关） |
| `Lenses/Scout/ModLens_Scout.lua` | Scout 自动透镜（有 GameConfiguration 开关 + 额外军事单位选项） |
| `Lenses/Archaeologist/ModLens_Archaeologist.lua` | Archaeologist 自动透镜（硬编码关闭的开关） |
| `Lenses/Naturalist/ModLens_Naturalist.lua` | Naturalist 自动透镜（注释掉的实现，作为参考） |
| `Lenses/UnitAction/ModLens_UnitAction.lua` | 早期版本 Scout 透镜（保留文件） |

## 核心事件监听

### 完整事件集

```lua
-- 【核心】单位选中/取消选中
Events.UnitSelectionChanged.Add(OnUnitSelectionChanged)
-- 参数: playerID, unitID, hexI, hexJ, hexK, bSelected, bEditable

-- 【必要】单位从地图移除（阵亡/删除）
Events.UnitRemovedFromMap.Add(OnUnitRemovedFromMap)
-- 参数: playerID, unitID

-- 【可选】单位移动完成（自动探索的 Scout 可能需要刷新）
Events.UnitMoveComplete.Add(OnUnitMoveComplete)
-- 参数: playerID, unitID

-- 【可选】单位被捕获（多人同时回合特需）
Events.UnitCaptured.Add(OnUnitCaptured)
-- 参数: currentUnitOwner, unit, owningPlayer, capturingPlayer

-- 【可选】单位行动力变化（Builder 耗尽次数时自动关闭）
Events.UnitChargesChanged.Add(OnUnitChargesChanged)
-- 参数: playerID, unitID, newCharges, oldCharges

-- 【可选】特定游戏事件（Scout 拾取蘑菇后刷新透镜）
Events.GoodyHutReward.Add(OnGoodyHutReward)
-- 参数: playerID
```

### UnitSelectionChanged — 核心激活/停用

```lua
local function OnUnitSelectionChanged(playerID, unitID, hexI, hexJ, hexK, bSelected, bEditable)
    -- 1. 开关检查
    if not AUTO_APPLY_LENS then return end
    -- 2. 本地玩家检查（不响应其他玩家的选择）
    if playerID ~= Game.GetLocalPlayer() then return end

    -- 3. 获取单位类型
    local unitType = GetUnitTypeFromIDs(playerID, unitID)

    if bSelected then
        -- 选择时激活
        if unitType == "UNIT_BUILDER" then
            ShowMyLens()
        end
    else
        -- 取消选择时停用
        if unitType == "UNIT_BUILDER" then
            ClearMyLens()
        end
    end
end
```

**GetUnitTypeFromIDs 辅助函数：**
```lua
-- 来自 LensSupport.lua
function GetUnitTypeFromIDs(playerID, unitID)
    if playerID == Game.GetLocalPlayer() then
        local pPlayer = Players[playerID]
        local pUnit = pPlayer:GetUnits():FindID(unitID)
        if pUnit ~= nil then
            return GameInfo.Units[pUnit:GetUnitType()].UnitType
        end
    end
    return nil
end
```

### 镜头激活/停用

```lua
local LENS_NAME = "ML_BUILDER"
local ML_LENS_LAYER = UILens.CreateLensLayerHash("Hex_Coloring_Appeal_Level")

local function ShowMyLens()
    LuaEvents.MinimapPanel_SetActiveModLens(LENS_NAME)  -- 通知 minimappanel
    UILens.ToggleLayerOn(ML_LENS_LAYER)                   -- 激活透镜层
end

local function ClearMyLens()
    if UILens.IsLayerOn(ML_LENS_LAYER) then
        UILens.ToggleLayerOff(ML_LENS_LAYER)
    end
    LuaEvents.MinimapPanel_SetActiveModLens("NONE")
end
```

### UnitRemovedFromMap — 防止遗留透镜

当单位阵亡或被删除时，需要关闭透镜：

```lua
local function OnUnitRemovedFromMap(playerID, unitID)
    if playerID ~= Game.GetLocalPlayer() then return end
    -- 检查当前激活的透镜是否为本透镜
    local lens = {}
    LuaEvents.MinimapPanel_GetActiveModLens(lens)
    if lens[1] == LENS_NAME then
        ClearMyLens()
    end
end
```

### UnitMoveComplete — 探索单位移动后刷新

Scout 在自动探索移动完成后需要刷新透镜（FOW 已变化）：

```lua
local function OnUnitMoveComplete(playerID, unitID)
    local pPlayer = Players[playerID]
    if pPlayer == nil then return end
    local pUnit = pPlayer:GetUnits():FindID(unitID)
    if pUnit == nil then return end
    -- 确保单位被选中（自动探索时可能不选中）
    if not UI.IsUnitSelected(pUnit) then return end
    -- 确保类型匹配
    local unitType = getUnitType(pUnit)
    if unitType and promotionClass == "PROMOTION_CLASS_RECON" then
        RefreshMyLens()  -- 先清除再重新激活
    end
end
```

### UnitChargesChanged — Builder 耗尽次数

```lua
local function OnUnitChargesChanged(playerID, unitID, newCharges, oldCharges)
    if not AUTO_APPLY_LENS then return end
    if playerID ~= Game.GetLocalPlayer() then return end
    if GetUnitTypeFromIDs(playerID, unitID) ~= "UNIT_BUILDER" then return end
    if newCharges == 0 then
        ClearMyLens()  -- 次数用完自动关闭
    end
end
```

### UnitCaptured — 多人游戏支持

在同时回合模式中，Builder 可能被敌方捕获：

```lua
local function OnUnitCaptured(currentUnitOwner, unit, owningPlayer, capturingPlayer)
    if owningPlayer ~= Game.GetLocalPlayer() then return end
    local unitType = GetUnitTypeFromIDs(owningPlayer, unitID)
    if unitType == "UNIT_BUILDER" then
        ClearMyLens()
    end
end
```

## 进阶：非单位类型的透镜条件

Scout 透镜支持两种激活模式：
- **侦察单位**：`promotionClass == "PROMOTION_CLASS_RECON"`（Scout, Ranger, Spec Ops 等）
- **所有军事陆地单位**：`militaryUnit and AUTO_APPLY_SCOUT_LENS_EXTRA`

```lua
local function OnUnitSelectionChanged(playerID, unitID, ...)
    -- ...
    local unitType = pUnit:GetUnitType()
    local promotionClass = GameInfo.Units[unitType].PromotionClass
    local unitDomain = GameInfo.Units[unitType].Domain
    local militaryUnit = (pUnit:GetCombat() > 0 or pUnit:GetRangedCombat() > 0)
                         and (unitDomain == "DOMAIN_LAND")

    if bSelected then
        if militaryUnit and AUTO_APPLY_SCOUT_LENS_EXTRA then
            ShowScoutLens()
        elseif promotionClass == "PROMOTION_CLASS_RECON" then
            ShowScoutLens()
        end
    end
end
```

## 用 GameConfiguration 控制自动行为

```lua
-- 读取设置（用 Boolean，因为 GameConfiguration 存储 Boolean 值）
local AUTO_APPLY_LENS = GameConfiguration.GetValue("ML_AutoApplyBuilderLens")

-- 设置面板通过 LuaEvents 通知变更
LuaEvents.ML_SettingsUpdate.Add(OnLensSettingsUpdate)

local function OnLensSettingsUpdate()
    AUTO_APPLY_LENS = GameConfiguration.GetValue("ML_AutoApplyBuilderLens")
end
```

在设置面板中（`ml_settingspanel.lua`）使用 `PopulateCheckBox` 辅助函数绑定：

```lua
PopulateCheckBox(Controls.AutoApplyBuilderLensCheckbox, "ML_AutoApplyBuilderLens")
-- 内部实现：
-- 1. 从 GameConfiguration.GetValue 读取
-- 2. 设置 CheckBox 状态
-- 3. 注册点击回调 → GameConfiguration.SetValue → LuaEvents.ML_SettingsUpdate()
```

## 完整事件生命周期

```
用户选择 Builder:
  Events.UnitSelectionChanged(playerID, unitID, ..., bSelected=true)
    → OnUnitSelectionChanged() → ShowMyLens()
      → LuaEvents.MinimapPanel_SetActiveModLens("ML_BUILDER")
      → UILens.ToggleLayerOn(ML_LENS_LAYER)
        → minimappanel:OnLensLayerOn → SetModLens()
        → 透镜文件:OnLensLayerOn → SetMyHexes()

用户取消选择:
  Events.UnitSelectionChanged(playerID, unitID, ..., bSelected=false)
    → OnUnitSelectionChanged() → ClearMyLens()
      → UILens.ToggleLayerOff(ML_LENS_LAYER)
      → LuaEvents.MinimapPanel_SetActiveModLens("NONE")

Builder 阵亡:
  Events.UnitRemovedFromMap(playerID, unitID)
    → OnUnitRemovedFromMap() → 确认是当前透镜 → ClearMyLens()

Builder 耗尽次数:
  Events.UnitChargesChanged(playerID, unitID, 0, oldCharges)
    → OnUnitChargesChanged() → ClearMyLens()

Builder 被俘:
  Events.UnitCaptured(owner, unit, selfPlayer, enemyPlayer)
    → OnUnitCaptured() → ClearMyLens()
```

## 设计要点

1. **LOCAL_PLAYER 守卫**：所有事件回调先检查 `playerID == Game.GetLocalPlayer()`
2. **可选自动应用**：通过 `GameConfiguration` 和设置面板让用户选择是否自动激活
3. **防止透镜残留**：`UnitRemovedFromMap` 必须检查当前激活透镜是否是自己的
4. **移动后刷新**：`UnitMoveComplete` 对于探索单位很重要（FOW 变化）
5. **多人同时回合**：`UnitCaptured` 处理单位被敌方夺取的情况
6. **行动力耗尽**：`UnitChargesChanged` 处理 Builder 耗尽次数自动关闭
7. **事件注销**：虽然 MoreLenses 未显式注销事件（一次性初始化），但规范的实现应在 Shutdown 中注销
8. **跨单位激活**：通过 `GetActiveModLens` 查询当前透镜，确保多个自动透镜不冲突

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `Settings/ml_settingspanel.xml` | 设置面板 — 提供所有自动应用透镜的开关控件 |
| `Base/Assets/UI/minimappanel.xml` | 透镜面板容器 — 自动激活/停用时操作的透镜层宿主 |

### ml_settingspanel.xml 控件 ID 对照

| XML 控件（ID） | 类型 | GameConfiguration Key | 用途 |
|---------------|------|----------------------|------|
| `SettingsPanel` | Container | — | 设置弹窗根容器（380x512，Anchor="C,C"） |
| `AutoApplyBuilderLensCheckbox` | GridButton (CheckBoxControl) | `ML_AutoApplyBuilderLens` | Builder 选中时自动激活透镜 |
| `BuilderLensDisableNothing` | GridButton (CheckBoxControl) | `ML_BuilderLensDisableNothingHighlight` | 禁用 Builder 透镜"无需操作"高亮 |
| `BuilderLensDisableDangerous` | GridButton (CheckBoxControl) | `ML_BuilderLensDisableDangerousHighlight` | 禁用 Builder 透镜危险地块高亮 |
| `AutoApplyScoutLensCheckbox` | GridButton (CheckBoxControl) | `ML_AutoApplyScoutLens` | 侦察单位选中时自动激活透镜 |
| `AutoApplyScoutLensExtraCheckbox` | GridButton (CheckBoxControl) | `ML_AutoApplyScoutLensExtra` | 扩展至所有军事陆地单位 |
| `ConfirmButton` | GridButton (ButtonConfirm) | — | 确认并关闭设置面板 |

### 设置面板代码绑定模式

```lua
-- 设置面板中
PopulateCheckBox(Controls.AutoApplyBuilderLensCheckbox, "ML_AutoApplyBuilderLens")
-- PopulateCheckBox 内部实现：
--   1. 从 GameConfiguration.GetValue(key) 读取当前值
--   2. 设置 CheckBox 的 IsChecked 状态
--   3. 注册点击回调：点击时 GameConfiguration.SetValue(key, newVal)
--                      → 触发 LuaEvents.ML_SettingsUpdate()
```

### 透镜文件读取配置

```lua
-- 在每个自动透镜的 Lua 文件中
local AUTO_APPLY_LENS = GameConfiguration.GetValue("ML_AutoApplyBuilderLens")
LuaEvents.ML_SettingsUpdate.Add(function()
    AUTO_APPLY_LENS = GameConfiguration.GetValue("ML_AutoApplyBuilderLens")
end)
```

### CheckBoxControl 样式模板

```xml
<GridButton ID="AutoApplyBuilderLensCheckbox" Anchor="L,C" Size="340,24"
            Style="CheckBoxControl"
            String="LOC_HUD_ML_SETTINGS_AUTO_APPLY_BUILDER"
            ToolTip="LOC_TOOLTOP_ML_SETTINGS_AUTO_APPLY_BUILDER"/>
```

此样式封装了 CheckBox + Label 的组合，无需在 XML 中分别定义 CheckBox 和 Label 控件。
