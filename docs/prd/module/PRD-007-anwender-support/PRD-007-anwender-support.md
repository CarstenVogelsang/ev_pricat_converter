# PRD-007: Anwender-Support (Ticket-System)

> **Status:** In Entwicklung
> **Version:** 1.0
> **Erstellt:** 2025-12-27
> **Priorität:** Hoch

---

## 1. Übersicht

### 1.1 Ziel

Ein integriertes Support-Ticket-System, das Benutzern ermöglicht, direkt aus der Anwendung Support-Anfragen zu stellen. Das System integriert sich nahtlos mit dem bestehenden Hilfesystem - überall wo ein Hilfe-Icon (i) existiert, kann auch eine Support-Anfrage gestellt werden.

### 1.2 Zielgruppen

| Rolle | Nutzung |
|-------|---------|
| **Kunde** | Tickets erstellen, eigene Tickets einsehen, auf Rückfragen antworten |
| **Mitarbeiter** | Tickets bearbeiten, beantworten, Status ändern |
| **Admin** | Zusätzlich: Teams verwalten, Mitglieder zuweisen |

### 1.3 Kernfunktionen (MVP)

1. **Ticket erstellen** - User kann Anfrage mit Typ, Titel, Beschreibung erstellen
2. **Kontext-Erfassung** - Modul, Hilfetext-Schlüssel, URL werden automatisch erfasst
3. **Ticket-Übersicht** - User sieht eigene Tickets mit Status
4. **Ticket-Detail** - Kommunikationsverlauf mit Kommentaren
5. **Admin-Dashboard** - Alle Tickets mit Filter und Bearbeitungsfunktionen
6. **E-Mail-Benachrichtigung** - Team wird bei neuem Ticket informiert

---

## 2. Datenmodell

### 2.1 Entitäten-Diagramm

```
┌─────────────────┐     ┌─────────────────────┐     ┌─────────────┐
│  SupportTeam    │────<│ SupportTeamMitglied │>────│    User     │
├─────────────────┤     └─────────────────────┘     └─────────────┘
│ id              │                                        │
│ name            │     ┌─────────────────────┐            │
│ beschreibung    │     │  SupportTeamModul   │            │
│ email           │────<│  (V2 - Team/Modul)  │>────┐      │
│ aktiv           │     └─────────────────────┘     │      │
└────────┬────────┘                                 │      │
         │                                    ┌─────┴──────┤
         │                                    │   Modul    │
         │                                    └────────────┘
         │
         │     ┌─────────────────────────────────────────────────┐
         └────>│              SupportTicket                      │
               ├─────────────────────────────────────────────────┤
               │ id, nummer (T-2025-00042)                       │
               │ titel, beschreibung                             │
               │ typ, status, prioritaet                         │
               │ modul_id, hilfetext_schluessel, seiten_url      │
               │ erstellt_von_id, team_id, bearbeiter_id         │
               │ kunde_id, timestamps                            │
               └───────────────────┬─────────────────────────────┘
                                   │
                                   │     ┌─────────────────────┐
                                   └────>│  TicketKommentar    │
                                         ├─────────────────────┤
                                         │ id, ticket_id       │
                                         │ user_id, inhalt     │
                                         │ ist_intern          │
                                         │ ist_status_aenderung│
                                         └─────────────────────┘
```

### 2.2 Ticket-Typen (TicketTyp Enum)

| Code | Label | Icon | Beschreibung |
|------|-------|------|--------------|
| `frage` | Frage | ti-help | Allgemeine Frage zur Nutzung |
| `verbesserung` | Verbesserungsvorschlag | ti-bulb | Vorschlag für neue Funktion |
| `bug` | Fehlermeldung | ti-bug | Fehler/Problem melden |
| `schulung` | Schulungsanfrage | ti-school | Schulungsbedarf |
| `daten` | Datenkorrektur | ti-database-edit | Datenänderung benötigt |
| `sonstiges` | Sonstiges | ti-dots | Alles andere |

### 2.3 Ticket-Status (TicketStatus Enum)

| Code | Label | Farbe | Beschreibung |
|------|-------|-------|--------------|
| `offen` | Offen | warning | Neu erstellt, noch nicht bearbeitet |
| `in_bearbeitung` | In Bearbeitung | info | Mitarbeiter arbeitet daran |
| `warte_auf_kunde` | Warte auf Kunde | secondary | Rückfrage an Ersteller |
| `geloest` | Gelöst | success | Problem behoben |
| `geschlossen` | Geschlossen | dark | Endgültig abgeschlossen |

### 2.4 Ticket-Priorität (TicketPrioritaet Enum)

| Code | Label | Farbe |
|------|-------|-------|
| `niedrig` | Niedrig | secondary |
| `normal` | Normal | primary |
| `hoch` | Hoch | warning |
| `kritisch` | Kritisch | danger |

---

## 3. User Interface

### 3.1 User-Frontend

#### 3.1.1 Meine Tickets (`/support/`)

- Tabelle mit eigenen Tickets
- Spalten: Nummer, Titel, Typ, Status, Erstellt am, Letzte Aktivität
- Filter: Status (Offen/Alle), Typ
- Sortierung: Neueste zuerst
- Button: "Neue Anfrage"

#### 3.1.2 Ticket erstellen (`/support/neu`)

**Formular:**
- Typ (Dropdown)
- Betreff (Textfeld, max 200 Zeichen)
- Beschreibung (Textarea mit Markdown-Unterstützung)
- Kontext-Info (readonly): Modul, Seite (falls von Help-Icon)

#### 3.1.3 Ticket-Detail (`/support/<nummer>`)

- Header: Nummer, Titel, Status-Badge, Typ-Badge
- Metadaten: Erstellt am, Letzte Änderung, Bearbeiter (falls zugewiesen)
- Beschreibung (Markdown gerendert)
- Kommentar-Timeline (chronologisch)
- Kommentar-Formular (nur wenn nicht geschlossen)

### 3.2 Admin-Frontend

#### 3.2.1 Support-Dashboard (`/admin/support/`)

- Statistik-Karten: Offene Tickets, In Bearbeitung, Heute neu
- Ticket-Tabelle mit erweiterten Filtern:
  - Status, Typ, Priorität
  - Modul, Team, Bearbeiter
  - Zeitraum
- Quick-Actions: Status ändern, Zuweisen

#### 3.2.2 Ticket bearbeiten (`/admin/support/ticket/<nummer>`)

- Alle User-Ansicht-Felder plus:
- Status ändern (Dropdown)
- Priorität ändern
- Bearbeiter zuweisen
- Interne Notizen (nur für Team sichtbar)

#### 3.2.3 Team-Verwaltung (`/admin/support/teams`)

- Liste aller Teams
- Team erstellen/bearbeiten
- Mitglieder hinzufügen/entfernen
- Teamleiter festlegen
- Benachrichtigungen aktivieren/deaktivieren

### 3.3 Help-Icon Integration

Das bestehende `help_icon` Macro wird erweitert. Neben dem Info-Icon (i) erscheint ein Support-Icon (Headset):

```
[i] [🎧]  ← Info + Support nebeneinander
```

Klick auf Support-Icon öffnet das globale Support-Modal mit vorausgefülltem Kontext.

---

## 4. E-Mail-Benachrichtigungen

### 4.1 MVP: Neues Ticket (`support_ticket_neu`)

**Trigger:** Neues Ticket erstellt
**Empfänger:** Team-Mitglieder mit `benachrichtigung_aktiv=True`
**Betreff:** `Neues Ticket {{ ticket_nummer }}: {{ ticket_titel }}`

**Platzhalter:**
- `{{ ticket_nummer }}` - z.B. "T-2025-00042"
- `{{ ticket_titel }}` - Betreff
- `{{ ticket_typ }}` - "Frage", "Fehlermeldung", etc.
- `{{ ticket_prioritaet }}` - "Normal", "Hoch", etc.
- `{{ ersteller_name }}` - Name des Erstellers
- `{{ modul_name }}` - Modul-Name (falls vorhanden)
- `{{ link }}` - Direkt-Link zum Ticket

### 4.2 V2: Status-Änderung (`support_ticket_status`)

**Trigger:** Status geändert
**Empfänger:** Ticket-Ersteller

### 4.3 V2: Neue Antwort (`support_ticket_antwort`)

**Trigger:** Neuer Kommentar (nicht intern)
**Empfänger:** Ticket-Ersteller (bei Antwort vom Team) bzw. Team (bei Antwort vom User)

---

## 5. Berechtigungen

### 5.1 Modul-Zugriff

| Rolle | Zugriff |
|-------|---------|
| Admin | ✅ Voll (User + Admin) |
| Mitarbeiter | ✅ Voll (User + Admin) |
| Kunde | ✅ Nur User-Frontend |

### 5.2 Ticket-Sichtbarkeit

| Rolle | Sieht |
|-------|-------|
| Kunde | Nur eigene Tickets |
| Mitarbeiter | Alle Tickets |
| Admin | Alle Tickets |

### 5.3 Kommentar-Sichtbarkeit

| Kommentar-Typ | Kunde | Mitarbeiter/Admin |
|---------------|-------|-------------------|
| Öffentlich | ✅ | ✅ |
| Intern (`ist_intern=True`) | ❌ | ✅ |

---

## 6. Audit-Logging

Folgende Aktionen werden im AuditLog erfasst:

| Aktion | Wichtigkeit | Details |
|--------|-------------|---------|
| `ticket_erstellt` | mittel | Ticket-Nummer, Typ, Modul |
| `ticket_status_geaendert` | mittel | Alter Status → Neuer Status |
| `ticket_zugewiesen` | niedrig | Bearbeiter-Name |
| `ticket_kommentar` | niedrig | Öffentlich/Intern |
| `team_erstellt` | mittel | Team-Name |
| `team_mitglied_hinzugefuegt` | niedrig | User-Name, Team-Name |

---

## 7. Technische Details

### 7.1 Ticket-Nummern-Format

Format: `T-YYYY-NNNNN`

- `T` - Prefix für "Ticket"
- `YYYY` - Jahr
- `NNNNN` - Laufende Nummer (5-stellig, mit führenden Nullen)

Beispiel: `T-2025-00042`

### 7.2 Kontext-Erfassung

Beim Erstellen eines Tickets werden automatisch erfasst:

| Feld | Quelle | Beispiel |
|------|--------|----------|
| `modul_id` | URL-Pfad (`/dialog/...` → Modul "dialog") | 5 |
| `hilfetext_schluessel` | Data-Attribut vom Help-Icon | `dialog.detail.fragen` |
| `seiten_url` | `window.location.href` | `/dialog/fragebogen/3` |
| `kunde_id` | `current_user.kunde_id` (falls Kunde) | 2 |

### 7.3 Markdown-Unterstützung

Beschreibungen und Kommentare unterstützen Markdown:
- Überschriften, Listen, Fett/Kursiv
- Code-Blöcke (mit Syntax-Highlighting)
- Links

Rendering erfolgt mit dem bestehenden `markdown` Template-Filter.

---

## 8. Roadmap

### 8.1 MVP (Phase 1) - Aktuell

- [x] Datenmodelle (SupportTeam, SupportTicket, TicketKommentar)
- [x] User-Frontend (Tickets erstellen, auflisten, Details)
- [x] Admin-Dashboard (alle Tickets, Filter, Bearbeitung)
- [x] Kommentare (öffentlich + intern)
- [x] Status-Workflow
- [x] Ein Default-Team
- [x] E-Mail bei neuem Ticket
- [x] Help-Icon Integration

### 8.2 V2 - Team-Management

- [ ] SupportTeamModul (Team pro Modul)
- [ ] Automatische Team-Zuweisung basierend auf Modul
- [ ] Mehrere Teams verwalten
- [ ] E-Mail bei Status-Änderung
- [ ] E-Mail bei neuer Antwort

### 8.3 V3+ - Erweiterte Features

- [ ] **Datei-Anhänge** - Screenshots, PDFs hochladen
- [ ] **SLA-Tracking** - Reaktionszeit, Lösungszeit messen
- [ ] **Prioritäts-Eskalation** - Automatisch bei Verzögerung
- [ ] **Ticket-Tags/Labels** - Zusätzliche Kategorisierung
- [ ] **Ticket-Vorlagen** - Vorgefertigte Antworten (Canned Responses)
- [ ] **Wissensdatenbank** - Häufige Fragen → HelpText verknüpfen
- [ ] **Kundenzufriedenheit** - Umfrage nach Ticket-Abschluss
- [ ] **Reporting-Dashboard** - Statistiken, Trends, Auslastung

---

## 9. Abhängigkeiten

### 9.1 Bestehende Module

| Modul | Verwendung |
|-------|------------|
| **E-Mail Service** | `BrevoService.send_with_template()` für Benachrichtigungen |
| **Hilfesystem** | Integration mit `help_icon` Macro |
| **Audit-Logging** | `log_event()` für wichtige Aktionen |
| **User/Rolle** | Berechtigungsprüfung |

### 9.2 Neue E-Mail-Templates

| Schlüssel | Name | Beschreibung |
|-----------|------|--------------|
| `support_ticket_neu` | Neues Support-Ticket | An Team bei neuem Ticket |
| `support_ticket_status` | Status-Update (V2) | An User bei Status-Änderung |
| `support_ticket_antwort` | Neue Antwort (V2) | Bei neuen Kommentaren |

---

## 10. Offene Fragen

| Frage | Status | Antwort |
|-------|--------|---------|
| Sollen Tickets auch per E-Mail erstellt werden können? | Offen | Für V3 vorgemerkt |
| Maximale Dateigröße für Anhänge? | Offen | Erst in V3 relevant |
| SLA-Zeitfenster (Arbeitstage vs. Kalendertage)? | Offen | Erst in V3 relevant |

---

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)
