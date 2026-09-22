# unit — 单位条目（section「单位」）

> list section。条目键来自样例 32.CIV。内容知识桥接 `01-core-tables/unit.md`。

## 条目键（32.CIV 实测）

| 键 | 填法 | 桥接 |
|----|------|------|
| `name` / `abbr` / `type` | `UNIT_{PREFIX}_...` | `06-naming.md` |
| `UnitType` | 完整单位 Type | `01-core-tables/unit.md` |
| `table_name` / `table_data` | 工具管理，不动 | — |
| `Name` / `Description` | 游戏内名/描述 | — |
| `icon_image_name` / `portrait_image_name` / `images` | 图标/竖图（模型图另走美术 section） | `02-config-files/icons.md` |
| `units_mode` / `units_presentation` | 模式（基础/资料片）/展示配置 | — |
| `units_xp2` | 核心表（成本/战斗力/移动力/视野/维护/晋升类 PromotionClass 等，工具表单） | `01-core-tables/unit.md` |
| `unit_replaces` / `unit_upgrades` | 替换/升级（`UNIT_*`） | — |
| `unit_captures` / `unit_retreats_xp1` | 俘虏/撤退形态 | — |
| `unit_building_prereqs` | 建造前置建筑 | — |
| `unit_ai_infos` | AI 用途（UNITAI_*，工具选择框） | DB 验证 |
| `type_tags` | 标签（TAG_*，如 TAG_NAVAL） | DB 验证 |
| `unit_ability_bindings` | **能力绑定**（指向「修改器」section 的 unit_abilities 或游戏既有能力） | `07-techniques/modifiers.md` |
| `subtables` | 次级表 | — |

## 要点

- 特殊单位若需独特能力 → 「修改器」section 的 `unit_abilities` 建能力条目，再在本条目 `unit_ability_bindings` 绑定（链完整，[规则正文](../../RULES.md)）
- TypeProperties（LIFESPAN 等）为 DLL 硬编码名，**不能自创**；工具表单内选择（查 [TypeProperties 参考](../../05-modtools-civ/authoring-reference.md)）
- 单位模型/图标贴图由美术 section 或工具"生成图标定义"处理

## 出口检查

- [ ] PromotionClass/UNITAI/TAG 全部 DB 验证（`SELECT DISTINCT ...`，[规则正文](../../RULES.md)）
- [ ] 能力绑定在 unit_abilities 或游戏库中存在
