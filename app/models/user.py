"""User Model for authentication."""
from datetime import datetime
from enum import Enum
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from app import db


class UserTyp(str, Enum):
    """User type for distinguishing humans from AI agents.

    Used for task assignment attribution in project management (PRD-011).
    """
    MENSCH = 'mensch'            # Human user
    KI_CLAUDE = 'ki_claude'      # Anthropic Claude
    KI_CODEX = 'ki_codex'        # OpenAI Codex
    KI_ANDERE = 'ki_andere'      # Other AI agents

    @classmethod
    def choices(cls):
        """Return list of (value, label) tuples for form selects."""
        labels = {
            cls.MENSCH: 'Mensch',
            cls.KI_CLAUDE: 'KI: Claude',
            cls.KI_CODEX: 'KI: Codex',
            cls.KI_ANDERE: 'KI: Andere',
        }
        return [(t.value, labels[t]) for t in cls]

    @classmethod
    def ki_typen(cls):
        """Return list of AI user type values."""
        return [cls.KI_CLAUDE.value, cls.KI_CODEX.value, cls.KI_ANDERE.value]


class User(UserMixin, db.Model):
    """User entity for authentication and authorization."""

    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    vorname = db.Column(db.String(50), nullable=False)
    nachname = db.Column(db.String(50), nullable=False)
    rolle_id = db.Column(db.Integer, db.ForeignKey('rolle.id'), nullable=False)
    aktiv = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Anrede/Briefanrede settings (personenbezogen)
    anrede = db.Column(db.String(20), nullable=True)  # herr, frau, divers
    kommunikation_stil = db.Column(db.String(20), nullable=True)  # NULL = Kunde-Default

    # User type for human/AI distinction (PRD-011)
    user_typ = db.Column(db.String(20), default=UserTyp.MENSCH.value, nullable=False)

    # NEW: 1:N relationship to Kunden via junction table
    kunde_zuordnungen = db.relationship(
        'KundeBenutzer',
        back_populates='user',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<User {self.email}>'

    def set_password(self, password):
        """Hash and set the password."""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """Check if password matches hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def rolle(self):
        """Backward-compatible property returning role name."""
        return self.rolle_obj.name if self.rolle_obj else None

    @property
    def is_admin(self):
        """Check if user has admin role."""
        return self.rolle_obj and self.rolle_obj.name == 'admin'

    @property
    def is_mitarbeiter(self):
        """Check if user has mitarbeiter role."""
        return self.rolle_obj and self.rolle_obj.name == 'mitarbeiter'

    @property
    def is_kunde(self):
        """Check if user has kunde role."""
        return self.rolle_obj and self.rolle_obj.name == 'kunde'

    @property
    def is_internal(self):
        """Check if user is internal (admin or mitarbeiter)."""
        return self.is_admin or self.is_mitarbeiter

    @property
    def is_ki(self):
        """Check if user is an AI agent."""
        return self.user_typ in UserTyp.ki_typen()

    @property
    def full_name(self):
        """Return full name."""
        return f'{self.vorname} {self.nachname}'

    @property
    def kunden(self):
        """Return all Kunden this user is assigned to."""
        return [zuo.kunde for zuo in self.kunde_zuordnungen]

    @property
    def kunde(self):
        """DEPRECATED: Return the primary Kunde (for backward compatibility).

        Returns the Kunde where this user is Hauptbenutzer, or first assigned Kunde.
        """
        # Prefer Kunde where user is Hauptbenutzer
        for zuo in self.kunde_zuordnungen:
            if zuo.ist_hauptbenutzer:
                return zuo.kunde
        # Fallback: first assigned Kunde
        if self.kunde_zuordnungen:
            return self.kunde_zuordnungen[0].kunde
        return None

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'email': self.email,
            'vorname': self.vorname,
            'nachname': self.nachname,
            'anrede': self.anrede,
            'kommunikation_stil': self.kommunikation_stil,
            'rolle': self.rolle,
            'rolle_id': self.rolle_id,
            'user_typ': self.user_typ,
            'is_ki': self.is_ki,
            'aktiv': self.aktiv,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
