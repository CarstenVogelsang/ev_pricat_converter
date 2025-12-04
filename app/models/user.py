"""User Model for authentication."""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

from app import db


class User(UserMixin, db.Model):
    """User entity for authentication and authorization."""

    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    vorname = db.Column(db.String(50), nullable=False)
    nachname = db.Column(db.String(50), nullable=False)
    rolle = db.Column(db.String(20), nullable=False, default='sachbearbeiter')
    aktiv = db.Column(db.Boolean, default=True, nullable=False)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.email}>'

    def set_password(self, password):
        """Hash and set the password."""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """Check if password matches hash."""
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        """Check if user has admin role."""
        return self.rolle == 'admin'

    @property
    def full_name(self):
        """Return full name."""
        return f'{self.vorname} {self.nachname}'

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'email': self.email,
            'vorname': self.vorname,
            'nachname': self.nachname,
            'rolle': self.rolle,
            'aktiv': self.aktiv,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
