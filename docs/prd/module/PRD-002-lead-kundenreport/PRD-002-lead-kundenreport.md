# Lead & Kundenreport

Verwaltung von Kunden/Leads mit automatischer Website-Analyse zur Extraktion von Corporate Identity (CI) Informationen.

## Funktionen

- **Kundenverwaltung:** CRUD-Operationen fuer Kunden/Leads
- **Website-Analyse:** Automatische CI-Extraktion via Firecrawl API
- **Corporate Identity:** Logo, Farben (Primary, Secondary, Accent, Background, Text)

## Zugriffsrechte

| Rolle | Zugriff |
|-------|---------|
| Admin | Vollzugriff |
| Mitarbeiter | Vollzugriff |
| Kunde | Kein Zugriff |

## Datenmodell

### Tabelle: `kunde`

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | Integer | Primary Key |
| firmierung | String(200) | Firmenname (Pflicht) |
| adresse | Text | Anschrift |
| website_url | String(500) | Website fuer CI-Analyse |
| shop_url | String(500) | Online-Shop URL |
| notizen | Text | Interne Notizen |
| aktiv | Boolean | Status (Default: true) |
| created_at | DateTime | Erstellungsdatum |
| updated_at | DateTime | Aktualisierungsdatum |

### Tabelle: `kunde_ci`

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| id | Integer | Primary Key |
| kunde_id | Integer | FK zu kunde (1:1) |
| logo_url | String(500) | URL zum Logo |
| primary_color | String(20) | Hauptfarbe (Hex) |
| secondary_color | String(20) | Sekundaerfarbe (Hex) |
| accent_color | String(20) | Akzentfarbe (Hex) |
| background_color | String(20) | Hintergrundfarbe (Hex) |
| text_primary_color | String(20) | Textfarbe primaer (Hex) |
| text_secondary_color | String(20) | Textfarbe sekundaer (Hex) |
| analysiert_am | DateTime | Zeitpunkt der Analyse |
| analyse_url | String(500) | Analysierte URL |
| raw_response | Text | Rohe API-Antwort (JSON) |

## Routes

| Route | Methode | Beschreibung |
|-------|---------|--------------|
| `/kunden/` | GET | Kundenliste mit Filter |
| `/kunden/neu` | GET/POST | Neuen Kunden anlegen |
| `/kunden/<id>` | GET | Kundendetails + CI |
| `/kunden/<id>/bearbeiten` | GET/POST | Kunden bearbeiten |
| `/kunden/<id>/loeschen` | POST | Kunden loeschen |
| `/kunden/<id>/analyse` | POST | Website-Analyse starten |
| `/kunden/<id>/projekt` | GET | Projektverwaltung (nur intern) |

## Firecrawl-Integration

### Konfiguration

| Config-Key | Beschreibung |
|------------|--------------|
| `firecrawl_api_key` | API-Key fuer Firecrawl |
| `firecrawl_credit_kosten` | Kosten pro Credit in Euro (Default: 0.005) |

### API-Kostentracking

Bei jedem erfolgreichen Firecrawl-Call wird ein `KundeApiNutzung`-Eintrag erstellt:
- **user_id:** User der den Call ausgelöst hat
- **kunde_id:** Kunde für den die Analyse durchgeführt wurde
- **credits_used:** 1 Credit pro Scrape
- **kosten_euro:** Berechnet aus `firecrawl_credit_kosten` × Credits

### API-Aufruf

```python
POST https://api.firecrawl.dev/v1/scrape
Headers: Authorization: Bearer {api_key}
Body: {
    "url": "https://kunde-website.de",
    "formats": ["extract"],
    "extract": {
        "schema": {
            "type": "object",
            "properties": {
                "logo_url": {"type": "string"},
                "colors": {
                    "type": "object",
                    "properties": {
                        "primary": {"type": "string"},
                        "secondary": {"type": "string"},
                        ...
                    }
                }
            }
        }
    }
}
```

### Extrahierte Daten

- **Logo:** URL zum Firmenlogo
- **Farben:**
  - Primary Color (Hauptfarbe)
  - Secondary Color (Sekundaerfarbe)
  - Accent Color (Akzentfarbe)
  - Background Color (Hintergrundfarbe)
  - Text Primary Color (Haupttextfarbe)
  - Text Secondary Color (Sekundaertextfarbe)

## UI-Komponenten

### Kundenliste (`/kunden/`)

- Tabelle mit Firmierung, Website, Status
- Filter: Aktiv/Inaktiv/Alle
- Buttons: Neu, Details, Bearbeiten

### Kundendetail (`/kunden/<id>`)

- Stammdaten-Karte (Firmierung, Adresse, URLs)
- CI-Karte mit Logo und Farbpalette
- **Raw JSON Button:** Code-Icon im CI-Header öffnet Modal mit formatiertem Firecrawl-Response
- Notizen-Bereich
- Buttons: Projekt (nur intern), Website-Analyse, Bearbeiten, Loeschen

### Projektverwaltung (`/kunden/<id>/projekt`)

Nur fuer Admin und Mitarbeiter sichtbar.

- **Taetigkeiten-Bereich:** Platzhalter fuer zukuenftige Erfassung von Mitarbeiter-Taetigkeiten
- **API-Kosten-Bereich:**
  - Summary-Cards: Credits, Kosten, beteiligte Mitarbeiter
  - Tabelle: Nutzung pro Mitarbeiter
  - Tabelle: Alle API-Calls chronologisch

### Kundenformular (`/kunden/neu`, `/kunden/<id>/bearbeiten`)

- WTForms mit Validierung
- Felder: Firmierung*, Adresse, Website-URL, Shop-URL, Notizen, Aktiv
- CSRF-Schutz

## Technische Details

### Service: `FirecrawlService`

```python
class FirecrawlService:
    API_BASE_URL = 'https://api.firecrawl.dev/v1'

    def analyze_branding(self, kunde: Kunde) -> FirecrawlResult:
        # 1. API-Request an Firecrawl
        # 2. Response parsen
        # 3. KundeCI erstellen/aktualisieren
        # 4. Result zurueckgeben
```

### Blueprint: `kunden_bp`

- Prefix: `/kunden`
- Decorator: `@login_required` + `@mitarbeiter_required`

## Letztes Update

2025-12-07
