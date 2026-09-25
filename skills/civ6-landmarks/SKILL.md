---
name: civ6-landmarks
description: 使用已安装的文明6 SDK 官方几何体组合改良和区域的静态 TileBase AST，建立 Landmarks.artdef、tilebases.xlp、建筑差分和 Art.xml 引用链，经 ModTools 导入 CIV 并运行官方 Cooker。适用于地标模型制作、AST 附件排布和美术资源缺失排查；不用于单位动画、FBX 转换或 HTML UI。
---

# 文明6地标与 AST 组合

目标是可再生成、可验证的地标资源包。AST 是几何实例、材质分组、状态和附件的组合描述，不是模型文件本身。优先复用已安装 SDK 的 `Geometries/*.geo` 与配套 FGX；保留官方材质引用，不把无骨骼的场景网格当作单位模型。

本技能随 ModTools 5.4 使用。复制技能目录可以分享制作方法和示例；`modgen landmark` 命令需要包含该模块的 ModTools 仓库，官方编译还需要用户本地 SDK 与 SDK Assets。

## 开始工作

1. 在仓库内先读 `skills/RULES.md`、`skills/WORKFLOW.md`、`modgen/AGENTS.md`。工具开发另读根 `CLAUDE.md`、路线图和变更日志。简短说明依据与待验证部分。
2. 确定 `.CIV`、绑定的 `.civ6proj`、SDK Assets 根和官方 SDK 根。先备份，保留游戏逻辑、UI、图标和扩展源码。
3. 从 CIV 列出改良、区域和真正可见的建筑。隐藏效果建筑不配模型。区分时代差分与建设/破损状态：取消时代差分不等于删除状态。
4. 设计每种模型的主建筑、地面、装饰、空地和建筑槽位。先贯通一个改良，再做区域。只有确有必要才进行 FGX/FBX 转换、安装其他 Blender 或修改官方工具。

## 按阶段读取

- **找模型、组成 AST**：读 [组合结构与边界](references/composition.md)。用 `landmark catalog` 查看 TileBase 候选，同时查看 `.geo` 的网格、材质组和骨骼。不能只根据文件名判定模型内容。
- **制作区域建筑差分**：读 [Landmarks 与建筑状态](references/landmarks.md)。核对 BaseVariants、BuildingVariants、BuildingSets 和建筑的美术登记。
- **导入、导出、编译及验收**：读 [工具与验证](references/workflow.md)。从 [最小配方](assets/minimal-recipe.json) 开始；里面的游戏实体名须换成已有 CIV 条目的 Type。

## 必须遵守

- 通过工具生成并导入资源包；CIV 保存 `美术.data.landmark_bundle.manifest`，不嵌入原始 XML。改配方后重新 compose 和 build，不靠修改输出工程里的 AST 维持结果。
- 仅使用本地已安装 SDK 作为几何和材质源。本技能不附官方 FGX、DDS 或材质，也不将可读取的文件宣称为开源授权。
- 原始几何引用、网格名、材质组、骨骼名必须存在；附件所指 AST 必须登记在同一 TileBase XLP。发现缺失不能改用一个看似相近的名字糊弄校验。
- Assets、Geometries、Materials 等美术源目录和 XLPs、ArtDefs 不注册为 civ6proj Content/Folder/None；保留磁盘源文件、XLP 内部登记和 Art.xml 引用，由官方目录扫描与 Cooker pantry 读取。Content 会把源文件直接复制到发布目录。
- 保留源 AST 的分组状态。不能对所有状态强制 Visible=true，也不能将建设模型、破损模型和完整模型同时显示。
- 区域底板要为全部建筑预留位置。建筑差分由游戏建筑 Type 触发；只有 BaseVariants 的完整大楼会在空区域提前出现。
- 优先使用官方已有骨骼锚点，保持附件偏移为零。需要自定义偏移时同时核对父模型、骨骼变换、缩放和坐标单位；不能直接把 Blender 中的原始 FGX 数值当成游戏坐标结论。
- `.CIV`、`*.landmarks/` 和工程输出是 Mod 的资源；单 Mod 的探索脚本、截图、日志留在 `modgen_work/` 或独立 Mod 仓库。通用工具、原创测试和技能才属于工具仓库。

## 最小闭环

```powershell
python -m modgen.cli landmark catalog --sdk-assets "<SDK Assets>" --query Sphinx
python -m modgen.cli landmark compose --recipe "recipe.json" --sdk-assets "<SDK Assets>" --out "MyMod.landmarks"
python -m modgen.cli landmark import "MyMod.CIV" --bundle "MyMod.landmarks/manifest.json"
python -m modgen.cli build "MyMod.CIV" --overwrite all --json
python -m modgen.cli landmark verify --bundle "MyMod.landmarks/manifest.json" --sdk-assets "<SDK Assets>" --project "<ModBuddy 项目目录>"
python -m modgen.cli landmark cook --bundle "MyMod.landmarks/manifest.json" --sdk-assets "<SDK Assets>" --sdk "<SDK>" --project "<ModBuddy 项目目录>" --out "modgen_work/art-check"
```

`build` 生成工程源码，`landmark cook` 只编译本资源链并保留日志，不部署 Mod。已有授权足够时继续完成，不在每一步重复索取批准。

## 验收分层

1. **配方与静态引用**：唯一名称、无附件环、存在的骨骼/网格/材质、完整 XLP 和引用链。
2. **编辑器往返**：打开/保存 CIV 后资源包仍在，预览含 AST，重新导出仍有相同文件；补充 Buildings.artdef 不覆盖既有建筑。
3. **官方编译**：本次独立暂存目录产生非空 BLP 和 ArtDef；同时检查返回码、日志和文件。旧文件、MSBuild 成功标记或截图都不能替代它。
4. **外观检查**：正常、未工作、建设、破损、空区域和每种建筑组合；至少两个方向看穿插、漂浮、比例、遮挡与六边形边界。
5. **游戏验收**：AE 的 TileBase 预览与实际地图地形、缩放、建造/劫掠/修复、建筑增减分别核实。Blender 离线图只用于构图，不验证引擎状态机、FOW、雪、道路和贴地。

交付附配方、资源包、工程位置、编译日志及待验收项，明确哪些阶段完成。AE 或游戏暂时不可用时如实记录，不将离线渲染描述为游戏截图。
