# ModTools 制作任务入口

制作 Mod、编写 .CIV、回答文明6实现问题时，按下列顺序读取：

1. [技能规则正文](skills/RULES.md)：数据来源、工具写入边界、任务必读项、验证要求。
2. [统一工作流](skills/WORKFLOW.md)：检索依据 → 规划完整功能 → 管理数据与扩展源码 → 统一检查与生成 → 交付。
3. [modgen 契约](modgen/AGENTS.md)：当前命令与字段要求。
4. 使用 `python -m modgen.cli skill "任务描述" --plan`，读取对应资料与相关章节。

这是兼容入口；行为规则只在 RULES 维护。原本放在本文件的命名、相邻加成和游戏陷阱已保留到 [制作参考](skills/05-modtools-civ/authoring-reference.md)。

工具开发任务按根目录 [AGENTS](AGENTS.md) 转到 [CLAUDE](CLAUDE.md)。
