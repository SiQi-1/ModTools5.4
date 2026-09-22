# AI 控制接口（ModTools 5.4）

> 让外部 AI agent（Claude / 脚本 / 任意 HTTP 客户端）**打开并驱动 ModTools GUI**：
> 打开工程、查看状态、一键生成、新建 .civ6proj、一键配置、游戏库导入、能力搜索、截图。
> 与 `modgen` CLI（无头生成/校验 .CIV）互补：modgen 负责"改数据"，本接口负责"驱动 GUI 的一键按钮与导出"。

## 两种使用方式

### 方式一：HTTP 服务器（推荐，AI 全程驻留驱动）

```bash
# 启动 GUI 并同时打开工程 + 启动控制服务（仅监听 127.0.0.1）
python ModTools5.4.py 我的工程.CIV --ai-port 8765

# 带 token（任何请求需带 X-ModTools-Token 头）
python ModTools5.4.py 我的工程.CIV --ai-port 8765 --ai-token <随机串>
```

请求协议：`POST http://127.0.0.1:8765/api`，请求体：

```json
{"action": "<动作名>", "params": {…}, "timeout": 120}
```

响应：

```json
{"ok": true, "result": {…}}
{"ok": false, "error": "错误说明"}
```

健康检查：`GET /health`（返回 `{"ok": true, "service": "modtools-ai-control"}`）。

### 方式二：CLI 一次性执行（--ai-exec）

启动 GUI → 自动打开工程 → 顺序执行动作 → 输出 JSON 结果 → 退出（退出码 0=全部成功，1=有失败，2=参数错误）：

```bash
python ModTools5.4.py 我的工程.CIV --ai-exec '{"action":"civ6proj_create"}' --ai-exec '{"action":"generate_all","params":{"overwrite":"all"}}'
```

- `--ai-exec` 可重复，值也可以是动作数组：`'[{"action":"ping"},{"action":"get_state"}]'`
- `--headless`：无窗口运行（offscreen；**screenshot 无意义**，其余动作正常）
- 结果同时写入 `%LOCALAPPDATA%\ModTools5.4\logs\ai_exec_result.json`（便携模式为 exe 旁 `logs\`；打包版无控制台时从这里读）

## 动作清单（`help` 动作可随时查询最新清单）

| 动作 | 参数 | 说明 |
|---|---|---|
| `ping` | — | 连通性检查 |
| `help` | — | 列出全部动作 |
| `open_project` | `path` | 打开 .CIV 工程 |
| `save_project` | `path?` | 保存工程（省略则存回原路径） |
| `get_state` | — | 工程快照：全局参数、18 分区条目（index/name/type）、必填缺失、**ui_icon_issues**（「UI图标」及独立 UI 纹理的 ERROR/WARNING）、civ6proj 状态、**file_info 文件动作清单 + custom_files 工程目录文件清单**（AI 与 GUI 视角一致） |
| `get_manifest` | — | 将导出的全部文件清单（与一键生成同源；`can_generate=false` 表示尚未绑定 .civ6proj） |
| `generate_all` | `overwrite: "ask"\|"all"\|"none"` | 一键生成全部文件。`ask`=交互弹窗（默认，适合人看）；`all`=全量覆盖并执行删除计划；`none`=跳过已存在文件。**「UI图标」或独立 UI 纹理有 ERROR 时返回 `{"ok": false, "error": "ui_icons_invalid", "issues": [...]}` 且不写入任何文件** |
| `generate_file` | `relative_path`, `overwrite?` | 生成单个文件（相对路径见 `get_manifest.files`；缺省 overwrite 走交互弹窗）。同样受「UI图标」与独立 UI 纹理校验阻断 |
| `civ6proj_create` | `directory?`, `file_name?`, `fields?`, `create_art_xml?` | 新建 ModBuddy 兼容 .civ6proj + 空白 Art.xml 并绑定到当前工程（无需 ModBuddy 新建工程）。默认目录 `文档\Firaxis ModBuddy\Civilization VI\<文件名>\` |
| `quick_config` | — | 一键配置：扫描工程目录，自动追加 UpdateDatabase/UpdateText/UpdateIcons 等文件动作 |
| `import_from_db` | `section`, `type`, `replace?` | 从游戏库导入条目。section=区域/建筑/单位/改良设施/伟人/政策卡；type=原版 Type（如 `DISTRICT_CAMPUS`）；replace=true 时填 Replaces（仅区域/建筑/单位） |
| `project_file_write` | `relative_path`, `content`, `register_action?`, `action_type?` | **自定义文件通道**：写 SQL/XML/Lua 进工程目录；默认自动按路径注册文件动作（Scripts/*.lua→AddGameplayScripts、UI/*.xml+lua→AddUserInterfaces、Import/*.lua→ImportFiles、Data/*.sql|xml→UpdateDatabase、Icons/→UpdateIcons、Text/→UpdateText；`action_type` 显式指定）；一键生成**原样透传** |
| `project_file_read` | `relative_path` | 读取工程目录文件内容（UTF-8 文本） |
| `project_file_list` | — | 列出工程目录全部文件（path/size）+ 已注册文件动作 |
| `project_file_delete` | `relative_path`, `remove_action?` | 删除工程目录文件（默认同时从文件动作移除引用） |
| `add_file_action` | `type`, `files`, `id?`, `load_order?` | 精确注册文件动作（UpdateIcons/UpdateText/UpdateColors 自动同时注册 FrontEnd+InGame） |
| `search` | `keyword`, `category?`, `limit?` | 能力实现搜索（与 GUI 小工具 / `modgen search` 同一 BM25 引擎；category=civilization/leader/trait/district/building/unit/improvement/project/policy/**technology(科技)**/**civic(市政)**/governor/governor_promotion/great_person/unit_ability/unit_promotion） |
| `skill` | `keyword?`, `limit?`, `file?`, `section?`, `plan?` | 章节检索返回 results/count/reading_plan；plan=true 只给必读清单；file 读全文，section 读标题及子节。keyword 或 file 至少一项。与 modgen skill 同一实现。 |
| `check_conflicts` | — | 自定义 SQL × 生成 SQL 冲突检测（主键双写=ERROR / UPDATE 生成表=WARNING；需先 save_project；modgen 源码环境） |
| `screenshot` | `path?` | 主窗口截图存 PNG（AI "看见" GUI；缺省存系统临时目录） |


`generate_all` / `generate_file` 同样校验 `文本.custom_entries`：格式错误、自定义 tag 重复或与自动生成 LOC 冲突，返回 `{"ok": false, "error": "custom_text_invalid", "issues": [...]}`，不写入生成物。当前正文语言为 `zh_Hans_CN`，GUI 文本预览与 SQL/XML 共用此声明。

`generate_all(overwrite="all")` 会覆盖现有 DDS/TEX；`none` 保留现有纹理。交互覆盖列表包含虚拟纹理计划（若已有纹理），勾选它覆盖纹理组；虚拟计划本身不落盘。

## 典型 AI 工作流

```bash
# 1) 启动 GUI + 控制服务（用户在旁可见 GUI 变化）
python ModTools5.4.py 工程.CIV --ai-port 8765

# 2) AI 查看状态（分区条目 / 必填缺失 / civ6proj 绑定）
curl -s -X POST http://127.0.0.1:8765/api -d '{"action":"get_state"}'

# 3) 没绑 .civ6proj → 直接新建（can_generate 变为 true）
curl -s -X POST http://127.0.0.1:8765/api -d '{"action":"civ6proj_create","params":{"file_name":"Siqi_Leaders_0035"}}'

# 4) 生成前先看清单，再从游戏库导入需要的原版数据
curl -s -X POST http://127.0.0.1:8765/api -d '{"action":"get_manifest"}'
curl -s -X POST http://127.0.0.1:8765/api -d '{"action":"import_from_db","params":{"section":"建筑","type":"BUILDING_MONUMENT"}}'

# 6) 确需 Lua/自定义 SQL 时（自定义文件通道：写入 + 自动注册动作 + 原样透传）
curl -s -X POST http://127.0.0.1:8765/api -d '{"action":"project_file_write","params":{"relative_path":"Scripts/My.lua","content":"function Initialize()\nend"}}'
curl -s -X POST http://127.0.0.1:8765/api -d '{"action":"project_file_write","params":{"relative_path":"Data/Extra.sql","content":"INSERT INTO Types VALUES (''TYPE_X'',''KIND_X'');"}}'

# 7) 一键生成全部文件（非交互，全量覆盖；自定义文件原样透传）
curl -s -X POST http://127.0.0.1:8765/api -d '{"action":"generate_all","params":{"overwrite":"all"}}'

# 8) 截图确认 GUI 现状
curl -s -X POST http://127.0.0.1:8765/api -d '{"action":"screenshot","params":{"path":"shot.png"}}'
```

一次性模式（自动化流水线）：

```bash
python ModTools5.4.py 工程.CIV --headless --ai-exec '{"action":"quick_config"}' --ai-exec '{"action":"generate_all","params":{"overwrite":"all"}}'
```

## AI 完整接管流程（一步步完成项目）

```bash
# ① 工程与内容（无头，modgen）
python -m modgen.cli new-project 工程.CIV --name 中文名 --prefix SIQI --infix 35
python -m modgen.cli generate <分类> --name ... --abbr ...          # → merge 进工程
python -m modgen.cli validate 工程.CIV && python -m modgen.cli preview 工程.CIV --dry-run
python -m modgen.cli civ6proj 工程.CIV --update-civ               # 绑定输出目录（ModID 自动生成并回写）
python -m modgen.cli custom-file write 工程.CIV --path Scripts/My.lua --content-file modgen_work/My.lua

# ② GUI 接管（有窗口，AI 驱动 + 用户可见；或 --headless 全自动）
python ModTools5.4.py 工程.CIV --ai-port 8765
#   AI 循环：get_state（分区/条目/必填缺失/文件动作/自定义文件清单）→
#   import_from_db（导入原版数据）→ project_file_write（自定义 SQL/Lua）→
#   quick_config → get_manifest → generate_all(overwrite=all) → screenshot 核对

# ③ 部署（.modinfo 下期工具生成；本期手写模板放入游戏 Mods 目录）
```

## ModID（GUID）说明

- 游戏的 Mod 唯一标识 = `.civ6proj` 里的 `<Guid>`（Build 时原样写入 `.modinfo` 的 `<Mod id>`）；重复会导致游戏把两个 Mod 当成同一个（存档兼容/覆盖冲突）。
- 所有新建入口（GUI「新建 .civ6proj」/ `modgen civ6proj` / AI `civ6proj_create`）在 `.CIV` 基础信息里**没有 guid 时自动生成 UUID v4**（与 ModBuddy 向导同机制，不会重复），并**回写进 .CIV**——之后无论重建多少次工程文件，`<Guid>` 都保持不变（ModID 稳定性）。`.CIV` 里已有 guid 时一律原样沿用。
- `civ6proj_create` 的返回结果含 `"guid"`；`get_state` 的 `project_info.guid` 可随时核对。

## 安全与边界

- 服务**只绑定 127.0.0.1**；`--ai-token` 提供可选鉴权（AI 启动时自定 token，不需回读）。
- 动作在 GUI 主线程执行：若 GUI 处于模态对话框（如交互式 `overwrite:"ask"` 弹窗），请求会阻塞直到超时（默认 120s，可用请求体 `timeout` 调整）——自动化时请用 `all`/`none`。
- 这是给**外部 AI 的驱动接口**，与已移除的应用内置 agent（2026-06-30）无关。
- `import_from_db` / `search` 需要游戏库（DebugGameplay.sqlite，设置页配置或运行过一次游戏）；`search` 中文检索另需文本库。
