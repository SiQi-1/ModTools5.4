# AGENT_SETUP.md —— 新设备环境初始化任务书

> 本文件给 **AI agent** 使用：在全新设备上完成 ModTools 5.4 的环境配置。
> 目标：让本机既能**运行编辑器**，也能让 **agent 生成/校验 .CIV**、**查询游戏实现**。
> 全程约 3-5 分钟（取决于网络）。

---

## 0. 开始前确认

| 检查项 | 说明 |
|---|---|
| 源码 | 已克隆仓库或收到完整源码目录（下文以 `<源码根>` 表示）；不需要 EXE/预制 ZIP |
| Python | 需要 **3.10+**（3.13 最佳）。未安装：引导用户到 python.org 下载安装，勾选 "Add to PATH" |
| 文明6 | 最好运行过一次（生成 `%LOCALAPPDATA%\...\Cache\DebugGameplay.sqlite`）；没有也不阻断安装 |
| 外部制作工具（可选） | 做 FGX/模型/贴图时需要 CivNexus6、AssetEditor、Blender；重装系统后按第 7 节重配 |

知识检索、条目生成和资源静态检查可直接用 Python 运行；完整预览/生成和 GUI 再执行下方初始化。源码分享方式见 [分享约定](docs/SOURCE_SHARING.md)。

## 1. 执行一键初始化（完整功能）

在 `<源码根>` 目录运行：

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

在 `<源码根>` 手动创建 `settings.json`（文本库用源码自带文件）：

```json
{
  "game_db_path": "C:/Users/<用户>/AppData/Local/Firaxis Games/Sid Meier's Civilization VI/Cache/DebugGameplay.sqlite",
  "active_text_db_path": "<源码根>/local_text_New.sqlite",
  "text_databases": [
    { "name": "内置中文文本库", "path": "<源码根>/local_text_New.sqlite" }
  ]
}
```

> 游戏库缺失时：编辑/生成/文本功能不受影响，仅"导入原版对象、能力搜索、modgen search"不可用。

### 2.3 验证

```bash
.venv\Scripts\python -c "import PyQt6, PIL; print('OK')"
.venv\Scripts\python -m modgen.cli search 农场     # 应输出命中对象（能力搜索验证）
.venv\Scripts\python -m modgen.cli skill 相邻加成   # 本地技能库检索（源码自带 skills/）
.venv\Scripts\python -m modgen.cli generate 区域 --name 测试 --abbr T --prefix X --infix 1
.venv\Scripts\python -m modgen.cli new-project _smoke.CIV --prefix X --infix 1   # 工程骨架（验证后删除 _smoke.CIV）
.venv\Scripts\python -m modgen.cli civ6proj _smoke.CIV --update-civ             # .civ6proj 生成（删除 _smoke.CIV 与工程目录）
.venv\Scripts\python -m modgen.cli custom-file write _smoke.CIV --path Scripts/T.lua --content "x"  # 自定义文件通道
```

## 3. 注册 .CIV 双击打开（可选，推荐）

```bash
python tools/register_file_association.py        # 注册
python tools/register_file_association.py --status
```

## 4. 使用指引（给用户/AI 的一句话总结）

- **启动编辑器**：`<源码根>\.venv\Scripts\python ModTools5.4.py`
- **AI 生成 .CIV**：必读 `modgen/AGENTS.md`；工具链 = `modgen new-project`（工程骨架）→ `generate/validate/merge`（含修改器 merge）→ `preview`（无头验证导出）→ `civ6proj --update-civ`（绑定输出目录）→ `custom-file`（自定义 SQL/Lua）→ `search/skill`（知识查询）
- **知识查询**：`modgen search <效果词>`（游戏库实现）/ `skill <关键词>`（本地技能库）/ `query "SELECT ..."`（游戏库只读）/ `loc <LOC_TAG>`，或 GUI 小工具「能力实现搜索」
- **AI 驱动 GUI**：`python ModTools5.4.py 工程.CIV --ai-port 8765`（协议见 `ModTools_5_4/docs/AI_CONTROL_API.md`）；一次性执行 `--ai-exec '<json动作>'`
- **方法论**：判断"某效果有没有现成实现" = `search` 查原版，不要凭记忆断言
- **模型/贴图制作**：先读 `skills/05-modtools-civ/blender-civnexus.md`；本机外部工具链配置（CivNexus6 注册表、AssetEditor DLL、Blender 插件）见第 7 节

## 5. 排障速查

| 现象 | 处理 |
|---|---|
| `python` 不是内部命令 | Python 未装或未加入 PATH，见第 0 节 |
| pip 安装失败（网络/镜像） | 换镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple` |
| `import PyQt6` 失败 | venv 未激活或装错解释器：确认用的是 `.venv\Scripts\python` |
| `search 中文` 无结果 | 文本库未配置（settings.json 的 active_text_db_path）；英文关键词不受影响 |
| 双击 .CIV 无反应 | 未注册关联或 Python/源码入口已移动；用 `register_file_association.py --status` 查看 |
| 中文显示"未知" | 文本库未配置或未导入 DLC 文本 |

## 6. 目录速览

```
<源码根>/
├─ ModTools5.4.py                     可选 GUI 源码入口
├─ ModTools_5_4/                      完整源码（agent 可读可改；docs/AI_CONTROL_API.md 在 ModTools_5_4/docs/）
├─ modgen/                            AI 生成 .CIV 工具 + AGENTS.md
├─ skills/                            本地技能库（modgen skill 检索）
├─ tools/setup_env.py                 一键初始化（本文件配套）
├─ tools/register_file_association.py .CIV 文件关联
├─ local_text_New.sqlite              内置中文文本库
├─ ModTools_5_4/data/                 工具运行资源（颜色预设/注释模板等）
└─ settings.json                      运行时配置（初始化生成）
```

## 7. 可选：外部建模/贴图工具链（重装系统后需重做）

以下**不是** ModTools 运行时依赖；只有做 FGX/GEO 模型、或用 Blender 转换 CN6 时才需要。2026-10-26 在本机实际配置并验证到“插件可加载/注册表可读/DLL 可解析”这一层；AssetEditor 首次启动和实际模型导入仍需人工验收。

### 7.1 CivNexus6 注册表（Blender ↔ CN6 ↔ FGX）

CivNexus6 启动时读取 `HKCU\Software\Firaxis\Tools` 的 `ToolAssetPath`；该目录必须同时有 `Assets` 和 `Resource` 两个子目录（可为空，位置任意）。缺失时 CN6 的 FGX 导入/导出会失败。

```powershell
$dummy = 'D:\文明6mod用文件夹\CivNexus6_1.3.3\CivNexus6\Dummy'   # 本机已有，内含 Assets/Resource
New-Item -Path 'HKCU:\Software\Firaxis\Tools' -Force | Out-Null
Set-ItemProperty -Path 'HKCU:\Software\Firaxis\Tools' -Name 'ToolAssetPath' -Value $dummy -Type String
Get-ItemProperty 'HKCU:\Software\Firaxis\Tools'
```

### 7.2 AssetEditor 的 FbxImporter.dll 名称修正（官方命名错误）

SDK 的 AssetEditor 程序集 `Firaxis.CivTech.Impl.dll` 在 P/Invoke 中引用 `FbxImporter.dll`；但 SDK 实际发布的是 `FbxImporter_Release.dll`（其它工具 DLL 也带 `_Release`），导致 AE 的 FBX/模型导入找不到 DLL。**复制一份**即可，不要覆盖或删除官方原件：

```powershell
$ae = "D:\steam\steamapps\common\Sid Meier's Civilization VI SDK\AssetModTools\AssetEditor"
Copy-Item -LiteralPath (Join-Path $ae 'FbxImporter_Release.dll') -Destination (Join-Path $ae 'FbxImporter.dll') -Force
(Get-FileHash (Join-Path $ae 'FbxImporter_Release.dll')).Hash -eq (Get-FileHash (Join-Path $ae 'FbxImporter.dll')).Hash
```

验证输出应为 `True`。Steam 校验/更新 SDK 可能清掉副本，更新后重做。

### 7.3 Blender 4.5 的 CivNexus6 导入/导出插件

插件来源 S1（Nexus-Buddy-2-Blender-Scripts 的 `Blender-2.8-Addons/`；2.8 版脚本可用于 Blender 3.x/4.x）。复制到用户 legacy addons 目录并启用：

```powershell
$src = '<Nexus-Buddy-2-Blender-Scripts>\Blender-2.8-Addons'
$dst = Join-Path $env:APPDATA 'Blender Foundation\Blender\4.5\scripts\addons'
New-Item -ItemType Directory -Force -Path $dst | Out-Null
Copy-Item "$src\io_import_cn6.py","$src\io_export_cn6.py","$src\io_import_na2.py" $dst -Force
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' -b --python-exit-code 1 --python-expr "import bpy; [bpy.ops.preferences.addon_enable(module=m) for m in ('io_import_cn6','io_export_cn6','io_import_na2')]; bpy.ops.wm.save_userpref(); print('ADDONS_OK')"
```

验证：Blender 的 File > Import 出现 `CivNexus6 (.cn6)` 与 `Civilization Animation (.na2)`，File > Export 出现 `CivNexus6 (.cn6)`；后台可用 `import_shape.cn6` / `export_shape.cn6` / `import_shape.na2` 操作符确认。

### 7.4 本机状态（2026-10-26）

- 已配置：`ToolAssetPath` 指向 `D:\文明6mod用文件夹\CivNexus6_1.3.3\CivNexus6\Dummy`；AE 目录已生成 `FbxImporter.dll` 副本（与 `_Release` 同 SHA-256）；Blender 4.5 三个插件已安装并启用、用户设置已保存。
- 未验证：CivNexus6 GUI 启动、AssetEditor 首次启动/实际 FBX 或模型导入、游戏内模型显示。
- 本机路径仅作示例；换设备时按 7.1–7.3 重新配置。

