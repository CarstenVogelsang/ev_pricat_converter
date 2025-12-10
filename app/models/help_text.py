"""HelpText model for editable UI help texts."""
from datetime import datetime

from app import db


class HelpText(db.Model):
    """Editable help texts for UI components (Cards, Forms, etc.)."""
    __tablename__ = 'help_text'

    id = db.Column(db.Integer, primary_key=True)

    # Unique key for identifying the help text location
    # Format: "module.page.section" e.g. "kunden.detail.branchen"
    schluessel = db.Column(db.String(100), unique=True, nullable=False, index=True)

    # Display title shown in modal header
    titel = db.Column(db.String(200), nullable=False)

    # Markdown content that will be rendered as HTML
    inhalt_markdown = db.Column(db.Text, nullable=False)

    # Active flag to enable/disable help texts
    aktiv = db.Column(db.Boolean, default=True)

    # Audit fields
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    updated_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    # Relationship to User who last updated
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])

    def __repr__(self):
        return f'<HelpText {self.schluessel}>'

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'schluessel': self.schluessel,
            'titel': self.titel,
            'inhalt_markdown': self.inhalt_markdown,
            'aktiv': self.aktiv,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'updated_by': self.updated_by.vorname if self.updated_by else None,
        }
