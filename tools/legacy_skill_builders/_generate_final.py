import re

md_file = r"D:\文明6mod用文件夹\AI制作Mod\skills\07-techniques\modifiers\modifier-unit-combat.md"
output_file = r"D:\文明6mod用文件夹\AI制作Mod\skills\07-techniques\modifiers\modifier-unit-combat-NEW.md"

with open(md_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Effect descriptions
effect_descriptions = {
    # 战斗力/属性
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

    # 移动力
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

    # 经验/等级
    "EFFECT_ADJUST_CITY_UNIT_MAX_LEVEL": "提升城市训练单位的最大等级上限",
    "EFFECT_ADJUST_UNIT_ATTACK_EXPERIENCE_MODIFIER": "调整单位攻击获得的经验倍率",
    "EFFECT_ADJUST_UNIT_EXPERIENCE_LEVEL": "直接提升单位的经验等级",
    "EFFECT_ADJUST_UNIT_EXPERIENCE_MODIFIER": "调整单位获取经验的倍率",
    "EFFECT_ADJUST_UNIT_GRANT_EXPERIENCE": "赠予单位指定数量的经验值",
    "EFFECT_ADJUST_UNIT_NO_BARB_XP_LIMIT": "移除单位从蛮族获得的经验上限",
    "EFFECT_ADJUST_UNIT_UPGRADE_GOODY_HUT": "允许单位从部落村庄中升级",

    # 回血/治疗
    "EFFECT_ADJUST_RANDOM_EVENT_NO_UNIT_DAMAGE": "保护单位免受指定随机环境事件的伤害",
    "EFFECT_ADJUST_UNIT_HEAL": "直接治疗单位指定血量",
    "EFFECT_ADJUST_UNIT_HEALING_MODIFIERS": "调整单位每回合的生命值回复量",
    "EFFECT_ADJUST_UNIT_HEALING_RELIGION_MODIFIERS": "调整宗教单位在特定宗教领土中的回复量",
    "EFFECT_ADJUST_UNIT_POST_COMBAT_HEAL": "单位战斗后回复指定血量",

    # 生产/购买
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

    # 间谍
    "EFFECT_ADJUST_UNIT_BOOST_ALL_SPIES": "提升所有间谍的有效等级",
    "EFFECT_ADJUST_UNIT_SPY_COUNTERSPY_ADJACENT_LEVEL_BOOST": "反间谍时提升相邻单元格友方间谍的等级",
    "EFFECT_ADJUST_UNIT_SPY_COUNTERSPY_ENTIRE_CITY": "反间谍时保护整个城市的所有区域",
    "EFFECT_ADJUST_UNIT_SPY_ESTABLISH_TIME": "减少间谍在目标城市建立据点的回合数",
    "EFFECT_ADJUST_UNIT_SPY_OFFENSIVE_OPERATION_TIME": "减少间谍进攻性行动所需回合数",
    "EFFECT_ADJUST_UNIT_SPY_OPERATION_CHANCE": "调整间谍行动的成功率",
    "EFFECT_ADJUST_UNIT_SPY_OPERATION_TIME": "减少特定间谍行动类型所需回合数",

    # 宗教传播
    "EFFECT_ADD_RELIGIOUS_UNIT": "解锁可购买的宗教单位类型",
    "EFFECT_ADJUST_UNIT_FOREIGN_SPREAD_MODIFIER": "调整宗教单位在外国领土的传播强度",
    "EFFECT_ADJUST_UNIT_LAND_VICTORY_SPREAD": "陆地单位击杀敌方时自动传播己方宗教",
    "EFFECT_ADJUST_UNIT_NO_FOREIGN_SPREAD": "禁止宗教单位在外国领土传教",
    "EFFECT_ADJUST_UNIT_SPREAD_CHARGES": "调整宗教单位的传教次数",

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
    "EFFECT_ADJUST_UNIT_ROCK_BAND_TOURISM_BOMB_VALUE_PEACE": "调整和平时期摇滚乐队的旅游业绩爆发值",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_CONVERT_CITY": "摇滚乐队演出后转化目标城市的信仰宗教",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_DISTRICT": "摇滚乐队在指定区域演出时额外获得旅游业绩",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_IMPROVEMENT": "摇滚乐队在指定改良设施上演出时额外获得旅游业绩",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_NATIONAL_PARK": "摇滚乐队在国家公园演出时额外获得旅游业绩",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_NATURAL_WONDER": "摇滚乐队在自然奇观演出时额外获得旅游业绩",
    "EFFECT_ADJUST_UNIT_TOURISM_BOMB_RANGE": "调整摇滚乐队旅游业绩爆发的有效范围",
    "EFFECT_ADJUST_UNIT_YIELD_PER_TOURISM_BOMB": "摇滚乐队旅游爆发时额外获得指定产出",

    # 视野/可见性
    "EFFECT_ADJUST_UNIT_HIDDEN_VISIBILITY": "赋予单位隐身能力（对敌方不可见）",
    "EFFECT_ADJUST_UNIT_SEE_HIDDEN": "赋予单位探测隐身单位的能力",
    "EFFECT_ADJUST_UNIT_SEE_THROUGH_FEATURES": "允许单位看穿地貌",
    "EFFECT_ADJUST_UNIT_SEE_THROUGH_TERRAIN": "允许单位看穿地形",
    "EFFECT_ADJUST_UNIT_SIGHT": "调整单位的视野范围",

    # 其他
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

# Template for ModifierStrings based on category
def get_modstr_template(et, desc):
    """Returns ModifierStrings preview template or None if not needed"""
    desc_lower = desc
    et_upper = et

    if "战斗力" in desc_lower:
        return "+{1_Amount} [ICON_Strength] 战斗力"
    if "移动力" in desc_lower or "MOVEMENT" in et_upper:
        if "登船" in desc_lower or "海洋" in desc_lower or "SEA" in et_upper:
            return "+{1_Amount} [ICON_Movement] 海洋移动力"
        return "+{1_Amount} [ICON_Movement] 移动力"
    if "经验" in desc_lower or "EXPERIENCE" in et_upper:
        return "+{1_Amount} 经验值"
    if "等级" in desc_lower:
        return "+{1_Amount} 等级"
    if "回复" in desc_lower or "治疗" in desc_lower or "HEAL" in et_upper:
        return "+{1_Amount} 每回合回复"
    if "伤害" in desc_lower or "DAMAGE" in et_upper:
        return "{1_Amount} 伤害"
    if "生产力" in desc_lower or "PRODUCTION" in et_upper:
        return "+{1_Amount}% [ICON_Production] 生产力"
    if "购买" in desc_lower or "PURCHASE" in et_upper:
        return "+{1_Amount}% [ICON_Gold] 购买费用"
    if "费用" in desc_lower or "维护" in desc_lower or "MAINTENANCE" in et_upper or "DISCOUNT" in et_upper:
        return "-{1_Amount} [ICON_Gold] 维护费"
    if "视野" in desc_lower or "SIGHT" in et_upper:
        return "+{1_Amount} 视野范围"
    if "间谍" in desc_lower or "SPY" in et_upper:
        if "时间" in desc_lower or "TIME" in et_upper:
            return "+{ReductionPercent}% 行动速度"
        if "几率" in desc_lower or "CHANCE" in et_upper:
            return "+{1_Amount} 行动成功率"
        return "+{1_Amount} 间谍等级"
    if "宗教" in desc_lower or "传播" in desc_lower or "SPREAD" in et_upper:
        if "压力" in desc_lower:
            return "+{1_Amount}% 宗教压力"
        if "次数" in desc_lower or "CHARGES" in et_upper:
            return "+{1_Amount} 传教次数"
        return "+{1_Amount} 宗教传播强度"
    if "摇滚" in desc_lower or "旅游" in desc_lower or "TOURISM" in et_upper:
        return "+{1_Amount} 旅游业绩"
    if "掠夺" in desc_lower or "劫掠" in desc_lower or "PILLAGE" in et_upper or "PLUNDER" in et_upper:
        return "+{1_Amount}% 掠夺产出"
    if "次数" in desc_lower or "CHARGES" in et_upper:
        return "+{1_Amount} 使用次数"
    if "时代" in desc_lower or "ERA_SCORE" in et_upper:
        return "+{1_Amount} 时代分数"
    if "财产" in desc_lower or "PROPERTY" in et_upper:
        return "+{1_Amount} 单位属性"
    if "产出" in desc_lower or "YIELD" in et_upper:
        return "+{PercentDefeatedStrength}% 敌方战斗力 [ICON_Yield] 产出"
    if "战斗后" in desc_lower or "胜利" in desc_lower:
        return "+{PercentDefeatedStrength}% 击杀单位战斗力 [ICON_Yield] 产出"
    if "城墙" in desc_lower or "WALL" in et_upper:
        return "可攻击城墙"
    if "控制区" in desc_lower or "ZOC" in et_upper:
        return "忽略控制区"
    if "夹击" in desc_lower or "FLANKING" in et_upper:
        return "+{Percent}% 夹击加成"
    if "支援" in desc_lower or "SUPPORT" in et_upper:
        return "+{Percent}% 支援加成"
    if "劫掠" in desc_lower or "RAID" in et_upper:
        return "可海岸劫掠"
    if "俘虏" in desc_lower or "CAPTURE" in et_upper:
        return "可俘虏单位"
    if "转化" in desc_lower or "CONVERT" in et_upper:
        return "可转化蛮族"
    if "遗物" in desc_lower or "RELIC" in et_upper:
        return "死亡时获得遗物"
    if "编队" in desc_lower or "FORMATION" in et_upper:
        return "编入高级编队"
    if "属性" in desc_lower or "PROPERTY" in et_upper:
        return "单位属性修正"
    if "环境" in desc_lower or "RANDOM_EVENT" in et_upper:
        return "免疫自然灾害"
    if "伞降" in desc_lower or "PARADROP" in et_upper:
        return "可伞降"
    if "跳跃" in desc_lower or "JUMP" in et_upper:
        return "+{Range} 跃迁距离"
    if "国际贸易" in desc_lower or "TRADE_ROUTE" in et_upper:
        return "免除商人被掠夺"
    if "边界" in desc_lower or "FOREIGN" in et_upper:
        return "可进入外国领土"
    if "河流" in desc_lower or "RIVERS" in et_upper:
        return "忽略河流"
    if "海岸" in desc_lower or "SHORES" in et_upper:
        return "忽略登船消耗"
    if "地形" in desc_lower or "TERRAIN_COST" in et_upper:
        return "忽略地形移动消耗"
    if "开阔" in desc_lower or "CLEAR_TERRAIN" in et_upper:
        return "+{1_Amount} [ICON_Movement] 开阔地形移动力"
    if "敌方" in desc_lower or "ENEMY" in et_upper:
        return "+{1_Amount} [ICON_Movement] 敌方领土移动力"
    if "友方" in desc_lower or "FRIENDLY" in et_upper:
        return "+{1_Amount} [ICON_Movement] 友方领土移动力"
    if "外交" in desc_lower or "DIPLO" in et_upper:
        return "+{1_Amount} [ICON_Strength] 外交能见度战斗力"
    if "奢侈品" in desc_lower or "LUXURY" in et_upper:
        return "+{1_Amount} [ICON_Strength] 每个奢侈品"
    if "未使用" in desc_lower or "UNUSED" in et_upper:
        return "+{1_Amount} [ICON_Strength] 每个未用移动力"
    if "圣城" in desc_lower or "HOLY" in et_upper:
        return "+{1_Amount} [ICON_Strength] 每个圣城"
    if "蛮族" in desc_lower or "BARBARIAN" in et_upper:
        return "+{1_Amount} [ICON_Strength] 对蛮族"
    if "区域攻击" in desc_lower or "AGAINST_DISTRICT" in et_upper:
        return "+{1_Amount} [ICON_Strength] 对区域"
    if "相邻" in desc_lower or "ADJACENT" in et_upper or "NEIGHBOR" in et_upper:
        return "+{1_Amount} [ICON_Strength] 相邻加成"
    if "防空" in desc_lower or "ANTI_AIR" in et_upper:
        return "+{1_Amount}% 防空战斗力"
    if "攻击范围" in desc_lower or "RANGE" in et_upper:
        return "+{1_Amount} 攻击范围"
    if "攻击次数" in desc_lower or "NUM_ATTACKS" in et_upper:
        return "+{1_Amount} 额外攻击次数"
    if "隐身" in desc_lower or "HIDDEN" in et_upper:
        return "对敌方隐身"
    if "探测" in desc_lower or "SEE_HIDDEN" in et_upper:
        return "可探测隐身单位"
    if "看穿" in desc_lower or "SEE_THROUGH" in et_upper:
        return "可看穿障碍"
    if "所有权" in desc_lower or "OWNER" in et_upper:
        return "转移单位所有权"
    if "地形" in desc_lower and "VALID" in et_upper:
        return "可通行海洋"
    if "区域建造" in desc_lower or "DISTRICT_CREATE" in et_upper:
        return "完成区域时生成单位"
    if "海军" in desc_lower and "DISTRICT" in et_upper:
        return "完成区域时获得海军单位"
    if "兵种" in desc_lower or "SETTLED" in et_upper:
        return "获得近战单位"
    if "晋升后" in desc_lower or "PROMOTE_NO_FINISH" in et_upper:
        return "晋升后可继续移动"
    if "伟人" in desc_lower and "次数" in desc_lower:
        return "+{1_Amount} 伟人使用次数"
    if "外贸" in desc_lower:
        return "文明或领袖特性效果"
    if "文物" in desc_lower or "ARTIFACT" in et_upper:
        return "可提取海洋文物"
    if "灾害" in desc_lower and "次数" in desc_lower:
        return "应对灾害次数"
    if "人口" in desc_lower:
        return "消耗-1人口"
    if "阻止" in desc_lower or "BLOCK" in et_upper:
        return "阻止特定单位进入"
    if "禁止" in desc_lower and "建设" in desc_lower:
        return "禁止建造此单位"
    if "禁止" in desc_lower and "生产" in desc_lower:
        return "禁止用此产出购买单位"
    if "启用" in desc_lower and "产出" in desc_lower:
        return "允许用此产出购买单位"
    if "解锁" in desc_lower or "ENABLE_UNIT_FAITH" in et_upper:
        return "可用信仰购买单位"
    if "返还" in desc_lower:
        return "+{1_Amount}% 返还产出"
    if "按消耗" in desc_lower or "PERCENT_UNIT_COST" in et_upper:
        return "+{UnitCostPercent}% 返还金币"
    if "按生产" in desc_lower or "PERCENT_UNIT_CREATED" in et_upper:
        return "+{UnitProductionPercent}% 生产力转换为产出"
    if "资源" in desc_lower and "赠予" in desc_lower:
        return "+{1_Amount} 免费奢侈品"
    if "资源" in desc_lower and "忽略" in desc_lower:
        return "忽略战略资源"
    if "征召" in desc_lower and "忽略" in desc_lower:
        return "征召单位忽略战略资源"
    if "征召" in desc_lower and "升级" in desc_lower:
        return "-{1_Amount}% 征召单位升级费"
    if "核" in desc_lower or "WMD" in et_upper:
        return "免疫核武器伤害"
    if "水灾" in desc_lower:
        return "免疫水灾伤害"
    if "控制区" in desc_lower and "忽略" in desc_lower:
        return "忽略控制区"
    if "逃脱" in desc_lower or "ESCAPE" in et_upper:
        return "+{1_Amount} 逃脱移动力"
    if "护卫" in desc_lower or "ESCORT" in et_upper:
        return "护卫队机动性"
    if "恢复" in desc_lower and "移动" in desc_lower:
        return "恢复全部移动力"
    if "绕过" in desc_lower or "BYPASS_COMBAT" in et_upper:
        return "忽略敌方单位阻挡"
    if "禁止攻击" in desc_lower or "CANNOT_ATTACK" in et_upper:
        return "无法攻击"
    if "受伤" in desc_lower and "惩罚" in desc_lower:
        return "受伤无战斗力惩罚"
    if "受伤" in desc_lower and "削减" in desc_lower:
        return "受伤战斗力惩罚-{50}%"
    if "时代" in desc_lower and "差异" in desc_lower:
        return "跨时代战斗力修正"
    if "操" in desc_lower and "行动" in desc_lower:
        return "禁用特定行动"
    if "登船" in desc_lower and "战斗" in desc_lower:
        return "登船时可战斗"
    if "护卫" in desc_lower:
        return "可护卫其他单位"
    if "圣城" in desc_lower:
        return "+{1_Amount} [ICON_Strength]"
    if "区域" in desc_lower and "忽略" in desc_lower:
        return "忽略区域防御"
    if "悬崖" in desc_lower:
        return "可攀爬悬崖"
    if "移动后" in desc_lower and "攻击" in desc_lower:
        return "移动后可攻击"

    return "（文本参考）"


# Process the file: for each ### section, add effect description and ModifierStrings
output = content

# First pass: handle sections that already have "需要 ModifierStrings" to avoid duplication
# Second pass: insert effect descriptions

# Strategy: Use regex to find each section and insert the effect description + ModifierStrings note
# Pattern: ### EFFECT_XXX\n\n...\n> **溯源**：...\n

def process_section(match):
    full = match.group(0)
    header = match.group(1)  # e.g. ### EFFECT_ADJUST_UNIT_ATTACK_RANGE
    body = match.group(2)  # everything after the header until next section
    et = header.replace('### ', '').strip()

    desc = effect_descriptions.get(et)
    if not desc:
        return full  # shouldn't happen

    # Check if already has effect description
    if '**效果**：' in body:
        return full

    # Check if already has a ModifierStrings note
    already_has_modstr = '需要 ModifierStrings' in body or '无需单独写 ModifierStrings' in body

    # Generate ModifierStrings template
    template = get_modstr_template(et, desc)

    # Find the position of the last 溯源 line
    trace_pattern = re.finditer(r'^> \*\*溯源\*\*.*$', body, re.MULTILINE)
    trace_positions = list(trace_pattern)

    if trace_positions:
        # CASE 1: Has trace block - insert description before it, ModifierStrings after it
        last_trace = trace_positions[-1]
        last_trace_start = last_trace.start()

        # Add effect description before first trace
        first_trace = trace_positions[0]
        desc_pos = first_trace.start()

        if '**效果**：' not in body[:desc_pos]:
            desc_line = f"\n**效果**：{desc}"
            body = body[:desc_pos] + desc_line + '\n' + body[desc_pos:]

        # Re-find trace positions (shifted by desc insertion)
        trace_pattern2 = re.finditer(r'^> \*\*溯源\*\*.*$', body, re.MULTILINE)
        trace_positions2 = list(trace_pattern2)

        # Add ModifierStrings after last trace (if not already present)
        if not already_has_modstr and trace_positions2:
            last_trace2 = trace_positions2[-1]
            after_last = body[last_trace2.end():]
            lines_after = after_last.split('\n')
            end_pos = 0
            for li, l in enumerate(lines_after):
                if l.strip() == '' or l.startswith('> '):
                    end_pos = li + 1
                else:
                    break
            insert_at = last_trace2.end() + sum(len(l) + 1 for l in lines_after[:end_pos])
            modstr_note = f"\n> 需要 ModifierStrings（Preview：`{template}`）\n"
            body = body[:insert_at] + modstr_note + body[insert_at:]
    else:
        # CASE 2: No trace block - insert description after parameter table, before ---
        # Find the last table line (either 参数 table or 无参数)
        desc_line = f"\n**效果**：{desc}"

        # Find the `---` separator (at end of section body)
        sep_match = re.search(r'\n---\s*$', body, re.MULTILINE)
        if sep_match:
            if not already_has_modstr:
                modstr_note = f"\n> 需要 ModifierStrings（Preview：`{template}`）"
                body = body[:sep_match.start()] + desc_line + modstr_note + '\n' + body[sep_match.start():]
            else:
                body = body[:sep_match.start()] + desc_line + '\n' + body[sep_match.start():]
        else:
            body = body.strip() + desc_line + '\n'
            if not already_has_modstr:
                body += f"> 需要 ModifierStrings（Preview：`{template}`）\n"

    return f"{header}\n{body}"


# Find all ### sections and process them
# Pattern: ### EFFECT_xxx (or GRANT_xxx) followed by content until next ### or ## or end
section_pattern = re.compile(r'(### (?:EFFECT_\w+|GRANT_\w+)\s*\n)(.*?)(?=\n### |\n## |\Z)', re.DOTALL)
output = section_pattern.sub(process_section, content)

with open(output_file, 'w', encoding='utf-8') as f:
    f.write(output)

# Report stats
effect_count = len(re.findall(r'^### (EFFECT_\w+|GRANT_\w+)', output, re.MULTILINE))
desc_count = output.count('**效果**：')
modstr_count = output.count('需要 ModifierStrings（Preview：')
print(f"EffectTypes: {effect_count}")
print(f"Effect descriptions added: {desc_count}")
print(f"ModifierStrings templates added: {modstr_count}")
print(f"Output: {output_file}")
