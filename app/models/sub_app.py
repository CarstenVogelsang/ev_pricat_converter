"""SubApp and SubAppAccess models for role-based app access control."""
from datetime import datetime

from app import db


class SubApp(db.Model):
    """Sub-application definition for dashboard."""
    __tablename__ = 'sub_app'

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    beschreibung = db.Column(db.String(255))
    icon = db.Column(db.String(50), default='ti-app')
    color = db.Column(db.String(20), default='primary')  # Bootstrap class (fallback)
    color_hex = db.Column(db.String(7), default='#0d6efd')  # Hex color for icon/button
    route_endpoint = db.Column(db.String(100))
    aktiv = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to SubAppAccess
    role_access = db.relationship('SubAppAccess', backref='sub_app', lazy='dynamic',
                                  cascade='all, delete-orphan')

    def __repr__(self):
        return f'<SubApp {self.slug}>'

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'slug': self.slug,
            'name': self.name,
            'beschreibung': self.beschreibung,
            'icon': self.icon,
            'color': self.color,
            'color_hex': self.color_hex,
            'route_endpoint': self.route_endpoint,
            'aktiv': self.aktiv,
            'sort_order': self.sort_order,
        }


class SubAppAccess(db.Model):
    """Mapping table for role-based sub-app access."""
    __tablename__ = 'sub_app_access'

    id = db.Column(db.Integer, primary_key=True)
    sub_app_id = db.Column(db.Integer, db.ForeignKey('sub_app.id'), nullable=False)
    rolle_id = db.Column(db.Integer, db.ForeignKey('rolle.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('sub_app_id', 'rolle_id', name='uq_subapp_rolle'),
    )

    def __repr__(self):
        return f'<SubAppAccess sub_app={self.sub_app_id} rolle={self.rolle_id}>'
