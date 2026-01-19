# PRD-013: Kunden-Mailing

## Übersicht

| Attribut | Wert |
|----------|------|
| **Modul-ID** | PRD-013 |
| **Name** | Kunden-Mailing |
| **Status** | In Entwicklung |
| **Version** | 1.4.0 |
| **Erstellt** | 2026-01-13 |

## Zusammenfassung

Das Kunden-Mailing-Modul ermöglicht das Versenden von Marketing-E-Mails an Kunden und Leads. Es bietet ein Baukasten-System für E-Mail-Inhalte mit vorgefertigten Sektionen und optionaler Integration mit dem Kunden-Dialog-Modul (PRD-006) für Fragebogen-Links.

### Kernfunktionen

- **Baukasten-System** für E-Mail-Sektionen (Header, Text/Bild, Fragebogen-CTA, Footer)
- **Zielgruppen** speicherbar für Wiederverwendung
- **Fragebogen-Integration** - Link zu bestehenden aktiven Fragebögen aus PRD-006
- **Personalisierung** mit Jinja2-Platzhaltern ({{ briefanrede }}, {{ firmenname }})
- **Klick-Tracking** für Fragebogen-Links
- **Abmelde-Link** (DSGVO-konform)
- **Manuelles Batching** bei >300 Empfängern (Brevo-Tageslimit)

---

## Datenmodell

### Neue Models

#### Mailing

```python
class MailingStatus(Enum):
    ENTWURF = 'entwurf'
    VERSENDET = 'versendet'

class Mailing(db.Model):
    __tablename__ = 'mailing'

    id = db.Column(db.Integer, primary_key=True)
    titel = db.Column(db.String(200), nullable=False)
    betreff = db.Column(db.String(200), nullable=False)
    status = db.Column(db.Enum(MailingStatus), default=MailingStatus.ENTWURF)
    sektionen_json = db.Column(db.JSON)  # Baukasten-Sektionen
    fragebogen_id = db.Column(db.Integer, db.ForeignKey('fragebogen.id'), nullable=True)

    erstellt_von_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    gesendet_am = db.Column(db.DateTime, nullable=True)

    # Cached stats
    anzahl_empfaenger = db.Column(db.Integer, default=0)
    anzahl_versendet = db.Column(db.Integer, default=0)
    anzahl_fehlgeschlagen = db.Column(db.Integer, default=0)
```

#### MailingEmpfaenger

```python
class EmpfaengerStatus(Enum):
    AUSSTEHEND = 'ausstehend'
    VERSENDET = 'versendet'
    FEHLGESCHLAGEN = 'fehlgeschlagen'

class MailingEmpfaenger(db.Model):
    __tablename__ = 'mailing_empfaenger'

    id = db.Column(db.Integer, primary_key=True)
    mailing_id = db.Column(db.Integer, db.ForeignKey('mailing.id'), nullable=False)
    kunde_id = db.Column(db.Integer, db.ForeignKey('kunde.id'), nullable=False)

    status = db.Column(db.Enum(EmpfaengerStatus), default=EmpfaengerStatus.AUSSTEHEND)
    versendet_am = db.Column(db.DateTime, nullable=True)
    fehler_meldung = db.Column(db.Text, nullable=True)

    # Tracking-Token für Klick-Tracking
    tracking_token = db.Column(db.String(100), unique=True, nullable=True)

    # FK zur FragebogenTeilnahme (wird bei Versand erstellt)
    fragebogen_teilnahme_id = db.Column(db.Integer, db.ForeignKey('fragebogen_teilnahme.id'), nullable=True)
```

#### MailingKlick

```python
class MailingKlick(db.Model):
    __tablename__ = 'mailing_klick'

    id = db.Column(db.Integer, primary_key=True)
    empfaenger_id = db.Column(db.Integer, db.ForeignKey('mailing_empfaenger.id'), nullable=False)
    link_typ = db.Column(db.String(50))  # 'fragebogen', 'abmelden', 'custom'
    geklickt_am = db.Column(db.DateTime, default=datetime.utcnow)
```

#### MailingZielgruppe

```python
class MailingZielgruppe(db.Model):
    __tablename__ = 'mailing_zielgruppe'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    beschreibung = db.Column(db.Text, nullable=True)
    filter_json = db.Column(db.JSON)  # Gespeicherte Filter-Kriterien
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
```

### Erweiterung Kunde-Model

```python
# In app/models/kunde.py - neue Felder
mailing_abgemeldet = db.Column(db.Boolean, default=False)
mailing_abgemeldet_am = db.Column(db.DateTime, nullable=True)
```

### Sektionen-JSON Schema

```json
{
  "sektionen": [
    {
      "id": "s1",
      "typ": "header",
      "config": {
        "zeige_logo": true
      }
    },
    {
      "id": "s2",
      "typ": "text_bild",
      "config": {
        "inhalt_html": "<p>Sehr geehrte/r {{ briefanrede }},</p>",
        "bild_url": null,
        "bild_position": "rechts"
      }
    },
    {
      "id": "s3",
      "typ": "fragebogen_cta",
      "config": {
        "button_text": "Jetzt teilnehmen",
        "button_farbe": "#007bff"
      }
    },
    {
      "id": "s4",
      "typ": "footer",
      "config": {
        "zeige_abmelde_link": true,
        "zusatz_text": null
      }
    }
  ]
}
```

---

## Services

### MailingService

Neuer Service in `app/services/mailing_service.py`:

**CRUD-Operationen:**
- `create_mailing(titel, betreff, erstellt_von)` → Mailing
- `update_mailing(mailing, **kwargs)` → Mailing
- `delete_mailing(mailing)` → bool

**Sektionen:**
- `add_sektion(mailing, typ, config)` → Sektion-ID
- `update_sektion(mailing, sektion_id, config)` → bool
- `remove_sektion(mailing, sektion_id)` → bool
- `reorder_sektionen(mailing, sektion_ids)` → bool

**Empfänger:**
- `add_empfaenger(mailing, kunde)` → MailingEmpfaenger
- `add_empfaenger_bulk(mailing, kunde_ids)` → int (Anzahl hinzugefügt)
- `get_verfuegbare_empfaenger(mailing)` → Query (filtert abgemeldete Kunden)
- `remove_empfaenger(mailing, kunde_id)` → bool

**Rendering:**
- `render_mailing_html(mailing, kunde)` → str (komplette E-Mail)
- `render_sektion(sektion, context)` → str (einzelne Sektion)
- `get_personalisierung_context(kunde)` → dict

**Fragebogen-Integration:**
- `ensure_fragebogen_teilnahme(mailing, empfaenger)` → FragebogenTeilnahme

**Versand:**
- `send_mailing(mailing, batch_size=None)` → dict (Statistik)
- `send_to_empfaenger(mailing, empfaenger)` → bool
- `get_batch_info(mailing)` → dict (Batch-Aufteilung)

**Tracking:**
- `generate_tracking_token(empfaenger)` → str
- `track_klick(token, link_typ)` → bool
- `handle_abmeldung(token)` → bool

**Zielgruppen:**
- `create_zielgruppe(name, filter_json)` → MailingZielgruppe
- `apply_zielgruppe(mailing, zielgruppe)` → int (Anzahl Empfänger)

### Personalisierungs-Platzhalter

| Platzhalter | Beschreibung | Beispiel |
|-------------|--------------|----------|
| `{{ briefanrede }}` | Anrede des Kunden | "Herr Müller" |
| `{{ firmenname }}` | Firmierung des Kunden | "Müller GmbH" |
| `{{ vorname }}` | Vorname des Kontakts | "Hans" |
| `{{ nachname }}` | Nachname des Kontakts | "Müller" |
| `{{ email }}` | E-Mail-Adresse | "hans@mueller.de" |
| `{{ fragebogen_link }}` | Magic-Link zum Fragebogen | (auto-generiert) |
| `{{ abmelde_link }}` | Link zur Abmeldung | (auto-generiert) |
| `{{ profil_link }}` | Link zur Profil-Seite | `/m/profil/<token>` |
| `{{ empfehlen_link }}` | Link zum Weiterempfehlungs-Formular | `/m/empfehlen/<token>` |
| `{{ browser_link }}` | Link zur Browser-Ansicht | `/m/browser/<token>` |
| `{{ cta_link }}` | Berechneter CTA-Link | Fragebogen oder externe URL |
| `{{ portal_name }}` | Name des Portals | "ev247" |
| `{{ jahr }}` | Aktuelles Jahr | "2026" |
| `{{ betreiber }}` | Betreiber-Kunde-Objekt | (Objekt mit Adresse, etc.) |
| `{{ branding }}` | Branding-Konfiguration | (Objekt mit Logo, Farben, etc.) |

---

## Routes

### Admin-Routes (`mailing_admin_bp`)

Prefix: `/admin/mailing/`

| Route | Methode | Funktion | Beschreibung |
|-------|---------|----------|--------------|
| `/` | GET | `index` | Liste aller Mailings |
| `/neu` | GET, POST | `neu` | Neues Mailing erstellen |
| `/<id>` | GET | `detail` | Mailing-Detail mit Statistiken |
| `/<id>/edit` | GET, POST | `edit` | Bearbeiten (nur ENTWURF) |
| `/<id>/editor` | GET | `editor` | Visueller Sektionen-Editor |
| `/<id>/editor/save` | POST | `editor_save` | Sektionen speichern (AJAX) |
| `/<id>/empfaenger` | GET | `empfaenger` | Empfänger verwalten |
| `/<id>/empfaenger/add` | POST | `empfaenger_add` | Empfänger hinzufügen |
| `/<id>/empfaenger/remove` | POST | `empfaenger_remove` | Empfänger entfernen |
| `/<id>/vorschau` | GET | `vorschau` | HTML-Preview |
| `/<id>/test-senden` | POST | `test_senden` | Test-E-Mail an eigene Adresse |
| `/<id>/senden` | POST | `senden` | Versand starten |
| `/<id>/statistik` | GET | `statistik` | Detaillierte Versand-Statistiken |
| `/zielgruppen` | GET | `zielgruppen` | Zielgruppen verwalten |
| `/zielgruppen/neu` | GET, POST | `zielgruppe_neu` | Neue Zielgruppe |
| `/zielgruppen/<id>/edit` | GET, POST | `zielgruppe_edit` | Zielgruppe bearbeiten |

### Öffentliche Routes (`mailing_bp`)

Prefix: `/m/`

| Route | Methode | Funktion | Beschreibung |
|-------|---------|----------|--------------|
| `/t/<token>` | GET | `track_click` | Klick-Tracking + Redirect |
| `/abmelden/<token>` | GET | `abmelden` | Abmelde-Seite |
| `/abmelden/<token>` | POST | `abmelden_confirm` | Abmeldung durchführen |
| `/profil/<token>` | GET | `profil` | Persönliche Daten anzeigen |
| `/empfehlen/<token>` | GET | `empfehlen` | Weiterempfehlungs-Formular |
| `/empfehlen/<token>` | POST | `empfehlen_submit` | Weiterempfehlung senden |
| `/browser/<token>` | GET | `browser_ansicht` | Mailing im Browser anzeigen |

---

## Templates

### Admin-Templates

```
app/templates/mailing_admin/
├── index.html          # Liste (ENTWURF / VERSENDET)
├── form.html           # Neu/Bearbeiten Formular
├── detail.html         # Detail + Statistik-Übersicht
├── editor.html         # Baukasten-Editor (Drag & Drop)
├── empfaenger.html     # Empfänger-Verwaltung
├── vorschau.html       # Preview im Browser
├── statistik.html      # Detaillierte Statistiken
├── zielgruppen/
│   ├── index.html      # Zielgruppen-Liste
│   └── form.html       # Zielgruppe Neu/Bearbeiten
```

### E-Mail-Sektionen-Templates

```
app/templates/mailing/email/
├── base.html                   # E-Mail-Wrapper (Branding)
├── sektion_header.html         # Logo, Kontakt-Links, Browser-Link
├── sektion_hero.html           # Headline, Subline, opt. Bild
├── sektion_text_bild.html      # Freier Content mit opt. Bild
├── sektion_fragebogen_cta.html # Legacy CTA-Button (wird von cta_button ersetzt)
├── sektion_cta_button.html     # Universeller CTA-Button (Fragebogen oder extern)
├── sektion_footer.html         # Impressum, Abmelde-Link, Profil, Weiterempfehlen
└── weiterempfehlung.html       # E-Mail für Weiterempfehlungen
```

### Öffentliche Templates

```
app/templates/mailing/
├── abmelden.html       # Abmelde-Bestätigung
├── abgemeldet.html     # Erfolgs-Seite nach Abmeldung
├── fehler.html         # Fehlerseite für ungültige Links
├── profil.html         # Persönliche Daten anzeigen
├── empfehlen.html      # Weiterempfehlungs-Formular
└── empfohlen.html      # Erfolgsseite nach Empfehlung
```

---

## Fragebogen-Integration

### Workflow

```
1. Admin erstellt Mailing mit Fragebogen-CTA-Sektion
2. Admin wählt aktiven Fragebogen aus Dropdown
3. Admin fügt Empfänger hinzu (manuell oder via Zielgruppe)
4. Beim Versand (pro Empfänger):
   a) ensure_fragebogen_teilnahme() → erstellt/holt Teilnahme mit Magic-Token
   b) Generiere Tracking-URL: /m/t/<tracking_token>?url=<magic_link>
   c) Rendere E-Mail mit personalisiertem CTA-Button
5. Empfänger klickt CTA:
   a) Tracking-Route erfasst Klick in mailing_klick
   b) Redirect zu /dialog/t/<magic_token>
   c) Kunde füllt Fragebogen aus (bestehendes System aus PRD-006)
```

### Tracking-URL Aufbau

Der Fragebogen-Link wird als Tracking-URL generiert:

```
https://ev247.de/m/t/abc123?typ=fragebogen&url=https://ev247.de/dialog/t/xyz789
```

Bei Klick:
1. `track_klick()` speichert Klick mit `link_typ='fragebogen'`
2. Redirect zur Original-URL (`/dialog/t/xyz789`)

---

## Rate-Limiting (Brevo)

### Tageslimit: 300 E-Mails

Bei Mailings mit mehr als 300 Empfängern wird ein **manuelles Batching** angeboten:

**UI-Hinweis bei Versand:**
```
Sie haben 450 Empfänger, aber nur 280 E-Mails heute verfügbar.

Batch 1: 280 E-Mails heute versenden
Batch 2: 170 E-Mails morgen versenden

[Batch 1 jetzt senden] [Abbrechen]
```

**Empfänger-Status nach Batch-Versand:**
- VERSENDET: E-Mail erfolgreich gesendet
- AUSSTEHEND: Für nächsten Batch vorgemerkt
- FEHLGESCHLAGEN: Versand fehlgeschlagen (mit Fehlermeldung)

---

## DSGVO-Konformität

### Abmelde-Link

Jede E-Mail enthält im Footer einen Abmelde-Link:

```html
<a href="{{ abmelde_link }}">Vom Newsletter abmelden</a>
```

### Abmelde-Prozess

1. Kunde klickt Abmelde-Link
2. Bestätigungsseite wird angezeigt
3. Bei Bestätigung:
   - `kunde.mailing_abgemeldet = True`
   - `kunde.mailing_abgemeldet_am = datetime.utcnow()`
4. Erfolgsseite wird angezeigt
5. Kunde wird bei zukünftigen Mailings automatisch ausgeschlossen

---

## Implementierungs-Phasen

### Phase 1: Basis-Infrastruktur (MVP)

- [ ] PRD-013 Dokument erstellen
- [ ] Models erstellen (`mailing.py`)
- [ ] Migration + Kunde-Erweiterung
- [ ] `MailingService` Basis (CRUD)
- [ ] Admin-Routes (Liste, Neu, Detail)
- [ ] Basis-Templates (Liste, Form)
- [ ] Blueprint registrieren

### Phase 2: Baukasten-Editor

- [ ] Sektionen-Schema definieren
- [ ] E-Mail-Sektionen-Templates
- [ ] Editor-UI (Drag & Drop mit SortableJS)
- [ ] Preview-Funktion
- [ ] Test-Versand an eigene Adresse

### Phase 3: Empfänger & Versand

- [ ] Empfänger-Management UI
- [ ] Zielgruppen-CRUD
- [ ] Fragebogen-Integration (ensure_teilnahme)
- [ ] Versand-Logik mit Batch-Warnung
- [ ] Abmelde-Link + Opt-out Route

### Phase 4: Tracking & Statistik

- [x] Tracking-Token System
- [x] Klick-Tracking Route
- [x] Statistik-Ansicht
- [x] Modul-Übersicht Integration

### Phase 5: Editor-Erweiterung & Öffentliche Seiten

- [x] Flyout-UI statt Modals (Bootstrap Offcanvas)
- [x] Hero-Sektion (Headline, Subline, Bild, Hintergrundfarbe)
- [x] CTA-Button vereinheitlicht (Fragebogen oder externe URL)
- [x] Header erweitert (Browser-Link, Telefon, E-Mail-Link)
- [x] Footer erweitert (Impressum-Block, Profil-Link, Weiterempfehlen-Link)
- [x] Öffentliche Profil-Seite (`/m/profil/<token>`)
- [x] Weiterempfehlungs-Formular (`/m/empfehlen/<token>`)
- [x] Browser-Ansicht (`/m/browser/<token>`)
- [x] DB-Erweiterung: Kunde.handelsregister_info, Kunde.umsatzsteuer_id
- [x] Config-Keys: betreiber_impressum_url, betreiber_datenschutz_url, betreiber_kontaktformular_url

---

## Verifikation

### Phase 1

- [ ] Mailing erstellen funktioniert
- [ ] Liste zeigt Mailings gruppiert nach Status
- [ ] Detail-Ansicht zeigt Mailing-Informationen

### Phase 2

- [ ] Sektionen können hinzugefügt/sortiert/entfernt werden
- [ ] Preview zeigt gerenderte E-Mail
- [ ] Test-E-Mail kommt an

### Phase 3

- [ ] Empfänger können aus Kunden/Leads gewählt werden
- [ ] Fragebogen-CTA enthält korrekten Magic-Link
- [ ] Batch-Warnung erscheint bei >300 Empfängern
- [ ] Abmelde-Link funktioniert

### Phase 4

- [x] Klicks auf Fragebogen-Link werden erfasst
- [x] Statistik zeigt versendet/geklickt/abgemeldet
- [x] Modul-Übersicht zeigt Mailing-Kachel

### Phase 5

- [x] Flyout öffnet/schließt smooth (statt Modal)
- [x] Alle 5 Sektionstypen im Dropdown sichtbar
- [x] Hero-Sektion kann hinzugefügt und bearbeitet werden
- [x] CTA-Button mit Fragebogen- und externe-URL-Auswahl
- [x] Footer zeigt Impressum-Daten
- [x] Profil-Seite zeigt Kundendaten
- [x] Weiterempfehlen-Formular sendet E-Mail
- [x] Browser-Ansicht zeigt vollständiges Mailing
