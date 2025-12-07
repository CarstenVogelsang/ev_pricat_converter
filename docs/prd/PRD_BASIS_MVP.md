# PRD Basis MVP

## Projekt ev247.de

**Version:** 1.1
**Datum:** 07.12.2025
**Status:** Draft

---

## 1. Zielsetzung

Multi-Tool-Plattform für e-vendo Mitarbeiter und Kunden.

---

## 2. Globale Plattform-Aufgaben

| # | Task | Status | Beschreibung |
|---|------|--------|--------------|
| G1 | Branding & Landing Page | ✅ Fertig | Logo, Farben, Copyright, öffentliche Startseite |
| G2 | Hauptmenü mit Rollen | ⏳ Offen | Menü-Sichtbarkeit nach Rolle |
| G3 | Rolle umbenennen | ⏳ Offen | sachbearbeiter → mitarbeiter |
| G4 | Rolle hinzufügen | ⏳ Offen | Neue Rolle: kunde |
| G5 | Kunde-Model | ⏳ Offen | Kunde-Entity mit User-Zuordnung |
| G6 | Repo umbenennen | ⏳ Offen | ev_pricat_converter → ev247 |
| G7 | API-Kostenabrechnung | ✅ Fertig | Tracking von API-Calls (Credits, Kosten in Euro) pro User/Kunde |

**Letztes Update:** 2025-12-07

---

## 3. Rollen-Konzept

### Aktuelle Rollen
- `admin` - Vollzugriff auf alle Funktionen
- `sachbearbeiter` - e-vendo Mitarbeiter

### Geplante Rollen
- `admin` - Vollzugriff
- `mitarbeiter` - e-vendo Mitarbeiter (Umbenennung von sachbearbeiter)
- `kunde` - Externer Kunde mit eingeschränktem Zugriff

### Menü-Sichtbarkeit (Ziel)

| Menüpunkt | admin | mitarbeiter | kunde |
|-----------|-------|-------------|-------|
| PRICAT Konverter | ✓ | ✓ | ✗ |
| Lead- & Kundenreport | ✓ | ✓ | ✓ |
| Lieferanten-Verwaltung | ✓ | ✓ | ✓ |
| Content Generator | ✓ | ✓ | ✓ |
| Admin | ✓ | ✗ | ✗ |
| DB Admin | ✓ | ✗ | ✗ |

---

## 4. Module

### Aktiv
- [PRD-001 PRICAT Converter](module/PRD-001-pricat-converter/PRD-001-pricat-converter.md) - VEDES PRICAT → Elena Import
- [PRD-002 Lead & Kundenreport](module/PRD-002-lead-kundenreport/PRD-002-lead-kundenreport.md) - Kundenverwaltung mit CI-Analyse

### Geplant
- [PRD-003 Kunde-Lieferanten-Zuordnung](module/PRD-003-kunde-hat-lieferanten/PRD-003-kunde-hat-lieferanten.md) - Kunden wählen relevante Lieferanten
- [PRD-004 Content Generator](module/PRD-004-content-generator/PRD-004-content-generator.md) - KI-generierte Texte via OpenRouter

---

## 5. Tech-Stack

| Komponente | Technologie | Begründung |
|------------|-------------|------------|
| **Sprache** | Python 3.11+ | Vorgabe, gute CSV/Excel-Unterstützung |
| **Package Manager** | uv | Schnell, modernes Dependency-Management |
| **Web-Framework** | Flask 3.x | Leichtgewichtig, schnell für MVP |
| **Prod-Server** | gunicorn | Produktions-WSGI-Server |
| **Datenbank** | SQLite / PostgreSQL | SQLite für Dev, PostgreSQL für Prod |
| **ORM** | SQLAlchemy | Flexible DB-Abstraktion |
| **Migrationen** | Flask-Migrate (Alembic) | Automatische Schema-Migrationen |
| **Admin** | Flask-Admin | DB-Verwaltung unter /db-admin |
| **Auth** | Flask-Login | Session-basierte Authentifizierung |
| **Frontend** | Jinja2 + Bootstrap 5 | Server-Side Rendering |
| **Deployment** | Nixpacks / Coolify | Container-Deployment |

---

## 6. Projektstruktur

```
ev247/
├── app/
│   ├── __init__.py           # Flask App Factory
│   ├── config.py             # Konfiguration
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py           # SQLAlchemy Base
│   │   ├── user.py           # User Model mit Rollen
│   │   └── config.py         # Config Key-Value Model
│   ├── services/
│   │   └── ...               # Business Logic
│   ├── routes/
│   │   ├── main.py           # Haupt-Blueprint
│   │   ├── auth.py           # Login/Logout
│   │   └── admin.py          # Admin-Panel
│   └── templates/
│       ├── base.html         # Basis-Template
│       └── ...
├── migrations/               # Alembic Migrationen
├── instance/
│   └── app.db                # SQLite Datenbank (Dev)
├── pyproject.toml            # Dependencies (uv)
├── uv.lock
└── run.py                    # Entry Point
```

---

## 7. Basis-Datenbank-Schema

### User Model

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| id | INTEGER PK | Primärschlüssel |
| username | VARCHAR(80) UNIQUE | Benutzername |
| email | VARCHAR(120) UNIQUE | E-Mail |
| password_hash | VARCHAR(255) | Passwort (bcrypt) |
| role | VARCHAR(20) | admin / sachbearbeiter / kunde |
| aktiv | BOOLEAN | Account aktiv |
| created_at | DATETIME | Erstellungszeitpunkt |

### Config Model (Key-Value Store)

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| id | INTEGER PK | Primärschlüssel |
| key | VARCHAR(50) UNIQUE | Konfigurations-Schlüssel |
| value | TEXT | Konfigurations-Wert |
| beschreibung | VARCHAR(255) | Beschreibung |
| created_at | DATETIME | Erstellungszeitpunkt |
| updated_at | DATETIME | Letztes Update |

### KundeApiNutzung Model (API-Kostentracking)

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| id | INTEGER PK | Primärschlüssel |
| kunde_id | INTEGER FK | Fremdschlüssel zu Kunde |
| user_id | INTEGER FK | Fremdschlüssel zu User (wer hat den Call ausgelöst) |
| api_service | VARCHAR(50) | Name des API-Services (z.B. "firecrawl") |
| api_endpoint | VARCHAR(100) | Endpoint (z.B. "scrape/branding") |
| credits_used | INTEGER | Verbrauchte Credits |
| kosten_euro | DECIMAL(10,4) | Kosten in Euro |
| beschreibung | VARCHAR(255) | Beschreibung des Calls |
| created_at | DATETIME | Zeitpunkt des Calls |

---

## 8. Infrastruktur

### Aktuell implementiert
- Flask 3.x mit Blueprints
- SQLAlchemy (SQLite/PostgreSQL/MariaDB)
- Flask-Login Authentifizierung
- Flask-Admin für DB-Verwaltung (/db-admin)
- Flask-Migrate für Schema-Migrationen
- S3-kompatibler Objektspeicher (optional)
- Coolify Deployment mit nixpacks
- Config Import/Export als JSON

### Geplant
- OpenRouter API Integration (für Content Generator)
- Kunde-Lieferant Zuordnung (n:m)

---

## 9. UI/UX Richtlinien

### Toast-Meldungen

Alle Benutzer-Feedback-Meldungen werden als **Bootstrap Toast-Meldungen** angezeigt.

**Keine Alert-Boxen** im Seiteninhalt.

| Kategorie | CSS-Klasse | Verwendung |
|-----------|------------|------------|
| success | `text-bg-success` | Aktion erfolgreich |
| danger | `text-bg-danger` | Fehler aufgetreten |
| warning | `text-bg-warning` | Warnung/Hinweis |
| info | `text-bg-info` | Information |

### Weitere Konventionen

- **Tabellen:** Bootstrap `table-hover` für interaktive Listen
- **Buttons:** Primäre Aktionen `btn-primary`, sekundäre `btn-outline-*`
- **Status-Badges:** `badge bg-success/secondary` für Aktiv/Inaktiv
- **Filter:** Dropdown oder Button-Group für Aktiv/Inaktiv/Alle
