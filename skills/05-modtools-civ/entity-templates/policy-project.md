# policy-project — 政策卡与项目条目（sections「政策卡」「项目」）

> 两个 list section 共用此模板。内容知识桥接 `01-core-tables/policy.md` + `project.md`。

## 政策卡条目（样例 50.CIV）

| 键 | 填法 |
|----|------|
| `name` / `abbr` / `type` | `POLICY_{PREFIX}_...` |
| `PolicyType` | 完整政策 Type |
| `table_name` / `table_data` | 工具管理，不动 |
| `Name` / `Description` | 游戏内名/描述（政策卡文本，`[ICON_xxx] 标签` 必带文字，陷阱 8） |
| `icon_image_name` / `portrait_image_name` / `images` | 图标/竖图 |
| `policies_xp1` | 核心表（槽位 GovernmentSlotType/时代/成本等，工具表单） |
| `policy_government_exclusive` | 专属政体（`GOVERNMENT_*`，DB 验证） |
| `subtables` | 次级表 |

> 政策效果 = 「修改器」section（`PolicyModifiers` 挂载链）。

## 项目条目（样例 32.CIV）

| 键 | 填法 |
|----|------|
| `name` / `abbr` / `type` | `PROJECT_{PREFIX}_...` |
| `ProjectType` | 完整项目 Type |
| `table_name` / `table_data` | 工具管理，不动 |
| `Name` / `Description` | 游戏内名/描述 |
| `icon_image_name` / `portrait_image_name` / `images` | 图标/竖图 |
| `projects_mode` / `projects_xp1` / `projects_xp2` | 模式/核心表（成本/时代/区域要求等，工具表单） |
| `project_building_costs` | 建筑成本类型（BUILDING_*） |
| `project_great_person_points` | 伟人点奖励（GreatPersonClassType/点数） |
| `project_resource_costs` | 资源消耗 |
| `project_yield_conversions` | 产出转化（如产能→信仰） |
| `project_prereqs` | 前置（科技/项目） |
| `subtables` | 次级表 |

> 项目完成效果 = 「修改器」section（`ProjectCompletionModifiers` 挂载链）。

## 出口检查

- [ ] 槽位/政体/建筑/伟人类型全部 DB 验证
- [ ] 效果挂载链完整（PolicyModifiers / ProjectCompletionModifiers 有行）
