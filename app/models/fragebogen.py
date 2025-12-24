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

    Schema V1 (flache Liste):
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

    Schema V2 (mehrseitig mit Wizard):
    {
        "version": 2,
        "seiten": [
            {
                "id": "s1",
                "titel": "Allgemeine Fragen",
                "hilfetext": "Optionaler Hilfetext für die Seite",
                "fragen": [
                    {
                        "id": "q1",
                        "typ": "text|dropdown|date|number|group|table|url|...",
                        "frage": "Frage",
                        "pflicht": true,
                        "prefill": "kunde.firmierung",  # V2: Vorausfüllung
                        "hilfetext": "Hilfe zur Frage",  # V2: Frage-Hilfe
                        "show_if": {"frage_id": "x", "equals": true}  # V2: Bedingte Anzeige
                    }
                ]
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

    # Versioning: V1 -> V2 -> V3 chain
    vorgaenger_id = db.Column(db.Integer, db.ForeignKey('fragebogen.id'), nullable=True)
    version_nummer = db.Column(db.Integer, default=1, nullable=False)

    # Soft-delete via archiving
    archiviert = db.Column(db.Boolean, default=False, nullable=False)
    archiviert_am = db.Column(db.DateTime, nullable=True)

    # Relationships
    erstellt_von = db.relationship('User', backref=db.backref('erstellte_frageboegen', lazy='dynamic'))
    teilnahmen = db.relationship('FragebogenTeilnahme', back_populates='fragebogen',
                                 cascade='all, delete-orphan')

    # Self-referential relationship for version chain
    vorgaenger = db.relationship(
        'Fragebogen',
        remote_side='Fragebogen.id',
        backref=db.backref('nachfolger', lazy='dynamic'),
        foreign_keys=[vorgaenger_id]
    )

    def __repr__(self):
        return f'<Fragebogen {self.titel}>'

    @property
    def is_v2(self) -> bool:
        """Check if this fragebogen uses V2 schema (with pages)."""
        return self.definition_json and self.definition_json.get('version') == 2

    @property
    def seiten(self) -> list:
        """Get the list of pages (V2 only, empty for V1)."""
        if self.is_v2:
            return self.definition_json.get('seiten', [])
        return []

    @property
    def fragen(self) -> list:
        """Get the list of all questions from definition_json.

        Works with both V1 (flat list) and V2 (pages) schemas.
        """
        if not self.definition_json:
            return []

        # V2: Collect questions from all pages
        if self.is_v2:
            alle_fragen = []
            for seite in self.definition_json.get('seiten', []):
                alle_fragen.extend(seite.get('fragen', []))
            return alle_fragen

        # V1: Direct fragen list
        return self.definition_json.get('fragen', [])

    @property
    def fragen_mit_prefill(self) -> list:
        """Get all questions that have prefill configured (V2 only)."""
        return [f for f in self.fragen if f.get('prefill')]

    @property
    def anzahl_fragen(self) -> int:
        """Get number of questions."""
        return len(self.fragen)

    @property
    def anzahl_seiten(self) -> int:
        """Get number of pages (1 for V1, actual count for V2)."""
        if self.is_v2:
            return len(self.seiten)
        return 1 if self.fragen else 0

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

    @property
    def is_archiviert(self) -> bool:
        """Check if this Fragebogen is archived."""
        return self.archiviert

    @property
    def ist_neueste_version(self) -> bool:
        """Check if this is the newest version (has no successors).

        Returns True if no newer version exists in the chain.
        Used to determine if duplication is allowed.
        """
        return self.nachfolger.count() == 0

    @property
    def version_kette(self) -> list:
        """Get the complete version chain, starting from V1.

        Returns a list of all Fragebögen in this version chain,
        ordered from oldest (V1) to newest.
        """
        # Navigate to V1 (root of the chain)
        root = self
        while root.vorgaenger:
            root = root.vorgaenger

        # Collect all versions forward
        chain = [root]
        current = root
        while current.nachfolger.first():
            current = current.nachfolger.first()
            chain.append(current)

        return chain

    def aktivieren(self):
        """Set status to AKTIV."""
        self.status = FragebogenStatus.AKTIV.value
        self.aktiviert_am = datetime.utcnow()

    def schliessen(self):
        """Set status to GESCHLOSSEN."""
        self.status = FragebogenStatus.GESCHLOSSEN.value
        self.geschlossen_am = datetime.utcnow()

    def reaktivieren(self):
        """Set status back to AKTIV from GESCHLOSSEN.

        Only closed questionnaires can be reactivated.
        The geschlossen_am timestamp is preserved as history.
        """
        if self.status != FragebogenStatus.GESCHLOSSEN.value:
            raise ValueError('Nur geschlossene Fragebögen können reaktiviert werden')
        self.status = FragebogenStatus.AKTIV.value
        # geschlossen_am bleibt erhalten als Historie

    def archivieren(self):
        """Archive this Fragebogen (soft-delete).

        Archived Fragebögen are hidden from the default list view
        but can be shown with a filter. They cannot be deleted.
        """
        self.archiviert = True
        self.archiviert_am = datetime.utcnow()

    def dearchivieren(self):
        """Restore an archived Fragebogen."""
        self.archiviert = False
        self.archiviert_am = None

    @property
    def teilnehmer_ohne_einladung(self) -> int:
        """Count participants who haven't received invitation email."""
        return sum(1 for t in self.teilnahmen if t.einladung_gesendet_am is None)

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
            # Versioning
            'version_nummer': self.version_nummer,
            'vorgaenger_id': self.vorgaenger_id,
            'ist_neueste_version': self.ist_neueste_version,
            # Archiving
            'archiviert': self.archiviert,
            'archiviert_am': self.archiviert_am.isoformat() if self.archiviert_am else None,
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

    # V2: Prefill snapshot for change detection
    # Stores the original values of prefilled fields when participation started
    # Used to detect which fields the customer changed from their stored data
    prefill_snapshot_json = db.Column(db.JSON, nullable=True)

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

    def get_geaenderte_felder(self) -> list:
        """Compare prefill snapshot with answers, return changed fields.

        Returns a list of dicts with:
        - frage_id: The question ID
        - prefill_key: The prefill mapping key (e.g., 'kunde.firmierung')
        - original: The original value from snapshot
        - neu: The new value from answer
        """
        if not self.prefill_snapshot_json:
            return []

        changes = []
        for frage in self.fragebogen.fragen_mit_prefill:
            prefill_key = frage.get('prefill')
            if not prefill_key:
                continue

            original = self.prefill_snapshot_json.get(prefill_key)
            antwort = self.get_antwort(frage['id'])

            if antwort:
                neue_value = antwort.value
                # Normalize for comparison (handle empty strings vs None)
                original_normalized = original if original else ''
                neue_normalized = neue_value if neue_value else ''

                if original_normalized != neue_normalized:
                    changes.append({
                        'frage_id': frage['id'],
                        'prefill_key': prefill_key,
                        'original': original,
                        'neu': neue_value
                    })

        return changes

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
            'prefill_snapshot_json': self.prefill_snapshot_json,
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
