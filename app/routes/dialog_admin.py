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
from sqlalchemy import or_, and_

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
    """List all questionnaires.

    Query params:
    - archived: '1' to show archived, default '0'
    """
    show_archived = request.args.get('archived', '0') == '1'

    # Filter by archive status
    query = Fragebogen.query
    if not show_archived:
        query = query.filter(Fragebogen.archiviert == False)

    frageboegen = query.order_by(Fragebogen.erstellt_am.desc()).all()

    # Group by status
    entwuerfe = [f for f in frageboegen if f.is_entwurf]
    aktive = [f for f in frageboegen if f.is_aktiv]
    geschlossene = [f for f in frageboegen if f.is_geschlossen]

    # Count archived for badge
    archiviert_count = Fragebogen.query.filter(Fragebogen.archiviert == True).count()

    return render_template('dialog_admin/index.html',
                           entwuerfe=entwuerfe,
                           aktive=aktive,
                           geschlossene=geschlossene,
                           show_archived=show_archived,
                           archiviert_count=archiviert_count)


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

    elif action == 'reaktivieren':
        if not fragebogen.is_geschlossen:
            flash('Nur geschlossene Fragebögen können reaktiviert werden.', 'warning')
        else:
            fragebogen.reaktivieren()
            db.session.commit()
            flash('Fragebogen wurde reaktiviert und ist wieder aktiv.', 'success')

    else:
        flash('Ungültige Aktion.', 'danger')

    return redirect(url_for('dialog_admin.detail', id=id))


@dialog_admin_bp.route('/<int:id>/teilnehmer')
def teilnehmer(id):
    """Manage questionnaire participants."""
    fragebogen = Fragebogen.query.get_or_404(id)

    # Get available kunden/leads (those who can receive questionnaires and not yet added)
    # - Kunden with user account (user_id is set)
    # - Leads with email address (typ='lead' and email is set)
    existing_kunde_ids = [t.kunde_id for t in fragebogen.teilnahmen]
    verfuegbare_kunden = Kunde.query.filter(
        or_(
            Kunde.user_id.isnot(None),  # Kunden with user account
            and_(
                Kunde.typ == 'lead',     # Leads...
                Kunde.email.isnot(None), # ...with email
                Kunde.email != ''
            )
        ),
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
        teilnahme = service.add_teilnehmer(fragebogen, kunde)

        # PRD006-T057: Einladungs-E-Mail automatisch versenden
        result = service.send_einladungen(fragebogen, [teilnahme])
        if result.success and result.sent_count > 0:
            flash(f'{kunde.firmierung} wurde hinzugefügt und Einladung versendet.', 'success')
        else:
            flash(f'{kunde.firmierung} wurde hinzugefügt, aber E-Mail konnte nicht versendet werden.', 'warning')
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


@dialog_admin_bp.route('/<int:id>/teilnehmer/<int:tid>/resend', methods=['POST'])
def resend_einladung(id, tid):
    """Resend invitation email to a specific participant."""
    fragebogen = Fragebogen.query.get_or_404(id)
    teilnahme = FragebogenTeilnahme.query.get_or_404(tid)

    if teilnahme.fragebogen_id != id:
        abort(400)

    if not fragebogen.is_aktiv:
        flash('Fragebogen muss aktiv sein um Einladungen zu senden.', 'warning')
        return redirect(url_for('dialog_admin.teilnehmer', id=id))

    if teilnahme.is_abgeschlossen:
        flash('Teilnehmer hat bereits abgeschlossen.', 'warning')
        return redirect(url_for('dialog_admin.teilnehmer', id=id))

    service = get_fragebogen_service()
    result = service.send_einladungen(fragebogen, [teilnahme], is_resend=True)

    if result.success and result.sent_count > 0:
        flash(f'Einladung an {teilnahme.kunde.firmierung} erneut gesendet.', 'success')
    else:
        error_msg = result.errors[0] if result.errors else 'Unbekannter Fehler'
        flash(f'Fehler beim Senden: {error_msg}', 'danger')

    return redirect(url_for('dialog_admin.teilnehmer', id=id))


@dialog_admin_bp.route('/<int:id>/auswertung')
def auswertung(id):
    """View questionnaire statistics and responses.

    Optional query param:
    - teilnehmer: ID of specific participant to view
    """
    fragebogen = Fragebogen.query.get_or_404(id)
    service = get_fragebogen_service()

    # Check for single participant filter
    teilnehmer_id = request.args.get('teilnehmer', type=int)

    if teilnehmer_id:
        # Single participant view
        teilnahme = FragebogenTeilnahme.query.get_or_404(teilnehmer_id)
        if teilnahme.fragebogen_id != id:
            abort(400)

        einzelauswertung = service.get_teilnehmer_auswertung(teilnahme)
        return render_template('dialog_admin/auswertung.html',
                               fragebogen=fragebogen,
                               stats=None,
                               einzelauswertung=einzelauswertung,
                               selected_teilnehmer_id=teilnehmer_id)
    else:
        # Overall statistics view
        stats = service.get_auswertung(fragebogen)
        return render_template('dialog_admin/auswertung.html',
                               fragebogen=fragebogen,
                               stats=stats,
                               einzelauswertung=None,
                               selected_teilnehmer_id=None)


@dialog_admin_bp.route('/<int:id>/duplicate', methods=['POST'])
def duplicate(id):
    """Create a new version of a Fragebogen.

    Only the newest version in a chain can be duplicated.
    Creates: V1 → V2 → V3, etc.
    """
    from app.services.logging_service import log_mittel

    fragebogen = Fragebogen.query.get_or_404(id)
    service = get_fragebogen_service()

    # Get custom title from form (optional)
    new_titel = request.form.get('titel', '').strip() or None

    try:
        new_fragebogen = service.duplicate_fragebogen(
            fragebogen,
            user_id=current_user.id,
            new_titel=new_titel
        )

        log_mittel(
            modul='dialog',
            aktion='fragebogen_dupliziert',
            details=f'Fragebogen "{fragebogen.titel}" V{fragebogen.version_nummer} → '
                    f'"{new_fragebogen.titel}" V{new_fragebogen.version_nummer}',
            entity_type='Fragebogen',
            entity_id=new_fragebogen.id
        )

        flash(f'Neue Version V{new_fragebogen.version_nummer} erstellt.', 'success')
        return redirect(url_for('dialog_admin.detail', id=new_fragebogen.id))

    except ValueError as e:
        # Not the newest version - can't duplicate
        flash(str(e), 'warning')
        return redirect(url_for('dialog_admin.detail', id=id))


@dialog_admin_bp.route('/<int:id>/archivieren', methods=['POST'])
def archivieren(id):
    """Archive a Fragebogen (soft-delete)."""
    from app.services.logging_service import log_mittel

    fragebogen = Fragebogen.query.get_or_404(id)

    if fragebogen.is_archiviert:
        flash('Fragebogen ist bereits archiviert.', 'warning')
        return redirect(url_for('dialog_admin.detail', id=id))

    service = get_fragebogen_service()
    service.archiviere_fragebogen(fragebogen)

    log_mittel(
        modul='dialog',
        aktion='fragebogen_archiviert',
        details=f'Fragebogen "{fragebogen.titel}" V{fragebogen.version_nummer} archiviert',
        entity_type='Fragebogen',
        entity_id=fragebogen.id
    )

    flash(f'Fragebogen "{fragebogen.titel}" wurde archiviert.', 'success')
    return redirect(url_for('dialog_admin.index'))


@dialog_admin_bp.route('/<int:id>/dearchivieren', methods=['POST'])
def dearchivieren(id):
    """Restore an archived Fragebogen."""
    from app.services.logging_service import log_mittel

    fragebogen = Fragebogen.query.get_or_404(id)

    if not fragebogen.is_archiviert:
        flash('Fragebogen ist nicht archiviert.', 'warning')
        return redirect(url_for('dialog_admin.detail', id=id))

    service = get_fragebogen_service()
    service.dearchiviere_fragebogen(fragebogen)

    log_mittel(
        modul='dialog',
        aktion='fragebogen_dearchiviert',
        details=f'Fragebogen "{fragebogen.titel}" V{fragebogen.version_nummer} wiederhergestellt',
        entity_type='Fragebogen',
        entity_id=fragebogen.id
    )

    flash(f'Fragebogen "{fragebogen.titel}" wurde wiederhergestellt.', 'success')
    return redirect(url_for('dialog_admin.detail', id=id))


@dialog_admin_bp.route('/<int:id>/vorschau')
def vorschau(id):
    """Preview a questionnaire in draft mode.

    Shows the questionnaire as it would appear to a participant,
    with a test customer for prefill data. No data is saved.
    The questionnaire remains in draft status.

    PRD006-T059: Fragebogen im Entwurf testen/ansehen
    """
    from datetime import date

    fragebogen = Fragebogen.query.get_or_404(id)

    # Only V2 (wizard) questionnaires are supported for preview
    if not fragebogen.is_v2:
        flash('Vorschau ist nur für Fragebögen mit Seiten (V2) verfügbar.', 'warning')
        return redirect(url_for('dialog_admin.detail', id=id))

    service = get_fragebogen_service()

    # Find a test customer for prefill simulation
    # Use the first Kunde with firmierung set, or fallback to empty data
    test_kunde = Kunde.query.filter(
        Kunde.firmierung.isnot(None),
        Kunde.firmierung != ''
    ).first()

    # Get prefill values for the test kunde (if available)
    antworten = {}
    if test_kunde:
        antworten = service.get_initial_antworten(fragebogen, test_kunde)

    return render_template('dialog/fragebogen_wizard.html',
                           fragebogen=fragebogen,
                           antworten=antworten,
                           test_kunde=test_kunde,
                           today=date.today().isoformat(),
                           preview_mode=True)
