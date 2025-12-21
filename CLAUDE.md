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
- [docs/prd/PRD_BASIS_RECHTEVERWALTUNG.md](docs/prd/PRD_BASIS_RECHTEVERWALTUNG.md) - Rollen, Modul-Zugriff, Admin-Sonderrechte
- [docs/prd/PRD_BASIS_CHANGELOG.md](docs/prd/PRD_BASIS_CHANGELOG.md) - Plattform-Änderungen

### Module

| Modul | PRD | Status |
|-------|-----|--------|
| PRICAT Converter | [PRD-001](docs/prd/module/PRD-001-pricat-converter/PRD-001-pricat-converter.md) | Aktiv |
| Lead & Kundenreport | [PRD-002](docs/prd/module/PRD-002-lead-kundenreport/PRD-002-lead-kundenreport.md) | Aktiv |
| Kunde-Lieferanten | [PRD-003](docs/prd/module/PRD-003-kunde-hat-lieferanten/PRD-003-kunde-hat-lieferanten.md) | Geplant |
| Content Generator | [PRD-004](docs/prd/module/PRD-004-content-generator/PRD-004-content-generator.md) | Geplant |
| Kunden-Dialog | [PRD-006](docs/prd/module/PRD-006-kunden-dialog/PRD-006-kunden-dialog.md) | Aktiv |

Jedes Modul hat ein eigenes `CHANGELOG.md` im jeweiligen Ordner.

### V2 Roadmap (nach MVP)

| Feature | Dokument | Hinweis |
|---------|----------|---------|
| Internationalisierung (i18n) | [ROADMAP-V2-i18n](docs/prd/roadmap/ROADMAP-V2-i18n.md) | Nur auf Nachfrage starten! |
| PRD-Management in DB | [ROADMAP-V2-prd-management](docs/prd/roadmap/ROADMAP-V2-prd-management.md) | Nach PRD-006 diskutieren |

## Wichtige Konventionen

- **UI-Feedback:** Bootstrap Toasts (keine Alert-Boxen)
- **Package Manager:** uv (nicht pip)
- **DB-Schema:** Bei Änderungen `flask db migrate` + `flask db upgrade`, NICHT DB löschen!
- **Sprache Docs:** Deutsch
- **Sprache Code:** Englisch
- **Deutsche Texte:** Immer echte Umlaute (ä, ü, ö, ß) verwenden, NICHT ae/ue/oe/ss

## UI-Konventionen für Module

### Audit-Logging

Alle Module müssen wichtige Benutzeraktionen in die `audit_log` Tabelle loggen.
Nutze dafür den `logging_service`:

```python
from app.services import log_event, log_kritisch, log_hoch, log_mittel

# Standard-Log
log_event('entity_type', entity_id, 'aktion', 'Beschreibung der Aktion')

# Mit Priorität
log_hoch('kunde', kunde_id, 'user_erstellt', f'User {email} für Kunde erstellt')
```

### Hilfe-Button (i)

Jedes Modul hat oben rechts einen Hilfe-Button für Enduser-Dokumentation:

```html
<button type="button" class="btn btn-sm btn-outline-info"
        data-bs-toggle="modal" data-bs-target="#helpModal">
    <i class="ti ti-info-circle"></i>
</button>
```

### DEV-Button (nur admin/mitarbeiter)

Jedes Modul hat oben rechts einen DEV-Button für Entwickler:

- Zeigt das PRD-Dokument aus Entwicklersicht
- Ermöglicht ggf. Bearbeitung des PRD (V2)

```html
{% if current_user.rolle.name in ['admin', 'mitarbeiter'] %}
<a href="{{ url_for('admin.prd_view', module='dialog') }}"
   class="btn btn-sm btn-outline-secondary">
    <i class="ti ti-code"></i> DEV
</a>
{% endif %}
```

### Hilfetexte-System

Hilfetexte werden in der `help_text` Tabelle gespeichert mit:

- **Schlüssel:** Format `bereich.seite.element` (z.B. `kunden.detail.stammdaten`)
- **Inhalt:** Markdown-formatierter Text
- **Anzeige:** (i)-Icons in Card-Headern mit Popover/Modal

```html
{% set help = get_help_text('kunden.detail.stammdaten') %}
{% if help %}
<button type="button" class="btn btn-sm btn-link text-muted"
        data-bs-toggle="popover" data-bs-content="{{ help.inhalt_markdown | markdown }}">
    <i class="ti ti-info-circle"></i>
</button>
{% endif %}
```

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
