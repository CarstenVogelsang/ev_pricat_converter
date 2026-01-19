"""Mailing models for Kunden-Mailing module (PRD-013)."""
from datetime import datetime
from enum import Enum
import secrets

from sqlalchemy.orm.attributes import flag_modified

from app import db


class MailingStatus(Enum):
    """Status of a Mailing."""
    ENTWURF = 'entwurf'        # Draft - being edited
    VERSENDET = 'versendet'    # Sent - at least partially


class EmpfaengerStatus(Enum):
    """Status of a MailingEmpfaenger."""
    AUSSTEHEND = 'ausstehend'      # Not yet sent
    VERSENDET = 'versendet'        # Successfully sent
    FEHLGESCHLAGEN = 'fehlgeschlagen'  # Failed to send


class Mailing(db.Model):
    """Marketing mailing/newsletter.

    Supports a modular section system (Baukasten) for email content:
    {
        "sektionen": [
            {
                "id": "s1",
                "typ": "header",
                "config": {"zeige_logo": true}
            },
            {
                "id": "s2",
                "typ": "text_bild",
                "config": {"inhalt_html": "...", "bild_url": null}
            },
            {
                "id": "s3",
                "typ": "fragebogen_cta",
                "config": {"button_text": "Jetzt teilnehmen"}
            },
            {
                "id": "s4",
                "typ": "footer",
                "config": {"zeige_abmelde_link": true}
            }
        ]
    }
    """
    __tablename__ = 'mailing'

    id = db.Column(db.Integer, primary_key=True)
    titel = db.Column(db.String(200), nullable=False)
    betreff = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=MailingStatus.ENTWURF.value)
    sektionen_json = db.Column(db.JSON, default=dict)

    # Optional Fragebogen integration (PRD-006)
    fragebogen_id = db.Column(db.Integer, db.ForeignKey('fragebogen.id'), nullable=True)

    # Creator reference
    erstellt_von_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    gesendet_am = db.Column(db.DateTime, nullable=True)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Cached statistics (updated after each send batch)
    anzahl_empfaenger = db.Column(db.Integer, default=0)
    anzahl_versendet = db.Column(db.Integer, default=0)
    anzahl_fehlgeschlagen = db.Column(db.Integer, default=0)

    # Relationships
    erstellt_von = db.relationship('User', backref=db.backref('erstellte_mailings', lazy='dynamic'))
    fragebogen = db.relationship('Fragebogen', backref=db.backref('mailings', lazy='dynamic'))
    empfaenger = db.relationship('MailingEmpfaenger', back_populates='mailing',
                                 cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Mailing {self.titel}>'

    @property
    def sektionen(self) -> list:
        """Get the list of sections from sektionen_json."""
        if not self.sektionen_json:
            return []
        return self.sektionen_json.get('sektionen', [])

    @property
    def anzahl_sektionen(self) -> int:
        """Get number of sections."""
        return len(self.sektionen)

    @property
    def hat_fragebogen(self) -> bool:
        """Check if this mailing has a linked Fragebogen."""
        return self.fragebogen_id is not None

    @property
    def hat_fragebogen_cta(self) -> bool:
        """Check if this mailing has a Fragebogen CTA section."""
        return any(s.get('typ') == 'fragebogen_cta' for s in self.sektionen)

    @property
    def is_entwurf(self) -> bool:
        return self.status == MailingStatus.ENTWURF.value

    @property
    def is_versendet(self) -> bool:
        return self.status == MailingStatus.VERSENDET.value

    @property
    def anzahl_ausstehend(self) -> int:
        """Get number of pending recipients."""
        return sum(1 for e in self.empfaenger if e.is_ausstehend)

    @property
    def anzahl_klicks(self) -> int:
        """Get total number of clicks across all recipients."""
        return sum(len(e.klicks) for e in self.empfaenger)

    @property
    def klickrate(self) -> float:
        """Get click rate as percentage (0-100)."""
        if self.anzahl_versendet == 0:
            return 0.0
        klicker = sum(1 for e in self.empfaenger if e.hat_geklickt)
        return (klicker / self.anzahl_versendet) * 100

    def add_sektion(self, typ: str, config: dict = None) -> str:
        """Add a new section and return its ID."""
        if not self.sektionen_json:
            self.sektionen_json = {'sektionen': []}

        sektion_id = f"s{len(self.sektionen) + 1}"
        self.sektionen_json['sektionen'].append({
            'id': sektion_id,
            'typ': typ,
            'config': config or {}
        })

        # Mark JSON field as modified so SQLAlchemy commits the change
        flag_modified(self, 'sektionen_json')

        return sektion_id

    def update_sektionen(self, sektionen: list):
        """Update all sections at once."""
        self.sektionen_json = {'sektionen': sektionen}
        flag_modified(self, 'sektionen_json')

    def versenden(self):
        """Mark mailing as sent."""
        self.status = MailingStatus.VERSENDET.value
        self.gesendet_am = datetime.utcnow()

    def update_statistik(self):
        """Recalculate cached statistics from empfaenger."""
        self.anzahl_empfaenger = len(self.empfaenger)
        self.anzahl_versendet = sum(1 for e in self.empfaenger if e.is_versendet)
        self.anzahl_fehlgeschlagen = sum(1 for e in self.empfaenger if e.is_fehlgeschlagen)

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'titel': self.titel,
            'betreff': self.betreff,
            'status': self.status,
            'sektionen_json': self.sektionen_json,
            'fragebogen_id': self.fragebogen_id,
            'erstellt_von_id': self.erstellt_von_id,
            'erstellt_am': self.erstellt_am.isoformat() if self.erstellt_am else None,
            'gesendet_am': self.gesendet_am.isoformat() if self.gesendet_am else None,
            'anzahl_empfaenger': self.anzahl_empfaenger,
            'anzahl_versendet': self.anzahl_versendet,
            'anzahl_fehlgeschlagen': self.anzahl_fehlgeschlagen,
            'anzahl_klicks': self.anzahl_klicks,
        }


class MailingEmpfaenger(db.Model):
    """Recipient of a Mailing.

    Links a Kunde to a Mailing with status tracking.
    Each Kunde can only be added once per Mailing.
    """
    __tablename__ = 'mailing_empfaenger'
    __table_args__ = (
        db.UniqueConstraint('mailing_id', 'kunde_id', name='uq_mailing_kunde'),
    )

    id = db.Column(db.Integer, primary_key=True)
    mailing_id = db.Column(db.Integer, db.ForeignKey('mailing.id'), nullable=False)
    kunde_id = db.Column(db.Integer, db.ForeignKey('kunde.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=EmpfaengerStatus.AUSSTEHEND.value)

    # Tracking token for click tracking
    tracking_token = db.Column(db.String(100), unique=True, nullable=True, index=True)

    # Timestamps
    hinzugefuegt_am = db.Column(db.DateTime, default=datetime.utcnow)
    versendet_am = db.Column(db.DateTime, nullable=True)
    fehler_meldung = db.Column(db.Text, nullable=True)

    # FK to FragebogenTeilnahme (created on send if mailing has Fragebogen)
    fragebogen_teilnahme_id = db.Column(db.Integer, db.ForeignKey('fragebogen_teilnahme.id'), nullable=True)

    # Relationships
    mailing = db.relationship('Mailing', back_populates='empfaenger')
    kunde = db.relationship('Kunde', backref=db.backref('mailing_empfaenger', lazy='dynamic'))
    fragebogen_teilnahme = db.relationship('FragebogenTeilnahme',
                                           backref=db.backref('mailing_empfaenger', uselist=False))
    klicks = db.relationship('MailingKlick', back_populates='empfaenger',
                             cascade='all, delete-orphan')

    def __repr__(self):
        return f'<MailingEmpfaenger mailing={self.mailing_id} kunde={self.kunde_id}>'

    @classmethod
    def create_for_kunde(cls, mailing_id: int, kunde_id: int):
        """Create a new empfaenger with generated tracking token.

        Args:
            mailing_id: The Mailing ID
            kunde_id: The Kunde ID

        Returns:
            MailingEmpfaenger instance (not yet committed)
        """
        return cls(
            mailing_id=mailing_id,
            kunde_id=kunde_id,
            tracking_token=secrets.token_urlsafe(32)
        )

    @property
    def is_ausstehend(self) -> bool:
        return self.status == EmpfaengerStatus.AUSSTEHEND.value

    @property
    def is_versendet(self) -> bool:
        return self.status == EmpfaengerStatus.VERSENDET.value

    @property
    def is_fehlgeschlagen(self) -> bool:
        return self.status == EmpfaengerStatus.FEHLGESCHLAGEN.value

    @property
    def hat_geklickt(self) -> bool:
        """Check if this recipient has clicked any link."""
        return len(self.klicks) > 0

    @property
    def anzahl_klicks(self) -> int:
        """Get number of clicks from this recipient."""
        return len(self.klicks)

    def mark_versendet(self):
        """Mark as successfully sent."""
        self.status = EmpfaengerStatus.VERSENDET.value
        self.versendet_am = datetime.utcnow()

    def mark_fehlgeschlagen(self, fehler: str):
        """Mark as failed with error message."""
        self.status = EmpfaengerStatus.FEHLGESCHLAGEN.value
        self.fehler_meldung = fehler

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'mailing_id': self.mailing_id,
            'kunde_id': self.kunde_id,
            'status': self.status,
            'tracking_token': self.tracking_token,
            'hinzugefuegt_am': self.hinzugefuegt_am.isoformat() if self.hinzugefuegt_am else None,
            'versendet_am': self.versendet_am.isoformat() if self.versendet_am else None,
            'fehler_meldung': self.fehler_meldung,
            'fragebogen_teilnahme_id': self.fragebogen_teilnahme_id,
            'anzahl_klicks': self.anzahl_klicks,
        }


class MailingKlick(db.Model):
    """Click tracking for Mailing links."""
    __tablename__ = 'mailing_klick'

    id = db.Column(db.Integer, primary_key=True)
    empfaenger_id = db.Column(db.Integer, db.ForeignKey('mailing_empfaenger.id'), nullable=False)
    link_typ = db.Column(db.String(50), nullable=False)  # 'fragebogen', 'abmelden', 'custom'
    geklickt_am = db.Column(db.DateTime, default=datetime.utcnow)

    # Optional: Original URL that was clicked
    url = db.Column(db.String(500), nullable=True)

    # Relationships
    empfaenger = db.relationship('MailingEmpfaenger', back_populates='klicks')

    def __repr__(self):
        return f'<MailingKlick empfaenger={self.empfaenger_id} typ={self.link_typ}>'

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'empfaenger_id': self.empfaenger_id,
            'link_typ': self.link_typ,
            'geklickt_am': self.geklickt_am.isoformat() if self.geklickt_am else None,
            'url': self.url,
        }


class MailingZielgruppe(db.Model):
    """Saved target group for Mailings.

    Stores filter criteria that can be reused for multiple mailings.
    Filter JSON schema:
    {
        "kriterien": [
            {"feld": "branche_id", "operator": "equals", "wert": 5},
            {"feld": "plz", "operator": "starts_with", "wert": "8"},
            {"feld": "klassifikation", "operator": "in", "wert": ["A", "B"]}
        ],
        "verknuepfung": "AND"  # or "OR"
    }
    """
    __tablename__ = 'mailing_zielgruppe'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    beschreibung = db.Column(db.Text, nullable=True)
    filter_json = db.Column(db.JSON, default=dict)

    # Creator reference
    erstellt_von_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    erstellt_von = db.relationship('User', backref=db.backref('erstellte_zielgruppen', lazy='dynamic'))

    def __repr__(self):
        return f'<MailingZielgruppe {self.name}>'

    @property
    def anzahl_kriterien(self) -> int:
        """Get number of filter criteria."""
        if not self.filter_json:
            return 0
        return len(self.filter_json.get('kriterien', []))

    def to_dict(self):
        """Return dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'beschreibung': self.beschreibung,
            'filter_json': self.filter_json,
            'erstellt_von_id': self.erstellt_von_id,
            'erstellt_am': self.erstellt_am.isoformat() if self.erstellt_am else None,
            'anzahl_kriterien': self.anzahl_kriterien,
        }
