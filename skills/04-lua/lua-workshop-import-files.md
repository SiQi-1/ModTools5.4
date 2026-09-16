# ImportFiles 完整文件替换模式（来源：Extended Policy Cards / Better Religion Screen）

## 做什么
通过 `.modinfo` 中的 `<ImportFiles>` 动作完全覆盖游戏原生 UI 文件（Lua + XML），用 LoadOrder 控制加载顺序。与 `ReplaceUIScript` 的函数级别覆盖不同，ImportFiles 是**整文件替换**，适合需要大量修改且不适合增量覆盖的场景。

## 涉及文件

| 文件 | 来源 Mod | 角色 |
|------|---------|------|
| `Extended Policy Cards.modinfo` | Extended Policy Cards (2266952591) | ImportFiles 配置 |
| `GovernmentScreen.lua` | Extended Policy Cards | 替换后的完整 Lua（2870 行） |
| `GovernmentScreen.xml` | Extended Policy Cards | 替换后的完整 XML（467 行） |
| `BetterReligionScreen.modinfo` | Better Religion Screen (2145663327) | ImportFiles 配置 |
| `UI/ReligionScreen.lua` | Better Religion Screen | 替换后的完整 Lua（1880 行） |
| `UI/ReligionScreen.xml` | Better Religion Screen | 替换后的完整 XML（419 行） |

## 技术原理

### modinfo 配置

```xml
<!-- Extended Policy Cards — LoadOrder 12000（高优先级，后加载） -->
<InGameActions>
    <ImportFiles id="EPC_IMPORT_FILES">
        <Properties>
            <LoadOrder>12000</LoadOrder>
        </Properties>
        <Items>
            <File>GovernmentScreen.lua</File>
            <File>GovernmentScreen.xml</File>
        </Items>
    </ImportFiles>
</InGameActions>

<Files>
    <File>GovernmentScreen.lua</File>
    <File>GovernmentScreen.xml</File>
</Files>
```

```xml
<!-- Better Religion Screen — LoadOrder 200（低优先级） -->
<InGameActions>
    <ImportFiles id="BRW_Imports">
        <Properties><LoadOrder>200</LoadOrder></Properties>
        <File>UI/ReligionScreen.xml</File>
        <File>UI/ReligionScreen.lua</File>
    </ImportFiles>
</InGameActions>

<Files>
    <File>UI/ReligionScreen.xml</File>
    <File>UI/ReligionScreen.lua</File>
</Files>
```

### 工作原理

1. 游戏启动时扫描所有活跃 Mod 的 `ImportFiles`
2. 按 `LoadOrder` 排序（数值越大越后加载，覆盖前面的同名文件）
3. 将 Mod 中的文件**复制到游戏 UI 文件系统**，覆盖原生文件
4. 文件路径（不含目录前缀）必须与目标游戏 UI 文件名一致

### 关键：文件路径匹配

```
Mod 中的文件:    GovernmentScreen.lua（或 UI/GovernmentScreen.lua 都不影响）
游戏目标文件:   GovernmentScreen.lua  ← 名称必须完全一致
```

注意：ImportFiles 只匹配**文件名**，不关心 Mod 中的子目录结构。`UI/ReligionScreen.lua` 和 `ReligionScreen.lua` 都能覆盖游戏的 `ReligionScreen.lua`。

## ImportFiles vs ReplaceUIScript 对比

| 特性 | ImportFiles | ReplaceUIScript |
|------|-----------|----------------|
| 替换范围 | 整文件 Lua + XML | 单个 Lua 文件 |
| 自定义粒度 | 完全控制所有代码 | 函数级别增量覆盖 |
| 游戏更新兼容 | 差（需手动合并上游改动） | 较好（只覆盖目标函数） |
| 多 Mod 兼容 | 差（后加载的覆盖先加载的） | 好（可链式调用 BASE_） |
| 代码量 | 大（需完整复制原文件） | 小（只写差异部分） |
| 适合场景 | UI 批量改造、新屏幕 | 修正/增强特定函数行为 |

## 从工坊 Mod 学到的实践

### 1. 修改标记注释

在替换文件中用明确注释标记修改：

```lua
-- Extended Policy Cards 的标记方式：
-- ARISTOS
local isBRSActive:boolean = Modding.IsModActive("6f2888d4-79dc-415f-a8ff-f9d81d7afb53")
-- END ARISTOS
```

```xml
<!-- XML 中同样标记修改区域 -->
<!-- ARISTOS -->
<Grid ID="EffectContainer" Anchor="C,B" Size="140,auto" Hidden="1">
    <Label ID="Effect" Anchor="C,B" Offset="0,8" TruncateWidth="120" />
</Grid>
<!-- END ARISTOS -->
```

### 2. FOR OVERRIDE 函数

原版代码通过 `FOR OVERRIDE` 注释标记可扩展点，替换时可以重新实现：

```lua
-- 原版 GovernmentScreen.lua 中的可扩展点：
-- FOR OVERRIDE
function GetPolicyCardSizeX()
    return SIZE_POLICY_CARD_X
end

-- FOR OVERRIDE
function GetEmptyPolicySlotTexture(typeIndex)
    return IMG_POLICYCARD_BY_ROWIDX[typeIndex] .. "_Empty"
end

-- FOR OVERRIDE
function IsReadOnly()
    return false
end

-- FOR OVERRIDE
function ShouldConfirmChanges()
    return true
end
```

### 3. 函数分离便于扩展

原版将函数分离为可单独覆盖的单元，例如：
```lua
-- 分离出的独立函数，可被 DLC/Mod 覆盖
function GetPolicyBGTexture(policyType)
    return PICS_SLOT_TYPE_CARD_BGS[GameInfo.Policies[policyType].GovernmentSlotType]
end

-- Separated into its own function so we can modify icons in DLC / Expansions
function RealizeGovernmentInstance(governmentType, inst, isCivilopediaAvailable)
    -- ...
end
```

### 4. LoadOrder 策略

| LoadOrder | 含义 | 示例 |
|-----------|------|------|
| 12000 | 高优先级，覆盖几乎所有其他 Mod | Extended Policy Cards |
| 200 | 低优先级，允许被其他 Mod 覆盖 | Better Religion Screen |
| 默认(1000) | 中等优先级 | 大多数 Mod |

选择原则：如果 Mod 是"增强/修复"型，用中等 LoadOrder；如果是"完全改造"型，用高 LoadOrder。

## 模式模板

### .modinfo 配置模板

```xml
<Mod id="your-mod-guid" version="1">
    <Properties>
        <Name>Your Mod Name</Name>
        <!-- ... 其他属性 ... -->
    </Properties>
    
    <InGameActions>
        <ImportFiles id="YourMod_Imports">
            <Properties>
                <LoadOrder>1000</LoadOrder>
            </Properties>
            <Items>
                <File>YourScreen.lua</File>
                <File>YourScreen.xml</File>
            </Items>
        </ImportFiles>
        
        <!-- 可选：额外文本文件 -->
        <UpdateText id="YourMod_Text">
            <File>Text/YourMod_en_US.xml</File>
        </UpdateText>
    </InGameActions>
    
    <Files>
        <File>YourScreen.lua</File>
        <File>YourScreen.xml</File>
        <File>Text/YourMod_en_US.xml</File>
    </Files>
</Mod>
```

## 设计要点

1. **可升级性差**：每次游戏更新可能破坏替换文件。如果原版文件改动，需要手动合并
2. **互斥性**：同一目标文件只能有一个 ImportFiles 生效（后加载的覆盖前面的）
3. **使用 LoadOrder 解决冲突**：与依赖 Mod 协调 LoadOrder 值
4. **完整功能复制**：不能只改写部分函数，必须完整包含原版所有逻辑（因为整文件替换）
5. **缺少增量优势**：相比 ReplaceUIScript，无法享受"只写差异"的优势
6. **适合全屏重做**：如果需要同时改 Lua 和 XML，ImportFiles 是唯一选择（ReplaceUIScript 只能替换 Lua）

## XML 配合

### 涉及的关键 XML 文件

| 文件 | 来源 Mod | 用途 |
|------|---------|------|
| `GovernmentScreen.xml` | Extended Policy Cards (2266952591) | 替换后的政策/政体屏幕完整 XML（467 行） |
| `UI/ReligionScreen.xml` | Better Religion Screen (2145663327) | 替换后的宗教屏幕完整 XML（419 行） |

### GovernmentScreen.xml 核心控件

| 控件 ID | 类型 | 用途 |
|---------|------|------|
| **框架** | | |
| `Vignette` | Container | 全屏暗色遮罩 |
| `MainContainer` | Container | 主内容容器（Offset="0,70"） |
| `AlphaAnim` / `RowAnim` | AlphaAnim / SlideAnim | 页面切换动画 |
| **Tab 导航** | | |
| `TabContainer` | Container | Tab 按钮容器 |
| `ButtonMyGovernment` / `ButtonPolicies` / `ButtonGovernments` | GridButton | 三大 Tab 按钮 |
| `TabArrow` | Image | Tab 选中箭头动画 |
| **My Government 面板** | | |
| `GovernmentName` | Label | 当前政体名称 |
| `GovernmentImage` | Image | 政体图片 |
| `GovernmentBonus` | Label | 政体内置加成 |
| `HeritageScrollPanel` / `HeritageBonusStack` | ScrollPanel / Stack | 传承加成列表 |
| **Policies 面板** | | |
| `PolicyCatalog` | Stack | 政策卡目录（水平滚动） |
| `StackMilitary` / `StackEconomic` / `StackDiplomatic` / `StackWildcard` | Container | 四行政策卡槽位 |
| `PolicyScroller` | ScrollPanel | 政策选择滚动区 |
| `FilterPolicyPulldown` | PullDown | 政策过滤下拉 |
| `ConfirmPolicies` / `UnlockPolicies` | GridButton | 确认/解锁政策按钮 |
| **Governments 面板** | | |
| `GovernmentTree` | AlphaAnim | 政体树视图 |
| `GovernmentScroller` | ScrollPanel | 政体树水平滚动 |
| `UnlockGovernments` | GridButton | 解锁政体按钮 |
| **Instances** | | |
| `PolicyCard` | Instance | 政策卡片（含 `EffectContainer` 和 `Effect` 由 EPC 新增） |
| `GovernmentItemInstance` | Instance | 政体条目 |
| `EmptyCard` | Instance | 空政策槽位 |
| `HeritageBonusInstance` | Instance | 传承加成条目 |
| `PolicyTabButtonInstance` | Instance | 过滤 Tab 按钮 |

### ReligionScreen.xml 核心控件

| 控件 ID | 类型 | 用途 |
|---------|------|------|
| **框架** | | |
| `Vignette` | Container | 全屏暗色遮罩 |
| `ModalControls` | Container | 标准 Modal 框架（Style="ModalScreen"） |
| **状态容器（一次性全部隐藏再选择性显示）** | | |
| `WorkingTowards` | Container | 正在努力获取万神殿/宗教 |
| `WorkingTowardsReligion` | Grid | 正在努力获得宗教 |
| `WorkingTowardsPantheon` | Grid | 正在努力获得万神殿 |
| `SelectBeliefs` | Container | 选择信条（万神殿/宗教） |
| `AddBeliefs` | Container | 为已有宗教添加信条 |
| `ChooseReligion` | Container | 创建新宗教 |
| `ViewReligion` | Container | 查看单个宗教详情 |
| `ViewAllReligions` | Container | 查看所有宗教 |
| **按钮** | | |
| `ConfirmBeliefs` / `ReselectBeliefs` / `ReselectReligion` | GridButton | 确认/重选信条/宗教 |
| `AddConfirmBeliefs` / `AddReselectBeliefs` / `AddReselectReligion` | GridButton | 添加模式下的确认/重选 |
| `ConfirmReligion` | GridButton | 确认创建宗教 |
| **Instances** | | |
| `BeliefSlot` | Instance | 可选信条条目（含图标+名称+描述） |
| `ReligionBelief` | Instance | 已装备信条条目 |
| `ReligionBeliefSmall` | Instance | 小号信条条目 |
| `ReligionOption` | Instance | 宗教图标选项按钮 |
| `Religion` | Instance | 宗教概览卡片 |
| `City` | Instance | 城市宗教数据行 |
| `CityFollowers` | Instance | 城市信徒数/压力 |

### 可复用 XML 模板（ImportFiles 全屏替换基本框架）

```xml
<?xml version="1.0" encoding="utf-8"?>
<Context>
    <!-- 全屏遮罩 -->
    <Container ID="Vignette" Style="FullScreenVignetteConsumer" />

    <!-- 主内容容器 -->
    <Container ID="MainContainer" Offset="0,70">
        <!-- 页面切换动画 -->
        <AlphaAnim ID="AlphaAnim" AlphaStart="1.0" AlphaEnd="0" Cycle="Once" Speed="3.4" Function="OutSine" Stopped="1">
            <SlideAnim ID="RowAnim" Start="0,0" End="0,0" Cycle="Once" Speed="2.4" Function="OutSine" Stopped="1">

                <!-- 内容区 -->
                <Stack ID="MainStack" StackGrowth="Right">
                    <!-- 左侧面板 -->
                    <Container ID="LeftPanel" Size="400,700"/>
                    <!-- 右侧面板 -->
                    <Container ID="RightPanel" Size="500,700"/>
                </Stack>

            </SlideAnim>
        </AlphaAnim>
    </Container>

    <!-- Tab 导航 -->
    <Container Anchor="C,T" Offset="0,35" Size="parent,31">
        <Container ID="TabContainer" Size="parent-7,31" Anchor="C,T">
            <GridButton ID="ButtonTab1" Size="200,34" Style="TabButton" String="LOC_TAB_1">
                <AlphaAnim ID="SelectTab1" Size="parent,parent" Speed="4" Hidden="1">
                    <GridButton Size="parent,parent" Style="TabButtonSelected" ConsumeMouseButton="0"/>
                </AlphaAnim>
            </GridButton>
            <GridButton ID="ButtonTab2" Size="200,34" Style="TabButton" String="LOC_TAB_2">
                <AlphaAnim ID="SelectTab2" Size="parent,parent" Speed="4" Hidden="1">
                    <GridButton Size="parent,parent" Style="TabButtonSelected" ConsumeMouseButton="0"/>
                </AlphaAnim>
            </GridButton>
        </Container>
    </Container>

    <Container Style="ModalScreenWide"/>

    <!-- Instances -->
    <Instance Name="CardInstance">
        <Container ID="Content" Size="140,150">
            <Button ID="Button" Size="parent,parent" Alpha="0"/>
            <Image ID="Background" Size="parent,parent">
                <Label ID="Title" Anchor="C,T" Offset="0,8" TruncateWidth="120" Align="Center" Style="FontNormal12"/>
                <Label ID="Description" Anchor="L,C" WrapWidth="119" Style="FontNormal12"/>
                <!-- 自定义扩展区域 -->
                <Grid ID="ExtraInfo" Anchor="C,B" Size="140,auto" Hidden="1">
                    <Label ID="ExtraLabel" Anchor="C,B" Offset="0,8" TruncateWidth="120"/>
                </Grid>
            </Image>
        </Container>
    </Instance>
</Context>
```

### 配合 ImportFiles 的 modinfo 片段

```xml
<InGameActions>
    <ImportFiles id="MyMod_Imports">
        <Properties>
            <LoadOrder>1000</LoadOrder>
        </Properties>
        <Items>
            <File>MyScreen.lua</File>
            <File>MyScreen.xml</File>
        </Items>
    </ImportFiles>
</InGameActions>
<Files>
    <File>MyScreen.lua</File>
    <File>MyScreen.xml</File>
</Files>
```
