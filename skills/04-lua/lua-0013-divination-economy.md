# 占卜点数经济系统（来源：0013）

## 做什么
一种替代性平行资源经济系统：玩家积累"占卜点数（Divination Point）"，通过 UI 触发可以按比例转化为科技值、文化值或生产力。生产力的转化最为复杂，采用两阶段注入机制：第一阶段按"剩余进度/3"注入且不超过点数上限，第二阶段在下个 DistrictBuildProgressChanged 事件中根据实际加成倍率补足或完成建造。

## 触发方式
通过 `GameEvents` 从 UI 侧（按钮点击）触发：
- `SiqiSetDivinationPoint` — 设置点数（参数：Propertykey, PointNum）
- `Siqi0013DivinationPointToScience` — 转化为科技
- `Siqi0013DivinationPointToCulture` — 转化为文化
- `Siqi0013DivinationPointToProduction` — 第一阶段生产力注入
- `Siqi0013DivinationPointToProductionLater` — 第二阶段生产力注入

## 涉及文件和函数

| 文件 | 函数 | 作用 |
|------|------|------|
| `Siqi_Leaders_0013_Scripts.lua` | `XianZhouSetDivinationPoint(playerID, params)` | 设置/累积点数 |
| `Siqi_Leaders_0013_Scripts.lua` | `DivinationPointToScience(playerID, params)` | 点数 → 科技（含上限检查） |
| `Siqi_Leaders_0013_Scripts.lua` | `DivinationPointToCulture(playerID, params)` | 点数 → 文化（含上限检查） |
| `Siqi_Leaders_0013_Scripts.lua` | `DivinationPointToProduction(playerID, params)` | 点数 → 生产力（第一阶段，3种分支） |
| `Siqi_Leaders_0013_Scripts.lua` | `DivinationPointToProductionLater(playerID, params)` | 点数 → 生产力（第二阶段，修正注入） |
| `Siqi_Leaders_0013_Scripts.lua` | `CelestialJadeCompleted(playerID, params)` | 奇观/项目完成后返还金币 |
| `Siqi_Leaders_0013_Scripts.lua` | `OnSiqiDistrictCompleted(...)` | 区域建成触发改良设施 |
| Events | `Events.DistrictBuildProgressChanged` | 触发第二阶段生产注入 |

## 核心代码

```lua
-- 科技/文化转化（简单模式）：检查所需进度 vs 有效点数
function DivinationPointToScience(playerID, params)
    local DivinationPoint = pPlayer:GetProperty(key) or 0
    local EffectivePoints = DivinationPoint * (100 - DIVINATION_TO_SCIENCE) / 100
    if (Cost - Progress) >= EffectivePoints then
        -- 点数不够用完 → 全投进去
        pPlayerTechs:ChangeCurrentResearchProgress(EffectivePoints)
        pPlayer:SetProperty(key, pPlayer:GetProperty(key) - DivinationPoint)
    else
        -- 点数超出所需 → 只投所需量，剩余保留
        pPlayerTechs:ChangeCurrentResearchProgress(Cost - Progress)
        pPlayer:SetProperty(key, pPlayer:GetProperty(key) - (Cost - Progress) * 100 / (100 - DIVINATION_TO_SCIENCE))
    end
end

-- 生产力转化（两阶段）：
-- 第一阶段：检查剩余进度，做3种分支
--   (a) 剩余进度/3 >= 有效点数 或 剩余 ≤ 10 → 全投
--   (b) 剩余进度 ≤ 10 且点数 > 剩余 → 只补足剩余
--   (c) 点数 > 剩余/3 且剩余 > 10 → 注入剩余/3（上限200%加速锤），存储进度数据等待第二阶段
function DivinationPointToProduction(playerID, params)
    local AddDivination = math.max((Cost - Progress) / 3, 10) -- 最大200%加速
    if (Cost - Progress) / 3 >= EffectivePoints or 10 >= EffectivePoints then
        -- 分支a：点数不足，全投
        pCityBuildQueue:AddProgress(EffectivePoints)
    elseif 10 >= (Cost - Progress) then
        -- 分支b：剩余进度<10锤，直接补足
        pCityBuildQueue:AddProgress(Cost - Progress)
    else
        -- 分支c：注入1/3进度，保存快照等第二阶段
        pCityBuildQueue:AddProgress(AddDivination)
        pCity:SetProperty(DivinationProduction, DivinationPreviousData)
    end
end

-- 第二阶段：根据实际加成倍率修正
function DivinationPointToProductionLater(playerID, params)
    -- 读取第一阶段保存的快照
    local ProductionModifier = (Progress - PreProgress - PreAddDivination) / PreAddDivination
    local ShouldAddDivination = (Cost - Progress) / (1 + ProductionModifier)
    if ProductionModifier >= 0 and EffectivePoints >= ShouldAddDivination then
        pCityBuildQueue:FinishProgress() -- 正加成 + 点够 → 直接完成
    elseif EffectivePoints <= ShouldAddDivination then
        pCityBuildQueue:AddProgress(EffectivePoints) -- 点不够 → 全投
    else
        pCityBuildQueue:FinishProgress() -- 负加成 + 点够 → 也完成
    end
end
```

## 关键设计要点

1. **三通道资源出口**：同一点数池可灵活分配给科技/文化/生产力，每种转化率独立可调
2. **两阶段生产力注入**：因为建造过程中可能有产能加成变化（政策卡、奇观等），第一阶段注入后等下一次 `DistrictBuildProgressChanged` 计算实际倍率，第二阶段精确补足，避免溢出浪费或不足
3. **损耗系数**：`DIVINATION_TO_SCIENCE/CULTURE/PRODUCTION` 参数（GlobalParameters 读取）控制转换损耗率，点数不是1:1转化
4. **进度快照机制**：通过 city Property `DivinationProduction` 存储 `{Hash, PercentComplete, Progress, Cost, AddDivination}` 在阶段间传递上下文
5. **快照一致性校验**：第二阶段检查 `Hash == PreHash`，防止玩家切换建造项目导致错误注入
