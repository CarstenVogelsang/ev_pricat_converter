"""Branche (Industry/Sector) model."""
from app import db


class Branche(db.Model):
    """Industry/Sector for categorizing customers."""
    __tablename__ = 'branche'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    icon = db.Column(db.String(50), nullable=False)  # Tabler Icon name (e.g., "train", "lego")
    aktiv = db.Column(db.Boolean, default=True)
    sortierung = db.Column(db.Integer, default=0)

    # Relationship to KundeBranche
    kunden = db.relationship('KundeBranche', back_populates='branche',
                             cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Branche {self.name}>'

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'icon': self.icon,
            'aktiv': self.aktiv,
            'sortierung': self.sortierung,
        }
