# CLAUDE.md

Anweisungen für Claude Code in diesem Repository.

## Projekt

**ev247** - Multi-Tool-Plattform für e-vendo Mitarbeiter und Kunden.

## Befehle

```bash
# Setup
uv sync

# Entwicklung
uv run python run.py

# Produktion
uv run gunicorn -w 4 -b 0.0.0.0:5000 'app:create_app()'

# Datenbank
uv run flask init-db       # Tabellen erstellen (nur bei neuer DB)
uv run flask seed          # Testdaten einfügen

# Datenbank-Migrationen (bei Schema-Änderungen)
uv run flask db migrate -m "Beschreibung"  # Migration generieren
uv run flask db upgrade                     # Migration anwenden
uv run flask db downgrade                   # Letzte Migration rückgängig
uv run flask db current                     # Aktuelle DB-Version
```

## Dokumentation

Alle Details zur Architektur, Datenmodellen und Features sind in den PRD-Dokumenten:

### Basis-Plattform

- [docs/prd/PRD_BASIS_MVP.md](docs/prd/PRD_BASIS_MVP.md) - Tech-Stack, Projektstruktur, DB-Schema, UI-Richtlinien
- [docs/prd/PRD_BASIS_CHANGELOG.md](docs/prd/PRD_BASIS_CHANGELOG.md) - Plattform-Änderungen

### Module

| Modul | PRD | Status |
|-------|-----|--------|
| PRICAT Converter | [PRD-001](docs/prd/module/PRD-001-pricat-converter/PRD-001-pricat-converter.md) | Aktiv |
| Lead & Kundenreport | [PRD-002](docs/prd/module/PRD-002-lead-kundenreport/PRD-002-lead-kundenreport.md) | Aktiv |
| Kunde-Lieferanten | [PRD-003](docs/prd/module/PRD-003-kunde-hat-lieferanten/PRD-003-kunde-hat-lieferanten.md) | Geplant |
| Content Generator | [PRD-004](docs/prd/module/PRD-004-content-generator/PRD-004-content-generator.md) | Geplant |

Jedes Modul hat ein eigenes `CHANGELOG.md` im jeweiligen Ordner.

## Wichtige Konventionen

- **UI-Feedback:** Bootstrap Toasts (keine Alert-Boxen)
- **Package Manager:** uv (nicht pip)
- **DB-Schema:** Bei Änderungen `flask db migrate` + `flask db upgrade`, NICHT DB löschen!
- **Sprache Docs:** Deutsch
- **Sprache Code:** Englisch

## Arbeitsweise

1. **Vor Änderungen:** Relevantes PRD-Dokument lesen
2. **Bei neuen Features:** PRD-Dokument aktualisieren
3. **Nach Implementierungen:** Changelogs aktualisieren (siehe unten)
4. **Nach Plan-Modus:** Zugehörige PRD- und CHANGELOG-Dokumente pflegen

### Changelog-Pflege (wichtig!)

Nach jeder Implementierung müssen die relevanten Changelogs aktualisiert werden:

- **Basis-Plattform-Änderungen** (Auth, Admin-UI, Core-Features):
  → [docs/prd/PRD_BASIS_CHANGELOG.md](docs/prd/PRD_BASIS_CHANGELOG.md)

- **Modul-spezifische Änderungen**:
  → `docs/prd/module/PRD-XXX-.../CHANGELOG.md` im jeweiligen Modul-Ordner

Format: [Keep a Changelog](https://keepachangelog.com/de/1.0.0/) mit Kategorien:

- `Added` - Neue Features
- `Changed` - Änderungen an bestehenden Features
- `Fixed` - Bugfixes
- `Removed` - Entfernte Features

## Playwright Login Credentials

Für automatisierte Tests via Playwright MCP können Login-Credentials aus `.env` Variablen gelesen werden:

```bash
# .env
EV247_ADMIN_EMAIL=carsten.vogelsang@e-vendo.de
EV247_ADMIN_PASSWORD=admin123
```

Diese Variablen werden NICHT von der Flask-App verwendet, sondern nur für Claude Code Playwright-Tests.
