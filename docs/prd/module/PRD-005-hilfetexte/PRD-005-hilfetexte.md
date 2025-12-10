# Hilfetexte-System

Kontextsensitive Hilfetexte fuer UI-Elemente mit Markdown-Unterstuetzung und Admin-Oberflaeche.

## Funktionen

- **Help-Icons:** (i)-Icons in Card-Headern oeffnen Modal mit Hilfetext
- **Markdown-Rendering:** Hilfetexte in Markdown verfassen, als HTML anzeigen
- **Admin-Oberflaeche:** Hilfetexte erstellen, bearbeiten, aktivieren/deaktivieren
- **Live-Vorschau:** Markdown-Preview beim Bearbeiten

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

### Jinja2-Macro

`app/templates/macros/help.html` - Wiederverwendbares Macro:

```jinja2
{% from "macros/help.html" import help_icon with context %}
{{ help_icon('kunden.detail.branchen') }}
```

**Wichtig:** `with context` ist erforderlich fuer den Context Processor!

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
