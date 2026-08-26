# AGENT_SETUP.md —— 新设备环境初始化任务书

> 本文件给 **AI agent** 使用：在全新设备上完成 ModTools 5.4 的环境配置。
> 目标：让本机既能**运行编辑器**，也能让 **agent 生成/校验 .CIV**、**查询游戏实现**。
> 全程约 3-5 分钟（取决于网络）。

---

## 0. 开始前确认

| 检查项 | 说明 |
|---|---|
| 解压 | 本 zip 已解压到目标目录（下文以 `<zip根>` 表示） |
| Python | 需要 **3.10+**（3.13 最佳）。未安装：引导用户到 python.org 下载安装，勾选 "Add to PATH" |
| 文明6 | 最好运行过一次（生成 `%LOCALAPPDATA%\...\Cache\DebugGameplay.sqlite`）；没有也不阻断安装 |

## 1. 执行一键初始化（推荐）

在 `<zip根>` 目录运行：

```bash
python tools/setup_env.py          # 全流程：检测 → venv → 依赖 → 数据库 → 验证
python tools/setup_env.py --check  # 只检测，不安装（排障用）
```

脚本会自动：创建 `.venv` → 安装 `requirements.txt` → 探测游戏库/文本库并生成便携 `settings.json` → 导入冒烟 + modgen 冒烟。

## 2. 手动配置（脚本失败/需自定义时）

### 2.1 创建虚拟环境并装依赖

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt   # Windows
# .venv/bin/python -m pip install -r requirements.txt      # macOS/Linux
```

### 2.2 配置数据库（settings.json）

在 `<zip根>` 手动创建 `settings.json`（文本库用 zip 自带文件）：

```json
{
  "game_db_path": "C:/Users/<用户>/AppData/Local/Firaxis Games/Sid Meier's Civilization VI/Cache/DebugGameplay.sqlite",
  "active_text_db_path": "<zip根>/local_text_New.sqlite",
  "text_databases": [
    { "name": "内置中文文本库", "path": "<zip根>/local_text_New.sqlite" }
  ]
}
```

> 游戏库缺失时：编辑/生成/文本功能不受影响，仅"导入原版对象、能力搜索、modgen search"不可用。

### 2.3 验证

```bash
.venv\Scripts\python -c "import PyQt6, PIL; print('OK')"
.venv\Scripts\python -m modgen.cli search 农场     # 应输出命中对象（能力搜索验证）
.venv\Scripts\python -m modgen.cli generate 区域 --name 测试 --abbr T --prefix X --infix 1
```

## 3. 注册 .CIV 双击打开（可选，推荐）

```bash
python tools/register_file_association.py        # 注册
python tools/register_file_association.py --status
```

## 4. 使用指引（给用户/AI 的一句话总结）

- **启动编辑器**：`<zip根>\.venv\Scripts\python ModTools5.4.py`（或双击 `ModTools5.4.exe`，exe 无需 Python）
- **AI 生成 .CIV**：必读 `modgen/AGENTS.md`；工具链 = `modgen generate/validate/merge` + `modgen search`（知识查询）
- **知识查询**：`python -m modgen.cli search <效果词>` 或 GUI 小工具「能力实现搜索」
- **方法论**：判断"某效果有没有现成实现" = `search` 查原版，不要凭记忆断言

## 5. 排障速查

| 现象 | 处理 |
|---|---|
| `python` 不是内部命令 | Python 未装或未加入 PATH，见第 0 节 |
| pip 安装失败（网络/镜像） | 换镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| `import PyQt6` 失败 | venv 未激活或装错解释器：确认用的是 `.venv\Scripts\python` |
| `search 中文` 无结果 | 文本库未配置（settings.json 的 active_text_db_path）；英文关键词不受影响 |
| 双击 .CIV 无反应 | 未注册关联或 exe 缺失；用 `register_file_association.py --status` 查看 |
| 中文显示"未知" | 文本库未配置或未导入 DLC 文本 |

## 6. 目录速览

```
<zip根>/
├─ ModTools5.4.py / ModTools5.4.exe   入口（源码版 / 打包版）
├─ ModTools_5_4/                      完整源码（agent 可读可改）
├─ modgen/                            AI 生成 .CIV 工具 + AGENTS.md
├─ tools/setup_env.py                 一键初始化（本文件配套）
├─ tools/register_file_association.py .CIV 文件关联
├─ local_text_New.sqlite              内置中文文本库
├─ data/                              可覆盖配置（颜色预设/注释模板等）
└─ settings.json                      运行时配置（初始化生成）
```
