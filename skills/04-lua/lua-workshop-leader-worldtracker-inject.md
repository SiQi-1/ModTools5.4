# WorldTracker PanelStack 注入模式（来源：工坊领袖 Mod）

## 做什么
在屏幕左上角 WorldTracker（世界追踪器）的 PanelStack 中注入自定义信息面板，显示领袖特有资源/点数/状态。点击可触发自定义面板或操作。

> **这是唯一覆盖 WorldTracker PanelStack 注入的技能**。与 TopPanel 扩展（顶部水平栏覆盖函数）和 LaunchBar 注入（右上角按钮堆栈）不同，本模式注入到**屏幕左上角的垂直追踪器面板**，适合展示实时变化的文明特有指标（点数、余额等）。

---

## 快速索引

| 来源 Mod | 注入路径 | 显示内容 | 点击行为 |
|----------|---------|---------|---------|
| EagleUnion (2966077687) | `/InGame/WorldTracker/PanelStack` | 研究点数余额 + 每回合增长 | 打开研究面板 |
| Liyue (2599959500) | `/InGame/WorldTracker/PanelStack` | 自定义资源/点数 | 自定义操作 |

---

## 一、完整模版：EagleUnion WorldTracker

### 1.1 初始化注入

```lua
function EagleTrackerInit()
    -- 1. 找到 WorldTracker 的 PanelStack
    local parent = ContextPtr:LookUpControl("/InGame/WorldTracker/PanelStack")
    if parent ~= nil then
        -- 2. 将自定义 Grid 移入 PanelStack
        Controls.EagleTrackerGrid:ChangeParent(parent)
        -- 3. 插入到指定位置（0 = 最前/顶部）
        parent:AddChildAtIndex(Controls.EagleTrackerGrid, 1)
        
        -- 4. 注册点击回调
        EagleUnionTracker.Point:Register()
        
        -- 5. 重新计算父容器布局
        parent:CalculateSize()
        parent:ReprocessAnchoring()
        
        -- 6. 初始刷新
        EagleTrackerReset()
    end
end
```

### 1.2 刷新逻辑：仅目标文明显示

```lua
-- 使用 MetaTable 组织逻辑（清晰分离 Reset / Callback / Register）
EagleUnionTracker = {
    Point = {
        Reset = function()
            local localPlayerID = Game.GetLocalPlayer()
            if EagleCore.CheckCivMatched(localPlayerID, 'CIVILIZATION_EAGLE_UNION') then
                -- 匹配目标文明：显示面板
                Controls.EagleTrackerGrid:SetHide(false)
                
                local point = EaglePointManager.GetEaglePoint(localPlayerID, true)
                Controls.PointBalance:SetText(Locale.ToNumber(point, "#,###.#"))
                
                local perTurnPoint = EaglePointManager:GetPerTurnPoint(localPlayerID, true)
                Controls.PointPerTurn:SetText(EagleCore.FormatValue(perTurnPoint))
                
                local tooltip = EaglePointManager:GetPerTurnPointTooltip(localPlayerID)
                Controls.EagleTrackerPoint:SetToolTipString(tooltip)
            else
                -- 不匹配：完全隐藏
                Controls.EagleTrackerGrid:SetHide(true)
            end
        end,

        Callback = function(self)
            self.Reset()
            LuaEvents.EagleUnionTopButton_TogglePopup()  -- 点击后打开面板
        end,

        Register = function(self)
            Controls.EagleTrackerPoint:RegisterCallback(Mouse.eLClick, function() self:Callback() end)
            Controls.EagleTrackerPoint:RegisterCallback(Mouse.eMouseEnter, EagleUnionEnter)
        end,
    }
}
```

### 1.3 刷新时机

```lua
function Initialize()
    -- 延迟到游戏视图加载完毕
    Events.LoadGameViewStateDone.Add(EagleTrackerInit)

    -- 数据变化时刷新
    Events.CityAddedToMap.Add(EagleTrackerReset)
    Events.CityProductionChanged.Add(EagleTrackerReset)
    Events.ResearchCompleted.Add(EagleTrackerReset)
    Events.CivicCompleted.Add(EagleTrackerReset)
    Events.LocalPlayerChanged.Add(EagleTrackerReset)
    Events.PlayerTurnActivated.Add(EagleTrackerReset)
    Events.GamePropertyChanged.Add(EagleTrackerReset)

    -- [可选] 更多刷新事件
    -- Events.CityPopulationChanged.Add(EagleTrackerReset)
    -- Events.DistrictAddedToMap.Add(EagleTrackerReset)
end
```

---

## 二、XML 控件定义

```xml
<!-- WorldTracker 行样式面板 -->
<Grid ID="EagleTrackerGrid" Anchor="L,T" Offset="14,0"
      Size="270,38" Hidden="1"
      SliceCorner="8,8" SliceTextureSize="16,16"
      Texture="Tracker_TrackBacking">

    <GridButton ID="EagleTrackerPoint" Anchor="L,C"
                Size="parent-1,parent-1" Offset="6,0"
                ConsumeMouseOver="1">

        <Stack StackGrowth="Right" Padding="4" Anchor="R,T">
            <!-- 每回合变化值 -->
            <Label ID="PointPerTurn" Style="FontNormal16"
                   Color="255,255,255,255" Anchor="C,C"
                   Offset="0,15" />
            <!-- 余额 -->
            <Label ID="PointBalance" Style="FontNormal16"
                   Color="255,255,255,255" Anchor="C,C"
                   Offset="0,15" />
        </Stack>

        <!-- 自定义图标 -->
        <Image ID="EagleTrackerIcon" Anchor="L,C" Offset="3,2"
               Size="32,32" Texture="EaglePoint_Icon" />
    </GridButton>
</Grid>
```

---

## 三、简化模版（纯文本 + 图标）

```lua
-- ===========================================================================
-- WorldTracker 注入 — 简化模板
-- ===========================================================================

function MyTrackerInit()
    local panelStack = ContextPtr:LookUpControl("/InGame/WorldTracker/PanelStack")
    if panelStack ~= nil then
        Controls.MyTrackerGrid:ChangeParent(panelStack)
        panelStack:AddChildAtIndex(Controls.MyTrackerGrid, 1)
        panelStack:CalculateSize()
        panelStack:ReprocessAnchoring()
        MyTrackerRefresh()
    end
end

function MyTrackerRefresh()
    local playerID = Game.GetLocalPlayer()
    if not MyLeaderCheck(playerID) then
        Controls.MyTrackerGrid:SetHide(true)
        return
    end
    Controls.MyTrackerGrid:SetHide(false)

    -- 从 GameProperty 或 PlayerProperty 读取自定义数据
    local value = Players[playerID]:GetProperty("MY_CUSTOM_PROPERTY") or 0
    Controls.MyTrackerValue:SetText(Locale.ToNumber(value, "#,###.#"))
    Controls.MyTrackerGrid:SetToolTipString(Locale.Lookup("LOC_MY_TRACKER_TOOLTIP", value))
end

function MyTrackerOnClick()
    -- 点击打开自定义面板
    LuaEvents.MyPanel_Toggle()
end

function Initialize()
    Events.LoadGameViewStateDone.Add(MyTrackerInit)
    Events.LocalPlayerTurnBegin.Add(MyTrackerRefresh)
    Events.GamePropertyChanged.Add(MyTrackerRefresh)
    Controls.MyTrackerGrid:RegisterCallback(Mouse.eLClick, MyTrackerOnClick)
end
Initialize()
```

---

## 四、AddChildAtIndex 位置说明

```lua
parent:AddChildAtIndex(control, 0)   -- 最前（顶部）
parent:AddChildAtIndex(control, 1)   -- 第二个位置
parent:AddChildAtIndex(control, -1)  -- 最后（底部）
```

通常用 `1` 插入到面板顶部，在科技/市政进度之上。

---

## 五、刷新事件选择指南

| 自定义数据来源 | 推荐刷新事件 |
|---------------|-------------|
| PlayerProperty（SetProperty） | `Events.GamePropertyChanged` |
| 自定义 GameProperty（Game:SetProperty） | `Events.GamePropertyChanged` |
| 城市产出变化 | `Events.CityProductionChanged` |
| 回合开始 | `Events.LocalPlayerTurnBegin` 或 `Events.PlayerTurnActivated` |
| 科技/市政完成 | `Events.ResearchCompleted` / `Events.CivicCompleted` |
| 建筑/区域完成 | `Events.CityProductionCompleted` / `Events.DistrictAddedToMap` |

---

## 六、与 TopPanel 扩展的区别

| 特性 | TopPanel 扩展 | WorldTracker 注入 |
|------|--------------|-------------------|
| 位置 | 屏幕顶部水平栏 | 屏幕左上角垂直列表 |
| 用途 | 全局产量/资源显示 | 文明特有资源/点数追踪 |
| 控件类型 | `m_YieldButtonDoubleManager` / IPM 条目 | 自定义 Grid |
| 注入方式 | 覆盖 `RefreshYields()` 函数 | `ChangeParent` + `AddChildAtIndex` |
| 复杂度 | 高（需 include 链 + 函数覆盖） | 低（直接操作控件树） |

---

## 七、常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| 面板出现在错误文明中 | 没在 Refresh 中做领袖判断 | `if not MyLeaderCheck then SetHide(true); return end` |
| 每次刷新面板闪烁 | `CalculateSize()` 调用过于频繁 | 用脏标记，仅在数据实际变化时重建 |
| `AddChildAtIndex` 没生效 | 控件先 `ChangeParent` 再 `AddChildAtIndex` | 调换顺序：先 `ChangeParent`，再 `AddChildAtIndex` |
| GamePropertyChanged 不触发 | GameProperty 未正确设置 | 检查 GP 端是否用 `Game:SetProperty()` 而非 `Player:SetProperty()` |

---

## XML 配合

### 用到的 XML 文件

| 来源 Mod | XML 文件路径 | 作用 |
|----------|------------|------|
| EagleUnion (2966077687) | `UI/Additions/EagleUnionTracker.xml` | WorldTracker 行样式面板控件 |

### 控件 ID 对照

| XML 控件 ID | 类型 | Lua 角色 |
|------------|------|---------|
| `EagleTrackerGrid` | `Grid` | 追踪器根容器，`ChangeParent` 挂载到 PanelStack |
| `EagleTrackerPoint` | `GridButton` | 可点击行按钮，注册 `Mouse.eLClick` 打开面板 |
| `PointBalance` | `Label` | 点数余额显示（例如 `SetText("1,234.5")`） |
| `PointPerTurn` | `Label` | 每回合点数变化显示 |
| `PointIconString` | `Label` | 图标字符串（`[ICON_xxx]` 格式） |

### Instance 模板

本模式使用自定义 Grid 而非 Instance。控件事先在 `<Context>` 中完整定义：

```xml
<Context Name="EagleTracker">
    <Grid ID="EagleTrackerGrid" Offset="0,0" Size="296,Auto" ...>
        <Stack ID="EagleTrackerStack" Anchor="C,T" StackGrowth="Bottom">
            <GridButton ID="EagleTrackerPoint" Anchor="L,C" Size="parent-30,30" ...>
                <Stack StackGrowth="Right">
                    <Label ID="PointIconString" String="[ICON_ResearchPointLarge]"/>
                    <Label ID="PointBalance" Style="FontNormal18" String="?"/>
                    <Label ID="PointPerTurn" Style="FontNormal14" String="0"/>
                </Stack>
            </GridButton>
        </Stack>
    </Grid>
</Context>
```

### 可复用 XML

- **行样式追踪面板**：`EagleTrackerGrid` 的 texture 和 Slice 属性可复用于任何需要在 WorldTracker 中插入自定义行的场景，只需更换图标和 Label 内容
- 作为 Context Additions 注册到 modinfo


## 参考图标菜单的尺寸约束（1528155583）

- 移植既有 UI 时，先保留原控件树的 Texture、Style、Size、Anchor、Offset、StackPadding 与图标子控件；通用行面板模板不能替代原菜单的几何结构。参考菜单根宽 296，圆形按钮 40×40，图标由子 Image 或 Label 显示。
- 不要把圆形 LaunchBar_Hook_ButtonSmall.dds 拉宽后用按钮的 String 代替图标子控件；新增文字按钮可采用原菜单已经使用的 GridButton Style="TabButton"。
- 数字输入采用官方 Popups/PopupDialog.xml 的 Grid Style="EditTextArea" 外框 + 内层 EditBox Style="BlueGlow"。城市本体与城墙各有独立输入框，先查上限再允许提交。
- UI 查询城中心使用官方 CityBannerManager 的 CityManager.GetDistrictAt(city:GetX(), city:GetY())；GetDistrictAtLocation 留在 GP。控件对照和 Lua 模拟检查不能代替游戏内渲染验收。

来源：工坊 1528155583/Base/UI/Panels/Cheat_Panel_World_Tracker.xml；官方 Base/Assets/UI/Popups/PopupDialog.xml 与 CityBannerManager.lua。尺寸/控件树已静态核对，2026-09-11 修复稿尚待游戏内渲染确认。
- 血量快捷按钮发送操作名到 GP，由 GP 在执行时读取当前血量再加减；不要在 UI 缓存上计算绝对值后提交，否则连续点击可能重复提交同一个结果。单位/城市本体可共用选择控件，城墙独立；隐藏城墙组时同时调整扩展区、状态行和根面板高度（Lua 5.1 模拟验证，2026-09-11）。
