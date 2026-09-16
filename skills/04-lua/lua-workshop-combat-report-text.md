# lua-workshop-combat-report-text -- 战斗报告文本替换 UI 模式

从工坊 Mod **Simplified Combat Reports** (1459524722) 提炼。核心模式：通过 XML `<Replace>` 标签覆盖游戏原版 `LOC_COMBAT_*` 文本键，实现战斗报告简化/重写，**无需修改任何 Lua 逻辑**。

---

## 核心机制

Civ6 的所有战斗报告文本都通过 `LOC_COMBAT_*` 系列 LocalizedText 键提供。Mod 使用 `<Replace>` 标签直接覆盖这些键的文本内容，替换为更简洁、带图标和信息浓度更高的版本。

**关键认知**：这个模式**完全不需要 Lua 端实现任何新逻辑**。Lua 文件 `FF16_Config_ICR.lua` 仅做一件事 —— 广播 "本 Mod 已启用" 事件通知其他 Mod。

```lua
function BroadcastModInUse()
    LuaEvents.FF16_ImprovedCombatReports();
end
Events.LoadGameViewStateDone.Add( BroadcastModInUse );
```

---

## XML 配合

本系统的核心实现完全在 XML 层面，通过 `<Replace>` 标签覆盖 30 个 `LOC_COMBAT_*` 文本键完成战斗报告重写。**不需要 Lua 逻辑**——Lua 文件仅用于广播 Mod 存在事件。

### 文件结构

```
Text/LocalizedText.xml  → 包含所有 <Replace> 块的单一 XML 文件
                          （按语言分组：en_US, ja_JP, zh_Hans_CN 等）
```

### 控件注入

无需新增 UI 控件。战斗报告文本通过游戏引擎内置的 `CombatLog` UI 组件自动渲染，`<Replace>` 标签直接修改其文本内容。

---

## XML 替换模式

### 基本语法

战斗报告文本通过 4 个索引参数注入具体信息（`{1_UnitName}`, `{2_Num}`, `{3_EnUName}`, `{4_Num}`等）。

```xml
<GameData>
    <LocalizedText>
        <Replace Tag="LOC_COMBAT_YOUR_UNIT_WITHDREW" Language="en_US">
            <Text>Your {1_UnitName} [ICON_Strength] Enemy {3_EnUName}!
[NEWLINE]Results: [COLOR_RED]Lost {2_Num}HP.[ENDCOLOR] / [COLOR_FLOAT_GOLD]Dealt {4_Num}HP DMG!</Text>
        </Replace>
    </LocalizedText>
</GameData>
```

### 涉及的完整战斗文本键清单

该 Mod 覆盖了所有 30 个 `LOC_COMBAT_*` 键，按场景分类：

#### 攻击 - 非决定性结果（Attacking - Non Conclusive）
| 键 | 含义 |
|---|------|
| `LOC_COMBAT_YOUR_UNIT_WITHDREW` | 你的单位攻击后撤退 |
| `LOC_COMBAT_YOUR_UNIT_WITHDREW_CITY` | 你的单位攻击城市后撤退 |
| `LOC_COMBAT_YOUR_UNIT_WITHDREW_ANTI_AIR` | 你的单位被防空火力击退 |
| `LOC_COMBAT_YOUR_UNIT_WITHDREW_INTERCEPTED` | 你的单位被拦截击退 |
| `LOC_COMBAT_YOUR_UNIT_ATTACKED_ENEMY_DISTRICT_DEFENSES` | 攻击敌方区域防御 |
| `LOC_COMBAT_YOUR_UNIT_BOMBARDED_ENEMY` | 你的单位轰炸敌方 |
| `LOC_COMBAT_YOUR_UNIT_ATTACKED_ENEMY_DISTRICT` | 你的单位攻击敌方区域 |
| `LOC_COMBAT_YOUR_UNIT_STRAFED_ENEMY` | 你的单位扫射敌方 |
| `LOC_COMBAT_YOUR_UNIT_BOMBED_ENEMY` | 你的单位轰炸敌方 |

#### 攻击 - 决定性结果（Attacking - Conclusive）
| 键 | 含义 |
|---|------|
| `LOC_COMBAT_YOUR_UNIT_DESTROYED_ENEMY` | 你的单位摧毁了敌方 |
| `LOC_COMBAT_YOUR_UNIT_DIED_ATTACKING` | 你的单位攻击中阵亡 |
| `LOC_COMBAT_YOUR_UNIT_DIED_ATTACKING_ANTI_AIR` | 你的单位被防空火力摧毁 |
| `LOC_COMBAT_YOUR_UNIT_DIED_ATTACKING_INTERCEPTED` | 你的单位攻击中被拦截摧毁 |
| `LOC_COMBAT_YOUR_UNIT_DIED_ATTACKING_CITY` | 你的单位攻击城市时阵亡 |

#### 占领（Captures）
| 键 | 含义 |
|---|------|
| `LOC_COMBAT_YOUR_UNIT_CAPTURED_ENEMY_UNIT` | 你的单位俘获敌单位 |
| `LOC_COMBAT_YOUR_UNIT_WAS_CAPTURED_BY_ENEMY_UNIT` | 你的单位被敌俘获 |
| `LOC_COMBAT_YOUR_CITY_WAS_CAPTURED` | 你的城市被占领 |
| `LOC_COMBAT_YOUR_UNIT_CAPTURED_ENEMY_CITY` | 你的单位占领敌城 |

#### 防御（Defending）
| 键 | 含义 |
|---|------|
| `LOC_COMBAT_ENEMY_UNIT_WITHDREW` | 敌方攻击后撤退 |
| `LOC_COMBAT_YOUR_UNIT_WAS_BOMBARDED_BY_ENEMY_DISTRICT` | 你的单位被敌区域轰炸 |
| `LOC_COMBAT_YOUR_UNIT_WAS_BOMBARDED_BY_ENEMY` | 你的单位被敌方轰炸 |
| `LOC_COMBAT_YOUR_UNIT_DIED_DEFENDING` | 你的单位防御中阵亡 |
| `LOC_COMBAT_YOU_KILLED_ENEMY_UNIT_DEFENDING_CITY` | 防御城市时击杀敌单位 |
| `LOC_COMBAT_YOUR_DISTRICT_DESTROYED_ENEMY` | 你的区域摧毁了敌单位 |
| `LOC_COMBAT_YOUR_DISTRICT_BOMBARDED_ENEMY` | 你的区域轰炸敌单位 |
| `LOC_COMBAT_ENEMY_UNIT_WITHDREW_INTERCEPTING` | 你的单位拦截击退敌方 |
| `LOC_COMBAT_YOUR_UNIT_DIED_INTERCEPTING` | 你的单位拦截中阵亡 |
| `LOC_COMBAT_YOU_KILLED_ENEMY_UNIT` | 防御时击杀敌单位 |
| `LOC_COMBAT_YOUR_UNIT_WAS_STRAFED_BY_ENEMY` | 你的单位被敌方扫射 |
| `LOC_COMBAT_YOUR_DISTRICT_WAS_ATTACKED_BY_ENEMY` | 你的区域被敌攻击 |
| `LOC_COMBAT_YOUR_DISTRICT_DEFENSE_WAS_ATTACKED_BY_ENEMY` | 你的区域防御被攻击 |

#### 大规模杀伤武器（WMD）
| 键 | 含义 |
|---|------|
| `LOC_COMBAT_YOUR_WMD_SUCCEEDED` | 你的 WMD 攻击成功 |
| `LOC_COMBAT_YOUR_WMD_FAILED_HIGH_DAMAGE` | 你的 WMD 因高伤害失败 |
| `LOC_COMBAT_ENEMY_WMD_SUCCEEDED` | 敌方 WMD 攻击成功 |
| `LOC_COMBAT_ENEMY_WMD_FAILED_HIGH_DAMAGE` | 阻止了敌方 WMD |

---

## 可用参数表

每个 `LOC_COMBAT_*` 键在游戏引擎中注入的参数不同。以下是从所有替换文本中提取的参数名：

| 参数 | 含义 | 出现频率 |
|------|------|---------|
| `{1_UnitName}` | 你的单位名称 | 攻击类、占领类 |
| `{2_UnitName}` | 你的单位名称（变体） | 防空/拦截被击、防御死亡 |
| `{1_Name}` | 你的区域名称 | 区域轰炸类 |
| `{2_Num}` | 你损失的生命值 | 几乎所有撤退/阵亡类 |
| `{3_Num}` | 损失生命值（变体） | 防空/拦截/防御类 |
| `{2_EnUName}` | 敌方简短单位名 | 攻击/轰炸/扫射类 |
| `{3_EnUName}` | 敌方简短单位名（变体） | 撤退类 |
| `{3_UnitName}` | 敌方完整单位名 | 摧毁/俘获类 |
| `{3_EnemyAdjective}` | 敌方文明形容词 | 防御死亡/击杀类 |
| `{4_EnemyUnitName}` | 敌方完整单位名 | 防御死亡/击杀/拦截死亡 |
| `{5_EnemyUnitName}` | 敌方完整单位名（变体） | 防空被击 |
| `{4_Num}` | 你造成的伤害 | 攻击类 |
| `{5_Num}` | 你造成的伤害（变体） | 防御死亡/击杀类 |
| `{6_Num}` | 你造成的伤害（变体） | 拦截类 |
| `{3_Damage}` | 区域造成的伤害 | 区域轰炸类 |
| `{2_Name}` | 敌方区域/改良名称 | 攻击区域类 |
| `{3_CityName}` | 敌方城市名称 | 占领城市类 |
| `{1_CityName}` | 你的城市名称 | 城市被占领 |
| `{2_CityName}` | 你的城市名称（变体） | 防御城市击杀 |
| `{1_EnemyAdjective}` | 敌方文明形容词 | WMD类 |
| `{2_EnemyUnitName}` | 敌方单位名 | WMD类 |
| `{4_Num}DEF` | 防御工事伤害 | 区域防御被攻击 |

---

## 颜色和图标约定

### 颜色码
| 颜色码 | 用途 |
|--------|------|
| `[COLOR_RED]` | 负面结果（损失HP、单位阵亡、城市被占） |
| `[COLOR_FLOAT_GOLD]` | 正面结果（造成伤害、摧毁敌人） |
| `[ENDCOLOR]` | 颜色结束标记 |

### 图标
| 图标 | 用途 |
|------|------|
| `[ICON_Strength]` | 近战攻击 |
| `[ICON_Ranged]` | 远程攻击 |
| `[ICON_Bombard]` | 轰炸/区域攻击 |

---

## 多语言支持模式

Mod 为每种语言提供独立的 `<Replace>` 块，使用 `Language` 属性区分。示例：

```xml
<!-- English -->
<Replace Tag="LOC_COMBAT_YOUR_UNIT_WITHDREW" Language="en_US">
    <Text>Your {1_UnitName} [ICON_Strength] Enemy {3_EnUName}!
[NEWLINE]Results: [COLOR_RED]Lost {2_Num}HP.[ENDCOLOR] / [COLOR_FLOAT_GOLD]Dealt {4_Num}HP DMG!</Text>
</Replace>

<!-- Japanese -->
<Replace Tag="LOC_COMBAT_YOUR_UNIT_WITHDREW" Language="ja_JP">
    <Text>あなたの{1_UnitName} [ICON_Strength] 敵の{3_EnUName}！
[NEWLINE]結果: [COLOR_RED]{2_Num}HPを喪失[ENDCOLOR] / [COLOR_FLOAT_GOLD]{4_Num}ダメージを与えた！[ENDCOLOR]</Text>
</Replace>
```

---

## 实现模板

### XML 文件结构（Text/xxx.xml）

```xml
<?xml version="1.0" encoding="utf-8"?>
<GameData>
    <LocalizedText>
        <!-- 按场景分组注释 -->
        <!-- Attacking - Non Conclusive -->
        <Replace Tag="LOC_COMBAT_YOUR_UNIT_WITHDREW" Language="en_US">
            <Text>Your {1_UnitName} [ICON_Strength] Enemy {3_EnUName}!
[NEWLINE]Results: [COLOR_RED]Lost {2_Num}HP.[ENDCOLOR] / [COLOR_FLOAT_GOLD]Dealt {4_Num}HP DMG!</Text>
        </Replace>
        <!-- ... 其余键 ... -->
    </LocalizedText>
</GameData>
```

### 可选 Lua 文件（广播 Mod 存在）

```lua
function BroadcastModInUse()
    LuaEvents.MyMod_Enabled();
end
Events.LoadGameViewStateDone.Add( BroadcastModInUse );
```

---

## 注意事项

1. **参数顺序不可更改**：每个 `LOC_COMBAT_*` 键的参数顺序由游戏引擎硬编码，不可调整
2. **参数存在性**：不同键的参数集合不同（如 WMD 类只有 `{1_UnitName}` 和 `{2_EnemyUnitName}`），需要用正确的参数编号
3. **`{2_Num}` vs `{3_Num}`**：同一数值在不同键中可能使用不同参数编号，需对照原版或实测确定
4. **`LOC_GRAMMAR_A_AN`**：用于英语中自动选择 "a" 或 "an"（如 `{LOC_GRAMMAR_A_AN << {4_EnemyAdjective}}`）
5. **format 变量风格**：参数格式为 `{序号_类型}`，类型包括 `UnitName`、`EnUName`、`Num`、`CityName`、`EnemyAdjective`、`Name`、`Damage`
6. **Language 属性**：仅在 `<LocalizedText>` 内部的 `<Replace>` 使用；如在 `<BaseGameText>` 中则不需要
7. **此模式不需要 Lua 核心逻辑**：纯 XML 替换即可完成功能
