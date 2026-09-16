# Quick Deals — 快速交易系统

参考 Mod: Quick Deals (2460661464)

## 核心架构

模块分四层：入口按钮 (LaunchButton) -> 主弹窗 (DealPopup) -> 交易逻辑 (DealManager, OfferAutomator) -> 缓存 (CacheManager)。

三个 Tab 各自独立：Sale（出售）、Purchase（购买）、Exchange（黄金兑换）。

## 模式 1: 启动栏按钮注入

将自定义按钮注入到游戏 LaunchBar 的 ButtonStack：

```lua
function AttachLaunchButton()
    local buttonStack = ContextPtr:LookUpControl("/InGame/LaunchBar/ButtonStack");
    ContextPtr:BuildInstanceForControl("LaunchBarItem", instance, buttonStack);
    instance.LaunchItemButton:RegisterCallback(Mouse.eLClick, ToggleDealPopup);
    -- 调整 backing 尺寸
    backing:SetSizeX(buttonStack:GetSizeX() + 116);
    LuaEvents.LaunchBar_Resize(buttonStack:GetSizeX());
end
```

## 模式 2: 弹窗作为非模态覆盖层

使用 `UIManager:QueuePopup` 配合 `RenderAtCurrentParent` 参数，使弹窗在 Screens 层级渲染而非完全盖住所有 UI：

```lua
function Open()
    if not UIManager:IsInPopupQueue(ContextPtr) then
        local kParameters = {};
        kParameters.RenderAtCurrentParent = true;
        kParameters.InputAtCurrentParent = true;
        kParameters.AlwaysVisibleInQueue = true;
        UIManager:QueuePopup(ContextPtr, PopupPriority.Low, kParameters);
        ContextPtr:ChangeParent(ContextPtr:LookUpControl("/InGame/Screens"));
    end
end
```

关闭时调用 `UIManager:DequeuePopup(ContextPtr)`。

## 模式 3: Tab 切换系统

Tab 按钮用 InstanceManager 创建，用 TabSupport 父类管理选择状态：

```lua
m_Tabs = CreateTabs(Controls.TabContainer, 42, 34, color);

local tabInstance = m_TabButtonIM:GetInstance();
tabInstance.Button:SetText(Locale.Lookup(text));
tabInstance.Button:RegisterCallback(Mouse.eMouseEnter, function() UI.PlaySound("Main_Menu_Mouse_Over"); end);
m_Tabs.AddTab(tabInstance.Button, callbackFunc);
```

每个 Tab 对应的内容面板通过 `LuaEvents.QD_PopupShowTab` 通知切换，各面板监听后调用 `ContextPtr:ChangeParent()` 将自身挂到 `TabContentContainer`。

## 模式 4: AI 交易自动化 — 抓取流程

`OfferAutomator` 是核心自动化引擎，通过 DiplomacyManager 模拟完整的交易会话：

```
OnStartAIOfferFetch(playerId, aiList, myItems)
  -> 遍历每个 AI:
    1. DiplomacyManager.RequestSession(playerId, aiId, "MAKE_DEAL")
    2. 等待 OnDiplomacyStatement 响应
    3. DealManager.GetWorkingDeal() 获取工作交易
    4. 添加我方物品到 deal
    5. DealManager.SendWorkingDeal(INSPECT) 询价
    6. 等待 AI 响应
    7. 如果双方都有物品且 AI 接受 -> 记录 offer，继续下一个 AI
    8. 如果一方没有物品 -> 发送 EQUALIZE 请求 AI 平衡报价
    9. 如果没有可交易物品 -> 尝试 AI 所有黄金
```

关键 API:
```lua
DiplomacyManager.RequestSession(playerId, otherId, "MAKE_DEAL");
DiplomacyManager.FindOpenSessionID(playerId, otherId);
DiplomacyManager.CloseSession(sessionId);

local deal = DealManager.GetWorkingDeal(DealDirection.OUTGOING, playerId, otherId);
DealManager.SendWorkingDeal(DealProposalAction.INSPECT, playerId, otherId);
DealManager.SendWorkingDeal(DealProposalAction.EQUALIZE, playerId, otherId);
DealManager.SendWorkingDeal(DealProposalAction.ACCEPTED, playerId, otherId);
DealManager.CopyIncomingToOutgoingWorkingDeal(playerId, otherId);
DealManager.AreWorkingDealsEqual(playerId, otherId);
```

## 模式 5: AI 外交响应处理

监听 `Events.DiplomacyStatement`，匹配 `RespondingToDealAction` 判断响应类型：

```lua
function OnDiplomacyStatement(fromPlayer, toPlayer, kVariants)
    -- kVariants.RespondingToDealAction: 我方上次发出的操作
    -- kVariants.DealAction: AI 对这个操作的响应 (ACCEPTED/REJECTED/EQUALIZE_FAILED)
    -- kVariants.SessionID
    -- kVariants.StatementType -> DiplomacyManager.GetKeyName() -> "MAKE_DEAL"
    -- kVariants.StatementSubType -> "NONE" / "HUMAN_ACCEPT_DEAL" 等
end
```

注意：AI 对 `ACCEPTED` 操作会响应两次（`NONE` + `HUMAN_ACCEPT_DEAL`），第二次响应后才算完成。

## 模式 6: 黄金交换协议

黄金有两种形式:
- `OneTimeGold` — 一次性金币 (duration=0)
- `MultiTurnGold` — 回合金 (duration=30)

转换比率 `GOLD_RATIO = 21`（21 一次性黄金 = 1 回合金）。

AI 黄金交换通过二分探测法：依次用 [1000, 100, 10, 1] 的步长探测 AI 能接受的最大回合金/一次性金数量。

```lua
-- 添加/修改黄金 deal item
function UpdatePlayerGoldInDeal(deal, goldPlayerId, oneTimeGoldDelta, multiTurnGoldDelta)
    local dealItems = deal:FindItemsByType(DealItemTypes.GOLD, DealItemSubTypes.NONE, goldPlayerId);
    -- 区分 duration==0 (one-time) 和 duration>0 (multi-turn)
    -- 用 deal:AddItemOfType() 添加新项
    -- 用 deal:RemoveItemByID() 移除
end
```

## 模式 7: 异步任务队列

因为每次 AI 外交请求需要异步等待响应，多个请求需排队：

```lua
function OnStartAIOfferFetch(...)
    if HasJobRunning() then
        m_PendingJob = { Type = JOB_TYPE.FETCH, Args = taskArgs };
        return;
    end
    -- 开始执行...
end

function EndAIOfferFetch()
    m_IsFetching = false;
    if not ProceedPendingJob() then
        -- 通知 UI 完成
        LuaEvents.QD_EndAIOfferFetch(m_Offers);
    end
end
```

## 模式 8: 交易物品管理

Offer 格式:
```lua
{
    PlayerId = aiPlayerId,
    OneTimeGold = 100,
    MultiTurnGold = 3,
    Total = 730,  -- OneTimeGold + MultiTurnGold * 30
    OfferedItems = { item1, item2, ... },
    HasNonGoldItem = false,
    Equalized = true,
}
```

DealItem 格式:
```lua
{
    Id = resourceIndex,
    Type = DealItemTypes.RESOURCES,
    Amount = 5,
    MaxAmount = 10,
    Duration = 0,  -- 0=一次性, 30=30回合
}
```

物品类型: RESOURCES, GOLD, FAVOR, GREATWORK, AGREEMENTS（开放边界等）。

## 模式 9: 通知系统

检查新出现的可交易物品，发送游戏内通知：

```lua
local QD_NOTIFICATION_HASH = GameInfo.Types["NOTIFICATION_QUICK_DEAL"].Hash;

-- 发送通知
NotificationManager.SendNotification(playerId, QD_NOTIFICATION_HASH,
    Locale.Lookup("LOC_QD_NEW_DEALS_AVAILABLE"), tooltipStr);

-- 监听通知点击
Events.NotificationActivated.Add(OnProcessNotification);
function OnProcessNotification(playerId, notificationId, activatedByUser)
    local notification = NotificationManager.Find(playerId, notificationId);
    if notification and notification:GetType() == QD_NOTIFICATION_HASH then
        Open();
    end
end
```

## 模式 10: 跨上下文共享 (ExposedMembers)

CacheManager 通过 `ExposedMembers` 在 UI 和 Gameplay 脚本间共享：

```lua
-- gameplay/qd_cachemanager.lua
CacheManager = {};
CacheManager.GetCachedDeals = function(isSell) ... end;
CacheManager.SetCachedDeals = function(deals, isSell) ... end;

ExposedMembers.QD = ExposedMembers.QD or {};
ExposedMembers.QD.CacheManager = CacheManager;

-- ui 脚本中访问
local CacheManager = ExposedMembers.QD.CacheManager;
```

缓存使用 `Players[player]:GetProperty(key)` / `SetProperty(key, value)`，数据在存档间持久化。

## 模式 11: 数据库驱动的物品分类

奢侈/战略资源的交易规则来自数据库:
- 奢侈品: 仅当己方有额外副本且对方没有时才能卖 (duration=30)
- 战略资源 (XP1): 固定 1 份 (duration=30)
- 战略资源 (XP2): 可以卖到阈值以上 (duration=0)
- 外交支持: 最多卖 20 点 (duration=0)
- 巨作/协议: 一次一份 (duration=30 for 开放边界)

资源需求检测:
```lua
function ResourceAmountNeeded(playerId, resourceIndex, limitToCap)
    -- XP2 战略资源可售出至储备上限
    -- 其他资源仅当对方没有时才需要
end
```

## 关键 Lua 事件

| 事件 | 说明 |
|------|------|
| `LuaEvents.QD_ToggleDealPopup` | 切换弹窗显隐 |
| `LuaEvents.QD_PopupShowTab(tabType)` | Tab 切换通知 |
| `LuaEvents.QD_StartAIOfferFetch` | 开始 AI 报价获取 |
| `LuaEvents.QD_EndAIOfferFetch(offers)` | AI 报价获取完成 |
| `LuaEvents.QD_StartAIOfferAccept` | 开始接受 AI 报价 |
| `LuaEvents.QD_EndAIOfferAccept(items)` | 已接受报价中的物品 |
| `LuaEvents.QD_StartAIGoldExchange` | 开始黄金兑换探测 |
| `LuaEvents.QD_EndAIGoldExchange(offers)` | 黄金兑换探测完成 |
| `LuaEvents.QD_StartMultiTurnGoldUpdate` | 回合金增量更新 |
| `LuaEvents.QD_EndMultiTurnGoldUpdate(offers, instance)` | 回合金更新完成 |
| `LuaEvents.QD_RequestDealScreen(playerId)` | 打开对某玩家的交易界面 |
| `LuaEvents.QD_CloseDealPopupSilently` | 静默关闭弹窗 |
| `LuaEvents.QDDealPopup_Opened` | 弹窗已打开 |
| `LuaEvents.QDDealPopup_Closed` | 弹窗已关闭 |
| `LuaEvents.QDDealPopup_CloseRequest` | 请求关闭弹窗 |
| `LuaEvents.QD_OnSurpriseSession(sessionId)` | 意外外交会话（被宣战等） |

## 重要细节

- 多人游戏下整个功能禁用
- `Events.DiplomacyStatement` 是全局事件 — 需要检查 `toPlayer` 和 `RespondingToDealAction` 判定归属
- `DealManager.ClearWorkingDeal()` 在开始新探测前调用，避免残留
- 玩家关闭弹窗时如果还有等待中的 AI 响应，需要先设置 `m_PopupCloseRequested = true` 标记，等响应回来后真正关闭
- EQUALIZE 请求可能没有响应，需启动 RequestTimer 动画做超时回退处理
- `EQUALIZE_FAILED` 不会作为正常外交响应到来，通过 timer 回调手动构造
- `DealProposalAction.ACCEPTED` 被 AI 接受后会关闭外交会话

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `ui/qd_launchbutton.xml` | LaunchBar 按钮注入：`LaunchBarItem` + `LaunchBarPinInstance` Instance |
| `ui/qd_dealpopup.xml` | 主交易弹窗布局：QDPopupContainer + Tab 容器 + TabButtonInstance |
| `ui/qd_instances.xml` | 核心 Instance 定义：IconOnly / IconAndText / AISaleOffer / AIPurchaseOfferRow / AIExchangeOfferRow |
| `ui/qd_popuptab_sale.xml` | Sale Tab 面板布局 |
| `ui/qd_popuptab_purchase.xml` | Purchase Tab 面板布局 |
| `ui/qd_popuptab_exchange.xml` | Exchange Tab 面板布局 |
| `data/qd_notifications.xml` | 通知类型注册（NOTIFICATION_QUICK_DEAL） |

### qd_launchbutton.xml 控件 ID 对照

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `LaunchItemButton` | Button | — | LaunchBar 入口按钮（49x49） |
| `LaunchItemIcon` | Image | — | 按钮图标（36x36） |
| `AlertIndicator` | Label | — | 新交易可用提示（[ICON_New]） |

**Instance 模板：**

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `LaunchBarItem` | LaunchBar 注入按钮 | `LaunchItemButton`(Button, 49x49), `LaunchItemIcon`(Image, 36x36), `AlertIndicator`(Label) |
| `LaunchBarPinInstance` | Pin 标记（7x7） | `Pin`(Image, "LaunchBar_TrackPip") |

### qd_dealpopup.xml 控件 ID 对照

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `Vignette` | Container | — | 全屏暗幕 |
| `QDPopupContainer` | Container | `Controls.QDPopupContainer` | 弹窗根容器（1280x768） |
| `TabContentContainer` | Container | `Controls.TabContentContainer` | Tab 内容切换容器 |
| `TabContainer` | Container | `Controls.TabContainer` | Tab 按钮容器 |
| `NotificationToggle` | CheckBox | `Controls.NotificationToggle` | 通知开关 |

**Instance 模板：**

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `TabButtonInstance` | Tab 按钮 | `Button`(GridButton, 170x34, "TabButton"), `SelectButton`(GridButton, "TabButtonSelected") |

### qd_instances.xml 核心 Instance 对照

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `IconOnly` | 纯图标条目（56x56） | `SelectButton`(GridButton), `Icon`(Image, 64x64), `AmountText`(Label), `UnacceptableIcon`(Image, Alert18), `RemoveButton`(Button), `StopAskingButton`(Button) |
| `IconAndText` | 图标+文字条目（200x56） | `SelectButton`(GridButton), `Icon`(Image, 44x44), `IconText`(Label), `ValueText`(ScrollTextField), `AmountText`(Label) |
| `AISaleOfferInstance` | AI 出售报价行 | `OfferContainer`, `LeaderTargetIcon`, `GoldBalance`(Label), `OneTimeGold`(IconOnly), `MultiTurnGold`(IconAndText), `OfferedItemsStack`, `AcceptDeal`(GridButton) |
| `AIPurchaseOfferRowInstance` | AI 购买报价行 | `OfferRowContainer`(1200xauto), 同上结构但布局不同 |
| `AIExchangeOfferRowInstance` | AI 兑换报价行 | `OfferRowContainer`, AI/Player 双方向黄金列 + `GoldRatio`(Label) |

### 可复用模板：弹窗 + Tab 结构

```xml
<Context>
    <Container ID="Vignette" Style="FullScreenVignetteConsumer" />
    <Container ID="QDPopupContainer" Anchor="C,C" Size="1280,768">
        <Container Style="ModalScreenWide"/>
        <Grid Style="DiplomacyInfoWindowGrid" Size="parent,parent-80" Offset="0,80">
            <Container ID="TabContentContainer" Size="parent,parent-33" Offset="0,12"/>
        </Grid>
        <Container Anchor="C,T" Offset="0,48" Size="auto,61">
            <Image Anchor="C,T" Size="auto,27" Texture="Controls_TabLedge2_Fill" StretchMode="Tile"/>
            <Grid Anchor="C,T" Size="auto,61" Texture="Controls_TabLedge2">
                <Container ID="TabContainer" Anchor="C,T" Offset="0,13" Size="auto,34"/>
            </Grid>
        </Container>
    </Container>
    <Instance Name="TabButtonInstance">
        <GridButton ID="Button" Size="170,34" Style="TabButton" FontSize="14" TextOffset="0,2">
            <GridButton ID="SelectButton" Size="parent,parent" Style="TabButtonSelected"
                        ConsumeMouseButton="0" ConsumeMouseOver="1" Hidden="1"/>
        </GridButton>
    </Instance>
</Context>
```
