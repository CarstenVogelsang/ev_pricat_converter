"""Flask Application Factory."""
import os
from datetime import datetime

import click
import markdown
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
    from app.routes.passwort import passwort_bp
    from app.routes.dialog import dialog_bp
    from app.routes.dialog_admin import dialog_admin_bp
    from app.routes.benutzer import benutzer_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(auth_bp)
    app.register_blueprint(kunden_bp)
    app.register_blueprint(lieferanten_auswahl_bp)
    app.register_blueprint(content_generator_bp)
    app.register_blueprint(abrechnung_bp)
    # PRD-006: Kunden-Dialog
    app.register_blueprint(passwort_bp)
    app.register_blueprint(dialog_bp)
    app.register_blueprint(dialog_admin_bp)
    # Benutzer-Administration
    app.register_blueprint(benutzer_bp)

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

    @app.template_filter('markdown')
    def markdown_filter(text):
        """Convert Markdown text to HTML."""
        from markupsafe import Markup
        if not text:
            return ''
        # Use tables and fenced_code extensions for better formatting
        html = markdown.markdown(text, extensions=['tables', 'fenced_code', 'nl2br'])
        return Markup(html)

    # Context processor for branding
    @app.context_processor
    def inject_branding():
        """Inject branding into all templates."""
        from app.services import BrandingService
        branding_service = BrandingService()
        return {'branding': branding_service.get_branding()}

    # Context processor for module colors
    @app.context_processor
    def inject_module_colors():
        """Make module colors available in all templates."""
        from app.models import Modul

        module_colors = {}
        try:
            modules = Modul.query.filter(Modul.route_endpoint.isnot(None)).all()
            for modul in modules:
                if modul.route_endpoint:
                    # Extract blueprint name from endpoint (e.g., "kunden.liste" -> "kunden")
                    blueprint = modul.route_endpoint.split('.')[0]
                    module_colors[blueprint] = {
                        'color_hex': modul.color_hex or '#0d6efd',
                        'icon': modul.icon,
                        'name': modul.name,
                        'description': modul.beschreibung
                    }
        except Exception:
            # DB not initialized yet
            pass
        return {'module_colors': module_colors}

    # Context processor for help texts
    @app.context_processor
    def inject_help_text_function():
        """Make get_help_text function available in all templates."""
        def get_help_text(schluessel):
            """Retrieve a help text by its key."""
            from app.models import HelpText
            try:
                return HelpText.query.filter_by(schluessel=schluessel, aktiv=True).first()
            except Exception:
                # DB not initialized yet
                return None
        return {'get_help_text': get_help_text}

    return app


def register_cli_commands(app):
    """Register CLI commands."""

    @app.cli.command('seed')
    def seed_command():
        """Seed the database with initial data."""
        from app.models import (
            Lieferant, Config as ConfigModel, Rolle,
            Branche, Verband, HelpText
        )

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
            ('firecrawl_api_key', '', 'Firecrawl API Key für Website-Analyse'),
            ('firecrawl_credit_kosten', '0.005', 'Kosten pro Firecrawl Credit in Euro'),
            # PRD-006: Brevo E-Mail Service
            ('brevo_api_key', '', 'Brevo API Key für E-Mail-Versand'),
            ('brevo_sender_email', 'noreply@e-vendo.de', 'Absender E-Mail-Adresse'),
            ('brevo_sender_name', 'e-vendo AG', 'Absender Name'),
            ('portal_base_url', 'https://portal.e-vendo.de', 'Basis-URL für Portal-Links'),
            # PRD-006: Brevo Rate Limiting (Free Plan: 300/day)
            ('brevo_daily_limit', '300', 'Max. E-Mails pro Tag (Brevo Free Plan)'),
            ('brevo_emails_sent_today', '0', 'Heute gesendete E-Mails (auto-reset)'),
            ('brevo_last_reset_date', '', 'Letztes Quota-Reset-Datum (YYYY-MM-DD)'),
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

        # Create Hauptbranchen (Top-Level Categories)
        hauptbranchen_data = [
            ('HANDEL', 'shopping-cart', 10),
            ('HANDWERK', 'tools', 20),
            ('DIENSTLEISTUNG', 'briefcase', 30),
        ]
        hauptbranchen = {}
        for name, icon, sortierung in hauptbranchen_data:
            existing = Branche.query.filter_by(name=name, parent_id=None).first()
            if not existing:
                branche = Branche(name=name, icon=icon, sortierung=sortierung, aktiv=True)
                db.session.add(branche)
                db.session.flush()  # Get ID for relationship
                hauptbranchen[name] = branche
                click.echo(f'Created Hauptbranche: {name}')
            else:
                hauptbranchen[name] = existing

        # Create Unterbranchen (Sub-Categories) under HANDEL
        handel = hauptbranchen.get('HANDEL')
        if handel:
            unterbranchen_handel = [
                ('Einzelhandel Modellbahn', 'train', 10),
                ('Einzelhandel Spielwaren', 'lego', 20),
                ('Einzelhandel Fahrrad', 'bike', 30),
                ('Einzelhandel GPK', 'glass', 40),
                ('Einzelhandel Geschenkartikel', 'gift', 50),
                ('Großhandel', 'building-warehouse', 60),
                ('Online-Handel', 'world-www', 70),
                ('Fachmarkt', 'building-store', 80),
                ('Babyausstattung', 'baby-carriage', 90),
                ('Schreibwaren', 'pencil', 100),
            ]
            for name, icon, sortierung in unterbranchen_handel:
                existing = Branche.query.filter_by(name=name, parent_id=handel.id).first()
                if not existing:
                    branche = Branche(
                        name=name, icon=icon, sortierung=sortierung,
                        parent_id=handel.id, aktiv=True
                    )
                    db.session.add(branche)
                    click.echo(f'Created Unterbranche: {name} (unter HANDEL)')

        # Create Verbände (Associations)
        verbaende_data = [
            ('VEDES', 'VEDES', 'https://www.vedes.com', None),
            ('idee+spiel', 'I+S', 'https://www.idee-und-spiel.de', None),
            ('Spielwaren-Ring', 'SWR', 'https://www.spielwarenring.de', None),
            ('EK/servicegroup', 'EK', 'https://www.ek-servicegroup.de', None),
            ('expert', 'expert', 'https://www.expert.de', None),
        ]
        for name, kuerzel, website, logo in verbaende_data:
            existing = Verband.query.filter_by(name=name).first()
            if not existing:
                verband = Verband(
                    name=name, kuerzel=kuerzel,
                    website_url=website, logo_url=logo, aktiv=True
                )
                db.session.add(verband)
                click.echo(f'Created Verband: {name}')

        # Create HelpTexts for UI components
        hilfetexte_data = [
            (
                'kunden.detail.stammdaten',
                'Stammdaten',
                '''## Kundenstammdaten

Die Stammdaten enthalten die wichtigsten Informationen zum Kunden:

- **Firmierung**: Offizieller Firmenname
- **e-vendo Kdnr.**: Kundennummer im e-vendo System
- **Adresse**: Geschäftsadresse des Kunden
- **Website & Shop**: Links zur Webpräsenz

Diese Daten können über "Bearbeiten" geändert werden.'''
            ),
            (
                'kunden.detail.branchen',
                'Branchen zuordnen',
                '''## Branchen zuordnen

Ordnen Sie dem Kunden passende Branchen zu, um ihn besser kategorisieren zu können.

### Bedienung

- **Linksklick**: Branche zuordnen oder entfernen
- **Rechtsklick**: Als **Primärbranche** markieren (max. 3)

### Primärbranchen

Primärbranchen werden mit einem **P** markiert und erscheinen in der Kundenliste.
Sie helfen bei der schnellen Identifikation der Hauptgeschäftsfelder.'''
            ),
            (
                'kunden.detail.verbaende',
                'Verbände zuordnen',
                '''## Verbandsmitgliedschaften

Hier können Sie die Verbandszugehörigkeiten des Kunden pflegen.

### Bekannte Verbände

- **VEDES**: Spielwarenverband
- **idee+spiel**: Franchise-System
- **EK/servicegroup**: Einkaufsverband

**Tipp**: Klicken Sie auf einen Verband, um die Mitgliedschaft zu togglen.'''
            ),
            (
                'kunden.detail.ci',
                'Corporate Identity',
                '''## Corporate Identity (CI)

Die CI-Daten werden automatisch von der Kundenwebsite analysiert.

### Analysierte Elemente

- **Logo**: Hauptlogo der Website
- **Farben**: Primaer-, Sekundaer- und Akzentfarben
- **Typografie**: Schriftarten (falls erkennbar)

### Analyse starten

Klicken Sie auf "Website-Analyse", um die CI neu zu erfassen.
Die Analyse nutzt die Firecrawl API.

**Hinweis**: Die Analyse kostet Credits.'''
            ),
        ]
        for schluessel, titel, inhalt in hilfetexte_data:
            existing = HelpText.query.filter_by(schluessel=schluessel).first()
            if not existing:
                help_text = HelpText(
                    schluessel=schluessel,
                    titel=titel,
                    inhalt_markdown=inhalt,
                    aktiv=True
                )
                db.session.add(help_text)
                click.echo(f'Created HelpText: {schluessel}')

        # Create default Email Templates for transactional emails
        from app.models import EmailTemplate

        email_templates_data = [
            {
                'schluessel': 'fragebogen_einladung',
                'name': 'Fragebogen Einladung',
                'beschreibung': 'E-Mail für Einladung zur Fragebogen-Teilnahme',
                'betreff': 'Einladung: {{ fragebogen_titel }}',
                'body_html': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: Arial, sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="background-color: {{ primary_color }}; padding: 30px; text-align: center;">
                            {% if logo_url %}
                            <img src="{{ logo_url }}" alt="{{ portal_name }}" height="40" style="max-height: 40px;">
                            {% else %}
                            <h1 style="color: #ffffff; margin: 0; font-size: 24px;">{{ portal_name }}</h1>
                            {% endif %}
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <h2 style="color: #333333; margin: 0 0 20px 0; font-size: 22px;">Einladung zur Teilnahme</h2>
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
                                Guten Tag,
                            </p>
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 30px 0;">
                                Sie sind eingeladen, an der Befragung <strong style="color: #333333;">{{ fragebogen_titel }}</strong> teilzunehmen.
                            </p>
                            <!-- Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" style="margin: 0 auto 30px auto;">
                                <tr>
                                    <td style="background-color: {{ primary_color }}; border-radius: 6px;">
                                        <a href="{{ link }}" style="display: inline-block; padding: 14px 32px; color: #ffffff; text-decoration: none; font-size: 16px; font-weight: bold;">
                                            Jetzt teilnehmen
                                        </a>
                                    </td>
                                </tr>
                            </table>
                            <p style="color: #999999; font-size: 14px; line-height: 1.6; margin: 0;">
                                Oder kopieren Sie diesen Link:<br>
                                <a href="{{ link }}" style="color: {{ primary_color }}; word-break: break-all;">{{ link }}</a>
                            </p>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 25px 30px; border-top: 1px solid #e9ecef;">
                            <p style="color: #6c757d; font-size: 13px; line-height: 1.5; margin: 0;">
                                {{ footer | safe }}
                            </p>
                            {% if copyright_text %}
                            <p style="color: #999999; font-size: 12px; margin: 15px 0 0 0;">
                                {{ copyright_text }}
                            </p>
                            {% endif %}
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>''',
                'body_text': '''Einladung zur Teilnahme

Guten Tag,

Sie sind eingeladen, an der Befragung "{{ fragebogen_titel }}" teilzunehmen.

Bitte nutzen Sie folgenden Link zur Teilnahme:
{{ link }}

{{ footer }}

{{ copyright_text }}'''
            },
            {
                'schluessel': 'passwort_zugangsdaten',
                'name': 'Zugangsdaten',
                'beschreibung': 'E-Mail mit Passwort-Link für neuen Benutzer',
                'betreff': 'Ihre Zugangsdaten für {{ portal_name }}',
                'body_html': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: Arial, sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="background-color: {{ primary_color }}; padding: 30px; text-align: center;">
                            {% if logo_url %}
                            <img src="{{ logo_url }}" alt="{{ portal_name }}" height="40" style="max-height: 40px;">
                            {% else %}
                            <h1 style="color: #ffffff; margin: 0; font-size: 24px;">{{ portal_name }}</h1>
                            {% endif %}
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <h2 style="color: #333333; margin: 0 0 20px 0; font-size: 22px;">Willkommen bei {{ portal_name }}</h2>
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
                                Guten Tag{% if vorname %} {{ vorname }}{% endif %},
                            </p>
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                                Für Sie wurde ein Benutzerkonto erstellt. Bitte vergeben Sie jetzt Ihr persönliches Passwort.
                            </p>
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 30px 0;">
                                <strong>Ihre E-Mail-Adresse:</strong> {{ email }}
                            </p>
                            <!-- Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" style="margin: 0 auto 30px auto;">
                                <tr>
                                    <td style="background-color: {{ primary_color }}; border-radius: 6px;">
                                        <a href="{{ link }}" style="display: inline-block; padding: 14px 32px; color: #ffffff; text-decoration: none; font-size: 16px; font-weight: bold;">
                                            Passwort festlegen
                                        </a>
                                    </td>
                                </tr>
                            </table>
                            <p style="color: #dc3545; font-size: 14px; line-height: 1.6; margin: 0 0 15px 0;">
                                <strong>Wichtig:</strong> Dieser Link ist nur 24 Stunden gültig.
                            </p>
                            <p style="color: #999999; font-size: 14px; line-height: 1.6; margin: 0;">
                                Falls der Button nicht funktioniert, kopieren Sie diesen Link:<br>
                                <a href="{{ link }}" style="color: {{ primary_color }}; word-break: break-all;">{{ link }}</a>
                            </p>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 25px 30px; border-top: 1px solid #e9ecef;">
                            <p style="color: #6c757d; font-size: 13px; line-height: 1.5; margin: 0;">
                                {{ footer | safe }}
                            </p>
                            {% if copyright_text %}
                            <p style="color: #999999; font-size: 12px; margin: 15px 0 0 0;">
                                {{ copyright_text }}
                            </p>
                            {% endif %}
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>''',
                'body_text': '''Willkommen bei {{ portal_name }}

Guten Tag{% if vorname %} {{ vorname }}{% endif %},

Für Sie wurde ein Benutzerkonto erstellt. Bitte vergeben Sie jetzt Ihr persönliches Passwort.

Ihre E-Mail-Adresse: {{ email }}

Klicken Sie auf folgenden Link, um Ihr Passwort festzulegen:
{{ link }}

WICHTIG: Dieser Link ist nur 24 Stunden gültig.

{{ footer }}

{{ copyright_text }}'''
            },
            {
                'schluessel': 'passwort_reset',
                'name': 'Passwort zurücksetzen',
                'beschreibung': 'E-Mail für Passwort-Reset-Anforderung',
                'betreff': 'Neues Passwort für {{ portal_name }}',
                'body_html': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: Arial, sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="background-color: {{ primary_color }}; padding: 30px; text-align: center;">
                            {% if logo_url %}
                            <img src="{{ logo_url }}" alt="{{ portal_name }}" height="40" style="max-height: 40px;">
                            {% else %}
                            <h1 style="color: #ffffff; margin: 0; font-size: 24px;">{{ portal_name }}</h1>
                            {% endif %}
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <h2 style="color: #333333; margin: 0 0 20px 0; font-size: 22px;">Passwort zurücksetzen</h2>
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
                                Guten Tag,
                            </p>
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 30px 0;">
                                Sie haben ein neues Passwort für Ihr Konto bei {{ portal_name }} angefordert.
                            </p>
                            <!-- Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" style="margin: 0 auto 30px auto;">
                                <tr>
                                    <td style="background-color: {{ primary_color }}; border-radius: 6px;">
                                        <a href="{{ link }}" style="display: inline-block; padding: 14px 32px; color: #ffffff; text-decoration: none; font-size: 16px; font-weight: bold;">
                                            Neues Passwort festlegen
                                        </a>
                                    </td>
                                </tr>
                            </table>
                            <p style="color: #dc3545; font-size: 14px; line-height: 1.6; margin: 0 0 15px 0;">
                                <strong>Wichtig:</strong> Dieser Link ist nur 1 Stunde gültig.
                            </p>
                            <p style="color: #999999; font-size: 14px; line-height: 1.6; margin: 0 0 15px 0;">
                                Falls der Button nicht funktioniert, kopieren Sie diesen Link:<br>
                                <a href="{{ link }}" style="color: {{ primary_color }}; word-break: break-all;">{{ link }}</a>
                            </p>
                            <p style="color: #999999; font-size: 14px; line-height: 1.6; margin: 0;">
                                Falls Sie diese Anforderung nicht gestellt haben, ignorieren Sie diese E-Mail. Ihr Passwort bleibt unverändert.
                            </p>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 25px 30px; border-top: 1px solid #e9ecef;">
                            <p style="color: #6c757d; font-size: 13px; line-height: 1.5; margin: 0;">
                                {{ footer | safe }}
                            </p>
                            {% if copyright_text %}
                            <p style="color: #999999; font-size: 12px; margin: 15px 0 0 0;">
                                {{ copyright_text }}
                            </p>
                            {% endif %}
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>''',
                'body_text': '''Passwort zurücksetzen

Guten Tag,

Sie haben ein neues Passwort für Ihr Konto bei {{ portal_name }} angefordert.

Klicken Sie auf folgenden Link, um ein neues Passwort festzulegen:
{{ link }}

WICHTIG: Dieser Link ist nur 1 Stunde gültig.

Falls Sie diese Anforderung nicht gestellt haben, ignorieren Sie diese E-Mail. Ihr Passwort bleibt unverändert.

{{ footer }}

{{ copyright_text }}'''
            },
            {
                'schluessel': 'test_email',
                'name': 'Test E-Mail',
                'beschreibung': 'Test-E-Mail aus Systemeinstellungen',
                'betreff': 'Test E-Mail von {{ portal_name }}',
                'body_html': '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f5f5f5; font-family: Arial, sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f5f5f5;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <!-- Header -->
                    <tr>
                        <td style="background-color: {{ primary_color }}; padding: 30px; text-align: center;">
                            {% if logo_url %}
                            <img src="{{ logo_url }}" alt="{{ portal_name }}" height="40" style="max-height: 40px;">
                            {% else %}
                            <h1 style="color: #ffffff; margin: 0; font-size: 24px;">{{ portal_name }}</h1>
                            {% endif %}
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <h2 style="color: #333333; margin: 0 0 20px 0; font-size: 22px;">✅ E-Mail-Konfiguration erfolgreich</h2>
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
                                Dies ist eine Test-E-Mail von {{ portal_name }}.
                            </p>
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                                Wenn Sie diese E-Mail erhalten haben, ist die Brevo-Integration korrekt konfiguriert.
                            </p>
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="10" style="background-color: #f8f9fa; border-radius: 6px; margin: 20px 0;">
                                <tr>
                                    <td style="color: #666666; font-size: 14px;">
                                        <strong>Branding-Test:</strong><br>
                                        • Primärfarbe: {{ primary_color }}<br>
                                        • Sekundärfarbe: {{ secondary_color }}<br>
                                        • Portal-Name: {{ portal_name }}<br>
                                        • Logo: {% if logo_url %}Konfiguriert{% else %}Nicht konfiguriert{% endif %}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f8f9fa; padding: 25px 30px; border-top: 1px solid #e9ecef;">
                            <p style="color: #6c757d; font-size: 13px; line-height: 1.5; margin: 0;">
                                {{ footer | safe }}
                            </p>
                            {% if copyright_text %}
                            <p style="color: #999999; font-size: 12px; margin: 15px 0 0 0;">
                                {{ copyright_text }}
                            </p>
                            {% endif %}
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>''',
                'body_text': '''E-Mail-Konfiguration erfolgreich

Dies ist eine Test-E-Mail von {{ portal_name }}.

Wenn Sie diese E-Mail erhalten haben, ist die Brevo-Integration korrekt konfiguriert.

Branding-Test:
- Primärfarbe: {{ primary_color }}
- Sekundärfarbe: {{ secondary_color }}
- Portal-Name: {{ portal_name }}
- Logo: {% if logo_url %}Konfiguriert{% else %}Nicht konfiguriert{% endif %}

{{ footer }}

{{ copyright_text }}'''
            },
        ]

        for template_data in email_templates_data:
            existing = EmailTemplate.query.filter_by(schluessel=template_data['schluessel']).first()
            if not existing:
                template = EmailTemplate(
                    schluessel=template_data['schluessel'],
                    name=template_data['name'],
                    beschreibung=template_data['beschreibung'],
                    betreff=template_data['betreff'],
                    body_html=template_data['body_html'],
                    body_text=template_data.get('body_text'),
                    aktiv=True
                )
                db.session.add(template)
                click.echo(f"Created EmailTemplate: {template_data['schluessel']}")
            else:
                click.echo(f"EmailTemplate already exists: {template_data['schluessel']}")

        # Create Module (unified module management - replaces SubApp)
        from app.models import Modul, ModulZugriff, ModulTyp
        # Format: (code, name, beschreibung, icon, color, color_hex, route_endpoint, sort_order, typ, zeige_dashboard)
        # typ: basis, kundenprojekt, sales_intern, consulting_intern, premium
        module_data = [
            # Basis-Module (always active, not on dashboard) - puzzle icon
            ('system', 'System & Administration', 'Systemeinstellungen und Benutzerverwaltung',
             'ti-puzzle', 'secondary', '#6c757d', None, 0, ModulTyp.BASIS.value, False),
            ('stammdaten', 'Stammdatenpflege', 'Lieferanten, Hersteller, Marken verwalten',
             'ti-puzzle', 'secondary', '#6c757d', None, 1, ModulTyp.BASIS.value, False),
            ('logging', 'Audit-Log', 'Systemereignisse protokollieren',
             'ti-puzzle', 'secondary', '#6c757d', None, 2, ModulTyp.BASIS.value, False),
            ('auth', 'Authentifizierung', 'Login und Benutzersitzungen',
             'ti-puzzle', 'secondary', '#6c757d', None, 3, ModulTyp.BASIS.value, False),
            # Dashboard modules with different types
            ('pricat', 'PRICAT Converter', 'VEDES PRICAT-Dateien zu Elena-Format konvertieren',
             'ti-route-square', 'primary', '#0d6efd', 'main.lieferanten', 10, ModulTyp.CONSULTING_INTERN.value, True),
            ('kunden', 'Lead & Kundenreport', 'Kunden verwalten und Website-Analyse',
             'ti-users', 'success', '#198754', 'kunden.liste', 20, ModulTyp.SALES_INTERN.value, True),
            ('lieferanten', 'Meine Lieferanten', 'Relevante Lieferanten auswählen',
             'ti-truck', 'info', '#0dcaf0', 'lieferanten_auswahl.index', 30, ModulTyp.KUNDENPROJEKT.value, True),
            ('content', 'Content Generator', 'KI-generierte Texte für Online-Shops',
             'ti-writing', 'warning', '#ffc107', 'content_generator.index', 40, ModulTyp.PREMIUM.value, True),
            # PRD-006: Kunden-Dialog Modul
            ('dialog', 'Kunden-Dialog', 'Fragebögen erstellen und Kunden befragen',
             'ti-messages', 'teal', '#20c997', 'dialog.index', 50, ModulTyp.KUNDENPROJEKT.value, True),
        ]
        for code, name, beschreibung, icon, color, color_hex, route_endpoint, sort_order, typ, zeige_dashboard in module_data:
            existing = Modul.query.filter_by(code=code).first()
            if not existing:
                modul = Modul(
                    code=code, name=name, beschreibung=beschreibung,
                    icon=icon, color=color, color_hex=color_hex,
                    route_endpoint=route_endpoint, sort_order=sort_order,
                    typ=typ, zeige_dashboard=zeige_dashboard, aktiv=True
                )
                db.session.add(modul)
                click.echo(f'Created Modul: {code} ({name}) [typ={typ}]')
            else:
                # Update existing Modul with new fields
                existing.beschreibung = beschreibung
                existing.icon = icon
                existing.color = color
                existing.color_hex = color_hex
                existing.route_endpoint = route_endpoint
                existing.sort_order = sort_order
                existing.typ = typ
                existing.zeige_dashboard = zeige_dashboard
                click.echo(f'Updated Modul: {code} ({name}) [typ={typ}]')
        db.session.flush()

        # Create ModulZugriff mappings (role-based module access)
        modul_access_mappings = [
            ('pricat', ['admin', 'mitarbeiter']),
            ('kunden', ['admin', 'mitarbeiter']),
            ('lieferanten', ['admin', 'mitarbeiter', 'kunde']),
            ('content', ['admin', 'mitarbeiter', 'kunde']),
            # PRD-006: Kunden-Dialog
            ('dialog', ['admin', 'mitarbeiter', 'kunde']),
        ]
        for code, role_names in modul_access_mappings:
            modul = Modul.query.filter_by(code=code).first()
            if modul:
                for role_name in role_names:
                    rolle = roles.get(role_name)
                    if rolle:
                        existing_access = ModulZugriff.query.filter_by(
                            modul_id=modul.id, rolle_id=rolle.id
                        ).first()
                        if not existing_access:
                            access = ModulZugriff(modul_id=modul.id, rolle_id=rolle.id)
                            db.session.add(access)
                            click.echo(f'Created ModulZugriff: {code} -> {role_name}')

        # PRD-006: Create example V2 questionnaire "Kunden-Anforderungen"
        from app.models import Fragebogen, FragebogenStatus, User

        # Find an admin user for creating the fragebogen (use first admin or skip)
        admin_rolle = roles.get('admin')
        admin_user = User.query.filter_by(rolle_id=admin_rolle.id).first() if admin_rolle else None

        kunden_anforderungen_json = {
            "version": 2,
            "seiten": [
                {
                    "id": "s1",
                    "titel": "1. Allgemeine Fragen zum Unternehmen",
                    "hilfetext": "Diese Informationen helfen uns, Ihr Unternehmen besser kennenzulernen.",
                    "fragen": [
                        {
                            "id": "firmierung",
                            "typ": "text",
                            "frage": "Firmierung",
                            "pflicht": True,
                            "prefill": "kunde.firmierung"
                        },
                        {
                            "id": "rechtsform",
                            "typ": "dropdown",
                            "frage": "Rechtsform",
                            "optionen": ["GmbH", "GmbH & Co. KG", "AG", "e.K.", "OHG", "KG", "Einzelunternehmen", "Sonstige"],
                            "pflicht": True
                        },
                        {
                            "id": "adresse",
                            "typ": "group",
                            "frage": "Adresse",
                            "fields": [
                                {"id": "strasse", "label": "Straße", "typ": "text", "width": "70%", "prefill": "kunde.strasse"},
                                {"id": "hausnummer", "label": "Nr.", "typ": "text", "width": "30%", "prefill": "kunde.hausnummer"}
                            ]
                        },
                        {
                            "id": "plz_ort",
                            "typ": "group",
                            "frage": "",
                            "fields": [
                                {"id": "plz", "label": "PLZ", "typ": "text", "width": "30%", "prefill": "kunde.plz"},
                                {"id": "ort", "label": "Ort", "typ": "text", "width": "70%", "prefill": "kunde.ort"}
                            ]
                        },
                        {
                            "id": "ansprechpartner",
                            "typ": "group",
                            "frage": "Ansprechpartner",
                            "fields": [
                                {"id": "vorname", "label": "Vorname", "typ": "text", "width": "50%"},
                                {"id": "nachname", "label": "Nachname", "typ": "text", "width": "50%"}
                            ]
                        },
                        {
                            "id": "telefon",
                            "typ": "text",
                            "frage": "Telefon",
                            "prefill": "kunde.telefon"
                        },
                        {
                            "id": "email",
                            "typ": "text",
                            "frage": "E-Mail",
                            "prefill": "kunde.email"
                        },
                        {
                            "id": "branche",
                            "typ": "dropdown",
                            "frage": "Haupt-Branche",
                            "optionen": ["Spielwaren", "Schreibwaren", "Haushaltswaren", "Sonstige"],
                            "freifeld": True,
                            "hilfetext": "Wählen Sie Ihre Hauptbranche oder geben Sie eine eigene ein"
                        },
                        {
                            "id": "verbaende",
                            "typ": "multiple_choice",
                            "frage": "Mitglied in Einkaufsverbänden",
                            "optionen": ["VEDES", "EK/servicegroup", "Spielwaren Ring", "Keiner"],
                            "hilfetext": "Mehrfachauswahl möglich"
                        },
                        {
                            "id": "anzahl_mitarbeiter",
                            "typ": "number",
                            "frage": "Anzahl Mitarbeiter",
                            "min": 1
                        },
                        {
                            "id": "anzahl_pc",
                            "typ": "number",
                            "frage": "Anzahl PC Arbeitsplätze",
                            "min": 1
                        },
                        {
                            "id": "startdatum",
                            "typ": "date",
                            "frage": "Gewünschtes Startdatum",
                            "min_date": "today"
                        },
                        {
                            "id": "aktuelle_wawi",
                            "typ": "dropdown",
                            "frage": "Aktuelle Warenwirtschaft",
                            "optionen": ["Keine", "JTL", "plentymarkets", "Sage", "SAP", "Andere"],
                            "freifeld": True
                        }
                    ]
                },
                {
                    "id": "s2",
                    "titel": "2. Geschäftstyp",
                    "hilfetext": "Beschreiben Sie Ihre Vertriebskanäle.",
                    "fragen": [
                        {
                            "id": "verkauf_stationaer",
                            "typ": "ja_nein",
                            "frage": "Verkauf stationär?"
                        },
                        {
                            "id": "anzahl_filialen",
                            "typ": "number",
                            "frage": "Anzahl Filialen",
                            "show_if": {"frage_id": "verkauf_stationaer", "equals": True},
                            "min": 1
                        },
                        {
                            "id": "kassen_info",
                            "typ": "group",
                            "frage": "Kasseninformationen",
                            "show_if": {"frage_id": "verkauf_stationaer", "equals": True},
                            "fields": [
                                {"id": "anzahl_kassen", "label": "Anzahl Kassen", "typ": "number", "width": "50%"},
                                {"id": "verkauefe_tag", "label": "Verkäufe/Tag", "typ": "number", "width": "50%"}
                            ]
                        },
                        {
                            "id": "anmeldung",
                            "typ": "single_choice",
                            "frage": "Kassenanmeldung",
                            "show_if": {"frage_id": "verkauf_stationaer", "equals": True},
                            "optionen": ["Dummy-User", "Konkreter Mitarbeiter"]
                        },
                        {
                            "id": "ma_wechsel",
                            "typ": "ja_nein",
                            "frage": "MA-Wechsel an Kasse",
                            "show_if": {"frage_id": "verkauf_stationaer", "equals": True}
                        },
                        {
                            "id": "ec_terminals",
                            "typ": "ja_nein",
                            "frage": "EC-Terminals angebunden",
                            "show_if": {"frage_id": "verkauf_stationaer", "equals": True}
                        },
                        {
                            "id": "kundendisplay",
                            "typ": "ja_nein",
                            "frage": "Kundendisplay angebunden",
                            "show_if": {"frage_id": "verkauf_stationaer", "equals": True}
                        },
                        {
                            "id": "verkauf_online",
                            "typ": "ja_nein",
                            "frage": "Verkauf online?"
                        },
                        {
                            "id": "onlineshop_system",
                            "typ": "dropdown",
                            "frage": "Onlineshop-System",
                            "show_if": {"frage_id": "verkauf_online", "equals": True},
                            "optionen": ["Shopware", "WooCommerce", "Magento", "Shopify", "Andere"],
                            "freifeld": True
                        },
                        {
                            "id": "marktplaetze",
                            "typ": "multiple_choice",
                            "frage": "Aktive Marktplätze",
                            "show_if": {"frage_id": "verkauf_online", "equals": True},
                            "optionen": ["Amazon", "eBay", "Otto", "Kaufland", "Keine"],
                            "hilfetext": "Wählen Sie alle genutzten Marktplätze"
                        },
                        {
                            "id": "website_url",
                            "typ": "url",
                            "frage": "Website-URL",
                            "placeholder": "https://www.ihre-website.de"
                        },
                        {
                            "id": "shop_url",
                            "typ": "url",
                            "frage": "Onlineshop-URL",
                            "show_if": {"frage_id": "verkauf_online", "equals": True},
                            "placeholder": "https://shop.ihre-website.de"
                        }
                    ]
                },
                {
                    "id": "s3",
                    "titel": "3. Weitere Informationen",
                    "hilfetext": "Optionale Zusatzinformationen für eine bessere Beratung.",
                    "fragen": [
                        {
                            "id": "besondere_anforderungen",
                            "typ": "text",
                            "frage": "Besondere Anforderungen oder Wünsche",
                            "multiline": True,
                            "hilfetext": "Beschreiben Sie hier, was Ihnen besonders wichtig ist"
                        },
                        {
                            "id": "zeitrahmen",
                            "typ": "single_choice",
                            "frage": "Gewünschter Zeitrahmen für Umsetzung",
                            "optionen": ["Sofort", "In 1-3 Monaten", "In 3-6 Monaten", "In 6-12 Monaten", "Flexibel"]
                        },
                        {
                            "id": "budget_rahmen",
                            "typ": "single_choice",
                            "frage": "Budgetrahmen",
                            "optionen": ["Unter 5.000 €", "5.000 - 15.000 €", "15.000 - 50.000 €", "Über 50.000 €", "Noch unklar"],
                            "hilfetext": "Eine grobe Einschätzung hilft uns bei der Planung"
                        },
                        {
                            "id": "kontakt_praeferenz",
                            "typ": "single_choice",
                            "frage": "Bevorzugte Kontaktaufnahme",
                            "optionen": ["Telefon", "E-Mail", "Videocall", "Persönliches Treffen"]
                        },
                        {
                            "id": "datenschutz_akzeptiert",
                            "typ": "ja_nein",
                            "frage": "Ich stimme der Verarbeitung meiner Daten gemäß Datenschutzerklärung zu",
                            "pflicht": True
                        }
                    ]
                }
            ]
        }

        existing_fb = Fragebogen.query.filter_by(titel='Kunden-Anforderungen').first()
        if not existing_fb:
            if admin_user:
                fragebogen = Fragebogen(
                    titel='Kunden-Anforderungen',
                    beschreibung='Erfassung der Anforderungen für neue Kunden - inkl. Unternehmensinfo, Vertriebskanäle und Projektwünsche.',
                    definition_json=kunden_anforderungen_json,
                    status=FragebogenStatus.ENTWURF.value,
                    erstellt_von_id=admin_user.id
                )
                db.session.add(fragebogen)
                click.echo('Created Fragebogen: Kunden-Anforderungen (V2 mit 3 Seiten)')
            else:
                click.echo('Skipped Fragebogen: No admin user exists yet. Run "flask seed-users" first.')
        else:
            click.echo('Fragebogen already exists: Kunden-Anforderungen')

        db.session.commit()
        click.echo('Database seeded successfully!')

    @app.cli.command('init-db')
    def init_db_command():
        """Initialize the database."""
        db.create_all()
        click.echo('Database initialized!')

    @app.cli.command('reset-db')
    def reset_db_command():
        """Drop all tables and recreate them. USE WITH CAUTION!

        Requires DB_RESET=true environment variable as safety measure.
        """
        import os
        if os.environ.get('DB_RESET', '').lower() != 'true':
            click.echo('ERROR: DB_RESET environment variable must be set to "true"')
            click.echo('This is a safety measure to prevent accidental data loss.')
            click.echo('')
            click.echo('Usage: DB_RESET=true flask reset-db')
            return

        click.echo('=' * 50)
        click.echo('WARNING: Dropping ALL tables...')
        click.echo('=' * 50)
        db.drop_all()
        click.echo('All tables dropped.')

        click.echo('Creating all tables...')
        db.create_all()
        click.echo('All tables created.')

        click.echo('')
        click.echo('Database reset complete!')
        click.echo('Run "flask seed" and "flask seed-users" to populate data.')

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
