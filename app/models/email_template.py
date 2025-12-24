"""Email template model for customizable email content.

Templates are stored in the database with Jinja2 placeholders.
This allows admins to customize email content without code changes.
"""
from datetime import datetime

from app import db


class EmailTemplate(db.Model):
    """Database-stored email template with Jinja2 placeholders.

    Templates support these standard placeholders:
    - {{ firmenname }} - Customer company name
    - {{ link }} - Action link (magic link, password link, etc.)
    - {{ fragebogen_titel }} - Questionnaire title
    - {{ portal_name }} - Portal name from branding
    - {{ primary_color }} - Brand primary color
    - {{ logo_url }} - Brand logo URL
    - {{ footer }} - Customer-specific or system footer

    Templates can also use Jinja2 conditionals:
    {% if logo_url %}<img src="{{ logo_url }}">{% endif %}
    """
    __tablename__ = 'email_template'

    id = db.Column(db.Integer, primary_key=True)

    # Unique key for looking up templates (e.g., 'fragebogen_einladung')
    schluessel = db.Column(db.String(50), unique=True, nullable=False, index=True)

    # Human-readable name for admin UI
    name = db.Column(db.String(100), nullable=False)

    # Description of when this template is used
    beschreibung = db.Column(db.Text, nullable=True)

    # Email subject line (supports Jinja2 placeholders)
    betreff = db.Column(db.String(200), nullable=False)

    # HTML body (supports Jinja2 placeholders)
    body_html = db.Column(db.Text, nullable=False)

    # Plain text fallback (optional, supports Jinja2 placeholders)
    body_text = db.Column(db.Text, nullable=True)

    # Whether this template is active
    aktiv = db.Column(db.Boolean, default=True, nullable=False)

    # Timestamps
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    aktualisiert_am = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<EmailTemplate {self.schluessel}>'

    @classmethod
    def get_by_key(cls, schluessel: str) -> 'EmailTemplate':
        """Get an active template by its key.

        Args:
            schluessel: Unique template key (e.g., 'fragebogen_einladung')

        Returns:
            EmailTemplate if found and active, None otherwise
        """
        return cls.query.filter_by(schluessel=schluessel, aktiv=True).first()

    @classmethod
    def get_all_active(cls) -> list:
        """Get all active templates."""
        return cls.query.filter_by(aktiv=True).order_by(cls.name).all()

    def to_dict(self) -> dict:
        """Return dictionary representation."""
        return {
            'id': self.id,
            'schluessel': self.schluessel,
            'name': self.name,
            'beschreibung': self.beschreibung,
            'betreff': self.betreff,
            'body_html': self.body_html,
            'body_text': self.body_text,
            'aktiv': self.aktiv,
            'erstellt_am': self.erstellt_am.isoformat() if self.erstellt_am else None,
            'aktualisiert_am': self.aktualisiert_am.isoformat() if self.aktualisiert_am else None,
        }
