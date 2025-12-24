"""Customer dialog routes for questionnaire participation.

Blueprint: dialog_bp
Prefix: /dialog/

Routes:
- GET / - List my questionnaires (requires login)
- GET /<id> - Fill questionnaire (requires login)
- GET /t/<token> - Magic-link access (no login)
- POST /t/<token>/antwort - Save answer (AJAX)
- POST /t/<token>/abschliessen - Complete questionnaire
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, abort
from flask_login import login_required, current_user

from app.models import (
    Fragebogen, FragebogenTeilnahme, FragebogenAntwort,
    FragebogenStatus, TeilnahmeStatus
)
from app.services import get_fragebogen_service
from app import db, csrf


dialog_bp = Blueprint('dialog', __name__, url_prefix='/dialog')


@dialog_bp.route('/')
@login_required
def index():
    """List questionnaires.

    - Admin/Mitarbeiter: See ALL questionnaires with participation stats
    - Kunde: See only assigned questionnaires
    """
    # Admin and Mitarbeiter see all questionnaires
    if current_user.is_admin or current_user.is_mitarbeiter:
        frageboegen = Fragebogen.query.order_by(Fragebogen.erstellt_am.desc()).all()

        # Group by status
        entwuerfe = [f for f in frageboegen if f.is_entwurf]
        aktive = [f for f in frageboegen if f.is_aktiv]
        geschlossene = [f for f in frageboegen if f.is_geschlossen]

        return render_template('dialog/index_internal.html',
                               entwuerfe=entwuerfe,
                               aktive=aktive,
                               geschlossene=geschlossene)

    # Kunde view: only own participations
    if not current_user.is_kunde:
        flash('Diese Seite ist nur für Kunden verfügbar.', 'warning')
        return redirect(url_for('main.landing'))

    kunde = current_user.kunde
    if not kunde:
        flash('Ihr Benutzerkonto ist keinem Kunden zugeordnet.', 'warning')
        return redirect(url_for('main.landing'))

    # Get all participations for this kunde
    teilnahmen = FragebogenTeilnahme.query.filter_by(kunde_id=kunde.id).all()

    # Group by status
    aktive = [t for t in teilnahmen if t.fragebogen.is_aktiv and not t.is_abgeschlossen]
    abgeschlossene = [t for t in teilnahmen if t.is_abgeschlossen]
    geschlossene = [t for t in teilnahmen if t.fragebogen.is_geschlossen and not t.is_abgeschlossen]

    return render_template('dialog/index.html',
                           aktive=aktive,
                           abgeschlossene=abgeschlossene,
                           geschlossene=geschlossene)


@dialog_bp.route('/<int:id>')
@login_required
def fragebogen(id):
    """Fill out a questionnaire (with login).

    - Admin/Mitarbeiter: Redirect to admin detail view
    - Kunde: Only accessible if user's Kunde is a participant
    """
    # Admin/Mitarbeiter redirect to admin view
    if current_user.is_admin or current_user.is_mitarbeiter:
        return redirect(url_for('dialog_admin.detail', id=id))

    if not current_user.is_kunde:
        abort(403)

    kunde = current_user.kunde
    if not kunde:
        abort(403)

    # Find participation
    teilnahme = FragebogenTeilnahme.query.filter_by(
        fragebogen_id=id,
        kunde_id=kunde.id
    ).first_or_404()

    fragebogen = teilnahme.fragebogen

    # Check status
    if fragebogen.is_geschlossen:
        return render_template('dialog/geschlossen.html', fragebogen=fragebogen)

    if teilnahme.is_abgeschlossen:
        return render_template('dialog/abgeschlossen.html',
                               fragebogen=fragebogen,
                               teilnahme=teilnahme)

    if not fragebogen.is_aktiv:
        flash('Dieser Fragebogen ist noch nicht freigegeben.', 'info')
        return redirect(url_for('dialog.index'))

    # Start if not yet started
    if teilnahme.is_eingeladen:
        teilnahme.starten()
        db.session.commit()

    # Get existing answers
    antworten = {a.frage_id: a.antwort_json for a in teilnahme.antworten}

    return render_template('dialog/fragebogen.html',
                           fragebogen=fragebogen,
                           teilnahme=teilnahme,
                           antworten=antworten)


@dialog_bp.route('/t/<token>')
def magic_link(token):
    """Access questionnaire via magic-link (no login required).

    Minimal UI, direct to questionnaire.
    Uses wizard template for V2 frageboegen, flat template for V1.
    """
    from datetime import date

    service = get_fragebogen_service()
    teilnahme = service.get_teilnahme_by_token(token)

    if not teilnahme:
        return render_template('dialog/invalid.html',
                               error='Ungültiger oder abgelaufener Link')

    fragebogen = teilnahme.fragebogen

    # Check status
    if fragebogen.is_geschlossen:
        return render_template('dialog/geschlossen.html',
                               fragebogen=fragebogen,
                               minimal=True)

    if teilnahme.is_abgeschlossen:
        return render_template('dialog/abgeschlossen.html',
                               fragebogen=fragebogen,
                               teilnahme=teilnahme,
                               minimal=True)

    if not fragebogen.is_aktiv:
        return render_template('dialog/invalid.html',
                               error='Dieser Fragebogen ist noch nicht freigegeben.')

    # Start if not yet started and create prefill snapshot for V2
    if teilnahme.is_eingeladen:
        teilnahme.starten()
        if fragebogen.is_v2:
            service.create_prefill_snapshot(teilnahme)
        db.session.commit()

    # Get existing answers
    antworten = {a.frage_id: a.antwort_json for a in teilnahme.antworten}

    # For V2: Merge prefilled values as initial answers
    if fragebogen.is_v2:
        initial = service.get_initial_antworten(fragebogen, teilnahme.kunde)
        # Only use prefill for fields that don't have an answer yet
        for frage_id, prefill_value in initial.items():
            if frage_id not in antworten:
                antworten[frage_id] = prefill_value

        return render_template('dialog/fragebogen_wizard.html',
                               fragebogen=fragebogen,
                               teilnahme=teilnahme,
                               token=token,
                               antworten=antworten,
                               today=date.today().isoformat())

    # V1: Use flat template
    return render_template('dialog/fragebogen_magic.html',
                           fragebogen=fragebogen,
                           teilnahme=teilnahme,
                           token=token,
                           antworten=antworten)


@dialog_bp.route('/t/<token>/antwort', methods=['POST'])
@csrf.exempt  # Magic-link token is already authentication
def save_antwort(token):
    """Save an answer via AJAX (magic-link).

    Expected JSON body:
    {
        "frage_id": "q1",
        "antwort": {"value": "Option A"} or {"values": [...]}
    }

    Returns JSON with success status.
    """
    service = get_fragebogen_service()
    teilnahme = service.get_teilnahme_by_token(token)

    if not teilnahme:
        return jsonify({'success': False, 'error': 'Ungültiger Token'}), 404

    if not teilnahme.fragebogen.is_aktiv:
        return jsonify({'success': False, 'error': 'Fragebogen nicht aktiv'}), 400

    if teilnahme.is_abgeschlossen:
        return jsonify({'success': False, 'error': 'Bereits abgeschlossen'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Keine Daten'}), 400

    frage_id = data.get('frage_id')
    antwort = data.get('antwort')

    if not frage_id or antwort is None:
        return jsonify({'success': False, 'error': 'frage_id und antwort erforderlich'}), 400

    try:
        service.save_antwort(teilnahme, frage_id, antwort)
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@dialog_bp.route('/t/<token>/abschliessen', methods=['POST'])
@csrf.exempt  # Magic-link token is already authentication
def complete(token):
    """Complete the questionnaire participation (magic-link).

    Validates that all required questions are answered.
    """
    service = get_fragebogen_service()
    teilnahme = service.get_teilnahme_by_token(token)

    if not teilnahme:
        return jsonify({'success': False, 'error': 'Ungültiger Token'}), 404

    if not teilnahme.fragebogen.is_aktiv:
        return jsonify({'success': False, 'error': 'Fragebogen nicht aktiv'}), 400

    if teilnahme.is_abgeschlossen:
        return jsonify({'success': False, 'error': 'Bereits abgeschlossen'}), 400

    try:
        service.complete_teilnahme(teilnahme)
        return jsonify({
            'success': True,
            'redirect': url_for('dialog.danke', token=token)
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@dialog_bp.route('/t/<token>/danke')
def danke(token):
    """Thank you page after completion."""
    service = get_fragebogen_service()
    teilnahme = service.get_teilnahme_by_token(token)

    if not teilnahme:
        return render_template('dialog/invalid.html',
                               error='Ungültiger Link')

    return render_template('dialog/danke.html',
                           fragebogen=teilnahme.fragebogen,
                           kunde=teilnahme.kunde,
                           minimal=True)
