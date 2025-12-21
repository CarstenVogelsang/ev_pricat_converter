# Changelog - Basis-Plattform

Alle wichtigen Änderungen an der **Basis-Plattform** (nicht modulspezifisch) werden hier dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

> **Hinweis:** Modul-spezifische Änderungen werden in den jeweiligen PRD-Dokumenten unter `module/` dokumentiert.

---

## [Unreleased]

### Added

- **Brevo Test-E-Mail Funktionalität:** In Systemeinstellungen `/admin/settings`
  - User-Dropdown zur Auswahl des Empfängers (Auswahl wird gespeichert)
  - Test-E-Mail mit Zeitstempel, Absender-Adresse, Server-Info
  - "Status prüfen" Button zeigt API-Status, Konto-E-Mail, Plan und Credits
  - Neue Methoden in `BrevoService`: `send_test_email()`, `check_api_status()`
  - Neue Routes: `POST /admin/brevo/test`, `POST /admin/brevo/status`

- **PRD_BASIS_RECHTEVERWALTUNG.md:** Neue zentrale Dokumentation für Rechteverwaltung
  - Konsolidiert Inhalte aus CLAUDE.md, PRD_BASIS_MVP.md, PRD_BASIS_MODULVERWALTUNG.md
  - Dokumentiert Admin-Sonderrechte (immer Zugriff auf alle Module)
  - Erklärt zwei Rollensysteme: Benutzer-Rollen vs. Branchenrollen
  - API-Autorisierung mit Decorator-Übersicht
  - Implementierungshinweise für neue Module

- **UI-Konventionen in CLAUDE.md:** Dokumentation der Standard-UI-Elemente
  - Audit-Logging für alle Module
  - Hilfe-Button (i) für Enduser-Dokumentation
  - DEV-Button für Entwickler-PRD-Ansicht
  - Hilfetexte-System mit `bereich.seite.element` Format
- **Roadmap V2: PRD-Management in DB:** Konzept für Feature-Status-Tracking
  - Neue Datei: `docs/prd/roadmap/ROADMAP-V2-prd-management.md`
  - Hybride Lösung: PRDs in Git, Status in DB
  - Browser-basierte Feature-Verwaltung (geplant)
- **PRD-006: Kunden-Dialog Modul** - Fragebogen-System für Kundenbefragungen
  - Fragebogen-Erstellung mit JSON-Definition (5 Frage-Typen)
  - Magic-Link für Login-freien Zugang
  - User-Erstellung für Kunden mit sicherem Passwort-Versand via Brevo
  - Admin-Verwaltung mit Statistiken und Auswertung
  - Neues Modul `dialog` mit Typ KUNDENPROJEKT
  - 4 neue Config-Einträge für Brevo E-Mail-Service
  - Migration: `855ad509f342` (Fragebogen, Teilnahme, Antwort, PasswordToken, Kunde.user_id)
- **Branchenmodell V2:** 2-stufige Taxonomie mit Rollen-System
  - Hierarchie: Hauptbranchen (z.B. HANDEL) → Unterbranchen (z.B. Spielwaren)
  - Neue Models: `BranchenRolle`, `BrancheBranchenRolle`, `KundeBranchenRolle`
  - UUID-Feld für externe Datenintegration (unternehmensdaten.org)
  - 6 vordefinierte Rollen: Hersteller, Großhändler, Filialist, Einzelhandel (stationär/online/omnichannel)
  - Zulässigkeitsmatrix: Welche Rollen pro Branche erlaubt sind
  - Admin-UI: Master-Detail für Branchen (`/admin/branchen`)
  - Admin-UI: BranchenRollen-Verwaltung (`/admin/branchenrollen`)
  - Kunden-UI: Rollen-Modal nach Branche-Klick mit Checkbox-Auswahl
  - Kunden-UI: Rollen-Icons unter zugeordneten Branchen
- **Branchen-Import:** JSON-Import für Hauptbranchen mit Unterbranchen und Rollen
  - Format: Kompatibel mit unternehmensdaten.org Export
  - Upsert-Logik: Update bei existierender UUID, sonst Insert
  - Automatische Icon-Bereinigung (FontAwesome/Tabler Prefix entfernen)
  - Testdatei: `docs/testdaten/branchenkatalog_handwerk.json`
- **Hauptbranche für Kunden:** Hauptbranche-Zuordnung vor Unterbranche-Auswahl
  - Neues Feld `kunde.hauptbranche_id` (FK auf Hauptbranche)
  - Kunden-UI: Hauptbranche-Card mit Button-Auswahl (HANDEL, HANDWERK, ...)
  - Filter: Nur Unterbranchen der gewählten Hauptbranche werden angezeigt
  - API: `POST /kunden/<id>/hauptbranche` zum Setzen/Entfernen
  - Dokumentation: PRD_Branchenmodell_V2.md Section 9
- **Verbände Logo-Upload:** Logos können direkt im Admin-Dialog hochgeladen werden
  - Automatische Thumbnail-Erstellung (max. 100x100px) mit Pillow
  - Speicherort: `static/uploads/verbaende/`
  - Fallback auf externe Logo-URL
  - Geplant: Original-Speicherung auf S3
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
- **Audit-Log System (Basis-Modul):** Neues PRD für zentrales Logging
  - Dokumentiert in: `docs/prd/PRD_BASIS_LOGGING.md`
  - Neues Model: `AuditLog` für Ereignis-Tracking
  - Neues Model: `Modul` (minimal) für Modul-Referenzen
  - Admin-UI geplant: `/admin/logs` mit Filter und Export
  - DSGVO-konform: User-IDs bleiben bei Löschung erhalten
- **Modulverwaltung (Konsolidierung):** SubApp und Modul zu einheitlichem System zusammengeführt
  - Dokumentiert in: `docs/prd/PRD_BASIS_MODULVERWALTUNG.md`
  - Erweiterte `Modul`-Tabelle mit UI-Feldern (icon, color, color_hex, route_endpoint, sort_order)
  - Neues Model: `ModulZugriff` für rollenbasierte Zugriffssteuerung
  - 8 Module: 4 Basis (system, stammdaten, logging, auth) + 4 Dashboard (pricat, kunden, lieferanten, content)
  - Admin-UI: `/admin/module` mit Drag&Drop-Sortierung, Aktivierung/Deaktivierung, Rollenzugriff
  - Dashboard: Zeigt nur Module mit `zeige_dashboard=True` und passendem Rollenzugriff
  - Migration: Daten von SubApp/SubAppAccess übernommen, alte Tabellen entfernt
- **Hauptbranche Phase 2:** Lösch-Logik dokumentiert
  - PRD_Branchenmodell_V2.md Sections 9.7-9.10
  - UI: Nach Auswahl nur gewählte Hauptbranche anzeigen
  - Kaskaden-Löschung: Entfernt auch Unterbranche-Zuordnungen
  - Modal-Warnung vor dem Löschen
  - Audit-Log Integration

### Changed

- PRD_BASIS_MVP.md enthält jetzt Tech-Stack, Projektstruktur, Basis-DB-Schema
- PRD_BASIS_MVP.md: Rollen-Abschnitt gekürzt, Verweis auf PRD_BASIS_RECHTEVERWALTUNG.md
- PRD_BASIS_MODULVERWALTUNG.md: Rechteverwaltungs-Referenz hinzugefügt
- Admin-Sidebar: Neuer Link "Systemeinstellungen" unter "Einstellungen"
- Admin-Sidebar: Neuer Link "Modulverwaltung" unter "Einstellungen"

### Fixed

- **Dialog-Modul Admin-Zugriff:** Admin und Mitarbeiter wurden von `/dialog/` auf Landing Page umgeleitet
  - Route prüft jetzt auf `is_admin`/`is_mitarbeiter` für interne Ansicht
  - Neues Template `dialog/index_internal.html` zeigt alle Fragebögen mit Statistiken
  - Admin/Mitarbeiter sehen jetzt alle Fragebögen mit Fortschritts-Indikatoren
  - Kunden sehen weiterhin nur ihre zugewiesenen Fragebögen

### Removed

- **SubApp und SubAppAccess:** Durch Modul/ModulZugriff ersetzt
  - Tabellen `sub_app` und `sub_app_access` entfernt
  - Datei `app/models/sub_app.py` gelöscht
  - CLI-Command `flask migrate-modules` entfernt (Migration abgeschlossen)

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
