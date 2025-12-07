# PRD MVP

## Projekt evp247.de

**Version:** 1.0  
**Datum:** 04.12.2025  
**Status:** Draft

---

## 1. Zielsetzung


Multi-Tool-Plattform für e-vendo Mitarbeiter und Kunden.

## Globale Plattform-Aufgaben

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
| PRICAT Konverter | ✓ | ✓ | ✗ |
| Lead- & Kundenreport | ✓ | ✓ | ✓ |
| Lieferanten-Verwaltung | ✓ | ✓ | ✓ |
| Content Generator | ✓ | ✓ | ✓ |
| Admin | ✓ | ✗ | ✗ |
| DB Admin | ✓ | ✗ | ✗ |

---

## Module

### Aktiv
- [001 PRICAT Converter](module/PRD-001-pricat-converter/PRD-001-pricat-converter.md) - VEDES PRICAT → Elena Import
- [002 Lead und Kundenreport](module/PRD-002-lead-kundenreport/PRD-002-lead-kundenreport.md) - Lead- & Kundenreport Generierung, Verwaltung und Versand

### Geplant
- [003 Kunde Lieferanten-Verwaltung](module/PRD-003-kunde-hat-lieferanten/PRD-003-kunde-hat-lieferanten.md) - Kunden-Lieferanten-Verwaltung: Kunde wählt relevante Lieferanten, e-vendo Mitarbeiter verwalten Zuordnung
- [004 Content Generator](module/PRD-004-content-generator/PRD-004-content-generator.md) - KI-generierte Texte für den Kunden-Online-Shopvia OpenRouter

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


