# Belief — 信仰定义（万神殿 / 创建者 / 追随者 / 强化者 / 崇拜 五类）

> 来源沉淀：Siqi_Update_0014（38 个自定义信条，2026-08 实测修正）。
> **核心铁律：信仰效果一律"间接两层"挂载（BeliefModifiers → 外层 ATTACH → 内层效果），禁止把效果 modifier 直接挂 BeliefModifiers**（0014 曾直接挂购买/解锁类效果，已实测修正为间接结构）。

## 涉及文件

| 文件 | 内容 |
|------|------|
| `Data/<ModName>_Beliefs.sql` | 信条主表（Types + Beliefs） |
| `Data/<ModName>_Modifiers.sql` | 效果链（BeliefModifiers + 外层 ATTACH + 内层效果 + 条件） |
| `Text/<ModName>_Text_CN.sql` | LOC_BELIEF 文本 |
| `Icons/<ModName>_Icons.xml` | 图标（自定义图集或复用 vanilla 图集） |

## 涉及的表（按 INSERT 顺序）

```
Types → Beliefs → BeliefModifiers → Modifiers(外层 ATTACH) → ModifierArguments
→ Modifiers(内层效果) → ModifierArguments → [RequirementSets → Requirements → RequirementArguments]
```

---

## 一、Types + Beliefs（主表）

```sql
INSERT INTO Types (Type, Kind) VALUES
('BELIEF_SIQI_B0014_1', 'KIND_BELIEF');

INSERT INTO Beliefs (BeliefType, Name, Description, BeliefClassType) VALUES
('BELIEF_SIQI_B0014_1', 'LOC_BELIEF_SIQI_B0014_1_NAME', 'LOC_BELIEF_SIQI_B0014_1_DESCRIPTION', 'BELIEF_CLASS_PANTHEON');
```

**BeliefClassType 枚举（决定信条出现在哪个选择池）：**

| 值 | 用途 |
|----|------|
| `BELIEF_CLASS_PANTHEON` | 万神殿（创建万神殿时选择；自定义数量直接进池子） |
| `BELIEF_CLASS_FOUNDER` | 创建者信条（大预言家创建宗教时选 1，**仅创教者受益**） |
| `BELIEF_CLASS_FOLLOWER` | 追随者信条（创建宗教时选 1，信教城市受益） |
| `BELIEF_CLASS_ENHANCER` | 强化者信条（强化宗教时选 1，宗教机制） |
| `BELIEF_CLASS_WORSHIP` | 崇拜信条（强化宗教时选 1，解锁宗教建筑，配 `MODIFIER_PLAYER_RELIGION_ADD_RELIGIOUS_BUILDING`） |

---

## 〇、五类信仰对照（核心速查，DB 实测）

> 每类信仰有**专属的 Requirement 语义**——选错类别 = 效果条件语义错误（0014 曾把 10 个创建者信条误标为万神殿，已修正）。

| 类别 | 语义 / 谁受益 | 选择时机 | 标准 Requirement | 典型效果（官方实例） | 挂载要点 |
|------|--------------|---------|------------------|---------------------|---------|
| **万神殿** PANTHEON | 创世神祇 / 全玩家 | 攒够信仰创建万神殿时选 1 | `PLAYER_HAS_PANTHEON_REQUIREMENTS`（玩家级）<br>`CITY_FOLLOWS_PANTHEON_REQUIREMENTS`（城市级） | 地块产出（收获女神）、相邻加成（丛林礼节）、城市加成、单位能力 | ATTACH 间接；相邻加成/城市成长可**直接挂**（官方例外清单） |
| **创建者** FOUNDER | 创教者专属收益 / 仅创教者 | 大预言家创建宗教时选 1 | **`PLAYER_FOUNDED_RELIGION_REQUIREMENTS`**（玩家是宗教创立者） | 每回合金币（什一税）、外交支持、伟人点、城市收益（商单：炼金科技~联盟协议类） | ATTACH 间接，外层 subject=PLAYER_FOUNDED_RELIGION_REQUIREMENTS；城市级效果外层用 **Owner**=该条件 |
| **追随者** FOLLOWER | 信徒产出收益 / 信教城市 | 创建宗教时选 1 | **`CITY_FOLLOWS_RELIGION_REQUIREMENTS`**（城市信仰该宗教）；变体 `CITY_FOLLOWS_RELIGION_HAS_SHRINE/TEMPLE`、`_WITH_2 DISTRICTS` | 城市产出：每奇迹/每区域/每人口/巨作收益（职业道德/神启/年历类） | ATTACH 间接，城市级效果外层 subject=CITY_FOLLOWS_RELIGION；玩家级集合效果用 PLAYER_FOUNDED_RELIGION |
| **强化者** ENHANCER | 宗教机制增强 / 全玩家 | 强化宗教时选 1 | **无统一条件**：`PLAYER_FOUNDED_RELIGION_REQUIREMENTS`（神圣秩序/传教士狂热）或自定义 req（`DEFENDER_OF_FAITH_REQUIREMENTS`/`JUST_WAR_REQUIREMENTS`/`HOLY_WATERS_HEALING_REQUIREMENTS`） | 传播强度/距离、自动传播、宗教战斗（圣战）、信仰购买（魂灵/辉光类）、宗教项目（拾荒类） | ATTACH + 自定义 req；宗教机制类（传播/自动传播/战斗损失）可直接挂 |
| **崇拜** WORSHIP | 宗教建筑 / 全玩家 | 强化宗教时选 1 | **无条件**（不需要 req） | 解锁宗教建筑（清真寺/宝塔类） | **直接挂** `MODIFIER_PLAYER_RELIGION_ADD_RELIGIOUS_BUILDING`（官方 14 个全如此，唯一例外）；建筑本身要三级链（寺庙前置） |

**四个核心 Requirement（官方定义）**：

| RequirementSet | Requirement | 语义 |
|----------------|------------|------|
| `PLAYER_HAS_PANTHEON_REQUIREMENTS` | `REQUIREMENT_PLAYER_HAS_PANTHEON` | 玩家拥有万神殿 |
| `CITY_FOLLOWS_PANTHEON_REQUIREMENTS` | `REQUIREMENT_CITY_FOLLOWS_PANTHEON` | 城市信仰万神殿 |
| `PLAYER_FOUNDED_RELIGION_REQUIREMENTS` | `REQUIREMENT_PLAYER_IS_RELIGION_FOUNDER` | 玩家是宗教创立者 |
| `CITY_FOLLOWS_RELIGION_REQUIREMENTS` | `REQUIREMENT_CITY_FOLLOWS_RELIGION` | 城市信仰该宗教 |

**类别选错的表现**：万神殿条件（`PLAYER_HAS_PANTHEON`）对创建者/强化者信条无效（选信条时条件必真但语义错误、且万神殿池被污染）；追随者用万神殿城市条件会让"不信教城市"也生效。0014 实测：创建者/强化者的玩家级效果统一用 `PLAYER_FOUNDED_RELIGION_REQUIREMENTS`，追随者城市级用 `CITY_FOLLOWS_RELIGION_REQUIREMENTS`。

---

## 二、效果挂载 — 间接两层（铁律）

### 什么时候必须间接 / 可以直接挂（DB 实测：DebugGameplay.sqlite 官方挂载统计）

| 挂载表 | ATTACH 间接 | 直接挂 | 结论 |
|--------|------------|--------|------|
| **BeliefModifiers（信条）** | **72%（62/86）** | 27%（24/86） | **一律间接两层**（除下表例外） |
| TraitModifiers（文明/领袖特质） | 13%（231/1741） | 86%（1510/1741） | **直接挂为主** |
| BuildingModifiers（建筑） | 3% | 96% | 直接挂 |
| DistrictModifiers（区域） | 2% | 97% | 直接挂 |
| UnitAbilityModifiers（单位能力） | 0% | 99% | 直接挂 |
| ProjectCompletionModifiers（项目完成） | 5% | 94% | 直接挂 |

**判别本质**：ATTACH 的作用是"把单对象效果扩散到多个满足条件的对象"（外层遍历 + 条件，内层挂到每个对象上）：
- 效果是**集合型**（`MODIFIER_PLAYER_CITIES_*` / `MODIFIER_ALL_CITIES_*` / `MODIFIER_PLAYER_UNITS_*` 等，作用于拥有者的所有子对象，新城新单位自动纳入）→ 挂在**特质/建筑/能力**上时**直接挂即可**（官方 86~99% 都这样）
- 效果是**单对象型**（`MODIFIER_SINGLE_CITY_*` / `MODIFIER_BUILDING_*` / `MODIFIER_UNIT_ADJUST_*`）→ 挂载点本身就是该对象时直接挂（BuildingModifiers 挂建筑）；挂载点是玩家/信条而要作用于"每个城市/单位"时**必须 ATTACH**
- **需要子对象级动态条件**（城市有某建筑/区域、地块特征/魅力、单位位置）→ 必须 ATTACH（外层 Subject 条件，内层只挂到满足条件的对象）
- **信条场景例外（官方直接挂，仅此 24 个）**：宗教建筑解锁 `ADD_RELIGIOUS_BUILDING`、相邻加成 `TERRAIN/FEATURE_ADJACENCY`、宗教机制类（`ENABLE_RELIGION_AUTO_SPREAD` / `ADJUST_RELIGIOUS_SPREAD_*` / `ENABLE_RELIGION_AWARDS_ENVOY` / `ADD_RELIGIOUS_UNIT` 等）、个别玩家级（`ADJUST_CITY_GROWTH`）
- **信条场景其余一切**（地块产出 / 建筑产出 / 城市加成 / 能力授予 / 信仰购买 / 购买折扣 / 解锁建造 / 伟人点数 / 商路…）→ 官方全部包成 ATTACH 间接，**禁止直接挂**（0014 实测：购买/解锁类直接挂不生效）

### 错误写法（直接挂效果，0014 实测不生效）

```sql
-- ❌ 禁止：BeliefModifiers 直接挂效果 modifier
INSERT INTO BeliefModifiers (BeliefType, ModifierId) VALUES
('BELIEF_XXX', 'MODIFIER_XXX_ENABLE_UNIT_FAITH_PURCHASE');
```

### 标准写法（间接两层）

```
BeliefModifiers (BeliefType, ModifierId)
  → 外层 MODIFIER_XXX_ATTACH（MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER / MODIFIER_ALL_CITIES_ATTACH_MODIFIER）
      ├─ OwnerRequirementSetId：可选（时代等玩家级条件，如 REQSET_ERA_AT_LEAST_MEDIEVAL）
      ├─ SubjectRequirementSetId：PLAYER_HAS_PANTHEON_REQUIREMENTS（玩家级）或 CITY_FOLLOWS_PANTHEON_REQUIREMENTS（城市级）
      └─ 参数 ModifierId → 内层
  → 内层 MODIFIER_XXX（实际效果，如 MODIFIER_PLAYER_CITIES_ENABLE_UNIT_FAITH_PURCHASE）
```

### 玩家级效果模板（能力授予 / 商路 / 购买解锁 / 政策槽等）

```sql
-- 外层（挂 BeliefModifiers）
INSERT INTO BeliefModifiers (BeliefType, ModifierId) VALUES
('BELIEF_XXX', 'MODIFIER_XXX_ATTACH');

INSERT INTO Modifiers (ModifierId, ModifierType, OwnerRequirementSetId, SubjectRequirementSetId, RunOnce, Permanent) VALUES
('MODIFIER_XXX_ATTACH', 'MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER', NULL, 'PLAYER_HAS_PANTHEON_REQUIREMENTS', 0, 0);

INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
('MODIFIER_XXX_ATTACH', 'ModifierId', 'MODIFIER_XXX');

-- 内层（实际效果）
INSERT INTO Modifiers (ModifierId, ModifierType, OwnerRequirementSetId, SubjectRequirementSetId, RunOnce, Permanent) VALUES
('MODIFIER_XXX', 'MODIFIER_PLAYER_CITIES_ENABLE_UNIT_FAITH_PURCHASE', NULL, NULL, 0, 0);

INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
('MODIFIER_XXX', 'Tag', 'CLASS_MELEE');
```

### 城市级效果模板（地块产出 / 城市加成等）

```sql
-- 外层 subject 用 CITY_FOLLOWS_PANTHEON_REQUIREMENTS，内层用城市/地块效果
INSERT INTO Modifiers (...) VALUES
('MODIFIER_XXX_ATTACH', 'MODIFIER_ALL_CITIES_ATTACH_MODIFIER', NULL, 'CITY_FOLLOWS_PANTHEON_REQUIREMENTS', 0, 0);

INSERT INTO ModifierArguments (...) VALUES
('MODIFIER_XXX_ATTACH', 'ModifierId', 'MODIFIER_XXX');

INSERT INTO Modifiers (...) VALUES
('MODIFIER_XXX', 'MODIFIER_CITY_PLOT_YIELDS_ADJUST_PLOT_YIELD', NULL, 'REQSET_XXX_PLOT_FEATURE', 0, 0);
```

### 时代条件（中世纪后生效等）

条件放**外层 OwnerRequirementSetId**，内层保持无条件：

```sql
INSERT INTO Modifiers (...) VALUES
('MODIFIER_XXX_ATTACH', 'MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER', 'REQSET_SIQI_0014_ERA_AT_LEAST_MEDIEVAL', 'PLAYER_HAS_PANTHEON_REQUIREMENTS', 0, 0);
```

---

## 三、按效果类型选链（速查）

| 想做什么 | 外层 | 内层 EffectType（示例） |
|----------|------|------------------------|
| 地块产出 | `MODIFIER_ALL_CITIES_ATTACH_MODIFIER` + `CITY_FOLLOWS_PANTHEON_REQUIREMENTS` | `MODIFIER_CITY_PLOT_YIELDS_ADJUST_PLOT_YIELD`（subject=地块条件） |
| 城市产出/防御/回血 | 同上 | `MODIFIER_SINGLE_CITY_ADJUST_CITY_YIELD_MODIFIER` / `ADJUST_OUTER_DEFENSE` 等 |
| 建筑产出 | 同上 | `MODIFIER_BUILDING_YIELD_CHANGE` |
| 单位能力授予 | `MODIFIER_ALL_PLAYERS_ATTACH_MODIFIER` + `PLAYER_HAS_PANTHEON_REQUIREMENTS` | `MODIFIER_PLAYER_UNITS_GRANT_ABILITY`（AbilityType 参数） |
| 信仰购买单位 | 同上 | `MODIFIER_PLAYER_CITIES_ENABLE_UNIT_FAITH_PURCHASE`（Tag 参数，按类逐个开放） |
| 信仰购买建筑 | 同上 | `MODIFIER_PLAYER_CITIES_ENABLE_BUILDING_FAITH_PURCHASE`（DistrictType 参数，按区域逐个开放） |
| 购买折扣 | 同上 | `MODIFIER_PLAYER_CITIES_ADJUST_ALL_BUILDINGS_PURCHASE_COST`（Amount=-40） |
| 解锁单位建造 | 同上 | `MODIFIER_PLAYER_ADJUST_VALID_UNIT_BUILD`（UnitType 参数，官方拉合尔城邦同款） |
| 区域效果 | 同上 | `MODIFIER_PLAYER_DISTRICTS_ADJUST_YIELD_MODIFIER` / `MODIFIER_ALL_DISTRICTS_ADJUST_YIELD_BASED_ON_ADJACENCY_BONUS`（subject=区域条件） |
| 政策槽 | 同上（可无 ATTACH 条件问题，仍建议间接） | `MODIFIER_PLAYER_CULTURE_ADJUST_GOVERNMENT_SLOTS_MODIFIER` |
| 玩家点数/商路 | 同上 | `MODIFIER_PLAYER_ADJUST_GREAT_PERSON_POINTS` / `MODIFIER_PLAYER_ADJUST_TRADE_ROUTE_YIELD` |

---

## 四、分档 / 遍历生成（重复效果用 SELECT，不手写）

- 遍历单位类、区域、特色单位等 → `INSERT ... SELECT ... FROM Tags / Districts / UnitReplaces`（先例：0049 信仰购买、0014 特色单位解锁）
- 魅力等数值分档 → 递归 CTE（SQLite 支持，先例 0035/0014）：

```sql
-- 魅力 1~20 分档：每档一条"外层 ATTACH + 内层产出 + 魅力区间条件"
INSERT INTO BeliefModifiers (BeliefType, ModifierId)
WITH RECURSIVE nums(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM nums WHERE n < 20)
SELECT 'BELIEF_XXX', 'MODIFIER_XXX_APPEAL_' || n || '_ATTACH' FROM nums;
```

---

## 五、图标与文本

- **五类信仰共用一个官方图集** `ICON_ATLAS_BELIEFS_PATHEON`（8×8=64 格，官方 `Icons_Beliefs.xml` 实证），按类别固定 Index：
  - 万神殿 = **专属图案**（Index 0-21/26/27，每个万神殿不同图标）→ **只有万神殿可用自定义专属图标**（0014：B1-B6 自定义 DDS）
  - **FOUNDER 创建者 = Index 24**（官方什一税/教皇首席等 9 信条通用图标）
  - FOLLOWER 追随者 = Index 23（神启/职业道德等通用图标）
  - ENHANCER 强化者 = Index 25（圣战/神圣秩序等通用图标）
  - WORSHIP 崇拜 = Index 22（清真寺/宝塔等建筑通用图标）
- 自定义图标：`ICON_BELIEF_XXX`（32/38/50/64/256 五档）
- 文本：`LOC_BELIEF_XXX_NAME`（简洁 2-6 字）+ `LOC_BELIEF_XXX_DESCRIPTION`（`[NEWLINE]` 分段落，`[ICON_Faith]` 等图标嵌入，图标后必须带文字标签；崇拜信条描述按官方格式"允许建造X（建筑效果列表）。"）

---

## 六、陷阱（实测）

1. **禁止直接挂效果（信条）**：购买/解锁/折扣类（`ENABLE_*_FAITH_PURCHASE`、`ADJUST_PLAYER_VALID_UNIT_BUILD`、`ADJUST_ALL_BUILDINGS_PURCHASE_COST`）以及绝大多数信仰效果，都必须走"外层 ATTACH → 内层"间接链；唯一可直接挂的是 §二 例外清单（宗教建筑/相邻/宗教机制）。**特质/建筑/区域/单位能力/项目完成挂载点则相反——直接挂是官方标准（86~99%）**
2. **条件位置**：时代/玩家级条件放外层 `OwnerRequirementSetId`；地块/单位级条件放内层 `SubjectRequirementSetId`
3. **类别与 Requirement 必须匹配**（0014 实测）：创建者/强化者的玩家级效果用 `PLAYER_FOUNDED_RELIGION_REQUIREMENTS`，追随者城市级用 `CITY_FOLLOWS_RELIGION_REQUIREMENTS`，**禁止对非万神殿信条用 `PLAYER_HAS_PANTHEON_REQUIREMENTS`**（万神殿池被污染 + 条件语义错误）；SELECT 生成行的条件行在下一行，批量替换时容易漏
4. **事件类 Requirement 必须 `Triggered=1`**（否则只触发一次）
5. **宗教建筑**（崇拜信条）：`Buildings` 表 `EnabledByReligion=1` + `PurchaseYield='YIELD_FAITH'` + 前置 `DISTRICT_HOLY_SITE`；**三级链**：`BuildingPrereqs (Building, PrereqBuilding)` 写 `('BUILDING_X', 'BUILDING_TEMPLE')`（官方崇拜建筑全如此）；**不要写 `BuildingReplaces` 的 `'0'` 行**（外键违规，官方从不写）；通用巨作槽用 `GREATWORKSLOT_PALACE`（非遗物槽）
6. **解锁特色单位**（隐藏能力）：`MODIFIER_PLAYER_ADJUST_VALID_UNIT_BUILD` 遍历 `UnitReplaces`；信仰购买需新建自定义 Tag（`Tags` 表 `Vocabulary='ABILITY_CLASS'`，无需注册 Types）批量绑定特色单位后按 Tag 开放
7. **建筑资源累积用 per-turn**：`MODIFIER_SINGLE_CITY_ADJUST_FREE_RESOURCE_EXTRACTION`（官方杰贝勒巴尔卡尔奇观同款），`MODIFIER_SINGLE_CITY_GRANT_RESOURCE_IN_CITY` 是一次性（伟人同款）
8. 万神殿数量：`BELIEF_CLASS_PANTHEON` 数量直接影响万神殿选择池（24 官方 + 自定义）；图标按类别固定 Index（§五），只有万神殿用自定义专属图标

---

## 七、全特性信条（吸收同类全部效果，0016 实测）

> 需求：一款信条 = 同类别其他全部信条的能力（"信徒全特性信仰"等）。**方案 A：共享 ModifierId，只遍历 BeliefModifiers**。

- 信条效果面只有 3 张表：`Beliefs` / `BeliefModifiers` / `BeliefClasses`；**无 Belief_ValidBuildings**，崇拜建筑解锁也在 BeliefModifiers 里走 `ADD_RELIGIOUS_BUILDING`
- 官方链是"BeliefModifiers → 外层 ATTACH → 参数 `ModifierId` → 内层效果"，内层不在 BeliefModifiers 里 → 把同类全部 `ModifierId` 挂到新信条即可**按引用原样复用整条链**（0016 实测 222 行、断链 0），无需任何新 Modifier 行：

```sql
INSERT INTO BeliefModifiers (BeliefType, ModifierId)
SELECT 'BELIEF_XXX', bm.ModifierId
FROM BeliefModifiers bm
JOIN Beliefs b ON b.BeliefType = bm.BeliefType
WHERE b.BeliefClassType = 'BELIEF_CLASS_FOLLOWER'
  AND b.BeliefType <> 'BELIEF_XXX';   -- 排除自身防自引用
```

- **LoadOrder 拉满（999999）**：SELECT 只能吸收"加载顺序在它之前"的信条（含其他 Mod）；要兼容 Mod 就把本文件放最后加载
- 安全前提：每类 `MaxInReligion=1`、每城单宗教、每玩家单创教 → 同一 ModifierId 不可能重复挂到同一对象（无双挂载）
- **官方中文类别名**（local_text 实证）：信徒 / 创始人 / 祭祀 / 强化——不是"追随者/创立者/创建者"
