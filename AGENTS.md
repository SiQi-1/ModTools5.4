# AGENTS.md — 任务路由（唯一 AI 入口）

> 先判断任务属于哪一类，只读该类入口；**不要通读 `docs/` 或 `skills/`**。
> 本仓库 = 可发布的工具源码 + `workspace/`（本机工作区，已忽略、永不提交）。

## 目录地图

| 路径 | 是什么 | 谁维护 |
|---|---|---|
| `docs/` | 人读文档：`user/` 使用、`dev/` 开发、`reference/` 参考、`meta/` 分享与来源 | 贡献者 |
| `skills/` | AI 知识库：规则、流程、路由、参考、可分享技能包 | 贡献者 |
| `modgen/` | CLI：生成/校验 `.CIV`（命令契约在 `modgen/AGENTS.md`） | 贡献者 |
| `ModTools_5_4/` | PyQt6 编辑器与生成引擎源码 | 贡献者 |
| `tests/`、`tools/` | 测试与维护脚本 | 贡献者 |
| `licenses/`、`THIRD_PARTY_NOTICES.md` | 第三方许可与来源 | 贡献者 |
| `workspace/` | 本机 Mod 工程、笔记、构建产物、外部资料（不在 Git 内） | 仅本机 |

## 目的 A：用工具做 Mod、写 `.CIV`、回答实现问题（最常见）

1. 读 [skills/RULES.md](skills/RULES.md) 与 [skills/WORKFLOW.md](skills/WORKFLOW.md)（合计约 14 KB，必读）。
2. 运行 `python -m modgen.cli skill "任务描述" --plan`，只读返回的 **must** 项和建议章节；`--section` 只取需要的节。
3. 涉及命令/字段时读 [modgen/AGENTS.md](modgen/AGENTS.md)（≤8 KB）；专项通道（地标/纹理/头像模板/资源检查等）再读 `modgen/docs/` 下对应单篇。
4. 产出只经 modgen 写入：`generate` → `validate` → `merge` → `project-check` → `preview`。
5. 找不到路由时看 [skills/SKILLS_OUTLINE.md](skills/SKILLS_OUTLINE.md)；资料依据见 [skills/SOURCES.md](skills/SOURCES.md)。

## 目的 B：改工具 / 改知识库 / 改文档

1. [docs/dev/architecture.md](docs/dev/architecture.md) —— 架构、模块地图、关键设计决策。
2. [docs/dev/roadmap.md](docs/dev/roadmap.md) —— 当前 Done/TODO。
3. [ModTools_5_4/CHANGELOG.md](ModTools_5_4/CHANGELOG.md) —— **只读顶部 5 条**，不要通读 260 KB。
4. 改知识库另读 [skills/AGENTS.md](skills/AGENTS.md)；第三方来源与分发边界读 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
5. 已定型的架构决策在 [docs/dev/decisions/](docs/dev/decisions/)；改决策要新增 ADR，不要往架构文档里堆。

## 目的 C：新设备 / 换环境

读 [docs/user/install.md](docs/user/install.md)（一键初始化、手动配置、验证、排障）。

## 红线（完整正文在 skills/RULES.md，此处不复制）

- ModifierType / EffectType / RequirementType / CollectionType 优先复用原版；自建必须同时注册。
- JSON 值禁止空字符串；参数与枚举必须查证；图片路径必须真实存在。
- 主内容不写 Lua / 手写 SQL / XML；自定义内容走扩展通道，工具是唯一写入者。
- 单个 Mod 的工程、脚本、日志、预览与构建产物只进 `workspace/`，不进 Git。

## 变更纪律

- 不新增根目录文档；新文档进 `docs/` 或 `skills/` 对应目录。
- 预算：普通文档 ≤32 KB，`SKILL.md` ≤500 行，`--plan` 必读总量 ≤30 KB；超限就拆。
- 每个事实只写一处；其余位置只放链接。改命令/行为 = 改契约，同步 `modgen/AGENTS.md`、`skills/catalog.json` 与测试。
- 新文档首行写元信息：`> 受众 … ｜ 何时读 … ｜ 适用版本 …`。
- 校验：`python -m modgen.cli skill --check`、`python -m unittest discover -s tests`。
