"""Branche (Industry/Sector) model.

Unterstuetzt 2-stufige Hierarchie:
- Hauptbranche (parent_id=NULL): z.B. HANDEL, DIENSTLEISTUNG, HANDWERK
- Unterbranche (parent_id!=NULL): z.B. Spielwaren, Modellbahn unter HANDEL
"""
from uuid import uuid4

from app import db


class Branche(db.Model):
    """Industry/Sector for categorizing customers.

    Hierarchische Struktur:
    - Hauptbranchen haben parent_id=NULL (z.B. HANDEL)
    - Unterbranchen haben parent_id gesetzt (z.B. Spielwaren unter HANDEL)

    Jede Branche hat eine UUID für externe Datenintegration (z.B. unternehmensdaten.org).
    """
    __tablename__ = 'branche'

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False,
                     default=lambda: str(uuid4()))

    # Hierarchie: NULL = Hauptbranche, sonst = Unterbranche
    parent_id = db.Column(db.Integer, db.ForeignKey('branche.id'), nullable=True)

    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(100), nullable=True)  # Für URLs, z.B. "handel-spielwaren"
    icon = db.Column(db.String(50), nullable=False)  # Tabler Icon name (e.g., "train", "lego")
    aktiv = db.Column(db.Boolean, default=True)
    sortierung = db.Column(db.Integer, default=0)

    # Self-referential relationship für Hierarchie
    parent = db.relationship(
        'Branche',
        remote_side=[id],
        backref=db.backref('unterbranchen', lazy='dynamic')
    )

    # Relationship to KundeBranche (bestehend)
    kunden = db.relationship('KundeBranche', back_populates='branche',
                             cascade='all, delete-orphan')

    # Relationship zu zulaessigen Rollen
    zulaessige_rollen = db.relationship(
        'BrancheBranchenRolle',
        back_populates='branche',
        cascade='all, delete-orphan'
    )

    # Unique Constraint: Name muss pro Ebene eindeutig sein
    # (gleicher Name unter verschiedenen Hauptbranchen erlaubt)
    __table_args__ = (
        db.UniqueConstraint('parent_id', 'name', name='uq_branche_parent_name'),
    )

    @property
    def ist_hauptbranche(self):
        """True wenn diese Branche eine Hauptbranche ist (parent_id=NULL)."""
        return self.parent_id is None

    @property
    def zulaessige_branchenrollen(self):
        """Gibt Liste der zulässigen BranchenRolle-Objekte zurück (nur aktive)."""
        return [
            zbr.branchenrolle
            for zbr in self.zulaessige_rollen
            if zbr.branchenrolle.aktiv
        ]

    @property
    def voller_name(self):
        """Gibt den vollen hierarchischen Namen zurück (z.B. 'HANDEL > Spielwaren')."""
        if self.parent:
            return f'{self.parent.name} > {self.name}'
        return self.name

    def __repr__(self):
        return f'<Branche {self.name}>'

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'parent_id': self.parent_id,
            'name': self.name,
            'slug': self.slug,
            'icon': self.icon,
            'aktiv': self.aktiv,
            'sortierung': self.sortierung,
            'ist_hauptbranche': self.ist_hauptbranche,
        }
