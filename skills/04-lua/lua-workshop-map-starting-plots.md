# Custom Starting Plot Assignment — 自定义起始位置分配

参考 Mod: Better Balanced Starts / BBS (2749991372)

## 概述

BBS 替换了原版 `AssignStartingPlots.lua`，提供自定义的出生点评估与分配系统。核心包括：地图类型感知的最小距离计算、正/负出生偏好、多层缓冲检查、产出评估（Fertility Scoring）、以及资源自动补足机制。同时包含独立的资源生成器和地形生成器，可按大陆分配资源。

---

## XML 配合

### BBS_UI.xml — 高级设置面板

`UI/BBS_UI.xml` 定义了 BBS 的游戏设置面板界面，提供以下配置选项：
- BBS 温度 (`BBStemp`) — 地图温度开关
- 山脊模式 (`BBSRidge`) — 山脊生成密度下拉框
- 战略资源密度 (`BBSStratRes`) — 0=标准 / 1=丰富 / 2=史诗 / 3=起始保底
- 最小间距 (`BBSMinDistance`) — 起始位置最小距离
- 森林平衡 (`BBSBalanceForests`) — 森林均衡分配开关
- 自然奇观配置 (`BBSNatural`)

### Config.xml — 配置参数注册

`Configuration/Config.xml` 向 `Parameters` / `DomainValues` / `ParameterCriteria` / `ConfigurationUpdates` 表注册所有 BBS 参数：
- 地图选项（`GroupId="MapOptions"`, SortIndex 220-235）
- BBS 选项（`GroupId="BBSOptions"`）
- 下拉框 Domain 定义（`RidgeDomain`, `StratResDomain`, `MinDistance`, `BalanceForests` 等）
- 地图类型感知的参数共享（每种地图脚本一份 `Key1="Map" Key2="xxx.lua"` 参数条目）

### ConfigText.xml + 多语言 XML

`Configuration/ConfigText.xml` 和 `Lang/english.xml` 等文件提供配置面板的多语言文本。

---

## 系统 1: 最小玩家距离计算

文件: `Data/BBS Maps/Utility/BBS_AssignStartingPlots.lua` (Create 函数)

### 两步计算

```
Phase 1: 根据地图脚本设定基础距离 (base_distance)
Phase 2: 根据地图大小 × 玩家数量微调
```

### 地图类型基础距离

```lua
local mapScript = MapConfiguration.GetValue("MAP_SCRIPT")

-- 陆地密集型地图 (有更多空间) → 更高距离
if mapScript == "Highlands_XP2.lua" or mapScript == "Lakes.lua" then
    Major_Distance_Target = 15
end
if mapScript == "InlandSea.lua" then
    Major_Distance_Target = 14
end
if mapScript == "Seven_Seas.lua" or mapScript == "Primordial.lua" then
    Major_Distance_Target = 13
end
if mapScript == "Pangaea.lua" or mapScript == "Tilted_Axis.lua" then
    Major_Distance_Target = 12
end
-- 水域密集型地图 (空间少) → 更低距离
if mapScript == "Continents.lua" or mapScript == "Fractal.lua" or mapScript == "Island_Plates.lua" then
    Major_Distance_Target = 10
end
if mapScript == "Terra.lua" then
    Major_Distance_Target = 8
end
```

### 玩家数量调整

```lua
-- 如果玩家过多(拥挤) → 减距离; 如果玩家过少(稀疏) → 加距离
-- 例: 标准地图 (size=3)
if realPlayersCount > 9 then
    Major_Distance_Target = Major_Distance_Target - 2
elseif realPlayersCount < 7 then
    Major_Distance_Target = Major_Distance_Target + 2
end
```

### 手动覆盖

```lua
local minDistance = MapConfiguration.GetValue("BBSMinDistance")
if minDistance ~= nil and minDistance ~= 0 then
    Major_Distance_Target = minDistance  -- 直接使用玩家设定
end
```

---

## 系统 2: 出生偏好系统 (Start Bias)

### 正偏好 — 从数据库读取

```lua
-- StartBiasCustom 表: 自定义文明偏好
g_custom_bias = {}
local info_results = DB.Query("SELECT * from StartBiasCustom")
for k, v in pairs(info_results) do
    table.insert(g_custom_bias, {
        CivilizationType = v.CivilizationType,
        CustomPlacement = v.CustomPlacement
    })
end
```

### 负偏好 — 某些文明避免的地形

```lua
-- StartBiasNegatives 表: 负面出生偏好
g_negative_bias = {}
local info_results = DB.Query("SELECT * from StartBiasNegatives")
for k, v in pairs(info_results) do
    table.insert(g_negative_bias, {
        CivilizationType = v.CivilizationType,
        TerrainType = v.TerrainType,
        FeatureType = v.FeatureType,
        Tier = v.Tier,
        Extra = v.Extra
    })
end
```

### 偏好处理方法

```lua
__SetStartBias    -- 为各文明查询和设置偏好
__BiasRoutine      -- 执行偏好评估循环
__FindBias         -- 在地图上找符合偏好的位置
__RateBiasPlots    -- 对偏好位置打分排序
__SetStartMaori    -- 毛利文明特殊海上出生逻辑
```

---

## 系统 3: 缓冲检查 (Buffer Checks)

文件: `BBS_AssignStartingPlots.lua` (多个 __xxxBufferCheck 方法)

### 自然奇观缓冲

```lua
function __NaturalWonderBufferCheck(pPlot)
    -- 检查起始位置周围 N 格内不能有自然奇观
    -- 确保公平性: 不因随机奇观位置造成巨大优势
end
```

### 奢侈品缓冲

```lua
function __LuxuryBufferCheck(pPlot)
    -- 检查周围是否有过多奢侈品聚集
    -- (防止某个起始位置获得不公平的资源优势)
end
```

### 文明间距离缓冲

```lua
__MajorMajorCivBufferCheck   -- 主要文明 vs 主要文明
__MinorMajorCivBufferCheck   -- 城邦 vs 主要文明
__MinorMinorCivBufferCheck   -- 城邦 vs 城邦
```

---

## 系统 4: 产出评估 (Fertility Scoring)

### 核心函数族

```lua
__BaseFertility             -- 根据地形/地貌/资源计算基础产出
__AddBonusFoodProduction    -- 添加额外粮锤
__AddFood                    -- 添加粮食
__AddProduction              -- 添加产能
__ScoreAdjacent              -- 评估相邻地块质量
__CountAdjacentTerrainsInRange  -- 统计范围内地形出现次数
__CountAdjacentFeaturesInRange   -- 统计范围内地貌出现次数
__CountAdjacentResourcesInRange  -- 统计范围内资源出现次数
__CountAdjacentYieldsInRange     -- 统计范围内产出值
```

### 评估模式

BBS 的 `__BaseFertility` 基于默认产出值评估起始地块的"肥沃度"，考虑周围 N 格范围内的地形、地貌、资源密度。这是一个启发式评分系统，与默认 Firaxis 实现的区别在于：

1. **更严格的距离权重**: 近处资源比远处资源更重要
2. **连续性奖励**: 多个同类型高产格连片得分更高
3. **负面特征惩罚**: 沙漠、冻土、冰雪周围的产出扣分

---

## 系统 5: 资源自动补足 (Starting Resource Balancing)

文件: `BBS_AssignStartingPlots.lua` (AddXxx 方法族)

### 奢侈品补足

```lua
__AddLuxury(pPlot)
-- 如果起始位置奢侈品不足，自动在周围添加
-- 注意：使用 __LuxuryCount 判断已有数量
```

### 战略资源补足

```lua
__BalancedStrategic(pPlot)
__FindSpecificStrategic(pPlot, resourceType)
__AddStrategic(pPlot, amount)
-- 根据配置 "BBSStratRes" 决定:
--   0 = 标准 (每人至少 1 铁/马)
--   1 = 丰富 (1.2x)
--   2 = 史诗 (2.5x)
--   3 = 起始保底 (保证首都可见范围内有马/铁)
```

### 加成资源补足

```lua
__AddBonus(pPlot)
__RemoveBonus(pPlot)        -- 移除过于密集的加成资源
__TryToRemoveBonusResource  -- 尝试移除替换为其他
```

### 雷线 (Ley Line) 特殊处理

```lua
__AddLeyLine(pPlot)
-- 如果文明使用秘密结社模式，确保起始位置附近有雷线
```

---

## 系统 6: 回退机制与错误处理

```lua
-- 三种失败标记
bError_major    = false   -- 主要错误 (无法找到足够空间)
bError_minor    = false   -- 次要错误 (城邦放置异常)
bError_proximity= false   -- 距离错误 (玩家间距离过近)
bError_shit_settle = false -- 产出极差位置

bbsFailed = false         -- 综合失败标记

-- 回退到原版 AssignStartingPlots
if bbsFailed then
    print("BBS: Too Many Attempts Failed - Go to Firaxis Placement")
    Game:SetProperty("BBS_RESPAWN", false)
    return AssignStartingPlots.Create(args)
end
```

### 重试循环

当放置失败时，系统会自动调整参数并重试：
- 逐步降低距离要求 (`iHard_Major = Major_Distance_Target`)
- 放宽产出阈值
- 最终回退到原版算法

---

## 系统 7: 独立资源生成器 (BBS_ResourceGenerator)

文件: `Data/BBS Maps/Utility/BBS_ResourceGenerator.lua`

### 与 Sukritact 的资源生成器对比

| 特性 | BBS_ResourceGenerator | Suk_Oceans ResourceGenerator |
|------|----------------------|---------------------------|
| 大陆感知 | 使用 `Map.GetContinentPlots()` | Jump Flood 重建大陆划分 |
| 奢侈品选择 | 洗牌后贪心选取 | 加权随机抽卡 (每大陆 2 种) |
| 水奢侈品 | 纬度分区放置 (热带/赤道) | 每大陆均匀分布 |
| 放置评分 | 500/相邻资源数 + 随机 | 热力图权重 + 邻近惩罚 |
| 重复移除 | `__RemoveDuplicateResources` 遍历移除 | 不在生成阶段处理 |

### 纬度分区水奢侈品

```lua
-- 热带 (纬度 > 35%)
self:__SetWaterLuxury(eChosenLux, 100.0, 35.1)
-- 赤道 (纬度 0~35%)
self:__SetWaterLuxury(eChosenLux, 35.0, 0.0)

function __SetWaterLuxury(eChosenLux, latitudeMax, latitudeMin)
    for x = 0, iW - 1 do
        for y = 0, iH - 1 do
            local lat = math.abs((iH/2) - y) / (iH/2) * 100.0
            if lat < latitudeMax and lat > latitudeMin then
                self:__PlaceWaterLuxury(eChosenLux, pPlot)
            end
        end
    end
end
```

### 放置概率模型

```lua
function __PlaceWaterLuxury(eChosenLux, pPlot)
    local score = TerrainBuilder.GetRandomNumber(iRandom, "...")
    score = score / ((GetAdjacentResourceCount(pPlot) + 1) * (3.0 + iBonusAdjacent))
    if score * seaFrequency >= 85 + 5 * occurrencesPerFrequency then
        ResourceBuilder.SetResourceType(pPlot, resourceType, 1)
        return true
    end
    return false
end
```

### 大陆感知的战略资源权重

```lua
-- 从 Resource_Distribution 表读取 Scarce/Average/Plentiful 分布
for row in GameInfo.Resource_Distribution() do
    if row.Continents == iNumContinents then
        for i = 1, row.Scarce do
            table.insert(aWeight, 1 - row.PercentAdjusted/100)
        end
        for i = 1, row.Average do
            table.insert(aWeight, 1)
        end
        for i = 1, row.Plentiful do
            table.insert(aWeight, 1 + row.PercentAdjusted/100)
        end
    end
end
-- 洗牌后分配到各大陆
aWeight = GetShuffledCopyOfTable(aWeight)
```

---

## 系统 8: 独立地形生成器 (BBS_TerrainGenerator)

文件: `Data/BBS Maps/Utility/BBS_TerrainGenerator.lua`

BBS 也有自定义的地形生成逻辑 `BBS_GenerateTerrainTypes`，基于分形噪声 + 纬度带 + 温度设置来分配地形：

```lua
function BBS_GenerateTerrainTypes(plotTypes, iW, iH, iFlags, bNoCoastalMountains, temperature, ...)
    -- 纬度带定义 (0~1 是南北极到赤道)
    local fSnowLatitude   = 0.86  -- 雪地起始纬度 (86%)
    local fTundraLatitude = 0.63  -- 冻土起始纬度
    local fDesertBottomLatitude = 0.40
    local fDesertTopLatitude    = 0.60
    local fGrassLatitude = 0.10  -- 全草原终止纬度

    -- 温度调整
    if temperature > 2.5 then  -- 冷
        iDesertPercent = iDesertPercent - 16
        fTundraLatitude = fTundraLatitude - 0.15
    elseif temperature < 1.5 then  -- 热
        iDesertPercent = iDesertPercent + 16
        fSnowLatitude = fSnowLatitude + 0.05
        fTundraLatitude = fTundraLatitude + 0.10
    end

    -- 使用分形噪声 (Fractal.Create) 生成沙漠/平原分布
    deserts = Fractal.Create(iW, iH, grain_amount, iFlags, fracXExp, fracYExp)
    iDesertTop = deserts:GetHeight(iDesertTopPercent)
    iDesertBottom = deserts:GetHeight(iDesertBottomPercent)
end
```

---

## 跨系统数据流: 事件注册与配置面板

### BBS_UI.lua — 高级设置面板

BBS 提供自定义游戏设置面板，通过 `BBS_UI.lua` + `BBS_UI.xml` 实现：
- BBS 温度 (BBStemp)
- 山脊模式 (BBSRidge)
- 战略资源密度 (BBSStratRes)
- 最小间距 (BBSMinDistance)
- 森林平衡 (BBSBalanceForests)

这些值通过 `MapConfiguration.GetValue()` 在 Lua 端读取。

### MapConfiguration 读取模式

```lua
-- 带默认值的配置读取
local value = MapConfiguration.GetValue("BBSMinDistance") or 0
local isTempOn = GameConfiguration.GetValue("BBStemp") == true
```

---

## 总结: 三种出生点分配哲学

| 哲学 | 代表实现 | 核心思路 |
|------|---------|----------|
| **距离优先** | BBS | 先算最小距离，再在满足距离的格子中选产出最高的 |
| **产出评估** | BBS `__BaseFertility` | 对候选格打分，选出最"肥沃"的位置 |
| **回退兜底** | BBS `bbsFailed` | 如果自定义算法失败，回退到原版 AssignStartingPlots |

BBS 的精华在于**多级回退**策略：先自定义 → 参数放宽松后重试 → 最终回退原版，保证在任何地图/设置组合下都不会导致地图生成失败。

---

## 相关参考

- `Data/BBS Maps/Utility/BBS_Balance.lua` — 生成后地形/地貌平衡调整
- `Data/BBS Maps/Utility/BBS_NaturalWonderGenerator.lua` — 自然奇观生成
- `Data/BBS Maps/Utility/BBS_MountainsCliffs.lua` — 山脉/悬崖调整
- `sql/bbs_bias_master.sql` — 文明出生偏好数据
- `sql/bbs_new_wonders.sql` — 新增自然奇观定义
- `Configuration/Config.sql` / `Config.xml` — 配置选项注册
