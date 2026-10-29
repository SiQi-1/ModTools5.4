# 地标 AST 与 Landmarks 资源包

> 受众：制作地标/静态 TileBase 资源包的 AI/开发者 ｜ 何时读：使用 landmark catalog/compose/import/verify/cook 时 ｜ 适用版本：ModTools 5.4

> 本文自 [modgen/AGENTS.md](../../AGENTS.md) 拆出；本通道只读此篇，通用硬规则仍以 AGENTS.md 为准。

## 地标 AST 与 Landmarks 资源包

本通道生成静态 TileBase，美术 XML/AST/XLP 由工具写出；不在 CIV 主内容手写 XML。共享核心是 `ModTools_5_4/project/landmarks.py`，CLI 是 `modgen/landmark.py`。完整制作技能：[civ6-landmarks](../../../skills/packages/civ6-landmarks/SKILL.md)。

```powershell
python -m modgen.cli landmark catalog --sdk-assets "<SDK Assets>" --query Sphinx
python -m modgen.cli landmark compose --recipe recipe.json --sdk-assets "<SDK Assets>" --out MyMod.landmarks
python -m modgen.cli landmark import MyMod.CIV --bundle MyMod.landmarks/manifest.json [--dry-run] [--replace]
python -m modgen.cli landmark verify --bundle MyMod.landmarks/manifest.json [--sdk-assets "<SDK Assets>"] [--project "<工程目录>"]
python -m modgen.cli landmark cook --bundle MyMod.landmarks/manifest.json --sdk-assets "<SDK Assets>" --sdk "<SDK>" --out workspace/scratch/art-check [--project "<工程目录>"]
```

- 配方 schema 与字段见[工具契约](../../../skills/packages/civ6-landmarks/references/workflow.md)；根 format=`MODTOOLS54_LANDMARK_RECIPE`。主内容 Type 必须先存在于 CIV，资产名与附件字段严格校验。
- `compose` 静态复用 SDK TileBase 的实例/材质组/可见状态，清除源附件和动画行为，再创建本地附件；不支持任意动画 AST 或单位骨骼转换。
- 配方可声明 local_pantry/local_files，纳管已经转换好的 AST/GEO/FGX/MTL/TEX/DDS；只复制清单文件，验证本地数据文件与材质贴图引用，二进制原样导出。该命令不执行 Blender/CN6 转换或处理动画。
- 区域 binding 可选 building_sets（建筑 Type 数组的数组），按已核对的前置/互斥与实际授予逻辑列可达阶段；必须含 []，无重复/未知项，每个声明建筑至少使用一次。生成器只输出这些集合；base_variants 不得引用被排除集合。顺序无关且输出稳定；省略/null 为旧配方保留全子集，新设计应显式填写。互斥建筑可共用资产与槽位，不假设异常授予来扩大模型组合。
- 区域 binding 可选 base_variants（buildings/asset 列表）：按完整建筑集合匹配，顺序无关、空数组代表空区域；未声明集合回退 base_asset。拒绝重复/未知建筑、重复集合和缺失资产。SDK 同名 GEO/MTL/TEX 仅在源及直接数据文件逐字节相同后合并，优先 Shared；同名 AST 仍需明确路径。
- 资源包含 AST、Landmarks、TileBase XLP、可选补充 Buildings、本地模型与材质贴图、recipe 与 manifest 散列。CIV 只存 `workspace.美术.data.landmark_bundle.manifest` 绝对路径；当前一个 CIV 一个包。
- `import` 校验完整批次后保存一次并备份 CIV，自动设置 need/source map、Landmarks/TileBase 标记与来源 SDK Art ID；不同包切换需 `--replace`。移动源目录后重新导入，当前不自动重定位。
- GUI 导入/导出保留声明；预览有 AST 组。工程总览允许 AST；生成 Assets 等标准美术源目录，但不登记为 civ6proj Content/Folder/None；更新既有工程时清除这些目录的旧注册，磁盘源文件保留，仍由目录扫描与 Cooker pantry 读取；补充建筑与已有 Buildings 合并。
- 包文件散列变化会阻断导出，调整应回到配方重新 compose；依赖或绑定变化后再次 import。`validate` 同时检查资源包来源存在且散列一致。
- `verify --project` 检查源文件、引用链和错误的美术源目录注册；不要求 AST Content。`verify` 不调用 SDK 二进制；`cook` 需要 Windows 官方 Cooker，使用新英文临时目录解决中文路径问题，只编译地标资源链。两者均不是游戏内视觉验收。
- Mod 源 `*.landmarks/` 与 CIV/扩展目录一起保留在本地或独立 Mod 仓库；通用示例和测试不包含官方几何/纹理文件。
