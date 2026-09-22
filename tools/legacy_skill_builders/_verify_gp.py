import sqlite3
import re

db = r"C:\Users\24948\AppData\Local\Firaxis Games\Sid Meier's Civilization VI\Cache\DebugGameplay.sqlite"
md_file = r"D:\文明6mod用文件夹\AI制作Mod\skills\07-techniques\modifiers\modifier-unit-combat.md"

conn = sqlite3.connect(db)
cursor = conn.cursor()

# Check GP_BIRTH for a few key effects to verify the query works
test_effects = [
    "EFFECT_ADJUST_UNIT_DAMAGE",
    "EFFECT_ADJUST_UNIT_MILITARY_FORMATION",
    "EFFECT_ADJUST_UNIT_GRANT_EXPERIENCE",
    "EFFECT_ADJUST_UNIT_IGNORE_RESOURCE_MAINTENANCE",
    "EFFECT_GRANT_FREE_RESOURCE_FROM_UNIT_PLOT",
    "EFFECT_ADJUST_UNIT_MOVEMENT",
    "EFFECT_RESTORE_UNIT_MOVEMENT",
    "EFFECT_ADJUST_UNIT_OWNER",
]

for et in test_effects:
    cursor.execute("SELECT ModifierType FROM DynamicModifiers WHERE EffectType = ?", (et,))
    mts = cursor.fetchall()
    found_birth = False
    for mt_row in mts:
        mt = mt_row[0]
        cursor.execute("""
            SELECT COUNT(*) FROM Modifiers m
            JOIN GreatPersonIndividualBirthModifiers gpb ON m.ModifierId = gpb.ModifierId
            WHERE m.ModifierType = ?
        """, (mt,))
        cnt = cursor.fetchone()[0]
        if cnt > 0:
            found_birth = True
            print(f"{et}: GP_BIRTH via {mt} (count={cnt})")

    if not found_birth:
        print(f"{et}: NOT GP_BIRTH ({len(mts)} modifier types)")

conn.close()
