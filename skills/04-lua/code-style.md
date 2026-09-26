# Lua 代码规范

来源：19.47 Mod 的组织方式。项目命名与模块布局是参考模式；环境隔离、API 查证及工具写入要求遵循 [规则正文](../RULES.md)。

---

## 事件环境与运行时核验

| 事件系统 | UI | GP | 环境边界 |
|---|---|---|---|
| LuaEvents | 可用，同环境通信 | 可用，GP → GP | 不可直接跨 UI / GP |
| Events | 可用 | 可用 | 具体事件、触发和参数按调用点核对 |
| GameEvents | 无原生 GP 事件表 | 可用 | UI 可使用显式桥接的 GP 引用，不能当成 UI 原生可用 |

按本项目原要求及用户 2026-09-25 的确认维护。外部技能的“GP 不可用 LuaEvents”不适用于本项目；事件未触发也不能一概归因于用了 Events 或 GameEvents，应查注册时机、具体事件、参数和环境。

GP-GP 和 UI-UI 的 LuaEvents 属于同环境通信；同名事件不建立跨环境通道。跨环境沿用下文 RequestPlayerOperation、Property 或明确的 ExposedMembers 桥接，不引入外部技能的全面禁用规定。桥接查询不替代需要同步的操作提交。

API 核验应记录环境、对象层级、返回值和官方调用点。FireTuner 独立上下文不能直接代表 Mod 自有环境，未实测的目标版本不标作已验证。

## 已核实的回合与宜居接口

- 当前回合使用 `Game.GetCurrentGameTurn()`，GP/UI 两端均有官方调用；不要写 `Game.GetGameTurn()`。官方依据为 `DLC/AlexanderScenario/Scripts/AlexanderScenario.lua` 和 `DLC/Expansion2/UI/Replacements/ARXManager_Expansion2.lua`。
- `City:GetGrowth():GetAmenitiesNeeded()` 是 UI 查询，官方 `Base/Assets/UI/CitySupport.lua` 用它读取需求；GP 不能直接调用。GP 的人口/免费宜居计算见 [非战斗 GP 函数](lua-gp-resource.md#城市宜居度计算gp-精确版)；需要 UI 完整统计时使用明确的只读桥接。
- 运行时证据：2026-09-25 的游戏日志在产出刷新、商路统计以及 GP 宜居任务轮询中记录上述两种错误；本地回归已在移除错误接口的测试环境中复现旧代码失败、修正代码通过，修复后的实机复测须另记。
- Lua 模拟测试不能随意补齐被测源码调用的方法。特别是 `Game` 及 GP/UI 对象，应按真实接口提供测试桩；否则拼错的方法名或环境错误也会“测试通过”。

## 原生属性的零返回值边界

- 未设置的原生 Property 可能返回 **零个 Lua 值**。当它是参数列表末尾的函数调用时，`tonumber(object:GetProperty(key))` 实际可能变成 `tonumber()`；外层 `or 0` 来不及生效，`type(...)` 也有相同风险。
- 先接收为局部变量，再检查或转换：`local value = object:GetProperty(key)`，随后 `tonumber(value) or 0` / `type(value)`。局部赋值会将零返回值接收为 `nil`；不要用吞错包装替代。
- 运行时证据：2026-09-25 16:25 的 19.47 日志在 GP 地块产出刷新记录 `bad argument #1 to 'tonumber' (value expected)`。同类检查还覆盖 UI 玩家/城市属性、织梦计数和破茧单位属性；这些扩展边界经模拟回归验证，不能当作每种对象均已实机复现。
- 测试桩须区别 `return nil` 和无 `return`：未设置时使用 `if properties[key] ~= nil then return properties[key] end`，保留已设置的 `false` / `0`。还应验证首次初始化、已有值保留、重复请求，以及常规/全量日志两种模式。

## 对象层级与环境的常见误用

- GP 当前生产使用 `City:GetBuildQueue():CurrentlyBuilding()`，读取类型字符串；空字符串或无有效类型表示未生产。`GetCurrentProductionTypeHash()` 是 UI 查询。存档中的旧 hash 应通过对应 `GameInfo` 行匹配，不能为兼容存档在 GP 调用 UI 接口。参见 [GP 生产力函数](lua-gp-resource.md#生产力奇观)。
- GP 全国区域遍历使用 `Player:GetDistricts():Members()`；不要把 UI 的 `City:GetDistricts():Members()` 移到 GP。局部城市统计须额外匹配所属城市。
- `City:GetBuildings():GetBuildingsAtLocation(plotIndex)`、`City:GetReligion():GetReligionsInCity()` 是 UI 查询，官方依据为 `Base/Assets/UI/CitySupport.lua`。UI 统计某宗教信徒时遍历返回的 `Religion` / `Followers`，不能借用 GP 的 `GetNumFollowers()`。
- 世界文字也分环境：GP 调用 `Game.AddWorldViewText(...)`，UI 调用 `UI.AddWorldViewText(...)`；不要把 GP 包装函数直接赋给 UI 命名空间。
- 资料表可能不完整：`Governor:GetTurnsToEstablish()` 在官方 `DLC/Expansion2/UI/Additions/GovernorSupport.lua` 中有调用，不能因表中仅列 manager 版本而认定它不存在。新增例外应附官方路径，而不是给测试桩临时补方法。
- 地块视野的官方 GP 例子见 `DLC/WarMachineScenario/Scripts/WarMachineScenario.lua`：`PlayersVisibility[playerID]:ChangeVisibilityCount(plotIndex, delta)`。重复刷新必须记录自己的增量；移除时只扣除自己增加的视野。

接口回归应从 API 资料和官方脚本建立 **GP/UI 各自的对象方法白名单**，至少核对 `Player`、`City`、各管理器和返回对象。不要使用为任意方法返回空函数的万能桩。用修复前源码验证错误能被测试捕获，再测试修改版；模拟通过与游戏引擎复测应分开记录。

---

## 一、文件目录与分类

| 目录 | 用途 | 加载 |
|------|------|------|
| `Scripts/` | 入口 + 事件注册 | InGameActions → AddGameplayScripts |
| `Import/` | 工具库（GP/UI/Support/Core） | `include("xxx.lua")` 被 Scripts/UI 引用 |
| `UI/` | 界面 | InGameActions → AddUserInterfaces |

```
<ModName>/
  Scripts/
    <ModName>_Scripts.lua       -- 唯一入口，极简
  Import/
    <ModName>_Support.lua       -- SiqiGP / SiqiUI 公共工具
    <ModName>_Core.lua          -- 模组专属逻辑（Mujica = {}）
  UI/
    <ModName>_CityButton.lua    -- 城市面板按钮（OOP）
    <ModName>_Popup.lua         -- 弹窗
    <ModName>_UI.lua            -- 全局 UI 刷新
```

> Scripts 只管 include + 初始化调用，不写具体逻辑。Import 是纯函数库，不注册事件。UI 注册事件在 `Initialize()` 中完成。

---

## 〇、工程文件注册（.civ6proj / .modinfo）

### 标准写法（ModBuddy 工程实证：10.0 / 3.1 / 19.47）

```xml
<InGameActions>
  ...UpdateText/UpdateIcons/UpdateDatabase...
  <AddUserInterfaces id="NewAction">
    <Properties>
      <Context>InGame</Context>
    </Properties>
    <File>UI/<ModName>_UI.xml</File>
  </AddUserInterfaces>
  <AddGameplayScripts id="NewAction">
    <File>Scripts/<ModName>_Scripts.lua</File>
  </AddGameplayScripts>
</InGameActions>
```

配套 ItemGroup（三个都要有）：

```xml
<Content Include="UI\<ModName>_UI.lua"><SubType>Content</SubType></Content>
<Content Include="UI\<ModName>_UI.xml"><SubType>Content</SubType></Content>
<Content Include="Scripts\<ModName>_Scripts.lua"><SubType>Content</SubType></Content>
<Folder Include="UI\" />
```

### 要点（实测）

1. **AddUserInterfaces 必须带 `<Properties><Context>InGame</Context></Properties>`**——缺 Context 属性时 UI 上下文不加载（0014 曾漏写，参考 10.0/3.1/19.47 修正）。Context 值：`InGame`（游戏内）/ `FrontEnd`（主菜单）
2. **只注册 .xml**，同名 .lua 自动配对加载（同名 XML/Lua 配对，见 [自定义文件指南](../05-modtools-civ/pipeline.md)）
3. **AddGameplayScripts 不需要 Properties**（0048 等实证）
4. 纯逻辑 UI 脚本（无可见控件，如"UI 监听 → EXECUTE_SCRIPT → GP"模式）：XML 里放一个隐藏 Grid 容器即可（0048 同款）：
   ```xml
   <Context>
     <Grid ID="xxxHiddenGrid" Anchor="C,C" Size="1,1" Hidden="1"/>
   </Context>
   ```
5. 另一变体（skill 内 ContextPath 方式）用于挂载到指定上下文路径：`<AddUserInterfaces><Item ContextPath="InGame/AdditionalUserInterfaces" /></AddUserInterfaces>`——ModBuddy 工程用 `<File>` 方式即可

---

## 二、Scripts 文件（入口）— 8.0 风格

```lua
--====================================================================
-- 常量
--====================================================================
local INDEX_PEACH_GENERAL = GameInfo.Units["UNIT_PEACH_GENERAL"].Index or -1
local TYPE_MYRTLE         = 'LEADER_MYRTLE'

ExposedMembers.GameEvents = GameEvents

--====================================================================
-- 工具函数
--====================================================================
-- 判断玩家是否为目标领袖，返回布尔值
function Siqi_IsPlayerLeader(playerID, leaderType)
    local pPlayerConfig = PlayerConfigurations[playerID]
    if pPlayerConfig == nil then return false; end
    if pPlayerConfig:GetLeaderTypeName() == leaderType then
        return true
    else
        return false
    end
end

-- 寻找玩家的第一个目标单位，返回单位对象或 nil
function Siqi_FindUnit(playerID, unittype)
    local pPlayer = Players[playerID]
    for i, unit in pPlayer:GetUnits():Members() do
        if unit:GetType() == unittype then
            return unit
        end
    end
    return nil
end

--====================================================================
-- 玫兰莎
--====================================================================
function Siqi_Myrtle_Build_AidStation(playerID, cityID)
    -- ...
end

--====================================================================
-- 苏苏洛
--====================================================================
function Siqi_Sussurro_Heal(playerID, unitID)
    -- ...
end

--====================================================================
-- 事件注册
--====================================================================
Events.PlayerTurnActivated.Add(function(playerID, bIsFirstTime)
    if not bIsFirstTime then return end
    Siqi_OnTurnActivated(playerID)
end)
```

- **用注释章节划分区域**：`--==== 工具函数 ====--`、`--==== 领袖名 ====--`、`--==== 事件注册 ====--`
- **纯函数**，不用表嵌套、不用 `self`、不用 OOP
- 不要 `--====` 延长到整行（保持简洁），用短分隔线
- `include` 不带分号
- 常量顶部声明，带 `or -1` 后备值
- `ExposedMembers.GameEvents = GameEvents` 放在顶部（UI 需要访问时）
- **禁用 `local function`**，Civ6 Lua 规范统一使用 `function Foo()` 声明函数，与现有代码库风格一致
- **事件注册必须在 `Initialize()` 函数内**，不能写在文件顶层。唯一例外是 `Events.LoadGameViewStateDone.Add(Initialize)` 本身
- **回合开始类周期逻辑优先 `Events.PlayerTurnActivated`**（本地玩家回合激活时机；官方 UI 与主流 Mod 通行做法）；不建议用全局回合事件（`GameEvents.OnGameTurnStarted`）做每回合任务——AI 回合、读档等时机不可控。用 `if playerID ~= Game.GetLocalPlayer() then return end` 保证一次/回合

---

## 三、GP 与 UI — 两个完全隔离的运行环境

Civ6 Lua 有两个独立执行环境，**函数不能跨环境调用**：

| | GP 环境 | UI 环境 |
|------|--------|--------|
| 运行位置 | `Scripts/`、`Import/`（被 Scripts include） | `UI/` 目录 |
| 读写游戏状态 | **可以** | **禁止** |
| 操作 UI 控件 | 不可以 | 可以 |
| 典型 API | `Players[]`, `pPlayer:GetTreasury()`, `Game.*` | `Controls.xxx`, `UI.GetHeadSelectedCity()`, `ContextPtr` |
| 修改游戏 | 直接调用 | `UI.RequestPlayerOperation(playerID, PlayerOperations.EXECUTE_SCRIPT, params)` 委托 GP |

> **接口文件（Objects.csv）标注了每个方法属于 GP 还是 UI。写任何函数前必须先查接口文件确认环境。**

```lua
-- Import 中按环境分表：
SiqiGP = {}     -- GP 环境可用的函数
SiqiUI = {}     -- UI 环境可用的函数
```

```lua
-- /* ====================================================================
-- SiqiGP API（GP 环境专用）
-- SiqiGP.IsCivilization(playerID, sCivilizationType) -- 是否目标文明
-- SiqiGP.ChangeGold(playerID, amount)                -- 修改金币
-- ==================================================================== */

SiqiGP.ChangeGold = function(playerID, amount)
    local pPlayer = Players[playerID]
    -- GetTreasury() 仅在 GP 环境可用，UI 环境调用会崩溃
    pPlayer:GetTreasury():ChangeGoldBalance(amount)
end
```

---

## 四、Import — Support 辅助函数

**策略**：两个文件都复制到 mod 的 Import/ 目录，只改文件名。每个环境只 include 自己的辅助文件，避免 GP/UI 函数混用导致崩溃。

### 引用文件

- `C:\Users\24948\Documents\Firaxis ModBuddy\Civilization VI\Siqi的mod示范\GP_Support_Function.lua`
- `C:\Users\24948\Documents\Firaxis ModBuddy\Civilization VI\Siqi的mod示范\UI_Support_Function.lua`

### 使用方式

```lua
-- Scripts 中：
include("GP_Support_Function.lua")

-- UI 文件中：
include("UI_Support_Function.lua")
```

### 核心原则：直接函数名，不用前缀

函数名本身已足够清晰，加 SiqiGP/SiqiUI 前缀只会增加冗余调用链：

```lua
ChangeGold(playerID, amount)      -- 不是 SiqiGP.ChangeGold
IsLeader(playerID, leaderType)    -- 不是 SiqiGP.IsLeader
FormatValue(value)                -- 不是 SiqiGP.FormatValue
```

### GP_Support_Function 核心函数

| 函数 | 说明 |
|------|------|
| `IsCivilization(playerID, type)` | 是否目标文明 |
| `IsLeader(playerID, type)` | 是否目标领袖 |
| `HasTrait(playerID, trait)` | 是否拥有特性 |
| `HasProperty(object, prop)` | 是否拥有属性（GetProperty 非 nil 且 >0） |
| `FormatValue(value)` | 格式化数字，正数 +千位分隔 |
| `GetYieldString(YieldType)` | 产出图标+名称字符串 |
| `Red(str)` / `Green(str)` / `ColorRGB(str, color)` | 文字着色 |
| `AddYieldStringToWorld(Amount, YieldType, iX, iY)` | 地图上飘产出文本 |
| `ChangeScience/Culture/Gold/Faith(playerID, amount)` | 修改产出 |
| `ChangeProduction(playerID, amount, cityID)` | 修改生产力（cityID=nil=全部城市） |
| `ChangeGreatPeoplePoints(playerID, amount, class)` | 修改伟人点数 |
| `ChangeUnitDamage(playerID, unitID, amount, NotKilled)` | 单位伤害 |
| `ChangeCityDamage(playerID, cityID, amount)` | 城市伤害（先城墙后本体） |
| `GrantBuilding/RemoveBuilding(playerID, building, cityID)` | 赠送/移除建筑 |
| `NumToTwo/TwoToNum/GetPlotTwo/SetPlotTwo` | 二进制 Plot Property 读写 |
| `GetTechsNum/GetCultsNum(playerID)` | 科技/市政数量 |
| `GetCityAminity(playerID, cityID)` | 城市宜居度 |
| `Siqi_InitUnit(iX, iY, unitType, playerID)` | 在单元格三环内放置单位 |

### UI_Support_Function 核心函数

| 函数 | 说明 |
|------|------|
| `GetCityPower(playerID, cityID)` | 城市电力 |
| `GetCityDistrictsSlotLeft(playerID, cityID)` | 城市剩余区域位 |
| `IsCityBesieged(playerID, cityID)` | 城市是否被围城 |
| `GetCityReligion(playerID, cityID)` | 城市主流宗教 |
| `GetCityPlayerFollows(playerID, cityID)` | 城市信仰玩家宗教的信徒数 |
| `GetCityTradeRoutesNum/GetCityForeignTradeRoutesNum` | 城市商路数/通往国外 |
| `GetProductionCost(playerID, cityID, conType, itemID)` | 建造造价 |
| `GetCityProductionProgress(playerID, cityID)` | 当前建造进度详情 |
| `GetCityGovernor(playerID, cityID)` | 城市当前总督类型 |
| `GetCityGovernorDetailed(playerID, cityID)` | 总督详细信息（含上任回合等） |
| `GetGovernorCity(playerID, governorType)` | 总督所在城市 |
| `GovernorHasPromotion(playerID, govType, promType)` | 总督是否拥有晋升 |

> 两个文件有函数重名（IsCivilization、HasProperty、FormatValue 等），因为它们两个环境都能跑。整包复制时不用处理重名。

---

## 五、UI 文件 — OOP 模式

```lua
include("Arknights_Cute_Leaders_19.47_Support.lua");
include("Arknights_Cute_Leaders_19.47_Core.lua");

local CityPanel = {}

function CityPanel:new()
    local o = {}
    setmetatable(o, self)
    self.__index = self
    o.plots = {}
    o.Bonus = 5
    return o
end

function CityPanel:Initialize()
    self:Init()
    Events.CitySelectionChanged.Add(function(playerID, cityID, ...)
        if playerID ~= Game.GetLocalPlayer() then return end
        if not IsLeader(playerID) then return end
        self:Refresh()
    end)
end

function CityPanel:Init()
    local pContext = ContextPtr:LookUpControl("/InGame/CityPanel/ActionStack")
    if pContext ~= nil then
        Controls.CityButton:ChangeParent(pContext)
        Controls.CityButton:RegisterCallback(Mouse.eLClick,
            function() self:OnButtonClicked() end)
    end
end

function CityPanel:Refresh()
    -- 刷新 UI 状态
end

function CityPanel:OnButtonClicked()
    -- 按钮逻辑
end

-- 实例化
local g_CityPanel = CityPanel:new()
g_CityPanel:Initialize()
```

- 用 metatable 实现 OOP：`setmetatable(o, self); self.__index = self`
- 方法定义用冒号：`function CityPanel:Initialize()`
- 方法调用也用冒号：`self:Refresh()`
- 文件末尾创建全局单例并初始化
- 每个面板一个文件

---

## 六、命名规范

| 层级 | 命名 | 示例 |
|------|------|------|
| 跨 mod 公共库 | `SiqiGP`, `SiqiUI` | `SiqiGP.ChangeGold()` |
| 本 mod namespace | `Mujica`, `Fever` | `Mujica.Doloris.Ability_Purchase()` |
| 子模块 | `Mujica.Doloris`, `Ability.Oblivionis` | `Ability.Oblivionis:Initialize()` |
| UI 类 | `CityPanel`, `DolorisChoosePanel` | `CityPanel:new()` |
| 单例 | `g_CityPanel` | `local g_CityPanel = CityPanel:new()` |
| 属性 Key | PascalCase 字符串 | `'SiqiMujica_Oblivionis'` |
| 局部常量 | UPPER_SNAKE | `GAME_SPEED`, `GAME_SPEED_MULTIPLIER` |
| 临时变量 | camelCase 或 下划线 | `attInfo`, `xinghui_now` |

---

## 七、GP↔UI 通信

五种方式，对应不同场景。

### 1. UI → GP（发送命令，不等待返回）

```lua
-- UI 端：发送命令到 GP 执行
local params = {
    OnStart = 'Siqi32_MoraPurchase',  -- GP 端的处理函数名
    playerID = Game.GetLocalPlayer(),
    itemID   = itemID,
}
UI.RequestPlayerOperation(Game.GetLocalPlayer(), PlayerOperations.EXECUTE_SCRIPT, params)

-- GP 端（Scripts）：接收并执行
function Siqi32_MoraPurchase(playerID, params)
    pPlayer:GetTreasury():ChangeGoldBalance(-100)
end
```

### 2. GP → UI（通知刷新，无参数）— BroadcastRefresh 模式

一个函数（GP 端调用）+ 一个事件（UI 端监听）。GP 只管改数据然后调 `BroadcastRefresh()`，UI 收到事件后自己读数据自己画。

```lua
-- GP 端（Support）：定义广播刷新函数
function Siqi32.BroadcastRefresh()
    if Game:GetProperty("SIQI32_CORE_REFRESH") then
        Game:SetProperty("SIQI32_CORE_REFRESH", false)
    end
    if not Game:GetProperty("SIQI32_CORE_REFRESH") then
        Game:SetProperty("SIQI32_CORE_REFRESH", true)
    end
end

-- GP 端：任意修改游戏状态后调用
ChangeGold(playerID, 500)
Siqi32.BroadcastRefresh()
```

```lua
-- UI 端（每个面板文件）：监听同一个事件，无条件刷新
function OnGamePropertyChanged()
    local balance = Players[Game.GetLocalPlayer()]:GetProperty("MORA") or 0
    Controls.BalanceLabel:SetText(FormatValue(balance))
end
Events.GamePropertyChanged.Add(OnGamePropertyChanged)
```

> 这是 GP→UI **最常用的模式**。GP 只改数据不改 UI，UI 自己读数据自己画，完全解耦。多个面板可以各自监听同一事件。

### 3. UI → GP → UI（查询，带返回值）

```lua
-- GP 端（Scripts）：注册带返回值的查询函数
function GetPlotWonderType(playerID, plotID)
    local pPlot = Map.GetPlotByIndex(plotID)
    return pPlot:GetWonderType()
end
GameEvents.Siqi32_GetPlotWonderType.Add(GetPlotWonderType)

-- GP 端先建立桥接
ExposedMembers.GameEvents = GameEvents
-- UI 端：显式取 GP 引用，确认初始化完成后调用
local GameEvents = ExposedMembers.GameEvents
if GameEvents == nil then return; end
local wonderType = GameEvents.Siqi32_GetPlotWonderType.Call(playerID, plotID)
```

> `GameEvents.xxx.Call()` 会阻塞等待 GP 端返回，仅用于查询，不适合耗时操作。

### 4. GP → UI → GP（ExposedMembers 反向查询）

```lua
-- UI 端：暴露函数给 GP
ExposedMembers.Siqi32 = {
    IsNingGovEstablished3Titles = function(playerID, cityID)
        return true  -- UI 端的查询结果
    end
}

-- GP 端：调用 UI 暴露的函数
if ExposedMembers.Siqi32 and 
   ExposedMembers.Siqi32.IsNingGovEstablished3Titles(playerID, cityID) then
    -- ...
end
```

### 5. GP → UI（GameEvents 事件广播）

需要传具体数据时使用，等价于带参数的"通知刷新"。

```lua
-- GP 端
GameEvents.Siqi32_StatueFormSwitch.Add(OnStatueFormSwitch)
ExposedMembers.GameEvents = GameEvents  -- 暴露给 UI

-- UI 端：显式引用 GP 的事件表
local GameEvents = ExposedMembers.GameEvents
if GameEvents == nil then return; end
GameEvents.Siqi32_StatueFormSwitch.Add(function(playerID, formType)
    -- 收到具体参数后处理
end)
```

### 总结

| 方向 | 方式 | 场景 |
|------|------|------|
| UI → GP | `RequestPlayerOperation` | 用户操作→修改游戏 |
| GP → UI | `Game:SetProperty` + UI 监听 | **刷新面板**（首选） |
| GP → UI（带数据） | 显式桥接的 `GameEvents` | 需要传具体参数时 |
| UI → GP → UI | 显式桥接的 `GameEvents.Call()` | UI 向 GP 查询并等返回值 |
| GP → UI → GP | `ExposedMembers` | GP 需要 UI 侧的数据 |

---

桥接示例的 GameEvents 来自 ExposedMembers.GameEvents，不能省略 GP 暴露和 UI 取引用的初始化。改变游戏状态的 UI 操作沿用 RequestPlayerOperation → GP 处理；同环境广播可用 LuaEvents，不依靠它跨 UI/GP。

---

## 八、注释规范

```lua
-- 行注释说明功能（中文）
function SiqiGP.ChangeGold(playerID, amount)
    local pPlayer = Players[playerID]
    pPlayer:GetTreasury():ChangeGoldBalance(amount)
end

-- /* ====================================================================
-- SiqiGP API 列表
-- SiqiGP.ChangeGold(playerID, amount)  -- 修改金币
-- ==================================================================== */
```

- 行注释用 `-- `（两个短横 + 空格）
- **API 注释块**：`-- /* ====` ... `-- ==== */` 包裹的函数列表
- 每个 API 一行：`-- 函数签名 中文说明`
- 不写作者、日期、ASCII 艺术字

---

## 九、日志

```lua
print("[模组名] 描述", param1, param2)
```

- 常规日志保留初始化、重要操作结果、拒绝原因、回退/补偿和异常；高频扫描、逐地块和逐单位明细放入默认关闭的全量模式。
- 全量模式可保留在发布源码中，但默认关闭并提供明确开关。字段至少包含模组前缀、GP/UI 上下文、回合、模块/阶段和玩家/实体 ID；不要从任意对象反射调用未知接口来收集日志。
- 区分 UI 提交、GP 收到、条件拒绝、调用返回和实际状态确认。UI/GP 可携带仅用于诊断的请求 ID；不能将“提交”或 modifier 挂载返回写成“已验证引擎效果”。
- 日志只读运行状态，不调用随机数、不补发奖励、不改变去重/结算；关闭全量后不应做额外大范围扫描。重复的桥接缺失警告可去重，并记录恢复。
- 不用空函数或吞错 pcall 让错误消失。若用进入/返回标记定位异常，保留原始 Lua 报错与堆栈。
- 回归必须比较常规/全量开关前后的结算、随机数次数和返回值；测试错误是否仍传播，并检查序列化对 nil、循环表和过长字段有界。

---

## 十、排版

- 缩进：4 空格
- `include("xxx.lua");` — 带分号
- `local pPlayer = Players[playerID]` — 获取对象统一变量名
- 表访问用点号：`pPlayer:GetTreasury():ChangeGoldBalance(amount)`
- 单行 if：`if not x then return; end`
- 函数间空一行分隔
