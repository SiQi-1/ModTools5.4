# Map Tacks — 地图钉相邻加成计算

参考 Mod: Detailed Map Tacks (2428969051)

## 核心架构

模块分三层：缓存层 (MapPinSubjectManager) -> 计算层 (YieldCalculator, ModifierCalculator, RequirementChecker) -> UI 层 (MapPinManager, MapPinPopup 覆写)。

MapPinSubject 结构:
```lua
{
    Id = pinID,           -- 原始 MapPin ID
    X, Y,                 -- 坐标
    Key = "DISTRICT_CAMPUS",  -- 游戏内类型标识
    Type = "DISTRICT",    -- MAP_PIN_TYPES 枚举
    YieldString,          -- 拼接好的产出字符串（显示用）
    YieldToolTip,         -- 产出来源详细说明
    CanPlace,             -- 能否放置
    CanPlaceToolTip,      -- 不能放置的原因
}
```

## 模式 1: PlayerConfigurations 缓存 + 序列化

数据持久化在 `PlayerConfigurations[playerID]` 中，通过 serialize/deserialize 读写 Lua 表。同步用 `Network.BroadcastPlayerInfo()`。

```lua
-- 读
local serialized = PlayerConfigurations[playerID]:GetValue("KEY");
local data = deserialize(serialized);

-- 写
local serialized = serialize(data);
PlayerConfigurations[playerID]:SetValue("KEY", serialized);

-- 广播到所有客户端
Network.BroadcastPlayerInfo();
```

Serialize 函数来自 metalua 的 identity-preserving 序列化，支持 table/string/number/boolean/function，支持共享引用和自引用。

## 模式 2: 数据库预缓存

初始化时遍历 GameInfo 表建立查找缓存，避免热路径中反复遍历：

```lua
-- 建筑-地貌兼容性缓存
BuildingRequiredFeature = {};
for row in GameInfo.Building_RequiredFeatures() do
    BuildingRequiredFeature[key] = true;
end

-- Requirement 参数缓存
for row in GameInfo.RequirementArguments() do
    m_CachedRequirementArgsMap[key] = row.Value;
end
```

## 模式 3: 地块特征聚合 (GetRealizedPlotFeatures)

核心函数：给定坐标和假设放置的 MapPin，返回地块上可用的所有 adjacency 特征。需要考虑：
- 放置后哪些特征会被移除（如丛林被伐除）
- 放置后哪些特征会被新建筑/区域替代
- 改良设施对资源的有效性
- 自然奇观不可破坏

返回格式:
```lua
{
    AdjacencyBonusTypes.ADJACENCY_FEATURE = "FEATURE_JUNGLE",
    AdjacencyBonusTypes.ADJACENCY_DISTRICT = "DISTRICT_CAMPUS",
    AdjacencyBonusTypes.ADJACENCY_TERRAIN = "TERRAIN_GRASS_HILLS",
}
```

## 模式 4: 遍历 Adjacency_YieldChanges 计算产出

遍历 `GameInfo.District_Adjacencies()`（区域）或 `GameInfo.Improvement_Adjacencies()`（改良）获取每个相邻加成的 YieldChangeId，然后查 `GameInfo.Adjacency_YieldChanges` 表计算产出：

```lua
for adjRow in GameInfo.District_Adjacencies() do
    if adjRow.DistrictType == districtType then
        local row = GameInfo.Adjacency_YieldChanges[adjRow.YieldChangeId];
        -- row.YieldType, row.YieldChange, row.AdjacentTerrain ...
        -- 检查 prereq/obsolete tech/civic
        -- 检查 ExcludedAdjacencies (特定文明/领袖排除)
        -- 检查 plot:IsRiver(), 相邻地块特征计数等
    end
end
```

Adjacency_YieldChanges 的相邻检查类型：
- `OtherDistrictAdjacent` — 任意区域
- `AdjacentResource` / `AdjacentSeaResource`
- `AdjacentWonder` / `AdjacentNaturalWonder`
- `AdjacentTerrain` / `AdjacentFeature` / `AdjacentImprovement` / `AdjacentDistrict`
- `AdjacentResourceClass`
- `AdjacentRiver` / `Self`

## 模式 5: Modifier 系统遍历

读取当前游戏中所有激活的 modifier，匹配 EffectType 计算额外产出：

```lua
for _, modifierObjID in ipairs(GameEffects.GetModifiers()) do
    local isActive = GameEffects.GetModifierActive(modifierObjID);
    local modifierDef = GameEffects.GetModifierDefinition(modifierObjID);
    -- modifierDef.ModifierType -> GameInfo.DynamicModifiers[row].EffectType
    -- EFFECT_DISTRICT_ADJACENCY, EFFECT_FEATURE_ADJACENCY, 
    -- EFFECT_RIVER_ADJACENCY, EFFECT_ADJUST_DISTRICT_YIELD_BASED_ON_ADJACENCY_BONUS ...
end
```

需要处理的 EffectType 白名单:
- `EFFECT_DISTRICT_ADJACENCY` — 额外区域相邻加成
- `EFFECT_FEATURE_ADJACENCY` — 地貌相邻加成
- `EFFECT_IMPROVEMENT_ADJACENCY` — 改良相邻加成
- `EFFECT_TERRAIN_ADJACENCY` — 地形相邻加成
- `EFFECT_RIVER_ADJACENCY` — 河流相邻加成
- `EFFECT_ADJUST_DISTRICT_YIELD_BASED_ON_ADJACENCY_BONUS` — 镜像产出（如职业道德）
- `EFFECT_ADJUST_VALID_FEATURES_DISTRICTS` — 改变可放置地貌
- `EFFECT_ADJUST_PLAYER_FEAUTE_REQUIRED_FOR_SPECIALTY_DISTRICTS` — 特色区域地貌要求
- `EFFECT_ADJUST_PLAYER_SPECIALTY_DISTRICT_CANNOT_BE_BUILT_ADJACENT_TO_CITY` — 高卢限制

## 模式 6: Requirement 检查系统

手动实现 Requirement 检查（因为 UI 层无法直接调用游戏引擎的 requirement set 评估）：

```lua
ReqCheck["REQUIREMENT_DISTRICT_TYPE_MATCHES"] = function(...)
    return GetModifierRequirementArgValue(requirementId, "DistrictType") == pinSubject.Key;
end
ReqCheck["REQUIREMENT_CITY_FOLLOWS_PANTHEON"] = function(...)
    return DoesPlayerHasModifierPantheon(playerID, modifierSubject.OwnerId);
end
ReqCheck["REQUIREMENT_CITY_FOLLOWS_RELIGION"] = function(...)
    return DoesPinHasModifierReligionBelief(pinSubject, modifierSubject.OwnerId);
end
```

支持的 Requirement 完整性决定了 modifier 计算精确度。新 requirement 需手动添加。

## 模式 7: 地块放置检查

检查 MapPin 对应类型能否放在给定地块上：
- 数据库表: `District_RequiredFeatures`, `District_ValidTerrains`, `Building_RequiredFeatures`, `Improvement_ValidTerrains`
- XP2 扩展: `Features_XP2.ValidDistrictPlacement`, `Features_XP2.ValidWonderPlacement`
- 特殊检查: 堤坝（河流交叉边数+河漫滩数+单河单坝）、金门大桥（地形模式）、渡槽（河流/山/绿洲/湖）、城市中心 3 格间距

## 模式 8: UI 覆写模式

通过 include base file 并缓存重写实现无侵入式 UI 扩展：

```lua
-- 查找 base file
local files = { "mappinmanager_cqui.lua", "mappinmanager.lua" };
for _, file in ipairs(files) do
    include(file);
    if Initialize then break; end
end

-- 缓存并覆写
BASE_MapPinFlag_Refresh = MapPinFlag.Refresh;
function MapPinFlag.Refresh(self)
    BASE_MapPinFlag_Refresh(self);  -- 调用原始逻辑
    UpdateYields(self);             -- 添加自定义逻辑
    UpdateCanPlace(self);
end
```

## 模式 9: 事件驱动刷新

监听游戏事件触发产出重算：

```lua
Events.DistrictAddedToMap.Add(OnDistrictAdded);
Events.DistrictRemovedFromMap.Add(OnDistrictChanged);
Events.ImprovementAddedToMap.Add(OnImprovementAdded);
Events.FeatureRemovedFromMap.Add(OnFeatureRemovedFromMap);
Events.PlotVisibilityChanged.Add(OnPlotVisibilityChanged);
Events.LocalPlayerTurnBegin.Add(OnLocalPlayerTurnBegin);
Events.LoadGameViewStateDone.Add(OnLoadGameViewStateDone);
```

刷新策略：只更新受影响的地图钉（自身 + 相邻 + 3 格内城市中心影响范围）。

## 关键 API

| API | 用途 |
|-----|------|
| `PlayerConfigurations[pid]:GetValue(key)` | 读取持久化数据 |
| `PlayerConfigurations[pid]:SetValue(key, value)` | 写入持久化数据 |
| `Network.BroadcastPlayerInfo()` | 同步到所有客户端 |
| `GameEffects.GetModifiers()` | 遍历所有激活 modifier |
| `GameEffects.GetModifierActive(objID)` | 检查 modifier 是否激活 |
| `GameEffects.GetModifierDefinition(objID)` | 获取 modifier 定义 |
| `GameEffects.GetModifierSubjects(objID)` | 获取 modifier 作用对象 |
| `GameEffects.GetModifierOwner(objID)` | 获取 modifier 拥有者 |
| `GameEffects.GetObjectName(objID)` | 获取对象名称 (LOC_...) |
| `GameEffects.GetObjectType(objID)` | 获取对象类型 |
| `GameEffects.GetModifierOwnerRequirementSet(objID)` | Owner requirement set |
| `GameEffects.GetRequirementSetState(setID)` | 需求集状态 ("Met"/"NotMet") |
| `PlayersVisibility[pid]:IsRevealed(plotIndex)` | 地块是否已揭示 |
| `Map.GetAdjacentPlots(x, y)` | 获取相邻地块 |
| `Players[pid]:GetTechs():HasTech(index)` | 检查科技 |
| `Players[pid]:GetCulture():HasCivic(index)` | 检查市政 |
| `Players[pid]:GetReligion():GetReligionTypeCreated()` | 检查创教状态 |
| `Cities.GetPlotPurchaseCity(x, y)` | 地块归属城市 |
| `RiverManager.GetRiverForFloodplain(x, y)` | 河漫滩对应河流 |
| `RiverManager.CanBeFlooded(plot)` | 地块是否可被洪水淹没 |

## 重要细节

- WonderIndex 在建成的当回合仍为 -1，需等到下回合才能通过 `GetWonderType()` 读到
- 区域和改良设施的 pillaged 状态需要在计算时处理
- `ExcludedAdjacencies` 表包含特定文明/领袖排除的相邻加成
- 特色区域替换 (`DistrictReplaces`) 需递归合并被替换区域的 modifier
- `EFFECT_ATTACH_MODIFIER` 类型的 modifier 会递归产生新的 modifier，需跳过

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `ui/mappinmanager.xml` | MapPinFlag 的 WorldAnchor 叠加层：旗标基座 + 产出容器 + 可放置标记 |
| `ui/dmt_yieldcalculator.xml` | 产出计算器面板（独立 UI） |

### mappinmanager.xml 控件 ID 对照

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `MapPinFlags` | Container | — | 所有 MapPin 旗标的父容器 |
| `Anchor` | WorldAnchor | — | 世界空间锚点（3D 坐标定位） |
| `FlagRoot` | Container | — | 旗标根容器 |
| `FlagBaseOutline` | Image | — | 旗标黑色轮廓 |
| `FlagBase` | Image | — | 旗标底色 |
| `FlagBaseLighten` / `FlagBaseDarken` | Image | — | 旗标亮/暗变体 |
| `NormalSelect` | Image | — | 选中高亮动画 |
| `NormalButton` | Button | — | 旗标点击区域（50x50） |
| `HexIcon` | Image | — | 六角图标（MapPins24） |
| `UnitIcon` | Image | — | 单位/区域/改良图标（24x24） |
| `NameContainer` | Image | — | 名称标签背景 |
| `NameLabel` | Label | — | 图钉名称 |
| `YieldContainer` | Grid | — | DMT 新增：产出数值背景（YieldBacking 样式） |
| `YieldText` | Label | — | DMT 新增：产出文本（YieldBonusText 样式） |
| `CanPlaceIcon` | Image | — | DMT 新增：不可放置警告图标（Alert18, 18x18） |

**Instance 模板：**

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `MapPinFlag` | 单个地图钉旗标 | `Anchor`(WorldAnchor), `NameLabel`(Label), `YieldText`(Label), `CanPlaceIcon`(Image), `UnitIcon`(Image) |

### 完整 MapPinFlag XML 模板

```xml
<Context>
    <Container ID="MapPinFlags"/>
    <Instance Name="MapPinFlag">
        <WorldAnchor ID="Anchor">
            <Container ID="FlagRoot" Anchor="C,B" Size="48,48">
                <Container Anchor="C,C" Size="50,50">
                    <Image Size="59,79" Texture="MapPin" Anchor="C,T" Offset="1,-16"/>
                    <Image ID="FlagBaseOutline" Size="50,50" Texture="MapPinFlag"/>
                    <Image ID="FlagBase" Size="50,50" Texture="MapPinFlag" TextureOffset="150,0"/>
                    <Button ID="NormalButton" Anchor="C,T" Size="50,50" NoDefaultSound="1">
                        <Image ID="HexIcon" Anchor="C,C" Size="32,32" Hide="1"/>
                        <Image ID="UnitIcon" Anchor="C,C" Size="24,24" Texture="MapPins24"/>
                    </Button>
                    <Image ID="NameContainer" Texture="Controls_DropShadow4"
                           Color="0,0,0,150" Size="auto,20"
                           Anchor="C,T" AnchorSide="I,O" Offset="0,-8">
                        <Label ID="NameLabel" Anchor="C,C"
                               Style="FontNormal14" FontStyle="Glow"/>
                    </Image>
                    <!-- DMT 扩展 -->
                    <Grid ID="YieldContainer" Style="YieldBacking"
                          Size="auto,24" Anchor="C,B" Color="0,0,0,128" Offset="1,-17">
                        <Label ID="YieldText" Anchor="C,C" Style="YieldBonusText"/>
                    </Grid>
                    <Image ID="CanPlaceIcon" Texture="Alert18" Size="18,18"
                           Anchor="R,T" Offset="0,3"/>
                </Container>
            </Container>
        </WorldAnchor>
    </Instance>
</Context>
```

### 关键 XML 扩展点

DMT 在 Firaxis 原始的 MapPinFlag Instance 中插入了三个新元素：
- `YieldContainer` + `YieldText`：显示计算出的产出字符串
- `CanPlaceIcon`：显示不可放置警告

这种"在已有 Instance 定义中追加元素"的模式与 `lua-workshop-instance-extension.md` 的模式相同。
