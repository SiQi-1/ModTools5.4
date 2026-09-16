# Modifier 通用技巧

> 本文档收录跨 EffectType 的通用 Schema 模式、常见陷阱和最佳实践。每个 EffectType 的参数详见同目录下 `modifier-*.md` 子文件。

---

## 技巧 1：Ability 的 TypeTags 过滤机制

**核心原则**：Ability 通过 TypeTags 绑定的 CLASS Tag **本身就是匹配过滤器**，不论 Inactive=0 还是 Inactive=1。

- `Inactive=0`：同 Tag 单位**自动获得**能力（无需任何 Modifier）
- `Inactive=1`：需 `EFFECT_GRANT_ABILITY` Modifier 手动授予，但**仍然受 Tag 过滤**——只有同 Tag 的单位才能被授予

**应用**：给特定兵种授予能力时，**不需要在 GRANT_ABILITY Modifier 上写 SubjectRequirementSet 按 PROMOTION_CLASS 筛选**。只需给 Ability 绑定对应 CLASS Tag，Tag 本身就会过滤。

**示例 — 只给远程+攻城单位授予能力**：

```sql
-- Ability 绑 Tag（Tag 过滤）
INSERT INTO TypeTags (Type, Tag) VALUES
('ABILITY_SIQI_RANGE_POWER', 'CLASS_RANGED'),
('ABILITY_SIQI_RANGE_POWER', 'CLASS_SIEGE');

-- Ability 设 Inactive=1
INSERT INTO UnitAbilities (...) VALUES
('ABILITY_SIQI_RANGE_POWER', NULL, '...', 1, 1);

-- 领袖特质授予，无需 SubjectRequirementSet
INSERT INTO Modifiers (ModifierId, ModifierType) VALUES
('MODIFIER_SIQI_GRANT_RANGE_POWER', 'MODIFIER_PLAYER_UNITS_GRANT_ABILITY');
INSERT INTO ModifierArguments (ModifierId, Name, Value) VALUES
('MODIFIER_SIQI_GRANT_RANGE_POWER', 'AbilityType', 'ABILITY_SIQI_RANGE_POWER');
INSERT INTO TraitModifiers (TraitType, ModifierId) VALUES
('TRAIT_LEADER_SIQI_xxx', 'MODIFIER_SIQI_GRANT_RANGE_POWER');
```

---

## 技巧 2：用 PLOTS 上下文检测战斗距离

**问题**：COMBATS 上下文中没有任何带 MinRange/MaxRange 的 RequirementType，无法直接检测"攻击者与目标的距离"。

**解决**：战斗 Modifier（`COLLECTION_UNIT_COMBAT`）中，Subject 是目标单位，其所在地块也是"地块"。因此可以用 **PLOTS 上下文的 RequirementType** 挂到 `SubjectRequirementSetId` 上。

**关键 RequirementType**：`REQUIREMENT_PLOT_ADJACENT_TO_OWNER`（参数 `MinDistance` / `MaxDistance`）

- Owner = 攻击方单位，Owner 所在地块 = 攻击起点
- Subject 地块 = 目标所在地块 = 攻击落点
- 两个地块的距离 = 攻击距离

**示例 — 攻击距离为 N 时战斗力 +N×3**：

```sql
-- 距离=5 时 +15 战斗力（10组硬编码，MinDist=MaxDist 精确匹配）
INSERT INTO Modifiers (ModifierId, ModifierType, SubjectRequirementSetId) VALUES
('MODIFIER_DIST_5_COMBAT', 'MODIFIER_UNIT_ADJUST_COMBAT_STRENGTH', 'REQSET_PLOT_DIST_5');

-- 条件：目标地块距离 Owner = 5
INSERT INTO Requirements (RequirementId, RequirementType) VALUES
('REQ_PLOT_DIST_5', 'REQUIREMENT_PLOT_ADJACENT_TO_OWNER');
INSERT INTO RequirementArguments (RequirementId, Name, Value) VALUES
('REQ_PLOT_DIST_5', 'MinDistance', 5),
('REQ_PLOT_DIST_5', 'MaxDistance', 5);
```

> **为什么 MinDist = MaxDist？** 范围条件（如 MinDist=1 MaxDist=5）会导致符合条件的多个 Modifier 同时生效、预览文本出现多条。精确匹配保证每次只有一个 Modifier 命中，预览干净。
