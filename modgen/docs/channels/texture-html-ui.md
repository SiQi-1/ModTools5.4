# HTML UI 纹理通道（texture render / import-manifest / verify）

> 受众：用 HTML 设计稿产出 UI 纹理的 AI/开发者 ｜ 何时读：使用 texture render/import-manifest/verify 或排查其依赖时 ｜ 适用版本：ModTools 5.4

> 本文自 [modgen/AGENTS.md](../../AGENTS.md) 拆出；本通道只读此篇，通用硬规则仍以 AGENTS.md 为准。

## HTML UI 纹理工具

配套可分享技能：[civ6-html-ui](../../../skills/packages/civ6-html-ui/SKILL.md)，完整用法/依赖见 [通用入口](../../../skills/packages/civ6-html-ui/references/portable-use.md)。正式来源随仓库发布，不依赖个人 agent 安装。

```bash
python -m modgen.cli texture render --html design/index.html --out design/textures
python -m modgen.cli texture import-manifest 工程.CIV --manifest design/textures/texture_manifest.json --dry-run
python -m modgen.cli texture import-manifest 工程.CIV --manifest design/textures/texture_manifest.json --replace
python -m modgen.cli texture verify --manifest design/textures/texture_manifest.json --project ModBuddy/MyMod
```

- `render`：本地 HTML 实现 textureSpecs/renderTexture；需 Node.js 22+ 与 Chromium/Chrome/Edge。`--node`/`--browser` 优先于 CIV6_UI_NODE/CIV6_UI_BROWSER，再查 PATH/常见浏览器路径；无 Codex 专用路径。`--replace` 才覆盖既有输出；不修改 CIV。
- `import-manifest`：标准库命令，清单格式 `{ "UI_MYMOD_PANEL": [640,400] }`，PNG 默认与清单同目录，可用 `--png-dir`。全批名称/重复/PNG 头/尺寸和合并结果校验后只保存一次，保留无关纹理与工作区；同名需 `--replace`，`--dry-run` 不写 CIV 或备份。源路径保存为绝对路径，不生成 DDS。
- `verify`：需 Pillow，只读检查源 PNG；加 `--project` 校验 DDS/TEX/UITexture XLP/Art.xml 及 alpha/可见像素。`--png-dir` 可覆盖源目录，`--tolerance` 为 0..255 最大单通道差，默认 0。不能代替 project-check 或实机验证。
- 三命令成功输出 JSON，失败非零退出；均不编译 XML、不自动翻译 HTML、不运行 ModBuddy/Cooker、不生成 modinfo 或部署。
- 现有 `texture add/list/remove` 契约不变；主数据、UI 扩展和完整生成仍分别走现有通道。
