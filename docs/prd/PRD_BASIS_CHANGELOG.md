# Changelog - Basis-Plattform

Alle wichtigen Änderungen an der **Basis-Plattform** (nicht modulspezifisch) werden hier dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

> **Hinweis:** Modul-spezifische Änderungen werden in den jeweiligen PRD-Dokumenten unter `module/` dokumentiert.

---

## [Unreleased]

### Added

- **Globale Medienverwaltung:** Neues `Medium`-Model für plattformweite Medienbibliothek
  - Unterstützt Datei-Uploads und externe URLs (z.B. Unsplash)
  - Typen: Banner, Bild, Logo, Dokument
  - Model: `app/models/medium.py` mit `MediumTyp` Enum
  - Factory-Methoden: `create_from_upload()`, `create_from_url()`
  - Migration: `bdb466fd8e04_add_medium_model_for_global_media_library.py`
  - Export: `Medium`, `MediumTyp` in `app/models/__init__.py`
  - Nutzung: Aktuell im Mailing-Editor für Banner- und Bild-Auswahl

- **BrandingService: Legal-URLs für E-Mail-Footer:** (PRD-013 Phase 5)
  - Neue Felder in `BrandingConfig`: `impressum_url`, `datenschutz_url`, `kontaktformular_url`
  - Config-Keys: `betreiber_impressum_url`, `betreiber_datenschutz_url`, `betreiber_kontaktformular_url`
  - Neue Factory-Funktion: `get_branding_service()` für Singleton-Zugriff
  - Betreiber-Admin erweitert: Eingabefelder für Impressum- und Datenschutz-URLs
  - Dateien: `branding_service.py`, `admin.py`, `betreiber.html`

- **Kunde-Model erweitert:** Handelsregister und USt-ID (PRD-013 Phase 5)
  - Neue Felder: `handelsregister_info` (z.B. "HRB 94083 B, AG Charlottenburg"), `umsatzsteuer_id` (z.B. "DE812373677")
  - Migration: `008c5f01f9c7_add_mailing_module_prd_013.py`
  - Dateien: `kunde.py`

- **Stammdaten-CRUD für Partner & Marken:** Vollständige CRUD-Administration für Geschäftspartner
  - **Lieferanten:** `/admin/lieferanten` mit Liste, Formular, Löschen
    - Felder: Kurzbezeichnung, VEDES-ID (unique), GLN (optional), Aktiv-Status
    - PRICAT-spezifische Felder (FTP-Pfade, ELENA-URLs) werden nur angezeigt, nicht editiert
    - PRICAT-Verwaltung erfolgt weiterhin über `/admin/pricat/`
  - **Hersteller:** `/admin/hersteller` mit Liste, Formular, Löschen
    - Felder: Kurzbezeichnung, GLN (unique, Pflicht), VEDES-ID (optional)
    - Anzeige der zugehörigen Marken im Formular
    - Kaskaden-Löschung: Löscht auch zugehörige Marken
  - **Marken:** `/admin/marken` mit Liste, Formular, Löschen
    - Felder: Kurzbezeichnung, Hersteller (Dropdown)
    - GLN evendo wird automatisch generiert: `{Hersteller.GLN}_{laufende_nummer}`
  - Neue Templates: `lieferant_form.html`, `hersteller.html`, `hersteller_form.html`, `marken.html`, `marke_form.html`
  - Neue Routes in `admin.py`: `lieferant_form()`, `lieferant_delete()`, `hersteller()`, `hersteller_form()`, `hersteller_delete()`, `marken()`, `marke_form()`, `marke_delete()`

- **Zentraler Tabler Icon Picker:** Wiederverwendbare Icon-Auswahl-Komponente
  - Offcanvas-Dialog mit ~5000 Tabler Icons
  - Suchfunktion für schnelle Icon-Suche
  - Live-Preview im Input-Feld
  - Jinja2-Macro `icon_input()` für konsistente Integration
  - Unterstützt Icons mit und ohne `ti-` Prefix (`strip_prefix` Parameter)
  - Eingebunden in: Branchen, Branchenrollen, Lookup-Werte, Module
  - Dateien: `macros/icon_picker.html`, `js/icon-picker.js`, `js/tabler-icons-list.json`

- **UI-Konvention: Aktionen-Positionierung:** Dokumentiert in PRD_BASIS_MVP.md
  - Aktionen horizontal unter dem Seitentitel statt in Sidebar
  - Primäre Aktionen als einzelne Buttons
  - Sekundäre/destruktive Aktionen im Dropdown-Menü
  - Pattern für alle Detail-Seiten der Plattform

### Changed

- **Seeding-Konzept überarbeitet:** 3-Stufen-System für granulare Kontrolle
  - Neuer Befehl `flask seed-essential`: Nur Rollen + 1 Admin-User aus ENV (Pflicht für Login)
  - `flask seed` umbenannt zu `flask seed-stammdaten`: Nur Stammdaten (Branchen, Verbände, Hilfetexte)
  - Neuer Befehl `flask seed-demo`: Demo-Daten für Entwicklung (LEGO, e-vendo Users, Test-Kunden)
  - LEGO-Lieferant verschoben: Von `seed` nach `seed-demo`
  - Neue ENV-Variable `INITIAL_ADMIN_EMAIL` (Pflicht für `seed-essential`)
  - Alte Befehle `flask seed` und `flask seed-users` bleiben als Kompatibilitäts-Aliase
  - Fake-Verbände "Spielwaren-Ring" und "expert" entfernt aus Seed-Daten
  - Dateien: `app/__init__.py`, `CLAUDE.md`, `.env.example`

- **Stammdaten-Gruppe umbenannt:** "PRICAT-Stammdaten" → "Partner & Marken"
  - Icon geändert: `ti-file-spreadsheet` → `ti-building-store`
  - Kachel-Beschreibungen aktualisiert (ohne PRICAT-Bezug)
  - PRD-Link entfernt (keine direkte PRD-Zuordnung für allgemeine Stammdaten)

- **Test-E-Mail Button in Vorschaumodus verschoben:** Verbesserter Workflow
  - Button von Bearbeitungsmodus in Vorschaumodus verschoben
  - Test-E-Mail nur verfügbar wenn Kunde für Vorschau ausgewählt
  - Empfänger wählbar: An Kunden senden oder an sich selbst (Admin)
  - Verwendet echte Kundendaten statt Beispieldaten für Platzhalter
  - Dateien: `email_template_form.html`, `email_template_preview.html`, `admin.py`

### Fixed

- **CSRF-Token in Lookup-Werte Admin:** Fehlende CSRF-Tokens hinzugefügt
  - Delete-Formular: Token-Input hinzugefügt
  - AJAX-Reorder: X-CSRFToken Header in Fetch-Request
  - Datei: `templates/administration/lookup_werte.html`

### Added

- **System-Fonts für E-Mail-Kompatibilität:** Arial, Times New Roman, Courier New
  - 3 System-Fonts hinzugefügt, die in E-Mail-Clients zuverlässig funktionieren
  - System-Fonts mit ✉-Symbol im Quill-Dropdown markiert (z.B. "Courier New ✉")
  - `is_system` Flag in Font-Konfiguration unterscheidet Web-/System-Fonts
  - System-Fonts werden nicht von Google Fonts geladen (sind lokal verfügbar)
  - Font-CSS wird automatisch in E-Mail-Templates injiziert
  - BrandingService: Neue Methode `get_font_css_for_email()` generiert CSS für Quill-Klassen
  - Kompakte Zeilenabstände: CSS-Fix für `<p>`-Margins in E-Mail-Signaturen
  - Dateien: `branding_service.py`, `betreiber.html`, `email_template_service.py`

- **Dual-Font-System für Branding:** Sekundär-Font für Überschriften und Akzente
  - Neues Dropdown für Sekundär-Font in Betreiber/Branding (optional)
  - Quill-Editor zeigt nur ausgewählte Fonts (Primär + Sekundär) – nicht alle 10 Fonts
  - Dynamische Font-Whitelist erzwingt Corporate Identity in Rich-Text-Inhalten
  - Neue Config-Keys: `brand_secondary_font_family`, `brand_secondary_font_weights`
  - BrandingService: Neue Methode `get_selected_fonts()` liefert ausgewählte Fonts
  - Multi-Font-Support in `get_google_fonts_url()` – lädt beide Fonts gleichzeitig
  - Hilfetext: `admin.betreiber.branding.secondary_font`
  - Dateien: `branding_service.py`, `admin.py`, `betreiber.html`

- **Google Fonts für Branding:** Systemweite Schriftarten-Auswahl in Betreiber/Branding
  - 7 Google Fonts verfügbar: Inter, Poppins, Roboto, Open Sans, Lato, Merriweather, JetBrains Mono
  - Live-Vorschau mit verschiedenen Font-Gewichten (Normal, Medium, Semibold, Bold)
  - Dynamisches Laden via Google Fonts CDN
  - Global auf gesamtes Portal angewendet (html/body)
  - Quill-Editor: Font-Auswahl in E-Mail-Signatur-Toolbar
  - Neue Config-Keys: `brand_font_family`, `brand_font_weights`
  - BrandingService: Neue Methode `get_google_fonts_url()`
  - Hilfetext: `admin.betreiber.branding.font`
  - Dateien: `branding_service.py`, `admin.py`, `betreiber.html`, `base.html`

- **Betreiber / Branding System:** Erweiterte Branding-Seite mit Betreiber-Konzept
  - Sidebar umbenannt: "Branding" → "Betreiber / Branding"
  - Neues Konzept: Ein Kunde als "Betreiber" (Systemkunde) liefert CI für das gesamte Portal
  - Dropdown-Auswahl: Kunde mit CI-Daten als Betreiber festlegen
  - Live-CI-Vorschau: Logo, Farben beim Auswählen eines Kunden
  - "Als Betreiber übernehmen" setzt `ist_systemkunde=True` und übernimmt CI
  - E-Mail-Signatur-Editor: WYSIWYG (TinyMCE) für `Kunde.email_footer`
  - Platzhalter `{{ footer | safe }}` nutzt Betreiber-Footer in E-Mail-Templates
  - Neue Routes: `GET/POST /admin/betreiber`, `POST /admin/betreiber/set`, `POST /admin/betreiber/footer`
  - Backwards-Kompatibilität: `/admin/branding` leitet auf `/admin/betreiber` weiter
  - Audit-Logging: `betreiber_gesetzt`, `email_footer_gespeichert`

- **E-Mail-Template-System:** Datenbankgestützte E-Mail-Templates mit CI/Branding
  - Neues Model `EmailTemplate` mit Jinja2-Platzhaltern (`{{ firmenname }}`, `{{ link }}`, etc.)
  - `EmailTemplateService` für Template-Rendering mit BrandingService-Integration
  - System-Branding (Logo, Primär-/Sekundärfarbe) wird automatisch eingefügt
  - Kunden-spezifischer Footer mit System-Kunde-Fallback
  - 4 Standard-Templates: `fragebogen_einladung`, `passwort_zugangsdaten`, `passwort_reset`, `test_email`
  - Admin-UI unter `/admin/email-templates`: Liste, Bearbeiten, Vorschau, Test-Versand
  - Neue `BrevoService`-Methoden: `send_with_template()`, `send_fragebogen_einladung_mit_template()`
  - Migration: `f5898ef9f836` (email_template, Kunde.email_footer, Kunde.ist_systemkunde)
  - Dokumentation: Templates in `flask seed` erstellt

- **Kundenname im Header:** Für Kunde-Benutzer wird im User-Dropdown zusätzlich die Firmierung angezeigt
  - Anzeige mit Gebäude-Icon unter der E-Mail-Adresse
  - Nur sichtbar für Benutzer mit `is_kunde = True` und zugeordnetem Kunden
  - Datei: `app/templates/base.html`

- **Brevo Test-E-Mail Funktionalität:** In Systemeinstellungen `/admin/settings`
  - User-Dropdown zur Auswahl des Empfängers (Auswahl wird gespeichert)
  - Test-E-Mail mit Zeitstempel, Absender-Adresse, Server-Info
  - "Status prüfen" Button zeigt API-Status, Konto-E-Mail, Plan und Credits
  - Neue Methoden in `BrevoService`: `send_test_email()`, `check_api_status()`
  - Neue Routes: `POST /admin/brevo/test`, `POST /admin/brevo/status`

- **Fragebogen Einladungs-Resend:** Auf `/admin/dialog/<id>/teilnehmer`
  - Neuer Resend-Button für jeden Teilnehmer (auch wenn bereits Einladung gesendet)
  - Neue Route: `POST /admin/dialog/<id>/teilnehmer/<tid>/resend`
  - Confirm-Dialog vor dem erneuten Senden

- **Audit-Logging für E-Mail-Versand:** Im Dialog-Modul
  - Erfolgreiche Einladungen: Aktion `einladung_gesendet` oder `einladung_erneut_gesendet`
  - Fehlgeschlagene Einladungen: Aktion `einladung_fehlgeschlagen`
  - Details enthalten: Fragebogen-Titel, E-Mail-Adresse, Kunde, Message-ID
  - Wichtigkeit: `mittel`

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

- **Hilfetexte-System (PRD-005):** Icon-Optimierung und Kontrast-Verbesserungen
  - Details siehe: `docs/prd/core/PRD-005-hilfetexte/CHANGELOG.md`
- PRD_BASIS_MVP.md enthält jetzt Tech-Stack, Projektstruktur, Basis-DB-Schema
- PRD_BASIS_MVP.md: Rollen-Abschnitt gekürzt, Verweis auf PRD_BASIS_RECHTEVERWALTUNG.md
- PRD_BASIS_MODULVERWALTUNG.md: Rechteverwaltungs-Referenz hinzugefügt
- Admin-Sidebar: Neuer Link "Systemeinstellungen" unter "Einstellungen"
- Admin-Sidebar: Neuer Link "Modulverwaltung" unter "Einstellungen"

### Fixed

- **Magic-Link CSRF-Exemption:** AJAX-Requests für Magic-Link-Routen waren durch CSRF-Schutz blockiert
  - `POST /dialog/t/<token>/antwort`: Antwort speichern
  - `POST /dialog/t/<token>/abschliessen`: Fragebogen abschließen
  - Lösung: `@csrf.exempt` Decorator, da Magic-Token bereits Authentifizierung ist

- **Dynamische Portal-URL im Dev-Modus:** E-Mail-Links zeigten auf Production statt localhost
  - Im Debug-Modus wird jetzt `request.host_url` verwendet (z.B. `http://localhost:5000`)
  - Im Production-Modus: Konfigurierte `portal_base_url` aus DB-Config
  - Betrifft: Fragebogen-Einladungen, Passwort-Links, Test-E-Mails

- **CSRF-Token in Dialog-Admin Templates:** Fehlende CSRF-Tokens hinzugefügt
  - `dialog_admin/detail.html`: Aktivieren- und Schließen-Formulare
  - `dialog_admin/teilnehmer.html`: Alle Formulare (Resend, Löschen, Hinzufügen, Alle einladen)

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
