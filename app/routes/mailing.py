"""Public routes for mailing tracking and opt-out (PRD-013).

Blueprint: mailing_bp
Prefix: /m/

These routes are PUBLIC (no login required) - accessed via email links.

Routes:
- GET /t/<token> - Track click and redirect to target
- GET /abmelden/<token> - Show opt-out confirmation page
- POST /abmelden/<token> - Process opt-out
- GET /profil/<token> - Show personal data page
- GET /empfehlen/<token> - Show recommend form
- POST /empfehlen/<token> - Process recommendation
- GET /browser/<token> - Show mailing in browser
"""
from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from urllib.parse import unquote

from app import db
from app.models import MailingEmpfaenger, MailingKlick
from app.services import get_mailing_service, get_branding_service


mailing_bp = Blueprint('mailing', __name__, url_prefix='/m')


@mailing_bp.route('/t/<token>')
def track_click(token):
    """Track a click on a mailing link and redirect to target.

    Query params:
    - typ: Link type ('fragebogen', 'abmelden', 'custom')
    - url: Target URL (for custom links, URL-encoded)

    The tracking token identifies the MailingEmpfaenger.
    """
    service = get_mailing_service()

    # Find empfaenger by token
    empfaenger = service.get_empfaenger_by_token(token)
    if not empfaenger:
        # Invalid token - show error page
        return render_template('mailing/fehler.html',
                               message='Dieser Link ist ungültig oder abgelaufen.'), 404

    # Get link type and target URL
    link_typ = request.args.get('typ', 'custom')

    # Record the click
    service.track_klick(token, link_typ)

    # Determine redirect target based on link type
    if link_typ == 'fragebogen':
        # Get the fragebogen teilnahme magic token
        if empfaenger.fragebogen_teilnahme and empfaenger.fragebogen_teilnahme.magic_token:
            target_url = url_for('dialog.magic_link',
                                 token=empfaenger.fragebogen_teilnahme.magic_token,
                                 _external=True)
        else:
            # No fragebogen linked or no teilnahme created
            return render_template('mailing/fehler.html',
                                   message='Der Fragebogen ist nicht mehr verfügbar.'), 404

    elif link_typ == 'abmelden':
        # Redirect to opt-out page
        target_url = url_for('mailing.abmelden', token=token, _external=True)

    else:
        # Custom URL from query param
        target_url = request.args.get('url')
        if target_url:
            target_url = unquote(target_url)
        else:
            # No target - redirect to home
            target_url = url_for('main.index', _external=True)

    return redirect(target_url)


@mailing_bp.route('/abmelden/<token>')
def abmelden(token):
    """Show opt-out confirmation page."""
    service = get_mailing_service()

    # Find empfaenger by token
    empfaenger = service.get_empfaenger_by_token(token)
    if not empfaenger:
        return render_template('mailing/fehler.html',
                               message='Dieser Abmelde-Link ist ungültig oder abgelaufen.'), 404

    kunde = empfaenger.kunde

    # Check if already opted out
    if kunde.mailing_abgemeldet:
        return render_template('mailing/abgemeldet.html',
                               kunde=kunde,
                               bereits_abgemeldet=True)

    return render_template('mailing/abmelden.html',
                           token=token,
                           kunde=kunde,
                           email=kunde.kontakt_email)


@mailing_bp.route('/abmelden/<token>', methods=['POST'])
def abmelden_confirm(token):
    """Process opt-out request."""
    service = get_mailing_service()

    try:
        service.handle_abmeldung(token)
    except ValueError as e:
        return render_template('mailing/fehler.html',
                               message=str(e)), 400

    # Get kunde for success page
    empfaenger = service.get_empfaenger_by_token(token)
    kunde = empfaenger.kunde if empfaenger else None

    return render_template('mailing/abgemeldet.html',
                           kunde=kunde,
                           bereits_abgemeldet=False)


# ========== PRD-013 Phase 5: New Public Pages ==========

@mailing_bp.route('/profil/<token>')
def profil(token):
    """Show personal data page for the recipient (PRD-013 Phase 5)."""
    service = get_mailing_service()
    branding_service = get_branding_service()

    # Find empfaenger by token
    empfaenger = service.get_empfaenger_by_token(token)
    if not empfaenger:
        return render_template('mailing/fehler.html',
                               message='Dieser Link ist ungültig oder abgelaufen.'), 404

    kunde = empfaenger.kunde
    branding = branding_service.get_branding_dict()

    return render_template('mailing/profil.html',
                           token=token,
                           kunde=kunde,
                           email=kunde.kontakt_email,
                           branding=branding)


@mailing_bp.route('/empfehlen/<token>', methods=['GET'])
def empfehlen(token):
    """Show recommend form (PRD-013 Phase 5)."""
    service = get_mailing_service()
    branding_service = get_branding_service()

    # Find empfaenger by token
    empfaenger = service.get_empfaenger_by_token(token)
    if not empfaenger:
        return render_template('mailing/fehler.html',
                               message='Dieser Link ist ungültig oder abgelaufen.'), 404

    kunde = empfaenger.kunde
    mailing = empfaenger.mailing
    branding = branding_service.get_branding_dict()

    return render_template('mailing/empfehlen.html',
                           token=token,
                           kunde=kunde,
                           mailing=mailing,
                           branding=branding)


@mailing_bp.route('/empfehlen/<token>', methods=['POST'])
def empfehlen_submit(token):
    """Process recommendation request (PRD-013 Phase 5)."""
    from app.services import get_brevo_service

    service = get_mailing_service()
    brevo = get_brevo_service()
    branding_service = get_branding_service()

    # Find empfaenger by token
    empfaenger = service.get_empfaenger_by_token(token)
    if not empfaenger:
        return render_template('mailing/fehler.html',
                               message='Dieser Link ist ungültig oder abgelaufen.'), 404

    kunde = empfaenger.kunde
    mailing = empfaenger.mailing
    branding = branding_service.get_branding_dict()

    # Get form data
    empfaenger_vorname = request.form.get('empfaenger_vorname', '').strip()
    empfaenger_nachname = request.form.get('empfaenger_nachname', '').strip()
    empfaenger_email = request.form.get('empfaenger_email', '').strip()
    kommentar = request.form.get('kommentar', '').strip()

    # Validate
    if not empfaenger_email:
        flash('Bitte eine E-Mail-Adresse eingeben.', 'warning')
        return redirect(url_for('mailing.empfehlen', token=token))

    # Track the recommendation
    service.track_klick(token, 'empfehlen')

    # Build and send recommendation email
    empfehler_name = kunde.firmierung
    if kunde.hauptbenutzer:
        empfehler_name = f'{kunde.hauptbenutzer.vorname} {kunde.hauptbenutzer.nachname}'

    html_content = render_template('mailing/email/weiterempfehlung.html',
                                   empfehler_name=empfehler_name,
                                   empfaenger_vorname=empfaenger_vorname,
                                   mailing=mailing,
                                   kommentar=kommentar,
                                   browser_link=url_for('mailing.browser_ansicht',
                                                        token=token,
                                                        _external=True),
                                   branding=branding)

    result = brevo._send_email(
        to_email=empfaenger_email,
        to_name=f'{empfaenger_vorname} {empfaenger_nachname}'.strip() or 'Empfänger',
        subject=f'{empfehler_name} empfiehlt: {mailing.titel}',
        html_content=html_content
    )

    if result.success:
        return render_template('mailing/empfohlen.html',
                               empfaenger_email=empfaenger_email,
                               branding=branding)
    else:
        flash(f'Fehler beim Senden: {result.error}', 'danger')
        return redirect(url_for('mailing.empfehlen', token=token))


@mailing_bp.route('/browser/<token>')
def browser_ansicht(token):
    """Show mailing content in browser (PRD-013 Phase 5)."""
    service = get_mailing_service()

    # Find empfaenger by token
    empfaenger = service.get_empfaenger_by_token(token)
    if not empfaenger:
        return render_template('mailing/fehler.html',
                               message='Dieser Link ist ungültig oder abgelaufen.'), 404

    mailing = empfaenger.mailing
    kunde = empfaenger.kunde

    # Track the view
    service.track_klick(token, 'browser')

    # Generate tracking URLs for this empfaenger
    if mailing.fragebogen_id and empfaenger.fragebogen_teilnahme:
        fragebogen_link = service.generate_tracking_url(empfaenger, 'fragebogen')
    else:
        fragebogen_link = '#'

    abmelde_link = service.generate_tracking_url(empfaenger, 'abmelden')

    # Render the full mailing HTML
    html_content = service.render_mailing_html(
        mailing,
        kunde=kunde,
        empfaenger=empfaenger,
        fragebogen_link=fragebogen_link,
        abmelde_link=abmelde_link,
        preview_mode=False
    )

    # Return the raw HTML (full page)
    return html_content
