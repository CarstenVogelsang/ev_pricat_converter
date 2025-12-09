"""Kunden (Customer) routes for Lead&Kundenreport app."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, URL, Optional

from sqlalchemy import func

from app import db
from app.models import Kunde, KundeCI, KundeApiNutzung, User
from app.services import FirecrawlService
from app.routes.auth import mitarbeiter_required

kunden_bp = Blueprint('kunden', __name__, url_prefix='/kunden')


class KundeForm(FlaskForm):
    """Form for creating/editing Kunde."""
    firmierung = StringField('Firmierung', validators=[DataRequired()])
    adresse = TextAreaField('Adresse', validators=[Optional()])
    website_url = StringField('Website URL', validators=[Optional(), URL()])
    shop_url = StringField('Online-Shop URL', validators=[Optional(), URL()])
    notizen = TextAreaField('Notizen', validators=[Optional()])
    aktiv = BooleanField('Aktiv', default=True)


@kunden_bp.route('/')
@login_required
@mitarbeiter_required
def liste():
    """List all Kunden."""
    kunden = Kunde.query.order_by(Kunde.firmierung).all()
    return render_template('kunden/liste.html', kunden=kunden)


@kunden_bp.route('/neu', methods=['GET', 'POST'])
@login_required
@mitarbeiter_required
def neu():
    """Create new Kunde."""
    form = KundeForm()

    if form.validate_on_submit():
        kunde = Kunde(
            firmierung=form.firmierung.data,
            adresse=form.adresse.data,
            website_url=form.website_url.data or None,
            shop_url=form.shop_url.data or None,
            notizen=form.notizen.data,
            aktiv=form.aktiv.data
        )
        db.session.add(kunde)
        db.session.commit()
        flash(f'Kunde "{kunde.firmierung}" wurde angelegt.', 'success')
        return redirect(url_for('kunden.detail', id=kunde.id))

    return render_template('kunden/form.html', form=form, titel='Neuer Kunde', kunde=None)


@kunden_bp.route('/<int:id>')
@login_required
@mitarbeiter_required
def detail(id):
    """View Kunde detail."""
    kunde = Kunde.query.get_or_404(id)
    return render_template('kunden/detail.html', kunde=kunde)


@kunden_bp.route('/<int:id>/bearbeiten', methods=['GET', 'POST'])
@login_required
@mitarbeiter_required
def bearbeiten(id):
    """Edit Kunde."""
    kunde = Kunde.query.get_or_404(id)
    form = KundeForm(obj=kunde)

    if form.validate_on_submit():
        kunde.firmierung = form.firmierung.data
        kunde.adresse = form.adresse.data
        kunde.website_url = form.website_url.data or None
        kunde.shop_url = form.shop_url.data or None
        kunde.notizen = form.notizen.data
        kunde.aktiv = form.aktiv.data
        db.session.commit()
        flash(f'Kunde "{kunde.firmierung}" wurde aktualisiert.', 'success')
        return redirect(url_for('kunden.detail', id=kunde.id))

    return render_template('kunden/form.html', form=form, titel='Kunde bearbeiten', kunde=kunde)


@kunden_bp.route('/<int:id>/loeschen', methods=['POST'])
@login_required
@mitarbeiter_required
def loeschen(id):
    """Delete Kunde."""
    kunde = Kunde.query.get_or_404(id)
    firmierung = kunde.firmierung
    db.session.delete(kunde)
    db.session.commit()
    flash(f'Kunde "{firmierung}" wurde geloescht.', 'success')
    return redirect(url_for('kunden.liste'))


@kunden_bp.route('/<int:id>/analyse', methods=['POST'])
@login_required
@mitarbeiter_required
def analyse(id):
    """Trigger Firecrawl website analysis."""
    kunde = Kunde.query.get_or_404(id)

    if not kunde.website_url:
        flash('Website-URL muss gesetzt sein fuer die Analyse.', 'warning')
        return redirect(url_for('kunden.detail', id=id))

    firecrawl_service = FirecrawlService()
    result = firecrawl_service.analyze_branding(kunde, user_id=current_user.id)

    if result.success:
        flash('Website-Analyse erfolgreich abgeschlossen.', 'success')
    else:
        flash(f'Analyse fehlgeschlagen: {result.error}', 'danger')

    return redirect(url_for('kunden.detail', id=id))


@kunden_bp.route('/<int:id>/reparse-logo', methods=['POST'])
@login_required
@mitarbeiter_required
def reparse_logo(id):
    """Re-extract logo from stored raw_response without new API call."""
    kunde = Kunde.query.get_or_404(id)

    if not kunde.ci or not kunde.ci.raw_response:
        flash('Kein Raw Response vorhanden. Bitte erst Website-Analyse durchfuehren.', 'warning')
        return redirect(url_for('kunden.detail', id=id))

    logo_url = FirecrawlService.reparse_logo_from_raw(kunde.ci)

    if logo_url:
        flash(f'Logo erfolgreich extrahiert.', 'success')
    else:
        flash('Kein Logo im Raw Response gefunden.', 'warning')

    return redirect(url_for('kunden.detail', id=id))


@kunden_bp.route('/<int:id>/projekt')
@login_required
@mitarbeiter_required
def projekt(id):
    """View Kunde project page with activities and API costs."""
    kunde = Kunde.query.get_or_404(id)

    # Get API usage for this Kunde (all users)
    api_nutzungen = KundeApiNutzung.query.filter_by(kunde_id=id)\
        .order_by(KundeApiNutzung.created_at.desc()).all()

    # Calculate totals
    totals = db.session.query(
        func.sum(KundeApiNutzung.credits_used).label('total_credits'),
        func.sum(KundeApiNutzung.kosten_euro).label('total_kosten'),
        func.count(KundeApiNutzung.id).label('anzahl_calls')
    ).filter(KundeApiNutzung.kunde_id == id).first()

    # Usage per user
    per_user = db.session.query(
        User.id,
        User.vorname,
        User.nachname,
        func.sum(KundeApiNutzung.credits_used).label('credits'),
        func.sum(KundeApiNutzung.kosten_euro).label('kosten'),
        func.count(KundeApiNutzung.id).label('calls')
    ).join(User, KundeApiNutzung.user_id == User.id)\
        .filter(KundeApiNutzung.kunde_id == id)\
        .group_by(User.id, User.vorname, User.nachname).all()

    return render_template(
        'kunden/projekt.html',
        kunde=kunde,
        api_nutzungen=api_nutzungen,
        totals=totals,
        per_user=per_user
    )
