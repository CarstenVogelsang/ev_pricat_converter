# Entity: Branche

## Beschreibung

Hierarchische Branchen-Struktur zur Kategorisierung von Kunden und Lieferanten. Unterstützt 2-stufige Hierarchie: Hauptbranchen (z.B. HANDEL) und Unterbranchen (z.B. Spielwaren, Modellbahn).

**Dateien:**
- Model: `app/models/branche.py`
- BranchenRolle: `app/models/branchenrolle.py`
- Junction: `app/models/branche_branchenrolle.py`
- Routes: `app/routes/admin.py`
- Templates: `app/templates/administration/branchen.html`

---

## Datenbankschema

### Tabelle: `branche`

| Feld | Typ | Constraint | Beschreibung |
|------|-----|------------|--------------|
| `id` | Integer | PK | Auto-Increment Primary Key |
| `uuid` | String(36) | UNIQUE, NOT NULL | UUID für externe Integration |
| `parent_id` | Integer | FK, NULL | NULL = Hauptbranche, sonst Unterbranche |
| `name` | String(100) | NOT NULL | Branchenname |
| `slug` | String(100) | NULL | URL-freundlicher Name |
| `icon` | String(50) | NOT NULL | Tabler Icon Name (z.B. "lego") |
| `aktiv` | Boolean | DEFAULT TRUE | Aktiv-Status |
| `sortierung` | Integer | DEFAULT 0 | Sortierreihenfolge |

**Constraints:**
- `uq_branche_parent_name`: UNIQUE(`parent_id`, `name`) - Name pro Ebene eindeutig

### Tabelle: `branchenrolle`

| Feld | Typ | Constraint | Beschreibung |
|------|-----|------------|--------------|
| `id` | Integer | PK | Auto-Increment Primary Key |
| `name` | String(100) | NOT NULL | Rollenname |
| `beschreibung` | Text | NULL | Beschreibung |
| `icon` | String(50) | NOT NULL | Tabler Icon Name |
| `aktiv` | Boolean | DEFAULT TRUE | Aktiv-Status |
| `sortierung` | Integer | DEFAULT 0 | Sortierreihenfolge |

### Tabelle: `branche_branchenrolle` (Junction)

| Feld | Typ | Constraint | Beschreibung |
|------|-----|------------|--------------|
| `branche_id` | Integer | FK, NOT NULL | Referenz auf `branche.id` |
| `branchenrolle_id` | Integer | FK, NOT NULL | Referenz auf `branchenrolle.id` |

---

## Hierarchie

```
HANDEL (parent_id=NULL)
├── Spielwaren (parent_id=HANDEL.id)
├── Modellbahn
├── Fahrrad
├── GPK (Glas Porzellan Keramik)
├── Geschenkartikel
├── Schreibwaren
├── Buchhandel
├── Fachmarkt
├── Babyausstattung
├── IT Software
└── Allgemein

DIENSTLEISTUNG (parent_id=NULL)
├── ...

HANDWERK (parent_id=NULL)
├── ...
```

---

## Beziehungen

```
┌─────────────┐
│   Branche   │◄─────┐ (self-referential)
└─────────────┘      │
       │             │
       │ parent_id ──┘
       │
       │ N:M
       ▼
┌─────────────────────┐       ┌─────────────────┐
│ BrancheBranchenRolle│ N───1 │  BranchenRolle  │
└─────────────────────┘       └─────────────────┘
```

### Verwendung in anderen Entities

- **Kunde:** M:N über `kunde_branche` + FK `hauptbranche_id`
- **Lieferant:** M:N über `lieferant_branche` (max. 3 HANDEL-Unterbranchen)

---

## Properties

### `ist_hauptbranche`
```python
@property
def ist_hauptbranche(self):
    """True wenn parent_id=NULL."""
    return self.parent_id is None
```

### `voller_name`
```python
@property
def voller_name(self):
    """Hierarchischer Name, z.B. 'HANDEL > Spielwaren'."""
    if self.parent:
        return f'{self.parent.name} > {self.name}'
    return self.name
```

### `zulaessige_branchenrollen`
```python
@property
def zulaessige_branchenrollen(self):
    """Liste aktiver BranchenRollen für diese Branche."""
    return [zbr.branchenrolle for zbr in self.zulaessige_rollen if zbr.branchenrolle.aktiv]
```

---

## BranchenRollen-System (V2)

Das BranchenRollen-System erlaubt die Zuordnung von Rollen pro Branche zu Kunden:

```
Kunde
  └── KundeBranchenRolle (branche_id, branchenrolle_id)
        └── z.B. "Spielwaren" + "Händler"
        └── z.B. "Spielwaren" + "Hersteller"
```

**Anwendungsfall:** Ein Kunde kann in verschiedenen Branchen unterschiedliche Rollen haben (Händler, Hersteller, Importeur, etc.).

---

## Verwendung in Modulen

| Modul | PRD | Verwendung |
|-------|-----|------------|
| Basis-Plattform | - | Kunden-Kategorisierung |
| PRICAT Converter | PRD-001 | Lieferant-Hauptbranche für Filter |
| Lead & Kundenreport | PRD-002 | Kunden nach Branche filtern |
| Kunde-Lieferanten | PRD-003 | Matching nach Branche (geplant) |

---

## Admin-UI

### Branchen-Verwaltung: `/admin/branchen`

**Features:**
- Hierarchische Darstellung (Hauptbranche → Unterbranchen)
- Icon-Picker für visuelle Darstellung
- Drag & Drop für Sortierung (geplant)
- Inline-Bearbeitung von Name und Icon

### Branchen als Filter

In der Lieferanten-Liste (`/admin/lieferanten`) werden nur **HANDEL-Unterbranchen** als Filter angeboten:

```python
handel = Branche.query.filter_by(name='HANDEL', parent_id=None).first()
handel_unterbranchen = Branche.query.filter_by(
    parent_id=handel.id,
    aktiv=True
).order_by(Branche.sortierung).all()
```

---

## Änderungshistorie

### 2025-12-29: Lieferant-Branchen-Zuordnung
- Neue Verwendung in `lieferant_branche` Junction
- Filter nach Hauptbranche in Lieferanten-Liste

### 2025-12-20: BranchenRollen V2
- Neues Model `BranchenRolle`
- Junction `branche_branchenrolle` für zulässige Rollen pro Branche
- Junction `kunde_branchenrolle` für Kunden-Zuordnung

### 2025-12-06: Initiale Erstellung
- 2-stufige Hierarchie (Haupt- und Unterbranchen)
- UUID für externe Integration
- Icon und Sortierung
