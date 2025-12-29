"""User-facing support routes for ticket management.

Blueprint: support_bp
Prefix: /support/

This module provides routes for users to create and manage their support tickets.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user

from app import db
from app.models import (
    SupportTicket, TicketKommentar, SupportTeam, Modul,
    TicketTyp, TicketStatus, TicketPrioritaet
)
from app.services import get_support_service

support_bp = Blueprint('support', __name__, url_prefix='/support')


@support_bp.route('/')
@login_required
def meine_tickets():
    """List all tickets created by the current user."""
    service = get_support_service()
    tickets = service.get_tickets_for_user(current_user)

    # Group by status
    offene = [t for t in tickets if t.ist_offen]
    geschlossene = [t for t in tickets if not t.ist_offen]

    return render_template(
        'support/meine_tickets.html',
        tickets=tickets,
        offene=offene,
        geschlossene=geschlossene,
        TicketTyp=TicketTyp,
        TicketStatus=TicketStatus
    )


@support_bp.route('/neu', methods=['GET', 'POST'])
@login_required
def ticket_erstellen():
    """Create a new support ticket."""
    if request.method == 'POST':
        titel = request.form.get('titel', '').strip()
        beschreibung = request.form.get('beschreibung', '').strip()
        typ = request.form.get('typ', TicketTyp.FRAGE.value)
        modul_code = request.form.get('modul_code', '')
        hilfetext_schluessel = request.form.get('hilfetext_schluessel', '')
        seiten_url = request.form.get('seiten_url', '')

        # Validation
        errors = []
        if not titel:
            errors.append('Bitte geben Sie einen Betreff ein.')
        if len(titel) > 200:
            errors.append('Der Betreff darf maximal 200 Zeichen lang sein.')
        if not beschreibung:
            errors.append('Bitte geben Sie eine Beschreibung ein.')
        if len(beschreibung) > 10000:
            errors.append('Die Beschreibung darf maximal 10.000 Zeichen lang sein.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template(
                'support/ticket_form.html',
                titel=titel,
                beschreibung=beschreibung,
                typ=typ,
                modul_code=modul_code,
                hilfetext_schluessel=hilfetext_schluessel,
                seiten_url=seiten_url,
                TicketTyp=TicketTyp
            )

        # Create ticket
        service = get_support_service()
        ticket = service.create_ticket(
            titel=titel,
            beschreibung=beschreibung,
            typ=typ,
            modul_code=modul_code or None,
            hilfetext_schluessel=hilfetext_schluessel or None,
            seiten_url=seiten_url or None
        )

        flash(f'Ihre Anfrage wurde erfolgreich erstellt (Ticket-Nr: {ticket.nummer}).', 'success')
        return redirect(url_for('support.ticket_detail', nummer=ticket.nummer))

    # GET: Show form
    # Pre-fill from query parameters (from help icon)
    modul_code = request.args.get('modul', '')
    hilfetext_schluessel = request.args.get('hilfe', '')
    seiten_url = request.args.get('url', '')

    return render_template(
        'support/ticket_form.html',
        titel='',
        beschreibung='',
        typ=TicketTyp.FRAGE.value,
        modul_code=modul_code,
        hilfetext_schluessel=hilfetext_schluessel,
        seiten_url=seiten_url,
        TicketTyp=TicketTyp
    )


@support_bp.route('/<nummer>')
@login_required
def ticket_detail(nummer):
    """View ticket details and comments."""
    ticket = SupportTicket.query.filter_by(nummer=nummer).first_or_404()

    # Check access
    if not ticket.kann_sehen(current_user):
        abort(403)

    # Get comments (filter internal comments for non-team members)
    if current_user.is_admin or current_user.is_mitarbeiter:
        kommentare = ticket.kommentare.all()
    else:
        kommentare = ticket.oeffentliche_kommentare

    return render_template(
        'support/ticket_detail.html',
        ticket=ticket,
        kommentare=kommentare,
        TicketStatus=TicketStatus
    )


@support_bp.route('/<nummer>/kommentar', methods=['POST'])
@login_required
def kommentar_hinzufuegen(nummer):
    """Add a comment to a ticket."""
    ticket = SupportTicket.query.filter_by(nummer=nummer).first_or_404()

    # Check access
    if not ticket.kann_sehen(current_user):
        abort(403)

    # Check if ticket is closed
    if ticket.status == TicketStatus.GESCHLOSSEN.value:
        flash('Dieses Ticket ist geschlossen und kann nicht mehr kommentiert werden.', 'warning')
        return redirect(url_for('support.ticket_detail', nummer=nummer))

    inhalt = request.form.get('inhalt', '').strip()
    if not inhalt:
        flash('Bitte geben Sie einen Kommentar ein.', 'danger')
        return redirect(url_for('support.ticket_detail', nummer=nummer))

    if len(inhalt) > 10000:
        flash('Der Kommentar darf maximal 10.000 Zeichen lang sein.', 'danger')
        return redirect(url_for('support.ticket_detail', nummer=nummer))

    # Add comment (users can't create internal comments)
    service = get_support_service()
    service.add_kommentar(
        ticket=ticket,
        inhalt=inhalt,
        ist_intern=False
    )

    # If ticket was waiting for customer, set back to in_bearbeitung
    if ticket.status == TicketStatus.WARTE_AUF_KUNDE.value:
        service.change_status(
            ticket=ticket,
            neuer_status=TicketStatus.IN_BEARBEITUNG.value,
            kommentar_text=None
        )

    flash('Ihr Kommentar wurde hinzugefügt.', 'success')
    return redirect(url_for('support.ticket_detail', nummer=nummer))


@support_bp.route('/api/quick-create', methods=['POST'])
@login_required
def quick_create():
    """AJAX endpoint for quick ticket creation from help modal.

    Expected JSON body:
    {
        "titel": "...",
        "beschreibung": "...",
        "typ": "frage",
        "modul_code": "dialog",
        "hilfetext_schluessel": "dialog.detail.fragen",
        "seiten_url": "http://..."
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Keine Daten erhalten'}), 400

    titel = data.get('titel', '').strip()
    beschreibung = data.get('beschreibung', '').strip()
    typ = data.get('typ', TicketTyp.FRAGE.value)
    modul_code = data.get('modul_code', '')
    hilfetext_schluessel = data.get('hilfetext_schluessel', '')
    seiten_url = data.get('seiten_url', '')

    # Validation
    if not titel:
        return jsonify({'success': False, 'error': 'Bitte geben Sie einen Betreff ein'}), 400
    if len(titel) > 200:
        return jsonify({'success': False, 'error': 'Der Betreff darf maximal 200 Zeichen lang sein'}), 400
    if not beschreibung:
        return jsonify({'success': False, 'error': 'Bitte geben Sie eine Beschreibung ein'}), 400
    if len(beschreibung) > 10000:
        return jsonify({'success': False, 'error': 'Die Beschreibung darf maximal 10.000 Zeichen lang sein'}), 400

    try:
        service = get_support_service()
        ticket = service.create_ticket(
            titel=titel,
            beschreibung=beschreibung,
            typ=typ,
            modul_code=modul_code or None,
            hilfetext_schluessel=hilfetext_schluessel or None,
            seiten_url=seiten_url or None
        )

        return jsonify({
            'success': True,
            'ticket_nummer': ticket.nummer,
            'redirect_url': url_for('support.ticket_detail', nummer=ticket.nummer)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
