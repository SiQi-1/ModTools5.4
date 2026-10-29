# 第三方参考资料与致谢

本项目在完善文明 6 制作知识和工具时参考了下列作者的成果。致谢不改变上游许可，也不将游戏素材、第三方二进制或社区模板自动纳入本项目的 MIT 许可证。

核对日期：2026-09-25；2026-10-26 复核来源治理与分发边界；2026-10-29 登记外置技能 civ6-model-import（仅名单，原件不内置、不随源码分享）与可拉取的外部 MCP 服务器 civ6-mcp（仅记录网址、版本与许可）。已落地社区制作指南、领袖外交表情差分、四类只读检查命令及知识检索路由；具体采用与验收边界见[整合记录](docs/meta/community-integration.md)。指南按来源编号署名；工具代码为本项目独立实现，不含上传器、Blender 插件、音频脚本或模板原件。

## 直接参考来源

2026-09-28 新增共享资源；2026-10-26 用户再次确认：区域、领袖头像及历史时刻 PSD 模板允许作为来源随 `skills/civ6-art-images/assets/templates/` 分发。模板来自用户提供的社区压缩包，作者暂未确认，文件未附具体许可证；保留原文件而不虚构署名或重新标记 MIT。原始名称、文件大小、SHA-256 与分享依据见 [模板清单](skills/packages/civ6-art-images/assets/templates/manifest.json)。原《如何使用.docx》（45,621,258 B）于 2026-10-29 转为 [使用说明](skills/packages/civ6-art-images/assets/templates/moments/usage.md) 与压缩截图，Word 原件不再随仓库分发。

| 编号 | 资料 | 作者 / 署名 | 本轮参考内容 | 许可核对 |
|---|---|---|---|---|
| S1 | [Nexus-Buddy-2-Blender-Scripts](https://github.com/Sukritact/Nexus-Buddy-2-Blender-Scripts) | Sukritact；脚本作者 Deliverator，部分脚本共同署名 Deliverator、Sukritact；仓库派生自 [deliverator23/Civilization-Blender-Scripts](https://github.com/deliverator23/Civilization-Blender-Scripts) | Blender ↔ CN6、NA2 动画导入与 CivNexus6 的职责划分 | 核对的提交未包含 LICENSE/COPYING，三个脚本未发现授权声明；本项目仅引用，不分发这些脚本 |
| S2 | `Civ6_2D纸片领袖模板包.zip` | 千寻瀑（千与千寻瀑；用户提供作者信息） | 纸片领袖资源链、Leader_Matte、环境灯光、颜色与透明度贴图、命名与验收 | 独立压缩包未附许可证；其中通用二进制和模板有其他来源，暂只作为技术参考 |
| S3 | `civ6-audio-pipeline_share.zip` | 千寻瀑（入口署名：千与千寻瀑） | 音频分类、声道与响度处理、Wwise 2015 工作流、Banks.ini / UpdateAudio 注册核验、已弃用打包方案 | 入口声明 MIT，但独立包无 LICENSE 文件；合集 S4 内的音频技能另有 MIT LICENSE。复制时应明确采用哪个包及文件版本，不能混淆 |
| S4 | `civ6-modding-skills.zip`；包内给出的上游：[nuanyuqingfeng/civ6-modding-skills](https://github.com/nuanyuqingfeng/civ6-modding-skills) | 千寻瀑；MIT 版权行原文署名 **千与千寻瀑** | 美术引用链、Cooker 差异分析、制作验证、UI / GP 环境核验、工坊交付流程 | 代码与文档附 MIT；保留[原许可证](licenses/civ6-modding-skills.LICENSE)。随包第三方资料、素材和工具须分别识别出处，不能一概归为作者原创 |
| S5 | `创意工坊上传器-CLI.zip`；[Civ6WorkshopUploader](https://github.com/Jianbao233/Civ6WorkshopUploader) | 煎包 / Jianbao233；许可证版权行：Civ6WorkshopUploader contributors | workspace 结构、命令与退出码、条目 ID 保存、英语主元数据与本地化、上传前检查 | 包内 MIT；保留[原许可证](licenses/Civ6WorkshopUploader.LICENSE)。上传器及 Steam DLL 未纳入本项目 |
| S6 | `LeaderFallbacks立绘差分模板，记得删中文.artdef` | 飞花白（用户提供作者信息） | 23 个外交状态与立绘映射，由独立模型与生成器实现差分功能 | 文件未附许可证；本项目不原样分发。模板中的中文说明是 XML 混合文本，需与实际注册结构区分 |
| S7 | Civ6ArtUnpack_Handover.zip | **千川白浪**（用户提供作者信息） | BLP/FGX 复原证据、三层类名、XLP 对象与引用、pantry 遮蔽、预乘纹理和回打包覆盖率；增强现有只读检查器 | 包内未发现独立 LICENSE/COPYING；知识重新组织、工具独立实现，不原样分发源码、Oodle/Granny 辅助二进制、.git、游戏资产和大型库存索引 |
| S8 | `civ6-model-import.zip` | 千寻瀑（用户提供署名） | UE 工程（鸣潮等）psk/ueanim → 文明6 领袖 3D 模型导入技能包：十步流程、四条采信判据、转换工具链与脚本、跨会话交接模板 | 包内未发现独立 LICENSE；`tools/CivNexus6/` 的 Firaxis/Granny/FBX 程序集与未签名 exe 为 CivNexus6 构建产物，许可以上游为准；本项目只登记名单与本机安装，不内置、不分发原件 |

S4 的线上仓库页面本次未成功读取；采用的是用户提供的本地包，而不是未经核实的线上最新版。2026-10-26 复核：线上 `nuanyuqingfeng/civ6-modding-skills` 现为约 9 个 skill 的 monorepo，仓库 LICENSE 为 PolyForm Noncommercial 1.0.0；本项目仅按旧 zip 的 MIT 版本采用已炼化部分并保留署名，不再从线上版本吸收内容，也不分发其文件。S1 的审阅提交为 `0a39dfbecdf23971f3df146765858a1f0e15505f`。S5 的元数据类型与更新行为补充核对 [ModConfig.cs](https://github.com/Jianbao233/Civ6WorkshopUploader/blob/17b32062e5663c3e0eedb390ec921f37f9a97ba5/src/ModConfig.cs) 和同提交 UploadCommand.cs；本地 1.0.0 包与该线上提交分别记录，不声称版本一致。

S7 的本地包标记生成于 2026-09-17；未读取或执行随包 .git 历史、解码器 EXE。移交 README、旧库说明与会话状态存在已记录的冲突，实际采用范围以 [美术解包指南](skills/reference/art/art-unpack.md) 为准。本项目以用户明确给出的“千川白浪”署名，不据包内个人路径推断作者身份。

S8 的压缩包由用户提供，作者署名千寻瀑（用户确认），包内版本 2026-10-27，包内 `MANIFEST.sha256` 记录全包文件散列。本项目不把该包纳入 Git 或源码分享，也不代替作者发布；本机安装到 Git 忽略的 `workspace/local_skills/civ6-model-import/`，名单、安装方法与检索命令见 [外置技能名单](skills/EXTERNAL_SKILLS.md)。包内文档的工程常量、本机绝对路径与实测结论不被吸收为本项目通用规则。

## 来源治理与分发边界（2026-10-26）

用户确认的处理方式：

| 类别 | 仓库内 | 分发 | 说明 |
|---|---|---|---|
| 已炼化 / 已改写 | 本项目自己的指南、工具、数据 | 随源码分享 | 保留来源编号、许可与采用边界；不再从上游整包吸收 |
| 仅参考的外部 skill / 知识仓库 | 不内置 | 不分发、不提供拉取工具 | 只在本页记录链接；需要时用户自行访问上游。不炼化、不复制 |
| 可拉取的外部 skill（公开仓库） | 不内置；仅名单记录 URL、版本与许可 | 不随源码分享；用户按 URL 自行 clone 到本机仓库外目录 | 例：civ6-mcp（MIT）；本项目只记录来源，不复制代码、不提供副本 |
| 压缩包 / 无 GitHub 原件 | 不内置 | 不提供下载或副本 | 缺失项由用户向作者或分享者获取 |
| 外置技能包（仅名单） | 不内置；仅在 [外置技能名单](skills/EXTERNAL_SKILLS.md) 登记 | 不随源码分享；本机安装到 Git 忽略的 `workspace/local_skills/` | 原件由用户向作者索取，本项目不代替作者发布 |
| 用户确认可分享的社区模板 | `skills/civ6-art-images/assets/templates/` | 随源码分享 | 仅 PSD 模板及原说明；作者仍待考 |
| 他人创意工坊 Mod 提炼资料 | 仅本机 `local_notes/04-lua-workshop/`（Git 忽略） | 不进入 Git、不随源码分享 | 见下节 |

## 本地保留、不再分享的他人工坊资料（2026-10-26）

`skills/04-lua/` 原有 92 篇 Lua/UI 资料提炼自他人 Steam 创意工坊 Mod（作者、Mod 名与 ID 见各文件原头部，例如 MoreLenses、MonopolyPlus、Better Religion Screen、Sukritact's Tourism Overview 等）。2026-10-26 起这些资料移出 Git 与源码分享，仅维护者本机保留在 `local_notes/04-lua-workshop/`（含本地索引；可用 `modgen skill --skills-dir local_notes/04-lua-workshop "关键词"` 检索）。本页不复制这些资料，也不主张其再分发许可；若未来重新纳入，必须逐篇补充作者/来源并确认许可。

仓库内 `skills/04-lua/` 继续保留自有 Mod 子系统、通用规范，以及对官方游戏 UI 文件的分析（17 篇，分析性质，不随包分发游戏文件）。官方游戏文件与 SDK 仍属 Firaxis Games / 2K。

## 文本库来源（`local_text_New.sqlite`，2026-10-29）

根目录 `local_text_New.sqlite` 是供工具查询的官方中文文本库（表 `LocalizedText`，仅 `zh_Hans_CN`）。2026-10-29 从本机《文明 VI》官方安装重新抓取生成，**不含任何 Mod / 工坊 / 自有工程词条**：

- 来源：`Base/Assets/Text/Vanilla_zh_Hans_CN.xml` 与 `DLC/*/Text/**` 中含 `Language="zh_Hans_CN"` 的多语言翻译文件（纯英文 `en_US/` 目录已排除）；文本版权归 Firaxis Games / 2K，本库仅为查询用派生数据。
- 生成方法：`ModTools_5_4/db/text_database.py` 的解析/导入函数（纯标准库），同一 Tag 后导入覆盖；一次性重建脚本与全部校验见 `workspace/review_notes/restructure/2026-10-29/text/build_clean_text_db.py` 与同目录 `clean_text_db_report.md`（该目录被 Git 忽略）。
- 规模与边界：32,268 行 / 约 8.3 MB。旧库（84,467 行，混有 52,208 条自有 Mod 词条）已备份为同目录 `old-local_text_New.sqlite`，不进入 Git。本库随源码分享工具列入分发范围，但只承载官方文本的查询副本，不代表本项目授予游戏文本的再分发许可；游戏素材与官方数据库权利仍属 Firaxis Games / 2K。

## 间接来源

S3 / S4 的作者明确说明，其工作流和验证记录建立在游戏、SDK 与社区教程之上。后续采用相关内容时，应保留原文已有的二级署名，尤其是：

- [Civ6_Modding_Textbook](https://github.com/dwughjsd/Civ6_Modding_Textbook)：小优妮 / dwughjsd；音频教程、Wwise 模板与纸片领袖交叉核对线索。
- [ml-civ6-lua-tutorial](https://github.com/FYMapleLeaves/ml-civ6-lua-tutorial)：枫叶；Lua 教程线索。
- [civ6-mcp](https://github.com/lmwilki/civ6-mcp)：lmwilki；S4 的 FireTuner 协议实现注明参考此项目。2026-10-29 用户确认按外置 skill 处理：可拉取、记录网址、不内置；本机安装说明见 [外置技能名单](skills/EXTERNAL_SKILLS.md#civ6-mcp)，本项目未复制其代码或文档。
- Firaxis Games / 2K：《文明 VI》与 SDK 的数据、素材及接口来源；本轮未新增分发其二进制素材或游戏数据库。

本页记录上述关联并不代表本项目已采用这些间接来源的全部内容；具体采用范围以对应文件说明为准。

## 本地包版本指纹

记录 SHA-256 以区分同名包的不同版本；原始文件位于用户提供的参考目录，发布包不依赖该目录。

| 文件 | SHA-256 |
|---|---|
| `civ6-audio-pipeline_share.zip` | `9d122f0b336d870800205d9c27b33321dd68839c60d129881b67b215d186437d` |
| `civ6-modding-skills.zip` | `1d62f97c789826e87283812ca1a0a628bb396e7bd55c664a1cc59af5b63f7930` |
| `Civ6_2D纸片领袖模板包.zip` | `5d937345b5f4a32d955da8342afb1ad67a28fc4c2bc4ead6c682a06edf984447` |
| `创意工坊上传器-CLI.zip` | `83e90bc32e8cb8c53eb57793c63a9a4b78d7add29d68ddb746e563d8817b8ed7` |
| `LeaderFallbacks立绘差分模板，记得删中文.artdef` | `3c3d73d3f0fc103fd42628f29196ef1272e70705aefdccd5e9e2802c34bee3b9` |
| Civ6ArtUnpack_Handover.zip | 8a559b7cf44f7645be2058a466a0e08eeaa9b9c1e1c9de290f7c08d6cafe8a6b |
| `civ6-model-import.zip` | `2d9f3727303fa71c651658e356bc3128dad655317d9a9c66d9387e99c7c7026f` |

## 采用与分发约定

- 对改编的代码、文档或数据，在文件头或“来源”段写明来源编号、原相对路径及本项目调整点；复制 MIT 内容时随包保留原版权与许可全文。
- 本项目自身规则、`.CIV` 字段和当前工具契约仍由现有入口维护；上游个人路径、特定 Mod 标识、历史测试结果不自动成为通用约束。
- 将上游实测、本项目静态核对、本项目测试和待实机验证分别标注；本项目未复现的游戏表现不能写成已验证。
- 他人工坊 Mod 提炼资料不进入 Git 与源码分享；外部 skill / 知识仓库不复制、不拉取、不炼化，只保留本页参考链接。
- 压缩包类原件不内置；缺失时在文档标明，由用户自行向作者或分享者获取，本项目不提供副本。外置技能包只在名单页登记，不入 Git、不随分享；用户从作者取得后安装到 Git 忽略的本地目录。
- 仅社区 PSD 模板（用户确认）随技能分享；其余第三方原件不纳入分发。
- 新增发布内容时，同步将本页及实际需要的许可证文件纳入源码分享工具 tools/share_source.py 的分发范围，避免源码有署名而分享目录遗漏。
