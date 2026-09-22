import sqlite3

db_path = "C:/Users/24948/AppData/Local/Firaxis Games/Sid Meier's Civilization VI/Cache/DebugGameplay.sqlite"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Effects where we STILL need to find (ModifierType, CollectionType)
effects_need_dm = [
    "EFFECT_ADJUST_BANNED_DIPLOMATIC_ACTIONS",
    "EFFECT_ADJUST_BANNED_DIPLOMATIC_ACTIONS_SPECIFIC_CIVILIZATION",
    "EFFECT_ADJUST_PLAYER_ANYONE_PLUNDER_FAVOR",
    "EFFECT_ADJUST_PLAYER_GOVERNOR_FAVOR",
    "EFFECT_ADJUST_PLAYER_GRIEVANCE_GENERATION",
    "EFFECT_ADJUST_PLAYER_POLICY_FAVOR",
    "EFFECT_ADJUST_PLAYER_SEND_INFLUENCE_TOKEN_FAVOR_BY_BONUS_TYPE",
    "EFFECT_ADJUST_PLAYER_SUZERAIN_FAVOR_BY_BONUS_TYPE",
    "EFFECT_ADJUST_PLAYER_TOURISM_FAVOR",
    "EFFECT_ADJUST_RELIGION_ANYONE_CONDEMNS_FAVOR",
    "EFFECT_DIPLOMACY_AGENDA_AYYUBID_DYNASTY",
    "EFFECT_DIPLOMACY_AGENDA_ENVIRONMENT",
    "EFFECT_DIPLOMACY_CULTURAL_ID",
    "EFFECT_DIPLOMACY_FORCE_INCURSION",
    "EFFECT_DIPLOMACY_SIMPLE_EFFECT",
    "EFFECT_ENABLE_RELIGION_AWARDS_ENVOY",
    "EFFECT_ENABLE_RELIGION_AWARDS_ENVOY_RELIGIOUS_PRESSURE",
    "EFFECT_GRANT_CITY_OWNER_INFLUENCE_TOKEN_WONDER",
    "EFFECT_GRANT_INFLUENCE_TOKEN_LEVY_MILITARY",
    "EFFECT_PLAYER_DIPLOMACY_AGENDA_COMPARE_ARMY_SIZE",
]

for effect in effects_need_dm:
    # Try to find ModifierId directly via Modifiers table where ModifierType = EFFECT_xxx
    cur.execute("""
        SELECT m.ModifierId, m.ModifierType, dm.CollectionType
        FROM Modifiers m
        LEFT JOIN DynamicModifiers dm ON m.ModifierType = dm.ModifierType
        WHERE m.ModifierType = ?
    """, (effect,))
    rows = cur.fetchall()

    if rows:
        print(f"\n=== {effect} (as ModifierType) ===")
        for mid, mt, ct in rows:
            cur.execute("SELECT Name, Value FROM ModifierArguments WHERE ModifierId = ? ORDER BY Name", (mid,))
            args = cur.fetchall()
            args_str = "; ".join(f"{n}={v}" for n, v in args)
            print(f"  CollectorId={mid} | MT={mt} | CT={ct} | Args: {args_str}")
    else:
        print(f"\n{effect}: NO MATCH (not in Modifiers as ModifierType)")

conn.close()
