import sqlite3
db_path = r"C:\Users\24948\AppData\Local\Firaxis Games\Sid Meier's Civilization VI\Cache\DebugGameplay.sqlite"
conn = sqlite3.connect(db_path)
c = conn.cursor()

# 1. Check FEATURE_PREREQ specifically
print("=== FEATURE_PREREQ vs FEATURE_UNLOCK ===")
for r in c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE ModifierType LIKE '%FEATURE%'"):
    if 'FEATURE' in r[0]:
        print(f"  {r[0]} | {r[1]}")

print()

# 2. Check MODIFIER_CITY_ADJUST_FEATURE_APPEAL_MODIFIER
print("=== FEATURE_APPEAL_MODIFIER ===")
for r in c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE ModifierType LIKE '%FEATURE_APPEAL%' OR ModifierType LIKE '%APPEAL_MODIFIER%'"):
    print(f"  {r[0]} | {r[1]}")

print()

# 3. Check MODIFIER_CITY_OWNER_ADJUST_IMPROVEMENT_AMENITY
print("=== IMPROVEMENT_AMENITY ModifierTypes ===")
for r in c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE ModifierType LIKE '%IMPROVEMENT_AMENITY%' OR ModifierType LIKE '%IMPROVEMENT_HOUSING%' OR ModifierType LIKE '%IMPROVEMENT_TOURISM%'"):
    print(f"  {r[0]} | {r[1]}")

print()

# 4. Check EFFECT_ADJUST_CITY_ALLOWED_IMPROVEMENT
print("=== CITY_ALLOWED_IMPROVEMENT ===")
for r in c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE ModifierType LIKE '%ALLOWED_IMPROVEMENT%' OR ModifierType LIKE '%VALID_IMPROVEMENT%'"):
    print(f"  {r[0]} | {r[1]}")

print()

# 5. Check EFFECT_GRANT_PLAYER_FAITH_FROM_REMOVE_FEATURE params
print("=== GRANT_PLAYER_FAITH_FROM_REMOVE_FEATURE ===")
for r in c.execute("""SELECT DISTINCT ma.Name, ma.Value FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType = 'MODIFIER_PLAYER_GRANT_FAITH_FROM_REMOVE_FEATURE'"""):
    print(f"  {r[0]} = {r[1]}")

print()

# 6. Check GRANT_PLOT
print("=== UNIT_GRANT_PLOT params ===")
for r in c.execute("""SELECT DISTINCT ma.Name FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType = 'MODIFIER_UNIT_GRANT_PLOT'"""):
    print(f"  {r[0]}")

print()

# 7. Check the EFFECT_ADJUST_OWNED_BONUS_RESOURCE_EXTRA_AMENITIES params
print("=== OWNED_BONUS_RESOURCE_EXTRA_AMENITIES ===")
for r in c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE ModifierType LIKE '%BONUS_RESOURCE%'"):
    print(f"  {r[0]} | {r[1]}")

print()

# 8. Check EFFECT_GRANT_FREE_RESOURCE_VISIBILITY params
print("=== GRANT_FREE_RESOURCE_VISIBILITY params ===")
for r in c.execute("""SELECT DISTINCT ma.Name FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType = 'MODIFIER_PLAYER_GRANT_FREE_RESOURCE_VISIBILITY'"""):
    print(f"  {r[0]}")

print()

# 9. Check ADJUST_CITY_EXTRA_AMENITY_FOR_LUXURY_DIVERSITY
print("=== LUXURY_DIVERSITY ===")
for r in c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE ModifierType LIKE '%LUXURY_DIVERSITY%'"):
    print(f"  {r[0]} | {r[1]}")

print()

# 10. Check GRANT_RANDOM_RESOURCE_PRODUCT
print("=== GRANT_RANDOM_RESOURCE_PRODUCT ===")
for r in c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE ModifierType LIKE '%RANDOM_RESOURCE%' OR ModifierType LIKE '%RESOURCE_PRODUCT%'"):
    print(f"  {r[0]} | {r[1]}")
for r in c.execute("""SELECT DISTINCT ma.Name FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType LIKE '%RANDOM_RESOURCE%' OR m.ModifierType LIKE '%RESOURCE_PRODUCT%'"""):
    print(f"  param: {r[0]}")

print()

# 11. EFFECT_ADJUST_PLAYER_BAN_RESOURCE
print("=== BAN_RESOURCE ===")
for r in c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE ModifierType LIKE '%BAN_RESOURCE%' OR ModifierType LIKE '%NO_CAP_RESOURCE%' OR ModifierType LIKE '%PREVENT_HARVEST%'"):
    print(f"  {r[0]} | {r[1]}")
for r in c.execute("""SELECT DISTINCT ma.Name FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType LIKE '%BAN_RESOURCE%'"""):
    print(f"  BAN param: {r[0]}")
for r in c.execute("""SELECT DISTINCT ma.Name FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType LIKE '%NO_CAP_RESOURCE%'"""):
    print(f"  NO_CAP param: {r[0]}")
for r in c.execute("""SELECT DISTINCT ma.Name FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType LIKE '%PREVENT_HARVEST%'"""):
    print(f"  PREVENT_HARVEST param: {r[0]}")

print()

# 12. MODIFIER_SINGLE_CITY_ADJUST_IMPROVEMENT_HOUSING
print("=== IMPROVEMENT_HOUSING params ===")
for r in c.execute("""SELECT DISTINCT ma.Name FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType LIKE '%IMPROVEMENT_HOUSING%'"""):
    print(f"  {r[0]}")

print()

# 13. Check FREE_POWER_SOURCE in a different way
print("=== Types with POWER_SOURCE ===")
for r in c.execute("SELECT Type FROM Types WHERE Type LIKE '%FREE%POWER%SOURCE%' OR Type LIKE 'FREE_POWER_SOURCE%'"):
    print(f"  {r[0]}")

conn.close()
