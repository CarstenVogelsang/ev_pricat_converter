# Entity-Dokumentation

Zentrale Dokumentation aller Datenbank-Entities der ev247-Plattform.

## Übersicht

| Entity | Beschreibung | Modul-Bezug |
|--------|--------------|-------------|
| [Lieferant](lieferant.md) | VEDES-Lieferanten mit Branchen-Zuordnung | PRD-001, PRD-003 |
| [Kunde](kunde.md) | Kunden mit CI, Branchen, Verbänden | PRD-002, PRD-006 |
| [Branche](branche.md) | Hierarchische Branchen-Struktur | Basis |
| [Produkt](produkt.md) | Produktdaten mit Eigenschaften | PRD-009 |

## Struktur der Entity-Dokumente

Jedes Entity-Dokument folgt dieser Struktur:

```markdown
# Entity: [Name]

## Beschreibung
[Kurze Beschreibung des Zwecks]

## Datenbankschema
[Tabellenstruktur mit Feldern, Typen, Constraints]

## Beziehungen
[M:N, 1:N Beziehungen zu anderen Entities]

## Properties & Methoden
[Berechnete Eigenschaften, Helper-Methoden]

## Verwendung in Modulen
[PRD-Referenzen]

## Änderungshistorie
[Wichtige Schema-Änderungen]
```

## Konventionen

### Namensgebung
- **Models:** PascalCase (z.B. `LieferantBranche`)
- **Tabellen:** snake_case (z.B. `lieferant_branche`)
- **Junction-Tables:** `{entity1}_{entity2}` alphabetisch

### Beziehungen
- **M:N:** Immer über Junction-Table mit eigenem Primary Key
- **1:N:** Foreign Key in der "N"-Tabelle
- **Soft-Delete:** `aktiv` Boolean statt echtem Löschen (wo sinnvoll)

### Constraints
- **Unique:** Über `UniqueConstraint` mit sprechendem Namen
- **Foreign Keys:** Immer mit `ondelete` Strategie (`CASCADE` oder `SET NULL`)

## Datei-Index

```
docs/prd/core/entities/
├── README.md           # Diese Datei
├── lieferant.md        # Lieferant + LieferantBranche
├── kunde.md            # Kunde + KundeCI + Junction-Tables
├── branche.md          # Branche + BranchenRolle
└── produkt.md          # Produkt + Eigenschaft-System
```
