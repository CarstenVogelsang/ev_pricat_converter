"""Password reveal routes for one-time password display.

Blueprint: passwort_bp
Prefix: /passwort/

Routes:
- GET /?token=... - Display password once
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for

from app.models import PasswordToken
from app import db


passwort_bp = Blueprint('passwort', __name__, url_prefix='/passwort')


@passwort_bp.route('/')
def reveal():
    """Display the password from a valid token (one-time only).

    Query params:
        token: The password reveal token

    Templates:
        - passwort/reveal.html - Success, shows password
        - passwort/invalid.html - Token not found
        - passwort/expired.html - Token expired or already used
    """
    token = request.args.get('token')

    if not token:
        return render_template('passwort/invalid.html',
                               error='Kein Token angegeben')

    # Find the token
    password_token = PasswordToken.query.filter_by(token=token).first()

    if not password_token:
        return render_template('passwort/invalid.html',
                               error='Ungültiger Token')

    # Check if already revealed
    if password_token.is_revealed:
        return render_template('passwort/expired.html',
                               reason='bereits_angezeigt',
                               message='Das Passwort wurde bereits angezeigt und ist nicht mehr verfügbar.')

    # Check if expired
    if password_token.is_expired:
        return render_template('passwort/expired.html',
                               reason='abgelaufen',
                               message='Der Link ist abgelaufen. Bitte kontaktieren Sie uns für neue Zugangsdaten.')

    # Reveal the password (this marks it as used)
    password = password_token.reveal()
    db.session.commit()

    if not password:
        return render_template('passwort/expired.html',
                               reason='fehler',
                               message='Das Passwort konnte nicht angezeigt werden.')

    # Get user info for display
    user = password_token.user

    return render_template('passwort/reveal.html',
                           password=password,
                           user=user)
