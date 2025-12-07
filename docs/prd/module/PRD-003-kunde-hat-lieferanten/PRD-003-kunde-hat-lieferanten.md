# Lieferanten-Auswahl

Kunden können festlegen, welche Lieferanten für sie relevant sind.

**Status:** Geplant

## Zielgruppe
- Kunden (primär)
- e-vendo Mitarbeiter (zur Unterstützung)

## Funktionen

### Geplant
- Kunde sieht Liste aller verfügbaren Lieferanten
- Checkbox/Toggle zur Auswahl relevanter Lieferanten
- Filterung nach Branche/Kategorie
- Speicherung der Auswahl pro Kunde

## Datenmodell

### Neue Tabelle: `kunde_lieferant` (n:m)
```
kunde_lieferant
├── kunde_id (FK → user.id oder neues kunde Model)
├── lieferant_id (FK → lieferant.id)
├── created_at
└── aktiv
```

### Offene Fragen
- Soll `Kunde` ein eigenes Model sein oder Erweiterung von `User`?
- Welche Zusatzfelder benötigt ein Kunde? (Firma, Kundennummer, etc.)

## UI/UX

### Mockup (grob)
```
┌─────────────────────────────────────────┐
│ Meine Lieferanten                       │
├─────────────────────────────────────────┤
│ [x] LEGO Spielwaren GmbH                │
│ [ ] Hasbro Deutschland                  │
│ [x] Ravensburger AG                     │
│ [ ] PLAYMOBIL                           │
│ ...                                     │
├─────────────────────────────────────────┤
│ [ Speichern ]                           │
└─────────────────────────────────────────┘
```

## Tasks

| # | Task | Status | Beschreibung |
|---|------|--------|--------------|
| L1 | Kunde-Model | ⏳ Offen | Entity für Kundendaten |
| L2 | n:m Beziehung | ⏳ Offen | kunde_lieferant Tabelle |
| L3 | Blueprint | ⏳ Offen | Routes für Lieferanten-Auswahl |
| L4 | UI | ⏳ Offen | Template mit Checkbox-Liste |
