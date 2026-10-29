# 文明6 Lua API 速查（官方文件静态核对 + 真机运行实测） — 单位/城市

> 分册：由 [lua-api.md](lua-api.md) 按主题拆出；覆盖 3. 单位操作、3.1 两个核心调用、3.2 UnitOperationTypes 观测成员（32 项，非穷举）、3.3 移动单位（最常用，官方完整分支）、3.4 建城 / 造改良 / 远程攻击、3.5 单位指令（Command，与 Operation 不同）、3.6 UnitManager 其它观测成员、4. 城市生产、4.1 核心调用、4.2 参数键（按生产对象选一个）、4.3 最简"造单位"和"造区域"、4.4 购买（Command 而非 Operation）、4.5 City 对象 / CityManager 其它。触发：移动单位、建城、城市生产时。

## 3. 单位操作

### 3.1 两个核心调用

```lua
-- 能开始吗？（第 5 参要结果表）
local bCanStart, tResults = UnitManager.CanStartOperation(pUnit, eOperation, targetPlot, tParameters, bWantResults);
-- 开始
UnitManager.RequestOperation(pUnit, eOperation, tParameters);
```

官方调用形式（**参数个数会变**，注意逐条比对）【静态核对】：

| 形式 | 来源 |
| --- | --- |
| `CanStartOperation(unit, op, nil, tParameters)` | `Base/Assets/UI/Civ6Common.lua:141` |
| `CanStartOperation(unit, op, nil, tParameters, true)` | `Base/Assets/UI/Panels/UnitPanel.lua:558` |
| `CanStartOperation(unit, op, nil, false, false)` — 注释 "No exclusion test, no results" | `UnitPanel.lua:609` |
| `CanStartOperation(unit, op, nil, false, OperationResultsTypes.ALL)` | `UnitPanel.lua:630` |
| `CanStartOperation(unit, op, targetPlot, false, true)` | `Base/Assets/UI/Choosers/EspionageChooser.lua:199` |
| `CanStartOperation(unit, op, nil, tParameters, OperationResultsTypes.NO_TARGETS)` | `UnitPanel.lua:677` |
| `RequestOperation(unit, op)` | `UnitPanel.lua:2535`、`:2636` |
| `RequestOperation(unit, op, tParameters)` | `UnitPanel.lua:2557`；`Civ6Common.lua:142` |

【静态核对】第 1 参 = 单位对象，第 2 参 = `UnitOperationTypes.*`，第 5 参可接受 `true/false` 或 `OperationResultsTypes.*`。
【待运行时验证】第 3 参 `targetPlot`（地格对象，非坐标）与第 4 参"参数表 or false"的准确契约；`OperationResultsTypes` 仅观测到 `ALL`（`UnitPanel.lua:630`）与 `NO_TARGETS`（`UnitPanel.lua:677`）两个值。

### 3.2 UnitOperationTypes 观测成员（32 项，非穷举）

| 成员 | 用途 | 来源 |
| --- | --- | --- |
| `MOVE_TO` | 移动 | `Civ6Common.lua:163`；`UnitPanel.lua:608` |
| `SWAP_UNITS` | 换位 | `Civ6Common.lua:160-161` |
| `FOUND_CITY` | 建城 | `UnitPanel.lua:629-630`、`:2636` |
| `BUILD_IMPROVEMENT` | 造改良 | `UnitPanel.lua:337`、`:2557` |
| `RANGE_ATTACK` | 远程攻击 | `Civ6Common.lua:148-149` |
| `AIR_ATTACK` / `DEPLOY` | 空袭/部署（空军） | `Civ6Common.lua:141-144` |
| `COASTAL_RAID` | 沿海劫掠 | `Civ6Common.lua:153-154` |
| `WMD_STRIKE` | 核打击 | `UnitPanel.lua:635-643` |
| `FORTIFY` / `ALERT` | 驻守/警戒 | `Base/Assets/UI/WorldTracker.lua:948` |
| `MAKE_TRADE_ROUTE` | 商队路线 | `Base/Assets/UI/Choosers/TradeRouteChooser.lua:817`、`:835` |
| `REBASE` | 飞机转场 | `Base/Assets/UI/WorldInput.lua:2486-2487` |
| `SPY_COUNTERSPY` / `SPY_TRAVEL_NEW_CITY` / `SPY_LISTENING_POST` / `SPY_SIPHON_FUNDS` / `SPY_GAIN_SOURCES` / `SPY_STEAL_TECH_BOOST` / `SPY_GREAT_WORK_HEIST` | 间谍 | `Choosers/EspionageChooser.lua:374`、`:616`；`Base/Assets/UI/EspionageSupport.lua:198-219` |
| 参数键 | `PARAM_X`、`PARAM_Y`、`PARAM_X0/PARAM_Y0/PARAM_X1/PARAM_Y1`、`PARAM_MODIFIERS`、`PARAM_IMPROVEMENT_TYPE`、`PARAM_OPERATION_TYPE`、`PARAM_WMD_TYPE`、`PARAM_FLAGS` | `Civ6Common.lua:105-106`、`:140`；`TradeRouteChooser.lua:813-816`；`UnitPanel.lua:568`、`:642`；`Choosers/TradeOriginChooser.lua:68`；`Base/Assets/UI/Popups/RazeCity.lua:17` |

移动修正符 `UnitOperationMoveModifiers.*`：`NONE`、`ATTACK`、`MOVE_IGNORE_UNEXPLORED_DESTINATION`（`Civ6Common.lua:140`、`:147`、`:152`）【静态核对】。

### 3.3 移动单位（最常用，官方完整分支）

官方 `MoveUnitToPlot` → `RequestMoveOperation`（`Base/Assets/UI/Civ6Common.lua:102-169`）【静态核对】：

```lua
local tParameters = {};
tParameters[UnitOperationTypes.PARAM_X] = plotX;      -- :105
tParameters[UnitOperationTypes.PARAM_Y] = plotY;      -- :106

-- 空军：AIR_ATTACK / DEPLOY
tParameters[UnitOperationTypes.PARAM_MODIFIERS] = UnitOperationMoveModifiers.ATTACK;
if UnitManager.CanStartOperation(kUnit, UnitOperationTypes.AIR_ATTACK, nil, tParameters) then
    UnitManager.RequestOperation(kUnit, UnitOperationTypes.AIR_ATTACK, tParameters);
elseif UnitManager.CanStartOperation(kUnit, UnitOperationTypes.DEPLOY, nil, tParameters) then
    UnitManager.RequestOperation(kUnit, UnitOperationTypes.DEPLOY, tParameters);
end

-- 陆军/海军
tParameters[UnitOperationTypes.PARAM_MODIFIERS] = UnitOperationMoveModifiers.NONE;
if UnitManager.CanStartOperation(kUnit, UnitOperationTypes.RANGE_ATTACK, nil, tParameters)
   and (kUnit:GetRangedCombat() > kUnit:GetCombat() or kUnit:GetBombardCombat() > kUnit:GetCombat()) then
    UnitManager.RequestOperation(kUnit, UnitOperationTypes.RANGE_ATTACK, tParameters);
else
    tParameters[UnitOperationTypes.PARAM_MODIFIERS] =
        UnitOperationMoveModifiers.ATTACK + UnitOperationMoveModifiers.MOVE_IGNORE_UNEXPLORED_DESTINATION;
    if UnitManager.CanStartOperation(kUnit, UnitOperationTypes.COASTAL_RAID, nil, tParameters) then
        UnitManager.RequestOperation(kUnit, UnitOperationTypes.COASTAL_RAID, tParameters);
    elseif plotX ~= kUnit:GetX() or plotY ~= kUnit:GetY() then
        if UnitManager.CanStartOperation(kUnit, UnitOperationTypes.SWAP_UNITS, nil, tParameters) then
            UnitManager.RequestOperation(kUnit, UnitOperationTypes.SWAP_UNITS, tParameters);
        else
            UnitManager.RequestOperation(kUnit, UnitOperationTypes.MOVE_TO, tParameters);   -- :163 兜底
        end
    end
end
```

> 关键点：**移动其实就是 `MOVE_TO` + `PARAM_X`/`PARAM_Y`**；上层逻辑只是用更具体的操作去覆盖"顺便攻击/换位/飞机"的特例。做 AI 驱动时，直接用 `MOVE_TO` + 坐标最省事，但会失去"到达即攻击"的行为。
> 另一个官方入口：`UI.SetInterfaceMode(InterfaceModeTypes.MOVE_TO)` 让玩家自己点目标（`UnitPanel.lua:2612-2616`）——这是 UI 交互路径，自动化里不推荐。

**宣战保护**：官方在移动前会查 `CombatManager.IsAttackChangeWarState(componentId, x, y)`（`Civ6Common.lua:116`），若会引发宣战则弹确认框而不直接移动。AI 驱动若要"绕过确认直接打"，需自行跳过该检查（行为差异【待运行时验证】）。

### 3.4 建城 / 造改良 / 远程攻击

```lua
-- 建城（UnitPanel.lua:2621-2642）：先判定，结果里可能提示会移除地貌
local bCanStart, kResults = UnitManager.CanStartOperation(pUnit, UnitOperationTypes.FOUND_CITY,
                                                          nil, false, OperationResultsTypes.ALL);
if bCanStart then
    UnitManager.RequestOperation(pUnit, UnitOperationTypes.FOUND_CITY);   -- :2636 / :2641
end

-- 造改良（UnitPanel.lua:2548-2557）：坐标必须给
local tParameters = {};
tParameters[UnitOperationTypes.PARAM_X] = pUnit:GetX();
tParameters[UnitOperationTypes.PARAM_Y] = pUnit:GetY();
tParameters[UnitOperationTypes.PARAM_IMPROVEMENT_TYPE] = improvementHash;   -- GameInfo.Improvements[...].Hash
UnitManager.RequestOperation(pUnit, UnitOperationTypes.BUILD_IMPROVEMENT, tParameters);

-- 远程攻击（WorldInput.lua:839-849）：目标用坐标
local plot = Map.GetPlotByIndex(plotID);
local tParameters = {};
tParameters[UnitOperationTypes.PARAM_X] = plot:GetX();
tParameters[UnitOperationTypes.PARAM_Y] = plot:GetY();
UnitManager.RequestOperation(pUnit, UnitOperationTypes.RANGE_ATTACK, tParameters);
```

`CanStartOperation` 返回的 `tResults` 是**表**，常用键 `UnitOperationResults.*`【静态核对】：
`IMPROVEMENTS`（可选改良列表）、`BEST_IMPROVEMENT`、`FEATURE_TYPE`（会移除的地貌）、`ACTION_NAME`、`ADDITIONAL_DESCRIPTION`、`FAILURE_REASONS`、`PLOTS`、`MODIFIERS`、`MODIFIER_IS_TARGET`
—— 来源：`Base/Assets/UI/Panels/UnitPanel.lua:504-528`、`:561-596`、`:686-703`、`:3815-3818`。

### 3.5 单位指令（Command，与 Operation 不同）

```lua
UnitManager.RequestCommand(pUnit, actionHash [, tParameters]);   -- UnitPanel.lua:2513
```

`UnitCommandTypes` 观测成员【静态核对】：`DELETE`、`CANCEL`、`NAME_UNIT`、`PROMOTE`、`UPGRADE`、`FORM_CORPS`、`FORM_ARMY`、`ENTER_FORMATION`、`AIRLIFT`、`TRANSFORM_UNIT`、`RESTORE_UNIT_MOVES`、`KILL_WEAKER_UNIT`、`NAVAL_GOLD_RAID`、`CONDEMN_HERETIC`、`MOVE_JUMP`、`WAKE`、`TYPE`，参数键 `PARAM_NAME`、`PARAM_PROMOTION_TYPE`、`PARAM_UNIT_ID`、`PARAM_UNIT_PLAYER`、`PARAM_X`、`PARAM_Y`
—— 来源：`UnitPanel.lua:412-448`、`:2602-2604`；`WorldInput.lua:2880-2882`、`:3030-3036`、`:3149-3154`、`:3272-3273`、`:3332-3333`；`WorldTracker.lua:955`。

`CanStartCommand` 观测形式：`CanStartCommand(unit, cmd, true)` / `CanStartCommand(unit, cmd, nil, true)` / `CanStartCommand(unit, cmd, false, tParameters, true)` —— `UnitPanel.lua:419`、`:437`、`:448`、`:454`、`:461-471`【静态核对】；参数语义【待运行时验证】。

### 3.6 UnitManager 其它观测成员

| 调用 | 说明 | 来源 |
| --- | --- | --- |
| `GetUnit(playerId, unitId)` | 取单位对象 | `Automation_ObserverCamera.lua:571` |
| `GetTypeName(unit)` | 类型名（`UNIT_xxx`） | `Base/Assets/Scenarios/Tutorial/TutorialScenarioBase.lua:1243` |
| `GetOperationTypeName(unit)` | 当前操作名 | `Debug/Unit.ltp:323` |
| `GetActivityType(unit)` | 活动类型 | `UnitPanel.lua:2147` |
| `GetQueuedDestination(unit)` | 已排队目标格 | `Base/Assets/UI/WorldInput.lua:821` |
| `GetTravelTime(unit, city)` / `GetEstablishInCityTime(unit, city)` | 间谍行程 | `Choosers/EspionageChooser.lua:404-405` |
| `GetTimeToComplete(op, unit)` | 操作所需回合 | `Base/Assets/UI/EspionageSupport.lua:30` |
| `GetResultProbability(op, unit, plot)` | 结果概率表 | `EspionageSupport.lua:35` |
| `Kill(unit, bDestroy)` | 删除单位 | `Debug/Unit.ltp:51`、`:65` |
| `RestoreMovementToFormation(unit)` / `RestoreUnitAttacks(unit)` | 恢复移动/攻击 | `Debug/Unit.ltp:24-25` |
| `GetUnitMaintenance(hash)` / `GetUnitCorpsMaintenance` / `GetUnitArmyMaintenance` / `GetUnitTypeBaseLifespan` | 费用/寿命 | `Base/Assets/UI/Screens/ReportScreen.lua:319-334`；`Civilopedia/CivilopediaPage_Unit.lua:354` |

单位对象（`pUnit`）观测成员：`GetID`、`GetOwner`、`GetX`、`GetY`、`GetUnitType`、`GetType`、`GetComponentID`、`IsDead`、`GetMovesRemaining`、`GetDamage`/`SetDamage`/`ChangeDamage`、`GetExperience():ChangeExperience(n)`、`GetCombat`/`GetRangedCombat`/`GetBombardCombat`、`GetReligion():GetReligionType()`
—— 来源：`UnitPanel.lua:545`、`:2553-2554`、`Civ6Common.lua:110-111`、`:148`、`Debug/Unit.ltp:37`、`:49-53`、`:485-493`【静态核对】。

---

## 4. 城市生产

### 4.1 核心调用

```lua
CityManager.RequestOperation(city, CityOperationTypes.BUILD, tParameters);
-- 能不能造（第 4 参 true = 要结果表）
local bCanStart, tResults = CityManager.CanStartOperation(city, CityOperationTypes.BUILD, tParameters, true);
```

【静态核对】4 参 `CanStartOperation` 见 `Base/Assets/UI/StrategicView_MapPlacement.lua:220`；3 参 `RequestOperation` 见 `Base/Assets/UI/Panels/ProductionPanel.lua:301`、`:315`、`:370`、`:403`、`:418`。
【待运行时验证】`CanStartOperation` 第 4 参是否严格为布尔（官方只出现过 `true`）。

### 4.2 参数键（按生产对象选一个）

| 要生产 | 参数键 | 值来源 | 来源 |
| --- | --- | --- | --- |
| 单位 | `CityOperationTypes.PARAM_UNIT_TYPE` | `GameInfo.Units[type].Hash` / 列表项 `unitEntry.Hash` | `ProductionPanel.lua:299` |
| 建筑/奇观 | `PARAM_BUILDING_TYPE` | `buildingEntry.Hash` | `ProductionPanel.lua:368`、`:361` |
| 区域 | `PARAM_DISTRICT_TYPE` | `districtEntry.Hash` | `ProductionPanel.lua:401`、`:394` |
| 项目 | `PARAM_PROJECT_TYPE` | `projectEntry.Hash` | `ProductionPanel.lua:416` |
| 军团/军队 | `MILITARY_FORMATION_TYPE` | `MilitaryFormationTypes.CORPS_MILITARY_FORMATION` / `ARMY_MILITARY_FORMATION` | `ProductionPanel.lua:314`、`:328` |
| 放置坐标（区域/奇观必须） | `PARAM_X` / `PARAM_Y` | `plot:GetX()` / `plot:GetY()` | `StrategicView_MapPlacement.lua:47-48`、`:205-207` |
| 队列插入模式 | `PARAM_INSERT_MODE` | `VALUE_APPEND` / `VALUE_REPLACE_AT` / `VALUE_REMOVE_AT` / `VALUE_SWAP` / `VALUE_MOVE_TO` / `VALUE_EXCLUSIVE` | `ProductionPanel.lua:2885-2899`；`ProductionHelper.lua:199-224` |
| 队列位置 | `PARAM_QUEUE_LOCATION` / `PARAM_QUEUE_SOURCE_LOCATION` / `PARAM_QUEUE_DESTINATION_LOCATION` | 整数索引（0 起） | `ProductionHelper.lua:200`、`:210-211`；`ProductionPanel.lua:2890` |

### 4.3 最简"造单位"和"造区域"

```lua
-- 造单位（ProductionPanel.lua:293-303 的等价最小写法）
local tParameters = {};
tParameters[CityOperationTypes.PARAM_UNIT_TYPE] = GameInfo.Units["UNIT_WARRIOR"].Hash;
tParameters[CityOperationTypes.PARAM_INSERT_MODE] = CityOperationTypes.VALUE_REPLACE_AT;
tParameters[CityOperationTypes.PARAM_QUEUE_DESTINATION_LOCATION] = 0;   -- 0 = 当前生产
CityManager.RequestOperation(pCity, CityOperationTypes.BUILD, tParameters);

-- 造需要选位置的区域（StrategicView_MapPlacement.lua:204-220 的等价写法）
local kPlot = Map.GetPlot(x, y);
local tParameters = {};
tParameters[CityOperationTypes.PARAM_X] = kPlot:GetX();
tParameters[CityOperationTypes.PARAM_Y] = kPlot:GetY();
tParameters[CityOperationTypes.PARAM_DISTRICT_TYPE] = GameInfo.Districts["DISTRICT_CAMPUS"].Hash;
tParameters[CityOperationTypes.PARAM_INSERT_MODE] = CityOperationTypes.VALUE_APPEND;
local bCanStart, tResults = CityManager.CanStartOperation(pCity, CityOperationTypes.BUILD, tParameters, true);
if bCanStart then
    CityManager.RequestOperation(pCity, CityOperationTypes.BUILD, tParameters);
end

-- 从队列删除 / 交换（ProductionHelper.lua:196-226）
tParameters[CityOperationTypes.PARAM_INSERT_MODE] = CityOperationTypes.VALUE_REMOVE_AT;
tParameters[CityOperationTypes.PARAM_QUEUE_LOCATION] = queueIndex;
CityManager.RequestOperation(pCity, CityOperationTypes.BUILD, tParameters);
```

> `CanStartOperation` 的 `tResults` 里常用 `CityOperationResults.SUCCESS_CONDITIONS`（字符串数组，需 `Locale.Lookup`）— `StrategicView_MapPlacement.lua:61-67`、`:226-232`【静态核对】。

### 4.4 购买（Command 而非 Operation）

```lua
local tParameters = {};
tParameters[CityCommandTypes.PARAM_UNIT_TYPE] = unitEntry.Hash;
tParameters[CityCommandTypes.PARAM_MILITARY_FORMATION_TYPE] = MilitaryFormationTypes.STANDARD_MILITARY_FORMATION;
tParameters[CityCommandTypes.PARAM_YIELD_TYPE] = GameInfo.Yields["YIELD_GOLD"].Index;   -- 或 YIELD_FAITH
CityManager.RequestCommand(pCity, CityCommandTypes.PURCHASE, tParameters);
```

来源：`ProductionPanel.lua:423-434`、`:449`、`:464`、`:478`；`StrategicView_MapPlacement.lua:218`、`:238`、`:242`【静态核对】。

`CityCommandTypes` 观测成员：`PURCHASE`、`RANGE_ATTACK`、`WMD_STRIKE`、`SET_FOCUS`、`MANAGE`、`NAME_CITY`、`DESTROY`、`SWAP_TILE_OWNER`；参数键 `PARAM_UNIT_TYPE`、`PARAM_BUILDING_TYPE`、`PARAM_DISTRICT_TYPE`、`PARAM_YIELD_TYPE`、`PARAM_PLOT_PURCHASE`、`PARAM_X`/`PARAM_Y`/`PARAM_X0`/`PARAM_Y0`/`PARAM_X1`/`PARAM_Y1`、`PARAM_RANGED_ATTACK`、`PARAM_WMD_TYPE`、`PARAM_MANAGE_CITIZEN`、`PARAM_SWAP_TILE_OWNER`、`PARAM_NAME`、`PARAM_DATA0`、`PARAM_FLAGS`
—— 来源：`ProductionPanel.lua:425-478`、`:1639-1640`；`Panels/CityPanel.lua:448-477`、`:616-629`；`StrategicView_MapPlacement.lua:198`；`WorldInput.lua:2232-2271`、`:2575`；`WorldView/PlotInfo.lua:60-78`；`CityPanelOverview.lua:763-765`【静态核对】。

### 4.5 City 对象 / CityManager 其它

| 调用 | 说明 | 来源 |
| --- | --- | --- |
| `pCity:GetBuildQueue()` → `:AddProgress(n)`、`:GetAt(i)`、`:HasBeenPlaced(hash)` | 生产队列 | `Debug/City.ltp:106-107`；`ProductionHelper.lua:179`、`:185`；`ProductionPanel.lua:345` |
| `pCity:ChangePopulation(delta)` | 人口 | `Debug/City.ltp:28`、`:40` |
| `pCity:SetProperty(key, valueOrNil)` | 城市属性 | `Debug/City.ltp:288`、`:301` |
| `pCity:GetDistricts():GetDistrictAtLocation(x, y)` → `:ChangeDamage(type, delta)` / `:SetPillaged(b)` / `:IsPillaged()` | 区域 | `Debug/City.ltp:118-122`、`:334-336` |
| `pCity:GetBuildings():HasBuilding(hash)` | 建筑 | `ProductionPanel.lua:352` |
| `pCity:GetName()` / `GetX()` / `GetY()` / `GetID()` / `GetOwner()` | 基本属性 | `Debug/City.ltp:415`、`:120` |
| `CityManager.GetCity(player, id)` / `GetCityAt(x, y)` | 取城市 | `ProductionHelper.lua:178`；`GenVFX.lua:32` |
| `CityManager.SetAsCapital(city)` / `SetAsOriginalCapital(city)` / `TransferCityToFreeCities(city)` | 改归属 | `Debug/City.ltp:314`、`:325`、`:277` |
| `Cities.DestroyCity(city)` | 摧毁城市 | `Debug/City.ltp:95` |
| `CityManager.CanStartCommand(city, cmd, wantResults, params, ...)` | 判定（5 参形式） | `ProductionPanel.lua:1639-1640`【待运行时验证】参数顺序 |

---

