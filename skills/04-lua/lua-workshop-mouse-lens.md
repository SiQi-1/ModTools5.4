# 鼠标/键盘交互透镜模式（来源：MoreLenses 871712879）

## 做什么
创建响应鼠标光标位置和键盘修饰键的交互式透镜。当按下 Ctrl 键+光标移动时，透镜动态刷新显示内容，实现"鼠标悬停着色"效果。同时支持地图拖动时跳过更新以避免性能问题。

## 涉及文件

| 文件 | 角色 |
|------|------|
| `Base/Assets/UI/minimappanel.lua` | `HandleMouseForModdedLens()` — 鼠标/键盘事件路由，Ctrl 键修饰符处理（Settler Lens） |
| `Lenses/CityOverlap/ModLens_CityOverlap.lua` | `HandleMouse()` — 鼠标跟随透镜的范围着色 |

## 像素 1：Ctrl+鼠标 Settler Lens

### 一、键盘修饰符检测

minimappanel.lua 在 `OnInputHandler` 中检测 Ctrl 键状态：

```lua
function OnInputHandler(pInputStruct)
    -- Ctrl 键按下/释放检测
    if pInputStruct:GetKey() == Keys.VK_CONTROL then
        local msg = pInputStruct:GetMessageType()
        if msg == KeyEvents.KeyDown then
            if not m_AltSettlerLensOn and UILens.IsLayerOn(m_HexColoringWaterAvail) then
                m_CurrentCursorPlotID = -1    -- 重置，强制刷新
                m_CtrlDown = true
                m_AltSettlerLensOn = true     -- 启用备用 Settler 透镜
            end
        elseif msg == KeyEvents.KeyUp then
            m_CurrentCursorPlotID = -1
            m_CtrlDown = false
            RefreshSettlerLens()              -- Ctrl 释放时恢复默认
        end
    end

    HandleMouseForModdedLens()  -- 关键：每次输入事件都广播鼠标处理
    -- ... 其余输入处理
end
```

### 二、鼠标处理广播（minimappanel.lua）

```lua
function HandleMouseForModdedLens()
    if not m_isMouseDragging then  -- 地图拖动时不处理
        LuaEvents.ML_HandleMouse() -- 广播给所有监听者

        -- 如果备用 Settler 透镜开启，检查光标位置变化
        if m_AltSettlerLensOn then
            local plotId = UI.GetCursorPlotID()
            if not Map.IsPlot(plotId) then return end
            if m_CurrentCursorPlotID == plotId then return end  -- 不变则跳过
            m_CurrentCursorPlotID = plotId

            if m_CtrlDown then
                RefreshSettlerLens()   -- Ctrl 按住 + 光标移动 → 刷新
            elseif UI.GetInterfaceMode() == InterfaceModeTypes.VIEW_MODAL_LENS then
                RefreshSettlerLens()   -- 透镜模式中 → 刷新
                m_AltSettlerLensOn = false
            else
                RecheckSettlerLens()   -- 退出透镜 → 检查是否需要恢复
                m_AltSettlerLensOn = false
            end
        end
    end
end
```

### 三、Settler Lens 光标跟随着色

当按下 Ctrl 键时，围绕光标位置着色周围地块：

```lua
CITY_WORK_RANGE = GlobalParameters.CITY_MIN_RANGE  -- 默认为 3

function SetSettlerLens()
    local plotId = UI.GetCursorPlotID()
    if not Map.IsPlot(plotId) then return end

    local pPlot = Map.GetPlotByIndex(plotId)
    local localPlayer = Game.GetLocalPlayer()
    local pPlayer = Players[localPlayer]
    local localPlayerVis = PlayersVisibility[localPlayer]

    -- 定义各类型的颜色
    local iUnusableColor = UI.GetColorValue("COLOR_ALT_SETTLER_UNUSABLE")
    local iOverlapColor  = UI.GetColorValue("COLOR_ALT_SETTLER_OVERLAP")
    local iResourceColor = UI.GetColorValue("COLOR_ALT_SETTLER_RESOURCE")
    local iHillColor     = UI.GetColorValue("COLOR_ALT_SETTLER_HILL")
    local iRegularColor  = UI.GetColorValue("COLOR_ALT_SETTLER_REGULAR")

    local tNonDimPlots    = {}
    local tUnusablePlots  = {}
    local tOverlapPlots   = {}
    local tResourcePlots  = {}
    local tHillPlots      = {}
    local tRegularPlots   = {}

    -- 使用六角螺旋迭代器，以光标地块为中心遍历 CITY_WORK_RANGE 范围内的所有地块
    for pRangePlot in PlotAreaSpiralIterator(pPlot, CITY_WORK_RANGE,
            SECTOR_NONE, DIRECTION_CLOCKWISE, DIRECTION_OUTWARDS, CENTRE_INCLUDE) do

        if localPlayerVis:IsRevealed(pRangePlot:GetX(), pRangePlot:GetY()) then
            local plotID = pRangePlot:GetIndex()
            table.insert(tNonDimPlots, plotID)

            -- 分类：先检查重叠工作区 → 不可通行 → 他人领地 → 资源 → 丘陵 → 普通
            if plotWithinWorkingRange(pPlayer, pRangePlot) then
                table.insert(tOverlapPlots, plotID)
            elseif pRangePlot:IsImpassable() then
                table.insert(tUnusablePlots, plotID)
            elseif pRangePlot:IsOwned() and pRangePlot:GetOwner() ~= localPlayer then
                table.insert(tUnusablePlots, plotID)
            elseif plotHasResource(pRangePlot) and playerHasDiscoveredResource(pPlayer, pRangePlot) then
                table.insert(tResourcePlots, plotID)
            elseif pRangePlot:IsHills() then
                table.insert(tHillPlots, plotID)
            else
                table.insert(tRegularPlots, plotID)
            end
        end
    end

    -- 批量着色
    if #tOverlapPlots > 0 then
        UILens.SetLayerHexesColoredArea(m_HexColoringWaterAvail, localPlayer, tOverlapPlots, iOverlapColor)
    end
    if #tUnusablePlots > 0 then
        UILens.SetLayerHexesColoredArea(m_HexColoringWaterAvail, localPlayer, tUnusablePlots, iUnusableColor)
    end
    -- ... 其余类别
end
```

**关键：PlotAreaSpiralIterator 螺旋迭代器**
```lua
-- 来自 LensSupport.lua (whoward69)
-- 以中心地块为起点，自内向外螺旋遍历半径 r 范围内的所有地块
for pPlot in PlotAreaSpiralIterator(pCenterPlot, range,
        SECTOR_NONE,            -- 从哪个扇区开始（NONE = 全部 6 个方向）
        DIRECTION_CLOCKWISE,     -- 顺时针
        DIRECTION_OUTWARDS,      -- 自内向外
        CENTRE_INCLUDE) do       -- 包含中心地块
    -- pPlot 是范围内的每个地块
end
```

### 四、刷新与恢复

```lua
function RefreshSettlerLens()
    UILens.ClearLayerHexes(m_HexColoringWaterAvail)
    SetWaterHexes()  -- 根据 Ctrl 状态调用 SetSettlerLens 或 SetDefaultWaterHexes
end

function SetWaterHexes()
    if not m_CtrlDown then
        SetDefaultWaterHexes()  -- 默认全图水源着色
    else
        SetSettlerLens()         -- Ctrl 按下时用光标跟随着色
    end
end

-- 退出 Settler Lens 时检查是否需要恢复
function RecheckSettlerLens()
    local selectedUnit = UI.GetHeadSelectedUnit()
    if selectedUnit ~= nil then
        if getUnitType(selectedUnit) == "UNIT_SETTLER" then
            RefreshSettlerLens()  -- Settler 仍然选中 → 恢复默认 Settler 透镜
            return
        end
    end
    -- Settler 未选中 → 完全关闭透镜
    if UILens.IsLayerOn(m_HexColoringWaterAvail) then
        UILens.ToggleLayerOff(m_HexColoringWaterAvail)
    end
end
```

## 像素 2：鼠标跟随 CityOverlap Lens

### 一、鼠标处理器注册

CityOverlap 透镜通过 `LuaEvents.ML_HandleMouse` 监听全局鼠标事件：

```lua
-- 在 Initialize 中注册
LuaEvents.ML_HandleMouse.Add(HandleMouse)

-- 实现
local function HandleMouse()
    if m_isOpen then  -- 只在面板打开时处理
        local plotId = UI.GetCursorPlotID()
        if not Map.IsPlot(plotId) then return end

        -- 优化：光标地块不变则跳过
        if m_CurrentCursorPlotID == plotId then return end
        m_CurrentCursorPlotID = plotId

        -- 只在当前透镜激活时刷新
        local lens = {}
        LuaEvents.MinimapPanel_GetActiveModLens(lens)
        if lens[1] == LENS_NAME then
            if Controls.OverlapLensMouseRange:IsChecked() then  -- 用户选择"鼠标范围模式"
                RefreshCityOverlapLens()
            end
        end
    end
end
```

### 二、鼠标范围着色

显示以光标地块为中心的 N 格范围内的城市分布：

```lua
local function SetRangeMouseLens()
    local plotId = UI.GetCursorPlotID()
    if not Map.IsPlot(plotId) then return end

    local pPlot = Map.GetPlotByIndex(plotId)
    local localPlayer = Game.GetLocalPlayer()
    local localPlayerVis = PlayersVisibility[localPlayer]
    local cityPlots = {}
    local normalPlot = {}

    -- 遍历光标周围 m_cityOverlapRange 格
    for pAdjacencyPlot in PlotAreaSpiralIterator(pPlot, m_cityOverlapRange,
            SECTOR_NONE, DIRECTION_CLOCKWISE, DIRECTION_OUTWARDS, CENTRE_INCLUDE) do
        if localPlayerVis:IsRevealed(pAdjacencyPlot:GetX(), pAdjacencyPlot:GetY()) then
            if pAdjacencyPlot:GetOwner() == localPlayer and pAdjacencyPlot:IsCity() then
                table.insert(cityPlots, pAdjacencyPlot:GetIndex())   -- 城市地块高亮
            else
                table.insert(normalPlot, pAdjacencyPlot:GetIndex())  -- 普通地块
            end
        end
    end

    -- 着色
    if table.count(cityPlots) > 0 then
        UILens.SetLayerHexesColoredArea(ML_LENS_LAYER, localPlayer, cityPlots, UI.GetColorValue("COLOR_GRADIENT8_1"))
    end
    if table.count(normalPlot) > 0 then
        UILens.SetLayerHexesColoredArea(ML_LENS_LAYER, localPlayer, normalPlot, UI.GetColorValue("COLOR_GRADIENT8_3"))
    end
end
```

### 三、模式切换

CityOverlap 面板提供两种模式，通过 RadioButton 切换：

```lua
-- 面板 XML 中的 RadioButton
<RadioButton ID="OverlapLensMouseNone" RadioGroup="OverlapMouse" ... />
<RadioButton ID="OverlapLensMouseRange" RadioGroup="OverlapMouse" ... />

-- 模式切换时刷新着色
Controls.OverlapLensMouseNone:RegisterCallback(Mouse.eLClick, RefreshCityOverlapLens)
Controls.OverlapLensMouseRange:RegisterCallback(Mouse.eLClick, RefreshCityOverlapLens)

function RefreshCityOverlapLens()
    UILens.ClearLayerHexes(ML_LENS_LAYER)
    if Controls.OverlapLensMouseRange:IsChecked() then
        SetRangeMouseLens()    -- 鼠标跟随模式
    else
        SetCityOverlapLens()   -- 全图模式
    end
end
```

### 四、范围调节控件

CityOverlap 面板提供 +/- 按钮调节搜索范围：

```lua
local DEFAULT_OVERLAP_RANGE = 6

function IncreseOverlapRange()
    m_cityOverlapRange = m_cityOverlapRange + 1
    Controls.OverlapRangeLabel:SetText(m_cityOverlapRange)
    RefreshCityOverlapLens()
end

function DecreaseOverlapRange()
    if m_cityOverlapRange > 0 then
        m_cityOverlapRange = m_cityOverlapRange - 1
    end
    Controls.OverlapRangeLabel:SetText(m_cityOverlapRange)
    RefreshCityOverlapLens()
end
```

## 性能注意事项

**避免每帧刷新：**
```lua
-- 关键：只有光标地块 ID 变化时才刷新
if m_CurrentCursorPlotID == plotId then
    return  -- 跳过，六边形网格中鼠标在同一地块内微小移动不触发
end
m_CurrentCursorPlotID = plotId
```

**拖动时跳过：**
```lua
function HandleMouseForModdedLens()
    if not m_isMouseDragging then  -- 用户拖动小地图时不处理鼠标透镜
        LuaEvents.ML_HandleMouse()
    end
end
```

**先 Clear 再着色：**
```lua
function RefreshCityOverlapLens()
    UILens.ClearLayerHexes(ML_LENS_LAYER)  -- 批清
    SetRangeMouseLens()                      -- 批着色
end
```

## 完整交互状态机

```
Settler 透镜默认状态: 显示全图水源可用性

用户选择 Settler → 自动开启 Settler 透镜 (OnUnitSelectionChanged)
  显示全图水源着色 (SetDefaultWaterHexes)

用户按住 Ctrl:
  m_CtrlDown = true
  m_AltSettlerLensOn = true
  显示光标周围的地块分级着色 (SetSettlerLens)

用户移动鼠标 (Ctrl 仍按住):
  m_CurrentCursorPlotID 变化 → RefreshSettlerLens()
  重新以新光标位置为中心计算着色

用户释放 Ctrl:
  m_CtrlDown = false
  RefreshSettlerLens() → 回到全图水源着色

用户取消选择 Settler:
  RecheckSettlerLens() → UILens.ToggleLayerOff(WaterAvail)
```

## 设计要点

1. **Ctrl 键修饰符**：通过 `Keys.VK_CONTROL` + `KeyDown/KeyUp` 判断，存储 `m_CtrlDown` 状态
2. **光标地块去重**：`m_CurrentCursorPlotID` 避免同一地块重复计算
3. **拖动时跳过**：`m_isMouseDragging` 标记，拖动小地图时不应刷新
4. **PlotAreaSpiralIterator**：六角格螺旋迭代器是鼠标范围着色的核心工具
5. **先清后设**：每次光标移动都 `ClearLayerHexes` → 重新着色（批量操作），而非逐个修改
6. **LuaEvents 路由**：`ML_HandleMouse` 作为广播事件，允许多个透镜同时监听
7. **模式切换**：通过面板控件的状态（CheckBox/RadioButton）决定着色行为
8. **退出清理**：Ctrl 释放时恢复默认透镜；单位取消选择时完全关闭透镜层

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `Lenses/CityOverlap/ModLens_CityOverlap.xml` | 城市交叠透镜面板：模式切换 RadioButton + 范围调节按钮 |
| `Base/Assets/UI/minimappanel.xml` | MinimapPanel — Ctrl 键检测和鼠标事件广播在此文件内 |

### ModLens_CityOverlap.xml 控件 ID 对照

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `OverlapLensOptionsPanel` | Container | `Controls.OverlapLensOptionsPanel` | 面板根容器 |
| `ShowLensOutsideBorder` | CheckBox | `Controls.ShowLensOutsideBorder` | 是否显示边境外的城市 |
| `OverlapLensMouseNone` | RadioButton | `Controls.OverlapLensMouseNone` | 模式 A：全图城市交叠显示 |
| `OverlapLensMouseRange` | RadioButton | `Controls.OverlapLensMouseRange` | 模式 B：以鼠标光标为中心的 N 格范围 |
| `OverlapRangeDown` | Button | `Controls.OverlapRangeDown` | 减小搜索范围 |
| `OverlapRangeUp` | Button | `Controls.OverlapRangeUp` | 增大搜索范围 |
| `OverlapRangeLabel` | Label | `Controls.OverlapRangeLabel` | 当前范围数值（如 "6"） |

### CityOverlap 面板 XML 结构

```xml
<Context>
  <Container ID="OverlapLensOptionsPanel" Size="230,350" Anchor="L,B" ConsumeMouse="1">
    <Grid Texture="Tracker_OptionsBacking.dds" SliceCorner="55,61">
      <Label String="{LOC_HUD_CITYOVERLAP_LENS:upper}" Style="FontFlair16"/>
      <Stack StackGrowth="Down" Padding="10">
        <CheckBox ID="ShowLensOutsideBorder" IsChecked="1" BoxOnLeft="1"/>
        <RadioButton ID="OverlapLensMouseNone" RadioGroup="OverlapMouse"
                     IsChecked="1" BoxOnLeft="1"/>
        <RadioButton ID="OverlapLensMouseRange" RadioGroup="OverlapMouse"
                     BoxOnLeft="1"/>
      </Stack>
      <Container Anchor="C,B" Size="parent-45,70" Offset="-5,50">
        <Button ID="OverlapRangeDown" Style="ArrowButtonLeft"/>
        <Button ID="OverlapRangeUp" Style="ArrowButtonRight"/>
        <Label ID="OverlapRangeLabel" String="6"/>
      </Container>
    </Grid>
  </Container>
</Context>
```

### Settler Lens 与 XML

Settler 透镜的 Ctrl+鼠标交互不需要额外 XML——完全在 minimappanel.lua 的 `OnInputHandler` 中通过 `Keys.VK_CONTROL` 检测实现。着色结果作用于 `m_HexColoringWaterAvail` 层（原生 Water 透镜层），该层在 minimappanel.xml 中已有 `WaterLensButton` RadioButton。

### 交互流程与控件关系

```
用户按 Ctrl + 移动鼠标
  → minimappanel.xml/OnInputHandler 检测 Keys.VK_CONTROL KeyDown/KeyUp
  → m_CtrlDown 状态切换
  → HandleMouseForModdedLens() → LuaEvents.ML_HandleMouse()
  → ModLens_CityOverlap.lua 监听 ML_HandleMouse
  → 检查 Controls.OverlapLensMouseRange:IsChecked()
  → 如果鼠标范围模式开启 → 重新计算着色
  → UILens.SetLayerHexesColoredArea() 更新地图
```
