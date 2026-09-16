# 贷款金融系统（来源：工坊 3031683464 Financial Tycoons）

## 做什么
为玩家提供可操作的贷款/金融界面。支持多笔贷款的:
- 借款（选择利率和期限）
- 提前还款（按实际时长计息，利息更低）
- 逾期扣款（现金不够时扣回合金）
- 免费贷款（其他玩家获得双倍收入）
- 时代推进时增加贷款额度上限
- 数据持久化（Game Property 存储，支持存档读档）

## Lua 端

### 架构：两个 Lua 上下文
```
ft_gameplay.lua  → 后端（数据存储、修改金币）
ft_ui.lua        → 前端（UI界面、贷款管理）
交互方式：ExposedMembers.FT.<函数名>
```

### ft_gameplay.lua — 后端数据层

#### 数据持久化
```lua
local FT_PROPERTY_ID = "FINACIAL_TYCOONS"

function SaveFTData(data)
    Game:SetProperty(FT_PROPERTY_ID, data)   -- 写入全局属性（随存档保存）
end

function FetchFTData()
    return Game:GetProperty(FT_PROPERTY_ID)  -- 从存档读取
end
```
数据格式：
```lua
{
    LoansData = {                    -- 所有贷款列表
        { Arrears=0, Amount=100, TurnsRemain=5, RateIndex=1 },
        ...
    },
    FreeLoanedBalance = 88          -- 已借免费贷款总额
}
```

#### 修改金币
```lua
function ChangeGoldBalance(iPlayerID, iAmount)
    local pPlayer = Players[iPlayerID]
    if pPlayer ~= nil then
        pPlayer:GetTreasury():ChangeGoldBalance(iAmount)
    end
end
```

#### ExposedMembers 桥接
```lua
if ExposedMembers.FT == nil then
    ExposedMembers.FT = {}
end
ExposedMembers.FT.SaveFTData = SaveFTData
ExposedMembers.FT.FetchFTData = FetchFTData
ExposedMembers.FT.FetchSimulateData = FetchSimulateData   -- 调试用
ExposedMembers.FT.ChangeGoldBalance = ChangeGoldBalance
```
这是 Civilization VI Mod 中 **Gameplay Script 与 UI Script 通信的标准方式**。

### ft_ui.lua — 前端贷款界面

#### 利率表
```lua
local m_kRateTable = {
    {Turns=10, Rate=0.05},    -- 10回合 5%利息
    {Turns=20, Rate=0.15},
    {Turns=30, Rate=0.3},
    {Turns=50, Rate=0.5},
    {Turns=100, Rate=1},      -- 100回合 100%利息
}
```

#### 贷款额度（按时代）
```lua
local m_kLoanQuotas = {
    [1]=1000, [2]=1200, [3]=1500, [4]=2000,    -- 远古→文艺复兴
    [5]=2600, [6]=3200, [7]=4000, [8]=5000      -- 工业→信息
}
local m_kFreeLoanQuotas = {
    [1]=1000, [2]=1500, [3]=2000, [4]=2500,
    [5]=3000, [6]=3500, [7]=4000, [8]=5000
}
```

#### 利息计算
```lua
function CaculateInterest(iAmount, iTurnsPast)
    -- 根据已借时长找对应利率档位
    -- 例：已借35回合 → 按50回合档计息
    local iRate = m_kRateTable[#m_kRateTable].Rate  -- 默认最高档
    for _,entry in ipairs(m_kRateTable) do
        if iTurnsPast <= entry.Turns then
            iRate = entry.Rate
            break
        end
    end
    return math.floor(iAmount * iRate)
end
```

#### Account（账户管理）
```lua
Account = {
    UpdateUpperLimits = function(newEra)     -- 时代推进时更新贷款上限
    ChangeGoldBalance = function(iNumber)    -- 改金币并刷新UI
    GetGoldBalance = function()              -- 获取金币余额
    GetGoldPerTurn = function()           -- 获取回合金（产出-维护费）
    CanLoanMore = function()              -- 是否还能借更多
    AvailableLoanedAmount = function()    -- 剩余可借金额
}
Account.Loan = function(iNumber)           -- 借款（增加已借额度+给钱）
Account.Pay = function(iNumber, iInterest) -- 还款（减少已借额度-扣钱+分给AI）
Account.PayOverdue = function(iNumber)     -- 逾期还款（只扣钱不分给AI）
Account.FreeLoan = function(iNumber)       -- 免费贷款（自己得钱，AI各得双倍）
```

#### 其他玩家分享
```lua
OtherPlayers = {
    Share = function(iNumber)
        -- 均分给所有存活大文明玩家
        local counts = PlayerManager.GetAliveMajorsCount() - 1
        if counts > 0 then OtherPlayers.GainEach(iNumber / counts) end
    end,
    GainEach = function(iNumber)
        -- 每个其他玩家获得 iNumber 金币
        for _,pPlayer in ipairs(PlayerManager.GetAliveMajors()) do
            if pPlayer:GetID() ~= m_iCurrentPlayerID then
                ExposedMembers.FT.ChangeGoldBalance(pPlayer:GetID(), iNumber)
            end
        end
    end
}
```

#### LoanItem（单笔贷款对象）

实现了完整的面向对象贷款管理：

```lua
LoanItem = {}
function LoanItem:New()       -- 构造：创建UI实例+绑定事件
function LoanItem:Init()      -- 初始化UI控件（滑块、按钮、下拉菜单）
function LoanItem:UpdateSlider()  -- 滑块拖动时更新显示金额和利息
function LoanItem:RefreshPayableState(spareGold) -- 检查是否够钱还款
function LoanItem:OnNewTurn() -- 每回合：倒计时→到期自动还款→不够钱进入逾期
function LoanItem:Loan()      -- 执行借款
function LoanItem:Pay()       -- 执行还款（含提前还款）
function LoanItem:PayOverdue()-- 逾期还款逻辑（先扣现金再扣回合金）
function LoanItem:GetCurrentInterest() -- 提前还款利息（按实际时长）
function LoanItem:GetFullInterest()    -- 到期利息（全额）
function LoanItem:Serialize()   -- 序列化为可存储的table
function LoanItem:Deserialize(tab) -- 从存储数据恢复
```

逾期还款逻辑：
```lua
function LoanItem:PayOverdue()
    if self.Arrears > 0 then
        local iGold = Account.GetGoldBalance()
        if iGold >= self.Arrears then
            Account.PayOverdue(self.Arrears)
            self.Arrears = 0
        else
            Account.PayOverdue(iGold)           -- 扣光现金
            self.Arrears = self.Arrears - iGold -- 剩余欠款
            -- 下回合继续扣回合金
        end
    end
    if self.Arrears > 0 then
        local iGoldPerTurn = Account.GetGoldPerTurn()
        Account.PayOverdue(iGoldPerTurn)
        self.Arrears = self.Arrears - iGoldPerTurn
        self.ui.ArrearLabel:SetHide(false) -- 显示欠款标签
    end
end
```

#### 数据流程
```
存档加载时：
  InitHandler → FetchDataFromGameplay()
    → ExposedMembers.FT.FetchFTData() 获取存档数据
    → 对每条 LoanData 创建 LoanItem 并 Deserialize

每回合结束时：
  OnLocalPlayerTurnChanged → UpdateLoanedTurns()
    → 每个 LoanItem:OnNewTurn()（倒计时/到期/逾期处理）

保存时：
  OnSaveComplete → SaveDataToGameplay()
    → 收集所有 LoanItem:Serialize()
    → ExposedMembers.FT.SaveFTData(data) 保存到 Property

时代变化时：
  OnPlayerEraChanged → m_iFreeLoanedBalance=0 → Account.UpdateUpperLimits()
```

#### 事件监听
```lua
Events.LoadGameViewStateDone.Add(OnLoadGameViewStateDone)
Events.LocalPlayerTurnEnd.Add(OnLocalPlayerTurnChanged)
Events.PlayerEraChanged.Add(OnPlayerEraChanged)
Events.SaveComplete.Add(OnSaveComplete)

-- 其他弹窗出现时自动隐藏贷款窗口
LuaEvents.DiplomacyActionView_HideIngameUI.Add(HideFTWindow)
LuaEvents.EndGameMenu_Shown.Add(HideFTWindow)
LuaEvents.FullscreenMap_Shown.Add(HideFTWindow)
-- 等等...
```

#### UI 入口：LaunchBar 按钮
```lua
function SetupLaunchBarButton()
    -- 在游戏顶部 LaunchBar 中插入一个按钮
    local ctrl = ContextPtr:LookUpControl("/InGame/LaunchBar/ButtonStack")
    EntryButtonInstance = m_LaunchItemInstanceManager:GetInstance(ctrl)
    EntryButtonInstance.LaunchItemButton:RegisterCallback(Mouse.eLClick, ShowFTWindow)
end
```

## SQL 配合
此系统纯 Lua 实现，无 SQL。

## XML 配合

### ft_text.xml
中英双语文本：包含窗口标题、贷款标签、利率提示、逾期提示等。

### ft_ui.xml
完整的 UI 布局定义：
- `MainContainer` — 贷款主窗口（780x400）
- `UsuriousLoan` Tab — 高利贷（带利率选择滑块、还款按钮、贷款堆叠列表）
- `FreeLoan` Tab — 免费贷款（4个预设金额按钮 100/500/1000/5000）
- `VAMTab` — 对赌协议（预留，未实现）
- `LoanInstance` — 单笔贷款的 UI 实例（滑块+利率下拉+金额显示+借款/还款按钮）
- `EntryButtonInstance` — LaunchBar 入口按钮

## ExposedMembers 通信模式

这是模组中 Gameplay Script 和 UI Script 通信的关键技术：

```
┌──────────────────────┐     ExposedMembers.FT     ┌──────────────────┐
│   ft_gameplay.lua    │ ◄────────────────────────► │    ft_ui.lua     │
│   (Gameplay Script)  │                            │   (UI Script)    │
├──────────────────────┤                            ├──────────────────┤
│ • SaveFTData()       │                            │ • Account        │
│ • FetchFTData()      │                            │ • LoanItem       │
│ • ChangeGoldBalance()│                            │ • UI Controls    │
└──────────────────────┘                            └──────────────────┘
```

Gameplay Script 在非沙箱环境运行，可以修改游戏数据（金币等）。
UI Script 在沙箱环境运行，只能操作界面。
通过 ExposedMembers 作为桥接，UI 可以调用 Gameplay 的函数。
