"""PasswordToken model for secure one-time password reveal."""
from datetime import datetime, timedelta
import secrets

from app import db


class PasswordToken(db.Model):
    """Token for one-time password reveal after user creation.

    When a user account is created for a Kunde, a random password is generated.
    This token allows the password to be revealed exactly once via a secure link.
    After 48 hours or first reveal, the plain password is deleted.
    """
    __tablename__ = 'password_token'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_plain = db.Column(db.String(100))  # Cleared after reveal
    expires_at = db.Column(db.DateTime, nullable=False)
    revealed_at = db.Column(db.DateTime)  # NULL = not yet revealed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    user = db.relationship('User', backref=db.backref('password_tokens', lazy='dynamic'))

    def __repr__(self):
        return f'<PasswordToken user_id={self.user_id}>'

    @classmethod
    def create_for_user(cls, user_id: int, password_plain: str, hours_valid: int = 48):
        """Create a new password token for a user.

        Args:
            user_id: The user ID
            password_plain: The plain text password to store temporarily
            hours_valid: How many hours the token is valid (default 48)

        Returns:
            PasswordToken instance (not yet committed)
        """
        return cls(
            user_id=user_id,
            token=secrets.token_urlsafe(48),  # 64 chars URL-safe
            password_plain=password_plain,
            expires_at=datetime.utcnow() + timedelta(hours=hours_valid)
        )

    @property
    def is_valid(self) -> bool:
        """Check if token is still valid (not expired, not revealed)."""
        if self.revealed_at is not None:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        return True

    @property
    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def is_revealed(self) -> bool:
        """Check if password was already revealed."""
        return self.revealed_at is not None

    def reveal(self) -> str | None:
        """Reveal and consume the password token.

        Returns the plain password and marks token as revealed.
        Returns None if already revealed or expired.
        """
        if not self.is_valid:
            return None

        password = self.password_plain
        self.revealed_at = datetime.utcnow()
        self.password_plain = None  # Clear the plain password
        return password

    def to_dict(self):
        """Return dictionary representation (without password!)."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'token': self.token,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'revealed_at': self.revealed_at.isoformat() if self.revealed_at else None,
            'is_valid': self.is_valid,
            'is_expired': self.is_expired,
            'is_revealed': self.is_revealed,
        }
