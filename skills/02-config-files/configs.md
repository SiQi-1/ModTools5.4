# Configs — Players + PlayerItems 注册

## 数据来源

`DebugConfiguration.sqlite`（前端配置数据库，**不是** DebugGameplay.sqlite）。Players 和 PlayerItems 均在此外。

## 涉及文件

| 文件 | 内容 |
|------|------|
| `Data/<ModName>_Configs.sql` | Players 注册 + PlayerItems 预览 |

> 此文件在 FrontEndActions 中加载。

---

## 一、Players

每个文明+领袖组合注册一行。同一文明多个领袖 = 多行，每行一个领袖。

```sql
INSERT INTO Players (
    Domain,
    CivilizationType,
    CivilizationName,
    CivilizationIcon,
    CivilizationAbilityName,
    CivilizationAbilityDescription,
    CivilizationAbilityIcon,
    LeaderType,
    LeaderName,
    LeaderIcon,
    LeaderAbilityName,
    LeaderAbilityDescription,
    LeaderAbilityIcon,
    Portrait,
    PortraitBackground,
    SortIndex
) VALUES
(
    'Players:Expansion2_Players',
    'CIVILIZATION_SIQI_{SHORT}',
    'LOC_CIVILIZATION_SIQI_{SHORT}_NAME',
    'ICON_CIVILIZATION_SIQI_{SHORT}',
    'LOC_TRAIT_CIVILIZATION_SIQI_{SHORT}_NAME',
    'LOC_TRAIT_CIVILIZATION_SIQI_{SHORT}_DESCRIPTION',
    'ICON_CIVILIZATION_SIQI_{SHORT}',
    'LEADER_SIQI_{SHORT}',
    'LOC_LEADER_SIQI_{SHORT}_NAME',
    'ICON_LEADER_SIQI_{SHORT}',
    'LOC_TRAIT_LEADER_SIQI_{SHORT}_NAME',
    'LOC_TRAIT_LEADER_SIQI_{SHORT}_DESCRIPTION',
    'ICON_LEADER_SIQI_{SHORT}',
    'PORTRAIT_LEADER_SIQI_{SHORT}',
    'PORTRAIT_BACKGROUND_LEADER_SIQI_{SHORT}',
    10
);
```

| # | 列名 | 说明 | 写不写 |
|---|------|------|--------|
| 1 | Domain | `Players:StandardPlayers` / `Players:Expansion1_Players` / `Players:Expansion2_Players` | **必写** |
| 2 | CivilizationType | `CIVILIZATION_SIQI_{SHORT}` | **必写** |
| 3 | CivilizationName | 文明名 LOC | **必写** |
| 4 | CivilizationIcon | 文明图标 | **必写** |
| 5 | CivilizationAbilityName | 文明特质名 LOC | **必写** |
| 6 | CivilizationAbilityDescription | 文明特质描述 LOC | **必写** |
| 7 | CivilizationAbilityIcon | 文明特质图标 | **必写** |
| 8 | LeaderType | `LEADER_SIQI_{SHORT}` | **必写** |
| 9 | LeaderName | 领袖名 LOC | **必写** |
| 10 | LeaderIcon | 领袖图标 | **必写** |
| 11 | LeaderAbilityName | 领袖特质名 LOC | **必写** |
| 12 | LeaderAbilityDescription | 领袖特质描述 LOC | **必写** |
| 13 | LeaderAbilityIcon | 领袖特质图标 | **必写** |
| 14 | Portrait | 领袖肖像纹理，`PORTRAIT_LEADER_SIQI_{SHORT}` | 按需 |
| 15 | PortraitBackground | 肖像背景，`PORTRAIT_BACKGROUND_LEADER_SIQI_{SHORT}` | 按需 |
| 16 | SortIndex | 选择界面排序位置（同文明多领袖建议同值） | 按需 |

> `PlayerColor` 一般省略（走 Colors.sql），`HumanPlayable` 默认 1。

---

## 二、PlayerItems

列出每个文明+领袖组合的**特色实体**（区域/单位/建筑/改良/总督等），在选人界面预览显示。

```sql
INSERT INTO PlayerItems (
    Domain,
    CivilizationType,
    LeaderType,
    Type,
    Icon,
    Name,
    Description,
    SortIndex
) VALUES
(
    'Players:Expansion2_Players',
    'CIVILIZATION_SIQI_{SHORT}',
    'LEADER_SIQI_{SHORT}',
    'DISTRICT_SIQI_BALLROOM',
    'ICON_DISTRICT_SIQI_BALLROOM',
    'LOC_TRAIT_DISTRICT_SIQI_BALLROOM_NAME',
    'LOC_TRAIT_DISTRICT_SIQI_BALLROOM_DESCRIPTION',
    10
);
```

| # | 列名 | 说明 |
|---|------|------|
| 1 | Domain | 同 Players |
| 2 | CivilizationType | 同 Players |
| 3 | LeaderType | 同 Players |
| 4 | Type | 实体 TYPE（`DISTRICT_xxx` / `UNIT_xxx` / `BUILDING_xxx` / `IMPROVEMENT_xxx` / `GOVERNOR_xxx`） |
| 5 | Icon | 实体图标 |
| 6 | Name | 显示名 LOC（**用 TRAIT_ 版本的 LOC**，不是实体自身的 LOC_xxx_NAME） |
| 7 | Description | 显示描述 LOC（同 TRAIT_ 版本） |
| 8 | SortIndex | 预览顺序（10, 20, 30...） |

> **规则**：
> - 只列特色实体，不列基础游戏实体
> - 同一实体属于多个领袖时，每个领袖各写一行
> - 不同领袖的同一文明可以有**不同的** PlayerItems 列表
> - Name/Description 用 `LOC_TRAIT_xxx_NAME/DESCRIPTION`（特质文本），非实体自身的 `LOC_xxx_NAME`

---

## 三、modinfo 加载顺序

```
FrontEndActions:
  1. UpdateDatabase (Configs.sql)     ← 最先加载
  2. UpdateText (Text_CN.sql)
  3. UpdateIcons
```

---

## 四、自动推导流程

生成 Configs.sql 时，无需用户额外说明。从已有的 skill 输出自动汇总：

1. 遍历 civilization.md / leader.md → 生成 Players 行（每个 civ+leader 组合一个）
2. 遍历 district.md / unit.md / building.md / improvement.md / governor.md → 收集所有 `SIQI_` 实体 Type
3. 按 civ+leader 分组生成 PlayerItems 行

> **注意**：实体归属哪个领袖由用户在其他 skill 中通过 TraitType 指定。Configs 阶段用 TraitType 反向匹配：某个实体的 TraitType 指哪个 Leader/Civ，该实体就出现在对应 PlayerItems 中。
