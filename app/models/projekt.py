"""Projekt model for project management (PRD-011).

A Projekt is the top-level container for components (PRDs/modules).
It can be either internal (ev247 platform development) or customer-specific.
"""
from datetime import datetime
from enum import Enum
from app import db


class ProjektTyp(str, Enum):
    """Project types for categorization."""
    INTERN = 'intern'      # Internal projects (ev247 platform)
    KUNDE = 'kunde'        # Customer projects (consulting)

    @classmethod
    def choices(cls):
        """Return list of (value, label) tuples for form selects."""
        labels = {
            cls.INTERN: 'Intern',
            cls.KUNDE: 'Kundenprojekt',
        }
        return [(t.value, labels[t]) for t in cls]


class Projekt(db.Model):
    """Represents a project in the project management system.

    A project contains multiple components (PRDs/modules) and can be
    either internal (ev247 development) or customer-specific.
    """
    __tablename__ = 'projekt'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    beschreibung = db.Column(db.Text, nullable=True)
    typ = db.Column(db.String(20), default=ProjektTyp.INTERN.value, nullable=False)

    # Optional reference to customer (for customer projects)
    kunde_id = db.Column(db.Integer, db.ForeignKey('kunde.id'), nullable=True)

    # Status
    aktiv = db.Column(db.Boolean, default=True, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    komponenten = db.relationship(
        'Komponente',
        backref='projekt',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='Komponente.sortierung'
    )
    kunde = db.relationship('Kunde', backref=db.backref('projekte', lazy='dynamic'))

    def __repr__(self):
        return f'<Projekt {self.name}>'

    @property
    def ist_kundenprojekt(self):
        """Check if this is a customer project."""
        return self.typ == ProjektTyp.KUNDE.value

    @property
    def anzahl_komponenten(self):
        """Return number of components in this project."""
        return self.komponenten.count()

    @property
    def aktive_komponenten(self):
        """Return active components."""
        return self.komponenten.filter_by(status='aktiv').all()

    def to_dict(self, include_komponenten=False):
        """Return dictionary representation.

        Args:
            include_komponenten: If True, include list of component summaries
        """
        result = {
            'id': self.id,
            'name': self.name,
            'beschreibung': self.beschreibung,
            'typ': self.typ,
            'kunde_id': self.kunde_id,
            'aktiv': self.aktiv,
            'anzahl_komponenten': self.anzahl_komponenten,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_komponenten:
            result['komponenten'] = [k.to_dict() for k in self.aktive_komponenten]
        return result
