"""Flask Application Factory."""
import os
import click
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from app.config import config

db = SQLAlchemy()
migrate = Migrate()


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

    # Register blueprints
    from app.routes import main_bp
    app.register_blueprint(main_bp)

    # Register CLI commands
    register_cli_commands(app)

    return app


def register_cli_commands(app):
    """Register CLI commands."""

    @app.cli.command('seed')
    def seed_command():
        """Seed the database with initial data."""
        from app.models import Lieferant, Config as ConfigModel

        # Create test supplier (LEGO)
        lego = Lieferant.query.filter_by(vedes_id='0000001872').first()
        if not lego:
            lego = Lieferant(
                gln='4023017000005',
                vedes_id='0000001872',
                kurzbezeichnung='LEGO Spielwaren GmbH',
                aktiv=True,
                ftp_pfad_quelle='/pricat/pricat_1872_Lego Spielwaren GmbH_0.csv',
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
            ('vedes_ftp_user', '', 'VEDES FTP Benutzer'),
            ('vedes_ftp_pass', '', 'VEDES FTP Passwort'),
            ('vedes_ftp_basepath', '/pricat/', 'Basispfad PRICAT-Dateien'),
            ('elena_ftp_host', '', 'Ziel-FTP Server'),
            ('elena_ftp_user', '', 'Ziel-FTP Benutzer'),
            ('elena_ftp_pass', '', 'Ziel-FTP Passwort'),
            ('image_download_threads', '5', 'Parallele Bild-Downloads'),
            ('image_timeout', '30', 'Timeout Bild-Download in Sekunden'),
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
