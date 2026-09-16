# 虚拟建筑临时效果系统 (Virtual Building Effects)

## 来源
- Celebrations (Nwflower, id=3492136529) — 庆典效果通过虚拟建筑实现

## 概述
利用 `InternalOnly=1` + `MustPurchase=1` 的虚拟建筑作为"效果容器"，通过 Lua 动态添加/移除建筑来临时应用或取消一组 Modifier 效果。

## XML 配合

本系统为纯 SQL + Lua 效果管理机制（`InternalOnly=1` 虚拟建筑），无独立 UI 面板。虚拟建筑的 UI 可见性通过 `InternalOnly=1` 控制（不在科技树/市政树中显示），其效果通过 `BuildingModifiers` 表自动注入，无需额外 XML 控件。庆典选择/切换 UI 配合 `CelebrationsTracker.xml` 和 `Celebration_Panel.xml`（见 `lua-workshop-misc-resource-accumulation.md`）。

---

## 为什么用虚拟建筑

在 Civ 6 中，Modifier 可以通过多种方式挂载：

| 方式 | 优点 | 缺点 |
|------|------|------|
| `Player:AttachModifierByID` | 简单直接，Permanent 修饰符随存档持久化，可靠 | 临时效果需 Lua 手动移除；绑定玩家级对象 |
| Unit Ability | 跟随单位 | 只作用于单位 |
| Virtual Building | 可组合多个 Modifier，随城市保存 | 需要城市载体，不适合纯玩家级永久效果 |

**虚拟建筑是"临时、可组合、可移除的效果包"的最佳方案。**

## 步骤 1：定义虚拟建筑 (SQL)

```sql
-- 建筑类型
INSERT INTO Types (Type, Kind)
VALUES ('BUILDING_YOUR_EFFECT', 'KIND_BUILDING');

-- 建筑定义（关键字段：InternalOnly, MustPurchase）
INSERT INTO Buildings (BuildingType, Name, Cost, InternalOnly, MustPurchase)
VALUES ('BUILDING_YOUR_EFFECT', 'LOC_YOUR_EFFECT_NAME', 1, 1, 1);

-- 关联 Modifier
INSERT INTO BuildingModifiers (BuildingType, ModifierId)
VALUES ('BUILDING_YOUR_EFFECT', 'MODIFIER_YOUR_EFFECT_1'),
       ('BUILDING_YOUR_EFFECT', 'MODIFIER_YOUR_EFFECT_2');

-- Modifier 定义
INSERT INTO Modifiers (ModifierId, ModifierType)
VALUES ('MODIFIER_YOUR_EFFECT_1', 'MODIFIER_PLAYER_CITIES_ADJUST_CITY_YIELD_MODIFIER_GRANCOLOMBIA_MAYA'),
       ('MODIFIER_YOUR_EFFECT_2', 'MODIFIER_PLAYER_ADJUST_GREAT_PERSON_POINTS');

INSERT INTO ModifierArguments (ModifierId, Name, Value)
VALUES ('MODIFIER_YOUR_EFFECT_1', 'Amount', '25'),
       ('MODIFIER_YOUR_EFFECT_1', 'YieldType', 'YIELD_FOOD'),
       ('MODIFIER_YOUR_EFFECT_2', 'Amount', '5'),
       ('MODIFIER_YOUR_EFFECT_2', 'GreatPersonClassType', 'GREAT_PERSON_CLASS_PROPHET');
```

关键字段说明：
- `Cost=1` — 名义成本（实际免费）
- `InternalOnly=1` — 不在科技树/市政树中显示
- `MustPurchase=1` — 不能用生产力建造，只能用 Lua 添加

## 步骤 2：动态添加虚拟建筑 (Lua)

```lua
function ApplyVirtualBuilding(playerID, buildingType)
    local pPlayer = Players[playerID]
    local pCapital = pPlayer:GetCities():GetCapitalCity()
    if not pCapital then return end

    local iBuilding = GameInfo.Buildings[buildingType].Index

    -- 防止重复添加
    if pCapital:GetBuildings():HasBuilding(iBuilding) then
        print('Building already exists')
        return
    end

    -- 核心 API：在首都创建建筑
    pCapital:GetBuildQueue():CreateBuilding(iBuilding)
end
```

**注意**：`GetBuildQueue():CreateBuilding()` 是立即创建，不需要等待回合。

## 步骤 3：移除虚拟建筑

```lua
function RemoveVirtualBuilding(playerID, buildingType)
    local pPlayer = Players[playerID]
    local pCapital = pPlayer:GetCities():GetCapitalCity()
    if not pCapital then return end

    local iBuilding = GameInfo.Buildings[buildingType].Index

    if pCapital:GetBuildings():HasBuilding(iBuilding) then
        pCapital:GetBuildings():RemoveBuilding(iBuilding)
    end
end
```

## 步骤 4：效果切换（多选一模式）

庆典系统允许同时只有一种庆典效果激活，切换时先清除旧的再添加新的：

```lua
function SwitchVirtualBuilding(playerID, newCelebrationType)
    local pPlayer = Players[playerID]
    local pCapital = pPlayer:GetCities():GetCapitalCity()

    -- 遍历所有可能的虚拟建筑
    for row in GameInfo.YourEffectMapping() do
        local iBuilding = GameInfo.Buildings[row.BuildingType].Index
        if row.EffectType ~= newCelebrationType
           and pCapital:GetBuildings():HasBuilding(iBuilding) then
            -- 移除旧的（不是当前选中的）
            pCapital:GetBuildings():RemoveBuilding(iBuilding)
        end
    end

    -- 添加新的
    local newBuildingType = GameInfo.YourEffectMapping[newCelebrationType].BuildingType
    local iNewBuilding = GameInfo.Buildings[newBuildingType].Index
    if not pCapital:GetBuildings():HasBuilding(iNewBuilding) then
        pCapital:GetBuildQueue():CreateBuilding(iNewBuilding)
    end
end
```

## 步骤 5：效果到期自动清除

```lua
local EFFECT_DURATION = 10  -- 持续回合数（随游戏速度缩放）

function CheckEffectExpiry(playerID)
    local pPlayer = Players[playerID]
    local lastTriggerTurn = pPlayer:GetProperty(KEY_LAST_TRIGGER_TURN) or 0
    local currentTurn = Game.GetCurrentGameTurn()

    if currentTurn > lastTriggerTurn + EFFECT_DURATION then
        -- 效果到期，清除虚拟建筑
        ClearAllVirtualBuildings(playerID)
    end
end
Events.PlayerTurnActivated.Add(function(playerID)
    CheckEffectExpiry(playerID)
end)
```

## 步骤 6：关联表设计 (SQL)

用映射表将效果类型与虚拟建筑关联：

```sql
CREATE TABLE IF NOT EXISTS NWflower_CelebrationModifiers (
    CelebrationsTypes TEXT NOT NULL,  -- 庆典类型（逻辑标识）
    BuildingType      TEXT DEFAULT NULL,  -- 对应的虚拟建筑
    PRIMARY KEY ('CelebrationsTypes'),
    FOREIGN KEY (BuildingType) REFERENCES Buildings(BuildingType)
);

-- 自动填充：BUILDING_ + 庆典类型
INSERT OR REPLACE INTO NWflower_CelebrationModifiers (CelebrationsTypes, BuildingType)
SELECT CelebrationsTypes, 'BUILDING_' || CelebrationsTypes
FROM NWflower_Celebrations;
```

## 步骤 7：DynamicModifier 自定义效果

当标准 ModifierType 不够用时，创建自定义 DynamicModifier：

```sql
-- 注册自定义 ModifierType
INSERT INTO Types (Type, Kind)
VALUES ('NW_CL_MODIFIER_SINGLE_CITY_GRANT_UNIT_BY_CLASS', 'KIND_MODIFIER');

-- 绑定 CollectionType 和 EffectType
INSERT INTO DynamicModifiers (ModifierType, CollectionType, EffectType)
VALUES ('NW_CL_MODIFIER_SINGLE_CITY_GRANT_UNIT_BY_CLASS',
        'COLLECTION_OWNER',           -- 作用集合：拥有者
        'EFFECT_GRANT_UNIT_BY_CLASS'); -- 效果类型：按兵种赠送单位

-- 使用（作为 BuildingModifier）
INSERT INTO BuildingModifiers (BuildingType, ModifierId)
VALUES ('BUILDING_MOBILIZATION', 'MODFIER_MOBILIZATION_SIEGE');

INSERT INTO Modifiers (ModifierId, ModifierType, Permanent)
VALUES ('MODFIER_MOBILIZATION_SIEGE',
        'NW_CL_MODIFIER_SINGLE_CITY_GRANT_UNIT_BY_CLASS', 1);

INSERT INTO ModifierArguments (ModifierId, Name, Value)
VALUES ('MODFIER_MOBILIZATION_SIEGE', 'UnitPromotionClassType',
        'PROMOTION_CLASS_SIEGE');
```

## 要点总结

1. `InternalOnly=1, MustPurchase=1` 是虚拟建筑的三要素
2. `GetBuildQueue():CreateBuilding()` 立即添加，`RemoveBuilding()` 移除
3. 虚拟建筑存档安全（跟随城市保存）
4. 一个虚拟建筑可以挂多个 `BuildingModifiers`，实现效果打包
5. 切换效果时先清后加，避免残留
6. 用关联表（映射表）管理效果类型与建筑的关系
7. 复杂效果可用 `DynamicModifiers` 自定义 ModifierType
