# ev247 Roadmap

Multi-Tool-Plattform für e-vendo Mitarbeiter und Kunden.

## Globale Platform-Tasks

| # | Task | Status | Beschreibung |
|---|------|--------|--------------|
| G1 | Branding & Landing Page | ✅ Fertig | Logo, Farben, Copyright, öffentliche Startseite |
| G2 | Hauptmenü mit Rollen | ⏳ Offen | Menü-Sichtbarkeit nach Rolle |
| G3 | Rolle umbenennen | ⏳ Offen | sachbearbeiter → mitarbeiter |
| G4 | Rolle hinzufügen | ⏳ Offen | Neue Rolle: kunde |
| G5 | Kunde-Model | ⏳ Offen | Kunde-Entity mit User-Zuordnung |
| G6 | Repo umbenennen | ⏳ Offen | ev_pricat_converter → ev247 |

**Letztes Update:** 2025-12-06

---

## Rollen-Konzept

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
| PRICAT Converter | ✓ | ✓ | ✗ |
| Lieferanten-Auswahl | ✓ | ✓ | ✓ |
| Content Generator | ✓ | ✓ | ✓ |
| Admin | ✓ | ✗ | ✗ |
| DB Admin | ✓ | ✗ | ✗ |

---

## Module

### Aktiv
- [PRICAT Converter](modules/pricat-converter.md) - VEDES PRICAT → Elena Import

### Geplant
- [Lieferanten-Auswahl](modules/lieferanten-auswahl.md) - Kunde wählt relevante Lieferanten
- [Content Generator](modules/content-generator.md) - KI-generierte Texte via OpenRouter

---

## Infrastruktur

### Aktuell implementiert
- Flask 3.x mit Blueprints
- SQLAlchemy (SQLite/PostgreSQL/MariaDB)
- Flask-Login Authentifizierung
- Flask-Admin für DB-Verwaltung
- Flask-Migrate für Schema-Migrationen
- S3-kompatibler Objektspeicher
- Coolify Deployment mit nixpacks

### Geplant
- OpenRouter API Integration (für Content Generator)
- Kunde-Lieferant Zuordnung (n:m)
