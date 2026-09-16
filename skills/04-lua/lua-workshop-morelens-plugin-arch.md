# MoreLenses 透镜插件架构（来源：MoreLenses 871712879）

## 做什么
通过替换游戏原生 MinimapPanel，建立一套可插拔的透镜插件系统。第三方 Mod 只需创建一个 Lua 文件并放入 `Lenses/` 目录，即可自动注册为新透镜——无需修改核心代码。同时替换 ModalLensPanel 以显示自定义透镜的图例。

## 涉及文件

| 文件 | 角色 |
|------|------|
| `Base/Assets/UI/minimappanel.lua` | 替换游戏 MinimapPanel：添加 `g_ModLenses` + `InitLens()` + `ToggleModLens()` + LuaEvents 通信 |
| `Base/Assets/UI/Panels/modallenspanel.lua` | 替换游戏 ModalLensPanel：添加 `g_ModLensModalPanel` + `ShowModLensKey()` |
| `Lenses/LensSupport.lua` | 公用函数库：地块检测、文明/领袖特质检测、六角网格迭代器等 |
| `Lenses/ModLens_*.lua` (8+ 文件) | 各独立透镜插件，自动发现加载 |
| `DLC/Expansion1/UI/Replacements/minimappanel.xml` | 扩展包 1 XML（添加 LoyaltyLens） |
| `DLC/Expansion2/UI/Replacements/minimappanel.xml` | 扩展包 2 XML（添加 PowerLens + LoyaltyLens） |

## 架构原理

### 一、MinimapPanel 替换

**项目配置：**
```xml
<!-- 在 ModBuddy .modinfo 或 .civ6proj 中配置 UI 替换 -->
<ReplaceUIScript>
    <LuaContext>MinimapPanel</LuaContext>
    <LuaReplace>Base/Assets/UI/minimappanel.lua</LuaReplace>
</ReplaceUIScript>
<ReplaceUIScript>
    <LuaContext>ModalLensPanel</LuaContext>
    <LuaReplace>Base/Assets/UI/Panels/modallenspanel.lua</LuaReplace>
</ReplaceUIScript>
```

### 二、include() 通配符自动发现

这是 MoreLenses 最核心的设计技巧：

```lua
-- minimappanel.lua 核心初始化代码
g_ModLenses = {} -- 全局透镜注册表，各 ModLens_*.lua 会自动填充
include("ModLens_", true)  -- 第二个参数 true = 通配符模式，加载所有以 "ModLens_" 开头的文件
```

```lua
-- modallenspanel.lua 核心初始化代码
g_ModLensModalPanel = {} -- 全局透镜图例注册表
include("ModLens_", true)  -- 同样加载所有 ModLens_*.lua
```

**工作原理：**
- `include("ModLens_", true)` 会扫描 Lua 搜索路径中所有以 `ModLens_` 开头的 `.lua` 文件并加载
- 各透镜文件在自己的全局作用域中向 `g_ModLenses` 和 `g_ModLensModalPanel` 注册
- 新增透镜只需创建一个 `ModLens_*.lua` 文件放入 Lenses 目录即可

### 三、透镜注册与按钮生成

**透镜入口数据结构：**
```lua
local MyLensEntry = {
    LensButtonText = "LOC_HUD_MY_LENS",          -- 按钮显示文本 (LOC_ key)
    LensButtonTooltip = "LOC_HUD_MY_LENS_TOOLTIP", -- 按钮提示 (LOC_ key)
    SortOrder = 100,          -- 排序权重（可选，越小越靠前）
    Initialize = OnInit,      -- 初始化回调（注册事件监听）或 nil
    OnToggle = TogglePanel,   -- 切换时打开/关闭附加面板回调（可选）
    GetColorPlotTable = OnGetColorPlotTable,  -- 返回 {[color]=plots} 表 或 nil（用自定义触发）
    NonStandardFunction = fn  -- 替代 GetColorPlotTable 的自定义函数（可选）
}
```

**注册流程（minimappanel.lua）：**
```lua
-- 1. 各 ModLens_*.lua 被 include 时自动填充 g_ModLenses
g_ModLenses[LENS_NAME] = MyLensEntry

-- 2. 初始化阶段调用 InitializeModLens()
function InitializeModLens()
    -- 按 SortOrder 排序
    local sortedModLenses = {}
    for lensName, modLens in pairs(g_ModLenses) do
        table.insert(sortedModLenses, { SortOrder = modLens.SortOrder, Name = lensName, Lens = modLens })
    end
    table.sort(sortedModLenses, function(a,b) return (a.SortOrder or 999) < (b.SortOrder or 999) end)
    -- 逐个调用 InitLens
    for _,modLens in ipairs(sortedModLenses) do
        InitLens(modLens.Name, modLens.Lens)
    end
end

-- 3. InitLens 创建按钮 + 注册回调
function InitLens(lensName, modLens)
    if modLens.Initialize ~= nil then modLens.Initialize() end
    local modLensToggle = m_LensButtonIM:GetInstance()
    modLensToggle.LensButton:GetTextButton():LocalizeAndSetText(modLens.LensButtonText)
    modLensToggle.LensButton:SetToolTipString(Locale.Lookup(modLens.LensButtonTooltip))
    modLensToggle.LensButton:RegisterCallback(Mouse.eLClick, function()
        ToggleModLens(modLensToggle.LensButton, lensName)
    end)
end
```

### 四、透镜激活 vs 默认透镜层的寄生关系

**核心设计：所有 Mod 透镜寄生在 "Appeal" 透镜层上**

```lua
-- 当用户点击模组透镜按钮
function ToggleModLens(buttonControl, lensName)
    if buttonControl:IsChecked() then
        SetActiveModdedLens(lensName)         -- 设置当前激活的模组透镜
        -- 如果 Appeal 透镜层已开启，先关闭清除旧着色
        if UILens.IsLayerOn(m_HexColoringAppeal) then
            UILens.SetActive("Default")
        end
        -- 关闭其他透镜的附加面板
        LuaEvents.ML_CloseLensPanels()
        if g_ModLenses[lensName].OnToggle ~= nil then
            g_ModLenses[lensName].OnToggle()  -- 打开/关闭附加面板
        end
        UILens.SetActive("Appeal")            -- 激活 Appeal 透镜 -> 触发 OnLensLayerOn
        RefreshInterfaceMode()
    else
        SetActiveModdedLens("NONE")
        -- 关闭透镜...
    end
end

-- OnLensLayerOn 中路由到模组透镜的着色函数
function OnLensLayerOn(layerNum)
    if layerNum == m_HexColoringAppeal then
        if m_CurrentModdedLensOn == "VANILLA_APPEAL" then
            SetAppealHexes()       -- 原生魅力透镜
        else
            SetModLens()           -- 模组透镜 → 调用 GetColorPlotTable
        end
    end
end
```

**为什么寄生在 Appeal 层：**
- 游戏只有固定的几个透镜层（Religion, Continent, Appeal, Government, Owner, Water, Tourism, Empire）
- 无法动态创建新的透镜层
- "Appeal" 层在大多数游戏中不被频繁使用，且着色逻辑可控
- 通过在 `OnLensLayerOn` 中路由，同一透镜层可显示完全不同的内容

### 五、透镜着色执行

```lua
function SetModLens()
    local getPlotColorFn = g_ModLenses[m_CurrentModdedLensOn].GetColorPlotTable
    local funNonStandard = g_ModLenses[m_CurrentModdedLensOn].NonStandardFunction
    if getPlotColorFn ~= nil then
        SetModLensHexes(getPlotColorFn())
    elseif funNonStandard ~= nil then
        funNonStandard()
    end
end

function SetModLensHexes(colorPlot)
    -- colorPlot 结构: { [ColorValue] = {plotID1, plotID2, ...}, [ColorValue2] = {...} }
    local localPlayer = Game.GetLocalPlayer()
    for color, plots in pairs(colorPlot) do
        if table.count(plots) > 0 then
            UILens.SetLayerHexesColoredArea(m_HexColoringAppeal, localPlayer, plots, color)
        end
    end
end
```

### 六、LuaEvents 模块间通信

MoreLenses 定义了一套私有的 LuaEvents 用于模块间协作：

```lua
-- MinimapPanel → 透镜模块
LuaEvents.MinimapPanel_SetActiveModLens(name)     -- 设置当前激活的模组透镜
LuaEvents.MinimapPanel_GetActiveModLens(tbl)      -- 查询当前激活的模组透镜
LuaEvents.MinimapPanel_GetLensPanelOffsets(tbl)   -- 获取透镜面板偏移（用于定位附加面板）
LuaEvents.MinimapPanel_AddLensEntry(name, entry)  -- 运行时动态添加透镜
LuaEvents.MinimapPanel_ModdedLensOn(name)          -- 通知模组透镜已切换（供外部 Mod 监听）

-- 透镜模块之间
LuaEvents.ML_CloseLensPanels()   -- 关闭所有模组透镜的附加面板
LuaEvents.ML_ReoffsetPanels()    -- 小地图大小变化时重新定位附加面板
LuaEvents.ML_HandleMouse()       -- 鼠标移动时通知透镜（CityOverlap 等)
LuaEvents.ML_ShowSettingsMenu()  -- 打开设置面板
LuaEvents.ML_SettingsUpdate()    -- 设置更新通知
```

### 七、小地图大小变化时的面板重定位

```lua
-- minimappanel.lua
function OnMinimapImageSizeChanged()
    ResizeBacking()
    LuaEvents.ML_ReoffsetPanels()  -- 通知所有附加面板重新定位
end

-- 附加面板（如 ResourceLensOptionsPanel）
local function OnReoffsetPanel()
    local offsets = {}
    LuaEvents.MinimapPanel_GetLensPanelOffsets(offsets)
    Controls.ResourceLensOptionsPanel:SetOffsetY(offsets.Y + PANEL_OFFSET_Y)
    Controls.ResourceLensOptionsPanel:SetOffsetX(offsets.X + PANEL_OFFSET_X)
end
LuaEvents.ML_ReoffsetPanels.Add(OnReoffsetPanel)
```

### 八、ModalLensPanel 自定义图例

```lua
-- 每个透镜文件同时向两个全局表注册
local MyModalEntry = {
    LensTextKey = "LOC_HUD_MY_LENS",
    Legend = {
        {"LOC_TOOLTIP_MY_LENS_CAT1", UI.GetColorValue("COLOR_MY_CAT1")},
        {"LOC_TOOLTIP_MY_LENS_CAT2", UI.GetColorValue("COLOR_MY_CAT2")},
    }
}
if g_ModLensModalPanel ~= nil then
    g_ModLensModalPanel[LENS_NAME] = MyModalEntry
end

-- modallenspanel.lua 在 OnLensLayerOn 中检测模组透镜并调用
function ShowModLensKey(lensName)
    ResetKeyStackIM()
    local info = g_ModLensModalPanel[lensName].Legend
    for _, hexColorAndKey in ipairs(info) do
        AddKeyEntry(unpack(hexColorAndKey))  -- {text, color}
    end
    Controls.LensText:SetText(Locale.ToUpper(Locale.Lookup(g_ModLensModalPanel[lensName].LensTextKey)))
end
```

## 完整透镜注册生命周期

```
1. minimappanel.lua 加载 → include("ModLens_", true)
2. 各 ModLens_*.lua 被 include → 填入 g_ModLenses 和 g_ModLensModalPanel
3. minimappanel.lua Initialize() → InitializeModLens()
   → 按 SortOrder 排序 → 逐个 InitLens()
   → 调用 lens.Initialize() 注册事件 → 创建按钮
4. 用户点击透镜按钮 → ToggleModLens()
   → SetActiveModdedLens(name)
   → 关闭/打开附加面板 (lens.OnToggle)
   → UILens.SetActive("Appeal") → 触发 OnLensLayerOn
5. OnLensLayerOn → SetModLens() → lens.GetColorPlotTable()
   → SetModLensHexes() → UILens.SetLayerHexesColoredArea()
```

## 设计要点

1. **野生 include 自动发现**：`include("ModLens_", true)` 是最优雅的插件注册方式，无需维护列表
2. **寄生在 Appeal 层**：所有模组透镜共享一个游戏透镜层，通过内部状态路由着色
3. **双全局表注册**：`g_ModLenses` (minimappanel) + `g_ModLensModalPanel` (modallenspanel)，一个文件同时注册两边
4. **LuaEvents 通信**：MinimapPanel 作为 Hub，通过 LuaEvents 广播状态变化和事件
5. **XML 替换多层**：Base/DLC1/DLC2 各一份 minimappanel.xml，DLC 版本在原生按钮列表中增加新透镜按钮
6. **运行时动态添加**：通过 `LuaEvents.MinimapPanel_AddLensEntry` 支持其他 Mod 在运行时注册透镜
7. **排序支持**：`SortOrder` 字段控制按钮显示顺序

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `Base/Assets/UI/minimappanel.xml` | 基础版 MinimapPanel 布局：LensPanel + MapOptionsPanel + MiniMap 容器 |
| `Base/Assets/UI/Panels/modallenspanel.xml` | ModalLensPanel 布局：图例面板（HeaderGrid + KeyPanel + KeyEntry Instance） |
| `DLC/Expansion1/UI/Replacements/minimappanel.xml` | XP1 版 MinimapPanel（新增 LoyaltyLens 按钮） |
| `DLC/Expansion2/UI/Replacements/minimappanel.xml` | XP2 版 MinimapPanel（新增 PowerLens + LoyaltyLens 按钮） |
| `Settings/ml_settingspanel.xml` | MoreLenses 设置面板（AutoApply 等开关） |

### minimappanel.xml 控件 ID 对照

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `LensPanel` | Grid | `Controls.LensPanel` | 透镜选择面板（230x326，默认 Hidden） |
| `LensChooserList` | ScrollPanel | — | 透镜按钮滚动容器 |
| `LensToggleStack` | Stack | — | 原生透镜 RadioButton 列表 + 模组透镜动态追加挂载点 |
| `LensButton` | CheckBox | `Controls.LensButton` | 小地图上方透镜入口按钮（44x44） |
| `MapOptionsPanel` | Grid | `Controls.MapOptionsPanel` | 地图选项面板 |
| `MapOptionsButton` | CheckBox | `Controls.MapOptionsButton` | 地图选项入口按钮 |
| `MiniMap` | Container | `Controls.MiniMap` | 小地图总容器 |
| `MinimapContainer` | Image | `Controls.MinimapContainer` | 小地图图像区域（256x256） |
| `MinimapImage` | Image | `Controls.MinimapImage` | 小地图实际纹理 |
| `CollapseButton` / `ExpandButton` | Button | `Controls.CollapseButton` / `Controls.ExpandButton` | 收放小地图 |
| `OptionsStack` | Stack | `Controls.OptionsStack` | 小地图底部选项按钮行 |
| `MLSettingsExpandButton` | GridButton | `Controls.MLSettingsExpandButton` | MoreLenses 设置按钮（LensPanel 内） |

**Instance 模板：**

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `LensButtonInstance` | 模组透镜按钮模板 | `LensButton`(RadioButton)，RadioGroup="ActiveLens"，BoxOnLeft="1" |

### modallenspanel.xml 控件 ID 对照

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `LensText` | Label | `Controls.LensText` | 透镜名称标题 |
| `CloseButton` | Button | `Controls.CloseButton` | 关闭图例面板 |
| `KeyPanel` | Grid | `Controls.KeyPanel` | 图例内容面板 |
| `KeyScrollPanel` | ScrollPanel | — | 图例条目滚动容器 |
| `KeyStack` | Stack | — | 图例条目挂载点（InstanceManager 父容器） |

**Instance 模板：**

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `KeyEntry` | 图例颜色条目 | `KeyColorImage`(Image, 32x36), `KeyLabel`(Label), `KeyBonusImage`(Image, ICON), `KeyBonusLabel`(Label) |

### 可复用 XML 模板

```xml
<!-- minimappanel 核心外壳（精简版） -->
<Context>
  <Grid ID="LensPanel" Anchor="L,T" Size="230,326"
        Texture="Tracker_OptionsBacking.dds" ConsumeAllMouse="1" Hidden="1">
    <ScrollPanel ID="LensChooserList" Style="ScrollPanelWithLeftBar">
      <Stack ID="LensToggleStack" StackGrowth="Bottom">
        <!-- 原生透镜 RadioButton 列表 -->
        <!-- 模组透镜通过 InstanceManager:GetInstance() 动态追加 -->
      </Stack>
    </ScrollPanel>
  </Grid>
  <Container ID="MiniMap" Anchor="L,B">
    <Image ID="MinimapContainer" Size="256,256">
      <Image ID="MinimapImage" Texture="MiniMap_BG.dds" Size="256,256" />
      <Stack ID="OptionsStack" StackGrowth="Right">
        <CheckBox ID="LensButton" ButtonSize="44,44" />
        <CheckBox ID="MapOptionsButton" ButtonSize="40,40" />
      </Stack>
    </Image>
  </Container>
  <Instance Name="LensButtonInstance">
    <RadioButton ID="LensButton" RadioGroup="ActiveLens"
                 ButtonTexture="Controls_RadioButtonLarge.dds" BoxOnLeft="1"/>
  </Instance>
</Context>
```

### DLC XML 替换策略

ModBuddy 的 `ImportFiles` 中设置 `Criteria="Expansion1"` / `Criteria="Expansion2"` 来控制加载哪个 XML 版本。Lua 文件在所有版本共用同一份，但 XML 需分 DLC 提供，每一份都必须在 `LensToggleStack` 中包含对应的原生透镜按钮。
