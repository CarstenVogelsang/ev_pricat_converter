# Changelog - PRD-008 Breadcrumb-Navigation

Alle nennenswerten Änderungen am Breadcrumb-System werden hier dokumentiert.

Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

---

## [1.0.0] - 2025-12-28

### Added
- Neues `breadcrumb` Macro in `app/templates/macros/breadcrumb.html`
- CLAUDE.md um Breadcrumb-Richtlinie erweitert
- PRD-008 Dokumentation erstellt

### Changed
- **Kunden-Modul:** 3 Templates mit Breadcrumb ausgestattet (liste, detail, form)
- **Dialog-Admin:** 5 Templates aktualisiert (index, detail, form, teilnehmer, auswertung)
- **Support:** 7 Templates aktualisiert (User: 3, Admin: 4)
- **Administration:** 8 Kern-Templates aktualisiert (index, Übersichtsseiten, wichtige Detail-Seiten)

### Removed
- Alte "Zurück"-Links in Templates durch Breadcrumbs ersetzt
- Manuelles Bootstrap-Breadcrumb-HTML durch Macro ersetzt
