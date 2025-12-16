# Changelog - PRD-006 Kunden-Dialog

Alle Änderungen am Modul "Kunden-Dialog" werden hier dokumentiert.

Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

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
