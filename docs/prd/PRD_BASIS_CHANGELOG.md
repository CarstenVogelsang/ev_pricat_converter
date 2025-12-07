# Changelog - Basis-Plattform

Alle wichtigen Änderungen an der **Basis-Plattform** (nicht modulspezifisch) werden hier dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

> **Hinweis:** Modul-spezifische Änderungen werden in den jeweiligen PRD-Dokumenten unter `module/` dokumentiert.

---

## [Unreleased]

### Added

- Dokumentationsstruktur reorganisiert: `docs/prd/` mit modularen PRDs

### Changed

- PRD_BASIS_MVP.md enthält jetzt Tech-Stack, Projektstruktur, Basis-DB-Schema

---

## [0.2.0] - 2025-12-06

### Added

- Flask-Admin für Datenbank-Verwaltung unter `/db-admin`
- Flask-Migrate für automatische Schema-Migrationen
- PostgreSQL und MariaDB Support via DATABASE_URL
- S3-kompatibler Objektspeicher für Dateipersistenz
- Config Import/Export als JSON
- Dashboard mit rollenbasiertem App-Zugriff
- Branding-System und öffentliche Landing Page

---

## [0.1.0] - 2025-12-04

### Added

- Flask Application Factory mit SQLAlchemy
- Benutzer-Authentifizierung mit Flask-Login
- User Model mit Rollen: `admin`, `sachbearbeiter`
- Config Model (Key-Value Store)
- Admin-Panel mit Health-Check
- Toast-Meldungen statt Alert-Boxen

### Infrastructure

- Coolify Deployment mit nixpacks
- SQLite als Standard-Datenbank
- uv als Package Manager
