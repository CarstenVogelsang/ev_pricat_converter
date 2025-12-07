# Changelog - PRD-002 Lead & Kundenreport

Alle Änderungen am Lead & Kundenreport Modul.

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
