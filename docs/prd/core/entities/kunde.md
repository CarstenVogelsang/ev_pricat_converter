# Entity: Kunde

## Beschreibung

Kunden und Leads der ev247-Plattform. Enthält Firmendaten, Corporate Identity (CI), Branchen-Zuordnungen und Benutzer-Verknüpfungen. Zentrale Entity für Lead&Kundenreport und Kunden-Dialog.

**Dateien:**
- Model: `app/models/kunde.py`
- Junction-Tables: `app/models/kunde_branche.py`, `app/models/kunde_verband.py`, `app/models/kunde_benutzer.py`
- Routes: `app/routes/kunden.py`
- Templates: `app/templates/kunden/`

---

## Datenbankschema

### Tabelle: `kunde`

| Feld | Typ | Constraint | Beschreibung |
|------|-----|------------|--------------|
| `id` | Integer | PK | Auto-Increment Primary Key |
| `firmierung` | String(200) | NOT NULL | Firmenname |
| `ev_kdnr` | String(50) | UNIQUE | e-vendo Kundennummer |
| `strasse` | String(200) | NULL | Straße und Hausnummer |
| `plz` | String(20) | NULL | Postleitzahl |
| `ort` | String(100) | NULL | Ort |
| `land` | String(100) | DEFAULT 'Deutschland' | Land |
| `adresse` | Text | NULL | Legacy-Adressfeld |
| `website_url` | String(500) | NULL | Website URL |
| `shop_url` | String(500) | NULL | Online-Shop URL |
| `telefon` | String(50) | NULL | Telefonnummer |
| `email` | String(200) | NULL | E-Mail-Adresse |
| `notizen` | Text | NULL | Interne Notizen |
| `aktiv` | Boolean | DEFAULT TRUE | Aktiv-Status |
| `email_footer` | Text | NULL | HTML-Footer für E-Mails |
| `ist_systemkunde` | Boolean | DEFAULT FALSE | System-Default für Footer |
| `anrede` | String(20) | DEFAULT 'firma' | herr/frau/divers/firma |
| `kommunikation_stil` | String(20) | DEFAULT 'foermlich' | foermlich/locker |
| `hauptbranche_id` | Integer | FK, NULL | Primäre Hauptbranche |
| `user_id` | Integer | FK, UNIQUE, NULL | **DEPRECATED** Legacy User |
| `created_at` | DateTime | DEFAULT NOW | Erstellungszeitpunkt |
| `updated_at` | DateTime | ON UPDATE | Letzter Änderungszeitpunkt |

### Tabelle: `kunde_ci` (1:1)

| Feld | Typ | Constraint | Beschreibung |
|------|-----|------------|--------------|
| `id` | Integer | PK | Auto-Increment Primary Key |
| `kunde_id` | Integer | FK, UNIQUE, NOT NULL | Referenz auf `kunde.id` |
| `logo_url` | String(500) | NULL | URL zum Logo |
| `primary_color` | String(20) | NULL | Hauptfarbe (#hex) |
| `secondary_color` | String(20) | NULL | Sekundärfarbe |
| `accent_color` | String(20) | NULL | Akzentfarbe |
| `background_color` | String(20) | NULL | Hintergrundfarbe |
| `text_primary_color` | String(20) | NULL | Primäre Textfarbe |
| `text_secondary_color` | String(20) | NULL | Sekundäre Textfarbe |
| `analysiert_am` | DateTime | NULL | Zeitpunkt der Analyse |
| `analyse_url` | String(500) | NULL | Analysierte URL |
| `raw_response` | Text | NULL | Rohe Firecrawl-Antwort |

### Junction-Tables

**`kunde_branche`:**
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `kunde_id` | Integer FK | Referenz auf `kunde.id` |
| `branche_id` | Integer FK | Referenz auf `branche.id` |
| `ist_primaer` | Boolean | Primärbranche-Markierung (max. 3) |

**`kunde_verband`:**
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `kunde_id` | Integer FK | Referenz auf `kunde.id` |
| `verband_id` | Integer FK | Referenz auf `verband.id` |

**`kunde_benutzer`:**
| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `kunde_id` | Integer FK | Referenz auf `kunde.id` |
| `user_id` | Integer FK | Referenz auf `user.id` |
| `ist_hauptbenutzer` | Boolean | Primärer Ansprechpartner |

---

## Beziehungen

```
┌─────────────┐       ┌─────────────────┐       ┌─────────────┐
│    Kunde    │ 1───N │   KundeBranche  │ N───1 │   Branche   │
└─────────────┘       └─────────────────┘       └─────────────┘
       │
       │ 1:1
       ▼
┌─────────────┐
│   KundeCI   │
└─────────────┘
       │
       │ N:M
       ▼
┌─────────────┐       ┌─────────────────┐       ┌─────────────┐
│    Kunde    │ N───M │  KundeBenutzer  │ M───N │    User     │
└─────────────┘       └─────────────────┘       └─────────────┘
```

---

## Properties & Methoden

### Branchen
- `hauptbranche`: Primäre Hauptbranche (direkte FK)
- `primaer_branchen`: Liste der Primärbranchen (max. 3)
- `alle_branchen`: Alle zugeordneten Branchen

### Benutzer
- `hauptbenutzer`: Primärer Ansprechpartner (User)
- `alle_benutzer`: Alle zugeordneten Benutzer
- `user`: **DEPRECATED** - Alias für `hauptbenutzer`

### Adresse
- `adresse_formatiert`: Formatierte Adresse aus strukturierten Feldern

### Kommunikation
- `effektiver_kommunikation_stil`: Stil mit User-Override
- `briefanrede`: Automatische Anrede basierend auf Stil
- `briefanrede_foermlich`: Formelle Anrede (Sie)
- `briefanrede_locker`: Informelle Anrede (Du)

---

## Verwendung in Modulen

| Modul | PRD | Verwendung |
|-------|-----|------------|
| Lead & Kundenreport | PRD-002 | Kunden- und Lead-Verwaltung |
| Kunden-Dialog | PRD-006 | Fragebogen-Teilnahme |
| Anwender-Support | PRD-007 | Support-Tickets |
| Kunde-Lieferanten | PRD-003 | Lieferanten-Zuordnung (geplant) |

---

## Änderungshistorie

### 2025-12-28: Benutzer 1:N Refactoring
- Neue Junction-Table `kunde_benutzer` für 1:N User-Zuordnung
- Property `hauptbenutzer` statt direkter FK
- Legacy `user_id` deprecated (Migration-Fallback)

### 2025-12-20: E-Mail-Templates
- Felder `anrede`, `kommunikation_stil` hinzugefügt
- Briefanrede-Properties für automatische Anrede

### 2025-12-06: Initiale Erstellung
- Basis-Felder: Firmendaten, Adresse, Kontakt
- KundeCI für Firecrawl-Branding
- M:N zu Branchen und Verbänden
