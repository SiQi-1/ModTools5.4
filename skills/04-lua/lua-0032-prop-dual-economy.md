# 属性双资源经济系统（来源：18.0 星辉/星数）

## 做什么
完全基于 Player/City Property 的双货币经济系统，不依赖 Modifier。包含**累积、每回合产出、消费、UI 展示**四大子系统。核心设计：两个对称资源（XingHui 星辉 / XingShu 星数）分别绑定两个领袖（Astesia / Astgenne），消费 5 点自动触发 GoodyHut 级奖励（市政鼓舞 / 科技尤里卡）。

## 涉及文件

| 文件 | 角色 |
|------|------|
| `18.0/Support/Arknights_Cute_Leaders_18_Support.lua` | 资源 CRUD 核心（Get/Change Amount，每回合计算） |
| `18.0/Scripts/Arknights_Cute_Leaders_18_Scripts.lua` | GP 事件连接（回合激活、伟人、建筑建造、尤里卡/鼓舞） |
| `18.0/UI/Arknights_Cute_Leaders_18_UI.lua` | WorldTracker 顶部栏展示（总量 + 每回合 + tooltip 明细） |
| `18.0/UI/Replacement/BoostUnlockedPopup_Core.lua` | GoodyHut 弹窗替换（区分来源显示） |

## GP 端

### 1. 资源定义

```lua
-- 两个对称 Property key
local Property_XingHui = "Siqi_XingHui"        -- 星辉总量
local Property_XingShu = "Siqi_XingShu"        -- 星数总量
-- 每回合累计计数器（达到 5 触发 GoodyHut）
Property_XingHui.."_now"  -- 星辉当前累计（用于判断是否达标 5）
Property_XingShu.."_now"  -- 星数当前累计
```

### 2. 增减操作（Support.lua）

```lua
SiqiSupport.ChangeAmount_XingHui = function(playerID, amount)
    -- amount > 0: 增加总量
    -- amount < 0: 减少总量 + 累计 _now 值 + 达到 5 时附加 Modifier
    -- 达到 5 时: pPlayer:AttachModifierByID("MODIFIER_SIQI_ASTESIA_GRANT_RANDOM_CIVIC_BOOST_GOODY_HUT")
```

关键设计：**消费时检查 `_now` 累计值**，每消费 5 点触发一次免费 GoodyHut 效果。

### 3. 每回合产出来自城市属性

```lua
SiqiSupport.GetPerTurn_XingHui = function(playerID)
    -- 遍历所有城市的 Hash_Xinghui_PerTurn 属性值
    -- Total = cityProperty / 10（整数向下取整）
    -- 返回 Total 和 tooltip 字符串
end
```

城市属性 `Xinghui_PerTurn` / `Xingshu_PerTurn` 由 SQL Modifier 设置（0032 自定义类型 `MODIFIER_SIQI32_CITIES_ADJUST_PROPERTY`：Types + DynamicModifiers，EffectType=`EFFECT_ADJUST_CITY_PROPERTY`，CollectionType=`COLLECTION_PLAYER_CITIES`。⚠️ 标准库无 `MODIFIER_PLAYER_CITIES_ADJUST_CITY_PROPERTY`，此名是文档漂移，勿用）。

### 4. 收入来源（Scripts.lua 事件注册）

| 收入来源 | 事件 | 数量 |
|---------|------|------|
| 触发尤里卡/鼓舞 | `CivicBoostTriggered` / `TechBoostTriggered` | +1 对应资源 |
| 每个自己的回合 | `PlayerTurnActivated` (bIsFirstTime) | 城市产出合计 |
| 建造星象学校 | `BuildingConstructed` (BUILDING_SIQI_ASTRO_SCHOOL) | +1 + 随机尤里卡科技 |
| 伟人激活（大科学家） | `UnitGreatPersonActivated` | 附加 Modifier |

### 5. 时代完成奖励（尤里卡/鼓舞全时代）

```lua
Siqi_HasTechBoostForEra(playerID, iTech)
-- 遍历该时代所有科技，检查是否全部已有尤里卡
Siqi_RewardTechBoostForEra(playerID, iTech)
-- 该时代所有未完成的科技立即完成（SetResearchProgress = GetResearchCost）
```

此为 Astgenne 领袖专属：如果触发了当前时代最后一个尤里卡，所有该时代科技自动完成。

### 6. GameEvents 对外接口

```lua
GameEvents.SiqiUbikaChange.Add(SiqiUbikaChange)           -- 外部修改资源: playerID, {Type, Amount}
GameEvents.SiqiUbikaPropertyFalse.Add(OnSiqiUbikaPropertyFalse)  -- 重置 GoodyHut 标记
```

## UI 端

### WorldTracker 顶部栏（18_UI.lua）

**注入位置：** `/InGame/WorldTracker/PanelStack`（索引 1，金币栏旁）

**显示内容：**
- 星辉/星数总量（格式：`1,234.5`）
- 每回合产出（格式：`+12.3`）
- 点击刷新按钮或自动刷新

**刷新时机：**
```lua
Events.LocalPlayerChanged.Add(SiqiRefresh)       -- 切领袖
Events.PlayerTurnActivated.Add(SiqiRefresh)       -- 回合开始
Events.GamePropertyChanged.Add(SiqiRefresh)       -- Game 属性变化（GP 端 SetProperty 后触发）
Events.CityPropertyChanged.Add(SiqiRefresh)       -- 城市属性变化（每回合产出源变化）
Events.CityProductionCompleted.Add(SiqiRefresh)   -- 完成生产
```

**显示/隐藏逻辑：** 仅当本地玩家拥有 PROPERTY_SIQI_ASTESIA 或 PROPERTY_SIQI_ASTGENNE 时显示，否则 `SetHide(true)`。

**Tooltip 明细：**
```
每回合总产出: +12.3
  城市A: +5.2
  城市B: +3.1
  城市C: +4.0
```

### 属性变化信号链

```
GP: pPlayer:SetProperty("Siqi_XingHui", newValue)
  └── 自动触发 Events.GamePropertyChanged
       └── UI: SiqiRefresh() 重新读取并渲染
```

**注意：** `Events.GamePropertyChanged` 不携带具体值，仅通知"某属性变了"，UI 需主动调用 `GetProperty()` 重新读取。

## XML 配合

### 需要的 SQL ModifierType

| ModifierType | 作用 |
|-------------|------|
| `MODIFIER_SIQI_ASTESIA_GRANT_RANDOM_CIVIC_BOOST_GOODY_HUT` | 随机市政鼓舞（模拟 GoodyHut） |
| `MODIFIER_SIQI_ASTGENNE_GRANT_RANDOM_TECHNOLOGY_BOOST_GOODY_HUT` | 随机科技尤里卡 |
| `MODIFIER_SIQI_UNCHARTED_STAR_MAP_ADJUST_BASE_YIELD_CHANGE` | 伟人激活附加效果 |
| 城市每回合产出 Modifier | `MODIFIER_PLAYER_CITIES_ADJUST_CITY_PROPERTY` 设置 `Xinghui_PerTurn` / `Xingshu_PerTurn` |

### GameCapabilities 属性注册

```xml
<GameCapabilities>
    <Property Name="Siqi_XingHui" ... />
    <Property Name="Siqi_XingHui_now" ... />
    <Property Name="Siqi_XingShu" ... />
    <Property Name="Siqi_XingShu_now" ... />
    <Property Name="PROPERTY_SIQI_ASTESIA_GRANT_RANDOM_CIVIC_BOOST_GOODY_HUT_USED" ... />
    <Property Name="PROPERTY_SIQI_ASTGENNE_GRANT_RANDOM_TECHNOLOGY_BOOST_GOODY_HUT_USED" ... />
</GameCapabilities>
```

## 设计要点

1. **双资源对称设计**：XingHui（市政系）和 XingShu（科技系）代码完全对称，只改 Property key 和奖励 Modifier
2. **消费累积阈值**：每消费 5 点触发 GoodyHut 奖励，用 `_now` 后缀 property 做累计计数器
3. **跨线程通信**：UI Refresher 监听 `Events.GamePropertyChanged` — 任何 GP 端 `SetProperty` 都会触发 UI 刷新
4. **每回合产出用 City Property**：不是 Player Property，而是每个城市的 `Xinghui_PerTurn` 哈希值，遍历求和
5. **GoodyHut 来源标记**：`PROPERTY_SIQI_ASTESIA_GRANT_RANDOM_CIVIC_BOOST_GOODY_HUT_USED` 用于区分弹窗来源（系统 GoodyHut vs 自产）
6. **时代检测完成奖励**：全时代尤里卡/鼓舞完成后自动完成所有该时代科技/市政
