"""Flask Application Factory."""
import os
from datetime import datetime

import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from app.config import config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Bitte melden Sie sich an.'
login_manager.login_message_category = 'info'


def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    # Ensure data directories exist
    for dir_path in [
        app.config['IMPORTS_DIR'],
        app.config['EXPORTS_DIR'],
        app.config['IMAGES_DIR']
    ]:
        dir_path.mkdir(parents=True, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # User loader for Flask-Login
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.routes import (
        main_bp, admin_bp, kunden_bp, lieferanten_auswahl_bp,
        content_generator_bp, abrechnung_bp
    )
    from app.routes.auth import auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(auth_bp)
    app.register_blueprint(kunden_bp)
    app.register_blueprint(lieferanten_auswahl_bp)
    app.register_blueprint(content_generator_bp)
    app.register_blueprint(abrechnung_bp)

    # Initialize Flask-Admin (under /db-admin, requires admin role)
    from app.admin import init_admin
    init_admin(app, db)

    # Register CLI commands
    register_cli_commands(app)

    # Register Jinja2 filters
    @app.template_filter('datetime')
    def format_datetime(timestamp):
        """Format Unix timestamp to readable date."""
        if timestamp:
            return datetime.fromtimestamp(timestamp).strftime('%d.%m.%Y %H:%M')
        return ''

    @app.template_filter('nl2br')
    def nl2br_filter(text):
        """Convert newlines to <br> tags."""
        from markupsafe import Markup, escape
        if not text:
            return ''
        return Markup(escape(text).replace('\n', Markup('<br>')))

    # Context processor for branding
    @app.context_processor
    def inject_branding():
        """Inject branding into all templates."""
        from app.services import BrandingService
        branding_service = BrandingService()
        return {'branding': branding_service.get_branding()}

    return app


def register_cli_commands(app):
    """Register CLI commands."""

    @app.cli.command('seed')
    def seed_command():
        """Seed the database with initial data."""
        from app.models import Lieferant, Config as ConfigModel, Rolle, SubApp, SubAppAccess

        # Create roles
        roles_data = [
            ('admin', 'Vollzugriff auf alle Funktionen'),
            ('mitarbeiter', 'e-vendo Mitarbeiter'),
            ('kunde', 'Externer Kunde'),
        ]
        roles = {}
        for name, beschreibung in roles_data:
            rolle = Rolle.query.filter_by(name=name).first()
            if not rolle:
                rolle = Rolle(name=name, beschreibung=beschreibung)
                db.session.add(rolle)
                click.echo(f'Created role: {name}')
            roles[name] = rolle
        db.session.flush()  # Get IDs

        # Create SubApps
        subapps_data = [
            ('pricat', 'PRICAT Converter', 'VEDES PRICAT-Dateien zu Elena-Format konvertieren',
             'ti-route-square', 'primary', 'main.lieferanten', True, 10),
            ('kunden-report', 'Lead & Kundenreport', 'Kunden verwalten und Website-Analyse',
             'ti-users', 'success', 'kunden.liste', True, 20),
            ('lieferanten-auswahl', 'Meine Lieferanten', 'Relevante Lieferanten auswaehlen',
             'ti-truck', 'info', 'lieferanten_auswahl.index', True, 30),
            ('content-generator', 'Content Generator', 'KI-generierte Texte fuer Online-Shops',
             'ti-writing', 'warning', 'content_generator.index', True, 40),
        ]
        subapps = {}
        for slug, name, beschreibung, icon, color, endpoint, aktiv, sort in subapps_data:
            subapp = SubApp.query.filter_by(slug=slug).first()
            if not subapp:
                subapp = SubApp(
                    slug=slug, name=name, beschreibung=beschreibung,
                    icon=icon, color=color, route_endpoint=endpoint,
                    aktiv=aktiv, sort_order=sort
                )
                db.session.add(subapp)
                click.echo(f'Created SubApp: {name}')
            else:
                # Update existing SubApp
                subapp.name = name
                subapp.beschreibung = beschreibung
                subapp.icon = icon
                subapp.color = color
                subapp.route_endpoint = endpoint
                subapp.aktiv = aktiv
                subapp.sort_order = sort
                click.echo(f'Updated SubApp: {name}')
            subapps[slug] = subapp
        db.session.flush()

        # Create SubAppAccess mappings
        access_mappings = [
            ('pricat', ['admin', 'mitarbeiter']),
            ('kunden-report', ['admin', 'mitarbeiter']),
            ('lieferanten-auswahl', ['admin', 'mitarbeiter', 'kunde']),
            ('content-generator', ['admin', 'mitarbeiter', 'kunde']),
        ]
        for slug, role_names in access_mappings:
            subapp = subapps.get(slug)
            if subapp:
                for role_name in role_names:
                    rolle = roles.get(role_name)
                    if rolle:
                        existing = SubAppAccess.query.filter_by(
                            sub_app_id=subapp.id, rolle_id=rolle.id
                        ).first()
                        if not existing:
                            access = SubAppAccess(sub_app_id=subapp.id, rolle_id=rolle.id)
                            db.session.add(access)

        # Create test supplier (LEGO)
        # Note: vedes_id is stored without leading zeros
        lego = Lieferant.query.filter_by(vedes_id='1872').first()
        if not lego:
            lego = Lieferant(
                gln='4023017000005',
                vedes_id='1872',
                kurzbezeichnung='LEGO Spielwaren GmbH',
                aktiv=True,
                ftp_quelldatei='pricat_1872_Lego Spielwaren GmbH_0.csv',
                elena_startdir='lego',
                elena_base_url='https://direct.e-vendo.de'
            )
            db.session.add(lego)
            click.echo('Created test supplier: LEGO Spielwaren GmbH')
        else:
            click.echo('Test supplier already exists: LEGO Spielwaren GmbH')

        # Create default config entries
        config_defaults = [
            ('vedes_ftp_host', 'ftp.vedes.de', 'VEDES FTP Server'),
            ('vedes_ftp_port', '21', 'VEDES FTP Port'),
            ('vedes_ftp_user', '', 'VEDES FTP Benutzer'),
            ('vedes_ftp_pass', '', 'VEDES FTP Passwort'),
            ('vedes_ftp_basepath', '/pricat/', 'Basispfad PRICAT-Dateien'),
            ('elena_ftp_host', '', 'Ziel-FTP Server'),
            ('elena_ftp_port', '21', 'Ziel-FTP Port'),
            ('elena_ftp_user', '', 'Ziel-FTP Benutzer'),
            ('elena_ftp_pass', '', 'Ziel-FTP Passwort'),
            ('image_download_threads', '5', 'Parallele Bild-Downloads'),
            ('image_timeout', '30', 'Timeout Bild-Download in Sekunden'),
            # S3 Storage
            ('s3_enabled', 'false', 'S3 Storage aktivieren (true/false)'),
            ('s3_endpoint', '', 'S3 Endpoint URL (z.B. https://fsn1.your-objectstorage.com)'),
            ('s3_access_key', '', 'S3 Access Key'),
            ('s3_secret_key', '', 'S3 Secret Key (Base64-kodiert)'),
            ('s3_bucket', 'pricat-converter', 'S3 Bucket Name'),
            # Branding
            ('brand_logo', '', 'Pfad zum Logo (leer = Platzhalter)'),
            ('brand_primary_color', '#0d6efd', 'Primärfarbe (Hex)'),
            ('brand_secondary_color', '#6c757d', 'Sekundärfarbe (Hex)'),
            ('brand_app_title', 'ev247', 'App-Titel im Header'),
            ('copyright_text', '© 2025 e-vendo AG', 'Copyright-Text im Footer'),
            ('copyright_url', 'https://www.e-vendo.de', 'Link zur Hauptwebsite'),
            # Firecrawl
            ('firecrawl_api_key', '', 'Firecrawl API Key fuer Website-Analyse'),
            ('firecrawl_credit_kosten', '0.005', 'Kosten pro Firecrawl Credit in Euro'),
        ]

        for key, value, beschreibung in config_defaults:
            existing = ConfigModel.query.filter_by(key=key).first()
            if not existing:
                config_entry = ConfigModel(
                    key=key,
                    value=value,
                    beschreibung=beschreibung
                )
                db.session.add(config_entry)
                click.echo(f'Created config: {key}')

        db.session.commit()
        click.echo('Database seeded successfully!')

    @app.cli.command('init-db')
    def init_db_command():
        """Initialize the database."""
        db.create_all()
        click.echo('Database initialized!')

    @app.cli.command('seed-users')
    def seed_users_command():
        """Create initial users."""
        from app.models import User, Rolle

        # Ensure roles exist first
        admin_rolle = Rolle.query.filter_by(name='admin').first()
        if not admin_rolle:
            click.echo('ERROR: Roles not found. Run "flask seed" first.')
            return

        users = [
            {
                'email': 'carsten.vogelsang@e-vendo.de',
                'vorname': 'Carsten',
                'nachname': 'Vogelsang',
                'rolle_name': 'admin',
                'password': 'admin123'  # Should be changed on first login
            },
            {
                'email': 'rainer.raschka@e-vendo.de',
                'vorname': 'Rainer',
                'nachname': 'Raschka',
                'rolle_name': 'admin',
                'password': 'admin123'  # Should be changed on first login
            }
        ]

        for user_data in users:
            existing = User.query.filter_by(email=user_data['email']).first()
            if not existing:
                rolle = Rolle.query.filter_by(name=user_data['rolle_name']).first()
                if not rolle:
                    click.echo(f"Role not found: {user_data['rolle_name']}")
                    continue
                user = User(
                    email=user_data['email'],
                    vorname=user_data['vorname'],
                    nachname=user_data['nachname'],
                    rolle_id=rolle.id,
                    aktiv=True
                )
                user.set_password(user_data['password'])
                db.session.add(user)
                click.echo(f"Created user: {user_data['email']} ({user_data['rolle_name']})")
            else:
                click.echo(f"User already exists: {user_data['email']}")

        db.session.commit()
        click.echo('Users seeded successfully!')
