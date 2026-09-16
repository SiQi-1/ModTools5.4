# basic-info — 基础信息 section（.CIV 的根基）

> dict section，三键包装：`{format, schema_version, data}`。`data` 含 4 组配置，**先写本 section，再写其它 section**（prefix/infix 决定所有 Type 命名）。

## data 键结构（来自样例 32.CIV）

| 组 | 键 | 含义 / 填法 |
|----|----|------------|
| `global_settings` | `prefix` | 前缀（如 `SIQI`），**所有 Type 前缀**，禁自创 |
| | `infix` | 中缀（如 32），工具编号段 |
| | `language` | 语言（`简体中文`），主体只写 zh_Hans_CN |
| `shared_workspace_params` | `prefix` / `infix` | 同 global_settings |
| | `file_name` | 工程文件名（如 `Siqi_Leaders_0032`），生成 SQL/XML 的基名 |
| `project_info` | `civ6proj_path` | 目标 ModBuddy 工程 .civ6proj 绝对路径（工具输出写入点，AGENTS.md §0） |
| | `mod_name`/`teaser`/`description` | 创意工坊展示文本（description 可含 `[NEWLINE]`） |
| | `authors`/`thanks` | 作者/鸣谢 |
| | `guid` | 工程 GUID（新建时工具生成；复用工程时保留原值） |
| | `supports_single_player`/`supports_multiplayer`/`supports_hotseat`/`affects_saved_games` | 布尔，`true/false` |
| | `*_raw` | 英文原名（打包名），与中文显示名分离 |
| | `localized_text_data` | 本地化文本（工具管理） |
| `file_info` | `front_end_actions` / `in_game_actions` / `delete_requests` | 工具管理（.modinfo Actions 映射），**不要手改** |

## 出口检查

- [ ] prefix/infix 与用户既有工程一致（查 `D:\文明6mod用文件夹\ModTools5.4\*.CIV` 现有工程惯例）
- [ ] `civ6proj_path` 指向真实存在的 ModBuddy 工程（AGENTS.md §0 路径）
- [ ] file_name 与工程命名一致（如 `Siqi_Leaders_0032`）
