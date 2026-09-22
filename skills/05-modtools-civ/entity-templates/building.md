# building — 建筑条目（section「建筑」）

> list section。条目键来自样例 32.CIV。内容知识桥接 `01-core-tables/building.md`。

## 条目键（32.CIV 实测）

| 键 | 填法 | 桥接 |
|----|------|------|
| `name` / `abbr` / `type` | `BUILDING_{PREFIX}_...` | `06-naming.md` |
| `BuildingType` | 完整建筑 Type | `01-core-tables/building.md` |
| `table_name` / `table_data` | 工具管理，不动 | — |
| `Name` / `Description` | 游戏内名/描述 | — |
| `icon_image_name` / `portrait_image_name` / `images` | 图标/竖图 | `02-config-files/icons.md` |
| `buildings_xp2` | 核心表（成本/维护/区域归属/专家槽等，工具表单） | `01-core-tables/building.md` |
| `building_replaces` | 替换建筑 | — |
| `building_prereqs` | 前置建筑/科技 | — |
| `building_citizen_yield_changes` | 公民产出 | — |
| `building_great_person_points` | 伟人点 | — |
| `building_required_features` / `building_valid_features` / `building_valid_terrains` | 地形/特征条件 | DB 验证 |
| `building_tourism_bombs_xp2` | 旅游业绩（考古等） | — |
| `building_resource_costs` | 资源消耗（如铀） | — |
| `building_yield_changes` / `building_yield_changes_bonus_with_power` | 产出 / 供电加成 | — |
| `building_yield_district_copies` | 复制区域产出（相邻加成入库） | — |
| `building_yields_per_era` | 时代递增产出 | — |
| `building_conditions` | 建造条件（如区域存在） | — |
| `building_build_charge_productions` | 建造者次数产出 | — |
| `building_greatworks` | **巨作槽位**（GreatWorkSlotType/数量） | `01-core-tables/building.md` 巨作段 |
| `subtables` | 次级表 | — |

## 铁律（[规则正文](../../RULES.md) 的 .CIV 形态）

- 建筑特质必须独立 `TRAIT_BUILDING_{TYPE}`（工具在 `trait_bindings`/内部自动生成，**不可复用文明/领袖特质**）

## 出口检查

- [ ] 建筑替换/前置/巨作槽 Type 全部 DB 验证
- [ ] 建筑特有产出效果若需 Modifier → 走「修改器」section，owners 挂 `BuildingModifiers` 链（陷阱 12）
