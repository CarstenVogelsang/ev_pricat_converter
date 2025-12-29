"""Support service for ticket management.

This module provides the SupportService class for handling support ticket
operations including creation, updates, notifications, and team management.
"""
from datetime import datetime
from typing import Optional, List

from flask import url_for, current_app
from flask_login import current_user

from app import db
from app.models import (
    SupportTicket, TicketKommentar, SupportTeam, SupportTeamMitglied,
    TicketTyp, TicketStatus, TicketPrioritaet, Modul, User
)
from app.services.logging_service import log_event, log_mittel, log_hoch


class SupportService:
    """Service for support ticket operations."""

    def create_ticket(
        self,
        titel: str,
        beschreibung: str,
        typ: str = TicketTyp.FRAGE.value,
        prioritaet: str = TicketPrioritaet.NORMAL.value,
        modul_code: str = None,
        hilfetext_schluessel: str = None,
        seiten_url: str = None,
        ersteller: User = None
    ) -> SupportTicket:
        """Create a new support ticket.

        Args:
            titel: Ticket title (max 200 chars)
            beschreibung: Detailed description
            typ: Ticket type (from TicketTyp enum)
            prioritaet: Priority level (from TicketPrioritaet enum)
            modul_code: Code of the module where ticket was created
            hilfetext_schluessel: Key of the related help text
            seiten_url: URL where ticket was created
            ersteller: User creating the ticket (defaults to current_user)

        Returns:
            The created SupportTicket instance
        """
        if ersteller is None:
            ersteller = current_user

        # Generate unique ticket number
        nummer = SupportTicket.generate_nummer()

        # Find module if code provided
        modul_id = None
        modul = None
        if modul_code:
            modul = Modul.query.filter_by(code=modul_code).first()
            if modul:
                modul_id = modul.id

        # Get default team
        team = SupportTeam.get_default_team()

        # Get customer context if user is a customer
        kunde_id = None
        if hasattr(ersteller, 'kunde_id') and ersteller.kunde_id:
            kunde_id = ersteller.kunde_id

        # Create ticket
        ticket = SupportTicket(
            nummer=nummer,
            titel=titel[:200],  # Ensure max length
            beschreibung=beschreibung,
            typ=typ,
            status=TicketStatus.OFFEN.value,
            prioritaet=prioritaet,
            modul_id=modul_id,
            hilfetext_schluessel=hilfetext_schluessel,
            seiten_url=seiten_url,
            erstellt_von_id=ersteller.id,
            team_id=team.id if team else None,
            kunde_id=kunde_id
        )

        db.session.add(ticket)
        db.session.commit()

        # Log the event
        log_mittel(
            'support',
            'ticket_erstellt',
            f'Ticket {nummer} erstellt: {titel[:50]}',
            entity_type='support_ticket',
            entity_id=ticket.id
        )

        # Send notification to team
        self.notify_team_new_ticket(ticket)

        return ticket

    def add_kommentar(
        self,
        ticket: SupportTicket,
        inhalt: str,
        ist_intern: bool = False,
        user: User = None
    ) -> TicketKommentar:
        """Add a comment to a ticket.

        Args:
            ticket: The ticket to comment on
            inhalt: Comment content
            ist_intern: Whether comment is internal (only visible to team)
            user: User adding the comment (defaults to current_user)

        Returns:
            The created TicketKommentar instance
        """
        if user is None:
            user = current_user

        kommentar = TicketKommentar(
            ticket_id=ticket.id,
            user_id=user.id,
            inhalt=inhalt,
            ist_intern=ist_intern,
            ist_status_aenderung=False
        )

        db.session.add(kommentar)

        # Update ticket timestamp
        ticket.aktualisiert_am = datetime.utcnow()

        db.session.commit()

        # Log the event
        log_event(
            'support',
            'ticket_kommentar',
            f'Kommentar hinzugefügt ({"intern" if ist_intern else "öffentlich"})',
            wichtigkeit='niedrig',
            entity_type='support_ticket',
            entity_id=ticket.id
        )

        return kommentar

    def change_status(
        self,
        ticket: SupportTicket,
        neuer_status: str,
        kommentar_text: str = None,
        user: User = None
    ) -> None:
        """Change ticket status with optional comment.

        Args:
            ticket: The ticket to update
            neuer_status: New status value
            kommentar_text: Optional comment explaining the change
            user: User making the change (defaults to current_user)
        """
        if user is None:
            user = current_user

        alter_status = ticket.status
        ticket.status = neuer_status
        ticket.aktualisiert_am = datetime.utcnow()

        # Set timestamps for resolved/closed
        if neuer_status == TicketStatus.GELOEST.value and not ticket.geloest_am:
            ticket.geloest_am = datetime.utcnow()
        elif neuer_status == TicketStatus.GESCHLOSSEN.value and not ticket.geschlossen_am:
            ticket.geschlossen_am = datetime.utcnow()

        # Create status change comment
        status_text = f'Status geändert: {TicketStatus.get_label(alter_status)} → {TicketStatus.get_label(neuer_status)}'
        if kommentar_text:
            status_text += f'\n\n{kommentar_text}'

        kommentar = TicketKommentar(
            ticket_id=ticket.id,
            user_id=user.id,
            inhalt=status_text,
            ist_intern=False,
            ist_status_aenderung=True
        )
        db.session.add(kommentar)

        db.session.commit()

        # Log the event
        log_mittel(
            'support',
            'ticket_status_geaendert',
            f'{TicketStatus.get_label(alter_status)} → {TicketStatus.get_label(neuer_status)}',
            entity_type='support_ticket',
            entity_id=ticket.id
        )

    def assign_ticket(
        self,
        ticket: SupportTicket,
        bearbeiter: User,
        user: User = None
    ) -> None:
        """Assign a ticket to a team member.

        Args:
            ticket: The ticket to assign
            bearbeiter: User to assign the ticket to
            user: User making the assignment (defaults to current_user)
        """
        if user is None:
            user = current_user

        old_bearbeiter = ticket.bearbeiter
        ticket.bearbeiter_id = bearbeiter.id
        ticket.aktualisiert_am = datetime.utcnow()

        # If ticket was open, set to in_bearbeitung
        if ticket.status == TicketStatus.OFFEN.value:
            ticket.status = TicketStatus.IN_BEARBEITUNG.value

        db.session.commit()

        # Log the event
        log_event(
            'support',
            'ticket_zugewiesen',
            f'Zugewiesen an {bearbeiter.vorname} {bearbeiter.nachname}',
            wichtigkeit='niedrig',
            entity_type='support_ticket',
            entity_id=ticket.id
        )

    def get_tickets_for_user(self, user: User) -> List[SupportTicket]:
        """Get all tickets created by a user.

        Args:
            user: The user whose tickets to retrieve

        Returns:
            List of SupportTicket instances
        """
        return SupportTicket.query.filter_by(
            erstellt_von_id=user.id
        ).order_by(SupportTicket.erstellt_am.desc()).all()

    def get_all_tickets(
        self,
        status: str = None,
        typ: str = None,
        prioritaet: str = None,
        team_id: int = None,
        bearbeiter_id: int = None,
        nur_offene: bool = False
    ) -> List[SupportTicket]:
        """Get all tickets with optional filters.

        Args:
            status: Filter by status
            typ: Filter by type
            prioritaet: Filter by priority
            team_id: Filter by team
            bearbeiter_id: Filter by assigned user
            nur_offene: Only return open tickets

        Returns:
            List of filtered SupportTicket instances
        """
        query = SupportTicket.query

        if status:
            query = query.filter(SupportTicket.status == status)
        elif nur_offene:
            query = query.filter(
                SupportTicket.status.in_(TicketStatus.aktive_status())
            )

        if typ:
            query = query.filter(SupportTicket.typ == typ)

        if prioritaet:
            query = query.filter(SupportTicket.prioritaet == prioritaet)

        if team_id:
            query = query.filter(SupportTicket.team_id == team_id)

        if bearbeiter_id:
            query = query.filter(SupportTicket.bearbeiter_id == bearbeiter_id)

        return query.order_by(SupportTicket.erstellt_am.desc()).all()

    def get_ticket_stats(self) -> dict:
        """Get ticket statistics for dashboard.

        Returns:
            Dictionary with ticket counts
        """
        today = datetime.utcnow().date()

        return {
            'offen': SupportTicket.query.filter(
                SupportTicket.status == TicketStatus.OFFEN.value
            ).count(),
            'in_bearbeitung': SupportTicket.query.filter(
                SupportTicket.status == TicketStatus.IN_BEARBEITUNG.value
            ).count(),
            'warte_auf_kunde': SupportTicket.query.filter(
                SupportTicket.status == TicketStatus.WARTE_AUF_KUNDE.value
            ).count(),
            'heute_erstellt': SupportTicket.query.filter(
                db.func.date(SupportTicket.erstellt_am) == today
            ).count(),
            'gesamt': SupportTicket.query.count(),
        }

    def notify_team_new_ticket(self, ticket: SupportTicket) -> None:
        """Send email notification to team about new ticket.

        Args:
            ticket: The newly created ticket
        """
        if not ticket.team:
            current_app.logger.warning(
                f'No team assigned to ticket {ticket.nummer}, skipping notification'
            )
            return

        # Get team members with notifications enabled
        recipients = ticket.team.mitglieder_mit_benachrichtigung
        if not recipients:
            current_app.logger.warning(
                f'No team members to notify for ticket {ticket.nummer}'
            )
            return

        try:
            from app.services import get_brevo_service

            brevo = get_brevo_service()
            if not brevo.is_configured:
                current_app.logger.warning('Brevo not configured, skipping notification')
                return

            # Prepare context for email template
            context = {
                'ticket_nummer': ticket.nummer,
                'ticket_titel': ticket.titel,
                'ticket_typ': ticket.typ_label,
                'ticket_prioritaet': ticket.prioritaet_label,
                'ersteller_name': f'{ticket.ersteller.vorname} {ticket.ersteller.nachname}',
                'modul_name': ticket.modul.name if ticket.modul else 'Allgemein',
                'link': url_for('support_admin.ticket_detail', nummer=ticket.nummer, _external=True),
            }

            # Send to each team member
            for mitglied in recipients:
                user = mitglied.user
                if user and user.email:
                    result = brevo.send_with_template(
                        'support_ticket_neu',
                        user.email,
                        f'{user.vorname} {user.nachname}',
                        context
                    )
                    if not result.success:
                        current_app.logger.error(
                            f'Failed to send notification to {user.email}: {result.error}'
                        )

        except Exception as e:
            current_app.logger.error(f'Error sending ticket notification: {e}')


# Singleton instance
_support_service = None


def get_support_service() -> SupportService:
    """Get the singleton SupportService instance."""
    global _support_service
    if _support_service is None:
        _support_service = SupportService()
    return _support_service
