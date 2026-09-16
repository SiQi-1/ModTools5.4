# 动态 InstanceManager：按需创建与缓存模式（来源：Better Religion Screen）

## 做什么
在运行时对父控件动态创建 `InstanceManager`，创建后缓存到父控件的数据字段上，下次使用时直接 `ResetInstances` 复用。这解决了"需要在父控件内部嵌套子列表，但子列表结构在编写 XML 时无法确定"的问题。

## 涉及文件

| 文件 | 来源 Mod | 角色 |
|------|---------|------|
| `ReligionScreen.lua` | Better Religion Screen (2145663327) | 多处使用此模式 |
| `ReligionScreen.xml` | Better Religion Screen | 含 City / Religion 等 Instance 定义 |

## 技术原理

### 问题场景

城市列表中的每个城市行需要展示：
- 城市名称、所属文明
- 万神殿信条名称和描述
- 每个宗教在该城市的信徒数和宗教压力

但宗教数量在运行时才知道（取决于本局游戏有多少宗教被创建），所以无法在 XML 中静态定义每个城市行内的"信徒列数"。

### 解决方案

在 ViewReligion() 中为每个城市行动态创建 `CityFollowers` 的 InstanceManager：

```lua
-- 核心模式代码
for _, city in ipairs(cities) do
    local cityInst = m_CitiesIM:GetInstance()
    -- ... 填充城市基础数据 ...

    -- 尝试获取已缓存的 IM
    local cityFollowersIM = cityInst[DATA_FIELD_FOLLOWERS_IM]

    if cityFollowersIM ~= nil then
        -- 已存在：直接重用
        cityFollowersIM:ResetInstances()
    else
        -- 不存在：创建新的并缓存
        cityFollowersIM = InstanceManager:new(
            "CityFollowers",            -- XML Instance 名称
            "BG",                        -- 子控件 ID（子控件挂载到哪个父控件下）
            cityInst.CityFollowers      -- 父控件
        )
        cityInst[DATA_FIELD_FOLLOWERS_IM] = cityFollowersIM  -- 缓存
    end

    -- 现在为每个宗教创建一列数据
    for i, religionEntry in ipairs(m_ReligionIcons) do
        local followersInst = cityFollowersIM:GetInstance()
        followersInst.BG:SetOffsetX(calculateOffset(i))
        followersInst.BG:SetSizeX(bucketSize)

        if city.Followers[religionEntry.Religion] ~= nil then
            followersInst.Followers:SetText(city.Followers[religionEntry.Religion])
        else
            followersInst.Followers:SetText("-")
        end
        -- ... 更多数据填充 ...
    end
end
```

### 同时用于"查看所有宗教"面板

同样模式用于宗教列表中的信条子列表：

```lua
function ViewAllReligions()
    -- ...
    for _, religionInfo in ipairs(allReligions) do
        local religionInst = m_ReligionsIM:GetInstance()
        -- ... 填充宗教基础数据 ...

        -- 尝试获取已缓存的信条 IM
        local beliefsIM = religionInst[DATA_FIELD_BELIEFS_IM]
        if beliefsIM ~= nil then
            beliefsIM:ResetInstances()
        else
            beliefsIM = InstanceManager:new(
                "ReligionBeliefSmall",
                "BeliefBG",
                religionInst.Beliefs
            )
            religionInst[DATA_FIELD_BELIEFS_IM] = beliefsIM
        end

        -- 为每个信条创建一行
        for _, belief in ipairs(religionInfo.Beliefs) do
            local beliefInst = beliefsIM:GetInstance()
            local beliefData = GameInfo.Beliefs[belief]
            beliefInst.BeliefLabel:SetText(...)
            beliefInst.BeliefIcon:SetTexture(...)
        end

        -- 重新计算尺寸
        religionInst.Beliefs:CalculateSize()
        religionInst.Beliefs:ReprocessAnchoring()
    end
end
```

### 涉及的字段常量

```lua
local DATA_FIELD_FOLLOWERS_IM = "FollowersIM"
local DATA_FIELD_BELIEFS_IM = "BeliefsIM"
```

### 涉及的 XML Instance

```xml
<!-- 城市行 —— 外层的 CityFollowers 容器 -->
<Instance Name="City">
    <Grid ID="CityBG" Texture="Controls_SlotCap" Size="960,auto">
        <Label ID="CityName" ... />
        <Label ID="CivName" ... />
        <!-- 动态创建 CityFollowers 实例将挂载到这个 Container 下 -->
        <Container ID="CityFollowers" Size="280,auto" Offset="340,0">
            <Grid ID="BG" Texture="Controls_Slot" Size="310,auto">
                <Label ID="CityPantheon" ... />
            </Grid>
        </Container>
    </Grid>
</Instance>

<!-- 每个宗教的信徒/压力子行 —— 被动态 IM 使用 -->
<Instance Name="CityFollowers">
    <Grid ID="BG" Texture="Controls_Slot" Size="1,45">
        <Label ID="Followers" Anchor="C,C" Offset="0,-8" />
        <Label ID="Pressure"  Anchor="C,C" Offset="0,10" />
    </Grid>
</Instance>

<!-- 小型信条行 —— 被宗教列表面板的动态 IM 使用 -->
<Instance Name="ReligionBeliefSmall">
    <Grid ID="BeliefBG" Texture="Religion_BeliefSlotSmall" Size="450,auto">
        <Image ID="BeliefIcon" Size="32,32" Texture="BeliefsPantheon32" />
        <Label ID="BeliefLabel" Offset="40,-1" Size="400" />
    </Grid>
</Instance>
```

## 模式模板

```lua
-- ===========================================================================
-- 动态 InstanceManager 模式模板
-- ===========================================================================

include("InstanceManager")

-- 数据字段名常量
local DATA_FIELD_SUB_IM = "SubIM"

-- 外层数据循环
function RenderParentList()
    m_ParentIM:ResetInstances()

    for _, parentItem in ipairs(parentItems) do
        local parentInst = m_ParentIM:GetInstance()

        -- 填充父级数据
        parentInst.Title:SetText(parentItem.Name)

        -- 获取或创建子 IM
        local subIM = parentInst[DATA_FIELD_SUB_IM]
        if subIM ~= nil then
            subIM:ResetInstances()
        else
            subIM = InstanceManager:new(
                "SubItem",                   -- XML Instance 名称
                "SubItemRoot",               -- 子控件在父 Instance 中的 ID
                parentInst.SubItemContainer  -- 父控件
            )
            parentInst[DATA_FIELD_SUB_IM] = subIM
        end

        -- 填充子级数据
        for _, subItem in ipairs(parentItem.Children) do
            local subInst = subIM:GetInstance()
            subInst.SubLabel:SetText(subItem.Name)
            subInst.SubValue:SetText(subItem.Value)

            -- 动态定位
            subInst.SubItemRoot:SetOffsetX(calculateXOffset(subItem))
            subInst.SubItemRoot:SetSizeX(calculateWidth(subItem))
        end

        -- 关键：子 Stack 填充后重新计算尺寸和锚定
        parentInst.SubItemContainer:CalculateSize()
        parentInst.SubItemContainer:ReprocessAnchoring()
        parentInst.ParentStack:CalculateSize()
        parentInst.ParentStack:ReprocessAnchoring()
    end

    -- 最外层容器也要重新计算
    Controls.ParentScrollbar:CalculateSize()
end
```

## 设计要点

1. **缓存检查**：每次先检查 `parentInst[DATA_FIELD] ~= nil`，存在则 `ResetInstances`，不存在则创建新的
2. **数据字段命名**：用常量 `DATA_FIELD_XXX_IM` 而非直接字面量，防止拼写错误
3. **CalculateSize + ReprocessAnchoring**：填充子数据后必须调用，否则控件尺寸不会更新，导致重叠或截断
4. **动态定位**：子控件用 `SetOffsetX` / `SetSizeX` 根据运行时数据动态定位（如按宗教数量均分宽度）
5. **ScrollPanel 也要重算**：如果列表在 ScrollPanel 内，外层 ScrollPanel 的 `CalculateSize` 也需要调用

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `UI/ReligionScreen.xml` | Better Religion Screen 完整布局 — 含 City / ReligionBeliefSmall / BeliefSlot 等 Instance 定义 |

### 相关 Instance 定义

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `City` | 城市行条目 | `CityBG`(Grid, 960xauto, "Controls_SlotCap"), `CityName`(Label), `CivName`(Label), `CityFollowers`(Container, 280xauto) — 内部 `BG`(Grid) + `CityPantheon`(Label) |
| `CityFollowers` | 动态创建的宗教信徒子列 | `BG`(Grid, 1x45, "Controls_Slot"), `Followers`(Label, "C,C", Offset="0,-8"), `Pressure`(Label, "C,C", Offset="0,10") |
| `ReligionBeliefSmall` | 宗教信条小条目 | `BeliefBG`(Grid, 450xauto, "Religion_BeliefSlotSmall"), `BeliefIcon`(Image, 32x32, "BeliefsPantheon32"), `BeliefLabel`(Label, Offset="40,-1", 400px) |

### City Instance 中的子容器

```xml
<Instance Name="City">
  <Grid ID="CityBG" Texture="Controls_SlotCap" Size="960,auto">
    <Label ID="CityName" ... />
    <Label ID="CivName" ... />
    <!-- 动态创建的 CityFollowers 实例将挂载到这个 Container 下 -->
    <Container ID="CityFollowers" Size="280,auto" Offset="340,0">
      <Grid ID="BG" Texture="Controls_Slot" Size="310,auto">
        <Label ID="CityPantheon" ... />
      </Grid>
    </Container>
  </Grid>
</Instance>
```

### 动态 IM 创建关键路径

```lua
-- CityFollowers IM 的父控件 = cityInst.CityFollowers（即 City Instance 的 CityFollowers Container）
cityFollowersIM = InstanceManager:new("CityFollowers", "BG", cityInst.CityFollowers)

-- ReligionBeliefSmall IM 的父控件 = religionInst.Beliefs（一个宗教 Instance 的 Beliefs 子容器）
beliefsIM = InstanceManager:new("ReligionBeliefSmall", "BeliefBG", religionInst.Beliefs)
```

### CityFollowers Instance 细节

```xml
<Instance Name="CityFollowers">
  <Grid ID="BG" Texture="Controls_Slot" Size="1,45">
    <Label ID="Followers" Anchor="C,C" Offset="0,-8" />
    <Label ID="Pressure"  Anchor="C,C" Offset="0,10" />
  </Grid>
</Instance>
```

宽度 `Size="1,45"` 是因为每个宗教列的实际宽度在 Lua 中动态计算（根据宗教数量均分 `CityFollowers` 的 280px），通过 `followersInst.BG:SetSizeX(bucketSize)` 设置。

### 数据字段常量对应

| Lua 常量 | 值 | 存储的 IM |
|---------|-----|----------|
| `DATA_FIELD_FOLLOWERS_IM` | `"FollowersIM"` | `cityInst` 上的 CityFollowers InstanceManager |
| `DATA_FIELD_BELIEFS_IM` | `"BeliefsIM"` | `religionInst` 上的 ReligionBeliefSmall InstanceManager |

这两个常量确保每次渲染时能通过 `parentInst[DATA_FIELD]` 检查是否已有缓存的 IM，避免重复创建。
