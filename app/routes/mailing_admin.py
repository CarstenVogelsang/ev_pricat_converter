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
    Mailing, MailingEmpfaenger, MailingStatus, Kunde, Fragebogen, FragebogenStatus,
    Medium, MediumTyp
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


# ========== Einstellungen ==========

@mailing_admin_bp.route('/einstellungen', methods=['GET', 'POST'])
def einstellungen():
    """Mailing-Modul Einstellungen."""
    import json
    from app.models import Config, User, Rolle

    # Load test users (role = test_benutzer)
    test_rolle = Rolle.query.filter_by(name='test_benutzer').first()
    test_benutzer = []
    if test_rolle:
        test_benutzer = User.query.filter_by(rolle_id=test_rolle.id, aktiv=True).all()

    # Load internal users (admins and mitarbeiter) for additional recipients
    interne_user = User.query.join(Rolle).filter(
        Rolle.name.in_(['admin', 'mitarbeiter']),
        User.aktiv == True
    ).order_by(User.nachname, User.vorname).all()

    if request.method == 'POST':
        # Handle regular config values
        for key in request.form:
            if key.startswith('mailing_') and not key.endswith('[]'):
                Config.set_value(key, request.form[key])

        # Handle selected test recipients (User IDs)
        selected_ids = request.form.getlist('test_empfaenger_ids[]')
        selected_ids = [int(id) for id in selected_ids if id.isdigit()]
        Config.set_value('mailing_test_empfaenger_ids', json.dumps(selected_ids))

        flash('Einstellungen gespeichert.', 'success')
        return redirect(url_for('mailing_admin.einstellungen'))

    # Load selected test recipient IDs
    selected_ids_raw = Config.get_value('mailing_test_empfaenger_ids', '[]')
    try:
        selected_ids = json.loads(selected_ids_raw)
    except (json.JSONDecodeError, TypeError):
        selected_ids = []

    settings = {
        'brevo_tageslimit': Config.get_value('mailing_brevo_tageslimit', '300'),
        'absender_email': Config.get_value('mailing_absender_email', ''),
        'absender_name': Config.get_value('mailing_absender_name', ''),
        'footer_text': Config.get_value('mailing_footer_text', ''),
        'cta_button_farbe': Config.get_value('mailing_cta_button_farbe', '#e83e8c'),
        'farbe': Config.get_value('mailing_farbe', '#e83e8c'),
    }

    return render_template('administration/mailing/einstellungen.html',
                           settings=settings,
                           test_benutzer=test_benutzer,
                           interne_user=interne_user,
                           selected_ids=selected_ids,
                           admin_tab='module')


# ========== Übersicht & CRUD ==========

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
    """Preview the mailing with sample data and working links."""
    import json
    from app.models import Config, User

    service = get_mailing_service()
    mailing = Mailing.query.get_or_404(id)

    # Load selected test recipients (User IDs)
    selected_ids_raw = Config.get_value('mailing_test_empfaenger_ids', '[]')
    try:
        selected_ids = json.loads(selected_ids_raw)
    except (json.JSONDecodeError, TypeError):
        selected_ids = []

    # Load User objects for dropdown
    test_empfaenger = []
    if selected_ids:
        test_empfaenger = User.query.filter(
            User.id.in_(selected_ids),
            User.aktiv == True
        ).all()

    # Fallback: Current user if no test recipients configured
    if not test_empfaenger:
        test_empfaenger = [current_user]

    # Get sample context with real preview links (G)
    sample_context = service.get_sample_context(mailing=mailing)

    # Get or create preview empfaenger for real link generation
    preview = service.get_or_create_preview_empfaenger(mailing)

    # Render with preview empfaenger (so links work)
    if preview:
        # Generate tracking URLs
        if mailing.fragebogen_id:
            service.ensure_fragebogen_teilnahme(mailing, preview)
            fragebogen_link = service.generate_tracking_url(preview, 'fragebogen') if preview.fragebogen_teilnahme else '#'
        else:
            fragebogen_link = '#'

        abmelde_link = service.generate_tracking_url(preview, 'abmelden')

        email_html = service.render_mailing_html(
            mailing,
            kunde=preview.kunde,
            empfaenger=preview,
            fragebogen_link=fragebogen_link,
            abmelde_link=abmelde_link,
            preview_mode=False  # Use real data
        )
    else:
        # Fallback to preview mode if no Betreiber
        email_html = service.render_mailing_html(mailing, preview_mode=True)

    return render_template('mailing_admin/vorschau.html',
                           mailing=mailing,
                           email_html=email_html,
                           sample_context=sample_context,
                           test_empfaenger=test_empfaenger)


@mailing_admin_bp.route('/<int:id>/editor')
def editor(id):
    """Visual section editor for the mailing."""
    mailing = Mailing.query.get_or_404(id)

    if not mailing.is_entwurf:
        flash('Nur Mailings im Entwurf-Status können bearbeitet werden.', 'warning')
        return redirect(url_for('mailing_admin.detail', id=id))

    # Section type definitions for the UI (PRD-013 Phase 5)
    sektion_typen = {
        'header': {
            'name': 'Header',
            'icon': 'ti-layout-navbar',
            'beschreibung': 'Logo, Telefon und Kontakt-Links',
            'default_config': {
                'zeige_logo': True,
                'logo_url': None,
                'zeige_telefon': True,
                'zeige_email_link': True,
                'zeige_browser_link': True
            }
        },
        'hero': {
            'name': 'Hero',
            'icon': 'ti-marquee-2',
            'beschreibung': 'Headline, Subline und Bild',
            'default_config': {
                'headline': 'Wichtige Information',
                'subline': '',
                'bild_url': None,
                'hintergrund_farbe': '#f8f9fa'
            }
        },
        'text_bild': {
            'name': 'Text/Bild',
            'icon': 'ti-article',
            'beschreibung': 'Freitext mit optionalem Bild',
            'default_config': {
                'inhalt_html': '<p>{{ briefanrede }},</p><p>Ihr Text hier...</p>',
                'bild_url': None,
                'bild_position': 'rechts',
                'bild_alt_text': ''
            }
        },
        'cta_button': {
            'name': 'CTA-Button',
            'icon': 'ti-click',
            'beschreibung': 'Call-to-Action (Fragebogen oder externe URL)',
            'default_config': {
                'link_typ': 'fragebogen',
                'fragebogen_id': None,
                'externe_url': '',
                'button_text': 'Jetzt teilnehmen',
                'button_farbe': '#e83e8c',
                'teaser_text': ''
            }
        },
        'footer': {
            'name': 'Footer',
            'icon': 'ti-layout-bottombar',
            'beschreibung': 'Impressum, Abmelden und weitere Links',
            'default_config': {
                'zeige_abmelde_link': True,
                'zeige_persoenliche_daten_link': True,
                'zeige_weiterempfehlen_link': True,
                'zusatz_text': None
            }
        },
        # Legacy: fragebogen_cta wurde durch cta_button ersetzt
        # Wird nicht im "Hinzufügen"-Dropdown angezeigt, aber existierende Sektionen können bearbeitet werden
        'fragebogen_cta': {
            'name': 'Fragebogen-Button (Legacy)',
            'icon': 'ti-forms',
            'beschreibung': 'Veraltet - bitte CTA-Button verwenden',
            'default_config': {
                'button_text': 'Jetzt teilnehmen',
                'button_farbe': '#0066cc'
            },
            'deprecated': True  # Markierung für Legacy-Typen
        }
    }

    # Get active Fragebögen for CTA-Button dropdown
    frageboegen = Fragebogen.query.filter_by(
        status=FragebogenStatus.AKTIV.value
    ).order_by(Fragebogen.titel).all()

    return render_template('mailing_admin/editor.html',
                           mailing=mailing,
                           sektion_typen=sektion_typen,
                           frageboegen=frageboegen)


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
    """Reorder sections (AJAX).

    Supports two modes:
    1. Array-based (Drag & Drop): {"ordnung": ["id1", "id2", "id3"]}
    2. Direction-based (legacy): {"sektion_id": "id1", "direction": "up|down"}
    """
    service = get_mailing_service()
    mailing = Mailing.query.get_or_404(id)

    if not mailing.is_entwurf:
        return jsonify({'success': False, 'error': 'Mailing kann nicht bearbeitet werden'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Keine Daten empfangen'}), 400

    # Mode 1: Array-based reordering (for Drag & Drop)
    if 'ordnung' in data:
        ordnung = data.get('ordnung', [])
        if not ordnung or not isinstance(ordnung, list):
            return jsonify({'success': False, 'error': 'Ungültige Reihenfolge'}), 400

        try:
            service.reorder_sektionen(mailing, ordnung)
            return jsonify({'success': True})
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 400

    # Mode 2: Direction-based reordering (legacy up/down buttons)
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


@mailing_admin_bp.route('/<int:id>/senden', methods=['GET', 'POST'])
def senden(id):
    """Send mailing to recipients with batch handling."""
    service = get_mailing_service()
    from app.services import get_brevo_service
    brevo = get_brevo_service()

    mailing = Mailing.query.get_or_404(id)

    # Check if mailing can be sent
    if mailing.anzahl_empfaenger == 0:
        flash('Keine Empfänger vorhanden.', 'warning')
        return redirect(url_for('mailing_admin.empfaenger', id=id))

    if request.method == 'POST':
        # Execute batch send
        max_count = request.form.get('max_count')
        max_count = int(max_count) if max_count else None

        result = service.send_batch(mailing, max_count)

        if result.sent_count > 0:
            flash(f'{result.sent_count} E-Mail(s) erfolgreich versendet.', 'success')

        if result.failed_count > 0:
            flash(f'{result.failed_count} E-Mail(s) fehlgeschlagen.', 'danger')

        if result.pending_count > 0:
            flash(f'{result.pending_count} E-Mail(s) noch ausstehend.', 'info')

        return redirect(url_for('mailing_admin.detail', id=id))

    # GET: Show send confirmation page
    batch_info = service.get_batch_info(mailing, brevo.get_remaining_quota())
    quota_info = brevo.get_quota_info()

    return render_template('mailing_admin/senden.html',
                           mailing=mailing,
                           batch_info=batch_info,
                           quota_info=quota_info)


@mailing_admin_bp.route('/<int:id>/test-senden', methods=['POST'])
def test_senden(id):
    """Send test email to selected user with real placeholder data."""
    from app.models import User

    service = get_mailing_service()
    mailing = Mailing.query.get_or_404(id)

    if not mailing.is_entwurf:
        flash('Nur Mailings im Entwurf-Status können getestet werden.', 'warning')
        return redirect(url_for('mailing_admin.detail', id=id))

    # Get recipient User from form
    empfaenger_id = request.form.get('test_empfaenger_id', '').strip()
    if empfaenger_id and empfaenger_id.isdigit():
        empfaenger_user = User.query.get(int(empfaenger_id))
    else:
        empfaenger_user = current_user

    # Get kunde for placeholder resolution (if user has one)
    kunde = None
    if empfaenger_user.kunden:
        kunde = empfaenger_user.kunden[0]  # First assigned customer

    result = service.send_test_email(
        mailing,
        to_email=empfaenger_user.email,
        kunde=kunde,
        to_name=empfaenger_user.full_name
    )

    if result.success:
        if kunde:
            flash(f'Test-E-Mail mit Kundendaten ({kunde.firmierung}) an {empfaenger_user.email} gesendet.', 'success')
        else:
            flash(f'Test-E-Mail (Beispieldaten) an {empfaenger_user.email} gesendet.', 'success')
    else:
        flash(f'Fehler beim Senden: {result.error}', 'danger')

    return redirect(url_for('mailing_admin.vorschau', id=id))


# ========== Phase 4: Statistik ==========

@mailing_admin_bp.route('/<int:id>/statistik')
def statistik(id):
    """Show detailed statistics for a mailing."""
    mailing = Mailing.query.get_or_404(id)

    # Klick-Verteilung nach Typ
    from app.models import MailingKlick
    klick_stats = db.session.query(
        MailingKlick.link_typ,
        db.func.count(MailingKlick.id).label('count')
    ).join(MailingEmpfaenger).filter(
        MailingEmpfaenger.mailing_id == id
    ).group_by(MailingKlick.link_typ).all()

    # In dict konvertieren für einfache Template-Nutzung
    klick_verteilung = {stat.link_typ: stat.count for stat in klick_stats}

    # Abgemeldete Kunden zählen (die durch dieses Mailing abgemeldet wurden)
    abmeldungen = klick_verteilung.get('abmelden', 0)

    # Top-Empfänger nach Klicks
    top_empfaenger = sorted(
        mailing.empfaenger,
        key=lambda e: e.anzahl_klicks,
        reverse=True
    )[:10]

    return render_template('mailing_admin/statistik.html',
                           mailing=mailing,
                           klick_verteilung=klick_verteilung,
                           abmeldungen=abmeldungen,
                           top_empfaenger=top_empfaenger)


# ========== Media Library API (D) ==========

@mailing_admin_bp.route('/api/medien')
def api_medien_list():
    """List available media for the editor (AJAX)."""
    typ = request.args.get('typ')  # Optional filter by type

    query = Medium.query.filter_by(aktiv=True)
    if typ:
        query = query.filter_by(typ=typ)

    medien = query.order_by(Medium.erstellt_am.desc()).all()

    return jsonify({
        'success': True,
        'medien': [m.to_dict() for m in medien]
    })


@mailing_admin_bp.route('/api/medien/upload', methods=['POST'])
def api_medien_upload():
    """Upload a new media file or add external URL (AJAX)."""
    titel = request.form.get('titel', '').strip()
    typ = request.form.get('typ', MediumTyp.BILD.value)
    externe_url = request.form.get('externe_url', '').strip()

    if not titel:
        return jsonify({'success': False, 'error': 'Bitte einen Titel angeben'}), 400

    try:
        # Option 1: External URL
        if externe_url:
            medium = Medium.create_from_url(
                url=externe_url,
                titel=titel,
                typ=typ,
                erstellt_von_id=current_user.id
            )
        # Option 2: File upload
        elif 'datei' in request.files and request.files['datei'].filename:
            file = request.files['datei']
            medium = Medium.create_from_upload(
                file=file,
                titel=titel,
                typ=typ,
                erstellt_von_id=current_user.id
            )
        else:
            return jsonify({'success': False, 'error': 'Keine Datei oder URL angegeben'}), 400

        db.session.add(medium)
        db.session.commit()

        return jsonify({
            'success': True,
            'medium': medium.to_dict()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
