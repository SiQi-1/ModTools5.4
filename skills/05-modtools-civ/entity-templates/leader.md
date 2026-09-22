# leader — 领袖条目（section「领袖」）

> list section。条目键来自样例 32.CIV。内容知识桥接 `01-core-tables/leader.md` + `agenda.md` + `02-config-files/diplo-text.md`。

## 条目键（32.CIV 实测）

| 键 | 填法 | 桥接 |
|----|------|------|
| `name` / `abbr` / `type` | 同文明条目（`LEADER_{PREFIX}_...`） | `06-naming.md` |
| `leader_name` | 游戏内领袖名（工具生成 LOC_LEADER_xxx_NAME） | `01-core-tables/leader.md` |
| `sex` | 性别（头像/文本用） | — |
| `capital_name` | 首都名（进城市名池） | — |
| `civilization_type` / `civilization_name` | 所属文明（必须已在「文明」section） | — |
| `leader_text` | 图鉴简介（PEDIA_LEADERS_PAGE） | `01-core-tables/leader.md` |
| `leader_quote` | 开场引言 | — |
| `ability_name` / `ability_description` | 领袖能力名/描述 → `TRAIT_LEADER_{TYPE}` | `01-core-tables/leader.md` |
| `select_sort_index` | 选人界面排序 | — |
| `add_diplo_background_curtain` | 外交背景幕布（bool） | — |
| `icon_image_name` | 头像图标 | `02-config-files/icons.md` |
| `foreground_image_name` / `background_image_name` | 文明选择背景图 | `02-config-files/icons.md` |
| `diplo_foreground_image_name` / `diplo_background_image_name` / `select_foreground_image_name` / `select_background_image_name` | 外交/选择界面图 | `02-config-files/icons.md` |
| `images` | 图片源对象（无图留 `{}`） | — |
| `bindings` | 特质挂载（能力/议程绑定） | [规则正文](../../RULES.md) |
| `diplomacy` | **外交文本结构**（问候/拒绝/议程反馈等；游戏内每句引一条 LOC） | `02-config-files/diplo-text.md` |

## 铁律（[规则正文](../../RULES.md) 的 .CIV 形态）

- 新建领袖继承基类：`InheritFrom` 语义 = 继承特质，**新建领袖一律 `LEADER_DEFAULT`**（工具在 bindings/内部表处理）
- 领袖议程：优先从游戏库 `RandomAgendas` 选（`group_workspace.py` 逻辑），自定义议程走「议程」section

## 出口检查

- [ ] civilization_type 指向「文明」section 已建条目
- [ ] 外交文本每句都有对应中文（diplo-text.md 模板）
- [ ] 领袖能力有独立 `TRAIT_LEADER_`（不共用文明特质）
