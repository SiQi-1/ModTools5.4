import sqlite3
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

db = r"C:\Users\24948\AppData\Local\Firaxis Games\Sid Meier's Civilization VI\Cache\DebugGameplay.sqlite"
local_db = r"D:\文明6mod用文件夹\AI制作Mod\reference\local_text_New.sqlite"
output_file = r"D:\文明6mod用文件夹\AI制作Mod\skills\07-techniques\modifiers\_unit_combat_info.txt"

# Extract all EffectTypes from the markdown file
md_file = r"D:\文明6mod用文件夹\AI制作Mod\skills\07-techniques\modifiers\modifier-unit-combat.md"
with open(md_file, 'r', encoding='utf-8') as f:
    content = f.read()

effect_types = re.findall(r'### (EFFECT_\w+|GRANT_\w+)', content)
print(f"Found {len(effect_types)} EffectTypes")

conn = sqlite3.connect(db)
cursor = conn.cursor()

# Discover available tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
all_tables = [r[0] for r in cursor.fetchall()]
print(f"DB has {len(all_tables)} tables")

with open(output_file, 'w', encoding='utf-8') as f:
    for et in effect_types:
        f.write(f"\n{'='*80}\n")
        f.write(f"EffectType: {et}\n")
        f.write(f"{'='*80}\n")

        # Find ModifierIds
        cursor.execute("SELECT ModifierId FROM Modifiers WHERE ModifierType = ? LIMIT 20", (et,))
        modifiers = [r[0] for r in cursor.fetchall()]
        f.write(f"  ModifierIds: {len(modifiers)}\n")

        all_args = set()
        for mid in modifiers:
            cursor.execute("SELECT Name, Value FROM ModifierArguments WHERE ModifierId = ?", (mid,))
            for arg in cursor.fetchall():
                all_args.add((arg[0], arg[1]))
            # Check GP birth
            cursor.execute("SELECT 1 FROM GreatPersonIndividualBirthModifiers WHERE ModifierId = ?", (mid,))
            if cursor.fetchone():
                f.write(f"    {mid} -> GP_BIRTH\n")
        for a in sorted(all_args)[:10]:
            f.write(f"    Arg: {a[0]} = {a[1]}\n")

        # Check GP_BIRTH via direct query
        cursor.execute("""
            SELECT COUNT(*) FROM Modifiers m
            JOIN GreatPersonIndividualBirthModifiers g ON m.ModifierId = g.ModifierId
            WHERE m.ModifierType = ?
        """, (et,))
        gp_count = cursor.fetchone()[0]

        # Determine upstream categories
        upstream_cats = []
        for mid in modifiers[:5]:
            # Policies
            cursor.execute("SELECT PolicyType FROM PolicyModifiers WHERE ModifierId = ?", (mid,))
            for r in cursor.fetchall():
                cat = f"Policy:{r[0]}"
                if cat not in upstream_cats: upstream_cats.append(cat)
            # Traits
            cursor.execute("SELECT TraitType FROM TraitModifiers WHERE ModifierId = ?", (mid,))
            for r in cursor.fetchall():
                cat = f"Trait:{r[0]}"
                if cat not in upstream_cats: upstream_cats.append(cat)
            # UnitAbilities
            cursor.execute("SELECT UnitAbilityType FROM UnitAbilityModifiers WHERE ModifierId = ?", (mid,))
            for r in cursor.fetchall():
                cat = f"UnitAbility:{r[0]}"
                if cat not in upstream_cats: upstream_cats.append(cat)
            # UnitPromotions
            cursor.execute("SELECT UnitPromotionType FROM UnitPromotionModifiers WHERE ModifierId = ?", (mid,))
            for r in cursor.fetchall():
                cat = f"UnitPromotion:{r[0]}"
                if cat not in upstream_cats: upstream_cats.append(cat)
            # GovernorPromotions
            cursor.execute("SELECT GovernorPromotionType FROM GovernorPromotionModifiers WHERE ModifierId = ?", (mid,))
            for r in cursor.fetchall():
                cat = f"GovPromo:{r[0]}"
                if cat not in upstream_cats: upstream_cats.append(cat)
            # Buildings
            cursor.execute("SELECT BuildingType FROM BuildingModifiers WHERE ModifierId = ?", (mid,))
            for r in cursor.fetchall():
                cat = f"Building:{r[0]}"
                if cat not in upstream_cats: upstream_cats.append(cat)
            # GreatPersonIndividuals
            cursor.execute("SELECT GreatPersonIndividualType FROM GreatPersonIndividualActionModifiers WHERE ModifierId = ?", (mid,))
            for r in cursor.fetchall():
                cat = f"GP_Action:{r[0]}"
                if cat not in upstream_cats: upstream_cats.append(cat)
            # Civics
            cursor.execute("SELECT CivicType FROM CivicModifiers WHERE ModifierId = ?", (mid,))
            for r in cursor.fetchall():
                cat = f"Civic:{r[0]}"
                if cat not in upstream_cats: upstream_cats.append(cat)
            # Technologies
            cursor.execute("SELECT TechnologyType FROM TechnologyModifiers WHERE ModifierId = ?", (mid,))
            for r in cursor.fetchall():
                cat = f"Tech:{r[0]}"
                if cat not in upstream_cats: upstream_cats.append(cat)
            # Beliefs
            cursor.execute("SELECT BeliefType FROM BeliefModifiers WHERE ModifierId = ?", (mid,))
            for r in cursor.fetchall():
                cat = f"Belief:{r[0]}"
                if cat not in upstream_cats: upstream_cats.append(cat)
            # Districts
            cursor.execute("SELECT DistrictType FROM DistrictModifiers WHERE ModifierId = ?", (mid,))
            for r in cursor.fetchall():
                cat = f"District:{r[0]}"
                if cat not in upstream_cats: upstream_cats.append(cat)
            # Commemorations
            cursor.execute("SELECT CommemorationType FROM CommemorationModifiers WHERE ModifierId = ?", (mid,))
            for r in cursor.fetchall():
                cat = f"Comm:{r[0]}"
                if cat not in upstream_cats: upstream_cats.append(cat)

        if upstream_cats:
            f.write(f"  Upstream: {'; '.join(upstream_cats[:15])}\n")

        # GP_BIRTH summary
        if gp_count > 0:
            f.write(f"  >> GP_BIRTH({gp_count}): YES -> NO ModifierStrings (GP handles text)\n")
        else:
            f.write(f"  >> GP_BIRTH: 0 -> NEEDS ModifierStrings\n")

        f.write(f"  ---\n")

conn.close()
print(f"Output written to {output_file}")
