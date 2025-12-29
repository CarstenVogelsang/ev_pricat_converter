# PRD-008: Globale Breadcrumb-Navigation

**Status:** Implementiert
**Version:** 1.0
**Erstellt:** 2025-12-28
**Autor:** Claude Code

---

## 1. Übersicht

### 1.1 Ziel

Ein konsistentes, zentrales Breadcrumb-System für die gesamte Anwendung, das dem Benutzer jederzeit zeigt, wo er sich befindet. Integration mit dem Support-System (PRD-007) für automatische Kontext-Übertragung.

### 1.2 Hintergrund

Vor der Implementierung gab es 3 verschiedene Navigation-Patterns in der Anwendung:
1. `module_header` Macro mit `breadcrumb`-Parameter
2. Manuelles Bootstrap `<nav aria-label="breadcrumb">` HTML
3. Einfache "Zurück"-Links

Dies führte zu inkonsistenter Benutzerführung und erschwerte die Wartung.

---

## 2. Lösung

### 2.1 Breadcrumb-Macro

**Datei:** `app/templates/macros/breadcrumb.html`

```html
{% from "macros/breadcrumb.html" import breadcrumb %}

{{ breadcrumb([
    {'label': 'Dashboard', 'url': url_for('main.dashboard'), 'icon': 'ti-home'},
    {'label': 'Kunden', 'url': url_for('kunden.liste'), 'icon': 'ti-users'},
    {'label': kunde.firmierung}
]) }}
```

### 2.2 Parameter

| Parameter | Typ | Erforderlich | Beschreibung |
|-----------|-----|--------------|--------------|
| `label` | String | Ja | Anzeigetext des Elements |
| `url` | String | Nein | Link-Ziel (fehlt beim letzten Element) |
| `icon` | String | Nein | Tabler-Icon Klasse (z.B. `ti-home`) |

### 2.3 Regeln

1. **Erste Ebene:** Immer "Dashboard" (bei User-Seiten) oder "Administration" (bei Admin-Seiten)
2. **Modul-Ebene:** Modul-Name mit Link und passendem Icon
3. **Letzte Ebene:** Aktuelle Seite **ohne** `url` (wird automatisch ohne Link dargestellt)
4. **Icons:** Nur für Dashboard/Administration und Module, nicht für Detail-Seiten

---

## 3. Patterns nach Bereich

### 3.1 User-Facing Module (base.html)

```html
{# Modul-Übersicht #}
{{ breadcrumb([
    {'label': 'Dashboard', 'url': url_for('main.dashboard'), 'icon': 'ti-home'},
    {'label': 'Kunden', 'icon': 'ti-users'}
]) }}

{# Detail-Seite #}
{{ breadcrumb([
    {'label': 'Dashboard', 'url': url_for('main.dashboard'), 'icon': 'ti-home'},
    {'label': 'Kunden', 'url': url_for('kunden.liste'), 'icon': 'ti-users'},
    {'label': kunde.firmierung}
]) }}

{# Formular-Seite #}
{{ breadcrumb([
    {'label': 'Dashboard', 'url': url_for('main.dashboard'), 'icon': 'ti-home'},
    {'label': 'Kunden', 'url': url_for('kunden.liste'), 'icon': 'ti-users'},
    {'label': 'Neuer Kunde'}
]) }}
```

### 3.2 Administration (administration/base.html)

```html
{# Admin-Übersicht #}
{{ breadcrumb([
    {'label': 'Dashboard', 'url': url_for('main.dashboard'), 'icon': 'ti-home'},
    {'label': 'Administration', 'icon': 'ti-settings'}
]) }}

{# Bereichs-Übersicht #}
{{ breadcrumb([
    {'label': 'Administration', 'url': url_for('admin.index'), 'icon': 'ti-settings'},
    {'label': 'Stammdaten', 'icon': 'ti-database'}
]) }}

{# Detail-Seite im Admin #}
{{ breadcrumb([
    {'label': 'Administration', 'url': url_for('admin.index'), 'icon': 'ti-settings'},
    {'label': 'Stammdaten', 'url': url_for('admin.stammdaten_uebersicht')},
    {'label': 'Branchen', 'icon': 'ti-category'}
]) }}
```

---

## 4. Integration mit PRD-007 (Support-System)

Der Breadcrumb-Pfad wird automatisch als Kontext an das Support-Modal übergeben. Die `formatKontextBreadcrumb()` Funktion in `base.html` verwendet dasselbe Schlüssel-Format wie die Help-Icons:

```javascript
// Schlüssel wie "kunden.detail.stammdaten"
// wird zu "Kunden › Detail › Stammdaten"
kontextText.innerHTML = formatKontextBreadcrumb(hilfetextSchluessel);
```

---

## 5. Implementierte Templates

### 5.1 Kunden-Modul (3 Templates)
- `kunden/liste.html`
- `kunden/detail.html`
- `kunden/form.html`

### 5.2 Dialog-Admin (5 Templates)
- `dialog_admin/index.html`
- `dialog_admin/detail.html`
- `dialog_admin/form.html`
- `dialog_admin/teilnehmer.html`
- `dialog_admin/auswertung.html`

### 5.3 Support (7 Templates)
- `support/meine_tickets.html`
- `support/ticket_form.html`
- `support/ticket_detail.html`
- `support/admin/dashboard.html`
- `support/admin/ticket_detail.html`
- `support/admin/teams.html`
- `support/admin/team_form.html`

### 5.4 Administration (8 Templates)
- `administration/index.html`
- `administration/module_uebersicht.html`
- `administration/stammdaten_uebersicht.html`
- `administration/einstellungen_uebersicht.html`
- `administration/hilfetexte.html`
- `administration/branchen.html`
- `administration/email_templates.html`
- `administration/verbaende.html`

---

## 6. Noch ausstehend

Folgende Templates sollten noch mit Breadcrumbs versehen werden (nach gleichem Pattern):

### Administration
- `branding.html`
- `pricat.html`
- `kunden_report.html`
- `lieferanten_auswahl.html`
- `content_generator.html`
- `branchenrollen.html`
- `logs.html`
- `module.html`
- `settings.html`
- `betreiber.html`
- `email_template_form.html`
- `email_template_preview.html`

### Weitere Module
- PRICAT-Converter Templates (falls vorhanden)
- Abrechnung Templates (falls vorhanden)
- Dashboard

---

## 7. CLAUDE.md Richtlinie

Die Breadcrumb-Richtlinie wurde in `CLAUDE.md` unter "UI-Konventionen für Module" dokumentiert.

---

## 8. Changelog

| Datum | Version | Änderung |
|-------|---------|----------|
| 2025-12-28 | 1.0 | Initiale Implementierung |
