# Changelog - PRD-010 Schulungen

Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/).

---

## [Unreleased]

### Added

- **PRD-Dokument erstellt:** Vollständige Anforderungsdokumentation
  - Datenmodell mit 5 Entitäten (Schulung, Thema, Durchführung, Termin, Buchung)
  - Routes-Struktur für öffentlich, Kunden-Portal und Admin
  - iframe-Einbettungs-Konzept für e-vendo.de Integration
  - E-Mail-Templates definiert (7 Schlüssel)
  - Excel-Export-Format für ERP-Integration
  - Dateien: `docs/prd/module/PRD-010-schulungen/PRD-010-schulungen.md`

- **Entity-Dokumentation erstellt:** `docs/prd/core/entities/schulung.md`
  - Vollständiges Datenbankschema für alle 6 Tabellen
  - Beziehungsdiagramm (ASCII)
  - Properties & Methoden definiert
  - Status-Workflows dokumentiert

- **SQLAlchemy-Models implementiert:**
  - `app/models/schulungsthema.py` - Wiederverwendbare Themenblöcke
  - `app/models/schulung.py` - Kurs-Template mit M:N Junction zu Themen
  - `app/models/schulungsdurchfuehrung.py` - Konkrete Instanz mit Terminen
  - `app/models/schulungsbuchung.py` - Buchung mit Status-Workflow
  - Alle Models exportiert in `app/models/__init__.py`

- **Modul in Modulverwaltung registriert:**
  - Code: `schulungen`, Typ: `kundenprojekt`
  - Icon: `ti-school`, Farbe: `purple` (#6f42c1)
  - Berechtigungen für admin, mitarbeiter, kunde

- **Admin-Routes implementiert:** `app/routes/schulungen_admin.py`
  - Schulungen: Liste, Anlegen, Bearbeiten, Löschen
  - Themen: Liste, Anlegen, Bearbeiten
  - Durchführungen: Liste, Anlegen, Detail mit Teilnehmern
  - Buchungen: Liste, Freischalten, Stornieren
  - Excel-Export für ERP-Integration

- **Öffentliche Routes implementiert:** `app/routes/schulungen.py`
  - Liste: Alle aktiven Schulungen mit Suche
  - Detail: Schulungsinfos mit Themen und Terminen
  - iframe-Varianten: `/schulungen/embed` und `/schulungen/embed/<id>`
  - Kunden-Portal: Meine Schulungen, Buchen, Stornieren

- **Templates erstellt:**
  - Admin: 8 Templates in `app/templates/administration/schulungen/`
  - Öffentlich: 6 Templates in `app/templates/schulungen/`
  - iframe: Standalone-Templates mit eigenem CSS (Light/Dark Theme)

---

## Geplante Releases

### [1.0.0] - TBD

**MVP Release mit:**

- Schulungen + Themen CRUD
- Durchführungen + automatische Terminberechnung
- Öffentliche Liste/Detail + iframe-Variante
- Kunden-Buchung + Stornierung
- Admin: Buchungsübersicht, Warteliste, Excel-Export
- E-Mail: Buchungsbestätigung

### [1.1.0] - TBD

**Erweiterungen:**

- E-Mail-Erinnerung vor Schulungsstart
- Teams-Link automatisch versenden
- Kategorien/Tags für Schulungen

### [2.0.0] - TBD

**Erweiterte Features:**

- Teilnehmer-Feedback
- Zertifikate generieren
- Online-Zahlung
