# religion-agenda — 信仰与议程条目（sections「信仰」「议程」）

> 两个 list section 共用此模板。

## 信仰条目（样例 U14.CIV）

| 键 | 填法 |
|----|------|
| `name` / `abbr` / `type` | `BELIEF_{PREFIX}_...` |
| `BeliefType` | 完整信仰 Type |
| `table_name` / `table_data` | 工具管理，不动 |
| `Name` / `Description` | 游戏内名/描述 |
| `icon_image_name` / `portrait_image_name` / `images` | 图标/竖图 |
| `use_official_icon` | 是否用官方图标（bool） |
| `subtables` | 次级表 |

> 信仰效果 = 「修改器」section（`BeliefModifiers` 挂载链）。信仰分类（万神殿/信徒/崇拜）以工具表单为准。

## 议程条目（**样例全空**，以工具源码为准）

- `entity_table_form.py`：议程表字段 `Name`/`Description`（中文）+ `type_key="AgendaType"`
- 工具生成链（`workspace_page.py`）：`Agendas`(AgendaType/Name/Description) → `AgendaTraits`（**自动生成 `TRAIT_{AgendaType}`**）→ `HistoricalAgendas`（绑定所属领袖，每个领袖建议只绑一个）→ 可选 `ExclusiveAgendas`（与随机议程互斥，AgendaTwo 候选来自游戏库 RandomAgendas）→ `AiLists`
- 议程效果 = 「修改器」section（`MODIFIER_PLAYER_DIPLOMACY_SIMPLE_MODIFIER`，SubjectRequirementSetId 可从游戏库导入官方模板；ModifierString Preview 自动生成）
- 隐藏议程：`HiddenAgenda`（触发后可见）

## 出口检查

- [ ] 信仰/议程 Type 前缀规范；议程随机池/互斥对象在游戏库存在
- [ ] 议程的 TraitType 自动生成（不手写冲突）
- [ ] 外交效果用 `MODIFIER_PLAYER_DIPLOMACY_SIMPLE_MODIFIER` + 官方条件模板（DB 验证）
