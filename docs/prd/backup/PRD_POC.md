# PRD POC (Proof of Concept)

## pricat-converter - MVP

**Version:** 1.0  
**Erstellt:** 2025-01-XX  
**Status:** Draft

---

## 1. Zielsetzung

Ein funktionsfähiger **Proof of Concept** zur Validierung des Workflows:
- VEDES PRICAT-Datei laden
- In Elena-Format konvertieren
- Bilder herunterladen
- Auf Ziel-FTP hochladen
- Elena-Import triggern

---

## 2. Scope POC

### 2.1 In Scope ✅

| Feature | Beschreibung |
|---------|--------------|
| Minimales Web-Frontend | Lieferanten-Liste mit "Verarbeite"-Button |
| SQLite-Datenbank | Tabellen: config, lieferant, hersteller, marke |
| VEDES FTP Download | PRICAT-Datei vom Quell-FTP laden |
| PRICAT Parser | CSV parsen, Spalten mappen |
| DB-Extraktion | Lieferant/Hersteller/Marke aus PRICAT extrahieren und in DB speichern |
| Elena-CSV Export | Konvertierung in Elena-Format |
| Bild-Download | Nebenläufiger Download der Artikelbilder |
| XLSX-Export | Excel mit Lieferant/Hersteller/Marken-Übersicht |
| Ziel-FTP Upload | CSV + Bilder hochladen |
| Elena-Trigger | HTTP-Request an getData.php |

### 2.2 Out of Scope ❌

| Feature | Grund |
|---------|-------|
| Benutzerauthentifizierung | POC-Phase |
| Multi-Mandanten | POC-Phase |
| Fehler-Retry-Mechanismen | V1 |
| Detailliertes Logging/Monitoring | V1 |
| Automatische Zeitsteuerung (Cron) | V1 |
| Validierung/Datenqualitätsprüfung | V1 |

---

## 3. User Stories

### US-01: Lieferanten anzeigen
**Als** Anwender  
**möchte ich** alle aktiven Lieferanten in einer Liste sehen  
**damit** ich auswählen kann, welchen Lieferanten ich verarbeiten möchte.

**Akzeptanzkriterien:**
- Liste zeigt: VEDES-ID, Kurzbezeichnung, GLN, letzte Konvertierung
- Nur aktive Lieferanten werden angezeigt
- Button "Verarbeite" pro Lieferant

### US-02: PRICAT verarbeiten
**Als** Anwender  
**möchte ich** per Klick auf "Verarbeite" die komplette Konvertierung starten  
**damit** die Artikeldaten automatisch ins Elena-System übertragen werden.

**Akzeptanzkriterien:**
- PRICAT wird vom VEDES-FTP geladen
- Daten werden in Elena-CSV konvertiert
- Bilder werden heruntergeladen
- XLSX-Übersicht wird erstellt
- Alles wird auf Ziel-FTP hochgeladen
- Elena-Import wird getriggert
- Status-Feedback im Frontend

### US-03: Stammdaten-Extraktion
**Als** System  
**möchte ich** Lieferant/Hersteller/Marke aus PRICAT extrahieren  
**damit** diese Informationen für spätere Verarbeitungen verfügbar sind.

**Akzeptanzkriterien:**
- Neue Lieferanten/Hersteller/Marken werden angelegt
- Bestehende Einträge werden aktualisiert (Upsert)
- Marken werden korrekt dem Hersteller zugeordnet
- GLN_evendo wird generiert: `{Hersteller.GLN}_{lfd_nr}`

### US-04: XLSX-Export
**Als** Anwender  
**möchte ich** eine Excel-Datei mit Lieferant/Hersteller/Marken erhalten  
**damit** ich eine Übersicht über die verarbeiteten Stammdaten habe.

**Akzeptanzkriterien:**
- Spalten: Kurzbezeichnung, GLN
- Enthält: 1 Lieferant, n Hersteller, m Marken
- Dateiname: `{lieferant_id}_stammdaten.xlsx`

---

## 4. Technische Anforderungen

### 4.1 Datenbank-Initialisierung

```sql
-- config Tabelle mit Beispieldaten
INSERT INTO config (key, value, description) VALUES
('vedes_ftp_host', 'ftp.nrz-gmbh.de', 'VEDES FTP Host'),
('vedes_ftp_user', 'M040086720000', 'VEDES FTP Benutzer'),
('vedes_ftp_pass', 'cHczNjI4', 'VEDES FTP Passwort'),
('vedes_ftp_path', '/Datenservice/DOWNLOAD/PRICAT/CSV/DELKREDERE/', 'VEDES FTP Pfad'),
('target_ftp_host', 'ftp-marketplace.e-vendo.de', 'Ziel FTP Host'),
('target_ftp_user', '415458-mobadb', 'Ziel FTP Benutzer'),
('target_ftp_pass', 'ZVNiQVZrdzVVQQ==', 'Ziel FTP Passwort'),
('target_ftp_path', '/', 'Ziel FTP Pfad'),
('target_ftp_path_images', '/images/', 'Ziel FTP Pfad für Bilder unterhalb des Lieferanten-Ordners'),
('target_ftp_path_conf', '/config/', 'Ziel FTP Pfad für Konfigurationsdateien config.php und mapping.php unterhalb des Lieferanten-Ordners'),
('elena_import_url', 'https://direct.e-vendo.de/importer/getData.php', 'Elena Import URL');

-- Beispiel-Lieferant
INSERT INTO lieferant (vedes_id, gln, kurzbezeichnung, aktiv, ftp_startdir) VALUES
('0000001872', '4023017000005', 'LEGO Spielwaren GmbH', 1, '1872_lego');
```

### 4.2 PRICAT-Spalten-Mapping (VEDES → Intern)

| VEDES Spalte | Index | Internes Feld |
|--------------|-------|---------------|
| H/P | 1 | record_type |
| PRICAT | 2 | message_type |
| VedesArtikelnummer | 6 | artikel_nr |
| EANUPC | 10 | ean |
| Artikelbezeichnung | 13 | bezeichnung |
| LieferantGLN | 26 | lieferant_gln |
| LieferantID | 27 | lieferant_vedes_id |
| Lieferantname | 28 | lieferant_name |
| HerstellerGLN | 30 | hersteller_gln |
| HerstellerID | 31 | hersteller_vedes_id |
| Herstellername | 32 | hersteller_name |
| ArtikelnummerDesHerstellers | 33 | hersteller_artikel_nr |
| UVPE | 34 | uvp |
| GNP_Lieferant | 35 | ek_preis |
| MWST | 39 | mwst_schluessel |
| MarkeText | 52 | marke |
| Gewicht | 64 | gewicht |
| Bilderlink | 95 | bild_url |
| Grunddatentext | 97 | langtext |
| Warnhinweise | 100 | warnhinweise |

### 4.3 Elena-CSV-Format

Basierend auf `mapping.php`:

```
Artikelnummer;MPN;GTIN/EAN;Kurzbezeichnung;Verkaufspreis;Grundnettopreis;...
```

**Delimiter:** Semikolon (`;`)  
**Encoding:** UTF-8  
**Escape:** `\\`  
**Enclosure:** `"`

### 4.4 XLSX-Export Format

**Dateiname:** `{lieferant_vedes_id}_stammdaten_uebersicht.xlsx`

**Sheet 1: Übersicht**
| Typ | Kurzbezeichnung | GLN |
|-----|-----------------|-----|
| Lieferant | LEGO Spielwaren GmbH | 4023017000005 |
| Hersteller | LEGO Spielwaren GmbH | 4023017000005 |
| Marke | LEGO® | 4023017000005_1 |
| Marke | LEGO® Icons | 4023017000005_2 |

---

## 5. Ablaufdiagramm POC

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Lieferant: LEGO Spielwaren GmbH (1872)                   │  │
│  │  GLN: 4023017000005                                       │  │
│  │  Letzte Konvertierung: 2025-01-15 14:30                   │  │
│  │                                          [Verarbeite]     │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ Klick "Verarbeite"
┌─────────────────────────────────────────────────────────────────┐
│                        BACKEND                                   │
│                                                                  │
│  1. ┌─────────────────────────────────────┐                     │
│     │ FTP Download PRICAT                 │                     │
│     │ pricat_1872_Lego_Spielwaren_GmbH.csv│                     │
│     └─────────────────────────────────────┘                     │
│                              │                                   │
│  2. ┌─────────────────────────────────────┐                     │
│     │ Parse PRICAT CSV                    │                     │
│     │ - Extrahiere Lieferant             │                     │
│     │ - Extrahiere Hersteller            │                     │
│     │ - Extrahiere Marken                │                     │
│     │ - Extrahiere Artikel               │                     │
│     └─────────────────────────────────────┘                     │
│                              │                                   │
│  3. ┌─────────────────────────────────────┐                     │
│     │ Update DB                           │                     │
│     │ - Upsert Lieferant                 │                     │
│     │ - Upsert Hersteller                │                     │
│     │ - Upsert Marken (mit GLN_evendo)   │                     │
│     └─────────────────────────────────────┘                     │
│                              │                                   │
│  4. ┌─────────────────────────────────────┐                     │
│     │ Konvertiere zu Elena-CSV            │                     │
│     │ - Mapping PRICAT → Elena           │                     │
│     │ - Schreibe CSV                     │                     │
│     └─────────────────────────────────────┘                     │
│                              │                                   │
│  5. ┌─────────────────────────────────────┐  ◀── PARALLEL       │
│     │ Download Bilder                     │                     │
│     │ - Async/ThreadPool                 │                     │
│     │ - Speichern in images/{id}_{name}/ │                     │
│     └─────────────────────────────────────┘                     │
│                              │                                   │
│  6. ┌─────────────────────────────────────┐                     │
│     │ Erstelle XLSX Übersicht             │                     │
│     │ - Lieferant                        │                     │
│     │ - Hersteller                       │                     │
│     │ - Marken                           │                     │
│     └─────────────────────────────────────┘                     │
│                              │                                   │
│  7. ┌─────────────────────────────────────┐                     │
│     │ FTP Upload                          │                     │
│     │ - CSV → /{startdir}/               │                     │
│     │ - Bilder → /{startdir}/images/     │                     │
│     │ - XLSX → /{startdir}/              │                     │
│     └─────────────────────────────────────┘                     │
│                              │                                   │
│  8. ┌─────────────────────────────────────┐                     │
│     │ Trigger Elena Import                │                     │
│     │ GET getData.php?startdir=1872_lego │                     │
│     │     &importfile=...csv             │                     │
│     │     &debuglevel=1                  │                     │
│     └─────────────────────────────────────┘                     │
│                              │                                   │
│  9. ┌─────────────────────────────────────┐                     │
│     │ Update letzte_konvertierung         │                     │
│     └─────────────────────────────────────┘                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND: Status "Erfolgreich verarbeitet" / Fehlermeldung     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 6. Frontend-Mockup

```
╔════════════════════════════════════════════════════════════════╗
║  PRICAT Converter                                              ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  Aktive Lieferanten                                            ║
║  ─────────────────────────────────────────────────────────────║
║                                                                ║
║  ┌──────────────────────────────────────────────────────────┐ ║
║  │ VEDES-ID: 0000001872                                      │ ║
║  │ Name: LEGO Spielwaren GmbH                                │ ║
║  │ GLN: 4023017000005                                        │ ║
║  │ FTP-Dir: 1872_lego                                        │ ║
║  │ Letzte Konvertierung: 2025-01-15 14:30:22                │ ║
║  │                                                           │ ║
║  │                                    [ Verarbeite ]         │ ║
║  └──────────────────────────────────────────────────────────┘ ║
║                                                                ║
║  ┌──────────────────────────────────────────────────────────┐ ║
║  │ VEDES-ID: 0000001745                                      │ ║
║  │ Name: Ravensburger Spieleverlag GmbH                      │ ║
║  │ GLN: 4005556000005                                        │ ║
║  │ FTP-Dir: 1745_ravensburger                                │ ║
║  │ Letzte Konvertierung: -                                   │ ║
║  │                                                           │ ║
║  │                                    [ Verarbeite ]         │ ║
║  └──────────────────────────────────────────────────────────┘ ║
║                                                                ║
║  ─────────────────────────────────────────────────────────────║
║  Status: Bereit                                                ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

---

## 7. API-Endpoints (POC)

| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | `/` | Frontend (HTML) |
| GET | `/api/lieferanten` | Liste aktiver Lieferanten |
| POST | `/api/lieferanten/{id}/verarbeite` | Starte Verarbeitung |
| GET | `/api/lieferanten/{id}/status` | Status der Verarbeitung |

---

## 8. Testdaten

### 8.1 Vorhandene Testdatei
`pricat_1872_Lego_Spielwaren_GmbH_0.csv` (954 Zeilen, ~953 Artikel)

### 8.2 Erwartete Ergebnisse
- 1 Lieferant: LEGO Spielwaren GmbH
- 1 Hersteller: LEGO Spielwaren GmbH
- n Marken: LEGO®, LEGO® Icons, LEGO® Creator, etc.
- ~953 Artikel in Elena-CSV
- ~953 Bilder heruntergeladen

---

## 9. Erfolgskriterien POC

| # | Kriterium | Messung |
|---|-----------|---------|
| 1 | PRICAT erfolgreich geparst | Alle Zeilen verarbeitet |
| 2 | DB-Tabellen gefüllt | Lieferant/Hersteller/Marken vorhanden |
| 3 | Elena-CSV erstellt | Datei valide, korrekte Spalten |
| 4 | Bilder heruntergeladen | Alle URLs abgerufen, Dateien vorhanden |
| 5 | XLSX erstellt | Datei enthält alle Stammdaten |
| 6 | FTP-Upload erfolgreich | Dateien auf Ziel-FTP vorhanden |
| 7 | Elena-Import getriggert | HTTP 200 von getData.php |

---

## 10. Risiken & Mitigationen

| Risiko | Wahrscheinlichkeit | Impact | Mitigation |
|--------|-------------------|--------|------------|
| VEDES-FTP nicht erreichbar | Mittel | Hoch | Manuelle Datei-Upload-Option |
| Bild-URLs ungültig/404 | Hoch | Mittel | Fehlertolerantes Download mit Logging |
| Encoding-Probleme CSV | Mittel | Mittel | Encoding-Detection, Fallback UTF-8 |
| Elena-Import schlägt fehl | Niedrig | Hoch | Response-Analyse, Retry-Option |

---

## 11. Nächste Schritte nach POC

1. **Code-Review & Refactoring**
2. **Fehlerbehandlung verbessern**
3. **Logging implementieren**
4. **V1-Features planen** (siehe PRD_V1.md)
