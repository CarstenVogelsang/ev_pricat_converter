"""Flask routes."""
from app.routes.main import main_bp
from app.routes.admin import admin_bp
from app.routes.kunden import kunden_bp

__all__ = ['main_bp', 'admin_bp', 'kunden_bp']
