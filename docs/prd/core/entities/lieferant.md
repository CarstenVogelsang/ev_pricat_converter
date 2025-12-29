# Entity: Lieferant

## Beschreibung

Lieferanten aus dem VEDES-Katalog, die Produkte über PRICAT-Dateien bereitstellen. Ein Lieferant kann mehreren Handelsbranchen zugeordnet sein (max. 3), wobei eine als Hauptbranche markiert wird.

**Dateien:**
- Model: `app/models/lieferant.py`
- Junction-Table: `app/models/lieferant_branche.py`
- Routes: `app/routes/admin.py`
- Templates: `app/templates/administration/lieferanten.html`, `lieferant_form.html`

---

## Datenbankschema

### Tabelle: `lieferant`

| Feld | Typ | Constraint | Beschreibung |
|------|-----|------------|--------------|
| `id` | Integer | PK | Auto-Increment Primary Key |
| `gln` | String(13) | UNIQUE, NULL | Global Location Number (optional) |
| `vedes_id` | String(13) | UNIQUE, NOT NULL, INDEX | Eindeutige VEDES-Lieferanten-ID |
| `kurzbezeichnung` | String(40) | NOT NULL | Name des Lieferanten |
| `aktiv` | Boolean | NOT NULL, DEFAULT FALSE | Aktiv im PRICAT-Converter |
| `ftp_quelldatei` | String(255) | NULL | Dateiname der PRICAT-Quelle |
| `ftp_pfad_ziel` | String(255) | NULL | Zielverzeichnis für Export |
| `elena_startdir` | String(50) | NULL | ELENA Start-Verzeichnis |
| `elena_base_url` | String(255) | NULL | ELENA Basis-URL |
| `letzte_konvertierung` | DateTime | NULL | Zeitpunkt letzter Konvertierung |
| `artikel_anzahl` | Integer | NULL | Anzahl Artikel in PRICAT |
| `ftp_datei_datum` | DateTime | NULL | Änderungsdatum der FTP-Datei |
| `ftp_datei_groesse` | Integer | NULL | Dateigröße in Bytes |
| `created_at` | DateTime | DEFAULT NOW | Erstellungszeitpunkt |
| `updated_at` | DateTime | ON UPDATE | Letzter Änderungszeitpunkt |

### Tabelle: `lieferant_branche` (Junction)

| Feld | Typ | Constraint | Beschreibung |
|------|-----|------------|--------------|
| `id` | Integer | PK | Auto-Increment Primary Key |
| `lieferant_id` | Integer | FK, NOT NULL | Referenz auf `lieferant.id` |
| `branche_id` | Integer | FK, NOT NULL | Referenz auf `branche.id` |
| `ist_hauptbranche` | Boolean | NOT NULL, DEFAULT FALSE | Hauptbranche-Markierung |
| `created_at` | DateTime | DEFAULT NOW | Erstellungszeitpunkt |

**Constraints:**
- `uq_lieferant_branche`: UNIQUE(`lieferant_id`, `branche_id`)
- FK `lieferant_id` → `lieferant.id` ON DELETE CASCADE
- FK `branche_id` → `branche.id` ON DELETE CASCADE

---

## Beziehungen

```
┌─────────────┐       ┌───────────────────┐       ┌─────────────┐
│  Lieferant  │ 1───N │ LieferantBranche  │ N───1 │   Branche   │
└─────────────┘       └───────────────────┘       └─────────────┘
       │                      │
       │                      └── ist_hauptbranche
       │
       └── branchen (relationship)
```

### M:N zu Branche
- Über Junction-Table `lieferant_branche`
- Max. 3 Branchen pro Lieferant
- Nur HANDEL-Unterbranchen erlaubt (`parent_id = HANDEL.id`)
- Eine Branche muss als `ist_hauptbranche` markiert sein

### 1:N zu Produkt (geplant)
- Ein Lieferant hat viele Produkte
- Definiert in PRD-009

---

## Properties & Methoden

### `hauptbranche` (Property)
```python
@property
def hauptbranche(self):
    """Die Hauptbranche des Lieferanten.

    Returns:
        Branche object oder None
    """
    for lb in self.branchen:
        if lb.ist_hauptbranche:
            return lb.branche
    # Fallback: erste zugeordnete Branche
    return self.branchen[0].branche if self.branchen else None
```

### `alle_branchen` (Property)
```python
@property
def alle_branchen(self):
    """Alle zugeordneten Branchen.

    Returns:
        List[Branche]
    """
    return [lb.branche for lb in self.branchen]
```

### `to_dict()` (Methode)
Serialisiert den Lieferanten für JSON-Responses.

---

## UI & Routes

### Listenansicht: `/admin/lieferanten`

**Features (implementiert 2025-12-29):**
- Tabelle mit Spalten: Name, VEDES-ID, GLN, Branche, Status, Aktionen
- **Filter:**
  - Branche-Dropdown (alle HANDEL-Unterbranchen)
  - Status-Dropdown (Aktiv/Inaktiv/Alle)
  - Auto-Submit bei Auswahl
- **Suche:**
  - Server-seitig mit `?q=` Parameter
  - Durchsucht: `kurzbezeichnung`, `vedes_id`, `gln`
- **Hauptbranche-Spalte:**
  - Zeigt Branchen-Icon mit Tooltip
  - "—" wenn keine Branche zugeordnet

**URL-Parameter:**
| Parameter | Typ | Beschreibung |
|-----------|-----|--------------|
| `branche` | Integer | Filter nach Hauptbranche-ID |
| `status` | String | `aktiv` oder `inaktiv` |
| `q` | String | Suchbegriff |

**Beispiele:**
- `/admin/lieferanten?status=aktiv` - Nur aktive Lieferanten
- `/admin/lieferanten?branche=2&q=LEGO` - Spielwaren-Lieferanten mit "LEGO"

### Detailansicht: `/admin/lieferanten/form/<id>`

**Features (implementiert 2025-12-29):**
- Stammdaten-Formular (Kurzbezeichnung, VEDES-ID, GLN, Aktiv)
- **Branchen-Zuordnung Card:**
  - Anklickbare Icon-Buttons für alle HANDEL-Unterbranchen
  - Linksklick: Branche zuordnen/entfernen (Toggle)
  - Rechtsklick: Als Hauptbranche setzen
  - Badge "H" für Hauptbranche
  - Counter "X/3" zeigt aktuelle Anzahl
- PRICAT-Informationen (nur Anzeige)

### AJAX-Endpoints

| Route | Method | Funktion |
|-------|--------|----------|
| `/admin/lieferanten/<id>/branchen/<branche_id>` | POST | Branche zuordnen |
| `/admin/lieferanten/<id>/branchen/<branche_id>` | DELETE | Branche entfernen |
| `/admin/lieferanten/<id>/branchen/<branche_id>/hauptbranche` | POST | Als Hauptbranche setzen |

**Geschäftsregeln:**
- Max. 3 Branchen pro Lieferant
- Erste zugeordnete Branche wird automatisch Hauptbranche
- Beim Entfernen der Hauptbranche: nächste Branche wird Hauptbranche
- Nur HANDEL-Unterbranchen sind zuordenbar

---

## Verwendung in Modulen

| Modul | PRD | Verwendung |
|-------|-----|------------|
| PRICAT Converter | PRD-001 | Konvertierung von PRICAT-Dateien |
| Kunde-Lieferanten | PRD-003 | Zuordnung von Kunden zu Lieferanten (geplant) |
| Produktdaten | PRD-009 | Lieferant als Quelle für Produkte |

---

## Änderungshistorie

### 2025-12-29: Branchen-Zuordnung & Filter

**Migration:** `46224706c611_add_lieferantbranche_junction_table.py`

**Änderungen am Model:**
- Neue Junction-Table `lieferant_branche` für M:N zu Branche
- Properties `hauptbranche` und `alle_branchen` hinzugefügt
- Relationship `branchen` mit `cascade='all, delete-orphan'`

**Änderungen an Routes:**
- `lieferanten()`: Filter für Branche, Status, Suchbegriff
- Neue AJAX-Endpoints für Branchen-Verwaltung

**Änderungen an Templates:**
- `lieferanten.html`: Filter-Card, Hauptbranche-Spalte, Tooltips
- `lieferant_form.html`: Branchen-Card mit Icon-Buttons

**Begründung:**
Lieferanten liefern Produkte aus mehreren Unterbranchen der Branche HANDEL. Die Zuordnung ermöglicht:
- Filterung nach Hauptbranche in der Listenansicht
- Bessere Kategorisierung für Kunden-Lieferanten-Zuordnung (PRD-003)
- Visuelle Darstellung über Branchen-Icons

### 2025-12-28: Stammdaten-CRUD

**Änderungen:**
- Route `/admin/lieferanten` für Stammdaten-Verwaltung
- Neue Templates `lieferanten.html`, `lieferant_form.html`
- CRUD-Operationen (Create, Read, Update, Delete)
- Trennung von PRICAT-spezifischen Feldern (nur Anzeige)

**Begründung:**
PRICAT-Converter Route wurde von `/lieferanten` nach `/pricat-converter` verschoben. Die freie Route wird nun für allgemeine Stammdaten-Verwaltung genutzt.

### 2025-12-04: Initiale Erstellung

**Migration:** Initiale DB-Erstellung

**Felder:**
- Basis-Felder: `id`, `gln`, `vedes_id`, `kurzbezeichnung`, `aktiv`
- PRICAT-Felder: `ftp_quelldatei`, `ftp_pfad_ziel`, `elena_startdir`, `elena_base_url`
- Statistik-Felder: `letzte_konvertierung`, `artikel_anzahl`
- Timestamps: `created_at`, `updated_at`

---

## Testdaten (Seed)

```python
# Beispiel-Lieferant aus seed.py
Lieferant(
    vedes_id='1872',
    kurzbezeichnung='LEGO Spielwaren GmbH',
    gln='4023017000005',
    aktiv=True
)
```

Nach dem Seed kann die Branchen-Zuordnung über die UI erfolgen:
1. `/admin/lieferanten` → LEGO bearbeiten
2. Spielwaren-Icon klicken → wird automatisch Hauptbranche
