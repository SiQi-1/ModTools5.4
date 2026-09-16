# 领袖能力系统（来源：0029）

## 做什么
7 个文明/领袖各有一套独立的 Lua 驱动能力，通过 `LeaderAbility.L1~L7` 表结构管理。除核心灵值系统外，每个领袖的专属加成和事件响应均在此实现。所有领袖共享 `UNIT_SIQI_U0029_5`（生灵单位）作为通用奖励载体。

## 涉及文件和函数
| 文件 | 职责 |
|------|------|
| `Lua/Siqi_Leaders_0029_LeaderAbilities.lua` | 7 个领袖全部能力 (~730 行) |
| `Support/Siqi_Leaders_0029_Core.lua` | Core.IsLeader(playerID, Index) 判断函数 |
| `Support/Siqi_Leaders_0029_Support.lua` | SiqiGP 工具函数供能力调用 |

## 7 大领袖能力总览

| 编号 | 领袖 | 专属单位/区域 | 核心机制 |
|------|------|------------|---------|
| L1 | 樱墨曦 | — | 单位多段晋升 + 黄金时代/伟人/任务完成送生灵 |
| L2 | 鹿薇 | DISTRICT_PRESERVE | 保护区完成送生灵 + 自动获得法典 |
| L3 | — | UNIT_SIQI_U0029_2 | 野蛮人营地生成系统 + 击杀奖励生产力/灵值 |
| L4 | — | — | 经济同盟 + 奢侈品收集里程碑 |
| L5 | — | DISTRICT_SIQI_D0029_3 | 尤里卡概率送生灵 + 科技完成给灵值 + 区域随机产出 |
| L6 | — | DISTRICT_SIQI_D0029_6 | 时代扣分 + 击杀扩散宗教 + 区域完成送生灵 |
| L7 | — | — | 城市人口到 10 送生灵 + 单位宜居度战斗力加成 |

## 核心模式

### 统一的领袖能力初始化
```lua
LeaderAbility.Initialize = function()
    LeaderAbility.L1Initialize()   -- 樱墨曦
    LeaderAbility.L2:Initialize()  -- 鹿薇
    LeaderAbility.L3:Initialize()
    LeaderAbility.L4:Initialize()
    LeaderAbility.L5:Initialize()
    LeaderAbility.L6:Initialize()
    LeaderAbility.L7:Initialize()
end
```

### 领袖判断统一入口
```lua
Core.IsLeader(playerID, 5) -- true/false，检查是否是 LEADER_SIQI_L0029_5
```

## L1 樱墨曦 — 生灵多段晋升

### 机制
生灵单位获得 `SIQI0029_PROMOTION_COUNT` 属性，每晋升一次消耗 1 点该属性，自动再获得一次晋升经验，实现"一次行动、N 次晋升"的效果。

### 触发条件（赠送生灵并赋予晋升次数）
| 条件 | 晋升次数 | 说明 |
|------|---------|------|
| 进入黄金时代 | 0 | 每时代赠送 1 个无晋升次数生灵 |
| 招募 8 个伟人 | 0 | 每 8 个伟人送 1 个（计数器扣减） |
| 主线任务等级 >= 3 | Level-3 | 任务等级越高，晋升次数越多 |

### 涉及函数
- `GrantPromotion(playerID, unitID)` — 给单位当前晋升所需经验
- `GiveUnitAndPromotion(playerID, promotionCount)` — 在首都生成生灵并设置晋升次数
- `OnUnitPromoted` — 监听晋升事件，消耗晋升次数自动再升级
- `OnGameEraChanged` — 黄金时代判断
- `OnUnitGreatPersonCreated` — 伟人计数
- `OnSiqi0029_MainQuestCompleted` — 主线任务完成回调

### 黄金时代判断
通过 Property `SIQI0029_IS_GOLDEN_AGE`（由 SQL Modifier 设置）判断。

## L2 鹿薇 — 保护区赠生灵

### 机制
建造保护区（PRESERVE）完成后，给该城市赠送一个生灵单位。同时自动赠送法典市政。

### 涉及函数
- `L2:GiveCivic(playerID)` — 检查并赠送 CIVIC_CODE_OF_LAWS
- `L2:GiveUnitSLToCity(playerID, CityID)` — 在城市位置生成生灵单位（被 L6、L7 复用）
- `L2:OnDistrictCompleted(playerID, cityID)` — 保护区完成回调

### 防重复
城市拥有 `PROPERTY_SIQI_0029_LUWEI` 标记后不再重复触发。

## L3 — 野蛮人营地生成系统（最复杂的领袖能力）

### 机制
每 7 回合在玩家领土外围（距离城市 4-7 环）自动生成一个野蛮人营地，营地分三类：水寨（沿海）、马寨（靠近马资源）、普通寨。

### 生成算法（`GetPlotsToAddBarbarians`）
1. **候选地块**：遍历玩家所有城市，取距离 4-7 环的所有地块
2. **排除规则**：
   - 水域、不可通行、自然奇观、有归属、有单位的地块 (`AllowPlots`)
   - 任意有主城市 4 环内的地块 (`BuildCityExclusionSet`)
   - 已有野蛮人营地 5 环内的地块 (`BuildBarbarianCampExclusionSet`)
3. **分类规则**：
   - 水寨：`pPlot:IsCoastalLand()` 的地块
   - 马寨：在 Horse 资源 3 环内的地块 (`horseInfluenced`)
   - 普通寨：其余合格地块
4. **权重抽选**：Coastal:Horse:Normal 权重为 1:1:2，加权随机选择

### 性能优化策略
- 不从全图遍历，而是从玩家城市出发取 7 环邻居
- `BuildCityExclusionSet` 和 `BuildBarbarianCampExclusionSet` 复用结果
- 单次最多尝试 20 次（`AddCampOfType` 循环）

### 其他能力
- 被宣战时赠送生灵单位（已注释，当前版本未启用）
- 首次建城赠送专属单位 `UNIT_SIQI_U0029_2`
- 击杀敌方单位奖励生产力（单位造价*20%）+ 灵值

### 涉及函数
- `L3:OnTurnBegin()` — 回合计数
- `L3:GetPlotsToAddBarbarians(playerID)` — 核心算法
- `L3:AddBarbariansCamp(playerID)` — 营地生成 + 发起攻城
- `L3:GetNearestCity(pPlot, playerID)` — 找最近城市
- `L3:OnUnitKilledInCombat` — 击杀奖励

## L4 — 联盟与奢侈品追踪

### 机制
- 与每名新领袖首次达成**经济同盟**时赠送生灵单位
- 拥有 4/8/12 种不同奢侈品时各赠送一次生灵单位

### 涉及函数
- `L4:OnAllianceAvailable(playerID, params)` — 监听 GameEvents.Siqi0029AllianceAvailable
- `L4:OnPlayerResourceChanged(playerID, resourceType)` — 监听 Events.PlayerResourceChanged，每次有奢侈资源变动都重新计数
- 防重复：用 `Siqi0029_L4_Had_Economic_Alliance` 表（按其他玩家 ID 为键）和 `SIQI0029_L4_RESOURCE_COUNTER_4/8/12` 标记

## L5 — 尤里卡概率 + 科技奖励

### 机制
- 尤里卡触发时有累积概率赠送生灵：起始 10%，未触发 +10%（最高 80%），触发后重置为 10%
- 完成科技研究时获得灵值（科技 Cost * 20%）
- 建造 `DISTRICT_SIQI_D0029_3` 时，给地块随机标记一种产出类型

### 涉及函数
- `L5:OnTechBoostTriggered(playerID, techType)` — 累积概率 + 触发重置
- `L5:OnResearchCompleted(playerID, techType)` — 科技完成给灵值
- `L5:OnDistrictCompleted(playerID, cityID, districtID)` — 标记地块产出类型
- `L5:RandYieldType()` — 随机 6 种产出之一
- `RandomByPercent(Percent)` — 百分比概率判定工具函数

## L6 — 时代惩罚 + 宗教扩散

### 机制
- 进入新时代时扣除 4 点时代分数
- 击杀敌方单位时，以击杀位置为中心，对 6 环内城市施加宗教压力（压力值 = 被击杀单位战斗力 * 10）
- 建造 `DISTRICT_SIQI_D0029_6` 时赠送生灵单位（调用 L2 的函数）

### 涉及函数
- `L6:OnGameEraChanged()` — 遍历所有 L6 玩家扣分
- `L6:OnUnitKilledInCombat(killedPlayerID, killedUnitID, playerID, unitID)` — 击杀触发宗教压力
- `L6:AddReligion(iX, iY, religionType, playerID, ring, power)` — 用 Map.GetNeighborPlots 找周围城市并施加压力
- `L6:OnDistrictCompleted(playerID, cityID, districtID)` — 调用 `L2:GiveUnitSLToCity`

## L7 — 人口赠单位 + 宜居度战力

### 机制
- 城市首次人口达到 10 时赠送生灵单位
- 单位战斗力根据所在城市宜居度动态变化：在自己领土内 = 城市宜居度；在他人领土 = 0

### 涉及函数
- `L7:OnCityPopulationChanged(playerID, cityID, cityPopulation)` — 人口到 10 触发
- `L7:OnUnitMoveComplete(playerID, unitID, iX, iY)` — 单位移动后刷新战斗力
- `L7:OnUnitAddedToMap(playerID, unitID)` — 单位生成时初始化战力

### 战斗力动态绑定
```lua
-- 进入己方领土：pUnit:SetProperty(CombatProperty, Amenity)
-- 离开己方领土：pUnit:SetProperty(CombatProperty, 0)
-- 通过 PropertyCiv0029L7StrengthBonus 属性传给 SQL Modifier 链
```

## 数据表依赖
每个领袖的能力通常依赖 SQL 端配置的 Modifier 链配合（如 `SIQI0029_IS_GOLDEN_AGE`、`PropertyCiv0029L7StrengthBonus` 等 Property），Lua 负责写入/更新这些 Property 值，SQL Modifier 根据 Property 值提供实际的游戏效果。

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `UI/Siqi_Leaders_0029_MainPanel.xml` | 任务面板 + 城市收入报表（Instance 模板最多，含 8 种 Instance） |
| `UI/Siqi_Leaders_0029_TopPanel.xml` | TopPanel 扩展：WMD 攻击按钮 + 生灵单位按钮 |
| `UI/Siqi_Leaders_0029_UnitButton.xml` | 单位面板弹窗按钮（UPopupDialog Context） |
| `UI/Siqi_Leaders_0029_UI.xml` | 通用 UI 控件 |
| `Data/Siqi_Leaders_0029_Modifiers.sql` | SQL Modifier 链定义 |
| `Data/Siqi_Leaders_0029_UnitAbilities.sql` | 单位能力定义 |
| `Data/Siqi_Leaders_0029_Units.sql` | 单位定义（含 UNIT_SIQI_U0029_5 生灵单位等） |
| `Data/Siqi_Leaders_0029_Districts.sql` | 自定义区域定义（DISTRICT_SIQI_D0029_3、D0029_6） |

### 控件 ID 与 Lua Controls.xxx 对照

#### Siqi_Leaders_0029_MainPanel.xml（任务面板 + 城市收入报表）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `MainContainer` | Container | `Controls.MainContainer` | 主面板容器（1200x720） |
| `CloseButton` | Button | `Controls.CloseButton` | 右上角关闭 |
| `TabControl` | Tab | `Controls.TabControl` | 标签页控件 |
| `SelectTab_Tab1` | GridButton | `Controls.SelectTab_Tab1` | "任务系统"标签 |
| `SelectTab_Tab2` | GridButton | `Controls.SelectTab_Tab2` | "城市产出报表"标签 |
| `Tab1` | Grid | `Controls.Tab1` | 任务页面内容 |
| `Tab2` | Grid | `Controls.Tab2` | 报表页面内容 |
| `ProgressContainer` | Container | `Controls.ProgressContainer` | 主线进度条容器 |
| `ProgressBar` | Bar | `Controls.ProgressBar` | 主线进度条 |
| `SideQuestScrollPanel` | ScrollPanel | `Controls.SideQuestScrollPanel` | 支线任务滚动面板 |
| `SideQuestInnerStack` | Stack | `Controls.SideQuestInnerStack` | 支线任务挂载点 |
| `Scroll` (Tab2) | ScrollPanel | `Controls.Scroll` | 报表滚动面板 |
| `Stack` (Tab2) | Stack | `Controls.Stack` | 报表城市行挂载点 |
| `LZTrackerGrid` | Container | `Controls.LZTrackerGrid` | 灵值显示栏（右上角） |
| `LZTrackerLZ` | GridButton | `Controls.LZTrackerLZ` | 灵值数值按钮 |
| `LZBalance` | Label | `Controls.LZBalance` | 灵值余额文本 |
| `LZPerTurn` | Label | `Controls.LZPerTurn` | 灵值每回合文本 |
| `LevelTrackerGrid` | Container | `Controls.LevelTrackerGrid` | 等级显示栏 |
| `LevelTrackerLevel` | GridButton | `Controls.LevelTrackerLevel` | 等级数值按钮 |
| `LevelLabel` | Label | `Controls.LevelLabel` | 等级文本 |
| `LeaderPortrait` | Image | `Controls.LeaderPortrait` | 领袖立绘（右下 640x640） |

**Instance 模板（8 种）：**

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `SiqiQuestSlot` | 支线任务条目 | `SiqiQuestSelect`(GridButton), `SiqiQuestIcon`(Image, 64x64), `SiqiQuestTitle`(Label), `SiqiQuestDesc`(Label), `SiqiQuestStatus`(Label), `SiqiQuestCompleteButton`(GridButton) |
| `SimpleInstance` | 简单行（Non-Collapsable） | `Top`(Stack) |
| `GroupInstance` | 可折叠行分组 | `RowHeaderButton`(GridButton), `RowExpandCheck`(Image), `CollapseScroll`(ScrollPanel), `CollapseAnim`(SlideAnim), `ContentStack`(Stack) |
| `SiqiCityIncomeHeaderInstance` | 报表表头行（5 列） | `Top`(Container, 666x25) |
| `SiqiCityIncomeLineItemInstance` | 报表数据行 | 5 个 Label: `LineItemName`, `BaseYield`, `SpecificPercentBonus`, `GeneralPercentBonus`, `FinalYield` |
| `SiqiCityIncomeInstance` | 城市收入卡片（含区域列表） | `CityName`(Label), `LineItemStack`(Stack), `BaseYield`/`SpecificPercentBonus`/`GeneralPercentBonus`/`FinalYield`(Label) |
| `SiqiCityIncomeTotalInstance` | 总计行 | `TotalBaseYield`, `TotalSpecificPercentBonus`, `TotalGeneralPercentBonus`, `TotalFinalYield`(Label) |
| `SiqiLaunchBarItem` | LaunchBar 入口按钮 | `LaunchItemButton`(Button, 49x49), `LaunchItemIcon`(Image) |
| `SiqiLaunchBarPinInstance` | LaunchBar 红点 | `Pin`(Image) |

#### Siqi_Leaders_0029_TopPanel.xml（TopPanel 按钮）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `WMDAttack` | Grid | `Controls.WMDAttack` | 核弹攻击计数显示（Style="SubContainerSmall2", 48x24） |
| `WMDAttackCount` | Label | `Controls.WMDAttackCount` | 核弹数量文本 |
| `SiqiButtonGrid` | Grid | `Controls.SiqiButtonGrid` | 生灵单位按钮容器 |
| `SiqiButton` | Button | `Controls.SiqiButton` | 生灵单位按钮（44x53） |
| `SiqiButtonIcon` | Image | — | 按钮图标（ICON_UNIT_SIQI_U0029_5） |

#### Siqi_Leaders_0029_UnitButton.xml（单位面板弹窗）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `Siqi0029UnitGrid` | Grid | `Controls.Siqi0029UnitGrid` | 单位面板弹窗容器（Hidden="1"） |
| `Siqi0029UnitButton` | Button | `Controls.Siqi0029UnitButton` | 弹窗触发按钮（44x53） |
| `Siqi0029UnitButtonIcon` | Image | — | 按钮图标（ICON_SIQI_SHENGLINGBITAN） |

**挂载注意：** 此 XML 使用 `UPopupDialog` Context Name（覆盖游戏原生弹窗），通过 MakeInstance 嵌入 `PopupDialog`。

### SQL 配合关键定义

```sql
-- GameProperty 定义（Modifiers.sql 中）
SIQI0029_IS_GOLDEN_AGE              -- L1 黄金时代标记（由 SQL Modifier 写入）
PropertyCiv0029L7StrengthBonus      -- L7 单位战斗力绑定属性

-- 自定义单位能力（UnitAbilities.sql）
ABILITY_UNIT_SIQI_U0029_5_XXX       -- 生灵单位系列能力

-- 自定义区域
DISTRICT_SIQI_D0029_3               -- L5 专属区域
DISTRICT_SIQI_D0029_6               -- L6 专属区域
```

### 添加新领袖能力的 XML 配合模板

```xml
<!-- 新领袖能力按钮（UnitPanel 扩展） -->
<Grid ID="NewLeaderAbilityGrid" Anchor="R,B" Size="auto,41" AutoSizePadding="6,0"
      Texture="SelectionPanel_ActionGroupSlot" SliceCorner="5,19" SliceSize="1,1"
      SliceTextureSize="12,41" ConsumeMouse="1" Hidden="1">
    <Button ID="NewLeaderAbilityButton" Anchor="C,B" Size="44,53" Texture="UnitPanel_ActionButton">
        <Image ID="NewLeaderAbilityButtonIcon" Anchor="C,C" Offset="0,-2" Size="38,38" Icon="ICON_NEW_ABILITY"/>
    </Button>
</Grid>
```

```lua
-- Lua 端注册（UI.lua）
function Initialize()
    local pContext = ContextPtr:LookUpControl("/InGame/UnitPanel/StandardActionsStack")
    if pContext then
        Controls.NewLeaderAbilityGrid:ChangeParent(pContext)
        Controls.NewLeaderAbilityButton:RegisterCallback(Mouse.eLClick, OnNewAbilityClicked)
    end
end
Events.LoadGameViewStateDone.Add(Initialize)
```

## 设计要点
1. **职责分离**：Lua 负责事件监听 + 数据写入，SQL Modifier 负责实际效果
2. **函数复用**：`L2:GiveUnitSLToCity` 被 L6、L7 调用；`GiveUnitAndPromotion` 被 L1/L3/L4/L5 调用
3. **性能意识**：L3 仅在存在该领袖时才注册事件监听；野蛮人营地生成算法避免全图遍历
4. **Property 去重**：每个领袖都使用城市/玩家的 Property 标记防重复触发
5. **游戏速度适配**：所有数值类奖励都乘以 `GAME_SPEED_MULTIPLIER` 适配不同速度
