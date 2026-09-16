# 联机稳定通信写法（唯一提交者模式）

> ## ⚠️ 使用条件（先读）
>
> **仅当用户明确要求"联机稳定 / 联机可用 / 多人对局不重复"时，才使用本写法。**
> 普通单人 Mod / 未要求联机的功能，直接用简单写法（GP 端注册 GameEvents、UI 直接 RequestPlayerOperation），不要套用本模式。
>
> **两种变体（写代码前必须向用户确认选哪种）**
>
> - **变体 A（仅本地玩家提交）**：代价 = **AI 玩家无效果**。事件归属判定（`playerID == 本地玩家`）隐含排除 AI——AI 玩此文明时，UI 提交类功能完全不生效。
> - **变体 B（AI 兼容，推荐）**：主机（玩家 ID 0）的设备**代替 AI 玩家提交**，只需在归属判定里补充"是否为人类"判断（见 §二 变体 B）。代价 = 依赖**主机 = 玩家 ID 0** 这一大厅前提；按钮类交互仍仅人类有效（AI 无法点击），只有事件/回合驱动的自动逻辑对 AI 生效。单机下本地玩家即玩家 0、AI 由本机模拟 → **变体 B 同时让单机局 AI 有效果**。
>

---

## 一、为什么需要（联机的根本问题）

| 触发端                         | 问题                                                                 |
| ------------------------------ | -------------------------------------------------------------------- |
| GP 端`GameEvents.X` 直接触发 | 每台机器各自触发 → 修改游戏状态的代码执行**N 次**（N=玩家数） |
| UI 端事件（按钮点击）          | 只在点击者机器触发，但 UI 不能改游戏状态                             |

**结论：修改游戏状态的逻辑必须满足两个条件——① 由唯一一方提交；② 提交后在所有机器恰好执行一次。**

## 二、核心模式（UI 唯一提交者 → EXECUTE_SCRIPT → GP 回调）

```
[事件归属玩家] --(仅当==本地玩家)--> UI.RequestPlayerOperation(EXECUTE_SCRIPT)
        --> 广播到所有机器，每台执行一次 --> GameEvents.回调名.Add(...)
```

**UI 端（唯一提交者判断 + 委托）：**

```lua
local localPlayerID = Network.IsInGameStartedState() and Game.GetLocalPlayer() or Network.GetLocalPlayerID();
-- 事件归属玩家必须 == 本地玩家，否则不提交（多台机器各发一次 = 重复执行）
if playerID ~= localPlayerID then return end;

UI.RequestPlayerOperation(localPlayerID, PlayerOperations.EXECUTE_SCRIPT, {
    OnStart = 'SIQI_XXXX_SKILL_ACTIVATE',  -- 事件名（GP 端监听）
    UnitID  = unitID,                      -- 任意参数字段，原样传给 GP
});
```

**GP 端（回调）：**

```lua
GameEvents.SIQI_XXXX_SKILL_ACTIVATE.Add(function(unitID)
    -- EXECUTE_SCRIPT 广播保证：每台机器恰好执行一次
    -- 这里可以安全地修改游戏状态
end);
```

### 变体 B：AI 兼容（主机代替 AI 提交）

原判定的代价是"AI 玩家无效果"。若用户要求 AI 玩本文明也有效果，改用以下判定：
**AI 归属的事件由主机（玩家 ID 0）的设备代为提交**，归属判定只多一个"是否为人类"判断。

```lua
-- UI 端（唯一提交者判断 · AI 兼容版）
local localPlayerID = Network.IsInGameStartedState() and Game.GetLocalPlayer() or Network.GetLocalPlayerID();

-- 人类判断（lua_api 已验证：[UI] PlayerConfiguration:IsHuman()）
local function IsHuman(playerID)
    local pConfig = PlayerConfigurations[playerID];
    return pConfig ~= nil and pConfig:IsHuman();
end

-- 提交者判定（保证每个归属玩家全局恰好一个提交者）：
--   ① 归属者 == 本地玩家 → 本人设备提交（人类）
--   ② 归属者是 AI 且本地是玩家 ID 0（主机）→ 主机设备代替 AI 提交
if playerID ~= localPlayerID and (localPlayerID ~= 0 or IsHuman(playerID)) then return end;

UI.RequestPlayerOperation(localPlayerID, PlayerOperations.EXECUTE_SCRIPT, {
    OnStart         = 'SIQI_XXXX_SKILL_ACTIVATE', -- 事件名（GP 端监听）
    TargetPlayerID  = playerID,                   -- ⚠️ 必须传归属者 ID：AI 场景下 ≠ 本地玩家
    UnitID          = unitID,                     -- 任意参数字段，原样传给 GP
});
```

**GP 端回调**：用 `params.TargetPlayerID` 定位 `Players[TargetPlayerID]` 施加效果，**不能默认本地玩家**。

要点：

- 前提：**主机固定为玩家 ID 0**（多人大厅第一位；单机本地玩家即 0，AI 由本机模拟 → 变体 B 同时让单机 AI 生效）
- 事件在主机上对 AI 玩家有触发时机才可代提交（回合开始类有；按钮点击类无——AI 无法点击，交互功能对 AI 仍无效）
- 其余规则（EXECUTE_SCRIPT 广播、GP 仅执行、bIsFirstTime、Initialize 注册）与基础模式完全一致

## 三、GetLocalPlayerID 模板（UI 端所有事件入口统一）

```lua
local function GetLocalPlayerID()
    if Network.IsInGameStartedState() then
        return Game.GetLocalPlayer();   -- ← 这行必须保留，禁止批量替换成 GetLocalPlayerID()
    end
    return Network.GetLocalPlayerID();
end
```

- 游戏进行中：`Game.GetLocalPlayer()`；联机大厅/加载中：`Network.GetLocalPlayerID()`
- **踩过的坑**：批量替换 `Game.GetLocalPlayer()` 时会误伤本模板内部，形成无限递归（替换前先 replace_all 或精确带分号匹配；替换完立即检查模板是否完好）

## 四、bIsFirstTime 回合防护

联机下玩家回合可能**重复激活**（读档/网络同步），回合开始类逻辑必须过滤：

```lua
Events.PlayerTurnActivated.Add(function(playerID, bIsFirstTime)
    if not bIsFirstTime then return end;   -- 只处理首次激活
    -- 回合开始逻辑（过期状态清除等）
end);
```

## 五、事件注册规范（code-style 强制）

- 事件注册必须写在 `Initialize()` 内（`LoadGameViewStateDone.Add(Initialize)` 包裹属例外情形）
- 禁止 `GameEvents.X.Add(...)` 的省略号写法——注册时机不明、易重复注册

## 六、事件分类决策表（哪些走 UI 提交 / 哪些保留 GP）

| 事件/功能                                                                                   | 处理端                                                                                                           | 原因                                                                                                                                                                  |
| ------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 按钮/面板交互（技能激活、购买、选地格）                                                     | **UI 唯一提交者 → EXECUTE_SCRIPT → GP**                                                                  | 只有点击者触发；多机各发一次会重复                                                                                                                                    |
| EXECUTE_SCRIPT 的 GP 回调                                                                   | **无脑执行**——所有业务判断（合法性/条件/可用性）在 UI 完成，GP 仅执行+nil 防护（0050 冷酷之拥原则）      | UI 是信息最全/最新环境；GP 重复判断→双份逻辑，一处对一处错更难排查                                                                                                   |
| 项目完成/生产切换类效果（如"完成项目击杀辖区敌军"）                                         | **UI 判断项目类型 + UI 收集数据 → EXECUTE_SCRIPT → GP 仅执行**                                           | 每次生产变更都发=跨线程噪音；UI 收集用 [GP+UI] API（`pCity:GetOwnedPlots()` 是 **[GP]**，UI 改用 `Players[e]:GetUnits():Members()` + `pPlot:GetOwner()`） |
| `Events.PlayerTurnActivated` 回合开始                                                     | UI 端 +**bIsFirstTime 过滤**（变体 B：主机对 AI 回合同样处理）                                             | 归属玩家回合激活；联机可重复触发；AI 回合在主机同样触发 → 自动逻辑可对 AI 生效                                                                                       |
| `Events.Combat` / `UnitDamageChanged` / `UnitKilledInCombat` / `UnitRemovedFromMap` | **GP 直接**                                                                                                | 回合外触发、无 UI 时机                                                                                                                                                |
| 需定位**攻击者身份**的战斗效果（受击反伤等，0054 实测）                                | **攻击者侧 UI 唯一提交**：UI 监听 `Events.Combat`（判定防守方=目标文明单位且确实受击）→ 攻击者==本地玩家自提 / 攻击者是 AI 且本地=主机0 代发 → EXECUTE_SCRIPT → GP 无脑执行 + 防守方 Property 回合戳冷却 | 攻击由玩家在自己回合发起，必有 UI 时机；仅"被动受伤"类（无攻击者视角）保留 GP 直连                                                  |
| `GameEvents.OnPillage`（掠夺类：污染/封锁/挖掘奖励等）                                    | **避免使用 → 改 UI 按钮 + EXECUTE_SCRIPT**（0050 教训：联机不稳定，重写为"选中单位在敌方领土→点击按钮"） | 掠夺事件联机行为不可靠；改为玩家主动提交更稳定                                                                                                                        |
| `UnitAddedToMap` / `SetProperty`                                                        | GP 直接                                                                                                          | 幂等，重复执行无害                                                                                                                                                    |
| `DiplomacyDeclareWar`                                                                     | **避免使用**                                                                                               | 联机高频触发不可靠 → 用遍历战争状态或 modifier 替代                                                                                                                  |
| 信仰/资源累计消耗                                                                           | Property 存储（`HasProperty()` 判断）                                                                          | 跨机一致性，差值基准用变量                                                                                                                                            |

> **按钮/面板交互在变体 B 下仍仅人类有效**——AI 无法点击，凡涉及玩家选择的交互不适用 AI 兼容；只有自动/无选择逻辑（回合开始、事件驱动）才由主机代提交。

## 七、能 modifier 就不 Lua（联机稳定的终极方案）

引擎级 modifier 天然跨机一致，事件类 Lua 逻辑（回合外触发、高频）尽量替换：

| 场景         | modifier                                                                                                          |
| ------------ | ----------------------------------------------------------------------------------------------------------------- |
| 建城送单位   | `MODIFIER_PLAYER_BUILT_CITIES_GRANT_FREE_UNIT`（RunOnce=1 + AllowUniqueOverride + UnitType）                    |
| 一次性给产出 | `MODIFIER_PLAYER_GRANT_YIELD`（RunOnce=1 + Permanent=1 + Amount + ScaleByGameSpeed + YieldType）                |
| 宣战期间加成 | `MODIFIER_PLAYER_ADD_DIPLOMATIC_YIELD_MODIFIER`（DiplomaticYieldSource=WAR_DECLARATION_RECEIVED + TurnsActive） |
| 动态授予能力 | `ChangeAbilityCount`（本身就是动态授予能力，无需另加 GRANT_ABILITY 块）                                         |

## 八、排查要点（联机相关疑难）

1. 多机重复执行 → 检查是否所有提交点都做了"归属者==本地玩家 或（归属者是 AI 且本地==主机 0）"判断
2. 单机正常、联机失效 → 检查事件注册是否在 `Initialize()` 内（LoadGameViewStateDone 包裹）
3. 回合开始逻辑重复跑 → 检查 bIsFirstTime 过滤
4. AI 玩该文明无效果 → ① 确认用的是变体 B（主机代提交）而非变体 A；② 确认该功能在主机上有 AI 触发时机（回合开始类有，按钮类无）；③ 确认主机=玩家 ID 0
5. 战斗/击杀类仍保留 GP 直连（不要"为了统一"改成 UI 提交——它们没有 UI 触发时机，改了反而失效）
6. 变体 B 的 GP 回调施加效果的对象 → 用 `params.TargetPlayerID` 定位 `Players[TargetPlayerID]`，不能默认本地玩家（AI 场景下归属者 ≠ 本地玩家）
