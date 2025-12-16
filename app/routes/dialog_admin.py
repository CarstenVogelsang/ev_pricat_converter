"""Admin routes for questionnaire management.

Blueprint: dialog_admin_bp
Prefix: /admin/dialog/

Only accessible for admin and mitarbeiter roles.

Routes:
- GET / - List all questionnaires
- GET/POST /neu - Create new questionnaire
- GET /<id> - Questionnaire details
- POST /<id>/edit - Update questionnaire
- POST /<id>/status - Change status
- GET /<id>/teilnehmer - Manage participants
- POST /<id>/teilnehmer/add - Add participant
- POST /<id>/teilnehmer/<tid>/remove - Remove participant
- POST /<id>/einladungen - Send invitations
- GET /<id>/auswertung - View statistics
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, abort
from flask_login import login_required, current_user

from app.models import (
    Fragebogen, FragebogenTeilnahme, Kunde,
    FragebogenStatus
)
from app.services import get_fragebogen_service
from app import db


dialog_admin_bp = Blueprint('dialog_admin', __name__, url_prefix='/admin/dialog')


def require_internal():
    """Check if current user is internal (admin or mitarbeiter)."""
    if not current_user.is_authenticated:
        abort(401)
    if not current_user.is_internal:
        abort(403)


@dialog_admin_bp.before_request
def check_access():
    """Ensure user has access to admin area."""
    require_internal()


@dialog_admin_bp.route('/')
def index():
    """List all questionnaires."""
    frageboegen = Fragebogen.query.order_by(Fragebogen.erstellt_am.desc()).all()

    # Group by status
    entwuerfe = [f for f in frageboegen if f.is_entwurf]
    aktive = [f for f in frageboegen if f.is_aktiv]
    geschlossene = [f for f in frageboegen if f.is_geschlossen]

    return render_template('dialog_admin/index.html',
                           entwuerfe=entwuerfe,
                           aktive=aktive,
                           geschlossene=geschlossene)


@dialog_admin_bp.route('/neu', methods=['GET', 'POST'])
def neu():
    """Create a new questionnaire."""
    if request.method == 'POST':
        titel = request.form.get('titel', '').strip()
        beschreibung = request.form.get('beschreibung', '').strip()
        definition_json = request.form.get('definition_json', '{}')

        if not titel:
            flash('Titel ist erforderlich.', 'danger')
            return render_template('dialog_admin/form.html',
                                   fragebogen=None,
                                   titel=titel,
                                   beschreibung=beschreibung,
                                   definition_json=definition_json)

        # Parse and validate JSON
        import json
        try:
            definition = json.loads(definition_json)
        except json.JSONDecodeError as e:
            flash(f'Ungültiges JSON: {e}', 'danger')
            return render_template('dialog_admin/form.html',
                                   fragebogen=None,
                                   titel=titel,
                                   beschreibung=beschreibung,
                                   definition_json=definition_json)

        service = get_fragebogen_service()
        validation = service.validate_definition(definition)

        if not validation.valid:
            for error in validation.errors:
                flash(error, 'danger')
            return render_template('dialog_admin/form.html',
                                   fragebogen=None,
                                   titel=titel,
                                   beschreibung=beschreibung,
                                   definition_json=definition_json)

        # Create fragebogen
        fragebogen = service.create_fragebogen(
            titel=titel,
            beschreibung=beschreibung,
            definition=definition,
            erstellt_von_id=current_user.id
        )

        flash(f'Fragebogen "{titel}" wurde erstellt.', 'success')
        return redirect(url_for('dialog_admin.detail', id=fragebogen.id))

    # GET - show empty form
    default_definition = '''{
  "fragen": [
    {
      "id": "q1",
      "typ": "single_choice",
      "frage": "Beispielfrage?",
      "optionen": ["Option A", "Option B", "Option C"],
      "pflicht": true
    }
  ]
}'''
    return render_template('dialog_admin/form.html',
                           fragebogen=None,
                           titel='',
                           beschreibung='',
                           definition_json=default_definition)


@dialog_admin_bp.route('/<int:id>')
def detail(id):
    """View questionnaire details."""
    fragebogen = Fragebogen.query.get_or_404(id)

    return render_template('dialog_admin/detail.html',
                           fragebogen=fragebogen)


@dialog_admin_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    """Edit questionnaire (only in ENTWURF status)."""
    fragebogen = Fragebogen.query.get_or_404(id)

    if not fragebogen.is_entwurf:
        flash('Fragebogen kann nur im Entwurf-Status bearbeitet werden.', 'warning')
        return redirect(url_for('dialog_admin.detail', id=id))

    if request.method == 'POST':
        import json

        titel = request.form.get('titel', '').strip()
        beschreibung = request.form.get('beschreibung', '').strip()
        definition_json = request.form.get('definition_json', '{}')

        if not titel:
            flash('Titel ist erforderlich.', 'danger')
            return render_template('dialog_admin/form.html',
                                   fragebogen=fragebogen,
                                   titel=titel,
                                   beschreibung=beschreibung,
                                   definition_json=definition_json)

        try:
            definition = json.loads(definition_json)
        except json.JSONDecodeError as e:
            flash(f'Ungültiges JSON: {e}', 'danger')
            return render_template('dialog_admin/form.html',
                                   fragebogen=fragebogen,
                                   titel=titel,
                                   beschreibung=beschreibung,
                                   definition_json=definition_json)

        service = get_fragebogen_service()
        validation = service.validate_definition(definition)

        if not validation.valid:
            for error in validation.errors:
                flash(error, 'danger')
            return render_template('dialog_admin/form.html',
                                   fragebogen=fragebogen,
                                   titel=titel,
                                   beschreibung=beschreibung,
                                   definition_json=definition_json)

        service.update_fragebogen(fragebogen, titel, beschreibung, definition)
        flash('Fragebogen wurde aktualisiert.', 'success')
        return redirect(url_for('dialog_admin.detail', id=id))

    # GET - show form with current data
    import json
    definition_json = json.dumps(fragebogen.definition_json, indent=2, ensure_ascii=False)

    return render_template('dialog_admin/form.html',
                           fragebogen=fragebogen,
                           titel=fragebogen.titel,
                           beschreibung=fragebogen.beschreibung or '',
                           definition_json=definition_json)


@dialog_admin_bp.route('/<int:id>/status', methods=['POST'])
def change_status(id):
    """Change questionnaire status.

    Expected form data:
    - action: 'aktivieren' or 'schliessen'
    """
    fragebogen = Fragebogen.query.get_or_404(id)
    action = request.form.get('action')

    if action == 'aktivieren':
        if not fragebogen.is_entwurf:
            flash('Nur Entwürfe können aktiviert werden.', 'warning')
        elif fragebogen.anzahl_fragen == 0:
            flash('Fragebogen hat keine Fragen.', 'danger')
        else:
            fragebogen.aktivieren()
            db.session.commit()
            flash('Fragebogen wurde aktiviert.', 'success')

    elif action == 'schliessen':
        if fragebogen.is_geschlossen:
            flash('Fragebogen ist bereits geschlossen.', 'warning')
        else:
            fragebogen.schliessen()
            db.session.commit()
            flash('Fragebogen wurde geschlossen.', 'success')

    else:
        flash('Ungültige Aktion.', 'danger')

    return redirect(url_for('dialog_admin.detail', id=id))


@dialog_admin_bp.route('/<int:id>/teilnehmer')
def teilnehmer(id):
    """Manage questionnaire participants."""
    fragebogen = Fragebogen.query.get_or_404(id)

    # Get available kunden (those with user and not yet added)
    existing_kunde_ids = [t.kunde_id for t in fragebogen.teilnahmen]
    verfuegbare_kunden = Kunde.query.filter(
        Kunde.user_id.isnot(None),
        ~Kunde.id.in_(existing_kunde_ids) if existing_kunde_ids else True
    ).order_by(Kunde.firmierung).all()

    return render_template('dialog_admin/teilnehmer.html',
                           fragebogen=fragebogen,
                           verfuegbare_kunden=verfuegbare_kunden)


@dialog_admin_bp.route('/<int:id>/teilnehmer/add', methods=['POST'])
def add_teilnehmer(id):
    """Add a participant to the questionnaire."""
    fragebogen = Fragebogen.query.get_or_404(id)
    kunde_id = request.form.get('kunde_id', type=int)

    if not kunde_id:
        flash('Bitte einen Kunden auswählen.', 'warning')
        return redirect(url_for('dialog_admin.teilnehmer', id=id))

    kunde = Kunde.query.get_or_404(kunde_id)
    service = get_fragebogen_service()

    try:
        service.add_teilnehmer(fragebogen, kunde)
        flash(f'{kunde.firmierung} wurde hinzugefügt.', 'success')
    except ValueError as e:
        flash(str(e), 'danger')

    return redirect(url_for('dialog_admin.teilnehmer', id=id))


@dialog_admin_bp.route('/<int:id>/teilnehmer/<int:tid>/remove', methods=['POST'])
def remove_teilnehmer(id, tid):
    """Remove a participant from the questionnaire."""
    teilnahme = FragebogenTeilnahme.query.get_or_404(tid)

    if teilnahme.fragebogen_id != id:
        abort(400)

    service = get_fragebogen_service()

    try:
        kunde_name = teilnahme.kunde.firmierung
        service.remove_teilnehmer(teilnahme)
        flash(f'{kunde_name} wurde entfernt.', 'success')
    except ValueError as e:
        flash(str(e), 'danger')

    return redirect(url_for('dialog_admin.teilnehmer', id=id))


@dialog_admin_bp.route('/<int:id>/einladungen', methods=['POST'])
def send_einladungen(id):
    """Send invitation emails to participants."""
    fragebogen = Fragebogen.query.get_or_404(id)

    if not fragebogen.is_aktiv:
        flash('Fragebogen muss aktiv sein um Einladungen zu senden.', 'warning')
        return redirect(url_for('dialog_admin.teilnehmer', id=id))

    # Get specific teilnahme IDs if provided, otherwise send to all
    teilnahme_ids = request.form.getlist('teilnahme_ids', type=int)

    if teilnahme_ids:
        teilnahmen = FragebogenTeilnahme.query.filter(
            FragebogenTeilnahme.id.in_(teilnahme_ids),
            FragebogenTeilnahme.fragebogen_id == id
        ).all()
    else:
        teilnahmen = None  # Service will send to all unsent

    service = get_fragebogen_service()
    result = service.send_einladungen(fragebogen, teilnahmen)

    if result.success:
        flash(f'{result.sent_count} Einladung(en) erfolgreich gesendet.', 'success')
    else:
        flash(f'{result.sent_count} gesendet, {result.failed_count} fehlgeschlagen.', 'warning')
        for error in (result.errors or [])[:5]:
            flash(error, 'danger')

    return redirect(url_for('dialog_admin.teilnehmer', id=id))


@dialog_admin_bp.route('/<int:id>/auswertung')
def auswertung(id):
    """View questionnaire statistics and responses."""
    fragebogen = Fragebogen.query.get_or_404(id)
    service = get_fragebogen_service()

    stats = service.get_auswertung(fragebogen)

    return render_template('dialog_admin/auswertung.html',
                           fragebogen=fragebogen,
                           stats=stats)
