"""
Erstellt die ideen.xlsx mit beiden Sheets und Beispieldaten.
Einmalig ausführen: python setup_excel.py
"""
import pandas as pd
from openpyxl import load_workbook

# --- Sheet 1: Produktionsplan ---
produktionsplan = pd.DataFrame([
    {
        "Projekt_ID": "PROJ_001",
        "Haupt_Subjekt": "Feuerdrache",
        "Thema": "Revierkampf zweier Alphadrachen in den vulkanischen Highlands",
        "Stil_Tonalität": "Discovery Channel, düster, cineastisch, dramatisch",
        "Gesamtdauer": 60,
        "Sprache": "Deutsch",
        "Status": None,
    },
    {
        "Projekt_ID": "PROJ_002",
        "Haupt_Subjekt": "Arkani",
        "Thema": "Jagdverhalten eines Rudels in der sibirischen Tundra",
        "Stil_Tonalität": "National Geographic, episch, ruhig, wissenschaftlich",
        "Gesamtdauer": 30,
        "Sprache": "Deutsch",
        "Status": None,
    },
    {
        "Projekt_ID": "PROJ_003",
        "Haupt_Subjekt": "T-Rex",
        "Thema": "Ein T-Rex überquert eine moderne Großstadt bei Nacht",
        "Stil_Tonalität": "BBC Earth, thriller, cinematisch, urban",
        "Gesamtdauer": 42,
        "Sprache": "Englisch",
        "Status": None,
    },
])

# --- Sheet 2: Charakter_Datenbank ---
charakter_db = pd.DataFrame([
    {
        "Haupt_Subjekt": "Feuerdrache",
        "Master_Prompt": (
            "massive western dragon, obsidian-black scales with ember-orange underbelly, "
            "four powerful legs, two enormous bat-like wings with red membrane, "
            "long spiked tail, glowing amber eyes, smoke trails from nostrils, "
            "scarred battle-worn hide, horns swept backwards"
        ),
        "Master_Image_ID": None,
    },
    {
        "Haupt_Subjekt": "Arkani",
        "Master_Prompt": (
            "Arcanine, large wolf-dog creature, cream and orange fur with black tiger stripes, "
            "thick bushy mane around neck and chest, amber eyes, powerful muscular build, "
            "large padded paws, fluffy tail with cream tip, noble and fierce expression"
        ),
        "Master_Image_ID": None,
    },
])

with pd.ExcelWriter("ideen.xlsx", engine="openpyxl") as writer:
    produktionsplan.to_excel(writer, sheet_name="Produktionsplan", index=False)
    charakter_db.to_excel(writer, sheet_name="Charakter_Datenbank", index=False)

print("✓ ideen.xlsx erfolgreich erstellt.")
print(f"  Produktionsplan: {len(produktionsplan)} Projekte")
print(f"  Charakter_Datenbank: {len(charakter_db)} Einträge")
