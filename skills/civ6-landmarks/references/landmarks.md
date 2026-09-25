# Landmarks、实体绑定与建筑差分

## 完整引用链

```text
CIV 资源包声明
  -> Assets/自定义.ast（仅引用官方几何和材质）
  -> XLPs/tilebases.xlp：EntryID = ObjectName = AST 的 m_Name
  -> ArtDefs/Landmarks.artdef：TileBase BLPEntryValue
  -> Improvements.artdef / Districts.artdef：Landmark/Xref
  -> 项目 Art.xml：Landmarks consumer + TileBase library + SDK dependencies
  -> 官方 Cooker：landmarks/tilebases.blp + 编译后的 ArtDefs
```

AST、XLP 和 Landmarks 中的名字必须逐段一致。只创建 Landmarks、不改实体的 Landmark/Xref，游戏仍会显示旧模型。只建 AST、不登记 XLP，附件也不会自动加载。

Assets、Geometries、Materials、Textures、Animations、Behaviors、DSGs 等美术源目录，以及 XLPs、ArtDefs，均不注册为 `.civ6proj` 的 Content/Folder/None。源文件仍保存在工程的标准目录：官方 Civ6.targets 扫描 ArtDefs/*.artdef、XLPs/*.XLP，Cooker 通过 `--pantry <ProjectDir>` 读取 AST、几何和材质引用。Content 会被直接复制进发布目录，错误登记会把可编辑源文件一并发布。XLP 内的资产登记及 Art.xml 引用仍必须完整；磁盘源码、Cooker 输入和发布包文件是不同层次。编译后的 Platforms/.../BLPs 不属于这些源目录，不受过滤影响。

本规则已按本机官方 Civ6.targets 的 CheckCookAssets/CookAssets/Build 逻辑及用户确认修正（2026-09-25）；此前“AST 纳入 Content”的说明是错误的。

## 改良

Landmarks 根集合为 `Landmarks`，每项通常包含 FlattenTerrain、RotationType 和子集合 Eras。单套模型用 Tag_Era=DEFAULT、Tag_Culture=DEFAULT、Tag_Appeal=ANY；Asset 指向自定义 TileBase。

Improvements.artdef 的 Improvement 条目保留可用的官方战略视图/音效，通过 Landmark 子集合的 `Xref` 引用新 Landmark 名。当前工具要求所选官方模板含且仅含一个对应 Xref，否则拒绝错误绑定。

## 区域

Landmarks 的区域条目位于根集合 `Districts`，不是根 `Landmarks`。需要三个子集合：

| 子集合 | 功能 |
|---|---|
| BaseVariants | 根据 Set_HeroBuildings 和时代/文化/吸引力选择地面及固定部分 |
| BuildingVariants | Tag_HeroBuilding 对应某个游戏建筑 Type，选择其独立 AST |
| BuildingSets | 每个集合列出已建成建筑的 ArtDef 引用 |

默认空区域使用 EMPTY 集合。当前生成器为最多 6 个建筑生成全部子集，兼容直接授予高阶建筑的存档；这只定义美术选择，不修改建筑前置或互斥条件。两个互斥博物馆在正常规则下不会同时建成，若其他 Mod 强行授予两者，可能同时叠加模型，应单独验收。

一套时代模型仍要定义每种建筑出现/消失的差分。底板可相同，但必须给各个集合提供有效的 BaseVariant；建筑模型不应全部写进底板。含永久隐藏效果的内部建筑不进入 BuildingSets。

Buildings.artdef 中的 `AffectsDistrictBuildingSet=true` 是建筑参与集合切换的关键。SDK 未包含的新资料片建筑可能没有可编译的注册条目，应补充对应建筑 Type 的最小美术字段。工具生成的补充 Buildings.artdef 与当前 Mod 的建筑条目合并，不用整份文件覆盖。

## 时代、DLC 与消费者

- 单套模型不需要为每个时代复制相同条目，DEFAULT 是明确的回退选择。
- 来源模型的 SDK pantry 决定依赖。Expansion2.Art.xml 依赖 Shared，**并不等于声明 Expansion1**；使用 Expansion1 的模型需保留对应 ID。
- 生成器从实际 SDK Art.xml 读取 ID，导入到 CIV 的美术配置，导出时保留全部已有和新增依赖，不能固定输出一个资料片。
- TileBase library 的包名与 BLP 的目录一致；Landmarks consumer 要引用 Landmarks.artdef 并声明 TileBase。实体/Buildings 的相关消费者也沿用官方规则。
- 不凭素材路径推断所有拥有基础游戏的玩家都具备全部 DLC 资源。项目依赖和目标玩家环境应一致。
