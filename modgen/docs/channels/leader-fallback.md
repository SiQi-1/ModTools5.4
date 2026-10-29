# 领袖外交表情差分（fallback_images）

> 受众：制作领袖美术与外交表情的 AI/开发者 ｜ 何时读：为领袖条目声明 fallback_images 或排查表情资源时 ｜ 适用版本：ModTools 5.4

> 本文自 [modgen/AGENTS.md](../../AGENTS.md) 拆出；本通道只读此篇，通用硬规则仍以 AGENTS.md 为准。

## 领袖外交表情差分

领袖条目可声明可选映射 fallback_images：键为外交状态，值为图片对象（path 必填，既有图片槽变换可选）。null / 空映射保留旧工程行为。DEFAULT 优先于 images.diplo_foreground，其余只导出明确提供的状态；有差分时必须有默认图。

只填 path 的新状态图按比例完整放入 960×960 透明画布；显式变换沿用图片槽规则。默认资源仍为 FALLBACK_NEUTRAL_<short_type>，其他状态为 FALLBACK_STATE_<STATE>__LEADER_<short_type>，避免 NEUTRAL 与默认资源冲突。状态、路径、资源名由 project/leader_fallbacks.py 统一；GUI、schema、CLI 校验与导出共享该模型。

validate 检查声明、状态、Type 和文件存在性，不加载 Qt/Pillow；GUI 生成前另检查图片可读性。完整生成会输出 PNG、DDS/TEX、LeaderFallback.xlp 和 FallbackLeaders.artdef。23 状态来自署名社区模板，其中 DECLAR_WAR_FROM_HUMAN 保留模板拼写，目标 SDK 和游戏触发仍需验收。字段例子与操作见 [领袖美术指南](../../../skills/reference/art/leader-art.md)。
