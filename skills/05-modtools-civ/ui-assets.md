# UI 美术与文本操作指南

涉及图标、独立UI纹理、按钮背景、精灵表、UI/Lua LOC 时必读。控件布局另读 [控件参考](../04-lua/lua-xml-controls.md)。

HTML/CSS 原型落地另读 [civ6-html-ui 技能](../civ6-html-ui/SKILL.md)，批量渲染/导入/校验入口见 [通用用法](../civ6-html-ui/references/portable-use.md)。

## 通道选择

领袖选人界面的场景型皮肤可采用“皮肤作背景＋透明空白前景”，避免前景控件的顶部间隙影响构图；两槽尺寸、排版与验收见 [领袖美术指南](leader-art.md#选人界面皮肤背景与空白前景)。

制作领袖头像、文明白标、改良灰度图标、区域图标和历史时刻，先读 [模板图像技能](../civ6-art-images/SKILL.md)。`modgen image` 负责 PSD 提取/PNG 配方处理/像素检查；素材构图与语义轮廓必须看图验收。先满足透明度、白色/灰度、对应底板与尺寸规范，再考虑原作还原。原始技能图或立绘不能直接充当成品。

区域的白色透明要求针对输入核心；核心须置于所选 PSD 区域的 Alpha 组下继承渐变、描边与发光。最终核心随模板着色，不能用“提取底板＋平涂白图”代替这个步骤。工具同时保留可编辑 PSD 和 PNG 渲染差异报告。

实体图标随实体生成；非实体小图标使用 UI图标；按钮背景和精灵表使用独立纹理 ui_textures；自定义文本使用 custom_entries。UI XML / Lua 通过 custom-file 写入；相关命令见 [契约](../../modgen/AGENTS.md)。

## UI图标规则（非实体美术资源声明）

给**不属于任何游戏实体**的 UI 元素声明专属图标（替代借 `ICON_YIELD_*` 凑）。写进 `workspace["UI图标"]` 列表：

```jsonc
{
  "icon_name": "ICON_SIQI_WUJIU_NEWS_CITY",   // 必填，须以 ICON_ 开头
  "name_zh": "城建图标",                       // 选填，仅 GUI 显示
  "sizes": [32, 50],                           // 选填，缺省 22/32/38/50/64/80/128/256
  "images": {"icon": {"path": "D:/art/news_city.png"}},  // 必填：工程外的源 PNG
  "alias": null                                // 选填；有别名时出 IconAliases 行，无值省略或 null
}
```

- **图集名自动推导**：`ATLAS_` + `icon_name` 去掉 `ICON_`（`ICON_X_32` 的文件名 → `ATLAS_X` 的 `IconSize=32` 行）；
- **命名空间硬约束**：`icon_name` 不得落进实体内置图标空间（`ICON_<实体类型>_*`，如 `ICON_DISTRICT_NEWS`
  会与 `DISTRICT_NEWS` 撞车）→ `validate` 报 ERROR；
- 源 PNG **必须存在**（工程外路径 / 工程目录相对路径 / 文件名按 `IMG|Images|Art` 搜索）→ 不存在报 ERROR；
  未设源图 = WARNING（该条被跳过）；源图最小边 < `max(sizes)` = WARNING（放大会模糊）；
- **不产出 SQL / Players / PlayerItems / 文本**——它只是美术资源，不是游戏实体；
- 校验：`python -m modgen.cli validate 工程.CIV`（与 GUI 生成前检查同源实现）；
- 单独看产物：`python -m modgen.cli preview 工程.CIV --section UI图标`（直接打印 Icons.xml）；
- 生成完整产物（Icons.xml + `IMG/ICON_X_<size>.png` + `Textures/…dds|.tex`）需 `.civ6proj` 已绑定，
  用 GUI / AI 接口 `generate_all`。


## 自定义 UI / Lua LOC 文本

先按[标题与描述分工](../02-config-files/text.md#15-ui-标题与描述分工)确定显示角色：UI 奖励名、页签与标题默认纯文字，描述中的数值/效果按语义加字体图标；独立 Image 图标另行设计。不要按关键词批量装饰全部 UI LOC。

实体名称、描述等仍填中文并由工具生成 LOC；不属于实体的 UI/Lua 文本可在 `workspace["文本"]["custom_entries"]` 声明：

```json
[{"tag":"LOC_MY_NEWS_TITLE","text":"乌啾的新闻社","group":"新闻界面","source":"news_ui"}]
```

- `tag` 必填，`LOC_` 开头，仅大写字母、数字、下划线；`text` 为非空中文正文。可选 `group` 决定输出注释分组，未填写时省略；`source` 是可选作者标记，工具不解释。
- 使用现有简体中文 `zh_Hans_CN` 输出，追加至标准 `Text/<文件名前缀>_Text_CN.sql`（其他语言设置沿用已有文件后缀规则），SQL/XML 预览均支持。引号/换行自动转义；不要再手写文本 SQL。
- `validate` 检查字段及自定义 LOC 重复；GUI/AI 生成还检查与实体等自动 LOC 的冲突，有错时返回 `custom_text_invalid` 并阻断生成。不要用此通道覆盖实体文本。
- 当前在 .CIV 中编辑，GUI 文本区负责预览；保存/重载保留条目。旧工程没有此字段时行为不变，不新增分节或 schema 版本。

## 独立 UI 纹理（背景 / 按钮 / 精灵表）

无需创建实体或图标，在 `workspace["美术"]["data"]["ui_textures"]` 声明列表：

```json
[{"name": "UI_MY_PANEL", "path": "D:/art/panel.png"}]
```

- GUI：美术页 →「独立 UI 纹理」→ 导入 PNG，可多选；支持改名、换源路径和移除。
- CLI：`texture add` 只登记资源并保存 `.CIV`（自动 `.bak`），不立即生成工程文件：

```powershell
python -m modgen.cli texture add 工程.CIV --name UI_MY_PANEL --source D:/art/panel.png
python -m modgen.cli texture add 工程.CIV --name UI_MY_PANEL --source D:/art/revised.png --replace
python -m modgen.cli texture list 工程.CIV
python -m modgen.cli texture remove 工程.CIV --name UI_MY_PANEL
```

- 名称以 `UI_` 开头，仅英文字母、数字、下划线，不含扩展名；重名比较忽略大小写。CLI 更新同名资源必须显式 `--replace`。
- PNG 必须存在，宽高各 1～8192；CLI / GUI 文件选择器保存绝对路径。手填 `.CIV` 也应使用绝对路径；相对路径按运行目录解析。
- 绑定 `.civ6proj` 后执行 GUI「生成所有文件」或 AI `generate_all`，原尺寸与 alpha 保留，不裁圆、不重采样为图标、不补黑边。
- 重新生成覆盖策略也适用于 DDS/TEX：`overwrite=all` 更新已有纹理，`none` 保留；GUI 覆盖选择中的虚拟纹理计划控制整组输出，不生成计划文件。
- 产物：`IMG/<name>.png`、`Textures/<name>.dds` 和 `.tex`；自动登记到 UITexture XLP 和对应 Art.xml 库。XML 直接 `Texture="UI_MY_PANEL"`，不生成 Icons.xml 图集行或 SQL。
- `validate` 校验名称、重复、源 PNG 和尺寸；GUI/AI 生成同时检查与现有美术输出的名称冲突，有错则整次生成阻断。AI 沿用 `ui_icons_invalid` / `ui_icon_issues` 字段，涵盖图标与独立纹理。
- 移除只删除声明，不删除源图片；后续生成撤下 XLP 登记。旧导出图片可能保留为未引用文件，不承诺物理清理。
- `.CIV` 格式版本与分节数不变，老工程没有 `ui_textures` 时按空列表处理。自定义 UI XML / Lua 仍须走 `custom-file` 通道。
