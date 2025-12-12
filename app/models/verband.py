"""Verband (Association/Federation) model."""
from app import db


class Verband(db.Model):
    """Trade association or federation for customers."""
    __tablename__ = 'verband'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    kuerzel = db.Column(db.String(20))  # e.g., "VEDES", "EK"
    logo_url = db.Column(db.String(500))  # External URL (fallback)
    logo_thumb = db.Column(db.String(255))  # Local thumbnail path
    website_url = db.Column(db.String(500))
    aktiv = db.Column(db.Boolean, default=True)

    # Relationship to KundeVerband
    kunden = db.relationship('KundeVerband', back_populates='verband',
                             cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Verband {self.name}>'

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'kuerzel': self.kuerzel,
            'logo_url': self.logo_url,
            'logo_thumb': self.logo_thumb,
            'website_url': self.website_url,
            'aktiv': self.aktiv,
        }
