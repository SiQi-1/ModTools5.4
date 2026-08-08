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

## 硬规则（生成/校验的依据）

- **Type 命名**：`{HEAD}_{前缀}_{中缀}{编号:04d}_{简称}`（如 `CIVILIZATION_SIQI_C0035_1`）。
  生成器按简称自动生成，AI 手写 type 会被 validate 警告/报错。
- **必填字段**：条目必须有 `name`（中文名）+ 分类标识（多数分类 `abbr`，总督用 `code`）。
  主表必填字段见 `schemas/entry_schemas.json` 中 `required` 字段；无默认值的必填字段（如单位 `FormationClass`）必须由 AI 填写。
- **LOC**：文本字段存中文，不写 `LOC_` 前缀 tag；导出时自动注册。
- **图片**：一律空 `images: {}`，路径由用户提供，AI 不生成图片数据。
- **图标名**：约定 `ICON_{Type}`，由生成器自动填。
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
