# Changelog - PRD-002 Lead & Kundenreport

Alle Änderungen am Lead & Kundenreport Modul.

---

## [Unreleased]

### Added

- **Raw JSON Modal:** Button in CI-Karte öffnet Modal mit formatiertem Firecrawl-Response
- **API-Kostentracking:** Jeder Firecrawl-Call wird mit Credits und Euro-Kosten protokolliert
- Config `firecrawl_credit_kosten` für konfigurierbaren Euro-Preis pro Credit

### Changed

- FirecrawlService akzeptiert jetzt `user_id` Parameter für Kostentracking

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
