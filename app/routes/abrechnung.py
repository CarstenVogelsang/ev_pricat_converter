"""API Usage Billing routes."""
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.models import KundeApiNutzung, Kunde

abrechnung_bp = Blueprint('abrechnung', __name__, url_prefix='/abrechnung')


@abrechnung_bp.route('/')
@login_required
def index():
    """Show API usage summary for current user."""
    # All usage entries for current user
    nutzungen = KundeApiNutzung.query.filter_by(user_id=current_user.id)\
        .order_by(KundeApiNutzung.created_at.desc())\
        .all()

    # Grouped by Kunde with totals
    summary_query = db.session.query(
        Kunde.id,
        Kunde.firmierung,
        func.sum(KundeApiNutzung.credits_used).label('total_credits'),
        func.sum(KundeApiNutzung.kosten_euro).label('total_kosten'),
        func.count(KundeApiNutzung.id).label('anzahl_calls')
    ).join(Kunde)\
        .filter(KundeApiNutzung.user_id == current_user.id)\
        .group_by(Kunde.id, Kunde.firmierung)\
        .order_by(Kunde.firmierung)\
        .all()

    # Total sum
    total = db.session.query(
        func.sum(KundeApiNutzung.credits_used).label('total_credits'),
        func.sum(KundeApiNutzung.kosten_euro).label('total_kosten')
    ).filter(KundeApiNutzung.user_id == current_user.id).first()

    return render_template(
        'abrechnung/index.html',
        nutzungen=nutzungen,
        summary=summary_query,
        total_credits=total.total_credits or 0,
        total_kosten=float(total.total_kosten or 0)
    )
