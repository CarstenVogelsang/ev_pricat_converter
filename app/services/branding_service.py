"""Branding Service for loading brand configuration."""
from dataclasses import dataclass

from app.models import Config


@dataclass
class BrandingConfig:
    """Branding configuration values."""
    logo_url: str
    primary_color: str
    secondary_color: str
    app_title: str
    copyright_text: str
    copyright_url: str


class BrandingService:
    """Service for loading branding configuration from database."""

    # Default values
    DEFAULT_PRIMARY_COLOR = '#0d6efd'
    DEFAULT_SECONDARY_COLOR = '#6c757d'
    DEFAULT_APP_TITLE = 'ev247'
    DEFAULT_COPYRIGHT_TEXT = '© 2025 e-vendo AG'
    DEFAULT_COPYRIGHT_URL = 'https://www.e-vendo.de'
    PLACEHOLDER_LOGO = '/static/placeholder-logo.svg'

    def get_branding(self) -> BrandingConfig:
        """Load branding configuration from database."""
        logo_path = Config.get_value('brand_logo', '')

        # Determine logo URL (use direct path, not url_for)
        if logo_path:
            logo_url = f'/static/uploads/{logo_path}'
        else:
            logo_url = '/static/placeholder-logo.svg'

        return BrandingConfig(
            logo_url=logo_url,
            primary_color=Config.get_value('brand_primary_color', self.DEFAULT_PRIMARY_COLOR),
            secondary_color=Config.get_value('brand_secondary_color', self.DEFAULT_SECONDARY_COLOR),
            app_title=Config.get_value('brand_app_title', self.DEFAULT_APP_TITLE),
            copyright_text=Config.get_value('copyright_text', self.DEFAULT_COPYRIGHT_TEXT),
            copyright_url=Config.get_value('copyright_url', self.DEFAULT_COPYRIGHT_URL),
        )

    def get_branding_dict(self) -> dict:
        """Get branding as dictionary for templates."""
        branding = self.get_branding()
        return {
            'logo_url': branding.logo_url,
            'primary_color': branding.primary_color,
            'secondary_color': branding.secondary_color,
            'app_title': branding.app_title,
            'copyright_text': branding.copyright_text,
            'copyright_url': branding.copyright_url,
        }
