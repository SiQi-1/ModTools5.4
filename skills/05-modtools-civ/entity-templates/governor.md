# governor — 总督条目（section「总督」）

> list section。条目键来自样例 32.CIV（5 个总督条目）。内容知识桥接 `01-core-tables/governor.md`。

## 条目键（32.CIV 实测）

| 键 | 填法 | 桥接 |
|----|------|------|
| `name` / `code` / `GovernorType` | 中文名 / 代码（英文缩写）/ `GOVERNOR_{TYPE}` | `06-naming.md` |
| `Name` / `Description` | 游戏内名/描述 | `01-core-tables/governor.md` |
| `Title` / `ShortTitle` | 称号（总督面板显示） | — |
| `IdentityPressure` / `TransitionStrength` / `AssignCityState` | 忠诚压力/过渡强度/城邦指派（数值或 null） | — |
| `TraitType` | 特质（工具表单选择/生成） | — |
| `new_trait_type` | 是否新建特质（bool） | — |
| `assign_to_major` / `cannot_assign` | 指派限制（bool） | — |
| `Image` / `PortraitImage` / `PortraitImageSelected` | 立绘（游戏惯例：总督图） | `02-config-files/icons.md` |
| `icon_image_name` / `icon_fill_image_name` / `icon_slot_image_name` / `images` | 图标三态 | — |
| `promotions` | **总督晋升列表**（每个晋升含名称/效果绑定） | `01-core-tables/governor.md` 晋升段 |

## 要点

- 每个晋升的效果 = 指向「修改器」section 的 modifiers（`GovernorPromotionModifiers` 挂载链）
- 晋升前置链（GovernorPromotionSets）以工具表单为准

## 出口检查

- [ ] 每个晋升的效果在「修改器」section 有定义（无孤儿）
- [ ] 图标三态字段齐全或 `images` 留 `{}`
