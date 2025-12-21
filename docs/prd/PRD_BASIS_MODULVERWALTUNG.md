# PRD: Modulverwaltung (Basis-Plattform)

> **Status:** ✅ Implementiert
> **Version:** 1.1
> **Erstellt:** 2025-12-12
> **Aktualisiert:** 2025-12-12
> **Priorität:** Abgeschlossen

---

## 1. Übersicht

### 1.1 Ziel

Konsolidierung der parallelen "Modul"-Konzepte (`SubApp` und `Modul`) in ein einheitliches System. Nach der Konsolidierung gibt es nur noch **ein** Modul-Model mit allen erforderlichen Eigenschaften für:

- **Dashboard-Anzeige** (Icon, Farbe, Route)
- **Audit-Logging** (Modul-Referenz)
- **Zugriffskontrolle** (Rollen-basiert)
- **Aktivierung/Deaktivierung** (außer Basismodule)

### 1.2 Aktueller Zustand (Analyse)

**Zwei parallele Systeme existieren:**

| Aspekt | SubApp | Modul |
|--------|--------|-------|
| **Zweck** | Dashboard-Kacheln, UI | Audit-Logging |
| **Einträge** | 4 (pricat, kunden, lieferanten, content) | 8 (4 Basis + 4 Optional) |
| **UI-Felder** | ✅ icon, color, color_hex, route_endpoint | ❌ |
| **Zugriffskontrolle** | ✅ SubAppAccess (rolle_id FK) | ❌ |
| **Basis-Flag** | ❌ | ✅ ist_basis |

**Probleme:**
- Doppelte Konzepte mit unterschiedlichen Namen
- SubApp fehlen die Basismodule (system, stammdaten, logging, auth)
- Modul fehlen UI-Eigenschaften
- Inkonsistente Benennung (sub_app vs modul)

### 1.3 Zielzustand

**Ein einheitliches `Modul`-Model** mit:

- Alle UI-Felder aus SubApp
- Basismodul-Flag aus aktuellem Modul
- Neues Flag `zeige_dashboard` (Basismodule erscheinen nicht auf Dashboard)
- Umbenannte Zugriffstabelle: `modul_zugriff` (statt sub_app_access)

---

## 2. Datenmodell (Konsolidiert)

### 2.1 Erweitertes Modul-Model

```python
class Modul(db.Model):
    """Unified module model for dashboard, logging, and access control."""
    __tablename__ = 'modul'

    id = db.Column(db.Integer, primary_key=True)

    # Identifikation (von beiden)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)  # z.B. 'kunden'
    name = db.Column(db.String(100), nullable=False)  # z.B. 'Lead & Kundenreport'
    beschreibung = db.Column(db.Text, nullable=True)

    # UI-Eigenschaften (von SubApp)
    icon = db.Column(db.String(50), default='ti-package')
    color = db.Column(db.String(20), default='primary')  # Bootstrap class
    color_hex = db.Column(db.String(7), default='#0d6efd')
    route_endpoint = db.Column(db.String(100), nullable=True)  # Flask endpoint
    sort_order = db.Column(db.Integer, default=0)

    # Modultyp und Status
    ist_basis = db.Column(db.Boolean, default=False)  # Kann nicht deaktiviert werden
    zeige_dashboard = db.Column(db.Boolean, default=True)  # Erscheint auf Dashboard
    aktiv = db.Column(db.Boolean, default=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    zugriffe = db.relationship('ModulZugriff', backref='modul',
                               lazy='dynamic', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='modul', lazy='dynamic')
```

### 2.2 Zugriffstabelle (umbenannt)

> **Rechteverwaltung:** Für Details zu Rollen, Admin-Sonderrechten und Zugriffskontrolle siehe [PRD_BASIS_RECHTEVERWALTUNG.md](PRD_BASIS_RECHTEVERWALTUNG.md).

```python
class ModulZugriff(db.Model):
    """Role-based module access control."""
    __tablename__ = 'modul_zugriff'

    id = db.Column(db.Integer, primary_key=True)
    modul_id = db.Column(db.Integer, db.ForeignKey('modul.id'), nullable=False)
    rolle_id = db.Column(db.Integer, db.ForeignKey('rolle.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('modul_id', 'rolle_id', name='uq_modul_rolle'),
    )
```

### 2.3 Vollständige Modulliste (Seed)

| Code | Name | ist_basis | zeige_dashboard | Icon | Route |
|------|------|-----------|-----------------|------|-------|
| `system` | System & Administration | ✅ | ❌ | ti-settings | - |
| `stammdaten` | Stammdatenpflege | ✅ | ❌ | ti-database | - |
| `logging` | Audit-Log | ✅ | ❌ | ti-list-check | - |
| `auth` | Authentifizierung | ✅ | ❌ | ti-lock | - |
| `pricat` | PRICAT Converter | ❌ | ✅ | ti-transform | pricat.index |
| `kunden` | Lead & Kundenreport | ❌ | ✅ | ti-users | kunden.index |
| `lieferanten` | Meine Lieferanten | ❌ | ✅ | ti-building-store | lieferanten.index |
| `content` | Content Generator | ❌ | ✅ | ti-wand | content.index |

---

## 3. Migrationsstrategie

### 3.1 Übersicht

Die Migration erfolgt in 4 Schritten, um Datenverlust zu vermeiden:

```
Schritt 1: Modul erweitern (neue Felder hinzufügen)
Schritt 2: Daten migrieren (SubApp → Modul, SubAppAccess → ModulZugriff)
Schritt 3: Code anpassen (alle Referenzen auf SubApp → Modul)
Schritt 4: Alte Tabellen entfernen (sub_app, sub_app_access)
```

### 3.2 Schritt 1: Schema-Erweiterung

**Migration für neue Felder in `modul`:**

```python
# migrations/versions/xxx_extend_modul.py
def upgrade():
    # Neue Felder zu modul hinzufügen
    op.add_column('modul', sa.Column('beschreibung', sa.Text(), nullable=True))
    op.add_column('modul', sa.Column('icon', sa.String(50), server_default='ti-package'))
    op.add_column('modul', sa.Column('color', sa.String(20), server_default='primary'))
    op.add_column('modul', sa.Column('color_hex', sa.String(7), server_default='#0d6efd'))
    op.add_column('modul', sa.Column('route_endpoint', sa.String(100), nullable=True))
    op.add_column('modul', sa.Column('sort_order', sa.Integer(), server_default='0'))
    op.add_column('modul', sa.Column('zeige_dashboard', sa.Boolean(), server_default='true'))
    op.add_column('modul', sa.Column('created_at', sa.DateTime()))

    # Neue Tabelle modul_zugriff
    op.create_table('modul_zugriff',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('modul_id', sa.Integer(), sa.ForeignKey('modul.id'), nullable=False),
        sa.Column('rolle_id', sa.Integer(), sa.ForeignKey('rolle.id'), nullable=False),
        sa.Column('created_at', sa.DateTime()),
        sa.UniqueConstraint('modul_id', 'rolle_id', name='uq_modul_rolle')
    )
```

### 3.3 Schritt 2: Datenmigration

**Manuelles Migrationsskript:**

```python
def migrate_sub_apps_to_modules():
    """Migrate SubApp data to Modul table."""
    from app.models import SubApp, SubAppAccess, Modul, ModulZugriff

    # Mapping SubApp.slug → Modul.code
    slug_to_code = {
        'pricat': 'pricat',
        'kunden-report': 'kunden',
        'lieferanten-auswahl': 'lieferanten',
        'content-generator': 'content',
    }

    for sub_app in SubApp.query.all():
        code = slug_to_code.get(sub_app.slug, sub_app.slug)
        modul = Modul.query.filter_by(code=code).first()

        if modul:
            # Update existing Modul with SubApp data
            modul.beschreibung = sub_app.beschreibung
            modul.icon = sub_app.icon
            modul.color = sub_app.color
            modul.color_hex = sub_app.color_hex
            modul.route_endpoint = sub_app.route_endpoint
            modul.sort_order = sub_app.sort_order
            modul.zeige_dashboard = True

            # Migrate access rights
            for access in sub_app.role_access:
                existing = ModulZugriff.query.filter_by(
                    modul_id=modul.id, rolle_id=access.rolle_id
                ).first()
                if not existing:
                    db.session.add(ModulZugriff(
                        modul_id=modul.id,
                        rolle_id=access.rolle_id
                    ))

    db.session.commit()
```

### 3.4 Schritt 3: Code-Anpassungen

**Betroffene Dateien:**

| Datei | Änderung |
|-------|----------|
| `app/models/__init__.py` | SubApp/SubAppAccess entfernen, ModulZugriff hinzufügen |
| `app/models/sub_app.py` | Datei löschen |
| `app/models/modul.py` | Erweitern mit neuen Feldern |
| `app/templates/dashboard.html` | SubApp → Modul |
| `app/routes/main.py` | get_user_apps() → get_user_modules() |
| `app/routes/admin.py` | SubApp-Verwaltung → Modul-Verwaltung |
| `app/cli.py` | Seed-Command aktualisieren |

### 3.5 Schritt 4: Aufräumen

```python
# Nach erfolgreicher Migration
def downgrade():
    op.drop_table('sub_app_access')
    op.drop_table('sub_app')
```

---

## 4. Dashboard-Integration

### 4.1 Helper-Funktion

```python
def get_user_modules(user) -> list[Modul]:
    """Get modules visible to user on dashboard.

    Returns modules that are:
    1. Active (aktiv=True)
    2. Should show on dashboard (zeige_dashboard=True)
    3. User has access (via ModulZugriff) OR user is admin
    """
    if user.rolle.name == 'admin':
        # Admins see all dashboard modules
        return Modul.query.filter(
            Modul.aktiv == True,
            Modul.zeige_dashboard == True
        ).order_by(Modul.sort_order).all()

    return Modul.query.filter(
        Modul.aktiv == True,
        Modul.zeige_dashboard == True,
        Modul.id.in_(
            db.session.query(ModulZugriff.modul_id)
            .filter(ModulZugriff.rolle_id == user.rolle_id)
        )
    ).order_by(Modul.sort_order).all()
```

### 4.2 Template-Anpassung

```html
<!-- templates/dashboard.html -->
{% for modul in modules %}
<div class="col-md-4 mb-4">
    <div class="card h-100 module-card" style="border-color: {{ modul.color_hex }}">
        <div class="card-body text-center">
            <i class="{{ modul.icon }}" style="font-size: 3rem; color: {{ modul.color_hex }}"></i>
            <h5 class="card-title mt-3">{{ modul.name }}</h5>
            <p class="card-text text-muted">{{ modul.beschreibung }}</p>
            <a href="{{ url_for(modul.route_endpoint) }}" class="btn btn-{{ modul.color }}">
                Öffnen
            </a>
        </div>
    </div>
</div>
{% endfor %}
```

---

## 5. Admin-UI

### 5.1 Route: `/admin/module`

**Funktionen:**

- Liste aller Module (sortiert nach sort_order)
- Aktivieren/Deaktivieren (außer Basismodule)
- Icon und Farbe bearbeiten
- Sortierung per Drag & Drop
- Rollen-Zuweisung pro Modul

### 5.2 Berechtigungslogik

```python
@admin_bp.route('/module/<int:id>/toggle', methods=['POST'])
def toggle_modul(id):
    modul = Modul.query.get_or_404(id)

    if modul.ist_basis:
        return jsonify({'error': 'Basismodule können nicht deaktiviert werden'}), 400

    modul.aktiv = not modul.aktiv
    db.session.commit()

    log_event(
        modul='system',
        aktion='modul_status_geaendert',
        details=f'Modul "{modul.name}" {"aktiviert" if modul.aktiv else "deaktiviert"}',
        wichtigkeit='mittel',
        entity_type='Modul',
        entity_id=modul.id
    )

    return jsonify({'success': True, 'aktiv': modul.aktiv})
```

---

## 6. Implementierungsreihenfolge

### Phase 1: Schema & Migration

| # | Aufgabe | Datei |
|---|---------|-------|
| 1.1 | Modul-Model erweitern | `app/models/modul.py` |
| 1.2 | ModulZugriff-Model erstellen | `app/models/modul_zugriff.py` |
| 1.3 | Models exportieren | `app/models/__init__.py` |
| 1.4 | Migration erstellen | `flask db migrate` |
| 1.5 | Migration anwenden | `flask db upgrade` |

### Phase 2: Datenmigration

| # | Aufgabe | Datei |
|---|---------|-------|
| 2.1 | Migrationsskript erstellen | `app/cli.py` (neuer Command) |
| 2.2 | SubApp-Daten → Modul übertragen | CLI: `flask migrate-modules` |
| 2.3 | Seed-Command aktualisieren | `app/cli.py` |

### Phase 3: Code-Anpassungen

| # | Aufgabe | Datei |
|---|---------|-------|
| 3.1 | Dashboard Helper | `app/routes/main.py` |
| 3.2 | Dashboard Template | `app/templates/dashboard.html` |
| 3.3 | Admin-Module-Route | `app/routes/admin.py` |
| 3.4 | Admin-Module-Template | `app/templates/administration/module.html` |

### Phase 4: Aufräumen

| # | Aufgabe |
|---|---------|
| 4.1 | SubApp-Referenzen entfernen |
| 4.2 | sub_app.py löschen |
| 4.3 | Migration für Tabellen-Drop |

---

## 7. Entscheidungen

### 7.1 Warum `zeige_dashboard` statt `ist_dashboard_modul`?

- Flexibler: Erlaubt temporäres Ausblenden von Modulen
- Konsistent: Boolesches Flag wie `aktiv` und `ist_basis`

### 7.2 Warum Umbenennung zu `modul` statt Beibehaltung von `sub_app`?

- **Konsistenz:** Alle PRDs verwenden den Begriff "Modul"
- **Klarheit:** "SubApp" suggeriert untergeordnete Anwendung, nicht Modul
- **Logging:** AuditLog referenziert bereits `modul_id`

### 7.3 Warum `modul_zugriff` statt `modul_rolle`?

- **Klarheit:** "Zugriff" beschreibt die Funktion besser als "Rolle"
- **Deutsch:** Konsistent mit deutscher Namenskonvention im Projekt

---

## 8. Offene Fragen (Beantwortet)

| Frage | Antwort |
|-------|---------|
| Sollen Module versioniert werden? | Nein (nicht im MVP) |
| Wie werden Modul-spezifische Einstellungen verwaltet? | Über Config-Tabelle mit Modul-Prefix |
| Was passiert mit bestehenden SubApp-Daten? | Werden migriert nach Modul |

---

## 9. Risiken

| Risiko | Mitigation |
|--------|------------|
| Datenverlust bei Migration | Backup vor Migration, schrittweise Durchführung |
| Breaking Changes | Alle SubApp-Referenzen vor Tabellen-Drop aktualisieren |
| Dashboard-Ausfall | Zuerst neue Logik implementieren, dann alte entfernen |

---

## Changelog

| Datum | Version | Änderung |
|-------|---------|----------|
| 2025-12-12 | 0.1 | Platzhalter erstellt |
| 2025-12-12 | 1.0 | Vollständige Spezifikation mit Konsolidierungsstrategie |