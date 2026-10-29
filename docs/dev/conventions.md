> 受众：贡献者 ｜ 何时读：提交代码/文档前 ｜ 适用版本：ModTools 5.4 ｜ 更新：2026-10-29

# 编码与文档约定

架构见 [architecture.md](architecture.md)；已定型决策见 [decisions/](decisions/)；当前进度见 [roadmap.md](roadmap.md)。

## 变更纪律

- **审批门**：用户提出宽泛/高层需求（新功能、新分类编辑器、子系统、跨多文件改动）时，先探查并给出设计摘要（涉及哪些表、UI 结构、命名、要改哪些文件），等用户明确同意后再写代码。
- 改命令/行为 = 改契约：同步 `modgen/AGENTS.md`、`skills/catalog.json` 与相关测试；知识改动后跑 `python -m modgen.cli skill --check`。
- 制作规则正文只在 `skills/RULES.md`；其他文档只放链接，不复制规则正文。
- 不新增根目录文档；新文档进 `docs/` 或 `skills/` 对应目录。

## 文件命名

- Data / Text / Icons 的 SQL/XML 文件用 `{文件名前缀}_{BaseName}.sql` 命名。
- **XLP 与 ArtDef 文件名禁止加文件名前缀**，使用原始文档名（如 `{leaderType.lower()}.xlp`、`{工程名}.Art.xml`）。

## 日志

- 只写 `ModTools_5_4/logs/`；不加终端/流 handler，避免 I/O 干扰 GUI。
- 日志文件被 git 跟踪（`.gitkeep` 之外尽量不追加新文件）。

## 美术源目录

- IMG 与标准 Cooker 源库（Assets、Geometries、Materials、Textures、Animations、Behaviors、DSGs、EnvironmentLights、FireFX、LightRigs、Lights、ParticleEffects、XLPs、ArtDefs）留在磁盘但**不注册进** `.civ6proj` 的 Content/Folder/None。
- 两个生成器共用 `civ6proj_generator.is_art_source_path`；更新既有工程时清理过期源注册。Civ6.targets 会原样复制 Content；Cooker 通过工程 pantry 解析源资源。保留 `Platforms/.../BLP` 等运行时文件与根 `Art.xml` 注册。

## Git 与工作区边界

- 单个 Mod 的工程、脚本、日志、预览与构建产物只进本机 `workspace/`（已 gitignore），不进 Git。
- 移动被跟踪文件用 `git mv` 保历史；未跟踪文件用普通移动。只读检查用 `git status` / `git ls-files` / grep。
- 不提交可执行文件、压缩包、`shares/`、缓存、`.venv/` 与本机 `settings.json`；`tools/share_source.py --check` 与 CI 兜底。

## 文档纪律

- 每篇文档**首行**写元信息：`> 受众：… ｜ 何时读：… ｜ 适用版本：ModTools 5.4 ｜ 更新：YYYY-MM-DD`；历史文档加 `状态：历史记录`。
- 预算：普通文档 ≤32 KB，`SKILL.md` ≤500 行，`--plan` 必读总量 ≤30 KB；超限就拆。
- 一个事实只写一处，其余位置放链接；引用代码规模/动作数/测试数时写明口径与日期。
- 文档索引与目录清单在 [docs/README.md](../README.md)。

## 测试与验收

```bash
python -m unittest discover -s tests -v      # 主套件（GUI 测试 offscreen）
python -m modgen.cli skill --check           # 知识库结构与检索门禁
python -S tools/share_source.py --check      # 源码分发检查
```

- 改 preview builder 字段时同步 `tests/sample_project.py` fixture；新增/重命名能力时补回归。
- 生成物、构建、部署与游戏内验证是不同层级，报告时必须说明验证到哪一层。
