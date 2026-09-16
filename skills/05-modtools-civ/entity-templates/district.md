# district — 区域条目（section「区域」）

> list section。条目键来自样例 32.CIV。内容知识桥接 `01-core-tables/district.md` + `skills/district-adjacency.md`。

## 条目键（32.CIV 实测）

| 键 | 填法 | 桥接 |
|----|------|------|
| `name` / `abbr` / `type` | `DISTRICT_{PREFIX}_...` | `06-naming.md` |
| `DistrictType` | 完整区域 Type（大写键 = 游戏实体） | `01-core-tables/district.md` |
| `table_name` / `table_data` | 工具管理，不动 | — |
| `Name` / `Description` | 游戏内名/描述（工具生成 LOC） | `01-core-tables/district.md` |
| `icon_image_name` / `portrait_image_name` / `images` | 图标/竖图 | `02-config-files/icons.md` |
| `districts_xp2` | 核心表数据（成本/维护/人口需求等，工具表单） | `01-core-tables/district.md` |
| `district_great_person_points` | 每回合伟人点 | — |
| `district_citizen_yield_changes` | 公民产出 | — |
| `district_required_features` | 需求地形（如火山） | DB 验证 |
| `district_trade_route_yields` | 贸易路线产出 | — |
| `district_valid_terrains` | 可建地形 | — |
| `district_replaces` | 替换哪个区域（`DistrictType`） | — |
| `adjacencies` | **相邻加成规则列表**（核心：ID/Description/YieldType/YieldChange/TilesRequired + 单条件） | `skills/district-adjacency.md`（完整规范） |
| `subtables` | 次级表 | — |

## 相邻加成要点（详情 district-adjacency.md）

- 一条规则只设一个条件（AdjacentTerrain/Feature/District/River/Wonder/NaturalWonder/Resource/ResourceClass/SeaResource/OtherDistrictAdjacent/Self）；多条件 = 多条规则
- 山脉加成标准写法：5 种地形各一条（GRASS/PLAINS/DESERT/TUNDRA/SNOW）
- Description 格式：`{解锁条件}+{1_Amount}[ICON_X]产出 来自相邻的{条件}。`
- 产出图标映射：YIELD_SCIENCE→`[ICON_Science]`、PRODUCTION→`[ICON_Production]`、GOLD→`[ICON_Gold]`、FOOD→`[ICON_Food]`、CULTURE→`[ICON_Culture]`、FAITH→`[ICON_Faith]`

## 出口检查

- [ ] 区域类型/替换对象/地形条件全部在 DB 验证过
- [ ] adjacencies 每条：单条件、有 Description、TilesRequired 合理（少量=2/标准=1/大量=2 每格产出）
- [ ] 图标字段与 `02-config-files/icons.md` 尺寸对照一致
