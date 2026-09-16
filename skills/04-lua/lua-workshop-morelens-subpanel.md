# 透镜附加配置面板模式（来源：MoreLenses 871712879）

## 做什么
为透镜创建一个可独立显示/隐藏的配置面板，放置在地图 UI 层（而非透镜弹出层），随小地图大小变化自动重新定位。面板可以有自己的 XML 布局、自己的输入处理、以及与透镜着色逻辑的双向交互。

## 涉及文件

| 文件 | 角色 |
|------|------|
| `Lenses/Resource/ModLens_Resource.lua` | 带资源筛选勾选面板的透镜，完整展示本模式 |
| `Lenses/Resource/ModLens_Resource.xml` | 资源面板的 XML 布局 |
| `Lenses/CityOverlap/ModLens_CityOverlap.lua` | 带范围控制面板的透镜 |
| `Lenses/CityOverlap/ModLens_CityOverlap.xml` | 城市交叠面板 XML |
| `Base/Assets/UI/minimappanel.lua` | 提供面板定位数据 (GetLensPanelOffsets) 和通信事件 |

## 架构

### 一、面板容器初始化与 ChangeParent

面板需要将自身从原始上下文移动到 `/InGame/HUD` 容器，以确保正确的显示层级和外交界面时的隐藏行为：

```lua
local PANEL_OFFSET_Y = 32   -- 面板相对小地图的垂直偏移
local PANEL_OFFSET_X = -5   -- 面板相对小地图的水平偏移

local function ChangeContainer()
    local hudContainer = ContextPtr:LookUpControl("/InGame/HUD")
    Controls.ResourceLensOptionsPanel:ChangeParent(hudContainer)
end

local function OnInit(isReload)
    if isReload then
        ChangeContainer()  -- 重载时重新挂载
    end
end

-- 注册 init/shutdown
ContextPtr:SetInitHandler(OnInit)
ContextPtr:SetShutdown(OnShutdown)

-- 游戏加载完毕后执行
Events.LoadScreenClose.Add(function()
    ChangeContainer()
    -- 此时注册透镜入口（延迟到 LoadScreenClose 确保两个面板都已就绪）
    LuaEvents.MinimapPanel_AddLensEntry(LENS_NAME, MyLensEntry)
    LuaEvents.ModalLensPanel_AddLensEntry(LENS_NAME, MyModalPanelEntry)
end)
```

### 二、定位与重定位

面板需要定位在小地图上方，并随小地图大小变化自动调整：

```lua
-- 初次定位
local function OnReoffsetPanel()
    local offsets = {}
    LuaEvents.MinimapPanel_GetLensPanelOffsets(offsets)
    -- offsets.X = LensPanel 右边缘的屏幕 X 坐标
    -- offsets.Y = MinimapContainer 顶部边缘的屏幕 Y 坐标
    Controls.ResourceLensOptionsPanel:SetOffsetY(offsets.Y + PANEL_OFFSET_Y)
    Controls.ResourceLensOptionsPanel:SetOffsetX(offsets.X + PANEL_OFFSET_X)
end

-- 监听重定位事件（小地图大小变化时触发）
LuaEvents.ML_ReoffsetPanels.Add(OnReoffsetPanel)
```

minimappanel.lua 如何计算偏移：
```lua
function GetLensPanelOffsets(offsets)
    local y = Controls.MinimapContainer:GetSizeY() + Controls.MinimapContainer:GetOffsetY()
    if m_isCollapsed then
        y = y - Controls.MinimapContainer:GetSizeY()  -- 收起时调整
    end
    offsets.Y = y
    offsets.X = Controls.LensPanel:GetSizeX() + Controls.LensPanel:GetOffsetX()
end
```

### 三、面板打开/关闭

```lua
local m_isOpen = false

local function Open()
    Controls.ResourceLensOptionsPanel:SetHide(false)
    m_isOpen = true
    -- 恢复默认设置或从持久化存储加载
    RefreshResourcePicker()
end

local function Close()
    Controls.ResourceLensOptionsPanel:SetHide(true)
    m_isOpen = false
end

local function TogglePanel()
    if m_isOpen then Close() else Open() end
end

-- 透镜入口使用 OnToggle 回调
MyLensEntry = {
    ...
    OnToggle = TogglePanel,  -- 透镜切换时打开/关闭面板
    GetColorPlotTable = nil,   -- 着色由面板内部控制
}

-- 额外监听：当其他透镜打开时关闭本面板
LuaEvents.ML_CloseLensPanels.Add(Close)
```

### 四、自有 InputHandler

面板需要自己的输入处理（与 minimappanel 的 InputHandler 共存）：

```lua
-- 注册面板的输入处理
ContextPtr:SetInputHandler(OnInputHandler, true)  -- true = 消费事件，不向下传递

-- 注意：面板本身的 Controls 如果设置了 ConsumeMouse="1"，会自动消费鼠标事件
```

### 五、与透镜着色的交互

当透镜层激活时，面板控制着色：

```lua
-- 监听 LensLayerOn 事件（因为 OnToggle 不处理着色）
Events.LensLayerOn.Add(OnLensLayerOn)

local function OnLensLayerOn(layerNum)
    if layerNum == ML_LENS_LAYER then
        local lens = {}
        LuaEvents.MinimapPanel_GetActiveModLens(lens)
        if lens[1] == LENS_NAME then
            RefreshMyLens()  -- 根据面板状态执行着色
        end
    end
end

-- 面板控件变更时刷新着色
function HandleBonusResourceCheckbox(pControl, resourceType)
    if not pControl.ResourceCheckbox:IsChecked() then
        find_and_remove(m_bonusResourcesToShow, resourceType)
    else
        ndup_insert(m_bonusResourcesToShow, resourceType)
    end
    RefreshResourceLens()  -- 立即更新着色
end
```

### 六、持久化面板状态

使用 `PlayerConfigurations:SetValue/GetValue` 跨存档保存面板选择：

```lua
-- 保存（序列化）
local function SaveBonusResourcesToShow()
    local localPlayerID = Game.GetLocalPlayer()
    local dataDump = DataDumper(m_bonusResourcesToShow, "bonusResourcesToShow", true)
    PlayerConfigurations[localPlayerID]:SetValue("ML_ModLens_Resource_bonusResourcesToShow", dataDump)
end

-- 加载（反序列化）
local function LoadBonusResourcesToShow()
    local localPlayerID = Game.GetLocalPlayer()
    local saved = PlayerConfigurations[localPlayerID]:GetValue("ML_ModLens_Resource_bonusResourcesToShow")
    if saved ~= nil then
        loadstring(saved)()  -- 执行序列化代码，恢复 bonuxResourcesToShow 变量
        -- 合并到 m_bonusResourcesToShow
    end
end

-- 在 Open() 时恢复
local function Open()
    Controls.ResourceLensOptionsPanel:SetHide(false)
    if not LoadBonusResourcesToShow() then
        m_resetBonusResourceList = true  -- 无存档时使用默认
    end
    RefreshResourcePicker()
end
```

**DataDumper 序列化：**
MoreLenses 内嵌了一个 Lua 表的序列化工具（~200 行），用于将表转换为可执行 Lua 代码字符串。简化替代方案：用 `table.concat(t, ",")` 存储简单的字符串列表。

### 七、面板清理

```lua
local function OnShutdown()
    -- 销毁容器时必须手动移除子控件
    local hudContainer = ContextPtr:LookUpControl("/InGame/HUD")
    if hudContainer ~= nil then
        hudContainer:DestroyChild(Controls.ResourceLensOptionsPanel)
    end
end
ContextPtr:SetShutdown(OnShutdown)
```

### 八、Mouse 交互透镜（CityOverlap 特例）

CityOverlap 透镜面板额外监听了鼠标移动事件：

```lua
-- 面板文件注册
LuaEvents.ML_HandleMouse.Add(HandleMouse)

-- minimappanel.lua 在 OnInputHandler 中调用
function HandleMouseForModdedLens()
    if not m_isMouseDragging then
        LuaEvents.ML_HandleMouse()  -- 广播鼠标移动给所有监听者
    end
end

-- 面板实现
local function HandleMouse()
    if m_isOpen then
        local plotId = UI.GetCursorPlotID()
        if not Map.IsPlot(plotId) then return end
        if m_CurrentCursorPlotID == plotId then return end  -- 忽略重复
        m_CurrentCursorPlotID = plotId
        -- 只在特定透镜激活时刷新
        local lens = {}
        LuaEvents.MinimapPanel_GetActiveModLens(lens)
        if lens[1] == LENS_NAME then
            if Controls.OverlapLensMouseRange:IsChecked() then
                RefreshCityOverlapLens()  -- 基于鼠标位置重新着色
            end
        end
    end
end
```

## XML 布局模板

```xml
<Context>
  <!-- 面板容器：独立定位，消费鼠标事件 -->
  <Container ID="MyLensOptionsPanel" Size="260,350" Anchor="L,B" ConsumeMouse="1">
    <Grid Size="parent,parent" Texture="Tracker_OptionsBacking.dds"
          SliceCorner="55,61" SliceSize="1,1" SliceTextureSize="121,119">
      <Label Anchor="C,T" String="{LOC_HUD_MY_LENS:upper}" Offset="-6,10"
             Style="FontFlair16" ... />
      <!-- 面板内容 -->
      <ScrollPanel ID="MyPickList" Anchor="L,T" Offset="35,35" Size="parent,parent-65"
                   Style="ScrollPanelWithLeftBar">
        <Stack ID="MyPickStack" Anchor="L,T" StackGrowth="Down" Padding="5">
          <!-- 动态填充的控件 -->
        </Stack>
      </ScrollPanel>
    </Grid>
  </Container>

  <!-- Instance 模板 -->
  <Instance Name="MyPickEntry">
    <Container Size="130,20">
      <CheckBox ID="MyCheckbox" ... />
      <Label ID="MyLabel" ... />
    </Container>
  </Instance>
</Context>
```

## 设计要点

1. **ChangeParent 到 HUD**：确保面板在打开外交界面等全屏 UI 时正确隐藏
2. **延迟注册**：在 `LoadScreenClose` 中调用 `AddLensEntry`，确保 minimappanel 已完全初始化
3. **OnToggle 而非 GetColorPlotTable**：面板自己控制着色时机，入口的 `GetColorPlotTable` 设为 nil
4. **监听 LensLayerOn**：OnToggle 只处理面板开关，实际着色在 LensLayerOn 事件中执行
5. **面板独占**：`LuaEvents.ML_CloseLensPanels` 确保同一时间只有一个面板打开
6. **Shutdown 清理**：`DestroyChild` 必须手动执行，因为 Panel 通过 `ChangeParent` 已脱离原始上下文
7. **保存设置**：用 `PlayerConfigurations:SetValue/GetValue` + 序列化实现跨存档持久化
8. **锚点位置**：面板用 `Anchor="L,B"` 定位在地图左下角（小地图上方），通过代码调整偏移

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `Lenses/Resource/ModLens_Resource.xml` | 资源筛选面板：类别 CheckBox + 按资源分类的 Stack + ResourcePickEntry Instance |
| `Lenses/CityOverlap/ModLens_CityOverlap.xml` | 城市交叠面板：CheckBox 选项 + RadioButton 模式切换 + 范围调节控件 |

### ModLens_Resource.xml 控件 ID 对照

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `ResourceLensOptionsPanel` | Container | `Controls.ResourceLensOptionsPanel` | 面板根容器（260x350，ConsumeMouse="1"） |
| `ResourcePickList` | ScrollPanel | — | 资源选择列表滚动容器 |
| `ResourcePickStack` | Stack | `Controls.ResourcePickStack` | 主 Stack（类别 CheckBox + 子 Stack 混排） |
| `ShowBonusResource` | CheckBox | `Controls.ShowBonusResource` | 加成资源总开关 |
| `BonusResourcePickStack` | Stack | — | 加成资源条目挂载点 |
| `ShowLuxuryResource` | CheckBox | `Controls.ShowLuxuryResource` | 奢侈资源总开关 |
| `LuxuryResourcePickStack` | Stack | — | 奢侈资源条目挂载点 |
| `ShowStrategicResource` | CheckBox | `Controls.ShowStrategicResource` | 战略资源总开关 |
| `StrategicResourcePickStack` | Stack | — | 战略资源条目挂载点 |

**Instance 模板：**

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `ResourcePickEntry` | 单个资源条目 | `ResourceCount`(Label, "99/99"), `ResourceCheckbox`(CheckBox, 17x17), `ResourceLabel`(Label) |

### ModLens_CityOverlap.xml 控件 ID 对照

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `OverlapLensOptionsPanel` | Container | `Controls.OverlapLensOptionsPanel` | 面板根容器（230x350） |
| `ShowLensOutsideBorder` | CheckBox | `Controls.ShowLensOutsideBorder` | "显示边境外的城市" 选项 |
| `OverlapLensMouseNone` | RadioButton | `Controls.OverlapLensMouseNone` | 模式：全图城市交叠 |
| `OverlapLensMouseRange` | RadioButton | `Controls.OverlapLensMouseRange` | 模式：鼠标范围城市交叠 |
| `OverlapRangeDown` | Button | `Controls.OverlapRangeDown` | 减小搜索范围（-1） |
| `OverlapRangeUp` | Button | `Controls.OverlapRangeUp` | 增大搜索范围（+1） |
| `OverlapRangeLabel` | Label | `Controls.OverlapRangeLabel` | 当前范围数字显示 |

### 可复用面板 XML 模板

```xml
<Context>
  <Container ID="MyLensOptionsPanel" Size="260,350" Anchor="L,B" ConsumeMouse="1">
    <Grid Size="parent,parent" Texture="Tracker_OptionsBacking.dds"
          SliceCorner="55,61" SliceSize="1,1" SliceTextureSize="121,119">
      <Label Anchor="C,T" String="{LOC_HUD_MY_LENS:upper}"
             Style="FontFlair16" FontStyle="Glow" SmallCaps="20"/>
      <ScrollPanel ID="MyPickList" Anchor="L,T" Offset="35,35"
                   Size="parent,parent-65" Style="ScrollPanelWithLeftBar">
        <Stack ID="MyPickStack" Anchor="L,T" StackGrowth="Down" Padding="5">
          <!-- 动态填充条目 -->
        </Stack>
      </ScrollPanel>
    </Grid>
  </Container>
  <Instance Name="MyPickEntry">
    <Container Size="130,20">
      <Label ID="MyCount" String="99/99" Anchor="R,C" Style="WhiteSemiBold14"/>
      <CheckBox ID="MyCheckbox" Anchor="L,C" ButtonSize="17,17"/>
      <Label ID="MyLabel" Anchor="L,C" Style="WhiteSemiBold14"/>
    </Container>
  </Instance>
</Context>
```

### ChangeParent 到 HUD 的 XML 前提

面板在 XML 中定义后属于其 `<Context>` 的根层级。Lua 中通过 `Controls.MyPanel:ChangeParent(hudContainer)` 将其移动到 `/InGame/HUD`，这是世界空间 UI 的标准做法。面板的 `ConsumeMouse="1"` 确保输入不会被下方地图接收。
