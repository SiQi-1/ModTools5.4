# 扩展已有 UI 屏幕（来源：工坊 1360462633 Extended Diplomacy Ribbon）

## 做什么
在不替换原版 UI 文件的前提下，扩展已有游戏界面的功能 —— 给领袖头像增加新指示器、扩展 Tooltip 内容、添加鼠标中键交互等。

## 挂载方式

### 方式一：`<LuaContext>` XML 注入（最关键的一步）
在原有 XML Context 文件中，添加一行 `<LuaContext>` 来劫持某个已存在的 Lua 子上下文，使其加载你的 Lua 文件：

```xml
<!-- 原版 DiplomacyActionView.xml 中，EDR 仅做了这一处修改 -->
<LuaContext ID="DiplomacyRibbon" FileName="DiplomacyRibbon" Offset="175,0"/>
```

原理：原版 `DiplomacyActionView.xml` 内部有一个 `LuaContext` 控件，原本加载 `DiplomacyRibbon.lua`。EDR 通过 `ImportFiles` 覆盖了这个 XML，把 `FileName` 指向自己的 `ExtendedDiplomacyRibbon.lua`（导入时已重命名为 `DiplomacyRibbon`）。

**注意**：你需要在 ModBuddy 的 `ImportFiles` 中将你的 Lua 文件重命名为与原版目标文件相同的名字（或在 XML 中写新名字）。

### 方式二：`<Include>` XML 实例覆盖
在同一个 `<Context>` 中引入 XML 文件，重新定义原版的 `<Instance>` 模板，为新控件"预留位置"：

```xml
<Include File="LeaderIcon"/>  <!-- 你自己的 leadericon.xml -->
```

```xml
<!-- leadericon.xml — 重新定义 LeaderIcon45 实例，增加 3 个 Label 指示器 -->
<Instance Name="LeaderIcon45">
    <Button ID="SelectButton" Size="auto,auto">
        <Image Texture="Controls_CircleBacking45" Size="51,51" Anchor="C,C" Offset="0,1"/>
        <Image ID="YouIndicator" Hidden="1" Size="55,53" Texture="Diplomacy_YouIndicator45" Anchor="C,C"/>
        <Image ID="Portrait" Anchor="C,C" Size="45,45" Texture="Leaders45"/>
        <Image ID="TeamRibbon" Anchor="C,B" Offset="0,-4" Texture="TeamRibbon53" Size="53,53"/>
        <Button ID="Relationship" Style="DiplomacyRelationshipPips" Anchor="L,B" Disabled="1" ConsumeMouse="0"/>
        <!-- ===== EDR 新增的 3 个指示器 ===== -->
        <Label ID="TradeIndicator" String="[ICON_NEW]" Anchor="L,T" Offset="0,2" Hidden="1"/>
        <Label ID="PeaceIndicator" String="[ICON_MAKE_PEACE]" Anchor="L,T" Offset="0,2" Hidden="1"/>
        <Label ID="DealIndicator" String="[ICON_TradeRouteLarge]" Anchor="R,B" Offset="0,0" Hidden="1"/>
        <!-- ===== EDR 新增结束 ===== -->
        <Image ID="CivIndicator" Anchor="R,T" Texture="CircleBacking22" Size="22,22" Offset="-5,-2" Hidden="1">
            <Image ID="CivIcon" Anchor="C,C" Texture="CivSymbols22" Size="22,22"/>
        </Image>
    </Button>
</Instance>
```

**关键点**：重定义的 Instance Name 必须和原版一致。新加的控件 ID 在原版 Lua 中不存在，但在你的 Lua 中会被访问。

## 关键 Lua 代码

### 1. include 链 + 函数缓存 + override（核心模式）

```lua
-- 第一步：include 原版 Lua 文件
include("DiplomacyRibbon")

-- 第二步：缓存原版函数
BASE_AddLeader = AddLeader
BASE_OnLeaderClicked = OnLeaderClicked

-- 第三步：覆盖关键函数，在其中调用原版 + 自己的逻辑
function AddLeader(iconName : string, playerID : number, kProps: table)
    -- 1) 调用原版，获取原版创建的控件表
    local leaderIcon = BASE_AddLeader(iconName, playerID, kProps)
    local instance = leaderIcon.Controls  -- 获取实例内控件引用

    -- 2) 通过 instance.XXX 访问你在 XML 中新增的控件
    instance.TradeIndicator:SetHide(not canTrade)
    instance.PeaceIndicator:SetHide(not canMakePeace)
    instance.DealIndicator:SetHide(dealsTooltip == nil)

    -- 3) 注册自己的事件回调（可以和原版的共存）
    leaderIcon:RegisterCallback(Mouse.eLClick, function() OnLeaderLeftClicked(playerID) end)
    leaderIcon:RegisterCallback(Mouse.eRClick, function() OnLeaderRightClicked(playerID) end)
    leaderIcon:RegisterCallback(Mouse.eMouseEnter, function() OnLeaderMouseOver(playerID) end)
    leaderIcon:RegisterCallback(Mouse.eMClick, function()
        m_isCTRLDown = not m_isCTRLDown  -- 中键切换状态
        OnLeaderMouseOver(playerID)
    end)

    -- 4) 扩展 Tooltip（在已有 Tooltip 后追加内容）
    local existingTooltip = instance.Portrait:GetToolTipString()
    instance.Portrait:SetToolTipString(existingTooltip .. GetExtendedTooltip(playerID))
end
```

### 2. 多 DLC 兼容的 include 链

EDR 有三层 Lua 文件：
```
DiplomacyRibbon.lua          (原版)
  └─ ExtendedDiplomacyRibbon.lua  (EDR 基础，include 原版)
       └─ XP2/EDR_DiplomacyRibbon_Expansion2.lua  (GS 扩展，include EDR 基础)
```

```lua
-- EDR_DiplomacyRibbon_Expansion2.lua
include("ExtendedDiplomacyRibbon.lua")  -- 继承 EDR 基础

-- 再次缓存已被上一级覆盖过的函数
BASE_UpdateLeaders = UpdateLeaders
BASE_RealizeSize = RealizeSize

-- 继续覆盖
function UpdateLeaders()
    -- 自己的逻辑（比如添加世界议会按钮）
    if m_kCongressButtonIM then
        -- ...
    end
    BASE_UpdateLeaders()  -- 调用上一级的 UpdateLeaders
end
```

### 3. DLC 检测

```lua
local m_isRiseAndFall:boolean = Modding.IsModActive("1B28771A-C749-434B-9053-D1380C553DE9")
local m_isGatheringStorm:boolean = Modding.IsModActive("4873eb62-8ccc-4574-b784-dda455e74e68")
```

### 4. Context 感知（判断自己在哪个父屏幕中）

```lua
function OnLeaderLeftClicked(playerID)
    -- 使用 LookUpControl 向上查找，判断当前所在屏幕
    if ContextPtr:LookUpControl(".."):GetID() == "DiplomacyActionView" then
        return nil  -- 在交易/外交界面中，不处理左键
    end
    BASE_OnLeaderClicked(playerID)
end
```

## 数据刷新

```lua
-- 1) 在外交会话关闭时刷新
Events.DiplomacySessionClosed.Add(UpdateLeaders)

-- 2) 在玩家回合开始时刷新
Events.LocalPlayerTurnBegin.Add(OnStartOfLocalPlayerTurn)

-- 3) 使用脏标记避免重复刷新
local isDiplomacyRibbonUpdated = false

function OnStartOfLocalPlayerTurn()
    isDiplomacyRibbonUpdated = false
    UpdateLeaders()
end
```

## 工程配置

1. **ImportFiles** 中配置 XML 文件覆盖（如 `DiplomacyActionView.xml`、`DiplomacyDealView.xml`），文件名必须与原版一致
2. Lua 文件也通过 ImportFiles 导入，`include()` 的文件名需匹配
3. 需要在 `.modinfo` 的 `InGameActions` 中注册，或作为 `ImportFiles` 导入后由重命名的 XML 中的 `<LuaContext>` 加载

## 适用场景
- 给外交条领袖头像加 Tooltip 信息（资源、交易、关系详情）
- 扩展交易界面的资源图标（加新指示器）
- 给现有 UI 添加新的交互模式（中键显示关系、右键直接和平谈判）
- 不改变原版整体布局，只做"增量"修改

## 注意事项
- 原版 Instance 的 Name 必须精确匹配，不然你的 Lua 里 `instance.XXX` 会 nil
- 函数缓存要放在 include 之后、覆盖之前
- DLC 兼容需要用 `Modding.IsModActive()` 先检测
- `ContextPtr:LookUpControl("..")` 可以用来判断当前 Lua 被加载到哪个 UI 上下文中

## XML 配合

### 涉及的关键 XML 文件

| 文件 | 路径（相对于 Mod 根目录） | 用途 |
|------|--------------------------|------|
| `leadericon.xml` | Mod 根目录 | 重定义 LeaderIcon Instance，新增 EDR 指示器控件 |
| `DiplomacyActionView.xml` | `XP2/DiplomacyActionView.xml` | 覆盖原版外交视图，注入 `<LuaContext>` 加载自定义 Lua |

### 核心控件 ID 对照表

| 控件 ID | 类型 | 所在 Instance | 用途 |
|---------|------|-------------|------|
| **EDR 新增指示器（添加到原版 LeaderIcon Instance 中）** | | | |
| `TradeIndicator` | Label | LeaderIcon45 / LeaderIcon55 | 可交易指示（`[ICON_NEW]`） |
| `PeaceIndicator` | Label | LeaderIcon45 / LeaderIcon55 | 可和平指示（`[ICON_MAKE_PEACE]`） |
| `DealIndicator` | Label | LeaderIcon45 / LeaderIcon55 | 交易中指示（`[ICON_TradeRouteLarge]`） |
| **原版 Instance 中已有的控件（被 EDR 扩展）** | | | |
| `SelectButton` | Button | LeaderIcon45 | 选择按钮（原版） |
| `Portrait` | Image | LeaderIcon45 | 领袖头像（原版，EDR 扩展其 Tooltip） |
| `Relationship` | Button | LeaderIcon45 | 关系图标（原版） |
| `CivIndicator` | Image | LeaderIcon45 | 文明图标容器（原版） |
| `CivIcon` | Image | LeaderIcon45 | 文明图标（原版） |
| `YouIndicator` | Image | LeaderIcon45 | 本地玩家指示器（原版） |
| `TeamRibbon` | Image | LeaderIcon45 | 队伍色带（原版） |
| **XML 注入点** | | | |
| `<LuaContext ID="DiplomacyRibbon">` | LuaContext | - | 在原版 DiplomacyActionView.xml 中唯一修改，将 FileName 指向自定义 Lua |

### 关键模式：Instance 重定义

在 `leadericon.xml` 中以 `<Include File="LeaderIcon">` 包裹，重定义原版 Instance Name（如 `LeaderIcon45`、`LeaderIcon55`），在里面添加新的控件 ID。Lua 侧通过 `instance = leaderIcon.Controls` 访问这些新控件：

```xml
<Include File="LeaderIcon">
    <!-- 重定义 LeaderIcon45，新增 3 个 Label 指示器 -->
    <Instance Name="LeaderIcon45">
        <Button ID="SelectButton" Size="auto,auto">
            <Image Texture="Controls_CircleBacking45" Size="51,51" Anchor="C,C" Offset="0,1"/>
            <Image ID="YouIndicator" Hidden="1" Size="55,53" Texture="Diplomacy_YouIndicator45" Anchor="C,C"/>
            <Image ID="Portrait" Anchor="C,C" Size="45,45" Texture="Leaders45"/>
            <Image ID="TeamRibbon" Anchor="C,B" Offset="0,-4" Texture="TeamRibbon53" Size="53,53"/>
            <Button ID="Relationship" Style="DiplomacyRelationshipPips" Anchor="L,B" Disabled="1" ConsumeMouse="0"/>
            <!-- === 自定义新增控件 === -->
            <Label ID="TradeIndicator" String="[ICON_NEW]" Anchor="L,T" Offset="0,2" Hidden="1"/>
            <Label ID="PeaceIndicator" String="[ICON_MAKE_PEACE]" Anchor="L,T" Offset="0,2" Hidden="1"/>
            <Label ID="DealIndicator" String="[ICON_TradeRouteLarge]" Anchor="R,B" Offset="0,0" Hidden="1"/>
            <!-- === 自定义新增结束 === -->
            <Image ID="CivIndicator" Anchor="R,T" Texture="CircleBacking22" Size="22,22" Offset="-5,-2" Hidden="1">
                <Image ID="CivIcon" Anchor="C,C" Texture="CivSymbols22" Size="22,22"/>
            </Image>
        </Button>
    </Instance>
</Include>
```

### LuaContext 注入模板

在原版 XML 中仅添加一行，将原版 Lua 替换为自己的：

```xml
<!-- 在原版 DiplomacyActionView.xml 中的唯一修改 -->
<LuaContext ID="DiplomacyRibbon" FileName="DiplomacyRibbon" Offset="175,0"/>
<!-- FileName 指向你通过 ImportFiles 导入的自定义 Lua 文件 -->
```
