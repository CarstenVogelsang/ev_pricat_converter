# Modul PRICAT Converter

Konvertiert VEDES PRICAT-Dateien (Lieferanten-Produktdaten) in das Elena-Importformat für e-vendo Systeme.

```
VEDES FTP (PRICAT CSV) → pricat-converter → Ziel-FTP (Elena CSV + Bilder) → Elena Import (getData.php)
```

## Task-Übersicht

| # | Task | Status | Beschreibung |
|---|------|--------|--------------|
| 1 | FTP Port-Konfiguration | ✅ Erledigt | Separate Port-Config für VEDES und Elena FTP |
| 2 | Admin-Seite | ✅ Erledigt | Admin-Panel mit FTP-Tests und Health-Checks |
| 3 | Benutzer-Authentifizierung | ✅ Erledigt | Flask-Login mit Admin/Sachbearbeiter-Rollen |
| 4 | VEDES_ID ohne Nullen | ✅ Erledigt | Führende Nullen aus VEDES_ID entfernen |
| 5 | Lieferanten-Sync | ✅ Erledigt | FTP-Scan und automatische Lieferanten-Anlage |
| 6 | Base64-Passwörter | ✅ Erledigt | FileZilla-kompatible Base64-Passwörter in Config |
| 7 | Lieferanten-Filter | ✅ Erledigt | Filter (Aktiv/Inaktiv/Alle) und Toggle-Button |
| 8 | Artikel-Anzahl & FTP Check | ✅ Erledigt | Artikelzählung, FTP Check Button, Download bei Änderung |
| 9 | Toast-Meldungen | ✅ Erledigt | Bootstrap Toasts statt Alert-Boxen für bessere UX |
| 10 | Config Import/Export | ✅ Erledigt | JSON Export/Import der Config-Tabelle |
| 11 | S3 Storage | ✅ Erledigt | S3-kompatibler Objektspeicher für Dateipersistenz |
| 12 | PostgreSQL/MariaDB | ✅ Erledigt | Datenbank-agnostische Konfiguration |
| 13 | Flask-Migrate | ✅ Erledigt | Automatische Schema-Migrationen mit Alembic |
| 14 | Flask-Admin | ✅ Erledigt | DB-Verwaltung unter /db-admin (nur Admins) |

**Letztes Update:** 2025-12-06

---

## Tech-Stack

| Komponente       | Technologie        | Begründung                              |
|------------------|--------------------|-----------------------------------------|
| **Sprache**      | Python 3.11+       | Vorgabe, gute CSV/Excel-Unterstützung   |
| **Package Manager** | uv              | Schnell, modernes Dependency-Management |
| **Web-Framework**| Flask              | Leichtgewichtig, schnell für MVP        |
| **Prod-Server**  | gunicorn           | Produktions-WSGI-Server                 |
| **Datenbank**    | SQLite/PostgreSQL  | SQLite für POC, PostgreSQL für Prod     |
| **ORM**          | SQLAlchemy         | Flexible DB-Abstraktion                 |
| **FTP**          | ftplib             | Python-Standard                         |
| **HTTP-Client**  | httpx / aiohttp    | Async Bild-Downloads                    |
| **Excel-Export** | openpyxl           | XLSX-Erstellung                         |
| **CSV**          | csv (stdlib)       | Standard-Parsing                        |
| **Frontend**     | Jinja2 + Bootstrap 5 | Minimal, schnell umsetzbar            |
| **Deployment**   | Nixpacks / Coolify | Container-Deployment                    |

---

## Projektstruktur

```
pricat-converter/
├── app/
│   ├── __init__.py           # Flask App Factory
│   ├── config.py             # Konfiguration
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py           # SQLAlchemy Base
│   │   ├── lieferant.py      # Lieferant Model
│   │   ├── hersteller.py     # Hersteller Model
│   │   ├── marke.py          # Marke Model
│   │   └── config.py         # Config Key-Value Model
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ftp_service.py    # FTP Upload/Download
│   │   ├── pricat_parser.py  # PRICAT CSV Parser
│   │   ├── elena_exporter.py # Elena CSV Generator
│   │   ├── image_downloader.py # Async Bild-Download
│   │   ├── xlsx_exporter.py  # XLSX Export
│   │   └── import_trigger.py # Elena Import auslösen
│   ├── routes/
│   │   └── main.py           # Web-Routen
│   └── templates/
│       ├── base.html
│       ├── index.html        # Lieferanten-Liste
│       └── status.html       # Verarbeitungs-Status
├── data/
│   ├── imports/              # Heruntergeladene PRICAT-Dateien
│   ├── exports/              # Generierte Elena-Dateien
│   └── images/               # Heruntergeladene Bilder
├── instance/
│   └── pricat.db             # SQLite Datenbank
├── pyproject.toml            # Dependencies (uv)
├── uv.lock
└── run.py                    # Entry Point
```

---

## Datenbank-Schema

### ER-Diagramm

```
┌─────────────────┐       ┌─────────────────┐       ┌──────────────────┐
│    Lieferant    │       │   Hersteller    │       │     Marke        │
├─────────────────┤       ├─────────────────┤       ├──────────────────┤
│ id (PK)         │       │ id (PK)         │       │ id (PK)          │
│ gln             │       │ gln             │◀──┐   │ kurzbezeichnung  │
│ vedes_id        │       │ vedes_id        │   │   │ gln_evendo       │
│ kurzbezeichnung │       │ kurzbezeichnung │   │   │ hersteller_id(FK)│──┐
│ aktiv           │       │ created_at      │   │   │ created_at       │  │
│ ftp_quelldatei  │       │ updated_at      │   │   │ updated_at       │  │
│ elena_startdir  │       └─────────────────┘   │   └──────────────────┘  │
│ letzte_konvert. │                             │                         │
│ created_at      │                             └─────────────────────────┘
│ updated_at      │                                   n:1 Beziehung
└─────────────────┘

┌─────────────────┐
│     Config      │
├─────────────────┤
│ id (PK)         │
│ key (unique)    │
│ value           │
│ beschreibung    │
│ created_at      │
│ updated_at      │
└─────────────────┘
```

### Tabellen-Definitionen

#### Tabelle: `lieferant`

| Spalte              | Typ          | Constraint    | Beschreibung                        |
|---------------------|--------------|---------------|-------------------------------------|
| id                  | INTEGER      | PK, AUTO      | Primärschlüssel                     |
| gln                 | VARCHAR(13)  | UNIQUE        | GLN des Lieferanten                 |
| vedes_id            | VARCHAR(13)  | UNIQUE        | VEDES-interne Lieferanten-ID        |
| kurzbezeichnung     | VARCHAR(40)  | NOT NULL      | Lieferantenname                     |
| aktiv               | BOOLEAN      | DEFAULT true  | Lieferant aktiv für Verarbeitung    |
| ftp_quelldatei      | VARCHAR(255) |               | Pfad/Datei auf VEDES-FTP            |
| ftp_pfad_ziel       | VARCHAR(255) |               | Ziel-Pfad auf Elena-FTP             |
| elena_startdir      | VARCHAR(50)  |               | startdir-Parameter für getData.php  |
| elena_base_url      | VARCHAR(255) |               | z.B. https://direct.e-vendo.de      |
| artikel_anzahl      | INTEGER      |               | Anzahl Artikel in PRICAT            |
| ftp_datei_datum     | DATETIME     |               | Änderungsdatum der FTP-Datei        |
| ftp_datei_groesse   | INTEGER      |               | Dateigröße in Bytes                 |
| letzte_konvertierung| DATETIME     |               | Zeitstempel letzte Verarbeitung     |
| created_at          | DATETIME     | DEFAULT NOW   | Erstellungszeitpunkt                |
| updated_at          | DATETIME     |               | Letztes Update                      |

#### Tabelle: `hersteller`

| Spalte          | Typ          | Constraint    | Beschreibung                        |
|-----------------|--------------|---------------|-------------------------------------|
| id              | INTEGER      | PK, AUTO      | Primärschlüssel                     |
| gln             | VARCHAR(13)  | UNIQUE        | GLN des Herstellers                 |
| vedes_id        | VARCHAR(13)  | UNIQUE        | VEDES-interne Hersteller-ID         |
| kurzbezeichnung | VARCHAR(40)  | NOT NULL      | Herstellername                      |
| created_at      | DATETIME     | DEFAULT NOW   | Erstellungszeitpunkt                |
| updated_at      | DATETIME     |               | Letztes Update                      |

#### Tabelle: `marke`

| Spalte          | Typ          | Constraint    | Beschreibung                        |
|-----------------|--------------|---------------|-------------------------------------|
| id              | INTEGER      | PK, AUTO      | Primärschlüssel                     |
| kurzbezeichnung | VARCHAR(40)  | NOT NULL      | Markenbezeichnung                   |
| gln_evendo      | VARCHAR(20)  | UNIQUE        | Format: {Hersteller.GLN}_{Nr}       |
| hersteller_id   | INTEGER      | FK            | Referenz auf Hersteller             |
| created_at      | DATETIME     | DEFAULT NOW   | Erstellungszeitpunkt                |
| updated_at      | DATETIME     |               | Letztes Update                      |

#### Tabelle: `config`

| Spalte       | Typ          | Constraint    | Beschreibung                        |
|--------------|--------------|---------------|-------------------------------------|
| id           | INTEGER      | PK, AUTO      | Primärschlüssel                     |
| key          | VARCHAR(50)  | UNIQUE        | Konfigurations-Schlüssel            |
| value        | TEXT         |               | Konfigurations-Wert                 |
| beschreibung | VARCHAR(255) |               | Beschreibung der Einstellung        |
| created_at   | DATETIME     | DEFAULT NOW   | Erstellungszeitpunkt                |
| updated_at   | DATETIME     |               | Letztes Update                      |

**Vordefinierte Config-Einträge:**

| Key                  | Beispiel-Value               | Beschreibung                    |
|----------------------|------------------------------|---------------------------------|
| vedes_ftp_host       | ftp.vedes.de                 | VEDES FTP Server                |
| vedes_ftp_port       | 21                           | VEDES FTP Port                  |
| vedes_ftp_user       | username                     | VEDES FTP Benutzer              |
| vedes_ftp_pass       | (base64)                     | VEDES FTP Passwort (Base64)     |
| vedes_ftp_basepath   | /pricat/                     | Basispfad auf VEDES FTP         |
| elena_ftp_host       | ftp.e-vendo.de               | Ziel-FTP Server                 |
| elena_ftp_port       | 21                           | Ziel-FTP Port                   |
| elena_ftp_user       | username                     | Ziel-FTP Benutzer               |
| elena_ftp_pass       | (base64)                     | Ziel-FTP Passwort (Base64)      |
| image_download_threads| 5                           | Parallele Bild-Downloads        |
| image_timeout        | 30                           | Timeout für Bild-Downloads (s)  |
| s3_enabled           | false                        | S3 Storage aktivieren           |
| s3_endpoint          | s3.eu-central-1.amazonaws.com| S3 Endpoint URL                 |
| s3_bucket            | pricat-data                  | S3 Bucket Name                  |

---

## PRICAT → Elena Mapping

### PRICAT Quellformat (VEDES StyleGuide V2.0)

- **Delimiter:** Semikolon (`;`)
- **Encoding:** UTF-8 (ggf. Latin-1 Fallback)
- **Header-Zeile:** Beginnt mit `H;PRICAT;...`
- **Daten-Zeilen:** Beginnen mit `P;PRICAT;...`
- **Spaltenanzahl:** 143

### Relevante PRICAT-Spalten (0-basiert)

| Nr  | PRICAT-Spalte              | Elena-Ziel                  |
|-----|----------------------------|-----------------------------|
| 5   | VedesArtikelnummer         | articleNumber               |
| 9   | EANUPC                     | articleNumberEAN            |
| 12  | Artikelbezeichnung         | articleName                 |
| 25  | LieferantGLN               | regularSupplierGLN          |
| 26  | LieferantID                | (DB: Lieferant)             |
| 27  | Lieferantname              | regularSupplierName         |
| 29  | HerstellerGLN              | manufacturerGLN             |
| 30  | HerstellerID               | (DB: Hersteller)            |
| 31  | Herstellername             | manufacturerName            |
| 32  | ArtikelnummerDesHerstellers| articleNumberMPN            |
| 33  | UVPE                       | recommendedRetailPrice      |
| 34  | GNP_Lieferant              | priceEK                     |
| 38  | MWST                       | taxRate                     |
| 51  | MarkeText                  | (DB: Marke.kurzbezeichnung) |
| 63  | Gewicht                    | weight                      |
| 94  | Bilderlink                 | pictures                    |
| 96  | Grunddatentext             | longDescription             |
| 99  | Warnhinweise               | (in longDescription)        |

### Elena Zielformat

CSV mit Semikolon-Delimiter, UTF-8, Double-Quote Enclosure.

Wichtige Felder:
- `articleNumber` - Artikelnummer
- `articleNumberMPN` - Hersteller-Artikelnummer
- `articleNumberEAN` - GTIN/EAN
- `articleName` - Kurzbezeichnung
- `priceEK` - Grundnettopreis
- `recommendedRetailPrice` - UVP
- `regularSupplierName` / `regularSupplierGLN` - Lieferant
- `manufacturerName` / `manufacturerGLN` - Hersteller
- `brandName` / `brandId` - Marke (brandId = gln_evendo)
- `longDescription` - Langtext
- `pictures` - Name Bild 1-15

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

## Komponenten

### FTP Service (`ftp_service.py`)

```python
class FTPService:
    def download_pricat(lieferant: Lieferant) -> Path
    def upload_elena_package(lieferant: Lieferant, csv_path: Path, images_dir: Path) -> bool
    def check_file_info(lieferant: Lieferant) -> FileInfo  # Datum, Größe
```

### PRICAT Parser (`pricat_parser.py`)

```python
class PricatParser:
    def parse(file_path: Path) -> PricatData
    def extract_entities(data: PricatData) -> tuple[Lieferant, list[Hersteller], list[Marke]]
    def get_image_urls(data: PricatData) -> list[str]
```

### Elena Exporter (`elena_exporter.py`)

```python
class ElenaExporter:
    def export(articles: list[Article], output_path: Path) -> Path
```

### Image Downloader (`image_downloader.py`)

```python
class ImageDownloader:
    async def download_all(urls: list[str], target_dir: Path, max_concurrent: int = 5) -> DownloadResult
```

### XLSX Exporter (`xlsx_exporter.py`)

```python
class XlsxExporter:
    def export_entities(lieferant: Lieferant, hersteller: list[Hersteller], marken: list[Marke], output_path: Path) -> Path
```

### Import Trigger (`import_trigger.py`)

```python
class ImportTrigger:
    def trigger(base_url: str, startdir: str, importfile: str, debuglevel: int = 1) -> ImportResult
```

---

## Datenfluss (Detail)

```
1. User klickt "Verarbeite" für Lieferant X
                    │
                    ▼
2. FTPService.download_pricat(X)
   └── Speichert: data/imports/pricat_{vedes_id}_{timestamp}.csv
                    │
                    ▼
3. PricatParser.parse(csv_path)
   ├── Extrahiert Lieferant → DB upsert
   ├── Extrahiert Hersteller → DB upsert
   ├── Extrahiert Marken → DB upsert (mit GLN_evendo Generierung)
   └── Gibt strukturierte Artikeldaten zurück
                    │
                    ▼
4. ImageDownloader.download_all(image_urls)
   └── Speichert: data/images/{vedes_id}_{kurzname}/*.jpg
       (parallel, async)
                    │
                    ▼
5. ElenaExporter.export(articles)
   └── Speichert: data/exports/elena_{vedes_id}_{timestamp}.csv
                    │
                    ▼
6. XlsxExporter.export_entities(...)
   └── Speichert: data/exports/entities_{vedes_id}_{timestamp}.xlsx
                    │
                    ▼
7. FTPService.upload_elena_package(...)
   └── Upload nach Ziel-FTP: /{startdir}/
                    │
                    ▼
8. ImportTrigger.trigger(...)
   └── GET https://{base_url}/importer/getData.php?startdir={startdir}&importfile={filename}
                    │
                    ▼
9. Update: Lieferant.letzte_konvertierung = NOW()
```

---

## Fehlerbehandlung

| Fehlerfall                    | Behandlung                                      |
|-------------------------------|-------------------------------------------------|
| VEDES-FTP nicht erreichbar    | Retry 3x, dann Fehlermeldung im UI              |
| PRICAT-Datei nicht gefunden   | Fehlermeldung, Lieferant als "keine Daten" markieren |
| CSV-Parsing-Fehler            | Log mit Zeilennummer, Abbruch mit Hinweis       |
| Bild-Download fehlgeschlagen  | Einzelbild überspringen, in Report vermerken    |
| Ziel-FTP Upload fehlgeschlagen| Retry 3x, dann Rollback/Fehlermeldung           |
| Elena-Import fehlgeschlagen   | HTTP-Response loggen, Fehlermeldung im UI       |

---

## UI/UX Richtlinien

### Toast-Meldungen

Alle Benutzer-Feedback-Meldungen werden als **Bootstrap Toast-Meldungen** angezeigt.

**Keine Alert-Boxen** im Seiteninhalt - diese führen zu schlechter UX.

**Toast-Eigenschaften:**
- Position: Oben rechts (fixed)
- Auto-Hide: Nach 5 Sekunden
- Schließbar: Manuell via X-Button
- Stapelbar: Mehrere Meldungen übereinander

**Farbkodierung:**

| Kategorie | CSS-Klasse | Verwendung |
|-----------|------------|------------|
| success | `text-bg-success` | Aktion erfolgreich |
| danger | `text-bg-danger` | Fehler aufgetreten |
| warning | `text-bg-warning` | Warnung/Hinweis |
| info | `text-bg-info` | Information |

### Weitere UI-Konventionen

- **Tabellen:** Bootstrap `table-hover` für interaktive Listen
- **Buttons:** Primäre Aktionen `btn-primary`, sekundäre `btn-outline-*`
- **Status-Badges:** `badge bg-success/secondary` für Aktiv/Inaktiv

---

## Erledigte Tasks

### Task 1: FTP Port-Konfiguration
- Neue Config-Einträge: `vedes_ftp_port` und `elena_ftp_port`
- Standard-Port 21 als Fallback

### Task 2: Admin-Seite mit Verbindungstests
- Blueprint `admin_bp` unter `/admin/*`
- Buttons für VEDES/Elena FTP Verbindungstests
- Health-Check Endpoint `/api/health`

### Task 3: Benutzer-Authentifizierung
- Flask-Login mit DB-basierten Rollen: `admin`, `mitarbeiter`, `kunde`
- Login-Schutz fuer alle Routes
- Initiale Benutzer via `flask seed-users`

### Task 4: VEDES_ID ohne führende Nullen
- `strip_leading_zeros()` Hilfsfunktion
- Speicherung ohne führende Nullen (z.B. `1872` statt `0000001872`)

### Task 5: Lieferanten-Synchronisation
- Automatische Anlage neuer Lieferanten aus FTP-Scan
- Spalte `ftp_pfad_quelle` → `ftp_quelldatei`
- GLN nullable für auto-erstellte Lieferanten

### Task 6: Base64-kodierte Passwörter
- FileZilla-kompatible Base64-Dekodierung
- `_decode_password()` Methode in FTPService

### Task 7: Lieferanten-Filter
- Filter: Aktiv/Inaktiv/Alle (Standard: Aktiv)
- Toggle-Button pro Lieferant

### Task 8: Artikel-Anzahl & FTP Check
- Felder: `artikel_anzahl`, `ftp_datei_datum`, `ftp_datei_groesse`
- Download nur bei Dateiänderung
- FTP Check Button pro Lieferant

### Task 9: Toast-Meldungen
- Bootstrap 5 Toasts (fixed oben rechts)
- Auto-Hide nach 5 Sekunden

### Task 10: Config Import/Export
- JSON Export aller Config-Einträge
- JSON Import mit Merge-Logik
- Admin-only Funktionen

### Task 11: S3 Storage Service
- `StorageService` Abstraktion (Local/S3)
- Hetzner Object Storage kompatibel
- Config: `s3_enabled`, `s3_endpoint`, `s3_bucket`, etc.

### Task 12: PostgreSQL/MariaDB Support
- DATABASE_URL Environment-Variable
- Automatische `postgres://` → `postgresql://` Konvertierung
- Treiber: psycopg2-binary, pymysql

### Task 13: Flask-Migrate
- Alembic-basierte Migrationen
- `flask db upgrade` im Deployment
- Initiale Migration für alle Models

### Task 14: Flask-Admin
- Unter `/db-admin` (nicht `/admin`)
- Nur für Rolle `admin` zugänglich
- Views: Lieferanten, Hersteller, Marken, Config, Users

---

## Elena Target Format

See `docs/beispiel_mapping.php` for full mapping. Key fields:
- articleNumber, articleNumberMPN, articleNumberEAN
- articleName, longDescription
- priceEK (Grundnettopreis), recommendedRetailPrice
- regularSupplierName/GLN, manufacturerName/GLN
- brandName, brandId (gln_evendo)
- pictures (Name Bild 1-15)

CSV format: Semicolon delimiter, UTF-8, double-quote enclosure

---
## Elena Target Format

See `docs/beispiel_mapping.php` for full mapping. Key fields:
- articleNumber, articleNumberMPN, articleNumberEAN
- articleName, longDescription
- priceEK (Grundnettopreis), recommendedRetailPrice
- regularSupplierName/GLN, manufacturerName/GLN
- brandName, brandId (gln_evendo)
- pictures (Name Bild 1-15)

CSV format: Semicolon delimiter, UTF-8, double-quote enclosure

---

## Offene Tasks

*Aktuell keine offenen pricat-spezifischen Tasks.*
