"""Main routes for the pricat-converter."""
import json
from pathlib import Path

from flask import Blueprint, render_template, jsonify, flash, redirect, url_for, request, current_app, session
from flask_login import login_required

from app import db
from app.models import Lieferant
from app.services import Processor, ProcessingStep

main_bp = Blueprint('main', __name__)

# Store processing results in memory (for demo - use Redis/DB in production)
_processing_results = {}


@main_bp.route('/')
@login_required
def index():
    """Display list of active suppliers."""
    lieferanten = Lieferant.query.filter_by(aktiv=True).order_by(Lieferant.kurzbezeichnung).all()
    return render_template('index.html', lieferanten=lieferanten)


@main_bp.route('/verarbeite/<int:lieferant_id>', methods=['POST'])
@login_required
def verarbeite(lieferant_id):
    """Start processing for a supplier."""
    lieferant = Lieferant.query.get_or_404(lieferant_id)

    # Check for local file option
    use_local = request.form.get('use_local', 'false') == 'true'
    skip_images = request.form.get('skip_images', 'false') == 'true'

    # Initialize processor with options
    processor = Processor(
        skip_ftp_download=use_local,
        skip_image_download=skip_images,
        skip_ftp_upload=True,  # Skip for now until FTP is configured
        skip_import_trigger=True  # Skip for now until Elena endpoint is reachable
    )

    # Try to find local PRICAT file
    local_pricat = None
    if use_local:
        imports_dir = current_app.config['IMPORTS_DIR']
        existing = list(imports_dir.glob(f"pricat_{lieferant.vedes_id}_*.csv"))
        if existing:
            local_pricat = sorted(existing)[-1]
        else:
            # Check docs folder for test file
            docs_pricat = Path(current_app.root_path).parent / 'docs' / f"pricat_{lieferant.vedes_id}_{lieferant.kurzbezeichnung}_0.csv"
            if docs_pricat.exists():
                local_pricat = docs_pricat

    # Execute processing
    result = processor.process(lieferant, local_pricat_path=local_pricat)

    # Store result for status page
    _processing_results[lieferant_id] = result

    if result.success:
        flash(f'Verarbeitung für {lieferant.kurzbezeichnung} erfolgreich: '
              f'{result.articles_count} Artikel, {result.hersteller_count} Hersteller, '
              f'{result.marken_count} Marken', 'success')
    else:
        error_msg = result.errors[0] if result.errors else 'Unbekannter Fehler'
        flash(f'Verarbeitung für {lieferant.kurzbezeichnung} fehlgeschlagen: {error_msg}', 'danger')

    return redirect(url_for('main.status', lieferant_id=lieferant.id))


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
        return redirect(url_for('main.index'))

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
