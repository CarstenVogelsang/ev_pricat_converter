"""Schulung Service - Business Logic für Schulungen (PRD-010).

Enthält die Geschäftslogik für:
- Buchungen (mit automatischer Wartelisten-Logik)
- Stornierungen (mit Frist-Check)
- Wartelisten-Freischaltung
- E-Mail-Benachrichtigungen
"""
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional, Tuple
from decimal import Decimal

from app import db
from app.models import Kunde
from app.models.schulung import Schulung
from app.models.schulungsbuchung import Schulungsbuchung, BuchungStatus
from app.models.schulungsdurchfuehrung import Schulungsdurchfuehrung, DurchfuehrungStatus
from app.services.logging_service import log_event, log_hoch


@dataclass
class BuchungResult:
    """Result of a booking operation."""
    success: bool
    buchung: Optional[Schulungsbuchung] = None
    ist_warteliste: bool = False
    message: str = ''
    error: Optional[str] = None


@dataclass
class StornoResult:
    """Result of a cancellation operation."""
    success: bool
    innerhalb_frist: bool = True
    nachruecker_freigeschaltet: Optional[Schulungsbuchung] = None
    message: str = ''
    error: Optional[str] = None


class SchulungService:
    """Service class for training booking operations.

    All public methods handle their own database transactions
    and send appropriate email notifications.
    """

    def __init__(self):
        self._email_service = None
        self._template_service = None

    @property
    def email_service(self):
        """Lazy-loaded email service."""
        if self._email_service is None:
            from app.services.email_service import get_brevo_service
            self._email_service = get_brevo_service()
        return self._email_service

    @property
    def template_service(self):
        """Lazy-loaded template service."""
        if self._template_service is None:
            from app.services.email_template_service import get_email_template_service
            self._template_service = get_email_template_service()
        return self._template_service

    # === BUCHUNG ===

    def buchen(
        self,
        kunde_id: int,
        durchfuehrung_id: int,
        anmerkungen: Optional[str] = None,
        send_email: bool = True
    ) -> BuchungResult:
        """Create a booking for a training execution.

        Automatically places booking on waitlist if no seats available.

        Args:
            kunde_id: Customer ID
            durchfuehrung_id: Execution ID
            anmerkungen: Optional notes
            send_email: Whether to send confirmation email

        Returns:
            BuchungResult with success status and booking details
        """
        # Validate customer
        kunde = Kunde.query.get(kunde_id)
        if not kunde:
            return BuchungResult(
                success=False,
                error=f'Kunde {kunde_id} nicht gefunden'
            )

        # Validate execution
        durchfuehrung = Schulungsdurchfuehrung.query.get(durchfuehrung_id)
        if not durchfuehrung:
            return BuchungResult(
                success=False,
                error=f'Durchführung {durchfuehrung_id} nicht gefunden'
            )

        # Check if booking already exists
        existing = Schulungsbuchung.query.filter_by(
            kunde_id=kunde_id,
            durchfuehrung_id=durchfuehrung_id
        ).filter(Schulungsbuchung.status != BuchungStatus.STORNIERT.value).first()

        if existing:
            return BuchungResult(
                success=False,
                error='Kunde hat bereits eine aktive Buchung für diese Durchführung'
            )

        # Check if execution is bookable
        if durchfuehrung.status not in [DurchfuehrungStatus.GEPLANT.value, DurchfuehrungStatus.AKTIV.value]:
            return BuchungResult(
                success=False,
                error=f'Durchführung kann nicht gebucht werden (Status: {durchfuehrung.status})'
            )

        # Determine status based on availability
        ist_warteliste = durchfuehrung.ist_ausgebucht
        status = BuchungStatus.WARTELISTE if ist_warteliste else BuchungStatus.GEBUCHT

        # Get current price
        schulung = durchfuehrung.schulung
        preis = schulung.aktueller_preis

        # Create booking
        buchung = Schulungsbuchung(
            kunde_id=kunde_id,
            durchfuehrung_id=durchfuehrung_id,
            status=status.value,
            preis_bei_buchung=preis,
            anmerkungen=anmerkungen
        )

        db.session.add(buchung)

        # Log event
        if ist_warteliste:
            log_event(
                'schulungen',
                'warteliste_hinzugefuegt',
                f'Kunde "{kunde.firmierung}" auf Warteliste für "{schulung.titel}"',
                entity_type='Schulungsbuchung',
                entity_id=buchung.id
            )
            message = f'Buchung auf Warteliste für "{schulung.titel}"'
        else:
            log_event(
                'schulungen',
                'gebucht',
                f'Kunde "{kunde.firmierung}" für "{schulung.titel}" gebucht',
                entity_type='Schulungsbuchung',
                entity_id=buchung.id
            )
            message = f'Buchung für "{schulung.titel}" bestätigt'

        db.session.commit()

        # Send confirmation email
        if send_email:
            template_key = 'schulung_warteliste' if ist_warteliste else 'schulung_buchung_bestaetigung'
            self._send_booking_email(buchung, template_key)

        return BuchungResult(
            success=True,
            buchung=buchung,
            ist_warteliste=ist_warteliste,
            message=message
        )

    # === STORNIERUNG ===

    def stornieren(
        self,
        buchung_id: int,
        nachruecher_freischalten: bool = True,
        send_email: bool = True
    ) -> StornoResult:
        """Cancel a booking.

        Optionally promotes the next person from waitlist.

        Args:
            buchung_id: Booking ID
            nachruecher_freischalten: Whether to promote next from waitlist
            send_email: Whether to send cancellation email

        Returns:
            StornoResult with cancellation details
        """
        buchung = Schulungsbuchung.query.get(buchung_id)
        if not buchung:
            return StornoResult(
                success=False,
                error=f'Buchung {buchung_id} nicht gefunden'
            )

        if buchung.is_storniert:
            return StornoResult(
                success=False,
                error='Buchung ist bereits storniert'
            )

        # Check cancellation deadline
        innerhalb_frist = buchung.kann_storniert_werden
        war_gebucht = buchung.is_gebucht
        durchfuehrung = buchung.durchfuehrung
        kunde = buchung.kunde
        schulung = durchfuehrung.schulung

        # Cancel the booking
        buchung.stornieren()

        # Log event
        frist_text = 'innerhalb' if innerhalb_frist else 'außerhalb'
        log_hoch(
            'schulungen',
            'storniert',
            f'Buchung von "{kunde.firmierung}" für "{schulung.titel}" storniert ({frist_text} der Frist)',
            entity_type='Schulungsbuchung',
            entity_id=buchung.id
        )

        # Promote next from waitlist if this was a confirmed booking
        nachruecker = None
        if war_gebucht and nachruecher_freischalten:
            nachruecker = self._naechster_von_warteliste(durchfuehrung, send_email)

        db.session.commit()

        # Send cancellation email
        if send_email:
            self._send_booking_email(buchung, 'schulung_storniert')

        message = 'Buchung erfolgreich storniert'
        if not innerhalb_frist:
            message += ' (außerhalb der kostenfreien Stornofrist)'
        if nachruecker:
            message += f' - {nachruecker.kunde.firmierung} von Warteliste nachgerückt'

        return StornoResult(
            success=True,
            innerhalb_frist=innerhalb_frist,
            nachruecker_freigeschaltet=nachruecker,
            message=message
        )

    # === WARTELISTE ===

    def freischalten(
        self,
        buchung_id: int,
        send_email: bool = True
    ) -> BuchungResult:
        """Promote a waitlist booking to confirmed.

        Args:
            buchung_id: Booking ID to promote
            send_email: Whether to send promotion email

        Returns:
            BuchungResult with promotion details
        """
        buchung = Schulungsbuchung.query.get(buchung_id)
        if not buchung:
            return BuchungResult(
                success=False,
                error=f'Buchung {buchung_id} nicht gefunden'
            )

        if not buchung.is_warteliste:
            return BuchungResult(
                success=False,
                error='Nur Wartelisten-Buchungen können freigeschaltet werden'
            )

        # Check if there's actually space now
        durchfuehrung = buchung.durchfuehrung
        if durchfuehrung.freie_plaetze <= 0:
            return BuchungResult(
                success=False,
                error='Keine freien Plätze verfügbar'
            )

        # Promote booking
        buchung.von_warteliste_freischalten()

        kunde = buchung.kunde
        schulung = durchfuehrung.schulung

        log_event(
            'schulungen',
            'warteliste_freigeschaltet',
            f'Kunde "{kunde.firmierung}" für "{schulung.titel}" von Warteliste freigeschaltet',
            entity_type='Schulungsbuchung',
            entity_id=buchung.id
        )

        db.session.commit()

        # Send promotion email
        if send_email:
            self._send_booking_email(buchung, 'schulung_warteliste_freigabe')

        return BuchungResult(
            success=True,
            buchung=buchung,
            ist_warteliste=False,
            message=f'Buchung für "{schulung.titel}" bestätigt - von Warteliste freigeschaltet'
        )

    # === TERMINE ===

    def berechne_termine(
        self,
        durchfuehrung: Schulungsdurchfuehrung
    ) -> list:
        """Calculate individual dates based on execution pattern.

        Creates Schulungstermin objects based on terminmuster.

        Args:
            durchfuehrung: The execution to calculate dates for

        Returns:
            List of Schulungstermin objects (not yet committed)
        """
        from datetime import timedelta, time as dt_time
        from app.models.schulungsdurchfuehrung import Schulungstermin

        # Get pattern
        muster = durchfuehrung.terminmuster or {}
        wochentage = muster.get('wochentage', [])
        uhrzeit_str = muster.get('uhrzeit', '14:00')

        # Parse time
        try:
            stunde, minute = map(int, uhrzeit_str.split(':'))
            start_zeit = dt_time(stunde, minute)
        except (ValueError, AttributeError):
            start_zeit = dt_time(14, 0)

        # Map weekday names to numbers (0=Monday)
        tag_map = {
            'Mo': 0, 'Di': 1, 'Mi': 2, 'Do': 3, 'Fr': 4, 'Sa': 5, 'So': 6
        }

        gewaehlte_tage = [tag_map[t] for t in wochentage if t in tag_map]
        if not gewaehlte_tage:
            gewaehlte_tage = [0]  # Default to Monday

        # Get topics
        themen = durchfuehrung.schulung.themen_sortiert if durchfuehrung.schulung else []
        if not themen:
            return []

        # Generate dates
        termine = []
        aktuelles_datum = durchfuehrung.start_datum
        termin_nummer = 1

        for thema in themen:
            # Find next valid weekday
            while aktuelles_datum.weekday() not in gewaehlte_tage:
                aktuelles_datum += timedelta(days=1)

            # Calculate end time based on topic duration
            dauer_minuten = thema.dauer_minuten
            end_zeit = (
                datetime.combine(date.today(), start_zeit) +
                timedelta(minutes=dauer_minuten)
            ).time()

            # Create appointment
            termin = Schulungstermin(
                durchfuehrung_id=durchfuehrung.id,
                thema_id=thema.id,
                termin_nummer=termin_nummer,
                datum=aktuelles_datum,
                uhrzeit_von=start_zeit,
                uhrzeit_bis=end_zeit
            )
            termine.append(termin)

            # Move to next day for next topic
            aktuelles_datum += timedelta(days=1)
            termin_nummer += 1

        return termine

    # === HELPER METHODS ===

    def _naechster_von_warteliste(
        self,
        durchfuehrung: Schulungsdurchfuehrung,
        send_email: bool = True
    ) -> Optional[Schulungsbuchung]:
        """Promote the next person from waitlist.

        Args:
            durchfuehrung: The execution to check waitlist for
            send_email: Whether to send notification email

        Returns:
            The promoted booking, or None if waitlist was empty
        """
        # Get first in waitlist (ordered by booking date)
        naechste_buchung = Schulungsbuchung.query.filter_by(
            durchfuehrung_id=durchfuehrung.id,
            status=BuchungStatus.WARTELISTE.value
        ).order_by(Schulungsbuchung.gebucht_am).first()

        if not naechste_buchung:
            return None

        # Promote
        naechste_buchung.von_warteliste_freischalten()

        kunde = naechste_buchung.kunde
        schulung = durchfuehrung.schulung

        log_event(
            'schulungen',
            'nachruecker_freigeschaltet',
            f'Nachruecker "{kunde.firmierung}" für "{schulung.titel}" automatisch freigeschaltet',
            entity_type='Schulungsbuchung',
            entity_id=naechste_buchung.id
        )

        # Send email
        if send_email:
            self._send_booking_email(naechste_buchung, 'schulung_warteliste_freigabe')

        return naechste_buchung

    def _send_booking_email(
        self,
        buchung: Schulungsbuchung,
        template_key: str
    ) -> bool:
        """Send a booking-related email.

        Args:
            buchung: The booking
            template_key: Email template key

        Returns:
            True if email was sent successfully
        """
        try:
            kunde = buchung.kunde
            durchfuehrung = buchung.durchfuehrung
            schulung = durchfuehrung.schulung

            # Build context
            context = {
                'firmenname': kunde.firmierung,
                'schulung_titel': schulung.titel,
                'schulung_beschreibung': schulung.beschreibung,
                'start_datum': durchfuehrung.start_datum.strftime('%d.%m.%Y'),
                'uhrzeit': durchfuehrung.uhrzeit_formatiert,
                'wochentage': durchfuehrung.wochentage_formatiert,
                'preis': f'{buchung.preis_bei_buchung:.2f} EUR',
                'teams_link': durchfuehrung.teams_link or '',
                'storno_frist': buchung.storno_frist_datum.strftime('%d.%m.%Y') if buchung.storno_frist_datum else '',
                'link': '',  # Could be a link to customer booking overview
            }

            # Get primary contact email
            ansprechpartner = kunde.ansprechpartner_list
            if not ansprechpartner:
                return False

            email = ansprechpartner[0].email
            if not email:
                return False

            # Render template
            try:
                rendered = self.template_service.render(template_key, context, kunde)
            except ValueError:
                # Template not found - skip silently
                return False

            # Send email
            result = self.email_service.send(
                to=email,
                subject=rendered['subject'],
                html=rendered['html'],
                text=rendered.get('text')
            )

            return result.success

        except Exception as e:
            # Log error but don't fail the operation
            print(f'Error sending booking email: {e}')
            return False

    # === STATISTICS ===

    def get_statistik(self) -> dict:
        """Get overview statistics for dashboard.

        Returns:
            Dict with various counts and statistics
        """
        heute = date.today()

        return {
            'schulungen_aktiv': Schulung.query.filter_by(aktiv=True).count(),
            'durchfuehrungen_geplant': Schulungsdurchfuehrung.query.filter(
                Schulungsdurchfuehrung.status == DurchfuehrungStatus.GEPLANT.value,
                Schulungsdurchfuehrung.start_datum >= heute
            ).count(),
            'buchungen_offen': Schulungsbuchung.query.filter_by(
                status=BuchungStatus.GEBUCHT.value
            ).count(),
            'warteliste': Schulungsbuchung.query.filter_by(
                status=BuchungStatus.WARTELISTE.value
            ).count(),
        }


# Singleton instance
_schulung_service: Optional[SchulungService] = None


def get_schulung_service() -> SchulungService:
    """Get the schulung service singleton."""
    global _schulung_service
    if _schulung_service is None:
        _schulung_service = SchulungService()
    return _schulung_service
