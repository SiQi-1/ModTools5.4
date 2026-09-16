# 二进制折叠产出入体系 (Binary Yield Property System)

> 来源：ChaoGong System (3475587881) + Modular Adjacency Bonus (3429735059)
> 核心模块，可独立复用

## 概述

将任意整数通过二进制分解为 N 个 0/1 旗标（Plot Property），再用 `REQUIREMENT_PLOT_PROPERTY_MATCHES` 叠加不同强度的 Modifier。适合需要在城市/区域地块上根据动态数值施加多档加成的需求。

## XML 配合

本系统为纯数值转换机制（整数 -> 二进制 Property -> SQL Requirement 触发），无独立 UI 面板。二进制位值列表通过 SQL 表 `Ruivo_BinaryList` 或 `APCG_BINARY_VASSAL_GOLD` 系列存储，Property 自动写入地块，效果通过标准 `REQUIREMENT_PLOT_PROPERTY_MATCHES` + `MODIFIER_*` 链生效。

---

## 核心原理

```
输入数值 → 二进制分解 → N个Property（每个0或1）
                            ↓
                SQL: REQUIREMENT_PLOT_PROPERTY_MATCHES
                            ↓
                    不同档位的 Modifier 生效
```

- 二进制位值表：1, 2, 4, 8, 16, 32, 64, 128, 256, 512（最大1023）
- 每个位值对应一个 Modifier，Amount = 位值本身
- 例如输入 13 → 分解为 8+4+1 → PRO_3=1, PRO_2=1, PRO_0=1，分别触发 Amount=8,4,1 的Modifier
- 总和 = 13，与输入一致

## SQL 端

### 1. 定义二进制位值表（参考 MAB）

```sql
CREATE TABLE Ruivo_BinaryList (
    Num INTEGER PRIMARY KEY
);
INSERT INTO Ruivo_BinaryList (Num)
VALUES (1), (2), (4), (8), (16), (32), (64), (128), (256), (512);
```

### 2. 定义 Modifier + REQ（以朝贡贸易路线为例）

```sql
-- 需求集
INSERT INTO RequirementSets (RequirementSetId, RequirementSetType) VALUES
('APCG_PRO_TR_1', 'REQUIREMENTSET_TEST_ALL');

INSERT INTO RequirementSetRequirements (RequirementSetId, RequirementId) VALUES
('APCG_PRO_TR_1', 'REQUIRES_CITY_HAS_PALACE'),
('APCG_PRO_TR_1', 'REQ_APCG_PRO_TR_1');

-- 需求：读取地块属性
INSERT INTO Requirements (RequirementId, RequirementType) VALUES
('REQ_APCG_PRO_TR_1', 'REQUIREMENT_PLOT_PROPERTY_MATCHES');

INSERT INTO RequirementArguments (RequirementId, Name, Value) VALUES
('REQ_APCG_PRO_TR_1', 'PropertyName', 'PRO_TRFG_1'),
('REQ_APCG_PRO_TR_1', 'PropertyMinimum', '1');

-- Modifier
INSERT INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId) VALUES
('MODIFIER_APCG_TRADE_ROUTE_1', 'MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_CAPACITY', 'APCG_PRO_TR_1');

INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
('MODIFIER_APCG_TRADE_ROUTE_1', 'Amount', '1');
```

### 3. 关键规律

- 位值 2^n 对应的 Modifier 中 Amount 也是 2^n
- 需求级别从 1 到 N（对应二进制位数）
- 可以挂在 `DistrictModifiers`（首都）或 `TraitModifiers` 上

## Lua 端

### 核心函数：二进制折叠写入

```lua
-- 二进制位值列表（从SQL表读取缓存）
Ruivo_BinaryList = {}  -- {1, 2, 4, 8, 16, 32, 64, 128, 256, 512}

-- 将实数值 iBonus 分解写入地块属性
function Ruivo_Zip_SetProperty(ID, iBonus, YieldChange, iX, iY)
    local pPlot = Map.GetPlot(iX, iY)

    -- 防重复写入
    local TotalKey = ID .. '_TOTAL'
    local current = pPlot:GetProperty(TotalKey) or 0
    if current == iBonus then return end

    pPlot:SetProperty(TotalKey, iBonus)

    -- 计算实际总量
    local ActualAmount = iBonus * YieldChange
    ActualAmount = math.floor(ActualAmount)
    pPlot:SetProperty(ID .. '_ACTUAL_AMOUNT', ActualAmount)

    -- 二进制分解
    local resultList = {}
    for _ = 1, #Ruivo_BinaryList do table.insert(resultList, 0) end

    for i = #Ruivo_BinaryList, 1, -1 do
        if ActualAmount >= Ruivo_BinaryList[i] then
            resultList[i] = 1
            ActualAmount = ActualAmount - Ruivo_BinaryList[i]
        end
    end

    -- 写入位值属性
    for i = 1, #Ruivo_BinaryList do
        local PropertyKey = ID .. '_' .. Ruivo_BinaryList[i]
        pPlot:SetProperty(PropertyKey, resultList[i])
    end
end
```

### 朝贡朝贡金示例（另一种写法）

```lua
function APCG_BINARY_VASSAL_GOLD(VASSAL_GOLD, iX, iY)
    -- 对 VASSAL_GOLD 的每个位进行计算
    local PRO_VASSAL_GOLD_1 = (math.floor(VASSAL_GOLD / 1)) % 2
    local PRO_VASSAL_GOLD_2 = (math.floor(VASSAL_GOLD / 2)) % 2
    -- ... 直到 PRO_VASSAL_GOLD_15 = (math.floor(VASSAL_GOLD / 16384)) % 2

    local pPlot = Map.GetPlot(iX, iY)
    pPlot:SetProperty("PRO_VASSAL_GOLD_1", PRO_VASSAL_GOLD_1)
    -- ... 写入所有位
end
```

## 触发刷新时机

- `Events.PlayerTurnActivated` — 每回合刷新
- `Events.DistrictBuildProgressChanged` — 区域建成时刷新（注意此事件触发2次，需开关法）
- `Events.CapitalCityChanged` — 首都变化时刷新

## 关键 REQ

- `REQUIREMENT_PLOT_PROPERTY_MATCHES`：检测地块上的 Property，支持 PropertyName + PropertyMinimum
- `REQUIRES_CITY_HAS_PALACE`：限制只对首都生效

## 使用场景

1. **贸易路线容量**：根据朝贡礼物的累计值，动态增加贸易路线数量
2. **朝贡金收入**：将附庸国金收入总和分解为地块属性，触发首都金币加成
3. **模块化相邻加成**：将相邻对象数量分解为位值，触发区域的产出加成

## 注意事项

1. **防重复写入**：用 `_TOTAL` 键对比当前值，相同时跳过，避免每回合反复 SetProperty
2. **二进制位数的实际上限**：10 位二进制最大表示 1023，但朝贡系统用了 15 位（最大 32767）
3. **零值处理**：当数值归零时记得更新属性（朝贡系统在 VASSAL_GOLD 为 0 时也调用写入）
4. **YieldChange 系数**：如果每个相邻对象提供非1的加成量，需要在二进制分解前乘以 YieldChange

## 相关 ModifierType

| ModifierType | 说明 |
|---|---|
| `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_CAPACITY` | 贸易路线容量 |
| `MODIFIER_PLAYER_DISTRICT_ADJUST_BASE_YIELD_CHANGE` | 区域基础产出(可堆叠) |
| `MODIFIER_PLAYER_ADJUST_YIELD_CHANGE` | 玩家全局产出变化 |
