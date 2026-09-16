# 朝贡/附庸体系 (Custom Alliance & Vassal System)

> 来源：ChaoGong System (3475587881)
> 完整独立系统，包含自定义同盟类型、附庸机制、UI弹窗、贡金收集

## 概述

在标准游戏同盟系统基础上扩展两种新同盟类型：**朝贡同盟 (CHAOGONG)** 和 **附庸同盟 (VASSAL)**。附庸通过征服城市后释放实现；朝贡通过外交弹窗支付金币建立。附庸国每回合向宗主国缴纳贡金（其金币收入的50%），贡金通过二进制折叠系统转化为首都地块属性，触发多档金币加成。

## 核心架构

```
┌───────────────┐     ┌──────────────────┐     ┌─────────────┐
│ 弹窗UI        │────>│ GameEvents Call  │────>│ GP 处理     │
│ (Popup_Panel) │     │ (CHAOGONG_First  │     │ (Chaogong_GP│
│               │     │  /Second/Third   │     │  .lua)      │
│               │     │  Button.Call)    │     │             │
└───────────────┘     └──────────────────┘     └──────┬──────┘
                                                      │
                                    ┌─────────────────▼──────┐
                                    │ 二进制折叠写入         │
                                    │ Property → REQ → Mod   │
                                    │ (首都地块属性)         │
                                    └────────────────────────┘
```

## XML 配合

### CHAOGONG_Popup_Panel.xml — 朝贡/附庸外交弹窗

`UI/CHAOGONG_Popup_Panel.xml` 定义了完整的外交弹窗界面：

```xml
<Context>
    <Container ID="MainContainer" Anchor="C,C" Size="500,300">
        <Grid ID="RazeCityWindow" Size="500,auto" Style="WindowFrameTitle">
            <Label ID="PanelHeader" Style="WindowHeader"
                   String="{LOC_CONFIRM_CHOICE:upper}"/>
            <Stack ID="PopupStack" Size="400,100" StackGrowth="Bottom"
                   StackPadding="10">
                <!-- 城市名称、人口、外交状态、折扣信息 -->
                <Label ID="CityHeader"/><Label ID="CityName"/>
                <Label ID="CityPopulation"/><Label ID="NumPeople"/>
                <Label ID="DiplomaticState"/><Label ID="NumDiplomaticState"/>
                <Label ID="GIFT_CUTOFF"/><Label ID="CUTOFF_PERCENT"/>
                <!-- 三个操作按钮 -->
                <GridButton ID="FirstButton" Size="200,41"  -- 朝贡
                            String="LOC_CHAOGONG_FIRSTBUTTON_TEXT"/>
                <GridButton ID="SecondButton" Size="200,41" -- 赠送国礼
                            String="LOC_CHAOGONG_SECONDBUTTON_TEXT"/>
                <GridButton ID="ThirdButton" Size="200,41"  -- 雇佣单位
                            String="LOC_CHAOGONG_THIRDBUTTON_TEXT"/>
            </Stack>
        </Grid>
    </Container>
</Context>
```

弹窗在 Lua 端 `ON_CHAOGONG_Popup_ShowScreen()` 中填充数据：显示目标文明名称、金币收入、外交状态、朝贡费用（考虑折扣）、可雇佣的最强单位等。

### CHAOGONG_Unit_Panel.xml — 单位面板朝贡按钮

`UI/CHAOGONG_Unit_Panel.xml` 在军事单位面板挂入朝贡按钮：

```xml
<Context>
    <Grid ID="APCGUnitButtonGrid" Anchor="R,B" Size="auto,41"
          Texture="SelectionPanel_ActionGroupSlot" Alpha="0.75">
        <Button ID="APCGUnitButton" Size="44,53" Texture="UnitPanel_ActionButton"
                ToolTip="LOC_CHAOGONG_UNIT_BUTTON">
            <Image Icon="ICON_YIELD_GOLD_3" Size="38,38"/>
        </Button>
    </Grid>
</Context>
```

按钮显示条件：选中军事单位 + 目标地块属于其他文明领土 + 与目标文明满足朝贡条件。

### RazeCity.xml — 征服建附庸的释放按钮

替换原版摧毁城市面板，添加"释放附庸"选项按钮。

### Localization.xml — 多语言文本

---

## SQL 核心定义

### 1. 自定义同盟类型

```sql
INSERT INTO Types (Type, Kind) VALUES
('DIPLOACTION_ALLIANCE_VASSAL', 'KIND_DIPLOMATIC_ACTION'),
('ALLIANCE_VASSAL', 'KIND_DIPLOMACY_ALLIANCE'),
('DIPLOACTION_ALLIANCE_CHAOGONG', 'KIND_DIPLOMATIC_ACTION'),
('ALLIANCE_CHAOGONG', 'KIND_DIPLOMACY_ALLIANCE');

INSERT INTO Alliances (AllianceType, Name, Description) VALUES
('ALLIANCE_VASSAL', 'LOC_ALLIANCE_VASSAL', '...'),
('ALLIANCE_CHAOGONG', 'LOC_ALLIANCE_CHAOGONG', '...');

-- 外交行动定义
INSERT INTO DiplomaticActions
(DiplomaticActionType, InitiatorPrereqCivic, TargetPrereqCivic, UIGroup, Cost, Duration)
VALUES
('DIPLOACTION_ALLIANCE_CHAOGONG', 'CIVIC_CIVIL_SERVICE', 'CIVIC_CIVIL_SERVICE',
 'ALLIANCES', '0', '30');

INSERT INTO DiplomaticActions_XP1 (DiplomaticActionType, AllianceType) VALUES
('DIPLOACTION_ALLIANCE_CHAOGONG', 'ALLIANCE_CHAOGONG');

-- 允许在结盟状态和宣布友好状态下使用
INSERT INTO DiplomaticStateActions
(StateType, DiplomaticActionType, AiAllowed, Worth, Cost, TransitionToState, TeamOnly)
VALUES
('DIPLO_STATE_ALLIED', 'DIPLOACTION_ALLIANCE_CHAOGONG', 0, 25, 50, NULL, 1),
('DIPLO_STATE_DECLARED_FRIEND', 'DIPLOACTION_ALLIANCE_CHAOGONG', 0, 25, 50, 'DIPLO_STATE_ALLIED', 0);
```

### 2. 同盟加成效果

```sql
-- 自定义 DynamicModifier: 同盟城市产出入系数
INSERT INTO DynamicModifiers (ModifierType, CollectionType, EffectType) VALUES
('MODIFIER_APCG_ALLIANCE_CITIES_ADJUST_YIELD_MODIFIER',
 'COLLECTION_ALLIANCE_CITIES', 'EFFECT_ADJUST_CITY_YIELD_MODIFIER');

-- 附庸同盟等级效果
INSERT INTO AllianceEffects (LevelRequirement, AllianceType, ModifierID) VALUES
('1', 'ALLIANCE_VASSAL', 'ALLIANCE_ADD_GOLD_TO_ORIGIN_TRADE_ROUTE_VASSAL'),
('1', 'ALLIANCE_VASSAL', 'ALLIANCE_ADD_GOLD_TO_DESTINATION_TRADE_ROUTE'),
('2', 'ALLIANCE_VASSAL', 'ALLIANCE_ADJUST_COMBAT_STRENGTH'),
('3', 'ALLIANCE_VASSAL', 'ALLIANCE_SHARE_VISIBILITY'),
('3', 'ALLIANCE_VASSAL', 'ALLIANCE_FREE_UNIT_UPGRADE');

-- 朝贡同盟等级效果
INSERT INTO AllianceEffects (LevelRequirement, AllianceType, ModifierID) VALUES
('1', 'ALLIANCE_CHAOGONG', 'ALLIANCE_ADD_GOLD_TO_ORIGIN_TRADE_ROUTE'),
('2', 'ALLIANCE_CHAOGONG', 'ALLIANCE_APCG_TRADE_GOLD'),
('3', 'ALLIANCE_CHAOGONG', 'ALLIANCE_APCG_TRADE_TECH'),
('3', 'ALLIANCE_CHAOGONG', 'ALLIANCE_APCG_TRADE_CIV');
```

### 3. 同盟升级速度调整

```sql
-- 加快同盟升级速度（原版太慢）
UPDATE GlobalParameters SET Value = 240 WHERE Name = 'ALLIANCE_LEVEL_TWO_XP';
UPDATE GlobalParameters SET Value = 560 WHERE Name = 'ALLIANCE_LEVEL_THREE_XP';
UPDATE GlobalParameters SET Value = 4 WHERE Name = 'ALLIANCE_POINTS_FOR_TRADE';
```

### 4. 贡金二进制 Modifier（贸易路线容量）

见 `lua-workshop-binary-yield.md`，此处从略。

### 5. GameConfig 开关

```sql
INSERT INTO Parameters
(ParameterId, Name, Description, Domain, DefaultValue,
 ConfigurationGroup, ConfigurationId, NameArrayConfigurationId, GroupId, SortIndex)
VALUES
('PAR_AP_Chaogong_DIP_Adjust', 'LOC_PAR_AP_Chaogong_DIP_Adjust_Name',
 '...Description', 'bool', 1, 'Game', 'PAR_AP_Chaogong_DIP_Adjust',
 'GAMEMODES_ENABLED_NAMES', 'AdvancedOptions', 11);
```

## Lua 核心实现

### 一、附庸系统 (Chaogong_GP.lua)

#### 附庸列表管理

```lua
VASSAL_LIST = {}  -- 所有附庸国的 playerID 列表

-- 初始化：从所有存活玩家中读取 APCG_IS_VASSAL 属性
function APCG_INITIALIZE_GET_VASSAL_LIST(localPlayerID)
    local players = Game.GetPlayers{Alive = true}
    for _, player in ipairs(players) do
        if player:GetProperty("APCG_IS_VASSAL") == 1 then
            table.insert(VASSAL_LIST, player:GetID())
        end
    end
end
```

#### 征服建附庸

```lua
-- 注册事件：点击"释放附庸"按钮时触发
GameEvents.CHAOGONG_RAZE_Button_APCG_CIV.Add(function(CITY_PLOT, eOriginalOwner)
    local g_pSelectedCity = Cities.GetCityInPlot(CITY_PLOT)
    localPlayer:GetDiplomacy():MakePeaceWith(eOriginalOwner)
    localPlayer:GetDiplomacy():SetHasAllied(eOriginalOwner,
        GameInfo.Alliances['ALLIANCE_VASSAL'].Index)
    table.insert(VASSAL_LIST, eOriginalOwner)
    APCG_ALLIANCES_FIRST_REVEAL(eOriginalOwner)  -- 先暴露对方领土
    Players[eOriginalOwner]:SetProperty("APCG_IS_VASSAL", 1)
end)
```

#### 每回合贡金计算

```lua
function APCG_VASSAL_OnGameTurnStarted(playerID)
    VASSAL_GOLD = 0
    if #VASSAL_LIST > 0 then
        for i, Vassal_player in ipairs(VASSAL_LIST) do
            -- 获取附庸国每回合金币产量
            pIncome = math.ceil(Players[Vassal_player]:GetTreasury():GetGoldYield())
            VASSAL_GOLD = VASSAL_GOLD + pIncome * 0.5  -- 收取50%
        end
        local pCapitalCity = localPlayer:GetCities():GetCapitalCity()
        APCG_BINARY_VASSAL_GOLD(VASSAL_GOLD, pCapitalCity:GetX(), pCapitalCity:GetY())
    end
end
```

注意事项：使用 `GetGoldYield()` 而非 `GetGoldBalance()`，前者是收入值，后者是余额。贡金只收取收入的一半。

#### 同盟结束处理

```lua
function APCG_VASSAL_CHANGE(playerID, otherplayerID, AllianceType)
    if AllianceType == GameInfo.Alliances['ALLIANCE_VASSAL'].Index then
        -- 从附庸列表中移除双方
        for i, id in ipairs(VASSAL_LIST) do
            if id == playerID or id == otherplayerID then
                table.remove(VASSAL_LIST, i)
                break
            end
        end
        Players[playerID]:SetProperty("APCG_IS_VASSAL", 0)
        Players[otherplayerID]:SetProperty("APCG_IS_VASSAL", 0)
    end
end

Events.AllianceEnded.Add(APCG_VASSAL_CHANGE)
```

### 二、朝贡系统

#### 按钮1：建立朝贡（支付金币）

```lua
GameEvents.CHAOGONG_FirstButton.Add(function(object_civID, object_Cost)
    localPlayer:GetTreasury():ChangeGoldBalance(-object_Cost)
    Players[object_civID]:GetTreasury():ChangeGoldBalance(object_Cost)
    localPlayer:GetDiplomacy():SetHasAllied(object_civID,
        GameInfo.Alliances['ALLIANCE_CHAOGONG'].Index)
    APCG_ALLIANCES_FIRST_REVEAL(object_civID)
    -- 记录朝贡次数，用于后续递减折扣
    local Former_times = Players[object_civID]:GetProperty('APCG_CHAOGONG_TIMES') or 0
    Players[object_civID]:SetProperty("APCG_CHAOGONG_TIMES", Former_times + 1)
end)
```

#### 费用计算（UI端 - 按外交状态）

```lua
-- 友好/宣布友好/同盟：基础费 = 对方收入 × 5
-- 中立：基础费 = 对方收入 × 10
-- 不友好：基础费 = 对方收入 × 15
-- 谴责：基础费 = 对方收入 × 20

-- 折扣：每朝贡过一次，费用 × (2/3)^n
local APCG_CUTOFF = (2/3) ^ APCG_Former_times
pCost = math.ceil(pIncome * base_multiplier * APCG_CUTOFF)
```

#### 按钮2：赠送国礼

```lua
GameEvents.CHAOGONG_SecondButton.Add(function(object_civID, object_income)
    -- 玩家支付 对方收入 × 5 的金币
    localPlayer:GetTreasury():ChangeGoldBalance(-object_income * 5)
    Players[object_civID]:GetTreasury():ChangeGoldBalance(object_income * 5)

    if Players[object_civID]:IsMajor() then
        -- 给主要文明赠送：增加贸易路线容量
        TRADE_ROUTE_FROM_GIFT = (TRADE_ROUTE_FROM_GIFT or 0) + 1
        local pCapitalCity = localPlayer:GetCities():GetCapitalCity()
        local pPlot = Map.GetPlot(pCapitalCity:GetX(), pCapitalCity:GetY())
        pPlot:SetProperty("APCG_TRADE_ROUTE_FROM_GIFT", TRADE_ROUTE_FROM_GIFT)
        APCG_BINARY_TRFG(TRADE_ROUTE_FROM_GIFT, pCapitalCity:GetX(), pCapitalCity:GetY())
    else
        -- 给城邦赠送：免费使者
        localPlayer:GetInfluence():GiveFreeTokenToPlayer(object_civID)
    end

    -- 每个时代每国只能送一次
    local Former_times = Players[object_civID]:GetProperty('APCG_GIFT_PER_ERA') or 0
    Players[object_civID]:SetProperty("APCG_GIFT_PER_ERA", Former_times + 1)
end)
```

#### 按钮3：雇佣单位

```lua
GameEvents.CHAOGONG_ThirdButton.Add(function(object_civID, Hiring_Unit)
    local Hire_Cost = GameInfo.Units[Hiring_Unit].Cost * 4
    localPlayer:GetTreasury():ChangeGoldBalance(-Hire_Cost)
    Players[object_civID]:GetTreasury():ChangeGoldBalance(Hire_Cost)
    -- 在首都创建该单位
    local pCapitalCity = localPlayer:GetCities():GetCapitalCity()
    UnitManager.InitUnit(localPlayerID, Hiring_Unit, pCapitalCity:GetX(), pCapitalCity:GetY())

    local Former_times = Players[object_civID]:GetProperty('APCG_HIRE_PER_ERA') or 0
    Players[object_civID]:SetProperty("APCG_HIRE_PER_ERA", Former_times + 1)
end)
```

### 三、城邦击杀得使者 (Chaogong_set.lua)

```lua
function CHAOGONG_CS_UnitKilled(killedPlayerID, killedUnitID, playerID, unitID)
    local player_CS = Players[killedPlayerID]
    -- 被杀方是城邦
    if not player_CS:IsMajor() and (killedPlayerID ~= 62) and (killedPlayerID ~= 63) then
        local localPlayer = Players[Game.GetLocalPlayer()]
        if localPlayerID == playerID then
            -- 在城邦领土上击杀 → 获使者
            local pUnit = UnitManager.GetUnit(playerID, unitID)
            local pPlot = Map.GetPlot(pUnit:GetX(), pUnit:GetY())
            if pPlot:GetOwner() == killedPlayerID then
                localPlayer:GetInfluence():GiveFreeTokenToPlayer(killedPlayerID)
            end
        end
    end
end

Events.UnitKilledInCombat.Add(CHAOGONG_CS_UnitKilled)
```

### 四、时代刷新

```lua
Events.GameEraChanged.Add(function(previousEra, newEra)
    local players = Game.GetPlayers{Alive = true}
    for _, player in ipairs(players) do
        player:SetProperty("APCG_GIFT_PER_ERA", 0)  -- 赠送次数重置
        player:SetProperty("APCG_HIRE_PER_ERA", 0)  -- 雇佣次数重置
    end
end)
```

### 五、UI弹窗 (CHAOGONG_Popup_Panel.lua)

```lua
-- 弹窗展示目标文明信息
function ON_CHAOGONG_Popup_ShowScreen(pPlayerID, pAlly)
    -- 显示文明名称、金币收入、外交状态
    -- 计算朝贡费用（考虑外交状态和已有次数折扣）
    -- 按钮1 (朝贡)：建立同盟
    -- 按钮2 (送礼)：给金币+商品 → 贸易路线/使者
    -- 按钮3 (雇佣)：从朝贡国招募最强可造陆军单位
end

-- 按钮3 (雇佣单位) 自动选择朝贡国可生产的最强陆军
for row in GameInfo.Units() do
    if row.FormationClass == 'FORMATION_CLASS_LAND_COMBAT' then
        if CanProduce(row.UnitType, pSelectedCity) then
            -- 比较 Combat / RangedCombat / Bombard 取最强
        end
    end
end
```

## 关键 Property 列表

| Property Name | 存储位置 | 说明 |
|---|---|---|
| `APCG_IS_VASSAL` | 玩家 | 是否为附庸国 (1/0) |
| `APCG_CHAOGONG_TIMES` | 玩家(目标) | 已被朝贡次数(影响费用折扣) |
| `APCG_GIFT_PER_ERA` | 玩家(目标) | 本时代已被赠送次数 |
| `APCG_HIRE_PER_ERA` | 玩家(目标) | 本时代已被雇佣次数 |
| `APCG_TRADE_ROUTE_FROM_GIFT` | 首都地块 | 累计贸易路线赠送数 |
| `PRO_TRFG_1~8` | 首都地块 | 贸易路线赠送的二进制旗标 |
| `PRO_VASSAL_GOLD_1~15` | 首都地块 | 贡金的二进制旗标 |

## 事件注册

| 事件 | 用途 |
|---|---|
| `Events.AllianceEnded` | 移除附庸关系 |
| `Events.CapitalCityChanged` | 标记新首都为附庸首都 |
| `Events.CityConquered` | 清除被征服的附庸首都标记 |
| `Events.UnitKilledInCombat` | 城邦击杀给使者 |
| `Events.GameEraChanged` | 重置每时代赠送/雇佣次数 |
| `Events.LoadGameViewStateDone` | 初始化 |

## 注意事项

1. **同盟类型冲突**：如果目标已经是其他同盟类型，`SetHasAllied` 会覆盖
2. **自定义 DynamicModifier**：`COLLECTION_ALLIANCE_CITIES` 是非标准集合，需要通过 DLL 扩展或动态注册
3. **UI弹窗触发**：需要配合 `Unit_Panel.lua` 修改，在单位面板中注入朝贡按钮
4. **费用为0检查**：弹窗中多处检查玩家金币是否够用
5. **自身排除**：禁止向自己朝贡 (pPlayerID == localPlayerID)
6. **城邦ID排除**：62和63是自由城市等特殊单位，需要排除

## 依赖

- 需要自定义同盟的 DynamicModifier 支持（可通过 DLL 扩展或 `INSERT INTO DynamicModifiers` 实现）
- 二进制折叠系统（见 `lua-workshop-binary-yield.md`）
