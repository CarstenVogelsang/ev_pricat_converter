"""Admin Page Visit tracking for 'recently visited' feature."""
from datetime import datetime

from app import db


class AdminPageVisit(db.Model):
    """Tracks admin page visits per user for 'recently visited' Quick Links."""

    __tablename__ = 'admin_page_visit'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    endpoint = db.Column(db.String(200), nullable=False)  # Flask endpoint, e.g. 'admin.system'
    page_url = db.Column(db.String(500), nullable=False)  # URL path, e.g. '/admin/system'
    page_title = db.Column(db.String(200))                # Human-readable title
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Relationship to User
    user = db.relationship('User', backref=db.backref('admin_page_visits', lazy='dynamic'))

    __table_args__ = (
        db.Index('idx_admin_page_visit_user_timestamp', 'user_id', 'timestamp'),
    )

    def __repr__(self):
        return f'<AdminPageVisit {self.endpoint} by User {self.user_id}>'

    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'endpoint': self.endpoint,
            'page_url': self.page_url,
            'page_title': self.page_title,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
