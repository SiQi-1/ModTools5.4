# 仓库内使用与跨 agent 分享

## 独立使用优先

解压后进入 civ6-html-ui 文件夹，先按 [分享包说明](../README.md) 运行三条独立脚本命令；需要进入游戏时读 [SDK 工程接入](standalone-integration.md)。这些步骤不要求 ModTools、.CIV 或固定版本。下方仓库 CLI 为可选接入。

## 入口与维护来源

`skills/civ6-html-ui/` 是仓库内的正式来源，随源码和发布包一起分发。无需个人安装目录、Codex API、插件或会话历史。支持 SKILL.md 的 agent 可直接加载；其他 agent 打开 SKILL.md 后按链接读取相关参考并执行普通命令即可。

从仓库根目录发现入口：

```bash
python -m modgen.cli skill "HTML 转文明6 UI" --plan
python -m modgen.cli skill --file civ6-html-ui/SKILL.md
```

只分享本能力时，复制或打包整个 `civ6-html-ui` 文件夹，保留 SKILL.md、references、scripts、assets 的相对结构。`agents/openai.yaml` 是可选显示元数据，其他平台可忽略；执行逻辑不读取它。不要只分享 SKILL.md 而遗漏脚本/示例，也不要带上生成纹理、浏览器 profile、缓存或原项目美术。

个人 agent 技能目录中的安装副本由本仓库同步，不在两处分别开发。不同 agent 的技能发现目录不同，本包不强制创建 `.codex`、`.claude`、`.cursor` 等配置；根 AGENTS 和现有知识检索提供平台中立的入口。

## 依赖与边界

| 操作 | 依赖 | 是否需要完整 ModTools |
|---|---|---|
| 读技能、编辑 HTML/XML/Lua | 文本编辑能力 | 否 |
| 运行 HTML 纹理导出 | Node.js 22+、本机 Chromium/Chrome/Edge | 否；可直接运行 .cjs |
| 原生按钮尺寸/字体静态检查 | Python 3.10+，目标字体 XML 可选 | 否；check-native-ui.py 只读 |
| PNG/导出链像素校验 | Python 3.10+、Pillow | 否；可直接运行 .py |
| 批量登记 `.CIV` | 当前 ModTools 源码、Python | 是；不需 Qt 或浏览器 |
| 完整工程检查/生成 | ModTools 配置、PyQt6、Pillow | 是 |
| 原生 Cooker/游戏验收 | 对应平台 SDK/游戏环境 | 独立步骤 |

浏览器工具采用 Node 标准 API、参数数组和本地文件 URL，校验脚本采用 pathlib；没有用户盘符和 Codex 私有运行时路径。Windows 隐藏子进程窗口；不会自动加 `--no-sandbox` 绕过 Chromium 限制。已实测 Windows；其他操作系统需提供可执行的 Chromium/Node 并运行示例验收，不能据此宣称 Civ6 SDK 或 ModTools GUI 全流程跨系统可用。

## 仓库 CLI 快速使用

先复制 `assets/starter/` 到 Mod 的设计目录并改名资源/LOC/事件前缀。以下导出命令也可直接跑原始示例；路径相对仓库根目录：

```bash
python -m modgen.cli texture render --html skills/civ6-html-ui/assets/starter/index.html --out modgen_work/ui-demo/textures
python -m modgen.cli texture verify --manifest modgen_work/ui-demo/textures/texture_manifest.json
```

`render` 优先使用 `--node` / `--browser` 指定值，其次 `CIV6_UI_NODE` / `CIV6_UI_BROWSER`，最后查 Node/PATH 浏览器及系统常见安装路径。显式路径无效时直接报错，不静默切换。未安装依赖时按提示配置，不默认下载/安装浏览器。路径有空格时整体加引号。

```bash
python -m modgen.cli texture render --html design/index.html --out design/textures --node "/path/to/node" --browser "/path/to/chromium"
```

确认清单后批量登记到已有 CIV；不是创建新 Mod 的替代命令：

```bash
python -m modgen.cli texture import-manifest MyMod.CIV --manifest design/textures/texture_manifest.json --dry-run
python -m modgen.cli texture import-manifest MyMod.CIV --manifest design/textures/texture_manifest.json
# 更新已有同名资源时显式允许替换：
python -m modgen.cli texture import-manifest MyMod.CIV --manifest design/textures/texture_manifest.json --replace
```

清单是 `{ "UI_MYMOD_PANEL": [640, 400] }`。PNG 默认为清单同目录的 `<name>.png`，可用 `--png-dir` 指定独立目录。工具检查全批名称、大小写重名、PNG 文件头/尺寸和既有声明后一次保存，并只做一次 `.bak` 备份；任何校验失败都不改 CIV。源路径保存为绝对路径，移动完整 Mod 后应重新导入以更新路径。保留未出现在本次清单中的纹理与其他工作区。

`--dry-run` 返回拟新增/替换条目，不创建备份、不写工程；它是可选的审阅工具，不是重复询问用户许可的流程。render/import/verify 成功均输出 JSON，错误返回非零状态；render 失败时不能使用旧清单当作本次成功的凭据。

登记后按 [导入与验证](integration-validation.md) 写 UI 扩展、生成至已绑定项目，再校验完整链：

```bash
python -m modgen.cli texture verify --manifest design/textures/texture_manifest.json --project ModBuddy/MyMod
```

本组命令不生成 modinfo、不部署，也不将 HTML 自动翻译为原生 XML。

## 独立分享包的脚本入口

无需 `python -m modgen.cli` 即可设计、渲染与验证，路径相对技能文件夹：

```bash
node scripts/render-textures.cjs --html assets/starter/index.html --out /path/to/output --browser "/path/to/chromium"
python scripts/verify-textures.py --manifest /path/to/output/texture_manifest.json --png-dir /path/to/output
```

独立包不包含 ModTools 生成器。可按 [SDK 工程接入](standalone-integration.md) 使用已有 ModBuddy/Asset Editor 流程完成资源和 UI 登记；仅需要写入 CIV 时才使用对应版本 ModTools 的实际 CLI。不会自动把 HTML 编译为完整 Mod。

仓库中也可直接运行原生布局检查脚本（字体表路径按目标游戏语言设置）：

```bash
python skills/civ6-html-ui/scripts/check-native-ui.py --manifest design/textures/texture_manifest.json --xml design/NativePanel.xml --font-styles "/path/to/game/Base/Assets/UI/Fonts/Civ6_FontStyles_zh_Hans_CN.xml"
```

开发者回归入口为 `python -m unittest tests.test_html_ui_tools tests.test_civ6_native_ui_validation -v`；默认不启动浏览器。设置 `CIV6_UI_BROWSER_TESTS=1` 后启用真实浏览器和整包复制测试，Node/浏览器路径使用上述环境变量或 PATH。
