# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **任务路由（先判断目的）**：本文件是**工具优化向**（开发/改进 ModTools、modgen、GUI、测试、打包）。
> 若任务是**实际应用向**（制作文明6 Mod、编写/修改 `.CIV`、回答 Mod 制作问题）→ 请读根目录 `AGENTS.md`（任务分流表）+ `AGENT.md` + `modgen/AGENTS.md`，本文件大部分内容与任务无关。

> **Agent 知识统一在根目录 `AGENT.md`**：涉及文明6 mod 制作知识、编写 `.CIV` 工程文件时，**先读 AGENT.md**（含两大硬规则：ModifierType 优先引用游戏库已有类型；JSON 禁止写 `""`；以及"主内容不写 Lua，自定义 SQL/XML/Lua 仅走自定义文件通道"的边界声明）。

## Project Overview

ModTools 5.4 is a PyQt6-based visual editor for creating Civilization VI mods (Chinese UI). It saves editing state in `.CIV` project files (JSON) and generates SQL/XML/Icons/ArtDef/XLP/Art.xml/Textures output files into a linked `.civ6proj` ModBuddy project directory.

- ~42,500 lines of Python across 36 source files; single largest file is `ui/pages/workspace_page.py` (~9,400 lines).
- Windows-only, Python 3.13 (`.venv/`, gitignored).
- **The AI Agent feature was removed on 2026-06-30** (no-agent branch). Do not add agent/ or chat-panel references; restore with `git checkout agent-dev` if ever needed.

## Commands

```bash
# Run from source
python ModTools5.4.py

# Run unit tests (no game needed; GUI tests run headless via offscreen)
python -m unittest discover -s tests -v

# Regenerate README screenshots (renders the real UI briefly)
python tools/make_screenshots.py

# Build release exe (PowerShell, generates dist/ + release/ + ModTools5.4.zip)
powershell -File build_release.ps1

# Build release exe with a specific Python interpreter
powershell -File build_release.ps1 -PythonExe python

# AI 控制接口（外部 AI 驱动 GUI）
python ModTools5.4.py 工程.CIV --ai-port 8765 [--ai-token X]     # localhost HTTP 服务（协议见 docs/AI_CONTROL_API.md）
python ModTools5.4.py 工程.CIV --headless --ai-exec '<json动作>'  # 一次性执行后退出（结果写 %LOCALAPPDATA%\ModTools5.4\logs\ai_exec_result.json）
```

- Build uses PyInstaller with `--onefile --noconsole` via `build_release.ps1` (CLI args, no spec file needed; a local `ModTools5.4.spec` exists but is gitignored and secondary).
- Only dependencies: PyQt6 + Pillow (see `requirements.txt`). Tests use stdlib `unittest`, no extra deps.
- Tests are run locally only (no CI). `release.yml` builds the exe on GitHub Actions when pushing a `v*` tag.
- Note: git tracks `local_text_New.sqlite` (runtime data); large artifacts (zip/exe/pyc/logs) are gitignored.

## Architecture (verified against source)

```
ModTools5.4.py                  # Entry point: raise SystemExit(launch())
ModTools_5_4/
├── ai/
│   └── control_server.py       # ★ AI 控制接口：动作注册表(ControlContext) + localhost HTTP 服务器(ControlServer, QTimer 桥) + --ai-exec
├── app/
│   ├── application.py          # QApplication bootstrap, window creation (解析 --ai-port/--ai-token/--ai-exec/--headless)
│   ├── config.py               # AppConfig dataclass, load_config() (MODTOOLS54_DEBUG env)
│   ├── logging_setup.py        # Logs to file only (no terminal output)
│   ├── settings_store.py       # Persistent settings via JSON files
│   └── user_paths.py           # Platform-specific default paths
├── application/
│   └── services.py              # Qt-free ProjectService / GenerationService seams
├── project/
│   ├── civ_project.py          # .CIV file model (JSON, schema 0.1.0), CIV_SECTION_ORDER, load/save
│   └── civ6proj_generator.py   # ★ 纯标准库 .civ6proj 生成器（复刻 ModBuddy 向导产物 + 空白 Art.xml；GUI/modgen/AI 三处共用）
├── db/
│   ├── interface.py            # Text DB tag resolution (LOC_xxx lookup)
│   ├── paths.py                # Default game DB path resolution
│   └── text_database.py        # Text DB creation, import (XML/SQL/DLC/modinfo), query
├── artdef_parser.py            # ArtDef XML parsing (From/{Base,DLC}/ scanner, lru_cache)
├── skills_search.py            # ★ 本地技能库检索引擎（仓库根 skills/；GUI/AI 接口与 modgen skill 单一实现）
├── ui/
│   ├── main_window.py          # QMainWindow: menu bar + QStackedWidget (4 pages: 主页/工作区/小工具/设置)
│   ├── theme.py / assets.py    # QSS loader / icon+image resource path helpers
│   ├── font_icons.py           # FontIcons registry loader (data/font_icons_registry.json)
│   ├── font_icon_popup.py      # Right-click icon picker popup for text editors
│   ├── image_ops.py            # Pillow image ops: circle crop (margin+border), grayscale, icon size table
│   ├── psd_summarizer.py       # PSD template summarizer: baked layer PNGs + recipe JSON (psd-tools, optional dep)
│   ├── ui_widget_kit.py        # ★ Reusable template widget system (~5,500 lines):
│   │                           #   TEMPLATE_SPECS + build_template_widget(), image slots, search dialogs
│   ├── responsive.py           # Width-responsive layout: ResponsiveGrid (3→2→1 cols), ResponsiveSplit
│   ├── dialogs/
│   │   └── conflict_file_dialog.py  # Conflict resolution dialog for text imports
│   └── pages/
│       ├── base_page.py        # BasePage ABC for all pages
│       ├── workspace_page.py   # ★ Core workspace (~9,400 lines): project tree, previews, generation engine
│       ├── group_workspace.py  # Category group/section panels + sub-entry editors (~4,400 lines)
│       ├── basic_info_workspace.py  # Prefix/infix, .civ6proj 选择/新建, file manifests
│       ├── modifier_workspace.py    # ★ Modifiers/Requirements/UnitAbilities editor (~7,200 lines)
│       ├── art_workspace.py    # XLP/ArtDef/Icons/Art.xml/Textures/Moments config
│       ├── great_people_editor.py   # Specialized GreatPersonClasses + Individuals editor
│       ├── entity_table_form.py     # ★ Main table + subtable form generation, composite editors (~6,600 lines)
│       ├── tools_page.py       # 小工具 page: 搜索(嵌入子页) + 图片工具 + PSD模板总结
│       ├── search_page.py      # Text search + Modifiers search (embedded as tools-page tab)
│       ├── settings_page.py    # Game DB + text DB configuration
│       └── home_page.py        # Welcome/landing page
├── data/
│   ├── settings.json           # Runtime config (DB paths, active text DB)
│   ├── art_xml_rules.json      # Art.xml mapping rules for ArtConsumer/Library
│   ├── effect_type_parameters.json / effect_comment_templates.json / requirement_comment_templates.json
│   │                           # Modifier Effect/Requirement parameter + comment templates (Chinese)
│   ├── standard_colors.json    # Official standard colors (leader color presets)
│   ├── font_icons_registry.json  # Pre-processed FontIcons name→index/atlas mapping
│   ├── default_blank_art.xml   # Blank Art.xml fallback template
│   └── FontIcons.dds / FontIconsXP1.dds  # Icon atlas images
├── From/Base/, From/DLC/       # Vanilla/expansion artdef reference files (art layer mapping source)
├── resources/
│   ├── styles/base.qss         # Qt stylesheet (box-shadow removed — Qt doesn't support it)
│   ├── icons/                  # App icons
│   └── images/                 # Embedded UI images (incl. citybanner_* city-state flag layers)
├── docs/
│   ├── AI_CONTROL_API.md       # AI 控制接口协议/动作表（外部 AI 驱动 GUI）
│   ├── ROADMAP.md              # Current Done/TODO status (keep in sync)
│   └── TEX_FORMAT.md           # Texture file format reference
└── logs/                       # modtools_5_4.log (git-tracked history; prefer not adding more)
```
根目录文档：`README.md`（使用教程）、`CIV6_MOD_TUTORIAL.md`（从零全流程教程，随包分发）、`AGENT_SETUP.md`（新设备初始化，给 AI agent）、`modgen/AGENTS.md`（AI 生成 .CIV 必读）、`skills/`（本地技能库 260+ 文件，随发布包分发，入口 `skills/AGENTS.md`，检索 `modgen skill`）。

## Tests

- `tests/` uses stdlib `unittest` (no pytest). Run locally: `python -m unittest discover -s tests -v`.
- Tests run without the game database or a display (`test_workspace_smoke.py` / `test_sql_previews.py` set `QT_QPA_PLATFORM=offscreen` themselves).
- `tests/sample_project.py` is the shared demo project fixture: one minimal entry per content section, also used by `tools/make_screenshots.py` (single source of truth).
- When adding/renaming fields in preview builders, update the fixture if the affected section's sample entry is minimal.

## Key Design Decisions

**AI authoring rules (agent 直接写 .CIV 时)**: 见根目录 `AGENT.md`（权威；游戏深度知识在仓库根 `skills/`，`modgen skill` 检索——2026-08-17 内迁自外部工作区，随发布包分发）。两大硬规则：(1) ModifierType 必须优先引用游戏库 DynamicModifiers 已存在的类型，禁止发明新类型（确需新建时才允许，且必须同时写 DynamicModifiers 行）；(2) JSON 值**禁止写 `""`**——空值必须省略字段或写 `null`，`""` 会生成 SQL `''` 字面量导致类型/外键报错（生成器已兜底：空参数行跳过、`None` 输出 `NULL`）。主内容（.CIV 条目）**不写 Lua、不手写 SQL/XML**；确需 Lua/自定义 SQL/XML 时走**自定义文件通道**（`modgen custom-file` / AI 动作 `project_file_write`，规则与分类见 `project/custom_files.py`——GUI 一键配置与 modgen 单一实现）。

**Project files**: `.CIV` files are JSON with a `meta` (format marker + schema version 0.1.0) and `workspace` (section-indexed dict). Sections follow a fixed order (`CIV_SECTION_ORDER`, 17 sections). "Direct workspace" sections (基础信息, 美术, 文本, 修改器) store a dict; all other sections store a list of objects.

**Output model**: All generation is driven by the workspace state and implemented inside `workspace_page.py` (per-section preview builder methods, e.g. `_build_civilization_sql_pair`, `_build_leader_sql_pair`, `_build_promotion_tree_sql_bundle`). Files are output to the linked `.civ6proj` directory. The output tree is built from `CIV_SECTION_ORDER` — each section contributes specific file types (SQL, XML, XLP, artdef, DDS/TEX, etc.). Empty categories produce no files; a delete plan (`file_info.delete_requests`) is honored on generation.

**Required field rules**: Defined in `REQUIRED_MAIN_TABLE_FIELD_RULES` in `entity_table_form.py`. UI labels append `*` for required fields. Generation aborts with a dialog if required fields are missing.

**Text database is mandatory**: Without a configured local text DB (with imported DLC text), all Chinese text previews show "未知" and text generation is incomplete. The tool intentionally does NOT use `DebugLocalization.sqlite` (the game never refreshes it) — see `db/interface.py` docstring.

**Import capability**: "导入" (import from game DB) buttons are only shown for 区域/建筑/单位/单位晋升/改良设施/伟人 (see `group_workspace.py` `needs_import`). Policy import logic exists in `workspace_page.py` but its button is not yet opened. 文明/领袖/总督/项目/信仰/议程 have no import. **AI 控制接口的 `import_from_db` 动作**覆盖 区域/建筑/单位/改良设施/伟人/政策卡（replace 仅前三类），是 GUI 按钮之外的第二入口。

**AI 控制接口**: `ai/control_server.py` 是给**外部 AI 的驱动接口**（localhost HTTP + `--ai-exec` 一次性执行），与 2026-06-30 移除的应用内置 agent 无关。动作在 GUI 主线程执行（HTTP 线程经 QTimer 队列桥接）；`generate_all`/`generate_file` 非交互模式（overwrite=all/none 或布尔）无弹窗并返回结果字典，交互模式（ask/缺省）行为与 GUI 完全一致。`.civ6proj` 生成统一走 `project/civ6proj_generator.py`（GUI 按钮 / modgen `civ6proj` / AI `civ6proj_create` 三处共用）；`.modinfo` 本期不生成（ROADMAP P1）。

**Convention — file naming**: Data/Text/Icons SQL/XML files use `{文件名前缀}_{BaseName}.sql` naming. XLP and ArtDef filenames must NOT add the prefix — they use raw document names (e.g., `{leaderType.lower()}.xlp`, `{工程名}.Art.xml`).

**Convention — logging**: Logs write to `ModTools_5_4/logs/` only. No terminal/stream handler — this avoids I/O interference with the GUI.

**Convention — IMG/Textures**: IMG and Textures directories are intentionally excluded from `.civ6proj` Content/Folder Include definitions.

## Changelog

`ModTools_5_4/CHANGELOG.md` is the authoritative history — every feature change is recorded there with date and tag (newest entry at top). `ModTools_5_4/docs/ROADMAP.md` tracks current Done/TODO status. Both must be updated when making functional changes. Note: entries 2026-06-30 ~ 2026-07-24 were back-filled in 2026-08-02.

## Workflow Rules

**Approval gate**: When the user makes a broad or high-level request (new feature, category editor, subsystem, or anything that spans multiple files), first explore and present a design summary — what tables are involved, what UI structure, what naming conventions, what files to touch — and wait for explicit user approval before writing any code. Do not skip the design step.
