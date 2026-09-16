# improvement — 改良设施条目（section「改良设施」）

> list section。条目键来自样例 40.CIV。内容知识桥接 `01-core-tables/improvement.md`。

## 条目键（40.CIV 实测）

| 键 | 填法 | 桥接 |
|----|------|------|
| `name` / `abbr` / `type` | `IMPROVEMENT_{PREFIX}_...` | `06-naming.md` |
| `ImprovementType` | 完整改良 Type | `01-core-tables/improvement.md` |
| `table_name` / `table_data` | 工具管理，不动 | — |
| `Name` / `Description` | 游戏内名/描述 | — |
| `icon_image_name` / `portrait_image_name` / `images` | 图标/竖图 | `02-config-files/icons.md` |
| `improvements_mode` / `improvements_xp2` | 模式/核心表（产出/建造者次数/移动消耗等，工具表单） | `01-core-tables/improvement.md` |
| `improvement_tourism` | 旅游业绩 | — |
| `improvement_yields_outside_territories` | 领土外产出 | — |
| `improvement_bonus_yield_changes` / `improvement_yield_changes` | 基础产出 / 加成产出 | — |
| `improvement_invalid_adjacent_features` | 禁止相邻特征 | DB 验证 |
| `improvement_valid_adjacent_resources` / `improvement_valid_adjacent_terrains` | 相邻资源/地形条件 | DB 验证 |
| `improvement_valid_build_units` | 可建造单位（如建造者/军事工程师） | DB 验证 |
| `improvement_valid_features` / `improvement_valid_resources` / `improvement_valid_terrains` | 可建特征/资源/地形 | DB 验证 |
| `improvement_adjacencies` | 相邻加成（规则同区域 `district-adjacency.md`） | `skills/district-adjacency.md` |
| `subtables` | 次级表 | — |

## 出口检查

- [ ] 地形/特征/资源/单位条件全部 DB 验证
- [ ] 相邻加成单条件规则 + Description 格式正确
