# PRD: Audit-Log System (Basis-Modul)

> **Status:** Geplant
> **Version:** 1.0
> **Erstellt:** 2025-12-12

---

## 1. Übersicht

### 1.1 Ziel

Ein zentrales Audit-Log-System zur Dokumentation wichtiger Ereignisse in allen Modulen der ev247-Plattform. Das System ermöglicht Nachvollziehbarkeit, Compliance-Anforderungen und Fehleranalyse.

### 1.2 Scope

- Ist ein **Basis-Modul** (immer aktiv, nicht deaktivierbar)
- Loggt Ereignisse aus allen Modulen
- Bietet Admin-UI zur Einsicht und Filterung
- DSGVO-konform (User-IDs bleiben bei Löschung erhalten)

---

## 2. Abhängigkeiten

### 2.1 Modul-Model (Minimal)

Das Logging-System benötigt ein minimales `Modul`-Model zur Referenzierung der Quellmodule.

> **Hinweis:** Vollständige Modulverwaltung (aktivieren/deaktivieren, Rollenzugriff) wird separat in [PRD_BASIS_MODULVERWALTUNG.md](PRD_BASIS_MODULVERWALTUNG.md) dokumentiert.

**Minimales Model:**

```python
class Modul(db.Model):
    """Basis-Model für Module (minimal für Logging)."""
    __tablename__ = 'modul'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)  # z.B. 'kunden', 'pricat'
    name = db.Column(db.String(100), nullable=False)              # z.B. 'Lead & Kundenreport'
    ist_basis = db.Column(db.Boolean, default=False)              # Basis-Module immer aktiv
    aktiv = db.Column(db.Boolean, default=True)
```

### 2.2 Initiale Module (Seed)

| Code | Name | Ist Basis |
|------|------|-----------|
| `system` | System & Administration | ✅ |
| `stammdaten` | Stammdatenpflege | ✅ |
| `logging` | Audit-Log | ✅ |
| `auth` | Authentifizierung | ✅ |
| `kunden` | Lead & Kundenreport | ❌ |
| `pricat` | PRICAT Converter | ❌ |
| `lieferanten` | Meine Lieferanten | ❌ |
| `content` | Content Generator | ❌ |

---

## 3. Datenmodell

### 3.1 AuditLog Tabelle

```python
class AuditLog(db.Model):
    """Audit-Log für wichtige Ereignisse in allen Modulen."""
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Wer hat die Aktion ausgeführt?
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref='audit_logs')

    # In welchem Modul?
    modul_id = db.Column(db.Integer, db.ForeignKey('modul.id'), nullable=False)
    modul = db.relationship('Modul', backref='audit_logs')

    # Was ist passiert?
    aktion = db.Column(db.String(100), nullable=False, index=True)
    details = db.Column(db.Text, nullable=True)

    # Wie wichtig?
    wichtigkeit = db.Column(db.String(20), default='niedrig', index=True)
    # Werte: niedrig, mittel, hoch, kritisch

    # Welche Entität war betroffen?
    entity_type = db.Column(db.String(50), nullable=True)  # z.B. 'Kunde', 'Branche'
    entity_id = db.Column(db.Integer, nullable=True)

    # Zusätzliche Metadaten
    ip_adresse = db.Column(db.String(45), nullable=True)  # IPv6-kompatibel
```

### 3.2 Felder-Beschreibung

| Feld | Typ | Beschreibung | Index |
|------|-----|--------------|-------|
| `id` | Integer PK | Auto-increment | ✅ |
| `timestamp` | DateTime | Zeitpunkt des Ereignisses | ✅ |
| `user_id` | Integer FK | User (nullable für System-Events) | - |
| `modul_id` | Integer FK | Referenz auf `modul.id` | - |
| `aktion` | String(100) | Aktion-Code (z.B. `hauptbranche_geloescht`) | ✅ |
| `details` | Text | Detailbeschreibung (human-readable) | - |
| `wichtigkeit` | String(20) | niedrig / mittel / hoch / kritisch | ✅ |
| `entity_type` | String(50) | Betroffene Entität (z.B. `Kunde`) | - |
| `entity_id` | Integer | ID der betroffenen Entität | - |
| `ip_adresse` | String(45) | IP des Users (IPv6: max 45 Zeichen) | - |

---

## 4. Helper-Funktion

### 4.1 log_event()

Eine zentrale Helper-Funktion vereinfacht das Logging aus allen Modulen:

```python
# app/services/logging_service.py

def log_event(
    modul: str,
    aktion: str,
    details: str = None,
    wichtigkeit: str = 'niedrig',
    entity_type: str = None,
    entity_id: int = None,
    user_id: int = None
) -> AuditLog:
    """
    Erstellt einen Audit-Log-Eintrag.

    Args:
        modul: Modul-Code (z.B. 'kunden', 'system')
        aktion: Aktion-Code (z.B. 'hauptbranche_geloescht')
        details: Detailbeschreibung (optional)
        wichtigkeit: niedrig/mittel/hoch/kritisch (default: niedrig)
        entity_type: Typ der betroffenen Entität (optional)
        entity_id: ID der betroffenen Entität (optional)
        user_id: User-ID (optional, default: current_user.id)

    Returns:
        AuditLog: Der erstellte Log-Eintrag
    """
    from flask import request
    from flask_login import current_user

    # Modul-ID ermitteln
    modul_obj = Modul.query.filter_by(code=modul).first()
    if not modul_obj:
        raise ValueError(f"Unbekanntes Modul: {modul}")

    # User-ID: Explizit oder current_user
    if user_id is None and current_user.is_authenticated:
        user_id = current_user.id

    # IP-Adresse aus Request
    ip_adresse = None
    if request:
        ip_adresse = request.remote_addr

    log_entry = AuditLog(
        user_id=user_id,
        modul_id=modul_obj.id,
        aktion=aktion,
        details=details,
        wichtigkeit=wichtigkeit,
        entity_type=entity_type,
        entity_id=entity_id,
        ip_adresse=ip_adresse
    )

    db.session.add(log_entry)
    # Commit erfolgt durch aufrufende Funktion

    return log_entry
```

### 4.2 Verwendungsbeispiel

```python
# In app/routes/kunden.py

from app.services.logging_service import log_event

@kunden_bp.route('/<int:id>/hauptbranche', methods=['DELETE'])
def delete_hauptbranche(id):
    kunde = Kunde.query.get_or_404(id)
    alte_hauptbranche = kunde.hauptbranche.name

    # Unterbranchen löschen...
    deleted_count = KundeBranche.query.filter_by(kunde_id=id).count()

    # Logging
    log_event(
        modul='kunden',
        aktion='hauptbranche_geloescht',
        details=f'Hauptbranche "{alte_hauptbranche}" und {deleted_count} Unterbranchen entfernt',
        wichtigkeit='mittel',
        entity_type='Kunde',
        entity_id=id
    )

    db.session.commit()
    return jsonify({'success': True})
```

---

## 5. Konfiguration

### 5.1 Config-Einträge

Neue Einträge in der `config`-Tabelle:

| Key | Beschreibung | Default | Typ |
|-----|--------------|---------|-----|
| `log_aufbewahrung_tage` | Tage bis zur automatischen Löschung | `365` | Integer |
| `log_aufbewahrung_kritisch` | Tage für kritische Logs (0 = unbegrenzt) | `0` | Integer |
| `log_email_bei_kritisch` | E-Mail an Admins bei kritischen Events | `false` | Boolean |

### 5.2 E-Mail-Benachrichtigung (Optional)

Für E-Mail-Benachrichtigungen bei kritischen Events wird SMTP-Konfiguration benötigt.

**Zusätzliche Config-Einträge (SMTP):**

| Key | Beschreibung |
|-----|--------------|
| `smtp_server` | SMTP Server (z.B. `smtp.gmail.com`) |
| `smtp_port` | Port (587 für TLS, 465 für SSL) |
| `smtp_user` | Benutzername |
| `smtp_password` | Passwort (verschlüsselt gespeichert) |
| `smtp_from` | Absender-Adresse |
| `smtp_admin_emails` | Komma-getrennte Admin-E-Mail-Adressen |

> **Hinweis:** SMTP-Konfiguration wird in den Systemeinstellungen (`/admin/settings`) unter einem neuen Tab "E-Mail" verwaltet.

---

## 6. Admin-UI

### 6.1 Route und Navigation

**Route:** `/admin/logs`

**Sidebar-Link:** Unter Kategorie "System" oder "Einstellungen":
```
📋 Audit-Log
```

### 6.2 UI-Mockup

```
┌─────────────────────────────────────────────────────────────────────┐
│ 📋 Audit-Log                                                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Filter:                                                            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐ │
│  │ Von Datum ▼  │ │ Bis Datum ▼  │ │ User ▼       │ │ Modul ▼    │ │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘ │
│                                                                     │
│  Wichtigkeit:  ☑ Kritisch  ☑ Hoch  ☑ Mittel  ☐ Niedrig             │
│                                                                     │
│  [Filter anwenden]                           [Export CSV] [JSON]   │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  Zeitstempel        │ User      │ Modul   │ Aktion           │ !   │
├─────────────────────┼───────────┼─────────┼──────────────────┼─────┤
│  12.12.2025 15:23   │ C.Vogels. │ Kunden  │ hauptbranche_gel.│ 🟡  │
│  12.12.2025 14:10   │ Admin     │ System  │ config_geaendert │ 🟠  │
│  12.12.2025 12:05   │ System    │ Auth    │ login_fehlgeschl.│ 🔴  │
│  ...                │           │         │                  │     │
├─────────────────────────────────────────────────────────────────────┤
│  Seite 1 von 12                              ◀ 1 2 3 ... 12 ▶      │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.3 Wichtigkeits-Anzeige

| Stufe | Icon | Farbe | Badge-Klasse |
|-------|------|-------|--------------|
| kritisch | 🔴 | Rot | `badge bg-danger` |
| hoch | 🟠 | Orange | `badge bg-warning` |
| mittel | 🟡 | Gelb | `badge bg-info` |
| niedrig | ⚪ | Grau | `badge bg-secondary` |

### 6.4 Detail-Ansicht (Modal)

Bei Klick auf einen Log-Eintrag öffnet sich ein Modal mit allen Details:

- Vollständiger Zeitstempel
- User (Name + E-Mail)
- Modul
- Aktion
- Details (vollständiger Text)
- Betroffene Entität (Typ + ID mit Link)
- IP-Adresse

### 6.5 Export-Funktionen

- **CSV:** Für Excel-Analyse
- **JSON:** Für technische Weiterverarbeitung

Beide Exporte respektieren die aktuellen Filter.

---

## 7. DSGVO-Konformität

### 7.1 User-Löschung

Bei Löschung eines Users:
- `user_id` bleibt in `audit_log` erhalten
- Anzeige: "Gelöschter Benutzer (ID: X)"
- **Kein** Cascade-Delete der Logs

**Implementierung:**

```python
# Bei User-Löschung NICHT:
# db.relationship('AuditLog', cascade='all, delete-orphan')

# Stattdessen in der Admin-UI:
def get_user_display(log_entry):
    if log_entry.user:
        return log_entry.user.name
    elif log_entry.user_id:
        return f"Gelöschter Benutzer (ID: {log_entry.user_id})"
    else:
        return "System"
```

### 7.2 Aufbewahrungsfristen

- Standard: 365 Tage (konfigurierbar)
- Kritische Events: Unbegrenzt (konfigurierbar)
- Automatische Bereinigung via Scheduled Job (später)

---

## 8. Initial zu loggende Ereignisse

### 8.1 Priorität 1 (Sofort implementieren)

| Modul | Aktion | Wichtigkeit | Trigger |
|-------|--------|-------------|---------|
| kunden | `hauptbranche_geloescht` | mittel | DELETE /kunden/<id>/hauptbranche |
| kunden | `kunde_geloescht` | hoch | DELETE /kunden/<id> |

### 8.2 Priorität 2 (Nach Basis-Implementierung)

| Modul | Aktion | Wichtigkeit | Trigger |
|-------|--------|-------------|---------|
| stammdaten | `branche_geloescht` | mittel | Branche löschen |
| stammdaten | `hauptbranche_geloescht` | hoch | Hauptbranche löschen |
| system | `user_angelegt` | mittel | User erstellen |
| system | `user_geloescht` | hoch | User löschen |
| system | `config_geaendert_sensibel` | hoch | Sensible Config ändern |
| auth | `login_fehlgeschlagen_mehrfach` | hoch | 3+ fehlgeschlagene Logins |
| auth | `passwort_geaendert` | niedrig | Passwort ändern |

### 8.3 Priorität 3 (Optional)

| Modul | Aktion | Wichtigkeit |
|-------|--------|-------------|
| pricat | `export_erstellt` | niedrig |
| kunden | `branche_zugeordnet` | niedrig |
| kunden | `rolle_zugeordnet` | niedrig |

---

## 9. Implementierungsreihenfolge

| # | Aufgabe | Datei |
|---|---------|-------|
| 1 | Modul-Model (minimal) erstellen | `app/models/modul.py` |
| 2 | AuditLog-Model erstellen | `app/models/audit_log.py` |
| 3 | Migration erstellen | `flask db migrate` |
| 4 | Seed-Daten für Module | `app/cli.py` |
| 5 | Helper-Funktion `log_event()` | `app/services/logging_service.py` |
| 6 | Admin-Route `/admin/logs` | `app/routes/admin.py` |
| 7 | Template mit Filtern | `app/templates/administration/logs.html` |
| 8 | Sidebar-Link hinzufügen | `app/templates/administration/base.html` |
| 9 | Log-Integration: Hauptbranche-Löschung | `app/routes/kunden.py` |

---

## 10. Akzeptanzkriterien

- [ ] `Modul`-Model existiert mit Seed-Daten
- [ ] `AuditLog`-Model existiert
- [ ] `log_event()` Helper-Funktion funktioniert
- [ ] Admin-UI unter `/admin/logs` erreichbar
- [ ] Filter nach Datum, User, Modul, Wichtigkeit funktionieren
- [ ] Pagination funktioniert (50 Einträge/Seite)
- [ ] Export als CSV und JSON möglich
- [ ] Hauptbranche-Löschung wird geloggt
- [ ] Bei User-Löschung: Logs bleiben mit Hinweis erhalten

---

## 11. Zukünftige Erweiterungen

- **Automatische Bereinigung:** Cronjob für Log-Cleanup nach Aufbewahrungsfrist
- **E-Mail-Alerts:** SMTP-Integration für kritische Events
- **Dashboard-Widget:** Letzte kritische Events auf Admin-Dashboard
- **API-Endpoint:** REST-API für externe Log-Abfrage
