# lua-19-fever-system — Fever 进度累计 + 模式切换系统

从 Arknights_Cute_Leaders_19.0 的 Fever 系统提炼。核心模式：玩家属性累计 → 阈值触发 → 进入限时增益模式 → 倒计时恢复。

---

## 快速索引

| 组件 | 说明 |
|------|------|
| 累计属性 | `feverBalance` — 玩家 Property 存储的 Fever 值 |
| 模式标记 | `Isfever` — 是否处于 Fever 模式 |
| 倒计时 | `feverTime` — Fever 模式剩余回合数 |
| 最大阈值 | `feverMax` — 触发 Fever 需要的累计值 |
| 持续时间 | `faverMaxTime` — Fever 模式持续回合数 |

---

## 一、完整实现

### 1.1 配置常量 + 属性 Key

```lua
local feverMax = GlobalParameters.SiqiFeverMax or 450       -- Fever 最大值
local faverMaxTime = GlobalParameters.SiqiFeverTime or 10    -- Fever 模式持续时间
local feverCivic = GlobalParameters.SiqiFeverCivic or 20     -- 完成市政增加的 Fever 值
local feverTech = GlobalParameters.SiqiFeverTech or 20       -- 完成科技增加的 Fever 值

local feverBalance = "Siqi_Fever_Balance"   -- Fever 平衡值的存储键
local Isfever = "Siqi_Is_Fever_Mode"       -- 是否处于 Fever 模式的存储键
local feverTime = "Siqi_Fever_Time"         -- Fever 模式持续时间的存储键
```

### 1.2 核心 API：Change / Get / Set

```lua
-- 改变 Fever 值（自动夹在 0~feverMax 之间，Fever 模式下不增长）
function Fever:Change(playerID, amount)
    local pPlayer = Players[playerID]
    local Balance = pPlayer:GetProperty(feverBalance) or 0
    local IsfeverMode = pPlayer:GetProperty(Isfever) or false
    Balance = Balance + amount
    if IsfeverMode then
        Balance = 0                       -- Fever 模式下不接受增长
    else
        if Balance < 0 then Balance = 0 end
        if Balance > feverMax then Balance = feverMax end
    end
    pPlayer:SetProperty(feverBalance, Balance)
    return Balance
end

function Fever:Get(playerID)
    return Players[playerID]:GetProperty(feverBalance) or 0
end

function Fever:Set(playerID, amount)
    Players[playerID]:SetProperty(feverBalance, amount)
end
```

### 1.3 模式切换（最关键）

```lua
-- 设置 Fever 模式：为所有城市设置地块 Property、授予建筑、注册/移除回合事件
function Fever:SetFeverMode(playerID, isFever)
    local pPlayer = Players[playerID]
    pPlayer:SetProperty(Isfever, isFever)

    -- 遍历所有城市，设置地块 Fever 标记（供 SQL Modifier 检测）
    local pCities = pPlayer:GetCities()
    for _, pCity in pCities:Members() do
        local pPlot = Map.GetPlot(pCity:GetX(), pCity:GetY())
        local oldfever = pPlot:GetProperty("Siqi_City_Fever_Mode") or false
        if oldfever ~= isFever then
            pPlot:SetProperty("Siqi_City_Fever_Mode", isFever)
        end
    end

    if isFever then
        -- 进入 Fever：授予建筑、完成所有生产力、附加 Governor 点数
        SiqiGP.GrantBuilding(playerID, 'BUILDING_SIQI_MUJICA_1')
        SiqiGP.FinishProduction(playerID)
        pPlayer:AttachModifierByID("MODIFIER_SIQI_MUJICA_FEVER_MODE_4_GOVERNOR_POINTS")

        -- 注册每回合倒计时事件
        local TurnActivated = function(m_playerID, bIsFirstTime)
            if m_playerID ~= playerID or not bIsFirstTime then return end
            Fever:ChangeFeverTime(playerID, -1)
        end
        Events.PlayerTurnActivated.Add(TurnActivated)

        Fever:Set(playerID, 0)    -- 进入 Fever 时清零

        -- 触发额外效果（总督 M3 能力等）
        Mujica.Oblivionis.Governor:M3Ability(playerID)
    else
        -- 退出 Fever：移除建筑、移除倒计时事件
        SiqiGP.RemoveBuilding(playerID, 'BUILDING_SIQI_MUJICA_1')
        Events.PlayerTurnActivated.Remove(TurnActivated)  -- 注意：需要持有函数引用
    end
end
```

> **注意**：`Events.PlayerTurnActivated.Remove` 需要传原始函数引用，上述闭包写法实际使用时需要把函数存为 upvalue 以便移除。

### 1.4 倒计时逻辑

```lua
-- 改变 Fever 剩余时间：从 0 增长时自动进入 Fever，归零时自动退出
function Fever:ChangeFeverTime(playerID, amount)
    local pPlayer = Players[playerID]
    local time = pPlayer:GetProperty(feverTime) or 0
    if time == 0 and amount > 0 then
        Fever:SetFeverMode(playerID, true)   -- 从 0 开始 → 自动进入 Fever
    end
    time = time + amount
    if time < 0 then
        time = 0
        Fever:SetFeverMode(playerID, false)  -- 归零 → 自动退出 Fever
    end
    pPlayer:SetProperty(feverTime, time)
    return time
end
```

### 1.5 新城市刷新 Fever 状态

```lua
-- 新建城市时，同步当前 Fever 状态到地块
function Fever:RefreshCityFeverMode(playerID, CityID)
    local m_isfever = Fever:IsfeverMode(playerID)
    local pCity = CityManager.GetCity(playerID, CityID)
    local pPlot = Map.GetPlot(pCity:GetX(), pCity:GetY())
    local oldfever = pPlot:GetProperty("Siqi_City_Fever_Mode") or false
    if oldfever ~= m_isfever then
        pPlot:SetProperty("Siqi_City_Fever_Mode", m_isfever)
    end
end
```

### 1.6 事件注册（GP 端）

```lua
function Fever.Initialize()
    -- 完成科技/市政时增加 Fever
    Events.CivicCompleted.Add(function(playerID, iCivic)
        if not SiqiGP.HasProperty(Players[playerID], Civ_Mujica) then return end
        Fever:Change(playerID, feverCivic)
    end)
    Events.ResearchCompleted.Add(function(playerID, iTech)
        if not SiqiGP.HasProperty(Players[playerID], Civ_Mujica) then return end
        Fever:Change(playerID, feverTech)
    end)
end
```

---

## 二、SQL 端配合

Fever 模式通过地块 Property `Siqi_City_Fever_Mode` 驱动 Modifier：

```sql
-- 示例：Fever 模式下城市+50% 文化产出
-- ⚠️ MODIFIER_ALL_CITIES_ADJUST_CITY_YIELD_MODIFIER 是文档逻辑名，实际注册为自定义类型
--    MODIFIER_SIQI_MUJICA_ALL_CITIES_ADJUST_CITY_YIELD_MODIFIER（Types + DynamicModifiers，COLLECTION_ALL_CITIES）
INSERT INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId) VALUES
('MODIFIER_SIQI_MUJICA_FEVER_CULTURE', 'MODIFIER_SIQI_MUJICA_ALL_CITIES_ADJUST_CITY_YIELD_MODIFIER', 'REQSET_SIQI_MUJICA_FEVER_MODE');

INSERT INTO RequirementSets (RequirementSetId, RequirementSetType) VALUES
('REQSET_SIQI_MUJICA_FEVER_MODE', 'REQUIREMENTSET_TEST_ALL');

INSERT INTO RequirementSetRequirements VALUES
('REQSET_SIQI_MUJICA_FEVER_MODE', 'REQ_SIQI_MUJICA_FEVER_MODE');

INSERT INTO Requirements (RequirementId, RequirementType) VALUES
('REQ_SIQI_MUJICA_FEVER_MODE', 'REQUIREMENT_PLOT_PROPERTY_MATCHES');

INSERT INTO RequirementArguments (RequirementId, Name, Value) VALUES
('REQ_SIQI_MUJICA_FEVER_MODE', 'PropertyName', 'Siqi_City_Fever_Mode'),
('REQ_SIQI_MUJICA_FEVER_MODE', 'PropertyMinimum', 1);
```

---

## 三、关键要点

| 要点 | 说明 |
|------|------|
| Property 存储累计值 | 用 Player Property 而非 UI 变量，支持存档 |
| 进入模式时清零 | `Fever:Set(playerID, 0)` 避免溢出 |
| 模式下不累积 | `Change()` 中检查 `IsfeverMode` |
| 地块标记 | 用 Plot Property 标记 Fever 状态，供 SQL Modifier 检测 |
| 倒计时自动退出 | `ChangeFeverTime()` 处理进入/退出双向逻辑 |
| 新城市同步 | 新建城市需调用 `RefreshCityFeverMode` |
| 事件注册/移除 | 用 `Events.PlayerTurnActivated.Add/Remove` 管理倒计时回调 |

---

## 四、变体：无需 Fever 模式的简单累计系统

```lua
-- 最简单：只累计，阈值触发一次性奖励后重置
local THRESHOLD = 200

function OnTurnActivated_Simple(playerID)
    local pPlayer = Players[playerID]
    local accumulated = pPlayer:GetProperty("MyMod_Accumulated") or 0
    local perTurn = pPlayer:GetProperty("MyMod_PerTurn") or 0
    if perTurn <= 0 then return end

    accumulated = accumulated + perTurn
    if accumulated >= THRESHOLD then
        -- 触发奖励
        pPlayer:AttachModifierByID("MODIFIER_MYMOD_REWARD")
        accumulated = accumulated - THRESHOLD  -- 保留溢出
    end
    pPlayer:SetProperty("MyMod_Accumulated", accumulated)
end
```
