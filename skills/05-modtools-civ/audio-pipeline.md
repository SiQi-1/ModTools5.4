# 音频管线：Wwise、Banks.ini 与 UpdateAudio

适用：普通音效、领袖语音、文明音乐、BNK/WEM 注册和静音排查。既有文明音乐复用与制作新 soundbank 是不同任务。

## 素材与制作路线

| 类别 | 主要工作 | 额外核对 |
|---|---|---|
| sfx 普通音效 | 整理素材、格式核验、事件与独立 bank | Lua / 数据触发端是否确实发出事件 |
| voice 领袖语音 | 语音语言、事件、SoundBank | 动画时间线的 Sound 事件与 Duration |
| bgm 文明音乐 | 时代容器、曲目、事件、SoundBank | 区分轮播、外交音乐和载入主题曲，核对时代权重 |

按用户用途与素材分类，不能单靠时长把台词误当音乐。保留母带，输出处理副本。

上游以 PCM WAV / 48 kHz 为整备基准，以 Wwise 2015.1.x 生成音频。目标版本与用户工程和 SDK 兼容性核对，不用新版 Wwise 自动升级旧工程。直接编辑工作单元前关闭 GUI，保留备份并维护 GUID 引用。

## 声道与响度

先转换到最终声道，再测量并做 ffmpeg loudnorm 两遍处理。若测量立体声后才混成单声道，成品与测量对象不同，可能出现响度偏差；处理后重新测量。

千寻瀑提供的参考目标：voice -21、quote -23.5、远古 BGM -28、后世 BGM -25、sfx -27 LUFS。这些是其模板和混音的校准配置，不是引擎必需数值；用户目标、动态范围和实机混音优先。时代选曲和权重按设计确定，不照抄特定项目策略。

长音频通常考虑流式媒体。“BNK 已生成”不表示所需 WEM 一并打包成功。

## 注册闭环

常见文件位于 Platforms/Windows/Audio：

1. Banks.ini 的 Global / Menu / InGame / 2D / 3D / FMV 分区列出相应 .bnk 文件名。
2. 工程或构建 modinfo 的 UpdateAudio 动作引用 INI。
3. INI、BNK 与所需 WEM 纳入 Content / Files，构建包包含这些实际文件。
4. 用 SoundBanksInfo 元数据核对 ReferencedStreamedFiles；嵌入 bank 的媒体不能误报为外部 WEM 缺失。

INI 按上游已验证路线使用无 BOM ASCII 和 CRLF。检查器将非 ASCII 报错、不同换行报建议，不改写文件。

上游 mechanism.md 较早段落提到动作可同时列 BNK/XML，但后续故障记录和 register_to_mod.py 已收敛为动作只引用 INI。本指南采用修正后的工作流，不把所有音频文件塞进 UpdateAudio。

## 当前命令

~~~powershell
python -m modgen.cli audio check ModBuddy/工程.civ6proj --json
python -m modgen.cli audio check Staging/工程.modinfo --json
~~~

只读解析工程 XML、命名空间和动作内嵌 XML，检查声明文件、INI、BNK 和可识别元数据中的流式 WEM。缺少匹配元数据列入 unverified；无静态错误不等于全部依赖或发声已验证。

extension 只管理 SQL/XML/Lua，不接收 BNK/WEM/INI。音频写入与 Wwise 编译仍由用户音频工具链完成；检查命令不导入声音、不改部署 Mod，不安装 Wwise/ffmpeg。

## 已弃用路径与验收

上游保留的纯 Python MS ADPCM bank 构造已被其实机记录弃用，曾导致噪音和闪退；本项目未集成。ShortID 研究不能证明自行构造的编码可交付。

验收依次记录：素材 → Wwise 编译 → 注册 → 构建包 → 事件触发 → 游戏播放。语音还需验收时间线，BGM 检查三个用途与时代切换。

## 来源

[来源 S3 / S4](../../THIRD_PARTY_NOTICES.md)：千寻瀑（千与千寻瀑）的 civ6-audio-pipeline，参考 SKILL.md、references/mechanism.md、scripts/audio_normalize.py、scripts/register_to_mod.py；音频教程线索来自小优妮的 Civ6_Modding_Textbook。指南和只读检查器独立适配，未复制 Wwise 工程、音频或 ADPCM 打包器。Wwise 和混音实机经验标为上游记录，非本项目复测。
