"""Admin routes for system management and testing."""
from flask import Blueprint, render_template, jsonify, flash, redirect, url_for
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
