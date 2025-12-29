"""Support ticket models for the ticket system.

This module contains the SupportTicket and TicketKommentar models,
as well as the enums for ticket type, status, and priority.
"""
from datetime import datetime
from enum import Enum

from app import db


class TicketTyp(str, Enum):
    """Types of support tickets."""
    FRAGE = 'frage'
    VERBESSERUNG = 'verbesserung'
    BUG = 'bug'
    SCHULUNG = 'schulung'
    DATEN = 'daten'
    SONSTIGES = 'sonstiges'

    @classmethod
    def choices(cls):
        """Return choices for form select fields."""
        labels = {
            cls.FRAGE: 'Frage',
            cls.VERBESSERUNG: 'Verbesserungsvorschlag',
            cls.BUG: 'Fehlermeldung',
            cls.SCHULUNG: 'Schulungsanfrage',
            cls.DATEN: 'Datenkorrektur',
            cls.SONSTIGES: 'Sonstiges',
        }
        return [(t.value, labels[t]) for t in cls]

    @classmethod
    def get_label(cls, value):
        """Get the German label for a ticket type value."""
        labels = {
            cls.FRAGE.value: 'Frage',
            cls.VERBESSERUNG.value: 'Verbesserungsvorschlag',
            cls.BUG.value: 'Fehlermeldung',
            cls.SCHULUNG.value: 'Schulungsanfrage',
            cls.DATEN.value: 'Datenkorrektur',
            cls.SONSTIGES.value: 'Sonstiges',
        }
        return labels.get(value, value)

    @classmethod
    def get_icon(cls, value):
        """Get the icon class for a ticket type.

        Returns icon with 'ti ' prefix for Tabler Icons compatibility.
        """
        icons = {
            cls.FRAGE.value: 'ti-help',
            cls.VERBESSERUNG.value: 'ti-bulb',
            cls.BUG.value: 'ti-alert-triangle',  # Changed from ti-bug for better visibility
            cls.SCHULUNG.value: 'ti-school',
            cls.DATEN.value: 'ti-database-edit',
            cls.SONSTIGES.value: 'ti-dots',
        }
        icon = icons.get(value, 'ti-ticket')
        return f'ti {icon}'


class TicketStatus(str, Enum):
    """Status values for support tickets."""
    OFFEN = 'offen'
    IN_BEARBEITUNG = 'in_bearbeitung'
    WARTE_AUF_KUNDE = 'warte_auf_kunde'
    GELOEST = 'geloest'
    GESCHLOSSEN = 'geschlossen'

    @classmethod
    def choices(cls):
        """Return choices for form select fields."""
        labels = {
            cls.OFFEN: 'Offen',
            cls.IN_BEARBEITUNG: 'In Bearbeitung',
            cls.WARTE_AUF_KUNDE: 'Warte auf Kunde',
            cls.GELOEST: 'Gelöst',
            cls.GESCHLOSSEN: 'Geschlossen',
        }
        return [(t.value, labels[t]) for t in cls]

    @classmethod
    def get_label(cls, value):
        """Get the German label for a status value."""
        labels = {
            cls.OFFEN.value: 'Offen',
            cls.IN_BEARBEITUNG.value: 'In Bearbeitung',
            cls.WARTE_AUF_KUNDE.value: 'Warte auf Kunde',
            cls.GELOEST.value: 'Gelöst',
            cls.GESCHLOSSEN.value: 'Geschlossen',
        }
        return labels.get(value, value)

    @classmethod
    def get_color(cls, value):
        """Get the Bootstrap color class for a status."""
        colors = {
            cls.OFFEN.value: 'warning',
            cls.IN_BEARBEITUNG.value: 'info',
            cls.WARTE_AUF_KUNDE.value: 'secondary',
            cls.GELOEST.value: 'success',
            cls.GESCHLOSSEN.value: 'dark',
        }
        return colors.get(value, 'secondary')

    @classmethod
    def aktive_status(cls):
        """Return list of status values that are considered 'open'."""
        return [cls.OFFEN.value, cls.IN_BEARBEITUNG.value, cls.WARTE_AUF_KUNDE.value]


class TicketPrioritaet(str, Enum):
    """Priority levels for support tickets."""
    NIEDRIG = 'niedrig'
    NORMAL = 'normal'
    HOCH = 'hoch'
    KRITISCH = 'kritisch'

    @classmethod
    def choices(cls):
        """Return choices for form select fields."""
        return [(p.value, p.value.capitalize()) for p in cls]

    @classmethod
    def get_label(cls, value):
        """Get the German label for a priority value."""
        return value.capitalize() if value else 'Normal'

    @classmethod
    def get_color(cls, value):
        """Get the Bootstrap color class for a priority."""
        colors = {
            cls.NIEDRIG.value: 'secondary',
            cls.NORMAL.value: 'primary',
            cls.HOCH.value: 'warning',
            cls.KRITISCH.value: 'danger',
        }
        return colors.get(value, 'primary')


class SupportTicket(db.Model):
    """Support ticket created by users.

    Captures user requests, questions, bug reports, and feature suggestions.
    Includes context information about where the ticket was created.
    """
    __tablename__ = 'support_ticket'

    id = db.Column(db.Integer, primary_key=True)

    # Human-readable ticket number (e.g., "T-2025-00042")
    nummer = db.Column(db.String(20), unique=True, nullable=False, index=True)

    # Content
    titel = db.Column(db.String(200), nullable=False)
    beschreibung = db.Column(db.Text, nullable=False)

    # Classification
    typ = db.Column(db.String(30), default=TicketTyp.FRAGE.value)
    status = db.Column(db.String(30), default=TicketStatus.OFFEN.value, index=True)
    prioritaet = db.Column(db.String(20), default=TicketPrioritaet.NORMAL.value)

    # Context (where was the ticket created from)
    modul_id = db.Column(db.Integer, db.ForeignKey('modul.id'), nullable=True)
    hilfetext_schluessel = db.Column(db.String(100), nullable=True)
    seiten_url = db.Column(db.String(500), nullable=True)

    # People involved
    erstellt_von_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )
    team_id = db.Column(
        db.Integer,
        db.ForeignKey('support_team.id'),
        nullable=True
    )
    bearbeiter_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=True
    )

    # Customer context (if ticket from customer)
    kunde_id = db.Column(db.Integer, db.ForeignKey('kunde.id'), nullable=True)

    # Timestamps
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    aktualisiert_am = db.Column(db.DateTime, onupdate=datetime.utcnow)
    geloest_am = db.Column(db.DateTime, nullable=True)
    geschlossen_am = db.Column(db.DateTime, nullable=True)

    # Relationships
    ersteller = db.relationship(
        'User',
        foreign_keys=[erstellt_von_id],
        backref='erstellte_tickets'
    )
    bearbeiter = db.relationship(
        'User',
        foreign_keys=[bearbeiter_id],
        backref='zugewiesene_tickets'
    )
    modul = db.relationship('Modul', backref='support_tickets')
    kunde = db.relationship('Kunde', backref='support_tickets')
    kommentare = db.relationship(
        'TicketKommentar',
        backref='ticket',
        lazy='dynamic',
        cascade='all, delete-orphan',
        order_by='TicketKommentar.erstellt_am'
    )

    def __repr__(self):
        return f'<SupportTicket {self.nummer}>'

    @classmethod
    def generate_nummer(cls):
        """Generate a unique ticket number.

        Format stored: YYYY-N (e.g., '2025-42')
        Display format: YY-HEX (e.g., '25-2A') via nummer_anzeige property
        """
        year = datetime.now().year

        # Find highest number this year (supports both old T-YYYY and new YYYY format)
        last = cls.query.filter(
            db.or_(
                cls.nummer.like(f'T-{year}-%'),  # Old format
                cls.nummer.like(f'{year}-%')     # New format
            )
        ).order_by(cls.id.desc()).first()

        if last:
            try:
                last_num = int(last.nummer.split('-')[-1])
                new_num = last_num + 1
            except (ValueError, IndexError):
                new_num = 1
        else:
            new_num = 1

        return f'{year}-{new_num}'

    @property
    def nummer_anzeige(self):
        """Get the display format for external users (hex-encoded).

        Converts internal format like '2025-42' to '25-2A'.
        Also supports legacy 'T-2025-00042' format.
        """
        try:
            # Parse the internal format
            parts = self.nummer.replace('T-', '').split('-')
            year = parts[0]
            seq_num = int(parts[-1])

            # Return YY-HEX format
            year_short = year[-2:]  # Last 2 digits of year
            hex_num = format(seq_num, 'X')  # Uppercase hex
            return f'{year_short}-{hex_num}'
        except (ValueError, IndexError, AttributeError):
            return self.nummer  # Fallback to stored value

    @property
    def nummer_intern(self):
        """Get the readable internal format for staff.

        Converts '2025-42' or 'T-2025-00042' to '#42 (2025)'.
        """
        try:
            parts = self.nummer.replace('T-', '').split('-')
            year = parts[0]
            seq_num = int(parts[-1])
            return f'#{seq_num} ({year})'
        except (ValueError, IndexError, AttributeError):
            return self.nummer  # Fallback to stored value

    @property
    def ist_offen(self):
        """Check if ticket is still open (not resolved or closed)."""
        return self.status in TicketStatus.aktive_status()

    @property
    def ist_geloest(self):
        """Check if ticket is resolved or closed."""
        return self.status in [TicketStatus.GELOEST.value, TicketStatus.GESCHLOSSEN.value]

    @property
    def typ_label(self):
        """Get the German label for the ticket type."""
        return TicketTyp.get_label(self.typ)

    @property
    def typ_icon(self):
        """Get the icon class for the ticket type."""
        return TicketTyp.get_icon(self.typ)

    @property
    def status_label(self):
        """Get the German label for the status."""
        return TicketStatus.get_label(self.status)

    @property
    def status_color(self):
        """Get the Bootstrap color class for the status."""
        return TicketStatus.get_color(self.status)

    @property
    def prioritaet_label(self):
        """Get the German label for the priority."""
        return TicketPrioritaet.get_label(self.prioritaet)

    @property
    def prioritaet_color(self):
        """Get the Bootstrap color class for the priority."""
        return TicketPrioritaet.get_color(self.prioritaet)

    @property
    def oeffentliche_kommentare(self):
        """Get public comments (visible to ticket creator)."""
        return self.kommentare.filter_by(ist_intern=False).all()

    @property
    def letzte_aktivitaet(self):
        """Get the timestamp of the last activity on this ticket."""
        last_comment = self.kommentare.order_by(
            TicketKommentar.erstellt_am.desc()
        ).first()
        if last_comment:
            return last_comment.erstellt_am
        return self.aktualisiert_am or self.erstellt_am

    def kann_bearbeiten(self, user):
        """Check if a user can edit this ticket."""
        # Admins and Mitarbeiter can edit all tickets
        if user.is_admin or user.is_mitarbeiter:
            return True
        # Creator can only view, not edit
        return False

    def kann_sehen(self, user):
        """Check if a user can view this ticket."""
        # Admins and Mitarbeiter can see all tickets
        if user.is_admin or user.is_mitarbeiter:
            return True
        # Creator can see their own ticket
        return self.erstellt_von_id == user.id


class TicketKommentar(db.Model):
    """Comment or reply on a support ticket.

    Can be public (visible to ticket creator) or internal (only for team).
    Status changes are also recorded as comments with ist_status_aenderung=True.
    """
    __tablename__ = 'ticket_kommentar'

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(
        db.Integer,
        db.ForeignKey('support_ticket.id'),
        nullable=False
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('user.id'),
        nullable=False
    )

    inhalt = db.Column(db.Text, nullable=False)

    # Type flags
    ist_intern = db.Column(db.Boolean, default=False)  # Only visible to team
    ist_status_aenderung = db.Column(db.Boolean, default=False)  # System-generated

    # Timestamps
    erstellt_am = db.Column(db.DateTime, default=datetime.utcnow)
    aktualisiert_am = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref='ticket_kommentare')

    def __repr__(self):
        return f'<TicketKommentar {self.id} on Ticket {self.ticket_id}>'

    def kann_sehen(self, user):
        """Check if a user can see this comment."""
        # Internal comments only visible to team
        if self.ist_intern:
            return user.is_admin or user.is_mitarbeiter
        return True
