"""Branding Service for loading brand configuration."""
from dataclasses import dataclass

from app.models import Config


@dataclass
class BrandingConfig:
    """Branding configuration values."""
    logo_url: str
    primary_color: str
    secondary_color: str
    light_text_color: str  # Text auf dunklem Hintergrund (Navbar)
    app_title: str
    copyright_text: str
    copyright_url: str
    font_family: str
    font_weights: str
    secondary_font_family: str  # Optional, can be empty
    secondary_font_weights: str


class BrandingService:
    """Service for loading branding configuration from database."""

    # Default values
    DEFAULT_PRIMARY_COLOR = '#0d6efd'
    DEFAULT_SECONDARY_COLOR = '#6c757d'
    DEFAULT_LIGHT_TEXT_COLOR = '#ffffff'  # Weiß für Text auf dunklem Hintergrund
    DEFAULT_APP_TITLE = 'ev247'
    DEFAULT_COPYRIGHT_TEXT = '© 2025 e-vendo AG'
    DEFAULT_COPYRIGHT_URL = 'https://www.e-vendo.de'
    PLACEHOLDER_LOGO = '/static/placeholder-logo.svg'
    DEFAULT_FONT_FAMILY = 'Inter'
    DEFAULT_FONT_WEIGHTS = '400,500,600,700'

    # Available fonts for branding selection
    # Format: {'name': 'Font Name', 'weights': '...', 'is_system': bool, 'fallback': '...'}
    #
    # - is_system=True: System font (no Google Fonts loading needed, works in emails)
    # - is_system=False: Web font (loaded from Google Fonts CDN)
    # - fallback: CSS fallback stack (sans-serif, serif, monospace)
    #
    # To add a new font:
    #   1. Add entry here
    #   2. Update Quill CSS in betreiber.html (.ql-font-* classes)
    #
    # To disable a font: Comment out the line with #
    #
    AVAILABLE_FONTS = [
        # === System Fonts (work in emails) ===
        {'name': 'Arial', 'weights': '400,700', 'is_system': True, 'fallback': 'sans-serif'},
        {'name': 'Times New Roman', 'weights': '400,700', 'is_system': True, 'fallback': 'serif'},
        {'name': 'Courier New', 'weights': '400,700', 'is_system': True, 'fallback': 'monospace'},
        # === Web Fonts (Google Fonts) ===
        # Sans-Serif
        {'name': 'Inter', 'weights': '400,500,600,700', 'is_system': False, 'fallback': 'sans-serif'},
        {'name': 'Poppins', 'weights': '400,500,600,700', 'is_system': False, 'fallback': 'sans-serif'},
        {'name': 'Roboto', 'weights': '400,500,700', 'is_system': False, 'fallback': 'sans-serif'},
        {'name': 'Open Sans', 'weights': '400,600,700', 'is_system': False, 'fallback': 'sans-serif'},
        {'name': 'Lato', 'weights': '400,700', 'is_system': False, 'fallback': 'sans-serif'},
        # Serif
        {'name': 'Merriweather', 'weights': '400,700', 'is_system': False, 'fallback': 'serif'},
        # Monospace
        {'name': 'JetBrains Mono', 'weights': '400,500,700', 'is_system': False, 'fallback': 'monospace'},
    ]

    def get_branding(self) -> BrandingConfig:
        """Load branding configuration from database."""
        logo_path = Config.get_value('brand_logo', '')
        logo_url_external = Config.get_value('brand_logo_url', '')

        # Determine logo URL: external URL takes precedence, then local file
        if logo_url_external:
            logo_url = logo_url_external
        elif logo_path:
            logo_url = f'/static/uploads/{logo_path}'
        else:
            logo_url = '/static/placeholder-logo.svg'

        return BrandingConfig(
            logo_url=logo_url,
            primary_color=Config.get_value('brand_primary_color', self.DEFAULT_PRIMARY_COLOR),
            secondary_color=Config.get_value('brand_secondary_color', self.DEFAULT_SECONDARY_COLOR),
            light_text_color=Config.get_value('brand_light_text_color', self.DEFAULT_LIGHT_TEXT_COLOR),
            app_title=Config.get_value('brand_app_title', self.DEFAULT_APP_TITLE),
            copyright_text=Config.get_value('copyright_text', self.DEFAULT_COPYRIGHT_TEXT),
            copyright_url=Config.get_value('copyright_url', self.DEFAULT_COPYRIGHT_URL),
            font_family=Config.get_value('brand_font_family', self.DEFAULT_FONT_FAMILY),
            font_weights=Config.get_value('brand_font_weights', self.DEFAULT_FONT_WEIGHTS),
            secondary_font_family=Config.get_value('brand_secondary_font_family', ''),
            secondary_font_weights=Config.get_value('brand_secondary_font_weights', ''),
        )

    def get_selected_fonts(self) -> list[dict]:
        """Get list of selected fonts (primary + optional secondary).

        Returns only the fonts that are configured for branding,
        used to build the Quill editor whitelist.
        """
        branding = self.get_branding()
        fonts = []

        # Primary font (always present)
        primary = next(
            (f for f in self.AVAILABLE_FONTS if f['name'] == branding.font_family),
            None
        )
        if primary:
            fonts.append(primary)

        # Secondary font (optional)
        if branding.secondary_font_family:
            secondary = next(
                (f for f in self.AVAILABLE_FONTS
                 if f['name'] == branding.secondary_font_family),
                None
            )
            if secondary and secondary not in fonts:
                fonts.append(secondary)

        return fonts

    def get_google_fonts_url(self, font_family: str = None, font_weights: str = None) -> str:
        """Generate Google Fonts CDN URL for selected fonts.

        When called without arguments, loads both primary and secondary fonts.
        When called with arguments, loads only the specified font.
        System fonts are skipped (they don't need loading).

        Args:
            font_family: Font name (defaults to configured fonts)
            font_weights: Comma-separated weights (defaults to configured weights)

        Returns:
            Google Fonts CSS URL (empty string if only system fonts selected)
        """
        if font_family is not None and font_weights is not None:
            # Single font mode - check if it's a system font
            font_info = next((f for f in self.AVAILABLE_FONTS if f['name'] == font_family), None)
            if font_info and font_info.get('is_system', False):
                return ''  # System font, no loading needed
            font_url = font_family.replace(' ', '+')
            return f"https://fonts.googleapis.com/css2?family={font_url}:wght@{font_weights}&display=swap"

        # Multi-font mode: load all selected web fonts (skip system fonts)
        selected_fonts = self.get_selected_fonts()
        web_fonts = [f for f in selected_fonts if not f.get('is_system', False)]

        if not web_fonts:
            # All selected fonts are system fonts, no loading needed
            return ''

        font_params = []
        for font in web_fonts:
            font_url = font['name'].replace(' ', '+')
            font_params.append(f"family={font_url}:wght@{font['weights']}")

        return f"https://fonts.googleapis.com/css2?{'&'.join(font_params)}&display=swap"

    def get_font_css_for_email(self) -> str:
        """Generate CSS for Quill font classes to use in email templates.

        This CSS maps Quill's .ql-font-* classes to actual font-family values.
        Include this in email <head> to render fonts correctly.

        Returns:
            CSS string with font class definitions
        """
        css_rules = [
            # Compact line spacing for Quill-generated paragraphs
            "p { margin: 0 0 2px 0; line-height: 1.4; }"
        ]
        for font in self.AVAILABLE_FONTS:
            # Generate CSS class name (lowercase, no spaces)
            class_name = font['name'].lower().replace(' ', '')
            fallback = font.get('fallback', 'sans-serif')
            css_rules.append(
                f".ql-font-{class_name} {{ font-family: '{font['name']}', {fallback}; }}"
            )
        return '\n'.join(css_rules)

    def get_branding_dict(self) -> dict:
        """Get branding as dictionary for templates."""
        branding = self.get_branding()
        return {
            'logo_url': branding.logo_url,
            'primary_color': branding.primary_color,
            'secondary_color': branding.secondary_color,
            'light_text_color': branding.light_text_color,
            'app_title': branding.app_title,
            'copyright_text': branding.copyright_text,
            'copyright_url': branding.copyright_url,
            'font_family': branding.font_family,
            'font_weights': branding.font_weights,
            'secondary_font_family': branding.secondary_font_family,
            'secondary_font_weights': branding.secondary_font_weights,
            'google_fonts_url': self.get_google_fonts_url(),  # Loads web fonts (empty if system only)
            'selected_fonts': self.get_selected_fonts(),
            'font_css_for_email': self.get_font_css_for_email(),  # CSS for email templates
        }
