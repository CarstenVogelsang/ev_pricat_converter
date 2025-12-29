# Changelog PRD-009: Produktdaten-Verwaltung

Alle wesentlichen Änderungen am Produktdaten-Modul.

Format: [Keep a Changelog](https://keepachangelog.com/de/1.0.0/)

---

## [0.1.0] - 2025-12-28

### Added

- **ProduktLookup Model** (`app/models/produkt_lookup.py`)
  - Speichert produkt-spezifische Codelisten (Länder, Währungen, Batterien, etc.)
  - 15 Kategorien mit 860 Einträgen
  - Methoden: `get_by_kategorie()`, `get_by_code()`, `get_choices()`

- **Attributgruppe Model** (`app/models/attributgruppe.py`)
  - 5-Ebenen Produktklassifikation nach NTG-Standard
  - 1.386 Einträge importiert
  - Methoden: `get_hauptkategorien()`, `get_by_ebene_1()`, `suche()`

- **EigenschaftDefinition Model** (`app/models/eigenschaft_definition.py`)
  - Definiert Produkteigenschaften mit Datentyp und Validierung
  - Unterstützt: text, number, integer, boolean, date, codelist
  - Codelist-Referenz zu ProduktLookup

- **EigenschaftWert Model** (`app/models/eigenschaft_wert.py`)
  - EAV-Pattern für flexible Produkteigenschaften
  - Typspezifische Wert-Spalten (wert_text, wert_number, wert_boolean, etc.)
  - Automatische Wert-Konvertierung basierend auf Datentyp

- **Produkt Model** (`app/models/produkt.py`)
  - Zentrale Produktstammdaten mit NTG-Kernfeldern
  - Beziehungen zu Lieferant, Attributgruppe, User
  - Helper-Methoden für Eigenschaften: `get_eigenschaft()`, `set_eigenschaft()`

- **Import-Scripts**
  - `scripts/import_produkt_codelisten.py` - Importiert 15 Codelisten
  - `scripts/import_attributgruppen.py` - Importiert 1.386 Attributgruppen

- **Admin-UI**
  - Neue Kacheln in Stammdaten-Übersicht für Produktdaten
  - `/admin/produkte` - Produktliste mit Suche
  - `/admin/produkt-lookup` - Codelisten nach Kategorie
  - `/admin/attributgruppen` - 5-Ebenen Klassifikation mit Suche
  - `/admin/eigenschaft-definitionen` - Eigenschafts-Definitionen

- **Migrationen**
  - `ffa7e6fe81a2_add_produktlookup_and_attributgruppe_.py`
  - `0a8a1f543f8e_add_eigenschaftdefinition_produkt_.py`

### Dokumentation

- PRD-009-produktdaten.md erstellt
- CHANGELOG.md erstellt

---

## Geplante Features

- [ ] Produkt-Formular mit dynamischen Eigenschaften
- [ ] Excel-Import/Export für Produkte
- [ ] Seed-Script für EigenschaftDefinitionen aus NTG-Feldern
- [ ] API-Endpunkte für Produktdaten
