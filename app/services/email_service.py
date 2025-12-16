"""Brevo E-Mail Service for transactional emails.

Uses Brevo (formerly Sendinblue) REST API for sending:
- Zugangsdaten E-Mails (2 separate emails for security)
- Fragebogen-Einladungen mit Magic-Link

Includes rate limiting for Brevo Free Plan (300 emails/day).
"""
import requests
from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.models import Config


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
        self._api_key = Config.get('brevo_api_key')
        self._sender_email = Config.get('brevo_sender_email', 'noreply@e-vendo.de')
        self._sender_name = Config.get('brevo_sender_name', 'e-vendo AG')
        self._portal_base_url = Config.get('portal_base_url', 'https://portal.e-vendo.de')

    @property
    def is_configured(self) -> bool:
        """Check if Brevo is configured."""
        self._load_config()
        return bool(self._api_key)

    def _reset_quota_if_new_day(self) -> None:
        """Reset the daily quota counter if a new day has started."""
        from app import db
        today_str = date.today().isoformat()
        last_reset = Config.get('brevo_last_reset_date', '')

        if last_reset != today_str:
            # New day - reset counter
            Config.set('brevo_emails_sent_today', '0')
            Config.set('brevo_last_reset_date', today_str)
            db.session.commit()

    def _check_and_update_quota(self) -> bool:
        """Check if quota is available and increment counter.

        Returns:
            True if email can be sent, False if quota exceeded.

        Raises:
            QuotaExceededError: If daily limit is reached.
        """
        from app import db
        self._reset_quota_if_new_day()

        daily_limit = int(Config.get('brevo_daily_limit', '300'))
        sent_today = int(Config.get('brevo_emails_sent_today', '0'))

        if sent_today >= daily_limit:
            raise QuotaExceededError(
                f'Tägliches E-Mail-Limit erreicht ({daily_limit} E-Mails). '
                f'Bitte warten Sie bis morgen oder erhöhen Sie das Limit in den Einstellungen.'
            )

        # Increment counter
        Config.set('brevo_emails_sent_today', str(sent_today + 1))
        db.session.commit()
        return True

    def get_remaining_quota(self) -> int:
        """Get the number of remaining emails for today.

        Returns:
            Number of emails that can still be sent today.
        """
        self._reset_quota_if_new_day()
        daily_limit = int(Config.get('brevo_daily_limit', '300'))
        sent_today = int(Config.get('brevo_emails_sent_today', '0'))
        return max(0, daily_limit - sent_today)

    def get_quota_info(self) -> dict:
        """Get quota information for display in admin UI.

        Returns:
            Dict with quota details.
        """
        self._reset_quota_if_new_day()
        daily_limit = int(Config.get('brevo_daily_limit', '300'))
        sent_today = int(Config.get('brevo_emails_sent_today', '0'))
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

        # Check quota before sending
        try:
            self._check_and_update_quota()
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


# Singleton instance
_brevo_service = None


def get_brevo_service() -> BrevoService:
    """Get the Brevo service singleton."""
    global _brevo_service
    if _brevo_service is None:
        _brevo_service = BrevoService()
    return _brevo_service
