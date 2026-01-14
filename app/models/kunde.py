"""Kunde (Customer) and KundeCI (Corporate Identity) models."""
from datetime import datetime
from enum import Enum

from app import db


class KundeTyp(Enum):
    """Type of Kunde record - distinguishes customers from leads."""
    KUNDE = 'kunde'    # Full customer with user accounts
    LEAD = 'lead'      # Prospect without user account (can receive questionnaires via email)


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

    # Contact information (company-level, not user-level)
    telefon = db.Column(db.String(50))
    email = db.Column(db.String(200))

    notizen = db.Column(db.Text)
    aktiv = db.Column(db.Boolean, default=True)

    # Lead vs Kunde distinction - allows tracking prospects without user accounts
    typ = db.Column(db.String(20), nullable=False, default=KundeTyp.KUNDE.value, index=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Email settings
    email_footer = db.Column(db.Text, nullable=True)  # HTML footer for emails
    ist_systemkunde = db.Column(db.Boolean, default=False, nullable=False)  # System default for footer

    # Anrede/Briefanrede settings for email templates
    anrede = db.Column(db.String(20), default='firma')  # herr, frau, divers, firma
    kommunikation_stil = db.Column(db.String(20), default='foermlich')  # foermlich, locker

    # DEPRECATED: Legacy 1:1 user assignment - use benutzer_zuordnungen instead
    # Kept temporarily for migration, will be removed in future version
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, unique=True)
    _legacy_user = db.relationship('User', foreign_keys=[user_id])

    # NEW: 1:N relationship to users via junction table
    benutzer_zuordnungen = db.relationship(
        'KundeBenutzer',
        back_populates='kunde',
        cascade='all, delete-orphan',
        order_by='desc(KundeBenutzer.ist_hauptbenutzer)'
    )

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

    # Mailing opt-out (PRD-013)
    mailing_abgemeldet = db.Column(db.Boolean, default=False, nullable=False)
    mailing_abgemeldet_am = db.Column(db.DateTime, nullable=True)

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
    def hauptbenutzer(self):
        """Return the primary user (Hauptbenutzer) for this Kunde.

        The Hauptbenutzer is the one marked with ist_hauptbenutzer=True.
        Falls back to first assigned user if none is marked.
        Falls back to legacy user_id if no junction entries exist.
        """
        # First check new junction table
        for zuo in self.benutzer_zuordnungen:
            if zuo.ist_hauptbenutzer:
                return zuo.user
        # Fallback: first user in list
        if self.benutzer_zuordnungen:
            return self.benutzer_zuordnungen[0].user
        # Fallback: legacy user_id relationship
        return self._legacy_user

    @property
    def user(self):
        """DEPRECATED: Use hauptbenutzer instead.

        Returns the Hauptbenutzer for backward compatibility.
        """
        return self.hauptbenutzer

    @property
    def alle_benutzer(self):
        """Return all users assigned to this Kunde."""
        return [zuo.user for zuo in self.benutzer_zuordnungen]

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

    # ========== Lead/Kunde Type Properties ==========

    @property
    def is_lead(self) -> bool:
        """Check if this is a Lead (prospect without user account)."""
        return self.typ == KundeTyp.LEAD.value

    @property
    def is_kunde(self) -> bool:
        """Check if this is a full Kunde (customer with user account)."""
        return self.typ == KundeTyp.KUNDE.value

    @property
    def kontakt_email(self) -> str | None:
        """Get contact email for this Kunde/Lead.

        For Leads: Always uses kunde.email (they don't have user accounts)
        For Kunden: Uses hauptbenutzer.email if available, falls back to kunde.email
        """
        if self.is_lead:
            return self.email
        user = self.hauptbenutzer
        if user and user.email:
            return user.email
        return self.email

    @property
    def kontakt_name(self) -> str:
        """Get contact name for addressing in emails.

        For Leads: Uses firmierung (company name)
        For Kunden: Uses user full_name if available, falls back to firmierung
        """
        if self.is_lead:
            return self.firmierung
        user = self.hauptbenutzer
        if user and user.full_name:
            return user.full_name
        return self.firmierung

    def kann_fragebogen_erhalten(self) -> bool:
        """Check if this Kunde/Lead can receive questionnaire invitations.

        Returns True if a contact email is available for sending invitations.
        Leads: Need email field set
        Kunden: Need user with email OR email field set
        """
        return bool(self.kontakt_email)

    def kann_mailing_erhalten(self) -> bool:
        """Check if this Kunde/Lead can receive marketing mailings.

        Returns True if:
        - A contact email is available
        - The customer has not opted out of mailings
        """
        return bool(self.kontakt_email) and not self.mailing_abgemeldet

    def mailing_abmelden(self):
        """Opt out of marketing mailings (DSGVO-compliant)."""
        self.mailing_abgemeldet = True
        self.mailing_abgemeldet_am = datetime.utcnow()

    def mailing_anmelden(self):
        """Opt back in to marketing mailings."""
        self.mailing_abgemeldet = False
        self.mailing_abgemeldet_am = None

    # ========== Briefanrede Properties ==========

    @property
    def effektiver_kommunikation_stil(self) -> str:
        """Effective communication style (User overrides Kunde default).

        Priority:
        1. hauptbenutzer.kommunikation_stil (if set)
        2. self.kommunikation_stil (Kunde default)
        3. 'foermlich' (system fallback)
        """
        user = self.hauptbenutzer
        if user and user.kommunikation_stil:
            return user.kommunikation_stil
        return self.kommunikation_stil or 'foermlich'

    @property
    def briefanrede(self) -> str:
        """Automatic salutation based on effective kommunikation_stil.

        Uses the effective style which considers User override over Kunde default.
        """
        if self.effektiver_kommunikation_stil == 'locker':
            return self.briefanrede_locker
        return self.briefanrede_foermlich

    @property
    def briefanrede_foermlich(self) -> str:
        """Formal salutation (Sie-form).

        Examples:
        - Herr: 'Sehr geehrter Herr Müller'
        - Frau: 'Sehr geehrte Frau Schmidt'
        - Divers: 'Guten Tag Alex Müller'
        - Firma: 'Sehr geehrte Damen und Herren'
        """
        return self._generate_briefanrede('foermlich')

    @property
    def briefanrede_locker(self) -> str:
        """Informal salutation (Du-form).

        Examples:
        - Herr: 'Lieber Herr Müller'
        - Frau: 'Liebe Frau Schmidt'
        - Divers: 'Hallo Alex'
        - Firma: 'Hallo zusammen'
        """
        return self._generate_briefanrede('locker')

    def _generate_briefanrede(self, stil: str) -> str:
        """Generate salutation from LookupWert pattern.

        Args:
            stil: 'foermlich' or 'locker'

        Returns:
            Formatted salutation string with name placeholders filled in

        Logic:
        - anrede comes from hauptbenutzer (personenbezogen: herr/frau/divers)
        - Falls back to 'firma' if no user or no anrede set
        """
        from app.models import LookupWert

        kategorie = f'anrede_{stil}'

        # Get anrede from hauptbenutzer (personenbezogen)
        user = self.hauptbenutzer
        anrede_key = user.anrede if user and user.anrede else 'firma'

        pattern = LookupWert.get_wert(kategorie, anrede_key)
        if not pattern:
            # Fallback if no pattern found
            if stil == 'locker':
                return 'Hallo'
            return 'Sehr geehrte Damen und Herren'

        # Get name parts from hauptbenutzer
        vorname = ''
        nachname = ''
        if user:
            vorname = user.vorname or ''
            nachname = user.nachname or ''

        # Replace placeholders and clean up whitespace
        result = pattern.format(vorname=vorname, nachname=nachname)
        # Remove double spaces and strip
        return ' '.join(result.split())

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
            'telefon': self.telefon,
            'email': self.email,
            'notizen': self.notizen,
            'aktiv': self.aktiv,
            'typ': self.typ,
            'is_lead': self.is_lead,
            'kontakt_email': self.kontakt_email,
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
