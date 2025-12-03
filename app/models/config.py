"""Config (Key-Value Store) Model."""
from datetime import datetime
from app import db


class Config(db.Model):
    """Configuration key-value store."""

    __tablename__ = 'config'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False, index=True)
    value = db.Column(db.Text)
    beschreibung = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Config {self.key}>'

    @staticmethod
    def get_value(key, default=None):
        """Get configuration value by key."""
        entry = Config.query.filter_by(key=key).first()
        return entry.value if entry else default

    @staticmethod
    def set_value(key, value, beschreibung=None):
        """Set configuration value."""
        entry = Config.query.filter_by(key=key).first()
        if entry:
            entry.value = value
            if beschreibung:
                entry.beschreibung = beschreibung
        else:
            entry = Config(key=key, value=value, beschreibung=beschreibung)
            db.session.add(entry)
        db.session.commit()
        return entry
