"""BrancheBranchenRolle (Industry-Role Assignment) model.

Zulässigkeitsmatrix: Definiert welche Rollen in welcher Branche erlaubt sind.
Nicht jede Rolle ist in jeder Branche sinnvoll (z.B. HERSTELLER in Steuerberatung).
"""
from app import db


class BrancheBranchenRolle(db.Model):
    """Zulässigkeitsmatrix: Welche Rollen sind in welcher Branche erlaubt.

    Diese Tabelle definiert, welche BranchenRollen für eine bestimmte Branche
    zur Auswahl stehen. Nur hier freigegebene Kombinationen können Kunden
    zugewiesen werden.

    Beispiel:
    - Branche "Spielwaren" + Rolle "HERSTELLER" = erlaubt
    - Branche "Spielwaren" + Rolle "EINZELHANDEL_ONLINE" = erlaubt
    - Branche "Steuerberatung" + Rolle "HERSTELLER" = NICHT erlaubt (kein Eintrag)
    """
    __tablename__ = 'branche_branchenrolle'

    id = db.Column(db.Integer, primary_key=True)
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
    branche = db.relationship('Branche', back_populates='zulaessige_rollen')
    branchenrolle = db.relationship('BranchenRolle', back_populates='zulaessig_in_branchen')

    # Unique Constraint: Jede Kombination nur einmal
    __table_args__ = (
        db.UniqueConstraint('branche_id', 'branchenrolle_id',
                           name='uq_branche_branchenrolle'),
    )

    def __repr__(self):
        return f'<BrancheBranchenRolle branche={self.branche_id} rolle={self.branchenrolle_id}>'
