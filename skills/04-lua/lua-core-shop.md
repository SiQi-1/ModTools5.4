# 双货币商店系统（来源：Core Mod）

## 做什么
实现一个完整的双货币商店系统：金币商店（消耗 Gold）+ 费用商店（消耗自定义 Cost 资源），含商品随机刷新/购买/升级/唯一商品过滤，支持三种商品类型（lua/modifier/property），通过 GameEvents + UI.RequestPlayerOperation 完成 GP-UI 安全通信。

## 涉及文件

| 文件 | 角色 |
|------|------|
| `Support/Arknights_Cute_Leaders_Core_Mod_ShopSupport.lua` | 核心：Commodity 对象 + Item 栏位 + GoldShop/CostShop CRUD（772行） |
| `Lua/Arknights_Cute_Leaders_Core_Mod_Shop.lua` | GP 端：回合刷新、PlayerTurnActivated 触发 |
| `Lua/Arknights_Cute_Leaders_Core_Mod_Shop_LuaEvent.lua` | GP 端：Lua 类型商品的购买处理函数表 |
| `UI/Arknights_Cute_Leaders_Core_Mod_ShopPanel.lua` | UI 端：双 Tab 面板 + InstanceManager 列表 + 购买按钮 |
| `UI/Arknights_Cute_Leaders_Core_Mod_ShopPanel.xml` | UI 端：面板布局 + Item 模板 |

## 架构概览

```
SQL 商品定义表 (Siqi_Core_GoldShop)
        ↓ 读取
ShopSupport.lua (GP+UI 共用)
  ├── SiqiCommodity  — 商品对象（参数初始化、购买执行、数据压缩）
  ├── SiqiItem       — 商品栏（等级、刷新、购买状态）
  ├── SiqiGoldShop   — 金币商店 CRUD（Player Property 持久化）
  └── SiqiCostShop   — 费用商店 CRUD（Player Property 持久化）
        ↓
Shop.lua (GP)          ShopPanel.lua (UI)
  └─ 回合驱动刷新        └─ InstanceManager 列表渲染 + 购买按钮
        ↓                       ↓
GameEvents.OnSiqiCoreShopCommodityBought  ←  UI.RequestPlayerOperation
        ↓
  Shop_LuaEvent.lua (GP)
    └─ LuaEvents.SiqiCore_GoldShopCommodityBought → 执行购买效果
```

## 核心对象

### 1. Commodity — 商品对象

每种商品由 SQL 表 `Siqi_Core_GoldShop` 定义一行。运行时从表读取元数据 + 随机参数生成。

```lua
-- 创建商品对象（从 SQL 元数据 + 随机初始化）
local Commodity = SiqiCommodity:new(playerID, ID)
Commodity:Init()  -- 随机 Amount + 解析参数值

-- 核心方法
Commodity:GetCost()        -- 总费用 = Cost * Amount
Commodity:GetDescription() -- 根据参数值动态拼接描述文本
Commodity:BoughtCommodity() -- 执行购买（根据 Type 分支）
Commodity:GetZip()         -- 序列化为压缩数据表（存储用）
```

### 商品 SQL 定义表结构

| 列 | 说明 | 示例 |
|----|------|------|
| `ID` | 商品ID | `'ID0'` |
| `Level` | 等级（1-9 金币商店，10+ 费用商店） | `1`, `11` |
| `Name` | LOC 名称 | `'LOC_SIQI_SHOP_ITEM_001'` |
| `Description` | LOC 描述（支持 `{1}` `{2}` 占位） | `'LOC_SIQI_SHOP_DESC_001'` |
| `Type` | 执行类型 | `'lua'` / `'modifier'` / `'property'` |
| `Cost` | 基础单价 | `100` |
| `MinAmount/MaxAmount` | 随机数量范围 | `1`, `3` |
| `IsCity` | 是否关联城市 | `true`/`false` |
| `IsOnce` | 是否唯一商品（只能买一次） | `true`/`false` |
| `ModifierId` | Type=modifier 时的 Modifier ID | `'MODIFIER_xxx'` |
| `PropertyName` | Type=property 时的 Property 名 | `'SIQI_CORE_PROP_xxx'` |
| `Parameter1-4` | 动态参数类型 | `'CITYNAME'` / `'YIELDNAME'` / `'NUM'` |

### 动态参数系统

Parameter 字段不是值本身，而是**参数类型标识**。Init() 时根据类型解析为实际值：

| 参数类型 | 说明 | GetValue 逻辑 |
|---------|------|-------------|
| `CITYNAME` | 随机城市ID | 从玩家城市中随机抽一个 |
| `YIELDNAME` | 随机产出类型 | 从 6 种 Yield 中随机抽 |
| `GREAYPERSON` | 随机伟人类型 | 从所有 GreatPersonClasses 随机抽 |
| `STRATEGICNAME` | 随机战略资源 | 从 RESOURCECLASS_STRATEGIC 随机抽 |
| `COMBATUNITNAME` | 随机军事单位 | 按 Cost 上限随机抽 |
| `UNIT_xx` | 固定单位类型 | 直接返回该 UNIT 字符串 |
| `NUM` | 本商品随机数量 | 返回 self.Amount |

参数数值后缀（如 `COMBATUNITNAME50`）中的数字作为 `GetValue(self, number)` 的第二个参数传入。

### 商品购买分流（BoughtCommodity）

```lua
function SiqiCommodity:BoughtCommodity()
    if self.IsOnce then
        -- 记录已购买的唯品ID到 Player Property
    end
    if self.Type == 'lua' then
        LuaEvents.SiqiCore_GoldShopCommodityBought(playerID, ID, Amount, values)
    elseif self.Type == 'modifier' and self.IsCity then
        pCity:AttachModifierByID(self.ModifierId)  -- × Amount 次
    elseif self.Type == 'property' and self.IsCity then
        pCity:SetProperty(propName, oldValue + Amount)
    elseif self.Type == 'modifier' and not self.IsCity then
        pPlayer:AttachModifierByID(self.ModifierId)  -- × Amount 次
    elseif self.Type == 'property' and not self.IsCity then
        pPlayer:SetProperty(propName, oldValue + Amount)
    end
    -- 扣费：金币商店扣 Gold，费用商店扣 Cost
end
```

### 2. Item — 商品栏位

每个商店有固定数量的栏位，每个栏位有等级、当前商品、购买状态。使用 `CommodityZip` 压缩数据持久化存储。

```lua
Item = {
    CommodityZip = {ID, Amount, value1-4},  -- 商品压缩数据（存 Player Property）
    HadBought = false,                       -- 本栏位是否已购买
    itemID = 1,                              -- 栏位序号
    level = 1,                               -- 栏位等级（决定刷出的商品范围）
}
```

## 双商店设计

### 金币商店 (SiqiGoldShop)

- 8 个栏位，初始等级 `{1,1,1,1,2,2,3,3}`
- 消耗 Gold（`pPlayer:GetTreasury():ChangeGoldBalance(-Cost)`）
- Level 1-9 的商品

### 费用商店 (SiqiCostShop)

- 10 个栏位，初始等级 `{11,11,11,11,12,12,13,13,13,13}`
- 消耗自定义 Cost（`SiqiCostShop.ChangeCost(playerID, -Cost)`）
- Level 10+ 的商品
- Cost 余额存储在 Player Property `SIQI_CORE_COST_TREASURY`
- 每回合自动 +10 Cost

### 商店数据持久化

```lua
-- 金币商店存 Player Property
pPlayer:SetProperty("SIQI_CORE_GOLD_SHOP_ITEMS", Items)

-- 费用商店存 Player Property
pPlayer:SetProperty("SIQI_CORE_COST_SHOP_ITEMS", Items)

-- 已购买的唯品ID列表
pPlayer:SetProperty("SIQI_CORE_SHOP_HAD_ONCE_COMMODITY", IsOnceIDs)
```

## 刷新机制

### 回合刷新（Shop.lua）

```lua
-- 全局计数器：每 BASE_TURN 回合（含游戏速度倍率）统一刷新所有玩家
Game:SetProperty("SIQI_CORE_SHOP_REFRESH_TURN", currentTurn)
```

### 栏位刷新逻辑

```lua
-- GetNewCommodity: 获取指定等级的随机新商品，过滤：
-- 1. 已购买的唯品（IsOnce）
-- 2. 本栏位已有的商品（避免重复）
-- 3. 玩家无城市时排除城市商品
-- 4. 若无可用商品返回 ID='NOT' 的空白商品

-- Refresh: 逐栏位刷新，且同行已刷出的唯品会被后续栏位排除
```

## 购买通信流程

```
UI: ShopPanel.lua
    │  BoughtCommodity(itemID, IsCost, instance)
    │  → params = {ItemID=itemID, OnStart='OnSiqiCoreShopCommodityBought', IsCost=IsCost}
    │  → UI.RequestPlayerOperation(playerID, PlayerOperations.EXECUTE_SCRIPT, params)
    ▼
GP: Shop.lua
    │  GameEvents.OnSiqiCoreShopCommodityBought
    │  → SiqiCostShop.BoughtItem / SiqiGoldShop.BoughtItem
    │  → Item.BoughtCommodity → Commodity:BoughtCommodity()
    │     └─ Type='lua' → LuaEvents.SiqiCore_GoldShopCommodityBought
    ▼
GP: Shop_LuaEvent.lua
    │  LuaEvents.SiqiCore_GoldShopCommodityBought
    │  → BUYGOLDSHOP[ID](playerID, values)  -- 执行具体购买效果
```

## SQL 配合

```sql
-- 商品元数据表（必需）
CREATE TABLE Siqi_Core_GoldShop (
    ID          TEXT PRIMARY KEY,
    Level       INTEGER NOT NULL,
    Name        TEXT,
    Description TEXT,
    Type        TEXT DEFAULT 'lua',
    Cost        INTEGER DEFAULT 0,
    MinAmount   INTEGER DEFAULT 1,
    MaxAmount   INTEGER DEFAULT 1,
    IsCity      BOOLEAN DEFAULT FALSE,
    IsOnce      BOOLEAN DEFAULT FALSE,
    ModifierId  TEXT,
    PropertyName TEXT,
    Parameter1  TEXT,
    Parameter2  TEXT,
    Parameter3  TEXT,
    Parameter4  TEXT
);
```

## 关键要点

| 要点 | 说明 |
|------|------|
| CommodityZip 压缩存储 | 商品数据序列化为 `{ID, Amount, value1-4}` 存入 Player Property，反序列化重建 |
| IsOnce 跨栏位过滤 | 所有栏位刷新时共用 `IsOnceIDs` 列表，防止同一唯品出现在多个栏位 |
| 城市商品动态排除 | 玩家无城市时不刷出城市类商品，`Siqi_RandomSelectOneCity()` 返回 false 时移除 |
| 费用商店无唯品过滤 | SiqiCostShop.Refresh 传空 `{}` 而非 IsOnceIDs，费用商店商品可重复出现 |
| GameRefresh 信号 | 每次保存商品数据后调用 `SiqiCommodity.GameRefresh()`，通过 Game Property 触发 UI 刷新 |
| 商店自动初始化 | LoadItems 在 Property 为空时自动创建新商店，保证首次加载不出错 |
| 栏位数量动态增减 | `ChangeItemsCount` 支持增减栏位，新增栏位默认 Level=1 |

## 辅助函数索引

见 `Arknights_Cute_Leaders_Core_Mod_Supports.lua`：二进制 Property 读写（`Siqi_10to2/2to10`、`Siqi_GetPlotProperty/SetPlotProperty`）、随机抽取（`Siqi_RandomSelectOneCity/OneGreatPersonClass/OneStrategicResource`）、单位生成（`Siqi_InitBarbarianUnit`）、产出修改（`SiqiYieldTypeChange`）。

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `UI/Arknights_Cute_Leaders_Core_Mod_ShopPanel.xml` | 双 Tab 商店主面板 + Item Instance 模板 + LaunchBar 按钮 |
| `UI/Arknights_Cute_Leaders_Core_Mod_UI.xml` | 通用 UI Context（空骨架，预留扩展） |
| `Arknights_Cute_Leaders_Core_Mod_Table.sql` | 核心自定义表：`Siqi_Core_GoldShop`（商品定义）、`Siqi_CoreBinaryList`、`Siqi_Core_Improvement_Adjacency` 等 |
| `Arknights_Cute_Leaders_Core_Mod_Gameplay.sql` | 二进制产出 Modifier 链（6 Yield，各效果按最高位 1024/64/8 分档，见 [位上限](lua-binary.md#上限按效果设定不按机器整数位数设定)）+ Core Mod 全局 Modifier/Property |
| `Arknights_Cute_Leaders_Core_Mod_Shop.sql` | 商品数据填充（金币商店 + 费用商店全部商品的 INSERT） |

### 控件 ID 与 Lua Controls.xxx 对照

#### Arknights_Cute_Leaders_Core_Mod_ShopPanel.xml（商店主面板）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `MainContainer` | Container | `Controls.MainContainer` | 整个面板外层容器（1200x720） |
| `ScreenTitle` | Label | — | 面板标题 |
| `CloseButton` | Button | `Controls.CloseButton` | 右上角关闭按钮 |
| `TabControl` | Tab | `Controls.TabControl` | 外层 Tab（采购中心 / 其他标签页） |
| `SelectTab_Tab1` ~ `Tab4` | GridButton | `Controls.SelectTab_Tab1~Tab4` | 外层标签切换按钮（当前仅 Tab1 启用，Tab2~Tab4 注释） |
| `Tab1` | Grid | `Controls.Tab1` | 采购中心标签页内容 |
| `TabContainer` | Container | `Controls.TabContainer` | 内层 Tab 页面容器 |
| `TabButtons` (内层) | Grid | `Controls.TabButtons` | 内层标签按钮容器（金币/费用切换） |
| `SelectTab_ShopTab1` | GridButton | `Controls.SelectTab_ShopTab1` | 金币商店标签按钮 |
| `SelectTab_ShopTab2` | GridButton | `Controls.SelectTab_ShopTab2` | 费用商店标签按钮 |
| `SiqiGoldShopnStack` | Stack | `Controls.SiqiGoldShopnStack` | 金币商店栏位挂载点（8 个 Instance） |
| `SiqiCostShopStack` | Stack | `Controls.SiqiCostShopStack` | 费用商店栏位挂载点（10 个 Instance） |

**Instance 模板：**

| Instance Name | 说明 | 关键子控件 |
|---------------|------|----------|
| `LaunchBarItem` | LaunchBar 入口按钮 | `LaunchItemButton`(Button), `LaunchItemIcon`(Image) |
| `LaunchBarPinInstance` | LaunchBar 红点提示 | `Pin`(Image) |
| `SiqiShopInstance` | 商店行容器（尺寸 210x570） | `Top`(Container), `Row1`/`Row2`(Image) |
| `ItemInstance` | 单个商品卡片 | `Top`(Container), `ItemIcon`(Image, 200x200), `ItemName`(Label), `ItemCost`(Label), `ItemBuyButton`(GridButton), `ItemBuyButtonText`(Label) |

**交互流程：**
```lua
-- 1. 面板初始化：注册 LaunchBar → 绑定 eLClick 打开/关闭面板
Controls.LaunchItemButton:RegisterCallback(Mouse.eLClick, OnLaunchItemButtonClicked)

-- 2. 面板打开时：Setup() 读取 GP 端 Player Property 还原商店状态
-- 3. 内层 Tab 切换：金币商店（ShopTab1）/ 费用商店（ShopTab2）
Controls.SelectTab_ShopTab1:RegisterCallback(Mouse.eLClick, OnShopTabSelected)
Controls.SelectTab_ShopTab2:RegisterCallback(Mouse.eLClick, OnShopTabSelected)

-- 4. 栏位渲染：遍历 Items，用 InstanceManager 填充商品卡片
local m_ShopIM = InstanceManager:new("SiqiShopInstance", "Top", Controls.SiqiGoldShopnStack)
local m_ItemIM = InstanceManager:new("ItemInstance", "Top", instance.Top)

-- 5. 购买按钮：点击 → UI.RequestPlayerOperation → GameEvents
instance.ItemBuyButton:RegisterCallback(Mouse.eLClick, function()
    BoughtCommodity(itemID, IsCost, instance)
end)

-- 6. 刷新：监听 GamePropertyChanged → GP 端数据变化后自动 Refresh()
```

### SQL 必需表

```sql
-- 商品元数据表（必须在 Table.sql 中创建）
CREATE TABLE Siqi_Core_GoldShop (
    ID                 TEXT PRIMARY KEY,
    Icon               TEXT NOT NULL    DEFAULT 'SIQI_CHIP_AGENT',
    Name               TEXT NOT NULL,
    Description        TEXT NOT NULL,
    Type               TEXT NOT NULL    DEFAULT 'lua',       -- lua / modifier / property
    Cost               INTEGER NOT NULL DEFAULT 0,
    MinAmount          INTEGER NOT NULL DEFAULT 1,
    MaxAmount          INTEGER NOT NULL DEFAULT 1,
    Level              INTEGER NOT NULL DEFAULT 1,
    ModifierId         TEXT             DEFAULT NULL,
    PropertyName       TEXT             DEFAULT NULL,
    IsCity             BOOLEAN NOT NULL CHECK (IsCity IN (0, 1)) DEFAULT 0,
    IsOnce             BOOLEAN NOT NULL CHECK (IsOnce IN (0, 1)) DEFAULT 0,
    Parameter1         TEXT             DEFAULT NULL,
    Parameter2         TEXT             DEFAULT NULL,
    Parameter3         TEXT             DEFAULT NULL,
    Parameter4         TEXT             DEFAULT NULL
);
```

### XML 添加新商品栏目模板

```xml
<!-- 新栏位列 -->
<Stack ID="NewShopStack" Anchor="L,T" Offset="11,0" StackGrowth="Right" Padding="8" />

<!-- 对应的 Instance 槽位容器（如需要不同尺寸） -->
<Instance Name="NewShopColumnInstance">
    <Container ID="Top" Size="210,570">
        <Image ID="Row1" Anchor="L,T" Offset="0,15" Texture="Circle44_Lighter" Color="0,0,0,255" Size="210,270"/>
        <Image ID="Row2" Anchor="L,T" Offset="0,285" Texture="Circle44_Lighter" Color="0,0,0,255" Size="210,270"/>
    </Container>
</Instance>
```

```lua
-- Lua 端注册
local m_NewShopIM = InstanceManager:new("NewShopColumnInstance", "Top", Controls.NewShopStack)
local m_NewItemIM = InstanceManager:new("ItemInstance", "Top", instance.Top)
```
