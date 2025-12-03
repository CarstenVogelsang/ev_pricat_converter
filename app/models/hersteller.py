"""Hersteller (Manufacturer) Model."""
from datetime import datetime
from app import db


class Hersteller(db.Model):
    """Manufacturer entity from VEDES PRICAT."""

    __tablename__ = 'hersteller'

    id = db.Column(db.Integer, primary_key=True)
    gln = db.Column(db.String(13), unique=True, nullable=False, index=True)
    vedes_id = db.Column(db.String(13), unique=True, index=True)
    kurzbezeichnung = db.Column(db.String(40), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationship to Marke
    marken = db.relationship('Marke', backref='hersteller', lazy='dynamic')

    def __repr__(self):
        return f'<Hersteller {self.kurzbezeichnung}>'

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'gln': self.gln,
            'vedes_id': self.vedes_id,
            'kurzbezeichnung': self.kurzbezeichnung
        }
