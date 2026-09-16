# 多步确认/重选工作流模式（来源：Better Religion Screen）

## 做什么
实现"选择 → 确认摘要 → 提交"的多步操作流程，支持在确认阶段退回重新选择或重新选择前置选项（如重新选择宗教后再重新选信条）。使用 `PlayerOperations` API 提交最终结果到游戏引擎，并防止重复提交。

## 涉及文件

| 文件 | 来源 Mod | 角色 |
|------|---------|------|
| `ReligionScreen.lua` | Better Religion Screen (2145663327) | 完整的工作流实现 |

## 技术原理

### 工作流状态图

```
选择万神殿信条：
  SelectPantheonBeliefs → ConfirmPantheonBeliefs → 提交 FoundPantheon

创建新宗教：
  ChooseReligion → SelectReligionBeliefs → ConfirmReligionBeliefs → 提交 FoundReligion + AddBelief

为已有宗教添加信条：
  SelectReligionBeliefs (Add 模式) → ConfirmReligionBeliefs → 提交 AddBelief
```

### 核心状态变量

```lua
local m_SelectedBeliefs = {}         -- 当前工作流中选中的信条 ID 列表
local m_isConfirmingBeliefs = false  -- 是否处于"确认"阶段（而非"选择"阶段）
local m_isConfirmedBeliefs = false   -- 防止重复提交的互斥锁
```

### 选择阶段

```lua
function SelectPantheonBeliefs()
    ResetState()

    m_SelectedBeliefs = {}
    m_isConfirmingBeliefs = false

    -- 设置 IM 引用
    m_Beliefs = {
        IM = m_SelectBeliefsIM,
        Stack = Controls.AvailableBeliefs,
        Scrollbar = Controls.AvailableBeliefsScrollbar
    }
    m_PendingBeliefs = {
        IM = m_SelectedBeliefsIM,
        Stack = Controls.SelectedBeliefs,
        Scrollbar = SelectedBeliefsScrollbar
    }
    m_PendingBeliefs.IM:ResetInstances()

    -- UI 文本
    Controls.ChooseBelief:SetHide(false)
    Controls.SelectBeliefs:SetHide(false)
    Controls.ChooseBeliefTitle:SetText(
        Locale.ToUpper(Locale.Lookup("LOC_UI_RELIGION_CHOOSE_PANTHEON_BELIEF")))

    -- 填充可选信条
    PopulateAvailableBeliefs("BELIEF_CLASS_PANTHEON")
end
```

### 自动进入确认阶段

```lua
function OnBeliefSelected(beliefID, availableBeliefInst)
    -- 禁用已选的信条
    SetBeliefSlotDisabled(availableBeliefInst, true)

    -- 添加到待确认列表
    AddSelectedBelief(beliefID)
    RealizeStack(m_PendingBeliefs.Stack, m_PendingBeliefs.Scrollbar, true)
    table.insert(m_SelectedBeliefs, beliefID)

    -- 根据条件自动推进状态
    if m_PantheonBelief < 0 then
        -- 万神殿：选完 1 个后自动进入确认
        ConfirmPantheonBeliefs()
    elseif table.count(m_SelectedBeliefs) + m_NumBeliefsEquipped >= m_NumBeliefsEarned then
        -- 宗教信条：全部选完后进入确认
        ConfirmReligionBeliefs()
    else
        -- 还有更多信条要选：继续留在选择阶段
        PopulateAvailableBeliefs()
    end
end
```

### 确认阶段

```lua
function ConfirmPantheonBeliefs()
    ResetState()
    m_isConfirmingBeliefs = true
    m_isConfirmedBeliefs = false  -- 重置防止重复提交

    Controls.ChooseBelief:SetHide(true)
    Controls.SelectBeliefs:SetHide(false)
    Controls.ConfirmBeliefs:SetHide(false)
    Controls.ReselectBeliefs:SetHide(false)

    -- 显示已选摘要
    local beliefName = Locale.Lookup(GameInfo.Beliefs[m_SelectedBeliefs[1]].Name)
    Controls.ReligionOrPatheonTitle:SetText(
        Locale.ToUpper(Locale.Lookup("LOC_UI_RELIGION_PANTHEON_NAME", beliefName)))

    -- "重新选择"按钮 → 回到选择阶段
    Controls.ReselectBeliefs:LocalizeAndSetText("LOC_UI_RELIGION_RESELECT_BELIEFS")
    Controls.ReselectBeliefs:RegisterCallback(Mouse.eLClick, SelectPantheonBeliefs)
    Controls.ReselectBeliefs:RegisterCallback(Mouse.eMouseEnter,
        function() UI.PlaySound("Main_Menu_Mouse_Over") end)

    -- "确认"按钮 → 提交
    Controls.ConfirmBeliefs:LocalizeAndSetText("LOC_UI_RELIGION_FOUND_PANTHEON")
    Controls.ConfirmBeliefs:RegisterCallback(Mouse.eMouseEnter,
        function() UI.PlaySound("Main_Menu_Mouse_Over") end)
    Controls.ConfirmBeliefs:RegisterCallback(Mouse.eLClick, function()
        if not m_isConfirmedBeliefs then           -- === 互斥锁 ===
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
```

### 从确认阶段取消选择

```lua
function OnBeliefUnSelected(beliefID, selectedBeliefInst, availableBeliefInst)
    -- 重新启用可用列表中的信条
    if availableBeliefInst then
        SetBeliefSlotDisabled(availableBeliefInst, false)
    end

    -- 从待确认列表移除
    m_PendingBeliefs.IM:ReleaseInstance(selectedBeliefInst)
    RealizeStack(m_PendingBeliefs.Stack, m_PendingBeliefs.Scrollbar, true)

    -- 从选中列表移除（包括同类的信徒信条）
    local beliefClass = GameInfo.Beliefs[beliefID].BeliefClassType
    if beliefClass == "BELIEF_CLASS_FOLLOWER" then
        m_PendingBeliefs.IM:ResetInstances()  -- 清除所有待确认信徒信条
    end

    for i = table.count(m_SelectedBeliefs), 1, -1 do
        if beliefID == m_SelectedBeliefs[i]
           or beliefClass == "BELIEF_CLASS_FOLLOWER" then
            table.remove(m_SelectedBeliefs, i)
        end
    end

    -- 根据当前阶段决定下一步
    if m_isConfirmingBeliefs then
        -- 在确认阶段取消 → 退回选择阶段
        if m_PantheonBelief < 0 then
            SelectPantheonBeliefs()
        else
            SelectReligionBeliefs()
        end
    elseif m_PantheonBelief >= 0 then
        -- 在选择阶段取消 → 刷新可用列表
        if table.count(m_SelectedBeliefs) + m_NumBeliefsEquipped >= 1 then
            PopulateAvailableBeliefs()
        else
            PopulateAvailableBeliefs("BELIEF_CLASS_FOLLOWER")
        end
    end
end
```

### 多步提交（宗教创建 + 信条装备）

```lua
function ConfirmReligionBeliefs()  -- 简化版
    local confirmBeliefsButton
    local reselectBeliefsButton
    local reselectReligionButton

    -- 根据是"新建宗教"还是"扩建信条"选择不同的控件
    if m_NumBeliefsEquipped == 0 then
        confirmBeliefsButton = Controls.ConfirmBeliefs
        reselectBeliefsButton = Controls.ReselectBeliefs
        reselectReligionButton = Controls.ReselectReligion
    else
        confirmBeliefsButton = Controls.AddConfirmBeliefs
        reselectBeliefsButton = Controls.AddReselectBeliefs
        reselectReligionButton = Controls.AddReselectReligion
    end

    -- "重新选择信条"按钮
    reselectBeliefsButton:RegisterCallback(Mouse.eLClick, function()
        m_SelectedBeliefs = {}
        if m_PendingBeliefs ~= nil then
            m_PendingBeliefs.IM:ResetInstances()
        end
        SelectReligionBeliefs()
    end)

    -- "重新选择宗教"按钮（仅新建宗教时可用）
    reselectReligionButton:RegisterCallback(Mouse.eLClick, ChooseReligion)

    -- "确认"按钮
    confirmBeliefsButton:RegisterCallback(Mouse.eLClick, function()
        if not m_isConfirmedBeliefs then
            m_isConfirmedBeliefs = true

            -- 步骤 1：如果是新建宗教，先创建宗教
            if m_PlayerReligionType < 0 then
                local tParameters = {}
                tParameters[PlayerOperations.PARAM_RELIGION_TYPE] =
                    GameInfo.Religions[m_SelectedReligion.ID].Hash
                if GameInfo.Religions[m_SelectedReligion.ID].RequiresCustomName then
                    tParameters[PlayerOperations.PARAM_RELIGION_CUSTOM_NAME] =
                        Controls.ChooseReligionName:GetText()
                end
                tParameters[PlayerOperations.PARAM_INSERT_MODE] =
                    PlayerOperations.VALUE_EXCLUSIVE
                UI.RequestPlayerOperation(Game.GetLocalPlayer(),
                    PlayerOperations.FOUND_RELIGION, tParameters)
            end

            -- 步骤 2：逐个添加信条
            for _, belief in ipairs(m_SelectedBeliefs) do
                local tParameters = {}
                tParameters[PlayerOperations.PARAM_BELIEF_TYPE] =
                    GameInfo.Beliefs[belief].Hash
                tParameters[PlayerOperations.PARAM_INSERT_MODE] =
                    PlayerOperations.VALUE_EXCLUSIVE
                UI.RequestPlayerOperation(Game.GetLocalPlayer(),
                    PlayerOperations.ADD_BELIEF, tParameters)
            end

            UI.PlaySound("Confirm_Religion")
            if m_PlayerReligionType >= 0 then
                Close()  -- 扩充信条后关闭
            end
        end
    end)
end
```

## 模式模板

```lua
-- ===========================================================================
-- 多步确认工作流模板
-- ===========================================================================

local m_SelectedItems = {}        -- 待确认的选中项
local m_IsConfirming = false     -- 是否在确认阶段
local m_HasConfirmed = false     -- 防止重复提交

-- 步骤 1：选择
function StartSelection()
    ResetUI()

    m_SelectedItems = {}
    m_IsConfirming = false

    -- 填充可选列表
    PopulateAvailableOptions()

    -- 每个选项点击后自动判断是否进入确认阶段
    -- (选够数量 → 自动进 Step 2，否则留在 Step 1)
end

-- 步骤 2：确认
function ConfirmSelection()
    ResetUI()
    m_IsConfirming = true
    m_HasConfirmed = false

    -- 显示摘要
    ShowSelectionSummary(m_SelectedItems)

    -- 重新选择 → 回 Step 1
    Controls.ReselectButton:RegisterCallback(Mouse.eLClick, StartSelection)

    -- 确认提交 → Step 3
    Controls.ConfirmButton:RegisterCallback(Mouse.eLClick, function()
        if not m_HasConfirmed then
            m_HasConfirmed = true
            SubmitSelection()
        end
    end)
end

-- 步骤 3：提交
function SubmitSelection()
    -- 多步提交示例：
    -- 1. 先创建主实体
    local params = {}
    params[PlayerOperations.PARAM_MAIN_TYPE] = mainData.Hash
    params[PlayerOperations.PARAM_INSERT_MODE] = PlayerOperations.VALUE_EXCLUSIVE
    UI.RequestPlayerOperation(Game.GetLocalPlayer(),
        PlayerOperations.CREATE_MAIN, params)

    -- 2. 再逐个添加附属项
    for _, item in ipairs(m_SelectedItems) do
        local p = {}
        p[PlayerOperations.PARAM_SUB_TYPE] = GameInfo.SubItems[item].Hash
        p[PlayerOperations.PARAM_INSERT_MODE] = PlayerOperations.VALUE_EXCLUSIVE
        UI.RequestPlayerOperation(Game.GetLocalPlayer(),
            PlayerOperations.ADD_SUB, p)
    end

    UI.PlaySound("Confirm_Action")
    Close()
end

-- 取消选择（从确认阶段退回）
function OnItemDeselected(itemID)
    RemoveItemFromSelection(itemID)

    if m_IsConfirming then
        StartSelection()     -- 退回选择阶段
    else
        RefreshAvailableOptions()  -- 留在选择阶段
    end
end
```

## 设计要点

1. **三阶段分离**：选择（m_IsConfirming=false）→ 确认（m_IsConfirming=true）→ 提交
2. **m_isConfirmedBeliefs 互斥锁**：防止玩家快速连点确认按钮导致重复提交
3. **手动推进 vs 自动推进**：万神殿"选 1 个自动确认"，宗教"全部选完自动确认"，不同流程可用不同策略
4. **重置按钮分层**：`ReselectBeliefs`（退回选择信条）+ `ReselectReligion`（退回选择宗教），逐级回退
5. **提交顺序**：先创建主实体再添加附属项（`FOUND_RELIGION` → `ADD_BELIEF`），保证依赖关系
6. **PlayerOperations 正确使用**：所有修改必须通过 `UI.RequestPlayerOperation`，不能直接修改游戏数据
7. **m_PendingBeliefs.IM:ResetInstances**：退回选择时清理待确认列表的视觉元素
8. **同类信条批量清除**：取消一个信徒信条时清除所有信徒信条（因为只能有一个），这是领域规则的体现

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `UI/ReligionScreen.xml` | Better Religion Screen 完整布局 — 含选择/确认阶段的所有控件容器 |

### 确认工作流涉及的控件 ID 对照

| XML 控件（ID） | 类型 | 阶段 | 用途 |
|---------------|------|------|------|
| `SelectBeliefs` | Container | 选择+确认 | 选择/确认信条的总容器（Offset="20,90"） |
| `ChooseBelief` | Grid | 选择 | 可选信条网格（980x420） |
| `ChooseBeliefTitle` | Label | 选择 | 信条选择标题 |
| `AvailableBeliefsScrollbar` | ScrollPanel | 选择 | 可选信条滚动面板 |
| `AvailableBeliefs` | Stack | 选择 | 可选信条条目挂载点（Growth="Right", WrapGrowth="Down"） |
| `SelectedBeliefsScrollbar` | ScrollPanel | 选择+确认 | 已选信条滚动面板 |
| `SelectedBeliefs` | Stack | 选择+确认 | 已选信条条目挂载点（Growth="Down"） |
| `ReligionOrPatheonTitle` | Label | 确认 | 选中的宗教/万神殿名称摘要 |
| `ReselectReligion` | GridButton | 确认 | "重新选择宗教"按钮（MainButton 样式，250x41） |
| `ReselectBeliefs` | GridButton | 确认 | "重新选择信条"按钮（250x41） |
| `ConfirmBeliefs` | GridButton | 确认 | "确认信条"按钮（ButtonConfirm 样式，250x41） |
| `AddBeliefs` | Container | 添加模式 | 为已有宗教添加信条的容器（结构同 SelectBeliefs） |
| `AddBelief` | Grid | 添加模式 | 添加模式的可选信条网格 |
| `AddAvailableBeliefs` | Stack | 添加模式 | 添加模式的可选信条挂载点 |
| `AddReselectReligion` | GridButton | 添加模式 | 添加模式的重新选择宗教 |
| `AddReselectBeliefs` | GridButton | 添加模式 | 添加模式的重新选择信条 |
| `AddConfirmBeliefs` | GridButton | 添加模式 | 添加模式的确认按钮 |
| `ChooseReligion` | Container | 选择宗教 | 宗教选择面板（含图标列表） |
| `PendingReligionTitle` / `PendingReligionStatus` / `PendingReligionEffect` | Label | 选择宗教 | 待选宗教的标题/状态/效果 |

### 工作流阶段与控件显隐

| 阶段 | 可见控件 | 隐藏控件 |
|------|---------|---------|
| 选择信条 | `ChooseBelief`, `AvailableBeliefs`, `SelectedBeliefs`, `WorkingTowards` | `ConfirmBeliefs`, `ReselectBeliefs`, `ReselectReligion` |
| 确认信条 | `SelectedBeliefs`, `ReligionOrPatheonTitle`, `ConfirmBeliefs`, `ReselectBeliefs`, `ReselectReligion` | `ChooseBelief`, `AvailableBeliefs`, `WorkingTowards` |
| 选择宗教 | `ChooseReligion` | `SelectBeliefs`, `AddBeliefs` |

### 确认按钮交互模板

```xml
<!-- 确认按钮 — 含互斥锁防护 -->
<GridButton ID="ConfirmBeliefs" Offset="492,640"
            Size="250,41" Anchor="C,C" Style="ButtonConfirm" />
<GridButton ID="ReselectBeliefs" Offset="492,590"
            Size="250,41" Anchor="C,C" Style="MainButton" />
<GridButton ID="ReselectReligion" Offset="492,540"
            Size="250,41" Anchor="C,C" Style="MainButton" />
```

```lua
Controls.ConfirmBeliefs:RegisterCallback(Mouse.eLClick, function()
    if not m_isConfirmedBeliefs then           -- 互斥锁
        m_isConfirmedBeliefs = true
        UI.RequestPlayerOperation(...)
    end
end)
```
