# ChangeParent 浮动叠加面板（来源：工坊 873246701）

## 做什么
创建一个独立 Context 的 UI 面板，运行时通过 `LookUpControl` + `ChangeParent` 将控件从自己的 Context 移动到 `/InGame/HUD` 容器，使之成为游戏主 HUD 上的浮动叠加层（而非侧面板或全屏面板）。

## 如何挂载到官方UI

### 核心两步

1. **在 OnInit (reload) 时执行 ChangeParent**：
```lua
local function ChangeContainer()
    local hudContainer = ContextPtr:LookUpControl("/InGame/HUD")
    Controls.SettingsPanel:ChangeParent(hudContainer)
end

local function OnInit(isReload:boolean)
    if isReload then
        ChangeContainer()
    end
end
```

2. **在 OnShutdown 时销毁子控件**（手动清理）：
```lua
local function OnShutdown()
    local hudContainer = ContextPtr:LookUpControl("/InGame/HUD")
    if hudContainer ~= nil then
        hudContainer:DestroyChild(Controls.SettingsPanel)
    end
end
```

**为什么需要 OnShutdown 手动销毁**：因为 ChangeParent 后控件已不在自己的 Context 下，引擎卸载该 Context 时不会自动清理已移走的子控件，必须手动 `DestroyChild`。

### 显示/隐藏

用 `SetHide` 控制，而非 PartialScreenHooks：
```lua
local function OnOpen()
    ContextPtr:SetHide(false);
end

local function OnClose()
    ContextPtr:SetHide(true);
end
```

### 触发入口

通过 LuaEvents 从其他 UI 触发：
```lua
-- 在 Initialize() 中注册
LuaEvents.BTS_ShowSettingsMenu.Add( OnOpen )

-- 在其他 UI 文件中调用
LuaEvents.BTS_ShowSettingsMenu()  -- 弹出设置面板
```

## 关键 Lua 代码

### 完整模板

```lua
-- MySettingsPanel.lua（独立 Context 文件）

local function ChangeContainer()
    local hudContainer = ContextPtr:LookUpControl("/InGame/HUD")
    Controls.MySettingsRoot:ChangeParent(hudContainer)
end

local function OnOpen()
    ContextPtr:SetHide(false);
end

local function OnClose()
    ContextPtr:SetHide(true);
end

local function OnInit(isReload:boolean)
    if isReload then
        ChangeContainer()
    end
end

local function OnShutdown()
    local hudContainer = ContextPtr:LookUpControl("/InGame/HUD")
    if hudContainer ~= nil then
        hudContainer:DestroyChild(Controls.MySettingsRoot)
    end
end

function Initialize()
    ContextPtr:SetInitHandler(OnInit)
    ContextPtr:SetShutdown(OnShutdown)

    -- 注册打开入口
    LuaEvents.MyMod_ShowSettings.Add(OnOpen)

    -- 设置面板按钮
    Controls.ConfirmButton:RegisterCallback(Mouse.eLClick, OnClose)
end
Initialize()
```

### CheckBox 绑定 GameConfiguration

```lua
local function PopulateCheckBox(control, setting_name)
    local current_value = GameConfiguration.GetValue(setting_name);
    if current_value == nil then
        -- 从数据库获取默认值
        if GameInfo.BTS_Settings[setting_name] then
            current_value = (GameInfo.BTS_Settings[setting_name].Value ~= 0)
        else
            current_value = false;
        end
        GameConfiguration.SetValue(setting_name, current_value);
    end

    control:SetSelected(current_value);
    control:RegisterCallback(Mouse.eLClick, function()
        local selected = not control:IsSelected();
        control:SetSelected(selected);
        GameConfiguration.SetValue(setting_name, selected);
        LuaEvents.BTS_SettingsUpdate();  -- 通知所有监听者
    end);
end
```

### 设置变更广播

```lua
-- 在设置面板中修改设置后广播
LuaEvents.BTS_SettingsUpdate()

-- 在各个 UI 文件中监听
LuaEvents.BTS_SettingsUpdate.Add(OnSettingsChange)

-- 在监听函数中重新读取设置
local function OnSettingsChange()
    showSortPriorities = GameConfiguration.GetValue("BTS_ShowSortPriorities")
    CacheEmpty()
    if m_isOpen then
        Refresh()
    end
end
```

## XML 控件定义

### 居中的浮动面板

```xml
<Context>
  <Container ID="SettingsPanel" Size="380,512" Anchor="C,C" ConsumeMouse="1">
    <Grid Size="parent,parent" Texture="Controls_ContainerBlue"
          SliceStart="0,0" SliceCorner="3,3" SliceSize="9,9" SliceTextureSize="16,16">

      <!-- 标题栏 -->
      <Container ID="Header" Size="parent,54" Anchor="C,T" Style="ShellHeaderContainer">
        <Grid Style="ShellHeaderButtonGrid">
          <Label Style="FontFlair24" FontStyle="glow" ColorSet="ShellHeader"
                 Anchor="C,C" String="LOC_MY_SETTINGS_TITLE"/>
        </Grid>
      </Container>

      <!-- 选项区 -->
      <Container Size="parent,parent-54" Offset="0,20" Anchor="C,T">
        <Stack Anchor="C,T" StackGrowth="Down" Padding="5" Offset="0,50">
          <GridButton ID="MyCheckbox" Anchor="L,C" Offset="0,0" Size="300,24"
                      Style="CheckBoxControl" String="LOC_MY_OPTION_TEXT"/>
        </Stack>
      </Container>

      <!-- 确认按钮 -->
      <Container Size="parent,60" Anchor="C,B" Offset="0,-5">
        <GridButton ID="ConfirmButton" Style="ButtonConfirm"
                    Anchor="C,C" Offset="0,-1" String="LOC_OK_BUTTON" Size="300,41"/>
      </Container>
    </Grid>
  </Container>
</Context>
```

关键属性：
- `Anchor="C,C"` — 屏幕居中
- `ConsumeMouse="1"` — 阻止鼠标穿透到底层 UI
- 不使用 SlideAnim（静态浮动面板）

## 应用场景

- 自定义 Settings / Options 面板
- 确认对话框 / 提示弹窗
- 任何需要浮动在 HUD 上方的独立 UI 面板

## XML 配合

### 涉及的关键 XML 文件

| 文件 | 路径（相对于 Mod 根目录） | 用途 |
|------|--------------------------|------|
| `BTS_SettingsPanel.xml` | `Settings/BTS_SettingsPanel.xml` | 独立 Context，定义浮动设置面板 |

### 核心控件 ID 对照表

| 控件 ID | 类型 | 用途 |
|---------|------|------|
| **面板容器** | | |
| `SettingsPanel` | Container | 浮动面板根容器（Size="380,512", Anchor="C,C", ConsumeMouse="1"），被 ChangeParent 移动到 `/InGame/HUD` |
| **标题栏** | | |
| `Header` | Container | 标题栏容器（Style="ShellHeaderContainer"） |
| **选项区** | | |
| `GeneralOptions` | Container | 选项列表容器 |
| `ApproximateTraderPathCheckbox` | GridButton | 复选框（Style="CheckBoxControl"） |
| `ShowSortPrioritiesCheckbox` | GridButton | 复选框 |
| `ShowAllRoutePathsCheckbox` | GridButton | 复选框 |
| `ShowTraderPathOnSelectionCheckbox` | GridButton | 复选框 |
| **确认按钮** | | |
| `ConfirmButton` | GridButton | 确认/关闭按钮（Style="ButtonConfirm"） |

### 可复用 XML 模板

```xml
<Context>
    <!-- 根容器：居中、消耗鼠标、固定尺寸 -->
    <Container ID="SettingsPanel" Size="380,512" Anchor="C,C" ConsumeMouse="1">
        <Grid Size="parent,parent" Texture="Controls_ContainerBlue" SliceStart="0,0" SliceCorner="3,3" SliceSize="9,9" SliceTextureSize="16,16">
            <!-- 标题栏 -->
            <Container ID="Header" Size="parent,54" Anchor="C,T" Style="ShellHeaderContainer">
                <Grid Style="ShellHeaderButtonGrid">
                    <Label Style="FontFlair24" FontStyle="glow" ColorSet="ShellHeader" Anchor="C,C" String="LOC_MY_TITLE"/>
                </Grid>
            </Container>

            <!-- 选项区域 -->
            <Container ID="OptionsContainer" Size="parent,parent-54" Offset="0,20" Hidden="0" Anchor="C,T">
                <Stack Anchor="C,T" StackGrowth="Down" Padding="5" Offset="0,50">
                    <GridButton ID="Option1Checkbox" Anchor="L,C" Offset="0,0" Size="300,24" Style="CheckBoxControl" String="LOC_OPTION_1"/>
                    <GridButton ID="Option2Checkbox" Anchor="L,C" Offset="0,0" Size="300,24" Style="CheckBoxControl" String="LOC_OPTION_2"/>
                    <!-- 更多选项... -->
                </Stack>
            </Container>

            <!-- 确认按钮 -->
            <Container ID="Footer" Size="parent,60" Anchor="C,B" Offset="0,-5" Style="ShellHeaderContainer">
                <GridButton ID="ConfirmButton" Style="ButtonConfirm" Anchor="C,C" Offset="0,-1" String="LOC_OK" Size="300,41"/>
            </Container>
        </Grid>
    </Container>
</Context>
```
