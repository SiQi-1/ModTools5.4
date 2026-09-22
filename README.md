# ModTools 5.4

基于 PyQt6 的文明6 Mod 可视化编辑器。用 `.CIV` 工程文件保存编辑状态，一键生成 SQL/XML/Icons/ArtDef/XLP/Textures 等输出文件到 ModBuddy 工程目录。**同时提供 AI 生成 .CIV 的工具链（modgen）**，并内置"能力实现搜索"作为知识获取途径——新设备无需外部知识库。

---

## 两种运行方式（zip 内两者都有）

| | `ModTools5.4.exe` | 源码版（`.py`） |
|---|---|---|
| 适用 | 只想点击即用 | 需要 agent 操作/修改/调试、二次开发 |
| 需要 Python | 否 | 是（3.10+，推荐 3.13） |
| 首次配置 | 无 | 运行一次 `python tools/setup_env.py` 自动完成 |
| AI 工作流 | 仅 GUI | ✅ 源码可读可改 + modgen + 测试全可用 |

> 新设备初始化（推荐让 AI agent 代做）：解压 → `python tools/setup_env.py` → 就绪。
> 详见 `AGENT_SETUP.md`（给 agent 的初始化任务书）。

---

## 快速上手（5 步）

> 📖 **完整从零教程**：`CIV6_MOD_TUTORIAL.md`（创建工程 → GUI/AI 制作全流程 → 部署进游戏，两条路径都有）。

1. **设置 → 配置文本/游戏数据库**：文本库选 `local_text_New.sqlite`（中文显示必需）；游戏库选 `DebugGameplay.sqlite`（导入原版对象、能力搜索必需）。源码版可运行 `python tools/setup_env.py` 自动配置
2. **文件 → 新建工程** → 输入工程名 → 保存为 `.CIV`
3. **基础信息 → 选择 .civ6proj**：指向你的 ModBuddy 工程文件（或点 **「新建 .civ6proj」** 由工具直接生成，无需 ModBuddy），设置前缀/中缀
4. **左侧树选择分类 → 新增/导入对象** → 编辑（必填字段标红 `*`）
5. **工程根节点 → 生成所有文件**：一键输出 SQL/XML/图标/ArtDef 等到 `.civ6proj` 目录

> 也可以直接**双击 .CIV 文件**打开工程（见下文「双击 .CIV 打开」）。

---

## 界面导览

主窗口 3 页（主页 / 工作区 / 设置），**小工具是独立窗口**（窗口菜单或主页按钮打开，可与主窗口并排）：

- **主页**：入口导航
- **工作区**：工程树 + 分类编辑（文明/领袖/区域/建筑/单位/晋升/改良/总督/伟人/政策/项目/信仰/议程）+ 基础信息 + 美术 + 修改器 + 文本
- **设置**：文本库/游戏库配置与导入
- **小工具（独立窗口）**：知识查询（能力实现搜索）+ 文本搜索 + Modifiers 搜索

---

## 知识查询：能力实现搜索

**"某个能力是怎么实现的？"** —— 不用记名字，按效果搜。两种入口查同一份数据：

| 入口 | 适用 |
|------|------|
| `python -m modgen.cli search <效果词>` | **AI / 命令行首选**（`--object` 列出 Modifier 完整实现，照抄用） |
| `python -m modgen.cli skill <关键词>` | **本地技能库章节检索**（仓库根 skills/，随发布包分发：SQL 模板/Lua API/.CIV 工作流/效果技巧；`--plan` 必读清单、`--file --section` 读章节、`--check` 质量检查） |
| 小工具窗口 → 能力实现搜索 | GUI 场景（卡片列表 + 详情树 + 图标/颜色渲染） |

- 中文搜效果/描述（自动效果词映射："宣战"→WAR），英文搜 Type/参数（`WAR`、`YIELD_PRODUCTION`）
- 打开对象后展示 Modifier 完整实现：效果类型 + 参数 + 条件集→条件，ATTACH/GRANT_ABILITY 嵌套自动展开
- **核心用途（做 Mod 时）**：想实现"某个效果"→ 搜效果词 → 找到游戏里现成的对象 → 抄它的实现。例如搜"农场"→ 高棉「大人工湖」→ `EFFECT_ADJUST_PLOT_YIELD`（Amount=2, YIELD_FOOD）——"相邻农场+食物"的现成解法，无需 Lua

---

## AI 生成 .CIV（modgen）

发布包随附 `modgen/`（纯标准库 CLI）：AI 用命令生成/校验/合并 `.CIV` 条目，**保证 GUI 能打开、能正确导出**——Type 由工具生成、EffectType/RequirementType 存在性由工具校验、参数骨架自动给出。**知识查询（"某个效果怎么实现"）由 `modgen search` 与能力实现搜索提供，AI 不需要记忆游戏知识。**

### 开局提示词（把这段给 AI）

```markdown
你是 ModTools 5.4 的 Mod 制作助手。工作目录里有 ModTools5.4.py（源码，可用 .venv 运行）
和 modgen/（AI 生成 .CIV 的工具，纯标准库）。请遵守：

1. 工程文件是 .CIV（JSON），你只通过 modgen 生成/校验/合并条目，绝不手写 JSON 结构。
   必读 modgen/AGENTS.md（硬规则：ModifierType 优先用游戏库已有类型、JSON 禁止 ""、
   主内容不写 Lua，自定义 SQL/XML/Lua 仅走 custom-file 通道）。
2. 生成条目：python -m modgen.cli generate <分类> --name 中文名 --abbr 英文简称
   --prefix <前缀> --infix <编号>；修改器用 generate-modifier / generate-requirement /
   generate-reqset / generate-ability（效果类型由工具校验，错了会拒绝）。
   新工程先建骨架：python -m modgen.cli new-project 工程.CIV --name 中文名
   --prefix <前缀> --infix <编号>（不要拷贝旧工程/手写骨架）。
3. 不知道"某个效果怎么实现"（如被宣战+100%产能、相邻农场+食物）：先运行
   python -m modgen.cli search <效果词> 查游戏里现成的实现（如 search --object 农场 →
   高棉大人工湖 → EFFECT_ADJUST_PLOT_YIELD + REQUIREMENT_*，直接照抄）；
   也可以让用户在 ModTools 小工具的"能力实现搜索"里搜效果词并把结果发给我。
   查表结构/字段用 python -m modgen.cli query "SELECT ..."（游戏库只读），
   查文本用 python -m modgen.cli loc <LOC_TAG>。
   **不要凭记忆断言某个效果没有现成实现**——绝大多数效果都能在游戏里找到对应
   modifier，搜不到再讨论其他方案。
4. 生成后必须 validate（ERROR 必须修、WARNING 需确认），再 merge 进工程
   （修改器条目用 `merge 工程.CIV 修改器 --entry X`）；merge 前可用
   python -m modgen.cli preview 工程.CIV --dry-run 预览将导出的全部文件、
   preview --section <分类> 检查具体 SQL/XML 内容；临时文件一律放 modgen_work/。
5. 主内容（13 分类/修改器/文本）不写 Lua、不手写 SQL/XML；确需 Lua/自定义 SQL/XML 时
   走**自定义文件通道**：python -m modgen.cli custom-file write 工程.CIV --path Scripts/My.lua
   --content-file modgen_work/My.lua（自动注册文件动作；AI 控制接口 project_file_write 同语义）。
   不生成图片资源、不做 3D 模型/动画/特效。
```

### 可用范围

| 能力 | 说明 |
|------|------|
| 工程骨架 | `new-project` 创建 .CIV（基础信息/美术/修改器/文本 结构就位） |
| 13 个内容分类 | 文明/领袖/区域/建筑/单位/单位晋升/改良设施/总督/伟人/政策卡/项目/信仰/议程 |
| 修改器四类 | Modifier / Requirement / RequirementSet / UnitAbility（效果类型存在性 + 参数骨架自动校验；`merge 工程.CIV 修改器` 直接合并） |
| 文本 | 中文文本直接写入条目，LOC tag 由导出自动注册；`loc <LOC_TAG>` 查询文本 |
| 知识查询 | `modgen search`（命令行）/ 能力实现搜索（GUI）——搜效果→找对象→抄实现；**`modgen skill <关键词>` 本地技能库章节检索**（仓库根 skills/，写法/模板/工作流/Lua 知识）；`query "SQL"` 查游戏库表结构/数据 |
| 生成输出 | 合并进 .CIV 后由 GUI 一键生成 SQL/XML/图标/ArtDef/XLP/Textures；`preview` 可无头预览将导出的全部文件（需 PyQt） |
| .civ6proj 工程 | `modgen civ6proj 工程.CIV [--update-civ]` 直接生成 ModBuddy 兼容工程文件 + 空白 Art.xml，**无需 ModBuddy 新建工程** |
| **自定义文件通道** | 自定义 SQL/XML/Lua：`modgen custom-file write/list/remove` 或 AI 控制接口 `project_file_write`——写入工程目录、自动注册文件动作、一键生成原样透传 |
| GUI 一键按钮 | **AI 控制接口**：`python ModTools5.4.py 工程.CIV --ai-port 8765` 后经 HTTP 驱动一键生成/一键配置/导入/截图（协议见 `ModTools_5_4/docs/AI_CONTROL_API.md`）；一次性执行 `--ai-exec '<json动作>'` |

### 边界（务必向用户强调）

| 能力 | 说明 |
|------|------|
| ⚠️ **Lua / 自定义 SQL/XML** | 仅经**自定义文件通道**（`custom-file` / `project_file_write`）工具化写入；主内容（.CIV 条目）不包含 Lua |
| ❌ **图片资源** | 图标/头像/立绘需用户提供，AI 不生成图片 |
| ❌ **模型/动画/特效** | 3D 模型、骨骼动画、粒子特效 |

> **重要方法论——"做不到"之前先搜索**：绝大多数 Mod 效果（包括相邻加成、城市产出调整等）游戏里**都有现成实现**，判断"有没有效果器"的唯一正确方法是用 `modgen search` / 能力实现搜索查原版，**而不是凭记忆断言**。确需 Lua 的情况极少（如自定义界面/事件逻辑），此时才如实告知。

---

## AI 控制接口（驱动 GUI 的一键按钮）

GUI 的很多能力（一键生成、一键配置、导入原版数据、截图观察界面）只有点按钮才能触发。
ModTools 内置 localhost 控制服务，让外部 AI **打开 GUI 并自己操作它**：

```bash
python ModTools5.4.py 工程.CIV --ai-port 8765        # 驻留服务（可选 --ai-token）
python ModTools5.4.py 工程.CIV --headless --ai-exec '{"action":"generate_all","params":{"overwrite":"all"}}'  # 一次性执行
```

- 20 个动作：`get_state` / `get_manifest` / `generate_all` / `generate_file` / `civ6proj_create` /
  `quick_config` / `import_from_db` / `search` / **`skill`（本地技能库）** / **`check_conflicts`（SQL 冲突检测）** / `screenshot` / `open_project` / `save_project` /
  `project_file_write` / `project_file_read` / `project_file_list` / `project_file_delete` / `add_file_action` …
- 协议与示例：`ModTools_5_4/docs/AI_CONTROL_API.md`（POST `http://127.0.0.1:8765/api`，JSON 进出）。

---

## 双击 .CIV 文件直接打开

程序支持启动参数传工程路径（`ModTools5.4.exe "xx.CIV"` 或 `python ModTools5.4.py "xx.CIV"`），注册 Windows 文件关联后即可双击打开：

**方式一：运行注册脚本（推荐）**

```powershell
python tools/register_file_association.py        # 注册
python tools/register_file_association.py --unregister  # 解除
python tools/register_file_association.py --status      # 查看状态
```

只写当前用户注册表（`HKCU\Software\Classes`），无需管理员权限。源码运行时关联到 `python + ModTools5.4.py`；打包 exe 运行时自动关联到 exe 自身。

**方式二：手动注册（.reg）**

把下面内容存为 `civ_assoc.reg`（把 `C:\路径\ModTools5.4.exe` 换成你的实际路径，引号不可省），双击导入：

```
Windows Registry Editor Version 5.00

[HKEY_CURRENT_USER\Software\Classes\.CIV]
@="ModTools5.4.CIV"

[HKEY_CURRENT_USER\Software\Classes\ModTools5.4.CIV\shell\open\command]
@="\"C:\\路径\\ModTools5.4.exe\" \"%1\""
```

> 注册后若资源管理器未立即生效，重启 explorer 或注销重登即可。

---

## 设置页（首次使用）

| 步骤 | 操作 |
|------|------|
| 文本数据库 | 发布包自带 `local_text_New.sqlite`（已含基础游戏中文文本），设置页直接选它即可。如需 DLC 文本，点"导入 DLC"选择游戏 DLC 目录追加导入 |
| 游戏数据库 | 选择 `DebugGameplay.sqlite`（`%LOCALAPPDATA%/Firaxis Games/.../Cache/`），用于导入原版对象、修改器搜索与能力实现搜索 |

> 没配文本库 → 中文预览大量"未知"。没配游戏库 → 导入/能力搜索不可用。

---

## 工程概念

| 文件 | 说明 |
|------|------|
| `.CIV` | ModTools 工程文件（JSON），保存所有编辑状态 |
| `.civ6proj` | ModBuddy 工程文件，ModTools 读取它来确定输出目录和文件结构 |

生成输出时，文件写入 `.civ6proj` 所在目录。

---

## 功能覆盖

| 分类 | 新建 | 导入 | 编辑器 | SQL/XML 预览 | 文件输出 |
|------|:--:|:--:|:--:|:--:|:--:|
| 文明 | ✓ | — | ✓ | ✓ | ✓ |
| 领袖 | ✓ | — | ✓ | ✓ | ✓ |
| 区域 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 建筑 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 单位 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 单位晋升 | ✓ | — | ✓ | ✓ | ✓ |
| 改良设施 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 总督 | ✓ | — | ✓ | ✓ | ✓ |
| 伟人 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 政策卡 | ✓ | — | ✓ | ✓ | ✓ |
| 项目 | ✓ | — | ✓ | ✓ | ✓ |
| 信仰 | ✓ | — | ✓ | ✓ | ✓ |
| 议程 | ✓ | — | ✓ | ✓ | ✓ |
| 美术 | — | — | ✓ | ✓ | ✓ |
| 修改器 | — | — | ✓ | ✓ | ✓ |

> "导入"指从游戏数据库（DebugGameplay.sqlite）导入原版对象。政策卡的导入逻辑已实现，但分组面板导入按钮暂未开放。

---

## 各工作区说明

### 基础信息
设置前缀/中缀（影响所有 Type 命名）、选择 `.civ6proj`、管理文件加载动作（FrontEnd/InGame ActionData）。"刷新配置"扫描工程目录中的自定义 XLP。一键配置快速生成常用文件条目。

### 文明 / 领袖
文明编辑器和领袖编辑器各自独立，支持 Trait 绑定、外交文本表格。
- **领袖颜色配置**：4 套配色（球衣），取色弹窗内置 28 个官方标准色 + 自定义颜色输入。横幅预览实时显示城邦旗帜渲染效果。
- **领袖图片**：前景/背景/外交/选择界面共 6 个图片槽位。

### 区域 / 建筑 / 单位 / 改良设施
复合编辑器，包含主表 + 多个副表（单行/多行）。支持从游戏数据库导入原版对象作为模板。必填字段标红 `*`。

### 单位晋升
独立的晋升树编辑器。两种模式：
- **树形**：卡片拖拽定位（Level 1→4），上下端口连线建立前置关系。支持 2221 / 2212 一键模板。
- **随机**：按 Level 分组列表排列。

晋升树节点自动注册为修改器的 `UnitPromotionModifiers` 所属。

### 总督 / 伟人
总督编辑器含晋升树可视化 + 圆形裁切头像。伟人编辑器含伟人类型、简化单位、伟人个体（激活类/巨作类）。

### 政策卡 / 项目 / 信仰
标准子条目编辑器，含主表和常用副表。

### 议程
复合编辑器：议程主表 + 历史议程（领袖绑定）/ 互斥议程 / 议程外交 Modifier（支持从数据库导入官方 SubjectRequirementSetId 模板）+ AI 偏好列表。

### 美术

美术页新增「独立 UI 纹理」：批量导入背景、按钮、精灵表 PNG，保留原尺寸和透明度，自动输出 IMG / DDS / TEX / XLP。CLI 等价入口：`python -m modgen.cli texture add 工程.CIV --name UI_MY_PANEL --source D:/art/panel.png`，随后「生成所有文件」。使用规则见 [modgen 契约](modgen/AGENTS.md#独立-ui-纹理背景--按钮--精灵表)。
管理 Icons.xml / ArtDef / XLP / Art.xml / Textures 输出。
- 图标预览和别名配置
- 领袖 XLP 独立生成
- Art.xml 工作区规则与原工程配置自动合并
- Moments 历史时刻插画
- 纹理链路：PNG → DDS → TEX → XLP

### 文本
统一预览 Text.sql / Text.xml 输出，包含各分类 Name/Description、修改器预览文本、外交文本等。描述类文本框支持右键插入 `[ICON_XXX]`。

### 修改器
Modifier / RequirementSet / Requirement / UnitAbility 的完整编辑器。
- 支持所属绑定（将修改器挂到任意分类的对象上）
- EffectType / RequirementType 搜索
- 参数表编辑器
- 战斗预览文本自动生成

---

## 常见问题

**Q: 中文大量显示"未知"**
→ 设置页没配文本数据库，或没导入 DLC 文本。

**Q: 点击生成提示"请先导入 .civ6proj"**
→ 基础信息里没有绑定 ModBuddy 工程文件：点 **「新建 .civ6proj」** 由工具直接生成（或选择已有的）。

**Q: 生成时提示文件已存在**
→ 会弹窗让你选择覆盖哪些文件，其余跳过。

**Q: 能力实现搜索搜不到结果**
→ 设置页没配游戏数据库（`DebugGameplay.sqlite`）；中文搜不到时可试试英文关键词（如"宣战"→`WAR`）。

**Q: 源码版启动报错 / 依赖问题**
→ 确认用 `.venv\Scripts\python` 运行，并已执行 `python tools/setup_env.py`；换镜像重装：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`。

**Q: 颜色配置里颜色全被当成自定义重新定义了**
→ 标准色匹配依赖 `standard_colors.json`，确保文件未被删除。

**Q: 双击 exe 毫无反应/没有界面**
→ 打包版无控制台，启动期异常会被静默吞掉。请检查 exe 所在目录（或 `%LOCALAPPDATA%\ModTools5.4\logs`）下的 `crash.log`，按其中报错排查；另外请确认系统为 Windows 10 或更高版本（Qt6 不支持 Win7/8）。

**Q: 我的文明6装D盘，影响使用吗**
→ 不影响。游戏 Cache 永远在 C 盘 `%LOCALAPPDATA%`，跟安装位置无关。配置文件里手动选一次即可。

---

## 系统要求

- Windows 10/11
- 文明6（需要至少运行过一次，以生成 Cache 中的游戏数据库）
- 源码版需要 Python 3.10+（打包版不需要）
- **ModBuddy 非必需**：
  - 工具可以**自己生成 `.civ6proj`**（基础信息「新建 .civ6proj」按钮 / `modgen civ6proj` 命令，生成物与 ModBuddy 向导产物同构，ModBuddy 仍可打开/构建）；
  - 最终部署到游戏需要 `.modinfo`：有 ModBuddy 用它构建生成；没有则**手写 .modinfo 放入游戏 Mods 目录**（教程有模板）。

---

## 素材来源与版权说明

本工具为文明6 Mod 制作提供参考数据与素材，其中部分文件来自游戏本体或 ModBuddy：

- `ModTools_5_4/From/{Base,DLC}/`：官方 ModBuddy 附带的 artdef 参考文件（仅用于解析艺术层条目名称与结构）。
- `ModTools_5_4/data/FontIcons.dds` / `FontIconsXP1.dds`：游戏界面图标图集（用于编辑器内图标插入与预览）。
- `ModTools_5_4/data/text_color_presets.json`：从游戏 `Base/Assets/UI/Civ6_ColorAtlas.xml` 提取的文本颜色预设。
- `local_text_New.sqlite`：由游戏文本（XML/SQL/DLC）导入生成的本地化文本数据库，仅作中文文本解析与预览用途。
- 应用图标与部分图片为基于游戏素材的二次创作。

以上素材仅服务于"为文明6制作 Mod"这一用途，版权归 Firaxis Games / 2K 及其相关方所有。若涉及侵权，请联系移除。本工具自身代码采用 MIT 许可证（见根目录 `LICENSE`）。

### AI 知识工作流

制作任务先读 [规则正文](skills/RULES.md) 与 [统一工作流](skills/WORKFLOW.md)。`python -m modgen.cli skill "任务描述" --plan --json` 返回任务必读资料；规则、指南、参数参考和历史案例分层读取。检索失败时换词并查来源，不能凭记忆补结论。维护知识后运行 `python -m modgen.cli skill --check`。
