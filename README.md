# pricat-converter

Web-Tool zur Konvertierung von VEDES PRICAT-Dateien (Lieferanten-Artikelstammdaten) in das Elena-Import-Format für e-vendo Systeme.

```
VEDES FTP (PRICAT CSV) → pricat-converter → Ziel-FTP (Elena CSV + Bilder) → Elena Import
```

## Tech-Stack

- Python 3.11+ / Flask / SQLAlchemy / SQLite
- uv (Dependency Management)
- gunicorn (Production Server)
- Bootstrap 5 (Frontend)

## Lokale Entwicklung

### Voraussetzungen

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

### Installation

```bash
# Repository klonen
git clone git@github.com:CarstenVogelsang/ev_pricat_converter.git
cd ev_pricat_converter

# Dependencies installieren
uv sync

# Datenbank initialisieren
uv run flask init-db

# Seed-Befehle (3-Stufen-System)
uv run flask seed-essential    # Rollen + Admin-User (PFLICHT)
uv run flask seed-stammdaten   # Branchen, Verbände, Hilfetexte
uv run flask seed-demo         # Test-Daten (nur Entwicklung)
```

### Server starten

```bash
# Development Server (mit Auto-Reload)
uv run python run.py
# → http://localhost:5000

# Production Server (lokal)
uv run gunicorn -w 4 -b 0.0.0.0:5000 'app:create_app()'
```

### Standard-Benutzer

| E-Mail | Passwort | Rolle |
|--------|----------|-------|
| carsten.vogelsang@e-vendo.de | admin123 | Admin |
| rainer.raschka@e-vendo.de | user123 | Sachbearbeiter |

## Deployment auf Coolify

Das Projekt ist für [Coolify](https://coolify.io/) mit Nixpacks vorbereitet.

### Schritte

1. **Neue Anwendung** in Coolify erstellen
2. **GitHub** als Quelle auswählen
3. Repository verbinden: `CarstenVogelsang/ev_pricat_converter`
4. Coolify erkennt automatisch:
   - Nixpacks als Build-System (via `nixpacks.toml`)
   - Port 3000 (Coolify-Standard)
5. **Deploy** klicken

### Was beim Start passiert

```bash
uv run flask init-db    # Datenbank-Tabellen erstellen
uv run flask seed       # Testdaten einfügen
uv run gunicorn ...     # Server auf Port 3000 starten
```

### Persistente Daten

Die SQLite-Datenbank liegt im Container unter `/app/instance/pricat.db`. Für persistente Daten:

1. In Coolify → Storage → Volume hinzufügen
2. Mount Path: `/app/instance`
3. Redeploy

## Datenbank-Befehle

```bash
uv run flask init-db           # Tabellen erstellen
uv run flask seed-essential    # Rollen + Admin-User (PFLICHT)
uv run flask seed-stammdaten   # Stammdaten (Branchen, Verbände, etc.)
uv run flask seed-demo         # Demo-Daten (nur Entwicklung)
uv run flask db migrate        # Migration erstellen
uv run flask db upgrade        # Migration anwenden
```

## Troubleshooting

### Port bereits belegt

```text
Address already in use
Port 5055 is in use by another program.
```

**Lösung:** Prozess auf Port direkt beenden (Einzeiler):

```bash
# Port 5055 freigeben (ändere die Portnummer nach Bedarf)
lsof -ti :5055 | xargs kill

# Alternative: Alle Python-Prozesse mit "run.py" beenden
pkill -f "python run.py"
```

<details>
<summary>Erklärung der Befehle</summary>

- `lsof` = **L**ist **O**pen **F**iles (zeigt welcher Prozess einen Port/Datei nutzt)
- `-t` = nur PID ausgeben (für Piping)
- `-i :PORT` = nach Netzwerk-Port filtern
- `xargs kill` = PID an `kill` weitergeben
- `pkill -f` = Prozesse nach Kommandozeilen-Pattern beenden

</details>

## Dokumentation

- `CLAUDE.md` - Entwickler-Dokumentation für Claude Code
- `docs/PRD_Software-Architektur.md` - Architektur, DB-Schema, Komponenten
- `docs/IMPLEMENTATION_PLAN.md` - Erledigte und geplante Tasks

## Lizenz

Proprietär - e-vendo AG
