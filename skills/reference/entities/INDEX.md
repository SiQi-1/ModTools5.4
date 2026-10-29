# 实体模板地图（reference/entities）

> 受众：写 .CIV 实体条目的制作者 ｜ 何时读：新增/修改文明、领袖、区域、建筑、单位等实体时 ｜ 适用版本：ModTools 5.4

> 每个模板 = 该实体在 .CIV 中的**条目键清单**（来自真实样例工程）+ 每个键的填法与相关参考。
> 键名以样例为准；新建条目时若工具已升级，以工具"新增"按钮生成的结构为准。
> 实体 Type / Modifier / Requirement 命名见 [命名参考](naming.md)；导出 SQL 的列含义只在需要核对时查 [表参考](../sql/INDEX.md)，不是必读。

## 模板清单

| 模板 | .CIV section | 条目形态 | 相关参考（内容层） |
|------|-------------|---------|------------------|
| `basic-info.md` | 基础信息（dict） | prefix/infix/工程信息 | [工程文件](../project/civ6proj.md)、[Configs](../config/configs.md) |
| `civilization.md` | 文明（list） | 文明条目 | [Configs](../config/configs.md)、[Colors](../config/colors.md)、[文明文化美术](../art/civilization-art.md) |
| `leader.md` | 领袖（list） | 领袖条目 | [议程](religion-agenda.md)、[外交文本](../config/diplo-text.md)、[领袖美术](../art/leader-art.md) |
| `district.md` | 区域（list） | 区域条目 | [相邻加成](../config/district-adjacency.md) |
| `building.md` | 建筑（list） | 建筑条目 | [修改器索引](../modifiers/INDEX.md) |
| `unit.md` | 单位（list） | 单位条目 | 修改器见 [修改器索引](../modifiers/INDEX.md) |
| `promotion.md` | 单位晋升（list） | 晋升树（nodes） | 单位条目 `unit.md` |
| `improvement.md` | 改良设施（list） | 改良条目 | [相邻加成](../config/district-adjacency.md) |
| `governor.md` | 总督（list） | 总督条目 + promotions | 条目键见本文件 |
| `greatperson.md` | 伟人（list） | 伟人条目 | 样例为空，以工具导入为准 |
| `policy-project.md` | 政策卡+项目（list） | 两条目 | 条目键见本文件 |
| `religion-agenda.md` | 信仰+议程（list） | 两条目 | 议程样例为空，以工具为准 |

## 通用规则（所有条目适用）

1. **`name`/`abbr`/`type` 三段头**：name=中文名，abbr=英文缩写（字母/数字/下划线），type=工具生成的完整 Type 名，只允许英文字母/数字/下划线；命名规则见 [命名参考](naming.md)。
2. **文本字段**：`Name`/`Description` 等大写键 = 游戏内文本（工具自动生成 LOC）；`*_name`/`*_description` 小写键 = 工具界面内名称；`loc_*` = 显式 LOC 控制。LOC 规范见 [文本规范](../config/text.md)。
3. **`table_name`/`table_data`**：由工具管理（默认模板表），不要手改。
4. **`images`**：对象字典（含 `icon_image_name`/`portrait_image_name` 等子键的源）；图标 PNG 由用户提供或工具从游戏库取。
5. **`subtables`**：次级表列表（如建筑的特殊产出表），条目键内以子表数组承载。
6. 所有值禁 `""`（见 [常见陷阱](../../guides/civ-pitfalls.md)）。

## 其他参考入口

- [naming — 实体命名（Type/Modifier/Requirement）](naming.md)
- [basic-info — 基础信息 section（.CIV 的根基）](basic-info.md)
- [building — 建筑条目（section「建筑」）](building.md)
- [civilization — 文明条目（section「文明」）](civilization.md)
- [district — 区域条目（section「区域」）](district.md)
- [governor — 总督条目（section「总督」）](governor.md)
- [greatperson — 伟人条目（section「伟人」）](greatperson.md)
- [improvement — 改良设施条目（section「改良设施」）](improvement.md)
- [leader — 领袖条目（section「领袖」）](leader.md)
- [policy-project — 政策卡与项目条目（sections「政策卡」「项目」）](policy-project.md)
- [promotion — 单位晋升条目（section「单位晋升」）](promotion.md)
- [religion-agenda — 信仰与议程条目（sections「信仰」「议程」）](religion-agenda.md)
- [unit — 单位条目（section「单位」）](unit.md)
