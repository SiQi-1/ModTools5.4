# 可选：ModTools 接入与分层验收

本页只适用于选择 ModTools 的工程。独立分享包先读 [SDK 工程接入](standalone-integration.md)，不依赖本页命令。

以下命令在 ModTools 根目录运行；`$civ`、`$designDir`、`$projectDir`、`$skillDir` 等均由调用者设置为真实路径。使用其他版本先查当前 `--help`、schema 和命令契约。

## 保存源文件

设计源、引用素材、PNG 与尺寸清单放在 Mod 的持久源码/工作目录中。不要把 `.CIV` 指向即将清理的临时截图，或指向 ModBuddy 的生成副本。用户已有源路径可以保留；命名为 `modgen_work` 的目录也可能承载正式来源，不能整体当缓存删除。

示意结构：

```text
MyMod.CIV
MyMod.extensions/UI/MyPanel.xml + MyPanel.lua
ui-design/index.html + styles/assets
ui-design/textures/texture_manifest.json + UI_MYMOD_*.png
verification/                 # 日志、截图、报告
ModBuddy/                    # 生成输出，不作正式编辑入口
```

## 注册纹理、文本和 UI

普通原尺寸 UI 纹理使用 ui_textures，而不是实体图标或 ICON_ 图集：

```powershell
python -m modgen.cli texture add "$civ" --name UI_MYMOD_PANEL --source "$designDir/textures/UI_MYMOD_PANEL.png"
python -m modgen.cli texture add "$civ" --name UI_MYMOD_BUTTON --source "$designDir/textures/UI_MYMOD_BUTTON.png" --replace
python -m modgen.cli texture list "$civ"
```

`--replace` 仅用于明确更新已有同名声明。字段形如 `workspace["美术"]["data"]["ui_textures"] = [{"name":"UI_MYMOD_PANEL","path":"绝对源PNG路径"}]`。add 只登记，不立即转换 DDS；宽高和 alpha 在生成时保留，不裁圆、不按图标缩放。

非实体的可本地化文本填 `workspace["文本"]["custom_entries"]`，条目如 `{"tag":"LOC_MYMOD_TITLE","text":"标题","group":"界面"}`，不要写独立文本 SQL，也不要借此覆盖生成的实体 LOC。项目 JSON 空值省略或用 null，不写 `""`。

UI XML/Lua 通过扩展通道写入。已有扩展工程不必重建骨架；新工程按当前契约初始化。临时内容文件可以编辑，正式源码由工具写入：

```powershell
python -m modgen.cli extension init "$civ" --ui
python -m modgen.cli extension write "$civ" --path UI/MyPanel.xml --role ui --feature panel --content-file "$designDir/MyPanel.xml"
python -m modgen.cli extension write "$civ" --path UI/MyPanel.lua --role ui --feature panel --content-file "$designDir/MyPanel.lua"
python -m modgen.cli extension check "$civ" --json
```

`extension init --ui` 会创建默认入口及 Core；只在需要骨架时运行，并检查是否还留有不用的默认入口。XML 根为 Context，同名 XML/Lua 配对、feature/依赖一致；UI 动作只引用 XML，两文件均进入 Content。纯 Lua helper 用 import。使用当前工具定义的依赖 ID，不根据文件名猜 ID。

## 生成至项目

```powershell
python -m modgen.cli validate "$civ"
python -m modgen.cli project-check "$civ" --json
# 仅新建/未绑定工程或用户要求改绑时使用：
python -m modgen.cli civ6proj "$civ" --out "$projectDir" --update-civ
python -m modgen.cli build "$civ" --overwrite all --json
```

已有工程沿用当前 civ6proj_path，不盲目再创建/改绑。`--overwrite all` 才能替换旧 DDS、TEX 和扩展输出；默认 none 可能使修改源图后仍看到旧皮肤。

链路应为：

```text
PNG 源 → .CIV ui_textures → IMG/PNG + Textures/DDS,TEX
                                ↓
                         XLP EntryID/ObjectName → Art.xml UITexture 库
扩展 XML/Lua 源 → .civ6proj Content + UI XML 入口动作
```

IMG/Textures 通常不在 `.civ6proj` Content/Folder Include 中，这是工具的正常约定。SDK targets 通过 XLP/pantry 处理美术，不要为通过自己编写的检查把全部 DDS 强塞入 Content。

```powershell
python "$skillDir/scripts/verify-textures.py" --manifest "$designDir/textures/texture_manifest.json" --png-dir "$designDir/textures" --project "$projectDir"
```

随附脚本逐张检查尺寸、TEX 名称/DDS 引用、UITexture XLP 条目和对应 Art.xml 库、导出 PNG/DDS 的 alpha 与黑白底可见像素。默认容差为 0，适合当前非压缩 RGBA 通道；确实使用有损格式时才显式指定 `--tolerance`（0～255 的最大单通道差），并报告选定值。不要用大容差掩盖倒置/错帧。

透明度为 0 的像素可能在转换时清空 RGB，所以不应要求原始 RGBA 字节相同；alpha 和黑白背景合成结果才反映可见一致性。非压缩 DDS 的细小原始 RGB 差异不要笼统叫“压缩误差”。

该脚本不替代 project-check、全部 XML 资源引用检查、Lua 编译或游戏验收。额外核对 UI 中每个新 Texture 与清单一致、LOC 已声明、扩展源与输出一致、UI 动作及依赖没有重复。XML 能解析只证明语法正确，不证明 ForgeUI 属性存在。

## 可选：官方纹理 Cooker

当任务包含引擎资源可用性验证且 SDK 已就绪，可仅 cook 目标 XLP，无需生成 modinfo 或部署到 Mods：

```powershell
& "$cookerExe" --absolute_paths --no_mt --mode XLP --platform Windows --pantry "$projectDir" --pantry "$basePantry" --stewpot "$cookOut" --config "$cookerConfig" "$projectDir/XLPs/MyTextures.xlp"
```

路径从本机 SDK 配置、项目 Art.xml 依赖和 `Civ6.targets` 查找，不写死本案例盘符。现有 XLP 如果引用原版 alias，还需要对应 SDK Assets pantry；缺少依赖可能报 UIErrorTexture、缺 Entry 或 BLP HAS MISSING ENTRIES。不要删除合法的原版条目来绕过错误。

检查退出码、日志中的成功标志、缺失资源/条目错误和实际输出文件，**仅退出 0 或出现 BLP 不足以判定成功**。平台只验证用户目标；MacOS 可另行 cook，不必所有任务都双平台。旧 Cooker 出现路径编码问题时，可复制必要输入到独立短 ASCII 临时目录，保留 TEX→DDS 相对结构；不要修改用户正式素材路径来迎合测试目录。

## 验收证据

| 层次 | 应验证 | 不能据此证明 |
|---|---|---|
| HTML | 实际截图、所有页面、状态和模拟交互、纹理尺寸/alpha | 游戏原生字体、实际点击层级 |
| XML/Lua | XML 解析、真实控件/API、Lua 语法、状态模拟、协议参数、重复打开/关闭 | 引擎渲染或真实 GP 结果 |
| CIV/导出 | validate/project-check、引用链、源/输出一致性 | Cooker 或游戏已通过 |
| Cooker | 资源依赖、输出、日志无缺失条目 | 游戏布局、输入/滚动、业务生效 |
| 游戏 | 不同分辨率/UI 缩放、字体、按钮四态、Esc、滚动、领袖门控、存读档、弹窗覆盖、玩法反馈 | 未测试的平台/配置 |

如果用通用 Lua 解释器检查 Civ6 带类型注解脚本，只在临时副本去掉其类型注解，不为迁就解析器重写正式代码。mock 必须能发现状态/请求错误，不能把未知方法全部吞掉然后声称 API 正确。

报告写实际完成层次与剩余项，不报没有定义依据的百分比。用户排除 modinfo 或已安装 Mod 时，导出和纹理 cook 可以独立完成，遵守该范围。

## 本技能随附示例的验证记录

2026-09-24：在 ModTools 5.4、Node.js 24 与 Windows Edge 环境，用原创 CSS 示例实测 3 张纹理的精确导出、重复生成一致性、错误输入拒绝、完整 CIV 导出链、透明/可见像素一致性及 Lua 生命周期模拟；Windows 官方纹理 Cooker 通过。中文 pantry 路径触发编码错误后，使用隔离 ASCII 目录验证成功。HTML 长文本、选择/禁用与确认交互已运行检查。此记录不代表示例已在游戏内验收。
