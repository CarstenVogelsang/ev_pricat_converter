# Roadmap V2: Internationalisierung (i18n)

**Status:** Geplant (nach MVP)
**Erstellt:** 2024-12-10
**Prioritaet:** Niedrig

---

## Uebersicht

Umstellung der aktuellen JavaScript-basierten Uebersetzung im DB-Admin auf eine saubere, server-seitige i18n-Loesung mit Flask-Babel.

### Aktueller Stand (V1 - MVP)

Die DB-Admin-Oberflaeche (`/db-admin/`) verwendet:
- **Server-seitig:** `column_labels` in Flask-Admin ModelViews fuer Feldbezeichnungen
- **Client-seitig:** JavaScript DOM-Manipulation fuer UI-Texte (Buttons, Navigation)

Diese Loesung ist pragmatisch und funktional, aber nicht skalierbar fuer:
- Mehrsprachige Anwendungen
- App-weite Uebersetzungen
- Wartbare Uebersetzungsdateien

---

## Ziel V2

Vollstaendige i18n-Loesung mit Flask-Babel fuer die gesamte Anwendung.

---

## Vergleich V1 vs. V2

| Aspekt | V1 (JavaScript) | V2 (Flask-Babel) |
|--------|-----------------|------------------|
| Aufwand | Minimal | Mittel |
| Dependencies | Keine | flask-babel |
| Wartung | Dict in Template editieren | .po/.mo Dateien |
| Mehrsprachigkeit | Nur Deutsch | Beliebig erweiterbar |
| Skalierbarkeit | Nur DB-Admin | App-weit |
| Performance | Client-seitig | Server-seitig |

---

## Voraussetzungen

- [ ] MVP ist abgeschlossen und stabil
- [ ] Bedarf fuer Mehrsprachigkeit besteht (z.B. englische Version)
- [ ] Zeit fuer Migration eingeplant

### Technische Hinweise

- **Flask-BabelEx ist deprecated!** Verwende stattdessen `flask-babel`
- Flask-Admin liefert **keine deutschen Uebersetzungen** mit - muessen selbst erstellt werden

---

## Implementierungsschritte

### 1. Dependencies hinzufuegen

```bash
uv add flask-babel
```

### 2. Babel initialisieren

In `app/__init__.py`:

```python
from flask_babel import Babel

babel = Babel()

def create_app():
    app = Flask(__name__)
    # ... bestehende Konfiguration ...

    babel.init_app(app, locale_selector=get_locale)

    return app

def get_locale():
    """Bestimme die Sprache fuer den aktuellen Request."""
    # Option 1: Immer Deutsch
    return 'de'

    # Option 2: Aus User-Profil
    # if current_user.is_authenticated:
    #     return current_user.language
    # return 'de'

    # Option 3: Browser-Accept-Language
    # return request.accept_languages.best_match(['de', 'en'])
```

### 3. Konfiguration

In `config.py`:

```python
BABEL_DEFAULT_LOCALE = 'de'
BABEL_DEFAULT_TIMEZONE = 'Europe/Berlin'
LANGUAGES = ['de', 'en']  # Unterstuetzte Sprachen
```

### 4. babel.cfg erstellen

Im Projekt-Root:

```ini
[python: **.py]
[jinja2: **/templates/**.html]
extensions=jinja2.ext.autoescape,jinja2.ext.with_
```

### 5. Uebersetzungen extrahieren und erstellen

```bash
# Strings extrahieren
pybabel extract -F babel.cfg -o messages.pot .

# Deutsche Uebersetzung initialisieren
pybabel init -i messages.pot -d app/translations -l de

# messages.po editieren (app/translations/de/LC_MESSAGES/messages.po)

# Kompilieren
pybabel compile -d app/translations

# Bei Updates
pybabel update -i messages.pot -d app/translations
```

### 6. Templates anpassen

```html
<!-- Vorher -->
<button>Save</button>

<!-- Nachher -->
<button>{{ _('Save') }}</button>
```

### 7. JavaScript-Uebersetzungen entfernen

Aus `app/templates/admin/base.html` das gesamte Translation-Script entfernen (Zeilen 154-229).

---

## Betroffene Dateien

| Datei | Aenderung |
|-------|-----------|
| `pyproject.toml` | flask-babel hinzufuegen |
| `app/__init__.py` | Babel initialisieren |
| `config.py` | BABEL_* Konfiguration |
| `babel.cfg` | Neu erstellen |
| `app/translations/` | Neuer Ordner fuer .po/.mo |
| `app/templates/admin/base.html` | JS-Script entfernen |
| `app/templates/**/*.html` | `{{ _('...') }}` Syntax |

---

## Referenzen

- [Flask-Babel Dokumentation](https://python-babel.github.io/flask-babel/)
- [Flask Mega-Tutorial: I18n and L10n](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-xiii-i18n-and-l10n)
- [Flask-Admin Localization](https://flask-admin.readthedocs.io/en/v1.0.9/localization/)

---

## Startbedingung

> **Dieses Feature wird durch explizite Nachfrage gestartet, wenn das MVP fertig ist.**

Nicht automatisch implementieren - nur auf Anfrage!
