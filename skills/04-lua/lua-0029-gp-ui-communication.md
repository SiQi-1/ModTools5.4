# GP↔UI 通信模式（来源：0029）

## 做什么
文明 6 Mod 中，Gameplay Script（GP）和 UI Script 运行在不同线程/上下文中。GP 可以修改游戏数据但不能读 UI，UI 可以读取游戏数据但不能修改。0029 使用了一套完整的跨线程通信模式来解决此问题，让 UI 端计算的数据能安全传递到 GP 端执行。

## 涉及文件

| 文件 | 角色 |
|------|------|
| `Support/Siqi_Leaders_0029_Core.lua` | GP+UI 共用逻辑（含通信桥） |
| `Support/Siqi_Leaders_0029_Support.lua` | GP/UI 双模式函数定义 |
| `Lua/Siqi_Leaders_0029_Gameplay.lua` | GP 端事件注册 |
| `UI/*.lua` | UI 端发起请求、显示数据 |

## 三种通信方式

### 方式一：UI.RequestPlayerOperation（UI → GP，主动修改）

UI 端无法直接修改游戏数据（如给玩家加资源），必须通过此方式委托 GP 端执行。

**模式：**
```lua
-- UI 端：发起请求
local params = {
    OnStart = 'Siqi0029_EventName',  -- 事件名，GP 端通过 GameEvents 监听
    Value = 100,                      -- 任意数据字段
    CityID = cityID
}
UI.RequestPlayerOperation(playerID, PlayerOperations.EXECUTE_SCRIPT, params)

-- GP 端：注册监听
GameEvents.Siqi0029_EventName.Add(function(playerID, params)
    -- 安全地修改游戏数据
    Core.ChangeLZ(playerID, params.Value)
end)
```

**0029 中所有 EXECUTE_SCRIPT 通信管道：**

| OnStart 事件名 | 携带数据 | GP 端处理 |
|---------------|---------|----------|
| `Siqi0029_ChangeLZ` | `Value` | Core.ChangeLZ (灵值增减) |
| `Siqi0029_ChangeCityRouteEnd` | `Value1`, `CityID` | 设置城市商路终点属性 |
| `Siqi0029_MainQuestComplete` | — | QUESTS:CompleteMainQuest |
| `Siqi0029_RefreshSideQuest` | `SlotIndex` | QUESTS:RefreshSideQuest |
| `Siqi0029_ForceCompleteSideQuest` | `SlotIndex`, `Cost` | QUESTS:ForceCompleteSideQuest |
| `Siqi0029_UnitButton_LZSJ` | `UnitID`, `PlotID`, `Dead`, `Up`, `LingZhi`, `iX`, `iY` | Core.GP.UnitButton_LZSJ |
| `Siqi_Leaders_0029_Purchase_SL` | `CityID`, `Cost` | Core.GP.OnPurchaseSL |

### 方式二：GameEvents（双向广播）

GameEvents 可在 UI 和 GP 两侧都触发/监听，是 0029 中数据从 UI 流向 GP 的主要管道（如城市产出、政体状态等信息 UI 可读但 GP 不行）。

**关键 GameEvents 清单：**

| 事件名 | 发送方 | 携带数据 | 用途 |
|--------|-------|---------|------|
| `Siqi0029_CityYield` | UI (MainPanel) | `Data` (按城市ID索引的产出表) | 供 CityYieldAtLeastX 等任务监听 |
| `Siqi0029_GovernmentData` | UI (MainPanel) | `GovernmentType` | 供 UseSpecificGovernment 任务监听 |
| `Siqi0029_MaxAdjacencyBonusInDistrict` | UI (MainPanel) | `Adjacencies` (按区域类型的邻接表) | 供 HaveAdjacencyBonusInDistrict 任务监听 |
| `Siqi0029AllianceAvailable` | UI | `OtherPlayerID` | L4 领袖监听联盟达成 |

### 方式三：LuaEvents（GP ↔ GP 同侧通信）

用于 GP 上下文内的模块间通信和广播（无需跨线程）。

**0029 的关键 LuaEvents：**

| 事件名 | 广播时机 | 监听者 |
|--------|---------|-------|
| `Siqi0029_LingZhiChanged(playerID, ChangeValue)` | Core.ChangeLZ 每次修改灵值 | GainXSoulPoints 任务、UI 面板 |
| `Siqi0029_MainQuestCompleted(playerID, CurrentLevel)` | 主线任务完成 | L1 樱墨曦 |
| `Siqi0029_SideQuestCompleted(playerID, DistrictType)` | 支线任务完成 | Core.GP.OnSideQuestCompleted（发放伟人）+ CompleteXDistrictQuests 任务 |
| `Siqi0029_UnitConverted(playerID, unitID, iX, iY)` | 凰茗狐转化单位成功 | ConvertXUnitsWithHuangMingHu 任务 |
| `Siqi0029_StopQuestListening(playerID, SlotIndex)` | 任务刷新/重设时 | 各任务的 stop_listening 闭包 |
| `Siqi0029_SetQuestData(playerID, params)` | DEBUG 手动设置 | QUESTS.SetQuestData |
| `Siqi0029_HistoricMoment(playerID, eraScore)` | 历史时刻达成 | AchieveXHistoricMomentsOfAtLeast4Stars 任务 |

## 方式四：Game Property 变更（GP → UI 信号）

通过 `Game.SetProperty` / `Game.GetProperty` 实现变更通知，UI 端通过 `Events.GamePropertyChanged` 检测变化。

**广播函数：**
```lua
function QUESTS:BroadcastQuestDataChanged()
    -- 每次触发都切换 true/false，确保总有一次变化
    if Game:GetProperty('Siqi_Leaders_0029_Quest_Data_Changed') then
        Game:SetProperty('Siqi_Leaders_0029_Quest_Data_Changed', false)
    else
        Game:SetProperty('Siqi_Leaders_0029_Quest_Data_Changed', true)
    end
end
```

**UI 端监听：**
```lua
Events.GamePropertyChanged.Add(function(propertyName)
    if propertyName == 'Siqi_Leaders_0029_Quest_Data_Changed' then
        RefreshQuestUI() -- 重新读取任务数据
    end
end)
```

## 数据流动全景图

```
UI 端（可读游戏数据）                     GP 端（可修改游戏数据）
┌─────────────────────┐                  ┌──────────────────────┐
│ MainPanel.lua       │                  │ Core.lua / Gameplay  │
│                     │                  │                      │
│ GetData() 计算灵值   │──EXECUTE_SCRIPT──▶│ Core.ChangeLZ()      │
│ RefreshQuestData()  │──EXECUTE_SCRIPT──▶│ QUESTS:CompleteMain  │
│ UnitButton 交互      │──EXECUTE_SCRIPT──▶│ UnitButton_LZSJ      │
│                     │                  │                      │
│ 发送 GameEvents:    │──GameEvents─────▶│ 各任务监听函数        │
│  CityYield          │                  │ (CityYieldAtLeastX等) │
│  GovernmentData     │                  │ (UseSpecificGov等)    │
│  AdjacencyBonus     │                  │ (HaveAdjacency等)     │
│                     │                  │                      │
│                     │◀─GameProperty───│ BroadcastQuestChanged │
│ 监听 PropertyChanged│                  │                      │
└─────────────────────┘                  └──────────────────────┘

GP 内部（同侧通信）：
   Core.ChangeLZ ──LuaEvents──▶ QUESTS.GainXSoulPoints 任务
   QUESTS 完成   ──LuaEvents──▶ L1.OnSiqi0029_MainQuestCompleted
   Combat        ──LuaEvents──▶ QUESTS.ConvertXUnitsWithHuangMingHu
```

## 设计要点

1. **GP 端唯一写入口**：所有游戏数据修改必须通过 `UI.RequestPlayerOperation` → `GameEvents` → GP 代码执行
2. **UI 端唯一读入口**：GP 无法直接读取城市产出、政体等 UI 专属数据，由 UI 端通过 GameEvents 主动推送
3. **事件名约定**：EXECUTE_SCRIPT 通信使用短事件名（如 `Siqi0029_ChangeLZ`），GameEvents 使用带模块前缀的完整名
4. **Property 信号**：用于简单的"数据变了请重新读"通知，避免携带大量数据跨线程传递
5. **LuaEvents 同侧**：用于 GP 内部解耦，各模块通过广播方式交互而不直接耦合
