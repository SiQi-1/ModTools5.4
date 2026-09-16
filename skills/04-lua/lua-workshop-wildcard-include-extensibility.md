# 通配符 include 扩展机制（来源：工坊 2066679333）

## 做什么
在主 Lua 文件末尾使用 `include("BaseFileName_", true)` 的通配符模式，让其他 Mod 可以通过创建 `BaseFileName_<Something>.lua` 文件来覆盖/扩展主文件的函数和变量，无需修改主文件本身。

## 如何挂载到官方UI

这是一种 Lua 代码架构模式，不涉及 UI 挂载。

## 关键 Lua 代码

### 核心语句

```lua
-- 在文件最末尾（Initialize() 调用之后）
include("DiplomacyDealView_", true);
```

第二个参数 `true` 表示"允许找不到文件时不报错"（即通配符匹配 zero 个文件也没关系）。

### 工作原理

`include("DiplomacyDealView_", true)` 会加载**所有**以 `DiplomacyDealView_` 开头的 Lua 文件。加载顺序不确定（由游戏引擎决定），但所有同名函数定义会相互覆盖——最后加载的文件中的函数定义生效。

### 扩展文件的写法

```lua
-- DiplomacyDealView_MyDLC.lua
-- 注意：不要 include("DiplomacyDealView")——基文件已经在前面加载完毕

-- 覆盖基文件的函数
function PopulateAvailableGold(player, iconList)
    -- 自定义逻辑……
    -- 可以调用 original_PopulateAvailableGold() 如果你提前保存了引用
end

-- 添加新函数
function MyCustomFunction()
    -- ...
end

-- 注册额外的回调
function OnExtraCallback()
    -- ...
end
```

### 基文件中的配合设计

为了让扩展文件能够安全覆盖，基文件应使用**全局函数**（非 local）：

```lua
-- 正确（可被扩展文件覆盖）
function PopulateAvailableGold(player, iconList)
    -- ...
end

-- 错误（local 函数无法被外部覆盖）
local function PopulateAvailableGold(player, iconList)
    -- ...
end
```

## 扩展文件可以覆盖的内容

| 覆盖目标 | 方式 |
|---------|------|
| 填充函数 | 重定义 `PopulateAvailableGold()` / `PopulateDealResources()` 等 |
| 点击回调 | 重定义 `OnClickAvailableResource()` 等 |
| 全局变量 | 直接修改 `ms_DefaultOneTimeGoldAmount` 等非 local 变量 |
| 初始化逻辑 | 在扩展文件中直接执行代码（文件加载时即执行） |

## DLC 特定扩展的实际案例

该 Mod 本身使用了这个模式来支持不同 DLC：

```
DiplomacyDealView.lua                          -- 主文件
DiplomacyDealView_Expansion2.lua               -- R&F / GS 扩展
DiplomacyDealView_KublaiKhanVietnam_MODE.lua   -- 忽必烈/越南模式
DiplomacyDealView_KublaiKhanVietnam_MODE_Expansion2.lua  -- DLC + XP2 组合
```

这些扩展文件覆盖主文件中的函数来添加 DLC 特有的交易物品（如外交支持、同盟类型等）。

### 检测 DLC 的存在

扩展文件通过检测 GameInfo 表是否存在来判断 DLC：

```lua
-- Expansion2 扩展文件示例
if GameInfo.Eras_XP2 ~= nil then
    -- 添加外交支持 (Favor) 作为可交易物品
    -- 覆盖 PopulateAvailableGold 来添加外交支持条目
end
```

## 初始化注意事项

主文件的 `Initialize()` 在文件末尾被调用（`Initialize();` 之后才是 `include("..._", true)`），因此扩展文件加载时，主文件的 `Initialize()` 已经执行完毕。扩展文件可以在自己的顶层代码中注册额外的事件或回调：

```lua
-- 在扩展文件中直接注册额外事件（文件加载时执行）
Events.GovernmentPolicyChanged.Add(MyPolicyChangeHandler);
LuaEvents.MyCustomEvent.Add(MyHandler);
```

## 应用场景

- 需要支持多个 DLC 的 Mod（不同 DLC 有不同的可交易物品/机制）
- 允许其他 Mod 扩展你的 UI（提供开放 API）
- 按功能模块拆分大型 UI 文件（Populate 逻辑 / 事件处理 / 动画等）

## XML 配合

### 涉及的关键 XML 文件

| 文件 | 路径 | 用途 |
|------|------|------|
| `DiplomacyDealView.xml` | Mod 根目录（2066679333） | 基文件 XML，定义所有 Instance 和控件 ID，扩展文件中的 Lua 代码通过 Controls/Instance 引用这些 ID |

### 核心控件 ID 对照表（扩展文件可能覆盖/引用的控件）

| 控件 ID | 类型 | 所在区域 | 用途 |
|---------|------|---------|------|
| **交易面板框架** | | | |
| `TradePanel` | Container | 全局 | 交易面板总容器 |
| `TradePanelFade` / `TradePanelSlide` | AlphaAnim / SlideAnim | 全局 | 面板入场动画 |
| **对话/按钮区** | | | |
| `AcceptDeal` | GridButton | DealOptionsStack | 接受交易 |
| `RefuseDeal` | GridButton | DealOptionsStack | 拒绝交易 |
| `EqualizeDeal` | GridButton | DealOptionsStack | 均衡交易（What Would It Take） |
| `DemandDeal` | GridButton | DealOptionsStack | 要求交易 |
| `LeaderDialog` | Label | LeaderDialogStack | 领袖对话文本 |
| `LeaderEffect` | Label | LeaderDialogStack | 领袖效果文本 |
| **我方/对方物品区** | | | |
| `MyOfferScroll` / `MyOfferStack` | ScrollPanel / Stack | MyOffer | 我方提议物品列表 |
| `TheirOfferScroll` / `TheirOfferStack` | ScrollPanel / Stack | TheirOffer | 对方提议物品列表 |
| `MyInventoryScroll` / `MyInventoryStack` | ScrollPanel / Stack | MyInventory | 我方可交易物品库存 |
| `TheirInventoryScroll` / `TheirInventoryStack` | ScrollPanel / Stack | TheirInventory | 对方可交易物品库存 |
| **分类标题** | | | |
| `OneTimeDealsHeader` / `For30TurnsDealsHeader` / `AgreementDealsHeader` / `CityDealsHeader` / `GreatWorksDealsHeader` / `CaptivesDealsHeader` | Grid | MyOffers / TheirOffers | 各类交易品分类标题 |
| `OneTimeDealsStack` / `For30TurnsDealsStack` / `AgreementDealsStack` / `CityDealsStack` / `GreatWorksDealsStack` / `CaptivesDealsStack` | Stack | MyOffers / TheirOffers | 各类交易品列表 |
| **弹窗编辑** | | | |
| `ValueEditPopupBackground` | Box | 全局 | 数值编辑弹窗遮罩 |
| `ValueEditPopup` | Grid | 全局 | 数值编辑弹窗 |
| `ValueEditIconGrid` / `ValueEditIcon` / `ValueEditAmountText` | GridButton / Image / Label | ValueEditPopup | 编辑弹窗内物品显示 |
| `ValueAmountEditBox` | EditBox | ValueEditPopup | 数值编辑输入框 |
| `ValueEditButton` | GridButton | ValueEditPopup | 确认/返回按钮 |
| **Instances（扩展文件可能创建/填充的）** | | | |
| `IconOnly` | Instance | - | 纯图标交易物品 |
| `IconAndText` | Instance | - | 图标+文本交易物品 |
| `SmallIconAndText` | Instance | - | 小号图标+文本 |
| `CityIconAndDetails` | Instance | - | 城市图标+详情展开 |
| `LeftRightList` | Instance | - | 横向列表容器 |
| `TopDownList` | Instance | - | 纵向列表容器 |
| `HistoryList` | Instance | - | 交易历史列表 |
| `MinimizedSection` | Instance | - | 折叠分类区 |
| `MyOffers` | Instance | - | 我方提议总容器 |
| `TheirOffers` | Instance | - | 对方提议总容器 |
| `AgreementOptionInstance` | Instance | - | 协议选项条目 |

### 可复用 XML 模板（支持通配符 include 扩展的基文件框架）

```xml
<Context Style="FontNormal16" ColorSet="BodyTextCool" FontStyle="Shadow" Size="parent,parent" ConsumeMouse="1">
    <!-- 缓存容器（隐藏，仅用于 InstanceManager 创建实例） -->
    <Container ID="IconCacheContainer" Hidden="1"/>

    <!-- 全屏背景 -->
    <Container Size="parent,parent"/>

    <!-- === 交易物品 Instance（扩展文件可覆盖其填充逻辑） === -->
    <Instance Name="ItemInstance">
        <GridButton ID="SelectButton" Style="ButtonDraggableGrid" Size="56,56" Anchor="L,T">
            <Image ID="Icon" StretchMode="None" Size="64,64" Anchor="C,C"/>
            <Label ID="AmountText" Style="FontNormalBold16" Anchor="R,B" Offset="-5,-9"/>
            <Button ID="RemoveButton" Anchor="L,B" Offset="-10,-10" Texture="Controls_RemoveDealSmall" Size="16,16" Hidden="1"/>
        </GridButton>
    </Instance>

    <!-- === 列表容器 Instance === -->
    <Instance Name="ListSection">
        <Stack ID="List" Size="parent, 0">
            <Grid Style="ColumnHeader" ID="Title" Size="parent-24,26" Anchor="C,T">
                <Label ID="TitleText" Anchor="C,C" Style="HeaderSmallCaps"/>
            </Grid>
            <Stack ID="ListStack" StackGrowth="Right" Anchor="L,T" WrapWidth="parent"/>
        </Stack>
    </Instance>

    <!-- === 主面板（扩展文件可重定义其填充函数） === -->
    <Container ID="MainPanel" Size="parent,parent">
        <AlphaAnim ID="PanelFade" AlphaBegin="0" AlphaEnd="1" Speed="2" Cycle="Once">
            <SlideAnim ID="PanelSlide" Start="-10,0" End="0,0" Speed="2" Cycle="Once">
                <Image Size="1000,parent" Anchor="L,T" Offset="20,0">
                    <!-- 内容区 -->
                    <Stack ID="ContentStack" StackGrowth="Down" Offset="0,10" Anchor="C,T">
                        <!-- 按钮区 -->
                        <Grid Style="SubContainer4" Size="parent-14,95" Anchor="C,T">
                            <Stack ID="ButtonStack" StackGrowth="Right" Anchor="C,C" Padding="4" WrapWidth="500">
                                <GridButton ID="ConfirmButton" Style="ButtonConfirm" Size="200,41"/>
                                <GridButton ID="CancelButton" Style="ButtonLightWeight" Size="200,32"/>
                            </Stack>
                        </Grid>

                        <!-- 表头 -->
                        <Grid Anchor="C,T" Size="parent, 38" Style="DiplomacyTitleBarGrid">
                            <Label ID="LeftHeader" Anchor="C,C" String="LOC_LEFT_TITLE" Style="DiplomacyIntelHeader"/>
                            <Label ID="RightHeader" Anchor="C,C" String="LOC_RIGHT_TITLE" Style="DiplomacyIntelHeader"/>
                        </Grid>

                        <!-- 左右物品区 -->
                        <Container ID="ItemsContainer" Size="parent,parent-160" Anchor="C,T">
                            <Container ID="LeftPanel" Size="249,parent" Anchor="L,T">
                                <ScrollPanel ID="LeftScroll" Size="parent,parent" Vertical="1" AutoScollbar="1">
                                    <Stack ID="LeftStack" StackGrowth="Right" WrapWidth="234"/>
                                </ScrollPanel>
                            </Container>
                            <Container ID="RightPanel" Size="249,parent" Anchor="R,T">
                                <ScrollPanel ID="RightScroll" Size="parent,parent" Vertical="1" AutoScollbar="1">
                                    <Stack ID="RightStack" StackGrowth="Right" WrapWidth="234"/>
                                </ScrollPanel>
                            </Container>
                        </Container>
                    </Stack>
                </Image>
            </SlideAnim>
        </AlphaAnim>
    </Container>
</Context>
```

### 扩展文件如何使用基文件的 XML 控件

```lua
-- 扩展文件（如 DiplomacyDealView_Expansion2.lua）中的函数覆盖
-- 可以自由访问基 XML 中定义的所有控件 ID

-- 覆盖基文件的填充函数，添加 DLC 特有物品
function PopulateAvailableItems(playerID, itemsStack)
    -- 先调用基文件逻辑（如果缓存了引用）
    --  或直接用 Controls / InstanceManager 在基文件的 Stack 上创建实例

    -- 添加 DLC 特有物品
    if GameInfo.Items_XP2 ~= nil then
        local instance = pItemIM:GetInstance()
        instance.Icon:SetIcon("ICON_DLC_ITEM")
        itemsStack:AddChild(instance.Top)
    end
end
```
