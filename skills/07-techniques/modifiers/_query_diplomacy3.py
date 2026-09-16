import sqlite3

db_path = "C:/Users/24948/AppData/Local/Firaxis Games/Sid Meier's Civilization VI/Cache/DebugGameplay.sqlite"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

effects = [
    "EFFECT_ADD_PLAYER_FAVOR",
    "EFFECT_ADJUST_DISABLE_INFLUENCE",
    "EFFECT_ADJUST_PLAYER_ADJUST_ENVOYS_NON_SPECIALTY",
    "EFFECT_ADJUST_PLAYER_DIPLOMATIC_VICTORY_POINTS",
    "EFFECT_ADJUST_PLAYER_EMERGENCY_FAVOR_MODIFIER",
    "EFFECT_ADJUST_PLAYER_EXTRA_FAVOR_PER_TURN",
    "EFFECT_ADJUST_PLAYER_FAVOR_REFUND_FOR_SUCCESSFUL_RESOLUTION",
    "EFFECT_ADJUST_PLAYER_GOVERNMENT_SLOT_TYPE_GRANT_FAVOR",
    "EFFECT_ADJUST_PLAYER_GREATPERSON_FAVOR_MODIFIER",
    "EFFECT_ADJUST_PLAYER_GRIEVANCE_DECAY",
    "EFFECT_ADJUST_PLAYER_OPEN_BORDERS_FROM_INFLUENCE",
    "EFFECT_ADJUST_PLAYER_SUZERAIN_FAVOR_MULTIPLIER",
    "EFFECT_ADJUST_PLAYER_YIELD_CHANGE_PER_USED_INFLUENCE_TOKEN",
    "EFFECT_DISABLE_PLAYER_GRIEVANCE_DECAY",
]

for effect in effects:
    short = effect.replace("EFFECT_", "").replace("ADJUST_", "").replace("PLAYER_", "")
    cur.execute(
        "SELECT DISTINCT m.ModifierType, m.ModifierId FROM Modifiers m WHERE m.ModifierType LIKE ?",
        ("%" + short + "%",)
    )
    rows = cur.fetchall()

    seen_types = set()
    print(f"\n=== {effect} ===")
    for mt, mid in rows:
        if mt in seen_types:
            continue
        seen_types.add(mt)

        # Get CollectionType from DynamicModifiers
        cur.execute("SELECT CollectionType FROM DynamicModifiers WHERE ModifierType = ?", (mt,))
        ct_row = cur.fetchone()
        ct = ct_row[0] if ct_row else "UNKNOWN"

        # Get arguments
        cur.execute("SELECT Name, Value, Type FROM ModifierArguments WHERE ModifierId = ? ORDER BY Name", (mid,))
        args = cur.fetchall()
        args_str = "; ".join(f"{n}={v}" for n, v, t in args)

        print(f"  {mt} | {ct} | {args_str}")

conn.close()
