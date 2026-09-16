# 议程（Agenda）

## 原理

议程在外交界面展示领袖的性格倾向。**自定义议程仅作为文本呈现**——AI 实际行为逻辑（OperationList）编译在游戏 DLL 中，Mod 无法新增。

## 架构

议程的效果通过**独立的 Trait + TraitModifiers** 实现，不与领袖特质共用：

```
Leader → HistoricalAgendas → AgendaType
AgendaType → AgendaTraits → TraitType (TRAIT_AGENDA_xxx)
TraitType → TraitModifiers → 具体 modifier
```

议程 Trait 是纯内部桥接，Name/Description 写 `''`。

## 涉及的表

| 表 | 列 | 写不写 |
|----|-----|--------|
| `Types` | `TRAIT_AGENDA_SQ_L{SHORT}_{N}`, `KIND_TRAIT` | **必写** |
| `Traits` | `TraitType`, `Name`, `Description` | **必写**（Name/Description 填 `''`） |
| `Agendas` | `AgendaType`, `OperationList`, `Name`, `Description` | **必写**（OperationList 填 NULL） |
| `HistoricalAgendas` | `LeaderType`, `AgendaType` | **必写** |
| `AgendaTraits` | `AgendaType`, `TraitType` | **必写** |
| `RandomAgendas` | `AgendaType`, `GameLimit` | 一般不写 |
| `ExclusiveAgendas` | `AgendaOne`, `AgendaTwo` | 一般不写 |
| `AgendaPreferredLeaders` | `AgendaType`, `LeaderType`, `PercentageChance` | 一般不写 |

## 命名

```
TRAIT_AGENDA_SQ_L{SHORT}_{N}
AGENDA_SQ_L{SHORT}_{N}
```

与领袖标识一一对应。如 `LEADER_SQ_L0037_1` → `AGENDA_SQ_L0037_1`。

## INSERT 模板

```sql
-- 议程 Trait（纯内部桥接）
INSERT INTO Types (Type, Kind) VALUES ('TRAIT_AGENDA_SQ_L{SHORT}_{N}', 'KIND_TRAIT');
INSERT INTO Traits (TraitType, Name, Description) VALUES
('TRAIT_AGENDA_SQ_L{SHORT}_{N}', '', '');

-- 议程本体
INSERT INTO Agendas (AgendaType, OperationList, Name, Description) VALUES
('AGENDA_SQ_L{SHORT}_{N}', NULL, 'LOC_AGENDA_SQ_L{SHORT}_{N}_NAME', 'LOC_AGENDA_SQ_L{SHORT}_{N}_DESCRIPTION');

-- 绑定领袖
INSERT INTO HistoricalAgendas (LeaderType, AgendaType) VALUES
('LEADER_SQ_L{SHORT}_{N}', 'AGENDA_SQ_L{SHORT}_{N}');

-- 绑定 Trait
INSERT INTO AgendaTraits (AgendaType, TraitType) VALUES
('AGENDA_SQ_L{SHORT}_{N}', 'TRAIT_AGENDA_SQ_L{SHORT}_{N}');
```

## 效果 Modifier

议程 modifier 挂载在 `TRAIT_AGENDA_SQ_L{SHORT}_{N}` 上，使用 `MODIFIER_PLAYER_DIPLOMACY_SIMPLE_MODIFIER`。

每条 modifier 需写 `ModifierStrings`（`Context='Sample'`），用于外交面板显示简短原因：

```sql
INSERT INTO ModifierStrings (ModifierId, Context, Text) VALUES
('MODIFIER_SQ0037_AGENDA_LIKE_XXX', 'Sample', 'LOC_TOOLTIP_SAMPLE_DIPLOMACY_SQ0037_XXX');
```

Sample 文本格式：简短原因，如"科技发达且民生幸福"、"穷兵黩武压迫他人"，参考官方 `LOC_TOOLTIP_SAMPLE_DIPLOMACY_*`。

## Text 模板

```sql
-- 议程名称和描述
('zh_Hans_CN', 'LOC_AGENDA_SQ_L{SHORT}_{N}_NAME',        '{议程名称}'),
('zh_Hans_CN', 'LOC_AGENDA_SQ_L{SHORT}_{N}_DESCRIPTION', '{喜欢xxx。讨厌xxx。}'),

-- 简短原因（Sample）
('zh_Hans_CN', 'LOC_TOOLTIP_SAMPLE_DIPLOMACY_SQ0037_XXX', '{简短原因}'),
```

Description 格式：先写喜欢的，再写讨厌的，中间用句号分隔。
