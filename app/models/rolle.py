"""Rolle (Role) model."""
from datetime import datetime

from app import db


class Rolle(db.Model):
    """Role model for user access control."""
    __tablename__ = 'rolle'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(30), unique=True, nullable=False)
    beschreibung = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to User
    users = db.relationship('User', backref='rolle_obj', lazy='dynamic')

    def __repr__(self):
        return f'<Rolle {self.name}>'

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'beschreibung': self.beschreibung,
        }
