"""Schulung Model - Kurs-Template für Online-Schulungen (PRD-010).

Eine Schulung ist ein Kurs-Template mit Preis, Metadaten und verknüpften Themen.
Konkrete Termine werden als Schulungsdurchführung angelegt.
"""
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from app import db


class Schulung(db.Model):
    """Kurs-Template mit Preis und Metadaten."""
    __tablename__ = 'schulung'

    id = db.Column(db.Integer, primary_key=True)

    # === GRUNDDATEN ===

    # Schulungstitel (z.B. "ERP Grundlagen für Einsteiger")
    titel = db.Column(db.String(200), nullable=False)

    # Ausführliche Beschreibung (Markdown-fähig)
    beschreibung = db.Column(db.Text)

    # === PREIS & ERP ===

    # ERP-Artikelnummer für Rechnungsstellung
    artikelnummer = db.Column(db.String(50))

    # Standardpreis in EUR
    preis = db.Column(db.Numeric(10, 2), nullable=False)

    # Optionaler Sonderpreis (Aktionspreis)
    sonderpreis = db.Column(db.Numeric(10, 2))

    # Aktionszeitraum für Sonderpreis
    aktionszeitraum_von = db.Column(db.Date)
    aktionszeitraum_bis = db.Column(db.Date)

    # === KAPAZITÄT & REGELN ===

    # Maximale Teilnehmerzahl pro Durchführung
    max_teilnehmer = db.Column(db.Integer, nullable=False, default=10)

    # Storno-Frist in Tagen vor Schulungsbeginn
    storno_frist_tage = db.Column(db.Integer, nullable=False, default=7)

    # === STATUS ===

    # Öffentlich sichtbar auf der Website
    aktiv = db.Column(db.Boolean, nullable=False, default=True)

    # Sortierung für Anzeige
    sortierung = db.Column(db.Integer, default=0)

    # === META ===

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # === RELATIONSHIPS ===

    # Verknüpfung zu Themen über Junction-Table
    thema_verknuepfungen = db.relationship(
        'SchulungThema',
        back_populates='schulung',
        cascade='all, delete-orphan',
        order_by='SchulungThema.sortierung'
    )

    # Durchführungen dieser Schulung
    durchfuehrungen = db.relationship(
        'Schulungsdurchfuehrung',
        back_populates='schulung',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    def __repr__(self):
        return f'<Schulung {self.id}: {self.titel[:30]}>'

    # === PROPERTIES ===

    @property
    def aktueller_preis(self) -> Decimal:
        """Gibt Sonderpreis zurück wenn im Aktionszeitraum, sonst Standardpreis."""
        heute = date.today()

        if self.sonderpreis is not None:
            von_ok = self.aktionszeitraum_von is None or self.aktionszeitraum_von <= heute
            bis_ok = self.aktionszeitraum_bis is None or self.aktionszeitraum_bis >= heute

            if von_ok and bis_ok:
                return self.sonderpreis

        return self.preis

    @property
    def hat_sonderpreis(self) -> bool:
        """True wenn aktuell ein Sonderpreis gilt."""
        return self.aktueller_preis != self.preis

    @property
    def themen_sortiert(self) -> list:
        """Alle Themen sortiert nach Junction-Sortierung."""
        return [vk.thema for vk in self.thema_verknuepfungen]

    @property
    def anzahl_themen(self) -> int:
        """Anzahl der verknüpften Themen."""
        return len(self.thema_verknuepfungen)

    @property
    def gesamtdauer_minuten(self) -> int:
        """Summe aller Themen-Dauern."""
        return sum(vk.thema.dauer_minuten for vk in self.thema_verknuepfungen)

    @property
    def gesamtdauer_formatiert(self) -> str:
        """Formatierte Gesamtdauer (z.B. '4h 30min')."""
        minuten = self.gesamtdauer_minuten
        if minuten >= 60:
            stunden = minuten // 60
            rest = minuten % 60
            if rest > 0:
                return f'{stunden}h {rest}min'
            return f'{stunden}h'
        return f'{minuten}min'

    @property
    def naechste_durchfuehrung(self):
        """Nächste geplante/aktive Durchführung."""
        from app.models.schulungsdurchfuehrung import DurchfuehrungStatus
        heute = date.today()
        return self.durchfuehrungen.filter(
            db.or_(
                Schulungsdurchfuehrung.status == DurchfuehrungStatus.GEPLANT.value,
                Schulungsdurchfuehrung.status == DurchfuehrungStatus.AKTIV.value
            ),
            Schulungsdurchfuehrung.start_datum >= heute
        ).order_by(Schulungsdurchfuehrung.start_datum).first()

    @property
    def kommende_durchfuehrungen(self) -> list:
        """Alle kommenden Durchführungen (geplant/aktiv, ab heute)."""
        from app.models.schulungsdurchfuehrung import DurchfuehrungStatus
        heute = date.today()
        return self.durchfuehrungen.filter(
            db.or_(
                Schulungsdurchfuehrung.status == DurchfuehrungStatus.GEPLANT.value,
                Schulungsdurchfuehrung.status == DurchfuehrungStatus.AKTIV.value
            ),
            Schulungsdurchfuehrung.start_datum >= heute
        ).order_by(Schulungsdurchfuehrung.start_datum).all()

    def to_dict(self, include_themen: bool = False):
        """Serialization for API/Export."""
        data = {
            'id': self.id,
            'titel': self.titel,
            'beschreibung': self.beschreibung,
            'artikelnummer': self.artikelnummer,
            'preis': str(self.preis) if self.preis else None,
            'sonderpreis': str(self.sonderpreis) if self.sonderpreis else None,
            'aktueller_preis': str(self.aktueller_preis),
            'hat_sonderpreis': self.hat_sonderpreis,
            'aktionszeitraum_von': self.aktionszeitraum_von.isoformat() if self.aktionszeitraum_von else None,
            'aktionszeitraum_bis': self.aktionszeitraum_bis.isoformat() if self.aktionszeitraum_bis else None,
            'max_teilnehmer': self.max_teilnehmer,
            'storno_frist_tage': self.storno_frist_tage,
            'aktiv': self.aktiv,
            'sortierung': self.sortierung,
            'anzahl_themen': self.anzahl_themen,
            'gesamtdauer_minuten': self.gesamtdauer_minuten,
            'gesamtdauer_formatiert': self.gesamtdauer_formatiert,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        if include_themen:
            data['themen'] = [vk.to_dict() for vk in self.thema_verknuepfungen]

        return data

    # === CLASS METHODS ===

    @classmethod
    def get_aktive(cls):
        """Get all active trainings ordered by sortierung."""
        return cls.query.filter_by(aktiv=True).order_by(cls.sortierung, cls.titel).all()

    @classmethod
    def get_mit_kommenden_terminen(cls):
        """Get active trainings that have upcoming executions."""
        from app.models.schulungsdurchfuehrung import DurchfuehrungStatus
        heute = date.today()

        return cls.query.filter_by(aktiv=True).filter(
            cls.durchfuehrungen.any(
                db.and_(
                    db.or_(
                        Schulungsdurchfuehrung.status == DurchfuehrungStatus.GEPLANT.value,
                        Schulungsdurchfuehrung.status == DurchfuehrungStatus.AKTIV.value
                    ),
                    Schulungsdurchfuehrung.start_datum >= heute
                )
            )
        ).order_by(cls.sortierung, cls.titel).all()

    @classmethod
    def suche(cls, suchbegriff: str, nur_aktive: bool = True, limit: int = 50):
        """Search trainings by title or description."""
        pattern = f'%{suchbegriff}%'
        query = cls.query.filter(
            db.or_(
                cls.titel.ilike(pattern),
                cls.beschreibung.ilike(pattern)
            )
        )
        if nur_aktive:
            query = query.filter_by(aktiv=True)
        return query.order_by(cls.sortierung, cls.titel).limit(limit).all()


# Import here to avoid circular imports
from app.models.schulungsdurchfuehrung import Schulungsdurchfuehrung


class SchulungThema(db.Model):
    """M:N Junction-Table zwischen Schulung und Schulungsthema.

    Enthält zusätzlich die Sortierung (Reihenfolge der Themen in einer Schulung).
    """
    __tablename__ = 'schulung_thema'
    __table_args__ = (
        db.UniqueConstraint('schulung_id', 'thema_id', name='uq_schulung_thema'),
    )

    id = db.Column(db.Integer, primary_key=True)
    schulung_id = db.Column(db.Integer, db.ForeignKey('schulung.id'), nullable=False)
    thema_id = db.Column(db.Integer, db.ForeignKey('schulungsthema.id'), nullable=False)

    # Reihenfolge des Themas in dieser Schulung
    sortierung = db.Column(db.Integer, nullable=False, default=0)

    # === RELATIONSHIPS ===

    schulung = db.relationship('Schulung', back_populates='thema_verknuepfungen')
    thema = db.relationship('Schulungsthema', back_populates='schulung_verknuepfungen')

    def __repr__(self):
        return f'<SchulungThema schulung={self.schulung_id} thema={self.thema_id}>'

    def to_dict(self):
        """Serialization including thema details."""
        return {
            'id': self.id,
            'schulung_id': self.schulung_id,
            'thema_id': self.thema_id,
            'sortierung': self.sortierung,
            'thema': self.thema.to_dict() if self.thema else None,
        }
