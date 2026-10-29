# 资源与发布产物检查（assets / audio / art / workshop check）

> 受众：检查发布产物与资源引用的 AI/开发者 ｜ 何时读：使用 assets check、audio check、art compare、workshop check 或 --cooker-config 时 ｜ 适用版本：ModTools 5.4

> 本文自 [modgen/AGENTS.md](../../AGENTS.md) 拆出；本通道只读此篇，通用硬规则仍以 AGENTS.md 为准。

## 资源与发布产物检查

~~~powershell
python -m modgen.cli assets check MyMod/MyMod.civ6proj --json
python -m modgen.cli audio check MyMod/MyMod.modinfo --json
python -m modgen.cli art compare MyMod/ArtDefs Cooked/ArtDefs --json
python -m modgen.cli workshop check workshop --modinfo MyMod.modinfo --json
~~~

- 四个入口只读、纯标准库，核心共用 project/asset_checks.py。与针对 .CIV 的 project-check 分开，不自动构建或上传。
- assets check：输入 .civ6proj / .modinfo；解析命名空间、内嵌动作 XML 和显式文件引用，检查资源 XML、模板残留、已知 Leader_Matte 槽及 LeaderFallback → XLP → TEX/DDS 链。IMG/Textures 不要求作为源工程 Content；外部 pantry 引用列入未验证项。
- assets check 可选 --cooker-config <Civ6.cfg>：只读加载目标 SDK 的注册表，分别核对 XLP/AST/GEO/TEX 类；校验 ASSET/TEXTURE XLP 的 ObjectName 对应资源是否属于 m_AllowedClasses，以及 AST 模型对应 GEO 是否属于 m_AllowedGeoClasses。ArtDef 与 AST 的 BLPEntryValue 都校验 EntryID。未知配置结构报错；缺配置、未支持实体类型或外部 pantry 对象明确未验证。未检查 FGX/BLP 内部数据及 pantry 优先级，不能将类关系通过等同于解包复原成功。
- audio check：同类工程输入；核对 UpdateAudio → INI → BNK、文件清单与可用 SoundBanksInfo 中的流式 WEM；INI 要求 ASCII 无 BOM，非 CRLF 提示。无 bank 元数据不能证明所有流式媒体完整。
- art compare：两个目录，默认比较 .artdef；可重复 --suffix 选择支持的资源 XML 后缀。忽略缩进/换行/注释和属性顺序，保留属性值、文本与子节点顺序；缺失、_MissingArt 和结构变化报错，并输出差异位置（最多 100 项）。
- workshop check：输入含 workshop.json、content 的 workspace；content 内需唯一 .modinfo，或 --modinfo 明确指定相对路径。检查 GUID、元数据类型、声明文件、动作引用、可选封面 PNG 头和既有条目 ID。dependencies 为 UInt64 整数列表；现有条目允许省略可选元数据。
- --json 报告包含 kind、target、ok、errors、warnings、unverified、checked；art 另有 comparisons。无静态错误退出 0，错误退出 1；警告/未验证不改变退出码。0 不代表 SDK 编译、游戏显示、Wwise 版本、Steam 所有权已经验证。
- 文件引用禁止绝对路径、越界和逃出输入根目录的链接；不修补源文件。Blender、Wwise、Cooker 和工坊上传器仍按各指南独立使用。

来源、版本及许可见 [第三方说明](../../../THIRD_PARTY_NOTICES.md)。
