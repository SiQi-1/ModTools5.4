# lua-0029-灵值经济系统 -- 基于8种产出属性的复合灵值经济体系

## 概述
灵值（LingZhi / Soul Points）是 Siqi_Leaders_0029 的核心自定义资源。该系统通过 **自定义 SQL 表驱动的属性-函数映射**，在每个回合自动计算各城市+玩家的灵值增量。灵值用于购买特殊单位、升级任务等级、强制完成任务等。

涉及文件：
- `Support/Siqi_Leaders_0029_Core.lua` -- 核心计算逻辑 `Core.UI:GetData()` (~300行)
- `Support/Siqi_Leaders_0029_Support.lua` -- SiqiGP/SiqiUI 辅助函数库
- `UI/Siqi_Leaders_0029_MainPanel.lua` -- DataPanelRefresh() UI 展示
- `UI/Siqi_Leaders_0029_TopPanel.lua` -- 城市面板灵值购买按钮
- `Data/Siqi_Leaders_0029_Modifiers.sql` -- 相关 Modifier
- 自定义 SQL 表: `Siqi_Leaders_0029_LINGZHI_CORE`

## 核心架构

### 属性分类（8 种属性）
灵值系统将产出分为 8 种属性，对应 7 个专属区域 + 1 个全局属性（属性 0 为全体作用，属性 1-7 与区域一一对应）：

| 属性 | 区域 | 产出类型 |
|------|------|----------|
| 0 | 全局（全体作用） | 通用 |
| 1 | DISTRICT_SIQI_D0029_1 | YIELD_PRODUCTION |
| 2 | DISTRICT_SIQI_D0029_2 | YIELD_PRODUCTION |
| 3 | DISTRICT_SIQI_D0029_3 | YIELD_SCIENCE |
| 4 | DISTRICT_SIQI_D0029_4 | YIELD_GOLD |
| 5 | DISTRICT_SIQI_D0029_5 | YIELD_CULTURE |
| 6 | DISTRICT_SIQI_D0029_6 | YIELD_FAITH |
| 7 | DISTRICT_SIQI_D0029_7 | YIELD_FOOD |

### 计算公式（城市级）
```
ForEachCity:
  ForEach property i in [0..7]:
    Base[i] = sum(city-level AmountFromFunction)
    Percent[i] = sum(city-level PercentFromFunction)
  
  For i in [1..7]:
    CityFinal[i] = Base[i] * (1 + Percent[i] / 100)
  
  CityEndLZ = (Sum(CityFinal[1..7]) + Base[0]) * (1 + Percent[0] / 100)
```

### 计算公式（玩家级）
```
ForEachPlayer:
  ForEach property i in [0..7]:
    PlayerBase[i] = sum(player-level AmountFromFunction) + sum(CityFinal[i] * (1 + CityPercent[0]/100))
    PlayerPercent[i] = sum(player-level PercentFromFunction)
  
  For i in [1..7]:
    PlayerFinal[i] = PlayerBase[i] * (1 + PlayerPercent[i] / 100)
  
  TotalEndLZ = (Sum(PlayerFinal[1..7]) + PlayerBase[0]) * (1 + PlayerPercent[0] / 100)
```

## GP 端

### Core.ChangeLZ(playerID, ChangeValue)
```lua
function Core.ChangeLZ(playerID, ChangeValue)
    ChangeValue = Core.ToOneDecimal(ChangeValue)
    Core.ChangeProperty(pPlayer, Property_LZ, ChangeValue)
    LuaEvents.Siqi0029_LingZhiChanged(playerID, ChangeValue) -- 广播变更
end
```
关键：每次修改灵值都通过 `LuaEvents.Siqi0029_LingZhiChanged` 广播，任务系统监听此事件检测 "获得X点灵值" 任务。

### Core.GetLZ(playerID)
返回当前灵值总量（一位小数）。

### Core.CanLevelUp(playerID)
判断是否满足升级条件：`灵值 >= Siqi_MainQuest_LZ_Requirement[CurrentLevel]`

升级所需灵值：
- Lv1: 1000
- Lv2: 2500
- Lv3: 8000
- Lv4: 20000
- Lv5: 50000
- Lv6: 100000

### Core.GP -- 灵值事件处理

| 事件 | 函数 | 说明 |
|------|------|------|
| GameEvents.Siqi0029_ChangeLZ | Add/Subtract LZ | UI端广播的灵值变更 |
| GameEvents.Siqi0029_UnitButton_LZSJ | UnitButton_LZSJ | 生灵单位收集灵值后回调 |
| Events.CityProductionCompleted | CityUnitProduction | 生产战斗单位奖励灵值（Cost*0.5） |
| Events.Combat | OnCombat | 凰茗狐战斗转化 + 占领区域送建造者 |
| GameEvents.Siqi_Leaders_0029_Purchase_SL | OnPurchaseSL | 购买生灵单位，消耗灵值 |

### 灵值获取途径
1. 每回合自动计算（Core.UI:GetData → Core.UI:AddLZ）
2. 生产战斗单位（拥有 DISTRICT_SIQI_D0029_2 的城市）
3. 尤里卡/鼓舞触发时的抽奖（Gameplay.lua, 30%概率）
4. WMD导弹爆炸（Gameplay.lua, 与科文进度挂钩）
5. 迪娅可击杀单位（Gameplay.lua）
6. 完成科技研究（L5 专属）
7. 生灵单位收集（UnitButton.lua）
8. 任务奖励发放（REWARDS.GiveLZPoints）

## UI 端

### Core.UI:GetData() -- 核心计算
通过遍历 `Siqi_Leaders_0029_LINGZHI_CORE` 自定义表（每行定义：`To_Type`、`DistrictType`、`FromFunction`、`Amount/Percent`、`CityPropertyKey`、`PlayerPropertyKey`），动态调用对应的计算函数。

支持的 FromFunction（城市级）：
- `FromCityGold`、`FromCityProduction`、`FromCityScience`、`FromCityCulture`、`FromCityFaith`、`FromCityFood` -- 城市产出比例转换
- `FromCityRouteGold` -- 贸易路线金币
- `FromCityAminity` -- 宜居度
- `FromCityPopulation` -- 人口
- `FromCityHousing` -- 住房
- `FromCityProperty` -- 自定义城市属性
- `FromPlayerProperty` -- 玩家属性（仅玩家级）
- `FromDealGold` -- 外交交易金币（仅玩家级）

### Core.UI:RefreshData()
每回合自动调用（通过 `Events.PlayerTurnActivated`）：
1. 调用 `GetData()` 计算本回合灵值增量
2. 调用 `AddLZ(Data.endLZ)` 通过 `UI.RequestPlayerOperation` 发送到 GP 线程

### Core.UI:RefreshCitiesRouteEnd()
检查所有城市是否是贸易路线终点，更新 `PropertyCiv0029LoyaltyValueBonus6_RouteEnd` 属性。

### MainPanel.lua -- DataPanelRefresh()
在 UI 面板中展示：
- 每个城市的各属性灵值贡献（可折叠分组）
- 玩家级灵值加成
- 总览（BaseYield、GeneralPercentBonus、FinalYield）
- 每个区域的图标和名称

### TopPanel.lua -- 城市购买按钮
在城市面板中添加 "购买生灵单位" 按钮：
- 费用 = `(200 + 购买次数 * 200) * 游戏速度倍率`
- 仅在任务等级 >= 6 时显示
- 调用 `GameEvents.Siqi_Leaders_0029_Purchase_SL`

## SQL 配合

### 自定义 SQL 表：Siqi_Leaders_0029_LINGZHI_CORE
这是驱动整个计算系统的核心数据表，每行定义一个加成规则：

| 字段 | 说明 |
|------|------|
| To_Type | 'City' 或 'Player' |
| DistrictType | 区域类型（nil = 全局） |
| FromFunction | Lua 函数名（如 'FromCityGold'） |
| FromFunctionValue1~3 | 函数参数 |
| Amount | 非 nil = 基础数值 |
| Percent | 非 nil = 百分比加成 |
| CityPropertyKey | 城市需满足的属性 |
| PlayerPropertyKey | 玩家需满足的属性 |
| Description | UI 工具提示文本 |

### 相关 Modifier
- `LINGZHI_PERCENTAGE_DISTRICT_SIQI_D0029_X` -- 区域任务固定增益百分比（渐进累积）
- `LINGZHI_PERCENTAGE_MAIN_QUESTS` -- 主线任务固定增益百分比
- `Property_Quest_Level` -- 任务等级
- `Siqi_Leaders_0029_LingZhi` -- 当前灵值 Property
- `Siqi_Leaders_0029_HasReligion` -- 是否已发教（未发教则灵值为 0）

## 设计模式与要点

1. **属性隔离**：属性 1-7 只受同属性和属性 0 的百分比加成影响，互不干扰
2. **两级计算**：先算城市级汇总，再算玩家级汇总，保证 UI 可以展示城市明细
3. **数据驱动**：加成规则完全由 SQL 表定义，不需要改 Lua 即可新增加成来源
4. **线程安全**：UI 端计算、GP 端执行修改，通过 `UI.RequestPlayerOperation` + `EXECUTE_SCRIPT` 通信
5. **前置条件**：玩家必须先创建宗教（`HasFoundedReligion`），否则灵值增量为 0
