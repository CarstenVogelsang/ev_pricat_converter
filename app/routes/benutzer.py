"""User administration routes.

Blueprint: benutzer_bp
Prefix: /admin/benutzer/

Only accessible for admin role.

Routes:
- GET / - List all users
- GET/POST /neu - Create new user
- GET/POST /<id> - Edit user
- POST /<id>/toggle-aktiv - Toggle active status
- POST /<id>/reset-passwort - Reset password
- POST /<id>/delete - Delete user
"""
import secrets
import string
from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user

from app import db
from app.models import User, Rolle
from app.services import log_mittel


benutzer_bp = Blueprint('benutzer', __name__, url_prefix='/admin/benutzer')


def require_admin():
    """Check if current user is admin."""
    if not current_user.is_authenticated:
        abort(401)
    if not current_user.is_admin:
        abort(403)


@benutzer_bp.before_request
def check_access():
    """Ensure user has admin access."""
    require_admin()


def generate_password(length=12):
    """Generate a random secure password."""
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@benutzer_bp.route('/')
def index():
    """List all users."""
    # Filter parameters
    rolle_filter = request.args.get('rolle', type=int)
    aktiv_filter = request.args.get('aktiv')

    query = User.query

    if rolle_filter:
        query = query.filter(User.rolle_id == rolle_filter)

    if aktiv_filter == '1':
        query = query.filter(User.aktiv == True)
    elif aktiv_filter == '0':
        query = query.filter(User.aktiv == False)

    users = query.order_by(User.nachname, User.vorname).all()
    rollen = Rolle.query.order_by(Rolle.name).all()

    return render_template('administration/benutzer.html',
                           users=users,
                           rollen=rollen,
                           rolle_filter=rolle_filter,
                           aktiv_filter=aktiv_filter)


@benutzer_bp.route('/neu', methods=['GET', 'POST'])
def neu():
    """Create a new user."""
    rollen = Rolle.query.order_by(Rolle.name).all()

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        vorname = request.form.get('vorname', '').strip()
        nachname = request.form.get('nachname', '').strip()
        rolle_id = request.form.get('rolle_id', type=int)
        passwort = request.form.get('passwort', '').strip()
        anrede = request.form.get('anrede', '').strip() or None
        kommunikation_stil = request.form.get('kommunikation_stil', '').strip() or None

        # Validation
        errors = []
        if not email:
            errors.append('E-Mail ist erforderlich.')
        elif User.query.filter_by(email=email).first():
            errors.append('Diese E-Mail-Adresse wird bereits verwendet.')

        if not vorname:
            errors.append('Vorname ist erforderlich.')
        if not nachname:
            errors.append('Nachname ist erforderlich.')
        if not rolle_id:
            errors.append('Rolle ist erforderlich.')

        if not passwort:
            passwort = generate_password()
            flash(f'Generiertes Passwort: {passwort}', 'info')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('administration/benutzer_form.html',
                                   user=None,
                                   rollen=rollen,
                                   email=email,
                                   vorname=vorname,
                                   nachname=nachname,
                                   rolle_id=rolle_id,
                                   anrede=anrede,
                                   kommunikation_stil=kommunikation_stil)

        # Create user
        user = User(
            email=email,
            vorname=vorname,
            nachname=nachname,
            rolle_id=rolle_id,
            anrede=anrede,
            kommunikation_stil=kommunikation_stil,
            aktiv=True
        )
        user.set_password(passwort)

        db.session.add(user)
        db.session.commit()

        log_mittel('system', 'benutzer_erstellt', f'Benutzer {user.full_name} ({user.email}) erstellt')

        flash(f'Benutzer {user.full_name} wurde erstellt.', 'success')
        return redirect(url_for('benutzer.index'))

    return render_template('administration/benutzer_form.html',
                           user=None,
                           rollen=rollen,
                           email='',
                           vorname='',
                           nachname='',
                           rolle_id=None,
                           anrede=None,
                           kommunikation_stil=None)


@benutzer_bp.route('/<int:id>', methods=['GET', 'POST'])
def edit(id):
    """Edit an existing user."""
    user = User.query.get_or_404(id)
    rollen = Rolle.query.order_by(Rolle.name).all()

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        vorname = request.form.get('vorname', '').strip()
        nachname = request.form.get('nachname', '').strip()
        rolle_id = request.form.get('rolle_id', type=int)
        anrede = request.form.get('anrede', '').strip() or None
        kommunikation_stil = request.form.get('kommunikation_stil', '').strip() or None

        # Validation
        errors = []
        if not email:
            errors.append('E-Mail ist erforderlich.')
        elif email != user.email and User.query.filter_by(email=email).first():
            errors.append('Diese E-Mail-Adresse wird bereits verwendet.')

        if not vorname:
            errors.append('Vorname ist erforderlich.')
        if not nachname:
            errors.append('Nachname ist erforderlich.')
        if not rolle_id:
            errors.append('Rolle ist erforderlich.')

        if errors:
            for error in errors:
                flash(error, 'danger')
            return render_template('administration/benutzer_form.html',
                                   user=user,
                                   rollen=rollen,
                                   email=email,
                                   vorname=vorname,
                                   nachname=nachname,
                                   rolle_id=rolle_id,
                                   anrede=anrede,
                                   kommunikation_stil=kommunikation_stil)

        # Update user
        user.email = email
        user.vorname = vorname
        user.nachname = nachname
        user.rolle_id = rolle_id
        user.anrede = anrede
        user.kommunikation_stil = kommunikation_stil

        db.session.commit()

        log_mittel('system', 'benutzer_aktualisiert', f'Benutzer {user.full_name} aktualisiert')

        flash(f'Benutzer {user.full_name} wurde aktualisiert.', 'success')
        return redirect(url_for('benutzer.index'))

    return render_template('administration/benutzer_form.html',
                           user=user,
                           rollen=rollen,
                           email=user.email,
                           vorname=user.vorname,
                           nachname=user.nachname,
                           rolle_id=user.rolle_id,
                           anrede=user.anrede,
                           kommunikation_stil=user.kommunikation_stil)


@benutzer_bp.route('/<int:id>/toggle-aktiv', methods=['POST'])
def toggle_aktiv(id):
    """Toggle user active status."""
    user = User.query.get_or_404(id)

    # Prevent deactivating yourself
    if user.id == current_user.id:
        flash('Sie können sich nicht selbst deaktivieren.', 'warning')
        return redirect(url_for('benutzer.index'))

    user.aktiv = not user.aktiv
    db.session.commit()

    status = 'aktiviert' if user.aktiv else 'deaktiviert'
    log_mittel('system', 'benutzer_status', f'Benutzer {user.full_name} {status}')

    flash(f'Benutzer {user.full_name} wurde {status}.', 'success')
    return redirect(url_for('benutzer.index'))


@benutzer_bp.route('/<int:id>/set-passwort', methods=['POST'])
def set_passwort(id):
    """Set user password (manual or generated by admin)."""
    user = User.query.get_or_404(id)

    new_password = request.form.get('new_password', '').strip()

    # Validate password
    if not new_password:
        flash('Bitte ein Passwort eingeben.', 'danger')
        return redirect(url_for('benutzer.edit', id=id))

    if len(new_password) < 8:
        flash('Passwort muss mindestens 8 Zeichen haben.', 'danger')
        return redirect(url_for('benutzer.edit', id=id))

    user.set_password(new_password)
    db.session.commit()

    log_mittel('system', 'benutzer_passwort', f'Passwort für {user.full_name} gesetzt')

    flash(f'Passwort für {user.full_name} wurde gespeichert.', 'success')
    return redirect(url_for('benutzer.edit', id=id))


@benutzer_bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    """Delete a user."""
    user = User.query.get_or_404(id)

    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('Sie können sich nicht selbst löschen.', 'warning')
        return redirect(url_for('benutzer.index'))

    # Check if user has associated Kunden (1:N relationship)
    if user.kunde_zuordnungen:
        kunden_namen = ', '.join([zuo.kunde.firmierung for zuo in user.kunde_zuordnungen])
        flash(f'Benutzer {user.full_name} ist mit Kunde(n) verknüpft: {kunden_namen}. '
              f'Bitte zuerst die Zuordnung(en) entfernen.', 'danger')
        return redirect(url_for('benutzer.index'))

    user_name = user.full_name
    db.session.delete(user)
    db.session.commit()

    log_mittel('system', 'benutzer_geloescht', f'Benutzer {user_name} gelöscht')

    flash(f'Benutzer {user_name} wurde gelöscht.', 'success')
    return redirect(url_for('benutzer.index'))
