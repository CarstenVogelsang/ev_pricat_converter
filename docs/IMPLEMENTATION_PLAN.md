# Verbesserungsplan pricat-converter

## Task-Übersicht

| # | Task | Status | Beschreibung |
|---|------|--------|--------------|
| 1 | FTP Port-Konfiguration | ✅ Erledigt | Separate Port-Config für VEDES und Elena FTP |
| 2 | Admin-Seite | ✅ Erledigt | Admin-Panel mit FTP-Tests und Health-Checks |
| 3 | Benutzer-Authentifizierung | ✅ Erledigt | Flask-Login mit Admin/Sachbearbeiter-Rollen |
| 4 | VEDES_ID ohne Nullen | ✅ Erledigt | Führende Nullen aus VEDES_ID entfernen |
| 5 | Lieferanten-Sync | ✅ Erledigt | FTP-Scan und automatische Lieferanten-Anlage |
| 6 | Base64-Passwörter | ✅ Erledigt | FileZilla-kompatible Base64-Passwörter in Config |
| 7 | Lieferanten-Filter | ✅ Erledigt | Filter (Aktiv/Inaktiv/Alle) und Toggle-Button |
| 8 | Artikel-Anzahl & FTP Check | ✅ Erledigt | Artikelzählung, FTP Check Button, Download bei Änderung |
| 9 | Toast-Meldungen | ✅ Erledigt | Bootstrap Toasts statt Alert-Boxen für bessere UX |

**Letztes Update:** 2025-12-04

---

## Gesammelte Tasks

### Task 1: FTP Port-Konfiguration
**Problem:** Der FTP-Port ist auf 21 hardcodiert. Es gibt keinen Config-Eintrag für den Port.

**Lösung:** Separater Port-Eintrag pro FTP-Server (Option A)
- Neue Config-Einträge: `vedes_ftp_port` und `elena_ftp_port`
- Port aus DB laden in `_load_vedes_config()` und `_load_elena_config()`
- Standard-Port 21 als Fallback

**Betroffene Dateien:**
- `app/__init__.py` - Seed-Einträge erweitern
- `app/services/ftp_service.py` - Config-Loading anpassen

---

### Task 2: Admin-Seite mit Verbindungstests

**Anforderung:**
- Admin-Seite für manuelle Tests (FTP-Verbindungen etc.)
- Buttons für VEDES FTP und Elena FTP Verbindungstests
- Automatisierter Precheck (Health-Check) für den Dienst

**Lösung:** Eigener `admin_bp` Blueprint mit `/admin/*` Routes

**Neue Routes:**
- `GET /admin` - Admin-Übersicht mit Test-Buttons
- `POST /admin/test-ftp/vedes` - VEDES FTP Verbindungstest
- `POST /admin/test-ftp/elena` - Elena FTP Verbindungstest
- `GET /admin/health` - Automatischer Health-Check (JSON) für alle Voraussetzungen
- `GET /api/health` - Öffentlicher Health-Endpoint für Monitoring

**Health-Check prüft:**
- Datenbank-Verbindung
- VEDES FTP erreichbar
- Elena FTP erreichbar
- Config-Einträge vollständig

**Betroffene Dateien:**
- `app/routes/admin.py` - NEU: Admin Blueprint
- `app/routes/__init__.py` - admin_bp exportieren
- `app/__init__.py` - admin_bp registrieren mit url_prefix='/admin'
- `app/templates/admin.html` - NEU: Admin-Template
- `app/templates/base.html` - Navigation erweitern (Admin-Link)

**Existierende Methode nutzen:**
- `FTPService.test_connection(target='vedes'|'elena')` bereits vorhanden

---

### Task 3: Benutzer-Authentifizierung mit Rollen

**Anforderung:**
- Login-Schutz für die gesamte Flask-Website
- Rollen: Admin und Sachbearbeiter
- Nur Admins können Admin-Seite nutzen
- 2 initiale Benutzer anlegen

**Lösung:** Flask-Login mit User-Model und Rollen

**Neue Packages:**
- `flask-login>=0.6.2` - Session-basierte Authentifizierung
- `flask-wtf>=1.2.0` - Login-Formular mit CSRF-Schutz

**User-Model Felder:**
- id, email (unique), password_hash
- vorname, nachname
- rolle ('admin' | 'sachbearbeiter')
- aktiv, last_login, created_at

**Initiale Benutzer (via flask seed-users):**
1. Carsten Vogelsang, carsten.vogelsang@e-vendo.de, Admin
2. Rainer Raschka, rainer.raschka@e-vendo.de, Sachbearbeiter

**Neue Routes:**
- `GET/POST /login` - Login-Seite
- `GET /logout` - Ausloggen
- Alle anderen Routes: `@login_required`
- Admin-Routes: `@admin_required` Decorator

**Betroffene Dateien:**
- `requirements.txt` - flask-login, flask-wtf hinzufügen
- `app/models/user.py` - NEU: User-Model
- `app/models/__init__.py` - User exportieren
- `app/__init__.py` - Flask-Login initialisieren, seed-users Command
- `app/routes/auth.py` - NEU: Login/Logout Routes
- `app/routes/__init__.py` - auth_bp exportieren
- `app/routes/main.py` - @login_required hinzufügen
- `app/routes/admin.py` - @admin_required hinzufügen
- `app/templates/login.html` - NEU: Login-Formular
- `app/templates/base.html` - User-Info in Navbar, Logout-Link

---

### Task 4: VEDES_ID ohne führende Nullen speichern

**Problem:** Die VEDES_ID wird aktuell mit führenden Nullen gespeichert (z.B. `0000001872` statt `1872`). Die ID soll ohne führende Nullen in der Datenbank abgelegt werden.

**Anforderung:**
- VEDES_ID in Lieferant-Tabelle ohne führende Nullen speichern
- Bei Vergleichen mit Daten aus PRICAT-Dateien (die führende Nullen enthalten) müssen die Nullen entfernt werden

**Lösung:**
- Hilfsfunktion `strip_leading_zeros(value)` für Vergleiche
- Beim Speichern: `lstrip('0')` oder Hilfsfunktion verwenden
- Bestehende Daten via Migration oder Seed-Update korrigieren

**Betroffene Dateien:**
- `app/__init__.py` - Seed-Daten anpassen (LEGO: `'1872'` statt `'0000001872'`)
- `app/services/pricat_parser.py` - Beim Extrahieren die Nullen entfernen
- `app/utils.py` - NEU: Hilfsfunktion `strip_leading_zeros()`
- Migration oder manuelles DB-Update für bestehende Daten

---

### Task 5: Lieferanten-Synchronisation mit VEDES FTP

**Anforderung:**
- Admin-Funktion zum Abgleich der Lieferanten-Tabelle mit dem VEDES FTP
- Neue Lieferanten automatisch anlegen (inaktiv, `aktiv=False`)
- Spalte `ftp_pfad_quelle` umbenennen in `ftp_quelldatei` (nur Dateiname, kein Pfad)
- VEDES_ID aus Dateinamen extrahieren (z.B. `pricat_1872_Lego Spielwaren GmbH_0.csv` → `1872`)

**Dateinamen-Format (Beispiel):**
```
pricat_1872_Lego Spielwaren GmbH_0.csv
       ^^^^
       VEDES_ID (ohne führende Nullen)
```

**Logik:**
1. Verbinde mit VEDES FTP
2. Liste alle CSV-Dateien im PRICAT-Verzeichnis
3. Parse VEDES_ID aus Dateinamen (Regex: `pricat_(\d+)_`)
4. Für jede Datei:
   - Suche Lieferant mit passender `vedes_id` (ohne führende Nullen, siehe Task 4)
   - Falls nicht vorhanden: Neuen Lieferant anlegen
     - `vedes_id`: Extrahierte ID
     - `gln`: Leer oder Platzhalter (später manuell ergänzen)
     - `kurzbezeichnung`: Aus Dateinamen extrahieren (Teil zwischen ID und `_0.csv`)
     - `ftp_quelldatei`: Dateiname
     - `aktiv`: False
5. Falls vorhanden: ggf. `ftp_quelldatei` aktualisieren

**Neue Routes (Admin-Blueprint):**
- `POST /admin/sync-lieferanten` - Synchronisation starten
- Anzeige der Ergebnisse (neu angelegt, aktualisiert, unverändert)

**Betroffene Dateien:**
- `app/models/lieferant.py` - Spalte `ftp_pfad_quelle` → `ftp_quelldatei`
- `app/models/lieferant.py` - `to_dict()` anpassen
- `app/__init__.py` - Seed-Daten anpassen
- `app/services/ftp_service.py` - Verweis auf `ftp_pfad_quelle` → `ftp_quelldatei`
- `app/routes/admin.py` - Neue Route für Sync
- `app/templates/admin.html` - Button + Ergebnisanzeige
- Migration: `flask db migrate` für Spaltenumbenennung

**Entscheidung:** `gln` auf `nullable=True` ändern. Das Feld wird später durch den Import gefüllt.

---

## Status
- [x] Alle Tasks gesammelt
- [x] Plan finalisiert
- [x] Umsetzung abgeschlossen (Commit: b35c272)

## Umsetzungsreihenfolge

Die Tasks wurden in dieser Reihenfolge umgesetzt:

1. **Task 4: VEDES_ID ohne führende Nullen** ✅
2. **Task 5: Lieferanten-Synchronisation** ✅
3. **Task 1: FTP Port-Konfiguration** ✅
4. **Task 2: Admin-Seite** ✅
5. **Task 3: Benutzer-Authentifizierung** ✅

## Initiale Benutzer

| E-Mail | Passwort | Rolle |
|--------|----------|-------|
| carsten.vogelsang@e-vendo.de | admin123 | Admin |
| rainer.raschka@e-vendo.de | user123 | Sachbearbeiter |

---

### Task 6: Base64-kodierte Passwörter (FileZilla-kompatibel)

**Problem:** FileZilla speichert Passwörter Base64-kodiert in der XML-Konfiguration. Beim Kopieren dieser Werte in die Config-Tabelle schlägt die FTP-Authentifizierung fehl.

**Lösung:** Passwörter werden Base64-kodiert in der Config-Tabelle gespeichert und beim Laden dekodiert.

**Änderungen:**
- `app/services/ftp_service.py`:
  - Neue Methode `_decode_password(password_b64)` zum Dekodieren
  - `_load_vedes_config()` und `_load_elena_config()` nutzen `_decode_password()`
  - Neues Feld `encoding` in `FTPConfig` Dataclass für FTP-Dateinamen-Encoding
  - Neuer Config-Eintrag `vedes_ftp_encoding` (z.B. `latin-1` für Umlaute)

**Betroffene Dateien:**
- `app/services/ftp_service.py` - Base64-Dekodierung, Encoding-Config

---

### Task 7: Lieferanten-Filter und Aktivieren/Deaktivieren

**Anforderung:**
- Filter in der Übersicht: "Aktiv", "Inaktiv", "Alle" (Standard: Aktiv)
- Button pro Lieferant zum Aktivieren/Deaktivieren

**Änderungen:**

**`app/routes/main.py`:**
- Route `index()`: Query-Parameter `?filter=aktiv|inaktiv|alle` auswerten
- Neue Route `toggle_aktiv(lieferant_id)`: POST-Route zum Umschalten des Status

**`app/templates/index.html`:**
- Filter-Buttons (Aktiv/Inaktiv/Alle) oberhalb der Tabelle
- Dynamischer Titel basierend auf Filter
- Status-Spalte mit Badge (Aktiv/Inaktiv)
- Toggle-Button pro Zeile (Aktivieren/Deaktivieren)
- Kontextabhängige Leermeldung

**Betroffene Dateien:**
- `app/routes/main.py` - Filter-Logik, Toggle-Route
- `app/templates/index.html` - Filter-UI, Status-Anzeige, Toggle-Button

---

### Task 9: Toast-Meldungen statt Alert-Boxen

**Problem:** Nach Button-Aktionen (z.B. "FTP Check") springt das Fenster nach oben und der User muss wieder zum Lieferanten scrollen. Flash-Meldungen werden oben als Alert-Boxen angezeigt.

**Lösung:** Bootstrap 5 Toast-Meldungen (fixed oben rechts)

**Toast-Eigenschaften:**
- Position: Oben rechts (fixed)
- Auto-Hide: Nach 5 Sekunden
- Farbkodierung: success/danger/warning/info

**Änderungen:**
- `app/templates/base.html`: Toast-Container + JavaScript zum automatischen Anzeigen
- `docs/PRD_Software-Architektur.md`: Neuer Abschnitt "11. UI/UX Richtlinien"
- `CLAUDE.md`: Hinweis auf Toast-Standard

**Leitplanke:** Ab sofort werden an allen Stellen Toast-Meldungen verwendet, keine Alert-Boxen im Seiteninhalt.
