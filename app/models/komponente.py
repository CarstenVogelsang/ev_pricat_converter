"""Komponente model for project management (PRD-011).

A Komponente represents a PRD/module/entity within a project.
It stores the PRD content as Markdown and tracks development phases.
"""
from datetime import datetime
from enum import Enum
from app import db


class KomponenteTyp(str, Enum):
    """Component types for categorization.

    - MODUL: Standalone module with menu entry (links to Modul table)
    - BASISFUNKTION: Cross-cutting functionality (core features)
    - ENTITY: Data model with CRUD operations
    """
    MODUL = 'modul'                  # Standalone module with menu entry
    BASISFUNKTION = 'basisfunktion'  # Cross-cutting functionality
    ENTITY = 'entity'                # Data model/entity

    @classmethod
    def choices(cls):
        """Return list of (value, label) tuples for form selects."""
        labels = {
            cls.MODUL: 'Modul',
            cls.BASISFUNKTION: 'Basisfunktion',
            cls.ENTITY: 'Entity/Stammdaten',
        }
        return [(t.value, labels[t]) for t in cls]


class KomponentePhase(str, Enum):
    """Development phases for components."""
    POC = 'poc'      # Proof of Concept
    MVP = 'mvp'      # Minimum Viable Product
    V1 = 'v1'        # Version 1.0
    V2 = 'v2'        # Version 2.0
    V3 = 'v3'        # Version 3.0

    @classmethod
    def choices(cls):
        """Return list of (value, label) tuples for form selects."""
        labels = {
            cls.POC: 'POC (Proof of Concept)',
            cls.MVP: 'MVP (Minimum Viable Product)',
            cls.V1: 'V1',
            cls.V2: 'V2',
            cls.V3: 'V3',
        }
        return [(t.value, labels[t]) for t in cls]


class KomponenteStatus(str, Enum):
    """Status of a component."""
    AKTIV = 'aktiv'
    ARCHIVIERT = 'archiviert'

    @classmethod
    def choices(cls):
        """Return list of (value, label) tuples for form selects."""
        labels = {
            cls.AKTIV: 'Aktiv',
            cls.ARCHIVIERT: 'Archiviert',
        }
        return [(t.value, labels[t]) for t in cls]


class Komponente(db.Model):
    """Represents a component (PRD/module/entity) within a project.

    Components store PRD content as Markdown and can be linked to the
    existing Modul system for role-based access control.
    """
    __tablename__ = 'komponente'

    id = db.Column(db.Integer, primary_key=True)
    projekt_id = db.Column(db.Integer, db.ForeignKey('projekt.id'), nullable=False)

    # Identification
    name = db.Column(db.String(100), nullable=False)
    prd_nummer = db.Column(db.String(10), nullable=True)  # e.g., "011"

    # Component type and optional module reference
    typ = db.Column(db.String(20), default=KomponenteTyp.MODUL.value, nullable=False)
    modul_id = db.Column(db.Integer, db.ForeignKey('modul.id'), nullable=True)

    # ERP module reference for customer projects (PRD011-T052)
    erp_modul_id = db.Column(db.Integer, db.ForeignKey('modul_erp.id'), nullable=True)

    # PRD content
    prd_inhalt = db.Column(db.Text, nullable=True)

    # Development status
    aktuelle_phase = db.Column(db.String(10), default=KomponentePhase.POC.value)
    status = db.Column(db.String(20), default=KomponenteStatus.AKTIV.value)

    # UI properties
    icon = db.Column(db.String(50), default='ti-package')
    sortierung = db.Column(db.Integer, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tasks = db.relationship(
        'Task',
        backref='komponente',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='Task.sortierung'
    )
    changelog_eintraege = db.relationship(
        'ChangelogEintrag',
        backref='komponente',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='ChangelogEintrag.erstellt_am.desc()'
    )
    modul = db.relationship('Modul', backref=db.backref('komponente', uselist=False))

    def __repr__(self):
        return f'<Komponente PRD-{self.prd_nummer} {self.name}>'

    @property
    def prd_bezeichnung(self):
        """Return formatted PRD designation."""
        if self.prd_nummer:
            return f'PRD-{self.prd_nummer}'
        return None

    @property
    def ist_modul(self):
        """Check if this is a module component."""
        return self.typ == KomponenteTyp.MODUL.value

    @property
    def ist_basisfunktion(self):
        """Check if this is a core functionality component."""
        return self.typ == KomponenteTyp.BASISFUNKTION.value

    @property
    def ist_entity(self):
        """Check if this is an entity component."""
        return self.typ == KomponenteTyp.ENTITY.value

    @property
    def typ_icon(self):
        """Return Tabler icon for component type (PRD011-T047)."""
        from app.models import LookupWert
        # For customer projects: use LookupWert
        if self.projekt and self.projekt.ist_kundenprojekt:
            return LookupWert.get_icon('komponente_typ_kunde', self.typ, 'ti-package')
        # For internal projects: static icons
        icons = {
            'modul': 'ti-layout-grid',
            'basisfunktion': 'ti-settings',
            'entity': 'ti-database',
        }
        return icons.get(self.typ, 'ti-package')

    @property
    def typ_label(self):
        """Return display label for component type (PRD011-T047)."""
        from app.models import LookupWert
        if self.projekt and self.projekt.ist_kundenprojekt:
            label = LookupWert.get_wert('komponente_typ_kunde', self.typ)
            if label:
                return label
        # Fallback: Enum-Labels
        for value, label in KomponenteTyp.choices():
            if value == self.typ:
                return label
        return self.typ

    @property
    def typ_farbe(self):
        """Return Bootstrap color for component type (PRD011-T047)."""
        from app.models import LookupWert
        if self.projekt and self.projekt.ist_kundenprojekt:
            return LookupWert.get_farbe('komponente_typ_kunde', self.typ, 'secondary')
        return 'secondary'

    @property
    def erp_modul_bezeichnung(self):
        """Return linked ERP module name if exists (PRD011-T052)."""
        if self.erp_modul:
            return self.erp_modul.bezeichnung
        return None

    @property
    def anzahl_tasks(self):
        """Return number of tasks for this component."""
        return self.tasks.count()

    @property
    def offene_tasks(self):
        """Return tasks that are not completed."""
        return self.tasks.filter(Task.status != 'erledigt').all()

    @property
    def erledigte_tasks(self):
        """Return completed tasks."""
        return self.tasks.filter_by(status='erledigt').all()

    def hat_kunde_zugriff(self):
        """Check if customers have access to this component's module.

        Returns True if:
        - Component is type 'modul'
        - Linked Modul has ModulZugriff for 'kunde' role
        """
        if not self.ist_modul or not self.modul:
            return False

        from app.models.rolle import Rolle
        kunde_rolle = Rolle.query.filter_by(name='kunde').first()
        if not kunde_rolle:
            return False

        return self.modul.zugriffe.filter_by(rolle_id=kunde_rolle.id).first() is not None

    def to_dict(self, include_prd=False, include_tasks=False):
        """Return dictionary representation.

        Args:
            include_prd: If True, include full PRD content
            include_tasks: If True, include task summaries
        """
        result = {
            'id': self.id,
            'projekt_id': self.projekt_id,
            'name': self.name,
            'prd_nummer': self.prd_nummer,
            'prd_bezeichnung': self.prd_bezeichnung,
            'typ': self.typ,
            'typ_icon': self.typ_icon,
            'typ_label': self.typ_label,
            'typ_farbe': self.typ_farbe,
            'modul_id': self.modul_id,
            'erp_modul_id': self.erp_modul_id,
            'erp_modul_bezeichnung': self.erp_modul_bezeichnung,
            'aktuelle_phase': self.aktuelle_phase,
            'status': self.status,
            'icon': self.icon,
            'sortierung': self.sortierung,
            'anzahl_tasks': self.anzahl_tasks,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_prd:
            result['prd_inhalt'] = self.prd_inhalt
        if include_tasks:
            result['tasks'] = [t.to_dict() for t in self.offene_tasks]
        return result
