"""Marke (Brand) Model."""
from datetime import datetime
from app import db


class Marke(db.Model):
    """Brand entity from VEDES PRICAT."""

    __tablename__ = 'marke'

    id = db.Column(db.Integer, primary_key=True)
    kurzbezeichnung = db.Column(db.String(40), nullable=False)
    gln_evendo = db.Column(db.String(20), unique=True, nullable=False, index=True)
    hersteller_id = db.Column(db.Integer, db.ForeignKey('hersteller.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Marke {self.kurzbezeichnung}>'

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'kurzbezeichnung': self.kurzbezeichnung,
            'gln_evendo': self.gln_evendo,
            'hersteller_id': self.hersteller_id
        }

    @staticmethod
    def generate_gln_evendo(hersteller, marke_name):
        """
        Generate unique GLN for brand.
        Format: {Hersteller.GLN}_{running_number}

        Example: 4023017000005_1, 4023017000005_2
        """
        existing_count = Marke.query.filter_by(hersteller_id=hersteller.id).count()
        nummer = existing_count + 1
        return f"{hersteller.gln}_{nummer}"
