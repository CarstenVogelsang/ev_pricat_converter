"""Kunden (Customer) routes for Lead&Kundenreport app."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField
from wtforms.validators import DataRequired, URL, Optional

from sqlalchemy import func

from app import db
from app.models import Kunde, KundeCI, KundeApiNutzung, User, Branche, Verband, KundeBranche, KundeVerband
from app.services import FirecrawlService
from app.routes.auth import mitarbeiter_required

kunden_bp = Blueprint('kunden', __name__, url_prefix='/kunden')


class KundeForm(FlaskForm):
    """Form for creating/editing Kunde."""
    firmierung = StringField('Firmierung', validators=[DataRequired()])
    ev_kdnr = StringField('e-vendo Kundennummer', validators=[Optional()])
    strasse = StringField('Straße', validators=[Optional()])
    plz = StringField('PLZ', validators=[Optional()])
    ort = StringField('Ort', validators=[Optional()])
    land = StringField('Land', validators=[Optional()])
    adresse = TextAreaField('Adresse (alt)', validators=[Optional()])
    website_url = StringField('Website URL', validators=[Optional(), URL()])
    shop_url = StringField('Online-Shop URL', validators=[Optional(), URL()])
    notizen = TextAreaField('Notizen', validators=[Optional()])
    aktiv = BooleanField('Aktiv', default=True)


@kunden_bp.route('/')
@login_required
@mitarbeiter_required
def liste():
    """List all Kunden with optional filters."""
    # Get filter parameters
    branche_id = request.args.get('branche', type=int)
    verband_id = request.args.get('verband', type=int)
    status = request.args.get('status', 'alle')

    # Base query
    query = Kunde.query

    # Apply filters
    if branche_id:
        query = query.join(KundeBranche).filter(KundeBranche.branche_id == branche_id)
    if verband_id:
        query = query.join(KundeVerband).filter(KundeVerband.verband_id == verband_id)
    if status == 'aktiv':
        query = query.filter(Kunde.aktiv == True)
    elif status == 'inaktiv':
        query = query.filter(Kunde.aktiv == False)

    kunden = query.order_by(Kunde.firmierung).all()

    # Get all Branchen and Verbände for filter dropdowns
    alle_branchen = Branche.query.filter_by(aktiv=True).order_by(Branche.sortierung).all()
    alle_verbaende = Verband.query.filter_by(aktiv=True).order_by(Verband.name).all()

    return render_template(
        'kunden/liste.html',
        kunden=kunden,
        alle_branchen=alle_branchen,
        alle_verbaende=alle_verbaende,
        filter_branche=branche_id,
        filter_verband=verband_id,
        filter_status=status
    )


@kunden_bp.route('/neu', methods=['GET', 'POST'])
@login_required
@mitarbeiter_required
def neu():
    """Create new Kunde."""
    form = KundeForm()

    if form.validate_on_submit():
        kunde = Kunde(
            firmierung=form.firmierung.data,
            ev_kdnr=form.ev_kdnr.data or None,
            strasse=form.strasse.data,
            plz=form.plz.data,
            ort=form.ort.data,
            land=form.land.data or 'Deutschland',
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

    # Get all active Branchen and Verbände for display
    alle_branchen = Branche.query.filter_by(aktiv=True).order_by(Branche.sortierung).all()
    alle_verbaende = Verband.query.filter_by(aktiv=True).order_by(Verband.name).all()

    # Get IDs of assigned Branchen and Verbände for the template
    kunde_branchen_ids = {kb.branche_id for kb in kunde.branchen}
    kunde_primaer_ids = {kb.branche_id for kb in kunde.branchen if kb.ist_primaer}
    kunde_verbaende_ids = {kv.verband_id for kv in kunde.verbaende}

    return render_template(
        'kunden/detail.html',
        kunde=kunde,
        alle_branchen=alle_branchen,
        alle_verbaende=alle_verbaende,
        kunde_branchen_ids=kunde_branchen_ids,
        kunde_primaer_ids=kunde_primaer_ids,
        kunde_verbaende_ids=kunde_verbaende_ids
    )


@kunden_bp.route('/<int:id>/bearbeiten', methods=['GET', 'POST'])
@login_required
@mitarbeiter_required
def bearbeiten(id):
    """Edit Kunde."""
    kunde = Kunde.query.get_or_404(id)
    form = KundeForm(obj=kunde)

    if form.validate_on_submit():
        kunde.firmierung = form.firmierung.data
        kunde.ev_kdnr = form.ev_kdnr.data or None
        kunde.strasse = form.strasse.data
        kunde.plz = form.plz.data
        kunde.ort = form.ort.data
        kunde.land = form.land.data or 'Deutschland'
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


# ===== AJAX Endpoints for Branchen/Verbände =====

@kunden_bp.route('/<int:id>/branche/<int:branche_id>', methods=['POST'])
@login_required
@mitarbeiter_required
def toggle_branche(id, branche_id):
    """Toggle Branche assignment for a Kunde."""
    kunde = Kunde.query.get_or_404(id)
    branche = Branche.query.get_or_404(branche_id)

    existing = KundeBranche.query.filter_by(
        kunde_id=id, branche_id=branche_id
    ).first()

    if existing:
        # Remove assignment
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'success': True, 'action': 'removed'})
    else:
        # Add assignment
        kb = KundeBranche(kunde_id=id, branche_id=branche_id, ist_primaer=False)
        db.session.add(kb)
        db.session.commit()
        return jsonify({'success': True, 'action': 'added'})


@kunden_bp.route('/<int:id>/branche/<int:branche_id>/primaer', methods=['POST'])
@login_required
@mitarbeiter_required
def toggle_primaer_branche(id, branche_id):
    """Toggle primary status for a Branche assignment. Max 3 primary branches."""
    kunde = Kunde.query.get_or_404(id)

    existing = KundeBranche.query.filter_by(
        kunde_id=id, branche_id=branche_id
    ).first()

    if not existing:
        # Branch not assigned yet - assign and make primary
        primaer_count = KundeBranche.query.filter_by(kunde_id=id, ist_primaer=True).count()
        if primaer_count >= 3:
            return jsonify({
                'success': False,
                'error': 'Maximal 3 Primärbranchen erlaubt'
            })
        kb = KundeBranche(kunde_id=id, branche_id=branche_id, ist_primaer=True)
        db.session.add(kb)
        db.session.commit()
        return jsonify({'success': True, 'action': 'added_primary'})
    else:
        if existing.ist_primaer:
            # Remove primary status
            existing.ist_primaer = False
            db.session.commit()
            return jsonify({'success': True, 'action': 'removed_primary'})
        else:
            # Make primary (check limit)
            primaer_count = KundeBranche.query.filter_by(kunde_id=id, ist_primaer=True).count()
            if primaer_count >= 3:
                return jsonify({
                    'success': False,
                    'error': 'Maximal 3 Primärbranchen erlaubt'
                })
            existing.ist_primaer = True
            db.session.commit()
            return jsonify({'success': True, 'action': 'set_primary'})


@kunden_bp.route('/<int:id>/verband/<int:verband_id>', methods=['POST'])
@login_required
@mitarbeiter_required
def toggle_verband(id, verband_id):
    """Toggle Verband membership for a Kunde."""
    kunde = Kunde.query.get_or_404(id)
    verband = Verband.query.get_or_404(verband_id)

    existing = KundeVerband.query.filter_by(
        kunde_id=id, verband_id=verband_id
    ).first()

    if existing:
        # Remove membership
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'success': True, 'action': 'removed'})
    else:
        # Add membership
        kv = KundeVerband(kunde_id=id, verband_id=verband_id)
        db.session.add(kv)
        db.session.commit()
        return jsonify({'success': True, 'action': 'added'})
