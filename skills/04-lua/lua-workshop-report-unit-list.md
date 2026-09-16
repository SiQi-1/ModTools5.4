# lua-workshop-report-unit-list -- 报表屏幕单位列表 UI 模式

从工坊 Mod **Better Report Screen** (1312585482) 的 `BRSPage_Units.lua` 提炼。核心模式：在报表屏幕（ReportScreen）中构建带可折叠分组、可排序列、活跃修饰符分析的单位列表页面。

---

## 架构概览

Better Report Screen 是一个多页面报表系统，每一页都是一个独立的 Lua 文件，被主文件 `reportscreen.lua` 通过 `include()` 加载。

**主文件职责**（`reportscreen.lua`）：
- 管理 Tab 切换（`AddTabSection` + `m_tabs`）
- 管理折叠分组（`NewCollapsibleGroupInstance` + `OnToggleCollapseGroup`）
- 管理全局脏标记（`g_DirtyFlag`）
- 提供通用工具函数（`spairs`、`Round`、`Clamp`、`toPlusMinusString`）
- 统一页面入口模式（`ViewXxxPage`）

**页面文件职责**（`BRSPage_Units.lua`）：
- 数据采集（`GetDataUnits` / `UpdateUnitsData`）
- 分组定义（按 FORMATION_CLASS 分类）
- 排序逻辑（按多字段排序）
- 渲染逻辑（填充 XML Instance 控件）

---

## 页面开发模式（每页三函数）

### 1. `GetDataXxx()` — 数据采集

从游戏对象中采集原始数据，返回分组后的数据表。

```lua
function GetDataUnits()
    local kUnitDataReport = {};

    for _, unit in pUnits:Members() do
        -- 按 FORMATION_CLASS 分类
        local formationClass = unitInfo.FormationClass;
        group_name = string.sub(formationClass, 17); -- 去掉 "FORMATION_CLASS_" 前缀

        -- 子类拆分
        if formationClass == "FORMATION_CLASS_CIVILIAN" then
            if unit:GetGreatPerson():IsGreatPerson() then group_name = "GREAT_PERSON";
            elseif unitInfo.MakeTradeRoute then           group_name = "TRADER";
            elseif unitInfo.Spy then                      group_name = "SPY";
            elseif unit:GetReligiousStrength() > 0 then group_name = "RELIGIOUS";
            end
        end

        -- 初始化分组（含 Header/Entry InstanceName）
        if kUnitDataReport[group_name] == nil then
            kUnitDataReport[group_name] = {
                ID = 1,
                func = group_military,            -- 该分组的渲染函数
                Header = "UnitsMilitaryHeaderInstance",
                Entry  = "UnitsMilitaryEntryInstance",
                Name   = "LOC_BRS_UNITS_GROUP_" .. group_name,
                units  = {}
            };
        end
        table.insert(kUnitDataReport[group_name].units, unit);
    end
    return kUnitDataReport;
end
```

### 2. `UpdateXxxData()` — 带缓存的更新

```lua
function UpdateUnitsData()
    m_kUnitDataReport = GetDataUnits();       -- 重新采集
    g_DirtyFlag.UNITS = false;                 -- 清除脏标记
end
```

### 3. `ViewXxxPage()` — 页面渲染

```lua
function ViewUnitsPage()
    if g_DirtyFlag.UNITS then UpdateUnitsData(); end  -- 按需刷新

    ResetTabForNewPageContent();                       -- 清空旧内容

    for iUnitGroup, kUnitGroup in spairs(m_kUnitDataReport,
        function(t, a, b) return t[b].ID > t[a].ID end  -- 按 ID 排序分组
    ) do
        local instance = NewCollapsibleGroupInstance()    -- 创建折叠组

        -- 设置组头
        instance.RowHeaderButton:SetText(Locale.Lookup(kUnitGroup.Name));
        instance.RowHeaderLabel:SetText("总数: " .. #kUnitGroup.units);

        -- 构建表头 Instance
        local pHeaderInstance = {}
        ContextPtr:BuildInstanceForControl(kUnitGroup.Header, pHeaderInstance,
            instance.ContentStack)

        -- 绑定表头排序回调
        pHeaderInstance.UnitTypeButton:RegisterCallback(Mouse.eLClick,
            function() instance.Descend = not instance.Descend;
                       sort_units("type", iUnitGroup, instance) end)

        -- 初始排序 + 渲染每一行
        for _, unit in spairs(kUnitGroup.units,
            function(t, a, b) return unit_sortFunction(false, "name", t, a, b) end
        ) do
            local unitInstance = {}
            ContextPtr:BuildInstanceForControl(kUnitGroup.Entry, unitInstance,
                instance.ContentStack)
            common_unit_fields(unit, unitInstance)          -- 公共字段
            kUnitGroup.func(unit, unitInstance, ...)        -- 分组特有字段
            -- 点击回调查看/选中单位
            unitInstance.LookAtButton:RegisterCallback(Mouse.eLClick, function()
                Close(); UI.LookAtPlot(unit:GetX(), unit:GetY());
                UI.SelectUnit(unit);
            end)
        end
        RealizeGroup(instance);
    end
    Controls.Stack:CalculateSize();
    Controls.Scroll:CalculateSize();
end
```

---

## 单位分组体系

按 `FORMATION_CLASS` 分为 9 个组，每个组有独立的 Header/Entry Instance 和渲染函数：

| 组名 | FORMATION_CLASS | Header Instance | Entry Instance | 渲染函数 |
|------|----------------|-----------------|----------------|---------|
| LAND_COMBAT | LAND_COMBAT | UnitsMilitaryHeaderInstance | UnitsMilitaryEntryInstance | group_military |
| NAVAL | NAVAL | UnitsMilitaryHeaderInstance | UnitsMilitaryEntryInstance | group_military |
| AIR | AIR | UnitsMilitaryHeaderInstance | UnitsMilitaryEntryInstance | group_military |
| SUPPORT | SUPPORT | UnitsMilitaryHeaderInstance | UnitsMilitaryEntryInstance | group_military |
| CIVILIAN | CIVILIAN | UnitsCivilianHeaderInstance | UnitsCivilianEntryInstance | group_civilian |
| RELIGIOUS | CIVILIAN(子类) | UnitsReligiousHeaderInstance | UnitsReligiousEntryInstance | group_religious |
| GREAT_PERSON | CIVILIAN(子类) | UnitsGreatPeopleHeaderInstance | UnitsGreatPeopleEntryInstance | group_great |
| SPY | CIVILIAN(子类) | UnitsSpyHeaderInstance | UnitsSpyEntryInstance | group_spy |
| TRADER | CIVILIAN(子类) | UnitsTraderHeaderInstance | UnitsTraderEntryInstance | group_trader |

---

## 排序系统

### 通用排序函数

```lua
function unit_sortFunction(descend, type, t, a, b)
    -- 按 type 提取比较值，然后按 descend 决定升序/降序
    if type == "type" then
        aUnit = UnitManager.GetTypeName(t[a])
        bUnit = UnitManager.GetTypeName(t[b])
    elseif type == "name" then
        aUnit = Locale.Lookup(t[a]:GetName())
        bUnit = Locale.Lookup(t[b]:GetName())
        if aUnit == bUnit then
            -- 同名时按军事编队排序
            aUnit = t[a]:GetMilitaryFormation()
            bUnit = t[b]:GetMilitaryFormation()
        end
    elseif type == "move" then
        -- 编队单位用 GetFormationMovesRemaining()
        if t[a]:GetFormationUnitCount() > 1 then
            aUnit = t[a]:GetFormationMovesRemaining()
        else
            aUnit = t[a]:GetMovesRemaining()
        end
    elseif type == "city" then
        -- 主排序按城市名，同名时按距离
        aUnit = t[a].NearCityName
        bUnit = t[b].NearCityName
        if aUnit == bUnit then
            aUnit = t[a].NearCityDistance
            bUnit = t[b].NearCityDistance
        end
    -- ... "maintenance", "status", "level", "exp", "health", "charge",
    --     "yield", "route", "class", "strength", "spread", "mission",
    --     "turns", "albums"
    end
    if descend then return aUnit > bUnit else return aUnit < bUnit end
end
```

### 排序触发

表头按钮点击 → 切换 `instance.Descend` → 调用 `sort_units(type, group, instance)` → 更新所有行数据。

---

## 单位修饰符分析系统

这是该 Mod 的核心特色：**运行时扫描 GameEffects API，提取每个单位身上的活跃修饰符并人类可读化展示**。

### 修饰符采集流程

```lua
-- 1. 建立追踪清单（所有己方单位）
local tTrackedUnits = {};
for _, unit in player:GetUnits():Members() do
    tTrackedUnits[unit:GetID()] = true;
    m_kModifiersUnits[unit:GetID()] = {};
end

-- 2. 遍历所有活跃 GameEffects 修饰符
for _, instID in ipairs(GameEffects.GetModifiers()) do
    local sOwnerType = GameEffects.GetObjectType(iOwnerID);
    local tSubjects = GameEffects.GetModifierSubjects(instID);

    -- 2a. 检查 Subjects（单位作为被修饰对象）
    if tSubjects then
        for _, subjectID in ipairs(tSubjects) do
            if GameEffects.GetObjectsPlayerId(subjectID) == playerID then
                local sSubjectType = GameEffects.GetObjectType(subjectID);
                if sSubjectType == "LOC_MODIFIER_OBJECT_UNIT" then
                    -- 解码 subject string "Unit: 12345 Owner: 0"
                    local sSubjectString = GameEffects.GetObjectString(subjectID);
                    local iUnitID = tonumber(string.match(sSubjectString, "Unit: (%d+)"));
                    if iUnitID and tTrackedUnits[iUnitID] then
                        RegisterModifierForUnit(iUnitID, sSubjectType, sSubjectName);
                    end
                end
            end
        end
    end

    -- 2b. 检查 Owner（单位作为修饰符拥有者）
    -- 使用 IsRegistered() 去重
    if sOwnerType == "LOC_MODIFIER_OBJECT_UNIT" then
        local sOwnerString = GameEffects.GetObjectString(iOwnerID);
        local iUnitID = tonumber(string.match(sOwnerString, "Unit: (%d+)"));
        if iUnitID and tTrackedUnits[iUnitID] and not IsRegistered(iUnitID) then
            RegisterModifierForUnit(iUnitID);
        end
    end
end
```

### 修饰符数据存储结构

```lua
data = {
    ID         = instID,                                    -- GameEffects 实例 ID
    Active     = GameEffects.GetModifierActive(instID),
    Definition = instdef,                                   -- { Id = "MODIFIER_..." }
    Arguments  = instdef.Arguments,                         -- { AbilityType="...", Amount="3", ... }
    OwnerType  = sOwnerType,                                -- "LOC_MODIFIER_OBJECT_CITY" 等
    OwnerName  = sOwnerName,                                -- "LOC_CITY_xxx_NAME" 等
    SubjectType = sSubjectType,                             -- 若来自 Subjects
    SubjectName = sSubjectName,
    UnitID     = iUnitID,
    Modifier   = RMA.FetchAndCacheData(instdef.Id),         -- RMA 静态缓存
};
```

### 修饰符 → 人类可读文本映射

在 `group_military()` 中，对每个修饰符的 EffectType 进行判定，生成可读描述：

```lua
local tTextsForEffects = {
    EFFECT_ATTACH_MODIFIER                        → "LOC_GREATPERSON_PASSIVE_NAME_DEFAULT",
    EFFECT_ADJUST_UNIT_EXTRACT_SEA_ARTIFACTS      → "[ICON_RESOURCE_SHIPWRECK]",
    EFFECT_ADJUST_UNIT_NUM_ATTACKS                → "LOC_PROMOTION_WOLFPACK_DESCRIPTION",
    EFFECT_ADJUST_UNIT_ATTACK_AND_MOVE            → "LOC_PROMOTION_GUERRILLA_DESCRIPTION",
    EFFECT_ADJUST_UNIT_MOVE_AND_ATTACK            → "LOC_PROMOTION_GUERRILLA_DESCRIPTION",
    EFFECT_ADJUST_UNIT_BYPASS_COMBAT_UNIT         → "LOC_ABILITY_BYPASS_COMBAT_UNIT_NAME",
    EFFECT_ADJUST_UNIT_IGNORE_TERRAIN_COST        → "LOC_ABILITY_IGNORE_TERRAIN_COST_NAME",
    EFFECT_ADJUST_UNIT_PARADROP_ABILITY           → "LOC_UNITCOMMAND_PARADROP_DESCRIPTION",
    EFFECT_ADJUST_UNIT_SEE_HIDDEN                 → "LOC_ABILITY_SEE_HIDDEN_NAME",
    EFFECT_ADJUST_UNIT_HIDDEN_VISIBILITY          → "LOC_ABILITY_STEALTH_NAME",
    EFFECT_ADJUST_UNIT_RAIDING                    → "LOC_ABILITY_COASTAL_RAID_NAME",
    EFFECT_ADJUST_UNIT_IGNORE_RIVERS              → "LOC_PROMOTION_AMPHIBIOUS_NAME",
    -- ...
};

-- 逐个 EffectType 分支处理
if tMod.EffectType == "EFFECT_ADJUST_PLAYER_STRENGTH_MODIFIER" then
    AddExtraPromoText(string.format("%+d [ICON_Strength]", tonumber(tMod.Arguments.Amount)));
elseif tMod.EffectType == "EFFECT_GRANT_ABILITY" then
    local unitAbility = GameInfo.UnitAbilities[tMod.Arguments.AbilityType];
    AddExtraPromoText(Locale.Lookup(unitAbility.Name) .. ": " .. Locale.Lookup(unitAbility.Description));
elseif tMod.EffectType == "EFFECT_GRANT_PROMOTION" then
    local unitPromotion = GameInfo.UnitPromotions[tMod.Arguments.PromotionType];
    AddExtraPromoText(Locale.Lookup(unitPromotion.Name) .. ": " .. Locale.Lookup(unitPromotion.Description));
-- ... 约 15 种 EffectType 分支
elseif tTextsForEffects[tMod.EffectType] then
    AddExtraPromoText(Locale.Lookup(tTextsForEffects[tMod.EffectType]));
else
    AddExtraPromoText("[COLOR_Grey]" .. tMod.EffectType .. "[ENDCOLOR]");  -- 未知类型显示原始名
end
```

### 能力过滤（避免显示无关修饰符）

```lua
function InitializeAbilitiesUnits()
    -- 第一次遍历: 提取所有 ABILITY_xxx 的 TypeTags
    for row in GameInfo.TypeTags() do
        if string.sub(row.Type, 1, 8) == "ABILITY_" then
            g_AbilitiesUnits[row.Type] = {};
            g_AbilitiesUnits[row.Type][row.Tag] = true;
        end
    end
    -- 第二次遍历: 对每个 UNIT_xxx，注册到所有匹配其 Tag 的能力
    for row in GameInfo.TypeTags() do
        if string.sub(row.Type, 1, 5) == "UNIT_" then
            for _, units in pairs(g_AbilitiesUnits) do
                if units[row.Tag] then units[row.Type] = true; end
            end
        end
    end
end
```

在 `RegisterModifierForUnit` 中，`EFFECT_GRANT_ABILITY` 类型会检查该能力是否适用于当前单位类型，不适用则跳过。

---

## 公共字段渲染（`common_unit_fields`）

所有单位分组共享的字段：

```lua
function common_unit_fields(unit, unitInstance)
    -- 单位类型图标（32x32）
    local tx, ty, ts = IconManager:FindIconAtlas("ICON_"..UnitManager.GetTypeName(unit), 32)
    unitInstance.UnitType:SetTexture(tx, ty, ts)
    unitInstance.UnitType:SetToolTipString(名称.."\n"..描述)

    -- 单位名称
    unitInstance.UnitName:SetText(Locale.Lookup(unit:GetName()))

    -- 状态图标（睡眠 / 跳过 / 驻防 / 无）
    local activityType = UnitManager.GetActivityType(unit)
    if activityType == ActivityTypes.ACTIVITY_SLEEP then
        -- "ICON_STATS_SLEEP"
    elseif activityType == ActivityTypes.ACTIVITY_HOLD then
        -- "ICON_STATS_SKIP"
    elseif activityType ~= ActivityTypes.ACTIVITY_AWAKE and unit:GetFortifyTurns() > 0 then
        -- "ICON_DEFENSE"
    else
        unitInstance.UnitStatus:SetHide(true)
    end

    -- 移动力（编队单位特殊处理）
    if unit:GetFormationUnitCount() > 1 then
        unitInstance.UnitMove:SetText(formation_moves .. "/" .. formation_max .. " [ICON_Formation]")
    else
        unitInstance.UnitMove:SetText(moves .. "/" .. max_moves)
        -- 移动力为 0 时红色标记
    end

    -- 最近城市（首都标记 + 距离）
    local sCityName = (isCapital and "[ICON_Capital]" or "") .. cityName
    if distance == 0 then sCityName = "[COLOR:16,232,75,160]" .. sCityName .. "[ENDCOLOR]"
    elseif not isOurs then sCityName = "[COLOR_Red]" .. sCityName .. " " .. distance .. "[ENDCOLOR]"
    else sCityName = sCityName .. " " .. distance end
    unitInstance.UnitCity:SetText((distance > 3) and "" or sCityName)

    -- 维护费
    unitInstance.UnitMaintenance:SetText(toPlusMinusString(-maintenance))
end
```

### 距离计算（每单位到最近城市的距离）

```lua
-- 初始化所有单位的默认距离为 9999
unit.NearCityDistance = 9999;

-- 遍历所有存活玩家的所有城市，计算每个单位到每个城市的最小距离
for _, player in ipairs(PlayerManager.GetAlive()) do
    for _, city in player:GetCities():Members() do
        for _, unit in ipairs(tUnitsDist) do
            local iDistance = Map.GetPlotDistance(unitX, unitY, cityX, cityY);
            if iDistance < unit.NearCityDistance then
                unit.NearCityDistance = iDistance;
                unit.NearCityName = sCityName;
                unit.NearCityIsCapital = city:IsCapital();
                unit.NearCityIsOurs = (player:GetID() == playerID);
            end
        end
    end
end
```

---

## 关键数据结构

### 分组实例扩展字段

```lua
instance["isCollapsed"]   -- 是否折叠
instance["CollapsePadding"] -- 折叠后的保留高度
instance["Children"]       -- 子行列表（BRS 新增，用于排序）
instance["Descend"]        -- 排序方向（BRS 新增）
```

### 脏标记系统

```lua
g_DirtyFlag = {
    UNITS    = true,   -- 单位数据需要刷新
    CITIES   = true,   -- 城市数据需要刷新
    -- ... 每页一个标记
};
-- 关闭报表时全部重置为 true
for flag, _ in pairs(g_DirtyFlag) do g_DirtyFlag[flag] = true; end
```

---

## XML 端 Instance 结构

每种单位分组需要两个 Instance：
- **Header Instance**：表头行，含可排序列标签按钮
- **Entry Instance**：数据行，含实际值的 Label/Image

以军事分组为例：

```xml
<!-- 表头 -->
<Instance Name="UnitsMilitaryHeaderInstance">
    <Container ID="Top" Offset="8,0" Size="1123,22">
        <Stack StackGrowth="Right">
            <GridButton ID="UnitTypeButton" Size="50,parent" .../>
            <GridButton ID="UnitNameButton" Size="250,parent" .../>
            <GridButton ID="UnitStatusButton" Size="50,parent" .../>
            <GridButton ID="UnitLevelButton" Size="100,parent" .../>
            <GridButton ID="UnitExpButton" Size="100,parent" .../>
            <GridButton ID="UnitHealthButton" Size="100,parent" .../>
            <GridButton ID="UnitMoveButton" Size="100,parent" .../>
            <GridButton ID="UnitDistrictButton" Size="30,parent" .../>
            <GridButton ID="UnitCityButton" Size="250,parent" .../>
            <GridButton ID="UnitUpgradeButton" Size="30,parent" .../>
            <GridButton ID="UnitMaintenanceButton" Size="35,parent" .../>
        </Stack>
    </Container>
</Instance>

<!-- 数据行 -->
<Instance Name="UnitsMilitaryEntryInstance">
    <Container ID="Top" Offset="8,0" Size="1123,28">
        <Stack StackGrowth="Right">
            <Image ID="UnitType" Size="32,32" />
            <GridButton ID="LookAtButton" ...>
                <Label ID="UnitName" ... />
            </GridButton>
            <Image ID="UnitStatus" Size="22,22" />
            <Label ID="UnitLevel" ... />
            <Label ID="UnitExp" ... />
            <Label ID="UnitHealth" ... />
            <Label ID="UnitMove" ... />
            <Label ID="UnitDistrict" ... />
            <Label ID="UnitCity" ... />
            <Button ID="Upgrade" Hidden="1" ... />
            <Label ID="UnitMaintenance" ... />
        </Stack>
    </Container>
</Instance>
```

---

## 实现模板

```lua
-- ===========================================================================
-- MyMod Report Page — 自定义报表页面
-- 参照 BRSPage_Units.lua 的三函数模式
-- ===========================================================================

-- 全局缓存
m_kMyDataReport = nil;

function GetDataMyReport()
    local playerID = Game.GetLocalPlayer();
    local kDataReport = {};

    -- 采集数据并按分组归类
    -- kDataReport[group_name] = { ID, func, Header, Entry, Name, items = {} }

    return kDataReport;
end

function UpdateMyReportData()
    m_kMyDataReport = GetDataMyReport();
    g_DirtyFlag.MYREPORT = false;
end

function my_sortFunction(descend, type, t, a, b)
    -- 按指定字段比较
    if descend then return aVal > bVal else return aVal < bVal end
end

function ViewMyReportPage()
    if g_DirtyFlag.MYREPORT then UpdateMyReportData(); end
    ResetTabForNewPageContent();

    for groupKey, groupData in spairs(m_kMyDataReport,
        function(t, a, b) return t[b].ID > t[a].ID end
    ) do
        local instance = NewCollapsibleGroupInstance();
        instance.RowHeaderButton:SetText(Locale.Lookup(groupData.Name));
        instance.RowHeaderLabel:SetText("总数: " .. #groupData.items);

        -- 构建表头 + 绑定排序
        local pHeader = {};
        ContextPtr:BuildInstanceForControl(groupData.Header, pHeader,
            instance.ContentStack);
        pHeader.SortButton:RegisterCallback(Mouse.eLClick, function()
            instance.Descend = not instance.Descend;
            sort_items("field", groupKey, instance);
        end);

        -- 渲染数据行
        for _, item in spairs(groupData.items,
            function(t,a,b) return my_sortFunction(false, "name", t, a, b) end
        ) do
            local itemInstance = {};
            ContextPtr:BuildInstanceForControl(groupData.Entry, itemInstance,
                instance.ContentStack);
            -- 填充 common_fields + group_func
            groupData.func(item, itemInstance, groupKey, instance, "name");
            itemInstance.LookAtButton:RegisterCallback(Mouse.eLClick, function()
                Close(); UI.LookAtPlot(item:GetX(), item:GetY());
            end);
        end
        RealizeGroup(instance);
    end
    Controls.Stack:CalculateSize();
    Controls.Scroll:CalculateSize();
end

-- 注册到主报表
-- 在 reportscreen.lua 的 LateInitialize() 中:
-- AddTabSection("LOC_MY_REPORT_TAB", ViewMyReportPage);
```

---

## 注意事项

1. **性能关键：脏标记**：`g_DirtyFlag` 避免每次切换 Tab 都重新采集数据，仅在关闭报表或明确事件触发时重置
2. **spairs 排序迭代器**：Lua 原版 `pairs` 无序，必须用自定义 `spairs` 按 ID 或名称排序
3. **分组 ID 决定显示顺序**：`kUnitDataReport[group_name].ID = 1~9`，`spairs` 按 ID 排序
4. **GameEffects 修饰符采集耗时**：处理 10000+ 修饰符约需 60ms，仅在打开报表时执行一次
5. **修饰符去重**：`IsRegistered(iUnitID)` 检查避免同一修饰符重复注册
6. **RMA 依赖**：修饰符文本使用了 `RMA.FetchAndCacheData()` 获取静态缓存数据
7. **`ContextPtr:BuildInstanceForControl`**：在给定 Stack 容器中动态构建 XML Instance 控件
8. **`Close()` 清除所有脏标记**：确保下次打开报表时数据完全刷新

---

## XML 配合

### XML 文件

| 文件 | 路径 |
|------|------|
| 报表主布局 | `reportscreen.xml` |

`reportscreen.xml` 包含所有报表页面的 UI 结构（~2291 行），涵盖 Tab、折叠组、页眉/条目的 Instance 定义。

### 核心控件 ID 对照表

| 控件 ID | 控件类型 | 用途 |
|---------|---------|------|
| `Main` | Box | 主窗口背景，`Size="1144,759" Color="11,27,40,255"` |
| `CloseButton` | Button | 关闭按钮 |
| `TabContainer` | Container | Tab 按钮容器 |
| `TabAnim` / `TabArrow` | SlideAnim / Image | Tab 切换动画箭头 |
| `Scroll` | ScrollPanel | 主内容滚动区 |
| `Stack` | Stack | 主内容堆叠（所有折叠组挂载点） |
| `CollapseAll` | GridButton | "全部折叠"按钮 |
| `TotalsLabel` | Label | 总计标签 |
| `BottomYieldTotals` | Container | 底部产量总计栏 |
| `BottomResourceTotals` | Container | 底部资源总计栏 |
| `GoldIncome` / `GoldExpense` / `GoldNet` | Label | 金币收入/支出/净值 |
| `FaithIncome` / `FaithNet` | Label | 信仰收入/净值 |
| `StrategicGrid` / `LuxuryGrid` / `BonusGrid` | Grid | 战略/奢侈/加成资源分栏 |
| `StrategicResources` / `LuxuryResources` / `BonusResources` | Stack | 各资源类图标堆叠 |

### 折叠组 Instance 体系

| Instance Name | 用途 |
|--------------|------|
| `GroupInstance` | 可折叠分组行（含折叠动画、ContentStack） |
| `SimpleInstance` | 不可折叠简单行容器 |
| `TabInstance` | 标签按钮 |

### 单位报表页 Instance 对照

| Instance Name | 角色 | 关键子控件 |
|--------------|------|----------|
| `UnitsMilitaryHeaderInstance` | 军事单位表头（12列） | `UnitTypeButton`, `UnitNameButton`, `UnitStatusButton`, `UnitLevelButton`, `UnitExpButton`, `UnitHealthButton`, `UnitMoveButton`, `UnitDistrictButton`, `UnitCityButton`, `UnitUpgradeButton`, `UnitMaintenanceButton` |
| `UnitsMilitaryEntryInstance` | 军事单位数据行 | `UnitType`, `LookAtButton`→`UnitName`, `UnitStatus`, `UnitLevel`, `UnitExp`, `UnitHealth`, `UnitMove`, `UnitDistrict`, `UnitCity`, `Upgrade`, `UnitMaintenance` |
| `UnitsCivilianHeaderInstance` | 平民单位表头 | 含 `UnitChargeButton`, `UnitAlbumsButton` |
| `UnitsTraderHeaderInstance` | 商人表头 | 含 `UnitRouteButton`, `UnitYieldButton` |
| `UnitsReligiousHeaderInstance` | 宗教单位表头 | 含 `UnitSpreadButton` |
| `UnitsGreatPeopleHeaderInstance` | 伟人表头 | 含 `UnitMissionButton` |
| `UnitsSpyHeaderInstance` | 间谍表头 | 含 `UnitMissionButton` |

Entry 版本的子控件与 Header 按钮对应，每列一个 Label/Image。

### 可复用模板：可折叠分组带排序表头

```xml
<Instance Name="GroupInstance">
  <Container ID="Top" Size="1123,10" AutoSize="V">
    <GridButton ID="RowHeaderButton" Offset="0,0" Size="parent,30" Style="RowButton" String="$RowHeaderButton">
      <Label ID="RowHeaderLabel" Anchor="R,C" Offset="50,0" Style="RowButton" String="$RowHeaderString$" Hidden="1" />
    </GridButton>
    <Image ID="RowExpandCheck" Anchor="R,T" Offset="5,5" Size="22,22" Texture="Controls_ExpandButton" />
    <ScrollPanel ID="CollapseScroll" Offset="0,31" Size="parent,20" FullClip="1">
      <SlideAnim ID="CollapseAnim" Start="0,0" Speed="4" Cycle="Once" Stopped="1">
        <Stack ID="ContentStack" Offset="0,0" StackGrowth="Bottom" />
      </SlideAnim>
    </ScrollPanel>
  </Container>
</Instance>
```

Header Instance 模板：每列一个 `Container` + `GridButton`（`Style="ButtonLightWeightSquareGrid"`），按钮 ID 用于 Lua 端绑定排序回调。
Entry Instance 模板：同宽度的 `Stack` 结构，每列一个 `Label`/`Image`/`GridButton`（含 `LookAtButton` 用于定位跳转）。
