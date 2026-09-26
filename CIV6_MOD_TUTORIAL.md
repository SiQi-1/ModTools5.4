# 文明6 Mod 制作全流程教程（ModTools 5.4）

从零开始：创建工程 → 用 ModTools 5.4 制作 → 部署进游戏。提供**两条路径**：
- **GUI 路径**：全程可视化操作
- **纯 AI 路径**：不开界面，用 modgen 命令行 + AI 完成（适合已有 Python 环境、习惯用 AI 的用户）

---

## 第 0 章 准备

### 0.1 安装与初始化

获取完整源码目录（skills + tools）后，知识检索和数据命令可直接通过 `python -m modgen.cli` 运行。
完整生成或可视化操作：运行 `python tools/setup_env.py` 初始化，再用 `.venv\Scripts\python ModTools5.4.py` 启动 GUI。
仓库不再分发 EXE 或预制 ZIP；详见 [源码分享约定](docs/SOURCE_SHARING.md)。

### 0.2 配置数据库（首次必做）

1. **文本数据库**：设置页选择 `local_text_New.sqlite`（源码自带）→ 中文显示正常
2. **游戏数据库**：设置页选择 `DebugGameplay.sqlite`（`%LOCALAPPDATA%\Firaxis Games\Sid Meier's Civilization VI\Cache\`）→ 导入原版对象、能力搜索可用

> 游戏库要求：文明6 至少运行过一次（生成 Cache 数据库）。

### 0.3 理解三类文件

| 文件 | 谁创建 | 作用 |
|------|--------|------|
| `.CIV` | ModTools | 编辑状态（JSON），**你操作的是它** |
| `.civ6proj` | **ModTools 直接生成**（或 ModBuddy） | 定位输出目录；ModTools 把生成的文件写进它所在目录 |
| `.modinfo` | 构建生成或手写 | **游戏加载 Mod 的依据**，放游戏 Mods 目录 |

关系：`.CIV`（编辑）→ ModTools 生成 SQL/XML/图片 + `.civ6proj` → 构建成 `.modinfo` → 游戏 Mods 目录。

> **`.civ6proj` 不需要 ModBuddy 新建**：基础信息页「新建 .civ6proj」按钮或
> `python -m modgen.cli civ6proj 工程.CIV --update-civ` 都能直接生成（与 ModBuddy
> 向导产物同构，含空白 Art.xml；ModBuddy 之后仍可打开/构建）。

---

## 第 1 章 创建工程

**GUI**：文件 → 新建工程 → 输入名称 → 保存为 `.CIV`。

**AI**：`python -m modgen.cli generate 文明 --name 示例文明 --abbr DEMO --prefix SIQI --infix 1`（输出 JSON 骨架；配合 `merge` 合并进工程）。

新建后进入「基础信息」：
- **前缀**（如 `SIQI`）：所有 Type 的前缀段
- **中缀**（如 `1`）：Type 的编号段（生成 `CIVILIZATION_SIQI_C0001_XXX` 形式）
- **.civ6proj 路径**：点 **「新建 .civ6proj」** 直接生成（默认 `文档\Firaxis ModBuddy\Civilization VI\<文件名>\`），或选择已有的 ModBuddy 工程文件

---

## 第 2 章 GUI 制作全流程（以"新文明 + 领袖特质"为例）

### 2.1 文明

左侧树 → 文明 → 新增：
1. 填中文名/简介/形容词（如"示例文明"）
2. 特质（Trait）：文明特质名 + 描述（能力稍后在修改器里挂）
3. 城市名/市民名（可导入或手填）
4. 绑定特色对象（特色区域/建筑/单位/改良，若打算做特色）

### 2.2 领袖

领袖 → 新增：名字/性别/文明绑定/外交文本；领袖特质类似文明特质。
（领袖颜色与图片在编辑器内配置，图片槽位见美术章。）

### 2.3 特色对象（可选）

区域/建筑/单位/改良设施/单位晋升 均可"从游戏数据库导入"原版对象作为模板，再改参数：
- 区域：主表 + 副表（含**相邻加成**——编辑器内置自动生成描述）
- 单位：必填 `FormationClass`（如 `FORMATION_CLASS_LAND_COMBAT`）；晋升树用画布编辑器（2221/2212 模板）

### 2.4 修改器：给特质挂能力

「修改器」工作区 → 新增 Modifier：
1. 选 **EffectType**（如 `EFFECT_ADJUST_CITY_YIELD`）→ 参数表自动按该效果类型生成骨架
2. 填参数（如 `Amount=1, YieldType=YIELD_SCIENCE`）
3. 加条件：RequirementSet + Requirement（如 `REQUIREMENT_PLAYER_IS_AT_WAR`）
4. 绑定所属：把 Modifier 挂到"文明特质"或"领袖特质"上

> **不知道用什么效果类型？** 见第 5 章知识查询——先搜原版怎么实现的，照抄。

### 2.5 美术（图标/领袖图片）

美术工作区：Icons.xml / ArtDef / XLP / Art.xml / Textures / Moments。
- 图标：为文明/领袖/对象配置图标（PNG 路径或数据库别名）
- 领袖图片：6 个槽位（前景/背景/外交/选择），领袖 XLP 独立生成
- 纹理链路：PNG → DDS → TEX → XLP

### 2.6 文本

「文本」工作区统一预览 Text.sql/Text.xml：各分类 Name/Description、修改器预览文本等自动聚合。
描述框支持右键插入 `[ICON_XXX]` 图标标记。

### 2.7 生成输出

工程根节点 → **生成所有文件**：弹出覆盖/删除确认 → 写出 SQL/XML/图标/ArtDef 等到 `.civ6proj` 目录。
预览可在各分类的 SQL/XML 预览页核对。

---

## 第 3 章 部署到游戏

### 方式 A：用 ModBuddy 构建（官方路径）

1. 用 ModBuddy 打开 `.civ6proj`（或新建工程指向同一目录）
2. Build → 输出到游戏 Mods 目录

### 方式 B：手写 .modinfo（无 ModBuddy）

1. 在 `.civ6proj` 同目录创建 `<Mod名>.modinfo`：

```xml
<?xml version="1.0" encoding="utf-8"?>
<Mod id="GUID 粘贴基础信息里的" version="1">
  <Properties>
    <Name>示例文明</Name>
    <Teaser>示例文明与领袖</Teaser>
    <Description>演示用 Mod</Description>
    <Authors>你</Authors>
  </Properties>
  <Files>
    <!-- 列出要打包进 Mod 的所有文件（相对路径） -->
    <File>Data/示例.sql</File>
    <File>Data/Text.sql</File>
    <File>Icons/Icons.xml</File>
    <File>ArtDefs/...</File>
  </Files>
  <Actions>
    <OnModLoaded>
      <UpdateDatabase id="Data">
        <File>Data/示例.sql</File>
      </UpdateDatabase>
      <UpdateDatabase id="Text">
        <File>Data/Text.sql</File>
      </UpdateDatabase>
      <UpdateIcons id="Icons">
        <File>Icons/Icons.xml</File>
      </UpdateIcons>
      <!-- ArtDef/XLP 等按需添加 -->
    </OnModLoaded>
  </Actions>
</Mod>
```

2. 把 `.modinfo` 与全部输出文件复制到游戏 Mods 目录：
   `文档\My Games\Sid Meier's Civilization VI\Mods\<Mod名>\`
3. 启动游戏 → 额外内容 → 启用 Mod

> 提示：`.civ6proj` 的 `FrontEndActionData/InGameActionData` 里 ModTools 已按文件类型自动生成 `UpdateDatabase/UpdateIcons` 等动作，手写时可参照。

---

## 第 4 章 纯 AI 工作流（不开 GUI）

适合已装 Python 的用户：让 AI（或你）用 modgen 命令行完成全部条目制作，最后用 GUI 生成输出。

### 4.1 工具链速查

```bash
# 环境（一次性）
python tools/setup_env.py

# 创建工程骨架（基础信息/美术/修改器/文本 结构就位，替代拷贝旧工程）
python -m modgen.cli new-project 示例.CIV --name 示例文明模组 --prefix SIQI --infix 1

# 生成条目骨架（Type/LOC/子表结构自动就位）
python -m modgen.cli generate 文明 --name 示例文明 --abbr DEMO --prefix SIQI --infix 1
python -m modgen.cli generate 领袖 --name 示例领袖 --abbr LEADER1 --prefix SIQI --infix 1

# 修改器四类（效果类型存在性 + 参数骨架自动校验）
python -m modgen.cli generate-modifier --effect EFFECT_ADJUST_CITY_YIELD --collection COLLECTION_CITY --desc 科技加成 --params '{"Amount":1,"YieldType":"YIELD_SCIENCE"}'
python -m modgen.cli generate-requirement --type REQUIREMENT_PLAYER_IS_AT_WAR --desc 处于战争
python -m modgen.cli generate-reqset --desc 战争条件集 --logic ALL --requirements '["REQUIREMENT_..."]'
python -m modgen.cli generate-ability --abbr AB1 --name 示例能力

# 校验（ERROR 必修 / WARNING 确认）与合并（内容分类与修改器均可 merge）
python -m modgen.cli validate 示例.CIV
python -m modgen.cli merge 示例.CIV 文明 --entry modgen_work/entry_文明.json
python -m modgen.cli merge 示例.CIV 修改器 --entry modgen_work/mod.json

# 生成→校验闭环：无头预览将导出的全部文件（不开 GUI 也能验证）
python -m modgen.cli preview 示例.CIV --dry-run
python -m modgen.cli preview 示例.CIV --section 领袖 --format sql

# 生成 .civ6proj 工程（无需 ModBuddy 新建；--update-civ 回写路径到 .CIV）
python -m modgen.cli civ6proj 示例.CIV --update-civ

# 自定义文件通道（确需 Lua / 自定义 SQL/XML 时；自动注册文件动作，一键生成原样透传）
python -m modgen.cli custom-file write 示例.CIV --path Scripts/My.lua --content-file modgen_work/My.lua
python -m modgen.cli custom-file write 示例.CIV --path Data/Extra.sql --content "INSERT INTO ..."
python -m modgen.cli custom-file list 示例.CIV

# 知识查询（不知道效果怎么做 → 先搜再抄；查表结构/查文本）
python -m modgen.cli search 宣战
python -m modgen.cli search --object 农场
python -m modgen.cli query "SELECT ModifierType, CollectionType FROM DynamicModifiers LIMIT 10"
python -m modgen.cli loc LOC_TRAIT_CIVILIZATION_XXX_NAME

# AI 控制接口：驱动 GUI 的一键按钮（打开 GUI 后 HTTP 调用；或一次性执行）
python ModTools5.4.py 示例.CIV --ai-port 8765
python ModTools5.4.py 示例.CIV --headless --ai-exec '{"action":"generate_all","params":{"overwrite":"all"}}'
# 动作表与协议：ModTools_5_4/docs/AI_CONTROL_API.md
```

### 4.2 完整示例：做一个"被宣战 +100% 产能"的领袖特质

```bash
# 0. 建工程骨架（一次性）
python -m modgen.cli new-project 示例.CIV --name 示例工程 --prefix SIQI --infix 1

# 1. 查原版实现（方法论：先搜索，不要凭记忆）
python -m modgen.cli search 宣战
# → 找到柯廷战争机器等，记下效果类型与条件

# 2. 生成并合并条目
python -m modgen.cli generate 领袖 --name 示例领袖 --abbr LEADER1 --prefix SIQI --infix 1 > modgen_work/entry.json
python -m modgen.cli generate-modifier --effect EFFECT_ADD_DIPLOMATIC_YIELD_MODIFIER \
  --collection COLLECTION_OWNER --desc 被宣战后产能加成 \
  --params '{"YieldType":"YIELD_PRODUCTION","Amount":100,"TurnsActive":10}' \
  --subject-reqset REQSET_SIQI_0001_AT_WAR > modgen_work/mod.json
python -m modgen.cli generate-requirement --type REQUIREMENT_PLAYER_IS_AT_WAR --desc 处于战争 > modgen_work/req.json
python -m modgen.cli generate-reqset --desc 战争条件集 --logic ALL \
  --requirements '["<生成的REQUIREMENT_ID>"]' > modgen_work/reqset.json
# ... merge 各条目进工程（含 `merge 示例.CIV 修改器 --entry modgen_work/mod.json`），validate 通过

# 3. 预览将导出的文件，确认无字段/引用问题（不开 GUI）
python -m modgen.cli preview 示例.CIV --dry-run
python -m modgen.cli preview 示例.CIV --section 领袖

# 4. 生成 .civ6proj（绑定输出目录）→ GUI 一键生成（或 --ai-exec 驱动）→ 部署（第 3 章）
python -m modgen.cli civ6proj 示例.CIV --update-civ
python ModTools5.4.py 示例.CIV --headless --ai-exec '{"action":"generate_all","params":{"overwrite":"all"}}'

# 4b. 确需 Lua / 自定义 SQL/XML 时（自定义文件通道，自动注册动作、一键生成原样透传）
python -m modgen.cli custom-file write 示例.CIV --path Scripts/My.lua --content-file modgen_work/My.lua
python -m modgen.cli custom-file write 示例.CIV --path Data/Extra.sql --content "INSERT INTO ..."
```

> 给 AI 的完整任务说明见 README「AI 生成 .CIV」章节的开局提示词；详细规则见 `modgen/AGENTS.md`。

---

## 第 5 章 知识查询（核心方法论）

**判断"某效果有没有现成实现"的唯一正确方法 = 搜索原版，不要凭记忆断言。**

```bash
python -m modgen.cli search <关键词>            # 中文效果词（宣战/产能/农场…）或英文（WAR/YIELD_*）
python -m modgen.cli search --object <关键词>    # 列出对象的全部 Modifier 实现（照抄用）
python -m modgen.cli skill <关键词>              # 本地技能库（仓库根 skills/）全文检索：写法/模板/工作流/Lua
python -m modgen.cli skill <关键词> --file <相对路径>   # 输出命中技能文件全文
```

示例：搜"农场"→ 高棉「大人工湖」→ `TRAIT_FARM_AQUEDUCT_ADJECENCY_FOOD [EFFECT_ADJUST_PLOT_YIELD] Amount=2, YIELD_FOOD` + 两个 `REQUIREMENT_*`（相邻水渠 + 地块是农场）——**"相邻农场+食物"的现成实现**。

GUI 等效：小工具窗口 → 能力实现搜索（同一份数据，卡片 + 详情树）。

**"怎么写"类知识**（SQL 模板、Lua API、.CIV 工作流）：`modgen skill <关键词>` 查仓库根 `skills/`（随源码分发，`--file` 看全文）。

**搜不到怎么办**：换英文关键词（效果词映射只覆盖常见词）→ 换相近词 → 才考虑"可能没有现成实现"（此时多半需要 Lua——走 `custom-file` 自定义文件通道，见第 4 章 4b）。

---

## 附录 A：常见效果速查（先 search，以下仅供参考）

| 想要的效果 | 典型效果器（以 search 结果为准） |
|-----------|-------------------------------|
| 城市产出加成 | `EFFECT_ADJUST_CITY_YIELD`（Amount/YieldType） |
| 玩家全局产出加成 | `EFFECT_ADJUST_PLAYER_YIELD_MODIFIER` |
| 地块产出（相邻/地形） | `EFFECT_ADJUST_PLOT_YIELD`、`EFFECT_DISTRICT_ADJACENCY`、`EFFECT_FEATURE_ADJACENCY` |
| 单位属性 | `EFFECT_ADJUST_UNIT_MOVEMENT`、`EFFECT_ADJUST_UNIT_COMBAT_STRENGTH` |
| 解锁/获得 | `EFFECT_GRANT_PLAYER_SPECIFIC_TECHNOLOGY`、`EFFECT_PLAYER_GRANT_FAITH` |
| 购买能力 | `EFFECT_ENABLE_UNIT_FAITH_PURCHASE`、`EFFECT_ENABLE_BUILDING_FAITH_PURCHASE` |
| 外交/战争 | `EFFECT_ADD_DIPLOMATIC_YIELD_MODIFIER`（+ `REQUIREMENT_PLAYER_IS_AT_WAR`） |
| 单位能力授予 | `MODIFIER_PLAYER_UNITS_GRANT_ABILITY` → `ABILITY_*` → UnitAbilityModifiers |
| 挂载链 | `MODIFIER_PLAYER_CITIES_ATTACH_MODIFIER`（参数 `ModifierId` 指向被挂载者） |

常用条件：`REQUIREMENT_PLAYER_IS_AT_WAR`、`REQUIREMENT_PLAYER_HAS_CIVIC/TECH`、`REQUIREMENT_CITY_HAS_DISTRICT`、`REQUIREMENT_PLOT_IMPROVEMENT_TYPE_MATCHES`、`REQUIREMENT_PLOT_ADJACENT_DISTRICT_TYPE_MATCHES`。

## 附录 B：排障速查

| 现象 | 处理 |
|------|------|
| 中文显示"未知" | 文本库未配置：设置页选 `local_text_New.sqlite` |
| 生成提示"请先导入 .civ6proj" | 基础信息未绑定 .civ6proj——点「新建 .civ6proj」由工具生成即可 |
| search 中文无结果 | 文本库未配置；或换英文关键词 |
| 游戏里 Mod 不生效 | 检查 Mods 目录结构（`Mods\<Mod名>\` 内含 .modinfo）；游戏内"额外内容"启用；XML 大小写 |
| 修改器报错"未知 EffectType" | 效果类型不存在：`modgen search <效果词>` 查现成实现 |
| 保存后 Type 丢失前缀 | 旧版平铺 .CIV 的已知问题已修复（2026-08-16）；重新保存一次即可 |
