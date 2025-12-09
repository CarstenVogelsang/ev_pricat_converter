# Changelog - Basis-Plattform

Alle wichtigen Änderungen an der **Basis-Plattform** (nicht modulspezifisch) werden hier dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

> **Hinweis:** Modul-spezifische Änderungen werden in den jeweiligen PRD-Dokumenten unter `module/` dokumentiert.

---

## [Unreleased]

### Added

- **Systemeinstellungen-Seite** `/admin/settings` mit 4 Tabs:
  - API & Services (Firecrawl API-Key, Credit-Kosten)
  - FTP-Konfiguration (VEDES + Elena mit Test-Buttons)
  - Storage (S3-Konfiguration, Bild-Download-Einstellungen)
  - Import/Export (JSON Export/Import, Config-Übersicht mit 24 Einträgen)
- Password-Toggle für sensible Felder (API-Keys, Passwörter)
- URL-Hash-Navigation für direkten Tab-Zugriff (`/admin/settings#storage`)
- Dokumentationsstruktur reorganisiert: `docs/prd/` mit modularen PRDs
- **API-Kostenabrechnung (G7):** Neues Model `KundeApiNutzung` für Tracking von API-Calls
- Abrechnungsseite unter `/abrechnung/` für User-spezifische API-Nutzung
- Navigation: "API-Abrechnung" im User-Dropdown-Menü
- Config: `firecrawl_credit_kosten` für konfigurierbaren Euro-Preis pro Credit

### Changed

- PRD_BASIS_MVP.md enthält jetzt Tech-Stack, Projektstruktur, Basis-DB-Schema
- Admin-Sidebar: Neuer Link "Systemeinstellungen" unter "Einstellungen"

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
