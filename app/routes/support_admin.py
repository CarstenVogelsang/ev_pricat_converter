"""Admin routes for support ticket management.

Blueprint: support_admin_bp
Prefix: /admin/support/

This module provides routes for administrators and support staff to manage tickets and teams.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import login_required, current_user

from app import db
from app.models import (
    SupportTicket, TicketKommentar, SupportTeam, SupportTeamMitglied,
    User, Modul, Rolle, TicketTyp, TicketStatus, TicketPrioritaet
)
from app.services import get_support_service
from app.routes.admin import admin_required, mitarbeiter_required

support_admin_bp = Blueprint('support_admin', __name__, url_prefix='/admin/support')


@support_admin_bp.route('/')
@login_required
@mitarbeiter_required
def dashboard():
    """Support dashboard with all tickets and statistics."""
    service = get_support_service()

    # Get filter parameters
    status_filter = request.args.get('status', '')
    typ_filter = request.args.get('typ', '')
    prioritaet_filter = request.args.get('prioritaet', '')
    bearbeiter_filter = request.args.get('bearbeiter', '')
    nur_offene = request.args.get('nur_offene', '1') == '1'

    # Get tickets with filters
    tickets = service.get_all_tickets(
        status=status_filter or None,
        typ=typ_filter or None,
        prioritaet=prioritaet_filter or None,
        bearbeiter_id=int(bearbeiter_filter) if bearbeiter_filter else None,
        nur_offene=nur_offene if not status_filter else False
    )

    # Get statistics
    stats = service.get_ticket_stats()

    # Get team members for filter dropdown (admin + mitarbeiter)
    team_members = User.query.join(Rolle).filter(
        Rolle.name.in_(['admin', 'mitarbeiter'])
    ).all()

    return render_template(
        'support/admin/dashboard.html',
        tickets=tickets,
        stats=stats,
        team_members=team_members,
        status_filter=status_filter,
        typ_filter=typ_filter,
        prioritaet_filter=prioritaet_filter,
        bearbeiter_filter=bearbeiter_filter,
        nur_offene=nur_offene,
        TicketTyp=TicketTyp,
        TicketStatus=TicketStatus,
        TicketPrioritaet=TicketPrioritaet,
        admin_tab='einstellungen'
    )


@support_admin_bp.route('/ticket/<nummer>', methods=['GET', 'POST'])
@login_required
@mitarbeiter_required
def ticket_detail(nummer):
    """View and manage a support ticket."""
    ticket = SupportTicket.query.filter_by(nummer=nummer).first_or_404()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'kommentar':
            # Add comment
            inhalt = request.form.get('inhalt', '').strip()
            ist_intern = request.form.get('ist_intern') == '1'

            if inhalt:
                service = get_support_service()
                service.add_kommentar(
                    ticket=ticket,
                    inhalt=inhalt,
                    ist_intern=ist_intern
                )
                flash('Kommentar hinzugefügt.', 'success')

        elif action == 'status':
            # Change status
            neuer_status = request.form.get('neuer_status')
            kommentar_text = request.form.get('status_kommentar', '').strip() or None

            if neuer_status:
                service = get_support_service()
                service.change_status(
                    ticket=ticket,
                    neuer_status=neuer_status,
                    kommentar_text=kommentar_text
                )
                flash(f'Status geändert zu: {TicketStatus.get_label(neuer_status)}', 'success')

        elif action == 'assign':
            # Assign to user
            bearbeiter_id = request.form.get('bearbeiter_id')
            if bearbeiter_id:
                bearbeiter = User.query.get(int(bearbeiter_id))
                if bearbeiter:
                    service = get_support_service()
                    service.assign_ticket(ticket, bearbeiter)
                    flash(f'Ticket zugewiesen an {bearbeiter.vorname} {bearbeiter.nachname}.', 'success')

        elif action == 'prioritaet':
            # Change priority
            neue_prioritaet = request.form.get('neue_prioritaet')
            if neue_prioritaet:
                ticket.prioritaet = neue_prioritaet
                db.session.commit()
                flash(f'Priorität geändert zu: {TicketPrioritaet.get_label(neue_prioritaet)}', 'success')

        return redirect(url_for('support_admin.ticket_detail', nummer=nummer))

    # GET: Show ticket details
    kommentare = ticket.kommentare.all()

    # Get team members for assignment dropdown
    team_members = User.query.join(Rolle).filter(
        Rolle.name.in_(['admin', 'mitarbeiter'])
    ).all()

    return render_template(
        'support/admin/ticket_detail.html',
        ticket=ticket,
        kommentare=kommentare,
        team_members=team_members,
        TicketTyp=TicketTyp,
        TicketStatus=TicketStatus,
        TicketPrioritaet=TicketPrioritaet,
        admin_tab='einstellungen'
    )


@support_admin_bp.route('/ticket/<nummer>/status', methods=['POST'])
@login_required
@mitarbeiter_required
def change_status(nummer):
    """AJAX endpoint to change ticket status."""
    ticket = SupportTicket.query.filter_by(nummer=nummer).first_or_404()

    neuer_status = request.form.get('status')
    if not neuer_status:
        return jsonify({'success': False, 'error': 'Kein Status angegeben'}), 400

    service = get_support_service()
    service.change_status(ticket, neuer_status)

    return jsonify({
        'success': True,
        'status': neuer_status,
        'status_label': TicketStatus.get_label(neuer_status),
        'status_color': TicketStatus.get_color(neuer_status)
    })


@support_admin_bp.route('/ticket/<nummer>/assign', methods=['POST'])
@login_required
@mitarbeiter_required
def assign_ticket(nummer):
    """AJAX endpoint to assign ticket to user."""
    ticket = SupportTicket.query.filter_by(nummer=nummer).first_or_404()

    bearbeiter_id = request.form.get('bearbeiter_id')
    if not bearbeiter_id:
        return jsonify({'success': False, 'error': 'Kein Bearbeiter angegeben'}), 400

    bearbeiter = User.query.get(int(bearbeiter_id))
    if not bearbeiter:
        return jsonify({'success': False, 'error': 'Bearbeiter nicht gefunden'}), 404

    service = get_support_service()
    service.assign_ticket(ticket, bearbeiter)

    return jsonify({
        'success': True,
        'bearbeiter_name': f'{bearbeiter.vorname} {bearbeiter.nachname}'
    })


# ============ Team Management (Admin Only) ============


@support_admin_bp.route('/teams')
@login_required
@admin_required
def teams():
    """List all support teams."""
    all_teams = SupportTeam.query.order_by(SupportTeam.name).all()

    return render_template(
        'support/admin/teams.html',
        teams=all_teams,
        admin_tab='einstellungen'
    )


@support_admin_bp.route('/teams/neu', methods=['GET', 'POST'])
@login_required
@admin_required
def team_erstellen():
    """Create a new support team."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        beschreibung = request.form.get('beschreibung', '').strip()
        email = request.form.get('email', '').strip() or None

        # Validation
        if not name:
            flash('Bitte geben Sie einen Team-Namen ein.', 'danger')
            return render_template(
                'support/admin/team_form.html',
                team=None,
                mitarbeiter_liste=get_mitarbeiter_liste(),
                admin_tab='einstellungen'
            )

        # Check unique name
        existing = SupportTeam.query.filter_by(name=name).first()
        if existing:
            flash('Ein Team mit diesem Namen existiert bereits.', 'danger')
            return render_template(
                'support/admin/team_form.html',
                team=None,
                mitarbeiter_liste=get_mitarbeiter_liste(),
                admin_tab='einstellungen'
            )

        team = SupportTeam(
            name=name,
            beschreibung=beschreibung,
            email=email,
            aktiv=True
        )
        db.session.add(team)
        db.session.commit()

        flash(f'Team "{name}" wurde erstellt.', 'success')
        return redirect(url_for('support_admin.team_bearbeiten', team_id=team.id))

    return render_template(
        'support/admin/team_form.html',
        team=None,
        mitarbeiter_liste=get_mitarbeiter_liste(),
        admin_tab='einstellungen'
    )


@support_admin_bp.route('/teams/<int:team_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def team_bearbeiten(team_id):
    """Edit a support team."""
    team = SupportTeam.query.get_or_404(team_id)

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update':
            # Update team info
            team.name = request.form.get('name', '').strip()
            team.beschreibung = request.form.get('beschreibung', '').strip()
            team.email = request.form.get('email', '').strip() or None
            team.aktiv = request.form.get('aktiv') == '1'

            db.session.commit()
            flash('Team wurde aktualisiert.', 'success')

        elif action == 'add_member':
            # Add team member
            user_id = request.form.get('user_id')
            if user_id:
                user = User.query.get(int(user_id))
                if user:
                    # Check if already member
                    existing = SupportTeamMitglied.query.filter_by(
                        team_id=team.id, user_id=user.id
                    ).first()
                    if existing:
                        flash(f'{user.vorname} {user.nachname} ist bereits Mitglied.', 'warning')
                    else:
                        mitglied = SupportTeamMitglied(
                            team_id=team.id,
                            user_id=user.id,
                            ist_teamleiter=False,
                            benachrichtigung_aktiv=True
                        )
                        db.session.add(mitglied)
                        db.session.commit()
                        flash(f'{user.vorname} {user.nachname} wurde hinzugefügt.', 'success')

        elif action == 'remove_member':
            # Remove team member
            mitglied_id = request.form.get('mitglied_id')
            if mitglied_id:
                mitglied = SupportTeamMitglied.query.get(int(mitglied_id))
                if mitglied and mitglied.team_id == team.id:
                    db.session.delete(mitglied)
                    db.session.commit()
                    flash('Mitglied wurde entfernt.', 'success')

        elif action == 'toggle_leader':
            # Toggle team leader status
            mitglied_id = request.form.get('mitglied_id')
            if mitglied_id:
                mitglied = SupportTeamMitglied.query.get(int(mitglied_id))
                if mitglied and mitglied.team_id == team.id:
                    mitglied.ist_teamleiter = not mitglied.ist_teamleiter
                    db.session.commit()

        elif action == 'toggle_notification':
            # Toggle notification status
            mitglied_id = request.form.get('mitglied_id')
            if mitglied_id:
                mitglied = SupportTeamMitglied.query.get(int(mitglied_id))
                if mitglied and mitglied.team_id == team.id:
                    mitglied.benachrichtigung_aktiv = not mitglied.benachrichtigung_aktiv
                    db.session.commit()

        return redirect(url_for('support_admin.team_bearbeiten', team_id=team.id))

    # Get list of users not in this team for "add member" dropdown
    team_member_ids = [m.user_id for m in team.mitglieder]
    query = User.query.join(Rolle).filter(
        Rolle.name.in_(['admin', 'mitarbeiter'])
    )
    if team_member_ids:
        query = query.filter(~User.id.in_(team_member_ids))
    available_users = query.all()

    return render_template(
        'support/admin/team_form.html',
        team=team,
        mitarbeiter_liste=available_users,
        admin_tab='einstellungen'
    )


@support_admin_bp.route('/teams/<int:team_id>/delete', methods=['POST'])
@login_required
@admin_required
def team_loeschen(team_id):
    """Delete a support team."""
    team = SupportTeam.query.get_or_404(team_id)

    # Check if team has tickets
    ticket_count = SupportTicket.query.filter_by(team_id=team.id).count()
    if ticket_count > 0:
        flash(f'Das Team kann nicht gelöscht werden, da {ticket_count} Tickets zugeordnet sind.', 'danger')
        return redirect(url_for('support_admin.team_bearbeiten', team_id=team.id))

    name = team.name
    db.session.delete(team)
    db.session.commit()

    flash(f'Team "{name}" wurde gelöscht.', 'success')
    return redirect(url_for('support_admin.teams'))


def get_mitarbeiter_liste():
    """Get list of users who can be team members (mitarbeiter + admin)."""
    return User.query.join(Rolle).filter(
        Rolle.name.in_(['admin', 'mitarbeiter'])
    ).order_by(User.nachname, User.vorname).all()
