"""LieferantBranche junction table for M:N relationship between Lieferant and Branche.

A Lieferant can be assigned to up to 3 branches (Unterbranchen of HANDEL).
One branch must be marked as the Hauptbranche (main branch).
"""

from datetime import datetime
from app import db


class LieferantBranche(db.Model):
    """Junction table for Lieferant-Branche relationship.

    Attributes:
        lieferant_id: FK to Lieferant
        branche_id: FK to Branche (only HANDEL sub-branches allowed)
        ist_hauptbranche: Whether this is the main branch (max 1 per Lieferant)
    """
    __tablename__ = 'lieferant_branche'

    id = db.Column(db.Integer, primary_key=True)
    lieferant_id = db.Column(
        db.Integer,
        db.ForeignKey('lieferant.id', ondelete='CASCADE'),
        nullable=False
    )
    branche_id = db.Column(
        db.Integer,
        db.ForeignKey('branche.id', ondelete='CASCADE'),
        nullable=False
    )
    ist_hauptbranche = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    lieferant = db.relationship('Lieferant', back_populates='branchen')
    branche = db.relationship('Branche')

    __table_args__ = (
        db.UniqueConstraint('lieferant_id', 'branche_id', name='uq_lieferant_branche'),
    )

    def __repr__(self):
        return f'<LieferantBranche {self.lieferant_id}->{self.branche_id}>'
