# Civ6 ForgeUI XML 控件参考 — 基础/结构

> 分册：由 [lua-xml-controls.md](lua-xml-controls.md) 按主题拆出；覆盖 七、基础视觉控件、八、结构/系统控件。触发：写 Box、Line、WorldAnchor、LuaContext、Instance 时。

## 七、基础视觉控件

## 18. Box

纯色矩形。无纹理、无交互。最简单的基础控件。

| 属性 | 格式 | 说明 |
|------|------|------|
| `Color` | `R,G,B,A` | **核心属性**——纯色填充。`"0,0,0,60"`=半透明暗色 |

```xml
<!-- 暗色背景 -->
<Box Size="parent,parent-10" Color="0,0,0,60" />

<!-- 1px 竖线分隔 -->
<Box Size="1,parent" Anchor="R,C" Color="0,0,0,150" />

<!-- 透明点击拦截区 -->
<Box Size="parent,parent" Color="0,0,0,0" ConsumeMouse="1" />
```

## 20. Line

矢量线段。起点、终点、宽度、颜色。

| 属性 | 格式 | 说明 |
|------|------|------|
| `Start` | `"X,Y"` | 起点（相对父容器） |
| `End` | `"X,Y"` | 终点 |
| `Width` | 整数 | 线宽（通常 `"2"`） |
| `Color` | `R,G,B,A` | 线色 |

```xml
<Line Start="10,1" End="730,1" Color="30,66,96,255" Width="2" />
<Line Start="750,8" End="750,45" Width="2" Color="0,0,0,122" />
```

---

## 八、结构/系统控件

## 21. WorldAnchor

3D 世界空间 → 2D 屏幕坐标锚点。仅在世界控件层使用（CityBanner、UnitFlag 等）。XML 中只写占位，位置由 Lua `SetWorldPosition(x,y,z)` 动态设置。极少直接手写。

## 22. LuaContext

将 Lua 文件绑定到 UI 控件树。**每个 UI 面板的加载入口。**

| 属性 | 格式 | 说明 |
|------|------|------|
| `FileName` | 文件名 | Luas 文件名（无 `.lua` 后缀）。引擎自动加载同名 `.xml` |

```xml
<LuaContext ID="TechTree" FileName="TechTree" Hidden="1" />
```

核心机制：
1. 引擎加载 `TechTree.lua` → 自动加载 `TechTree.xml`
2. `TechTree.lua` 中 `ContextPtr` 指向此上下文根
3. `Hidden="1"` → Lua 通过 `ContextPtr:SetHide(false)` 显示

## 23. Instance

**模板/蓝图——不直接渲染。** 定义一段控件结构供 Lua 通过 `InstanceManager` 在运行时动态克隆。这是批量生成同类控件的核心机制。

| 属性 | 格式 | 说明 |
|------|------|------|
| `Name` | 字符串 | 模板名。Lua 中 `CreateInstance("Name")` |

```xml
<Instance Name="IconOnly">
    <GridButton ID="SelectButton" Style="ButtonDraggableGrid" Size="56,56" Anchor="L,T">
        <Image ID="Icon" StretchMode="None" Size="64,64" Anchor="C,C"/>
        <Label ID="AmountText" Style="FontNormalBold16" Anchor="R,B" Offset="-5,-9"/>
    </GridButton>
</Instance>
```

### Instance 的使用模式（重点）

**① 模板定义（XML 中）**：

Instance 在 XML 中定义一次，包含所有需要的子控件及 ID。这些 ID 在克隆后成为独立副本，可以各自赋值。

**② InstanceManager 创建（Lua 中）**：

```lua
-- 创建 InstanceManager（通常在 OnInit 中）
g_MyIM = InstanceManager:new("MyInstanceName", "SelectButton", Controls.MyParentContainer)

-- 克隆一个实例并赋值
local inst = g_MyIM:CreateInstance()
inst.Icon:SetTexture(iconSheet, offsetX, offsetY)
inst.AmountText:SetText("+5")
inst.SelectButton:RegisterCallback(Mouse.eLClick, OnClick)
```

**③ 带数据的列表构建**：

```lua
g_MyIM:ResetInstances()  -- 清空所有克隆
for _, data in ipairs(dataList) do
    local inst = g_MyIM:CreateInstance()
    inst.Icon:SetTexture(data.icon)
    inst.AmountText:SetText(tostring(data.amount))
end
```

**④ Instance 内控件被创建后才存在**：

```lua
-- 错误：Controls.SelectButton 不存在（这是模板 ID，不是实际控件）
-- 正确：inst = g_MyIM:CreateInstance(); inst.SelectButton:SetHide(false)
```

**⑤ 与 PullDown 的关系**：

PullDown 的 `<InstanceData Name="InstanceOne">` 本质就是 Instance——Lua 通过 PullDown 的 `AddItem()` 等方法自动管理克隆和回收。

### Instance 注意事项

- **Instance 内的 ID 只在克隆后通过 `inst.xxx` 访问**——不是全局 `Controls.xxx`
- **不要手动创建 Instance 内的按钮回调时引用全局变量**——使用闭包捕获 `data` 或 `inst`
- **ResetInstances() 后重新 CreateInstance() 之前，旧引用失效**
- **Instance 定义通常在 XML 文件顶层**（与面板内容同级），便于查找

---

