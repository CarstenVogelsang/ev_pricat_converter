"""Main routes for the pricat-converter."""
from flask import Blueprint, render_template, jsonify, flash, redirect, url_for

from app import db
from app.models import Lieferant

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Display list of active suppliers."""
    lieferanten = Lieferant.query.filter_by(aktiv=True).order_by(Lieferant.kurzbezeichnung).all()
    return render_template('index.html', lieferanten=lieferanten)


@main_bp.route('/verarbeite/<int:lieferant_id>', methods=['POST'])
def verarbeite(lieferant_id):
    """Start processing for a supplier."""
    lieferant = Lieferant.query.get_or_404(lieferant_id)

    # TODO: Implement actual processing
    # 1. Download PRICAT from VEDES FTP
    # 2. Parse PRICAT
    # 3. Extract entities (Hersteller, Marken)
    # 4. Download images
    # 5. Generate Elena CSV
    # 6. Generate XLSX
    # 7. Upload to target FTP
    # 8. Trigger Elena import

    flash(f'Verarbeitung für {lieferant.kurzbezeichnung} gestartet (noch nicht implementiert)', 'info')
    return redirect(url_for('main.index'))


@main_bp.route('/status/<int:lieferant_id>')
def status(lieferant_id):
    """Display processing status for a supplier."""
    lieferant = Lieferant.query.get_or_404(lieferant_id)
    return render_template('status.html', lieferant=lieferant)


@main_bp.route('/api/lieferanten')
def api_lieferanten():
    """API endpoint: List all active suppliers."""
    lieferanten = Lieferant.query.filter_by(aktiv=True).all()
    return jsonify([l.to_dict() for l in lieferanten])
