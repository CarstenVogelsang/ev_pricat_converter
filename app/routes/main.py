"""Main routes for the pricat-converter."""
import json
from pathlib import Path

from flask import Blueprint, render_template, jsonify, flash, redirect, url_for, request, current_app, session
from flask_login import login_required, current_user

from app import db
from app.models import Lieferant
from app.services import Processor, ProcessingStep, FTPService, BrandingService

main_bp = Blueprint('main', __name__)

# Store processing results in memory (for demo - use Redis/DB in production)
_processing_results = {}


@main_bp.route('/')
def landing():
    """Public landing page or redirect to dashboard."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    branding_service = BrandingService()
    branding = branding_service.get_branding()
    return render_template('landing.html', branding=branding)


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard with role-based app access."""
    from app.models import SubApp, SubAppAccess

    # Admin sees all active apps
    if current_user.is_admin:
        subapps = SubApp.query.filter_by(aktiv=True).order_by(SubApp.sort_order).all()
    else:
        # Non-admin: query apps accessible to their role
        subapps = SubApp.query.join(SubAppAccess).filter(
            SubApp.aktiv == True,
            SubAppAccess.rolle_id == current_user.rolle_id
        ).order_by(SubApp.sort_order).all()

    # Convert to template-friendly format
    apps = []
    for subapp in subapps:
        app_data = {
            'id': subapp.slug,
            'name': subapp.name,
            'description': subapp.beschreibung,
            'icon': subapp.icon,
            'color': subapp.color,
            'disabled': not subapp.route_endpoint,
            'url': url_for(subapp.route_endpoint) if subapp.route_endpoint else '#'
        }
        apps.append(app_data)

    return render_template('dashboard.html', apps=apps)


@main_bp.route('/lieferanten')
@login_required
def lieferanten():
    """Display list of suppliers with filter."""
    filter_param = request.args.get('filter', 'aktiv')

    if filter_param == 'inaktiv':
        lieferanten = Lieferant.query.filter_by(aktiv=False).order_by(Lieferant.kurzbezeichnung).all()
        titel = 'Inaktive Lieferanten'
    elif filter_param == 'alle':
        lieferanten = Lieferant.query.order_by(Lieferant.kurzbezeichnung).all()
        titel = 'Alle Lieferanten'
    else:
        lieferanten = Lieferant.query.filter_by(aktiv=True).order_by(Lieferant.kurzbezeichnung).all()
        titel = 'Aktive Lieferanten'
        filter_param = 'aktiv'

    return render_template('index.html', lieferanten=lieferanten, filter=filter_param, titel=titel)


@main_bp.route('/toggle-aktiv/<int:lieferant_id>', methods=['POST'])
@login_required
def toggle_aktiv(lieferant_id):
    """Toggle supplier active status."""
    lieferant = Lieferant.query.get_or_404(lieferant_id)
    lieferant.aktiv = not lieferant.aktiv
    db.session.commit()

    status = 'aktiviert' if lieferant.aktiv else 'deaktiviert'
    flash(f'{lieferant.kurzbezeichnung} wurde {status}.', 'success')

    # Redirect back with current filter
    current_filter = request.form.get('current_filter', 'aktiv')
    return redirect(url_for('main.lieferanten', filter=current_filter))


@main_bp.route('/ftp-check/<int:lieferant_id>', methods=['POST'])
@login_required
def ftp_check(lieferant_id):
    """Check and download PRICAT file from FTP if changed."""
    lieferant = Lieferant.query.get_or_404(lieferant_id)

    ftp_service = FTPService()
    result = ftp_service.update_single_lieferant(lieferant)

    if result['success']:
        if result['downloaded']:
            flash(f'{lieferant.kurzbezeichnung}: {result["message"]}', 'success')
        else:
            flash(f'{lieferant.kurzbezeichnung}: {result["message"]}', 'info')
    else:
        flash(f'{lieferant.kurzbezeichnung}: {result["message"]}', 'danger')

    # Redirect back with current filter
    current_filter = request.form.get('current_filter', 'aktiv')
    return redirect(url_for('main.lieferanten', filter=current_filter))


@main_bp.route('/verarbeite-lokal/<int:lieferant_id>', methods=['POST'])
@login_required
def verarbeite_lokal(lieferant_id):
    """Process using local PRICAT file (no network operations)."""
    lieferant = Lieferant.query.get_or_404(lieferant_id)

    # Find local PRICAT file
    imports_dir = current_app.config['IMPORTS_DIR']
    existing = list(imports_dir.glob(f"pricat_{lieferant.vedes_id}_*.csv"))

    # Also check docs folder
    docs_pricat = Path(current_app.root_path).parent / 'docs'
    docs_files = list(docs_pricat.glob(f"pricat_{lieferant.vedes_id}_*.csv"))
    existing.extend(docs_files)

    if not existing:
        flash(f'Keine lokale PRICAT-Datei für {lieferant.kurzbezeichnung} gefunden', 'warning')
        return redirect(url_for('main.lieferanten'))

    local_pricat = sorted(existing, key=lambda p: p.stat().st_mtime)[-1]

    # Process locally
    processor = Processor(
        skip_ftp_download=True,
        skip_image_download=True,
        skip_ftp_upload=True,
        skip_import_trigger=True
    )

    result = processor.process(lieferant, local_pricat_path=local_pricat)
    _processing_results[lieferant_id] = result

    if result.success:
        flash(f'Lokale Verarbeitung für {lieferant.kurzbezeichnung} erfolgreich: '
              f'{result.articles_count} Artikel exportiert', 'success')
    else:
        error_msg = result.errors[0] if result.errors else 'Unbekannter Fehler'
        flash(f'Verarbeitung fehlgeschlagen: {error_msg}', 'danger')

    return redirect(url_for('main.status', lieferant_id=lieferant.id))


@main_bp.route('/status/<int:lieferant_id>')
@login_required
def status(lieferant_id):
    """Display processing status for a supplier."""
    lieferant = Lieferant.query.get_or_404(lieferant_id)
    result = _processing_results.get(lieferant_id)
    return render_template('status.html', lieferant=lieferant, result=result)


@main_bp.route('/api/status/<int:lieferant_id>')
def api_status(lieferant_id):
    """API endpoint: Get processing status."""
    result = _processing_results.get(lieferant_id)

    if not result:
        return jsonify({'status': 'not_started'})

    steps_data = []
    for step in result.steps:
        steps_data.append({
            'step': step.step.value,
            'name': step.step.name,
            'success': step.success,
            'message': step.message
        })

    return jsonify({
        'status': 'completed' if result.success else 'failed',
        'success': result.success,
        'current_step': result.current_step.value,
        'progress': result.progress_percent,
        'steps': steps_data,
        'articles_count': result.articles_count,
        'hersteller_count': result.hersteller_count,
        'marken_count': result.marken_count,
        'images_downloaded': result.images_downloaded,
        'errors': result.errors,
        'elena_csv': str(result.elena_csv_path) if result.elena_csv_path else None,
        'xlsx': str(result.xlsx_path) if result.xlsx_path else None
    })


@main_bp.route('/api/lieferanten')
def api_lieferanten():
    """API endpoint: List all active suppliers."""
    lieferanten = Lieferant.query.filter_by(aktiv=True).all()
    return jsonify([l.to_dict() for l in lieferanten])


@main_bp.route('/downloads')
@login_required
def downloads():
    """List available export files."""
    exports_dir = current_app.config['EXPORTS_DIR']

    files = []
    for f in exports_dir.glob('*'):
        if f.is_file() and f.name != '.gitkeep':
            files.append({
                'name': f.name,
                'size': f.stat().st_size,
                'modified': f.stat().st_mtime
            })

    files.sort(key=lambda x: x['modified'], reverse=True)
    return render_template('downloads.html', files=files)
