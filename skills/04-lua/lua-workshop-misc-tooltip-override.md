# ToolTip 覆写模式 (ToolTip Override Pattern)

## 来源
- TechCivicProgressPlus (Firstborn/DeepLogic, id=2604740398) — 增强科技/文化 Tooltip 显示溢出和增强预览
- 通用模式，大量 Mod 使用

## 概述
覆写游戏内置的 ToolTip 生成函数，在不修改游戏核心逻辑的情况下在 Tooltip 中显示额外的 Mod 数据（如溢出值、增强预览、额外产出等）。

## 步骤 1：缓存原始函数

```lua
-- 保存原版 Tooltip 函数
local Base_GetTechnologyToolTip = ToolTipHelper.GetTechnologyToolTip
local Base_GetCivicToolTip = ToolTipHelper.GetCivicToolTip
```

## 步骤 2：覆写 Tooltip 函数

```lua
ToolTipHelper.GetTechnologyToolTip = function(techType, playerId)
    -- 先获取原始 tooltip
    local originalText = Base_GetTechnologyToolTip(techType, playerId)

    -- 获取额外信息
    local extraInfo = GetYourExtraInfo(techType, playerId)

    -- 拼接返回
    return originalText .. "[NEWLINE][NEWLINE]" .. extraInfo
end
```

**注意**：必须返回完整字符串（不是修改原字符串），因为原版函数在每个 tooltip 请求时都会重新生成。

## 步骤 3：注入到全局 Tooltip 生成器表

```lua
-- g_ToolTipGenerators 是 Civ 6 的全局 tooltip 注册表
g_ToolTipGenerators.KIND_TECH = ToolTipHelper.GetTechnologyToolTip
g_ToolTipGenerators.KIND_CIVIC = ToolTipHelper.GetCivicToolTip
```

这样在科技树、市政树、TopPanel 等所有地方鼠标悬停时都会使用新版 Tooltip。

## 步骤 4：完整示例：显示科技溢出

```lua
-- 文件: UI/ToolTipHelper_PlayerYields.lua

-- 缓存原始 tooltip 函数
Base_GetScienceTooltip = GetScienceTooltip

function GetScienceTooltip()
    local original = Base_GetScienceTooltip()

    local localPlayerID = Game.GetLocalPlayer()
    local playerTech = Players[localPlayerID]:GetTechs()
    local scienceYield = playerTech:GetScienceYield()

    if scienceYield > 0 then
        -- 触发溢出计算（由其他 Lua 文件提供）
        ExposedMembers.TechCivicProgress.GetTechOverflow()
        local overflow = ExposedMembers.TechCivicProgress.overflow_tech

        local yield_icon = GameInfo.Yields["YIELD_SCIENCE"].IconString
        original = original .. "[NEWLINE] " ..
            Locale.Lookup("LOC_RESEARCH_OVERFLOW") ..
            Locale.Lookup(" {1_Overflow} {2_Icon} {3_Name}",
                string.format("%.1f", overflow), yield_icon, "")
    end

    return original
end
```

## 步骤 5：完整的科技/市政 ToolTip 覆写（含增强预览）

```lua
-- 缓存原版
Base_GetTechnologyToolTip = ToolTipHelper.GetTechnologyToolTip

ToolTipHelper.GetTechnologyToolTip = function(techType, playerId)
    local tech = GameInfo.Technologies[techType]
    if not tech then return end

    local name = tech.Name
    local cost = tech.Cost
    local progress = 0
    local boosted = false
    local boost_ratio = 0

    if playerId then
        local player = Players[playerId]
        if player then
            local playerTechs = player:GetTechs()
            if playerTechs then
                cost = playerTechs:GetResearchCost(tech.Index)
                progress = playerTechs:GetResearchProgress(tech.Index)
                boosted = playerTechs:HasBoostBeenTriggered(tech.Index)
                boost_ratio = GetBoostRatio(tech.TechnologyType, playerId, true)
            end
        end
    end

    -- 构建 tooltip
    local lines = {}
    table.insert(lines, Locale.ToUpper(name))
    table.insert(lines, Locale.Lookup("{1_Progress}/{2_Cost} {3_Icon} {4_Name}",
        string.format("%.1f", progress), cost,
        GameInfo.Yields["YIELD_SCIENCE"].IconString,
        GameInfo.Yields["YIELD_SCIENCE"].Name))

    -- 增强：显示获得 Eureka 后的估算进度
    if (not boosted) and (boost_ratio > 0) then
        local boosted_progress = math.min(
            progress + math.floor(math.max(cost * boost_ratio / 100.0 - 1, 0)),
            cost
        )
        table.insert(lines, Locale.Lookup("{1_Progress}/{2_Cost} ... ({3_Boost})",
            string.format("%.1f", boosted_progress), cost,
            Locale.Lookup('LOC_ESTIMATED_PROGRESS_AFTER_BOOST')))
    end

    -- 描述
    if not Locale.IsNilOrWhitespace(tech.Description) then
        table.insert(lines, "[NEWLINE]" .. Locale.Lookup(tech.Description))
    end

    -- 解锁内容等（与标准 Tooltip 格式一致）
    -- ...

    return table.concat(lines, "[NEWLINE]")
end

-- 注册
g_ToolTipGenerators.KIND_TECH = ToolTipHelper.GetTechnologyToolTip
```

## 步骤 6：用 GameEffects API 获取 Modifier 加成

```lua
function GetExtraBoostFromModifiers(playerID, isTech)
    -- 缓存：同一回合多次调用不必重新遍历
    local cur = Game.GetCurrentGameTurn()
    if cur == cached_turn then
        return isTech and cached_extra_techboost or cached_extra_civicboost
    end

    cached_turn = cur
    local tech_ratio = 0
    local civic_ratio = 0

    -- 遍历所有 Modifier 实例
    for _, modifierObjID in ipairs(GameEffects.GetModifiers()) do
        local isActive = GameEffects.GetModifierActive(modifierObjID)
        local ownerObjID = GameEffects.GetModifierOwner(modifierObjID)

        -- 检查是否属于当前玩家且激活
        if isActive
           and GameEffects.GetObjectsPlayerId(ownerObjID) == playerID
           and IsOwnerRequirementSetMet(modifierObjID) then

            local modifierDef = GameEffects.GetModifierDefinition(modifierObjID)
            local modifierType = GameInfo.Modifiers[modifierDef.Id].ModifierType
            local modifierTypeRow = GameInfo.DynamicModifiers[modifierType]

            if modifierTypeRow then
                if modifierTypeRow.EffectType == 'EFFECT_ADJUST_TECHNOLOGY_BOOST' then
                    tech_ratio = tech_ratio + modifierDef.Arguments.Amount
                end
                if modifierTypeRow.EffectType == 'EFFECT_ADJUST_CIVIC_BOOST' then
                    civic_ratio = civic_ratio + modifierDef.Arguments.Amount
                end
            end
        end
    end

    cached_extra_techboost = tech_ratio
    cached_extra_civicboost = civic_ratio
    return isTech and cached_extra_techboost or cached_extra_civicboost
end

-- 辅助函数：检查 Modifier 的 OwnerRequirementSet 是否满足
function IsOwnerRequirementSetMet(modifierObjID)
    if modifierObjID and modifierObjID ~= 0 then
        local setId = GameEffects.GetModifierOwnerRequirementSet(modifierObjID)
        if setId then
            return GameEffects.GetRequirementSetState(setId) == "Met"
        end
    end
    return true
end
```

**关键 API**：
- `GameEffects.GetModifiers()` — 获取所有激活的 Modifier 对象
- `GameEffects.GetModifierActive(modObjId)` — Modifier 是否激活
- `GameEffects.GetModifierOwner(modObjId)` — 获取 Modifier 拥有者对象
- `GameEffects.GetObjectsPlayerId(ownerObjId)` — 拥有者对象对应的玩家 ID
- `GameEffects.GetModifierDefinition(modObjId)` — 获取 Modifier 定义（含 ModifierId 和 Arguments）
- `GameEffects.GetModifierOwnerRequirementSet(modObjId)` — 获取 OwnerRequirementSet
- `GameEffects.GetRequirementSetState(setId)` — 检查 RequirementSet 状态

## 步骤 7：加载方式

ToolTip 覆写脚本通常作为 `ImportFiles` 在 UI 上下文加载：

```xml
<InGameActions>
    <ImportFiles id="UpdateToolTip">
        <File>UI/ToolTipLoader_TCP.lua</File>      <!-- 覆写 ToolTipHelper -->
        <File>UI/ToolTipHelper_PlayerYields.lua</File>  <!-- 覆写 TopPanel tooltip -->
    </ImportFiles>
</InGameActions>
```

**ImportFiles vs AddUserInterfaces**：
- `ImportFiles`：在 UI 上下文的所有文件之前加载，可以覆写全局函数
- `AddUserInterfaces`：作为独立 UI 上下文加载，适合有自己 XML 的面板

## 要点总结

1. **缓存原始函数**：`Base_XXX = OriginalFunction`，在覆写中调用 `Base_XXX()` 获取原始内容
2. **返回完整字符串**：不能修改原字符串后返回（原字符串被 Lua GC 可能失效），必须创建新字符串
3. **注册到全局表**：`g_ToolTipGenerators.KIND_XXX = YourFunction` 使系统识别
4. **GameEffects API**：遍历 Modifier 实例的能力很强，但开销大，务必做回合缓存
5. **ImportFiles 加载**：确保在 ToolTipHelper 被使用前完成覆写
6. **格式一致性**：保持与游戏标准 Tooltip 格式一致（使用 Locale.Lookup、[NEWLINE]、[ICON_xxx] 等）

---

## XML 配合

### 文件路径

ToolTip 覆写通常不涉及独立的 XML 文件——ToolTip 是动态生成的字符串，不需要布局控件。但需要在 ModBuddy 项目配置中正确设置加载方式。

### ModBuddy 项目文件配置（.modinfo / .civ6proj）

ToolTip 覆写 Lua 文件通常通过 `ImportFiles` 加载：

```xml
<InGameActions>
    <!-- 方式 A：ImportFiles — 在 UI 上下文预加载，可覆写全局 ToolTip 函数 -->
    <ImportFiles id="ToolTipOverride">
        <File>UI/ToolTipLoader_MyMod.lua</File>
        <File>UI/ToolTipHelper_MyMod.lua</File>
    </ImportFiles>

    <!-- 方式 B：AddUserInterfaces — 独立 UI 上下文（如 ToolTip 需要独立面板） -->
    <AddUserInterfaces id="ToolTipPanel">
        <File>UI/MyToolTipPanel.lua</File>
        <File>UI/MyToolTipPanel.xml</File>
    </AddUserInterfaces>
</InGameActions>
```

### 加载方式对比

| 方式 | 用途 | XML/Lua 依赖 | 适用场景 |
|------|------|------------|---------|
| `ImportFiles` | 在 UI 上下文预加载 | 仅 Lua | ToolTip 函数覆写、全局 Hook |
| `AddUserInterfaces` | 独立 UI 上下文 | Lua + XML | 需要自定义面板/弹窗的 ToolTip |

`ImportFiles` 在 UI 上下文的所有其他文件之前加载，因此可以在 `ToolTipHelper` 使用前完成覆写。

### 如果需要 XML 面板的 ToolTip

当 ToolTip 覆写需要在 ToolTip 中嵌入自定义 UI 控件时，可以创建独立的 XML 面板：

```xml
<!-- MyToolTipPanel.xml -->
<Context>
    <Container ID="MyToolTipPanel" Anchor="C,C" Size="300,auto"
              Texture="Controls_SubContainer" ConsumeMouse="1" Hidden="1">
        <Stack StackGrowth="Down" Padding="4">
            <Label ID="ToolTipTitle" Style="FontFlair16" />
            <Label ID="ToolTipDetail" Style="FontNormal14" WrapWidth="280" />
            <Grid ID="ToolTipYieldGrid" Anchor="L,T" Size="auto,auto">
                <!-- 动态填充的产出行 -->
            </Grid>
        </Stack>
    </Container>
    <Instance Name="ToolTipYieldEntry">
        <Stack StackGrowth="Right" Padding="2">
            <Image ID="YieldIcon" Size="22,22" />
            <Label ID="YieldValue" Style="FontNormal14" />
        </Stack>
    </Instance>
</Context>
```

### ToolTip 覆写的全局注入点

| 注册位置 | 覆写方式 | 影响范围 |
|---------|---------|---------|
| `ToolTipHelper.GetTechnologyToolTip` | 函数覆写 | 科技树、TopPanel、所有科技 Tooltip |
| `ToolTipHelper.GetCivicToolTip` | 函数覆写 | 市政树、TopPanel、所有市政 Tooltip |
| `g_ToolTipGenerators.KIND_XXX` | 表注册 | 对应类型的所有 Tooltip 实例 |
| TopPanel Yield 函数 | 函数覆写 | 顶栏产出 Tooltip |
| Plot ToolTip 函数 | 函数覆写 | 地块 ToolTip（需修改 `PlotInfo.lua`） |
| Unit ToolTip 函数 | 函数覆写 | 单位面板 ToolTip |

### 无 XML 文件的纯 Lua 模式

很多 ToolTip 覆写不需要任何 XML：
- 覆写 `ToolTipHelper` 只涉及字符串拼接，不涉及 UI 控件
- 使用 `Locale.Lookup` + `[ICON_xxx]` + `[NEWLINE]` 格式与标准 ToolTip 一致
- GameEffects API 获取的 Modifier 数据也是纯字符串输出

仅在需要在 ToolTip 中嵌入交互式控件时才需要 XML。
