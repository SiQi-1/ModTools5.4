# 世界空间 UI 叠加层模式（来源：DetailedAppealLens 2553831629）

## 做什么
使用 `WorldAnchor` + `InstanceManager` 在 3D 世界地图上叠加 UI 元素，响应透镜层开关事件来显示/隐藏叠加内容。核心思路是将 UI 控件定位到世界各地块的 3D 坐标上，随摄像机移动而移动，实现"世界空间 UI"效果。

## 涉及文件

| 文件 | 角色 |
|------|------|
| `DetailedAppealLens.lua` | 核心实现（195 行）：ParentMap 切换、Instance 管理、地块遍历、透镜事件响应 |
| `DetailedAppealLens.xml` | XML 布局：Container + WorldAnchor Instance |

## 技术原理

### 一、WorldAnchor 定位

不同于常规 UI 控件使用屏幕坐标锚定，`WorldAnchor` 将控件固定在 3D 世界坐标上：

```xml
<Instance Name="AppealInstance">
    <WorldAnchor ID="Anchor" Anchor="C,C" Size="2,2">
        <Stack ID="IconStack" Anchor="C,C" Size="100,50" Padding="1" StackGrowth="Right">
            <Image ID="PrereqIcon" Anchor="C,C" Offset="0,0" Size="22,22" Icon="ICON_STAT_APPEAL" Hidden="1" />
            <Grid ID="PlotBonus" Anchor="C,C" Size="56,34" Style="DistrictBonusBack" Hidden="1">
                <Label ID="BonusText" Anchor="C,C" Offset="-1,-1" Style="YieldBonusText" String="?"/>
            </Grid>
        </Stack>
    </WorldAnchor>
</Instance>
```

**WorldAnchor 关键属性：**
- `Anchor="C,C" Size="2,2"` — 锚定方式；Size 决定点击区域（此处 2x2 极小，因为非交互元素）
- 通过代码设置世界位置：`pInstance.Anchor:SetWorldPositionVal(worldX, worldY, zDepth)`

### 二、Container 挂载到世界视图层

UI 叠加层必须挂载到 `/InGame/WorldViewControls`，而不是留在自己的上下文容器中：

```lua
local IsChangedMapParent = false

local function ChangeParentMap()
    if not IsChangedMapParent then
        local wvc = ContextPtr:LookUpControl("/InGame/WorldViewControls")
        if wvc ~= nil then
            Controls.PlotAppealContainer:ChangeParent(wvc)
            IsChangedMapParent = true
        end
    end
end

-- 在游戏视图加载完成后执行（确保 WorldViewControls 已创建）
Events.LoadGameViewStateDone.Add(OnLoadGameViewStateDone)
local function OnLoadGameViewStateDone()
    ChangeParentMap()
end
```

**为什么是 `/InGame/WorldViewControls`：**
- 此容器是地图视图的顶级容器，其中的子控件会随摄像机移动
- 层级正确：在资源图标下方、地块上方
- 在全屏 UI（如外交）打开时会自动隐藏

### 三、InstanceManager 管理世界图标

```lua
-- 定义 Instance 管理器（引用 XML Instance Name）
local m_PlotBonusIM = InstanceManager:new("AppealInstance", "Anchor", Controls.PlotAppealContainer)
-- 参数: XML Instance Name, 锚定控件 ID, 父容器

-- 地块 → Instance 映射缓存
local m_MapIcons = {}  -- { [plotIndex] = instance }

function GetInstanceAt(plotIndex)
    local pInstance = m_MapIcons[plotIndex]
    if pInstance == nil then
        pInstance = m_PlotBonusIM:GetInstance()
        m_MapIcons[plotIndex] = pInstance
        -- 将 Instance 定位到 3D 世界坐标
        local worldX, worldY = UI.GridToWorld(plotIndex)
        pInstance.Anchor:SetWorldPositionVal(worldX, worldY - 17, 0)
        -- 参数: X, Y, Z (深度)
    end
    return pInstance
end
```

**关键 API：**
```lua
UI.GridToWorld(plotIndex)                     -- 地块索引 → 世界坐标 (x, y)
pInstance.Anchor:SetWorldPositionVal(x, y, z)  -- 设置 WorldAnchor 的世界位置
```

### 四、按需填充与更新

当地块需要显示叠加层时：

```lua
function ProcessPlots(plots)
    if plots == nil then return end
    for i, plotID in ipairs(plots) do
        local kPlot = Map.GetPlotByIndex(plotID)
        if kPlot ~= nil then
            -- 跳过不适合的地块
            if (not kPlot:IsLake()) and (not kPlot:IsMountain()) then
                local instance = GetInstanceAt(plotID)
                local appeal = kPlot:GetAppeal()
                local appeal_str = tostring(appeal)
                if appeal > 0 then
                    appeal_str = '+' .. appeal_str
                end

                -- 设置文本颜色（正值为绿色）
                local appeal_text = appeal_str
                if appeal > 0 then
                    appeal_text = '[COLOR:ResCultureLabelCS]' .. appeal_str .. '[ENDCOLOR]'
                end

                instance.PrereqIcon:SetHide(false)
                instance.PlotBonus:SetHide(false)
                instance.BonusText:SetText(appeal_text)

                -- 动态调整背景大小
                local x, y = instance.BonusText:GetSizeVal()
                instance.PlotBonus:SetSizeVal(x + PADDING_X, y + PADDING_Y)

                -- 偏移避免与资源图标重叠
                instance.PlotBonus:SetOffsetY(-48)
                instance.PrereqIcon:SetOffsetY(-48)
            end
        end
    end
end
```

### 五、透镜层事件响应

```lua
local m_HexColoringAppeal = UILens.CreateLensLayerHash("Hex_Coloring_Appeal_Level")
local m_IsAppealLens = true  -- 只有原生 Appeal 透镜激活时才显示

function OnLensLayerOn(layerNum)
    if not (layerNum == m_HexColoringAppeal) or (not m_IsAppealLens) then
        return
    end
    RealizeAppealTiles()  -- 显示所有地块的魅力值叠加层
end

function OnLensLayerOff(layerNum)
    if not (layerNum == m_HexColoringAppeal) or (not m_IsAppealLens) then
        return
    end
    RemoveAppealTiles()  -- 清除所有叠加层
end
```

### 六、与 MoreLenses 模组透镜的兼容

DetailedAppealLens 通过监听 `MinimapPanel_ModdedLensOn` LuaEvent 来判断当前是否是原生 Appeal 透镜：

```lua
function OnMinimapPanel_ModdedLensOn(lensName)
    if lensName == 'VANILLA_APPEAL' then
        m_IsAppealLens = true   -- 原生魅力透镜 → 显示叠加层
    else
        m_IsAppealLens = false  -- 模组透镜（Builder/Scout 等）→ 隐藏叠加层
        RemoveAppealTiles()
    end
end

LuaEvents.MinimapPanel_ModdedLensOn.Add(OnMinimapPanel_ModdedLensOn)
```

### 七、清除与释放

```lua
function RemoveAppealTiles()
    for key, pInstance in pairs(m_MapIcons) do
        m_PlotBonusIM:ReleaseInstance(pInstance)
        m_MapIcons[key] = nil
    end
end

function ClearEveything()
    for key, pInstance in pairs(m_MapIcons) do
        m_PlotBonusIM:ReleaseInstance(pInstance)
        m_MapIcons[key] = nil
    end
end

-- Shutdown
function OnShutdown()
    ClearEveything()
    m_PlotBonusIM:DestroyInstances()
    IsChangedMapParent = false
    Events.LensLayerOn.Remove(OnLensLayerOn)
    Events.LensLayerOff.Remove(OnLensLayerOff)
end
```

### 八、按大陆分批处理（性能优化）

```lua
function RealizeAppealTiles()
    for i, ContinentID in ipairs(Map.GetContinentsInUse()) do
        ProcessPlots(Map.GetVisibleContinentPlots(ContinentID))
    end
end
```

`Map.GetVisibleContinentPlots(ContinentID)` 返回一个大陆的所有可见地块索引，比遍历全图更高效。

## 完整初始化流程

```lua
function Initialize()
    ContextPtr:SetShutdown(OnShutdown)
    Events.LoadGameViewStateDone.Add(OnLoadGameViewStateDone)  -- 挂载父容器
    Events.LensLayerOn.Add(OnLensLayerOn)
    Events.LensLayerOff.Add(OnLensLayerOff)
    LuaEvents.MinimapPanel_ModdedLensOn.Add(OnMinimapPanel_ModdedLensOn)
end
Initialize()
```

## XML 容器结构

```xml
<Context Layer="DetailedAppealLens">
    <!-- 空容器：所有 Instance 的挂载点 -->
    <Container ID="PlotAppealContainer" />

    <!-- Instance 模板 -->
    <Instance Name="AppealInstance">
        <WorldAnchor ID="Anchor" Anchor="C,C" Size="2,2">
            <!-- 世界空间 UI 内容 -->
        </WorldAnchor>
    </Instance>
</Context>
```

**关键点：`Layer` 属性**
- `Layer="DetailedAppealLens"` 定义 UI 层，影响控件的显示层级（不必依赖默认值）
- `Container ID="PlotAppealContainer"` 为空——所有控件由 InstanceManager 动态创建

## 设计要点

1. **WorldAnchor 是核心**：所有世界空间定位依赖 `SetWorldPositionVal`
2. **挂载到 WorldViewControls**：必须通过 `ChangeParent` 脱离自身 Context，否则控件不随摄像机移动
3. **Instance 缓存复用**：`m_MapIcons[plotIndex]` 避免重复创建 Instance
4. **Z 深度调整**：`SetOffsetY(-48)` 将叠加层向上偏移，避免与资源图标重叠
5. **ReleaseInstance vs DestroyInstances**：清除时用 `ReleaseInstance`，Shutdown 时用 `DestroyInstances`
6. **与模组透镜兼容**：监听 `MinimapPanel_ModdedLensOn` 判断是否是原生 Appeal 透镜
7. **按大陆处理**：`Map.GetVisibleContinentPlots()` 比全图遍历性能更好
8. **跳过不适用地块**：山、湖泊无需叠加层的地块提前 continue
9. **颜色标记**：用 `[COLOR:ColorName]text[ENDCOLOR]` 语法在文本中嵌入颜色
10. **动态尺寸**：`GetSizeVal` + `SetSizeVal` 让背景适应文本宽度

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `DetailedAppealLens.xml` | 世界空间 UI 叠加层：Container + WorldAnchor Instance 定义 |

### 控件 ID 对照

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `PlotAppealContainer` | Container | `Controls.PlotAppealContainer` | 空容器 — 所有 AppealInstance 的父挂载点 |
| `Anchor` | WorldAnchor | — | 世界空间锚点（由 InstanceManager 动态创建子实例） |

**Instance 模板：**

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `AppealInstance` | 世界空间魅力值图标 | `Anchor`(WorldAnchor, 2x2), `IconStack`(Stack, Growth="Right"), `PrereqIcon`(Image, ICON_STAT_APPEAL, 22x22), `PlotBonus`(Grid, DistrictBonusBack, 56x34), `BonusText`(Label, YieldBonusText) |

### 完整 XML 模板

```xml
<Context Layer="DetailedAppealLens">
    <Container ID="PlotAppealContainer" />
    <Instance Name="AppealInstance">
        <WorldAnchor ID="Anchor" Anchor="C,C" Size="2,2">
            <Stack ID="IconStack" Anchor="C,C" Size="100,50"
                   Padding="1" StackGrowth="Right">
                <Image ID="PrereqIcon" Anchor="C,C" Size="22,22"
                       Icon="ICON_STAT_APPEAL" Hidden="1" />
                <Grid ID="PlotBonus" Anchor="C,C" Size="56,34"
                      Style="DistrictBonusBack" Hidden="1">
                    <Label ID="BonusText" Anchor="C,C" Offset="-1,-1"
                           Style="YieldBonusText" String="?"/>
                </Grid>
            </Stack>
        </WorldAnchor>
    </Instance>
</Context>
```

### ChangeParent 路径

```
XML Context → Controls.PlotAppealContainer
  → ChangeParent → /InGame/WorldViewControls
```

`Layer="DetailedAppealLens"` 定义 UI 层名（影响初始显示层级），最终通过 ChangeParent 挂载到 `WorldViewControls` 后层级由目标容器决定。

### 复用要点

1. 将 Context Layer 改为自定义名称
2. 修改 Instance Name 和内部控件 ID
3. 保持 `WorldAnchor` + `SetWorldPositionVal` 定位方式
4. 保持 Container 空容器作为 Instance 父节点
5. Lua 中 `ChangeParent` 到 `/InGame/WorldViewControls`
