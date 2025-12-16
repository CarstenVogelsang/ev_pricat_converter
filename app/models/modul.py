"""Modul model - Unified module management for ev247 platform.

Combines dashboard UI (former SubApp) and logging functionality.
See PRD_BASIS_MODULVERWALTUNG.md for full documentation.

Modul-Typen:
- BASIS: System-Module (Auth, Logging, etc.) - immer aktiv
- KUNDENPROJEKT: Kunden-spezifische Module
- SALES_INTERN: Nur für Sales-Team (intern)
- CONSULTING_INTERN: Nur für Consulting (intern)
- PREMIUM: Premium-Module
"""
from datetime import datetime
from enum import Enum
from app import db


class ModulTyp(str, Enum):
    """Module types for categorization and access control.

    Internal types (SALES_INTERN, CONSULTING_INTERN) should not be
    accessible to external roles like 'Kunde'.
    """
    BASIS = 'basis'                    # System modules (always active)
    KUNDENPROJEKT = 'kundenprojekt'    # Customer-specific modules
    SALES_INTERN = 'sales_intern'      # Internal: Sales team only
    CONSULTING_INTERN = 'consulting_intern'  # Internal: Consulting only
    PREMIUM = 'premium'                # Premium modules

    @classmethod
    def choices(cls):
        """Return list of (value, label) tuples for form selects."""
        labels = {
            cls.BASIS: 'Basis',
            cls.KUNDENPROJEKT: 'Kundenprojekt',
            cls.SALES_INTERN: 'Sales (intern)',
            cls.CONSULTING_INTERN: 'Consulting (intern)',
            cls.PREMIUM: 'Premium',
        }
        return [(t.value, labels[t]) for t in cls]

    @classmethod
    def interne_typen(cls):
        """Return list of internal type values (not for external roles)."""
        return [cls.SALES_INTERN.value, cls.CONSULTING_INTERN.value]


class Modul(db.Model):
    """Represents a module in the ev247 platform.

    This unified model replaces the former SubApp model and provides:
    - Dashboard display (icon, color, route)
    - Audit logging reference
    - Role-based access control (via ModulZugriff)
    - Activation/deactivation (except basis modules)
    - Module type categorization (BASIS, KUNDENPROJEKT, etc.)

    Basis-Module (typ='basis') are always active and cannot be deactivated.
    They don't appear on the dashboard (zeige_dashboard=False).

    Internal types (SALES_INTERN, CONSULTING_INTERN) cannot be assigned
    to external roles like 'Kunde'.
    """
    __tablename__ = 'modul'

    id = db.Column(db.Integer, primary_key=True)

    # Identification
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    beschreibung = db.Column(db.Text, nullable=True)

    # UI properties (from former SubApp)
    icon = db.Column(db.String(50), default='ti-package')
    color = db.Column(db.String(20), default='primary')  # Bootstrap class
    color_hex = db.Column(db.String(7), default='#0d6efd')  # Hex color for icon
    route_endpoint = db.Column(db.String(100), nullable=True)  # Flask endpoint
    sort_order = db.Column(db.Integer, default=0)

    # Module type and status
    typ = db.Column(db.String(30), default=ModulTyp.BASIS.value)  # Module type
    zeige_dashboard = db.Column(db.Boolean, default=True)  # Show on dashboard
    aktiv = db.Column(db.Boolean, default=True)

    @property
    def ist_basis(self):
        """Backwards-compatible property: True if module is BASIS type."""
        return self.typ == ModulTyp.BASIS.value

    @property
    def ist_intern(self):
        """True if module is an internal type (not for external roles)."""
        return self.typ in ModulTyp.interne_typen()

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    zugriffe = db.relationship('ModulZugriff', backref='modul',
                               lazy='dynamic', cascade='all, delete-orphan')
    audit_logs = db.relationship('AuditLog', backref='modul', lazy='dynamic')

    def __repr__(self):
        return f'<Modul {self.code}>'

    @classmethod
    def get_by_code(cls, code: str) -> 'Modul':
        """Get a module by its code."""
        return cls.query.filter_by(code=code).first()

    @classmethod
    def get_dashboard_modules(cls, user=None):
        """Get all modules visible on dashboard.

        Args:
            user: Optional user to filter by role access

        Returns:
            List of active modules that should appear on dashboard
        """
        from flask_login import current_user

        query = cls.query.filter(
            cls.aktiv == True,
            cls.zeige_dashboard == True
        )

        if user is None:
            user = current_user

        # Admins see all dashboard modules
        if hasattr(user, 'is_admin') and user.is_admin:
            return query.order_by(cls.sort_order).all()

        # Other users only see modules they have access to
        if hasattr(user, 'rolle_id') and user.rolle_id:
            query = query.filter(
                cls.id.in_(
                    db.session.query(ModulZugriff.modul_id)
                    .filter(ModulZugriff.rolle_id == user.rolle_id)
                )
            )

        return query.order_by(cls.sort_order).all()

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'beschreibung': self.beschreibung,
            'icon': self.icon,
            'color': self.color,
            'color_hex': self.color_hex,
            'route_endpoint': self.route_endpoint,
            'sort_order': self.sort_order,
            'typ': self.typ,
            'ist_basis': self.ist_basis,  # computed property
            'ist_intern': self.ist_intern,  # computed property
            'zeige_dashboard': self.zeige_dashboard,
            'aktiv': self.aktiv,
        }


class ModulZugriff(db.Model):
    """Role-based module access control.

    Determines which roles have access to which modules.
    Replaces the former SubAppAccess model.
    """
    __tablename__ = 'modul_zugriff'

    id = db.Column(db.Integer, primary_key=True)
    modul_id = db.Column(db.Integer, db.ForeignKey('modul.id'), nullable=False)
    rolle_id = db.Column(db.Integer, db.ForeignKey('rolle.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to Rolle
    rolle = db.relationship('Rolle', backref=db.backref('modul_zugriffe', lazy='dynamic'))

    __table_args__ = (
        db.UniqueConstraint('modul_id', 'rolle_id', name='uq_modul_rolle'),
    )

    def __repr__(self):
        return f'<ModulZugriff modul={self.modul_id} rolle={self.rolle_id}>'
