"""Kunde (Customer) and KundeCI (Corporate Identity) models."""
from datetime import datetime

from app import db


class Kunde(db.Model):
    """Customer/Lead model for Lead&Kundenreport app."""
    __tablename__ = 'kunde'

    id = db.Column(db.Integer, primary_key=True)
    firmierung = db.Column(db.String(200), nullable=False)

    # e-vendo customer number
    ev_kdnr = db.Column(db.String(50), unique=True)

    # Structured address fields
    strasse = db.Column(db.String(200))
    plz = db.Column(db.String(20))
    ort = db.Column(db.String(100))
    land = db.Column(db.String(100), default='Deutschland')

    # Legacy address field (kept for migration fallback)
    adresse = db.Column(db.Text)

    website_url = db.Column(db.String(500))
    shop_url = db.Column(db.String(500))
    notizen = db.Column(db.Text)
    aktiv = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Ansprechpartner (User) für Kunden-Portal-Zugang
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, unique=True)
    user = db.relationship('User', backref=db.backref('kunde', uselist=False))

    # Hauptbranche - muss vor Unterbranche-Zuordnung gesetzt sein
    hauptbranche_id = db.Column(db.Integer, db.ForeignKey('branche.id'), nullable=True)
    hauptbranche = db.relationship('Branche', foreign_keys=[hauptbranche_id])

    # Relationship to KundeCI (1:1)
    ci = db.relationship('KundeCI', backref='kunde', uselist=False,
                         cascade='all, delete-orphan')

    # Relationships to Branchen and Verbände (N:M)
    branchen = db.relationship('KundeBranche', back_populates='kunde',
                               cascade='all, delete-orphan')
    verbaende = db.relationship('KundeVerband', back_populates='kunde',
                                cascade='all, delete-orphan')

    # Relationship zu BranchenRollen (N:M ueber KundeBranchenRolle)
    branchenrollen = db.relationship('KundeBranchenRolle', back_populates='kunde',
                                     cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Kunde {self.firmierung}>'

    @property
    def primaer_branchen(self):
        """Get primary branches (max 3)."""
        return [kb.branche for kb in self.branchen if kb.ist_primaer]

    @property
    def alle_branchen(self):
        """Get all assigned branches."""
        return [kb.branche for kb in self.branchen]

    @property
    def alle_verbaende(self):
        """Get all assigned associations."""
        return [kv.verband for kv in self.verbaende]

    @property
    def rollen_pro_branche(self):
        """Dict: branche_id -> Liste von BranchenRolle-Objekten.

        Gibt für jede zugeordnete Branche die Liste der Rollen zurück,
        die der Kunde in dieser Branche hat.
        """
        result = {}
        for kbr in self.branchenrollen:
            if kbr.branche_id not in result:
                result[kbr.branche_id] = []
            result[kbr.branche_id].append(kbr.branchenrolle)
        return result

    @property
    def adresse_formatiert(self):
        """Get formatted address from structured fields or legacy field."""
        if self.strasse or self.plz or self.ort:
            parts = []
            if self.strasse:
                parts.append(self.strasse)
            if self.plz or self.ort:
                city_part = ' '.join(filter(None, [self.plz, self.ort]))
                parts.append(city_part)
            if self.land and self.land != 'Deutschland':
                parts.append(self.land)
            return ', '.join(parts)
        return self.adresse or ''

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'firmierung': self.firmierung,
            'ev_kdnr': self.ev_kdnr,
            'strasse': self.strasse,
            'plz': self.plz,
            'ort': self.ort,
            'land': self.land,
            'adresse': self.adresse,
            'adresse_formatiert': self.adresse_formatiert,
            'website_url': self.website_url,
            'shop_url': self.shop_url,
            'notizen': self.notizen,
            'aktiv': self.aktiv,
            'has_ci': self.ci is not None,
            'branchen': [b.to_dict() for b in self.alle_branchen],
            'verbaende': [v.to_dict() for v in self.alle_verbaende],
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
