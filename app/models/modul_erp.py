"""ModulErp model for ERP/Shop module references (PRD011-T052).

ModulErp represents bookable function modules of the e-vendo ERP/Shop system.
These are NOT the same as ev247 Modul entries (which represent app areas with
access control). ModulErp entries are used to link customer project components
to specific ERP functionality.
"""
from datetime import datetime
from enum import Enum
from app import db


class ModulErpKontext(str, Enum):
    """Context where the ERP module is available."""
    ERP = 'erp'
    SHOP = 'shop'
    BEIDES = 'beides'

    @classmethod
    def choices(cls):
        """Return list of (value, label) tuples for form selects."""
        labels = {
            cls.ERP: 'ERP',
            cls.SHOP: 'Shop',
            cls.BEIDES: 'ERP & Shop',
        }
        return [(t.value, labels[t]) for t in cls]


class ModulErp(db.Model):
    """Represents a bookable ERP/Shop module from e-vendo.

    These modules can be linked to customer project components of type
    'modul_erp' to track which ERP functionality the customer
    is requesting customizations for.
    """
    __tablename__ = 'modul_erp'

    id = db.Column(db.Integer, primary_key=True)

    # Identification
    artikelnummer = db.Column(db.String(50), unique=True, nullable=False)
    bezeichnung = db.Column(db.String(200), nullable=False)

    # PRD011-T054: Icon for visual representation in dropdowns
    icon = db.Column(db.String(50), default='ti-plug')

    # Context
    kontext = db.Column(db.String(20), default=ModulErpKontext.ERP.value, nullable=False)

    # Optional details
    beschreibung = db.Column(db.Text, nullable=True)

    # Status
    aktiv = db.Column(db.Boolean, default=True, nullable=False)
    sortierung = db.Column(db.Integer, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    komponenten = db.relationship(
        'Komponente',
        backref='erp_modul',
        lazy='dynamic'
    )

    def __repr__(self):
        return f'<ModulErp {self.artikelnummer}: {self.bezeichnung}>'

    @property
    def kontext_label(self):
        """Return display label for context."""
        for value, label in ModulErpKontext.choices():
            if value == self.kontext:
                return label
        return self.kontext

    @property
    def anzahl_komponenten(self):
        """Return number of linked components."""
        return self.komponenten.count()

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'artikelnummer': self.artikelnummer,
            'bezeichnung': self.bezeichnung,
            'icon': self.icon,
            'kontext': self.kontext,
            'kontext_label': self.kontext_label,
            'beschreibung': self.beschreibung,
            'aktiv': self.aktiv,
            'sortierung': self.sortierung,
            'anzahl_komponenten': self.anzahl_komponenten,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
