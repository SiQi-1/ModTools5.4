# GreatPerson — 伟人定义

## 两路线型

| 路线 | 特征 | 核心 CREATE |
|------|------|------------|
| 能力型 | 有主动行动（ActionCharges ≥ 1），使用时触发 ActionModifiers，诞生时触发 BirthModifiers | GreatPersonClasses → GreatPersonIndividuals → *Modifiers |
| 巨作型 | ActionCharges = 0，无主动行动。巨作通过 GreatWorks 表链到 GreatPersonIndividualType | 能力型全部 + GreatWorkObjectTypes → GreatWorks → GreatWork_YieldChanges |

> 0022 模组展示了标准巨作型伟人写法：一个类多个体，每个体产出 3 个巨作，无主动行动。

## 涉及文件

| 文件 | 内容 |
|------|------|
| `Data/<ModName>_GreatPeople.sql` | 伟人类别 + 个体 + Modifier 绑定 |
| `Data/<ModName>_GreatWorks.sql` | 巨作（巨作型伟人用） |
| `Text/<ModName>_Text_CN.sql` | 所有文本 |
| `Data/<ModName>_Modifiers.sql` | Action/Birth Modifiers 的具体定义 |

## 涉及的表（按 INSERT 顺序）

```
Types → GreatPersonClasses → GreatPersonIndividuals
→ [ExcludedGreatPersonClasses] → [Map_GreatPersonClasses]
→ GreatPersonIndividualBirthModifiers → GreatPersonIndividualActionModifiers
→ [GreatPersonIndividualIconModifiers]
→ GreatWorkObjectTypes → GreatWorks → [GreatWork_ValidSubTypes]
→ [GreatWork_YieldChanges] → [GreatWorkModifiers]
→ [GreatWorks_ImprovementType] → [GreatWorks_MODE]
```

---

## 一、Types

```sql
INSERT INTO Types (Type, Kind) VALUES
('GREAT_PERSON_CLASS_SIQI_{SHORT}', 'KIND_GREAT_PERSON_CLASS'),
('GREAT_PERSON_INDIVIDUAL_SIQI_{SHORT}', 'KIND_GREAT_PERSON_INDIVIDUAL');
```

> 巨作还需：`('GREATWORK_SIQI_{SHORT}', 'KIND_GREATWORK')`

---

## 二、GreatPersonClasses（伟人类别，10 列）

```sql
INSERT INTO GreatPersonClasses (
    GreatPersonClassType,
    Name,
    UnitType,
    DistrictType,
    AvailableInTimeline,
    GenerateDuplicateIndividuals,
    PseudoYieldType,
    IconString,
    ActionIcon,
    MaxPlayerInstances
) VALUES
(
    'GREAT_PERSON_CLASS_SIQI_{SHORT}',
    'LOC_GREAT_PERSON_CLASS_SIQI_{SHORT}_NAME',
    'UNIT_GREAT_SIQI_{SHORT}',
    'DISTRICT_CITY_CENTER',
    0,
    1,
    'PSEUDOYIELD_GPP_GENERAL',
    '[ICON_GreatGeneral]',
    'ICON_UNITOPERATION_GENERAL_ACTION',
    NULL
);
```

| # | 列名 | 说明 |
|---|------|------|
| 1 | GreatPersonClassType | 伟人类别标识 |
| 2 | Name | 名称 LOC |
| 3 | UnitType | 对应伟人单位（需先在 Units.sql 中定义） |
| 4 | DistrictType | 生成伟人的区域（`DISTRICT_CITY_CENTER` 表示在市中心） |
| 5 | AvailableInTimeline | 1=显示在招募面板，0=不显示（不可正常招募，仅 MOD 解锁） |
| 6 | GenerateDuplicateIndividuals | 1=同一伟人可重复出现 |
| 7 | PseudoYieldType | `PSEUDOYIELD_GPP_xxx`，查 `PseudoYieldType.txt` GPP 节 |
| 8 | IconString | 图标，如 `[ICON_GreatGeneral]`。如无新导，只用已有 |
| 9 | ActionIcon | 行动图标，如 `ICON_UNITOPERATION_GENERAL_ACTION`。如无新导，只用已有 |
| 10 | MaxPlayerInstances | NULL=不限，1=每玩家一次（先知） |

---

## 三、GreatPersonIndividuals（伟人个体，39 列）

### 3.1 基础 INSERT 模板（最小集）

```sql
INSERT INTO GreatPersonIndividuals (
    GreatPersonIndividualType,
    Name,
    GreatPersonClassType,
    EraType,
    Gender,
    ActionCharges
) VALUES
(
    'GREAT_PERSON_INDIVIDUAL_SIQI_{SHORT}',
    'LOC_GREAT_PERSON_INDIVIDUAL_SIQI_{SHORT}_NAME',
    'GREAT_PERSON_CLASS_SIQI_{SHORT}',
    'ERA_ANCIENT',
    'F',
    0
);
```

> `ActionCharges=0` = 无主动行动（巨作型）。能力型通常 =1。

### 3.2 逐列参考

**基础身份：**

| # | 列名 | 值参考 | 说明 |
|---|------|--------|------|
| 1 | GreatPersonIndividualType | `GREAT_PERSON_INDIVIDUAL_SIQI_{SHORT}` | 伟人个体标识 |
| 2 | Name | LOC | 名称 |
| 3 | GreatPersonClassType | 见上文 | 所属类别 |
| 4 | EraType | `EraType.txt`（ERA_ANCIENT～ERA_FUTURE） | 时代 |
| 5 | Gender | `'M'` / `'F'` | 性别（影响模型） |

**行动次数 / 文本覆盖：**

| # | 列名 | 说明 | 参考 |
|---|------|------|------|
| 6 | ActionCharges | 行动次数（0=无主动行动） | 通常 0 或 1 |
| 28 | ActionNameTextOverride | 行动按钮文本 LOC | 最常用 `LOC_GREATPERSON_ACTION_NAME_RETIRE`（"解散"） |
| 29 | ActionEffectTextOverride | 行动效果描述 LOC | `LOC_GREATPERSON_{NAME}_ACTIVE` |
| 30 | ActionEffectTileHighlighting | 行动时高亮地块（默认 1） | 按需 |
| 31 | BirthNameTextOverride | 被动诞生文本 LOC（极少用） | — |
| 32 | BirthEffectTextOverride | 被动效果描述 LOC（极少用） | — |

> Birth = **被动**（诞生时触发），Action = **主动**（使用行动时触发）。

**行动地块限制（能力型）：**

| # | 列名 | 类型 | 说明 |
|---|------|------|------|
| 7 | ActionRequiresOwnedTile | BOOLEAN | 需要己方领土 |
| 8 | ActionRequiresUnownedTile | BOOLEAN | 需要无主地块 |
| 9 | ActionRequiresAdjacentMountain | BOOLEAN | 需相邻山脉 |
| 10 | ActionRequiresAdjacentOwnedTile | BOOLEAN | 需相邻己方领土 |
| 11 | ActionRequiresAdjacentBarbarianUnit | BOOLEAN | 需相邻蛮族（布狄卡） |
| 12 | ActionRequiresOnOrAdjacentNaturalWonder | BOOLEAN | 需在/相邻自然奇观 |
| 13 | ActionRequiresOnOrAdjacentFeatureType | TEXT | 需在/相邻特定地貌。唯一样例：`FEATURE_JUNGLE`，查 `FeatureType.txt` |
| 14 | ActionRequiresIncompleteWonder | BOOLEAN | 需未完成奇观（大工加速） |
| 15 | ActionRequiresIncompleteSpaceRaceProject | BOOLEAN | 需未完成航天项目 |
| 16 | ActionRequiresVisibleLuxury | BOOLEAN | 需可见奢侈资源 |

**行动单位/建筑限制（能力型）：**

| # | 列名 | 值参考 | 说明 |
|---|------|--------|------|
| 17 | ActionRequiresNoMilitaryUnit | BOOLEAN | 地块上无军事单位 |
| 18 | ActionRequiresPlayerRelicSlot | BOOLEAN | 需玩家有遗物槽 |
| 19 | ActionRequiresMilitaryUnitDomain | `MilitaryDomain.txt` | `DOMAIN_LAND` / `DOMAIN_SEA` |
| 20 | ActionRequiresUnitMilitaryFormation | — | 仅 `STANDARD_MILITARY_FORMATION` |
| 21 | ActionRequiresNearbyUnitWithTagA | `AbilityClassTag.txt` | `CLASS_MELEE` / `CLASS_LIGHT_CAVALRY` / `CLASS_HEAVY_CAVALRY` / `CLASS_ANTI_CAVALRY` |
| 22 | ActionRequiresNearbyUnitWithTagB | 同上 | 同上 |
| 23 | ActionRequiresLandMilitaryUnitWithinXTiles | INTEGER | X 格内需有陆军 |
| 24 | ActionRequiresEnemyMilitaryUnitWithinXTiles | INTEGER | X 格内需有敌军 |
| 25 | ActionRequiresCityGreatWorkObjectType | `GreatWorkObjectType.txt` | 城市需有特定巨作类型（如 `GREATWORKOBJECT_ARTIFACT`） |
| 26 | ActionRequiresCompletedDistrictType | `DistrictType.txt` | 需已完成特定区域（如 `DISTRICT_CITY_CENTER`） |

**其他限制：**

| # | 列名 | 说明 |
|---|------|------|
| 27 | ActionRequiresGoldCost | 行动消耗金币 |
| 33 | AreaHighlightRadius | 高亮半径（需配合对应条件列使用，如 `ActionRequiresCompletedDistrictType` 配合 1 表示目标城市中心周围 1 格高亮） |
| 35 | ActionRequiresEnemyTerritory | 需在敌方领土 |
| 36 | ActionRequiresCityStateTerritory | 需在城邦领土 |
| 37 | ActionRequiresNonHostileTerritory | 需在非敌对领土 |
| 38 | ActionRequiresSuzerainTerritory | 需在宗主国领土 |
| 26 | ActionRequiresMissingBuildingType | 城市需缺少某建筑 |
| 39 | ActionRequiresUnitCanGainExperience | 需单位可获取经验 |

---

## 四、GreatPersonIndividualBirthModifiers

被动（诞生时）触发。**需要配合 ModifierStrings 显示描述。**

```sql
INSERT INTO GreatPersonIndividualBirthModifiers (GreatPersonIndividualType, ModifierId) VALUES
('GREAT_PERSON_INDIVIDUAL_SIQI_{SHORT}', 'MODIFIER_SIQI_G0030_X_ABILITY_Y');
```

```sql
-- 必须配合 ModifierStrings（Context=Summary）才能在伟人面板显示
INSERT INTO ModifierStrings (ModifierId, Context, Text) VALUES
('MODIFIER_SIQI_G0030_X_ABILITY_Y', 'Summary', 'LOC_MODIFIER_SIQI_G0030_X_ABILITY_Y_SUMMARY');
```

---

## 五、GreatPersonIndividualActionModifiers

主动（使用行动时）触发。比 Birth 多一个 `AttachmentTargetType` 参数。

```sql
INSERT INTO GreatPersonIndividualActionModifiers (GreatPersonIndividualType, ModifierId, AttachmentTargetType) VALUES
('GREAT_PERSON_INDIVIDUAL_SIQI_{SHORT}', 'MODIFIER_SIQI_G0030_1_ADJUST_xxx', 'GREAT_PERSON_ACTION_ATTACHMENT_TARGET_PLAYER');
```

> **AttachmentTargetType 可选值（6 个）：**
> | 值 | 说明 |
> |----|------|
> | `GREAT_PERSON_ACTION_ATTACHMENT_TARGET_PLAYER` | 挂到玩家 |
> | `GREAT_PERSON_ACTION_ATTACHMENT_TARGET_CITY` | 挂到目标城市 |
> | `GREAT_PERSON_ACTION_ATTACHMENT_TARGET_DISTRICT_IN_TILE` | 挂到格上区域 |
> | `GREAT_PERSON_ACTION_ATTACHMENT_TARGET_DISTRICT_WONDER_IN_TILE` | 挂到格上奇观 |
> | `GREAT_PERSON_ACTION_ATTACHMENT_TARGET_UNIT_GREATPERSON` | 挂到伟人自身 |
> | `GREAT_PERSON_ACTION_ATTACHMENT_TARGET_UNIT_DOMAIN_MILITARY_IN_TILE` | 挂到格上军事单位 |

---

## 六、GreatPersonIndividualIconModifiers

```sql
INSERT INTO GreatPersonIndividualIconModifiers (GreatPersonIndividualType, OverrideUnitIcon) VALUES
('GREAT_PERSON_INDIVIDUAL_SIQI_{SHORT}', 'ICON_UNIT_SIQI_XXX');
```

---

## 七、ExcludedGreatPersonClasses

```sql
INSERT INTO ExcludedGreatPersonClasses (GreatPersonClassType, TraitType) VALUES
('GREAT_PERSON_CLASS_PROPHET', 'TRAIT_CIVILIZATION_SIQI_C0022_C1');
```

> 排除某文明不能招募的伟人类别。

---

## 八、Map_GreatPersonClasses

```sql
INSERT INTO Map_GreatPersonClasses (MapSizeType, GreatPersonClassType, MaxWorldInstances) VALUES
('MAPSIZE_DUEL', 'GREAT_PERSON_CLASS_SIQI_{SHORT}', 3);
```

| MapSizeType | 说明 |
|-------------|------|
| `MAPSIZE_DUEL` | 决斗 |
| `MAPSIZE_TINY` | 极微 |
| `MAPSIZE_SMALL` | 较小 |
| `MAPSIZE_STANDARD` | 标准 |
| `MAPSIZE_LARGE` | 较大 |
| `MAPSIZE_HUGE` | 巨大 |

> 一般不写，有需求时才写。查 `EraType.txt` 和 `GreatPersonClassType.txt`。

---

## 九、巨作路线

### 9.1 GreatWorkObjectTypes

```sql
INSERT INTO GreatWorkObjectTypes (GreatWorkObjectType, Value, PseudoYieldType, Name, IconString) VALUES
('GREATWORKOBJECT_SIQI_{SHORT}', 2, 'PSEUDOYIELD_GREATWORK_WRITING', 'LOC_GREATWORKOBJECT_SIQI_{SHORT}_NAME', '[ICON_GreatWork_SIQI_{SHORT}]');
```

> `GreatWorkObjectType` 可正常新建，无 UI 问题。
> `GreatWorkSlotType` 新建有 UI 问题，不建议新建。
> 已有枚举见 `GreatWorkObjectType.txt`。

### 9.2 GreatWorks

```sql
INSERT INTO GreatWorks (
    GreatWorkType,
    GreatWorkObjectType,
    GreatPersonIndividualType,
    Name,
    Audio,
    Image,
    Quote,
    Tourism,
    EraType
) VALUES
(
    'GREATWORK_SIQI_{SHORT}',
    'GREATWORKOBJECT_MUSIC',
    'GREAT_PERSON_INDIVIDUAL_SIQI_{SHORT}',
    'LOC_GREATWORK_SIQI_{SHORT}_NAME',
    'GM_Vivaldi_Winter',
    NULL,
    NULL,
    4,
    'ERA_ANCIENT'
);
```

| # | 列名 | 说明 | 参考 |
|---|------|------|------|
| 1 | GreatWorkType | 巨作标识 | **必写** |
| 2 | GreatWorkObjectType | 对象类型 | 查 `GreatWorkObjectType.txt` |
| 3 | GreatPersonIndividualType | 创作此巨作的伟人个体 | 可 NULL |
| 4 | Name | 名称 LOC |  |
| 5 | Audio | 音频 Key（音乐类用），只用已有或 NULL | 如 `GM_Vivaldi_Winter` |
| 6 | Image | 图片（难自定义），一般 NULL |  |
| 7 | Quote | 引言 LOC（著作/艺术类），作家/艺术家用 |  |
| 8 | Tourism | 旅游业绩 | 见下表 |
| 9 | EraType | 时代 | 查 `EraType.txt` |

> **Tourism 参考：**
> | 类型 | 值 |
> |------|-----|
> | 著作 (Writing) | 2 |
> | 美术 (Portrait/Landscape/Sculpture/Religious) | 2 |
> | 音乐 (Music) | 4 |
> | 文物 (Artifact) | 3 |
> | 遗物 (Relic) | 8 |

### 9.3 GreatWork_ValidSubTypes

```sql
INSERT INTO GreatWork_ValidSubTypes (GreatWorkSlotType, GreatWorkObjectType) VALUES
('GREATWORKSLOT_WRITING', 'GREATWORKOBJECT_WRITING');
```

> 已有枚举见 `GreatWorkSlotType.txt`（不建议新建）和 `GreatWorkObjectType.txt`。

### 9.4 GreatWork_YieldChanges

```sql
INSERT INTO GreatWork_YieldChanges (GreatWorkType, YieldType, YieldChange) VALUES
('GREATWORK_SIQI_{SHORT}', 'YIELD_CULTURE', 2),
('GREATWORK_SIQI_{SHORT}', 'YIELD_SCIENCE', 2);
```

| YieldType | Change | 场景 |
|---|------|------|
| `YIELD_CULTURE` | 2 | 标准著作/美术 |
| `YIELD_CULTURE` | 3 | 文物 |
| `YIELD_CULTURE` | 4 | 音乐 |
| `YIELD_FAITH` | 4 | 遗物（秘密结社） |

### 9.5 GreatWorkModifiers

```sql
INSERT INTO GreatWorkModifiers (GreatWorkType, ModifierID) VALUES
('GREATWORK_SIQI_{SHORT}', 'MODIFIER_SIQI_xxx');
```

> **已知 bug**：伟人创作的巨作，需**移动巨作后** Modifier 才会生效。

### 9.6 GreatWorks_ImprovementType

```sql
INSERT INTO GreatWorks_ImprovementType (GreatWorkType, ResourceType) VALUES
('GREATWORK_PRODUCT_HONEY_1', 'RESOURCE_HONEY');
```

> 垄断模式：巨作产品关联资源。`ImprovementType` 可选（官方通常只填 `ResourceType`）。

### 9.7 GreatWorks_MODE

```sql
INSERT INTO GreatWorks_MODE (GreatWorkType, RequiredGovernor) VALUES
('GREATWORK_RELIC_25', 'GOVERNOR_VOIDSINGERS');
```

> 秘密结社：遗物需要特定总督（虚空结社）。

---

## 十、Text — 本地化文本

### 能力型

```sql
-- 伟人类别
('zh_Hans_CN', 'LOC_GREAT_PERSON_CLASS_SIQI_{SHORT}_NAME', '{类别名}'),
-- 伟人个体
('zh_Hans_CN', 'LOC_GREAT_PERSON_INDIVIDUAL_SIQI_{SHORT}_NAME', '{伟人名}'),
-- 主动效果描述
('zh_Hans_CN', 'LOC_GREAT_PERSON_INDIVIDUAL_SIQI_{SHORT}_EFFECT', '{主动效果文本}'),
```

### 巨作型（额外）

```sql
-- 巨作名
('zh_Hans_CN', 'LOC_GREATWORK_SIQI_{SHORT}_NAME', '{巨作名}'),
-- 引言（作家/艺术家用）
('zh_Hans_CN', 'LOC_GREATWORK_SIQI_{SHORT}_QUOTE', '{引言}'),
```

---

## 十一、Enum 文件

| 文件 | 使用于 |
|------|--------|
| `EraType.txt` | GreatPersonIndividuals.EraType, GreatWorks.EraType |
| `PseudoYieldType.txt`（GPP 节） | GreatPersonClasses.PseudoYieldType |
| `PseudoYieldType.txt`（GREATWORK 节） | GreatWorkObjectTypes.PseudoYieldType |
| `GreatWorkObjectType.txt` | GreatWorks.GreatWorkObjectType, GreatWork_ValidSubTypes |
| `GreatWorkSlotType.txt` | GreatWork_ValidSubTypes（不建议新建） |
| `MilitaryDomain.txt` | ActionRequiresMilitaryUnitDomain |
| `AbilityClassTag.txt` | ActionRequiresNearbyUnitWithTagA/B |
| `DistrictType.txt` | ActionRequiresCompletedDistrictType |
| `FeatureType.txt` | ActionRequiresOnOrAdjacentFeatureType |
| `AdvisorType.txt` | 不直接使用（列参考用） |
