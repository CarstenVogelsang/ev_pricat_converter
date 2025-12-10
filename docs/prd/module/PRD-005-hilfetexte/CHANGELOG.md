# Changelog PRD-005 Hilfetexte

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
