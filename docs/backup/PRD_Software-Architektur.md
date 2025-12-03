# PRD Software-Architektur

## pricat-converter

**Version:** 1.0  
**Erstellt:** 2025-01-XX  
**Status:** Draft

---

## 1. Übersicht

Der **pricat-converter** ist ein Web-Tool zur Konvertierung von VEDES PRICAT-Dateien in das Elena-Import-Format für e-vendo. Das Tool liest Lieferanten-Stammdaten im VEDES-Format, transformiert diese und lädt die Ergebnisse inkl. Artikelbilder auf einen FTP-Server.

---

## 2. Tech-Stack

| Komponente | Technologie | Version |
|------------|-------------|---------|
| Backend | Python | 3.11+ |
| Web-Framework | Flask / FastAPI | Latest |
| Datenbank | SQLite | 3.x |
| Frontend | HTML/CSS/JS (minimal) | - |
| FTP-Client | ftplib (stdlib) | - |
| HTTP-Client | requests / httpx | Latest |
| Async/Parallel | asyncio / concurrent.futures | - |
| Excel-Export | openpyxl | Latest |
| CSV-Verarbeitung | csv (stdlib) / pandas | - |

---

## 3. Systemarchitektur

```
┌──────────────────────────────────────────────────────────────────────┐
│                         pricat-converter                             │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐    │
│  │   Frontend   │───▶│   Backend    │───▶│      SQLite DB       │    │
│  │  (HTML/JS)   │    │  (Python)    │    │                      │    │
│  └──────────────┘    └──────┬───────┘    └──────────────────────┘    │
│                             │                                        │
│         ┌───────────────────┼───────────────────┐                    │
│         ▼                   ▼                   ▼                    │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐           │
│  │  VEDES FTP  │    │ Bild-URLs   │    │   Ziel-FTP      │           │
│  │  (Source)   │    │ (HTTPS)     │    │   (Target)      │           │
│  └─────────────┘    └─────────────┘    └─────────────────┘           │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   Elena-Import (PHP)    │
                    │   getData.php           │
                    └─────────────────────────┘
```

---

## 4. Datenbankschema

### 4.1 ER-Diagramm

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     config       │       │    lieferant    │       │   hersteller    │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │       │ id (PK)         │       │ id (PK)         │
│ key (UNIQUE)    │       │ vedes_id        │       │ vedes_id        │
│ value           │       │ gln             │       │ gln             │
│ description     │       │ kurzbezeichnung │       │ kurzbezeichnung │
│ created_at      │       │ aktiv           │       │ created_at      │
│ updated_at      │       │ ftp_startdir    │       │ updated_at      │
└─────────────────┘       │ letzte_konvert  │       └────────┬────────┘
                          │ created_at      │                │
                          │ updated_at      │                │ 1
                          └─────────────────┘                │
                                                             │
                                                             │ n
                                                    ┌────────┴────────┐
                                                    │      marke      │
                                                    ├─────────────────┤
                                                    │ id (PK)         │
                                                    │ kurzbezeichnung │
                                                    │ gln_evendo      │
                                                    │ hersteller_id   │
                                                    │ created_at      │
                                                    │ updated_at      │
                                                    └─────────────────┘
```

### 4.2 Tabellendefinitionen

#### config
Speichert Key-Value-Konfigurationen (FTP-Zugangsdaten, Pfade, etc.)

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| id | INTEGER PRIMARY KEY | Auto-Increment |
| key | TEXT UNIQUE NOT NULL | Konfigurationsschlüssel |
| value | TEXT | Konfigurationswert |
| description | TEXT | Beschreibung |
| created_at | TIMESTAMP | Erstellungszeitpunkt |
| updated_at | TIMESTAMP | Letzte Änderung |

**Beispiel-Einträge:**
- `vedes_ftp_host`, `vedes_ftp_user`, `vedes_ftp_pass`, `vedes_ftp_path`
- `target_ftp_host`, `target_ftp_user`, `target_ftp_pass`
- `elena_import_base_url`

#### lieferant
Lieferantenstammdaten aus PRICAT-Dateien

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| id | INTEGER PRIMARY KEY | Auto-Increment |
| vedes_id | TEXT UNIQUE NOT NULL | VEDES-interne Lieferantennummer (Spalte 27) |
| gln | TEXT | GLN des Lieferanten (Spalte 26) |
| kurzbezeichnung | TEXT NOT NULL | Lieferantenname (Spalte 28) |
| aktiv | BOOLEAN DEFAULT 1 | Lieferant aktiv für Verarbeitung |
| ftp_startdir | TEXT | Zielverzeichnis auf FTP (z.B. "1872_lego") |
| letzte_konvertierung | TIMESTAMP | Zeitpunkt der letzten erfolgreichen Konvertierung |
| created_at | TIMESTAMP | Erstellungszeitpunkt |
| updated_at | TIMESTAMP | Letzte Änderung |

#### hersteller
Herstellerstammdaten aus PRICAT-Dateien

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| id | INTEGER PRIMARY KEY | Auto-Increment |
| vedes_id | TEXT UNIQUE NOT NULL | VEDES-interne Herstellernummer (Spalte 31) |
| gln | TEXT | GLN des Herstellers (Spalte 30) |
| kurzbezeichnung | TEXT NOT NULL | Herstellername (Spalte 32) |
| created_at | TIMESTAMP | Erstellungszeitpunkt |
| updated_at | TIMESTAMP | Letzte Änderung |

#### marke
Markeninformationen (n:1 Beziehung zu Hersteller)

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| id | INTEGER PRIMARY KEY | Auto-Increment |
| kurzbezeichnung | TEXT NOT NULL | Markenbezeichnung (Spalte 52 - MarkeText) |
| gln_evendo | TEXT UNIQUE | Generierte GLN: {Hersteller.GLN}_{lfd_nr} |
| hersteller_id | INTEGER FK | Fremdschlüssel zu hersteller.id |
| created_at | TIMESTAMP | Erstellungszeitpunkt |
| updated_at | TIMESTAMP | Letzte Änderung |

#### artikel (optional für Zwischenspeicherung)
Artikeldaten während der Verarbeitung

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| id | INTEGER PRIMARY KEY | Auto-Increment |
| vedes_artikelnummer | TEXT | VEDES Sortimentsnummer (Spalte 6) |
| ean | TEXT | EAN (Spalte 10) |
| artikelbezeichnung | TEXT | Artikelname (Spalte 13) |
| lieferant_id | INTEGER FK | Fremdschlüssel zu lieferant.id |
| hersteller_id | INTEGER FK | Fremdschlüssel zu hersteller.id |
| marke_id | INTEGER FK | Fremdschlüssel zu marke.id |
| uvp | DECIMAL | UVP (Spalte 34) |
| ek_preis | DECIMAL | EK-Preis (Spalte 35) |
| bild_url | TEXT | Haupt-Bild-URL (Spalte 95) |
| raw_data | JSON | Komplette Rohdaten als JSON |
| created_at | TIMESTAMP | Erstellungszeitpunkt |

---

## 5. Komponenten

### 5.1 Backend-Module

```
pricat-converter/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Flask/FastAPI App-Entry
│   ├── config.py               # App-Konfiguration
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py           # SQLAlchemy Models
│   │   ├── connection.py       # DB-Connection
│   │   └── migrations/         # Schema-Migrationen
│   ├── services/
│   │   ├── __init__.py
│   │   ├── pricat_parser.py    # VEDES PRICAT Parser
│   │   ├── elena_converter.py  # Konvertierung zu Elena-Format
│   │   ├── ftp_service.py      # FTP Upload/Download
│   │   ├── image_downloader.py # Async Bild-Download
│   │   ├── xlsx_exporter.py    # Excel-Export
│   │   └── elena_trigger.py    # Elena-Import HTTP-Trigger
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py           # REST-API Endpoints
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
├── static/                     # CSS, JS
├── templates/                  # HTML-Templates
├── data/
│   ├── imports/                # Heruntergeladene PRICAT-Dateien
│   ├── exports/                # Generierte Elena-CSVs
│   └── images/                 # Heruntergeladene Bilder
│       └── {lieferant_id}_{kurzbezeichnung}/
├── tests/
├── requirements.txt
├── pricat_converter.db         # SQLite Datenbank
└── README.md
```

### 5.2 Service-Beschreibungen

| Service | Beschreibung |
|---------|--------------|
| `pricat_parser.py` | Liest VEDES PRICAT-CSV, extrahiert Header/Daten, mappt Spalten |
| `elena_converter.py` | Transformiert PRICAT-Daten in Elena-Format gemäß mapping.php |
| `ftp_service.py` | FTP-Verbindung, Download von VEDES, Upload zu Ziel-FTP |
| `image_downloader.py` | Paralleler Download von Artikelbildern via asyncio/ThreadPool |
| `xlsx_exporter.py` | Erstellt Excel mit Lieferant/Hersteller/Marken-Übersicht |
| `elena_trigger.py` | HTTP-Request an Elena getData.php nach erfolgreichem Upload |

---

## 6. Datenfluss

### 6.1 PRICAT-Spalten → Elena-Mapping

| VEDES PRICAT (Spalte) | Elena-Feld | Bemerkung |
|-----------------------|------------|-----------|
| 6 - VedesArtikelnummer | articleNumber | Artikelnummer |
| 10 - EANUPC | articleNumberEAN | EAN/GTIN |
| 13 - Artikelbezeichnung | articleName | Kurzbezeichnung |
| 26 - LieferantGLN | dataSupplierGLN | GLN Lieferant |
| 28 - Lieferantname | dataSupplierName | Name Lieferant |
| 30 - HerstellerGLN | manufacturerGLN | GLN Hersteller |
| 32 - Herstellername | manufacturerName | Name Hersteller |
| 33 - ArtikelnummerDesHerstellers | articleNumberMPN | Hersteller-Artikelnr. |
| 34 - UVPE | recommendedRetailPrice, listPrice | UVP |
| 35 - GNP_Lieferant | priceEK | Einkaufspreis |
| 39 - MWST | taxRate | MwSt-Satz (1→19%, 2→7%) |
| 52 - MarkeText | brandName | Marke |
| 64 - Gewicht | weight | Gewicht |
| 95 - Bilderlink | pictures | Bild-URL |
| 97 - Grunddatentext | longDescription | Langtext |
| 100 - Warnhinweise | (extraInformation) | Warnhinweise |

### 6.2 Verarbeitungsablauf

```
1. VEDES FTP
   └──▶ Download pricat_{id}_{name}.csv
         │
2. PRICAT Parser
   └──▶ Parse CSV, extrahiere Stammdaten
         │
3. DB Update
   └──▶ Aktualisiere Lieferant/Hersteller/Marke-Tabellen
         │
4. Elena Converter
   └──▶ Transformiere zu Elena-CSV-Format
         │
5. Image Downloader (parallel)
   └──▶ Lade Bilder von medien.vedes.de
         │
6. XLSX Exporter
   └──▶ Erstelle Übersicht (Kurzbezeichnung, GLN)
         │
7. FTP Upload
   └──▶ Upload CSV + Bilder zu Ziel-FTP
         │
8. Elena Trigger
   └──▶ HTTP GET getData.php?startdir=...&importfile=...
```

---

## 7. Externe Schnittstellen

### 7.1 VEDES FTP (Source)
- **Protokoll:** FTP/FTPS
- **Dateien:** `pricat_{lieferant_id}_{name}_{nr}.csv`
- **Encoding:** UTF-8 / Windows-1252

### 7.2 Bild-Server
- **URL-Muster:** `https://medien.vedes.de/Produktbilder_VEDES_Original/...`
- **Formate:** JPG, PNG

### 7.3 Ziel-FTP (Target)
- **Protokoll:** FTP/FTPS
- **Struktur:**
  ```
  /{startdir}/
  ├── {lieferant}_stammdaten.csv
  ├── mapping.php
  ├── config.php
  └── images/
      └── *.jpg
  ```

### 7.4 Elena-Import
- **Endpoint:** `https://{domain}/importer/getData.php`
- **Parameter:**
  - `startdir` - FTP-Unterverzeichnis
  - `importfile` - CSV-Dateiname
  - `debuglevel` - 0/1

---

## 8. Sicherheit

- FTP-Zugangsdaten verschlüsselt in DB speichern (oder via Environment-Variablen)
- Keine sensiblen Daten in Logs
- Validierung aller Eingaben
- Rate-Limiting für Bild-Downloads

---

## 9. Erweiterbarkeit

Das System ist so konzipiert, dass später weitere Quellformate (nicht nur VEDES PRICAT) unterstützt werden können:
- Parser-Interface für verschiedene Importformate
- Modulare Converter-Struktur
- Konfigurierbare Feld-Mappings pro Lieferant
