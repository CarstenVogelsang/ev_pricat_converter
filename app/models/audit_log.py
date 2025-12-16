"""AuditLog model for tracking important events across all modules.

Documented in PRD_BASIS_LOGGING.md.
"""
from datetime import datetime
from app import db


class AuditLog(db.Model):
    """Audit log entry for tracking important events.

    Events are categorized by importance (niedrig, mittel, hoch, kritisch)
    and can be filtered by module, user, date range, etc.

    DSGVO: user_id remains in log even after user deletion.
    Display as "Gelöschter Benutzer (ID: X)" when user is deleted.
    """
    __tablename__ = 'audit_log'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True, nullable=False)

    # Who performed the action?
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user = db.relationship('User', backref=db.backref('audit_logs', lazy='dynamic'))

    # In which module?
    # Note: relationship is defined in Modul model with backref='modul'
    modul_id = db.Column(db.Integer, db.ForeignKey('modul.id'), nullable=False)

    # What happened?
    aktion = db.Column(db.String(100), nullable=False, index=True)
    details = db.Column(db.Text, nullable=True)

    # How important?
    # Values: niedrig, mittel, hoch, kritisch
    wichtigkeit = db.Column(db.String(20), default='niedrig', index=True, nullable=False)

    # Which entity was affected?
    entity_type = db.Column(db.String(50), nullable=True)  # e.g. 'Kunde', 'Branche'
    entity_id = db.Column(db.Integer, nullable=True)

    # Additional metadata
    ip_adresse = db.Column(db.String(45), nullable=True)  # IPv6 compatible

    def __repr__(self):
        return f'<AuditLog {self.id}: {self.aktion} @ {self.timestamp}>'

    @property
    def user_display(self) -> str:
        """Get display name for user, handling deleted users."""
        if self.user:
            return self.user.full_name or self.user.email
        elif self.user_id:
            return f"Gelöschter Benutzer (ID: {self.user_id})"
        else:
            return "System"

    @property
    def wichtigkeit_badge_class(self) -> str:
        """Get Bootstrap badge class for importance level."""
        mapping = {
            'kritisch': 'bg-danger',
            'hoch': 'bg-warning text-dark',
            'mittel': 'bg-info',
            'niedrig': 'bg-secondary'
        }
        return mapping.get(self.wichtigkeit, 'bg-secondary')

    @property
    def wichtigkeit_icon(self) -> str:
        """Get icon for importance level."""
        mapping = {
            'kritisch': 'alert-octagon',
            'hoch': 'alert-triangle',
            'mittel': 'info-circle',
            'niedrig': 'circle'
        }
        return mapping.get(self.wichtigkeit, 'circle')
