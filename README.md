# Fake-Dokumentations-Pipeline

Vollautomatisierte KI-Pipeline für cineastische Fake-Dokumentationen.

## Setup

```bash
pip install pandas openpyxl groq requests

# Excel mit Beispieldaten erstellen (einmalig)
python setup_excel.py

# Pipeline starten
python main.py
```

## Verzeichnisstruktur

```
fd1/
├── ideen.xlsx              ← Produktionsplan + Charakter_Datenbank
├── assets/
│   ├── Feuerdrache.png     ← Optionales Masterbild (verhindert Charakter-Drift)
│   └── Arkani.png
├── Projekte/
│   └── PROJ_001/
│       ├── regieplan_details.xlsx
│       └── bilder/
│           ├── szene_0_frame.jpg
│           ├── szene_1_frame.jpg
│           └── ...
├── main.py
└── setup_excel.py
```

## ideen.xlsx — Sheet: Produktionsplan

| Spalte | Beschreibung |
|---|---|
| `Projekt_ID` | Eindeutige ID, z. B. `PROJ_001` |
| `Haupt_Subjekt` | Das Hauptwesen, z. B. `Feuerdrache` |
| `Thema` | Die Handlung der Doku |
| `Stil_Tonalität` | z. B. `Discovery Channel, düster, cineastisch` |
| `Gesamtdauer` | In Sekunden (z. B. `60`) |
| `Sprache` | `Deutsch` oder `Englisch` |
| `Status` | Leer = offen, `Abgeschlossen`, `Fehler (teilweise)` |

## ideen.xlsx — Sheet: Charakter_Datenbank

| Spalte | Beschreibung |
|---|---|
| `Haupt_Subjekt` | Muss mit Produktionsplan übereinstimmen |
| `Master_Prompt` | Anatomische DNA (Farben, Texturen, Merkmale) |
| `Master_Image_ID` | Leonardo-ID des Referenzbildes (auto-gesetzt) |

## Masterbild hinzufügen

Lege ein PNG/JPG unter `assets/{Haupt_Subjekt}.png` ab, bevor du die Pipeline startest.  
Beim ersten Lauf wird das Bild zu Leonardo hochgeladen und die ID in der Datenbank gespeichert.  
Bei allen Folge-Projekten mit demselben Subjekt wird automatisch diese Referenz genutzt.

## Szenenberechnung

```
Anzahl Szenen = ceil(Gesamtdauer / 6 Sekunden)
+ 1 Startframe (Szene 0, kein Voiceover/Movement)
```
