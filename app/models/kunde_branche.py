"""KundeBranche (Customer-Industry association) model."""
from app import db


class KundeBranche(db.Model):
    """Association table between Kunde and Branche with additional fields."""
    __tablename__ = 'kunde_branche'

    id = db.Column(db.Integer, primary_key=True)
    kunde_id = db.Column(db.Integer, db.ForeignKey('kunde.id'), nullable=False)
    branche_id = db.Column(db.Integer, db.ForeignKey('branche.id'), nullable=False)
    ist_primaer = db.Column(db.Boolean, default=False)  # Max 3 per customer

    # Relationships
    kunde = db.relationship('Kunde', back_populates='branchen')
    branche = db.relationship('Branche', back_populates='kunden')

    # Unique constraint: one entry per kunde-branche combination
    __table_args__ = (
        db.UniqueConstraint('kunde_id', 'branche_id', name='uq_kunde_branche'),
    )

    def __repr__(self):
        return f'<KundeBranche kunde_id={self.kunde_id} branche_id={self.branche_id}>'
