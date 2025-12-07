"""Kunde (Customer) and KundeCI (Corporate Identity) models."""
from datetime import datetime

from app import db


class Kunde(db.Model):
    """Customer/Lead model for Lead&Kundenreport app."""
    __tablename__ = 'kunde'

    id = db.Column(db.Integer, primary_key=True)
    firmierung = db.Column(db.String(200), nullable=False)
    adresse = db.Column(db.Text)
    website_url = db.Column(db.String(500))
    shop_url = db.Column(db.String(500))
    notizen = db.Column(db.Text)
    aktiv = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationship to KundeCI (1:1)
    ci = db.relationship('KundeCI', backref='kunde', uselist=False,
                         cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Kunde {self.firmierung}>'

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'firmierung': self.firmierung,
            'adresse': self.adresse,
            'website_url': self.website_url,
            'shop_url': self.shop_url,
            'notizen': self.notizen,
            'aktiv': self.aktiv,
            'has_ci': self.ci is not None,
        }


class KundeCI(db.Model):
    """Corporate Identity data from Firecrawl analysis."""
    __tablename__ = 'kunde_ci'

    id = db.Column(db.Integer, primary_key=True)
    kunde_id = db.Column(db.Integer, db.ForeignKey('kunde.id'), unique=True, nullable=False)

    # Firecrawl branding results
    logo_url = db.Column(db.String(500))
    primary_color = db.Column(db.String(20))
    secondary_color = db.Column(db.String(20))
    accent_color = db.Column(db.String(20))
    background_color = db.Column(db.String(20))
    text_primary_color = db.Column(db.String(20))
    text_secondary_color = db.Column(db.String(20))

    # Metadata
    analysiert_am = db.Column(db.DateTime)
    analyse_url = db.Column(db.String(500))
    raw_response = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<KundeCI kunde_id={self.kunde_id}>'

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'kunde_id': self.kunde_id,
            'logo_url': self.logo_url,
            'primary_color': self.primary_color,
            'secondary_color': self.secondary_color,
            'accent_color': self.accent_color,
            'background_color': self.background_color,
            'text_primary_color': self.text_primary_color,
            'text_secondary_color': self.text_secondary_color,
            'analysiert_am': self.analysiert_am.isoformat() if self.analysiert_am else None,
            'analyse_url': self.analyse_url,
        }
