# lua-workshop-top-panel-extension — 顶部面板扩展模式

从工坊 Mod TopPanelPro (2997927787) 提炼。在标准顶部面板基础上扩展额外的产量/资源条目，不替换整个 TopPanel 文件，而是覆盖关键函数。

---

## 快速索引

| 技术点 | 说明 |
|--------|------|
| **文件覆盖链** | 逐级 include 找到实际 BaseFile，然后覆盖 `RefreshYields()` / `LateInitialize()` |
| **产量按钮创建** | 使用 `m_YieldButtonDoubleManager:GetInstance()` 创建产量条目 |
| **Tooltip 系统** | XML 定义 `ToolTipType` + Lua 用 `TTManager:GetTypeControlTable()` 获取 |
| **团队资源可见性** | 遍历队友，检查 `pPlayerResources:IsResourceVisible()` |

---

## 一、核心架构：覆盖链

### 1.1 找到 Base 文件（兼容多版本 DLC）

```lua
-- ===========================================================================
-- 逐级 include，找到实际存在的 TopPanel 基本文件
-- ===========================================================================
local files = {
    "TopPanel_Expansion2",   -- GS
    "TopPanel_Expansion1",   -- R&F
    "TopPanel",              -- Vanilla
}

local BaseFile = ""

for _, file in ipairs(files) do
    include(file)
    if Initialize then
        print("Loading " .. file .. " as base file");
        BaseFile = file
        break
    end
end
```

### 1.2 保存 Base 函数引用 + 覆盖

```lua
-- 保存原始函数
TPE_BASE_RefreshYields = RefreshYields;
TPT_BASE_LateInitialize = LateInitialize;

-- ===========================================================================
-- 覆盖 RefreshYields：先调原始，再追加自定义
-- ===========================================================================
function RefreshYields()
    TPE_BASE_RefreshYields();      -- 先执行原始产量刷新

    RefreshFood()                  -- 追加：食物
    RefreshProduction()            -- 追加：生产力
    RefreshPopulation()            -- 追加：人口
    RefreshLuxuryResourcesType()   -- 追加：奢侈品

    -- 重新计算布局
    Controls.YieldStack:CalculateSize();
    Controls.StaticInfoStack:CalculateSize();
    Controls.InfoStack:CalculateSize();
end

-- ===========================================================================
-- 覆盖 LateInitialize：先调原始，再注册新事件
-- ===========================================================================
function LateInitialize()
    TPT_BASE_LateInitialize()

    Events.ResearchCompleted.Add(GetTeamVisibleResources);
    Events.CivicCompleted.Add(GetTeamVisibleResources);

    -- [可选] 检测 FFA 模式（无队伍时每人 ID=TeamID）
    for j, playerID in ipairs(PlayerManager.GetAliveMajorIDs()) do
        if Players[playerID]:GetTeam() ~= playerID then
            IsFFA = false
        end
    end
end
```

---

## 二、产量按钮：用 InstanceManager 创建

### 2.1 双行产量按钮（DoubleManager）

用于需要显示"当前值 + 每回合变化"的条目（如食物、人口）。

```lua
local m_FoodYieldButton = nil

function RefreshFood()
    -- 只创建一次，后续复用（类似单例）
    m_FoodYieldButton = m_FoodYieldButton or m_YieldButtonDoubleManager:GetInstance();

    -- 汇总城市数据
    local pTotalFood = 0
    local pTotalFoodSurplus = 0
    local pPlayerCities = Players[Game.GetLocalPlayer()]:GetCities()

    for i, pCity in pPlayerCities:Members() do
        local pCityFood = pCity:GetYield(YieldTypes.Food)
        local pFoodSurplus, growthModifier = GetFoodSurplus(pCity)

        pTotalFood = pTotalFood + pCityFood
        pTotalFoodSurplus = pTotalFoodSurplus + pFoodSurplus

        -- 收集城市粒度数据（供 Tooltip 使用）
        local kdate = {
            CityName = Locale.Lookup(pCity:GetName()),
            CityFood = pCityFood,
            FoodSurplus = pFoodSurplus,
            GrowthModifier = growthModifier,
        }
        table.insert(Food_Info.CitysInfo, kdate)
    end

    -- 设置图标、数值、颜色、Tooltip
    m_FoodYieldButton.YieldIconString:SetText("[ICON_FoodLarge]")
    m_FoodYieldButton.YieldPerTurn:SetColorByName("ResFoodLabelCS")
    m_FoodYieldButton.YieldPerTurn:SetText(Locale.ToNumber(pTotalFoodSurplus, "+#####.#;-#####.#"))
    m_FoodYieldButton.YieldBalance:SetText(Locale.ToNumber(pTotalFood, "#####.#"));
    m_FoodYieldButton.YieldBalance:SetColorByName("ResFoodLabelCS");
    m_FoodYieldButton.YieldBacking:SetToolTipType("TooltipType_TopPanel_Food")
    m_FoodYieldButton.YieldBacking:SetColorByName("ResFoodLabelCS")

    -- Tooltip 回调（延迟刷新，避免每帧重建）
    m_FoodYieldButton.YieldBacking:ClearToolTipCallback()
    m_FoodYieldButton.YieldBacking:SetToolTipCallback(
        function()
            if CanRefresh then
                LuaEvents.TopPanelToolTip_Food_Refresh(Food_Info)
                CanRefresh = false
            end
        end
    );

    m_FoodYieldButton.YieldButtonStack:CalculateSize()
end
```

### 2.2 单行产量按钮（SingleManager）

用于只需要显示"总计值"的条目（如生产力、奢侈品）。

```lua
local m_ProductionYieldButton = nil

function RefreshProduction()
    m_ProductionYieldButton = m_ProductionYieldButton or m_YieldButtonSingleManager:GetInstance()

    -- ... 汇总逻辑 ...

    m_ProductionYieldButton.YieldIconString:SetText("[ICON_ProductionLarge]")
    m_ProductionYieldButton.YieldPerTurn:SetText(Locale.ToNumber(pTotalProduction, "+#####.#;-#####.#"))
    m_ProductionYieldButton.YieldPerTurn:SetColorByName("ResProductionLabelCS")
    m_ProductionYieldButton.YieldBacking:SetColorByName("ChatMessage_Whisper")
    m_ProductionYieldButton.YieldBacking:SetToolTipType("TooltipType_TopPanel_Production")
    m_ProductionYieldButton.YieldBacking:ClearToolTipCallback()
    m_ProductionYieldButton.YieldBacking:SetToolTipCallback(function()
        if CanRefresh then
            LuaEvents.TopPanelToolTip_Production_Refresh(Production_Info)
            CanRefresh = false
        end
    end);
    m_ProductionYieldButton.YieldButtonStack:CalculateSize()
end
```

### 2.3 InstanceManager 类型对照

| Manager 变量 | 行数 | 字段 |
|-------------|------|------|
| `m_YieldButtonDoubleManager` | 2 行（图标+数字行 / 变化行） | `YieldIconString`, `YieldBalance`, `YieldPerTurn`, `YieldBacking` |
| `m_YieldButtonSingleManager` | 1 行（图标+数字） | `YieldIconString`, `YieldPerTurn`, `YieldBacking` |

---

## 三、Tooltip 系统：TTManager + InstanceManager

### 3.1 XML 定义 ToolTipType

创建独立 XML 文件（如 `TopPanel_TT.xml`），包含 3 部分：

```xml
<?xml version="1.0" encoding="utf-8" ?>
<Context>
    <!-- Part 1: ToolTipType — 悬浮窗的外层结构 -->
    <ToolTipType Name="TooltipType_TopPanel_Production">
        <Grid ID="BG" SliceCorner="10,10" SliceTextureSize="33,32"
              Texture="Controls_Tooltip" AutoSize="1"
              InnerPadding="25,25" InnerOffset="10,10"
              Color="255,255,255,255" Anchor="L,T">
            <Stack Offset="0,0" StackGrowth="Down" Anchor="C,T">
                <Label ID="Production_Header" Anchor="C,T"
                       Style="FontFlair18" Color="5,29,51,255"
                       SmallCaps="20" SmallCapsType="EveryWord" Offset="0,8"/>
                <Stack ID="TopPanel_Production_Citys_Stack"
                       StackGrowth="Down" Anchor="C,T" Offset="2,10" Padding="-6"/>
                <Box Size="240,8" Color="0,0,0,0" Anchor="C,T"/>
            </Stack>
        </Grid>
    </ToolTipType>

    <!-- Part 2: Instance — Tooltip 内每行的模板 -->
    <Instance Name="TopPanel_ProductionInstance">
        <Grid ID="BG" Size="auto,auto"
              SliceCorner="10,10" SliceTextureSize="33,32"
              Texture="Controls_Tooltip" MinSize="220,45"
              InnerPadding="25,25" Anchor="L,C" InnerOffset="10,10"
              Color="255,255,255,50">
            <Label ID="CityName" Anchor="L,C" Offset="0,2" Size="126,16" Style="FontFlair16" Color="5,29,51,255" TruncateWidth="127" String="$CityName$"/>
            <Label ID="CityProduction" Anchor="R,C" Offset="0,2" Style="FontNormalMedium16" Color0="5,29,51,255" Color1="0,0,0,50" FontStyle="Shadow" LeadingOffset="2" KerningAdjustment="1" String="$987$"/>
        </Grid>
    </Instance>

    <!-- Part 3: 更多 ToolTipType + Instance（重复以上结构） -->
</Context>
```

### 3.2 Lua 绑定 Tooltip

```lua
include("InstanceManager");

local m_TPT_TopPanel_Production_TT = {}
local m_TPT_TopPanel_Food_TT = {}
local m_TPT_TopPanel_Population_TT = {}

-- ===========================================================================
-- Tooltip 刷新函数（由 LuaEvents 触发）
-- ===========================================================================
function OnTopPanelToolTip_Production_Refresh(Production_Info)
    m_TPT_TopPanel_Production_TT.Production_Header:SetText(
        Locale.Lookup("LOC_TOPPANEL_PRODUCTION_TOOLTIP_HEADER",
                      Production_Info.TotalProduction))

    -- 清空旧实例
    m_TPT_TopPanel_Production_TT.TopPanel_Production_Citys_Stack:DestroyAllChildren()

    -- 懒创建 InstanceManager
    if m_TPT_TopPanel_Production_TT.IM == nil then
        m_TPT_TopPanel_Production_TT.IM = InstanceManager:new(
            "TopPanel_ProductionInstance", "BG",
            m_TPT_TopPanel_Production_TT.TopPanel_Production_Citys_Stack)
    end

    -- 填充数据
    for i, kdate in ipairs(Production_Info.CitysInfo) do
        local tInstance = m_TPT_TopPanel_Production_TT.IM:GetInstance()
        tInstance.CityName:SetText(kdate.CityName)
        tInstance.CityProduction:SetText(
            Locale.ToNumber(kdate.CityProduction,
                            "+#####.#[icon_Production]"))
    end

    m_TPT_TopPanel_Production_TT.TopPanel_Production_Citys_Stack:CalculateSize();
    m_TPT_TopPanel_Production_TT.MainStack:CalculateSize();
end

-- ===========================================================================
-- Initialize: 用 TTManager 获取 ToolTip 控件表 + 绑定 LuaEvents
-- ===========================================================================
function Initialize()
    TTManager:GetTypeControlTable("TooltipType_TopPanel_Production",
                                   m_TPT_TopPanel_Production_TT)
    TTManager:GetTypeControlTable("TooltipType_TopPanel_Food",
                                   m_TPT_TopPanel_Food_TT)
    TTManager:GetTypeControlTable("TooltipType_TopPanel_Population",
                                   m_TPT_TopPanel_Population_TT)

    LuaEvents.TopPanelToolTip_Production_Refresh.Add(
        OnTopPanelToolTip_Production_Refresh)
    LuaEvents.TopPanelToolTip_Food_Refresh.Add(
        OnTopPanelToolTip_Food_Refresh)
    LuaEvents.TopPanelToolTip_Population_Refresh.Add(
        OnTopPanelToolTip_Population_Refresh)
end
Initialize();
```

### 3.3 Tooltip 回调流程

```
RefreshYields()
  └→ m_FoodYieldButton.YieldBacking:SetToolTipType("TooltipType_TopPanel_Food")
  └→ SetToolTipCallback(function()
        LuaEvents.TopPanelToolTip_Food_Refresh(Food_Info)
     end)
           │
           ▼
OnTopPanelToolTip_Food_Refresh(Food_Info)
  └→ 通过 TTManager:GetTypeControlTable() 获得的控件表
  └→ InstanceManager:new("TopPanel_FoodInstance", ...):GetInstance()
  └→ 填充每行数据
```

---

## 四、团队资源可见性

### 4.1 遍历队友检查资源解锁

```lua
local g_TeamVisibleResources = {};

function GetTeamVisibleResources(playerID)
    -- 判断是队友（或自己）
    if Players[Game.GetLocalPlayer()]:GetTeam() == Players[playerID]:GetTeam()
       or playerID == Game.GetLocalPlayer() then
        local pPlayerResources = Players[playerID]:GetResources();
        for i, kdate in ipairs(g_TopPanelResources) do
            if pPlayerResources:IsResourceVisible(kdate.Hash) then
                g_TeamVisibleResources[kdate.Index] = true
            end
        end
    end
end
```

### 4.2 队友多余资源统计

```lua
function GetMoreLUXURYstr(playerID)
    local pPlayerResources = Players[playerID]:GetResources()
    local More = false
    local LUXURYstr = ""

    for resource in GameInfo.Resources() do
        if resource.ResourceClassType == "RESOURCECLASS_LUXURY" then
            local amount = pPlayerResources:GetResourceAmount(resource.ResourceType)
            if amount > 1 and IsNewLuxury(resource) then
                -- 检查该资源是否可以被交易给本地玩家
                if PopulateAvailableResources(playerID, resource) then
                    More = true
                    LUXURYstr = LUXURYstr
                        .. "[NEWLINE][ICON_"..resource.ResourceType.."] "
                        .. Locale.Lookup(resource.Name)
                end
            end
        end
    end

    if More then return LUXURYstr else return false end
end

-- 判断队友的资源是否可交易给己方
function PopulateAvailableResources(otherPlayerID, Resource)
    local localPlayerID = Game.GetLocalPlayer()
    local pForDeal = DealManager.GetWorkingDeal(
        DealDirection.OUTGOING, localPlayerID, otherPlayerID);
    local possibleResources = DealManager.GetPossibleDealItems(
        otherPlayerID, localPlayerID, DealItemTypes.RESOURCES, pForDeal);
    if possibleResources ~= nil then
        for i, entry in ipairs(possibleResources) do
            local resourceDesc = GameInfo.Resources[entry.ForType];
            if resourceDesc == Resource and entry.MaxAmount > 1 then
                return true
            end
        end
    end
    return false
end
```

---

## 五、Override 完整 RefreshResources（仅 GS 版）

对于需要完全改造战略资源显示的 Mod，可以覆盖整个 `RefreshResources()`。

```lua
if BaseFile == "TopPanel_Expansion2" then
    function RefreshResources()
        -- [完全重写，同 Orig 文件逻辑，额外加入团队资源显示]
        -- ...

        -- 关键改动：在 Tooltip 末尾追加团队战略资源信息
        local TeamStrategicYtext = Locale.Lookup("LOC_TOP_PANEL_TEAM_MORE_STRATEGIC_NAME")
        local TeamMore = false
        for j, playerID in ipairs(PlayerManager.GetAliveMajorIDs()) do
            if Players[Game.GetLocalPlayer()]:GetTeam() == Players[playerID]:GetTeam()
               and Game.GetLocalPlayer() ~= playerID then
                local Strategicstr = GetMoreStrategicstr(playerID, resource)
                if Strategicstr ~= 0 then
                    TeamMore = true
                    TeamStrategicYtext = TeamStrategicYtext..Strategicstr
                end
            end
        end
        if TeamMore == true and isStrategicsTradingAllowed == true then
            tooltip = tooltip .. "[NEWLINE]" .. TeamStrategicYtext
        end
    end
end
```

---

## 六、文本定义

```xml
<LocalizedText>
    <Replace Tag="LOC_TPT_TOP_PANEL_LUXURY_RESOURCES" Language="zh_Hans_CN">
        <Text>[ICON_RESOURCE_TOYS] 拥有的奢侈品: ({1_Type} 种类)</Text>
    </Replace>
    <Replace Tag="LOC_TOP_PANEL_MORE_LUXURY_NAME" Language="zh_Hans_CN">
        <Text>[NEWLINE][NEWLINE]自己的额外奢侈品[NEWLINE]</Text>
    </Replace>
    <Replace Tag="LOC_TOP_PANEL_TEAM_MORE_LUXURY_NAME" Language="zh_Hans_CN">
        <Text>[NEWLINE][NEWLINE]其他玩家的重复奢侈品</Text>
    </Replace>
    <Replace Tag="LOC_TOPPANEL_PRODUCTION_TOOLTIP_HEADER" Language="zh_Hans_CN">
        <Text>+{1_Num} [Icon_ProductionLarge] 生产力</Text>
    </Replace>
    <Replace Tag="LOC_TOPPANEL_FOOD_TOOLTIP_HEADER" Language="zh_Hans_CN">
        <Text>+{1_Num} [Icon_FoodLarge] 食物</Text>
    </Replace>
    <Replace Tag="LOC_TOPPANEL_POPULATION_TOOLTIP_HEADER" Language="zh_Hans_CN">
        <Text>{1_Num} [Icon_Citizen] 人口</Text>
    </Replace>
</LocalizedText>
```

---

## 七、关键要点速查

### 7.1 覆盖 vs 替换

| 策略 | 适用场景 | 风险 |
|------|---------|------|
| 覆盖函数（推荐） | 追加功能，不改变原有逻辑 | 低，base 更新影响小 |
| 替换整个文件 | 完全自定义 TopPanel | 高，需随游戏版本维护 |

### 7.2 核心 Lua API

| API | 用途 |
|-----|------|
| `m_YieldButtonDoubleManager:GetInstance()` | 创建双行产量条目 |
| `m_YieldButtonSingleManager:GetInstance()` | 创建单行产量条目 |
| `yieldButton.YieldBacking:SetToolTipType(name)` | 绑定 XML ToolTipType |
| `yieldButton.YieldBacking:SetToolTipCallback(fn)` | 设置悬浮回调 |
| `TTManager:GetTypeControlTable(name, tbl)` | 获取 ToolTip 的控件表 |
| `InstanceManager:new(name, rootName, parent)` | 创建 Tooltip 行实例 |
| `Locale.ToNumber(value, format)` | 格式化数字显示 |

### 7.3 文件结构

```
Mod/
└── TPE/
    ├── BaseText.xml              -- 旧版 EnglishText 兼容
    ├── TopPanel_Text.xml         -- LocalizedText 多语言
    └── UI/
        ├── TopPanelExtension.lua -- 主逻辑（覆盖刷新函数）
        ├── TopPanel_TT.lua       -- Tooltip 填充逻辑
        └── TopPanel_TT.xml       -- Tooltip 结构 + Instance 模板
```

---

## XML 配合

### XML 文件

| 文件 | 路径 | 角色 |
|------|------|------|
| Tooltip 布局 | `TPE/UI/TopPanel_TT.xml` | 自定义 Tooltip 结构 + Instance 模板 |

TopPanelExtension 本身不提供独立 XML——它通过 `LookUpControl` 注入到游戏原版 TopPanel 的现有控件树中。但自定义 Tooltip 需要独立的 XML。

### TooltipType 体系

| ToolTipType Name | 对应产量 | 子 Stack |
|-----------------|---------|---------|
| `TooltipType_TopPanel_Production` | 生产力 | `TopPanel_Production_Citys_Stack` |
| `TooltipType_TopPanel_Food` | 食物 | `TopPanel_Food_Citys_Stack` |
| `TooltipType_TopPanel_Population` | 人口 | `TopPanel_Population_Citys_Stack` |

### Instance 对照表

| Instance Name | 绑定 ToolTipType | 子控件 |
|--------------|-----------------|--------|
| `TopPanel_ProductionInstance` | `TooltipType_TopPanel_Production` | `BG` -> `CityName`, `CityProduction` |
| `TopPanel_FoodInstance` | `TooltipType_TopPanel_Food` | `BG` -> `BGStack` -> `PantheonBannerIconContainer`(CitizenGrowthStatus), `CityName`, `GrowthModifier`, `Food`, `FoodSurplus` |
| `TopPanel_PopulationInstance` | `TooltipType_TopPanel_Population` | `BG` -> `BGStack` -> `PantheonBannerIconContainer`(CitizenIcon+Population), `CityName`, `YieldModifier`, `House`, `Amenity` |

### Lua 绑定流程

```
Initialize: TTManager 获取 Tooltip 控件表
  -> TTManager:GetTypeControlTable("TooltipType_TopPanel_Production", m_TT)
RefreshYields: 按钮绑定 TooltipType
  -> button.YieldBacking:SetToolTipType("TooltipType_TopPanel_Production")
Tooltip 回调: 触发 LuaEvents
  -> button.YieldBacking:SetToolTipCallback(function()
       LuaEvents.TopPanelToolTip_Production_Refresh(data)
     end)
回调函数: InstanceManager 填充行
  -> m_TT.IM = InstanceManager:new("TopPanel_ProductionInstance", "BG", m_TT.Stack)
  -> local inst = m_TT.IM:GetInstance()
  -> inst.CityName:SetText(...)
```