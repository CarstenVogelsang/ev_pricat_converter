# PRICAT Converter

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

## Erledigte Tasks

### Task 1: FTP Port-Konfiguration
- Neue Config-Einträge: `vedes_ftp_port` und `elena_ftp_port`
- Standard-Port 21 als Fallback

### Task 2: Admin-Seite mit Verbindungstests
- Blueprint `admin_bp` unter `/admin/*`
- Buttons für VEDES/Elena FTP Verbindungstests
- Health-Check Endpoint `/api/health`

### Task 3: Benutzer-Authentifizierung
- Flask-Login mit Rollen: `admin`, `sachbearbeiter`
- Login-Schutz für alle Routes
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

## Offene Tasks

*Aktuell keine offenen pricat-spezifischen Tasks.*

---

## Technische Details

### PRICAT Format
- **Delimiter:** Semikolon (`;`)
- **Encoding:** Latin-1 oder UTF-8
- **Header:** Zeile beginnt mit `H;PRICAT;...`
- **Daten:** Zeilen beginnen mit `P;PRICAT;...`
- **143 Spalten**

### Elena Zielformat
- CSV mit Semikolon-Delimiter, UTF-8
- Felder: articleNumber, articleName, priceEK, etc.
- Bilder: Name Bild 1-15

### Datenbank-Models
- **Lieferant:** gln, vedes_id, kurzbezeichnung, aktiv, ftp_quelldatei, elena_startdir
- **Hersteller:** gln, vedes_id, kurzbezeichnung
- **Marke:** kurzbezeichnung, gln_evendo, hersteller_id (FK)
- **Config:** key-value Store
- **User:** email, password_hash, vorname, nachname, rolle, aktiv
