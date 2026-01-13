# Hilfetexte-System

Kontextsensitive Hilfetexte fuer UI-Elemente mit Markdown-Unterstuetzung und Admin-Oberflaeche.

## Funktionen

- **Help-Icons:** (i)-Icons in Card-Headern oeffnen Modal mit Hilfetext
- **Markdown-Rendering:** Hilfetexte in Markdown verfassen, als HTML anzeigen
- **Admin-Oberflaeche:** Hilfetexte erstellen, bearbeiten, aktivieren/deaktivieren
- **Live-Vorschau:** Markdown-Preview beim Bearbeiten
- **Support-Integration:** Optionale Verknuepfung mit Support-Tickets (PRD-007)

## Architektur-Uebersicht

```
┌─────────────────────────────────────────────────────────────────────┐
│                            TEMPLATE                                  │
│  {% from "macros/help.html" import help_icon with context %}        │
│  {{ help_icon('kunden.detail.branchen') }}                          │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     JINJA2 MACRO (help.html)                         │
│  - Ruft get_help_text(schluessel) auf                               │
│  - Rendert (i)-Button mit Bootstrap Modal                           │
│  - Wendet |markdown Filter auf Inhalt an                            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
          ┌────────────────────┴────────────────────┐
          ▼                                         ▼
┌─────────────────────────────┐     ┌─────────────────────────────────┐
│    CONTEXT PROCESSOR        │     │      MARKDOWN FILTER            │
│    (app/__init__.py)        │     │      (app/__init__.py)          │
│                             │     │                                 │
│  def get_help_text(key):    │     │  @app.template_filter('markdown')│
│    return HelpText.query    │     │  def markdown_filter(text):     │
│      .filter_by(...)        │     │    return markdown.markdown(...)│
│      .first()               │     │                                 │
└──────────────┬──────────────┘     └─────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      DATENBANK (help_text)                           │
│  id | schluessel              | titel        | inhalt_markdown      │
│  1  | kunden.detail.branchen  | Branchen     | ## Erklaerung...     │
└─────────────────────────────────────────────────────────────────────┘
```

## Visuelle Darstellung in Views

### Das (i)-Icon

Das Hilfe-Icon erscheint als kleines Info-Symbol (ⓘ) neben Titeln, Labels oder Card-Headern:

- **Icon:** Tabler Icon `ti-info-circle`
- **Farbe:** Grau (`text-muted`) auf hellem Hintergrund, weiss (`text-white-50`) auf dunklem
- **Hover:** Icon wechselt zu Info-Blau
- **Position:** Inline nach dem Text mit leichtem Abstand (`ms-2`)

**Beispiel-Darstellung:**

```
┌─────────────────────────────────────────────────────────────────────┐
│ ▼ Card Header                                                       │
├─────────────────────────────────────────────────────────────────────┤
│  📁 Branchen ⓘ                                        [Badge]       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Card Body Content...                                               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
              ↑
         Klick oeffnet Modal
```

### Das Modal

Bei Klick auf das (i)-Icon oeffnet sich ein zentriertes Bootstrap-Modal:

```
┌──────────────────────────────────────────────┐
│  ⓘ Branchen                            [X]  │  ← Titel aus HelpText.titel
├──────────────────────────────────────────────┤
│                                              │
│  Hier steht der Hilfetext als               │  ← Markdown gerendert zu HTML
│  formatierter Text mit:                      │
│                                              │
│  - Aufzaehlungen                            │
│  - **Fettschrift**                          │
│  - `Code-Beispiele`                         │
│                                              │
└──────────────────────────────────────────────┘
```

### Regeln fuer die Platzierung

| Bereich | Platzierung | Beispiel |
|---------|-------------|----------|
| Card-Header | Nach dem Titel-Text | `<span>Branchen {{ help_icon(...) }}</span>` |
| Formular-Labels | Nach dem Label-Text | `<label>Feld {{ help_icon(...) }}</label>` |
| Modul-Header | In der Button-Gruppe rechts | Neben DEV-Button |
| Tabellen-Header | Nach der Spalten-Ueberschrift | `<th>Spalte {{ help_icon(...) }}</th>` |

### Wann KEIN Hilfe-Icon anzeigen

- Wenn kein Hilfetext in der Datenbank existiert (Macro rendert nichts)
- Wenn der Hilfetext auf `aktiv = False` gesetzt ist
- Bei selbsterklaerenden UI-Elementen (Overkill vermeiden)

## Zugriffsrechte

| Rolle | Zugriff |
|-------|---------|
| Admin | Erstellen, Bearbeiten, Loeschen |
| Mitarbeiter | Erstellen, Bearbeiten |
| Kunde | Nur Lesen (Help-Icons sehen) |

## Datenmodell

### Tabelle: `help_text`

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | Integer | Primary Key |
| schluessel | String(100) | Eindeutiger Key (z.B. "kunden.detail.branchen") |
| titel | String(200) | Modal-Ueberschrift |
| inhalt_markdown | Text | Hilfetext in Markdown |
| aktiv | Boolean | Anzeigen ja/nein |
| created_at | DateTime | Erstellungsdatum |
| updated_at | DateTime | Aktualisierungsdatum |
| updated_by_id | Integer | FK zu user (Bearbeiter) |

## Routes

| Route | Methode | Beschreibung |
|-------|---------|--------------|
| `/admin/hilfetexte` | GET/POST | Admin-Oberflaeche |

## Technische Umsetzung

### Jinja2-Macros

Die Datei `app/templates/macros/help.html` stellt **vier Macro-Varianten** bereit:

| Macro | Beschreibung | Anwendungsfall |
|-------|--------------|----------------|
| `help_icon` | Standard (i)-Icon mit Modal | Card-Header, Labels |
| `help_modal` | Nur Modal ohne Trigger-Button | Eigener Trigger noetig |
| `help_icon_with_support` | (i)-Icon + Headset-Icon | Seiten mit Support-Integration (PRD-007) |
| `support_icon` | Nur Headset-Icon | Seiten ohne Hilfetext aber mit Support |

### 1. help_icon (Standard)

```jinja2
{% from "macros/help.html" import help_icon with context %}

<!-- Standard (grau auf hellem Hintergrund) -->
{{ help_icon('kunden.detail.branchen') }}

<!-- Auf farbigem Header (weiss auf dunklem Hintergrund) -->
{{ help_icon('schluessel', light=true) }}
```

**Parameter:**
- `schluessel` (required): Eindeutiger Key aus der Datenbank
- `light` (optional, default=false): Weisses Icon fuer dunkle Hintergruende

### 2. help_modal (nur Modal)

Fuer komplexe Layouts, wo der Trigger-Button separat gestaltet werden soll:

```jinja2
{% from "macros/help.html" import help_modal with context %}

<button data-bs-toggle="modal" data-bs-target="#helpModal_kunden_detail_branchen">
    Eigener Button
</button>
{{ help_modal('kunden.detail.branchen') }}
```

### 3. help_icon_with_support (mit Support-Integration)

Zeigt neben dem (i)-Icon auch ein Headset-Icon zum Erstellen von Support-Tickets:

```jinja2
{% from "macros/help.html" import help_icon_with_support with context %}

{{ help_icon_with_support('kunden.detail.stammdaten') }}
```

**Ergebnis:** `ⓘ 🎧` - Beide Icons nebeneinander

Das Modal enthaelt zusaetzlich einen "Support kontaktieren" Button im Footer.

### 4. support_icon (nur Support)

Fuer Seiten ohne Hilfetext, die trotzdem Support-Anfragen ermoeglichen:

```jinja2
{% from "macros/help.html" import support_icon with context %}

{{ support_icon() }}
```

---

**Wichtig:** `with context` ist bei allen Macros erforderlich fuer den Context Processor!

### Markdown-Filter

`app/__init__.py` - Jinja2-Filter fuer Markdown→HTML:

```python
@app.template_filter('markdown')
def markdown_filter(text):
    return markdown.markdown(text, extensions=['tables', 'fenced_code', 'nl2br'])
```

### Context Processor

`app/__init__.py` - `get_help_text()` Funktion fuer Templates:

```python
@app.context_processor
def inject_help_text_function():
    def get_help_text(schluessel):
        return HelpText.query.filter_by(schluessel=schluessel, aktiv=True).first()
    return {'get_help_text': get_help_text}
```

## Schluessel-Konvention

Format: `bereich.seite.element`

Beispiele:
- `kunden.detail.branchen`
- `kunden.detail.verbaende`
- `kunden.detail.ci`
- `kunden.detail.stammdaten`

## Seed-Daten

Initiale Hilfetexte werden ueber `flask seed` angelegt.

## Verwendung in Templates

### Help-Icon in Card-Header einbinden

```html
{% from "macros/help.html" import help_icon with context %}

<div class="card">
    <div class="card-header">
        <span><i class="ti ti-category"></i> Branchen {{ help_icon('kunden.detail.branchen') }}</span>
    </div>
    <div class="card-body">
        ...
    </div>
</div>
```

### Admin-UI

Die Verwaltung der Hilfetexte erfolgt unter **Administration > Hilfetexte** (`/admin/hilfetexte`):

- Liste aller Hilfetexte mit Schluessel, Titel und Status
- Formular zum Anlegen neuer Hilfetexte
- Bearbeiten-Modal mit Markdown-Editor
- Vorschau-Modal zeigt gerenderten Hilfetext
- Loeschen nur fuer Admins

## Dependencies

- `markdown>=3.5` - Python Markdown Library
