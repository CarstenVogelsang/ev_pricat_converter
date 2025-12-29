# Entity: Produkt

## Beschreibung

Produktstammdaten nach NTG-Standard (Normdatensatz für den Technischen Großhandel). Kern-Felder werden direkt am Produkt gespeichert, erweiterte Eigenschaften über das EAV-Pattern (Entity-Attribute-Value) in `eigenschaft_wert`.

**Dateien:**
- Model: `app/models/produkt.py`
- EAV-System: `app/models/eigenschaft_definition.py`, `app/models/eigenschaft_wert.py`
- Attributgruppen: `app/models/attributgruppe.py`
- Routes: `app/routes/admin.py` (Produkte-Admin)

---

## Datenbankschema

### Tabelle: `produkt`

#### Identifikation
| Feld | Typ | Constraint | NTG | Beschreibung |
|------|-----|------------|-----|--------------|
| `id` | Integer | PK | - | Auto-Increment Primary Key |
| `ean` | String(14) | UNIQUE, NOT NULL, INDEX | P-007 | EAN/GTIN (Pflichtfeld) |
| `artikelnummer_lieferant` | String(35) | INDEX | P-013 | Lieferanten-Artikelnummer |
| `artikelnummer_hersteller` | String(35) | NULL | P-014 | Hersteller-Artikelnummer |

#### Lieferant-Beziehung
| Feld | Typ | Constraint | NTG | Beschreibung |
|------|-----|------------|-----|--------------|
| `lieferant_id` | Integer | FK, NULL | - | Interne Lieferant-Zuordnung |
| `gln_lieferant` | String(13) | NULL | P-001 | GLN des Lieferanten |

#### Grunddaten
| Feld | Typ | Constraint | NTG | Beschreibung |
|------|-----|------------|-----|--------------|
| `artikelbezeichnung` | String(250) | NOT NULL | P-015 | Artikelbezeichnung |
| `kurzbezeichnung` | String(35) | NULL | P-016 | Kurzbezeichnung |
| `hersteller_name` | String(35) | NULL | P-004 | Hersteller-Name |
| `markenname` | String(35) | NULL | P-010 | Markenname |
| `serienname` | String(35) | NULL | P-012 | Serienname |

#### Preise
| Feld | Typ | Constraint | NTG | Beschreibung |
|------|-----|------------|-----|--------------|
| `uvpe` | Numeric(15,2) | NULL | P-067 | Unverbindliche Preisempfehlung |
| `ekp_netto` | Numeric(15,4) | NULL | P-091 | Einkaufspreis netto |
| `mwst_satz` | Numeric(5,2) | NULL | P-068 | MwSt-Satz |
| `waehrung` | String(3) | DEFAULT 'EUR' | P-069 | Währung (ISO 4217) |

#### Logistik (Stück-Ebene)
| Feld | Typ | Constraint | NTG | Beschreibung |
|------|-----|------------|-----|--------------|
| `stueck_laenge_cm` | Numeric(18,3) | NULL | P-031 | Länge in cm |
| `stueck_breite_cm` | Numeric(18,3) | NULL | P-032 | Breite in cm |
| `stueck_hoehe_cm` | Numeric(18,3) | NULL | P-033 | Höhe in cm |
| `stueck_gewicht_kg` | Numeric(18,3) | NULL | P-034 | Gewicht in kg |

#### Klassifikation
| Feld | Typ | Constraint | NTG | Beschreibung |
|------|-----|------------|-----|--------------|
| `attributgruppe_id` | Integer | FK, NULL | P-146 | 5-Ebenen Produktkategorie |
| `zolltarif_nr` | String(11) | NULL | P-089 | Zolltarifnummer |
| `ursprungsland` | String(2) | NULL | P-097 | ISO 3166-1 alpha-2 |

#### Status & Termine
| Feld | Typ | Constraint | NTG | Beschreibung |
|------|-----|------------|-----|--------------|
| `status` | String(15) | DEFAULT 'entwurf' | - | entwurf/aktiv/auslauf/archiviert |
| `lieferbar_ab` | Date | NULL | P-074 | Verfügbar ab |
| `lieferbar_bis` | Date | NULL | P-075 | Verfügbar bis |
| `erste_auslieferung` | Date | NULL | P-076 | Erste Auslieferung |

#### Langtexte
| Feld | Typ | Constraint | NTG | Beschreibung |
|------|-----|------------|-----|--------------|
| `b2c_text` | Text | NULL | P-156 | B2C Werbetext (bis 6000 Z.) |
| `b2b_kurztext` | String(500) | NULL | P-155 | B2B Kurztext |

#### Meta
| Feld | Typ | Constraint | Beschreibung |
|------|-----|------------|--------------|
| `created_at` | DateTime | DEFAULT NOW | Erstellungszeitpunkt |
| `updated_at` | DateTime | ON UPDATE | Letzter Änderungszeitpunkt |
| `created_by_id` | Integer | FK, NULL | Ersteller (User) |

---

## EAV-System (Eigenschaft-Wert)

Erweiterte Eigenschaften werden über das EAV-Pattern gespeichert:

```
┌─────────────────────────┐       ┌───────────────────┐
│  EigenschaftDefinition  │       │  EigenschaftWert  │
├─────────────────────────┤       ├───────────────────┤
│ ntg_code (z.B. "P-123") │◄──────│ definition_id     │
│ bezeichnung             │       │ produkt_id        │
│ daten_typ (Text/Number) │       │ wert_text         │
│ einheit                 │       │ wert_number       │
│ gruppe                  │       │ wert_date         │
└─────────────────────────┘       └───────────────────┘
```

### Vorteile des EAV-Patterns:
- **Flexibilität:** Neue Eigenschaften ohne Schema-Migration
- **NTG-Konformität:** Alle 200+ NTG-Felder abbildbar
- **Sparse Data:** Nur gesetzte Werte werden gespeichert

### Nachteile:
- **Query-Komplexität:** JOINs für Eigenschafts-Abfragen
- **Keine DB-Validierung:** Datentypen werden im Code validiert

---

## Beziehungen

```
┌─────────────┐
│   Produkt   │
└─────────────┘
       │
       ├── N:1 → Lieferant (lieferant_id)
       │
       ├── N:1 → Attributgruppe (attributgruppe_id)
       │
       ├── N:1 → User (created_by_id)
       │
       └── 1:N → EigenschaftWert (eigenschaften)
```

---

## Status-Workflow

```
┌──────────┐     ┌────────┐     ┌─────────┐     ┌─────────────┐
│ Entwurf  │────►│ Aktiv  │────►│ Auslauf │────►│ Archiviert  │
└──────────┘     └────────┘     └─────────┘     └─────────────┘
```

| Status | Bedeutung |
|--------|-----------|
| `entwurf` | In Bearbeitung, nicht veröffentlicht |
| `aktiv` | Verfügbar für Kunden |
| `auslauf` | Abverkauf, keine Nachbestellung |
| `archiviert` | Nicht mehr sichtbar |

---

## Properties & Methoden

### `vollstaendiger_name`
```python
@property
def vollstaendiger_name(self):
    """Marke + Bezeichnung für Anzeige."""
    if self.markenname:
        return f"{self.markenname} - {self.artikelbezeichnung}"
    return self.artikelbezeichnung
```

### `kategorie_pfad`
```python
@property
def kategorie_pfad(self):
    """Vollständiger Kategorie-Pfad aus Attributgruppe."""
    return self.attributgruppe.vollstaendiger_name if self.attributgruppe else None
```

### Class Methods
- `get_by_ean(ean)`: Produkt nach EAN suchen
- `suche(suchbegriff, limit)`: Volltextsuche
- `get_by_lieferant(lieferant_id)`: Produkte eines Lieferanten
- `count_by_status()`: Statistik nach Status

### Eigenschaft-Helper
- `get_eigenschaft(ntg_code)`: Einzelne Eigenschaft lesen
- `set_eigenschaft(ntg_code, value)`: Eigenschaft setzen
- `get_eigenschaften_by_gruppe(gruppe)`: Alle Eigenschaften einer Gruppe

---

## Verwendung in Modulen

| Modul | PRD | Verwendung |
|-------|-----|------------|
| Produktdaten | PRD-009 | Hauptmodul für Produktverwaltung |
| PRICAT Converter | PRD-001 | Import von PRICAT-Produktdaten |
| Content Generator | PRD-004 | KI-Texterstellung für Produkte (geplant) |

---

## Attributgruppen (5-Ebenen)

Hierarchische Produktkategorisierung nach ETIM/NTG:

```
Ebene 1: Branche (z.B. "Spielwaren")
└── Ebene 2: Gruppe (z.B. "Bausteine")
    └── Ebene 3: Untergruppe (z.B. "LEGO")
        └── Ebene 4: Klasse (z.B. "City")
            └── Ebene 5: Attributgruppe (z.B. "Fahrzeuge")
```

---

## Änderungshistorie

### 2025-12-28: PRD-009 Implementierung
- Neues Produkt-Model mit NTG-Kern-Feldern
- EAV-System für erweiterte Eigenschaften
- Attributgruppen für Kategorisierung
- Admin-UI für Produktverwaltung

### Geplant: PRICAT-Import
- Automatischer Import aus PRICAT-Dateien
- Mapping von NTG-Feldern auf Produkt-Columns
- Delta-Import für Aktualisierungen
