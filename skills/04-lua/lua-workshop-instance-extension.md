# XML Instance 扩展与条件激活模式（来源：Extended Policy Cards）

## 做什么
在不改变现有 Instance 结构的前提下，向 XML `<Instance>` 定义中添加新的子元素（如额外的 Label、Container），并在 Lua 中根据运行时条件（Mod 是否活跃、数据是否存在）控制这些新元素的显隐和内容填充。这是增强已有 UI 组件的最轻量方式。

## 涉及文件

| 文件 | 来源 Mod | 角色 |
|------|---------|------|
| `GovernmentScreen.xml` | Extended Policy Cards (2266952591) | PolicyCard Instance 含扩展 EffectContainer |
| `GovernmentScreen.lua` | Extended Policy Cards | RealizePolicyCard() 控制显隐和内容 |

## 技术原理

### XML 端：在 Instance 定义中追加元素

原始 Firaxis PolicyCard Instance 定义（简化）：
```xml
<Instance Name="PolicyCard">
    <Container ID="Content" Size="140,150">
        <Image ID="Background" Size="parent,parent" Texture="Governments_DiplomacyCard">
            <Grid ID="TitleContainer" Anchor="C,T" Size="140,auto">
                <Label ID="Title" Anchor="C,T" Offset="0,8" TruncateWidth="120" />
            </Grid>
            <Container ID="DescriptionContainer" Size="parent,parent">
                <Label ID="Description" Anchor="L,C" WrapWidth="119" />
            </Container>
            <!-- 原有的 NewIcon 总是在最后 -->
            <Label ID="NewIcon" Anchor="R,T" Offset="-4,-4" Hidden="1" />
        </Image>
    </Container>
</Instance>
```

Extended Policy Cards 在 DescriptionContainer 和 NewIcon 之间插入了新元素：
```xml
<Instance Name="PolicyCard">
    <Container ID="Content" Size="140,150">
        <Image ID="Background" Size="parent,parent" Texture="Governments_DiplomacyCard">
            <Grid ID="TitleContainer" ...>
                <Label ID="Title" ... />
            </Grid>
            <Container ID="DescriptionContainer" ...>
                <Label ID="Description" ... />
            </Container>
            <!-- ARISTOS: 新增 EffectContainer -->
            <Grid ID="EffectContainer" Anchor="C,B" Size="140,auto"
                  Color="0,0,0,100" AutoSizePadding="0,5" Style="DropShadow4" Hidden="1">
                <Label ID="Effect" Anchor="C,B" Offset="0,8"
                       TruncateWidth="120" ToolTip="" Align="Center"
                       Style="FontNormal12" FontStyle="Stroke" String=""
                       ColorSet="BodyTextCool"/>
                <Image Anchor="C,T" Offset="0,2" Size="parent,2"
                       Texture="Controls_Div6" Color="255,255,255,20"
                       StretchMode="Fill"/>
            </Grid>
            <!-- END ARISTOS -->
            <Label ID="NewIcon" Anchor="R,T" Offset="-4,-4" Hidden="1" />
        </Image>
    </Container>
</Instance>
```

### Lua 端：条件激活

```lua
function RealizePolicyCard(cardInstance, policyType)
    local policy = m_kPolicyCatalogData[policyType]

    -- 基础渲染（标题、描述）
    cardInstance.Title:SetText(policy.Name)
    cardInstance.Description:SetText(policy.Description)
    cardInstance.Background:SetTexture(GetPolicyBGTexture(policyType))

    -- 条件激活扩展元素
    if isBRSActive then
        local policyEffect = RMA.CalculateModifierEffect("Policy", policyType, 0, nil, nil)

        -- 工具提示增强：始终追加计算数据（无论 Effect 是否为空）
        cardInstance.Draggable:SetToolTipString(
            cardName .. "[NEWLINE][NEWLINE]" ..
            policy.Description ..
            (policyEffect == "" and "" or "[NEWLINE][NEWLINE]" .. policyEffect)
        )

        -- 底部容器显示：只在有数据时显示
        if policyEffect ~= "" then
            cardInstance.EffectContainer:SetHide(false)
            cardInstance.Effect:SetText(policyEffect)
            cardInstance.Effect:SetToolTipString(policyEffect)
        else
            cardInstance.EffectContainer:SetHide(true)
        end
    else
        -- 依赖 Mod 不存在：隐藏扩展元素，回退到标准行为
        cardInstance.Draggable:SetToolTipString(
            cardName .. "[NEWLINE][NEWLINE]" .. policy.Description
        )
        cardInstance.EffectContainer:SetHide(true)
    end
end
```

## 关键设计决策

### 1. Hidden="1" 作为默认状态

扩展元素在 XML 中设置 `Hidden="1"`，Lua 中按需显示。这样即使依赖 Mod 不活跃，新元素也不会意外露出空壳。

### 2. 两处位置都放数据

```lua
-- A. 工具提示版本：所有效果信息（可能很长）
cardInstance.Draggable:SetToolTipString(...)

-- B. 底部容器版本：修剪后的效果文本（需要适合 120px 宽度）
cardInstance.Effect:SetText(policyEffect)
```

两种显示方式互为补充：卡牌底部显示截断版本，鼠标悬停时工具提示显示完整信息。

### 3. 分层条件判断

```lua
if isBRSActive then                    -- 第一层：依赖 Mod 是否活跃？
    local effect = CalcEffect(...)
    if effect ~= "" then               -- 第二层：是否有实际数据？
        EffectContainer:SetHide(false) -- 显示
    else
        EffectContainer:SetHide(true)  -- 隐藏
    end
else
    EffectContainer:SetHide(true)      -- 隐藏
end
```

## 模式模板

```xml
<!-- 在目标 Instance 中追加 -->
<Instance Name="ExistingInstanceName">
    <!-- ... 原有元素 ... -->

    <!-- MyMod: 新增扩展元素 -->
    <Container ID="MyExtensionContainer" Anchor="C,B" Size="parent,auto" Hidden="1">
        <Label ID="MyExtensionLabel" Anchor="C,C"
               Style="FontNormal12" FontStyle="Stroke"
               String="" ColorSet="BodyTextCool"/>
    </Container>
    <!-- End MyMod -->
</Instance>
```

```lua
-- 在渲染函数中条件激活
local isExtAvailable = Modding.IsModActive("dependency-mod-guid")

function RealizeExistingItem(itemInstance, itemType)
    -- 基础渲染
    itemInstance.Title:SetText(baseData.Name)
    itemInstance.Description:SetText(baseData.Description)

    -- 扩展渲染
    if isExtAvailable and SomeCondition() then
        local extData = GetExtendedData(itemType)
        if extData ~= "" then
            itemInstance.MyExtensionContainer:SetHide(false)
            itemInstance.MyExtensionLabel:SetText(extData)
        else
            itemInstance.MyExtensionContainer:SetHide(true)
        end
    else
        itemInstance.MyExtensionContainer:SetHide(true)
    end
end
```

## 设计要点

1. **Hidden="1" 默认隐藏**：所有扩展元素默认隐藏，Lua 中按需显示
2. **标记注释**：用 `<!-- ModName -->` / `<!-- End ModName -->` 标记修改区域
3. **多种显示方式**：同时填充卡牌显示区 + 工具提示，确保不同交互方式都能看到扩展数据
4. **依赖 Mod 检测**：用 `Modding.IsModActive()` 而非直接检查 Lua 函数存在性
5. **Instance 复用**：所有通过 InstanceManager 创建的实例自动获得扩展元素，无需额外代码
6. **只加不删**：不要删除原有元素或改变原有 Anchor/Size，避免破坏原版布局

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `GovernmentScreen.xml` | Extended Policy Cards 的替换 XML — 含 PolicyCard + WildCard Instance（均追加 EffectContainer） |

### PolicyCard Instance 扩展前后对照

**Firaxis 原始 PolicyCard（简化）：**
```xml
<Instance Name="PolicyCard">
    <Container ID="Content" Size="140,150">
        <Image ID="Background" Texture="Governments_DiplomacyCard">
            <Grid ID="TitleContainer" ...>
                <Label ID="Title" Anchor="C,T" TruncateWidth="120" />
            </Grid>
            <Container ID="DescriptionContainer" Size="parent,parent">
                <Label ID="Description" Anchor="L,C" WrapWidth="119" />
            </Container>
            <Label ID="NewIcon" Anchor="R,T" Hidden="1" />
        </Image>
    </Container>
</Instance>
```

**Extended Policy Cards 追加后：**
```xml
<Instance Name="PolicyCard">
    <Container ID="Content" Size="140,150">
        <Image ID="Background" Texture="Governments_DiplomacyCard">
            <Grid ID="TitleContainer" ...> ... </Grid>
            <Container ID="DescriptionContainer" ...> ... </Container>
            <!-- ===== EPC 新增 ===== -->
            <Grid ID="EffectContainer" Anchor="C,B" Size="140,auto"
                  Color="0,0,0,100" AutoSizePadding="0,5"
                  Style="DropShadow4" Hidden="1">
                <Label ID="Effect" Anchor="C,B" Offset="0,8"
                       TruncateWidth="120" ToolTip=""
                       Style="FontNormal12" FontStyle="Stroke"
                       ColorSet="BodyTextCool"/>
                <Image Anchor="C,T" Offset="0,2" Size="parent,2"
                       Texture="Controls_Div6" Color="255,255,255,20"/>
            </Grid>
            <!-- ===== EPC 结束 ===== -->
            <Label ID="NewIcon" Anchor="R,T" Hidden="1" />
        </Image>
    </Container>
</Instance>
```

### 新增 EffectContainer 控件明细

| 控件 ID | 类型 | 用途 |
|--------|------|------|
| `EffectContainer` | Grid | 扩展元素根容器（Hidden="1" 默认，Anchor="C,B"，140xauto） |
| `Effect` | Label | 产出文字显示（TruncateWidth="120"，FontNormal12，FontStyle="Stroke"） |

### WildCard Instance 扩展

WildCard PolicyCard 也追加了相同的 EffectContainer：

| 控件 ID | 类型 | 用途 |
|--------|------|------|
| `WildEffectContainer` | Grid | WildCard 的扩展容器（Anchor="R,B"，Offset="0,150"） |
| `WildEffect` | Label | WildCard 的产出文字 |

### Lua 条件激活逻辑

```lua
-- 仅在 Better Report Screen (BRS) 活跃时激活
if isBRSActive then
    local effect = RMA.CalculateModifierEffect("Policy", policyType, 0, nil, nil)
    if effect ~= "" then
        cardInstance.EffectContainer:SetHide(false)  -- XML 默认 Hidden="1"
        cardInstance.Effect:SetText(effect)
        cardInstance.Effect:SetToolTipString(effect)
    else
        cardInstance.EffectContainer:SetHide(true)
    end
else
    cardInstance.EffectContainer:SetHide(true)  -- 确保扩展元素隐藏
end
```

### XML 标记注释约定

在 XML 中用 `<!-- ModName -->` / `<!-- End ModName -->` 注释标记修改区域，方便后续维护和合并冲突处理。

### 复用模式

```xml
<!-- 在目标 Instance 中追加扩展元素的模板 -->
<Grid ID="MyExtensionContainer" Anchor="C,B" Size="parent,auto"
      Color="0,0,0,100" AutoSizePadding="0,5"
      Style="DropShadow4" Hidden="1">
    <Label ID="MyExtensionLabel" Anchor="C,B" Offset="0,8"
           TruncateWidth="120" ToolTip=""
           Style="FontNormal12" FontStyle="Stroke"
           ColorSet="BodyTextCool"/>
    <Image Anchor="C,T" Offset="0,2" Size="parent,2"
           Texture="Controls_Div6" Color="255,255,255,20"/>
</Grid>
```

关键原则：`Hidden="1"` 默认、`Anchor` 不影响原有布局、只追加不删除、用注释标记修改区域。
