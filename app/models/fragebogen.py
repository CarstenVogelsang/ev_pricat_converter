"""Fragebogen (Questionnaire) models for Kunden-Dialog module."""
from datetime import datetime
from enum import Enum
import secrets

from app import db


class FragebogenStatus(Enum):
    """Status of a Fragebogen."""
    ENTWURF = 'entwurf'        # Draft - being edited
    AKTIV = 'aktiv'            # Active - can be filled out
    GESCHLOSSEN = 'geschlossen'  # Closed - no more responses


class TeilnahmeStatus(Enum):
    """Status of a FragebogenTeilnahme."""
    EINGELADEN = 'eingeladen'    # Invited but not started
    GESTARTET = 'gestartet'      # Started but not finished
    ABGESCHLOSSEN = 'abgeschlossen'  # Completed


class Fragebogen(db.Model):
    """Questionnaire definition.

    The questions are stored as JSON in definition_json with this schema:
    {
        "fragen": [
            {
                "id": "q1",
                "typ": "single_choice|multiple_choice|skala|text|ja_nein",
                "frage": "Question text",
                "optionen": ["Option A", "Option B"],  # for choice types
                "min": 1, "max": 5,                    # for skala
                "labels": {"1": "Low", "5": "High"},   # optional for skala
                "multiline": true,                     # for text
                "pflicht": true                        # required field
            }
        ]
    }
    """
    __tablename__ = 'fragebogen'

    id = db.Column(db.Integer, primary_key=True)
    titel = db.Column(db.String(200), nullable=False)
    beschreibung = db.Column(db.Text)
    definition_json = db.Column(db.JSON, nullable=False, default=dict)
    status = db.Column(db.String(20), nullable=False, default=FragebogenStatus.ENTWURF.value)

    # Creator reference
    erstellt_von_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)

    # Timestamps
    aktiviert_am = db.Column(db.DateTime)  # When status changed to AKTIV
    geschlossen_am = db.Column(db.DateTime)  # When status changed to GESCHLOSSEN
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    erstellt_von = db.relationship('User', backref=db.backref('erstellte_frageboegen', lazy='dynamic'))
    teilnahmen = db.relationship('FragebogenTeilnahme', back_populates='fragebogen',
                                 cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Fragebogen {self.titel}>'

    @property
    def fragen(self) -> list:
        """Get the list of questions from definition_json."""
        if self.definition_json and 'fragen' in self.definition_json:
            return self.definition_json['fragen']
        return []

    @property
    def anzahl_fragen(self) -> int:
        """Get number of questions."""
        return len(self.fragen)

    @property
    def anzahl_teilnehmer(self) -> int:
        """Get number of participants."""
        return len(self.teilnahmen)

    @property
    def anzahl_abgeschlossen(self) -> int:
        """Get number of completed participations."""
        return sum(1 for t in self.teilnahmen if t.status == TeilnahmeStatus.ABGESCHLOSSEN.value)

    @property
    def is_entwurf(self) -> bool:
        return self.status == FragebogenStatus.ENTWURF.value

    @property
    def is_aktiv(self) -> bool:
        return self.status == FragebogenStatus.AKTIV.value

    @property
    def is_geschlossen(self) -> bool:
        return self.status == FragebogenStatus.GESCHLOSSEN.value

    def aktivieren(self):
        """Set status to AKTIV."""
        self.status = FragebogenStatus.AKTIV.value
        self.aktiviert_am = datetime.utcnow()

    def schliessen(self):
        """Set status to GESCHLOSSEN."""
        self.status = FragebogenStatus.GESCHLOSSEN.value
        self.geschlossen_am = datetime.utcnow()

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'titel': self.titel,
            'beschreibung': self.beschreibung,
            'definition_json': self.definition_json,
            'status': self.status,
            'erstellt_von_id': self.erstellt_von_id,
            'erstellt_am': self.erstellt_am.isoformat() if self.erstellt_am else None,
            'aktiviert_am': self.aktiviert_am.isoformat() if self.aktiviert_am else None,
            'geschlossen_am': self.geschlossen_am.isoformat() if self.geschlossen_am else None,
            'anzahl_fragen': self.anzahl_fragen,
            'anzahl_teilnehmer': self.anzahl_teilnehmer,
            'anzahl_abgeschlossen': self.anzahl_abgeschlossen,
        }


class FragebogenTeilnahme(db.Model):
    """Participation of a Kunde in a Fragebogen.

    Links a Kunde to a Fragebogen with a unique Magic-Link token.
    Each Kunde can only participate once per Fragebogen.
    """
    __tablename__ = 'fragebogen_teilnahme'
    __table_args__ = (
        db.UniqueConstraint('fragebogen_id', 'kunde_id', name='uq_fragebogen_kunde'),
    )

    id = db.Column(db.Integer, primary_key=True)
    fragebogen_id = db.Column(db.Integer, db.ForeignKey('fragebogen.id'), nullable=False)
    kunde_id = db.Column(db.Integer, db.ForeignKey('kunde.id'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default=TeilnahmeStatus.EINGELADEN.value)

    # Timestamps
    eingeladen_am = db.Column(db.DateTime, default=datetime.utcnow)
    gestartet_am = db.Column(db.DateTime)
    abgeschlossen_am = db.Column(db.DateTime)

    # Email tracking
    einladung_gesendet_am = db.Column(db.DateTime)  # When invitation email was sent

    # Relationships
    fragebogen = db.relationship('Fragebogen', back_populates='teilnahmen')
    kunde = db.relationship('Kunde', backref=db.backref('fragebogen_teilnahmen', lazy='dynamic'))
    antworten = db.relationship('FragebogenAntwort', back_populates='teilnahme',
                                cascade='all, delete-orphan')

    def __repr__(self):
        return f'<FragebogenTeilnahme fragebogen={self.fragebogen_id} kunde={self.kunde_id}>'

    @classmethod
    def create_for_kunde(cls, fragebogen_id: int, kunde_id: int):
        """Create a new participation with generated token.

        Args:
            fragebogen_id: The Fragebogen ID
            kunde_id: The Kunde ID

        Returns:
            FragebogenTeilnahme instance (not yet committed)
        """
        return cls(
            fragebogen_id=fragebogen_id,
            kunde_id=kunde_id,
            token=secrets.token_urlsafe(48)  # 64 chars URL-safe
        )

    @property
    def is_eingeladen(self) -> bool:
        return self.status == TeilnahmeStatus.EINGELADEN.value

    @property
    def is_gestartet(self) -> bool:
        return self.status == TeilnahmeStatus.GESTARTET.value

    @property
    def is_abgeschlossen(self) -> bool:
        return self.status == TeilnahmeStatus.ABGESCHLOSSEN.value

    def starten(self):
        """Mark participation as started."""
        if self.is_eingeladen:
            self.status = TeilnahmeStatus.GESTARTET.value
            self.gestartet_am = datetime.utcnow()

    def abschliessen(self):
        """Mark participation as completed."""
        self.status = TeilnahmeStatus.ABGESCHLOSSEN.value
        self.abgeschlossen_am = datetime.utcnow()

    def get_antwort(self, frage_id: str):
        """Get answer for a specific question."""
        for antwort in self.antworten:
            if antwort.frage_id == frage_id:
                return antwort
        return None

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'fragebogen_id': self.fragebogen_id,
            'kunde_id': self.kunde_id,
            'token': self.token,
            'status': self.status,
            'eingeladen_am': self.eingeladen_am.isoformat() if self.eingeladen_am else None,
            'gestartet_am': self.gestartet_am.isoformat() if self.gestartet_am else None,
            'abgeschlossen_am': self.abgeschlossen_am.isoformat() if self.abgeschlossen_am else None,
            'einladung_gesendet_am': self.einladung_gesendet_am.isoformat() if self.einladung_gesendet_am else None,
        }


class FragebogenAntwort(db.Model):
    """Answer to a question in a Fragebogen.

    Stores the answer as JSON to support different question types:
    - single_choice: {"value": "Option A"}
    - multiple_choice: {"values": ["Option A", "Option C"]}
    - skala: {"value": 4}
    - text: {"value": "Free text answer"}
    - ja_nein: {"value": true}
    """
    __tablename__ = 'fragebogen_antwort'
    __table_args__ = (
        db.UniqueConstraint('teilnahme_id', 'frage_id', name='uq_teilnahme_frage'),
    )

    id = db.Column(db.Integer, primary_key=True)
    teilnahme_id = db.Column(db.Integer, db.ForeignKey('fragebogen_teilnahme.id'), nullable=False)
    frage_id = db.Column(db.String(50), nullable=False)  # References id in definition_json
    antwort_json = db.Column(db.JSON, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    teilnahme = db.relationship('FragebogenTeilnahme', back_populates='antworten')

    def __repr__(self):
        return f'<FragebogenAntwort teilnahme={self.teilnahme_id} frage={self.frage_id}>'

    @property
    def value(self):
        """Get the primary value from the answer."""
        if not self.antwort_json:
            return None
        return self.antwort_json.get('value') or self.antwort_json.get('values')

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'teilnahme_id': self.teilnahme_id,
            'frage_id': self.frage_id,
            'antwort_json': self.antwort_json,
            'value': self.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
