"""BranchenRolle (Industry Role) model.

Rollen-Katalog für Branchen, z.B. HERSTELLER, EINZELHANDEL_ONLINE, etc.
Diese Rollen können Kunden pro Branche zugewiesen werden.
"""
from uuid import uuid4

from app import db


class BranchenRolle(db.Model):
    """Rollen-Katalog für Branchen (z.B. HERSTELLER, EINZELHANDEL_ONLINE).

    Beispiele für Rollen:
    - HERSTELLER: Produziert eigene Produkte
    - GROSSHAENDLER: Vertreibt an Wiederverkäufer
    - FILIALIST: Betreibt mehrere Filialen
    - EINZELHANDEL_STATIONAER: Ladengeschäft
    - EINZELHANDEL_ONLINE: Reiner Online-Shop
    - EINZELHANDEL_OMNICHANNEL: Stationär + Online
    """
    __tablename__ = 'branchenrolle'

    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False,
                     default=lambda: str(uuid4()))
    code = db.Column(db.String(50), unique=True, nullable=False)  # z.B. EINZELHANDEL_ONLINE
    name = db.Column(db.String(100), nullable=False)              # z.B. "Einzelhandel Online"
    icon = db.Column(db.String(50))                               # Tabler Icon für Anzeige
    beschreibung = db.Column(db.Text)
    aktiv = db.Column(db.Boolean, default=True)
    sortierung = db.Column(db.Integer, default=0)

    # Relationships
    # Branchen, in denen diese Rolle zulaessig ist
    zulaessig_in_branchen = db.relationship(
        'BrancheBranchenRolle',
        back_populates='branchenrolle',
        cascade='all, delete-orphan'
    )

    # Kunden, die diese Rolle haben
    kunden_mit_rolle = db.relationship(
        'KundeBranchenRolle',
        back_populates='branchenrolle',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<BranchenRolle {self.code}>'

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'code': self.code,
            'name': self.name,
            'icon': self.icon,
            'beschreibung': self.beschreibung,
            'aktiv': self.aktiv,
            'sortierung': self.sortierung,
        }
