# 范围挂载：每个来源对象贡献一份效果

适用：每有一个满足距离/类型条件的区域、城市、单位、改良或建筑，目标获得固定奖励；例如“每个恰好两格远的区域，提供 +4 相邻”。先读 [修改器指南](../../../05-modtools-civ/modifiers.md) 和 [ATTACH 机制](../modifier-attach.md)。

## 先判断是不是必须算出一个数字

如果效果是 `合格来源数 × 固定 Amount`，每个来源各挂一份效果即可自然累加。来源移走、被移除或条件不满足时，由原生动态链撤销相应贡献。只为乘以固定值而扫描地图、写 Property、展开二进制，通常多了一整套状态同步。

原生条件能够表达的“没有相邻区域”、区域类型、拥有者特质也不需要 Property。真正需要读取城市文化总值、取整换算等原生表/效果无法表达的动态数值，才考虑 [Property 二进制](../../../04-lua/lua-binary.md)。永久奖励的 `AttachModifierByID` 是另一种用法，不等于这里可撤销的 `EFFECT_ATTACH_MODIFIER` 链。

## 来源到目标的链路

```text
挂载入口（特质、GameModifiers，或实体原生挂载表）
  → 来源集合 + 来源条件：为每个来源 S 挂内层 Modifier
    → 目标集合 + 目标条件：owner=S，subject=T
      → REQUIREMENT_PLOT_ADJACENT_TO_OWNER：MinDistance=2, MaxDistance=2
      → 目标类型、目标拥有者条件
      → Attach 固定产出 Modifier 到 T
        → COLLECTION_OWNER：owner=T，Amount=4
```

两个合格来源分别贡献 +4，合计 +8；同一 Modifier 定义可以产生多个来源实例。距离必须在 owner 仍是 S 的那一层判断，不能等 attach 到 T 后再比较 T 与自己。

若直接以源对象挂载 `COLLECTION_*` 的固定效果就能表达需求，可省去最后一次 ATTACH。已有 DistrictModifiers / BuildingModifiers / ImprovementModifiers / UnitAbility 等入口时，优先复用；不要机械增加层数。

| 来源/目标 | 集合与挂载要点 |
|---|---|
| 区域 | `COLLECTION_ALL_DISTRICTS` / `COLLECTION_PLAYER_DISTRICTS`；市中心是否计入、虚拟 `DISTRICT_WONDER` 是否排除须明确 |
| 城市 | `COLLECTION_ALL_CITIES` / `COLLECTION_PLAYER_CITIES`；距离通常定位到市中心 |
| 单位 | 单位集合或 UnitAbility；判断 owner 单位与 subject 的位置，原生能力标签可过滤兵种 |
| 改良、建筑 | 使用相应实体挂载表，再筛目标集合；普通改良相邻仍先用 Improvement_Adjacencies |

具体 CollectionType、EffectType、参数要从当前快照/官方数据核实。不要因为对象“在地块上”就假设所有效果都支持同一集合。

## 拥有者与重复叠加

- ATTACH 后，内层 owner 变为选中的来源对象。若该来源属于外国玩家，内层 `COLLECTION_PLAYER_*` 会跟随来源拥有者；不能把它当成最初特质的玩家。
- 需要统计外国来源时，可用全体目标集合，并在 subject 明确限制受益文明/领袖。多个同文明玩家存在时，逐玩家重复创建同一全局来源链会翻倍；可用单一 GameModifiers 入口，或设计具有明确玩家身份约束的链。
- “来源拥有者满足条件”和“受益目标拥有者满足条件”是两回事。为来源写 owner 条件，不能代替目标玩家筛选。
- 动态范围链通常 `RunOnce=false`、`NewOnly=false`、`Permanent=false`。不要套永久奖励模板；也不要设置阻止不同来源累加的 stack limit。
- 目标集合成员数量与定义条目数量不同。避免为了少写几条定义而全地图重复铺大量无关实例，能从来源类型提前筛选就提前筛选。

## 类型替代、离群与生命周期

区域替代要覆盖 DistrictReplaces 链。可以在晚于实体定义的自定义 SQL 中扩展条件集，不必在 Lua 每回合重建映射。动态 SQL 通过 extension 通道写入，Modifier 本体仍保留在 .CIV，避免同主键双写。

“不与任何区域相邻”可将各区域类型的 `REQUIREMENT_PLOT_ADJACENT_DISTRICT_TYPE_MATCHES` 设 Inverse，再放入 ALL 条件集；明确 MinRange/MaxRange、MustBeFunctioning，并按游戏实际表补充所有类型。替代类型匹配是布尔 ANY 关系，不因同一对象同时匹配多个类别而重复发效果。

劫掠、修复、建造、捕获、拆除及读档是原生生命周期验收项。旧 ATTACH 文档中的失效报告未在该页附完整复现环境，不能据此断言所有挂载都失效，也不能因为 SQL 通过就声称恢复行为正常。只有具体目标链复现问题后，才针对该链补最小处理，不先用 Property 重写全部效果。

## 验证

1. 从实际生成的 SQL 检查入口、ModifierId、RequirementSetId、owner/subject 每一层、未被其他入口重复直挂的内层。
2. 放置 0/1/2 个来源，距离 1/2/3，验证精确范围及线性叠加；包括外国来源、第二个同文明玩家、不同城市和替代对象。
3. 切换领土/对象拥有者，撤去来源；确认没有由 Permanent、RunOnce、NewOnly 或 stack limit 留下旧效果。
4. 单独实机测试劫掠修复、未完工对象、读档；数据库和关系模型测试不能代替引擎生命周期。

依据：官方 `Base/Assets/Gameplay/Data/Modifiers.xml` 的 ATTACH/Collection 定义；纳斯卡线与伟人距离条件（见 [通用技巧](../../modifier-techniques.md)）；用户确认的对象逐份挂载设计。2026-09-28 回流，原生实机表现须针对具体链记录。
