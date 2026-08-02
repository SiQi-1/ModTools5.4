# ModTools 5.4 路线图（2026-08 更新）

> 本文档用于同步"代码真实状态"和"下一步优先级"。
> 详细历史请看 `CHANGELOG.md`。功能改动时需同步更新两份文档。

## 一、当前已完成（Done）

### 1) 工程与工作区框架
- `.CIV` 工程结构（schema 0.1.0）、序列化与加载流程已落地，按 `CIV_SECTION_ORDER` 17 节归一化。
- 主窗口已接入新建/打开/保存工程；工作区树支持分类节点与子条目组切换。

### 2) 分类编辑能力（13 个内容分类全部接入）
- 文明、领袖、区域、建筑、单位、单位晋升、改良设施、总督、伟人、政策卡、项目、信仰、议程。
- 议程已完整接入：复合编辑器（主表 + HistoricalAgendas / ExclusiveAgendas / AgendaModifiers / AI 偏好）→ SQL/XML 预览 → 生成输出，不再有占位。
- 单位晋升为独立画布式晋升树编辑器（卡片拖拽 + 端口连线 + 2221/2212 模板 + 随机模式）。

### 3) 修改器工作区
- Modifier / RequirementSet / Requirement / UnitAbility 全链路编辑。
- EffectType / RequirementType 搜索与参数模板、中文注释模板（effect/requirement_comment_templates.json）。
- 批量生成对话框（BatchGenerateDialog）、RequirementSet 配对参数、快捷键、战斗预览文本（ModifierStrings）。

### 4) 美术与输出链路
- Icons.xml / ArtDef / XLP / Art.xml / Textures（PNG→DDS→TEX→XLP）/ Moments / 领袖独立 XLP。
- 领袖颜色配置与城邦旗帜实时预览；图片圆形裁切 + 黑边。
- 工程根一键生成：Data/Text/Icons/美术文件 + 覆盖冲突弹窗 + 删除计划。

### 5) 文本与搜索
- 文本工作区统一承载 Text.sql / Text.xml 预览；描述框右键 `[ICON_XXX]` 插入。
- 搜索页：文本搜索 ✓、ModifierType 搜索 ✓。

### 6) 数据库导入能力（游戏库）
- 区域、建筑、单位、单位晋升、改良设施、伟人、政策卡（逻辑已实现）。

### 7) 发布与工程规范化（2026-08）
- `build_release.ps1`：PyInstaller onefile（`--noconsole`）→ release/ + ModTools5.4.zip。
- GitHub Actions：`ci.yml`（push/PR 编译检查 + 单元测试）、`release.yml`（`v*` tag 自动构建并发布 GitHub Release）。
- 首版测试 19 个用例（工程模型 / artdef 解析 / 文本库 / 无头 GUI 冒烟），`python -m unittest discover -s tests -v`。
- MIT LICENSE、requirements.txt、.gitattributes、README 截图自动生成脚本（tools/make_screenshots.py）。

## 二、当前缺口（TODO）

### P1：全局搜索接入真实逻辑
- 现状：搜索页"全局搜索"只有按分类的占位面板。
- 目标：按分类提供可检索结果，并支持定位到对应工作区条目。

### P1：导入按钮开放与补齐
- 现状：分组面板"导入"按钮仅对 区域/建筑/单位/单位晋升/改良设施/伟人 显示；政策卡导入逻辑已实现但按钮未开放（`group_workspace.py` 显隐名单需加入政策卡）。
- 未实现导入：文明、领袖、总督、项目、信仰、议程。

### P2：测试与回归扩展
- 现状：已有 19 个冒烟/逻辑用例，但 SQL 预览方法尚未按分类逐一覆盖（当前仅验证空工程不崩溃）。
- 目标：补充带示例数据的分类预览断言；必要时引入 GUI 交互测试（QTest）。

### P2：打包配置收敛
- 现状：`build_release.ps1` 与本地 `ModTools5.4.spec` 各维护一份数据清单，易漂移。
- 目标：改为单一来源（spec 由脚本生成或删除 spec 路径）。

## 三、建议迭代顺序

### 迭代 A（建议先做）
- 全局搜索：关键词检索 + 结果定位，复用各分类已有名称/预览逻辑。

### 迭代 B
- 开放政策卡导入按钮；补齐 文明/领袖/总督/项目/信仰/议程 的数据库导入。

### 迭代 C
- 最小测试集与回归脚本（启动冒烟、工程读写、核心预览生成）。

### 迭代 D
- 打包配置收敛、版本号统一维护、大文件拆分（workspace_page 9.4k 行）。

## 四、维护约定

- 每次功能合并后，同步更新：
  - `CHANGELOG.md`（事实记录，最上方为最新）
  - 本文档（当前状态与下一步）
- 文档描述以"已在代码中存在的能力"为准，避免前瞻规划替代现状说明。
- 文件命名红线：Data/Text/Icons 可使用"文件名前缀_..."，但 XLP 与 ArtDef 文件名禁止加前缀。
- AI Agent 功能已移除（2026-06-30），如需恢复使用 `git checkout agent-dev`。
