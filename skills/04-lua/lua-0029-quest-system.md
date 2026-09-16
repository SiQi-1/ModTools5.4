# 任务+奖励系统（来源：0029）

## 做什么
一个**数据驱动的动态任务引擎**，为每位玩家生成 1 个主线任务 + 7 个区域支线任务（对应 7 个专属区域槽位）。完成主线任务推进等级（1-6 级），完成支线任务获得区域固定增益和伟人奖励。最高等级时可刷新支线、消耗灵值强制完成。

**核心循环：** 建立宗教 → 初始化任务 → 完成任务 → 发奖励 → 升级 → 刷新更高等级任务

## 涉及文件和函数
| 文件 | 职责 |
|------|------|
| `Support/Siqi_Leaders_0029_Core.lua` | QUESTS 系统（~3300 行）+ REWARDS 系统（~300 行） |
| `Lua/Siqi_Leaders_0029_Gameplay.lua` | 初始化调用 `QUESTS:Initialize()` |
| 自定义 SQL 表: `Siqi_Leaders_0029_QUESTS` | 任务定义（Name, Description, QuestFunction, QuestFunctionValue1/2） |
| 自定义 SQL 表: `Siqi_Leaders_0029_QUEST_BINDINGS` | 任务-等级-区域绑定（Level, QuestID, DistrictType, IsMainQuest） |
| 自定义 SQL 表: `Siqi_Leaders_0029_QUEST_REWARDS` | 奖励定义（Level, RewardFunction, RewardFunctionValue1/2, Description） |

## 核心架构

### 任务等级体系
六级递增的灵值门槛和收益：

| 等级 | 灵值需求 | 主线奖励（永久%） | 支线奖励（每次+%） |
|------|---------|-----------------|-------------------|
| 1 | 1,000 | +10% | +15% |
| 2 | 2,500 | +15% | +20% |
| 3 | 8,000 | +20% | +25% |
| 4 | 20,000 | +25% | +30% |
| 5 | 50,000 | +30% | +35% |
| 6 | 100,000 | +50% | +40% |

### 任务数据结构
每个玩家通过 `Property_Quest` 存储一张表：
```lua
{
    MainQuest = QuestID,       -- 主线任务 ID
    MainReward = RewardID,     -- 主线奖励 ID（比支线高一级）
    MainHadComplete = false,   -- 是否已完成
    [1] = {quest=QID, reward=RID, HadComplete=false},  -- 区域槽位 1
    [2] = {quest=QID, reward=RID, HadComplete=false},
    -- ... 共 7 个支线槽位
}
```
辅助属性：`Property_Level`（当前等级）、`Property_Used_Quest`（已抽过的任务哈希集，防重复）

### 35 种任务类型的完整清单

#### 城市与建造类
| 函数名 | 监听事件 | 说明 |
|--------|---------|------|
| `BuildXCities` | GameEvents.CityBuilt | 建立 X 个新城市 |
| `BuildXDistricts` | Events.DistrictBuildProgressChanged | 修建 X 个区域 |
| `BuildSpecificDistrict` | Events.DistrictBuildProgressChanged | 建造指定的区域类型 |
| `BuildWonders` | Events.WonderCompleted | 完成一个奇观 |

#### 产出与经济类
| 函数名 | 监听事件 | 说明 |
|--------|---------|------|
| `CityYieldAtLeastX` | GameEvents.Siqi0029_CityYield | 拥有产出 >=X 的城市 |
| `HaveAtLeastXGold` | Events.PlayerTurnActivated | 回合开始拥有 X 金币 |
| `HaveAtLeastXGoldPerTurn` | Events.PlayerTurnActivated | 回合金 >=X |
| `HaveAtLeastXCulturePerTurn` | Events.PlayerTurnActivated | 回合文化 >=X |
| `TotalCivilizationProductionAtLeastX` | Events.PlayerTurnActivated | 总生产力 >=X |

#### 科技与文化类
| 函数名 | 监听事件 | 说明 |
|--------|---------|------|
| `CompleteSpecificTech` | Events.ResearchCompleted | 完成随机指定的科技 |
| `CompleteSpecificCivic` | Events.CivicCompleted | 完成随机指定的市政 |
| `CompleteXEurekas` | Events.TechBoostTriggered | 触发 X 次尤里卡 |
| `CompleteAnySpaceProject` | Events.CityProjectCompleted | 完成任意太空项目 |
| `UseSpecificGovernment` | GameEvents.Siqi0029_GovernmentData | 使用随机指定的政体（UI 侧判断） |

#### 军事与征服类
| 函数名 | 监听事件 | 说明 |
|--------|---------|------|
| `ConquerXCities` | GameEvents.CityConquered | 征服 X 个城市 |
| `ProduceXUnits` | Events.CityProductionCompleted | 生产 X 个单位 |
| `HealXUnitHealth` | Events.UnitDamageChanged | 治疗 X 点单位生命值 |
| `BreakCityWallsWithDiyaKe` | Events.Combat | 用迪娅可击破 X 次城墙 |
| `ConvertXUnitsWithHuangMingHu` | LuaEvents.Siqi0029_UnitConverted | 用凰茗狐转化 X 个单位 |
| `FireXIrisMissiles` | Events.WMDDetonated | 发射 X 次鸢尾花导弹 |
| `KillXUnitsWithApostle` | Events.Combat | 用使徒击杀 X 个单位 |

#### 贸易与改良类
| 函数名 | 监听事件 | 说明 |
|--------|---------|------|
| `EstablishXTradeRoutes` | Events.TradeRouteAddedToMap | 建立 X 条贸易路线 |
| `ImproveXLuxuryResources` | Events.ImprovementAddedToMap | 改良 X 个奢侈品 |
| `ImproveXTiles` | Events.ImprovementAddedToMap | 改良 X 个地块 |

#### 区域与邻接类
| 函数名 | 监听事件 | 说明 |
|--------|---------|------|
| `HaveAdjacencyBonusInDistrict` | GameEvents.Siqi0029_MaxAdjacencyBonusInDistrict | 拥有邻接加成 >=X 的区域（UI 侧判断） |
| `HaveXTilesWithAtLeastYYield` | GameEvents.Siqi0029_CityYield | 拥有产出 >=Y 的地块 X 个（UI 侧） |
| `HaveXCivilizationUniqueDistricts` | Events.DistrictBuildProgressChanged | 拥有 X 个特色区域 |

#### 宗教类
| 函数名 | 监听事件 | 说明 |
|--------|---------|------|
| `PurchaseXMissionaries` | Events.UnitAddedToMap | 购买 X 个传教士 |
| `HaveXCitiesFollowingReligion` | Events.PlayerTurnActivated | 拥有 X 座信教城市 |
| `SpendXFaith` | Events.FaithChanged | 花费 X 点信仰 |
| `HaveXHolySiteBuildings` | Events.PlayerTurnActivated | 拥有 X 个圣地建筑 |

#### 城市状态类
| 函数名 | 监听事件 | 说明 |
|--------|---------|------|
| `HaveXCitiesWithAtLeastYPopulation` | Events.PlayerTurnActivated | 拥有 >=Y 人口的城市 X 个 |
| `HaveXCitiesWithAtLeastYHousing` | Events.PlayerTurnActivated | 拥有 >=Y 住房的城市 X 个 |
| `HaveXCitiesWithAtLeastYAmenities` | Events.PlayerTurnActivated | 拥有 >=Y 宜居度的城市 X 个 |

#### 伟人与特殊类
| 函数名 | 监听事件 | 说明 |
|--------|---------|------|
| `GetGreatPerson` | Events.UnitGreatPersonCreated | 招募特定类型的伟人 |
| `GetXGreatPeople` | Events.UnitGreatPersonCreated | 招募 X 个伟人 |
| `GainXSoulPoints` | LuaEvents.Siqi0029_LingZhiChanged | 获得 X 点灵值 |
| `BecomeSuzerainOfXCityStates` | Events.PlayerTurnActivated | 成为 X 个城邦的宗主国 |
| `TrainXCivilianUnits` | Events.CityProductionCompleted | 训练 X 个平民单位 |
| `AchieveXHistoricMomentsOfAtLeast4Stars` | LuaEvents.Siqi0029_HistoricMoment | 达成 X 个 4 星以上历史时刻 |
| `CapitalCityTotalYieldAtLeastX` | Events.PlayerTurnActivated | 首都总产出 >=X |
| `CompleteXProjects` | Events.CityProjectCompleted | 完成 X 个项目 |
| `CompleteXDistrictQuests` | LuaEvents.Siqi0029_SideQuestCompleted | 完成 X 个区域任务（6 级支线） |

## 核心代码

### 任务完成流程（QUESTS:SetQuestByTypeComplete）
每次任务完成时的核心逻辑：
1. 调用 `SetQuestComplete` 或 `SetSideQuestComplete` 标记完成
2. 主线完成 → 触发 `LuaEvents.Siqi0029_MainQuestCompleted` 广播
3. 支线完成 → 触发 `LuaEvents.Siqi0029_SideQuestCompleted` 广播 + 发放伟人奖励（`Core.GiveGreatPerson`）
4. 支线完成 → 累加 `LINGZHI_PERCENTAGE_DISTRICT_SIQI_D0029_X` 属性值（每次 +15~40%）

### 任务监听建立模式（以 BuildXCities 为例）
```lua
QUESTS['BuildXCities'] = function(self, m_playerID, params)
    -- 1. 为每个任务槽位生成唯一的 Property 键
    local Property_Current_Count = 'Siqi_Leaders_0029_Quest_BuildXCities_' ..
        tostring(IsMain and 'Main' or tostring(SlotIndex))
    -- 2. 定义闭包监听函数（捕获 m_playerID）
    function m_function(playerID, cityID, cityX, cityY)
        if playerID ~= m_playerID then return; end
        -- 累加计数
        Core.ChangeProperty(pPlayer, Property_Current_Count, 1)
        if currentCount >= requiredNumber then
            self:SetQuestByTypeComplete(m_playerID, IsMain, SlotIndex) -- 标记完成
            REWARDS:GiveRewardByID(m_playerID, params.RewardID)        -- 发放奖励
            Events.xxx.Remove(m_function)                                -- 移除监听
            LuaEvents.Siqi0029_StopQuestListening.Remove(stop_listening) -- 移除停止监听
        end
    end
    Events.xxx.Add(m_function)
    -- 3. 定义停止监听函数（用于等级提升/强制停止时清理）
    function stop_listening(playerID, m_SlotIndex)
        GameEvents.CityBuilt.Remove(m_function)
        pPlayer:SetProperty(Property_Current_Count, nil) -- 清除残留
    end
    LuaEvents.Siqi0029_StopQuestListening.Add(stop_listening)
end
```

### 等级升级流程（CompleteMainQuest）
```lua
function QUESTS:CompleteMainQuest(playerID)
    LuaEvents.Siqi0029_StopQuestListening(playerID) -- 停止所有监听
    local CurrentLevel = pPlayer:GetProperty(Property_Level) or 1
    if CurrentLevel >= 6 then -- 已满级，授予首都特殊建筑
        SiqiGP.GrantBuilding(playerID, 'BUILDING_SIQI0029', capitalCityID)
        return
    end
    self:RefreshQuestData(playerID, CurrentLevel + 1) -- 刷新所有任务
    Core.ChangeProperty(pPlayer, 'LINGZHI_PERCENTAGE_MAIN_QUESTS', MainAmount) -- 永久增益
    LuaEvents.Siqi0029_MainQuestCompleted(playerID, CurrentLevel) -- 广播
end
```

### 任务随机生成（GetRandomQuestByLevel）
1. 从 `Siqi_Leaders_0029_QUEST_BINDINGS` 加载该等级的所有未使用任务
2. 主任务：选择绑定表中标记 `IsMainQuest=true` 的任务
3. 支线：80% 概率抽对应区域的专属任务，20% 概率抽通用任务（`DistrictType=nil`）
4. 用过的任务记录在 `Property_Used_Quest` 哈希集中，不会重复抽取

### 任务描述和进度（UI 数据获取）
QUESTS.GetDescription 和 QUESTS.GetProgress 两个函数表，每个任务类型注册对应函数：
- `BasicDescriptionTemplate` — 显示 "完成 X 次"（用 QuestFunctionValue1 填充）
- `DirectDescriptionTemplate` — 直接使用 LOC 文本
- `BuildSpecificDistrict` — 动态解析区域名称
- `CompleteSpecificTech` — 从 Property 中读取随机确定的目标科技名称
- `BasicProgressTemplate` — 显示 "当前值/目标值"（从 Property 读取）
- `SimpleProgressTemplate` — 显示 "0/1"

## 奖励系统 (REWARDS)

### 奖励类型
| 函数 | 参数 | 效果 |
|------|------|------|
| `GiveGold` | Value1=数量 | 加金币 |
| `GiveScience` | Value1=数量 | 加科技 |
| `GiveCulture` | Value1=数量 | 加文化 |
| `GiveFaith` | Value1=数量 | 加信仰 |
| `AttachplayerModifier` | Value1=ModifierType | 为玩家附加 Modifier（最常用） |
| `GiveLZPoints` | Value1=数量 | 加灵值 |
| `GiveStrategicResource` | Value1=数量 | 随机给一种已可见的战略资源 |
| `GiveDiplomaticFavor` | Value1=数量 | 加外交支持 |
| `GivePercentageYieldBonusToAllCities` | 无 | 随机一种产出 +% 加成到全城 |

### 奖励发放（数据驱动）
```lua
function REWARDS:GiveRewardByID(playerID, RewardID)
    local eReward = GameInfo.Siqi_Leaders_0029_QUEST_REWARDS[RewardID]
    local RewardFunction = eReward.RewardFunction
    REWARDS[RewardFunction](playerID, {
        Value1 = eReward.RewardFunctionValue1,
        Value2 = eReward.RewardFunctionValue2
    })
end
```

## GP↔UI 通信

### 事件列表
| 事件名 | 方向 | 触发时机 |
|--------|------|---------|
| `GameEvents.Siqi0029_MainQuestComplete` | UI→GP | 玩家点击完成主任务按钮 |
| `GameEvents.Siqi0029_RefreshSideQuest` | UI→GP | 玩家刷新支线（6 级） |
| `GameEvents.Siqi0029_ForceCompleteSideQuest` | UI→GP | 玩家消耗灵值强制完成支线 |
| `LuaEvents.Siqi0029_MainQuestCompleted` | GP→GP | 主任务完成广播（L1 领袖监听） |
| `LuaEvents.Siqi0029_SideQuestCompleted` | GP→GP | 支线完成广播（发放伟人） |
| `LuaEvents.Siqi0029_StopQuestListening` | GP→GP | 停止指定槽位的任务监听 |
| `GameEvents.Siqi0029_CityYield` | UI→GP | 城市产出数据广播（CityYieldAtLeastX 等任务需要） |
| `GameEvents.Siqi0029_GovernmentData` | UI→GP | 政体数据广播（UseSpecificGovernment 任务需要） |
| `GameEvents.Siqi0029_MaxAdjacencyBonusInDistrict` | UI→GP | 最大邻接加成数据广播 |
| `Game.SetProperty('Siqi_Leaders_0029_Quest_Data_Changed')` | GP→UI | 任务数据变更通知（通过 PropertyChanged 事件） |

### 核心模式：UI 请求 → GP 执行
```lua
-- UI 端
local params = { OnStart = 'Siqi0029_MainQuestComplete' }
UI.RequestPlayerOperation(playerID, PlayerOperations.EXECUTE_SCRIPT, params)

-- GP 端
GameEvents.Siqi0029_MainQuestComplete.Add(function(playerID, params)
    QUESTS:CompleteMainQuest(playerID)
end)
```

## 设计要点
1. **闭包捕获**：每个任务监听函数捕获 `m_playerID`，确保只响应目标玩家
2. **动态清理**：每个任务都配有 `stop_listening` 函数，等级升级/读档重新设置时主动销毁旧监听
3. **任务去重**：`Property_Used_Quest` 记录已分配过的任务哈希集，整个 mod 周期内不会重复
4. **区域绑定**：7 个支线槽位对应 7 个专属区域，SQL 表中通过 `DistrictType` 和 `SlotIndex` 映射
5. **渐进收益**：主线奖励的 % 乘算在灵值计算公式中，支线每完成一次就累加一次 %
6. **支线刷新**：6 级时可刷新支线（`Siqi0029_SideRefreshCount_X` 记录次数），有费用机制
7. **防双触发**：区域建成的 `DistrictBuildProgressChanged` 事件会触发两次，通过 `Last_Build` 属性去重

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `UI/Siqi_Leaders_0029_MainPanel.xml` | 任务主面板布局（Context 根） |
| `UI/Siqi_Leaders_0029_UI.xml` | 空壳 Context，用于 Include 入口（无实质控件） |

### 控件 ID 与 Lua Controls.xxx 对照

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `MainContainer` | Container | `Controls.MainContainer` | 主容器（1200x720，锚定 C,C） |
| `ScreenConsumer` | BoxButton | `Controls.ScreenConsumer` | 背景遮罩点击关闭 |
| `CloseButton` | Button | `Controls.CloseButton` | 右上角关闭按钮 |
| `ScreenTitle` | Label | — | 标题文本 |
| `TabControl` | Tab | — | 标签页切换容器 |
| `SelectTab_Tab1` | GridButton | `Controls.SelectTab_Tab1` | 任务页面标签（注册 eLClick 回调） |
| `SelectTab_Tab2` | GridButton | `Controls.SelectTab_Tab2` | 数据面板标签（注册 eLClick 回调） |
| `LeaderPortrait` | Image | `Controls.LeaderPortrait` | 领袖立绘（640x640） |
| `LZTrackerLZ` | GridButton | `Controls.LZTrackerLZ` | 灵值追踪格（含 ToolTip） |
| `LZBalance` | Label | `Controls.LZBalance` | 灵值余额数字 |
| `LZPerTurn` | Label | `Controls.LZPerTurn` | 灵值每回合数字 |
| `LZIconString` | Label | — | 灵值图标 |
| `LevelTrackerLevel` | GridButton | `Controls.LevelTrackerLevel` | 等级追踪格（含 ToolTip） |
| `LevelLabel` | Label | `Controls.LevelLabel` | 等级文本 |
| `ProgressContainer` | Container | — | 进度条容器 |
| `ProgressBar` | Bar | `Controls.ProgressBar` | 进度条（Percent 属性） |
| `ProgressLabel` | Label | — | 进度文字 |
| `Amount` | Label | `Controls.Amount` | X/Y 进度文本 |
| `SideQuestScrollPanel` | ScrollPanel | — | 支线任务滚动面板 |
| `SideQuestInnerStack` | Stack | `Controls.SideQuestInnerStack` | InstanceManager 父容器（任务槽位挂载点） |
| `Scroll` | ScrollPanel | `Controls.Scroll` | 数据面板滚动面板 |
| `Stack` | Stack | `Controls.Stack` | 数据面板主 Stack（GroupInstance / SimpleInstance 父容器） |
| `TabContainer` | Container | — | 标签内容容器 |
| `BottomButtons` | Stack | — | 顶部灵值/等级显示行 |

### Instance 模板（由 InstanceManager 动态生成）

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `SiqiQuestSlot` | 单个任务槽位 | `SiqiQuestSelect`(GridButton), `SiqiQuestIcon`(Image), `SiqiQuestTitle`(Label), `SiqiQuestDesc`(Label), `SiqiQuestStatus`(Label), `SiqiQuestCompleteButton`(GridButton) |
| `SimpleInstance` | 不可折叠行 | `Top`(Stack) |
| `GroupInstance` | 可折叠分组 | `Top`(Container), `RowHeaderButton`(GridButton), `CollapseScroll`(ScrollPanel), `ContentStack`(Stack) |
| `SiqiCityIncomeHeaderInstance` | 数据面板表头 | `Top`(Container) — 6 列 Label |
| `SiqiCityIncomeLineItemInstance` | 数据面板行项 | `LineItemName`(Label), `DistrictIcon`(Image), `BaseYield`(Label), `SpecificPercentBonus`(Label), `GeneralPercentBonus`(Label), `FinalYield`(Label) |
| `SiqiCityIncomeInstance` | 城市收入行 | `CityName`(Label), `LineItemStack`(Stack), 以及 4 个产出 Label |
| `SiqiCityIncomeTotalInstance` | 收入总计行 | `TotalBaseYield`, `TotalSpecificPercentBonus`, `TotalGeneralPercentBonus`, `TotalFinalYield` |
| `SiqiLaunchBarItem` | 工具栏按钮 | `LaunchItemButton`(Button), `LaunchItemIcon`(Image) |
| `SiqiLaunchBarPinInstance` | 工具栏图钉 | `Pin`(Image) |

### 控件父子关系挂载模式

```lua
-- InstanceManager 模板名必须匹配 XML 中的 <Instance Name="...">
local m_QuestPanelIM = InstanceManager:new("SiqiQuestSlot", "Top", Controls.SideQuestInnerStack)

-- 获取动态实例后，子控件通过实例对象引用（不是 Controls.xxx）
local instance = m_QuestPanelIM:GetInstance()
instance.SiqiQuestIcon:SetIcon("ICON_...")    -- 子控件 ID
instance.SiqiQuestTitle:SetText("...")
instance.SiqiQuestCompleteButton:RegisterCallback(Mouse.eLClick, handler)
```

### 添加新控件模板

```xml
<!-- 在 MainContainer 内或其他 Container 内添加 -->
<Grid ID="SiqiNewFeaturePanel" Anchor="C,C" Size="400,300" 
      Texture="Controls_ContainerBlue" SliceCorner="3,3" SliceSize="9,9" SliceTextureSize="16,16">
    <Label ID="SiqiNewFeatureTitle" Anchor="C,T" Offset="0,10" 
           Style="FontFlair16" String="LOC_NEW_FEATURE_TITLE"/>
    <Button ID="SiqiNewFeatureButton" Anchor="C,B" Offset="0,20" 
            Size="120,40" Texture="Controls_Confirm" String="LOC_CONFIRM"/>
</Grid>
```

```lua
-- Lua 端对应
Controls.SiqiNewFeatureButton:RegisterCallback(Mouse.eLClick, OnNewFeatureClicked)
Controls.SiqiNewFeatureTitle:SetText(Locale.Lookup("LOC_NEW_FEATURE_TITLE"))
```
