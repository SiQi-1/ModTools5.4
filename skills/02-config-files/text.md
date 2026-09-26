# Text — 本地化文本规范

## 涉及文件

| 文件 | 内容 |
|------|------|
| `Text/<ModName>_Text_CN.sql` | 所有中文文本 |
| `Text/<ModName>_UIText_CN.sql` | UI 文本（有 UI 时） |

> INSERT 模板已分散在各 skill 的 "Text" 部分，本文记录**书写规范**。

---

## 一、书写风格

### 1.1 命名类（NAME）

- 简洁，2-6 个汉字为佳
- 示例：`舞会演出厅`、`安眠伴随兽`、`偶像光环`

### 1.2 描述类（DESCRIPTION）

- 一段话描述功能，使用游戏内标准术语
- 用 `[NEWLINE]` 换行分隔多层效果
- 在效果、产出和费用说明中按语义使用 `[ICON_xxx]`；标题/名称见 1.5。

**示例（建筑）：**
```
芭蕾舞厅建筑，提供2点【ICON_GreatWork_Religious】巨作槽位（宗教类）。[NEWLINE]拥有2次【ICON_GreatPerson】大作家伟人点数。[NEWLINE]每回合获得3点【ICON_GreatArtist】大艺术家伟人点数。
```

### 1.3 特质类（TRAIT_xxx）

- 标题格式：`{文明/领袖名}的特色{类型名}`或`「{技能名}」`
- 描述直接说明效果，无需冗余前缀

### 1.4 总督晋升类

- 用 `L<N>_NAME` / `L<N>_DESCRIPTION` 后缀
- 名称简洁概括能力名（如"梦境编织者"），描述详述效果

### 1.5 UI 标题与描述分工

- 页面标题、页签、奖励名称、卡片标题和分组名通常使用纯文字；不因名称含有“住房”“科技”等词就插入 `[ICON_XXX]`。例如标题写 `住房`，描述写 `本城 +2[ICON_Housing]住房`。
- 图标用于效果说明、产出数值、费用等需要对应游戏概念的内容，按下文图标规则保留文字标签。标题旁独立的实体/类别 Image 图标是视觉控件，不受此字体图标约定影响。
- 先确定文本在 UI 中的角色，再进行格式化；不要把全部 UI LOC 统一送入描述用的关键词装饰器。一个 LOC 同时用作名称和完整效果说明时应拆开。
- 校验覆盖 XML 的标题 Label 和 Lua 动态填入的奖励名称/分组名；不能只凭 LOC 后缀或“是否出现图标”判定合格。原版特定界面或用户明确要求标题包含图标时按其约定处理，不自动删除别的 Mod 的原始文本。

---

## 二、图标嵌入

### 2.1 产出图标

| 代码 | 显示 |
|------|------|
| `[ICON_Science]` | 科技值 |
| `[ICON_Culture]` | 文化值 |
| `[ICON_Gold]` | 金币 |
| `[ICON_Production]` | 生产力 |
| `[ICON_Food]` | 食物 |
| `[ICON_Faith]` | 信仰值 |
| `[ICON_Amenities]` | 宜居度 |
| `[ICON_Housing]` | 住房 |
| `[ICON_Tourism]` | 旅游业绩 |
| `[ICON_TradeRoute]` | 商路 |

### 2.2 伟人/巨作图标

| 代码 | 显示 |
|------|------|
| `[ICON_GreatGeneral]` | 大将军 |
| `[ICON_GreatAdmiral]` | 海军统帅 |
| `[ICON_GreatEngineer]` | 大工程师 |
| `[ICON_GreatMerchant]` | 大商人 |
| `[ICON_GreatScientist]` | 大科学家 |
| `[ICON_GreatWriter]` | 大作家 |
| `[ICON_GreatArtist]` | 大艺术家 |
| `[ICON_GreatMusician]` | 大音乐家 |
| `[ICON_GreatProphet]` | 大预言家 |
| `[ICON_GreatPerson]` | 伟人（通用） |
| `[ICON_GreatWork_Writing]` | 著作 |
| `[ICON_GreatWork_Portrait]` | 肖像 |
| `[ICON_GreatWork_Landscape]` | 风景 |
| `[ICON_GreatWork_Sculpture]` | 雕塑 |
| `[ICON_GreatWork_Religious]` | 宗教巨作 |
| `[ICON_GreatWork_Artifact]` | 文物 |
| `[ICON_GreatWork_Music]` | 音乐 |
| `[ICON_GreatWork_Relic]` | 遗物 |

### 2.3 其他常用

| 代码 | 显示 |
|------|------|
| `[ICON_Citizen]` | 公民/人口 |
| `[ICON_Governor]` | 总督 |
| `[ICON_Envoy]` | 使者 |
| `[ICON_Movement]` | 移动力 |
| `[ICON_Damaged]` | 伤害/受损 |
| `[ICON_Strength]` | 近战战斗力 |
| `[ICON_Ranged]` | 远程战斗力 |
| `[ICON_Bombard]` | 轰炸战斗力 |
| `[ICON_Range]` | 射程 |
| `[ICON_Charges]` | 建造次数 |
| `[ICON_Policy]` | 政策卡 |
| `[ICON_TechBoosted]` | 科技加速 |
| `[ICON_CivicBoosted]` | 市政加速 |

### 2.4 嵌入规则

- `[ICON_xxx]` 后**必须跟文字标签**，不可裸写图标：`+2 [ICON_Science] 科技值`、`+1 [ICON_Food] 食物`
- 多个产出用 `、` 分隔：`+2 [ICON_Science] 科技值、+1 [ICON_Culture] 文化值`
- 图标与文字之间不加空格
- 自定义图标直接用 `ICON_xxx` 引用，格式同上

---

## 三、使用 `{LOC_xxx}` 引用链

当实体名称和特质名称相同时，用引用链避免重复文本：

```sql
('zh_Hans_CN', 'LOC_TRAIT_BUILDING_SIQI_BALLROOM_NAME', '{LOC_BUILDING_SIQI_BALLROOM_NAME}');
```

> 效果：特质名直接显示为建筑名，无需写两遍。

---

## 四、常用文本模式

### 4.1 被动效果（伟人/BirthModifier）
```
被动效果：{效果描述}
```

### 4.2 主动效果（伟人/Action）
```
使用后：{效果描述}
```

### 4.3 政策卡
```
{效果1}[NEWLINE]{效果2}
```

### 4.4 限制条件说明
```
条件：{限制条件}[NEWLINE]效果：{效果}
```
