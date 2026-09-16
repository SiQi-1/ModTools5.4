# 科技/文化溢出计算器 (Tech/Civic Overflow Calculator)

## 来源
- TechCivicProgressPlus (Firstborn/DeepLogic, id=2604740398) — 科技溢出计算与 Tooltip 增强

## 概述
计算科技/文化研究中存在的溢出量，用于在 UI 上显示"当前拥有 X 溢出"。核心算法是二分搜索找到实际的单回合产出。

## XML 配合

本系统为纯 Lua 计算机制，无独立 UI 面板。溢出数值通过修改游戏的科技/文化 Tooltip 字符串来呈现（在 `GetScienceTooltip()` / `GetCultureTooltip()` 中追加），无需额外 XML 控件。注意需要替换或 hook 原版 `ToolTipHelper_PlayerYields.lua` 来注入溢出文本。

---

## 核心概念

Civ 6 的科技/文化进度存储为整数，但每回合产出可能包含小数。如果玩家面板显示"3 回合完成"，实际可能是 2.1 到 3.0 回合之间。溢出计算器通过二分搜索找到真实产出。

```
已知：第N回合进度 = 面板整数进度
已知：面板显示的回合数 = turnsLeft（整数）
求解：真实的每回合产出 yield（带小数）

数学关系：
  cost - progress = turnsLeft * yield + overflow
  其中 overflow = yield - (cost - progress - (turnsLeft-1) * yield)
  即 overflow = turnsLeft * yield - (cost - progress)
```

## 步骤 1：溢出公式

```lua
-- 已知：
--   progress: 当前进度值（整数）
--   cost: 总成本
--   turnsLeft: 面板显示的剩余回合数
--   yield: 每回合产出（含小数，未知精确值）
--
-- 求溢出量：
--   溢出 = yield * turnsLeft - (cost - progress)
--   其中 yield 的真实值在区间内：
--     minV = (cost - progress) / turnsLeft       -- 刚好 turnsLeft 回合
--     maxV = (cost - progress) / (turnsLeft - 1) -- 刚好 turnsLeft-1 回合
```

## 步骤 2：二分搜索实现

```lua
function GetOverflowHelper(playerID, yield, itemId, minV, maxV, is_tech, research_cost)
    -- 精度足够时停止
    if math.abs(maxV - minV) < 0.05 then
        return (maxV + minV) / 2
    end

    -- 取中点，计算新进度
    local cost = (minV + maxV) / 2 + yield
    local progress = research_cost - cost

    if is_tech then
        Players[playerID]:GetTechs():SetResearchProgress(itemId, progress)
        turnsLeft = Players[playerID]:GetTechs():GetTurnsToResearch(itemId)
    else
        Players[playerID]:GetCulture():SetCulturalProgress(itemId, progress)
        turnsLeft = Players[playerID]:GetCulture():GetTurnsLeftOnCurrentCivic()
    end

    -- 根据回合数收缩区间
    local minCand = cost - turnsLeft * yield
    local maxCand = cost - (turnsLeft - 1) * yield

    if minCand > minV then minV = minCand end
    if maxCand < maxV then maxV = maxCand end

    return GetOverflowHelper(playerID, yield, itemId, minV, maxV, is_tech, research_cost)
end
```

**注意**：这个函数会临时修改科技进度来探测回合数，最后必须恢复原始进度值。

## 步骤 3：科技溢出完整计算

```lua
function GetTechOverflow()
    local playerID = Game.GetLocalPlayer()
    local playerTech = Players[playerID]:GetTechs()
    local scienceYield = playerTech:GetScienceYield()

    if scienceYield <= 0 then return 0 end

    -- 找最后一个未研究的科技（树的最深层）
    local lastTechID = nil
    for tech in GameInfo.Technologies() do
        if tech.Index and not playerTech:HasTech(tech.Index) then
            lastTechID = tech.Index
        end
    end

    if not lastTechID then return 0 end

    local savProgress = playerTech:GetResearchProgress(lastTechID)
    local techCost = playerTech:GetResearchCost(lastTechID)
    local turnsLeft = playerTech:GetTurnsToResearch(lastTechID)

    -- 还原到至少需要 2 回合以上（排除 1 回合完成的情况）
    while turnsLeft <= 1 do
        playerTech:SetResearchProgress(lastTechID,
            playerTech:GetResearchProgress(lastTechID) - scienceYield)
        turnsLeft = playerTech:GetTurnsToResearch(lastTechID)
    end

    if turnsLeft > 2 then
        playerTech:SetResearchProgress(lastTechID,
            playerTech:GetResearchProgress(lastTechID) + (turnsLeft - 2) * scienceYield)
    end

    -- 计算溢出
    turnsLeft = playerTech:GetTurnsToResearch(lastTechID)
    local cost = playerTech:GetResearchCost(lastTechID) - playerTech:GetResearchProgress(lastTechID)
    local min = cost - turnsLeft * scienceYield
    local max = cost - (turnsLeft - 1) * scienceYield
    local overflow = GetOverflowHelper(playerID, scienceYield, lastTechID, min, max, true, techCost)

    -- 恢复原始进度
    playerTech:SetResearchProgress(lastTechID, savProgress)

    return math.max(0, overflow)
end
```

## 步骤 4：跨文件通信 (ExposedMembers)

```lua
-- 文件 A: CheckOverflow.lua (AddGameplayScripts)
ExposedMembers.TechCivicProgress = {}
ExposedMembers.TechCivicProgress.overflow_tech = 0
ExposedMembers.TechCivicProgress.overflow_civic = 0
ExposedMembers.TechCivicProgress.GetTechOverflow = GetTechOverflow
ExposedMembers.TechCivicProgress.GetCivicOverflow = GetCivicOverflow

-- 文件 B: ToolTipHelper_PlayerYields.lua (ImportFiles / UI)
-- 读取结果
local overflow = ExposedMembers.TechCivicProgress.overflow_tech
-- 或在需要时调用计算
ExposedMembers.TechCivicProgress.GetTechOverflow()
local overflow = ExposedMembers.TechCivicProgress.overflow_tech
```

## 步骤 5：UI 触发计算时机

在 Tooltip 显示时触发计算：

```lua
local localTurnTech = 0
local localCurTech = -1
local localCurTechProgress = -1
local localTurnTechComputed = false

function GetScienceTooltip()
    -- ... 获取标准 tooltip ...
    local pPlayerTechs = Players[localPlayerID]:GetTechs()
    local scienceYield = pPlayerTechs:GetScienceYield()

    if scienceYield > 0 then
        local curTech = pPlayerTechs:GetResearchingTech()
        local curProgress = pPlayerTechs:GetResearchProgress(curTech)

        -- 只在回合变化或科技变化时重新计算
        if localTurnTech < Game.GetCurrentGameTurn() then
            localTurnTech = Game.GetCurrentGameTurn()
            localTurnTechComputed = false
            localCurTech = curTech
            localCurTechProgress = curProgress
        elseif (curTech ~= localCurTech or curProgress ~= localCurTechProgress)
               and (not localTurnTechComputed) then
            localTurnTechComputed = true
            ExposedMembers.TechCivicProgress.GetTechOverflow()
        end

        -- 显示溢出
        local overflow = ExposedMembers.TechCivicProgress.overflow_tech
        szReturnValue = szReturnValue .. "[NEWLINE] " ..
            Locale.Lookup("LOC_RESEARCH_OVERFLOW") ..
            " " .. string.format("%.1f", overflow)
    end
    return szReturnValue
end
```

## 步骤 6：研究完成后自动计算

```lua
local localTechCompleted = -1
function OnResearchCompleted(player, tech)
    if player == Game.GetLocalPlayer() and localTechCompleted ~= tech then
        localTechCompleted = tech
        ExposedMembers.TechCivicProgress.GetTechOverflow()
    end
end
Events.ResearchCompleted.Add(OnResearchCompleted)
```

## 要点总结

1. **二分搜索精度**：`< 0.05` 足够精确
2. **临时修改进度恢复**：计算完后务必用保存的值恢复
3. **排除 1 回合完成**：通过减少进度使 turnsLeft > 1，确保有溢出空间
4. **ExposedMembers**：跨文件通信的标准方式，AddGameplayScripts 文件定义，UI 文件读取
5. **缓存计算结果**：每回合重新计算，不需每帧计算
6. **溢出为 0 时不显示**：`math.max(0, overflow)` 保证不为负

## 文化溢出的特殊性

文化溢出计算更复杂，因为 Civ 6 没有 `GetResearchingCivic()`（正在研究什么），需要：
1. 用 `GetProgressingCivic()` 获取当前正在进行的市政
2. 用 `GetCivicQueue()` 获取市政队列
3. 手动切换 `SetProgressingCivic()` 来探测最后一层的溢出

因此 TechCivicProgressPlus 的文化溢出部分默认被注释掉了。
