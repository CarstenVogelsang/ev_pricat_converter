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
    from app.routes.support import support_bp
    from app.routes.support_admin import support_admin_bp
    from app.routes.schulungen import schulungen_bp
    from app.routes.schulungen_admin import schulungen_admin_bp
    from app.routes.api_projekte import api_projekte_bp
    from app.routes.projekte_admin import projekte_admin_bp
    from app.routes.api_upload import api_upload_bp
    from app.routes.mailing_admin import mailing_admin_bp
    from app.routes.mailing import mailing_bp

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
    # PRD-007: Anwender-Support
    app.register_blueprint(support_bp)
    app.register_blueprint(support_admin_bp)
    # PRD-010: Schulungen
    app.register_blueprint(schulungen_bp)
    app.register_blueprint(schulungen_admin_bp)
    # PRD-011: Projektverwaltung
    app.register_blueprint(api_projekte_bp)
    csrf.exempt(api_projekte_bp)  # API-Endpoints brauchen kein CSRF (für Claude Code)
    app.register_blueprint(projekte_admin_bp)
    # Markdown Image Upload API
    app.register_blueprint(api_upload_bp)
    # PRD-013: Kunden-Mailing
    app.register_blueprint(mailing_admin_bp)
    app.register_blueprint(mailing_bp)  # Öffentliche Routes (Tracking, Abmeldung)

    # =========================================================================
    # Admin Page Visit Tracking (for "Recently Visited" Quick Links)
    # =========================================================================
    # Page title mapping for human-readable display
    ADMIN_PAGE_TITLES = {
        # Main sections
        'admin.system': 'System',
        'admin.module_uebersicht': 'Module',
        'admin.stammdaten_uebersicht': 'Stammdaten',
        'admin.einstellungen_uebersicht': 'Einstellungen',
        # Stammdaten
        'admin.betreiber': 'Betreiber',
        'admin.branding': 'Branding',
        'admin.lieferanten': 'Lieferanten',
        'admin.rollen': 'Rollen',
        'admin.branchen': 'Branchen',
        'admin.verbaende': 'Verbände',
        'admin.hilfetexte': 'Hilfetexte',
        # Modules
        'admin.pricat': 'PRICAT Converter',
        'admin.kunden_report': 'Lead & Kundenreport',
        'admin.lieferanten_auswahl': 'Meine Lieferanten',
        'admin.content_generator': 'Content Generator',
        # Dialog module
        'dialog_admin.index': 'Fragebögen',
        'dialog_admin.einstellungen': 'Dialog-Einstellungen',
        'dialog_admin.edit': 'Fragebogen bearbeiten',
        'dialog_admin.detail': 'Fragebogen-Details',
        # Schulungen module
        'schulungen_admin.index': 'Schulungen',
        'schulungen_admin.einstellungen': 'Schulungen-Einstellungen',
        'schulungen_admin.detail': 'Schulung-Details',
        # Projektverwaltung module
        'projekte_admin.index': 'Projekte',
        'projekte_admin.einstellungen': 'Projekt-Einstellungen',
        'projekte_admin.projekt_detail': 'Projekt-Details',
        'projekte_admin.komponente_detail': 'Komponente-Details',
        # Mailing module
        'mailing_admin.index': 'Mailings',
        'mailing_admin.einstellungen': 'Mailing-Einstellungen',
        'mailing_admin.detail': 'Mailing-Details',
        'mailing_admin.editor': 'Mailing-Editor',
        'mailing_admin.senden': 'Mailing senden',
        'mailing_admin.statistik': 'Mailing-Statistik',
        # Kunden
        'kunden.liste': 'Kunden-Liste',
        'kunden.detail': 'Kunden-Details',
        # Support
        'support_admin.index': 'Anwender-Support',
        # Benutzer
        'benutzer.liste': 'Benutzer-Liste',
        'benutzer.detail': 'Benutzer-Details',
    }

    def get_admin_page_title(endpoint):
        """Get human-readable title for an admin endpoint."""
        if not endpoint:
            return 'Unbekannt'
        if endpoint in ADMIN_PAGE_TITLES:
            return ADMIN_PAGE_TITLES[endpoint]
        # Fallback: Create title from endpoint name
        parts = endpoint.split('.')
        if len(parts) >= 2:
            return parts[-1].replace('_', ' ').title()
        return endpoint.title()

    @app.before_request
    def track_admin_page_visit():
        """Track page visits in admin area for 'Recently Visited' feature."""
        from flask_login import current_user
        from flask import request
        from app.models import AdminPageVisit

        # Skip if not authenticated
        if not current_user.is_authenticated:
            return
        # Skip non-GET requests (only track page views)
        if request.method != 'GET':
            return
        # Skip if no endpoint (static files, etc.)
        if not request.endpoint:
            return
        # Only track admin-related endpoints
        admin_prefixes = ('admin.', 'dialog_admin.', 'schulungen_admin.',
                          'projekte_admin.', 'mailing_admin.', 'support_admin.',
                          'benutzer.', 'kunden.', 'dbadmin.')
        if not any(request.endpoint.startswith(prefix) for prefix in admin_prefixes):
            return
        # Skip API and AJAX endpoints
        if 'api' in request.endpoint or request.is_json:
            return

        try:
            # Check if last visit was same endpoint (avoid duplicates)
            last_visit = AdminPageVisit.query.filter_by(
                user_id=current_user.id
            ).order_by(AdminPageVisit.timestamp.desc()).first()

            if last_visit and last_visit.endpoint == request.endpoint:
                # Same page as last visit - update timestamp instead of creating new
                last_visit.timestamp = datetime.utcnow()
                last_visit.page_url = request.path  # URL might have changed (query params)
                db.session.commit()
                return

            # Create new visit entry
            visit = AdminPageVisit(
                user_id=current_user.id,
                endpoint=request.endpoint,
                page_url=request.path,
                page_title=get_admin_page_title(request.endpoint)
            )
            db.session.add(visit)
            db.session.commit()

            # Cleanup old entries (keep max 50 per user)
            visit_count = AdminPageVisit.query.filter_by(
                user_id=current_user.id
            ).count()
            if visit_count > 50:
                old_visits = AdminPageVisit.query.filter_by(
                    user_id=current_user.id
                ).order_by(AdminPageVisit.timestamp.asc()).limit(visit_count - 50).all()
                for old_visit in old_visits:
                    db.session.delete(old_visit)
                db.session.commit()
        except Exception:
            # Don't let tracking errors break the app
            db.session.rollback()

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

    # Context processor for recently visited admin pages
    @app.context_processor
    def inject_recent_admin_pages():
        """Inject recently visited admin pages into all templates."""
        from flask_login import current_user
        from app.models import AdminPageVisit
        from sqlalchemy import func

        if not current_user.is_authenticated:
            return {'recent_admin_pages': []}

        try:
            # Get unique recent pages (deduplicated by endpoint, ordered by most recent)
            # Using a subquery to get the latest visit per endpoint
            subquery = db.session.query(
                AdminPageVisit.endpoint,
                func.max(AdminPageVisit.timestamp).label('latest_timestamp')
            ).filter_by(
                user_id=current_user.id
            ).group_by(
                AdminPageVisit.endpoint
            ).subquery()

            recent = db.session.query(AdminPageVisit).join(
                subquery,
                db.and_(
                    AdminPageVisit.endpoint == subquery.c.endpoint,
                    AdminPageVisit.timestamp == subquery.c.latest_timestamp
                )
            ).filter(
                AdminPageVisit.user_id == current_user.id
            ).order_by(
                AdminPageVisit.timestamp.desc()
            ).limit(3).all()

            return {'recent_admin_pages': recent}
        except Exception:
            return {'recent_admin_pages': []}

    return app


def register_cli_commands(app):
    """Register CLI commands."""

    @app.cli.command('seed-essential')
    def seed_essential_command():
        """Seed minimum required data (roles + 1 admin user from ENV).

        This is the FIRST command to run on a fresh installation.
        Creates only what's needed to log in.

        Required ENV variables:
            INITIAL_ADMIN_EMAIL: Email for the initial admin user

        Optional ENV variables:
            INITIAL_ADMIN_PASSWORD: Password (default: admin123)
        """
        from app.models import Rolle, User

        click.echo('=' * 50)
        click.echo('Seeding ESSENTIAL data (roles + admin)...')
        click.echo('=' * 50)

        # 1. Create roles (absolute minimum)
        roles_data = [
            ('admin', 'Vollzugriff auf alle Funktionen'),
            ('mitarbeiter', 'e-vendo Mitarbeiter'),
            ('kunde', 'Externer Kunde'),
        ]
        for name, beschreibung in roles_data:
            if not Rolle.query.filter_by(name=name).first():
                rolle = Rolle(name=name, beschreibung=beschreibung)
                db.session.add(rolle)
                click.echo(f'✓ Created role: {name}')
            else:
                click.echo(f'  Role exists: {name}')
        db.session.flush()

        # 2. Create admin user from ENV
        admin_email = os.environ.get('INITIAL_ADMIN_EMAIL')
        if not admin_email:
            click.echo('')
            click.echo('WARNING: INITIAL_ADMIN_EMAIL not set!')
            click.echo('No admin user created. Set this ENV variable and run again.')
            click.echo('')
            db.session.commit()
            return

        if not User.query.filter_by(email=admin_email).first():
            admin_rolle = Rolle.query.filter_by(name='admin').first()
            password = os.environ.get('INITIAL_ADMIN_PASSWORD', 'admin123')

            user = User(
                email=admin_email,
                vorname='Admin',
                nachname='User',
                rolle_id=admin_rolle.id,
                aktiv=True
            )
            user.set_password(password)
            db.session.add(user)
            click.echo(f'✓ Created admin user: {admin_email}')

            if password == 'admin123':
                click.echo('')
                click.echo('⚠️  Using default password "admin123"')
                click.echo('   Set INITIAL_ADMIN_PASSWORD for production!')
        else:
            click.echo(f'  Admin user exists: {admin_email}')

        db.session.commit()
        click.echo('')
        click.echo('Essential seeding complete!')
        click.echo('Next: Run "flask seed-stammdaten" for production data.')

    @app.cli.command('seed-stammdaten')
    def seed_stammdaten_command():
        """Seed production master data (Branchen, Verbände, Hilfetexte, Config).

        Run AFTER seed-essential. Does NOT create:
        - Roles (use seed-essential)
        - Users (use seed-essential or seed-demo)
        - Test data (use seed-demo)
        """
        from app.models import (
            Config as ConfigModel, Rolle,
            Branche, Verband, HelpText
        )

        click.echo('=' * 50)
        click.echo('Seeding STAMMDATEN (master data)...')
        click.echo('=' * 50)

        # Check if essential seed was run
        if not Rolle.query.filter_by(name='admin').first():
            click.echo('ERROR: Roles not found. Run "flask seed-essential" first!')
            return

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
            # PRD-011: Projektverwaltung KI-Prompt
            ('projektverwaltung_ki_prompt_suffix', '''Bei Unklarheiten zur Anforderung bitte Rückfragen stellen. Nach Erledigung den Task via API auf "Review" setzen:
`curl -X PATCH http://localhost:5001/api/tasks/{task_id} -H "Content-Type: application/json" -d '{"status": "review"}'`

Falls "Bei Erledigung Changelog-Eintrag erstellen" aktiviert ist, wird automatisch ein Changelog erstellt.''', 'KI-Prompt Suffix für Projektverwaltung Tasks'),
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
            ('VEDES', 'vedes', 'https://www.vedes.com', None),
            ('idee+spiel', 'ius', 'https://www.idee-und-spiel.de', None),
            ('EK/servicegroup', 'ek', 'https://www.ek-servicegroup.de', None),
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
            # Betreiber / Branding Hilfetexte
            (
                'admin.betreiber.modul',
                'Betreiber & Branding',
                '''Auf dieser Seite verwalten Sie das **Erscheinungsbild** (Branding) des gesamten Portals.

**Was können Sie hier tun?**

1. **Betreiber auswählen** – Wählen Sie einen Kunden als "Betreiber", dessen Corporate Identity (Logo, Farben) wird für das Portal übernommen

2. **Branding anpassen** – Passen Sie Logo, Farben und App-Titel nach Ihren Wünschen an

3. **E-Mail-Signatur** – Definieren Sie die Signatur, die unter allen System-E-Mails erscheint

**Wann brauche ich das?**

- Beim erstmaligen Einrichten des Portals
- Wenn Sie das Portal für einen anderen Kunden "umbranden" möchten
- Um die E-Mail-Signatur zu aktualisieren'''
            ),
            (
                'admin.betreiber.auswahl',
                'Betreiber auswählen',
                '''Der **Betreiber** ist der Kunde, dessen Corporate Identity (CI) für das gesamte Portal verwendet wird.

**Was wird übernommen?**

- **Logo**: Wird im Header angezeigt
- **Farben**: Primär- und Sekundärfarbe für das Portal-Design
- **E-Mail-Signatur**: Wird in allen System-E-Mails als Footer verwendet

**Voraussetzung**: Der Kunde muss eine analysierte CI haben. Diese kann über die Kundendetailseite mit "Website-Analyse" erstellt werden.'''
            ),
            (
                'admin.betreiber.branding',
                'Branding-Einstellungen',
                '''Hier können Sie das Portal-Branding anpassen:

- **Logo**: Das Firmenlogo im Header
- **App-Titel**: Name der Anwendung
- **Farben**: Primär- und Sekundärfarbe
- **Copyright**: Footer-Informationen

Die Einstellungen werden automatisch vom gewählten Betreiber übernommen, können aber hier manuell angepasst werden.'''
            ),
            (
                'admin.betreiber.branding.logo',
                'Logo hochladen',
                '''Das Logo wird im Header der Anwendung angezeigt.

**Erlaubte Formate:**

- **PNG** (empfohlen für transparenten Hintergrund)
- **JPG/JPEG**
- **GIF**
- **SVG** (für skalierbare Grafiken)

**Empfehlung**: Maximale Höhe ca. 80px für optimale Darstellung.'''
            ),
            (
                'admin.betreiber.branding.titel',
                'App-Titel',
                '''Der App-Titel wird an folgenden Stellen angezeigt:

- **Header**: Neben dem Logo
- **Browser-Tab**: Als Seitentitel
- **Dokumenten-Titel**: In der Titelzeile

**Standard**: ev247'''
            ),
            (
                'admin.betreiber.branding.farben',
                'Farbeinstellungen',
                '''**Primärfarbe** – Die Hauptfarbe des Portals:
- Header-Hintergrund
- Primäre Buttons
- Links und Akzente

**Sekundärfarbe** – Für sekundäre Elemente:
- Sekundäre Buttons
- Badges und Labels
- Hover-Effekte

**Tipp**: Wählen Sie Farben mit gutem Kontrast für bessere Lesbarkeit.'''
            ),
            (
                'admin.betreiber.branding.copyright',
                'Copyright & Website',
                '''**Copyright-Text**: Erscheint im Footer der Anwendung.
**Beispiel**: © 2025 Musterfirma GmbH

**Link zur Website**: Falls vorhanden, wird die URL aus den Kunden-Daten übernommen. Sie kann hier überschrieben werden.

**Hinweis**: Bei Wechsel des Betreibers wird die URL aus den Kundendaten neu übernommen.'''
            ),
            (
                'admin.betreiber.signatur',
                'E-Mail-Signatur',
                '''Die Signatur erscheint **automatisch am Ende** aller System-E-Mails wie Einladungen, Passwort-Zurücksetzen oder Benachrichtigungen.

**Was sollte enthalten sein?**
- Firmenname und Adresse
- Kontaktdaten: Telefon, E-Mail
- Website-Link
- Optional: Rechtliche Hinweise, Social Media

**Editor-Funktionen**: Nutzen Sie die Toolbar für Fett, Kursiv, Farben, Links und Aufzählungen.

**Hinweis**: Änderungen wirken sich sofort auf alle zukünftigen E-Mails aus.'''
            ),
            (
                'admin.betreiber.branding.font',
                'Schriftart',
                '''Die Schriftart wird aus **Google Fonts** geladen und auf das gesamte Portal angewendet.

**Verfügbare Fonts:**
- **Inter** – Modern, sehr gut lesbar (Standard)
- **Poppins** – Geometrisch, freundlich
- **Roboto** – Google-Standardschrift
- **Open Sans** – Neutral, professionell
- **Lato** – Warm, humanistisch

Alle Fonts unterstützen deutsche Umlaute (ä, ö, ü, ß).

**Tipp**: Wählen Sie eine gut lesbare Schrift, die zu Ihrer Corporate Identity passt.'''
            ),
            (
                'admin.betreiber.branding.secondary_font',
                'Sekundär-Font',
                '''Der Sekundär-Font kann für **Überschriften** oder besondere **Akzente** in Rich-Text-Inhalten verwendet werden.

**Wichtig:** In allen WYSIWYG-Editoren (z.B. E-Mail-Signatur) sind **nur** der Primär- und Sekundär-Font auswählbar – nicht alle verfügbaren Schriftarten.

Falls kein Sekundär-Font gewählt wird, steht im Editor nur der Primär-Font zur Verfügung.

**Empfehlung**: Für einen professionellen Look sollten Primär- und Sekundär-Font gut zueinander passen. Beliebte Kombinationen:
- **Inter** (Fließtext) + **Poppins** (Überschriften)
- **Roboto** (Fließtext) + **Merriweather** (Überschriften)'''
            ),
            # Dialog-Modul Hilfetexte (PRD-006)
            (
                'dialog.index.uebersicht',
                'Fragebogen-Übersicht',
                '''## Fragebogen-Verwaltung

Hier sehen Sie alle Fragebögen, gruppiert nach Status:

- **Entwürfe**: Noch in Bearbeitung, können geändert werden
- **Aktiv**: Teilnehmer können antworten
- **Geschlossen**: Keine Antworten mehr möglich

**Tipp**: Klicken Sie auf einen Fragebogen, um Details zu sehen.'''
            ),
            (
                'dialog.detail.uebersicht',
                'Fragebogen-Detail',
                '''## Fragebogen-Detailansicht

Hier sehen Sie alle Informationen zu diesem Fragebogen:

**Aktionen** (je nach Status):
- **Bearbeiten**: Fragen ändern (nur im Entwurf)
- **Aktivieren**: Fragebogen für Teilnehmer freischalten
- **Teilnehmer verwalten**: Kunden einladen
- **Auswertung**: Antworten analysieren

**Versionierung:**
Über "Neue Version erstellen" können Sie eine Kopie anfertigen, um Änderungen vorzunehmen ohne die Original-Antworten zu verlieren.'''
            ),
            (
                'dialog.detail.fragen',
                'Fragen des Fragebogens',
                '''## Fragenübersicht

Alle Fragen des Fragebogens mit Typ und Optionen.

**Fragetypen:**
- **Text**: Freitext-Antwort
- **Auswahl**: Eine Option wählen
- **Mehrfach**: Mehrere Optionen möglich
- **Skala**: Bewertung auf einer Skala

**Hinweis**: Fragen können nur im Entwurf-Status bearbeitet werden.'''
            ),
            (
                'dialog.detail.version',
                'Versionierung',
                '''## Fragebogen-Versionierung

Fragebögen werden versioniert: **V1 → V2 → V3**

**Warum Versionierung?**
- Änderungen dokumentieren
- Alte Antworten bleiben erhalten
- Vergleich zwischen Versionen möglich

**Neue Version erstellen:**
1. Nur die **neueste Version** kann dupliziert werden
2. Alle Fragen werden übernommen
3. Teilnehmer müssen neu zugeordnet werden'''
            ),
            (
                'dialog.detail.teilnehmer',
                'Teilnehmer-Status',
                '''## Teilnehmer-Übersicht

Zeigt den Fortschritt der Teilnehmer:

- **X / Y abgeschlossen**: X Teilnehmer haben alle Fragen beantwortet
- **Einladungen ausstehend**: Teilnehmer ohne gesendete Einladungs-E-Mail

**Teilnehmer verwalten**: Klicken Sie auf den Link, um Teilnehmer hinzuzufügen oder Einladungen zu senden.'''
            ),
            (
                'dialog.form.fragen_editor',
                'Fragen-Editor',
                '''## Fragen erstellen und bearbeiten

**Neue Frage hinzufügen:**
1. Klicken Sie auf "Frage hinzufügen"
2. Wählen Sie den Fragetyp
3. Geben Sie die Frage ein
4. Bei Auswahl-Fragen: Optionen definieren

**Reihenfolge ändern:**
Ziehen Sie Fragen per Drag & Drop in die gewünschte Reihenfolge.

**Pflichtfragen:**
Markieren Sie wichtige Fragen als Pflicht – Teilnehmer müssen diese beantworten.'''
            ),
            (
                'dialog.teilnehmer.liste',
                'Teilnehmer-Liste',
                '''## Teilnehmer verwalten

**Status-Bedeutung:**
- 🔴 **Offen**: Noch keine Einladung gesendet
- 🟡 **Eingeladen**: Einladung gesendet, noch nicht beantwortet
- 🟢 **Abgeschlossen**: Alle Fragen beantwortet

**Aktionen:**
- **Einladung senden**: E-Mail mit Link zum Fragebogen
- **Erinnerung senden**: Bei überfälligen Teilnehmern
- **Entfernen**: Teilnehmer aus dem Fragebogen löschen'''
            ),
            (
                'dialog.teilnehmer.einladung',
                'Einladungen versenden',
                '''## Einladungs-E-Mails

Teilnehmer erhalten eine personalisierte E-Mail mit:
- Link zum Fragebogen
- Persönlicher Anrede
- Informationen zum Fragebogen

**Wichtig:**
- E-Mails werden über Brevo versendet
- Prüfen Sie die E-Mail-Adresse vor dem Versand
- Einladungen können wiederholt gesendet werden'''
            ),
            (
                'dialog.auswertung.uebersicht',
                'Auswertung',
                '''## Fragebogen-Auswertung

Analysiert alle eingegangenen Antworten:

**Statistiken:**
- Anzahl Teilnehmer / Antworten
- Antwortquote in Prozent
- Durchschnittliche Bewertungen

**Export:**
Die Auswertung kann als CSV oder Excel exportiert werden.

**Tipp**: Für aussagekräftige Ergebnisse sollten mindestens 5 Antworten vorliegen.'''
            ),
            # PRD-011: Task-Klassifizierung Hilfetexte (PRD011-T029: mit Icons)
            (
                'projekte.task.typ',
                'Task-Klassifizierung',
                '''## Task-Klassifizierung

Wähle den passenden Typ für diesen Task:

| | Typ | Beschreibung |
|:---:|-----|--------------|
| <i class="ti ti-sparkles text-info"></i> | **Funktion** | Neuentwicklung einer fachlichen oder technischen Funktion |
| <i class="ti ti-trending-up text-success"></i> | **Verbesserung** | Optimierung bestehender Funktionen (UX, Performance) |
| <i class="ti ti-bug text-danger"></i> | **Fehlerbehebung** | Behebung eines reproduzierbaren Fehlers |
| <i class="ti ti-tool text-secondary"></i> | **Technische Aufgabe** | Refactoring, Architektur, Infrastruktur |
| <i class="ti ti-shield-exclamation text-warning"></i> | **Sicherheitsproblem** | Zugriffskontrolle, Datenschutz, Sicherheitslücken |
| <i class="ti ti-search text-purple"></i> | **Recherche** | Analyse- oder Evaluierungsaufgabe |
| <i class="ti ti-file-text text-dark"></i> | **Dokumentation** | Benutzer- oder Entwickler-Dokumentation |
| <i class="ti ti-test-pipe text-cyan"></i> | **Test / QS** | Tests, Testkonzepte, manuelle Prüfungen |

**Tipp**: Die Klassifizierung hilft bei der Priorisierung und Auswertung von Tasks.'''
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
            else:
                # Update existing entry if content is empty or different
                if not existing.inhalt_markdown or existing.inhalt_markdown.strip() == '':
                    existing.titel = titel
                    existing.inhalt_markdown = inhalt
                    click.echo(f'Updated empty HelpText: {schluessel}')
                elif existing.inhalt_markdown != inhalt:
                    existing.titel = titel
                    existing.inhalt_markdown = inhalt
                    click.echo(f'Updated HelpText: {schluessel}')

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
            {
                'schluessel': 'support_ticket_neu',
                'name': 'Neues Support-Ticket',
                'beschreibung': 'Benachrichtigung an Support-Team bei neuem Ticket (PRD-007)',
                'betreff': 'Neues Ticket {{ ticket_nummer }}: {{ ticket_titel }}',
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
                            <h2 style="color: #333333; margin: 0 0 20px 0; font-size: 22px;">
                                🎫 Neues Support-Ticket
                            </h2>
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                                Ein neues Support-Ticket wurde erstellt:
                            </p>
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="10" style="background-color: #f8f9fa; border-radius: 6px; margin: 0 0 20px 0;">
                                <tr>
                                    <td style="color: #333333; font-size: 14px; border-bottom: 1px solid #e9ecef;">
                                        <strong>Ticket-Nr:</strong> {{ ticket_nummer }}
                                    </td>
                                </tr>
                                <tr>
                                    <td style="color: #333333; font-size: 14px; border-bottom: 1px solid #e9ecef;">
                                        <strong>Betreff:</strong> {{ ticket_titel }}
                                    </td>
                                </tr>
                                <tr>
                                    <td style="color: #333333; font-size: 14px; border-bottom: 1px solid #e9ecef;">
                                        <strong>Typ:</strong> {{ ticket_typ }}
                                    </td>
                                </tr>
                                <tr>
                                    <td style="color: #333333; font-size: 14px; border-bottom: 1px solid #e9ecef;">
                                        <strong>Erstellt von:</strong> {{ ersteller_name }}{% if ersteller_email %} ({{ ersteller_email }}){% endif %}
                                    </td>
                                </tr>
                                {% if modul_name %}
                                <tr>
                                    <td style="color: #333333; font-size: 14px;">
                                        <strong>Modul:</strong> {{ modul_name }}
                                    </td>
                                </tr>
                                {% endif %}
                            </table>
                            <p style="color: #666666; font-size: 14px; line-height: 1.6; margin: 0 0 20px 0;">
                                <strong>Beschreibung:</strong><br>
                                {{ ticket_beschreibung | replace('\n', '<br>') | safe }}
                            </p>
                            <!-- Button -->
                            <table role="presentation" cellspacing="0" cellpadding="0" style="margin: 0 auto 30px auto;">
                                <tr>
                                    <td style="background-color: {{ primary_color }}; border-radius: 6px;">
                                        <a href="{{ link }}" style="display: inline-block; padding: 14px 32px; color: #ffffff; text-decoration: none; font-size: 16px; font-weight: bold;">
                                            Ticket anzeigen
                                        </a>
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
                'body_text': '''Neues Support-Ticket

Ein neues Support-Ticket wurde erstellt:

Ticket-Nr: {{ ticket_nummer }}
Betreff: {{ ticket_titel }}
Typ: {{ ticket_typ }}
Erstellt von: {{ ersteller_name }}{% if ersteller_email %} ({{ ersteller_email }}){% endif %}
{% if modul_name %}Modul: {{ modul_name }}{% endif %}

Beschreibung:
{{ ticket_beschreibung }}

Ticket anzeigen: {{ link }}

{{ footer }}

{{ copyright_text }}'''
            },
            # PRD-010: Schulungen E-Mail Templates
            {
                'schluessel': 'schulung_buchung_bestaetigung',
                'name': 'Schulung Buchungsbestätigung',
                'beschreibung': 'Bestätigung einer Schulungsbuchung (PRD-010)',
                'betreff': 'Buchungsbestätigung: {{ schulung_titel }}',
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
                        <td style="background-color: #6f42c1; padding: 30px; text-align: center;">
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
                            <h2 style="color: #333333; margin: 0 0 20px 0; font-size: 22px;">
                                ✅ Buchungsbestätigung
                            </h2>
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
                                {{ briefanrede }},
                            </p>
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                                Ihre Buchung für die Schulung <strong style="color: #333333;">{{ schulung_titel }}</strong> wurde bestätigt.
                            </p>
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="10" style="background-color: #f8f9fa; border-radius: 6px; margin: 0 0 20px 0;">
                                <tr>
                                    <td style="color: #333333; font-size: 14px; border-bottom: 1px solid #e9ecef;">
                                        <strong>📅 Startdatum:</strong> {{ start_datum }}
                                    </td>
                                </tr>
                                <tr>
                                    <td style="color: #333333; font-size: 14px; border-bottom: 1px solid #e9ecef;">
                                        <strong>🕐 Uhrzeit:</strong> {{ uhrzeit }}
                                    </td>
                                </tr>
                                <tr>
                                    <td style="color: #333333; font-size: 14px; border-bottom: 1px solid #e9ecef;">
                                        <strong>📆 Wochentage:</strong> {{ wochentage }}
                                    </td>
                                </tr>
                                <tr>
                                    <td style="color: #333333; font-size: 14px;">
                                        <strong>💶 Preis:</strong> {{ preis }}
                                    </td>
                                </tr>
                            </table>
                            {% if teams_link %}
                            <p style="color: #666666; font-size: 14px; line-height: 1.6; margin: 0 0 15px 0;">
                                <strong>Teams-Link:</strong><br>
                                <a href="{{ teams_link }}" style="color: #6f42c1;">{{ teams_link }}</a>
                            </p>
                            {% endif %}
                            <p style="color: #999999; font-size: 14px; line-height: 1.6; margin: 20px 0 0 0;">
                                Kostenfreie Stornierung möglich bis: <strong>{{ storno_frist }}</strong>
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
                'body_text': '''Buchungsbestätigung

{{ briefanrede }},

Ihre Buchung für die Schulung "{{ schulung_titel }}" wurde bestätigt.

Startdatum: {{ start_datum }}
Uhrzeit: {{ uhrzeit }}
Wochentage: {{ wochentage }}
Preis: {{ preis }}
{% if teams_link %}
Teams-Link: {{ teams_link }}
{% endif %}

Kostenfreie Stornierung möglich bis: {{ storno_frist }}

{{ footer }}

{{ copyright_text }}'''
            },
            {
                'schluessel': 'schulung_warteliste',
                'name': 'Schulung Warteliste',
                'beschreibung': 'Benachrichtigung bei Wartelisten-Platzierung (PRD-010)',
                'betreff': 'Warteliste: {{ schulung_titel }}',
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
                        <td style="background-color: #ffc107; padding: 30px; text-align: center;">
                            {% if logo_url %}
                            <img src="{{ logo_url }}" alt="{{ portal_name }}" height="40" style="max-height: 40px;">
                            {% else %}
                            <h1 style="color: #333333; margin: 0; font-size: 24px;">{{ portal_name }}</h1>
                            {% endif %}
                        </td>
                    </tr>
                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 30px;">
                            <h2 style="color: #333333; margin: 0 0 20px 0; font-size: 22px;">
                                ⏳ Warteliste
                            </h2>
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
                                {{ briefanrede }},
                            </p>
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                                Die Schulung <strong style="color: #333333;">{{ schulung_titel }}</strong> ist aktuell ausgebucht. Sie wurden auf die Warteliste gesetzt.
                            </p>
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="10" style="background-color: #fff3cd; border-radius: 6px; margin: 0 0 20px 0;">
                                <tr>
                                    <td style="color: #856404; font-size: 14px;">
                                        <strong>📅 Gewünschter Termin:</strong> {{ start_datum }}<br>
                                        <strong>🕐 Uhrzeit:</strong> {{ uhrzeit }}
                                    </td>
                                </tr>
                            </table>
                            <p style="color: #666666; font-size: 14px; line-height: 1.6; margin: 0;">
                                Sobald ein Platz frei wird, werden Sie automatisch benachrichtigt und Ihre Buchung wird bestätigt.
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
                'body_text': '''Warteliste

{{ briefanrede }},

Die Schulung "{{ schulung_titel }}" ist aktuell ausgebucht. Sie wurden auf die Warteliste gesetzt.

Gewünschter Termin: {{ start_datum }}
Uhrzeit: {{ uhrzeit }}

Sobald ein Platz frei wird, werden Sie automatisch benachrichtigt und Ihre Buchung wird bestätigt.

{{ footer }}

{{ copyright_text }}'''
            },
            {
                'schluessel': 'schulung_warteliste_freigabe',
                'name': 'Schulung von Warteliste freigeschaltet',
                'beschreibung': 'Benachrichtigung wenn Platz frei wird (PRD-010)',
                'betreff': '🎉 Platz frei: {{ schulung_titel }}',
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
                        <td style="background-color: #198754; padding: 30px; text-align: center;">
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
                            <h2 style="color: #333333; margin: 0 0 20px 0; font-size: 22px;">
                                🎉 Platz freigeworden!
                            </h2>
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
                                {{ briefanrede }},
                            </p>
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                                Gute Nachrichten! Ein Platz ist frei geworden und Ihre Buchung für <strong style="color: #333333;">{{ schulung_titel }}</strong> wurde bestätigt.
                            </p>
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="10" style="background-color: #d1e7dd; border-radius: 6px; margin: 0 0 20px 0;">
                                <tr>
                                    <td style="color: #0f5132; font-size: 14px;">
                                        <strong>📅 Startdatum:</strong> {{ start_datum }}<br>
                                        <strong>🕐 Uhrzeit:</strong> {{ uhrzeit }}<br>
                                        <strong>📆 Wochentage:</strong> {{ wochentage }}<br>
                                        <strong>💶 Preis:</strong> {{ preis }}
                                    </td>
                                </tr>
                            </table>
                            {% if teams_link %}
                            <p style="color: #666666; font-size: 14px; line-height: 1.6; margin: 0 0 15px 0;">
                                <strong>Teams-Link:</strong><br>
                                <a href="{{ teams_link }}" style="color: #198754;">{{ teams_link }}</a>
                            </p>
                            {% endif %}
                            <p style="color: #999999; font-size: 14px; line-height: 1.6; margin: 20px 0 0 0;">
                                Kostenfreie Stornierung möglich bis: <strong>{{ storno_frist }}</strong>
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
                'body_text': '''Platz freigeworden!

{{ briefanrede }},

Gute Nachrichten! Ein Platz ist frei geworden und Ihre Buchung für "{{ schulung_titel }}" wurde bestätigt.

Startdatum: {{ start_datum }}
Uhrzeit: {{ uhrzeit }}
Wochentage: {{ wochentage }}
Preis: {{ preis }}
{% if teams_link %}
Teams-Link: {{ teams_link }}
{% endif %}

Kostenfreie Stornierung möglich bis: {{ storno_frist }}

{{ footer }}

{{ copyright_text }}'''
            },
            {
                'schluessel': 'schulung_storniert',
                'name': 'Schulung Stornierungsbestätigung',
                'beschreibung': 'Bestätigung einer Stornierung (PRD-010)',
                'betreff': 'Stornierung: {{ schulung_titel }}',
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
                        <td style="background-color: #6c757d; padding: 30px; text-align: center;">
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
                            <h2 style="color: #333333; margin: 0 0 20px 0; font-size: 22px;">
                                ❌ Stornierungsbestätigung
                            </h2>
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 15px 0;">
                                {{ briefanrede }},
                            </p>
                            <p style="color: #666666; font-size: 16px; line-height: 1.6; margin: 0 0 20px 0;">
                                Ihre Buchung für die Schulung <strong style="color: #333333;">{{ schulung_titel }}</strong> wurde storniert.
                            </p>
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="10" style="background-color: #f8f9fa; border-radius: 6px; margin: 0 0 20px 0;">
                                <tr>
                                    <td style="color: #333333; font-size: 14px;">
                                        <strong>📅 Termin:</strong> {{ start_datum }}<br>
                                        <strong>🕐 Uhrzeit:</strong> {{ uhrzeit }}
                                    </td>
                                </tr>
                            </table>
                            <p style="color: #666666; font-size: 14px; line-height: 1.6; margin: 0;">
                                Bei Fragen stehen wir Ihnen gerne zur Verfügung.
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
                'body_text': '''Stornierungsbestätigung

{{ briefanrede }},

Ihre Buchung für die Schulung "{{ schulung_titel }}" wurde storniert.

Termin: {{ start_datum }}
Uhrzeit: {{ uhrzeit }}

Bei Fragen stehen wir Ihnen gerne zur Verfügung.

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

        # Create LookupWert entries for Anrede patterns (Briefanrede system)
        from app.models import LookupWert

        # Format: (kategorie, schluessel, wert, sortierung)
        # {vorname} and {nachname} are placeholders replaced by Kunde.briefanrede properties
        anrede_patterns = [
            # Formelle Anreden (Sie-Form)
            ('anrede_foermlich', 'herr', 'Sehr geehrter Herr {nachname}', 1),
            ('anrede_foermlich', 'frau', 'Sehr geehrte Frau {nachname}', 2),
            ('anrede_foermlich', 'divers', 'Guten Tag {vorname} {nachname}', 3),
            ('anrede_foermlich', 'firma', 'Sehr geehrte Damen und Herren', 4),
            # Lockere Anreden (Du-Form)
            ('anrede_locker', 'herr', 'Lieber Herr {nachname}', 1),
            ('anrede_locker', 'frau', 'Liebe Frau {nachname}', 2),
            ('anrede_locker', 'divers', 'Hallo {vorname}', 3),
            ('anrede_locker', 'firma', 'Hallo zusammen', 4),
        ]

        for kategorie, schluessel, wert, sortierung in anrede_patterns:
            existing = LookupWert.query.filter_by(
                kategorie=kategorie,
                schluessel=schluessel
            ).first()
            if not existing:
                lookup_entry = LookupWert(
                    kategorie=kategorie,
                    schluessel=schluessel,
                    wert=wert,
                    sortierung=sortierung,
                    aktiv=True
                )
                db.session.add(lookup_entry)
                click.echo(f"Created LookupWert: {kategorie}.{schluessel}")
            else:
                click.echo(f"LookupWert already exists: {kategorie}.{schluessel}")

        # PRD-007: Support ticket enums in LookupWert
        # Format: (kategorie, schluessel, wert, icon, farbe, sortierung)
        support_lookups = [
            # Ticket-Typen
            ('support_typ', 'frage', 'Frage', 'ti-help', 'info', 1),
            ('support_typ', 'verbesserung', 'Verbesserungsvorschlag', 'ti-bulb', 'primary', 2),
            ('support_typ', 'bug', 'Fehlermeldung', 'ti-alert-triangle', 'danger', 3),
            ('support_typ', 'schulung', 'Schulungsanfrage', 'ti-school', 'warning', 4),
            ('support_typ', 'daten', 'Datenkorrektur', 'ti-database-edit', 'secondary', 5),
            ('support_typ', 'sonstiges', 'Sonstiges', 'ti-dots', 'light', 6),
            # Ticket-Status
            ('support_status', 'offen', 'Offen', 'ti-clock', 'warning', 1),
            ('support_status', 'in_bearbeitung', 'In Bearbeitung', 'ti-loader', 'info', 2),
            ('support_status', 'warte_auf_kunde', 'Warte auf Kunde', 'ti-hourglass', 'secondary', 3),
            ('support_status', 'geloest', 'Gelöst', 'ti-check', 'success', 4),
            ('support_status', 'geschlossen', 'Geschlossen', 'ti-archive', 'dark', 5),
            # Ticket-Priorität
            ('support_prioritaet', 'niedrig', 'Niedrig', 'ti-arrow-down', 'secondary', 1),
            ('support_prioritaet', 'normal', 'Normal', 'ti-minus', 'primary', 2),
            ('support_prioritaet', 'hoch', 'Hoch', 'ti-arrow-up', 'warning', 3),
            ('support_prioritaet', 'kritisch', 'Kritisch', 'ti-alert-triangle', 'danger', 4),
        ]

        for kategorie, schluessel, wert, icon, farbe, sortierung in support_lookups:
            existing = LookupWert.query.filter_by(
                kategorie=kategorie,
                schluessel=schluessel
            ).first()
            if not existing:
                lookup_entry = LookupWert(
                    kategorie=kategorie,
                    schluessel=schluessel,
                    wert=wert,
                    icon=icon,
                    farbe=farbe,
                    sortierung=sortierung,
                    aktiv=True
                )
                db.session.add(lookup_entry)
                click.echo(f"Created LookupWert: {kategorie}.{schluessel}")
            else:
                # Update existing entries with new icon/farbe if missing
                if not existing.icon or not existing.farbe:
                    existing.icon = icon
                    existing.farbe = farbe
                    click.echo(f"Updated LookupWert: {kategorie}.{schluessel}")
                else:
                    click.echo(f"LookupWert already exists: {kategorie}.{schluessel}")

        # PRD-011: Task type classification in LookupWert
        # Format: (kategorie, schluessel, wert, icon, farbe, sortierung)
        task_typ_lookups = [
            ('task_typ', 'funktion', 'Funktion', 'ti-sparkles', 'info', 1),
            ('task_typ', 'verbesserung', 'Verbesserung', 'ti-trending-up', 'success', 2),
            ('task_typ', 'fehlerbehebung', 'Fehlerbehebung', 'ti-bug', 'danger', 3),
            ('task_typ', 'technisch', 'Technische Aufgabe', 'ti-tool', 'secondary', 4),
            ('task_typ', 'sicherheit', 'Sicherheitsproblem', 'ti-shield-exclamation', 'warning', 5),
            ('task_typ', 'recherche', 'Recherche', 'ti-search', 'purple', 6),
            ('task_typ', 'dokumentation', 'Dokumentation', 'ti-file-text', 'dark', 7),
            ('task_typ', 'test', 'Test / QS', 'ti-test-pipe', 'cyan', 8),
        ]

        for kategorie, schluessel, wert, icon, farbe, sortierung in task_typ_lookups:
            existing = LookupWert.query.filter_by(
                kategorie=kategorie,
                schluessel=schluessel
            ).first()
            if not existing:
                lookup_entry = LookupWert(
                    kategorie=kategorie,
                    schluessel=schluessel,
                    wert=wert,
                    icon=icon,
                    farbe=farbe,
                    sortierung=sortierung,
                    aktiv=True
                )
                db.session.add(lookup_entry)
                click.echo(f"Created LookupWert: {kategorie}.{schluessel}")
            else:
                click.echo(f"LookupWert already exists: {kategorie}.{schluessel}")

        # PRD011-T047: Component types for customer projects
        # PRD011-T053: modul_erp (ERP-Modul) + modul_ev247 (ev247-Plattform)
        komponente_typ_kunde_lookups = [
            ('komponente_typ_kunde', 'modul_erp', 'Modul (ERP)', 'ti-plug', 'primary', 10),
            ('komponente_typ_kunde', 'modul_ev247', 'Modul (ev247)', 'ti-layout-grid', 'info', 15),
            ('komponente_typ_kunde', 'online_shop', 'Online-Shop', 'ti-shopping-cart', 'success', 20),
            ('komponente_typ_kunde', 'seo_sea', 'SEO/SEA', 'ti-chart-line', 'warning', 30),
            ('komponente_typ_kunde', 'onboarding', 'Onboarding', 'ti-user-check', 'cyan', 40),
            ('komponente_typ_kunde', 'stammdaten', 'Stammdaten', 'ti-database', 'secondary', 50),
            ('komponente_typ_kunde', 'hosting', 'Hosting', 'ti-server', 'dark', 60),
            ('komponente_typ_kunde', 'schnittstelle', 'Schnittstelle', 'ti-arrows-exchange', 'danger', 70),
        ]

        for kategorie, schluessel, wert, icon, farbe, sortierung in komponente_typ_kunde_lookups:
            existing = LookupWert.query.filter_by(
                kategorie=kategorie,
                schluessel=schluessel
            ).first()
            if not existing:
                lookup_entry = LookupWert(
                    kategorie=kategorie,
                    schluessel=schluessel,
                    wert=wert,
                    icon=icon,
                    farbe=farbe,
                    sortierung=sortierung,
                    aktiv=True
                )
                db.session.add(lookup_entry)
                click.echo(f"Created LookupWert: {kategorie}.{schluessel}")
            else:
                click.echo(f"LookupWert already exists: {kategorie}.{schluessel}")

        # PRD011-T053: Remove old entries (replaced by modul_erp + modul_ev247)
        for old_schluessel in ['modul', 'modul_kundenauftrag']:
            old_lookup = LookupWert.query.filter_by(
                kategorie='komponente_typ_kunde',
                schluessel=old_schluessel
            ).first()
            if old_lookup:
                db.session.delete(old_lookup)
                click.echo(f"Deleted old LookupWert: komponente_typ_kunde.{old_schluessel}")

        # PRD011-T052: Seed ERP modules (e-vendo ERP/Shop system modules)
        # PRD011-T054: Added icon column for visual representation
        from app.models import ModulErp
        erp_module_data = [
            # (artikelnummer, bezeichnung, kontext, sortierung, icon)
            ('CLOUD-S-AMA', 'Amazon Marktplatz Schnittstelle', 'erp', 10, 'ti-brand-amazon'),
            ('CLOUD-S-OTTO', 'Otto Marktplatz Schnittstelle', 'erp', 20, 'ti-building-store'),
        ]
        for artikelnummer, bezeichnung, kontext, sortierung, icon in erp_module_data:
            existing = ModulErp.query.filter_by(artikelnummer=artikelnummer).first()
            if not existing:
                erp_modul = ModulErp(
                    artikelnummer=artikelnummer,
                    bezeichnung=bezeichnung,
                    kontext=kontext,
                    sortierung=sortierung,
                    icon=icon,
                    aktiv=True
                )
                db.session.add(erp_modul)
                click.echo(f"Created ModulErp: {artikelnummer}")
            else:
                # PRD011-T054: Update icon if changed
                if existing.icon != icon:
                    existing.icon = icon
                    click.echo(f"Updated ModulErp icon: {artikelnummer} -> {icon}")
                else:
                    click.echo(f"ModulErp already exists: {artikelnummer}")

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
            # Administration Dashboard-Modul (nur für Admin sichtbar durch Admin-Bypass)
            ('administration', 'Administration', 'Benutzer, Einstellungen und Systemverwaltung',
             'ti-settings', 'secondary', '#6c757d', 'admin.index', 5, ModulTyp.BASIS.value, True),
            # Dashboard modules with different types
            ('pricat', 'PRICAT Converter', 'VEDES PRICAT-Dateien zu Elena-Format konvertieren',
             'ti-route-square', 'primary', '#0d6efd', 'main.pricat_converter', 10, ModulTyp.CONSULTING_INTERN.value, True),
            ('kunden', 'Lead & Kundenreport', 'Kunden verwalten und Website-Analyse',
             'ti-users', 'success', '#198754', 'kunden.liste', 20, ModulTyp.SALES_INTERN.value, True),
            ('lieferanten', 'Meine Lieferanten', 'Relevante Lieferanten auswählen',
             'ti-truck', 'info', '#0dcaf0', 'lieferanten_auswahl.index', 30, ModulTyp.KUNDENPROJEKT.value, True),
            ('content', 'Content Generator', 'KI-generierte Texte für Online-Shops',
             'ti-writing', 'warning', '#ffc107', 'content_generator.index', 40, ModulTyp.PREMIUM.value, True),
            # PRD-006: Kunden-Dialog Modul
            ('dialog', 'Kunden-Dialog', 'Fragebögen erstellen und Kunden befragen',
             'ti-messages', 'teal', '#20c997', 'dialog.index', 50, ModulTyp.KUNDENPROJEKT.value, True),
            # PRD-007: Anwender-Support Modul
            ('support', 'Anwender-Support', 'Support-Tickets erstellen und verwalten',
             'ti-headset', 'info', '#17a2b8', 'support.meine_tickets', 60, ModulTyp.KUNDENPROJEKT.value, True),
            # PRD-010: Schulungen Modul
            ('schulungen', 'Schulungen', 'Online-Schulungen buchen und verwalten',
             'ti-school', 'purple', '#6f42c1', 'schulungen.liste', 70, ModulTyp.KUNDENPROJEKT.value, True),
            # PRD-011: Projektverwaltung Modul (intern)
            ('projekte', 'Projektverwaltung', 'PRDs, Tasks und Changelogs verwalten',
             'ti-folder', 'danger', '#dc3545', 'projekte_admin.index', 80, ModulTyp.BASIS.value, False),
            # PRD-013: Kunden-Mailing Modul
            ('mailing', 'Kunden-Mailing', 'Marketing-E-Mails an Kunden versenden',
             'ti-mail-forward', 'pink', '#e83e8c', 'mailing_admin.index', 90, ModulTyp.KUNDENPROJEKT.value, True),
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
            # PRD-007: Anwender-Support
            ('support', ['admin', 'mitarbeiter', 'kunde']),
            # PRD-010: Schulungen
            ('schulungen', ['admin', 'mitarbeiter', 'kunde']),
            # PRD-011: Projektverwaltung (nur intern)
            ('projekte', ['admin', 'mitarbeiter']),
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

        # PRD-007: Create default support team
        from app.models import SupportTeam, SupportTeamMitglied, User

        default_team = SupportTeam.query.filter_by(name='Allgemeiner Support').first()
        if not default_team:
            default_team = SupportTeam(
                name='Allgemeiner Support',
                beschreibung='Standard-Team für alle Support-Anfragen',
                icon='ti-users',
                aktiv=True
            )
            db.session.add(default_team)
            db.session.flush()
            click.echo('Created SupportTeam: Allgemeiner Support')

            # Add all admins and mitarbeiter to the default team
            admin_rolle = roles.get('admin')
            mitarbeiter_rolle = roles.get('mitarbeiter')

            if admin_rolle:
                admin_users = User.query.filter_by(rolle_id=admin_rolle.id).all()
                for user in admin_users:
                    mitglied = SupportTeamMitglied(
                        team_id=default_team.id,
                        user_id=user.id,
                        ist_teamleiter=True,
                        benachrichtigung_aktiv=True
                    )
                    db.session.add(mitglied)
                    click.echo(f'Added {user.email} to SupportTeam as Teamleiter')

            if mitarbeiter_rolle:
                mitarbeiter_users = User.query.filter_by(rolle_id=mitarbeiter_rolle.id).all()
                for user in mitarbeiter_users:
                    mitglied = SupportTeamMitglied(
                        team_id=default_team.id,
                        user_id=user.id,
                        ist_teamleiter=False,
                        benachrichtigung_aktiv=True
                    )
                    db.session.add(mitglied)
                    click.echo(f'Added {user.email} to SupportTeam as Mitglied')
        else:
            click.echo('SupportTeam already exists: Allgemeiner Support')

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
        click.echo('')
        click.echo('Next steps:')
        click.echo('  flask seed-essential    # Roles + admin user (required)')
        click.echo('  flask seed-stammdaten   # Master data (Branchen, etc.)')
        click.echo('  flask seed-demo         # Demo data (development only)')

    @app.cli.command('seed-demo')
    def seed_demo_command():
        """Seed demo/test data for development environments.

        Creates:
        - Test supplier (LEGO)
        - e-vendo admin users (Carsten, Rainer)
        - Claude AI user
        - test_benutzer role
        - Test customers with users (for mailing tests)

        Run AFTER seed-essential and seed-stammdaten.
        NOT for production use!
        """
        from app.models import User, Rolle, Kunde, KundeBenutzer, Lieferant, UserTyp
        from app.models.kunde import KundeTyp

        click.echo('=' * 50)
        click.echo('Seeding DEMO data (for development only)...')
        click.echo('=' * 50)

        # Check if essential seed was run
        admin_rolle = Rolle.query.filter_by(name='admin').first()
        if not admin_rolle:
            click.echo('ERROR: Roles not found. Run "flask seed-essential" first!')
            return

        # ─────────────────────────────────────────────────
        # 1. Create test supplier (LEGO)
        # ─────────────────────────────────────────────────
        click.echo('\n--- Test-Lieferant ---')
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
            click.echo('✓ Created test supplier: LEGO Spielwaren GmbH')
        else:
            click.echo('  Test supplier exists: LEGO Spielwaren GmbH')

        # ─────────────────────────────────────────────────
        # 2. Create e-vendo admin users
        # ─────────────────────────────────────────────────
        click.echo('\n--- e-vendo Admin-Users ---')
        initial_password = os.environ.get('INITIAL_ADMIN_PASSWORD', 'admin123')

        evendo_users = [
            {
                'email': 'carsten.vogelsang@e-vendo.de',
                'vorname': 'Carsten',
                'nachname': 'Vogelsang',
                'rolle_name': 'admin',
            },
            {
                'email': 'rainer.raschka@e-vendo.de',
                'vorname': 'Rainer',
                'nachname': 'Raschka',
                'rolle_name': 'admin',
            }
        ]

        for user_data in evendo_users:
            existing = User.query.filter_by(email=user_data['email']).first()
            if not existing:
                rolle = Rolle.query.filter_by(name=user_data['rolle_name']).first()
                user = User(
                    email=user_data['email'],
                    vorname=user_data['vorname'],
                    nachname=user_data['nachname'],
                    rolle_id=rolle.id,
                    aktiv=True
                )
                user.set_password(initial_password)
                db.session.add(user)
                click.echo(f"✓ Created user: {user_data['email']}")
            else:
                click.echo(f"  User exists: {user_data['email']}")

        # ─────────────────────────────────────────────────
        # 3. Create Claude AI user
        # ─────────────────────────────────────────────────
        click.echo('\n--- Claude AI User ---')
        claude = User.query.filter_by(email='claude@anthropic.com').first()
        if not claude:
            mitarbeiter_rolle = Rolle.query.filter_by(name='mitarbeiter').first()
            if mitarbeiter_rolle:
                claude = User(
                    email='claude@anthropic.com',
                    vorname='Claude',
                    nachname='AI',
                    rolle_id=mitarbeiter_rolle.id,
                    user_typ=UserTyp.KI_CLAUDE.value,
                    aktiv=True
                )
                claude.set_password('ki-user-no-login')
                db.session.add(claude)
                db.session.flush()
                click.echo('✓ Created KI user: Claude (Anthropic)')

                # Assign Claude to Betreiber if exists
                betreiber = Kunde.query.filter_by(ist_systemkunde=True).first()
                if betreiber:
                    zuordnung = KundeBenutzer(
                        kunde_id=betreiber.id,
                        user_id=claude.id,
                        ist_hauptbenutzer=False
                    )
                    db.session.add(zuordnung)
                    click.echo(f'  Assigned to Betreiber: {betreiber.firmierung}')
        else:
            click.echo('  Claude AI user exists')

        # ─────────────────────────────────────────────────
        # 4. Create test_benutzer role
        # ─────────────────────────────────────────────────
        click.echo('\n--- Test-Rolle ---')
        test_rolle = Rolle.query.filter_by(name='test_benutzer').first()
        if not test_rolle:
            test_rolle = Rolle(name='test_benutzer', beschreibung='Test-Benutzer für Mailing-Tests')
            db.session.add(test_rolle)
            db.session.flush()
            click.echo('✓ Created role: test_benutzer')
        else:
            click.echo('  Role exists: test_benutzer')

        # ─────────────────────────────────────────────────
        # 5. Create test customers with users
        # ─────────────────────────────────────────────────
        click.echo('\n--- Test-Kunden und Test-Users ---')
        test_data = [
            {
                'user': {
                    'email': 'carsten.vogelsang+testuser1@gmail.com',
                    'vorname': 'Max',
                    'nachname': 'Mustermann',
                    'anrede': 'herr',
                    'kommunikation_stil': 'foermlich',
                },
                'kunde': {
                    'firmierung': 'Mustermann GmbH',
                    'strasse': 'Musterstraße 123',
                    'plz': '12345',
                    'ort': 'Musterstadt',
                    'telefon': '+49 123 456789',
                    'email': 'info@mustermann-gmbh.de',
                }
            },
            {
                'user': {
                    'email': 'carsten.vogelsang+testuser2@gmail.com',
                    'vorname': 'Erika',
                    'nachname': 'Musterfrau',
                    'anrede': 'frau',
                    'kommunikation_stil': 'locker',
                },
                'kunde': {
                    'firmierung': 'Musterfrau & Co. KG',
                    'strasse': 'Beispielweg 42',
                    'plz': '54321',
                    'ort': 'Beispielstadt',
                    'telefon': '+49 987 654321',
                    'email': 'kontakt@musterfrau-kg.de',
                }
            },
            {
                'user': {
                    'email': 'carsten.vogelsang+testuser3@gmail.com',
                    'vorname': 'Hans',
                    'nachname': 'Testmann',
                    'anrede': 'herr',
                    'kommunikation_stil': 'foermlich',
                },
                'kunde': {
                    'firmierung': 'Testmann IT Solutions',
                    'strasse': 'Technikring 7',
                    'plz': '99999',
                    'ort': 'Techstadt',
                    'telefon': '+49 555 123456',
                    'email': 'hello@testmann-it.de',
                }
            }
        ]

        for data in test_data:
            # Create or get user
            user = User.query.filter_by(email=data['user']['email']).first()
            if not user:
                user = User(
                    email=data['user']['email'],
                    vorname=data['user']['vorname'],
                    nachname=data['user']['nachname'],
                    anrede=data['user']['anrede'],
                    kommunikation_stil=data['user']['kommunikation_stil'],
                    rolle_id=test_rolle.id,
                    aktiv=True
                )
                user.set_password('test-user-no-login-' + str(hash(data['user']['email'])))
                db.session.add(user)
                db.session.flush()
                click.echo(f"✓ Created test user: {data['user']['vorname']} {data['user']['nachname']}")

            # Create or get kunde
            kunde = Kunde.query.filter_by(firmierung=data['kunde']['firmierung']).first()
            if not kunde:
                kunde = Kunde(
                    firmierung=data['kunde']['firmierung'],
                    strasse=data['kunde']['strasse'],
                    plz=data['kunde']['plz'],
                    ort=data['kunde']['ort'],
                    telefon=data['kunde']['telefon'],
                    email=data['kunde']['email'],
                    typ=KundeTyp.TESTKUNDE.value,
                    aktiv=True
                )
                db.session.add(kunde)
                db.session.flush()
                click.echo(f"✓ Created test customer: {data['kunde']['firmierung']}")

            # Link user to customer
            zuordnung = KundeBenutzer.query.filter_by(
                kunde_id=kunde.id, user_id=user.id
            ).first()
            if not zuordnung:
                zuordnung = KundeBenutzer(
                    kunde_id=kunde.id,
                    user_id=user.id,
                    ist_hauptbenutzer=True
                )
                db.session.add(zuordnung)

        db.session.commit()
        click.echo('')
        click.echo('Demo seeding complete!')

    # ─────────────────────────────────────────────────────────
    # Compatibility aliases for old commands
    # ─────────────────────────────────────────────────────────
    @app.cli.command('seed')
    @click.pass_context
    def seed_legacy_command(ctx):
        """DEPRECATED: Use seed-essential + seed-stammdaten instead."""
        click.echo('⚠️  DEPRECATED: "flask seed" is deprecated.')
        click.echo('')
        click.echo('Please use the new commands:')
        click.echo('  flask seed-essential    # Roles + admin user (required)')
        click.echo('  flask seed-stammdaten   # Master data (Branchen, etc.)')
        click.echo('  flask seed-demo         # Demo data (development only)')
        click.echo('')
        click.echo('Running seed-stammdaten for backwards compatibility...')
        click.echo('')
        ctx.invoke(seed_stammdaten_command)

    @app.cli.command('seed-users')
    @click.pass_context
    def seed_users_legacy_command(ctx):
        """DEPRECATED: Use seed-demo instead."""
        click.echo('⚠️  DEPRECATED: "flask seed-users" is deprecated.')
        click.echo('Please use: flask seed-demo')
        click.echo('')
        click.echo('Running seed-demo for backwards compatibility...')
        click.echo('')
        ctx.invoke(seed_demo_command)
