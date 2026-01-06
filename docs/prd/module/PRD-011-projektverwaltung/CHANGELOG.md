# Changelog - PRD-011 Projektverwaltung

Alle bemerkenswerten Änderungen an diesem Modul werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

---

## [Unreleased]

### Geplant (V1)

- Migration bestehender PRDs aus Dateisystem in DB
- Öffentliches Changelog (Release Notes View)
- MD-Export CLI (`flask export-prds`)
- Dashboard mit Projekt-Übersicht
- Reporting (Velocity, Burndown)

---

## [MVP] - 2025-12-29

### Added

- **Task-Typ mit Icons** (PRD011-T029):
  - Custom Bootstrap 5 Dropdown statt Standard-Select für Icon-Anzeige
  - 8 Task-Typen mit farbigen Tabler-Icons (Funktion, Verbesserung, Fehlerbehebung, etc.)
  - Help-Modal z-index Fix für Lesbarkeit im Offcanvas (z-index: 1060)
  - Icons in der Hilfe-Tabelle für visuelle Orientierung
- **Kanban-Board UI** mit Drag & Drop:
  - SortableJS für Drag & Drop zwischen Spalten
  - Automatische Sortierung und Status-Update via AJAX
  - Kompakte Task-Karten mit Priorität-Badge und Phase-Tag
- **Task-CRUD mit Offcanvas-Editor** (Asana-Style):
  - Rechts ausfahrender Drawer für Task-Details
  - Alle Task-Eigenschaften bearbeitbar (Titel, Beschreibung, Status, Priorität, Phase)
  - User-Zuweisung (Mensch oder KI)
  - Löschen-Funktion mit Bestätigung
- **Phase-Filter im Board**:
  - Toggle-Buttons für POC/MVP/V1/V2/V3
  - Filtert Tasks nach Entwicklungsphase
- **PRD-Editor mit Live-Preview**:
  - Split-View mit Markdown-Editor links, Preview rechts
  - Client-seitiges Rendering mit marked.js
  - Keyboard-Shortcuts (Ctrl+S zum Speichern, Tab für Einrückung)
- **Changelog-Verwaltung**:
  - Manuelle Changelog-Einträge erstellen
  - Automatische Generierung bei Task-Abschluss
  - Kategorien: Added, Changed, Fixed, Removed, Deprecated, Security
  - Sichtbarkeit: Intern oder Öffentlich
- **Admin-UI Integration**:
  - Neuer Eintrag in Module-Übersicht
  - Projekt-Liste mit Statistiken
  - Komponenten-Sidebar im Kanban-Board
- **Task-Model Erweiterungen**:
  - `prioritaet_badge` Property für Bootstrap-Badge-Klassen
  - `zugewiesen` Alias für Template-Verwendung

---

## [POC] - 2025-12-29

### Added

- **Datenmodelle** implementiert:
  - `Projekt` - Container für Komponenten (intern/kunde)
  - `Komponente` - PRD/Modul mit `typ` (modul/basisfunktion/entity) und `modul_id` FK
  - `Task` - Aufgaben mit Kanban-Status und Priorität
  - `ChangelogEintrag` - Automatische Dokumentation mit `sichtbarkeit`
- **User-Erweiterung**: `user_typ` Feld zur Unterscheidung Mensch/KI (claude/codex/andere)
- **API-Blueprint** für Claude Code Integration:
  - `GET /api/projekte` - Liste aller Projekte
  - `GET /api/komponenten` - Liste/Filter von Komponenten
  - `GET /api/komponenten/{id}/prd` - PRD als Markdown
  - `GET /api/komponenten/{id}/tasks` - Tasks mit Filter
  - `GET /api/komponenten/{id}/changelog` - Changelog als Markdown
  - `POST /api/tasks/{id}/erledigen` - Task abschließen mit auto Changelog
  - `GET /api/komponenten-uebersicht` - Schnelle ID-Übersicht
- **CLAUDE.md** mit API-Dokumentation ergänzt
- **DB-Migration** mit Safety-Checks für vorhandene Tabellen

### Design-Entscheidungen

- `Komponente.typ`: modul/basisfunktion/entity zur Kategorisierung
- `Komponente.modul_id`: FK zum bestehenden Modul-System für Berechtigungs-Ableitung
- `ChangelogEintrag.sichtbarkeit`: intern/oeffentlich mit Override-Option
- `UserTyp`: Enum für POC (mensch/ki_claude/ki_codex/ki_andere), dynamische Tabelle in V2
- Task-UI: Asana-Style mit Bootstrap Offcanvas für Task-Editor (MVP)
