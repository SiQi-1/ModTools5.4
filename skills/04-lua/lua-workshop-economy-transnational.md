# 跨国公司系统（来源：工坊 2479197624 MonopolyPlus）

## 做什么
允许玩家在**无主地块**上建造跨国公司改良设施，获得该格奢侈资源的**副本**。
通过 Lua 监听地块改良事件实现领土外资源获取。

## Lua 端

`lua/Leu_Transnational_Functions.lua`

### 核心变量
```lua
local iImprovement = "IMPROVEMENT_LEU_TRANSNATIONAL"       -- 陆地跨国公司
local iImprovementSea = "IMPROVEMENT_LEU_TRANSNATIONAL_SEA" -- 海洋跨国公司
```

### 初始化工
遍历 `GameInfo.Resources()` 构建 `tLuxuries` 表（所有 `RESOURCECLASS_LUXURY` 类资源）。

### 事件监听（4 个）
```lua
Events.ImprovementAddedToMap.Add(OnImprovementAdded_Transnationals)
GameEvents.OnImprovementPillaged.Add(OnImprovementPillaged_Transnationals)
Events.ImprovementRemovedFromMap.Add(OnIUmprovementRemovedFromMap_Transnationals)
--Events.ImprovementOwnershipChanged.Add(...)  -- 注释掉未启用
```

### 建造时（OnImprovementAdded_Transnationals）
1. 检查地块是否无主（`pPlotOwner == -1`）
2. 通过 `WorldBuilder.CityManager():SetPlotOwner()` 将地块**临时授予玩家首都**
3. 用 `pPlot:SetProperty("TransnationalOwnerID", iOwner)` 记录真实所有者
4. 调用 `pPlayer:GetResources():ChangeResourceAmount(iResourceID, 1)` 增加 1 份奢侈资源

### 被劫掠时（OnImprovementPillaged_Transnationals）
1. 通过 `Map.GetUnitsAt()` 获取劫掠单位，识别劫掠者
2. 用 `pPlot:GetProperty("TransnationalOwnerID")` 找回原所有者
3. 扣除资源副本：`ChangeResourceAmount(iResourceID, -1)`
4. 用 `WorldBuilder.CityManager():SetPlotOwner(x, y, -1)` 归还地块
5. 用 `ImprovementBuilder.SetImprovementType(pPlot, -1)` 移除改良设施
6. 清除属性：`pPlot:SetProperty("TransnationalOwnerID", -1)`

### 移除时（OnIUmprovementRemovedFromMap_Transnationals）
1. 对比 `iOwner` 与 `pPlot:GetProperty("TransnationalOwnerID")`
2. 匹配时归还地块所有权，清除属性
3. 注意：资源扣除在劫掠时已完成，此处注释掉不重复扣

### 土地易主时（OnImprovementOwnershipChanged_Transnationals）
- 若 `player == -1`（地块被遗弃），强制清除改良设施

### 关键技术点
- `WorldBuilder.CityManager():SetPlotOwner(x, y, playerID, cityID)` — 修改地块归属
- `pPlot:SetProperty(key, value)` / `pPlot:GetProperty(key)` — 存储自定义数据
- `ImprovementBuilder.SetImprovementType(pPlot, -1)` — 强制移除改良
- 用 Property 存储原始所有者再恢复，避免 Lua 无法持久化数据的问题

## SQL 配合

`Core/MonopolyPlus_Improvements.sql`

### 改良设施定义关键字段
| 字段 | 陆地 | 海洋 |
|------|------|------|
| `ImprovementType` | `IMPROVEMENT_LEU_TRANSNATIONAL` | `IMPROVEMENT_LEU_TRANSNATIONAL_SEA` |
| `PrereqTech` | `TECH_ECONOMICS` | `TECH_PLASTICS` |
| `Domain` | `DOMAIN_LAND` | `DOMAIN_SEA` |
| `CanBuildOutsideTerritory` | **1** | **1** |
| `Workable` | **0** | **0** |
| `Appeal` | -2 | -2 |
| `PlunderAmount` | 500 | 500 |
| `Removable` | 1 | 1 |

- `CanBuildOutsideTerritory=1` 是允许在无主地块建造的关键
- `Workable=0` 意味着不占用市民工作位

### ValidResources
跨国公司可建在**所有奢侈和战略资源**上：
```sql
INSERT INTO Improvement_ValidResources
SELECT 'IMPROVEMENT_LEU_TRANSNATIONAL', ResourceType, 0
FROM Resources WHERE ResourceClassType = 'RESOURCECLASS_STRATEGIC'
UNION ALL
SELECT ... FROM Resources WHERE ResourceClassType = 'RESOURCECLASS_LUXURY'
```

### 基础产出
- 陆地：`YIELD_GOLD=4`, `YIELD_SCIENCE=2`
- 海洋：`YIELD_GOLD=4`, `YIELD_SCIENCE=2`

### BonusYieldChanges（随时代递增）
| 科技/市政 | 增产 |
|-----------|------|
| `CIVIC_CAPITALISM` | 金+1 |
| `CIVIC_SPACE_RACE` | 科+1 |
| `CIVIC_GLOBALIZATION` | 金+1, 科+1 |

### 禁止改良建造
在跨国公司地块上禁止建造其他改良：
- 使用 `MODIFIER_LEU_CHANGE_UNIT_OPERATION_AVAILABILITY` 禁止 `UNITOPERATION_BUILD_IMPROVEMENT`
- 条件用 `REQUIREMENT_PLOT_ADJACENT_IMPROVEMENT_TYPE_MATCHES` (MinRange=0,MaxRange=0)

### 兼容性
- `Improvement_YieldsOutsideTerritories` 表注册（保证境外改良产出生效）
- `Improvements_XP2.DisasterResistant=1`（抗自然灾害）

## XML 配合
无独立 XML，文本和图标在 MonopolyPlus 主 SQL 中。
