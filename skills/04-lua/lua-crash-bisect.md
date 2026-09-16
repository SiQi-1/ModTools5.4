# lua-crash-bisect — 无日志开局崩溃二分排查（0054 实录）

> 适用：开局（建图/首回合）即崩、Database.log/Lua.log 均无、控制变量确认"仅本文明/领袖崩溃"。
> 说明：SQLite 层面的模拟加载（临时库 executescript）**看不到**游戏侧引用校验与引擎求值崩溃，
> 最终以游戏内二分实测为准；先例对照（0039~53 已出货源码）用于收敛新颖组合。

## 一、先判定崩溃层

| 现象 | 结论 |
|---|---|
| 换任意其它领袖不崩、仅本文明崩 | 崩溃在"本文明特有数据/机制初始化"，与全局 SQL/Lua 加载无关 |
| 主菜单即崩、与选谁无关 | DB/图标/美术加载层，走 SQL 门禁（见 05-modtools-civ/pipeline.md 落盘门禁四件套） |
| 加载画面崩 | 优先怀疑领袖美术（LoadingInfo 贴图/.tex/XLP） |
| 能进图、首回合崩 | 优先怀疑首回合 Lua（如开局解锁）或该文明被动 modifier 求值 |

## 二、二分矩阵（一次只动一个变量，逐级向内）

1. **整文件停载**：从 .civ6proj UpdateDatabase 摘除目标 SQL（或 XML 注释该行）→ 不崩 = 该文件内容
2. **挂载全注释**：`/* */` 包住所有 Trait/UnitAbility/District/Policy/Project 挂载语句、定义保留 → 不崩 = 挂载触发；仍崩 = 定义解析/注册本身（如 DynamicModifiers 自定义行、Modifiers/Arguments 数据行）
3. **Lua 全关**：把 GP/UI 的 `Initialize` 函数体与 `LoadGameViewStateDone.Add` 逐行 `--` 注释 → 不崩 = Lua 事件链（保留函数定义便于恢复）
4. **行级半量注释**：在 Modifiers/ModifierArguments 大 INSERT 内用 `--` 注释一半行 + 对应参数行；**注意末行分号**：被注释行自带尾逗号随行消失、语句合法；若语句末行（`);` 行）被注释，必须把 `;` 迁移到上一激活行（行内尾注释感知：用 `';' in line.split(' -- ')[0]` 判语句结束）
5. 每轮只改一处，标记 `[二分 R*]` 注释说明，实测后决定恢复/继续

## 三、踩坑与佐证（0054 实录）

- **虚空接口**：`pCulture:UnlockGovernment()` CSV 有记录、工坊有用法，但官方源码零使用 → 首回合调用直接开局崩溃且无日志；"看逻辑不会崩"会被这类接口推翻。处置：换同系出货实证写法（政体解锁 → 完成前置市政 `SetCulturalProgress=GetCultureCost`，见 lua-gp-resource.md）
- **Cache DB 佐证**：`Cache/DebugGameplay.sqlite` 里本 Mod 行数>0 = 该局加载已成功（崩溃在更后阶段）；无扩展启动的 schema 会缺 XP2/Moments 表——先确认测试局环境
- **加载器引用校验**：`UnitAiInfos.AiType` 等引用列在模拟加载中不报错、进游戏才报 `Invalid Reference`；二分前先对照 DB 查表
- **恢复纪律**：二分改动必须可逆（注释块内保留原文或使用 `_preview54_check` 等阶段快照整体重建）；全部结束后做一次全量门禁复验
