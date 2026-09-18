import re

new_file = r"D:\文明6mod用文件夹\AI制作Mod\skills\07-techniques\modifiers\modifier-unit-combat-NEW.md"

with open(new_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Directly fix each (文本参考) by finding the nearest ### header and using the correct template
lines = content.split('\n')
current_et = None
fixed = 0

# Template rules - more exhaustive
def get_tpl(et, desc):
    d = desc.lower() if desc else ''
    e = et.upper()
    if "op" not in dir(): pass  # placeholder

    # Combat strength
    if "战斗力" in d:
        if "防空" in d: return "+{1_Amount}% 防空战斗力"
        if "蛮族" in d or "BARBARIAN" in e: return "+{1_Amount} [ICON_Strength] 对蛮族"
        if "外交" in d or "DIPLO" in e: return "+{1_Amount} [ICON_Strength] 外交能见度"
        if "圣城" in d or "HOLY" in e: return "+{1_Amount} [ICON_Strength] 每个圣城"
        if "奢侈品" in d or "LUXURY" in e: return "+{1_Amount} [ICON_Strength] 每个奢侈品"
        if "未使用" in d or "UNUSED" in e: return "+{1_Amount} [ICON_Strength] 每个未用移动力"
        if "相邻" in d or "ADJACENT" in e or "NEIGHBOR" in e: return "+{1_Amount} [ICON_Strength] 相邻加成"
        if "区域" in d or "AGAINST_DISTRICT" in e: return "+{1_Amount} [ICON_Strength] 对区域"
        if "受伤" in d: return "-{1_Amount}% 受伤战斗惩罚"
        if "时代" in d: return "跨时代战斗力修正"
        if "支援" in d: return "+{Percent}% 支援加成"
        if "侧翼" in d or "FLANKING" in e: return "+{Percent}% 夹击加成"
        if "友方" in d or "FRIENDLY" in e: return "+{1_Amount} [ICON_Strength] 友方领土"
        return "+{1_Amount} [ICON_Strength] 战斗力"

    # Movement
    if "移动力" in d or "MOVEMENT" in e:
        if "登船" in d or "EMBARK" in e: return "+{1_Amount} [ICON_Movement] 登船移动力"
        if "海洋" in d or "SEA" in e: return "+{1_Amount} [ICON_Movement] 海洋移动力"
        if "开阔" in d or "CLEAR" in e: return "+{1_Amount} [ICON_Movement] 开阔地形初始移动力"
        if "敌方" in d or "ENEMY" in e: return "+{1_Amount} [ICON_Movement] 敌方领土初始移动力"
        if "友方" in d or "FRIENDLY" in e: return "+{1_Amount} [ICON_Movement] 友方领土初始移动力"
        if "恢复" in d or "RESTORE" in e: return "恢复全部移动力"
        return "+{1_Amount} [ICON_Movement] 移动力"

    # Experience
    if "经验" in d or "EXPERIENCE" in e:
        if "攻击" in d and "经验" in d: return "+{1_Amount}% 攻击经验"
        return "+{1_Amount} 经验值"

    if "等级" in d: return "+{1_Amount} 等级"

    # Healing
    if "回复" in d or "治疗" in d or "HEAL" in e:
        if "战斗后" in d or "POST_COMBAT" in e: return "+{1_Amount} 击杀后回复"
        if "宗教" in d: return "+{1_Amount} 宗教领土回复"
        if "直接" in d: return "+{1_Amount} 立即回复"
        return "+{1_Amount} 每回合回复"

    if "伤害" in d or "DAMAGE" in e:
        if "环境" in d or "RANDOM" in e: return "免疫自然灾害"
        if "核" in d or "WMD" in e: return "免疫核武器伤害"
        if "水灾" in d: return "免疫水灾伤害"
        return "{1_Amount} 伤害"

    # Production
    if "生产力" in d or "PRODUCTION" in e:
        return "+{1_Amount}% [ICON_Production] 生产力"

    if "购买" in d or "PURCHASE" in e:
        if "信仰" in d or "FAITH" in e: return "可用信仰购买单位"
        return "+{1_Amount}% [ICON_Gold] 购买费用"

    if "费用" in d or "维护" in d or "MAINTENANCE" in e:
        return "-{1_Amount} [ICON_Gold] 维护费"

    if "升级费" in d:
        return "-{1_Amount}% 升级费用"

    # Sight/Visibility
    if "视野" in d or "SIGHT" in e: return "+{1_Amount} 视野范围"
    if "隐身" in d or "HIDDEN" in e: return "对敌方隐身"
    if "探测" in d or "SEE_HIDDEN" in e: return "可探测隐身单位"
    if "看穿" in d or "SEE_THROUGH" in e:
        if "地形" in d and "地貌" not in d: return "可看穿地形和地貌"
        return "可看穿障碍"

    # Spy
    if "间谍" in d or "SPY" in e:
        if "时间" in d or "TIME" in e: return "+{ReductionPercent}% 行动速度"
        if "成功" in d or "CHANCE" in e: return "+{1_Amount} 行动成功率"
        if "反间谍" in d or "COUNTERSPY" in e: return "+{1_Amount} 反间谍等级"
        if "等级" in d: return "+{1_Amount} 间谍等级"
        return "+{1_Amount} 间谍行动效率"

    # Religion
    if "宗教" in d or "传播" in d or "SPREAD" in e:
        if "压力" in d or "EVICT" in e: return "+{1_Amount}% 宗教压力"
        if "次数" in d or "CHARGES" in e: return "+{1_Amount} 传教次数"
        if "外国" in d or "FOREIGN" in e: return "+{1_Amount}% 外国传播强度"
        if "击杀" in d or "LAND_VICTORY" in e: return "击杀时传播宗教"
        if "禁止" in d or "NO_FOREIGN" in e: return "不可在外国传教"
        if "解锁" in d or "ADD_RELIGIOUS" in e: return "解锁宗教单位"
        if "首次" in d or "INITIATION" in e:
            if "人口" in d: return "+{1_Amount} [ICON_Science] 每人口产出"
            return "+{1_Amount} [ICON_Gold] 首次传教产出"
        if "自然奇观" in d or "NATURAL_WONDER" in e: return "自然奇观传教不消耗次数"
        return "+{1_Amount} 宗教传播强度"

    # Rock band / Tourism
    if "摇滚" in d or "旅游" in d or "TOURISM" in e:
        if "忠诚" in d or "LOYALTY" in e: return "+{1_Amount} 忠诚度下降"
        if "专辑" in d or "ALBUM" in e: return "+{1_Amount}% 专辑销售额"
        if "等级" in d or "LEVEL" in e: return "+{1_Amount} 摇滚乐队等级"
        if "和平" in d or "PEACE" in e: return "+{1_Amount}% 和平时期旅游爆发"
        if "转化" in d or "CONVERT" in e: return "演出后转化城市宗教"
        if "范围" in d or "RANGE" in e: return "+{Range} 旅游爆发范围"
        return "+{1_Amount} 旅游业绩"

    # Pillage/Plunder
    if "掠夺" in d or "劫掠" in d or "PILLAGE" in e or "PLUNDER" in e:
        if "区域" in d or "DISTRICT" in e: return "+{1_Amount}% 区域掠夺产出"
        if "改良" in d or "IMPROVEMENT" in e: return "+{1_Amount}% 改良设施掠夺产出"
        if "信仰" in d and "区域" in d: return "+{1_Amount} [ICON_Faith] 区域掠夺信仰"
        if "信仰" in d: return "+{1_Amount} [ICON_Faith] 改良掠夺信仰"
        return "+{1_Amount}% 掠夺产出"

    # Charges
    if "次数" in d or "CHARGES" in e:
        if "伟人" in d: return "+{1_Amount} 伟人使用次数"
        if "灾害" in d: return "+{1_Amount} 灾害应对次数"
        return "+{1_Amount} 使用次数"

    # Era score
    if "时代" in d or "ERA_SCORE" in e:
        if "击杀" in d: return "+{1_Amount} 时代分数/击杀"
        if "晋升" in d: return "+{1_Amount} 时代分数/晋升"
        return "+{1_Amount} 时代分数"

    # Specific abilities
    if "攻击范围" in d or "射程" in d: return "+{1_Amount} 攻击范围"
    if "攻击次数" in d or "NUM_ATTACKS" in e: return "+{1_Amount} 额外攻击次数"
    if "属性" in d or "PROPERTY" in e: return "单位属性修正"
    if "编队" in d or "FORMATION" in e: return "编入军团/军队"
    if "城墙" in d or "WALL" in e:
        if "绕过" in d or "BYPASS" in e: return "可绕过城墙"
        if "攻击" in d or "ENABLE" in e: return "可攻击城墙"
        return "城墙相关"
    if "控制区" in d or "ZOC" in e:
        if "忽略" in d: return "忽略控制区"
        if "移除" in d or "EXERT" in e: return "施加控制区"
        return "控制区修正"
    if "劫掠" in d or "RAID" in e or "COASTAL_RAID" in e:
        if "高级" in d: return "可高级劫掠"
        return "+{Bonus}% 劫掠产出"
    if "俘虏" in d or "CAPTURE" in e: return "可俘虏单位"
    if "转化" in d and "蛮族" in d: return "可转化蛮族"
    if "遗物" in d or "RELIC" in e: return "死亡时获得遗物"
    if "伞降" in d or "PARADROP" in e: return "可伞降"
    if "跳跃" in d or "JUMP" in e: return "+{Range} 跳跃距离"
    if "商人" in d or "TRADE_ROUTE" in e: return "商人免于被掠夺"
    if "河流" in d or "RIVERS" in e: return "忽略河流移动消耗"
    if "登船" in d or "SHORES" in e: return "忽略登船移动消耗"
    if "地形" in d and "忽略" in d: return "忽略地形移动消耗"
    if "悬崖" in d or "CLIFF" in e: return "可攀爬悬崖"
    if "禁止" in d and "攻击" in d: return "无法攻击"
    if "进入" in d and "外国" in d: return "可进入外国领土"
    if "移动" in d and "攻击" in d or "MOVE_AND_ATTACK" in e: return "移动后可攻击"
    if "攻击" in d and "移动" in d or "ATTACK_AND_MOVE" in e: return "攻击后可移动"
    if "晋升后" in d or "PROMOTE_NO_FINISH" in e: return "晋升后可继续移动"
    if "部落" in d or "GOODY_HUT" in e: return "可从部落村庄升级"
    if "所有权" in d or "OWNER" in e: return "转移单位所有权"
    if "地形" in d and "通行" in d: return "可通行指定地形"
    if "免费" in d or "GRANT_FREE" in e: return "+{1_Amount} 免费资源"
    if "建造" in d and "特殊" in d: return "可建造特殊单位"
    if "禁止建造" in d: return "禁止建造此单位"
    if "禁止" in d and "产出" in d: return "禁止产出购买单位"
    if "启用" in d and "产出" in d: return "允许产出购买单位"
    if "按消耗" in d or "PERCENT_UNIT_COST" in e: return "+{UnitCostPercent}% 返还金币"
    if "按生产" in d or "PERCENT_UNIT_CREATED" in e: return "+{UnitProductionPercent}% 生产力转产出"
    if "人口" in d: return "训练时消耗人口"
    if "海军" in d and "区域" in d: return "完成区域时获得海军单位"
    if "区域建造" in d and "生成" in d: return "完成区域时生成单位"
    if "兵种" in d or "SETTLED" in e: return "获赠近战单位"
    if "文物" in d or "ARTIFACT" in e: return "可提取海洋文物"
    if "行动操作" in d or "OPERATION" in e: return "禁用特定行动"
    if "外贸" in d: return "允许商人登船"
    if "护航" in d or "ESCORT" in e: return "可护卫其他单位"
    if "逃脱" in d or "ESCAPE" in e: return "+{1_Amount} 逃脱移动力"
    if "国际" in d: return "可进入外国领土"
    if "忽略" in d and "单位" in d: return "忽略敌方单位阻挡"
    if "忽略战略" in d: return "忽略战略资源维护"

    # Additional fallbacks
    if "区域" in d and "加速" in d: return "+{1_Amount}% 区域数单位生产力"
    if "项目" in d and "加速" in d: return "+{1_Amount}% 项目数单位生产力"
    if "奇观" in d and "加速" in d: return "+{1_Amount}% 奇观进度生产力"
    if "生成" in d and "携带" in d and "能力" in d: return "建造时生成特殊单位"

    # Fallbacks by EffectType name pattern
    if "BYPASS_COMBAT" in e: return "忽略敌方单位阻挡"
    if "BYPASS_WALLS_PROMOTION" in e: return "可绕过城墙"
    if "ENABLE_WALL_ATTACK_PROMOTION" in e: return "可攻击城墙"
    if "ENABLE_WALL_WHOLE_GAME_SAME_RELIGION" in e: return "同宗教可攻击城墙"
    if "ENABLE_WALL_SAME_RELIGION_PROMOTION" in e: return "同宗教指定兵种可攻击城墙"
    if "IGNORE_RANGED" in e: return "忽略远程区域惩罚"
    if "IGNORE_STRATEGIC_RESOURCE_LEVIED" in e: return "征召单位忽略战略资源"
    if "MILITARY_POLICIES" in e: return "+{1_Amount} [ICON_Strength] 每个军事政策"
    if "NO_REDUCTION_DAMAGE" in e: return "受伤无战斗力惩罚"
    if "STRENGTH_FROM_CITY_CULTURAL" in e: return "文化身份战斗力加成"
    if "STRENGTH_REDUCTION_FOR_DAMAGE" in e: return "-{50}% 受伤战斗力惩罚"
    if "WATER_DAMAGE" in e: return "免疫水灾伤害"
    if "BLOCK_UNIT_ENTRY" in e: return "阻止单位进入领土"
    if "BAN_UNIT_PRODUCTION" in e: return "禁止产出购买单位"
    if "BUFF_UNIT_PRODUCTION" in e: return "提升产出购买效率"
    if "BUILD_DISABLED" in e: return "禁止建造单位"
    if "EMBARK_UNIT_PASS" in e: return "允许商人登船通行"
    if "FIGHT_WHILE_EMBARKED" in e: return "登船时可战斗"
    if "FORCE_RETREAT" in e: return "强制击退敌方"
    if "MAX_LEVEL" in e: return "提升单位等级上限"
    if "NO_BARB_XP" in e: return "蛮族无经验上限"
    if "DISTRICT_ADD_NAVAL_UNIT" in e: return "完成区域获得海军单位"
    if "NUM_UNITS_SUPPORTED" in e: return "+{1_Amount} 可支持单位数"
    if "NOT_FOUND" in e: return "（文本参考）"

    return "（文本参考）"


effect_descs = {
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

output_lines = []
i = 0
while i < len(lines):
    line = lines[i]

    # Track current effect type
    m = re.match(r'^### (EFFECT_\w+|GRANT_\w+)', line)
    if m:
        current_et = m.group(1)

    # Check for (文本参考)
    if '（文本参考）' in line:
        if current_et:
            desc = effect_descs.get(current_et, '')
            template = get_tpl(current_et, desc)
            new_line = line.replace('（文本参考）', template)
            output_lines.append(new_line)
            if template != '（文本参考）':
                fixed += 1
                print(f"  Fixed: {current_et} -> {template}")
            else:
                print(f"  STILL BROKEN: {current_et}")
        else:
            output_lines.append(line)
    else:
        output_lines.append(line)

    i += 1

content_new = '\n'.join(output_lines)

# Clean up triple+ blank lines
content_new = re.sub(r'\n{3,}', '\n\n', content_new)

with open(new_file, 'w', encoding='utf-8') as f:
    f.write(content_new)

print(f"\nFixed {fixed} (文本参考) entries")
print(f"Updated: {new_file}")
