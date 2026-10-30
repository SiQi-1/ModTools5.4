> 受众：使用中遇到问题的用户 ｜ 何时读：报错、显示异常、生成不完整时 ｜ 适用版本：ModTools 5.4 ｜ 更新：2026-10-29

# 常见问题

## 显示与配置

**Q: 中文大量显示「未知」**
→ 设置页没配文本数据库，或没导入 DLC 文本。

**Q: 点击生成提示「请先导入 .civ6proj」**
→ 基础信息里没有绑定 ModBuddy 工程文件：点 **「新建 .civ6proj」** 由工具直接生成（或选择已有的）。

**Q: 生成时提示文件已存在**
→ 会弹窗让你选择覆盖哪些文件，其余跳过。

**Q: 能力实现搜索搜不到结果**
→ 设置页没配游戏数据库（`DebugGameplay.sqlite`）；中文搜不到时可试英文关键词（如「宣战」→ `WAR`）。

**Q: 颜色配置里颜色全被当成自定义重新定义了**
→ 标准色匹配依赖 `standard_colors.json`，确保文件未被删除。

**Q: 我的文明6装 D 盘，影响使用吗**
→ 不影响。游戏 Cache 永远在 C 盘 `%LOCALAPPDATA%`，跟安装位置无关；配置文件里手动选一次即可。

## 运行环境

**Q: 双击 `ModTools5.4.py` 没反应 / 提示缺少 PyQt6**
→ 新用户首次双击会弹窗询问是否自动初始化，选「是」会创建 `.venv` 并安装 PyQt6/Pillow（需联网，几分钟），完成后自动打开。若没有弹窗（例如 AI/无控制台），先在源码目录运行 `python tools/setup_env.py`。若系统里根本没有 Python，双击 `.py` 不会执行，需先安装 Python 3.10+ 并勾选 “Add python.exe to PATH”。

**Q: 源码版启动报错 / 依赖问题**
→ 确认用 `.venv\Scripts\python` 运行，并已执行 `python tools/setup_env.py`；换镜像重装：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`。

**Q: 双击 .CIV 无反应**
→ 未注册关联，或 Python/源码入口已移动；用 `tools/register_file_association.py --status` 查看，必要时重新注册。

**Q: 生成时提示「未知 EffectType」**
→ 该效果类型不存在：用 `python -m modgen.cli search <效果词>` 查原版现成实现，不要凭记忆写。

## 系统要求

- Windows 10/11；文明6（至少运行过一次，以生成 Cache 中的游戏数据库）
- 源码版需要 Python 3.10+（推荐 3.13）
- **ModBuddy 非必需**：工具可自己生成 `.civ6proj`（基础信息「新建 .civ6proj」/ `modgen civ6proj`）；最终部署需要 `.modinfo`——有 ModBuddy 用构建生成，没有则手写放入游戏 Mods 目录（模板见 [教程第 3 章](tutorial.md)）。