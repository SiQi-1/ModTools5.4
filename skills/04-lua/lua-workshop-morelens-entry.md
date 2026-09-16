# 透镜入口数据结构与注册模式（来源：MoreLenses 871712879）

## 做什么
定义单个透镜的完整入口数据结构，说明如何自注册到 MoreLenses 插件架构的两个全局表中，使透镜的小地图按钮、着色逻辑和图例面板都能正常工作。

## 涉及文件

| 文件 | 角色 |
|------|------|
| `Lenses/Wonder/ModLens_Wonder.lua` | 最简洁的透镜实现，展示最小入口 |
| `Lenses/Barbarian/ModLens_Barbarian.lua` | 同上，单一颜色分类 |
| `Lenses/Scout/ModLens_Scout.lua` | 带自动应用 + 事件监听的透镜 |
| `Lenses/Builder/ModLens_Builder.lua` | 带配置系统和规则引擎的复杂透镜 |
| `Lenses/Resource/ModLens_Resource.lua` | 带独立附件面板的透镜 |
| `Lenses/CityOverlap/ModLens_CityOverlap.lua` | 鼠标交互 + 附加面板 |
| `Base/Assets/UI/minimappanel.lua` | 消费入口数据的核心文件 |
| `Base/Assets/UI/Panels/modallenspanel.lua` | 消费图例数据的核心文件 |

## 透镜入口完整数据结构

```lua
local MyLensEntry = {
    -- [必填] 按钮文本的 LOC_ key
    LensButtonText = "LOC_HUD_MY_LENS",

    -- [必填] 按钮提示的 LOC_ key
    LensButtonTooltip = "LOC_HUD_MY_LENS_TOOLTIP",

    -- [可选] 排序权重，越小越靠前。不填默认 999
    SortOrder = 100,

    -- [可选] 初始化函数，注册游戏事件监听。签名: function()
    Initialize = OnInit,

    -- [可选] 透镜切换回调，用于打开/关闭附加面板。签名: function()
    OnToggle = TogglePanel,

    -- [可选] 返回着色数据表。签名: function() → { [color] = {plotID, ...}, ... }
    -- 与 NonStandardFunction 二选一。如果不需要自定义触发（如附加面板自己触发），填 nil
    GetColorPlotTable = OnGetColorPlotTable,

    -- [可选] 替代 GetColorPlotTable 的自定义着色函数（不做标准化着色）。签名: function()
    NonStandardFunction = OnNonStandardColoring,
}
```

## 自注册模式

### 双表注册（透镜文件末尾）

每个透镜文件在文件末尾（全局作用域）向两个表注册：

```lua
local LENS_NAME = "ML_MY_LENS"
local ML_LENS_LAYER = UILens.CreateLensLayerHash("Hex_Coloring_Appeal_Level")

-- ========== 向 minimappanel.lua 注册 ==========
if g_ModLenses ~= nil then
    g_ModLenses[LENS_NAME] = MyLensEntry
end

-- ========== 向 modallenspanel.lua 注册 ==========
if g_ModLensModalPanel ~= nil then
    g_ModLensModalPanel[LENS_NAME] = {
        LensTextKey = "LOC_HUD_MY_LENS",
        Legend = {
            {"LOC_TOOLTIP_MY_CAT1", UI.GetColorValue("COLOR_MY_CAT1")},
            {"LOC_TOOLTIP_MY_CAT2", UI.GetColorValue("COLOR_MY_CAT2")},
        }
    }
end
```

**为什么用 `if ... ~= nil then` 守卫：**
- 这两个全局表分别在 minimappanel.lua 和 modallenspanel.lua 中创建
- 如果某个面板没有被加载（例如其他 Mod 覆盖），注册会静默跳过
- 确保透镜文件可以独立存在，不与特定面板耦合

## GetColorPlotTable 标准模式

这是透镜中最核心的函数。返回一个 `{ [颜色值] = {地块ID列表} }` 的表：

```lua
local function OnGetColorPlotTable()
    local mapWidth, mapHeight = Map.GetGridSize()
    local localPlayer = Game.GetLocalPlayer()
    local localPlayerVis = PlayersVisibility[localPlayer]

    -- 定义颜色
    local Cat1Color = UI.GetColorValue("COLOR_MY_CAT1")
    local Cat2Color = UI.GetColorValue("COLOR_MY_CAT2")
    local IgnoreColor = UI.GetColorValue("COLOR_MORELENSES_GREY")

    -- 初始化返回表
    local colorPlot = {}
    colorPlot[Cat1Color] = {}
    colorPlot[Cat2Color] = {}
    colorPlot[IgnoreColor] = {}

    -- 遍历所有地块，分类
    for i = 0, (mapWidth * mapHeight) - 1, 1 do
        local pPlot = Map.GetPlotByIndex(i)
        if localPlayerVis:IsRevealed(pPlot:GetX(), pPlot:GetY()) then
            if someCondition1(pPlot) then
                table.insert(colorPlot[Cat1Color], i)
            elseif someCondition2(pPlot) then
                table.insert(colorPlot[Cat2Color], i)
            else
                table.insert(colorPlot[IgnoreColor], i)
            end
        end
    end

    return colorPlot
end
```

**颜色值来源：**
```lua
UI.GetColorValue("COLOR_<ColorName>")
-- 颜色定义在 Colors.xml 中注册，如：
-- <Color Name="COLOR_BUILDER_LENS_P1"          Red="0.400" Green="0.400" Blue="0.443" Alpha="1.000"/>
```

## Initialize 事件注册模式

需要生命周期管理的透镜在此注册游戏事件：

```lua
local function OnInitialize()
    -- 单位选择时自动切换透镜
    Events.UnitSelectionChanged.Add(OnUnitSelectionChanged)
    -- 单位从地图移除时关闭透镜
    Events.UnitRemovedFromMap.Add(OnUnitRemovedFromMap)
    -- 单位移动完成时刷新透镜
    Events.UnitMoveComplete.Add(OnUnitMoveComplete)
    -- 特定游戏事件
    Events.GoodyHutReward.Add(OnGoodyHutReward)
    -- 设置更新
    LuaEvents.ML_SettingsUpdate.Add(OnLensSettingsUpdate)
end
```

## 主动激活/停用透镜（使用 LuaEvents）

当透镜需要自动激活（如选择特定单位时）而不通过按钮：

```lua
-- 激活
local function ShowMyLens()
    LuaEvents.MinimapPanel_SetActiveModLens(LENS_NAME)
    UILens.ToggleLayerOn(ML_LENS_LAYER)
end

-- 停用
local function ClearMyLens()
    if UILens.IsLayerOn(ML_LENS_LAYER) then
        UILens.ToggleLayerOff(ML_LENS_LAYER)
    end
    LuaEvents.MinimapPanel_SetActiveModLens("NONE")
end
```

## 运行时动态注册（非 include 扫描）

对于自身不是 `ModLens_*.lua` 文件的透镜，可以在 `LoadScreenClose` 事件中注册：

```lua
-- 在 Resource Lens 的 Initialize() 中
Events.LoadScreenClose.Add(function()
    LuaEvents.MinimapPanel_AddLensEntry(LENS_NAME, MyLensEntry)
    LuaEvents.ModalLensPanel_AddLensEntry(LENS_NAME, MyModalPanelEntry)
end)
```

## NonStandardFunction 模式

当透镜着色逻辑不能简单地用 `{color → plots}` 表表达时，使用此模式：

```lua
-- 入口定义
MyLensEntry = {
    ...
    GetColorPlotTable = nil,   -- 不使用标准模式
    NonStandardFunction = OnNonStandardColoring,
}

-- 实现完全自由的着色
local function OnNonStandardColoring()
    -- 可以调用任何 UILens API
    -- 可以逐个地块着色（性能差但灵活）
    -- 可以组合多个透镜层
end
```

## OnToggle 附加面板模式

当透镜需要显示一个配置面板时：

```lua
MyLensEntry = {
    ...
    OnToggle = TogglePanel,
    GetColorPlotTable = nil,   -- 着色由面板内部控制
}
```

## 最小透镜示例（Wonder）

```lua
include("LensSupport")

local LENS_NAME = "ML_WONDER"
local ML_LENS_LAYER = UILens.CreateLensLayerHash("Hex_Coloring_Appeal_Level")

local function OnGetColorPlotTable()
    local localPlayerVis = PlayersVisibility[Game.GetLocalPlayer()]
    local NaturalWonderColor = UI.GetColorValue("COLOR_NATURAL_WONDER_LENS")
    local PlayerWonderColor = UI.GetColorValue("COLOR_PLAYER_WONDER_LENS")
    local IgnoreColor = UI.GetColorValue("COLOR_MORELENSES_GREY")
    local colorPlot = { [NaturalWonderColor] = {}, [PlayerWonderColor] = {}, [IgnoreColor] = {} }

    local mapWidth, mapHeight = Map.GetGridSize()
    for i = 0, (mapWidth * mapHeight) - 1, 1 do
        local pPlot = Map.GetPlotByIndex(i)
        if localPlayerVis:IsRevealed(pPlot:GetX(), pPlot:GetY()) then
            if plotHasWonder(pPlot) then
                table.insert(colorPlot[PlayerWonderColor], i)
            elseif plotHasNaturalWonder(pPlot) then
                table.insert(colorPlot[NaturalWonderColor], i)
            else
                table.insert(colorPlot[IgnoreColor], i)
            end
        end
    end
    return colorPlot
end

local WonderLensEntry = {
    LensButtonText = "LOC_HUD_WONDER_LENS",
    LensButtonTooltip = "LOC_HUD_WONDER_LENS_TOOLTIP",
    Initialize = nil,
    GetColorPlotTable = OnGetColorPlotTable,
}

if g_ModLenses ~= nil then
    g_ModLenses[LENS_NAME] = WonderLensEntry
end
if g_ModLensModalPanel ~= nil then
    g_ModLensModalPanel[LENS_NAME] = {
        LensTextKey = "LOC_HUD_WONDER_LENS",
        Legend = {
            {"LOC_TOOLTIP_WONDER_LENS_NWONDER", UI.GetColorValue("COLOR_NATURAL_WONDER_LENS")},
            {"LOC_TOOLTIP_RESOURCE_LENS_PWONDER", UI.GetColorValue("COLOR_PLAYER_WONDER_LENS")},
        }
    }
end
```

## 设计要点

1. **LENS_NAME 约定**：使用 `"ML_<NAME>"` 格式作为唯一标识符
2. **ML_LENS_LAYER 常量**：始终使用 `UILens.CreateLensLayerHash("Hex_Coloring_Appeal_Level")` 因为所有模组透镜寄生在 Appeal 层
3. **双表 nil 守卫**：确保透镜文件可被安全 include，不依赖全局表的存在
4. **GetColorPlotTable 返回的结构**：`{ [color_number] = {plot_indexes} }`，key 是 `UI.GetColorValue()` 返回的数值
5. **Legend 结构**：`{ {LOC_String, ColorValue}, ... }`，传递给 `AddKeyEntry(unpack(...))`
6. **初始化顺序**：所有 include 扫描在模块加载时完成，`InitializeModLens()` 在面板初始化时调用

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `Base/Assets/UI/minimappanel.xml` | 透镜面板布局，含 `LensButtonInstance` 模板定义 |
| `Base/Assets/UI/Panels/modallenspanel.xml` | 图例面板布局，含 `KeyEntry` 模板定义 |

### 透镜入口关联的 XML 控件

每个透镜入口在 minimappanel.lua 中通过 InstanceManager 创建按钮，对应 XML 中的 `LensButtonInstance`：

| Lua 字段 | 对应 XML 控件 | 说明 |
|---------|-------------|------|
| `LensButtonText` | `LensButton:GetTextButton():LocalizeAndSetText(...)` | 按钮文本 |
| `LensButtonTooltip` | `LensButton:SetToolTipString(...)` | 按钮提示 |
| `SortOrder` | 无直接映射 | 控制 `InitLens()` 中的创建顺序 |
| `Initialize` | 无直接映射 | 注册事件监听 |
| `OnToggle` | 无直接映射 | 面板开关回调 |
| `GetColorPlotTable` | 无直接映射 | 返回 `{[color]=plots}` 着色数据 |

### LensButtonInstance 模板

```xml
<Instance Name="LensButtonInstance">
  <RadioButton ID="LensButton" RadioGroup="ActiveLens"
               ButtonTexture="Controls_RadioButtonLarge.dds"
               ButtonSize="35,35" CheckSize="35,35"
               CheckTextureOffset="0,35" BoxOnLeft="1"/>
</Instance>
```

### 图例 KeyEntry 模板

```xml
<Instance Name="KeyEntry">
  <Image ID="KeyColorImage" Size="32,36" Texture="Controls_KeySwatchHex">
    <Stack ID="KeyInfoStack" StackGrowth="Down" Anchor="L,C" Offset="38,0">
      <Label ID="KeyLabel" Style="FontNormal14" WrapWidth="140"/>
      <Stack ID="KeyBonusStack" StackGrowth="Right">
        <Image ID="KeyBonusImage" Size="16,16" Icon="ICON_HOUSING" IconSize="16"/>
        <Label ID="KeyBonusLabel" Offset="0,2" Style="FontNormal14"/>
      </Stack>
    </Stack>
  </Image>
</Instance>
```

### 透镜文件与 Colors.xml 配合

透镜着色使用的颜色值来自 `Colors.xml`：
```xml
<Colors>
  <Color Name="COLOR_MORELENSES_GREY" Red="0.400" Green="0.400" Blue="0.443" Alpha="1.000"/>
  <Color Name="COLOR_BUILDER_LENS_P1" Red="0.200" Green="0.800" Blue="0.200" Alpha="1.000"/>
  <!-- ... -->
</Colors>
```

Lua 中通过 `UI.GetColorValue("COLOR_XXX")` 获取数值，传递给 `UILens.SetLayerHexesColoredArea()`。
