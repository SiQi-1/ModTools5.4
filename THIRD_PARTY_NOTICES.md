# 第三方参考资料与致谢

本项目在完善文明 6 制作知识和工具时参考了下列作者的成果。致谢不改变上游许可，也不将游戏素材、第三方二进制或社区模板自动纳入本项目的 MIT 许可证。

本轮核对日期：2026-09-25。已落地社区制作指南、领袖外交表情差分、四类只读检查命令及知识检索路由；具体采用与验收边界见[整合记录](docs/COMMUNITY_SKILL_INTEGRATION.md)。指南按来源编号署名；工具代码为本项目独立实现，不含上传器、Blender 插件、音频脚本或模板原件。

## 直接参考来源

| 编号 | 资料 | 作者 / 署名 | 本轮参考内容 | 许可核对 |
|---|---|---|---|---|
| S1 | [Nexus-Buddy-2-Blender-Scripts](https://github.com/Sukritact/Nexus-Buddy-2-Blender-Scripts) | Sukritact；脚本作者 Deliverator，部分脚本共同署名 Deliverator、Sukritact；仓库派生自 [deliverator23/Civilization-Blender-Scripts](https://github.com/deliverator23/Civilization-Blender-Scripts) | Blender ↔ CN6、NA2 动画导入与 CivNexus6 的职责划分 | 核对的提交未包含 LICENSE/COPYING，三个脚本未发现授权声明；本项目仅引用，不分发这些脚本 |
| S2 | `Civ6_2D纸片领袖模板包.zip` | 千寻瀑（千与千寻瀑；用户提供作者信息） | 纸片领袖资源链、Leader_Matte、环境灯光、颜色与透明度贴图、命名与验收 | 独立压缩包未附许可证；其中通用二进制和模板有其他来源，暂只作为技术参考 |
| S3 | `civ6-audio-pipeline_share.zip` | 千寻瀑（入口署名：千与千寻瀑） | 音频分类、声道与响度处理、Wwise 2015 工作流、Banks.ini / UpdateAudio 注册核验、已弃用打包方案 | 入口声明 MIT，但独立包无 LICENSE 文件；合集 S4 内的音频技能另有 MIT LICENSE。复制时应明确采用哪个包及文件版本，不能混淆 |
| S4 | `civ6-modding-skills.zip`；包内给出的上游：[nuanyuqingfeng/civ6-modding-skills](https://github.com/nuanyuqingfeng/civ6-modding-skills) | 千寻瀑；MIT 版权行原文署名 **千与千寻瀑** | 美术引用链、Cooker 差异分析、制作验证、UI / GP 环境核验、工坊交付流程 | 代码与文档附 MIT；保留[原许可证](licenses/civ6-modding-skills.LICENSE)。随包第三方资料、素材和工具须分别识别出处，不能一概归为作者原创 |
| S5 | `创意工坊上传器-CLI.zip`；[Civ6WorkshopUploader](https://github.com/Jianbao233/Civ6WorkshopUploader) | 煎包 / Jianbao233；许可证版权行：Civ6WorkshopUploader contributors | workspace 结构、命令与退出码、条目 ID 保存、英语主元数据与本地化、上传前检查 | 包内 MIT；保留[原许可证](licenses/Civ6WorkshopUploader.LICENSE)。上传器及 Steam DLL 未纳入本项目 |
| S6 | `LeaderFallbacks立绘差分模板，记得删中文.artdef` | 飞花白（用户提供作者信息） | 23 个外交状态与立绘映射，由独立模型与生成器实现差分功能 | 文件未附许可证；本项目不原样分发。模板中的中文说明是 XML 混合文本，需与实际注册结构区分 |
| S7 | Civ6ArtUnpack_Handover.zip | **千川白浪**（用户提供作者信息） | BLP/FGX 复原证据、三层类名、XLP 对象与引用、pantry 遮蔽、预乘纹理和回打包覆盖率；增强现有只读检查器 | 包内未发现独立 LICENSE/COPYING；知识重新组织、工具独立实现，不原样分发源码、Oodle/Granny 辅助二进制、.git、游戏资产和大型库存索引 |

S4 的线上仓库页面本次未成功读取；采用的是用户提供的本地包，而不是未经核实的线上最新版。S1 的审阅提交为 `0a39dfbecdf23971f3df146765858a1f0e15505f`。S5 的元数据类型与更新行为补充核对 [ModConfig.cs](https://github.com/Jianbao233/Civ6WorkshopUploader/blob/17b32062e5663c3e0eedb390ec921f37f9a97ba5/src/ModConfig.cs) 和同提交 UploadCommand.cs；本地 1.0.0 包与该线上提交分别记录，不声称版本一致。

S7 的本地包标记生成于 2026-09-17；未读取或执行随包 .git 历史、解码器 EXE。移交 README、旧库说明与会话状态存在已记录的冲突，实际采用范围以 [美术解包指南](skills/05-modtools-civ/art-unpack.md) 为准。本项目以用户明确给出的“千川白浪”署名，不据包内个人路径推断作者身份。

## 间接来源

S3 / S4 的作者明确说明，其工作流和验证记录建立在游戏、SDK 与社区教程之上。后续采用相关内容时，应保留原文已有的二级署名，尤其是：

- [Civ6_Modding_Textbook](https://github.com/dwughjsd/Civ6_Modding_Textbook)：小优妮 / dwughjsd；音频教程、Wwise 模板与纸片领袖交叉核对线索。
- [ml-civ6-lua-tutorial](https://github.com/FYMapleLeaves/ml-civ6-lua-tutorial)：枫叶；Lua 教程线索。
- [civ6-mcp](https://github.com/lmwilki/civ6-mcp)：lmwilki；S4 的 FireTuner 协议实现注明参考此项目。本轮未复制或执行该协议实现。
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

## 采用与分发约定

- 对改编的代码、文档或数据，在文件头或“来源”段写明来源编号、原相对路径及本项目调整点；复制 MIT 内容时随包保留原版权与许可全文。
- 本项目自身规则、`.CIV` 字段和当前工具契约仍由现有入口维护；上游个人路径、特定 Mod 标识、历史测试结果不自动成为通用约束。
- 将上游实测、本项目静态核对、本项目测试和待实机验证分别标注；本项目未复现的游戏表现不能写成已验证。
- 新增发布内容时，同步将本页及实际需要的许可证文件纳入源码分享工具 tools/share_source.py 的分发范围，避免源码有署名而分享目录遗漏。
