# Policy — 政策卡定义

## 涉及文件

| 文件 | 内容 |
|------|------|
| `Data/<ModName>_Policies.sql` | 政策卡主表 + 子表 |
| `Icons/<ModName>_Icons.xml` | `icons.md` — 政策卡图标（共用 `ICON_ATLAS_POLICIES` 图集） |
| `Scripts/<ModName>_Scripts.lua` | ExplicitUnlock 政策的 Lua 解锁（方法2） |

## 涉及的表（按 INSERT 顺序）

```
Types → Policies → [Policies_XP1] → [Policy_GovernmentExclusives_XP2]
→ [ObsoletePolicies] → PolicyModifiers
```

---

## 一、Types

```sql
INSERT INTO Types (Type, Kind) VALUES
('POLICY_SIQI_{SHORT}', 'KIND_POLICY');
```

---

## 二、Policies（主表，8 列）

### 完整 INSERT 模板

```sql
INSERT INTO Policies (
    PolicyType,
    Name,
    Description,
    PrereqCivic,
    PrereqTech,
    GovernmentSlotType,
    RequiresGovernmentUnlock,
    ExplicitUnlock
) VALUES
(
    'POLICY_SIQI_{SHORT}',
    'LOC_POLICY_SIQI_{SHORT}_NAME',
    'LOC_POLICY_SIQI_{SHORT}_DESCRIPTION',
    'CIVIC_DEFENSIVE_TACTICS',
    NULL,
    'SLOT_MILITARY',
    0,
    0
);
```

### 逐列参考

**身份 + 文本：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 1 | PolicyType | `POLICY_SIQI_{SHORT}` | **必写** |
| 2 | Name | `LOC_POLICY_SIQI_{SHORT}_NAME` | **必写** |
| 3 | Description | `LOC_POLICY_SIQI_{SHORT}_DESCRIPTION` | 按需 |

**前置条件：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 4 | PrereqCivic | `CIVIC_xxx` | 可选（与 PrereqTech 二选一） |
| 5 | PrereqTech | `TECH_xxx` | 可选 |

**槽位 / 解锁：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 6 | GovernmentSlotType | 见下表 | **必写** |
| 7 | RequiresGovernmentUnlock | 1=需政体解锁，通常不写 | 默认 NULL |
| 8 | ExplicitUnlock | 1=不随市政自动解锁，需 Lua 手动 `UnlockPolicy` | 按需 |

> **GovernmentSlotType 可选值：**
> | 值 | 说明 |
> |----|------|
> | `SLOT_MILITARY` | 军事槽 |
> | `SLOT_ECONOMIC` | 经济槽 |
> | `SLOT_DIPLOMATIC` | 外交槽 |
> | `SLOT_GREAT_PERSON` | 伟人槽 |
> | `SLOT_WILDCARD` | 万能槽 |

---

## 三、Policies_XP1（时代/年龄限制）

```sql
INSERT INTO Policies_XP1 (PolicyType, MinimumGameEra, MaximumGameEra, RequiresDarkAge, RequiresGoldenAge) VALUES
('POLICY_SIQI_{SHORT}', NULL, NULL, 0, 0);
```

| # | 列名 | 说明 |
|---|------|------|
| 1 | PolicyType | 政策卡 |
| 2 | MinimumGameEra | 最低可用时代，如 `ERA_MEDIEVAL` |
| 3 | MaximumGameEra | 最高可用时代 |
| 4 | RequiresDarkAge | 1=仅黑暗时代可用（黑暗政策卡） |
| 5 | RequiresGoldenAge | 1=仅黄金时代可用（着力点政策卡） |

---

## 四、Policy_GovernmentExclusives_XP2（政体遗产卡）

```sql
INSERT INTO Policy_GovernmentExclusives_XP2 (PolicyType, GovernmentType) VALUES
('POLICY_SIQI_{SHORT}', 'GOVERNMENT_DEMOCRACY');
```

> 切换政体后，旧政体的独占政策卡可保留一张继续使用。

| # | 列名 | 说明 |
|---|------|------|
| 1 | PolicyType | 政策卡 |
| 2 | GovernmentType | 绑定的政体 |

---

## 五、ObsoletePolicies（淘汰机制）

```sql
INSERT INTO ObsoletePolicies (PolicyType, ObsoletePolicy, RequiresAvailableGreatPersonClass) VALUES
('POLICY_DISCIPLINE', 'POLICY_NATIVE_CONQUEST', NULL);
```

| # | 列名 | 说明 |
|---|------|------|
| 1 | PolicyType | 被淘汰的旧政策卡 |
| 2 | ObsoletePolicy | 替代的新政策卡（可为 NULL） |
| 3 | RequiresAvailableGreatPersonClass | 需要已招募某类伟人才能淘汰（如 `GREAT_PERSON_CLASS_GENERAL`）。独立条件，可不配合 ObsoletePolicy 使用 |

---

## 六、PolicyModifiers

```sql
INSERT INTO PolicyModifiers (PolicyType, ModifierId) VALUES
('POLICY_SIQI_{SHORT}', 'MODIFIER_SIQIXXX_xxx');
```

> ModifierId 定义在 `07-techniques/modifiers.md`。

---

## 七、技巧一：专属政策卡（Ban + 反选）

纯 SQL 实现，禁止非目标文明使用。

```sql
-- 对所有玩家禁用政策卡，仅目标领袖除外
INSERT INTO Modifiers (ModifierId, ModifierType, OwnerRequirementSetId) VALUES
('MODIFIER_SIQI_BAN_POLICY_{SHORT}', 'MODIFIER_MAJOR_PLAYERS_ADJUST_BANNED_POLICY', 'REQSET_IS_NOT_OUR_LEADER_{SHORT}');

INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
('MODIFIER_SIQI_BAN_POLICY_{SHORT}', 'PolicyType', 'POLICY_SIQI_{SHORT}');

INSERT INTO GameModifiers (ModifierId) VALUES
('MODIFIER_SIQI_BAN_POLICY_{SHORT}');

-- 条件集：非我方领袖
INSERT INTO RequirementSets (RequirementSetId, RequirementSetType) VALUES
('REQSET_IS_NOT_OUR_LEADER_{SHORT}', 'REQUIREMENTSET_TEST_ALL');

INSERT INTO RequirementSetRequirements (RequirementSetId, RequirementId) VALUES
('REQSET_IS_NOT_OUR_LEADER_{SHORT}', 'REQ_IS_NOT_OUR_LEADER_{SHORT}');

INSERT INTO Requirements (RequirementId, RequirementType, Inverse) VALUES
('REQ_IS_NOT_OUR_LEADER_{SHORT}', 'REQUIREMENT_PLAYER_LEADER_TYPE_MATCHES', 1);

INSERT INTO RequirementArguments (RequirementId, Name, Value) VALUES
('REQ_IS_NOT_OUR_LEADER_{SHORT}', 'LeaderType', 'LEADER_SIQI_{SHORT}');
```

> 原理：`MODIFIER_MAJOR_PLAYERS_ADJUST_BANNED_POLICY`（标准类型，EffectType=`EFFECT_ADJUST_PLAYER_BAN_POLICY`，CollectionType=`COLLECTION_MAJOR_PLAYERS`，参数 `PolicyType`）挂到 `GameModifiers`（全局），但 OwnerRequirementSet 用 Inverse 反选，只有非目标领袖被 Ban，目标领袖不受影响。
>
> ⚠️ 类型名易错：正确是 `MAJOR_PLAYERS` + `BANNED_POLICY`（复数 + BANNED）。`MODIFIER_PLAYER_ADJUST_BAN_POLICY` 不存在（曾误写）。

---

## 八、技巧二：ExplicitUnlock + Lua

政策卡设 `ExplicitUnlock=1`，不随市政自动解锁，通过 Lua 事件精准控制。

### SQL 侧

```sql
INSERT INTO Policies (PolicyType, Name, Description, PrereqCivic, GovernmentSlotType, ExplicitUnlock) VALUES
('POLICY_SIQI_{SHORT}', 'LOC_POLICY_SIQI_{SHORT}_NAME', 'LOC_POLICY_SIQI_{SHORT}_DESCRIPTION', NULL, 'SLOT_WILDCARD', 1);
```

### Lua 侧

```lua
-- 解锁政策卡（PolicyIndex = Policies 表 Index，非 Types 表 Index）
local PolicyIndex = GameInfo.Policies["POLICY_SIQI_{SHORT}"].Index
if not pPlayer:GetCulture():IsPolicyUnlocked(PolicyIndex) then
    pPlayer:GetCulture():UnlockPolicy(PolicyIndex)
end
```

**完整示例（区域建成解锁 + 防重复）：**
```lua
OnDistrictCompleted = function(self, playerID)
    local pPlayer = Players[playerID]
    if pPlayer:GetProperty("SIQI0030_UNLOCKED_POLICY_X") then return end
    pPlayer:SetProperty("SIQI0030_UNLOCKED_POLICY_X", true)

    local PolicyIndex = GameInfo.Policies["POLICY_SIQI_P0030_1"].Index
    if not pPlayer:GetCulture():IsPolicyUnlocked(PolicyIndex) then
        pPlayer:GetCulture():UnlockPolicy(PolicyIndex)
    end
end,
```

> `UnlockPolicy` 的参数是 `GameInfo.Policies["xxx"].Index`（Policies 表 Index），**不是** `GameInfoTypes["xxx"]`（Types 表 Index），两者不同。

**关键 Lua 接口：**
| 接口 | 说明 |
|------|------|
| `pPlayer:GetCulture():UnlockPolicy(index)` | 解锁政策卡（参数为 Policy Index） |
| `pPlayer:GetCulture():IsPolicyUnlocked(index)` | 查是否已解锁 |
| `pPlayer:GetCulture():IsPolicyBanned(index)` | 查是否被禁用 |
| `pPlayer:GetCulture():IsPolicyActive(index)` | 查是否正在使用 |

---

## 九、Text — 本地化文本

```sql
INSERT INTO LocalizedText (Language, Tag, Text) VALUES
('zh_Hans_CN', 'LOC_POLICY_SIQI_{SHORT}_NAME',        '{中文名}'),
('zh_Hans_CN', 'LOC_POLICY_SIQI_{SHORT}_DESCRIPTION', '{中文描述}');
```

---

## 十、Enum 文件

| 文件 | 内容 |
|------|------|
| [GovernmentSlotType 查询依据](../SOURCES.md#类型与枚举) | 5 种政策槽位 |
