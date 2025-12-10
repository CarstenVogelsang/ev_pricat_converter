"""KundeVerband (Customer-Association membership) model."""
from app import db


class KundeVerband(db.Model):
    """Association table between Kunde and Verband."""
    __tablename__ = 'kunde_verband'

    id = db.Column(db.Integer, primary_key=True)
    kunde_id = db.Column(db.Integer, db.ForeignKey('kunde.id'), nullable=False)
    verband_id = db.Column(db.Integer, db.ForeignKey('verband.id'), nullable=False)

    # Relationships
    kunde = db.relationship('Kunde', back_populates='verbaende')
    verband = db.relationship('Verband', back_populates='kunden')

    # Unique constraint: one entry per kunde-verband combination
    __table_args__ = (
        db.UniqueConstraint('kunde_id', 'verband_id', name='uq_kunde_verband'),
    )

    def __repr__(self):
        return f'<KundeVerband kunde_id={self.kunde_id} verband_id={self.verband_id}>'
