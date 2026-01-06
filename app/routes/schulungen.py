"""User-facing routes for Schulungen (PRD-010).

Blueprint: schulungen_bp
Prefix: /schulungen/

This module provides routes for:
- Public view of available trainings (with iframe variant)
- Customer booking and cancellation
- Customer's own bookings overview
"""
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app import db
from app.models import (
    Schulung, Schulungsthema, Schulungsdurchfuehrung,
    Schulungsbuchung, BuchungStatus, DurchfuehrungStatus
)
from app.services import log_event

schulungen_bp = Blueprint('schulungen', __name__, url_prefix='/schulungen')


# =============================================================================
# PUBLIC ROUTES (no login required)
# =============================================================================

@schulungen_bp.route('/')
def liste():
    """List all active trainings with upcoming executions."""
    # Get filter parameters
    suche = request.args.get('suche', '').strip()

    if suche:
        schulungen = Schulung.suche(suche, nur_aktive=True)
    else:
        schulungen = Schulung.get_mit_kommenden_terminen()

    # Widget nur für Admin/Mitarbeiter
    schulungen_widget = None
    if current_user.is_authenticated:
        if current_user.is_admin or current_user.rolle.name == 'mitarbeiter':
            schulungen_widget = {
                'buchungen_offen': Schulungsbuchung.query.filter_by(
                    status=BuchungStatus.GEBUCHT.value
                ).count(),
                'warteliste': Schulungsbuchung.query.filter_by(
                    status=BuchungStatus.WARTELISTE.value
                ).count(),
                'naechste_termine': Schulungsdurchfuehrung.get_kommende()[:3],
                'schulungen_aktiv': Schulung.query.filter_by(aktiv=True).count(),
            }

    return render_template(
        'schulungen/liste.html',
        schulungen=schulungen,
        suche=suche,
        schulungen_widget=schulungen_widget
    )


@schulungen_bp.route('/<int:id>')
def detail(id):
    """Show training details with upcoming executions."""
    schulung = Schulung.query.get_or_404(id)

    if not schulung.aktiv:
        abort(404)

    durchfuehrungen = schulung.kommende_durchfuehrungen

    return render_template(
        'schulungen/detail.html',
        schulung=schulung,
        durchfuehrungen=durchfuehrungen
    )


# =============================================================================
# IFRAME VARIANTS (no header/footer, for e-vendo.de embedding)
# =============================================================================

@schulungen_bp.route('/embed')
def embed_liste():
    """iframe-optimized list of trainings."""
    suche = request.args.get('suche', '').strip()
    theme = request.args.get('theme', 'light')

    if suche:
        schulungen = Schulung.suche(suche, nur_aktive=True)
    else:
        schulungen = Schulung.get_mit_kommenden_terminen()

    return render_template(
        'schulungen/embed_liste.html',
        schulungen=schulungen,
        suche=suche,
        theme=theme
    )


@schulungen_bp.route('/embed/<int:id>')
def embed_detail(id):
    """iframe-optimized training detail."""
    schulung = Schulung.query.get_or_404(id)

    if not schulung.aktiv:
        abort(404)

    theme = request.args.get('theme', 'light')
    durchfuehrungen = schulung.kommende_durchfuehrungen

    return render_template(
        'schulungen/embed_detail.html',
        schulung=schulung,
        durchfuehrungen=durchfuehrungen,
        theme=theme
    )


# =============================================================================
# CUSTOMER PORTAL (login required)
# =============================================================================

@schulungen_bp.route('/meine')
@login_required
def meine_schulungen():
    """List customer's booked trainings."""
    if not current_user.kunde:
        flash('Sie sind keinem Kunden zugeordnet.', 'warning')
        return redirect(url_for('main.dashboard'))

    buchungen = Schulungsbuchung.get_by_kunde(
        current_user.kunde.id,
        nur_aktive=True
    )

    # Separate into upcoming and past
    heute = date.today()
    kommende = []
    vergangene = []

    for buchung in buchungen:
        if buchung.durchfuehrung.start_datum >= heute:
            kommende.append(buchung)
        else:
            vergangene.append(buchung)

    return render_template(
        'schulungen/meine.html',
        kommende=kommende,
        vergangene=vergangene,
        BuchungStatus=BuchungStatus
    )


@schulungen_bp.route('/buchen/<int:durchfuehrung_id>', methods=['GET', 'POST'])
@login_required
def buchen(durchfuehrung_id):
    """Book a training execution."""
    durchfuehrung = Schulungsdurchfuehrung.query.get_or_404(durchfuehrung_id)

    if not current_user.kunde:
        flash('Sie sind keinem Kunden zugeordnet.', 'warning')
        return redirect(url_for('schulungen.detail', id=durchfuehrung.schulung_id))

    # Check if already booked
    if Schulungsbuchung.kunde_hat_gebucht(current_user.kunde.id, durchfuehrung_id):
        flash('Sie haben diese Schulung bereits gebucht.', 'info')
        return redirect(url_for('schulungen.meine_schulungen'))

    # Check if bookable
    if not durchfuehrung.is_geplant:
        flash('Diese Schulung kann nicht mehr gebucht werden.', 'warning')
        return redirect(url_for('schulungen.detail', id=durchfuehrung.schulung_id))

    if request.method == 'POST':
        # Determine status (gebucht or warteliste)
        if durchfuehrung.ist_ausgebucht:
            status = BuchungStatus.WARTELISTE.value
            message = 'Sie wurden auf die Warteliste gesetzt. Wir benachrichtigen Sie, wenn ein Platz frei wird.'
        else:
            status = BuchungStatus.GEBUCHT.value
            message = 'Ihre Buchung war erfolgreich!'

        # Create booking
        buchung = Schulungsbuchung(
            kunde_id=current_user.kunde.id,
            durchfuehrung_id=durchfuehrung_id,
            status=status,
            preis_bei_buchung=durchfuehrung.schulung.aktueller_preis
        )
        db.session.add(buchung)
        db.session.commit()

        log_event(
            'schulungen', 'gebucht',
            f'Schulung "{durchfuehrung.schulung.titel}" gebucht (Status: {status})',
            entity_type='Schulungsbuchung', entity_id=buchung.id
        )

        flash(message, 'success')
        return redirect(url_for('schulungen.meine_schulungen'))

    return render_template(
        'schulungen/buchen.html',
        durchfuehrung=durchfuehrung,
        schulung=durchfuehrung.schulung
    )


@schulungen_bp.route('/stornieren/<int:buchung_id>', methods=['POST'])
@login_required
def stornieren(buchung_id):
    """Cancel a booking."""
    buchung = Schulungsbuchung.query.get_or_404(buchung_id)

    # Security: Only owner can cancel
    if not current_user.kunde or buchung.kunde_id != current_user.kunde.id:
        abort(403)

    # Check if cancellation is allowed
    if not buchung.kann_storniert_werden:
        flash('Die Stornierungsfrist ist abgelaufen. Bitte kontaktieren Sie uns.', 'warning')
        return redirect(url_for('schulungen.meine_schulungen'))

    if buchung.is_storniert:
        flash('Diese Buchung wurde bereits storniert.', 'info')
        return redirect(url_for('schulungen.meine_schulungen'))

    # Cancel booking
    buchung.stornieren()
    db.session.commit()

    log_event(
        'schulungen', 'storniert',
        f'Schulung "{buchung.schulung.titel}" vom Kunden storniert',
        entity_type='Schulungsbuchung', entity_id=buchung.id
    )

    flash('Ihre Buchung wurde erfolgreich storniert.', 'success')
    return redirect(url_for('schulungen.meine_schulungen'))
