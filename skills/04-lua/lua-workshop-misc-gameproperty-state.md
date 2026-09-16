# GameProperty 跨端状态持久化

## 来源
- Choosable Goody Huts (Konomi, id=3014867813) — 追踪地图上的村庄归属
- Celebrations (Nwflower, id=3492136529) — 追踪幸福值、庆典次数

## 概述
`Game:SetProperty` / `Game:GetProperty` 和 `Player:SetProperty` / `Player:GetProperty` 是 Civ 6 Lua 中最重要的跨上下文状态存储机制。GameProperty 在 Gameplay 端和 UI 端均可读写，且自动保存到存档。

## 两种 Property 对比

| 特性 | Game:SetProperty | Player:SetProperty |
|------|-----------------|-------------------|
| 作用域 | 全局游戏 | 单个玩家 |
| UI 端可写 | 否（仅读） | 否（仅读，需 GP 代理） |
| GP 端可读写 | 是 | 是 |
| 存档持久 | 是 | 是 |
| 类型 | 任意 Lua 值（含 table） | 任意 Lua 值 |
| 限制 | 无明确限制 | 无明确限制 |
| 典型用途 | 地图共享数据 | 玩家私有数据 |

## 模式 1：玩家私有数据 (Player:SetProperty/GetProperty)

适用于追踪每个玩家的独立数据：

```lua
-- Gameplay 端
local KEY_POINTS = 'YourSystemPoints'
local KEY_TIMES = 'YourSystemTimes'

-- 设置
function SetPoints(playerID, value)
    Players[playerID]:SetProperty(KEY_POINTS, value)
end

-- 读取
function GetPoints(playerID)
    local pPlayer = Players[playerID]
    if not pPlayer then return 0 end
    return pPlayer:GetProperty(KEY_POINTS) or 0  -- 默认值
end

-- 修改（累加）
function AddPoints(playerID, delta)
    local current = GetPoints(playerID)
    SetPoints(playerID, current + delta)
    return current + delta
end
```

**UI 端读取**（无需 GP 代理）：
```lua
local point = Players[localPlayerID]:GetProperty('YourSystemPoints') or 0
```

## 模式 2：全局共享数据 (Game:SetProperty/GetProperty)

适用于需要在多个玩家之间共享的数据：

```lua
-- Gameplay 端：追踪地图上的村庄
local KEY_GOODY = 'CGH_GOODY'
local m_GoodyHuts = {}  -- { [plotIndex] = ownerPlayerID }

-- 初始化（扫描全图）
function InitializeData()
    m_GoodyHuts = {}
    local mapWidth, mapHeight = Map.GetGridSize()
    for i = 0, mapWidth * mapHeight - 1 do
        local pPlot = Map.GetPlotByIndex(i)
        if pPlot:GetImprovementType() == improvementIndex then
            m_GoodyHuts[i] = -1  -- -1 表示无归属
        end
    end
    Game:SetProperty(KEY_GOODY, m_GoodyHuts)
end

-- 地图变化时更新
function OnImprovementAddedToMap(iX, iY, eImprovement, playerID)
    if eImprovement == targetIndex then
        -- 从 Game 中读取（可能在上一帧被其他事件修改）
        m_GoodyHuts = Game:GetProperty(KEY_GOODY)
        if m_GoodyHuts == nil then InitializeData() end

        local pPlot = Map.GetPlot(iX, iY)
        m_GoodyHuts[pPlot:GetIndex()] = playerID
        Game:SetProperty(KEY_GOODY, m_GoodyHuts)  -- 写回
    end
end

Events.ImprovementAddedToMap.Add(OnImprovementAddedToMap)
```

**重要**：由于 `Game:SetProperty` 会触发事件，多个事件处理函数可能交错执行。因此每次修改前必须重新 `Game:GetProperty` 获取最新值，修改后再 `Game:SetProperty`。

## 模式 3：UI 端写入 Property（通过 GP 代理）

UI 端不能直接 `SetProperty`，必须通过 `UI.RequestPlayerOperation` 让 GP 端执行：

```lua
-- UI 端
function AddPointsFromUI(delta)
    local kParameters = {}
    kParameters.OnStart = 'YourPointsAddHandler'
    kParameters.delta = delta
    UI.RequestPlayerOperation(Game.GetLocalPlayer(),
                             PlayerOperations.EXECUTE_SCRIPT, kParameters)
end

-- Gameplay 端
function OnPointsAddFromUI(playerID, params)
    AddPoints(playerID, params.delta)
end
GameEvents.YourPointsAddHandler.Add(OnPointsAddFromUI)
```

## 模式 4：Object Property（建筑/单位级别属性）

Celbrations 的 `CelebrationsCore.lua` 提供了通用的 ObjectProperty 设置方法：

```lua
local g_ObjectStateCache = {}

function SetObjectState(pObject, sPropertyName, value)
    if not pObject then return end

    -- 缓存一份在 Lua 端（避免频繁跨 C 边界查询）
    if g_ObjectStateCache[pObject] == nil then
        g_ObjectStateCache[pObject] = {}
    end
    g_ObjectStateCache[pObject][sPropertyName] = value

    if UI ~= nil then
        -- UI 端无法直接修改，通过 PlayerOperations 代理
        local kParameters = {}
        kParameters.propertyName = sPropertyName
        kParameters.value = value
        kParameters.objectID = pObject:GetComponentID()
        kParameters.OnStart = "OnPlayerCommandSetObjectState"
        UI.RequestPlayerOperation(Game.GetLocalPlayer(),
                                 PlayerOperations.EXECUTE_SCRIPT, kParameters)
    else
        -- GP 端直接设置
        if pObject.SetProperty then
            pObject:SetProperty(sPropertyName, value)
        end
    end
end

-- GP 端响应 UI 请求
function OnPlayerCommandSetObjectStateHandler(ePlayer, params)
    local pObject = Game.GetObjectFromComponentID(params.objectID)
    if pObject then
        SetObjectState(pObject, params.propertyName, params.value)
    end
end
GameEvents.OnPlayerCommandSetObjectState.Add(OnPlayerCommandSetObjectStateHandler)
```

## 模式 5：Effect 解锁标记

Celebrations 使用 Property 作为效果解锁标记：

```sql
-- SQL 表定义
CREATE TABLE YourOptions (
    OptionType TEXT PRIMARY KEY,
    UnlocksFromEffect INTEGER DEFAULT 0  -- 是否需要解锁
);

-- SQL 表插入
INSERT INTO YourOptions (OptionType, UnlocksFromEffect)
VALUES ('YOUR_OPTION_BOAT_BOOST', 1);
```

```lua
-- GP 端：当条件满足时设置解锁标记
function UnlockBoatBoost(playerID)
    local isActivated = Players[playerID]:GetProperty('Property_YOUR_OPTION_BOAT_BOOST')
    if not isActivated then
        Players[playerID]:SetProperty('Property_YOUR_OPTION_BOAT_BOOST', 1)
    end
end

-- UI 端：检查解锁条件
function IsOptionUnlocked(playerID, optionType)
    local row = GameInfo.YourOptions[optionType]
    if row and row.UnlocksFromEffect == 1 then
        return Players[playerID]:GetProperty('Property_' .. optionType) ~= nil
    end
    return true
end
```

**命名约定**：效果解锁标记统一用 `'Property_' .. OptionType`。

## 模式 6：地图初始化时的数据加载

需要在 `LoadGameViewStateDone` 事件中初始化，确保游戏数据已加载：

```lua
function Initialize()
    -- 先尝试从 Game:GetProperty 加载（读档情况）
    m_Data = Game:GetProperty(KEY_DATA)
    if m_Data == nil then
        InitializeData()  -- 新游戏，扫描地图
    end
end

Events.LoadGameViewStateDone.Add(Initialize)
```

**注意**：不要在 `LoadScreenClose` 等过早事件中初始化，此时游戏数据可能还未完全加载。

## 要点总结

1. **Player vs Game**：玩家独有数据用 `Player:SetProperty`，共享数据用 `Game:SetProperty`
2. **UI 只读**：UI 端只能读 Property，写必须通过 `UI.RequestPlayerOperation` 代理到 GP
3. **默认值**：始终用 `or default_value` 处理首次读取为 nil 的情况
4. **读写循环**：修改 GameProperty 时先读再写，防止冲突
5. **存档安全**：所有 Property 自动保存到存档，无需手动序列化
6. **命名约定**：用有意义的 key，避免与其他 Mod 冲突（加前缀）
7. **缓存可选**：频繁读取可以缓存到局部变量，但修改时必须写回
