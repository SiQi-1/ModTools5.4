# Tourism Overview 独立面板模式（来源：Sukritact's Tourism Overview）

从工坊 Mod `2953909938`（Sukritact's Tourism Overview）提炼的独立全屏面板实现模式，涵盖 LaunchBar 按钮注册、自定义 InstanceManager、进度条百分比绘制、旅游加成图标可视化等技巧。

---

## 源文件

| 文件 | 角色 |
|------|------|
| `UI/Suk_TourismOverview.lua` | 全部逻辑：LaunchBar 按钮、面板渲染、数据计算 |
| `UI/Suk_TourismOverview.xml` | 全部布局：ProgressInstance、ConversionInstance、Content |

---

## 模式一：LaunchBar 按钮注入

### 1.1 按钮初始化

在 UI 加载完成后，通过 `LookUpControl` 获取 LaunchBar 容器，直接将按钮插入其中。

```lua
function OnLoaded()
    g_.LaunchBar              = ContextPtr:LookUpControl("/InGame/LaunchBar")
    g_.ButtonStack            = ContextPtr:LookUpControl("/InGame/LaunchBar/ButtonStack")
    g_.LaunchBacking          = ContextPtr:LookUpControl("/InGame/LaunchBar/LaunchBacking")
    g_.LaunchBackingDropShadow= ContextPtr:LookUpControl("/InGame/LaunchBar/LaunchBarDropShadow")
    g_.LaunchBackingTile      = ContextPtr:LookUpControl("/InGame/LaunchBar/LaunchBackingTile")

    pLaunchBarItemIM = Suk_InstanceManager:new("LaunchBarItem", "LaunchItemButton",
        g_.ButtonStack, g_.LaunchBar)
    pLaunchBarPinIM  = Suk_InstanceManager:new("LaunchBarPinInstance", "Pin",
        g_.ButtonStack, g_.LaunchBar)

    g_.tButton = pLaunchBarItemIM:GetInstance()
    g_.tPin    = pLaunchBarPinIM:GetInstance()

    -- 设置按钮外观和回调
    g_.tButton.LaunchItemButton:SetTexture("LaunchBar_Hook_GreatWorksButton")
    g_.tButton.LaunchItemButton:SetToolTipString(Locale.Lookup("LOC_SUK_TOURISM_OVERVIEW_SCREEN"))
    g_.tButton.LaunchItemIcon:SetTexture("LaunchBar_Hook_Suk_TourismOverview")
    g_.tButton.LaunchItemButton:RegisterCallback(Mouse.eLClick, OnOpen)
end
```

### 1.2 条件显示按钮

```lua
function UpdateButton(iPlayer)
    if iPlayer and iPlayer ~= Game.GetLocalPlayer() then return end

    local iPlayer = Game.GetLocalPlayer()
    local pPlayer = Players[iPlayer]
    if not pPlayer then g_.tButton.LaunchItemButton:SetHide(true); return end

    local iTourism = pPlayer:GetStats():GetTourism() or 0
    local iForeignTourists = pPlayer:GetCulture():GetTouristsTo() or 0

    local bHideButton = (iTourism <= 0) and (iForeignTourists <= 0)
    g_.tButton.LaunchItemButton:SetHide(bHideButton)
    g_.tPin.Pin:SetHide(bHideButton)

    RealizeBacking()   -- 调整 LaunchBar 宽度
end
```

### 1.3 LaunchBar 宽度调整

```lua
function RealizeBacking()
    g_.ButtonStack:CalculateSize();
    g_.LaunchBacking:SetSizeX(g_.ButtonStack:GetSizeX() + 116);
    g_.LaunchBackingTile:SetSizeX(g_.ButtonStack:GetSizeX() - 20);
    g_.LaunchBackingDropShadow:SetSizeX(g_.ButtonStack:GetSizeX());
    -- 通知外交条带调整滚动宽度
    LuaEvents.LaunchBar_Resize(g_.ButtonStack:GetSizeX());
end
```

---

## 模式二：自定义 InstanceManager（可设 Context）

标准的 `InstanceManager:new()` 使用全局 `ContextPtr` 构建实例。当需要在 **其他 Context** 中构建实例时（如 LaunchBar），需要扩展 InstanceManager。

```lua
Suk_InstanceManager = {};
for k,v in pairs(InstanceManager) do
    Suk_InstanceManager[k] = v
end

-- 扩展构造函数，接受额外 Context 参数
Suk_InstanceManager.Base_New = Suk_InstanceManager.new
Suk_InstanceManager.new = function(self, instanceName, rootControlName, ParentControl, Context)
    local o = Suk_InstanceManager.Base_New(self, instanceName, rootControlName, ParentControl)
    o.m_Context = Context or ContextPtr
    return o
end

-- 重写 BuildInstance，使用存储的 Context
Suk_InstanceManager.BuildInstance = function(self)
    local controlTable = {}
    if self.m_ParentControl == nil then
        self.m_Context:BuildInstance(self.m_InstanceName, controlTable);
    else
        self.m_Context:BuildInstanceForControl(self.m_InstanceName, controlTable, self.m_ParentControl);
    end
    -- ... 其余同标准 InstanceManager
end

-- 重写 DestroyInstances 同理，用 self.m_Context 替代 ContextPtr
```

**用途：** 在 LaunchBar 中创建按钮实例时，必须用 `/InGame/LaunchBar` 这个 Context。

---

## 模式三：进度条百分比驱动

### 3.1 百分比计算 + Shadow Bar

将数值转换为百分比（0~1），驱动的进度条宽度：

```lua
function ProgressBarSize(tInstance, iPercent, iMarkerOffset)
    if iMarkerOffset then
        tInstance.Marker:SetHide(false)
        tInstance.Marker:SetOffsetX(iMarkerOffset)
    else
        tInstance.Marker:SetHide(true)
    end

    local iMaxSize = tInstance.Info:GetSizeX() - 4
    local iMinSize = 17
    local iSize = math.floor(iPercent * iMaxSize + 0.5)
    iSize = (iSize / iMinSize >= 0.5) and math.max(iMinSize, iSize) or 0;

    if iSize < 1 then
        tInstance.Bar:SetHide(true)
    else
        tInstance.Bar:SetHide(false)
        tInstance.Bar:SetSizeX(iSize + 4)
    end
    return iSize + 4
end

-- Bar XML 结构（前景/覆盖层分离）：
-- GridButton BarBacking → GridButton Bar → GridButton BarOverlay
-- 优点：Backing 是背景，Bar 是进度填充（动态调整 SizeX），BarOverlay 是装饰层
```

**注意：** 此方法不依赖 `TextureBar`（带纹理的百分比填充条），而是直接 `SetSizeX()` 调整宽度，适合精确控制像素级宽度。

### 3.2 TextureBar 圆形仪表（旅游转换）

XML 中使用 TextureBar 实现**圆形进度表**：

```xml
<Image Size="52,52" Texture="Suk_ForeignTourism_Meter" Anchor="C,T">
    <TextureBar ID="ForeignTouristsFill" Direction="Up" Speed="0"
        Size="52,52" TextureOffset="0,52"
        Texture="Suk_ForeignTourism_Meter"/>
</Image>
```

Lua 端设置：
```lua
tInstance.ForeignTouristsFill:SetPercent(iForeignProgress / TOURISM_TO_MOVE_CITIZEN)
```

---

## 模式四：旅游加成图标可视化（红绿灯）

三个加成维度（开放边境/贸易路线/政体），用颜色表达状态：

```lua
local TOURISM_OPEN_BORDERS = tonumber(GameInfo.GlobalParameters.TOURISM_OPEN_BORDERS_BONUS.Value)
local TOURISM_TRADE_ROUTE  = tonumber(GameInfo.GlobalParameters.TOURISM_TRADE_ROUTE_BONUS.Value)
local TOURISM_CONFLICTING_GOV = tonumber(GameInfo.GlobalParameters.TOURISM_CONFLICTING_GOVERNMENT_MULTIPLIER.Value)
-- ...
tData.OpenBorders = (hasOpenBorders) and TOURISM_OPEN_BORDERS or 0
tData.TradeRoute   = (hasTradeRoute)    and TOURISM_TRADE_ROUTE  or 0

-- 不同政体惩罚
if iGovernment ~= iLocalPlayerGovernment then
    tData.Government = (
        GameInfo.Governments[iGovernment].OtherGovernmentIntolerance +
        GameInfo.Governments[iLocalPlayerGovernment].OtherGovernmentIntolerance
    ) * TOURISM_CONFLICTING_GOV
end

-- 渲染颜色
for _, sIcon in pairs(m_BonusIcons) do
    if v[sIcon] == 0 then
        tInstance[sIcon]:SetColor(COLOR_GREY)    -- 未获得
    elseif v[sIcon] > 0 then
        tInstance[sIcon]:SetColor(COLOR_WHITE)   -- 正常
    else
        tInstance[sIcon]:SetColor(COLOR_RED)     -- 惩罚
    end
end
```

---

## 模式五：从 Tooltip 解析数值

游戏提供的 `GetTouristsFromTooltip()` 返回的是带有格式化的字符串，需要正则提取数字：

```lua
function ParseTooltip(str)
    local numbers = {}
    for num in str:gmatch("%d+[,.]?%d*") do
        num = num:gsub(",", "")      -- 去除千位分隔符
        table.insert(numbers, tonumber(num))
        if #numbers == 2 then break end
    end
    while #numbers < 2 do
        table.insert(numbers, 0)
    end
    return unpack(numbers)   -- 返回两个值：PerTurn, Lifetime
end

tData.TourismPerTurn, tData.LifetimeTourism = ParseTooltip(tData.Tooltip)
```

---

## 模式六：玩家颜色渐变系统

```lua
function GetPlayerInfo(iPlayer)
    local iLocalPlayer = Game.GetLocalPlayer()
    local bShowCivIcon = (iPlayer == iLocalPlayer)
    -- 未见面用暗色
    local tData = {
        CivIcon     = "ICON_CIVILIZATION_UNKNOWN",
        FrontColor  = UNKNOWN_COLOR_F,
        BackColor   = UNKNOWN_COLOR_B,
        BackColor_L = UNKNOWN_COLOR_BL,  -- 亮色变体
        BackColor_D = UNKNOWN_COLOR_BD,  -- 暗色变体
        Name        = "LOC_DIPLOPANEL_UNMET_PLAYER",
        HasMet      = false
    }

    bShowCivIcon = bShowCivIcon or Players[iLocalPlayer]:GetDiplomacy():HasMet(iPlayer)
    if not bShowCivIcon then return tData end

    local pPlayerConfig = PlayerConfigurations[iPlayer]
    tData.CivIcon = "ICON_" .. pPlayerConfig:GetCivilizationTypeName()
    tData.Name     = Locale.Lookup(pPlayerConfig:GetCivilizationShortDescription())
    tData.HasMet   = true

    local iBackColor, iFrontColor = UI.GetPlayerColors(iPlayer)
    tData.FrontColor  = iFrontColor
    tData.BackColor   = iBackColor
    tData.BackColor_L = UI.DarkenLightenColor(iBackColor, 80, 255)
    tData.BackColor_D = UI.DarkenLightenColor(iBackColor, -55, 230)

    return tData
end
```

**用途：** 在 XML 中将 BackColor_L/BackColor_D 分别赋给 BannerLighter/BannerDarker 图层，模拟出有立体感的横幅。

---

## 模式七：XSD 外部引用

XML 中引用外部 XSD Schema 使得 ModBuddy 等 IDE 可以提供自动补全：

```xml
<Context xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:noNamespaceSchemaLocation="..\..\..\..\..\CivTech\Libs\ForgeUI\ForgeUI_Assets\Controls.xsd">
```

---

## 模式八：展开/关闭

```lua
function OnClose()
    if not ContextPtr:IsHidden() then
        UI.PlaySound("UI_Screen_Close")
    end
    UIManager:DequeuePopup(ContextPtr)
end

function OnOpen()
    if (Game.GetLocalPlayer() == -1) then return end
    if not UIManager:IsInPopupQueue(ContextPtr) then
        local kParameters = {};
        kParameters.RenderAtCurrentParent = true;
        kParameters.InputAtCurrentParent = true;
        kParameters.AlwaysVisibleInQueue = true;
        UIManager:QueuePopup(ContextPtr, PopupPriority.Low, kParameters);
        UI.PlaySound("UI_Screen_Open");
    end
    RefreshPanel()
    Controls.ScreenAnimIn:SetToBeginning();
    Controls.ScreenAnimIn:Play();
end
```

---

## 快捷键支持

```lua
m_ToggleVisibilityAction = nil
function OnInputActionTriggered(actionId)
    if m_ToggleVisibilityAction == actionId then
        if ContextPtr:IsHidden() then
            OnOpen();
        else
            OnClose()
        end
    end
end

function OnInit()
    m_ToggleVisibilityAction = Input.GetActionId("Suk_TourismOverview");
    if m_ToggleVisibilityAction ~= nil then
        Events.InputActionTriggered.Add(OnInputActionTriggered)
    end
end
```

**注意：** 这需要配合 Mod 注册一个 InputAction，否则 `GetActionId` 返回 nil。

---

## 完整事件监听

| 事件 | 用途 |
|------|------|
| `Events.LoadScreenClose` | 推迟初始化直到 UI 树完整 |
| `Events.PlayerTurnActivated` | 每回合检查是否显示按钮 |
| `Events.InputActionTriggered` | 快捷键切换面板 |
| `Mouse.eLClick` (Close按钮) | 手动关闭 |

---

## 关键 include

```lua
include("InstanceManager")
include("CivilizationIcon")
```

---

## XML 配合

### XML 文件

| 文件 | 路径 |
|------|------|
| 面板布局 | `UI/Suk_TourismOverview.xml` |

### 核心控件 ID 对照表

| 控件 ID | 控件类型 | 用途 |
|---------|---------|------|
| `PopupContainer` | Container | 根容器，`Anchor="C,C" Size="1280,768"` |
| `Content` | Container | 内容区，`Size="parent-40,parent-80"` |
| `SummaryText` | Container | 左侧摘要区，`Size="400,230"` |
| `YourProgress` | MakeInstance | 自身旅游进度条实例 |
| `ProgressScrollPanel` | ScrollPanel | 其他文明进度滚动区 |
| `ProgressStack` | Stack | 进度实例堆叠 |
| `ConversionScrollPanel` | ScrollPanel | 旅游转换滚动区（右侧） |
| `ConversionStack` | Stack | 转换实例 wrapping 堆叠，`WrapWidth="Parent"` |
| `EarningHeaderBacking` | Grid | 旅游收入说明区 |
| `EarningSummary` | Label | 总结性文字 |
| `CoversionCost` | Label | 转换成本文本 |
| `Vignette` | Container | 暗角遮罩 |
| `ModalFrame` | Container | 模态框框架 |

### Instance 对照表

| Instance Name | 用途 |
|--------------|------|
| `ProgressInstance` | 单个文明旅游进度行（CivIcon + Bar + Amount + Marker） |
| `ConversionInstance` | 单个文明旅游转换行（CivBanner + Foreign/Domestic Meter + 加成图标） |

### ProgressInstance 关键子控件

| 子控件 | 用途 |
|--------|------|
| `CivIconBacking` / `CivIcon` | 文明图标（36px） |
| `Label` | 文明名称 |
| `Amount` | 游客数/旅游业绩 |
| `BarBacking` → `Bar` → `BarOverlay` | 三层进度条（背景/填充/装饰层） |
| `Marker` | 进度标记偏移线 |

### ConversionInstance 关键子控件

| 子控件 | 用途 |
|--------|------|
| `ForeignTouristsFill` | TextureBar 圆形仪表（外国游客） |
| `DomesticTouristsFill` | TextureBar 圆形仪表（国内游客） |
| `OpenBorders` / `TradeRoute` / `Government` | 三个旅游加成图标 |

### 可复用模板：进度条三层结构

```xml
<GridButton ID="BarBacking" Texture="Suk_TourismOverview_Bar" SliceCorner="10,10" SliceSize="1,1" Size="Parent,21">
  <GridButton ID="Bar" Texture="Suk_TourismOverview_Bar" SliceCorner="10,10" SliceSize="1,1" Size="Parent,Parent">
    <GridButton ID="BarOverlay" Texture="Suk_TourismOverview_BarOverlay" SliceCorner="10,10" SliceSize="1,1" Size="Parent,Parent"/>
  </GridButton>
  <Image ID="Marker" Size="4,21" Texture="Suk_TourismOverview_BarMarker" Anchor="L,C"/>
</GridButton>
```
