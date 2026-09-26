# skills + tools 源码分享

本项目从 2026-09-26 起以当前源码为唯一维护入口。skills 提供制作规则和知识，modgen 提供命令行工具，ModTools_5_4 提供共享生成/校验核心和可选 GUI。源码更新后即可使用，不再等待另一份 EXE 或预制 ZIP 更新。

## 使用与更新

- 推荐克隆仓库；更新前保存自己的源码改动，再拉取新提交。Mod 工程集中在忽略的 modgen_work/，不要覆盖正式工程。
- 收到源码分享目录后，从 AGENTS.md 开始。知识与数据命令只需 Python 3.10+；完整生成/预览和 GUI 用 python tools/setup_env.py 安装 PyQt6、Pillow 并配置本机数据库。
- HTML 转 UI 可以单独分享完整 skills/civ6-html-ui/，含 scripts、references、assets 和 LICENSE；不依赖 ModTools 版本。其他模块有共享依赖，应使用完整源码目录。
- 分享目录不含 Git 历史；若需持续开发，使用 Git 克隆。手工更新分享目录时放到新位置，重新初始化个人配置。

## 维护者导出

在完整 Git 工作区使用 Python 和 Git：

~~~powershell
# 新增源码先加入 Git 索引；已跟踪文件的修改无需先提交
git add -- <本次新增源码文件>
python tools/share_source.py --check
python tools/share_source.py --out shares/ModTools-skills-tools-2026-09-26
~~~

--check 仅检查当前 Git 索引中的文件路径及必需源码，错误返回 1。它会拒绝被强行加入索引的 EXE、DLL、安装包、压缩包及其散列侧文件、本机 settings、虚拟环境和构建目录。Git 忽略规则用于日常操作，CI 的同一检查用于兜底。

--out 先做同样检查，然后复制**已跟踪文件在工作目录中的当前内容**，不使用旧发布缓存。新增但未加入 Git 索引的文件不会复制。源文件缺失、越界或是符号链接/目录联接时拒绝导出。仓库内仅允许写入 shares/ 下的新目录；仓库外也须使用新目录，不覆盖旧目录，不删除已有文件。意外 I/O 失败可能留下部分目录；没有完整 SOURCE_MANIFEST.json 的目录不应分享，修复后换新目录导出。

SOURCE_MANIFEST.json 包含基准提交号、导出时是否有本地改动、UTC 时间以及每个分发文件的大小和 SHA-256。修改过的工作区不会冒充该提交的纯净快照，以逐文件散列为内容依据。清单本身不列入自己的散列。

## 包含范围

- skills、modgen 及 schemas、ModTools_5_4 源码/运行数据/资源、可选 GUI 入口。
- 初始化与维护工具、通用测试、开发与使用文档。
- local_text_New.sqlite 参考文本库；它是工具运行数据，不是旧应用安装包。
- LICENSE、THIRD_PARTY_NOTICES.md、licenses/ 和社区整合记录，保留所有已采用来源的署名。

不包含 .git、历史 EXE/ZIP、构建输出、虚拟环境、缓存、日志、Mod 专用工作文件、个人 settings.json。tools/legacy_skill_builders 只分享停用说明，不分发旧维护脚本。工具不会复制未知的根目录文件。

导出在新目录完成后可以直接分享整个文件夹。若传输渠道要求临时压缩，可由发送者在仓库外处理；压缩文件不成为项目依赖或 Git 维护对象。

## 验证与自动检查

~~~powershell
python tools/share_source.py --check
python -m unittest discover -s tests -p test_source_distribution.py -v
python -m modgen.cli skill --check
~~~

source-check.yml 在推送、拉取请求和手动触发时运行检查，并导出源码目录，在该目录用 python -S 运行技能检查与条目生成，确认不依赖原工作区或已安装的 GUI 包。流程不构建/上传 EXE、ZIP，也不发布二进制 Release。

本次从 Git 索引移出的旧 ZIP、散列和开发机配置仍留在原电脑；既有 Git 历史和远端 Release 未重写或删除，因此历史克隆体积不会自动缩小。提交当前清理后，新版本的文件树和后续源码分享均不再包含这些旧文件。
