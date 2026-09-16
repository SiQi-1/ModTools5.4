# 城市面板资源消费系统（来源：18.0 CityPanel）

## 做什么
在城市详情面板（CityPanel）内嵌入自定义消费按钮，消耗自定义资源（XingHui/XingShu）换取城市产出加成、区域相邻加成或生产力注入。展示了 `UI.RequestPlayerOperation` + GameEvent 的完整 UI → GP 消费管道，以及 InstanceManager 动态列表 + 城市选择联动刷新模式。

## 涉及文件

| 文件 | 角色 |
|------|------|
| `18.0/UI/Arknights_Cute_Leaders_18_CityPanel.lua` | Astesia 面板：消费星辉 → 城市产出 +1（6 种产出可选） |
| `18.0/UI/Arknights_Cute_Leaders_18_CityPanel_2.lua` | Astgenne 面板：消费星数 → 区域相邻加成 20%（动态列表） |
| `18.0/Support/Arknights_Cute_Leaders_18_Support.lua` | 提供 GetAmount_XingHui / GetAmount_XingShu（判断是否可消费） |
| `Scripts/Arknights_Cute_Leaders_18_Scripts.lua` | 监听 `SiqiUbikaChange` GameEvent 执行消费 |
| `Core Mod/Arknights_Cute_Leaders_Core_Mod_GamePlay.lua` | 提供 `SiqiCore_ChangeCityYield` / `SiqiCore_ChangeDistrictYield` / `SiqiCore_AddCityProduction`（核心修改函数） |

## GP 端

### 消费管道

所有消费均通过 `UI.RequestPlayerOperation` → `GameEvents` → GP 执行：

```lua
-- UI 端（CityPanel.lua）
function OnChangeCityYield(PlayerID, CityID, YieldType, Amount)
    local params = {}
    params.OnStart = 'SiqiCore_ChangeCityYield'  -- GP 端 GameEvents 名称
    params.YieldType = YieldType
    params.Amount = Amount
    params.CityID = CityID
    UI.RequestPlayerOperation(PlayerID, PlayerOperations.EXECUTE_SCRIPT, params)
end
```

### GP 端处理函数（Core Mod GamePlay.lua）

```lua
-- 修改城市产出固定值
function SiqiCore_ChangeCityYield(playerID, params)
    SiqiChangeCityYieldChange(playerID, params.CityID, params.YieldType, params.Amount)
end

-- 填充城市生产力
function SiqiCore_AddCityProduction(playerID, params)
    SiqiYieldTypeChange['YIELD_PRODUCTION'](playerID, params.CityID, params.Amount)
end

-- 修改区域产出
function SiqiCore_ChangeDistrictYield(playerID, params)
    SiqiChangeDistrictYieldChange(params.iX, params.iY, params.YieldType, params.Amount)
end
```

### 资源扣除

消费时同步扣除资源（通过 `SiqiUbikaChange` GameEvent）：
```lua
function OnChangeXingHui(PlayerID, Amount)
    params.OnStart = 'SiqiUbikaChange'  -- GP 端 SiqiSupport.ChangeAmount_XingHui
    params.Type = "XingHui"
    params.Amount = Amount               -- 负数 = 消费
    UI.RequestPlayerOperation(PlayerID, PlayerOperations.EXECUTE_SCRIPT, params)
end
```

## UI 端

### 模式一：固定产出按钮（Astesia - CityPanel.lua）

**注入位置：** `/InGame/CityPanel/MainPanel`（偏移 -250, 20）

**6 个产出按钮**（科学/信仰/金币/食物/生产力/文化），每个按钮：
- Tooltip 显示消耗 1 星辉 → 获得 X 点该产出
- 产出量 = `pCity:GetYield(yieldIndex) * 0.1`（城市当前产出的 10%，最少 1）
- 星辉不足时 `SetDisabled(true)`
- 点击触发 `OnChangeCityYield` → `OnChangeXingHui(-1)` → `Refresh()`

**额外功能：生产力注入按钮**
```lua
-- 消耗 1 星辉 → 注入当前生产任务 20% 成本的生产力
local progressNeeded = productiondata.cost * 0.2
params.OnStart = 'SiqiCore_AddCityProduction'
```

**刷新时机：**
```lua
Events.CitySelectionChanged.Add(OnSiqiCitySelectionChanged)   -- 切换城市
Events.CityFocusChanged.Add(OnRefresh)
Events.CityInitialized.Add(OnRefresh)
Events.CityProductionChanged.Add(OnRefresh)
Events.CityWorkerChanged.Add(OnRefresh)
Events.PlayerTurnActivated.Add(OnRefresh)
Events.GamePropertyChanged.Add(OnRefresh)                       -- 资源变化
```

### 模式二：动态区域列表（Astgenne - CityPanel_2.lua）

**注入位置：** `/InGame/CityPanel/MainPanel`（偏移 -330, 20）

**核心：InstanceManager 动态生成区域列表**

```lua
local m_SiqiAstGenneIM = InstanceManager:new("SiqiAstGenneSlot", "SiqiAstGenneSelect", Controls.SiqiUbikaStack)
```

**逻辑流程：**

1. `Refresh()` 被调用时：
   - 获取当前城市所有已完成区域
   - 过滤出有相邻加成的区域（通过 `Siqi_GetYieldBonus` 查询自定义表）
   - 用 `m_SiqiAstGenneIM:DestroyInstances()` + `ResetInstances()` 重建列表
   - 每个区域生成一个 instance，显示：图标、名称、当前相邻加成值

2. 每项显示三行文本：
   - Text1: 区域名 + 状态（未建成/被掠夺/星数不足 显示红色；正常 显示绿色）
   - Text2: 当前相邻加成值（如 `+3 [ICON_SCIENCE]`）
   - Text3: 消耗 + 收益（如 `-1[ICON_SIQI_XINGSHU] +1 [ICON_SCIENCE]`）

3. 点击区域按钮：
   ```lua
   OnChangeDistrictYield(playerID, district)
   -- → params.OnStart = 'SiqiCore_ChangeDistrictYield'
   -- → Amount = math.ceil(district.AdjacencyBonus * 0.2)  -- 相邻加成的 20%，最少 1
   -- → OnChangeXingShu(playerID, -1)  -- 扣除 1 星数
   ```

**禁用条件：**
```lua
function Disable(district)
    return (not district.isBuilt) or (district.isPillaged) or (SiqiSupport.GetAmount_XingShu(Game.GetLocalPlayer()) < 1)
end
```

**空列表处理：** 当城市无符合条件的区域时，显示占位 instance（红色文字 "无可用区域"）。

## 与 WorldTracker 的联动

CityPanel 消费资源后：
```
CityPanel: OnChangeXingHui(playerID, -1)
  → GP: SiqiSupport.ChangeAmount_XingHui(playerID, -1)
    → pPlayer:SetProperty("Siqi_XingHui", newValue)
      → Events.GamePropertyChanged 自动触发
        → WorldTracker: SiqiRefresh() 更新显示
        → CityPanel: OnRefresh() 更新按钮禁用状态
```

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `UI/Arknights_Cute_Leaders_18_CityPanel.xml` | Astesia（星辉消费）面板：6 产出按钮 + 生产力注入按钮 |
| `UI/Arknights_Cute_Leaders_18_CityPanel_2.xml` | Astgenne（星数消费）面板：动态区域列表 + InstanceManager 模板 |
| `Arknights_Cute_Leaders_18_Configs.sql` | PlayerItems + GameCapabilities（XingHui/XingShu 属性注册） |
| `Arknights_Cute_Leaders_18_Modifiers.sql` | 区域产出 Modifier 链定义 |
| `Arknights_Cute_Leaders_18_Adjacents.sql` | 自定义相邻加成数据表 |

### 控件 ID 与 Lua Controls.xxx 对照

#### Arknights_Cute_Leaders_18_CityPanel.xml（Astesia 星辉消费 — 固定产出按钮）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `SiqiUbikaGrid` | Grid | `Controls.SiqiUbikaGrid` | 外层容器（160x160，Hidden="1"） |
| `SiqiUbikaYieldScienceButton` | Button | `Controls.SiqiUbikaYieldScienceButton` | 科技产出 +1 |
| `SiqiUbikaYieldCultureButton` | Button | `Controls.SiqiUbikaYieldCultureButton` | 文化产出 +1 |
| `SiqiUbikaYieldFaithButton` | Button | `Controls.SiqiUbikaYieldFaithButton` | 信仰产出 +1 |
| `SiqiUbikaYieldGoldButton` | Button | `Controls.SiqiUbikaYieldGoldButton` | 金币产出 +1 |
| `SiqiUbikaYieldProductionButton` | Button | `Controls.SiqiUbikaYieldProductionButton` | 生产力产出 +1 |
| `SiqiUbikaYieldFoodButton` | Button | `Controls.SiqiUbikaYieldFoodButton` | 食物产出 +1 |
| `SiqiUbikaProductionButton` | GridButton | `Controls.SiqiUbikaProductionButton` | 生产力注入按钮（MainButton 样式） |
| `SiqiUbikaProductionButtonLabel` | Label | — | 注入按钮文本 |

**布局：** 6 个产出按钮分两行（3+3 Stack），下方 1 个生产力注入按钮。

#### Arknights_Cute_Leaders_18_CityPanel_2.xml（Astgenne 星数消费 — 动态区域列表）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `SiqiUbikaGrid` | Grid | `Controls.SiqiUbikaGrid` | 外层容器（240x240，Hidden="1"） |
| `SiqiUbikaContainer` | Container | `Controls.SiqiUbikaContainer` | 内容容器 |
| `SiqiUbikaScrollPanel` | ScrollPanel | `Controls.SiqiUbikaScrollPanel` | 区域列表滚动面板 |
| `SiqiUbikaStack` | Stack | `Controls.SiqiUbikaStack` | 区域列表挂载点（InstanceManager 父容器） |
| `SiqiUbikaProductionButton` | GridButton | `Controls.SiqiUbikaProductionButton` | 区域产出注入按钮 |

**Instance 模板：**

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `SiqiAstGenneSlot` | 单个区域条目（GridButton 256x64） | `SiqiAstGenneSelect`(GridButton), `SiqiAstGenneIcons`(Image, 50x50), `SiqiAstGenneText1`(Label, 区域名+状态), `SiqiAstGenneText2`(Label, 当前相邻加成值), `SiqiAstGenneText3`(Label, 消耗+收益) |

**挂载模式（两套面板共用）：**
```lua
-- CityPanel 注入到 "/InGame/CityPanel/MainPanel"
function Initialize()
    local pContext = ContextPtr:LookUpControl("/InGame/CityPanel/MainPanel")
    if pContext then
        Controls.SiqiUbikaGrid:ChangeParent(pContext)
        Controls.SiqiUbikaGrid:SetOffsetX(-250)  -- Astesia / Astgenne 偏移量不同
    end
    Events.CitySelectionChanged.Add(OnSiqiCitySelectionChanged)
end
Events.LoadGameViewStateDone.Add(Initialize)
```

### SQL 必需表

```sql
-- 区域相邻加成自定义表（Adjacents.sql）
-- 存储各区域的当前产出加成值，由 SQL Modifier 计算填入，UI 读取展示

-- Player Property 注册（Configs.sql）
INSERT INTO GameCapabilities (Property, ...) VALUES
    ('Siqi_XingHui', ...),    -- 星辉资源
    ('Siqi_XingShu', ...);    -- 星数资源
```

### 添加新消费按钮模板

```xml
<!-- CityPanel 中新增消费按钮 -->
<Grid ID="NewCustomGrid" Anchor="L,B" Size="160,160" Texture="UnitPanel_SpecialActionsFrame"
      SliceCorner="5,10" ConsumeMouse="1" Hidden="1">
    <Container Anchor="C,T" Size="parent,parent" Offset="0,0">
        <Grid Offset="-4,-4" Size="parent+8,parent+8" Style="ScreenFrame"/>
        <Stack StackGrowth="Down" Padding="3" Anchor="C,C" Offset="0,0">
            <GridButton ID="NewCustomButton" Anchor="C,T" Size="parent,33" Style="MainButton">
                <Label ID="NewCustomButtonLabel" Anchor="C,C" Offset="0,0"
                       Style="FontNormal18" ColorSet="ResFaithLabelCS" String="LOC_NEW_BUTTON"/>
            </GridButton>
        </Stack>
    </Container>
</Grid>
```

```lua
-- Lua 端注册
Controls.NewCustomButton:RegisterCallback(Mouse.eLClick, function()
    OnCustomConsume(playerID, CityID)
end)
```

## 设计要点

1. **父面板注入**：通过 `ContextPtr:LookUpControl("/InGame/CityPanel/MainPanel")` 找到面板，`ChangeParent` + `SetOffset` 定位
2. **按钮状态实时**：每次 Refresh 都重新计算 `XinghuiAmount < 1` → `SetDisabled`
3. **消费前校验**：在 UI 端通过 `SiqiSupport.GetAmount_XingHui()` 检查余额 → 按钮禁用，双重保险
4. **InstanceManager 重建模式**：`DestroyInstances()` + `ResetInstances()` + `GetInstance()` 循环 — 每次 Refresh 都完全重建列表
5. **城市产出关联**：产出收益 = 城市当前产出 * 0.1，鼓励在高产出城市消费
6. **点击回调闭包捕获**：`function() OnChangeCityYield(playerID, CityID, YieldType, amount) end` — 需要闭包捕获当前的 playerID/CityID/YieldType
