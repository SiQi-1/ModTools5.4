# promotion — 单位晋升条目（section「单位晋升」）

> list section。条目形态（样例 53.CIV）：`{abbr, type, name, mode, nodes}` —— **无 table_name 包装**，节点树直接内嵌。
> 内容知识桥接 `01-core-tables/unit.md` 晋升段 + `skills/07-techniques/modifiers.md`。

## 条目键（53.CIV 实测）

| 键 | 填法 |
|----|------|
| `abbr` / `type` / `name` | 三段头（type = `UNIT_` 前缀晋升树 Type，规则同其它条目） |
| `mode` | 树模式（工具表单） |
| `nodes` | **节点列表**：每个节点 = 一个晋升（名称/列行位置/前置节点/效果绑定） |

## 要点

- 每个晋升节点的效果 = 指向「修改器」section 的 modifiers（`MODIFIER_PLAYER_UNIT_...` 或标准 `MODIFIER_UNIT_...`），或游戏既有晋升效果
- 晋升树节点间用 `promotion_prereqs` 类字段构成前后置（以工具表单为准）
- 晋升类（PromotionClass）在「单位」条目 units_xp2 中指定，本 section 只建树

## 出口检查

- [ ] 节点效果全部在「修改器」section 有定义（无孤儿 modifier_id）
- [ ] 树无环（前置链完整）
- [ ] PromotionClass 在 DB 验证
