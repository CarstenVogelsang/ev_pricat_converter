"""Email Template Service for rendering database-stored email templates.

Renders Jinja2 templates with branding and customer-specific footers.
"""
from typing import Optional

from jinja2 import Environment, BaseLoader, TemplateSyntaxError

from app import db
from app.models import EmailTemplate, Kunde
from app.services.branding_service import BrandingService


class EmailTemplateService:
    """Service for rendering email templates with Jinja2.

    Templates support these standard placeholders:
    - {{ firmenname }} - Customer company name
    - {{ link }} - Action link (magic link, password link, etc.)
    - {{ fragebogen_titel }} - Questionnaire title
    - {{ briefanrede }} - Automatic salutation (based on customer's kommunikation_stil)
    - {{ briefanrede_foermlich }} - Formal salutation (Sie-form)
    - {{ briefanrede_locker }} - Informal salutation (Du-form)
    - {{ portal_name }} - Portal name from branding
    - {{ primary_color }} - Brand primary color
    - {{ logo_url }} - Brand logo URL
    - {{ footer }} - Customer-specific or system footer
    """

    def __init__(self):
        self.branding_service = BrandingService()
        self._jinja_env = Environment(loader=BaseLoader(), autoescape=True)

    def render(
        self,
        schluessel: str,
        context: dict,
        kunde: Optional[Kunde] = None
    ) -> dict:
        """Render an email template.

        Args:
            schluessel: Template key (e.g., 'fragebogen_einladung')
            context: Variables for template (firmenname, link, etc.)
            kunde: Optional customer for footer

        Returns:
            {
                'subject': str,      # Rendered subject
                'html': str,         # Rendered HTML body
                'text': str | None   # Rendered text body (if available)
            }

        Raises:
            ValueError: If template not found or inactive
            TemplateSyntaxError: If template has syntax errors
        """
        template = EmailTemplate.get_by_key(schluessel)
        if not template:
            raise ValueError(f"E-Mail-Template '{schluessel}' nicht gefunden oder inaktiv")

        # Load branding
        branding = self.branding_service.get_branding_dict()

        # Build full context with branding, footer, and briefanrede
        # IMPORTANT: Defaults come FIRST, then context spreads LAST to allow overrides
        full_context = {
            # Briefanrede defaults (can be overridden by context)
            'briefanrede': kunde.briefanrede if kunde else 'Sehr geehrte Damen und Herren',
            'briefanrede_foermlich': kunde.briefanrede_foermlich if kunde else 'Sehr geehrte Damen und Herren',
            'briefanrede_locker': kunde.briefanrede_locker if kunde else 'Hallo',
            # Branding
            'branding': branding,
            'primary_color': branding.get('primary_color', '#0d6efd'),
            'secondary_color': branding.get('secondary_color', '#6c757d'),
            'logo_url': branding.get('logo_url'),
            'portal_name': branding.get('app_title', 'ev247'),
            'copyright_text': branding.get('copyright_text', ''),
            # Footer
            'footer': self._get_footer(kunde),
            # Context LAST - allows sample_context to override defaults (e.g., in preview)
            **context,
        }

        try:
            # Render subject
            subject_template = self._jinja_env.from_string(template.betreff)
            subject = subject_template.render(full_context)

            # Render HTML body
            html_template = self._jinja_env.from_string(template.body_html)
            html = html_template.render(full_context)

            # Inject font CSS for Quill classes into <head>
            font_css = self.branding_service.get_font_css_for_email()
            if font_css and '<head>' in html:
                style_block = f'<style type="text/css">\n{font_css}\n</style>\n</head>'
                html = html.replace('</head>', style_block)

            # Render text body (optional)
            text = None
            if template.body_text:
                text_template = self._jinja_env.from_string(template.body_text)
                text = text_template.render(full_context)

            return {
                'subject': subject,
                'html': html,
                'text': text
            }

        except TemplateSyntaxError as e:
            raise TemplateSyntaxError(
                f"Syntaxfehler im Template '{schluessel}': {e.message}",
                lineno=e.lineno
            )

    def _get_footer(self, kunde: Optional[Kunde] = None) -> str:
        """Get email footer for customer or system default.

        Priority:
        1. Customer's own footer (if set)
        2. System customer's footer (Kunde with ist_systemkunde=True)
        3. Empty string

        Args:
            kunde: Optional customer to get footer for

        Returns:
            HTML footer string
        """
        # Check customer-specific footer
        if kunde and kunde.email_footer:
            return kunde.email_footer

        # Fall back to system customer footer
        system_kunde = Kunde.query.filter_by(ist_systemkunde=True).first()
        if system_kunde and system_kunde.email_footer:
            return system_kunde.email_footer

        return ''

    def get_template(self, schluessel: str) -> Optional[EmailTemplate]:
        """Get a template by key (for admin editing).

        Args:
            schluessel: Template key

        Returns:
            EmailTemplate or None
        """
        return EmailTemplate.query.filter_by(schluessel=schluessel).first()

    def get_all_templates(self) -> list:
        """Get all templates for admin management."""
        return EmailTemplate.query.order_by(EmailTemplate.name).all()

    def preview(
        self,
        schluessel: str,
        sample_context: Optional[dict] = None
    ) -> dict:
        """Preview a template with sample data.

        Useful for admin UI to see how a template will look.

        Args:
            schluessel: Template key
            sample_context: Optional custom sample data

        Returns:
            Rendered preview dict
        """
        default_sample = {
            'firmenname': 'Musterfirma GmbH',
            'link': 'https://example.com/action',
            'fragebogen_titel': 'Beispiel-Fragebogen',
            'email': 'beispiel@example.com',
            'vorname': 'Max',
            'nachname': 'Mustermann',
            # Briefanrede defaults (will be overridden if kunde is passed)
            'briefanrede': 'Sehr geehrte Damen und Herren',
            'briefanrede_foermlich': 'Sehr geehrte Damen und Herren',
            'briefanrede_locker': 'Hallo zusammen',
        }

        context = {**default_sample, **(sample_context or {})}
        return self.render(schluessel, context)


# Singleton instance
_email_template_service: Optional[EmailTemplateService] = None


def get_email_template_service() -> EmailTemplateService:
    """Get the email template service singleton."""
    global _email_template_service
    if _email_template_service is None:
        _email_template_service = EmailTemplateService()
    return _email_template_service
