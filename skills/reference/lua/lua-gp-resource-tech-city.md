# lua-gp-resource — 非战斗类 GP 函数 — 科技/城市状态

> 分册：由 [lua-gp-resource.md](lua-gp-resource.md) 按主题拆出；覆盖 科技市政、获取已完成尤里卡但未研究的科技列表、判断某时代科技是否全部已触发尤里卡、赠送某时代全部未完成科技、判断某时代市政是否全部已触发鼓舞、赠送某时代全部未完成市政、解锁政体（完成前置市政，稳定写法）、HasTech — 检查玩家是否拥有某科技、HasCivic — 检查玩家是否拥有某市政、城市状态 / Property、城市宜居度计算（GP 精确版）、宜居度转二进制属性（桃金娘 / 苏苏洛共用）、星辉系统：消耗星辉 → 触发鼓舞/尤里卡、摩拉产出系统核心：UI 计算 → GP 写 Property、BroadcastRefresh — 广播刷新（GP → UI 通知）。触发：改科技市政、城市状态与 Property 时。

## 科技市政

### 获取已完成尤里卡但未研究的科技列表

```lua
function GetHasBoostTechs(playerID)
    local pPlayer = Players[playerID]
    local playerTechs = pPlayer:GetTechs()
    local Techs = {}
    for tech in GameInfo.Technologies() do
        if playerTechs:HasBoostBeenTriggered(tech.Index) and (not playerTechs:HasTech(tech.Index)) then
            table.insert(Techs, tech.Index)
        end
    end
    return Techs
end
```

### 判断某时代科技是否全部已触发尤里卡

传入 playerID 和某个科技的 Index，返回该科技所属 Era 是否全部未完成科技都已触发尤里卡。

```lua
function HasTechBoostForEra(playerID, iTech)
    local pPlayer = Players[playerID]
    local playerTechs = pPlayer:GetTechs()
    local TechInfo = GameInfo.Technologies[iTech]
    if TechInfo == nil then return false end
    local EraType = TechInfo.EraType
    local AllHasBoost = true
    for tech in GameInfo.Technologies() do
        if tech.EraType == EraType
            and (not playerTechs:HasBoostBeenTriggered(tech.Index))
            and (not playerTechs:HasTech(tech.Index)) then
            AllHasBoost = false
            break
        end
    end
    return AllHasBoost
end
```

### 赠送某时代全部未完成科技

```lua
function RewardTechBoostForEra(playerID, iTech)
    local pPlayer = Players[playerID]
    local playerTechs = pPlayer:GetTechs()
    local TechInfo = GameInfo.Technologies[iTech]
    local EraType = TechInfo.EraType
    for tech in GameInfo.Technologies() do
        if tech.EraType == EraType and (not playerTechs:HasTech(tech.Index)) then
            playerTechs:SetResearchProgress(tech.Index, playerTechs:GetResearchCost(tech.Index))
        end
    end
end
```

### 判断某时代市政是否全部已触发鼓舞

```lua
function HasCivicBoostForEra(playerID, iCivic)
    local pPlayer = Players[playerID]
    local playerCivics = pPlayer:GetCulture()
    local CivicInfo = GameInfo.Civics[iCivic]
    if CivicInfo == nil then return false end
    local EraType = CivicInfo.EraType
    local AllHasBoost = true
    for civic in GameInfo.Civics() do
        if civic.EraType == EraType
            and (not playerCivics:HasBoostBeenTriggered(civic.Index))
            and (not playerCivics:HasCivic(civic.Index)) then
            AllHasBoost = false
            break
        end
    end
    return AllHasBoost
end
```

### 赠送某时代全部未完成市政

```lua
function RewardCivicBoostForEra(playerID, iCivic)
    local pPlayer = Players[playerID]
    local playerCivics = pPlayer:GetCulture()
    local CivicInfo = GameInfo.Civics[iCivic]
    local EraType = CivicInfo.EraType
    for civic in GameInfo.Civics() do
        if civic.EraType == EraType and (not playerCivics:HasCivic(civic.Index)) then
            playerCivics:SetCulturalProgress(civic.Index, playerCivics:GetCultureCost(civic.Index))
        end
    end
end
```

### 解锁政体（完成前置市政，稳定写法）

`UnlockGovernment`/`IsGovernmentUnlocked` 官方源码零使用、0054 实测**开局崩溃** → 弃用（memory feedback-0054-government-unlock）。政体可用判定 = 其 `PrereqCivic` 已完成 → 稳定实现 = 遍历政体收集前置市政并"立即完成市政"：

```lua
-- 每回合幂等兜底（读档自愈）
-- 跳过 PrereqCivic=NULL（初始政体酋邦无前置）
-- T1 三政体共用 CIVIC_POLITICAL_PHILOSOPHY → table 去重只完成一次
function UnlockGovernmentsByCivic(playerID)
    local pCulture = Players[playerID]:GetCulture();
    if pCulture == nil then return end
    local civicToComplete = {};
    for row in GameInfo.Governments() do
        local prereq = row.PrereqCivic;
        if prereq ~= nil then
            local civicInfo = GameInfo.Civics[prereq];
            if civicInfo ~= nil and not pCulture:HasCivic(civicInfo.Index) then
                civicToComplete[civicInfo.Index] = civicInfo.Index;
            end
        end
    end
    for _, civicIndex in pairs(civicToComplete) do
        pCulture:SetCulturalProgress(civicIndex, pCulture:GetCultureCost(civicIndex));
    end
end
```

- `SetCulturalProgress(idx, GetCultureCost(idx))` = "立即赠送市政"（0013/0026/0029/0030/18.0 出货 Mod 实证）
- 政策卡直接全量 `UnlockPolicy(Index)`（`for row in GameInfo.Policies()` + `IsPolicyUnlocked` 幂等）；`ExplicitUnlock=1` 自创卡与基础卡均可用此法解锁
- 完成市政会连带解锁该市政的奖励政策（"任意政体+任意政策"文案即此口径）

### HasTech — 检查玩家是否拥有某科技

```lua
function HasTech(playerID, techType)
    if not techType or techType == "" then return true end
    local pPlayer = Players[playerID]
    if not pPlayer then return false end
    local techInfo = GameInfo.Technologies[techType]
    if not techInfo then return false end
    local pTeam = Teams[pPlayer:GetTeam()]
    if not pTeam then return false end
    return pTeam:HasTech(techInfo.Index)
end
```

### HasCivic — 检查玩家是否拥有某市政

```lua
function HasCivic(playerID, civicType)
    if not civicType or civicType == "" then return true end
    local pPlayer = Players[playerID]
    if not pPlayer then return false end
    local civicInfo = GameInfo.Civics[civicType]
    if not civicInfo then return false end
    local pCulture = pPlayer:GetCulture()
    if not pCulture then return false end
    return pCulture:HasCivic(civicInfo.Index)
end
```

---

## 城市状态 / Property

### 城市宜居度计算（GP 精确版）

基于 GlobalParameters 精确计算溢出宜居度：总宜居度 + 免费宜居度 - 人口消耗。

```lua
function GetCitySurplusAmenities(pCity)
    local CityGrowth = pCity:GetGrowth()
    local TotalAmenities = CityGrowth:GetAmenities()
    local Population = pCity:GetPopulation()
    local CITY_POP_PER_AMENITY = GameInfo.GlobalParameters['CITY_POP_PER_AMENITY'].Value
    local AmenitiesNeeded_FromPopulation = math.ceil(Population / CITY_POP_PER_AMENITY)
    local CITY_AMENITIES_FOR_FREE = GameInfo.GlobalParameters['CITY_AMENITIES_FOR_FREE'].Value
    local Count = TotalAmenities + CITY_AMENITIES_FOR_FREE - AmenitiesNeeded_FromPopulation
    return Count
end
```

### 宜居度转二进制属性（桃金娘 / 苏苏洛共用）

城市溢出宜居度→地块二进制 Property。桃金娘：每 2 宜居度 +10% 产出。苏苏洛：补全到 6 再修正。

```lua
-- 二进制表常量
local NumberTable = {1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048}

-- 数字转定长二进制表
function NumToBinary(num, length)
    local result = {}
    for i = 1, length do
        result[i] = 0
        if num >= NumberTable[i] then
            result[i] = 1
            num = num - NumberTable[i]
        end
    end
    return result
end

function SetAmenitiesPropertyInCity(playerID, cityID)
    local pCity = CityManager.GetCity(playerID, cityID)
    if pCity == nil then return end
    local Amenities = GetCitySurplusAmenities(pCity)
    local pPlot = Map.GetPlot(pCity:GetX(), pCity:GetY())

    -- 桃金娘：每 2 宜居度 +10% 产出，上限 8 位
    if IsLeader(playerID, 'LEADER_MYRTLE') then
        if Amenities < 0 then Amenities = 0 end
        local yieldbonus = math.floor(Amenities / 2)
        local yieldbonus2 = NumToBinary(yieldbonus, 8)
        for i = 1, 8 do
            pPlot:SetProperty("SIQI_MYRTLE_CITY_PROPERTY_" .. NumberTable[i], yieldbonus2[i])
        end
    end

    -- 苏苏洛：补全宜居度到 6，然后修正（多退少补），上限 5 位
    if IsLeader(playerID, 'LEADER_SUSSURRO') then
        local Happyiness = 0
        for i = 1, 5 do
            local num = NumberTable[i]
            Happyiness = Happyiness + (pPlot:GetProperty("SIQI_SUSSURRO_HAPPYINESS_" .. num) or 0) * num
        end
        if Amenities < 6 then
            Happyiness = Happyiness + (6 - Amenities)
        elseif Amenities > 6 and Happyiness > 0 then
            Happyiness = Happyiness - (Amenities - 6)
        end
        if Happyiness < 0 then Happyiness = 0 end
        local HappyinessTable = NumToBinary(Happyiness, 5)
        for i = 1, 5 do
            pPlot:SetProperty("SIQI_SUSSURRO_HAPPYINESS_" .. NumberTable[i], HappyinessTable[i])
        end
    end
end
```

### 星辉系统：消耗星辉 → 触发鼓舞/尤里卡

每消耗 1 星辉累加计数器，满 5 触发一次随机鼓舞/尤里卡（AttachModifierByID），计数器清零。星辉(XingHui)→鼓舞，星术(XingShu)→尤里卡，两者对称。

```lua
function ChangeAmount_XingHui(playerID, amount)
    local pPlayer = Players[playerID]
    local key = "Siqi_XingHui"
    local cur = pPlayer:GetProperty(key) or 0
    pPlayer:SetProperty(key, cur + amount)
    if amount < 0 then
        local now = (pPlayer:GetProperty(key .. "_now") or 0) + math.abs(amount)
        if now >= 5 then
            pPlayer:AttachModifierByID("MODIFIER_SIQI_ASTESIA_GRANT_RANDOM_CIVIC_BOOST_GOODY_HUT")
            pPlayer:SetProperty('PROPERTY_SIQI_ASTESIA_GRANT_RANDOM_CIVIC_BOOST_GOODY_HUT_USED', true)
            now = 0
        end
        pPlayer:SetProperty(key .. "_now", now)
    end
    BroadcastRefresh()
end

-- ChangeAmount_XingShu 同理：key="Siqi_XingShu"，满5触发尤里卡 Modifier
```

### 摩拉产出系统核心：UI 计算 → GP 写 Property

UI 端读取各城市 From/Req/To 规则表 → 计算每回合摩拉 → 通过 EXECUTE_SCRIPT 异步发给 GP → GP 端写 Player Property(MORA) + 广播刷新。

```lua
-- GP 端接收 UI 计算结果
function GP_OnApplyTurnMora(playerID, params)
    if not params then return end
    local amount = params.Amount or 0
    if amount <= 0 then return end
    local pPlayer = Players[playerID]
    if not pPlayer then return end
    local current = pPlayer:GetProperty('MORA') or 0
    pPlayer:SetProperty('MORA', current + amount)
    pPlayer:SetProperty('MORA_PER_TURN', amount)
    BroadcastRefresh()
end

-- 统一余额变更入口（所有摩拉增加/消耗必须走此函数）
function Mora_ChangeBalance(playerID, amount, reason)
    local pPlayer = Players[playerID]
    if not pPlayer then return end
    if amount == 0 then return end
    local current = pPlayer:GetProperty("MORA") or 0
    local newBalance = current + amount
    pPlayer:SetProperty("MORA", newBalance)
    BroadcastRefresh()
end

```

### BroadcastRefresh — 广播刷新（GP → UI 通知）

toggle Game Property 触发跨上下文 Events.GamePropertyChanged。GP 修改数据后调用，UI 监听后自行读 Property 刷新。

```lua
function BroadcastRefresh()
    if Game:GetProperty("SIQI32_CORE_REFRESH") then
        Game:SetProperty("SIQI32_CORE_REFRESH", false)
    end
    if not Game:GetProperty("SIQI32_CORE_REFRESH") then
        Game:SetProperty("SIQI32_CORE_REFRESH", true)
    end
end
```
UI 端监听 `Events.GamePropertyChanged`，自行读 Property 刷新面板。见 `code-style.md` 第七章。

---

