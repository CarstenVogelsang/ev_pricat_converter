# ROADMAP: Admin-Navigation Zentralisierung (V2)

## Status: Geplant (nach MVP)

---

## Problem

### 1. Tab-State (admin_tab)

Aktuell muss jede Admin-Route manuell `admin_tab='module'`, `admin_tab='stammdaten'` etc. an das Template übergeben:

```python
# AKTUELL: Jede Route manuell
return render_template('...', admin_tab='module')
return render_template('...', admin_tab='stammdaten')
return render_template('...', admin_tab='einstellungen')
```

**Probleme:**
- Nicht DRY - Code-Duplikation in jeder Route
- Fehleranfällig - vergessenes `admin_tab` führt zu inaktivem Tab
- Inkonsistent - jeder Entwickler muss das Muster kennen

### 2. Breadcrumb-Hierarchie

Aktuell muss jede Admin-Seite die vollständige Breadcrumb-Hierarchie manuell definieren:

```html
{{ breadcrumb([
    {'label': 'Administration', 'url': url_for('admin.index'), 'icon': 'ti-settings'},
    {'label': 'Module', 'url': url_for('admin.module_uebersicht'), 'icon': 'ti-apps'},
    {'label': 'Schulungen', 'url': url_for('schulungen_admin.index'), 'icon': 'ti-school'},
    {'label': 'Themen', 'icon': 'ti-list'}
]) }}
```

**Probleme:**
- Sehr lang und repetitiv
- Fehleranfällig bei Hierarchie-Änderungen
- Keine automatische Ableitung aus URL/Blueprint-Struktur

---

## Lösungskonzept

### Context Processor für admin_tab

Ein Flask Context Processor kann `admin_tab` automatisch aus dem Blueprint-Namen ableiten:

```python
# app/context_processors.py

ADMIN_TAB_MAPPING = {
    'schulungen_admin': 'module',
    'dialog_admin': 'module',
    'pricat_admin': 'module',
    'support_admin': 'einstellungen',
    'admin.kunden_': 'stammdaten',
    'admin.lieferanten_': 'stammdaten',
    'admin.marken_': 'stammdaten',
    'admin.hersteller_': 'stammdaten',
    # ...
}

@app.context_processor
def inject_admin_tab():
    """Automatische admin_tab Ermittlung aus Blueprint/Endpoint."""
    endpoint = request.endpoint or ''

    # Mapping durchsuchen
    for pattern, tab in ADMIN_TAB_MAPPING.items():
        if endpoint.startswith(pattern):
            return {'admin_tab': tab}

    # Fallback
    return {'admin_tab': 'system'}
```

### Breadcrumb-Service

Ein Service könnte Breadcrumbs aus einer Konfiguration oder der URL-Struktur ableiten:

```python
# app/services/breadcrumb_service.py

BREADCRUMB_REGISTRY = {
    'schulungen_admin.index': [
        {'key': 'administration'},
        {'key': 'module'},
        {'key': 'schulungen'}
    ],
    'schulungen_admin.themen_liste': [
        {'key': 'administration'},
        {'key': 'module'},
        {'key': 'schulungen', 'link': True},
        {'key': 'themen'}
    ],
}

def get_breadcrumb_for_endpoint(endpoint: str, **kwargs) -> list:
    """Breadcrumb-Definition aus Registry holen."""
    # ...
```

**Alternative:** Decorator-basierter Ansatz

```python
@breadcrumb(['administration', 'module', 'schulungen'])
def index():
    ...
```

---

## Implementierungsschritte

### Phase 1: Context Processor für admin_tab
1. Context Processor implementieren mit Blueprint-Mapping
2. Tests schreiben
3. `admin_tab` aus allen render_template Aufrufen entfernen
4. Verifizieren dass alle Tabs korrekt aktiv sind

### Phase 2: Breadcrumb-Registry (optional)
1. Breadcrumb-Registry mit Endpoint → Breadcrumb Mapping
2. Context Processor oder Template-Helper
3. Schrittweise Migration bestehender Templates

---

## Aufwand

| Phase | Geschätzter Aufwand |
|-------|---------------------|
| Phase 1: admin_tab Context Processor | 2-3 Stunden |
| Phase 2: Breadcrumb-Registry | 4-6 Stunden |
| Tests + Migration | 2-3 Stunden |
| **Gesamt** | **8-12 Stunden** |

---

## Abhängigkeiten

- Keine externen Abhängigkeiten
- Betrifft alle Admin-Bereiche
- Sollte in einem Rutsch migriert werden (kein Mischbetrieb)

---

## Risiken

| Risiko | Mitigation |
|--------|------------|
| Unvollständiges Mapping | Fallback auf 'system' Tab |
| Performance | Context Processor ist sehr leichtgewichtig |
| Komplexität | Klare Dokumentation + Tests |

---

## Betroffene Dateien (aktuell)

### Routes mit `admin_tab`:
- `app/routes/admin.py` (30+ Stellen)
- `app/routes/schulungen_admin.py` (14 Stellen)
- `app/routes/support_admin.py` (7 Stellen)

### Templates mit manueller Breadcrumb:
- Alle Templates unter `app/templates/administration/`
- Ca. 50+ Templates

---

## Referenzen

- [PRD-008: Breadcrumb-Navigation](../core/PRD-008-breadcrumb-navigation/PRD-008-breadcrumb-navigation.md)
- [Flask Context Processors](https://flask.palletsprojects.com/en/latest/templating/#context-processors)
