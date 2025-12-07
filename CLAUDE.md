# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**pricat-converter** converts VEDES PRICAT files (supplier product data) to Elena import format for e-vendo systems.

```
VEDES FTP (PRICAT CSV) → pricat-converter → Target FTP (Elena CSV + Images) → Elena Import (getData.php)
```

## Commands

### Development Setup (uv)
```bash
uv sync                # Install dependencies from pyproject.toml
```

### Run Application
```bash
uv run python run.py   # Development server at http://localhost:5000
uv run gunicorn -w 4 -b 0.0.0.0:5000 'app:create_app()'  # Production
```

### Database
```bash
uv run flask db init          # Initialize migrations (first time)
uv run flask db migrate       # Create migration
uv run flask db upgrade       # Apply migrations
uv run flask init-db          # Create tables directly
uv run flask seed             # Insert test data (LEGO supplier)
```

## Architecture

### Tech Stack
- Python 3.11+ / Flask / SQLAlchemy / SQLite
- **uv** for dependency management (pyproject.toml + uv.lock)
- Jinja2 + Bootstrap 5 (Frontend)
- httpx/aiohttp (async image downloads)
- openpyxl (Excel export)
- gunicorn (Production Server)
- **UI-Feedback: Bootstrap Toasts** (keine Alert-Boxen im Seiteninhalt - siehe PRD 11.1)

### Data Flow
1. Download PRICAT from VEDES FTP
2. Parse CSV → extract Lieferant/Hersteller/Marken → save to DB
3. Download images (async, parallel)
4. Generate Elena CSV + XLSX
5. Upload to target FTP
6. Trigger Elena import via HTTP GET

### Database Models
- **Lieferant** (Supplier): gln, vedes_id, kurzbezeichnung, aktiv, ftp_pfad_quelle/ziel, elena_startdir/base_url
- **Hersteller** (Manufacturer): gln, vedes_id, kurzbezeichnung
- **Marke** (Brand): kurzbezeichnung, gln_evendo (format: `{Hersteller.GLN}_{nr}`), hersteller_id FK
- **Config**: key-value store for FTP credentials, settings

## PRICAT Format

- **Delimiter**: Semicolon (`;`)
- **Encoding**: Latin-1 or UTF-8 (check before parsing)
- **Header row**: Starts with `H;PRICAT;...`
- **Data rows**: Start with `P;PRICAT;...`
- **143 columns total**

### Key Column Indices (0-based)
```python
PRICAT_COLUMNS = {
    'record_type': 0,           # H/P
    'vedes_artikelnummer': 5,
    'ean': 9,
    'artikelbezeichnung': 12,
    'lieferant_gln': 25,
    'lieferant_id': 26,
    'lieferant_name': 27,
    'hersteller_gln': 29,
    'hersteller_id': 30,
    'hersteller_name': 31,
    'hersteller_artikelnr': 32,
    'uvpe': 33,
    'gnp_lieferant': 34,
    'mwst': 38,
    'marke_text': 51,
    'gewicht': 63,
    'bilderlink': 94,
    'grunddatentext': 96,
    'warnhinweise': 99,
}
```



## Documentation

- `docs/PRD_Software-Architektur.md` - Full architecture, DB schema, component specs
- `docs/PRD_POC.md` - MVP scope, user stories, UI mockups
- `docs/beispiel_mapping.php` - Elena field mapping reference
- `docs/musterlieferant_stammdaten.csv` - Example Elena CSV output
- `docs/IMPLEMENTATION_PLAN.md` - **Implementierungsplan für neue Features** (im Plan-Modus verwenden!)

## Implementation Status (POC)

### Phase 1: Foundation (Done)
- [x] Project structure
- [x] Flask App Factory
- [x] SQLAlchemy Models
- [x] Basic routes and templates
- [x] DB seed command

### Phase 2: Core Services (Done)
- [x] `pricat_parser.py` - PRICAT CSV parsing
- [x] `elena_exporter.py` - Elena CSV generation
- [x] `image_downloader.py` - Async image download
- [x] `xlsx_exporter.py` - Entity XLSX export

### Phase 3: FTP & Import (Done)
- [x] `ftp_service.py` - VEDES download, target upload
- [x] `import_trigger.py` - HTTP GET to getData.php

### Phase 4: Integration (Done)
- [x] End-to-end processing flow (`processor.py`)
- [x] Progress tracking in UI (status.html, downloads.html)
