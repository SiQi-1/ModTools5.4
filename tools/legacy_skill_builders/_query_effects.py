import sqlite3
import json

db = sqlite3.connect("C:/Users/24948/AppData/Local/Firaxis Games/Sid Meier's Civilization VI/Cache/DebugGameplay.sqlite")
db.row_factory = sqlite3.Row
c = db.cursor()

# Read effects list
with open(r"D:\文明6mod用文件夹\AI制作Mod\skills\07-techniques\modifiers\_modifier-unit-combat.md.effects.txt", encoding="utf-8") as f:
    effects = [line.strip() for line in f if line.strip() and line.strip()[0] == 'E']

results = []
for etype in effects:
    # Find ModifierType from Modifiers table
    c.execute("SELECT ModifierType, CollectionType FROM DynamicModifiers WHERE EffectType = ?", (etype,))
    rows = c.fetchall()

    if not rows:
        results.append({"effect": etype, "modifiers": [], "note": "NOT FOUND"})
        continue

    for row in rows:
        mt = row["ModifierType"]
        ct = row["CollectionType"]
        # Find arguments
        c.execute("SELECT Name, Value, Type FROM ModifierArguments WHERE ModifierId IN (SELECT ModifierId FROM Modifiers WHERE ModifierType = ?) LIMIT 5", (mt,))
        args = [{"name": a["Name"], "value": a["Value"], "type": a["Type"]} for a in c.fetchall()]

        results.append({
            "effect": etype,
            "modifierType": mt,
            "collectionType": ct,
            "arguments": args
        })

with open(r"D:\文明6mod用文件夹\AI制作Mod\skills\07-techniques\modifiers\_query_result.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"Total effects: {len(effects)}, Results: {len(results)}")
