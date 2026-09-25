# AST 组合结构与边界

## 依据与检索

优先检查用户安装的 SDK Assets：`Civ6/pantry`、`Civ6/DLC/Shared/pantry`、`Expansion1/pantry`、`Expansion2/pantry`。AST 位于 Assets，几何描述位于 Geometries，材质位于 Materials。查询：

```powershell
python -m modgen.cli landmark catalog --sdk-assets "<SDK Assets>" --query Museum
```

catalog 返回来源相对路径、几何实例和附件数量。同名资源有多个候选时使用精确 SDK 相对路径，不按扫描顺序选第一个。SDK 根以外的路径和 `..` 被拒绝。

可以学习已有 Mod 的排布和 Landmarks 写法，但先追踪其几何、材质、动画与 XLP；不能将另一个 Mod 的自定义部件当成官方资源。已有示例也可能有 `Lankmarks.artdef` 等拼写错误。

## 几何与材质

`.geo` 中应检查：

- `m_Meshes/Element/m_Name`：真实网格名；每个网格下 `m_Groups` 是材质分组。
- `m_Bones`：附件可选的骨骼名。AST 的实例名、几何名和骨骼名不是同一个概念。
- `m_DataFiles`：配套 FGX 必须存在。只引用 `.geo` 名并不能补救缺失的二进制模型。
- `m_ClassName`：地标通常是 LandmarkModel；单位及其动画不在此工作流内。

AST 的 `m_GeometrySet/m_ModelInstances` 保留几何和每个材质组的状态表。`m_GroupStates` 下对应的参数包括 Material、FOWMaterial、BurnMaterial、SnowMaterial、Visible 等。不要把模型的唯一材质名套到全部网格上。

`modgen landmark compose` 以官方 TileBase AST 为静态源，保留实例、材质和组状态；去掉旧附件、DSG、动画/VFX 时间线，再按配方创建本地附件。此流程不适用于需要动画行为的喷泉水流、机械或单位；静态喷泉模型本身可以使用，但不能声称保留了水流特效。

## 附件

每个附件必须同时提供：

- 本包中的 `asset` 名；生成 BLPEntryValue，Class/Library=TileBase，XLP=`tilebases.xlp`，Package=`landmarks/tilebases`。
- 父 AST 的 `instance` 名及该实例几何中的 `bone` 名。
- `position` 三维偏移、`rotation` 三维旋转、正的 `scale`。配方旋转沿用 AST 的弧度数据；复制参考布局时不要把弧度当度数。

生成器使用 `ConnectionType=NONE`、`TerrainFollowMode=Pivot Height`、`Cull Mode=PERMANENT`，适用于固定装饰。道路接口、水岸装饰、资源条件化附件应另查官方写法，不强塞进当前有限 schema。

优先选官方锚点，让 `position=[0,0,0]`。旋转和缩放还会叠加骨骼本身的变换；同样的三维数值在不同锚点上未必得到相同世界位置。不要在 `m_ModelInstances` 中发明 XML 位置字段。

## 状态与遮挡轮廓

Worked、Unworked、Pillaged、Construction、Unbuilt 是状态，不是时代。原有废墟和建设网格的 Visible 表必须保留。某些奇观组件在五种状态都可见，可以通过 `hide_states` 只限制 Construction/Unbuilt，避免主体提前出现；该字段不会强制打开原本不可见的网格。

官方底板若给出 Obstruction Profile，应保留原有合法轮廓。骨骼型空底板可能没有三角网格，强制自动生成 OB 会得到空轮廓警告。添加超出原轮廓的大体积部件还需要在 AE/游戏中验证遮挡、单位穿插；Cooker 无报错不意味着碰撞轮廓合适。

`hide_geometry` 只隐藏源实例的材质组，常用于保留锚点的组合载体；它不自动隐藏附件，也不替代父子状态验收。

## 已遇到的 SDK 格式问题

- 部分 Expansion1 XML 用 `AssetObjects::` 名称并带文件末尾 NUL。读取器只将此已知名称转为 `AssetObjects..` 并去掉末尾 NUL；不修改 SDK 原文件。
- 某些官方 AST 残留已经从 `.geo` 删除的材质组。默认报错；确认来源后，配方可显式 `drop_stale_groups=true`，按实际网格/组删除残留绑定。不得关闭整个验证器来绕过问题。
- `Materials/FOW/DefaultMaterial.mtl` 是子目录资源，不能把斜杠一概理解为 SDK 根相对路径。精确带后缀的相对路径和库内逻辑名有不同用途。
- FGX 的原始单位、根变换和模型锚点都需要核对；离线导出的网格位置不自动等于 AST 的游戏空间。比较库中的完整组合，再做小范围调整。

实际核实样本包括官方 IMP_Sphinx、IMP_Open_Air_Museum、DIS_THR 系列及静态奇观组件。适用范围是静态 TileBase 组合，不能推广为所有官方 AST 的通用转换器。
