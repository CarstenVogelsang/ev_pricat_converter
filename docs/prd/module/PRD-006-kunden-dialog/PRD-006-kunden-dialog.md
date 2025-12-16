# PRD-006: Kunden-Dialog

**Modul-Code:** `dialog`
**Status:** Aktiv
**Erstellt:** 2025-12-15
**Typ:** KUNDENPROJEKT

## Übersicht

Das Modul "Kunden-Dialog" ermöglicht die Erstellung von Fragebögen für Kundenbefragungen.
Kunden können entweder über das Portal (mit Login) oder via Magic-Link (ohne Login) teilnehmen.

## Kernfunktionen

### 1. Fragebogen-Verwaltung (Admin)

- **Fragebogen erstellen**: Titel, Beschreibung, JSON-Definition mit Fragen
- **Fragen-Typen**:
  - `single_choice` - Einzelauswahl
  - `multiple_choice` - Mehrfachauswahl
  - `skala` - Bewertungsskala (z.B. 1-5)
  - `text` - Freitext (optional mehrzeilig)
  - `ja_nein` - Ja/Nein-Auswahl
- **Status-Workflow**: ENTWURF → AKTIV → GESCHLOSSEN
- **Teilnehmer-Verwaltung**: Kunden hinzufügen, Einladungen senden
- **Auswertung**: Statistiken und Antworten-Übersicht

### 2. Kunden-Teilnahme

- **Portal-Zugang** (mit Login): Übersicht aller zugeordneten Fragebögen
- **Magic-Link** (ohne Login): Direktzugang via E-Mail-Link
- **Auto-Save**: Antworten werden automatisch gespeichert
- **Pflichtfragen**: Müssen vor Abschluss beantwortet werden

### 3. User-Erstellung für Kunden

- Kunden können einen User-Account erhalten
- Sicherer Passwort-Versand via 2 E-Mails:
  1. Portal-URL + Benutzername
  2. Passwort-Link (einmalige Anzeige)
- E-Mail-Versand via Brevo REST API

## Datenmodelle

### Fragebogen
```
id, titel, beschreibung, definition_json, status
erstellt_von_id, erstellt_am, aktiviert_am, geschlossen_am
```

### FragebogenTeilnahme
```
id, fragebogen_id, kunde_id, token (Magic-Link)
status: EINGELADEN → GESTARTET → ABGESCHLOSSEN
eingeladen_am, gestartet_am, abgeschlossen_am, einladung_gesendet_am
```

### FragebogenAntwort
```
id, teilnahme_id, frage_id, antwort_json
```

### PasswordToken
```
id, user_id, token, password_plain (temp)
expires_at (48h), revealed_at
```

### Kunde-Erweiterung
```
+ user_id (FK zu User, nullable, unique)
```

## JSON-Schema für Fragen

```json
{
  "fragen": [
    {
      "id": "q1",
      "typ": "single_choice",
      "frage": "Wie zufrieden sind Sie?",
      "optionen": ["Sehr zufrieden", "Zufrieden", "Neutral", "Unzufrieden"],
      "pflicht": true
    },
    {
      "id": "q2",
      "typ": "skala",
      "frage": "Bewerten Sie unseren Service",
      "min": 1,
      "max": 5,
      "labels": {"1": "Schlecht", "5": "Sehr gut"}
    },
    {
      "id": "q3",
      "typ": "text",
      "frage": "Weitere Anmerkungen?",
      "multiline": true,
      "pflicht": false
    }
  ]
}
```

## Routes

### Öffentlich (ohne Login)

| Route | Methode | Beschreibung |
|-------|---------|--------------|
| `/passwort/?token=...` | GET | Passwort einmalig anzeigen |
| `/dialog/t/<token>` | GET | Fragebogen via Magic-Link |
| `/dialog/t/<token>/antwort` | POST | Antwort speichern (AJAX) |
| `/dialog/t/<token>/abschliessen` | POST | Fragebogen abschließen |
| `/dialog/t/<token>/danke` | GET | Danke-Seite |

### Kunden-Portal (Login erforderlich)

| Route | Methode | Beschreibung |
|-------|---------|--------------|
| `/dialog/` | GET | Meine Fragebögen |
| `/dialog/<id>` | GET | Fragebogen ausfüllen |

### Admin-Bereich (intern)

| Route | Methode | Beschreibung |
|-------|---------|--------------|
| `/admin/dialog/` | GET | Fragebogen-Liste |
| `/admin/dialog/neu` | GET/POST | Neuer Fragebogen |
| `/admin/dialog/<id>` | GET | Fragebogen-Details |
| `/admin/dialog/<id>/edit` | GET/POST | Bearbeiten (nur Entwurf) |
| `/admin/dialog/<id>/status` | POST | Status ändern |
| `/admin/dialog/<id>/teilnehmer` | GET | Teilnehmer verwalten |
| `/admin/dialog/<id>/teilnehmer/add` | POST | Teilnehmer hinzufügen |
| `/admin/dialog/<id>/teilnehmer/<tid>/remove` | POST | Teilnehmer entfernen |
| `/admin/dialog/<id>/einladungen` | POST | Einladungen senden |
| `/admin/dialog/<id>/auswertung` | GET | Statistiken |

### Kunden-API-Erweiterung

| Route | Methode | Beschreibung |
|-------|---------|--------------|
| `/kunden/<id>/user/create` | POST | User für Kunde erstellen |
| `/kunden/<id>/user/send-credentials` | POST | Zugangsdaten senden |
| `/kunden/<id>/user/new-token` | POST | Neues Passwort erstellen |

## Konfiguration

| Key | Beschreibung | Default |
|-----|--------------|---------|
| `brevo_api_key` | Brevo API Key | - |
| `brevo_sender_email` | Absender E-Mail | noreply@e-vendo.de |
| `brevo_sender_name` | Absender Name | e-vendo AG |
| `portal_base_url` | Portal Basis-URL | https://portal.e-vendo.de |

## Berechtigungen

| Rolle | Zugriff |
|-------|---------|
| admin | Voller Zugriff |
| mitarbeiter | Voller Zugriff |
| kunde | Nur eigene Fragebögen (Portal + Magic-Link) |

## Services

- **BrevoService**: E-Mail-Versand via Brevo REST API
- **PasswordService**: User-Erstellung, Token-Management, Credential-Versand
- **FragebogenService**: CRUD, Validierung, Teilnehmer-Management, Auswertung

## Abhängigkeiten

- `requests` - HTTP-Client für Brevo API
- Brevo-Account mit API-Key für E-Mail-Versand

## Dateien

```
app/
├── models/
│   ├── password_token.py          # PasswordToken Model
│   └── fragebogen.py              # Fragebogen, Teilnahme, Antwort
├── services/
│   ├── email_service.py           # BrevoService
│   ├── password_service.py        # PasswordService
│   └── fragebogen_service.py      # FragebogenService
├── routes/
│   ├── passwort.py                # passwort_bp
│   ├── dialog.py                  # dialog_bp
│   └── dialog_admin.py            # dialog_admin_bp
└── templates/
    ├── passwort/                  # 3 Templates
    ├── dialog/                    # 7 Templates
    └── dialog_admin/              # 5 Templates
```
