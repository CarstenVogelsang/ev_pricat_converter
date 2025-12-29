"""
EigenschaftWert Model - Eigenschaftswerte pro Produkt (EAV-Pattern)

Speichert die konkreten Werte von Produkteigenschaften.
Pro Produkt und EigenschaftDefinition gibt es genau einen Eintrag.

Wert-Spalten nach Datentyp:
- wert_text: Für Text und Codelist-Codes
- wert_number: Für Dezimalzahlen
- wert_integer: Für Ganzzahlen
- wert_boolean: Für Ja/Nein
- wert_date: Für Datumsangaben

Beispiele:
    Produkt 1, "Batterie erforderlich": wert_boolean = True
    Produkt 1, "Ursprungsland": wert_text = "DE"
    Produkt 1, "Länge in cm": wert_number = 25.5
"""
from datetime import date, datetime
from decimal import Decimal
from app import db


class EigenschaftWert(db.Model):
    """Eigenschaftswert für ein Produkt (EAV-Pattern)."""
    __tablename__ = 'eigenschaft_wert'

    id = db.Column(db.Integer, primary_key=True)

    # Foreign key to Produkt
    produkt_id = db.Column(
        db.Integer,
        db.ForeignKey('produkt.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Foreign key to EigenschaftDefinition
    definition_id = db.Column(
        db.Integer,
        db.ForeignKey('eigenschaft_definition.id'),
        nullable=False,
        index=True
    )

    # === Value columns (only one is filled based on datentyp) ===

    # Text value (for text, codelist codes)
    wert_text = db.Column(db.Text)

    # Numeric value (for decimals)
    wert_number = db.Column(db.Numeric(18, 4))

    # Integer value
    wert_integer = db.Column(db.Integer)

    # Boolean value (for Ja/Nein)
    wert_boolean = db.Column(db.Boolean)

    # Date value
    wert_date = db.Column(db.Date)

    # Unique constraint: One value per product per definition
    __table_args__ = (
        db.UniqueConstraint('produkt_id', 'definition_id', name='uq_eigenschaft_wert'),
    )

    # Relationships
    definition = db.relationship('EigenschaftDefinition', lazy='joined')

    def __repr__(self):
        return f'<EigenschaftWert P{self.produkt_id} {self.definition.ntg_code if self.definition else "?"}>'

    @property
    def wert(self):
        """
        Get the value based on the definition's datentyp.

        Returns the appropriate value column based on the data type.
        """
        if not self.definition:
            return self.wert_text  # Fallback

        datentyp = self.definition.datentyp

        if datentyp == 'boolean':
            return self.wert_boolean
        elif datentyp == 'number':
            return self.wert_number
        elif datentyp == 'integer':
            return self.wert_integer
        elif datentyp == 'date':
            return self.wert_date
        else:
            # text, codelist
            return self.wert_text

    @wert.setter
    def wert(self, value):
        """
        Set the value in the appropriate column based on definition's datentyp.
        """
        if not self.definition:
            self.wert_text = str(value) if value is not None else None
            return

        datentyp = self.definition.datentyp

        # Clear all value columns first
        self.wert_text = None
        self.wert_number = None
        self.wert_integer = None
        self.wert_boolean = None
        self.wert_date = None

        if value is None or value == '':
            return

        if datentyp == 'boolean':
            self.wert_boolean = self._parse_boolean(value)
        elif datentyp == 'number':
            self.wert_number = Decimal(str(value))
        elif datentyp == 'integer':
            self.wert_integer = int(value)
        elif datentyp == 'date':
            self.wert_date = self._parse_date(value)
        else:
            # text, codelist
            self.wert_text = str(value)

    def _parse_boolean(self, value):
        """Parse various boolean representations."""
        if isinstance(value, bool):
            return value
        val_str = str(value).upper().strip()
        return val_str in ('J', 'JA', 'Y', 'YES', '1', 'TRUE', 'WAHR')

    def _parse_date(self, value):
        """Parse date from various formats."""
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, str):
            # Try common formats
            for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y'):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
        return None

    @property
    def wert_anzeige(self):
        """
        Human-readable display value.

        For codelist values, returns the bezeichnung instead of just the code.
        """
        wert = self.wert

        if wert is None:
            return ''

        if self.definition and self.definition.datentyp == 'codelist':
            from app.models import ProduktLookup
            kategorie = self.definition.codelist_kategorie
            if kategorie:
                lookup = ProduktLookup.get_by_code(kategorie, str(wert))
                if lookup:
                    return lookup.bezeichnung
            return str(wert)

        if self.definition and self.definition.datentyp == 'boolean':
            return 'Ja' if wert else 'Nein'

        if isinstance(wert, date):
            return wert.strftime('%d.%m.%Y')

        if isinstance(wert, Decimal):
            return str(wert).rstrip('0').rstrip('.')

        return str(wert)

    def to_dict(self):
        """Serialization for API/Export."""
        return {
            'id': self.id,
            'produkt_id': self.produkt_id,
            'definition_id': self.definition_id,
            'ntg_code': self.definition.ntg_code if self.definition else None,
            'name': self.definition.name if self.definition else None,
            'wert': str(self.wert) if self.wert is not None else None,
            'wert_anzeige': self.wert_anzeige
        }

    # === Class methods ===

    @classmethod
    def get_for_produkt(cls, produkt_id, nur_gefuellt=True):
        """Get all property values for a product."""
        query = cls.query.filter_by(produkt_id=produkt_id)
        if nur_gefuellt:
            # Only return entries with actual values
            query = query.filter(
                db.or_(
                    cls.wert_text.isnot(None),
                    cls.wert_number.isnot(None),
                    cls.wert_integer.isnot(None),
                    cls.wert_boolean.isnot(None),
                    cls.wert_date.isnot(None),
                )
            )
        return query.all()

    @classmethod
    def get_by_gruppe(cls, produkt_id, gruppe):
        """Get property values for a product in a specific group."""
        from app.models import EigenschaftDefinition
        return cls.query.join(EigenschaftDefinition).filter(
            cls.produkt_id == produkt_id,
            EigenschaftDefinition.gruppe == gruppe
        ).order_by(EigenschaftDefinition.sortierung).all()

    @classmethod
    def set_wert(cls, produkt_id, definition_id, value):
        """
        Set or update a property value for a product.

        Creates a new entry if it doesn't exist, updates if it does.
        """
        existing = cls.query.filter_by(
            produkt_id=produkt_id,
            definition_id=definition_id
        ).first()

        if existing:
            existing.wert = value
            return existing
        else:
            new_entry = cls(produkt_id=produkt_id, definition_id=definition_id)
            # Load definition for proper type handling
            from app.models import EigenschaftDefinition
            new_entry.definition = EigenschaftDefinition.query.get(definition_id)
            new_entry.wert = value
            db.session.add(new_entry)
            return new_entry

    @classmethod
    def delete_for_produkt(cls, produkt_id):
        """Delete all property values for a product."""
        cls.query.filter_by(produkt_id=produkt_id).delete()
