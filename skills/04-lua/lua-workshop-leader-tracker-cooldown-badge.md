# TopPanel 冷却/状态徽章追踪器（来源：夏日口袋 2880952125）

## 做什么
在顶部面板右侧（科学/文化/金币条右边、时钟/菜单左边区域）插入一个自定义状态徽章按钮，显示技能/项目的冷却剩余回合数或可用状态。适合需要向玩家持续展示"某能力还有 N 回合可用"的场景。

## 涉及文件

| 文件 | 角色 |
|------|------|
| `UI/Additions/SP_AoProjectColdDown.lua` | 主逻辑：添加徽章、刷新状态、监听事件 |
| `UI/Additions/SP_AoProjectColdDown.xml` | 徽章 UI 定义（预先写好） |
| `Scripts/SP_Gameplay.lua` / `SP_Gameplay_Shiroha.lua` | GP 端：设置/读取 Property，暴露 GameEvents |
| `UI/Additions/SP_Support.lua` | 辅助函数：PlayerHasLeaderTrait |

## 核心模式

### 1. 添加徽章到 TopPanel

使用 `ChangeParent` 将预先定义好的 UI 控件移动到 TopPanel 的右侧区域：

```lua
function AddButtonToTopPanel()
    -- 获取 TopPanel 右侧栈（时钟、文明百科、菜单按钮所在位置）
    local topPanelRight = ContextPtr:LookUpControl("/InGame/TopPanel/RightContents")
    if topPanelRight then
        Controls.Icon:SetIcon('ICON_PROJECT_SP_BUTTERFLY')
        Controls.SPAoProjectColdDown:ChangeParent(topPanelRight)
        topPanelRight:CalculateSize()
        topPanelRight:ReprocessAnchoring()

        -- 注册刷新事件
        Events.LocalPlayerTurnBegin.Add(OnLocalPlayerTurnBegin_Ao)
        Events.CityProjectCompleted.Add(OnCityProjectCompleted)
        RefreshStatus()
    end
end
```

关键：必须在 `Events.LoadGameViewStateDone` 中调用，确保 TopPanel 已初始化。

### 2. 根据冷却状态刷新徽章文字/提示

```lua
function RefreshStatus()
    local param = {}
    -- 通过 ExposedMembers 跨上下文读取 GP 端数据
    GameEvents.SummerPocketsGetPlayerProperty.Call(
        Game.GetLocalPlayer(), SP_AO_BUTTERFLY, param)

    if param.Property and param.Property.LastForbiddenTurn then
        local leftTurns = param.Property.LastForbiddenTurn
            + SP_AO_BUTTERFLY_COLD - Game.GetCurrentGameTurn()
        if leftTurns >= 1 then
            -- 冷却中：显示剩余回合数
            Controls.ProjectStatus:SetText('[ICON_Turn]' .. tostring(leftTurns))
            Controls.SPAoProjectColdDown:LocalizeAndSetToolTip(
                'LOC_SP_AO_PROJECT_TOOLTIP_FORBIDDEN', leftTurns)
        else
            -- 可用
            Controls.ProjectStatus:LocalizeAndSetText(
                'LOC_SP_AO_PROJECT_STATUS_AVAILABLE')
            Controls.SPAoProjectColdDown:LocalizeAndSetToolTip(
                'LOC_SP_AO_PROJECT_TOOLTIP_AVAILABLE')
        end
    else
        Controls.ProjectStatus:LocalizeAndSetText(
            'LOC_SP_AO_PROJECT_STATUS_AVAILABLE')
        Controls.SPAoProjectColdDown:LocalizeAndSetToolTip(
            'LOC_SP_AO_PROJECT_TOOLTIP_AVAILABLE')
    end
end
```

### 3. 刷新触发

```lua
-- 每回合刷新
function OnLocalPlayerTurnBegin_Ao()
    RefreshStatus()
end

-- 项目完成时刷新（如果冷却由项目触发）
function OnCityProjectCompleted(playerID, cityID, projectID, ...)
    if playerID ~= Game.GetLocalPlayer() then return end
    if m_ProjectButterflyInfo.Index == projectID then
        RefreshStatus()
    end
end
```

### 4. 条件性加载（仅特定领袖显示）

```lua
function OnLoadGameViewStateDone()
    if PlayerHasLeaderTrait(Game.GetLocalPlayer(), 'TRAIT_LEADER_SORAKADO_AO') then
        AddButtonToTopPanel()
    end
end

function Initialize()
    Events.LoadGameViewStateDone.Add(OnLoadGameViewStateDone)
end
Initialize()
```

## XML 配合

徽章需要预先定义在 `SP_AoProjectColdDown.xml` 中（通常是一个带图标的 Grid/Stack），但不需要在 modinfo 中作为独立 Context 注册——它作为 Additions 由 Lua 动态挂载到 TopPanel。

## 什么时候用

- 领袖有冷却机制的技能/项目/行动，需要在主界面持续显示状态
- 资源每回合自动积累，需要显示当前数量（可改用 `SetText(tostring(count))` + `[ICON_Resource]`）
- 不想修改整个 TopPanel 文件，只想追加一个小元素

## 什么时候不用

- 需要修改 TopPanel 产量/资源列的布局或数据 → 用 TopPanel 文件覆盖模式（`lua-workshop-top-panel-extension.md`）
- 需要复杂的交互（多按钮、下拉等）→ 考虑弹出面板或 CityPanel 扩展

## 扩展：通用回合倒计时徽章

```lua
-- 模板：通用的"冷却倒计时"徽章
function AddCooldownBadge(iconName, propertyKey, cooldownTurns, tooltipLocAvail, tooltipLocCD)
    local topPanelRight = ContextPtr:LookUpControl("/InGame/TopPanel/RightContents")
    if not topPanelRight then return end

    -- ... ChangeParent, 设置图标 ...

    local function Refresh()
        local pPlayer = Players[Game.GetLocalPlayer()]
        local lastUsed = pPlayer:GetProperty(propertyKey) or -999
        local leftTurns = lastUsed + cooldownTurns - Game.GetCurrentGameTurn()
        if leftTurns >= 1 then
            Controls.StatusLabel:SetText('[ICON_Turn]' .. leftTurns)
            Controls.Root:LocalizeAndSetToolTip(tooltipLocCD, leftTurns)
        else
            Controls.StatusLabel:LocalizeAndSetText(tooltipLocAvail)
            Controls.Root:LocalizeAndSetToolTip(tooltipLocAvail)
        end
    end

    Events.LocalPlayerTurnBegin.Add(Refresh)
    -- 如果冷却由特定事件触发，也注册那个事件
    Refresh()
end
```

## 来源

工坊 Mod 2880952125（夏日口袋 Summer Pockets），`UI/Additions/SP_AoProjectColdDown.lua`——紬·文德斯的"蝴蝶效应"项目冷却追踪器。
