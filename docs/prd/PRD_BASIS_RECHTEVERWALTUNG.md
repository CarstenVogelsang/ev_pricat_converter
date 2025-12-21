# PRD: Rechteverwaltung (Basis-Plattform)

> **Status:** ✅ Implementiert
> **Version:** 1.0
> **Erstellt:** 2025-12-21
> **Priorität:** Abgeschlossen

---

## 1. Übersicht

Die ev247-Plattform verwendet **zwei unabhängige Rollensysteme**:

| System | Ebene | Zweck |
|--------|-------|-------|
| **Benutzer-Rollen** | Plattform | Login, Menü-Sichtbarkeit, Modul-Zugriff |
| **Branchenrollen** | Geschäftsmodell | Kunden-Kategorisierung (Händler, Hersteller, etc.) |

Diese Trennung ist bewusst: Ein Benutzer kann gleichzeitig `mitarbeiter` (Plattform-Rolle) und `Hersteller` (Branchenrolle für einen Kunden) sein.

---

## 2. Benutzer-Rollen (Plattform-Ebene)

### 2.1 Rollen-Katalog

| Rolle | Beschreibung | Sonderrechte |
|-------|--------------|--------------|
| `admin` | Vollzugriff | **Immer Zugriff auf ALLE Module** (siehe 2.2) |
| `mitarbeiter` | e-vendo Mitarbeiter | Interne Module, Kundenverwaltung |
| `kunde` | Externer Kunde | Nur zugewiesene Module |

**Implementierung:** `app/models/rolle.py`, `app/models/user.py`

### 2.2 Admin-Sonderrechte (KRITISCH!)

> ⚠️ **WICHTIGSTE REGEL IM SYSTEM**

Die Rolle `admin` hat folgende Sonderrechte:

1. **Automatischer Modul-Zugriff**: Admin sieht ALLE aktiven Dashboard-Module, unabhängig von der `ModulZugriff`-Tabelle
2. **Uneingeschränkter Zugriff**: Kann nicht entzogen werden (kein ModulZugriff-Eintrag nötig)
3. **Bypass in Routen**: Routen mit Rollen-Prüfung müssen Admin immer durchlassen

**Code-Implementierung:**

```python
# app/models/modul.py (Zeile 131-133)
@classmethod
def get_dashboard_modules(cls, user=None):
    # ...

    # Admins see all dashboard modules
    if hasattr(user, 'is_admin') and user.is_admin:
        return query.order_by(cls.sort_order).all()
```

**Regel für neue Module:**
- Bei Modul-Aktivierung: Admin bekommt automatisch Zugriff
- Der Zugriff wird NICHT über ModulZugriff gesteuert, sondern ist im Code verankert

### 2.3 Rollen-Eigenschaften (User-Model)

```python
# app/models/user.py
class User(db.Model):
    @property
    def is_admin(self) -> bool:
        return self.rolle and self.rolle.name == 'admin'

    @property
    def is_mitarbeiter(self) -> bool:
        return self.rolle and self.rolle.name in ('admin', 'mitarbeiter')

    @property
    def is_kunde(self) -> bool:
        return self.rolle and self.rolle.name == 'kunde'

    @property
    def is_internal(self) -> bool:
        """True if user is admin or mitarbeiter (internal staff)."""
        return self.rolle and self.rolle.name in ('admin', 'mitarbeiter')
```

### 2.4 Menü-Sichtbarkeit

| Menüpunkt | admin | mitarbeiter | kunde |
|-----------|:-----:|:-----------:|:-----:|
| Dashboard | ✓ | ✓ | ✓ |
| PRICAT Konverter | ✓ | ✓ | ✗ |
| Lead- & Kundenreport | ✓ | ✓ | ✗ |
| Meine Lieferanten | ✓ | ✓ | ✓ |
| Content Generator | ✓ | ✓ | ✓ |
| Kunden-Dialog | ✓ | ✓ | ✓ |
| Administration | ✓ | ✗ | ✗ |
| DB Admin (/db-admin) | ✓ | ✗ | ✗ |

---

## 3. Modul-Zugriffskontrolle

### 3.1 ModulZugriff-Tabelle

Die Tabelle `modul_zugriff` verknüpft Rollen mit Modulen:

```python
class ModulZugriff(db.Model):
    __tablename__ = 'modul_zugriff'

    id = db.Column(db.Integer, primary_key=True)
    modul_id = db.Column(db.Integer, db.ForeignKey('modul.id'))
    rolle_id = db.Column(db.Integer, db.ForeignKey('rolle.id'))
```

**Wichtig:** Diese Tabelle wird für **alle Rollen außer Admin** verwendet. Admins umgehen diese Prüfung (siehe 2.2).

### 3.2 Modul-Typen

| Typ | Beschreibung | Für Rolle `kunde` sichtbar? |
|-----|--------------|:---------------------------:|
| `basis` | Systemmodule (Auth, Logging) | - (nicht auf Dashboard) |
| `kundenprojekt` | Kundenspezifische Module | ✓ (wenn ModulZugriff) |
| `sales_intern` | Nur für Sales-Team | ✗ |
| `consulting_intern` | Nur für Consulting | ✗ |
| `premium` | Premium-Module | ✓ (wenn ModulZugriff) |

**Code:** `app/models/modul.py` - `ModulTyp` Enum

### 3.3 Standard-Modul-Zuweisungen (Seed)

| Modul-Code | admin | mitarbeiter | kunde |
|------------|:-----:|:-----------:|:-----:|
| `pricat` | ✓ | ✓ | ✗ |
| `kunden` | ✓ | ✓ | ✗ |
| `lieferanten` | ✓ | ✓ | ✓ |
| `content` | ✓ | ✓ | ✓ |
| `dialog` | ✓ | ✓ | ✓ |

**Hinweis:** Admin-Einträge existieren als Dokumentation, werden aber nicht geprüft (siehe 2.2).

---

## 4. Branchenrollen (Geschäftsmodell-Ebene)

Branchenrollen sind **unabhängig** von Benutzer-Rollen und definieren die Geschäftsbeziehung eines Kunden.

> Siehe [PRD_Branchenmodell_V2.md](PRD_Branchenmodell_V2.md) für vollständige Dokumentation.

### 4.1 Übersicht

| Branchenrolle | Beschreibung |
|---------------|--------------|
| `Händler` | Kauft und verkauft Waren |
| `Hersteller` | Produziert Waren |
| `Großhändler` | Verkauft an Händler |
| `Verbandsmitglied` | Gehört zu Verband |
| `Dienstleister` | Bietet Services an |

### 4.2 Zuweisung

- Ein Kunde kann **mehrere Branchenrollen** haben (n:m über `kunde_branchenrolle`)
- Branchenrollen beeinflussen **nicht** den Plattform-Zugriff
- Branchenrollen werden für Filterung und Segmentierung verwendet

---

## 5. API-Autorisierung (Decorators)

### 5.1 Decorator-Übersicht

| Decorator | Erlaubte Rollen | Verwendung |
|-----------|-----------------|------------|
| `@login_required` | Alle authentifizierten | Standard für geschützte Seiten |
| `@mitarbeiter_required` | admin, mitarbeiter | Interne Funktionen |
| `@admin_required` | admin | Administration, DB-Admin |

**Implementierung:** `app/routes/auth.py`

### 5.2 Route-Konventionen

```python
# Nur authentifizierte Benutzer
@dialog_bp.route('/')
@login_required
def index():
    pass

# Nur interne Mitarbeiter (admin + mitarbeiter)
@dialog_admin_bp.before_request
def check_access():
    if not current_user.is_internal:
        abort(403)

# Nur Admin
@admin_bp.route('/settings')
@admin_required
def settings():
    pass
```

### 5.3 Admin-Endpunkte

| Route-Prefix | Decorator/Check | Beschreibung |
|--------------|-----------------|--------------|
| `/admin/*` | `@admin_required` | Administration |
| `/admin/dialog/*` | `is_internal` | Fragebogen-Verwaltung |
| `/db-admin/*` | Flask-Admin Auth | Datenbank-Admin |

---

## 6. Sicherheitsregeln

### 6.1 Unveränderliche Regeln

1. **Admin-Bypass darf nicht umgangen werden**
   - Alle Modul-Zugriffsprüfungen müssen Admin durchlassen
   - Bei neuen Routen: Immer Admin-Check einbauen

2. **Externe Rollen können keine internen Module sehen**
   - `ModulTyp.SALES_INTERN` und `CONSULTING_INTERN` sind für `kunde` nicht sichtbar
   - Prüfung in `Modul.ist_intern`

3. **Interne Mitarbeiter-Ansicht**
   - Routen, die sowohl für Kunden als auch interne Nutzer sind, müssen unterschiedliche Views rendern
   - Beispiel: `/dialog/` zeigt Kunden nur eigene Fragebögen, Admin/Mitarbeiter alle

### 6.2 DSGVO-Konformität

- User-IDs bleiben bei Löschung erhalten (für Audit-Log)
- Personenbezogene Daten werden anonymisiert, nicht gelöscht
- Audit-Log-Einträge sind nicht löschbar

---

## 7. Implementierungshinweise

### 7.1 Neue Module hinzufügen

1. Modul in Seed-Daten hinzufügen (`app/__init__.py`)
2. ModulZugriff für gewünschte Rollen definieren (außer Admin)
3. Route mit passender Zugriffsprüfung erstellen
4. Bei gemischten Routen: Admin/Mitarbeiter-Bypass einbauen

```python
# Beispiel: Gemischte Route
@blueprint.route('/')
@login_required
def index():
    if current_user.is_admin or current_user.is_mitarbeiter:
        # Admin/Mitarbeiter sehen alles
        return render_template('modul/index_internal.html', ...)

    # Kunde sieht nur eigene Daten
    return render_template('modul/index.html', ...)
```

### 7.2 Checkliste für Routen

- [ ] `@login_required` oder spezifischerer Decorator?
- [ ] Admin-Bypass für gemischte Routen?
- [ ] Interne vs. externe View getrennt?
- [ ] Korrekte Redirect-Ziele bei 403?

---

## 8. Verwandte Dokumente

| Dokument | Inhalt |
|----------|--------|
| [PRD_BASIS_MVP.md](PRD_BASIS_MVP.md) | Übersicht Tech-Stack, Projekt |
| [PRD_BASIS_MODULVERWALTUNG.md](PRD_BASIS_MODULVERWALTUNG.md) | Modul-Model, Dashboard-Integration |
| [PRD_Branchenmodell_V2.md](PRD_Branchenmodell_V2.md) | Branchenrollen-Hierarchie |

---

## Changelog

| Datum | Version | Änderung |
|-------|---------|----------|
| 2025-12-21 | 1.0 | Initiale Version - Konsolidierung aus CLAUDE.md, PRD_BASIS_MVP.md, PRD_BASIS_MODULVERWALTUNG.md |
