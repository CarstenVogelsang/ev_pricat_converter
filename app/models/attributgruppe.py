"""
Attributgruppe Model - 5-Ebenen Produktklassifikation (NTG Attributgruppenschlüssel)

Hierarchie:
- Ebene 1: Hauptkategorie (17 Stück: Spielzeug, Schreibwaren, Babyausstattung, etc.)
- Ebene 2: Unterkategorie (~100)
- Ebene 3: Sub-Unterkategorie (~300)
- Ebene 4: Produktgruppe (~800)
- Ebene 5: Spezifischer Typ (1684 gesamt: Babybälle, Beißringe, etc.)

NTG-Schlüssel Beispiel: "101001001001000" = Spielzeug > Baby > Babyspielzeug > Babyspielzeug > Babybälle
"""
from app import db


class Attributgruppe(db.Model):
    """5-Ebenen Produktkategorien (NTG Attributgruppenschlüssel)"""
    __tablename__ = 'attributgruppe'

    id = db.Column(db.Integer, primary_key=True)

    # Vollständiger NTG-Schlüssel (15 Zeichen)
    # Format: "1" + 2-stellig + 3-stellig + 3-stellig + 3-stellig + 3-stellig
    ntg_schluessel = db.Column(db.String(15), unique=True, index=True)

    # Ebene 1: Hauptkategorie (z.B. "01" = Spielzeug)
    ebene_1_code = db.Column(db.String(2))
    ebene_1_name = db.Column(db.String(100))

    # Ebene 2: Unterkategorie (z.B. "001" = Baby- & Kleinkindspielzeug)
    ebene_2_code = db.Column(db.String(3))
    ebene_2_name = db.Column(db.String(100))

    # Ebene 3: Sub-Unterkategorie (z.B. "001" = Babyspielzeug)
    ebene_3_code = db.Column(db.String(3))
    ebene_3_name = db.Column(db.String(100))

    # Ebene 4: Produktgruppe (z.B. "001" = Babybälle)
    ebene_4_code = db.Column(db.String(3))
    ebene_4_name = db.Column(db.String(100))

    # Ebene 5: Spezifischer Typ (z.B. "000" = Standard)
    ebene_5_code = db.Column(db.String(3))
    ebene_5_name = db.Column(db.String(100))

    # Aktiv-Flag
    aktiv = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<Attributgruppe {self.ntg_schluessel}: {self.vollstaendiger_name}>'

    @property
    def vollstaendiger_name(self):
        """Vollständiger Pfad: 'Spielzeug > Baby- & Kleinkind > Babyspielzeug > Babybälle'"""
        parts = []
        if self.ebene_1_name:
            parts.append(self.ebene_1_name)
        if self.ebene_2_name:
            parts.append(self.ebene_2_name)
        if self.ebene_3_name:
            parts.append(self.ebene_3_name)
        if self.ebene_4_name:
            parts.append(self.ebene_4_name)
        if self.ebene_5_name and self.ebene_5_name != self.ebene_4_name:
            parts.append(self.ebene_5_name)
        return ' > '.join(parts)

    @property
    def kurz_name(self):
        """Nur der spezifischste Name (Ebene 5 oder 4)"""
        return self.ebene_5_name or self.ebene_4_name or self.ebene_3_name or self.ebene_2_name or self.ebene_1_name

    def to_dict(self):
        """Serialisierung für API/Export"""
        return {
            'id': self.id,
            'ntg_schluessel': self.ntg_schluessel,
            'ebene_1': {'code': self.ebene_1_code, 'name': self.ebene_1_name},
            'ebene_2': {'code': self.ebene_2_code, 'name': self.ebene_2_name},
            'ebene_3': {'code': self.ebene_3_code, 'name': self.ebene_3_name},
            'ebene_4': {'code': self.ebene_4_code, 'name': self.ebene_4_name},
            'ebene_5': {'code': self.ebene_5_code, 'name': self.ebene_5_name},
            'vollstaendiger_name': self.vollstaendiger_name,
            'aktiv': self.aktiv
        }

    # === Klassenmethoden für häufige Abfragen ===

    @classmethod
    def get_hauptkategorien(cls):
        """Alle Ebene-1 Kategorien (unique)"""
        from sqlalchemy import func
        result = db.session.query(
            cls.ebene_1_code,
            cls.ebene_1_name,
            func.count(cls.id).label('anzahl')
        ).filter(cls.aktiv == True)\
         .group_by(cls.ebene_1_code, cls.ebene_1_name)\
         .order_by(cls.ebene_1_code)\
         .all()
        return [{'code': r[0], 'name': r[1], 'anzahl': r[2]} for r in result]

    @classmethod
    def get_by_ebene_1(cls, ebene_1_code):
        """Alle Einträge einer Hauptkategorie"""
        return cls.query.filter_by(ebene_1_code=ebene_1_code, aktiv=True)\
                        .order_by(cls.ebene_2_code, cls.ebene_3_code, cls.ebene_4_code, cls.ebene_5_code)\
                        .all()

    @classmethod
    def suche(cls, suchbegriff, limit=50):
        """Suche in allen Ebenen-Namen"""
        pattern = f'%{suchbegriff}%'
        return cls.query.filter(
            cls.aktiv == True,
            db.or_(
                cls.ebene_1_name.ilike(pattern),
                cls.ebene_2_name.ilike(pattern),
                cls.ebene_3_name.ilike(pattern),
                cls.ebene_4_name.ilike(pattern),
                cls.ebene_5_name.ilike(pattern),
            )
        ).limit(limit).all()

    @classmethod
    def get_choices(cls, ebene_1_code=None):
        """Für Select-Felder: Liste von (id, vollstaendiger_name) Tupeln"""
        query = cls.query.filter_by(aktiv=True)
        if ebene_1_code:
            query = query.filter_by(ebene_1_code=ebene_1_code)
        entries = query.order_by(cls.ntg_schluessel).all()
        choices = [(str(e.id), e.vollstaendiger_name) for e in entries]
        choices.insert(0, ('', '--- Bitte wählen ---'))
        return choices
