"""Flask-Admin configuration with role-based access control."""
from flask import redirect, url_for
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from markupsafe import Markup


# Common German labels for shared fields
COMMON_LABELS = {
    'id': 'ID',
    'created_at': 'Erstellt am',
    'updated_at': 'Aktualisiert am',
    'aktiv': 'Aktiv',
    'kurzbezeichnung': 'Kurzbezeichnung',
    'gln': 'GLN',
    'vedes_id': 'VEDES-ID',
    'name': 'Name',
}


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


# --- Specialized ModelViews with German labels ---

class LieferantModelView(SecureModelView):
    """ModelView for Lieferant with German labels."""
    column_labels = {
        **COMMON_LABELS,
        'ftp_quelldatei': 'FTP-Quelldatei',
        'ftp_pfad_ziel': 'FTP-Zielpfad',
        'elena_startdir': 'Elena Startverzeichnis',
        'elena_base_url': 'Elena Basis-URL',
        'letzte_konvertierung': 'Letzte Konvertierung',
        'artikel_anzahl': 'Artikelanzahl',
        'ftp_datei_datum': 'FTP-Dateidatum',
        'ftp_datei_groesse': 'Dateigroesse (Bytes)',
    }
    column_list = ['gln', 'vedes_id', 'kurzbezeichnung', 'aktiv', 'artikel_anzahl', 'letzte_konvertierung']
    column_searchable_list = ['kurzbezeichnung', 'gln', 'vedes_id']
    column_filters = ['aktiv']


class HerstellerModelView(SecureModelView):
    """ModelView for Hersteller with German labels."""
    column_labels = {
        **COMMON_LABELS,
        'marken': 'Marken',
    }
    column_list = ['gln', 'vedes_id', 'kurzbezeichnung', 'created_at']
    column_searchable_list = ['kurzbezeichnung', 'gln', 'vedes_id']


class MarkeModelView(SecureModelView):
    """ModelView for Marke with German labels."""
    column_labels = {
        **COMMON_LABELS,
        'gln_evendo': 'GLN (e-vendo)',
        'hersteller_id': 'Hersteller ID',
        'hersteller': 'Hersteller',
    }
    column_list = ['kurzbezeichnung', 'gln_evendo', 'hersteller', 'created_at']
    column_searchable_list = ['kurzbezeichnung', 'gln_evendo']


class KundeModelView(SecureModelView):
    """ModelView for Kunde with German labels."""
    column_labels = {
        **COMMON_LABELS,
        'firmierung': 'Firmierung',
        'ev_kdnr': 'e-vendo Kundennr.',
        'strasse': 'Strasse',
        'plz': 'PLZ',
        'ort': 'Ort',
        'land': 'Land',
        'adresse': 'Adresse (Legacy)',
        'website_url': 'Website',
        'shop_url': 'Shop-URL',
        'notizen': 'Notizen',
        'ci': 'Corporate Identity',
        'branchen': 'Branchen',
        'verbaende': 'Verbaende',
    }
    column_list = ['firmierung', 'ev_kdnr', 'ort', 'aktiv', 'created_at']
    column_searchable_list = ['firmierung', 'ev_kdnr', 'ort']
    column_filters = ['aktiv', 'land']


class BrancheModelView(SecureModelView):
    """ModelView for Branche with German labels."""
    column_labels = {
        **COMMON_LABELS,
        'icon': 'Icon (Tabler)',
        'sortierung': 'Sortierung',
        'kunden': 'Kunden',
    }
    column_list = ['name', 'icon', 'aktiv', 'sortierung']
    column_searchable_list = ['name']
    column_filters = ['aktiv']


class VerbandModelView(SecureModelView):
    """ModelView for Verband with German labels."""
    column_labels = {
        **COMMON_LABELS,
        'kuerzel': 'Kuerzel',
        'logo_url': 'Logo-URL',
        'website_url': 'Website',
        'kunden': 'Kunden',
    }
    column_list = ['name', 'kuerzel', 'aktiv', 'website_url']
    column_searchable_list = ['name', 'kuerzel']
    column_filters = ['aktiv']


class UserModelView(SecureModelView):
    """ModelView for User with German labels."""
    column_labels = {
        **COMMON_LABELS,
        'email': 'E-Mail',
        'password_hash': 'Passwort-Hash',
        'vorname': 'Vorname',
        'nachname': 'Nachname',
        'rolle_id': 'Rolle',
        'rolle_obj': 'Rolle',
        'last_login': 'Letzter Login',
    }
    column_list = ['email', 'vorname', 'nachname', 'rolle_obj', 'aktiv', 'last_login']
    column_searchable_list = ['email', 'vorname', 'nachname']
    column_filters = ['aktiv']
    # Hide password hash from form
    form_excluded_columns = ['password_hash']


class ConfigModelView(SecureModelView):
    """ModelView for Config with German labels."""
    column_labels = {
        **COMMON_LABELS,
        'key': 'Schluessel',
        'value': 'Wert',
        'beschreibung': 'Beschreibung',
    }
    column_list = ['key', 'value', 'beschreibung', 'updated_at']
    column_searchable_list = ['key', 'beschreibung']


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

    # Add model views with categories (using specialized views with German labels)
    # PRICAT
    admin.add_view(LieferantModelView(Lieferant, db.session, name='Lieferanten', category='PRICAT'))
    admin.add_view(HerstellerModelView(Hersteller, db.session, name='Hersteller', category='PRICAT'))
    admin.add_view(MarkeModelView(Marke, db.session, name='Marken', category='PRICAT'))

    # Kunden
    admin.add_view(KundeModelView(Kunde, db.session, name='Kunden', category='Kunden'))
    admin.add_view(BrancheModelView(Branche, db.session, name='Branchen', category='Kunden'))
    admin.add_view(VerbandModelView(Verband, db.session, name='Verbaende', category='Kunden'))

    # System
    admin.add_view(UserModelView(User, db.session, name='Benutzer', category='System'))
    admin.add_view(ConfigModelView(Config, db.session, name='Konfiguration', category='System'))

    return admin
