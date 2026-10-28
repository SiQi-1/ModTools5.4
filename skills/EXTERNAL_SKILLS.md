# 外置技能名单（不随仓库分发）

本页登记**未纳入 Git、不随源码分享**的外置技能包。仓库只保留名单、作者署名、来源指纹与本机安装/检索方法；不内置原件、不提供下载或副本，也不代替作者发布。需要时由使用者向作者获取压缩包，自行安装到本机 `local_skills/`（已由 Git 忽略）。

## civ6-model-import：UE 模型导入文明6领袖 3D

| 项目 | 内容 |
|---|---|
| 技能名 | civ6-model-import |
| 作者 / 署名 | 千寻瀑（用户提供署名） |
| 原始包 | `civ6-model-import.zip`，完整分发版，包内版本 2026-10-27 |
| 大小 / SHA-256 | 12,594,811 字节 / `2d9f3727303fa71c651658e356bc3128dad655317d9a9c66d9387e99c7c7026f` |
| 内容 | `SKILL.md`、7 篇 `references/` 文档、`scripts/` 转换与采样脚本、C# 读数工具源码、`patches/UAnimSequence.cs`，以及 `tools/CivNexus6/` 转换工具链（含未签名 exe 与 Firaxis/Granny/FBX 程序集） |
| 适用 | 把 UE 工程（鸣潮等）的 psk 模型与 ueanim 动画导入文明6，作为领袖 3D 模型；含十步流程、四条采信判据、朝向/口型/眨眼处理与跨会话交接模板 |
| 不适用 | 引用原版模型素材、Blender 通用 fgx/ast 导出、纯 UI/音频任务；这些仍走本项目既有指南 |
| 本机安装 | `local_skills/civ6-model-import/`（Git 忽略；换机器重新向作者取得后解压） |
| 取得方式 | 向作者 **千寻瀑** 索取压缩包；本仓库不提供下载、不内置原件、不代替作者发布 |

### 本机安装与检索

1. 从作者处取得 `civ6-model-import.zip`，解压到仓库根目录，得到 `local_skills/civ6-model-import/SKILL.md`。
2. 外置技能不并入默认 `skills/` 索引，按目录检索与读取：

   ```powershell
   python -m modgen.cli skill "领袖3D模型 psk ueanim 导入" --skills-dir local_skills/civ6-model-import
   python -m modgen.cli skill --file SKILL.md --skills-dir local_skills/civ6-model-import
   ```

3. 按包内 `SKILL.md` 的开工自检与参数槽位执行；工具链部署位置以包内 `references/upstream.md` 为准，部署到工程树外。

### 边界与署名

- 压缩包原件与解压内容不进入 Git，也不进入源码分享目录；`tools/share_source.py --check` 会拒绝被误跟踪的 `local_skills/` 文件。
- 包内未发现独立 LICENSE 文件；`tools/CivNexus6/` 的 Firaxis/Granny/FBX 程序集与未签名 exe 来自作者的 CivNexus6 构建产物，许可以上游为准；本项目不复制、不重新分发。
- 包内文档的本机绝对路径、工程常量与实测结论只在该包语境有效，不自动成为本项目通用规则；需要时按本项目 [规则正文](RULES.md) 与 [统一工作流](WORKFLOW.md) 复核。
- 本机未安装该包时检索不到属正常情况，不代表能力不存在；先按上方向作者取得。

来源与指纹另见 [第三方来源声明](../THIRD_PARTY_NOTICES.md)，整合记录见 [社区整合记录](../docs/COMMUNITY_SKILL_INTEGRATION.md)。
