"""Schulungsdurchfuehrung & Schulungstermin Models (PRD-010).

Eine Durchführung ist eine konkrete Instanz einer Schulung mit festgelegten Terminen.
Termine werden aus dem Terminmuster und den verknüpften Themen generiert.
"""
from datetime import datetime, date, time
from enum import Enum
from app import db


class DurchfuehrungStatus(Enum):
    """Status einer Schulungsdurchführung."""
    GEPLANT = 'geplant'           # Geplant, Buchungen möglich
    AKTIV = 'aktiv'               # Läuft gerade
    ABGESCHLOSSEN = 'abgeschlossen'  # Beendet
    ABGESAGT = 'abgesagt'         # Abgesagt (keine Durchführung)


class Schulungsdurchfuehrung(db.Model):
    """Konkrete Instanz einer Schulung mit Terminen.

    Terminmuster-Format (JSON):
    {
        "wochentage": ["Di", "Do"],   # Schulungstage
        "uhrzeit": "14:00",           # Startzeit
        "dauer_std": 2                # Optional: Überschreibt Themen-Dauer
    }
    """
    __tablename__ = 'schulungsdurchfuehrung'

    id = db.Column(db.Integer, primary_key=True)

    # Referenz zur Schulung (Template)
    schulung_id = db.Column(db.Integer, db.ForeignKey('schulung.id'), nullable=False)

    # === TERMINE ===

    # Erster Schulungstag
    start_datum = db.Column(db.Date, nullable=False)

    # Terminmuster als JSON
    terminmuster = db.Column(db.JSON, nullable=False)

    # === TEAMS-MEETING ===

    # Microsoft Teams Link für alle Termine
    teams_link = db.Column(db.String(500))

    # === STATUS ===

    # Aktueller Status
    status = db.Column(
        db.String(20),
        nullable=False,
        default=DurchfuehrungStatus.GEPLANT.value
    )

    # === NOTIZEN ===

    # Interne Anmerkungen (nur für Admins)
    anmerkungen = db.Column(db.Text)

    # === META ===

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # === RELATIONSHIPS ===

    schulung = db.relationship('Schulung', back_populates='durchfuehrungen')

    # Generierte Termine
    termine = db.relationship(
        'Schulungstermin',
        back_populates='durchfuehrung',
        cascade='all, delete-orphan',
        order_by='Schulungstermin.datum, Schulungstermin.uhrzeit_von'
    )

    # Buchungen für diese Durchführung
    buchungen = db.relationship(
        'Schulungsbuchung',
        back_populates='durchfuehrung',
        cascade='all, delete-orphan',
        lazy='dynamic'
    )

    def __repr__(self):
        return f'<Schulungsdurchfuehrung {self.id}: {self.schulung.titel if self.schulung else "?"} ab {self.start_datum}>'

    # === PROPERTIES ===

    @property
    def is_geplant(self) -> bool:
        return self.status == DurchfuehrungStatus.GEPLANT.value

    @property
    def is_aktiv(self) -> bool:
        return self.status == DurchfuehrungStatus.AKTIV.value

    @property
    def is_abgeschlossen(self) -> bool:
        return self.status == DurchfuehrungStatus.ABGESCHLOSSEN.value

    @property
    def is_abgesagt(self) -> bool:
        return self.status == DurchfuehrungStatus.ABGESAGT.value

    @property
    def ist_buchbar(self) -> bool:
        """True wenn Buchungen möglich sind (geplant + nicht ausgebucht)."""
        return self.is_geplant and not self.ist_ausgebucht

    @property
    def freie_plaetze(self) -> int:
        """Anzahl freier Plätze (Max - gebuchte Teilnehmer)."""
        return max(0, self.schulung.max_teilnehmer - self.anzahl_gebucht)

    @property
    def ist_ausgebucht(self) -> bool:
        """True wenn keine freien Plätze mehr."""
        return self.freie_plaetze <= 0

    @property
    def anzahl_gebucht(self) -> int:
        """Anzahl verbindlicher Buchungen (Status = gebucht)."""
        from app.models.schulungsbuchung import BuchungStatus
        return self.buchungen.filter_by(status=BuchungStatus.GEBUCHT.value).count()

    @property
    def anzahl_warteliste(self) -> int:
        """Anzahl Wartelisten-Buchungen."""
        from app.models.schulungsbuchung import BuchungStatus
        return self.buchungen.filter_by(status=BuchungStatus.WARTELISTE.value).count()

    @property
    def teilnehmer_gebucht(self) -> list:
        """Alle verbindlichen Buchungen."""
        from app.models.schulungsbuchung import BuchungStatus
        return self.buchungen.filter_by(status=BuchungStatus.GEBUCHT.value).all()

    @property
    def teilnehmer_warteliste(self) -> list:
        """Alle Wartelisten-Buchungen."""
        from app.models.schulungsbuchung import BuchungStatus
        return self.buchungen.filter_by(
            status=BuchungStatus.WARTELISTE.value
        ).order_by('gebucht_am').all()

    @property
    def erster_termin(self):
        """Erster Termin dieser Durchführung."""
        return self.termine[0] if self.termine else None

    @property
    def letzter_termin(self):
        """Letzter Termin dieser Durchführung."""
        return self.termine[-1] if self.termine else None

    @property
    def wochentage_formatiert(self) -> str:
        """Formatierte Wochentage aus Terminmuster."""
        if not self.terminmuster:
            return ''
        wochentage = self.terminmuster.get('wochentage', [])
        return ', '.join(wochentage)

    @property
    def uhrzeit_formatiert(self) -> str:
        """Formatierte Uhrzeit aus Terminmuster."""
        if not self.terminmuster:
            return ''
        return self.terminmuster.get('uhrzeit', '')

    # === STATUS TRANSITIONS ===

    def aktivieren(self):
        """Set status to AKTIV."""
        if self.status != DurchfuehrungStatus.GEPLANT.value:
            raise ValueError('Nur geplante Durchführungen können aktiviert werden')
        self.status = DurchfuehrungStatus.AKTIV.value

    def abschliessen(self):
        """Set status to ABGESCHLOSSEN."""
        if self.status != DurchfuehrungStatus.AKTIV.value:
            raise ValueError('Nur aktive Durchführungen können abgeschlossen werden')
        self.status = DurchfuehrungStatus.ABGESCHLOSSEN.value

    def absagen(self):
        """Set status to ABGESAGT."""
        if self.status not in [DurchfuehrungStatus.GEPLANT.value, DurchfuehrungStatus.AKTIV.value]:
            raise ValueError('Nur geplante oder aktive Durchführungen können abgesagt werden')
        self.status = DurchfuehrungStatus.ABGESAGT.value

    def to_dict(self, include_termine: bool = False, include_buchungen: bool = False):
        """Serialization for API/Export."""
        data = {
            'id': self.id,
            'schulung_id': self.schulung_id,
            'schulung_titel': self.schulung.titel if self.schulung else None,
            'start_datum': self.start_datum.isoformat() if self.start_datum else None,
            'terminmuster': self.terminmuster,
            'wochentage': self.wochentage_formatiert,
            'uhrzeit': self.uhrzeit_formatiert,
            'teams_link': self.teams_link,
            'status': self.status,
            'anmerkungen': self.anmerkungen,
            'freie_plaetze': self.freie_plaetze,
            'ist_ausgebucht': self.ist_ausgebucht,
            'ist_buchbar': self.ist_buchbar,
            'anzahl_gebucht': self.anzahl_gebucht,
            'anzahl_warteliste': self.anzahl_warteliste,
            'max_teilnehmer': self.schulung.max_teilnehmer if self.schulung else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        if include_termine:
            data['termine'] = [t.to_dict() for t in self.termine]

        if include_buchungen:
            data['buchungen'] = [b.to_dict() for b in self.buchungen.all()]

        return data

    # === CLASS METHODS ===

    @classmethod
    def get_kommende(cls, limit: int = 20):
        """Get upcoming executions (geplant/aktiv, ab heute)."""
        heute = date.today()
        return cls.query.filter(
            db.or_(
                cls.status == DurchfuehrungStatus.GEPLANT.value,
                cls.status == DurchfuehrungStatus.AKTIV.value
            ),
            cls.start_datum >= heute
        ).order_by(cls.start_datum).limit(limit).all()

    @classmethod
    def get_by_schulung(cls, schulung_id: int, nur_kommende: bool = True):
        """Get all executions for a training."""
        query = cls.query.filter_by(schulung_id=schulung_id)

        if nur_kommende:
            heute = date.today()
            query = query.filter(
                db.or_(
                    cls.status == DurchfuehrungStatus.GEPLANT.value,
                    cls.status == DurchfuehrungStatus.AKTIV.value
                ),
                cls.start_datum >= heute
            )

        return query.order_by(cls.start_datum).all()


class Schulungstermin(db.Model):
    """Konkreter Kalender-Termin (generiert aus Durchführung + Thema)."""
    __tablename__ = 'schulungstermin'

    id = db.Column(db.Integer, primary_key=True)

    # Referenz zur Durchführung
    durchfuehrung_id = db.Column(
        db.Integer,
        db.ForeignKey('schulungsdurchfuehrung.id'),
        nullable=False
    )

    # Referenz zum Thema (welches Thema wird behandelt)
    thema_id = db.Column(
        db.Integer,
        db.ForeignKey('schulungsthema.id'),
        nullable=False
    )

    # Termin-Nummer (1, 2, 3...)
    termin_nummer = db.Column(db.Integer, nullable=False)

    # === DATUM & ZEIT ===

    datum = db.Column(db.Date, nullable=False)
    uhrzeit_von = db.Column(db.Time, nullable=False)
    uhrzeit_bis = db.Column(db.Time, nullable=False)

    # === RELATIONSHIPS ===

    durchfuehrung = db.relationship('Schulungsdurchfuehrung', back_populates='termine')
    thema = db.relationship('Schulungsthema', back_populates='termine')

    def __repr__(self):
        return f'<Schulungstermin {self.termin_nummer}: {self.datum} {self.uhrzeit_von}>'

    @property
    def ist_vergangen(self) -> bool:
        """True wenn der Termin in der Vergangenheit liegt."""
        heute = date.today()
        return self.datum < heute

    @property
    def ist_heute(self) -> bool:
        """True wenn der Termin heute ist."""
        return self.datum == date.today()

    @property
    def dauer_minuten(self) -> int:
        """Dauer des Termins in Minuten."""
        von = datetime.combine(date.today(), self.uhrzeit_von)
        bis = datetime.combine(date.today(), self.uhrzeit_bis)
        delta = bis - von
        return int(delta.total_seconds() / 60)

    @property
    def zeitraum_formatiert(self) -> str:
        """Formatierter Zeitraum (z.B. '14:00 - 15:30')."""
        return f'{self.uhrzeit_von.strftime("%H:%M")} - {self.uhrzeit_bis.strftime("%H:%M")}'

    def to_dict(self):
        """Serialization for API/Export."""
        return {
            'id': self.id,
            'durchfuehrung_id': self.durchfuehrung_id,
            'thema_id': self.thema_id,
            'thema_titel': self.thema.titel if self.thema else None,
            'termin_nummer': self.termin_nummer,
            'datum': self.datum.isoformat() if self.datum else None,
            'uhrzeit_von': self.uhrzeit_von.strftime('%H:%M') if self.uhrzeit_von else None,
            'uhrzeit_bis': self.uhrzeit_bis.strftime('%H:%M') if self.uhrzeit_bis else None,
            'zeitraum': self.zeitraum_formatiert,
            'dauer_minuten': self.dauer_minuten,
            'ist_vergangen': self.ist_vergangen,
            'ist_heute': self.ist_heute,
        }
