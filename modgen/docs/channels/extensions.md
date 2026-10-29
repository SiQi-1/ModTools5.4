# 项目级扩展通道（extension / custom-file / 加载顺序 / 兼容）

> 受众：处理项目级扩展与自定义文件的 AI/开发者 ｜ 何时读：需要扩展清单、custom-file 写入或判断加载顺序/兼容性时 ｜ 适用版本：ModTools 5.4

> 本文自 [modgen/AGENTS.md](../../AGENTS.md) 拆出；本通道只读此篇，通用硬规则仍以 AGENTS.md 为准。

## 项目级扩展、自定义文件与加载顺序（硬规则）

- **自定义文件**：新任务先启用 extension 清单，SQL/XML/Lua 正文通过 extension write 或 custom-file write / AI project_file_write 存到源码目录，生成时按清单注册并复制到输出。Scripts 用 gameplay；UI XML/Lua 配对，动作只引用 XML；Import 用 import；数据库、文本、图标分别声明 database/text/icons。旧工程未启用时保留按路径分类与输出目录透传。路径越界被拒绝。
- **自定义 SQL 协调**：默认把未被 .CIV 支持的 Gameplay SQL 放入 Core.sql；相同主键不得双写，UPDATE/DELETE 需明确依赖，不得机械替换成 REPLACE。
- **加载顺序**：扩展清单独立编译 MTX_ 动作，按作用域、前后阶段和依赖决定顺序。旧 custom-file 自动动作仍按 (type,id) 合并并保留旧顺序，不能只凭默认 10000 推断加载时机。完整契约见 [项目级扩展](../../../skills/guides/project-extensions.md)。
- **统一检查与生成**：project-check 组合数据、源码/依赖、预览、动作和 SQL 冲突；build 自动配置后检查、生成并保存动作，默认 overwrite=none，all 才覆盖已有输出。build 不调用 ModBuddy Build/Cooker，不部署。
- **兼容**：未启用 extensions 的旧 .CIV 不变。启用后 custom-file write 自动写源码；无动作文件不适用，Lua 库声明 import。CLI 修改备份 .CIV.bak；AI extension 修改自动保存。GUI/CLI/AI 共用 project/extensions.py。

`extension write/import --role ui_replace --lua-context CityPanel` 管理原生 UI 替换：只接受 UI/ 下 Lua 与 in_game，lua_context 为无路径/扩展名的上下文。自动生成 ReplaceUIScript 的 Properties（LuaContext/LuaReplace/LoadOrder，从 20001 起）；文件仍进 Content，无 XML 配对，也不再注册 AddUserInterfaces 或 ImportFiles。GUI 与 CLI 同源生成，AI extension 同名参数为 lua_context。`assets check` 同时检查 LuaReplace 的文件引用。
