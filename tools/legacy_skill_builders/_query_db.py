import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8')

db = r"C:\Users\24948\AppData\Local\Firaxis Games\Sid Meier's Civilization VI\Cache\DebugGameplay.sqlite"
local_db = r"D:\文明6mod用文件夹\AI制作Mod\reference\local_text_New.sqlite"
output_file = r"D:\文明6mod用文件夹\AI制作Mod\skills\07-techniques\modifiers\_trace_result6.txt"

with open(output_file, 'w', encoding='utf-8') as f:
    conn = sqlite3.connect(db)
    cursor = conn.cursor()

    # 1. Check all modifiers on INDUSTRIALIST promotion
    f.write("=== All modifiers on GOVERNOR_PROMOTION_RESOURCE_MANAGER_INDUSTRIALIST ===\n")
    cursor.execute("""
        SELECT m.ModifierId, m.ModifierType, m.SubjectRequirementSetId
        FROM GovernorPromotionModifiers gpm
        JOIN Modifiers m ON gpm.ModifierId = m.ModifierId
        WHERE gpm.GovernorPromotionType = 'GOVERNOR_PROMOTION_RESOURCE_MANAGER_INDUSTRIALIST'
    """)
    for r in cursor.fetchall():
        f.write(f"  {r[0]}\n    ModifierType={r[1]}\n    SubjectReqSet={r[2]}\n")
        cursor.execute("SELECT Name, Value FROM ModifierArguments WHERE ModifierId = ?", (r[0],))
        for a in cursor.fetchall():
            f.write(f"    Arg: {a[0]} = {a[1]}\n")

    # 2. Check EFFECT_ADJUST_GOVERNOR_ALLIANCE_POINTS upstream Chinese text
    f.write("\n=== KHASS_ODA_BASHI promotion details ===\n")
    cursor.execute("""
        SELECT m.ModifierId, m.ModifierType
        FROM GovernorPromotionModifiers gpm
        JOIN Modifiers m ON gpm.ModifierId = m.ModifierId
        WHERE gpm.GovernorPromotionType = 'GOVERNOR_PROMOTION_KHASS_ODA_BASHI'
    """)
    for r in cursor.fetchall():
        f.write(f"  {r[0]} -> {r[1]}\n")
        cursor.execute("SELECT Name, Value FROM ModifierArguments WHERE ModifierId = ?", (r[0],))
        for a in cursor.fetchall():
            f.write(f"    Arg: {a[0]} = {a[1]}\n")

    # 3. Check AMBASSADOR_AFFLUENCE multiple effects
    f.write("\n=== ALL modifiers on GOVERNOR_PROMOTION_AMBASSADOR_AFFLUENCE ===\n")
    cursor.execute("SELECT gpm.ModifierId, gpm.GovernorPromotionType FROM GovernorPromotionModifiers gpm WHERE gpm.GovernorPromotionType = 'GOVERNOR_PROMOTION_AMBASSADOR_AFFLUENCE'")
    for r in cursor.fetchall():
        f.write(f"  {r[0]}\n")
        cursor.execute("SELECT m.ModifierType FROM Modifiers m WHERE m.ModifierId = ?", (r[0],))
        for m in cursor.fetchall():
            f.write(f"    ModifierType: {m[0]}\n")

    # 4. Check the EFFECT_ADJUST_GOVERNOR_IDENITITY_PER_TITLE note: COMMUNICATIONS_OFFICE
    f.write("\n=== MODIFIER_PLAYER_GOVERNORS_ADJUST_IDENTITY_PER_TITLE instance args ===\n")
    cursor.execute("SELECT * FROM ModifierArguments WHERE ModifierId = 'COMMUNICATIONS_OFFICE_GOVERNOR_IDENTITY_PER_TITLE'")
    for r in cursor.fetchall():
        f.write(f"  Name={r[0]}, Value={r[1]}, Type={r[2]}, Extra={r[3] if len(r)>3 else 'N/A'}\n")

    # Check ModifierArguments table structure
    cursor.execute("PRAGMA table_info(ModifierArguments)")
    cols = [r[1] for r in cursor.fetchall()]
    f.write(f"  ModifierArguments columns: {cols}\n")

    # Direct query with full columns
    cursor.execute("SELECT * FROM ModifierArguments WHERE ModifierId = 'COMMUNICATIONS_OFFICE_GOVERNOR_IDENTITY_PER_TITLE'")
    for r in cursor.fetchall():
        f.write(f"  Full row({len(r)} cols): {r}\n")

    # Check if COMMUNICATIONS_OFFICE has proper argument for Amount
    f.write("\n=== Direct check COMMUNICATIONS_OFFICE modifier ===\n")
    cursor.execute("SELECT * FROM Modifiers WHERE ModifierId = 'COMMUNICATIONS_OFFICE_GOVERNOR_IDENTITY_PER_TITLE'")
    for r in cursor.fetchall():
        f.write(f"  Modifier: {r}\n")

    # 5. EFFECT_ADJUST_CITY_TOKENS_GRANTED - check the instance
    f.write("\n=== EFFECT_ADJUST_CITY_TOKENS_GRANTED instance ===\n")
    cursor.execute("SELECT ModifierId FROM Modifiers WHERE ModifierType = 'MODIFIER_GOVERNOR_ADJUST_CITY_ENVOYS'")
    for r in cursor.fetchall():
        mid = r[0]
        f.write(f"  {mid}\n")
        cursor.execute("SELECT Name, Value FROM ModifierArguments WHERE ModifierId = ?", (mid,))
        for a in cursor.fetchall():
            f.write(f"    Arg: {a[0]} = {a[1]}\n")
        cursor.execute("SELECT gpm.GovernorPromotionType FROM GovernorPromotionModifiers gpm WHERE gpm.ModifierId = ?", (mid,))
        for gp in cursor.fetchall():
            f.write(f"    GovernorPromotion: {gp[0]}\n")

    # 6. EFFECT_GOVERNOR_ADJUST_CITY_TOKENS_GRANTED_MODIFIER
    f.write("\n=== EFFECT_GOVERNOR_ADJUST_CITY_TOKENS_GRANTED_MODIFIER instance ===\n")
    cursor.execute("SELECT ModifierId FROM Modifiers WHERE ModifierType = 'MODIFIER_GOVERNOR_ADJUST_CITY_ENVOYS_MODIFIER'")
    for r in cursor.fetchall():
        mid = r[0]
        f.write(f"  {mid}\n")
        cursor.execute("SELECT Name, Value FROM ModifierArguments WHERE ModifierId = ?", (mid,))
        for a in cursor.fetchall():
            f.write(f"    Arg: {a[0]} = {a[1]}\n")
        cursor.execute("SELECT gpm.GovernorPromotionType FROM GovernorPromotionModifiers gpm WHERE gpm.ModifierId = ?", (mid,))
        for gp in cursor.fetchall():
            f.write(f"    GovernorPromotion: {gp[0]}\n")

    # 7. Look up Chinese text for these envoy-related promotions
    text_conn = sqlite3.connect(local_db)
    tc = text_conn.cursor()
    f.write("\n=== Chinese text for AMBASSADOR_ENVOY-related promotions ===\n")
    tc.execute("SELECT Tag, Text FROM LocalizedText WHERE Tag LIKE '%AMBASSADOR_ENVOY%' AND Language='zh_Hans_CN'")
    for tag, text in tc.fetchall():
        f.write(f"  {tag}: {text}\n")
    tc.execute("SELECT Tag, Text FROM LocalizedText WHERE Tag LIKE '%CARDINAL_ENVOY%' AND Language='zh_Hans_CN'")
    for tag, text in tc.fetchall():
        f.write(f"  {tag}: {text}\n")

    # 8. Check all governor promotions from CARDINAL governor
    f.write("\n=== CARDINAL governor promotions ===\n")
    tc.execute("SELECT Tag, Text FROM LocalizedText WHERE Tag LIKE 'LOC_GOVERNOR_PROMOTION_CARDINAL_%_NAME' AND Language='zh_Hans_CN'")
    for tag, text in tc.fetchall():
        f.write(f"  {tag}: {text}\n")

    text_conn.close()
    conn.close()

print("Output written to _trace_result6.txt")
