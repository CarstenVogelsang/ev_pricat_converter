"""Admin routes for system management and testing."""
import json
import os
import sys
from datetime import datetime
from flask import Blueprint, render_template, jsonify, flash, redirect, url_for, request, Response, current_app, make_response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import flask

from app import db
from app.models import Config, Lieferant, User, Kunde, KundeCI, Branche, Verband, HelpText, BranchenRolle, BrancheBranchenRolle, Modul, ModulZugriff, AuditLog, Rolle, LookupWert, LieferantBranche
from app.models import ProduktLookup, Attributgruppe, EigenschaftDefinition, Produkt, ProduktStatus
from app.services import FTPService, BrandingService, get_brevo_service
from app.routes.auth import admin_required, mitarbeiter_required

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
THUMB_MAX_SIZE = (100, 100)  # Max thumbnail dimensions


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def create_thumbnail(file, save_path, max_size=THUMB_MAX_SIZE):
    """Create a thumbnail from uploaded image file.

    Args:
        file: File-like object with image data
        save_path: Path where to save the thumbnail
        max_size: Tuple of (width, height) for max dimensions

    Returns:
        True if successful, False otherwise
    """
    try:
        from PIL import Image

        img = Image.open(file)

        # Convert RGBA to RGB for JPEG
        if img.mode == 'RGBA' and save_path.lower().endswith(('.jpg', '.jpeg')):
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            img = background

        # Create thumbnail (maintains aspect ratio)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)

        # Determine format
        if save_path.lower().endswith('.png'):
            img.save(save_path, 'PNG', optimize=True)
        elif save_path.lower().endswith('.gif'):
            img.save(save_path, 'GIF')
        elif save_path.lower().endswith('.svg'):
            # SVG cannot be thumbnailed, just copy
            file.seek(0)
            with open(save_path, 'wb') as f:
                f.write(file.read())
        else:
            img.save(save_path, 'JPEG', quality=85, optimize=True)

        return True
    except Exception as e:
        current_app.logger.error(f"Thumbnail creation failed: {e}")
        return False

admin_bp = Blueprint('admin', __name__)


# ============================================================================
# System Overview (NEW)
# ============================================================================

@admin_bp.route('/')
@login_required
@admin_required
def index():
    """Admin system overview page."""
    # Database status
    db_status = True
    try:
        db.session.execute(db.text('SELECT 1'))
    except Exception:
        db_status = False

    # Counts
    user_count = User.query.count()
    kunde_count = Kunde.query.count()
    lieferant_count = Lieferant.query.count()

    # Modules (dashboard modules only)
    dashboard_modules = Modul.query.filter(
        Modul.zeige_dashboard == True
    ).order_by(Modul.sort_order).all()

    # Environment info
    environment = os.environ.get('FLASK_CONFIG', 'development')

    return render_template(
        'administration/index.html',
        admin_tab='system',
        db_status=db_status,
        user_count=user_count,
        kunde_count=kunde_count,
        lieferant_count=lieferant_count,
        modules=dashboard_modules,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        flask_version=flask.__version__,
        environment=environment
    )


# ============================================================================
# Tab-Übersichtsseiten (NEU)
# ============================================================================

@admin_bp.route('/module-uebersicht')
@login_required
@admin_required
def module_uebersicht():
    """Module administration overview with tiles."""
    return render_template('administration/module_uebersicht.html', admin_tab='module')


@admin_bp.route('/stammdaten-uebersicht')
@login_required
@admin_required
def stammdaten_uebersicht():
    """Stammdaten administration overview with tiles."""
    return render_template('administration/stammdaten_uebersicht.html', admin_tab='stammdaten')


@admin_bp.route('/einstellungen-uebersicht')
@login_required
@admin_required
def einstellungen_uebersicht():
    """Einstellungen administration overview with tiles."""
    return render_template('administration/einstellungen_uebersicht.html', admin_tab='einstellungen')


# ============================================================================
# PRICAT Converter Admin
# ============================================================================

@admin_bp.route('/pricat/')
@login_required
@admin_required
def pricat():
    """PRICAT Converter admin page."""
    # Get config status
    configs = Config.query.all()
    config_dict = {c.key: c.value for c in configs}

    # Check which configs are set
    config_status = {
        'vedes_ftp': bool(config_dict.get('vedes_ftp_host') and config_dict.get('vedes_ftp_user')),
        'elena_ftp': bool(config_dict.get('elena_ftp_host') and config_dict.get('elena_ftp_user')),
    }

    # Get supplier count
    lieferant_count = Lieferant.query.count()
    active_lieferant_count = Lieferant.query.filter_by(aktiv=True).count()

    return render_template(
        'administration/pricat.html',
        config_status=config_status,
        lieferant_count=lieferant_count,
        active_lieferant_count=active_lieferant_count
    )


@admin_bp.route('/test-ftp/vedes', methods=['POST'])
@login_required
@admin_required
def test_ftp_vedes():
    """Test VEDES FTP connection."""
    ftp_service = FTPService()
    result = ftp_service.test_connection(target='vedes')

    if result.success:
        flash(f'VEDES FTP Verbindung erfolgreich: {result.message}', 'success')
    else:
        flash(f'VEDES FTP Verbindung fehlgeschlagen: {result.message}', 'danger')

    return redirect(url_for('admin.pricat'))


@admin_bp.route('/test-ftp/elena', methods=['POST'])
@login_required
@admin_required
def test_ftp_elena():
    """Test Elena FTP connection."""
    ftp_service = FTPService()
    result = ftp_service.test_connection(target='elena')

    if result.success:
        flash(f'Elena FTP Verbindung erfolgreich: {result.message}', 'success')
    else:
        flash(f'Elena FTP Verbindung fehlgeschlagen: {result.message}', 'danger')

    return redirect(url_for('admin.pricat'))


@admin_bp.route('/sync-lieferanten', methods=['POST'])
@login_required
@admin_required
def sync_lieferanten():
    """Synchronize Lieferanten with VEDES FTP."""
    ftp_service = FTPService()
    result = ftp_service.sync_lieferanten()

    if result['success']:
        flash(result['message'], 'success')
        if result['created']:
            flash(f"Neu angelegt: {', '.join(result['created'][:5])}"
                  + (f" (+{len(result['created'])-5} weitere)" if len(result['created']) > 5 else ''),
                  'info')
    else:
        flash(f"Sync fehlgeschlagen: {result['message']}", 'danger')

    return redirect(url_for('admin.pricat'))


@admin_bp.route('/config/export')
@login_required
@admin_required
def config_export():
    """Export all config entries as JSON file."""
    configs = Config.query.all()
    config_list = [
        {
            'key': c.key,
            'value': c.value,
            'beschreibung': c.beschreibung
        }
        for c in configs
    ]

    # Create JSON response with download headers
    json_data = json.dumps(config_list, indent=2, ensure_ascii=False)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'pricat_config_{timestamp}.json'

    response = make_response(json_data)
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.headers['Cache-Control'] = 'no-cache'
    return response


@admin_bp.route('/config/import', methods=['POST'])
@login_required
@admin_required
def config_import():
    """Import config entries from uploaded JSON file."""
    if 'config_file' not in request.files:
        flash('Keine Datei ausgewählt', 'danger')
        return redirect(url_for('admin.pricat'))

    file = request.files['config_file']
    if file.filename == '':
        flash('Keine Datei ausgewählt', 'danger')
        return redirect(url_for('admin.pricat'))

    if not file.filename.endswith('.json'):
        flash('Nur JSON-Dateien erlaubt', 'danger')
        return redirect(url_for('admin.pricat'))

    try:
        # Read and parse JSON
        content = file.read().decode('utf-8')
        config_list = json.loads(content)

        if not isinstance(config_list, list):
            flash('Ungültiges JSON-Format (erwartet: Array)', 'danger')
            return redirect(url_for('admin.pricat'))

        created = 0
        updated = 0

        for entry in config_list:
            if 'key' not in entry:
                continue

            existing = Config.query.filter_by(key=entry['key']).first()
            if existing:
                existing.value = entry.get('value', '')
                if 'beschreibung' in entry:
                    existing.beschreibung = entry['beschreibung']
                updated += 1
            else:
                new_config = Config(
                    key=entry['key'],
                    value=entry.get('value', ''),
                    beschreibung=entry.get('beschreibung', '')
                )
                db.session.add(new_config)
                created += 1

        db.session.commit()
        flash(f'Config importiert: {created} neu, {updated} aktualisiert', 'success')

    except json.JSONDecodeError as e:
        flash(f'JSON-Fehler: {str(e)}', 'danger')
    except Exception as e:
        flash(f'Import-Fehler: {str(e)}', 'danger')

    return redirect(url_for('admin.pricat'))


# ============================================================================
# Other Module Admin Pages (Placeholders)
# ============================================================================

@admin_bp.route('/kunden-report/')
@login_required
@admin_required
def kunden_report():
    """Lead & Kundenreport admin page."""
    return render_template('administration/kunden_report.html')


@admin_bp.route('/lieferanten-auswahl/')
@login_required
@admin_required
def lieferanten_auswahl():
    """Meine Lieferanten admin page."""
    return render_template('administration/lieferanten_auswahl.html')


@admin_bp.route('/content-generator/')
@login_required
@admin_required
def content_generator():
    """Content Generator admin page."""
    return render_template('administration/content_generator.html')


# ============================================================================
# Health Checks
# ============================================================================

@admin_bp.route('/health')
def health():
    """Health check endpoint (JSON) for monitoring."""
    health_status = {
        'status': 'healthy',
        'checks': {}
    }

    # Database check
    try:
        db.session.execute(db.text('SELECT 1'))
        health_status['checks']['database'] = {'status': 'ok'}
    except Exception as e:
        health_status['checks']['database'] = {'status': 'error', 'message': str(e)}
        health_status['status'] = 'unhealthy'

    # Config check
    required_configs = ['vedes_ftp_host', 'vedes_ftp_user']
    missing_configs = []
    for key in required_configs:
        config = Config.query.filter_by(key=key).first()
        if not config or not config.value:
            missing_configs.append(key)

    if missing_configs:
        health_status['checks']['config'] = {
            'status': 'warning',
            'missing': missing_configs
        }
    else:
        health_status['checks']['config'] = {'status': 'ok'}

    # FTP checks (optional, can be slow)
    ftp_service = FTPService()

    # VEDES FTP
    vedes_result = ftp_service.test_connection(target='vedes')
    health_status['checks']['vedes_ftp'] = {
        'status': 'ok' if vedes_result.success else 'error',
        'message': vedes_result.message
    }
    if not vedes_result.success:
        health_status['status'] = 'degraded'

    # Elena FTP
    elena_result = ftp_service.test_connection(target='elena')
    health_status['checks']['elena_ftp'] = {
        'status': 'ok' if elena_result.success else 'error',
        'message': elena_result.message
    }
    if not elena_result.success:
        health_status['status'] = 'degraded'

    return jsonify(health_status)


@admin_bp.route('/api/health')
def api_health():
    """Simple health check for load balancers/monitoring."""
    try:
        db.session.execute(db.text('SELECT 1'))
        return jsonify({'status': 'ok'}), 200
    except Exception:
        return jsonify({'status': 'error'}), 503


# ============================================================================
# Betreiber / Branding Settings
# ============================================================================

@admin_bp.route('/betreiber', methods=['GET', 'POST'])
@login_required
@admin_required
def betreiber():
    """Betreiber / Branding settings page.

    Der Betreiber ist der Kunde, dessen CI für das Portal verwendet wird.
    - Dropdown zur Auswahl des Betreibers
    - CI-Vorschau
    - E-Mail-Signatur-Editor (WYSIWYG)
    """
    branding_service = BrandingService()

    if request.method == 'POST':
        action = request.form.get('action', 'save_branding')

        if action == 'save_branding':
            # Handle logo upload
            if 'logo' in request.files:
                file = request.files['logo']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    # Add timestamp to prevent caching issues
                    name, ext = os.path.splitext(filename)
                    filename = f"logo_{int(datetime.now().timestamp())}{ext}"

                    upload_path = os.path.join(
                        current_app.static_folder, 'uploads', filename
                    )
                    file.save(upload_path)

                    # Save to config
                    _update_config('brand_logo', filename)
                    flash('Logo erfolgreich hochgeladen', 'success')

            # Handle text fields
            _update_config('brand_app_title', request.form.get('app_title', ''))
            _update_config('brand_primary_color', request.form.get('primary_color', '#0d6efd'))
            _update_config('brand_secondary_color', request.form.get('secondary_color', '#6c757d'))
            _update_config('copyright_text', request.form.get('copyright_text', ''))
            _update_config('copyright_url', request.form.get('copyright_url', ''))

            # Handle font settings
            _update_config('brand_font_family', request.form.get('font_family', 'Inter'))
            _update_config('brand_font_weights', request.form.get('font_weights', '400,500,600,700'))

            # Handle secondary font settings
            _update_config('brand_secondary_font_family', request.form.get('secondary_font_family', ''))
            _update_config('brand_secondary_font_weights', request.form.get('secondary_font_weights', ''))

            db.session.commit()
            flash('Branding-Einstellungen gespeichert', 'success')
            return redirect(url_for('admin.betreiber'))

    # GET request
    # Get current Betreiber (Systemkunde)
    betreiber_kunde = Kunde.query.filter_by(ist_systemkunde=True).first()

    # Load Kunden with CI data for Betreiber selection
    kunden_mit_ci = Kunde.query.filter(Kunde.ci != None).order_by(Kunde.firmierung).all()

    branding_config = branding_service.get_branding()
    selected_fonts = branding_service.get_selected_fonts()
    return render_template(
        'administration/betreiber.html',
        branding=branding_config,
        current_logo=Config.get_value('brand_logo', ''),
        kunden_mit_ci=kunden_mit_ci,
        betreiber=betreiber_kunde,
        available_fonts=BrandingService.AVAILABLE_FONTS,
        selected_fonts=selected_fonts
    )


# Keep old route for backwards compatibility
@admin_bp.route('/branding', methods=['GET', 'POST'])
@login_required
@admin_required
def branding():
    """Redirect to betreiber page (backwards compatibility)."""
    return redirect(url_for('admin.betreiber'))


@admin_bp.route('/betreiber/set', methods=['POST'])
@login_required
@admin_required
def set_betreiber():
    """Set a Kunde as the Betreiber (Systemkunde) and adopt their CI."""
    from app.services import log_mittel

    kunde_id = request.form.get('kunde_id', type=int)
    if not kunde_id:
        flash('Bitte einen Kunden auswählen', 'warning')
        return redirect(url_for('admin.betreiber'))

    kunde = Kunde.query.get_or_404(kunde_id)

    # Remove current Betreiber flag
    Kunde.query.filter_by(ist_systemkunde=True).update({'ist_systemkunde': False})

    # Set new Betreiber
    kunde.ist_systemkunde = True

    # Adopt CI if available
    if kunde.ci:
        ci = kunde.ci
        if ci.logo_url:
            _update_config('brand_logo_url', ci.logo_url)
            _update_config('brand_logo', '')  # Clear local logo
        if ci.primary_color:
            _update_config('brand_primary_color', ci.primary_color)
        if ci.secondary_color:
            _update_config('brand_secondary_color', ci.secondary_color)

    # Set copyright from Firmierung
    _update_config('copyright_text', f'© {datetime.now().year} {kunde.firmierung}')
    if kunde.website_url:
        _update_config('copyright_url', kunde.website_url)

    db.session.commit()

    log_mittel(
        modul='system',
        aktion='betreiber_gesetzt',
        details=f'"{kunde.firmierung}" als Betreiber gesetzt',
        entity_type='Kunde',
        entity_id=kunde.id
    )
    db.session.commit()

    flash(f'"{kunde.firmierung}" ist jetzt Betreiber. CI wurde übernommen.', 'success')
    return redirect(url_for('admin.betreiber'))


@admin_bp.route('/betreiber/footer', methods=['POST'])
@login_required
@admin_required
def save_footer():
    """Save the E-Mail footer/signature for the Betreiber."""
    from app.services import log_mittel

    betreiber = Kunde.query.filter_by(ist_systemkunde=True).first()
    if not betreiber:
        flash('Kein Betreiber ausgewählt. Bitte zuerst einen Betreiber festlegen.', 'warning')
        return redirect(url_for('admin.betreiber'))

    footer_html = request.form.get('email_footer', '').strip()
    betreiber.email_footer = footer_html if footer_html else None

    db.session.commit()

    log_mittel(
        modul='system',
        aktion='email_footer_gespeichert',
        details=f'E-Mail-Signatur für Betreiber "{betreiber.firmierung}" aktualisiert',
        entity_type='Kunde',
        entity_id=betreiber.id
    )
    db.session.commit()

    flash('E-Mail-Signatur gespeichert', 'success')
    return redirect(url_for('admin.betreiber'))


@admin_bp.route('/betreiber/delete-logo', methods=['POST'])
@login_required
@admin_required
def delete_logo():
    """Delete the current logo."""
    logo_path = Config.get_value('brand_logo', '')
    if logo_path:
        full_path = os.path.join(current_app.static_folder, 'uploads', logo_path)
        if os.path.exists(full_path):
            os.remove(full_path)

        _update_config('brand_logo', '')
        # Also clear external logo URL
        _update_config('brand_logo_url', '')
        db.session.commit()
        flash('Logo gelöscht', 'success')

    return redirect(url_for('admin.betreiber'))


@admin_bp.route('/branding/apply-kunde/<int:kunde_id>', methods=['POST'])
@login_required
@admin_required
def apply_kunde_branding(kunde_id):
    """Apply branding from Kunde CI data (legacy route, use set_betreiber instead)."""
    kunde = Kunde.query.get_or_404(kunde_id)

    if not kunde.ci:
        flash('Kunde hat keine CI-Daten', 'warning')
        return redirect(url_for('admin.betreiber'))

    ci = kunde.ci

    # Logo übernehmen (externe URL)
    if ci.logo_url:
        _update_config('brand_logo_url', ci.logo_url)
        # Clear local logo so external URL is used
        _update_config('brand_logo', '')

    # Farben übernehmen
    if ci.primary_color:
        _update_config('brand_primary_color', ci.primary_color)
    if ci.secondary_color:
        _update_config('brand_secondary_color', ci.secondary_color)

    # Copyright aus Firmierung
    _update_config('copyright_text', f'© {datetime.now().year} {kunde.firmierung}')

    # Website-Link
    if kunde.website_url:
        _update_config('copyright_url', kunde.website_url)

    db.session.commit()
    flash(f'Branding von "{kunde.firmierung}" übernommen', 'success')
    return redirect(url_for('admin.betreiber'))


def _update_config(key: str, value: str):
    """Update or create a config entry."""
    config = Config.query.filter_by(key=key).first()
    if config:
        config.value = value
    else:
        config = Config(key=key, value=value)
        db.session.add(config)


# ============================================================================
# System Settings
# ============================================================================

@admin_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    """System settings page for API keys and configuration."""
    if request.method == 'POST':
        # API & Services - Firecrawl
        _update_config('firecrawl_api_key', request.form.get('firecrawl_api_key', ''))
        _update_config('firecrawl_credit_kosten', request.form.get('firecrawl_credit_kosten', '0.005'))

        # API & Services - Brevo E-Mail
        _update_config('brevo_api_key', request.form.get('brevo_api_key', ''))
        _update_config('brevo_sender_email', request.form.get('brevo_sender_email', 'noreply@e-vendo.de'))
        _update_config('brevo_sender_name', request.form.get('brevo_sender_name', 'e-vendo AG'))
        _update_config('portal_base_url', request.form.get('portal_base_url', 'https://portal.e-vendo.de'))
        _update_config('brevo_daily_limit', request.form.get('brevo_daily_limit', '300'))

        # FTP VEDES
        _update_config('vedes_ftp_host', request.form.get('vedes_ftp_host', ''))
        _update_config('vedes_ftp_port', request.form.get('vedes_ftp_port', '21'))
        _update_config('vedes_ftp_user', request.form.get('vedes_ftp_user', ''))
        _update_config('vedes_ftp_pass', request.form.get('vedes_ftp_pass', ''))
        _update_config('vedes_ftp_basepath', request.form.get('vedes_ftp_basepath', '/pricat/'))
        _update_config('vedes_ftp_encoding', request.form.get('vedes_ftp_encoding', 'utf-8'))

        # FTP Elena
        _update_config('elena_ftp_host', request.form.get('elena_ftp_host', ''))
        _update_config('elena_ftp_port', request.form.get('elena_ftp_port', '21'))
        _update_config('elena_ftp_user', request.form.get('elena_ftp_user', ''))
        _update_config('elena_ftp_pass', request.form.get('elena_ftp_pass', ''))

        # S3 Storage
        _update_config('s3_enabled', 'true' if request.form.get('s3_enabled') else 'false')
        _update_config('s3_endpoint', request.form.get('s3_endpoint', ''))
        _update_config('s3_access_key', request.form.get('s3_access_key', ''))
        _update_config('s3_secret_key', request.form.get('s3_secret_key', ''))
        _update_config('s3_bucket', request.form.get('s3_bucket', ''))

        # Image Download
        _update_config('image_download_threads', request.form.get('image_download_threads', '5'))
        _update_config('image_timeout', request.form.get('image_timeout', '30'))

        db.session.commit()
        flash('Einstellungen gespeichert', 'success')
        return redirect(url_for('admin.settings'))

    # Load all configs for display
    config_keys = [
        'firecrawl_api_key', 'firecrawl_credit_kosten',
        'brevo_api_key', 'brevo_sender_email', 'brevo_sender_name', 'portal_base_url', 'brevo_daily_limit',
        'brevo_test_user_id',
        'vedes_ftp_host', 'vedes_ftp_port', 'vedes_ftp_user', 'vedes_ftp_pass', 'vedes_ftp_basepath', 'vedes_ftp_encoding',
        'elena_ftp_host', 'elena_ftp_port', 'elena_ftp_user', 'elena_ftp_pass',
        's3_enabled', 's3_endpoint', 's3_access_key', 's3_secret_key', 's3_bucket',
        'image_download_threads', 'image_timeout'
    ]
    configs = {key: Config.get_value(key, '') for key in config_keys}

    # Load all configs for overview table
    all_configs_list = Config.query.order_by(Config.key).all()
    all_configs = {c.key: c.value for c in all_configs_list}
    config_count = len(all_configs_list)

    # Get Brevo quota info for display
    brevo_service = get_brevo_service()
    brevo_quota = brevo_service.get_quota_info()

    # Get all users for test email dropdown
    all_users = User.query.filter_by(aktiv=True).order_by(User.nachname, User.vorname).all()

    return render_template(
        'administration/settings.html',
        configs=configs,
        all_configs=all_configs,
        config_count=config_count,
        brevo_quota=brevo_quota,
        all_users=all_users
    )


# ============================================================================
# Brevo E-Mail Test
# ============================================================================

@admin_bp.route('/brevo/test', methods=['POST'])
@login_required
@admin_required
def brevo_test_email():
    """Send a test email via Brevo to verify configuration."""
    test_user_id = request.form.get('test_user_id', type=int)

    if not test_user_id:
        flash('Bitte einen Empfänger auswählen', 'warning')
        return redirect(url_for('admin.settings') + '#api')

    # Save selection for next time
    _update_config('brevo_test_user_id', str(test_user_id))
    db.session.commit()

    # Get user
    user = User.query.get(test_user_id)
    if not user:
        flash('Benutzer nicht gefunden', 'danger')
        return redirect(url_for('admin.settings') + '#api')

    # Send test email
    brevo_service = get_brevo_service()
    result = brevo_service.send_test_email(user.email, user.full_name)

    if result.success:
        flash(f'Test-E-Mail erfolgreich an {user.email} gesendet (Message-ID: {result.message_id})', 'success')
    else:
        flash(f'Fehler beim Senden der Test-E-Mail: {result.error}', 'danger')

    return redirect(url_for('admin.settings') + '#api')


@admin_bp.route('/brevo/status', methods=['POST'])
@login_required
@admin_required
def brevo_check_status():
    """Check Brevo API status and account info."""
    brevo_service = get_brevo_service()
    status = brevo_service.check_api_status()

    if status['success']:
        flash(
            f'Brevo API aktiv ✓ | Konto: {status["email"]} | Plan: {status["plan"]} | Credits: {status["credits"]}',
            'success'
        )
    else:
        flash(f'Brevo API Fehler: {status["error"]}', 'danger')

    return redirect(url_for('admin.settings') + '#api')


# ============================================================================
# Branchen Management
# ============================================================================

@admin_bp.route('/branchen', methods=['GET', 'POST'])
@login_required
@admin_required
def branchen():
    """Manage Branchen (Industries) - Master-Detail UI.

    Master-Detail Ansicht:
    - Links: Hauptbranchen (parent_id=NULL)
    - Rechts: Unterbranchen der ausgewaehlten Hauptbranche
    """
    # Aktive Hauptbranche aus Query-Parameter
    aktive_hauptbranche_id = request.args.get('hauptbranche', type=int)

    if request.method == 'POST':
        action = request.form.get('action')
        branche_typ = request.form.get('branche_typ', 'unterbranche')  # 'hauptbranche' oder 'unterbranche'

        if action == 'create':
            name = request.form.get('name', '').strip()
            icon = request.form.get('icon', 'category').strip()
            sortierung = request.form.get('sortierung', 0, type=int)

            if name:
                if branche_typ == 'hauptbranche':
                    # Hauptbranche: parent_id = NULL
                    existing = Branche.query.filter_by(name=name, parent_id=None).first()
                    if existing:
                        flash(f'Hauptbranche "{name}" existiert bereits', 'warning')
                    else:
                        slug = name.lower().replace(' ', '-').replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
                        branche = Branche(name=name, icon=icon, sortierung=sortierung, aktiv=True, parent_id=None, slug=slug)
                        db.session.add(branche)
                        db.session.commit()
                        flash(f'Hauptbranche "{name}" angelegt', 'success')
                        aktive_hauptbranche_id = branche.id
                else:
                    # Unterbranche: parent_id = aktive Hauptbranche
                    parent_id = request.form.get('parent_id', type=int) or aktive_hauptbranche_id
                    if not parent_id:
                        flash('Bitte erst eine Hauptbranche auswählen', 'warning')
                    else:
                        existing = Branche.query.filter_by(name=name, parent_id=parent_id).first()
                        if existing:
                            flash(f'Unterbranche "{name}" existiert bereits in dieser Hauptbranche', 'warning')
                        else:
                            parent = Branche.query.get(parent_id)
                            parent_slug = parent.slug or parent.name.lower()
                            slug = f"{parent_slug}-{name.lower().replace(' ', '-').replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')}"
                            branche = Branche(name=name, icon=icon, sortierung=sortierung, aktiv=True, parent_id=parent_id, slug=slug)
                            db.session.add(branche)
                            db.session.commit()
                            flash(f'Unterbranche "{name}" angelegt', 'success')

        elif action == 'update':
            branche_id = request.form.get('id', type=int)
            branche = Branche.query.get(branche_id)
            if branche:
                branche.name = request.form.get('name', branche.name).strip()
                branche.icon = request.form.get('icon', branche.icon).strip()
                branche.sortierung = request.form.get('sortierung', branche.sortierung, type=int)
                branche.aktiv = request.form.get('aktiv') == 'on'

                # Zulässige Rollen aktualisieren (nur für Unterbranchen)
                if not branche.ist_hauptbranche:
                    selected_rollen = request.form.getlist('rollen', type=int)
                    # Alte Zuordnungen löschen
                    BrancheBranchenRolle.query.filter_by(branche_id=branche.id).delete()
                    # Neue Zuordnungen anlegen
                    for rolle_id in selected_rollen:
                        bbr = BrancheBranchenRolle(branche_id=branche.id, branchenrolle_id=rolle_id)
                        db.session.add(bbr)

                db.session.commit()
                flash(f'Branche "{branche.name}" aktualisiert', 'success')

                # Bei Unterbranche: Hauptbranche beibehalten
                if branche.parent_id:
                    aktive_hauptbranche_id = branche.parent_id

        elif action == 'delete':
            branche_id = request.form.get('id', type=int)
            branche = Branche.query.get(branche_id)
            if branche:
                # Check if used by customers
                if branche.kunden:
                    flash(f'Branche "{branche.name}" wird von {len(branche.kunden)} Kunden verwendet und kann nicht gelöscht werden', 'warning')
                # Check if Hauptbranche with Unterbranchen
                elif branche.ist_hauptbranche and branche.unterbranchen.count() > 0:
                    flash(f'Hauptbranche "{branche.name}" hat noch {branche.unterbranchen.count()} Unterbranchen und kann nicht gelöscht werden', 'warning')
                else:
                    name = branche.name
                    parent_id = branche.parent_id
                    db.session.delete(branche)
                    db.session.commit()
                    flash(f'Branche "{name}" gelöscht', 'success')
                    # Bei Unterbranche: Hauptbranche beibehalten
                    if parent_id:
                        aktive_hauptbranche_id = parent_id

        # Redirect mit Hauptbranche-Parameter
        if aktive_hauptbranche_id:
            return redirect(url_for('admin.branchen', hauptbranche=aktive_hauptbranche_id))
        return redirect(url_for('admin.branchen'))

    # GET: Daten laden
    hauptbranchen = Branche.query.filter_by(parent_id=None).order_by(Branche.sortierung, Branche.name).all()

    # Erste Hauptbranche als Default auswählen
    if not aktive_hauptbranche_id and hauptbranchen:
        aktive_hauptbranche_id = hauptbranchen[0].id

    # Unterbranchen der aktiven Hauptbranche laden
    unterbranchen = []
    aktive_hauptbranche = None
    if aktive_hauptbranche_id:
        aktive_hauptbranche = Branche.query.get(aktive_hauptbranche_id)
        if aktive_hauptbranche:
            unterbranchen = Branche.query.filter_by(parent_id=aktive_hauptbranche_id).order_by(Branche.sortierung, Branche.name).all()

    # Alle aktiven BranchenRollen für Multi-Select
    alle_rollen = BranchenRolle.query.filter_by(aktiv=True).order_by(BranchenRolle.sortierung).all()

    return render_template(
        'administration/branchen.html',
        hauptbranchen=hauptbranchen,
        unterbranchen=unterbranchen,
        aktive_hauptbranche=aktive_hauptbranche,
        aktive_hauptbranche_id=aktive_hauptbranche_id,
        alle_rollen=alle_rollen
    )


@admin_bp.route('/branchen/reorder', methods=['POST'])
@login_required
@admin_required
def branchen_reorder():
    """Update sort order for Branchen via AJAX."""
    data = request.get_json()

    if not data or 'order' not in data:
        return jsonify({'success': False, 'message': 'Keine Sortierreihenfolge übergeben'}), 400

    order = data['order']  # Liste von IDs in neuer Reihenfolge

    try:
        for index, branche_id in enumerate(order):
            branche = Branche.query.get(int(branche_id))
            if branche:
                branche.sortierung = (index + 1) * 10  # 10, 20, 30, ...

        db.session.commit()
        return jsonify({'success': True, 'message': 'Sortierung gespeichert'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/branchen/import', methods=['POST'])
@login_required
@admin_required
def branchen_import():
    """Import Hauptbranche with Unterbranchen and Rollen from JSON file.

    Expected JSON format (from unternehmensdaten.org):
    {
        "meta": {
            "source": "unternehmensdaten.org",
            "version": "1.0",
            "export_date": "2025-12-12T10:30:00Z",
            "type": "branchenkatalog"
        },
        "hauptbranche": {
            "uuid": "...",
            "name": "HANDWERK",
            "slug": "handwerk",
            "icon": "fas fa-tools"
        },
        "unterbranchen": [
            {
                "uuid": "...",
                "name": "Elektroinstallation",
                "slug": "elektroinstallation",
                "icon": "fas fa-bolt",
                "sortierung": 1,
                "rollen": ["hersteller", "grosshaendler"]
            }
        ],
        "rollen_katalog": [  // optional
            {
                "uuid": "...",
                "code": "hersteller",
                "name": "Hersteller",
                "icon": "fas fa-industry",
                "beschreibung": "..."
            }
        ]
    }
    """
    if 'import_file' not in request.files:
        flash('Keine Datei ausgewählt', 'danger')
        return redirect(url_for('admin.branchen'))

    file = request.files['import_file']
    if file.filename == '':
        flash('Keine Datei ausgewählt', 'danger')
        return redirect(url_for('admin.branchen'))

    if not file.filename.endswith('.json'):
        flash('Nur JSON-Dateien erlaubt', 'danger')
        return redirect(url_for('admin.branchen'))

    try:
        # Read and parse JSON
        content = file.read().decode('utf-8')
        data = json.loads(content)

        # Validate required fields
        if 'hauptbranche' not in data:
            flash('Ungültiges Format: "hauptbranche" fehlt', 'danger')
            return redirect(url_for('admin.branchen'))

        hb_data = data['hauptbranche']
        if 'name' not in hb_data:
            flash('Ungültiges Format: "hauptbranche.name" fehlt', 'danger')
            return redirect(url_for('admin.branchen'))

        stats = {
            'rollen_created': 0,
            'rollen_updated': 0,
            'hauptbranche_created': False,
            'hauptbranche_updated': False,
            'unterbranchen_created': 0,
            'unterbranchen_updated': 0,
            'rollen_zuordnungen': 0
        }

        # 1. Optional: Process rollen_katalog first (so we can reference them later)
        rollen_code_map = {}  # code -> BranchenRolle
        if 'rollen_katalog' in data:
            for rolle_data in data['rollen_katalog']:
                code = rolle_data.get('code', '').strip().upper()
                if not code:
                    continue

                # Try to find by UUID first, then by code
                rolle = None
                if rolle_data.get('uuid'):
                    rolle = BranchenRolle.query.filter_by(uuid=rolle_data['uuid']).first()
                if not rolle:
                    rolle = BranchenRolle.query.filter_by(code=code).first()

                if rolle:
                    # Update existing
                    rolle.name = rolle_data.get('name', rolle.name)
                    rolle.icon = _clean_icon(rolle_data.get('icon', rolle.icon))
                    rolle.beschreibung = rolle_data.get('beschreibung', rolle.beschreibung)
                    if rolle_data.get('uuid') and not rolle.uuid:
                        rolle.uuid = rolle_data['uuid']
                    stats['rollen_updated'] += 1
                else:
                    # Create new
                    rolle = BranchenRolle(
                        uuid=rolle_data.get('uuid'),
                        code=code,
                        name=rolle_data.get('name', code),
                        icon=_clean_icon(rolle_data.get('icon', 'tag')),
                        beschreibung=rolle_data.get('beschreibung', ''),
                        aktiv=True,
                        sortierung=rolle_data.get('sortierung', 0)
                    )
                    db.session.add(rolle)
                    stats['rollen_created'] += 1

                rollen_code_map[code] = rolle

        # Commit rollen first so they have IDs
        db.session.flush()

        # Build full code map including existing roles
        all_rollen = BranchenRolle.query.all()
        for r in all_rollen:
            rollen_code_map[r.code] = r

        # 2. Process Hauptbranche (upsert by UUID or name)
        hauptbranche = None
        if hb_data.get('uuid'):
            hauptbranche = Branche.query.filter_by(uuid=hb_data['uuid'], parent_id=None).first()
        if not hauptbranche:
            hauptbranche = Branche.query.filter_by(name=hb_data['name'], parent_id=None).first()

        if hauptbranche:
            # Update existing
            hauptbranche.name = hb_data['name']
            hauptbranche.slug = hb_data.get('slug') or _generate_slug(hb_data['name'])
            hauptbranche.icon = _clean_icon(hb_data.get('icon', hauptbranche.icon))
            if hb_data.get('uuid') and not hauptbranche.uuid:
                hauptbranche.uuid = hb_data['uuid']
            stats['hauptbranche_updated'] = True
        else:
            # Create new
            hauptbranche = Branche(
                uuid=hb_data.get('uuid'),
                name=hb_data['name'],
                slug=hb_data.get('slug') or _generate_slug(hb_data['name']),
                icon=_clean_icon(hb_data.get('icon', 'folder')),
                parent_id=None,
                aktiv=True,
                sortierung=hb_data.get('sortierung', 0)
            )
            db.session.add(hauptbranche)
            stats['hauptbranche_created'] = True

        # Flush to get hauptbranche.id
        db.session.flush()

        # 3. Process Unterbranchen
        if 'unterbranchen' in data:
            for idx, ub_data in enumerate(data['unterbranchen']):
                if not ub_data.get('name'):
                    continue

                # Try to find by UUID first, then by name+parent
                unterbranche = None
                if ub_data.get('uuid'):
                    unterbranche = Branche.query.filter_by(uuid=ub_data['uuid']).first()
                if not unterbranche:
                    unterbranche = Branche.query.filter_by(
                        name=ub_data['name'],
                        parent_id=hauptbranche.id
                    ).first()

                if unterbranche:
                    # Update existing
                    unterbranche.name = ub_data['name']
                    unterbranche.slug = ub_data.get('slug') or _generate_slug(ub_data['name'], hauptbranche.slug)
                    unterbranche.icon = _clean_icon(ub_data.get('icon', unterbranche.icon))
                    unterbranche.sortierung = ub_data.get('sortierung', (idx + 1) * 10)
                    if ub_data.get('uuid') and not unterbranche.uuid:
                        unterbranche.uuid = ub_data['uuid']
                    stats['unterbranchen_updated'] += 1
                else:
                    # Create new
                    unterbranche = Branche(
                        uuid=ub_data.get('uuid'),
                        name=ub_data['name'],
                        slug=ub_data.get('slug') or _generate_slug(ub_data['name'], hauptbranche.slug),
                        icon=_clean_icon(ub_data.get('icon', 'category')),
                        parent_id=hauptbranche.id,
                        aktiv=True,
                        sortierung=ub_data.get('sortierung', (idx + 1) * 10)
                    )
                    db.session.add(unterbranche)
                    stats['unterbranchen_created'] += 1

                # Flush to get unterbranche.id
                db.session.flush()

                # 4. Process Rollen-Zuordnungen for this Unterbranche
                if 'rollen' in ub_data and isinstance(ub_data['rollen'], list):
                    # Clear existing assignments
                    BrancheBranchenRolle.query.filter_by(branche_id=unterbranche.id).delete()

                    for rolle_code in ub_data['rollen']:
                        code_upper = rolle_code.strip().upper()
                        if code_upper in rollen_code_map:
                            rolle = rollen_code_map[code_upper]
                            # Create assignment
                            bbr = BrancheBranchenRolle(
                                branche_id=unterbranche.id,
                                branchenrolle_id=rolle.id
                            )
                            db.session.add(bbr)
                            stats['rollen_zuordnungen'] += 1
                        else:
                            current_app.logger.warning(
                                f"Import: Unbekannte Rolle '{rolle_code}' für Branche '{unterbranche.name}'"
                            )

        db.session.commit()

        # Build success message
        messages = []
        if stats['hauptbranche_created']:
            messages.append(f"Hauptbranche '{hauptbranche.name}' angelegt")
        elif stats['hauptbranche_updated']:
            messages.append(f"Hauptbranche '{hauptbranche.name}' aktualisiert")

        if stats['unterbranchen_created'] > 0:
            messages.append(f"{stats['unterbranchen_created']} Unterbranchen angelegt")
        if stats['unterbranchen_updated'] > 0:
            messages.append(f"{stats['unterbranchen_updated']} Unterbranchen aktualisiert")
        if stats['rollen_zuordnungen'] > 0:
            messages.append(f"{stats['rollen_zuordnungen']} Rollen-Zuordnungen")
        if stats['rollen_created'] > 0:
            messages.append(f"{stats['rollen_created']} neue Rollen")

        flash('Import erfolgreich: ' + ', '.join(messages), 'success')
        return redirect(url_for('admin.branchen', hauptbranche=hauptbranche.id))

    except json.JSONDecodeError as e:
        flash(f'JSON-Fehler: {str(e)}', 'danger')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Branchen-Import Fehler: {e}")
        flash(f'Import-Fehler: {str(e)}', 'danger')

    return redirect(url_for('admin.branchen'))


def _clean_icon(icon_str):
    """Remove 'fas fa-' or 'ti ti-' prefix from icon string."""
    if not icon_str:
        return 'category'
    icon_str = icon_str.strip()
    # Remove FontAwesome prefixes
    for prefix in ['fas fa-', 'far fa-', 'fab fa-', 'fa-']:
        if icon_str.startswith(prefix):
            return icon_str[len(prefix):]
    # Remove Tabler prefixes
    if icon_str.startswith('ti ti-'):
        return icon_str[6:]
    if icon_str.startswith('ti-'):
        return icon_str[3:]
    return icon_str


def _generate_slug(name, parent_slug=None):
    """Generate a URL-safe slug from a name."""
    slug = name.lower().strip()
    # German umlauts
    replacements = [
        ('ä', 'ae'), ('ö', 'oe'), ('ü', 'ue'), ('ß', 'ss'),
        (' ', '-'), ('/', '-'), ('&', '-und-')
    ]
    for old, new in replacements:
        slug = slug.replace(old, new)
    # Remove other special chars
    slug = ''.join(c for c in slug if c.isalnum() or c == '-')
    # Remove multiple dashes
    while '--' in slug:
        slug = slug.replace('--', '-')
    slug = slug.strip('-')

    if parent_slug:
        return f"{parent_slug}-{slug}"
    return slug


# ============================================================================
# BranchenRollen Management (Rollen-Katalog)
# ============================================================================

@admin_bp.route('/branchenrollen', methods=['GET', 'POST'])
@login_required
@admin_required
def branchenrollen():
    """Manage BranchenRollen (Industry Roles).

    Rollen wie HERSTELLER, EINZELHANDEL_ONLINE, etc. die Kunden
    pro Branche zugewiesen werden können.
    """
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create':
            code = request.form.get('code', '').strip().upper()
            name = request.form.get('name', '').strip()
            icon = request.form.get('icon', 'tag').strip()
            beschreibung = request.form.get('beschreibung', '').strip()
            sortierung = request.form.get('sortierung', 0, type=int)

            if code and name:
                existing = BranchenRolle.query.filter_by(code=code).first()
                if existing:
                    flash(f'BranchenRolle mit Code "{code}" existiert bereits', 'warning')
                else:
                    rolle = BranchenRolle(
                        code=code,
                        name=name,
                        icon=icon,
                        beschreibung=beschreibung,
                        sortierung=sortierung,
                        aktiv=True
                    )
                    db.session.add(rolle)
                    db.session.commit()
                    flash(f'BranchenRolle "{name}" angelegt', 'success')
            else:
                flash('Code und Name sind erforderlich', 'warning')

        elif action == 'update':
            rolle_id = request.form.get('id', type=int)
            rolle = BranchenRolle.query.get(rolle_id)
            if rolle:
                # Code darf nicht geändert werden wenn bereits verwendet
                new_code = request.form.get('code', rolle.code).strip().upper()
                if new_code != rolle.code:
                    existing = BranchenRolle.query.filter_by(code=new_code).first()
                    if existing:
                        flash(f'Code "{new_code}" wird bereits verwendet', 'warning')
                        return redirect(url_for('admin.branchenrollen'))
                    rolle.code = new_code

                rolle.name = request.form.get('name', rolle.name).strip()
                rolle.icon = request.form.get('icon', rolle.icon).strip()
                rolle.beschreibung = request.form.get('beschreibung', rolle.beschreibung).strip()
                rolle.sortierung = request.form.get('sortierung', rolle.sortierung, type=int)
                rolle.aktiv = request.form.get('aktiv') == 'on'
                db.session.commit()
                flash(f'BranchenRolle "{rolle.name}" aktualisiert', 'success')

        elif action == 'delete':
            rolle_id = request.form.get('id', type=int)
            rolle = BranchenRolle.query.get(rolle_id)
            if rolle:
                # Prüfen ob verwendet (in Zulässigkeitsmatrix oder Kundenzuordnungen)
                zulaessig_count = len(rolle.zulaessig_in_branchen)
                kunden_count = len(rolle.kunden_mit_rolle)

                if zulaessig_count > 0 or kunden_count > 0:
                    flash(
                        f'BranchenRolle "{rolle.name}" wird verwendet '
                        f'({zulaessig_count} Branchen, {kunden_count} Kundenzuordnungen) '
                        'und kann nicht gelöscht werden',
                        'warning'
                    )
                else:
                    name = rolle.name
                    db.session.delete(rolle)
                    db.session.commit()
                    flash(f'BranchenRolle "{name}" gelöscht', 'success')

        return redirect(url_for('admin.branchenrollen'))

    rollen_list = BranchenRolle.query.order_by(BranchenRolle.sortierung, BranchenRolle.name).all()
    return render_template('administration/branchenrollen.html', rollen=rollen_list)


@admin_bp.route('/branchenrollen/reorder', methods=['POST'])
@login_required
@admin_required
def branchenrollen_reorder():
    """Update sort order for BranchenRollen via AJAX."""
    data = request.get_json()

    if not data or 'order' not in data:
        return jsonify({'success': False, 'message': 'Keine Sortierreihenfolge übergeben'}), 400

    order = data['order']  # Liste von IDs in neuer Reihenfolge

    try:
        for index, rolle_id in enumerate(order):
            rolle = BranchenRolle.query.get(int(rolle_id))
            if rolle:
                rolle.sortierung = (index + 1) * 10  # 10, 20, 30, ...

        db.session.commit()
        return jsonify({'success': True, 'message': 'Sortierung gespeichert'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================================
# Verbände Management
# ============================================================================

def _handle_verband_logo_upload(verband_id):
    """Handle logo upload for a Verband, creating a thumbnail.

    Args:
        verband_id: ID of the Verband

    Returns:
        Filename of saved thumbnail or None
    """
    if 'logo' not in request.files:
        return None

    file = request.files['logo']
    if not file or not file.filename:
        return None

    if not allowed_file(file.filename):
        flash('Ungültiges Dateiformat. Erlaubt: PNG, JPG, JPEG, GIF, SVG', 'warning')
        return None

    # Ensure upload directory exists
    upload_dir = os.path.join(current_app.static_folder, 'uploads', 'verbaende')
    os.makedirs(upload_dir, exist_ok=True)

    # Generate filename with timestamp
    filename = secure_filename(file.filename)
    name, ext = os.path.splitext(filename)
    thumb_filename = f"verband_{verband_id}_{int(datetime.now().timestamp())}{ext}"
    save_path = os.path.join(upload_dir, thumb_filename)

    # Create thumbnail
    if create_thumbnail(file, save_path):
        return thumb_filename
    else:
        flash('Fehler beim Erstellen des Thumbnails', 'danger')
        return None


@admin_bp.route('/verbaende', methods=['GET', 'POST'])
@login_required
@admin_required
def verbaende():
    """Manage Verbände (Associations)."""
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create':
            name = request.form.get('name', '').strip()
            kuerzel = request.form.get('kuerzel', '').strip()
            website_url = request.form.get('website_url', '').strip()
            logo_url = request.form.get('logo_url', '').strip()

            if name:
                existing = Verband.query.filter_by(name=name).first()
                if existing:
                    flash(f'Verband "{name}" existiert bereits', 'warning')
                else:
                    verband = Verband(
                        name=name,
                        kuerzel=kuerzel or None,
                        website_url=website_url or None,
                        logo_url=logo_url or None,
                        aktiv=True
                    )
                    db.session.add(verband)
                    db.session.commit()

                    # Handle logo upload after we have an ID
                    thumb_filename = _handle_verband_logo_upload(verband.id)
                    if thumb_filename:
                        verband.logo_thumb = thumb_filename
                        db.session.commit()

                    flash(f'Verband "{name}" angelegt', 'success')

        elif action == 'update':
            verband_id = request.form.get('id', type=int)
            verband = Verband.query.get(verband_id)
            if verband:
                verband.name = request.form.get('name', verband.name).strip()
                verband.kuerzel = request.form.get('kuerzel', '').strip() or None
                verband.website_url = request.form.get('website_url', '').strip() or None
                verband.logo_url = request.form.get('logo_url', '').strip() or None
                verband.aktiv = request.form.get('aktiv') == 'on'

                # Handle logo upload
                thumb_filename = _handle_verband_logo_upload(verband.id)
                if thumb_filename:
                    # Delete old thumbnail if exists
                    if verband.logo_thumb:
                        old_path = os.path.join(
                            current_app.static_folder, 'uploads', 'verbaende', verband.logo_thumb
                        )
                        if os.path.exists(old_path):
                            os.remove(old_path)
                    verband.logo_thumb = thumb_filename

                # Handle logo deletion
                if request.form.get('delete_logo') == 'on':
                    if verband.logo_thumb:
                        old_path = os.path.join(
                            current_app.static_folder, 'uploads', 'verbaende', verband.logo_thumb
                        )
                        if os.path.exists(old_path):
                            os.remove(old_path)
                        verband.logo_thumb = None

                db.session.commit()
                flash(f'Verband "{verband.name}" aktualisiert', 'success')

        elif action == 'delete':
            verband_id = request.form.get('id', type=int)
            verband = Verband.query.get(verband_id)
            if verband:
                # Check if used
                if verband.kunden:
                    flash(f'Verband "{verband.name}" wird von {len(verband.kunden)} Kunden verwendet und kann nicht gelöscht werden', 'warning')
                else:
                    # Delete logo file if exists
                    if verband.logo_thumb:
                        logo_path = os.path.join(
                            current_app.static_folder, 'uploads', 'verbaende', verband.logo_thumb
                        )
                        if os.path.exists(logo_path):
                            os.remove(logo_path)

                    name = verband.name
                    db.session.delete(verband)
                    db.session.commit()
                    flash(f'Verband "{name}" gelöscht', 'success')

        return redirect(url_for('admin.verbaende'))

    verbaende_list = Verband.query.order_by(Verband.name).all()
    return render_template('administration/verbaende.html', verbaende=verbaende_list)


# ============================================================================
# Hilfetexte Management
# ============================================================================

@admin_bp.route('/hilfetexte', methods=['GET', 'POST'])
@login_required
@mitarbeiter_required
def hilfetexte():
    """Manage help texts for UI components."""
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create':
            schluessel = request.form.get('schluessel', '').strip()
            titel = request.form.get('titel', '').strip()
            inhalt_markdown = request.form.get('inhalt_markdown', '').strip()

            if schluessel and titel:
                existing = HelpText.query.filter_by(schluessel=schluessel).first()
                if existing:
                    flash(f'Hilfetext mit Schlüssel "{schluessel}" existiert bereits', 'warning')
                else:
                    help_text = HelpText(
                        schluessel=schluessel,
                        titel=titel,
                        inhalt_markdown=inhalt_markdown,
                        aktiv=True,
                        updated_by_id=current_user.id
                    )
                    db.session.add(help_text)
                    db.session.commit()
                    flash(f'Hilfetext "{titel}" angelegt', 'success')
            else:
                flash('Schlüssel und Titel sind Pflichtfelder', 'warning')

        elif action == 'update':
            help_id = request.form.get('id', type=int)
            help_text = HelpText.query.get(help_id)
            if help_text:
                # Check if new schluessel conflicts with existing
                new_schluessel = request.form.get('schluessel', '').strip()
                if new_schluessel != help_text.schluessel:
                    existing = HelpText.query.filter_by(schluessel=new_schluessel).first()
                    if existing:
                        flash(f'Schlüssel "{new_schluessel}" wird bereits verwendet', 'warning')
                        return redirect(url_for('admin.hilfetexte'))

                help_text.schluessel = new_schluessel
                help_text.titel = request.form.get('titel', help_text.titel).strip()
                help_text.inhalt_markdown = request.form.get('inhalt_markdown', '').strip()
                help_text.aktiv = request.form.get('aktiv') == 'on'
                help_text.updated_by_id = current_user.id
                db.session.commit()
                flash(f'Hilfetext "{help_text.titel}" aktualisiert', 'success')

        elif action == 'delete':
            # Only admins can delete
            if current_user.rolle != 'admin':
                flash('Nur Administratoren können Hilfetexte löschen', 'danger')
                return redirect(url_for('admin.hilfetexte'))

            help_id = request.form.get('id', type=int)
            help_text = HelpText.query.get(help_id)
            if help_text:
                titel = help_text.titel
                db.session.delete(help_text)
                db.session.commit()
                flash(f'Hilfetext "{titel}" gelöscht', 'success')

        return redirect(url_for('admin.hilfetexte'))

    hilfetexte_list = HelpText.query.order_by(HelpText.schluessel).all()
    return render_template('administration/hilfetexte.html', hilfetexte=hilfetexte_list)


# ============================================================================
# E-Mail Templates Management
# ============================================================================

@admin_bp.route('/email-templates')
@login_required
@admin_required
def email_templates():
    """List all email templates for management."""
    from app.models import EmailTemplate

    templates = EmailTemplate.query.order_by(EmailTemplate.name).all()
    return render_template(
        'administration/email_templates.html',
        templates=templates
    )


@admin_bp.route('/email-templates/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def email_template_edit(id):
    """Edit an email template."""
    from app.models import EmailTemplate
    from app.services import log_mittel

    template = EmailTemplate.query.get_or_404(id)

    if request.method == 'POST':
        template.name = request.form.get('name', template.name).strip()
        template.beschreibung = request.form.get('beschreibung', '').strip() or None
        template.betreff = request.form.get('betreff', template.betreff).strip()
        template.body_html = request.form.get('body_html', template.body_html)
        template.body_text = request.form.get('body_text', '').strip() or None
        template.aktiv = request.form.get('aktiv') == 'on'

        db.session.commit()

        log_mittel(
            modul='system',
            aktion='email_template_bearbeitet',
            details=f'E-Mail-Template "{template.schluessel}" bearbeitet',
            entity_type='EmailTemplate',
            entity_id=template.id
        )
        db.session.commit()

        flash(f'Template "{template.name}" gespeichert', 'success')
        return redirect(url_for('admin.email_templates'))

    # GET request
    # List of available placeholders for help text
    placeholders = [
        ('{{ firmenname }}', 'Firmenname des Kunden'),
        ('{{ link }}', 'Aktions-Link (Magic-Link, Passwort-Link, etc.)'),
        ('{{ fragebogen_titel }}', 'Titel des Fragebogens'),
        ('{{ briefanrede }}', 'Automatische Anrede (basierend auf Kundenstil)'),
        ('{{ briefanrede_foermlich }}', 'Formelle Anrede (Sehr geehrte/r...)'),
        ('{{ briefanrede_locker }}', 'Lockere Anrede (Hallo/Liebe/r...)'),
        ('{{ email }}', 'E-Mail-Adresse des Empfängers'),
        ('{{ vorname }}', 'Vorname des Empfängers'),
        ('{{ nachname }}', 'Nachname des Empfängers'),
        ('{{ portal_name }}', 'Portal-Name aus Branding'),
        ('{{ primary_color }}', 'Primärfarbe aus Branding'),
        ('{{ secondary_color }}', 'Sekundärfarbe aus Branding'),
        ('{{ logo_url }}', 'Logo-URL aus Branding'),
        ('{{ footer | safe }}', 'Kunden- oder System-Footer (HTML)'),
        ('{{ copyright_text }}', 'Copyright-Text aus Branding'),
    ]

    # Get all users for test email dropdown
    all_users = User.query.filter_by(aktiv=True).order_by(User.nachname, User.vorname).all()

    return render_template(
        'administration/email_template_form.html',
        template=template,
        placeholders=placeholders,
        all_users=all_users
    )


@admin_bp.route('/email-templates/<int:id>/preview')
@login_required
@admin_required
def email_template_preview(id):
    """Preview an email template with sample or real customer data."""
    from app.models import EmailTemplate
    from app.services import get_email_template_service

    template = EmailTemplate.query.get_or_404(id)
    template_service = get_email_template_service()

    # Optional: Kunde für echte Daten auswählen
    kunde_id = request.args.get('kunde_id', type=int)
    kunde = Kunde.query.get(kunde_id) if kunde_id else None

    # Alle aktiven Kunden für Dropdown laden
    kunden = Kunde.query.filter_by(aktiv=True).order_by(Kunde.firmierung).all()

    # Context mit Kundendaten oder Beispieldaten
    sample_context = {}
    if kunde:
        sample_context = {
            'firmenname': kunde.firmierung or 'N/A',
            'email': kunde.email or (kunde.user.email if kunde.user else 'N/A'),
            'vorname': kunde.user.vorname if kunde.user else 'Max',
            'nachname': kunde.user.nachname if kunde.user else 'Mustermann',
            # Briefanrede aus Kunde-Properties
            'briefanrede': kunde.briefanrede,
            'briefanrede_foermlich': kunde.briefanrede_foermlich,
            'briefanrede_locker': kunde.briefanrede_locker,
        }

    try:
        rendered = template_service.preview(template.schluessel, sample_context)
        return render_template(
            'administration/email_template_preview.html',
            template=template,
            rendered=rendered,
            kunden=kunden,
            kunde=kunde
        )
    except Exception as e:
        flash(f'Fehler bei der Vorschau: {str(e)}', 'danger')
        return redirect(url_for('admin.email_template_edit', id=id))


@admin_bp.route('/email-templates/<int:id>/send-test', methods=['POST'])
@login_required
@admin_required
def email_template_send_test(id):
    """Send a test email using this template.

    Supports two modes:
    1. Preview mode (new): Uses kunde_id + recipient (kunde/self)
    2. Legacy mode: Uses test_user_id (for backward compatibility)
    """
    from app.models import EmailTemplate
    from app.services import get_brevo_service

    template = EmailTemplate.query.get_or_404(id)
    brevo_service = get_brevo_service()

    # Check for new preview mode (kunde_id)
    kunde_id = request.form.get('kunde_id', type=int)
    recipient = request.form.get('recipient', 'self')

    if kunde_id:
        # New preview mode: Use real customer data
        kunde = Kunde.query.get_or_404(kunde_id)

        # Determine recipient
        if recipient == 'kunde' and kunde.email:
            to_email = kunde.email
            to_name = kunde.firmierung
        else:
            to_email = current_user.email
            to_name = current_user.full_name

        # Use real customer data for placeholders
        context = {
            'firmenname': kunde.firmierung,
            'link': 'https://example.com/action',
            'fragebogen_titel': 'Beispiel-Fragebogen',
            'email': kunde.email or '',
            'vorname': kunde.user.vorname if kunde.user else '',
            'nachname': kunde.user.nachname if kunde.user else '',
        }

        redirect_url = url_for('admin.email_template_preview', id=id, kunde_id=kunde_id)

    else:
        # Legacy mode: Use test_user_id
        test_user_id = request.form.get('test_user_id', type=int)
        if not test_user_id:
            flash('Bitte einen Empfänger auswählen', 'warning')
            return redirect(url_for('admin.email_template_preview', id=id))

        user = User.query.get(test_user_id)
        if not user:
            flash('Benutzer nicht gefunden', 'danger')
            return redirect(url_for('admin.email_template_preview', id=id))

        to_email = user.email
        to_name = user.full_name

        # Sample context for test
        context = {
            'firmenname': 'Musterfirma GmbH',
            'link': 'https://example.com/action',
            'fragebogen_titel': 'Beispiel-Fragebogen',
            'email': user.email,
            'vorname': user.vorname,
            'nachname': user.nachname,
        }

        redirect_url = url_for('admin.email_template_preview', id=id)

    result = brevo_service.send_with_template(
        template_schluessel=template.schluessel,
        to_email=to_email,
        to_name=to_name,
        context=context
    )

    if result.success:
        flash(f'Test-E-Mail mit Template "{template.name}" an {to_email} gesendet', 'success')
    else:
        flash(f'Fehler: {result.error}', 'danger')

    return redirect(redirect_url)


# ============================================================================
# Audit-Log
# ============================================================================

@admin_bp.route('/logs')
@login_required
@admin_required
def logs():
    """View audit logs with filtering and pagination."""
    # Get filter parameters
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Filters
    modul_filter = request.args.get('modul', '')
    user_filter = request.args.get('user', type=int)
    wichtigkeit_filter = request.args.getlist('wichtigkeit')  # Can be multiple
    datum_von = request.args.get('datum_von', '')
    datum_bis = request.args.get('datum_bis', '')

    # Build query
    query = AuditLog.query

    if modul_filter:
        modul_obj = Modul.query.filter_by(code=modul_filter).first()
        if modul_obj:
            query = query.filter(AuditLog.modul_id == modul_obj.id)

    if user_filter:
        query = query.filter(AuditLog.user_id == user_filter)

    if wichtigkeit_filter:
        query = query.filter(AuditLog.wichtigkeit.in_(wichtigkeit_filter))

    if datum_von:
        try:
            von_date = datetime.strptime(datum_von, '%Y-%m-%d')
            query = query.filter(AuditLog.timestamp >= von_date)
        except ValueError:
            pass

    if datum_bis:
        try:
            bis_date = datetime.strptime(datum_bis, '%Y-%m-%d')
            # Add one day to include the entire day
            from datetime import timedelta
            bis_date = bis_date + timedelta(days=1)
            query = query.filter(AuditLog.timestamp < bis_date)
        except ValueError:
            pass

    # Order by timestamp descending (newest first)
    query = query.order_by(AuditLog.timestamp.desc())

    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    logs_list = pagination.items

    # Get all modules and users for filter dropdowns
    alle_module = Modul.query.order_by(Modul.name).all()
    alle_user = User.query.order_by(User.nachname, User.vorname).all()

    return render_template(
        'administration/logs.html',
        logs=logs_list,
        pagination=pagination,
        alle_module=alle_module,
        alle_user=alle_user,
        # Current filter values for form
        filter_modul=modul_filter,
        filter_user=user_filter,
        filter_wichtigkeit=wichtigkeit_filter,
        filter_datum_von=datum_von,
        filter_datum_bis=datum_bis
    )


@admin_bp.route('/logs/export')
@login_required
@admin_required
def logs_export():
    """Export audit logs as JSON or CSV."""
    export_format = request.args.get('format', 'json')

    # Apply same filters as logs view
    modul_filter = request.args.get('modul', '')
    user_filter = request.args.get('user', type=int)
    wichtigkeit_filter = request.args.getlist('wichtigkeit')
    datum_von = request.args.get('datum_von', '')
    datum_bis = request.args.get('datum_bis', '')

    query = AuditLog.query

    if modul_filter:
        modul_obj = Modul.query.filter_by(code=modul_filter).first()
        if modul_obj:
            query = query.filter(AuditLog.modul_id == modul_obj.id)

    if user_filter:
        query = query.filter(AuditLog.user_id == user_filter)

    if wichtigkeit_filter:
        query = query.filter(AuditLog.wichtigkeit.in_(wichtigkeit_filter))

    if datum_von:
        try:
            von_date = datetime.strptime(datum_von, '%Y-%m-%d')
            query = query.filter(AuditLog.timestamp >= von_date)
        except ValueError:
            pass

    if datum_bis:
        try:
            bis_date = datetime.strptime(datum_bis, '%Y-%m-%d')
            from datetime import timedelta
            bis_date = bis_date + timedelta(days=1)
            query = query.filter(AuditLog.timestamp < bis_date)
        except ValueError:
            pass

    logs_list = query.order_by(AuditLog.timestamp.desc()).limit(10000).all()

    if export_format == 'csv':
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Zeitstempel', 'User', 'Modul', 'Aktion', 'Details', 'Wichtigkeit', 'Entity', 'IP'])

        for log in logs_list:
            writer.writerow([
                log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                log.user_display,
                log.modul.name if log.modul else '',
                log.aktion,
                log.details or '',
                log.wichtigkeit,
                f'{log.entity_type} #{log.entity_id}' if log.entity_type else '',
                log.ip_adresse or ''
            ])

        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=audit_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        return response

    else:
        # JSON export
        data = []
        for log in logs_list:
            data.append({
                'id': log.id,
                'timestamp': log.timestamp.isoformat(),
                'user_id': log.user_id,
                'user_display': log.user_display,
                'modul': log.modul.code if log.modul else None,
                'modul_name': log.modul.name if log.modul else None,
                'aktion': log.aktion,
                'details': log.details,
                'wichtigkeit': log.wichtigkeit,
                'entity_type': log.entity_type,
                'entity_id': log.entity_id,
                'ip_adresse': log.ip_adresse
            })

        response = make_response(json.dumps(data, ensure_ascii=False, indent=2))
        response.headers['Content-Type'] = 'application/json; charset=utf-8'
        response.headers['Content-Disposition'] = f'attachment; filename=audit_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        return response


# ============================================================================
# Module Management
# ============================================================================

@admin_bp.route('/module')
@login_required
@admin_required
def module():
    """Manage modules (activate/deactivate, role access)."""
    module_list = Modul.query.order_by(Modul.sort_order, Modul.name).all()
    alle_rollen = Rolle.query.order_by(Rolle.name).all()

    return render_template(
        'administration/module.html',
        module=module_list,
        alle_rollen=alle_rollen
    )


@admin_bp.route('/module/<int:id>/toggle', methods=['POST'])
@login_required
@admin_required
def module_toggle(id):
    """Toggle module active status."""
    from app.services import log_mittel

    modul = Modul.query.get_or_404(id)

    if modul.ist_basis:
        return jsonify({'success': False, 'error': 'Basismodule können nicht deaktiviert werden'}), 400

    modul.aktiv = not modul.aktiv
    db.session.commit()

    log_mittel(
        modul='system',
        aktion='modul_status_geaendert',
        details=f'Modul "{modul.name}" {"aktiviert" if modul.aktiv else "deaktiviert"}',
        entity_type='Modul',
        entity_id=modul.id
    )
    db.session.commit()

    return jsonify({'success': True, 'aktiv': modul.aktiv})


@admin_bp.route('/module/<int:id>/access', methods=['POST'])
@login_required
@admin_required
def module_access(id):
    """Update role access for a module."""
    modul = Modul.query.get_or_404(id)

    data = request.get_json()
    if not data or 'rollen' not in data:
        return jsonify({'success': False, 'error': 'Keine Rollen übergeben'}), 400

    rolle_ids = data['rollen']

    # Define external roles that cannot access internal modules (lowercase)
    EXTERNE_ROLLEN_NAMEN = ['kunde']

    try:
        # Validate: Internal modules cannot be assigned to external roles
        if modul.ist_intern:
            for rolle_id in rolle_ids:
                rolle = Rolle.query.get(rolle_id)
                if rolle and rolle.name.lower() in EXTERNE_ROLLEN_NAMEN:
                    return jsonify({
                        'success': False,
                        'error': f'Interne Module können nicht der Rolle "{rolle.name}" zugewiesen werden'
                    }), 400

        # Clear existing access
        ModulZugriff.query.filter_by(modul_id=modul.id).delete()

        # Add new access
        for rolle_id in rolle_ids:
            rolle = Rolle.query.get(rolle_id)
            if rolle:
                access = ModulZugriff(modul_id=modul.id, rolle_id=rolle_id)
                db.session.add(access)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Zugriffe aktualisiert'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/module/reorder', methods=['POST'])
@login_required
@admin_required
def module_reorder():
    """Update sort order for modules via AJAX."""
    data = request.get_json()

    if not data or 'order' not in data:
        return jsonify({'success': False, 'message': 'Keine Sortierreihenfolge übergeben'}), 400

    order = data['order']  # List of IDs in new order

    try:
        for index, modul_id in enumerate(order):
            modul = Modul.query.get(int(modul_id))
            if modul:
                modul.sort_order = (index + 1) * 10  # 10, 20, 30, ...

        db.session.commit()
        return jsonify({'success': True, 'message': 'Sortierung gespeichert'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/module/<int:id>/edit', methods=['POST'])
@login_required
@admin_required
def module_edit(id):
    """Edit module properties (beschreibung, icon, typ, color_hex)."""
    from app.services import log_mittel
    from app.models import ModulTyp

    modul = Modul.query.get_or_404(id)

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Keine Daten übergeben'}), 400

    try:
        changes = []

        # Update beschreibung
        if 'beschreibung' in data:
            new_beschreibung = data['beschreibung'].strip() if data['beschreibung'] else None
            if modul.beschreibung != new_beschreibung:
                changes.append(f"Beschreibung geändert")
                modul.beschreibung = new_beschreibung

        # Update icon
        if 'icon' in data:
            new_icon = data['icon'].strip() if data['icon'] else 'ti-apps'
            if modul.icon != new_icon:
                changes.append(f"Icon geändert zu {new_icon}")
                modul.icon = new_icon

        # Update typ
        if 'typ' in data:
            new_typ = data['typ'].strip() if data['typ'] else ModulTyp.BASIS.value
            # Validate typ
            valid_types = [t.value for t in ModulTyp]
            if new_typ in valid_types and modul.typ != new_typ:
                changes.append(f"Typ geändert zu {new_typ}")
                modul.typ = new_typ

        # Update color_hex
        if 'color_hex' in data:
            new_color = data['color_hex'].strip() if data['color_hex'] else '#6c757d'
            if modul.color_hex != new_color:
                changes.append(f"Farbe geändert zu {new_color}")
                modul.color_hex = new_color

        if changes:
            db.session.commit()

            log_mittel(
                modul='system',
                aktion='modul_bearbeitet',
                details=f'Modul "{modul.name}": {", ".join(changes)}',
                entity_type='Modul',
                entity_id=modul.id
            )
            db.session.commit()

        return jsonify({'success': True, 'message': 'Modul aktualisiert'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# LookupWert Management (Configurable Key-Value Pairs)
# ============================================================================

@admin_bp.route('/lookup-werte', methods=['GET', 'POST'])
@login_required
@admin_required
def lookup_werte():
    """Manage LookupWert entries (configurable key-value pairs).

    Provides CRUD operations for system configuration values like
    support ticket types, status values, etc.
    """
    from app.services import log_mittel

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'create':
            kategorie = request.form.get('kategorie', '').strip()
            schluessel = request.form.get('schluessel', '').strip().lower()
            wert = request.form.get('wert', '').strip()
            icon = request.form.get('icon', '').strip() or None
            farbe = request.form.get('farbe', '').strip() or None
            sortierung = request.form.get('sortierung', 0, type=int)

            if kategorie and schluessel and wert:
                existing = LookupWert.query.filter_by(
                    kategorie=kategorie,
                    schluessel=schluessel
                ).first()

                if existing:
                    flash(f'Eintrag "{kategorie}.{schluessel}" existiert bereits', 'warning')
                else:
                    lookup = LookupWert(
                        kategorie=kategorie,
                        schluessel=schluessel,
                        wert=wert,
                        icon=icon,
                        farbe=farbe,
                        sortierung=sortierung,
                        aktiv=True
                    )
                    db.session.add(lookup)
                    db.session.commit()

                    log_mittel(
                        modul='system',
                        aktion='lookup_erstellt',
                        details=f'LookupWert erstellt: {kategorie}.{schluessel}',
                        entity_type='LookupWert',
                        entity_id=lookup.id
                    )
                    db.session.commit()

                    flash(f'Eintrag "{kategorie}.{schluessel}" erstellt', 'success')
            else:
                flash('Kategorie, Schlüssel und Wert sind erforderlich', 'danger')

        elif action == 'update':
            lookup_id = request.form.get('id', type=int)
            lookup = LookupWert.query.get(lookup_id)

            if lookup:
                lookup.wert = request.form.get('wert', lookup.wert).strip()
                lookup.icon = request.form.get('icon', '').strip() or None
                lookup.farbe = request.form.get('farbe', '').strip() or None
                lookup.sortierung = request.form.get('sortierung', lookup.sortierung, type=int)
                lookup.aktiv = 'aktiv' in request.form

                db.session.commit()

                log_mittel(
                    modul='system',
                    aktion='lookup_bearbeitet',
                    details=f'LookupWert bearbeitet: {lookup.kategorie}.{lookup.schluessel}',
                    entity_type='LookupWert',
                    entity_id=lookup.id
                )
                db.session.commit()

                flash(f'Eintrag aktualisiert', 'success')
            else:
                flash('Eintrag nicht gefunden', 'danger')

        elif action == 'delete':
            lookup_id = request.form.get('id', type=int)
            lookup = LookupWert.query.get(lookup_id)

            if lookup:
                key = f"{lookup.kategorie}.{lookup.schluessel}"
                redirect_tab = lookup.kategorie  # Remember tab before delete
                db.session.delete(lookup)
                db.session.commit()

                log_mittel(
                    modul='system',
                    aktion='lookup_geloescht',
                    details=f'LookupWert gelöscht: {key}',
                    entity_type='LookupWert',
                    entity_id=lookup_id
                )
                db.session.commit()

                flash(f'Eintrag "{key}" gelöscht', 'success')
                return redirect(url_for('admin.lookup_werte', tab=redirect_tab))
            else:
                flash('Eintrag nicht gefunden', 'danger')

        # Redirect with tab parameter to stay on current category
        redirect_tab = request.form.get('redirect_tab', '')
        if redirect_tab:
            return redirect(url_for('admin.lookup_werte', tab=redirect_tab))
        return redirect(url_for('admin.lookup_werte'))

    # GET: Load all entries grouped by category
    kategorien = LookupWert.get_kategorien()
    entries_by_kategorie = {}

    for kategorie in kategorien:
        entries_by_kategorie[kategorie] = LookupWert.query.filter_by(
            kategorie=kategorie
        ).order_by(LookupWert.sortierung, LookupWert.schluessel).all()

    # All modules for assignment
    module = Modul.query.order_by(Modul.name).all()

    return render_template(
        'administration/lookup_werte.html',
        kategorien=kategorien,
        entries_by_kategorie=entries_by_kategorie,
        module=module,
        admin_tab='stammdaten'
    )


@admin_bp.route('/lookup-werte/reorder', methods=['POST'])
@login_required
@admin_required
def lookup_werte_reorder():
    """Update sort order for LookupWerte via AJAX."""
    data = request.get_json()

    if not data or 'order' not in data:
        return jsonify({'success': False, 'message': 'Keine Sortierreihenfolge übergeben'}), 400

    order = data['order']  # List of IDs in new order

    try:
        for index, lookup_id in enumerate(order):
            lookup = LookupWert.query.get(int(lookup_id))
            if lookup:
                lookup.sortierung = (index + 1) * 10  # 10, 20, 30, ...

        db.session.commit()
        return jsonify({'success': True, 'message': 'Sortierung gespeichert'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================================================
# PRD-009: Produktdaten Administration
# ============================================================================

@admin_bp.route('/produkte')
@login_required
@admin_required
def produkte():
    """Produkte list view with search."""
    search = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = 25

    query = Produkt.query

    if search:
        pattern = f'%{search}%'
        query = query.filter(
            db.or_(
                Produkt.ean.ilike(pattern),
                Produkt.artikelnummer_lieferant.ilike(pattern),
                Produkt.artikelbezeichnung.ilike(pattern),
                Produkt.markenname.ilike(pattern),
            )
        )

    produkte = query.order_by(Produkt.artikelbezeichnung).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template(
        'administration/produkte.html',
        produkte=produkte,
        search=search,
        admin_tab='stammdaten'
    )


@admin_bp.route('/produkte/form', methods=['GET', 'POST'])
@admin_bp.route('/produkte/form/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def produkt_form(id=None):
    """Create or edit a product."""
    from decimal import Decimal, InvalidOperation
    from datetime import datetime

    # Load existing product or create new one
    if id:
        produkt = Produkt.query.get_or_404(id)
    else:
        produkt = Produkt()

    if request.method == 'POST':
        try:
            # Identifikation (EAN nur bei Neuanlage änderbar)
            if not id:
                produkt.ean = request.form.get('ean', '').strip()
            produkt.artikelnummer_lieferant = request.form.get('artikelnummer_lieferant', '').strip() or None
            produkt.artikelnummer_hersteller = request.form.get('artikelnummer_hersteller', '').strip() or None

            # Grunddaten
            produkt.artikelbezeichnung = request.form.get('artikelbezeichnung', '').strip()
            produkt.kurzbezeichnung = request.form.get('kurzbezeichnung', '').strip() or None
            produkt.status = request.form.get('status', 'entwurf')

            # Marke & Hersteller
            produkt.markenname = request.form.get('markenname', '').strip() or None
            produkt.hersteller_name = request.form.get('hersteller_name', '').strip() or None
            produkt.serienname = request.form.get('serienname', '').strip() or None

            # Preise (Decimal-Felder)
            def parse_decimal(value, precision=2):
                if not value or not value.strip():
                    return None
                try:
                    return Decimal(value.strip()).quantize(Decimal(10) ** -precision)
                except InvalidOperation:
                    return None

            produkt.uvpe = parse_decimal(request.form.get('uvpe'), 2)
            produkt.ekp_netto = parse_decimal(request.form.get('ekp_netto'), 4)
            produkt.mwst_satz = parse_decimal(request.form.get('mwst_satz'), 2)
            produkt.waehrung = request.form.get('waehrung', 'EUR')

            # Logistik (Decimal-Felder)
            produkt.stueck_laenge_cm = parse_decimal(request.form.get('stueck_laenge_cm'), 3)
            produkt.stueck_breite_cm = parse_decimal(request.form.get('stueck_breite_cm'), 3)
            produkt.stueck_hoehe_cm = parse_decimal(request.form.get('stueck_hoehe_cm'), 3)
            produkt.stueck_gewicht_kg = parse_decimal(request.form.get('stueck_gewicht_kg'), 3)

            # Klassifikation
            produkt.zolltarif_nr = request.form.get('zolltarif_nr', '').strip() or None
            produkt.ursprungsland = request.form.get('ursprungsland', '').strip().upper() or None

            # Termine (Date-Felder)
            def parse_date(value):
                if not value or not value.strip():
                    return None
                try:
                    return datetime.strptime(value.strip(), '%Y-%m-%d').date()
                except ValueError:
                    return None

            produkt.lieferbar_ab = parse_date(request.form.get('lieferbar_ab'))
            produkt.lieferbar_bis = parse_date(request.form.get('lieferbar_bis'))
            produkt.erste_auslieferung = parse_date(request.form.get('erste_auslieferung'))

            # Beschreibungstexte
            produkt.b2b_kurztext = request.form.get('b2b_kurztext', '').strip() or None
            produkt.b2c_text = request.form.get('b2c_text', '').strip() or None

            # Meta
            if not id:
                produkt.created_by_id = current_user.id

            # Validate required fields
            if not produkt.ean:
                flash('EAN/GTIN ist erforderlich.', 'danger')
                return render_template('administration/produkt_form.html', produkt=produkt, admin_tab='stammdaten')

            if not produkt.artikelbezeichnung:
                flash('Artikelbezeichnung ist erforderlich.', 'danger')
                return render_template('administration/produkt_form.html', produkt=produkt, admin_tab='stammdaten')

            # Check EAN uniqueness for new products
            if not id:
                existing = Produkt.get_by_ean(produkt.ean)
                if existing:
                    flash(f'Ein Produkt mit EAN {produkt.ean} existiert bereits.', 'danger')
                    return render_template('administration/produkt_form.html', produkt=produkt, admin_tab='stammdaten')

            # Save
            db.session.add(produkt)
            db.session.commit()

            flash(f'Produkt "{produkt.artikelbezeichnung[:50]}" wurde gespeichert.', 'success')
            return redirect(url_for('admin.produkte'))

        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Speichern: {str(e)}', 'danger')

    return render_template(
        'administration/produkt_form.html',
        produkt=produkt,
        admin_tab='stammdaten'
    )


@admin_bp.route('/produkte/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def produkt_delete(id):
    """Delete a product."""
    produkt = Produkt.query.get_or_404(id)
    bezeichnung = produkt.artikelbezeichnung[:50]

    try:
        db.session.delete(produkt)
        db.session.commit()
        flash(f'Produkt "{bezeichnung}" wurde gelöscht.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Löschen: {str(e)}', 'danger')

    return redirect(url_for('admin.produkte'))


@admin_bp.route('/produkt-lookup')
@login_required
@admin_required
def produkt_lookup():
    """Produkt-Codelisten overview."""
    # Get all categories with counts
    kategorien_counts = ProduktLookup.count_by_kategorie()

    # Get selected category
    kategorie = request.args.get('kategorie', '')

    # Get entries for selected category
    eintraege = []
    if kategorie:
        eintraege = ProduktLookup.get_by_kategorie(kategorie, nur_aktive=False)

    return render_template(
        'administration/produkt_lookup.html',
        kategorien_counts=kategorien_counts,
        kategorie=kategorie,
        eintraege=eintraege,
        admin_tab='stammdaten'
    )


@admin_bp.route('/attributgruppen')
@login_required
@admin_required
def attributgruppen():
    """Attributgruppen (5-Ebenen Produktklassifikation) overview."""
    # Get all Ebene 1 categories
    hauptkategorien = Attributgruppe.get_hauptkategorien()

    # Get selected Ebene 1
    ebene_1 = request.args.get('ebene_1', '')
    search = request.args.get('q', '')

    eintraege = []
    if search:
        eintraege = Attributgruppe.suche(search, limit=100)
    elif ebene_1:
        eintraege = Attributgruppe.get_by_ebene_1(ebene_1)

    return render_template(
        'administration/attributgruppen.html',
        hauptkategorien=hauptkategorien,
        ebene_1=ebene_1,
        search=search,
        eintraege=eintraege,
        admin_tab='stammdaten'
    )


@admin_bp.route('/eigenschaft-definitionen')
@login_required
@admin_required
def eigenschaft_definitionen():
    """EigenschaftDefinitionen (Produkt-Eigenschaften) overview."""
    # Get all groups
    gruppen = EigenschaftDefinition.get_gruppen()

    # Get selected group
    gruppe = request.args.get('gruppe', '')

    eintraege = []
    if gruppe:
        eintraege = EigenschaftDefinition.get_by_gruppe(gruppe, nur_aktive=False)
    else:
        # Show all if no group selected
        eintraege = EigenschaftDefinition.query.order_by(
            EigenschaftDefinition.gruppe,
            EigenschaftDefinition.sortierung
        ).all()

    return render_template(
        'administration/eigenschaft_definitionen.html',
        gruppen=gruppen,
        gruppe=gruppe,
        eintraege=eintraege,
        admin_tab='stammdaten'
    )


# ============================================================================
# API: PRD Content (für DEV-Button Modal)
# ============================================================================

@admin_bp.route('/api/prd-content')
@login_required
@admin_required
def prd_content():
    """Serve PRD markdown content as HTML for modal display.

    Security: Only allows paths starting with 'docs/prd/'.
    """
    import markdown
    import os

    path = request.args.get('path', '')

    # Security check: Only allow docs/prd/ paths
    if not path.startswith('docs/prd/'):
        return '<div class="alert alert-danger">Ungültiger Pfad</div>', 400

    # Prevent directory traversal
    if '..' in path:
        return '<div class="alert alert-danger">Ungültiger Pfad</div>', 400

    # Construct full path
    base_path = os.path.dirname(current_app.root_path)
    full_path = os.path.join(base_path, path)

    # Check if file exists
    if not os.path.isfile(full_path):
        return f'<div class="alert alert-warning"><i class="ti ti-file-off me-2"></i>PRD-Datei nicht gefunden: <code>{path}</code></div>', 404

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Convert markdown to HTML
        md = markdown.Markdown(extensions=[
            'tables',
            'fenced_code',
            'codehilite',
            'toc',
            'nl2br'
        ])
        html = md.convert(content)

        # Wrap in styled container
        styled_html = f'''
        <div class="prd-content">
            <style>
                .prd-content h1 {{ font-size: 1.75rem; border-bottom: 2px solid #dee2e6; padding-bottom: 0.5rem; margin-bottom: 1rem; }}
                .prd-content h2 {{ font-size: 1.5rem; border-bottom: 1px solid #dee2e6; padding-bottom: 0.25rem; margin-top: 1.5rem; }}
                .prd-content h3 {{ font-size: 1.25rem; margin-top: 1.25rem; }}
                .prd-content h4 {{ font-size: 1.1rem; margin-top: 1rem; }}
                .prd-content table {{ width: 100%; margin: 1rem 0; }}
                .prd-content table th, .prd-content table td {{
                    padding: 0.5rem;
                    border: 1px solid #dee2e6;
                    text-align: left;
                }}
                .prd-content table th {{ background-color: #f8f9fa; font-weight: 600; }}
                .prd-content table tr:nth-child(even) {{ background-color: #f8f9fa; }}
                .prd-content code {{
                    background-color: #f1f3f5;
                    padding: 0.125rem 0.25rem;
                    border-radius: 0.25rem;
                    font-size: 0.875rem;
                }}
                .prd-content pre {{
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                    padding: 1rem;
                    border-radius: 0.5rem;
                    overflow-x: auto;
                }}
                .prd-content pre code {{
                    background-color: transparent;
                    padding: 0;
                    color: inherit;
                }}
                .prd-content ul, .prd-content ol {{ padding-left: 1.5rem; }}
                .prd-content li {{ margin-bottom: 0.25rem; }}
                .prd-content blockquote {{
                    border-left: 4px solid #6c757d;
                    padding-left: 1rem;
                    margin-left: 0;
                    color: #6c757d;
                }}
            </style>
            {html}
        </div>
        '''

        return styled_html

    except Exception as e:
        current_app.logger.error(f"Error reading PRD file {path}: {e}")
        return f'<div class="alert alert-danger"><i class="ti ti-alert-circle me-2"></i>Fehler beim Laden: {str(e)}</div>', 500


# ============================================================================
# Platzhalter-Routes für neue Stammdaten-Kacheln
# ============================================================================

@admin_bp.route('/rollen')
@login_required
@admin_required
def rollen():
    """Benutzerrollen verwalten (Platzhalter)."""
    rollen_liste = Rolle.query.order_by(Rolle.name).all()

    return render_template(
        'administration/rollen.html',
        rollen=rollen_liste,
        admin_tab='stammdaten'
    )


@admin_bp.route('/lieferanten')
@login_required
@admin_required
def lieferanten():
    """Lieferanten-Stammdaten verwalten mit Filter und Suche."""
    # Filter-Parameter aus Request
    branche_id = request.args.get('branche', type=int)
    status = request.args.get('status', '')
    suchbegriff = request.args.get('q', '').strip()

    # HANDEL-Unterbranchen für Filter-Dropdown laden
    handel = Branche.query.filter_by(name='HANDEL', parent_id=None).first()
    handel_unterbranchen = []
    if handel:
        handel_unterbranchen = Branche.query.filter_by(
            parent_id=handel.id,
            aktiv=True
        ).order_by(Branche.sortierung).all()

    # Query aufbauen mit Filtern
    query = Lieferant.query

    # Filter: Hauptbranche
    if branche_id:
        query = query.join(LieferantBranche).filter(
            LieferantBranche.branche_id == branche_id,
            LieferantBranche.ist_hauptbranche == True
        )

    # Filter: Status (aktiv/inaktiv)
    if status == 'aktiv':
        query = query.filter(Lieferant.aktiv == True)
    elif status == 'inaktiv':
        query = query.filter(Lieferant.aktiv == False)

    # Suche: Name, VEDES-ID oder GLN
    if suchbegriff:
        query = query.filter(
            db.or_(
                Lieferant.kurzbezeichnung.ilike(f'%{suchbegriff}%'),
                Lieferant.vedes_id.ilike(f'%{suchbegriff}%'),
                Lieferant.gln.ilike(f'%{suchbegriff}%')
            )
        )

    lieferanten_liste = query.order_by(Lieferant.kurzbezeichnung).all()

    return render_template(
        'administration/lieferanten.html',
        lieferanten=lieferanten_liste,
        handel_unterbranchen=handel_unterbranchen,
        filter_branche=branche_id,
        filter_status=status,
        suchbegriff=suchbegriff,
        admin_tab='stammdaten'
    )


@admin_bp.route('/lieferanten/form', methods=['GET', 'POST'])
@admin_bp.route('/lieferanten/form/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def lieferant_form(id=None):
    """Create or edit a supplier."""
    if id:
        lieferant = Lieferant.query.get_or_404(id)
    else:
        lieferant = Lieferant()

    # Load HANDEL sub-branches for branch assignment
    handel = Branche.query.filter_by(name='HANDEL', parent_id=None).first()
    handel_unterbranchen = []
    if handel:
        handel_unterbranchen = Branche.query.filter_by(
            parent_id=handel.id,
            aktiv=True
        ).order_by(Branche.sortierung).all()

    # Get assigned branch IDs
    zugeordnete_branche_ids = [lb.branche_id for lb in lieferant.branchen] if lieferant.id else []

    # Common template data
    template_data = {
        'lieferant': lieferant,
        'admin_tab': 'stammdaten',
        'handel_unterbranchen': handel_unterbranchen,
        'zugeordnete_branche_ids': zugeordnete_branche_ids
    }

    if request.method == 'POST':
        # Get form data
        kurzbezeichnung = request.form.get('kurzbezeichnung', '').strip()
        vedes_id = request.form.get('vedes_id', '').strip()
        gln = request.form.get('gln', '').strip() or None
        aktiv = 'aktiv' in request.form

        # Validation
        if not kurzbezeichnung:
            flash('Kurzbezeichnung ist erforderlich.', 'danger')
            return render_template('administration/lieferant_form.html', **template_data)

        if not vedes_id:
            flash('VEDES-ID ist erforderlich.', 'danger')
            return render_template('administration/lieferant_form.html', **template_data)

        # Check for duplicate VEDES-ID (only for new entries or changed ID)
        if not lieferant.id or lieferant.vedes_id != vedes_id:
            existing = Lieferant.query.filter_by(vedes_id=vedes_id).first()
            if existing and existing.id != lieferant.id:
                flash(f'VEDES-ID "{vedes_id}" existiert bereits.', 'danger')
                return render_template('administration/lieferant_form.html', **template_data)

        # Check for duplicate GLN
        if gln:
            existing_gln = Lieferant.query.filter_by(gln=gln).first()
            if existing_gln and existing_gln.id != lieferant.id:
                flash(f'GLN "{gln}" existiert bereits.', 'danger')
                return render_template('administration/lieferant_form.html', **template_data)

        # Update fields
        lieferant.kurzbezeichnung = kurzbezeichnung
        if not lieferant.id:  # Only set VEDES-ID for new entries
            lieferant.vedes_id = vedes_id
        lieferant.gln = gln
        lieferant.aktiv = aktiv

        try:
            if not lieferant.id:
                db.session.add(lieferant)
            db.session.commit()
            flash(f'Lieferant "{kurzbezeichnung}" wurde gespeichert.', 'success')
            return redirect(url_for('admin.lieferanten'))
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Speichern: {str(e)}', 'danger')

    return render_template('administration/lieferant_form.html', **template_data)


# ═══════════════════════════════════════════════════════════════════════════════
# Lieferant-Branchen AJAX Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@admin_bp.route('/lieferanten/<int:id>/branchen/<int:branche_id>', methods=['POST'])
@login_required
@admin_required
def lieferant_branche_add(id, branche_id):
    """Add a branch to a supplier (AJAX)."""
    lieferant = Lieferant.query.get_or_404(id)
    branche = Branche.query.get_or_404(branche_id)

    # Validate: Only HANDEL sub-branches allowed
    handel = Branche.query.filter_by(name='HANDEL', parent_id=None).first()
    if not handel or branche.parent_id != handel.id:
        return jsonify({'error': 'Nur HANDEL-Unterbranchen erlaubt'}), 400

    # Check if already assigned
    existing = LieferantBranche.query.filter_by(
        lieferant_id=id,
        branche_id=branche_id
    ).first()
    if existing:
        return jsonify({'error': 'Branche bereits zugeordnet'}), 400

    # Check max 3 branches
    if len(lieferant.branchen) >= 3:
        return jsonify({'error': 'Maximal 3 Branchen erlaubt'}), 400

    # First branch becomes Hauptbranche automatically
    ist_hauptbranche = len(lieferant.branchen) == 0

    try:
        lb = LieferantBranche(
            lieferant_id=id,
            branche_id=branche_id,
            ist_hauptbranche=ist_hauptbranche
        )
        db.session.add(lb)
        db.session.commit()
        return jsonify({'success': True, 'ist_hauptbranche': ist_hauptbranche})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/lieferanten/<int:id>/branchen/<int:branche_id>', methods=['DELETE'])
@login_required
@admin_required
def lieferant_branche_remove(id, branche_id):
    """Remove a branch from a supplier (AJAX)."""
    lb = LieferantBranche.query.filter_by(
        lieferant_id=id,
        branche_id=branche_id
    ).first_or_404()

    war_hauptbranche = lb.ist_hauptbranche

    try:
        db.session.delete(lb)
        db.session.commit()

        # If we removed the Hauptbranche, assign next one
        if war_hauptbranche:
            lieferant = Lieferant.query.get(id)
            if lieferant.branchen:
                lieferant.branchen[0].ist_hauptbranche = True
                db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/lieferanten/<int:id>/branchen/<int:branche_id>/hauptbranche', methods=['POST'])
@login_required
@admin_required
def lieferant_branche_hauptbranche(id, branche_id):
    """Set a branch as Hauptbranche (AJAX)."""
    lieferant = Lieferant.query.get_or_404(id)

    # Check if branch is assigned
    target_lb = LieferantBranche.query.filter_by(
        lieferant_id=id,
        branche_id=branche_id
    ).first()

    # If not assigned, add it first
    if not target_lb:
        branche = Branche.query.get_or_404(branche_id)

        # Validate: Only HANDEL sub-branches
        handel = Branche.query.filter_by(name='HANDEL', parent_id=None).first()
        if not handel or branche.parent_id != handel.id:
            return jsonify({'error': 'Nur HANDEL-Unterbranchen erlaubt'}), 400

        # Check max 3 branches
        if len(lieferant.branchen) >= 3:
            return jsonify({'error': 'Maximal 3 Branchen erlaubt'}), 400

        target_lb = LieferantBranche(
            lieferant_id=id,
            branche_id=branche_id,
            ist_hauptbranche=False
        )
        db.session.add(target_lb)

    try:
        # Remove Hauptbranche from all others
        for lb in lieferant.branchen:
            lb.ist_hauptbranche = False

        # Set new Hauptbranche
        target_lb.ist_hauptbranche = True
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/lieferanten/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def lieferant_delete(id):
    """Delete a supplier."""
    lieferant = Lieferant.query.get_or_404(id)
    name = lieferant.kurzbezeichnung

    try:
        db.session.delete(lieferant)
        db.session.commit()
        flash(f'Lieferant "{name}" wurde gelöscht.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Löschen: {str(e)}', 'danger')

    return redirect(url_for('admin.lieferanten'))


@admin_bp.route('/hersteller')
@login_required
@admin_required
def hersteller():
    """Hersteller-Stammdaten verwalten."""
    from app.models import Hersteller
    hersteller_liste = Hersteller.query.order_by(Hersteller.kurzbezeichnung).all()

    return render_template(
        'administration/hersteller.html',
        hersteller=hersteller_liste,
        admin_tab='stammdaten'
    )


@admin_bp.route('/hersteller/form', methods=['GET', 'POST'])
@admin_bp.route('/hersteller/form/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def hersteller_form(id=None):
    """Create or edit a manufacturer."""
    from app.models import Hersteller

    if id:
        hersteller = Hersteller.query.get_or_404(id)
    else:
        hersteller = Hersteller()

    if request.method == 'POST':
        # Get form data
        kurzbezeichnung = request.form.get('kurzbezeichnung', '').strip()
        gln = request.form.get('gln', '').strip()
        vedes_id = request.form.get('vedes_id', '').strip() or None

        # Validation
        if not kurzbezeichnung:
            flash('Kurzbezeichnung ist erforderlich.', 'danger')
            return render_template('administration/hersteller_form.html',
                                 hersteller=hersteller, admin_tab='stammdaten')

        if not gln:
            flash('GLN ist erforderlich.', 'danger')
            return render_template('administration/hersteller_form.html',
                                 hersteller=hersteller, admin_tab='stammdaten')

        # Check for duplicate GLN (only for new entries or changed GLN)
        if not hersteller.id or hersteller.gln != gln:
            existing = Hersteller.query.filter_by(gln=gln).first()
            if existing and existing.id != hersteller.id:
                flash(f'GLN "{gln}" existiert bereits.', 'danger')
                return render_template('administration/hersteller_form.html',
                                     hersteller=hersteller, admin_tab='stammdaten')

        # Check for duplicate VEDES-ID
        if vedes_id:
            existing_vedes = Hersteller.query.filter_by(vedes_id=vedes_id).first()
            if existing_vedes and existing_vedes.id != hersteller.id:
                flash(f'VEDES-ID "{vedes_id}" existiert bereits.', 'danger')
                return render_template('administration/hersteller_form.html',
                                     hersteller=hersteller, admin_tab='stammdaten')

        # Update fields
        hersteller.kurzbezeichnung = kurzbezeichnung
        if not hersteller.id:  # Only set GLN for new entries
            hersteller.gln = gln
        hersteller.vedes_id = vedes_id

        try:
            if not hersteller.id:
                db.session.add(hersteller)
            db.session.commit()
            flash(f'Hersteller "{kurzbezeichnung}" wurde gespeichert.', 'success')
            return redirect(url_for('admin.hersteller'))
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Speichern: {str(e)}', 'danger')

    return render_template('administration/hersteller_form.html',
                         hersteller=hersteller, admin_tab='stammdaten')


@admin_bp.route('/hersteller/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def hersteller_delete(id):
    """Delete a manufacturer and all associated brands."""
    from app.models import Hersteller

    hersteller = Hersteller.query.get_or_404(id)
    name = hersteller.kurzbezeichnung
    marken_count = hersteller.marken.count()

    try:
        db.session.delete(hersteller)
        db.session.commit()
        if marken_count > 0:
            flash(f'Hersteller "{name}" und {marken_count} zugehörige Marken wurden gelöscht.', 'success')
        else:
            flash(f'Hersteller "{name}" wurde gelöscht.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Löschen: {str(e)}', 'danger')

    return redirect(url_for('admin.hersteller'))


@admin_bp.route('/marken')
@login_required
@admin_required
def marken():
    """Marken-Stammdaten verwalten."""
    from app.models import Marke
    marken_liste = Marke.query.order_by(Marke.kurzbezeichnung).all()

    return render_template(
        'administration/marken.html',
        marken=marken_liste,
        admin_tab='stammdaten'
    )


@admin_bp.route('/marken/form', methods=['GET', 'POST'])
@admin_bp.route('/marken/form/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def marke_form(id=None):
    """Create or edit a brand."""
    from app.models import Marke, Hersteller

    if id:
        marke = Marke.query.get_or_404(id)
    else:
        marke = Marke()

    hersteller_liste = Hersteller.query.order_by(Hersteller.kurzbezeichnung).all()

    if request.method == 'POST':
        # Get form data
        kurzbezeichnung = request.form.get('kurzbezeichnung', '').strip()
        hersteller_id = request.form.get('hersteller_id', '').strip()

        # Validation
        if not kurzbezeichnung:
            flash('Kurzbezeichnung ist erforderlich.', 'danger')
            return render_template('administration/marke_form.html',
                                 marke=marke, hersteller=hersteller_liste, admin_tab='stammdaten')

        if not hersteller_id:
            flash('Hersteller ist erforderlich.', 'danger')
            return render_template('administration/marke_form.html',
                                 marke=marke, hersteller=hersteller_liste, admin_tab='stammdaten')

        # Get the selected manufacturer
        selected_hersteller = Hersteller.query.get(int(hersteller_id))
        if not selected_hersteller:
            flash('Hersteller nicht gefunden.', 'danger')
            return render_template('administration/marke_form.html',
                                 marke=marke, hersteller=hersteller_liste, admin_tab='stammdaten')

        # Update fields
        marke.kurzbezeichnung = kurzbezeichnung
        marke.hersteller_id = int(hersteller_id)

        # Generate GLN evendo if new
        if not marke.id:
            marke.gln_evendo = Marke.generate_gln_evendo(selected_hersteller, kurzbezeichnung)

        try:
            if not marke.id:
                db.session.add(marke)
            db.session.commit()
            flash(f'Marke "{kurzbezeichnung}" wurde gespeichert.', 'success')
            return redirect(url_for('admin.marken'))
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Speichern: {str(e)}', 'danger')

    return render_template('administration/marke_form.html',
                         marke=marke, hersteller=hersteller_liste, admin_tab='stammdaten')


@admin_bp.route('/marken/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def marke_delete(id):
    """Delete a brand."""
    from app.models import Marke

    marke = Marke.query.get_or_404(id)
    name = marke.kurzbezeichnung

    try:
        db.session.delete(marke)
        db.session.commit()
        flash(f'Marke "{name}" wurde gelöscht.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Fehler beim Löschen: {str(e)}', 'danger')

    return redirect(url_for('admin.marken'))


@admin_bp.route('/config')
@login_required
@admin_required
def config():
    """Systemkonfiguration verwalten."""
    configs = Config.query.order_by(Config.key).all()

    return render_template(
        'administration/config.html',
        configs=configs,
        admin_tab='stammdaten'
    )
