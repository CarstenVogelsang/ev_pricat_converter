"""KundeBranchenRolle (Customer-Industry-Role Assignment) model.

Speichert welche Rollen ein Kunde in einer bestimmten Branche hat.
Ein Kunde kann mehrere Rollen pro Branche haben (z.B. HERSTELLER + EINZELHANDEL_ONLINE).
"""
from app import db


class KundeBranchenRolle(db.Model):
    """Zuordnung: Kunde hat in einer Branche bestimmte Rollen.

    Diese Tabelle speichert die konkreten Rollen eines Kunden pro Branche.
    Die Rollen müssen in BrancheBranchenRolle für die jeweilige Branche
    freigegeben sein (Validierung in Service-Layer).

    Beispiel:
    - Kunde "Spielwaren Mueller" in Branche "Spielwaren":
      - Rolle FILIALIST
      - Rolle EINZELHANDEL_OMNICHANNEL
    """
    __tablename__ = 'kunde_branchenrolle'

    id = db.Column(db.Integer, primary_key=True)
    kunde_id = db.Column(
        db.Integer,
        db.ForeignKey('kunde.id', ondelete='CASCADE'),
        nullable=False
    )
    branche_id = db.Column(
        db.Integer,
        db.ForeignKey('branche.id', ondelete='CASCADE'),
        nullable=False
    )
    branchenrolle_id = db.Column(
        db.Integer,
        db.ForeignKey('branchenrolle.id', ondelete='CASCADE'),
        nullable=False
    )

    # Relationships
    kunde = db.relationship('Kunde', back_populates='branchenrollen')
    branche = db.relationship('Branche')
    branchenrolle = db.relationship('BranchenRolle', back_populates='kunden_mit_rolle')

    # Unique Constraint: Jede Kombination nur einmal
    __table_args__ = (
        db.UniqueConstraint('kunde_id', 'branche_id', 'branchenrolle_id',
                           name='uq_kunde_branche_branchenrolle'),
    )

    def __repr__(self):
        return f'<KundeBranchenRolle kunde={self.kunde_id} branche={self.branche_id} rolle={self.branchenrolle_id}>'
