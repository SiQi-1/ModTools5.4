# 状态机 UI 模式：单屏多状态导航（来源：Better Religion Screen）

## 做什么
一个 Lua 文件管理多个完全不同的 UI 状态（如"查看宗教""选择万神殿""确认信条"），通过 `ResetState()` 隐藏所有控件再选择性显示目标状态。这是一种轻量级状态机模式，避免为每个状态创建独立 UI 文件。

## 涉及文件

| 文件 | 来源 Mod | 角色 |
|------|---------|------|
| `ReligionScreen.lua` | Better Religion Screen (2145663327) | 完整的状态机实现 |
| `ReligionScreen.xml` | Better Religion Screen | 包含所有状态的 UI 容器 |

## 技术原理

### 状态枚举（隐式）

ViewMyReligion() 函数根据玩家游戏状态路由到不同的 UI 状态：

```
玩家状态检查链：
  没有万神殿？ ──Yes──▶ 能否创建万神殿？
                              ├─ Yes → SelectPantheonBeliefs()
                              └─ No  → WorkingTowardsPantheon()
  有万神殿？ ──Yes──▶ 信条数为 0？
                              ├─ Yes → WorkingTowardsReligion()
                              └─ No  → 还没创教？
                                        ├─ Yes → ChooseReligion()
                                        └─ No  → 还有未装备信条？
                                                  ├─ Yes → SelectReligionBeliefs()
                                                  └─ No  → ViewReligion(playerReligion)
```

### ResetState() 模式

```lua
function ResetState()
    -- 隐藏所有可能的状态区域
    Controls.ViewReligion:SetHide(true)
    Controls.ChooseReligion:SetHide(true)
    Controls.AddBeliefs:SetHide(true)
    Controls.AddConfirmBeliefs:SetHide(true)
    Controls.AddReselectBeliefs:SetHide(true)
    Controls.AddReselectReligion:SetHide(true)
    Controls.SelectBeliefs:SetHide(true)
    Controls.ConfirmBeliefs:SetHide(true)
    Controls.ReselectBeliefs:SetHide(true)
    Controls.ReselectReligion:SetHide(true)
    Controls.SelectBeliefsPantheonIcon:SetHide(true)
    Controls.SelectBeliefsPantheonImage:SetHide(true)
    Controls.SelectBeliefsPantheonTitle:SetHide(true)
    Controls.SelectBeliefsPantheonDescription:SetHide(true)
    Controls.WorkingTowards:SetHide(true)
    Controls.WorkingTowardsReligion:SetHide(true)
    Controls.ViewAllReligions:SetHide(true)
end
```

### 状态函数示例

每个状态函数遵循相同模式：ResetState → 填充数据 → 显示目标容器：

```lua
-- 状态：选择万神殿信条
function SelectPantheonBeliefs()
    ResetState()

    m_SelectedBeliefs = {}
    m_isConfirmingBeliefs = false
    m_Beliefs = { IM = m_SelectBeliefsIM, Stack = Controls.AvailableBeliefs, ... }
    m_PendingBeliefs = { IM = m_SelectedBeliefsIM, Stack = Controls.SelectedBeliefs, ... }
    m_PendingBeliefs.IM:ResetInstances()

    Controls.ChooseBelief:SetHide(false)
    Controls.SelectBeliefs:SetHide(false)
    Controls.ChooseBeliefTitle:SetText(...)
    Controls.ReligionOrPatheonTitle:SetText(...)
    Controls.ReligionOrPatheonImage:SetOffsetY(OFFSET_CHOOSING_PANTHEON_BELIEFS)

    SetReligionIcon(Controls.ReligionOrPatheonImage)
    PopulateAvailableBeliefs("BELIEF_CLASS_PANTHEON")
end

-- 状态：确认万神殿选择
function ConfirmPantheonBeliefs()
    ResetState()
    m_isConfirmingBeliefs = true
    m_isConfirmedBeliefs = false

    Controls.ChooseBelief:SetHide(true)
    Controls.SelectBeliefs:SetHide(false)
    Controls.ConfirmBeliefs:SetHide(false)
    Controls.ReselectBeliefs:SetHide(false)

    -- 显示已选信条信息
    local beliefName = Locale.Lookup(GameInfo.Beliefs[m_SelectedBeliefs[1]].Name)
    Controls.ReligionOrPatheonTitle:SetText(Locale.ToUpper(
        Locale.Lookup("LOC_UI_RELIGION_PANTHEON_NAME", beliefName)))

    -- 按钮回调
    Controls.ReselectBeliefs:RegisterCallback(Mouse.eLClick, SelectPantheonBeliefs)
    Controls.ConfirmBeliefs:RegisterCallback(Mouse.eLClick, function()
        if not m_isConfirmedBeliefs then
            m_isConfirmedBeliefs = true
            local tParameters = {}
            tParameters[PlayerOperations.PARAM_BELIEF_TYPE] =
                GameInfo.Beliefs[m_SelectedBeliefs[1]].Hash
            tParameters[PlayerOperations.PARAM_INSERT_MODE] =
                PlayerOperations.VALUE_EXCLUSIVE
            UI.RequestPlayerOperation(Game.GetLocalPlayer(),
                PlayerOperations.FOUND_PANTHEON, tParameters)
            UI.PlaySound("Confirm_Religion")
        end
    end)
end

-- 状态：查看已创建的宗教
function ViewReligion(religionType)
    ResetState()

    -- 数据验证
    local religion = nil
    for _, tmp in ipairs(m_pGameReligion:GetReligions()) do
        if tmp.Religion == religionType then religion = tmp; break end
    end
    if religion == nil then return end

    Controls.ViewReligion:SetHide(false)

    -- 填充宗教详情...
    Controls.ViewReligionTitle:SetText(...)
    Controls.ViewReligionFounder:SetText(...)
    Controls.ViewReligionHolyCity:SetText(...)
    Controls.ViewReligionDominance:SetText(...)

    -- 填充信徒数据、城市数据...
    PopulateReligionBeliefs(religion)
    PopulateCitiesData(religionType)
    PopulateFollowersGrid(religionType)
end
```

### 状态中继续的确认守卫

在确认状态中切换回选择状态时，需要重新判断前置条件：

```lua
function OnBeliefUnSelected(beliefID, selectedBeliefInst, availableBeliefInst)
    -- ... 移除选中 ...

    if m_isConfirmingBeliefs then
        -- 从确认状态返回：回到选择状态
        if m_PantheonBelief < 0 then
            SelectPantheonBeliefs()
        else
            SelectReligionBeliefs()
        end
    elseif m_PantheonBelief >= 0 then
        -- 在选择状态中移除信条：刷新可用列表
        if table.count(m_SelectedBeliefs) + m_NumBeliefsEquipped >= 1 then
            PopulateAvailableBeliefs()
        else
            PopulateAvailableBeliefs("BELIEF_CLASS_FOLLOWER")
        end
    end
end
```

### 状态间防止重复确认

```lua
-- 确认按钮回调中的重复确认防止
Controls.ConfirmBeliefs:RegisterCallback(Mouse.eLClick, function()
    if not m_isConfirmedBeliefs then       -- 守卫：防止连点
        m_isConfirmedBeliefs = true
        -- 执行确认逻辑...
        UI.RequestPlayerOperation(...)
        UI.PlaySound("Confirm_Religion")
    end
end)
```

## 模式模板

```lua
-- ===========================================================================
-- 状态机 UI 模板
-- ===========================================================================

-- 状态定义（可选，便于维护）
local STATES = {
    VIEW_MAIN       = 1,
    SELECT_ITEM     = 2,
    CONFIRM_ITEM    = 3,
    ADD_ITEM        = 4,
}

function ResetState()
    -- 隐藏所有状态容器
    Controls.MainView:SetHide(true)
    Controls.SelectView:SetHide(true)
    Controls.ConfirmView:SetHide(true)
    Controls.AddView:SetHide(true)
    -- 隐藏子元素（如果需要在状态间切换）
    Controls.PanelTitle:SetHide(true)
    Controls.PanelImage:SetHide(true)
end

-- 路由函数：根据游戏状态决定显示哪个界面
function RouteToState()
    local playerData = GetPlayerData()
    if not playerData.HasItem then
        if playerData.CanCreateItem then
            SelectItem()
        else
            ShowWorkingTowards()
        end
    elseif playerData.HasPendingSlots then
        SelectItemToAdd()
    else
        ViewMain(playerData.ActiveItem)
    end
end

-- 状态 A：查看
function ViewMain(itemID)
    ResetState()
    Controls.MainView:SetHide(false)
    -- 填充数据...
end

-- 状态 B：选择
function SelectItem()
    ResetState()
    Controls.SelectView:SetHide(false)
    -- 填充选项列表...
    -- 选中后自动进入确认状态
end

-- 状态 C：确认
function ConfirmItem()
    ResetState()
    Controls.ConfirmView:SetHide(false)
    -- 显示已选内容摘要
    -- 确认按钮 → 提交 + 关闭
    -- 重新选择按钮 → 回到状态 B
end

-- 状态 D：添加
function SelectItemToAdd()
    ResetState()
    -- 类似选择但用于已有物品之上追加新物品
end
```

## 设计要点

1. **ResetState 先全部隐藏**：确保没有前一个状态的 UI 残留
2. **状态函数末尾显示目标容器**：只有目标状态需要的容器才设为可见
3. **确认守卫 m_isConfirmedBeliefs**：防止玩家连点确认按钮导致重复请求
4. **m_isConfirmingBeliefs 跟踪上下文**：在选择状态中取消信条时，根据此标记决定回到选择还是确认状态
5. **InstanceManager 在状态切换时 ResetInstances**：确保列表数据不会在状态间交叉污染
6. **游戏事件驱动的状态重评估**：`OnBeliefAdded` 等事件触发 `UpdateData()` → 重新路由状态

## 适用场景

| 场景 | 说明 |
|------|------|
| 创建/选择流程 | 选择 → 确认 → 提交 的多步流程 |
| 条件分支面板 | 不同游戏阶段显示完全不同界面 |
| 向导式交互 | 多步骤引导玩家完成操作 |
| 信息层级展示 | 总览 → 点击 → 详情 的逐步深入 |

## XML 配合

### 涉及的关键 XML 文件

| 文件 | 路径（相对于 Mod 根目录） | 用途 |
|------|--------------------------|------|
| `UI/ReligionScreen.xml` | `UI/ReligionScreen.xml` | 包含所有 7 个状态容器 + 11 个 Instance 的完整 Context |

### 核心控件 ID 对照表（按状态分组）

| 控件 ID | 类型 | 所属状态 | 用途 |
|---------|------|---------|------|
| **框架** | | | |
| `Vignette` | Container | 全局 | 全屏暗色遮罩 |
| `ModalControls` | Container | 全局 | Modal 框架（Style="ModalScreen"） |
| `TabContainer` | Container | 全局 | 动态 Tab 容器（Instance 填充） |
| **状态：努力获取** | | | |
| `WorkingTowards` | Container | WorkingTowards | 未获得万神殿/宗教（Hidden="1"） |
| `WorkingTowardsReligion` | Grid | WorkingTowards | 正在努力获得宗教子面板 |
| `WorkingTowardsReligionTitle` | Label | WorkingTowards | 状态标题 |
| `WorkingTowardsReligionDesc` | Label | WorkingTowards | 状态描述 |
| `WorkingTowardsPantheon` | Grid | WorkingTowards | 正在努力获得万神殿子面板 |
| `WorkingTowardsPantheonTitle` | Label | WorkingTowards | 万神殿名称 |
| `WorkingTowardsPantheonEffect` | Label | WorkingTowards | 万神殿效果描述 |
| `WorkingTowardsPantheonStatus` | Label | WorkingTowards | 万神殿获取进度 |
| **状态：选择信条** | | | |
| `SelectBeliefs` | Container | SelectBeliefs | 选择信条面板（Hidden="1"） |
| `ChooseBelief` | Grid | SelectBeliefs | 信条选择区框架 |
| `ChooseBeliefTitle` | Label | SelectBeliefs | 信条选择区标题 |
| `AvailableBeliefsScrollbar` | ScrollPanel | SelectBeliefs | 可用信条滚动区 |
| `AvailableBeliefs` | Stack | SelectBeliefs | 可用信条列表（StackGrowth="Right" WrapGrowth="Down"） |
| `SelectedBeliefsScrollbar` | ScrollPanel | SelectBeliefs | 已选信条滚动区 |
| `SelectedBeliefs` | Stack | SelectBeliefs | 已选信条列表 |
| `SelectBeliefsPantheonTitle` | Label | SelectBeliefs | 万神殿名称展示 |
| `SelectBeliefsPantheonDescription` | Label | SelectBeliefs | 万神殿描述 |
| `SelectBeliefsPantheonIcon` | Image | SelectBeliefs | 万神殿图标 |
| `ConfirmBeliefs` | GridButton | SelectBeliefs | 确认信条按钮 |
| `ReselectBeliefs` | GridButton | SelectBeliefs | 重新选择信条按钮 |
| `ReselectReligion` | GridButton | SelectBeliefs | 重新选择宗教按钮 |
| `ReligionOrPatheonImage` | Image | SelectBeliefs | 宗教/万神殿大图 |
| `ReligionOrPatheonTitle` | Label | SelectBeliefs | 宗教/万神殿名称 |
| **状态：添加信条** | | | |
| `AddBeliefs` | Container | AddBeliefs | 添加信条面板（Hidden="1"，结构与 SelectBeliefs 对应） |
| `AddBelief` | Grid | AddBeliefs | 信条选择区 |
| `AddAvailableBeliefs` | Stack | AddBeliefs | 可用信条列表 |
| `AddConfirmBeliefs` | GridButton | AddBeliefs | 确认添加按钮 |
| `AddReselectBeliefs` | GridButton | AddBeliefs | 重新选择按钮 |
| `AddReselectReligion` | GridButton | AddBeliefs | 重新选择宗教按钮 |
| **状态：创建宗教** | | | |
| `ChooseReligion` | Container | ChooseReligion | 创建宗教面板（Hidden="1"） |
| `ChooseReligionTitle` | Label | ChooseReligion | 标题 |
| `ChooseReligionItems` | Stack | ChooseReligion | 宗教图标列表 |
| `ChooseReligionName` | EditBox | ChooseReligion | 宗教名称输入框 |
| `ConfirmReligion` | GridButton | ChooseReligion | 确认创建按钮 |
| **状态：查看宗教** | | | |
| `ViewReligion` | Container | ViewReligion | 查看宗教详情面板（Hidden="1"） |
| `ViewReligionImage` | Image | ViewReligion | 宗教图标 |
| `ViewReligionTitle` | Label | ViewReligion | 宗教名称 |
| `ViewReligionFounder` | Label | ViewReligion | 创教者 |
| `ViewReligionHolyCity` | Label | ViewReligion | 圣城 |
| `ViewReligionDominance` | Label | ViewReligion | 宗教压力 |
| `ViewReligionBeliefs` | Stack | ViewReligion | 信条列表 |
| `CitiesScrollbar` | ScrollPanel | ViewReligion | 城市列表滚动区 |
| `Cities` | Stack | ViewReligion | 城市数据列表 |
| **状态：查看所有宗教** | | | |
| `ViewAllReligions` | Container | ViewAllReligions | 查看所有宗教面板（Hidden="1"） |
| `Religions` | Stack | Religions | 宗教概览卡片列表 |
| **Instances** | | | |
| `ReligionTab` | Instance | 全局 | 宗教 Tab 按钮 |
| `BeliefSlot` | Instance | SelectBeliefs | 可选信条条目 |
| `ReligionBelief` | Instance | ViewReligion | 已装备信条条目 |
| `ReligionBeliefSmall` | Instance | ViewReligion | 小号信条条目 |
| `ReligionOption` | Instance | ChooseReligion | 宗教图标选项 |
| `Religion` | Instance | ViewAllReligions | 宗教概览卡片 |
| `City` | Instance | ViewReligion | 城市宗教数据行 |
| `CityFollowers` | Instance | ViewReligion | 城市信徒数/压力 |
| `UnitIconInstance` | Instance | （预留） | 单位图标 |
| `CivLineInstance` | Instance | ViewReligion | 文明条目行 |
| `ReligionIcon` | Instance | （预留） | 宗教图标 |

### 可复用 XML 模板（单屏多状态基础骨架）

```xml
<Context>
    <Container ID="Vignette" Style="FullScreenVignetteConsumer" />
    <Container ID="ModalControls" Style="ModalScreen">

        <!-- Tab 导航区 -->
        <Container Anchor="C,T" Offset="0,30" Size="500,61">
            <Container ID="TabContainer" Size="Parent-80,34" Offset="40,13"/>
        </Container>

        <!-- 状态 A：查看主界面 -->
        <Container ID="StateView" Offset="10,80" Hidden="1">
            <ScrollPanel ID="MainScrollPanel" Size="1000,685" Vertical="1">
                <Stack ID="MainStack" Anchor="C,T" StackGrowth="Down" StackPadding="3"/>
            </ScrollPanel>
        </Container>

        <!-- 状态 B：选择/创建 -->
        <Container ID="StateSelect" Offset="20,90" Hidden="1">
            <ScrollPanel ID="SelectScrollPanel" Size="980,420" Vertical="1">
                <Stack ID="SelectStack" StackGrowth="Right" WrapGrowth="Down" WrapWidth="980"/>
            </ScrollPanel>
            <GridButton ID="ConfirmButton" Offset="492,640" Size="250,41" Anchor="C,C" Style="ButtonConfirm"/>
        </Container>

        <!-- 状态 C：确认 -->
        <Container ID="StateConfirm" Offset="20,90" Hidden="1">
            <Label ID="ConfirmTitle" Anchor="C,C" Style="FontFlair24"/>
            <GridButton ID="ConfirmSubmitButton" Size="250,41" Anchor="C,B" Style="ButtonConfirm"/>
            <GridButton ID="ConfirmReselectButton" Size="250,41" Anchor="C,B" Style="MainButton"/>
        </Container>

    </Container>

    <!-- Instances -->
    <Instance Name="ItemSlot">
        <GridButton ID="ItemButton" Size="450,auto" AutoSizePadding="0,6" MinSize="192,72">
            <Image ID="ItemIcon" Size="64,64" Anchor="L,C"/>
            <Label ID="ItemLabel" Anchor="L,C" Offset="75,2" Style="FontFlair16"/>
            <Label ID="ItemDescription" WrapWidth="365" Style="FontNormal14" Anchor="L,C" Offset="75,20"/>
        </GridButton>
    </Instance>
</Context>
```

### ResetState 对应的 XML 设计原则

- 所有状态容器初始必须 `Hidden="1"`
- 每个状态容器之间同级独立，不应嵌套
- Instance 定义在 Context 最底部（不在任何状态容器内）
- `ResetState()` 用 `Controls.StateX:SetHide(true)` 隐藏所有，再用 `Controls.StateTarget:SetHide(false)` 显示目标
