

# Changelog

Alle wichtigen Änderungen an diesem Projekt werden hier dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

---

## [Unreleased]

### Added
- Flask-Admin für Datenbank-Verwaltung unter `/db-admin` (Task 14)
- Flask-Migrate für automatische Schema-Migrationen (Task 13)
- PostgreSQL und MariaDB Support via DATABASE_URL (Task 12)
- S3-kompatibler Objektspeicher für Dateipersistenz (Task 11)
- Config Import/Export als JSON (Task 10)

### Changed
- Dokumentationsstruktur: `docs/modules/` für modulare Dokumentation
- `IMPLEMENTATION_PLAN.md` → `docs/modules/pricat-converter.md`

---

## [0.1.0] - 2025-12-04

### Added
- Flask Application Factory mit SQLAlchemy
- Benutzer-Authentifizierung mit Flask-Login (Task 3)
- Admin-Panel mit FTP-Verbindungstests (Task 2)
- Lieferanten-Synchronisation mit VEDES FTP (Task 5)
- Lieferanten-Filter (Aktiv/Inaktiv/Alle) (Task 7)
- Artikel-Anzahl und FTP Check pro Lieferant (Task 8)
- Toast-Meldungen statt Alert-Boxen (Task 9)
- FTP Port-Konfiguration (Task 1)
- Base64-kodierte Passwörter (Task 6)
- VEDES_ID ohne führende Nullen (Task 4)

### Models
- Lieferant, Hersteller, Marke
- Config (key-value Store)
- User mit Rollen (admin, sachbearbeiter)

### Infrastruktur
- Coolify Deployment mit nixpacks
- SQLite als Standard-Datenbank
