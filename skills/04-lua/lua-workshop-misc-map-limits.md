# 地图规模扩展 (Map Size Limits Extension)

## 来源
- More Players (Arstahd, id=2118297372) — 增加每张地图的玩家/城邦/宗教上限

## 概述
通过少量 SQL 和 Lua 文件替换，突破游戏地图的玩家数、城邦数、宗教数限制。适合制作"超大图"或"更多对手"类 Mod。

## 步骤 1：SQL 增加游戏数据上限

### MapSizes（地图规模表）
```sql
-- Config Data: 增加玩家和城邦上限
-- 原值：每个地图尺寸 +4 玩家, +2 城邦
UPDATE MapSizes SET MaxPlayers = MaxPlayers + 4, MaxCityStates = MaxCityStates + 2;
```

`MapSizes` 表结构（关键字段）：
- `MapSizeType` — 地图尺寸类型
- `MaxPlayers` — 最大玩家数（默认：
  - Duel: 4, Tiny: 6, Small: 10, Standard: 16, Large: 20, Huge: 24）
- `MaxCityStates` — 最大城邦数

### Map_GreatPersonClasses（伟人与地图大小关联）
```sql
-- Gameplay Data: 增加大预言家数量
-- 原值：每个地图尺寸 +1 大预言家
UPDATE Map_GreatPersonClasses SET MaxWorldInstances = MaxWorldInstances + 1;
```

注意区分加载位置：
- Config Data (FrontEndActions) — 影响游戏设置界面
- Gameplay Data (InGameActions) — 影响游戏内的逻辑

## 步骤 2：Lua 替换 StagingRoom（多人房间）

当需要突破多人游戏大厅的硬编码限制时，需要替换整个 `stagingroom.lua`。

### 关键常量修改
```lua
-- 原版值：12
local MAX_EVER_PLAYERS : number = 48;  -- 绝对上限
local MAX_SUPPORTED_PLAYERS : number = 48;  -- 推荐上限
local g_currentMaxPlayers : number = MAX_EVER_PLAYERS;
```

### 动态获取地图最大玩家数
```lua
function BuildPlayerList()
    -- 从 MapConfiguration 获取当前地图的最大玩家数
    g_currentMaxPlayers = math.min(MapConfiguration.GetMaxMajorPlayers(), 48);
    -- ...
end
```

### 热座模式 UI 适配
```lua
-- 热座模式增加玩家列表高度
if GameConfiguration.IsHotseat() then
    Controls.PrimaryStackGrid:SetSizeY(
        window - Controls.ChatContainer:GetSizeY() + 221
    )
end
```

## 步骤 3：modinfo 配置

```xml
<Mod id="YOUR-MOD-GUID">
    <FrontEndActions>
        <!-- Config Data：影响游戏设置界面 -->
        <UpdateDatabase id="MOD_CONFIG_DATA">
            <File>Mod Config Data.sql</File>
        </UpdateDatabase>
        <!-- StagingRoom 替换 -->
        <ImportFiles id="MOD_LUA">
            <File>stagingroom.lua</File>
        </ImportFiles>
    </FrontEndActions>

    <InGameActions>
        <!-- Gameplay Data：影响游戏内逻辑 -->
        <UpdateDatabase id="MOD_GAMEPLAY_DATA">
            <File>Mod Gameplay Data.sql</File>
        </UpdateDatabase>
    </InGameActions>
</Mod>
```

**重要**：StagingRoom 替换必须用 `FrontEndActions > ImportFiles`，因为在进入游戏前就加载。

## 步骤 4：StagingRoom 替换的注意事项

替换完整 stagingroom.lua 是高风险的，因为：
- 游戏更新可能改变原版 stagingroom.lua
- 与其他修改 stagingroom 的 Mod 冲突
- 需要复制整个文件（1300+ 行）并只修改少数关键值

### 最小侵入式修改（推荐）

不要全部替换，只修改关键值：

```lua
-- 在原版 stagingroom.lua 的基础上，找到并修改：
local MAX_EVER_PLAYERS : number = 12;  -- 改为 48
local MAX_SUPPORTED_PLAYERS : number = 12;  -- 改为 48

-- 找到 BuildPlayerList 函数，修改：
g_currentMaxPlayers = math.min(MapConfiguration.GetMaxMajorPlayers(), 12);
-- 改为：
g_currentMaxPlayers = math.min(MapConfiguration.GetMaxMajorPlayers(), 48);
```

### 版本标记

在文件头部注释标记修改位置：
```lua
----------------------------------------------------------------
-- Staging Room Screen -- ARSTAHD EDITED -- More Players v2.4
----------------------------------------------------------------
```

这样在游戏更新后可以快速定位并重新应用修改。

## 步骤 5：相关表结构参考

### 关键表关系
```
MapSizes
  └─ MaxPlayers, MaxCityStates, DefaultPlayers

Map_GreatPersonClasses
  └─ MapSizeType, GreatPersonClassType, MaxWorldInstances
     关联 MapSizes 和 GreatPersonClasses

Parameters (游戏设置参数)
  └─ MAX_PLAYERS, MAX_CITY_STATES (界面滑块范围)
```

### 可能需要扩展的其他限制
```sql
-- 宗教数量限制（如果存在）
-- 某些 Mod 可能需要增加宗教数量

-- 伟人世界实例数
UPDATE GreatPersonIndividuals SET MaxWorldInstances = MaxWorldInstances + N;

-- 如果游戏有硬编码的查询限制（如最多 63 个玩家），
-- 则需要在 Lua 层面处理边界情况
```

## 要点总结

1. **SQL 改数据**：`MapSizes.MaxPlayers` / `MaxCityStates` 是游戏数据层面的限制
2. **Lua 改 UI**：`stagingroom.lua` 的 `MAX_EVER_PLAYERS` 是 UI 层面的硬编码限制
3. **数据与 UI 必须同步**：只改 SQL 不改 Lua，UI 不会显示额外槽位
4. **Config vs Gameplay**：MapSizes 是 Config 数据（设置界面），Map_GreatPersonClasses 是 Gameplay 数据（游戏内）
5. **风险提示**：替换 stagingroom.lua 容易因游戏更新失效，需要维护
6. **实际限制**：理论上最多 63 个槽位（ID 系统限制），实际上 48 个是目前测试过的极限
