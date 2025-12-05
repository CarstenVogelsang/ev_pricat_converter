# PRD Software-Architektur

## pricat-converter

**Version:** 1.0  
**Datum:** 2025-01-03  
**Status:** Draft

---

## 1. Übersicht

Der **pricat-converter** ist ein Web-Tool zur Konvertierung von VEDES PRICAT-Dateien (Lieferanten-Artikelstammdaten) in das Elena-Import-Format für e-vendo Systeme.

### 1.1 Systemkontext

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│   VEDES FTP     │────▶│   pricat-converter   │────▶│  Ziel-FTP       │
│  (PRICAT CSV)   │     │                      │     │  (Elena CSV +   │
│                 │     │  - Web UI            │     │   Bilder)       │
└─────────────────┘     │  - Konvertierung     │     └────────┬────────┘
                        │  - Bild-Download     │              │
┌─────────────────┐     │  - DB-Verwaltung     │              ▼
│  Bild-URLs      │────▶│                      │     ┌─────────────────┐
│  (HTTPS)        │     └──────────────────────┘     │  Elena-Import   │
└─────────────────┘                                  │  (getData.php)  │
                                                     └─────────────────┘
```

---

## 2. Tech-Stack

| Komponente       | Technologie        | Begründung                              |
|------------------|--------------------|-----------------------------------------|
| **Sprache**      | Python 3.11+       | Vorgabe, gute CSV/Excel-Unterstützung   |
| **Package Manager** | uv              | Schnell, modernes Dependency-Management |
| **Web-Framework**| Flask              | Leichtgewichtig, schnell für MVP        |
| **Prod-Server**  | gunicorn           | Produktions-WSGI-Server                 |
| **Datenbank**    | SQLite             | Einfach, kein Server nötig, für POC ideal|
| **ORM**          | SQLAlchemy         | Flexible DB-Abstraktion                 |
| **FTP**          | ftplib             | Python-Standard                         |
| **HTTP-Client**  | httpx / aiohttp    | Async Bild-Downloads                    |
| **Excel-Export** | openpyxl           | XLSX-Erstellung                         |
| **CSV**          | csv (stdlib)       | Standard-Parsing                        |
| **Frontend**     | Jinja2 + Bootstrap 5 | Minimal, schnell umsetzbar            |
| **Deployment**   | Nixpacks / Coolify | Container-Deployment                    |

---

## 3. Projektstruktur

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
│   │   ├── artikel.py        # Artikel Model (optional)
│   │   └── config.py         # Config Key-Value Model
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ftp_service.py    # FTP Upload/Download
│   │   ├── pricat_parser.py  # PRICAT CSV Parser
│   │   ├── elena_exporter.py # Elena CSV Generator
│   │   ├── image_downloader.py # Async Bild-Download
│   │   ├── xlsx_exporter.py  # XLSX Export (Lieferant/Hersteller/Marke)
│   │   └── import_trigger.py # Elena Import auslösen
│   ├── routes/
│   │   ├── __init__.py
│   │   └── main.py           # Web-Routen
│   └── templates/
│       ├── base.html
│       ├── index.html        # Lieferanten-Liste
│       └── status.html       # Verarbeitungs-Status
├── data/
│   ├── imports/              # Heruntergeladene PRICAT-Dateien
│   ├── exports/              # Generierte Elena-Dateien
│   └── images/               # Heruntergeladene Bilder
│       └── {lieferant_id}_{kurzname}/
├── instance/
│   └── pricat.db             # SQLite Datenbank
├── tests/
├── requirements.txt
├── run.py                    # Entry Point
└── README.md
```

---

## 4. Datenbank-Schema

### 4.1 ER-Diagramm

```
┌─────────────────┐       ┌─────────────────┐       ┌──────────────────┐
│    Lieferant    │       │   Hersteller    │       │     Marke        │
├─────────────────┤       ├─────────────────┤       ├──────────────────┤
│ id (PK)         │       │ id (PK)         │       │ id (PK)          │
│ gln             │       │ gln             │◀──┐   │ kurzbezeichnung  │
│ vedes_id        │       │ vedes_id        │   │   │ gln_evendo       │
│ kurzbezeichnung │       │ kurzbezeichnung │   │   │ hersteller_id(FK)│──┐
│ aktiv           │       │ created_at      │   │   │ created_at       │  │
│ ftp_path        │       │ updated_at      │   │   │ updated_at       │  │
│ letzte_konvert. │       └─────────────────┘   │   └──────────────────┘  │
│ created_at      │                             │                         │
│ updated_at      │                             └─────────────────────────┘
└─────────────────┘                                   n:1 Beziehung

┌─────────────────┐
│     Config       │
├─────────────────┤
│ id (PK)         │
│ key (unique)    │
│ value           │
│ beschreibung    │
│ created_at      │
│ updated_at      │
└─────────────────┘
```

### 4.2 Tabellen-Definitionen

#### Tabelle: `lieferant`

| Spalte              | Typ          | Constraint    | Beschreibung                        |
|---------------------|--------------|---------------|-------------------------------------|
| id                  | INTEGER      | PK, AUTO      | Primärschlüssel                     |
| gln                 | VARCHAR(13)  | UNIQUE        | GLN des Lieferanten                 |
| vedes_id            | VARCHAR(13)  | UNIQUE        | VEDES-interne Lieferanten-ID        |
| kurzbezeichnung     | VARCHAR(40)  | NOT NULL      | Lieferantenname                     |
| aktiv               | BOOLEAN      | DEFAULT true  | Lieferant aktiv für Verarbeitung    |
| ftp_pfad_quelle     | VARCHAR(255) |               | Pfad auf VEDES-FTP                  |
| ftp_pfad_ziel       | VARCHAR(255) |               | Ziel-Pfad auf Elena-FTP             |
| elena_startdir      | VARCHAR(50)  |               | startdir-Parameter für getData.php  |
| elena_base_url      | VARCHAR(255) |               | z.B. https://direct.e-vendo.de      |
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

| Key                  | Beispiel-Value                          | Beschreibung                    |
|----------------------|-----------------------------------------|---------------------------------|
| vedes_ftp_host       | ftp.vedes.de                            | VEDES FTP Server                |
| vedes_ftp_user       | username                                | VEDES FTP Benutzer              |
| vedes_ftp_pass       | (encrypted)                             | VEDES FTP Passwort              |
| vedes_ftp_basepath   | /pricat/                                | Basispfad auf VEDES FTP         |
| elena_ftp_host       | ftp.e-vendo.de                          | Ziel-FTP Server                 |
| elena_ftp_user       | username                                | Ziel-FTP Benutzer               |
| elena_ftp_pass       | (encrypted)                             | Ziel-FTP Passwort               |
| image_download_threads| 5                                       | Parallele Bild-Downloads        |
| image_timeout        | 30                                      | Timeout für Bild-Downloads (s)  |

---

## 5. PRICAT → Elena Feld-Mapping

### 5.1 PRICAT Quellformat (VEDES StyleGuide V2.0)

- **Delimiter:** Semikolon (`;`)
- **Encoding:** UTF-8 (ggf. Latin-1 Fallback)
- **Zeilen:** Header beginnt mit `H;PRICAT;...`, Daten mit `P;PRICAT;...`
- **Spaltenanzahl:** 143

### 5.2 Relevante PRICAT-Spalten

| Nr  | PRICAT-Spalte              | Elena-Ziel                  |
|-----|----------------------------|-----------------------------|
| 6   | VedesArtikelnummer         | articleNumber               |
| 10  | EANUPC                     | articleNumberEAN            |
| 13  | Artikelbezeichnung         | articleName                 |
| 26  | LieferantGLN               | regularSupplierGLN          |
| 27  | LieferantID                | (DB: Lieferant)             |
| 28  | Lieferantname              | regularSupplierName         |
| 30  | HerstellerGLN              | manufacturerGLN             |
| 31  | HerstellerID               | (DB: Hersteller)            |
| 32  | Herstellername             | manufacturerName            |
| 33  | ArtikelnummerDesHerstellers| articleNumberMPN            |
| 34  | UVPE                       | recommendedRetailPrice      |
| 35  | GNP_Lieferant              | priceEK                     |
| 39  | MWST                       | taxRate                     |
| 52  | MarkeText                  | (DB: Marke.kurzbezeichnung) |
| 64  | Gewicht                    | weight                      |



### 5.3 Elena Zielformat

Basierend auf /docs/beispiel_mapping.php:

```php
'fields' => [
    'articleNumber' => 'Artikelnummer',
    'articleNumberMPN' => 'MPN',
    'articleNumberEAN' => 'GTIN/EAN',
    'articleName' => 'Kurzbezeichnung',
    'recommendedRetailPrice' => 'Verkaufspreis', 
    'listPrice' => 'Verkaufspreis',
    'priceEK' => 'Grundnettopreis',
    'regularSupplierName' => 'Lieferant', 
    'regularSupplierGLN' => 'Lie-GLN',
    'manufacturerName' => 'Hersteller.kurzbezeichnung',
    'manufacturerGLN' => 'Hersteller-GLN',
    'brandName' => 'Marke',
    'longDescription' => 'Bez-Lang',
    'taxRate' => 'MWST',
    'weight' => 'Gewicht',
    'pictures' => ['Name Bild 1', ...],
    // ... weitere Felder
]
```

---

## 6. Komponenten-Beschreibung

### 6.1 FTP Service (`ftp_service.py`)

**Verantwortlichkeiten:**
- Verbindung zu VEDES-FTP herstellen
- PRICAT-Dateien herunterladen
- Verbindung zu Ziel-FTP herstellen
- Elena-CSV + Bilder hochladen

**Interface:**
```python
class FTPService:
    def download_pricat(lieferant: Lieferant) -> Path
    def upload_elena_package(lieferant: Lieferant, csv_path: Path, images_dir: Path) -> bool
```

### 6.2 PRICAT Parser (`pricat_parser.py`)

**Verantwortlichkeiten:**
- PRICAT-CSV einlesen und parsen
- Lieferant/Hersteller/Marke extrahieren und in DB speichern
- Artikeldaten strukturiert zurückgeben

**Interface:**
```python
class PricatParser:
    def parse(file_path: Path) -> PricatData
    def extract_entities(data: PricatData) -> tuple[Lieferant, list[Hersteller], list[Marke]]
    def get_image_urls(data: PricatData) -> list[str]
```

### 6.3 Elena Exporter (`elena_exporter.py`)

**Verantwortlichkeiten:**
- Artikeldaten in Elena-Format transformieren
- Elena-CSV schreiben

**Interface:**
```python
class ElenaExporter:
    def export(articles: list[Article], output_path: Path) -> Path
```

### 6.4 Image Downloader (`image_downloader.py`)

**Verantwortlichkeiten:**
- Bilder parallel (async) herunterladen
- In Lieferanten-Ordner speichern
- Fortschritt/Fehler tracken

**Interface:**
```python
class ImageDownloader:
    async def download_all(urls: list[str], target_dir: Path, max_concurrent: int = 5) -> DownloadResult
```

### 6.5 XLSX Exporter (`xlsx_exporter.py`)

**Verantwortlichkeiten:**
- XLSX mit Lieferant/Hersteller/Marken-Info erstellen
- Spalten: Kurzbezeichnung, GLN

**Interface:**
```python
class XlsxExporter:
    def export_entities(lieferant: Lieferant, hersteller: list[Hersteller], marken: list[Marke], output_path: Path) -> Path
```

### 6.6 Import Trigger (`import_trigger.py`)

**Verantwortlichkeiten:**
- Elena getData.php aufrufen
- Ergebnis/Status zurückgeben

**Interface:**
```python
class ImportTrigger:
    def trigger(base_url: str, startdir: str, importfile: str, debuglevel: int = 1) -> ImportResult
```

---

## 7. Datenfluss

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

## 8. Fehlerbehandlung

| Fehlerfall                    | Behandlung                                      |
|-------------------------------|-------------------------------------------------|
| VEDES-FTP nicht erreichbar    | Retry 3x, dann Fehlermeldung im UI              |
| PRICAT-Datei nicht gefunden   | Fehlermeldung, Lieferant als "keine Daten" markieren |
| CSV-Parsing-Fehler            | Log mit Zeilennummer, Abbruch mit Hinweis       |
| Bild-Download fehlgeschlagen  | Einzelbild überspringen, in Report vermerken    |
| Ziel-FTP Upload fehlgeschlagen| Retry 3x, dann Rollback/Fehlermeldung           |
| Elena-Import fehlgeschlagen   | HTTP-Response loggen, Fehlermeldung im UI       |

---

## 9. Sicherheit

- FTP-Passwörter verschlüsselt in DB speichern (Fernet/AES)
- Keine Credentials im Code oder Logs
- Input-Validierung bei CSV-Parsing
- Prepared Statements für DB-Queries (SQLAlchemy)

---

## 10. Erweiterbarkeit (V1+)

- **Scheduler:** Automatische tägliche Verarbeitung (APScheduler/Celery)
- **Multi-User:** Login-System, Benutzerrechte
- **Weitere Quellformate:** Nicht-VEDES PRICAT
- **API:** REST-Endpoints für externe Integration
- **Monitoring:** Prometheus Metrics, Health-Checks

---

## 11. UI/UX Richtlinien

### 11.1 Benutzer-Feedback: Toast-Meldungen

**Standard:** Alle Benutzer-Feedback-Meldungen (Erfolg, Fehler, Warnung, Info) werden als **Bootstrap Toast-Meldungen** angezeigt.

**Keine Alert-Boxen** im Seiteninhalt verwenden - diese führen zu schlechter UX, da der User nach Aktionen scrollen muss.

**Toast-Eigenschaften:**
- Position: Oben rechts (fixed)
- Auto-Hide: Nach 5 Sekunden
- Schließbar: Manuell via X-Button
- Stapelbar: Mehrere Meldungen werden übereinander angezeigt

**Farbkodierung (Bootstrap):**
| Kategorie | CSS-Klasse | Verwendung |
|-----------|------------|------------|
| success | `text-bg-success` | Aktion erfolgreich |
| danger | `text-bg-danger` | Fehler aufgetreten |
| warning | `text-bg-warning` | Warnung/Hinweis |
| info | `text-bg-info` | Information |

**Implementierung in `base.html`:**
```html
<div class="toast-container position-fixed top-0 end-0 p-3" style="z-index: 1100;">
    <!-- Flask flash messages als Toasts -->
</div>
```

### 11.2 Weitere UI-Konventionen

- **Tabellen:** Bootstrap `table-hover` für interaktive Listen
- **Buttons:** Primäre Aktionen `btn-primary`, sekundäre `btn-outline-*`
- **Status-Badges:** `badge bg-success/secondary` für Aktiv/Inaktiv
