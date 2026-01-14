"""Admin routes for mailing management (PRD-013).

Blueprint: mailing_admin_bp
Prefix: /admin/mailing/

Only accessible for admin and mitarbeiter roles.

Routes:
- GET / - List all mailings
- GET/POST /neu - Create new mailing
- GET /<id> - Mailing details
- GET/POST /<id>/edit - Edit mailing
- POST /<id>/delete - Delete mailing
- GET /<id>/empfaenger - Manage recipients
- POST /<id>/empfaenger/add - Add recipients
- POST /<id>/empfaenger/<eid>/remove - Remove recipient
- GET /<id>/vorschau - Preview email with sample data
- GET /<id>/editor - Visual section editor
- POST /<id>/editor/sektion - Add section (AJAX)
- PATCH /<id>/editor/sektion/<sid> - Update section (AJAX)
- DELETE /<id>/editor/sektion/<sid> - Delete section (AJAX)
- POST /<id>/editor/reorder - Reorder sections (AJAX)
- POST /<id>/test-senden - Send test email (Phase 3)
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort, jsonify
from flask_login import login_required, current_user

from app.models import (
    Mailing, MailingEmpfaenger, MailingStatus, Kunde, Fragebogen, FragebogenStatus
)
from app.services import get_mailing_service
from app import db


mailing_admin_bp = Blueprint('mailing_admin', __name__, url_prefix='/admin/mailing')


def require_internal():
    """Check if current user is internal (admin or mitarbeiter)."""
    if not current_user.is_authenticated:
        abort(401)
    if not current_user.is_internal:
        abort(403)


@mailing_admin_bp.before_request
def check_access():
    """Ensure user has access to admin area."""
    require_internal()


@mailing_admin_bp.route('/')
def index():
    """List all mailings grouped by status."""
    service = get_mailing_service()
    mailings = service.get_all_mailings()

    # Group by status
    entwuerfe = [m for m in mailings if m.is_entwurf]
    versendet = [m for m in mailings if m.is_versendet]

    return render_template('mailing_admin/index.html',
                           entwuerfe=entwuerfe,
                           versendet=versendet)


@mailing_admin_bp.route('/neu', methods=['GET', 'POST'])
def neu():
    """Create a new mailing."""
    service = get_mailing_service()

    if request.method == 'POST':
        titel = request.form.get('titel', '').strip()
        betreff = request.form.get('betreff', '').strip()
        fragebogen_id = request.form.get('fragebogen_id')

        if not titel:
            flash('Bitte einen Titel eingeben.', 'warning')
            return redirect(url_for('mailing_admin.neu'))

        if not betreff:
            flash('Bitte einen Betreff eingeben.', 'warning')
            return redirect(url_for('mailing_admin.neu'))

        # Convert fragebogen_id
        fragebogen_id = int(fragebogen_id) if fragebogen_id else None

        mailing = service.create_mailing(
            titel=titel,
            betreff=betreff,
            erstellt_von_id=current_user.id,
            fragebogen_id=fragebogen_id
        )

        flash(f'Mailing "{titel}" wurde erstellt.', 'success')
        return redirect(url_for('mailing_admin.detail', id=mailing.id))

    # GET: Show form
    # Get active Fragebögen for selection
    frageboegen = Fragebogen.query.filter_by(
        status=FragebogenStatus.AKTIV.value
    ).order_by(Fragebogen.titel).all()

    return render_template('mailing_admin/form.html',
                           mailing=None,
                           frageboegen=frageboegen,
                           mode='neu')


@mailing_admin_bp.route('/<int:id>')
def detail(id):
    """Show mailing details with statistics."""
    mailing = Mailing.query.get_or_404(id)

    return render_template('mailing_admin/detail.html',
                           mailing=mailing)


@mailing_admin_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    """Edit a mailing (only in ENTWURF status)."""
    service = get_mailing_service()
    mailing = Mailing.query.get_or_404(id)

    if not mailing.is_entwurf:
        flash('Nur Mailings im Entwurf-Status können bearbeitet werden.', 'warning')
        return redirect(url_for('mailing_admin.detail', id=id))

    if request.method == 'POST':
        titel = request.form.get('titel', '').strip()
        betreff = request.form.get('betreff', '').strip()
        fragebogen_id = request.form.get('fragebogen_id')

        if not titel:
            flash('Bitte einen Titel eingeben.', 'warning')
            return redirect(url_for('mailing_admin.edit', id=id))

        if not betreff:
            flash('Bitte einen Betreff eingeben.', 'warning')
            return redirect(url_for('mailing_admin.edit', id=id))

        # Convert fragebogen_id (-1 means remove)
        fragebogen_id = int(fragebogen_id) if fragebogen_id else -1

        try:
            service.update_mailing(
                mailing,
                titel=titel,
                betreff=betreff,
                fragebogen_id=fragebogen_id
            )
            flash('Mailing wurde aktualisiert.', 'success')
        except ValueError as e:
            flash(str(e), 'danger')

        return redirect(url_for('mailing_admin.detail', id=id))

    # GET: Show form
    frageboegen = Fragebogen.query.filter_by(
        status=FragebogenStatus.AKTIV.value
    ).order_by(Fragebogen.titel).all()

    return render_template('mailing_admin/form.html',
                           mailing=mailing,
                           frageboegen=frageboegen,
                           mode='edit')


@mailing_admin_bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    """Delete a mailing (only in ENTWURF status with no sent emails)."""
    service = get_mailing_service()
    mailing = Mailing.query.get_or_404(id)

    try:
        service.delete_mailing(mailing)
        flash('Mailing wurde gelöscht.', 'success')
        return redirect(url_for('mailing_admin.index'))
    except ValueError as e:
        flash(str(e), 'danger')
        return redirect(url_for('mailing_admin.detail', id=id))


@mailing_admin_bp.route('/<int:id>/empfaenger')
def empfaenger(id):
    """Manage recipients of a mailing."""
    service = get_mailing_service()
    mailing = Mailing.query.get_or_404(id)

    # Get available Kunden (not yet added, can receive mailings)
    verfuegbare = service.get_verfuegbare_empfaenger(mailing)

    # Get batch info for sending
    batch_info = service.get_batch_info(mailing)

    return render_template('mailing_admin/empfaenger.html',
                           mailing=mailing,
                           verfuegbare=verfuegbare,
                           batch_info=batch_info)


@mailing_admin_bp.route('/<int:id>/empfaenger/add', methods=['POST'])
def empfaenger_add(id):
    """Add recipients to a mailing."""
    service = get_mailing_service()
    mailing = Mailing.query.get_or_404(id)

    # Get selected Kunde IDs
    kunde_ids = request.form.getlist('kunde_ids')
    kunde_ids = [int(kid) for kid in kunde_ids if kid]

    if not kunde_ids:
        flash('Bitte mindestens einen Empfänger auswählen.', 'warning')
        return redirect(url_for('mailing_admin.empfaenger', id=id))

    added = service.add_empfaenger_bulk(mailing, kunde_ids)

    if added > 0:
        flash(f'{added} Empfänger hinzugefügt.', 'success')
    else:
        flash('Keine neuen Empfänger hinzugefügt (bereits vorhanden oder nicht berechtigt).', 'info')

    return redirect(url_for('mailing_admin.empfaenger', id=id))


@mailing_admin_bp.route('/<int:id>/empfaenger/<int:eid>/remove', methods=['POST'])
def empfaenger_remove(id, eid):
    """Remove a recipient from a mailing."""
    service = get_mailing_service()
    mailing = Mailing.query.get_or_404(id)

    empfaenger = MailingEmpfaenger.query.get_or_404(eid)
    if empfaenger.mailing_id != mailing.id:
        abort(404)

    try:
        service.remove_empfaenger(mailing, empfaenger.kunde_id)
        flash('Empfänger entfernt.', 'success')
    except ValueError as e:
        flash(str(e), 'danger')

    return redirect(url_for('mailing_admin.empfaenger', id=id))


# ========== Phase 2: Editor & Preview ==========

@mailing_admin_bp.route('/<int:id>/vorschau')
def vorschau(id):
    """Preview the mailing with sample data."""
    service = get_mailing_service()
    mailing = Mailing.query.get_or_404(id)

    # Render with sample data
    email_html = service.render_mailing_html(mailing, preview_mode=True)
    sample_context = service.get_sample_context()

    return render_template('mailing_admin/vorschau.html',
                           mailing=mailing,
                           email_html=email_html,
                           sample_context=sample_context)


@mailing_admin_bp.route('/<int:id>/editor')
def editor(id):
    """Visual section editor for the mailing."""
    mailing = Mailing.query.get_or_404(id)

    if not mailing.is_entwurf:
        flash('Nur Mailings im Entwurf-Status können bearbeitet werden.', 'warning')
        return redirect(url_for('mailing_admin.detail', id=id))

    # Section type definitions for the UI
    sektion_typen = {
        'header': {
            'name': 'Header',
            'icon': 'ti-layout-navbar',
            'beschreibung': 'Logo und Portal-Name',
            'default_config': {'zeige_logo': True, 'logo_url': None}
        },
        'text_bild': {
            'name': 'Text/Bild',
            'icon': 'ti-article',
            'beschreibung': 'Freitext mit optionalem Bild',
            'default_config': {
                'inhalt_html': '<p>{{ briefanrede }},</p><p>Ihr Text hier...</p>',
                'bild_url': None,
                'bild_position': 'rechts'
            }
        },
        'fragebogen_cta': {
            'name': 'Fragebogen-Button',
            'icon': 'ti-click',
            'beschreibung': 'Call-to-Action Button',
            'default_config': {'button_text': 'Jetzt teilnehmen', 'button_farbe': '#0066cc'}
        },
        'footer': {
            'name': 'Footer',
            'icon': 'ti-layout-bottombar',
            'beschreibung': 'Abmelde-Link und Impressum',
            'default_config': {'zeige_abmelde_link': True, 'zusatz_text': None}
        }
    }

    return render_template('mailing_admin/editor.html',
                           mailing=mailing,
                           sektion_typen=sektion_typen)


# ========== AJAX Endpoints for Editor ==========

@mailing_admin_bp.route('/<int:id>/editor/sektion', methods=['POST'])
def editor_sektion_add(id):
    """Add a new section to the mailing (AJAX)."""
    service = get_mailing_service()
    mailing = Mailing.query.get_or_404(id)

    if not mailing.is_entwurf:
        return jsonify({'success': False, 'error': 'Mailing kann nicht bearbeitet werden'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Keine Daten empfangen'}), 400

    typ = data.get('typ')
    config = data.get('config', {})

    try:
        sektion_id = service.add_sektion(mailing, typ, config)
        return jsonify({'success': True, 'sektion_id': sektion_id})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@mailing_admin_bp.route('/<int:id>/editor/sektion/<sektion_id>', methods=['PATCH'])
def editor_sektion_update(id, sektion_id):
    """Update a section's configuration (AJAX)."""
    service = get_mailing_service()
    mailing = Mailing.query.get_or_404(id)

    if not mailing.is_entwurf:
        return jsonify({'success': False, 'error': 'Mailing kann nicht bearbeitet werden'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Keine Daten empfangen'}), 400

    config = data.get('config', {})

    try:
        service.update_sektion(mailing, sektion_id, config)
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@mailing_admin_bp.route('/<int:id>/editor/sektion/<sektion_id>', methods=['DELETE'])
def editor_sektion_delete(id, sektion_id):
    """Delete a section from the mailing (AJAX)."""
    service = get_mailing_service()
    mailing = Mailing.query.get_or_404(id)

    if not mailing.is_entwurf:
        return jsonify({'success': False, 'error': 'Mailing kann nicht bearbeitet werden'}), 400

    try:
        service.remove_sektion(mailing, sektion_id)
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@mailing_admin_bp.route('/<int:id>/editor/reorder', methods=['POST'])
def editor_reorder(id):
    """Reorder sections (AJAX) - move a section up or down."""
    service = get_mailing_service()
    mailing = Mailing.query.get_or_404(id)

    if not mailing.is_entwurf:
        return jsonify({'success': False, 'error': 'Mailing kann nicht bearbeitet werden'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Keine Daten empfangen'}), 400

    sektion_id = data.get('sektion_id')
    direction = data.get('direction')  # 'up' or 'down'

    if not sektion_id or direction not in ('up', 'down'):
        return jsonify({'success': False, 'error': 'Ungültige Parameter'}), 400

    # Get current section order
    sektionen = mailing.sektionen
    sektion_ids = [s.get('id') for s in sektionen]

    # Find index and swap
    try:
        idx = sektion_ids.index(sektion_id)
    except ValueError:
        return jsonify({'success': False, 'error': 'Sektion nicht gefunden'}), 404

    if direction == 'up' and idx > 0:
        # Swap with previous
        sektion_ids[idx], sektion_ids[idx - 1] = sektion_ids[idx - 1], sektion_ids[idx]
    elif direction == 'down' and idx < len(sektion_ids) - 1:
        # Swap with next
        sektion_ids[idx], sektion_ids[idx + 1] = sektion_ids[idx + 1], sektion_ids[idx]
    else:
        # Already at boundary, nothing to do
        return jsonify({'success': True, 'message': 'Keine Änderung möglich'})

    try:
        service.reorder_sektionen(mailing, sektion_ids)
        return jsonify({'success': True})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@mailing_admin_bp.route('/<int:id>/test-senden', methods=['POST'])
def test_senden(id):
    """Send test email to current user (placeholder for Phase 3)."""
    mailing = Mailing.query.get_or_404(id)

    if not mailing.is_entwurf:
        flash('Nur Mailings im Entwurf-Status können getestet werden.', 'warning')
        return redirect(url_for('mailing_admin.detail', id=id))

    # TODO: Phase 3 - implement actual test send
    flash('Test-Versand wird in Phase 3 implementiert.', 'info')
    return redirect(url_for('mailing_admin.vorschau', id=id))
