"""
ProduktLookup Model - Produkt-spezifische Codelisten

Speichert alle Codelisten für Produktdaten (NTG-Standard):
- Länder (258 Einträge)
- Währungen (6)
- Gewichtseinheiten (18)
- Batterien (88)
- WEEE Kennzeichnung (8)
- Gefahrengutschlüssel (26)
- DVD/Blu-Ray Codes (21)
- GPC Brick (75)
- Bamberger Verzeichnis (93)
- Saisonkennzeichen (43)
- MwSt-Sätze (31)
- Genre (49)
- Plattform (20)
- Gefahrstoffe (135)
- Lagerklassen (29)
"""
from app import db


class ProduktLookup(db.Model):
    """Produkt-spezifische Codelisten (Länder, Währungen, Batterien, etc.)"""
    __tablename__ = 'produkt_lookup'

    id = db.Column(db.Integer, primary_key=True)

    # Kategorie für Gruppierung (z.B. 'laender', 'waehrungen', 'batterien')
    kategorie = db.Column(db.String(50), nullable=False, index=True)

    # Code aus Quelldokument (z.B. 'DE', 'EUR', 'LR6')
    code = db.Column(db.String(50), nullable=False)

    # Anzeige-Bezeichnung (z.B. 'Deutschland', 'Euro', 'AA Batterie')
    bezeichnung = db.Column(db.String(255), nullable=False)

    # Flexible Zusatzfelder für kategorie-spezifische Daten
    # z.B. bei Batterien: zusatz_1 = Volt, zusatz_2 = IEC-Kennzeichen
    zusatz_1 = db.Column(db.String(100))
    zusatz_2 = db.Column(db.String(100))
    zusatz_3 = db.Column(db.String(100))

    # Sortierung innerhalb der Kategorie
    sortierung = db.Column(db.Integer, default=0)

    # Aktiv-Flag für Soft-Delete
    aktiv = db.Column(db.Boolean, default=True, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('kategorie', 'code', name='uq_produkt_lookup_kategorie_code'),
    )

    def __repr__(self):
        return f'<ProduktLookup {self.kategorie}:{self.code}>'

    def to_dict(self):
        """Serialisierung für API/Export"""
        return {
            'id': self.id,
            'kategorie': self.kategorie,
            'code': self.code,
            'bezeichnung': self.bezeichnung,
            'zusatz_1': self.zusatz_1,
            'zusatz_2': self.zusatz_2,
            'zusatz_3': self.zusatz_3,
            'sortierung': self.sortierung,
            'aktiv': self.aktiv
        }

    # === Klassenmethoden für häufige Abfragen ===

    @classmethod
    def get_by_kategorie(cls, kategorie, nur_aktive=True):
        """Alle Einträge einer Kategorie, sortiert"""
        query = cls.query.filter_by(kategorie=kategorie)
        if nur_aktive:
            query = query.filter_by(aktiv=True)
        return query.order_by(cls.sortierung, cls.bezeichnung).all()

    @classmethod
    def get_by_code(cls, kategorie, code):
        """Einzelnen Eintrag nach Kategorie und Code"""
        return cls.query.filter_by(kategorie=kategorie, code=code).first()

    @classmethod
    def get_choices(cls, kategorie, include_empty=True):
        """Für Select-Felder: Liste von (code, bezeichnung) Tupeln"""
        entries = cls.get_by_kategorie(kategorie)
        choices = [(e.code, e.bezeichnung) for e in entries]
        if include_empty:
            choices.insert(0, ('', '--- Bitte wählen ---'))
        return choices

    @classmethod
    def get_kategorien(cls):
        """Alle verfügbaren Kategorien"""
        result = db.session.query(cls.kategorie).distinct().order_by(cls.kategorie).all()
        return [r[0] for r in result]

    @classmethod
    def count_by_kategorie(cls):
        """Anzahl Einträge pro Kategorie"""
        from sqlalchemy import func
        result = db.session.query(
            cls.kategorie,
            func.count(cls.id)
        ).group_by(cls.kategorie).order_by(cls.kategorie).all()
        return dict(result)
