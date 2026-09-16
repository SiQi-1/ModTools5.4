# 独立 Modal 屏幕 + LaunchBar 按钮注入（来源：工坊 1753346735 Sukritact's Relations Overview）

## 做什么
创建一个全新的独立 UI 屏幕（Modal 弹窗），包含自定义图表/关系图渲染，并通过 LookUpControl 向游戏顶栏（LaunchBar）注入按钮来触发打开。

## 架构概览

```
Suk_RelationsOverview.xml     — 全新 <Context>，定义全部控件和 Instance
Suk_RelationsOverview.lua     — 全部逻辑：数据采集、图表渲染、LaunchBar 注入
```

**注意**：这不是在扩展已有 UI，而是创建一个**完全独立的屏幕**。它与原版 UI 的关系仅仅是：
1. 通过 LaunchBar 注入一个按钮来触发打开/关闭
2. 作为 Popup 叠加到 InGame 层级中

## 挂载方式

### 1. 新建 XML Context（独立屏幕）

```xml
<?xml version="1.0" encoding="utf-8"?>
<Context>
    <!-- 套用游戏的全屏 Modal 框架 -->
    <Container ID="Vignette" Style="FullScreenVignetteConsumer"/>
    
    <!-- 主内容容器 -->
    <Container ID="PopupContainer" Anchor="C,C" Size="1024,768">
        <!-- 背景装饰 -->
        <Image ID="WoodPaneling" .../>
        
        <!-- 核心内容 -->
        <Container ID="Content" Size="parent,parent-40" Anchor="C,B">
            <!-- 自定义图表区域 -->
            <Container ID="DiagramContainer" Size="0,0" Anchor="C,C">
                <Container ID="LinesStack" Size="parent,parent" Anchor="C,C">
                    <!-- 线条动画（用于高亮/淡化） -->
                    <AlphaAnim ID="HideLines" AlphaBegin="1" AlphaEnd="0.05" Speed="4" .../>
                </Container>
                <Container ID="LeadersStack" Size="parent,parent" Anchor="C,C"/>
            </Container>
        </Container>
        
        <!-- 标准 Modal 框架按钮 -->
        <Container ID="ModalFrame" Style="ModalScreenWide"/>
    </Container>
</Context>
```

### 2. LaunchBar 按钮注入（关键模式）

不修改任何原版 XML 文件，纯 Lua 运行时注入：

```lua
function OnLoaded()
    -- 1) 通过 LookUpControl 找到 InGame 的 LaunchBar 及其子控件
    g_.LaunchBar            = ContextPtr:LookUpControl("/InGame/LaunchBar")
    g_.ButtonStack          = ContextPtr:LookUpControl("/InGame/LaunchBar/ButtonStack")
    g_.LaunchBacking        = ContextPtr:LookUpControl("/InGame/LaunchBar/LaunchBacking")
    g_.LaunchBackingTile    = ContextPtr:LookUpControl("/InGame/LaunchBar/LaunchBackingTile")

    -- 2) 使用 InstanceManager 在 LaunchBar 的 ButtonStack 中创建实例
    pLaunchBarItemIM = Suk_InstanceManager:new(
        "LaunchBarItem",            -- XML 中定义的 Instance Name
        "LaunchItemButton",         -- 根控件 ID
        g_.ButtonStack,             -- 父容器（通过 LookUpControl 获得）
        g_.LaunchBar                -- 所属 Context（LaunchBar 的上下文）
    )

    -- 3) 获取一个实例并配置
    g_.tButton = pLaunchBarItemIM:GetInstance()
    g_.tButton.LaunchItemButton:SetTexture("LaunchBar_Hook_GreatWorksButton")
    g_.tButton.LaunchItemButton:SetToolTipString(Locale.Lookup("LOC_SUK_GLOBAL_RELATIONS_SCREEN"))
    g_.tButton.LaunchItemIcon:SetTexture("LaunchBar_Hook_Suk_RelationshipOverview")
    g_.tButton.LaunchItemButton:RegisterCallback(Mouse.eLClick, OnOpen)

    -- 4) 调整 LaunchBar 尺寸以容纳新按钮
    RealizeBacking()
end

function RealizeBacking()
    g_.ButtonStack:CalculateSize()
    g_.LaunchBacking:SetSizeX(g_.ButtonStack:GetSizeX() + 116)
    -- 通知外交条调整滚动宽度
    LuaEvents.LaunchBar_Resize(g_.ButtonStack:GetSizeX())
end
```

**初始化时机**：通过 `Events.LoadScreenClose.Add(OnInit)` 确保游戏 UI 完全加载后才执行 LookUpControl。

```lua
function OnInit(bIsReload)
    Events.LoadScreenClose.Add(OnInit)  -- 重新加载时也重新初始化
    if not ContextPtr:LookUpControl("/InGame/LaunchBar") then return end
    OnLoaded()
end
```

## 自定义 InstanceManager（跨 Context）

标准 InstanceManager 只能在同一 Context 内创建实例。要向 LaunchBar 注入按钮，需要支持跨 Context：

```lua
-- 继承标准 InstanceManager 的所有方法
Suk_InstanceManager = {}
for k,v in pairs(InstanceManager) do Suk_InstanceManager[k] = v end

-- 重写 new: 增加第 4 个参数 Context
Suk_InstanceManager.new = function(self, instanceName, rootControlName, ParentControl, Context)
    local o = Suk_InstanceManager.Base_New(self, instanceName, rootControlName, ParentControl)
    o.m_Context = Context or ContextPtr  -- 保存目标 Context
    return o
end

-- 重写 BuildInstance: 使用保存的 Context 来创建实例
Suk_InstanceManager.BuildInstance = function(self)
    local controlTable = {}
    if self.m_ParentControl == nil then
        self.m_Context:BuildInstance(self.m_InstanceName, controlTable)
    else
        self.m_Context:BuildInstanceForControl(self.m_InstanceName, controlTable, self.m_ParentControl)
    end
    -- ... 其余逻辑
end
```

## Popup 管理

使用 `UIManager:QueuePopup` 而非简单的 Show/Hide，实现 RenderAtCurrentParent 模式：

```lua
function OnOpen()
    if (Game.GetLocalPlayer() == -1) then return end

    if not UIManager:IsInPopupQueue(ContextPtr) then
        local kParameters = {}
        kParameters.RenderAtCurrentParent = true   -- 渲染在父层级而非屏幕最上层
        kParameters.InputAtCurrentParent = true    -- 输入也绑定在当前父层级
        kParameters.AlwaysVisibleInQueue = true    -- 切到其他 Popup 后仍显示
        UIManager:QueuePopup(ContextPtr, PopupPriority.Low, kParameters)
        UI.PlaySound("UI_Screen_Open")
    end

    RefreshPanel()

    -- 播放开场动画
    Controls.ScreenAnimIn:SetToBeginning()
    Controls.ScreenAnimIn:Play()
end

function OnClose()
    if not ContextPtr:IsHidden() then
        UI.PlaySound("UI_Screen_Close")
    end
    UIManager:DequeuePopup(ContextPtr)
end
```

## 热键绑定

```lua
function OnInit(bIsReload)
    -- 通过 InputAction 系统绑定热键
    m_ToggleVisibilityAction = Input.GetActionId("Suk_GlobalRelations")
    if m_ToggleVisibilityAction ~= nil then
        Events.InputActionTriggered.Add(OnInputActionTriggered)
    end
end

function OnInputActionTriggered(actionId)
    if m_ToggleVisibilityAction == actionId then
        if ContextPtr:IsHidden() then OnOpen() else OnClose() end
    end
end
```

## 图表/图形渲染

使用数学函数在 UI 控件上做自定义渲染：

```lua
-- 圆形定位：将 N 个领袖头像均匀排列在圆上
function Circle_GetCoords(iPercent, iRadius)
    local iCosMod = math.cos(iPercent * math.pi * 2)
    local iDirection = iPercent >= 0.5 and -1 or 1
    local iY = iCosMod * iRadius * -1
    local iX = Circle_GetX(iY, iRadius) * iDirection
    return math_round(iX), math_round(iY)
end

-- 绘制连线
function DrawLine(pInstanceA, pInstanceB, iRadius, iColor, iOffset)
    local iStartX, iStartY = pInstanceA.Top:GetOffsetVal()
    local iEndX, iEndY = pInstanceB.Top:GetOffsetVal()
    iStartX = iStartX + iRadius + iOffsetX
    iStartY = iStartY + iRadius + iOffsetY
    -- ...
    local pLine = pLines_IM:GetInstance()
    pLine.Line:SetStartVal(iStartX, iStartY)
    pLine.Line:SetEndVal(iEndX, iEndY)
    if iColor then pLine.Line:SetColor(iColor) end
    return pLine
end
```

## 数据刷新

在本屏幕的 `RefreshPanel()` 中一次性完成所有更新：

```lua
function RefreshPanel()
    -- 1) 重置所有 InstanceManager
    pPlayerIcons_IM:ResetInstances()
    pLines_IM:ResetInstances()
    pKeys_IM:ResetInstances()

    -- 2) 从 Game API 获取数据
    local tPlayers = PlayerManager.GetAliveMajors()
    local iLocalPlayer = Game.GetLocalPlayer()

    -- 3) 为每个玩家创建头像实例，计算圆形坐标
    for iIndex, pPlayer in ipairs(tPlayers) do
        local pInstance = pPlayerIcons_IM:GetInstance()
        local pLeaderIcon = LeaderIcon:AttachInstance(pInstance.Icon)
        -- ...
        local iPercent = (iIndex - 1) / iNumPlayers
        local iOffsetX, iOffsetY = Circle_GetCoords(iPercent, iRadius)
        pInstance.Top:SetOffsetVal(iOffsetX, iOffsetY)
    end

    -- 4) 计算并绘制关系连线
    tRelationships = GetRelationshipInfo()
    for iA, pInstanceA in ipairs(tInstances) do
        for iB, pInstanceB in ipairs(tInstances) do
            if pInstanceB ~= pInstanceA then
                if tRelationships[iLineID] then
                    tPlayerLines[iLineID] = DrawLine(pInstanceA, pInstanceB, ...)
                end
            end
        end
    end

    -- 5) 生成图例
    GenerateKeys()
end
```

## 鼠标交互（悬停高亮相关连线）

```lua
function OnMouseEnter(iPlayerA)
    -- 收集与悬停领袖相关的所有连线
    local tExclude = {}
    for iIndex, pPlayer in ipairs(tPlayers) do
        local iPlayerB = pPlayer:GetID()
        if iPlayerA ~= iPlayerB then
            iRelationshipID = CantorPairing(iPlayerB, iPlayerA)
            if tPlayerLines[iRelationshipID] then
                -- 显示该领袖头像上的关系图标
                tPlayerIcons[iPlayerB].Controls.Relationship:SetVisState(...)
                tPlayerIcons[iPlayerB].Controls.Relationship:SetHide(false)
                tExclude[pLine] = true
            end
        end
    end

    -- 将所有连线分为两组：相关的留在 LinesStack，不相关的移到 HideLines（动画淡出）
    for _, tTable in pairs(tPlayerLines) do
        if not tExclude[pLine] then
            pLine.Line:ChangeParent(Controls.HideLines)    -- 移到动画容器 → 淡出
        else
            pLine.Line:ChangeParent(Controls.LinesStack)   -- 保持在可见容器
        end
    end
    Controls.HideLines:SetToBeginning()
    Controls.HideLines:Play()
end

function OnMouseExit()
    -- 恢复所有连线
    for _, pPlayerIcon in pairs(tPlayerIcons) do
        pPlayerIcon.Controls.Relationship:SetHide(true)
    end
    Controls.HideLines:SetToEnd()
    Controls.HideLines:Reverse()  -- 反向播放动画 → 淡入
    pIcons_IM:ResetInstances()
end
```

## 清理（OnShutdown）

```lua
function OnShutdown()
    -- 销毁注入到 LaunchBar 的实例
    pLaunchBarItemIM:DestroyInstances()
    pLaunchBarPinIM:DestroyInstances()

    -- 移除事件监听
    Events.LoadScreenClose.Remove(OnInit)
    Events.InputActionTriggered.Remove(OnInputActionTriggered)
end
```

## 适用场景
- 创建全新的关系图/雷达图/网络图等可视化面板
- 在 LaunchBar 注入自定义按钮（不需要修改原版 XML）
- 实现 RenderAtCurrentParent 的半透明叠加层（不阻塞游戏操作）
- 热键切换的独立面板

## 注意事项
- **LookUpControl 的时机**：必须在 `Events.LoadScreenClose` 之后，否则 `/InGame/LaunchBar` 尚未创建
- **跨 Context 的 InstanceManager**：标准 InstanceManager 不支持向其他 Context 创建实例，需要定制版本
- **ChangeParent 技巧**：通过把控件从一个容器移到另一个（有 AlphaAnim 的容器），实现过渡动画效果
- **LaunchBar_Resize 事件**：注入新按钮后需触发此事件通知外交条调整宽度
- 必须在 `.modinfo` 中作为 `InGameUIAddin` 注册此 Context

## XML 配合

### 涉及的关键 XML 文件

| 文件 | 路径（相对于 Mod 根目录） | 用途 |
|------|--------------------------|------|
| `Suk_RelationsOverview.xml` | `UI/Suk_RelationsOverview.xml` | 独立 Context，定义全屏 Modal 及所有 Instance |
| `LeaderIcon` (Include) | 游戏内置 | 领袖头像 Instance 复用 |

### 核心控件 ID 对照表

| 控件 ID | 类型 | 用途 |
|---------|------|------|
| `Vignette` | Container | 全屏暗色遮罩（Style="FullScreenVignetteConsumer"） |
| `PopupContainer` | Container | 主弹窗容器，Anchor="C,C" Size="1024,768" |
| `Content` | Container | 内容区容器 |
| `ContentStack` | Stack | 水平分栏（左 KeyPanel + 右 DiagramContainer） |
| `KeyPanel` | Grid | 图例面板 |
| `KeyStack` | Stack | 图例条目列表 |
| `DiagramContainer` | Container | 图表渲染区（Size="0,0"，子控件绝对定位） |
| `LinesStack` | Container | 可见连线层 |
| `LeadersStack` | Container | 领袖头像层 |
| `HideLines` | AlphaAnim | 淡出动画（隐藏被排除的连线） |
| `ModalFrame` | Container | 标准 Modal 关闭/帮助按钮框架 |
| `Relationships` / `Deals` | GridButton | Tab 切换按钮 |
| **Instances** | | |
| `LeaderInstance` | Instance | 领袖头像 + 文明旗标 + 箭头指示器 |
| `KeyInstance` | Instance | 图例条目（标题 + 色条） |
| `FontIconInstance` | Instance | 字体图标渲染 |
| `LineInstance` | Instance | 连线（Color + Start/End + Width） |
| **LaunchBar 注入** | | |
| `LaunchBarItem` | Instance | 注入 LaunchBar 的按钮实例（跨 Context 创建） |

### 可复用 XML 模板

```xml
<?xml version="1.0" encoding="utf-8"?>
<Context>
    <!-- 全屏遮罩 -->
    <Container ID="Vignette" Style="FullScreenVignetteConsumer" />

    <!-- 主弹窗 -->
    <Container ID="PopupContainer" Anchor="C,C" Size="1024,768">
        <!-- 背景 -->
        <Image ID="Background" Size="parent,parent" Texture="Parchment_Pattern" StretchMode="Tile" ConsumeMouse="1"/>

        <!-- 内容区 -->
        <Container ID="Content" Size="parent,parent-40" Anchor="C,B">
            <Stack ID="ContentStack" StackGrowth="Right" Anchor="C,C" Padding="50">
                <!-- 左面板：数据列表 -->
                <Container Size="300,parent" Anchor="C,C">
                    <!-- Tab 按钮 -->
                    <Container Anchor="C,T" Size="350,61" Offset="0,-9">
                        <Stack StackGrowth="Right" Anchor="C,C" Padding="5">
                            <GridButton ID="Tab1" Size="150,34" Style="TabButton" String="LOC_TAB_1">
                                <GridButton ID="Tab1_Selected" Size="parent,parent" Style="TabButtonSelected" ConsumeMouseButton="0" ConsumeMouseOver="1"/>
                            </GridButton>
                        </Stack>
                    </Container>

                    <!-- 列表/图例 -->
                    <Grid ID="ListPanel" Size="300,auto" Anchor="C,C" AutoSizePadding="10,30">
                        <Stack ID="ListStack" StackGrowth="Bottom" Anchor="C,C" Padding="15"/>
                    </Grid>
                </Container>

                <!-- 右面板：自定义渲染区 -->
                <Container ID="RenderContainer" Size="0,0" Anchor="C,C">
                    <Container ID="ForegroundLayer" Size="parent,parent" Anchor="C,C"/>
                    <Container ID="BackgroundLayer" Size="parent,parent" Anchor="C,C">
                        <AlphaAnim ID="FadeAnim" AlphaBegin="1" AlphaEnd="0.05" Speed="4" Function="Root" Cycle="Once" Stopped="1"/>
                    </Container>
                </Container>
            </Stack>
        </Container>

        <!-- 标准 Modal 框架 -->
        <Container ID="ModalFrame" Style="ModalScreenWide" />
    </Container>

    <!-- Instances -->
    <Instance Name="ItemInstance">
        <Container ID="Top" Size="auto,auto" Anchor="C,C">
            <Image ID="Icon" Size="45,45" Anchor="C,C"/>
            <Label ID="Caption" WrapWidth="200" Anchor="L,C" Style="FontNormal14"/>
        </Container>
    </Instance>

    <Instance Name="LineInstance">
        <Line Color="255,0,0" Start="0,0" End="0,0" Width="3" ID="Line"/>
    </Instance>

    <Instance Name="LaunchBarItem">
        <Button ID="LaunchItemButton" Size="49,49" Texture="LaunchBar_Hook_GovernmentButton">
            <Image ID="LaunchItemIcon" Anchor="C,C" Size="38,38"/>
        </Button>
    </Instance>
</Context>
```
