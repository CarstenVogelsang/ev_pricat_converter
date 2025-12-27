# Changelog - PRD-006 Kunden-Dialog

Alle Änderungen am Modul "Kunden-Dialog" werden hier dokumentiert.

Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

## [Unreleased]

### Added

- **Hilfetexte für Dialog-Modul:** 8 neue Hilfetext-Einträge (PRD-005 Pattern)
  - `dialog.index.uebersicht` - Fragebogen-Übersicht
  - `dialog.detail.fragen` - Fragenübersicht
  - `dialog.detail.version` - Versionierung erklärt
  - `dialog.detail.teilnehmer` - Teilnehmer-Status
  - `dialog.form.fragen_editor` - Fragen-Editor Hilfe
  - `dialog.teilnehmer.liste` - Teilnehmer-Liste
  - `dialog.teilnehmer.einladung` - Einladungen versenden
  - `dialog.auswertung.uebersicht` - Auswertung erklärt

### Changed

- **Aktionen horizontal positioniert:** Neue UI-Konvention für Detail-Seite
  - Aktionen-Card aus Sidebar entfernt
  - Horizontale Aktionsleiste unter dem Seitentitel
  - Primäre Aktionen (Bearbeiten, Aktivieren, Teilnehmer) als einzelne Buttons
  - Sekundäre Aktionen (Neue Version, Archivieren) im Dropdown "Weitere"
  - Bessere Sichtbarkeit und schnellerer Zugriff
  - Datei: `dialog_admin/detail.html`

---

## [1.4.1] - 2025-12-24

### Changed

- **Anrede-Refactoring:** Anrede vom Kunden zum User verschoben (personenbezogen)
  - `anrede` (herr/frau/divers) ist jetzt am **User** statt am Kunden
  - `kommunikation_stil` am User kann den Kunde-Standard überschreiben
  - Neue Property: `kunde.effektiver_kommunikation_stil` (User-Präferenz > Kunde-Default)
  - Briefanrede-Logik nutzt jetzt `hauptbenutzer.anrede`
  - Fallback "firma" wenn kein User/Anrede gesetzt
  - Migration: `941599ad1756` (anrede, kommunikation_stil zu User)

### Fixed

- **Preview-Bug:** Briefanrede in E-Mail-Template-Vorschau zeigt jetzt korrekte Kundendaten
  - Problem: sample_context-Werte wurden von Defaults überschrieben
  - Lösung: Dict-Merge-Reihenfolge korrigiert (Defaults zuerst, context zuletzt)

---

## [1.4.0] - 2025-12-24

### Added

- **Anrede/Briefanrede-System:** Personalisierte Anreden für E-Mail-Templates
  - Neues Model: `LookupWert` - Generische Key-Value-Tabelle für erweiterbare Konfiguration
  - Kunde-Feld: `kommunikation_stil` (förmlich/locker) als Firmen-Standard
  - Neue Properties: `briefanrede`, `briefanrede_foermlich`, `briefanrede_locker`
  - Unterschiedliche Namenslogik pro Anrede-Typ:
    - Herr/Frau: Nachname → "Sehr geehrter Herr Müller"
    - Divers: Vorname → "Hallo Alex" / "Guten Tag Alex Müller"
    - Firma: Neutral → "Sehr geehrte Damen und Herren"
  - Neue E-Mail-Platzhalter: `{{ briefanrede }}`, `{{ briefanrede_foermlich }}`, `{{ briefanrede_locker }}`
  - Kunde-Formular: Kommunikationsstil-Dropdown (Firmen-Standard)
  - Benutzer-Formular: Anrede + Kommunikationsstil (User-spezifisch)
  - E-Mail-Template-Vorschau: Zeigt Briefanrede mit echten Kundendaten
  - Seed-Daten: 8 Anrede-Patterns (4 förmlich + 4 locker)
  - Migration: `fcd085ac4338` (LookupWert-Tabelle, kommunikation_stil zu Kunde)

---

## [1.3.0] - 2025-12-23

### Added

- **Fragebogen-Versionierung:** Versionskette für Fragebögen mit Archivierung
  - Neue Felder: `vorgaenger_id`, `version_nummer`, `archiviert`, `archiviert_am`
  - Self-referential FK für Versionskette: V1 → V2 → V3
  - Nur neueste Version kann dupliziert werden (Prüfung in Service + UI)
  - Archivierung statt Löschung (Soft-Delete)
  - Index-Seite: Toggle "Archivierte anzeigen" mit Badge-Counter
  - Detail-Seite: Version-Card mit Vorgänger/Nachfolger-Links
  - Neue Properties: `ist_neueste_version`, `version_kette`, `is_archiviert`
  - Neue Service-Methoden: `archiviere_fragebogen()`, `dearchiviere_fragebogen()`
  - Neue Routes: `POST /admin/dialog/<id>/archivieren`, `POST /admin/dialog/<id>/dearchivieren`
  - Audit-Log: `fragebogen_archiviert`, `fragebogen_dearchiviert`
  - Migration: `dd224207bda2` (vorgaenger_id, version_nummer, archiviert, archiviert_am)

### Changed

- **Duplizieren:** Setzt jetzt `vorgaenger_id` und erhöht `version_nummer`
  - Duplizieren-Button deaktiviert für ältere Versionen (Hinweis auf neueste Version)
  - Neue Version zeigt Vorgänger-Link

---

## [1.2.0] - 2025-12-23

### Added

- **Einzelauswertung für Teilnehmer:** Dropdown-Filter in der Auswertungsseite
  - Wähle einzelne Teilnehmer aus, um alle ihre Antworten zu sehen
  - Anzeige der Änderungen an Prefill-Daten mit farblicher Hervorhebung
  - Badge `(✎ X Änderungen)` im Dropdown zeigt Teilnehmer mit Änderungen
  - Geänderter Original-Wert wird durchgestrichen angezeigt
  - Neue Service-Methode: `get_teilnehmer_auswertung()`
  - Route: `GET /admin/dialog/<id>/auswertung?teilnehmer=<tid>`

- **Fragebogen duplizieren:** Kopier-Funktion für Fragebögen
  - Button "Duplizieren" in der Fragebogen-Detailseite (für alle Status)
  - Modal zur Eingabe des neuen Titels (Default: "Kopie von {Original}")
  - Kopiert: Titel, Beschreibung, JSON-Definition mit allen Fragen
  - Kopiert NICHT: Teilnehmer, Antworten (startet leer)
  - Kopie wird immer als ENTWURF erstellt
  - Neue Service-Methode: `duplicate_fragebogen()`
  - Route: `POST /admin/dialog/<id>/duplicate`
  - Audit-Log: `fragebogen_dupliziert`

---

## [1.1.0] - 2025-12-16

### Added

- **Admin-Sidebar:** Link zu "Kunden-Dialog" in der Admin-Navigation hinzugefügt
- **Kunden-Detailseite:** User-Account-Card mit:
  - Status-Anzeige (User vorhanden / nicht vorhanden)
  - "Benutzer erstellen"-Button mit Modal-Formular
  - "Zugangsdaten senden"- und "Neues Passwort"-Buttons
- **Brevo Rate Limiting:** Schutz vor Überschreitung des täglichen E-Mail-Limits
  - Neue Config-Einträge: `brevo_daily_limit`, `brevo_emails_sent_today`, `brevo_last_reset_date`
  - Automatischer Reset um Mitternacht
  - `QuotaExceededError` Exception bei Limit-Überschreitung
  - `get_quota_info()` Methode für Status-Abfrage
- **Admin-Settings:** Brevo-Quota-Anzeige mit:
  - Progress-Bar für verbrauchtes Limit
  - Farbwechsel bei niedrigem (<10%) oder erschöpftem Limit
  - Konfigurierbares tägliches Limit (Standard: 300 für Free Plan)

---

## [1.0.0] - 2025-12-15

### Added

- **Datenmodelle**
  - `PasswordToken` für einmalige Passwort-Anzeige
  - `Fragebogen` mit JSON-Definition für Fragen
  - `FragebogenTeilnahme` mit Magic-Link-Token
  - `FragebogenAntwort` für flexible Antwort-Speicherung
  - `Kunde.user_id` für User-Zuordnung

- **Services**
  - `BrevoService` für E-Mail-Versand via REST API
  - `PasswordService` für User-Erstellung und Token-Management
  - `FragebogenService` für CRUD und Auswertung

- **Routes**
  - `passwort_bp` (`/passwort/`) - Passwort-Anzeige
  - `dialog_bp` (`/dialog/`) - Kunden-Portal und Magic-Link
  - `dialog_admin_bp` (`/admin/dialog/`) - Admin-Verwaltung
  - Erweiterung `kunden_bp` - User-Erstellung für Kunden

- **Fragen-Typen**
  - `single_choice` - Einzelauswahl
  - `multiple_choice` - Mehrfachauswahl
  - `skala` - Bewertungsskala
  - `text` - Freitext
  - `ja_nein` - Ja/Nein

- **Templates**
  - 3 Passwort-Templates (reveal, invalid, expired)
  - 7 Dialog-Templates (index, fragebogen, fragebogen_magic, geschlossen, abgeschlossen, danke, invalid)
  - 5 Admin-Templates (index, form, detail, teilnehmer, auswertung)

- **Konfiguration**
  - Brevo API-Key und Absender-Einstellungen
  - Portal-Basis-URL
