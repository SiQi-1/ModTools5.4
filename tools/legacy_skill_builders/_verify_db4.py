import sqlite3
db_path = r"C:\Users\24948\AppData\Local\Firaxis Games\Sid Meier's Civilization VI\Cache\DebugGameplay.sqlite"
conn = sqlite3.connect(db_path)
c = conn.cursor()

# 1. Check DynamicModifiers structure
print("=== DynamicModifiers columns ===")
for r in c.execute("PRAGMA table_info(DynamicModifiers)"):
    print(f"  {r[1]} ({r[2]})")

# 2. Which EffectType maps to which ModifierType
print("\n=== Key EffectType-ModifierType mappings ===")
for r in c.execute("""
    SELECT EffectType, ModifierType, CollectionType FROM DynamicModifiers
    WHERE ModifierType IN (
        'MODIFIER_SINGLE_CITY_ADJUST_FREE_RESOURCE_EXTRACTION',
        'MODIFIER_EMERGENCY_CITIES_GRANT_FREE_RESOURCE_IN_CITY',
        'MODIFIER_PLAYER_ADJUST_FREE_RESOURCE_EXTRACTION',
        'MODIFIER_PLAYER_ADJUST_FREE_RESOURCE_IMPORT',
        'MODIFIER_PLAYER_ADJUST_FREE_RESOURCE_IMPORT_EXTRACTION'
    )
"""):
    print(f"  {r[0]} -> {r[1]} ({r[2]})")

print("\n=== FEATURE_UNLOCK EffectType ===")
for r in c.execute("""
    SELECT EffectType, ModifierType, CollectionType FROM DynamicModifiers
    WHERE ModifierType = 'MODIFIER_PLAYER_ADJUST_FEATURE_UNLOCK'
"""):
    print(f"  {r[0]} -> {r[1]} ({r[2]})")

print("\n=== ALL IMPROVEMENT/Terrain/Feature ADJACENCY EffectTypes ===")
for r in c.execute("""
    SELECT EffectType, ModifierType, CollectionType FROM DynamicModifiers
    WHERE (ModifierType LIKE '%IMPROVEMENT_ADJACENCY%' OR ModifierType LIKE '%TERRAIN_ADJACENCY%'
    OR ModifierType LIKE '%FEATURE_ADJACENCY%')
"""):
    print(f"  {r[0]} -> {r[1]} ({r[2]})")

print("\n=== EFFECT_HOUSING params including IMPROVEMENT_HOUSING ===")
for r in c.execute("""
    SELECT DISTINCT ma.Name FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType = 'MODIFIER_SINGLE_CITY_ADJUST_IMPROVEMENT_HOUSING'
"""):
    print(f"  {r[0]}")

# Check if there's also ImprovementType in some Modifier instances
print("\n=== IMPROVEMENT_HOUSING ModifierArguments with ImprovementType ===")
for r in c.execute("""
    SELECT ma.ModifierId, ma.Name, ma.Value FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType = 'MODIFIER_SINGLE_CITY_ADJUST_IMPROVEMENT_HOUSING' AND ma.Name = 'ImprovementType'
"""):
    print(f"  {r[0]}: {r[1]} = {r[2]}")

print("\n=== EFFECT_ADJUST_CITY_APPEAL params ===")
for r in c.execute("""
    SELECT DISTINCT ma.Name FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType IN ('MODIFIER_SINGLE_CITY_ADJUST_CITY_APPEAL', 'MODIFIER_PLAYER_CITIES_ADJUST_CITY_APPEAL')
"""):
    print(f"  {r[0]}")

print("\n=== ALL_CITIES_IMPROVEMENT_ADJACENCY check ===")
for r in c.execute("SELECT ModifierType FROM DynamicModifiers WHERE ModifierType = 'MODIFIER_ALL_CITIES_IMPROVEMENT_ADJACENCY'"):
    print(f"  FOUND: {r[0]}")
if not c.execute("SELECT ModifierType FROM DynamicModifiers WHERE ModifierType = 'MODIFIER_ALL_CITIES_IMPROVEMENT_ADJACENCY'").fetchall():
    print("  NOT FOUND in DB")

print("\n=== SINGLE_CITY_TERRAIN_ADJACENCY check ===")
for r in c.execute("SELECT ModifierType FROM DynamicModifiers WHERE ModifierType = 'MODIFIER_SINGLE_CITY_TERRAIN_ADJACENCY'"):
    print(f"  FOUND: {r[0]}")
if not c.execute("SELECT ModifierType FROM DynamicModifiers WHERE ModifierType = 'MODIFIER_SINGLE_CITY_TERRAIN_ADJACENCY'").fetchall():
    print("  NOT FOUND in DB")

print("\n=== FEATURE_PREREQ check ===")
for r in c.execute("SELECT ModifierType FROM DynamicModifiers WHERE ModifierType LIKE '%FEATURE_PREREQ%'"):
    print(f"  FOUND: {r[0]}")
if not c.execute("SELECT ModifierType FROM DynamicModifiers WHERE ModifierType LIKE '%FEATURE_PREREQ%'").fetchall():
    print("  NOT FOUND in DB")

print("\n=== EFFECT_ADJUST_RESOURCE_YIELD_BY_COUNT params ===")
for r in c.execute("""
    SELECT DISTINCT ma.Name FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType = 'MODIFIER_PLAYER_CITIES_ADJUST_RESOURCE_YIELD_BY_COUNT'
"""):
    print(f"  {r[0]}")

print("\n=== EFFECT_ADJUST_YIELD_BY_NUMBER_OF_RESOURCES params ===")
for r in c.execute("""
    SELECT DISTINCT ma.Name FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType = 'MODIFIER_PLAYER_CITIES_ADJUST_YIELD_BY_NUMBER_RESOURCES'
"""):
    print(f"  {r[0]}")

print("\n=== EFFECT_ADJUST_EXTRA_ACCUMALATION_TERRAIN params ===")
for r in c.execute("""
    SELECT DISTINCT ma.Name FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType = 'MODIFIER_PLAYER_CITIES_ADJUST_EXTRA_ACCUMALATION_TERRAIN'
"""):
    print(f"  {r[0]}")

conn.close()
