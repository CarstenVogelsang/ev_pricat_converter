# Roadmap V2: PRD-Management in Datenbank

**Status:** Geplant (nach MVP)
**Erstellt:** 2025-12-16
**Priorität:** Mittel

---

## Übersicht

Erweiterung des Modulsystems um ein integriertes PRD-Management mit Feature-Status-Tracking und Browser-basierter Bearbeitung.

### Aktueller Stand (V1 - MVP)

PRD-Dokumente werden derzeit als Markdown-Dateien verwaltet:

- **Speicherort:** `docs/prd/module/PRD-XXX-name/`
- **Vorteile:** Git-versioniert, diff-freundlich
- **Nachteile:** Keine dynamische Status-Anzeige, kein Browser-Editing

---

## Ziel V2

Hybride Lösung: PRD-Dateien bleiben in Git, aber Feature-Status wird in der Datenbank geführt.

---

## Konzept

### 1. Neue DB-Tabelle `feature_status`

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `id` | Integer | Primärschlüssel |
| `modul_id` | FK | Referenz auf `modul` |
| `feature_key` | String | Eindeutiger Key (z.B. `fragebogen.auswertung`) |
| `titel` | String | Kurzer Titel des Features |
| `status` | Enum | GEPLANT, IN_ARBEIT, IMPLEMENTIERT, DEPRECATED |
| `prd_section` | String | Verweis auf PRD-Abschnitt (optional) |
| `implementiert_am` | Date | Wann implementiert |
| `notizen` | Text | Freitext für Entwickler |

### 2. Admin-UI unter `/admin/module/<code>/features`

- Übersicht aller Features eines Moduls mit Status
- Status-Toggle (Dropdown)
- Notizen bearbeiten
- Link zum PRD-Abschnitt

### 3. DEV-Button Integration

Der DEV-Button in jedem Modul zeigt:

- PRD-Inhalt (Markdown gerendert)
- Feature-Status aus DB (dynamisch)
- Ampel-Anzeige für Implementierungsfortschritt

### 4. Export-Funktion

- Generiere CHANGELOG.md aus Feature-Status-Änderungen
- Zeitraum wählbar (letzter Sprint, Monat, etc.)

---

## Vorteile

| Aspekt | V1 (nur Files) | V2 (Hybrid) |
|--------|----------------|-------------|
| Versionierung | Git | Git (PRDs) + DB (Status) |
| Status-Tracking | Manuell in MD | Automatisch in DB |
| Browser-Editing | Nein | Ja (Notizen, Status) |
| Export | Manuell | Automatisch |
| DEV-Ansicht | Statisch | Dynamisch |

---

## Implementierungsschritte

### Phase 1: Datenmodell

1. Model `FeatureStatus` erstellen
2. Migration ausführen
3. Seed für existierende Module

### Phase 2: Admin-UI

1. Route `/admin/module/<code>/features`
2. Template mit Feature-Liste
3. AJAX-Status-Toggle

### Phase 3: DEV-Button

1. Route `/admin/prd/<module_code>`
2. PRD-Datei lesen und rendern
3. Feature-Status einblenden

### Phase 4: Export

1. Export-Button in Admin
2. Zeitraum-Auswahl
3. Markdown-CHANGELOG generieren

---

## Betroffene Dateien (geplant)

| Datei | Änderung |
|-------|----------|
| `app/models/feature_status.py` | Neues Model |
| `app/routes/admin.py` | Feature-Verwaltung Routes |
| `app/templates/administration/module_features.html` | Neues Template |
| `app/templates/administration/prd_view.html` | PRD-Ansicht |
| `app/templates/components/dev_button.html` | Wiederverwendbare Komponente |

---

## Startbedingung

> **Dieses Feature wird durch explizite Nachfrage gestartet, nachdem PRD-006 abgeschlossen ist.**

Nicht automatisch implementieren - erst nach Diskussion mit dem User!
