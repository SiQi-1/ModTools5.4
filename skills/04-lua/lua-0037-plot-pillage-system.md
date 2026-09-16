# 单元格掠夺与产出修改系统（来源：16.0 Shamare + Tecno）

## 做什么
两套互补的单位-地块交互系统：Shamare（巫恋）允许战斗单位掠夺敌方地块产出并转换为奖励；Tecno（涤火杰西卡）允许建造者消耗劳动力在地块上增加固定产出。都通过 `UI.RequestPlayerOperation` + GameEvent 实现 UI → GP 消费管道，并在 GP 端通过 LuaEvents 修改地块属性。

## 涉及文件

| 文件 | 角色 |
|------|------|
| `16.0/Scripts/Arknights_Cute_Leaders_16.0_Scripts.lua` | GP 端：掠夺逻辑 + 建造者产出修改 + 击杀生成单位 |
| `16.0/UI/Arknights_Cute_Leaders_16.0_UI.lua` | UI 端：单位面板按钮系统（325 行），含动态产出网格 |
| Core Mod 的 LuaEvents | `SiqiChangePlotYieldChange` — 地块产出修改底层函数 |

## 系统一：Shamare 地块掠夺（战斗单位）

### GP 端

**掠夺逻辑：**
```lua
function SiqiShamarePillage(playerID, params)
    -- 1. 遍历 YieldAmount：扣除地块上的产出
    for _, row in ipairs(params.YieldAmount) do
        LuaEvents.SiqiChangePlotYieldChange(params.plotIndex, row.YieldType, -row.Amount)
    end
    
    -- 2. 遍历 PillgaedAmount：发放奖励
    for _, row in ipairs(params.PillgaedAmount) do
        Siqi_Reward(playerID, row.YieldType, row.Amount)
        Game.AddWorldViewText(0, '+'..amount..Siqi_GetYieldString(yieldType), pPlot:GetX(), pPlot:GetY())
    end
    
    -- 3. 消耗单位行动力
    UnitManager.ReportActivation(pUnit, "SIQI_SHAMARE_PILLAGE")
    UnitManager.FinishMoves(pUnit)
end
```

**奖励映射表（PillgaedReward）：**
```lua
PillgaedReward["YIELD_FOOD"]       = {YieldType = "YIELD_GOLD",    Amount = 30}
PillgaedReward["YIELD_PRODUCTION"] = {YieldType = "YIELD_SCIENCE", Amount = 20}
PillgaedReward["YIELD_GOLD"]       = {YieldType = "YIELD_GOLD",    Amount = 40}
PillgaedReward["YIELD_SCIENCE"]    = {YieldType = "YIELD_SCIENCE", Amount = 40}
PillgaedReward["YIELD_CULTURE"]    = {YieldType = "YIELD_CULTURE", Amount = 40}
PillgaedReward["YIELD_FAITH"]      = {YieldType = "YIELD_FAITH",   Amount = 40}
```

**奖励计算：**
```lua
amount = math.floor(
    ePillgaedReward.Amount *           -- 基础值
    SiqiGetPlayerProgress(playerID) *  -- 玩家进度系数
    yield *                            -- 掠夺的地块产出点数
    GAME_SPEED_MULTIPLIER             -- 游戏速度
)
```

### UI 端

**注入位置：** `/InGame/UnitPanel/StandardActionsStack`

**按钮显示条件（IsButtonHide）：**
1. 玩家必须拥有 TRAIT_SHAMARE
2. 单位必须有战斗力
3. 单位需有剩余移动力
4. 当前单元格不是区域
5. 单元格所有者与玩家处于战争状态
6. 水域单位必须在水域地块 / 陆地单位必须在陆地
7. 单元格总产出 > 0

**按钮禁用条件（IsButtonDisabled）：**
- 产出为 0 时显示 "无产出可掠夺"
- 有产出时 tooltip 显示：当前产出明细 + 对应奖励预览

**点击处理：**
```lua
function OnButtonClickedSiqiShamare()
    -- 收集当前地块所有 >0 的产出
    for i = 0, 5 do
        if yield > 0 then
            table.insert(YieldAmount, {YieldType = yieldType, Amount = yield})
            table.insert(PillgaedAmount, {YieldType = rewardType, Amount = calculated})
        end
    end
    UI.RequestPlayerOperation(playerID, PlayerOperations.EXECUTE_SCRIPT, {
        OnStart = "SiqiShamarePillage",
        YieldAmount = YieldAmount,
        PillgaedAmount = PillgaedAmount,
        plotIndex = pPlot:GetIndex(),
        unitID = pUnit:GetID()
    })
end
```

## 系统二：Tecno 建造者产出修改

### GP 端

```lua
function SiqiTecnoYieldChange(playerID, params)
    -- 1. 地块产出 +2
    LuaEvents.SiqiChangePlotYieldChange(params.plotIndex, params.YieldType, 2)
    
    -- 2. 消耗劳动力 + 结束移动
    UnitManager.ReportActivation(pUnit, "SIQI_TECNO_YIELD_CHANGE")
    UnitManager.FinishMoves(pUnit)
    Siqi_Reduced_Unit_Charges(playerID, unitID)  -- 减少建造次数
end
```

**击杀生成单位（Tecno 专属）：**
```lua
function SiqiOnUnitKilledInCombat(killedPlayerID, killedUnitID, playerID, unitID)
    -- Tecno 击杀时：生成布偶舞者
    if SIqi_PlayerHasTrait(playerID, TRAIT_TECNO) then
        Siqi_InitBarbarianUnit(pUnit:GetX(), pUnit:GetY(), TYPE_PUPPET_DANCER, playerID)
    end
    -- Tecno 被击杀时：所有城市附加旅游业绩 Modifier
    if SIqi_PlayerHasTrait(killedPlayerID, TRAIT_TECNO) then
        for i, pCity in pPlayerCities:Members() do
            pCity:AttachModifierByID("MODIFIER_SIQI_TECNO_ADJUST_TOURISM_CHANGE_THEATER")
        end
    end
end
```

### UI 端

**动态产出选择网格：**

InstanceManager 定义：
```lua
local m_SiqiTecnoIM = InstanceManager:new("SiqiTecnoInstance", "Top", Controls.SiqiTecnoButtonStack)
```

**网格构建（SiqiTecno:YieldRefresh）：**
```lua
-- 3 列布局，每行显示 3 个产出按钮
for i = 1, count, 3 do
    local columnInstance = m_SiqiTecnoIM:GetInstance()
    for iRow = 1, 3 do
        if (i + iRow - 1) <= count then
            local t = Detail[(i + iRow - 1)]
            local slotName = "Row" .. tostring(iRow)
            local instance = {}
            ContextPtr:BuildInstanceForControl("YieldInstance", instance, columnInstance[slotName])
            instance.YieldIcon:SetIcon(t.YieldIcon)
            instance.YieldButton:RegisterCallback(Mouse.eLClick, function()
                SiqiTecno:YieldChange(t.YieldType)
            end)
            instance.YieldButton:SetToolTipString(tooltip)
        end
    end
end
```

**面板大小自适应：**
```lua
Controls.SiqiTecnoButtonStack:CalculateSize()
Controls.SiqiTecnoGrid:SetSizeX(stackWidth + RES_PANEL_ART_PADDING_X)
Controls.SiqiTecnoGrid:SetSizeY(stackHeight + RES_PANEL_ART_PADDING_Y)
```

**面板定位：** 注入到 UnitPanelSlide 滑出面板中，偏移到右侧：
```lua
Controls.SiqiTecnoGrid:SetOffsetX(container:GetSizeX() + container2:GetSizeX() + 202)
```

**按钮显示条件（IsButtonHideB）：**
1. 单位必须是建造者 (`UNIT_BUILDER`)
2. 玩家必须有 TRAIT_TECNO
3. 建造次数 > 0
4. 剩余移动力 > 0
5. 所在单元格属于玩家自己
6. 不在非市中心区域上

**按钮点击处理：**
```lua
function SiqiTecno:YieldChange(YieldType)
    UI.RequestPlayerOperation(pUnit:GetOwner(), PlayerOperations.EXECUTE_SCRIPT, {
        OnStart = "SiqiTecnoYieldChange",
        YieldType = YieldType,
        unitID = pUnit:GetID(),
        plotIndex = pPlot:GetIndex()
    })
end
```

## 单位激活特效

```lua
function SiqiOnUnitActive(owner, unitID, x, y, eReason)
    if eReason == SIQI_SHAMARE_PILLAGE then
        WorldView.PlayEffectAtXY("IMPROVEMENT_CREATED", uX, uY)
    elseif eReason == HASH_TECNO_YIELD_CHANGE then
        SimUnitSystem.SetAnimationState(pUnit, "ACTION_A", "IDLE")
        WorldView.PlayEffectAtXY("IMPROVEMENT_CREATED", uX, uY)
    end
end
```

## 奖励分发函数

```lua
function Siqi_Reward(playerID, YieldType, Amount)
    if YieldType == "YIELD_GOLD" then
        pPlayer:GetTreasury():ChangeGoldBalance(Amount)
    elseif YieldType == "YIELD_SCIENCE" then
        pPlayer:GetTechs():ChangeCurrentResearchProgress(Amount)
    elseif YieldType == "YIELD_CULTURE" then
        pPlayer:GetCulture():ChangeCurrentCulturalProgress(Amount)
    elseif YieldType == "YIELD_FAITH" then
        pPlayer:GetReligion():ChangeFaithBalance(Amount)
    end
    -- 注意：YIELD_FOOD 和 YIELD_PRODUCTION 不会直接发放奖励
end
```

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `UI/Arknights_Cute_Leaders_16.0_UI.xml` | Shamare 掠夺按钮 + Tecno 建造者产出选择网格（含 2 种 Instance 模板） |
| `Arknights_Cute_Leaders_16.0_Modifiers.sql` | Modifier 链定义（含 Tecno 旅游业绩加成等） |
| `Arknights_Cute_Leaders_16.0_UnitAbilities.sql` | 单位能力定义 |
| `Arknights_Cute_Leaders_16.0_Configs.sql` | GameCapabilities 属性注册 |
| `Arknights_Cute_Leaders_16.0_Improvements.sql` | 自定义改良设施（布苹果等） |

### 控件 ID 与 Lua Controls.xxx 对照

#### Arknights_Cute_Leaders_16.0_UI.xml（双系统面板）

**Shamare 掠夺按钮：**

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `SiqiShamareGrid` | Grid | `Controls.SiqiShamareGrid` | 掠夺按钮容器（Hidden="1"） |
| `SiqiShamareButton` | Button | `Controls.SiqiShamareButton` | 掠夺触发按钮（44x53，ICON_UNITOPERATION_PILLAGE） |
| `SiqiShamareButtonIcon` | Image | — | 按钮图标 |

**Tecno 建造者产出选择面板：**

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `SiqiTecnoGrid` | Grid | `Controls.SiqiTecnoGrid` | 产出选择面板外层（51x160，Offset="501,0"） |
| `SiqiTecnoButtonStack` | Stack | `Controls.SiqiTecnoButtonStack` | 产出按钮挂载点（StackGrowth="Left"，InstanceManager 父容器） |

**Instance 模板（2 种）：**

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `SiqiTecnoInstance` | 产出列容器（尺寸 38x140） | `Top`(Container), `Row1`(Image), `Row2`(Image), `Row3`(Image) — 3 行插槽 |
| `YieldInstance` | 单个产出按钮（嵌套在 Row1~Row3 中） | `YieldButton`(Button, 44x53), `YieldIcon`(Image, 38x38) |

**Instance 嵌套模式：**
```lua
-- 外层 Instance 提供 3 行插槽
local columnInstance = m_SiqiTecnoIM:GetInstance()
-- 内层 Instance 填充每行的产出按钮
for iRow = 1, 3 do
    local slotName = "Row" .. tostring(iRow)
    local instance = {}
    ContextPtr:BuildInstanceForControl("YieldInstance", instance, columnInstance[slotName])
    instance.YieldIcon:SetIcon(yieldIcon)
    instance.YieldButton:RegisterCallback(Mouse.eLClick, function()
        OnYieldChange(yieldType)
    end)
end
```

### 挂载模式（双系统各自挂载）

**Shamare 按钮 — 挂载到 UnitPanel/StandardActionsStack：**
```lua
local pContext = ContextPtr:LookUpControl("/InGame/UnitPanel/StandardActionsStack")
Controls.SiqiShamareGrid:ChangeParent(pContext)
Controls.SiqiShamareButton:RegisterCallback(Mouse.eLClick, OnButtonClickedSiqiShamare)
```

**Tecno 面板 — 挂载到 UnitPanelSlide（滑出面板）：**
```lua
local pContainer = ContextPtr:LookUpControl("/InGame/UnitPanel/UnitPanelSlide")
Controls.SiqiTecnoGrid:ChangeParent(pContainer)
-- 偏移定位到右侧
Controls.SiqiTecnoGrid:SetOffsetX(container:GetSizeX() + container2:GetSizeX() + 202)
-- 强制面板重排
ContextPtr:LookUpControl('/InGame/UnitPanel/UnitPanelBaseContainer'):Reparent()
```

### SQL 必需定义

#### Modifier 链

| ModifierType | 作用 |
|-------------|------|
| `MODIFIER_SIQI_TECNO_ADJUST_TOURISM_CHANGE_THEATER` | Tecno 被击杀后所有城市附加旅游业绩加成 |

#### GameCapabilities 属性

```sql
-- Configs.sql 注册
Siqi_ClothAppleImprovement          -- 布苹果改良设施标记

-- 其他 Lua 内部使用的 Property（通过 pPlayer/pCity:SetProperty 操作，也需注册）
```

### 添加新单位-地块交互按钮模板

```xml
<!-- 新交互按钮（UnitPanel 注入） -->
<Grid ID="NewInteractionGrid" Anchor="R,B" Size="auto,41" AutoSizePadding="6,0"
      Texture="SelectionPanel_ActionGroupSlot" SliceCorner="5,19" SliceSize="1,1"
      SliceTextureSize="12,41" ConsumeMouse="1" Hidden="1">
    <Button ID="NewInteractionButton" Anchor="C,B" Size="44,53" Texture="UnitPanel_ActionButton">
        <Image ID="NewInteractionButtonIcon" Anchor="C,C" Offset="0,-2" Size="38,38"
               Icon="ICON_NEW_INTERACTION"/>
    </Button>
</Grid>

<!-- 如果新系统需要内嵌选择面板（类似 Tecno 模式） -->
<Instance Name="NewInteractionSlotInstance">
    <Container ID="Top" Size="38,140">
        <Image ID="Row1" Anchor="L,T" Offset="0,15" Texture="UnitPanel_SpecialActionSlot" />
        <Image ID="Row2" Anchor="L,T" Offset="0,60" Texture="UnitPanel_SpecialActionSlot" />
        <Image ID="Row3" Anchor="L,T" Offset="0,105" Texture="UnitPanel_SpecialActionSlot" />
    </Container>
</Instance>
```

```lua
-- Lua 端注册
Controls.NewInteractionGrid:ChangeParent(pContext)
Controls.NewInteractionButton:RegisterCallback(Mouse.eLClick, OnNewInteractionClicked)
-- 发送 GameEvent
UI.RequestPlayerOperation(playerID, PlayerOperations.EXECUTE_SCRIPT, {
    OnStart = "NewInteractionEvent",
    plotIndex = pPlot:GetIndex(),
    unitID = pUnit:GetID()
})
```

## 设计要点

1. **掠夺不消耗单位**：只调用 `FinishMoves` 结束移动，不杀死单位（不同于标准掠夺）
2. **奖励与掠夺量成正比**：`amount = base * progress * yield * speed`，大地块产出 = 更多奖励
3. **产出类型映射奖励类型**：食物 → 金币，生产力 → 科技，金币/科技/文化/信仰 → 同类
4. **建造者面板扩展**：通过 `ChangeParent` 注入到 UnitPanelSlide，而非 StandardActionsStack
5. **BuildInstanceForControl**：在 InstanceManager 的 slot 中嵌套子控件实例
6. **面板尺寸自适应**：`CalculateSize()` + `GetSizeX/Y()` 动态计算
7. **Reparent 刷新**：`ContextPtr:LookUpControl('/InGame/UnitPanel/UnitPanelBaseContainer'):Reparent()` 强制面板重排
8. **双角色条件互斥**：Shamare 检查战斗单位条件，Tecno 检查建造者条件，共享同一个 UI 文件但逻辑完全独立
