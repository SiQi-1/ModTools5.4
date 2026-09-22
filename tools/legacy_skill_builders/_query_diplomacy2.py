import sqlite3

db_path = "C:/Users/24948/AppData/Local/Firaxis Games/Sid Meier's Civilization VI/Cache/DebugGameplay.sqlite"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

not_found = [
    "EFFECT_ADD_PLAYER_FAVOR",
    "EFFECT_ADJUST_BANNED_DIPLOMATIC_ACTIONS",
    "EFFECT_ADJUST_BANNED_DIPLOMATIC_ACTIONS_SPECIFIC_CIVILIZATION",
    "EFFECT_ADJUST_DISABLE_INFLUENCE",
    "EFFECT_ADJUST_PLAYER_ADJUST_ENVOYS_NON_SPECIALTY",
    "EFFECT_ADJUST_PLAYER_ANYONE_PLUNDER_FAVOR",
    "EFFECT_ADJUST_PLAYER_DIPLOMATIC_VICTORY_POINTS",
    "EFFECT_ADJUST_PLAYER_EMERGENCY_FAVOR_MODIFIER",
    "EFFECT_ADJUST_PLAYER_EXTRA_FAVOR_PER_TURN",
    "EFFECT_ADJUST_PLAYER_FAVOR_REFUND_FOR_SUCCESSFUL_RESOLUTION",
    "EFFECT_ADJUST_PLAYER_GOVERNMENT_SLOT_TYPE_GRANT_FAVOR",
    "EFFECT_ADJUST_PLAYER_GOVERNOR_FAVOR",
    "EFFECT_ADJUST_PLAYER_GREATPERSON_FAVOR_MODIFIER",
    "EFFECT_ADJUST_PLAYER_GRIEVANCE_DECAY",
    "EFFECT_ADJUST_PLAYER_GRIEVANCE_GENERATION",
    "EFFECT_ADJUST_PLAYER_OPEN_BORDERS_FROM_INFLUENCE",
    "EFFECT_ADJUST_PLAYER_POLICY_FAVOR",
    "EFFECT_ADJUST_PLAYER_SEND_INFLUENCE_TOKEN_FAVOR_BY_BONUS_TYPE",
    "EFFECT_ADJUST_PLAYER_SUZERAIN_FAVOR_BY_BONUS_TYPE",
    "EFFECT_ADJUST_PLAYER_SUZERAIN_FAVOR_MULTIPLIER",
    "EFFECT_ADJUST_PLAYER_TOURISM_FAVOR",
    "EFFECT_ADJUST_PLAYER_YIELD_CHANGE_PER_USED_INFLUENCE_TOKEN",
    "EFFECT_ADJUST_RELIGION_ANYONE_CONDEMNS_FAVOR",
    "EFFECT_DIPLOMACY_AGENDA_AYYUBID_DYNASTY",
    "EFFECT_DIPLOMACY_AGENDA_ENVIRONMENT",
    "EFFECT_DIPLOMACY_CULTURAL_ID",
    "EFFECT_DIPLOMACY_FORCE_INCURSION",
    "EFFECT_DIPLOMACY_SIMPLE_EFFECT",
    "EFFECT_DISABLE_PLAYER_GRIEVANCE_DECAY",
    "EFFECT_ENABLE_RELIGION_AWARDS_ENVOY",
    "EFFECT_ENABLE_RELIGION_AWARDS_ENVOY_RELIGIOUS_PRESSURE",
    "EFFECT_GRANT_CITY_OWNER_INFLUENCE_TOKEN_WONDER",
    "EFFECT_GRANT_INFLUENCE_TOKEN_LEVY_MILITARY",
    "EFFECT_PLAYER_DIPLOMACY_AGENDA_COMPARE_ARMY_SIZE",
]

for effect in not_found:
    short = effect.replace("EFFECT_", "").replace("ADJUST_", "").replace("PLAYER_", "")

    # 1. Search Modifiers where ModifierType contains part of effect name
    cur.execute(
        "SELECT DISTINCT m.ModifierType, m.ModifierId FROM Modifiers m WHERE m.ModifierType LIKE ? LIMIT 5",
        ("%" + short + "%",)
    )
    r1 = cur.fetchall()

    # 2. Check DynamicModifiers
    mod_type = effect.replace("EFFECT_", "MODIFIER_")
    cur.execute(
        "SELECT dm.ModifierType, dm.CollectionType FROM DynamicModifiers dm WHERE dm.ModifierType = ?",
        (mod_type,)
    )
    r3 = cur.fetchall()

    found = False
    if r1:
        print(f"{effect}: Modifiers -> {r1}")
        found = True
    if r3:
        print(f"{effect}: Direct DM -> {r3}")
        found = True
    if not found:
        cur.execute(
            "SELECT m.ModifierId, m.ModifierType FROM Modifiers m WHERE m.ModifierType = ? LIMIT 3",
            (effect,)
        )
        r5 = cur.fetchall()
        if r5:
            print(f"{effect}: As ModifierType -> {r5}")
            # Get arguments too
            mid = r5[0][0]
            cur.execute(
                "SELECT Name, Value, Type FROM ModifierArguments WHERE ModifierId = ?",
                (mid,)
            )
            args = cur.fetchall()
            for a in args:
                print(f"    Arg: {a}")
            found = True
    if not found:
        print(f"{effect}: TRULY NOT FOUND")

conn.close()
