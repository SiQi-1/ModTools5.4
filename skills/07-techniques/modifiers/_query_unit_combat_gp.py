import sqlite3
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

db = r"C:\Users\24948\AppData\Local\Firaxis Games\Sid Meier's Civilization VI\Cache\DebugGameplay.sqlite"
output_file = r"D:\文明6mod用文件夹\AI制作Mod\skills\07-techniques\modifiers\_unit_combat_gpbirth.txt"

md_file = r"D:\文明6mod用文件夹\AI制作Mod\skills\07-techniques\modifiers\modifier-unit-combat.md"
with open(md_file, 'r', encoding='utf-8') as f:
    content = f.read()

effect_types = re.findall(r'### (EFFECT_\w+|GRANT_\w+)', content)
print(f"Found {len(effect_types)} EffectTypes")

conn = sqlite3.connect(db)
cursor = conn.cursor()

with open(output_file, 'w', encoding='utf-8') as f:
    for et in effect_types:
        # Get ModifierType from DynamicModifiers
        cursor.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE EffectType = ?", (et,))
        dm_rows = cursor.fetchall()

        if not dm_rows:
            f.write(f"{et}: NO DynamicModifiers entry\n")
            continue

        for dm in dm_rows:
            mt = dm[0]
            # Check if this ModifierType appears in GreatPersonIndividualBirthModifiers
            cursor.execute("""
                SELECT COUNT(*), gpb.GreatPersonIndividualType
                FROM Modifiers m
                JOIN GreatPersonIndividualBirthModifiers gpb ON m.ModifierId = gpb.ModifierId
                WHERE m.ModifierType = ?
                GROUP BY gpb.GreatPersonIndividualType
            """, (mt,))
            gp_rows = cursor.fetchall()

            if gp_rows:
                f.write(f"{et}: GP_BIRTH FOUND - {len(gp_rows)} GP individuals use {mt}\n")
            # else:
            #     f.write(f"{et}: NOT GP_BIRTH\n")

# Only print those with GP_BIRTH
conn.close()
print(f"Output written to {output_file}")
