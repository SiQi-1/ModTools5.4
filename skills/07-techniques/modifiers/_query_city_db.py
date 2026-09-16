import sqlite3

db_path = r"C:\Users\24948\AppData\Local\Firaxis Games\Sid Meier's Civilization VI\Cache\DebugGameplay.sqlite"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Check Modifiers table for entries using MODIFIER_PLAYER_CAPITAL_CITY_ADJUST_CITY_GROWTH
# and other no-param ModifierTypes
no_param_types = [
    "MODIFIER_PLAYER_CAPITAL_CITY_ADJUST_CITY_GROWTH",
    "MODIFIER_PLAYER_CITIES_ADJUST_CITY_HIT_POINTS",
    "MODIFIER_SINGLE_CITY_ADJUST_IDENTITY_PRESSURE",
    "MODIFIER_PLAYER_CAPITAL_CITY_ADJUST_CITY_YIELD_MODIFIER",
    "MODIFIER_PLAYER_CITIES_NO_CULTURE_BORDER_EXPANSION",
    "MODIFIER_SINGLE_CITY_ADJUST_PREVENT_BYPASS_OUTER_DEFENSE",
    "MODIFIER_SINGLE_CITY_ADJUST_PREVENT_MELEE_ATTACK_OUTER_DEFENSES",
    "MODIFIER_SINGLE_CITY_RECOMMISSION_REACTOR",
    "MODIFIER_PLAYER_CITIES_GRANT_ROAD_TO_CAPITAL",
    "MODIFIER_PLAYER_CITIES_GRANT_TRADING_POST",
    "MODIFIER_EMERGENCY_CITIES_KILL_ALL_EMERGENCY_TARGET_SPIES",
    "MODIFIER_CITY_PURCHASE_PRODUCTION",
    "MODIFIER_PLAYER_ADD_UPGRADE_MILITARY_FORMATION_ON_CITY_CONQUEST",
]

for mt in no_param_types:
    cur.execute("SELECT ModifierId FROM Modifiers WHERE ModifierType = ?", (mt,))
    results = cur.fetchall()
    if results:
        print(f"\n{mt}: {len(results)} ModifierId(s)")
        for r in results[:3]:
            # check args
            cur.execute("SELECT Name, Value, Type FROM ModifierArguments WHERE ModifierId = ?", (r[0],))
            args = cur.fetchall()
            print(f"  {r[0]}: args={[(a[0], a[1]) for a in args]}")
    else:
        print(f"\n{mt}: NO Modifiers entries found")

# Also check EFFECT_ADJUST_PLAYER_BAN_CITY_PRODUCTION parameter details
print("\n\n=== Checking BanDistrictBuildings usage ===")
cur.execute("""
    SELECT ma.ModifierId, ma.Name, ma.Value, ma.Type
    FROM ModifierArguments ma
    WHERE ma.Name = 'BanDistrictBuildings'
""")
for r in cur.fetchall():
    print(f"  {r}")

conn.close()
