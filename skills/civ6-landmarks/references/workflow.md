# 工具契约与验证

## 配方

根：`format="MODTOOLS54_LANDMARK_RECIPE"`、`assets`、`bindings`。

`assets[]`：

| 字段 | 含义 |
|---|---|
| name | 本包唯一 ASCII 资源名，以字母开始，仅字母数字下划线 |
| source | 官方 TileBase AST 逻辑名，或 SDK Assets 根内的精确相对路径 |
| description | 可选说明 |
| attachments | 可选本包附件；asset、instance、bone 必填；position/rotation 缺省 [0,0,0]，scale 缺省 1 |
| hide_states | 可选；只能填五种合法状态；仅关闭对应几何组的可见性 |
| hide_geometry | 可选；隐藏源几何材质组，保留骨骼载体 |
| drop_stale_groups | 可选且默认 false；确认官方 AST 存在残留分组后才开启 |

`bindings[]`：`kind` 是 improvement 或 district；`entity` 是现有 CIV Type；`source` 是可复用的官方实体 ArtDef 名；`landmark` 是新 Landmark 名；`base_asset` 指向本包 AST。区域还可提供 `buildings=[{"type":"BUILDING_...","asset":"AST_..."}]`。

JSON 不写空字符串。模型实例内偏移、自定义材质、动画、外包附件和任意 XML 注入不在 schema 内；资产和附件的未知字段会报错，避免拼错 position 后静默落到原点。

## 资源包与编辑器

`landmark compose` 校验全部配方后写出 Assets、XLPs、ArtDefs、recipe.json 和 manifest.json。manifest 记录文件 SHA-256、绑定、SDK 来源与必需 Art ID。非空且不含 manifest 的输出目录被拒绝；不会递归清空用户目录。

`landmark import <CIV> --bundle <manifest>` 先完整校验再保存一次 CIV，沿用 `.CIV.bak` 备份。`--dry-run` 不写 CIV；切换到其他包需 `--replace`。同包更新用重新 compose + build，依赖或绑定变更后再次 import。

CIV 的 `美术.data.landmark_bundle={"manifest":"绝对路径"}` 是单包声明。当前版本没有 GUI 配方编辑器，也不自动搬迁绝对资源路径；移动项目后在新位置重新 import。GUI 打开/保存保留声明，预览含 AST；完整导出包含全部受管资源。

直接修改资源包里的受管 AST 会改变散列，导出会阻断并提示重新 compose；只修改导出的工程 AST 则会在下一次 build 时被资源包覆盖。AE 中试出的有效布局应改回配方再生成；当前版本不支持将任意 AE 工程反向导入配方。

## 静态检查

`landmark verify --bundle ...` 检查散列、AST 名称/类、附件引用/环、XLP 的一对一登记和 Landmarks 资产引用。

加 `--sdk-assets`：验证官方几何、FGX、材质、真实网格/材质组、锚点实例和骨骼。加 `--project`：核对导出文件、实体 Xref、美术源目录不被错误注册进工程发布项、Art.xml 的 TileBase/consumer/DLC 声明和补充建筑。

该检查不是通用引擎模拟器，不验证材质的实际视觉效果或建筑状态机。新增一般能力应同步代码、测试、modgen/AGENTS.md、README、路线图和变更日志。

## 官方 Cooker

`landmark cook` 使用新建的英文临时目录，因为官方 Cooker 实测会损坏中文 pantry 路径。它复制当前资源包和可选项目 ArtDef/Art.xml，再调用安装的 `Civ6AssetCooker_FinalRelease.exe`；不修改 SDK、不启动 ModBuddy、不部署游戏。

输出包含日志、`cook-report.json` 和本次生成的 BLP/ArtDefs。检查返回码、非空新文件以及错误日志，不沿用上次输出。官方 MSBuild 的部分 Exec 使用 IgnoreExitCode，不能仅凭 ModBuddy 的“成功”判定资源有效。

无 `--project` 时可做最小包试编译，但会缺少真实 Game Art 文件和实体上下文；完整验收应传实际工程。保留暂存路径便于调试；若要清理，只删除报告中明确属于本任务的目录。

## AE 与离线预览

1. 从绑定的 ModBuddy 工程打开 AE，确保项目与所需 SDK pantry 已加载。若中文路径导致解析问题，在英文路径建立独立测试工程并使用本次资源；Cooker 暂存 pantry 不包含完整 civ6proj，不能当成可直接打开的 AE 工程。
2. 在 AE 的 TileBase 资源中找到自定义 AST；查看 Worked/Unworked/Pillaged/Construction/Unbuilt。
3. 对区域逐个加载底板及建筑组合，检查空槽位、互斥博物馆、直接授予高阶建筑和两种保留地建筑。
4. 最后在游戏里核实贴地、树林/地貌相交、道路、冬雪/FOW、单位遮挡和建筑触发。没有对应界面截图或引擎反馈时不要标为完成。

Blender 可读离线提取的官方网格做构图；推荐后台 `--factory-startup`，避免用户已装的角色/MMD 插件影响渲染，不改变其个人启动文件。高版本 Blender 是否兼容旧导入插件，要按实际使用的交换格式验证；纯离线网格预览不需要先安装旧版。

## 本轮经验的验证范围

2026-09-25 的 19.47 实作：22 个 AST、2 个改良、3 个区域和 6 个可见建筑差分完成资源链、CIV 往返、静态检查、官方 Cooker 与 Blender 构图预览。AE 桌面控制入口受到本机工具启动错误影响，游戏内状态切换仍待验收。这个结果不能作为以后任何新组合免检的依据。
