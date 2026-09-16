# LaunchBar 按钮注入 + 动态尺寸调整（来源：工坊领袖 Mod）

## 做什么
在屏幕右上角 LaunchBar（启动栏）注入自定义按钮，点击可打开自定义面板。与 TopPanel 产量扩展不同，这是"添加一个可点击的功能按钮到右上角按钮堆栈中"的模式。

> **与 `lua-workshop-standalone-modal.md` 的区别**：后者使用自定义跨 Context InstanceManager 来注入 LaunchBar 按钮并配合独立 Modal 全屏。本模式使用更简单的 `BuildInstanceForControl`（标准 API），聚焦于**领袖条件注入** —— 按钮仅对特定领袖/文明可见，不需要定制 InstanceManager。

---

## 快速索引

| 来源 Mod | 注入点 | 用途 |
|----------|--------|------|
| EagleUnion (2966077687) | `/InGame/LaunchBar/ButtonStack` | 研究点数面板入口 |
| Klee (2882489805) | `/InGame/TopPanel/InfoStack/StaticInfoStack` | WMD 炸弹计数 |

---

## 一、LaunchBar 按钮 — 完整模版（EagleUnion）

### 1.1 初始化

```lua
local m_EagleLaunchButtonInstance = {}

function EagleAttachLaunchButton()
    -- 1. 找到 LaunchBar 按钮堆栈
    local buttonStack = ContextPtr:LookUpControl("/InGame/LaunchBar/ButtonStack")

    -- 2. 用 BuildInstanceForControl 创建按钮实例（比 ChangeParent 更优雅）
    ContextPtr:BuildInstanceForControl("EagleUnionItem", m_EagleLaunchButtonInstance, buttonStack)
    m_EagleLaunchButtonInstance.EagleUnionButton:RegisterCallback(Mouse.eLClick, EagleUnionTogglePopup)
    m_EagleLaunchButtonInstance.EagleUnionButton:RegisterCallback(Mouse.eMouseEnter, EagleUnionEnter)

    -- 3. 重新计算堆栈尺寸
    buttonStack:CalculateSize()

    -- 4. 动态调整背景 backing 宽度（关键步骤）
    local backing = ContextPtr:LookUpControl("/InGame/LaunchBar/LaunchBacking")
    backing:SetSizeX(buttonStack:GetSizeX() + 116)

    local backingTile = ContextPtr:LookUpControl("/InGame/LaunchBar/LaunchBackingTile")
    backingTile:SetSizeX(buttonStack:GetSizeX() - 20)

    -- 5. 通知其他组件 LaunchBar 尺寸变化（如果存在监听者）
    LuaEvents.LaunchBar_Resize(buttonStack:GetSizeX())
end

function Initialize()
    if EagleCore.CheckCivMatched(Game.GetLocalPlayer(), 'CIVILIZATION_EAGLE_UNION') then
        Events.LoadGameViewStateDone.Add(EagleAttachLaunchButton)
    end
end
```

### 1.2 按钮显示/隐藏：领袖判断

```lua
function EagleRefreshLaunchButton()
    local localPlayer = Game.GetLocalPlayer()
    if EagleCore.CheckCivMatched(localPlayer, 'CIVILIZATION_EAGLE_UNION') then
        m_EagleLaunchButtonInstance.EagleUnionButton:SetHide(false)
    end
end
```

### 1.3 按钮点击：通过 LuaEvents 打开面板

```lua
function EagleUnionTogglePopup()
    LuaEvents.EagleUnionTopButton_TogglePopup()
end
```

面板端注册：
```lua
LuaEvents.EagleUnionTopButton_TogglePopup.Add(Toggle)
```

---

## 二、TopPanel InfoStack 注入（Klee 模式）

适用于注入到 `/InGame/TopPanel/InfoStack/StaticInfoStack`，如武器计数器。

```lua
isAttached = false

function AttachToTopPanel()
    local infoStack = ContextPtr:LookUpControl("/InGame/TopPanel/InfoStack/StaticInfoStack")
    if not isAttached then
        Controls.JumpyDumpty:ChangeParent(infoStack)
        infoStack:AddChildAtIndex(Controls.JumpyDumpty, 3)   -- 指定插入位置
        infoStack:CalculateSize()
        infoStack:ReprocessAnchoring()
        isAttached = true
    end
    kleeWMD()
end

function kleeWMD()
    kleeOnWMDUpdate(Game.GetLocalPlayer())
end

function kleeOnWMDUpdate(owner, WMDtype)
    local eLocalPlayer = Game.GetLocalPlayer()
    if eLocalPlayer ~= -1 and owner == eLocalPlayer then
        local player = Players[owner]
        local playerWMDs = player:GetWMDs()
        for entry in GameInfo.WMDs() do
            if entry.WeaponType == "WMD_JUMPY_DUMPTY" then
                local count = playerWMDs:GetWeaponCount(entry.Index)
                if count > 0 then
                    Controls.JumpyDumpty:SetHide(false)
                    Controls.JumpyDumptyCount:SetText(count)
                else
                    Controls.JumpyDumpty:SetHide(true)
                end
            end
        end
    end
    ContextPtr:RequestRefresh()
end
```

---

## 三、XML 控件定义

### 3.1 LaunchBar 按钮 Instance（EagleUnion 模式）

```xml
<Instance Name="EagleUnionItem">
    <GridButton ID="EagleUnionButton" Style="LaunchBarButton"
                Size="60,62" Anchor="L,C" Hidden="1"
                ToolTip="LOC_EAGLE_UNION_BUTTON_TOOLTIP">
        <Image ID="EagleUnionIcon" Size="40,40" Anchor="C,C"
               Texture="EagleUnion_Icon" />
    </GridButton>
</Instance>
```

### 3.2 TopPanel 信息条 Instance（Klee 模式）

```xml
<Grid ID="JumpyDumpty" Anchor="L,C" Offset="6,2" Hidden="1"
      Size="48,46" SliceCorner="0,0" SliceTextureSize="48,46"
      Texture="TopBar_ButtonBacking">
    <Image Anchor="C,C" Offset="0,-2" Size="32,32"
           Texture="WMD_JumpyDumpty" />
    <Label ID="JumpyDumptyCount" Anchor="R,B"
           Offset="4,4" Style="FontNormal16" Color="255,255,255,255" />
</Grid>
```

---

## 四、关键 API 速查

| API | 用途 |
|-----|------|
| `BuildInstanceForControl(name, instanceTable, parent)` | 在当前 Context XML 中构建 Instance 到指定父容器 |
| `ChangeParent(parent)` | 将已有控件移到新父容器下（适用于非 Instance 控件） |
| `AddChildAtIndex(control, index)` | 将控件插入父容器指定索引位置 |
| `backing:SetSizeX(width)` | 动态调整 LaunchBar 背景宽度 |
| `CalculateSize()` / `ReprocessAnchoring()` | 重新计算父容器尺寸和锚定 |
| `LuaEvents.LaunchBar_Resize(newWidth)` | 通知其他组件 LaunchBar 尺寸变化 |

---

## 五、注入点对照

| 注入路径 | 方法 | 用途 |
|---------|------|------|
| `/InGame/LaunchBar/ButtonStack` | `BuildInstanceForControl` | 右上角功能按钮 |
| `/InGame/TopPanel/InfoStack/StaticInfoStack` | `ChangeParent` + `AddChildAtIndex` | 产量区旁的指示器 |
| `/InGame/TopPanel/InfoStack` | `ChangeParent` | 大的信息区 |

---

## 六、常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 按钮出现但背景没有拉长 | 没调 `backing:SetSizeX()` | 加上动态调整 backing 尺寸 |
| 按钮被截断 | `CalculateSize()` 没调 | 每次添加控件后调用 `CalculateSize()` |
| 按钮在错误玩家游戏中也显示 | 没在 `Initialize` 中做领袖判断 | 在 `Initialize` 和 `Refresh` 中都加判断 |
| `BuildInstanceForControl` 报 nil | Instance 名称在 XML 中未定义 | 检查 Instance Name 与 XML 完全一致 |

---

## XML 配合

### 用到的 XML 文件

| 来源 Mod | XML 文件路径 | 作用 |
|----------|------------|------|
| EagleUnion (2966077687) | `UI/Additions/EagleUnionTopButton.xml` | LaunchBar 按钮 Instance 定义 |
| Klee (2882489805) | `UI/Additions/Xxx.xml` | TopPanel WMD 计数器控件 |

### 控件 ID 对照

| XML 控件 ID | 类型 | Lua 角色 |
|------------|------|---------|
| `EagleUnionItem` (Instance) | `Button` | LaunchBar 入口按钮模板，`BuildInstanceForControl` 构建 |
| `EagleUnionButton` | `Button` (子) | 注册 `Mouse.eLClick` 切换弹窗 |
| `EagleUnionIcon` | `Image` | 按钮图标 |
| `EagleUnionPinInstance` (Instance) | `Image` | 装饰性分隔点 |
| `JumpyDumpty` | `Grid` | TopPanel 信息条根容器，`ChangeParent` 挂载 |
| `JumpyDumptyCount` | `Label` | 炸弹/资源计数文本 |

### Instance 模板

```xml
<Instance Name="EagleUnionItem">
    <GridButton ID="EagleUnionButton" Style="LaunchBarButton"
                Size="60,62" Anchor="L,C" Hidden="1"
                ToolTip="LOC_EAGLE_UNION_BUTTON_TOOLTIP">
        <Image ID="EagleUnionIcon" Size="40,40" Anchor="C,C"
               Texture="EagleUnion_Icon" />
    </GridButton>
</Instance>
```

### 可复用 XML

- **LaunchBar 按钮 Instance**：所有需要右上角入口按钮的能力都可复用 `EagleUnionItem` 模式，只需换图标和 ToolTip
- **TopPanel 信息 Grid**：`JumpyDumpty` 模式可复用于任何需要在 TopPanel 显示计数/状态的场景
- 这两个 XML 作为 Context Additions 注册到 modinfo，由 Lua 在 `LoadGameViewStateDone` 中动态挂载
