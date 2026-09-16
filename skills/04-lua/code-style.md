# Lua 代码规范

基于 19.47 Mod 提炼。18.0 为前期风格，19.47 为当前标准。

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
2. **只注册 .xml**，同名 .lua 自动配对加载（AGENTS.md 陷阱 10：两个文件必须成对存在）
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

-- UI 端：调用并获取返回值
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

-- UI 端
GameEvents.Siqi32_StatueFormSwitch.Add(function(playerID, formType)
    -- 收到具体参数后处理
end)
```

### 总结

| 方向 | 方式 | 场景 |
|------|------|------|
| UI → GP | `RequestPlayerOperation` | 用户操作→修改游戏 |
| GP → UI | `Game:SetProperty` + UI 监听 | **刷新面板**（首选） |
| GP → UI（带数据） | `GameEvents` | 需要传具体参数时 |
| UI → GP → UI | `GameEvents.Call()` | UI 向 GP 查询并等返回值 |
| GP → UI → GP | `ExposedMembers` | GP 需要 UI 侧的数据 |

---

```lua
-- UI 端：发出事件
GameEvents.SiqiOblivionisButtonClicked.Add(function(playerID, params)
    self:OnCityButtonClicked(playerID, params)
end)

-- UI 端（在 UI 上下文访问 GameEvents 需通过 ExposedMembers）
GameEvents = ExposedMembers.GameEvents

-- Scripts 端：接收事件
local params = {
    OnStart = 'SiqiUbika_SpeedDistrict',
    iX = iX, iY = iY, iUnit = pUnit:GetID()
}
UI.RequestPlayerOperation(Game.GetLocalPlayer(), PlayerOperations.EXECUTE_SCRIPT, params)
```

- `UI.RequestPlayerOperation` → Scripts 端执行（GP 同步）
- `GameEvents` 用于 Scripts↔Scripts 或 UI↔Scripts 之间广播事件
- UI 文件中 GameEvents 通过 `ExposedMembers.GameEvents` 获取
- 事件命名：`Siqi<功能名><动作>`

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

- 修饰符触发、GP 同步、错误必须打印
- 调试日志最终删除

---

## 十、排版

- 缩进：4 空格
- `include("xxx.lua");` — 带分号
- `local pPlayer = Players[playerID]` — 获取对象统一变量名
- 表访问用点号：`pPlayer:GetTreasury():ChangeGoldBalance(amount)`
- 单行 if：`if not x then return; end`
- 函数间空一行分隔
