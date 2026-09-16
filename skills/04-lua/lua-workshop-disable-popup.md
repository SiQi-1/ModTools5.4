# lua-workshop-disable-popup — 弹窗禁用/条件跳过

从工坊 Mod **Disable Tech Civic Popup (2994800768)** 提炼。通过 include() 覆盖 + 保存原始函数引用，实现条件性地跳过游戏原生弹窗。同时演示 TopPanel 按钮注入和 GameConfiguration 持久化配置 UI。

---

## 快速索引

| 模式 | 适用场景 |
|------|---------|
| include() + BASE_ 函数引用 | 条件跳过任何游戏原生弹窗 |
| GameConfiguration.SetValue/GetValue | 跨会话持久化 Mod 选项 |
| TopPanel 按钮注入 | 在顶部栏添加 Mod 设置入口 |
| LookUpControl + ChangeParent | 将自定义控件挂入游戏现有面板 |

---

## 一、架构概览

```
TechCivicCompletedPopup_DTCP.lua (替换文件)
  └─ include("TechCivicCompletedPopup.lua")   -- 先加载原版
       ├─ Base_AddCompletedPopup = AddCompletedPopup   -- 保存原函数
       └─ function AddCompletedPopup(...)              -- 覆盖
            ├─ if (tech and !enableTechPopup) → return -- 跳过
            └─ Base_AddCompletedPopup(...)             -- 否则原样调用

DTCP_UI.lua (独立 UI Context)
  ├─ Controls.DTCP_Button:ChangeParent(topPanel)       -- 注入按钮
  ├─ Controls.DTCP_Panel:SetHide/SetShow              -- 配置面板显隐
  ├─ Controls.DTCP_TechCheckBox/CivicCheckBox          -- 选项绑定
  └─ GameConfiguration.SetValue("enableTechPopup", ...)
```

---

## 二、弹窗条件跳过模式

### 2.1 核心模板

```lua
-- TechCivicCompletedPopup_DTCP.lua
include("TechCivicCompletedPopup.lua");  -- 加载原版

-- 保存原始函数引用
Base_AddCompletedPopup = AddCompletedPopup;

-- 覆盖同名函数
function AddCompletedPopup(player:number, civic:number, tech:number, isByUser:boolean)
    -- 条件路由
    if (tech and not GameConfiguration.GetValue('enableTechPopup'))
    or (civic and not GameConfiguration.GetValue('enableCivicPopup')) then
        return;  -- 跳过弹窗
    end

    -- 回退到原始行为
    Base_AddCompletedPopup(player, civic, tech, isByUser);
end
```

### 2.2 通用模板

```lua
-- 1. 加载原始 UI 文件
include("TargetGameUIFile");

-- 2. 保存需要覆盖的原始函数
local BASE_TargetFunction = TargetFunction;

-- 3. 重新定义同名函数
function TargetFunction(...)
    -- 条件路由：如果不满足自定义条件，跳过
    if ShouldSkipPopup() then
        return;
    end

    -- 条件路由：如果不属于目标玩家/场景，回退原版
    if not IsTargetPlayer() then
        BASE_TargetFunction(...);
        return;
    end

    -- 自定义逻辑...
    BASE_TargetFunction(...);  -- 或完全替换
end
```

### 2.3 常见跳过场景

| 场景 | 判断条件 | 处理 |
|------|---------|------|
| 跳过科技完成弹窗 | `tech and not enableTechPopup` | `return` |
| 跳过市政完成弹窗 | `civic and not enableCivicPopup` | `return` |
| 跳过后保留音效/通知 | 调用原生逻辑的子集 | 部分调用 BASE_ |
| 自定义弹窗内容 | 全部替换 | 不调用 BASE_ |
| 条件性静默完成 | `isByUser == false` | `return`（非玩家操作不弹） |

---

## 三、GameConfiguration 持久化配置

### 3.1 读写配置

```lua
-- 写入
GameConfiguration.SetValue('enableTechPopup', enableTechPopup);
GameConfiguration.SetValue('enableCivicPopup', enableCivicPopup);

-- 读取
local enableTechPopup = GameConfiguration.GetValue('enableTechPopup');
-- 注意：GetValue 在初始化前可能返回 nil，需用 || 兜底或确保 Initialize() 先写入
```

**关键特性：**
- 配置值跨存档持久化（写入 GameConfiguration 表）
- 无需手动保存/加载 — 游戏自动管理
- 值可以是 `boolean`、`number`、`string`
- Key 采用小驼峰命名，避免与游戏原生键冲突

### 3.2 初始化即写入默认值

```lua
function Initialize()
    enableTechPopup = false;   -- 默认关闭
    enableCivicPopup = false;
    Controls.DTCP_TechCheckBox:SetCheck(enableTechPopup);
    Controls.DTCP_CivicCheckBox:SetCheck(enableCivicPopup);
    GameConfiguration.SetValue('enableTechPopup', enableTechPopup);
    GameConfiguration.SetValue('enableCivicPopup', enableCivicPopup);
end
```

---

## 四、TopPanel 按钮注入

### 4.1 核心代码

```lua
local function AddButtonToTopPanel()
    -- 1. 查找 TopPanel 的右内容区
    local topPanel = ContextPtr:LookUpControl(
        "/InGame/TopPanel/RightContents"
    );

    -- 2. 将自定义按钮挂入该面板
    Controls.DTCP_Button:ChangeParent(topPanel);

    -- 3. 按索引插入（排在第 3 个子控件位置）
    topPanel:AddChildAtIndex(Controls.DTCP_Button, 3);

    -- 4. 刷新布局
    topPanel:CalculateSize();
    topPanel:ReprocessAnchoring();
end
```

### 4.2 XML 定义

```xml
<Context Name="DTCP_Context">
    <!-- 顶部栏按钮 -->
    <Button ID="DTCP_Button"
        Size="29,29"
        Anchor="C,C"
        Texture="DTCP_Icon.dds"
        ToolTip="LOC_DTCP_BUTTON_TOOLTIP"
        ConsumeMouse="1"/>

    <!-- 配置弹出面板 -->
    <Container ID="DTCP_Container" Size="500,500" Anchor="C,C">
        <Container ID="DTCP_Panel" Size="500,140" Anchor="C,T"
                   ConsumeMouse="1" Hidden="1">
            <Grid ID="DTCP_PanelGrid"
                  Texture="Controls_PanelBlue"
                  Style="CityPanelSlotGrid" ...>
                <Stack ID="DTCP_PanelStack" Anchor="C,T"
                       StackGrowth="Bottom" StackPadding="5">
                    <!-- 标题 -->
                    <Label ID="DTCP_Title" String="LOC_DTCP_TITLE" ... />
                    <!-- 科技开关 -->
                    <CheckBox ID="DTCP_TechCheckBox" ... />
                    <!-- 市政开关 -->
                    <CheckBox ID="DTCP_CivicCheckBox" ... />
                    <!-- 关闭按钮 -->
                    <GridButton ID="DTCP_OK_Button" String="LOC_OK_BUTTON" ... />
                </Stack>
            </Grid>
        </Container>
    </Container>
</Context>
```

### 4.3 常用父容器路径

| LookUpControl 路径 | 注入位置 |
|-------------------|---------|
| `/InGame/TopPanel/RightContents` | 顶部栏右侧（科技/市政旁边） |
| `/InGame/TopPanel` | 整个顶部栏 |
| `/InGame/TopPanel/LeftContents` | 顶部栏左侧 |
| `/InGame/LaunchBar/ButtonStack` | 单位命令条的按钮区 |
| `/InGame/CityPanel/ActionStack` | 城市面板的操作按钮区 |
| `/InGame/UnitPanel/StandardActionsStack` | 单位面板的标准操作区 |

---

## 五、配置面板显隐切换

### 5.1 按钮点击

```lua
local function ToggleDialogVisibility()
    Controls.DTCP_Panel:SetHide(not Controls.DTCP_Panel:IsHidden());
end

-- 按钮注册
Controls.DTCP_Button:RegisterCallback(Mouse.eLClick, OnTopPanelButtonClick);
Controls.DTCP_OK_Button:RegisterCallback(Mouse.eLClick, OnMenuCloseButtonClick);
```

### 5.2 CheckBox 绑定

```lua
local function ToggleTech()
    enableTechPopup = not enableTechPopup;
    GameConfiguration.SetValue('enableTechPopup', enableTechPopup);
end

local function ToggleCivic()
    enableCivicPopup = not enableCivicPopup;
    GameConfiguration.SetValue('enableCivicPopup', enableCivicPopup);
end

Controls.DTCP_TechCheckBox:RegisterCallback(Mouse.eLClick, ToggleTech);
Controls.DTCP_CivicCheckBox:RegisterCallback(Mouse.eLClick, ToggleCivic);
```

**注意：** 这里使用 `Mouse.eLClick` 直接监听，而非 `RegisterCheckHandler`。两种方式等价，但 `RegisterCallback` 需自行翻转状态，`RegisterCheckHandler` 自动传递布尔值。

---

## 六、初始化时机

```lua
-- DTCP_UI.lua
local function Initialize()
    Controls.DTCP_Button:RegisterCallback(Mouse.eLClick, OnTopPanelButtonClick);
    Controls.DTCP_OK_Button:RegisterCallback(Mouse.eLClick, OnMenuCloseButtonClick);
    Controls.DTCP_TechCheckBox:RegisterCallback(Mouse.eLClick, ToggleTech);
    Controls.DTCP_CivicCheckBox:RegisterCallback(Mouse.eLClick, ToggleCivic);
    AddButtonToTopPanel();
    ContextPtr:SetHide(false);

    -- 设置默认值
    enableTechPopup = false;
    enableCivicPopup = false;
    Controls.DTCP_TechCheckBox:SetCheck(enableTechPopup);
    Controls.DTCP_CivicCheckBox:SetCheck(enableCivicPopup);
    GameConfiguration.SetValue('enableTechPopup', enableTechPopup);
    GameConfiguration.SetValue('enableCivicPopup', enableCivicPopup);
end

local function OnLoadGameViewStateDone()
    Initialize();
end

Events.LoadGameViewStateDone.Add(OnLoadGameViewStateDone);
```

**关键：** 必须等到 `Events.LoadGameViewStateDone` 再初始化，此时 `/InGame/TopPanel/RightContents` 等控件路径才可用。

---

## 七、ModBuddy 配置

### 7.1 文件替换声明

在 `.modinfo` 中声明 UI 文件替换：

```xml
<!-- 替换 TechCivicCompletedPopup.lua -->
<ReplaceUIScript>
    <LuaContext>TechCivicCompletedPopup</LuaContext>
    <LuaReplace>TechCivicCompletedPopup_DTCP.lua</LuaReplace>
</ReplaceUIScript>
```

### 7.2 独立 UI Context 声明

```xml
<!-- DTCP_UI.xml + DTCP_UI.lua 组成独立 Context -->
<AddUserInterfaces>
    <File>DTCP_UI</File>
    <Name>DTCP_Context</Name>
</AddUserInterfaces>
```

---

## 八、完整文件清单

| 文件 | 角色 |
|------|------|
| `DTCP_UI.xml` | 配置面板 + TopPanel 按钮的 XML |
| `DTCP_UI.lua` | 按钮逻辑、面板显隐、GameConfiguration 读写 |
| `DTCP_UI.dds` | 按钮图标 |
| `TechCivicCompletedPopup_DTCP.lua` | 替换文件：条件跳过弹窗 |
| `DTCP_Text.xml` | 本地化文本（多语言） |

---

## 九、设计要点

1. **include() 必须第一行**：`include("TechCivicCompletedPopup.lua")` 必须在文件最顶部，确保所有原版变量/函数已定义
2. **BASE_ 命名约定**：原始函数引用用 `Base_` 或 `BASE_` 前缀，清晰区分覆盖函数
3. **条件路由两层判断**：先判断是否跳过（`return`），再判断是否回退原版（调 `BASE_`），最后才是自定义逻辑
4. **GameConfiguration 默认值**：Initialize() 中先 `SetValue` 写入默认值，避免 `GetValue` 返回 nil 导致逻辑异常
5. **TopPanel 注入时机**：必须在 `Events.LoadGameViewStateDone` 之后，否则 `LookUpControl` 路径不存在
6. **面板用 Hidden 控制**：初始化设为 `Hidden="1"`，点击按钮时切换
7. **`ChangeParent` + `AddChildAtIndex`**：改变父容器并控制排序位置
8. **`CalculateSize + ReprocessAnchoring`**：改变父容器后必须调用，否则布局异常

---

## 十、扩展：弹窗替换（非跳过）

当需要修改弹窗内容而非跳过时：

```lua
include("TargetPopup.lua");
local BASE_ShowPopup = ShowPopup;

function ShowPopup(...)
    -- 自定义条件判断
    if IsCustomScenario() then
        -- 完全自定义的弹窗逻辑
        ShowCustomPopup(...);
    else
        -- 回退原版
        BASE_ShowPopup(...);
    end
end
```

**常见可替换弹窗文件：**
| 游戏文件 | 弹窗内容 |
|---------|---------|
| `TechCivicCompletedPopup` | 科技/市政完成 |
| `BoostUnlockedPopup` | 尤里卡/鼓舞触发 |
| `EndGameMenu` | 游戏结束画面 |
| `DiplomacyActionView` | 外交面板 |
| `GreatPersonPopup` | 伟人招募 |
| `GreatWorksOverview` | 巨作展示 |
| `WorldCongresPopup` | 世界议会 |

---

## XML 配合

### XML 文件

| 文件 | 路径 | 角色 |
|------|------|------|
| 配置面板 + 按钮 | `DTCP_UI.xml` | TopPanel 按钮 + 设置弹出面板 |

Mod 的 Lua 覆盖文件（`TechCivicCompletedPopup_DTCP.lua`）不需要独立 XML——它通过 `include()` 复用原版 `TechCivicCompletedPopup.xml`。配置 UI 使用独立的 XML/Lua Context。

### 核心控件 ID 对照表

| 控件 ID | 控件类型 | 用途 |
|---------|---------|------|
| `DTCP_Button` | Button | TopPanel 注入按钮（29x29，`Texture="DTCP_Icon.dds"`） |
| `DTCP_Container` | Container | 居中定位容器 |
| `DTCP_Panel` | Container | 设置弹出面板（`Hidden="1"`，500x140） |
| `DTCP_PanelGrid` | Grid | 面板背景（`Texture="Controls_PanelBlue"`） |
| `DTCP_PanelStack` | Stack | 面板内容栈（`StackGrowth="Bottom"`） |
| `DTCP_Title` | Label | 面板标题 |
| `DTCP_TechCheckBox` | CheckBox | 科技弹窗开关（`IsChecked="0"` 默认关） |
| `DTCP_CivicCheckBox` | CheckBox | 市政弹窗开关（`IsChecked="0"` 默认关） |
| `DTCP_OK_Button` / `DTCP_OK_ButtonGrid` | GridButton / Grid | 关闭按钮 |

### 面板 XML 模板

```xml
<Context Name="DTCP_Context">
    <!-- TopPanel 注入按钮 -->
    <Button ID="DTCP_Button" Size="29,29" Anchor="C,C"
            Texture="DTCP_Icon.dds"
            ToolTip="LOC_DTCP_BUTTON_TOOLTIP" ConsumeMouse="1"/>

    <!-- 设置弹出面板 -->
    <Container ID="DTCP_Container" Size="500,500" Anchor="C,C">
        <Container ID="DTCP_Panel" Size="500,140" Anchor="C,T"
                   ConsumeMouse="1" Hidden="1">
            <Grid ID="DTCP_PanelGrid" Anchor="C,T"
                  Texture="Controls_PanelBlue" Size="parent,parent"
                  Style="CityPanelSlotGrid" ...>
                <Stack ID="DTCP_PanelStack" Anchor="C,T"
                       Size="parent-40,auto" StackGrowth="Bottom" StackPadding="5">
                    <Label ID="DTCP_Title" Anchor="C,C"
                           String="LOC_DTCP_TITLE" Style="PanelHeaderText" .../>
                    <CheckBox ID="DTCP_TechCheckBox" IsChecked="0"
                              String="LOC_DTCP_TECH_CHECKBOX" .../>
                    <CheckBox ID="DTCP_CivicCheckBox" IsChecked="0"
                              String="LOC_DTCP_CIVIC_CHECKBOX" .../>
                    <GridButton ID="DTCP_OK_Button" Size="150,40"
                                Style="MainButton" String="LOC_OK_BUTTON" />
                </Stack>
            </Grid>
        </Container>
    </Container>
</Context>
```

### 按钮注入路径参考

| LookUpControl 路径 | 注入位置 |
|-------------------|---------|
| `/InGame/TopPanel/RightContents` | 顶部栏右侧（本 Mod 使用） |
| `/InGame/TopPanel` | 整个顶部栏 |
| `/InGame/LaunchBar/ButtonStack` | 单位命令条按钮区 |
| `/InGame/CityPanel/ActionStack` | 城市面板操作区 |
