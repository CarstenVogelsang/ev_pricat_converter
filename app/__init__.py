"""Flask Application Factory."""
import os
from datetime import datetime

import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

from app.config import config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
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

    # User loader for Flask-Login
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.routes import main_bp, admin_bp
    from app.routes.auth import auth_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(auth_bp)

    # Register CLI commands
    register_cli_commands(app)

    # Register Jinja2 filters
    @app.template_filter('datetime')
    def format_datetime(timestamp):
        """Format Unix timestamp to readable date."""
        if timestamp:
            return datetime.fromtimestamp(timestamp).strftime('%d.%m.%Y %H:%M')
        return ''

    return app


def register_cli_commands(app):
    """Register CLI commands."""

    @app.cli.command('seed')
    def seed_command():
        """Seed the database with initial data."""
        from app.models import Lieferant, Config as ConfigModel

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
        from app.models import User

        users = [
            {
                'email': 'carsten.vogelsang@e-vendo.de',
                'vorname': 'Carsten',
                'nachname': 'Vogelsang',
                'rolle': 'admin',
                'password': 'admin123'  # Should be changed on first login
            },
            {
                'email': 'rainer.raschka@e-vendo.de',
                'vorname': 'Rainer',
                'nachname': 'Raschka',
                'rolle': 'admin',
                'password': 'admin123'  # Should be changed on first login
            }
        ]

        for user_data in users:
            existing = User.query.filter_by(email=user_data['email']).first()
            if not existing:
                user = User(
                    email=user_data['email'],
                    vorname=user_data['vorname'],
                    nachname=user_data['nachname'],
                    rolle=user_data['rolle'],
                    aktiv=True
                )
                user.set_password(user_data['password'])
                db.session.add(user)
                click.echo(f"Created user: {user_data['email']} ({user_data['rolle']})")
            else:
                click.echo(f"User already exists: {user_data['email']}")

        db.session.commit()
        click.echo('Users seeded successfully!')
