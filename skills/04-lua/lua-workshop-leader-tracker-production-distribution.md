# 生产力储存与分配追踪器（来源：碧蓝航线北方议会 3335420111）

## 做什么
在城市面板（CityPanel）的 ActionStack 中添加一个"生产力分发"按钮，追踪城市储存的生产力总量，并将它按需分配给范围内其他城市的生产队列。按钮的 Tooltip 动态计算并展示每座目标城市将获得的精确生产力量，实现了从"储存-展示-分配"的完整 UI 管道。

## 涉及文件

| 文件 | 角色 |
|------|------|
| `UI/Additions/NorthernCityPanel.lua` | 主 UI 逻辑：按钮状态、分配计算、Tooltip 生成 |
| `UI/Additions/NorthernCityPanel.xml` | 按钮 UI 定义 |
| `Import/Modules/NorthernCore.lua` | 核心工具库：生产详情获取、距离计算等 |
| `Import/NorthernSupport.lua` | 生产力数据类：Yield 提取、Modifier 计算、储存读写 |
| `Scripts/NorthernScript.lua` 等 | GP 端：EXECUTE_SCRIPT 处理分发 |

## 核心模式

### 1. 按钮定位到 CityPanel ActionStack

与崩坏仙舟 Mod 使用相同的位置（CityPanel 右下角的 ActionStack）：

```lua
function NorthernParliamentAddButton()
    local pContext = ContextPtr:LookUpControl("/InGame/CityPanel/ActionStack")
    if pContext then
        Controls.NorthernParliamentCityStack:ChangeParent(pContext)
        Controls.NorthernParliamentCityButton:RegisterCallback(
            Mouse.eLClick, NorthernParliamentCityButtonClick)
        Controls.NorthernParliamentCityButton:RegisterCallback(
            Mouse.eMouseEnter, NorthernParliamentEnter)
        NorthernParliamentResetButton()
    end
end
```

### 2. 动态获取需要分配的生产力

生产队列解析（来自 `NorthernCore.GetProductionDetail`）：

```lua
function NorthernCityPanel.GetProductionNeed(pCity)
    local needProduction = nil
    if pCity == nil then return needProduction end

    -- 获取当前生产队列的详细信息
    local cityProduction = NorthernCore.GetProductionDetail(pCity)
    if cityProduction.Producting then
        needProduction = cityProduction.TotalCost - cityProduction.Progress

        local cityID, ownerID = pCity:GetID(), pCity:GetOwner()
        if Utils:GetMultiplierUsable(ownerID, cityID) then
            -- 获取该类型生产的效率乘数
            local multiplier = 1
            if cityProduction.IsBuilding then
                multiplier = Utils:GetBuildingMultiplier(ownerID, cityID, cityProduction.ItemIndex)
            elseif cityProduction.IsDistrict then
                multiplier = Utils:GetDistrictMultiplier(ownerID, cityID, cityProduction.ItemIndex)
            elseif cityProduction.IsUnit then
                multiplier = Utils:GetUnitMultiplier(ownerID, cityID, cityProduction.ItemIndex)
            elseif cityProduction.IsProject then
                multiplier = Utils:GetProjectMultiplier(ownerID, cityID, cityProduction.ItemIndex)
            end
            -- 实际需要 = (总成本 - 进度) / 乘数 - 已回收进度
            needProduction = math.ceil(
                (needProduction / multiplier) - Utils:GetSalvageProgress(ownerID, cityID))
        end
    end
    return needProduction
end
```

### 3. 公平分配算法

按需分配生产力——先满足需求最小的城市，剩余再均分：

```lua
function NorthernCityPanel:GetDetail(pCity)
    local detail = { Disable = true, CityTable = {}, TotalProduction = 0 }

    -- 获取储存的生产力
    local totalProduction = cityObj:GetStoredProduction()
    detail.TotalProduction = totalProduction

    -- 收集范围内所有有生产需求的城市
    local cityList = {}
    for _, city in pCities:Members() do
        if pCity ~= city and GetDistance(pCity, city) <= range
            and self.GetProductionNeed(city) ~= nil then
            table.insert(cityList, { city, self.GetProductionNeed(city) })
        end
    end

    -- 按需求从小到大排序
    table.sort(cityList, function(a, b) return a[2] < b[2] end)

    local denominator = #cityList
    local aveProduction, remainder = self.NumDivision(totalProduction, denominator)

    for _, city in ipairs(cityList) do
        local needProduction = city[2]
        if needProduction < aveProduction then
            -- 需求小于平均值：直接满足全部需求
            totalProduction = totalProduction - needProduction
            SetCityTable(city[1], needProduction)
            -- 重算平均值
            denominator = denominator - 1
            if denominator > 0 then
                aveProduction, remainder = self.NumDivision(totalProduction, denominator)
            end
        else
            -- 需求 >= 平均值：给平均值 + 可能的余数
            totalProduction = totalProduction - aveProduction
            local grant = aveProduction
            if remainder > 0 then
                remainder = remainder - 1
                grant = grant + 1
            end
            if grant > 0 then SetCityTable(city[1], grant) end
        end
    end
    return detail
end
```

### 4. 动态 Tooltip 展示分配合集

```lua
function NorthernCityPanel:Reset(pCity)
    local detail = self:GetDetail(pCity)

    Controls.NorthernParliamentCityButton:SetDisabled(detail.Disable)
    Controls.NorthernParliamentCityButton:SetAlpha((detail.Disable and 0.7) or 1)

    local tooltip = Locale.Lookup('LOC_SIB_PROJECT_NAME') ..
        '[NEWLINE][NEWLINE]' .. Locale.Lookup('LOC_SIB_PROJECT_DESC', range)
    tooltip = tooltip .. '[NEWLINE][NEWLINE]' ..
        Locale.Lookup('LOC_SIB_PROJECT_PRODUCTION_DETAIL', detail.TotalProduction)

    -- 逐城市显示分配结果
    if next(detail.CityTable) then
        tooltip = tooltip .. '[NEWLINE][NEWLINE]' ..
            Locale.Lookup('LOC_SIB_PROJECT_PRODUCTION_CITY')
        for _, city in pairs(detail.CityTable) do
            tooltip = tooltip .. '[NEWLINE]' ..
                Locale.Lookup('LOC_SIB_PROJECT_PRODUCTION_CITY_DETAIL',
                    city[1], city[2])
        end
    end

    -- 禁用时显示原因
    if detail.Disable then
        tooltip = tooltip .. '[NEWLINE][NEWLINE]' .. detail.Reason
    end

    Controls.NorthernParliamentCityButton:SetToolTipString(tooltip)
end
```

### 5. 消费通过 EXECUTE_SCRIPT

```lua
function NorthernParliamentCityButtonClick()
    local pCity = UI.GetHeadSelectedCity()
    if pCity then
        local detail = NorthernCityPanel:GetDetail(pCity)
        if detail.Disable then return end
        UI.RequestPlayerOperation(Game.GetLocalPlayer(),
            PlayerOperations.EXECUTE_SCRIPT, {
                CityID    = pCity:GetID(),
                CityTable = detail.CityTable,    -- 城市ID → 分配量映射
                OnStart   = 'NorthernParliamentGiveProduction'
            }
        )
        UI.PlaySound("Confirm_Production")
        Network.BroadcastPlayerInfo()
    end
end
```

### 6. 多地刷新触发

```lua
function Initialize()
    Events.LoadGameViewStateDone.Add(NorthernParliamentAddButton)
    Events.CitySelectionChanged.Add(NorthernParliamentCitySelectionChanged)
    Events.LocalPlayerChanged.Add(NorthernParliamentResetButton)

    -- 任何可能改变城市生产状态的事件都刷新
    Events.DistrictAddedToMap.Add(NorthernParliamentResetButton)
    Events.DistrictBuildProgressChanged.Add(NorthernParliamentResetButton)
    Events.DistrictRemovedFromMap.Add(NorthernParliamentResetButton)
    Events.DistrictPillaged.Add(NorthernParliamentResetButton)
    Events.CityAddedToMap.Add(NorthernParliamentResetButton)
    Events.CityProductionQueueChanged.Add(NorthernParliamentResetButton)
    Events.CityProductionUpdated.Add(NorthernParliamentResetButton)
    Events.CityProductionChanged.Add(NorthernParliamentResetButton)
    Events.CityProductionCompleted.Add(NorthernParliamentResetButton)
    Events.CityRemovedFromMap.Add(NorthernParliamentResetButton)
    Events.CityPropertyChanged.Add(NorthernParliamentResetButton)
end
```

## 条件可见性

```lua
function NorthernParliamentResetButton()
    local pCity = UI.GetHeadSelectedCity()
    if pCity and NorthernCore.CheckCivMatched(
            pCity:GetOwner(), 'CIVILIZATION_NORTHERN_PARLIAMENT') then
        Controls.NorthernParliamentCityStack:SetHide(false)
        NorthernCityPanel:Reset(pCity)
    else
        Controls.NorthernParliamentCityStack:SetHide(true)
    end
end
```

## GP 端配合

`NorthernSupport.lua` 中定义了经济层：
- **储存精度**：生产力以 ×10 精度存储（避免浮点误差）：`city:SetProperty(SupportKey, math.floor(production * 10))`
- **每回合积累**：`NorthernSupport:UpdateStoredProduction()` → 累加当回合城市产出
- **消费时**：`NorthernSupport:ChangeStoredProduction(-amount)` 扣减

## 与已有模式的对比

| 已有模式 | 本模式差异 |
|----------|-----------|
| `lua-0036-productivity-stockpile.md` | 本模式是**城市间分配**而非城市内注入；有距离限制和效率乘数 |
| `lua-0033-citypanel-resource-spending.md` | 本模式资源来源是**城市产出自动累积**；Tooltip **动态计算分配结果** |
| `lua-workshop-economy-warehouse.md` | 类似仓库概念，但本模式专门针对生产力且UI在CityPanel而非独立面板 |

## 来源

工坊 Mod 3335420111（碧蓝航线北方议会 Northern Parliament），`UI/Additions/NorthernCityPanel.lua`——苏维埃工业基地的生产力储存与分配系统。

---

## XML 配合

### 用到的 XML 文件

| 来源 Mod | XML 文件路径 | 作用 |
|----------|------------|------|
| Northern Parliament (3335420111) | `UI/Additions/NorthernCityPanel.xml` | 城市面板生产力分发按钮 |

### 控件 ID 对照

| XML 控件 ID | 类型 | Lua 角色 |
|------------|------|---------|
| `NorthernParliamentCityStack` | `Stack` | 按钮根容器，`ChangeParent` 挂载到 CityPanel ActionStack |
| `NorthernParliamentCityButton` | `Button` | 主按钮，注册 `Mouse.eLClick` 执行分发 + `Mouse.eMouseEnter` 更新 Tooltip |
| `NorthernParliamentCityIcon` | `Image` | 按钮图标 |

### 完整 XML

```xml
<Context Name="NorthernParliamentCityPanelAddon">
    <Stack ID="NorthernParliamentCityStack" Anchor="C,B"
           StackGrowth="Right" StackPadding="4">
        <Button ID="NorthernParliamentCityButton" Anchor="L,B"
                Size="44,53" Texture="UnitPanel_ActionButton">
            <Image ID="NorthernParliamentCityIcon" Anchor="C,C"
                   Offset="-1,-3" Size="32,32"
                   Icon="ICON_NORTHERN_PARLIAMENT_CITY"/>
        </Button>
    </Stack>
</Context>
```

### 可复用 XML

- **CityPanel ActionStack 单按钮**：最简模式 — 一个 Context + 一个 Stack + 一个 Button，适合任何"选中城市时弹出一个操作按钮"的场景
- 按钮尺寸 44×53 + `Texture="UnitPanel_ActionButton"` 与游戏原生风格一致
- 作为 Context Additions 注册到 modinfo，`LoadGameViewStateDone` 时挂载
