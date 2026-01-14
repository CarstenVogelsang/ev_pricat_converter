# Changelog - PRD-013 Kunden-Mailing

Alle wichtigen Änderungen am Kunden-Mailing-Modul werden hier dokumentiert.

## [1.1.0] - 2026-01-14

### Added (Phase 2: Baukasten-Editor)

- E-Mail-Templates mit Inline-Styles für E-Mail-Client-Kompatibilität:
  - `base.html` - E-Mail-Wrapper mit Table-Layout
  - `sektion_header.html` - Logo/Portal-Name
  - `sektion_text_bild.html` - Freier Content mit optionalem Bild
  - `sektion_fragebogen_cta.html` - CTA-Button zum Fragebogen
  - `sektion_footer.html` - Abmelde-Link und Footer-Text
- Visueller Baukasten-Editor (`/admin/mailing/<id>/editor`)
  - Sektionen hinzufügen, bearbeiten, löschen
  - Button-basiertes Reordering (↑/↓)
  - Modal-Dialoge für Sektion-Konfiguration
- E-Mail-Vorschau (`/admin/mailing/<id>/vorschau`)
  - Live-Preview im iframe
  - Desktop/Mobile Toggle
  - Sample-Daten für Personalisierung
- AJAX-Endpoints für Editor-Operationen:
  - POST `/editor/sektion` - Sektion hinzufügen
  - PATCH `/editor/sektion/<sid>` - Sektion bearbeiten
  - DELETE `/editor/sektion/<sid>` - Sektion löschen
  - POST `/editor/reorder` - Reihenfolge ändern
- Service-Erweiterungen:
  - `get_sample_context()` - Beispieldaten für Preview
  - `render_mailing_html()` mit `preview_mode` Parameter

### Changed

- Detail-Ansicht um Editor- und Vorschau-Links erweitert

## [1.0.0] - 2026-01-13

### Added (Phase 1: Basis-Infrastruktur)

- PRD-013 Dokument erstellt mit vollständiger Spezifikation
- Datenmodell-Design (Mailing, MailingEmpfaenger, MailingKlick, MailingZielgruppe)
- Service-Architektur definiert (MailingService)
- Route-Struktur für Admin und öffentliche Endpunkte
- Template-Struktur für Admin-UI und E-Mail-Sektionen
- Fragebogen-Integration mit PRD-006 spezifiziert
- DSGVO-konforme Abmelde-Funktion geplant
- Manuelles Batching für Brevo-Tageslimit dokumentiert
