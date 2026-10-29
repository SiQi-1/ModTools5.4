# lua-gp-resource — 非战斗类 GP 函数

> 本文件已按主题拆成分册（每册 ≤32KB），保留为索引：按触发条件选读对应分册，不要整篇读取。

> 总览：基于 Siqi_Leaders_0032（最新标准）和 19.47 Mod 提炼。GP 环境专用，所有函数均需在 Scripts/Import 中运行。 ---

## 分册清单

| 分册 | 覆盖内容 | 触发条件 |
|---|---|---|
| [lua-gp-resource-yield-production.md](lua-gp-resource-yield-production.md) | 产出、ChangeScience / ChangeCulture / ChangeGold / ChangeFaith — 一次性产出修改、ChangeProduction — 一次性生产力修改（指定城市或全部城市）、FinishProduction — 立即完成当前生产任务、OnGoldProduction — 金币购买生产力（凝光核心：1:2 比率 + 总督返还 20%）、游戏速度倍率（固定写法）、AddWonderProgress — 按百分比推进奇观建造、生产力/奇观、闲云：奇观建成 → 其他在建奇观推进 20%、闲云：派遣总督 → 奇观 +80% 进度（2 回合冷却）、大工程司：加速区域重建（拆除→立即重建）、桃金娘：无生产任务时奖励产出 | 改产出、生产力、奇观时 |
| [lua-gp-resource-gp-building-modifier.md](lua-gp-resource-gp-building-modifier.md) | 伟人、ChangeGreatPeoplePoints — 修改指定类别伟人点数、Siqi_AddGreatPeople — 赠送指定伟人个体到首都、击杀单位 → +5 大将军点数（魈基础）、建筑、GrantBuilding — 授予建筑（指定城市或首都）、RemoveBuilding — 移除建筑、七天神像形态切换（钟离）、修改器、AttachModifierByID 动态附加（Doloris 能力购买）、AttachModifierByID 计时脱手（魈 R1：4 层槽位，15 回合过期剥离）、AttachModifierByID 计数触发（凝光 L2：每 7 条商路 → +1 商人 +1 容量）、分期扣款系统（摩拉克斯馈赠） | 改伟人、建筑、修改器时 |
| [lua-gp-resource-tech-city.md](lua-gp-resource-tech-city.md) | 科技市政、获取已完成尤里卡但未研究的科技列表、判断某时代科技是否全部已触发尤里卡、赠送某时代全部未完成科技、判断某时代市政是否全部已触发鼓舞、赠送某时代全部未完成市政、解锁政体（完成前置市政，稳定写法）、HasTech — 检查玩家是否拥有某科技、HasCivic — 检查玩家是否拥有某市政、城市状态 / Property、城市宜居度计算（GP 精确版）、宜居度转二进制属性（桃金娘 / 苏苏洛共用）、星辉系统：消耗星辉 → 触发鼓舞/尤里卡、摩拉产出系统核心：UI 计算 → GP 写 Property、BroadcastRefresh — 广播刷新（GP → UI 通知） | 改科技市政、城市状态与 Property 时 |
| [lua-gp-resource-plot-build-count.md](lua-gp-resource-plot-build-count.md) | 地块购买、金币购买地块（Wuxian / 通用）、信仰购买地块（0026 / FAITH_BUY_PLOTS 通用）、建造/生产加强、区域瞬间完成（0015：首个专业化区域免费秒建）、建造单位翻倍（0028：特定区域所在城市造战斗单位→额外送一个）、`Events.CityProductionCompleted` — `iConstructionType` 值、`Events.CityMadePurchase` — `purchaseType` 值（`EventSubTypes` 枚举）、区域完成时赠送最低级建筑（0028）、计数/里程碑系统、改良计数里程碑奖励（0026：农场/种植园分别计数，按 3/6/9/12/36 档发奖）、城市资源种类追踪（0026：奖励资源每类仅第一份计入区域产出加成） | 地块购买、建造生产、计数里程碑时 |
| [lua-gp-resource-economy-trigger.md](lua-gp-resource-economy-trigger.md) | 消费返利系统、金币消费返利 20%（0026：总督 R2 晋升城市购买时自动返还 20% 金币）、科技市政操作、直接完成指定市政（0026 / 通用）、直接完成指定科技（通用）、尤里卡触发时抽奖（0024：30% 概率触发随机鼓舞/尤里卡）、征服、城市征服奖励（0034：金币按区域数量+减少人口保底）、奇观/伟人触发、奇观完成随机奖励（0028：尤里卡/鼓舞二选一 + 随机 100 伟人点）、累计/阈值系统、灵值累积系统（0024：每回合累加资源，满 200 触发进度+重置）、多源进度追踪系统（0024：伟人/宗教/黄金时代/项目多来源累计，26 点胜利）、项目完成奖励、工程项目完成 → 一次性 AttachModifierByID 多重奖励（0027）、首都切换（0018：项目完成后将当前城市设为首都）、城市生产状态追踪、生产队列变更时写地块 Property（0019：标记城市是否正在执行目标项目）、城市数据、城市主流宗教获取（0027/0028 Support：GP 端通用）、玩家科文进度系数（0027/0028 Support：1~10 的动态系数）、自定义资源/货币系统、Game Property 自定义余额系统（0015 香韵：玩家独立余额）、工人创建/移除地貌资源（0015：消耗自定义资源创建 Feature/Resource） | 消费返利、征服、奇观触发、阈值系统、自定义货币时 |

## 使用建议

先按任务关键词在上表定位分册，只读命中分册；参数表在分册内，不要一次加载全部。原文件的目录/分组索引已由本表替代。
