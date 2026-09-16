# lua-workshop-combat-morale -- 单位士气属性系统

从工坊 Mod **AP Morale System** (3536386676) 提炼。核心模式：基于 `PRO_` 自定义属性的单位士气值系统，士气影响战斗力；通过战斗事件（优势进攻/击杀/战损）改变士气，每回合向 0 自然趋近；城市围城机制用 bitflag 编码累积围城回合数并授予战斗力加成。

---

## 快速索引

| 模式 | 核心 API / 技术 | 适用场景 |
|------|----------------|---------|
| 单位/地块属性 | `pUnit:SetProperty('PRO_XXX', val)` / `GetProperty` | 自定义状态存储 |
| 属性→战斗力映射 | `MODIFIER_UNIT_ADJUST_COMBAT_STRENGTH` + Key=`PRO_XXX` | 属性值转战斗修正 |
| 属性→属性调整 | `MODIFIER_UNIT_ADJUST_PROPERTY` | Modifier 修改属性值 |
| bitflag 编码 | `Value % 2`, `(Value/2) % 2` 等 | 紧凑存储多级状态 |
| 围城回合累积 | `Events.CitySiegeStatusChanged` + `TurnEnd` | 围城效果随时间增强 |
| 战斗伤害比较 | `CombatResultParameters.DAMAGE_TO` | 判断优势/劣势 |
| 战争开关节制 | `DiplomacyDeclareWar / MakePeace` 监听 | 和平时期关闭系统 |
| 自定义配置表 | `CREATE TABLE + GameInfo.XXX` | 运行时读取 Mod 参数 |
| 玩家文明类型 | `PlayerConfigurations[id]:GetCivilizationTypeName()` | 判断蛮族/自由城邦 |

---

## 架构概览

```
APMS_GP.lua           → 游戏逻辑主控（事件注册、属性读写、初始化）
APMS_Modifier.sql     → 能力/Modifier/Requirement 定义
Config.sql            → 游戏参数注册（轻量化模式开关）
DATA/TABLE_APMS_DATA.sql → 自定义配置表结构
DATA/APMS_DATA_INSERT.sql → 配置表数据（各项参数默认值）
DATA/APMS_DATA_MANAGE.sql → 围城战斗力倍率 = 配置值 × 围城属性值
```

**核心数据流**：
```
战斗事件(Combat/UnitKilledInCombat) → 计算士气变化 → SetProperty('PRO_APMS', newValue)
Property 值变化 → MODIFIER_UNIT_ADJUST_COMBAT_STRENGTH(Key='PRO_APMS') → 实时战斗力修正
每回合 → 士气向 0 趋近 → SetProperty
```

---

## XML 配合

本系统无独立 UI 面板。士气值通过 `PRO_` Property + `MODIFIER_UNIT_ADJUST_COMBAT_STRENGTH` 间接影响战斗力，围城系统通过 `REQUIREMENT_PLOT_PROPERTY_MATCHES` 触发。配置参数存储在 `APMS_DATA` 自定义表中，通过 Lua `GameInfo.APMS_DATA` 读取，无需 XML 控件。

---

## 一、单位士气属性系统

### 1.1 属性读写

```lua
-- 设置士气值（带上下限钳制）
function APMS_PropertySet(PlayerID, UnitID, Value)
    if Value > Max_Morale then
        print("Morale Full")
    elseif Value < -Max_Morale then
        print("Morale Lowest")
    else
        local pUnit = UnitManager.GetUnit(PlayerID, UnitID)
        pUnit:SetProperty('PRO_APMS', Value)
    end
end

-- 读取士气值
local Former_Pro = pUnit:GetProperty('PRO_APMS') or 0
```

**`PRO_` 前缀约定**：自定义属性必须以 `PRO_` 开头，这样 `MODIFIER_UNIT_ADJUST_COMBAT_STRENGTH` 的 `Key` 参数才能识别。

### 1.2 战斗力映射（SQL 侧）

```sql
-- 能力定义
INSERT INTO Types (Type, Kind) VALUES
('ABILITY_APMS_PROPERTY_STRENTH', 'KIND_ABILITY');

INSERT INTO UnitAbilities (UnitAbilityType, Name, Inactive) VALUES
('ABILITY_APMS_PROPERTY_STRENTH', 'LOC_...', 0);

INSERT INTO TypeTags (Type, Tag) VALUES
('ABILITY_APMS_PROPERTY_STRENTH', 'CLASS_ALL_COMBAT_UNITS');

INSERT INTO UnitAbilityModifiers (UnitAbilityType, ModifierId) VALUES
('ABILITY_APMS_PROPERTY_STRENTH', 'MODIFIER_APMS_PROPERTY_STRENTH');

-- 核心 Modifier：PRO_APMS 属性值 → 战斗力加成
INSERT INTO Modifiers (ModifierId, ModifierType) VALUES
('MODIFIER_APMS_PROPERTY_STRENTH', 'MODIFIER_UNIT_ADJUST_COMBAT_STRENGTH');

INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
('MODIFIER_APMS_PROPERTY_STRENTH', 'Key', 'PRO_APMS');
```

**`MODIFIER_UNIT_ADJUST_COMBAT_STRENGTH` + `Key='PRO_APMS'` 的含义**：该 Modifier 将 `PRO_APMS` 属性值直接作为战斗力修正。例如：
- `PRO_APMS = 5` → 单位 +5 战斗力
- `PRO_APMS = -3` → 单位 -3 战斗力

属性值变化时，战斗力自动实时更新，无需额外 Lua 处理。

---

## 二、士气变化源

### 2.1 优势进攻（造成伤害更多的一方 +1）

```lua
function APMS_GP_OnCombat(m_combatResults)
    if APMS_Switch == 1 then
        if m_combatResults == nil then return end

        local attacker = m_combatResults[CombatResultParameters.ATTACKER]
        local defender = m_combatResults[CombatResultParameters.DEFENDER]

        -- 攻击方造成伤害 > 防御方造成伤害（且攻击方造成伤害不为 0）
        if (attacker[CombatResultParameters.DAMAGE_TO]
            < defender[CombatResultParameters.DAMAGE_TO])
        and (attacker[CombatResultParameters.DAMAGE_TO] ~= 0) then
            local info = attacker[CombatResultParameters.ID]
            local pUnit = UnitManager.GetUnit(info.player, info.id)
            APMS_PropertySet(info.player, info.id,
                (pUnit:GetProperty('PRO_APMS') or 0) + Gain_Morale_From_Advantage_Attack)
        end

        -- 记录战斗坐标，供 UnitKilledInCombat 使用
        CURRENT_COMBAT_X = m_combatResults[CombatResultParameters.LOCATION].x
        CURRENT_COMBAT_Y = m_combatResults[CombatResultParameters.LOCATION].y
    end
end
Events.Combat.Add(APMS_GP_OnCombat)
```

**注意 `DAMAGE_TO` 的比较方向**：这里 `attacker[DAMAGE_TO] < defender[DAMAGE_TO]` 看似反直觉（攻击方造成伤害小于防御方），实际上 `DAMAGE_TO` 是**受到的伤害**，即：
- `attacker[DAMAGE_TO]` = 攻击方受到的伤害（防御方造成的伤害）
- 所以 `attacker[DAMAGE_TO] < defender[DAMAGE_TO]` = 攻击方受伤更少 = 攻击方优势

### 2.2 击杀单位（周围 2 格士气变化）

```lua
function APMS_GP_OnUnitKilledInCombat(killedPlayerID, killedUnitID, playerID, unitID)
    if APMS_Switch == 1 then
        local pUnit = UnitManager.GetUnit(playerID, unitID)
        if pUnit ~= nil then
            -- 以上次战斗坐标为中心，扫描 2 格范围
            local pPlots = Map.GetNeighborPlots(CURRENT_COMBAT_X, CURRENT_COMBAT_Y, 2)
            for _, pPlot in ipairs(pPlots) do
                local pUnits = Units.GetUnitsInPlot(pPlot)
                for _, iUnit in ipairs(pUnits) do
                    local iPlayerId = iUnit:GetOwner()
                    if iPlayerId == killedPlayerID then
                        -- 阵亡方周围的友军 -1 士气
                        local Former_Pro = iUnit:GetProperty('PRO_APMS') or 0
                        APMS_PropertySet(iPlayerId, iUnit:GetID(),
                            Former_Pro - Gain_Morale_From_Unit_Killed)
                    elseif iPlayerId == playerID then
                        -- 击杀方周围的友军 +1 士气
                        local Former_Pro = iUnit:GetProperty('PRO_APMS') or 0
                        APMS_PropertySet(iPlayerId, iUnit:GetID(),
                            Former_Pro + Gain_Morale_From_Unit_Killed)
                    end
                end
            end
        end
    end
end
Events.UnitKilledInCombat.Add(APMS_GP_OnUnitKilledInCombat)
```

**设计要点**：
- 使用 `Map.GetNeighborPlots(x, y, 2)` 而非 BFS，直接获取 2 格内的所有地块
- 使用 `Combat` 事件中记录的 `CURRENT_COMBAT_X/Y` 而非死亡单位坐标（死亡后坐标可能已无效）
- 影响范围：2 格内的所有友方/敌方单位

### 2.3 每回合士气自然趋近 0

```lua
function APMS_GP_OnGameTurnStarted(playerID)
    if APMS_Switch == 1 then
        local currentTurn = Game.GetCurrentGameTurn()
        -- 每 N 回合执行一次（N = Turn_Multiple_For_Ajust_Morale，默认 2）
        if currentTurn % Turn_Multiple_For_Ajust_Morale == 1 then
            local players = Game.GetPlayers{Alive = true}
            for _, player in ipairs(players) do
                for _, pUnit in player:GetUnits():Members() do
                    local Former_Pro = pUnit:GetProperty('PRO_APMS') or 0
                    if Former_Pro > 0 then
                        APMS_PropertySet(pUnit:GetOwner(), pUnit:GetID(), Former_Pro - 1)
                    elseif Former_Pro < 0 then
                        APMS_PropertySet(pUnit:GetOwner(), pUnit:GetID(), Former_Pro + 1)
                    end
                end
            end
        end
    end
end
GameEvents.OnGameTurnStarted.Add(APMS_GP_OnGameTurnStarted)
```

**设计考量**：
- 使用 `% Turn_Multiple_For_Ajust_Morale` 控制衰减频率，避免每回合都遍历所有单位
- 双向趋近：正值 -1，负值 +1，最终回 0
- 遍历全局所有玩家的所有单位（O(N) 操作，使用取模降低执行频率）

---

## 三、城市围城系统

### 3.1 bitflag 编码设计

围城回合数存储在**地块属性** `PRO_APMS_CITY` 中，同时用 bitflag 拆分到 5 个子属性中以便 SQL Requirement 读取：

```lua
function APMS_SIEGE_PropertySet(iX, iY, Value)
    local pPlot = Map.GetPlot(iX, iY)
    pPlot:SetProperty('PRO_APMS_CITY', Value)        -- 总值（用于显示/调试）
    pPlot:SetProperty('PRO_APMS_CITY_1', Value % 2)  -- bit 0 (围城 >=1 回合)
    pPlot:SetProperty('PRO_APMS_CITY_2', (math.floor(Value / 2)) % 2)   -- bit 1 (>=2 回合)
    pPlot:SetProperty('PRO_APMS_CITY_4', (math.floor(Value / 4)) % 2)   -- bit 2 (>=4 回合)
    pPlot:SetProperty('PRO_APMS_CITY_8', (math.floor(Value / 8)) % 2)   -- bit 3 (>=8 回合)
    pPlot:SetProperty('PRO_APMS_CITY_16', (math.floor(Value / 16)) % 2) -- bit 4 (>=16 回合)
end
```

**编码逻辑**：如果围城 5 回合，则 `Value=5`，bitflag 为：
- `PRO_APMS_CITY_1 = 1` (5 >= 1)
- `PRO_APMS_CITY_2 = 1` (5 >= 2)
- `PRO_APMS_CITY_4 = 1` (5 >= 4)
- `PRO_APMS_CITY_8 = 0` (5 < 8)
- `PRO_APMS_CITY_16 = 0` (5 < 16)

SQL 侧用 `REQUIREMENT_PLOT_PROPERTY_MATCHES` 检查每个 bit 属性是否 >=1，从而决定授予哪一级围城战斗力加成。

### 3.2 围城状态跟踪

```lua
local Sieging_City_List = {}  -- 本回合被围城的城市 {playerID, cityID}
local Sieged_City_List = {}   -- 上回合被围城的城市（用于对比）

function APMS_GP_OnCitySiegeStatusChanged(playerID, cityID, bIsBesieged)
    local pPlot = Map.GetPlot(pCity:GetX(), pCity:GetY())
    local Former_Pro_City = pPlot:GetProperty('PRO_APMS_CITY') or 0

    if bIsBesieged then
        -- 首次被围城时初始化属性
        if Former_Pro_City < 1 then
            APMS_SIEGE_PropertySet(pCity:GetX(), pCity:GetY(), 1)
        end
        -- 去重后记录到围城列表
        for i = #Sieging_City_List, 1, -1 do
            local v = Sieging_City_List[i]
            if v[1] == playerID and v[2] == cityID then
                table.remove(Sieging_City_List, i)
            end
        end
        table.insert(Sieging_City_List, {playerID, cityID})
    elseif bIsBesieged == false then
        -- 围城解除：从列表中移除
        for i = #Sieging_City_List, 1, -1 do
            local v = Sieging_City_List[i]
            if v[1] == playerID and v[2] == cityID then
                table.remove(Sieging_City_List, i)
            end
        end
    end
end
Events.CitySiegeStatusChanged.Add(APMS_GP_OnCitySiegeStatusChanged)
```

### 3.3 回合末围城值递增和清除

```lua
function APMS_GP_OnTurnEnd()
    local Sieging_Index = {}

    -- 1. 遍历本回合围城城市：围城值 +1
    for i, v in ipairs(Sieging_City_List) do
        local playerID, cityID = v[1], v[2]
        local key = playerID .. ":" .. cityID
        Sieging_Index[key] = true

        local pCity = CityManager.GetCity(playerID, cityID)
        if pCity ~= nil then
            local pPlot = Map.GetPlot(pCity:GetX(), pCity:GetY())
            local Former_Pro_City = pPlot:GetProperty('PRO_APMS_CITY') or 0
            APMS_SIEGE_PropertySet(pCity:GetX(), pCity:GetY(), Former_Pro_City + 1)
        end
    end

    -- 2. 清理：上回合围城但本回合不在围城列表中的城市，围城值归零
    for i = #Sieged_City_List, 1, -1 do
        local v = Sieged_City_List[i]
        local playerID, cityID = v[1], v[2]
        local key = playerID .. ":" .. cityID

        if not Sieging_Index[key] then
            local pCity = CityManager.GetCity(playerID, cityID)
            if pCity ~= nil then
                local pPlot = Map.GetPlot(pCity:GetX(), pCity:GetY())
                APMS_SIEGE_PropertySet(pCity:GetX(), pCity:GetY(), 0)
            end
        end
    end

    -- 3. 用本回合列表覆盖上回合列表
    Sieged_City_List = {}
    for i, v in ipairs(Sieging_City_List) do
        table.insert(Sieged_City_List, v)
    end
end
Events.TurnEnd.Add(APMS_GP_OnTurnEnd)
```

**双列表对比法**：`Sieging_City_List`（本回合）+ `Sieged_City_List`（上回合），回合末对比两者，确定哪些城市围城状态变化，防止围城一回合就获得高额加成。

### 3.4 围城 Modifier 链（SQL 侧）

```sql
-- 城市中心附加围城 Modifier
INSERT INTO DistrictModifiers (DistrictType, ModifierId) VALUES
('DISTRICT_CITY_CENTER', 'MODIFIER_APMS_SIEGE1_ATTACH'),
-- ... 共 5 级（SIEGE1/2/4/8/16）× 2（陆地/海洋）= 10 个 Modifier

-- 围城 Modifier 结构（以 SIEGE1 为例）
-- 层 1: ATTACH — 条件满足时挂载子 Modifier
INSERT INTO Modifiers (ModifierId, ModifierType, OwnerRequirementSetId, SubjectRequirementSetId) VALUES
('MODIFIER_APMS_SIEGE1_ATTACH', 'MODIFIER_ALL_UNITS_ATTACH_MODIFIER',
 'APMS_PRO_SIEGE_1',           -- Owner: 城市中心地块属性 PRO_APMS_CITY_1 >= 1?
 'APMS_AOE_LAND_3_REQUIREMENTS'); -- Subject: 3 格内陆上敌方单位？

INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
('MODIFIER_APMS_SIEGE1_ATTACH', 'ModifierId', 'MODIFIER_APMS_SIEGE1');

-- 层 2: 属性调整 — 给符合条件的敌方单位设置 PRO_APMS_SIEGE_STRENGTH
INSERT INTO Modifiers (ModifierId, ModifierType) VALUES
('MODIFIER_APMS_SIEGE1', 'MODIFIER_UNIT_ADJUST_PROPERTY');

INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
('MODIFIER_APMS_SIEGE1', 'Key', 'PRO_APMS_SIEGE_STRENGTH'),
('MODIFIER_APMS_SIEGE1', 'Amount', '1');  -- Value = 1 * Gain_Strength_Per_Siege_Turn

-- 层 3: 属性→战斗力 — PRO_APMS_SIEGE_STRENGTH 属性转战斗力
INSERT INTO UnitAbilityModifiers (UnitAbilityType, ModifierId) VALUES
('ABILITY_APMS_SIEGE_PROPERTY_STRENTH', 'MODIFIER_APMS_SIEGE_PROPERTY_STRENTH');

INSERT INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId) VALUES
('MODIFIER_APMS_SIEGE_PROPERTY_STRENTH', 'MODIFIER_UNIT_ADJUST_COMBAT_STRENGTH',
  NULL, 'APMS_PRO_SIEGE_CITY');

INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
('MODIFIER_APMS_SIEGE_PROPERTY_STRENTH', 'Key', 'PRO_APMS_SIEGE_STRENGTH');
```

**三级链路总结**：
```
ATTACH Modifier（条件检查）
 → MODIFIER_UNIT_ADJUST_PROPERTY（给敌方单位加属性）
   → MODIFIER_UNIT_ADJUST_COMBAT_STRENGTH（属性转战斗力）
```

### 3.5 需求条件

```sql
-- 地块属性匹配：检查对应 bitflag 是否 >=1
INSERT INTO Requirements (RequirementId, RequirementType) VALUES
('REQUIRES_APMS_PRO_SIEGE_1', 'REQUIREMENT_PLOT_PROPERTY_MATCHES');
INSERT INTO RequirementArguments (RequirementId, Name, Value) VALUES
('REQUIRES_APMS_PRO_SIEGE_1', 'PropertyName', 'PRO_APMS_CITY_1'),
('REQUIRES_APMS_PRO_SIEGE_1', 'PropertyMinimum', '1');

-- 3 格内有敌方单位
INSERT INTO Requirements (RequirementId, RequirementType) VALUES
('APMS_AOE_REQUIRES_OWNER_ADJACENCY_3', 'REQUIREMENT_PLOT_ADJACENT_TO_OWNER_AT_WAR');
INSERT INTO RequirementArguments (RequirementId, Name, Value) VALUES
('APMS_AOE_REQUIRES_OWNER_ADJACENCY_3', 'MaxDistance', '3'),
('APMS_AOE_REQUIRES_OWNER_ADJACENCY_3', 'MinDistance', '0');
```

---

## 四、战争状态开关机制

该 Mod 提供"轻量化模式"：仅在战争期间启用士气系统，和平时期关闭。

```lua
local APMS_Switch = 1  -- 默认开启

-- 宣战时开启
function APMS_Switch_OnDiplomacyDeclareWar(firstPlayerID, secondPlayerID)
    local LocalPlayerID = Game.GetLocalPlayer()
    if (firstPlayerID == LocalPlayerID) or (secondPlayerID == LocalPlayerID) then
        APMS_Switch = 1
    end
end

-- 和平时检查是否还有任何战争
function APMS_Switch_OnDiplomacyMakePeace(firstPlayerID, secondPlayerID)
    local LocalPlayerID = Game.GetLocalPlayer()
    if (firstPlayerID == LocalPlayerID) or (secondPlayerID == LocalPlayerID) then
        local players = Game.GetPlayers{Alive = true}
        APMS_Switch = 0
        for _, player in ipairs(players) do
            if (player:GetID() < 62)  -- 排除自由城邦/蛮族
            and player:GetDiplomacy():IsAtWarWith(LocalPlayerID) then
                APMS_Switch = 1
                break
            end
        end
        -- 所有战争结束：清除所有单位的士气值
        if APMS_Switch == 0 then
            for _, player in ipairs(players) do
                for _, pUnit in player:GetUnits():Members() do
                    APMS_PropertySet(pUnit:GetOwner(), pUnit:GetID(), 0)
                end
            end
        end
    end
end

Events.DiplomacyDeclareWar.Add(APMS_Switch_OnDiplomacyDeclareWar)
Events.DiplomacyMakePeace.Add(APMS_Switch_OnDiplomacyMakePeace)
```

**`player:GetID() < 62` 的作用**：区分主要文明玩家和自由城邦/蛮族。玩家 ID 0-61 是主要文明，>=62 的 ID 分配给自由城邦等特殊实体。

---

## 五、自定义配置表

```sql
-- 表结构
CREATE TABLE APMS_DATA (
    Name  TEXT NOT NULL,
    Value INTEGER,
    PRIMARY KEY (Name)
);

-- 配置数据
INSERT INTO APMS_DATA (Name, Value) VALUES
('APMS_Lite_Mode', 0),                    -- 轻量化模式（0=始终运行，1=仅战时）
('Gain_Morale_From_Advantage_Attack', 1), -- 优势进攻士气变化量
('Gain_Morale_From_Unit_Killed', 1),      -- 击杀单位士气变化量
('Turn_Multiple_For_Ajust_Morale', 2),    -- 士气趋近频率（每 N 回合）
('Gain_Strength_Per_Siege_Turn', 2),      -- 围城战斗力倍率
('Max_Morale', 10);                       -- 士气最大绝对值
```

**Lua 侧读取配置**：
```lua
function Initialize()
    APMS_Lite_Mode = GameInfo.APMS_DATA["APMS_Lite_Mode"].Value or 0
    Gain_Morale_From_Advantage_Attack = GameInfo.APMS_DATA["Gain_Morale_From_Advantage_Attack"].Value
    Gain_Morale_From_Unit_Killed      = GameInfo.APMS_DATA["Gain_Morale_From_Unit_Killed"].Value
    Turn_Multiple_For_Ajust_Morale    = GameInfo.APMS_DATA["Turn_Multiple_For_Ajust_Morale"].Value
    Max_Morale                        = GameInfo.APMS_DATA["Max_Morale"].Value
end
```

**注意**：`GameInfo.APMS_DATA["key"].Value` 只在自定义表有主键时才有效。Lua 中通过 `GameInfo.<表名>()` 遍历，`GameInfo.<表名>["key"]` 按主键索引。

---

## 六、完整使用模板

### 最小士气系统

```lua
-- Morale_GP.lua
local MAX_MORALE = 10

function MoraleSet(playerID, unitID, value)
    if math.abs(value) > MAX_MORALE then return end
    local unit = UnitManager.GetUnit(playerID, unitID)
    if unit then unit:SetProperty('PRO_MORALE', value) end
end

-- 击杀 +1
function OnUnitKilled(killedPID, killedUID, killerPID, killerUID)
    local unit = UnitManager.GetUnit(killerPID, killerUID)
    if unit then
        MoraleSet(killerPID, killerUID, (unit:GetProperty('PRO_MORALE') or 0) + 1)
    end
end
Events.UnitKilledInCombat.Add(OnUnitKilled)

-- 每回合衰减
function OnTurnStart()
    local players = Game.GetPlayers{Alive = true}
    for _, player in ipairs(players) do
        for _, unit in player:GetUnits():Members() do
            local morale = unit:GetProperty('PRO_MORALE') or 0
            if morale > 0 then
                MoraleSet(unit:GetOwner(), unit:GetID(), morale - 1)
            elseif morale < 0 then
                MoraleSet(unit:GetOwner(), unit:GetID(), morale + 1)
            end
        end
    end
end
Events.TurnBegin.Add(OnTurnStart)
```

```sql
-- Morale_Modifier.sql
INSERT INTO Types (Type, Kind) VALUES
('ABILITY_MORALE_COMBAT', 'KIND_ABILITY');

INSERT INTO TypeTags (Type, Tag) VALUES
('ABILITY_MORALE_COMBAT', 'CLASS_ALL_COMBAT_UNITS');

INSERT INTO UnitAbilities (UnitAbilityType, Name, Inactive) VALUES
('ABILITY_MORALE_COMBAT', 'LOC_ABILITY_MORALE_NAME', 0);

INSERT INTO UnitAbilityModifiers (UnitAbilityType, ModifierId) VALUES
('ABILITY_MORALE_COMBAT', 'MODIFIER_MORALE_STRENGTH');

INSERT INTO Modifiers (ModifierId, ModifierType) VALUES
('MODIFIER_MORALE_STRENGTH', 'MODIFIER_UNIT_ADJUST_COMBAT_STRENGTH');

INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
('MODIFIER_MORALE_STRENGTH', 'Key', 'PRO_MORALE');
```

---

## 七、注意事项

1. **属性持久化**：`SetProperty` 设置的属性会随存档保存，但需要在 `LoadGameViewStateDone` 事件中重新初始化围城列表（用地块属性反查哪些城市围城值 > 0）。

2. **`REQUIREMENT_PLOT_PROPERTY_MATCHES`**：该 RequirementType 检查的是 Subject 的地块属性（而非 Owner）。在围城场景中，Subject 是敌方单位所在的地块，因此需要先在城市中心地块上设置属性，再由 DistrictModifier 链条传播。

3. **bitflag 的精度限制**：`PRO_APMS_CITY_16` 及以上 bit 的值为 0 或 1，意味着围城 16 回合和围城 64 回合的战斗力加成相同。如需更细粒度，需增加更多 bitflag 级别。

4. **性能**：每回合遍历所有玩家的所有单位（士气趋近）可能很昂贵。使用 `Turn_Multiple_For_Ajust_Morale` 控制频率是关键优化。

5. **战争开关**：轻量化模式下和平时期清除士气会丢失所有单位的状态。如果希望保留士气值但暂停效果，可以只暂停事件处理而不清除属性值。
