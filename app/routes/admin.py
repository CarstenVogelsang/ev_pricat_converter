"""Admin routes for system management and testing."""
import json
import os
import sys
from datetime import datetime
from flask import Blueprint, render_template, jsonify, flash, redirect, url_for, request, Response, current_app
from flask_login import login_required
from werkzeug.utils import secure_filename
import flask

from app import db
from app.models import Config, Lieferant, User, Kunde, SubApp
from app.services import FTPService, BrandingService
from app.routes.auth import admin_required

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

    # SubApps
    subapps = SubApp.query.order_by(SubApp.sort_order).all()

    # Environment info
    environment = os.environ.get('FLASK_CONFIG', 'development')

    return render_template(
        'administration/index.html',
        db_status=db_status,
        user_count=user_count,
        kunde_count=kunde_count,
        lieferant_count=lieferant_count,
        subapps=subapps,
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

    return Response(
        json_data,
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )


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

    # GET request
    branding_config = branding_service.get_branding()
    return render_template(
        'administration/branding.html',
        branding=branding_config,
        current_logo=Config.get_value('brand_logo', '')
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
        db.session.commit()
        flash('Logo gelöscht', 'success')

    return redirect(url_for('admin.branding'))


def _update_config(key: str, value: str):
    """Update or create a config entry."""
    config = Config.query.filter_by(key=key).first()
    if config:
        config.value = value
    else:
        config = Config(key=key, value=value)
        db.session.add(config)
