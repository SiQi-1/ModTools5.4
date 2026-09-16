# 自定义游戏内弹出对话框（来源：工坊领袖 Mod）

## 做什么
使用 `UIManager:QueuePopup` 创建自定义游戏内对话框（Yes/No、Yes-only、多按钮），替代原版 PopupDialog。可与 LuaEvents 联动，从任何 UI 组件触发。

> **与 `lua-workshop-misc-ui-popup-choice.md` 的区别**：后者通过自定义 Notification 类型 + `NotificationPanel` 替换来触发弹窗，结构固定（PullDown + OK/Cancel）。本模式通过 **LuaEvents 跨组件触发**，按钮由 InstanceManager **动态创建**，适合轻量级的确认/提示对话框场景，不需要自定义通知类型。

---

## 快速索引

| 来源 Mod | 文件 | 模式 |
|----------|------|------|
| Yosuga Sora (2743674155) | `HarukaDialog.lua` | Yes/YesNo 对话框 + LuaEvents 触发 |
| Yosuga Sora (2743674155) | `HarukaChange.lua` | Governor 替换面板（全屏弹窗） |
| EagleUnion (2966077687) | `EagleUnionExtraPanel.lua` | 多功能确认面板（侧滑动） |

---

## 一、核心机制：UIManager:QueuePopup

### 1.1 三个关键参数

```lua
local kParameters = {}
kParameters.RenderAtCurrentParent = true    -- 在当前位置渲染，不覆盖全屏
kParameters.InputAtCurrentParent = true     -- 输入限制在当前父级范围内
kParameters.AlwaysVisibleInQueue = true     -- 排队的其他弹窗不遮挡
UIManager:QueuePopup(ContextPtr, PopupPriority.Low, kParameters)
```

| 参数 | 作用 |
|------|------|
| `RenderAtCurrentParent = true` | 弹窗在当前位置渲染，不强制置顶 |
| `InputAtCurrentParent = true` | 点击弹窗外的区域不会触发 UI 事件（鼠标限定在弹窗内） |
| `AlwaysVisibleInQueue = true` | 即使有其他弹窗排队，也保持可见 |

### 1.2 打开/关闭流程

```lua
-- 打开
function Open()
    if not UIManager:IsInPopupQueue(ContextPtr) then
        local kParameters = {}
        kParameters.RenderAtCurrentParent = true
        kParameters.InputAtCurrentParent = true
        kParameters.AlwaysVisibleInQueue = true
        UIManager:QueuePopup(ContextPtr, PopupPriority.Low, kParameters)
        UI.PlaySound("UI_Screen_Open")
    end
end

-- 关闭
function Close()
    if UIManager:DequeuePopup(ContextPtr) then
        UI.PlaySound("UI_Screen_Close")
    end
end
```

---

## 二、Yes-Only 对话框模版（HarukaDialog 模式）

### 2.1 完整实现

```lua
include("InstanceManager")

local m_DialogButtonIM = InstanceManager:new("DialogButtonInstance", "Button", Controls.PopupStack)

-- ===========================================================================
-- 显示纯提示对话框（只有 "确定" 按钮）
-- ===========================================================================
function OpenYesDialog(text, callbackOk)
    local localPlayer = Game.GetLocalPlayer()
    if localPlayer == -1 then return end

    -- 1. 创建 OK 按钮
    local dialogButtonInstance = m_DialogButtonIM:GetInstance()
    dialogButtonInstance.Button:SetText(Locale.Lookup('LOC_OK'))
    dialogButtonInstance.Button:RegisterCallback(Mouse.eLClick, function()
        Close()
        callbackOk()
    end)

    -- 2. 鼠标悬浮效果（可选）
    dialogButtonInstance.Button:RegisterCallback(Mouse.eMouseEnter, function()
        dialogButtonInstance.BlueBackground:SetTexture('galleryUI18')
    end)
    dialogButtonInstance.Button:RegisterCallback(Mouse.eMouseExit, function()
        dialogButtonInstance.BlueBackground:SetTexture('galleryUI14')
    end)

    -- 3. 设置文本
    Controls.Text:SetText(text)

    -- 4. 播放动画
    Controls.PopupAlphaIn:SetToBeginning()
    Controls.PopupAlphaIn:Play()
    Controls.PopupSlideIn:SetToBeginning()
    Controls.PopupSlideIn:Play()

    -- 5. 显示对话框
    Controls.DialogBox:SetHide(false)
    Controls.PopupStack:CalculateSize()

    Open()  -- QueuePopup
end
```

### 2.2 Yes/No 对话框

```lua
function OpenYesNoDialog(text, callbackOk)
    local localPlayer = Game.GetLocalPlayer()
    if localPlayer == -1 then return end

    -- 两个按钮：OK + Cancel
    local btnOk = m_DialogButtonIM:GetInstance()
    btnOk.Button:SetText(Locale.Lookup('LOC_OK'))
    btnOk.Button:RegisterCallback(Mouse.eLClick, function()
        Close()
        callbackOk()
    end)

    local btnCancel = m_DialogButtonIM:GetInstance()
    btnCancel.Button:SetText(Locale.Lookup('LOC_CANCEL'))
    btnCancel.Button:RegisterCallback(Mouse.eLClick, Close)

    Controls.Text:SetText(text)
    Controls.DialogBox:SetHide(false)
    Controls.PopupStack:CalculateSize()

    Open()  -- QueuePopup
end
```

### 2.3 关闭

```lua
function Close()
    if UIManager:DequeuePopup(ContextPtr) then
        UI.PlaySound("UI_Screen_Close")
    end
    Controls.DialogBox:SetHide(true)
    m_DialogButtonIM:ResetInstances()
    Controls.PopupStack:CalculateSize()
end
```

---

## 三、LuaEvents 跨组件触发

### 3.1 注册全局触发事件

```lua
-- 在 Initialize 中注册 LuaEvents 供其他 UI 组件调用
function Initialize()
    ContextPtr:SetInputHandler(OnInputHandler, true)

    LuaEvents.MyDialog_OpenYesDialog.Add(OpenYesDialog)
    LuaEvents.MyDialog_OpenYesNoDialog.Add(OpenYesNoDialog)

    Events.LocalPlayerTurnEnd.Add(function()
        if ContextPtr:IsVisible() then Close() end
    end)
end
Initialize()
```

### 3.2 从其他 UI 触发

```lua
-- 在 CityPanel 按钮回调中
LuaEvents.MyDialog_OpenYesNoDialog(
    Locale.Lookup("LOC_CONFIRM_SPEND_RESOURCE", cost),
    function() ExecuteSpend() end
)
```

---

## 四、输入处理

```lua
function OnInputHandler(pInputStruct)
    if ContextPtr:IsHidden() then return false end

    -- ESC 关闭
    if pInputStruct:GetMessageType() == KeyEvents.KeyUp
       and pInputStruct:GetKey() == Keys.VK_ESCAPE then
        Close()
    end
    -- 拦截所有按键，防止跳过回合
    return true
end
```

---

## 五、XML 对话框结构

```xml
<!-- DialogBox 初始隐藏，打开时显示 -->
<Grid ID="DialogBox" Hidden="1" Size="320,auto" Anchor="C,C">

    <!-- 弹出动画 -->
    <AlphaAnim ID="PopupAlphaIn" Speed="5" Cycle="Once"
               StartValue="0" EndValue="1" />
    <SlideAnim ID="PopupSlideIn" Speed="80" Cycle="Once"
               StartOffset="0,30" EndOffset="0,0" />

    <!-- 对话框背景 -->
    <Grid Style="DiplomacyInfoWindowGrid" Size="parent,auto" AutoSizePadding="0,13">
        <Stack StackPadding="4">
            <!-- 文本内容 -->
            <Label ID="Text" Anchor="C,T" Style="FontNormal16"
                   WrapWidth="280" Offset="0,10" />

            <!-- 按钮容器（Instance 动态填充） -->
            <Stack ID="PopupStack" Anchor="C,T" StackGrowth="Right"
                   StackPadding="8" />
        </Stack>
    </Grid>
</Grid>
```

### Button Instance 模板

```xml
<Instance Name="DialogButtonInstance">
    <GridButton ID="Button" Style="MainButton" Size="auto,41"
                Anchor="C,C">
        <Image ID="BlueBackground" Texture="galleryUI14" />
        <Label ID="ButtonText" Anchor="C,C" Style="FontNormal16" />
    </GridButton>
</Instance>
```

---

## 六、与 PopupDialog 的对比

| 特性 | `PopupDialog` (原版) | `UIManager:QueuePopup` (自定义) |
|------|---------------------|--------------------------------|
| 弹窗位置 | 屏幕正中强制居中 | 可在在父容器内渲染 |
| 按钮样式 | 系统固定样式 | 完全自定义 |
| 动画 | 无 | 支持 AlphaAnim / SlideAnim |
| Leader 模式兼容 | 可能不兼容 | 完全兼容 |
| 多按钮复杂度 | 简单 Yes/No 固定 | InstanceManager 动态创建任意数量按钮 |

---

## 七、自动关闭场景

```lua
function Initialize()
    -- 以下 LuaEvent 触发时自动关闭弹窗（避免遮挡其他 UI）
    LuaEvents.DiplomacyActionView_HideIngameUI.Add(Close)
    LuaEvents.EndGameMenu_Shown.Add(Close)
    LuaEvents.FullscreenMap_Shown.Add(Close)
    LuaEvents.TechTree_OpenTechTree.Add(Close)
    LuaEvents.CivicsTree_OpenCivicsTree.Add(Close)
    LuaEvents.Government_OpenGovernment.Add(Close)
    LuaEvents.GovernorPanel_Opened.Add(Close)
    LuaEvents.GreatPeople_OpenGreatPeople.Add(Close)
    LuaEvents.GreatWorks_OpenGreatWorks.Add(Close)
    LuaEvents.Religion_OpenReligion.Add(Close)

    -- 回合结束自动关闭
    Events.LocalPlayerTurnEnd.Add(function()
        if ContextPtr:IsVisible() then Close() end
    end)
end
```

---

## 八、关键要点

1. **`RenderAtCurrentParent = true`** 是关键参数，让弹窗不占满屏幕，能保持在地图/城市视图之上
2. **关闭时务必 `ResetInstances()`**，避免 Instance 累积内存泄漏
3. **ESC 键拦截**：`OnInputHandler` 返回 `true` 阻止 ESC 跳过回合
4. **回合结束关闭**：始终监听 `Events.LocalPlayerTurnEnd` 自动关闭
5. **LuaEvents 命名**：建议用 `{ModPrefix}_Open{Action}Dialog` 风格避免冲突

---

## XML 配合

### 用到的 XML 文件

| 来源 Mod | XML 文件路径 | 作用 |
|----------|------------|------|
| Yosuga Sora (2743674155) | `UI/Additions/HarukaDialog.xml` | Yes/YesNo 对话框控件 + 按钮 Instance |
| Yosuga Sora (2743674155) | `UI/Additions/HarukaChange.xml` | Governor 替换面板（全屏弹窗） |
| EagleUnion (2966077687) | `UI/Additions/EagleUnionExtraPanel.lua` | 多功能确认面板（侧滑动） |

### 控件 ID 对照

| XML 控件 ID | 类型 | Lua 角色 |
|------------|------|---------|
| `HarukaDialogBox` | `Box` | 对话框根容器，`SetHide(false/true)` 控制显隐 |
| `PopupAlphaIn` | `AlphaAnim` | 弹出透明度动画 |
| `PopupSlideIn` | `SlideAnim` | 弹出滑动动画 |
| `Text` | `Label` | 对话框主体文本内容 |
| `PopupStack` | `Stack` | 按钮容器，InstanceManager 目标父节点 |
| `HarukaDialogButtonInstance` (Instance) | `GridButton` | 按钮模板，含 `Button` + `BlueBackground` |

### Instance 模板

```xml
<Instance Name="DialogButtonInstance">
    <GridButton ID="Button" Size="124,28" FontSize="18" FontStyle="Stroke">
        <Image ID="BlueBackground" Anchor="C,B" Offset="0,1"
               Size="124,28" Texture="galleryUI14" Alpha="0.7"/>
    </GridButton>
</Instance>
```

### 可复用 XML

- **对话框框架**：`DialogBox` + `PopupStack` + `AlphaAnim/SlideAnim` 三件套可复用于任何轻量弹窗
- **按钮 Instance**：`DialogButtonInstance` 模式适合所有 InstanceManager 动态创建多按钮的场景
- 作为独立 Context 注册到 modinfo，由 LuaEvents 跨组件触发
