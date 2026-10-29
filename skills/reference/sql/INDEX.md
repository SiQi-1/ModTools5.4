# 实体表参考索引（reference/sql）

> 仅用于核对生成 SQL 的列含义；主内容由工具生成，禁止手写。每个文件 = 一个实体类型的表结构参考（Types → 主表 → 关联表 → 文本）与字段陷阱；生成器负责列清单与 INSERT 顺序，实体口径以 [实体模板](../entities/INDEX.md) 为准。
> 核对表间先后关系见 [.civ6proj 动作顺序](../project/civ6proj.md)；是否该用原生表由 [规则正文](../../RULES.md) R3 判断。

## 实体索引

| 文件 | 内容 | 关键表（实测） |
|------|------|--------|
| [civilization.md](civilization.md) | 文明 + 城市名 + 市民名 | Civilizations / CityNames / CivilizationCitizenNames / StartBias* |
| [leader.md](leader.md) | 领袖 + LoadingInfo + 绑文明 | Leaders / LeaderTraits / LoadingInfo / Leaders_XP2 |
| [district.md](district.md) | 区域 + 取代/模型来源 | Districts / DistrictReplaces / District_CitizenYieldChanges |
| [building.md](building.md) | 建筑 + Prereq/GreatWork | Buildings / BuildingReplaces / Building_GreatWorks |
| [unit.md](unit.md) | 单位 + UnitAbilities + 晋升 | Units / TypeTags / UnitAbilityModifiers |
| [improvement.md](improvement.md) | 改良设施 | Improvements / Improvement_Adjacencies / Improvement_Valid* |
| [governor.md](governor.md) | 总督 + 晋升 | Governors / GovernorPromotions / GovernorPromotionModifiers |
| [policy.md](policy.md) | 政策卡（含 Lua 专属解锁技巧） | Policies / PolicyModifiers / Policies_XP1 |
| [project.md](project.md) | 项目 | Projects / Project_BuildingCosts / ProjectCompletionModifiers |
| [greatperson.md](greatperson.md) | 伟人（能力型 + 巨作型） | GreatPersonIndividuals / GreatWorkObjectTypes |
| [agenda.md](agenda.md) | 议程 | Agendas / AgendaTraits / HistoricalAgendas |
| [government.md](government.md) | 政体 | Governments / Government_SlotCounts / Governments_XP2 |
| [belief.md](belief.md) | 信仰（万神殿/追随者/强化者/崇拜）| Beliefs / BeliefModifiers / 间接两层挂载链（0014 实测） |

## 通用规则

- 所有 Type 名先按 [枚举查询依据](../../SOURCES.md#类型与枚举)核实类型与来源，再写 INSERT
- 相邻加成（区域/改良共用）见 [相邻加成](../config/district-adjacency.md)
- 实体间公共列：`{实体}Type` 必写、`TraitType` 独立特质（建筑/区域/改良不可复用文明特质）
- 文本 LOC_ 命名格式见 `../reference/config/text.md`
- 主表导出遵循稀疏 INSERT：主键/Type、Name、Description 与实际有值字段保留；可选空值不写成 `NULL`，不同记录按列集合拆分 INSERT。文中完整列模板用于查字段含义，不要求每次导出把整张表铺开。

## 登记纪律

新增/改名本目录文件后，必须同步本 INDEX 与 `../SKILLS_OUTLINE.md`（[规则正文](../../RULES.md) 硬规则）。
