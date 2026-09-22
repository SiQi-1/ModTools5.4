import sqlite3
db_path = r"C:\Users\24948\AppData\Local\Firaxis Games\Sid Meier's Civilization VI\Cache\DebugGameplay.sqlite"
conn = sqlite3.connect(db_path)
c = conn.cursor()

# 1. FREE_POWER_SOURCE values from ModifierArguments
print("=== FREE_POWER_SOURCE values in ModifierArguments ===")
for r in c.execute("""SELECT DISTINCT ma.Value FROM ModifierArguments ma
    WHERE ma.Name = 'SourceType'
    ORDER BY ma.Value"""):
    print(f"  {r[0]}")

print()

# 2. IMPROVEMENT/Terrain/Feature params
print("=== EFFECT_ADJUST_PLAYER_TERRAIN_WORK_IMPASSABLE_MODIFIER params ===")
for r in c.execute("""SELECT DISTINCT ma.Name, ma.Value FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType = 'MODIFIER_PLAYER_ADJUST_TERRAIN_WORKABLE'"""):
    print(f"  {r[0]} = {r[1]}")

print()

# 3. FEATURE_UNLOCK vs FEATURE_PREREQ
print("=== MODIFIER_PLAYER_ADJUST_FEATURE_UNLOCK params & existence ===")
for r in c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE ModifierType LIKE '%FEATURE%UNLOCK%' OR ModifierType LIKE '%FEATURE%PREREQ%'"):
    print(f"  {r[0]} | {r[1]}")
for r in c.execute("""SELECT DISTINCT ma.Name FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType LIKE '%FEATURE_UNLOCK%' OR m.ModifierType LIKE '%FEATURE_PREREQ%'"""):
    print(f"  param: {r[0]}")

print()

# 4. Check MODIFIER_SINGLE_CITY_TERRAIN_ADJACENCY exists
print("=== MODIFIER_SINGLE_CITY_TERRAIN_ADJACENCY ===")
for r in c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE ModifierType = 'MODIFIER_SINGLE_CITY_TERRAIN_ADJACENCY'"):
    print(f"  {r[0]} | {r[1]}")
for r in c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE ModifierType LIKE '%TERRAIN_ADJACENCY%'"):
    print(f"  {r[0]} | {r[1]}")

print()

# 5. Check MODIFIER_ALL_CITIES_IMPROVEMENT_ADJACENCY
print("=== MODIFIER_ALL_CITIES_IMPROVEMENT_ADJACENCY ===")
for r in c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE ModifierType LIKE '%IMPROVEMENT_ADJACENCY%'"):
    print(f"  {r[0]} | {r[1]}")

print()

# 6. IMPROVEMENT_GOODY_HUT params
print("=== EFFECT_ADJUST_IMPROVEMENT_GOODY_HUT params ===")
for r in c.execute("""SELECT DISTINCT ma.Name FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType = 'MODIFIER_PLAYER_ADJUST_IMPROVEMENT_GOODY_HUT'"""):
    print(f"  {r[0]}")

print()

# 7. RESOURCE harvest bonus - SIQI variants
print("=== CITY_RESOURCE_HARVEST_BONUS ModifierTypes ===")
for r in c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE ModifierType LIKE '%HARVEST_BONUS%'"):
    print(f"  {r[0]} | {r[1]}")

print()

# 8. STRATEGIC_RESOURCE_REQUIREMENT_MODIFIER variants
print("=== STRATEGIC_RESOURCE_REQUIREMENT ModifierTypes ===")
for r in c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE ModifierType LIKE '%STRATEGIC_RESOURCE%'"):
    print(f"  {r[0]} | {r[1]}")

print()

# 9. RESOURCE_STOCKPILE_CAP
print("=== RESOURCE_STOCKPILE_CAP ModifierTypes ===")
for r in c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE ModifierType LIKE '%STOCKPILE_CAP%'"):
    print(f"  {r[0]} | {r[1]}")

print()

# 10. FREE_RESOURCE_EXTRACTED vs FREE_RESOURCE_EXTRACTION
print("=== FREE_RESOURCE_EXTRACTED/EXTRACTION ModifierTypes ===")
for r in c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE ModifierType LIKE '%FREE_RESOURCE_EXTRAC%' OR ModifierType LIKE '%FREE_RESOURCE%IMPORT%'"):
    print(f"  {r[0]} | {r[1]}")

print()
for r in c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE ModifierType LIKE '%FREE_RESOURCE%' ORDER BY ModifierType"):
    print(f"  {r[0]} | {r[1]}")

conn.close()
