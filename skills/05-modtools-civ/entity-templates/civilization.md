# civilization — 文明条目（section「文明」）

> list section。条目键来自样例 32.CIV。内容知识桥接 `01-core-tables/civilization.md` + `02-config-files/configs.md` + `colors.md`。

> ## ⚠️ 高频坑：civilization_description = 文明**正式全称**，不是百科简介
> 三个显示字段的分工（对照原版官方文案，DB LOC 实证）：
> - `civilization_name` = **简称**（中国 / 罗马 / 黑珍珠）
> - `civilization_description` = **正式全称**（中华帝国 / 罗马帝国 / 黑珍珠帝国；无后缀的文明可与 name 相同，如"童话王国"）
> - `civilization_adjective` = 形容词（中国的 / 罗马的 / 黑珍珠的）
> **禁止把百科介绍段落写进 `civilization_description`**——该文本会出现在 DOM 胜利播报、文明图鉴等正式名称语境，写段落=整段百科当国名。反例：53.CIV（把大炎百科段写入了 description）；正例：52.CIV（黑珍珠 → 黑珍珠帝国）。
> `description_suffix` 只是编辑器的尾注选项（帝国/王国/共和国/城邦），不承载正文。

## 条目键（32.CIV 实测）

| 键 | 填法 | 桥接 |
|----|------|------|
| `name` | 中文名（如 璃月） | — |
| `abbr` | 英文缩写（字母/数字/下划线） | `06-naming.md` |
| `type` | `CIVILIZATION_{PREFIX}_{INFIX}{4位}_{ABBR}`（如 `CIVILIZATION_SIQI_0032_LIYUE`） | `06-naming.md` |
| `civilization_name` / `civilization_description` / `civilization_adjective` | 游戏内显示文本（工具生成 LOC_CIVILIZATION_xxx） | `01-core-tables/civilization.md` |
| `description_suffix` | 描述尾注（可选） | — |
| `loc_name` / `loc_description` / `loc_adjective` | 显式 LOC 控制（默认自动生成，一般不动） | `02-config-files/text.md` |
| `level` | `CIVILIZATION_LEVEL_FULL_CIV`（完整文明）；城邦/部落不在此写 | `reference/enums/` |
| `ethnicity` | `ETHNICITY_*`（外观民族） | DB 验证 |
| `city_name_depth` | 城市名池深度（每格几组名） | — |
| `trait_name` / `trait_description` | 文明特质名/描述 → 工具生成 `TRAIT_CIVILIZATION_{TYPE}` 及 LOC | `01-core-tables/civilization.md` |
| `trait_bindings` | 特质挂载（TraitType ↔ 本条目） | AGENTS.md §5 陷阱 12 |
| `icon_image_name` / `images` | 文明图标（用户 PNG 或游戏库） | `02-config-files/icons.md` |
| `city_info` / `citizen_info` | **城市名/公民名池，必须显式给**（不自动继承，AGENTS.md §5 陷阱 2） | `01-core-tables/civilization.md` CityNames |
| `start_bias` | 出生地偏好（`START_BIAS_*`） | DB 验证 |

## 连带必做（不在本条目内）

- **配色**：`data/standard_colors.json` 选主/次色（工具「自定义颜色仅支持十进制 RGB」），对应 `02-config-files/colors.md`
- **Players/PlayerItems**：工具按文明条目自动生成 → 验证时对照 `02-config-files/configs.md`（`PLAYER_COLOR_`/`CIVILIZATION_` 注册）

## 出口检查

- [ ] type 前缀 = 基础信息 prefix；abbr 无中文
- [ ] city_info/citizen_info 已显式填写（非空）
- [ ] 颜色为十进制 RGB 预设（`standard_colors.json` 内）
- [ ] 图标字段非虚构路径；无图时 `images` 留 `{}`
