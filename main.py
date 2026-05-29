"""
Fake-Dokumentations-Pipeline
Erstellt vollautomatisch cineastische Fake-Dokumentationen (Bilder + Regieplan).
"""

import json
import math
import os
import time

import pandas as pd
import requests
from groq import Groq

# ---------------------------------------------------------------------------
# KONFIGURATION
# ---------------------------------------------------------------------------

LEONARDO_API_KEY = "f291c7d8-71df-4a47-9c51-c023553ad98e"
GROQ_API_KEY     = "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"
EXCEL_PATH       = "ideen.xlsx"
ASSETS_DIR       = "assets"

# Leonardo Vision XL  (stabil für organische Charaktere)
LEO_MODEL_ID = "6bef9f1b-29cb-40c7-b9df-32b51c1f67d3"

# Sekunden pro Szene (Basis für Szenenberechnung)
SECONDS_PER_SCENE = 6

# Wie viele Wörter passen in eine 6-Sekunden-Szene (ca. 2.5 W/s)
WORDS_PER_SCENE = int(SECONDS_PER_SCENE * 2.5)

# Character Reference Gewicht (0.0 = frei, 1.0 = Pixel-Kopie)
CHARACTER_REF_WEIGHT = 0.85

# Maximale Retry-Versuche für Leonardo + Wartezeit in Sekunden
MAX_RETRIES   = 3
RETRY_WAIT    = 5

# ---------------------------------------------------------------------------

client_groq = Groq(api_key=GROQ_API_KEY)

HEADERS_LEO = {
    "accept":        "application/json",
    "content-type":  "application/json",
    "authorization": f"Bearer {LEONARDO_API_KEY}",
}


# ---------------------------------------------------------------------------
# HILFSFUNKTIONEN
# ---------------------------------------------------------------------------

def upload_master_image(file_path: str) -> str | None:
    """
    Lädt ein lokales Masterbild zu Leonardo hoch (S3-Presigned-URL).
    Gibt die Leonardo-Image-ID zurück oder None bei Fehler.
    """
    if not os.path.exists(file_path):
        print(f"[WARN] Masterbild nicht gefunden: {file_path}")
        return None

    print(f"[UPLOAD] Lade Masterbild hoch: {file_path}")

    try:
        resp = requests.post(
            "https://cloud.leonardo.ai/api/rest/v1/init-image",
            json={"extension": os.path.splitext(file_path)[1].lstrip(".")},
            headers=HEADERS_LEO,
            timeout=30,
        )
        resp.raise_for_status()
        res = resp.json()

        if "uploadInitImage" not in res:
            print(f"[ERROR] Upload-Init fehlgeschlagen: {res}")
            return None

        init_data  = res["uploadInitImage"]
        fields     = init_data["fields"]
        upload_url = init_data["url"]
        image_id   = init_data["id"]

        # fields kann als JSON-String ankommen
        if isinstance(fields, str):
            fields = json.loads(fields)

        ext = os.path.splitext(file_path)[1].lower()
        mime = "image/png" if ext == ".png" else "image/jpeg"

        with open(file_path, "rb") as fh:
            s3_resp = requests.post(
                upload_url,
                data=fields,
                files={"file": (os.path.basename(file_path), fh, mime)},
                timeout=60,
            )

        if s3_resp.status_code != 204:
            print(f"[ERROR] S3-Upload fehlgeschlagen (HTTP {s3_resp.status_code})")
            return None

        print(f"[UPLOAD] Masterbild hochgeladen → ID: {image_id}")
        return image_id

    except Exception as exc:
        print(f"[ERROR] Upload-Exception: {exc}")
        return None


def _build_generation_payload(prompt: str, master_image_id: str | None) -> dict:
    """Baut den Leonardo-API-Payload zusammen."""
    payload: dict = {
        "height":      768,
        "width":       1360,
        "prompt":      prompt,
        "num_images":  1,
        "modelId":     LEO_MODEL_ID,
        "presetStyle": "CINEMATIC",
        "public":      False,
    }

    if master_image_id:
        # Character Reference: behält Aussehen, erlaubt neue Posen
        payload["controlNet"]         = True
        payload["controlNetType"]     = "CHARACTER_REFERENCE"
        payload["imagePrompts"]       = [master_image_id]
        payload["imagePromptWeight"]  = CHARACTER_REF_WEIGHT

    return payload


def leonardo_generate(prompt: str, master_image_id: str | None = None) -> tuple[str | None, str | None]:
    """
    Generiert ein Bild via Leonardo.ai.
    Gibt (image_url, image_id) zurück oder (None, None) bei Fehler.
    Beinhaltet Polling bis COMPLETE oder FAILED.
    """
    url = "https://cloud.leonardo.ai/api/rest/v1/generations"
    payload = _build_generation_payload(prompt, master_image_id)

    try:
        resp = requests.post(url, json=payload, headers=HEADERS_LEO, timeout=30)
        resp.raise_for_status()
        res_data = resp.json()
    except Exception as exc:
        print(f"[ERROR] Leonardo POST Exception: {exc}")
        return None, None

    if "sdGenerationJob" not in res_data:
        print(f"[ERROR] Leonardo Antwort ohne generationId: {res_data}")
        return None, None

    gen_id = res_data["sdGenerationJob"]["generationId"]
    poll_url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}"

    print(f"   [POLL] Warte auf Generation {gen_id} ...")
    while True:
        time.sleep(5)
        try:
            check = requests.get(poll_url, headers=HEADERS_LEO, timeout=30).json()
            data  = check.get("generations_by_pk", {})
        except Exception as exc:
            print(f"   [WARN] Polling-Fehler: {exc} — retry ...")
            continue

        status = data.get("status")
        if status == "COMPLETE":
            imgs = data.get("generated_images", [])
            if imgs:
                return imgs[0]["url"], imgs[0]["id"]
            return None, None
        elif status == "FAILED":
            print("   [ERROR] Generation FAILED.")
            return None, None

        print("   ... Bild wird gerendert ...")


def generate_with_retry(
    prompt: str,
    master_image_id: str | None,
    scene_label: str,
) -> tuple[str | None, str | None]:
    """Wrapper um leonardo_generate mit bis zu MAX_RETRIES Versuchen."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            img_url, img_id = leonardo_generate(prompt, master_image_id)
            if img_url:
                return img_url, img_id
            print(f"   [RETRY {attempt}/{MAX_RETRIES}] Szene {scene_label}: kein Ergebnis.")
        except Exception as exc:
            print(f"   [RETRY {attempt}/{MAX_RETRIES}] Szene {scene_label}: Exception: {exc}")

        if attempt < MAX_RETRIES:
            print(f"   Warte {RETRY_WAIT}s ...")
            time.sleep(RETRY_WAIT)

    return None, None


# ---------------------------------------------------------------------------
# GROQ: REGIEPLAN GENERIEREN
# ---------------------------------------------------------------------------

def generate_regieplan(
    subjekt: str,
    thema: str,
    stil: str,
    dna: str,
    dauer: int,
    sprache: str,
) -> pd.DataFrame | None:
    """
    Lässt Groq einen vollständigen Regieplan als Markdown-Tabelle erstellen.
    Gibt ein DataFrame zurück oder None bei Fehler.
    """
    anzahl_szenen = math.ceil(dauer / SECONDS_PER_SCENE)

    prompt = f"""
Du bist ein erfahrener Dokumentarfilm-Regisseur und schreibst einen Regieplan für eine
Fake-Dokumentation im Stil von Discovery Channel / National Geographic.

PROJEKT-DETAILS:
- Hauptsubjekt: {subjekt}
- Thema / Handlung: {thema}
- Stil & Tonalität: {stil}
- Visuelle DNA (IMMER in Bildprompts nutzen): {dna}
- Gesamtdauer: {dauer} Sekunden → {anzahl_szenen} Szenen à {SECONDS_PER_SCENE} Sek. + 1 Startframe (Szene 0)
- Sprache: {sprache}

AUFGABE:
Erstelle eine Tabelle mit EXAKT {anzahl_szenen + 1} Zeilen (Szene 0 bis {anzahl_szenen}).

SPALTEN (getrennt durch '|'):
Szene | Voiceover_Text | Bild_Prompt_Ende | Video_Movement | Untertitel

DETAILLIERTE REGELN PRO SPALTE:

1. Szene
   - Fortlaufende Nummer: 0, 1, 2, ..., {anzahl_szenen}

2. Voiceover_Text
   - Wissenschaftlicher, epischer Sprecher-Text im Doku-Stil ({sprache})
   - Ca. {WORDS_PER_SCENE} Wörter pro Szene (passend zu {SECONDS_PER_SCENE} Sekunden)
   - Szene 0: "leer"

3. Bild_Prompt_Ende  ← STATISCHES STANDBILD AM ENDE DER SZENE
   - MUSS BEGINNEN MIT: "{subjekt}, {dna},"
   - Dann: exakte Pose (z. B. "Flügel im 45-Grad-Winkel gestreckt, Hinterbeine auf Felsvorsprung")
   - Kamerawinkel variieren: Close-up, Wide Shot, Low-Angle, Drone Shot, Side Profile
   - Licht & Atmosphäre passend zum Thema nennen (z. B. "golden hour backlight, volumetric fog")
   - KEINE Handlungssätze ("er rennt") → NUR statische Beschreibungen ("in rennender Pose, Beine abgehoben")
   - Das Subjekt MUSS min. 50% des Bildrahmens einnehmen
   - Bevorzuge Medium Shot oder Close-up für Gesichts-/Detailerhalt
   - KEIN Verschwinden im Nebel oder Distanz
   - Szene 0: Startframe des gesamten Videos (erste Pose)

4. Video_Movement  ← RUNWAY-PROMPT FÜR DIE BEWEGUNG ZWISCHEN START- UND ENDBILD
   - Kontinuität: Start dieser Szene = Ende der vorherigen Szene
   - Beschreibe: Kamerabewegung, Brennweite, Tiefenschärfe, Bewegungsablauf des Subjekts
   - Stil muss passen zu: {stil}
   - Formuliere als einen einzelnen, flüssigen Prompt in natürlicher Sprache
   - Szene 0: "leer"

5. Untertitel
   - Der exakte On-Screen-Text (identisch mit Voiceover_Text oder gekürzt für Social Media)
   - Szene 0: "leer"

KREATIVE VORGABEN:
- Die Handlung muss "{thema}" chronologisch und spannend erzählen
- Jede Szene baut logisch auf der vorherigen auf (Kontinuität!)
- Wissenschaftliche Fachbegriffe einsetzen (Anatomie, Verhalten, Ökologie)
- Ton: sachlich-ehrfürchtig, wie ein echter Naturdoku-Sprecher

WICHTIG: Antworte NUR mit der Markdown-Tabelle. Keine Einleitung, kein Schluss, keine Erklärungen.
"""

    try:
        chat = client_groq.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.8,
        )
        ki_output = chat.choices[0].message.content
    except Exception as exc:
        print(f"[ERROR] Groq Exception: {exc}")
        return None

    # Tabelle parsen
    lines = [
        l.strip()
        for l in ki_output.split("\n")
        if "|" in l and "---" not in l
    ]

    if not lines:
        print("[ERROR] Groq hat keine Tabelle zurückgegeben.")
        print("Raw output:", ki_output[:500])
        return None

    # Header-Zeile der KI überspringen, falls vorhanden
    if lines and any(kw in lines[0] for kw in ("Szene", "Scene", "szene")):
        lines = lines[1:]

    columns = ["Szene", "Voiceover_Text", "Bild_Prompt_Ende", "Video_Movement", "Untertitel"]
    rows = []
    for line in lines:
        parts = [cell.strip() for cell in line.split("|")]
        # Führende/trailing leere Zellen durch '|...|' entfernen
        parts = [p for p in parts if p]
        if len(parts) >= 5:
            rows.append(parts[:5])
        elif len(parts) > 0:
            # Auffüllen falls KI zu wenige Spalten liefert
            while len(parts) < 5:
                parts.append("leer")
            rows.append(parts[:5])

    if not rows:
        print("[ERROR] Konnte keine Zeilen aus der Tabelle parsen.")
        return None

    df = pd.DataFrame(rows, columns=columns)
    print(f"[GROQ] Regieplan erstellt: {len(df)} Szenen geparst.")
    return df


# ---------------------------------------------------------------------------
# HAUPT-PIPELINE
# ---------------------------------------------------------------------------

def run_full_automation() -> str:
    # ------------------------------------------------------------------
    # 0. Excel laden
    # ------------------------------------------------------------------
    if not os.path.exists(EXCEL_PATH):
        return f"[ABORT] {EXCEL_PATH} nicht gefunden. Bitte zuerst setup_excel.py ausführen."

    df_plan = pd.read_excel(EXCEL_PATH, sheet_name="Produktionsplan")
    df_db   = pd.read_excel(EXCEL_PATH, sheet_name="Charakter_Datenbank")

    # Dtype-Fix: verhindert LossySetitemError beim späteren Status-Setzen
    df_plan["Status"] = df_plan["Status"].astype(object)
    df_db["Master_Image_ID"] = df_db["Master_Image_ID"].astype(object)

    offene = df_plan[df_plan["Status"].isna()]
    if offene.empty:
        return "[DONE] Keine offenen Projekte im Produktionsplan."

    idx = offene.index[0]
    p   = offene.iloc[0]

    proj_id  = str(p["Projekt_ID"])
    subjekt  = str(p["Haupt_Subjekt"])
    thema    = str(p["Thema"])
    stil     = str(p["Stil_Tonalität"])
    dauer    = int(p["Gesamtdauer"]) if pd.notna(p.get("Gesamtdauer")) else 30
    sprache  = str(p["Sprache"]) if pd.notna(p.get("Sprache")) else "Deutsch"

    print(f"\n{'='*60}")
    print(f"  PROJEKT: {proj_id}  |  SUBJEKT: {subjekt}")
    print(f"  THEMA:   {thema}")
    print(f"  STIL:    {stil}")
    print(f"  DAUER:   {dauer}s  |  SPRACHE: {sprache}")
    print(f"{'='*60}\n")

    # ------------------------------------------------------------------
    # 1. Charakter-DNA aus Datenbank laden oder Fehler melden
    # ------------------------------------------------------------------
    db_match = df_db[df_db["Haupt_Subjekt"] == subjekt]

    if db_match.empty:
        return (
            f"[ABORT] '{subjekt}' nicht in Charakter_Datenbank gefunden.\n"
            f"Bitte Eintrag in Sheet 'Charakter_Datenbank' anlegen."
        )

    db_row       = db_match.iloc[0]
    db_idx       = db_match.index[0]
    dna          = str(db_row["Master_Prompt"])
    master_img_id: str | None = (
        str(db_row["Master_Image_ID"])
        if pd.notna(db_row.get("Master_Image_ID")) and str(db_row.get("Master_Image_ID", "")).strip()
        else None
    )

    print(f"[DNA] Charakter-DNA geladen für '{subjekt}'.")

    # ------------------------------------------------------------------
    # 2. Masterbild hochladen (falls noch keine ID in DB)
    # ------------------------------------------------------------------
    if not master_img_id:
        # Suche nach einem lokalen Masterbild in assets/
        candidates = [
            os.path.join(ASSETS_DIR, f"{subjekt}.png"),
            os.path.join(ASSETS_DIR, f"{subjekt}.jpg"),
            os.path.join(ASSETS_DIR, f"{subjekt.lower()}.png"),
            os.path.join(ASSETS_DIR, f"{subjekt.lower()}.jpg"),
        ]
        local_master = next((c for c in candidates if os.path.exists(c)), None)

        if local_master:
            master_img_id = upload_master_image(local_master)
            if master_img_id:
                # ID in Datenbank persistieren
                df_db.at[db_idx, "Master_Image_ID"] = master_img_id
                print(f"[DB] Master_Image_ID gespeichert: {master_img_id}")
        else:
            print(
                f"[INFO] Kein lokales Masterbild in '{ASSETS_DIR}/' gefunden.\n"
                f"       Tipp: Lege '{ASSETS_DIR}/{subjekt}.png' ab, um Charakter-Drift zu verhindern.\n"
                f"       Fahre ohne Character-Reference fort (erste Generierung wird das neue Master)."
            )

    # ------------------------------------------------------------------
    # 3. Ordnerstruktur anlegen
    # ------------------------------------------------------------------
    base_folder  = os.path.join("Projekte", proj_id)
    bilder_folder = os.path.join(base_folder, "bilder")
    os.makedirs(bilder_folder, exist_ok=True)

    # ------------------------------------------------------------------
    # 4. Regieplan via Groq erstellen
    # ------------------------------------------------------------------
    print(f"\n[GROQ] Erstelle Regieplan ({math.ceil(dauer / SECONDS_PER_SCENE)} Szenen + Szene 0) ...")
    df_regie = generate_regieplan(subjekt, thema, stil, dna, dauer, sprache)

    if df_regie is None:
        return "[ABORT] Regieplan konnte nicht erstellt werden."

    regie_path = os.path.join(base_folder, "regieplan_details.xlsx")
    df_regie.to_excel(regie_path, index=False)
    print(f"[SAVE] Regieplan gespeichert: {regie_path}")

    # ------------------------------------------------------------------
    # 5. Bilder generieren
    # ------------------------------------------------------------------
    print(f"\n[LEO] Starte Bildgenerierung für {len(df_regie)} Szenen ...")
    alle_bilder_ok = True
    first_generated_id: str | None = None  # Für späteres Master-Update

    for _, scene in df_regie.iterrows():
        szene_nr    = str(scene["Szene"])
        bild_prompt = str(scene["Bild_Prompt_Ende"])

        if not bild_prompt or bild_prompt.lower() in ("leer", "nan", ""):
            print(f"[SKIP] Szene {szene_nr}: kein Bildprompt vorhanden.")
            continue

        print(f"\n[SCENE {szene_nr}] Generiere Bild ...")
        print(f"   Prompt: {bild_prompt[:120]}{'...' if len(bild_prompt) > 120 else ''}")

        # Prompt zusammensetzen: DNA ist bereits im Bild_Prompt_Ende (durch Groq),
        # wir fügen technische Qualitäts-Tags hinzu.
        full_prompt = (
            f"DOCUMENTARY SHOT: {bild_prompt}, "
            "highly detailed, photorealistic, 8k, cinematic lighting, "
            "nature documentary style, sharp focus"
        )

        img_url, img_id = generate_with_retry(
            prompt=full_prompt,
            master_image_id=master_img_id,
            scene_label=szene_nr,
        )

        if img_url:
            filename  = f"szene_{szene_nr}_frame.jpg"
            save_path = os.path.join(bilder_folder, filename)

            try:
                img_data = requests.get(img_url, timeout=60).content
                with open(save_path, "wb") as fh:
                    fh.write(img_data)
                print(f"   [OK] {filename} gespeichert ({len(img_data) // 1024} KB).")
            except Exception as exc:
                print(f"   [ERROR] Bild konnte nicht gespeichert werden: {exc}")
                alle_bilder_ok = False
                continue

            # Erstes erfolgreich generiertes Bild als potentielles neues Master merken
            if first_generated_id is None and img_id:
                first_generated_id = img_id

            time.sleep(2)  # Rate-Limit-Puffer
        else:
            print(f"   [FAIL] Szene {szene_nr}: Nach {MAX_RETRIES} Versuchen kein Bild.")
            alle_bilder_ok = False

    # ------------------------------------------------------------------
    # 6. Falls noch kein Master-Image in DB → erstes generiertes Bild eintragen
    # ------------------------------------------------------------------
    if not master_img_id and first_generated_id:
        df_db.at[db_idx, "Master_Image_ID"] = first_generated_id
        print(f"\n[DB] Neues Master_Image_ID gesetzt: {first_generated_id}")

    # ------------------------------------------------------------------
    # 7. Status-Update nur bei vollständigem Erfolg
    # ------------------------------------------------------------------
    if alle_bilder_ok:
        df_plan.at[idx, "Status"] = "Abgeschlossen"
        status_msg = "Abgeschlossen"
    else:
        df_plan.at[idx, "Status"] = "Fehler (teilweise)"
        status_msg = "Fehler (teilweise)"

    # Excel speichern (beide Sheets)
    with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl") as writer:
        df_plan.to_excel(writer, sheet_name="Produktionsplan", index=False)
        df_db.to_excel(writer, sheet_name="Charakter_Datenbank", index=False)

    print(f"\n[SAVE] {EXCEL_PATH} aktualisiert → Status: {status_msg}")

    return (
        f"\n{'='*60}\n"
        f"  {'ERFOLG' if alle_bilder_ok else 'TEILWEISE ERFOLG'}: Projekt {proj_id}\n"
        f"  Status: {status_msg}\n"
        f"  Bilder: {bilder_folder}/\n"
        f"  Regieplan: {regie_path}\n"
        f"{'='*60}"
    )


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(run_full_automation())
