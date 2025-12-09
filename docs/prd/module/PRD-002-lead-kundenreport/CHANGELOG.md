# Changelog - PRD-002 Lead & Kundenreport

Alle Änderungen am Lead & Kundenreport Modul.

---

## [Unreleased]

### Added

- **Logo Re-Extraktion:** Button "Erneut extrahieren" in CI-Karte wenn Logo nicht gefunden
  - Extrahiert Logo aus gespeichertem Raw Response ohne neuen API-Call
  - Route `/kunden/<id>/reparse-logo`
- **Raw JSON Modal:** Button in CI-Karte öffnet Modal mit formatiertem Firecrawl-Response
- **API-Kostentracking:** Jeder Firecrawl-Call wird mit Credits und Euro-Kosten protokolliert
- Config `firecrawl_credit_kosten` für konfigurierbaren Euro-Preis pro Credit
- **Projektverwaltung:** Neue Seite `/kunden/<id>/projekt` für interne Mitarbeiter
  - Tätigkeiten-Bereich (Platzhalter für zukünftige Funktion)
  - API-Kosten pro Kunde mit Aufschlüsselung nach Mitarbeiter
- User-Model Properties: `is_mitarbeiter`, `is_kunde`, `is_internal`

### Changed

- **Logo-Extraktion verbessert:** Fallback-Kette prüft jetzt drei mögliche Pfade im Firecrawl-Response:
  1. `data.branding.logo` (direkt)
  2. `data.branding.images.logo` (verschachtelt)
  3. `data.images.logo` (Root-Ebene)
- FirecrawlService akzeptiert jetzt `user_id` Parameter für Kostentracking
- **API-Abrechnung im User-Dropdown:** Nur sichtbar für Rolle `kunde`
- **Projekt-Button auf Kunden-Detail:** Nur sichtbar für `admin` und `mitarbeiter`

---

## [1.0.0] - 2025-12-07

### Added

- Kunde Model mit Stammdaten (Firmierung, Adresse, URLs)
- KundeCI Model für Corporate Identity Daten
- Firecrawl Service für Website-Analyse
- Kundenliste mit Filter (Aktiv/Inaktiv/Alle)
- Kundendetail-Ansicht mit CI-Anzeige
- Kundenformular (Neu/Bearbeiten)
- Website-Analyse Button für CI-Extraktion
- Blueprint `kunden_bp` unter `/kunden`

### Features

- Automatische Logo-Extraktion via Firecrawl
- Farbpaletten-Extraktion (Primary, Secondary, Accent, Background, Text)
- Raw-Response Speicherung für Debugging
