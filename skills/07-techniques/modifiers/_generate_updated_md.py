import sqlite3
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

db = r"C:\Users\24948\AppData\Local\Firaxis Games\Sid Meier's Civilization VI\Cache\DebugGameplay.sqlite"
md_file = r"D:\文明6mod用文件夹\AI制作Mod\skills\07-techniques\modifiers\modifier-unit-combat.md"
output_file = r"D:\文明6mod用文件夹\AI制作Mod\skills\07-techniques\modifiers\modifier-unit-combat-NEW.md"

with open(md_file, 'r', encoding='utf-8') as f:
    content = f.read()

conn = sqlite3.connect(db)
cursor = conn.cursor()

# Build cache: for each EffectType, determine if GP_BIRTH, and get context
def get_effecttype_info(effect_type):
    """Returns (is_gp_birth, description, modifiers_strings_note)"""
    # Get ModifierTypes from DynamicModifiers
    cursor.execute("SELECT ModifierType FROM DynamicModifiers WHERE EffectType = ?", (effect_type,))
    dm_rows = cursor.fetchall()
    mtypes = [r[0] for r in dm_rows]

    # Check GP_BIRTH
    is_gp_birth = False
    for mt in mtypes:
        cursor.execute("""
            SELECT 1 FROM Modifiers m
            JOIN GreatPersonIndividualBirthModifiers gpb ON m.ModifierId = gpb.ModifierId
            WHERE m.ModifierType = ?
        """, (mt,))
        if cursor.fetchone():
            is_gp_birth = True
            break

    return is_gp_birth, mtypes

# Effect descriptions dictionary - derived from EffectType name semantics
# We'll generate these and use them in the output
effect_descriptions = {
    # 战斗力/属性
    "EFFECT_ADJUST_ADJACENT_LEVIED_UNIT_COMBAT_BONUS": "调整相邻征召单位的近战战斗力（绝对值加成）",
    "EFFECT_ADJUST_NUMBER_ALLIES_UNIT_COMBAT_BONUS": "根据相邻友军数量调整单位近战战斗力",
    "EFFECT_ADJUST_UNIT_AGAINST_DISTRICT_COMBAT_BONUS": "调整单位对区域攻击时的战斗力加成",
    "EFFECT_ADJUST_UNIT_ANTI_AIR_STRENGTH": "调整单位的防空战斗力（百分比）",
    "EFFECT_ADJUST_UNIT_ATTACK_RANGE": "调整单位的攻击范围（射程）",
    "EFFECT_ADJUST_UNIT_ADVANCED_COASTAL_RAID": "赋予单位高级海岸劫掠能力（可直接劫掠海岸区域）",
    "EFFECT_ADJUST_UNIT_ADVANCED_PILLAGING": "赋予单位高级掠夺能力（可掠夺更多类型）",
    "EFFECT_ADJUST_UNIT_BARBARIAN_COMBAT": "调整单位对蛮族的战斗力",
    "EFFECT_ADJUST_UNIT_BYPASS_COMBAT_UNIT": "允许单位绕过敌方战斗单位移动",
    "EFFECT_ADJUST_UNIT_BYPASS_WALLS": "允许近战单位绕过城墙直接攻击市中心",
    "EFFECT_ADJUST_UNIT_BYPASS_WALLS_PROMOTION_CLASS": "允许指定晋升类别的单位绕开城墙",
    "EFFECT_ADJUST_UNIT_CANNOT_ATTACK": "禁止单位发动攻击（设为不可攻击）",
    "EFFECT_ADJUST_UNIT_COMBAT_CAPTURE": "调整单位在战斗中俘获敌方单位的能力",
    "EFFECT_ADJUST_UNIT_COMBAT_STRENGTH": "调整单位的近战战斗力（绝对值加成）",
    "EFFECT_ADJUST_UNIT_COMBAT_UNIT_CAPTURE": "允许俘虏特定类型的战斗单位（如转化敌方单位）",
    "EFFECT_ADJUST_UNIT_CONVERTS_BARBARIANS": "赋予单位转化蛮族为己方单位的能力",
    "EFFECT_ADJUST_UNIT_DAMAGE": "对单位造成直接伤害（正数=伤害，负数=治疗）",
    "EFFECT_ADJUST_UNIT_DIPLO_VISIBILITY_COMBAT_MODIFIER": "根据外交能见度差距提供战斗力加成（每个等级差距+Amount）",
    "EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK": "允许近战单位攻击城墙",
    "EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_PROMOTION_CLASS": "允许指定晋升类别的单位攻击城墙",
    "EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_WHOLE_GAME_PROMOTION_CLASS": "全局允许指定晋升类别的单位攻击城墙（整局游戏生效）",
    "EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_WHOLE_GAME_SAME_RELIGION": "全局允许相同宗教文明的单位攻击城墙（整局游戏生效）",
    "EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_WHOLE_GAME_SAME_RELIGION_PROMOTION_CLASS": "全局允许同宗教文明指定晋升类别的单位攻击城墙",
    "EFFECT_ADJUST_UNIT_ERA_STRENGTH_MODIFIER": "根据时代差异调整单位战斗力",
    "EFFECT_ADJUST_UNIT_EVICT_PERCENT": "调整宗教单位驱逐敌方宗教的压力百分比",
    "EFFECT_ADJUST_UNIT_EXERT_ZOC": "赋予/移除单位的控制区（ZOC）能力",
    "EFFECT_ADJUST_UNIT_FIGHT_WHILE_EMBARKED": "允许单位在登船状态下发动战斗",
    "EFFECT_ADJUST_UNIT_FLANKING_BONUS_MODIFIER": "调整单位的侧翼夹击加成倍率（百分比）",
    "EFFECT_ADJUST_UNIT_FORCE_RETREAT": "赋予单位强制击退敌方单位的能力",
    "EFFECT_ADJUST_UNIT_FRIENDLY_TERRITORY_COMBAT": "调整单位在友方领土中的战斗力",
    "EFFECT_ADJUST_UNIT_HOLY_CITIES_COMBAT_MODIFIER": "根据圣城数量调整单位战斗力",
    "EFFECT_ADJUST_UNIT_IGNORE_CLIFF_WALLS": "允许单位忽略悬崖移动限制",
    "EFFECT_ADJUST_UNIT_IGNORE_RANGED_VS_DISTRICT_PENALTY": "忽略远程单位对区域攻击的减伤惩罚",
    "EFFECT_ADJUST_UNIT_IGNORE_RESOURCE_MAINTENANCE": "免除单位的战略资源维护需求",
    "EFFECT_ADJUST_UNIT_IGNORE_STRATEGIC_RESOURCE_LEVIED": "免除征召单位的战略资源维护需求",
    "EFFECT_ADJUST_UNIT_IGNORE_ZOC": "赋予单位忽略敌方控制区（ZOC）的能力",
    "EFFECT_ADJUST_UNIT_MILITARY_FORMATION": "将单位升级为军团/军队等编队形态",
    "EFFECT_ADJUST_UNIT_MILITARY_POLICIES_COMBAT_MODIFIER": "根据已启用军事政策槽位数量提供战斗力加成",
    "EFFECT_ADJUST_UNIT_NEIGHBOR_COMBAT_MODIFIER": "根据相邻己方单位数量调整战斗力",
    "EFFECT_ADJUST_UNIT_NO_REDUCTION_DAMAGE": "移除单位受伤后的战斗力惩罚（满血战斗到最后一刻）",
    "EFFECT_ADJUST_UNIT_NUM_ATTACKS": "调整单位每回合的攻击次数",
    "EFFECT_ADJUST_UNIT_PER_LUXURY_ATTACK_MODIFIER": "根据拥有奢侈品数量提供战斗力加成",
    "EFFECT_ADJUST_UNIT_PER_UNUSED_MOVEMENT_COMBAT_BONUS": "根据未使用移动力提供战斗力加成",
    "EFFECT_ADJUST_UNIT_POST_COMBAT_YIELD": "战斗胜利后获得指定产出（文化/金币/信仰/科技等）",
    "EFFECT_ADJUST_UNIT_PROPERTY": "调整单位自定义属性值（Key参数决定具体属性）",
    "EFFECT_ADJUST_UNIT_RAIDING": "赋予单位海岸劫掠能力及劫掠产出加成",
    "EFFECT_ADJUST_UNIT_RELIC_UPON_DEATH": "宗教单位死亡时产生遗物",
    "EFFECT_ADJUST_UNIT_STRENGTH_FROM_CITY_CULTURAL_IDENTITY": "根据城市文化身份调整单位战斗力",
    "EFFECT_ADJUST_UNIT_STRENGTH_REDUCTION_FOR_DAMAGE_MODIFIER": "调整受伤单位的战斗力削减幅度",
    "EFFECT_ADJUST_UNIT_SUPPORT_BONUS_MODIFIER": "调整单位的支援加成倍率",
    "EFFECT_ADJUST_UNIT_WATER_DAMAGE_PROTECTION": "保护单位免受水灾（洪水等）伤害",
    "EFFECT_ADJUST_UNIT_WMD_PROTECTION": "保护单位免受核武器伤害及辐射影响",
    "EFFECT_ADJUST_UNITS_RELIGIOUS_STRENGTH_BY_RELIGION_TYPE": "根据宗教类型调整宗教单位的宗教战斗力",
    "EFFECT_GRANT_STRENGTH_PER_ADJACENT_UNIT_TYPE": "根据相邻指定单位类型数量提供战斗力加成",

    # 移动力
    "EFFECT_ADJUST_PLAYER_EMBARKED_UNIT_MOVEMENT": "调整所有登船单位的移动力",
    "EFFECT_ADJUST_PLAYER_EMBARK_UNIT_PASS": "允许指定单位类型登船通行",
    "EFFECT_ADJUST_UNIT_ATTACK_AND_MOVE": "允许单位攻击后再移动",
    "EFFECT_ADJUST_UNIT_CLEAR_TERRAIN_START_MOVEMENT": "若回合开始时位于开阔地形，增加移动力",
    "EFFECT_ADJUST_UNIT_ENTER_FOREIGN_LANDS": "允许单位进入外国领土（无视边界）",
    "EFFECT_ADJUST_UNIT_ENEMY_TERRITORY_START_MOVEMENT": "若回合开始时位于敌方领土，增加移动力",
    "EFFECT_ADJUST_UNIT_ESCAPE_BOOST": "增加间谍逃脱时的移动力",
    "EFFECT_ADJUST_UNIT_ESCORT_MOBILITY": "赋予单位护卫其他单位的机动能力",
    "EFFECT_ADJUST_UNIT_FRIENDLY_TERRITORY_START_MOVEMENT": "若回合开始时位于友方领土，增加移动力",
    "EFFECT_ADJUST_UNIT_IGNORE_RIVERS": "单位移动时忽略河流消耗",
    "EFFECT_ADJUST_UNIT_IGNORE_SHORES": "单位登船/下船时忽略移动力消耗",
    "EFFECT_ADJUST_UNIT_IGNORE_TERRAIN_COST": "单位移动时忽略地貌移动力消耗",
    "EFFECT_ADJUST_UNIT_JUMP_ABILITY": "赋予/调整单位的跳跃（空降/传送）距离",
    "EFFECT_ADJUST_UNIT_MOVEMENT": "调整单位的移动力（绝对值）",
    "EFFECT_ADJUST_UNIT_MOVE_AND_ATTACK": "控制单位是否能在移动后攻击",
    "EFFECT_ADJUST_UNIT_PARADROP_ABILITY": "赋予/移除单位的伞降能力",
    "EFFECT_ADJUST_UNIT_PROMOTE_NO_FINISH_MOVES": "单位晋升后不结束回合（仍可移动）",
    "EFFECT_ADJUST_UNIT_SEA_MOVEMENT": "调整单位的海洋移动力",
    "EFFECT_ADJUST_UNIT_TRADE_ROUTE_PLUNDER_IMMUNITY": "赋予贸易路线单位免于被掠夺的免疫能力",
    "EFFECT_RESTORE_UNIT_MOVEMENT": "恢复单位的全部移动力和攻击力",

    # 经验/等级
    "EFFECT_ADJUST_CITY_UNIT_MAX_LEVEL": "提升城市训练单位的最大等级上限",
    "EFFECT_ADJUST_UNIT_ATTACK_EXPERIENCE_MODIFIER": "调整单位攻击获得的经验倍率",
    "EFFECT_ADJUST_UNIT_EXPERIENCE_LEVEL": "直接提升单位的经验等级",
    "EFFECT_ADJUST_UNIT_EXPERIENCE_MODIFIER": "调整单位获取经验的倍率（百分比）",
    "EFFECT_ADJUST_UNIT_GRANT_EXPERIENCE": "赠予单位指定数量的经验值",
    "EFFECT_ADJUST_UNIT_NO_BARB_XP_LIMIT": "移除单位从蛮族获得的经验上限",
    "EFFECT_ADJUST_UNIT_UPGRADE_GOODY_HUT": "允许单位从部落村庄中升级",

    # 回血/治疗
    "EFFECT_ADJUST_RANDOM_EVENT_NO_UNIT_DAMAGE": "保护单位免受指定随机环境事件的伤害",
    "EFFECT_ADJUST_UNIT_HEAL": "直接治疗单位指定血量",
    "EFFECT_ADJUST_UNIT_HEALING_MODIFIERS": "调整单位每回合的回复量（按领土类型区分）",
    "EFFECT_ADJUST_UNIT_HEALING_RELIGION_MODIFIERS": "调整宗教单位在特定宗教领土中的回复量",
    "EFFECT_ADJUST_UNIT_POST_COMBAT_HEAL": "单位战斗后回复指定血量",

    # 生产/购买
    "EFFECT_ADJUST_ALL_UNITS_PURCHASE_COST": "调整所有单位的购买费用（金币或信仰）",
    "EFFECT_ADJUST_ALL_UNIT_PRODUCTION_MODIFIER": "调整所有单位的生产力产出倍率",
    "EFFECT_ADJUST_CITY_ALL_MILITARY_UNITS_PRODUCTION": "调整城市军事单位的生产力产出倍率",
    "EFFECT_ADJUST_CITY_POPULATION_UNIT_CREATED": "训练指定单位时消耗城市人口",
    "EFFECT_ADJUST_CITY_PRODUCTION_UNIT": "调整城市特定兵种的生产力基础产出",
    "EFFECT_ADJUST_PLAYER_BAN_UNIT_PRODUCTION_YIELD": "禁止使用特定产出类型（如信仰）生产单位",
    "EFFECT_ADJUST_PLAYER_BLOCK_UNIT_ENTRY": "阻止指定单位类型进入己方领土",
    "EFFECT_ADJUST_PLAYER_BUFF_UNIT_PRODUCTION_YIELD": "调整使用特定产出类型生产单位时的效率",
    "EFFECT_ADJUST_PLAYER_LEVIED_UNIT_UPGRADE_DISCOUNT_PERCENT": "降低征召单位的升级费用百分比",
    "EFFECT_ADJUST_PLAYER_UNIT_BUILD_DISABLED": "禁止建造指定单位类型",
    "EFFECT_ADJUST_PLAYER_UNIT_DISTRICT_PERCENT": "根据已建区域数量加速单位建造",
    "EFFECT_ADJUST_PLAYER_UNIT_PROJECT_PERCENT": "根据已建项目数量加速单位建造",
    "EFFECT_ADJUST_PLAYER_UNIT_UPGRADE_DISCOUNT_PERCENT": "降低单位升级费用百分比",
    "EFFECT_ADJUST_PLAYER_UNIT_UPGRADE_RESOURCE_COST_DISCOUNT": "降低单位升级的战略资源费用",
    "EFFECT_ADJUST_PLAYER_UNIT_WONDER_PERCENT": "根据奇观建造进度加速单位建造",
    "EFFECT_ADJUST_PLAYER_VALID_UNIT_BUILD": "允许建造指定的特殊单位类型",
    "EFFECT_ADJUST_UNIT_DOMAIN_PRODUCTION": "调整指定领域（陆地/海洋）单位的生产力产出",
    "EFFECT_ADJUST_UNIT_MAINTENANCE_DISCOUNT": "降低单位的维护费用（金币减免）",
    "EFFECT_ADJUST_UNIT_PRODUCTION": "调整特定单位类型的生产力消耗倍率",
    "EFFECT_ADJUST_UNIT_PURCHASE_COST": "调整特定单位类型的购买费用",
    "EFFECT_ADJUST_UNIT_TAG_ERA_PRODUCTION": "调整指定时代/晋升类别的单位生产力消耗倍率",
    "EFFECT_ENABLE_UNIT_FAITH_PURCHASE": "允许使用信仰购买指定类别的单位",
    "EFFECT_GRANT_CITY_YIELD_PERCENT_UNIT_CREATED_COST": "训练单位时，按单位生产力消耗的百分比获得额外产出",
    "EFFECT_GRANT_PLAYER_YIELD_PERCENT_UNIT_COST": "训练单位时，按单位消耗的百分比返还指定产出",

    # 间谍
    "EFFECT_ADJUST_UNIT_BOOST_ALL_SPIES": "提升所有间谍的有效等级（攻击/防御）",
    "EFFECT_ADJUST_UNIT_SPY_COUNTERSPY_ADJACENT_LEVEL_BOOST": "反间谍时提升相邻单元格友方间谍的等级",
    "EFFECT_ADJUST_UNIT_SPY_COUNTERSPY_ENTIRE_CITY": "反间谍时保护整个城市的所有区域",
    "EFFECT_ADJUST_UNIT_SPY_ESTABLISH_TIME": "减少间谍在目标城市建立据点的回合数",
    "EFFECT_ADJUST_UNIT_SPY_OFFENSIVE_OPERATION_TIME": "减少间谍进攻性行动所需时间",
    "EFFECT_ADJUST_UNIT_SPY_OPERATION_CHANCE": "调整间谍行动的成功率（攻击/防御）",
    "EFFECT_ADJUST_UNIT_SPY_OPERATION_TIME": "减少特定间谍行动类型所需回合数",

    # 宗教传播
    "EFFECT_ADD_RELIGIOUS_UNIT": "解锁可购买的宗教单位类型",
    "EFFECT_ADJUST_UNIT_FOREIGN_SPREAD_MODIFIER": "调整宗教单位在外国领土的传播强度",
    "EFFECT_ADJUST_UNIT_LAND_VICTORY_SPREAD": "陆地单位击杀敌方单位时自动传播己方宗教",
    "EFFECT_ADJUST_UNIT_NO_FOREIGN_SPREAD": "禁止宗教单位在外国领土传教",
    "EFFECT_ADJUST_UNIT_SPREAD_CHARGES": "调整宗教单位的传教次数（充能）",

    # 掠夺/劫掠
    "EFFECT_ADJUST_UNIT_FAITH_ON_DISTRICT_PLUNDER": "掠夺区域时额外获得信仰",
    "EFFECT_ADJUST_UNIT_FAITH_ON_IMPROVEMENT_PLUNDER": "掠夺改良设施时额外获得信仰",
    "EFFECT_ADJUST_UNIT_PILLAGE_DISTRICT_MODIFIER": "调整掠夺区域获得的产出倍率",
    "EFFECT_ADJUST_UNIT_PILLAGE_IMPROVEMENT_MODIFIER": "调整掠夺改良设施获得的产出倍率",
    "EFFECT_ADJUST_UNIT_PLUNDER_YIELDS": "调整单位掠夺时获得的总产出倍率",

    # 旅游/摇滚乐队
    "EFFECT_ADJUST_PLAYER_ROCK_BAND_UNIT_ALBUM_SALES": "调整摇滚乐队演出后的专辑销售旅游业绩",
    "EFFECT_ADJUST_UNIT_POST_TOURISM_BOMB_LOYALTY": "摇滚乐队演出后降低目标城市的忠诚度",
    "EFFECT_ADJUST_UNIT_ROCK_BAND_LEVEL_DISTRICT": "摇滚乐队在指定区域演出时获得额外等级",
    "EFFECT_ADJUST_UNIT_ROCK_BAND_LEVEL_IMPROVEMENT": "摇滚乐队在指定改良设施上演出时获得额外等级",
    "EFFECT_ADJUST_UNIT_ROCK_BAND_LEVEL_NATIONAL_PARK": "摇滚乐队在国家公园演出时获得额外等级",
    "EFFECT_ADJUST_UNIT_ROCK_BAND_LEVEL_NATURAL_WONDER": "摇滚乐队在自然奇观演出时获得额外等级",
    "EFFECT_ADJUST_UNIT_ROCK_BAND_TOURISM_BOMB_VALUE_PEACE": "调整和平时期的摇滚乐队旅游业绩爆发值",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_CONVERT_CITY": "摇滚乐队演出后转化目标城市为信仰的宗教",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_DISTRICT": "摇滚乐队在指定区域演出时额外获得旅游业绩",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_IMPROVEMENT": "摇滚乐队在指定改良设施上演出时额外获得旅游业绩",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_NATIONAL_PARK": "摇滚乐队在国家公园演出时额外获得旅游业绩",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_NATURAL_WONDER": "摇滚乐队在自然奇观演出时额外获得旅游业绩",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_RANGE": "调整摇滚乐队旅游业绩爆发的有效范围",
    "EFFECT_ADJUST_UNIT_YIELD_PER_TOURISM_BOMB": "摇滚乐队旅游爆发时额外获得指定产出",

    # 视野/可见性
    "EFFECT_ADJUST_UNIT_HIDDEN_VISIBILITY": "赋予单位隐身能力（对敌方不可见）",
    "EFFECT_ADJUST_UNIT_SEE_HIDDEN": "赋予单位探测隐身单位的能力",
    "EFFECT_ADJUST_UNIT_SEE_THROUGH_FEATURES": "允许单位看穿地貌（森林/雨林/沼泽等）",
    "EFFECT_ADJUST_UNIT_SEE_THROUGH_TERRAIN": "允许单位看穿地形（丘陵等）",
    "EFFECT_ADJUST_UNIT_SIGHT": "调整单位的视野范围",

    # 其他
    "EFFECT_ADJUST_NUM_UNITS_SUPPORTED": "调整可支持的考古学家等单位数量",
    "EFFECT_ADJUST_PLAYER_DISTRICT_AND_BUILDINGS_CREATE_UNIT_WITH_ABILITY_BY_CLASS": "建造区域及建筑时生成携带指定能力的单位",
    "EFFECT_ADJUST_PLAYER_DISTRICT_CREATE_UNIT": "完成区域建造时生成指定单位",
    "EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_NON_BARBARIAN_UNIT_KILLED_BY_GDR": "GDR击杀非蛮族单位时获得时代分数",
    "EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_NON_BARBARIAN_UNIT_SEA_KILLED": "海军单位击杀非蛮族单位时获得时代分数",
    "EFFECT_ADJUST_PLAYER_ERA_SCORE_PER_UNIT_PROMOTION_EARNED": "单位晋升时获得时代分数",
    "EFFECT_ADJUST_UNIT_BUILD_CHARGES": "调整建造者/工兵的使用次数",
    "EFFECT_ADJUST_UNIT_DISASTER_CHARGES": "调整单位应对灾害的使用次数",
    "EFFECT_ADJUST_UNIT_EXTRACT_SEA_ARTIFACTS": "赋予单位提取海洋文物的能力",
    "EFFECT_ADJUST_UNIT_GREAT_PERSON_CHARGES": "调整伟人的使用次数",
    "EFFECT_ADJUST_UNIT_INITIATION_YIELD": "宗教单位首次传教时获得指定产出",
    "EFFECT_ADJUST_UNIT_INITIATION_YIELD_POPULATION": "宗教单位按目标城市人口传教时获得指定产出",
    "EFFECT_ADJUST_UNIT_NATURAL_WONDER_DEFERRED_CHARGES": "宗教单位在自然奇观旁传教不消耗次数",
    "EFFECT_ADJUST_UNIT_OWNER": "转移单位的所有权给当前玩家",
    "EFFECT_ADJUST_UNIT_VALID_TERRAIN": "设置单位可通行/不可通行的地形类型",
    "EFFECT_CHANGE_UNIT_OPERATION_AVAILABILITY": "禁用/启用单位的特定行动操作",
    "EFFECT_DISTRICT_ADD_NAVAL_UNIT": "完成区域建造时获得一艘海军单位",
    "EFFECT_GRANT_FREE_RESOURCE_FROM_UNIT_PLOT": "单位站立单元格赠予免费奢侈品资源",
    "EFFECT_SETTLED_FOREIGN_CONTINENT_UNIT_CLASS": "在其他大陆建立城市时赠送指定兵种类别的单位",
}

# ModifierStrings decision: For combat-related effects (STRENGTH/MOVEMENT/EXPERIENCE/HEALING etc.),
# check if used by GP_BIRTH. If not, provide template.

# Read the file and process section by section
lines = content.split('\n')
new_lines = []
i = 0

# Check which effects have GP_BIRTH
gp_birth_effects = set()
for et in effect_descriptions:
    cursor.execute("SELECT ModifierType FROM DynamicModifiers WHERE EffectType = ?", (et,))
    for dm in cursor.fetchall():
        mt = dm[0]
        cursor.execute("""
            SELECT 1 FROM Modifiers m
            JOIN GreatPersonIndividualBirthModifiers gpb ON m.ModifierId = gpb.ModifierId
            WHERE m.ModifierType = ?
        """, (mt,))
        if cursor.fetchone():
            gp_birth_effects.add(et)
            break

print(f"GP_BIRTH effects: {gp_birth_effects}")

# Now process each section in the markdown
while i < len(lines):
    line = lines[i]
    new_lines.append(line)

    # Check if this is an ### EFFECT_ or ### GRANT_ header
    match = re.match(r'^### (EFFECT_\w+|GRANT_\w+)', line)
    if match:
        et = match.group(1)
        desc = effect_descriptions.get(et, "（待补充效果描述）")

        # Find the 溯源 block for this effect (the first > **溯源** line after this header)
        trace_idx = None
        after_header_end = i + 1
        # Skip the blank line and tables
        j = i + 1
        while j < len(lines):
            if lines[j].startswith('> **溯源**'):
                trace_idx = j
                break
            j += 1

        # Also find the separator (---) before next header
        sep_idx = None
        j = i + 1
        while j < len(lines):
            if re.match(r'^### (EFFECT_\w+|GRANT_\w+)', lines[j]) or re.match(r'^## ', lines[j]):
                sep_idx = j - 2  # Approximate
                break
            j += 1
        if sep_idx is None:
            sep_idx = len(lines) - 1

        # Determine ModifierStrings
        is_birth = et in gp_birth_effects

        # Check the existing 溯源 to determine the source type
        trace_lines_after = []
        if trace_idx:
            k = trace_idx
            while k < len(lines) and lines[k].startswith('>'):
                trace_lines_after.append(lines[k])
                k += 1

        # For ModifierStrings, we need to know if this is a toggle/bool effect or an amount-based effect
        # Look at parameters to determine
        has_amount = False
        has_percent = False
        params_text = ""
        j = i + 1
        while j < sep_idx and j < len(lines):
            if '`Amount`' in lines[j] or '`Percent`' in lines[j]:
                if '`Amount`' in lines[j]:
                    has_amount = True
                    params_text = 'Amount'
                if '`Percent`' in lines[j]:
                    has_percent = True
                    params_text = 'Percent'
                break
            j += 1

        # Check if toggle-type (Enable/Disable/Bypass/CanAttack etc.)
        is_toggle = False
        for line_check in lines[i:sep_idx+1]:
            if any(t in line_check for t in ['`CanCapture`', '`Enable`', '`Disable`', '`Bypass`', '`Converts`',
                                              '`CanFight`', '`ForceRetreat`', '`Ignore`', '`CanMove`',
                                              '`CanAttack`', '`CanDrop`', '`NoFinishMoves`', '`Exert`',
                                              '`Enter`', '`Hidden`', '`SeeHidden`', '`CanSee`', '`NoReduction`',
                                              '`NoDamage`', '`Extract`', '`NewOwner`', '`Valid`', '`Convert`',
                                              '`NoSpread`', '`EntireCity`', '`NoLimit`', '`LandVictorySpread`',
                                              '`CanRaid`', '`EscortMobility`', '`UseAdvancedCoastalRaid`',
                                              '`UseAdvancedPillaging`']):
                is_toggle = True
                break

        # Build ModifierStrings note
        modstr_note = ""
        if is_birth:
            modstr_note = "伟人被动使用，文本由伟人 BirthModifier 负责，此效果无需单独写 ModifierStrings"
        else:
            # Determine preview template based on effect type
            if "ICON_Strength" in str(desc) or "战斗力" in str(desc):
                if has_amount or has_percent:
                    modstr_note = f"需要 ModifierStrings（Preview：`+{{{params_text}}} [ICON_Strength] 战斗力`）"
                else:
                    modstr_note = "需要 ModifierStrings（Preview）"
            elif "ICON_Movement" in str(desc) or "移动力" in str(desc):
                if has_amount or has_percent:
                    modstr_note = f"需要 ModifierStrings（Preview：`+{{{params_text}}} [ICON_Movement] 移动力`）"
                else:
                    modstr_note = "需要 ModifierStrings（Preview）"
            elif "经验" in str(desc):
                if has_amount or has_percent:
                    modstr_note = f"需要 ModifierStrings（Preview：`+{{{params_text}}} 经验`）"
                else:
                    modstr_note = "需要 ModifierStrings（Preview）"
            elif "回复" in str(desc) or "治疗" in str(desc) or "回血" in str(desc):
                if has_amount or has_percent:
                    modstr_note = f"需要 ModifierStrings（Preview：`+{{{params_text}}} 每回合回复`）"
                else:
                    modstr_note = "需要 ModifierStrings（Preview）"
            elif "生产力" in str(desc) or "生产" in str(desc) or "购买" in str(desc) or "费用" in str(desc):
                if has_amount or has_percent:
                    if "Percent" in params_text:
                        modstr_note = f"需要 ModifierStrings（Preview：`+{{{params_text}}}% [ICON_Production] 生产力`）"
                    else:
                        modstr_note = f"需要 ModifierStrings（Preview：`+{{{params_text}}} [ICON_Production] 生产力`）"
                else:
                    modstr_note = "需要 ModifierStrings（Preview）"
            elif "视野" in str(desc) or "可见" in str(desc) or "隐身" in str(desc):
                if has_amount:
                    modstr_note = f"需要 ModifierStrings（Preview：`+{{{params_text}}} 视野范围`）"
                else:
                    modstr_note = "需要 ModifierStrings（Preview）"
            elif "间谍" in str(desc) or "SPY" in et:
                modstr_note = "需要 ModifierStrings（Preview）"
            elif "宗教" in str(desc) or "传播" in str(desc) or "传教" in str(desc):
                modstr_note = "需要 ModifierStrings（Preview）"
            elif "摇滚乐队" in str(desc) or "旅游" in str(desc) or "TOURISM" in et:
                modstr_note = "需要 ModifierStrings（Preview）"
            elif "掠夺" in str(desc) or "劫掠" in str(desc):
                if has_amount:
                    modstr_note = f"需要 ModifierStrings（Preview：`+{{{params_text}}}% 掠夺产出`）"
                else:
                    modstr_note = "需要 ModifierStrings（Preview）"
            elif "消耗" in str(desc) or "次数" in str(desc):
                if has_amount:
                    modstr_note = f"需要 ModifierStrings（Preview：`+{{{params_text}}} 使用次数`）"
                else:
                    modstr_note = "需要 ModifierStrings（Preview）"
            else:
                modstr_note = "需要 ModifierStrings（Preview）"

        # Insert effect description before 溯源 block
        if i + 2 < len(new_lines):
            # Find trace block start
            j = i
            while j < len(lines):
                if lines[j].startswith('> **溯源**'):
                    break
                if re.match(r'^### (EFFECT_\w+|GRANT_\w+)', j > i and lines[j] or '') or re.match(r'^## ', lines[j]):
                    # No trace found before next section
                    j = -1
                    break
                j += 1

            if j > 0 and j < len(lines):
                trace_text = lines[j]
                # We need to insert the effect description before this line BUT after the previous content.
                # The structure is:
                # > **溯源**：...
                # We add a bold effect description line right above the > **溯源** line

                # Actually, let me insert it in a clean way - add it as the last non-blank line before trace
                # First, find where to put it:
                # It should go right after the "参数" table and the blank line before "> **溯源**"

                # The trace line is at index j in the original `lines`
                # We need to output it at the right position in `new_lines`
                # Since we're iterating forward, we'll track the insertion.
                # Let me instead just handle this inline.

                pass  # handled via direct tracking below

    i += 1

conn.close()

# Since the inline approach is complex, let me use a different strategy:
# I'll parse the file by EffectType sections and rewrite them.
print("\nGenerating updated markdown using section parser...")

conn2 = sqlite3.connect(db)
cursor2 = conn2.cursor()

with open(md_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Split by ### headers
parts = re.split(r'(?=^### )', content, flags=re.MULTILINE)

output_parts = []
for part in parts:
    match = re.match(r'^### (EFFECT_\w+|GRANT_\w+)', part)
    if not match:
        output_parts.append(part.rstrip())
        continue

    et = match.group(1)
    desc = effect_descriptions.get(et, "（待补充效果描述）")

    # Find the trace block in this part
    trace_match = re.search(r'^> \*\*溯源\*\*', part, re.MULTILINE)

    # Determine GP_BIRTH
    cursor2.execute("SELECT ModifierType FROM DynamicModifiers WHERE EffectType = ?", (et,))
    is_birth = False
    for dm in cursor2.fetchall():
        mt = dm[0]
        cursor2.execute("""
            SELECT 1 FROM Modifiers m
            JOIN GreatPersonIndividualBirthModifiers gpb ON m.ModifierId = gpb.ModifierId
            WHERE m.ModifierType = ?
        """, (mt,))
        if cursor2.fetchone():
            is_birth = True
            break

    # Determine parameters for ModifierStrings template
    has_amount = '`Amount`' in part
    has_percent = '`Percent`' in part
    param_name = 'Amount' if has_amount else ('Percent' if has_percent else 'Amount')

    # Build ModifierStrings note
    if is_birth:
        modstr_note = "> 伟人被动使用，文本由伟人 BirthModifier 负责，此效果无需单独写 ModifierStrings"
    else:
        modstr_note = None  # We'll use category-based templates below

    # Build the new section
    # Insert effect desc right before the trace block
    if trace_match:
        # Insert bold effect description before trace
        desc_line = f"\n**效果**：{desc}\n"
        new_part = part[:trace_match.start()] + desc_line + part[trace_match.start():]

        # Now add ModifierStrings after the trace block
        # Find end of 溯源 block (last line starting with >)
        trace_start = trace_match.start() + len(desc_line)
        lines_after_trace = new_part[trace_start:].split('\n')

        # Find where trace block ends
        trace_end_in_lines = 0
        for li, l in enumerate(lines_after_trace):
            if l.startswith('> ') or l.startswith('>**'):
                trace_end_in_lines = li + 1
            else:
                break

        # If there's already a "需要 ModifierStrings" note, don't add again
        rest_line_start = trace_start + sum(len(l)+1 for l in lines_after_trace[:trace_end_in_lines])
        rest = new_part[rest_line_start:]

        if '需要 ModifierStrings' not in rest and '无需单独写 ModifierStrings' not in rest and not is_birth:
            # Generate ModifierStrings template
            desc_lower = desc
            if "战斗力" in desc_lower or "STRENGTH" in et:
                template = f"+{{{param_name}}} [ICON_Strength] 战斗力"
            elif "移动力" in desc_lower or "MOVEMENT" in et:
                template = f"+{{{param_name}}} [ICON_Movement] 移动力"
            elif "经验" in desc_lower or "EXPERIENCE" in et or "等级" in desc_lower:
                template = f"+{{{param_name}}} 经验值"
            elif "回复" in desc_lower or "治疗" in desc_lower or "回血" in desc_lower or "HEAL" in et:
                template = f"+{{{param_name}}} 每回合回复"
            elif "生产力" in desc_lower or "生产" in desc_lower or "PRODUCTION" in et:
                template = f"+{{{param_name}}}% [ICON_Production] 生产力"
            elif "购买" in desc_lower or "费用" in desc_lower or "PURCHASE" in et:
                template = f"{param_name} 购买费用修正"
            elif "视野" in desc_lower or "SIGHT" in et:
                template = f"+{{{param_name}}} 视野范围"
            elif "间谍" in desc_lower or "SPY" in et:
                template = f"+{{{param_name}}} 间谍行动效率"
            elif "宗教" in desc_lower or "传播" in desc_lower or "SPREAD" in et:
                template = f"+{{{param_name}}} 宗教传播强度"
            elif "摇滚" in desc_lower or "旅游" in desc_lower or "TOURISM" in et:
                template = f"+{{{param_name}}} 旅游业绩"
            elif "掠夺" in desc_lower or "劫掠" in desc_lower or "PILLAGE" in et:
                template = f"+{{{param_name}}}% 掠夺产出"
            elif "次数" in desc_lower or "CHARGES" in et:
                template = f"+{{{param_name}}} 使用次数"
            elif "维护" in desc_lower or "MAINTENANCE" in et:
                template = f"{param_name} [ICON_Gold] 维护费减免"
            elif "伤害" in desc_lower or "DAMAGE" in et:
                template = f"{param_name} 伤害"
            elif "时代" in desc_lower or "ERA" in et:
                template = f"+{{{param_name}}} 时代分数"
            elif "财产" in desc_lower or "PROPERTY" in et:
                template = f"{param_name} 单位属性修正"
            else:
                template = f"{param_name} 修正"

            modstr_text = f"\n> 需要 ModifierStrings（Preview：`{template}`）\n"

            # Insert after the trace block
            insert_pos = trace_start + sum(len(l)+1 for l in lines_after_trace[:trace_end_in_lines])
            new_part = new_part[:insert_pos] + modstr_text + new_part[insert_pos:]

        output_parts.append(new_part.rstrip())
    else:
        # No trace block - just add desc at top
        desc_line = f"\n**效果**：{desc}\n"
        # Insert after the parameters table (before ---)
        sep_match = re.search(r'\n---\n', part)
        if sep_match:
            new_part = part[:sep_match.start()] + desc_line + part[sep_match.start():]
        else:
            new_part = part.strip() + '\n' + desc_line

        output_parts.append(new_part.rstrip())

conn2.close()

with open(output_file, 'w', encoding='utf-8') as f:
    f.write('\n\n'.join(output_parts))

print(f"Output written to {output_file}")
print(f"Sections: {len([p for p in parts if re.match(r'^### (EFFECT_|GRANT_)', p)])}")
