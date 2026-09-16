import os
base = r"D:\文明6mod用文件夹\AI制作Mod\skills\07-techniques\modifiers"
files = [
    "_query_unit_combat.py", "_query_unit_combat_gp.py", "_unit_combat_info.txt", "_unit_combat_gpbirth.txt",
    "_generate_updated_md.py", "_verify_gp.py", "_generate_final.py", "_upgrade_templates.py",
    "_fix_templates.py", "run_gen.py", "copy_final.py", "modifier-unit-combat-NEW.md"
]
for f in files:
    path = os.path.join(base, f)
    if os.path.exists(path):
        os.remove(path)
        print(f"Deleted: {f}")
    else:
        print(f"Not found: {f}")
print("Cleanup done!")
