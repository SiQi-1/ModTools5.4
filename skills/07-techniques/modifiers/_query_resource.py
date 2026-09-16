import sqlite3

db_path = "C:/Users/24948/AppData/Local/Firaxis Games/Sid Meier's Civilization VI/Cache/DebugGameplay.sqlite"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

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

print("=== DynamicModifiers ===")
for e in sorted(effects):
    cur.execute("SELECT EffectType, ModifierType, CollectionType FROM DynamicModifiers WHERE EffectType = ?", (e,))
    row = cur.fetchone()
    if row:
        print("DM|{}|{}|{}".format(row[0], row[1], row[2]))
    else:
        print("DM|{}|NOT_FOUND|NOT_FOUND".format(e))

# Get distinct modifier types for these effects
modifier_types = []
placeholders = ",".join(["?"] * len(effects))
cur.execute(
    "SELECT DISTINCT dm.ModifierType FROM DynamicModifiers dm WHERE dm.EffectType IN ({})".format(placeholders),
    effects
)
for r in cur.fetchall():
    modifier_types.append(r[0])

print()
print("=== ModifierArguments ===")
for mt in sorted(modifier_types):
    cur.execute(
        "SELECT m.ModifierId, ma.Name, ma.Value, ma.Type "
        "FROM Modifiers m JOIN ModifierArguments ma ON m.ModifierId = ma.ModifierId "
        "WHERE m.ModifierType = ? ORDER BY m.ModifierId, ma.Name",
        (mt,)
    )
    rows = cur.fetchall()

    params = {}
    for mod_id, name, val, typ in rows:
        if name not in params:
            params[name] = {"values": set(), "type": typ}
        params[name]["values"].add(str(val))

    print("-- {} --".format(mt))
    for pname in sorted(params.keys()):
        vals = sorted(params[pname]["values"])[:5]
        vlist = ", ".join(vals)
        print("  Param: {} | Type: {} | Eg: {}".format(pname, params[pname]["type"], vlist))

    # Print example ModifierIds
    mod_ids = set()
    for mod_id, name, val, typ in rows:
        mod_ids.add(mod_id)
    print("  ModifierIds (up to 5): {}".format(", ".join(sorted(mod_ids)[:5])))
    print()

conn.close()
