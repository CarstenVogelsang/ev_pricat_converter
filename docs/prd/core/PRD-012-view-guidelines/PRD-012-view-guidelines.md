# PRD-012: View-Struktur-Richtlinien

## Übersicht

Dieses Dokument definiert einheitliche Gestaltungsrichtlinien für alle Views in der ev247-Plattform. Ziel ist eine konsistente Benutzeroberfläche, die intuitiv bedienbar ist und ein professionelles Erscheinungsbild bietet.

---

## Grundprinzipien

1. **Konsistenz** - Gleiche Elemente verhalten sich überall gleich
2. **Hierarchie** - Wichtige Elemente sind prominent platziert
3. **Effizienz** - Häufige Aktionen sind schnell erreichbar
4. **Klarheit** - Der Benutzer weiß immer, wo er sich befindet

---

## View-Typen

### 1. Listen-Ansichten

Listen-Ansichten zeigen eine Übersicht von Datensätzen mit Such-/Filtermöglichkeiten.

#### Struktur

```
┌─────────────────────────────────────────────────────────────┐
│ Breadcrumb: Dashboard / Modul-Name                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ [Icon] Modul-Titel (Badge: Anzahl)    [Aktion] [+Neu]│   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─ Filter-Bereich (optional) ──────────────────────────┐   │
│  │ [Dropdown] [Dropdown] [Suchfeld...] [Filter-Button]  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─ Daten-Card ─────────────────────────────────────────┐   │
│  │ ┌─────────────────────────────────────────────────┐  │   │
│  │ │ Spalte 1  │ Spalte 2  │ Spalte 3  │ Aktionen   │  │   │
│  │ ├───────────┼───────────┼───────────┼────────────┤  │   │
│  │ │ Daten     │ Daten     │ Daten     │ [Edit][Del]│  │   │
│  │ │ Daten     │ Daten     │ Daten     │ [Edit][Del]│  │   │
│  │ └─────────────────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Elemente

| Element | Position | Beschreibung |
|---------|----------|--------------|
| **Breadcrumb** | Ganz oben | Navigation mit Icons für Hauptbereiche |
| **Modul-Header** | Unter Breadcrumb | Titel mit Icon, Badge (Anzahl), Aktions-Buttons rechts |
| **Filter-Bereich** | Unter Header | Optional, in Card oder integriert im Header |
| **Daten-Card** | Hauptbereich | Tabelle oder Card-Grid mit Daten |
| **Zeilen-Aktionen** | Rechts in Tabelle | Edit/Delete Buttons pro Zeile |

#### Code-Beispiel

```html
{{ breadcrumb([
    {'label': 'Dashboard', 'url': url_for('main.dashboard'), 'icon': 'ti-home'},
    {'label': 'Modul-Name'}
]) }}

<div class="d-flex justify-content-between align-items-center mb-4">
    <div class="d-flex align-items-center gap-3">
        <div class="rounded-circle bg-primary-subtle p-3">
            <i class="ti ti-icon fs-2 text-primary"></i>
        </div>
        <h2 class="mb-0">Modul-Titel</h2>
        <span class="badge bg-secondary">{{ items|length }}</span>
    </div>
    <div class="d-flex gap-2">
        <a href="{{ url_for('modul.neu') }}" class="btn btn-primary">
            <i class="ti ti-plus"></i> Neu
        </a>
    </div>
</div>
```

---

### 2. Formular-Ansichten (Neu/Bearbeiten)

Formular-Ansichten dienen der Erfassung oder Bearbeitung von Datensätzen.

#### Struktur

```
┌─────────────────────────────────────────────────────────────┐
│ Breadcrumb: Dashboard / Modul / Aktion                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Titel (Neuer X / X bearbeiten)       [Abbrechen] [Save]    │
│                                                             │
│  ┌─ Stammdaten-Card ────────────────────────────────────┐   │
│  │                                                      │   │
│  │  Name/Titel *                    [Typ ▼] [✓ Aktiv]   │   │
│  │  ┌──────────────────────────┐    ┌────┐  ┌───────┐   │   │
│  │  │ Eingabefeld              │    │ ▼  │  │  ✓    │   │   │
│  │  └──────────────────────────┘    └────┘  └───────┘   │   │
│  │                                                      │   │
│  │  Weitere Pflichtfelder                               │   │
│  │  ┌──────────────────────────────────────────────┐    │   │
│  │  │                                              │    │   │
│  │  └──────────────────────────────────────────────┘    │   │
│  │                                                      │   │
│  │  Optionale Felder                                    │   │
│  │  ┌──────────────────────────────────────────────┐    │   │
│  │  │                                              │    │   │
│  │  └──────────────────────────────────────────────┘    │   │
│  │                                                      │   │
│  │  Notizen                                             │   │
│  │  ┌──────────────────────────────────────────────┐    │   │
│  │  │                                              │    │   │
│  │  │                                              │    │   │
│  │  └──────────────────────────────────────────────┘    │   │
│  │                                                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Feld-Reihenfolge

| Priorität | Felder | Begründung |
|-----------|--------|------------|
| 1 (oben) | Name/Titel, Typ, Status/Aktiv | Wichtigste Identifikation |
| 2 | Pflichtfelder (Adresse, Kontakt) | Notwendige Daten |
| 3 | Optionale Felder | Ergänzende Daten |
| 4 (unten) | Notizen, Freitext | Selten genutztes Feld |

#### Button-Platzierung

| Button-Typ | Position | Reihenfolge |
|------------|----------|-------------|
| **Abbrechen** | Header rechts | Links (sekundär) |
| **Speichern** | Header rechts | Rechts (primär) |
| **Löschen** | Header rechts (optional) | Zwischen Abbrechen und Speichern |

**Wichtig:** Buttons gehören NICHT ans Ende des Formulars, sondern in den Header neben dem Titel!

#### Code-Beispiel

```html
{{ breadcrumb([
    {'label': 'Dashboard', 'url': url_for('main.dashboard'), 'icon': 'ti-home'},
    {'label': 'Modul', 'url': url_for('modul.liste'), 'icon': 'ti-icon'},
    {'label': titel}
]) }}

<form method="POST">
    {{ form.hidden_tag() }}

    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2>{{ titel }}</h2>
        <div class="d-flex gap-2">
            <a href="{{ url_for('modul.liste') }}" class="btn btn-outline-secondary">
                Abbrechen
            </a>
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

---

### 3. Detail-Ansichten

Detail-Ansichten zeigen einen einzelnen Datensatz mit allen Informationen.

#### Struktur

```
┌─────────────────────────────────────────────────────────────┐
│ Breadcrumb: Dashboard / Modul / Entity-Name                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [Icon] Entity-Name [Badge]        [Aktion1] [Bearbeiten]   │
│                                                             │
│  ┌─ Haupt-Content (col-md-8) ───┐  ┌─ Meta (col-md-4) ───┐  │
│  │                              │  │                     │  │
│  │  Hauptinformationen          │  │  Status: Aktiv      │  │
│  │                              │  │  Erstellt: Datum    │  │
│  │  ┌─ Section ──────────────┐  │  │  Geändert: Datum    │  │
│  │  │ Details               │  │  │                     │  │
│  │  └────────────────────────┘  │  │  ┌─ Actions ─────┐  │  │
│  │                              │  │  │ [Bearbeiten]  │  │  │
│  │  ┌─ Section ──────────────┐  │  │  │ [Löschen]     │  │  │
│  │  │ Verknüpfte Daten      │  │  │  └───────────────┘  │  │
│  │  └────────────────────────┘  │  │                     │  │
│  │                              │  │                     │  │
│  └──────────────────────────────┘  └─────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Layout

| Bereich | Breite | Inhalt |
|---------|--------|--------|
| **Haupt-Content** | `col-md-8` | Stammdaten, Listen, Tabellen |
| **Meta-Sidebar** | `col-md-4` | Status, Timestamps, Quick-Actions |

#### Code-Beispiel

```html
<div class="row">
    <div class="col-md-8">
        <!-- Hauptinformationen -->
        <div class="card mb-4">
            <div class="card-header">
                <i class="ti ti-info-circle"></i> Details
            </div>
            <div class="card-body">
                <!-- Content -->
            </div>
        </div>
    </div>
    <div class="col-md-4">
        <!-- Meta-Informationen -->
        <div class="card">
            <div class="card-header">Status</div>
            <div class="card-body">
                <!-- Status, Timestamps -->
            </div>
        </div>
    </div>
</div>
```

---

## Modul-Header Gradient

Alle Views eines Moduls verwenden die Modul-Farbe als Gradient-Hintergrund im Header.
Dies schafft visuelle Konsistenz und Wiedererkennungswert innerhalb eines Moduls.

### Gradient-Formel

```css
background: linear-gradient(135deg, {color_hex}20 0%, transparent 70%);
```

- `{color_hex}` = Modul-Farbe (z.B. `#198754` für Kunden)
- `20` = Hex-Wert für ~12.5% Opazität
- `135deg` = Gradient von links-oben nach rechts-unten
- `transparent 70%` = Sanfter Übergang zu transparent

### Anwendung nach View-Typ

| View-Typ | Header-Stil |
|----------|-------------|
| **Listen** | Gradient + Icon-Kreis + Titel + Badge + Buttons |
| **Formulare** | Gradient + Titel + Buttons (ohne Icon-Kreis) |
| **Details** | Gradient + Icon-Kreis + Titel + Badges + Buttons |

### Code-Beispiel für Formulare

```html
{% set module = module_colors.get('modul_name', {'color_hex': '#198754', 'icon': 'ti-icon'}) %}

<div class="d-flex justify-content-between align-items-center mb-4 p-3 rounded"
     style="background: linear-gradient(135deg, {{ module.color_hex }}20 0%, transparent 70%);">
    <h2 class="mb-0">{{ titel }}</h2>
    <div class="d-flex gap-2">
        <a href="..." class="btn btn-outline-secondary">Abbrechen</a>
        <button type="submit" class="btn btn-primary">
            <i class="ti ti-check"></i> Speichern
        </button>
    </div>
</div>
```

---

## Komponenten-Richtlinien

### Breadcrumb

```html
{% from "macros/breadcrumb.html" import breadcrumb %}

{{ breadcrumb([
    {'label': 'Dashboard', 'url': url_for('main.dashboard'), 'icon': 'ti-home'},
    {'label': 'Modul', 'url': url_for('modul.liste'), 'icon': 'ti-icon'},
    {'label': 'Aktuelle Seite'}  {# Kein url = aktuelle Seite #}
]) }}
```

**Regeln:**
- Icons nur für Dashboard und Module (erste zwei Ebenen)
- Letzte Ebene ohne URL (aktuelle Seite)
- Maximal 4 Ebenen

### Buttons

| Typ | Klasse | Verwendung |
|-----|--------|------------|
| Primär | `btn btn-primary` | Hauptaktion (Speichern, Erstellen) |
| Sekundär | `btn btn-outline-secondary` | Abbrechen, Zurück |
| Gefahr | `btn btn-outline-danger` | Löschen (mit Confirm) |
| Link | `btn btn-link` | Nebensächliche Aktionen |

### Cards

```html
<div class="card">
    <div class="card-header">
        <i class="ti ti-icon"></i> Titel
    </div>
    <div class="card-body">
        <!-- Content -->
    </div>
</div>
```

### Badges

| Typ | Klasse | Verwendung |
|-----|--------|------------|
| Anzahl | `badge bg-secondary` | Zähler im Header |
| Status Aktiv | `badge bg-success` | Aktiver Status |
| Status Inaktiv | `badge bg-secondary` | Inaktiver Status |
| Typ/Kategorie | `badge bg-info` | Lead, Entwurf, etc. |

---

## Responsive Design

| Breakpoint | Verhalten |
|------------|-----------|
| `< 768px` (mobile) | Buttons unter Titel, 1-spaltig |
| `>= 768px` (tablet) | Buttons neben Titel, 2-spaltig |
| `>= 992px` (desktop) | Volle Breite, 8-4 Layout |

---

## Checkliste für neue Views

- [ ] Breadcrumb vorhanden?
- [ ] Titel mit korrektem Icon?
- [ ] Aktions-Buttons rechts oben?
- [ ] Wichtige Felder (Typ, Status) oben im Formular?
- [ ] Card-Struktur für Inhalte?
- [ ] Responsive Layout getestet?
- [ ] Help-Icons wo nötig?

---

## Verwandte PRDs

- [PRD-008: Breadcrumb-Navigation](../PRD-008-breadcrumb-navigation/PRD-008-breadcrumb-navigation.md)
- [PRD-005: Hilfetexte](../PRD-005-hilfetexte/PRD-005-hilfetexte.md)
