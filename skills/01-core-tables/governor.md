# Governor — 总督定义

## 涉及文件

| 文件 | 内容 |
|------|------|
| `Data/<ModName>_Governors.sql` | 总督主表 + 子表（晋升树/Modifiers） |
| `Icons/<ModName>_Icons.xml` | `icons.md` — 总督图标（普通 22/32/64 + 填充 22/32 + 槽位 22/32） |
| `Text/<ModName>_Text_CN.sql` | 总督名/描述/头衔、晋升名/描述 |

## 涉及的表（按 INSERT 顺序）

```
Types → Traits → Governors → [Governors_XP2] → [GovernorReplaces] → [GovernorsCannotAssign]
→ GovernorPromotions → GovernorPromotionSets → GovernorPromotionPrereqs
→ [GovernorPromotionConditions]
→ GovernorModifiers → GovernorPromotionModifiers
```

不归 governor.md 的表：
- **GovernorModifiers / GovernorPromotionModifiers** → 关联逻辑到此，ModifierId 的定义在 `07-techniques/modifiers.md`

---

## 一、Types

```sql
INSERT INTO Types (Type, Kind) VALUES
('TRAIT_GOVERNOR_SIQI_{SHORT}', 'KIND_TRAIT'),
('GOVERNOR_SIQI_{SHORT}', 'KIND_GOVERNOR'),
('GOVERNOR_SIQI_{SHORT}_PROMOTION_BASE', 'KIND_GOVERNOR_PROMOTION'),
('GOVERNOR_SIQI_{SHORT}_PROMOTION_L1', 'KIND_GOVERNOR_PROMOTION'),
('GOVERNOR_SIQI_{SHORT}_PROMOTION_R1', 'KIND_GOVERNOR_PROMOTION'),
('GOVERNOR_SIQI_{SHORT}_PROMOTION_L2', 'KIND_GOVERNOR_PROMOTION'),
('GOVERNOR_SIQI_{SHORT}_PROMOTION_R2', 'KIND_GOVERNOR_PROMOTION'),
('GOVERNOR_SIQI_{SHORT}_PROMOTION_M3', 'KIND_GOVERNOR_PROMOTION');
```

> 晋升命名：`GOVERNOR_SIQI_{SHORT}_PROMOTION_{Column}{Level}` — Column=L/M/R，Level=1/2/3。BASE 无位置标识。

---

## 二、Traits

总督可直接使用文明/领袖的 TraitType，无需新建特质的 Traits 行。

```sql
-- 方式一：直接使用文明/领袖已有特质（推荐）
-- GovernorType 的 TraitType 直接填 'TRAIT_CIVILIZATION_SIQI_xxx' 或 'TRAIT_LEADER_SIQI_xxx'
```

如果单独新建总督特质（如 19.47 Mod），需要 `InternalOnly=1` 隐藏该特质行，保持 UI 整洁：

```sql
-- 方式二：新建总督独立特质
INSERT INTO Types (Type, Kind) VALUES
('TRAIT_GOVERNOR_SIQI_{SHORT}', 'KIND_TRAIT');

INSERT INTO Traits (TraitType, Name, Description, InternalOnly) VALUES
('TRAIT_GOVERNOR_SIQI_{SHORT}', 'LOC_TRAIT_GOVERNOR_SIQI_{SHORT}_NAME', 'LOC_TRAIT_GOVERNOR_SIQI_{SHORT}_DESCRIPTION', 1);
```

> `InternalOnly=1`：不显示在 UI 中，仅做逻辑绑定用。

---

## 三、Governors（主表，12 列）

### 完整 INSERT 模板

```sql
INSERT INTO Governors (
    GovernorType,
    Name,
    Description,
    IdentityPressure,
    Title,
    ShortTitle,
    TransitionStrength,
    AssignCityState,
    Image,
    PortraitImage,
    PortraitImageSelected,
    TraitType
) VALUES
(
    'GOVERNOR_SIQI_{SHORT}',
    'LOC_GOVERNOR_SIQI_{SHORT}_NAME',
    'LOC_GOVERNOR_SIQI_{SHORT}_DESCRIPTION',
    8,
    'LOC_GOVERNOR_SIQI_{SHORT}_TITLE',
    'LOC_GOVERNOR_SIQI_{SHORT}_SHORT_TITLE',
    150,
    0,
    'GOVERNOR_SIQI_{SHORT}_NORMAL',
    'GOVERNOR_SIQI_{SHORT}_NORMAL',
    'GOVERNOR_SIQI_{SHORT}_SELECTED',
    'TRAIT_GOVERNOR_SIQI_{SHORT}'
);
```

### 逐列参考

**身份 + 文本：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 1 | GovernorType | `GOVERNOR_SIQI_{SHORT}` | **必写** |
| 2 | Name | `LOC_GOVERNOR_SIQI_{SHORT}_NAME` | **必写** |
| 3 | Description | `LOC_GOVERNOR_SIQI_{SHORT}_DESCRIPTION` | **必写** |
| 5 | Title | `LOC_GOVERNOR_SIQI_{SHORT}_TITLE`（头衔，如"总务官"） | **必写** |
| 6 | ShortTitle | `LOC_GOVERNOR_SIQI_{SHORT}_SHORT_TITLE`（短头衔） | **必写** |
| 12 | TraitType | `TRAIT_GOVERNOR_SIQI_{SHORT}` | 按需 |

> Title 与 ShortTitle 通常相同（参考官版：总务官=总务官）。

**忠诚度 / 就职：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 4 | IdentityPressure | 标准值 8 | 按需 |
| 7 | TransitionStrength | 见下表 | 按需 |

> **TransitionStrength 对照：**
> | 值 | 就职回合数 |
> |----|-----------|
> | 100 | 5 回合 |
> | 125 | 4 回合 |
> | 150 | 3 回合 |
> | 250 | 2 回合 |
> | 500 | 2 回合（bug，UI 显示 0 实际仍 2） |
> | 501+ | 立即就职 |

**美术：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 9 | Image | `GOVERNOR_SIQI_{SHORT}_NORMAL` | **必写** |
| 10 | PortraitImage | `GOVERNOR_SIQI_{SHORT}_NORMAL`（与 Image 相同） | 按需 |
| 11 | PortraitImageSelected | `GOVERNOR_SIQI_{SHORT}_SELECTED`（选中高亮） | 按需 |

**指派限制：**

| # | 列名 | 值参考 | 写不写 |
|---|------|--------|--------|
| 8 | AssignCityState | 1=可派往城邦（如阿玛妮） | 按需 |

---

## 四、Governors_XP2

```sql
INSERT INTO Governors_XP2 (GovernorType, AssignToMajor) VALUES
('GOVERNOR_SIQI_{SHORT}', 0);
```

| 列 | 说明 |
|---|------|
| AssignToMajor | 1=可派往主要文明 |

---

## 五、GovernorReplaces

```sql
INSERT INTO GovernorReplaces (UniqueGovernorType, ReplacesGovernorType) VALUES
('GOVERNOR_SIQI_{SHORT}', 'GOVERNOR_THE_EDUCATOR');
```

> **只有第一行有效**（官方 bug），如需取代多个总督只写一行。

---

## 六、GovernorsCannotAssign

```sql
INSERT INTO GovernorsCannotAssign (GovernorType, CannotAssign) VALUES
('GOVERNOR_SIQI_{SHORT}', 1);
```

> 秘密结社用：CannotAssign=1 = 无需就职即可生效。

---

## 七、晋升树

### 结构

- **Level 0**：基础能力，Column=1（中），BaseAbility=1，无需前置
- **Level 1-3**：晋升能力，Column=0(L) / 1(M) / 2(R)，BaseAbility=0
- 标准数量：1 BASE + 5 晋升 = 6 个
- 有效范围：Level 0-3，超过 UI 可能不兼容但数据库可运行

### 三种常见布局

**分叉汇聚型（L/R → L/R → M）：**
```
Level 0:      [BASE]
Level 1:   L1      R1
Level 2:   L2      R2
Level 3:      [M3]
```

**中轴分叉型（M → L/R → L/R）：**
```
Level 0:      [BASE]
Level 1:      [M1]
Level 2:   L2      R2
Level 3:   L3      R3
```

**L/R→中→L/R型：**
```
Level 0:      [BASE]
Level 1:   L1      R1
Level 2:      [M2]
Level 3:   L3      R3
```

### GovernorPromotions

```sql
INSERT INTO GovernorPromotions (GovernorPromotionType, Name, Description, Level, Column, BaseAbility) VALUES
('GOVERNOR_SIQI_{SHORT}_PROMOTION_BASE', 'LOC_GOVERNOR_SIQI_{SHORT}_PROMOTION_BASE_NAME', 'LOC_GOVERNOR_SIQI_{SHORT}_PROMOTION_BASE_DESCRIPTION', 0, 1, 1),
('GOVERNOR_SIQI_{SHORT}_PROMOTION_L1',  'LOC_GOVERNOR_SIQI_{SHORT}_PROMOTION_L1_NAME',  'LOC_GOVERNOR_SIQI_{SHORT}_PROMOTION_L1_DESCRIPTION',  1, 0, 0),
('GOVERNOR_SIQI_{SHORT}_PROMOTION_R1',  'LOC_GOVERNOR_SIQI_{SHORT}_PROMOTION_R1_NAME',  'LOC_GOVERNOR_SIQI_{SHORT}_PROMOTION_R1_DESCRIPTION',  1, 2, 0),
('GOVERNOR_SIQI_{SHORT}_PROMOTION_L2',  'LOC_GOVERNOR_SIQI_{SHORT}_PROMOTION_L2_NAME',  'LOC_GOVERNOR_SIQI_{SHORT}_PROMOTION_L2_DESCRIPTION',  2, 0, 0),
('GOVERNOR_SIQI_{SHORT}_PROMOTION_R2',  'LOC_GOVERNOR_SIQI_{SHORT}_PROMOTION_R2_NAME',  'LOC_GOVERNOR_SIQI_{SHORT}_PROMOTION_R2_DESCRIPTION',  2, 2, 0),
('GOVERNOR_SIQI_{SHORT}_PROMOTION_M3',  'LOC_GOVERNOR_SIQI_{SHORT}_PROMOTION_M3_NAME',  'LOC_GOVERNOR_SIQI_{SHORT}_PROMOTION_M3_DESCRIPTION',  3, 1, 0);
```

### GovernorPromotionSets

```sql
INSERT INTO GovernorPromotionSets (GovernorType, GovernorPromotion) VALUES
('GOVERNOR_SIQI_{SHORT}', 'GOVERNOR_SIQI_{SHORT}_PROMOTION_BASE'),
('GOVERNOR_SIQI_{SHORT}', 'GOVERNOR_SIQI_{SHORT}_PROMOTION_L1'),
('GOVERNOR_SIQI_{SHORT}', 'GOVERNOR_SIQI_{SHORT}_PROMOTION_R1'),
('GOVERNOR_SIQI_{SHORT}', 'GOVERNOR_SIQI_{SHORT}_PROMOTION_L2'),
('GOVERNOR_SIQI_{SHORT}', 'GOVERNOR_SIQI_{SHORT}_PROMOTION_R2'),
('GOVERNOR_SIQI_{SHORT}', 'GOVERNOR_SIQI_{SHORT}_PROMOTION_M3');
```

### GovernorPromotionPrereqs

以分叉汇聚型（Oblivionis）为例：

```sql
INSERT INTO GovernorPromotionPrereqs (GovernorPromotionType, PrereqGovernorPromotion) VALUES
-- L1, R1 需要 BASE
('GOVERNOR_SIQI_{SHORT}_PROMOTION_L1', 'GOVERNOR_SIQI_{SHORT}_PROMOTION_BASE'),
('GOVERNOR_SIQI_{SHORT}_PROMOTION_R1', 'GOVERNOR_SIQI_{SHORT}_PROMOTION_BASE'),
-- L2 需要 L1, R2 需要 R1
('GOVERNOR_SIQI_{SHORT}_PROMOTION_L2', 'GOVERNOR_SIQI_{SHORT}_PROMOTION_L1'),
('GOVERNOR_SIQI_{SHORT}_PROMOTION_R2', 'GOVERNOR_SIQI_{SHORT}_PROMOTION_R1'),
-- M3 需要 L2 AND R2（两行）
('GOVERNOR_SIQI_{SHORT}_PROMOTION_M3', 'GOVERNOR_SIQI_{SHORT}_PROMOTION_L2'),
('GOVERNOR_SIQI_{SHORT}_PROMOTION_M3', 'GOVERNOR_SIQI_{SHORT}_PROMOTION_R2');
```

> 关键规则：
> - BASE 无前置
> - M 级需要左右两侧均解锁（两行 INSERT）
> - 其余沿树枝单向依赖

---

## 八、GovernorPromotionConditions

```sql
INSERT INTO GovernorPromotionConditions (GovernorPromotionType, HiddenWithoutPrereqs, EarliestGameEra) VALUES
('GOVERNOR_SIQI_{SHORT}_PROMOTION_L2', 1, 'ERA_MEDIEVAL');
```

| 列 | 说明 |
|---|------|
| HiddenWithoutPrereqs | 无前置时隐藏（秘密结社用） |
| EarliestGameEra | 最早可用时代，如 `ERA_MEDIEVAL` |

---

## 九、GovernorModifiers / GovernorPromotionModifiers

```sql
INSERT INTO GovernorModifiers (GovernorType, ModifierId) VALUES
('GOVERNOR_SIQI_{SHORT}', 'MODIFIER_SIQIXXX_xxx');

INSERT INTO GovernorPromotionModifiers (GovernorPromotionType, ModifierId) VALUES
('GOVERNOR_SIQI_{SHORT}_PROMOTION_L1', 'MODIFIER_SIQIXXX_xxx');
```

> ModifierId 的具体定义在 `07-techniques/modifiers.md` 中。

---

## 十、Text — 本地化文本

```sql
INSERT INTO LocalizedText (Language, Tag, Text) VALUES
-- 总督本体
('zh_Hans_CN', 'LOC_GOVERNOR_SIQI_{SHORT}_NAME',        '{中文名}'),
('zh_Hans_CN', 'LOC_GOVERNOR_SIQI_{SHORT}_DESCRIPTION', '{中文描述}'),
('zh_Hans_CN', 'LOC_GOVERNOR_SIQI_{SHORT}_TITLE',       '{头衔}'),
('zh_Hans_CN', 'LOC_GOVERNOR_SIQI_{SHORT}_SHORT_TITLE', '{短头衔}'),
-- 特质
('zh_Hans_CN', 'LOC_TRAIT_GOVERNOR_SIQI_{SHORT}_NAME',        '{特质名称}'),
('zh_Hans_CN', 'LOC_TRAIT_GOVERNOR_SIQI_{SHORT}_DESCRIPTION', '{特质描述}'),
-- 晋升
('zh_Hans_CN', 'LOC_GOVERNOR_SIQI_{SHORT}_PROMOTION_BASE_NAME', '{基础能力名}'),
('zh_Hans_CN', 'LOC_GOVERNOR_SIQI_{SHORT}_PROMOTION_BASE_DESCRIPTION', '{基础能力描述}'),
('zh_Hans_CN', 'LOC_GOVERNOR_SIQI_{SHORT}_PROMOTION_L1_NAME',  '{L1晋升名}'),
('zh_Hans_CN', 'LOC_GOVERNOR_SIQI_{SHORT}_PROMOTION_L1_DESCRIPTION', '{L1晋升描述}');
```

---

## 十一、Enum 文件

| 文件 | 内容 |
|------|------|
| `reference/enums/GovernorType.txt` | 官方 8 总督 + MOD/SIQI 总督 |
