"""Flask-Admin configuration with role-based access control."""
from flask import redirect, url_for
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from markupsafe import Markup


def get_branding_extra_css():
    """Generate extra CSS for branding colors."""
    from app.services import BrandingService
    branding_service = BrandingService()
    branding = branding_service.get_branding()
    return Markup(f'''
    <style>
        .navbar-default {{
            background-color: {branding.primary_color} !important;
            border-color: {branding.primary_color} !important;
        }}
        .navbar-default .navbar-brand,
        .navbar-default .navbar-nav > li > a {{
            color: #fff !important;
        }}
        .navbar-default .navbar-nav > li > a:hover,
        .navbar-default .navbar-nav > li > a:focus {{
            color: rgba(255,255,255,0.8) !important;
            background-color: rgba(0,0,0,0.1) !important;
        }}
        .navbar-default .navbar-nav > .active > a,
        .navbar-default .navbar-nav > .active > a:hover,
        .navbar-default .navbar-nav > .active > a:focus {{
            color: #fff !important;
            background-color: rgba(0,0,0,0.2) !important;
        }}
        .navbar-back-link {{
            padding: 8px 15px;
            color: rgba(255,255,255,0.9) !important;
            display: inline-block;
            font-size: 13px;
            border-right: 1px solid rgba(255,255,255,0.2);
            margin-right: 10px;
            text-decoration: none;
        }}
        .navbar-back-link:hover {{
            color: #fff !important;
            text-decoration: none;
            background-color: rgba(0,0,0,0.1);
        }}
        .btn-primary {{
            background-color: {branding.primary_color} !important;
            border-color: {branding.primary_color} !important;
        }}
        .btn-primary:hover {{
            background-color: {branding.secondary_color} !important;
            border-color: {branding.secondary_color} !important;
        }}
        a {{ color: {branding.primary_color}; }}
        a:hover {{ color: {branding.secondary_color}; }}
    </style>
    ''')


class SecureModelView(ModelView):
    """ModelView that requires admin role."""

    def is_accessible(self):
        """Check if current user is admin."""
        return current_user.is_authenticated and current_user.rolle == 'admin'

    def inaccessible_callback(self, name, **kwargs):
        """Redirect to login if not accessible."""
        return redirect(url_for('auth.login'))

    def render(self, template, **kwargs):
        """Add branding and extra CSS to template context."""
        from app.services import BrandingService
        branding_service = BrandingService()
        kwargs['branding'] = branding_service.get_branding()
        kwargs['extra_css'] = get_branding_extra_css()
        return super().render(template, **kwargs)


class SecureAdminIndexView(AdminIndexView):
    """Admin index view that requires admin role."""

    @expose('/')
    def index(self):
        """Check admin access before showing index."""
        if not (current_user.is_authenticated and current_user.rolle == 'admin'):
            return redirect(url_for('auth.login'))
        return super().index()

    def render(self, template, **kwargs):
        """Add branding and extra CSS to template context."""
        from app.services import BrandingService
        branding_service = BrandingService()
        kwargs['branding'] = branding_service.get_branding()
        kwargs['extra_css'] = get_branding_extra_css()
        return super().render(template, **kwargs)


def init_admin(app, db):
    """Initialize Flask-Admin with all model views."""
    from app.models import Lieferant, Hersteller, Marke, Config, User, Branche, Verband, Kunde

    admin = Admin(
        app,
        name='DB Admin',
        url='/db-admin',
        endpoint='dbadmin',  # Unique endpoint to avoid conflict with admin_bp
        index_view=SecureAdminIndexView(url='/db-admin', endpoint='dbadmin')
    )

    # Add model views
    admin.add_view(SecureModelView(Lieferant, db.session, name='Lieferanten'))
    admin.add_view(SecureModelView(Hersteller, db.session, name='Hersteller'))
    admin.add_view(SecureModelView(Marke, db.session, name='Marken'))
    admin.add_view(SecureModelView(Config, db.session, name='Config'))
    admin.add_view(SecureModelView(User, db.session, name='Users'))
    admin.add_view(SecureModelView(Kunde, db.session, name='Kunden'))
    admin.add_view(SecureModelView(Branche, db.session, name='Branchen'))
    admin.add_view(SecureModelView(Verband, db.session, name='Verbände'))

    return admin
