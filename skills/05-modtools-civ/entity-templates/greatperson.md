# greatperson — 伟人条目（section「伟人」）

> list section。**当前所有样例工程均为空**（32~53.CIV / Mujica / U14 均无伟人条目），本模板以工具源码行为为准：
> - `great_people_editor.py`：伟人分**激活类**与**巨作类**；每个伟人个体含 `Name`（中文名）、`GreatPersonClassType`（伟人类型）、所属文明、`UnitType`、出生效果等
> - 伟人类型（GreatPersonClasses）可**从游戏库导入**（工具按钮「导入伟人类型」），含 `GreatPersonClassType`/`UnitType`/`Name`/`DistrictType`/`ActionIcon`
> - 伟人个体出生/行动效果 = 指向「修改器」section（`GreatPersonIndividualBirthModifiers`/`GreatPersonIndividualActionModifiers` 挂载链）
>
> 内容知识桥接 `01-core-tables/greatperson.md`。

## 首次建伟人时的做法

1. 在工具中「新增伟人个体」→ 看工具生成的结构（本模板随首个真实样例补充键清单）
2. 伟人类型优先从游戏库导入（`GREAT_PERSON_CLASS_*`，DB 验证）
3. 出生/行动效果走「修改器」section，owners 挂伟人表链（陷阱 12）

## 出口检查

- [ ] GreatPersonClassType 在游戏库存在（`SELECT * FROM GreatPersonClasses`）
- [ ] 效果挂载链完整（Birth/Action Modifiers 表有行）
- [ ] 巨作类伟人的巨作槽/类型在工具表单配置（`building_greatworks` 段参考）
