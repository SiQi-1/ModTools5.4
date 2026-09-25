# 美术引用链与 Cooker 产物检查

适用：ArtDef/XLP 引用、纸片资源缺失、Cooker 产物语义差异、_MissingArt。

## 分开检查四个阶段

.CIV → ModTools 源工程 → ModBuddy / SDK Cooker 产物 → 游戏加载。modgen build 只生成源工程；检查通过不表示 Cooker 或画面已验证。

ArtDef 的 BLPEntryValue 指向 XLP EntryID，再由 ObjectName 连接资产或纹理。部分名称来自官方 pantry 或依赖包，不能要求一切都在当前 Mod 目录。

## 本地资源检查 assets check

~~~powershell
python -m modgen.cli assets check ModBuddy/工程.civ6proj --json
~~~

读取 Content、动作和本地美术 XML，检查显式文件、模板占位符、标签外说明文字、LeaderFallback 条目、纹理伴随文件、GEO/ENV 相对二进制引用和 Leader_Matte 必要槽位。

本项目有意不将 IMG/Textures 列入 civ6proj Content，不因此误报。虚拟 (Mod Art Dependency File) 交给 ModBuddy，MSBuild 动态引用标为未验证。

BLP 或灯光需要外部 pantry 时列入 unverified，不能凭本地缺文件认定错误。检查器不解析 FGX/WIG 内部结构，不验证所有引擎类和 DLC 依赖。

## Cooker 源与产物比较 art compare

~~~powershell
python -m modgen.cli art compare ModBuddy/ArtDefs Staging/ArtDefs --json
~~~

默认比较 .artdef；可重复传 --suffix .artdef --suffix .xlp 等支持的资源 XML 后缀。只有确有同名 XML 源和产物时才比较；BLP 没有同名源 XML。

| 状态 | 含义 |
|---|---|
| identical | 字节相同 |
| format_only | XML 结构相同，仅格式、注释变化 |
| semantic_change | 属性、有效文本、结构或集合顺序变化 |
| invalid_xml | XML 解析失败 |

比较忽略缩进、换行和注释，保留属性值、有效文本与元素顺序。相同文件仍检查 XML 和 _MissingArt。缺失文件或语义差异返回非零；语义变化不自动等于损坏，Cooker 补默认结构也需核对。

上游记录了 Cooker 清空无法解析的引用或替换为 _MissingArt；不能因编译只报 warning 就忽略。修复回到源声明和依赖，不直接补丁部署产物。

## 报告与边界

命令输出 ok / errors / warnings / unverified / checked。ok 只表示当前静态检查无错误。不要为消除差异自动统一全部 Lua/XML/SQL 行尾或删除注释；先判断内容意义是否改变。

## 来源

[来源 S4](../../THIRD_PARTY_NOTICES.md)：千寻瀑（千与千寻瀑）的 civ6-art-reference/reference/chain-map.md、cook-layer.md、artdef_sync_check.py，以及 civ6-modding/tools/verify_mod_package.py。吸收区分格式差异、依赖与实机验证的方法；以 XML 结构比较、显式目录和路径边界重新实现，未复制本机路径与自动修复流程。
