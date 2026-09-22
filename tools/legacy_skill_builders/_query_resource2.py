import sqlite3

db_path = "C:/Users/24948/AppData/Local/Firaxis Games/Sid Meier's Civilization VI/Cache/DebugGameplay.sqlite"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Check for EffectTypes with multiple ModifierType entries
effects = [
    "EFFECT_ADJUST_ADD_AMENITY_PER_ADJACENT_LUXURY",
    "EFFECT_ADJUST_CITY_EXTRA_ACCUMULATION_FOR_STRATEGIC_DIVERSITY",
    "EFFECT_ADJUST_CITY_EXTRA_ACCUMULATION_SPECIFIC_RESOURCE",
    "EFFECT_ADJUST_CITY_EXTRA_AMENITY_FOR_LUXURY_DIVERSITY",
    "EFFECT_ADJUST_CITY_FREE_POWER",
    "EFFECT_ADJUST_CITY_IGNORE_STRATEGIC_RESOURCE_REQUIREMENTS",
    "EFFECT_ADJUST_CITY_REQUIRED_POWER",
    "EFFECT_ADJUST_CITY_RESOURCE_HARVEST_BONUS",
    "EFFECT_ADJUST_CITY_STRATEGIC_RESOURCE_REQUIREMENT_MODIFIER",
    "EFFECT_ADJUST_FULL_ACCESS_ONE_STRATEGIC",
    "EFFECT_ADJUST_MODIFIED_FREE_POWER_IN_CITY",
    "EFFECT_ADJUST_MOST_ADVANCED_STRATEGIC_RESOURCE_COUNT",
    "EFFECT_ADJUST_OWNED_BONUS_RESOURCE_EXTRA_AMENITIES",
    "EFFECT_ADJUST_OWNED_LUXURY_EXTRA_AMENITIES",
    "EFFECT_ADJUST_PLAYER_BAN_RESOURCE",
    "EFFECT_ADJUST_PLAYER_FREE_RESOURCE_IMPORT",
    "EFFECT_ADJUST_PLAYER_FREE_RESOURCE_IMPORT_EXTRACTION",
    "EFFECT_ADJUST_PLAYER_NO_CAP_RESOURCE",
    "EFFECT_ADJUST_PLAYER_PREVENT_HARVEST_RESOURCE",
    "EFFECT_ADJUST_PLAYER_RESOURCE_ACCUMULATION_MODIFIER",
    "EFFECT_ADJUST_PLAYER_RESOURCE_STOCKPILE_CAP",
    "EFFECT_ADJUST_RESOURCE_YIELD_BY_COUNT",
    "EFFECT_ADJUST_YIELD_BY_NUMBER_OF_RESOURCES",
    "EFFECT_CITY_GRANT_RANDOM_RESOURCE_PRODUCT",
    "EFFECT_GRANT_FREE_RESOURCE_EXTRACTED",
    "EFFECT_GRANT_FREE_RESOURCE_IN_CITY",
    "EFFECT_GRANT_FREE_RESOURCE_VISIBILITY",
    "EFFECT_GRANT_PLAYER_FREE_RESOURCE_EXTRACTED"
]

print("=== ALL DynamicModifiers entries for our 28 effects ===")
placeholders = ",".join(["?"] * len(effects))
cur.execute(
    "SELECT EffectType, ModifierType, CollectionType FROM DynamicModifiers WHERE EffectType IN ({}) ORDER BY EffectType, ModifierType".format(placeholders),
    effects
)
for row in cur.fetchall():
    print("  {} | {} | {}".format(row[0], row[1], row[2]))

# Also check what EffectType maps to these extra modifier types
extra_types = [
    "MODIFIER_SINGLE_CITY_ADJUST_FREE_POWER",
    "MODIFIER_SIQI32_PLAYER_CITIES_ADJUST_STRATEGIC_RESOURCE",
    "MODIFIER_SIQI_CITIES_ADJUST_RESOURCE_HARVEST_BONUS",
    "MODIFIER_EMERGENCY_CITIES_GRANT_FREE_RESOURCE_IN_CITY",
    "MODIFIER_PLAYER_CITIES_ADJUST_RESOURCE_STOCKPILE_CAP"
]

print()
print("=== Check EffectType for extra ModifierTypes ===")
for mt in extra_types:
    cur.execute("SELECT EffectType, ModifierType, CollectionType FROM DynamicModifiers WHERE ModifierType = ?", (mt,))
    rows = cur.fetchall()
    if rows:
        for r in rows:
            print("  {} | {} | {}".format(r[0], r[1], r[2]))
    else:
        print("  {} | NOT IN DynamicModifiers".format(mt))

# Check if EFFECT_ADJUST_CITY_FREE_POWER has two entries
print()
print("=== All DynamicModifiers entries for EFFECT_ADJUST_CITY_FREE_POWER ===")
cur.execute("SELECT * FROM DynamicModifiers WHERE EffectType = 'EFFECT_ADJUST_CITY_FREE_POWER'")
for r in cur.fetchall():
    print("  {}".format(r))

# Check what effect MODIFIER_SINGLE_CITY_ADJUST_FREE_POWER is for
print()
print("=== Full DynamicModifiers rows for MODIFIER_SINGLE_CITY_ADJUST_FREE_POWER ===")
cur.execute("SELECT * FROM DynamicModifiers WHERE ModifierType = 'MODIFIER_SINGLE_CITY_ADJUST_FREE_POWER'")
for r in cur.fetchall():
    print("  {}".format(r))

conn.close()
