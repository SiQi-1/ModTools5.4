# modgen —— 文明6 Mod 工程(.CIV) 生成与校验工具

> **本文件是 AI Agent 的必读说明**。使用本目录的工具生成/校验 .CIV 工程前，请先完整阅读。

## 本工具是什么

生成"合规的文明6 Mod 工程条目"（.CIV 工作区结构），而不是直接生成 SQL/XML。
规则来自 ModTools 5.4 编辑器（GUI）——工具生成的条目保证编辑器能打开、能正确导出。

- **不依赖** PyQt6 / GUI，纯标准库，任何环境可直接运行
- **Type 永远由工具生成**，AI 不要手写 Type（详见"硬规则"）
- 中文文本存条目（name/Description 等），LOC tag 由导出约定自动注册，条目里不写 LOC

## 用法

```bash
# 生成一个合规条目（JSON 输出到 stdout）
python -m modgen.cli generate <分类> --name 中文名 --abbr 英文简称 [--prefix 前缀] [--infix 编号] [--desc 描述]

# 校验条目文件或整个工程
python -m modgen.cli validate 工程.CIV [--prefix 前缀] [--infix 编号]
python -m modgen.cli validate --section 分类 --entry entry.json [--prefix 前缀] [--infix 编号]

# 合并条目进工程（同 type 去重，自动备份 .bak）
python -m modgen.cli merge 工程.CIV <分类> --entry entry.json [--prefix 前缀] [--infix 编号]

# 修改器四类生成（EffectType/RequirementType 存在性与参数骨架自动处理）
python -m modgen.cli generate-modifier --effect EFFECT_XXX --collection COLLECTION_XXX --desc 效果描述 [--params '{"Amount":2,"YieldType":"YIELD_PRODUCTION"}']
python -m modgen.cli generate-requirement --type REQUIREMENT_XXX --desc 条件描述 [--params '{"...":...}']
python -m modgen.cli generate-reqset --desc 集合描述 --logic ALL [--requirements '["REQUIREMENT_A"]']
python -m modgen.cli generate-ability --abbr 简称 --name 中文名 [--desc 中文描述]
```

`--prefix`/`--infix` 来自工程"基础信息"（前缀如 SIQI、中缀编号如 35）。

## 推荐工作流（AI 必须遵守）

1. `generate` 生成条目骨架（Type/LOC/默认值/子表结构已就位）
2. 把用户意图填入骨架：必填字段、数值、子表内容（如子表为空需确认是否应填）
3. `validate` 校验（`--entry` 单条目 或 整个工程）
   - ERROR = 硬错误，必须修
   - WARNING = 建议（type 与规则生成值不一致多为语义式命名，需确认）
4. 修正后 `merge` 进工程
5. 切勿跳过 validate 直接 merge——merge 默认校验，不合格会拒绝

## 临时文件约定（必须遵守）

- **所有临时条目文件（entry 等）一律写入 `modgen_work/` 目录**（仓库根下，已 gitignore，绝不提交 git）。
- 不要在任何其他位置留下生成中间文件（工程目录、仓库根、modgen/ 内）。
- `generate` 输出是 stdout——能直接消费就不要落盘；必须落盘时用 `modgen_work/`。
- merge 会在工程旁生成 `.CIV.bak`（自动备份，已 gitignore，下次覆盖）。

## 硬规则（生成/校验的依据）

- **Type 命名**：`{HEAD}_{前缀}_{中缀}{编号:04d}_{简称}`（如 `CIVILIZATION_SIQI_C0035_1`）。
  生成器按简称自动生成，AI 手写 type 会被 validate 警告/报错。
- **必填字段**：条目必须有 `name`（中文名）+ 分类标识（多数分类 `abbr`，总督用 `code`）。
  主表必填字段见 `schemas/entry_schemas.json` 中 `required` 字段；无默认值的必填字段（如单位 `FormationClass`）必须由 AI 填写。
- **LOC**：文本字段存中文，不写 `LOC_` 前缀 tag；导出时自动注册。
- **图片**：项目图标有图片槽（目标 **256×256**，`images.icon` 已预填尺寸骨架，AI 只需填 `path`）；信仰 `has_images=False`（GUI 无图片槽，图标经美术页别名/数据库处理，无需导入图片）；其余分类一律空 `images: {}`，路径由用户提供。
- **图标名**：约定 `ICON_{Type}`，由生成器自动填（如 `ICON_PROJECT_SIQI_P0035_TEST`）。
- **引用**：`bindings` / `trait_bindings` 中的 section/name 必须指向存在的对象。

## 分类说明

| 分类 | Type 前缀 | 标识键 | 备注 |
|---|---|---|---|
| 文明 | CIVILIZATION | abbr | trait_bindings 绑定特色对象 |
| 领袖 | LEADER | abbr | bindings 绑定所属文明等 |
| 区域 | DISTRICT | abbr | 主表 table_data + 子表 |
| 建筑 | BUILDING | abbr | 主表 table_data + 子表 |
| 单位 | UNIT | abbr | FormationClass 必填无默认 |
| 单位晋升 | PROMOTION_CLASS | type | 晋升树，nodes 列表 |
| 改良设施 | IMPROVEMENT | abbr | PlunderType 必填（默认 NO_PLUNDER） |
| 总督 | GOVERNOR | code | 顶层无 type，用 GovernorType |
| 伟人 | GREAT_PERSON_CLASS | (class_data) | 个体在 individuals |
| 政策卡 | POLICY | abbr | |
| 项目 | PROJECT | abbr | |
| 信仰 | BELIEF | abbr | |
| 议程 | AGENDA | (type) | 顶层无 abbr |

## 修改器规则（generate-modifier 等）

- **ModifierId 命名**：`MODIFIER_{前缀}_{项目号:04d}_{描述}`（如 `MODIFIER_SIQI_0035_ADJ_STRENGTH`）；
  Requirement 用 `REQUIREMENT_`、ReqSet 用 `REQSET_`、Ability 用 `ABILITY_{前缀}_{中缀}{编号:04d}_{简称}`。
- **EffectType / RequirementType / CollectionType 必须真实存在**——generator 会校验并拒绝未知类型，
  validate 也会对未知类型报错（参数集合来自 `schemas/modifier_schemas.json`，源自游戏库权威数据）。
- **参数名必须属于该 Effect/Requirement 的参数集合**（多写/拼错报 error，标准参数缺失给 warning）。
- **引用**：`owner_reqset` / `subject_reqset` / `bound_requirements` 必须指向工程内存在的 ReqSet/Requirement。
- 生成的 Modifier 参数骨架 value 为 null，AI 需填入实际值（数值/Type/文本）。
- 注意：`generate-modifier` 产物是"自定义 ModifierType"（modifier_type = modifier_id），
  若要用游戏内置 ModifierType，需另行指定。

## 外部知识库（生成前建议查阅字段语义）

`AI制作Mod/` 目录（本仓库外部）包含完整的文明6 Mod 制作知识：
- `skills/01-core-tables/*.md`：各分类字段语义与坑（生成必读）
- `skills/06-naming.md`：命名规范（与工具规则一致）
- `skills/district-adjacency.md`：相邻加成语义（DistrictType 是归属方，不参与来源描述）
- `skills/07-techniques/`：修改器技巧
- `reference/csv-export/`：EffectType/RequirementType 权威参数表
- `memory/`：历史错误反馈（易错点）

生成时：字段语义不确定 → 查 `01-core-tables`；Modifier 参数不确定 → 查 `reference/csv-export`。

## 重新生成 schema

编辑器字段变化后，需重新提取 schema（需要 PyQt 环境）：

```bash
python modgen/tools/extract_schemas.py
```
