"""Junction table for Kunde-User N:M relationship with Hauptbenutzer flag."""
from datetime import datetime

from app import db


class KundeBenutzer(db.Model):
    """Association table linking Kunde to User with Hauptbenutzer designation.

    A Kunde can have multiple Users, but exactly one should be marked
    as ist_hauptbenutzer=True (the primary contact for questionnaires etc.)
    """
    __tablename__ = 'kunde_benutzer'

    id = db.Column(db.Integer, primary_key=True)
    kunde_id = db.Column(db.Integer, db.ForeignKey('kunde.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ist_hauptbenutzer = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Unique constraint: A user can only be assigned once per Kunde
    __table_args__ = (
        db.UniqueConstraint('kunde_id', 'user_id', name='uq_kunde_benutzer'),
    )

    # Relationships
    kunde = db.relationship('Kunde', back_populates='benutzer_zuordnungen')
    user = db.relationship('User', back_populates='kunde_zuordnungen')

    def __repr__(self):
        hauptbenutzer_str = ' (Haupt)' if self.ist_hauptbenutzer else ''
        return f'<KundeBenutzer kunde={self.kunde_id} user={self.user_id}{hauptbenutzer_str}>'
