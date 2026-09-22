# -*- coding: utf-8 -*-
import sqlite3
import json
from collections import OrderedDict

DB_PATH = "C:/Users/24948/AppData/Local/Firaxis Games/Sid Meier's Civilization VI/Cache/DebugGameplay.sqlite"
EFFECTS_FILE = r"D:\文明6mod用文件夹\AI制作Mod\skills\07-techniques\modifiers\_modifier-unit-combat.md.effects.txt"

# Read effects list
effects_list = []
with open(EFFECTS_FILE, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line:
            effects_list.append(line)

print("Effects from file:", len(effects_list))

# Query DB
db = sqlite3.connect(DB_PATH)
db.row_factory = sqlite3.Row
c = db.cursor()

effects_data = OrderedDict()

for etype in effects_list:
    c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE EffectType = ?", (etype,))
    rows = c.fetchall()

    if etype not in effects_data:
        effects_data[etype] = {"pairs": [], "args": {}}

    for row in rows:
        mt = row["ModifierType"]
        ct = row["CollectionType"]
        pair = (mt, ct)
        if pair not in effects_data[etype]["pairs"]:
            effects_data[etype]["pairs"].append((mt, ct))

        # Get arguments for this modifier type (sample from first 10 real usages)
        c.execute("SELECT Name, Value FROM ModifierArguments WHERE ModifierId IN (SELECT ModifierId FROM Modifiers WHERE ModifierType = ?) LIMIT 20", (mt,))
        args = c.fetchall()
        for a in args:
            name = a["Name"]
            value = a["Value"]
            if name not in effects_data[etype]["args"]:
                effects_data[etype]["args"][name] = set()
            if value and value.strip():
                effects_data[etype]["args"][name].add(value)

db.close()

print("Unique effects queried:", len(effects_data))

# Save full data to JSON for reference
with open(r"D:\文明6mod用文件夹\AI制作Mod\skills\07-techniques\modifiers\_query_result_v2.json", "w", encoding="utf-8") as f:
    serializable = {}
    for k, v in effects_data.items():
        serializable[k] = {
            "pairs": [(mt, ct) for mt, ct in v["pairs"]],
            "args": {ak: sorted(av) for ak, av in v["args"].items()}
        }
    json.dump(serializable, f, ensure_ascii=False, indent=2)

print("Saved JSON. Now generating markdown...")

# === Categories ===
categories = OrderedDict()

# 1. 战斗力/属性
combat_list = [
    "EFFECT_ADJUST_ADJACENT_LEVIED_UNIT_COMBAT_BONUS",
    "EFFECT_ADJUST_NUMBER_ALLIES_UNIT_COMBAT_BONUS",
    "EFFECT_ADJUST_UNIT_AGAINST_DISTRICT_COMBAT_BONUS",
    "EFFECT_ADJUST_UNIT_ANTI_AIR_STRENGTH",
    "EFFECT_ADJUST_UNIT_ATTACK_RANGE",
    "EFFECT_ADJUST_UNIT_ADVANCED_COASTAL_RAID",
    "EFFECT_ADJUST_UNIT_ADVANCED_PILLAGING",
    "EFFECT_ADJUST_UNIT_BARBARIAN_COMBAT",
    "EFFECT_ADJUST_UNIT_BYPASS_COMBAT_UNIT",
    "EFFECT_ADJUST_UNIT_BYPASS_WALLS",
    "EFFECT_ADJUST_UNIT_BYPASS_WALLS_PROMOTION_CLASS",
    "EFFECT_ADJUST_UNIT_CANNOT_ATTACK",
    "EFFECT_ADJUST_UNIT_COMBAT_CAPTURE",
    "EFFECT_ADJUST_UNIT_COMBAT_STRENGTH",
    "EFFECT_ADJUST_UNIT_COMBAT_UNIT_CAPTURE",
    "EFFECT_ADJUST_UNIT_CONVERTS_BARBARIANS",
    "EFFECT_ADJUST_UNIT_DAMAGE",
    "EFFECT_ADJUST_UNIT_DIPLO_VISIBILITY_COMBAT_MODIFIER",
    "EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK",
    "EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_PROMOTION_CLASS",
    "EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_WHOLE_GAME_PROMOTION_CLASS",
    "EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_WHOLE_GAME_SAME_RELIGION",
    "EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_WHOLE_GAME_SAME_RELIGION_PROMOTION_CLASS",
    "EFFECT_ADJUST_UNIT_ERA_STRENGTH_MODIFIER",
    "EFFECT_ADJUST_UNIT_EVICT_PERCENT",
    "EFFECT_ADJUST_UNIT_EXERT_ZOC",
    "EFFECT_ADJUST_UNIT_FIGHT_WHILE_EMBARKED",
    "EFFECT_ADJUST_UNIT_FLANKING_BONUS_MODIFIER",
    "EFFECT_ADJUST_UNIT_FORCE_RETREAT",
    "EFFECT_ADJUST_UNIT_FRIENDLY_TERRITORY_COMBAT",
    "EFFECT_ADJUST_UNIT_HOLY_CITIES_COMBAT_MODIFIER",
    "EFFECT_ADJUST_UNIT_IGNORE_CLIFF_WALLS",
    "EFFECT_ADJUST_UNIT_IGNORE_RANGED_VS_DISTRICT_PENALTY",
    "EFFECT_ADJUST_UNIT_IGNORE_RESOURCE_MAINTENANCE",
    "EFFECT_ADJUST_UNIT_IGNORE_STRATEGIC_RESOURCE_LEVIED",
    "EFFECT_ADJUST_UNIT_IGNORE_ZOC",
    "EFFECT_ADJUST_UNIT_MILITARY_FORMATION",
    "EFFECT_ADJUST_UNIT_MILITARY_POLICIES_COMBAT_MODIFIER",
    "EFFECT_ADJUST_UNIT_NEIGHBOR_COMBAT_MODIFIER",
    "EFFECT_ADJUST_UNIT_NO_REDUCTION_DAMAGE",
    "EFFECT_ADJUST_UNIT_NUM_ATTACKS",
    "EFFECT_ADJUST_UNIT_PER_LUXURY_ATTACK_MODIFIER",
    "EFFECT_ADJUST_UNIT_PER_UNUSED_MOVEMENT_COMBAT_BONUS",
    "EFFECT_ADJUST_UNIT_POST_COMBAT_YIELD",
    "EFFECT_ADJUST_UNIT_PROPERTY",
    "EFFECT_ADJUST_UNIT_RAIDING",
    "EFFECT_ADJUST_UNIT_RELIC_UPON_DEATH",
    "EFFECT_ADJUST_UNIT_STRENGTH_FROM_CITY_CULTURAL_IDENTITY",
    "EFFECT_ADJUST_UNIT_STRENGTH_REDUCTION_FOR_DAMAGE_MODIFIER",
    "EFFECT_ADJUST_UNIT_SUPPORT_BONUS_MODIFIER",
    "EFFECT_ADJUST_UNIT_WATER_DAMAGE_PROTECTION",
    "EFFECT_ADJUST_UNIT_WMD_PROTECTION",
    "EFFECT_ADJUST_UNITS_RELIGIOUS_STRENGTH_BY_RELIGION_TYPE",
    "EFFECT_GRANT_STRENGTH_PER_ADJACENT_UNIT_TYPE",
]
cats1 = OrderedDict()
for e in combat_list:
    if e in effects_data:
        cats1[e] = effects_data[e]
categories[u"## 战斗力/属性"] = cats1

# 2. 移动力
move_list = [
    "EFFECT_ADJUST_PLAYER_EMBARKED_UNIT_MOVEMENT",
    "EFFECT_ADJUST_PLAYER_EMBARK_UNIT_PASS",
    "EFFECT_ADJUST_UNIT_ATTACK_AND_MOVE",
    "EFFECT_ADJUST_UNIT_CLEAR_TERRAIN_START_MOVEMENT",
    "EFFECT_ADJUST_UNIT_ENTER_FOREIGN_LANDS",
    "EFFECT_ADJUST_UNIT_ENEMY_TERRITORY_START_MOVEMENT",
    "EFFECT_ADJUST_UNIT_ESCAPE_BOOST",
    "EFFECT_ADJUST_UNIT_ESCORT_MOBILITY",
    "EFFECT_ADJUST_UNIT_FRIENDLY_TERRITORY_START_MOVEMENT",
    "EFFECT_ADJUST_UNIT_IGNORE_RIVERS",
    "EFFECT_ADJUST_UNIT_IGNORE_SHORES",
    "EFFECT_ADJUST_UNIT_IGNORE_TERRAIN_COST",
    "EFFECT_ADJUST_UNIT_JUMP_ABILITY",
    "EFFECT_ADJUST_UNIT_MOVEMENT",
    "EFFECT_ADJUST_UNIT_MOVE_AND_ATTACK",
    "EFFECT_ADJUST_UNIT_PARADROP_ABILITY",
    "EFFECT_ADJUST_UNIT_PROMOTE_NO_FINISH_MOVES",
    "EFFECT_ADJUST_UNIT_SEA_MOVEMENT",
    "EFFECT_ADJUST_UNIT_TRADE_ROUTE_PLUNDER_IMMUNITY",
    "EFFECT_RESTORE_UNIT_MOVEMENT",
]
cats2 = OrderedDict()
for e in move_list:
    if e in effects_data:
        cats2[e] = effects_data[e]
categories[u"## 移动力"] = cats2

# 3. 经验/等级
xp_list = [
    "EFFECT_ADJUST_CITY_UNIT_MAX_LEVEL",
    "EFFECT_ADJUST_UNIT_ATTACK_EXPERIENCE_MODIFIER",
    "EFFECT_ADJUST_UNIT_EXPERIENCE_LEVEL",
    "EFFECT_ADJUST_UNIT_EXPERIENCE_MODIFIER",
    "EFFECT_ADJUST_UNIT_GRANT_EXPERIENCE",
    "EFFECT_ADJUST_UNIT_NO_BARB_XP_LIMIT",
    "EFFECT_ADJUST_UNIT_UPGRADE_GOODY_HUT",
]
cats3 = OrderedDict()
for e in xp_list:
    if e in effects_data:
        cats3[e] = effects_data[e]
categories[u"## 经验/等级"] = cats3

# 4. 回血/治疗
heal_list = [
    "EFFECT_ADJUST_RANDOM_EVENT_NO_UNIT_DAMAGE",
    "EFFECT_ADJUST_UNIT_HEAL",
    "EFFECT_ADJUST_UNIT_HEALING_MODIFIERS",
    "EFFECT_ADJUST_UNIT_HEALING_RELIGION_MODIFIERS",
    "EFFECT_ADJUST_UNIT_POST_COMBAT_HEAL",
]
cats4 = OrderedDict()
for e in heal_list:
    if e in effects_data:
        cats4[e] = effects_data[e]
categories[u"## 回血/治疗"] = cats4

# 5. 生产/购买
prod_list = [
    "EFFECT_ADJUST_ALL_UNITS_PURCHASE_COST",
    "EFFECT_ADJUST_ALL_UNIT_PRODUCTION_MODIFIER",
    "EFFECT_ADJUST_CITY_ALL_MILITARY_UNITS_PRODUCTION",
    "EFFECT_ADJUST_CITY_POPULATION_UNIT_CREATED",
    "EFFECT_ADJUST_CITY_PRODUCTION_UNIT",
    "EFFECT_ADJUST_PLAYER_BAN_UNIT_PRODUCTION_YIELD",
    "EFFECT_ADJUST_PLAYER_BLOCK_UNIT_ENTRY",
    "EFFECT_ADJUST_PLAYER_BUFF_UNIT_PRODUCTION_YIELD",
    "EFFECT_ADJUST_PLAYER_LEVIED_UNIT_UPGRADE_DISCOUNT_PERCENT",
    "EFFECT_ADJUST_PLAYER_UNIT_BUILD_DISABLED",
    "EFFECT_ADJUST_PLAYER_UNIT_DISTRICT_PERCENT",
    "EFFECT_ADJUST_PLAYER_UNIT_PROJECT_PERCENT",
    "EFFECT_ADJUST_PLAYER_UNIT_UPGRADE_DISCOUNT_PERCENT",
    "EFFECT_ADJUST_PLAYER_UNIT_UPGRADE_RESOURCE_COST_DISCOUNT",
    "EFFECT_ADJUST_PLAYER_UNIT_WONDER_PERCENT",
    "EFFECT_ADJUST_PLAYER_VALID_UNIT_BUILD",
    "EFFECT_ADJUST_UNIT_DOMAIN_PRODUCTION",
    "EFFECT_ADJUST_UNIT_MAINTENANCE_DISCOUNT",
    "EFFECT_ADJUST_UNIT_PRODUCTION",
    "EFFECT_ADJUST_UNIT_PURCHASE_COST",
    "EFFECT_ADJUST_UNIT_TAG_ERA_PRODUCTION",
    "EFFECT_ENABLE_UNIT_FAITH_PURCHASE",
    "EFFECT_GRANT_CITY_YIELD_PERCENT_UNIT_CREATED_COST",
    "EFFECT_GRANT_PLAYER_YIELD_PERCENT_UNIT_COST",
]
cats5 = OrderedDict()
for e in prod_list:
    if e in effects_data:
        cats5[e] = effects_data[e]
categories[u"## 生产/购买"] = cats5

# 6. 间谍
spy_list = [
    "EFFECT_ADJUST_UNIT_BOOST_ALL_SPIES",
    "EFFECT_ADJUST_UNIT_SPY_COUNTERSPY_ADJACENT_LEVEL_BOOST",
    "EFFECT_ADJUST_UNIT_SPY_COUNTERSPY_ENTIRE_CITY",
    "EFFECT_ADJUST_UNIT_SPY_ESTABLISH_TIME",
    "EFFECT_ADJUST_UNIT_SPY_OFFENSIVE_OPERATION_TIME",
    "EFFECT_ADJUST_UNIT_SPY_OPERATION_CHANCE",
    "EFFECT_ADJUST_UNIT_SPY_OPERATION_TIME",
]
cats6 = OrderedDict()
for e in spy_list:
    if e in effects_data:
        cats6[e] = effects_data[e]
categories[u"## 间谍"] = cats6

# 7. 宗教传播
rel_list = [
    "EFFECT_ADD_RELIGIOUS_UNIT",
    "EFFECT_ADJUST_UNIT_FOREIGN_SPREAD_MODIFIER",
    "EFFECT_ADJUST_UNIT_LAND_VICTORY_SPREAD",
    "EFFECT_ADJUST_UNIT_NO_FOREIGN_SPREAD",
    "EFFECT_ADJUST_UNIT_SPREAD_CHARGES",
]
cats7 = OrderedDict()
for e in rel_list:
    if e in effects_data:
        cats7[e] = effects_data[e]
categories[u"## 宗教传播"] = cats7

# 8. 掠夺/劫掠
pill_list = [
    "EFFECT_ADJUST_UNIT_FAITH_ON_DISTRICT_PLUNDER",
    "EFFECT_ADJUST_UNIT_FAITH_ON_IMPROVEMENT_PLUNDER",
    "EFFECT_ADJUST_UNIT_PILLAGE_DISTRICT_MODIFIER",
    "EFFECT_ADJUST_UNIT_PILLAGE_IMPROVEMENT_MODIFIER",
    "EFFECT_ADJUST_UNIT_PLUNDER_YIELDS",
]
cats8 = OrderedDict()
for e in pill_list:
    if e in effects_data:
        cats8[e] = effects_data[e]
categories[u"## 掠夺/劫掠"] = cats8

# 9. 旅游/摇滚乐队
tour_list = [
    "EFFECT_ADJUST_PLAYER_ROCK_BAND_UNIT_ALBUM_SALES",
    "EFFECT_ADJUST_UNIT_POST_TOURISM_BOMB_LOYALTY",
    "EFFECT_ADJUST_UNIT_ROCK_BAND_LEVEL_DISTRICT",
    "EFFECT_ADJUST_UNIT_ROCK_BAND_LEVEL_IMPROVEMENT",
    "EFFECT_ADJUST_UNIT_ROCK_BAND_LEVEL_NATIONAL_PARK",
    "EFFECT_ADJUST_UNIT_ROCK_BAND_LEVEL_NATURAL_WONDER",
    "EFFECT_ADJUST_UNIT_ROCK_BAND_TOURISM_BOMB_VALUE_PEACE",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_CONVERT_CITY",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_DISTRICT",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_IMPROVEMENT",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_NATIONAL_PARK",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_NATURAL_WONDER",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_RANGE",
    "EFFECT_ADJUST_UNIT_YIELD_PER_TOURISM_BOMB",
]
cats9 = OrderedDict()
for e in tour_list:
    if e in effects_data:
        cats9[e] = effects_data[e]
categories[u"## 旅游/摇滚乐队"] = cats9

# 10. 视野/可见性
vis_list = [
    "EFFECT_ADJUST_UNIT_HIDDEN_VISIBILITY",
    "EFFECT_ADJUST_UNIT_SEE_HIDDEN",
    "EFFECT_ADJUST_UNIT_SEE_THROUGH_FEATURES",
    "EFFECT_ADJUST_UNIT_SEE_THROUGH_TERRAIN",
    "EFFECT_ADJUST_UNIT_SIGHT",
]
cats10 = OrderedDict()
for e in vis_list:
    if e in effects_data:
        cats10[e] = effects_data[e]
categories[u"## 视野/可见性"] = cats10

# 11. 其他
other_list = [
    "EFFECT_ADJUST_NUM_UNITS_SUPPORTED",
    "EFFECT_ADJUST_PLAYER_DISTRICT_AND_BUILDINGS_CREATE_UNIT_WITH_ABILITY_BY_CLASS",
    "EFFECT_ADJUST_PLAYER_DISTRICT_CREATE_UNIT",
    "EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_NON_BARBARIAN_UNIT_KILLED_BY_GDR",
    "EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_NON_BARBARIAN_UNIT_SEA_KILLED",
    "EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_UNIT_PROMOTION_EARNED",
    "EFFECT_ADJUST_UNIT_BUILD_CHARGES",
    "EFFECT_ADJUST_UNIT_DISASTER_CHARGES",
    "EFFECT_ADJUST_UNIT_EXTRACT_SEA_ARTIFACTS",
    "EFFECT_ADJUST_UNIT_GREAT_PERSON_CHARGES",
    "EFFECT_ADJUST_UNIT_INITIATION_YIELD",
    "EFFECT_ADJUST_UNIT_INITIATION_YIELD_POPULATION",
    "EFFECT_ADJUST_UNIT_NATURAL_WONDER_DEFERRED_CHARGES",
    "EFFECT_ADJUST_UNIT_OWNER",
    "EFFECT_ADJUST_UNIT_VALID_TERRAIN",
    "EFFECT_CHANGE_UNIT_OPERATION_AVAILABILITY",
    "EFFECT_DISTRICT_ADD_NAVAL_UNIT",
    "EFFECT_GRANT_FREE_RESOURCE_FROM_UNIT_PLOT",
    "EFFECT_SETTLED_FOREIGN_CONTINENT_UNIT_CLASS",
]
cats11 = OrderedDict()
for e in other_list:
    if e in effects_data:
        cats11[e] = effects_data[e]
categories[u"## 其他"] = cats11

# Check for uncategorized effects
categorized = set()
for cat_dict in categories.values():
    categorized.update(cat_dict.keys())
uncategorized = set(effects_data.keys()) - categorized
if uncategorized:
    print("WARNING: Uncategorized effects:", sorted(uncategorized))
    # Add them to "其他"
    for e in sorted(uncategorized):
        cats11[e] = effects_data[e]
    categories[u"## 其他"] = cats11

# === Generate Markdown ===
lines = []
lines.append("# modifier-unit-combat — 单位战斗/属性/移动/经验/间谍/旅游/宗教等 EffectType")
lines.append("")
lines.append("> 共 {} 个 EffectType（来自 DynamicModifiers 表），按子类别分组。参数值来自 ModifierArguments 表中真实使用示例。".format(len(effects_data)))
lines.append("")

lines.append("## 目录")
lines.append("")
idx = 1
for cat_name in categories.keys():
    anchor = cat_name.replace(u"## ", "").replace(u"/", "").replace(u" ", "-")
    lines.append("{}. [{}](#{})".format(idx, cat_name.replace(u"## ", ""), anchor.lower()))
    idx += 1
lines.append("")
lines.append("---")
lines.append("")

for cat_name, cat_dict in categories.items():
    lines.append(cat_name)
    lines.append("")

    if not cat_dict:
        lines.append("*(暂无)*")
        lines.append("")
        continue

    for ename, info in cat_dict.items():
        # Brief description
        desc = ename.replace("EFFECT_", "").lower().replace("_", " ")

        lines.append("### " + ename)
        lines.append("")
        lines.append("" + desc + "。")
        lines.append("")

        lines.append("| ModifierType | CollectionType |")
        lines.append("|---|---|")
        for mt, ct in info["pairs"]:
            lines.append("| `" + mt + "` | `" + ct + "` |")
        lines.append("")

        if info["args"]:
            lines.append("| 参数 | 示例值 |")
            lines.append("|---|---|")
            for aname in sorted(info["args"].keys()):
                avals = sorted(info["args"][aname])
                if len(avals) <= 5:
                    vstr = "、".join("`" + v + "`" for v in avals)
                else:
                    vstr = "、".join("`" + v + "`" for v in avals[:5]) + " ... (共 {} 种值)".format(len(avals))
                lines.append("| `" + aname + "` | " + vstr + " |")
        else:
            lines.append("| *(无参数)* | |")
        lines.append("")
        lines.append("---")
        lines.append("")

out = "\n".join(lines)

# Append review section
review = [
    "",
    "## 待审核",
    "",
    "### ADJUST_UNIT_PROPERTY — 通用属性修改",
    "",
    "`EFFECT_ADJUST_UNIT_PROPERTY` 是最通用的单位属性修改 Effect，其行为完全由参数决定：",
    "",
    "- **`Amount`** — 数值修改量（可为负）",
    "- **`Key`** — 属性键名（`PropertyName`），决定修改哪个属性",
    "",
    "示例 Key 值（来自 MOD 数据）：`SIQI_GREYTHROAT_LEAD_PROPERTY`、`PROPERTY_SIQI_SHAMARE_UU_DECOMBAT`、`SIQI_KROOS_PLAYER_PROMOTION_UNIT_PROPERTY`、`PROPERTY_SIQI_TECNO_UU_COMBAT`、`SIQI_BOLIVAR_REBELS_PROPERTY` 等。",
    "",
    "原生游戏极少直接使用此 EffectType（多为 MOD 使用），其威力在于配合**自定义 PropertyKey 系统**实现任意属性的动态调整。",
    "",
    "### 相似效果对比",
    "",
    "| 相似组 | 差异说明 |",
    "|---|---|",
    "| `ADJUST_UNIT_MOVEMENT` vs `ADJUST_UNIT_SEA_MOVEMENT` | 前者通用移动力，后者仅海上移动力 |",
    "| `ADJUST_PLAYER_EMBARKED_UNIT_MOVEMENT` vs `ADJUST_UNIT_SEA_MOVEMENT` | 前者仅限搭载状态，后者永久海上移动力 |",
    "| `ADJUST_UNIT_ATTACK_AND_MOVE` vs `ADJUST_UNIT_MOVE_AND_ATTACK` | 前者攻击后可移动，后者移动后可攻击 |",
    "| `ADJUST_UNIT_HEAL` (一次性回血) vs `ADJUST_UNIT_HEALING_MODIFIERS` (每回合回血加成) | 前者瞬间回复指定 HP%，后者每回合回复 +Amount% |",
    "| `ADJUST_UNIT_EXPERIENCE_MODIFIER` vs `ADJUST_UNIT_GRANT_EXPERIENCE` | 前者按百分比加成经验获取，后者直接给予经验（-1 表示免费晋升） |",
    "| `ADJUST_UNIT_PRODUCTION` (指定 UnitType) vs `ADJUST_ALL_UNIT_PRODUCTION_MODIFIER` (全体) vs `ADJUST_CITY_ALL_MILITARY_UNITS_PRODUCTION` (仅军事) | 作用范围不同 |",
    "| `ADJUST_UNIT_PILLAGE_*` vs `ADJUST_UNIT_PLUNDER_YIELDS` | 掠夺行为的具体奖励方式不同 |",
    "| `EFFECT_ADJUST_UNIT_BYPASS_WALLS` vs `EFFECT_ADJUST_UNIT_BYPASS_WALLS_PROMOTION_CLASS` | 前者针对特定单位，后者针对整个晋升类别 |",
    "| `EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK` vs `EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_PROMOTION_CLASS` | 同上，范围不同 |",
    "| `EFFECT_ADJUST_UNIT_IGNORE_TERRAIN_COST` vs `EFFECT_ADJUST_UNIT_IGNORE_RIVERS` vs `EFFECT_ADJUST_UNIT_IGNORE_SHORES` | 忽略不同地形类型 |",
    "",
    "### 常见参数枚举值",
    "",
    "| 参数 | 常用枚举类型 | 示例值 |",
    "|---|---|---|",
    "| `UnitType` | Units | `UNIT_BUILDER`、`UNIT_SETTLER`、`UNIT_APOSTLE`、`UNIT_WARRIOR_MONK` |",
    "| `UnitDomain` | Domains | `DOMAIN_LAND`、`DOMAIN_SEA`、`DOMAIN_ALL` |",
    "| `UnitPromotionClass` | UnitPromotionClasses | `PROMOTION_CLASS_MELEE`、`PROMOTION_CLASS_ANTI_CAVALRY`、`PROMOTION_CLASS_HEAVY_CAVALRY`、`PROMOTION_CLASS_LIGHT_CAVALRY`、`PROMOTION_CLASS_RANGED` |",
    "| `MilitaryFormationType` | MilitaryFormations | `CORPS_MILITARY_FORMATION`、`ARMY_MILITARY_FORMATION` |",
    "| `EraType` | Eras | `ERA_ANCIENT`、`ERA_CLASSICAL`、`ERA_MEDIEVAL` |",
    "| `YieldType` | Yields | `YIELD_GOLD`、`YIELD_FAITH`、`YIELD_CULTURE`、`YIELD_SCIENCE` |",
    "| `DistrictType` | Districts | `DISTRICT_INDUSTRIAL_ZONE`、`DISTRICT_THEATER`、`DISTRICT_ENTERTAINMENT_COMPLEX` |",
    "| `TerrainType` | Terrains | `TERRAIN_OCEAN` |",
    "| `Type` (Healing) | — | `ALL`、`FRIENDLY`、`NEUTRAL`、`ENEMY` (治疗范围，区分地块归属) |",
    "| `OperationType` (Spy) | UnitOperations | `UNITOPERATION_SPY_GREAT_WORK_HEIST`、`UNITOPERATION_SPY_RECRUIT_PARTISANS`、`UNITOPERATION_SPY_DISRUPT_ROCKETRY` |",
    "",
    "### 命名注意",
    "",
    "- `ADJUST_UNIT_` 开头的为**单位级**修改（作用于特定单位），`ADJUST_PLAYER_` 为**玩家级**（作用于玩家所有符合条件的单位）",
    "- `_PROMOTION_CLASS` 后缀表示作用于整个**晋升类**而非单个单位",
    "- `_WHOLE_GAME` 后缀表示全局永久效果（通常是政策卡/市政效果）",
    "- 参数名并非强制，由 ModifierType 的 C++ 实现决定，需以数据库实际记录为准",
]

out += "\n".join(review)
MD_PATH = r"D:\文明6mod用文件夹\AI制作Mod\skills\07-techniques\modifiers\modifier-unit-combat.md"
with open(MD_PATH, "w", encoding="utf-8") as f:
    f.write(out)

print("Markdown written. Categories:")
for k, v in categories.items():
    print("  {}: {} effects".format(k, len(v)))
print("Total bytes:", len(out))
