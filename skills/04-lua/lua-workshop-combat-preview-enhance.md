# lua-workshop-combat-preview-enhance -- 战斗预览面板增强 UI 模式

从工坊 Mod **Better Combat Info** (3254574708) 提炼。核心模式：完整替换游戏原生 `UnitPanel.lua` + `UnitPanel.xml`，在战斗预览中添加伤害范围预判、多层血条、力量差值显示、修饰符分页列表等功能。

---

## 架构概览

该 Mod 通过 **ImportFiles** 方式完整替换了游戏的 `UnitPanel.lua` 和 `UnitPanel.xml`。它并非在原版上打补丁，而是以原版代码为基础进行**内联扩展**，在关键函数中添加 BCI（Better Combat Info）标记的新逻辑。

Mod 的 `.dep` 文件声明了兼容性（与 Enhanced Heal Tooltip 兼容，与 Black Death Mod 不兼容）。

---

## 核心增强功能

### 1. 战斗伤害范围计算

原理：从 `GlobalParameters` 读取战斗公式参数，计算可能的**最小/最大伤害**。

```lua
function GetPossibleCombatDamage_BetterCombatInfo(reverse)
    local attacker = m_combatResults[CombatResultParameters.ATTACKER];
    local defender = m_combatResults[CombatResultParameters.DEFENDER];

    local iAttackerStrength = attacker[CombatResultParameters.COMBAT_STRENGTH]
                            + attacker[CombatResultParameters.STRENGTH_MODIFIER];
    local iDefenderStrength = defender[CombatResultParameters.COMBAT_STRENGTH]
                            + defender[CombatResultParameters.STRENGTH_MODIFIER];

    -- 获取力量差（reverse 参数用于近战反击伤害计算）
    local combat_Difference = iAttackerStrength - iDefenderStrength
    if reverse then combat_Difference = -combat_Difference end

    -- 从 GlobalParameters 读取公式参数
    local base_combat_damage = GlobalParameters.COMBAT_BASE_DAMAGE or 24
    local max_extra_combat_damage = GlobalParameters.COMBAT_MAX_EXTRA_DAMAGE or 12
    local combat_power_scaling = GlobalParameters.COMBAT_POWER_SCALING or 0.04

    -- 基于 e^(power * diff) 的指数伤害公式
    local min_combat_damage = math.floor(
        base_combat_damage * math.exp(combat_power_scaling * combat_Difference)
    )
    local max_combat_damage = math.floor(
        (base_combat_damage + max_extra_combat_damage)
        * math.exp(combat_power_scaling * combat_Difference)
    )

    return min_combat_damage, max_combat_damage
end
```

**关键 `reverse` 参数**：近战攻击中攻击方也会受到反击伤害。`reverse=true` 时力量差反转，用于估算己方受到的反击伤害范围。

### 2. 显示条件判定

BCI 增强信息仅在满足以下条件时显示：

```lua
function CanShowCombatDetail_BetterCombatInfo()
    -- 条件 1: m_combatResults 存在
    -- 条件 2: 防御者是单位（非城区/地块）
    -- 条件 3: 防御者有战斗力（力量 > 0）
    -- 条件 4: 攻击者不是空军单位
    -- 条件 5: 战斗类型是近战/远程/轰炸
    local defenderID = defender[CombatResultParameters.ID];
    if (defenderID.type == ComponentType.UNIT) then
        local pkDefender = UnitManager.GetUnit(defenderID.player, defenderID.id);
        if (pkDefender ~= nil) and iDefenderStrength > 0 then
            local attacker_domain = GameInfo.Units[attacker_typeStr].Domain
            if attacker_domain ~= "DOMAIN_AIR" then
                if combatType == CombatTypes.MELEE
                or combatType == CombatTypes.RANGED
                or combatType == CombatTypes.BOMBARD then
                    showCombatDetails = true
                end
            end
        end
    end
end
```

### 3. 三层血量条

在原版双层血量条（当前血 + 预估伤害后血）基础上，增加中间层：**当前血 + 最小预估伤害**。

```lua
function RealizeHealthMeter_BetterCombatInfo(control, percent,
    controlShadow2, shadowPercent2,   -- 新增中间层
    controlShadow,  shadowPercent)

    -- 三层颜色定义
    local METER_HP_GOOD_MID_SHADOW  = UI.GetColorValueFromHexLiteral(0xB24BE810)
    local METER_HP_OK_MID_SHADOW    = UI.GetColorValueFromHexLiteral(0xB22DFFF8)
    local METER_HP_BAD_MID_SHADOW   = UI.GetColorValueFromHexLiteral(0xB20101F5)

    -- 设置主血条颜色
    if percent > 0.7 then control:SetColor(COLORS.METER_HP_GOOD)
    elseif percent > 0.4 then control:SetColor(COLORS.METER_HP_OK)
    else control:SetColor(COLORS.METER_HP_BAD) end

    -- 半圆血条缩放
    percent = (percent * 0.5) + 0.5
    shadowPercent2 = (shadowPercent2 * 0.5) + 0.5
    shadowPercent = (shadowPercent * 0.5) + 0.5

    control:SetPercent(percent)
    controlShadow2:SetPercent(shadowPercent2)   -- 最小伤害层
    controlShadow:SetPercent(shadowPercent)     -- 当前血量层
end
```

**血条三层语义**：
- **外层（controlShadow）**：当前血量（不变）
- **中间层（controlShadow2）**：当前血量 - 最小预估伤害（最乐观情景）
- **内层（control）**：当前血量 - 最大预估伤害（最悲观情景）

### 4. 战斗力量差值显示

在战斗预览中新增力量差值 UI 元素：

```lua
-- OnShowCombat() 中的 BCI 部分
local combat_difference = iAttackerStrength - iDefenderStrength
if combat_difference >= 0 then
    combat_difference_info = Locale.Lookup(
        "LOC_HUD_UNIT_PANEL_OUTCOME_STRENGTH_DIFFERENCE_POSITIVE", combat_difference)
else
    combat_difference_info = Locale.Lookup(
        "LOC_HUD_UNIT_PANEL_OUTCOME_STRENGTH_DIFFERENCE_NEGATIVE", combat_difference)
end
Controls.CombatStrength_Difference_Text_BCI:SetText(combat_difference_info)
Controls.CombatStrength_Difference_BG_BCI:SetHide(false)
```

### 5. 战斗结果预判（生存分析）

基于伤害范围判断攻击方/防御方是否会死亡：

```lua
-- 防御方死亡判断
if defender_health - min_combat_damage <= 0 then
    defender_result = Locale.Lookup("LOC_HUD_UNIT_PANEL_OUTCOME_JUDGEMENT_DEFENDER_DIE", ...)
elseif (defender_health - min_combat_damage > 0)
   and (defender_health - max_combat_damage <= 0) then
    defender_result = Locale.Lookup("LOC_HUD_UNIT_PANEL_OUTCOME_JUDGEMENT_DEFENDER_POSSIBLE_DIE", ...)
else
    defender_result = Locale.Lookup("LOC_HUD_UNIT_PANEL_OUTCOME_JUDGEMENT_DEFENDER_LIVE", ...)
end

-- 攻击方死亡判断（仅近战，因为远程不会受反击）
if combatType == CombatTypes.MELEE then
    if attacker_health - min_combat_damage_r <= 0 then
        attacker_result = Locale.Lookup("LOC_HUD_UNIT_PANEL_OUTCOME_JUDGEMENT_ATTACKER_DIE", ...)
    -- ... 可能死亡 / 不会死亡
    end
end
```

### 6. 战斗力修饰符分页列表

从 CombatResultParameters 的多个 PREVIEW_TEXT_* 字段提取修饰符文本，按类别归类并分页显示。

```lua
function GetCombatModifierList(combatantHash)
    local baseStrengthText = baseStrengthValue .. " " ..
        Locale.Lookup("LOC_COMBAT_PREVIEW_BASE_STRENGTH");

    -- 按类别提取修饰符
    modifierList, modifierListSize = AddModifierToList(modifierList, ...,
        baseStrengthText, "ICON_STRENGTH");
    -- interceptorModifierText → "ICON_STATS_INTERCEPTOR"
    -- antiAirModifierText      → "ICON_STATS_ANTIAIR"
    -- healthModifierText       → "ICON_DAMAGE"
    -- terrainModifierText      → "ICON_STATS_TERRAIN"
    -- opponentModifierText     → "ICON_STRENGTH"
    -- modifierModifierText     → "ICON_STRENGTH"
    -- flankingModifierText     → "ICON_POSITION"
    -- promotionModifierText    → "ICON_PROMOTION"
    -- defenseModifierText      → "ICON_DEFENSE"
    -- resourceModifierText     → "ICON_RESOURCES"

    return modifierList, modifierListSize;
end
```

**分页机制**：`m_maxModifiersPerPage = 5`，超过 5 个修饰符时使用 AlphaAnim 分页轮播。

```lua
function UpdateModifiers(startIndex, stack, stackAnim, stackAnimCallback, stackIM,
                          modifierList, modifierCount)
    -- 从 startIndex 开始逐条添加到 Stack
    -- 检测 Stack 高度是否溢出
    -- 溢出时停止，记录 nextIndex
    -- 播放 AlphaAnim，结束后回调自身 (nextIndex)
end
```

### 7. 完整修饰符列表面板（BCI 新增）

当修饰符数量 >= 5 时，在战斗力旁边显示完整的修饰符列表面板。

```lua
function BuildCombatStrengthModifiers_BCI(bci_background, bci_text, hide,
                                           modifierList, modifierCount)
    if modifierList == nil or modifierCount == nil or modifierCount == 0 then
        bci_background:SetHide(true); return
    end

    local label_text = ""
    local valid_modifier_num = 0
    for i=0, modifierCount, 1 do
        if modifierList[i] ~= nil then
            local modifier_text = modifierEntry["text"]
            local modifier_icon = modifierEntry["icon"]
            -- 尝试 22px 图标 → 16px 图标 → 纯文字
            if textureSheet_22 ~= nil then
                label_text = label_text .. "[ICON_" .. modifier_icon .. "] " .. modifier_text
            else
                label_text = label_text .. modifier_text
            end
        end
    end

    -- 仅当 >= 5 条时才显示（少量修饰符在右侧小轮播中已可见）
    if valid_modifier_num >= 5 then
        bci_background:SetHide(false);
        bci_text:SetText(label_text);
        -- 根据行数调整面板高度和偏移
        if valid_modifier_num < 10 then
            bci_background:SetSizeY(256);
            bci_background:SetOffsetY(-430)
        else
            bci_background:SetSizeY(512);
            bci_background:SetOffsetY(-560)
        end
    end
end
```

---

## XML 配合

本系统通过 **ImportFiles 完整替换** `UnitPanel.xml` 的方式注入增强控件，而非在原文件上打补丁。

### UnitPanel.xml — 替换后的战斗预览面板

在 `CombatPreviewBanners` 容器内新增以下 BCI 控件，均默认 `Hidden="1"`：

| 控件 ID | 类型 | 功能 |
|---------|------|------|
| `CombatPossibleResultBG_BCI` | Image(含Label) | 战斗结果预判文本（可能造成伤害/可能死亡等） |
| `UnitHealth_BG_BCI` | Image(含Label) | 己方单位当前血量 |
| `TargetHealth_BG_BCI` | Image(含Label) | 敌方单位当前血量 |
| `UnitCombatStrength_ModifierList_BG_BCI` | Image(含Label) | 攻击方完整修饰符列表（>=5条时显示） |
| `TargetCombatStrength_ModifierList_BG_BCI` | Image(含Label) | 防御方完整修饰符列表 |
| `CombatStrength_Difference_BG_BCI` | Image(含Label) | 力量差值（+N 或 -N） |
| `UnitHealthMeterShadow2` | Meter | 己方三层血条的中间层（最小伤害预判） |
| `TargetHealthMeterShadow2` | Meter | 敌方三层血条的中间层 |

### 文本文件

`Text/BetterCombatInfo_Text_en_US.xml` + `Text/BetterCombatInfo_Text_zh_Hans_CN.xml` 定义所有 BCI 新增文本键：
- `LOC_HUD_UNIT_PANEL_OUTCOME_STRENGTH_DIFFERENCE_*`
- `LOC_HUD_UNIT_PANEL_OUTCOME_POSSIBLE_RESULT*`
- `LOC_HUD_UNIT_PANEL_OUTCOME_JUDGEMENT_*`（攻击方/防御方死亡判据）
- `LOC_HUD_UNIT_PANEL_OUTCOME_SELF_UNIT_HEALTH` / `TARGET_UNIT_HEALTH`

### 兼容性

`.dep` 文件声明与同样替换 `UnitPanel` 的 Mod 不兼容。与 Enhanced Heal Tooltip 兼容。

---

## XML 端新增控件

在 `UnitPanel.xml` 的 `CombatPreviewBanners` 容器内新增以下 BCI 控件：

| 控件 ID | 类型 | 功能 |
|---------|------|------|
| `CombatPossibleResultBG_BCI` | Image(含Label) | 战斗结果预判文本（可能造成伤害/可能死亡等） |
| `UnitHealth_BG_BCI` | Image(含Label) | 己方单位当前血量 |
| `TargetHealth_BG_BCI` | Image(含Label) | 敌方单位当前血量 |
| `UnitCombatStrength_ModifierList_BG_BCI` | Image(含Label) | 攻击方完整修饰符列表 |
| `TargetCombatStrength_ModifierList_BG_BCI` | Image(含Label) | 防御方完整修饰符列表 |
| `CombatStrength_Difference_BG_BCI` | Image(含Label) | 力量差值（+N 或 -N） |
| `UnitHealthMeterShadow2` | Meter | 己方三层血条的中间层 |
| `TargetHealthMeterShadow2` | Meter | 敌方三层血条的中间层 |

均默认 `Hidden="1"`，由 Lua 在 `CanShowCombatDetail_BetterCombatInfo()` 通过后设为可见。

---

## 文本键定义

```xml
<!-- 力量差值 -->
LOC_HUD_UNIT_PANEL_OUTCOME_STRENGTH_DIFFERENCE_POSITIVE  → "+{1_Num}[ICON_Strength]"
LOC_HUD_UNIT_PANEL_OUTCOME_STRENGTH_DIFFERENCE_NEGATIVE  → "{1_Num}[ICON_Strength]"

<!-- 战斗结果 -->
LOC_HUD_UNIT_PANEL_OUTCOME_POSSIBLE_RESULT          → "可能造成 {2_MinNum}~{3_MaxNum} 伤害"
LOC_HUD_UNIT_PANEL_OUTCOME_POSSIBLE_RESULT_REVERSE  → "可能受到 {2_MinNum}~{3_MaxNum} 伤害"

<!-- 死亡判断 -->
LOC_HUD_UNIT_PANEL_OUTCOME_JUDGEMENT_ATTACKER_LIVE           → "不会死亡"
LOC_HUD_UNIT_PANEL_OUTCOME_JUDGEMENT_ATTACKER_POSSIBLE_DIE   → "可能死亡"
LOC_HUD_UNIT_PANEL_OUTCOME_JUDGEMENT_ATTACKER_DIE            → "必然死亡"
LOC_HUD_UNIT_PANEL_OUTCOME_JUDGEMENT_DEFENDER_LIVE           → "敌方不会死亡"
LOC_HUD_UNIT_PANEL_OUTCOME_JUDGEMENT_DEFENDER_POSSIBLE_DIE   → "敌方可能死亡"
LOC_HUD_UNIT_PANEL_OUTCOME_JUDGEMENT_DEFENDER_DIE            → "敌方必然死亡"

<!-- 血量 -->
LOC_HUD_UNIT_PANEL_OUTCOME_SELF_UNIT_HEALTH    → "{1_Health}/{2_MaxDamage}[ICON_DAMAGED]"
LOC_HUD_UNIT_PANEL_OUTCOME_TARGET_UNIT_HEALTH  → "{1_Health}/{2_MaxDamage}[ICON_DAMAGED]"
```

---

## 事件监听增强

BCI 在原版 UnitPanel 的事件监听基础上未增加新事件，但修改了以下事件处理函数中的逻辑：

| 函数 | BCI 增强内容 |
|------|-------------|
| `OnShowCombat()` | 条件判断 + 三层血条 + 修饰符列表构建 |
| `ShowCombatAssessment()` | 伤害范围 + 生存判据 + 力量差值 + 血量显示 |
| `ViewTarget()` | 目标三层血条 (TargetHealthMeterShadow2) |
| `View()` | 己方三层血条 (UnitHealthMeterShadow2) |

---

## 实现模板

### 替换文件结构

```
Mod/
  UI/
    Replacements/
      UnitPanel.lua       -- 完整替换原版文件（添加 BCI 标记的函数）
      UnitPanel.xml       -- 完整替换原版文件（添加 BCI 控件）
      UnitPanel_BetterCombatInfo.lua  -- BCI 专属函数（实际为空注释）
  Text/
    BetterCombatInfo_Text_en_US.xml
    BetterCombatInfo_Text_zh_Hans_CN.xml
  Better_Combat_Informations_UnitPanel.modinfo
```

### BCI 关键函数清单

| 函数 | 职责 |
|------|------|
| `CanShowCombatDetail_BetterCombatInfo()` | 判断是否显示 BCI 增强信息 |
| `GetPossibleCombatDamage_BetterCombatInfo(reverse)` | 计算伤害范围 [min, max] |
| `GetDefenderUnitName_BetterCombatInfo()` | 获取防御方名称+血量 |
| `GetAttackerUnitName_BetterCombatInfo()` | 获取攻击方名称+血量 |
| `RealizeHealthMeter_BetterCombatInfo(...)` | 三层血条渲染 |
| `BuildCombatStrengthModifiers_BCI(...)` | 构建完整修饰符列表文本 |
| `GetCombatModifierList(combatantHash)` | 提取修饰符列表 |

---

## 注意事项

1. **ImportFiles 完整替换**：此模式替换了整个 UnitPanel 文件，与任何同样替换 UnitPanel 的 Mod 互斥（.dep 文件中声明了不兼容关系）
2. **CombatResultParameters 依赖**：伤害预判依赖于 `CombatManager.SimulateAttackInto()` 返回的完整结果表，其中 `FINAL_DAMAGE_TO` 等字段是关键数据源
3. **GlobalParameters 硬编码默认值**：`COMBAT_BASE_DAMAGE=24`, `COMBAT_MAX_EXTRA_DAMAGE=12`, `COMBAT_POWER_SCALING=0.04` 是 fallback 值，实际运行时从 `GameInfo.GlobalParameters` 读取
4. **语言特殊处理**：`m_bci_currentLanguage` 用于判断是否为中文，中文下每行结果间加空行 `[NEWLINE][NEWLINE]`
5. **三层血条的颜色码**使用 `UI.GetColorValueFromHexLiteral(0x...)` 自定义，注意是 BGR 顺序（0xBBGGRRAA）
6. **XML 新增控件的纹理**（`CombatPreview_CombatStat_BCI_140_50.dds` 等）需要额外 dds 资源
