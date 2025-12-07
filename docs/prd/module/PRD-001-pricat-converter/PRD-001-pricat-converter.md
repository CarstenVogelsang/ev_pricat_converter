# PRD-001: PRICAT Converter

Konvertiert VEDES PRICAT-Dateien (Lieferanten-Produktdaten) in das Elena-Importformat für e-vendo Systeme.

**Status:** Aktiv
**Letztes Update:** 2025-12-07

```
VEDES FTP (PRICAT CSV) → pricat-converter → Ziel-FTP (Elena CSV + Bilder) → Elena Import
```

---

## 1. Funktionsübersicht

| Funktion | Beschreibung |
|----------|--------------|
| PRICAT Download | CSV-Dateien vom VEDES-FTP herunterladen |
| Entity-Extraktion | Lieferant, Hersteller, Marken aus PRICAT extrahieren |
| Bild-Download | Artikelbilder parallel herunterladen |
| Elena-Export | CSV im Elena-Format generieren |
| FTP-Upload | Dateien auf Ziel-FTP hochladen |
| Import-Trigger | Elena-Import per HTTP auslösen |

---

## 2. Zugriffsrechte

| Rolle | Zugriff |
|-------|---------|
| Admin | Vollzugriff |
| Mitarbeiter | Vollzugriff |
| Kunde | Kein Zugriff |

---

## 3. Datenmodell

### Tabelle: `lieferant`

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| id | INTEGER PK | Primärschlüssel |
| gln | VARCHAR(13) UNIQUE | GLN des Lieferanten |
| vedes_id | VARCHAR(13) UNIQUE | VEDES-interne ID |
| kurzbezeichnung | VARCHAR(40) | Lieferantenname |
| aktiv | BOOLEAN | Aktiv für Verarbeitung |
| ftp_quelldatei | VARCHAR(255) | Pfad auf VEDES-FTP |
| ftp_pfad_ziel | VARCHAR(255) | Ziel-Pfad auf Elena-FTP |
| elena_startdir | VARCHAR(50) | startdir für getData.php |
| elena_base_url | VARCHAR(255) | z.B. https://direct.e-vendo.de |
| artikel_anzahl | INTEGER | Anzahl Artikel in PRICAT |
| ftp_datei_datum | DATETIME | Änderungsdatum FTP-Datei |
| ftp_datei_groesse | INTEGER | Dateigröße in Bytes |
| letzte_konvertierung | DATETIME | Letzte Verarbeitung |
| created_at | DATETIME | Erstellungszeitpunkt |
| updated_at | DATETIME | Letztes Update |

### Tabelle: `hersteller`

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| id | INTEGER PK | Primärschlüssel |
| gln | VARCHAR(13) UNIQUE | GLN des Herstellers |
| vedes_id | VARCHAR(13) UNIQUE | VEDES-interne ID |
| kurzbezeichnung | VARCHAR(40) | Herstellername |
| created_at | DATETIME | Erstellungszeitpunkt |
| updated_at | DATETIME | Letztes Update |

### Tabelle: `marke`

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| id | INTEGER PK | Primärschlüssel |
| kurzbezeichnung | VARCHAR(40) | Markenbezeichnung |
| gln_evendo | VARCHAR(20) UNIQUE | Format: {Hersteller.GLN}_{Nr} |
| hersteller_id | INTEGER FK | Referenz auf Hersteller |
| created_at | DATETIME | Erstellungszeitpunkt |
| updated_at | DATETIME | Letztes Update |

---

## 4. PRICAT-Format (VEDES)

- **Delimiter:** Semikolon (`;`)
- **Encoding:** UTF-8 (ggf. Latin-1 Fallback)
- **Header-Zeile:** Beginnt mit `H;PRICAT;...`
- **Daten-Zeilen:** Beginnen mit `P;PRICAT;...`
- **Spaltenanzahl:** 143

### Relevante Spalten (0-basiert)

| Index | PRICAT-Spalte | Elena-Ziel |
|-------|---------------|------------|
| 5 | VedesArtikelnummer | articleNumber |
| 9 | EANUPC | articleNumberEAN |
| 12 | Artikelbezeichnung | articleName |
| 25 | LieferantGLN | regularSupplierGLN |
| 26 | LieferantID | (DB: Lieferant) |
| 27 | Lieferantname | regularSupplierName |
| 29 | HerstellerGLN | manufacturerGLN |
| 30 | HerstellerID | (DB: Hersteller) |
| 31 | Herstellername | manufacturerName |
| 32 | ArtikelnummerDesHerstellers | articleNumberMPN |
| 33 | UVPE | recommendedRetailPrice |
| 34 | GNP_Lieferant | priceEK |
| 38 | MWST | taxRate |
| 51 | MarkeText | brandName |
| 63 | Gewicht | weight |
| 94 | Bilderlink | pictures |
| 96 | Grunddatentext | longDescription |
| 99 | Warnhinweise | (in longDescription) |

---

## 5. Elena-Zielformat

CSV mit Semikolon-Delimiter, UTF-8, Double-Quote Enclosure.

### Wichtige Felder

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

Siehe auch: [beispiel_mapping.php](beispiel_mapping.php)

---

## 6. Services

### FTPService

```python
class FTPService:
    def download_pricat(lieferant: Lieferant) -> Path
    def upload_elena_package(lieferant, csv_path, images_dir) -> bool
    def check_file_info(lieferant) -> FileInfo
```

### PricatParser

```python
class PricatParser:
    def parse(file_path: Path) -> PricatData
    def extract_entities(data) -> tuple[Lieferant, list[Hersteller], list[Marke]]
    def get_image_urls(data) -> list[str]
```

### ElenaExporter

```python
class ElenaExporter:
    def export(articles: list[Article], output_path: Path) -> Path
```

### ImageDownloader

```python
class ImageDownloader:
    async def download_all(urls, target_dir, max_concurrent=5) -> DownloadResult
```

### ImportTrigger

```python
class ImportTrigger:
    def trigger(base_url, startdir, importfile, debuglevel=1) -> ImportResult
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
   └── Extrahiert Marken → DB upsert
                    │
                    ▼
4. ImageDownloader.download_all(image_urls)
   └── Speichert: data/images/{vedes_id}_{kurzname}/*.jpg
                    │
                    ▼
5. ElenaExporter.export(articles)
   └── Speichert: data/exports/elena_{vedes_id}_{timestamp}.csv
                    │
                    ▼
6. FTPService.upload_elena_package(...)
   └── Upload nach Ziel-FTP: /{startdir}/
                    │
                    ▼
7. ImportTrigger.trigger(...)
   └── GET {base_url}/importer/getData.php?startdir={startdir}&importfile={filename}
                    │
                    ▼
8. Update: Lieferant.letzte_konvertierung = NOW()
```

---

## 8. Config-Einträge

| Key | Beispiel | Beschreibung |
|-----|----------|--------------|
| vedes_ftp_host | ftp.vedes.de | VEDES FTP Server |
| vedes_ftp_port | 21 | VEDES FTP Port |
| vedes_ftp_user | username | VEDES FTP Benutzer |
| vedes_ftp_pass | (base64) | VEDES FTP Passwort |
| vedes_ftp_basepath | /pricat/ | Basispfad auf VEDES FTP |
| elena_ftp_host | ftp.e-vendo.de | Ziel-FTP Server |
| elena_ftp_port | 21 | Ziel-FTP Port |
| elena_ftp_user | username | Ziel-FTP Benutzer |
| elena_ftp_pass | (base64) | Ziel-FTP Passwort |
| image_download_threads | 5 | Parallele Bild-Downloads |
| image_timeout | 30 | Timeout in Sekunden |

---

## 9. Offene Tasks

*Aktuell keine offenen Tasks.*

---

## 10. Referenzen

- [beispiel_mapping.php](beispiel_mapping.php) - Elena Field Mapping
- [musterlieferant_stammdaten.csv](musterlieferant_stammdaten.csv) - Beispiel Elena CSV
- [pricat_1872_Lego Spielwaren GmbH_0.csv](pricat_1872_Lego%20Spielwaren%20GmbH_0.csv) - Beispiel PRICAT
