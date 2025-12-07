"""Authentication routes."""
from datetime import datetime
from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField
from wtforms.validators import DataRequired, Email

from app import db
from app.models import User

auth_bp = Blueprint('auth', __name__)


class LoginForm(FlaskForm):
    """Login form."""
    email = StringField('E-Mail', validators=[DataRequired(), Email()])
    password = PasswordField('Passwort', validators=[DataRequired()])
    remember = BooleanField('Angemeldet bleiben')


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Zugriff verweigert. Admin-Rechte erforderlich.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def mitarbeiter_required(f):
    """Decorator to require mitarbeiter or admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.rolle not in ['admin', 'mitarbeiter']:
            flash('Zugriff verweigert. Mitarbeiter-Rechte erforderlich.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and user.check_password(form.password.data):
            if not user.aktiv:
                flash('Ihr Konto ist deaktiviert.', 'danger')
                return render_template('login.html', form=form)

            login_user(user, remember=form.remember.data)
            user.last_login = datetime.utcnow()
            db.session.commit()

            flash(f'Willkommen, {user.vorname}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('main.dashboard'))

        flash('Ungueltige E-Mail oder Passwort.', 'danger')

    return render_template('login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout user."""
    logout_user()
    flash('Sie wurden abgemeldet.', 'info')
    return redirect(url_for('auth.login'))
