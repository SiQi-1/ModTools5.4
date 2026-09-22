import sqlite3
import os
from urllib.parse import quote

db_path = r"C:\Users\24948\AppData\Local\Firaxis Games\Sid Meier's Civilization VI\Cache\DebugGameplay.sqlite"
assert os.path.exists(db_path), "DB not found"
conn = sqlite3.connect(db_path)
c = conn.cursor()

# 1. Governor ModifierTypes
print("=== GOVERNOR ModifierTypes ===")
for r in c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE ModifierType LIKE '%GOVERNOR%' ORDER BY ModifierType"):
    print(f"  {r[0]} | {r[1]}")
print()

# 2. Governor params
print("=== GOVERNOR ModifierArguments ===")
gov_types = [r[0] for r in c.execute("SELECT ModifierType FROM DynamicModifiers WHERE ModifierType LIKE '%GOVERNOR%'")]
for gt in gov_types:
    params = c.execute("""
        SELECT DISTINCT ma.Name, ma.Value, ma.Type
        FROM ModifierArguments ma JOIN Modifiers m ON ma.ModifierId = m.ModifierId
        WHERE m.ModifierType = ?
    """, (gt,)).fetchall()
    if params:
        print(f"  {gt}:")
        for p in params:
            print(f"    {p[0]} = {p[1]} (Type={p[2]})")

print()

# 3. GreatPeople/GreatWork
print("=== GREAT_PEOPLE/GREAT_WORK ModifierTypes ===")
for r in c.execute("""SELECT ModifierType, CollectionType FROM DynamicModifiers
    WHERE ModifierType LIKE '%GREAT_P%' OR ModifierType LIKE '%GREAT_WORK%'
    OR ModifierType LIKE '%GREATWORK%' OR ModifierType LIKE '%THEMED%'
    OR ModifierType LIKE '%GREAT_PEOPLE%' OR ModifierType LIKE '%NO_GREAT%'
    OR ModifierType LIKE '%GRANT_BOOST%'
    ORDER BY ModifierType"""):
    print(f"  {r[0]} | {r[1]}")
print()

# 3b. Key param check: GreatPersonClass vs GreatPersonClassType
print("=== GRANT_BOOST params (check GreatPersonClass vs GreatPersonClassType) ===")
for r in c.execute("""SELECT DISTINCT ma.Name FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType = 'MODIFIER_PLAYER_GRANT_BOOST_WITH_GREAT_PERSON'"""):
    print(f"  {r[0]}")
print()

print("=== GRANT_GREAT_PERSON_CLASS_IN_CITY params ===")
for r in c.execute("""SELECT DISTINCT ma.Name FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType LIKE '%GRANT_GREAT_PERSON_CLASS_IN_CITY%'"""):
    print(f"  {r[0]}")
print()

print("=== ADJUST_GREAT_PEOPLE_POINTS_PER_KILL params ===")
for r in c.execute("""SELECT DISTINCT ma.Name FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType LIKE '%GREAT_PEOPLE_POINTS_PER_KILL%'"""):
    print(f"  {r[0]}")

print()

# 4. FREE_POWER
print("=== FREE_POWER ModifierTypes ===")
for r in c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE ModifierType LIKE '%FREE_POWER%' OR ModifierType LIKE '%POWER%' ORDER BY ModifierType"):
    print(f"  {r[0]} | {r[1]}")
print()

print("=== FREE_POWER_SOURCE Types ===")
for r in c.execute("SELECT Type FROM Types WHERE Type LIKE '%POWER_SOURCE%' OR Type LIKE '%FREE_POWER%' ORDER BY Type"):
    print(f"  {r[0]}")
print()

print("=== ADJUST_CITY_FREE_POWER params ===")
for r in c.execute("""SELECT DISTINCT ma.Name FROM ModifierArguments ma
    JOIN Modifiers m ON ma.ModifierId = m.ModifierId
    WHERE m.ModifierType LIKE '%ADJUST_FREE_POWER%'"""):
    print(f"  {r[0]}")

print()

# 5. IMPROVEMENT/Terrain/Feature adjacency
print("=== ADJACENCY ModifierTypes (improvement/terrain/feature) ===")
for r in c.execute("""SELECT ModifierType, CollectionType FROM DynamicModifiers
    WHERE (ModifierType LIKE '%IMPROVEMENT%ADJACENCY%' OR ModifierType LIKE '%TERRAIN%ADJACENCY%'
    OR ModifierType LIKE '%FEATURE%ADJACENCY%')
    ORDER BY ModifierType"""):
    print(f"  {r[0]} | {r[1]}")
print()

print("=== Adjacency_YieldChanges columns ===")
for r in c.execute("PRAGMA table_info(Adjacency_YieldChanges)"):
    print(f"  {r[1]} ({r[2]})")
print()

# Sample from Adjacency_YieldChanges
print("=== Adjacency_YieldChanges sample (5 rows) ===")
for r in c.execute("SELECT * FROM Adjacency_YieldChanges LIMIT 5"):
    print(f"  {r}")

conn.close()
