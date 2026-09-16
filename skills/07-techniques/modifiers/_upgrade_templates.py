import re

new_file = r"D:\文明6mod用文件夹\AI制作Mod\skills\07-techniques\modifiers\modifier-unit-combat-NEW.md"

with open(new_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Find each "> 需要 ModifierStrings（Preview/Summary）" and replace with template version
# We need to find the nearest ### header to determine which template to use

effect_descriptions = {
    "EFFECT_ADJUST_ADJACENT_LEVIED_UNIT_COMBAT_BONUS": "调整相邻征召单位的近战战斗力（绝对值加成）",
    "EFFECT_ADJUST_NUMBER_ALLIES_UNIT_COMBAT_BONUS": "根据相邻友军数量调整单位近战战斗力",
    "EFFECT_ADJUST_UNIT_AGAINST_DISTRICT_COMBAT_BONUS": "调整单位对区域攻击时的战斗力加成",
    "EFFECT_ADJUST_UNIT_ANTI_AIR_STRENGTH": "调整单位的防空战斗力",
    "EFFECT_ADJUST_UNIT_ATTACK_RANGE": "调整单位的攻击范围（射程）",
    "EFFECT_ADJUST_UNIT_ADVANCED_COASTAL_RAID": "赋予单位高级海岸劫掠能力",
    "EFFECT_ADJUST_UNIT_ADVANCED_PILLAGING": "赋予单位高级掠夺能力",
    "EFFECT_ADJUST_UNIT_BARBARIAN_COMBAT": "调整单位对蛮族的战斗力",
    "EFFECT_ADJUST_UNIT_BYPASS_COMBAT_UNIT": "允许单位绕过敌方战斗单位移动",
    "EFFECT_ADJUST_UNIT_BYPASS_WALLS": "允许近战单位绕过城墙直接攻击市中心",
    "EFFECT_ADJUST_UNIT_BYPASS_WALLS_PROMOTION_CLASS": "允许指定晋升类别的单位绕开城墙",
    "EFFECT_ADJUST_UNIT_CANNOT_ATTACK": "禁止单位发动攻击",
    "EFFECT_ADJUST_UNIT_COMBAT_CAPTURE": "调整单位在战斗中俘获敌方单位的能力",
    "EFFECT_ADJUST_UNIT_COMBAT_STRENGTH": "调整单位的近战战斗力（绝对值加成）",
    "EFFECT_ADJUST_UNIT_COMBAT_UNIT_CAPTURE": "允许俘虏特定类型的敌方单位",
    "EFFECT_ADJUST_UNIT_CONVERTS_BARBARIANS": "赋予单位转化蛮族为己方单位的能力",
    "EFFECT_ADJUST_UNIT_DAMAGE": "对单位造成直接伤害（正数=伤害，负数=治疗）",
    "EFFECT_ADJUST_UNIT_DIPLO_VISIBILITY_COMBAT_MODIFIER": "根据外交能见度差距提供战斗力加成",
    "EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK": "允许近战单位攻击城墙",
    "EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_PROMOTION_CLASS": "允许指定晋升类别的单位攻击城墙",
    "EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_WHOLE_GAME_PROMOTION_CLASS": "全局允许指定晋升类别的单位攻击城墙",
    "EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_WHOLE_GAME_SAME_RELIGION": "全局允许相同宗教文明的单位攻击城墙",
    "EFFECT_ADJUST_UNIT_ENABLE_WALL_ATTACK_WHOLE_GAME_SAME_RELIGION_PROMOTION_CLASS": "全局允许同宗教文明指定晋升类别的单位攻击城墙",
    "EFFECT_ADJUST_UNIT_ERA_STRENGTH_MODIFIER": "根据时代差异调整单位战斗力",
    "EFFECT_ADJUST_UNIT_EVICT_PERCENT": "调整宗教单位驱逐敌方宗教的压力百分比",
    "EFFECT_ADJUST_UNIT_EXERT_ZOC": "赋予/移除单位的控制区（ZOC）能力",
    "EFFECT_ADJUST_UNIT_FIGHT_WHILE_EMBARKED": "允许单位在登船状态下发动战斗",
    "EFFECT_ADJUST_UNIT_FLANKING_BONUS_MODIFIER": "调整单位的侧翼夹击加成倍率",
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
    "EFFECT_ADJUST_UNIT_NO_REDUCTION_DAMAGE": "移除单位受伤后的战斗力惩罚",
    "EFFECT_ADJUST_UNIT_NUM_ATTACKS": "调整单位每回合的攻击次数",
    "EFFECT_ADJUST_UNIT_PER_LUXURY_ATTACK_MODIFIER": "根据拥有奢侈品数量提供战斗力加成",
    "EFFECT_ADJUST_UNIT_PER_UNUSED_MOVEMENT_COMBAT_BONUS": "根据未使用移动力提供战斗力加成",
    "EFFECT_ADJUST_UNIT_POST_COMBAT_YIELD": "战斗胜利后获得指定产出",
    "EFFECT_ADJUST_UNIT_PROPERTY": "调整单位自定义属性值（Key参数决定具体属性）",
    "EFFECT_ADJUST_UNIT_RAIDING": "赋予单位海岸劫掠能力及劫掠产出加成",
    "EFFECT_ADJUST_UNIT_RELIC_UPON_DEATH": "宗教单位死亡时产生遗物",
    "EFFECT_ADJUST_UNIT_STRENGTH_FROM_CITY_CULTURAL_IDENTITY": "根据城市文化身份调整单位战斗力",
    "EFFECT_ADJUST_UNIT_STRENGTH_REDUCTION_FOR_DAMAGE_MODIFIER": "调整受伤单位的战斗力削减幅度",
    "EFFECT_ADJUST_UNIT_SUPPORT_BONUS_MODIFIER": "调整单位的支援加成倍率",
    "EFFECT_ADJUST_UNIT_WATER_DAMAGE_PROTECTION": "保护单位免受水灾伤害",
    "EFFECT_ADJUST_UNIT_WMD_PROTECTION": "保护单位免受核武器伤害及辐射影响",
    "EFFECT_ADJUST_UNITS_RELIGIOUS_STRENGTH_BY_RELIGION_TYPE": "根据宗教类型调整宗教单位的宗教战斗力",
    "EFFECT_GRANT_STRENGTH_PER_ADJACENT_UNIT_TYPE": "根据相邻指定单位类型数量提供战斗力加成",
    "EFFECT_ADJUST_PLAYER_EMBARKED_UNIT_MOVEMENT": "调整所有登船单位的移动力",
    "EFFECT_ADJUST_PLAYER_EMBARK_UNIT_PASS": "允许指定单位类型登船通行",
    "EFFECT_ADJUST_UNIT_ATTACK_AND_MOVE": "允许单位攻击后再移动",
    "EFFECT_ADJUST_UNIT_CLEAR_TERRAIN_START_MOVEMENT": "若回合开始时位于开阔地形，增加移动力",
    "EFFECT_ADJUST_UNIT_ENTER_FOREIGN_LANDS": "允许单位进入外国领土（无视封闭边界）",
    "EFFECT_ADJUST_UNIT_ENEMY_TERRITORY_START_MOVEMENT": "若回合开始时位于敌方领土，增加移动力",
    "EFFECT_ADJUST_UNIT_ESCAPE_BOOST": "增加间谍逃脱时的移动力",
    "EFFECT_ADJUST_UNIT_ESCORT_MOBILITY": "赋予单位护卫其他单位的机动能力",
    "EFFECT_ADJUST_UNIT_FRIENDLY_TERRITORY_START_MOVEMENT": "若回合开始时位于友方领土，增加移动力",
    "EFFECT_ADJUST_UNIT_IGNORE_RIVERS": "单位移动时忽略河流消耗",
    "EFFECT_ADJUST_UNIT_IGNORE_SHORES": "单位登船/下船时忽略移动力消耗",
    "EFFECT_ADJUST_UNIT_IGNORE_TERRAIN_COST": "单位移动时忽略地形/地貌的移动力消耗",
    "EFFECT_ADJUST_UNIT_JUMP_ABILITY": "赋予/调整单位的跳跃（空降/传送）距离",
    "EFFECT_ADJUST_UNIT_MOVEMENT": "调整单位的移动力（绝对值）",
    "EFFECT_ADJUST_UNIT_MOVE_AND_ATTACK": "控制单位是否能在移动后攻击",
    "EFFECT_ADJUST_UNIT_PARADROP_ABILITY": "赋予/移除单位的伞降能力",
    "EFFECT_ADJUST_UNIT_PROMOTE_NO_FINISH_MOVES": "单位晋升后不结束回合（仍可移动/攻击）",
    "EFFECT_ADJUST_UNIT_SEA_MOVEMENT": "调整单位的海洋移动力",
    "EFFECT_ADJUST_UNIT_TRADE_ROUTE_PLUNDER_IMMUNITY": "赋予贸易路线单位免于被掠夺的免疫能力",
    "EFFECT_RESTORE_UNIT_MOVEMENT": "恢复单位的全部移动力",
    "EFFECT_ADJUST_CITY_UNIT_MAX_LEVEL": "提升城市训练单位的最大等级上限",
    "EFFECT_ADJUST_UNIT_ATTACK_EXPERIENCE_MODIFIER": "调整单位攻击获得的经验倍率",
    "EFFECT_ADJUST_UNIT_EXPERIENCE_LEVEL": "直接提升单位的经验等级",
    "EFFECT_ADJUST_UNIT_EXPERIENCE_MODIFIER": "调整单位获取经验的倍率",
    "EFFECT_ADJUST_UNIT_GRANT_EXPERIENCE": "赠予单位指定数量的经验值",
    "EFFECT_ADJUST_UNIT_NO_BARB_XP_LIMIT": "移除单位从蛮族获得的经验上限",
    "EFFECT_ADJUST_UNIT_UPGRADE_GOODY_HUT": "允许单位从部落村庄中升级",
    "EFFECT_ADJUST_RANDOM_EVENT_NO_UNIT_DAMAGE": "保护单位免受指定随机环境事件的伤害",
    "EFFECT_ADJUST_UNIT_HEAL": "直接治疗单位指定血量",
    "EFFECT_ADJUST_UNIT_HEALING_MODIFIERS": "调整单位每回合的生命值回复量",
    "EFFECT_ADJUST_UNIT_HEALING_RELIGION_MODIFIERS": "调整宗教单位在特定宗教领土中的回复量",
    "EFFECT_ADJUST_UNIT_POST_COMBAT_HEAL": "单位战斗后回复指定血量",
    "EFFECT_ADJUST_ALL_UNITS_PURCHASE_COST": "调整所有单位的购买费用",
    "EFFECT_ADJUST_ALL_UNIT_PRODUCTION_MODIFIER": "调整所有单位的生产力产出倍率",
    "EFFECT_ADJUST_CITY_ALL_MILITARY_UNITS_PRODUCTION": "调整城市军事单位的生产力产出倍率",
    "EFFECT_ADJUST_CITY_POPULATION_UNIT_CREATED": "训练指定单位时消耗城市人口",
    "EFFECT_ADJUST_CITY_PRODUCTION_UNIT": "调整城市特定条件下的单位生产力基础产出",
    "EFFECT_ADJUST_PLAYER_BAN_UNIT_PRODUCTION_YIELD": "禁止使用特定产出类型生产单位",
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
    "EFFECT_ADJUST_UNIT_DOMAIN_PRODUCTION": "调整指定领域单位的生产力产出",
    "EFFECT_ADJUST_UNIT_MAINTENANCE_DISCOUNT": "降低单位的维护费用",
    "EFFECT_ADJUST_UNIT_PRODUCTION": "调整特定单位类型的生产力消耗倍率",
    "EFFECT_ADJUST_UNIT_PURCHASE_COST": "调整特定单位类型的购买费用",
    "EFFECT_ADJUST_UNIT_TAG_ERA_PRODUCTION": "调整指定时代/晋升类别单位的生产力消耗倍率",
    "EFFECT_ENABLE_UNIT_FAITH_PURCHASE": "允许使用信仰购买指定类别的单位",
    "EFFECT_GRANT_CITY_YIELD_PERCENT_UNIT_CREATED_COST": "训练单位时按生产力消耗百分比获得额外产出",
    "EFFECT_GRANT_PLAYER_YIELD_PERCENT_UNIT_COST": "训练单位时按消耗百分比返还指定产出",
    "EFFECT_ADJUST_UNIT_BOOST_ALL_SPIES": "提升所有间谍的有效等级",
    "EFFECT_ADJUST_UNIT_SPY_COUNTERSPY_ADJACENT_LEVEL_BOOST": "反间谍时提升相邻单元格友方间谍的等级",
    "EFFECT_ADJUST_UNIT_SPY_COUNTERSPY_ENTIRE_CITY": "反间谍时保护整个城市的所有区域",
    "EFFECT_ADJUST_UNIT_SPY_ESTABLISH_TIME": "减少间谍在目标城市建立据点的回合数",
    "EFFECT_ADJUST_UNIT_SPY_OFFENSIVE_OPERATION_TIME": "减少间谍进攻性行动所需回合数",
    "EFFECT_ADJUST_UNIT_SPY_OPERATION_CHANCE": "调整间谍行动的成功率",
    "EFFECT_ADJUST_UNIT_SPY_OPERATION_TIME": "减少特定间谍行动类型所需回合数",
    "EFFECT_ADD_RELIGIOUS_UNIT": "解锁可购买的宗教单位类型",
    "EFFECT_ADJUST_UNIT_FOREIGN_SPREAD_MODIFIER": "调整宗教单位在外国领土的传播强度",
    "EFFECT_ADJUST_UNIT_LAND_VICTORY_SPREAD": "陆地单位击杀敌方时自动传播己方宗教",
    "EFFECT_ADJUST_UNIT_NO_FOREIGN_SPREAD": "禁止宗教单位在外国领土传教",
    "EFFECT_ADJUST_UNIT_SPREAD_CHARGES": "调整宗教单位的传教次数",
    "EFFECT_ADJUST_UNIT_FAITH_ON_DISTRICT_PLUNDER": "掠夺区域时额外获得信仰",
    "EFFECT_ADJUST_UNIT_FAITH_ON_IMPROVEMENT_PLUNDER": "掠夺改良设施时额外获得信仰",
    "EFFECT_ADJUST_UNIT_PILLAGE_DISTRICT_MODIFIER": "调整掠夺区域获得的产出倍率",
    "EFFECT_ADJUST_UNIT_PILLAGE_IMPROVEMENT_MODIFIER": "调整掠夺改良设施获得的产出倍率",
    "EFFECT_ADJUST_UNIT_PLUNDER_YIELDS": "调整单位掠夺时获得的总产出倍率",
    "EFFECT_ADJUST_PLAYER_ROCK_BAND_UNIT_ALBUM_SALES": "调整摇滚乐队演出后的专辑销售旅游业绩",
    "EFFECT_ADJUST_UNIT_POST_TOURISM_BOMB_LOYALTY": "摇滚乐队演出后降低目标城市的忠诚度",
    "EFFECT_ADJUST_UNIT_ROCK_BAND_LEVEL_DISTRICT": "摇滚乐队在指定区域演出时获得额外等级",
    "EFFECT_ADJUST_UNIT_ROCK_BAND_LEVEL_IMPROVEMENT": "摇滚乐队在指定改良设施上演出时获得额外等级",
    "EFFECT_ADJUST_UNIT_ROCK_BAND_LEVEL_NATIONAL_PARK": "摇滚乐队在国家公园演出时获得额外等级",
    "EFFECT_ADJUST_UNIT_ROCK_BAND_LEVEL_NATURAL_WONDER": "摇滚乐队在自然奇观演出时获得额外等级",
    "EFFECT_ADJUST_UNIT_ROCK_BAND_TOURISM_BOMB_VALUE_PEACE": "调整和平时期摇滚乐队的旅游业绩爆发值",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_CONVERT_CITY": "摇滚乐队演出后转化目标城市的信仰宗教",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_DISTRICT": "摇滚乐队在指定区域演出时额外获得旅游业绩",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_IMPROVEMENT": "摇滚乐队在指定改良设施上演出时额外获得旅游业绩",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_NATIONAL_PARK": "摇滚乐队在国家公园演出时额外获得旅游业绩",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_NATURAL_WONDER": "摇滚乐队在自然奇观演出时额外获得旅游业绩",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_RANGE": "调整摇滚乐队旅游业绩爆发的有效范围",
    "EFFECT_ADJUST_UNIT_YIELD_PER_TOURISM_BOMB": "摇滚乐队旅游爆发时额外获得指定产出",
    "EFFECT_ADJUST_UNIT_HIDDEN_VISIBILITY": "赋予单位隐身能力（对敌方不可见）",
    "EFFECT_ADJUST_UNIT_SEE_HIDDEN": "赋予单位探测隐身单位的能力",
    "EFFECT_ADJUST_UNIT_SEE_THROUGH_FEATURES": "允许单位看穿地貌",
    "EFFECT_ADJUST_UNIT_SEE_THROUGH_TERRAIN": "允许单位看穿地形",
    "EFFECT_ADJUST_UNIT_SIGHT": "调整单位的视野范围",
    "EFFECT_ADJUST_NUM_UNITS_SUPPORTED": "调整可支持的单位数量（如考古学家）",
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
    "EFFECT_ADJUST_UNIT_VALID_TERRAIN": "设置单位可通行的地形类型",
    "EFFECT_CHANGE_UNIT_OPERATION_AVAILABILITY": "禁用/启用单位的特定行动操作",
    "EFFECT_DISTRICT_ADD_NAVAL_UNIT": "完成区域建造时获得一艘海军单位",
    "EFFECT_GRANT_FREE_RESOURCE_FROM_UNIT_PLOT": "赠予单位所在单元格的奢侈品资源",
    "EFFECT_SETTLED_FOREIGN_CONTINENT_UNIT_CLASS": "在其他大陆建立城市时赠送指定兵种类别的单位",
}

# Find all sections and their old notes
# Find old "需要 ModifierStrings（Preview/Summary）" notes and upgrade them
old_pattern = re.compile(r'> 需要 ModifierStrings（Preview/Summary）')

# For each match, find the preceding ### header to get the effect type
lines = content.split('\n')
current_et = None
output_lines = []

# Categorize by position: find each ### header, then when we hit an old note, replace it
i = 0
replacements = 0
while i < len(lines):
    line = lines[i]

    # Track current effect type
    if re.match(r'^### (EFFECT_\w+|GRANT_\w+)', line):
        current_et = line.replace('### ', '').strip()

    # Check for old format ModifierStrings
    if '需要 ModifierStrings（Preview/Summary）' in line:
        if current_et:
            desc = effect_descriptions.get(current_et, current_et)
            et = current_et
            template = None
            if "战斗力" in desc:
                template = "+{Amount} [ICON_Strength] 战斗力"
            elif "移动力" in desc or "MOVEMENT" in et:
                template = "+{Amount} [ICON_Movement] 移动力"
            elif "经验" in desc:
                template = "+{Amount} 经验值"
            elif "等级" in desc:
                template = "+{Amount} 等级"
            elif "回复" in desc or "治疗" in desc or "HEAL" in et:
                template = "+{Amount} 每回合回复"
            elif "伤害" in desc or "DAMAGE" in et:
                template = "{Amount} 伤害修正"
            elif "生产力" in desc or "PRODUCTION" in et:
                template = "+{Amount}% [ICON_Production] 生产力"
            elif "购买" in desc or "PURCHASE" in et:
                template = "+{Amount}% 购买费用"
            elif "费用" in desc or "维护" in desc:
                template = "-{Amount} [ICON_Gold] 维护费"
            elif "视野" in desc or "SIGHT" in et:
                template = "+{Amount} 视野范围"
            elif "间谍" in desc or "SPY" in et:
                template = "+{Amount} 间谍行动效率"
            elif "宗教" in desc or "传播" in desc:
                template = "+{Amount} 宗教传播强度"
            elif "摇滚" in desc or "旅游" in desc:
                template = "+{Amount} 旅游业绩"
            elif "掠夺" in desc or "劫掠" in desc:
                template = "+{Amount}% 掠夺产出"
            elif "次数" in desc or "CHARGES" in et:
                template = "+{Amount} 使用次数"
            elif "时代" in desc:
                template = "+{Amount} 时代分数"
            elif "编队" in desc or "FORMATION" in et:
                template = "编入军团/军队"
            elif "城墙" in desc or "WALL" in et:
                template = "可攻击城墙"
            elif "军" in desc or "夹击" in desc:
                template = "+{Amount} [ICON_Strength] 战斗力"
            elif "支援" in desc:
                template = "+{Percent}% 支援加成"
            elif "夹击" in desc:
                template = "+{Percent}% 夹击加成"
            elif "劫掠" in desc or "RAID" in et:
                template = "+{Amount} 劫掠加成"
            elif "遗物" in desc:
                template = "死亡时获得遗物"
            elif "俘" in desc:
                template = "可俘虏单位"
            elif "转化" in desc:
                template = "可转化蛮族"
            elif "ZOC" in desc or "控制区" in desc:
                template = "忽略控制区"
            elif "看穿" in desc:
                template = "可看穿障碍"
            elif "隐身" in desc:
                template = "对敌方隐身"
            elif "探测" in desc:
                template = "可探测隐身单位"
            elif "攻击范围" in desc or "射程" in desc:
                template = "+{Amount} 攻击范围"
            elif "禁止" in desc and "攻击" in desc:
                template = "无法攻击"
            elif "进入" in desc and "外国" in desc:
                template = "可进入外国领土"
            elif "河流" in desc:
                template = "忽略河流移动消耗"
            elif "移动" in desc and "攻击" in desc:
                template = "移动后可攻击"
            elif "升级" in desc:
                template = "+{Amount} 升级次数"
            elif "部落" in desc or "GOODY" in et:
                template = "可从部落村庄升级"
            elif "所有权" in desc or "OWNER" in et:
                template = "转移单位所有权"
            elif "地形" in desc and "通行" in desc:
                template = "可通行指定地形"
            elif "免费" in desc:
                template = "+{Amount} 免费资源"
            elif "建造" in desc and "单位" in desc:
                template = "可建造特殊单位"
            elif "特种" in desc:
                template = "可建造特殊单位"
            else:
                template = "（文本参考）"

            new_line = f"> 需要 ModifierStrings（Preview：`{template}`）"
            output_lines.append(new_line)
            replacements += 1
        else:
            output_lines.append(line)
    # Also check for "伟人被动使用" style notes or already-upgraded notes
    else:
        output_lines.append(line)

    i += 1

content_new = '\n'.join(output_lines)

# Clean up extra blank lines (max 1 consecutive blank line)
content_new = re.sub(r'\n{3,}', '\n\n', content_new)

with open(new_file, 'w', encoding='utf-8') as f:
    f.write(content_new)

print(f"Upgraded {replacements} old ModifierStrings notes")
print(f"File updated: {new_file}")
