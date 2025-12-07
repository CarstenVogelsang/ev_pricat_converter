# PRD POC (Proof of Concept / MVP)

## pricat-converter

**Version:** 1.0  
**Datum:** 2025-01-03  
**Status:** Draft

---

## 1. Zielsetzung

Das POC demonstriert die Kernfunktionalität des pricat-converters:

> **Eine VEDES PRICAT-Datei eines Lieferanten einlesen, in das Elena-Format konvertieren, Bilder herunterladen und das Paket auf den Ziel-FTP hochladen.**

### 1.1 Erfolgs-Kriterien

- [ ] Lieferanten aus DB anzeigen
- [ ] PRICAT-Datei von VEDES-FTP herunterladen
- [ ] PRICAT parsen und Lieferant/Hersteller/Marken in DB speichern
- [ ] Elena-CSV generieren
- [ ] Bilder parallel herunterladen
- [ ] XLSX mit Entitäten erstellen
- [ ] Alles auf Ziel-FTP hochladen
- [ ] Elena-Import triggern

---

## 2. Scope

### 2.1 In Scope (POC)

| Feature                          | Beschreibung                                    |
|----------------------------------|-------------------------------------------------|
| Minimales Web-UI                 | Liste aktiver Lieferanten + "Verarbeite"-Button |
| DB-Verwaltung                    | SQLite mit Lieferant, Hersteller, Marke, Config |
| PRICAT-Download                  | Von VEDES-FTP                                   |
| PRICAT-Parsing                   | Alle 143 Spalten, Mapping auf Elena-Felder      |
| Entitäten-Extraktion             | Lieferant, Hersteller, Marken → DB              |
| Elena-CSV-Export                 | Gemäß mapping.php Format                        |
| Bild-Download                    | Async/parallel von HTTPS-URLs                   |
| XLSX-Export                      | Lieferant/Hersteller/Marken mit GLN             |
| FTP-Upload                       | Elena-CSV + Bilder auf Ziel-FTP                 |
| Import-Trigger                   | HTTP-GET auf getData.php                        |

### 2.2 Out of Scope (POC)

- Benutzer-Authentifizierung
- Automatische Scheduler
- Fehler-Recovery / Rollback
- Detaillierte Fortschrittsanzeige
- Artikel-Vorschau/Bearbeitung
- Mehrere parallele Verarbeitungen
- Logging-Dashboard
- API-Endpoints

---

## 3. User Stories

### US-01: Lieferanten anzeigen
**Als** Anwender  
**möchte ich** alle aktiven Lieferanten sehen  
**damit** ich einen zur Verarbeitung auswählen kann.

**Akzeptanzkriterien:**
- Liste zeigt: Kurzbezeichnung, VEDES-ID, GLN, letzte Konvertierung
- Nur aktive Lieferanten werden angezeigt
- "Verarbeite"-Button pro Lieferant

---

### US-02: Verarbeitung starten
**Als** Anwender  
**möchte ich** die Verarbeitung für einen Lieferanten starten  
**damit** dessen PRICAT-Daten konvertiert werden.

**Akzeptanzkriterien:**
- Klick auf "Verarbeite" startet den Prozess
- UI zeigt Fortschritt/Status
- Bei Erfolg: Erfolgsmeldung mit Details
- Bei Fehler: Fehlermeldung mit Ursache

---

### US-03: Entitäten in DB speichern
**Als** System  
**möchte ich** Lieferant, Hersteller und Marken aus der PRICAT extrahieren  
**damit** diese Stammdaten verfügbar sind.

**Akzeptanzkriterien:**
- Lieferant wird aus Spalten 26-28 extrahiert (GLN, ID, Name)
- Hersteller werden aus Spalten 30-32 extrahiert
- Marken werden aus Spalte 52 extrahiert
- GLN_evendo für Marken: `{Hersteller.GLN}_{laufende_nummer}`
- Duplikate werden per UPSERT behandelt

---

### US-04: Elena-CSV generieren
**Als** System  
**möchte ich** die PRICAT-Daten in eine Elena-CSV transformieren  
**damit** der Elena-Import diese verarbeiten kann.

**Akzeptanzkriterien:**
- CSV-Format gemäß mapping.php
- Delimiter: Semikolon
- Encoding: UTF-8
- Alle gemappten Felder korrekt befüllt

---

### US-05: Bilder herunterladen
**Als** System  
**möchte ich** alle Artikelbilder herunterladen  
**damit** diese mit der Elena-CSV hochgeladen werden.

**Akzeptanzkriterien:**
- Bilder aus Spalte 95 (Bilderlink) extrahieren
- Paralleler Download (max. 5 gleichzeitig)
- Speicherung in `data/images/{vedes_id}_{kurzname}/`
- Fehlgeschlagene Downloads werden geloggt aber übersprungen

---

### US-06: XLSX-Export
**Als** Anwender  
**möchte ich** eine XLSX-Datei mit Lieferant/Hersteller/Marken erhalten  
**damit** ich die Stammdaten prüfen kann.

**Akzeptanzkriterien:**
- XLSX mit Spalten: Typ, Kurzbezeichnung, GLN
- Enthält: 1 Lieferant, n Hersteller, n Marken
- Dateiname: `entities_{vedes_id}_{timestamp}.xlsx`

---

### US-07: FTP-Upload
**Als** System  
**möchte ich** die generierten Dateien auf den Ziel-FTP hochladen  
**damit** der Elena-Import sie verarbeiten kann.

**Akzeptanzkriterien:**
- Elena-CSV wird hochgeladen
- Bilder werden in images/-Unterordner hochgeladen
- Zielverzeichnis: `/{startdir}/`

---

### US-08: Import auslösen
**Als** System  
**möchte ich** den Elena-Import per HTTP-Request starten  
**damit** die Daten automatisch importiert werden.

**Akzeptanzkriterien:**
- HTTP-GET auf: `{base_url}/importer/getData.php?startdir={startdir}&importfile={filename}&debuglevel=1`
- Response wird geloggt
- Status wird im UI angezeigt

---

## 4. Technische Details

### 4.1 Datenbank-Initialisierung

```python
# Initiale Config-Einträge
CONFIG_DEFAULTS = [
    ('vedes_ftp_host', 'ftp.vedes.de', 'VEDES FTP Server'),
    ('vedes_ftp_user', '', 'VEDES FTP Benutzer'),
    ('vedes_ftp_pass', '', 'VEDES FTP Passwort (verschlüsselt)'),
    ('vedes_ftp_basepath', '/pricat/', 'Basispfad PRICAT-Dateien'),
    ('elena_ftp_host', '', 'Ziel-FTP Server'),
    ('elena_ftp_user', '', 'Ziel-FTP Benutzer'),
    ('elena_ftp_pass', '', 'Ziel-FTP Passwort (verschlüsselt)'),
    ('image_download_threads', '5', 'Parallele Bild-Downloads'),
    ('image_timeout', '30', 'Timeout Bild-Download in Sekunden'),
]
```

### 4.2 PRICAT-Spalten-Mapping (Index 0-basiert)

```python
PRICAT_COLUMNS = {
    # Zeilen-Identifikation
    'record_type': 0,           # H oder P
    'message_type': 1,          # PRICAT
    
    # Artikel-Grunddaten
    'vedes_artikelnummer': 5,   # VedesArtikelnummer
    'ean': 9,                   # EANUPC
    'artikelbezeichnung': 12,   # Artikelbezeichnung
    'artbez_prefix': 11,        # Artbez_Prefix
    'artbez_suffix': 13,        # Artbez_Suffix
    
    # Lieferant
    'lieferant_gln': 25,        # LieferantGLN
    'lieferant_id': 26,         # LieferantID
    'lieferant_name': 27,       # Lieferantname
    'lieferant_artikelnr': 28,  # ArtikelnummerDesLieferanten
    
    # Hersteller
    'hersteller_gln': 29,       # HerstellerGLN
    'hersteller_id': 30,        # HerstellerID
    'hersteller_name': 31,      # Herstellername
    'hersteller_artikelnr': 32, # ArtikelnummerDesHerstellers
    
    # Preise
    'uvpe': 33,                 # UVPE
    'gnp_lieferant': 34,        # GNP_Lieferant (EK-Preis)
    'mwst': 38,                 # MWST
    
    # Marke
    'marke_text': 51,           # MarkeText
    
    # Maße/Gewicht
    'gewicht': 63,              # Gewicht
    'gewicht_einheit': 64,      # Gewichtseinheit
    
    # Bilder & Texte
    'bilderlink': 94,           # Bilderlink
    'grunddatentext': 96,       # Grunddatentext
    'warnhinweise': 99,         # Warnhinweise
    
    # Inhalt/Grundpreis
    'inhalt': 123,              # Inhalt
    'inhalt_einheit': 124,      # Inhalt_Einheit
}
```

### 4.3 Elena-CSV Spalten

```python
ELENA_COLUMNS = [
    'Artikelnummer',
    'MPN',
    'GTIN/EAN',
    'Kurzbezeichnung',
    'Verkaufspreis',
    'Grundnettopreis',
    'Lieferant',
    'Lie-GLN',
    'Hersteller',
    'Hersteller-GLN',
    'Marke',
    'Bez-Lang',
    'MWST',
    'Gewicht',
    'PA-Einheit',
    'PA-Inhalt',
    'Herkunftsland',
    'Zolltarifnummer',
    'Name Bild 1',
    'Name Bild 2',
    'Name Bild 3',
    # ... weitere nach Bedarf
]
```

### 4.4 Marke GLN_evendo Generierung

```python
def generate_gln_evendo(hersteller: Hersteller, marke_name: str) -> str:
    """
    Generiert eindeutige GLN für Marke.
    Format: {Hersteller.GLN}_{laufende_nummer}
    
    Beispiel: 4023017000005_1, 4023017000005_2
    """
    existing_marken = Marke.query.filter_by(hersteller_id=hersteller.id).count()
    nummer = existing_marken + 1
    return f"{hersteller.gln}_{nummer}"
```

---

## 5. UI-Mockup

### 5.1 Hauptseite (Lieferanten-Liste)

```
┌─────────────────────────────────────────────────────────────────────┐
│  pricat-converter                                        [Einstellungen]
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Aktive Lieferanten                                                 │
│  ─────────────────                                                  │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ Kurzbezeichnung      │ VEDES-ID   │ GLN           │ Letzte    │  │
│  │                      │            │               │ Konvert.  │  │
│  ├──────────────────────┼────────────┼───────────────┼───────────┤  │
│  │ LEGO Spielwaren GmbH │ 0000001872 │ 4023017000005 │ 02.01.25  │  │
│  │                                                   [Verarbeite]│  │
│  ├──────────────────────┼────────────┼───────────────┼───────────┤  │
│  │ Ravensburger         │ 0000001745 │ 4005556000005 │ -         │  │
│  │                                                   [Verarbeite]│  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Verarbeitungs-Status

```
┌─────────────────────────────────────────────────────────────────────┐
│  Verarbeitung: LEGO Spielwaren GmbH                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Status: ██████████████████░░░░░░░░░░░░ 60%                         │
│                                                                     │
│  ✓ PRICAT heruntergeladen (953 Artikel)                             │
│  ✓ Lieferant/Hersteller/Marken extrahiert                           │
│  ⟳ Bilder werden heruntergeladen... (234/389)                       │
│  ○ Elena-CSV generieren                                             │
│  ○ XLSX erstellen                                                   │
│  ○ FTP-Upload                                                       │
│  ○ Import starten                                                   │
│                                                                     │
│                                              [Abbrechen] [Schließen]│
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Ablauf (Sequenzdiagramm)

```
User          UI            Backend         VEDES-FTP    Ziel-FTP    Elena
 │             │               │                │            │          │
 │──Verarbeite─▶│               │                │            │          │
 │             │───Start───────▶│                │            │          │
 │             │               │───Download─────▶│            │          │
 │             │               │◀──PRICAT.csv───│            │          │
 │             │               │                │            │          │
 │             │               │ Parse PRICAT   │            │          │
 │             │               │ Extract Entities            │          │
 │             │               │ Save to DB     │            │          │
 │             │               │                │            │          │
 │             │               │ Download Images (async)     │          │
 │             │               │                │            │          │
 │             │               │ Generate Elena CSV          │          │
 │             │               │ Generate XLSX  │            │          │
 │             │               │                │            │          │
 │             │               │───Upload───────────────────▶│          │
 │             │               │◀──OK──────────────────────│          │
 │             │               │                │            │          │
 │             │               │───GET getData.php──────────────────────▶│
 │             │               │◀──Response─────────────────────────────│
 │             │               │                │            │          │
 │             │◀──Fertig──────│                │            │          │
 │◀──Anzeige───│               │                │            │          │
```

---

## 7. Testdaten

### 7.1 Test-Lieferant (DB-Seed)

```sql
INSERT INTO lieferant (gln, vedes_id, kurzbezeichnung, aktiv, ftp_pfad_quelle, elena_startdir, elena_base_url)
VALUES (
    '4023017000005',
    '0000001872', 
    'LEGO Spielwaren GmbH',
    1,
    '/pricat/pricat_1872_Lego_Spielwaren_GmbH_0.csv',
    'lego',
    'https://direct.e-vendo.de'
);
```

### 7.2 Test-PRICAT

Datei: `pricat_1872_Lego_Spielwaren_GmbH_0.csv` (953 Artikel)

---

## 8. Risiken & Mitigations

| Risiko                              | Wahrscheinlichkeit | Impact | Mitigation                          |
|-------------------------------------|--------------------|--------|-------------------------------------|
| VEDES-FTP nicht erreichbar          | Mittel             | Hoch   | Manuelle Datei-Upload-Option        |
| Bild-Server langsam/überlastet      | Hoch               | Mittel | Timeout + Skip fehlgeschlagener     |
| PRICAT-Format ändert sich           | Niedrig            | Hoch   | Spalten-Mapping konfigurierbar      |
| Große Dateien (>10k Artikel)        | Mittel             | Mittel | Batch-Verarbeitung, Streaming       |

---

## 9. Offene Fragen

1. **FTP-Zugangsdaten:** Wie werden diese initial eingetragen? (UI oder SQL?)
2. **Mehrere Bilder:** Hat ein Artikel mehrere Bild-URLs? (Nur Spalte 95 oder weitere?)
3. **Error-Handling:** Was passiert bei Teil-Fehlern (z.B. 10% Bilder fehlgeschlagen)?
4. **Datei-Namenskonvention:** Wie soll die Elena-CSV benannt werden?

---

## 10. Nächste Schritte

1. [ ] Projektstruktur anlegen
2. [ ] SQLAlchemy Models implementieren
3. [ ] DB-Migration + Seed-Daten
4. [ ] PRICAT-Parser implementieren
5. [ ] Elena-Exporter implementieren
6. [ ] Image-Downloader implementieren
7. [ ] FTP-Service implementieren
8. [ ] Flask-Routes + Templates
9. [ ] Integration-Test mit Testdaten
10. [ ] Deployment-Dokumentation
