"""API Usage Tracking Model."""
from datetime import datetime
from decimal import Decimal

from app import db


class KundeApiNutzung(db.Model):
    """Track API costs per customer and user."""

    __tablename__ = 'kunde_api_nutzung'

    id = db.Column(db.Integer, primary_key=True)
    kunde_id = db.Column(
        db.Integer, db.ForeignKey('kunde.id'), nullable=False, index=True
    )
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id'), nullable=False, index=True
    )

    # API Details
    api_service = db.Column(db.String(50), nullable=False)  # e.g. "firecrawl"
    api_endpoint = db.Column(db.String(100), nullable=False)  # e.g. "scrape/branding"

    # Costs
    credits_used = db.Column(db.Integer, nullable=False, default=1)
    kosten_euro = db.Column(db.Numeric(10, 4), nullable=False)  # 4 decimal places for 0.005

    # Description
    beschreibung = db.Column(db.String(255))

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationships
    kunde = db.relationship(
        'Kunde', backref=db.backref('api_nutzungen', lazy='dynamic')
    )
    user = db.relationship(
        'User', backref=db.backref('api_nutzungen', lazy='dynamic')
    )

    def __repr__(self):
        return f'<KundeApiNutzung {self.api_service}:{self.api_endpoint}>'

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'kunde_id': self.kunde_id,
            'user_id': self.user_id,
            'api_service': self.api_service,
            'api_endpoint': self.api_endpoint,
            'credits_used': self.credits_used,
            'kosten_euro': float(self.kosten_euro),
            'beschreibung': self.beschreibung,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
