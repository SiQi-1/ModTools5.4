# 写 Modifier SQL 前的强制检查清单

> **在写任何 INSERT 之前，逐项回答。全部确认后才开始写代码。**

## 第零步：确认最接近的参考 Mod

- [ ] 找到功能最相似的已有 Mod 工程名 + 文件名
- [ ] 打开该文件的对应部分，准备逐列对照

| 任务类型 | 推荐参考 |
|---------|---------|
| ATTACH 链（通用Trait） | `Siqi_Leaders_0045/Modifiers.sql` |
| Property → Combat | `Siqi_Leaders_0032/Modifiers.sql` 行 621, 1088, 1723 |
| 多层手动遍历 | `Siqi_Leaders_0045/Modifiers.sql` 行 5-71, 131-196 |
| 建城效果 | `Siqi_Leaders_0045/Modifiers.sql` 行 121-124 |
| 区域槽位效果 | `Siqi_Leaders_0045/Modifiers.sql` 行 201-202 |

## 第一步：列清单

- [ ] 列出本功能所有 ModifierId（对外层 ATTACH 和内层效果分别列出）
- [ ] 列出每个 Modifier 要用的 **ModifierType**（精确到标准名）
- [ ] 列出需要新建的 Type（KIND_MODIFIER + KIND_ABILITY）
- [ ] 列出所有 RequirementType（精确到从 CSV/DB 验证过的名称）

## 第二步：验证 ModifierType 是否存在

每个 ModifierType 必须通过以下方式之一验证：

1. 在已有 Mod 的 SQL 中能搜到该 ModifierType 被使用
2. 标准类型清单中明确列出

**不确定是否存在的，用 Grep 搜已有项目（0032、0045、Core）。搜不到就创建 DynamicModifier。**

禁止行为：
- 凭记忆写 ModifierType 名
- 假设 "应该和 EffectType 同名"
- 为已存在的标准类型创建 DynamicModifier

## 第三步：确认表列序

复制参考文件的 INSERT 列名，不要自己写：

```
Modifiers:      (ModifierId, ModifierType, SubjectRequirementSetId, RunOnce, Permanent)
Requirements:   (RequirementId, RequirementType, Inverse)
ModifierArguments: (ModifierId, Name, Value)
```

确认 `Inverse` vs `Triggered` — 默认用 `Inverse`。

## 第四步：验证 RequirementType

每个 RequirementType 必须：
- [ ] 在 CSV 中存在（`reference/csv-export/Requirements.csv`）
- [ ] 参数名和参数类型正确（查 "RequirementArguments" 部分的参数名）
- [ ] 对于事件类 Requirement（如 `REQUIREMENT_PLAYER_TURN_STARTED`），确认是否需 `Triggered=1`

## 第五步：写代码

- [ ] 从参考文件**复制链结构**（表顺序、列顺序、链中各层关系）
- [ ] 只改 Type 名和数值
- [ ] 每个 ATTACH 的 ModifierArguments 写 `ModifierId` 参数链到内层
- [ ] TraitModifiers / DistrictModifiers / UnitAbilityModifiers 等关联表不遗漏

## 第六步：写完自检

- [ ] 每个 ModifierId 在 ModifierArguments 中都有对应条目
- [ ] 每个 ATTACH 的 ModifierId 参数指向一个存在的 ModifierId
- [ ] 每个 GrantAbility 的 AbilityType 参数指向一个存在的 AbilityType
- [ ] 每个 Ability 在 UnitAbilityModifiers 中都有条目
- [ ] 所有 RequirementSet 在 RequirementSetRequirements 中都有条目
- [ ] LOC 文本 Key 与 Text SQL 中的 Tag 一一对应（如果有 ModifierStrings）
