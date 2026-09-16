# 仓库系统（来源：工坊 2479197624 MonopolyPlus）

## 做什么
建造仓库/集装箱码头后，Lua 扫描相邻地块有无奢侈资源，设置 Plot Property 标记。
SQL 端根据 Property 触发相邻加成、贸易路线加成、公司加成等效果。

这是一种 **Lua Property + SQL Requirement 联动** 的模式：Lua 负责"发现并标记"，SQL 负责"标记后兑现效果"。

## Lua 端

`lua/Leu_Warehouse_Functions.lua`

### 核心变量
```lua
local iProperty = "Leu_Warehouse_Has_"           -- 属性键前缀
local iImprovement = "IMPROVEMENT_LEU_WAREHOUSE"   -- 仓库
local iNavalImprovement = "IMPROVEMENT_LEU_CONTAINER_PORT" -- 集装箱码头
```

### 奢侈品表构建
1. 从 `GameInfo.Resources()` 获取所有奢侈资源 → `tLuxuries`
2. 检查 `CAPABILITY_MONOPOLIES` 是否激活
3. 从 `GameInfo.Improvement_ValidResources` 中筛选垄断模式有效的奢侈资源 → `tValidLuxury`

### 建造时（Leu_Warehouse_ImprovementCreated）
1. 检查自身格位是否有资源（`iPlot:GetResourceType() == -1`）
2. 若自身无资源，扫描**相邻 6 格**：
   ```lua
   for direction = 0, DirectionTypes.NUM_DIRECTION_TYPES - 1, 1 do
       local adjacentPlot = Map.GetAdjacentPlot(iX, iY, direction)
       -- 排除城市中心格
       if adjacentPlot and not adjacentPlot:IsCity() then
           adjResource = adjacentPlot:GetResourceType()
           -- 匹配 tValidLuxury 表
           if 匹配 then
               iPlot:SetProperty("Leu_Warehouse_Has_" .. iResourceTypeStr, 1)
           end
       end
   end
   ```
3. 对每种相邻奢侈资源设置属性值为 1

### 移除时（Leu_Warehouse_ImprovementRemoved）
1. 遍历所有 `tValidLuxury`
2. 将所有 `Leu_Warehouse_Has_XXX` 属性清零：
   ```lua
   iPlot:SetProperty("Leu_Warehouse_Has_" .. iResourceTypeStr, 0)
   ```

### 事件绑定
```lua
if bMonopoliesActive == true then
    Events.ImprovementAddedToMap.Add(Leu_Warehouse_ImprovementCreated)
    Events.ImprovementRemovedFromMap.Add(Leu_Warehouse_ImprovementRemoved)
end
```
仅在垄断模式激活时才注册事件。

### 关键技术点
- `DirectionTypes.NUM_DIRECTION_TYPES` — 获取相邻方向的总数（6）
- `Map.GetAdjacentPlot(x, y, direction)` — 获取相邻地块
- `adjacentPlot:IsCity()` — 排除城市中心（城市中心=区域，不产资源）
- Property 名称拼接：`"Leu_Warehouse_Has_" .. ResourceType` 作为属性键
- 只扫描自身无资源的仓库格（有资源格本身就能建行业）

## SQL 配合

### Corporation Boost 联动
`Core/MonopolyPlus_ImprovementsCorporationBoost.sql`

仓库/集装箱码头的 Property 被用作 Requirement 条件：
```sql
-- 临时表存储映射
CREATE TABLE Leu_CorporationResourceReqs (
    ResourceType     TEXT PRIMARY KEY,
    BoostModifier    TEXT,        -- LEU_INVESTOR_CORPORATION_BOOST_XXX
    AdjRequirementSet TEXT,      -- LEU_BOOSTER_ADJ_TO_XXX
    CorpRequirementSet TEXT,     -- LEU_IS_XXX_CORPORATION
    PropertyRequirement TEXT,    -- REQUIRES_LEU_ADJ_XXX_PROPERTY
    ResourceRequirement TEXT,    -- REQUIRES_LEU_CORP_TILE_HAS_XXX
    ResourceProperty  TEXT       -- Leu_Warehouse_Has_XXX
);

-- 从 ResourceCorporations 表自动填充
INSERT INTO Leu_CorporationResourceReqs
SELECT ResourceType, 'LEU_INVESTOR_CORPORATION_BOOST_'||ResourceType, ...
FROM ResourceCorporations;
```

#### 效果链
1. **Property Requirement**：
   ```sql
   INSERT INTO Requirements
   SELECT PropertyRequirement, 'REQUIREMENT_PLOT_PROPERTY_MATCHES'
   -- Args: PropertyName=Leu_Warehouse_Has_XXX, PropertyMinimum=1
   ```

2. **Corporation Plot Requirement**：
   ```sql
   INSERT INTO RequirementSetRequirements
   SELECT CorpRequirementSet, ResourceRequirement   -- 地块有对应资源
   UNION ALL
   SELECT CorpRequirementSet, 'LEU_WAREHOUSE_CORPORATION_PLOT' -- 地块是公司改良
   ```

3. **Boost Modifier**（地块产出）：
   ```sql
   -- ModifierType = MODIFIER_GAME_ADJUST_PLOT_YIELD
   -- OwnerRequirementSet = AdjRequirementSet (相邻仓库+Property=1)
   -- SubjectRequirementSet = CorpRequirementSet (公司地块+该资源)
   -- Args: YieldType='YIELD_GOLD', Amount=5
   ```

4. **Trade Route Modifier**（商路加成）：
   ```sql
   -- 自定义 ModifierType: MODIFIER_LEU_MONOPOLY_PLOT_ATTACH_MODIFIER
   -- DynamicModifier: COLLECTION_ALL_PLOT_YIELDS → EFFECT_ATTACH_MODIFIER
   -- Args: ModifierId='CIVIC_GRANT_ONE_TRADE_ROUTE'
   ```
   当仓库相邻某奢侈资源且该资源有公司时，赋予该地块一个额外的商路 modifier。

### DynamicModifier 注册
```sql
INSERT INTO Types VALUES ('MODIFIER_LEU_MONOPOLY_PLOT_ATTACH_MODIFIER', 'KIND_MODIFIER');
INSERT INTO DynamicModifiers VALUES
('MODIFIER_LEU_MONOPOLY_PLOT_ATTACH_MODIFIER',
 'COLLECTION_ALL_PLOT_YIELDS',
 'EFFECT_ATTACH_MODIFIER');
```

### 仓库基础定义
| 改良设施 | 前置科技 | 产出 |
|----------|----------|------|
| `IMPROVEMENT_LEU_WAREHOUSE` | TECH_ECONOMICS | 金4, 锤1 |
| `IMPROVEMENT_LEU_CONTAINER_PORT` | TECH_PLASTICS | 金4, 锤2 |

- `RequiresAdjacentLuxury=1` — 必须与奢侈资源相邻
- `OnePerCity=1` — 每城限一
- `OnlyOpenBorders=1` — 不能建在开边地块（防止建在别人领土旁？）

### 相邻加成
仓库/码头为商业中心、港口、工业区提供产出加成：
- 仓库 → 商业中心 +2金，工业区 +2锤
- 码头 → 商业中心 +2金，工业区 +2锤

### 贸易路线加成
```sql
-- MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD_PER_IMPROVEMENT_AT_LOCATION
-- Args: ImprovementType, Origin=1, YieldType, Amount
```
- 仓库：+5金 / +2锤 每条商路
- 码头：+5金 / +2锤 每条商路
- 公司地块额外：+1金 / +1锤

## XML 配合
无独立 XML，文本在 MonopolyPlus Text SQL 文件中。
