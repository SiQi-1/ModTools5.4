# 自定义事件/选择框架（来源：Iberia XP ProfoundSilence）

## 做什么
实现一个可复用的自定义事件系统：在回合开始/特定时机触发事件弹窗，玩家做出选择后执行不同效果，支持多阶段事件链（事件1 → 选择A → 子事件1A）。

## 涉及 Mod

| Mod | 系统 | 功能 |
|-----|------|------|
| Iberia XP | Oph_Events / Oph_EventChoices | ProfoundSilence 事件及两个选择分支 |
| Iberia XP | ProfoundSilence EventHandler | 条件触发 + 执行效果 + 场景特效恢复 |
| Iberia XP | OphEventChoice_Iberia | 选择项的动态 tooltip 生成 |

## 架构

```
[条件检查] → [触发事件]
  LuaEvents.Oph_EventPopup(EventType)
    ↓
[事件弹窗 UI] (CreateEventMethod[EventType])
  → 读取 GameInfo.Oph_Events[EventType] → 渲染标题/描述/选择项
  → 选择项动态构建 (CreateChoiceMethod[ChoiceType])
    ↓
[玩家选择] → LuaEvents.Iberia_Event_ProfoundSilence_Positive()
  → UI.RequestPlayerOperation(EXECUTE_SCRIPT, { OnStart = "GameplayHandler" })
  → LuaEvents.Oph_EventPopup(SubEventType, subIndex) -- 可选子事件
  → LuaEvents.Oph_Event_Finished() -- 关闭弹窗
```

## 步骤 1：数据库表定义 (SQL)

```sql
-- 事件定义表
CREATE TABLE Oph_Events (
    EventType TEXT,
    Title TEXT,
    Desc TEXT,
    EventImage TEXT
);

-- 选择项定义表
CREATE TABLE Oph_EventChoices (
    ChoiceType TEXT,
    EventType TEXT,
    Title TEXT,
    Desc TEXT,
    Tooltip TEXT  -- 动态填充的占位
);

-- 示例数据
INSERT INTO Oph_Events (EventType, Title, Desc)
VALUES ('EVENT_OPH_IBERIA_PROFOUND_SILENCE',
    'LOC_EVENT_PROFOUND_SILENCE_TITLE',
    'LOC_EVENT_PROFOUND_SILENCE_DESC');

INSERT INTO Oph_EventChoices (ChoiceType, EventType, Title, Desc)
VALUES ('CHOICE_IBERIA_PROFOUND_POSITIVE',
    'EVENT_OPH_IBERIA_PROFOUND_SILENCE',
    'LOC_CHOICE_PROFOUND_POSITIVE_TITLE',
    'LOC_CHOICE_PROFOUND_POSITIVE_DESC');

INSERT INTO Oph_EventChoices (ChoiceType, EventType, Title, Desc)
VALUES ('CHOICE_IBERIA_PROFOUND_NEGATIVE',
    'EVENT_OPH_IBERIA_PROFOUND_SILENCE',
    'LOC_CHOICE_PROFOUND_NEGATIVE_TITLE',
    'LOC_CHOICE_PROFOUND_NEGATIVE_DESC');
```

## 步骤 2：事件创建函数注册（CreateEventMethod 表）

在事件选择 UI 文件中注册事件工厂函数：

```lua
-- OphEventChoice_Iberia.lua（UI Additions）

-- 注册事件创建方法：返回 {Title, Desc, Image} 等
CreateEventMethod['EVENT_OPH_IBERIA_PROFOUND_SILENCE'] = function(EventType)
    local EventInfo = GameInfo.Oph_Events[EventType]
    EventInfo.Title = Locale.Lookup(EventInfo.Title)
    EventInfo.Desc = Locale.Lookup(EventInfo.Desc)
    return EventInfo
end

-- 注册选择项创建方法：返回动态填充后的 {Title, Desc, Tooltip}
CreateChoiceMethod['CHOICE_IBERIA_PROFOUND_POSITIVE'] = function(EventType)
    local ChoiceInfo = GameInfo.Oph_EventChoices['CHOICE_IBERIA_PROFOUND_POSITIVE']
    if EventType == ChoiceInfo.EventType then
        -- 动态生成受影响城市的列表
        local citiesInfo = ""
        local pPlayer = Players[Game.GetLocalPlayer()]
        for _, pCity in pPlayer:GetCities():Members() do
            if pCity and not pCity:IsCapital() then
                local pHarbor = pCity:GetDistricts():GetDistrict(
                    GameInfo.Districts['DISTRICT_HARBOR'].Index)
                if pHarbor then
                    citiesInfo = citiesInfo .. " " .. Locale.Lookup(pCity:GetName())
                end
            end
        end

        ChoiceInfo.Desc = Locale.Lookup(ChoiceInfo.Desc)
        ChoiceInfo.Tooltip = Locale.Lookup('LOC_CHOICE_DETAIL')
        if citiesInfo ~= "" then
            ChoiceInfo.Tooltip = ChoiceInfo.Tooltip
                .. '[NEWLINE][NEWLINE][ICON_BULLET]'
                .. Locale.Lookup('LOC_CHOICE_AFFECTED_CITIES', citiesInfo)
        end
    end
    return ChoiceInfo
end

CreateChoiceMethod['CHOICE_IBERIA_PROFOUND_NEGATIVE'] = function(EventType)
    -- 类似：列出缺少港口或伊比利亚教堂的城市
    local citiesInfo = ""
    for _, pCity in pPlayer:GetCities():Members() do
        if (not pCity:GetDistricts():HasDistrict(harborIndex, true)
            or not pCity:GetDistricts():HasDistrict(churchIndex, true))
            and not pCity:IsCapital() then
            citiesInfo = citiesInfo .. " " .. Locale.Lookup(pCity:GetName())
        end
    end
    ChoiceInfo.Tooltip = Locale.Lookup('LOC_CHOICE_DETAIL', citiesInfo)
    return ChoiceInfo
end

-- 注册子事件（事件选择后的确认弹窗）
CreateCustomChoice['EVENT_OPH_IBERIA_PROFOUND_SILENCE_1'] = function(index)
    local ChoiceInfo = {}
    if index == 1 then
        ChoiceInfo = {
            Desc = Locale.Lookup('LOC_OK_BUTTON'),
            Tooltip = "",
            Index = -1
        }
    end
    return ChoiceInfo
end
```

## 步骤 3：事件触发 — EventHandler

### 多条件链式检查

```lua
-- EventHandler_Iberia.lua（UI Additions）

local TriggerRequirements = {
    -- 条件1：拥有7+港口城市
    function(iPlayer)
        local pPlayer = Players[iPlayer]
        local NumHarborCity = 0
        for _, pCity in pPlayer:GetCities():Members() do
            if pCity:GetDistricts():HasDistrict(harborIndex, true) then
                NumHarborCity = NumHarborCity + 1
                if NumHarborCity >= 7 then return true end
            end
        end
        return false
    end,
    -- 条件2：文艺复兴时代或之后
    function(iPlayer)
        return Players[iPlayer]:GetEra() >= GameInfo.Eras['ERA_RENAISSANCE'].Index
    end,
    -- 条件3：概率触发（带递增概率保底）
    function(iPlayer)
        local pPlayer = Players[iPlayer]
        local Trigger = math.max(5,
            pPlayer:GetProperty('IberiaProfoundSilenceTrigger') or 5)
        local RandNum = math.random() * 100
        if RandNum < Trigger then
            return true
        else
            -- 失败时增加下次概率
            if pPlayer:IsTurnActive() then
                UI.RequestPlayerOperation(iPlayer,
                    PlayerOperations.EXECUTE_SCRIPT, {
                        Key = 'IberiaProfoundSilenceTrigger',
                        Value = Trigger + 1,
                        OnStart = "Iberia_SetProperty",
                    }
                )
            end
            return false
        end
    end
}

function OnLocalPlayerTurnBegin()
    local iPlayer = Game.GetLocalPlayer()
    local pPlayer = Players[iPlayer]

    -- 门控检查
    if not HasTrait_Property(TRAIT_IBERIA, iPlayer) then return end
    if not pPlayer:IsTurnActive() then return end
    if not pPlayer:IsHuman() then return end
    if GameConfiguration.IsAnyMultiplayer() then return end
    if pPlayer:GetProperty('IberiaProfoundSilenceIsTriggered') then return end

    -- 链式检查：任一条件失败则终止
    for _, func in ipairs(TriggerRequirements) do
        if not func(iPlayer) then return end
    end

    -- 所有条件满足 → 触发事件
    LuaEvents.Oph_EventPopup('EVENT_OPH_IBERIA_PROFOUND_SILENCE')
end

Events.LocalPlayerTurnBegin.Add(OnLocalPlayerTurnBegin)
```

## 步骤 4：选择回调 — 执行效果

```lua
-- 正面选择：对所有非首都港口城市施加效果
function Iberia_Event_ProfoundSilence_Positive()
    local LocalPlayer = Game.GetLocalPlayer()
    local pLocalPlayer = Players[LocalPlayer]
    if not pLocalPlayer:IsTurnActive() then return end

    local AffectedPlots = {}
    for _, pCity in pLocalPlayer:GetCities():Members() do
        if pCity and not pCity:IsCapital() then
            local pHarbor = pCity:GetDistricts():GetDistrict(harborIndex)
            if pHarbor then
                -- UI 端特效：辐射效果预览
                local worldX, worldY, worldZ = UI.GridToWorld(
                    pCityCenter:GetX(), pCityCenter:GetY())
                local id = AssetPreview.Create("FXm_Radiation", worldX, worldY)
                if id >= 0 then
                    AssetPreview.SetInstanceScale(id, 2)
                end
                AffectedPlots[pPlot:GetIndex()] = true
            end
        end
    end

    -- 发送 Gameplay 执行请求
    UI.RequestPlayerOperation(LocalPlayer,
        PlayerOperations.EXECUTE_SCRIPT, {
            AffectedPlots = AffectedPlots,
            OnStart = "IberiaProfoundSilenceResponsePositive",
        }
    )

    -- 触发子事件弹窗
    LuaEvents.Oph_EventPopup('EVENT_OPH_IBERIA_PROFOUND_SILENCE_1', 1)
    LuaEvents.Oph_Event_Finished()
end

-- 负面选择
function Iberia_Event_ProfoundSilence_Negative()
    UI.RequestPlayerOperation(LocalPlayer,
        PlayerOperations.EXECUTE_SCRIPT, {
            OnStart = "IberiaProfoundSilenceResponseNegative",
        }
    )
    LuaEvents.Oph_EventPopup('EVENT_OPH_IBERIA_PROFOUND_SILENCE_2', 1)
    LuaEvents.Oph_Event_Finished()
end

-- 不做任何事
function Oph_Event_DoNothing()
    LuaEvents.Oph_Event_Finished()
end

-- 注册到 LuaEvents
LuaEvents.Iberia_Event_ProfoundSilence_Positive.Add(Iberia_Event_ProfoundSilence_Positive)
LuaEvents.Iberia_Event_ProfoundSilence_Negative.Add(Iberia_Event_ProfoundSilence_Negative)
LuaEvents.Oph_Event_DoNothing.Add(Oph_Event_DoNothing)
```

## 步骤 5：场景特效恢复（加载时恢复全局状态）

```lua
function RestoreAssets()
    local AffectedPlots = Game.GetProperty('ProfoundSilenceAffectingPlot') or {}
    for iPlot, _ in pairs(AffectedPlots) do
        local pPlot = Map.GetPlotByIndex(iPlot)
        local key = pPlot:GetProperty('IsProfoundSilenceAffected') or 0
        if key > 0 then
            local worldX, worldY, worldZ = UI.GridToWorld(pPlot:GetX(), pPlot:GetY())
            local id = AssetPreview.Create("FXm_Radiation", worldX, worldY)
            if id >= 0 then
                AssetPreview.SetInstanceScale(id, 2)
            end
        end
    end
end

function Init()
    RestoreAssets()  -- 游戏加载时恢复所有特效
    Events.LocalPlayerTurnBegin.Add(OnLocalPlayerTurnBegin)
    -- 注册选择回调
    LuaEvents.Iberia_Event_ProfoundSilence_Positive.Add(...)
    LuaEvents.Iberia_Event_ProfoundSilence_Negative.Add(...)
end

Events.LoadGameViewStateDone.Add(Init)

include('GamePlayExtended_Ophidy_Iberia_ProfoundSilence_EventHandler_', true)
```

## 步骤 6：递增概率保底机制（反非洲人）

```lua
-- 条件3中的概率递增
-- 每次未触发，概率 +1%（起始5%，最大100%，即20回合保底）
local Trigger = math.max(5, pPlayer:GetProperty('TriggerKey') or 5)
if math.random() * 100 < Trigger then
    return true  -- 触发
else
    -- 增加下次概率
    UI.RequestPlayerOperation(iPlayer, EXECUTE_SCRIPT, {
        Key = 'TriggerKey',
        Value = Trigger + 1,
        OnStart = "SetProperty",
    })
    return false
end
```

## 完整事件流

```
[回合开始] LocalPlayerTurnBegin
  → 门控: 领袖匹配 / 人类玩家 / 非多人 / 未触发过 / 回合激活
  → 链式条件:
    [条件1: 7+港口] → [条件2: 文艺复兴+] → [条件3: 概率5%+]
      → 全部通过 → LuaEvents.Oph_EventPopup("EVENT_...")

[事件弹窗 UI]
  → CreateEventMethod["EVENT_..."]()
    → 读取 GameInfo.Oph_Events → 返回 {Title, Desc}
  → CreateChoiceMethod["CHOICE_POSITIVE"]()
    → 动态计算受影响城市 → 返回 {Title, Desc, Tooltip}
  → CreateChoiceMethod["CHOICE_NEGATIVE"]()
    → 动态计算受惩罚城市 → 返回 {Title, Desc, Tooltip}

[玩家选择正面]
  → LuaEvents.Iberia_Event_ProfoundSilence_Positive()
    → 遍历城市 → AssetPreview.Create("FXm_Radiation") 特效
    → UI.RequestPlayerOperation(EXECUTE_SCRIPT, {
        OnStart = "IberiaProfoundSilenceResponsePositive",
        AffectedPlots = {...}
      })
    → LuaEvents.Oph_EventPopup("..._1", 1)  -- 子事件
    → LuaEvents.Oph_Event_Finished()         -- 关闭弹窗

[子事件] CreateCustomChoice["EVENT_..._1"](1)
  → 返回 {Desc = "确定"} → 玩家点确定 → 关闭

[Gameplay 端] GameEvents.IberiaProfoundSilenceResponsePositive.Add(handler)
  → handler(playerID, params)
    → 对 AffectedPlots 中的每个地块执行效果
```

## 初始化完整事件绑定

```lua
function Init()
    RestoreAssets()

    Events.LocalPlayerTurnBegin.Add(OnLocalPlayerTurnBegin)

    -- 选择回调
    LuaEvents.Iberia_Event_ProfoundSilence_Positive.Add(Iberia_Event_ProfoundSilence_Positive)
    LuaEvents.Iberia_Event_ProfoundSilence_Negative.Add(Iberia_Event_ProfoundSilence_Negative)
    LuaEvents.Oph_Event_DoNothing.Add(Oph_Event_DoNothing)
end

Events.LoadGameViewStateDone.Add(Init)

-- 兼容热重载
include('GamePlayExtended_Ophidy_Iberia_ProfoundSilence_EventHandler_', true)
```

## 设计要点

1. **CreateEventMethod / CreateChoiceMethod 表驱动**：通过函数表注册而不是硬编码，支持多个 Mod 的多个事件共享同一 UI 框架
2. **动态 Tooltip**：选择项的 Tooltip 根据当前游戏状态动态生成（如列出受影响城市）
3. **多阶段事件链**：主事件 → 子事件 → 确认 → 关闭
4. **概率递增保底**：每次未触发增加概率，确保事件最终一定发生
5. **全局状态恢复**：`RestoreAssets()` 在游戏加载时恢复所有场景特效（通过 Game.GetProperty 跨存档持久化）
6. **AssetPreview.Create**：在 UI 端创建临时 3D 特效预览（不影响游戏状态，只需 assetName 在 AssetPreview 系统中注册）
7. **UI.RequestPlayerOperation 中的 OnStart 名称**：必须与 Gameplay 端的 `GameEvents.<name>.Add()` 一致
8. **门控检查**：触发前检查 领袖匹配/人类玩家/非多人/未触发过/回合激活
9. **LuaEvents 命名约定**：`ModName_Event_Type_Action`（如 `Iberia_Event_ProfoundSilence_Positive`）
10. **include('FileName_', true)**：兼容热重载

---

## XML 配合

### 用到的 XML 文件

| 来源 Mod | XML 文件路径 | 作用 |
|----------|------------|------|
| Iberia XP (3391173367) | `Event_ProfoundSilence/UI/Additions/ProfoundSilence/EventHandler_Iberia.xml` | 事件弹窗 UI 容器（空壳 Context） |
| Iberia XP (3391173367) | `Event_ProfoundSilence/UI/Additions/PenalBattalion/PenalBattalionCleansing.xml` | 净化单位按钮 Grid |
| Iberia XP (3391173367) | `Database/Iberia_ProfoundSilence_Texture.xml` | 事件 UI 纹理资源 |

### 控件 ID 对照

| XML 控件 ID | 类型 | Lua 角色 |
|------------|------|---------|
| `EventHandler_Iberia.xml` 中的 `Context` | 空壳 | 事件弹窗的宿主 Context，控件全在 Lua 中动态生成 |
| `PenalBattalionButtonGrid` | `Grid` | 净化按钮根容器，挂载到 UnitPanel |
| `PenalBattalionButton` | `Button` | 净化按钮 |
| `PenalBattalionButtonIcon` | `Image` | 净化按钮图标 |

### Instance 模板

事件选择框架的弹窗 UI 大部分在 Lua 中动态构建（使用函数表 `CreateEventMethod` / `CreateChoiceMethod`）。XML 端仅需要一个空白 Context 作为宿主：

```xml
<Context>
    <!-- 事件弹窗的容器由 Lua 动态生成，这里仅作为宿主 Context -->
</Context>
```

对于联动 UnitPanel 的净化按钮，复用标准单按钮模板（见 `lua-workshop-leader-unit-panel-injection.md`）：

```xml
<Context>
    <Grid ID="PenalBattalionButtonGrid" Anchor="R,B" Size="auto,41"
          Texture="SelectionPanel_ActionGroupSlot"
          SliceCorner="5,19" SliceSize="1,1" SliceTextureSize="12,41"
          ConsumeMouse="1" Alpha="1" Hide="true">
        <Button ID="PenalBattalionButton" Anchor="C,B" Size="44,53"
                Texture="UnitPanel_ActionButton">
            <Image ID="PenalBattalionButtonIcon" Anchor="C,C" Offset="0,-2"
                   Size="38,38" Icon="ICON_PENAL_BATTALION_UNITOPERATION_CLEANSING"/>
        </Button>
    </Grid>
</Context>
```

### 可复用 XML

- **空壳 Context**：当 UI 元素完全由 Lua 动态构建（InstanceManager + 函数表驱动）时，XML 仅需一个空的 `<Context>` 作为宿主
- **UnitPanel 按钮**：配合事件框架的操作按钮复用 `lua-workshop-leader-unit-panel-injection.md` 的单按钮模板
- 数据库表（`Oph_Events` / `Oph_EventChoices`）在 SQL 中定义，不在 XML 中
- `AssetPreview` 特效资源需在 `Database/*.art.xml` 或 `Icons.xml` 中注册
- 所有 UI Additions XML 作为 Context Additions 注册到 modinfo
