# 热度直播打赏系统（来源：13.0）

## 做什么
实现一个完整的热度 → 直播 → 打赏/事件系统。玩家每回合积累"热度值"，热度分为 6 个等级（0-5），等级越高越容易刷出高级随机奖励。通过"主播U"单位对城市进行直播，触发 66 种随机奖励/事件（金币、资源、单位、城市转移、灾难等），并渲染带模拟弹幕的直播面板。

## 涉及文件

| 文件 | 角色 |
|------|------|
| `Scripts/Arknights_Cute_Leaders_13.0_Scripts.lua` | GP 端：热度累计、等级阈值、奖励分发、事件注册 |
| `Scripts/Arknights_Cute_Leaders_13.0_Reward.lua` | GP 端：66 个奖励/事件函数 + 随机数值计算 + 灾难/掠夺系统（1080行） |
| `UI/Arknights_Cute_Leaders_13.0_UI.lua` | UI 端：单位面板按钮控制（何时显示/启用） |
| `UI/Arknights_Cute_Leaders_13.0_Button.lua` | UI 端：LaunchBar 入口按钮 + 领袖过滤 |
| `UI/Arknights_Cute_Leaders_13.0_Panel.lua` | UI 端：直播面板（模拟弹幕、热度显示、打赏列表、时间驱动刷新） |
| `UI/Arknights_Cute_Leaders_13.0_Popup.lua` | UI 端：确认弹窗（展示直播结果摘要） |

## 架构全景

```
热度累计（GP: Scripts.lua）
  ├── PlayerTurnActivated → 随机 +1%~10% 热度
  ├── ImprovementAddedToMap → 建造直播间 +15%
  └── SiqiUOfficalOnButtonClicked → 直播后热度结算
        ↓
等级判定：AI_classify_num(NowHot) → 0~5 级
        ↓
打赏/事件分发：Siqi_Reward_Or_Event(playerID, NowHot)
  ├── 打赏：等级+1 次，每次按概率表选 RewardLevel → 随机 RewardID
  └── 事件：30%概率触发，按概率表选 EventLevel → 随机 EventID
        ↓
执行效果：Reward.lua 的 66 个 Siqi_Function[N]
  ├── Siqi_Function[1~36]   打赏（正面效果）
  └── Siqi_Function[37~66]  事件（负面效果）
        ↓
文本存储：Player Property "SIQI_U_OFFICAL_REWARD_STRING"
        ↓
面板渲染：Panel.lua 每 N 秒刷新弹幕 + 打赏列表
  └── 弹幕速度随热度等级加快（6级每30秒刷新）
```

## 一、热度系统

### 等级阈值

```lua
-- 对数型阈值：100 → 1000 → 10000 → 100000 → 1000000
function AI_classify_num(n)
    if n < 100 then return 0
    elseif n < 1000 then return 1
    elseif n < 10000 then return 2
    elseif n < 100000 then return 3
    elseif n < 1000000 then return 4
    else return 5 end
end
```

### 热度修改 API

```lua
-- 绝对增减（最小+1，最大+1000000）
Siqi_ChangePlayerHot(playerID, HotChange)

-- 按比例增减（基于当前热度的百分比）
Siqi_ChangePlayerHotByPercent(playerID, Percent)

-- 热度存储：pPlayer:GetProperty('SiqiUOfficalHot')
```

### 等级突破机制

每次热度越过 10^n 阈值时，为 [直播间改良] 附加额外的 Modifier：

```lua
function Siqi_SetPlayerModifier(playerID)
    -- 当前热度 ≥ 需求热度 (ShouldHot) 时
    pPlayer:AttachModifierByID('MODIFIER_SIQI_U_OFFICAL_ADJUST_PLOT_YIELD_IF_IMPROVEMENT_YIELD_CULTURE')
    pPlayer:AttachModifierByID('MODIFIER_SIQI_U_OFFICAL_ADJUST_PLOT_YIELD_IF_IMPROVEMENT_YIELD_PRODUCTION')
    ShouldHot = ShouldHot * 10  -- 下一级阈值 ×10
end
```

## 二、奖励/事件概率引擎

### 概率表（基于热度等级）

```lua
Siqi_ULKRewardProbability = {
    [0] = { 60, 25, 10, 5, 0, 0 },  -- 60%获得0级奖励, 25%获得1级...
    [1] = { 50, 25, 10, 10, 5, 0 },
    [2] = { 35, 30, 15, 10, 5, 5 },
    [3] = { 20, 25, 30, 15, 5, 5 },
    [4] = { 5, 15, 30, 25, 15, 10 },
    [5] = { 0, 5, 20, 30, 25, 20 }
}

-- 使用：按累积概率判定返回等级 0~5
function Siqi_GetRewardOrEventLevel(HotLevel)
    randNum = 1~100
    for i, prob in ipairs(probabilities) do
        cumulative += prob
        if randNum <= cumulative then return i-1 end
    end
end
```

### 奖励/事件 ID 表（SQL 驱动）

```lua
-- 初始化时从 SQL 按 MinLevel 过滤加载
for i = 0, 5 do
    Siqi_ULKReward[i] = DB.Query("SELECT * FROM Siqi_ULKReward WHERE MinLevel <= "..i.." AND IsBadEvent = 0")
    Siqi_ULKEvent[i]  = DB.Query("SELECT * FROM Siqi_ULKReward WHERE MinLevel <= "..i.." AND IsBadEvent = 1")
end
```

## 三、66 个奖励/事件函数综述

### 打赏函数 (Siqi_Function[1]~[36])

| 编号 | 效果 | 数值公式 | 作用对象 |
|------|------|---------|---------|
| 1 | +金币 | `Siqi_GetRandNumber(6-level, level, 50%)` | 玩家 |
| 2 | +信仰 | `Siqi_GetRandNumber(4/(level+1), level, 30%)` | 玩家 |
| 3 | +科技进度 | `Siqi_GetRandNumber(1, level, 10+level*10%)` | 玩家 |
| 4 | +文化进度 | `Siqi_GetRandNumber(1, level, 10+level*10%)` | 玩家 |
| 5 | +城市人口 | `level` 座城市各+1 | 随机城市 |
| 6 | +城市生产力 | `Siqi_GetRandNumber(1/(level+1), level, 30%)` 直接 AddProgress | 随机城市 |
| 7~12 | 城市产出%加成 | `Siqi_GetRandNumber2(1, level, 30%)` | 随机城市 |
| 13~18 | 城市产出固定加成 | `Siqi_GetRandNumber2(0.2, level, 20%)` | 随机城市 |
| 19 | +随机尤里卡 | `level-1` 个 | 玩家 |
| 20 | +随机鼓舞 | `level-1` 个 | 玩家 |
| 21 | +随机科技 | `level-2` 个 | 玩家 |
| 22 | +随机市政 | `level-2` 个 | 玩家 |
| 23 | +随机伟人点数 | `Siqi_GetRandNumber(0.6, level, 20%)` × 随机伟人类别 | 玩家 |
| 24 | 偷取随机领袖金币 | 全额转移 | 随机非战争领袖→玩家 |
| 25 | +使者 | `level-1` 个 | 玩家 |
| 26 | +影响力/回合 | `level` 层 Modifier | 玩家 |
| 27 | +开拓者 | `level-2` 座城市各1 | 随机城市 |
| 28 | +建造者 | `level-2` 座城市各1 | 随机城市 |
| 29 | +随机时代军事单位 | 在首都生成 | 首都 |
| 30 | +总督头衔 | `level-2` 个 | 玩家 |
| 31 | 夺取某文明某城市 | CityManager.TransferCity | 随机非战争领袖→玩家 |
| 32 | +城市忠诚度 | 二进制分块附加 Modifier（1/2/4/8 累加） | 1座城市 |
| 33 | +额外区域位 | 每城1层 Modifier | 随机城市 |
| 34 | 秒生产 | FinishProgress | 1-2座城市 |
| 35 | +单位移动力 | ChangeExtraMoves(+1) | 随机单位 |
| 36 | +单位战斗力 | SetProperty + Ability 双保险 | 随机战斗单位 |

### 事件函数 (Siqi_Function[37]~[66])

| 编号 | 效果 | 数量 | 作用对象 |
|------|------|------|---------|
| 37~40 | -金币/信仰/科技/文化 | 波动减扣 | 玩家 |
| 41 | -城市人口 | `level` 座城市各-1 | 随机城市 |
| 42 | -城市生产力 | AddProgress(-amount) | 随机城市 |
| 43~48 | 城市产出%减成 | 负值 | 随机城市 |
| 49~54 | 城市产出固定减成 | 负值 | 随机城市 |
| 55 | 随机单位死亡 | UnitManager.Kill | 随机单位 |
| 56 | 随机城市叛乱 | TransferCityToFreeCities（40%概率降级为-金币） | 1-2座城市 |
| 57 | 随机城市毁灭 | DestroyCity（60%概率降级为-金币） | 1座城市 |
| 58 | 城市随机灾难 | 森林火灾/丛林火灾/火山/洪水（根据地形特征） | 1-4座城市 |
| 59 | 随机范围掠夺 | 城市周围2格全掠夺（改良+区域+建筑） | 1-4座城市 |
| 60 | 随机尤里卡清空 | SetResearchProgress(0) | 1-3个科技 |
| 61 | 随机鼓舞清空 | SetCulturalProgress(0) | 1-3个市政 |
| 62 | 城市出现蛮子 | 1-5个随机时代单位 | 随机城市 |
| 63 | 城市破坏 | 城市中心 ChangeDamage | 1-3座城市 |
| 64 | -单位战斗力 | SetProperty 负值 | 随机战斗单位 |
| 65 | -单位移动力 | ChangeExtraMoves(-1) | 1-3个单位 |
| 66 | -城市忠诚度 | 二进制分块附加负面 Modifier | 1座城市 |

### 数值波动机制

两种基础数值表：
```lua
-- 非线性（前中期收益大）
RewardAmount  = { [0]=20, [1]=80, [2]=160, [3]=480, [4]=960, [5]=1920 }
-- 线性
RewardAmount2 = { [0]=10, [1]=20, [2]=30, [3]=40, [4]=50, [5]=60 }

-- 带波动的数值计算
Siqi_GetRandNumber(multiplier, level, ChangePercent)
  → amount = RewardAmount[level] * multiplier * GAME_SPEED_MULTIPLIER
  → 随机波动 ±ChangePercent%
```

## 四、直播流程（UI → GP 多步通信）

### 完整链路

```
1. 单位面板按钮 (UI.lua)
   │  OnUnitMoveComplete / OnUnitSelectionChanged → Refresh()
   │  检查：是 UNIT_STREAMER_U + 有剩余移动力 + 这座城市是首次直播
   │  → Controls.SiqiUOfficalButton 显示在单位面板
   │
2. 按钮点击 (UI.lua → Popup.lua)
   │  OnButtonClickedSiqiUOffical:
   │  → 随机判定：To 事件(45%) / From 事件(40%) / 灾害(40%) / 奖励等级
   │  → 10%概率单位死亡
   │  → LuaEvents.SiqiUOfficalButtonPopupDialog(params) → 弹出确认窗口
   │  → UI.RequestPlayerOperation(ownerID, EXECUTE_SCRIPT, params)
   │
3. GP 执行 (Scripts.lua)
   │  GameEvents.SiqiUOfficalOnButtonClicked
   │  → 根据判定结果增减热度
   │  → LuaEvents.SiqiUOfficalAddReward 执行打赏/事件
   │  → 单位 Kill 或 FinishMoves + 记录直播城市列表
   │
4. 面板渲染 (Panel.lua)
   │  每 N 秒 TimeRefresh → Refresh()
   │  → 读取 Player Property "SIQI_U_OFFICAL_REWARD_STRING"
   │  → 弹幕：AI_getChatTextByHotLevel → 随热度变更聊天文本类型
   │  → 打赏列表：InstanceManager 逐条渲染
```

### 按钮显示/启用逻辑

```lua
-- 隐藏条件：不是 UNIT_STREAMER_U、不在城市上、无剩余移动力
function IsButtonHide(pUnit)
    if unitType ~= 'UNIT_STREAMER_U' then return true end
    if Cities.GetPlotPurchaseCity(pPlot) == nil then return true end
    if pUnit:GetMovementMovesRemaining() == 0 then return true end
    return false
end

-- 禁用条件：这个城市已经直播过
function IsButtonDisabled(pUnit)
    local HadLiveCity = pUnit:GetProperty('SiqiUOfficalIsFrist') or {}
    for _, v in pairs(HadLiveCity) do
        if v.X == CityX and v.Y == CityY then
            return true, "这座城市已经直播过了"  -- 禁用+提示
        end
    end
    return false, "可直播"
end
```

## 五、模拟弹幕系统

### 聊天文本等级

SQL 表 `Siqi_AvatarChat` 按 `ChatType` 分为 5 类：
- Type 0: 路人发言（低热主要）
- Type 1-2: 中等互动
- Type 3: 小黑子文本（从 InitialPreferenceLevel=0 的头像池选）
- Type 4: 特殊文本（绑定特定头像）

### 热度驱动的文本比例

```lua
Siqi_ULKChatProbability = {
    [0] = { 50, 30, 15, 5, 0 },   -- 热低：多为路人
    [5] = { 10, 35, 30, 15, 10 }   -- 热高：大量互动+特殊文本
}
```

### 刷新节奏随热度变化

```lua
-- ShowULKWindow 时根据热度设置刷新间隔和基础弹幕数
NowHot < 100         → MAXTIME=180, BASECHATNUMBER=4
NowHot < 1000        → MAXTIME=120, BASECHATNUMBER=8
NowHot < 10000       → MAXTIME=90,  BASECHATNUMBER=12
NowHot < 100000      → MAXTIME=60,  BASECHATNUMBER=16
NowHot < 1000000     → MAXTIME=45,  BASECHATNUMBER=20
NowHot >= 1000000    → MAXTIME=30,  BASECHATNUMBER=25
```

刷新逻辑：每次刷新追加 1 条新弹幕 + 保留历史（上限 25 条），使用 `Events.GameCoreEventPublishComplete` 每秒倒计时。

## 六、灾难生成附加系统

53 号事件"城市随机灾难"独立实现了完整的地图随机事件引擎：

```lua
-- 搜索顺序：特征 > 地形
-- 森林 → RANDOM_EVENT_FOREST_FIRE
-- 丛林 → RANDOM_EVENT_JUNGLE_FIRE
-- 火山 → 50%温和 / 30%灾难性 / 20%超级
-- 冲积平原 → 50%中度 / 30%大型 / 20%千年
-- 其他地形 → 查 RandomEvent_Terrains 表匹配

-- 使用 GameRandomEvents.ApplyEvent({EventType=Index, Location=plotIndex, ...})
```

需要 RiverManager/MapFeatureManager 预先建立河流和火山列表。

## 七、城市区域+建筑全掠夺

```lua
function Siqi_AllPillagedFromXY(iX, iY)
    -- 遍历相邻 6 格：
    -- 1. 掠夺改良设施（ImprovementBuilder.SetImprovementPillaged）
    -- 2. 掠夺区域（pDistrict:SetPillaged(true)）
    -- 3. 掠夺建筑（DB.Query 查该区域的所有建筑，逐个 SetPillaged）
    --    排除：奇观区域、Cost=1 的建筑（城墙/纪念碑等基础建筑）
end
```

## 八、城市产出 Property 正负数分离系统

Reward.lua 内建了城市产出 Property 的正负数分离存储（与 lua-binary.md 相同原理但独立实现）：

```lua
-- 前缀命名
s_add  = 'SIQI_U_OFFICAL_CITY_CHANGE_YIELD_xx_PROPERTY_'  -- 正数属性
s_lost = 'SIQI_U_OFFICAL_CITY_NOT_CHANGE_YIELD_xx_PROPERTY_' -- 负数属性

-- Siqi_CityYieldChange(pCity, amount, yieldIndex, IsChange)
-- 自动处理正负值：amount>0 先消负数再增正数，amount<0 先消正数再增负数
```

与 Core Mod 的二进制 Property 系统使用相同原理但前缀命名不同。

## 九、SQL 配合

```sql
-- 奖励/事件定义表
CREATE TABLE Siqi_ULKReward (
    RewardID    INTEGER PRIMARY KEY,
    MinLevel    INTEGER NOT NULL,    -- 最低热度等级可触发
    IsBadEvent  BOOLEAN DEFAULT 0,  -- 0=奖励 1=事件
    Name        TEXT,
    Description TEXT,                -- 支持占位符
    Effect      TEXT                 -- 效果简短名称（Popup用）
);

-- 聊天文本表
CREATE TABLE Siqi_AvatarChat (
    ChatID   INTEGER PRIMARY KEY,
    ChatType INTEGER NOT NULL,       -- 0-4 文本等级
    ChatText TEXT,                   -- LOC 文本
    AvatarID INTEGER                 -- Type=4 时绑定的头像
);

-- 头像表
CREATE TABLE Siqi_Avatar (
    AvatarID              INTEGER PRIMARY KEY,
    Name                  TEXT,
    InitialPreferenceLevel INTEGER DEFAULT 0,
    IsSpecial             BOOLEAN DEFAULT 0
);
```

## 十、XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `UI/Arknights_Cute_Leaders_13.0_Button.xml` | LaunchBar 入口按钮（SiqiUOfficalItem Instance） |
| `UI/Arknights_Cute_Leaders_13.0_UI.xml` | 单位面板按钮（SiqiUOfficalGrid）— 选中 UNIT_STREAMER_U 时显示 |
| `UI/Arknights_Cute_Leaders_13.0_Panel.xml` | 直播主面板（弹幕区 + 打赏列表 + 背景图） |
| `UI/Arknights_Cute_Leaders_13.0_Popup.xml` | 直播确认弹窗（继承 PopupDialog） |
| `Arknights_Cute_Leaders_13.0_Reward.sql` | Siqi_ULKReward 奖励/事件定义表 |
| `Arknights_Cute_Leaders_13.0_Chat.sql` | Siqi_AvatarChat / Siqi_Avatar 弹幕文本和头像表 |

### 控件 ID 与 Lua Controls.xxx 对照

#### Arknights_Cute_Leaders_13.0_UI.xml（单位面板按钮）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `SiqiUOfficalGrid` | Grid | `Controls.SiqiUOfficalGrid` | 外层容器（Hidden="1" 默认隐藏） |
| `SiqiUOfficalButton` | Button | `Controls.SiqiUOfficalButton` | 直播入口按钮（44x53，注册 eLClick） |
| `SiqiUOfficalButtonIcon` | Image | — | 按钮图标（ICON_U_OFFICAL_ACTION_LIVE） |

#### Arknights_Cute_Leaders_13.0_Button.xml（LaunchBar 入口）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `SiqiUOfficalButton` (LaunchBar) | Button | `Controls.LaunchItemButton` | LaunchBar 入口按钮（49x49） |
| `SiqiUOfficalIcon` | Image | — | LaunchBar 图标 |
| `ReminderPin` | Image | — | 红点提示（Pin） |

**Instance Name：** `SiqiUOfficalItem` 注册在 LaunchBar 容器中。

#### Arknights_Cute_Leaders_13.0_Panel.xml（直播主面板）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `ScreenConsumer` | BoxButton | — | 背景遮罩（全屏消费鼠标事件） |
| `MainULKContainer` | Container | `Controls.MainULKContainer` | 主面板容器（1029x770） |
| `CloseButton` | Button | `Controls.CloseButton` | 右上角关闭按钮 |
| `LiveTitleContainer` | Container | `Controls.LiveTitleContainer` | 直播标题区（720x120） |
| `LiveContentContainer` | Container | `Controls.LiveContentContainer` | 直播内容区（720x395） |
| `LiveChatContainer` | Container | `Controls.LiveChatContainer` | 弹幕区（右侧 295x720） |
| `LiveChatScrollPanel` | ScrollPanel | `Controls.LiveChatScrollPanel` | 弹幕滚动面板 |
| `LiveChatStackContent` | Stack | `Controls.LiveChatStackContent` | 弹幕文本挂载点 |
| `LiveRewardContainer` | Container | `Controls.LiveRewardContainer` | 打赏列表区（左下 720x220） |
| `LiveRewardScrollPanel` | ScrollPanel | `Controls.LiveRewardScrollPanel` | 打赏滚动面板 |
| `LiveRewardStackContent` | Stack | `Controls.LiveRewardStackContent` | 打赏条目挂载点 |

**Instance 模板：**

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `LiveRewardItem` | 单条打赏信息 | `LiveRewardItemStack`(Stack), `LiveRewardText`(Label) |

#### Arknights_Cute_Leaders_13.0_Popup.xml（确认弹窗）

```xml
<Context Name="UPopupDialog">
    <Include File="PopupDialog" />
    <MakeInstance Name="PopupDialog" />
</Context>
```
继承游戏原生 `PopupDialog`，Lua 端通过 `LuaEvents.SiqiUOfficalButtonPopupDialog` 驱动弹窗内容。

### 通用挂载模式

```lua
-- 单位面板按钮挂载（UI.xml）
function Initialize()
    local pContext = ContextPtr:LookUpControl("/InGame/UnitPanel/StandardActionsStack")
    if pContext then
        Controls.SiqiUOfficalGrid:ChangeParent(pContext)
        Controls.SiqiUOfficalButton:RegisterCallback(Mouse.eLClick, OnButtonClickedSiqiUOffical)
    end
    Events.UnitSelectionChanged.Add(OnUnitSelectionChanged)
    Events.UnitMoveComplete.Add(OnUnitMoveComplete)
end

-- LaunchBar 按钮挂载（Button.xml + Button.lua）
local pLaunchBar = ContextPtr:LookUpControl("/InGame/TopOptionsBar/OptionsStack")
local instance = pLaunchBar:BuildInstanceForControl("SiqiUOfficalItem", pLaunchBar)
-- 领袖过滤：非目标领袖 SetHide(true)
```

### 添加新弹幕/打赏展示模板

```xml
<!-- 新打赏条目模板 -->
<Instance Name="NewRewardItem">
    <Stack ID="NewRewardItemStack" Size="parent-55,40" Anchor="L,C" Offset="0,0" StackGrowth="Down">
        <Label ID="NewRewardText" Anchor="L,C" Size="parent,parent" Offset="3,0"
               Style="FontFlair16" FontStyle="glow" ColorSet="ShellHeader"/>
    </Stack>
</Instance>
```

```lua
-- Lua 端注册
local m_RewardIM = InstanceManager:new("NewRewardItem", "NewRewardItemStack", Controls.LiveRewardStackContent)
local instance = m_RewardIM:GetInstance()
instance.NewRewardText:SetText(Locale.Lookup(rewardText))
```

## 十一、关键要点

| 要点 | 说明 |
|------|------|
| 对数型热度等级 | 100/1K/10K/100K/1M 阈值，符合"越往后越难升"的体验 |
| 双重概率系统 | 先按热度等级掷等级（概率表），再从该等级的 ID 池中随机选 |
| 30% 事件触发率 | 每个奖励等级对应 30% 概率额外触发一次负面事件 |
| 恶意函数降级保护 | 城市叛乱(40%)、城市毁灭(60%)、无可用目标时降级为扣金币 |
| 直播城市去重 | 用 Unit Property 记录已直播城市坐标表，防止重复直播 |
| 弹幕最大 25 条 | 防内存无限增长，超过上限删最早元素 |
| 热度→弹幕速度正反馈 | 热度越高刷新越快 + 高级文本比例越大，增强沉浸感 |
| 单位战斗力双保险 | 同时设 Unit Property + Unit Ability，确保 Modifier 能读取 |
| 玩家回合清空弹幕 | `PlayerTurnActivated` 时 `ChatTextTable = {}` |
| 两大支撑函数集 | `Siqi_GetRandNumber`(非线性) / `Siqi_GetRandNumber2`(线性)，统一波动公式 |
