# Changelog - PRD-001 PRICAT Converter

Alle Änderungen am PRICAT Converter Modul.

---

## [Unreleased]

### Changed

- **Route umbenannt:** `/lieferanten` → `/pricat-converter`
  - Konsistent mit Dashboard-Kachel "PRICAT Converter"
  - Template umbenannt: `index.html` → `pricat_converter.html`
  - Alle `url_for()`-Referenzen aktualisiert
  - Modul-Datenbank-Eintrag `route_endpoint` auf `main.pricat_converter` geändert
  - Grund: Die Route `/lieferanten` wird jetzt für die allgemeine Lieferanten-Stammdatenverwaltung benötigt

### Added

- PRICAT Admin: Neue Card "Bild-Download Einstellungen" mit Link zu Systemeinstellungen
- Deep-Link `/admin/settings#storage` führt direkt zum Storage-Tab

---

## [1.0.0] - 2025-12-06

### Completed Tasks

| Task | Beschreibung |
|------|--------------|
| Task 1 | FTP Port-Konfiguration - Separate Ports für VEDES und Elena FTP |
| Task 2 | Admin-Seite - Admin-Panel mit FTP-Tests und Health-Checks |
| Task 3 | Benutzer-Authentifizierung - Flask-Login mit Rollen |
| Task 4 | VEDES_ID ohne Nullen - Führende Nullen entfernen |
| Task 5 | Lieferanten-Sync - FTP-Scan und automatische Anlage |
| Task 6 | Base64-Passwörter - FileZilla-kompatible Passwörter |
| Task 7 | Lieferanten-Filter - Filter und Toggle-Button |
| Task 8 | Artikel-Anzahl & FTP Check - Zählung und Download bei Änderung |
| Task 9 | Toast-Meldungen - Bootstrap Toasts statt Alert-Boxen |
| Task 10 | Config Import/Export - JSON Export/Import |
| Task 11 | S3 Storage - S3-kompatibler Objektspeicher |
| Task 12 | PostgreSQL/MariaDB - Datenbank-agnostische Konfiguration |
| Task 13 | Flask-Migrate - Automatische Schema-Migrationen |
| Task 14 | Flask-Admin - DB-Verwaltung unter /db-admin |

### Added

- PRICAT Parser für VEDES CSV-Format
- Elena Exporter für Ziel-CSV
- Async Image Downloader
- FTP Service für Up-/Download
- Import Trigger für Elena getData.php
- Lieferant, Hersteller, Marke Models
- Lieferanten-Übersicht mit Filter
- Verarbeitungs-Status-Anzeige

---

## [0.1.0] - 2025-12-04

### Added

- Initiale Projektstruktur
- Flask App Factory
- Basis-Models (Lieferant, Hersteller, Marke, Config)
- Seed-Command für Testdaten
