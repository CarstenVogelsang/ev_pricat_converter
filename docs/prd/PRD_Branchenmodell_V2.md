Rolle & Ziel
Du bist ein KI-Codeagent in einem bestehenden Flask-POC.
Deine Aufgabe ist es, das bisherige, zu einfache Branchenmodell in eine neue 2-stufige Branchen-Taxonomie mit Rollen zu überführen, inklusive:

Anpassung der Datenbankmodelle (SQLAlchemy),

Erstellung von Migrationen,

Anpassung der Admin-UI (Branchen & Rollen verwalten),

Vorbereitung der späteren Nutzung im Branchenverzeichnis (Cityserver).

Schreibe deinen Plan und deinen Code so, dass ein menschlicher Entwickler ihn gut nachvollziehen kann. Bezeichner (Klassen, Felder, Variablen) und Kommentare sollen überwiegend deutschsprachig oder denglisch sein.

1. Kontext & Ist-Zustand
1.1 Technischer Rahmen

Backend: Flask

ORM: SQLAlchemy (ggf. mit Flask-SQLAlchemy)

Es gibt einen Admin-Bereich, in dem aktuell eine einfache Branchenverwaltung existiert:

Route in etwa /admin/branchen

Formular „Neue Branche“ (Name, Icon)

Rechts eine Liste vorhandener Branchen mit Status „Aktiv“ und Aktionen (Bearbeiten, Löschen, Sortierung).

1.2 Aktuelles Datenmodell (vereinfacht)

Tabelle / Modell Branche
Felder (aus der DB/GUI ersichtlich):

id (PK, integer)

name (z. B. „Einzelhandel Spielwaren“, „Einzelhandel Modellbahn“, „Einzelhandel Fahrrad“, „Einzelhandel Buchhandel“, „Einzelhandel (allgemein)“, „Großhandel (allgemein)“, „Hersteller IT Software“ …)

icon (Tabler Icon Name, z. B. „train“, „bike“, „book“, „building-store“)

aktiv (0/1)

sortierung (integer)

Tabelle / Modell KundeBranche (M2M zwischen Kunden und Branchen)
Felder:

id

kunde_id (FK auf Kunde) – Unternehmen heißen im POC „Kunde“ und sollen auch so heißen

branche_id (FK auf Branche)

ist_primaer (0/1 – Kennzeichnung „Hauptbranche des Kunden“)

Das Modell Kunde selbst bleibt unverändert (wichtig: nicht umbenennen).

Aktuell ist Branche flach – es gibt keine Hauptbranchen, keine Rollen.

2. Soll-Konzept / Zielbild

Wir möchten:

Eine hierarchische Branchenstruktur:

Ebene 1: Hauptbranche, z. B. HANDEL, HANDWERK, DIENSTLEISTUNG, …

Ebene 2: konkrete Branche innerhalb einer Hauptbranche, z. B.

HANDEL.Spielwaren

HANDEL.Modellbahn

HANDEL.Baby

HANDEL.Schreibwaren

Wichtig: Die Struktur soll nicht mehr „Einzelhandel Spielwaren“ im Namen enthalten, sondern durch Hauptbranche + Rolle abgebildet werden. Beispiel:

Hauptbranche: HANDEL

Branche: Spielwaren

Rollen: EINZELHANDEL_STATIONAER, EINZELHANDEL_ONLINE, EINZELHANDEL_OMNICHANNEL, FILIALIST, HERSTELLER, GROSSHANDEL (sofern sinnvoll).

Einen Rollen-Katalog für Branchenrollen:

Beispiele für Rollen-Codes:

HERSTELLER

GROSSHAENDLER

FILIALIST

EINZELHANDEL_STATIONAER

EINZELHANDEL_ONLINE

EINZELHANDEL_OMNICHANNEL

ggf. weitere später.

Ein Constraint-Modell „branche_branchenrolle“:

Nicht jede Rolle ist in jeder Branche sinnvoll.

Beispiel: In einer Branche „Steuerberatung“ wäre HERSTELLER Unsinn.

Es soll daher eine Tabelle/Relation geben, die festlegt, welche Rollen pro Branche zulässig sind.

Kunden-Zuordnung:

Ein Kunde kann mehreren Branchen angehören (z. B. HANDEL.Spielwaren und HANDEL.Schreibwaren).

Ein Kunde kann Rollen je Branche haben.
Beispiel:

Kunde X: Branche HANDEL.Spielwaren → Rollen [FILIALIST, EINZELHANDEL_OMNICHANNEL]

Bei der Auswahl von Rollen für einen Kunden dürfen nur Rollen zur Auswahl stehen, die in branche_branchenrolle als zulässig definiert sind.

3. Ziel-Datenmodell (SQLAlchemy)

Entwirf und implementiere folgende Modelle (Namen können leicht variieren, aber bitte deutschsprachig/denglisch):

Branche (erweitertes existierendes Modell)

id (PK)

parent_id (nullable FK auf Branche.id)

NULL → Hauptbranche (z. B. „HANDEL“)

!= NULL → Unterbranche / Kategorie innerhalb einer Hauptbranche (z. B. „Spielwaren“ mit parent_id = ID von „HANDEL“)

name

slug (für Pfade / URLs, kann später auch von Cityserver genutzt werden)

icon

aktiv

sortierung

BranchenRolle (neuer Rollen-Katalog)

id (PK)

code (z. B. EINZELHANDEL_ONLINE, eindeutig)

name (sprechendes Label, z. B. „Einzelhandel Online“)

beschreibung (optional)

aktiv (bool)

sortierung (int)

BrancheBranchenRolle (Zulässigkeitsmatrix)

id (PK)

branche_id (FK → Branche.id, in der Regel eine Unterbranche; theoretisch könnte man auch Rollen auf Hauptbranche erlauben)

branchenrolle_id (FK → BranchenRolle.id)

Unique-Constraint auf (branche_id, branchenrolle_id)

Semantik: „Diese Rolle darf in dieser Branche vergeben werden.“

KundeBranche (bestehendes Modell, anpassen falls nötig)

weiter wie bisher:

id

kunde_id (FK auf Kunde)

branche_id (FK auf Branche)

ist_primaer (bool)

Dieses Modell bleibt als M2M-Verknüpfung Kunde ↔ Branche erhalten.

KundeBranchenRolle (neues Modell für Rollen je Kunde & Branche)

id (PK)

kunde_id (FK → Kunde.id)

branche_id (FK → Branche.id)

branchenrolle_id (FK → BranchenRolle.id)

Optional: ist_primaer (bool), falls du eine Hauptrolle kennzeichnen möchtest.

Unique-Constraint auf (kunde_id, branche_id, branchenrolle_id)

Semantik: „Kunde X hat in Branche Y die Rolle Z.“

Stelle sicher, dass das Modell so gebaut ist, dass:

bei der Validierung/Business-Logik nur Rollen ausgewählt werden können, die in BrancheBranchenRolle für die jeweilige Branche freigeschaltet sind.

4. Migrations-Plan (Daten & Struktur)

Erstelle einen konkreten Plan und die zugehörigen Migrationsskripte (z. B. mit Alembic oder manuelle SQL-Skripte), die folgende Schritte abbilden:

Strukturmigration

Füge parent_id und slug zur bestehenden Tabelle branche hinzu.

Lege neue Tabellen an:

branchenrolle

branche_branchenrolle

kunde_branchenrolle

Achte auf Foreign-Keys, Indizes und Unique-Constraints.

Datenmigration – Hauptbranchen anlegen

Lege mindestens eine Hauptbranche HANDEL an (später können weitere wie DIENSTLEISTUNG, HANDWERK etc. folgen).

Weise den bereits vorhandenen Branchen aus dem POC vorerst der Hauptbranche HANDEL zu, indem du:

einen Datensatz Branche(name="HANDEL", parent_id=NULL, ...) anlegst.

für alle bestehenden Branchen parent_id auf die ID dieser Hauptbranche setzt.

Optional (wenn sinnvoll): Bereinige die Namen, z. B.:

aus „Einzelhandel Spielwaren“ → Unterbranche „Spielwaren“ mit parent_id = HANDEL

aus „Großhandel (allgemein)“ → geänderte Unterbranche „Großhandel (allgemein)“ bleibt unter HANDEL o. ä.

Datenmigration – Rollen initial befüllen

Lege einige typische Rollen in branchenrolle an:

HERSTELLER, GROSSHAENDLER, FILIALIST, EINZELHANDEL_STATIONAER, EINZELHANDEL_ONLINE, EINZELHANDEL_OMNICHANNEL.

Lege in branche_branchenrolle die zulässigen Kombinationen an:

z. B. für Unterbranchen wie Spielwaren/Modellbahn/Baby/Schreibwaren:

erlaube HERSTELLER, GROSSHAENDLER, FILIALIST, EINZELHANDEL_*.

für Branchen wie „Steuerberatung“ (wenn sie später kommen) würden HERSTELLER/GROSSHAENDLER nicht freigegeben.

Für bestehende Kunden musst du an dieser Stelle noch keine Rollen vergeben – das kann später manuell über die UI geschehen. Wichtig ist nur, dass der Mechanismus vorbereitet ist.

Legacy-Felder/Struktur

Entferne keine alten Spalten oder Logik, bevor die neue UI fertig ist.

Markiere im Code alte Pfade/Funktionen als „Legacy“, falls sie nach der Migration nicht mehr benutzt werden sollen.

5. UI-Anpassungen (Admin-Oberfläche)

Passe die Admin-UI so an, dass folgende Verwaltungsfunktionen zur Verfügung stehen:

Hauptbranchen verwalten

Ansicht: Liste aller Branchen mit parent_id IS NULL (Hauptbranchen).

Funktionen:

Anlegen neuer Hauptbranchen (Name, Icon, Sortierung, aktiv).

Bearbeiten/Löschen von Hauptbranchen (nur möglich, wenn keine oder nur kontrolliert abhängige Unterbranchen existieren).

Unterbranchen (Kategorien) je Hauptbranche verwalten

Bei Klick auf eine Hauptbranche:

Anzeige der zugehörigen Unterbranchen (parent_id = <Hauptbranche.id>).

Möglichkeit, neue Unterbranchen anzulegen (Name, Icon, Sortierung, aktiv).

Bearbeiten/Löschen/Sortieren wie bisher.

Optional: In der bestehenden „Branchen verwalten“-Maske kannst du links die Hauptbranchen, rechts die Unterbranchen derselben Hauptbranche anzeigen (Master-Detail).

Branchenrollen verwalten

Eigene Admin-Seite für BranchenRolle:

Liste aller Rollen (Code, Name, aktiv, Sortierung).

Anlegen/Bearbeiten/Löschen.

Zulässige Rollen je Branche verwalten (BrancheBranchenRolle)

In der Bearbeitungsmaske einer Unterbranche:

Multi-Select-Feld mit allen verfügbaren Rollen.

Speichern in branche_branchenrolle.

Darstellung in der Liste (z. B. kleine Badges „Hersteller“, „Einzelhandel Online“ …), damit man schnell sieht, welche Rollen für eine Branche erlaubt sind.

Kunden-UI (nur vorbereiten / minimal anpassen)

(Optional, falls bereits ein Kunden-Admin existiert:)

ermögliche beim Bearbeiten eines Kunden:

Auswahl einer oder mehrerer Branchen (kunde_branche), inkl. Kennzeichnung der primären Branche.

Auswahl von Rollen pro Branche:

Nach Auswahl einer Branche sollen nur die Rollen angeboten werden, die in branche_branchenrolle für diese Branche freigegeben sind.

Implementiere vorerst eine einfache Lösung, z. B.:

Liste der Branchen mit Checkboxen,

pro aktivierter Branche ein Multi-Select für Rollen.

6. Validierungen & Business-Logik

Implementiere (im Modell oder in Formular-/Service-Logik):

Beim Anlegen/Ändern eines Eintrags in KundeBranchenRolle:

Prüfe, ob es einen Eintrag in BrancheBranchenRolle für (branche_id, branchenrolle_id) gibt.

Wenn nicht, verhindere das Speichern und gib eine klare Fehlermeldung aus (z. B. „Diese Rolle ist für die ausgewählte Branche nicht zulässig“).

Stelle sicher, dass:

kunde_id + branche_id in KundeBranche vorhanden ist, bevor Rollen für diese Kombination angelegt werden (oder lege sie automatisch an).

ist_primaer für KundeBranche pro Kunde höchstens einmal auf True gesetzt ist (optional: DB-Constraint oder Logik).

7. Vorgehensweise & Output

Arbeite in folgenden Schritten und zeige nach jedem Schritt deinen Code:

Analyse & kurzer Plan

Fasse in wenigen Stichpunkten zusammen, welche Dateien/Module im Projekt du anfassen wirst (z. B. models.py, admin_views.py, templates/admin/branchen.html, Migrations-Scripts).

Modelle & Migrationen

Implementiere/erweitere die SQLAlchemy-Modelle (Branche, BranchenRolle, BrancheBranchenRolle, KundeBranche, KundeBranchenRolle).

Schreibe die passenden Migrationsskripte und kommentiere auf Deutsch, was passiert.

Datenmigration

Implementiere die initiale Migration der vorhandenen Branchen in die neue 2-Stufen-Struktur (Hauptbranchen + Unterbranchen) und lege erste Rollen/Kombinationen an.

UI-Anpassung Branchen & Rollen

Passe die Admin-Templates und Routen so an, dass Hauptbranchen, Unterbranchen, Rollen und branche_branchenrolle verwaltbar sind.

(Optional) Kunden-UI

Ergänze mindestens eine einfache Maske, um für einen Kunden seine Branchen und Rollen zu pflegen, inklusive Filterung der Rollen nach Branche.

Tests & kurze Doku

Füge einfache Unit- oder Integrationstests hinzu (z. B. für das Anlegen von Branchen, Rollen, das Zuordnen von Rollen zu Branchen und Kunden).

Erstelle eine kurze Markdown-Datei (z. B. docs/branchenmodell.md), in der du:

das neue Modell erklärst,

die wichtigsten Tabellen auflistest,

und das Zusammenspiel Branche ↔ BranchenRolle ↔ BrancheBranchenRolle ↔ KundeBranche ↔ KundeBranchenRolle beschreibst.

Halte dich bei Benennungen an sprechende deutschsprachige Namen und schreibe ausführliche deutsche Kommentare, insbesondere bei Migrations- und Mapping-Logik.

---

## 8. Branchen-Import aus externen Quellen

### 8.1 Übersicht

Um Branchenkataloge aus externen Quellen (z.B. SaaS-Dienste wie unternehmensdaten.org) zu importieren, wird eine Import-Funktion bereitgestellt.

### 8.2 JSON-Format (unternehmensdaten.org Export)

Das Import-Format ist so gestaltet, als käme es von einem externen Branchenkatalog-Service:

```json
{
  "meta": {
    "source": "unternehmensdaten.org",
    "version": "1.0",
    "export_date": "2025-12-12T10:30:00Z",
    "type": "branchenkatalog"
  },
  "hauptbranche": {
    "uuid": "550e8400-e29b-41d4-a716-446655440000",
    "name": "HANDWERK",
    "slug": "handwerk",
    "icon": "fas fa-tools"
  },
  "unterbranchen": [
    {
      "uuid": "550e8400-e29b-41d4-a716-446655440001",
      "name": "Elektroinstallation",
      "slug": "elektroinstallation",
      "icon": "fas fa-bolt",
      "sortierung": 1,
      "rollen": ["hersteller", "grosshaendler", "einzelhandel_stationaer"]
    }
  ],
  "rollen_katalog": [
    {
      "uuid": "r-001",
      "code": "hersteller",
      "name": "Hersteller",
      "icon": "fas fa-industry",
      "beschreibung": "Produzierendes Unternehmen"
    }
  ]
}
```

### 8.3 Felder-Beschreibung

| Block | Feld | Beschreibung | Pflicht |
|-------|------|--------------|---------|
| meta | source | Quellsystem | Nein |
| meta | version | Format-Version | Nein |
| meta | export_date | Export-Zeitstempel (ISO 8601) | Nein |
| hauptbranche | uuid | Externe UUID für Upsert | Nein |
| hauptbranche | name | Name der Hauptbranche (z.B. "HANDWERK") | **Ja** |
| hauptbranche | slug | URL-Slug | Nein (wird generiert) |
| hauptbranche | icon | Icon (FontAwesome oder Tabler) | Nein (Default: folder) |
| unterbranchen[] | uuid | Externe UUID für Upsert | Nein |
| unterbranchen[] | name | Name der Unterbranche | **Ja** |
| unterbranchen[] | slug | URL-Slug | Nein (wird generiert) |
| unterbranchen[] | icon | Icon | Nein (Default: category) |
| unterbranchen[] | sortierung | Sortier-Reihenfolge | Nein (Index × 10) |
| unterbranchen[] | rollen | Array von Rollen-Codes | Nein |
| rollen_katalog[] | code | Eindeutiger Code (UPPER_CASE) | **Ja** (wenn Block vorhanden) |
| rollen_katalog[] | name | Anzeigename | Nein (Default: Code) |
| rollen_katalog[] | icon | Icon | Nein (Default: tag) |
| rollen_katalog[] | beschreibung | Beschreibungstext | Nein |

### 8.4 Upsert-Logik

Die Import-Funktion nutzt eine **Upsert-Strategie**:

1. **UUID vorhanden?** → Suche nach UUID
2. **UUID nicht gefunden?** → Suche nach Name (+ parent_id bei Unterbranchen)
3. **Gefunden?** → Update bestehenden Eintrag
4. **Nicht gefunden?** → Insert neuer Eintrag

### 8.5 Icon-Bereinigung

Icons werden automatisch bereinigt:

- `fas fa-bolt` → `bolt`
- `ti ti-tools` → `tools`
- `fa-building` → `building`

### 8.6 Admin-UI Integration

**Route:** `POST /admin/branchen/import`

**UI-Element:** Import-Button in der Branchen-Verwaltung mit Modal für Datei-Upload.

### 8.7 Testdatei

Eine Beispiel-Testdatei befindet sich unter:
`docs/testdaten/branchenkatalog_handwerk.json`

Diese enthält die Hauptbranche "HANDWERK" mit 8 typischen Unterbranchen.

---

## 9. Hauptbranche für Kunden (Hauptbranche-Zuordnung)

### 9.1 Übersicht

Bevor ein Kunde Unterbranchen zugeordnet bekommen kann, muss ihm eine **Hauptbranche** (Hauptbranche) zugewiesen werden. Dies stellt sicher, dass Kunden nur Unterbranchen aus ihrer relevanten Geschäftskategorie wählen können.

**Beispiel:**
- Citykauf ist ein Handelsunternehmen
- Zuerst wird Hauptbranche "HANDEL" gesetzt
- Danach können nur HANDEL-Unterbranchen (Spielwaren, Schreibwaren, etc.) zugeordnet werden

### 9.2 Datenmodell-Erweiterung

**Tabelle `kunde`** erhält neues Feld:

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `hauptbranche_id` | Integer (FK) | Referenz auf `branche.id` mit `parent_id=NULL` (Hauptbranche) |

```python
# app/models/kunde.py
hauptbranche_id = db.Column(db.Integer, db.ForeignKey('branche.id'), nullable=True)
hauptbranche = db.relationship('Branche', foreign_keys=[hauptbranche_id])
```

### 9.3 Validierungsregeln

1. **Nur Hauptbranchen erlaubt:** `hauptbranche_id` darf nur auf eine Branche mit `parent_id=NULL` zeigen
2. **Nullable:** Bestehende Kunden behalten NULL bis manuell gesetzt
3. **Unterbranche-Filter:** Wenn Hauptbranche gesetzt → nur Unterbranchen dieser Kategorie anzeigen

### 9.4 API Endpoint

**Route:** `POST /kunden/<id>/hauptbranche`

**Request Body:**
```json
{ "hauptbranche_id": 123 }  // Setzen
{ "hauptbranche_id": null }  // Entfernen
```

**Response:**
```json
{
  "success": true,
  "message": "Hauptbranche auf \"HANDEL\" gesetzt",
  "hauptbranche_id": 123,
  "hauptbranche_name": "HANDEL"
}
```

### 9.5 UI-Integration

**Kunden-Detail (`/kunden/<id>`):**

1. **Hauptbranche Card** (blau hervorgehoben):
   - Alle Hauptbranchen als Buttons
   - Aktive Hauptbranche visuell markiert
   - X-Button zum Entfernen (nur wenn gesetzt)
   - Hinweis wenn nicht gesetzt

2. **Unterbranchen Card:**
   - Ohne Hauptbranche: Hinweistext "Bitte erst Hauptbranche wählen"
   - Mit Hauptbranche: Nur Unterbranchen der gewählten Kategorie
   - Badge im Header zeigt aktive Hauptbranche

### 9.6 Akzeptanzkriterien (Phase 1)

- [x] Kunde.hauptbranche_id Feld vorhanden
- [x] Migration erstellt und angewandt
- [x] Nur Hauptbranchen (parent_id=NULL) als Hauptbranche erlaubt
- [x] UI zeigt Hauptbranche-Auswahl
- [x] Unterbranchen werden nach Hauptbranche gefiltert
- [x] Hinweis wenn keine Hauptbranche gesetzt

### 9.7 Hauptbranche ändern (Phase 2)

**Verhalten nach Auswahl:**

Sobald eine Hauptbranche gesetzt ist:
1. **Nur die gewählte Hauptbranche wird angezeigt** (andere werden ausgeblendet)
2. Neben der gewählten Hauptbranche erscheint ein **Löschen-Button** (Papierkorb-Icon)
3. Um eine andere Hauptbranche zu wählen, muss erst die aktuelle gelöscht werden
4. Der Workflow beginnt dann von vorne (alle Hauptbranchen zur Auswahl)

**Begründung:** Eine Änderung der Hauptbranche ist eine schwerwiegende Entscheidung, da sie die möglichen Unterbranchen grundlegend ändert. Das bewusste Löschen stellt sicher, dass Benutzer diese Konsequenz verstehen.

### 9.8 Lösch-Verhalten mit Kaskaden-Logik

**Kritische Aktion:** Das Löschen der Hauptbranche hat Auswirkungen auf verknüpfte Daten.

#### 9.8.1 Kaskaden-Löschung

Beim Entfernen der Hauptbranche werden automatisch gelöscht:
- Alle `KundeBranche`-Einträge des Kunden
- Alle `KundeBranchenRolle`-Einträge des Kunden

**Begründung:** Unterbranchen gehören zu einer Hauptbranche. Wird die Hauptbranche entfernt, wären die Unterbranche-Zuordnungen inkonsistent.

#### 9.8.2 Bestätigungs-Modal

Vor dem Löschen erscheint ein **modales Warndialog**:

```
┌─────────────────────────────────────────────────────┐
│ ⚠️ Hauptbranche entfernen                     [X]  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Beim Entfernen der Hauptbranche werden auch       │
│  X zugeordnete Unterbranchen gelöscht!             │
│                                                     │
│  Diese Aktion kann nicht rückgängig gemacht        │
│  werden.                                            │
│                                                     │
├─────────────────────────────────────────────────────┤
│           [Abbrechen]    [Trotzdem löschen]        │
└─────────────────────────────────────────────────────┘
```

**Inhalt:**
- Header: Rot/Danger-Styling mit Warnsymbol
- Body: Dynamische Anzahl der betroffenen Unterbranchen
- Footer: "Abbrechen" (primär) und "Trotzdem löschen" (danger)

#### 9.8.3 API Endpoint (DELETE)

**Route:** `DELETE /kunden/<id>/hauptbranche`

**Response (Erfolg):**
```json
{
  "success": true,
  "message": "Hauptbranche \"HANDEL\" und 5 Unterbranchen-Zuordnungen entfernt",
  "deleted_branches": 5,
  "deleted_roles": 12
}
```

**Backend-Ablauf:**
1. Zähle betroffene Einträge in `KundeBranche` und `KundeBranchenRolle`
2. Lösche alle `KundeBranchenRolle`-Einträge des Kunden
3. Lösche alle `KundeBranche`-Einträge des Kunden
4. Setze `kunde.hauptbranche_id = NULL`
5. **Logging:** Ereignis im Audit-Log dokumentieren
6. Commit und Response

### 9.9 Audit-Logging

Das Löschen einer Hauptbranche ist ein **mittelschweres Ereignis** und wird im Audit-Log dokumentiert.

**Log-Eintrag:**

| Feld | Wert |
|------|------|
| modul | `kunden` |
| aktion | `hauptbranche_geloescht` |
| wichtigkeit | `mittel` |
| entity_type | `Kunde` |
| entity_id | Kunde-ID |
| details | `Hauptbranche "HANDEL" und 5 Unterbranchen gelöscht` |

Siehe auch: [PRD_BASIS_LOGGING.md](PRD_BASIS_LOGGING.md) für das vollständige Logging-System.

### 9.10 Akzeptanzkriterien (Phase 2)

- [ ] Nach Hauptbranche-Auswahl: Nur gewählte wird angezeigt
- [ ] Löschen-Button neben aktiver Hauptbranche
- [ ] Modal-Warnung vor dem Löschen
- [ ] Dynamische Anzeige der betroffenen Unterbranche-Anzahl
- [ ] DELETE-Endpoint löscht Hauptbranche + alle Unterbranche-Zuordnungen + Rollen
- [ ] Löschung wird im Audit-Log dokumentiert
- [ ] Toast-Meldung nach erfolgreichem Löschen
