# UI Popup Choice System

## 来源
- Choosable Goody Huts (Konomi, id=3014867813) — 村庄奖励选择弹窗
- Celebrations (Nwflower, id=3492136529) — 庆典选择弹窗

## 概述
实现"游戏事件触发 -> 弹出 UI 面板 -> 玩家选择 -> 执行效果"的完整流程。核心是 UI 端和 Gameplay 端通过 `PlayerOperations.EXECUTE_SCRIPT` 通信。

## 架构

```
[Gameplay事件] -> [Notification] -> [NotificationPanel替换] -> [UI弹窗] -> [UI.RequestPlayerOperation] -> [Gameplay执行]
```

## 步骤 1：自定义通知类型 (SQL)

```sql
INSERT INTO Types (Type, Kind)
VALUES ('NOTIFICATION_YOUR_MOD', 'KIND_NOTIFICATION');

INSERT INTO Notifications (NotificationType, SeverityType, ExpiresEndOfTurn, AutoNotify, AutoActivate, Message, Summary)
VALUES ('NOTIFICATION_YOUR_MOD', 'MID', 1, 0, 1,
    'LOC_YOUR_MOD_TITLE', 'LOC_YOUR_MOD_DESC');
```

关键字段：
- `AutoNotify=0, AutoActivate=1` — 自动激活（而不是自动通知），适合需要玩家操作的通知
- `SeverityType` — HIGH/MID/LOW，影响通知排序

## 步骤 2：Gameplay 端发送通知 (Lua)

```lua
-- 在 Gameplay 脚本中 (AddGameplayScripts)
function TrySendNotification(playerID, unitID, x, y)
    local pPlayer = Players[playerID]
    if not pPlayer:IsHuman() then return end

    local notificationData = {}
    notificationData[ParameterTypes.MESSAGE] = Locale.Lookup(m_NotificationInfo.Message)
    notificationData[ParameterTypes.SUMMARY] = Locale.Lookup(m_NotificationInfo.Summary)
    notificationData[ParameterTypes.LOCATION] = { x = x, y = y }
    notificationData.UnitID = unitID  -- 自定义数据，UI 端读取

    NotificationManager.SendNotification(playerID, m_NotificationInfo.Hash, notificationData)
end

-- 在游戏事件中调用
function OnUnitTriggerGoodyHut(playerID, unitID, goodyHutType)
    TrySendNotification(playerID, unitID, x, y)
end
Events.UnitTriggerGoodyHut.Add(OnUnitTriggerGoodyHut)
```

## 步骤 3：替换 NotificationPanel 处理函数 (UI/Lua)

用 `g_notificationHandlers[hash]` 替换默认行为：

```lua
-- UI/Replacements/ 或 UI/ 下的文件，作为 ImportFiles 加载
local BASE_RegisterHandlers = RegisterHandlers;
local m_NotificationInfo = GameInfo.Notifications['NOTIFICATION_YOUR_MOD'];

function OnNotificationAdd(pNotification)
    -- 调用原始处理器
    OnDefaultAddNotification(pNotification)

    -- 检查是否是当前玩家回合
    if pNotification and Players[pNotification:GetPlayerID()]:IsTurnActive() then
        -- 读取自定义数据
        local unitID = pNotification:GetValue('UnitID')
        local x, y = pNotification:GetLocation()

        -- 触发弹窗（通过 LuaEvents 传递给弹窗 UI）
        LuaEvents.YourMod_OpenPopup(unitID, x, y, extraData)
    end
end

function OnNotificationActivate(notificationEntry, notificationID, activatedByUser)
    -- 玩家点击通知时也触发弹窗
    if notificationEntry.m_PlayerID == Game.GetLocalPlayer() then
        local pNotification = GetActiveNotificationFromEntry(notificationEntry, notificationID)
        if pNotification then
            -- 同样调用弹窗
            LuaEvents.YourMod_OpenPopup(...)
        end
    end
end

function RegisterHandlers()
    BASE_RegisterHandlers();
    if m_NotificationInfo then
        local hash = m_NotificationInfo.Hash
        g_notificationHandlers[hash] = MakeDefaultHandlers();
        g_notificationHandlers[hash].Add = OnNotificationAdd;
        g_notificationHandlers[hash].Activate = OnNotificationActivate;
        g_notificationHandlers[hash].AddSound = "ALERT_POSITIVE";
        -- 禁用默认 dismiss 行为，让通知常驻直到处理
        g_notificationHandlers[hash].TryDismiss = function() return; end;
    end
end
```

**加载方式**：NotificationPanel 替换脚本必须作为 `ImportFiles` 加载（不是 `AddUserInterfaces`），因为需要覆盖全局的 `RegisterHandlers` 函数。

## 步骤 4：弹窗 UI (XML + Lua)

### XML 模板

```xml
<Context>
    <Container Style="FullScreenVignetteConsumer"/>
    <BoxButton ID="ScreenConsumer" ConsumeMouseButton="1" ConsumeMouseWheel="1"/>

    <Grid ID="DropShadow" Size="595,250" Anchor="C,C" Style="DropShadow2">
        <Grid ID="Window" Anchor="C,C" Style="EventPopupFrame">
            <Grid Style="EventPopupTitleBar" Anchor="C,T">
                <Label ID="EventTitle" Style="EventPopupTitle" String="LOC_YOUR_TITLE"/>
            </Grid>

            <Container ID="MainContainer" Anchor="C,T">
                <Stack StackGrowth="Down">
                    <Label ID="EventDescription" WrapWidth="parent-20"/>
                    <PullDown ID="Pulldown" Anchor="C,T">
                        <!-- 下拉选择控件 -->
                    </PullDown>
                </Stack>
            </Container>

            <Stack Anchor="C,B" StackGrowth="Right" StackPadding="20">
                <GridButton ID="OKButton" Style="MainButton" Size="220,40" String="LOC_OK"/>
                <GridButton ID="ContinueButton" Style="MainButton" Size="220,40" String="LOC_CANCEL"/>
            </Stack>
        </Grid>
    </Grid>
</Context>
```

### Lua 脚本

```lua
function Open(unitID, x, y, extraData)
    -- 用 QueuePopup 而不是直接显示
    if not UIManager:IsInPopupQueue(ContextPtr) then
        UIManager:QueuePopup(ContextPtr, PopupPriority.Low)
        UI.PlaySound("UI_Screen_Open");
    end
end

function Close()
    if UIManager:DequeuePopup(ContextPtr) then
        UI.PlaySound("UI_Screen_Close");
    end
end

function OnOKButton()
    local kParameters = {
        OnStart = 'YourGameplayHandlerName',
        -- 传递选择的数据
        ChosenOption = m_SelectedOption,
        UnitID = m_UnitID,
    }

    -- 核心：UI -> Gameplay 通信
    UI.RequestPlayerOperation(Game.GetLocalPlayer(), PlayerOperations.EXECUTE_SCRIPT, kParameters)
    Close()
end

-- 初始化
function Initialize()
    ContextPtr:SetInputHandler(OnInputHandler, true);
    Controls.OKButton:RegisterCallback(Mouse.eLClick, OnOKButton);
    Controls.ContinueButton:RegisterCallback(Mouse.eLClick, Close);
end
Initialize();
```

## 步骤 5：Gameplay 端响应 UI 请求

```lua
-- 在 AddGameplayScripts 中注册 GameEvents
function YourGameplayHandler(playerID, params)
    if Players[playerID] then
        -- 执行 Modifier 效果
        Players[playerID]:AttachModifierByID(params.ModifierID)

        -- 或对单位添加能力
        local pUnit = UnitManager.GetUnit(playerID, params.UnitID)
        if pUnit then
            pUnit:GetAbility():ChangeAbilityCount(ability, 1)
            pUnit:GetAbility():ChangeAbilityCount(ability, -1)
        end
    end
end

-- 注册 GameEvents
GameEvents.YourGameplayHandlerName.Add(YourGameplayHandler)
```

**关键**：`kParameters.OnStart` 的值必须与 `GameEvents.<name>.Add()` 的名称完全一致。

## 步骤 6：双倍奖励适配（可选）

Choosable Goody Huts 展示了如何支持"双倍奖励" Mod：

```lua
-- 在弹窗 Open 时接收 double 标记
function Open(unitID, x, y, double)
    m_IsDouble = double
end

-- 在 OK 按钮回调中传递
if m_IsDoubleGoodyModActive and not m_IsDouble then
    kParameters.Double = true  -- 需要再次触发
    kParameters.X = x
    kParameters.Y = y
end
```

## 步骤 7：通知清理

```lua
-- 弹窗关闭后 dismiss 通知
function DismissNotification()
    if m_NotificationID ~= -1 then
        NotificationManager.Dismiss(playerID, m_NotificationID)
        m_NotificationID = -1
    end
end

LuaEvents.YourMod_Dismiss.Add(DismissNotification)
```

## modinfo 配置要点

```
<InGameActions>
    <!-- Gameplay脚本：发送通知 + 处理UI请求 -->
    <AddGameplayScripts>
        <File>Scripts/YourMod.lua</File>
    </AddGameplayScripts>

    <!-- NotificationPanel替换（覆盖RegisterHandlers）必须用ImportFiles -->
    <ImportFiles>
        <File>UI/Replacements/NotificationPanel_YourMod.lua</File>
    </ImportFiles>

    <!-- 弹窗UI（标准AddUserInterfaces） -->
    <AddUserInterfaces>
        <File>UI/Additions/YourPopup.xml</File>
    </AddUserInterfaces>
</InGameActions>
```

**注意**：
- `ImportFiles` 中的 Lua 文件在所有文件之前加载，适合覆盖全局函数
- `AddGameplayScripts` 加载到 Gameplay 上下文
- NotificationPanel 替换脚本必须在 UI 上下文中导入（FrontEnd 或 ImportFiles）

## Celebration 面板 vs Goody Hut 面板的差异

| 特性 | Goody Hut 弹窗 | Celebration 面板 |
|------|---------------|-----------------|
| 触发器 | UnitTriggerGoodyHut 事件 | PlayerTurnActivated 事件 |
| 通知 | 自定义通知类型 | 自定义通知类型 |
| 弹出方式 | QueuePopup (Low priority) | SetHide(false/true) |
| 选择控件 | PullDown 下拉 | InstanceManager 列表 |
| 关闭方式 | ESC + Cancel 按钮 | CloseButton + Skip |
| 通信方式 | PlayerOperations.EXECUTE_SCRIPT | PlayerOperations.EXECUTE_SCRIPT |
| 重复触发 | 每次踩村庄 | 每回合检查 |

## 要点总结

1. **UI->GP 通信**：`UI.RequestPlayerOperation(playerID, PlayerOperations.EXECUTE_SCRIPT, params)`，其中 `params.OnStart` 是 `GameEvents` 名称
2. **NotificationPanel 替换**：必须用 `ImportFiles`，在 `RegisterHandlers()` 中覆盖 `g_notificationHandlers[hash]`
3. **弹窗生命周期**：`UIManager:QueuePopup` / `DequeuePopup`，检查 `IsInPopupQueue` 避免重复弹出
4. **自定义数据传递**：通过 `notificationData[key]` 存储，`pNotification:GetValue(key)` 读取

---

## XML 配合

### 来源一：Choosable Goody Huts（3014867813）

| 文件 | 路径 | 角色 |
|------|------|------|
| 弹窗布局 | `UI/Additions/ChoosableGoodyHuts.xml` | 村庄选择弹窗（PullDown 模式） |

**核心控件 ID：**

| 控件 ID | 控件类型 | 用途 |
|---------|---------|------|
| `ScreenConsumer` | BoxButton | 全屏点击遮罩 |
| `DropShadow` | Grid | 弹窗阴影框（595x250） |
| `Window` | Grid | 弹窗主窗口（`Style="EventPopupFrame"`） |
| `EventTitle` | Label | 弹窗标题 |
| `EventDescription` | Label | 弹窗描述文字 |
| `Pulldown` | PullDown | 选项下拉选择器 |
| `OKButton` | GridButton | 确认按钮（初态 `Disabled="1"`） |
| `ContinueButton` | GridButton | 取消/关闭按钮 |

**标准弹窗框架模板：**
```xml
<Context>
    <Container Style="FullScreenVignetteConsumer"/>
    <BoxButton ID="ScreenConsumer" Color="0,0,0,0" Size="parent,parent"
               ConsumeMouseButton="1" ConsumeMouseWheel="1"/>
    <Grid ID="DropShadow" Size="595,250" Anchor="C,C" Style="DropShadow2">
        <Grid ID="Window" Size="parent-5,parent+8" Anchor="C,C"
              Style="EventPopupFrame" SizePadding="0,20">
            <Grid Style="EventPopupTitleBar" Size="parent-32,65"
                  Offset="0,17" Anchor="C,T">
                <Label ID="EventTitle" Style="EventPopupTitle"/>
            </Grid>
            <Container ID="MainContainer" Size="parent-32,570" Anchor="C,T">
                <!-- 内容区（PullDown / InstanceManager） -->
            </Container>
            <Stack ID="ButtonStack" Anchor="C,B" Offset="0,26"
                   StackPadding="20" StackGrowth="Right">
                <GridButton ID="OKButton" Style="MainButton" Size="220,40" String="LOC_OK"/>
                <GridButton ID="ContinueButton" Style="MainButton" Size="220,40" String="LOC_CANCEL"/>
            </Stack>
        </Grid>
    </Grid>
</Context>
```

### 来源二：Celebrations（3492136529）

| 文件 | 路径 | 角色 |
|------|------|------|
| 庆典面板 | `UI/Celebration_Panel.xml` | 庆典选择面板（InstanceManager 列表模式） |

**核心控件 ID：**

| 控件 ID | 控件类型 | 用途 |
|---------|---------|------|
| `PopupBackground` | Image | 仿羊皮纸背景（`Ages_ParchmentNormal`） |
| `PopupFrame` | Grid | 仿古框架（`Ages_FrameNormal`） |
| `Title` | Label | 面板标题 |
| `AgeAchieved` | Label | 进入的时代名称（副标题） |
| `CommemorationsScroller` | ScrollPanel | 纪念选项滚动区 |
| `CommemorationsStack` | Stack | 纪念条目堆叠 |
| `CommemorationsScrollBar` | ScrollBar | 滚动条 |
| `Confirm` | GridButton | 确认按钮（初态 `Disabled="1"`） |
| `CloseButton` | Button | 关闭按钮 |
| `HeroicFrameGlow` | Image | 英雄时代发光特效 |

**Instance 对照表（Celebration_Panel.xml）：**

| Instance Name | 用途 | 子控件 |
|--------------|------|--------|
| `Commemoration` | 纪念选项条目 | `SelectCheck`(GridButton, States=7) -> `CommemorationIcon`(86x86), `MomentCategory`(类别名), `MomentBonuses`(效果文本) |

**InstanceManager 列表模板：**
```xml
<Instance Name="Commemoration">
    <GridButton ID="SelectCheck" Anchor="C,C" Size="parent-44,auto"
                MinSize="0,136" AutoSizePadding="0,20"
                Texture="Ages_ButtonComNormal" States="7"
                StateOffsetIncrement="0,136">
        <Image Texture="Ages_ComIconFrame" Anchor="L,C" Offset="26,0" Size="84,84">
            <Image ID="CommemorationIcon" Anchor="C,C"
                   Size="86,86" Icon="ICON_COMMEMORATION_INFRASTRUCTURE" IconSize="86"/>
        </Image>
        <Stack Anchor="L,C" Offset="120,0" StackGrowth="Down" StackPadding="4">
            <Label ID="MomentCategory" Style="WindowHeader" WrapWidth="490"/>
            <Label ID="MomentBonuses" Style="FontNormal14" WrapWidth="490"/>
        </Stack>
    </GridButton>
</Instance>
```

### 两种弹窗模式对比

| 特性 | PullDown 模式（Goody Huts） | InstanceManager 模式（Celebrations） |
|------|--------------------------|-------------------------------------|
| 选择控件 | PullDown 下拉 | InstanceManager 网格/列表 |
| 适用场景 | 选项少、文本简短 | 选项多、带图标描述 |
| 弹出方式 | QueuePopup | SetHide(false/true) |
| 初始确认按钮 | Disabled=1（先选后点） | Disabled=1（先选后点） |
| 关闭方式 | Cancel 按钮 + ESC | CloseButton + Skip |
| XML 复杂度 | 低（PullDown 内嵌 InstanceData） | 中（独立 Instance + ScrollPanel） |
