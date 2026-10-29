# 原生相邻与文本图标检查（adjacency / text-icons）

> 受众：配置相邻加成或效果描述图标的 AI/开发者 ｜ 何时读：涉及原生相邻桥接表、adjacency 命令或 description 图标时 ｜ 适用版本：ModTools 5.4

> 本文自 [modgen/AGENTS.md](../../AGENTS.md) 拆出；本通道只读此篇，通用硬规则仍以 AGENTS.md 为准。


```powershell
python -m modgen.cli adjacency list --ruleset expansion2
python -m modgen.cli adjacency show DISTRICT_CAMPUS --ruleset expansion2
python -m modgen.cli adjacency check 工程.CIV --ruleset expansion2
python -m modgen.cli text-icons format --role description --text "+2食物、+3金币"
python -m modgen.cli text-icons check 工程.CIV
python -m modgen.tools.extract_vanilla_adjacencies --game-dir "游戏目录"
```

这些命令输出 JSON，不写工程。adjacency 的 base/expansion1/expansion2 核心规则集来自随包官方 XML 快照；show 返回原规则详情和可复用的 existing 行，list 含无相邻的基础区域及可选包基础区域。check 对比替代关系及真实导出优先级，列出缺项、改写和等价 custom；有需复核项退出 1。可选模式和其他 Mod 的追加规则需另查目标环境。

text-icons format 接受 --text 或 --file，角色为 description/name/title；名称原样返回，描述返回幂等候选，保留已有标签及 LOC 占位符，不自动写回。check 只检查效果描述字段与自定义 `_DESCRIPTION` 文本；缺失或未知字体图标需语义复核，不自动改标题、对白。project-check/build 自动包含 adjacency_inheritance 和 description_icons 两项，提示作为 warning，不阻断有意重设计；相邻规则集从 Expansion1/2 依赖推断，未声明时按本体检查。

`.CIV` 的 `adjacencies` / `improvement_adjacencies` 都使用原生桥接表。未改变的原规则填写 `{ "mode": "existing", "id": "Jungle_Science" }`；只有效果变化才 custom，不把普通改良相邻转成 Lua 计数。完整流程见 [相邻指南](../../../skills/reference/config/district-adjacency.md) 与 [文本规范](../../../skills/reference/config/text.md)。
