# PRD-011: Projektverwaltung

## Übersicht

| Eigenschaft | Wert |
|-------------|------|
| **Modul-ID** | PRD-011 |
| **Name** | Projektverwaltung |
| **Status** | In Entwicklung |
| **Aktuelle Phase** | POC |
| **Zielgruppe** | Admin, Mitarbeiter |
| **Abhängigkeiten** | Basis-Plattform |

---

## 1. Ziel & Vision

Die Projektverwaltung ist ein **selbstreferenzielles System**: Es verwaltet die Entwicklung der ev247-Plattform – inklusive sich selbst.

### Kernideen

1. **PRD-Dokumente in der Datenbank** statt im Dateisystem
2. **Kanban-Board** für Task-Verwaltung pro Modul/Komponente
3. **Automatischer Changelog** bei Task-Abschluss
4. **API für Claude Code** zum Lesen von PRDs und Tasks
5. **Erweiterbar** für Kundenprojekte (Consulting-Tätigkeiten)

### Use Cases

| Akteur | Use Case |
|--------|----------|
| **Claude (KI)** | Liest PRD & Tasks via API, um Anforderungen zu verstehen |
| **Entwickler** | Pflegt Tasks im Kanban-Board, schließt ab → Changelog |
| **Mitarbeiter** | Sieht Projektfortschritt, erstellt Anforderungen |
| **Kunde** | Sieht Fortschritt seines Projekts (optional, V1) |

---

## 2. Datenmodell

### 2.1 Projekt

Das übergeordnete Container-Objekt.

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | Integer | Primary Key |
| `name` | String(100) | Projektname (z.B. "ev247-Plattform") |
| `beschreibung` | Text | Kurzbeschreibung |
| `typ` | Enum | `intern` / `kunde` |
| `kunde_id` | Integer (FK) | Optional, Verweis auf Kunde |
| `aktiv` | Boolean | Projekt aktiv? |
| `created_at` | DateTime | Erstelldatum |
| `updated_at` | DateTime | Letzte Änderung |

### 2.2 Komponente (= PRD/Modul/Entity)

Ein Modul, eine Basisfunktion oder ein Entity innerhalb eines Projekts.

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | Integer | Primary Key |
| `projekt_id` | Integer (FK) | Zugehöriges Projekt |
| `name` | String(100) | Komponentenname (z.B. "Schulungen") |
| `prd_nummer` | String(10) | PRD-Nummer (z.B. "010", "011") |
| `typ` | Enum | `modul` / `basisfunktion` / `entity` |
| `modul_id` | Integer (FK) | Optional, Verweis auf bestehendes Modul (wenn `typ=modul`) |
| `prd_inhalt` | Text | PRD-Dokument als Markdown |
| `aktuelle_phase` | Enum | `poc` / `mvp` / `v1` / `v2` / ... |
| `status` | Enum | `aktiv` / `archiviert` |
| `icon` | String(50) | Tabler-Icon (z.B. "ti-school") |
| `sortierung` | Integer | Reihenfolge in Listen |
| `created_at` | DateTime | Erstelldatum |
| `updated_at` | DateTime | Letzte Änderung |

#### Komponenten-Typen

| Typ | Beschreibung | Beispiel | Modul-Referenz |
|-----|--------------|----------|----------------|
| `modul` | Eigenständiges Modul mit Menü-Eintrag | PRD-010 Schulungen | Ja → `modul_id` FK |
| `basisfunktion` | Querschnittsfunktion (Core) | PRD-005 Hilfetexte | Nein |
| `entity` | Stammdaten/Model mit CRUD | Lieferant, Kunde | Nein |

**Hinweis:** Bei `typ=modul` wird `modul_id` gesetzt, um die Verknüpfung zum bestehenden Modul-System herzustellen. Dadurch kann die Changelog-Sichtbarkeit über `ModulZugriff` abgeleitet werden.

### 2.3 Task

Eine Aufgabe innerhalb einer Komponente.

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | Integer | Primary Key |
| `komponente_id` | Integer (FK) | Zugehörige Komponente |
| `titel` | String(200) | Kurztitel |
| `beschreibung` | Text | Detailbeschreibung (Markdown) |
| `phase` | Enum | `poc` / `mvp` / `v1` / `v2` / ... |
| `status` | Enum | `backlog` / `geplant` / `in_arbeit` / `review` / `erledigt` |
| `prioritaet` | Enum | `niedrig` / `mittel` / `hoch` / `kritisch` |
| `zugewiesen_an` | Integer (FK) | Optional, User-ID |
| `sortierung` | Integer | Reihenfolge im Kanban |
| `created_at` | DateTime | Erstelldatum |
| `updated_at` | DateTime | Letzte Änderung |
| `erledigt_am` | DateTime | Abschlussdatum |

### 2.4 ChangelogEintrag

Automatisch generiert bei Task-Abschluss.

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | Integer | Primary Key |
| `komponente_id` | Integer (FK) | Zugehörige Komponente |
| `task_id` | Integer (FK) | Auslösender Task (optional) |
| `version` | String(20) | Version (z.B. "POC", "MVP", "1.0.0") |
| `kategorie` | Enum | `added` / `changed` / `fixed` / `removed` |
| `beschreibung` | Text | Changelog-Text |
| `sichtbarkeit` | Enum | `intern` / `oeffentlich` (Default: `intern`) |
| `erstellt_am` | DateTime | Erstelldatum |
| `erstellt_von` | Integer (FK) | User-ID |

#### Sichtbarkeits-Logik

Die Sichtbarkeit eines Changelog-Eintrags wird wie folgt bestimmt:

1. **Expliziter Override:** Wenn `sichtbarkeit = 'oeffentlich'` gesetzt ist → öffentlich sichtbar
2. **Modul-Ableitung:** Wenn `komponente.typ = 'modul'` UND das verknüpfte Modul via `ModulZugriff` für die Rolle "Kunde" freigegeben ist → Changelog kann öffentlich sein
3. **Default:** Alle anderen Einträge sind nur intern sichtbar (admin/mitarbeiter)

### 2.5 User-Erweiterung

Bestehende User-Tabelle wird erweitert.

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `user_typ` | Enum | `mensch` / `ki_claude` / `ki_codex` / `ki_andere` |

#### User-Typ Strategie

| Phase | Umsetzung |
|-------|-----------|
| **POC** | Enum-Feld im User-Model (statisch) |
| **V2** | Separate `UserTyp`-Tabelle für dynamische Verwaltung neuer KI-Modelle |

**Hinweis:** Das Enum ist für den POC ausreichend, da neue KI-Modelle selten hinzukommen. In V2 kann dies bei Bedarf zu einer separaten Tabelle migriert werden.

---

## 3. API-Endpoints (für Claude Code)

### 3.1 Projekte

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/projekte` | GET | Liste aller Projekte |
| `/api/projekte/{id}` | GET | Projekt-Details inkl. Komponenten |

### 3.2 Komponenten/PRDs

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/komponenten/{id}` | GET | Komponenten-Details |
| `/api/komponenten/{id}/prd` | GET | PRD als Markdown (Content-Type: text/markdown) |
| `/api/komponenten/{id}/tasks` | GET | Tasks (Query: `?phase=mvp&status=in_arbeit`) |
| `/api/komponenten/{id}/changelog` | GET | Changelog als Markdown |

### 3.3 Tasks

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/tasks/{id}` | GET | Task-Details |
| `/api/tasks/{id}/erledigen` | POST | Task abschließen (generiert Changelog) |

---

## 4. UI-Konzept

### 4.1 Navigation

```
Administration
└── Module (bestehend)
    └── Projektverwaltung
        ├── Projekte (Liste)
        ├── Kanban-Board (pro Komponente)
        └── Changelog (gesamt oder gefiltert)
```

### 4.2 Kanban-Board

```
┌─────────────────────────────────────────────────────────────────────┐
│  Komponente: Schulungen (PRD-010)                    Phase: MVP ▼  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  BACKLOG        GEPLANT        IN ARBEIT      REVIEW      ERLEDIGT  │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐│
│  │ Task A  │   │ Task B  │   │ Task C  │   │ Task D  │   │ Task E  ││
│  │ ──────  │   │ ──────  │   │ ──────  │   │ ──────  │   │ ──────  ││
│  │ @Claude │   │ @Max    │   │ @Claude │   │         │   │ ✓       ││
│  └─────────┘   └─────────┘   └─────────┘   └─────────┘   └─────────┘│
│  ┌─────────┐                                                         │
│  │ Task F  │                                                         │
│  └─────────┘                                                         │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.3 Task-Karte (Asana-Style)

Das UI-Konzept orientiert sich an Asana/Trello für optimale Bedienbarkeit:

#### Kanban-Karte (kompakt)

Auf dem Board werden Tasks als kompakte Karten dargestellt:

- **Titel** (max. 2 Zeilen)
- **Priorität-Badge** (farbig: kritisch=rot, hoch=orange, mittel=blau, niedrig=grau)
- **Zugewiesen an** (Avatar oder KI-Icon)
- **Phase-Badge** (POC/MVP/V1...)

#### Task-Detail (Offcanvas/Drawer)

Bei Klick auf eine Karte öffnet sich **rechts ein Seitenbereich** (Bootstrap Offcanvas):

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│  KANBAN-BOARD                                          │  TASK-DETAIL       │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐              │                    │
│  │     │ │     │ │ ███ │ │     │ │     │              │  Task C            │
│  │     │ │     │ │ ◄── │ │     │ │     │              │  ──────────────    │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘              │  Status: In Arbeit │
│  BACKLOG  GEPLANT  IN ARB  REVIEW  ERLED              │  Phase: MVP        │
│                                                        │  Priorität: ●●○○   │
│                                                        │  Zugewiesen: @Clau │
│                                                        │                    │
│                                                        │  Beschreibung:     │
│                                                        │  [Markdown-Editor] │
│                                                        │                    │
│                                                        │  [Speichern]       │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Vorteile:**
- Board bleibt sichtbar während der Bearbeitung
- Schnelles Wechseln zwischen Tasks
- Keine Seiten-Navigation nötig
- Fokussiertes Arbeiten im Drawer

---

## 5. Phasen-Roadmap

### POC (Proof of Concept)

- [x] PRD-Dokument erstellen
- [ ] Datenmodell implementieren (Projekt, Komponente, Task, ChangelogEintrag)
- [ ] User-Erweiterung (user_typ)
- [ ] Basis-CRUD für Projekte/Komponenten
- [ ] API-Endpoints für Claude-Integration
- [ ] Migration: Bestehende PRDs in DB importieren
- [ ] CLAUDE.md ergänzen

### MVP

- [ ] Kanban-Board UI (SortableJS)
- [ ] Task-CRUD mit Drag & Drop
- [ ] Phase-Filter im Board
- [ ] Automatische Changelog-Generierung bei Task-Abschluss
- [ ] PRD-Editor mit Markdown-Preview
- [ ] User-Zuweisung (Mensch oder KI)

### V1

- [ ] Kundenprojekte (projekt.typ = 'kunde')
- [ ] Öffentlicher Changelog (Release Notes)
- [ ] MD-Export CLI (`flask export-prds`)
- [ ] Dashboard mit Projekt-Übersicht
- [ ] Benachrichtigungen bei Zuweisung

### V2 (Roadmap)

- [ ] Reporting: Velocity, Burndown-Charts
- [ ] GitHub Issues Sync (bidirektional?)
- [ ] Kommentare an Tasks
- [ ] Zeiterfassung pro Task

---

## 6. Integration mit Claude Code

### 6.1 CLAUDE.md-Ergänzung

Nach Implementierung wird CLAUDE.md um folgenden Abschnitt erweitert:

```markdown
## Projektverwaltung (PRD-011)

PRD-Dokumente und Tasks sind in der Datenbank gespeichert.

### Daten abrufen

- **PRD lesen:** `curl http://localhost:5001/api/komponenten/{id}/prd`
- **Tasks lesen:** `curl http://localhost:5001/api/komponenten/{id}/tasks?phase=mvp`
- **Changelog:** `curl http://localhost:5001/api/komponenten/{id}/changelog`

### Komponenten-IDs (ev247-Projekt)

| ID | PRD | Name |
|----|-----|------|
| 1 | 001 | PRICAT Converter |
| 2 | 006 | Kunden-Dialog |
| ... | ... | ... |

### Fallback

Falls API nicht erreichbar: `uv run flask export-prds` generiert MD-Dateien nach docs/prd/
```

### 6.2 Workflow

1. **Anforderung erfassen:** User beschreibt Feature → Claude erstellt Task in DB
2. **Planen:** Task wird `geplant`, Phase zugewiesen
3. **Implementieren:** Task wird `in_arbeit`, Claude arbeitet
4. **Abschließen:** Task wird `erledigt` → Changelog-Eintrag automatisch
5. **Dokumentieren:** PRD wird aktualisiert

---

## 7. Berechtigungen

| Rolle | Projekte | Tasks | Changelog |
|-------|----------|-------|-----------|
| **admin** | CRUD | CRUD | Lesen/Schreiben |
| **mitarbeiter** | Lesen | CRUD (eigene) | Lesen |
| **kunde** | Eigene lesen | Eigene lesen | Eigenes lesen |

---

## 8. Technische Hinweise

### 8.1 Migration bestehender PRDs

CLI-Befehl: `uv run flask import-prds`

1. Scannt `docs/prd/module/PRD-*/`
2. Erstellt Komponente pro PRD
3. Importiert PRD-Inhalt und CHANGELOG.md
4. Erstellt Tasks aus Roadmap (optional, manuell)

### 8.2 Export nach Markdown

CLI-Befehl: `uv run flask export-prds`

1. Generiert `docs/prd/module/PRD-{nr}-{name}/PRD-{nr}-{name}.md`
2. Generiert `docs/prd/module/PRD-{nr}-{name}/CHANGELOG.md`
3. Nützlich als Backup und für Git-Versionierung

---

## Changelog

Siehe [CHANGELOG.md](./CHANGELOG.md)
