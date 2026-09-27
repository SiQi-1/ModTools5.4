# 领袖美术：选人排版、外交差分与纸片领袖

适用：选人前景/背景、领袖立绘、外交表情、LeaderFallback、平面模型纸片。普通 UI 背景另见 [美术与文本](ui-assets.md)。

## 选人界面：皮肤背景与空白前景

先按素材构图区分排版：独立人物立绘可放前景；带完整场景的皮肤立绘可优先放背景，前景明确配置透明占位图。用户制作经验指出，选人前景在游戏控件中可能存在顶部间隙和额外裁切，单独查看导出 PNG 完整并不能证明游戏里显示完整。

- `images.select_background` 放皮肤图，当前导出为 **384×1024**；重新按该画幅设置缩放与偏移，不能直接复制前景的 512×1024 坐标，亦不能非等比拉伸原图。
- `images.select_foreground` 放空白前景，当前导出为 **512×1024**。保留有效图片声明及资源绑定，不用删除图片槽、空路径或未导出的文件代替透明图。
- 空白图也要检查 Alpha：白色预览不代表透明，边缘可能残留可见像素。保留原图，通过已有图片槽裁切/偏移隔离已确认的边缘残留，并检查最终导出前景的 Alpha 全为 0。
- 背景的人脸、头饰、手部与主体范围由多模态模型或人工复核；纯文本模型只复用已验收坐标。换背景槽后须重新看导出图，游戏中的顶部、可视边界与文本遮挡另行验收。
- 各场景独立选择：改变选人图片不自动改变加载、头像或外交；外交默认图还要核对 `fallback_images.DEFAULT`，其优先级高于 `images.diplo_foreground`。

依据：2026-09-28 用户提供的选人排版经验；尺寸与字段已核对当前 `_collect_leader_direct_image_plans` 导出器。此策略不宣称所有独立人物立绘都必须改放背景，也不把 PNG/SDK 检查当作游戏内验收。项目素材、路径、坐标和报告保留在各 Mod 的本地工作目录。

## 先选择资源路线

| 需求 | 路线 |
|---|---|
| 一张外交回退立绘 | 领袖 images.diplo_foreground，沿用当前工具输出 |
| 开心、敌对、宣战等表情变化 | 领袖 fallback_images；工具生成 PNG、DDS/TEX、XLP、ArtDef |
| 三维外交场景的平面模型 | 纸片领袖，需要 GEO/FGX/WIG、材质、行为资产、环境与灯光，再经 SDK Cooker |
| 真正的三维领袖与动画 | [Blender / CivNexus6](blender-civnexus.md) |

外交回退图片和三维平面模型是两套资源，不要因为都使用立绘就混用纹理类别。

## 外交表情差分 fallback_images

GUI：领袖编辑器 → “外交表情差分（展开）”。每个状态可以选择、清除和预览图片。清除只移除声明，不删除源图。图片选择存绝对路径；现有图片裁切等元数据可经 .CIV 保留。表格预览显示原图，最终缩放/裁切以导出 PNG 为准。

条目字段为可选对象，值使用现有图片槽格式：

~~~json
{
  "fallback_images": {
    "DEFAULT": {"path": "D:/MyMod/Art/neutral.png"},
    "HAPPY": {"path": "D:/MyMod/Art/happy.png"},
    "ENRAGED": {"path": "D:/MyMod/Art/angry.png"}
  }
}
~~~

示例路径需替换为实际文件。实体骨架、Type 和合并继续走 [工程流程](../WORKFLOW.md)，不要手写最终 XLP / ArtDef。

- DEFAULT 优先采用显式图片，否则沿用 images.diplo_foreground。声明差分时必须有默认图；未声明状态交由 DEFAULT 回退。
- 默认资源名保持 FALLBACK_NEUTRAL_ 加领袖去掉 LEADER_ 后的标识；独立状态使用 FALLBACK_STATE_<状态>__LEADER_<标识>，双下划线与 LEADER_ 明确分隔状态和领袖名。因此 DEFAULT 与 NEUTRAL 可以使用不同图片。
- 回退图导出 960×960；新增声明只给 path 时等比居中适配画布，显式 scale/offset/canvas 参数继续按图片槽排版，旧默认图排版不变；保留 alpha，纹理类别为 Leader_Fallback。同图可用于多个状态，各状态保留独立资源名。
- 文件使用 LeaderFallback.xlp / FallbackLeaders.artdef，不添加工程文件名前缀。
- 空映射或省略字段兼容旧工程。无效状态、空路径、缺失默认图或源文件会报错；GUI 生成前还解码图片检查可读性。
- 不把模板中标签后的中文说明写入 ArtDef。中文留在文档、界面或 XML 注释中。

状态的单一实现是 [leader_fallbacks.py](../../ModTools_5_4/project/leader_fallbacks.py)，来自飞花白模板：DEFAULT、DECLARE_WAR_FROM_AI、DECLAR_WAR_FROM_HUMAN、DEFEAT、ENRAGED、FIRST_MEET、HAPPY、HAPPY_IDLE、HAPPY_NEGATIVE、HAPPY_POSITIVE、KUDOS、NEUTRAL、NEUTRAL_GREETING、NEUTRAL_NEGATIVE、NEUTRAL_POSITIVE、NEUTRAL_TO_HAPPY、NEUTRAL_TO_UNHAPPY、UNHAPPY、UNHAPPY_IDLE、UNHAPPY_NEGATIVE、UNHAPPY_POSITIVE、UNHAPPY_TO_NEUTRAL、WARNING。

DECLAR_WAR_FROM_HUMAN 保留原模板拼写。本仓库没有其官方枚举快照，不擅自改名；各状态能否由目标游戏环境触发需实机确认。

## 三维纸片领袖资源链

千寻瀑模板的链路：LeaderType → Leaders.artdef → 领袖 XLP / LightRig XLP → AST / LRG → GEO / MTL / ENV → FGX / WIG / DDS / TEX。

对这一平面模板：

- 材质使用 Leader_Matte，至少接上 BaseColor 和 Opacity。上游记录了该模板用普通 Leader 材质发灰的问题；不能推广到正常三维模型。
- 检查环境方向灯是否为空；上游修正版补有三盏灯。具体灯强、尺寸和压缩选项依模板与画面验收决定，不对所有领袖强制同一数值。
- BaseColor 和 Opacity 保持同一人物布局，避免透明轮廓错位。高饱和边缘色差需检查 TEX 色度损失设置。
- 名称从工具生成的 LeaderType 派生，不继承作者专用后缀。FGX/WIG、GEO 和相机引用须一致。
- 本项目尚无整套模型资源的自动导入写入通道；SQL/XML/Lua 的 extension 不接收这些二进制。采用用户合法取得的模板与 SDK 工程，构建后核验。

## 验证与排错

~~~powershell
python -m modgen.cli validate 工程.CIV
python -m modgen.cli assets check ModBuddy/工程.civ6proj --json
~~~

后者检查已生成工程和本地资源，不调用 Cooker。只有完成 SDK 编译和游戏测试，才确认外交照明、透明边缘、表情触发和窗口缩放。

全黑先核对灯光环境；发灰先核对该纸片模板的材质；只有背景先核对几何和资产引用；修改无变化先确认重新 cook。源码和产物的差异见 [Cooker 检查](art-cook-validation.md)。

## 来源与验证边界

参考 [来源 S2 / S4 / S6](../../THIRD_PARTY_NOTICES.md)：千寻瀑（千与千寻瀑）的《制作方法.md》及 civ6-asset-forge/reference/leader-2d.md；飞花白的 LeaderFallbacks 模板。按本项目 .CIV、编辑器和生成器重新组织，未复制上游模型、贴图或模板。自动化回归覆盖声明、GUI 往返和导出；游戏表现不视为已验证。
