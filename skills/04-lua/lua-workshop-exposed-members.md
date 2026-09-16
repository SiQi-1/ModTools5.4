# ExposedMembers 跨 Mod 通信模式（来源：Extended Policy Cards + Better Report Screen）

## 做什么
一个 Mod 通过全局表 `ExposedMembers` 暴露数据和计算函数，另一个 Mod 通过 `Modding.IsModActive()` 检测依赖 Mod 是否活跃，若活跃则从 `ExposedMembers` 获取引用并调用其函数。这是 Civ 6 Mod 之间互相协作的标准方式，避免代码重复。

## 涉及文件

| 文件 | 来源 Mod | 角色 |
|------|---------|------|
| `GovernmentScreen.lua` | Extended Policy Cards (2266952591) | 消费者：读取 BRS 暴露的数据 |
| `GovernmentScreen.xml` | Extended Policy Cards | 消费者：含扩展 UI 元素的 Instance |

## 技术原理

### 生产者端（Better Report Screen）

BRS Mod 在其 Lua 中创建 `ExposedMembers.RMA` 全局表，放置共享函数：

```lua
-- BRS Mod (生产者)
if not ExposedMembers.RMA then ExposedMembers.RMA = {} end
ExposedMembers.RMA.CalculateModifierEffect = function(modifierType, policyType, amount, arg1, arg2)
    -- 计算并返回 modifier 的影响描述字符串
    return calculatedEffectString
end
```

`ExposedMembers` 是游戏提供的全局命名空间，跨所有加载的 Mod 持久存在。它是一个 Lua 全局表，所有 UI 上下文共享。

### 消费者端（Extended Policy Cards）

```lua
-- Extended Policy Cards (消费者)
local isBRSActive:boolean = Modding.IsModActive("6f2888d4-79dc-415f-a8ff-f9d81d7afb53")

-- 如果 BRS 不存在，创建空壳防止 nil 错误
if not ExposedMembers.RMA then ExposedMembers.RMA = {} end
local RMA = ExposedMembers.RMA
```

关键函数使用方式：
```lua
function RealizePolicyCard(cardInstance, policyType)
    -- ... 基础渲染 ...

    if isBRSActive then
        local policyEffect = RMA.CalculateModifierEffect("Policy", policyType, 0, nil, nil)
        -- 将计算结果显示在卡牌上
        if policyEffect ~= "" then
            cardInstance.EffectContainer:SetHide(false)
            cardInstance.Effect:SetText(policyEffect)
            cardInstance.Effect:SetToolTipString(policyEffect)
        else
            cardInstance.EffectContainer:SetHide(true)
        end
    else
        cardInstance.EffectContainer:SetHide(true)
    end
end
```

## 完整模式模板

### 生产者模板

```lua
-- 在 Mod A 的 Lua 中
if not ExposedMembers.MyMod then ExposedMembers.MyMod = {} end
local API = ExposedMembers.MyMod

-- 暴露计算函数
function API.CalculateYieldEffect(objectType, objectID)
    -- 从数据库/游戏状态计算影响值
    local result = ""
    -- ... 计算逻辑 ...
    return result
end

-- 暴露数据
function API.GetModData()
    return {
        Version = 1,
        -- ... 其他数据 ...
    }
end

-- 暴露常量
API.COLOR_HIGHLIGHT = UI.GetColorValueFromHexLiteral(0xFF00FF00)
```

### 消费者模板

```lua
-- 在 Mod B 的 Lua 中
-- 1. 获取 B 自己的 Mod ID（从 .modinfo）
local DEP_MOD_ID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

-- 2. 检测依赖 Mod 是否活跃
local isDepActive = Modding.IsModActive(DEP_MOD_ID)

-- 3. 安全创建空壳
if not ExposedMembers.MyMod then ExposedMembers.MyMod = {} end
local MyModAPI = ExposedMembers.MyMod

-- 4. 使用
function OnSomethingHappened()
    if isDepActive and MyModAPI.CalculateYieldEffect then
        local effect = MyModAPI.CalculateYieldEffect("BUILDING", buildingID)
        -- 在 UI 上显示 effect
    end
end
```

## 设计要点

1. **空壳保护**：消费者必须 `if not ExposedMembers.X then ExposedMembers.X = {} end` 防止生产者未加载时的 nil 错误
2. **IsModActive 检测**：使用 `Modding.IsModActive("Mod GUID")` 判断依赖是否可用，不能只检查 `ExposedMembers` 非空（可能有同名冲突）
3. **Mod GUID 来源**：从 `.modinfo` 的 `<Mod id="...">` 中获取 GUID
4. **函数存在性检查**：调用前检查 `API.FunctionName ~= nil`，因为生产者可能版本不同
5. **命名约定**：`ExposedMembers` 下的命名空间应使用唯一的缩写，避免与其他 Mod 冲突。BRS 用 `RMA`，Extended Policy Cards 用 `RMA` 读取
6. **不可跨线程**：`ExposedMembers` 只在 UI 上下文间共享，不能从 GP 端访问

## 常见应用场景

| 场景 | 说明 |
|------|------|
| 数值计算共享 | 一个 Mod 实现复杂的 modifier 效果计算，其他 Mod 复用 |
| UI 增强 | 一个 Mod 提供基础 UI 框架，其他 Mod 挂载额外显示 |
| 事件转发 | 一个 Mod 监听游戏事件，广播给其他 Mod |
| 配置共享 | 多个 Mod 共享同一份配置数据，避免重复维护 |

## 与 GP↔UI 通信的区别

| 特性 | ExposedMembers | GP↔UI 通信 (GameEvents) |
|------|---------------|----------------------|
| 通信方向 | UI ↔ UI（同侧） | UI ↔ GP（跨线程） |
| 用途 | Mod 间数据/函数共享 | 游戏数据修改请求 |
| 持久性 | 整个游戏会话 | 事件驱动，不持久 |
| 典型场景 | UI 组件复用、Mod 互操作 | UI 请求修改游戏数据 |

## XML 配合

### 涉及的关键 XML 文件

| 文件 | 来源 Mod | 用途 |
|------|---------|------|
| `GovernmentScreen.xml` | Extended Policy Cards (2266952591) | 消费者 XML：含 `EffectContainer` 和 `Effect` 控件，用于展示从 ExposedMembers 获取的计算结果 |

### 核心控件 ID 对照表

| 控件 ID | 类型 | 所在 Instance | 用途 |
|---------|------|-------------|------|
| `EffectContainer` | Grid | PolicyCard | EPC 新增，包裹效果文本，Hidden="1"（默认隐藏，有数据时显示） |
| `Effect` | Label | PolicyCard | 显示从 `ExposedMembers.RMA.CalculateModifierEffect()` 获取的效果文本 |
| `Description` | Label | PolicyCard | 原版政策卡描述 |
| `Title` | Label | PolicyCard | 原版政策卡标题 |
| `Button` | Button | PolicyCard | 原版政策卡点击热区 |

### 关键 XML 模式：预留扩展容器

消费者 XML 中为跨 Mod 数据预留隐藏容器，Lua 根据 `Modding.IsModActive()` 决定是否填充：

```xml
<Instance Name="PolicyCard">
    <Container ID="Content" Size="140,150">
        <Button ID="Button" Size="parent,parent" Alpha="0"/>
        <Image ID="Background" Size="parent,parent">
            <!-- 标题 -->
            <Grid ID="TitleContainer" Anchor="C,T" Size="140,auto" Color="0,0,0,100">
                <Label ID="Title" Anchor="C,T" Offset="0,8" TruncateWidth="120" Align="Center" Style="FontNormal12"/>
            </Grid>

            <!-- 描述 -->
            <Container ID="DescriptionContainer" Size="parent,parent">
                <Label ID="Description" Anchor="L,C" WrapWidth="119" Style="FontNormal12"/>
            </Container>

            <!-- === 跨 Mod 扩展位：隐藏容器，由 ExposedMembers 数据填充 === -->
            <Grid ID="EffectContainer" Anchor="C,B" Size="140,auto" Color="0,0,0,100" AutoSizePadding="0,5" Hidden="1">
                <Label ID="Effect" Anchor="C,B" Offset="0,8" TruncateWidth="120" Align="Center" Style="FontNormal12"/>
            </Grid>
            <!-- === 跨 Mod 扩展位结束 === -->
        </Image>
    </Container>
</Instance>
```

### Lua 配合代码

```lua
-- 如果生产者 Mod 活跃，使用其暴露的数据填充 EffectContainer
if isBRSActive then
    local effect = RMA.CalculateModifierEffect("Policy", policyType, 0, nil, nil)
    if effect ~= "" then
        cardInstance.EffectContainer:SetHide(false)
        cardInstance.Effect:SetText(effect)
        cardInstance.Effect:SetToolTipString(effect)
    else
        cardInstance.EffectContainer:SetHide(true)
    end
else
    cardInstance.EffectContainer:SetHide(true)
end
```
