# 收藏品系统 (Collectibles / Rarity Item System)

> 来源：Collectibles Mode (3565119013)
> 完整独立系统，基于 Lua 实现的收藏品/道具框架

## 概述

一个完整的收藏品/道具系统，核心概念：
- 每个玩家拥有独立的收藏品库存（通过 Player Property 持久化）
- 收藏品分稀有度 (Rarity 0-7)，影响获取概率和售价
- 双阶段 Modifier：**出生效果**（获取时永久获得）+ **激活效果**（主动使用，有冷却/容量限制）
- 代币 (Token) 经济系统：分数、利息、时代工资等收入来源
- 商店系统：随机商品列表，可购买
- 发现系统：随机获取收藏品（带稀有度级联判定）

## 架构

```
┌──────────────────────────────────────┐
│  数据库定义层                         │
│  Ophidy_Collectibles (收藏品定义)     │
│  Ophidy_Collectible_BirthModifier     │
│  Ophidy_Collectible_ActiveModifier    │
│  GlobalParameters (全局参数)          │
└──────────┬───────────────────────────┘
           │
┌──────────▼───────────────────────────┐
│  CollectibleManager (核心管理器)      │
│  - 收藏品 CRUD                        │
│  - 代币系统                           │
│  - 稀有度判定                         │
│  - 发现/商店                          │
└──────────┬───────────────────────────┘
           │
┌──────────▼───────────────────────────┐
│  Collectibles_Handler (事件处理)      │
│  - 回合迭代 (代币收入 + 时代礼物)     │
│  - 注册 UI→GP GameEvents              │
└──────────┬───────────────────────────┘
           │
┌──────────▼───────────────────────────┐
│  UI模块                               │
│  - Collectibles_MainPanel (主面板)    │
│  - Collectibles_Popup (详情弹窗)      │
│  - Collectibles_Button (入口按钮)     │
└──────────────────────────────────────┘
```

## XML 配合

### Collectibles_Button.xml — LaunchBar 入口按钮

`UI/Additions/Collectibles_Button.xml` 在游戏顶部 LaunchBar 挂入收藏品入口按钮：

```xml
<Context FontStyle="Stroke">
    <Instance Name="ButtonInstance">
        <Button ID="Button" Size="49,49" Texture="LaunchBar_Hook_GreatWorksButton"
                ToolTip="LOC_UI_COLLECTIBLES_PANEL_BUTTON_TOOLTIP">
            <Image ID="Icon" Texture="LaunchButton_Hook_Ovd_CollectiblesButton"
                   Size="35,35"/>
            <Label ID="AlertIndicator" String="[ICON_New]" Hidden="1"/>
        </Button>
    </Instance>
</Context>
```

`AlertIndicator` 用于提示有新收藏品/商品可领取。

### Collectibles_MainPanel.xml — 收藏品主管界面

`UI/Additions/Collectibles_MainPanel.xml` 定义了完整的收藏品管理面板（1536x768），分两个 Tab：
- **Showcase（收藏品展示）**：顶部已激活收藏品滚动面板（`CollectiblesActivatedScrollPanel`）+ 下方全部收藏品列表（`CollectiblesListStack`），支持按类别筛选和激活操作
- **Trader（交易/商店）**：代币余额显示（`Tokens`）+ 刷新按钮 + 商品列表（`GoodsStack`），支持购买收藏品

面板使用 `GreatWorks_Background` 纹理风格。

### Collectibles_Popup.xml — 收藏品详情弹窗

`UI/Additions/Collectibles_Popup.xml` 为单个收藏品提供详情弹窗，显示：稀有度、出生效果描述、激活效果描述、冷却时间、持有数量、操作按钮（激活/购买/发现等）。

### Collectibles_theme1.xml / Collectibles_theme2.xml — 主题数据

定义各主题下收藏品的游戏数据（通过 `ExposedMembers` 暴露给 GP 端）。每个主题有独立的 SQL 数据文件和文本文件（`Collectibles_themeN_xx_XX.xml`）。

### Collectibles_UI_Text.xml — 界面文本

所有按钮、标签、提示的本地化文本。

### Civilopedia.xml — 百科页面

收藏品系统的百科条目定义。

---

## SQL 核心定义

### 1. 收藏品定义表

```sql
CREATE TABLE IF NOT EXISTS 'Ophidy_Collectibles' (
    'CollectibleType'  TEXT NOT NULL,
    'Name'             TEXT NOT NULL,
    'Description'      TEXT NOT NULL,
    'BirthDesc'        TEXT,            -- 出生效果描述
    'ActiveDesc'       TEXT,            -- 激活效果描述
    'Rarity'           INT NOT NULL CHECK (Rarity IN (0,1,2,3,4,5,6,7)) DEFAULT 1,
    'Cooldown'         INT NOT NULL DEFAULT 20,          -- 冷却时间(回合)
    'TraitType'        TEXT DEFAULT NULL,                 -- 专属某文明/领袖
    'Unchangeable'     BOOLEAN NOT NULL CHECK (Unchangeable IN (0,1)) DEFAULT 0,
    'StackLimit'       INT NOT NULL DEFAULT 1,           -- 最大可持有数量
    'Tradable'         BOOLEAN NOT NULL CHECK (Tradable IN (0,1)) DEFAULT 1,
    'MustPurchase'     BOOLEAN NOT NULL CHECK (MustPurchase IN (0,1)) DEFAULT 0,
    'MaxInstance'      INT,                              -- 全局最大生成数量
    'Cost'             INT,                              -- 手动定价（覆盖自动计算）
    'ExplicitUnlock'   BOOLEAN NOT NULL CHECK (ExplicitUnlock IN (0,1)) DEFAULT 0,
    PRIMARY KEY (CollectibleType)
);
```

### 2. 效果挂载表

```sql
CREATE TABLE IF NOT EXISTS 'Ophidy_Collectible_BirthModifier' (
    'CollectibleType' TEXT NOT NULL,
    'ModifierId'      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS 'Ophidy_Collectible_ActiveModifier' (
    'CollectibleType' TEXT NOT NULL,
    'ModifierId'      TEXT NOT NULL
);
```

### 3. 全局参数

```sql
INSERT INTO GlobalParameters (Name, Value) VALUES
('PARAMETER_OPHIDY_COLLECTIBLE_GOODS_NUM',        7),   -- 每次刷新商品数
('PARAMETER_OPHIDY_COLLECTIBLE_MAX_DISCOUNT',     80),  -- 最大折扣%
('PARAMETER_OPHIDY_COLLECTIBLE_ERA_CHANGE_GIFT',  1),   -- 新时代礼物数量
('PARAMETER_OPHIDY_COLLECTIBLE_MEETING_GIFT',     2),   -- 初次见面礼物数量
('PARAMETER_OPHIDY_COLLECTIBLE_ACTIVE_CAPACITY',  1),   -- 初始激活容量
('PARAMETER_OPHIDY_COLLECTIBLE_NUM_DISCOVERS',    3),   -- 每次发现数量
('PARAMETER_OPHIDY_COLLECTIBLE_MAX_RARITY_INIT',  3),   -- 初始稀有度上限
('PARAMETER_OPHIDY_COLLECTIBLE_MAX_INTEREST',     100), -- 利息上限
('PARAMETER_OPHIDY_COLLECTIBLE_PRICE_ERA_PROGRESS', 0.3); -- 时代价格系数

-- 每级稀有度基准价格
('PARAMETER_OPHIDY_COLLECTIBLE_COST_0', 20),
('PARAMETER_OPHIDY_COLLECTIBLE_COST_1', 60),
-- ... 直至 COST_6 = 800
```

### 4. 容量随时代增长

```sql
CREATE TEMPORARY TABLE Collectibles_CapacityIncreaseEra (
    EraType TEXT NOT NULL, Amount INT NOT NULL
);
-- 古典+1, 中世纪+1, 文艺复兴+2, 工业+1, 现代+1, 原子+2, 信息+1, 未来+1
```

### 5. 自定义 DynamicModifier

```sql
-- 给所有玩家调属性（用于全局效果）
INSERT INTO DynamicModifiers (ModifierType, CollectionType, EffectType) VALUES
('MODTYPE_OCM_ALL_PLAYERS_ADJUST_PROPERTY', 'COLLECTION_ALL_PLAYERS',
 'EFFECT_ADJUST_PLAYER_PROPERTY');
```

## Lua 核心实现

### 一、CollectibleManager（核心管理器）

管理器使用 `setmetatable` 模式，每个玩家一个实例（通过 Player Property 存取）。

#### 数据结构

```lua
-- 保存在 pPlayer:GetProperty("Ophidy_CollectiblesData") 中
{
    CollectiblesInfo = {  -- [index] = {
        --   所有 Ophidy_Collectibles 表的字段,
        --   BuildCount, StackCount (运行时),
        --   BirthModifiers = {ModifierId, ...},
        --   ActiveModifiers = {ModifierId, ...}
        }
    },
    BusyCapacity = 0,          -- 已占用的激活容量
    Token = 0,                 -- 代币余额
    Activatings = {            -- [index] = remainingCooldown
    },
    Existings = {index, ...},  -- 持有的收藏品Index列表
    Waitings = {               -- [index] = 剩余可获取次数 (-1=无限)
    },
    Goods = {                  -- 当前商店商品
        {Index, CollectibleType, Rarity, Cost, BirthModifiers, ActiveModifiers}
    }
}
```

#### 获取玩家收藏品实例

```lua
function CollectibleManager:GetCollectibles(iPlayer)
    local pPlayer = Players[iPlayer]
    if pPlayer then
        local o = {}
        setmetatable(o, self)
        self.__index = self

        local SavedData = pPlayer:GetProperty("Ophidy_CollectiblesData") or {}
        o.CollectiblesInfo = SavedData.CollectiblesInfo or {}
        o.BusyCapacity      = SavedData.BusyCapacity or 0
        o.Token             = SavedData.Token or 0
        o.Activatings       = SavedData.Activatings or {}
        o.Existings         = SavedData.Existings or {}
        o.Waitings          = SavedData.Waitings or o:InitPlayerWaitings(iPlayer)
        o.Goods             = SavedData.Goods or {}
        o.iPlayer           = iPlayer
        return o
    end
end
```

#### 创建收藏品

```lua
function CollectibleManager:CreateCollectible(iCollectible, enableExplicitUnlock)
    if self:IsCollectibleAvailable(iCollectible) or
       (enableExplicitUnlock and GameInfo.Ophidy_Collectibles[iCollectible].ExplicitUnlock) then
        local CollectibleInfo = self:GetCollectible(iCollectible) or self:InitCollectibleInfo(iCollectible)
        CollectibleInfo.BuildCount = CollectibleInfo.BuildCount + 1
        CollectibleInfo.StackCount = CollectibleInfo.StackCount + 1

        -- 出生效果：永久附加 Modifier
        for _, ModifierId in ipairs(CollectibleInfo.BirthModifiers) do
            Players[self.iPlayer]:AttachModifierByID(ModifierId)
        end

        table.insert(self.Existings, iCollectible)
        self.CollectiblesInfo[iCollectible] = CollectibleInfo

        -- 扣减可获取次数
        if self.Waitings[iCollectible] and self.Waitings[iCollectible] > 0 then
            self.Waitings[iCollectible] = self.Waitings[iCollectible] - 1
        end

        self:SaveCollectiblesData()
        GameEvents.Ophidy_Collectible_Added.Call(self.iPlayer, iCollectible)
        return true
    end
    return false
end
```

#### 随机创建（带稀有度判定）

```lua
function CollectibleManager:CreateRandomCollectible(kParam)
    local minRarity = kParam.minRarity or 1
    local maxRarity = kParam.maxRarity or 6
    local applyRarityBonus = kParam.applyRarityBonus or false

    -- 稀有度判定
    local Rarity = self:DetermineRarity(minRarity, maxRarity, extraLuck, applyRarityBonus)

    -- 在该稀有度下随机选一个可用的收藏品
    local iCollectible = self:FindRandomCollectible(Rarity, includePurchase, mustPurchase)
    if iCollectible > -1 then
        return self:CreateCollectible(iCollectible)
    end
    return false
end
```

#### 稀有度判定算法（级联机制）

```lua
function CollectibleManager:DetermineRarity(minRarity, maxRarity, extraLuck, applyRarityBonus)
    -- 基础成功率 40%，可通过属性加成
    local CheckDifficulty = tonumber(
        GameConfiguration.GetValue("Opd_Luck") or 40
    ) + (pPlayer:GetProperty("PARAMETER_OPHIDY_COLLECTIBLE_EXTRA_LUCKY") or 0)

    local success = true
    local Rarity = 1

    -- 逐级判定：从1开始，每次成功稀有度+1，直到失败或达到上限
    while success and Rarity < maxRarity do
        local randnum = Game.GetRandNum(100, "Rarity Jump") + 1
        if randnum <= CheckDifficulty then
            Rarity = Rarity + 1
        else
            success = false
        end
    end
    Rarity = math.max(Rarity, minRarity)
    return Rarity
end

-- 获取6级收藏品的概率为 (0.4)^5 = 1.024%
```

#### 激活收藏品

```lua
function CollectibleManager:ActivateCollectible(iCollectible)
    if self:IsCollectibleUsable(iCollectible) then
        -- 附加临时 Modifier
        for _, ModifierId in ipairs(CollectibleInfo.ActiveModifiers) do
            Players[self.iPlayer]:AttachModifierByID(ModifierId)
        end
        self.BusyCapacity = self.BusyCapacity + 1
        -- 冷却 = 基础冷却 × 游戏速度系数
        self.Activatings[iCollectible] = math.ceil(CollectibleInfo.Cooldown * SpeedMultiplier)
        self:SaveCollectiblesData()
        return true
    end
    return false
end
```

#### 释放收藏品（冷却到期）

```lua
function CollectibleManager:ChangeCollectiblesCooldown(amount)
    amount = amount or 1
    for iCollectible, cooldown in pairs(self.Activatings) do
        self.Activatings[iCollectible] = cooldown - amount
        if self.Activatings[iCollectible] <= 0 then
            self:ReleaseCollectible(iCollectible)
        end
    end
    self:SaveCollectiblesData()
end

function CollectibleManager:ReleaseCollectible(iCollectible)
    if self.Activatings[iCollectible] then
        for _, ModifierId in ipairs(CollectibleInfo.ActiveModifiers) do
            Players[self.iPlayer]:DetachModifierByID(ModifierId)  -- 需要DLL扩展
        end
        self.BusyCapacity = self.BusyCapacity - 1
        self.Activatings[iCollectible] = nil
        self:SaveCollectiblesData()
    end
end
```

### 二、Collectibles_Handler（事件处理）

#### 每回合代币计算

```lua
function Iterator(iPlayer)
    local pPlayer = Players[iPlayer]
    if pPlayer:IsHuman() then
        -- 初次见面礼物
        local b = pPlayer:GetProperty("COLLECTIBLES_GOT_MEETING_GIFT")
        if not b then
            CreateInitMultiCollectibles(iPlayer, num)
            CollectibleManager:GetCollectibles(iPlayer):GenerateGoods()
            pPlayer:SetProperty("COLLECTIBLES_GOT_MEETING_GIFT", true)
        end

        -- 时代变化礼物
        local b = pPlayer:GetProperty("COLLECTIBLES_GOT_ERA_CHANGE_GIFT_" .. iEra)
        if not b and iStartEra ~= iEra then
            CreateMultiCollectibles(iPlayer, num)
            CollectibleManager:GetCollectibles(iPlayer):GenerateGoods()
            pPlayer:SetProperty("COLLECTIBLES_GOT_ERA_CHANGE_GIFT_" .. iEra, true)
        end

        -- === 代币收入计算 ===
        local Increment = 0
        -- 1. 分数差额
        local ScoreChange = pPlayer:GetScore() - Stored
        Increment = Increment + ScoreChange
        -- 2. 利息：Token × InterestRate / 100 (上限100)
        -- 3. 时代工资：iEra + 1 (带时代系数)
        -- 4. 时代加成属性
        -- 5. 普通加成属性
        -- 6. Modifier 百分比
        -- 7. GameConfig 倍率
        CollectibleManager:GetCollectibles(iPlayer):ChangeToken(Increment)
    end
end

GameEvents.PlayerTurnStartComplete.Add(Iterator)
```

### 三、商店系统

```lua
-- 生成商品
function CollectibleManager:GenerateGoods(kParam)
    local Num = pPlayer:GetProperty("PARAMETER_OPHIDY_COLLECTIBLE_GOODS_NUM")
              or GlobalParameters.PARAMETER_OPHIDY_COLLECTIBLE_GOODS_NUM
    local Goods = {}
    local Pool = DB.Query("SELECT * FROM Ophidy_Collectibles WHERE Tradable = 1")
    while #Goods < Num and #Pool > 0 do
        local Good = table.remove(Pool, Game.GetRandNum(#Pool) + 1)
        if self:IsCollectibleAvailable(Good.Index) then
            table.insert(Goods, Good)
        end
    end
    self.Goods = Goods
end

-- 获取商品（带价格计算）
function CollectibleManager:GetGoods()
    -- 默认定价 = 稀有度基准价
    -- EraProgress: 价格 × (1 + 时代 × 0.3)
    -- 速度系数: × SpeedMultiplier
    -- 折扣: × (100 - discount%) / 100
    -- 各 GoodAdjustFunc 逐层处理
end

-- 购买
function CollectibleManager:PurchaseGood(iCollectible, cost)
    -- 从商品列表移除
    self:ChangeToken(-cost)
    self:CreateCollectible(iCollectible)
end
```

### 四、发现系统

```lua
-- 生成一组发现（随机稀有度）
function CollectibleManager:GenerateDiscover(kParam)
    local amount = amountOverride or defaultAmount
    local tBatch = {}
    repeat
        local Rarity = self:DetermineRarity(minRarity, maxRarity)
        local iCollectible = self:FindRandomCollectible(Rarity)
        table.insert(tBatch, iCollectible)
    until (#tBatch == amount)
    -- 传给UI显示
    ReportingEvents.SendLuaEvent('Ophidy_Collectible_Generate_DiscoverBatch', ...)
end

-- 从发现中选择一个获取
function CollectibleManager:CreateDiscover(tBatch, iCollectible)
    -- 先释放临时占用
    for _, index in ipairs(tBatch) do
        if self.Waitings[index] and self.Waitings[index] ~= -1 then
            self.Waitings[index] = self.Waitings[index] + 1
        end
    end
    self:CreateCollectible(iCollectible, true)
end
```

### 五、UI↔GP 通信

```lua
-- GP 端注册
GameEvents.Request_Ophidy_Collectibles_Activate.Add(Request_Ophidy_Collectibles_Activate)
GameEvents.Request_Ophidy_Collectibles_Purchase.Add(Request_Ophidy_Collectibles_Purchase)
GameEvents.Request_Ophidy_Collectibles_Discover.Add(Request_Ophidy_Collectibles_Discover)
GameEvents.Request_Ophidy_Collectibles_RefreshGoods.Add(Request_Ophidy_Collectibles_RefreshGoods)

-- GP → UI: 通过 ReportingEvents 发送事件
ReportingEvents.SendLuaEvent('Ophidy_Collectible_Activated', {iPlayer, iCollectible})
ReportingEvents.SendLuaEvent('Ophidy_Collectible_Generate_DiscoverBatch', {iPlayer, tBatch})

-- GP → UI: 通过 GameEvents 发送事件
GameEvents.Ophidy_Collectible_Added.Call(iPlayer, iCollectible)
GameEvents.Ophidy_Collectible_Token_Changed.Call(iPlayer, eAmount)
```

## 关键 Property 列表

| Property Name | 存储位置 | 说明 |
|---|---|---|
| `Ophidy_CollectiblesData` | 玩家 | 核心数据容器（table通过json序列化） |
| `COLLECTIBLES_GOT_MEETING_GIFT` | 玩家 | 是否已领取初次见面礼 |
| `COLLECTIBLES_GOT_ERA_CHANGE_GIFT_N` | 玩家 | 是否已领取第N时代礼物 |
| `COLLECTIBLES_SCORE_STORED` | 玩家 | 上回合分数（用于计算差值） |
| `COLLECTIBLES_SCORE_CHANGED_INFO` | 玩家 | 代币收入明细 |
| `PARAMETER_OPHIDY_COLLECTIBLE_ACTIVE_CAPACITY` | 玩家 | 激活容量（可被Modifier修改） |
| `PARAMETER_OPHIDY_COLLECTIBLE_EXTRA_LUCKY` | 玩家 | 额外幸运值 |
| `PARAMETER_OPHIDY_COLLECTIBLE_TURN_TOKEN_CHANGE` | 玩家 | 每回合固定代币加成 |
| `PARAMETER_OPHIDY_COLLECTIBLE_TRADE_DISCOUNT` | 玩家 | 交易折扣% |

## 好感调整函数 (GoodAdjustFunc / RarityAdjustFunc)

框架通过函数名注册到表中，可扩展：

```lua
-- 商品价格调整
GoodAdjustFunc["EraProgress"] = function(self, Goods)
    -- 价格 × (1 + 时代 × 系数) × 速度系数
end
GoodAdjustFunc["GeneralDiscount"] = function(self, Goods)
    -- 价格 × (100 - discount) / 100
end
GoodAdjustFunc["FourleafDiscount"] = function(self, Goods)
    -- 第一个商品额外折扣
end

-- 稀有度范围调整
RarityAdjustFunc["ProfoundSilence"] = function(self, minRarity, maxRarity)
    -- 限制稀有度上限
end
```

## 主题系统

框架支持多主题（theme1, theme2），每个主题有独立的：
- `Collectibles_themeN.sql` — 收藏品定义
- `Collectibles_themeN.lua` (Script) — 主题专用脚本
- `CollectibleInfoHandler_themeN.lua` — 主题信息处理器
- 文本文件 `Collectibles_themeN_xx_XX.xml`

通过 `CollectibleManager_Addition_*.lua` 自动包含主题扩展。

## 注意事项

1. **DLL依赖**：`DetachModifierByID` 需要 DLL 扩展支持，原版游戏无此API
2. **AttachModifierByID**：原版游戏支持，已在游戏中可用
3. **Player Property 序列化**：所有数据打包为一个 table 存到 `Ophidy_CollectiblesData`，Lua table 可被自动序列化
4. **Waitings 机制**：每个收藏品有全局获取次数上限 (MaxInstance)，防止无限获取
5. **初始化 Waitings**：新游戏时检查 `TraitType`，不从专属收藏品开始等待
6. **收藏品初始化**：`InitCollectibleInfo` 会根据 `Ophidy_Collectibles` + 关联的 BirthModifier/ActiveModifier 构建完整信息表
