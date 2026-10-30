> 受众：想做文明6 Mod 的人（含让 AI 代做的用户） ｜ 何时读：第一次接触本工具 ｜ 适用版本：ModTools 5.4 ｜ 更新：2026-10-29

# ModTools 5.4

以 **skills + tools 源码** 分享的文明6 Mod 制作工具集：用 `.CIV` 工程文件保存编辑状态，一键生成 SQL/XML/Icons/ArtDef/XLP/Textures 到 ModBuddy 工程目录；同时提供 AI 生成 `.CIV` 的 modgen 工具链与内置「能力实现搜索」。

## 三个入口

| 入口 | 适合 | 开始方式 |
|---|---|---|
| **AI** | 让 AI 生成/校验/合并 `.CIV` 条目、回答「某效果怎么实现」 | 读 [AGENTS.md](AGENTS.md)，再按任务读 [skills/RULES.md](skills/RULES.md) 与 [skills/WORKFLOW.md](skills/WORKFLOW.md) |
| **CLI（modgen）** | 无 GUI 的脚本与自动化；纯标准库 | `python -m modgen.cli new-project 工程.CIV --name 中文名 --prefix SIQI --infix 1`；命令契约 [modgen/AGENTS.md](modgen/AGENTS.md) |
| **GUI（PyQt6，可选）** | 可视化编辑、一键生成、能力搜索、截图观察 | 直接双击 `ModTools5.4.py`（首次缺环境会弹窗引导自动初始化）；或 `python tools/setup_env.py` 后 `.venv\Scripts\python ModTools5.4.py` |

三条路径共用同一份工程与生成引擎；AI 也可经 [AI 控制接口](docs/reference/ai-control-api.md)（**22 个动作**，localhost HTTP）驱动 GUI 的一键按钮。

## 获取

克隆本仓库，或获取完整源码分享目录（skills、tools、文档同源更新）。**不发布内置 EXE、预制 ZIP，也不需要 PyInstaller**。新设备初始化见 [docs/user/install.md](docs/user/install.md)；新 Mod 的工作文件放 `workspace/scratch/`。

## 截图

![ModTools 5.4 界面封面](ModTools_5_4/resources/app_cover.png)

主窗口 **3 页**（主页 / 工作区 / 设置），**小工具是独立窗口**（知识查询 / 文本搜索 / Modifiers 搜索），可与主窗口并排。各页与工作区细节见 [界面导览](docs/user/gui-guide.md)；截图可用 `python tools/make_screenshots.py` 重新生成。

## 文档地图

| 想做的事 | 先读 |
|---|---|
| 5 分钟做出第一个工程 | [docs/user/quickstart.md](docs/user/quickstart.md) |
| 从零完整教程（GUI / AI 两条路径） | [docs/user/tutorial.md](docs/user/tutorial.md) |
| 新设备 / 换环境初始化 | [docs/user/install.md](docs/user/install.md) |
| 界面与各工作区说明 | [docs/user/gui-guide.md](docs/user/gui-guide.md) |
| 把这段提示词交给 AI | [docs/user/ai-prompt.md](docs/user/ai-prompt.md) |
| 常见问题 | [docs/user/faq.md](docs/user/faq.md) |
| 改工具（架构 / 路线图 / 约定 / ADR） | [docs/dev/architecture.md](docs/dev/architecture.md) |
| AI 控制接口协议、纹理格式 | [docs/reference/](docs/reference/) |
| 分享与第三方来源 | [docs/meta/](docs/meta/) |

完整文档索引与元信息规范见 [docs/README.md](docs/README.md)。

## 分享与许可

维护者导出源码分享目录：`python tools/share_source.py --check`，再 `python tools/share_source.py --out shares/<新目录>`。只复制已跟踪文件，生成 `SOURCE_MANIFEST.json` 记录基准提交与逐文件 SHA-256；约定见 [分享与维护约定](docs/meta/source-sharing.md)。第三方来源、作者署名与分发边界见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)；本工具自身代码为 MIT（[LICENSE](LICENSE)）。
