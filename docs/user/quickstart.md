> 受众：第一次使用 ModTools 的人 ｜ 何时读：拿到源码后 5 分钟内要做出第一个工程 ｜ 适用版本：ModTools 5.4 ｜ 更新：2026-10-29

# 快速上手（5 步）

完整从零流程（含部署进游戏）见 [完整教程](tutorial.md)；界面与各工作区细节见 [界面导览](gui-guide.md)。

## 0. 环境（一次性）

| 你要做什么 | 需要装什么 | 怎么运行 |
|---|---|---|
| 只做数据 / 知识检索（AI 或命令行） | Python 3.10+（推荐 3.13），标准库即可 | `python -m modgen.cli ...` |
| 完整生成、预览与 GUI | PyQt6 + Pillow | `python tools/setup_env.py`；之后双击 `ModTools5.4.py` 或桌面快捷方式均可（当前 Python 缺 PyQt6 时脚本会自动改用仓库 `.venv`） |

新设备初始化、数据库与排障见 [新设备初始化](install.md)。

## 1. 设置 → 配置文本/游戏数据库（首次必做）

| 数据库 | 选什么 | 作用 |
|---|---|---|
| 文本库 | 源码自带 `local_text_New.sqlite` | 中文显示；可「导入 DLC」追加文本 |
| 游戏库 | `DebugGameplay.sqlite`（`%LOCALAPPDATA%\Firaxis Games\...\Cache\`） | 导入原版对象、修改器搜索、能力实现搜索 |

> 没配文本库 → 中文预览大量「未知」。没配游戏库 → 导入/能力搜索不可用。源码版可运行 `python tools/setup_env.py` 自动探测配置。

## 2. 文件 → 新建工程 → 输入工程名 → 保存为 `.CIV`

## 3. 基础信息 → 选择 `.civ6proj`

指向你的 ModBuddy 工程文件，或点 **「新建 .civ6proj」** 由工具直接生成（无需 ModBuddy）；设置前缀 / 中缀。

## 4. 左侧树选择分类 → 新增/导入对象 → 编辑

必填字段标红 `*`。13 个内容分类见 [功能覆盖](gui-guide.md#功能覆盖)。

## 5. 工程根节点 → 生成所有文件

一键输出 SQL/XML/图标/ArtDef 等到 `.civ6proj` 目录。

## 也可以纯 AI / 命令行建工程

```bash
python -m modgen.cli new-project 示例.CIV --name 示例工程 --prefix SIQI --infix 1
python -m modgen.cli generate 文明 --name 示例文明 --abbr DEMO --prefix SIQI --infix 1
python -m modgen.cli validate 示例.CIV
python -m modgen.cli merge 示例.CIV 文明 --entry workspace/mods/entry_文明.json
python -m modgen.cli civ6proj 示例.CIV --update-civ
```

命令契约以 [modgen/AGENTS.md](../../modgen/AGENTS.md) 为准；把提示词交给 AI 见 [AI 开局提示词](ai-prompt.md)。

## 工程概念：三类文件

| 文件 | 谁创建 | 作用 |
|---|---|---|
| `.CIV` | ModTools / `modgen new-project` | 编辑状态（JSON），**你操作的是它** |
| `.civ6proj` | ModTools 直接生成（或 ModBuddy） | 定位输出目录；生成文件写入它所在目录 |
| `.modinfo` | 构建生成或手写 | 游戏加载 Mod 的依据，放游戏 Mods 目录 |

## 双击 .CIV 直接打开

```powershell
.venv\Scripts\python tools/register_file_association.py
.venv\Scripts\python tools/register_file_association.py --status
```

只写当前用户注册表（`HKCU\Software\Classes`），无需管理员权限；移动源码目录后需重新注册。

## 下一步

- 完整流程与部署：[tutorial.md](tutorial.md)
- 常见问题：[faq.md](faq.md)
