# 头像、图标与历史时刻模板（image inspect-psd/extract-psd/render/check）

> 受众：制作头像/图标/历史时刻图片的 AI/开发者 ｜ 何时读：使用 image 子命令或 PSD 模板配方时 ｜ 适用版本：ModTools 5.4

> 本文自 [modgen/AGENTS.md](../../AGENTS.md) 拆出；本通道只读此篇，通用硬规则仍以 AGENTS.md 为准。

## 头像、图标与历史时刻模板

完整方法见 [图像模板技能](../../../skills/packages/civ6-art-images/SKILL.md)。普通实体图像使用 image，不必引入 HTML。

```powershell
python -m modgen.cli image inspect-psd "模板.psd" --out workspace/scratch/template-inspect
python -m modgen.cli image extract-psd "模板.psd" --layer 1 --channel alpha --out workspace/scratch/template-mask.png
python -m modgen.cli image render recipe.json --out workspace/scratch/result.png
python -m modgen.cli image check workspace/scratch/result.png --kind moment
```

- 四个子命令都返回 JSON。渲染支持 white/grayscale/leader/district/moment 配方；相对素材路径按配方所在目录解析。
- 读取 PSD 需要可选依赖 psd-tools；区域 Alpha 组渲染需要 psd-tools[composite]>=1.20；普通 PNG 合成/检查只需 Pillow。不要求多模态 SDK。
- inspect 输出层级编号、边界、效果和 PSD 保存的合成预览；extract pixels 读取单层缓存像素，composite 重算所选分支；不保证所有 Photoshop 特效复现。
- 原始素材不得覆盖；已有输出需 --replace。render 同时输出成品、JSON 散列/检查报告和多背景、多尺寸预览。
- leader 强制提供 crop；district 拒绝非白色透明核心。check 的 ok 仅为像素检查，不证明脸部居中、图形可辨或游戏显示正确；所有报告保留视觉复核项。
- district 强制 template_psd、alpha_layer、background_layer；将白色核心放入 Alpha 组、隐藏样例并读取渐变/描边/发光，额外输出保留原样式的 .psd。拒绝旧 background/stroke 平涂配方与不支持的样式。PNG 为参数化渲染，报告记录发光、渐变与原生 Photoshop 的差异，不能声称像素级一致。
- image 不写 .CIV 或最终游戏资源。通过已有图片槽登记成品，再由 build 生成 DDS/TEX/XLP。预制头像应关闭二次裁圆/黑边。
