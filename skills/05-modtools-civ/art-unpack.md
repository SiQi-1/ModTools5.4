# Civ6 美术解包、复原与产物验收

适用：BLP / CIVBIG / SHARED_DATA 解包、FGX / GEO 重建、领袖蒙皮、预乘纹理回打包、pantry 同名遮蔽、Cooker 假成功。制作新的静态地标仍先用 [地标技能](../civ6-landmarks/SKILL.md)，本篇用于资源证据和排错，不取代该工具。

来源是千川白浪的 Civ6ArtUnpack_Handover.zip（2026-09-17 移交包），[来源编号 S7](../../THIRD_PARTY_NOTICES.md)。本项目已核对文档与部分代码，并用本机官方 Civ6.cfg 验证类注册结构；没有在本轮复现全量 BLP 解包、领袖重建或其成功率。

## 先分清五种完成状态

| 状态 | 必须提供的证据 |
|---|---|
| 能定位或列出 | 实际包、DLC/路径、记录种类、名称、偏移和长度；找到字符串不等于找到可解载荷 |
| 能解码 | 解出实际数据，并与独立已知资源比较；不能只生成同名空壳 |
| 能重建 | 从明确的导出数据生成源资产；说明模板、骨架、UV、切线和未知部分 |
| 能编译 | 本次源参与了编译，产物包含目标对象；排除 SDK 同名 pantry 遮蔽及旧产物 |
| 游戏可用 | 实际几何、材质、动画、光照与触发在目标游戏中成立 |

ModBuddy 显示 Build succeeded、Cooker 返回 0、BLP 非空、文件长度相同，都不能单独证明复原正确。检查完整日志及产物内部条目，再按目标比较几何或像素；字符串 grep 也只能证明有文字，不能证明对应网格有效。

源、重建、Cooker 产物和游戏部署各保存身份、散列及验收结果。重建阶段若又从原始包复制全部字节，最终 SHA-256 相同只能说明直通，不能说明已经解码和重建。

## 本项目能直接使用的检查

~~~powershell
python -m modgen.cli assets check MyMod/MyMod.civ6proj --json
python -m modgen.cli assets check MyMod/MyMod.civ6proj --cooker-config "SDK/AssetModTools/Cooker/Civ6.cfg" --json
python -m modgen.cli art compare MyMod/ArtDefs Cooked/ArtDefs --json
~~~

第一条核对现有资源和 ARTDEF/AST 的 BLPEntryValue 引用。第二条增加来自指定官方配置的类核验：

- XLP 的 m_ClassName 查 m_XLPClasses，不与 AST 或 GEO 共用一张类表。
- ASSET / TEXTURE 类型的 XLP 按 m_ObjectName 找本地 AST / TEX，校验其类是否在 m_AllowedClasses 中；m_EntryID 是外部引用名，两者可以不同。
- AST 的 m_ClassName 查 AssetClass，模型 m_GeoName 连接 GEO，再按 m_AllowedGeoClasses 验证几何类。
- GEO / TEX 分别查 GeometryClass / TextureClass。SDK 中同名的 AnimationClass 等不覆盖这些类别。
- 外部 pantry 才有的对象列为 unverified；不能把没有扫描的外部库判成文件缺失，也不能默认它有效。
- 尚未覆盖的 XLP 实体类型、FGX 网格/骨架、实际 pantry 优先级及编译后 BLP 明确保留为未验证。

以所用 SDK 配置为准，不把固定类数量或作者机器的映射常量带入规则。本轮本机配置确认 LeaderFallback 允许 Leader_Fallback，UITexture 允许 UISliceTexture / UserInterface；误用 UI 贴图类可能被 Cooker 剔除。合法 DecalGeometry 也不能无条件禁止，但不能因为它排在允许列表第一位就拿来重建普通实体几何。

类校验只读，不选择类、不改源文件、不执行 Cooker；报告和退出码沿用 [检查器契约](../../modgen/AGENTS.md#资源与发布产物检查)。

## BLP 与名字的证据边界

- 区分容器头、自描述区、记录族和载荷。上游不同阶段描述了 0x70 扫描、72/104 等记录布局；不能将某个步长当所有 BLP 记录的统一格式。
- 同名记录可对应不同缓冲；不能按名字只留第一项。还要记录包路径、DLC、记录类型、偏移、尺寸，区分顶点/索引和共享池。
- 不把 SkinnedVB、AuxVertData、ResultVB、AdjacencyGraph、SharedFinIB 等内部缓冲名直接当 XLP 资产名。
- EntryID、ObjectName、文件 stem 和原始包内名称分别保留；名称可能含路径。磁盘安全命名需保留映射，不能洗白后再按名字错误地判缺。
- 同 stem 的 LeaderFallbackImages、light_rigs 等可能来自不同 DLC。输出和缓存按来源相对路径/DLC 隔离，避免累积或覆盖。
- 统计覆盖率要说明分母是包、资产、子网格、三角还是已解释载荷。源资料的 99.07% 等是作者某次样本和判据的历史结果，不是本项目承诺。

## 几何、蒙皮与重新烤制

上游较新的 LEADER_GEOMETRY_SPEC 与 multimesh.py 描述按子网格处理 SkinnedVB / AuxVertData / ResultVB，记录了 80 / 36 / 8 字节流与 8 个骨骼影响。它们与较早 README 的“领袖不可用”或“合并为单网格”不一致，必须连同来源版本阅读，不把旧假设用于新资产。

这些是待目标样本复验的技术线索，不能直接推成所有资源都需 152 字节 FGX 顶点或所有 UV 池都按同一种方式切分。逐子网格核对索引范围、位置、法线/切线、权重、骨架、材质槽和 UV；缺 UV 时可记录几何已解，不能宣称完整外观复原。

GEO 的网格声明要与 FGX 实际网格对应。编译器可能按接缝拆分/合并顶点，因此顶点数相同不是充分判据；同样，三角数相同也不能证明位置正确。点云容差匹配、索引/拓扑、材质绑定和视觉对照各有作用，NaN 与量化误差需单独记账。

验收自建资源时，给资源唯一测试名，记录实际使用的本地文件和外部依赖，做最小对照构建以排除 pantry 同名遮蔽。按包隔离 Cooker 进程和输出有利于定位崩溃；遇到中文路径编码问题使用独立 ASCII 暂存，不改用户正式路径。

## 纹理与回打包

上游将预乘 RGBA 载荷与 PNG 视图分开保存：低 alpha 的反预乘可能丢失信息，预览 PNG 不一定能重建原始字节。不要因此给本项目普通 HTML/PNG 源图自动预乘；原始载荷的域、格式和 mip 链必须先确认。

字节一致只适用于已明确可逆的范围。记录 mip 数量、每级尺寸、压缩/未压缩格式和色彩空间；不能用一个纹理族的不可逆结论覆盖另一个族。BC5 法线等需要在正确的向量/着色语义下比较，普通 RGB 相似度不能证明切线空间正确。

回打包验收分开报告实际重建载荷、可再生对齐/填充、自描述骨架直通和未知间隙；0% 载荷覆盖即使散列一致，也不是完整解包成功。

## 使用原移交包时

原包作为用户本地参考保留，不是本仓库自动安装的依赖。按其路径移植清单检查游戏、SDK、SDK Assets、FBX 模板及工具路径，只在隔离工作副本中适配必要入口；不全局替换仓库或 SDK，也不盲目 import 批处理脚本。

已静态核对 blpkit/cli.py 的 header、entries、meshes、obj、fgx、chain、sweep、fgxsec、selftest、env 入口。原包需要自己的 NumPy/Pillow 及部分外部工具；本项目 assets check 仍是纯标准库。完整依赖和执行副作用按具体入口检查，本轮没有执行原包二进制。

已确认的移交冲突：

| 冲突 | 本项目处理 |
|---|---|
| 文档提到 batch_extract_leaders.py / batch_cook_pantry_leaders.py，包内缺失 | 不发布这些命令为可用能力；其他同名近似脚本不视为替代 |
| SESSION_STATE 记 extract_leader_submeshes(blp_path) | 实际函数参数是 blp_bytes, descs；引用代码签名 |
| README、GOAL、SESSION 对领袖/动画和完成率前后不同 | 保留时间与证据级别；有提取代码不等于整条重建/游戏链已验证 |
| 源资料曾建议把 XLP 列入 civ6proj Content | 按本项目现行美术源目录与 SDK targets 契约；不导入旧临时规避方案 |
| 上游复原实验禁止复制 SDK 资产 | 是其“独立复原”验收条件，不改成本项目所有 Mod 制作的一般禁令；引用和分发仍遵守各自许可 |

Lua 与玩法旁支仍遵循本项目原规则：LuaEvents 同环境可用、不可直接跨 UI/GP；Events 支持 UI/GP；GameEvents 属 GP，显式桥接需注明。不会因新资料覆盖这些已确认约定。

## 来源与本轮验证

作者：**千川白浪**（用户提供署名）。参考包内 README_移交说明.md、Hook/SESSION_STATE.md、GOAL_ASSETS.md、LEADER_GEOMETRY_SPEC.md、blpkit/README.md、cli.py、multimesh.py，以及经验库的类名空间、TEX/XLP、回打包、命名、Cooker 与工程还原笔记。

未发现包级 LICENSE/COPYING；本项目重新组织知识并独立实现检查，不复制其 blpkit、Oodle/Granny 辅助程序、.git 历史、索引库存或游戏资产。包散列、采用范围与证据见 [来源 S7](../../THIRD_PARTY_NOTICES.md) 和 [整合记录](../../docs/COMMUNITY_SKILL_INTEGRATION.md)。
