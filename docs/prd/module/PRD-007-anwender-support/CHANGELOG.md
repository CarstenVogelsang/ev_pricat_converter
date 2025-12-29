# Changelog - PRD-007 Anwender-Support

Alle wichtigen Änderungen am Anwender-Support Modul werden hier dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

## [Unreleased]

Keine ausstehenden Änderungen.

---

## [1.1.0] - 2025-12-28

### Added

- **LookupWert Admin-UI**: Neue Verwaltungsoberfläche unter Administration → Stammdaten → Lookup-Werte
  - Gruppierte Anzeige nach Kategorie (support_typ, support_status, support_prioritaet)
  - Inline-Bearbeitung von Wert, Icon, Farbe, Sortierung, Aktiv-Status
  - Drag & Drop Sortierung mit SortableJS
  - Neue Einträge hinzufügen mit Kategorie-Autocomplete
- **Ticket-Nummern-Format**:
  - Neues Format: `YYYY-N` intern, `YY-HEX` für Kunden (z.B. `25-2A`)
  - Property `nummer_anzeige` für Hex-Darstellung (Kundensicht)
  - Property `nummer_intern` für lesbare Darstellung (Staff: `#42 (2025)`)
  - Backwards-kompatibel mit Legacy-Format `T-YYYY-NNNNN`
- **LookupWert-Model erweitert**:
  - Neue Spalte `icon` (String, Tabler-Icon-Klasse)
  - Neue Spalte `farbe` (String, Bootstrap-Farbklasse)
  - Neue Spalte `modul_id` (FK, optionale Modul-Zuordnung)
  - Helper-Methoden: `get_icon()`, `get_farbe()`, `get_entry()`
- **Seed-Daten**: Support-Typen, Status und Prioritäten als LookupWert-Einträge

### Fixed

- **Icon-Bug**: Tabler-Icons wurden nicht korrekt angezeigt, da der `ti`-Prefix fehlte
  - `TicketTyp.get_icon()` gibt jetzt `ti ti-{icon}` zurück statt nur `ti-{icon}`
  - Bug-Icon von `ti-bug` zu `ti-alert-triangle` geändert (bessere Sichtbarkeit)

### Changed

- **Templates aktualisiert**: User-Templates zeigen `nummer_anzeige`, Admin-Templates zeigen `nummer_intern` mit Tooltip

---

## [1.0.0] - 2025-12-28

### Hinzugefügt

- **User-Frontend**:
  - Meine Support-Anfragen (`/support/tickets`) - Liste offener und geschlossener Tickets
  - Neues Ticket erstellen (`/support/tickets/neu`) mit Kontext-Übernahme
  - Ticket-Detail (`/support/tickets/<nummer>`) mit Kommentarverlauf
  - Markdown-Support in Beschreibungen und Kommentaren
- **Admin-Dashboard** (`/admin/support`):
  - Übersicht aller Tickets mit Statistiken
  - Filter nach Status, Typ, Priorität, Bearbeiter
  - Team-Verwaltung
- **Datenmodelle**:
  - `SupportTeam` - Support-Teams mit Mitgliederzuweisung
  - `SupportTicket` - Tickets mit Nummern-Generierung und Kontext
  - `TicketKommentar` - Kommentare (öffentlich + intern) und Status-Änderungen
  - Enums: `TicketTyp`, `TicketStatus`, `TicketPrioritaet`
- **Breadcrumb-Navigation**: Alle Support-Templates mit Breadcrumbs (PRD-008)
