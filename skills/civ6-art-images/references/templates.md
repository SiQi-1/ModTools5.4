# 模板提取与配方

## 随包模板

模板已随技能放入 `assets/templates/`：区域 `district.psd`、头像 `leader.psd`、历史时刻 `moments/`（含 1～18、模板1、模板-2～-7 和原《如何使用.docx》）。原始文件逐字节保留；[清单](../assets/templates/manifest.json) 记录散列、原名和分享依据，作者待考。不要再要求使用者复现维护者的 D 盘路径。

## PSD 检查与选择

```powershell
python -m modgen.cli image inspect-psd "模板.psd" --out modgen_work/template-inspect
python -m modgen.cli image extract-psd "模板.psd" --layer 1 --channel alpha --out modgen_work/templates/mask.png
```

`inspect-psd` 保留 PSD 内嵌的合成预览，返回树形编号，如 `1/9/0`。编号按该 PSD 的实际顺序确定，不按名字猜测。`extract-psd` 默认 pixels 模式只接受单个无蒙版的像素/缓存图层，保留原始位置和图层透明度；`--mode composite` 支持多个 `--layer`，保留所选子树原本可见的子层，强制打开祖先、关闭其他分支。两种方式都输出 PSD 整张画布，避免边界偏移。

输出已有文件时需要 `--replace`；始终拒绝覆盖源文件。Alpha 提取输出 L 模式 PNG，合成器将其灰度值直接作为透明度，不会把这张灰度蒙版当成不透明背景。

## 已研究的历史时刻模板

用户提供的“历史图片模板（集合）”包含 456×332 PSD。其《如何使用.docx》要求用模板图层选区裁切新图，再着色，或叠加黄色正片叠底层。`模板-2.psd` 中 `0` 为黑色展示底，`1` 为带柔边透明度的白色笔刷轮廓。因此提取 `1` 的 Alpha，不提取黑底合成图；其他模板先 inspect 确认层结构。

```json
{
  "version": 1,
  "kind": "moment",
  "source": "scene.png",
  "mask": "mask.png",
  "focus": [0.5, 0.5],
  "contrast": 1.1,
  "tone": ["#35291e", "#ddcba7"]
}
```

默认 456×332，图像覆盖画布并按 focus 选择裁切重心。tone 是暗部/亮部双色映射，保留亮暗层次。最终 Alpha 为原图 Alpha × 模板蒙版。**绝不对最终场景执行“所有黑色变透明”**，画面里的暗色设备、头发、阴影应保留。

扁平黑底白蒙版可显式用 `mask_channel: luminance`。彩色场景不适用这个黑底转换规则。默认 Alpha 通道适用于透明 PNG 蒙版；L 模式蒙版直接读灰度。

## 已研究的领袖头像模板

用户提供的“领袖头像模板.psd”为 256×256；`0/0` 是圆形地图底板，边界约 `[12,11,247,246]`；其余图层包含背景装饰和示例人物，不能原样当作新头像。可提取该层两次：RGBA 作底板，Alpha 作蒙版。

```powershell
python -m modgen.cli image extract-psd "领袖头像模板.psd" --layer 0/0 --out base.png
python -m modgen.cli image extract-psd "领袖头像模板.psd" --layer 0/0 --channel alpha --out circle.png
```

```json
{
  "version": 1,
  "kind": "leader",
  "source": "standing-art.png",
  "crop": [386, 68, 616, 298],
  "background": "base.png",
  "mask": "circle.png",
  "border": 2,
  "border_color": "#101820"
}
```

crop 是演示坐标，必须根据当前原图看图确定，不能直接套给其他人物。先保留脸、头发和身份特征，再决定肩部比例；脸部视觉中心比整张立绘或大饰物的包围盒中心更重要。该命令采用圆形裁切；头发/帽子出框需要另行制作分层前景，不自动猜测。

## 白色、灰度与区域图标

文明白标配方：`{"version":1,"kind":"white","source":"emblem.png","mask_channel":"alpha","margin":20}`。透明轮廓涂成纯白，抗锯齿只写 Alpha；不透明黑底白图改为 luminance。色彩复杂的图案不能靠灰度化获得正确轮廓。

改良配方：`{"version":1,"kind":"grayscale","source":"relay.png","levels":[128,255],"margin":20}`。保留透明度，将明暗映射为白灰。先选择或制作简洁通信塔图形；把彩色技能图变灰不等于获得合适图标。

用户提供的“区域图标模板.psd”含 Import Alpha 和 Choose District。学院的底板组为 `1/9/0`，**Alpha 组为 `1/9/1`**，里面的 `District Alpha` 是待替换样例。新图案必须在这个 Alpha 组下，不能只提取底板后叠白图。工具隐藏旧样例、Import Alpha、Reference 及其他区域组，插入新白色核心；原模板只读。

已核实学院 Alpha 样式：青蓝渐变叠加（-90°）、3 px 内部渐变描边、3 px/45% 正片叠底外发光；底板包含自身渐变与 11 px/13% 柔光内发光。脚本读取实际 PSD 参数，不把这些数值硬编码为所有区域通用色。中央核心框约 `[58,58,200,200]`。

依赖：`python -m pip install "psd-tools[composite]>=1.20"`。先 inspect 自己的模板，再填写下方两个组编号；编号不保证跨版本相同。

```json
{
  "version": 1,
  "kind": "district",
  "source": "workroom-white.png",
  "template_psd": "区域图标模板.psd",
  "alpha_layer": "1/9/1",
  "background_layer": "1/9/0",
  "glyph_box": [58,58,200,200]
}
```

区域配方拒绝彩色/实底核心，以及旧的 background/stroke/stroke_color 配方。渐变叠加和渐变描边由 psd-tools 合成；额外按描述符实现平滑、线性轮廓的内外发光（Normal/Multiply/SoftLight）。不支持的样式、噪点发光、非默认有效渐变中点等会报错。输入白图转为模板配色是正常结果，不应在合成后再次刷白。

输出同名 `.psd` 副本，新图层 `ModTools Core` 实际位于 Alpha 内，原始效果描述完整保留；PNG 报告列出每个效果与具体参数。PNG 的发光使用形态扩张/高斯核近似，渐变平滑度、抖动与色彩管理不等同 Photoshop。fx scale 元数据保留在 PSD，脚本使用已存储像素尺寸，不再二次乘算。PSD 缓存预览由第三方合成器生成，不作为原生 Photoshop 对照。

需要像素级原生结果时，在 Photoshop 打开这个副本导出 PNG，再做尺寸与小图验收。第三方合成器本身也明确说明与 Photoshop 可能存在差异，见 [psd-tools 合成文档](https://psd-tools.readthedocs.io/en/latest/reference/psd_tools.composite.html)。

## 合成与检查

区域制作的固定顺序：①查看核心轮廓与 PSD；②inspect 定位所选区域的底板组和 Alpha 组；③将核心整理为纯白透明 PNG；④用含 template_psd/alpha_layer/background_layer 的 district 配方渲染；⑤确认副本中 ModTools Core 位于 Alpha 内、样例隐藏、效果参数完整；⑥看 256/64/38/22 预览；⑦以 contain、关闭二次裁圆/描边写入实体图片槽；⑧检查实际导出的 PNG/DDS，再进行官方编译。原 PSD、白色输入、recipe、可编辑 PSD 和效果报告共同构成可复现记录。

```powershell
python -m modgen.cli image render recipe.json --out result.png
python -m modgen.cli image check result.png --kind district
```

render 生成 PNG、同名 JSON 报告及 `.preview.png`。报告中 `ok` 仅代表像素检查；`visual_review: required` 始终保留。白色检查可见像素 RGB=255，灰度检查 R=G=B；各类要求透明背景、透明四角和非空主体。leader/district 默认检查 256×256，moment 检查 456×332。已有游戏小尺寸输出可用 `--size 宽 高` 按对应尺寸检查。验收还需查看实际导出的 PNG/DDS，避免 .CIV 再次裁圆、缩放或加边框。

领袖颜色填写 `#RRGGBB`，不能把 `COLOR_STANDARD_*` 字符串填入当前编辑器颜色槽；工具自动解析或生成 Colors/PlayerColors。同时查看主色背景、徽记副色和至少一组备选色，避免高饱和色互相冲突。
