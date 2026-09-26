# lua-binary -- 产出二进制：Property 与 AttachModifierByID

## 核心概念

### 为什么用二进制？

Property 是可由 Lua 读写、保存状态的键值；修改器的固定 Amount 不会自动乘以某个 Property 的数值。二进制把数值拆为少量固定 Amount 定义，避免为每个奖励金额注册一个 Modifier。它有“覆盖目标值”和“追加奖励增量”两种不同用法，先选场景再实现。

**二进制方案**：把一个大数值拆成多个二进制位，每个位对应一个独立的 Property 和 Modifier。

```
数值 10 (1010₂)：
  ┌─ SiqiMujica_Science2  = 1  → 触发 Modifier  Amount=2
  └─ SiqiMujica_Science8  = 1  → 触发 Modifier  Amount=8
                                  总产量修正 = 10
```

**核心优势**：
- **16 个位 → 16 层 Modifier**，最大值 = 1+2+4+...+32768 = 65535
- **循环利用**：每回合用 `SetPlotTwo` 把新值直接写入，旧值自动被覆盖
- **避免无限叠加**：不依赖 `ChangeProperty`（会累加），而是用 `SetProperty`（精确设值）
- **SQL 端自动匹配**：`REQUIREMENT_PLOT_PROPERTY_MATCHES` 检查每个位是否为 1，为 1 则激活对应 Modifier

### 两层映射关系

```
Lua 端（写 Property）:
  数值 10 → NumToTwo(10, 12) → {0,1,0,1,0,0,0,0,0,0,0,0}
  → SetProperty("MYKEY2", 1)
  → SetProperty("MYKEY8", 1)

SQL 端（读 Property → 激活 Modifier）:
  REQUIREMENT_PLOT_PROPERTY_MATCHES(PropertyName='MYKEY2', PropertyMinimum=1)
    → Modifier MY_MODIFIER_2 (Amount=2)
  REQUIREMENT_PLOT_PROPERTY_MATCHES(PropertyName='MYKEY8', PropertyMinimum=1)
    → Modifier MY_MODIFIER_8 (Amount=8)

结果: 地块获得 2+8=10 产出
```

### 正负数分离（NEG_ 前缀）

当数值可为负数时（如宜居度转产出可能为负），正数和负数存**不同的 Property 前缀**：

```
正值:  MYKEY1, MYKEY2, MYKEY4, ...
负值:  NEG_MYKEY1, NEG_MYKEY2, NEG_MYKEY4, ...
```

SQL 端生成两套 Modifier：
- `MY_MODIFIER_MYKEY_2` Amount=2（对应正数位）
- `MY_MODIFIER_NEG_MYKEY_2` Amount=-2（对应负数位）

---

## 二进制产出方案选择

| 需求 | 推荐方案 | 运行时职责 |
|---|---|---|
| 根据人口、宜居等状态重算，可能降低或清零 | Property 法 | GP 写入本系统目标总值的全部二进制位，包括将旧位关闭 |
| 少量事件给予不可撤销的永久固定产出 | AttachModifierByID 法 | 只把本次奖励增量拆位，给目标城市附加对应修改器 |
| 大量高频永久累加，希望限制实例增长 | 按需求选择 Property | 修改器定义少不等于运行时实例少；频繁 Attach 会累积实例 |
| 条件、期限、每人口、区域或地块产出 | 分别建模 | 不因都有 YieldType 就合并进永久城市固定产出 |

### Property 法：城市集合 + 市中心地块条件

文明专属城市固定产出可将 `MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_CHANGE` 挂到该文明/领袖 Trait，集合为 `COLLECTION_PLAYER_CITIES`、效果为 `EFFECT_ADJUST_CITY_YIELD_CHANGE`。每个位的 SubjectRequirementSet 使用 `REQUIREMENT_PLOT_PROPERTY_MATCHES` 检查该城市中心地块的位属性；Lua 仅写市中心 Property，不需要再逐城 Attach 一套控制器。确需跨所有玩家城市时才选择匹配的全局集合/挂载位置，不把玩家城市集合直接挂给 GameModifiers。

例如将本系统科技加成从 10 改成 7：先前 2、8 位开启，现在写成 1、2、4 位开启并关闭 8 位；归零时全部关闭。只更新变化位，避免每回合无变化也重复写入。位属性影响的是这组修改器，不会覆盖其他建筑自身的正常产出。

### AttachModifierByID 法：按本次奖励增量拆分

永久固定产出可定义 `MODIFIER_SINGLE_CITY_ADJUST_YIELD_CHANGE`，集合为 `COLLECTION_OWNER`，不挂产出位条件，在 GP 中调用 `city:AttachModifierByID(id)`。例如六种产出各定义 1、2、4、8、16，共 30 个定义；奖励 +18 金币只附加金币 16 和金币 2。

```lua
-- modifiers[i] 对应 bits[i]；由已核验的奖励表提供非负整数增量。
local bits = {1, 2, 4, 8, 16}
assert(amount >= 0 and amount <= 31 and amount == math.floor(amount))
for i, bit in ipairs(bits) do
    if math.floor(amount / bit) % 2 == 1 then
        city:AttachModifierByID(modifiers[i])
    end
end
```

1、2、4、8 各用一次覆盖 0～15，加上 16 才覆盖 0～31。这是**单次增量**的可表示范围，不是累计收益上限；多次合法奖励累计可超过 31。位数按实际最大单次奖励选择，超出时扩展或明确拆成多批，不能静默截掉高位。

允许同一 Modifier ID 重复叠加时，不设置阻止叠加的 OwnerStackLimit/SubjectStackLimit；是否持久和叠加还需目标游戏环境验证。永久奖励不要每回合或每次打开界面重放。发奖事件依赖业务记录防重，已发放的记录随存档保留；不要每次加载根据历史总额再 Attach 一遍。增量法不方便撤回，需求若包含减值或清零，优先使用 Property。

### 两种实现之间的迁移

不要把已经整套 Attach 的条件修改器原 ID 直接改成无条件 Amount，否则旧存档可能同时激活全部位。改变实例语义时使用新 ID，明确停用旧控制属性/来源，只迁移目标永久效果一次；人口、免费单位等即时效果不能跟着重放。迁移须在记录新的奖励之前运行，避免把本次奖励同时算进历史补发和正常发奖。

比较所有旧/新奖励的实际数值，检查零值、位边界、同 ID 多次奖励、累计超过单次表示范围、重复事件与重复读档。SQL/模拟检查证明配置和分支，不证明游戏内保存的原生实例已经正确迁移；单独记录实机验收结果。

依据：原版 DynamicModifiers 中两种城市产出类型的集合/效果定义；用户确认的城市地块 Property 与重复 Attach 模式。按场景择用，不宣称某一种普遍更快。后文保留 Property helper 与历史全局模板，采用前核对当前项目的集合和加载环境。

## 核心函数

### 常量定义

```lua
-- 二进制位列表（16 位，最大支持 65535）
local SiqiBinaryList = {1,2,4,8,16,32,64,128,256,512,1024,2048,4096,8192,16384,32768}
local BIT_COUNT = #SiqiBinaryList  -- = 16（也可按需只用前 12 位 = 4095）
```

```sql
-- SQL 端同步的表（用于批量生成 Modifier）
CREATE TABLE Siqi_BinaryList (Num INTEGER PRIMARY KEY);
INSERT INTO Siqi_BinaryList (Num) VALUES
(1),(2),(4),(8),(16),(32),(64),(128),(256),(512),(1024),(2048);
```

### NumToTwo(num, n) — 数字 → 二进制表

低位在前：`t[1]=1, t[2]=2, t[3]=4, ...`。例: `NumToTwo(10,4)` → `{0,1,0,1}`

```lua
function NumToTwo(num, n)
    local t = {}
    for i = n, 1, -1 do  -- 从高位到低位
        if num >= SiqiBinaryList[i] then
            table.insert(t, 1); num = num - SiqiBinaryList[i]
        else
            table.insert(t, 0)
        end
    end
    local tt = {}
    for i = #t, 1, -1 do table.insert(tt, t[i]) end  -- 反转使低位在前
    return tt
end
```

### TwoToNum(t) — 二进制表 → 数字

例: `TwoToNum({0,1,0,1})` → `10`

```lua
function TwoToNum(t)
    local num = 0
    for i = 1, #t do
        if t[i] == 1 then num = num + SiqiBinaryList[i] end
    end
    return num
end
```

### GetPlotTwo / GetPlotNum — 读取地块二进制属性

```lua
-- 返回完整 16 位二进制表（读取 sproperty.."1", sproperty.."2", sproperty.."4", ...）
function GetPlotTwo(plotID, sproperty)
    local plot = Map.GetPlotByIndex(plotID)
    if not plot then return NumToTwo(0, #SiqiBinaryList); end
    local t = {}
    for i = 1, #SiqiBinaryList do
        table.insert(t, plot:GetProperty(sproperty .. SiqiBinaryList[i]) or 0)
    end
    return t
end

-- 快捷读数值接口
function GetPlotNum(plotID, sproperty)
    return TwoToNum(GetPlotTwo(plotID, sproperty))
end
```

### SetPlotTwo — 写入地块二进制属性（核心刷新函数）

**只写变化位**：先读旧值，仅当 `new[i] ~= old[i]` 才 SetProperty。大部分情况无变化，不触发任何写入。

```lua
function SetPlotTwo(plotID, sproperty, t)
    local plot = Map.GetPlotByIndex(plotID)
    if not plot then return; end
    local oldt = GetPlotTwo(plotID, sproperty)
    for i = 1, #t do
        if t[i] ~= oldt[i] then plot:SetProperty(sproperty .. SiqiBinaryList[i], t[i]) end
    end
end
```

### SetPlotNum — 按数值写入

```lua
function SetPlotNum(plotID, sproperty, num, n)
    SetPlotTwo(plotID, sproperty, NumToTwo(num, n))
end
```

### ChangeplotNum — 增量修改（支持正负数分离）

适用于"增加 X 点产出"。自动将正值存入 `sproperty`，负值存入 `NEG .. sproperty`。

```lua
-- NEG: 负数前缀（如 "NEG_"），nil 则不支持负数；n/m: 正/负数区位数
function ChangeplotNum(plotID, sproperty, amount, n, NEG, m)
    local num = GetPlotNum(plotID, sproperty)
    local Negnum = NEG and GetPlotNum(plotID, NEG .. sproperty) or 0
    local oldnum, newnum = num - Negnum, num - Negnum + amount
    if amount == 0 then return; end
    if newnum >= 0 then
        SetPlotNum(plotID, sproperty, newnum, n)
        if NEG then SetPlotNum(plotID, NEG .. sproperty, 0, m) end
    elseif NEG and newnum < 0 then
        SetPlotNum(plotID, sproperty, 0, n)
        SetPlotNum(plotID, NEG .. sproperty, -newnum, m)
    else
        SetPlotNum(plotID, sproperty, 0, n)
    end
end
```

### SetplotNumNew — 覆盖写入（支持正负数分离）

用于每回合刷新：直接将属性**设为精确值**（非增量）。

```lua
function SetplotNumNew(plotID, sproperty, amount, n, NEG, m)
    -- 覆盖目标值为零也必须关闭旧位。
    if NEG and amount < 0 then
        SetPlotNum(plotID, sproperty, 0, n)
        SetPlotNum(plotID, NEG .. sproperty, -amount, m)
    elseif NEG and amount >= 0 then
        SetPlotNum(plotID, sproperty, amount, n)
        SetPlotNum(plotID, NEG .. sproperty, 0, m)
    else
        SetPlotNum(plotID, sproperty, math.max(amount, 0), n)
    end
end
```

### 函数对比

| 函数 | 场景 | 正负数分离 |
|------|------|-----------|
| `SetPlotTwo` | 直接写二进制表（最高效，只写变化位） | 手动 |
| `SetPlotNum` | 按数值写，内部转二进制 | 不支持 |
| `ChangeplotNum` | 增量修改（old + amount） | 支持 |
| `SetplotNumNew` | 覆盖为精确值 | 支持 |

---

## SQL 端：Property 配置表 + 批量 Modifier 生成

### 1. 定义 BinaryList 表

```sql
CREATE TABLE IF NOT EXISTS Siqi_BinaryList (Num INTEGER PRIMARY KEY);
INSERT OR IGNORE INTO Siqi_BinaryList (Num) VALUES
(1),(2),(4),(8),(16),(32),(64),(128),(256),(512),(1024),(2048);
```

### 2. 定义 YieldPropertyKey 映射表

每种产出类型一行，指定 PropertKey 前缀、ModifierType、最大/最小值。

```sql
CREATE TABLE IF NOT EXISTS Siqi_YieldPropertyKey (
    YieldType    TEXT PRIMARY KEY,
    PropertyKey  TEXT NOT NULL,          -- 属性前缀（如 "SIQIMJ_Science"）
    ModifierType TEXT NOT NULL,          -- 如 "MODIFIER_ALL_CITIES_ADJUST_CITY_YIELD_CHANGE"
    ArgName1     TEXT,                   -- 额外 ModifierArgument 参数名（如 "YieldType"）
    ArgValue1    TEXT,                   -- 对应值
    HasNegative  INTEGER NOT NULL DEFAULT 1,  -- 是否生成负数 Modifier
    MaxValue     INTEGER NOT NULL DEFAULT 2048,  -- 正数最大位值（如 2048 = 12 位）
    MinValue     INTEGER NOT NULL DEFAULT 256    -- 负数最大位值（如 256 = 9 位）
);

-- 示例数据
INSERT OR IGNORE INTO Siqi_YieldPropertyKey
(YieldType, PropertyKey, ModifierType, ArgName1, ArgValue1, HasNegative, MaxValue, MinValue) VALUES
('YIELD_FOOD',    'SIQIMJ_Food',    'MODIFIER_ALL_CITIES_ADJUST_CITY_YIELD_CHANGE', 'YieldType', 'YIELD_FOOD',    1, 2048, 256),
('YIELD_SCIENCE', 'SIQIMJ_Science', 'MODIFIER_ALL_CITIES_ADJUST_CITY_YIELD_CHANGE', 'YieldType', 'YIELD_SCIENCE', 1, 2048, 256);
```

### 3. 批量生成 Modifier + Requirement + RequirementSet

核心模式：每种产出 × 每个二进制位 = 一组 Modifier。正数位和负数位各一套。

```sql
-- 命名前缀（自行替换）
-- PREFIX     = 'SIQIMJ'              → ModifierId:  "SIQIMJ_YIELD_FOOD_4"
-- REQSET_PFX = 'REQSET_SIQIMJ'      → ReqSetId:    "REQSET_SIQIMJ_YIELD_FOOD_4"
-- REQ_PFX    = 'REQ_SIQIMJ'          → ReqId:       "REQ_SIQIMJ_YIELD_FOOD_4"
-- NEG_ 前缀用于负数位

-- 1. Modifiers（正数位：WHERE B.Num <= A.MaxValue / 负数位：WHERE HasNegative=1 AND B.Num <= A.MinValue）
INSERT OR IGNORE INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId)
SELECT PREFIX||'_'||A.YieldType||'_'||B.Num, A.ModifierType, REQSET_PFX||'_'||A.YieldType||'_'||B.Num
FROM YieldPropertyKey A, BinaryList B WHERE B.Num <= A.MaxValue
UNION
SELECT PREFIX||'_'||A.YieldType||'_NEG_'||B.Num, A.ModifierType, REQSET_PFX||'_'||A.YieldType||'_NEG_'||B.Num
FROM YieldPropertyKey A, BinaryList B WHERE A.HasNegative = 1 AND B.Num <= A.MinValue;

-- 2. ModifierArguments: Amount = Num（负数位 = -Num）
INSERT OR IGNORE INTO ModifierArguments (ModifierId, Name, Value)
SELECT PREFIX||'_'||A.YieldType||'_'||B.Num, 'Amount', B.Num
FROM YieldPropertyKey A, BinaryList B WHERE B.Num <= A.MaxValue
UNION
SELECT PREFIX||'_'||A.YieldType||'_NEG_'||B.Num, 'Amount', -B.Num
FROM YieldPropertyKey A, BinaryList B WHERE A.HasNegative = 1 AND B.Num <= A.MinValue;

-- 3. ModifierArguments: 额外参数（如 YieldType），仅当 ArgName1 非空
INSERT OR IGNORE INTO ModifierArguments (ModifierId, Name, Value)
SELECT PREFIX||'_'||A.YieldType||'_'||B.Num, A.ArgName1, A.ArgValue1
FROM YieldPropertyKey A, BinaryList B WHERE A.ArgName1 IS NOT NULL AND B.Num <= A.MaxValue
UNION
SELECT PREFIX||'_'||A.YieldType||'_NEG_'||B.Num, A.ArgName1, A.ArgValue1
FROM YieldPropertyKey A, BinaryList B WHERE A.ArgName1 IS NOT NULL AND A.HasNegative = 1 AND B.Num <= A.MinValue;

-- 4. RequirementSets（TEST_ALL：所有条件必须同时满足）
INSERT OR IGNORE INTO RequirementSets (RequirementSetId, RequirementSetType)
SELECT REQSET_PFX||'_'||A.YieldType||'_'||B.Num, 'REQUIREMENTSET_TEST_ALL'
FROM YieldPropertyKey A, BinaryList B WHERE B.Num <= A.MaxValue
UNION
SELECT REQSET_PFX||'_'||A.YieldType||'_NEG_'||B.Num, 'REQUIREMENTSET_TEST_ALL'
FROM YieldPropertyKey A, BinaryList B WHERE A.HasNegative = 1 AND B.Num <= A.MinValue;

-- 5. RequirementSetRequirements（绑定 ReqSet ↔ Req）
INSERT OR IGNORE INTO RequirementSetRequirements (RequirementSetId, RequirementId)
SELECT REQSET_PFX||'_'||A.YieldType||'_'||B.Num, REQ_PFX||'_'||A.YieldType||'_'||B.Num
FROM YieldPropertyKey A, BinaryList B WHERE B.Num <= A.MaxValue
UNION
SELECT REQSET_PFX||'_'||A.YieldType||'_NEG_'||B.Num, REQ_PFX||'_'||A.YieldType||'_NEG_'||B.Num
FROM YieldPropertyKey A, BinaryList B WHERE A.HasNegative = 1 AND B.Num <= A.MinValue;

-- 6. Requirements: REQUIREMENT_PLOT_PROPERTY_MATCHES
INSERT OR IGNORE INTO Requirements (RequirementId, RequirementType)
SELECT REQ_PFX||'_'||A.YieldType||'_'||B.Num, 'REQUIREMENT_PLOT_PROPERTY_MATCHES'
FROM YieldPropertyKey A, BinaryList B WHERE B.Num <= A.MaxValue
UNION
SELECT REQ_PFX||'_'||A.YieldType||'_NEG_'||B.Num, 'REQUIREMENT_PLOT_PROPERTY_MATCHES'
FROM YieldPropertyKey A, BinaryList B WHERE A.HasNegative = 1 AND B.Num <= A.MinValue;

-- 7. RequirementArguments: PropertyName = PropertyKey + Num（正）/ NEG_ + PropertyKey + Num（负）
INSERT OR IGNORE INTO RequirementArguments (RequirementId, Name, Value)
SELECT REQ_PFX||'_'||A.YieldType||'_'||B.Num, 'PropertyName', A.PropertyKey||B.Num
FROM YieldPropertyKey A, BinaryList B WHERE B.Num <= A.MaxValue
UNION
SELECT REQ_PFX||'_'||A.YieldType||'_NEG_'||B.Num, 'PropertyName', 'NEG_'||A.PropertyKey||B.Num
FROM YieldPropertyKey A, BinaryList B WHERE A.HasNegative = 1 AND B.Num <= A.MinValue;

-- 8. RequirementArguments: PropertyMinimum = 1（属性值 ≥ 1 即触发）
INSERT OR IGNORE INTO RequirementArguments (RequirementId, Name, Value)
SELECT REQ_PFX||'_'||A.YieldType||'_'||B.Num, 'PropertyMinimum', 1
FROM YieldPropertyKey A, BinaryList B WHERE B.Num <= A.MaxValue
UNION
SELECT REQ_PFX||'_'||A.YieldType||'_NEG_'||B.Num, 'PropertyMinimum', 1
FROM YieldPropertyKey A, BinaryList B WHERE A.HasNegative = 1 AND B.Num <= A.MinValue;

-- 9. 注册到 GameModifiers（全局生效，无需绑定 Trait）
INSERT OR IGNORE INTO GameModifiers (ModifierId)
SELECT PREFIX||'_'||A.YieldType||'_'||B.Num
FROM YieldPropertyKey A, BinaryList B WHERE B.Num <= A.MaxValue
UNION
SELECT PREFIX||'_'||A.YieldType||'_NEG_'||B.Num
FROM YieldPropertyKey A, BinaryList B WHERE A.HasNegative = 1 AND B.Num <= A.MinValue;
```

> **注意**：上述 SQL 使用变量名作为表名（`YieldPropertyKey`、`BinaryList`）和前缀（`PREFIX`），实际使用时需替换为你的表名和前缀。

### 生成的命名规范总结

| 组件 | 命名格式 | 示例 |
|------|---------|------|
| ModifierId | `PREFIX_YieldType_Num` | `SIQIMJ_YIELD_FOOD_4` |
| 负数 Modifier | `PREFIX_YieldType_NEG_Num` | `SIQIMJ_YIELD_FOOD_NEG_4` |
| RequirementSetId | `REQSET_PREFIX_YieldType_Num` | `REQSET_SIQIMJ_YIELD_FOOD_4` |
| RequirementId | `REQ_PREFIX_YieldType_Num` | `REQ_SIQIMJ_YIELD_FOOD_4` |
| PropertyName（正） | `PropertyKey + Num` | `SIQIMJ_Food4` |
| PropertyName（负） | `NEG_ + PropertyKey + Num` | `NEG_SIQIMJ_Food4` |

---

## 应用模板

### 模版一：产出加成（每回合刷新，地块属性 → Modifier）

核心流程：UI 端计算 → EXECUTE_SCRIPT 传给 GP → GP 端 NumToTwo → SetPlotTwo 写入。

```lua
-- UI 端：每回合采集城市数据，计算产出值
function MyMod.UI.RefreshYields(playerID)
    local pPlayer = Players[playerID]
    local yields = {}
    for _, pCity in pPlayer:GetCities():Members() do
        local amount = pCity:GetPopulation()  -- 例：1人口 → 1产出
        local pPlot = Map.GetPlot(pCity:GetX(), pCity:GetY())
        if pPlot then
            table.insert(yields, {
                plotID = pPlot:GetIndex(),
                propKey = "MYMOD_Science",
                amount = amount
            })
        end
    end
    if #yields > 0 then
        UI.RequestPlayerOperation(playerID, PlayerOperations.EXECUTE_SCRIPT,
            { OnStart = 'MyMod_ApplyYields', Yields = yields })
    end
end

-- GP 端：收数据，写 Property
function MyMod.GP.ApplyYields(playerID, params)
    if not params or not params.Yields then return end
    for _, e in ipairs(params.Yields) do
        SiqiGP.SetPlotTwo(e.plotID, e.propKey, SiqiGP.NumToTwo(e.amount, 12))
    end
end
```

SQL 端：创建 BinaryList + YieldPropertyKey 表，然后按上文"批量生成"模板执行。

```sql
INSERT OR IGNORE INTO MyMod_YieldPropertyKey
(YieldType, PropertyKey, ModifierType, ArgName1, ArgValue1, HasNegative, MaxValue) VALUES
('YIELD_SCIENCE', 'MYMOD_Science', 'MODIFIER_ALL_CITIES_ADJUST_CITY_YIELD_CHANGE',
 'YieldType', 'YIELD_SCIENCE', 0, 2048);
```

### 模版二：宜居度转产出（支持正负数）

宜居度可正可负，用 `SetplotNumNew` 分离存储。

```lua
-- UI 端
function MyMod.RefreshAmenityYield(playerID)
    for _, pCity in Players[playerID]:GetCities():Members() do
        local g = pCity:GetGrowth()
        local amenity = g:GetAmenities() - g:GetAmenitiesNeeded()
        do -- 零宜居差额也提交，用于清除旧加成。
            local p = Map.GetPlot(pCity:GetX(), pCity:GetY())
            UI.RequestPlayerOperation(playerID, PlayerOperations.EXECUTE_SCRIPT, {
                OnStart = 'MyMod_ApplyAmenity', plotID = p:GetIndex(),
                propKey = 'MYMOD_Amenity_Science', amount = amenity,
                maxBits = 12, minBits = 8
            })
        end
    end
end

-- GP 端
function MyMod.GP.ApplyAmenity(playerID, p)
    SiqiGP.SetplotNumNew(p.plotID, p.propKey, p.amount, p.maxBits, 'NEG_', p.minBits)
end
```

SQL: `HasNegative = 1`，正数最大 2048(12位)，负数最大 256(8位)。

```sql
INSERT OR IGNORE INTO MyMod_YieldPropertyKey
(YieldType, PropertyKey, ModifierType, ArgName1, ArgValue1, HasNegative, MaxValue, MinValue) VALUES
('YIELD_SCIENCE', 'MYMOD_Amenity_Science', 'MODIFIER_ALL_CITIES_ADJUST_CITY_YIELD_CHANGE',
 'YieldType', 'YIELD_SCIENCE', 1, 2048, 256);
```

### 模版三：击杀数转战斗力 / 城市属性转加成（永久叠加）

永久值用 `Permanent_` 前缀 Property 存储累计量，刷新时用 `PermanentAmount + 当回合增量` 作为目标值。

```lua
-- 单位击杀事件（GP 端直接写，无需 UI）
function MyMod.OnUnitKilled(ownerPlayerID, unitID)
    local pCapital = Players[ownerPlayerID]:GetCities():GetCapitalCity()
    if not pCapital then return end
    local plotID = Map.GetPlot(pCapital:GetX(), pCapital:GetY()):GetIndex()
    SiqiGP.ChangeplotNum(plotID, 'MYMOD_CombatBonus', 1, 12, nil, nil)
    -- ↑ NEG=nil 表示只增不减
end
```

### 模版四：Player Property 二进制（非地块）

同原理可用于 Player Property，SQL 端用 `REQUIREMENT_PLAYER_PROPERTY_MATCHES` + `COLLECTION_OWNER`。

```lua
function GetPlayerTwo(playerID, sproperty)
    local p = Players[playerID]
    if not p then return NumToTwo(0, BIT_COUNT) end
    local t = {}
    for i = 1, BIT_COUNT do
        table.insert(t, p:GetProperty(sproperty .. SiqiBinaryList[i]) or 0)
    end
    return t
end

function SetPlayerTwo(playerID, sproperty, t)
    local p = Players[playerID]
    if not p then return end
    local oldt = GetPlayerTwo(playerID, sproperty)
    for i = 1, #t do
        if t[i] ~= oldt[i] then p:SetProperty(sproperty .. SiqiBinaryList[i], t[i]) end
    end
end
```

---

## 完整工作流

1. **SQL 准备（一次性）**：创建 BinaryList + YieldPropertyKey 表，批量生成 Modifier/Requirement，注册到 GameModifiers
2. **Lua 初始化**：加载 Support.lua（提供 NumToTwo/SetPlotTwo 等），注册事件监听（如 PlayerTurnActivated）
3. **运行时刷新**：UI 端计算产出值 → EXECUTE_SCRIPT 传 `{plotID, propKey, amount}` → GP 端 `NumToTwo` → `SetPlotTwo` 写入
4. **自动生效**：`REQUIREMENT_PLOT_PROPERTY_MATCHES` 检测 PropertyNameX == 1 → 触发 Amount=X 的 Modifier

---

## 注意事项

1. **Lua + SQL 两端的 BinaryList 位数必须一致**，否则位序错乱
2. **SetPlotTwo 只写变化位**是性能关键，不要在循环里全量 SetProperty
3. **位数计算**：`math.floor(math.log(MaxValue, 2)) + 1`（MaxValue=2048 → 12位，MinValue=256 → 9位）
4. **属性命名**：正位 = `PropertyKey + Num`，负位 = `NEG_ + PropertyKey + Num`，两端命名必须一致
5. **GP vs UI**：`SetProperty` 仅 GP 端可用；UI 计算后须通过 `UI.RequestPlayerOperation(..., EXECUTE_SCRIPT, data)` 发送
6. **永久值**：先按前述场景选择方案。Property 累计值仅在新奖励发生时增加，刷新只覆盖当前总值；直接 Attach 则按业务记录只发本次增量，不能把同一回合增量重复计入。
