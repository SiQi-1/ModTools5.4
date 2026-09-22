import shutil
src = r"D:\文明6mod用文件夹\AI制作Mod\skills\07-techniques\modifiers\modifier-unit-combat-NEW.md"
dst = r"D:\文明6mod用文件夹\AI制作Mod\skills\07-techniques\modifiers\modifier-unit-combat.md"
shutil.copy2(src, dst)
print(f"Copied: {src} -> {dst}")
print("Done!")
