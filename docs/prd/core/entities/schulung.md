# Entity: Schulung (PRD-010)

## Beschreibung

Schulungsverwaltung für Online-Schulungen (Teams-Meetings). Besteht aus mehreren zusammenhängenden Entitäten für Kurs-Templates, wiederverwendbare Themen, konkrete Durchführungen und Buchungen.

**Dateien:**

- Models: `app/models/schulung.py`, `schulungsthema.py`, `schulungsdurchfuehrung.py`, `schulungsbuchung.py`
- Routes: `app/routes/schulungen.py`, `app/routes/schulungen_admin.py`
- Templates: `app/templates/schulungen/`, `app/templates/administration/schulungen/`
- Service: `app/services/schulung_service.py`

---

## Datenbankschema

### Tabelle: `schulung`

Kurs-Template mit Preis und Metadaten.

| Feld | Typ | Constraint | Beschreibung |
|------|-----|------------|--------------|
| `id` | Integer | PK | Auto-Increment |
| `titel` | String(200) | NOT NULL | Schulungstitel |
| `beschreibung` | Text | NULL | Ausführliche Beschreibung (Markdown) |
| `artikelnummer` | String(50) | NULL | ERP-Artikelnummer für Rechnung |
| `preis` | Numeric(10,2) | NOT NULL | Standardpreis in EUR |
| `sonderpreis` | Numeric(10,2) | NULL | Aktionspreis |
| `aktionszeitraum_von` | Date | NULL | Sonderpreis gültig ab |
| `aktionszeitraum_bis` | Date | NULL | Sonderpreis gültig bis |
| `max_teilnehmer` | Integer | NOT NULL, DEFAULT 10 | Maximale Teilnehmerzahl |
| `storno_frist_tage` | Integer | NOT NULL, DEFAULT 7 | Tage vor Start |
| `aktiv` | Boolean | NOT NULL, DEFAULT TRUE | Öffentlich sichtbar |
| `sortierung` | Integer | DEFAULT 0 | Reihenfolge |
| `created_at` | DateTime | DEFAULT NOW | Erstellung |
| `updated_at` | DateTime | ON UPDATE | Änderung |

### Tabelle: `schulungsthema`

Einzelne Themenblöcke (wiederverwendbar in mehreren Schulungen).

| Feld | Typ | Constraint | Beschreibung |
|------|-----|------------|--------------|
| `id` | Integer | PK | Auto-Increment |
| `titel` | String(200) | NOT NULL | Thementitel |
| `beschreibung` | Text | NULL | Beschreibung (Markdown) |
| `dauer_minuten` | Integer | NOT NULL, DEFAULT 45 | Dauer |
| `aktiv` | Boolean | NOT NULL, DEFAULT TRUE | Verwendbar |
| `created_at` | DateTime | DEFAULT NOW | Erstellung |

### Tabelle: `schulung_thema` (Junction)

M:N Verknüpfung zwischen Schulung und Thema.

| Feld | Typ | Constraint | Beschreibung |
|------|-----|------------|--------------|
| `id` | Integer | PK | Auto-Increment |
| `schulung_id` | Integer | FK, NOT NULL | → `schulung.id` |
| `thema_id` | Integer | FK, NOT NULL | → `schulungsthema.id` |
| `sortierung` | Integer | NOT NULL, DEFAULT 0 | Reihenfolge |

**Constraints:** `uq_schulung_thema`: UNIQUE(`schulung_id`, `thema_id`)

### Tabelle: `schulungsdurchfuehrung`

Konkrete Instanz einer Schulung mit Terminen.

| Feld | Typ | Constraint | Beschreibung |
|------|-----|------------|--------------|
| `id` | Integer | PK | Auto-Increment |
| `schulung_id` | Integer | FK, NOT NULL | → `schulung.id` |
| `start_datum` | Date | NOT NULL | Erster Schulungstag |
| `terminmuster` | JSON | NOT NULL | `{"wochentage": ["Di", "Do"], "uhrzeit": "14:00"}` |
| `teams_link` | String(500) | NULL | Microsoft Teams Link |
| `status` | String(20) | NOT NULL, DEFAULT 'geplant' | geplant/aktiv/abgeschlossen/abgesagt |
| `anmerkungen` | Text | NULL | Interne Notizen |
| `created_at` | DateTime | DEFAULT NOW | Erstellung |
| `updated_at` | DateTime | ON UPDATE | Änderung |

### Tabelle: `schulungstermin`

Konkrete Kalender-Termine (generiert).

| Feld | Typ | Constraint | Beschreibung |
|------|-----|------------|--------------|
| `id` | Integer | PK | Auto-Increment |
| `durchfuehrung_id` | Integer | FK, NOT NULL | → `schulungsdurchfuehrung.id` |
| `thema_id` | Integer | FK, NOT NULL | → `schulungsthema.id` |
| `termin_nummer` | Integer | NOT NULL | 1, 2, 3... |
| `datum` | Date | NOT NULL | Konkretes Datum |
| `uhrzeit_von` | Time | NOT NULL | Startzeit |
| `uhrzeit_bis` | Time | NOT NULL | Endzeit |

### Tabelle: `schulungsbuchung`

Buchung einer Durchführung durch einen Kunden.

| Feld | Typ | Constraint | Beschreibung |
|------|-----|------------|--------------|
| `id` | Integer | PK | Auto-Increment |
| `kunde_id` | Integer | FK, NOT NULL | → `kunde.id` |
| `durchfuehrung_id` | Integer | FK, NOT NULL | → `schulungsdurchfuehrung.id` |
| `status` | String(20) | NOT NULL, DEFAULT 'gebucht' | gebucht/warteliste/storniert |
| `preis_bei_buchung` | Numeric(10,2) | NOT NULL | Preis zum Buchungszeitpunkt |
| `gebucht_am` | DateTime | NOT NULL | Buchungszeitpunkt |
| `storniert_am` | DateTime | NULL | Stornierungszeitpunkt |
| `anmerkungen` | Text | NULL | Notizen |
| `created_at` | DateTime | DEFAULT NOW | Erstellung |

**Constraints:** `uq_kunde_durchfuehrung`: UNIQUE(`kunde_id`, `durchfuehrung_id`)

---

## Beziehungen

```
┌─────────────────┐                    ┌─────────────────┐
│    Schulung     │◄───── M:N ────────►│ Schulungsthema  │
└─────────────────┘   schulung_thema   └─────────────────┘
         │                                      │
         │ 1:N                                  │ (referenziert)
         ▼                                      │
┌─────────────────────────┐                     │
│ Schulungsdurchfuehrung  │                     │
└─────────────────────────┘                     │
         │                                      │
         ├── 1:N ──► Schulungstermin ◄──────────┘
         │
         └── 1:N ──► Schulungsbuchung ──► N:1 ──► Kunde
```

---

## Properties & Methoden

### Schulung

```python
@property
def aktueller_preis(self) -> Decimal:
    """Gibt Sonderpreis zurück wenn im Aktionszeitraum, sonst Standardpreis."""

@property
def themen_sortiert(self) -> List[Schulungsthema]:
    """Alle Themen sortiert nach Junction-Sortierung."""

@property
def naechste_durchfuehrung(self) -> Optional[Schulungsdurchfuehrung]:
    """Nächste geplante/aktive Durchführung."""

@property
def gesamtdauer_minuten(self) -> int:
    """Summe aller Themen-Dauern."""
```

### Schulungsdurchfuehrung

```python
@property
def freie_plaetze(self) -> int:
    """Max. Teilnehmer minus gebuchte Teilnehmer."""

@property
def ist_ausgebucht(self) -> bool:
    """True wenn keine freien Plätze."""

@property
def teilnehmer_gebucht(self) -> List[Schulungsbuchung]:
    """Alle verbindlichen Buchungen."""

@property
def teilnehmer_warteliste(self) -> List[Schulungsbuchung]:
    """Alle Wartelisten-Buchungen."""

def generiere_termine(self) -> List[Schulungstermin]:
    """Berechnet Termine aus Themen und Terminmuster."""
```

### Schulungsbuchung

```python
@property
def kann_storniert_werden(self) -> bool:
    """True wenn innerhalb der Storno-Frist."""

@property
def storno_frist_datum(self) -> date:
    """Letzter Tag für Stornierung."""
```

---

## Status-Workflows

### Durchführung-Status

```
┌──────────┐     ┌────────┐     ┌───────────────┐
│ geplant  │────►│ aktiv  │────►│ abgeschlossen │
└──────────┘     └────────┘     └───────────────┘
      │
      └──────────────────────────►┌──────────┐
                                  │ abgesagt │
                                  └──────────┘
```

### Buchung-Status

```
┌──────────┐                      ┌───────────┐
│ gebucht  │─────(Stornierung)───►│ storniert │
└──────────┘                      └───────────┘
      ▲
      │ (Freischaltung)
      │
┌──────────────┐
│  warteliste  │─────(Stornierung)───► storniert
└──────────────┘
```

---

## Verwendung in Modulen

| Modul | PRD | Verwendung |
|-------|-----|------------|
| Schulungen | PRD-010 | Hauptmodul |
| Kunden | PRD-002 | Buchungen sind an Kunde gebunden |

---

## Änderungshistorie

### 2025-12-29: Entity-Dokumentation erstellt

- Vollständiges Datenmodell dokumentiert
- Beziehungen und Properties definiert
- Status-Workflows beschrieben

### 2025-12-29: PRD-010 erstellt

- Initiale Anforderungsdokumentation
- 5 Entitäten: Schulung, Thema, Durchführung, Termin, Buchung
- iframe-Einbettungskonzept
