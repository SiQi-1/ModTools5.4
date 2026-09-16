# 自定义 SQL 表驱动游戏逻辑

## 来源
- Choosable Goody Huts (Konomi, id=3014867813) — 自定义村庄奖励选择表 `GoodyHutSubTypes_Choose`
- Celebrations (Nwflower, id=3492136529) — 自定义庆典类型表 `NWflower_Celebrations` 和映射表 `NWflower_CelebrationModifiers`

## 概述
通过创建自定义 SQL 表，将游戏逻辑数据从 Lua 代码中分离出来，实现"数据驱动"的设计模式。自定义表可以在 GameInfo 中通过 `GameInfo.TableName()` 迭代器访问。

## 步骤 1：创建自定义表 (SQL)

```sql
CREATE TABLE "GoodyHutSubTypes_Choose" (
    "GoodyHut" TEXT NOT NULL,
    "SubTypeGoodyHut" TEXT NOT NULL UNIQUE,
    "Description" TEXT,
    "Weight" INTEGER NOT NULL DEFAULT 0,
    "ModifierID" TEXT NOT NULL,
    "UpgradeUnit" BOOLEAN NOT NULL CHECK (UpgradeUnit IN (0,1)) DEFAULT 0,
    "Turn" INTEGER NOT NULL DEFAULT 0,
    "Experience" BOOLEAN NOT NULL CHECK (Experience IN (0,1)) DEFAULT 0,
    "Heal" INTEGER NOT NULL DEFAULT 0,
    "Relic" BOOLEAN NOT NULL CHECK (Relic IN (0,1)) DEFAULT 0,
    "Trader" BOOLEAN NOT NULL CHECK (Trader IN (0,1)) DEFAULT 0,
    "MinOneCity" BOOLEAN NOT NULL CHECK (MinOneCity IN (0,1)) DEFAULT 0,
    "RequiresUnit" BOOLEAN NOT NULL CHECK (RequiresUnit IN (0,1)) DEFAULT 0,
    PRIMARY KEY(SubTypeGoodyHut),
    FOREIGN KEY (GoodyHut) REFERENCES GoodyHuts(GoodyHutType)
        ON DELETE CASCADE ON UPDATE CASCADE
);
```

**表设计要点**：
- 布尔字段用 `CHECK (IN (0,1))` 约束
- 外键关联游戏核心表以保持数据完整性
- 给每个字段合理的默认值
- PRIMARY KEY 用业务标识字段（而非自增 ID）

## 步骤 2：从游戏核心表导入数据

```sql
-- 从 GoodyHutSubTypes 复制数据到新表
INSERT INTO GoodyHutSubTypes_Choose
SELECT * FROM GoodyHutSubTypes
WHERE GoodyHut NOT IN ('METEOR_GOODIES', 'SAILOR_WONDROUS', 'DUMMY_BUILDING')
  AND Weight > 0;

-- 同时把原表的 AI 数据做好（避免修改原表影响其他 Mod）
UPDATE GoodyHutSubTypes
SET Description = NULL
WHERE GoodyHut NOT IN ('METEOR_GOODIES', 'SAILOR_WONDROUS', 'DUMMY_BUILDING')
  AND Weight > 0;
```

## 步骤 3：AI/人类分支处理

Choosable Goody Huts 的巧妙设计：为 AI 复制一份 Modifier：

```sql
-- 复制 Modifier（加 _AI 后缀）
INSERT INTO Modifiers (ModifierId, ModifierType, RunOnce, Permanent, SubjectRequirementSetId)
SELECT ModifierID || '_AI', ModifierType, RunOnce, Permanent, 'PLAYER_IS_AI'
FROM Modifiers
WHERE EXISTS (
    SELECT ModifierId FROM GoodyHutSubTypes
    WHERE Modifiers.ModifierId = GoodyHutSubTypes.ModifierId
      AND GoodyHutSubTypes.GoodyHut NOT IN ('METEOR_GOODIES', 'SAILOR_WONDROUS', 'DUMMY_BUILDING')
      AND GoodyHutSubTypes.Weight > 0
);

-- 复制 ModifierArguments
INSERT INTO ModifierArguments (ModifierId, Name, Type, Value)
SELECT ModifierID || '_AI', Name, Type, Value
FROM ModifierArguments
WHERE ... (相同条件);

-- 更新原表的 ModifierID 指向 AI 版本
UPDATE GoodyHutSubTypes
SET ModifierID = ModifierID || '_AI'
WHERE ... (相同条件);
```

**关键思路**：原版 Modifier 保留给玩家的自定义表使用；AI 使用带 `_AI` 后缀和 `PLAYER_IS_AI` SubjectRequirementSet 的版本，保持随机行为。

## 步骤 4：Lua 访问自定义表

```lua
-- 遍历自定义表（和遍历任何 GameInfo 表一样）
for row in GameInfo.GoodyHutSubTypes_Choose() do
    local name = Locale.Lookup('LOC_KNM_CHOOSE_' .. row.SubTypeGoodyHut)
    local choosable = true

    -- 读取自定义字段
    if row.MinOneCity and not isMinOneCity then
        choosable = false
    end
    if row.RequiresUnit and not hasUnit then
        choosable = false
    end
    if row.Turn > 0 and Game:GetCurrentGameTurn() < row.Turn then
        choosable = false
    end

    table.insert(targets, {
        SubType = row.SubTypeGoodyHut,
        Name = name,
        ModifierID = row.ModifierID,
        Choosable = choosable,
        RequiresUnit = row.RequiresUnit,
    })
end
```

## 步骤 5：带外键+时代的配置表 (Celebrations 风格)

```sql
CREATE TABLE IF NOT EXISTS NWflower_Celebrations (
    CelebrationsTypes TEXT NOT NULL,
    Name              TEXT,
    Description       TEXT,
    PreEra            TEXT NOT NULL DEFAULT 'ERA_ANCIENT'
        REFERENCES Eras(EraType) ON UPDATE CASCADE ON DELETE SET DEFAULT,
    ObsoleteEra       TEXT DEFAULT NULL
        REFERENCES Eras(EraType) ON UPDATE CASCADE ON DELETE SET DEFAULT,
    UnlocksFromEffect INTEGER DEFAULT 0,
    Weight            INTEGER DEFAULT 100,
    PRIMARY KEY ('CelebrationsTypes'),
    CHECK (UnlocksFromEffect IN (0, 1)),
    CHECK (Weight >= 0)
);

-- 自动填充 Name 和 Description
UPDATE NWflower_Celebrations
SET Name = 'LOC_' || CelebrationsTypes || '_NAME',
    Description = 'LOC_' || CelebrationsTypes || '_DESCRIPTION'
WHERE CelebrationsTypes IS NOT NULL;
```

**自动填充技巧**：用字符串拼接 `'LOC_' || CelebrationsTypes || '_NAME'` 统一生成 LOC 标签，减少手动 INSERT 工作量。

## 步骤 6：关联映射表设计

```sql
-- 映射表：庆典类型 -> 虚拟建筑
CREATE TABLE IF NOT EXISTS NWflower_CelebrationModifiers (
    CelebrationsTypes TEXT NOT NULL
        REFERENCES NWflower_Celebrations(CelebrationsTypes)
            ON UPDATE CASCADE ON DELETE CASCADE,
    BuildingType TEXT DEFAULT NULL
        REFERENCES Buildings(BuildingType)
            ON UPDATE CASCADE ON DELETE SET NULL,
    PRIMARY KEY ('CelebrationsTypes')
);

-- 自动填充：BUILDING_ + 类型名 = 建筑名
INSERT OR REPLACE INTO NWflower_CelebrationModifiers (CelebrationsTypes, BuildingType)
SELECT CelebrationsTypes, 'BUILDING_' || CelebrationsTypes
FROM NWflower_Celebrations;
```

## 步骤 7：配置表 + 参数化 (GameMode 风格)

Celebrations 是一个 GameMode，有可调参数：

```xml
<!-- Config XML: 注册游戏模式 -->
<GameModeItems>
    <Row GameModeType="GAMEMODE_CELEBRATION"
         Name="LOC_GAMEMODE_CELEBRATION_NAME"
         Description="LOC_GAMEMODE_CELEBRATION_DESCRIPTION"
         Portrait="GAMEMODE_CELEBRATION_PORT"
         Icon="ICON_GAMEMODE_CELEBRATION"
         SortIndex="10"/>
</GameModeItems>

<Parameters>
    <!-- 启用/禁用 -->
    <Row ParameterId="GAMEMODE_CELEBRATION" Domain="bool" DefaultValue="1"
         ConfigurationId="GAMEMODE_CELEBRATION"
         GroupId="GameModes" SortIndex="100"/>

    <!-- 高级选项：庆典的时代限制 -->
    <Row ParameterId="NW_CELEBRATION_ERA_SETTING"
         Domain="NW_CELEBRATION_ERA_CONFIG" DefaultValue="0"
         ConfigurationId="NW_CELEBRATION_ERA_SETTING"
         GroupId="AdvancedOptions" ChangeableAfterGameStart="0" SortIndex="1679"/>

    <!-- 高级选项：触发频率 -->
    <Row ParameterId="NW_CELEBRATION_FREQUENCY"
         Domain="NW_CELEBRATION_FREQUENCY_CONFIG" DefaultValue="2"
         ConfigurationId="NW_CELEBRATION_FREQUENCY"
         GroupId="AdvancedOptions" ChangeableAfterGameStart="0" SortIndex="1679"/>
</Parameters>

<DomainValues>
    <Row Domain="NW_CELEBRATION_ERA_CONFIG" Value="0"
         Name="LOC_ERA_CONFIG_0_NAME" SortIndex="1"/>
    <Row Domain="NW_CELEBRATION_ERA_CONFIG" Value="1"
         Name="LOC_ERA_CONFIG_1_NAME" SortIndex="2"/>
    <Row Domain="NW_CELEBRATION_ERA_CONFIG" Value="2"
         Name="LOC_ERA_CONFIG_2_NAME" SortIndex="3"/>
</DomainValues>
```

**Lua 读取参数**：
```lua
local FREQUENCY = GameConfiguration.GetValue('NW_CELEBRATION_FREQUENCY') or 2
```

## 步骤 8：条件加载 (ActionCriteria)

```xml
<ActionCriteria>
    <!-- 只在庆典模式开启时加载 -->
    <Criteria id="Celebration_Gamemode">
        <ConfigurationValueMatches>
            <ConfigurationId>GAMEMODE_CELEBRATION</ConfigurationId>
            <Group>Game</Group>
            <Value>1</Value>
        </ConfigurationValueMatches>
    </Criteria>

    <!-- 子选项：不同配置加载不同 SQL -->
    <Criteria id="Policy_Slots_Never_Expire">
        <ConfigurationValueMatches>
            <ConfigurationId>NW_CELEBRATION_ERA_SETTING</ConfigurationId>
            <Group>Game</Group>
            <Value>1</Value>
        </ConfigurationValueMatches>
    </Criteria>
</ActionCriteria>

<InGameActions>
    <!-- 带条件加载 -->
    <UpdateDatabase id="Celebrations_DB" Criteria="Celebration_Gamemode">
        ...
    </UpdateDatabase>
    <UpdateDatabase id="Celebrations_DB_PS" Criteria="Policy_Slots_Never_Expire">
        <File>Celebrations_Database_PermanentlySlots.sql</File>
    </UpdateDatabase>
</InGameActions>
```

## 要点总结

1. **表命名**：自定义表加前缀或后缀避免与游戏表冲突
2. **外键约束**：引用游戏核心表确保数据完整性
3. **默认值**：所有非关键字段给合理的 DEFAULT 值
4. **LOC 自动生成**：用 SQL 拼接 `'LOC_' || key || '_SUFFIX'` 批量设置 Name/Description
5. **AI/人类分支**：通过复制 Modifier 并加 `SubjectRequirementSetId='PLAYER_IS_AI'` 实现
6. **GameInfo 访问**：自定义表自动暴露为 `GameInfo.TableName()` 迭代器
7. **条件加载**：用 ActionCriteria 根据游戏设置选择性加载不同数据文件
8. **参数化**：用 Parameters/DomainValues 提供玩家可调设置，用 `GameConfiguration.GetValue()` 读取
