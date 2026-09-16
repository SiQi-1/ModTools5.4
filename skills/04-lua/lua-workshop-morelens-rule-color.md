# 基于规则优先级的地块着色系统（来源：MoreLenses Builder Lens 871712879）

## 做什么
为透镜实现一套可配置的、基于优先级规则的逐地块判定着色系统。通过"颜色优先级 + 规则表 + 外置配置文件"三层架构，使透镜着色逻辑模块化、可扩展、可配置。

## 涉及文件

| 文件 | 角色 |
|------|------|
| `Lenses/Builder/ModLens_Builder.lua` | 规则引擎主文件：优先级定义、颜色映射、规则遍历、危险地块检测、单位事件监听 |
| `Lenses/Builder/BuilderLens_Config_Default.lua` | 默认规则配置文件：12 条规则分别处理国家公园、资源、地热、度假区、掠夺等 |
| `Lenses/Builder/BuilderLens_Support.lua` | 规则辅助函数库：地块检索、有效改良检测、相邻判断、特质/总督检测 |
| `Lenses/LensSupport.lua` | 公共函数库 |
| `Settings/ml_settingspanel.lua` | 设置面板：控制 Builder Lens 的 3 个 GameConfiguration 布尔开关 |

## 架构

### 一层：颜色优先级定义

```lua
-- 颜色按优先级从高到低排列
local m_BuilderLens_PN  = UI.GetColorValue("COLOR_BUILDER_LENS_PN")   -- 无需操作 / 已处理
local m_BuilderLens_PD  = UI.GetColorValue("COLOR_BUILDER_LENS_PD")   -- 危险地块
local m_BuilderLens_P1  = UI.GetColorValue("COLOR_BUILDER_LENS_P1")   -- 优先级 1
local m_BuilderLens_P1N = UI.GetColorValue("COLOR_BUILDER_LENS_P1N")  -- 优先级 1 次选
local m_BuilderLens_P2  = UI.GetColorValue("COLOR_BUILDER_LENS_P2")   -- 优先级 2
-- ... P3, P4, P5, P6, P7 ...

local m_FallbackColor = m_BuilderLens_PN  -- 无规则匹配时的默认颜色

-- 遍历顺序决定优先级（先检查的颜色有更高优先级）
local m_ModLenses_Builder_Priority = {
    m_BuilderLens_PN,  -- 先检查"无需操作"（跳过区）
    m_BuilderLens_PD,  -- 再检查危险区
    m_BuilderLens_P1,  -- 然后是核心推荐
    m_BuilderLens_P2,  -- 次要推荐
    m_BuilderLens_P3,
    m_BuilderLens_P4,
    m_BuilderLens_P5,
    m_BuilderLens_P6,
    m_BuilderLens_P7,
}
```

### 二层：规则配置表

每个颜色槽是一个规则数组，每个规则是一个函数：

```lua
g_ModLenses_Builder_Config = {
    [m_BuilderLens_PN]  = {},  -- 规则数组
    [m_BuilderLens_PD]  = {},  -- 危险地块（运行时填充，非配置文件）
    [m_BuilderLens_P1]  = {},  -- 资源改善
    [m_BuilderLens_P2]  = {},  -- 掠夺/度假区/地热
    [m_BuilderLens_P3]  = {},  -- 推荐地块
    [m_BuilderLens_P4]  = {},  -- 山丘
    [m_BuilderLens_P5]  = {},  -- 可提取特征
    [m_BuilderLens_P6]  = {},
    [m_BuilderLens_P7]  = {},  -- 通用可改良
}

-- 通过 include 通配符加载配置
include("BuilderLens_Config_", true)
```

### 三层：规则函数

每条规则是一个接收 `pPlot` 参数的函数，返回：
- `color_number` — 匹配成功，返回对应的着色值
- `nil` 或 `-1` — 不匹配，继续检查下一条规则
- `-2` — 特殊标记，表示"完全忽略此地块的后续所有规则，也不着色"

```lua
-- 示例：资源改善规则（P1）
table.insert(g_ModLenses_Builder_Config[m_BuilderLens_P1],
    function(pPlot)
        local localPlayer = Game.GetLocalPlayer()
        local pPlayer = Players[localPlayer]
        if pPlot:GetOwner() == localPlayer and not plotHasDistrict(pPlot) then
            if playerHasDiscoveredResource(pPlayer, pPlot) then
                if plotHasImprovement(pPlot) then
                    if plotHasCorrectImprovement(pPlot) then
                        return m_BuilderLens_PN  -- 已有正确改良，标记为"无需操作"
                    end
                end
                if plotResourceImprovable(pPlayer, pPlot) then
                    if plotWithinWorkingRange(pPlayer, pPlot) then
                        return m_BuilderLens_P1    -- 工作范围内 → P1
                    else
                        return m_BuilderLens_P1N   -- 工作范围外 → P1 次选（较轻颜色）
                    end
                else
                    return m_BuilderLens_PN  -- 不可改良，标记为"无需操作"
                end
            end
        end
        return -1  -- 不匹配
    end)
```

### 四层：主着色函数

```lua
local function OnGetColorPlotTable()
    local mapWidth, mapHeight = Map.GetGridSize()
    local localPlayer = Game.GetLocalPlayer()
    local pPlayer = Players[localPlayer]
    local localPlayerVis = PlayersVisibility[localPlayer]

    local colorPlot = {}
    local dangerousPlotsHash = {}
    colorPlot[m_FallbackColor] = {}

    -- 如果启用危险地块检测，先收集所有危险地块
    if not DISABLE_DANGEROUS_PLOT_HIGHLIGHT then
        -- 遍历整个地图，标记敌对单位及其邻接地块
        for i = 0, (mapWidth * mapHeight) - 1, 1 do
            local pPlot = Map.GetPlotByIndex(i)
            if localPlayerVis:IsVisible(pPlot:GetX(), pPlot:GetY()) then
                -- 查找地块上的敌方/蛮族军事单位
                -- 将该单位所在及邻接地块标记为 dangerousPlotsHash[plotIndex] = true
            end
        end
    end

    -- 主循环：遍历所有可见地块
    for i = 0, (mapWidth * mapHeight) - 1, 1 do
        local pPlot = Map.GetPlotByIndex(i)
        -- 跳过危险地块（单独处理）
        if dangerousPlotsHash[i] == nil and localPlayerVis:IsRevealed(pPlot:GetX(), pPlot:GetY()) then
            local bPlotColored = false
            -- 按优先级顺序检查每个颜色槽
            for _, color in ipairs(m_ModLenses_Builder_Priority) do
                config = g_ModLenses_Builder_Config[color]
                if config ~= nil and table.count(config) > 0 then
                    -- 依次执行该颜色槽的每条规则
                    for _, rule in ipairs(config) do
                        if rule ~= nil then
                            ruleColor = rule(pPlot)
                            if ruleColor ~= nil and ruleColor ~= -1 then
                                if ruleColor == -2 then  -- 完全忽略标记
                                    bPlotColored = true
                                    break
                                end
                                if colorPlot[ruleColor] == nil then
                                    colorPlot[ruleColor] = {}
                                end
                                table.insert(colorPlot[ruleColor], i)
                                bPlotColored = true
                                break  -- 已着色，停止此颜色槽的后续规则
                            end
                        end
                    end
                end
                if bPlotColored then break end  -- 已着色，停止后续颜色槽
            end
            -- 无规则匹配且属于本地玩家 → 用默认颜色
            if not bPlotColored and pPlot:GetOwner() == localPlayer then
                table.insert(colorPlot[m_FallbackColor], i)
            end
        end
    end

    -- 危险地块单独追加（确保在一切规则的末尾处理）
    if not DISABLE_DANGEROUS_PLOT_HIGHLIGHT then
        colorPlot[m_BuilderLens_PD] = {}
        for iPlot, _ in pairs(dangerousPlotsHash) do
            table.insert(colorPlot[m_BuilderLens_PD], iPlot)
        end
    end

    return colorPlot
end
```

## 性能优化策略

规则的排列影响性能：
1. **先过滤无关地块（P3 IGNORE_PLOTS）**：非本土地块、有区域、有改良、不可通行等地块直接返回 `-2`（完全忽略），避免后续规则执行
2. **先处理高优先级**：紧急/重要的规则放前面
3. **权重系统**：工作范围内的优先，外的次选

```lua
-- IGNORE PLOTS 规则（在 P3 中，但优先级在 P1/P2 之后）
table.insert(g_ModLenses_Builder_Config[m_BuilderLens_P3],
    function(pPlot)
        if pPlot:GetOwner() ~= localPlayer then return -2 end  -- 非本土地块完全跳过
        if plotHasDistrict(pPlot) then return m_BuilderLens_PN end
        if plotHasImprovement(pPlot) then return m_BuilderLens_PN end
        if pPlot:IsImpassable() then return m_BuilderLens_PN end
        if not plotWithinWorkingRange(pPlayer, pPlot) then return m_BuilderLens_PN end
    end)
```

## GameConfiguration 集成

透镜通过 `GameConfiguration` 读取用户设置：

```lua
-- Bool: 选择 Builder 时是否自动激活透镜
local AUTO_APPLY_BUILDER_LENS = GameConfiguration.GetValue("ML_AutoApplyBuilderLens")
-- Bool: 是否禁用"无需操作"地块的高亮
local DISABLE_NOTHING_PLOT_HIGHLIGHT = GameConfiguration.GetValue("ML_BuilderLensDisableNothingHighlight")
-- Bool: 是否禁用危险地块高亮
local DISABLE_DANGEROUS_PLOT_HIGHLIGHT = GameConfiguration.GetValue("ML_BuilderLensDisableDangerousHighlight")
```

设置变更时通过 LuaEvents 通知：
```lua
LuaEvents.ML_SettingsUpdate.Add(OnLensSettingsUpdate)

local function OnLensSettingsUpdate()
    AUTO_APPLY_BUILDER_LENS = GameConfiguration.GetValue("ML_AutoApplyBuilderLens")
    DISABLE_NOTHING_PLOT_HIGHLIGHT = GameConfiguration.GetValue("ML_BuilderLensDisableNothingHighlight")
    DISABLE_DANGEROUS_PLOT_HIGHLIGHT = GameConfiguration.GetValue("ML_BuilderLensDisableDangerousHighlight")
end
```

## 规则编写常用辅助函数

来自 `LensSupport.lua` 和 `BuilderLens_Support.lua`：

| 函数 | 用途 |
|------|------|
| `plotHasResource(pPlot)` | 地块有资源 |
| `plotHasImprovement(pPlot)` | 地块有改良设施 |
| `plotHasFeature(pPlot)` | 地块有地貌特征 |
| `plotHasDistrict(pPlot)` | 地块有区域 |
| `plotHasWonder(pPlot)` | 地块有人造奇观 |
| `plotHasNaturalWonder(pPlot)` | 地块有自然奇观 |
| `plotWithinWorkingRange(pPlayer, pPlot)` | 地块在城市工作范围（3 格）内 |
| `playerHasDiscoveredResource(pPlayer, pPlot)` | 玩家已发现该地块的资源 |
| `playerCanHave(pPlayer, xmlEntry)` | 玩家满足科技/市政/特质前提 |
| `districtComplete(pPlayer, pPlot)` | 地块上的区域已完工 |
| `PlotRingIterator(pPlot, r, sector, anticlock)` | 六角环迭代器 |
| `PlotAreaSpiralIterator(pPlot, r, sector, anticlock, inwards, centre)` | 六角螺旋区域迭代器 |
| `plotCanHaveImprovement(pPlayer, pPlot, kImprvRow)` | 地块可建造指定改良设施 |
| `plotCanHaveSomeImprovement(pPlayer, pPlot)` | 地块可建造任意改良设施 |
| `plotResourceImprovable(pPlayer, pPlot)` | 地块资源可被改良 |
| `plotHasCorrectImprovement(pPlot)` | 地块有正确的资源改良设施 |

## 配置文件的模块化（Config 文件模式）

```lua
-- BuilderLens_Config_Default.lua
include("BuilderLens_Support")

-- 每条规则自主 table.insert 到对应的颜色槽
table.insert(g_ModLenses_Builder_Config[m_BuilderLens_P1],
    function(pPlot)
        -- ... 判断逻辑 ...
        return m_BuilderLens_P1  -- 或 -1（不匹配）
    end)

table.insert(g_ModLenses_Builder_Config[m_BuilderLens_P2],
    function(pPlot)
        -- ...
    end)
```

**包含机制：**
```lua
-- ModLens_Builder.lua 中
include("BuilderLens_Config_", true)  -- 加载所有 BuilderLens_Config_*.lua
```

这允许第三方 Mod 创建自己的 `BuilderLens_Config_MyMod.lua` 文件，向规则系统中添加自定义规则，而无需修改核心文件。

## 设计要点

1. **优先级顺序**：`m_ModLenses_Builder_Priority` 数组的顺序决定检查顺序，先匹配先着色
2. **规则返回协议**：返回颜色值=匹配；返回 nil/-1=跳过；返回 -2=完全忽略此地块
3. **颜色槽数组**：同一优先级可有多个颜色，规则可返回任意已定义颜色
4. **break 机制**：一旦规则匹配（返回非 nil 且非 -1），停止该颜色槽剩余规则的执行
5. **危险地块单独通道**：在规则引擎之外并行收集，最后追加到 colorPlot
6. **include 通配符配置**：`include("BuilderLens_Config_", true)` 实现规则文件热插拔
7. **性能关键**：IGNORE 规则尽早执行（返回 -2），避免对已处理地块做无效计算

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `Base/Assets/UI/minimappanel.xml` | 透镜面板容器 — 规则着色结果最终在此面板的 `LensToggleStack` 中通过按钮激活触发 |
| `Base/Assets/UI/Panels/modallenspanel.xml` | 图例面板 — 显示 `Legend` 中定义的颜色分类条目 |
| `Settings/ml_settingspanel.xml` | 设置面板 — 含 3 个 Builder Lens 开关：`AutoApplyBuilderLensCheckbox`、`BuilderLensDisableNothing`、`BuilderLensDisableDangerous` |

### Settings 面板控件 ID 对照

| XML 控件（ID） | 类型 | GameConfiguration Key | 用途 |
|---------------|------|----------------------|------|
| `AutoApplyBuilderLensCheckbox` | GridButton (CheckBoxControl) | `ML_AutoApplyBuilderLens` | 选择 Builder 时自动激活透镜 |
| `BuilderLensDisableNothing` | GridButton (CheckBoxControl) | `ML_BuilderLensDisableNothingHighlight` | 禁用"无需操作"高亮 |
| `BuilderLensDisableDangerous` | GridButton (CheckBoxControl) | `ML_BuilderLensDisableDangerousHighlight` | 禁用危险地块高亮 |
| `AutoApplyScoutLensCheckbox` | GridButton (CheckBoxControl) | `ML_AutoApplyScoutLens` | 选择侦察单位时自动激活 |
| `AutoApplyScoutLensExtraCheckbox` | GridButton (CheckBoxControl) | `ML_AutoApplyScoutLensExtra` | 扩展至所有军事陆地单位 |
| `ConfirmButton` | GridButton (ButtonConfirm) | — | 确认并关闭设置 |
| `SettingsPanel` | Container | — | 设置弹窗根容器（380x512） |

### Settings 面板布局

```xml
<Context>
  <Container ID="SettingsPanel" Size="380,512" Anchor="C,C" ConsumeMouse="1">
    <Grid Style="ShellHeaderContainer">
      <Label String="LOC_HUD_ML_SETTINGS_PANEL_TITLE"/>
    </Grid>
    <Stack Anchor="C,T" StackGrowth="Down" Padding="5" Offset="0,50">
      <GridButton ID="AutoApplyBuilderLensCheckbox" Style="CheckBoxControl" />
      <GridButton ID="BuilderLensDisableNothing" Style="CheckBoxControl" />
      <GridButton ID="BuilderLensDisableDangerous" Style="CheckBoxControl" />
      <GridButton ID="AutoApplyScoutLensCheckbox" Style="CheckBoxControl" />
      <GridButton ID="AutoApplyScoutLensExtraCheckbox" Style="CheckBoxControl" />
    </Stack>
    <GridButton ID="ConfirmButton" Style="ButtonConfirm" String="LOC_AUTONARRATE_BUTTON_DONE"/>
  </Container>
</Context>
```

### 规则配置与 XML 的桥接

规则引擎本身不需要 XML 控件，但着色结果通过 `UILens.SetLayerHexesColoredArea()` 作用于透镜层，而透镜层由 minimappanel.xml 中的 `LensButtonInstance` 按钮激活。颜色定义来自 Colors.xml，值通过 `UI.GetColorValue()` 获取：

```xml
<!-- Colors.xml 示例 -->
<Color Name="COLOR_BUILDER_LENS_P1"  Red="0.200" Green="0.800" Blue="0.200" Alpha="1.000"/>
<Color Name="COLOR_BUILDER_LENS_P1N" Red="0.000" Green="0.460" Blue="0.000" Alpha="1.000"/>
<Color Name="COLOR_BUILDER_LENS_PD"  Red="0.800" Green="0.000" Blue="0.000" Alpha="1.000"/>
```
