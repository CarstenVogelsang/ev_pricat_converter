# Changelog PRD-005 Hilfetexte

## [1.1.0] - 2025-12-25

### Geaendert

- **Icon-Vereinheitlichung:** `ti-info-circle` ueberall (Trigger + Modal)
  - Vorher: Trigger nutzte `ti-info-circle`, Modal nutzte `ti-help-circle`
  - Jetzt: Einheitlich `ti-info-circle` fuer konsistentes UI
- **Kontrast-Parameter:** Neuer `light` Parameter fuer farbige Header
  - `{{ help_icon('schluessel', light=true) }}` fuer weisse Icons auf dunklem Hintergrund
  - `text-white-50` statt `text-muted` auf farbigen Headern (bg-primary, bg-info)
- **E-Mail-Signatur Hilfetext:** Technische Erklaerung fuer `{{ footer | safe }}` hinzugefuegt
  - Was bedeutet `{{ }}`?
  - Was bedeutet `| safe`?
  - Hinweis, dass Platzhalter bereits in Templates vorhanden ist
- **Icon-Styling:** Unterstreichung entfernt (`text-decoration-none`)
- **Icon-Groesse:** Vergroessert mit `fs-5` fuer bessere Sichtbarkeit
- **Hover-Effekt:** Icon wechselt zu Info-Blau beim Ueberfahren mit der Maus
- **E-Mail-Signatur Hilfetext:** Vereinfacht - technischen Teil (`{{ footer | safe }}`) entfernt, benutzerfreundlicher formuliert
- **Seed-Logik:** Aktualisiert jetzt auch existierende Hilfetexte (nicht nur neue erstellen)
- **Text-Lesbarkeit:** CSS-Fix fuer Modal-Inhalt - Text immer dunkel auf weissem Hintergrund
- **Struktur vereinfacht:** H2-Ueberschriften aus allen Betreiber-Hilfetexten entfernt (Titel bereits im Modal-Header)
- **Schriftgroesse:** Einheitliche 14px (0.875rem) fuer alle Hilfetexte im Modal

### Hinzugefuegt

- **Modul-Hilfetext:** `admin.betreiber.modul` - Erklaert die gesamte Betreiber/Branding-Seite
- **Betreiber-Seite:** 8 Hilfetexte mit (i)-Icons versehen
  - `admin.betreiber.modul` - Modul-Uebersicht (NEU)
  - `admin.betreiber.auswahl` - Betreiber-Konzept erklaert
  - `admin.betreiber.branding` - Branding-Uebersicht
  - `admin.betreiber.branding.logo` - Logo-Upload-Hinweise
  - `admin.betreiber.branding.titel` - App-Titel-Verwendung
  - `admin.betreiber.branding.farben` - Primaer-/Sekundaerfarbe
  - `admin.betreiber.branding.copyright` - Copyright-Einstellungen
  - `admin.betreiber.signatur` - E-Mail-Signatur mit technischem Hintergrund

---

## [1.0.0] - 2025-12-10

### Hinzugefuegt
- HelpText Model mit Markdown-Unterstuetzung
- Jinja2-Macro `help_icon()` fuer Card-Header
- Admin-Oberflaeche unter `/admin/hilfetexte`
- Markdown→HTML Rendering via Python `markdown` Library
- Context Processor fuer `get_help_text()` in Templates
- Live-Vorschau beim Bearbeiten
- Initiale Seed-Daten fuer Kunden-Detail-Seite:
  - `kunden.detail.stammdaten`
  - `kunden.detail.branchen`
  - `kunden.detail.verbaende`
  - `kunden.detail.ci`
