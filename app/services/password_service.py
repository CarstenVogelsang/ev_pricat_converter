"""Password Service for Kunde user account management.

Handles:
- User account creation for Kunden
- Secure password generation
- Password token creation
- Credential email sending (2 separate emails)
"""
import secrets
import string
from dataclasses import dataclass
from typing import Optional, Tuple

from app import db
from app.models import User, Kunde, Rolle, PasswordToken, KundeBenutzer
from app.services.email_service import get_brevo_service, EmailResult


@dataclass
class UserCreationResult:
    """Result of user creation operation."""
    success: bool
    user: Optional[User] = None
    password_token: Optional[PasswordToken] = None
    is_hauptbenutzer: bool = False
    error: Optional[str] = None


@dataclass
class CredentialsSendResult:
    """Result of sending credentials emails."""
    success: bool
    mail1_result: Optional[EmailResult] = None
    mail2_result: Optional[EmailResult] = None
    error: Optional[str] = None


class PasswordService:
    """Service for managing Kunde user accounts and credentials."""

    @staticmethod
    def generate_secure_password(length: int = 16) -> str:
        """Generate a secure random password.

        Args:
            length: Password length (default 16)

        Returns:
            Random password with mixed case, digits, and special chars
        """
        # Character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special = '!@#$%&*+-='

        # Ensure at least one of each type
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(special)
        ]

        # Fill remaining with random chars from all sets
        all_chars = lowercase + uppercase + digits + special
        password.extend(secrets.choice(all_chars) for _ in range(length - 4))

        # Shuffle to avoid predictable positions
        password_list = list(password)
        secrets.SystemRandom().shuffle(password_list)

        return ''.join(password_list)

    @staticmethod
    def get_kunde_rolle() -> Optional[Rolle]:
        """Get the 'kunde' role from database."""
        return Rolle.query.filter_by(name='kunde').first()

    def create_user_for_kunde(self, kunde: Kunde, email: str,
                              vorname: str, nachname: str) -> UserCreationResult:
        """Create a user account for a Kunde.

        The first user created for a Kunde automatically becomes Hauptbenutzer.

        Args:
            kunde: The Kunde to create user for
            email: Email address for the user
            vorname: First name
            nachname: Last name

        Returns:
            UserCreationResult with user, password token, and hauptbenutzer flag
        """
        # Validations
        email = email.lower().strip()

        if User.query.filter_by(email=email).first():
            return UserCreationResult(
                success=False,
                error=f'E-Mail-Adresse {email} ist bereits vergeben'
            )

        kunde_rolle = self.get_kunde_rolle()
        if not kunde_rolle:
            return UserCreationResult(
                success=False,
                error='Rolle "kunde" nicht gefunden'
            )

        try:
            # Check if this will be the first user (becomes Hauptbenutzer)
            is_first_user = len(kunde.benutzer_zuordnungen) == 0
            is_hauptbenutzer = is_first_user

            # Generate password
            password_plain = self.generate_secure_password()

            # Create user
            user = User(
                email=email,
                vorname=vorname,
                nachname=nachname,
                rolle_id=kunde_rolle.id,
                aktiv=True
            )
            user.set_password(password_plain)
            db.session.add(user)
            db.session.flush()  # Get user.id

            # Create KundeBenutzer junction entry
            kunde_benutzer = KundeBenutzer(
                kunde_id=kunde.id,
                user_id=user.id,
                ist_hauptbenutzer=is_hauptbenutzer
            )
            db.session.add(kunde_benutzer)

            # Update legacy kunde.user_id for backward compatibility (if first user)
            if is_first_user:
                kunde.user_id = user.id

            # Create password token
            password_token = PasswordToken.create_for_user(
                user_id=user.id,
                password_plain=password_plain
            )
            db.session.add(password_token)

            db.session.commit()

            return UserCreationResult(
                success=True,
                user=user,
                password_token=password_token,
                is_hauptbenutzer=is_hauptbenutzer
            )

        except Exception as e:
            db.session.rollback()
            return UserCreationResult(
                success=False,
                error=f'Fehler beim Erstellen: {str(e)}'
            )

    def send_credentials(self, user: User,
                         password_token: PasswordToken) -> CredentialsSendResult:
        """Send both credential emails to the user.

        Args:
            user: The user to send credentials to
            password_token: The password token for reveal link

        Returns:
            CredentialsSendResult with status of both emails
        """
        brevo = get_brevo_service()

        if not brevo.is_configured:
            return CredentialsSendResult(
                success=False,
                error='E-Mail-Service (Brevo) ist nicht konfiguriert'
            )

        # Send first email (Portal URL + Username)
        mail1_result = brevo.send_zugangsdaten_mail1(
            to_email=user.email,
            to_name=user.full_name,
            username=user.email
        )

        if not mail1_result.success:
            return CredentialsSendResult(
                success=False,
                mail1_result=mail1_result,
                error=f'E-Mail 1 fehlgeschlagen: {mail1_result.error}'
            )

        # Send second email (Password link)
        mail2_result = brevo.send_zugangsdaten_mail2(
            to_email=user.email,
            to_name=user.full_name,
            password_token=password_token.token
        )

        if not mail2_result.success:
            return CredentialsSendResult(
                success=False,
                mail1_result=mail1_result,
                mail2_result=mail2_result,
                error=f'E-Mail 2 fehlgeschlagen: {mail2_result.error}'
            )

        return CredentialsSendResult(
            success=True,
            mail1_result=mail1_result,
            mail2_result=mail2_result
        )

    def create_and_send(self, kunde: Kunde, email: str,
                        vorname: str, nachname: str) -> Tuple[UserCreationResult, Optional[CredentialsSendResult]]:
        """Create user and send credentials in one operation.

        Args:
            kunde: The Kunde to create user for
            email: Email address
            vorname: First name
            nachname: Last name

        Returns:
            Tuple of (UserCreationResult, CredentialsSendResult or None)
        """
        # First create the user
        creation_result = self.create_user_for_kunde(kunde, email, vorname, nachname)

        if not creation_result.success:
            return creation_result, None

        # Then send credentials
        send_result = self.send_credentials(
            creation_result.user,
            creation_result.password_token
        )

        return creation_result, send_result


# Singleton instance
_password_service = None


def get_password_service() -> PasswordService:
    """Get the password service singleton."""
    global _password_service
    if _password_service is None:
        _password_service = PasswordService()
    return _password_service
