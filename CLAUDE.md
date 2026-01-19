# CLAUDE.md

Anweisungen für Claude Code in diesem Repository.

## Projekt

**ev247** - Multi-Tool-Plattform für e-vendo Mitarbeiter und Kunden.

## Kommunikation

**Wir duzen uns!** Das ist unsere Unternehmensphilosophie – wir sind ein Team und kommunizieren auf Augenhöhe. Bitte verwende in allen Antworten die Du-Form.

## Befehle

```bash
# Setup
uv sync

# Entwicklung (Port 5001, da 5000 oft belegt)
uv run python run.py

# Produktion
uv run gunicorn -w 4 -b 0.0.0.0:5001 'app:create_app()'

# Datenbank Setup (Produktion)
uv run flask init-db           # Tabellen erstellen
uv run flask seed-essential    # Rollen + Admin-User (PFLICHT!)
uv run flask seed-stammdaten   # Branchen, Verbände, Hilfetexte

# Datenbank Setup (Entwicklung) - zusätzlich:
uv run flask seed-demo         # Test-Lieferant, Demo-Users

# Datenbank-Migrationen (bei Schema-Änderungen)
uv run flask db migrate -m "Beschreibung"  # Migration generieren
uv run flask db upgrade                     # Migration anwenden
uv run flask db downgrade                   # Letzte Migration rückgängig
uv run flask db current                     # Aktuelle DB-Version
```

## Dokumentation

Alle Details zur Architektur, Datenmodellen und Features sind in den PRD-Dokumenten:

### Basis-Plattform

- [docs/prd/PRD_BASIS_MVP.md](docs/prd/PRD_BASIS_MVP.md) - Tech-Stack, Projektstruktur, DB-Schema, UI-Richtlinien
- [docs/prd/PRD_BASIS_RECHTEVERWALTUNG.md](docs/prd/PRD_BASIS_RECHTEVERWALTUNG.md) - Rollen, Modul-Zugriff, Admin-Sonderrechte
- [docs/prd/PRD_BASIS_CHANGELOG.md](docs/prd/PRD_BASIS_CHANGELOG.md) - Plattform-Änderungen

### PRD-Ordnerstruktur

| Ordner | Inhalt | Kriterien |
|--------|--------|-----------|
| `docs/prd/` | Basis-Dokumente | Plattform-Architektur, übergreifend |
| `docs/prd/module/` | Module | Eigenständige Features mit Menü-Eintrag |
| `docs/prd/core/` | Basisfunktionalitäten | Querschnittsfunktionen, von Modulen genutzt |
| `docs/prd/roadmap/` | Roadmap | Zukünftige Features nach MVP |

**Regel:** Nur eigenständige Module mit eigenem Menü-Eintrag gehören in `module/`.
Querschnittsfunktionen (Hilfetexte, Breadcrumb, etc.) gehören in `core/`.

### Module

| Modul | PRD | Status |
|-------|-----|--------|
| PRICAT Converter | [PRD-001](docs/prd/module/PRD-001-pricat-converter/PRD-001-pricat-converter.md) | Aktiv |
| Lead & Kundenreport | [PRD-002](docs/prd/module/PRD-002-lead-kundenreport/PRD-002-lead-kundenreport.md) | Aktiv |
| Kunde-Lieferanten | [PRD-003](docs/prd/module/PRD-003-kunde-hat-lieferanten/PRD-003-kunde-hat-lieferanten.md) | Geplant |
| Content Generator | [PRD-004](docs/prd/module/PRD-004-content-generator/PRD-004-content-generator.md) | Geplant |
| Kunden-Dialog | [PRD-006](docs/prd/module/PRD-006-kunden-dialog/PRD-006-kunden-dialog.md) | Aktiv |
| Anwender-Support | [PRD-007](docs/prd/module/PRD-007-anwender-support/PRD-007-anwender-support.md) | Aktiv |
| Produktdaten | [PRD-009](docs/prd/module/PRD-009-produktdaten/PRD-009-produktdaten.md) | MVP |
| Schulungen | [PRD-010](docs/prd/module/PRD-010-schulungen/PRD-010-schulungen.md) | In Entwicklung |
| Projektverwaltung | [PRD-011](docs/prd/module/PRD-011-projektverwaltung/PRD-011-projektverwaltung.md) | POC |
| Kunden-Mailing | [PRD-013](docs/prd/module/PRD-013-kunden-mailing/PRD-013-kunden-mailing.md) | In Entwicklung |

### Basisfunktionalitäten (core/)

| Feature | PRD | Status |
|---------|-----|--------|
| Hilfetexte | [PRD-005](docs/prd/core/PRD-005-hilfetexte/PRD-005-hilfetexte.md) | Aktiv |
| Breadcrumb-Navigation | [PRD-008](docs/prd/core/PRD-008-breadcrumb-navigation/PRD-008-breadcrumb-navigation.md) | Aktiv |
| View-Struktur-Richtlinien | [PRD-012](docs/prd/core/PRD-012-view-guidelines/PRD-012-view-guidelines.md) | Aktiv |

Jedes Modul/Feature hat ein eigenes `CHANGELOG.md` im jeweiligen Ordner.

### V2 Roadmap (nach MVP)

| Feature | Dokument | Hinweis |
|---------|----------|---------|
| Internationalisierung (i18n) | [ROADMAP-V2-i18n](docs/prd/roadmap/ROADMAP-V2-i18n.md) | Nur auf Nachfrage starten! |
| PRD-Management in DB | [ROADMAP-V2-prd-management](docs/prd/roadmap/ROADMAP-V2-prd-management.md) | Nach PRD-006 diskutieren |

## Wichtige Konventionen

- **UI-Feedback:** Bootstrap Toasts (keine Alert-Boxen)
- **Package Manager:** uv (nicht pip)
- **DB-Schema:** Bei Änderungen `flask db migrate` + `flask db upgrade`, NICHT DB löschen!
- **Sprache Docs:** Deutsch
- **Sprache Code:** Englisch
- **Deutsche Texte:** Immer echte Umlaute (ä, ü, ö, ß) verwenden, NICHT ae/ue/oe/ss

## UI-Konventionen für Module

### Audit-Logging

Alle Module müssen wichtige Benutzeraktionen in die `audit_log` Tabelle loggen.
Nutze dafür den `logging_service`:

```python
from app.services import log_event, log_kritisch, log_hoch, log_mittel

# Standard-Log
log_event('entity_type', entity_id, 'aktion', 'Beschreibung der Aktion')

# Mit Priorität
log_hoch('kunde', kunde_id, 'user_erstellt', f'User {email} für Kunde erstellt')
```

### Hilfe-Button (i)

Jedes Modul hat oben rechts einen Hilfe-Button für Enduser-Dokumentation:

```html
<button type="button" class="btn btn-sm btn-outline-info"
        data-bs-toggle="modal" data-bs-target="#helpModal">
    <i class="ti ti-info-circle"></i>
</button>
```

### DEV-Button (nur admin/mitarbeiter)

Jedes Modul hat oben rechts einen DEV-Button für Entwickler:

- Zeigt das PRD-Dokument aus Entwicklersicht
- Ermöglicht ggf. Bearbeitung des PRD (V2)

```html
{% if current_user.rolle.name in ['admin', 'mitarbeiter'] %}
<a href="{{ url_for('admin.prd_view', module='dialog') }}"
   class="btn btn-sm btn-outline-secondary">
    <i class="ti ti-code"></i> DEV
</a>
{% endif %}
```

### Modul-Einstellungen

Jedes Modul sollte eine eigene Einstellungen-Seite haben. Das Pattern ist einheitlich:

**Route-Pattern:**
```python
@{modul}_admin_bp.route('/einstellungen', methods=['GET', 'POST'])
@login_required
@mitarbeiter_required
def einstellungen():
    from app.models import Config

    if request.method == 'POST':
        for key in request.form:
            if key.startswith('{modul}_'):
                Config.set_value(key, request.form[key])
        flash('Einstellungen gespeichert', 'success')
        return redirect(url_for('{modul}_admin.einstellungen'))

    settings = {
        'einstellung_name': Config.get_value('{modul}_einstellung_name', 'default'),
    }
    return render_template('administration/{modul}/einstellungen.html', settings=settings)
```

**Config-Key-Konvention:**
```
{modul_code}_{einstellung_name}
```

Beispiele:
- `projektverwaltung_ki_prompt_suffix`
- `schulungen_max_teilnehmer_default`
- `dialog_antwort_frist_tage`

**Template-Pfad:**
```
app/templates/administration/{modul}/einstellungen.html
```

**Navigation:**
1. **Modul-Übersicht** (`/admin/module-uebersicht`): Nutze `admin_tile` Macro mit `settings_url` Parameter
2. **Modul-Index**: Button mit Text "Einstellungen" in der Button-Gruppe

```html
{# In module_uebersicht.html #}
{{ admin_tile(
    'Modulname',
    'Beschreibung',
    'ti-icon',
    url_for('{modul}_admin.index'),
    color_hex='#hex',
    settings_url=url_for('{modul}_admin.einstellungen')
) }}

{# In {modul}/index.html #}
<a href="{{ url_for('{modul}_admin.einstellungen') }}" class="btn btn-outline-secondary">
    <i class="ti ti-settings"></i> Einstellungen
</a>
```

### Hilfetexte-System (PRD-005)

**WICHTIG:** Erklärungstexte gehören NICHT direkt in den Content!

Verwende immer das Hilfesystem:

- **PRD:** [PRD-005-hilfetexte](docs/prd/core/PRD-005-hilfetexte/PRD-005-hilfetexte.md)
- **Admin-UI:** `/admin/hilfetexte`
- **Schlüssel-Format:** `bereich.seite.element` (z.B. `admin.betreiber.auswahl`)

**Verwendung in Templates:**

```html
{% from "macros/help.html" import help_icon with context %}

<div class="card-header">
    <span><i class="ti ti-icon"></i> Titel {{ help_icon('bereich.seite.element') }}</span>
</div>
```

**WICHTIG:** `with context` ist erforderlich für den Context Processor!

**Wenn du ein neues Modul/Maske implementierst:**

1. Prüfe, ob Hilfetexte benötigt werden
2. Lege Schlüssel nach Konvention `bereich.seite.element` an (in seed oder Admin-UI)
3. Füge Help-Icons mit Macro ein
4. Entferne `<p class="text-muted">` Beschreibungstexte und `<div class="form-text">` Hinweise

### Button-Platzierung in Cards

Speichern- und Löschen-Buttons werden **nie** mitten im Content platziert, sondern:

| Button-Typ | Position | Beispiel |
|------------|----------|----------|
| **Speichern** (primär) | Card-Header, rechts | `<button class="btn btn-primary btn-sm">` |
| **Löschen** (destruktiv) | Card-Footer oder Card-Header (mit Confirm) | `onclick="confirm('...')"` |
| **Formular-Aktionen** | Card-Footer bei langen Formularen | `<div class="card-footer">` |

**Pattern für Card-Header mit Button:**

```html
<form method="post">
    <div class="card">
        <div class="card-header d-flex justify-content-between align-items-center">
            <span><i class="ti ti-icon"></i> Titel</span>
            <button type="submit" class="btn btn-primary btn-sm">
                <i class="ti ti-device-floppy"></i> Speichern
            </button>
        </div>
        <div class="card-body">
            <!-- Formularfelder -->
        </div>
    </div>
</form>
```

**Ausnahme:** Bei sehr langen Formularen kann der Speichern-Button auch im Card-Footer platziert werden.

### Breadcrumb-Navigation (PRD-008)

**WICHTIG:** Jede Seite muss eine Breadcrumb-Navigation haben!

Die Breadcrumb zeigt dem Benutzer, wo er sich befindet und ermöglicht schnelle Navigation zu übergeordneten Bereichen.

**Verwendung in Templates:**

```html
{% from "macros/breadcrumb.html" import breadcrumb %}

{{ breadcrumb([
    {'label': 'Dashboard', 'url': url_for('main.dashboard'), 'icon': 'ti-home'},
    {'label': 'Kunden', 'url': url_for('kunden.liste'), 'icon': 'ti-users'},
    {'label': kunde.firmierung}
]) }}
```

**Regeln:**

| Regel | Beschreibung |
|-------|--------------|
| **Erste Ebene** | Immer "Dashboard" mit Link und `ti-home` Icon |
| **Modul-Ebene** | Modul-Name mit Link und passendem Icon |
| **Letzte Ebene** | Aktuelle Seite **ohne** `url` (wird automatisch ohne Link dargestellt) |
| **Icons** | Nur für Dashboard und Module, nicht für Detail-Seiten |

**Beispiele nach Bereich:**

```html
{# Kunden-Liste #}
{{ breadcrumb([
    {'label': 'Dashboard', 'url': url_for('main.dashboard'), 'icon': 'ti-home'},
    {'label': 'Kunden'}
]) }}

{# Kunden-Detail #}
{{ breadcrumb([
    {'label': 'Dashboard', 'url': url_for('main.dashboard'), 'icon': 'ti-home'},
    {'label': 'Kunden', 'url': url_for('kunden.liste'), 'icon': 'ti-users'},
    {'label': kunde.firmierung}
]) }}

{# Admin-Bereich #}
{{ breadcrumb([
    {'label': 'Administration', 'url': url_for('admin.index'), 'icon': 'ti-settings'},
    {'label': 'Hilfetexte'}
]) }}
```

**PRD:** [PRD-008-breadcrumb-navigation](docs/prd/core/PRD-008-breadcrumb-navigation/PRD-008-breadcrumb-navigation.md)

### View-Struktur-Richtlinien (PRD-012)

**WICHTIG:** Alle Views müssen den Richtlinien in [PRD-012-view-guidelines](docs/prd/core/PRD-012-view-guidelines/PRD-012-view-guidelines.md) folgen!

**Kurzübersicht:**

| Element | Position | Beschreibung |
|---------|----------|--------------|
| **Breadcrumb** | Ganz oben | Navigation mit Icons für Hauptbereiche |
| **Titel + Buttons** | Unter Breadcrumb | Titel links, Aktions-Buttons rechts (`d-flex justify-content-between`) |
| **Wichtige Felder** | Oben im Formular | Typ, Status, Aktiv - direkt nach Name/Titel |
| **Filter** | Unter Titel | Nur bei Listen-Ansichten |
| **Stammdaten** | Haupt-Card | In logischen Gruppen mit `<hr>` getrennt |
| **Optionale Felder** | Unten | Notizen, Freitext am Ende |

**View-Typen:**

1. **Listen-Ansichten**: Breadcrumb → Header mit Buttons → Filter → Tabelle/Grid
2. **Formular-Ansichten**: Breadcrumb → Header mit Buttons → Card mit Feldern
3. **Detail-Ansichten**: Breadcrumb → Header → 2-spaltiges Layout (8-4)

**Code-Pattern für Formular-Header:**

```html
<form method="POST">
    {{ form.hidden_tag() }}

    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="mb-0">{{ titel }}</h2>
        <div class="d-flex gap-2">
            <a href="{{ url_for('modul.liste') }}" class="btn btn-outline-secondary">Abbrechen</a>
            <button type="submit" class="btn btn-primary">
                <i class="ti ti-check"></i> Speichern
            </button>
        </div>
    </div>

    <div class="card">
        <div class="card-body">
            <!-- Felder hier -->
        </div>
    </div>
</form>
```

**PRD:** [PRD-012-view-guidelines](docs/prd/core/PRD-012-view-guidelines/PRD-012-view-guidelines.md)

## Arbeitsweise

### ⚠️ WICHTIG: PRD-Pflicht bei neuen Anforderungen

**Bei jeder neuen größeren Anforderung gilt:**

1. **PRD ZUERST erstellen** - Bevor Code geschrieben wird, muss ein PRD-Dokument im Ordner `docs/prd/module/PRD-XXX-...` angelegt werden
2. **User-Genehmigung einholen** - Der User prüft das PRD und genehmigt die Umsetzung explizit
3. **Erst nach Genehmigung implementieren** - Keine Implementierung ohne vorherige PRD-Freigabe!

**Workflow:**

```text
Anforderung → PRD schreiben → User prüft → Genehmigung → Implementierung → CHANGELOG
```

Dies ist **PFLICHT** für alle neuen Module, größere Features und architektonische Änderungen!

### Allgemeine Schritte

1. **Vor Änderungen:** Relevantes PRD-Dokument lesen
2. **Bei neuen Features:** PRD-Dokument aktualisieren
3. **Nach Implementierungen:** Changelogs aktualisieren (siehe unten)
4. **Nach Plan-Modus:** Zugehörige PRD- und CHANGELOG-Dokumente pflegen

### Changelog-Pflege (PFLICHT!)

⚠️ **JEDE Implementierung MUSS im entsprechenden CHANGELOG dokumentiert werden!**

Nach jeder Änderung - egal wie klein - müssen die relevanten Changelogs aktualisiert werden:

- **Basis-Plattform-Änderungen** (Auth, Admin-UI, Core-Features, Stammdaten-CRUD):
  → [docs/prd/PRD_BASIS_CHANGELOG.md](docs/prd/PRD_BASIS_CHANGELOG.md)

- **Modul-spezifische Änderungen**:
  → `docs/prd/module/PRD-XXX-.../CHANGELOG.md` im jeweiligen Modul-Ordner

- **Core-Features** (Hilfetexte, Breadcrumbs, etc.):
  → `docs/prd/core/PRD-XXX-.../CHANGELOG.md` im jeweiligen Core-Ordner

**Wichtig:** Bei Änderungen, die mehrere Bereiche betreffen, ALLE betroffenen Changelogs aktualisieren!

Format: [Keep a Changelog](https://keepachangelog.com/de/1.0.0/) mit Kategorien:

- `Added` - Neue Features
- `Changed` - Änderungen an bestehenden Features
- `Fixed` - Bugfixes
- `Removed` - Entfernte Features

## Projektverwaltung API (PRD-011)

### ⚠️ WICHTIG: Tasks NUR via API bearbeiten!

**NIEMALS** Tasks über die Browser-UI (Playwright) lesen oder bearbeiten!

Verwende **IMMER** die REST-API:
- **Task lesen:** `curl http://localhost:5001/api/tasks/by-nummer/{task_nummer}`
- **Task aktualisieren:** `curl -X PATCH http://localhost:5001/api/tasks/{id} -H "Content-Type: application/json" -d '{"status": "review"}'`
- **Task-Beschreibung ändern:** `curl -X PATCH http://localhost:5001/api/tasks/{id} -H "Content-Type: application/json" -d '{"beschreibung": "Neue Beschreibung"}'`

**Warum?** Die API ist zuverlässiger, schneller und die Änderungen werden korrekt in der Datenbank gespeichert.

PRD-Dokumente, Tasks und Changelogs sind in der Datenbank gespeichert und über eine REST-API abrufbar.

### Daten abrufen

```bash
# Alle Komponenten mit IDs anzeigen
curl http://localhost:5001/api/komponenten-uebersicht

# PRD als Markdown lesen
curl http://localhost:5001/api/komponenten/{id}/prd

# Tasks für eine Komponente (filterbar)
curl http://localhost:5001/api/komponenten/{id}/tasks
curl http://localhost:5001/api/komponenten/{id}/tasks?phase=mvp
curl http://localhost:5001/api/komponenten/{id}/tasks?status=in_arbeit

# Changelog als Markdown
curl http://localhost:5001/api/komponenten/{id}/changelog

# Task über Task-Nummer abrufen (z.B. PRD011-T020)
curl http://localhost:5001/api/tasks/by-nummer/PRD011-T020

# Task Status ändern (z.B. auf "in_arbeit" setzen)
curl -X PATCH http://localhost:5001/api/tasks/20 \
     -H "Content-Type: application/json" \
     -d '{"status": "in_arbeit"}'

# Task als erledigt markieren (erstellt automatisch Changelog-Eintrag)
curl -X POST http://localhost:5001/api/tasks/{id}/erledigen
```

### API-Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/projekte` | GET | Liste aller Projekte |
| `/api/projekte/{id}` | GET | Projekt-Details inkl. Komponenten |
| `/api/komponenten` | GET | Liste aller Komponenten (filterbar) |
| `/api/komponenten/{id}` | GET | Komponenten-Details |
| `/api/komponenten/{id}/prd` | GET | PRD als Markdown |
| `/api/komponenten/{id}/tasks` | GET | Tasks (Query: `?phase=mvp&status=in_arbeit`) |
| `/api/komponenten/{id}/changelog` | GET | Changelog als Markdown |
| `/api/tasks/{id}` | GET | Task-Details |
| `/api/tasks/by-nummer/{task_nummer}` | GET | Task über Task-Nummer (z.B. `PRD011-T020`) |
| `/api/tasks/{id}` | PATCH | Task aktualisieren (status, zugewiesen_an, prioritaet) |
| `/api/tasks/{id}/erledigen` | POST | Task abschließen (generiert Changelog) |
| `/api/komponenten-uebersicht` | GET | Schnelle Übersicht aller Komponenten-IDs |

### Fallback

Falls die API nicht erreichbar ist oder keine Daten in der DB vorhanden sind, befinden sich die PRD-Dokumente weiterhin im Dateisystem unter `docs/prd/`.

### Task-Workflow für Claude

**WICHTIG:** Wenn du einen Task bearbeitest und fertig bist:

1. **NICHT** `/api/tasks/{id}/erledigen` verwenden!
2. **STATTDESSEN** Status auf "Review" setzen:

   ```bash
   curl -X PATCH http://localhost:5001/api/tasks/{id} \
        -H "Content-Type: application/json" \
        -d '{"status": "review"}'
   ```

**Warum?** Der Developer möchte:

- Deine Arbeit reviewen
- Ggf. Feedback geben oder weitere Todos anlegen
- Den Task selbst auf "Erledigt" setzen

**Ausnahme:** Nur wenn der User explizit sagt "Task abschließen" oder "erledigen", verwende `/api/tasks/{id}/erledigen`.

### Task abschließen mit Changelog

Wenn ein Task abgeschlossen wird und die Checkbox "Bei Erledigung Changelog-Eintrag erstellen" aktiviert ist (Default: `True`), wird automatisch ein Changelog-Eintrag in der Datenbank erstellt:

```bash
# Task als erledigt markieren (erstellt automatisch Changelog wenn aktiviert)
curl -X POST http://localhost:5001/api/tasks/{id}/erledigen

# Mit optionalen Parametern
curl -X POST http://localhost:5001/api/tasks/{id}/erledigen \
     -H "Content-Type: application/json" \
     -d '{"changelog_kategorie": "fixed", "changelog_beschreibung": "Custom Beschreibung"}'
```

**Parameter für `/api/tasks/{id}/erledigen`:**

| Parameter | Default | Beschreibung |
|-----------|---------|--------------|
| `create_changelog` | `true` | Changelog-Eintrag erstellen? |
| `changelog_kategorie` | `added` | `added`, `changed`, `fixed`, `removed` |
| `changelog_beschreibung` | Task-Titel | Optionale custom Beschreibung |

**Wichtig:** Der Changelog-Eintrag wird in der Datenbank gespeichert und auf der Changelog-Seite der Komponente angezeigt.

## MCP-Server / Plugins

Claude Code hat Zugriff auf folgende MCP-Server für dieses Projekt:

### Context7 (Dokumentation)

Nutze Context7, um **aktuelle Library-Dokumentation** abzurufen:

```text
"Hole die Flask-Dokumentation für Blueprints via Context7"
"Was sagt die SQLAlchemy-Doku zu relationship()?"
```

**Wann nutzen:**

- Bei Unsicherheit über API-Syntax
- Für aktuelle Best Practices (Flask, SQLAlchemy, Jinja2, Bootstrap 5)
- Bei neuen Library-Features

### Playwright (Browser-Automation)

Nutze Playwright für **UI-Tests und Screenshots**:

```text
"Öffne localhost:5000 und mach einen Screenshot"
"Teste den Login-Flow mit den Credentials aus .env"
```

**Wann nutzen:**

- Nach UI-Änderungen zur visuellen Überprüfung
- Für automatisierte Funktionstests
- Um Fehler im Browser zu reproduzieren

## Playwright Login Credentials

Für automatisierte Tests via Playwright MCP können Login-Credentials aus `.env` Variablen gelesen werden:

```bash
# .env
EV247_ADMIN_EMAIL=carsten.vogelsang@e-vendo.de
EV247_ADMIN_PASSWORD=admin123
```

Diese Variablen werden NICHT von der Flask-App verwendet, sondern nur für Claude Code Playwright-Tests.
