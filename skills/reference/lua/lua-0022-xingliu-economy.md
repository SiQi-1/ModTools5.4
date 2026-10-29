# lua-0022-xingliu-economy -- 心流 (Xingliu) 双资源经济系统

从 Siqi_Leaders_0022 提炼。核心模式：伟人点数按比例转化为 P（心灵），P 再产 Xingliu（心流），Xingliu 作为通用货币购买伟人/建筑/单位。

---

## 快速索引

| 组件 | 键名 | 说明 |
|------|------|------|
| Xingliu 余额 | `Siqi_Xingliu_Banlance` | 可消耗的货币（Player Property） |
| P 余额 | `Siqi_Xingliu_P_Banlance` | 积累型资源（Player Property） |
| Xingliu 每回合 | `Siqi_Xingliu_PerTurn` | 存储每回合 Xingliu 增量（用于 UI） |
| GW 追踪 | `GREATWORK_SIQI_G0022_*` | 匹配巨作前缀 |
| 信仰标记 | `Siqi_No_Faith` | 城市无信仰 debuff 属性 |
| 总督标记 | `Siqi_Has_Governor` | 城市总督 debuff 属性 |

---

## 一、资源转换链

```
Great Musician 点数(50%) \
                            → P（心灵）= min(大音/0.5, 大科/0.5) × 2
Great Scientist 点数(50%) /
                                    ↓ P × 2 → Xingliu 每回合
巨作(GREATWORK_SIQI_G0022_*): 每件 +2 Xingliu/回合
建造者B2: 文化相邻加成 → Xingliu/回合
建造者B4: Player Property → Xingliu/回合
单位维护费: -Xingliu/回合
```

---

## 二、核心 API：Xingliu 表

### 2.1 余额读写

```lua
local XingliuBanlance = DB.MakeHash("Siqi_Xingliu_Banlance")
local P_Banlance = DB.MakeHash("Siqi_Xingliu_P_Banlance")

-- 获取 Xingliu 余额
function Xingliu:GetXingliu(PlayerID)
    return Players[PlayerID]:GetProperty(XingliuBanlance) or 0
end

-- 获取 P 余额
function Xingliu:GetP(PlayerID)
    return Players[PlayerID]:GetProperty(P_Banlance) or 0
end

-- 修改 Xingliu（下限 0 + 自动广播刷新）
function Xingliu:ChangeXingliu(PlayerID, amount)
    local pPlayer = Players[PlayerID]
    local Banlance = (pPlayer:GetProperty(XingliuBanlance) or 0) + amount
    if Banlance < 0 then Banlance = 0 end
    pPlayer:SetProperty(XingliuBanlance, Banlance)
    SiqiGameRefresh()
end

-- 修改 P（下限 0 + 自动广播刷新）
function Xingliu:ChangeP(PlayerID, amount)
    local pPlayer = Players[PlayerID]
    local P_Amount = (pPlayer:GetProperty(P_Banlance) or 0) + amount
    if P_Amount < 0 then P_Amount = 0 end
    pPlayer:SetProperty(P_Banlance, P_Amount)
    SiqiGameRefresh()
end
```

### 2.2 广播刷新

```lua
function SiqiGameRefresh()
    if Game:GetProperty("SIQI_CORE_GAME_REFRESH") then
        Game:SetProperty("SIQI_CORE_GAME_REFRESH", false)
    end
    if not Game:GetProperty("SIQI_CORE_GAME_REFRESH") then
        Game:SetProperty("SIQI_CORE_GAME_REFRESH", true)
    end
end
```

UI 端监听 `Events.GamePropertyChanged` 触发 `SIQI_CORE_GAME_REFRESH` 变化后刷新面板。

---

## 三、GetData() — 核心计算引擎

每回合调用，遍历所有城市，计算 P 和 Xingliu 的每回合产出。关键逻辑：

### 3.1 P 计算（城市级）

```lua
-- 只计算两种伟人点数：大音乐家(50%) + 大科学家(50%)
local GreatPoints = {}
GreatPoints["GREAT_PERSON_CLASS_MUSICIAN"] = true
GreatPoints["GREAT_PERSON_CLASS_SCIENTIST"] = true

-- 木桶效应：P = min(大音/0.5, 大科/0.5) × 2
function GetMaxGreatPersonPoints(a, d)
    return math.min(a / 0.50, d / 0.50)
end
```

遍历城市所有建筑和区域的 `Building_GreatPersonPoints` / `District_GreatPersonPoints`，累加每种伟人点数。

### 3.2 城市 Debuff 系统

每个城市对 GP 点数产出有两个 debuff，各减 30%：

| Debuff | 属性名 | 触发条件 |
|--------|--------|---------|
| 无信仰 | `Siqi_No_Faith` | 城市 Property > 0 |
| 无总督 | `Siqi_Has_Governor` | 城市 Property > 0 |

```lua
local Debuff = 1
if pCity:GetProperty(NoFaith) and pCity:GetProperty(NoFaith) > 0 then
    Debuff = Debuff - 0.3
end
if pCity:GetProperty(HasGovernor) and pCity:GetProperty(HasGovernor) > 0 then
    Debuff = Debuff - 0.3
end
-- 实际 GP 产出 = 基础点数 × Debuff（最低 0.4）
```

### 3.3 Xingliu 每回合来源

```
Xingliu_PerTurn =
    + P_PerTurn × 2          -- P 转换（每点 P = 2 Xingliu）
    + FromGW                 -- 巨作（每件 +2）
    + FromBelief_B2          -- B2 建造者：DISTRICT_SIQI_D0022_D1 文化相邻加成
    + FromBelief_B4          -- B4 建造者：Player Property 直接给值
    - FromUnit               -- 单位维护费
```

### 3.4 完整 GetData 函数签名和数据表结构

```lua
function Xingliu:GetData(playerID)
    -- 返回 table:
    -- t.points["GREAT_PERSON_CLASS_MUSICIAN"] = number   -- 大音乐家总点数
    -- t.points["GREAT_PERSON_CLASS_SCIENTIST"] = number  -- 大科学家总点数
    -- t.Cities[cityID]["GREAT_PERSON_CLASS_*"] = number  -- 城市明细
    -- t.Cities[cityID].DebuffFromFaith = bool
    -- t.Cities[cityID].DebuffFromGrovernor = bool
    -- t.P_PerTurn = number               -- 每回合 P 产出
    -- t.Xingliu_PerTurn = number         -- 每回合 Xingliu 产出
    -- t.FromGreatWorks = number          -- 巨作贡献
    -- t.FromUnit = number                -- 单位维护费
    -- t.Xingliu_Banlance = number        -- 当前 Xingliu 余额
    -- t.P_Banlance = number              -- 当前 P 余额
    -- t.ToolTip = { Musician=, Scientist=, P_ZHU=, Xingliu= }
end
```

---

## 四、消耗系统（Xingliu 作为货币）

通过 `GameEvents` 从 UI 发射，GP 端接收并扣款。

### 4.1 购买伟人

```lua
function Siqi0022_GreatPersonPurchase(playerID, params)
    Game.GetGreatPeople():GrantPerson(params.Hash, params.Class, params.era, 0, playerID, false)
    Xingliu:ChangeP(playerID, -params.Cost)     -- 消耗 P（不是 Xingliu）
    Game.SetProperty("Siqi0022_GreatPerson_" .. params.index, true)  -- 防重复购买
    -- 第 1~12 号伟人额外触发领袖特性的鼓舞/尤里卡
    if params.index >= 1 and params.index <= 12 then
        if SiqiGP.HasTrait(playerID, m_Leader) then
            pPlayer:AttachModifierByID("MODIFIER_SIQI_L0022_L1_GRANT_TECHNOLOGY_BOOST")
            pPlayer:AttachModifierByID("MODIFIER_SIQI_L0022_L1_GRANT_CIVIC_BOOST")
        end
    end
end
```

### 4.2 购买建筑

```lua
function Siqi0022_BuildingPurchase(playerID, params)
    local pCity = CityManager.GetCity(playerID, params.CityID)
    if pCity and not pCity:GetBuildings():HasBuilding(building.Index) then
        pCity:GetBuildQueue():CreateBuilding(building.Index)
        Xingliu:ChangeXingliu(playerID, -params.Cost)
    end
end
```

### 4.3 购买单位（含军团/军队）

```lua
function Siqi0022_UnitPurchase(playerID, params)
    local pCity = CityManager.GetCity(playerID, params.CityID)
    if not params.IsReligion then
        local pUnit = UnitManager.InitUnit(playerID, params.Type, pCity:GetX(), pCity:GetY())
        if params.IsCorps then
            pUnit:SetMilitaryFormation(MilitaryFormationTypes.CORPS_FORMATION)
        elseif params.IsArmy then
            pUnit:SetMilitaryFormation(MilitaryFormationTypes.ARMY_FORMATION)
        end
        Xingliu:ChangeXingliu(playerID, -params.Cost)
        if params.Type == "UNIT_SETTLER" then
            pCity:ChangePopulation(-1)    -- 移民额外扣 1 人口
        end
    else
        -- 宗教单位通过 AttachModifierByID 赠送
        pCity:AttachModifierByID("MODIFIER_SIQI_0022_GRANT_" .. params.Type)
        Xingliu:ChangeXingliu(playerID, -params.Cost)
    end
end
```

### 4.4 GameEvents 注册（GP 端）

```lua
GameEvents.Siqi0022_GreatPersonPurchase.Add(Siqi0022_GreatPersonPurchase)
GameEvents.Siqi0022_BuildingPurchase.Add(Siqi0022_BuildingPurchase)
GameEvents.Siqi0022_UnitPurchase.Add(Siqi0022_UnitPurchase)
GameEvents.Siqi0022_ChangeXingliu.Add(Siqi0022_ChangeXingliu)
```

---

## 五、自定义伟人类别与个体触发

### 5.1 触发伟人 13 号：完成占星术科技

```lua
function SiqiOnResearchCompleted(ePlayer, eTech)
    if not SiqiGP.HasTrait(ePlayer, m_Trait) then return end
    if eTech == GameInfo.Technologies["TECH_ASTROLOGY"].Index then
        local pCity = pPlayer:GetCities():GetCapitalCity()
        GrantVirtualBuilding(pPlayer, "BUILDING_SIQI_B0022_B3", pCity)  -- 授予虚拟建筑
        -- 赠送 13 号伟人（免费，防重复）
        if not Game.GetProperty("Siqi0022_GreatPerson_13") then
            Siqi0022_GreatPersonPurchase(ePlayer, {Hash=..., Class=..., Cost=0, index=13})
        end
    end
end
```

### 5.2 触发伟人 14 号：完成自定义项目

```lua
function SiqiOnCityProjectCompleted(playerID, cityID, projectID, ...)
    if projectID ~= GameInfo.Projects['PROJECT_SIQI_P0022_P1'].Index then return end
    Siqi0022_GreatPersonPurchase(playerID, {Hash=..., Class=..., Cost=0, index=14})
end
```

### 5.3 伟人激活回调

```lua
function SiqiOnUnitGreatPersonActivated(unitOwner, unitID, greatPersonClassID, greatPersonIndividualID)
    if not SiqiGP.HasTrait(unitOwner, m_Trait) then return end
    if greatPersonClassID ~= m_GreatPersonClass then return end
    -- 激活后永久 +2 Xingliu/回合
    local o = pPlayer:GetProperty(XingliuPerTurn) or 0
    pPlayer:SetProperty(XingliuPerTurn, o + 2)
end
```

---

## 六、单位特殊行动

### 6.1 相位穿梭（Leap）

```lua
function U0022LeapAction1(playerID, params)
    local pUnit = UnitManager.GetUnit(playerID, params.UnitID)
    if pUnit then
        UnitManager.PlaceUnit(pUnit, params.X, params.Y)  -- 传送到目标格
        UnitManager.FinishMoves(pUnit)
    end
end
GameEvents.U0022LeapAction1.Add(U0022LeapAction1)
```

### 6.2 宗教压力爆发

```lua
function U0022ReligionAction1(playerID, params)
    local pUnit = UnitManager.GetUnit(playerID, params.UnitID)
    local combat = pUnit:GetCombat() or 0
    local pCity = CityManager.GetCity(params.City.playerID, params.City.ID)
    local impact = math.floor(combat * 2.5)  -- 压力 = 战斗力 × 2.5
    pCity:GetReligion():AddReligiousPressure(playerID, params.ReligionType, impact, -1)
    Xingliu:ChangeXingliu(playerID, -params.Cost)
    UnitManager.FinishMoves(pUnit)
    -- 记录额外消耗（递增）
    local o = pPlayer:GetProperty("Siqi_U0022_ExtraCost") or 0
    pPlayer:SetProperty("Siqi_U0022_ExtraCost", o + 1)
    pUnit:SetProperty("Siqi_U0022_Used", true)          -- 单位当回合标记
    -- 全局单位使用记录（每回合重置）
    local t = Game:GetProperty('Siqi_U0022_Used_Units') or {}
    table.insert(t, {owner = playerID, id = pUnit:GetID()})
    Game:SetProperty('Siqi_U0022_Used_Units', t)
end
```

### 6.3 回合开始时重置单位状态

```lua
function SiqiOnTurnBegin()
    local Units = Game:GetProperty('Siqi_U0022_Used_Units') or {}
    for _, unit in ipairs(Units) do
        local pUnit = UnitManager.GetUnit(unit.owner, unit.id)
        if pUnit then pUnit:SetProperty("Siqi_U0022_Used", false) end
    end
    Game:SetProperty('Siqi_U0022_Used_Units', {})
end
Events.TurnBegin.Add(SiqiOnTurnBegin)
```

---

## 七、击杀返还 Xingliu（建造者 B6）

```lua
function SiqiOnUnitKilledInCombat(killedPlayerID, killedUnitID, playerID, unitID)
    local pKilledUnit = UnitManager.GetUnit(killedPlayerID, killedUnitID)
    if not SiqiGP.HasProperty(Players[killedPlayerID], Beielf_B6) then return end
    local cost = math.floor(GameInfo.Units[pKilledUnit:GetType()].Cost * 0.8 * GAME_SPEED_MULTIPLIER)
    Xingliu:ChangeXingliu(killedPlayerID, cost)
    -- 地图浮字
    Game.AddWorldViewText(0, "+"..tostring(cost).." [ICON_SIQI_XINGLIU]", iX, iY)
end
```

---

## 八、区划产出属性刷新（Siqi0022 文明专属）

城市特定区划的产出需要刷新到地块 Property，使 SQL Modifier 生效：

```lua
-- UI 端读取每个城市需要更新的区划产出
function Siqi0022.UI.GetCityData(playerID, pCity)
    local limit = pPlayer:GetProperty(property_Civ_Limit) or 0
    local FromGW = 0
    -- 统计城市中 GREATWORK_SIQI_G0022_* 巨作数量
    -- 每个巨作给所有区划产出 +1
    for row in GameInfo.Siqi_0022_DistrictYieldSupport() do
        local new = (pCity:GetProperty(property_Civ_City .. row.DistrictType) or 0) + FromGW
        if new > limit then new = limit end
        -- 只收集需要变化的区划
    end
end

-- GP 端刷新地块 Property
function Siqi0022.GP.Refresh(playerID, data)
    for _, row in ipairs(data) do
        local plot = Map.GetPlot(row.iX, row.iY)
        for _, d in ipairs(row.Data) do
            plot:SetProperty(property_Civ .. d.DistrictType, d.Amount)
        end
    end
    SiqiGameRefresh()
end
```

---

## 九、设计要点

| 要点 | 说明 |
|------|------|
| 双资源设计 | P 是"积累型"（只能涨不能主动花），Xingliu 是"消耗型" |
| 木桶效应 | P 产出取决于最少的伟人点数，防止单一种类垄断 |
| 城市级 Debuff | 每城独立计算 GP 产出 debuff（信仰/总督），鼓励铺城 |
| 巨作联动 | 自定义巨作前缀匹配，给 Xingliu 产出 |
| 购买体系 | 统一通过 GameEvents 消费 Xingliu，支持伟人/建筑/单位三种 |
| 单位回合状态 | 用全局 Game Property 存储 `{owner, id}` 表，每回合 TurnBegin 重置 |
| 虚拟建筑 | GrantVirtualBuilding 用 CreateBuilding 而非直接修改 Building 表 |

---

## 十、文件清单

| 文件 | 内容 |
|------|------|
| `Scripts/Siqi_Leaders_0022_Scripts.lua` | 入口 + GameEvents 注册 + 事件回调 |
| `Support/Siqi_Leaders_0022_Support.lua` | Xingliu API + GetData 计算 + Siqi0022 区划刷新 |

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `UI/Siqi_Leaders_0022_CityPanel.xml` | 城市杏仁（Almond）复选框 — 控制城市产出切换 |
| `UI/Siqi_Leaders_0022_UnitButton.xml` | 单位行动按钮 — 宗教压力 / 相位穿梭入口 |
| `UI/Siqi_Leaders_0022_UnitPanel.xml` | 单位面板扩展 — KTA 按钮（相位穿梭） |
| `UI/Siqi_Leaders_0022_TopPanel.xml` | TopPanel 扩展 — Xingliu 余额 / 每回合显示 |
| `UI/Siqi_Leaders_0022_ProductionPanel.xml` | 自定义生产面板 — Xingliu 购买伟人/建筑/单位 |
| `UI/Siqi_Leaders_0022_UI.xml` | 空壳 Context — 仅作为 Include 入口 |

### 控件 ID 与 Lua Controls.xxx 对照

#### CityPanel.xml

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `SiqiAlmondGrid` | Grid | `Controls.SiqiAlmondGrid` | 杏仁复选框容器 |
| `SiqiAlmondCheck` | CheckBox | `Controls.SiqiAlmondCheck` | 杏仁启用/禁用切换（IsChecked/SetDisabled/SetToolTipString） |

```lua
-- CityPanel.lua 读取方式
if Controls.SiqiAlmondCheck:IsChecked() then
    -- 使用 Xingliu 产出
end
-- 挂载到原版 CityPanel
local pContext = ContextPtr:LookUpControl("/InGame/CityPanel")
Controls.SiqiAlmondGrid:ChangeParent(pContext)
```

#### UnitButton.xml（宗教压力按钮）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `UnitGrid` | Grid | `Controls.UnitGrid` | 宗教行动按钮容器 |
| `UnitButton` | Button | `Controls.UnitButton` | 宗教压力释放按钮 |
| `UnitButtonIcon` | Image | — | 按钮图标 |

#### UnitPanel.xml（相位穿梭按钮）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `KTAButtonGrid` | Grid | `Controls.KTAButtonGrid` | 相位穿梭按钮容器 |
| `KTAButton` | Button | `Controls.KTAButton` | 相位穿梭按钮（注册 eLClick） |
| `KTAButtonIcon` | Image | — | 按钮图标（ICON_UNIT_SIQI_U0022_U2） |

#### TopPanel.xml（Xingliu 余额显示）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `CelebrationsTrackerGrid` | Container | `Controls.CelebrationsTrackerGrid` | Xingliu 追踪容器 |
| `CelebrationsTrackerHappiness` | GridButton | `Controls.CelebrationsTrackerHappiness` | Xingliu 余额按钮 |
| `HappinessIconString` | Label | — | Xingliu 图标 |
| `HappinessBalance` | Label | `Controls.HappinessBalance` | Xingliu 余额数字 |
| `HappinessPerTurn` | Label | `Controls.HappinessPerTurn` | Xingliu 每回合数字 |

#### ProductionPanel.xml（Xingliu 购买面板）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `Siqi_RightPanel` | Context | — | 根 Context Name |
| `ProductionPanel` | Container | — | 生产面板主容器 |
| `PurchaseMenu` | Container | `Controls.PurchaseMenu` | 金币购买页 |
| `PurchaseFaithMenu` | Container | `Controls.PurchaseFaithMenu` | 信仰购买页 |
| `PurchaseTab` | GridButton | `Controls.PurchaseTab` | 金币购买标签 |
| `PurchaseFaithTab` | GridButton | `Controls.PurchaseFaithTab` | 信仰购买标签 |
| `GreatPersonPointType1` | GridButton | `Controls.GreatPersonPointType1` | 大音乐家点数显示 |
| `GreatPersonPointType4` | GridButton | `Controls.GreatPersonPointType4` | 大科学家点数显示 |
| `SiqiFlowButton1` | GridButton | `Controls.SiqiFlowButton1` | Xingliu 产出按钮1 |
| `SiqiFlowButton2` | GridButton | `Controls.SiqiFlowButton2` | P产出按钮1 |
| `HeaderLabel` | Label | — | 面板标题 |
| `CloseButton` | Button | — | 关闭按钮 |
| `PurchaseListScroll` | ScrollPanel | `Controls.PurchaseListScroll` | 购买列表滚动面板 |
| `PurchaseList` | Stack | `Controls.PurchaseList` | 购买列表 Item 挂载点 |
| `NoGoldContent` | Grid | `Controls.NoGoldContent` | "金币不足"提示 |
| `PurchaseFaithListScroll` | ScrollPanel | `Controls.PurchaseFaithListScroll` | 信仰购买滚动面板 |
| `PurchaseFaithList` | Stack | `Controls.PurchaseFaithList` | 信仰购买列表 |

### Instance 模板（ProductionPanel）

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `NestedList` | 嵌套列表（伟人/建筑/单位分类折叠） | `Header`(GridButton), `HeaderOn`(GridButton), `ListSlide`(SlideAnim), `List`(Stack) |
| `BuildingListInstance` | 建筑购买项 | `Button`(GridButton), `Icon`(Image), `LabelText`(Label), `CostText`(Label), `ProductionProgress`(TextureBar) |
| `UnitListInstance` | 战斗单位购买项（含军团/军队扩展） | `Button`(GridButton), `TrainCorpsButton`/`TrainArmyButton`, `ArmyCorpsDrawer` |
| `CivilianListInstance` | 平民单位购买项 | `Button`(GridButton), `Icon`, `LabelText`, `CostText` |

### 按钮回调注册模式

```lua
-- CityPanel 杏仁复选框
Controls.SiqiAlmondCheck:RegisterCheckCallback(function() OnAlmondToggled() end)

-- UnitButton 单位行动按钮
local pContext = ContextPtr:LookUpControl("/InGame/UnitPanel/StandardActionsStack")
Controls.UnitGrid:ChangeParent(pContext)
Controls.UnitButton:RegisterCallback(Mouse.eLClick, OnUnitActionClicked)

-- ProductionPanel 标签切换
Controls.PurchaseTab:RegisterCallback(Mouse.eLClick, function() ShowPurchaseMenu() end)
Controls.PurchaseFaithTab:RegisterCallback(Mouse.eLClick, function() ShowPurchaseFaithMenu() end)
```

### 添加新控件模板

```xml
<!-- 新单位行动按钮模板 (UnitButton.xml) -->
<Grid ID="NewActionGrid" Anchor="R,B" Size="auto,41" AutoSizePadding="6,0" 
      Texture="SelectionPanel_ActionGroupSlot" SliceCorner="5,19" SliceSize="1,1" 
      SliceTextureSize="12,41" ConsumeMouse="1" Hidden="1">
    <Button ID="NewActionButton" Anchor="C,B" Size="44,53" Texture="UnitPanel_ActionButton">
        <Image ID="NewActionIcon" Anchor="C,C" Offset="0,-2" Size="38,38" Icon="ICON_YOUR_ICON"/>
    </Button>
</Grid>
```

```lua
-- 挂载到 UnitPanel
local pContext = ContextPtr:LookUpControl("/InGame/UnitPanel/StandardActionsStack")
Controls.NewActionGrid:ChangeParent(pContext)
Controls.NewActionButton:RegisterCallback(Mouse.eLClick, OnNewActionClicked)
```
