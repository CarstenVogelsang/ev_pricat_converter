"""Admin routes for system management and testing."""
import json
import os
import sys
from datetime import datetime
from flask import Blueprint, render_template, jsonify, flash, redirect, url_for, request, Response, current_app, make_response
from flask_login import login_required
from werkzeug.utils import secure_filename
import flask

from app import db
from app.models import Config, Lieferant, User, Kunde, KundeCI, Branche, Verband, HelpText, BranchenRolle, BrancheBranchenRolle, Modul, ModulZugriff, AuditLog, Rolle
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
# Branding Settings
# ============================================================================

@admin_bp.route('/branding', methods=['GET', 'POST'])
@login_required
@admin_required
def branding():
    """Branding settings page."""
    branding_service = BrandingService()

    if request.method == 'POST':
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

        db.session.commit()
        flash('Branding-Einstellungen gespeichert', 'success')
        return redirect(url_for('admin.branding'))

    # GET request - load Kunden with CI data for import feature
    kunden_mit_ci = Kunde.query.filter(Kunde.ci != None).order_by(Kunde.firmierung).all()

    branding_config = branding_service.get_branding()
    return render_template(
        'administration/branding.html',
        branding=branding_config,
        current_logo=Config.get_value('brand_logo', ''),
        kunden_mit_ci=kunden_mit_ci
    )


@admin_bp.route('/branding/delete-logo', methods=['POST'])
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

    return redirect(url_for('admin.branding'))


@admin_bp.route('/branding/apply-kunde/<int:kunde_id>', methods=['POST'])
@login_required
@admin_required
def apply_kunde_branding(kunde_id):
    """Apply branding from Kunde CI data."""
    kunde = Kunde.query.get_or_404(kunde_id)

    if not kunde.ci:
        flash('Kunde hat keine CI-Daten', 'warning')
        return redirect(url_for('admin.branding'))

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
    return redirect(url_for('admin.branding'))


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
