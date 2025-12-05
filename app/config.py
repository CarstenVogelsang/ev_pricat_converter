"""Flask Application Configuration."""
import os
from pathlib import Path

basedir = Path(__file__).parent.parent.absolute()


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Database URL - supports SQLite, PostgreSQL, MariaDB/MySQL
    # Fix postgres:// → postgresql:// (some tools use deprecated format)
    _database_url = os.environ.get('DATABASE_URL', '')
    if _database_url.startswith('postgres://'):
        _database_url = _database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = _database_url or f'sqlite:///{basedir}/instance/pricat.db'

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Data directories
    DATA_DIR = basedir / 'data'
    IMPORTS_DIR = DATA_DIR / 'imports'
    EXPORTS_DIR = DATA_DIR / 'exports'
    IMAGES_DIR = DATA_DIR / 'images'

    # Image download settings
    IMAGE_DOWNLOAD_THREADS = 5
    IMAGE_TIMEOUT = 30


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
