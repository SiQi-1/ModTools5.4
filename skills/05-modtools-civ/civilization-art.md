# 文明文化美术配置：Cultures.artdef

适用：新增文明、修改文明城市/建筑外观或单位文化。常见口头名称“Culture.artdef”对应工具实际输出的 `ArtDefs/Cultures.artdef`，文件名使用复数，不加工程前缀。

## 在工具里配置

使用美术页的“文明音乐与文化（Civilizations / Cultures）”：为目标文明勾选需要美术，点击“文化”按钮，分别选择“城市与建筑文化”和“单位文化”。音乐来源是独立设置，不能代替文化选择。

`.CIV` 对应位置是 `workspace.美术.data.civs`，以工具已生成的文明 `type` 为键。每个需要配置的文明填写：

| 字段 | 内容 |
|---|---|
| `need` | `true`，否则该文明的文化选择不会导出 |
| `cultures.Culture` | 城市与建筑文化分组，字符串数组 |
| `cultures.UnitCulture` | 单位文化分组，字符串数组 |
| `music_source` | 独立的原版文明音乐来源；不从它自动推导文化 |

已有工程使用 `modgen.merger.load_civ` / `save_civ` 保存上述状态，先 `validate` 再生成绑定工程；不要直接手写或补丁生成的 ArtDef。只改文化时保留原有音乐、其他美术状态和文明 Type。

文明数据中的 `ethnicity` / `ETHNICITY_*` 不会填充上述 ArtDef 映射。不能以已经填写民族外观、图标、音乐或领袖立绘为由跳过文化配置。

## 选择有效分组

以当前工具的文化选择器和原版参考为准。当前枚举与导出入口分别是：

- `ModTools_5_4/ui/pages/art_workspace.py` 的 `_CULTURE_GROUPS_FALLBACK`、`_CulturePickerDialog`。
- 同文件的 `_build_cultures_artdef_xml`。
- 原版资料在 `ModTools_5_4/From/Base/`、`ModTools_5_4/From/DLC/` 下对应的 `Cultures.artdef`。

按设计风格选一个合适的原版文明作为参考，核对它在不同分组中的成员关系，覆盖需要的城市/建筑时代样式和单位文化。不要把某个项目的固定三组建筑文化套用到所有文明，也不要为了“完整”勾选全部风格。

两个集合的名称和拼写不同。例如 `Culture` 可选 `AncientEarth`、`Mediterranean`、`ModernGlass`，`UnitCulture` 可选 `European`；这只是字段示例，不是通用推荐。`Culture.SoutheastAsian` 与 `UnitCulture.SouthEastAsian` 的大小写也不同。当前导出器会忽略不在选项中的名称，因此只通过 JSON 校验不足以证明已正确导出。

## 生成后检查实际成员关系

按[统一工作流](../WORKFLOW.md)运行 `build --overwrite all`、`project-check`，并以 [assets check](art-cook-validation.md)检查生成工程。

逐个核对目标文明：

1. `ArtDefs/Cultures.artdef` 包含非空的 `Culture` 和 `UnitCulture` 分组；各组选中的文明引用指向目标 Type，不能只检查文件存在。
2. 这些引用指向 `Civilizations.artdef` 的 `Civilization` 集合，目标文明确实存在；合并方式应保留工具生成的追加语义，不能清空其他文明的组成员。
3. `<工程>.Art.xml` 的 `Cultures` consumer 引用 `Cultures.artdef` 和 `Civilizations.artdef`；同时核对本工程使用的 `Units`、`Landmarks` 等 consumer 的文化文件关系。
4. 源 ArtDef 保存在 `ArtDefs/`，由 Art.xml / Cooker 使用；不要为让它出现在项目列表而手工加进 `.civ6proj` 的 Content/Folder/None。

当前静态检查不保证每个新增文明都有文化分组，以上覆盖检查仍需执行。若工程只有机制或 UI 改动、没有新增或重映射文明，则记录无需新增文化映射；不生成空壳文件充当完成。

## 证据与验证边界

本指南依据当前 GUI 配置状态与导出器核对。`.CIV` → 源 ArtDef → Art.xml 的引用验证，与 SDK 编译、游戏内城市及单位外观验收分开记录。文件存在或构建成功不能证明所有时代的实际外观符合设计。
