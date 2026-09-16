# lua-workshop-notification-log — 通知日志面板（WorldTracker 扩展）

从工坊 Mod **Notification Log (1459493312)** 提炼。在 WorldTracker 中创建可折叠的持久化通知日志面板，拦截 `Events.StatusMessage` 将飘屏消息重定向到滚动日志。

---

## 快速索引

| 模式 | 适用场景 |
|------|---------|
| include() 链覆盖 WorldTracker | 在左侧追踪面板中嵌入自定义 UI |
| LuaEvents 跨 Context 通信 | UI 文件间广播状态（如禁用飘屏） |
| BuildInstanceForControl | 在运行时动态创建 XML Instance |
| StatusMessage 拦截重定向 | 将 Gossip/Combat 消息从飘屏改为日志 |
| 日志持久化/清空 | 回合间保留或清空日志条目 |

---

## 一、架构概览

```
WorldTracker.xml (原版)
  └─ WorldTracker.lua (原版)
       └─ WorldTracker_Expansion1.lua (原版)
            └─ WorldTracker_FF16.lua (替换文件, include "WorldTracker_Expansion1")
                 ├─ ContextPtr:BuildInstanceForControl("GossipLogInstance", ...)
                 ├─ ContextPtr:BuildInstanceForControl("GossipOptionsPanel", ...)
                 ├─ Events.StatusMessage.Add(UpdateLogs)   -- 拦截消息
                 └─ Events.LocalPlayerTurnEnd.Add(ClearLogs) -- 回合清空

StatusMessagePanel.lua (替换文件, include "StatusMessagePanel")
  ├─ LuaEvents.FF16_GossipLogDisabled.Add(DisableGossipMessages)
  └─ LuaEvents.FF16_GossipLogEnabled.Add(EnableGossipMessages)
```

---

## 二、include() 链覆盖模式

### 2.1 WorldTracker 覆盖

```lua
-- WorldTracker_FF16.lua — 先加载原版，再扩展功能
include("WorldTracker_Expansion1");

-- 扩展变量
local m_gossipLogInstance  :table = {};
local m_gossipEntryInstances :table = {};
local m_maxLogEntries = 50;

-- 覆盖原有函数
function RealizeEmptyMessage()
    -- 扩展后的逻辑
    if(m_hideChat and m_hideCivics and m_hideResearch and m_hideGossipLog) then
        Controls.EmptyPanel:SetHide(false);
    else
        Controls.EmptyPanel:SetHide(true);
    end
end

-- 新增初始化（会追加到原版 Initialize 之后执行）
function Initialize()
    print("FinalFreak16: Loading Mod - Notification Log.");
    -- 动态创建实例...
end
Initialize();
```

**关键要点：**
- `include("WorldTracker_Expansion1")` 先加载，保证原版所有函数/变量就绪
- 覆盖函数名需与原版一致（如 `RealizeEmptyMessage`）
- 新 `Initialize()` 在原版之后执行，双重初始化安全（Lua 允许重新定义后再调用）

---

## 三、Instance 动态创建

### 3.1 XML Instance 定义

在替换的 WorldTracker.xml 中定义新的 Instance 模板：

```xml
<Instance Name="GossipLogInstance">
    <Grid ID="MainPanel" Size="296,28" Texture="ResearchPanel_Frame" ...>
        <Box ID="GossipLogPanel" Anchor="C,T" Size="294,28">
            <TextButton ID="NewLogNumber" Anchor="L,T" ... />
            <TextButton ID="TitleText" ... String="LOC_FF16_NOTIFICATION_LOG_TITLE" />
            <GridButton ID="OptionsButton" Anchor="R,T" ... />
            <ScrollPanel ID="GossipLogScrollPanel" Vertical="1" ...>
                <ScrollBar ID="GossipScrollBar" ... />
                <Stack ID="GossipLogStack" StackGrowth="Top" />
            </ScrollPanel>
        </Box>
    </Grid>
</Instance>

<Instance Name="GossipLogEntry">
    <Container ID="LogRoot" Anchor="L,C" Size="280,35">
        <Label ID="Icon" ... />
        <Label ID="String" WrapWidth="250" Style="FontNormal12" />
        <Box ID="Divider" Color="255,255,255,35" />
    </Container>
</Instance>

<Instance Name="TurnCountLogEntry">
    <Container ID="LogRoot" Anchor="L,C" Size="280,35">
        <Label ID="String" Anchor="C,C" Style="FontNormal12" />
        <Box ID="Divider" Color="255,255,255,35" />
    </Container>
</Instance>
```

### 3.2 Lua 端创建 Instance

```lua
-- 在 Initialize() 中调用
ContextPtr:BuildInstanceForControl(
    "GossipLogInstance",              -- XML Instance Name
    m_gossipLogInstance,              -- 接收控件引用的 table
    Controls.WorldTrackerVerticalContainer  -- 父容器
);
```

**`BuildInstanceForControl` 参数：**
1. `instanceName` — XML 中 `<Instance Name="...">` 的名字
2. `controlTable` — 空 table，创建后填充控件引用（如 `m_gossipLogInstance.MainPanel`、`m_gossipLogInstance.GossipLogStack`）
3. `parentControl` — 父容器，Instance 挂载到此容器下

### 3.3 日志条目动态生成

```lua
function UpdateGossipLog(logString :string, type:number)
    local controlTable = {};

    if(type == ReportingStatusTypes.DEFAULT) then
        ContextPtr:BuildInstanceForControl(
            "GossipLogEntry", controlTable,
            m_gossipLogInstance.GossipLogStack
        );
    else
        if(string.find(logString, "]TURN")) then
            ContextPtr:BuildInstanceForControl(
                "TurnCountLogEntry", controlTable,
                m_gossipLogInstance.GossipLogStack
            );
        else
            ContextPtr:BuildInstanceForControl(
                "GossipLogEntry", controlTable,
                m_gossipLogInstance.GossipLogStack
            );
        end
    end

    -- 设置文本和图标
    controlTable.String:SetText(gossipText);
    controlTable.Icon:SetText(gossipIcon);

    -- 记录到全局列表（用于清理）
    table.insert(m_gossipEntryInstances, controlTable);
end
```

---

## 四、StatusMessage 拦截与重定向

### 4.1 核心拦截函数

```lua
function UpdateLogs(logString :string, fDisplayTime:number, type:number)
    if(type == ReportingStatusTypes.GOSSIP) then
        if not(m_gossipTurnCounterAdded) then
            AddTurnCounterToLogs(Game.GetCurrentGameTurn(), 1);
            m_gossipTurnCounterAdded = true;
        end
        UpdateGossipLog(logString, type);
    elseif(type == ReportingStatusTypes.DEFAULT) then
        if not(m_combatTurnCounterAdded) then
            AddTurnCounterToLogs(Game.GetCurrentGameTurn(), 2);
            m_combatTurnCounterAdded = true;
        end
        UpdateGossipLog(logString, type);
    end
    UI.PlaySound("Main_Menu_Mouse_Over");
end

-- 在 Initialize() 中注册拦截
Events.StatusMessage.Add(UpdateLogs);
```

### 4.2 日志清空策略

```lua
-- 回合结束时清空
function ClearLogs()
    if not(m_persistGossipLog) then
        ClearGossipLog();
    end
    m_gossipLogNewEntryCount = 0;
    m_gossipLogInstance.NewLogNumber:SetText("");
end

function ClearGossipLog()
    local numLogInstances:number = table.count(m_gossipEntryInstances);
    for i=1, numLogInstances do
        m_gossipLogInstance.GossipLogStack:ReleaseChild(
            m_gossipEntryInstances[i].LogRoot
        );
    end
    m_gossipEntryInstances = {};
    m_gossipLogInstance.GossipLogStack:CalculateSize();
    m_gossipLogInstance.GossipLogStack:ReprocessAnchoring();
end

Events.LocalPlayerTurnEnd.Add(ClearLogs);
```

**ReleaseChild vs ResetInstances：**
- `Stack:ReleaseChild(control)` — 从 Stack 移除单个子控件，用于手动管理
- `InstanceManager:ResetInstances()` — 清空 InstanceManager 管理的所有实例

---

## 五、LuaEvents 跨 Context 通信

### 5.1 StatusMessagePanel.lua — 发送端

```lua
local m_notificationLogDisabled :boolean = false;

function DisableGossipMessages()
    m_notificationLogDisabled = true;
end
function EnableGossipMessages()
    m_notificationLogDisabled = false;
end

-- 注册监听
LuaEvents.FF16_GossipLogDisabled.Add(DisableGossipMessages);
LuaEvents.FF16_GossipLogEnabled.Add(EnableGossipMessages);

-- 在 OnStatusMessage 中判断
function OnStatusMessage(str, fDisplayTime, type)
    if(m_notificationLogDisabled == false) then
        print("Ignoring Notification Message as Notification Log is Enabled.");
        return;  -- 日志启用时跳过飘屏
    end
    -- 正常显示飘屏...
end
```

### 5.2 WorldTracker_FF16.lua — 触发端

```lua
function ToggleGossipLog(hideGossipLog:boolean)
    if hideGossipLog then
        m_gossipLogInstance.MainPanel:SetHide(false);
        Controls.GossipCheck:SetCheck(true);
        m_hideGossipLog = false;
        LuaEvents.FF16_GossipLogEnabled();   -- 广播：日志启用
    else
        m_gossipLogInstance.MainPanel:SetHide(true);
        Controls.GossipCheck:SetCheck(false);
        m_hideGossipLog = true;
        LuaEvents.FF16_GossipLogDisabled();  -- 广播：日志禁用
    end
end
```

**模式总结：**
```
[WorldTracker context]                    [StatusMessagePanel context]
ToggleGossipLog()
  → LuaEvents.FF16_GossipLogEnabled()  →  DisableGossipMessages() 或
  → LuaEvents.FF16_GossipLogDisabled() →  EnableGossipMessages()
```

---

## 六、WorldTracker 下拉栏扩展

### 6.1 XML 中添加 CheckBox

```xml
<!-- 在 WorldTracker.xml 的 DropdownGrid Stack 最末端 -->
<Container ID="GossipCheckButton" Size="auto,auto" Anchor="R,T">
    <CheckBox ID="GossipCheck" Anchor="R,T"
        Style="WorldTrackerCheckBox" TextOffset="-5"
        String="Notification Log" WrapWidth="180" Align="Right"/>
</Container>
```

### 6.2 Lua 中注册处理

```lua
Controls.GossipCheck:SetCheck(true);
Controls.GossipCheck:RegisterCheckHandler(
    function() ToggleGossipLog(m_hideGossipLog); end
);
```

---

## 七、选项面板模式

### 7.1 滑动条 + CheckBox 配置

```lua
-- 滑动条回调
m_gossipOptionsInstance.LogSizeSlider:RegisterSliderCallback(
    function(option)
        if(logSize_sliderValue ~= option) then
            logSize_sliderValue = option;
            logSize_sliderStep = m_gossipOptionsInstance.LogSizeSlider:GetStep();
            -- 更新文本、设置尺寸、播放音效
            m_GL_CurrentSetSize = logSize_sliderStep;
            SetGossipLogSizeLock(m_GL_CurrentSetSize);
            UI.PlaySound("Main_Menu_Mouse_Over");
        end
    end
);

-- 通用 CheckBox 辅助函数
function PopulateCheckBox(control, current_value, check_handler, is_locked)
    if(current_value == 0) then
        control:SetSelected(false);
    else
        control:SetSelected(true);
    end
    control:SetDisabled(is_locked ~= false);
    if(check_handler) then
        control:RegisterCallback(Mouse.eLClick, function()
            local selected = not control:IsSelected();
            control:SetSelected(selected);
            check_handler(selected);
        end);
        control:RegisterCallback(Mouse.eMouseEnter, function()
            UI.PlaySound("Main_Menu_Mouse_Over");
        end);
    end
end
```

### 7.2 选项面板显隐切换

```lua
local m_gossipOptionsHidden :boolean = true;

function OnOpenGossipLogOptions()
    if(m_gossipOptionsHidden) then
        m_gossipOptionsInstance.GossipOptionsRoot:SetHide(false);
        m_gossipOptionsHidden = false;
    else
        m_gossipOptionsInstance.GossipOptionsRoot:SetHide(true);
        m_gossipOptionsHidden = true;
    end
end

-- 绑定到标题点击和按钮
m_gossipLogInstance.TitleText:RegisterCallback(Mouse.eLClick, OnOpenGossipLogOptions);
m_gossipLogInstance.OptionsButton:RegisterCallback(Mouse.eLClick, OnOpenGossipLogOptions);
```

---

## 八、日志条目上限控制

```lua
-- 达到上限时移除最早的条目
if(table.count(m_gossipEntryInstances) > m_maxLogEntries) then
    m_gossipLogInstance.GossipLogStack:ReleaseChild(
        m_gossipEntryInstances[1].LogRoot
    );
    table.remove(m_gossipEntryInstances, 1);
end
```

---

## 九、字符串分割工具

```lua
-- 用于拆分 "[ICON_xxx] Message Text" 格式
function strSplit(self, delimiter)
    local result = {};
    for match in (self..delimiter):gmatch("(.-)"..delimiter) do
        table.insert(result, match);
    end
    return result;
end

-- 使用示例
local gossipString = strSplit(logString, "] ");
local gossipIcon = gossipString[1] .. "]";   -- "[ICON_xxx]"
local gossipText = gossipString[2];            -- "Message Text"
```

---

## 十、关键事件速查

| 事件 | 用途 |
|------|------|
| `Events.StatusMessage(str, time, type)` | 拦截所有飘屏消息（GOSSIP/DEFAULT） |
| `Events.LocalPlayerTurnEnd` | 回合结束清空日志 |
| `Events.LocalPlayerTurnBegin` | 回合开始检测刷新 |
| `LuaEvents.FF16_GossipLogDisabled/Enabled` | 跨 Context 通知日志开关状态 |
| `LuaEvents.Custom_GossipMessage` | 测试用的自定义消息事件 |

---

## 十一、设计要点

1. **双文件替换**：StatusMessagePanel.lua 和 WorldTracker_FF16.lua 都需替换，两者通过 LuaEvents 通信
2. **include() 必须在覆盖文件顶部**：保证原版全局变量已初始化
3. **BuildInstanceForControl 的父容器必须是运行时已存在的控件**：不能挂在 Hidden 容器下
4. **Stack:ReleaseChild() vs InstanceManager:ResetInstances()**：手动管理的列表用 ReleaseChild；IM 管理的用 ResetInstances
5. **GossipLogStack 用 StackGrowth="Top"**：新条目在顶部插入，底部的旧条目被顶出
6. **CalculateSize + ReprocessAnchoring**：每次增删条目后必须调用，否则 Stack 不刷新
7. **日志上限硬编码**：`m_maxLogEntries` 需谨慎调整，避免性能问题

---

## XML 配合

### XML 文件

| 文件 | 路径 | 角色 |
|------|------|------|
| WorldTracker 替换 | `UI/WorldTracker.xml` | 在左侧追踪面板中嵌入日志 + 选项面板 |

**覆盖策略**：同名 `WorldTracker.xml` 替换原版，在 `WorldTrackerVerticalContainer` 中追加新 Instance，在 `DropdownGrid` 中追加 CheckBox。

### 新增控件 ID 对照表

| 控件 ID | 控件类型 | 用途 |
|---------|---------|------|
| `GossipCheck` | CheckBox | WorldTracker 下拉栏中的通知日志开关 |
| `GossipCheckButton` | Container | 开关容器 |

### 新增 Instance 对照表

| Instance Name | 用途 | 关键子控件 |
|--------------|------|----------|
| `GossipLogInstance` | 通知日志面板主体 | `MainPanel` -> `NewLogNumber`(新条目数), `TitleText`(标题), `OptionsButton`(设置按钮), `GossipLogScrollPanel` -> `GossipScrollBar` + `GossipLogStack`(日志条目堆叠，`StackGrowth="Top"`) |
| `GossipLogEntry` | 普通日志条目 | `LogRoot` -> `Icon`(分类图标 Label), `String`(文本 Label, WrapWidth=250), `Divider`(分隔线) |
| `TurnCountLogEntry` | 回合分隔条目 | `LogRoot` -> `String`(居中回合标识), `Divider` |
| `GossipOptionsPanel` | 日志设置面板 | `GossipOptionsRoot`(Hidden=1) -> `Background` -> `MainStack` -> `LogSizeSlider`(滑动条), `LogMaxSizeSlider`(上限滑动条), `EmptyLogCheckBox`(自动清空) |

### Instance 结构模板

```xml
<Instance Name="GossipLogInstance">
  <Grid ID="MainPanel" Size="296,28" Texture="ResearchPanel_Frame" Color="15,56,89,205">
    <Box ID="GossipLogPanel" Anchor="C,T" Offset="0,1" Size="294,28" Color="15,56,89,205">
      <TextButton ID="NewLogNumber" Anchor="L,T" Offset="5,4" Style="FontFlair16" Color0="150,150,150,255" />
      <Stack Anchor="C,T" StackGrowth="Right">
        <Image Offset="0,1" Size="22,22" IconSize="22" Icon="ICON_GOSSIP"/>
        <TextButton ID="TitleText" Offset="2,6" Anchor="C,T" Size="200,40" Style="PanelHeaderText" String="..."/>
      </Stack>
      <GridButton ID="OptionsButton" Anchor="R,T" Offset="1,-1" Size="25,25" ... />
      <Container Size="parent,parent-5" Offset="-5,0">
        <ScrollPanel ID="GossipLogScrollPanel" Anchor="L,T" Offset="20,35" Vertical="1" Size="296,parent-35">
          <ScrollBar ID="GossipScrollBar" Style="Slider_Blue" ... />
          <Stack ID="GossipLogStack" Anchor="L,T" Offset="-5,-7" StackGrowth="Top" />
        </ScrollPanel>
      </Container>
    </Box>
  </Grid>
</Instance>

<Instance Name="GossipLogEntry">
  <Container ID="LogRoot" Offset="0,9" Anchor="L,C" Size="280,35">
    <Stack Anchor="L,C" StackGrowth="Right">
      <Label ID="Icon" Anchor="L,C" Offset="-5,2"/>
      <Label ID="String" Anchor="L,C" Offset="2,0" WrapWidth="250" Style="FontNormal12" />
    </Stack>
    <Box ID="Divider" Anchor="L,B" Offset="-13,-5" Size="294,1" Color="255,255,255,35"/>
  </Container>
</Instance>
```
