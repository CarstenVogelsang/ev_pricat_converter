"""
Produkt Model - Zentrale Produktstammdaten (NTG-Standard)

Enthält die Kern-Felder, die direkt am Produkt gespeichert werden:
- Identifikation (EAN, Artikelnummer)
- Grunddaten (Bezeichnung, Marke, Hersteller)
- Preise (UVPE, MwSt)
- Logistik (Maße, Gewicht)
- Klassifikation (Attributgruppe, Zolltarif)
- Status und Termine

Weitere Eigenschaften werden über EigenschaftWert (EAV-Pattern) verknüpft.
"""
from datetime import datetime
from app import db


class ProduktStatus:
    """Status-Werte für Produkte."""
    ENTWURF = 'entwurf'
    AKTIV = 'aktiv'
    AUSLAUF = 'auslauf'
    ARCHIVIERT = 'archiviert'

    CHOICES = [
        (ENTWURF, 'Entwurf'),
        (AKTIV, 'Aktiv'),
        (AUSLAUF, 'Auslauf'),
        (ARCHIVIERT, 'Archiviert'),
    ]


class Produkt(db.Model):
    """Produktstammdaten mit Kern-Feldern."""
    __tablename__ = 'produkt'

    id = db.Column(db.Integer, primary_key=True)

    # === IDENTIFIKATION ===

    # EAN/GTIN (Pflichtfeld, unique) - NTG-P-007
    ean = db.Column(db.String(14), nullable=False, unique=True, index=True)

    # Artikelnummer Lieferant - NTG-P-013
    artikelnummer_lieferant = db.Column(db.String(35), index=True)

    # Artikelnummer Hersteller - NTG-P-014
    artikelnummer_hersteller = db.Column(db.String(35))

    # === LIEFERANT-BEZIEHUNG ===

    # Foreign Key zu Lieferant (optional, für interne Zuordnung)
    lieferant_id = db.Column(db.Integer, db.ForeignKey('lieferant.id'))

    # GLN Lieferant - NTG-P-001 (13-stellig, alternativ zum FK)
    gln_lieferant = db.Column(db.String(13))

    # === GRUNDDATEN ===

    # Artikelbezeichnung - NTG-P-015
    artikelbezeichnung = db.Column(db.String(250), nullable=False)

    # Kurzbezeichnung - NTG-P-016
    kurzbezeichnung = db.Column(db.String(35))

    # Hersteller Name - NTG-P-004
    hersteller_name = db.Column(db.String(35))

    # Markenname - NTG-P-010
    markenname = db.Column(db.String(35))

    # Serienname - NTG-P-012
    serienname = db.Column(db.String(35))

    # === PREISE ===

    # Unverbindliche Preisempfehlung (UVPE) - NTG-P-067
    uvpe = db.Column(db.Numeric(15, 2))

    # Einkaufspreis netto - NTG-P-091
    ekp_netto = db.Column(db.Numeric(15, 4))

    # MwSt-Satz - NTG-P-068
    mwst_satz = db.Column(db.Numeric(5, 2))

    # Währung - NTG-P-069 (Default: EUR)
    waehrung = db.Column(db.String(3), default='EUR')

    # === LOGISTIK (Stück-Ebene) ===

    # Länge Stück in cm - NTG-P-031
    stueck_laenge_cm = db.Column(db.Numeric(18, 3))

    # Breite Stück in cm - NTG-P-032
    stueck_breite_cm = db.Column(db.Numeric(18, 3))

    # Höhe Stück in cm - NTG-P-033
    stueck_hoehe_cm = db.Column(db.Numeric(18, 3))

    # Gewicht Stück in kg - NTG-P-034
    stueck_gewicht_kg = db.Column(db.Numeric(18, 3))

    # === KLASSIFIKATION ===

    # Attributgruppe (5-Ebenen Produktkategorisierung) - NTG-P-146
    attributgruppe_id = db.Column(db.Integer, db.ForeignKey('attributgruppe.id'))

    # Zolltarifnummer (8- oder 11-stellig) - NTG-P-089
    zolltarif_nr = db.Column(db.String(11))

    # Ursprungsland (ISO 3166-1 alpha-2) - NTG-P-097
    ursprungsland = db.Column(db.String(2))

    # === STATUS & TERMINE ===

    # Status (intern)
    status = db.Column(db.String(15), default=ProduktStatus.ENTWURF)

    # Lieferbar ab - NTG-P-074
    lieferbar_ab = db.Column(db.Date)

    # Lieferbar bis - NTG-P-075
    lieferbar_bis = db.Column(db.Date)

    # Erste Auslieferung - NTG-P-076
    erste_auslieferung = db.Column(db.Date)

    # === LANGTEXTE ===

    # B2C Werbetext (bis 6000 Zeichen) - NTG-P-156
    b2c_text = db.Column(db.Text)

    # B2B Kurztext - NTG-P-155
    b2b_kurztext = db.Column(db.String(500))

    # === META ===

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    # Erstellt von (User)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    # === RELATIONSHIPS ===

    lieferant = db.relationship('Lieferant', backref='produkte')
    attributgruppe = db.relationship('Attributgruppe', backref='produkte')
    created_by = db.relationship('User', backref='erstellte_produkte')

    # Eigenschaften über EigenschaftWert (EAV)
    eigenschaften = db.relationship(
        'EigenschaftWert',
        backref='produkt',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Produkt {self.ean}: {self.artikelbezeichnung[:30] if self.artikelbezeichnung else "?"}>'

    @property
    def vollstaendiger_name(self):
        """Marke + Bezeichnung für Anzeige."""
        if self.markenname:
            return f"{self.markenname} - {self.artikelbezeichnung}"
        return self.artikelbezeichnung

    @property
    def kategorie_pfad(self):
        """Vollständiger Kategorie-Pfad aus Attributgruppe."""
        if self.attributgruppe:
            return self.attributgruppe.vollstaendiger_name
        return None

    def to_dict(self, include_eigenschaften=False):
        """Serialization for API/Export."""
        data = {
            'id': self.id,
            'ean': self.ean,
            'artikelnummer_lieferant': self.artikelnummer_lieferant,
            'artikelnummer_hersteller': self.artikelnummer_hersteller,
            'artikelbezeichnung': self.artikelbezeichnung,
            'kurzbezeichnung': self.kurzbezeichnung,
            'hersteller_name': self.hersteller_name,
            'markenname': self.markenname,
            'serienname': self.serienname,
            'uvpe': str(self.uvpe) if self.uvpe else None,
            'ekp_netto': str(self.ekp_netto) if self.ekp_netto else None,
            'mwst_satz': str(self.mwst_satz) if self.mwst_satz else None,
            'waehrung': self.waehrung,
            'stueck_laenge_cm': str(self.stueck_laenge_cm) if self.stueck_laenge_cm else None,
            'stueck_breite_cm': str(self.stueck_breite_cm) if self.stueck_breite_cm else None,
            'stueck_hoehe_cm': str(self.stueck_hoehe_cm) if self.stueck_hoehe_cm else None,
            'stueck_gewicht_kg': str(self.stueck_gewicht_kg) if self.stueck_gewicht_kg else None,
            'zolltarif_nr': self.zolltarif_nr,
            'ursprungsland': self.ursprungsland,
            'status': self.status,
            'lieferbar_ab': self.lieferbar_ab.isoformat() if self.lieferbar_ab else None,
            'lieferbar_bis': self.lieferbar_bis.isoformat() if self.lieferbar_bis else None,
            'kategorie': self.kategorie_pfad,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

        if include_eigenschaften:
            data['eigenschaften'] = [e.to_dict() for e in self.eigenschaften.all()]

        return data

    # === CLASS METHODS ===

    @classmethod
    def get_by_ean(cls, ean):
        """Get product by EAN/GTIN."""
        return cls.query.filter_by(ean=ean).first()

    @classmethod
    def suche(cls, suchbegriff, limit=50):
        """Search products by EAN, article number, or name."""
        pattern = f'%{suchbegriff}%'
        return cls.query.filter(
            db.or_(
                cls.ean.ilike(pattern),
                cls.artikelnummer_lieferant.ilike(pattern),
                cls.artikelbezeichnung.ilike(pattern),
                cls.markenname.ilike(pattern),
            )
        ).limit(limit).all()

    @classmethod
    def get_by_lieferant(cls, lieferant_id, nur_aktive=True):
        """Get all products for a supplier."""
        query = cls.query.filter_by(lieferant_id=lieferant_id)
        if nur_aktive:
            query = query.filter(cls.status != ProduktStatus.ARCHIVIERT)
        return query.order_by(cls.artikelbezeichnung).all()

    @classmethod
    def count_by_status(cls):
        """Count products by status."""
        from sqlalchemy import func
        result = db.session.query(
            cls.status,
            func.count(cls.id)
        ).group_by(cls.status).all()
        return dict(result)

    # === EIGENSCHAFT HELPER ===

    def get_eigenschaft(self, ntg_code):
        """Get a specific property value by NTG code."""
        from app.models import EigenschaftDefinition, EigenschaftWert
        definition = EigenschaftDefinition.get_by_ntg_code(ntg_code)
        if not definition:
            return None

        wert = EigenschaftWert.query.filter_by(
            produkt_id=self.id,
            definition_id=definition.id
        ).first()

        return wert.wert if wert else None

    def set_eigenschaft(self, ntg_code, value):
        """Set a property value by NTG code."""
        from app.models import EigenschaftDefinition, EigenschaftWert
        definition = EigenschaftDefinition.get_by_ntg_code(ntg_code)
        if not definition:
            raise ValueError(f"Unbekannter NTG-Code: {ntg_code}")

        return EigenschaftWert.set_wert(self.id, definition.id, value)

    def get_eigenschaften_by_gruppe(self, gruppe):
        """Get all property values for a specific group."""
        from app.models import EigenschaftWert
        return EigenschaftWert.get_by_gruppe(self.id, gruppe)
