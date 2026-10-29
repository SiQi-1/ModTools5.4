# 生灵单位系统（来源：0029）

## 做什么
`UNIT_SIQI_U0029_5`（生灵单位）是 Siqi_Leaders_0029 中的通用奖励载体，几乎被所有子系统当作奖励发放。它可以通过多种途径获得，作为灵值收集工具在地图上活动，也可以通过灵值直接购买。

## 涉及文件和函数

| 文件 | 相关函数 |
|------|---------|
| `Lua/Siqi_Leaders_0029_LeaderAbilities.lua` | `GiveUnitAndPromotion`, `L2:GiveUnitSLToCity`, L1-L7 各领袖能力 |
| `Lua/Siqi_Leaders_0029_Gameplay.lua` | `OnCityBuilt`（建城送生灵），OnTechBoostTriggered |
| `Support/Siqi_Leaders_0029_Core.lua` | `Core.GP.OnPurchaseSL`, `Core.GP.UnitButton_LZSJ`, `Core.GP.CityUnitProduction` |
| `UI/Siqi_Leaders_0029_UnitButton.lua` | 单位按钮交互 UI |
| `UI/Siqi_Leaders_0029_TopPanel.lua` | 城市购买按钮 |

## 获得途径

### 免费赠送（多种触发条件）
| 触发条件 | 来源 | 数量 |
|---------|------|------|
| 建立新城市 | Gameplay.lua `OnCityBuilt` | 1（被注释，当前未启用） |
| 建造保护区完成 | L2 鹿薇 | 每个保护区 1 个（去重） |
| 建造 DISTRICT_SIQI_D0029_6 | L6 | 每个该区域 1 个（去重，调用 L2 函数） |
| 城市人口首次达到 10 | L7 | 每个城市 1 个（去重） |
| 被宣战 | L3（已注释） | 1 |
| 首次建城 | L3 | 1（专属单位 UNIT_SIQI_U0029_2，非生灵） |
| 进入黄金时代 | L1 樱墨曦 | 每时代 1 个 |
| 招募 8 个伟人 | L1 樱墨曦 | 1（计数器扣减） |
| 主线任务等级 >= 3 | L1 樱墨曦 | 升级时 1 个 + 晋升次数 |
| 达成经济同盟 | L4 | 每个新同盟 1 个（去重） |
| 拥有 4/8/12 种奢侈品 | L4 | 各 1 个 |
| 尤里卡触发（概率） | L5 | 1（累积概率 10%-80%） |
| WMD 导弹爆炸 | Gameplay.lua | 无（仅奖励科技文化灵值） |

### 灵值购买（6 级任务后）
- 费用：`(200 + 购买次数 * 200) * 游戏速度倍率`，消耗灵值购买
- 入口：TopPanel 城市面板按钮
- 流程：UI 发起 `Siqi_Leaders_0029_Purchase_SL` → GP 执行 `Core.GP.OnPurchaseSL`
- 购买计数器：`Siqi0029_PurchaseCount`（影响下次价格）

## 单位交互（收集灵值）

### UnitButton 系统
生灵单位拥有特殊的操作按钮（`Siqi_Leaders_0029_UnitButton.lua`），在可交互地块上触发"灵值收集"事件。

### 收集结果类型
通过 `GameEvents.Siqi0029_UnitButton_LZSJ` 携带以下数据到 GP 端：

| 字段 | 类型 | 说明 |
|------|------|------|
| `UnitID` | number | 操作的单位 |
| `PlotID` | number | 目标地块 |
| `LingZhi` | number | 获得的灵值 |
| `Dead` | bool | 单位是否因此阵亡 |
| `Up` | bool | 单位是否因此升级 |
| `iX, iY` | number | 坐标 |

### GP 端处理（`Core.GP.UnitButton_LZSJ`）
1. 增加灵值（`Core.ChangeLZ`）
2. 显示飘字（`Core.AddWorldLZText`）
3. L6 领袖额外获得随机两种产出（科技/文化/生产力中随机两选，+10%+浮动 0-5%）
4. 标记单位已行动（`PROPERTY_SIQI_0029_UNIT_ACTED` 按 PlotID 记录）
5. 累加收集计数（`PROPERTY_SIQI_0029_SL_COUNT`）
6. 强制结束单位移动
7. 如果 Dead：`UnitManager.Kill(pUnit)`
8. 如果 Up：给 2 级晋升经验

## 生灵晋升系统（L1 樱墨曦专属）

生灵单位获得 `SIQI0029_PROMOTION_COUNT` 属性，每次单位晋升时自动消耗该属性，再获得一次晋升经验值：

```lua
function OnUnitPromoted(playerID, unitID)
    local promotionCount = pUnit:GetProperty(SIQI_C0029_1_PROMOTION_COUNT) or 0
    if promotionCount > 0 then
        GrantPromotion(playerID, unitID)  -- 再给一次满经验
        pUnit:SetProperty(SIQI_C0029_1_PROMOTION_COUNT, promotionCount - 1)
    end
end
```

## 战斗事件关联

### 生产战斗单位奖励灵值（所有文明通用）
在拥有 `DISTRICT_SIQI_D0029_2` 的城市生产战斗单位时，奖励灵值 = 单位 Cost * 0.5（`Core.GP.CityUnitProduction`）

### 迪娅可击杀奖励（L3 专属）
L3 领袖击杀单位时获得灵值 = 被击杀单位 Cost * 20%（`L3:OnUnitKilledInCombat`）

### L6 击杀宗教扩散
L6 领袖击杀单位时，以击杀位置为中心 6 环内施加宗教压力（与生灵单位无关，但和战斗事件绑定）

## Property 体系
| Property 名 | 作用对象 | 说明 |
|------------|---------|------|
| `PROPERTY_SIQI_0029_UNIT_ACTED` | Unit | 已交互过的地块哈希表 |
| `PROPERTY_SIQI_0029_SL_COUNT` | Unit | 累计收集灵值次数 |
| `SIQI0029_PROMOTION_COUNT` | Unit | L1 晋升次数（消耗型） |
| `Siqi0029_PurchaseCount` | Player | 累计购买次数（影响价格） |
| `PROPERTY_SIQI_0029_LUWEI` | City | L2 保护区已处理标记 |
| `PROPERTY_SIQI_0029_L5_DISTRICT_COMPLETED` | City | L5 区域已处理标记 |
| `PROPERTY_SIQI_0029_L6_DISTRICT_COMPLETED` | City | L6 区域已处理标记 |
| `SIQI0029_L7_CITY_POPULATION` | City | L7 人口已达标标记 |

## GP↔UI 通信
| 事件 | 方向 | 触发时机 |
|------|------|---------|
| `GameEvents.Siqi_Leaders_0029_Purchase_SL` | UI→GP | 城市面板点击购买按钮 |
| `GameEvents.Siqi0029_UnitButton_LZSJ` | UI→GP | UnitButton 收集灵值操作 |
| `LuaEvents.Siqi0029_UnitConverted` | GP→GP | 凰茗狐转化单位（非生灵专属） |

## 设计要点
1. **通用奖励载体**：生灵单位是 7 个领袖能力的统一奖励，通过各自的条件触发赠送
2. **L2 函数被复用**：`L2:GiveUnitSLToCity` 被 L6（区域完成）和 L7（人口达标）以及 `Core.GP.OnPurchaseSL`（购买）调用
3. **购买递增费用**：购买次数越多费用越贵，形成软上限
4. **操作结果多样化**：收集灵值可能导致单位死亡/升级/获得灵值，增加趣味性
5. **L1 晋升链**：从任务等级获得晋升次数，单位晋升自动连锁，形成独特的单位培养玩法

---

## XML 配合

### 文件路径

| 文件 | 用途 |
|------|------|
| `UI/Siqi_Leaders_0029_UnitButton.xml` | 生灵单位操作按钮（挂在 UnitPanel 的 StandardActionsStack） |
| `UI/Siqi_Leaders_0029_TopPanel.xml` | TopPanel 扩展：灵值购买按钮 + WMD 攻击计数 |

### 控件 ID 与 Lua Controls.xxx 对照

#### UnitButton.xml（单位操作面板）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `UPopupDialog` | Context | — | 根 Context Name（PopupDialog 弹窗用） |
| `Siqi0029UnitGrid` | Grid | `Controls.Siqi0029UnitGrid` | 按钮外层容器（SetHide 控制显隐） |
| `Siqi0029UnitButton` | Button | `Controls.Siqi0029UnitButton` | 灵值收集按钮（44x53，注册 eLClick） |
| `Siqi0029UnitButtonIcon` | Image | — | 按钮图标（ICON_SIQI_SHENGLINGBITAN） |

**挂载模式：**
```lua
-- 初始化时将按钮容器挂载到原版 StandardActionsStack
local pContext = ContextPtr:LookUpControl("/InGame/UnitPanel/StandardActionsStack")
if pContext ~= nil then
    Controls.Siqi0029UnitGrid:ChangeParent(pContext)
    Controls.Siqi0029UnitButton:RegisterCallback(Mouse.eLClick, OnSiqi0029UnitButtonClicked)
end
```

#### TopPanel.xml（城市面板购买按钮）

| XML 控件（ID） | 类型 | Lua 引用 | 用途 |
|---------------|------|---------|------|
| `WMDAttack` | Grid | `Controls.WMDAttack` | WMD 攻击计数容器（48x24） |
| `WMDAttackCount` | Label | `Controls.WMDAttackCount` | WMD 数量显示 |
| `SiqiButtonGrid` | Grid | `Controls.SiqiButtonGrid` | 灵值购买按钮容器（SetHide 控制） |
| `SiqiButton` | Button | `Controls.SiqiButton` | 灵值购买按钮（注册 eLClick） |
| `SiqiButtonIcon` | Image | — | 按钮图标（ICON_UNIT_SIQI_U0029_5） |

**挂载模式：**
```lua
-- TopPanel 的 SiqiButtonGrid 本身就在 Context 中，直接通过 Controls 访问
-- 不需要 ChangeParent
Controls.SiqiButtonGrid:SetHide(HideSiqiButton())
Controls.SiqiButton:SetDisabled(disabled)
Controls.SiqiButton:RegisterCallback(Mouse.eLClick, OnSiqiButtonClicked)
```

### 添加新控件模板（UnitButton 类）

```xml
<!-- 新单位操作按钮，放在 UnitButton.xml 中 -->
<Grid ID="SiqiNewUnitActionGrid" Anchor="R,B" Size="auto,41" 
      AutoSizePadding="6,0" Texture="SelectionPanel_ActionGroupSlot" 
      SliceCorner="5,19" SliceSize="1,1" SliceTextureSize="12,41" 
      ConsumeMouse="1" Hidden="1">
    <Button ID="SiqiNewUnitActionButton" Anchor="C,B" Size="44,53" 
            Texture="UnitPanel_ActionButton">
        <Image ID="SiqiNewUnitActionIcon" Anchor="C,C" Offset="0,-2" 
               Size="38,38" Icon="ICON_YOUR_ICON"/>
    </Button>
</Grid>
```

```lua
-- Lua 端
function Init()
    local pContext = ContextPtr:LookUpControl("/InGame/UnitPanel/StandardActionsStack")
    if pContext then
        Controls.SiqiNewUnitActionGrid:ChangeParent(pContext)
        Controls.SiqiNewUnitActionButton:RegisterCallback(Mouse.eLClick, OnNewActionClicked)
    end
    Events.UnitSelectionChanged.Add(OnUnitSelectionChanged)
    Events.UnitMoveComplete.Add(OnUnitMoveComplete)
end
```

### PopupDialog 弹窗模式

UnitButton 使用 PopupDialog 而非自定义面板 XML：
```lua
local m_kPopupDialog = PopupDialog:new("UPopupDialog")  -- 匹配 Context Name
m_kPopupDialog:AddTitle(title)
m_kPopupDialog:AddText(content)
m_kPopupDialog:AddButton(locText, callback)
m_kPopupDialog:Open()
UIManager:QueuePopup(ContextPtr, PopupPriority.Utmost)
```
