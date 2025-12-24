"""Brevo E-Mail Service for transactional emails.

Uses Brevo (formerly Sendinblue) REST API for sending:
- Zugangsdaten E-Mails (2 separate emails for security)
- Fragebogen-Einladungen mit Magic-Link
- Template-basierte E-Mails mit System-Branding

Includes rate limiting for Brevo Free Plan (300 emails/day).
"""
import requests
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.models import Config, Kunde


class QuotaExceededError(Exception):
    """Raised when daily email quota is exceeded."""
    pass


@dataclass
class EmailResult:
    """Result of an email send operation."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class BrevoService:
    """Service for sending transactional emails via Brevo REST API.

    Config keys (stored in Config model):
    - brevo_api_key: Brevo API key
    - brevo_sender_email: Sender email address
    - brevo_sender_name: Sender display name
    - portal_base_url: Base URL for portal links
    """

    BREVO_API_URL = 'https://api.brevo.com/v3/smtp/email'

    def __init__(self):
        self._api_key = None
        self._sender_email = None
        self._sender_name = None
        self._portal_base_url = None

    def _load_config(self):
        """Load configuration from database."""
        from flask import current_app, request, has_request_context

        self._api_key = Config.get_value('brevo_api_key')
        self._sender_email = Config.get_value('brevo_sender_email', 'noreply@e-vendo.de')
        self._sender_name = Config.get_value('brevo_sender_name', 'e-vendo AG')

        # Portal URL: Dynamisch im Dev-Modus, Config im Prod-Modus
        configured_url = Config.get_value('portal_base_url', '')

        if current_app.debug and has_request_context():
            # Im Dev-Modus: Aktuelle Request-URL verwenden (z.B. http://localhost:5000)
            self._portal_base_url = request.host_url.rstrip('/')
        elif configured_url:
            self._portal_base_url = configured_url.rstrip('/')
        else:
            self._portal_base_url = 'https://portal.e-vendo.de'

    @property
    def is_configured(self) -> bool:
        """Check if Brevo is configured."""
        self._load_config()
        return bool(self._api_key)

    def _reset_quota_if_new_day(self) -> None:
        """Reset the daily quota counter if a new day has started."""
        today_str = date.today().isoformat()
        last_reset = Config.get_value('brevo_last_reset_date', '')

        if last_reset != today_str:
            # New day - reset counter (set_value commits automatically)
            Config.set_value('brevo_emails_sent_today', '0')
            Config.set_value('brevo_last_reset_date', today_str)

    def _check_quota(self) -> bool:
        """Check if quota is available (without incrementing).

        Returns:
            True if email can be sent.

        Raises:
            QuotaExceededError: If daily limit is reached.
        """
        self._reset_quota_if_new_day()

        daily_limit = int(Config.get_value('brevo_daily_limit', '300'))
        sent_today = int(Config.get_value('brevo_emails_sent_today', '0'))

        if sent_today >= daily_limit:
            raise QuotaExceededError(
                f'Tägliches E-Mail-Limit erreicht ({daily_limit} E-Mails). '
                f'Bitte warten Sie bis morgen oder erhöhen Sie das Limit in den Einstellungen.'
            )
        return True

    def _increment_quota(self) -> None:
        """Increment the sent counter after successful send."""
        sent_today = int(Config.get_value('brevo_emails_sent_today', '0'))
        Config.set_value('brevo_emails_sent_today', str(sent_today + 1))

    def get_remaining_quota(self) -> int:
        """Get the number of remaining emails for today.

        Returns:
            Number of emails that can still be sent today.
        """
        self._reset_quota_if_new_day()
        daily_limit = int(Config.get_value('brevo_daily_limit', '300'))
        sent_today = int(Config.get_value('brevo_emails_sent_today', '0'))
        return max(0, daily_limit - sent_today)

    def get_quota_info(self) -> dict:
        """Get quota information for display in admin UI.

        Returns:
            Dict with quota details.
        """
        self._reset_quota_if_new_day()
        daily_limit = int(Config.get_value('brevo_daily_limit', '300'))
        sent_today = int(Config.get_value('brevo_emails_sent_today', '0'))
        remaining = max(0, daily_limit - sent_today)
        percent_used = (sent_today / daily_limit * 100) if daily_limit > 0 else 0

        return {
            'daily_limit': daily_limit,
            'sent_today': sent_today,
            'remaining': remaining,
            'percent_used': min(100, percent_used),
            'is_low': remaining < (daily_limit * 0.1),  # <10% remaining
            'is_exhausted': remaining == 0
        }

    def _send_email(self, to_email: str, to_name: str, subject: str,
                    html_content: str, text_content: str = None) -> EmailResult:
        """Send an email via Brevo API.

        Args:
            to_email: Recipient email
            to_name: Recipient name
            subject: Email subject
            html_content: HTML body
            text_content: Plain text body (optional)

        Returns:
            EmailResult with success status
        """
        self._load_config()

        if not self._api_key:
            return EmailResult(success=False, error='Brevo API-Key nicht konfiguriert')

        # Check quota before sending (but don't increment yet)
        try:
            self._check_quota()
        except QuotaExceededError as e:
            return EmailResult(success=False, error=str(e))

        headers = {
            'accept': 'application/json',
            'api-key': self._api_key,
            'content-type': 'application/json'
        }

        payload = {
            'sender': {
                'name': self._sender_name,
                'email': self._sender_email
            },
            'to': [
                {'email': to_email, 'name': to_name}
            ],
            'subject': subject,
            'htmlContent': html_content
        }

        if text_content:
            payload['textContent'] = text_content

        try:
            response = requests.post(self.BREVO_API_URL, headers=headers, json=payload, timeout=30)

            if response.status_code == 201:
                # Only increment quota on successful send
                self._increment_quota()
                data = response.json()
                return EmailResult(success=True, message_id=data.get('messageId'))
            else:
                error_msg = f'Brevo API Fehler: {response.status_code}'
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', error_msg)
                except Exception:
                    pass
                return EmailResult(success=False, error=error_msg)

        except requests.Timeout:
            return EmailResult(success=False, error='Brevo API Timeout')
        except requests.RequestException as e:
            return EmailResult(success=False, error=f'Netzwerkfehler: {str(e)}')

    def send_zugangsdaten_mail1(self, to_email: str, to_name: str,
                                username: str) -> EmailResult:
        """Send first credentials email with portal URL and username.

        Args:
            to_email: Recipient email
            to_name: Recipient name
            username: The login username (usually email)

        Returns:
            EmailResult
        """
        self._load_config()

        subject = 'Ihre Zugangsdaten zum e-vendo Kundenportal (1/2)'

        html_content = f'''
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #0066cc;">Willkommen im e-vendo Kundenportal</h2>

            <p>Guten Tag {to_name},</p>

            <p>wir haben einen Zugang zum e-vendo Kundenportal für Sie eingerichtet.</p>

            <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0;"><strong>Portal-URL:</strong></p>
                <p style="margin: 10px 0;"><a href="{self._portal_base_url}" style="color: #0066cc;">{self._portal_base_url}</a></p>

                <p style="margin: 20px 0 0 0;"><strong>Ihr Benutzername:</strong></p>
                <p style="margin: 10px 0; font-family: monospace; font-size: 16px;">{username}</p>
            </div>

            <p><strong>Wichtig:</strong> Ihr Passwort erhalten Sie in einer separaten E-Mail.</p>

            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                Mit freundlichen Grüßen<br>
                Ihr e-vendo Team
            </p>
        </body>
        </html>
        '''

        text_content = f'''
Willkommen im e-vendo Kundenportal

Guten Tag {to_name},

wir haben einen Zugang zum e-vendo Kundenportal für Sie eingerichtet.

Portal-URL: {self._portal_base_url}
Ihr Benutzername: {username}

Wichtig: Ihr Passwort erhalten Sie in einer separaten E-Mail.

Mit freundlichen Grüßen
Ihr e-vendo Team
        '''

        return self._send_email(to_email, to_name, subject, html_content, text_content)

    def send_zugangsdaten_mail2(self, to_email: str, to_name: str,
                                password_token: str) -> EmailResult:
        """Send second credentials email with password reveal link.

        Args:
            to_email: Recipient email
            to_name: Recipient name
            password_token: Token for one-time password reveal

        Returns:
            EmailResult
        """
        self._load_config()

        password_url = f'{self._portal_base_url}/passwort/?token={password_token}'

        subject = 'Ihr Passwort für das e-vendo Kundenportal (2/2)'

        html_content = f'''
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #0066cc;">Ihr Passwort</h2>

            <p>Guten Tag {to_name},</p>

            <p>klicken Sie auf den folgenden Link, um Ihr Passwort anzuzeigen:</p>

            <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
                <a href="{password_url}"
                   style="display: inline-block; background-color: #0066cc; color: white;
                          padding: 12px 24px; text-decoration: none; border-radius: 4px;
                          font-weight: bold;">
                    Passwort anzeigen
                </a>
            </div>

            <p style="color: #cc0000;"><strong>Wichtige Hinweise:</strong></p>
            <ul style="color: #666;">
                <li>Das Passwort kann nur <strong>einmal</strong> angezeigt werden</li>
                <li>Der Link ist <strong>48 Stunden</strong> gültig</li>
                <li>Notieren Sie sich das Passwort sicher</li>
                <li>Teilen Sie diesen Link nicht mit anderen Personen</li>
            </ul>

            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                Mit freundlichen Grüßen<br>
                Ihr e-vendo Team
            </p>
        </body>
        </html>
        '''

        text_content = f'''
Ihr Passwort für das e-vendo Kundenportal

Guten Tag {to_name},

klicken Sie auf den folgenden Link, um Ihr Passwort anzuzeigen:

{password_url}

Wichtige Hinweise:
- Das Passwort kann nur einmal angezeigt werden
- Der Link ist 48 Stunden gültig
- Notieren Sie sich das Passwort sicher
- Teilen Sie diesen Link nicht mit anderen Personen

Mit freundlichen Grüßen
Ihr e-vendo Team
        '''

        return self._send_email(to_email, to_name, subject, html_content, text_content)

    def send_fragebogen_einladung(self, to_email: str, to_name: str,
                                  fragebogen_titel: str, magic_token: str,
                                  kunde_firmierung: str = None) -> EmailResult:
        """Send questionnaire invitation with magic-link.

        Args:
            to_email: Recipient email
            to_name: Recipient name
            fragebogen_titel: Title of the questionnaire
            magic_token: Token for direct access (no login required)
            kunde_firmierung: Company name (optional)

        Returns:
            EmailResult
        """
        self._load_config()

        magic_url = f'{self._portal_base_url}/dialog/t/{magic_token}'

        subject = f'Einladung zum Fragebogen: {fragebogen_titel}'

        greeting = f'Guten Tag {to_name}'
        if kunde_firmierung:
            greeting = f'Guten Tag {to_name} ({kunde_firmierung})'

        html_content = f'''
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #0066cc;">{fragebogen_titel}</h2>

            <p>{greeting},</p>

            <p>wir laden Sie herzlich ein, an unserem Fragebogen teilzunehmen.</p>

            <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center;">
                <a href="{magic_url}"
                   style="display: inline-block; background-color: #28a745; color: white;
                          padding: 14px 28px; text-decoration: none; border-radius: 4px;
                          font-weight: bold; font-size: 16px;">
                    Fragebogen starten
                </a>
            </div>

            <p style="color: #666;">
                <strong>Hinweis:</strong> Dieser Link ist persönlich und nur für Sie bestimmt.
                Eine Anmeldung ist nicht erforderlich.
            </p>

            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                Mit freundlichen Grüßen<br>
                Ihr e-vendo Team
            </p>
        </body>
        </html>
        '''

        text_content = f'''
{fragebogen_titel}

{greeting},

wir laden Sie herzlich ein, an unserem Fragebogen teilzunehmen.

Klicken Sie hier, um den Fragebogen zu starten:
{magic_url}

Hinweis: Dieser Link ist persönlich und nur für Sie bestimmt.
Eine Anmeldung ist nicht erforderlich.

Mit freundlichen Grüßen
Ihr e-vendo Team
        '''

        return self._send_email(to_email, to_name, subject, html_content, text_content)


    def send_test_email(self, to_email: str, to_name: str) -> EmailResult:
        """Send a test email to verify Brevo configuration.

        Args:
            to_email: Recipient email
            to_name: Recipient name

        Returns:
            EmailResult with success status and message_id
        """
        from datetime import datetime
        self._load_config()

        timestamp = datetime.now().strftime('%d.%m.%Y %H:%M:%S')

        subject = f'[TEST] e-vendo Portal - Brevo Konfigurationstest ({timestamp})'

        html_content = f'''
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #28a745;">✓ Brevo Test erfolgreich</h2>

            <p>Guten Tag {to_name},</p>

            <p>Dies ist eine Test-E-Mail zur Überprüfung der Brevo-Konfiguration im e-vendo Kundenportal.</p>

            <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #333;">Konfigurationsdetails</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px 0; border-bottom: 1px solid #ddd;"><strong>Zeitstempel:</strong></td>
                        <td style="padding: 8px 0; border-bottom: 1px solid #ddd;">{timestamp}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; border-bottom: 1px solid #ddd;"><strong>Absender E-Mail:</strong></td>
                        <td style="padding: 8px 0; border-bottom: 1px solid #ddd;">{self._sender_email}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; border-bottom: 1px solid #ddd;"><strong>Absender Name:</strong></td>
                        <td style="padding: 8px 0; border-bottom: 1px solid #ddd;">{self._sender_name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; border-bottom: 1px solid #ddd;"><strong>Portal URL:</strong></td>
                        <td style="padding: 8px 0; border-bottom: 1px solid #ddd;">{self._portal_base_url}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;"><strong>API Server:</strong></td>
                        <td style="padding: 8px 0;">api.brevo.com</td>
                    </tr>
                </table>
            </div>

            <p style="color: #28a745;">
                <strong>✓ Die Brevo-Konfiguration funktioniert korrekt.</strong>
            </p>

            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                Mit freundlichen Grüßen<br>
                Ihr e-vendo System
            </p>
        </body>
        </html>
        '''

        text_content = f'''
Brevo Test erfolgreich

Guten Tag {to_name},

Dies ist eine Test-E-Mail zur Überprüfung der Brevo-Konfiguration im e-vendo Kundenportal.

Konfigurationsdetails:
- Zeitstempel: {timestamp}
- Absender E-Mail: {self._sender_email}
- Absender Name: {self._sender_name}
- Portal URL: {self._portal_base_url}
- API Server: api.brevo.com

Die Brevo-Konfiguration funktioniert korrekt.

Mit freundlichen Grüßen
Ihr e-vendo System
        '''

        return self._send_email(to_email, to_name, subject, html_content, text_content)

    def check_api_status(self) -> dict:
        """Check Brevo API status and account info.

        Returns:
            Dict with API status information.
        """
        self._load_config()

        if not self._api_key:
            return {
                'success': False,
                'error': 'API-Key nicht konfiguriert',
                'configured': False
            }

        headers = {
            'accept': 'application/json',
            'api-key': self._api_key
        }

        try:
            # Get account info from Brevo API
            response = requests.get(
                'https://api.brevo.com/v3/account',
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'configured': True,
                    'email': data.get('email', '-'),
                    'company_name': data.get('companyName', '-'),
                    'plan': data.get('plan', [{}])[0].get('type', 'unknown') if data.get('plan') else 'unknown',
                    'credits': data.get('plan', [{}])[0].get('credits', 0) if data.get('plan') else 0
                }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'error': 'Ungültiger API-Key',
                    'configured': True
                }
            else:
                return {
                    'success': False,
                    'error': f'API-Fehler: {response.status_code}',
                    'configured': True
                }

        except requests.Timeout:
            return {
                'success': False,
                'error': 'Timeout bei API-Anfrage',
                'configured': True
            }
        except requests.RequestException as e:
            return {
                'success': False,
                'error': f'Netzwerkfehler: {str(e)}',
                'configured': True
            }

    # ==========================================================================
    # Template-basierte E-Mail-Methoden (mit System-Branding)
    # ==========================================================================

    def _get_template_service(self):
        """Lazy-load the EmailTemplateService to avoid circular imports."""
        from app.services.email_template_service import get_email_template_service
        return get_email_template_service()

    def send_fragebogen_einladung_mit_template(
        self,
        to_email: str,
        to_name: str,
        fragebogen_titel: str,
        magic_token: str,
        kunde: Kunde = None
    ) -> EmailResult:
        """Send questionnaire invitation using database template with branding.

        This method uses the 'fragebogen_einladung' template from the database,
        which includes system branding (logo, colors) and customer footer.

        Args:
            to_email: Recipient email
            to_name: Recipient name
            fragebogen_titel: Title of the questionnaire
            magic_token: Token for direct access (no login required)
            kunde: Optional Kunde for footer customization

        Returns:
            EmailResult
        """
        self._load_config()

        magic_url = f'{self._portal_base_url}/dialog/t/{magic_token}'

        context = {
            'fragebogen_titel': fragebogen_titel,
            'link': magic_url,
            'firmenname': kunde.firmierung if kunde else '',
            'email': to_email,
        }

        try:
            template_service = self._get_template_service()
            rendered = template_service.render('fragebogen_einladung', context, kunde)

            return self._send_email(
                to_email=to_email,
                to_name=to_name,
                subject=rendered['subject'],
                html_content=rendered['html'],
                text_content=rendered.get('text')
            )
        except ValueError as e:
            # Template not found - fall back to non-template method
            return EmailResult(success=False, error=str(e))

    def send_passwort_link(
        self,
        to_email: str,
        to_name: str,
        password_token: str,
        vorname: str = None,
        kunde: Kunde = None
    ) -> EmailResult:
        """Send password setup link for new users using database template.

        Uses the 'passwort_zugangsdaten' template. The recipient can set
        their password by clicking the link.

        Args:
            to_email: Recipient email
            to_name: Recipient display name
            password_token: Token for password setup
            vorname: First name for personalized greeting
            kunde: Optional Kunde for footer customization

        Returns:
            EmailResult
        """
        self._load_config()

        password_url = f'{self._portal_base_url}/passwort/setzen/{password_token}'

        context = {
            'link': password_url,
            'email': to_email,
            'vorname': vorname,
        }

        try:
            template_service = self._get_template_service()
            rendered = template_service.render('passwort_zugangsdaten', context, kunde)

            return self._send_email(
                to_email=to_email,
                to_name=to_name,
                subject=rendered['subject'],
                html_content=rendered['html'],
                text_content=rendered.get('text')
            )
        except ValueError as e:
            return EmailResult(success=False, error=str(e))

    def send_passwort_reset(
        self,
        to_email: str,
        to_name: str,
        reset_token: str,
        kunde: Kunde = None
    ) -> EmailResult:
        """Send password reset link using database template.

        Uses the 'passwort_reset' template. The recipient can reset
        their password by clicking the link.

        Args:
            to_email: Recipient email
            to_name: Recipient display name
            reset_token: Token for password reset
            kunde: Optional Kunde for footer customization

        Returns:
            EmailResult
        """
        self._load_config()

        reset_url = f'{self._portal_base_url}/passwort/reset/{reset_token}'

        context = {
            'link': reset_url,
            'email': to_email,
        }

        try:
            template_service = self._get_template_service()
            rendered = template_service.render('passwort_reset', context, kunde)

            return self._send_email(
                to_email=to_email,
                to_name=to_name,
                subject=rendered['subject'],
                html_content=rendered['html'],
                text_content=rendered.get('text')
            )
        except ValueError as e:
            return EmailResult(success=False, error=str(e))

    def send_test_email_mit_template(
        self,
        to_email: str,
        to_name: str
    ) -> EmailResult:
        """Send test email using database template with branding.

        Uses the 'test_email' template to demonstrate the email configuration
        and branding settings.

        Args:
            to_email: Recipient email
            to_name: Recipient display name

        Returns:
            EmailResult
        """
        context = {
            'email': to_email,
        }

        try:
            template_service = self._get_template_service()
            rendered = template_service.render('test_email', context)

            return self._send_email(
                to_email=to_email,
                to_name=to_name,
                subject=rendered['subject'],
                html_content=rendered['html'],
                text_content=rendered.get('text')
            )
        except ValueError as e:
            return EmailResult(success=False, error=str(e))

    def send_with_template(
        self,
        template_schluessel: str,
        to_email: str,
        to_name: str,
        context: dict,
        kunde: Kunde = None
    ) -> EmailResult:
        """Send email using any database template.

        Generic method to send emails with any registered template.

        Args:
            template_schluessel: Template key (e.g., 'fragebogen_einladung')
            to_email: Recipient email
            to_name: Recipient display name
            context: Variables for template rendering
            kunde: Optional Kunde for footer customization

        Returns:
            EmailResult
        """
        try:
            template_service = self._get_template_service()
            rendered = template_service.render(template_schluessel, context, kunde)

            return self._send_email(
                to_email=to_email,
                to_name=to_name,
                subject=rendered['subject'],
                html_content=rendered['html'],
                text_content=rendered.get('text')
            )
        except ValueError as e:
            return EmailResult(success=False, error=str(e))


# Singleton instance
_brevo_service = None


def get_brevo_service() -> BrevoService:
    """Get the Brevo service singleton."""
    global _brevo_service
    if _brevo_service is None:
        _brevo_service = BrevoService()
    return _brevo_service
