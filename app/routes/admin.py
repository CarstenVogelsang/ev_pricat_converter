"""Admin routes for system management and testing."""
import json
from datetime import datetime
from flask import Blueprint, render_template, jsonify, flash, redirect, url_for, request, Response
from flask_login import login_required

from app import db
from app.models import Config, Lieferant
from app.services import FTPService
from app.routes.auth import admin_required

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/')
@login_required
@admin_required
def index():
    """Admin overview page with test buttons."""
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
        'admin.html',
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

    return redirect(url_for('admin.index'))


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

    return redirect(url_for('admin.index'))


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

    return redirect(url_for('admin.index'))


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


# Public API health endpoint
@admin_bp.route('/api/health')
def api_health():
    """Simple health check for load balancers/monitoring."""
    try:
        db.session.execute(db.text('SELECT 1'))
        return jsonify({'status': 'ok'}), 200
    except Exception:
        return jsonify({'status': 'error'}), 503


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
        return redirect(url_for('admin.index'))

    file = request.files['config_file']
    if file.filename == '':
        flash('Keine Datei ausgewählt', 'danger')
        return redirect(url_for('admin.index'))

    if not file.filename.endswith('.json'):
        flash('Nur JSON-Dateien erlaubt', 'danger')
        return redirect(url_for('admin.index'))

    try:
        # Read and parse JSON
        content = file.read().decode('utf-8')
        config_list = json.loads(content)

        if not isinstance(config_list, list):
            flash('Ungültiges JSON-Format (erwartet: Array)', 'danger')
            return redirect(url_for('admin.index'))

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

    return redirect(url_for('admin.index'))
