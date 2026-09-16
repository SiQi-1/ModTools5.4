# 城市面板可展开操作按钮组（来源：工坊 3665503799 Black Shores / 3549419242 BAIE）

## 做什么
在城市面板（CityPanel）的 ActionStack 中注入一个可展开的主按钮，点击后展开 2-4 个子操作按钮，每个子按钮对应不同功能（如消耗资源加速生产/科技/开启支援模式）。

## 架构

```
CityPanel ActionStack
  └── RootGrid (ChangeParent注入)
      ├── MainButton (点击展开/收起)
      └── ButtonContainer (初始隐藏，展开时显示)
          ├── SubButton1 (加速生产)
          ├── SubButton2 (加速科技)
          └── SubButton3 (支援模式，可左右键不同行为)
```

---

## 一、XML 控件定义

```xml
<Context Name="MyCityActionContext">
    <!-- 根容器 -->
    <Grid ID="MyCityTrackerGrid" Anchor="L,B" Size="43,41"
          Texture="UnitPanel_ActionButton" SliceSize="1,1"
          SliceTextureSize="auto,10" ConsumeMouse="1" Alpha="0.75">

        <!-- 主按钮 -->
        <Button ID="MyMainButton" Anchor="L,B" Size="44,53"
                Texture="UnitPanel_ActionButton" ToolTip="LOC_MAIN_TOOLTIP">
            <Image ID="MyMainIcon" Anchor="C,C" Offset="0,-5" Size="44,44" />
        </Button>
    </Grid>

    <!-- 可展开的子按钮容器（初始隐藏） -->
    <Container ID="MyButtonContainer" Anchor="L,B"
               Size="auto,auto" Hidden="1">
        <Stack StackGrowth="Down" StackPadding="2">
            <Button ID="MySubButton1" Size="44,44" .../>
            <Button ID="MySubButton2" Size="44,44" .../>
            <Button ID="MySubButton3" Size="44,44" .../>
        </Stack>
    </Container>
</Context>
```

## 二、挂载到 CityPanel

```lua
function Initialize()
    local pContext = ContextPtr:LookUpControl("/InGame/CityPanel/ActionStack")
    if pContext then
        local pParentGrid = Controls.MyCityTrackerGrid
        if pParentGrid then
            pParentGrid:ChangeParent(pContext)
            pParentGrid:ReprocessAnchoring()

            -- 注册主按钮点击
            Controls.MyMainButton:RegisterCallback(Mouse.eLClick, OnMainButtonClick)
        end
    end
end
Events.LoadGameViewStateDone.Add(Initialize)
```

## 三、展开/收起逻辑

```lua
local g_bMainButtonExpanded = false

function OnMainButtonClick()
    -- 状态检查
    local pCity = UI.GetHeadSelectedCity()
    if not pCity or pCity:GetOwner() ~= localPlayerID then return end

    g_bMainButtonExpanded = not g_bMainButtonExpanded
    Controls.MyMainButton:SetSelected(g_bMainButtonExpanded)
    Controls.MyButtonContainer:SetHide(not g_bMainButtonExpanded)

    if g_bMainButtonExpanded then
        -- 展开时刷新子按钮状态
        RefreshSubButtons()
    end
end

function ResetButtonState()
    g_bMainButtonExpanded = false
    Controls.MyButtonContainer:SetHide(true)
    Controls.MyMainButton:SetSelected(false)
end
```

## 四、子按钮状态刷新（动态启用/禁用 + Tooltip）

```lua
function RefreshSubButtons()
    local pCity = UI.GetHeadSelectedCity()
    if not pCity then
        Controls.MyButtonContainer:SetHide(true)
        Controls.MyMainButton:SetDisabled(true)
        return
    end

    local iPlayer = pCity:GetOwner()
    local currentResource = GetPlayerResource(iPlayer)
    local bHasResource = currentResource >= NEED_AMOUNT

    -- 按钮1：始终可用性检查
    Controls.MySubButton1:SetDisabled(not bHasResource)
    Controls.MySubButton1:SetToolTipString(
        bHasResource
            and Locale.Lookup("LOC_BTN1_READY", currentResource)
            or Locale.Lookup("LOC_BTN1_INSUFFICIENT", currentResource, NEED_AMOUNT)
    )

    -- 按钮2：需要还有生产队列
    local prodInfo = GetCityProductionInfo(pCity)
    local bHasProduction = prodInfo and prodInfo.Cost > 0
    Controls.MySubButton2:SetDisabled(not bHasProduction)
    Controls.MySubButton2:SetToolTipString(
        bHasProduction
            and Locale.Lookup("LOC_BTN2_READY", prodInfo.Name)
            or Locale.Lookup("LOC_BTN2_NOTHING")
    )
end
```

## 五、子按钮左右键不同行为

```lua
-- 左键：开启支援
function OnSubButtonLeftClick()
    ShowConfirmPopup()  -- 弹确认窗
end

-- 右键：关闭支援
function OnSubButtonRightClick()
    ShowCloseConfirmPopup()
end

-- 注册（在刷新时动态注册，以便更新状态）
Controls.MySubButton3:ClearCallback(Mouse.eLClick)
Controls.MySubButton3:ClearCallback(Mouse.eRClick)

if currentLevel >= 1 then
    Controls.MySubButton3:RegisterCallback(Mouse.eRClick, function()
        ResetButtonState()
        ShowCloseConfirmPopup()
    end)
end
if bHasResource then
    Controls.MySubButton3:RegisterCallback(Mouse.eLClick, function()
        ResetButtonState()
        ShowConfirmPopup()
    end)
end
```

## 六、生命周期事件监听

```lua
-- 城市切换时刷新
Events.CitySelectionChanged.Add(function(ownerPlayerID, cityID, i, j, k, isSelected)
    if ownerPlayerID == localPlayerID then
        if isSelected then
            RefreshSubButtons()
        else
            ResetButtonState()
        end
    end
end)

-- 生产队列变更时刷新
Events.CityProductionQueueChanged.Add(function(playerID, ...)
    if playerID == localPlayerID then RefreshSubButtons() end
end)

-- 回合切换时重置
Events.PlayerTurnDeactivated.Add(function(playerID)
    if playerID == localPlayerID then ResetButtonState() end
end)
```

---

## XML 配合

### 用到的 XML 文件

| 来源 Mod | XML 文件路径 | 作用 |
|----------|------------|------|
| Black Shores (3665503799) | `UI/Leader_CML/CML_Switcher_BS.xml` | 城市面板可展开按钮组 |
| BAIE (3549419242) | `UI/XXX.xml`（推断） | 类似的可展开按钮模式 |

### 控件 ID 对照（以 CML Switcher 为例）

| XML 控件 ID | 类型 | Lua 角色 |
|------------|------|---------|
| `CMLSwitcherCity_RootGrid` | `Grid` | 根容器，`ChangeParent` 挂载到 CityPanel ActionStack |
| `CMLSwitcherCity_MainBtn` | `Button` | 主按钮，点击展开/收起子按钮 |
| `CMLSwitcherCity_Icon` | `Image` | 主按钮图标 |

### 完整 XML

```xml
<Context Name="CMLSwitcherCity_Context">
    <Grid ID="CMLSwitcherCity_RootGrid" Anchor="L,B" Size="43,41"
          Texture="UnitPanel_ActionButton" SliceSize="1,1"
          SliceTextureSize="auto,10" ConsumeMouse="1" Alpha="0.75">
        <Button ID="CMLSwitcherCity_MainBtn" Anchor="L,B" Offset="0,0"
                Size="44,53" Texture="UnitPanel_ActionButton"
                ToolTip="LOC_CML_SWITCHER_CITY_DEFAULT">
            <Image ID="CMLSwitcherCity_Icon" Anchor="C,C" Offset="0,-5"
                   Size="44,44" />
        </Button>
    </Grid>
</Context>
```

### 可复用 XML

- **CityPanel 可展开按钮**：Grid 主容器 + Button 主按钮 + Container 子按钮组三件套，适合所有"选中城市展开多操作"的场景
- 子按钮 Container 定义在同一个 Context 中，初始 `Hidden="1"`
- 作为 Context Additions 注册到 modinfo，`LoadGameViewStateDone` + `CitySelectionChanged` 时联动
```
