"""Flask routes."""
from app.routes.main import main_bp
from app.routes.admin import admin_bp
from app.routes.kunden import kunden_bp
from app.routes.lieferanten_auswahl import lieferanten_auswahl_bp
from app.routes.content_generator import content_generator_bp
from app.routes.abrechnung import abrechnung_bp

__all__ = [
    'main_bp',
    'admin_bp',
    'kunden_bp',
    'lieferanten_auswahl_bp',
    'content_generator_bp',
    'abrechnung_bp',
]
