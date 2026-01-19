# Changelog - PRD-013 Kunden-Mailing

Alle wichtigen Änderungen am Kunden-Mailing-Modul werden hier dokumentiert.

## [1.9.0] - 2026-01-15

### Added (Phase 5f: Test-Benutzer-System)

**Neuer KundeTyp: TESTKUNDE:**
- `KundeTyp.TESTKUNDE` für Test-Kunden, die nicht in normalen Listen erscheinen
- Property `is_testkunde` im Kunde-Model
- Alle Kunden-Queries filtern jetzt Test-Kunden automatisch aus

**Neue Rolle: test_benutzer:**
- Rolle für dedizierte Test-Benutzer (können sich nicht einloggen)
- Property `is_test_benutzer` im User-Model
- Test-Benutzer haben zugeordnete "Musterkunden" für Platzhalter-Auflösung

**CLI-Command: `flask seed-test-users`:**
- Erstellt 3 Test-Benutzer mit realistischen Musterkunden:
  - Max Mustermann → Mustermann GmbH
  - Erika Musterfrau → Musterfrau & Co. KG
  - Hans Testmann → Testmann IT Solutions
- Gmail-Aliase für Test-E-Mails: `carsten.vogelsang+testuser1@gmail.com` etc.

### Changed

**Einstellungen-UI überarbeitet:**
- E-Mail-Adressliste ersetzt durch Benutzer-Tabelle mit Checkboxen
- Zeigt Test-Benutzer (mit zugehörigem Musterkunden) und interne User
- Config-Key geändert: `mailing_test_empfaenger_ids` (JSON-Array von User-IDs)

**Vorschau-Seite:**
- Dropdown zeigt jetzt User mit Namen und Typ-Badge (Test/Admin/Mitarbeiter)
- Parameter geändert: `test_empfaenger_id` statt `test_email`

**Test-Versand mit echten Kundendaten:**
- Bei Test-Benutzern werden Platzhalter mit echten Kundendaten aufgelöst
- Bei internen Usern (ohne Kunde) werden weiterhin Beispieldaten verwendet
- Flash-Message informiert, welcher Modus verwendet wurde

### Technical Details

**Model-Erweiterungen:**
- `app/models/kunde.py`: `KundeTyp.TESTKUNDE`, `is_testkunde` Property
- `app/models/user.py`: `is_test_benutzer` Property

**Gefilterte Queries (Test-Kunden ausgeblendet):**
- `app/routes/kunden.py` (Zeile 62)
- `app/routes/dialog_admin.py` (Zeile 272)
- `app/routes/projekte_admin.py` (Zeilen 65, 219)
- `app/routes/admin.py` (Zeile 1672)

**Geänderte Dateien:**
- `app/__init__.py`: Rolle `test_benutzer` im Seed, neuer CLI-Command
- `app/routes/mailing_admin.py`: `einstellungen()`, `vorschau()`, `test_senden()` überarbeitet
- `app/services/mailing_service.py`: `send_test_email()` akzeptiert optionalen `kunde` Parameter
- `app/templates/administration/mailing/einstellungen.html`: Komplett neu (Empfänger-Tabelle)
- `app/templates/mailing_admin/vorschau.html`: Dropdown für User statt E-Mail-Adressen

**Keine DB-Migration erforderlich** - `typ` Feld existiert bereits als String.

---

## [1.8.0] - 2026-01-14

### Changed (Phase 5e: Vorschau UX-Verbesserungen)

**Test-Versand aktiviert (A):**
- Testversand-Button ist jetzt funktionsfähig (Backend war bereits implementiert)
- Button in Header-Aktionsleiste verschoben für bessere Erreichbarkeit (C)
- Dropdown zur Auswahl der Test-E-Mail-Adresse

**Konfigurierbare Test-Adressen (B):**
- Neuer Abschnitt "Test-Versand" in den Modul-Einstellungen
- Dynamische Liste mit bis zu 10 Test-E-Mail-Adressen
- Einfaches Hinzufügen/Entfernen von Adressen
- Config-Key: `mailing_test_email_adressen` (JSON-Array)

**Platzhalter-Info als Flyout (D):**
- Beispieldaten-Karte durch "Platzhalter-Info"-Button ersetzt
- Flyout zeigt alle verfügbaren Platzhalter und deren Beispielwerte
- Verwendet Bootstrap Offcanvas (450px Breite)

**Aufgeräumte Vorschau-Seite (E):**
- Sektionen-Karte entfernt (redundant, da im Preview sichtbar)
- E-Mail-Vorschau nutzt jetzt volle Breite
- Cleaner Header mit: Test-Dropdown, Platzhalter-Info, Editor, Zurück

### Technical Details

**Geänderte Dateien:**
- `app/routes/mailing_admin.py`: `einstellungen()` und `vorschau()` erweitert, `test_senden()` akzeptiert jetzt E-Mail aus Form
- `app/templates/mailing_admin/vorschau.html`: Komplett überarbeitetes Layout
- `app/templates/administration/mailing/einstellungen.html`: Neuer Abschnitt für Test-Adressen

---

## [1.7.0] - 2026-01-14

### Changed (Phase 5d: Drag & Drop Sortierung)

**Sektionen-Sortierung mit SortableJS:**
- Hoch/Runter Buttons (↑↓) durch Drag & Drop ersetzt
- Hamburger-Icon (`ti-grip-vertical`) als Drag-Handle
- Visuelles Feedback: Ghost-Element beim Ziehen, Shadow bei gewähltem Element
- Positions-Badges werden live aktualisiert
- Backend unterstützt jetzt Array-basiertes Reordering (`ordnung: ["id1", "id2", ...]`)

**Technische Details:**
- SortableJS 1.15.0 via CDN (bereits im Projekt verwendet)
- CSS-Klassen: `.sortable-handle`, `.sortable-ghost`, `.sortable-chosen`
- Neue Funktion: `saveSektionenOrder()` ersetzt `moveSektion()`
- Backend-Route `editor/reorder` erweitert für beide Modes (Array + legacy direction)

---

## [1.6.0] - 2026-01-14

### Added (Phase 5c: Editor UX-Verbesserungen)

**Markdown-Editor (b):**
- Text/Bild-Sektion nutzt jetzt Markdown statt HTML
- Markdown wird beim E-Mail-Rendering automatisch zu HTML konvertiert
- Extensions: `nl2br` (Zeilenumbrüche), `extra` (Tables, Fenced Code)
- Markdown-Hilfetext unter dem Textarea
- Größerer Editor (rows=12 statt 8)

**Platzhalter-Fix (a):**
- Platzhalter-Dropdown zeigt jetzt korrekt `{{ briefanrede }}` etc. an
- Jinja2-Escape-Syntax verwendet, damit die Template-Variablen nicht gerendert werden
- `insertPlaceholder()` Funktion nutzt Unicode-Escaping (`\u007B\u007B`) für geschweifte Klammern
  - Problem: JavaScript-String `'{{ ' + placeholder + ' }}'` wurde von Jinja2 interpretiert
  - Lösung: Unicode-Escaping umgeht Jinja2-Template-Processing

**Responsive Flyout (c):**
- Offcanvas-Breite responsive: 600px max, 45vw auf Desktop, 85vw auf Mobile
- Mehr Platz für Editor-Inhalte auf großen Bildschirmen

**Buttons im Header (d):**
- "Abbrechen" und "Speichern" Buttons in den Offcanvas-Header verschoben
- Bessere Erreichbarkeit ohne Scrollen
- Footer komplett entfernt

### Changed

- **mailing_service.py:** `render_sektion()` konvertiert Markdown→HTML für text_bild Sektionen
- **editor.html:** CSS für responsive Offcanvas-Breite, Header-Buttons

---

## [1.5.0] - 2026-01-14

### Added (Phase 5b: Editor UX-Verbesserungen)

**Vorschau-Verbesserungen:**
- **(A) Vergrößertes Vorschaufenster:** iframe mit `min-height: 800px` und Auto-Höhenanpassung
- **(B) Betreff-Anzeige:** Betreff prominent über dem E-Mail-Preview dargestellt
- **(G) Funktionierende Footer-Links:** Preview verwendet echten Test-Empfänger (Betreiber)
  - Neue Service-Methode: `get_or_create_preview_empfaenger()`
  - `get_sample_context()` erweitert um `mailing`-Parameter für echte Tracking-URLs

**Header-Sektion (C):**
- Telefon und E-Mail werden jetzt korrekt im Header angezeigt (mit Unicode-Icons)
- Fallback-Logik: `betreiber.telefon` → `betreiber.email` → `betreiber.kontakt_email`

**Medienverwaltung im Editor (D):**
- Medien-Auswahl-Modal mit Filter-Tabs (Alle, Banner, Bilder, Logos)
- Integration über "Auswählen"-Button in Hero- und Text/Bild-Sektionen
- Live-Vorschau beim Auswählen eines Mediums
- Upload-Bereich für neue Bilder (Datei-Upload + externe URL)
- API-Endpunkte: `GET /api/medien`, `POST /api/medien/upload`

**Platzhalter-Dropdown (E):**
- Text/Bild-Sektion hat jetzt Dropdown für Personalisierungs-Platzhalter
- Einfaches Einfügen von `{{ briefanrede }}`, `{{ firmenname }}`, etc.

**Legacy-Support (F):**
- `fragebogen_cta` als `deprecated: True` markiert
- Existierende Sektionen können bearbeitet werden
- Typ erscheint nicht mehr im "Hinzufügen"-Dropdown

### Changed

- **Editor-Template:** Neue CSS-Styles für Media-Card-Hover-Effekte
- **API-Upload:** Unterstützt jetzt sowohl Datei-Upload als auch externe URLs

---

## [1.4.0] - 2026-01-14

### Added (Phase 5: Editor-Erweiterung & Öffentliche Seiten)

**Neue Sektionstypen:**
- **Hero-Sektion**: Headline, Subline, optionales Bild, Hintergrundfarbe
- **CTA-Button**: Vereinheitlichter Call-to-Action mit Link-Typ-Auswahl (Fragebogen oder externe URL)

**Erweiterte Sektionstypen:**
- **Header**:
  - Logo-URL überschreibbar
  - Telefon-Link ein/ausblendbar
  - E-Mail-Link (zum Kontaktformular)
  - "Im Browser öffnen"-Link
- **Footer**:
  - Impressum-Block mit Betreiber-Daten (Adresse, Handelsregister, USt-ID)
  - Link "Persönliche Daten" zu Profil-Seite
  - Link "Weiterempfehlen" zu Empfehlungs-Formular

**Neue öffentliche Routes (`/m/`):**
- `GET /m/profil/<token>` - Persönliche Daten des Empfängers anzeigen
- `GET /m/empfehlen/<token>` - Weiterempfehlungs-Formular
- `POST /m/empfehlen/<token>` - Weiterempfehlung absenden
- `GET /m/browser/<token>` - Mailing im Browser anzeigen

**Neue E-Mail-Templates:**
- `sektion_hero.html` - Hero-Sektion
- `sektion_cta_button.html` - Universeller CTA-Button
- `email/weiterempfehlung.html` - E-Mail für Weiterempfehlungen

**Neue öffentliche Templates:**
- `mailing/profil.html` - Persönliche Daten
- `mailing/empfehlen.html` - Weiterempfehlungs-Formular
- `mailing/empfohlen.html` - Erfolgsseite nach Empfehlung

**Neue Platzhalter:**
- `{{ profil_link }}` - Link zur Profil-Seite
- `{{ empfehlen_link }}` - Link zum Weiterempfehlungs-Formular
- `{{ browser_link }}` - Link zur Browser-Ansicht
- `{{ cta_link }}` - Berechneter CTA-Link (Fragebogen oder extern)
- `{{ betreiber }}` - Betreiber-Kunde-Objekt
- `{{ branding }}` - Branding-Konfiguration

**DB-Erweiterungen:**
- `Kunde.handelsregister_info` - Handelsregister-Eintrag (z.B. "HRB 94083 B, AG Charlottenburg")
- `Kunde.umsatzsteuer_id` - USt-ID (z.B. "DE812373677")

**Config-Keys:**
- `betreiber_impressum_url` - Link zum Impressum
- `betreiber_datenschutz_url` - Link zur Datenschutzerklärung
- `betreiber_kontaktformular_url` - Link zum Kontaktformular

**Branding-Service:**
- `BrandingConfig` um `impressum_url`, `datenschutz_url`, `kontaktformular_url` erweitert
- `get_branding_service()` Factory-Funktion hinzugefügt

### Changed

- **Editor-UI**: Modals durch seitlichen Flyout (Bootstrap Offcanvas) ersetzt
- **Editor-Titel**: "Baukasten-Editor" → "Mailing-Editor"
- **Sektionen-Dropdown**: Zeigt jetzt alle 5 Typen (Header, Hero, Text/Bild, CTA-Button, Footer)

### Fixed

- **CTA-Button-Rendering**: `cta_link` wird korrekt aus Fragebogen oder externer URL berechnet

## [1.3.3] - 2026-01-14

### Fixed

- **Baukasten-Editor:** "Sektion bearbeiten" Button funktioniert jetzt korrekt
  - Ursache: Inline-onclick mit `|tojson|e` Filter verursachte JSON-Parsing-Fehler durch doppeltes HTML-Encoding
  - Lösung: JSON-Config in `data-*` Attribut mit Single-Quotes speichern, Event-Listener statt inline-onclick
  - Zusätzlich: `escapeForTemplate()` Funktion für sichere Template-Literal-Interpolation
  - Betroffen: [editor.html](../../../../app/templates/mailing_admin/editor.html) Zeilen 101-105, 294-309, 325-395

## [1.3.2] - 2026-01-14

### Fixed

- **Baukasten-Editor:** "Sektion hinzufügen" Button funktioniert jetzt korrekt
  - Ursache: SQLAlchemy erkannte In-Place-Änderungen am JSON-Feld `sektionen_json` nicht
  - Lösung: `flag_modified()` in `Mailing.add_sektion()` und `update_sektionen()` hinzugefügt
  - Betroffen: [mailing.py](../../../../app/models/mailing.py) Zeilen 132-152

## [1.3.1] - 2026-01-14

### Added (Phase 4b: Einstellungsbereich)

- Einstellungen-Route `/admin/mailing/einstellungen`:
  - Brevo Rate-Limiting (Tageslimit konfigurierbar)
  - E-Mail Standardwerte (Absender-Email, Absender-Name, Footer-Text)
  - CTA-Button Design (Standard-Farbe mit Color-Picker)
- Einstellungen-Template unter `administration/mailing/einstellungen.html`
- Zahnrad-Icon auf Modul-Kachel in der Modul-Übersicht
- Einstellungen-Button in der Mailing-Index-Seite

### Config-Keys

- `mailing_brevo_tageslimit` - E-Mails pro Tag (Default: 300)
- `mailing_absender_email` - Überschreibt globale Brevo-Einstellung
- `mailing_absender_name` - Überschreibt globale Brevo-Einstellung
- `mailing_footer_text` - Zusatz-Text im E-Mail-Footer
- `mailing_cta_button_farbe` - Standard-Farbe für CTA-Buttons

## [1.3.0] - 2026-01-14

### Added (Phase 4: Tracking & Statistik)

- Detaillierte Statistik-Seite (`/admin/mailing/<id>/statistik`):
  - Übersichts-Karten: Empfänger, Versendet, Klicks, Klickrate
  - Klick-Verteilung nach Typ (Fragebogen, Abmelden, Custom-Links)
  - Empfänger-Status Visualisierung (Erfolgreich, Fehlgeschlagen, Ausstehend)
  - Top-Empfänger nach Klicks Rangliste
  - Abmeldungen-Übersicht
- Kunden-Mailing Kachel in Modul-Übersicht (`/admin/module-uebersicht`)
- Statistik-Button in Detail-Ansicht für versendete Mailings

### Note

- Tracking-System (Token, Klick-Erfassung, MailingKlick-Modell) war bereits in Phase 3 implementiert

## [1.2.0] - 2026-01-14

### Added (Phase 3: Empfänger & Versand)

- Öffentliches Blueprint `mailing_bp` unter `/m/`:
  - `GET /m/t/<token>` - Klick-Tracking mit Weiterleitung
  - `GET /m/abmelden/<token>` - Abmelde-Bestätigungsseite
  - `POST /m/abmelden/<token>` - Abmeldung durchführen
- Öffentliche Templates (ohne Login, mit Branding):
  - `mailing/abmelden.html` - Abmelde-Formular
  - `mailing/abgemeldet.html` - Erfolgsseite
  - `mailing/fehler.html` - Fehlerseite für ungültige Links
- Versand-Service-Methoden in `MailingService`:
  - `generate_tracking_url()` - Tracking-URLs generieren
  - `send_test_email()` - Test-E-Mail an beliebige Adresse
  - `send_to_empfaenger()` - E-Mail an einzelnen Empfänger
  - `send_batch()` - Batch-Versand mit Quota-Respekt
- Admin-Route `/<id>/senden` mit Batch-Warnung UI
- Admin-Template `senden.html` mit:
  - Quota-Anzeige (Fortschrittsbalken)
  - Batch-Warnung bei >300 Empfängern
  - Auswahl der zu versendenden Anzahl
- Test-Versand-Button aktiviert in Vorschau-Seite
- Integration mit BrevoService für tatsächlichen E-Mail-Versand

### Changed

- Detail-Ansicht: "Jetzt versenden"-Button führt nun zur Senden-Seite
- Test-Senden-Route nutzt nun echten Service statt Platzhalter

## [1.1.0] - 2026-01-14

### Added (Phase 2: Baukasten-Editor)

- E-Mail-Templates mit Inline-Styles für E-Mail-Client-Kompatibilität:
  - `base.html` - E-Mail-Wrapper mit Table-Layout
  - `sektion_header.html` - Logo/Portal-Name
  - `sektion_text_bild.html` - Freier Content mit optionalem Bild
  - `sektion_fragebogen_cta.html` - CTA-Button zum Fragebogen
  - `sektion_footer.html` - Abmelde-Link und Footer-Text
- Visueller Baukasten-Editor (`/admin/mailing/<id>/editor`)
  - Sektionen hinzufügen, bearbeiten, löschen
  - Button-basiertes Reordering (↑/↓)
  - Modal-Dialoge für Sektion-Konfiguration
- E-Mail-Vorschau (`/admin/mailing/<id>/vorschau`)
  - Live-Preview im iframe
  - Desktop/Mobile Toggle
  - Sample-Daten für Personalisierung
- AJAX-Endpoints für Editor-Operationen:
  - POST `/editor/sektion` - Sektion hinzufügen
  - PATCH `/editor/sektion/<sid>` - Sektion bearbeiten
  - DELETE `/editor/sektion/<sid>` - Sektion löschen
  - POST `/editor/reorder` - Reihenfolge ändern
- Service-Erweiterungen:
  - `get_sample_context()` - Beispieldaten für Preview
  - `render_mailing_html()` mit `preview_mode` Parameter

### Changed

- Detail-Ansicht um Editor- und Vorschau-Links erweitert

## [1.0.0] - 2026-01-13

### Added (Phase 1: Basis-Infrastruktur)

- PRD-013 Dokument erstellt mit vollständiger Spezifikation
- Datenmodell-Design (Mailing, MailingEmpfaenger, MailingKlick, MailingZielgruppe)
- Service-Architektur definiert (MailingService)
- Route-Struktur für Admin und öffentliche Endpunkte
- Template-Struktur für Admin-UI und E-Mail-Sektionen
- Fragebogen-Integration mit PRD-006 spezifiziert
- DSGVO-konforme Abmelde-Funktion geplant
- Manuelles Batching für Brevo-Tageslimit dokumentiert
