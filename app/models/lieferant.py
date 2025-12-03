"""Lieferant (Supplier) Model."""
from datetime import datetime
from app import db


class Lieferant(db.Model):
    """Supplier entity from VEDES PRICAT."""

    __tablename__ = 'lieferant'

    id = db.Column(db.Integer, primary_key=True)
    gln = db.Column(db.String(13), unique=True, nullable=False, index=True)
    vedes_id = db.Column(db.String(13), unique=True, nullable=False, index=True)
    kurzbezeichnung = db.Column(db.String(40), nullable=False)
    aktiv = db.Column(db.Boolean, default=True, nullable=False)
    ftp_pfad_quelle = db.Column(db.String(255))
    ftp_pfad_ziel = db.Column(db.String(255))
    elena_startdir = db.Column(db.String(50))
    elena_base_url = db.Column(db.String(255))
    letzte_konvertierung = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Lieferant {self.kurzbezeichnung}>'

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'gln': self.gln,
            'vedes_id': self.vedes_id,
            'kurzbezeichnung': self.kurzbezeichnung,
            'aktiv': self.aktiv,
            'ftp_pfad_quelle': self.ftp_pfad_quelle,
            'ftp_pfad_ziel': self.ftp_pfad_ziel,
            'elena_startdir': self.elena_startdir,
            'elena_base_url': self.elena_base_url,
            'letzte_konvertierung': self.letzte_konvertierung.isoformat() if self.letzte_konvertierung else None
        }
