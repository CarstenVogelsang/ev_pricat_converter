"""Schulungsbuchung Model - Buchung einer Schulungsdurchführung (PRD-010).

Eine Buchung verknüpft einen Kunden mit einer Schulungsdurchführung.
Enthält den Buchungsstatus (gebucht, warteliste, storniert) und den
Preis zum Buchungszeitpunkt.
"""
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from app import db


class BuchungStatus(Enum):
    """Status einer Schulungsbuchung."""
    GEBUCHT = 'gebucht'         # Verbindlich gebucht
    WARTELISTE = 'warteliste'   # Auf Warteliste
    STORNIERT = 'storniert'     # Storniert


class Schulungsbuchung(db.Model):
    """Buchung einer Schulungsdurchführung durch einen Kunden."""
    __tablename__ = 'schulungsbuchung'
    __table_args__ = (
        db.UniqueConstraint('kunde_id', 'durchfuehrung_id', name='uq_kunde_durchfuehrung'),
    )

    id = db.Column(db.Integer, primary_key=True)

    # Referenz zum Kunden
    kunde_id = db.Column(db.Integer, db.ForeignKey('kunde.id'), nullable=False)

    # Referenz zur Durchführung
    durchfuehrung_id = db.Column(
        db.Integer,
        db.ForeignKey('schulungsdurchfuehrung.id'),
        nullable=False
    )

    # === STATUS ===

    status = db.Column(
        db.String(20),
        nullable=False,
        default=BuchungStatus.GEBUCHT.value
    )

    # === PREIS ===

    # Preis zum Buchungszeitpunkt (Snapshot für Abrechnung)
    preis_bei_buchung = db.Column(db.Numeric(10, 2), nullable=False)

    # === TIMESTAMPS ===

    # Buchungszeitpunkt
    gebucht_am = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Stornierungszeitpunkt (wenn storniert)
    storniert_am = db.Column(db.DateTime)

    # === NOTIZEN ===

    anmerkungen = db.Column(db.Text)

    # === META ===

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # === RELATIONSHIPS ===

    kunde = db.relationship('Kunde', backref=db.backref('schulungsbuchungen', lazy='dynamic'))
    durchfuehrung = db.relationship('Schulungsdurchfuehrung', back_populates='buchungen')

    def __repr__(self):
        return f'<Schulungsbuchung {self.id}: Kunde {self.kunde_id} für {self.durchfuehrung_id}>'

    # === PROPERTIES ===

    @property
    def is_gebucht(self) -> bool:
        return self.status == BuchungStatus.GEBUCHT.value

    @property
    def is_warteliste(self) -> bool:
        return self.status == BuchungStatus.WARTELISTE.value

    @property
    def is_storniert(self) -> bool:
        return self.status == BuchungStatus.STORNIERT.value

    @property
    def schulung(self):
        """Shortcut zur Schulung über Durchführung."""
        return self.durchfuehrung.schulung if self.durchfuehrung else None

    @property
    def storno_frist_datum(self) -> date:
        """Letzter Tag für kostenfreie Stornierung."""
        if not self.durchfuehrung:
            return None
        tage = self.durchfuehrung.schulung.storno_frist_tage
        return self.durchfuehrung.start_datum - timedelta(days=tage)

    @property
    def kann_storniert_werden(self) -> bool:
        """True wenn Stornierung noch möglich ist (innerhalb der Frist)."""
        if self.is_storniert:
            return False
        if not self.storno_frist_datum:
            return False
        return date.today() <= self.storno_frist_datum

    @property
    def tage_bis_storno_frist(self) -> int:
        """Anzahl Tage bis zur Storno-Frist (negativ = überschritten)."""
        if not self.storno_frist_datum:
            return 0
        delta = self.storno_frist_datum - date.today()
        return delta.days

    # === STATUS TRANSITIONS ===

    def stornieren(self):
        """Buchung stornieren."""
        if self.is_storniert:
            raise ValueError('Buchung ist bereits storniert')
        self.status = BuchungStatus.STORNIERT.value
        self.storniert_am = datetime.utcnow()

    def auf_warteliste_setzen(self):
        """Buchung auf Warteliste setzen."""
        if not self.is_gebucht:
            raise ValueError('Nur gebuchte Buchungen können auf die Warteliste gesetzt werden')
        self.status = BuchungStatus.WARTELISTE.value

    def von_warteliste_freischalten(self):
        """Buchung von Warteliste auf gebucht setzen."""
        if not self.is_warteliste:
            raise ValueError('Nur Wartelisten-Buchungen können freigeschaltet werden')
        self.status = BuchungStatus.GEBUCHT.value

    def to_dict(self, include_kunde: bool = False, include_durchfuehrung: bool = False):
        """Serialization for API/Export."""
        data = {
            'id': self.id,
            'kunde_id': self.kunde_id,
            'durchfuehrung_id': self.durchfuehrung_id,
            'status': self.status,
            'preis_bei_buchung': str(self.preis_bei_buchung) if self.preis_bei_buchung else None,
            'gebucht_am': self.gebucht_am.isoformat() if self.gebucht_am else None,
            'storniert_am': self.storniert_am.isoformat() if self.storniert_am else None,
            'anmerkungen': self.anmerkungen,
            'kann_storniert_werden': self.kann_storniert_werden,
            'storno_frist_datum': self.storno_frist_datum.isoformat() if self.storno_frist_datum else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        if include_kunde and self.kunde:
            data['kunde'] = {
                'id': self.kunde.id,
                'firmierung': self.kunde.firmierung,
                'kundennummer': self.kunde.kundennummer,
            }

        if include_durchfuehrung and self.durchfuehrung:
            data['durchfuehrung'] = self.durchfuehrung.to_dict()

        return data

    # === CLASS METHODS ===

    @classmethod
    def get_by_kunde(cls, kunde_id: int, nur_aktive: bool = True):
        """Get all bookings for a customer."""
        query = cls.query.filter_by(kunde_id=kunde_id)
        if nur_aktive:
            query = query.filter(cls.status != BuchungStatus.STORNIERT.value)
        return query.order_by(cls.gebucht_am.desc()).all()

    @classmethod
    def get_by_durchfuehrung(cls, durchfuehrung_id: int):
        """Get all bookings for an execution."""
        return cls.query.filter_by(durchfuehrung_id=durchfuehrung_id).order_by(cls.gebucht_am).all()

    @classmethod
    def kunde_hat_gebucht(cls, kunde_id: int, durchfuehrung_id: int) -> bool:
        """Check if a customer has an active booking for an execution."""
        return cls.query.filter_by(
            kunde_id=kunde_id,
            durchfuehrung_id=durchfuehrung_id
        ).filter(cls.status != BuchungStatus.STORNIERT.value).first() is not None

    @classmethod
    def get_fuer_export(cls, von_datum: date = None, bis_datum: date = None):
        """Get bookings for Excel export (ERP integration).

        Returns bookings with status=gebucht within date range.
        """
        query = cls.query.filter_by(status=BuchungStatus.GEBUCHT.value)

        if von_datum:
            query = query.filter(cls.gebucht_am >= datetime.combine(von_datum, datetime.min.time()))
        if bis_datum:
            query = query.filter(cls.gebucht_am <= datetime.combine(bis_datum, datetime.max.time()))

        return query.order_by(cls.gebucht_am).all()


# Import at end to avoid circular imports
from datetime import timedelta
