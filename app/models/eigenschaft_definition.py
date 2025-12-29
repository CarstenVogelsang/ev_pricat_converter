"""
EigenschaftDefinition Model - Definition der Produkteigenschaften (NTG-Felder)

Speichert die Metadaten für flexible Produkteigenschaften:
- NTG-Code (z.B. NTG-P-105)
- Name und Beschreibung
- Datentyp und Validierung
- Codelist-Referenz für Auswahllisten
- Gruppierung für UI-Organisation

Beispiele:
- NTG-P-105: "Batterie erforderlich" (Boolean)
- NTG-P-097: "Ursprungsland" (Codelist: laender)
- NTG-P-031: "Länge Stück in cm" (Decimal)
"""
from app import db


class DatenTyp:
    """Erlaubte Datentypen für Eigenschaften."""
    TEXT = 'text'           # Freitext (String)
    NUMBER = 'number'       # Dezimalzahl
    INTEGER = 'integer'     # Ganzzahl
    BOOLEAN = 'boolean'     # Ja/Nein
    DATE = 'date'           # Datum
    CODELIST = 'codelist'   # Auswahl aus ProduktLookup

    CHOICES = [
        (TEXT, 'Text'),
        (NUMBER, 'Dezimalzahl'),
        (INTEGER, 'Ganzzahl'),
        (BOOLEAN, 'Ja/Nein'),
        (DATE, 'Datum'),
        (CODELIST, 'Auswahlliste'),
    ]


class EigenschaftDefinition(db.Model):
    """Definition einer Produkteigenschaft (NTG-Feld)."""
    __tablename__ = 'eigenschaft_definition'

    id = db.Column(db.Integer, primary_key=True)

    # NTG-Code (unique identifier from NTG standard)
    # Format: NTG-P-XXX (e.g., NTG-P-105, NTG-P-097)
    ntg_code = db.Column(db.String(15), unique=True, index=True)

    # Human-readable name
    name = db.Column(db.String(100), nullable=False)

    # Detailed description (from Feldbeschreibung PDF)
    beschreibung = db.Column(db.Text)

    # Data type for validation
    datentyp = db.Column(db.String(20), nullable=False, default=DatenTyp.TEXT)

    # Maximum length for text fields (e.g., 35 for an35)
    max_laenge = db.Column(db.Integer)

    # Number of decimal places for number fields
    dezimalstellen = db.Column(db.Integer)

    # Reference to ProduktLookup.kategorie for codelist fields
    codelist_kategorie = db.Column(db.String(50))

    # UI grouping (e.g., 'batterie', 'weee', 'logistik', 'preise')
    gruppe = db.Column(db.String(50), index=True)

    # Sort order within group
    sortierung = db.Column(db.Integer, default=0)

    # Is this field required?
    pflichtfeld = db.Column(db.Boolean, default=False)

    # Active flag for soft-delete
    aktiv = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<EigenschaftDefinition {self.ntg_code}: {self.name}>'

    def to_dict(self):
        """Serialization for API/Export."""
        return {
            'id': self.id,
            'ntg_code': self.ntg_code,
            'name': self.name,
            'beschreibung': self.beschreibung,
            'datentyp': self.datentyp,
            'max_laenge': self.max_laenge,
            'dezimalstellen': self.dezimalstellen,
            'codelist_kategorie': self.codelist_kategorie,
            'gruppe': self.gruppe,
            'sortierung': self.sortierung,
            'pflichtfeld': self.pflichtfeld,
            'aktiv': self.aktiv
        }

    # === Class methods for common queries ===

    @classmethod
    def get_by_gruppe(cls, gruppe, nur_aktive=True):
        """Get all definitions in a group, sorted."""
        query = cls.query.filter_by(gruppe=gruppe)
        if nur_aktive:
            query = query.filter_by(aktiv=True)
        return query.order_by(cls.sortierung, cls.name).all()

    @classmethod
    def get_gruppen(cls):
        """Get all distinct groups."""
        result = db.session.query(cls.gruppe).filter(
            cls.gruppe.isnot(None),
            cls.aktiv == True
        ).distinct().order_by(cls.gruppe).all()
        return [r[0] for r in result]

    @classmethod
    def get_by_ntg_code(cls, ntg_code):
        """Get definition by NTG code."""
        return cls.query.filter_by(ntg_code=ntg_code).first()

    @classmethod
    def get_pflichtfelder(cls):
        """Get all required field definitions."""
        return cls.query.filter_by(pflichtfeld=True, aktiv=True)\
                        .order_by(cls.gruppe, cls.sortierung).all()

    @classmethod
    def get_choices_for_gruppe(cls, gruppe):
        """For select fields: List of (id, name) tuples."""
        entries = cls.get_by_gruppe(gruppe)
        return [(str(e.id), f"{e.ntg_code}: {e.name}") for e in entries]

    def validate_value(self, value):
        """
        Validate a value against this definition.

        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        if value is None or value == '':
            if self.pflichtfeld:
                return False, f"{self.name} ist ein Pflichtfeld"
            return True, None

        if self.datentyp == DatenTyp.TEXT:
            if self.max_laenge and len(str(value)) > self.max_laenge:
                return False, f"{self.name} darf max. {self.max_laenge} Zeichen haben"

        elif self.datentyp == DatenTyp.NUMBER:
            try:
                float(value)
            except (ValueError, TypeError):
                return False, f"{self.name} muss eine Zahl sein"

        elif self.datentyp == DatenTyp.INTEGER:
            try:
                int(value)
            except (ValueError, TypeError):
                return False, f"{self.name} muss eine Ganzzahl sein"

        elif self.datentyp == DatenTyp.BOOLEAN:
            if str(value).upper() not in ('J', 'N', 'JA', 'NEIN', 'Y', 'YES', 'NO', '1', '0', 'TRUE', 'FALSE'):
                return False, f"{self.name} muss Ja/Nein sein"

        elif self.datentyp == DatenTyp.CODELIST:
            if self.codelist_kategorie:
                from app.models import ProduktLookup
                lookup = ProduktLookup.get_by_code(self.codelist_kategorie, str(value))
                if not lookup:
                    return False, f"Ungültiger Code '{value}' für {self.name}"

        return True, None
