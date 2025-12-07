"""Routes for Lieferanten-Auswahl (Meine Lieferanten) module."""

from flask import Blueprint, render_template
from flask_login import login_required

lieferanten_auswahl_bp = Blueprint(
    'lieferanten_auswahl',
    __name__,
    url_prefix='/lieferanten-auswahl'
)


@lieferanten_auswahl_bp.route('/')
@login_required
def index():
    """Display the Lieferanten-Auswahl dashboard."""
    return render_template('lieferanten_auswahl/index.html')
