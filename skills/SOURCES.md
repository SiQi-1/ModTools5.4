# 资料依据与可用查询

## 当前工具

- [modgen 契约](../modgen/AGENTS.md) 与 `python -m modgen.cli --help`：命令入口。
- [实体 schema](../modgen/schemas/entry_schemas.json)、[修改器 schema](../modgen/schemas/modifier_schemas.json)：字段与参数；schema 有版本边界，不能替代游戏语义验证。
- [工程模型](../ModTools_5_4/project/civ_project.py)、[UI图标](../ModTools_5_4/project/ui_icons.py)、[纹理](../ModTools_5_4/project/ui_textures.py)、[自定义文本](../ModTools_5_4/project/custom_text.py)：当前实现。

## 类型与枚举

旧技能引用的枚举导出文件没有随仓库分发，链接统一指向本节。按被引用的类型查实际列值，先查表结构，不能假设类型名就是表名。

```powershell
python -m modgen.cli query "PRAGMA table_info(Units)"
python -m modgen.cli query "SELECT DISTINCT PromotionClass FROM Units"
python -m modgen.cli query "SELECT Type, Kind FROM Types WHERE Type='UNIT_WARRIOR'"
python -m modgen.cli query "SELECT ModifierType, CollectionType, EffectType FROM DynamicModifiers LIMIT 10"
python -m modgen.cli search "城市产出"
```

`DebugGameplay.sqlite` 是目标环境的运行缓存，包含其他 Mod；查得到只说明当前环境有记录。原版 ModifierType 来源查 [原版快照](../ModTools_5_4/data/vanilla_modifier_types.json)，需要注册的自定义类型见 [修改器指南](05-modtools-civ/modifiers.md)。其他枚举可查官方定义与对应表；数据库未配置时明确缺少验证来源。

## 文本与图标

- LOC：`python -m modgen.cli loc LOC_UNIT_WARRIOR_NAME`，读取已配置文本库，解析引用链。
- 字体图标：[注册表](../ModTools_5_4/data/font_icons_registry.json)；配色：[标准色](../ModTools_5_4/data/standard_colors.json)。图标不靠猜数据库表。
- 自定义 LOC、UI图标、背景纹理见 [美术与文本指南](05-modtools-civ/ui-assets.md)。

## Lua 与控件

先读 [Lua 规范](04-lua/code-style.md) 和 [控件参考](04-lua/lua-xml-controls.md)，再从 [Lua 索引](04-lua/INDEX.md) 找接近的已记录模式。API/事件需对照目标版本官方 Lua/XML 调用点；区分 GP/UI 环境。没有证据时标为待验证并做最小测试，不能虚构接口。

## 历史资料

资料中的个人 Mod 编号、工坊 ID、旧外部目录是溯源说明，不是本仓库可执行依赖。旧导出快照、DLL 类型清单、查询脚本未随包提供，不能根据这些路径调用不存在的工具。当前可用入口为上面的 CLI、随包数据及本地已配置游戏文件。

历史生成器与重复草稿隔离在 [维护归档](../tools/legacy_skill_builders/README.md)，不参与知识检索；它们可能包含旧绝对路径，禁止直接运行来覆盖现行资料。需要再生成时，应先迁移脚本并加入输出差异校验。
