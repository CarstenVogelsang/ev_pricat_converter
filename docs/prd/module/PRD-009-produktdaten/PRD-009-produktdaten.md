# PRD-009: Produktdaten-Verwaltung

**Status:** MVP implementiert
**Modul:** Administration → Stammdaten → Produktdaten
**Erstellt:** 2025-12-28

---

## Übersicht

Dieses Modul implementiert ein vollständiges Produktdaten-Verwaltungssystem basierend auf dem NTG-Standard (Nationale Artikeldatennorm für die Spielwarenbranche).

### Kernfunktionen

1. **ProduktLookup** - Produkt-spezifische Codelisten (Länder, Währungen, Batterien, etc.)
2. **Attributgruppen** - 5-Ebenen hierarchische Produktklassifikation (1684 Einträge)
3. **EigenschaftDefinition** - Flexible Produkt-Eigenschafts-Definitionen
4. **Produkt** - Zentrale Produktstammdaten mit EAV-Pattern für Eigenschaften
5. **EigenschaftWert** - Eigenschaftswerte pro Produkt

---

## Architektur

### Entity-Relationship-Diagramm

```
Lieferant (1) ──┐
                │
Attributgruppe (1) ──┐
                     ├── Produkt (n) ── EigenschaftWert (n) ── EigenschaftDefinition (1)
                     │                         │
                     │                         └── ProduktLookup (für Codelist-Werte)
                     │
User (created_by) ───┘
```

### Tabellenstruktur

| Tabelle | Beschreibung | Einträge |
|---------|--------------|----------|
| `produkt_lookup` | Codelisten (Länder, Währungen, Batterien, etc.) | 860 |
| `attributgruppe` | 5-Ebenen Produktklassifikation | 1.386 |
| `eigenschaft_definition` | Eigenschafts-Feld-Definitionen | 0 (MVP) |
| `produkt` | Produktstammdaten | 0 (MVP) |
| `eigenschaft_wert` | Eigenschaftswerte pro Produkt | 0 (MVP) |

---

## Datenmodelle

### ProduktLookup

Speichert 15 Codelisten für Produktdaten:

| Kategorie | Einträge | Beschreibung |
|-----------|----------|--------------|
| `laender` | 255 | ISO 3166-1 Ländercodes |
| `batterien` | 84 | Batterietypen (ANSI, IEC, Volt) |
| `gefahrstoffe` | 246 | P-Sätze, H-Sätze, EUH-Sätze |
| `bamberger` | 70 | Bamberger Verzeichnis |
| `genre` | 44 | Medien-Genres |
| `saison` | 31 | Saisonkennzeichen |
| `mwst_saetze` | 27 | MwSt-Sätze pro Land |
| `lagerklassen` | 26 | Lagerklassen Gefahrstoffe |
| `gefahrengut` | 17 | Gefahrgutschlüssel |
| `plattform` | 17 | Gaming-Plattformen |
| `gpc_brick` | 12 | GPC Produktkategorien |
| `gewichtseinheiten` | 12 | Gewichts- und Maßeinheiten |
| `dvd_bluray_codes` | 11 | DVD/Blu-Ray Region Codes |
| `weee_kennzeichnung` | 5 | WEEE-Kategorien |
| `waehrungen` | 3 | Währungscodes |

### Attributgruppe

5-Ebenen Produktklassifikation nach NTG:

| Ebene | Beschreibung | Beispiel |
|-------|--------------|----------|
| 1 | Hauptkategorie | Spielzeug |
| 2 | Unterkategorie | Baby- & Kleinkindspielzeug |
| 3 | Sub-Unterkategorie | Babyspielzeug |
| 4 | Produktgruppe | Babybälle |
| 5 | Spezifischer Typ | Babybälle |

### Produkt

Kernfelder direkt am Produkt:

| Feld | NTG-Code | Typ | Beschreibung |
|------|----------|-----|--------------|
| `ean` | NTG-P-007 | String(14) | EAN/GTIN (Pflicht) |
| `artikelnummer_lieferant` | NTG-P-013 | String(35) | Lieferanten-Artikelnummer |
| `artikelbezeichnung` | NTG-P-015 | String(250) | Artikelbezeichnung (Pflicht) |
| `markenname` | NTG-P-010 | String(35) | Markenname |
| `uvpe` | NTG-P-067 | Decimal(15,2) | Unverb. Preisempfehlung |
| `stueck_laenge_cm` | NTG-P-031 | Decimal(18,3) | Länge in cm |
| `stueck_breite_cm` | NTG-P-032 | Decimal(18,3) | Breite in cm |
| `stueck_hoehe_cm` | NTG-P-033 | Decimal(18,3) | Höhe in cm |
| `stueck_gewicht_kg` | NTG-P-034 | Decimal(18,3) | Gewicht in kg |
| `zolltarif_nr` | NTG-P-089 | String(11) | Zolltarifnummer |
| `ursprungsland` | NTG-P-097 | String(2) | Ursprungsland (ISO) |

### EigenschaftWert (EAV-Pattern)

Flexible Produkteigenschaften mit typisierten Wert-Spalten:

| Spalte | Verwendung |
|--------|------------|
| `wert_text` | Text, Codelist-Codes |
| `wert_number` | Dezimalzahlen |
| `wert_integer` | Ganzzahlen |
| `wert_boolean` | Ja/Nein |
| `wert_date` | Datumsangaben |

---

## Admin-UI

### Zugang

Administration → Stammdaten → Produktdaten (PRD-009)

### Seiten

| Seite | Route | Beschreibung |
|-------|-------|--------------|
| Produkte | `/admin/produkte` | Produktliste mit Suche |
| Produkt-Codelisten | `/admin/produkt-lookup` | 15 Codelisten anzeigen |
| Attributgruppen | `/admin/attributgruppen` | 5-Ebenen Klassifikation |
| Eigenschaften | `/admin/eigenschaft-definitionen` | Eigenschafts-Definitionen |

---

## Import-Scripts

### Codelisten importieren

```bash
uv run python scripts/import_produkt_codelisten.py
```

Liest `NTG_Artikelstamm-Codelisten.xls` und importiert 860 Einträge.

### Attributgruppen importieren

```bash
uv run python scripts/import_attributgruppen.py
```

Liest `NTG_Attributgruppenschluessel.xlsx` und importiert 1.386 Einträge.

---

## Quelldokumente

Im Ordner `docs/prd/module/PRD-009-produktdaten/`:

| Dokument | Inhalt |
|----------|--------|
| `NTG_Artikelvorlage_gruppiert.xlsx` | 377 Felder mit NTG-P-Codes |
| `Artikeldaten_Feldbeschreibung.pdf` | 18 Seiten, 399 Feldbeschreibungen |
| `NTG_Artikelstamm-Codelisten.xls` | 15 Codelisten (~900 Einträge) |
| `NTG_Attributgruppenschluessel.xlsx` | 5-Ebenen Kategorien (1684) |

---

## Roadmap

### Phase 1: Grundlagen (✅ abgeschlossen)

- [x] ProduktLookup Model + Import
- [x] Attributgruppe Model + Import
- [x] Admin-UI für Codelisten und Attributgruppen

### Phase 2: Eigenschaften-System (✅ abgeschlossen)

- [x] EigenschaftDefinition Model
- [x] EigenschaftWert Model (EAV-Pattern)
- [x] Admin-UI für Eigenschaften

### Phase 3: Produkt-Verwaltung (✅ abgeschlossen)

- [x] Produkt Model mit Kern-Feldern
- [x] Admin-UI Produkt-Liste

### Phase 4: Erweiterungen (geplant)

- [ ] Produkt-Formular mit dynamischen Eigenschaften
- [ ] Excel-Import für Produkte
- [ ] Excel-Export für Produkte
- [ ] Seed-Script für EigenschaftDefinitionen aus NTG-Feldern

---

## Technische Notizen

### EAV-Pattern Vorteile

1. **Flexibilität**: Neue Eigenschaften ohne Schema-Änderung
2. **Speichereffizienz**: Nur gesetzte Eigenschaften werden gespeichert
3. **Typsicherheit**: Datentyp in Definition, passende Wert-Spalte verwendet

### NTG-Feldformat-Mapping

| NTG-Format | Python-Typ | DB-Spalte |
|------------|------------|-----------|
| `n13`, `n15` | `Decimal` | `wert_number` |
| `an1` (J/N) | `Boolean` | `wert_boolean` |
| `an35`, `an250` | `String` | `wert_text` |
| `an6000` | `Text` | `wert_text` |
| `DD.MM.YYYY` | `Date` | `wert_date` |
| Codelist | `FK` | `wert_text` (Code) |

---

## Abhängigkeiten

- **Lieferant**: Produkt.lieferant_id → Lieferant.id
- **User**: Produkt.created_by_id → User.id
- **Attributgruppe**: Produkt.attributgruppe_id → Attributgruppe.id
