# PRD-010: Schulungen

**Modul-Code:** `schulungen`
**Status:** In Entwicklung
**Erstellt:** 2025-12-29
**Typ:** KUNDENPROJEKT

---

## 1. Übersicht

Online-Schulungsverwaltung für Teams-basierte Schulungen. Das Modul bietet:

- **Öffentliches Frontend** (iframe-einbettbar auf e-vendo.de)
- **Kunden-Portal** für Buchung und Verwaltung eigener Schulungen
- **Admin-Backend** für Schulungsverwaltung, Teilnehmer und Warteliste
- **Excel-Export** für ERP-Import (Rechnungsstellung)

### Zielgruppen

| Rolle | Nutzung |
|-------|---------|
| **Besucher (nicht eingeloggt)** | Schulungsübersicht ansehen, Preise sehen |
| **Kunde** | Schulungen buchen, stornieren, eigene Buchungen verwalten |
| **Mitarbeiter** | Schulungen verwalten, Buchungen einsehen |
| **Admin** | Vollzugriff, Warteliste freischalten, Export |

### Kernfunktionen (MVP)

1. Schulungen mit wiederverwendbaren Themen verwalten
2. Schulungsdurchführungen mit automatischer Terminberechnung
3. Öffentliche Ansicht (mit iframe-Variante für e-vendo.de)
4. Buchung durch eingeloggte Kunden
5. Warteliste bei Überbuchung (manuelles Freischalten)
6. Selbst-Stornierung durch Kunden
7. Excel-Export für ERP-Integration
8. E-Mail-Benachrichtigungen

---

## 2. Datenmodelle

### Entity-Beziehungen

```
┌─────────────────┐
│    Schulung     │ (Kurs-Template)
└─────────────────┘
         │
         │ M:N (schulung_thema)
         ▼
┌─────────────────┐
│ Schulungsthema  │ (wiederverwendbar)
└─────────────────┘
         │
         │ (referenziert in Terminen)
         ▼
┌─────────────────────────┐
│ Schulungsdurchfuehrung  │ (konkrete Instanz)
└─────────────────────────┘
         │
         ├── 1:N → Schulungstermin (generierte Termine)
         │
         └── 1:N → Schulungsbuchung (Teilnehmer)
                        │
                        └── N:1 → Kunde
```

### Tabelle: `schulung`

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
| `storno_frist_tage` | Integer | NOT NULL, DEFAULT 7 | Tage vor Start, bis Storno möglich |
| `aktiv` | Boolean | NOT NULL, DEFAULT TRUE | Öffentlich sichtbar |
| `sortierung` | Integer | DEFAULT 0 | Reihenfolge in Liste |
| `created_at` | DateTime | DEFAULT NOW | Erstellungszeitpunkt |
| `updated_at` | DateTime | ON UPDATE | Letzter Änderungszeitpunkt |

### Tabelle: `schulungsthema`

| Feld | Typ | Constraint | Beschreibung |
|------|-----|------------|--------------|
| `id` | Integer | PK | Auto-Increment |
| `titel` | String(200) | NOT NULL | Thementitel |
| `beschreibung` | Text | NULL | Themen-Beschreibung (Markdown) |
| `dauer_minuten` | Integer | NOT NULL, DEFAULT 45 | Dauer in Minuten |
| `aktiv` | Boolean | NOT NULL, DEFAULT TRUE | Verwendbar |
| `created_at` | DateTime | DEFAULT NOW | Erstellungszeitpunkt |

### Tabelle: `schulung_thema` (Junction M:N)

| Feld | Typ | Constraint | Beschreibung |
|------|-----|------------|--------------|
| `id` | Integer | PK | Auto-Increment |
| `schulung_id` | Integer | FK, NOT NULL | Referenz auf `schulung.id` |
| `thema_id` | Integer | FK, NOT NULL | Referenz auf `schulungsthema.id` |
| `sortierung` | Integer | NOT NULL, DEFAULT 0 | Reihenfolge in Schulung |

**Constraints:**

- `uq_schulung_thema`: UNIQUE(`schulung_id`, `thema_id`)
- FK `schulung_id` → `schulung.id` ON DELETE CASCADE
- FK `thema_id` → `schulungsthema.id` ON DELETE RESTRICT

### Tabelle: `schulungsdurchfuehrung`

| Feld | Typ | Constraint | Beschreibung |
|------|-----|------------|--------------|
| `id` | Integer | PK | Auto-Increment |
| `schulung_id` | Integer | FK, NOT NULL | Referenz auf `schulung.id` |
| `start_datum` | Date | NOT NULL | Erster Schulungstag |
| `terminmuster` | JSON | NOT NULL | `{"wochentage": ["Di", "Do"], "uhrzeit": "14:00"}` |
| `teams_link` | String(500) | NULL | Microsoft Teams Meeting-Link |
| `status` | String(20) | NOT NULL, DEFAULT 'geplant' | geplant/aktiv/abgeschlossen/abgesagt |
| `anmerkungen` | Text | NULL | Interne Notizen |
| `created_at` | DateTime | DEFAULT NOW | Erstellungszeitpunkt |
| `updated_at` | DateTime | ON UPDATE | Letzter Änderungszeitpunkt |

**Status-Workflow:**

```
┌──────────┐     ┌────────┐     ┌───────────────┐
│ Geplant  │────►│ Aktiv  │────►│ Abgeschlossen │
└──────────┘     └────────┘     └───────────────┘
      │
      └──────────────────────────►┌──────────┐
                                  │ Abgesagt │
                                  └──────────┘
```

### Tabelle: `schulungstermin`

| Feld | Typ | Constraint | Beschreibung |
|------|-----|------------|--------------|
| `id` | Integer | PK | Auto-Increment |
| `durchfuehrung_id` | Integer | FK, NOT NULL | Referenz auf `schulungsdurchfuehrung.id` |
| `thema_id` | Integer | FK, NOT NULL | Referenz auf `schulungsthema.id` |
| `termin_nummer` | Integer | NOT NULL | 1, 2, 3... (Reihenfolge) |
| `datum` | Date | NOT NULL | Konkretes Datum |
| `uhrzeit_von` | Time | NOT NULL | Startzeit |
| `uhrzeit_bis` | Time | NOT NULL | Endzeit |

**Constraints:**

- FK `durchfuehrung_id` → `schulungsdurchfuehrung.id` ON DELETE CASCADE
- FK `thema_id` → `schulungsthema.id` ON DELETE RESTRICT

### Tabelle: `schulungsbuchung`

| Feld | Typ | Constraint | Beschreibung |
|------|-----|------------|--------------|
| `id` | Integer | PK | Auto-Increment |
| `kunde_id` | Integer | FK, NOT NULL | Referenz auf `kunde.id` |
| `durchfuehrung_id` | Integer | FK, NOT NULL | Referenz auf `schulungsdurchfuehrung.id` |
| `status` | String(20) | NOT NULL, DEFAULT 'gebucht' | gebucht/warteliste/storniert |
| `preis_bei_buchung` | Numeric(10,2) | NOT NULL | Preis zum Buchungszeitpunkt |
| `gebucht_am` | DateTime | NOT NULL, DEFAULT NOW | Buchungszeitpunkt |
| `storniert_am` | DateTime | NULL | Stornierungszeitpunkt |
| `anmerkungen` | Text | NULL | Notizen zur Buchung |
| `created_at` | DateTime | DEFAULT NOW | Erstellungszeitpunkt |

**Constraints:**

- `uq_kunde_durchfuehrung`: UNIQUE(`kunde_id`, `durchfuehrung_id`) - Ein Kunde pro Durchführung
- FK `kunde_id` → `kunde.id` ON DELETE CASCADE
- FK `durchfuehrung_id` → `schulungsdurchfuehrung.id` ON DELETE CASCADE

**Buchungs-Status:**

| Status | Bedeutung |
|--------|-----------|
| `gebucht` | Verbindlich gebucht, Platz reserviert |
| `warteliste` | Max. Teilnehmer erreicht, wartet auf Freigabe |
| `storniert` | Buchung storniert (durch Kunde oder Admin) |

---

## 3. User Interface

### 3.1 Öffentliches Frontend

**Ohne Login zugänglich - auch als iframe einbettbar**

#### Schulungsliste (`/schulungen/`)

- Kachel-/Listen-Ansicht aller aktiven Schulungen
- Filter: Kategorie (V2), Preis, Verfügbarkeit
- Anzeige: Titel, Beschreibung, Preis, nächster Start
- "Jetzt buchen" Button → öffnet Buchungsseite

#### Schulungsdetail (`/schulungen/<id>`)

- Vollständige Beschreibung
- Themen-Liste mit Dauer
- Nächste Durchführungen mit freien Plätzen
- Preis (inkl. Sonderpreis wenn aktiv)
- "Jetzt buchen" Button

### 3.2 iframe-Einbettung

**Besonderheit: Ohne Header/Footer für Integration in e-vendo.de**

#### Embed-Liste (`/schulungen/embed`)

- Identisch zur normalen Liste
- Kein Header, Footer, Navigation
- Transparenter Hintergrund
- "Jetzt buchen" öffnet neues Fenster (ev247.de)

#### Embed-Detail (`/schulungen/embed/<id>`)

- Identisch zum normalen Detail
- "Jetzt buchen" öffnet neues Fenster mit Login

**URL-Parameter:**

| Parameter | Beschreibung |
|-----------|--------------|
| `theme` | `light` oder `dark` (optional) |
| `ref` | Tracking-Quelle (z.B. `evendo`) |

### 3.3 Kunden-Portal (Login erforderlich)

#### Meine Schulungen (`/schulungen/meine`)

- Liste eigener Buchungen (gebucht, warteliste, storniert)
- Status-Badge pro Buchung
- "Stornieren" Button (wenn innerhalb Frist)
- Teams-Link (nur bei gebuchten, aktiven Schulungen)

#### Buchungsseite (`/schulungen/buchen/<durchfuehrung_id>`)

- Schulungs-Details
- Aktueller Preis (Normal/Sonder)
- Freie Plätze / Warteliste-Hinweis
- Checkbox "Ich akzeptiere die AGB"
- "Verbindlich buchen" Button

#### Stornierungsseite (`/schulungen/stornieren/<buchung_id>`)

- Buchungs-Details
- Hinweis auf Stornierungsfrist
- Bestätigung erforderlich
- E-Mail-Benachrichtigung nach Stornierung

### 3.4 Admin-Backend

#### Schulungen-Übersicht (`/admin/schulungen/`)

- Tabelle aller Schulungen (aktiv/inaktiv)
- Spalten: Titel, Preis, Themen-Anzahl, Durchführungen, Aktiv
- Aktionen: Bearbeiten, Neue Durchführung

#### Schulung bearbeiten (`/admin/schulungen/form/<id>`)

- Stammdaten (Titel, Beschreibung, Preis, etc.)
- Themen-Zuordnung (Drag & Drop Sortierung)
- Artikelnummer für ERP
- Aktiv-Status

#### Themen-Verwaltung (`/admin/schulungen/themen`)

- CRUD für Schulungsthemen
- Verwendung in Schulungen anzeigen

#### Durchführungen (`/admin/schulungen/durchfuehrungen`)

- Alle Durchführungen mit Status
- Filter: Schulung, Status, Zeitraum
- Teilnehmerzahl / Max anzeigen

#### Durchführung-Detail (`/admin/schulungen/durchfuehrung/<id>`)

- Teilnehmer-Liste (gebucht + warteliste)
- Generierte Termine
- Teams-Link bearbeiten
- Warteliste → Gebucht freischalten
- Status ändern

#### Buchungen (`/admin/schulungen/buchungen`)

- Alle Buchungen mit Filter
- Filter: Schulung, Status, Zeitraum
- Export-Button

#### Excel-Export (`/admin/schulungen/export`)

- Filter: Zeitraum, Schulung, Status
- Download als .xlsx

---

## 4. Routes

### Öffentlich (ohne Login)

| Route | Methode | Beschreibung |
|-------|---------|--------------|
| `/schulungen/` | GET | Schulungsliste |
| `/schulungen/<int:id>` | GET | Schulungsdetail |
| `/schulungen/embed` | GET | iframe-Liste |
| `/schulungen/embed/<int:id>` | GET | iframe-Detail |

### Kunden-Portal (Login erforderlich, Rolle: kunde)

| Route | Methode | Beschreibung |
|-------|---------|--------------|
| `/schulungen/meine` | GET | Meine Buchungen |
| `/schulungen/buchen/<int:durchfuehrung_id>` | GET | Buchungsformular |
| `/schulungen/buchen/<int:durchfuehrung_id>` | POST | Buchung abschicken |
| `/schulungen/stornieren/<int:buchung_id>` | GET | Stornierungsformular |
| `/schulungen/stornieren/<int:buchung_id>` | POST | Stornierung durchführen |

### Admin-Bereich (Rolle: admin, mitarbeiter)

| Route | Methode | Beschreibung |
|-------|---------|--------------|
| `/admin/schulungen/` | GET | Schulungen-Übersicht |
| `/admin/schulungen/form` | GET/POST | Neue Schulung |
| `/admin/schulungen/form/<int:id>` | GET/POST | Schulung bearbeiten |
| `/admin/schulungen/<int:id>/delete` | POST | Schulung löschen |
| `/admin/schulungen/themen` | GET | Themen-Liste |
| `/admin/schulungen/themen/form` | GET/POST | Neues Thema |
| `/admin/schulungen/themen/form/<int:id>` | GET/POST | Thema bearbeiten |
| `/admin/schulungen/durchfuehrungen` | GET | Durchführungen-Liste |
| `/admin/schulungen/durchfuehrung/form/<int:schulung_id>` | GET/POST | Neue Durchführung |
| `/admin/schulungen/durchfuehrung/<int:id>` | GET | Durchführung-Detail |
| `/admin/schulungen/durchfuehrung/<int:id>/termine-generieren` | POST | Termine neu berechnen |
| `/admin/schulungen/buchung/<int:id>/freischalten` | POST | Warteliste freischalten |
| `/admin/schulungen/buchung/<int:id>/stornieren` | POST | Admin-Stornierung |
| `/admin/schulungen/buchungen` | GET | Alle Buchungen |
| `/admin/schulungen/export` | GET | Excel-Export |

---

## 5. Services

### `schulung_service.py`

```python
class SchulungService:
    """Geschäftslogik für Schulungsverwaltung."""

    @staticmethod
    def get_aktueller_preis(schulung: Schulung) -> Decimal:
        """Gibt den aktuellen Preis (Normal oder Sonder) zurück."""

    @staticmethod
    def berechne_termine(durchfuehrung: Schulungsdurchfuehrung) -> List[Schulungstermin]:
        """Generiert Termine aus Schulungsthemen und Terminmuster."""

    @staticmethod
    def buchen(kunde: Kunde, durchfuehrung: Schulungsdurchfuehrung) -> Schulungsbuchung:
        """Bucht eine Schulung (oder setzt auf Warteliste)."""

    @staticmethod
    def stornieren(buchung: Schulungsbuchung, durch_admin: bool = False) -> bool:
        """Storniert eine Buchung (prüft Storno-Frist)."""

    @staticmethod
    def freischalten(buchung: Schulungsbuchung) -> bool:
        """Schaltet Wartelisten-Buchung frei."""

    @staticmethod
    def export_buchungen(filter_params: dict) -> bytes:
        """Generiert Excel-Export für ERP-Import."""
```

---

## 6. Abhängigkeiten

### Bestehende Module

| Modul | Verwendung |
|-------|------------|
| **Kunde** (PRD-002) | Buchung ist an Kunde gebunden |
| **E-Mail-Templates** | Buchungsbestätigung, Erinnerung, etc. |
| **Hilfetexte** (PRD-005) | Help-Icons in Admin-UI |
| **Audit-Log** | Logging von Buchungen, Stornierungen |

### Neue E-Mail-Templates

| Schlüssel | Anlass |
|-----------|--------|
| `schulung_buchung_bestaetigung` | Nach erfolgreicher Buchung |
| `schulung_warteliste` | Wenn auf Warteliste gesetzt |
| `schulung_warteliste_freigabe` | Wenn von Warteliste nachgerückt |
| `schulung_erinnerung` | X Tage vor Schulungsstart |
| `schulung_storniert_kunde` | Wenn Kunde selbst storniert |
| `schulung_storniert_admin` | Wenn Admin storniert |
| `schulung_teams_link` | Teams-Link für Teilnahme |

### Platzhalter für E-Mail-Templates

```jinja2
{{ schulung_titel }}          # Schulungstitel
{{ schulung_preis }}          # Preis bei Buchung
{{ durchfuehrung_start }}     # Start-Datum
{{ durchfuehrung_termine }}   # Liste aller Termine
{{ teams_link }}              # Microsoft Teams Link
{{ storno_frist }}            # Letztmöglicher Storno-Tag
{{ buchungs_status }}         # gebucht/warteliste
```

---

## 7. Berechtigungen

### Modul-Zugriff

| Rolle | Zugriff |
|-------|---------|
| **Besucher** | Öffentliche Seiten (Liste, Detail, Embed) |
| **Kunde** | + Meine Buchungen, Buchen, Stornieren |
| **Mitarbeiter** | + Admin-Übersichten (read-only) |
| **Admin** | Vollzugriff |

### Objekt-Level

| Objekt | Sichtbarkeit |
|--------|--------------|
| **Schulung** | Öffentlich wenn `aktiv=True` |
| **Durchführung** | Öffentlich wenn `status != 'abgesagt'` |
| **Buchung** | Nur eigene (Kunde) oder alle (Admin/Mitarbeiter) |

---

## 8. Audit-Logging

| Entity | Aktion | Beschreibung |
|--------|--------|--------------|
| `schulungsbuchung` | `erstellt` | Neue Buchung |
| `schulungsbuchung` | `storniert` | Stornierung (durch Kunde) |
| `schulungsbuchung` | `admin_storniert` | Stornierung (durch Admin) |
| `schulungsbuchung` | `freigeschaltet` | Von Warteliste nachgerückt |
| `schulungsdurchfuehrung` | `erstellt` | Neue Durchführung |
| `schulungsdurchfuehrung` | `status_geaendert` | Status-Änderung |

---

## 9. Technische Details

### iframe-Einbettung

**Problem:** Cookie-Probleme bei Cross-Domain iframes

**Lösung:**

- iframe zeigt nur Ansicht (keine Auth erforderlich)
- "Jetzt buchen" öffnet neues Fenster auf ev247.de
- Session/Login findet im Hauptfenster statt

**Template-Struktur:**

```
schulungen/
├── embed_base.html       # Eigenständiges HTML (kein extends base.html)
├── embed_liste.html      # {% extends "schulungen/embed_base.html" %}
├── embed_detail.html     # {% extends "schulungen/embed_base.html" %}
├── liste.html            # {% extends "base.html" %}
├── detail.html           # {% extends "base.html" %}
├── meine.html            # {% extends "base.html" %}
└── buchen.html           # {% extends "base.html" %}
```

### Terminberechnung

```python
def berechne_termine(durchfuehrung):
    """
    Berechnet konkrete Termine aus:
    - durchfuehrung.start_datum
    - durchfuehrung.terminmuster (JSON)
    - schulung.themen (sortiert)

    Beispiel-Muster:
    {
        "wochentage": ["Di", "Do"],
        "uhrzeit": "14:00"
    }

    Algorithmus:
    1. Startdatum finden (erster passender Wochentag)
    2. Für jedes Thema: nächsten passenden Wochentag wählen
    3. Uhrzeit aus Muster, Endzeit = Start + thema.dauer_minuten
    """
```

### Excel-Export Format

| Spalte | Beschreibung |
|--------|--------------|
| Kundennummer | `kunde.ev_kdnr` |
| Firmenname | `kunde.firmierung` |
| Schulung | `schulung.titel` |
| Artikelnummer | `schulung.artikelnummer` |
| Preis | `buchung.preis_bei_buchung` |
| Buchungsdatum | `buchung.gebucht_am` |
| Start | `durchfuehrung.start_datum` |
| Status | `buchung.status` |

---

## 10. Roadmap

### V1 (MVP)

- [x] Anforderungen klären
- [ ] Datenmodell implementieren
- [ ] Admin: Schulungen + Themen CRUD
- [ ] Admin: Durchführungen + Terminberechnung
- [ ] Admin: Buchungen-Übersicht + Freischalten
- [ ] Admin: Excel-Export
- [ ] Öffentlich: Liste + Detail
- [ ] Öffentlich: Embed-Variante
- [ ] Kunden: Buchen + Meine Schulungen
- [ ] Kunden: Stornierung
- [ ] E-Mail: Buchungsbestätigung

### V2

- [ ] E-Mail: Erinnerung vor Schulungsstart (Cron-Job)
- [ ] E-Mail: Teams-Link automatisch senden
- [ ] Kategorien/Tags für Schulungen
- [ ] Kalenderansicht für Durchführungen
- [ ] Teilnehmerliste als PDF
- [ ] Warteliste automatisch nachrücken (optional)

### V3+

- [ ] Teilnehmer-Feedback nach Schulung
- [ ] Zertifikate generieren
- [ ] Online-Zahlung Integration
- [ ] Dozenten-Verwaltung
- [ ] Wiederkehrende Schulungen (Auto-Anlage)

---

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)
