"""Schulungsthema Model - Wiederverwendbare Themenblöcke für Schulungen (PRD-010).

Ein Schulungsthema ist ein einzelner Lernblock, der in mehreren Schulungen
verwendet werden kann. Themen haben eine definierte Dauer und können mit
Beschreibungen/Markdown-Inhalten versehen werden.
"""
from datetime import datetime
from app import db


class Schulungsthema(db.Model):
    """Einzelnes Schulungsthema (wiederverwendbar in mehreren Schulungen)."""
    __tablename__ = 'schulungsthema'

    id = db.Column(db.Integer, primary_key=True)

    # === GRUNDDATEN ===

    # Thementitel (z.B. "ERP Grundlagen", "Bestellwesen")
    titel = db.Column(db.String(200), nullable=False)

    # Ausführliche Beschreibung (Markdown-fähig)
    beschreibung = db.Column(db.Text)

    # Dauer in Minuten (z.B. 45, 60, 90)
    dauer_minuten = db.Column(db.Integer, nullable=False, default=45)

    # === STATUS ===

    # Aktiv = Kann in Schulungen verwendet werden
    aktiv = db.Column(db.Boolean, nullable=False, default=True)

    # === META ===

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # === RELATIONSHIPS ===

    # Verknüpfung zu Schulungen über Junction-Table
    schulung_verknuepfungen = db.relationship(
        'SchulungThema',
        back_populates='thema',
        cascade='all, delete-orphan'
    )

    # Termine, die dieses Thema verwenden
    termine = db.relationship(
        'Schulungstermin',
        back_populates='thema',
        lazy='dynamic'
    )

    def __repr__(self):
        return f'<Schulungsthema {self.id}: {self.titel[:30]}>'

    @property
    def dauer_formatiert(self) -> str:
        """Formatierte Dauer (z.B. '1h 30min' oder '45min')."""
        if self.dauer_minuten >= 60:
            stunden = self.dauer_minuten // 60
            minuten = self.dauer_minuten % 60
            if minuten > 0:
                return f'{stunden}h {minuten}min'
            return f'{stunden}h'
        return f'{self.dauer_minuten}min'

    @property
    def anzahl_schulungen(self) -> int:
        """Anzahl der Schulungen, die dieses Thema verwenden."""
        return len(self.schulung_verknuepfungen)

    def to_dict(self):
        """Serialization for API/Export."""
        return {
            'id': self.id,
            'titel': self.titel,
            'beschreibung': self.beschreibung,
            'dauer_minuten': self.dauer_minuten,
            'dauer_formatiert': self.dauer_formatiert,
            'aktiv': self.aktiv,
            'anzahl_schulungen': self.anzahl_schulungen,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    # === CLASS METHODS ===

    @classmethod
    def get_aktive(cls):
        """Get all active themes ordered by title."""
        return cls.query.filter_by(aktiv=True).order_by(cls.titel).all()

    @classmethod
    def suche(cls, suchbegriff: str, nur_aktive: bool = True, limit: int = 50):
        """Search themes by title or description."""
        pattern = f'%{suchbegriff}%'
        query = cls.query.filter(
            db.or_(
                cls.titel.ilike(pattern),
                cls.beschreibung.ilike(pattern)
            )
        )
        if nur_aktive:
            query = query.filter_by(aktiv=True)
        return query.order_by(cls.titel).limit(limit).all()
